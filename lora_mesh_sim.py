#!/usr/bin/env python3
"""Packet-level LoRa mesh simulator.

This simulator is intentionally compact: it models LoRa as a shared,
half-duplex broadcast channel and implements behavior-equivalent baselines for
Meshtastic-style managed flooding and MeshCore-style path-cache/source routing.

It is not a firmware clone. The goal is to provide a fair, reproducible
research harness where multiple routing policies run on the same topology,
traffic, PHY, collision, and propagation models.
"""

from __future__ import annotations

import argparse
import csv
import json
import heapq
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


BROADCAST_DST = -1
DEFAULT_CALM_DISCOVERY_WINDOW_S = 2.0


def dbm_to_mw(dbm: float) -> float:
    return 10 ** (dbm / 10.0)


def mw_to_dbm(mw: float) -> float:
    if mw <= 0:
        return -float("inf")
    return 10.0 * math.log10(mw)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def required_snr_db(sf: int) -> float:
    """Approximate LoRa demodulation SNR threshold by spreading factor."""

    table = {
        7: -7.5,
        8: -10.0,
        9: -12.5,
        10: -15.0,
        11: -17.5,
        12: -20.0,
    }
    return table[sf]


@dataclass(frozen=True)
class RadioConfig:
    sf: int = 9
    bw_hz: int = 125_000
    cr: int = 1  # LoRa coding-rate index: 1 means 4/5, 4 means 4/8.
    payload_bytes: int = 32
    preamble_symbols: int = 8
    explicit_header: bool = True
    crc: bool = True
    tx_power_dbm: float = 17.0
    carrier_mhz: float = 915.0
    noise_figure_db: float = 6.0
    path_loss_exp: float = 2.7
    shadow_sigma_db: float = 4.0
    capture_threshold_db: float = 6.0
    prr_slope: float = 1.15

    @property
    def noise_floor_dbm(self) -> float:
        return -174.0 + 10.0 * math.log10(self.bw_hz) + self.noise_figure_db

    @property
    def toa_s(self) -> float:
        """LoRa time-on-air for the configured packet size."""

        sf = self.sf
        bw = self.bw_hz
        cr = self.cr
        payload = self.payload_bytes
        de = 1 if sf >= 11 and bw <= 125_000 else 0
        ih = 0 if self.explicit_header else 1
        crc = 1 if self.crc else 0
        t_sym = (2**sf) / bw
        t_preamble = (self.preamble_symbols + 4.25) * t_sym
        numerator = 8 * payload - 4 * sf + 28 + 16 * crc - 20 * ih
        denominator = 4 * (sf - 2 * de)
        payload_symbols = 8 + max(math.ceil(numerator / denominator) * (cr + 4), 0)
        return t_preamble + payload_symbols * t_sym


@dataclass
class Node:
    node_id: int
    x: float
    y: float
    role: str = "router"
    battery: float = 1.0
    tx_available_at: float = 0.0
    congestion: float = 0.0
    queue_delay: float = 0.0

    @property
    def can_relay(self) -> bool:
        return self.role in {"router", "repeater"}


@dataclass(frozen=True)
class Packet:
    kind: str
    flow_id: int
    origin: int
    final_dst: int
    ttl: int
    created_at: float
    protocol: str
    request_id: int = 0
    path: Tuple[int, ...] = ()
    path_index: int = 0
    learned_path: Tuple[int, ...] = ()
    path_confidence: float = 0.0
    app_payload: bool = True

    @property
    def flood_key(self) -> Tuple[str, int, int, int]:
        return (self.kind, self.origin, self.flow_id, self.request_id)

    @property
    def is_control(self) -> bool:
        return self.kind in {"RREQ", "RREP"}

    def with_ttl(self, ttl: int) -> "Packet":
        return Packet(
            kind=self.kind,
            flow_id=self.flow_id,
            origin=self.origin,
            final_dst=self.final_dst,
            ttl=ttl,
            created_at=self.created_at,
            protocol=self.protocol,
            request_id=self.request_id,
            path=self.path,
            path_index=self.path_index,
            learned_path=self.learned_path,
            path_confidence=self.path_confidence,
            app_payload=self.app_payload,
        )

    def append_path(self, node_id: int) -> "Packet":
        return Packet(
            kind=self.kind,
            flow_id=self.flow_id,
            origin=self.origin,
            final_dst=self.final_dst,
            ttl=self.ttl,
            created_at=self.created_at,
            protocol=self.protocol,
            request_id=self.request_id,
            path=self.path + (node_id,),
            path_index=self.path_index,
            learned_path=self.learned_path,
            path_confidence=self.path_confidence,
            app_payload=self.app_payload,
        )

    def advance_path(self) -> "Packet":
        return Packet(
            kind=self.kind,
            flow_id=self.flow_id,
            origin=self.origin,
            final_dst=self.final_dst,
            ttl=self.ttl,
            created_at=self.created_at,
            protocol=self.protocol,
            request_id=self.request_id,
            path=self.path,
            path_index=self.path_index + 1,
            learned_path=self.learned_path,
            path_confidence=self.path_confidence,
            app_payload=self.app_payload,
        )


@dataclass
class PendingSend:
    canceled: bool = False


@dataclass
class Transmission:
    tx_id: int
    sender: int
    packet: Packet
    start: float
    end: float


@dataclass
class RxInfo:
    sender: int
    rx_power_dbm: float
    snr_db: float
    sinr_db: float
    collided: bool


@dataclass
class FlowRecord:
    flow_id: int
    src: int
    dst: int
    created_at: float
    delivered_at: Optional[float] = None
    broadcast_receivers: Set[int] = field(default_factory=set)


@dataclass(frozen=True)
class RouteEntry:
    created_at: float
    expires_at: float
    path: Tuple[int, ...]
    confidence: float


@dataclass(frozen=True)
class AdaptiveProfile:
    name: str
    route_ttl_s: float
    discovery_window_s: float
    fallback_confidence_threshold: float
    fallback_ttl: int
    fallback_delay_margin_s: float
    hop_penalty_per_hop: float
    route_age_penalty: float


@dataclass(frozen=True)
class LearningSnapshot:
    tx_count: int
    control_tx: int
    collision_fail: int
    route_cache_hits: int
    route_cache_misses: int
    route_repair_count: int
    fallback_forward_count: int
    path_confidence_total: float
    path_confidence_samples: int
    unicast_flows: int
    broadcast_flows: int
    unicast_deliveries: int
    broadcast_deliveries: int
    delivery_delay_total_s: float
    delivery_delay_samples: int


@dataclass
class FlowDecision:
    src: int
    dst: int
    state_index: int
    action_index: int
    profile_name: str
    created_at: float
    delivered: bool = False
    delivered_at: Optional[float] = None
    control_count: int = 0
    fallback_count: int = 0
    route_miss: int = 0
    timeout_retries: int = 0
    confidence: float = 0.0


