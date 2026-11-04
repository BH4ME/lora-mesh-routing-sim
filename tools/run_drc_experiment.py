#!/usr/bin/env python3
"""Auditable mechanical-smoke runner for the independent MeshEcho-DRC core.

This runner deliberately owns its evidence schema instead of treating the
legacy SR runner's summary as DRC evidence.  It freezes one application trace
and one topology/pair pool per seed, executes all arms on that same input, and
emits a request-to-TX ledger, per-receiver RX attempts, and ACK provenance.

Only the ``smoke``/``custom`` stages are exposed here.  Development and
holdout cohorts must be frozen and authorized by a later experiment layer;
this module must not silently open either cohort.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import random
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import (  # noqa: E402
    BROADCAST_DST,
    EVENT_PRIORITY,
    Node,
    Packet,
    RadioConfig,
    Simulator,
    Transmission,
    build_protocol,
    generate_nodes,
)


# Keep all controls on the same physical simulator wire.  The arm names are
# existing build_protocol identities, so no label-only alias can accidentally
# turn into a different implementation.
DRC_PROTOCOLS = (
    "meshecho-drc",
    "meshecho-drc-no-rescue",
    "meshecho-drc-fixed-guard",
    "meshecho-drc-all-f",
    "meshecho-drc-r-only",
)
SAME_WIRE_CONTROLS = DRC_PROTOCOLS[1:]
SCHEMA = "meshecho-drc-evidence-v1"
CONTRACT_PATH = ROOT / "docs" / "research" / "meshecho_drc_runner_contract_20261006.md"
VERSION_PATH = ROOT / "VERSION"


@dataclass(frozen=True)
class DrcCase:
    """All inputs that affect one paired application trace.

    ``fixed-once`` is the default because a mechanical smoke should be
    deterministic and easy to inspect.  ``poisson`` remains available for a
    later, explicitly frozen experiment stage.
    """

    key: str = "drc_smoke"
    nodes: int = 8
    area_m: float = 250.0
    duration_s: float = 120.0
    rate_per_min: float = 4.0
    traffic: str = "unicast"
    pair_count: int = 4
    pair_schedule: str = "fixed-once"
    payload_bytes: int = 32
    tx_power_dbm: float = 17.0
    path_loss_exp: float = 2.75
    shadow_sigma_db: float = 4.0
    temporal_fading_sigma_db: float = 0.0
    temporal_fading_interval_s: float = 60.0
    capture_threshold_db: float = 6.0
    sf: int = 9
    bw_hz: int = 125_000
    cr: int = 1
    max_hops: int = 6
    route_ttl_s: float = 600.0
    flood_base_delay_s: float = 0.45
    flood_jitter_s: float = 0.65
    safety_margin_s: float = 0.25
    fixed_guard_s: float = 15.0

    def __post_init__(self) -> None:
        if self.nodes < 2:
            raise ValueError("DRC case requires at least two nodes")
        if self.area_m <= 0 or self.duration_s <= 0:
            raise ValueError("DRC case area and duration must be positive")
        if self.pair_count <= 0:
            raise ValueError("DRC case pair_count must be positive")
        if self.pair_count > self.nodes * (self.nodes - 1):
            raise ValueError("DRC pair_count exceeds directed node pairs")
        if self.pair_schedule not in {"fixed-once", "poisson"}:
            raise ValueError("unknown DRC pair schedule")


@dataclass(frozen=True)
class DrcRun:
    row: Dict[str, Any]
    flows: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    requests: List[Dict[str, Any]]
    transmissions: List[Dict[str, Any]]
    rx_attempts: List[Dict[str, Any]]
    acks: List[Dict[str, Any]]
    identity: Dict[str, Any]


@dataclass(frozen=True)
class DrcExperiment:
    case: DrcCase
    protocols: Tuple[str, ...]
    seeds: Tuple[int, ...]
    deadline_s: float
    split: str
    runs: List[Dict[str, Any]]
    flows: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    requests: List[Dict[str, Any]]
    transmissions: List[Dict[str, Any]]
    rx_attempts: List[Dict[str, Any]]
    acks: List[Dict[str, Any]]
    paired: List[Dict[str, Any]]
    source_sha256: Dict[str, str]
    identities: Dict[int, Dict[str, Any]]


class _RecordingSimulator(Simulator):
    """Keep every started TX after the simulator prunes its collision window."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.tx_history: List[Transmission] = []

    def begin_transmission(self, sender: int, packet: Packet, pending: Any) -> None:
        previous = self.metrics.tx_count
        super().begin_transmission(sender, packet, pending)
        if self.metrics.tx_count > previous:
            self.tx_history.append(self.tx_history_packet())

    def tx_history_packet(self) -> Transmission:
        # ``begin_transmission`` appends to ``self.transmissions`` before the
        # event is scheduled.  The last element is the newly committed TX.
        return self.transmissions[-1]


def _canonical(value: Any) -> Any:
    """Convert simulator values to deterministic JSON-compatible values."""

    if isinstance(value, Mapping):
        return {str(key): _canonical(item) for key, item in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_canonical(item) for item in value]
    if hasattr(value, "value") and not isinstance(value, (str, bytes)):
        return _canonical(value.value)
    if hasattr(value, "__dict__") and not isinstance(value, type):
        return _canonical(vars(value))
    if isinstance(value, float):
        return round(value, 12)
    return value


def _digest(value: Any) -> str:
    payload = json.dumps(_canonical(value), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    """Hash a file without materializing its contents in memory.

    Population RX ledgers can be gigabytes even though each individual row is
    small.  ``Path.read_bytes`` briefly duplicates that whole ledger in RAM,
    which is particularly harmful while the just-finished simulation still
    owns its in-memory evidence.  Fixed-size chunks keep the hash operation
    bounded independently of artifact size.
    """

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_hashes() -> Dict[str, str]:
    paths = (
        ROOT / "lora_mesh_sim.py",
        ROOT / "meshecho_drc.py",
        Path(__file__).resolve(),
        CONTRACT_PATH,
    )
    return {str(path.relative_to(ROOT)): _file_sha256(path) for path in paths}


def _git_revision() -> str:
    try:
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
        ).strip()
        dirty = subprocess.run(
            ["git", "diff", "--quiet", "--"], cwd=ROOT,
            check=False,
        ).returncode != 0
        return revision + ("+dirty" if dirty else "")
    except (OSError, subprocess.SubprocessError):
        return "unavailable"


def _version() -> str:
    try:
        return VERSION_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return "unversioned"


def _radio(case: DrcCase) -> RadioConfig:
    return RadioConfig(
        sf=case.sf,
        bw_hz=case.bw_hz,
        cr=case.cr,
        payload_bytes=case.payload_bytes,
        tx_power_dbm=case.tx_power_dbm,
        tx_current_ma=120.0,
        rx_current_ma=10.3,
        supply_voltage_v=3.3,
        path_loss_exp=case.path_loss_exp,
        shadow_sigma_db=case.shadow_sigma_db,
        temporal_fading_sigma_db=case.temporal_fading_sigma_db,
        temporal_fading_interval_s=case.temporal_fading_interval_s,
        capture_threshold_db=case.capture_threshold_db,
    )


def _make_pair_pool(nodes: Sequence[Node], seed: int, count: int) -> List[Tuple[int, int]]:
    pairs = [(a.node_id, b.node_id) for a in nodes for b in nodes if a.node_id != b.node_id]
    random.Random(seed + 20_000).shuffle(pairs)
    return pairs[:count]


