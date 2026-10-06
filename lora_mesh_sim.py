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
import struct
import zlib
from collections import OrderedDict
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from meshecho_utility import Action as UtilityAction
from meshecho_utility import UtilityObservation, choose_action
from meshecho_cpr import (
    CprAckObservation,
    CprAction,
    CprFlowRecord,
    CprObservation,
    CprPendingRelay,
    CprRelayLedger,
    choose_recovery_action,
)
from meshecho_drc import (
    DrcAction,
    DrcDecision,
    DrcSourceState,
    RecoveryState,
    RoutePhase,
    choose_start_action,
)


BROADCAST_DST = -1
DEFAULT_CALM_DISCOVERY_WINDOW_S = 2.0
DEFAULT_MESHCORE_DISCOVERY_WINDOW_S = 0.0
DEFAULT_MATCHED_MESHCORE_ROUTE_TTL_S = 600.0
MATCHED_RREQ_BASE_DELAY_S = 0.5
MATCHED_RREQ_JITTER_S = 0.7
EVENT_PRIORITY = {
    # Equal-time receive/ACK processing must happen before deadline or guard
    # timers; a source request is committed last after those observations.
    "tx_end": 0,
    "app_send": 1,
    "protocol_timer": 1,
    "flow_timeout": 1,
    "tx_request": 2,
}
ICC_PROTOCOLS = (
    "meshtastic",
    "meshcore",
    "etx",
    "ett",
    "minhop",
    "meshecho",
)

# MeshEcho is the ICC method.  These variants are deliberately kept outside
# the default ICC matrix so that component evidence cannot be mistaken for
# additional competing protocols.
MESHECHO_ABLATIONS = (
    "meshecho-no-confidence",
    "meshecho-no-fallback",
    "meshecho-no-hop-penalty",
    "meshecho-no-age-penalty",
)
SR_PROTOCOL_MODES = {
    "meshecho-sr": "sr",
    "meshecho-sr-fr": "fr",
    "meshecho-sr-trigger-f": "trigger-f",
    "meshecho-sr-periodic": "periodic",
}
MAG_PROTOCOL_MODES = {
    "meshecho-mag": "mag",
    "meshecho-mag-fr": "fr",
    "meshecho-mag-trigger-f": "trigger-f",
    "meshecho-mag-periodic": "periodic",
}
LPR_PROTOCOL_MODES = {
    "meshecho-lpr": "lpr",
    "meshecho-lpr-fr": "fr",
    "meshecho-lpr-trigger-f": "trigger-f",
    "meshecho-lpr-periodic": "periodic",
    "meshecho-lpr-unobserved-edge": "unobserved-edge",
}
UGR_PROTOCOL_MODES = {
    "meshecho-ugr": "utility",
    "meshecho-ugr-fr": "fr",
    "meshecho-ugr-trigger-f": "trigger-f",
    "meshecho-ugr-no-feedback": "no-feedback",
}
DRC_PROTOCOL_MODES = {
    "meshecho-drc": "drc",
    "meshecho-drc-no-rescue": "no-rescue",
    "meshecho-drc-fixed-guard": "fixed-guard",
    "meshecho-drc-all-f": "all-f",
    "meshecho-drc-r-only": "r-only",
}
CPR_PROTOCOL_MODES = {
    "meshecho-cpr": "cpr",
    "meshecho-cpr-nocancel": "no-cancel",
}
DRC_MAX_PENDING_FALLBACKS_PER_NODE = 128


def dbm_to_mw(dbm: float) -> float:
    return 10 ** (dbm / 10.0)


def mw_to_dbm(mw: float) -> float:
    if mw <= 0:
        return -float("inf")
    return 10.0 * math.log10(mw)


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def percentile(values: Sequence[float], quantile: float) -> float:
    """Return a linearly interpolated percentile for a finite sample."""

    if not values:
        return 0.0
    ordered = sorted(values)
    position = clamp(quantile, 0.0, 1.0) * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


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
    payload_bytes: int = 32  # Application bytes; packet headers are added per frame.
    preamble_symbols: int = 8
    explicit_header: bool = True
    crc: bool = True
    tx_power_dbm: float = 17.0
    carrier_mhz: float = 915.0
    noise_figure_db: float = 6.0
    path_loss_exp: float = 2.7
    shadow_sigma_db: float = 4.0
    temporal_fading_sigma_db: float = 0.0
    temporal_fading_interval_s: float = 60.0
    capture_threshold_db: float = 6.0
    prr_slope: float = 1.15
    tx_current_ma: float = 120.0
    rx_current_ma: float = 10.3
    supply_voltage_v: float = 3.3

    @property
    def noise_floor_dbm(self) -> float:
        return -174.0 + 10.0 * math.log10(self.bw_hz) + self.noise_figure_db

    @property
    def toa_s(self) -> float:
        """Nominal payload-only ToA retained for legacy metric scoring."""

        return self.toa_s_for_bytes(self.payload_bytes)

    def toa_s_for_bytes(self, payload_bytes: int) -> float:
        """LoRa time-on-air for a complete PHY payload of this many bytes."""

        sf = self.sf
        bw = self.bw_hz
        cr = self.cr
        de = 1 if sf >= 11 and bw <= 125_000 else 0
        ih = 0 if self.explicit_header else 1
        crc = 1 if self.crc else 0
        t_sym = (2**sf) / bw
        t_preamble = (self.preamble_symbols + 4.25) * t_sym
        numerator = 8 * payload_bytes - 4 * sf + 28 + 16 * crc - 20 * ih
        denominator = 4 * (sf - 2 * de)
        payload_symbols = 8 + max(math.ceil(numerator / denominator) * (cr + 4), 0)
        return t_preamble + payload_symbols * t_sym

    def packet_toa_s(self, packet: "Packet") -> float:
        return self.toa_s_for_bytes(packet.wire_size_bytes(self.payload_bytes))

    @property
    def tx_energy_per_packet_j(self) -> float:
        """Electrical energy consumed by one radio transmission."""

        return self.supply_voltage_v * (self.tx_current_ma / 1000.0) * self.toa_s

    @property
    def rx_energy_per_packet_j(self) -> float:
        """Electrical energy consumed while a radio listens for one packet."""

        return self.supply_voltage_v * (self.rx_current_ma / 1000.0) * self.toa_s


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
    alternate_path: Tuple[int, ...] = ()
    path_confidence: float = 0.0
    app_payload: bool = True
    min_forward_margin_q: Optional[int] = None
    min_forward_margin_hop: Optional[int] = None
    repair_index: Optional[int] = None
    backup_relay_id: Optional[int] = None
    backup_epoch_id: Optional[int] = None

    def __post_init__(self) -> None:
        if (self.backup_relay_id is not None
                and (type(self.backup_relay_id) is not int
                     or not 0 <= self.backup_relay_id < 2**16)):
            raise ValueError("backup relay ID must fit in 16 bits")
        if (self.backup_epoch_id is not None
                and (type(self.backup_epoch_id) is not int
                     or not 0 <= self.backup_epoch_id < 2**32)):
            raise ValueError("backup epoch ID must fit in 32 bits")

    @property
    def flood_key(self) -> Tuple[str, int, int, int]:
        return (self.kind, self.origin, self.flow_id, self.request_id)

    @property
    def is_control(self) -> bool:
        return self.kind in {"RREQ", "RREP", "ACK", "ACK_DONE"}

    def wire_size_bytes(self, app_payload_bytes: int) -> int:
        """Modeled wire length with 16-bit node IDs and a 32-bit flow ID.

        Timestamps and protocol names are simulator metadata, not wire fields.
        A RREP's learned path is the reverse of its forwarding path and needs
        no second copy when that relationship holds. Zero confidence denotes
        an absent optional score field; emitted score-bearing packets use
        positive values.
        """

        if app_payload_bytes < 0:
            raise ValueError("application payload length must be nonnegative")
        size = 10  # kind, TTL, flow ID, origin, destination
        if self.kind in {"RREQ", "RREP"}:
            size += 4  # request ID
        if self.path:
            size += 2 + 2 * len(self.path)  # path count, hop index, node IDs
        if self.learned_path and self.learned_path != tuple(reversed(self.path)):
            size += 1 + 2 * len(self.learned_path)
        if self.alternate_path:
            size += 1 + 2 * len(self.alternate_path)
        if self.kind in {"RREQ", "RREP"} and self.path_confidence:
            size += 1  # quantized path confidence
        if self.min_forward_margin_q is not None:
            size += 1  # quantized minimum forward-hop SNR margin
        if self.min_forward_margin_hop is not None:
            size += 1  # index of the hop that supplied the minimum margin
        if self.repair_index is not None:
            size += 1  # protocol-specific repair or ACK-copy marker
        if self.backup_relay_id is not None or self.backup_epoch_id is not None:
            size += 1  # extension-presence flags
            if self.backup_relay_id is not None:
                size += 2
            if self.backup_epoch_id is not None:
                size += 4
        if self.app_payload:
            size += app_payload_bytes
        return size

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
            alternate_path=self.alternate_path,
            path_confidence=self.path_confidence,
            app_payload=self.app_payload,
            min_forward_margin_q=self.min_forward_margin_q,
            min_forward_margin_hop=self.min_forward_margin_hop,
            repair_index=self.repair_index,
            backup_relay_id=self.backup_relay_id,
            backup_epoch_id=self.backup_epoch_id,
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
            alternate_path=self.alternate_path,
            path_confidence=self.path_confidence,
            app_payload=self.app_payload,
            min_forward_margin_q=self.min_forward_margin_q,
            min_forward_margin_hop=self.min_forward_margin_hop,
            repair_index=self.repair_index,
            backup_relay_id=self.backup_relay_id,
            backup_epoch_id=self.backup_epoch_id,
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
            alternate_path=self.alternate_path,
            path_confidence=self.path_confidence,
            app_payload=self.app_payload,
            min_forward_margin_q=self.min_forward_margin_q,
            min_forward_margin_hop=self.min_forward_margin_hop,
            repair_index=self.repair_index,
            backup_relay_id=self.backup_relay_id,
            backup_epoch_id=self.backup_epoch_id,
        )

    def retreat_path(self) -> "Packet":
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
            path_index=self.path_index - 1,
            learned_path=self.learned_path,
            alternate_path=self.alternate_path,
            path_confidence=self.path_confidence,
            app_payload=self.app_payload,
            min_forward_margin_q=self.min_forward_margin_q,
            min_forward_margin_hop=self.min_forward_margin_hop,
            repair_index=self.repair_index,
            backup_relay_id=self.backup_relay_id,
            backup_epoch_id=self.backup_epoch_id,
        )


@dataclass
class PendingSend:
    canceled: bool = False
    committed: bool = False
    can_start_at: Optional[Callable[[float], bool]] = None
    request_id: int = 0
    requested_at: Optional[float] = None


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
    tx_id: Optional[int] = None
    attempt_id: Optional[int] = None


@dataclass
class FlowRecord:
    flow_id: int
    src: int
    dst: int
    created_at: float
    delivered_at: Optional[float] = None
    acked_at: Optional[float] = None
    broadcast_receivers: Set[int] = field(default_factory=set)


@dataclass(frozen=True)
class RouteEntry:
    created_at: float
    expires_at: float
    path: Tuple[int, ...]
    confidence: float


@dataclass
class SRDestinationState:
    send_times: List[float] = field(default_factory=list)
    acked_margins_q: List[int] = field(default_factory=list)
    acked_margin_hops: List[int] = field(default_factory=list)
    last_ack_at: Optional[float] = None
    last_discovery_at: Optional[float] = None
    last_repair_at: Optional[float] = None
    pending_discovery_flow: Optional[int] = None
    consecutive_f_misses: int = 0
    consecutive_r_misses: int = 0
    had_r_miss_since_commit: bool = False
    last_commit_flow: int = 0
    last_direct_ack_flow: int = 0
    trial_path: Tuple[int, ...] = ()
    trial_from_flow: int = 0
    trial_generation: int = 0
    active_trial_flow: Optional[int] = None
    r_miss_flows: Set[int] = field(default_factory=set)
    f_miss_flows: Set[int] = field(default_factory=set)
    recent_r_flows: List[int] = field(default_factory=list)
    backup_path: Tuple[int, ...] = ()
    backup_generation: int = 0
    backup_learned_at: Optional[float] = None
    certified_backup_relay: Optional[int] = None
    certified_backup_epoch: Optional[int] = None
    certified_backup_at: Optional[float] = None
    utility_attempts: Dict[str, int] = field(default_factory=dict)
    utility_acks: Dict[str, int] = field(default_factory=dict)


@dataclass
class DHRActiveFlow:
    src: int
    dst: int
    path: Tuple[int, ...]
    created_at: float
    initial_start: float
    route_generation: int
    selected_action: Optional[str] = None
    started_marker: Optional[int] = None
    backup_path: Tuple[int, ...] = ()
    backup_started_at: Optional[float] = None
    flood_requested: bool = False


@dataclass
class AFSPendingFlood:
    packet: Packet
    pending: PendingSend
    received_at: float


@dataclass
class BARFloodWindow:
    first_at: float
    first_path: Tuple[int, ...]
    repair_index: Optional[int]
    extra_scheduled: bool = False


@dataclass
class DBRFloodWindow:
    first_at: float
    first_packet: Packet
    paths: List[Tuple[int, ...]]


@dataclass
class DCBFloodWindow:
    first_at: float
    first_packet: Packet
    paths: List[Tuple[float, Tuple[int, ...]]]


@dataclass
class DCBRelayPending:
    packet: Packet
    received_at: float
    quiet: bool = False


@dataclass(frozen=True)
class DCBActiveNomination:
    src: int
    dst: int
    relay: int
    epoch: int
    start: float
    deadline: float


@dataclass(frozen=True)
class DiscoveryRecord:
    key: Tuple[int, int, int]
    started_at: float
    closed_at: float
    candidate_paths: Tuple[Tuple[int, ...], ...]
    selected_path: Optional[Tuple[int, ...]]


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
    rx_success: int
    rx_fail: int
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
    unicast_acks: int
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
    profile: Optional[AdaptiveProfile] = None


class Metrics:
    def __init__(self, node_count: int) -> None:
        self.node_count = node_count
        self.flows: Dict[int, FlowRecord] = {}
        self.unicast_flows = 0
        self.broadcast_flows = 0
        self.unicast_deliveries = 0
        self.unicast_acks = 0
        self.broadcast_deliveries = 0
        self.delivery_delay_total_s = 0.0
        self.delivery_delay_samples = 0
        self.tx_count = 0
        self.data_tx = 0
        self.control_tx = 0
        self.ack_tx = 0
        self.total_airtime_s = 0.0
        self.channel_busy_time_s = 0.0
        self.tx_energy_j = 0.0
        self.rx_energy_j = 0.0
        self.transmission_intervals: List[Tuple[float, float]] = []
        self.rx_success = 0
        self.rx_fail = 0
        self.collision_fail = 0
        self.duplicate_rx = 0
        self.suppressed_forwards = 0
        self.route_requests = 0
        self.route_replies = 0
        self.route_discovery_attempts = 0
        self.route_discovery_successes = 0
        self.route_cache_hits = 0
        self.route_cache_misses = 0
        self.fallback_forward_count = 0
        self.route_repair_count = 0
        self.ack_timeout_invalidations = 0
        self.timeout_invalidations_after_destination_delivery = 0
        self.path_confidence_total = 0.0
        self.path_confidence_samples = 0
        self.policy_switch_count = 0
        self.policy_update_count = 0
        self.policy_reward_total = 0.0
        self.active_profile_index = -1
        self.profile_selection_counts: Dict[int, int] = {}

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

    def mark_acknowledged(self, flow_id: int, receiver: int, now: float) -> bool:
        flow = self.flows.get(flow_id)
        if (
            flow is None
            or flow.dst == BROADCAST_DST
            or receiver != flow.src
            or flow.acked_at is not None
        ):
            return False
        flow.acked_at = now
        self.unicast_acks += 1
        return True

    def record_path_confidence(self, confidence: float) -> None:
        self.path_confidence_total += clamp(confidence, 0.0, 1.0)
        self.path_confidence_samples += 1

    def record_profile_selection(self, profile_index: int) -> None:
        self.profile_selection_counts[profile_index] = (
            self.profile_selection_counts.get(profile_index, 0) + 1
        )

    def record_transmission(self, start: float, end: float) -> None:
        self.transmission_intervals.append((start, end))

    def finalize_channel_busy_time(self, duration_s: Optional[float] = None) -> None:
        if not self.transmission_intervals:
            self.channel_busy_time_s = 0.0
            return
        intervals = self.transmission_intervals
        if duration_s is not None:
            intervals = [
                (max(0.0, start), min(duration_s, end))
                for start, end in intervals
                if start < duration_s and end > 0.0
            ]
        if not intervals:
            self.channel_busy_time_s = 0.0
            return
        ordered = sorted(intervals)
        busy = 0.0
        current_start, current_end = ordered[0]
        for start, end in ordered[1:]:
            if start <= current_end:
                current_end = max(current_end, end)
            else:
                busy += current_end - current_start
                current_start, current_end = start, end
        self.channel_busy_time_s = busy + current_end - current_start

    def snapshot(self) -> LearningSnapshot:
        return LearningSnapshot(
            tx_count=self.tx_count,
            control_tx=self.control_tx,
            rx_success=self.rx_success,
            rx_fail=self.rx_fail,
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
            unicast_acks=self.unicast_acks,
            broadcast_deliveries=self.broadcast_deliveries,
            delivery_delay_total_s=self.delivery_delay_total_s,
            delivery_delay_samples=self.delivery_delay_samples,
        )

    def summarize(self, protocol: str, seed: int, duration_s: float) -> Dict[str, Any]:
        self.finalize_channel_busy_time(duration_s)
        unicast = [f for f in self.flows.values() if f.dst != BROADCAST_DST]
        broadcast = [f for f in self.flows.values() if f.dst == BROADCAST_DST]
        destination_delivered_unicast = [f for f in unicast if f.delivered_at is not None]
        acked_unicast = [f for f in unicast if f.acked_at is not None]
        destination_unicast_pdr = (
            len(destination_delivered_unicast) / len(unicast) if unicast else 0.0
        )
        unicast_pdr = len(acked_unicast) / len(unicast) if unicast else 0.0
        delays = [
            f.acked_at - f.created_at
            for f in acked_unicast
            if f.acked_at is not None
        ]
        avg_delay = sum(delays) / len(delays) if delays else 0.0
        delivery_delays = [
            f.delivered_at - f.created_at
            for f in destination_delivered_unicast
            if f.delivered_at is not None
        ]

        if broadcast:
            expected = len(broadcast) * (self.node_count - 1)
            actual = sum(len(f.broadcast_receivers) for f in broadcast)
            broadcast_coverage = actual / expected if expected else 0.0
        else:
            broadcast_coverage = 0.0

        delivered_total = len(acked_unicast) + sum(len(f.broadcast_receivers) for f in broadcast)
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
        rx_attempts = self.rx_success + self.rx_fail
        packet_reception_ratio = self.rx_success / rx_attempts if rx_attempts else 0.0
        collision_rate = self.collision_fail / rx_attempts if rx_attempts else 0.0

        return {
            "protocol": protocol,
            "seed": seed,
            "duration_s": round(duration_s, 6),
            "flows": len(self.flows),
            "unicast_flows": len(unicast),
            "broadcast_flows": len(broadcast),
            "unicast_pdr": round(unicast_pdr, 6),
            "destination_unicast_pdr": round(destination_unicast_pdr, 6),
            "broadcast_coverage": round(broadcast_coverage, 6),
            "avg_delay_s": round(avg_delay, 6),
            "unicast_delivery_delay_s": round(
                sum(delivery_delays) / len(delivery_delays)
                if delivery_delays
                else 0.0,
                6,
            ),
            "unicast_ack_delay_s": round(avg_delay, 6),
            "p95_unicast_delivery_delay_s": round(
                percentile(delivery_delays, 0.95), 6
            ),
            "p95_unicast_ack_delay_s": round(percentile(delays, 0.95), 6),
            "unicast_deliveries": self.unicast_deliveries,
            "unicast_acks": self.unicast_acks,
            "broadcast_deliveries": self.broadcast_deliveries,
            "tx_count": self.tx_count,
            "data_tx": self.data_tx,
            "control_tx": self.control_tx,
            "ack_tx": self.ack_tx,
            "total_airtime_s": round(self.total_airtime_s, 6),
            "channel_busy_time_s": round(self.channel_busy_time_s, 6),
            "channel_busy_ratio": round(
                self.channel_busy_time_s / duration_s if duration_s else 0.0,
                6,
            ),
            "tx_energy_j": round(self.tx_energy_j, 6),
            "rx_energy_j": round(self.rx_energy_j, 6),
            "total_energy_j": round(self.tx_energy_j + self.rx_energy_j, 6),
            "energy_per_delivery_j": round(
                (self.tx_energy_j + self.rx_energy_j) / delivered_total
                if delivered_total
                else 0.0,
                6,
            ),
            "airtime_per_delivery_s": round(airtime_per_delivery, 6),
            "mean_delivery_delay_s": round(mean_delivery_delay, 6),
            "rx_success": self.rx_success,
            "rx_fail": self.rx_fail,
            "rx_attempts": rx_attempts,
            "packet_reception_ratio": round(packet_reception_ratio, 6),
            "collision_fail": self.collision_fail,
            "collision_rate": round(collision_rate, 6),
            "duplicate_rx": self.duplicate_rx,
            "suppressed_forwards": self.suppressed_forwards,
            "route_requests": self.route_requests,
            "route_replies": self.route_replies,
            "route_discovery_attempts": self.route_discovery_attempts,
            "route_discovery_successes": self.route_discovery_successes,
            "route_cache_hits": self.route_cache_hits,
            "route_cache_misses": self.route_cache_misses,
            "fallback_forward_count": self.fallback_forward_count,
            "route_repair_count": self.route_repair_count,
            "ack_timeout_invalidations": self.ack_timeout_invalidations,
            "timeout_invalidations_after_destination_delivery": (
                self.timeout_invalidations_after_destination_delivery
            ),
            "mean_path_confidence": round(mean_path_confidence, 6),
            "control_overhead_ratio": round(control_overhead_ratio, 6),
            "policy_switch_count": self.policy_switch_count,
            "policy_update_count": self.policy_update_count,
            "policy_reward_total": round(self.policy_reward_total, 6),
            "active_profile_index": self.active_profile_index,
            "profile_lean_count": self.profile_selection_counts.get(0, 0),
            "profile_balanced_count": self.profile_selection_counts.get(1, 0),
            "profile_rescue_count": self.profile_selection_counts.get(2, 0),
        }


class Simulator:
    def __init__(
        self,
        nodes: Sequence[Node],
        radio: RadioConfig,
        protocol: "RoutingProtocol",
        seed: int,
        max_hops: int,
        independent_random_streams: bool = False,
        matched_rreq_timing: bool = False,
        record_rx_attempts: Optional[bool] = None,
    ) -> None:
        self.nodes = {node.node_id: node for node in nodes}
        self.radio = radio
        self.protocol = protocol
        self.seed = seed
        self.random = random.Random(seed)
        self.matched_rreq_timing = matched_rreq_timing
        # Keep legacy output reproducible by default. The split mode prevents
        # protocol-specific jitter/exploration draws from moving channel draws.
        self.channel_random = (
            random.Random(seed + 0x51ED270B)
            if independent_random_streams
            else self.random
        )
        self.max_hops = max_hops
        self.now = 0.0
        self._event_counter = 0
        self._tx_counter = 0
        self.events: List[Tuple[float, Tuple[int, int], str, Any]] = []
        self.transmissions: List[Transmission] = []
        self._request_counter = 0
        self.tx_requests: List[Dict[str, Any]] = []
        self._request_records: Dict[int, Dict[str, Any]] = {}
        self.application_events: List[Dict[str, Any]] = []
        self._application_counter = 0
        self._current_application_ordinal: Optional[int] = None
        self._rx_attempt_counter = 0
        self.rx_attempts: List[Dict[str, Any]] = []
        self.ack_provenance: List[Dict[str, Any]] = []
        self._ack_event_counter = 0
        self.record_rx_attempts = (
            protocol.name.startswith(("meshecho-drc", "meshecho-cpr"))
            if record_rx_attempts is None else bool(record_rx_attempts)
        )
        shadow_rng = random.Random(seed + 0x5F3759DF)
        self.link_shadowing_db: Dict[Tuple[int, int], float] = {}
        node_ids = sorted(self.nodes)
        for index, first in enumerate(node_ids):
            for second in node_ids[index + 1 :]:
                self.link_shadowing_db[(first, second)] = shadow_rng.gauss(
                    0.0,
                    self.radio.shadow_sigma_db,
                )
        self.metrics = Metrics(len(nodes))
        self.protocol.bind(self)

    def rreq_forward_delay(self, packet: Packet, relay: int) -> float:
        """Return a stable relay delay shared by matched discovery policies."""

        key = (
            f"rreq:{self.seed}:{packet.origin}:{packet.final_dst}:"
            f"{packet.request_id}:{relay}"
        )
        return MATCHED_RREQ_BASE_DELAY_S + (
            random.Random(key).random() * MATCHED_RREQ_JITTER_S
        )

    def discovery_collection_window_s(self, requested_s: float) -> float:
        """Bound matched collection by the longest admissible RREQ path."""

        if requested_s <= 0.0 or not self.matched_rreq_timing:
            return requested_s
        hops = max(1, self.max_hops)
        longest_rreq = Packet(
            kind="RREQ", flow_id=0, origin=0, final_dst=1, ttl=hops,
            created_at=0.0, protocol="timing", path=tuple(range(hops)),
            path_confidence=1.0, app_payload=False,
        )
        airtime_s = self.radio.packet_toa_s(longest_rreq)
        relay_bound_s = MATCHED_RREQ_BASE_DELAY_S + MATCHED_RREQ_JITTER_S
        return max(
            requested_s,
            (hops - 1) * (relay_bound_s + airtime_s) + airtime_s,
        )

    def route_discovery_rrep_wait_s(
        self, requested_wait_s: float, requested_window_s: float,
        native_relay_delay_bound_s: float = 0.0,
    ) -> float:
        """Allow a max-hop RREQ, destination collection, and reverse RREP."""

        hops = max(1, self.max_hops)
        request = Packet(
            kind="RREQ", flow_id=0, origin=0, final_dst=1, ttl=hops,
            created_at=0.0, protocol="timing", path=tuple(range(hops)),
            path_confidence=1.0, app_payload=False,
        )
        reverse_path = tuple(range(hops + 1))
        reply = Packet(
            kind="RREP", flow_id=0, origin=1, final_dst=0, ttl=hops,
            created_at=0.0, protocol="timing", path=reverse_path,
            learned_path=tuple(reversed(reverse_path)),
            path_confidence=1.0, app_payload=False,
        )
        request_airtime_s = self.radio.packet_toa_s(request)
        reply_airtime_s = self.radio.packet_toa_s(reply)
        relay_bound_s = (
            MATCHED_RREQ_BASE_DELAY_S + MATCHED_RREQ_JITTER_S
            if self.matched_rreq_timing else native_relay_delay_bound_s
        )
        request_travel_s = hops * request_airtime_s + (hops - 1) * relay_bound_s
        reply_travel_s = hops * reply_airtime_s
        return max(
            requested_wait_s,
            request_travel_s
            + self.discovery_collection_window_s(requested_window_s)
            + reply_travel_s
            + max(request_airtime_s, reply_airtime_s),
        )

    def schedule(self, when: float, event_type: str, data: Any) -> None:
        self._event_counter += 1
        # Complete a physical receive before same-time protocol decisions and
        # sends. The explicit table is part of the DRC deadline contract.
        priority = EVENT_PRIORITY.get(event_type, 1)
        heapq.heappush(
            self.events, (when, (priority, self._event_counter), event_type, data),
        )

    def distance_m(self, a: int, b: int) -> float:
        na = self.nodes[a]
        nb = self.nodes[b]
        return math.hypot(na.x - nb.x, na.y - nb.y)

    def path_loss_db(
        self,
        distance_m: float,
        shadowing_db: Optional[float] = None,
    ) -> float:
        distance_m = max(distance_m, 1.0)
        # Free-space path loss at 1 m. 32.44 + MHz + km form.
        pl0 = 32.44 + 20.0 * math.log10(self.radio.carrier_mhz) + 20.0 * math.log10(0.001)
        shadow = (
            self.channel_random.gauss(0.0, self.radio.shadow_sigma_db)
            if shadowing_db is None
            else shadowing_db
        )
        return pl0 + 10.0 * self.radio.path_loss_exp * math.log10(distance_m) + shadow

    def temporal_fading_db(
        self,
        sender: int,
        receiver: int,
        when: Optional[float],
    ) -> float:
        """Return a paired, deterministic block-fading offset.

        The offset is keyed by seed, unordered link, and time block.  It is
        therefore identical for all protocols in a paired run, independent of
        event-order random draws, while still allowing a cached route to become
        stale after the channel block changes.
        """

        sigma = self.radio.temporal_fading_sigma_db
        if sigma <= 0.0 or when is None:
            return 0.0
        interval = max(self.radio.temporal_fading_interval_s, 1e-9)
        block = math.floor(max(0.0, when) / interval)
        first, second = sorted((sender, receiver))
        mixed = (
            (self.seed * 0x9E3779B1)
            ^ (first * 0x85EBCA6B)
            ^ (second * 0xC2B2AE35)
            ^ (block * 0x27D4EB2D)
        ) & 0xFFFFFFFFFFFFFFFF
        return random.Random(mixed).gauss(0.0, sigma)

    def rx_power_dbm(
        self,
        sender: int,
        receiver: int,
        when: Optional[float] = None,
    ) -> float:
        key = tuple(sorted((sender, receiver)))
        shadowing_db = self.link_shadowing_db.get(key, 0.0)
        return self.radio.tx_power_dbm - self.path_loss_db(
            self.distance_m(sender, receiver),
            shadowing_db=shadowing_db,
        ) + self.temporal_fading_db(sender, receiver, when)

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
        if handle.request_id == 0:
            self._request_counter += 1
            handle.request_id = self._request_counter
            handle.requested_at = self.now
            flow_record = getattr(self.protocol, "flow_records", {}).get(packet.flow_id)
            record = {
                "request_id": handle.request_id,
                "event_ordinal": self._event_counter + 1,
                "application_ordinal": self._current_application_ordinal,
                "requested_at": self.now,
                "sender": sender,
                "flow_id": packet.flow_id,
                "packet_kind": packet.kind,
                "protocol": packet.protocol,
                "origin": packet.origin,
                "final_dst": packet.final_dst,
                "wire_request_id": packet.request_id,
                "path": tuple(packet.path),
                "path_index": packet.path_index,
                "repair_index": packet.repair_index,
                "deadline_at": getattr(flow_record, "deadline", None),
                "status": "scheduled",
                "status_at": None,
                "start": None,
                "end": None,
                "queue_wait_s": None,
                "tx_id": None,
                "actual_packet_kind": None,
                "no_start_reason": None,
            }
            self.tx_requests.append(record)
            self._request_records[handle.request_id] = record
        self.schedule(self.now + max(0.0, delay_s), "tx_request", (sender, packet, handle))
        return handle

    def finalize_request_ledger(self, cutoff: Optional[float] = None) -> None:
        """Close requests that were still queued when an artifact window ended.

        ``run`` may be called repeatedly by existing diagnostics, so cutoff
        classification is explicit rather than silently performed at every
        partial run.  A finalized request never receives a physical TX join.
        """

        cutoff_at = self.now if cutoff is None else float(cutoff)
        for record in self.tx_requests:
            if record["status"] != "scheduled":
                continue
            record["status"] = "not_processed_by_cutoff"
            record["status_at"] = cutoff_at
            record["no_start_reason"] = "request-remained-in-event-queue"

    def begin_transmission(self, sender: int, packet: Packet, pending: PendingSend) -> None:
        record = self._request_records.get(pending.request_id)
        if pending.canceled:
            if record is not None:
                record["status"] = "canceled"
                record["status_at"] = self.now
                record["no_start_reason"] = "canceled-before-start"
            return
        node = self.nodes[sender]
        start = max(self.now, node.tx_available_at)
        if pending.can_start_at is not None and not pending.can_start_at(start):
            if record is not None:
                record["status"] = "guard-rejected"
                record["status_at"] = start
                record["start"] = start
                record["queue_wait_s"] = max(
                    0.0, start - float(record["requested_at"])
                )
                record["no_start_reason"] = "can-start-predicate"
            return
        packet = self.protocol.on_tx_request(sender, packet, start, pending)
        if packet is None:
            if record is not None:
                record["status"] = "protocol-no-start"
                record["status_at"] = start
                record["start"] = start
                record["queue_wait_s"] = max(
                    0.0, start - float(record["requested_at"])
                )
                record["no_start_reason"] = "protocol-hook"
            return
        if record is not None:
            record["actual_packet_kind"] = packet.kind
            record["protocol"] = packet.protocol
            record["origin"] = packet.origin
            record["final_dst"] = packet.final_dst
            record["wire_request_id"] = packet.request_id
            record["path"] = tuple(packet.path)
            record["path_index"] = packet.path_index
            record["repair_index"] = packet.repair_index
            record["deadline_at"] = getattr(
                getattr(self.protocol, "flow_records", {}).get(packet.flow_id),
                "deadline", record.get("deadline_at"),
            )
        pending.committed = True
        airtime_s = self.radio.packet_toa_s(packet)
        end = start + airtime_s
        node.tx_available_at = end
        self._tx_counter += 1
        tx = Transmission(self._tx_counter, sender, packet, start, end)
        self.transmissions.append(tx)
        if record is not None:
            record["status"] = "started"
            record["status_at"] = start
            record["start"] = start
            record["end"] = end
            record["queue_wait_s"] = max(
                0.0, start - float(record["requested_at"])
            )
            record["tx_id"] = tx.tx_id
            record["actual_packet_kind"] = packet.kind
        self.metrics.tx_count += 1
        self.metrics.total_airtime_s += airtime_s
        self.metrics.record_transmission(start, end)
        self.metrics.tx_energy_j += (
            self.radio.supply_voltage_v * self.radio.tx_current_ma / 1000.0 * airtime_s
        )
        listening_nodes = sum(
            1
            for receiver in self.nodes
            if receiver != sender
            and not self.receiver_is_transmitting(receiver, start, end)
        )
        self.metrics.rx_energy_j += (
            listening_nodes * self.radio.supply_voltage_v
            * self.radio.rx_current_ma / 1000.0 * airtime_s
        )
        if packet.is_control:
            self.metrics.control_tx += 1
        else:
            self.metrics.data_tx += 1
        if packet.kind == "RREQ":
            self.metrics.route_requests += 1
        if packet.kind == "RREP":
            self.metrics.route_replies += 1
        if packet.kind == "ACK":
            self.metrics.ack_tx += 1
        if packet.kind == "FALLBACK":
            self.metrics.fallback_forward_count += 1
        self.schedule(end, "tx_end", tx)
        self.protocol.on_transmit(sender, packet, start, end)

    def transmissions_overlapping(self, start: float, end: float) -> Iterable[Transmission]:
        for tx in self.transmissions:
            if tx.start < end and start < tx.end:
                yield tx

    def prune_transmissions(self) -> None:
        """Retain interferers for every transmission not yet processed."""

        earliest_pending_start = min(
            (tx.start for tx in self.transmissions if tx.end >= self.now),
            default=self.now,
        )
        self.transmissions = [
            tx for tx in self.transmissions if tx.end > earliest_pending_start
        ]

    def receiver_is_transmitting(self, receiver: int, start: float, end: float) -> bool:
        return any(tx.sender == receiver for tx in self.transmissions_overlapping(start, end))

    def _record_rx_attempt(
        self,
        tx: Transmission,
        receiver: int,
        *,
        reason: str,
        decoded: bool,
        rx_power_dbm: Optional[float] = None,
        snr_db: Optional[float] = None,
        sinr_db: Optional[float] = None,
        interference_tx_ids: Iterable[int] = (),
    ) -> Optional[int]:
        if not self.record_rx_attempts:
            return None
        self._rx_attempt_counter += 1
        attempt_id = self._rx_attempt_counter
        self.rx_attempts.append({
            "rx_attempt_id": attempt_id,
            "attempt_ordinal": attempt_id,
            "tx_id": tx.tx_id,
            "receiver": receiver,
            "sender": tx.sender,
            "flow_id": tx.packet.flow_id,
            "request_id": tx.packet.request_id,
            "packet_kind": tx.packet.kind,
            "repair_index": tx.packet.repair_index,
            "path": tuple(tx.packet.path),
            "path_index": tx.packet.path_index,
            "start": tx.start,
            "end": tx.end,
            "rx_power_dbm": rx_power_dbm,
            "snr_db": snr_db,
            "sinr_db": sinr_db,
            "interference_tx_ids": tuple(sorted(interference_tx_ids)),
            "reason": reason,
            "decoded": decoded,
            "in_deadline": None,
        })
        return attempt_id

    def try_receive(self, tx: Transmission, receiver: int) -> Optional[RxInfo]:
        if receiver == tx.sender:
            self._record_rx_attempt(
                tx, receiver, reason="self", decoded=False,
            )
            return None
        if self.receiver_is_transmitting(receiver, tx.start, tx.end):
            self.metrics.rx_fail += 1
            self._record_rx_attempt(
                tx, receiver, reason="half_duplex", decoded=False,
            )
            return None

        signal_dbm = self.rx_power_dbm(tx.sender, receiver, when=tx.start)
        interference_dbm: List[float] = []
        for other in self.transmissions_overlapping(tx.start, tx.end):
            if other.tx_id == tx.tx_id or other.sender == receiver:
                continue
            interference_dbm.append(
                self.rx_power_dbm(other.sender, receiver, when=other.start)
            )

        snr_db = self.snr_from_power(signal_dbm)
        collided = False
        sinr_db = snr_db
        if interference_dbm:
            strongest_interference = max(interference_dbm)
            if signal_dbm < strongest_interference + self.radio.capture_threshold_db:
                self.metrics.rx_fail += 1
                self.metrics.collision_fail += 1
                interference_ids = [
                    other.tx_id
                    for other in self.transmissions_overlapping(tx.start, tx.end)
                    if other.tx_id != tx.tx_id and other.sender != receiver
                ]
                self._record_rx_attempt(
                    tx, receiver, reason="capture_collision", decoded=False,
                    rx_power_dbm=signal_dbm, snr_db=snr_db, sinr_db=sinr_db,
                    interference_tx_ids=interference_ids,
                )
                return None
            noise_mw = dbm_to_mw(self.radio.noise_floor_dbm)
            signal_mw = dbm_to_mw(signal_dbm)
            interference_mw = sum(dbm_to_mw(x) for x in interference_dbm)
            sinr_db = 10.0 * math.log10(signal_mw / (noise_mw + interference_mw))
            collided = True

        interference_ids = [
            other.tx_id
            for other in self.transmissions_overlapping(tx.start, tx.end)
            if other.tx_id != tx.tx_id and other.sender != receiver
        ]
        if self.channel_random.random() <= self.prr_from_snr(sinr_db):
            self.metrics.rx_success += 1
            attempt_id = self._record_rx_attempt(
                tx, receiver, reason="success", decoded=True,
                rx_power_dbm=signal_dbm, snr_db=snr_db, sinr_db=sinr_db,
                interference_tx_ids=interference_ids,
            )
            return RxInfo(
                tx.sender, signal_dbm, snr_db, sinr_db, collided,
                tx_id=tx.tx_id, attempt_id=attempt_id,
            )

        self.metrics.rx_fail += 1
        self._record_rx_attempt(
            tx, receiver, reason="prr_fail", decoded=False,
            rx_power_dbm=signal_dbm, snr_db=snr_db, sinr_db=sinr_db,
            interference_tx_ids=interference_ids,
        )
        return None

    def record_ack_provenance(
        self,
        packet: Packet,
        rx: RxInfo,
        *,
        receiver: int,
        accepted: bool,
        rejection_reason: Optional[str] = None,
        route_generation: Optional[int] = None,
        accepted_at: Optional[float] = None,
        deadline_at: Optional[float] = None,
    ) -> int:
        """Persist the physical evidence used for a source ACK decision."""

        self._ack_event_counter += 1
        self.ack_provenance.append({
            "ack_event_id": self._ack_event_counter,
            "flow_id": packet.flow_id,
            "source": packet.final_dst,
            "destination": packet.origin,
            "receiver": receiver,
            "ack_tx_id": rx.tx_id,
            "ack_rx_attempt_id": rx.attempt_id,
            "ack_rx_at": self.now,
            "deadline_at": deadline_at,
            "reverse_path": tuple(packet.path),
            "reverse_hop": packet.path_index,
            "repair_index": packet.repair_index,
            "accepted": bool(accepted),
            "rejection_reason": rejection_reason,
            "accepted_at": accepted_at,
            "route_generation": route_generation,
            "route_generation_after": None,
        })
        return self._ack_event_counter

    def handle_tx_end(self, tx: Transmission) -> None:
        self.prune_transmissions()
        for receiver in self.nodes:
            rx = self.try_receive(tx, receiver)
            if rx is not None:
                self.protocol.on_receive(receiver, tx.packet, rx)

    def mark_delivered(self, flow_id: int, receiver: int, packet: Packet) -> None:
        flow = self.metrics.flows.get(flow_id)
        if (flow is None or packet.origin != flow.src
                or packet.final_dst != flow.dst):
            return
        was_delivered = False
        if flow.dst == BROADCAST_DST:
            was_delivered = receiver != flow.src and receiver not in flow.broadcast_receivers
        else:
            was_delivered = receiver == flow.dst and flow.delivered_at is None
        self.metrics.mark_delivered(flow_id, receiver, self.now)
        if was_delivered:
            self.protocol.on_delivery(flow_id, receiver, self.now, packet)

    def mark_acknowledged(self, flow_id: int, receiver: int, packet: Packet) -> None:
        if self.metrics.mark_acknowledged(flow_id, receiver, self.now):
            self.protocol.on_ack(flow_id, receiver, self.now, packet)

    def run(self, until_s: float) -> Metrics:
        while self.events:
            when, event_order, event_type, data = heapq.heappop(self.events)
            if when > until_s:
                heapq.heappush(self.events, (when, event_order, event_type, data))
                break
            self.now = when
            if event_type == "app_send":
                src, dst, flow_id = data
                self._application_counter += 1
                ordinal = self._application_counter
                self.application_events.append({
                    "ordinal": ordinal,
                    "time": self.now,
                    "src": src,
                    "dst": dst,
                    "flow_id": flow_id,
                })
                self._current_application_ordinal = ordinal
                try:
                    self.protocol.send_app(src, dst, flow_id)
                finally:
                    self._current_application_ordinal = None
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
                    self.protocol.on_flow_completion(
                        flow_id,
                        self.protocol.flow_confirmed(flow),
                        self.now,
                    )
            else:
                raise ValueError(f"unknown event type: {event_type}")
        self.now = until_s
        return self.metrics


class RoutingProtocol:
    name = "base"

    def bind(self, sim: Simulator) -> None:
        self.sim = sim
        self.discovery_records: List[DiscoveryRecord] = []
        self.discovery_started_at: Dict[Tuple[int, int, int], float] = {}
        self.closed_discovery_keys: Set[Tuple[int, int, int]] = set()

    def record_discovery(
        self,
        key: Tuple[int, int, int],
        candidate_paths: Iterable[Tuple[int, ...]],
        selected_path: Optional[Tuple[int, ...]],
    ) -> None:
        self.closed_discovery_keys.add(key)
        self.discovery_records.append(
            DiscoveryRecord(
                key=key,
                started_at=self.discovery_started_at.pop(key),
                closed_at=self.sim.now,
                candidate_paths=tuple(sorted(set(candidate_paths))),
                selected_path=selected_path,
            )
        )

    def send_app(self, src: int, dst: int, flow_id: int) -> None:
        raise NotImplementedError

    def on_receive(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        raise NotImplementedError

    def on_delivery(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        return None

    def on_ack(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        return None

    def on_transmit(self, sender: int, packet: Packet, start: float, end: float) -> None:
        return None

    def on_tx_request(
        self, sender: int, packet: Packet, start: float, pending: PendingSend,
    ) -> Optional[Packet]:
        """Return the packet to physically start, or ``None`` to no-start.

        The hook runs after the node's actual queue-available start time is
        known. Existing protocols retain their historical behavior by
        returning the requested packet unchanged. A protocol with a
        deadline-sensitive controller may re-evaluate a placeholder request
        here without charging a phantom transmission.
        """

        del sender, start, pending
        return packet

    def on_flow_completion(self, flow_id: int, delivered: bool, now: float) -> None:
        return None

    def flow_confirmed(self, flow: FlowRecord) -> bool:
        return flow.delivered_at is not None

    def ack_next_hop_matches(self, receiver: int, packet: Packet) -> bool:
        return 0 <= packet.path_index < len(packet.path) and packet.path[packet.path_index] == receiver

    def reverse_ack_delay_s(self, packet: Packet) -> float:
        return 0.0

    def send_ack_on_reverse_path(self, receiver: int, packet: Packet) -> None:
        if packet.path_index <= 0 or receiver != packet.final_dst:
            return
        ack = Packet(
            kind="ACK",
            flow_id=packet.flow_id,
            origin=receiver,
            final_dst=packet.origin,
            ttl=self.sim.max_hops,
            created_at=self.sim.now,
            protocol=self.name,
            request_id=packet.request_id,
            path=packet.path,
            path_index=packet.path_index - 1,
            app_payload=False,
            min_forward_margin_q=packet.min_forward_margin_q,
            min_forward_margin_hop=packet.min_forward_margin_hop,
            repair_index=packet.repair_index,
        )
        self.sim.transmit_later(receiver, ack, delay_s=self.reverse_ack_delay_s(packet))

    def send_direct_ack(self, receiver: int, packet: Packet) -> None:
        if receiver != packet.final_dst or packet.origin == BROADCAST_DST:
            return
        ack = Packet(
            kind="ACK",
            flow_id=packet.flow_id,
            origin=receiver,
            final_dst=packet.origin,
            ttl=self.sim.max_hops,
            created_at=self.sim.now,
            protocol=self.name,
            request_id=packet.request_id,
            path=(receiver, packet.origin),
            path_index=1,
            app_payload=False,
            min_forward_margin_q=packet.min_forward_margin_q,
            min_forward_margin_hop=packet.min_forward_margin_hop,
        )
        self.sim.transmit_later(receiver, ack, delay_s=0.0)

    def on_ack_packet(self, receiver: int, packet: Packet) -> None:
        if not self.ack_next_hop_matches(receiver, packet):
            return
        if receiver == packet.final_dst:
            self.sim.mark_acknowledged(packet.flow_id, receiver, packet)
            return
        if packet.ttl <= 1:
            return
        forwarded = packet.retreat_path().with_ttl(packet.ttl - 1)
        self.sim.transmit_later(receiver, forwarded, delay_s=0.0)


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
            path=(src,),
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
        if packet.kind == "ACK":
            self.on_ack_packet(receiver, packet)
            return
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
        packet_at_receiver = packet
        if packet.final_dst != BROADCAST_DST and packet.path:
            packet_at_receiver = Packet(
                kind=packet.kind,
                flow_id=packet.flow_id,
                origin=packet.origin,
                final_dst=packet.final_dst,
                ttl=packet.ttl,
                created_at=packet.created_at,
                protocol=packet.protocol,
                request_id=packet.request_id,
                path=packet.path + (receiver,),
                path_index=len(packet.path),
                learned_path=packet.learned_path,
                path_confidence=packet.path_confidence,
                app_payload=packet.app_payload,
                min_forward_margin_q=packet.min_forward_margin_q,
                min_forward_margin_hop=packet.min_forward_margin_hop,
            )
        if packet.final_dst == BROADCAST_DST or packet.final_dst == receiver:
            self.sim.mark_delivered(packet.flow_id, receiver, packet_at_receiver)
            if packet.final_dst == receiver:
                self.send_ack_on_reverse_path(receiver, packet_at_receiver)

        node = self.sim.nodes[receiver]
        if packet.ttl <= 1 or not node.can_relay:
            return
        if packet.final_dst != BROADCAST_DST and packet.final_dst == receiver:
            return

        forwarded = packet_at_receiver.with_ttl(packet.ttl - 1)
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
        discovery_window_s: float = DEFAULT_MESHCORE_DISCOVERY_WINDOW_S,
        rrep_wait_s: float = 10.0,
    ) -> None:
        self.route_ttl_s = route_ttl_s
        self.flood_base_delay_s = flood_base_delay_s
        self.flood_jitter_s = flood_jitter_s
        self.discovery_window_s = max(0.0, discovery_window_s)
        self.rrep_wait_s = rrep_wait_s
        self.route_cache: Dict[int, Dict[int, Tuple[float, Tuple[int, ...]]]] = {}
        self.pending_data: Dict[Tuple[int, int], List[int]] = {}
        self.seen_rreq: Dict[int, Set[Tuple[int, int, int]]] = {}
        self.rreq_candidates: Dict[Tuple[int, int, int], List[Tuple[int, ...]]] = {}
        self.rreq_timers: Set[Tuple[int, int, int]] = set()
        self.source_expired_discoveries: Set[Tuple[int, int, int]] = set()

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.route_cache = {node_id: {} for node_id in sim.nodes}
        self.pending_data = {}
        self.seen_rreq = {node_id: set() for node_id in sim.nodes}
        self.rreq_candidates = {}
        self.rreq_timers = set()
        self.source_expired_discoveries = set()

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
        self.sim.metrics.route_discovery_attempts += 1
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
        if self.discovery_window_s > 0.0:
            key = (src, dst, request_id)
            self.rreq_candidates[key] = []

    def finish_route_discovery(self, key: Tuple[int, int, int]) -> None:
        """Reply after a matched discovery window using the shortest candidate."""

        self.rreq_timers.discard(key)
        candidates = self.rreq_candidates.pop(key, [])
        if not candidates:
            self.record_discovery(key, [], None)
            return
        src, dst, request_id = key
        learned_path = min(candidates, key=lambda path: (len(path), path))
        self.record_discovery(key, candidates, learned_path)
        reverse_path = tuple(reversed(learned_path))
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
            learned_path=learned_path,
            app_payload=False,
        )
        self.sim.transmit_later(dst, reply, delay_s=0.0)

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

    def on_transmit(self, sender: int, packet: Packet, start: float, end: float) -> None:
        if packet.kind == "RREQ" and sender == packet.origin:
            wait_s = self.sim.route_discovery_rrep_wait_s(
                self.rrep_wait_s, self.discovery_window_s,
                self.flood_base_delay_s + self.flood_jitter_s,
            )
            key = (sender, packet.final_dst, packet.request_id)
            self.sim.schedule(
                start + wait_s, "protocol_timer",
                lambda key=key: self.expire_source_discovery(key),
            )

    def expire_source_discovery(self, key: Tuple[int, int, int]) -> None:
        src, dst, request_id = key
        queued = self.pending_data.get((src, dst), [])
        if not queued or queued[0] != request_id:
            return
        self.source_expired_discoveries.add(key)
        self.pending_data.pop((src, dst), None)
        if key not in self.rreq_timers:
            self.rreq_candidates.pop(key, None)

    def on_receive(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if packet.kind == "RREQ":
            self.on_rreq(receiver, packet)
        elif packet.kind == "RREP":
            self.on_rrep(receiver, packet)
        elif packet.kind == "DATA":
            self.on_data(receiver, packet)
        elif packet.kind == "ACK":
            self.on_ack_packet(receiver, packet)

    def on_rreq(self, receiver: int, packet: Packet) -> None:
        if receiver in packet.path:
            return
        key = (packet.origin, packet.final_dst, packet.request_id)
        new_path = packet.path + (receiver,)
        if receiver == packet.final_dst:
            if self.discovery_window_s <= 0.0:
                # Preserve the historical immediate-reply baseline when no
                # matched discovery window is requested.  In this mode the
                # destination answers only the first copy of a request;
                # duplicate suppression is intentionally scoped to this
                # legacy branch because the matched-window branch below must
                # expose every candidate path.
                if key in self.seen_rreq[receiver]:
                    self.sim.metrics.duplicate_rx += 1
                    return
                self.seen_rreq[receiver].add(key)
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
            else:
                if key in self.closed_discovery_keys:
                    return
                if key not in self.rreq_timers:
                    self.rreq_timers.add(key)
                    self.discovery_started_at[key] = self.sim.now
                    self.sim.schedule(
                        self.sim.now + self.sim.discovery_collection_window_s(
                            self.discovery_window_s
                        ),
                        "protocol_timer",
                        lambda key=key: self.finish_route_discovery(key),
                    )
                self.rreq_candidates.setdefault(key, []).append(new_path)
                # The destination is the candidate collector in the matched
                # window.  It must observe every arriving path, just as
                # MeshEcho and the metric baselines do; suppressing duplicate
                # RREQs before this branch makes the source-route baseline
                # incomparable by shrinking its candidate pool.
                self.seen_rreq[receiver].add(key)
            return

        if key in self.seen_rreq[receiver]:
            self.sim.metrics.duplicate_rx += 1
            return
        self.seen_rreq[receiver].add(key)

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
        delay = (
            self.sim.rreq_forward_delay(packet, receiver)
            if self.sim.matched_rreq_timing
            else self.flood_delay()
        )
        self.sim.transmit_later(receiver, forwarded, delay_s=delay)

    def path_next_hop_matches(self, receiver: int, packet: Packet) -> bool:
        next_index = packet.path_index + 1
        return next_index < len(packet.path) and packet.path[next_index] == receiver

    def on_rrep(self, receiver: int, packet: Packet) -> None:
        if not self.path_next_hop_matches(receiver, packet):
            return
        advanced = packet.advance_path()
        if receiver == packet.final_dst:
            if (receiver, packet.origin, packet.request_id) in self.source_expired_discoveries:
                return
            learned = packet.learned_path
            dst = learned[-1]
            self.route_cache[receiver][dst] = (self.sim.now + self.route_ttl_s, learned)
            queued = self.pending_data.pop((receiver, dst), [])
            if queued:
                self.sim.metrics.route_discovery_successes += 1
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
            self.sim.mark_delivered(packet.flow_id, receiver, advanced)
            self.send_ack_on_reverse_path(receiver, advanced)
            return
        self.sim.transmit_later(receiver, advanced, delay_s=0.0)


class MeshtasticCommonAck(MeshtasticLike):
    """Product-inspired, not firmware-equivalent, DATA-first ACK baseline.

    A managed DATA flood traces the first path. Relays learn a next hop from
    the returning ACK; only a source-received ACK confirms a reusable route.
    An unacknowledged directed flow invalidates that route for the next flow,
    without retransmitting the current flow.
    """

    name = "meshtastic-common-ack"

    def __init__(
        self,
        route_ttl_s: float = 600.0,
        ack_guard_s: float = 15.0,
        app_deadline_s: float = 30.0,
        base_delay_s: float = 0.75,
        jitter_s: float = 0.75,
        role_bonus_s: float = 0.25,
    ) -> None:
        if min(route_ttl_s, ack_guard_s, app_deadline_s) <= 0.0:
            raise ValueError("route TTL and ACK deadlines must be positive")
        super().__init__(base_delay_s, jitter_s, role_bonus_s)
        self.route_ttl_s = route_ttl_s
        self.ack_guard_s = ack_guard_s
        self.app_deadline_s = app_deadline_s
        self.next_hops: Dict[int, Dict[int, Tuple[float, int]]] = {}
        self.flow_modes: Dict[int, str] = {}
        self.flow_sent_paths: Dict[int, Tuple[int, ...]] = {}
        self.flow_deadlines: Dict[int, float] = {}
        self.flow_route_versions: Dict[int, int] = {}
        self.route_versions: Dict[Tuple[int, int], int] = {}
        self.timed_out_flows: Set[int] = set()

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.next_hops = {node_id: {} for node_id in sim.nodes}
        self.flow_modes = {}
        self.flow_sent_paths = {}
        self.flow_deadlines = {}
        self.flow_route_versions = {}
        self.route_versions = {}
        self.timed_out_flows = set()

    def get_route(self, src: int, dst: int) -> Optional[int]:
        entry = self.next_hops[src].get(dst)
        if entry is None:
            return None
        expires_at, next_hop = entry
        if expires_at <= self.sim.now:
            del self.next_hops[src][dst]
            return None
        return next_hop

    def evict_route(self, src: int, dst: int) -> None:
        self.next_hops[src].pop(dst, None)

    def send_app(self, src: int, dst: int, flow_id: int) -> None:
        self.sim.metrics.register_flow(flow_id, src, dst, self.sim.now)
        route = self.get_route(src, dst) if dst != BROADCAST_DST else None
        if route is None:
            if dst != BROADCAST_DST:
                self.sim.metrics.route_cache_misses += 1
            self.send_data_flood(src, dst, flow_id)
        else:
            self.sim.metrics.route_cache_hits += 1
            self.send_directed(src, dst, flow_id, route)

    def send_data_flood(self, src: int, dst: int, flow_id: int) -> None:
        self.flow_modes[flow_id] = "F"
        packet = Packet(
            kind="DATA", flow_id=flow_id, origin=src, final_dst=dst,
            ttl=self.sim.max_hops, created_at=self.sim.metrics.flows[flow_id].created_at,
            protocol=self.name, request_id=flow_id, path=(src,),
        )
        self.seen[src].add(packet.flood_key)
        self.sim.transmit_later(src, packet, delay_s=0.0)

    def send_directed(self, src: int, dst: int, flow_id: int, route: int) -> None:
        path = (src, route)
        self.flow_modes[flow_id] = "R"
        self.flow_sent_paths[flow_id] = path
        self.flow_route_versions[flow_id] = self.route_versions.get((src, dst), 0)
        packet = Packet(
            kind="DIRECT", flow_id=flow_id, origin=src, final_dst=dst,
            ttl=self.sim.max_hops, created_at=self.sim.metrics.flows[flow_id].created_at,
            protocol=self.name, request_id=flow_id, path=path,
        )
        self.sim.transmit_later(src, packet, delay_s=0.0)

    def on_receive(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if packet.kind == "DIRECT":
            self.on_directed_data(receiver, packet)
        else:
            super().on_receive(receiver, packet, rx)

    def on_directed_data(self, receiver: int, packet: Packet) -> None:
        next_index = packet.path_index + 1
        if next_index >= len(packet.path) or packet.path[next_index] != receiver:
            return
        advanced = packet.advance_path()
        if receiver == packet.final_dst:
            self.sim.mark_delivered(packet.flow_id, receiver, advanced)
            self.send_ack_on_reverse_path(receiver, advanced)
            return
        if packet.ttl <= 1 or not self.sim.nodes[receiver].can_relay:
            return
        next_hop = self.get_route(receiver, packet.final_dst)
        if next_hop is None or next_hop in advanced.path:
            return
        forwarded = Packet(
            kind="DIRECT", flow_id=packet.flow_id, origin=packet.origin,
            final_dst=packet.final_dst, ttl=packet.ttl - 1,
            created_at=packet.created_at, protocol=self.name,
            request_id=packet.request_id, path=advanced.path + (next_hop,),
            path_index=advanced.path_index,
        )
        self.sim.transmit_later(receiver, forwarded, delay_s=0.0)

    def on_transmit(self, sender: int, packet: Packet, start: float, end: float) -> None:
        if packet.kind not in {"DATA", "DIRECT"} or sender != packet.origin:
            return
        flow = self.sim.metrics.flows.get(packet.flow_id)
        if flow is None or flow.dst == BROADCAST_DST:
            return
        deadline = start + self.ack_guard_s
        self.flow_deadlines[packet.flow_id] = deadline
        self.sim.schedule(
            deadline, "protocol_timer",
            lambda flow_id=packet.flow_id: self.expire_ack(flow_id),
        )

    def expire_ack(self, flow_id: int) -> None:
        flow = self.sim.metrics.flows.get(flow_id)
        if flow is None or flow.acked_at is not None or flow_id in self.timed_out_flows:
            return
        self.timed_out_flows.add(flow_id)
        if self.flow_modes.get(flow_id) != "R":
            return
        key = (flow.src, flow.dst)
        if self.route_versions.get(key, 0) != self.flow_route_versions[flow_id]:
            return
        self.evict_route(flow.src, flow.dst)
        self.sim.metrics.ack_timeout_invalidations += 1
        if flow.delivered_at is not None:
            self.sim.metrics.timeout_invalidations_after_destination_delivery += 1

    def ack_matches_sent_route(self, flow_id: int, path: Tuple[int, ...]) -> bool:
        return path[:2] == self.flow_sent_paths.get(flow_id)

    def on_ack_packet(self, receiver: int, packet: Packet) -> None:
        path = packet.path
        index = packet.path_index
        if (
            not 0 <= index < len(path)
            or path[index] != receiver
            or path[-1] != packet.origin
        ):
            return
        if receiver == packet.final_dst:
            flow = self.sim.metrics.flows.get(packet.flow_id)
            if (
                flow is None or packet.request_id != packet.flow_id
                or receiver != flow.src or packet.origin != flow.dst
                or self.sim.now > flow.created_at + self.app_deadline_s
                or (
                    self.flow_modes.get(flow.flow_id) == "R"
                    and not self.ack_matches_sent_route(flow.flow_id, path)
                )
            ):
                return
        if index + 1 < len(path):
            self.next_hops[receiver][packet.origin] = (
                self.sim.now + self.route_ttl_s, path[index + 1],
            )
        super().on_ack_packet(receiver, packet)

    def on_ack(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        flow = self.sim.metrics.flows[flow_id]
        if packet.path[0] != receiver or packet.path[-1] != flow.dst:
            return
        self.timed_out_flows.discard(flow_id)
        key = (receiver, flow.dst)
        self.route_versions[key] = self.route_versions.get(key, 0) + 1
        self.commit_source_route(receiver, flow.dst, packet.path, now)

    def commit_source_route(
        self, src: int, dst: int, path: Tuple[int, ...], now: float,
    ) -> None:
        self.next_hops[src][dst] = (now + self.route_ttl_s, path[1])


class MeshCoreCommonAck(MeshtasticCommonAck):
    """Product-inspired DATA-first source routing, not MeshCore firmware."""

    name = "meshcore-common-ack"

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.source_paths: Dict[int, Dict[int, Tuple[float, Tuple[int, ...]]]] = {
            node_id: {} for node_id in sim.nodes
        }

    def get_route(self, src: int, dst: int) -> Optional[Tuple[int, ...]]:
        entry = self.source_paths[src].get(dst)
        if entry is None:
            return None
        expires_at, path = entry
        if expires_at <= self.sim.now:
            del self.source_paths[src][dst]
            return None
        return path

    def evict_route(self, src: int, dst: int) -> None:
        self.source_paths[src].pop(dst, None)

    def send_directed(
        self, src: int, dst: int, flow_id: int, route: Tuple[int, ...],
    ) -> None:
        self.flow_modes[flow_id] = "R"
        self.flow_sent_paths[flow_id] = route
        self.flow_route_versions[flow_id] = self.route_versions.get((src, dst), 0)
        packet = Packet(
            kind="DIRECT", flow_id=flow_id, origin=src, final_dst=dst,
            ttl=self.sim.max_hops, created_at=self.sim.metrics.flows[flow_id].created_at,
            protocol=self.name, request_id=flow_id, path=route,
        )
        self.sim.transmit_later(src, packet, delay_s=0.0)

    def on_directed_data(self, receiver: int, packet: Packet) -> None:
        next_index = packet.path_index + 1
        if next_index >= len(packet.path) or packet.path[next_index] != receiver:
            return
        advanced = packet.advance_path()
        if receiver == packet.final_dst:
            self.sim.mark_delivered(packet.flow_id, receiver, advanced)
            self.send_ack_on_reverse_path(receiver, advanced)
        elif packet.ttl > 1 and self.sim.nodes[receiver].can_relay:
            self.sim.transmit_later(receiver, advanced.with_ttl(packet.ttl - 1), 0.0)

    def ack_matches_sent_route(self, flow_id: int, path: Tuple[int, ...]) -> bool:
        return path == self.flow_sent_paths.get(flow_id)

    def commit_source_route(
        self, src: int, dst: int, path: Tuple[int, ...], now: float,
    ) -> None:
        self.source_paths[src][dst] = (now + self.route_ttl_s, path)


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
        route_miss_recovery_enabled: bool = True,
        rrep_wait_s: float = 10.0,
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
        self.route_miss_recovery_enabled = route_miss_recovery_enabled
        self.rrep_wait_s = rrep_wait_s
        self.route_cache: Dict[int, Dict[int, RouteEntry]] = {}
        self.pending_data: Dict[Tuple[int, int], List[int]] = {}
        self.seen_floods: Dict[int, Set[Tuple[str, int, int, int]]] = {}
        self.pending_fallback: Dict[Tuple[int, Tuple[str, int, int, int]], PendingSend] = {}
        self.source_fallbacks: Dict[int, List[PendingSend]] = {}
        self.rreq_candidates: Dict[Tuple[int, int, int], List[Tuple[Tuple[int, ...], float]]] = {}
        self.rreq_timers: Set[Tuple[int, int, int]] = set()
        self.source_expired_discoveries: Set[Tuple[int, int, int]] = set()

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.route_cache = {node_id: {} for node_id in sim.nodes}
        self.pending_data = {}
        self.seen_floods = {node_id: set() for node_id in sim.nodes}
        self.pending_fallback = {}
        self.source_fallbacks = {}
        self.rreq_candidates = {}
        self.rreq_timers = set()
        self.source_expired_discoveries = set()

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

    def route_confidence(
        self,
        entry: RouteEntry,
        route_age_penalty: Optional[float] = None,
    ) -> float:
        age = max(0.0, self.sim.now - entry.created_at)
        lifetime = max(1.0, entry.expires_at - entry.created_at)
        penalty = self.route_age_penalty if route_age_penalty is None else route_age_penalty
        age_penalty = clamp(age / lifetime, 0.0, 1.0) * penalty
        return clamp(entry.confidence - age_penalty, 0.0, 1.0)

    def route_ttl_for(self, flow_id: int) -> float:
        return self.route_ttl_s

    def discovery_window_for(self, flow_id: int) -> float:
        return self.discovery_window_s

    def fallback_confidence_threshold_for(self, flow_id: int) -> float:
        return self.fallback_confidence_threshold

    def fallback_ttl_for(self, flow_id: int) -> int:
        return self.fallback_ttl

    def fallback_delay_margin_for(self, flow_id: int) -> float:
        return self.fallback_delay_margin_s

    def route_age_penalty_for(self, flow_id: int) -> float:
        return self.route_age_penalty

    def select_route_candidate(
        self,
        candidates: Sequence[Tuple[Tuple[int, ...], float]],
        flow_id: int,
    ) -> Tuple[Tuple[int, ...], float]:
        return max(candidates, key=lambda item: (item[1], -len(item[0])))

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
        self.sim.metrics.route_discovery_attempts += 1
        request_id = flow_id
        key = (src, dst, request_id)
        self.rreq_candidates[key] = []
        packet = Packet(
            kind="RREQ",
            flow_id=flow_id,
            origin=src,
            final_dst=dst,
            ttl=self.discovery_ttl_for(src, dst, flow_id),
            created_at=self.sim.now,
            protocol=self.name,
            request_id=request_id,
            path=(src,),
            path_confidence=1.0,
            app_payload=False,
        )
        self.seen_floods[src].add(packet.flood_key)
        self.sim.transmit_later(src, packet, delay_s=0.0)

    def discovery_ttl_for(self, src: int, dst: int, flow_id: int) -> int:
        return self.sim.max_hops

    def finish_route_discovery(self, key: Tuple[int, int, int]) -> None:
        self.rreq_timers.discard(key)
        candidates = self.rreq_candidates.pop(key, [])
        if not candidates:
            self.record_discovery(key, [], None)
            self.finish_failed_route_discovery(key)
            return
        src, dst, request_id = key
        path, confidence = self.select_route_candidate(candidates, request_id)
        self.record_discovery(key, (path for path, _ in candidates), path)
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

    def finish_failed_route_discovery(self, key: Tuple[int, int, int]) -> None:
        src, dst, _ = key
        queued = self.pending_data.pop((src, dst), [])
        for flow_id in queued:
            self.sim.metrics.route_repair_count += 1
            fallback_ttl = self.route_miss_recovery_ttl(flow_id)
            if fallback_ttl <= 0:
                continue
            self.start_fallback(
                src,
                dst,
                flow_id,
                ttl=fallback_ttl,
                delay_s=0.0,
            )

    def route_miss_recovery_ttl(self, flow_id: Optional[int] = None) -> int:
        if not self.route_miss_recovery_enabled:
            return 0
        return self.fallback_ttl_for(flow_id if flow_id is not None else 0)

    def send_data_on_path(
        self,
        src: int,
        dst: int,
        flow_id: int,
        entry: RouteEntry,
    ) -> None:
        if len(entry.path) < 2:
            return
        confidence = self.route_confidence(
            entry,
            self.route_age_penalty_for(flow_id),
        )
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
        if confidence < self.fallback_confidence_threshold_for(flow_id):
            fallback_delay = (
                self.sim.radio.packet_toa_s(packet)
                * min(max(len(entry.path) - 1, 1), 4)
                + self.fallback_delay_margin_for(flow_id)
            )
            self.start_fallback(
                src,
                dst,
                flow_id,
                ttl=self.fallback_ttl_for(flow_id),
                delay_s=fallback_delay,
            )

    def start_fallback(self, src: int, dst: int, flow_id: int, ttl: int, delay_s: float) -> None:
        fallback = Packet(
            kind="FALLBACK",
            flow_id=flow_id,
            origin=src,
            final_dst=dst,
            ttl=ttl,
            created_at=self.sim.metrics.flows[flow_id].created_at,
            protocol=self.name,
            path=(src,),
        )
        self.seen_floods[src].add(fallback.flood_key)
        pending = self.sim.transmit_later(src, fallback, delay_s=delay_s)
        if delay_s > 0.0:
            self.source_fallbacks.setdefault(flow_id, []).append(pending)

    def on_ack(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        pending_fallbacks = self.source_fallbacks.pop(flow_id, [])
        for pending in pending_fallbacks:
            pending.canceled = True

    def on_transmit(self, sender: int, packet: Packet, start: float, end: float) -> None:
        if packet.kind == "RREQ" and sender == packet.origin:
            wait_s = self.sim.route_discovery_rrep_wait_s(
                self.rrep_wait_s, self.discovery_window_for(packet.flow_id),
                self.flood_base_delay_s + self.flood_jitter_s + 0.35,
            )
            key = (sender, packet.final_dst, packet.request_id)
            self.sim.schedule(
                start + wait_s, "protocol_timer",
                lambda key=key: self.expire_source_discovery(key),
            )

    def expire_source_discovery(self, key: Tuple[int, int, int]) -> None:
        src, dst, request_id = key
        queued = self.pending_data.get((src, dst), [])
        if not queued or queued[0] != request_id:
            return
        self.source_expired_discoveries.add(key)
        self.finish_failed_route_discovery(key)
        if key not in self.rreq_timers:
            self.rreq_candidates.pop(key, None)

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
        elif packet.kind == "ACK":
            self.on_ack_packet(receiver, packet)

    def collect_rreq_candidate(
        self,
        packet: Packet,
        path: Tuple[int, ...],
        score: float,
    ) -> None:
        request_key = (packet.origin, packet.final_dst, packet.request_id)
        if request_key in self.closed_discovery_keys:
            return
        if request_key not in self.rreq_timers:
            self.rreq_timers.add(request_key)
            self.discovery_started_at[request_key] = self.sim.now
            self.sim.schedule(
                self.sim.now + self.sim.discovery_collection_window_s(
                    self.discovery_window_for(packet.flow_id)
                ),
                "protocol_timer",
                lambda key=request_key: self.finish_route_discovery(key),
            )
        self.rreq_candidates.setdefault(request_key, []).append((path, score))

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
            self.collect_rreq_candidate(packet, new_path, confidence)
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
        delay = (
            self.sim.rreq_forward_delay(packet, receiver)
            if self.sim.matched_rreq_timing
            else self.flood_delay(receiver, rx)
        )
        self.sim.transmit_later(receiver, forwarded, delay_s=delay)

    def on_rrep(self, receiver: int, packet: Packet) -> None:
        if not self.path_next_hop_matches(receiver, packet):
            return
        advanced = packet.advance_path()
        if receiver == packet.final_dst:
            if (receiver, packet.origin, packet.request_id) in self.source_expired_discoveries:
                return
            learned = packet.learned_path
            dst = learned[-1]
            confidence = packet.path_confidence or clamp(1.0 - (len(learned) - 2) * 0.06, 0.25, 0.95)
            self.route_cache[receiver][dst] = RouteEntry(
                created_at=self.sim.now,
                expires_at=self.sim.now + self.route_ttl_for(packet.flow_id),
                path=learned,
                confidence=confidence,
            )
            queued = self.pending_data.pop((receiver, dst), [])
            if queued:
                self.sim.metrics.route_discovery_successes += 1
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
            self.sim.mark_delivered(packet.flow_id, receiver, advanced)
            self.send_ack_on_reverse_path(receiver, advanced)
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
        if packet.path:
            packet_at_receiver = Packet(
                kind=packet.kind,
                flow_id=packet.flow_id,
                origin=packet.origin,
                final_dst=packet.final_dst,
                ttl=packet.ttl,
                created_at=packet.created_at,
                protocol=packet.protocol,
                request_id=packet.request_id,
                path=packet.path + (receiver,),
                path_index=len(packet.path),
                learned_path=packet.learned_path,
                path_confidence=packet.path_confidence,
                app_payload=packet.app_payload,
                min_forward_margin_q=packet.min_forward_margin_q,
                min_forward_margin_hop=packet.min_forward_margin_hop,
                repair_index=packet.repair_index,
            )
        else:
            packet_at_receiver = packet

        if packet.final_dst == BROADCAST_DST or packet.final_dst == receiver:
            self.sim.mark_delivered(packet.flow_id, receiver, packet_at_receiver)
            if packet.final_dst == receiver:
                if packet_at_receiver.path:
                    self.send_ack_on_reverse_path(receiver, packet_at_receiver)
                else:
                    self.send_direct_ack(receiver, packet_at_receiver)

        node = self.sim.nodes[receiver]
        if packet.ttl <= 1 or not node.can_relay:
            return
        if packet.final_dst != BROADCAST_DST and packet.final_dst == receiver:
            return

        forwarded = packet_at_receiver.with_ttl(packet.ttl - 1)
        pending = self.sim.transmit_later(receiver, forwarded, delay_s=self.flood_delay(receiver, rx))
        self.pending_fallback[pending_key] = pending


class MeshEcho(CalmMesh):
    """The named MeshEcho policy used by the ICC evaluation.

    ``CalmMesh`` remains available as a legacy CLI alias, but this class is
    the protocol identity used by the paper and all ICC-facing artifacts.
    """

    name = "meshecho"

    def path_confidence(self, path: Tuple[int, ...], inbound_confidence: float) -> float:
        if len(path) < 2:
            return clamp(inbound_confidence, 0.0, 1.0)
        hop_penalty = self.hop_penalty_per_hop if len(path) > 2 else 0.0
        return clamp(inbound_confidence - hop_penalty, 0.05, 0.98)


class MeshEchoCalibrated(MeshEcho):
    """Rank RREQ paths by their weakest model-inferred hop PRR."""

    name = "meshecho-calibrated"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["hop_penalty_per_hop"] = 0.0
        super().__init__(*args, **kwargs)

    def link_confidence(self, rx: RxInfo) -> float:
        return self.sim.prr_from_snr(rx.sinr_db)

    def path_confidence(self, path: Tuple[int, ...], inbound_confidence: float) -> float:
        del path
        return clamp(inbound_confidence, 0.0, 1.0)


class MeshEchoSR(MeshEchoCalibrated):
    """Source-local flood/route controller with ACK-confirmed route state."""

    name = "meshecho-sr"

    def __init__(
        self, *args: Any, ack_guard_s: float = 15.0,
        app_deadline_s: float = 30.0, rrep_wait_s: float = 10.0,
        mode: str = "sr",
        **kwargs: Any,
    ) -> None:
        if min(ack_guard_s, app_deadline_s, rrep_wait_s) <= 0.0:
            raise ValueError("SR deadlines must be positive")
        if mode not in SR_PROTOCOL_MODES.values():
            raise ValueError(f"unknown SR mode: {mode}")
        kwargs["route_miss_recovery_enabled"] = False
        super().__init__(*args, **kwargs)
        self.mode = mode
        self.name = next(name for name, candidate_mode in SR_PROTOCOL_MODES.items()
                         if candidate_mode == mode)
        self.ack_guard_s = ack_guard_s
        self.app_deadline_s = app_deadline_s
        self.rrep_wait_s = rrep_wait_s
        self.action_events: List[Dict[str, Any]] = []
        self.flow_actions: Dict[int, str] = {}
        self.flow_data_actions: Dict[int, str] = {}
        self.flow_sent_paths: Dict[int, Tuple[int, ...]] = {}
        self.flow_old_paths: Dict[int, Tuple[int, ...]] = {}
        self.flow_timeout_applied: Set[int] = set()
        self.destination_state: Dict[Tuple[int, int], SRDestinationState] = {}
        self.destination_last_used: Dict[Tuple[int, int], int] = {}
        self.state_touch_count = 0
        self.source_tokens: Dict[int, int] = {}
        self.source_app_counts: Dict[int, int] = {}

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.action_events = []
        self.flow_actions = {}
        self.flow_data_actions = {}
        self.flow_sent_paths = {}
        self.flow_old_paths = {}
        self.flow_timeout_applied = set()
        self.destination_state = {}
        self.destination_last_used = {}
        self.state_touch_count = 0
        self.source_tokens = {src: 1 for src in sim.nodes}
        self.source_app_counts = {src: 0 for src in sim.nodes}

    def source_state(self, src: int, dst: int) -> SRDestinationState:
        key = (src, dst)
        if key not in self.destination_state:
            source_keys = [item for item in self.destination_state if item[0] == src]
            if len(source_keys) >= 8:
                candidates = [
                    item for item in source_keys
                    if self.destination_state[item].pending_discovery_flow is None
                ] or source_keys
                oldest = min(candidates, key=lambda item: self.destination_last_used[item])
                pending_flow = self.destination_state[oldest].pending_discovery_flow
                if pending_flow is not None:
                    self.expire_discovery(
                        oldest[0], oldest[1], pending_flow,
                        reason="source-state-eviction",
                    )
                del self.destination_state[oldest]
                del self.destination_last_used[oldest]
                self.route_cache[src].pop(oldest[1], None)
            self.destination_state[key] = SRDestinationState()
        self.state_touch_count += 1
        self.destination_last_used[key] = self.state_touch_count
        return self.destination_state[key]

    def send_app(self, src: int, dst: int, flow_id: int) -> None:
        self.sim.metrics.register_flow(flow_id, src, dst, self.sim.now)
        state = self.source_state(src, dst)
        recent_sends = sum(when >= self.sim.now - 300.0 for when in state.send_times)
        state.send_times = (
            [when for when in state.send_times if when >= self.sim.now - 300.0]
            + [self.sim.now]
        )[-2:]
        self.source_app_counts[src] += 1
        if self.source_app_counts[src] % 10 == 0:
            self.source_tokens[src] = 1
        entry = self.get_route(src, dst) if dst != BROADCAST_DST else None
        eligible_discovery = (
            state.pending_discovery_flow is None
            and self.source_tokens[src] > 0
            and (
                state.last_discovery_at is None
                or self.sim.now - state.last_discovery_at >= 300.0
            )
        )
        if entry is None:
            cold_d_trigger = (
                dst != BROADCAST_DST
                and state.consecutive_f_misses >= 2
                and recent_sends >= 2
                and eligible_discovery
            )
            action = "D" if cold_d_trigger else "F"
            reason = "repeated-cold-misses" if action == "D" else "no-confirmed-route"
        elif state.consecutive_r_misses >= 2:
            action, reason = "F", "route-ack-misses"
        elif (
            self.sim.now - entry.created_at >= 180.0
            and (recent_sends >= 2 or self.mode == "periodic")
            and eligible_discovery
            and not state.had_r_miss_since_commit
        ):
            action, reason = "D", "aging-confirmed-route"
        else:
            action, reason = "R", "confirmed-route"
        # Research-only matched branch runs may replace the action at an
        # otherwise-D decision.  The original D decision remains the ledger
        # reference, so token/timestamp accounting stays comparable across
        # D, old-route R and useful-payload F branches.
        would_discover = action == "D"
        override = getattr(self, "source_action_overrides", {}).get(flow_id)
        if override is not None:
            if not would_discover:
                raise ValueError(
                    "source action override is only valid at a D decision"
                )
            if override not in {"D", "R", "F"}:
                raise ValueError(f"unknown matched source action: {override}")
            if override == "R" and entry is None:
                raise ValueError("matched R action requires a confirmed route")
            action = override
            reason = f"matched-override-{override}"
        if would_discover and self.mode == "fr":
            action = "F" if entry is None else "R"
            reason += "-fr-control"
        elif would_discover and self.mode == "trigger-f":
            action = "F"
            reason += "-trigger-f"
        self.flow_actions[flow_id] = action
        self.action_events.append(
            {"event": "decision", "time": self.sim.now, "flow_id": flow_id,
             "src": src, "dst": dst, "action": action, "reason": reason}
        )
        if would_discover and self.mode != "fr":
            self.source_tokens[src] -= 1
            state.last_discovery_at = self.sim.now
        if action == "D":
            self.flow_old_paths[flow_id] = entry.path if entry is not None else ()
            state.pending_discovery_flow = flow_id
            self.pending_data[(src, dst)] = [flow_id]
            self.start_route_discovery(src, dst, flow_id)
            return
        if action == "R" and entry is not None:
            self.sim.metrics.route_cache_hits += 1
            self.send_data_on_path(src, dst, flow_id, entry)
            return
        self.sim.metrics.route_cache_misses += 1
        self.send_flood(src, dst, flow_id)

    def send_flood(self, src: int, dst: int, flow_id: int) -> None:
        self.flow_data_actions[flow_id] = "F"
        packet = Packet(
            kind="FLOOD",
            flow_id=flow_id,
            origin=src,
            final_dst=dst,
            ttl=self.useful_flood_ttl(),
            created_at=self.sim.now,
            protocol=self.name,
            request_id=flow_id,
            path=(src,),
            min_forward_margin_q=self.source_forward_margin_q(),
            min_forward_margin_hop=self.source_forward_margin_hop(),
        )
        self.seen_floods[src].add(packet.flood_key)
        self.sim.transmit_later(src, packet, delay_s=0.0)

    def useful_flood_ttl(self) -> int:
        return self.sim.max_hops

    def source_forward_margin_q(self) -> Optional[int]:
        return None

    def source_forward_margin_hop(self) -> Optional[int]:
        return None

    def send_data_on_path(
        self, src: int, dst: int, flow_id: int, entry: RouteEntry,
        candidate: bool = False,
    ) -> None:
        self.flow_data_actions[flow_id] = "D-candidate" if candidate else "R"
        if not candidate:
            state = self.destination_state[(src, dst)]
            state.recent_r_flows = (state.recent_r_flows + [flow_id])[-2:]
            state.consecutive_r_misses = self.trailing_r_misses(state)
        packet = Packet(
            kind="DATA", flow_id=flow_id, origin=src, final_dst=dst,
            ttl=self.sim.max_hops,
            created_at=self.sim.metrics.flows[flow_id].created_at,
            protocol=self.name, request_id=flow_id, path=entry.path,
            min_forward_margin_q=self.source_forward_margin_q(),
            min_forward_margin_hop=self.source_forward_margin_hop(),
            **self.r_data_wire_fields(src, dst, flow_id, entry, candidate),
        )
        self.flow_sent_paths[flow_id] = entry.path
        self.sim.transmit_later(src, packet, delay_s=0.0)

    def r_data_wire_fields(
        self, src: int, dst: int, flow_id: int, entry: RouteEntry,
        candidate: bool,
    ) -> Dict[str, int]:
        return {}

    @staticmethod
    def trailing_r_misses(state: SRDestinationState) -> int:
        count = 0
        for recent_flow in reversed(state.recent_r_flows):
            if recent_flow not in state.r_miss_flows:
                break
            count += 1
        return count

    def on_rrep(self, receiver: int, packet: Packet) -> None:
        if not self.path_next_hop_matches(receiver, packet):
            return
        advanced = packet.advance_path()
        if receiver != packet.final_dst:
            self.sim.transmit_later(receiver, advanced, delay_s=0.0)
            return
        learned = packet.learned_path
        if not learned or learned[0] != receiver:
            return
        dst = learned[-1]
        state = self.destination_state.get((receiver, dst))
        queued = self.pending_data.get((receiver, dst), [])
        if state is None or state.pending_discovery_flow != packet.flow_id or queued != [packet.flow_id]:
            return
        self.pending_data.pop((receiver, dst), None)
        state.pending_discovery_flow = None
        self.sim.metrics.route_discovery_successes += 1
        self.action_events.append(
            {"event": "candidate", "time": self.sim.now, "flow_id": packet.flow_id,
             "src": receiver, "dst": dst, "action": "D", "path": learned,
             "old_path": self.flow_old_paths.get(packet.flow_id, ()),
             "different_path": bool(self.flow_old_paths.get(packet.flow_id))
             and learned != self.flow_old_paths[packet.flow_id]}
        )
        candidate = RouteEntry(self.sim.now, self.sim.now + self.route_ttl_s,
                               learned, packet.path_confidence)
        self.send_data_on_path(receiver, dst, packet.flow_id, candidate, candidate=True)

    def finish_failed_route_discovery(self, key: Tuple[int, int, int]) -> None:
        # Candidate collection closes at the destination; the source learns
        # failure only when its own RREP timer expires.
        del key

    def fallback_pending_discovery(self, key: Tuple[int, int, int]) -> None:
        src, dst, flow_id = key
        queued = self.pending_data.pop((src, dst), [])
        state = self.destination_state.get((src, dst))
        if state is not None and state.pending_discovery_flow == flow_id:
            state.pending_discovery_flow = None
        for queued_flow_id in queued:
            entry = self.get_route(src, dst)
            if entry is None:
                self.send_flood(src, dst, queued_flow_id)
            else:
                self.send_data_on_path(src, dst, queued_flow_id, entry)

    def expire_discovery(
        self, src: int, dst: int, flow_id: int,
        reason: str = "rrep-timeout",
    ) -> None:
        state = self.destination_state.get((src, dst))
        if state is None or state.pending_discovery_flow != flow_id:
            return
        self.action_events.append(
            {"event": "timeout", "time": self.sim.now, "flow_id": flow_id,
             "src": src, "dst": dst, "action": "D", "reason": reason}
        )
        self.fallback_pending_discovery((src, dst, flow_id))

    def on_transmit(self, sender: int, packet: Packet, start: float, end: float) -> None:
        if (packet.kind == "RREQ" and sender == packet.origin
                and self.flow_actions.get(packet.flow_id) == "D"):
            wait_s = self.sim.route_discovery_rrep_wait_s(
                self.rrep_wait_s, self.discovery_window_for(packet.flow_id),
                self.flood_base_delay_s + self.flood_jitter_s + 0.35,
            )
            self.sim.schedule(
                start + wait_s, "protocol_timer",
                lambda src=sender, dst=packet.final_dst, flow_id=packet.flow_id:
                    self.expire_discovery(src, dst, flow_id),
            )
            return
        if packet.kind not in {"DATA", "FLOOD"} or sender != packet.origin:
            return
        flow = self.sim.metrics.flows.get(packet.flow_id)
        if flow is None:
            return
        deadline = start + self.ack_guard_s
        self.sim.schedule(
            deadline, "protocol_timer",
            lambda flow_id=packet.flow_id: self.expire_data_ack(flow_id),
        )

    def expire_data_ack(self, flow_id: int) -> None:
        flow = self.sim.metrics.flows.get(flow_id)
        if flow is None or flow.acked_at is not None or flow_id in self.flow_timeout_applied:
            return
        self.flow_timeout_applied.add(flow_id)
        state = self.destination_state.get((flow.src, flow.dst))
        if state is None:
            return
        actual_action = self.flow_data_actions.get(flow_id)
        if actual_action == "R" and self.route_miss_is_current(flow_id, state):
            state.r_miss_flows.add(flow_id)
            state.consecutive_r_misses = self.trailing_r_misses(state)
            state.had_r_miss_since_commit = True
        elif actual_action == "F":
            state.f_miss_flows.add(flow_id)
            state.consecutive_f_misses += 1
        self.action_events.append(
            {"event": "timeout", "time": self.sim.now, "flow_id": flow_id,
             "src": flow.src, "dst": flow.dst, "action": self.flow_actions[flow_id],
             "reason": "source-ack-timeout"}
        )

    def route_miss_is_current(self, flow_id: int, state: SRDestinationState) -> bool:
        return True

    def on_receive(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if packet.kind == "FLOOD":
            self.on_fallback(receiver, packet, rx)
        else:
            super().on_receive(receiver, packet, rx)

    def on_ack_packet(self, receiver: int, packet: Packet) -> None:
        if receiver == packet.final_dst:
            flow = self.sim.metrics.flows.get(packet.flow_id)
            if (
                flow is None or packet.request_id != packet.flow_id
                or receiver != flow.src
                or self.sim.now > flow.created_at + self.app_deadline_s
                or self.flow_data_actions.get(packet.flow_id) is None
            ):
                return
            if (
                self.flow_data_actions[packet.flow_id] != "F"
                and packet.path != self.flow_sent_paths.get(packet.flow_id)
            ):
                return
        super().on_ack_packet(receiver, packet)

    def on_ack(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        flow = self.sim.metrics.flows[flow_id]
        if packet.request_id != flow_id or receiver != flow.src or len(packet.path) < 2:
            return
        state = self.destination_state.get((receiver, flow.dst))
        if state is None:
            return
        data_action = self.flow_data_actions.get(flow_id)
        if data_action == "R":
            state.r_miss_flows.discard(flow_id)
            state.consecutive_r_misses = self.trailing_r_misses(state)
            state.had_r_miss_since_commit = bool(state.r_miss_flows)
            return
        if flow_id < state.last_commit_flow:
            return
        if data_action == "D-candidate" and packet.path != self.flow_sent_paths.get(flow_id):
            return
        state.last_commit_flow = flow_id
        state.consecutive_f_misses = 0
        state.consecutive_r_misses = 0
        state.had_r_miss_since_commit = False
        state.f_miss_flows.clear()
        state.r_miss_flows.clear()
        state.recent_r_flows.clear()
        self.route_cache[receiver][flow.dst] = RouteEntry(
            created_at=now,
            expires_at=now + self.route_ttl_s,
            path=packet.path,
            confidence=1.0,
        )
        self.action_events.append(
            {"event": "commit", "time": now, "flow_id": flow_id,
             "src": receiver, "dst": flow.dst, "action": self.flow_actions[flow_id],
             "path": packet.path,
             "replaced_confirmed_path": bool(self.flow_old_paths.get(flow_id))
             and packet.path != self.flow_old_paths[flow_id]}
        )


class _DrcSeenTable:
    """Bounded duplicate table used by the independent DRC core."""

    def __init__(self, max_entries: int = 128, ttl_s: float = 30.0) -> None:
        self.max_entries = max_entries
        self.ttl_s = ttl_s
        self.entries: "OrderedDict[Tuple[Any, ...], float]" = OrderedDict()

    def _purge(self, now: float) -> None:
        expired = [key for key, seen_at in self.entries.items()
                   if now - seen_at >= self.ttl_s]
        for key in expired:
            self.entries.pop(key, None)

    def contains(self, key: Tuple[Any, ...], now: float) -> bool:
        self._purge(now)
        seen_at = self.entries.get(key)
        if seen_at is None:
            return False
        self.entries.move_to_end(key)
        return True

    def add(self, key: Tuple[Any, ...], now: float) -> None:
        self._purge(now)
        self.entries.pop(key, None)
        while len(self.entries) >= self.max_entries:
            self.entries.popitem(last=False)
        self.entries[key] = now


class MeshEchoDRC(RoutingProtocol):
    """Deadline-reserved source controller, independent of MeshEchoSR.

    DRC retains only the tested physical forwarding primitives. Its source
    action is evaluated by ``Simulator.on_tx_request`` at the actual queue
    available time, then reserves at most one useful FLOOD recovery under the
    original application deadline. It has no RREQ/RREP discovery branch,
    route-age trigger, source token, or inherited miss selector.
    """

    name = "meshecho-drc"

    def __init__(
        self,
        *,
        mode: str = "drc",
        route_ttl_s: float = 600.0,
        flood_base_delay_s: float = 0.45,
        flood_jitter_s: float = 0.65,
        app_deadline_s: float = 30.0,
        safety_margin_s: float = 0.25,
        fixed_guard_s: float = 15.0,
    ) -> None:
        if mode not in set(DRC_PROTOCOL_MODES.values()):
            raise ValueError(f"unknown DRC mode: {mode}")
        if min(route_ttl_s, app_deadline_s) <= 0.0:
            raise ValueError("DRC route TTL and deadline must be positive")
        if min(flood_base_delay_s, flood_jitter_s, safety_margin_s) < 0.0:
            raise ValueError("DRC timing values must be nonnegative")
        self.mode = mode
        self.name = next(
            name for name, candidate in DRC_PROTOCOL_MODES.items()
            if candidate == mode
        )
        self.route_ttl_s = route_ttl_s
        self.flood_base_delay_s = flood_base_delay_s
        self.flood_jitter_s = flood_jitter_s
        self.app_deadline_s = app_deadline_s
        self.safety_margin_s = safety_margin_s
        self.fixed_guard_s = fixed_guard_s
        self.route_states: Dict[int, DrcSourceState] = {}
        self.flow_states: Dict[int, DrcSourceState] = {}
        self.flow_records: Dict[int, Any] = {}
        self.flow_pending: Dict[int, PendingSend] = {}
        self.recovery_pending: Dict[int, PendingSend] = {}
        self.route_cache: Dict[int, Dict[int, RouteEntry]] = {}
        self.seen_floods: Dict[int, _DrcSeenTable] = {}
        self.pending_fallback: "OrderedDict[Tuple[int, Tuple[Any, ...]], PendingSend]" = OrderedDict()
        self.action_events: List[Dict[str, Any]] = []
        self.flow_actions: Dict[int, str] = {}
        self.flow_sent_paths: Dict[int, Tuple[int, ...]] = {}
        self.flow_ack_paths: Dict[int, Tuple[int, ...]] = {}
        self.guard_scheduled: Set[int] = set()
        self.deadline_scheduled: Set[int] = set()
        self.retired_flows: Set[int] = set()
        self.last_commit_flow: Dict[Tuple[int, int], int] = {}

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.route_states = {
            node_id: DrcSourceState() for node_id in sim.nodes
        }
        self.flow_states = {}
        self.flow_records = {}
        self.flow_pending = {}
        self.recovery_pending = {}
        self.route_cache = {node_id: {} for node_id in sim.nodes}
        self.seen_floods = {
            node_id: _DrcSeenTable() for node_id in sim.nodes
        }
        self.pending_fallback = OrderedDict()
        self.action_events = []
        self.flow_actions = {}
        self.flow_sent_paths = {}
        self.flow_ack_paths = {}
        self.guard_scheduled = set()
        self.deadline_scheduled = set()
        self.retired_flows = set()
        self.last_commit_flow = {}

    def _state(self, src: int) -> DrcSourceState:
        return self.route_states[src]

    @staticmethod
    def _seen_key(packet: Packet) -> Tuple[Any, ...]:
        return (
            packet.kind, packet.origin, packet.flow_id, packet.request_id,
            packet.repair_index,
        )

    def _store_pending_fallback(
        self, receiver: int, key: Tuple[Any, ...], pending: PendingSend,
    ) -> None:
        """Keep relay-side pending FLOOD state within the device contract."""

        pending_key = (receiver, key)
        self.pending_fallback.pop(pending_key, None)
        self.pending_fallback[pending_key] = pending
        node_keys = [
            candidate for candidate in self.pending_fallback
            if candidate[0] == receiver
        ]
        while len(node_keys) > DRC_MAX_PENDING_FALLBACKS_PER_NODE:
            evicted_key = node_keys.pop(0)
            evicted = self.pending_fallback.pop(evicted_key, None)
            if evicted is not None and not evicted.committed:
                evicted.canceled = True
                self.action_events.append({
                    "event": "state-eviction", "time": self.sim.now,
                    "node": receiver, "state": "pending_fallback",
                    "reason": "capacity",
                })

    def _route_record(self, src: int, dst: int, now: float):
        return self._state(src).get_route(dst, now=now)

    def _mirror_route(self, src: int, record: Any) -> None:
        self.route_cache[src][record.destination] = RouteEntry(
            created_at=record.last_accepted_ack_at or self.sim.now,
            expires_at=record.expires_at,
            path=record.path,
            confidence=1.0,
        )

    def _remove_route(self, src: int, dst: int) -> None:
        self._state(src).routes.pop(dst, None)
        self.route_cache[src].pop(dst, None)

    def _route_bound_s(self, src: int, dst: int, flow_id: int, path: Tuple[int, ...]) -> float:
        hops = max(1, len(path) - 1)
        data = Packet(
            kind="DATA", flow_id=flow_id, origin=src, final_dst=dst,
            ttl=self.sim.max_hops, created_at=self.sim.now,
            protocol=self.name, request_id=flow_id, path=path,
        )
        ack = Packet(
            kind="ACK", flow_id=flow_id, origin=dst, final_dst=src,
            ttl=self.sim.max_hops, created_at=self.sim.now,
            protocol=self.name, request_id=flow_id, path=path,
            path_index=max(0, len(path) - 2), app_payload=False,
        )
        return hops * (
            self.sim.radio.packet_toa_s(data) + self.sim.radio.packet_toa_s(ack)
        ) + self.safety_margin_s

    def _flood_bound_s(
        self, src: int, dst: int, flow_id: int, *, marked: bool = False,
    ) -> float:
        hops = max(1, self.sim.max_hops)
        max_path = tuple(range(hops + 1))
        flood = Packet(
            kind="FLOOD", flow_id=flow_id, origin=src, final_dst=dst,
            ttl=hops, created_at=self.sim.now, protocol=self.name,
            request_id=flow_id, path=max_path,
            repair_index=2 if marked else None,
        )
        ack = Packet(
            kind="ACK", flow_id=flow_id, origin=dst, final_dst=src,
            ttl=hops, created_at=self.sim.now, protocol=self.name,
            request_id=flow_id, path=max_path,
            path_index=max(0, len(max_path) - 2), app_payload=False,
            repair_index=2 if marked else None,
        )
        delay_bound = self.flood_base_delay_s + self.flood_jitter_s + 0.35
        return (
            hops * self.sim.radio.packet_toa_s(flood)
            + max(0, hops - 1) * delay_bound
            + hops * self.sim.radio.packet_toa_s(ack)
            + self.safety_margin_s
        )

    def _placeholder(
        self, src: int, dst: int, flow_id: int, kind: str,
    ) -> Packet:
        return Packet(
            kind=kind, flow_id=flow_id, origin=src, final_dst=dst,
            ttl=self.sim.max_hops, created_at=self.sim.metrics.flows[flow_id].created_at,
            protocol=self.name, request_id=flow_id, path=(src,), app_payload=False,
        )

    def _decision_event(
        self, flow: Any, decision: DrcDecision, start: float,
        route_bound_s: float, flood_bound_s: float,
    ) -> None:
        self.action_events.append({
            "event": "decision", "time": start, "flow_id": flow.flow_id,
            "src": flow.source, "dst": flow.destination,
            "action": decision.action.value, "reason": decision.reason,
            "route_bound_s": route_bound_s, "flood_bound_s": flood_bound_s,
            "deadline": flow.deadline,
            "route_generation": flow.route_generation,
        })

    def send_app(self, src: int, dst: int, flow_id: int) -> None:
        self.sim.metrics.register_flow(flow_id, src, dst, self.sim.now)
        if dst == BROADCAST_DST:
            packet = Packet(
                kind="FLOOD", flow_id=flow_id, origin=src, final_dst=dst,
                ttl=self.sim.max_hops, created_at=self.sim.now,
                protocol=self.name, request_id=flow_id, path=(src,),
            )
            self.seen_floods[src].add(self._seen_key(packet), self.sim.now)
            self.sim.transmit_later(src, packet, delay_s=0.0)
            return

        state = self._state(src)
        registration = state.register_flow(
            flow_id, source=src, destination=dst,
            enqueue_at=self.sim.now, deadline_s=self.app_deadline_s,
        )
        if not registration.accepted or registration.flow is None:
            self.action_events.append({
                "event": "decision", "time": self.sim.now, "flow_id": flow_id,
                "src": src, "dst": dst, "action": "DROP",
                "reason": registration.reason,
            })
            return
        flow = registration.flow
        self.flow_states[flow_id] = state
        self.flow_records[flow_id] = flow
        placeholder = self._placeholder(src, dst, flow_id, "DRC_REQUEST")
        self.flow_pending[flow_id] = self.sim.transmit_later(
            src, placeholder, delay_s=0.0,
        )
        if flow_id not in self.deadline_scheduled:
            self.deadline_scheduled.add(flow_id)
            self.sim.schedule(
                flow.deadline, "protocol_timer",
                lambda flow_id=flow_id: self._expire_deadline(flow_id),
            )

    def on_tx_request(
        self, sender: int, packet: Packet, start: float, pending: PendingSend,
    ) -> Optional[Packet]:
        if packet.kind == "DRC_REQUEST":
            return self._start_initial(sender, packet.flow_id, start, pending)
        if packet.kind == "DRC_RECOVERY_REQUEST":
            return self._start_recovery(sender, packet.flow_id, start, pending)
        return packet

    def _start_initial(
        self, sender: int, flow_id: int, start: float, pending: PendingSend,
    ) -> Optional[Packet]:
        del pending
        flow = self.flow_records.get(flow_id)
        state = self.flow_states.get(flow_id)
        if flow is None or state is None or flow_id in self.retired_flows:
            return None
        if flow.acked_at is not None or start >= flow.deadline:
            self.action_events.append({
                "event": "decision", "time": start, "flow_id": flow_id,
                "src": flow.source, "dst": flow.destination,
                "action": DrcAction.DROP_DEADLINE_INFEASIBLE.value,
                "reason": "deadline-infeasible",
                "deadline": flow.deadline,
            })
            self.action_events.append({
                "event": "no-start", "time": start, "flow_id": flow_id,
                "src": flow.source, "dst": flow.destination,
                "action": "DROP", "reason": "deadline-infeasible",
            })
            return None
        record = self._route_record(flow.source, flow.destination, start)
        route_bound_s = (
            self._route_bound_s(flow.source, flow.destination, flow_id, record.path)
            if record is not None else 0.0
        )
        flood_bound_s = self._flood_bound_s(
            flow.source, flow.destination, flow_id, marked=False,
        )
        observation = state.observation_for(
            flow_id, now=start, route_bound_s=route_bound_s,
            flood_bound_s=flood_bound_s,
        )
        decision = choose_start_action(observation)
        if self.mode == "all-f":
            if start + flood_bound_s <= flow.deadline:
                decision = DrcDecision(DrcAction.F_INITIAL, "all-f-control")
            else:
                decision = DrcDecision(
                    DrcAction.DROP_DEADLINE_INFEASIBLE,
                    "all-f-deadline-infeasible",
                )
        elif self.mode == "r-only" and decision.action is DrcAction.R_RESERVED:
            decision = DrcDecision(DrcAction.R_ONLY, "r-only-control")
        elif self.mode == "fixed-guard" and decision.action is DrcAction.R_RESERVED:
            decision = DrcDecision(
                DrcAction.R_RESERVED, "fixed-guard-control",
                guard_at=start + self.fixed_guard_s,
            )
        if decision.action is DrcAction.DROP_DEADLINE_INFEASIBLE:
            self._decision_event(flow, decision, start, route_bound_s, flood_bound_s)
            return None
        state.start_initial(flow_id, decision, now=start)
        self._decision_event(flow, decision, start, route_bound_s, flood_bound_s)
        self.flow_actions[flow_id] = decision.action.value
        if decision.action in {DrcAction.R_RESERVED, DrcAction.R_ONLY}:
            if record is None:
                return None
            self.flow_sent_paths[flow_id] = record.path
            return Packet(
                kind="DATA", flow_id=flow_id, origin=flow.source,
                final_dst=flow.destination, ttl=self.sim.max_hops,
                created_at=flow.enqueue_at, protocol=self.name,
                request_id=flow_id, path=record.path,
            )
        self.flow_sent_paths[flow_id] = (flow.source,)
        return Packet(
            kind="FLOOD", flow_id=flow_id, origin=flow.source,
            final_dst=flow.destination, ttl=self.sim.max_hops,
            created_at=flow.enqueue_at, protocol=self.name,
            request_id=flow_id, path=(flow.source,),
        )

    def _start_recovery(
        self, sender: int, flow_id: int, start: float, pending: PendingSend,
    ) -> Optional[Packet]:
        del sender, pending
        flow = self.flow_records.get(flow_id)
        state = self.flow_states.get(flow_id)
        if flow is None or state is None or flow_id in self.retired_flows:
            return None
        if self.mode in {"no-rescue", "r-only"}:
            state.cancel_recovery(flow_id)
            self.action_events.append({
                "event": "no-start", "time": start, "flow_id": flow_id,
                "src": flow.source, "dst": flow.destination,
                "action": DrcAction.F_RECOVERY.value,
                "reason": "recovery-disabled-control",
            })
            return None
        route = self._route_record(flow.source, flow.destination, start)
        route_bound_s = (
            self._route_bound_s(flow.source, flow.destination, flow_id, route.path)
            if route is not None else 0.0
        )
        flood_bound_s = self._flood_bound_s(
            flow.source, flow.destination, flow_id, marked=True,
        )
        decision = choose_start_action(state.observation_for(
            flow_id, now=start, route_bound_s=route_bound_s,
            flood_bound_s=flood_bound_s,
        ))
        self._decision_event(flow, decision, start, route_bound_s, flood_bound_s)
        if decision.action is not DrcAction.F_RECOVERY:
            state.cancel_recovery(flow_id)
            return None
        state.start_recovery(flow_id, decision, now=start)
        self.flow_actions[flow_id] = decision.action.value
        self.action_events.append({
            "event": "recovery-start", "time": start, "flow_id": flow_id,
            "src": flow.source, "dst": flow.destination,
            "action": decision.action.value, "repair_index": 2,
        })
        return Packet(
            kind="FLOOD", flow_id=flow_id, origin=flow.source,
            final_dst=flow.destination, ttl=self.sim.max_hops,
            created_at=flow.enqueue_at, protocol=self.name,
            request_id=flow_id, path=(flow.source,), repair_index=2,
        )

    def on_transmit(self, sender: int, packet: Packet, start: float, end: float) -> None:
        del end
        if sender != packet.origin:
            self.pending_fallback.pop((sender, self._seen_key(packet)), None)
        if sender != packet.origin:
            return
        flow = self.flow_records.get(packet.flow_id)
        if flow is None:
            return
        if packet.kind == "DATA" and packet.repair_index is None:
            if flow.initial_action is DrcAction.R_RESERVED and flow.flow_id not in self.guard_scheduled:
                self.guard_scheduled.add(flow.flow_id)
                if flow.guard_at is not None and flow.guard_at < flow.deadline:
                    self.sim.schedule(
                        flow.guard_at, "protocol_timer",
                        lambda flow_id=flow.flow_id: self._arm_recovery(flow_id),
                    )
        elif packet.kind == "FLOOD" and packet.repair_index is None:
            return

    def _arm_recovery(self, flow_id: int) -> None:
        flow = self.flow_records.get(flow_id)
        state = self.flow_states.get(flow_id)
        if flow is None or state is None or flow_id in self.retired_flows:
            return
        if flow.acked_at is not None or self.mode in {"no-rescue", "r-only"}:
            return
        if not state.arm_recovery(flow_id, now=self.sim.now):
            self.action_events.append({
                "event": "recovery-skip", "time": self.sim.now,
                "flow_id": flow_id, "reason": "stale-route-generation",
            })
            return
        placeholder = self._placeholder(
            flow.source, flow.destination, flow_id, "DRC_RECOVERY_REQUEST",
        )
        self.recovery_pending[flow_id] = self.sim.transmit_later(
            flow.source, placeholder, delay_s=0.0,
        )
        self.action_events.append({
            "event": "recovery-request", "time": self.sim.now,
            "flow_id": flow_id, "action": DrcAction.F_RECOVERY.value,
        })

    def _expire_deadline(self, flow_id: int) -> None:
        flow = self.flow_records.get(flow_id)
        state = self.flow_states.get(flow_id)
        if flow is None or state is None or flow_id in self.retired_flows:
            return
        if flow.acked_at is not None:
            self._retire(flow_id)
            return
        pending = self.flow_pending.pop(flow_id, None)
        if pending is not None:
            pending.canceled = True
        pending = self.recovery_pending.pop(flow_id, None)
        if pending is not None:
            pending.canceled = True
        record = state.routes.get(flow.destination)
        if record is not None and flow.initial_action in {
            DrcAction.R_RESERVED, DrcAction.R_ONLY,
        } and record.generation == flow.route_generation:
            evicted = state.record_in_deadline_miss(
                flow.destination, flow.route_generation,
            )
            if evicted:
                self._remove_route(flow.source, flow.destination)
            else:
                self._mirror_route(flow.source, record)
        self.action_events.append({
            "event": "timeout", "time": self.sim.now, "flow_id": flow_id,
            "src": flow.source, "dst": flow.destination,
            "reason": "deadline-censor",
        })
        self._retire(flow_id)

    def _retire(self, flow_id: int) -> None:
        state = self.flow_states.get(flow_id)
        if state is not None:
            state.active_flows.pop(flow_id, None)
        self.retired_flows.add(flow_id)
        self.flow_pending.pop(flow_id, None)
        self.recovery_pending.pop(flow_id, None)

    def _source_ack_rejection_reason(
        self, flow: Any, packet: Packet, rx: RxInfo,
    ) -> Optional[str]:
        if packet.kind != "ACK":
            return "wrong-kind"
        if packet.request_id != flow.flow_id:
            return "flow-request-mismatch"
        if packet.origin != flow.destination or packet.final_dst != flow.source:
            return "endpoint-mismatch"
        if packet.app_payload:
            return "ack-has-payload"
        if self.sim.now > flow.deadline:
            return "late"
        if packet.path_index != 0:
            return "path-index-mismatch"
        if len(packet.path) < 2 or len(packet.path) > self.sim.max_hops + 1:
            return "path-length-mismatch"
        if packet.path[0] != flow.source or packet.path[-1] != flow.destination:
            return "path-endpoint-mismatch"
        if len(set(packet.path)) != len(packet.path):
            return "looped-path"
        if rx.sender != packet.path[1]:
            return "path-or-sender-mismatch"
        marker = packet.repair_index
        if marker not in {None, 2}:
            return "marker-mismatch"
        if marker == 2:
            if flow.recovery_state is not RecoveryState.STARTED:
                return "recovery-not-started"
            if flow.flow_id < self.last_commit_flow.get(
                (flow.source, flow.destination), -1
            ):
                return "stale-generation"
        elif flow.initial_action in {DrcAction.R_RESERVED, DrcAction.R_ONLY}:
            if packet.path != flow.initial_path:
                return "initial-path-mismatch"
            record = self._route_record(flow.source, flow.destination, self.sim.now)
            if record is None or record.generation != flow.route_generation:
                return "route-generation-mismatch"
        return None

    def _valid_source_ack(self, flow: Any, packet: Packet, rx: RxInfo) -> bool:
        return self._source_ack_rejection_reason(flow, packet, rx) is None

    def on_receive(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if packet.kind == "DATA":
            self._on_data(receiver, packet, rx)
        elif packet.kind == "FLOOD":
            self._on_flood(receiver, packet, rx)
        elif packet.kind == "ACK":
            self._on_ack_packet(receiver, packet, rx)

    def _on_data(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        del rx
        next_index = packet.path_index + 1
        if next_index >= len(packet.path) or packet.path[next_index] != receiver:
            return
        advanced = packet.advance_path()
        if receiver == packet.final_dst:
            self.sim.mark_delivered(packet.flow_id, receiver, advanced)
            self.send_ack_on_reverse_path(receiver, advanced)
            return
        if packet.ttl <= 1 or not self.sim.nodes[receiver].can_relay:
            return
        self.sim.transmit_later(receiver, advanced.with_ttl(packet.ttl - 1), 0.0)

    def _flood_delay(
        self, receiver: int, rx: RxInfo, packet: Optional[Packet] = None,
    ) -> float:
        margin = rx.snr_db - required_snr_db(self.sim.radio.sf)
        weak_penalty = clamp((5.0 - margin) / 10.0, 0.0, 1.0) * 0.35
        role_discount = 0.15 if self.sim.nodes[receiver].role == "repeater" else 0.0
        if packet is None:
            # Compatibility for callers outside the DRC forwarding path.  DRC
            # itself always supplies the packet so paired arms do not consume
            # an event-order-sensitive shared RNG stream.
            jitter = self.sim.random.random()
        else:
            context = (
                self.sim.seed, packet.kind, packet.origin, packet.final_dst,
                packet.flow_id, packet.request_id, packet.repair_index,
                receiver, packet.path_index, tuple(packet.path),
            )
            jitter = random.Random(repr(context)).random()
        return max(
            0.05,
            self.flood_base_delay_s + weak_penalty
            + jitter * self.flood_jitter_s - role_discount,
        )

    def _on_flood(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        key = self._seen_key(packet)
        pending_key = (receiver, key)
        if self.seen_floods[receiver].contains(key, self.sim.now):
            pending = self.pending_fallback.get(pending_key)
            if pending is not None and not pending.canceled:
                pending.canceled = True
                self.pending_fallback.pop(pending_key, None)
                self.sim.metrics.suppressed_forwards += 1
            self.sim.metrics.duplicate_rx += 1
            return
        self.seen_floods[receiver].add(key, self.sim.now)
        packet_at_receiver = replace(
            packet,
            path=packet.path + (receiver,),
            path_index=len(packet.path),
        )
        if packet.final_dst == BROADCAST_DST or packet.final_dst == receiver:
            self.sim.mark_delivered(packet.flow_id, receiver, packet_at_receiver)
            if packet.final_dst == receiver:
                self.send_ack_on_reverse_path(receiver, packet_at_receiver)
        node = self.sim.nodes[receiver]
        if packet.ttl <= 1 or not node.can_relay:
            return
        if packet.final_dst != BROADCAST_DST and packet.final_dst == receiver:
            return
        forwarded = packet_at_receiver.with_ttl(packet.ttl - 1)
        pending = self.sim.transmit_later(
            receiver, forwarded, delay_s=self._flood_delay(receiver, rx, packet),
        )
        self._store_pending_fallback(receiver, key, pending)

    def _on_ack_packet(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        index = packet.path_index
        if (
            not 0 <= index < len(packet.path)
            or packet.path[index] != receiver
            or index + 1 >= len(packet.path)
            or packet.path[index + 1] != rx.sender
        ):
            if receiver == packet.final_dst:
                self.sim.record_ack_provenance(
                    packet, rx, receiver=receiver, accepted=False,
                    rejection_reason="path-or-sender-mismatch",
                    deadline_at=None,
                )
            return
        if receiver == packet.final_dst:
            flow = self.flow_records.get(packet.flow_id)
            if flow is None:
                self.sim.record_ack_provenance(
                    packet, rx, receiver=receiver, accepted=False,
                    rejection_reason="unknown-flow",
                    deadline_at=None,
                )
                return
            rejection_reason = self._source_ack_rejection_reason(flow, packet, rx)
            self.sim.record_ack_provenance(
                packet, rx, receiver=receiver,
                accepted=rejection_reason is None,
                rejection_reason=rejection_reason,
                route_generation=flow.route_generation,
                accepted_at=self.sim.now if rejection_reason is None else None,
                deadline_at=flow.deadline,
            )
            if rejection_reason is not None:
                return
            self.sim.mark_acknowledged(packet.flow_id, receiver, packet)
            return
        if packet.ttl <= 1:
            return
        forwarded = packet.retreat_path().with_ttl(packet.ttl - 1)
        self.sim.transmit_later(receiver, forwarded, delay_s=0.0)

    def on_ack(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        del receiver
        flow = self.flow_records.get(flow_id)
        state = self.flow_states.get(flow_id)
        if flow is None or state is None or flow_id in self.retired_flows:
            return
        if packet.repair_index in {None, 2} and packet.repair_index == 2:
            if flow_id < self.last_commit_flow.get(
                (flow.source, flow.destination), -1
            ):
                return
        if not state.accept_valid_ack(
            flow_id, packet.path, now=now,
            marker=packet.repair_index, route_ttl_s=self.route_ttl_s,
        ):
            return
        self.flow_ack_paths[flow_id] = packet.path
        pending = self.recovery_pending.pop(flow_id, None)
        if pending is not None and not pending.committed:
            pending.canceled = True
        record = state.routes.get(flow.destination)
        key = (flow.source, flow.destination)
        if record is not None:
            self.last_commit_flow[key] = flow_id
            self._mirror_route(flow.source, record)
        # The provenance row is created at physical ACK reception, before
        # ``accept_valid_ack`` can install a route learned from an initial F.
        # Fill the post-commit generation now so the raw evidence can explain
        # both the decision-time generation and the state transition it caused.
        for provenance in reversed(self.sim.ack_provenance):
            if (
                provenance.get("accepted")
                and provenance.get("flow_id") == flow_id
                and provenance.get("ack_rx_at") == now
                and tuple(provenance.get("reverse_path", ())) == tuple(packet.path)
            ):
                provenance["route_generation_after"] = flow.route_generation
                break
        self.action_events.append({
            "event": "ack-accept", "time": now, "flow_id": flow_id,
            "src": flow.source, "dst": flow.destination,
            "action": self.flow_actions.get(flow_id), "path": packet.path,
            "repair_index": packet.repair_index,
        })
        self._retire(flow_id)


class MeshEchoCPR(MeshEchoDRC):
    """Cost-responsive recovery successor with ACK-terminated relay state.

    CPR has its own protocol identity and will not be included in the DRC
    control matrix.  The class initially reuses only the physical forwarding
    substrate and route bookkeeping; source recovery and relay cancellation
    are implemented by CPR-specific hooks below.
    """

    name = "meshecho-cpr"

    def __init__(self, *args: Any, cancel_on_ack: bool = True, **kwargs: Any) -> None:
        # Reuse only the PHY-facing route/flood helpers.  CPR has independent
        # source lifecycle and ACK validation below; it does not call DRC's
        # reservation/fixed-guard selector.
        super().__init__(*args, mode="drc", **kwargs)
        self.cancel_on_ack = bool(cancel_on_ack)
        self.name = "meshecho-cpr" if cancel_on_ack else "meshecho-cpr-nocancel"
        self._reset_cpr_state(max_hops=8)

    def _reset_cpr_state(self, *, max_hops: int) -> None:
        self.cpr_pending = CprRelayLedger(
            max_records=8, max_hops=max_hops,
            evict_pending=self.cancel_on_ack,
        )
        self.cpr_flows: Dict[int, CprFlowRecord] = {}
        self.cpr_initial_pending: Dict[int, PendingSend] = {}
        self.cpr_repeat_pending: Dict[int, PendingSend] = {}
        self.cpr_recovery_pending: Dict[int, PendingSend] = {}
        self.cpr_repeat_timers: Set[int] = set()
        self.cpr_recovery_timers: Set[int] = set()
        self.cpr_ack_event_ids: Dict[int, int] = {}
        self.retired_flow_order: List[int] = []

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self._reset_cpr_state(max_hops=sim.max_hops)

    @staticmethod
    def _fits(now: float, duration_s: float, deadline: float) -> bool:
        return now < deadline and now + duration_s <= deadline

    def _cpr_route_bound_s(
        self, src: int, dst: int, flow_id: int, path: Tuple[int, ...],
        *, repair_index: Optional[int] = None,
    ) -> float:
        """Bound the exact wire form used by an initial or repeat DATA."""

        hops = max(1, len(path) - 1)
        data = Packet(
            kind="DATA", flow_id=flow_id, origin=src, final_dst=dst,
            ttl=self.sim.max_hops, created_at=self.sim.now,
            protocol=self.name, request_id=flow_id, path=path,
            repair_index=repair_index,
        )
        ack = Packet(
            kind="ACK", flow_id=flow_id, origin=dst, final_dst=src,
            ttl=self.sim.max_hops, created_at=self.sim.now,
            protocol=self.name, request_id=flow_id, path=path,
            path_index=max(0, len(path) - 2), app_payload=False,
            repair_index=repair_index,
        )
        return hops * (
            self.sim.radio.packet_toa_s(data) +
            self.sim.radio.packet_toa_s(ack)
        ) + self.safety_margin_s

    def _cpr_flow(self, flow_id: int) -> Optional[CprFlowRecord]:
        return self.cpr_flows.get(flow_id)

    def _cpr_placeholder(self, flow: CprFlowRecord, kind: str) -> Packet:
        return Packet(
            kind=kind,
            flow_id=flow.flow_id,
            origin=flow.source,
            final_dst=flow.destination,
            ttl=self.sim.max_hops,
            created_at=flow.enqueue_at,
            protocol=self.name,
            request_id=flow.flow_id,
            path=(flow.source,),
            app_payload=False,
        )

    def send_app(self, src: int, dst: int, flow_id: int) -> None:
        self.sim.metrics.register_flow(flow_id, src, dst, self.sim.now)
        if dst == BROADCAST_DST:
            # Broadcast has no source ACK lifecycle; retain the tested flood
            # primitive without entering the CPR unicast state machine.
            packet = Packet(
                kind="FLOOD", flow_id=flow_id, origin=src, final_dst=dst,
                ttl=self.sim.max_hops, created_at=self.sim.now,
                protocol=self.name, request_id=flow_id, path=(src,),
            )
            self.seen_floods[src].add(self._seen_key(packet), self.sim.now)
            self.sim.transmit_later(src, packet, delay_s=0.0)
            return

        state = self._state(src)
        registration = state.register_flow(
            flow_id, source=src, destination=dst,
            enqueue_at=self.sim.now, deadline_s=self.app_deadline_s,
        )
        if not registration.accepted:
            self.action_events.append({
                "event": "decision", "time": self.sim.now,
                "flow_id": flow_id, "src": src, "dst": dst,
                "action": "DROP", "reason": registration.reason,
            })
            return
        flow = CprFlowRecord(
            flow_id=flow_id, source=src, destination=dst,
            enqueue_at=self.sim.now,
            deadline=self.sim.now + self.app_deadline_s,
        )
        self.cpr_flows[flow_id] = flow
        self.flow_records[flow_id] = flow
        self.flow_states[flow_id] = state
        self.cpr_initial_pending[flow_id] = self.sim.transmit_later(
            src, self._cpr_placeholder(flow, "CPR_REQUEST"), delay_s=0.0,
        )
        self.sim.schedule(
            flow.deadline, "protocol_timer",
            lambda flow_id=flow_id: self._cpr_expire_deadline(flow_id),
        )

    def on_tx_request(
        self, sender: int, packet: Packet, start: float, pending: PendingSend,
    ) -> Optional[Packet]:
        if packet.kind == "CPR_REQUEST":
            return self._cpr_start_initial(sender, packet.flow_id, start, pending)
        if packet.kind == "CPR_REPEAT_REQUEST":
            return self._cpr_start_repeat(sender, packet.flow_id, start, pending)
        if packet.kind == "CPR_RECOVERY_REQUEST":
            return self._cpr_start_recovery(sender, packet.flow_id, start, pending)
        return super().on_tx_request(sender, packet, start, pending)

    def _cpr_decision_event(
        self, flow: CprFlowRecord, *, action: str, reason: str, time: float,
        route_bound_s: Optional[float] = None,
        flood_bound_s: Optional[float] = None,
    ) -> None:
        event = {
            "event": "decision", "time": time, "flow_id": flow.flow_id,
            "src": flow.source, "dst": flow.destination,
            "action": action, "reason": reason, "deadline": flow.deadline,
            "route_generation": flow.route_generation,
            "initial_route_epoch": flow.initial_route_epoch,
            "recovery_route_epoch": flow.recovery_route_epoch,
        }
        if route_bound_s is not None:
            event["route_bound_s"] = route_bound_s
        if flood_bound_s is not None:
            event["flood_bound_s"] = flood_bound_s
        self.action_events.append(event)

    def _cpr_start_initial(
        self, sender: int, flow_id: int, start: float, pending: PendingSend,
    ) -> Optional[Packet]:
        del sender, pending
        flow = self._cpr_flow(flow_id)
        state = self.flow_states.get(flow_id)
        if flow is None or state is None or flow_id in self.retired_flows:
            return None
        if flow.acked_at is not None or start >= flow.deadline:
            self._cpr_decision_event(
                flow, action="DROP", reason="deadline-infeasible", time=start,
            )
            return None
        flow.initial_route_epoch = state.route_generation_for(flow.destination)
        route = self._route_record(flow.source, flow.destination, start)
        route_bound_s = (
            self._route_bound_s(flow.source, flow.destination, flow_id, route.path)
            if route is not None else 0.0
        )
        flood_bound_s = self._flood_bound_s(
            flow.source, flow.destination, flow_id, marked=False,
        )
        use_route = (
            route is not None
            and route.phase is RoutePhase.READY
            and self._fits(
            start, route_bound_s, flow.deadline,
            )
        )
        if use_route:
            flow.initial_action = "R"
            flow.initial_path = route.path
            flow.route_generation = route.generation
            self.flow_actions[flow_id] = "R_INITIAL"
            self.flow_sent_paths[flow_id] = route.path
            self._cpr_decision_event(
                flow, action="R_INITIAL", reason="confirmed-route",
                time=start, route_bound_s=route_bound_s,
                flood_bound_s=flood_bound_s,
            )
            return Packet(
                kind="DATA", flow_id=flow_id, origin=flow.source,
                final_dst=flow.destination, ttl=self.sim.max_hops,
                created_at=flow.enqueue_at, protocol=self.name,
                request_id=flow_id, path=route.path,
            )
        if not self._fits(start, flood_bound_s, flow.deadline):
            self._cpr_decision_event(
                flow, action="DROP", reason="deadline-infeasible", time=start,
                route_bound_s=route_bound_s, flood_bound_s=flood_bound_s,
            )
            return None
        flow.initial_action = "F"
        flow.initial_path = (flow.source,)
        self.flow_actions[flow_id] = "F_INITIAL"
        self.flow_sent_paths[flow_id] = (flow.source,)
        self._cpr_decision_event(
            flow, action="F_INITIAL", reason="no-feasible-confirmed-route",
            time=start, route_bound_s=route_bound_s,
            flood_bound_s=flood_bound_s,
        )
        return Packet(
            kind="FLOOD", flow_id=flow_id, origin=flow.source,
            final_dst=flow.destination, ttl=self.sim.max_hops,
            created_at=flow.enqueue_at, protocol=self.name,
            request_id=flow_id, path=(flow.source,),
        )

    def _cpr_start_repeat(
        self, sender: int, flow_id: int, start: float, pending: PendingSend,
    ) -> Optional[Packet]:
        del sender, pending
        flow = self._cpr_flow(flow_id)
        if (
            flow is None or flow_id in self.retired_flows
            or flow.acked_at is not None
            or flow.initial_action != "R"
            or not flow.repeat_requested
            or flow.repeat_started_at is not None
        ):
            return None
        route = self._route_record(flow.source, flow.destination, start)
        if (
            route is None
            or route.phase is not RoutePhase.READY
            or route.generation != flow.route_generation
        ):
            self._cpr_decision_event(
                flow, action="DROP", reason="stale-route-generation", time=start,
            )
            return None
        route_bound_s = self._cpr_route_bound_s(
            flow.source, flow.destination, flow_id, flow.initial_path,
            repair_index=1,
        )
        decision = choose_recovery_action(CprObservation(
            now=start, deadline=flow.deadline,
            route_bound_s=route_bound_s,
            flood_bound_s=self._flood_bound_s(
                flow.source, flow.destination, flow_id, marked=True,
            ),
            repeat_started=False,
        ))
        if decision.action is not CprAction.R_REPEAT:
            self._cpr_decision_event(
                flow, action=decision.action.value, reason=decision.reason, time=start,
                route_bound_s=route_bound_s,
            )
            return None
        self.flow_actions[flow_id] = "R_REPEAT"
        self.flow_sent_paths[flow_id] = flow.initial_path
        self._cpr_decision_event(
            flow, action="R_REPEAT", reason="repeat-after-initial-miss", time=start,
            route_bound_s=route_bound_s,
        )
        return Packet(
            kind="DATA", flow_id=flow_id, origin=flow.source,
            final_dst=flow.destination, ttl=self.sim.max_hops,
            created_at=flow.enqueue_at, protocol=self.name,
            request_id=flow_id, path=flow.initial_path, repair_index=1,
        )

    def _cpr_start_recovery(
        self, sender: int, flow_id: int, start: float, pending: PendingSend,
    ) -> Optional[Packet]:
        del sender, pending
        flow = self._cpr_flow(flow_id)
        state = self.flow_states.get(flow_id)
        if (
            flow is None or state is None or flow_id in self.retired_flows
            or flow.acked_at is not None
            or not flow.repeat_started_at is not None
            or not flow.recovery_requested
            or flow.recovery_started_at is not None
        ):
            return None
        route = self._route_record(flow.source, flow.destination, start)
        route_valid = (
            route is not None
            and route.phase is RoutePhase.READY
            and route.generation == flow.route_generation
        )
        flood_bound_s = self._flood_bound_s(
            flow.source, flow.destination, flow_id, marked=True,
        )
        decision = choose_recovery_action(CprObservation(
            now=start,
            deadline=flow.deadline,
            route_bound_s=self._cpr_route_bound_s(
                flow.source, flow.destination, flow_id, flow.initial_path,
                repair_index=1,
            ),
            flood_bound_s=flood_bound_s,
            repeat_started=True,
        ))
        if not route_valid:
            decision = CprDecision(
                CprAction.DROP_DEADLINE_INFEASIBLE,
                "stale-route-generation",
            )
        if decision.action is not CprAction.F_RECOVERY:
            self._cpr_decision_event(
                flow, action=decision.action.value, reason=decision.reason, time=start,
                flood_bound_s=flood_bound_s,
            )
            return None
        flow.recovery_route_epoch = state.route_generation_for(flow.destination)
        self.flow_actions[flow_id] = "F_RECOVERY"
        self.flow_sent_paths[flow_id] = (flow.source,)
        self._cpr_decision_event(
            flow, action=CprAction.F_RECOVERY.value, reason=decision.reason,
            time=start, flood_bound_s=flood_bound_s,
        )
        return Packet(
            kind="FLOOD", flow_id=flow_id, origin=flow.source,
            final_dst=flow.destination, ttl=self.sim.max_hops,
            created_at=flow.enqueue_at, protocol=self.name,
            request_id=flow_id, path=(flow.source,), repair_index=2,
        )

    def on_transmit(self, sender: int, packet: Packet, start: float, end: float) -> None:
        super().on_transmit(sender, packet, start, end)
        self.cpr_pending.retire()
        if sender != packet.origin:
            return
        flow = self._cpr_flow(packet.flow_id)
        if flow is None:
            return
        if packet.repair_index is None and packet.kind in {"DATA", "FLOOD"}:
            flow.initial_started_at = start
            if (packet.kind == "DATA" and flow.initial_action == "R"
                    and flow.flow_id not in self.cpr_repeat_timers):
                self.cpr_repeat_timers.add(flow.flow_id)
                bound = self._cpr_route_bound_s(
                    flow.source, flow.destination, flow.flow_id, flow.initial_path,
                    repair_index=1,
                )
                self.sim.schedule(
                    min(flow.deadline, start + bound), "protocol_timer",
                    lambda flow_id=flow.flow_id: self._cpr_arm_repeat(flow_id),
                )
        elif packet.kind == "DATA" and packet.repair_index == 1:
            flow.repeat_started_at = start
            if flow.flow_id not in self.cpr_recovery_timers:
                self.cpr_recovery_timers.add(flow.flow_id)
                bound = self._cpr_route_bound_s(
                    flow.source, flow.destination, flow.flow_id, flow.initial_path,
                    repair_index=1,
                )
                self.sim.schedule(
                    min(flow.deadline, start + bound), "protocol_timer",
                    lambda flow_id=flow.flow_id: self._cpr_arm_recovery(flow_id),
                )
        elif packet.kind == "FLOOD" and packet.repair_index == 2:
            flow.recovery_started_at = start
            self.action_events.append({
                "event": "recovery-tx", "time": start, "flow_id": flow.flow_id,
                "src": sender, "repair_index": 2,
            })

    def _cpr_arm_repeat(self, flow_id: int) -> None:
        flow = self._cpr_flow(flow_id)
        if (
            flow is None or flow_id in self.retired_flows
            or flow.acked_at is not None or flow.initial_action != "R"
            or flow.repeat_requested or flow.initial_started_at is None
        ):
            return
        if self.sim.now >= flow.deadline:
            return
        flow.repeat_requested = True
        placeholder = self._cpr_placeholder(flow, "CPR_REPEAT_REQUEST")
        self.cpr_repeat_pending[flow_id] = self.sim.transmit_later(
            flow.source, placeholder, delay_s=0.0,
        )
        self.action_events.append({
            "event": "repeat-request", "time": self.sim.now,
            "flow_id": flow_id, "repair_index": 1,
        })

    def _cpr_arm_recovery(self, flow_id: int) -> None:
        flow = self._cpr_flow(flow_id)
        if (
            flow is None or flow_id in self.retired_flows
            or flow.acked_at is not None or flow.repeat_started_at is None
            or flow.recovery_requested or flow.recovery_started_at is not None
        ):
            return
        if self.sim.now >= flow.deadline:
            return
        flow.recovery_requested = True
        placeholder = self._cpr_placeholder(flow, "CPR_RECOVERY_REQUEST")
        self.cpr_recovery_pending[flow_id] = self.sim.transmit_later(
            flow.source, placeholder, delay_s=0.0,
        )
        self.action_events.append({
            "event": "recovery-request", "time": self.sim.now,
            "flow_id": flow_id, "repair_index": 2,
        })

    def _cpr_expire_deadline(self, flow_id: int) -> None:
        flow = self._cpr_flow(flow_id)
        state = self.flow_states.get(flow_id)
        if flow is None or state is None or flow_id in self.retired_flows:
            return
        if flow.acked_at is not None:
            self._cpr_retire(flow_id)
            return
        for pending_map in (
            self.cpr_initial_pending,
            self.cpr_repeat_pending,
            self.cpr_recovery_pending,
        ):
            pending = pending_map.pop(flow_id, None)
            if pending is not None:
                pending.canceled = True
        record = state.routes.get(flow.destination)
        if (
            record is not None
            and record.phase is RoutePhase.READY
            and flow.initial_action == "R"
            and flow.route_generation is not None
            and record.generation == flow.route_generation
        ):
            evicted = state.record_in_deadline_miss(
                flow.destination, flow.route_generation,
            )
            if evicted:
                self._remove_route(flow.source, flow.destination)
            else:
                self._mirror_route(flow.source, record)
        self.action_events.append({
            "event": "timeout", "time": self.sim.now, "flow_id": flow_id,
            "src": flow.source, "dst": flow.destination,
            "reason": "deadline-censor",
        })
        self._cpr_retire(flow_id)

    def _cpr_retire(self, flow_id: int) -> None:
        state = self.flow_states.get(flow_id)
        if state is not None:
            state.active_flows.pop(flow_id, None)
        self.retired_flows.add(flow_id)
        self.retired_flow_order.append(flow_id)
        while len(self.retired_flow_order) > 256:
            expired = self.retired_flow_order.pop(0)
            self.retired_flows.discard(expired)
        self.cpr_flows.pop(flow_id, None)
        self.flow_records.pop(flow_id, None)
        self.cpr_ack_event_ids.pop(flow_id, None)
        self.cpr_repeat_timers.discard(flow_id)
        self.cpr_recovery_timers.discard(flow_id)
        self.cpr_initial_pending.pop(flow_id, None)
        self.cpr_repeat_pending.pop(flow_id, None)
        self.cpr_recovery_pending.pop(flow_id, None)

    def _cpr_ack_rejection_reason(
        self, flow: CprFlowRecord, packet: Packet, rx: RxInfo,
    ) -> Optional[str]:
        if packet.kind != "ACK":
            return "wrong-kind"
        if packet.request_id != flow.flow_id:
            return "flow-request-mismatch"
        if packet.origin != flow.destination or packet.final_dst != flow.source:
            return "endpoint-mismatch"
        if packet.app_payload:
            return "ack-has-payload"
        if self.sim.now > flow.deadline:
            return "late"
        path = tuple(packet.path)
        if packet.path_index != 0:
            return "path-index-mismatch"
        if len(path) < 2 or len(path) > self.sim.max_hops + 1:
            return "path-length-mismatch"
        if path[0] != flow.source or path[-1] != flow.destination:
            return "path-endpoint-mismatch"
        if len(set(path)) != len(path):
            return "looped-path"
        if rx.sender != path[1]:
            return "path-or-sender-mismatch"
        state = self.flow_states.get(flow.flow_id)
        if state is None:
            return "unknown-flow-state"
        current_epoch = state.route_generation_for(flow.destination)
        record = state.routes.get(flow.destination)
        marker = packet.repair_index
        if marker is None:
            if flow.initial_started_at is None:
                return "initial-not-started"
            if flow.initial_action == "R" and path != flow.initial_path:
                return "initial-path-mismatch"
            if flow.initial_action == "R":
                if (
                    record is None
                    or record.phase is not RoutePhase.READY
                    or record.generation != flow.route_generation
                ):
                    return "stale-route-generation"
            elif current_epoch != flow.initial_route_epoch:
                return "stale-route-generation"
        elif marker == 1:
            if flow.repeat_started_at is None:
                return "repeat-not-started"
            if path != flow.initial_path:
                return "repeat-path-mismatch"
            if (
                record is None
                or record.phase is not RoutePhase.READY
                or record.generation != flow.route_generation
            ):
                return "stale-route-generation"
        elif marker == 2:
            if flow.recovery_started_at is None:
                return "recovery-not-started"
            expected_epoch = (
                flow.recovery_route_epoch
                if flow.recovery_route_epoch is not None
                else flow.route_generation
            )
            if expected_epoch is None or current_epoch != expected_epoch:
                return "stale-route-generation"
            if (
                record is None
                or record.phase is not RoutePhase.READY
                or record.generation != expected_epoch
            ):
                return "stale-route-generation"
        else:
            return "marker-mismatch"
        return None

    def on_receive(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if packet.kind == "ACK":
            self._cpr_cancel_relay(receiver, packet, rx)
            self._cpr_on_ack_packet(receiver, packet, rx)
            return
        if packet.kind == "FLOOD":
            self._cpr_on_flood(receiver, packet, rx)
            return
        if packet.kind == "DATA":
            self._on_data(receiver, packet, rx)

    def _cpr_on_flood(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        self.cpr_pending.retire()
        key = self._seen_key(packet)
        unseen = not self.seen_floods[receiver].contains(key, self.sim.now)
        super()._on_flood(receiver, packet, rx)
        if not unseen:
            return
        valid_forward = (
            packet.app_payload
            and packet.repair_index in {None, 2}
            and packet.request_id == packet.flow_id
            and packet.origin != receiver != packet.final_dst
            and packet.ttl > 1 and self.sim.nodes[receiver].can_relay
            and bool(packet.path) and packet.path[0] == packet.origin
            and packet.path[-1] == rx.sender
            and receiver not in packet.path
            and len(set(packet.path)) == len(packet.path)
            and 1 <= len(packet.path) < self.sim.max_hops
            and packet.path_index == len(packet.path) - 1
        )
        if not valid_forward:
            return
        pending_key = (receiver, key)
        pending = self.pending_fallback.get(pending_key)
        if pending is None or pending.canceled or pending.committed:
            return
        if not self.cancel_on_ack:
            return
        evicted = self.cpr_pending.enroll(
            CprPendingRelay(
                relay=receiver,
                origin=packet.origin,
                final_dst=packet.final_dst,
                flow_id=packet.flow_id,
                request_id=packet.request_id,
                repair_index=packet.repair_index,
                path=tuple(packet.path),
                pending=pending,
            )
        )
        for record in evicted:
            self.action_events.append({
                "event": "state-eviction", "time": self.sim.now,
                "node": receiver, "state": "cpr_pending_relay",
                "flow_id": record.flow_id,
                "repair_index": record.repair_index,
                "reason": "capacity",
                "pending_canceled": bool(record.pending.canceled),
            })

    def _cpr_cancel_relay(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if not self.cancel_on_ack:
            return
        canceled = self.cpr_pending.cancel_for_ack(
            relay=receiver,
            ack=CprAckObservation(
                receiver=receiver, sender=rx.sender,
                flow_id=packet.flow_id, request_id=packet.request_id,
                origin=packet.origin, final_dst=packet.final_dst,
                path=tuple(packet.path), path_index=packet.path_index,
                repair_index=packet.repair_index,
                app_payload=packet.app_payload,
            ),
        )
        if not canceled:
            return
        key = (
            receiver,
            ("FLOOD", packet.final_dst, packet.flow_id,
             packet.request_id, packet.repair_index),
        )
        self.pending_fallback.pop(key, None)
        self.action_events.append({
            "event": "cpr-cancel", "time": self.sim.now,
            "flow_id": packet.flow_id, "relay": receiver,
            "repair_index": packet.repair_index,
            "ack_rx_attempt_id": rx.attempt_id,
        })

    def _cpr_on_ack_packet(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        index = packet.path_index
        if (
            not 0 <= index < len(packet.path)
            or packet.path[index] != receiver
            or index + 1 >= len(packet.path)
            or packet.path[index + 1] != rx.sender
        ):
            if receiver == packet.final_dst:
                self.sim.record_ack_provenance(
                    packet, rx, receiver=receiver, accepted=False,
                    rejection_reason="path-or-sender-mismatch",
                    deadline_at=None,
                )
            return
        if receiver == packet.final_dst:
            flow = self._cpr_flow(packet.flow_id)
            if flow is None:
                self.sim.record_ack_provenance(
                    packet, rx, receiver=receiver, accepted=False,
                    rejection_reason="unknown-flow", deadline_at=None,
                )
                return
            rejection = self._cpr_ack_rejection_reason(flow, packet, rx)
            ack_event_id = self.sim.record_ack_provenance(
                packet, rx, receiver=receiver, accepted=rejection is None,
                rejection_reason=rejection,
                route_generation=(
                    flow.route_generation
                    if flow.route_generation is not None
                    else flow.initial_route_epoch
                ),
                accepted_at=self.sim.now if rejection is None else None,
                deadline_at=flow.deadline,
            )
            if rejection is None:
                self.cpr_ack_event_ids[flow.flow_id] = ack_event_id
                self.sim.mark_acknowledged(packet.flow_id, receiver, packet)
            return
        if packet.ttl <= 1:
            return
        self.sim.transmit_later(receiver, packet.retreat_path().with_ttl(packet.ttl - 1), 0.0)

    def on_ack(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        del receiver
        flow = self._cpr_flow(flow_id)
        state = self.flow_states.get(flow_id)
        if flow is None or state is None or flow_id in self.retired_flows:
            return
        marker = packet.repair_index
        if marker not in {None, 1, 2}:
            return
        if self._cpr_ack_rejection_reason(
            flow, packet, RxInfo(
                sender=packet.path[1], rx_power_dbm=0.0, snr_db=0.0,
                sinr_db=0.0, collided=False,
            ),
        ) is not None:
            return
        flow.acked_at = now
        for pending_map in (
            self.cpr_initial_pending,
            self.cpr_repeat_pending,
            self.cpr_recovery_pending,
        ):
            pending = pending_map.pop(flow_id, None)
            if pending is not None and not pending.committed:
                pending.canceled = True
        route_generation_before = state.route_generation_for(flow.destination)
        route = state.install_route(
            flow.destination, tuple(packet.path), now=now,
            ttl_s=self.route_ttl_s,
        )
        self._mirror_route(flow.source, route)
        self.flow_ack_paths[flow_id] = tuple(packet.path)
        self.last_commit_flow[(flow.source, flow.destination)] = flow_id
        ack_event_id = self.cpr_ack_event_ids.pop(flow_id, None)
        if ack_event_id is not None:
            for provenance in self.sim.ack_provenance:
                if provenance.get("ack_event_id") == ack_event_id:
                    provenance["route_generation"] = (
                        flow.route_generation
                        if flow.route_generation is not None
                        else route_generation_before
                    )
                    provenance["route_generation_after"] = route.generation
                    break
        self.action_events.append({
            "event": "ack-accept", "time": now, "flow_id": flow_id,
            "src": flow.source, "dst": flow.destination,
            "action": self.flow_actions.get(flow_id),
            "path": tuple(packet.path), "repair_index": marker,
            "route_generation_before": route_generation_before,
            "route_generation_after": route.generation,
        })
        self._cpr_retire(flow_id)


class MeshEchoDHR(MeshEchoSR):
    """Source-local, same-flow recovery after an unACKed routed DATA send."""

    name = "meshecho-dhr"

    def __init__(
        self, *args: Any, rescue_mode: str = "adaptive",
        source_mode: str = "sr", **kwargs: Any,
    ) -> None:
        names = {
            "adaptive": "meshecho-dhr",
            "none": "meshecho-dhr-none",
            "repeat": "meshecho-dhr-repeat",
            "flood": "meshecho-dhr-flood",
        }
        if rescue_mode not in names:
            raise ValueError(f"unknown DHR rescue mode: {rescue_mode}")
        super().__init__(*args, mode=source_mode, **kwargs)
        self.rescue_mode = rescue_mode
        self.name = names[rescue_mode]
        self.active_flows: Dict[int, DHRActiveFlow] = {}

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.active_flows = {}

    def on_transmit(self, sender: int, packet: Packet, start: float, end: float) -> None:
        if (sender == packet.origin and
                (packet.kind, packet.repair_index) in {("DATA", 1), ("FLOOD", 2)}):
            active = self.active_flows.get(packet.flow_id)
            if active is not None:
                active.started_marker = packet.repair_index
            self.action_events.append(
                {"event": "dhr_recovery_tx", "time": start, "end": end,
                 "flow_id": packet.flow_id, "src": sender,
                 "dst": packet.final_dst,
                 "action": "R" if packet.repair_index == 1 else "F",
                 "repair_index": packet.repair_index}
            )
            return
        super().on_transmit(sender, packet, start, end)
        if (sender != packet.origin or packet.kind != "DATA"
                or packet.repair_index is not None
                or self.flow_actions.get(packet.flow_id) != "R"
                or self.flow_data_actions.get(packet.flow_id) != "R"):
            return
        active_count = sum(
            active.src == sender for active in self.active_flows.values()
        )
        if active_count >= 8:
            self.action_events.append(
                {"event": "dhr_state_drop", "time": start,
                 "flow_id": packet.flow_id, "src": sender,
                 "dst": packet.final_dst, "reason": "active-capacity"}
            )
            return
        state = self.destination_state.get((sender, packet.final_dst))
        self.active_flows[packet.flow_id] = DHRActiveFlow(
            src=sender, dst=packet.final_dst, path=packet.path,
            created_at=packet.created_at, initial_start=start,
            route_generation=state.last_commit_flow if state is not None else 0,
        )
        self.sim.schedule(
            packet.created_at + self.app_deadline_s + 1e-6,
            "protocol_timer",
            lambda flow_id=packet.flow_id: self.active_flows.pop(flow_id, None),
        )

    def log_destination_rx(self, receiver: int, packet: Packet) -> None:
        flow = self.sim.metrics.flows.get(packet.flow_id)
        if (flow is None or receiver != flow.dst or packet.origin != flow.src
                or packet.request_id != packet.flow_id):
            return
        self.action_events.append(
            {"event": "dhr_destination_rx", "time": self.sim.now,
             "flow_id": packet.flow_id, "src": flow.src, "dst": receiver,
             "repair_index": packet.repair_index,
             "duplicate": flow.delivered_at is not None}
        )

    def on_data(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if receiver == packet.final_dst and self.path_next_hop_matches(receiver, packet):
            self.log_destination_rx(receiver, packet)
        super().on_data(receiver, packet, rx)

    def on_fallback(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if receiver == packet.final_dst and packet.kind == "FLOOD":
            self.log_destination_rx(receiver, packet)
        super().on_fallback(receiver, packet, rx)

    def on_ack_packet(self, receiver: int, packet: Packet) -> None:
        if receiver != packet.final_dst:
            super().on_ack_packet(receiver, packet)
            return
        flow = self.sim.metrics.flows.get(packet.flow_id)
        path = packet.path
        valid = (
            flow is not None and receiver == flow.src
            and packet.origin == flow.dst
            and packet.request_id == packet.flow_id
            and packet.path_index == 0
            and 2 <= len(path) <= self.sim.max_hops + 1
            and path[0] == flow.src and path[-1] == flow.dst
            and len(set(path)) == len(path)
            and self.sim.now <= flow.created_at + self.app_deadline_s
            and packet.flow_id in self.flow_data_actions
        )
        if valid:
            initial_action = self.flow_data_actions[packet.flow_id]
            initial_path = self.flow_sent_paths.get(packet.flow_id)
            if packet.repair_index is None:
                valid = initial_action != "R" or path == initial_path
            elif packet.repair_index == 1:
                active = self.active_flows.get(packet.flow_id)
                valid = (initial_action == "R" and path == initial_path
                         and active is not None and active.started_marker == 1)
            elif packet.repair_index == 2:
                active = self.active_flows.get(packet.flow_id)
                valid = (initial_action == "R"
                         and active is not None and active.started_marker == 2)
            else:
                valid = False
        if not valid:
            self.action_events.append(
                {"event": "dhr_source_ack_rx", "time": self.sim.now,
                 "flow_id": packet.flow_id, "src": receiver,
                 "dst": packet.origin, "repair_index": packet.repair_index,
                 "accepted": False}
            )
            return
        prior_ack = flow.acked_at
        if packet.repair_index == 2:
            RoutingProtocol.on_ack_packet(self, receiver, packet)
        else:
            super().on_ack_packet(receiver, packet)
        self.action_events.append(
            {"event": "dhr_source_ack_rx", "time": self.sim.now,
             "flow_id": packet.flow_id, "src": receiver,
             "dst": flow.dst, "repair_index": packet.repair_index,
             "accepted": prior_ack is None and flow.acked_at is not None}
        )

    def on_ack(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        flow = self.sim.metrics.flows.get(flow_id)
        if flow is None:
            return
        state = self.destination_state.get((receiver, flow.dst))
        current = self.route_cache.get(receiver, {}).get(flow.dst)
        if packet.repair_index == 2:
            if state is not None and flow_id >= state.last_commit_flow:
                old_path = self.flow_sent_paths.get(flow_id)
                state.last_commit_flow = flow_id
                state.consecutive_f_misses = 0
                state.consecutive_r_misses = 0
                state.had_r_miss_since_commit = False
                state.f_miss_flows.clear()
                state.r_miss_flows.clear()
                state.recent_r_flows.clear()
                self.route_cache[receiver][flow.dst] = RouteEntry(
                    created_at=now, expires_at=now + self.route_ttl_s,
                    path=packet.path, confidence=1.0,
                )
                self.action_events.append(
                    {"event": "commit", "time": now, "flow_id": flow_id,
                     "src": receiver, "dst": flow.dst,
                     "action": "F-recovery", "path": packet.path,
                     "replaced_confirmed_path": bool(old_path)
                     and old_path != packet.path}
                )
                state.last_ack_at = now
            self.active_flows.pop(flow_id, None)
            return
        initial_path = self.flow_sent_paths.get(flow_id)
        current_r = (
            self.flow_data_actions.get(flow_id) != "R"
            or (state is not None and current is not None
                and flow_id >= state.last_commit_flow
                and initial_path == current.path)
        )
        if not current_r:
            self.active_flows.pop(flow_id, None)
            return
        super().on_ack(flow_id, receiver, now, packet)
        current = self.route_cache.get(receiver, {}).get(flow.dst)
        if (state is not None and current is not None
                and flow_id >= state.last_commit_flow
                and packet.path == current.path):
            state.last_ack_at = now
        self.active_flows.pop(flow_id, None)

    def rescue_round_trip_bound_s(self, path: Tuple[int, ...]) -> float:
        hops = len(path) - 1
        route_data = Packet(
            kind="DATA", flow_id=0, origin=path[0], final_dst=path[-1],
            ttl=self.sim.max_hops, created_at=0.0, protocol=self.name,
            request_id=0, path=path, repair_index=1,
        )
        route_ack = replace(route_data, kind="ACK", origin=path[-1],
                            final_dst=path[0], app_payload=False)
        route_bound = hops * (
            self.sim.radio.packet_toa_s(route_data)
            + self.sim.radio.packet_toa_s(route_ack)
        )
        flood_hops = self.useful_flood_ttl()
        longest_path = tuple(range(flood_hops + 1))
        flood_data = replace(route_data, kind="FLOOD", path=longest_path,
                             ttl=flood_hops, repair_index=2)
        flood_ack = replace(route_ack, path=longest_path, repair_index=2)
        flood_bound = flood_hops * (
            self.sim.radio.packet_toa_s(flood_data)
            + self.flood_base_delay_s + self.flood_jitter_s + 0.35
            + self.sim.radio.packet_toa_s(flood_ack)
        )
        return max(route_bound, flood_bound) + 1.0

    def expire_data_ack(self, flow_id: int) -> None:
        flow = self.sim.metrics.flows.get(flow_id)
        r_timeout = (
            flow is not None and flow.acked_at is None
            and flow_id not in self.flow_timeout_applied
            and self.flow_actions.get(flow_id) == "R"
            and self.flow_data_actions.get(flow_id) == "R"
        )
        super().expire_data_ack(flow_id)
        if not r_timeout or flow is None:
            return
        active = self.active_flows.get(flow_id)
        path = active.path if active is not None else None
        reason = "admitted"
        if active is None:
            reason = "active-capacity"
        elif len(path) < 2 or path[0] != flow.src or path[-1] != flow.dst:
            reason = "no-path"
        elif active.selected_action is not None:
            reason = "already-selected"
        elif self.sim.nodes[flow.src].tx_available_at > self.sim.now + 1e-9:
            reason = "source-busy"
        elif self.sim.now + self.rescue_round_trip_bound_s(path) > (
            active.created_at + self.app_deadline_s
        ):
            reason = "deadline-budget"
        if reason != "admitted":
            self.action_events.append(
                {"event": "dhr_guard", "time": self.sim.now,
                 "flow_id": flow_id, "src": flow.src, "dst": flow.dst,
                 "admitted": False, "reason": reason,
                 "selected_action": "none"}
            )
            return
        state = self.destination_state.get((flow.src, flow.dst))
        last_ack_at = state.last_ack_at if state is not None else None
        use_flood = (
            last_ack_at is None or self.sim.now - last_ack_at >= 120.0
            or (state is not None and state.consecutive_r_misses >= 2)
        )
        selected_action = {
            "adaptive": "F" if use_flood else "R",
            "none": "none",
            "repeat": "R",
            "flood": "F",
        }[self.rescue_mode]
        use_flood = selected_action == "F"
        self.action_events.append(
            {"event": "dhr_guard", "time": self.sim.now,
             "flow_id": flow_id, "src": flow.src, "dst": flow.dst,
             "admitted": True, "reason": "admitted",
             "selected_action": selected_action}
        )
        active.selected_action = selected_action
        if selected_action == "none":
            return
        packet = (
            Packet(
                kind="FLOOD", flow_id=flow_id, origin=flow.src,
                final_dst=flow.dst, ttl=self.useful_flood_ttl(),
                created_at=flow.created_at, protocol=self.name,
                request_id=flow_id, path=(flow.src,), repair_index=2,
            ) if use_flood else Packet(
                kind="DATA", flow_id=flow_id, origin=flow.src,
                final_dst=flow.dst, ttl=self.sim.max_hops,
                created_at=flow.created_at, protocol=self.name,
                request_id=flow_id, path=path, repair_index=1,
            )
        )
        if use_flood:
            self.seen_floods[flow.src].add(packet.flood_key)
        deadline_at = active.created_at + self.app_deadline_s
        pending = PendingSend(can_start_at=lambda start, flow_id=flow_id,
                             path=path, active=active:
            abs(start - self.sim.now) <= 1e-9
            and self.active_flows.get(flow_id) is active
            and active.started_marker is None
            and start + self.rescue_round_trip_bound_s(path) <= deadline_at)
        self.sim.transmit_later(flow.src, packet, delay_s=0.0, pending=pending)


class MeshEchoDHRDelayedAck(MeshEchoDHR):
    """Fixed-F control that waits after the first FLOOD decode before ACKing."""

    name = "meshecho-dhr-flood-ack-delay"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, rescue_mode="flood", **kwargs)
        self.name = "meshecho-dhr-flood-ack-delay"

    def reverse_ack_delay_s(self, packet: Packet) -> float:
        return 2.0 if packet.kind == "FLOOD" else 0.0


class MeshEchoDHRDelayedAckFlood2(MeshEchoDHRDelayedAck):
    """Fixed useful-DATA FLOOD radius without changing route discovery."""

    name = "meshecho-dhr-flood-ack-delay-flood2"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.name = "meshecho-dhr-flood-ack-delay-flood2"

    def useful_flood_ttl(self) -> int:
        return min(2, self.sim.max_hops)


class MeshEchoDCB(MeshEchoDHRDelayedAck):
    """Destination-certified conditional backup prototype."""

    name = "meshecho-dcb"

    def __init__(
        self, *args: Any, relay_mode: str = "conditional",
        source_mode: str = "sr", **kwargs: Any,
    ) -> None:
        names = {
            "conditional": "meshecho-dcb",
            "no-forward": "meshecho-dcb-no-forward",
            "unconditional": "meshecho-dcb-unconditional",
            "current-overhear": "meshecho-dcb-current-overhear",
        }
        if relay_mode not in names:
            raise ValueError(f"unknown DCB relay mode: {relay_mode}")
        if (source_mode not in {"sr", "fr", "trigger-f"}
                or (source_mode != "sr" and relay_mode != "conditional")):
            raise ValueError(f"unknown DCB source/relay mode: {source_mode}/{relay_mode}")
        super().__init__(*args, source_mode=source_mode, **kwargs)
        self.relay_mode = relay_mode
        self.name = {
            "sr": names[relay_mode],
            "fr": "meshecho-dcb-source-fr",
            "trigger-f": "meshecho-dcb-source-trigger-f",
        }[source_mode]
        self.feedback_windows: Dict[Tuple[int, int, int, Optional[int]], DCBFloodWindow] = {}
        self.relay_pending: Dict[Tuple[int, int], DCBRelayPending] = {}
        self.peak_feedback_windows_by_destination: Dict[int, int] = {}
        self.peak_pending_backups_by_relay: Dict[int, int] = {}
        self.active_nominations: Dict[int, DCBActiveNomination] = {}
        self.recent_sender_rx: Dict[int, Dict[int, float]] = {}
        self.relay_last_forwarded_flow: Dict[Tuple[int, int], int] = {}

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.feedback_windows = {}
        self.relay_pending = {}
        self.peak_feedback_windows_by_destination = {node_id: 0 for node_id in sim.nodes}
        self.peak_pending_backups_by_relay = {node_id: 0 for node_id in sim.nodes}
        self.active_nominations = {}
        self.recent_sender_rx = {node_id: {} for node_id in sim.nodes}
        self.relay_last_forwarded_flow = {}

    def on_receive(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if (self.relay_mode == "current-overhear"
                and self.sim.nodes[receiver].can_relay):
            recent = self.recent_sender_rx[receiver]
            recent[rx.sender] = self.sim.now
            if len(recent) > 8:
                oldest = min(recent, key=lambda sender: (recent[sender], sender))
                recent.pop(oldest)
        if (packet.kind == "DATA" and packet.repair_index is None
                and packet.path == (packet.origin, packet.final_dst)
                and packet.path_index == 0
                and packet.backup_relay_id is not None
                and packet.backup_epoch_id is not None
                and rx.sender == packet.origin
                and receiver not in {packet.origin, packet.final_dst}
                and (self.relay_mode == "current-overhear"
                     or packet.backup_relay_id == receiver)
                and self.sim.nodes[receiver].can_relay):
            self.buffer_nominated_data(receiver, packet)
        if packet.kind == "DATA" and packet.repair_index == 4:
            self.note_other_backup(receiver, packet, rx)
        if packet.kind == "ACK":
            self.note_relay_ack(receiver, packet, rx)
            if not (
                0 <= packet.path_index < len(packet.path) - 1
                and packet.path[packet.path_index] == receiver
                and packet.path[packet.path_index + 1] == rx.sender
            ):
                if receiver == packet.final_dst:
                    self.action_events.append(
                        {"event": "dcb_source_ack_rx", "time": self.sim.now,
                         "flow_id": packet.flow_id, "accepted": False,
                         "reason": "path-or-sender-mismatch",
                         "sender": rx.sender, "epoch": packet.backup_epoch_id,
                         "path": packet.path}
                    )
                return
        super().on_receive(receiver, packet, rx)

    def buffer_nominated_data(self, receiver: int, packet: Packet) -> None:
        key = (receiver, packet.flow_id)
        if packet.flow_id <= self.relay_last_forwarded_flow.get(
            (receiver, packet.origin), -1,
        ):
            return
        if key in self.relay_pending:
            return
        pending_count = sum(relay == receiver for relay, _ in self.relay_pending)
        if pending_count >= 4:
            self.action_events.append(
                {"event": "dcb_relay_drop", "time": self.sim.now,
                 "flow_id": packet.flow_id, "relay": receiver,
                 "reason": "pending-capacity"}
            )
            return
        pending = DCBRelayPending(packet=packet, received_at=self.sim.now)
        self.relay_pending[key] = pending
        self.peak_pending_backups_by_relay[receiver] = max(
            self.peak_pending_backups_by_relay[receiver], pending_count + 1,
        )
        self.action_events.append(
            {"event": "dcb_relay_pending_open", "time": self.sim.now,
             "flow_id": packet.flow_id, "relay": receiver,
             "active_count": pending_count + 1}
        )
        delay_s = 2.0
        if self.relay_mode == "current-overhear":
            last_dst_rx = self.recent_sender_rx[receiver].get(packet.final_dst)
            recent_dst = (
                last_dst_rx is not None
                and self.sim.now - last_dst_rx <= 120.0
            )
            packed = struct.pack(
                ">IIH", packet.flow_id, packet.backup_epoch_id, receiver,
            )
            slot = (0 if recent_dst else 4) + zlib.crc32(packed) % 4
            delay_s = 0.25 * (slot + 1)
            self.action_events.append(
                {"event": "dcb_current_slot", "time": self.sim.now,
                 "flow_id": packet.flow_id, "relay": receiver,
                 "slot": slot, "recent_dst": recent_dst}
            )
        self.sim.schedule(
            self.sim.now + delay_s, "protocol_timer",
            lambda key=key, pending=pending: self.try_relay_backup(key, pending),
        )

    def remove_relay_pending(self, key: Tuple[int, int]) -> None:
        if self.relay_pending.pop(key, None) is None:
            return
        relay, flow_id = key
        self.action_events.append(
            {"event": "dcb_relay_pending_close", "time": self.sim.now,
             "flow_id": flow_id, "relay": relay,
             "active_count": sum(node == relay for node, _ in self.relay_pending)}
        )

    def note_relay_ack(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if (packet.repair_index is not None
                or packet.path != (packet.final_dst, packet.origin)
                or packet.path_index != 0
                or rx.sender != packet.origin):
            return
        pending = self.relay_pending.get((receiver, packet.flow_id))
        if (pending is not None and pending.packet.origin == packet.final_dst
                and pending.packet.final_dst == packet.origin
                and packet.request_id == packet.flow_id):
            pending.quiet = True

    def note_other_backup(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if self.relay_mode != "current-overhear":
            return
        pending = self.relay_pending.get((receiver, packet.flow_id))
        if (pending is not None and len(packet.path) == 3
                and len(set(packet.path)) == 3
                and packet.path_index == 1
                and packet.request_id == packet.flow_id
                and packet.backup_relay_id is None
                and rx.sender == packet.path[1] != receiver
                and packet.path[0] == pending.packet.origin
                and packet.path[-1] == pending.packet.final_dst
                and packet.backup_epoch_id == pending.packet.backup_epoch_id):
            pending.quiet = True

    def try_relay_backup(
        self, key: Tuple[int, int], pending: DCBRelayPending,
    ) -> None:
        relay, flow_id = key
        if self.relay_pending.get(key) is not pending:
            return
        if self.relay_mode == "no-forward":
            reason = "no-forward-control"
        elif pending.quiet and self.relay_mode != "unconditional":
            reason = "overheard-ack-or-backup"
        elif self.sim.nodes[relay].tx_available_at > self.sim.now + 1e-9:
            reason = "busy-radio"
        else:
            reason = None
        if reason is not None:
            self.action_events.append(
                {"event": "dcb_relay_skip", "time": self.sim.now,
                 "flow_id": flow_id, "relay": relay, "reason": reason}
            )
            self.remove_relay_pending(key)
            return
        original = pending.packet
        backup = Packet(
            kind="DATA", flow_id=flow_id, origin=original.origin,
            final_dst=original.final_dst, ttl=self.sim.max_hops,
            created_at=original.created_at, protocol=self.name,
            request_id=flow_id,
            path=(original.origin, relay, original.final_dst),
            path_index=1, repair_index=4,
            backup_epoch_id=original.backup_epoch_id,
        )

        def can_start(start: float) -> bool:
            allowed = (
                self.relay_pending.get(key) is pending
                and (not pending.quiet or self.relay_mode == "unconditional")
                and abs(start - self.sim.now) <= 1e-9
                and start <= pending.received_at + 2.0 + 1e-9
            )
            if not allowed:
                self.remove_relay_pending(key)
            return allowed

        self.sim.transmit_later(
            relay, backup, delay_s=0.0,
            pending=PendingSend(can_start_at=can_start),
        )

    def on_transmit(self, sender: int, packet: Packet, start: float, end: float) -> None:
        initial_r = (sender == packet.origin and packet.kind == "DATA"
                     and packet.repair_index is None
                     and self.flow_data_actions.get(packet.flow_id) == "R")
        if initial_r:
            if start > self.sim.now + 1e-9:
                self.sim.schedule(
                    start, "protocol_timer",
                    lambda sender=sender, packet=packet, start=start, end=end:
                        self.on_transmit(sender, packet, start, end),
                )
                return
            if start > packet.created_at + self.app_deadline_s:
                self.action_events.append(
                    {"event": "dcb_initial_r_skip", "time": start,
                     "flow_id": packet.flow_id, "src": sender,
                     "reason": "after-deadline"}
                )
                return
        if (packet.kind == "DATA" and packet.repair_index == 4
                and len(packet.path) == 3 and sender == packet.path[1]):
            self.remove_relay_pending((sender, packet.flow_id))
            highwater_key = (sender, packet.origin)
            self.relay_last_forwarded_flow[highwater_key] = max(
                self.relay_last_forwarded_flow.get(highwater_key, -1),
                packet.flow_id,
            )
            self.action_events.append(
                {"event": "dcb_backup_tx", "time": start, "end": end,
                 "flow_id": packet.flow_id, "relay": sender,
                 "epoch": packet.backup_epoch_id}
            )
        super().on_transmit(sender, packet, start, end)
        if (sender == packet.origin and packet.kind == "DATA"
                and packet.repair_index is None
                and packet.path == (sender, packet.final_dst)
                and packet.backup_relay_id is not None
                and packet.backup_epoch_id is not None):
            nomination = DCBActiveNomination(
                src=sender, dst=packet.final_dst,
                relay=packet.backup_relay_id, epoch=packet.backup_epoch_id,
                start=start, deadline=packet.created_at + self.app_deadline_s,
            )
            if start <= self.sim.now + 1e-9:
                self.activate_nomination(packet.flow_id, nomination)
            else:
                self.sim.schedule(
                    start, "protocol_timer",
                    lambda flow_id=packet.flow_id, nomination=nomination:
                        self.activate_nomination(flow_id, nomination),
                )

    def activate_nomination(
        self, flow_id: int, nomination: DCBActiveNomination,
    ) -> None:
        if self.sim.now > nomination.deadline:
            return
        self.active_nominations[flow_id] = nomination
        self.sim.schedule(
            nomination.deadline + 1e-6, "protocol_timer",
            lambda flow_id=flow_id, nomination=nomination:
                self.active_nominations.pop(flow_id, None)
                if self.active_nominations.get(flow_id) is nomination else None,
        )

    def on_ack_packet(self, receiver: int, packet: Packet) -> None:
        if receiver != packet.final_dst or packet.repair_index != 4:
            super().on_ack_packet(receiver, packet)
            return
        flow = self.sim.metrics.flows.get(packet.flow_id)
        nomination = self.active_nominations.get(packet.flow_id)
        matched_path = (
            nomination is not None
            and packet.path == (nomination.src, nomination.relay, nomination.dst)
        )
        if self.relay_mode == "current-overhear" and nomination is not None:
            matched_path = (
                len(packet.path) == 3
                and packet.path[0] == nomination.src
                and packet.path[-1] == nomination.dst
                and packet.path[1] not in {nomination.src, nomination.dst}
            )
        if flow is None or nomination is None:
            reason = "inactive-flow"
        elif (receiver != flow.src or receiver != nomination.src
              or packet.origin != flow.dst or packet.origin != nomination.dst):
            reason = "endpoint-mismatch"
        elif packet.request_id != packet.flow_id:
            reason = "flow-id-mismatch"
        elif packet.path_index != 0:
            reason = "path-index-mismatch"
        elif not matched_path:
            reason = "path-mismatch"
        elif packet.backup_relay_id is not None:
            reason = "unexpected-relay-field"
        elif packet.backup_epoch_id != nomination.epoch:
            reason = "epoch-mismatch"
        elif self.sim.now < nomination.start:
            reason = "before-data-start"
        elif self.sim.now > nomination.deadline:
            reason = "deadline-expired"
        else:
            reason = "valid"
        valid = reason == "valid"
        prior_ack = flow.acked_at if flow is not None else None
        if valid:
            RoutingProtocol.on_ack_packet(self, receiver, packet)
        accepted = bool(valid and prior_ack is None and flow.acked_at is not None)
        self.action_events.append(
            {"event": "dcb_source_ack_rx", "time": self.sim.now,
             "flow_id": packet.flow_id, "accepted": accepted,
             "reason": ("accepted" if accepted else "already-acked")
             if valid else reason,
             "epoch": packet.backup_epoch_id, "path": packet.path}
        )

    def on_data(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if packet.repair_index == 4:
            if (receiver != packet.final_dst or len(packet.path) != 3
                    or len(set(packet.path)) != 3
                    or packet.path != (packet.origin, rx.sender, receiver)
                    or packet.path_index != 1
                    or packet.request_id != packet.flow_id
                    or packet.backup_relay_id is not None
                    or packet.backup_epoch_id is None):
                return
        super().on_data(receiver, packet, rx)

    def send_ack_on_reverse_path(self, receiver: int, packet: Packet) -> None:
        if packet.repair_index != 4:
            super().send_ack_on_reverse_path(receiver, packet)
            return
        if (packet.path_index <= 0 or receiver != packet.final_dst
                or packet.backup_epoch_id is None):
            return
        ack = Packet(
            kind="ACK", flow_id=packet.flow_id, origin=receiver,
            final_dst=packet.origin, ttl=self.sim.max_hops,
            created_at=self.sim.now, protocol=self.name,
            request_id=packet.request_id, path=packet.path,
            path_index=packet.path_index - 1, app_payload=False,
            repair_index=4, backup_epoch_id=packet.backup_epoch_id,
        )
        self.sim.transmit_later(receiver, ack, delay_s=0.0)

    def r_data_wire_fields(
        self, src: int, dst: int, flow_id: int, entry: RouteEntry,
        candidate: bool,
    ) -> Dict[str, int]:
        if candidate or len(entry.path) != 2:
            return {}
        state = self.destination_state.get((src, dst))
        if (state is None or state.certified_backup_relay is None
                or state.certified_backup_epoch != state.last_commit_flow
                or state.certified_backup_at is None
                or self.sim.now - state.certified_backup_at > 120.0):
            return {}
        return {
            "backup_relay_id": state.certified_backup_relay,
            "backup_epoch_id": state.certified_backup_epoch,
        }

    def on_ack(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        if packet.repair_index == 4:
            nomination = self.active_nominations.pop(flow_id, None)
            state = self.destination_state.get((receiver, packet.origin))
            current = self.route_cache.get(receiver, {}).get(packet.origin)
            if (nomination is not None and state is not None
                    and state.last_commit_flow == nomination.epoch
                    and current is not None
                    and current.path == (nomination.src, nomination.dst)):
                state.r_miss_flows.discard(flow_id)
                state.consecutive_r_misses = self.trailing_r_misses(state)
                state.had_r_miss_since_commit = bool(state.r_miss_flows)
                state.last_ack_at = now
            self.active_flows.pop(flow_id, None)
            return
        super().on_ack(flow_id, receiver, now, packet)
        self.active_nominations.pop(flow_id, None)
        if (packet.repair_index not in {None, 2}
                or (packet.repair_index is None
                    and self.flow_data_actions.get(flow_id) != "F")):
            return
        state = self.destination_state.get((receiver, packet.origin))
        current = self.route_cache.get(receiver, {}).get(packet.origin)
        if (state is None or current is None or state.last_commit_flow != flow_id
                or current.path != packet.path):
            return
        nominee = packet.backup_relay_id
        if (len(packet.path) == 2 and nominee is not None
                and nominee not in {receiver, packet.origin}):
            state.certified_backup_relay = nominee
            state.certified_backup_epoch = flow_id
            state.certified_backup_at = now
        else:
            state.certified_backup_relay = None
            state.certified_backup_epoch = None
            state.certified_backup_at = None

    def on_fallback(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if packet.kind != "FLOOD" or receiver != packet.final_dst:
            super().on_fallback(receiver, packet, rx)
            return
        path = packet.path + (receiver,)
        if (packet.request_id != packet.flow_id
                or not packet.path or packet.path[0] != packet.origin
                or packet.path_index != len(packet.path) - 1
                or packet.path[-1] != rx.sender or receiver in packet.path
                or not 2 <= len(path) <= self.sim.max_hops + 1
                or len(set(path)) != len(path)
                or packet.repair_index not in {None, 2}):
            return

        self.log_destination_rx(receiver, packet)
        key = (receiver, packet.origin, packet.flow_id, packet.repair_index)
        window = self.feedback_windows.get(key)
        if packet.flood_key in self.seen_floods[receiver]:
            self.sim.metrics.duplicate_rx += 1
            if (window is not None and self.sim.now <= window.first_at + 2.0
                    and len(window.paths) < 4
                    and all(saved != path for _, saved in window.paths)):
                window.paths.append((self.sim.now, path))
            return

        self.seen_floods[receiver].add(packet.flood_key)
        complete = replace(packet, path=path, path_index=len(path) - 1)
        self.sim.mark_delivered(packet.flow_id, receiver, complete)
        capacity = sum(item[0] == receiver for item in self.feedback_windows)
        if capacity >= 8:
            self.action_events.append(
                {"event": "dcb_feedback_capacity_overflow", "time": self.sim.now,
                 "flow_id": packet.flow_id, "src": packet.origin, "dst": receiver}
            )
            self.send_feedback_ack(receiver, complete, None)
            return
        self.feedback_windows[key] = DCBFloodWindow(
            first_at=self.sim.now, first_packet=complete,
            paths=[(self.sim.now, path)],
        )
        self.peak_feedback_windows_by_destination[receiver] = max(
            self.peak_feedback_windows_by_destination[receiver], capacity + 1,
        )
        self.action_events.append(
            {"event": "dcb_feedback_window_open", "time": self.sim.now,
             "flow_id": packet.flow_id, "src": packet.origin,
             "dst": receiver, "repair_index": packet.repair_index,
             "active_count": capacity + 1}
        )
        self.sim.schedule(
            self.sim.now + 2.0, "protocol_timer",
            lambda key=key: self.close_feedback_window(key),
        )

    def close_feedback_window(
        self, key: Tuple[int, int, int, Optional[int]],
    ) -> None:
        window = self.feedback_windows.pop(key, None)
        if window is None:
            return
        self.action_events.append(
            {"event": "dcb_feedback_window_close", "time": self.sim.now,
             "flow_id": key[2], "src": key[1], "dst": key[0],
             "repair_index": key[3],
             "active_count": sum(item[0] == key[0] for item in self.feedback_windows)}
        )
        primary = window.first_packet.path
        alternatives = [
            (when, path[1]) for when, path in window.paths[1:]
            if len(primary) == 2 and len(path) == 3
            and path[0] == primary[0] and path[-1] == primary[-1]
        ]
        nominee = min(alternatives)[1] if alternatives else None
        self.send_feedback_ack(key[0], window.first_packet, nominee)

    def send_feedback_ack(
        self, receiver: int, packet: Packet, nominee: Optional[int],
    ) -> None:
        ack = Packet(
            kind="ACK", flow_id=packet.flow_id, origin=receiver,
            final_dst=packet.origin, ttl=self.sim.max_hops,
            created_at=self.sim.now, protocol=self.name,
            request_id=packet.request_id, path=packet.path,
            path_index=packet.path_index - 1, app_payload=False,
            min_forward_margin_q=packet.min_forward_margin_q,
            min_forward_margin_hop=packet.min_forward_margin_hop,
            repair_index=packet.repair_index,
            backup_relay_id=nominee,
        )
        self.sim.transmit_later(receiver, ack, delay_s=0.0)


class MeshEchoDCBPromote(MeshEchoDCB):
    """DCB with ACK-proven backup route promotion."""

    name = "meshecho-dcb-promote"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.name = "meshecho-dcb-promote"

    def on_ack(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        nomination = (self.active_nominations.get(flow_id)
                      if packet.repair_index == 4 else None)
        current_before = self.route_cache.get(receiver, {}).get(packet.origin)
        super().on_ack(flow_id, receiver, now, packet)
        if (packet.repair_index is None
                and self.flow_data_actions.get(flow_id) == "R"
                and current_before is not None
                and current_before.path == packet.path):
            state = self.destination_state.get((receiver, packet.origin))
            if state is not None:
                state.last_direct_ack_flow = max(state.last_direct_ack_flow, flow_id)
        if nomination is None:
            return
        state = self.destination_state.get((receiver, packet.origin))
        current = self.route_cache.get(receiver, {}).get(packet.origin)
        flow = self.sim.metrics.flows.get(flow_id)
        if (flow is None or flow.acked_at != now
                or receiver != nomination.src or packet.origin != nomination.dst
                or packet.path != (nomination.src, nomination.relay, nomination.dst)
                or packet.backup_epoch_id != nomination.epoch
                or not nomination.start <= now <= nomination.deadline
                or self.flow_data_actions.get(flow_id) != "R"
                or state is None or state.last_commit_flow != nomination.epoch
                or state.certified_backup_relay != nomination.relay
                or state.certified_backup_epoch != nomination.epoch
                or state.certified_backup_at is None
                or current is None or current.expires_at <= now
                or current.path != (nomination.src, nomination.dst)
                or self.flow_sent_paths.get(flow_id) != current.path
                or state.last_direct_ack_flow > flow_id
                or flow_id <= state.last_commit_flow):
            return
        state.last_commit_flow = flow_id
        state.last_ack_at = now
        state.consecutive_f_misses = 0
        state.consecutive_r_misses = 0
        state.had_r_miss_since_commit = False
        state.f_miss_flows.clear()
        state.r_miss_flows.clear()
        state.recent_r_flows.clear()
        state.certified_backup_relay = None
        state.certified_backup_epoch = None
        state.certified_backup_at = None
        self.route_cache[receiver][packet.origin] = RouteEntry(
            created_at=now, expires_at=now + self.route_ttl_s,
            path=packet.path, confidence=1.0,
        )
        self.action_events.append(
            {"event": "commit", "time": now, "flow_id": flow_id,
             "src": receiver, "dst": packet.origin, "action": "R-backup",
             "path": packet.path, "replaced_confirmed_path": True}
        )


class MeshEchoDCBTrial(MeshEchoDCB):
    """DCB with a one-flow trial of an ACK-proven backup path."""

    name = "meshecho-dcb-trial"

    def __init__(
        self, *args: Any, trial_enabled: bool = True,
        blind_switch: bool = False, **kwargs: Any,
    ) -> None:
        if blind_switch and not trial_enabled:
            raise ValueError("blind switch requires the switch control")
        super().__init__(*args, **kwargs)
        self.trial_enabled = trial_enabled
        self.blind_switch = blind_switch
        self.name = (
            "meshecho-dcb-trial-blind" if blind_switch else
            "meshecho-dcb-trial" if trial_enabled else
            "meshecho-dcb-trial-no-switch"
        )
        self.flow_route_generations: Dict[int, Tuple[SRDestinationState, int]] = {}

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.flow_route_generations = {}

    def route_miss_is_current(self, flow_id: int, state: SRDestinationState) -> bool:
        origin = self.flow_route_generations.get(flow_id)
        return bool(
            origin is not None and origin[0] is state
            and origin[1] == state.last_commit_flow
        )

    def commit_source_route(
        self, state: SRDestinationState, flow_id: int, src: int,
        dst: int, now: float, path: Tuple[int, ...], action: str,
    ) -> None:
        state.last_commit_flow = flow_id
        state.last_ack_at = now
        state.consecutive_f_misses = 0
        state.consecutive_r_misses = 0
        state.had_r_miss_since_commit = False
        state.f_miss_flows.clear()
        state.r_miss_flows.clear()
        state.recent_r_flows.clear()
        state.trial_path = ()
        state.trial_from_flow = 0
        state.trial_generation = 0
        state.active_trial_flow = None
        state.certified_backup_relay = None
        state.certified_backup_epoch = None
        state.certified_backup_at = None
        if path == (src, dst):
            state.last_direct_ack_flow = max(state.last_direct_ack_flow, flow_id)
        self.route_cache[src][dst] = RouteEntry(
            created_at=now, expires_at=now + self.route_ttl_s,
            path=path, confidence=1.0,
        )
        self.action_events.append(
            {"event": "commit", "time": now, "flow_id": flow_id,
             "src": src, "dst": dst, "action": action,
             "path": path, "replaced_confirmed_path": True}
        )

    def on_ack(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        nomination = (self.active_nominations.get(flow_id)
                      if packet.repair_index == 4 else None)
        state_before = self.destination_state.get((receiver, packet.origin))
        commit_before = state_before.last_commit_flow if state_before is not None else None
        current_before = self.route_cache.get(receiver, {}).get(packet.origin)
        super().on_ack(flow_id, receiver, now, packet)
        self.flow_route_generations.pop(flow_id, None)
        state = self.destination_state.get((receiver, packet.origin))
        if state is None:
            return
        if (state is state_before and state.last_commit_flow != commit_before
                and packet.repair_index in {None, 2}):
            abandoned_flow = state.active_trial_flow
            state.trial_path = ()
            state.trial_from_flow = 0
            state.trial_generation = 0
            state.active_trial_flow = None
            if abandoned_flow is not None:
                self.action_events.append(
                    {"event": "trial_abandoned", "time": now,
                     "flow_id": abandoned_flow, "reason": "new-route-commit"}
                )
        if state.active_trial_flow == flow_id:
            state.active_trial_flow = None
            if (packet.repair_index is None
                    and self.flow_data_actions.get(flow_id) == "R"
                    and packet.path == self.flow_sent_paths.get(flow_id)
                    and state.trial_generation == state.last_commit_flow
                    and state.last_direct_ack_flow <= flow_id
                    and current_before is not None
                    and current_before.path == (receiver, packet.origin)
                    and flow_id > state.last_commit_flow):
                self.commit_source_route(
                    state, flow_id, receiver, packet.origin, now,
                    packet.path, "R-trial",
                )
            return
        if (packet.repair_index is None
                and self.flow_data_actions.get(flow_id) == "R"
                and packet.path == (receiver, packet.origin)
                and packet.path == self.flow_sent_paths.get(flow_id)
                and current_before is not None
                and current_before.path != packet.path
                and flow_id > state.last_commit_flow):
            self.commit_source_route(
                state, flow_id, receiver, packet.origin, now,
                packet.path, "R-newer",
            )
        if (packet.repair_index is None
                and self.flow_data_actions.get(flow_id) == "R"
                and current_before is not None
                and current_before.path == packet.path):
            state.last_direct_ack_flow = max(state.last_direct_ack_flow, flow_id)
        current = self.route_cache.get(receiver, {}).get(packet.origin)
        if (not self.trial_enabled or nomination is None or current is None
                or state.active_trial_flow is not None
                or state.last_commit_flow != nomination.epoch
                or state.last_direct_ack_flow > flow_id
                or flow_id <= state.last_commit_flow
                or (state.trial_generation == nomination.epoch
                    and flow_id <= state.trial_from_flow)
                or current.expires_at <= now
                or current.path != (nomination.src, nomination.dst)
                or packet.path != (nomination.src, nomination.relay, nomination.dst)
                or packet.backup_epoch_id != nomination.epoch
                or self.flow_sent_paths.get(flow_id) != current.path):
            return
        if self.blind_switch:
            self.commit_source_route(
                state, flow_id, receiver, packet.origin, now,
                packet.path, "R-backup-blind",
            )
            return
        state.trial_path = packet.path
        state.trial_from_flow = flow_id
        state.trial_generation = nomination.epoch
        self.action_events.append(
            {"event": "trial_pending", "time": now, "flow_id": flow_id,
             "src": receiver, "dst": packet.origin, "path": packet.path}
        )

    def send_app(self, src: int, dst: int, flow_id: int) -> None:
        self.sim.metrics.register_flow(flow_id, src, dst, self.sim.now)
        state = self.source_state(src, dst)
        entry = self.get_route(src, dst) if dst != BROADCAST_DST else None
        usable_trial = (
            entry is not None and state.trial_path
            and state.active_trial_flow is None
            and state.trial_generation == state.last_commit_flow
            and state.last_direct_ack_flow <= state.trial_from_flow
            and entry.path == (src, dst)
        )
        if not usable_trial:
            state.trial_path = ()
        if entry is None:
            action, reason = "F", "no-confirmed-route"
        elif usable_trial:
            action, reason = "R", "ack-proven-trial"
        elif state.had_r_miss_since_commit:
            action, reason = "F", "route-ack-miss"
        else:
            action, reason = "R", "confirmed-route"
        self.flow_actions[flow_id] = action
        self.action_events.append(
            {"event": "decision", "time": self.sim.now,
             "flow_id": flow_id, "src": src, "dst": dst,
             "action": action, "reason": reason}
        )
        if action == "F":
            self.sim.metrics.route_cache_misses += 1
            self.send_flood(src, dst, flow_id)
            return
        self.sim.metrics.route_cache_hits += 1
        self.flow_route_generations[flow_id] = (state, state.last_commit_flow)
        if usable_trial:
            trial_path = state.trial_path
            state.trial_path = ()
            state.active_trial_flow = flow_id
            entry = RouteEntry(
                entry.created_at, entry.expires_at, trial_path, 1.0,
            )
        self.send_data_on_path(src, dst, flow_id, entry)

    def expire_data_ack(self, flow_id: int) -> None:
        for state in self.destination_state.values():
            if state.active_trial_flow == flow_id:
                state.active_trial_flow = None
                state.trial_path = ()
                self.action_events.append(
                    {"event": "trial_abandoned", "time": self.sim.now,
                     "flow_id": flow_id, "reason": "source-ack-guard"}
                )
                break
        super().expire_data_ack(flow_id)
        self.flow_route_generations.pop(flow_id, None)


class MeshEchoDBR(MeshEchoDHRDelayedAck):
    """Draft deadline-reserved backup recovery after a confirmed useful flood."""

    name = "meshecho-dbr"

    def __init__(
        self, *args: Any, recovery_mode: str = "selective", **kwargs: Any,
    ) -> None:
        names = {
            "selective": "meshecho-dbr",
            "fixed-f": "meshecho-dbr-fixed-f",
            "fixed-f-plain": "meshecho-dbr-fixed-f-plain",
            "same": "meshecho-dbr-same",
            "first-alt": "meshecho-dbr-first-alt",
        }
        if recovery_mode not in names:
            raise ValueError(f"unknown DBR recovery mode: {recovery_mode}")
        super().__init__(*args, **kwargs)
        self.recovery_mode = recovery_mode
        self.name = names[recovery_mode]
        self.feedback_windows: Dict[Tuple[int, int, int, Optional[int]], DBRFloodWindow] = {}

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.feedback_windows = {}

    def on_receive(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if packet.kind == "ACK" and not (
            0 <= packet.path_index < len(packet.path) - 1
            and packet.path[packet.path_index] == receiver
            and packet.path[packet.path_index + 1] == rx.sender
        ):
            return
        super().on_receive(receiver, packet, rx)

    def send_app(self, src: int, dst: int, flow_id: int) -> None:
        self.sim.metrics.register_flow(flow_id, src, dst, self.sim.now)
        state = self.source_state(src, dst)
        entry = self.get_route(src, dst) if dst != BROADCAST_DST else None
        action = "R" if entry is not None else "F"
        self.flow_actions[flow_id] = action
        self.action_events.append(
            {"event": "decision", "time": self.sim.now, "flow_id": flow_id,
             "src": src, "dst": dst, "action": action,
             "reason": "confirmed-route" if entry is not None else "no-confirmed-route"}
        )
        if entry is not None:
            self.sim.metrics.route_cache_hits += 1
            self.send_data_on_path(src, dst, flow_id, entry)
        else:
            self.sim.metrics.route_cache_misses += 1
            self.send_flood(src, dst, flow_id)

    def on_transmit(self, sender: int, packet: Packet, start: float, end: float) -> None:
        if (sender == packet.origin and packet.kind == "DATA"
                and packet.repair_index == 3):
            active = self.active_flows.get(packet.flow_id)
            if active is not None:
                active.started_marker = 3
                active.backup_started_at = start
                self.sim.schedule(
                    start + 2.0, "protocol_timer",
                    lambda flow_id=packet.flow_id: self.expire_backup_ack(flow_id),
                )
            self.action_events.append(
                {"event": "dbr_backup_tx", "time": start, "end": end,
                 "flow_id": packet.flow_id, "src": sender,
                 "dst": packet.final_dst, "path": packet.path}
            )
            return
        super().on_transmit(sender, packet, start, end)

    def backup_route_is_valid(
        self, state: SRDestinationState, active: DHRActiveFlow, now: float,
    ) -> bool:
        path = state.backup_path
        current = self.route_cache.get(active.src, {}).get(active.dst)
        return bool(
            2 <= len(path) <= self.sim.max_hops + 1
            and state.backup_generation == active.route_generation
            and state.last_commit_flow == active.route_generation
            and current is not None and current.path == active.path
            and current.expires_at > now
            and state.backup_learned_at is not None
            and (self.recovery_mode == "first-alt"
                 or now - state.backup_learned_at <= 120.0)
            and path[0] == active.src and path[-1] == active.dst
            and path[1] != active.path[1]
            and len(set(path)) == len(path)
        )

    def backup_round_trip_bound_s(self, path: Tuple[int, ...]) -> float:
        data = Packet(
            kind="DATA", flow_id=0, origin=path[0], final_dst=path[-1],
            ttl=self.sim.max_hops, created_at=0.0, protocol=self.name,
            path=path, repair_index=3,
        )
        ack = replace(data, kind="ACK", origin=path[-1],
                      final_dst=path[0], app_payload=False)
        return (len(path) - 1) * (
            self.sim.radio.packet_toa_s(data)
            + self.sim.radio.packet_toa_s(ack)
        ) + 1.0

    def flood_round_trip_bound_s(self) -> float:
        path = tuple(range(self.sim.max_hops + 1))
        data = Packet(
            kind="FLOOD", flow_id=0, origin=path[0], final_dst=path[-1],
            ttl=self.sim.max_hops, created_at=0.0, protocol=self.name,
            path=path, repair_index=2,
        )
        ack = replace(data, kind="ACK", origin=path[-1],
                      final_dst=path[0], app_payload=False,
                      alternate_path=path)
        return self.sim.max_hops * (
            self.sim.radio.packet_toa_s(data)
            + self.flood_base_delay_s + self.flood_jitter_s + 0.35
            + self.sim.radio.packet_toa_s(ack)
        ) + 3.0

    def request_recovery_flood(
        self, flow_id: int, active: DHRActiveFlow,
    ) -> None:
        flow = self.sim.metrics.flows.get(flow_id)
        if (flow is None or flow.acked_at is not None
                or self.active_flows.get(flow_id) is not active
                or active.flood_requested):
            return
        deadline_at = flow.created_at + self.app_deadline_s
        if self.sim.now + self.flood_round_trip_bound_s() > deadline_at:
            return
        active.flood_requested = True
        packet = Packet(
            kind="FLOOD", flow_id=flow_id, origin=flow.src,
            final_dst=flow.dst, ttl=self.sim.max_hops,
            created_at=flow.created_at, protocol=self.name,
            request_id=flow_id, path=(flow.src,), repair_index=2,
        )
        self.seen_floods[flow.src].add(packet.flood_key)
        def can_start_flood(start: float) -> bool:
            if self.active_flows.get(flow_id) is not active:
                reason = "active-changed"
            elif flow.acked_at is not None:
                reason = "already-acked"
            elif active.started_marker == 2:
                reason = "already-started"
            elif start > self.sim.now + 1e-9:
                reason = "source-queued"
            elif start + self.flood_round_trip_bound_s() > deadline_at:
                reason = "deadline-budget"
            else:
                return True
            active.flood_requested = False
            self.action_events.append(
                {"event": "dbr_recovery_request_drop", "time": self.sim.now,
                 "flow_id": flow_id, "src": flow.src, "dst": flow.dst,
                 "action": "F", "reason": reason,
                 "requested_start": start}
            )
            if (reason == "source-queued"
                    and start + self.flood_round_trip_bound_s() <= deadline_at):
                self.sim.schedule(
                    start, "protocol_timer",
                    lambda: self.request_recovery_flood(flow_id, active),
                )
            return False

        pending = PendingSend(can_start_at=can_start_flood)
        self.sim.transmit_later(flow.src, packet, delay_s=0.0, pending=pending)

    def expire_backup_ack(self, flow_id: int) -> None:
        active = self.active_flows.get(flow_id)
        if active is None or active.backup_started_at is None:
            return
        self.request_recovery_flood(flow_id, active)

    def expire_data_ack(self, flow_id: int) -> None:
        flow = self.sim.metrics.flows.get(flow_id)
        r_timeout = (
            flow is not None and flow.acked_at is None
            and flow_id not in self.flow_timeout_applied
            and self.flow_actions.get(flow_id) == "R"
            and self.flow_data_actions.get(flow_id) == "R"
        )
        MeshEchoSR.expire_data_ack(self, flow_id)
        if not r_timeout or flow is None:
            return
        active = self.active_flows.get(flow_id)
        state = self.destination_state.get((flow.src, flow.dst))
        def record_guard(selected_action: str, reason: str) -> None:
            self.action_events.append(
                {"event": "dbr_guard", "time": self.sim.now,
                 "flow_id": flow_id, "src": flow.src, "dst": flow.dst,
                 "decision_admitted": selected_action != "none",
                 "selected_action": selected_action, "reason": reason,
                 "route_generation": active.route_generation if active else None,
                 "backup_age_s": (
                     self.sim.now - state.backup_learned_at
                     if state is not None and state.backup_learned_at is not None
                     else None),
                }
            )

        if active is None or state is None or active.selected_action is not None:
            record_guard("none", "active-unavailable")
            return
        deadline_at = flow.created_at + self.app_deadline_s
        if self.sim.nodes[flow.src].tx_available_at > self.sim.now + 1e-9:
            record_guard("none", "source-busy")
            idle_at = self.sim.nodes[flow.src].tx_available_at
            if idle_at + self.flood_round_trip_bound_s() <= deadline_at:
                self.sim.schedule(
                    idle_at, "protocol_timer",
                    lambda: self.request_recovery_flood(flow_id, active),
                )
            return
        backup_valid = (
            self.recovery_mode in {"selective", "same", "first-alt"}
            and self.backup_route_is_valid(state, active, self.sim.now)
        )
        backup_fits = (
            backup_valid and self.sim.now + max(
                self.backup_round_trip_bound_s(state.backup_path),
                self.backup_round_trip_bound_s(active.path),
            ) + 2.0 + self.flood_round_trip_bound_s() <= deadline_at
        )
        if backup_fits:
            path = active.path if self.recovery_mode == "same" else state.backup_path
            record_guard("B", "backup-admitted")
            active.selected_action = "B"
            active.backup_path = path
            packet = Packet(
                kind="DATA", flow_id=flow_id, origin=flow.src,
                final_dst=flow.dst, ttl=self.sim.max_hops,
                created_at=flow.created_at, protocol=self.name,
                request_id=flow_id, path=path, repair_index=3,
            )
            def can_start_backup(start: float) -> bool:
                if self.active_flows.get(flow_id) is not active:
                    reason = "active-changed"
                elif flow.acked_at is not None:
                    reason = "already-acked"
                elif active.backup_started_at is not None:
                    reason = "already-started"
                elif start > self.sim.now + 1e-9:
                    reason = "source-queued"
                elif not self.backup_route_is_valid(state, active, start):
                    reason = "backup-invalid"
                elif path != (active.path if self.recovery_mode == "same"
                              else state.backup_path):
                    reason = "path-changed"
                elif start + max(
                    self.backup_round_trip_bound_s(state.backup_path),
                    self.backup_round_trip_bound_s(active.path),
                ) + 2.0 + self.flood_round_trip_bound_s() > deadline_at:
                    reason = "deadline-budget"
                else:
                    return True
                self.action_events.append(
                    {"event": "dbr_recovery_request_drop", "time": self.sim.now,
                     "flow_id": flow_id, "src": flow.src, "dst": flow.dst,
                     "action": "B", "reason": reason,
                     "requested_start": start}
                )
                if reason not in {"active-changed", "already-acked"}:
                    retry_at = max(self.sim.now, start)
                    if retry_at + self.flood_round_trip_bound_s() <= deadline_at:
                        self.sim.schedule(
                            retry_at, "protocol_timer",
                            lambda: self.request_recovery_flood(flow_id, active),
                        )
                return False

            pending = PendingSend(can_start_at=can_start_backup)
            self.sim.transmit_later(flow.src, packet, delay_s=0.0, pending=pending)
            return
        if self.sim.now + self.flood_round_trip_bound_s() <= deadline_at:
            if backup_valid:
                reason = "backup-deadline-budget"
            elif (self.route_cache.get(flow.src, {}).get(flow.dst) is not None
                  and self.route_cache[flow.src][flow.dst].expires_at <= self.sim.now):
                reason = "primary-expired"
            elif (self.recovery_mode != "first-alt" and state.backup_path
                  and state.backup_learned_at is not None
                  and self.sim.now - state.backup_learned_at > 120.0):
                reason = "backup-stale"
            else:
                reason = "backup-unavailable"
            record_guard("F", reason)
            active.selected_action = "F"
            self.request_recovery_flood(flow_id, active)
        else:
            record_guard("none", "deadline-budget")

    def on_ack_packet(self, receiver: int, packet: Packet) -> None:
        if receiver != packet.final_dst or packet.repair_index != 3:
            super().on_ack_packet(receiver, packet)
            return
        flow = self.sim.metrics.flows.get(packet.flow_id)
        active = self.active_flows.get(packet.flow_id)
        path = packet.path
        valid = (
            flow is not None and active is not None
            and receiver == flow.src and packet.origin == flow.dst
            and packet.request_id == packet.flow_id and packet.path_index == 0
            and path == active.backup_path
            and active.backup_started_at is not None
            and 2 <= len(path) <= self.sim.max_hops + 1
            and len(set(path)) == len(path)
            and self.sim.now <= flow.created_at + self.app_deadline_s
        )
        prior_ack = flow.acked_at if flow is not None else None
        if valid:
            RoutingProtocol.on_ack_packet(self, receiver, packet)
        self.action_events.append(
            {"event": "dbr_source_ack_rx", "time": self.sim.now,
             "flow_id": packet.flow_id, "src": receiver,
             "dst": packet.origin, "repair_index": 3,
             "accepted": bool(valid and prior_ack is None
                              and flow.acked_at is not None),
             "path": path}
        )

    def on_ack(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        if packet.repair_index == 3:
            flow = self.sim.metrics.flows.get(flow_id)
            state = self.destination_state.get((receiver, packet.origin))
            active = self.active_flows.get(flow_id)
            current = self.route_cache.get(receiver, {}).get(flow.dst) if flow else None
            if (flow is not None and state is not None and active is not None
                    and flow_id >= state.last_commit_flow
                    and active.route_generation == state.last_commit_flow
                    and current is not None and current.path == active.path):
                state.last_commit_flow = flow_id
                state.last_ack_at = now
                state.consecutive_r_misses = 0
                state.r_miss_flows.clear()
                state.backup_path = ()
                state.backup_generation = 0
                state.backup_learned_at = None
                self.route_cache[receiver][flow.dst] = RouteEntry(
                    created_at=now, expires_at=now + self.route_ttl_s,
                    path=packet.path, confidence=1.0,
                )
                self.action_events.append(
                    {"event": "commit", "time": now, "flow_id": flow_id,
                     "src": receiver, "dst": flow.dst,
                     "action": "B-recovery", "path": packet.path}
                )
            elif flow is not None:
                self.action_events.append(
                    {"event": "dbr_route_commit_skip", "time": now,
                     "flow_id": flow_id, "src": receiver, "dst": flow.dst,
                     "action": "B-recovery", "reason": "generation-changed"}
                )
            self.active_flows.pop(flow_id, None)
            return
        super().on_ack(flow_id, receiver, now, packet)
        if packet.repair_index not in {None, 2}:
            return
        flow = self.sim.metrics.flows.get(flow_id)
        if (flow is None or packet.repair_index != 2
                and self.flow_data_actions.get(flow_id) != "F"):
            return
        state = self.destination_state.get((receiver, flow.dst))
        current = self.route_cache.get(receiver, {}).get(flow.dst)
        if (state is None or current is None or state.last_commit_flow != flow_id
                or current.path != packet.path):
            return
        alternate = packet.alternate_path
        valid = (
            alternate and 2 <= len(alternate) <= self.sim.max_hops + 1
            and alternate[0] == receiver and alternate[-1] == flow.dst
            and len(set(alternate)) == len(alternate)
            and alternate[1] != packet.path[1]
        )
        state.backup_path = alternate if valid else ()
        state.backup_generation = flow_id if valid else 0
        state.backup_learned_at = now if valid else None

    def on_fallback(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if packet.kind != "FLOOD" or receiver != packet.final_dst:
            super().on_fallback(receiver, packet, rx)
            return
        path = packet.path + (receiver,)
        if (packet.request_id != packet.flow_id
                or not packet.path or packet.path[0] != packet.origin
                or packet.path[-1] != rx.sender or receiver in packet.path
                or not 2 <= len(path) <= self.sim.max_hops + 1
                or len(set(path)) != len(path)
                or packet.repair_index not in {None, 2}):
            return

        self.log_destination_rx(receiver, packet)
        key = (receiver, packet.origin, packet.flow_id, packet.repair_index)
        window = self.feedback_windows.get(key)
        if packet.flood_key in self.seen_floods[receiver]:
            self.sim.metrics.duplicate_rx += 1
            if (window is not None and self.sim.now <= window.first_at + 2.0
                    and path not in window.paths and len(window.paths) < 4):
                window.paths.append(path)
            return

        self.seen_floods[receiver].add(packet.flood_key)
        complete = replace(packet, path=path, path_index=len(path) - 1)
        self.sim.mark_delivered(packet.flow_id, receiver, complete)
        capacity = sum(item[0] == receiver for item in self.feedback_windows)
        if capacity >= 8:
            self.action_events.append(
                {"event": "dbr_feedback_capacity_overflow",
                 "time": self.sim.now, "flow_id": packet.flow_id,
                 "src": packet.origin, "dst": receiver,
                 "active_windows": capacity}
            )
            self.sim.schedule(
                self.sim.now + 2.0, "protocol_timer",
                lambda receiver=receiver, complete=complete:
                    self.send_feedback_ack(receiver, complete, ()),
            )
            return
        self.feedback_windows[key] = DBRFloodWindow(
            first_at=self.sim.now, first_packet=complete, paths=[path],
        )
        self.sim.schedule(
            self.sim.now + 2.0, "protocol_timer",
            lambda key=key: self.close_feedback_window(key),
        )

    def close_feedback_window(
        self, key: Tuple[int, int, int, Optional[int]],
    ) -> None:
        window = self.feedback_windows.pop(key, None)
        if window is None:
            return
        primary = window.first_packet.path
        alternatives = [
            path for path in window.paths[1:]
            if path[1] != primary[1]
        ]
        backup = min(alternatives, key=lambda path: (len(path), path)) if alternatives else ()
        if self.recovery_mode == "fixed-f-plain":
            backup = ()
        self.send_feedback_ack(key[0], window.first_packet, backup)

    def send_feedback_ack(
        self, receiver: int, packet: Packet, alternate_path: Tuple[int, ...],
    ) -> None:
        ack = Packet(
            kind="ACK", flow_id=packet.flow_id, origin=receiver,
            final_dst=packet.origin, ttl=self.sim.max_hops,
            created_at=self.sim.now, protocol=self.name,
            request_id=packet.request_id, path=packet.path,
            path_index=packet.path_index - 1, app_payload=False,
            alternate_path=alternate_path,
            min_forward_margin_q=packet.min_forward_margin_q,
            min_forward_margin_hop=packet.min_forward_margin_hop,
            repair_index=packet.repair_index,
        )
        self.sim.transmit_later(receiver, ack, delay_s=0.0)


class MeshEchoDHRDelayedAckShortGuard(MeshEchoDHRDelayedAck):
    """Fixed short source guard for initial routed DATA only."""

    def __init__(self, *args: Any, r_guard_s: int, **kwargs: Any) -> None:
        if r_guard_s not in (1, 2, 4, 8):
            raise ValueError("short R guard must be 1, 2, 4, or 8 s")
        super().__init__(*args, **kwargs)
        self.r_guard_s = r_guard_s
        self.name = f"meshecho-dhr-flood-ack-delay-guard{r_guard_s}"

    def on_transmit(self, sender: int, packet: Packet, start: float, end: float) -> None:
        super().on_transmit(sender, packet, start, end)
        if (sender == packet.origin and packet.kind == "DATA"
                and packet.repair_index is None
                and self.flow_actions.get(packet.flow_id) == "R"
                and self.flow_data_actions.get(packet.flow_id) == "R"):
            self.sim.schedule(
                start + self.r_guard_s, "protocol_timer",
                lambda flow_id=packet.flow_id: self.expire_data_ack(flow_id),
            )


@dataclass
class DHRDelayedAckRepeatState:
    first_decode_at: float
    path: Tuple[int, ...]
    repair_index: Optional[int]
    first_ack_packet: Optional[Packet] = None
    first_ack_started: bool = False


class MeshEchoDHRDelayedAckRepeat(MeshEchoDHRDelayedAck):
    """Fixed-delay FLOOD ACK with one same-path, locally bounded repeat."""

    name = "meshecho-dhr-flood-ack-delay-repeat"
    repeat_wait_s = 0.5
    repeat_window_s = 10.0
    max_active_per_destination = 8

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.name = "meshecho-dhr-flood-ack-delay-repeat"
        self.pending_ack_repeats: Dict[
            Tuple[int, int, int], DHRDelayedAckRepeatState
        ] = {}

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.pending_ack_repeats = {}

    def on_fallback(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        first_decode = (
            packet.kind == "FLOOD" and receiver == packet.final_dst
            and packet.flood_key not in self.seen_floods[receiver]
            and packet.request_id == packet.flow_id
            and packet.path and packet.path[0] == packet.origin
            and packet.path[-1] == rx.sender
            and receiver not in packet.path
            and len(set(packet.path)) == len(packet.path)
            and len(packet.path) <= self.sim.max_hops
        )
        if first_decode:
            key = (receiver, packet.origin, packet.flow_id)
            active_count = sum(
                dst == receiver for dst, _, _ in self.pending_ack_repeats
            )
            if active_count < self.max_active_per_destination:
                state = DHRDelayedAckRepeatState(
                    first_decode_at=self.sim.now,
                    path=packet.path + (receiver,),
                    repair_index=packet.repair_index,
                )
                self.pending_ack_repeats[key] = state
                self.sim.schedule(
                    math.nextafter(
                        self.sim.now + self.repeat_window_s, math.inf,
                    ),
                    "protocol_timer",
                    lambda key=key, state=state:
                        self.pending_ack_repeats.pop(key, None)
                        if self.pending_ack_repeats.get(key) is state else None,
                )
            else:
                self.action_events.append(
                    {"event": "delayed_ack_repeat_drop", "time": self.sim.now,
                     "flow_id": packet.flow_id, "dst": receiver,
                     "reason": "active-capacity"}
                )
        super().on_fallback(receiver, packet, rx)

    def send_ack_on_reverse_path(self, receiver: int, packet: Packet) -> None:
        if packet.kind != "FLOOD":
            super().send_ack_on_reverse_path(receiver, packet)
            return
        if packet.path_index <= 0 or receiver != packet.final_dst:
            return
        ack = Packet(
            kind="ACK", flow_id=packet.flow_id, origin=receiver,
            final_dst=packet.origin, ttl=self.sim.max_hops,
            created_at=self.sim.now, protocol=self.name,
            request_id=packet.request_id, path=packet.path,
            path_index=packet.path_index - 1, app_payload=False,
            min_forward_margin_q=packet.min_forward_margin_q,
            min_forward_margin_hop=packet.min_forward_margin_hop,
            repair_index=packet.repair_index,
        )
        key = (receiver, packet.origin, packet.flow_id)
        state = self.pending_ack_repeats.get(key)
        if (state is not None and state.path == packet.path
                and state.repair_index == packet.repair_index):
            state.first_ack_packet = ack
        self.sim.transmit_later(
            receiver, ack, delay_s=self.reverse_ack_delay_s(packet),
        )

    def on_transmit(self, sender: int, packet: Packet, start: float, end: float) -> None:
        super().on_transmit(sender, packet, start, end)
        if packet.kind != "ACK" or sender != packet.origin:
            return
        key = (sender, packet.final_dst, packet.flow_id)
        state = self.pending_ack_repeats.get(key)
        if (state is None or state.first_ack_started
                or packet is not state.first_ack_packet):
            return
        state.first_ack_started = True
        repeat_at = end + self.repeat_wait_s
        if repeat_at > state.first_decode_at + self.repeat_window_s:
            self.pending_ack_repeats.pop(key, None)
            self.action_events.append(
                {"event": "delayed_ack_repeat_drop", "time": repeat_at,
                 "flow_id": packet.flow_id, "dst": sender,
                 "reason": "local-window"}
            )
            return

        def admit_repeat(actual_start: float) -> bool:
            if self.pending_ack_repeats.get(key) is not state:
                return False
            self.pending_ack_repeats.pop(key, None)
            if actual_start > state.first_decode_at + self.repeat_window_s:
                self.action_events.append(
                    {"event": "delayed_ack_repeat_drop", "time": actual_start,
                     "flow_id": packet.flow_id, "dst": sender,
                     "reason": "local-window"}
                )
                return False
            self.action_events.append(
                {"event": "delayed_ack_repeat_tx", "time": actual_start,
                 "flow_id": packet.flow_id, "dst": sender,
                 "path": packet.path}
            )
            return True

        self.sim.transmit_later(
            sender, packet, delay_s=max(0.0, repeat_at - self.sim.now),
            pending=PendingSend(can_start_at=admit_repeat),
        )


class MeshEchoAFS(MeshEchoDHR):
    """Cancel a queued FLOOD relay after an off-path destination ACK decode."""

    def __init__(self, *args: Any, cancel_on_ack: bool = True, **kwargs: Any) -> None:
        super().__init__(*args, rescue_mode="flood", **kwargs)
        self.cancel_on_ack = cancel_on_ack
        self.name = "meshecho-afs" if cancel_on_ack else "meshecho-afs-nocancel"
        self.afs_pending: Dict[Tuple[int, Tuple[str, int, int, int]], AFSPendingFlood] = {}

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.afs_pending = {}

    def retire_afs_pending(self) -> None:
        for key, record in tuple(self.afs_pending.items()):
            if (record.pending.canceled or record.pending.committed
                    or self.pending_fallback.get(key) is not record.pending
                    or self.sim.now >= record.received_at + 30.0):
                del self.afs_pending[key]

    def on_fallback(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        self.retire_afs_pending()
        unseen = packet.flood_key not in self.seen_floods[receiver]
        relay = self.sim.nodes[receiver]
        valid_forward = (
            packet.kind == "FLOOD" and packet.app_payload
            and packet.repair_index in {None, 2}
            and packet.request_id == packet.flow_id
            and packet.origin != receiver != packet.final_dst
            and packet.ttl > 1 and relay.can_relay
            and bool(packet.path) and packet.path[0] == packet.origin
            and packet.path[-1] == rx.sender
            and receiver not in packet.path
            and len(set(packet.path)) == len(packet.path)
            and 1 <= len(packet.path) < self.sim.max_hops
            and packet.path_index == len(packet.path) - 1
        )
        super().on_fallback(receiver, packet, rx)
        if not unseen or not valid_forward:
            self.retire_afs_pending()
            return
        key = (receiver, packet.flood_key)
        pending = self.pending_fallback.get(key)
        if (pending is None or pending.canceled or pending.committed
                or sum(item[0] == receiver for item in self.afs_pending) >= 8):
            return
        forwarded = replace(
            packet, path=packet.path + (receiver,),
            path_index=len(packet.path), ttl=packet.ttl - 1,
        )
        record = AFSPendingFlood(forwarded, pending, self.sim.now)
        self.afs_pending[key] = record
        self.sim.schedule(
            self.sim.now + 30.0, "protocol_timer",
            lambda key=key, record=record: self.afs_pending.pop(key, None)
            if self.afs_pending.get(key) is record else None,
        )

    def on_receive(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if packet.kind == "ACK":
            self.on_overheard_ack(receiver, packet, rx)
        super().on_receive(receiver, packet, rx)

    def on_overheard_ack(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        self.retire_afs_pending()
        path = packet.path
        if not (
            not packet.app_payload and packet.flow_id > 0
            and packet.request_id == packet.flow_id
            and 2 <= len(path) <= self.sim.max_hops + 1
            and len(set(path)) == len(path)
            and path[0] == packet.final_dst and path[-1] == packet.origin
            and 0 <= packet.path_index < len(path) - 1
            and path[packet.path_index + 1] == rx.sender
            and receiver not in path
        ):
            return
        flood_key = ("FLOOD", packet.final_dst, packet.flow_id, packet.request_id)
        key = (receiver, flood_key)
        record = self.afs_pending.get(key)
        if record is None:
            return
        flood = record.packet
        if not (
            flood.final_dst == packet.origin
            and flood.repair_index == packet.repair_index
            and self.pending_fallback.get(key) is record.pending
            and not record.pending.canceled and not record.pending.committed
        ):
            return
        self.action_events.append(
            {"event": "afs_opportunity", "time": self.sim.now,
             "flow_id": packet.flow_id, "relay": receiver,
             "repair_index": packet.repair_index}
        )
        if self.cancel_on_ack:
            record.pending.canceled = True
            self.action_events.append(
                {"event": "afs_cancel", "time": self.sim.now,
                 "flow_id": packet.flow_id, "relay": receiver,
                 "repair_index": packet.repair_index}
            )
        del self.afs_pending[key]

    def on_transmit(self, sender: int, packet: Packet, start: float, end: float) -> None:
        if packet.kind == "FLOOD" and sender != packet.origin:
            self.afs_pending.pop((sender, packet.flood_key), None)
        super().on_transmit(sender, packet, start, end)


class MeshEchoBAR(MeshEchoDHR):
    """Fixed-F DHR with a bounded destination-decoded reverse ACK option."""

    ack_window_s = 1.0

    def __init__(self, *args: Any, ack_mode: str = "alternate", **kwargs: Any) -> None:
        if ack_mode not in {"alternate", "same"}:
            raise ValueError(f"unknown BAR ACK mode: {ack_mode}")
        super().__init__(*args, rescue_mode="flood", **kwargs)
        self.ack_mode = ack_mode
        self.name = f"meshecho-bar-{ack_mode}"
        self.ack_windows: Dict[Tuple[int, int, int], BARFloodWindow] = {}

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.ack_windows = {}

    def on_fallback(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if packet.kind == "FLOOD" and receiver == packet.final_dst:
            for key, window in tuple(self.ack_windows.items()):
                if (key[0] == receiver
                        and self.sim.now > window.first_at + self.ack_window_s):
                    del self.ack_windows[key]
        valid_path = (
            packet.kind == "FLOOD"
            and receiver == packet.final_dst
            and packet.request_id == packet.flow_id
            and bool(packet.path)
            and packet.path[0] == packet.origin
            and packet.path[-1] == rx.sender
            and receiver not in packet.path
            and len(set(packet.path)) == len(packet.path)
            and 2 <= len(packet.path) + 1 <= self.sim.max_hops + 1
        )
        if valid_path:
            path = packet.path + (receiver,)
            key = (receiver, packet.origin, packet.flow_id)
            window = self.ack_windows.get(key)
            if window is None and packet.flood_key not in self.seen_floods[receiver]:
                tracked = sum(key[0] == receiver for key in self.ack_windows) < 8
                self.action_events.append(
                    {"event": "bar_first_flood_rx", "time": self.sim.now,
                     "flow_id": packet.flow_id, "src": packet.origin,
                     "dst": receiver, "path": path,
                     "repair_index": packet.repair_index,
                     "tracked": tracked}
                )
                if tracked:
                    window = BARFloodWindow(self.sim.now, path, packet.repair_index)
                    self.ack_windows[key] = window
                    # Preserve eligibility for a receipt exactly at the 1-s boundary.
                    self.sim.schedule(
                        math.nextafter(
                            window.first_at + self.ack_window_s, math.inf,
                        ),
                        "protocol_timer",
                        lambda key=key, window=window:
                        self.expire_ack_window(key, window),
                    )
            elif (window is not None and not window.extra_scheduled
                    and self.sim.now - window.first_at <= self.ack_window_s
                    and packet.repair_index == window.repair_index
                    and path[-2] != window.first_path[-2]):
                window.extra_scheduled = True
                reply_path = path if self.ack_mode == "alternate" else window.first_path
                self.action_events.append(
                    {"event": "bar_candidate", "time": self.sim.now,
                     "flow_id": packet.flow_id, "src": packet.origin,
                     "dst": receiver, "first_path": window.first_path,
                     "alternate_path": path, "reply_path": reply_path,
                     "repair_index": packet.repair_index,
                     "mode": self.ack_mode}
                )
                self.send_extra_ack(receiver, packet, reply_path, window)
        super().on_fallback(receiver, packet, rx)

    def expire_ack_window(
        self, key: Tuple[int, int, int], window: BARFloodWindow,
    ) -> None:
        if self.ack_windows.get(key) is window:
            del self.ack_windows[key]

    def send_extra_ack(
        self, receiver: int, packet: Packet, path: Tuple[int, ...],
        window: BARFloodWindow,
    ) -> None:
        ack = Packet(
            kind="ACK", flow_id=packet.flow_id, origin=receiver,
            final_dst=packet.origin, ttl=self.sim.max_hops,
            created_at=self.sim.now, protocol=self.name,
            request_id=packet.request_id, path=path,
            path_index=len(path) - 2, app_payload=False,
            min_forward_margin_q=packet.min_forward_margin_q,
            min_forward_margin_hop=packet.min_forward_margin_hop,
            repair_index=packet.repair_index,
        )
        logged = False

        def can_start_extra_ack(start: float) -> bool:
            nonlocal logged
            if logged or start > window.first_at + self.ack_window_s:
                return False
            self.action_events.append(
                {"event": "bar_extra_ack_tx", "time": start,
                 "flow_id": ack.flow_id, "path": ack.path,
                 "mode": self.ack_mode}
            )
            logged = True
            return True

        pending = PendingSend(can_start_at=can_start_extra_ack)
        self.sim.transmit_later(receiver, ack, delay_s=0.0, pending=pending)


class MeshEchoMAG(MeshEchoSR):
    """Measured forward-margin feedback on the shared F/R/D data plane."""

    name = "meshecho-mag"

    def __init__(self, *args: Any, mode: str = "mag", **kwargs: Any) -> None:
        if mode not in MAG_PROTOCOL_MODES.values():
            raise ValueError(f"unknown MAG mode: {mode}")
        super().__init__(*args, mode="sr", **kwargs)
        self.mag_mode = mode
        self.name = next(name for name, candidate in MAG_PROTOCOL_MODES.items()
                         if candidate == mode)

    def source_forward_margin_q(self) -> Optional[int]:
        return 127

    def discovery_ttl_for(self, src: int, dst: int, flow_id: int) -> int:
        entry = self.get_route(src, dst)
        if entry is None:
            return self.sim.max_hops
        return min(self.sim.max_hops, len(entry.path))

    def link_confidence(self, rx: RxInfo) -> float:
        margin_db = rx.snr_db - required_snr_db(self.sim.radio.sf)
        quantized = round(clamp((margin_db + 16.0) / 32.0, 0.01, 0.99) * 255)
        return quantized / 255.0

    def estimated_action_costs(self, entry: RouteEntry) -> Tuple[float, float]:
        max_path = tuple(range(self.sim.max_hops + 1))
        request_path = tuple(range(self.discovery_ttl_for(
            entry.path[0], entry.path[-1], 0,
        ) + 1))
        hops = len(entry.path) - 1
        common = dict(
            flow_id=0, origin=entry.path[0], final_dst=entry.path[-1],
            ttl=self.sim.max_hops, created_at=self.sim.now, protocol=self.name,
        )
        rreq = Packet(kind="RREQ", path=request_path, app_payload=False,
                      path_confidence=0.5, **common)
        rrep = Packet(kind="RREP", path=entry.path, app_payload=False,
                      path_confidence=0.5, **common)
        data = Packet(kind="DATA", path=entry.path, min_forward_margin_q=127, **common)
        ack = Packet(kind="ACK", path=entry.path, app_payload=False,
                     min_forward_margin_q=0, **common)
        flood = Packet(kind="FLOOD", path=max_path,
                       min_forward_margin_q=127, **common)
        toa = self.sim.radio.packet_toa_s
        discover = 16 * toa(rreq) + hops * (toa(rrep) + toa(data) + toa(ack))
        useful_flood = 16 * toa(flood) + hops * toa(ack)
        return discover, useful_flood

    def discovery_fits_deadline(self, src: int, entry: RouteEntry) -> bool:
        hops = len(entry.path) - 1
        wait_s = self.sim.route_discovery_rrep_wait_s(
            self.rrep_wait_s, self.discovery_window_s,
            self.flood_base_delay_s + self.flood_jitter_s + 0.35,
        )
        common = dict(
            flow_id=0, origin=src, final_dst=entry.path[-1],
            ttl=self.sim.max_hops, created_at=self.sim.now, protocol=self.name,
            path=entry.path, min_forward_margin_q=127,
        )
        data_toa = self.sim.radio.packet_toa_s(Packet(kind="DATA", **common))
        ack_toa = self.sim.radio.packet_toa_s(
            Packet(kind="ACK", app_payload=False, **common)
        )
        queued_s = max(0.0, self.sim.nodes[src].tx_available_at - self.sim.now)
        return queued_s + wait_s + hops * (data_toa + ack_toa) + 3.0 <= self.app_deadline_s

    def send_app(self, src: int, dst: int, flow_id: int) -> None:
        self.sim.metrics.register_flow(flow_id, src, dst, self.sim.now)
        if dst == BROADCAST_DST:
            self.send_flood(src, dst, flow_id)
            return
        state = self.source_state(src, dst)
        recent_sends = sum(when >= self.sim.now - 300.0 for when in state.send_times)
        state.send_times = (
            [when for when in state.send_times if when >= self.sim.now - 300.0]
            + [self.sim.now]
        )[-2:]
        self.source_app_counts[src] += 1
        if self.source_app_counts[src] % 10 == 0:
            self.source_tokens[src] = 1
        entry = self.get_route(src, dst)
        eligible_discovery = (
            state.pending_discovery_flow is None
            and self.source_tokens[src] > 0
            and (
                state.last_discovery_at is None
                or self.sim.now - state.last_discovery_at >= 300.0
            )
        )
        would_discover = False
        if entry is None:
            action, reason = "F", "no-confirmed-route"
        elif state.consecutive_r_misses >= 2:
            action, reason = "F", "route-ack-misses"
        elif (not state.acked_margins_q or state.last_ack_at is None
              or self.sim.now - state.last_ack_at > 300.0):
            action, reason = "F", "stale-route-feedback"
        else:
            latest_q = state.acked_margins_q[-1]
            falling = (
                len(state.acked_margins_q) >= 2
                and state.acked_margins_q[-2] - latest_q >= 6
                and latest_q <= 12
            )
            risk = latest_q <= 6 or falling
            periodic_due = (
                self.mag_mode == "periodic"
                and self.sim.now - entry.created_at >= 180.0
            )
            if self.mag_mode == "periodic":
                should_refresh = periodic_due
            else:
                should_refresh = risk
            if not should_refresh:
                action, reason = "R", "healthy-confirmed-route"
            elif self.mag_mode == "fr":
                action, reason = "R", "risk-fr-control"
            else:
                discover_cost, flood_cost = self.estimated_action_costs(entry)
                if (recent_sends >= 2 and eligible_discovery
                        and self.discovery_fits_deadline(src, entry)
                        and discover_cost <= 1.10 * flood_cost):
                    would_discover = True
                    if self.mag_mode == "trigger-f":
                        action, reason = "F", "measured-risk-trigger-f"
                    else:
                        action = "D"
                        reason = (
                            "periodic-route-age" if periodic_due
                            else "measured-route-risk"
                        )
                else:
                    if self.mag_mode == "periodic":
                        action, reason = "R", "periodic-gate-rejected"
                    else:
                        action, reason = "R", "risk-gate-rejected-reuse"
        self.flow_actions[flow_id] = action
        self.action_events.append(
            {"event": "decision", "time": self.sim.now, "flow_id": flow_id,
             "src": src, "dst": dst, "action": action, "reason": reason}
        )
        if would_discover:
            self.source_tokens[src] -= 1
            state.last_discovery_at = self.sim.now
        if action == "D":
            self.flow_old_paths[flow_id] = entry.path
            state.pending_discovery_flow = flow_id
            self.pending_data[(src, dst)] = [flow_id]
            self.start_route_discovery(src, dst, flow_id)
            return
        if action == "R":
            self.sim.metrics.route_cache_hits += 1
            self.send_data_on_path(src, dst, flow_id, entry)
            return
        self.sim.metrics.route_cache_misses += 1
        self.send_flood(src, dst, flow_id)

    def on_ack(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        flow = self.sim.metrics.flows[flow_id]
        action = self.flow_data_actions.get(flow_id)
        super().on_ack(flow_id, receiver, now, packet)
        margin_q = packet.min_forward_margin_q
        if margin_q is None or margin_q == 127:
            return
        state = self.destination_state.get((receiver, flow.dst))
        entry = self.get_route(receiver, flow.dst)
        if (state is None or entry is None or packet.path != entry.path
                or flow_id < state.last_commit_flow):
            return
        if action == "R":
            state.acked_margins_q = (state.acked_margins_q + [margin_q])[-2:]
        elif action in {"F", "D-candidate"} and state.last_commit_flow == flow_id:
            state.acked_margins_q = [margin_q]
        else:
            return
        state.last_ack_at = now

    def with_measured_margin(self, packet: Packet, rx: RxInfo) -> Packet:
        margin_db = rx.snr_db - required_snr_db(self.sim.radio.sf)
        measured_q = int(clamp(round(2.0 * margin_db), -126, 126))
        inherited_q = packet.min_forward_margin_q
        if inherited_q is None:
            return packet
        measured_hop = (
            len(packet.path) if packet.kind == "FLOOD" else packet.path_index + 1
        )
        if inherited_q != 127 and measured_q >= inherited_q:
            return packet
        return replace(
            packet,
            min_forward_margin_q=measured_q,
            min_forward_margin_hop=(
                measured_hop if packet.min_forward_margin_hop is not None else None
            ),
        )

    def on_receive(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if packet.kind in {"DATA", "FLOOD"}:
            packet = self.with_measured_margin(packet, rx)
        super().on_receive(receiver, packet, rx)


class MeshEchoUGR(MeshEchoMAG):
    """Utility-gated source routing with ACK-carried local feedback.

    UGR replaces SR's fixed F/R/D trigger table with a source-local posterior
    over each action.  The simulator, packet formats, route discovery and
    ACK validation remain shared with the tested SR implementation; only the
    action-selection and online accounting policy are new.
    """

    name = "meshecho-ugr"

    def __init__(self, *args: Any, mode: str = "utility", **kwargs: Any) -> None:
        if mode not in set(UGR_PROTOCOL_MODES.values()):
            raise ValueError(f"unknown UGR mode: {mode}")
        super().__init__(*args, mode="mag", **kwargs)
        self.ugr_mode = mode
        self.name = next(
            name for name, candidate in UGR_PROTOCOL_MODES.items()
            if candidate == mode
        )
        self.utility_recorded: Set[int] = set()

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.utility_recorded = set()

    @staticmethod
    def _count(state: SRDestinationState, table: str, action: str) -> int:
        values = getattr(state, table)
        return max(0, int(values.get(action, 0)))

    def estimate_action_costs(
        self, src: int, dst: int, entry: RouteEntry,
    ) -> Tuple[float, float, float]:
        """Estimate charged route, flood and discovery ToA from local state."""

        hops = max(1, len(entry.path) - 1)
        common = dict(
            flow_id=0,
            origin=src,
            final_dst=dst,
            ttl=self.sim.max_hops,
            created_at=self.sim.now,
            protocol=self.name,
            request_id=0,
        )
        data = Packet(kind="DATA", path=entry.path, **common)
        ack = Packet(
            kind="ACK", path=entry.path, path_index=len(entry.path) - 2,
            app_payload=False, **common,
        )
        flood = Packet(
            kind="FLOOD", path=(src,), app_payload=True, **common,
        )
        rreq = Packet(
            kind="RREQ", path=(src,), path_confidence=1.0,
            app_payload=False, **common,
        )
        rrep = Packet(
            kind="RREP", path=tuple(reversed(entry.path)),
            learned_path=entry.path, path_confidence=1.0,
            app_payload=False, **common,
        )
        toa = self.sim.radio.packet_toa_s
        route_cost = hops * (toa(data) + toa(ack))
        flood_cost = self.useful_flood_ttl() * toa(flood) + toa(ack)
        discovery_cost = (
            16 * toa(rreq) + hops * (toa(rrep) + toa(data) + toa(ack))
        )
        return route_cost, flood_cost, discovery_cost

    def _observation(
        self, src: int, dst: int, state: SRDestinationState,
        entry: RouteEntry,
    ) -> UtilityObservation:
        route_cost, flood_cost, discovery_cost = self.estimate_action_costs(
            src, dst, entry,
        )
        latest = state.acked_margins_q[-1] if state.acked_margins_q else None
        previous = (
            state.acked_margins_q[-2]
            if len(state.acked_margins_q) >= 2 else None
        )
        flow = self.sim.metrics.flows.get(max(self.flow_actions, default=0))
        remaining = self.app_deadline_s
        if flow is not None:
            remaining = max(0.0, flow.created_at + self.app_deadline_s - self.sim.now)
        return UtilityObservation(
            route_available=True,
            route_age_s=max(0.0, self.sim.now - entry.created_at),
            route_hops=max(1, len(entry.path) - 1),
            route_ttl_s=self.route_ttl_s,
            remaining_deadline_s=remaining,
            token_available=self.source_tokens[src] > 0,
            recent_demand=sum(
                when >= self.sim.now - 300.0 for when in state.send_times
            ) >= 2,
            r_attempts=self._count(state, "utility_attempts", "R"),
            r_acks=self._count(state, "utility_acks", "R"),
            f_attempts=self._count(state, "utility_attempts", "F"),
            f_acks=self._count(state, "utility_acks", "F"),
            d_attempts=self._count(state, "utility_attempts", "D"),
            d_acks=self._count(state, "utility_acks", "D"),
            latest_margin_q=latest,
            previous_margin_q=previous,
            consecutive_r_misses=state.consecutive_r_misses,
            route_cost_s=route_cost,
            flood_cost_s=flood_cost,
            discovery_cost_s=discovery_cost,
        )

    def _choose_action(
        self, src: int, dst: int, state: SRDestinationState,
        entry: Optional[RouteEntry],
    ) -> Tuple[str, str]:
        if entry is None:
            return "F", "no-confirmed-route"
        observation = self._observation(src, dst, state, entry)
        if self.ugr_mode == "no-feedback":
            observation = replace(
                observation, latest_margin_q=None, previous_margin_q=None,
            )
        decision = choose_action(observation)
        action = decision.action.value
        reason = decision.reason
        if action == "D" and self.ugr_mode in {"fr", "trigger-f"}:
            action = "F"
            reason = "discovery-disabled-control"
        return action, reason

    def _record_attempt(self, state: SRDestinationState, action: str) -> None:
        state.utility_attempts[action] = state.utility_attempts.get(action, 0) + 1

    def _record_ack(self, flow_id: int) -> None:
        if flow_id in self.utility_recorded:
            return
        flow = self.sim.metrics.flows.get(flow_id)
        action = self.flow_actions.get(flow_id)
        if flow is None or action not in {"R", "F", "D"}:
            return
        state = self.destination_state.get((flow.src, flow.dst))
        if state is None:
            return
        state.utility_acks[action] = state.utility_acks.get(action, 0) + 1
        self.utility_recorded.add(flow_id)

    def send_app(self, src: int, dst: int, flow_id: int) -> None:
        self.sim.metrics.register_flow(flow_id, src, dst, self.sim.now)
        if dst == BROADCAST_DST:
            self.send_flood(src, dst, flow_id)
            return
        state = self.source_state(src, dst)
        state.send_times = (
            [when for when in state.send_times if when >= self.sim.now - 300.0]
            + [self.sim.now]
        )[-2:]
        self.source_app_counts[src] += 1
        if self.source_app_counts[src] % 10 == 0:
            self.source_tokens[src] = 1
        entry = self.get_route(src, dst)
        action, reason = self._choose_action(src, dst, state, entry)
        self.flow_actions[flow_id] = action
        self._record_attempt(state, action)
        self.action_events.append(
            {"event": "decision", "time": self.sim.now, "flow_id": flow_id,
             "src": src, "dst": dst, "action": action, "reason": reason,
             "controller": "utility-gated",
             "route_attempts": self._count(state, "utility_attempts", "R"),
             "route_acks": self._count(state, "utility_acks", "R"),
             "flood_attempts": self._count(state, "utility_attempts", "F"),
             "flood_acks": self._count(state, "utility_acks", "F"),
             "discovery_attempts": self._count(state, "utility_attempts", "D"),
             "discovery_acks": self._count(state, "utility_acks", "D")}
        )
        if action == "D":
            if entry is None:
                raise RuntimeError("UGR discovery requires a confirmed route")
            self.source_tokens[src] = max(0, self.source_tokens[src] - 1)
            state.last_discovery_at = self.sim.now
            state.pending_discovery_flow = flow_id
            self.flow_old_paths[flow_id] = entry.path
            self.pending_data[(src, dst)] = [flow_id]
            self.start_route_discovery(src, dst, flow_id)
            return
        if action == "R" and entry is not None:
            self.sim.metrics.route_cache_hits += 1
            self.send_data_on_path(src, dst, flow_id, entry)
            return
        self.sim.metrics.route_cache_misses += 1
        self.send_flood(src, dst, flow_id)

    def expire_data_ack(self, flow_id: int) -> None:
        super().expire_data_ack(flow_id)
        if flow_id in self.utility_recorded:
            return
        flow = self.sim.metrics.flows.get(flow_id)
        if flow is not None and flow.acked_at is None:
            self.utility_recorded.add(flow_id)

    def on_ack(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        super().on_ack(flow_id, receiver, now, packet)
        self._record_ack(flow_id)


class MeshEchoLPR(MeshEchoMAG):
    """Indexed feedback foundation for localized payload repair."""

    name = "meshecho-lpr"

    def __init__(self, *args: Any, mode: str = "lpr", **kwargs: Any) -> None:
        if mode not in LPR_PROTOCOL_MODES.values():
            raise ValueError(f"unknown LPR mode: {mode}")
        super().__init__(*args, mode="mag", **kwargs)
        self.lpr_mode = mode
        self.name = next(name for name, candidate in LPR_PROTOCOL_MODES.items()
                         if candidate == mode)
        self.heard_neighbors: Dict[int, Dict[int, Tuple[float, float]]] = {}
        self.flow_repair_indices: Dict[int, int] = {}
        self.pending_patch_relays: Dict[Tuple[int, int], Tuple[PendingSend, int]] = {}
        self.seen_patch_relays: Dict[int, List[int]] = {}
        self.seen_patch_targets: Dict[int, List[int]] = {}

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.heard_neighbors = {node_id: {} for node_id in sim.nodes}
        self.flow_repair_indices = {}
        self.pending_patch_relays = {}
        self.seen_patch_relays = {node_id: [] for node_id in sim.nodes}
        self.seen_patch_targets = {node_id: [] for node_id in sim.nodes}

    def remember_neighbor(self, receiver: int, rx: RxInfo) -> None:
        heard = self.heard_neighbors[receiver]
        heard.pop(rx.sender, None)
        heard[rx.sender] = (
            self.sim.now, rx.snr_db - required_snr_db(self.sim.radio.sf)
        )
        if len(heard) > 8:
            heard.pop(next(iter(heard)))

    def has_recent_successor_observation(self, receiver: int, successor: int) -> bool:
        observation = self.heard_neighbors[receiver].get(successor)
        return bool(
            observation is not None
            and self.sim.now - observation[0] <= 300.0
            and observation[1] >= 0.0
        )

    def source_forward_margin_hop(self) -> Optional[int]:
        return 255

    def repair_fits_deadline(self, src: int, entry: RouteEntry) -> bool:
        hops = len(entry.path)
        data = Packet(
            kind="DATA", flow_id=0, origin=src, final_dst=entry.path[-1],
            ttl=self.sim.max_hops, created_at=self.sim.now, protocol=self.name,
            path=entry.path, min_forward_margin_q=127,
            min_forward_margin_hop=255, repair_index=1,
        )
        ack = replace(data, kind="ACK", app_payload=False, repair_index=None)
        queued_s = max(0.0, self.sim.nodes[src].tx_available_at - self.sim.now)
        return (
            queued_s + hops * (self.sim.radio.packet_toa_s(data)
                               + self.sim.radio.packet_toa_s(ack))
            + self.flood_base_delay_s + self.flood_jitter_s + 3.0
            <= self.app_deadline_s
        )

    def send_app(self, src: int, dst: int, flow_id: int) -> None:
        self.sim.metrics.register_flow(flow_id, src, dst, self.sim.now)
        if dst == BROADCAST_DST:
            self.send_flood(src, dst, flow_id)
            return
        state = self.source_state(src, dst)
        recent_sends = sum(when >= self.sim.now - 300.0 for when in state.send_times)
        state.send_times = (
            [when for when in state.send_times if when >= self.sim.now - 300.0]
            + [self.sim.now]
        )[-2:]
        self.source_app_counts[src] += 1
        if self.source_app_counts[src] % 10 == 0:
            self.source_tokens[src] = 1
        entry = self.get_route(src, dst)
        if entry is None:
            action, reason = "F", "no-confirmed-route"
        elif state.consecutive_r_misses >= 2:
            action, reason = "F", "route-ack-misses"
        elif (not state.acked_margins_q or not state.acked_margin_hops
              or state.last_ack_at is None
              or self.sim.now - state.last_ack_at > 300.0):
            action, reason = "F", "stale-route-feedback"
        else:
            latest_q = state.acked_margins_q[-1]
            falling = (
                len(state.acked_margins_q) >= 2
                and state.acked_margins_q[-2] - latest_q >= 6
                and latest_q <= 12
            )
            risk = latest_q <= 6 or falling
            trigger = (
                self.sim.now - entry.created_at >= 180.0
                if self.lpr_mode == "periodic" else risk
            )
            weak_hop = state.acked_margin_hops[-1]
            eligible = (
                trigger and recent_sends >= 2 and self.source_tokens[src] > 0
                and (state.last_repair_at is None
                     or self.sim.now - state.last_repair_at >= 300.0)
                and 1 <= weak_hop < len(entry.path)
                and len(entry.path) <= self.sim.max_hops
                and self.repair_fits_deadline(src, entry)
            )
            if eligible and self.lpr_mode == "fr":
                action, reason = "R", "fr-only-control"
            elif eligible and self.lpr_mode == "trigger-f":
                action, reason = "F", "risk-trigger-full-flood-control"
                self.source_tokens[src] -= 1
                state.last_repair_at = self.sim.now
            elif eligible:
                action, reason = (
                    "P",
                    "periodic-route-age" if self.lpr_mode == "periodic" else
                    "unobserved-edge-control" if self.lpr_mode == "unobserved-edge" else
                    "ack-indexed-weak-edge",
                )
            else:
                action, reason = "R", "confirmed-route"
        self.flow_actions[flow_id] = action
        self.action_events.append(
            {"event": "decision", "time": self.sim.now, "flow_id": flow_id,
             "src": src, "dst": dst, "action": action, "reason": reason}
        )
        if action == "P":
            self.sim.metrics.route_cache_hits += 1
            self.source_tokens[src] -= 1
            state.last_repair_at = self.sim.now
            selected_hop = (
                random.Random(f"lpr-edge:{self.sim.seed}:{flow_id}").randrange(
                    1, len(entry.path)
                )
                if self.lpr_mode == "unobserved-edge" else weak_hop
            )
            self.flow_old_paths[flow_id] = entry.path
            self.flow_repair_indices[flow_id] = selected_hop
            self.sim.schedule(
                self.sim.now + self.app_deadline_s + 1e-6,
                "protocol_timer",
                lambda flow_id=flow_id: self.flow_repair_indices.pop(flow_id, None),
            )
            self.flow_data_actions[flow_id] = "P"
            self.flow_sent_paths[flow_id] = entry.path
            packet = Packet(
                kind="DATA", flow_id=flow_id, origin=src, final_dst=dst,
                ttl=self.sim.max_hops,
                created_at=self.sim.metrics.flows[flow_id].created_at,
                protocol=self.name, request_id=flow_id, path=entry.path,
                min_forward_margin_q=127, min_forward_margin_hop=255,
                repair_index=selected_hop,
            )
            if selected_hop == 1:
                self.send_patch(src, packet)
            else:
                self.sim.transmit_later(src, packet, delay_s=0.0)
            return
        if action == "R":
            self.sim.metrics.route_cache_hits += 1
            self.send_data_on_path(src, dst, flow_id, entry)
            return
        self.sim.metrics.route_cache_misses += 1
        self.send_flood(src, dst, flow_id)

    def send_patch(self, sender: int, packet: Packet) -> None:
        self.sim.transmit_later(sender, replace(packet, kind="PATCH"), delay_s=0.0)

    def on_transmit(self, sender: int, packet: Packet, start: float, end: float) -> None:
        if packet.kind == "PATCH_RELAY":
            self.pending_patch_relays.pop((sender, packet.flow_id), None)
        if packet.kind == "PATCH" and sender == packet.origin:
            self.sim.schedule(
                start + self.ack_guard_s, "protocol_timer",
                lambda flow_id=packet.flow_id: self.expire_data_ack(flow_id),
            )
            return
        super().on_transmit(sender, packet, start, end)

    def on_data(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if packet.repair_index is None:
            super().on_data(receiver, packet, rx)
            return
        if not self.path_next_hop_matches(receiver, packet):
            return
        advanced = packet.advance_path()
        if receiver == packet.final_dst:
            self.sim.mark_delivered(packet.flow_id, receiver, advanced)
            self.send_ack_on_reverse_path(receiver, advanced)
        elif advanced.path_index + 1 == packet.repair_index:
            self.send_patch(receiver, advanced)
        else:
            self.sim.transmit_later(receiver, advanced, delay_s=0.0)

    def on_receive(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        self.remember_neighbor(receiver, rx)
        pending_relay = self.pending_patch_relays.get((receiver, packet.flow_id))
        if pending_relay is not None:
            pending, successor = pending_relay
            successor_continued = (
                rx.sender == successor and packet.kind in {"DATA", "ACK"}
            )
            earlier_candidate = (
                packet.kind == "PATCH_RELAY"
                and packet.repair_index is not None
                and 0 <= packet.path_index < len(packet.path)
                and packet.repair_index == packet.path_index + 1
                and packet.repair_index < len(packet.path)
                and packet.path[packet.path_index] == rx.sender
                and packet.path[packet.repair_index] == successor
            )
            if (not pending.canceled and not pending.committed
                    and (successor_continued or earlier_candidate)):
                pending.canceled = True
                self.sim.metrics.suppressed_forwards += 1
                self.pending_patch_relays.pop((receiver, packet.flow_id), None)
        if packet.kind not in {"PATCH", "PATCH_RELAY"}:
            super().on_receive(receiver, packet, rx)
            return
        packet = self.with_measured_margin(packet, rx)
        if (packet.repair_index is None
                or packet.repair_index != packet.path_index + 1
                or packet.repair_index >= len(packet.path)):
            return
        successor = packet.path[packet.repair_index]
        if receiver != successor:
            if (packet.kind != "PATCH" or receiver in packet.path
                    or not self.sim.nodes[receiver].can_relay
                    or len(packet.path) > self.sim.max_hops
                    or not self.has_recent_successor_observation(receiver, successor)):
                return
            key = (receiver, packet.flow_id)
            seen = self.seen_patch_relays[receiver]
            if packet.flow_id in seen:
                return
            seen.append(packet.flow_id)
            if len(seen) > 128:
                seen.pop(0)
            detour = packet.path[:packet.repair_index] + (receiver,) + packet.path[packet.repair_index:]
            relay = replace(
                packet, kind="PATCH_RELAY", path=detour,
                path_index=packet.repair_index,
                repair_index=packet.repair_index + 1,
                ttl=packet.ttl - 1,
            )
            self.pending_patch_relays[key] = (
                self.sim.transmit_later(
                    receiver, relay, delay_s=self.flood_delay(receiver, rx)
                ),
                successor,
            )
            return
        seen = self.seen_patch_targets[receiver]
        if packet.flow_id in seen:
            self.sim.metrics.duplicate_rx += 1
            return
        seen.append(packet.flow_id)
        if len(seen) > 128:
            seen.pop(0)
        advanced = packet.advance_path()
        continued = replace(advanced, kind="DATA", repair_index=None)
        if receiver == packet.final_dst:
            self.sim.mark_delivered(packet.flow_id, receiver, continued)
            self.send_ack_on_reverse_path(receiver, continued)
        else:
            self.sim.transmit_later(receiver, continued, delay_s=0.0)

    def on_ack_packet(self, receiver: int, packet: Packet) -> None:
        if (receiver == packet.final_dst
                and self.flow_data_actions.get(packet.flow_id) == "P"):
            flow = self.sim.metrics.flows.get(packet.flow_id)
            old_path = self.flow_old_paths.get(packet.flow_id)
            repair_index = self.flow_repair_indices.get(packet.flow_id)
            if (flow is None or old_path is None or repair_index is None
                    or receiver != flow.src
                    or packet.origin != flow.dst
                    or packet.request_id != packet.flow_id
                    or self.sim.now > flow.created_at + self.app_deadline_s
                    or not self.ack_next_hop_matches(receiver, packet)
                    or not self.valid_repair_path(old_path, packet.path, repair_index)):
                return
            self.sim.mark_acknowledged(packet.flow_id, receiver, packet)
            return
        super().on_ack_packet(receiver, packet)

    def valid_repair_path(
        self, old_path: Tuple[int, ...], actual: Tuple[int, ...], repair_index: int,
    ) -> bool:
        if len(actual) - 1 > self.sim.max_hops:
            return False
        if actual == old_path:
            return True
        return bool(
            len(actual) == len(old_path) + 1
            and actual[:repair_index] == old_path[:repair_index]
            and actual[repair_index] not in old_path
            and actual[repair_index + 1:] == old_path[repair_index:]
        )

    def on_ack(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        action = self.flow_data_actions.get(flow_id)
        super().on_ack(flow_id, receiver, now, packet)
        if action == "P":
            self.flow_repair_indices.pop(flow_id, None)
        state = self.destination_state.get((receiver, self.sim.metrics.flows[flow_id].dst))
        if state is None or packet.min_forward_margin_hop is None:
            return
        if action == "R":
            state.acked_margin_hops = (state.acked_margin_hops
                                       + [packet.min_forward_margin_hop])[-2:]
        elif action in {"F", "P"} and state.last_commit_flow == flow_id:
            state.acked_margin_hops = [packet.min_forward_margin_hop]
            if action == "P" and packet.min_forward_margin_q is not None:
                state.acked_margins_q = [packet.min_forward_margin_q]
                state.last_ack_at = now


class MeshEchoDPA(MeshEchoSR):
    """DATA-first F/R routing with one destination-decoded alternate ACK path."""

    name = "meshecho-dpa"
    ack_window_s = 3.0

    def __init__(self, *args: Any, ack_mode: str = "diverse", **kwargs: Any) -> None:
        if ack_mode not in {"diverse", "repeat", "single"}:
            raise ValueError(f"unknown DPA ACK mode: {ack_mode}")
        super().__init__(*args, mode="fr", **kwargs)
        self.ack_mode = ack_mode
        self.name = {
            "diverse": "meshecho-dpa",
            "repeat": "meshecho-dpa-repeat",
            "single": "meshecho-dpa-fr",
        }[ack_mode]
        self.first_flood_paths: Dict[
            Tuple[int, Tuple[str, int, int, int]], Tuple[float, Tuple[int, ...]]
        ] = {}
        self.second_ack_flows: Set[Tuple[int, Tuple[str, int, int, int]]] = set()

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.first_flood_paths = {}
        self.second_ack_flows = set()

    def on_ack_packet(self, receiver: int, packet: Packet) -> None:
        if receiver != packet.final_dst:
            super().on_ack_packet(receiver, packet)
            return
        flow = self.sim.metrics.flows.get(packet.flow_id)
        if flow is None:
            return
        prior_ack = flow.acked_at
        if (packet.origin == flow.dst and len(packet.path) >= 2
                and packet.path[0] == flow.src and packet.path[-1] == flow.dst):
            super().on_ack_packet(receiver, packet)
        if self.flow_data_actions.get(packet.flow_id) == "F":
            self.action_events.append(
                {"event": "dpa_source_ack_rx", "time": self.sim.now,
                 "flow_id": packet.flow_id, "src": receiver, "dst": flow.dst,
                 "action": "F", "path": packet.path,
                 "on_path": self.ack_next_hop_matches(receiver, packet),
                 "accepted": prior_ack is None and flow.acked_at is not None}
            )

    def on_transmit(self, sender: int, packet: Packet, start: float, end: float) -> None:
        super().on_transmit(sender, packet, start, end)
        if (packet.kind == "ACK" and sender == packet.origin
                and self.flow_data_actions.get(packet.flow_id) == "F"):
            self.action_events.append(
                {"event": "dpa_ack_tx", "time": start, "end": end,
                 "flow_id": packet.flow_id, "src": packet.final_dst,
                 "dst": sender, "action": "F", "path": packet.path}
            )

    def on_fallback(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if packet.kind != "FLOOD" or receiver != packet.final_dst:
            super().on_fallback(receiver, packet, rx)
            return
        realized_path = packet.path + (receiver,)
        if (not packet.path
                or packet.path[0] != packet.origin
                or packet.path[-1] != rx.sender
                or receiver in packet.path
                or len(set(realized_path)) != len(realized_path)
                or len(realized_path) - 1 > self.sim.max_hops):
            return
        key = (receiver, packet.flood_key)
        first = self.first_flood_paths.get(key)
        was_seen = packet.flood_key in self.seen_floods[receiver]
        super().on_fallback(receiver, packet, rx)
        if not was_seen:
            first_at = self.sim.now
            first_path = realized_path
            self.action_events.append(
                {"event": "dpa_first_path", "time": first_at,
                 "flow_id": packet.flow_id, "src": packet.origin, "dst": receiver,
                 "action": "F", "path": first_path}
            )
            if self.ack_mode == "single":
                return
            active = [item for item in self.first_flood_paths if item[0] == receiver]
            if len(active) >= 8:
                oldest = min(active, key=lambda item: self.first_flood_paths[item][0])
                self.expire_ack_window(oldest, self.first_flood_paths[oldest][0])
            self.first_flood_paths[key] = (first_at, first_path)
            self.sim.schedule(
                first_at + self.ack_window_s, "protocol_timer",
                lambda key=key, first_at=first_at: self.expire_ack_window(key, first_at),
            )
            return
        if self.ack_mode == "single" or first is None or key in self.second_ack_flows:
            return
        first_at, first_path = first
        alternate = realized_path
        if (self.sim.now - first_at >= self.ack_window_s
                or alternate == first_path
                or len(alternate) < 3
                or alternate[1] == first_path[1]):
            return
        self.second_ack_flows.add(key)
        self.action_events.append(
            {"event": "dpa_second_path", "time": self.sim.now,
             "flow_id": packet.flow_id, "src": packet.origin, "dst": receiver,
             "action": "F", "first_path": first_path,
             "second_path": alternate}
        )
        reply_path = alternate if self.ack_mode == "diverse" else first_path
        self.send_ack_on_reverse_path(
            receiver, replace(packet, path=reply_path, path_index=len(reply_path) - 1)
        )

    def expire_ack_window(
        self, key: Tuple[int, Tuple[str, int, int, int]], first_at: float,
    ) -> None:
        first = self.first_flood_paths.get(key)
        if first is not None and first[0] == first_at:
            del self.first_flood_paths[key]
            self.second_ack_flows.discard(key)


class MeshEchoRAC(MeshEchoDPA):
    """DATA-conditioned, off-path relay for a first FLOOD's reverse ACK."""

    name = "meshecho-rac"
    relay_wait_s = 0.20

    def __init__(self, *args: Any, mode: str = "corridor", **kwargs: Any) -> None:
        if mode not in {"corridor", "repeat", "fr"}:
            raise ValueError(f"unknown RAC mode: {mode}")
        super().__init__(*args, ack_mode="single", **kwargs)
        self.mode_rac = mode
        self.name = {
            "corridor": "meshecho-rac",
            "repeat": "meshecho-rac-repeat",
            "fr": "meshecho-rac-fr",
        }[mode]
        self.flood_senders: Dict[Tuple[int, int, int, int, int], Set[int]] = {}
        self.scheduled_repairs: Dict[Tuple[int, int, int, int], None] = {}
        self.attempted_repairs: Set[Tuple[int, int, int, int]] = set()
        self.scheduled_repeats: Dict[Tuple[int, int, int, int], None] = {}
        self.attempted_repeats: Set[Tuple[int, int, int, int]] = set()
        self.seen_ack_hops: Set[Tuple[int, int, int, Tuple[int, ...]]] = set()

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.flood_senders = {}
        self.scheduled_repairs = {}
        self.attempted_repairs = set()
        self.scheduled_repeats = {}
        self.attempted_repeats = set()
        self.seen_ack_hops = set()

    def valid_f_ack_packet(self, packet: Packet) -> bool:
        flow = self.sim.metrics.flows.get(packet.flow_id)
        return bool(
            flow is not None
            and self.flow_data_actions.get(packet.flow_id) == "F"
            and packet.request_id == packet.flow_id
            and packet.origin == flow.dst
            and packet.final_dst == flow.src
            and len(packet.path) >= 2
            and packet.path[0] == flow.src
            and packet.path[-1] == flow.dst
            and len(set(packet.path)) == len(packet.path)
            and len(packet.path) - 1 <= self.sim.max_hops
            and self.sim.now < flow.created_at + self.app_deadline_s
        )

    def on_ack_packet(self, receiver: int, packet: Packet) -> None:
        flow = self.sim.metrics.flows.get(packet.flow_id)
        at_source = (flow is not None and receiver == packet.final_dst
                     and self.flow_data_actions.get(packet.flow_id) == "F")
        prior_ack = flow.acked_at if at_source else None
        if (receiver != packet.final_dst
                and self.flow_data_actions.get(packet.flow_id) == "F"):
            if (not self.valid_f_ack_packet(packet)
                    or not self.ack_next_hop_matches(receiver, packet)
                    or packet.ttl <= 1):
                return
            key = (receiver, packet.flow_id, packet.request_id, packet.path)
            if key in self.seen_ack_hops:
                return
            self.seen_ack_hops.add(key)
            flow = self.sim.metrics.flows[packet.flow_id]
            self.sim.schedule(
                flow.created_at + self.app_deadline_s,
                "protocol_timer",
                lambda key=key: self.seen_ack_hops.discard(key),
            )
        super().on_ack_packet(receiver, packet)
        if at_source:
            self.action_events.append(
                {"event": "rac_source_ack_rx", "time": self.sim.now,
                 "flow_id": packet.flow_id, "src": receiver, "dst": flow.dst,
                 "path": packet.path, "repair_index": packet.repair_index,
                 "on_path": self.ack_next_hop_matches(receiver, packet),
                 "accepted": prior_ack is None and flow.acked_at is not None}
            )

    def send_ack_on_reverse_path(self, receiver: int, packet: Packet) -> None:
        if packet.kind != "FLOOD":
            super().send_ack_on_reverse_path(receiver, packet)
            return
        if packet.path_index <= 0 or receiver != packet.final_dst:
            return
        ack = Packet(
            kind="ACK", flow_id=packet.flow_id, origin=receiver,
            final_dst=packet.origin, ttl=self.sim.max_hops,
            created_at=self.sim.now, protocol=self.name,
            request_id=packet.request_id, path=packet.path,
            path_index=packet.path_index - 1, app_payload=False,
            repair_index=255,
        )
        self.sim.transmit_later(receiver, ack, delay_s=0.0)

    def on_receive(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if (packet.kind == "FLOOD" and packet.path
                and packet.path[-1] == rx.sender
                and packet.path[0] == packet.origin):
            key = (receiver, packet.origin, packet.final_dst,
                   packet.flow_id, packet.request_id)
            if key not in self.flood_senders:
                active = [item for item in self.flood_senders if item[0] == receiver]
                if len(active) >= 8:
                    del self.flood_senders[active[0]]
                senders: Set[int] = set()
                self.flood_senders[key] = senders
                self.sim.schedule(
                    self.sim.now + 30.0, "protocol_timer",
                    lambda key=key, senders=senders:
                        self.expire_flood_observation(key, senders),
                )
            if len(self.flood_senders[key]) < 2:
                self.flood_senders[key].add(rx.sender)
        elif packet.kind == "ACK":
            index = packet.path_index
            if (0 <= index < len(packet.path) - 1
                    and packet.path[index + 1] == rx.sender
                    and self.valid_f_ack_packet(packet)):
                continuation_key = (
                    receiver, packet.flow_id, packet.request_id, index + 1,
                )
                if (continuation_key in self.scheduled_repairs
                        or continuation_key in self.scheduled_repeats):
                    self.action_events.append(
                        {"event": "rac_cancel", "time": self.sim.now,
                         "flow_id": packet.flow_id, "src": packet.final_dst,
                         "dst": packet.origin, "receiver": receiver,
                         "continuation_sender": rx.sender}
                    )
                self.scheduled_repairs.pop(continuation_key, None)
                self.scheduled_repeats.pop(continuation_key, None)
            if (self.mode_rac == "corridor"
                    and 0 <= index < len(packet.path) - 1
                    and self.valid_f_ack_packet(packet)
                    and packet.repair_index == 255
                    and packet.path[index + 1] == rx.sender
                    and receiver not in packet.path
                    and self.sim.nodes[receiver].can_relay
                    and packet.ttl > index + 1):
                key = (receiver, packet.final_dst, packet.origin,
                       packet.flow_id, packet.request_id)
                pending_key = (receiver, packet.flow_id,
                               packet.request_id, index)
                if (packet.path[index] in self.flood_senders.get(key, set())
                        and pending_key not in self.attempted_repairs):
                    active = [item for item in self.scheduled_repairs
                              if item[0] == receiver]
                    if len(active) >= 8:
                        del self.scheduled_repairs[active[0]]
                    self.scheduled_repairs[pending_key] = None
                    self.attempted_repairs.add(pending_key)
                    flow = self.sim.metrics.flows[packet.flow_id]
                    self.sim.schedule(
                        flow.created_at + self.app_deadline_s,
                        "protocol_timer",
                        lambda pending_key=pending_key:
                            self.attempted_repairs.discard(pending_key),
                    )
                    self.action_events.append(
                        {"event": "rac_corridor_eligible", "time": self.sim.now,
                         "flow_id": packet.flow_id, "src": packet.final_dst,
                         "dst": packet.origin, "action": "F",
                         "candidate": receiver,
                         "next_hop": packet.path[index], "path": packet.path}
                    )
                    wait_s = self.relay_wait_s + 0.15 * (
                        (receiver + packet.flow_id) % 4
                    )
                    self.sim.schedule(
                        self.sim.now + wait_s, "protocol_timer",
                        lambda receiver=receiver, packet=packet,
                        pending_key=pending_key:
                            self.relay_ack_if_pending(
                                receiver, packet, pending_key,
                            ),
                    )
        super().on_receive(receiver, packet, rx)

    def expire_flood_observation(
        self, key: Tuple[int, int, int, int, int], senders: Set[int],
    ) -> None:
        if self.flood_senders.get(key) is senders:
            del self.flood_senders[key]

    def on_transmit(self, sender: int, packet: Packet, start: float, end: float) -> None:
        super().on_transmit(sender, packet, start, end)
        if (packet.kind == "ACK" and packet.repair_index == 0
                and sender not in packet.path):
            self.action_events.append(
                {"event": "rac_repair_tx", "time": start, "end": end,
                 "flow_id": packet.flow_id, "src": packet.final_dst,
                 "dst": packet.origin, "sender": sender, "path": packet.path}
            )
        if packet.kind == "ACK" and packet.repair_index == 1:
            self.action_events.append(
                {"event": "rac_repeat_tx", "time": start, "end": end,
                 "flow_id": packet.flow_id, "src": packet.final_dst,
                 "dst": packet.origin, "sender": sender, "path": packet.path}
            )
        if (self.mode_rac != "repeat" or packet.kind != "ACK"
                or packet.repair_index != 255
                or not 0 <= packet.path_index + 1 < len(packet.path)
                or packet.path[packet.path_index + 1] != sender):
            return
        pending_key = (sender, packet.flow_id, packet.request_id, packet.path_index)
        if pending_key in self.attempted_repeats:
            return
        active = [item for item in self.scheduled_repeats if item[0] == sender]
        if len(active) >= 8:
            del self.scheduled_repeats[active[0]]
        self.scheduled_repeats[pending_key] = None
        self.attempted_repeats.add(pending_key)
        flow = self.sim.metrics.flows.get(packet.flow_id)
        expiry_at = (flow.created_at + self.app_deadline_s
                     if flow is not None else start + self.app_deadline_s)
        self.sim.schedule(
            expiry_at, "protocol_timer",
            lambda pending_key=pending_key:
                self.attempted_repeats.discard(pending_key),
        )
        self.sim.schedule(
            end + self.relay_wait_s, "protocol_timer",
            lambda sender=sender, packet=packet, pending_key=pending_key:
                self.repeat_ack_if_pending(sender, packet, pending_key),
        )

    def relay_ack_if_pending(
        self, receiver: int, packet: Packet,
        pending_key: Tuple[int, int, int, int],
    ) -> None:
        if pending_key not in self.scheduled_repairs:
            return
        del self.scheduled_repairs[pending_key]
        flow = self.sim.metrics.flows.get(packet.flow_id)
        if (flow is None
                or self.sim.now >= flow.created_at + self.app_deadline_s):
            return
        self.sim.transmit_later(
            receiver,
            replace(packet, repair_index=0).with_ttl(packet.ttl - 1),
            delay_s=0.0,
        )

    def repeat_ack_if_pending(
        self, sender: int, packet: Packet,
        pending_key: Tuple[int, int, int, int],
    ) -> None:
        if pending_key not in self.scheduled_repeats:
            return
        del self.scheduled_repeats[pending_key]
        flow = self.sim.metrics.flows.get(packet.flow_id)
        if (flow is None
                or self.sim.now >= flow.created_at + self.app_deadline_s):
            return
        self.sim.transmit_later(
            sender, replace(packet, repair_index=1), delay_s=0.0,
        )


class MeshEchoCLAR(MeshEchoDPA):
    """Source-closure-assisted ACK repair using only decoded local packets."""

    name = "meshecho-clar"
    relay_wait_s = 0.20
    local_lifetime_s = 30.0

    def __init__(self, *args: Any, mode: str = "repair", **kwargs: Any) -> None:
        if mode not in {"repair", "no-cancel", "repeat", "fr"}:
            raise ValueError(f"unknown CLAR mode: {mode}")
        super().__init__(*args, ack_mode="single", **kwargs)
        self.clar_mode = mode
        self.name = {
            "repair": "meshecho-clar",
            "no-cancel": "meshecho-clar-nocancel",
            "repeat": "meshecho-clar-repeat",
            "fr": "meshecho-clar-fr",
        }[mode]
        self.flood_prefixes: Dict[
            Tuple[int, int, int, int, int],
            Dict[int, Tuple[Tuple[int, ...], float]],
        ] = {}
        self.pending_repairs: Dict[
            Tuple[int, int, int, int, Tuple[int, ...]], float,
        ] = {}
        self.pending_repeats: Dict[
            Tuple[int, int, int, int, Tuple[int, ...]], float,
        ] = {}
        self.attempted_repairs: Set[
            Tuple[int, int, int, int, Tuple[int, ...]]
        ] = set()
        self.attempted_repeats: Set[
            Tuple[int, int, int, int, Tuple[int, ...]]
        ] = set()
        self.closed_flows: Dict[Tuple[int, int, int, int, int], float] = {}
        self.seen_ack_hops: Set[
            Tuple[int, int, int, Tuple[int, ...]]
        ] = set()

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.flood_prefixes = {}
        self.pending_repairs = {}
        self.pending_repeats = {}
        self.attempted_repairs = set()
        self.attempted_repeats = set()
        self.closed_flows = {}
        self.seen_ack_hops = set()

    def flow_key(self, receiver: int, src: int, dst: int,
                 flow_id: int, request_id: int) -> Tuple[int, int, int, int, int]:
        return (receiver, src, dst, flow_id, request_id)

    def observe_flood(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        path = packet.path
        if (not path or path[0] != packet.origin or path[-1] != rx.sender
                or receiver in path or len(set(path)) != len(path)
                or len(path) > self.sim.max_hops
                or packet.request_id != packet.flow_id):
            return
        key = self.flow_key(receiver, packet.origin, packet.final_dst,
                            packet.flow_id, packet.request_id)
        if key not in self.flood_prefixes:
            active = [item for item in self.flood_prefixes if item[0] == receiver]
            if len(active) >= 8:
                oldest = active[0]
                del self.flood_prefixes[oldest]
                self.closed_flows.pop(oldest, None)
            observations: Dict[int, Tuple[Tuple[int, ...], float]] = {}
            self.flood_prefixes[key] = observations
            self.sim.schedule(
                self.sim.now + self.local_lifetime_s, "protocol_timer",
                lambda key=key, observations=observations:
                    self.expire_observation(key, observations),
            )
        observations = self.flood_prefixes[key]
        if rx.sender not in observations and len(observations) < 2:
            observations[rx.sender] = (
                path, self.sim.now + self.local_lifetime_s,
            )

    def expire_observation(
        self, key: Tuple[int, int, int, int, int],
        observations: Dict[int, Tuple[Tuple[int, ...], float]],
    ) -> None:
        if self.flood_prefixes.get(key) is observations:
            del self.flood_prefixes[key]
            self.closed_flows.pop(key, None)

    def valid_local_f_ack(
        self, receiver: int, packet: Packet, rx: RxInfo,
    ) -> bool:
        path = packet.path
        index = packet.path_index
        if (packet.repair_index not in {0, 1, 255}
                or packet.request_id != packet.flow_id
                or len(path) < 2 or path[0] != packet.final_dst
                or path[-1] != packet.origin
                or len(set(path)) != len(path)
                or len(path) - 1 > self.sim.max_hops
                or not 0 <= index < len(path) - 1 or packet.ttl <= 0):
            return False
        if receiver == path[index]:
            if index == 0:
                return self.flow_data_actions.get(packet.flow_id) == "F"
            key = self.flow_key(receiver, path[0], path[-1],
                                packet.flow_id, packet.request_id)
            observations = self.flood_prefixes.get(key, {})
            if not any(
                prefix + (receiver,) == path[:index + 1]
                and self.sim.now < expiry
                for prefix, expiry in observations.values()
            ):
                return False
            return (packet.repair_index == 0
                    or rx.sender == path[index + 1])
        if receiver in path or packet.repair_index != 255:
            return False
        key = self.flow_key(receiver, path[0], path[-1],
                            packet.flow_id, packet.request_id)
        observed = self.flood_prefixes.get(key, {}).get(path[index])
        return bool(
            observed is not None and observed[0] == path[:index + 1]
            and self.sim.now < observed[1]
            and rx.sender == path[index + 1]
            and self.sim.nodes[receiver].can_relay
            and packet.ttl > index + 1
        )

    def on_ack_done(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if (packet.origin != rx.sender or packet.request_id != packet.flow_id
                or packet.ttl != 1 or packet.path or packet.app_payload):
            return
        key = self.flow_key(receiver, packet.origin, packet.final_dst,
                            packet.flow_id, packet.request_id)
        observed = self.flood_prefixes.get(key, {}).get(packet.origin)
        if (observed is None or observed[0] != (packet.origin,)
                or self.sim.now >= observed[1]):
            return
        self.action_events.append(
            {"event": "clar_done_rx", "time": self.sim.now,
             "flow_id": packet.flow_id, "src": packet.origin,
             "dst": packet.final_dst, "receiver": receiver}
        )
        if self.clar_mode == "no-cancel":
            return
        self.closed_flows[key] = observed[1]
        for pending_key in list(self.pending_repairs):
            node, flow_id, request_id, index, path = pending_key
            if (node == receiver and flow_id == packet.flow_id
                    and request_id == packet.request_id and index == 0
                    and path[0] == packet.origin
                    and path[-1] == packet.final_dst):
                del self.pending_repairs[pending_key]
                self.action_events.append(
                    {"event": "clar_cancel", "time": self.sim.now,
                     "flow_id": flow_id, "src": packet.origin,
                     "dst": packet.final_dst, "receiver": receiver,
                     "reason": "source-done"}
                )
        for pending_key in list(self.pending_repeats):
            node, flow_id, request_id, index, path = pending_key
            if (node == receiver and flow_id == packet.flow_id
                    and request_id == packet.request_id and index == 0
                    and path[0] == packet.origin
                    and path[-1] == packet.final_dst):
                del self.pending_repeats[pending_key]
                self.action_events.append(
                    {"event": "clar_cancel", "time": self.sim.now,
                     "flow_id": flow_id, "src": packet.origin,
                     "dst": packet.final_dst, "receiver": receiver,
                     "reason": "source-done-repeat"}
                )

    def cancel_on_ack_continuation(
        self, receiver: int, packet: Packet, rx: RxInfo,
    ) -> None:
        index = packet.path_index
        if (packet.repair_index not in {0, 1, 255}
                or packet.request_id != packet.flow_id
                or not 0 <= index < len(packet.path) - 1
                or packet.path[0] != packet.final_dst
                or packet.path[-1] != packet.origin
                or len(set(packet.path)) != len(packet.path)
                or len(packet.path) - 1 > self.sim.max_hops
                or packet.app_payload
                or packet.ttl <= (1 if index > 0 else 0)
                or rx.sender != packet.path[index + 1]):
            return
        for pending_key in list(self.pending_repairs):
            node, flow_id, request_id, target_index, path = pending_key
            if (node == receiver and flow_id == packet.flow_id
                    and request_id == packet.request_id
                    and target_index == index + 1 and path == packet.path):
                del self.pending_repairs[pending_key]
                self.action_events.append(
                    {"event": "clar_cancel", "time": self.sim.now,
                     "flow_id": flow_id, "src": path[0],
                     "dst": path[-1], "receiver": receiver,
                     "reason": "ack-continuation"}
                )
        for pending_key in list(self.pending_repeats):
            node, flow_id, request_id, target_index, path = pending_key
            if (node == receiver and flow_id == packet.flow_id
                    and request_id == packet.request_id
                    and target_index == index + 1 and path == packet.path):
                del self.pending_repeats[pending_key]
                self.action_events.append(
                    {"event": "clar_cancel", "time": self.sim.now,
                     "flow_id": flow_id, "src": path[0],
                     "dst": path[-1], "receiver": receiver,
                     "reason": "ack-continuation-repeat"}
                )

    def observe_f_ack(
        self, receiver: int, packet: Packet, rx: RxInfo,
    ) -> None:
        index = packet.path_index
        if (self.clar_mode in {"fr", "repeat"} or receiver in packet.path
                or packet.repair_index != 255):
            return
        key = self.flow_key(receiver, packet.path[0], packet.path[-1],
                            packet.flow_id, packet.request_id)
        if index == 0 and key in self.closed_flows:
            return
        observed = self.flood_prefixes.get(key, {}).get(packet.path[index])
        if observed is None:
            return
        pending_key = (receiver, packet.flow_id, packet.request_id,
                       index, packet.path)
        if pending_key in self.attempted_repairs:
            return
        if sum(item[0] == receiver for item in self.attempted_repairs) >= 32:
            return
        active = [item for item in self.pending_repairs if item[0] == receiver]
        if len(active) >= 8:
            del self.pending_repairs[active[0]]
        self.pending_repairs[pending_key] = observed[1]
        self.attempted_repairs.add(pending_key)
        self.sim.schedule(
            observed[1], "protocol_timer",
            lambda pending_key=pending_key:
                self.attempted_repairs.discard(pending_key),
        )
        self.action_events.append(
            {"event": "clar_candidate_eligible", "time": self.sim.now,
             "flow_id": packet.flow_id, "src": packet.final_dst,
             "dst": packet.origin, "action": "F", "candidate": receiver,
             "next_hop": packet.path[index], "path": packet.path}
        )
        wait_s = self.relay_wait_s + 0.15 * ((receiver + packet.flow_id) % 4)
        self.sim.schedule(
            self.sim.now + wait_s, "protocol_timer",
            lambda receiver=receiver, packet=packet, pending_key=pending_key:
                self.relay_ack_if_pending(receiver, packet, pending_key),
        )

    def relay_ack_if_pending(
        self, receiver: int, packet: Packet,
        pending_key: Tuple[int, int, int, int, Tuple[int, ...]],
    ) -> None:
        expiry = self.pending_repairs.pop(pending_key, None)
        if expiry is None or self.sim.now >= expiry:
            return
        key = self.flow_key(receiver, packet.path[0], packet.path[-1],
                            packet.flow_id, packet.request_id)
        if packet.path_index == 0 and key in self.closed_flows:
            return
        self.sim.transmit_later(
            receiver, replace(packet, repair_index=0).with_ttl(packet.ttl - 1),
            delay_s=0.0,
            pending=PendingSend(can_start_at=lambda start: start < expiry),
        )

    def repeat_ack_if_pending(
        self, sender: int, packet: Packet,
        pending_key: Tuple[int, int, int, int, Tuple[int, ...]],
    ) -> None:
        expiry = self.pending_repeats.pop(pending_key, None)
        if expiry is None or self.sim.now >= expiry:
            return
        key = self.flow_key(sender, packet.path[0], packet.path[-1],
                            packet.flow_id, packet.request_id)
        if packet.path_index == 0 and key in self.closed_flows:
            return
        self.sim.transmit_later(
            sender, replace(packet, repair_index=1), delay_s=0.0,
            pending=PendingSend(can_start_at=lambda start: start < expiry),
        )

    def on_receive(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if packet.kind == "ACK_DONE":
            self.on_ack_done(receiver, packet, rx)
            return
        if packet.kind == "FLOOD":
            self.observe_flood(receiver, packet, rx)
        elif packet.kind == "ACK" and packet.repair_index is not None:
            self.cancel_on_ack_continuation(receiver, packet, rx)
            if not self.valid_local_f_ack(receiver, packet, rx):
                return
            self.observe_f_ack(receiver, packet, rx)
        super().on_receive(receiver, packet, rx)

    def on_ack_packet(self, receiver: int, packet: Packet) -> None:
        source_flow = (
            self.sim.metrics.flows.get(packet.flow_id)
            if packet.repair_index is not None and receiver == packet.final_dst
            else None
        )
        prior_ack = source_flow.acked_at if source_flow is not None else None
        if (packet.repair_index is not None
                and receiver != packet.final_dst):
            if packet.ttl <= 1:
                return
            key = (receiver, packet.flow_id, packet.request_id, packet.path)
            if key in self.seen_ack_hops:
                return
            if sum(item[0] == receiver for item in self.seen_ack_hops) >= 32:
                self.action_events.append(
                    {"event": "clar_state_drop", "time": self.sim.now,
                     "flow_id": packet.flow_id, "src": packet.final_dst,
                     "dst": packet.origin, "action": "F",
                     "receiver": receiver, "state": "seen-ack-hops"}
                )
                return
            self.seen_ack_hops.add(key)
            self.sim.schedule(
                self.sim.now + self.local_lifetime_s, "protocol_timer",
                lambda key=key: self.seen_ack_hops.discard(key),
            )
        super().on_ack_packet(receiver, packet)
        if source_flow is not None:
            self.action_events.append(
                {"event": "clar_source_ack_rx", "time": self.sim.now,
                 "flow_id": packet.flow_id, "src": receiver,
                 "dst": source_flow.dst, "action": "F", "path": packet.path,
                 "repair_index": packet.repair_index,
                 "on_path": self.ack_next_hop_matches(receiver, packet),
                 "accepted": prior_ack is None
                 and source_flow.acked_at is not None}
            )

    def send_ack_on_reverse_path(self, receiver: int, packet: Packet) -> None:
        if packet.kind != "FLOOD":
            super().send_ack_on_reverse_path(receiver, packet)
            return
        if packet.path_index <= 0 or receiver != packet.final_dst:
            return
        ack = Packet(
            kind="ACK", flow_id=packet.flow_id, origin=receiver,
            final_dst=packet.origin, ttl=self.sim.max_hops,
            created_at=self.sim.now, protocol=self.name,
            request_id=packet.request_id, path=packet.path,
            path_index=packet.path_index - 1, app_payload=False,
            repair_index=255,
        )
        self.sim.transmit_later(receiver, ack, delay_s=0.0)

    def on_ack(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        super().on_ack(flow_id, receiver, now, packet)
        if (self.clar_mode == "fr"
                or self.flow_data_actions.get(flow_id) != "F"):
            return
        done = Packet(
            kind="ACK_DONE", flow_id=flow_id, origin=receiver,
            final_dst=packet.origin, ttl=1, created_at=now,
            protocol=self.name, request_id=flow_id, app_payload=False,
        )
        self.sim.transmit_later(receiver, done, delay_s=0.0)

    def on_transmit(self, sender: int, packet: Packet, start: float, end: float) -> None:
        super().on_transmit(sender, packet, start, end)
        if packet.kind == "ACK_DONE":
            self.action_events.append(
                {"event": "clar_done_tx", "time": start, "end": end,
                 "flow_id": packet.flow_id, "src": sender,
                 "dst": packet.final_dst, "action": "F"}
            )
        if (packet.kind == "ACK" and packet.repair_index == 0
                and sender not in packet.path):
            self.action_events.append(
                {"event": "clar_repair_tx", "time": start, "end": end,
                 "flow_id": packet.flow_id, "src": packet.final_dst,
                 "dst": packet.origin, "action": "F", "sender": sender,
                 "path": packet.path}
            )
        if packet.kind == "ACK" and packet.repair_index == 1:
            self.action_events.append(
                {"event": "clar_repeat_tx", "time": start, "end": end,
                 "flow_id": packet.flow_id, "src": packet.final_dst,
                 "dst": packet.origin, "action": "F", "sender": sender,
                 "path": packet.path}
            )
        if (self.clar_mode != "repeat" or packet.kind != "ACK"
                or packet.repair_index != 255
                or not 0 <= packet.path_index + 1 < len(packet.path)
                or packet.path[packet.path_index + 1] != sender):
            return
        pending_key = (sender, packet.flow_id, packet.request_id,
                       packet.path_index, packet.path)
        if pending_key in self.attempted_repeats:
            return
        if sum(item[0] == sender for item in self.attempted_repeats) >= 32:
            return
        active = [item for item in self.pending_repeats if item[0] == sender]
        if len(active) >= 8:
            del self.pending_repeats[active[0]]
        self.pending_repeats[pending_key] = end + self.local_lifetime_s
        self.attempted_repeats.add(pending_key)
        self.sim.schedule(
            end + self.local_lifetime_s, "protocol_timer",
            lambda pending_key=pending_key:
                self.attempted_repeats.discard(pending_key),
        )
        self.sim.schedule(
            end + self.relay_wait_s, "protocol_timer",
            lambda sender=sender, packet=packet, pending_key=pending_key:
                self.repeat_ack_if_pending(sender, packet, pending_key),
        )


class MeshEchoBudgeted(MeshEcho):
    """Prefer a short route unless a near-shortest candidate is clearly better."""

    name = "meshecho-budgeted"

    def select_route_candidate(
        self,
        candidates: Sequence[Tuple[Tuple[int, ...], float]],
        flow_id: int,
    ) -> Tuple[Tuple[int, ...], float]:
        del flow_id
        shortest = min(candidates, key=lambda item: (len(item[0]), item[0]))
        eligible = (item for item in candidates if len(item[0]) <= len(shortest[0]) + 1)
        best = min(eligible, key=lambda item: (-item[1], len(item[0]), item[0]))
        gain = best[1] - shortest[1]
        return best if gain > 0.10 or math.isclose(gain, 0.10, rel_tol=0.0, abs_tol=1e-12) else shortest


class MeshEchoNoConfidence(MeshEcho):
    """MeshEcho with confidence ranking removed.

    The discovery budget and forwarding/recovery machinery stay unchanged;
    candidates are selected by shortest path, making this a route-admission
    ablation rather than a different protocol family.
    """

    name = "meshecho-no-confidence"

    def select_route_candidate(
        self,
        candidates: Sequence[Tuple[Tuple[int, ...], float]],
        flow_id: int,
    ) -> Tuple[Tuple[int, ...], float]:
        del flow_id
        return min(candidates, key=lambda item: (len(item[0]), -item[1], item[0]))


class MeshEchoNoFallback(MeshEcho):
    """MeshEcho with route-miss recovery disabled."""

    name = "meshecho-no-fallback"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["route_miss_recovery_enabled"] = False
        super().__init__(*args, **kwargs)


class MeshEchoNoHopPenalty(MeshEcho):
    """MeshEcho without the explicit per-hop confidence penalty."""

    name = "meshecho-no-hop-penalty"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["hop_penalty_per_hop"] = 0.0
        super().__init__(*args, **kwargs)


class MeshEchoNoAgePenalty(MeshEcho):
    """MeshEcho without route-cache age decay."""

    name = "meshecho-no-age-penalty"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs["route_age_penalty"] = 0.0
        super().__init__(*args, **kwargs)


class MetricMesh(CalmMesh):
    """Matched-discovery source routing with a standard path metric.

    The metric baselines deliberately share MeshEcho's packet/routing machinery
    but disable route-miss fallback and profile learning.  They differ only
    in how a received RREQ candidate is scored:

    * ``etx`` minimizes the sum of expected transmissions, ``1 / PRR``.
    * ``ett`` minimizes airtime-weighted expected transmissions,
      ``ToA / PRR``.
    * ``prr-product`` maximizes the product of modeled per-hop PRRs.

    ETX and ETT scores use ``1 / (1 + cost)``; PRR-product is already a
    bounded higher-is-better value. All use the same RREQ SINR observation.
    """

    def __init__(
        self,
        metric_kind: str,
        route_ttl_s: float = DEFAULT_MATCHED_MESHCORE_ROUTE_TTL_S,
        discovery_window_s: float = DEFAULT_CALM_DISCOVERY_WINDOW_S,
        flood_base_delay_s: float = 0.5,
        flood_jitter_s: float = 0.7,
        route_miss_recovery_enabled: bool = False,
        rrep_wait_s: float = 10.0,
    ) -> None:
        if metric_kind not in {"etx", "ett", "prr-product"}:
            raise ValueError(f"unknown metric kind: {metric_kind}")
        super().__init__(
            route_ttl_s=route_ttl_s,
            discovery_window_s=discovery_window_s,
            flood_base_delay_s=flood_base_delay_s,
            flood_jitter_s=flood_jitter_s,
            fallback_confidence_threshold=0.0,
            route_miss_recovery_enabled=route_miss_recovery_enabled,
            rrep_wait_s=rrep_wait_s,
        )
        self.metric_kind = metric_kind
        self.name = f"{metric_kind}-mesh"

    def flood_delay(
        self,
        receiver: Optional[int] = None,
        rx: Optional[RxInfo] = None,
    ) -> float:
        """Use the source-route flood timing, without confidence bias."""

        del receiver, rx
        return self.flood_base_delay_s + self.sim.random.random() * self.flood_jitter_s

    def cost_from_link(self, prr: float, toa_s: float) -> float:
        """Return the per-hop ETX or ETT cost for a measured PRR."""

        bounded_prr = clamp(prr, 0.05, 1.0)
        if self.metric_kind == "etx":
            return 1.0 / bounded_prr
        return toa_s / bounded_prr

    @staticmethod
    def score_from_cost(cost: float) -> float:
        """Convert a non-negative path cost to a bounded higher-is-better score."""

        return 1.0 / (1.0 + max(0.0, cost))

    def extend_metric(self, previous_score: float, rx: RxInfo) -> float:
        """Append one received hop to an accumulated path score."""

        hop_prr = self.sim.prr_from_snr(rx.sinr_db)
        if self.metric_kind == "prr-product":
            return previous_score * hop_prr
        previous_cost = (
            1.0 / max(previous_score, 1e-9) - 1.0
            if previous_score > 0.0
            else 0.0
        )
        total_cost = previous_cost + self.cost_from_link(
            hop_prr,
            self.sim.radio.toa_s,
        )
        return self.score_from_cost(total_cost)

    def select_route_candidate(
        self,
        candidates: Sequence[Tuple[Tuple[int, ...], float]],
        flow_id: int,
    ) -> Tuple[Tuple[int, ...], float]:
        del flow_id
        return max(candidates, key=lambda item: (item[1], -len(item[0]), item[0]))

    def on_rreq(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        if receiver in packet.path:
            return
        key = packet.flood_key
        new_path = packet.path + (receiver,)
        previous_score = packet.path_confidence or 1.0
        score = self.extend_metric(previous_score, rx)

        if receiver == packet.final_dst:
            self.collect_rreq_candidate(packet, new_path, score)
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
            path_confidence=score,
            app_payload=False,
        )
        delay = (
            self.sim.rreq_forward_delay(packet, receiver)
            if self.sim.matched_rreq_timing
            else self.flood_delay()
        )
        self.sim.transmit_later(receiver, forwarded, delay_s=delay)


class PRRProductFallback(MetricMesh):
    """PRR-product with MeshEcho's route-miss recovery budget and timing."""

    name = "prr-product-fallback-mesh"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(
            metric_kind="prr-product",
            flood_base_delay_s=0.45,
            flood_jitter_s=0.65,
            route_miss_recovery_enabled=True,
            **kwargs,
        )
        self.name = "prr-product-fallback-mesh"

    def flood_delay(
        self,
        receiver: Optional[int] = None,
        rx: Optional[RxInfo] = None,
    ) -> float:
        return CalmMesh.flood_delay(self, receiver, rx)


class AckRouteEviction:
    """Discard only a still-cached route used by an unacknowledged DATA flow."""

    def __init__(self, *args: Any, ack_guard_s: float = 15.0, **kwargs: Any) -> None:
        if ack_guard_s <= 0.0:
            raise ValueError("ACK guard must be positive")
        super().__init__(*args, **kwargs)
        self.ack_guard_s = ack_guard_s
        self.pending_ack_routes: Dict[
            int, Tuple[int, int, RouteEntry, Optional[float]]
        ] = {}

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.pending_ack_routes = {}

    def send_data_on_path(
        self, src: int, dst: int, flow_id: int, entry: RouteEntry
    ) -> None:
        self.pending_ack_routes[flow_id] = (src, dst, entry, None)
        super().send_data_on_path(src, dst, flow_id, entry)

    def on_transmit(self, sender: int, packet: Packet, start: float, end: float) -> None:
        super().on_transmit(sender, packet, start, end)
        route = self.pending_ack_routes.get(packet.flow_id)
        if (
            packet.kind != "DATA"
            or packet.origin != sender
            or route is None
            or route[0] != sender
            or route[1] != packet.final_dst
            or route[2].path != packet.path
        ):
            return
        src, dst, entry, _ = route
        self.pending_ack_routes[packet.flow_id] = (src, dst, entry, start)
        self.sim.schedule(
            start + self.ack_guard_s,
            "protocol_timer",
            lambda: self.expire_unacknowledged_route(packet.flow_id, src, dst, entry),
        )

    def expire_unacknowledged_route(
        self, flow_id: int, src: int, dst: int, entry: RouteEntry
    ) -> None:
        route = self.pending_ack_routes.get(flow_id)
        if route is None or route[2] is not entry:
            return
        del self.pending_ack_routes[flow_id]
        flow = self.sim.metrics.flows.get(flow_id)
        if flow is None or flow.acked_at is not None:
            return
        if self.route_cache[src].get(dst) is entry:
            del self.route_cache[src][dst]
            self.sim.metrics.ack_timeout_invalidations += 1
            if flow.delivered_at is not None:
                self.sim.metrics.timeout_invalidations_after_destination_delivery += 1

    def on_ack(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        confirmed = self.pending_ack_routes.pop(flow_id, None)
        if confirmed is not None and confirmed[3] is not None:
            src, dst, entry, confirmed_start = confirmed
            for pending_flow_id, pending in list(self.pending_ack_routes.items()):
                pending_src, pending_dst, pending_entry, pending_start = pending
                if (
                    pending_src == src
                    and pending_dst == dst
                    and pending_entry is entry
                    and pending_start is not None
                    and pending_start <= confirmed_start
                ):
                    del self.pending_ack_routes[pending_flow_id]
        super().on_ack(flow_id, receiver, now, packet)


class MeshEchoAckEvict(AckRouteEviction, MeshEcho):
    """Optional ACK-feedback stale-cache experiment; never retries the flow."""

    name = "meshecho-ack-evict"


class PRRProductAckEvict(AckRouteEviction, MetricMesh):
    """Give the PRR-product comparator the same ACK-feedback budget."""

    name = "prr-product-ack-evict-mesh"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(metric_kind="prr-product", **kwargs)
        self.name = "prr-product-ack-evict-mesh"


class MinHopMesh(CalmMesh):
    """Matched-discovery shortest-path baseline.

    This baseline shares MeshEcho's candidate-collection window and packet
    model, but selects the fewest-hop candidate and disables route-miss
    fallback.  It is intentionally distinct from ETX/ETT: it ignores link
    quality after candidate exposure and represents a common hop-count
    routing policy.
    """

    name = "minhop-mesh"

    def __init__(
        self,
        route_ttl_s: float = DEFAULT_MATCHED_MESHCORE_ROUTE_TTL_S,
        discovery_window_s: float = DEFAULT_CALM_DISCOVERY_WINDOW_S,
        flood_base_delay_s: float = 0.5,
        flood_jitter_s: float = 0.7,
        rrep_wait_s: float = 10.0,
    ) -> None:
        super().__init__(
            route_ttl_s=route_ttl_s,
            discovery_window_s=discovery_window_s,
            flood_base_delay_s=flood_base_delay_s,
            flood_jitter_s=flood_jitter_s,
            fallback_confidence_threshold=0.0,
            route_miss_recovery_enabled=False,
            rrep_wait_s=rrep_wait_s,
        )

    def select_route_candidate(
        self,
        candidates: Sequence[Tuple[Tuple[int, ...], float]],
        flow_id: int,
    ) -> Tuple[Tuple[int, ...], float]:
        del flow_id
        return min(candidates, key=lambda item: (len(item[0]), -item[1], item[0]))


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
        protocol_name: str = "smart-calm",
        update_interval_s: float = 30.0,
        learning_rate: float = 0.45,
        discount: float = 0.75,
        exploration: float = 0.02,
        flow_timeout_s: float = 15.0,
        max_timeout_retries: int = 2,
        retry_after_fallback: bool = False,
        route_miss_fallback_ttl: int = 0,
        timeout_fallback_min_ttl: int = 1,
        prior_q_values: Optional[Dict[Tuple[int, int], float]] = None,
        profiles: Sequence[AdaptiveProfile] = DEFAULT_PROFILES,
        learning_enabled: bool = True,
        fallback_enabled: bool = True,
        confidence_enabled: bool = True,
        fixed_profile_index: Optional[int] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.name = protocol_name
        self.update_interval_s = update_interval_s
        self.learning_rate = learning_rate
        self.discount = discount
        self.exploration = exploration
        self.flow_timeout_s = flow_timeout_s
        self.max_timeout_retries = max_timeout_retries
        self.retry_after_fallback = retry_after_fallback
        self.route_miss_fallback_ttl = route_miss_fallback_ttl
        self.timeout_fallback_min_ttl = max(1, timeout_fallback_min_ttl)
        self.profiles = tuple(profiles)
        self.learning_enabled = learning_enabled
        self.fallback_enabled = fallback_enabled
        self.confidence_enabled = confidence_enabled
        self.fixed_profile_index = fixed_profile_index
        if self.fixed_profile_index is not None:
            self.fixed_profile_index = max(
                0,
                min(self.fixed_profile_index, len(self.profiles) - 1),
            )
        self.active_profile_index = 1 if len(self.profiles) > 1 else 0
        self.active_state_index = 0
        self.q_values: Dict[Tuple[int, int], float] = {}
        self.last_snapshot: Optional[LearningSnapshot] = None
        self.flow_decisions: Dict[int, FlowDecision] = {}
        self.prior_q_values: Dict[Tuple[int, int], float] = dict(prior_q_values or {})
        self.apply_profile(self.active_profile_index)

    def bind(self, sim: Simulator) -> None:
        super().bind(sim)
        self.active_profile_index = min(self.active_profile_index, len(self.profiles) - 1)
        self.apply_profile(self.active_profile_index)
        self.active_state_index = 0
        self.q_values = dict(self.prior_q_values)
        self.last_snapshot = sim.metrics.snapshot()
        self.flow_decisions = {}
        sim.metrics.active_profile_index = self.active_profile_index
        if self.learning_enabled:
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
        delivered = snapshot.unicast_acks
        pdr = delivered / attempts
        route_attempts = snapshot.route_cache_hits + snapshot.route_cache_misses
        miss_ratio = snapshot.route_cache_misses / max(1, route_attempts)
        receive_attempts = snapshot.rx_success + snapshot.rx_fail
        collision_rate = snapshot.collision_fail / max(1, receive_attempts)

        if pdr < 0.65 or miss_ratio > 0.45:
            reliability_bucket = 0
        elif pdr < 0.85 or miss_ratio > 0.25:
            reliability_bucket = 1
        else:
            reliability_bucket = 2

        congestion_bucket = 1 if collision_rate > 0.18 else 0
        return reliability_bucket * 2 + congestion_bucket

    def learning_tick(self) -> None:
        if not self.learning_enabled:
            return
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
        new_unicast_acks = current.unicast_acks - previous.unicast_acks
        new_broadcast_deliveries = current.broadcast_deliveries - previous.broadcast_deliveries
        new_tx = current.tx_count - previous.tx_count
        new_control = current.control_tx - previous.control_tx
        new_collisions = current.collision_fail - previous.collision_fail
        new_repairs = current.route_repair_count - previous.route_repair_count
        new_fallback = current.fallback_forward_count - previous.fallback_forward_count
        new_delay_total = current.delivery_delay_total_s - previous.delivery_delay_total_s
        new_delay_samples = current.delivery_delay_samples - previous.delivery_delay_samples
        new_rx_success = current.rx_success - previous.rx_success
        new_rx_fail = current.rx_fail - previous.rx_fail

        unicast_pdr = new_unicast_acks / max(1, new_unicast)
        broadcast_gain = new_broadcast_deliveries / max(1, new_broadcast * max(1, self.sim.metrics.node_count - 1))
        avg_delay = new_delay_total / max(1, new_delay_samples)
        control_ratio = new_control / max(1, new_tx)
        collision_pressure = new_collisions / max(1, new_rx_success + new_rx_fail)

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

    def choose_profile_for_flow(self, state_index: int) -> int:
        if self.fixed_profile_index is not None:
            return self.fixed_profile_index
        if not self.learning_enabled:
            return self.active_profile_index
        return self.select_action(state_index)

    def _profile_for_flow(self, flow_id: int) -> Optional[AdaptiveProfile]:
        decision = self.flow_decisions.get(flow_id)
        return decision.profile if decision is not None else None

    def route_ttl_for(self, flow_id: int) -> float:
        profile = self._profile_for_flow(flow_id)
        return profile.route_ttl_s if profile is not None else super().route_ttl_for(flow_id)

    def discovery_window_for(self, flow_id: int) -> float:
        profile = self._profile_for_flow(flow_id)
        return (
            profile.discovery_window_s
            if profile is not None
            else super().discovery_window_for(flow_id)
        )

    def fallback_confidence_threshold_for(self, flow_id: int) -> float:
        if not self.fallback_enabled or not self.confidence_enabled:
            # A negative threshold keeps the confidence-triggered fallback
            # branch disabled without changing route-miss/timeout guards. The
            # no-confidence ablation also disables this branch so it tests
            # shortest-candidate admission without a hidden confidence path.
            return -float("inf")
        profile = self._profile_for_flow(flow_id)
        return (
            profile.fallback_confidence_threshold
            if profile is not None
            else super().fallback_confidence_threshold_for(flow_id)
        )

    def fallback_ttl_for(self, flow_id: int) -> int:
        profile = self._profile_for_flow(flow_id)
        return profile.fallback_ttl if profile is not None else super().fallback_ttl_for(flow_id)

    def fallback_delay_margin_for(self, flow_id: int) -> float:
        profile = self._profile_for_flow(flow_id)
        return (
            profile.fallback_delay_margin_s
            if profile is not None
            else super().fallback_delay_margin_for(flow_id)
        )

    def route_age_penalty_for(self, flow_id: int) -> float:
        profile = self._profile_for_flow(flow_id)
        return (
            profile.route_age_penalty
            if profile is not None
            else super().route_age_penalty_for(flow_id)
        )

    def select_route_candidate(
        self,
        candidates: Sequence[Tuple[Tuple[int, ...], float]],
        flow_id: int,
    ) -> Tuple[Tuple[int, ...], float]:
        if not self.confidence_enabled:
            return min(candidates, key=lambda item: (len(item[0]), item[0]))
        return super().select_route_candidate(candidates, flow_id)

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
            action_index = self.choose_profile_for_flow(state_index)
            if action_index != self.active_profile_index:
                self.sim.metrics.policy_switch_count += 1
            self.active_state_index = state_index
            self.active_profile_index = action_index
            self.apply_profile(action_index)
            self.sim.metrics.active_profile_index = self.active_profile_index
            self.sim.metrics.record_profile_selection(action_index)
            self.flow_decisions[flow_id] = FlowDecision(
                src=src,
                dst=dst,
                state_index=state_index,
                action_index=action_index,
                profile_name=self.profiles[action_index].name,
                created_at=self.sim.now,
                profile=self.profiles[action_index],
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
            _, _, flow_id = key
            _, confidence = self.select_route_candidate(candidates, flow_id)
            decision = self.flow_decisions.get(flow_id)
            if decision is not None:
                decision.confidence = confidence
        super().finish_route_discovery(key)

    def route_miss_recovery_ttl(self, flow_id: Optional[int] = None) -> int:
        if not self.fallback_enabled:
            return 0
        if self.route_miss_fallback_ttl > 0:
            return self.route_miss_fallback_ttl
        return self.sim.max_hops

    def send_data_on_path(self, src: int, dst: int, flow_id: int, entry: RouteEntry) -> None:
        decision = self.flow_decisions.get(flow_id)
        if decision is not None:
            decision.confidence = max(
                decision.confidence,
                self.route_confidence(entry, self.route_age_penalty_for(flow_id)),
            )
        super().send_data_on_path(src, dst, flow_id, entry)

    def retry_data_on_cached_path(self, decision: FlowDecision, flow_id: int) -> bool:
        entry = self.get_route(decision.src, decision.dst)
        if entry is None or len(entry.path) < 2:
            return False
        confidence = self.route_confidence(
            entry,
            self.route_age_penalty_for(flow_id),
        )
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

    def on_ack(self, flow_id: int, receiver: int, now: float, packet: Packet) -> None:
        super().on_ack(flow_id, receiver, now, packet)
        decision = self.flow_decisions.get(flow_id)
        if decision is None or decision.delivered:
            return
        decision.delivered = True
        decision.delivered_at = now
        self.learn_from_flow(decision, delivered=True, now=now)
        self.flow_decisions.pop(flow_id, None)

    def flow_confirmed(self, flow: FlowRecord) -> bool:
        return flow.acked_at is not None

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
                if self.fallback_enabled:
                    retry_ttl = max(
                        self.fallback_ttl_for(flow_id),
                        self.timeout_fallback_min_ttl,
                    )
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
        if not self.learning_enabled:
            return
        latency = max(0.0, (decision.delivered_at or now) - decision.created_at)
        reward = (
            (1.0 if delivered else -0.8)
            - 0.02 * latency
            - 0.08 * decision.route_miss
            - 0.035 * decision.fallback_count
            + (0.08 * decision.confidence if self.confidence_enabled else 0.0)
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


def independent_rng_streams_enabled(args: argparse.Namespace) -> bool:
    """Read both spellings used by older callers and the CLI parser."""

    return bool(
        getattr(
            args,
            "independent_rng_streams",
            getattr(args, "independent_random_streams", False),
        )
    )


def build_protocol(name: str, args: Optional[argparse.Namespace] = None) -> RoutingProtocol:
    if name in {"meshecho-dcb", "meshecho-dcb-no-forward",
                "meshecho-dcb-unconditional", "meshecho-dcb-current-overhear",
                "meshecho-dcb-source-fr", "meshecho-dcb-source-trigger-f",
                "meshecho-dcb-promote",
                "meshecho-dcb-trial", "meshecho-dcb-trial-no-switch",
                "meshecho-dcb-trial-blind"}:
        dcb_class = (
            MeshEchoDCBPromote if name == "meshecho-dcb-promote" else
            MeshEchoDCBTrial if name in {
                "meshecho-dcb-trial", "meshecho-dcb-trial-no-switch",
                "meshecho-dcb-trial-blind"
            } else MeshEchoDCB
        )
        return dcb_class(
            relay_mode={
                "meshecho-dcb": "conditional",
                "meshecho-dcb-no-forward": "no-forward",
                "meshecho-dcb-unconditional": "unconditional",
                "meshecho-dcb-current-overhear": "current-overhear",
                "meshecho-dcb-source-fr": "conditional",
                "meshecho-dcb-source-trigger-f": "conditional",
                "meshecho-dcb-promote": "conditional",
                "meshecho-dcb-trial": "conditional",
                "meshecho-dcb-trial-no-switch": "conditional",
                "meshecho-dcb-trial-blind": "conditional",
            }[name],
            source_mode={
                "meshecho-dcb-source-fr": "fr",
                "meshecho-dcb-source-trigger-f": "trigger-f",
            }.get(name, "sr"),
            **({"trial_enabled": name != "meshecho-dcb-trial-no-switch",
                "blind_switch": name == "meshecho-dcb-trial-blind"}
               if dcb_class is MeshEchoDCBTrial else {}),
            route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
            discovery_window_s=getattr(args, "calm_discovery_window_s", 2.0),
            app_deadline_s=getattr(args, "sr_app_deadline_s", 30.0),
            ack_guard_s=getattr(args, "sr_ack_guard_s", 15.0),
            rrep_wait_s=getattr(args, "sr_rrep_wait_s", 10.0),
        )
    if name in {"meshecho-dbr", "meshecho-dbr-fixed-f",
                "meshecho-dbr-fixed-f-plain", "meshecho-dbr-same",
                "meshecho-dbr-first-alt"}:
        return MeshEchoDBR(
            recovery_mode={
                "meshecho-dbr": "selective",
                "meshecho-dbr-fixed-f": "fixed-f",
                "meshecho-dbr-fixed-f-plain": "fixed-f-plain",
                "meshecho-dbr-same": "same",
                "meshecho-dbr-first-alt": "first-alt",
            }[name],
            route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
            discovery_window_s=getattr(args, "calm_discovery_window_s", 2.0),
            app_deadline_s=getattr(args, "sr_app_deadline_s", 30.0),
            ack_guard_s=getattr(args, "sr_ack_guard_s", 15.0),
            rrep_wait_s=getattr(args, "sr_rrep_wait_s", 10.0),
        )
    if name in {f"meshecho-dhr-flood-ack-delay-guard{guard}"
                for guard in (1, 2, 4, 8)}:
        return MeshEchoDHRDelayedAckShortGuard(
            r_guard_s=int(name.rsplit("guard", 1)[1]),
            route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
            discovery_window_s=getattr(args, "calm_discovery_window_s", 2.0),
            app_deadline_s=getattr(args, "sr_app_deadline_s", 30.0),
            ack_guard_s=15.0,
            rrep_wait_s=getattr(args, "sr_rrep_wait_s", 10.0),
        )
    if name in {"meshecho-afs", "meshecho-afs-nocancel"}:
        return MeshEchoAFS(
            cancel_on_ack=name == "meshecho-afs",
            route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
            discovery_window_s=getattr(args, "calm_discovery_window_s", 2.0),
            app_deadline_s=getattr(args, "sr_app_deadline_s", 30.0),
            ack_guard_s=getattr(args, "sr_ack_guard_s", 15.0),
            rrep_wait_s=getattr(args, "sr_rrep_wait_s", 10.0),
        )
    if name in {"meshecho-bar-alternate", "meshecho-bar-same"}:
        return MeshEchoBAR(
            ack_mode="alternate" if name == "meshecho-bar-alternate" else "same",
            route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
            discovery_window_s=getattr(args, "calm_discovery_window_s", 2.0),
            app_deadline_s=getattr(args, "sr_app_deadline_s", 30.0),
            ack_guard_s=getattr(args, "sr_ack_guard_s", 15.0),
            rrep_wait_s=getattr(args, "sr_rrep_wait_s", 10.0),
        )
    if name in {"meshecho-dhr", "meshecho-dhr-none",
                "meshecho-dhr-repeat", "meshecho-dhr-flood",
                "meshecho-dhr-flood-ack-delay",
                "meshecho-dhr-flood-ack-delay-flood2",
                "meshecho-dhr-flood-ack-delay-repeat"}:
        dhr_type = (
            MeshEchoDHRDelayedAckRepeat
            if name == "meshecho-dhr-flood-ack-delay-repeat" else
            MeshEchoDHRDelayedAckFlood2
            if name == "meshecho-dhr-flood-ack-delay-flood2" else
            MeshEchoDHRDelayedAck
            if name == "meshecho-dhr-flood-ack-delay" else MeshEchoDHR
        )
        dhr_kwargs = (
            {} if name in {"meshecho-dhr-flood-ack-delay",
                           "meshecho-dhr-flood-ack-delay-flood2",
                           "meshecho-dhr-flood-ack-delay-repeat"} else
            {"rescue_mode": {
                "meshecho-dhr": "adaptive",
                "meshecho-dhr-none": "none",
                "meshecho-dhr-repeat": "repeat",
                "meshecho-dhr-flood": "flood",
            }[name]}
        )
        return dhr_type(
            **dhr_kwargs,
            route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
            discovery_window_s=getattr(args, "calm_discovery_window_s", 2.0),
            app_deadline_s=getattr(args, "sr_app_deadline_s", 30.0),
            ack_guard_s=getattr(args, "sr_ack_guard_s", 15.0),
            rrep_wait_s=getattr(args, "sr_rrep_wait_s", 10.0),
        )
    if name in {"meshecho-clar", "meshecho-clar-nocancel",
                "meshecho-clar-repeat", "meshecho-clar-fr"}:
        return MeshEchoCLAR(
            mode={
                "meshecho-clar": "repair",
                "meshecho-clar-nocancel": "no-cancel",
                "meshecho-clar-repeat": "repeat",
                "meshecho-clar-fr": "fr",
            }[name],
            route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
            discovery_window_s=getattr(args, "calm_discovery_window_s", 2.0),
            app_deadline_s=getattr(args, "sr_app_deadline_s", 30.0),
            ack_guard_s=getattr(args, "sr_ack_guard_s", 15.0),
            rrep_wait_s=getattr(args, "sr_rrep_wait_s", 10.0),
        )
    if name in {"meshecho-rac", "meshecho-rac-repeat", "meshecho-rac-fr"}:
        return MeshEchoRAC(
            mode={
                "meshecho-rac": "corridor",
                "meshecho-rac-repeat": "repeat",
                "meshecho-rac-fr": "fr",
            }[name],
            route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
            discovery_window_s=getattr(args, "calm_discovery_window_s", 2.0),
            app_deadline_s=getattr(args, "sr_app_deadline_s", 30.0),
            ack_guard_s=getattr(args, "sr_ack_guard_s", 15.0),
            rrep_wait_s=getattr(args, "sr_rrep_wait_s", 10.0),
        )
    if name in {"meshecho-dpa", "meshecho-dpa-repeat", "meshecho-dpa-fr"}:
        return MeshEchoDPA(
            ack_mode={
                "meshecho-dpa": "diverse",
                "meshecho-dpa-repeat": "repeat",
                "meshecho-dpa-fr": "single",
            }[name],
            route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
            discovery_window_s=getattr(args, "calm_discovery_window_s", 2.0),
            app_deadline_s=getattr(args, "sr_app_deadline_s", 30.0),
            ack_guard_s=getattr(args, "sr_ack_guard_s", 15.0),
            rrep_wait_s=getattr(args, "sr_rrep_wait_s", 10.0),
        )
    if name in LPR_PROTOCOL_MODES:
        return MeshEchoLPR(
            mode=LPR_PROTOCOL_MODES[name],
            route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
            discovery_window_s=getattr(args, "calm_discovery_window_s", 2.0),
            app_deadline_s=getattr(args, "sr_app_deadline_s", 30.0),
            ack_guard_s=getattr(args, "sr_ack_guard_s", 15.0),
            rrep_wait_s=getattr(args, "sr_rrep_wait_s", 10.0),
        )
    if name in CPR_PROTOCOL_MODES:
        return MeshEchoCPR(
            cancel_on_ack=name == "meshecho-cpr",
            route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
            flood_base_delay_s=getattr(
                args, "calm_flood_base_delay_s", 0.45,
            ),
            flood_jitter_s=getattr(args, "calm_flood_jitter_s", 0.65),
            app_deadline_s=getattr(args, "sr_app_deadline_s", 30.0),
            safety_margin_s=getattr(args, "drc_safety_margin_s", 0.25),
            fixed_guard_s=getattr(args, "drc_fixed_guard_s", 15.0),
        )
    if name in DRC_PROTOCOL_MODES:
        return MeshEchoDRC(
            mode=DRC_PROTOCOL_MODES[name],
            route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
            flood_base_delay_s=getattr(
                args, "calm_flood_base_delay_s", 0.45,
            ),
            flood_jitter_s=getattr(args, "calm_flood_jitter_s", 0.65),
            app_deadline_s=getattr(args, "sr_app_deadline_s", 30.0),
            safety_margin_s=getattr(args, "drc_safety_margin_s", 0.25),
            fixed_guard_s=getattr(args, "drc_fixed_guard_s", 15.0),
        )
    if name in UGR_PROTOCOL_MODES:
        return MeshEchoUGR(
            mode=UGR_PROTOCOL_MODES[name],
            route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
            discovery_window_s=getattr(args, "calm_discovery_window_s", 2.0),
            app_deadline_s=getattr(args, "sr_app_deadline_s", 30.0),
            ack_guard_s=getattr(args, "sr_ack_guard_s", 15.0),
            rrep_wait_s=getattr(args, "sr_rrep_wait_s", 10.0),
        )
    if name in MAG_PROTOCOL_MODES:
        return MeshEchoMAG(
            mode=MAG_PROTOCOL_MODES[name],
            route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
            discovery_window_s=getattr(args, "calm_discovery_window_s", 2.0),
            app_deadline_s=getattr(args, "sr_app_deadline_s", 30.0),
            ack_guard_s=getattr(args, "sr_ack_guard_s", 15.0),
            rrep_wait_s=getattr(args, "sr_rrep_wait_s", 10.0),
        )
    if name in SR_PROTOCOL_MODES:
        return MeshEchoSR(
            mode=SR_PROTOCOL_MODES[name],
            route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
            discovery_window_s=getattr(args, "calm_discovery_window_s", 2.0),
            app_deadline_s=getattr(args, "sr_app_deadline_s", 30.0),
            ack_guard_s=getattr(args, "sr_ack_guard_s", 15.0),
            rrep_wait_s=getattr(args, "sr_rrep_wait_s", 10.0),
        )
    if name in {"meshtastic-common-ack", "meshcore-common-ack"}:
        protocol_class = (
            MeshtasticCommonAck if name == "meshtastic-common-ack"
            else MeshCoreCommonAck
        )
        return protocol_class(
            route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
            ack_guard_s=getattr(args, "sr_ack_guard_s", 15.0),
            app_deadline_s=getattr(args, "sr_app_deadline_s", 30.0),
            base_delay_s=getattr(args, "calm_flood_base_delay_s", 0.45),
            jitter_s=getattr(args, "calm_flood_jitter_s", 0.65),
        )
    if name == "meshtastic":
        return MeshtasticLike()
    if name == "meshcore":
        if args is None:
            return MeshCoreLike()
        return MeshCoreLike(
            route_ttl_s=getattr(
                args,
                "meshcore_route_ttl_s",
                300.0,
            ),
            discovery_window_s=getattr(
                args,
                "meshcore_discovery_window_s",
                DEFAULT_MESHCORE_DISCOVERY_WINDOW_S,
            ),
            rrep_wait_s=getattr(args, "sr_rrep_wait_s", 10.0),
        )
    if name in {"etx", "ett", "prr-product", "prr-product-fallback", "prr-product-ack-evict"}:
        if args is None:
            args = argparse.Namespace()
        metric_kwargs = dict(
            route_ttl_s=getattr(
                args,
                "metric_route_ttl_s",
                getattr(
                    args,
                    "calm_route_ttl_s",
                    getattr(args, "meshcore_route_ttl_s", DEFAULT_MATCHED_MESHCORE_ROUTE_TTL_S),
                ),
            ),
            discovery_window_s=getattr(
                args,
                "metric_discovery_window_s",
                getattr(
                    args,
                    "calm_discovery_window_s",
                    getattr(args, "meshcore_discovery_window_s", DEFAULT_CALM_DISCOVERY_WINDOW_S),
                ),
            ),
            rrep_wait_s=getattr(args, "sr_rrep_wait_s", 10.0),
        )
        if name == "prr-product-ack-evict":
            metric_kwargs["ack_guard_s"] = getattr(args, "ack_guard_s", 15.0)
            return PRRProductAckEvict(**metric_kwargs)
        if name == "prr-product-fallback":
            return PRRProductFallback(**metric_kwargs)
        return MetricMesh(metric_kind=name, **metric_kwargs)
    if name == "minhop":
        if args is None:
            return MinHopMesh()
        return MinHopMesh(
            route_ttl_s=getattr(
                args,
                "minhop_route_ttl_s",
                getattr(
                    args,
                    "calm_route_ttl_s",
                    getattr(
                        args,
                        "meshcore_route_ttl_s",
                        DEFAULT_MATCHED_MESHCORE_ROUTE_TTL_S,
                    ),
                ),
            ),
            discovery_window_s=getattr(
                args,
                "minhop_discovery_window_s",
                getattr(
                    args,
                    "calm_discovery_window_s",
                    getattr(
                        args,
                        "meshcore_discovery_window_s",
                        DEFAULT_CALM_DISCOVERY_WINDOW_S,
                    ),
                ),
            ),
            rrep_wait_s=getattr(args, "sr_rrep_wait_s", 10.0),
        )
    if name in {"calm", "meshecho", "meshecho-calibrated", "meshecho-ack-evict", "meshecho-budgeted", *MESHECHO_ABLATIONS}:
        if args is None:
            if name == "calm":
                return CalmMesh()
            if name == "meshecho":
                return MeshEcho()
            return {
                "meshecho-calibrated": MeshEchoCalibrated,
                "meshecho-ack-evict": MeshEchoAckEvict,
                "meshecho-budgeted": MeshEchoBudgeted,
                "meshecho-no-confidence": MeshEchoNoConfidence,
                "meshecho-no-fallback": MeshEchoNoFallback,
                "meshecho-no-hop-penalty": MeshEchoNoHopPenalty,
                "meshecho-no-age-penalty": MeshEchoNoAgePenalty,
            }[name]()
        meshecho_classes = {
            "meshecho": MeshEcho,
            "meshecho-calibrated": MeshEchoCalibrated,
            "meshecho-ack-evict": MeshEchoAckEvict,
            "meshecho-budgeted": MeshEchoBudgeted,
            "meshecho-no-confidence": MeshEchoNoConfidence,
            "meshecho-no-fallback": MeshEchoNoFallback,
            "meshecho-no-hop-penalty": MeshEchoNoHopPenalty,
            "meshecho-no-age-penalty": MeshEchoNoAgePenalty,
        }
        protocol_class = CalmMesh if name == "calm" else meshecho_classes[name]
        protocol_kwargs = dict(
            route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
            discovery_window_s=getattr(args, "calm_discovery_window_s", DEFAULT_CALM_DISCOVERY_WINDOW_S),
            flood_base_delay_s=getattr(args, "calm_flood_base_delay_s", 0.45),
            flood_jitter_s=getattr(args, "calm_flood_jitter_s", 0.65),
            fallback_ttl=getattr(args, "calm_fallback_ttl", 2),
            fallback_confidence_threshold=getattr(args, "calm_fallback_confidence_threshold", 0.0),
            fallback_delay_margin_s=getattr(args, "calm_fallback_delay_margin_s", 0.6),
            hop_penalty_per_hop=getattr(args, "calm_hop_penalty_per_hop", 0.025),
            route_age_penalty=getattr(args, "calm_route_age_penalty", 0.1),
            route_miss_recovery_enabled=not getattr(
                args,
                "calm_disable_route_miss_fallback",
                False,
            ),
            rrep_wait_s=getattr(args, "sr_rrep_wait_s", 10.0),
        )
        if name == "meshecho-ack-evict":
            protocol_kwargs["ack_guard_s"] = getattr(args, "ack_guard_s", 15.0)
        protocol = protocol_class(**protocol_kwargs)
        return protocol
    if name in {
        "smart-calm",
        "smart-calm-static",
        "smart-calm-no-fallback",
        "smart-calm-no-confidence",
    }:
        if args is None:
            args = argparse.Namespace()
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
            protocol_name=name,
            update_interval_s=getattr(args, "smart_update_interval_s", 30.0),
            learning_rate=getattr(args, "smart_learning_rate", 0.45),
            exploration=getattr(args, "smart_exploration", 0.02),
            flow_timeout_s=getattr(args, "smart_flow_timeout_s", 15.0),
            max_timeout_retries=getattr(args, "smart_max_timeout_retries", 2),
            retry_after_fallback=getattr(args, "smart_retry_after_fallback", False),
            route_miss_fallback_ttl=getattr(args, "smart_route_miss_fallback_ttl", 0),
            timeout_fallback_min_ttl=getattr(args, "smart_timeout_fallback_min_ttl", 1),
            prior_q_values=SmartCalmMesh.load_prior_q_values(getattr(args, "smart_prior_json"))
            if getattr(args, "smart_prior_json", None)
            else None,
            flood_base_delay_s=getattr(args, "calm_flood_base_delay_s", 0.45),
            flood_jitter_s=getattr(args, "calm_flood_jitter_s", 0.65),
            rrep_wait_s=getattr(args, "sr_rrep_wait_s", 10.0),
            profiles=profiles,
            learning_enabled=name != "smart-calm-static",
            fallback_enabled=name != "smart-calm-no-fallback",
            confidence_enabled=name != "smart-calm-no-confidence",
            fixed_profile_index=1 if name == "smart-calm-static" else None,
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
        tx_current_ma=getattr(args, "tx_current_ma", 120.0),
        rx_current_ma=getattr(args, "rx_current_ma", 10.3),
        supply_voltage_v=getattr(args, "supply_voltage_v", 3.3),
        path_loss_exp=args.path_loss_exp,
        shadow_sigma_db=args.shadow_sigma_db,
        temporal_fading_sigma_db=getattr(args, "temporal_fading_sigma_db", 0.0),
        temporal_fading_interval_s=getattr(
            args,
            "temporal_fading_interval_s",
            60.0,
        ),
        capture_threshold_db=args.capture_threshold_db,
    )
    protocol = build_protocol(protocol_name, args)
    sim = Simulator(
        nodes,
        radio,
        protocol,
        seed=seed,
        max_hops=args.max_hops,
        independent_random_streams=independent_rng_streams_enabled(args),
    )
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
        "destination_unicast_pdr",
        "broadcast_coverage",
        "avg_delay_s",
        "mean_delivery_delay_s",
        "p95_unicast_ack_delay_s",
        "tx_count",
        "data_tx",
        "control_tx",
        "ack_tx",
        "total_airtime_s",
        "channel_busy_ratio",
        "total_energy_j",
        "energy_per_delivery_j",
        "airtime_per_delivery_s",
        "packet_reception_ratio",
        "collision_fail",
        "collision_rate",
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
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys()),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="LoRa mesh routing simulator")
    parser.add_argument(
        "--protocol",
        choices=[
            "meshtastic",
            "meshcore",
            "meshtastic-common-ack",
            "meshcore-common-ack",
            "etx",
            "ett",
            "prr-product",
            "prr-product-fallback",
            "prr-product-ack-evict",
            "minhop",
            "calm",
            "meshecho",
            "meshecho-calibrated",
            "meshecho-ack-evict",
            "meshecho-budgeted",
            *MESHECHO_ABLATIONS,
            *SR_PROTOCOL_MODES,
            *MAG_PROTOCOL_MODES,
            *LPR_PROTOCOL_MODES,
            *CPR_PROTOCOL_MODES,
            "meshecho-dpa",
            "meshecho-dpa-repeat",
            "meshecho-dpa-fr",
            "meshecho-rac",
            "meshecho-rac-repeat",
            "meshecho-rac-fr",
            "meshecho-clar",
            "meshecho-clar-nocancel",
            "meshecho-clar-repeat",
            "meshecho-clar-fr",
            "meshecho-dhr-flood-ack-delay",
            "meshecho-dhr-flood-ack-delay-flood2",
            "meshecho-dhr-flood-ack-delay-repeat",
            "meshecho-dhr-flood-ack-delay-guard1",
            "meshecho-dhr-flood-ack-delay-guard2",
            "meshecho-dhr-flood-ack-delay-guard4",
            "meshecho-dhr-flood-ack-delay-guard8",
            "meshecho-dcb-source-trigger-f",
            "smart-calm",
            "smart-calm-static",
            "smart-calm-no-fallback",
            "smart-calm-no-confidence",
            "both",
            "all",
            "all4",
            "icc",
        ],
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
    parser.add_argument(
        "--payload-bytes",
        type=int,
        default=32,
        help="application payload bytes; modeled packet headers are added",
    )
    parser.add_argument("--tx-power-dbm", type=float, default=17.0)
    parser.add_argument(
        "--tx-current-ma",
        type=float,
        default=120.0,
        help="radio transmit current used for energy accounting",
    )
    parser.add_argument(
        "--rx-current-ma",
        type=float,
        default=10.3,
        help="radio receive/listen current used for energy accounting",
    )
    parser.add_argument(
        "--supply-voltage-v",
        type=float,
        default=3.3,
        help="radio supply voltage used for energy accounting",
    )
    parser.add_argument("--path-loss-exp", type=float, default=2.7)
    parser.add_argument("--shadow-sigma-db", type=float, default=4.0)
    parser.add_argument(
        "--temporal-fading-sigma-db",
        type=float,
        default=0.0,
        help="block-fading standard deviation in dB; zero keeps static shadowing",
    )
    parser.add_argument(
        "--temporal-fading-interval-s",
        type=float,
        default=60.0,
        help="duration of each paired block-fading interval",
    )
    parser.add_argument("--capture-threshold-db", type=float, default=6.0)
    parser.add_argument(
        "--independent-rng-streams",
        action="store_true",
        help=(
            "use a separate random stream for channel reception outcomes; "
            "keeps protocol jitter and learning draws from consuming it"
        ),
    )
    parser.add_argument("--calm-route-ttl-s", type=float, default=600.0)
    parser.add_argument(
        "--meshcore-route-ttl-s",
        type=float,
        default=DEFAULT_MATCHED_MESHCORE_ROUTE_TTL_S,
        help="source-route cache lifetime for the MeshCore-like baseline",
    )
    parser.add_argument(
        "--meshcore-discovery-window-s",
        type=float,
        default=DEFAULT_MESHCORE_DISCOVERY_WINDOW_S,
        help=(
            "optional route-discovery collection window for MeshCore-like; "
            "set to the CALM window for a matched timing audit"
        ),
    )
    parser.add_argument("--calm-discovery-window-s", type=float, default=2.0)
    parser.add_argument("--sr-rrep-wait-s", type=float, default=10.0)
    parser.add_argument("--calm-flood-base-delay-s", type=float, default=0.45)
    parser.add_argument("--calm-flood-jitter-s", type=float, default=0.65)
    parser.add_argument("--calm-fallback-ttl", type=int, default=2)
    parser.add_argument("--calm-fallback-confidence-threshold", type=float, default=0.0)
    parser.add_argument("--calm-fallback-delay-margin-s", type=float, default=0.6)
    parser.add_argument("--calm-hop-penalty-per-hop", type=float, default=0.025)
    parser.add_argument("--calm-route-age-penalty", type=float, default=0.1)
    parser.add_argument(
        "--calm-disable-route-miss-fallback",
        action="store_true",
        help=(
            "disable CALM fallback after route-discovery failure; "
            "used for recovery-budget sensitivity checks"
        ),
    )
    parser.add_argument("--smart-update-interval-s", type=float, default=30.0)
    parser.add_argument("--smart-learning-rate", type=float, default=0.45)
    parser.add_argument("--smart-exploration", type=float, default=0.02)
    parser.add_argument("--smart-flow-timeout-s", type=float, default=15.0)
    parser.add_argument("--smart-max-timeout-retries", type=int, default=2)
    parser.add_argument(
        "--smart-route-miss-fallback-ttl",
        type=int,
        default=0,
        help="limit route-miss fallback radius; 0 keeps the normal max-hops route-discovery recovery",
    )
    parser.add_argument(
        "--smart-timeout-fallback-min-ttl",
        type=int,
        default=1,
        help="minimum fallback radius after a timeout retry; use 2 to reproduce Smart-CALM v1.1",
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
        protocols = ["meshtastic", "meshcore", "etx", "ett", "minhop", "meshecho"]
    elif args.protocol == "all4":
        protocols = [
            "meshtastic",
            "meshcore",
            "etx",
            "ett",
            "minhop",
            "meshecho",
            "smart-calm",
        ]
    elif args.protocol == "icc":
        protocols = list(ICC_PROTOCOLS)
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