class Metrics:
    def __init__(self, node_count: int) -> None:
        self.node_count = node_count
        self.flows: Dict[int, FlowRecord] = {}
        self.unicast_flows = 0
        self.broadcast_flows = 0
        self.unicast_deliveries = 0
        self.broadcast_deliveries = 0
        self.delivery_delay_total_s = 0.0
        self.delivery_delay_samples = 0
        self.tx_count = 0
        self.data_tx = 0
        self.control_tx = 0
        self.total_airtime_s = 0.0
        self.rx_success = 0
        self.rx_fail = 0
        self.collision_fail = 0
        self.duplicate_rx = 0
        self.suppressed_forwards = 0
        self.route_requests = 0
        self.route_replies = 0
        self.route_cache_hits = 0
        self.route_cache_misses = 0
        self.fallback_forward_count = 0
        self.route_repair_count = 0
        self.path_confidence_total = 0.0
        self.path_confidence_samples = 0
        self.policy_switch_count = 0
        self.policy_update_count = 0
        self.policy_reward_total = 0.0
        self.active_profile_index = -1

    def register_flow(self, flow_id: int, src: int, dst: int, now: float) -> None:
        self.flows[flow_id] = FlowRecord(flow_id, src, dst, now)
        if dst == BROADCAST_DST:
            self.broadcast_flows += 1
        else:
            self.unicast_flows += 1

    def mark_delivered(self, flow_id: int, receiver: int, now: float) -> None:
        flow = self.flows.get(flow_id)
        if flow is None:
            return
        if flow.dst == BROADCAST_DST:
            if receiver != flow.src:
                was_new = receiver not in flow.broadcast_receivers
                flow.broadcast_receivers.add(receiver)
                if was_new:
                    self.broadcast_deliveries += 1
                    delay = max(0.0, now - flow.created_at)
                    self.delivery_delay_total_s += delay
                    self.delivery_delay_samples += 1
        elif receiver == flow.dst and flow.delivered_at is None:
            flow.delivered_at = now
            self.unicast_deliveries += 1
            delay = max(0.0, now - flow.created_at)
            self.delivery_delay_total_s += delay
            self.delivery_delay_samples += 1

    def record_path_confidence(self, confidence: float) -> None:
        self.path_confidence_total += clamp(confidence, 0.0, 1.0)
        self.path_confidence_samples += 1

    def snapshot(self) -> LearningSnapshot:
        return LearningSnapshot(
            tx_count=self.tx_count,
            control_tx=self.control_tx,
            collision_fail=self.collision_fail,
            route_cache_hits=self.route_cache_hits,
            route_cache_misses=self.route_cache_misses,
            route_repair_count=self.route_repair_count,
            fallback_forward_count=self.fallback_forward_count,
            path_confidence_total=self.path_confidence_total,
            path_confidence_samples=self.path_confidence_samples,
            unicast_flows=self.unicast_flows,
            broadcast_flows=self.broadcast_flows,
            unicast_deliveries=self.unicast_deliveries,
            broadcast_deliveries=self.broadcast_deliveries,
            delivery_delay_total_s=self.delivery_delay_total_s,
            delivery_delay_samples=self.delivery_delay_samples,
        )

    def summarize(self, protocol: str, seed: int, duration_s: float) -> Dict[str, Any]:
        unicast = [f for f in self.flows.values() if f.dst != BROADCAST_DST]
        broadcast = [f for f in self.flows.values() if f.dst == BROADCAST_DST]
        delivered_unicast = [f for f in unicast if f.delivered_at is not None]
        unicast_pdr = len(delivered_unicast) / len(unicast) if unicast else 0.0
        delays = [f.delivered_at - f.created_at for f in delivered_unicast if f.delivered_at]
        avg_delay = sum(delays) / len(delays) if delays else 0.0

        if broadcast:
            expected = len(broadcast) * (self.node_count - 1)
            actual = sum(len(f.broadcast_receivers) for f in broadcast)
            broadcast_coverage = actual / expected if expected else 0.0
        else:
            broadcast_coverage = 0.0

        delivered_total = len(delivered_unicast) + sum(len(f.broadcast_receivers) for f in broadcast)
        airtime_per_delivery = self.total_airtime_s / delivered_total if delivered_total else 0.0
        mean_delivery_delay = (
            self.delivery_delay_total_s / self.delivery_delay_samples
            if self.delivery_delay_samples
            else 0.0
        )
        mean_path_confidence = (
            self.path_confidence_total / self.path_confidence_samples
            if self.path_confidence_samples
            else 0.0
        )
        control_overhead_ratio = self.control_tx / self.tx_count if self.tx_count else 0.0

        return {
            "protocol": protocol,
            "seed": seed,
            "duration_s": round(duration_s, 6),
            "flows": len(self.flows),
            "unicast_flows": len(unicast),
            "broadcast_flows": len(broadcast),
            "unicast_pdr": round(unicast_pdr, 6),
            "broadcast_coverage": round(broadcast_coverage, 6),
            "avg_delay_s": round(avg_delay, 6),
            "unicast_deliveries": self.unicast_deliveries,
            "broadcast_deliveries": self.broadcast_deliveries,
            "tx_count": self.tx_count,
            "data_tx": self.data_tx,
            "control_tx": self.control_tx,
            "total_airtime_s": round(self.total_airtime_s, 6),
            "airtime_per_delivery_s": round(airtime_per_delivery, 6),
            "mean_delivery_delay_s": round(mean_delivery_delay, 6),
            "rx_success": self.rx_success,
            "rx_fail": self.rx_fail,
            "collision_fail": self.collision_fail,
            "duplicate_rx": self.duplicate_rx,
            "suppressed_forwards": self.suppressed_forwards,
            "route_requests": self.route_requests,
            "route_replies": self.route_replies,
            "route_cache_hits": self.route_cache_hits,
            "route_cache_misses": self.route_cache_misses,
            "fallback_forward_count": self.fallback_forward_count,
            "route_repair_count": self.route_repair_count,
            "mean_path_confidence": round(mean_path_confidence, 6),
            "control_overhead_ratio": round(control_overhead_ratio, 6),
            "policy_switch_count": self.policy_switch_count,
            "policy_update_count": self.policy_update_count,
            "policy_reward_total": round(self.policy_reward_total, 6),
            "active_profile_index": self.active_profile_index,
        }


class Simulator:
    def __init__(
        self,
        nodes: Sequence[Node],
        radio: RadioConfig,
        protocol: "RoutingProtocol",
        seed: int,
        max_hops: int,
    ) -> None:
        self.nodes = {node.node_id: node for node in nodes}
        self.radio = radio
        self.protocol = protocol
        self.seed = seed
        self.random = random.Random(seed)
        self.max_hops = max_hops
        self.now = 0.0
        self._event_counter = 0
        self._tx_counter = 0
        self.events: List[Tuple[float, int, str, Any]] = []
        self.transmissions: List[Transmission] = []
        self.metrics = Metrics(len(nodes))
        self.protocol.bind(self)

    def schedule(self, when: float, event_type: str, data: Any) -> None:
        self._event_counter += 1
        heapq.heappush(self.events, (when, self._event_counter, event_type, data))

    def distance_m(self, a: int, b: int) -> float:
        na = self.nodes[a]
        nb = self.nodes[b]
        return math.hypot(na.x - nb.x, na.y - nb.y)

    def path_loss_db(self, distance_m: float) -> float:
        distance_m = max(distance_m, 1.0)
        # Free-space path loss at 1 m. 32.44 + MHz + km form.
        pl0 = 32.44 + 20.0 * math.log10(self.radio.carrier_mhz) + 20.0 * math.log10(0.001)
        shadow = self.random.gauss(0.0, self.radio.shadow_sigma_db)
        return pl0 + 10.0 * self.radio.path_loss_exp * math.log10(distance_m) + shadow

    def rx_power_dbm(self, sender: int, receiver: int) -> float:
        return self.radio.tx_power_dbm - self.path_loss_db(self.distance_m(sender, receiver))

    def snr_from_power(self, rx_power_dbm: float) -> float:
        return rx_power_dbm - self.radio.noise_floor_dbm

    def prr_from_snr(self, snr_db: float) -> float:
        margin = snr_db - required_snr_db(self.radio.sf)
        return 1.0 / (1.0 + math.exp(-self.radio.prr_slope * margin))

    def transmit_later(
        self,
        sender: int,
        packet: Packet,
        delay_s: float,
        pending: Optional[PendingSend] = None,
    ) -> PendingSend:
        handle = pending or PendingSend()
        self.schedule(self.now + max(0.0, delay_s), "tx_request", (sender, packet, handle))
        return handle

    def begin_transmission(self, sender: int, packet: Packet, pending: PendingSend) -> None:
        if pending.canceled:
            return
        node = self.nodes[sender]
        start = max(self.now, node.tx_available_at)
        end = start + self.radio.toa_s
        node.tx_available_at = end
        self._tx_counter += 1
        tx = Transmission(self._tx_counter, sender, packet, start, end)
        self.transmissions.append(tx)
        self.metrics.tx_count += 1
        self.metrics.total_airtime_s += self.radio.toa_s
        if packet.is_control:
            self.metrics.control_tx += 1
        else:
            self.metrics.data_tx += 1
        if packet.kind == "RREQ":
            self.metrics.route_requests += 1
        if packet.kind == "RREP":
            self.metrics.route_replies += 1
        if packet.kind == "FALLBACK":
            self.metrics.fallback_forward_count += 1
        self.schedule(end, "tx_end", tx)

    def transmissions_overlapping(self, start: float, end: float) -> Iterable[Transmission]:
        for tx in self.transmissions:
            if tx.start < end and start < tx.end:
                yield tx

    def prune_transmissions(self) -> None:
        """Keep only transmissions that can still overlap packets ending now.

        All packets use the same fixed LoRa PHY profile in this simulator, so a
        packet ending at time t can only overlap transmissions whose end time is
        after t - ToA. Future scheduled transmissions are also kept.
        """

        earliest_relevant_end = self.now - self.radio.toa_s
        self.transmissions = [
            tx for tx in self.transmissions if tx.end > earliest_relevant_end
        ]

    def receiver_is_transmitting(self, receiver: int, start: float, end: float) -> bool:
        return any(tx.sender == receiver for tx in self.transmissions_overlapping(start, end))

    def try_receive(self, tx: Transmission, receiver: int) -> Optional[RxInfo]:
        if receiver == tx.sender:
            return None
        if self.receiver_is_transmitting(receiver, tx.start, tx.end):
            self.metrics.rx_fail += 1
            return None

        signal_dbm = self.rx_power_dbm(tx.sender, receiver)
        interference_dbm: List[float] = []
        for other in self.transmissions_overlapping(tx.start, tx.end):
            if other.tx_id == tx.tx_id or other.sender == receiver:
                continue
            interference_dbm.append(self.rx_power_dbm(other.sender, receiver))

        snr_db = self.snr_from_power(signal_dbm)
        collided = False
        sinr_db = snr_db
        if interference_dbm:
            strongest_interference = max(interference_dbm)
            if signal_dbm < strongest_interference + self.radio.capture_threshold_db:
                self.metrics.rx_fail += 1
                self.metrics.collision_fail += 1
                return None
            noise_mw = dbm_to_mw(self.radio.noise_floor_dbm)
            signal_mw = dbm_to_mw(signal_dbm)
            interference_mw = sum(dbm_to_mw(x) for x in interference_dbm)
            sinr_db = 10.0 * math.log10(signal_mw / (noise_mw + interference_mw))
            collided = True

        if self.random.random() <= self.prr_from_snr(sinr_db):
            self.metrics.rx_success += 1
            return RxInfo(tx.sender, signal_dbm, snr_db, sinr_db, collided)

        self.metrics.rx_fail += 1
        return None

    def handle_tx_end(self, tx: Transmission) -> None:
        self.prune_transmissions()
        for receiver in self.nodes:
            rx = self.try_receive(tx, receiver)
            if rx is not None:
                self.protocol.on_receive(receiver, tx.packet, rx)

    def mark_delivered(self, flow_id: int, receiver: int, packet: Packet) -> None:
        flow = self.metrics.flows.get(flow_id)
        was_delivered = False
        if flow is not None:
            if flow.dst == BROADCAST_DST:
                was_delivered = receiver != flow.src and receiver not in flow.broadcast_receivers
            else:
                was_delivered = receiver == flow.dst and flow.delivered_at is None
        self.metrics.mark_delivered(flow_id, receiver, self.now)
        if was_delivered:
            self.protocol.on_delivery(flow_id, receiver, self.now, packet)

    def run(self, until_s: float) -> Metrics:
        while self.events:
            when, _, event_type, data = heapq.heappop(self.events)
            if when > until_s:
                break
            self.now = when
            if event_type == "app_send":
                src, dst, flow_id = data
                self.protocol.send_app(src, dst, flow_id)
            elif event_type == "tx_request":
                sender, packet, pending = data
                self.begin_transmission(sender, packet, pending)
            elif event_type == "tx_end":
                self.handle_tx_end(data)
            elif event_type == "protocol_timer":
                data()
            elif event_type == "flow_timeout":
                flow_id = data
                flow = self.metrics.flows.get(flow_id)
                if flow is not None and flow.dst != BROADCAST_DST:
                    self.protocol.on_flow_completion(flow_id, flow.delivered_at is not None, self.now)
            else:
                raise ValueError(f"unknown event type: {event_type}")
        self.now = until_s
        return self.metrics


