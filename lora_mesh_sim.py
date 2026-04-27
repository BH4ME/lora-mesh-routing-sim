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
import heapq
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple


BROADCAST_DST = -1


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


class Metrics:
    def __init__(self, node_count: int) -> None:
        self.node_count = node_count
        self.flows: Dict[int, FlowRecord] = {}
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

    def register_flow(self, flow_id: int, src: int, dst: int, now: float) -> None:
        self.flows[flow_id] = FlowRecord(flow_id, src, dst, now)

    def mark_delivered(self, flow_id: int, receiver: int, now: float) -> None:
        flow = self.flows.get(flow_id)
        if flow is None:
            return
        if flow.dst == BROADCAST_DST:
            if receiver != flow.src:
                flow.broadcast_receivers.add(receiver)
        elif receiver == flow.dst and flow.delivered_at is None:
            flow.delivered_at = now

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
            "tx_count": self.tx_count,
            "data_tx": self.data_tx,
            "control_tx": self.control_tx,
            "total_airtime_s": round(self.total_airtime_s, 6),
            "airtime_per_delivery_s": round(airtime_per_delivery, 6),
            "rx_success": self.rx_success,
            "rx_fail": self.rx_fail,
            "collision_fail": self.collision_fail,
            "duplicate_rx": self.duplicate_rx,
            "suppressed_forwards": self.suppressed_forwards,
            "route_requests": self.route_requests,
            "route_replies": self.route_replies,
            "route_cache_hits": self.route_cache_hits,
            "route_cache_misses": self.route_cache_misses,
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
            self.sim.metrics.mark_delivered(packet.flow_id, receiver, self.sim.now)

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
            self.sim.metrics.mark_delivered(packet.flow_id, receiver, self.sim.now)
            node = self.sim.nodes[receiver]
            if packet.ttl > 1 and node.can_relay:
                self.sim.transmit_later(receiver, packet.with_ttl(packet.ttl - 1), self.flood_delay())
            return

        if not self.path_next_hop_matches(receiver, packet):
            return
        advanced = packet.advance_path()
        if receiver == packet.final_dst:
            self.sim.metrics.mark_delivered(packet.flow_id, receiver, self.sim.now)
            return
        self.sim.transmit_later(receiver, advanced, delay_s=0.0)


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


def build_protocol(name: str) -> RoutingProtocol:
    if name == "meshtastic":
        return MeshtasticLike()
    if name == "meshcore":
        return MeshCoreLike()
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
    protocol = build_protocol(protocol_name)
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
    parser.add_argument("--protocol", choices=["meshtastic", "meshcore", "both"], default="both")
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
    parser.add_argument("--csv", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    protocols = ["meshtastic", "meshcore"] if args.protocol == "both" else [args.protocol]
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