def _schedule_traffic(
    sim: Simulator,
    case: DrcCase,
    pairs: Sequence[Tuple[int, int]],
    seed: int,
) -> None:
    if case.traffic != "unicast":
        raise ValueError("DRC evidence runner currently requires unicast traffic")
    if case.pair_schedule == "fixed-once":
        if case.duration_s <= 1.0:
            raise ValueError("fixed-once DRC case duration must exceed 1 second")
        for flow_id, (src, dst) in enumerate(pairs, start=1):
            when = 1.0 + (flow_id - 1) * min(1.0, (case.duration_s - 1.0) / max(1, len(pairs)))
            sim.schedule(when, "app_send", (src, dst, flow_id))
        return
    rng = random.Random(seed + 10_000)
    mean_interval = 60.0 / case.rate_per_min if case.rate_per_min > 0 else case.duration_s
    now = 1.0
    flow_id = 1
    while now < case.duration_s:
        src, dst = pairs[(flow_id - 1) % len(pairs)]
        sim.schedule(now, "app_send", (src, dst, flow_id))
        flow_id += 1
        now += rng.expovariate(1.0 / mean_interval)


def _trace_from_events(sim: Simulator) -> Tuple[List[Dict[str, Any]], str]:
    events = sorted(
        (when, event_order, data)
        for when, event_order, kind, data in sim.events
        if kind == "app_send"
    )
    trace = [
        {
            "time": when,
            "ordinal": ordinal,
            "src": data[0],
            "dst": data[1],
            "flow_id": data[2],
        }
        for ordinal, (when, _event_order, data) in enumerate(events, start=1)
    ]
    if not trace:
        raise ValueError("DRC case scheduled no application flows")
    return trace, _digest(trace)


def _topology_identity(nodes: Sequence[Node], radio: RadioConfig, pairs: Sequence[Tuple[int, int]]) -> Dict[str, str]:
    topology = [
        {"node_id": node.node_id, "x": node.x, "y": node.y, "role": node.role}
        for node in nodes
    ]
    radio_fields = {
        key: value for key, value in vars(radio).items()
        if not key.startswith("_")
    }
    return {
        "topology_sha256": _digest(topology),
        "radio_sha256": _digest(radio_fields),
        "pair_pool_sha256": _digest(list(pairs)),
    }


def _packet_row(tx: Transmission, request_by_tx: Mapping[int, Mapping[str, Any]], deadline_by_flow: Mapping[int, float], cutoff: float) -> Dict[str, Any]:
    packet = tx.packet
    deadline = deadline_by_flow.get(packet.flow_id)
    request = request_by_tx.get(tx.tx_id, {})
    return {
        "tx_id": tx.tx_id,
        "tx_request_id": request.get("tx_request_id"),
        "sender": tx.sender,
        "flow_id": packet.flow_id,
        "wire_request_id": packet.request_id,
        "packet_kind": packet.kind,
        "actual_packet_kind": packet.kind,
        "origin": packet.origin,
        "final_dst": packet.final_dst,
        "path": tuple(packet.path),
        "path_index": packet.path_index,
        "repair_index": packet.repair_index,
        "start": tx.start,
        "end": tx.end,
        "toa_s": tx.end - tx.start,
        "deadline_at": deadline,
        "deadline_class": (
            "before_deadline" if deadline is None or tx.start <= deadline else "post_deadline"
        ),
        "cutoff_class": "before_cutoff" if tx.start <= cutoff else "post_cutoff",
    }


def _request_rows(
    sim: Simulator,
    protocol: Any,
    trace: Sequence[Mapping[str, Any]],
    deadline_s: float,
    cutoff: float,
    arm: str,
) -> List[Dict[str, Any]]:
    deadlines = {int(item["flow_id"]): float(item["time"]) + deadline_s for item in trace}
    decision_by_flow: Dict[int, List[Mapping[str, Any]]] = defaultdict(list)
    for event in getattr(protocol, "action_events", []):
        if event.get("event") == "decision":
            decision_by_flow[int(event["flow_id"])].append(event)
    rows: List[Dict[str, Any]] = []
    for source in sim.tx_requests:
        row = dict(source)
        row["protocol"] = arm
        tx_request_id = row.pop("request_id")
        row["tx_request_id"] = tx_request_id
        row["request_id"] = row.get("wire_request_id")
        row["deadline_at"] = deadlines.get(int(row["flow_id"]), row.get("deadline_at"))
        start = row.get("start")
        status_at = row.get("status_at")
        cutoff_time = start if start is not None else status_at
        row["cutoff_class"] = (
            "before_cutoff" if cutoff_time is not None and cutoff_time <= cutoff else "post_cutoff"
        )
        deadline = row.get("deadline_at")
        row["deadline_class"] = (
            "before_deadline" if start is not None and deadline is not None and start <= deadline
            else "post_deadline" if start is not None
            else "no_start"
        )
        row["toa_s"] = (
            float(row["end"]) - float(row["start"])
            if row.get("start") is not None and row.get("end") is not None else None
        )
        row["status_reason"] = row.get("no_start_reason")
        if row["status"] == "protocol-no-start":
            decisions = decision_by_flow.get(int(row["flow_id"]), [])
            if decisions and any("deadline-infeasible" in str(item.get("reason", "")) for item in decisions):
                row["status_reason"] = "deadline-infeasible"
                row["raw_no_start_reason"] = row.get("no_start_reason")
        row["case_cutoff_s"] = cutoff
        rows.append(row)
    return rows


def _flow_rows(
    sim: Simulator,
    protocol: Any,
    trace: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
    deadline_s: float,
    arm: str,
) -> List[Dict[str, Any]]:
    requests_by_flow: Dict[int, List[Mapping[str, Any]]] = defaultdict(list)
    for request in request_rows:
        requests_by_flow[int(request["flow_id"])].append(request)
    actions_by_flow: Dict[int, List[Mapping[str, Any]]] = defaultdict(list)
    for event in getattr(protocol, "action_events", []):
        actions_by_flow[int(event["flow_id"])].append(event)
    rows: List[Dict[str, Any]] = []
    for item in trace:
        flow_id = int(item["flow_id"])
        when = float(item["time"])
        deadline = when + deadline_s
        metric = sim.metrics.flows.get(flow_id)
        decisions = [event for event in actions_by_flow[flow_id] if event.get("event") == "decision"]
        initial_decision = decisions[0] if decisions else {}
        recovery_decisions = decisions[1:]
        requests = requests_by_flow[flow_id]
        initial_requests = [request for request in requests if request.get("packet_kind") == "DRC_REQUEST"]
        recovery_requests = [request for request in requests if request.get("packet_kind") == "DRC_RECOVERY_REQUEST"]
        initial_started = next((request for request in initial_requests if request.get("status") == "started"), None)
        recovery_started = next((request for request in recovery_requests if request.get("status") == "started"), None)
        no_start_reasons = [
            request.get("status_reason") or request.get("no_start_reason")
            for request in requests
            if request.get("status") != "started"
        ]
        acked_at = metric.acked_at if metric is not None else None
        delivered_at = metric.delivered_at if metric is not None else None
        rows.append({
            "protocol": arm,
            "flow_id": flow_id,
            "src": int(item["src"]),
            "dst": int(item["dst"]),
            "enqueued_at": when,
            "deadline_at": deadline,
            "registered": metric is not None,
            "initial_decision_at": initial_decision.get("time"),
            "initial_action": initial_decision.get("action"),
            "decision_reason": initial_decision.get("reason"),
            "route_generation": initial_decision.get("route_generation"),
            "initial_request_id": initial_started.get("tx_request_id") if initial_started else None,
            "initial_physical_start": initial_started.get("start") if initial_started else None,
            "recovery_state": (
                "started" if recovery_started else
                "requested" if recovery_requests else
                "not_due"
            ),
            "recovery_request_id": recovery_started.get("tx_request_id") if recovery_started else None,
            "recovery_physical_start": recovery_started.get("start") if recovery_started else None,
            "recovery_decision_count": len(recovery_decisions),
            "accepted_ack_at": acked_at,
            "first_delivery_at": delivered_at,
            "ack_by_deadline": bool(acked_at is not None and acked_at <= deadline),
            "delivery_by_deadline": bool(delivered_at is not None and delivered_at <= deadline),
            "late_ack": bool(acked_at is not None and acked_at > deadline),
            "late_delivery": bool(delivered_at is not None and delivered_at > deadline),
            "no_start_count": len(no_start_reasons),
            "no_start_reasons": tuple(reason for reason in no_start_reasons if reason),
            "state_capacity_drop": any(
                str(event.get("reason", "")) == "state-capacity-drop"
                for event in actions_by_flow[flow_id]
            ),
            "deadline_infeasible": any(
                "deadline-infeasible" in str(event.get("reason", ""))
                for event in actions_by_flow[flow_id]
            ),
        })
    return rows