class RoutingProtocol:
    name = "base"

    def bind(self, sim: Simulator) -> None:
        self.sim = sim

    def send_app(self, src: int, dst: int, flow_id: int) -> None:
        raise NotImplementedError

    def on_receive(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        raise NotImplementedError

    def on_delivery(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        return None

    def on_flow_completion(self, flow_id: int, delivered: bool, now: float) -> None:
        return None


class MeshtasticLike(RoutingProtocol):
    """Managed-flooding baseline.

    A new packet is rebroadcast once by relay-capable nodes. Forwarding is
    delayed, and pending rebroadcasts are suppressed if another copy is heard.
    """

    name = "meshtastic-like"

    def __init__(
        self,
        base_delay_s: float = 0.75,
        jitter_s: float = 0.75,
        role_bonus_s: float = 0.25,
    ) -> None:
        self.base_delay_s = base_delay_s
        self.jitter_s = jitter_s
        self.role_bonus_s = role_bonus_s
        self.seen: Dict[int, Set[Tuple[str, int, int, int]]] = {}
        self.pending: Dict[Tuple[int, Tuple[str, int, int, int]], PendingSend] = {}

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.seen = {node_id: set() for node_id in sim.nodes}
        self.pending = {}

    def send_app(self, src: int, dst: int, flow_id: int) -> None:
        self.sim.metrics.register_flow(flow_id, src, dst, self.sim.now)
        packet = Packet(
            kind="DATA",
            flow_id=flow_id,
            origin=src,
            final_dst=dst,
            ttl=self.sim.max_hops,
            created_at=self.sim.now,
            protocol=self.name,
        )
        self.seen[src].add(packet.flood_key)
        self.sim.transmit_later(src, packet, delay_s=0.0)

    def managed_delay(self, receiver: int, rx: RxInfo) -> float:
        node = self.sim.nodes[receiver]
        margin = rx.snr_db - required_snr_db(self.sim.radio.sf)
        snr_penalty = clamp((8.0 - margin) / 8.0, 0.0, 1.0) * 0.6
        role_discount = self.role_bonus_s if node.role == "repeater" else 0.0
        return max(
            0.05,
            self.base_delay_s
            + snr_penalty
            + self.sim.random.random() * self.jitter_s
            - role_discount,
        )

    def on_receive(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if packet.kind != "DATA":
            return
        key = packet.flood_key
        pending_key = (receiver, key)
        if key in self.seen[receiver]:
            pending = self.pending.get(pending_key)
            if pending is not None and not pending.canceled:
                pending.canceled = True
                self.sim.metrics.suppressed_forwards += 1
            self.sim.metrics.duplicate_rx += 1
            return

        self.seen[receiver].add(key)
        if packet.final_dst == BROADCAST_DST or packet.final_dst == receiver:
            self.sim.mark_delivered(packet.flow_id, receiver, packet)

        node = self.sim.nodes[receiver]
        if packet.ttl <= 1 or not node.can_relay:
            return
        if packet.final_dst != BROADCAST_DST and packet.final_dst == receiver:
            return

        forwarded = packet.with_ttl(packet.ttl - 1)
        delay = self.managed_delay(receiver, rx)
        pending = self.sim.transmit_later(receiver, forwarded, delay_s=delay)
        self.pending[pending_key] = pending


class MeshCoreLike(RoutingProtocol):
    """Path-discovery and source-route baseline.

    First unicast to a destination floods a route request. The destination
    replies along the reverse discovered path, and the source caches the path.
    Later unicast packets carry the complete source route and are forwarded
    only by the next node on that route.
    """

    name = "meshcore-like"

    def __init__(
        self,
        route_ttl_s: float = 300.0,
        flood_base_delay_s: float = 0.5,
        flood_jitter_s: float = 0.7,
    ) -> None:
        self.route_ttl_s = route_ttl_s
        self.flood_base_delay_s = flood_base_delay_s
        self.flood_jitter_s = flood_jitter_s
        self.route_cache: Dict[int, Dict[int, Tuple[float, Tuple[int, ...]]]] = {}
        self.pending_data: Dict[Tuple[int, int], List[int]] = {}
        self.seen_rreq: Dict[int, Set[Tuple[int, int, int]]] = {}

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.route_cache = {node_id: {} for node_id in sim.nodes}
        self.pending_data = {}
        self.seen_rreq = {node_id: set() for node_id in sim.nodes}

    def send_app(self, src: int, dst: int, flow_id: int) -> None:
        self.sim.metrics.register_flow(flow_id, src, dst, self.sim.now)
        if dst == BROADCAST_DST:
            # MeshCore still needs flooding for group/broadcast style traffic.
            packet = Packet(
                kind="DATA",
                flow_id=flow_id,
                origin=src,
                final_dst=dst,
                ttl=self.sim.max_hops,
                created_at=self.sim.now,
                protocol=self.name,
            )
            flood_key = (packet.origin, packet.flow_id, packet.request_id)
            self.seen_rreq[src].add(flood_key)
            self.sim.transmit_later(src, packet, delay_s=0.0)
            return

        route = self.get_route(src, dst)
        if route is not None:
            self.sim.metrics.route_cache_hits += 1
            self.send_data_on_path(src, dst, flow_id, route)
            return

        self.sim.metrics.route_cache_misses += 1
        self.pending_data.setdefault((src, dst), []).append(flow_id)
        if len(self.pending_data[(src, dst)]) == 1:
            self.start_route_discovery(src, dst, flow_id)

    def get_route(self, src: int, dst: int) -> Optional[Tuple[int, ...]]:
        entry = self.route_cache[src].get(dst)
        if entry is None:
            return None
        expires_at, path = entry
        if expires_at <= self.sim.now:
            del self.route_cache[src][dst]
            return None
        return path

    def start_route_discovery(self, src: int, dst: int, flow_id: int) -> None:
        request_id = flow_id
        packet = Packet(
            kind="RREQ",
            flow_id=flow_id,
            origin=src,
            final_dst=dst,
            ttl=self.sim.max_hops,
            created_at=self.sim.now,
            protocol=self.name,
            request_id=request_id,
            path=(src,),
            app_payload=False,
        )
        self.seen_rreq[src].add((src, dst, request_id))
        self.sim.transmit_later(src, packet, delay_s=0.0)

    def send_data_on_path(self, src: int, dst: int, flow_id: int, path: Tuple[int, ...]) -> None:
        if len(path) < 2:
            return
        packet = Packet(
            kind="DATA",
            flow_id=flow_id,
            origin=src,
            final_dst=dst,
            ttl=self.sim.max_hops,
            created_at=self.sim.metrics.flows[flow_id].created_at,
            protocol=self.name,
            path=path,
            path_index=0,
        )
        self.sim.transmit_later(src, packet, delay_s=0.0)

    def flood_delay(self) -> float:
        return self.flood_base_delay_s + self.sim.random.random() * self.flood_jitter_s

    def on_receive(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if packet.kind == "RREQ":
            self.on_rreq(receiver, packet)
        elif packet.kind == "RREP":
            self.on_rrep(receiver, packet)
        elif packet.kind == "DATA":
            self.on_data(receiver, packet)

    def on_rreq(self, receiver: int, packet: Packet) -> None:
        if receiver in packet.path:
            return
        key = (packet.origin, packet.final_dst, packet.request_id)
        if key in self.seen_rreq[receiver]:
            self.sim.metrics.duplicate_rx += 1
            return
        self.seen_rreq[receiver].add(key)

        new_path = packet.path + (receiver,)
        if receiver == packet.final_dst:
            # Reply from destination back to source on the reverse path.
            reverse_path = tuple(reversed(new_path))
            reply = Packet(
                kind="RREP",
                flow_id=packet.flow_id,
                origin=receiver,
                final_dst=packet.origin,
                ttl=self.sim.max_hops,
                created_at=self.sim.now,
                protocol=self.name,
                request_id=packet.request_id,
                path=reverse_path,
                path_index=0,
                learned_path=new_path,
                app_payload=False,
            )
            self.sim.transmit_later(receiver, reply, delay_s=0.0)
            return

        node = self.sim.nodes[receiver]
        if packet.ttl <= 1 or not node.can_relay:
            return
        forwarded = Packet(
            kind="RREQ",
            flow_id=packet.flow_id,
            origin=packet.origin,
            final_dst=packet.final_dst,
            ttl=packet.ttl - 1,
            created_at=packet.created_at,
            protocol=self.name,
            request_id=packet.request_id,
            path=new_path,
            app_payload=False,
        )
        self.sim.transmit_later(receiver, forwarded, delay_s=self.flood_delay())

    def path_next_hop_matches(self, receiver: int, packet: Packet) -> bool:
        next_index = packet.path_index + 1
        return next_index < len(packet.path) and packet.path[next_index] == receiver

    def on_rrep(self, receiver: int, packet: Packet) -> None:
        if not self.path_next_hop_matches(receiver, packet):
            return
        advanced = packet.advance_path()
        if receiver == packet.final_dst:
            learned = packet.learned_path
            dst = learned[-1]
            self.route_cache[receiver][dst] = (self.sim.now + self.route_ttl_s, learned)
            queued = self.pending_data.pop((receiver, dst), [])
            for flow_id in queued:
                self.send_data_on_path(receiver, dst, flow_id, learned)
            return
        self.sim.transmit_later(receiver, advanced, delay_s=0.0)

    def on_data(self, receiver: int, packet: Packet) -> None:
        if packet.final_dst == BROADCAST_DST:
            # Broadcast fallback for group traffic, managed as a simple flood.
            key = (packet.origin, packet.flow_id, packet.request_id)
            if key in self.seen_rreq[receiver]:
                self.sim.metrics.duplicate_rx += 1
                return
            self.seen_rreq[receiver].add(key)
            self.sim.mark_delivered(packet.flow_id, receiver, packet)
            node = self.sim.nodes[receiver]
            if packet.ttl > 1 and node.can_relay:
                self.sim.transmit_later(receiver, packet.with_ttl(packet.ttl - 1), self.flood_delay())
            return

        if not self.path_next_hop_matches(receiver, packet):
            return
        advanced = packet.advance_path()
        if receiver == packet.final_dst:
            self.sim.mark_delivered(packet.flow_id, receiver, packet)
            return
        self.sim.transmit_later(receiver, advanced, delay_s=0.0)


class CalmMesh(RoutingProtocol):
    """Confidence-aware adaptive routing for LoRa Mesh.

    CALM treats redundancy as a controlled resource. It selects cached source
    routes by estimated path confidence, then adds bounded fallback forwarding
    only when a path is not confident enough for pure source routing.
    """

    name = "calm-mesh"

    def __init__(
        self,
        route_ttl_s: float = 600.0,
        discovery_window_s: float = 2.0,
        flood_base_delay_s: float = 0.45,
        flood_jitter_s: float = 0.65,
        fallback_ttl: int = 2,
        fallback_confidence_threshold: float = 0.0,
        fallback_delay_margin_s: float = 0.6,
        hop_penalty_per_hop: float = 0.025,
        route_age_penalty: float = 0.1,
    ) -> None:
        self.route_ttl_s = route_ttl_s
        self.discovery_window_s = discovery_window_s
        self.flood_base_delay_s = flood_base_delay_s
        self.flood_jitter_s = flood_jitter_s
        self.fallback_ttl = fallback_ttl
        self.fallback_confidence_threshold = fallback_confidence_threshold
        self.fallback_delay_margin_s = fallback_delay_margin_s
        self.hop_penalty_per_hop = hop_penalty_per_hop
        self.route_age_penalty = route_age_penalty
        self.route_cache: Dict[int, Dict[int, RouteEntry]] = {}
        self.pending_data: Dict[Tuple[int, int], List[int]] = {}
        self.seen_floods: Dict[int, Set[Tuple[str, int, int, int]]] = {}
        self.pending_fallback: Dict[Tuple[int, Tuple[str, int, int, int]], PendingSend] = {}
        self.source_fallbacks: Dict[int, List[PendingSend]] = {}
        self.rreq_candidates: Dict[Tuple[int, int, int], List[Tuple[Tuple[int, ...], float]]] = {}
        self.rreq_timers: Set[Tuple[int, int, int]] = set()

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.route_cache = {node_id: {} for node_id in sim.nodes}
        self.pending_data = {}
        self.seen_floods = {node_id: set() for node_id in sim.nodes}
        self.pending_fallback = {}
        self.source_fallbacks = {}
        self.rreq_candidates = {}
        self.rreq_timers = set()

    def flood_delay(self, receiver: Optional[int] = None, rx: Optional[RxInfo] = None) -> float:
        delay = self.flood_base_delay_s + self.sim.random.random() * self.flood_jitter_s
        if receiver is not None and rx is not None:
            margin = rx.snr_db - required_snr_db(self.sim.radio.sf)
            weak_link_penalty = clamp((5.0 - margin) / 10.0, 0.0, 1.0) * 0.35
            repeater_discount = 0.15 if self.sim.nodes[receiver].role == "repeater" else 0.0
            delay += weak_link_penalty - repeater_discount
        return max(0.05, delay)

    def link_confidence(self, rx: RxInfo) -> float:
        margin = rx.snr_db - required_snr_db(self.sim.radio.sf)
        margin_score = 1.0 / (1.0 + math.exp(-0.7 * margin))
        collision_penalty = 0.18 if rx.collided else 0.0
        return clamp(margin_score - collision_penalty, 0.05, 0.98)

    def path_confidence(self, path: Tuple[int, ...], inbound_confidence: float) -> float:
        if len(path) < 2:
            return clamp(inbound_confidence, 0.0, 1.0)
        hop_penalty = max(0, len(path) - 2) * self.hop_penalty_per_hop
        return clamp(inbound_confidence - hop_penalty, 0.05, 0.98)

    def route_confidence(self, entry: RouteEntry) -> float:
        age = max(0.0, self.sim.now - entry.created_at)
        lifetime = max(1.0, entry.expires_at - entry.created_at)
        age_penalty = clamp(age / lifetime, 0.0, 1.0) * self.route_age_penalty
        return clamp(entry.confidence - age_penalty, 0.0, 1.0)

    def send_app(self, src: int, dst: int, flow_id: int) -> None:
        self.sim.metrics.register_flow(flow_id, src, dst, self.sim.now)
        if dst == BROADCAST_DST:
            packet = Packet(
                kind="DATA",
                flow_id=flow_id,
                origin=src,
                final_dst=dst,
                ttl=self.sim.max_hops,
                created_at=self.sim.now,
                protocol=self.name,
            )
            self.seen_floods[src].add(packet.flood_key)
            self.sim.transmit_later(src, packet, delay_s=0.0)
            return

        entry = self.get_route(src, dst)
        if entry is not None:
            self.sim.metrics.route_cache_hits += 1
            self.send_data_on_path(src, dst, flow_id, entry)
            return

        self.sim.metrics.route_cache_misses += 1
        self.pending_data.setdefault((src, dst), []).append(flow_id)
        if len(self.pending_data[(src, dst)]) == 1:
            self.start_route_discovery(src, dst, flow_id)

    def get_route(self, src: int, dst: int) -> Optional[RouteEntry]:
        entry = self.route_cache[src].get(dst)
        if entry is None:
            return None
        if entry.expires_at <= self.sim.now:
            del self.route_cache[src][dst]
            self.sim.metrics.route_repair_count += 1
            return None
        return entry

    def start_route_discovery(self, src: int, dst: int, flow_id: int) -> None:
        request_id = flow_id
        key = (src, dst, request_id)
        self.rreq_candidates[key] = []
        packet = Packet(
            kind="RREQ",
            flow_id=flow_id,
            origin=src,
            final_dst=dst,
            ttl=self.sim.max_hops,
            created_at=self.sim.now,
            protocol=self.name,
            request_id=request_id,
            path=(src,),
            path_confidence=1.0,
            app_payload=False,
        )
        self.seen_floods[src].add(packet.flood_key)
        self.sim.transmit_later(src, packet, delay_s=0.0)
        if key not in self.rreq_timers:
            self.rreq_timers.add(key)
            self.sim.schedule(
                self.sim.now + self.discovery_window_s,
                "protocol_timer",
                lambda key=key: self.finish_route_discovery(key),
            )

    def finish_route_discovery(self, key: Tuple[int, int, int]) -> None:
        self.rreq_timers.discard(key)
        candidates = self.rreq_candidates.pop(key, [])
        if not candidates:
            self.finish_failed_route_discovery(key)
            return
        src, dst, request_id = key
        path, confidence = max(candidates, key=lambda item: (item[1], -len(item[0])))
        reverse_path = tuple(reversed(path))
        reply = Packet(
            kind="RREP",
            flow_id=request_id,
            origin=dst,
            final_dst=src,
            ttl=self.sim.max_hops,
            created_at=self.sim.now,
            protocol=self.name,
            request_id=request_id,
            path=reverse_path,
            path_index=0,
            learned_path=path,
            path_confidence=confidence,
            app_payload=False,
        )
        self.sim.transmit_later(dst, reply, delay_s=0.0)
        self.sim.metrics.record_path_confidence(confidence)

    def route_miss_recovery_ttl(self) -> int:
        return self.sim.max_hops

    def finish_failed_route_discovery(self, key: Tuple[int, int, int]) -> None:
        src, dst, _ = key
        queued = self.pending_data.pop((src, dst), [])
        for flow_id in queued:
            self.sim.metrics.route_repair_count += 1
            self.start_fallback(
                src,
                dst,
                flow_id,
                ttl=self.route_miss_recovery_ttl(),
                delay_s=0.0,
            )

    def send_data_on_path(self, src: int, dst: int, flow_id: int, entry: RouteEntry) -> None:
        if len(entry.path) < 2:
            return
        confidence = self.route_confidence(entry)
        packet = Packet(
            kind="DATA",
            flow_id=flow_id,
            origin=src,
            final_dst=dst,
            ttl=self.sim.max_hops,
            created_at=self.sim.metrics.flows[flow_id].created_at,
            protocol=self.name,
            path=entry.path,
            path_index=0,
        )
        self.sim.transmit_later(src, packet, delay_s=0.0)
        self.sim.metrics.record_path_confidence(confidence)
        if confidence < self.fallback_confidence_threshold:
            fallback_delay = (
                self.sim.radio.toa_s * min(max(len(entry.path) - 1, 1), 4)
                + self.fallback_delay_margin_s
            )
            self.start_fallback(src, dst, flow_id, ttl=self.fallback_ttl, delay_s=fallback_delay)

    def start_fallback(self, src: int, dst: int, flow_id: int, ttl: int, delay_s: float) -> None:
        fallback = Packet(
            kind="FALLBACK",
            flow_id=flow_id,
            origin=src,
            final_dst=dst,
            ttl=ttl,
            created_at=self.sim.metrics.flows[flow_id].created_at,
            protocol=self.name,
        )
        self.seen_floods[src].add(fallback.flood_key)
        pending = self.sim.transmit_later(src, fallback, delay_s=delay_s)
        if delay_s > 0.0:
            self.source_fallbacks.setdefault(flow_id, []).append(pending)

    def on_delivery(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        pending_fallbacks = self.source_fallbacks.pop(flow_id, [])
        for pending in pending_fallbacks:
            pending.canceled = True

    def path_next_hop_matches(self, receiver: int, packet: Packet) -> bool:
        next_index = packet.path_index + 1
        return next_index < len(packet.path) and packet.path[next_index] == receiver

    def on_receive(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if packet.kind == "RREQ":
            self.on_rreq(receiver, packet, rx)
        elif packet.kind == "RREP":
            self.on_rrep(receiver, packet)
        elif packet.kind == "DATA":
            self.on_data(receiver, packet, rx)
        elif packet.kind == "FALLBACK":
            self.on_fallback(receiver, packet, rx)

    def on_rreq(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if receiver in packet.path:
            return
        key = packet.flood_key
        new_path = packet.path + (receiver,)
        inherited_confidence = packet.path_confidence or 1.0
        confidence = self.path_confidence(
            new_path,
            min(inherited_confidence, self.link_confidence(rx)),
        )
        if receiver == packet.final_dst:
            request_key = (packet.origin, packet.final_dst, packet.request_id)
            self.rreq_candidates.setdefault(request_key, []).append((new_path, confidence))
            self.seen_floods[receiver].add(key)
            return

        if key in self.seen_floods[receiver]:
            self.sim.metrics.duplicate_rx += 1
            return
        self.seen_floods[receiver].add(key)

        node = self.sim.nodes[receiver]
        if packet.ttl <= 1 or not node.can_relay:
            return
        forwarded = Packet(
            kind="RREQ",
            flow_id=packet.flow_id,
            origin=packet.origin,
            final_dst=packet.final_dst,
            ttl=packet.ttl - 1,
            created_at=packet.created_at,
            protocol=self.name,
            request_id=packet.request_id,
            path=new_path,
            path_confidence=confidence,
            app_payload=False,
        )
        self.sim.transmit_later(receiver, forwarded, delay_s=self.flood_delay(receiver, rx))

    def on_rrep(self, receiver: int, packet: Packet) -> None:
        if not self.path_next_hop_matches(receiver, packet):
            return
        advanced = packet.advance_path()
        if receiver == packet.final_dst:
            learned = packet.learned_path
            dst = learned[-1]
            confidence = packet.path_confidence or clamp(1.0 - (len(learned) - 2) * 0.06, 0.25, 0.95)
            self.route_cache[receiver][dst] = RouteEntry(
                created_at=self.sim.now,
                expires_at=self.sim.now + self.route_ttl_s,
                path=learned,
                confidence=confidence,
            )
            queued = self.pending_data.pop((receiver, dst), [])
            for flow_id in queued:
                entry = self.route_cache[receiver][dst]
                self.send_data_on_path(receiver, dst, flow_id, entry)
            return
        self.sim.transmit_later(receiver, advanced, delay_s=0.0)

    def on_data(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if packet.final_dst == BROADCAST_DST:
            self.on_fallback(receiver, packet, rx)
            return

        if not self.path_next_hop_matches(receiver, packet):
            return
        advanced = packet.advance_path()
        if receiver == packet.final_dst:
            self.sim.mark_delivered(packet.flow_id, receiver, packet)
            return
        self.sim.transmit_later(receiver, advanced, delay_s=0.0)

    def on_fallback(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        key = packet.flood_key
        pending_key = (receiver, key)
        if key in self.seen_floods[receiver]:
            pending = self.pending_fallback.get(pending_key)
            if pending is not None and not pending.canceled:
                pending.canceled = True
                self.sim.metrics.suppressed_forwards += 1
            self.sim.metrics.duplicate_rx += 1
            return
        self.seen_floods[receiver].add(key)

        if packet.final_dst == BROADCAST_DST or packet.final_dst == receiver:
            self.sim.mark_delivered(packet.flow_id, receiver, packet)

        node = self.sim.nodes[receiver]
        if packet.ttl <= 1 or not node.can_relay:
            return
        if packet.final_dst != BROADCAST_DST and packet.final_dst == receiver:
            return

        forwarded = packet.with_ttl(packet.ttl - 1)
        pending = self.sim.transmit_later(receiver, forwarded, delay_s=self.flood_delay(receiver, rx))
        self.pending_fallback[pending_key] = pending


class SmartCalmMesh(CalmMesh):
    """MCU-friendly online-learning CALM variant.

    The controller is intentionally small: it learns among a few prevalidated
    parameter profiles instead of running an expensive neural policy. That makes
    the design realistic for firmware while still allowing nodes to adapt after
    deployment.
    """

    name = "smart-calm"

    DEFAULT_PROFILES = (
        AdaptiveProfile(
            name="lean",
            route_ttl_s=900.0,
            discovery_window_s=2.0,
            fallback_confidence_threshold=0.0,
            fallback_ttl=1,
            fallback_delay_margin_s=0.6,
            hop_penalty_per_hop=0.02,
            route_age_penalty=0.08,
        ),
        AdaptiveProfile(
            name="balanced",
            route_ttl_s=600.0,
            discovery_window_s=2.0,
            fallback_confidence_threshold=0.0,
            fallback_ttl=2,
            fallback_delay_margin_s=0.6,
            hop_penalty_per_hop=0.025,
            route_age_penalty=0.1,
        ),
        AdaptiveProfile(
            name="rescue",
            route_ttl_s=360.0,
            discovery_window_s=2.8,
            fallback_confidence_threshold=0.9,
            fallback_ttl=3,
            fallback_delay_margin_s=0.9,
            hop_penalty_per_hop=0.04,
            route_age_penalty=0.18,
        ),
    )

    @classmethod
    def profiles_from_base_parameters(
        cls,
        route_ttl_s: float,
        discovery_window_s: float,
        fallback_confidence_threshold: float,
        fallback_ttl: int,
        fallback_delay_margin_s: float,
        hop_penalty_per_hop: float,
        route_age_penalty: float,
    ) -> Tuple[AdaptiveProfile, ...]:
        """Build learning profiles around the user-provided CALM baseline."""

        return (
            AdaptiveProfile(
                name="lean",
                route_ttl_s=route_ttl_s * 1.5,
                discovery_window_s=max(0.1, discovery_window_s - 0.4),
                fallback_confidence_threshold=max(0.0, fallback_confidence_threshold - 0.15),
                fallback_ttl=max(1, fallback_ttl - 1),
                fallback_delay_margin_s=fallback_delay_margin_s,
                hop_penalty_per_hop=max(0.0, hop_penalty_per_hop * 0.8),
                route_age_penalty=max(0.0, route_age_penalty * 0.8),
            ),
            AdaptiveProfile(
                name="balanced",
                route_ttl_s=route_ttl_s,
                discovery_window_s=discovery_window_s,
                fallback_confidence_threshold=fallback_confidence_threshold,
                fallback_ttl=fallback_ttl,
                fallback_delay_margin_s=fallback_delay_margin_s,
                hop_penalty_per_hop=hop_penalty_per_hop,
                route_age_penalty=route_age_penalty,
            ),
            AdaptiveProfile(
                name="rescue",
                route_ttl_s=max(1.0, route_ttl_s * 0.6),
                discovery_window_s=discovery_window_s + 0.4,
                fallback_confidence_threshold=max(0.9, fallback_confidence_threshold),
                fallback_ttl=fallback_ttl + 1,
                fallback_delay_margin_s=fallback_delay_margin_s + 0.3,
                hop_penalty_per_hop=hop_penalty_per_hop * 1.6,
                route_age_penalty=route_age_penalty * 1.8,
            ),
        )

    def __init__(
        self,
        update_interval_s: float = 30.0,
        learning_rate: float = 0.45,
        discount: float = 0.75,
        exploration: float = 0.02,
        flow_timeout_s: float = 35.0,
        max_timeout_retries: int = 2,
        retry_after_fallback: bool = False,
        route_miss_fallback_ttl: int = 0,
        prior_q_values: Optional[Dict[Tuple[int, int], float]] = None,
        profiles: Sequence[AdaptiveProfile] = DEFAULT_PROFILES,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.update_interval_s = update_interval_s
        self.learning_rate = learning_rate
        self.discount = discount
        self.exploration = exploration
        self.flow_timeout_s = flow_timeout_s
        self.max_timeout_retries = max_timeout_retries
        self.retry_after_fallback = retry_after_fallback
        self.route_miss_fallback_ttl = route_miss_fallback_ttl
        self.profiles = tuple(profiles)
        self.active_profile_index = 1 if len(self.profiles) > 1 else 0
        self.active_state_index = 0
        self.q_values: Dict[Tuple[int, int], float] = {}
        self.last_snapshot: Optional[LearningSnapshot] = None
        self.flow_decisions: Dict[int, FlowDecision] = {}
        self.prior_q_values: Dict[Tuple[int, int], float] = dict(prior_q_values or {})
        self.fallback_pressure_ewma = 0.0
        self.fallback_controller_state = 0
        self.apply_profile(self.active_profile_index)

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.active_profile_index = min(self.active_profile_index, len(self.profiles) - 1)
        self.apply_profile(self.active_profile_index)
        self.active_state_index = 0
        self.q_values = dict(self.prior_q_values)
        self.last_snapshot = sim.metrics.snapshot()
        self.flow_decisions = {}
        self.fallback_pressure_ewma = 0.0
        self.fallback_controller_state = 0
        sim.metrics.active_profile_index = self.active_profile_index
        sim.schedule(
            sim.now + self.update_interval_s,
            "protocol_timer",
            self.learning_tick,
        )

    def apply_profile(self, index: int) -> None:
        profile = self.profiles[index]
        self.route_ttl_s = profile.route_ttl_s
        self.discovery_window_s = profile.discovery_window_s
        self.fallback_confidence_threshold = profile.fallback_confidence_threshold
        self.fallback_ttl = profile.fallback_ttl
        self.fallback_delay_margin_s = profile.fallback_delay_margin_s
        self.hop_penalty_per_hop = profile.hop_penalty_per_hop
        self.route_age_penalty = profile.route_age_penalty

    def state_index_from_snapshot(self, snapshot: LearningSnapshot) -> int:
        attempts = max(1, snapshot.unicast_flows)
        delivered = snapshot.unicast_deliveries
        pdr = delivered / attempts
        route_attempts = snapshot.route_cache_hits + snapshot.route_cache_misses
        miss_ratio = snapshot.route_cache_misses / max(1, route_attempts)
        collision_per_tx = snapshot.collision_fail / max(1, snapshot.tx_count)

        if pdr < 0.65 or miss_ratio > 0.45:
            reliability_bucket = 0
        elif pdr < 0.85 or miss_ratio > 0.25:
            reliability_bucket = 1
        else:
            reliability_bucket = 2

        congestion_bucket = 1 if collision_per_tx > 18.0 else 0
        return reliability_bucket * 2 + congestion_bucket

    def learning_tick(self) -> None:
        current = self.sim.metrics.snapshot()
        previous = self.last_snapshot or current
        reward = self.window_reward(previous, current)
        new_state = self.state_index_from_snapshot(current)
        old_key = (self.active_state_index, self.active_profile_index)
        old_value = self.q_values.get(old_key, 0.0)
        best_next = max(
            self.q_values.get((new_state, action_index), 0.0)
            for action_index in range(len(self.profiles))
        )
        updated = old_value + self.learning_rate * (
            reward + self.discount * best_next - old_value
        )
        self.q_values[old_key] = updated
        self.sim.metrics.policy_update_count += 1
        self.sim.metrics.policy_reward_total += reward
        self.active_state_index = new_state
        next_action = self.select_action(new_state)
        if next_action != self.active_profile_index:
            self.sim.metrics.policy_switch_count += 1
        self.active_profile_index = next_action
        self.apply_profile(next_action)
        self.sim.metrics.active_profile_index = self.active_profile_index
        self.last_snapshot = current
        self.sim.schedule(
            self.sim.now + self.update_interval_s,
            "protocol_timer",
            self.learning_tick,
        )

    def window_reward(self, previous: LearningSnapshot, current: LearningSnapshot) -> float:
        new_unicast = current.unicast_flows - previous.unicast_flows
        new_broadcast = current.broadcast_flows - previous.broadcast_flows
        new_unicast_deliveries = current.unicast_deliveries - previous.unicast_deliveries
        new_broadcast_deliveries = current.broadcast_deliveries - previous.broadcast_deliveries
        new_tx = current.tx_count - previous.tx_count
        new_control = current.control_tx - previous.control_tx
        new_collisions = current.collision_fail - previous.collision_fail
        new_repairs = current.route_repair_count - previous.route_repair_count
        new_fallback = current.fallback_forward_count - previous.fallback_forward_count
        new_delay_total = current.delivery_delay_total_s - previous.delivery_delay_total_s
        new_delay_samples = current.delivery_delay_samples - previous.delivery_delay_samples

        unicast_pdr = new_unicast_deliveries / max(1, new_unicast)
        broadcast_gain = new_broadcast_deliveries / max(1, new_broadcast * max(1, self.sim.metrics.node_count - 1))
        avg_delay = new_delay_total / max(1, new_delay_samples)
        control_ratio = new_control / max(1, new_tx)
        collision_pressure = new_collisions / max(1, new_tx)

        return (
            1.6 * unicast_pdr
            + 0.4 * broadcast_gain
            - 0.03 * avg_delay
            - 0.35 * control_ratio
            - 0.012 * collision_pressure
            - 0.05 * new_repairs
            - 0.004 * new_fallback
        )

    def select_action(self, state_index: int) -> int:
        if self.sim.random.random() < self.exploration:
            return self.sim.random.randrange(len(self.profiles))

        def score(action_index: int) -> Tuple[float, float]:
            profile_bias = {
                0: 0.015,
                1: 0.0,
                2: -0.015,
            }.get(action_index, 0.0)
            return (self.q_values.get((state_index, action_index), 0.0) + profile_bias, -action_index)

        return max(range(len(self.profiles)), key=score)

    @classmethod
    def load_prior_q_values(cls, path: Path | str) -> Dict[Tuple[int, int], float]:
        prior_path = Path(path)
        with prior_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        q_values: Dict[Tuple[int, int], float] = {}
        for item in payload.get("q_values", []):
            try:
                state = int(item["state"])
                action = int(item["action"])
                value = float(item["value"])
            except (KeyError, TypeError, ValueError):
                continue
            q_values[(state, action)] = value
        return q_values

    def send_app(self, src: int, dst: int, flow_id: int) -> None:
        if dst != BROADCAST_DST:
            state_index = self.state_index_from_snapshot(self.sim.metrics.snapshot())
            action_index = self.select_action(state_index)
            if action_index != self.active_profile_index:
                self.sim.metrics.policy_switch_count += 1
            self.active_state_index = state_index
            self.active_profile_index = action_index
            self.apply_profile(action_index)
            self.sim.metrics.active_profile_index = self.active_profile_index
            self.flow_decisions[flow_id] = FlowDecision(
                src=src,
                dst=dst,
                state_index=state_index,
                action_index=action_index,
                profile_name=self.profiles[action_index].name,
                created_at=self.sim.now,
            )
            self.sim.schedule(
                self.sim.now + self.flow_timeout_s,
                "flow_timeout",
                flow_id,
            )
        super().send_app(src, dst, flow_id)

    def start_route_discovery(self, src: int, dst: int, flow_id: int) -> None:
        decision = self.flow_decisions.get(flow_id)
        if decision is not None:
            decision.route_miss += 1
        super().start_route_discovery(src, dst, flow_id)

    def start_fallback(self, src: int, dst: int, flow_id: int, ttl: int, delay_s: float) -> None:
        decision = self.flow_decisions.get(flow_id)
        if decision is not None:
            decision.fallback_count += 1
        super().start_fallback(src, dst, flow_id, ttl, delay_s)

    def finish_route_discovery(self, key: Tuple[int, int, int]) -> None:
        candidates = self.rreq_candidates.get(key, [])
        if candidates:
            _, confidence = max(candidates, key=lambda item: (item[1], -len(item[0])))
            _, _, flow_id = key
            decision = self.flow_decisions.get(flow_id)
            if decision is not None:
                decision.confidence = confidence
        super().finish_route_discovery(key)

    def route_miss_recovery_ttl(self) -> int:
        if self.route_miss_fallback_ttl > 0:
            return self.route_miss_fallback_ttl
        return self.sim.max_hops

    def timeout_fallback_ttl(self) -> int:
        ttl = max(self.fallback_ttl, 1)
        if self.active_profile_index != len(self.profiles) - 1:
            return ttl

        controller_state = self.update_fallback_controller()
        if controller_state >= 2:
            return 1
        if controller_state == 1:
            return min(ttl, 2)
        return ttl

    def update_fallback_controller(self) -> int:
        snapshot = self.sim.metrics.snapshot()
        pressure = self.fallback_pressure_score(snapshot)
        self.fallback_pressure_ewma = max(
            pressure,
            0.7 * self.fallback_pressure_ewma + 0.3 * pressure,
        )
        guard_state = self.fallback_pressure_guard_state(snapshot)

        if guard_state >= 2 or pressure >= 0.78:
            self.fallback_controller_state = 2
        elif self.fallback_controller_state >= 2:
            if self.fallback_pressure_ewma < 0.52:
                self.fallback_controller_state = 1
        elif self.fallback_controller_state == 1:
            if self.fallback_pressure_ewma >= 0.78:
                self.fallback_controller_state = 2
            elif self.fallback_pressure_ewma < 0.34:
                self.fallback_controller_state = 0
        elif guard_state >= 1 or self.fallback_pressure_ewma >= 0.58:
            self.fallback_controller_state = 1

        return self.fallback_controller_state

    def fallback_pressure_guard_state(self, snapshot: LearningSnapshot) -> int:
        collision_per_tx = snapshot.collision_fail / max(1, snapshot.tx_count)
        fallback_per_unicast = snapshot.fallback_forward_count / max(1, snapshot.unicast_flows)
        tx_per_min = snapshot.tx_count / max(1.0 / 60.0, self.sim.now / 60.0)

        if tx_per_min < 220.0:
            return 0
        if collision_per_tx > 23.0 and fallback_per_unicast > 2.0:
            return 2
        if collision_per_tx > 22.5 and fallback_per_unicast > 1.5:
            return 1
        return 0

    def fallback_pressure_score(self, snapshot: LearningSnapshot) -> float:
        collision_per_tx = snapshot.collision_fail / max(1, snapshot.tx_count)
        fallback_per_unicast = snapshot.fallback_forward_count / max(1, snapshot.unicast_flows)
        tx_per_min = snapshot.tx_count / max(1.0 / 60.0, self.sim.now / 60.0)
        miss_ratio = 1.0 - snapshot.unicast_deliveries / max(1, snapshot.unicast_flows)

        collision_score = clamp((collision_per_tx - 18.0) / 8.0, 0.0, 1.0)
        fallback_score = clamp((fallback_per_unicast - 1.0) / 3.0, 0.0, 1.0)
        load_score = clamp((tx_per_min - 180.0) / 180.0, 0.0, 1.0)
        reliability_score = clamp(miss_ratio / 0.25, 0.0, 1.0)

        return (
            0.34 * collision_score
            + 0.28 * fallback_score
            + 0.28 * load_score
            + 0.10 * reliability_score
        )

    def send_data_on_path(self, src: int, dst: int, flow_id: int, entry: RouteEntry) -> None:
        decision = self.flow_decisions.get(flow_id)
        if decision is not None:
            decision.confidence = max(decision.confidence, self.route_confidence(entry))
        super().send_data_on_path(src, dst, flow_id, entry)

    def retry_data_on_cached_path(self, decision: FlowDecision, flow_id: int) -> bool:
        entry = self.get_route(decision.src, decision.dst)
        if entry is None or len(entry.path) < 2:
            return False
        confidence = self.route_confidence(entry)
        packet = Packet(
            kind="DATA",
            flow_id=flow_id,
            origin=decision.src,
            final_dst=decision.dst,
            ttl=self.sim.max_hops,
            created_at=self.sim.metrics.flows[flow_id].created_at,
            protocol=self.name,
            path=entry.path,
            path_index=0,
        )
        decision.confidence = max(decision.confidence, confidence)
        self.sim.metrics.record_path_confidence(confidence)
        self.sim.transmit_later(decision.src, packet, delay_s=0.0)
        return True

    def on_delivery(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        super().on_delivery(flow_id, receiver, now, packet)
        decision = self.flow_decisions.get(flow_id)
        if decision is None or decision.delivered:
            return
        decision.delivered = True
        decision.delivered_at = now
        self.learn_from_flow(decision, delivered=True, now=now)
        self.flow_decisions.pop(flow_id, None)

    def on_flow_completion(self, flow_id: int, delivered: bool, now: float) -> None:
        decision = self.flow_decisions.get(flow_id)
        if decision is None or decision.delivered:
            return
        can_retry_timeout = (
            not delivered
            and decision.timeout_retries < self.max_timeout_retries
            and (self.retry_after_fallback or decision.fallback_count == 0)
        )
        if can_retry_timeout:
            decision.timeout_retries += 1
            if not self.retry_data_on_cached_path(decision, flow_id):
                retry_ttl = self.timeout_fallback_ttl()
                self.start_fallback(
                    decision.src,
                    decision.dst,
                    flow_id,
                    ttl=retry_ttl,
                    delay_s=0.0,
                )
            self.sim.schedule(now + self.flow_timeout_s, "flow_timeout", flow_id)
            return
        self.learn_from_flow(decision, delivered=delivered, now=now)
        self.flow_decisions.pop(flow_id, None)

    def learn_from_flow(self, decision: FlowDecision, delivered: bool, now: float) -> None:
        latency = max(0.0, (decision.delivered_at or now) - decision.created_at)
        reward = (
            (1.0 if delivered else -0.8)
            - 0.02 * latency
            - 0.08 * decision.route_miss
            - 0.035 * decision.fallback_count
            + 0.08 * decision.confidence
        )
        state = self.state_index_from_snapshot(self.sim.metrics.snapshot())
        key = (decision.state_index, decision.action_index)
        old_value = self.q_values.get(key, 0.0)
        best_next = max(
            self.q_values.get((state, action_index), 0.0)
            for action_index in range(len(self.profiles))
        )
        self.q_values[key] = old_value + self.learning_rate * (
            reward + self.discount * best_next - old_value
        )
        self.sim.metrics.policy_update_count += 1
        self.sim.metrics.policy_reward_total += reward


def generate_nodes(
    count: int,
    area_m: float,
    rng: random.Random,
    repeater_ratio: float = 0.0,
) -> List[Node]:
    nodes = []
    for node_id in range(count):
        role = "repeater" if rng.random() < repeater_ratio else "router"
        nodes.append(Node(node_id, rng.random() * area_m, rng.random() * area_m, role=role))
    return nodes


def schedule_traffic(
    sim: Simulator,
    duration_s: float,
    rate_per_min: float,
    traffic: str,
    rng: random.Random,
    pair_count: int,
) -> None:
    node_ids = list(sim.nodes)
    fixed_pairs: List[Tuple[int, int]] = []
    if traffic in {"unicast", "mixed"} and pair_count > 0:
        attempts = 0
        while len(fixed_pairs) < pair_count and attempts < pair_count * 20:
            attempts += 1
            src = rng.choice(node_ids)
            dst = rng.choice([node_id for node_id in node_ids if node_id != src])
            pair = (src, dst)
            if pair not in fixed_pairs:
                fixed_pairs.append(pair)

    flow_id = 1
    t = 1.0
    mean_interval = 60.0 / rate_per_min if rate_per_min > 0 else duration_s
    while t < duration_s:
        src = rng.choice(node_ids)
        if traffic == "broadcast":
            dst = BROADCAST_DST
        elif traffic == "mixed" and rng.random() < 0.5:
            dst = BROADCAST_DST
        elif fixed_pairs:
            src, dst = rng.choice(fixed_pairs)
        else:
            dst = rng.choice([node_id for node_id in node_ids if node_id != src])
        sim.schedule(t, "app_send", (src, dst, flow_id))
        flow_id += 1
        t += rng.expovariate(1.0 / mean_interval)


def build_protocol(name: str, args: Optional[argparse.Namespace] = None) -> RoutingProtocol:
    if name == "meshtastic":
        return MeshtasticLike()
    if name == "meshcore":
        return MeshCoreLike()
    if name == "calm":
        if args is None:
            return CalmMesh()
        return CalmMesh(
            route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
            discovery_window_s=getattr(args, "calm_discovery_window_s", DEFAULT_CALM_DISCOVERY_WINDOW_S),
            flood_base_delay_s=getattr(args, "calm_flood_base_delay_s", 0.45),
            flood_jitter_s=getattr(args, "calm_flood_jitter_s", 0.65),
            fallback_ttl=getattr(args, "calm_fallback_ttl", 2),
            fallback_confidence_threshold=getattr(args, "calm_fallback_confidence_threshold", 0.0),
            fallback_delay_margin_s=getattr(args, "calm_fallback_delay_margin_s", 0.6),
            hop_penalty_per_hop=getattr(args, "calm_hop_penalty_per_hop", 0.025),
            route_age_penalty=getattr(args, "calm_route_age_penalty", 0.1),
        )
    if name == "smart-calm":
        if args is None:
            return SmartCalmMesh()
        profiles = SmartCalmMesh.profiles_from_base_parameters(
            route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
            discovery_window_s=getattr(args, "calm_discovery_window_s", DEFAULT_CALM_DISCOVERY_WINDOW_S),
            fallback_confidence_threshold=getattr(args, "calm_fallback_confidence_threshold", 0.0),
            fallback_ttl=getattr(args, "calm_fallback_ttl", 2),
            fallback_delay_margin_s=getattr(args, "calm_fallback_delay_margin_s", 0.6),
            hop_penalty_per_hop=getattr(args, "calm_hop_penalty_per_hop", 0.025),
            route_age_penalty=getattr(args, "calm_route_age_penalty", 0.1),
        )
        return SmartCalmMesh(
            update_interval_s=getattr(args, "smart_update_interval_s", 30.0),
            learning_rate=getattr(args, "smart_learning_rate", 0.45),
            exploration=getattr(args, "smart_exploration", 0.02),
            flow_timeout_s=getattr(args, "smart_flow_timeout_s", 35.0),
            max_timeout_retries=getattr(args, "smart_max_timeout_retries", 2),
            retry_after_fallback=getattr(args, "smart_retry_after_fallback", False),
            route_miss_fallback_ttl=getattr(args, "smart_route_miss_fallback_ttl", 0),
            prior_q_values=SmartCalmMesh.load_prior_q_values(getattr(args, "smart_prior_json"))
            if getattr(args, "smart_prior_json", None)
            else None,
            flood_base_delay_s=getattr(args, "calm_flood_base_delay_s", 0.45),
            flood_jitter_s=getattr(args, "calm_flood_jitter_s", 0.65),
            profiles=profiles,
        )
    raise ValueError(f"unknown protocol: {name}")


def run_one(args: argparse.Namespace, protocol_name: str, seed: int) -> Dict[str, Any]:
    topology_rng = random.Random(seed)
    nodes = generate_nodes(args.nodes, args.area_m, topology_rng, args.repeater_ratio)
    radio = RadioConfig(
        sf=args.sf,
        bw_hz=args.bw_hz,
        cr=args.cr,
        payload_bytes=args.payload_bytes,
        tx_power_dbm=args.tx_power_dbm,
        path_loss_exp=args.path_loss_exp,
        shadow_sigma_db=args.shadow_sigma_db,
        capture_threshold_db=args.capture_threshold_db,
    )
    protocol = build_protocol(protocol_name, args)
    sim = Simulator(nodes, radio, protocol, seed=seed, max_hops=args.max_hops)
    traffic_rng = random.Random(seed + 10_000)
    schedule_traffic(
        sim,
        args.duration_s,
        args.rate_per_min,
        args.traffic,
        traffic_rng,
        args.pair_count,
    )
    metrics = sim.run(args.duration_s)
    return metrics.summarize(protocol.name, seed, args.duration_s)


def print_table(rows: Sequence[Dict[str, Any]]) -> None:
    if not rows:
        return
    columns = [
        "protocol",
        "seed",
        "flows",
        "unicast_pdr",
        "broadcast_coverage",
        "avg_delay_s",
        "mean_delivery_delay_s",
        "tx_count",
        "data_tx",
        "control_tx",
        "total_airtime_s",
        "airtime_per_delivery_s",
        "collision_fail",
        "duplicate_rx",
        "suppressed_forwards",
        "route_cache_hits",
        "route_cache_misses",
        "fallback_forward_count",
        "route_repair_count",
        "mean_path_confidence",
        "control_overhead_ratio",
        "policy_switch_count",
        "policy_update_count",
        "policy_reward_total",
        "active_profile_index",
    ]
    widths = {
        col: max(len(col), *(len(str(row[col])) for row in rows))
        for col in columns
    }
    header = "  ".join(col.ljust(widths[col]) for col in columns)
    print(header)
    print("-" * len(header))
    for row in rows:
        print("  ".join(str(row[col]).ljust(widths[col]) for col in columns))


def write_csv(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LoRa mesh routing simulator")
    parser.add_argument(
        "--protocol",
        choices=["meshtastic", "meshcore", "calm", "smart-calm", "both", "all", "all4"],
        default="both",
    )
    parser.add_argument("--nodes", type=int, default=40)
    parser.add_argument("--area-m", type=float, default=2500.0)
    parser.add_argument("--duration-s", type=float, default=1800.0)
    parser.add_argument("--rate-per-min", type=float, default=8.0)
    parser.add_argument("--traffic", choices=["unicast", "broadcast", "mixed"], default="unicast")
    parser.add_argument(
        "--pair-count",
        type=int,
        default=0,
        help="reuse this many fixed unicast source/destination pairs; useful for MeshCore-style route caching",
    )
    parser.add_argument("--seeds", type=int, default=3, help="number of repeated random seeds")
    parser.add_argument("--seed0", type=int, default=1)
    parser.add_argument("--max-hops", type=int, default=7)
    parser.add_argument("--repeater-ratio", type=float, default=0.0)

    parser.add_argument("--sf", type=int, default=9)
    parser.add_argument("--bw-hz", type=int, default=125_000)
    parser.add_argument("--cr", type=int, default=1)
    parser.add_argument("--payload-bytes", type=int, default=32)
    parser.add_argument("--tx-power-dbm", type=float, default=17.0)
    parser.add_argument("--path-loss-exp", type=float, default=2.7)
    parser.add_argument("--shadow-sigma-db", type=float, default=4.0)
    parser.add_argument("--capture-threshold-db", type=float, default=6.0)
    parser.add_argument("--calm-route-ttl-s", type=float, default=600.0)
    parser.add_argument("--calm-discovery-window-s", type=float, default=2.0)
    parser.add_argument("--calm-flood-base-delay-s", type=float, default=0.45)
    parser.add_argument("--calm-flood-jitter-s", type=float, default=0.65)
    parser.add_argument("--calm-fallback-ttl", type=int, default=2)
    parser.add_argument("--calm-fallback-confidence-threshold", type=float, default=0.0)
    parser.add_argument("--calm-fallback-delay-margin-s", type=float, default=0.6)
    parser.add_argument("--calm-hop-penalty-per-hop", type=float, default=0.025)
    parser.add_argument("--calm-route-age-penalty", type=float, default=0.1)
    parser.add_argument("--smart-update-interval-s", type=float, default=30.0)
    parser.add_argument("--smart-learning-rate", type=float, default=0.45)
    parser.add_argument("--smart-exploration", type=float, default=0.02)
    parser.add_argument("--smart-flow-timeout-s", type=float, default=35.0)
    parser.add_argument("--smart-max-timeout-retries", type=int, default=2)
    parser.add_argument(
        "--smart-route-miss-fallback-ttl",
        type=int,
        default=0,
        help="limit route-miss fallback radius; 0 keeps the normal max-hops route-discovery recovery",
    )
    parser.add_argument(
        "--smart-retry-after-fallback",
        action="store_true",
        help="allow Smart-CALM to send a timeout retry even after the flow already used fallback",
    )
    parser.add_argument("--smart-prior-json", type=Path)
    parser.add_argument("--csv", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.protocol == "both":
        protocols = ["meshtastic", "meshcore"]
    elif args.protocol == "all":
        protocols = ["meshtastic", "meshcore", "calm"]
    elif args.protocol == "all4":
        protocols = ["meshtastic", "meshcore", "calm", "smart-calm"]
    else:
        protocols = [args.protocol]
    rows = []
    for i in range(args.seeds):
        seed = args.seed0 + i
        for protocol in protocols:
            rows.append(run_one(args, protocol, seed))
    print_table(rows)
    if args.csv:
        write_csv(args.csv, rows)
        print(f"\nWrote {args.csv}")


if __name__ == "__main__":
    main()