def _action_rows(protocol: Any, arm: str, seed: int, case: DrcCase) -> List[Dict[str, Any]]:
    rows = []
    for ordinal, event in enumerate(getattr(protocol, "action_events", []), start=1):
        rows.append({
            "case": case.key,
            "protocol": arm,
            "seed": seed,
            "action_ordinal": ordinal,
            **_canonical(event),
        })
    return rows


def _identity_records(
    case: DrcCase,
    arm: str,
    seed: int,
    trace: Sequence[Mapping[str, Any]],
    trace_sha256: str,
    nodes: Sequence[Node],
    radio: RadioConfig,
    pairs: Sequence[Tuple[int, int]],
) -> Dict[str, Any]:
    identity = _topology_identity(nodes, radio, pairs)
    return {
        "seed": seed,
        "protocol": arm,
        "case_sha256": _digest(asdict(case)),
        "trace_sha256": trace_sha256,
        "trace_schema": "time+ordinal+src+dst+flow_id",
        **identity,
    }


def run_one(
    case: DrcCase,
    protocol_name: str,
    seed: int,
    deadline_s: float = 30.0,
) -> DrcRun:
    """Run one DRC arm and return only auditable raw evidence plus a summary."""

    if protocol_name not in DRC_PROTOCOLS:
        raise ValueError(f"unknown DRC arm: {protocol_name}")
    if type(seed) is not int:
        raise ValueError("DRC seed must be an integer")
    if deadline_s <= 0:
        raise ValueError("DRC deadline_s must be positive")

    topology_rng = random.Random(seed)
    nodes = generate_nodes(case.nodes, case.area_m, topology_rng, repeater_ratio=0.0)
    radio = _radio(case)
    args = argparse.Namespace(
        calm_route_ttl_s=case.route_ttl_s,
        calm_flood_base_delay_s=case.flood_base_delay_s,
        calm_flood_jitter_s=case.flood_jitter_s,
        sr_app_deadline_s=deadline_s,
        drc_safety_margin_s=case.safety_margin_s,
        drc_fixed_guard_s=case.fixed_guard_s,
    )
    protocol = build_protocol(protocol_name, args)
    sim = _RecordingSimulator(
        nodes,
        radio,
        protocol,
        seed=seed,
        max_hops=case.max_hops,
        independent_random_streams=True,
        record_rx_attempts=True,
    )
    pairs = _make_pair_pool(nodes, seed, case.pair_count)
    _schedule_traffic(sim, case, pairs, seed)
    trace, trace_sha256 = _trace_from_events(sim)
    cutoff = case.duration_s + deadline_s
    identity = _identity_records(case, protocol_name, seed, trace, trace_sha256, nodes, radio, pairs)
    sim.run(cutoff)
    sim.finalize_request_ledger(cutoff)

    requests = _request_rows(sim, protocol, trace, deadline_s, cutoff, protocol_name)
    request_by_tx = {
        int(row["tx_id"]): row for row in requests
        if row.get("status") == "started" and row.get("tx_id") is not None
    }
    deadlines = {int(item["flow_id"]): float(item["time"]) + deadline_s for item in trace}
    transmissions = [
        _packet_row(tx, request_by_tx, deadlines, cutoff)
        for tx in sim.tx_history
    ]
    tx_request_by_tx = {
        int(row["tx_id"]): row.get("tx_request_id")
        for row in transmissions
        if row.get("tx_id") is not None
    }
    rx_attempts = []
    for source in sim.rx_attempts:
        row = dict(source)
        row["protocol"] = protocol_name
        row["tx_request_id"] = tx_request_by_tx.get(int(row["tx_id"]))
        deadline = deadlines.get(int(row["flow_id"]))
        row["in_deadline"] = bool(deadline is not None and float(row["end"]) <= deadline)
        rx_attempts.append(_canonical(row))
    acks = []
    for source in sim.ack_provenance:
        row = dict(source)
        row["protocol"] = protocol_name
        row["ack_tx_request_id"] = tx_request_by_tx.get(row.get("ack_tx_id"))
        deadline = deadlines.get(int(row["flow_id"]))
        row["in_deadline"] = bool(
            deadline is not None and row.get("accepted_at") is not None
            and float(row["accepted_at"]) <= deadline
        )
        acks.append(_canonical(row))
    flows = _flow_rows(sim, protocol, trace, requests, deadline_s, protocol_name)
    actions = _action_rows(protocol, protocol_name, seed, case)
    metrics = sim.metrics.summarize(protocol_name, seed, cutoff)
    acked = sum(bool(row["ack_by_deadline"]) for row in flows)
    delivered = sum(bool(row["delivery_by_deadline"]) for row in flows)
    started = [row for row in requests if row.get("status") == "started"]
    tx_airtime = sum(float(row["toa_s"]) for row in transmissions if row["start"] <= cutoff)
    tx_energy = sum(
        float(row["toa_s"]) * radio.supply_voltage_v * radio.tx_current_ma / 1000.0
        for row in transmissions if row["start"] <= cutoff
    )
    rx_count_by_tx = Counter(int(item["tx_id"]) for item in rx_attempts)
    spillover_tx = [
        item for item in transmissions
        if float(item["start"]) <= cutoff < float(item["end"])
    ]
    # ``Simulator.run(cutoff)`` intentionally does not process a tx_end after
    # cutoff.  Refusing an incomplete RX ledger is safer than silently
    # treating that packet as having no receivers; a future staged runner may
    # use an extended physical drain and prove the corresponding window rule.
    incomplete_rx_tx = [
        item["tx_id"] for item in transmissions
        if float(item["start"]) <= cutoff
        and rx_count_by_tx.get(int(item["tx_id"]), 0) != case.nodes
    ]
    row = {
        **metrics,
        "case": case.key,
        "protocol": protocol_name,
        "seed": seed,
        "generation_horizon_s": case.duration_s,
        "application_deadline_s": deadline_s,
        "drain_until_s": cutoff,
        "case_sha256": identity["case_sha256"],
        "scheduled_trace_sha256": trace_sha256,
        "topology_sha256": identity["topology_sha256"],
        "radio_sha256": identity["radio_sha256"],
        "pair_pool_sha256": identity["pair_pool_sha256"],
        "scheduled_unicast_flows": len(trace),
        "ack_by_deadline": acked,
        "delivery_by_deadline": delivered,
        "ack_pdr_deadline": acked / len(trace),
        "delivery_pdr_deadline": delivered / len(trace),
        "late_ack_count": sum(bool(item["late_ack"]) for item in flows),
        "late_delivery_count": sum(bool(item["late_delivery"]) for item in flows),
        "request_count": len(requests),
        "started_request_count": len(started),
        "no_start_count": len(requests) - len(started),
        "tx_ledger_airtime_s": tx_airtime,
        "tx_ledger_energy_j": tx_energy,
        "rx_attempt_count": len(rx_attempts),
        "accepted_ack_count": sum(bool(item["accepted"]) for item in acks),
        "protocol_action_count": len(actions),
        "spillover_tx_count": len(spillover_tx),
        "incomplete_rx_tx_count": len(incomplete_rx_tx),
        "seed_split": "smoke",
    }
    # Request and physical evidence IDs are only run-local.  Persist the
    # scope beside every row so an auditor never joins equal tx_id values from
    # different paired arms by accident.
    for collection in (flows, actions, requests, transmissions, rx_attempts, acks):
        for evidence in collection:
            evidence.setdefault("case", case.key)
            evidence.setdefault("seed", seed)
            evidence.setdefault("protocol", protocol_name)
    return DrcRun(row, flows, actions, requests, transmissions, rx_attempts, acks, identity)


def run_one_drc(
    case: DrcCase,
    protocol_name: str,
    seed: int,
    deadline_s: float = 30.0,
) -> DrcRun:
    """Explicitly named public alias for callers migrating from SR runners."""

    return run_one(case, protocol_name, seed, deadline_s)


def _paired_rows(runs: Sequence[Mapping[str, Any]], protocols: Sequence[str]) -> List[Dict[str, Any]]:
    by_seed = {(int(row["seed"]), str(row["protocol"])): row for row in runs}
    focus = protocols[0]
    result = []
    for seed in sorted({int(row["seed"]) for row in runs}):
        base = by_seed[(seed, focus)]
        for comparator in protocols[1:]:
            other = by_seed[(seed, comparator)]
            result.append({
                "seed": seed,
                "focus": focus,
                "comparator": comparator,
                "ack_pdr_gain": base["ack_pdr_deadline"] - other["ack_pdr_deadline"],
                "delivery_pdr_gain": base["delivery_pdr_deadline"] - other["delivery_pdr_deadline"],
                "relative_airtime_cost": (
                    (base["tx_ledger_airtime_s"] - other["tx_ledger_airtime_s"])
                    / other["tx_ledger_airtime_s"]
                    if other["tx_ledger_airtime_s"] else None
                ),
                "trace_match": base["scheduled_trace_sha256"] == other["scheduled_trace_sha256"],
                "topology_match": base["topology_sha256"] == other["topology_sha256"],
                "pair_pool_match": base["pair_pool_sha256"] == other["pair_pool_sha256"],
            })
    return result


def run_matrix(
    case: DrcCase,
    protocols: Sequence[str] = DRC_PROTOCOLS,
    seeds: Sequence[int] = (91000,),
    deadline_s: float = 30.0,
    split: str = "smoke",
) -> DrcExperiment:
    """Run a paired mechanical smoke matrix and reject identity drift."""

    protocols = tuple(protocols)
    seeds = tuple(seeds)
    if split not in {"smoke", "custom"}:
        raise ValueError("DRC runner only permits smoke/custom; development/holdout are closed")
    if not protocols or not seeds:
        raise ValueError("protocols and seeds must be nonempty")
    if len(set(protocols)) != len(protocols):
        raise ValueError("protocol list contains duplicates")
    if len(set(seeds)) != len(seeds):
        raise ValueError("seed list contains duplicates")
    unknown = [name for name in protocols if name not in DRC_PROTOCOLS]
    if unknown:
        raise ValueError(f"unknown DRC arm: {unknown[0]}")
    if split == "smoke" and tuple(seeds) != (91000,) and len(seeds) != 1:
        # A single arbitrary smoke seed is useful in tests; multi-seed smoke
        # must be explicitly labeled custom to prevent accidental cohort use.
        raise ValueError("smoke accepts one seed; use custom for a matrix")

    runs: List[Dict[str, Any]] = []
    flows: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []
    requests: List[Dict[str, Any]] = []
    transmissions: List[Dict[str, Any]] = []
    rx_attempts: List[Dict[str, Any]] = []
    acks: List[Dict[str, Any]] = []
    identities: Dict[int, Dict[str, Any]] = {}
    for seed in seeds:
        expected_identity: Optional[Dict[str, Any]] = None
        for protocol in protocols:
            result = run_one(case, protocol, seed, deadline_s)
            identity = dict(result.identity)
            identity.pop("protocol", None)
            if expected_identity is None:
                expected_identity = identity
                identities[seed] = dict(result.identity)
            elif identity != expected_identity:
                raise ValueError(f"paired input identity drift for seed {seed} ({protocol})")
            runs.append(dict(result.row, seed_split=split))
            flows.extend(dict(item, seed_split=split) for item in result.flows)
            actions.extend(dict(item, seed_split=split) for item in result.actions)
            requests.extend(dict(item, seed_split=split) for item in result.requests)
            transmissions.extend(dict(item, seed_split=split) for item in result.transmissions)
            rx_attempts.extend(dict(item, seed_split=split) for item in result.rx_attempts)
            acks.extend(dict(item, seed_split=split) for item in result.acks)
    paired = _paired_rows(runs, protocols)
    experiment = DrcExperiment(
        case=case,
        protocols=protocols,
        seeds=seeds,
        deadline_s=deadline_s,
        split=split,
        runs=runs,
        flows=flows,
        actions=actions,
        requests=requests,
        transmissions=transmissions,
        rx_attempts=rx_attempts,
        acks=acks,
        paired=paired,
        source_sha256=_source_hashes(),
        identities=identities,
    )
    _audit_records(experiment)
    return experiment


def iter_matrix(
    case: DrcCase,
    protocols: Sequence[str] = DRC_PROTOCOLS,
    seeds: Sequence[int] = (91000,),
    deadline_s: float = 30.0,
    split: str = "smoke",
) -> Iterator[DrcRun]:
    """Yield one paired arm result at a time without retaining its ledgers.

    ``run_matrix`` is intentionally kept as the convenient in-memory API for
    small smoke tests.  Population experiments, however, may produce
    gigabytes of RX-attempt evidence.  This iterator performs the same input
    validation and common-random-input identity check while allowing callers
    to write each :class:`DrcRun` before the next simulation starts.

    The first arm for a seed establishes its topology/trace identity.  Later
    arms are checked before they are yielded; if identity drift is detected,
    the caller can discard the partially written artifact rather than silently
    compare unpaired inputs.
    """

    protocols = tuple(protocols)
    seeds = tuple(seeds)
    if split not in {"smoke", "custom"}:
        raise ValueError("DRC runner only permits smoke/custom; development/holdout are closed")
    if not protocols or not seeds:
        raise ValueError("protocols and seeds must be nonempty")
    if len(set(protocols)) != len(protocols):
        raise ValueError("protocol list contains duplicates")
    if len(set(seeds)) != len(seeds):
        raise ValueError("seed list contains duplicates")
    unknown = [name for name in protocols if name not in DRC_PROTOCOLS]
    if unknown:
        raise ValueError(f"unknown DRC arm: {unknown[0]}")
    if split == "smoke" and tuple(seeds) != (91000,) and len(seeds) != 1:
        raise ValueError("smoke accepts one seed; use custom for a matrix")

    for seed in seeds:
        expected_identity: Optional[Dict[str, Any]] = None
        for protocol in protocols:
            result = run_one(case, protocol, seed, deadline_s)
            identity = dict(result.identity)
            identity.pop("protocol", None)
            if expected_identity is None:
                expected_identity = identity
            elif identity != expected_identity:
                raise ValueError(f"paired input identity drift for seed {seed} ({protocol})")
            yield result


def _artifact_paths(prefix: Path) -> Dict[str, Path]:
    return {
        "runs": Path(f"{prefix}.runs.csv"),
        "paired": Path(f"{prefix}.paired.csv"),
        "flows": Path(f"{prefix}.flows.jsonl"),
        "actions": Path(f"{prefix}.actions.jsonl"),
        "requests": Path(f"{prefix}.requests.jsonl"),
        "tx": Path(f"{prefix}.tx.jsonl"),
        "rx_attempts": Path(f"{prefix}.rx_attempts.jsonl"),
        "acks": Path(f"{prefix}.acks.jsonl"),
        "manifest": Path(f"{prefix}.manifest.json"),
    }


def artifact_paths(prefix: Path) -> Dict[str, Path]:
    """Return artifact paths without touching the filesystem."""

    return _artifact_paths(Path(prefix))


def _write_csv(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    fieldnames: List[str] = []
    seen = set()
    for record in records:
        for key in record:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("x", newline="", encoding="utf-8") as handle:
        if not fieldnames:
            return
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            writer.writerow({key: _canonical(record.get(key)) for key in fieldnames})


def _write_jsonl(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(_canonical(record), sort_keys=True, separators=(",", ":")))
            handle.write("\n")


def _artifact_records(bundle: DrcExperiment) -> Dict[str, Sequence[Mapping[str, Any]]]:
    return {
        "runs": bundle.runs,
        "paired": bundle.paired,
        "flows": bundle.flows,
        "actions": bundle.actions,
        "requests": bundle.requests,
        "tx": bundle.transmissions,
        "rx_attempts": bundle.rx_attempts,
        "acks": bundle.acks,
    }


def write_artifacts(prefix: Path, bundle: DrcExperiment) -> Dict[str, Path]:
    """Write raw evidence and a self-hashing manifest, refusing overwrite."""

    _audit_records(bundle)
    paths = _artifact_paths(Path(prefix))
    Path(prefix).parent.mkdir(parents=True, exist_ok=True)
    existing = [path for path in paths.values() if path.exists()]
    if existing:
        raise FileExistsError(f"DRC artifact already exists: {existing[0]}")
    records = _artifact_records(bundle)
    for key in ("runs", "paired"):
        _write_csv(paths[key], records[key])
    for key in ("flows", "actions", "requests", "tx", "rx_attempts", "acks"):
        _write_jsonl(paths[key], records[key])

    artifact_sha256 = {
        key: _file_sha256(paths[key]) for key in records
    }
    manifest = {
        "schema": SCHEMA,
        "core_contract_sha256": _file_sha256(CONTRACT_PATH),
        "source_sha256": bundle.source_sha256,
        "sim_version": _version(),
        "git_revision": _git_revision(),
        "python_version": platform.python_version(),
        "case": asdict(bundle.case),
        "case_sha256": _digest(asdict(bundle.case)),
        "protocols": list(bundle.protocols),
        "seeds": list(bundle.seeds),
        "seed_split": bundle.split,
        "deadline_s": bundle.deadline_s,
        "application_trace_schema": "time+ordinal+src+dst+flow_id",
        "event_priority": dict(EVENT_PRIORITY),
        "topology_pair_pool_sha256_by_seed": {
            str(seed): {
                "topology_sha256": identity["topology_sha256"],
                "pair_pool_sha256": identity["pair_pool_sha256"],
            }
            for seed, identity in bundle.identities.items()
        },
        "application_trace_sha256_by_seed": {
            str(seed): identity["trace_sha256"]
            for seed, identity in bundle.identities.items()
        },
        "artifacts": {
            key: {"sha256": artifact_sha256[key], "records": len(records[key])}
            for key in records
        },
        "counts": {
            "runs": len(bundle.runs),
            "scheduled_flows": len(bundle.flows),
            "requests": len(bundle.requests),
            "transmissions": len(bundle.transmissions),
            "rx_attempts": len(bundle.rx_attempts),
            "accepted_acks": sum(bool(row["accepted"]) for row in bundle.acks),
            "invalid_records": 0,
            "spillover_tx": sum(int(row.get("spillover_tx_count", 0)) for row in bundle.runs),
            "incomplete_rx_tx": sum(int(row.get("incomplete_rx_tx_count", 0)) for row in bundle.runs),
        },
        "gates": {
            "mechanical_smoke": True,
            "development": False,
            "holdout": False,
        },
        "paired": {
            "arms": list(bundle.protocols),
            "comparisons": len(bundle.paired),
            "identity_checked": True,
        },
    }
    with paths["manifest"].open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, sort_keys=True, indent=2)
        handle.write("\n")
    return paths


@dataclass(frozen=True)
class DrcStreamResult:
    """Small result returned by :func:`write_artifacts_stream`.

    Evidence rows are deliberately not retained here.  They remain in the
    JSONL artifacts and are checked by :func:`audit_artifacts`; only the run
    summaries and paired identities needed by population-level statistics are
    kept in memory.
    """

    paths: Dict[str, Path]
    runs: List[Dict[str, Any]]
    paired: List[Dict[str, Any]]
    identities: Dict[int, Dict[str, Any]]
    source_sha256: Dict[str, str]


def write_artifacts_stream(
    prefix: Path,
    case: DrcCase,
    protocols: Sequence[str],
    seeds: Sequence[int],
    deadline_s: float,
    split: str,
    results: Iterable[DrcRun],
) -> DrcStreamResult:
    """Append one :class:`DrcRun` at a time and write the normal artifact set.

    This is the disk-backed counterpart to :func:`write_artifacts`.  It keeps
    the full request/TX/RX/ACK evidence, but bounds Python memory by retaining
    only the small run matrix and per-seed input identities.  The output
    schema and manifest fields intentionally match ``write_artifacts`` so the
    existing artifact auditor can be used unchanged.
    """

    protocols = tuple(protocols)
    seeds = tuple(seeds)
    if not protocols or not seeds:
        raise ValueError("protocols and seeds must be nonempty")
    if not str(split).strip():
        raise ValueError("stream artifact split must be nonempty")
    if len(set(protocols)) != len(protocols):
        raise ValueError("protocol list contains duplicates")
    if len(set(seeds)) != len(seeds):
        raise ValueError("seed list contains duplicates")
    unknown = [name for name in protocols if name not in DRC_PROTOCOLS]
    if unknown:
        raise ValueError(f"unknown DRC arm: {unknown[0]}")

    paths = _artifact_paths(Path(prefix))
    Path(prefix).parent.mkdir(parents=True, exist_ok=True)
    existing = [path for path in paths.values() if path.exists()]
    if existing:
        raise FileExistsError(f"DRC artifact already exists: {existing[0]}")

    json_keys = ("flows", "actions", "requests", "tx", "rx_attempts", "acks")
    handles: Dict[str, Any] = {}
    created: List[Path] = []
    runs: List[Dict[str, Any]] = []
    identities: Dict[int, Dict[str, Any]] = {}
    seen_scopes: set[Tuple[int, str]] = set()
    run_fieldnames: Optional[List[str]] = None
    record_counts: Dict[str, int] = {
        "runs": 0,
        "paired": 0,
        **{key: 0 for key in json_keys},
    }
    accepted_ack_count = 0

    def write_jsonl(key: str, rows: Iterable[Mapping[str, Any]]) -> None:
        nonlocal accepted_ack_count
        handle = handles[key]
        for row in rows:
            value = _canonical(row)
            handle.write(json.dumps(value, sort_keys=True, separators=(",", ":")))
            handle.write("\n")
            record_counts[key] += 1
            if key == "acks" and bool(row.get("accepted")):
                accepted_ack_count += 1

    try:
        handles["runs"] = paths["runs"].open("x", newline="", encoding="utf-8")
        created.append(paths["runs"])
        for key in json_keys:
            handles[key] = paths[key].open("x", encoding="utf-8")
            created.append(paths[key])

        for result in results:
            if not isinstance(result, DrcRun):
                raise TypeError("stream results must yield DrcRun values")
            row = dict(result.row, seed_split=split)
            try:
                seed = int(row["seed"])
                protocol = str(row["protocol"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("stream run has an invalid seed/protocol scope") from exc
            scope = (seed, protocol)
            if scope in seen_scopes:
                raise ValueError("duplicate seed/arm run record")
            if seed not in seeds or protocol not in protocols:
                raise ValueError("stream result is outside the declared seed/arm matrix")
            seen_scopes.add(scope)
            if run_fieldnames is None:
                run_fieldnames = list(row)
                writer = csv.DictWriter(
                    handles["runs"],
                    fieldnames=run_fieldnames,
                    extrasaction="ignore",
                )
                writer.writeheader()
            else:
                writer = csv.DictWriter(
                    handles["runs"],
                    fieldnames=run_fieldnames,
                    extrasaction="ignore",
                )
            writer.writerow({key: _canonical(row.get(key)) for key in run_fieldnames})
            runs.append(row)
            record_counts["runs"] += 1

            identity = dict(result.identity)
            identity_without_protocol = dict(identity)
            identity_without_protocol.pop("protocol", None)
            previous = identities.get(seed)
            if previous is None:
                identities[seed] = identity
            else:
                previous_without_protocol = dict(previous)
                previous_without_protocol.pop("protocol", None)
                if previous_without_protocol != identity_without_protocol:
                    raise ValueError(f"paired input identity drift for seed {seed} ({protocol})")

            write_jsonl("flows", (dict(item, seed_split=split) for item in result.flows))
            write_jsonl("actions", (dict(item, seed_split=split) for item in result.actions))
            write_jsonl("requests", (dict(item, seed_split=split) for item in result.requests))
            write_jsonl("tx", (dict(item, seed_split=split) for item in result.transmissions))
            write_jsonl("rx_attempts", (dict(item, seed_split=split) for item in result.rx_attempts))
            write_jsonl("acks", (dict(item, seed_split=split) for item in result.acks))

        expected_scopes = {(seed, protocol) for seed in seeds for protocol in protocols}
        if seen_scopes != expected_scopes:
            raise ValueError("stream run matrix is incomplete")
        if not runs:
            raise ValueError("stream produced no runs")
        if run_fieldnames is None:
            raise ValueError("stream produced no run rows")
        for handle in handles.values():
            handle.flush()
            handle.close()
        handles.clear()

        paired = _paired_rows(runs, protocols)
        _write_csv(paths["paired"], paired)
        created.append(paths["paired"])
        record_counts["paired"] = len(paired)
        artifact_keys = ("runs", "paired", *json_keys)
        artifact_sha256 = {key: _file_sha256(paths[key]) for key in artifact_keys}
        manifest = {
            "schema": SCHEMA,
            "core_contract_sha256": _file_sha256(CONTRACT_PATH),
            "source_sha256": _source_hashes(),
            "sim_version": _version(),
            "git_revision": _git_revision(),
            "python_version": platform.python_version(),
            "case": asdict(case),
            "case_sha256": _digest(asdict(case)),
            "protocols": list(protocols),
            "seeds": list(seeds),
            "seed_split": split,
            "deadline_s": deadline_s,
            "application_trace_schema": "time+ordinal+src+dst+flow_id",
            "event_priority": dict(EVENT_PRIORITY),
            "topology_pair_pool_sha256_by_seed": {
                str(seed): {
                    "topology_sha256": identity["topology_sha256"],
                    "pair_pool_sha256": identity["pair_pool_sha256"],
                }
                for seed, identity in identities.items()
            },
            "application_trace_sha256_by_seed": {
                str(seed): identity["trace_sha256"]
                for seed, identity in identities.items()
            },
            "artifacts": {
                key: {"sha256": artifact_sha256[key], "records": record_counts[key]}
                for key in artifact_keys
            },
            "counts": {
                "runs": record_counts["runs"],
                "scheduled_flows": record_counts["flows"],
                "requests": record_counts["requests"],
                "transmissions": record_counts["tx"],
                "rx_attempts": record_counts["rx_attempts"],
                "accepted_acks": accepted_ack_count,
                "invalid_records": 0,
                "spillover_tx": sum(int(row.get("spillover_tx_count", 0)) for row in runs),
                "incomplete_rx_tx": sum(int(row.get("incomplete_rx_tx_count", 0)) for row in runs),
            },
            "gates": {
                "mechanical_smoke": True,
                "development": False,
                "holdout": False,
            },
            "paired": {
                "arms": list(protocols),
                "comparisons": len(paired),
                "identity_checked": True,
            },
        }
        with paths["manifest"].open("x", encoding="utf-8") as handle:
            json.dump(manifest, handle, sort_keys=True, indent=2)
            handle.write("\n")
        created.append(paths["manifest"])
        return DrcStreamResult(
            paths=paths,
            runs=runs,
            paired=paired,
            identities=identities,
            source_sha256=manifest["source_sha256"],
        )
    except Exception:
        for handle in handles.values():
            try:
                handle.close()
            except OSError:
                pass
        for path in created:
            try:
                path.unlink()
            except OSError:
                pass
        raise


def _iter_jsonl(path: Path) -> Iterator[Dict[str, Any]]:
    """Yield JSONL records one at a time.

    The RX attempt artifact is intentionally append-only and can contain
    millions of rows. Keeping this iterator separate from ``_load_jsonl``
    lets small callers retain the convenient list API while audits consume
    large ledgers with bounded memory.
    """

    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid JSONL record in {Path(path).name} line {line_number}"
                ) from exc
            if not isinstance(value, dict):
                raise ValueError(
                    f"JSONL record in {Path(path).name} line {line_number} is not an object"
                )
            yield value


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    """Compatibility list loader for small callers and focused tests."""

    return list(_iter_jsonl(path))


def _audit_records(bundle: DrcExperiment) -> None:
    expected_runs = len(bundle.protocols) * len(bundle.seeds)
    if len(bundle.runs) != expected_runs:
        raise ValueError("runs record count does not match seed/arm matrix")
    run_keys = [(int(row["seed"]), str(row["protocol"])) for row in bundle.runs]
    if len(set(run_keys)) != len(run_keys):
        raise ValueError("duplicate seed/arm run record")
    expected_keys = {(seed, arm) for seed in bundle.seeds for arm in bundle.protocols}
    if set(run_keys) != expected_keys:
        raise ValueError("missing seed/arm run record")

    for seed in bundle.seeds:
        per_arm = [row for row in bundle.runs if int(row["seed"]) == seed]
        identity_fields = ("case_sha256", "scheduled_trace_sha256", "topology_sha256", "radio_sha256", "pair_pool_sha256")
        for field in identity_fields:
            if len({row[field] for row in per_arm}) != 1:
                raise ValueError(f"paired identity mismatch in {field} for seed {seed}")
    for row in bundle.runs:
        if int(row.get("spillover_tx_count", 0)) != 0 or int(row.get("incomplete_rx_tx_count", 0)) != 0:
            raise ValueError("RX ledger is incomplete for a TX crossing the cutoff")

    scopes = {(int(row["seed"]), str(row["protocol"])) for row in bundle.runs}
    for seed, protocol in scopes:
        scope = lambda rows: [
            row for row in rows
            if int(row.get("seed", -1)) == seed and str(row.get("protocol")) == protocol
        ]
        scoped_requests = scope(bundle.requests)
        scoped_transmissions = scope(bundle.transmissions)
        scoped_rx = scope(bundle.rx_attempts)
        scoped_acks = scope(bundle.acks)
        started = [row for row in scoped_requests if row.get("status") == "started"]
        tx_ids = [int(row["tx_id"]) for row in started if row.get("tx_id") is not None]
        if len(tx_ids) != len(set(tx_ids)):
            raise ValueError("started request ledger has duplicate tx_id")
        physical_ids = [int(row["tx_id"]) for row in scoped_transmissions]
        if set(tx_ids) != set(physical_ids):
            raise ValueError("request/TX one-to-one join failed")
        for row in scoped_transmissions:
            if row.get("toa_s") is None or abs(float(row["toa_s"]) - (float(row["end"]) - float(row["start"]))) > 1e-9:
                raise ValueError("transmission ToA does not recompute")
        tx_id_set = set(physical_ids)
        for row in scoped_rx:
            if int(row["tx_id"]) not in tx_id_set:
                raise ValueError("RX attempt references unknown TX")
            if row.get("reason") not in {"success", "half_duplex", "capture_collision", "prr_fail", "self"}:
                raise ValueError("RX attempt has unknown failure reason")
        rx_count_by_tx = Counter(int(row["tx_id"]) for row in scoped_rx)
        for tx in scoped_transmissions:
            if float(tx["start"]) <= float(next(item["drain_until_s"] for item in bundle.runs if int(item["seed"]) == seed and str(item["protocol"]) == protocol)) and rx_count_by_tx.get(int(tx["tx_id"]), 0) != bundle.case.nodes:
                raise ValueError("RX ledger is incomplete for a started TX")
        attempt_by_id = {int(row["rx_attempt_id"]): row for row in scoped_rx}
        for row in scoped_acks:
            if row.get("accepted"):
                attempt = attempt_by_id.get(int(row["ack_rx_attempt_id"])) if row.get("ack_rx_attempt_id") is not None else None
                if attempt is None or attempt.get("reason") != "success" or not attempt.get("decoded"):
                    raise ValueError("accepted ACK lacks a successful physical RX attempt")
                if int(attempt["tx_id"]) != int(row["ack_tx_id"]):
                    raise ValueError("ACK provenance TX/RX mismatch")
                if int(attempt["receiver"]) != int(row["receiver"]):
                    raise ValueError("ACK provenance receiver mismatch")

    flow_keys = {(int(row["seed"]), str(row["protocol"]), int(row["flow_id"])) for row in bundle.flows}
    if len(flow_keys) != len(bundle.flows):
        raise ValueError("duplicate flow evidence record")
    expected_flow_count = sum(int(row["scheduled_unicast_flows"]) for row in bundle.runs)
    if len(bundle.flows) != expected_flow_count:
        raise ValueError("scheduled flow denominator is incomplete")
    for run in bundle.runs:
        scoped_count = sum(
            1 for flow in bundle.flows
            if int(flow["seed"]) == int(run["seed"])
            and str(flow["protocol"]) == str(run["protocol"])
        )
        if scoped_count != int(run["scheduled_unicast_flows"]):
            raise ValueError("flow evidence does not match run denominator")


def audit_artifacts(manifest_path: Path) -> Dict[str, Any]:
    """Re-read every artifact, verify hashes/counts, and recompute joins.

    Any missing file, hash mismatch, schema mismatch, or invalid join raises
    ``ValueError``.  The function intentionally does not repair artifacts.
    """

    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        raise ValueError("manifest is missing")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("manifest cannot be read") from exc
    if manifest.get("schema") != SCHEMA:
        raise ValueError("unsupported DRC artifact schema")
    if manifest.get("event_priority") != dict(EVENT_PRIORITY):
        raise ValueError("event-priority contract differs from current simulator")
    expected_source = manifest.get("source_sha256")
    if expected_source != _source_hashes():
        raise ValueError("source hash mismatch; artifact is not reproducible with current code")
    if manifest.get("core_contract_sha256") != _file_sha256(CONTRACT_PATH):
        raise ValueError("runner contract hash mismatch")
    prefix = str(manifest_path)
    if not prefix.endswith(".manifest.json"):
        raise ValueError("manifest filename must end in .manifest.json")
    prefix = Path(prefix[:-len(".manifest.json")])
    paths = _artifact_paths(prefix)
    artifact_details = manifest.get("artifacts")
    if not isinstance(artifact_details, Mapping):
        raise ValueError("manifest artifact table is missing")
    expected_artifacts = set(paths) - {"manifest"}
    if set(artifact_details) != expected_artifacts:
        unknown = sorted(set(artifact_details) - expected_artifacts)
        missing = sorted(expected_artifacts - set(artifact_details))
        if unknown:
            raise ValueError(f"unknown artifact key: {unknown[0]}")
        raise ValueError(f"artifact table is missing: {missing[0]}")

    # Keep only the small CSV summaries. JSONL evidence is counted in a
    # streaming pass and re-read below with bounded-memory join indexes.
    records: Dict[str, List[Dict[str, Any]]] = {}
    for key, details in artifact_details.items():
        if key not in paths:
            raise ValueError(f"unknown artifact key: {key}")
        if not isinstance(details, Mapping):
            raise ValueError(f"artifact metadata is invalid: {key}")
        if not paths[key].exists():
            raise ValueError(f"artifact missing: {key}")
        if _file_sha256(paths[key]) != details.get("sha256"):
            raise ValueError(f"artifact hash mismatch: {key}")
        if key in {"runs", "paired"}:
            with paths[key].open(newline="", encoding="utf-8") as handle:
                records[key] = [dict(row) for row in csv.DictReader(handle)]
            actual_count = len(records[key])
        else:
            actual_count = sum(1 for _ in _iter_jsonl(paths[key]))
        if actual_count != int(details.get("records", -1)):
            raise ValueError(f"artifact record count mismatch: {key}")
    if int(manifest.get("counts", {}).get("invalid_records", -1)) != 0:
        raise ValueError("manifest claims invalid records")
    if int(manifest.get("counts", {}).get("spillover_tx", 0)) != 0 or int(manifest.get("counts", {}).get("incomplete_rx_tx", 0)) != 0:
        raise ValueError("artifact manifest contains an incomplete cutoff TX")
    run_rows = records.get("runs", [])
    if not run_rows:
        raise ValueError("runs artifact is empty")
    scopes: Dict[Tuple[int, str], Dict[str, Any]] = {}
    for row in run_rows:
        try:
            scope = (int(row["seed"]), str(row["protocol"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("runs artifact has an invalid scope") from exc
        if scope in scopes:
            raise ValueError("duplicate seed/arm run record")
        scopes[scope] = row

    case_metadata = manifest.get("case")
    if not isinstance(case_metadata, Mapping) or "nodes" not in case_metadata:
        raise ValueError("manifest case metadata is missing node count")
    try:
        node_count = int(case_metadata["nodes"])
    except (TypeError, ValueError) as exc:
        raise ValueError("manifest case node count is invalid") from exc

    def scope_for(row: Mapping[str, Any], artifact: str) -> Tuple[int, str]:
        try:
            scope = (int(row["seed"]), str(row["protocol"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{artifact} artifact has an invalid scope") from exc
        if scope not in scopes:
            raise ValueError(f"{artifact} artifact references unknown run scope")
        return scope

    started_tx_by_scope: Dict[Tuple[int, str], set[int]] = defaultdict(set)
    for row in _iter_jsonl(paths["requests"]):
        scope = scope_for(row, "requests")
        if row.get("status") != "started" or row.get("tx_id") is None:
            continue
        try:
            tx_id = int(row["tx_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("started request has an invalid tx_id") from exc
        if tx_id in started_tx_by_scope[scope]:
            raise ValueError("started request ledger has duplicate tx_id")
        started_tx_by_scope[scope].add(tx_id)

    tx_ids_by_scope: Dict[Tuple[int, str], set[int]] = defaultdict(set)
    tx_starts_by_scope: Dict[Tuple[int, str], Dict[int, float]] = defaultdict(dict)
    for row in _iter_jsonl(paths["tx"]):
        scope = scope_for(row, "tx")
        try:
            tx_id = int(row["tx_id"])
            start = float(row["start"])
            end = float(row["end"])
            toa = float(row["toa_s"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("transmission artifact has invalid timing or tx_id") from exc
        if tx_id in tx_ids_by_scope[scope]:
            raise ValueError("transmission artifact has duplicate tx_id")
        if abs(toa - (end - start)) > 1e-9:
            raise ValueError("transmission ToA does not recompute")
        tx_ids_by_scope[scope].add(tx_id)
        tx_starts_by_scope[scope][tx_id] = start
    for scope in scopes:
        if started_tx_by_scope.get(scope, set()) != tx_ids_by_scope.get(scope, set()):
            raise ValueError("request/TX join failed in artifacts")

    def truth(value: Any) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes"}
        return bool(value)

    accepted_by_attempt: Dict[Tuple[Tuple[int, str], int], Tuple[int, int]] = {}
    for row in _iter_jsonl(paths["acks"]):
        if not truth(row.get("accepted")):
            continue
        scope = scope_for(row, "acks")
        try:
            attempt_id = int(row["ack_rx_attempt_id"])
            ack_tx_id = int(row["ack_tx_id"])
            receiver = int(row["receiver"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("accepted ACK has incomplete provenance") from exc
        if ack_tx_id not in tx_ids_by_scope.get(scope, set()):
            raise ValueError("accepted ACK references unknown TX")
        key = (scope, attempt_id)
        if key in accepted_by_attempt:
            raise ValueError("duplicate accepted ACK RX attempt reference")
        accepted_by_attempt[key] = (ack_tx_id, receiver)

    allowed_reasons = {"success", "half_duplex", "capture_collision", "prr_fail", "self"}
    rx_count_by_tx: Dict[Tuple[int, str], Counter[int]] = defaultdict(Counter)
    seen_accepted: set[Tuple[Tuple[int, str], int]] = set()
    for row in _iter_jsonl(paths["rx_attempts"]):
        scope = scope_for(row, "rx_attempts")
        try:
            tx_id = int(row["tx_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("RX attempt has an invalid tx_id") from exc
        if tx_id not in tx_ids_by_scope.get(scope, set()):
            raise ValueError("RX references unknown TX in artifacts")
        if row.get("reason") not in allowed_reasons:
            raise ValueError("RX attempt has unknown failure reason")
        rx_count_by_tx[scope][tx_id] += 1
        if row.get("rx_attempt_id") is None:
            continue
        try:
            attempt_id = int(row["rx_attempt_id"])
        except (TypeError, ValueError) as exc:
            raise ValueError("RX attempt has an invalid rx_attempt_id") from exc
        key = (scope, attempt_id)
        expected = accepted_by_attempt.get(key)
        if expected is None:
            continue
        if row.get("reason") != "success" or not truth(row.get("decoded")):
            raise ValueError("accepted ACK lacks physical success in artifacts")
        try:
            receiver = int(row["receiver"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("accepted ACK has invalid receiver provenance") from exc
        if tx_id != expected[0] or receiver != expected[1]:
            raise ValueError("ACK provenance TX/RX mismatch")
        seen_accepted.add(key)

    if set(accepted_by_attempt) != seen_accepted:
        raise ValueError("accepted ACK lacks a physical RX attempt")
    for scope, starts in tx_starts_by_scope.items():
        try:
            cutoff = float(scopes[scope]["drain_until_s"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("run artifact has invalid drain cutoff") from exc
        counts = rx_count_by_tx.get(scope, Counter())
        for tx_id, start in starts.items():
            if start <= cutoff and counts.get(tx_id, 0) != node_count:
                raise ValueError("RX ledger is incomplete for a started TX")
    return manifest


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default="drc_smoke")
    parser.add_argument("--seed", action="append", type=int, dest="seeds")
    parser.add_argument("--protocol", action="append", dest="protocols")
    parser.add_argument("--deadline-s", type=float, default=30.0)
    parser.add_argument("--out-prefix", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.case != "drc_smoke":
        parser.error("only the frozen local drc_smoke case is available")
    args.seeds = tuple(args.seeds or (91000,))
    args.protocols = tuple(args.protocols or DRC_PROTOCOLS)
    return args


def main(argv: Optional[Sequence[str]] = None) -> None:
    args = parse_args(argv)
    bundle = run_matrix(DrcCase(), args.protocols, args.seeds, args.deadline_s, "custom")
    paths = write_artifacts(args.out_prefix, bundle)
    print(paths["manifest"])


if __name__ == "__main__":
    main()
