#!/usr/bin/env python3
"""Deadline-aware, seed-paired experiment harness for MeshEcho-SR."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import (
    BROADCAST_DST,
    Packet,
    PendingSend,
    RxInfo,
    Simulator,
    Transmission,
    build_protocol,
    generate_nodes,
    percentile,
)
from tools.run_fair_multihop_probe import (
    connected_multihop_pairs,
    make_args,
    make_radio,
    paired_mean_ci,
    schedule_probe_traffic,
)


@dataclass(frozen=True)
class SrCase:
    key: str
    nodes: int = 50
    area_m: float = 8250.0
    duration_s: float = 600.0
    rate_per_min: float = 4.0
    traffic: str = "unicast"
    traffic_pattern: str = "standard"
    pair_mode: str = "connected-multihop"
    pair_count: int = 4
    pair_schedule: str = "poisson"
    edge_prr_threshold: float = 0.90
    min_graph_hops: int = 2
    max_graph_hops: int = 4
    sf: int = 7
    bw_hz: int = 125_000
    cr: int = 1
    payload_bytes: int = 32
    tx_power_dbm: float = 17.0
    path_loss_exp: float = 2.75
    shadow_sigma_db: float = 4.0
    temporal_fading_sigma_db: float = 6.0
    temporal_fading_interval_s: float = 60.0
    capture_threshold_db: float = 6.0
    max_hops: int = 6
    route_ttl_s: float = 600.0
    matched_rreq_timing: bool = True


@dataclass(frozen=True)
class SrRun:
    row: Dict[str, Any]
    flows: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]


@dataclass(frozen=True)
class SrExperiment:
    case: SrCase
    protocols: tuple[str, ...]
    seeds: tuple[int, ...]
    deadline_s: float
    rows: List[Dict[str, Any]]
    flows: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    comparisons: List[Dict[str, Any]]
    split: str
    source_sha256: Dict[str, str]


class RecordingSimulator(Simulator):
    """Retain actual transmission starts after the active collision set is pruned."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.tx_history: List[Transmission] = []
        self.ack_expected_decodes: set[int] = set()
        self.first_data_delivery_kind: Dict[int, str] = {}

    def begin_transmission(self, sender: int, packet: Packet, pending: PendingSend) -> None:
        previous_tx_count = self.metrics.tx_count
        super().begin_transmission(sender, packet, pending)
        if self.metrics.tx_count > previous_tx_count:
            self.tx_history.append(self.transmissions[-1])

    def try_receive(self, tx: Transmission, receiver: int) -> RxInfo | None:
        rx = super().try_receive(tx, receiver)
        packet = tx.packet
        if (rx is not None and packet.kind == "ACK"
                and 0 <= packet.path_index < len(packet.path)
                and packet.path[packet.path_index] == receiver):
            self.ack_expected_decodes.add(tx.tx_id)
        return rx

    def mark_delivered(self, flow_id: int, receiver: int, packet: Packet) -> None:
        flow = self.metrics.flows.get(flow_id)
        first_unicast = (flow is not None and flow.dst != BROADCAST_DST
                         and flow.delivered_at is None)
        super().mark_delivered(flow_id, receiver, packet)
        if (first_unicast and flow.delivered_at is not None
                and packet.kind in {"DATA", "FLOOD"}):
            self.first_data_delivery_kind[flow_id] = (
                "R" if packet.kind == "DATA" else "F"
            )


SR_PROTOCOLS = (
    "meshecho-sr",
    "meshecho-sr-fr",
    "meshecho-sr-trigger-f",
    "meshecho-sr-periodic",
)
MAG_PROTOCOLS = (
    "meshecho-mag",
    "meshecho-mag-fr",
    "meshecho-mag-trigger-f",
    "meshecho-mag-periodic",
)
LPR_PROTOCOLS = (
    "meshecho-lpr",
    "meshecho-lpr-fr",
    "meshecho-lpr-trigger-f",
    "meshecho-lpr-periodic",
    "meshecho-lpr-unobserved-edge",
)
DPA_PROTOCOLS = (
    "meshecho-dpa",
    "meshecho-dpa-fr",
    "meshecho-dpa-repeat",
)
RAC_PROTOCOLS = (
    "meshecho-rac",
    "meshecho-rac-repeat",
    "meshecho-rac-fr",
)
CLAR_PROTOCOLS = (
    "meshecho-clar",
    "meshecho-clar-nocancel",
    "meshecho-clar-repeat",
    "meshecho-clar-fr",
)
DHR_PROTOCOLS = (
    "meshecho-dhr",
    "meshecho-dhr-none",
    "meshecho-dhr-repeat",
    "meshecho-dhr-flood",
)
BAR_PROTOCOLS = (
    "meshecho-bar-alternate",
    "meshecho-dhr-flood",
    "meshecho-bar-same",
)
DHR_FAMILY_PROTOCOLS = DHR_PROTOCOLS + (
    BAR_PROTOCOLS[0], BAR_PROTOCOLS[2], "meshecho-dhr-flood-ack-delay",
    "meshecho-dhr-flood-ack-delay-repeat",
    "meshecho-dhr-flood-ack-delay-guard1",
    "meshecho-dhr-flood-ack-delay-guard2",
    "meshecho-dhr-flood-ack-delay-guard4",
    "meshecho-dhr-flood-ack-delay-guard8",
)
LPR_PRIMARY_COMPARATORS = ("meshecho-lpr-fr", "meshecho-lpr-trigger-f")
DPA_PRIMARY_COMPARATORS = ("meshecho-dpa-fr", "meshecho-dpa-repeat")
RAC_PRIMARY_COMPARATORS = ("meshecho-rac-fr", "meshecho-rac-repeat")
CLAR_PRIMARY_COMPARATORS = ("meshecho-clar-fr", "meshecho-clar-repeat")
DHR_PRIMARY_COMPARATORS = ("meshecho-dhr-repeat", "meshecho-dhr-flood")
MAG_PRIMARY_COMPARATORS = ("meshecho-mag-fr", "meshecho-mag-trigger-f")
DEVELOPMENT_SEEDS = tuple(range(3001, 3021))
LPR_DEVELOPMENT_SEEDS = tuple(range(5001, 5021))
DPA_DEVELOPMENT_SEEDS = tuple(range(6001, 6021))
RAC_DEVELOPMENT_SEEDS = tuple(range(7001, 7021))
CLAR_DEVELOPMENT_SEEDS = tuple(range(8001, 8021))
DHR_DEVELOPMENT_SEEDS = tuple(range(9001, 9021))
DHR_HOLDOUT_SEEDS = tuple(range(10001, 10041))
BAR_DEVELOPMENT_SEEDS = tuple(range(16001, 16021))
BAR_HOLDOUT_SEEDS = tuple(range(17001, 17041))
HOLDOUT_SEEDS = tuple(range(4001, 4041))
DBR_RESERVED_SEEDS = frozenset(
    (44200, *range(44001, 44021), *range(44101, 44141))
)
FIRST_HOP_RECEIPT_RESERVED_SEEDS = frozenset(
    (45000, *range(45001, 45021))
)
DESTINATION_BACKUP_RESERVED_SEEDS = frozenset(
    (46000, *range(46001, 46021))
)
DCB_RESERVED_SEEDS = frozenset(
    (47000, *range(47001, 47021), *range(48001, 48041))
)
SOURCE_FILES = (
    ROOT / "lora_mesh_sim.py",
    ROOT / "tools" / "run_fair_multihop_probe.py",
    ROOT / "tools" / "run_sr_experiment.py",
    ROOT / "docs" / "research" / "meshecho_lpr_design.md",
)
DPA_SOURCE_FILES = SOURCE_FILES[:-1] + (
    ROOT / "docs" / "research" / "meshecho_dpa_design.md",
)
RAC_SOURCE_FILES = SOURCE_FILES[:-1] + (
    ROOT / "docs" / "research" / "meshecho_rac_design.md",
)
CLAR_SOURCE_FILES = SOURCE_FILES[:-1] + (
    ROOT / "docs" / "research" / "meshecho_clar_design.md",
)
DHR_SOURCE_FILES = SOURCE_FILES[:-1] + (
    ROOT / "docs" / "research" / "meshecho_dhr_design.md",
)
BAR_SOURCE_FILES = SOURCE_FILES[:-1] + (
    ROOT / "docs" / "research" / "meshecho_bounded_reverse_ack_candidate.md",
    ROOT / "tests" / "test_meshecho_bar.py",
    ROOT / "tests" / "test_sr_experiment.py",
)
SR_CASES = {
    "recurring_fading": SrCase(key="recurring_fading"),
    "recurring_static": SrCase(key="recurring_static", temporal_fading_sigma_db=0.0),
    "random_pairs": SrCase(
        key="random_pairs",
        area_m=18_000.0,
        pair_mode="random",
        pair_count=0,
    ),
    "phase_shift": SrCase(key="phase_shift", traffic_pattern="phase-shift"),
}


def seeds_for_split(split: str) -> tuple[int, ...]:
    if split == "development":
        return DEVELOPMENT_SEEDS
    if split == "lpr-development":
        return LPR_DEVELOPMENT_SEEDS
    if split == "dpa-development":
        return DPA_DEVELOPMENT_SEEDS
    if split == "rac-development":
        return RAC_DEVELOPMENT_SEEDS
    if split == "clar-development":
        return CLAR_DEVELOPMENT_SEEDS
    if split == "dhr-development":
        return DHR_DEVELOPMENT_SEEDS
    if split == "dhr-holdout":
        return DHR_HOLDOUT_SEEDS
    if split == "bar-development":
        return BAR_DEVELOPMENT_SEEDS
    if split == "bar-holdout":
        return BAR_HOLDOUT_SEEDS
    if split == "holdout":
        return HOLDOUT_SEEDS
    if split == "lpr-holdout":
        return HOLDOUT_SEEDS
    if split == "dpa-holdout":
        return HOLDOUT_SEEDS
    if split == "rac-holdout":
        return HOLDOUT_SEEDS
    if split == "clar-holdout":
        return HOLDOUT_SEEDS
    raise ValueError(f"unknown seed split: {split}")


def confirmatory_comparison_eligible(
    split: str, case: str, focus: str, comparator: str,
) -> bool:
    return (
        case == "recurring_fading"
        and (
            (split == "holdout" and focus == "meshecho-mag"
             and comparator in MAG_PRIMARY_COMPARATORS)
            or (split == "lpr-holdout" and focus == "meshecho-lpr"
                and comparator in LPR_PRIMARY_COMPARATORS)
            or (split == "dpa-holdout" and focus == "meshecho-dpa"
                and comparator in DPA_PRIMARY_COMPARATORS)
            or (split == "rac-holdout" and focus == "meshecho-rac"
                and comparator in RAC_PRIMARY_COMPARATORS)
            or (split == "clar-holdout" and focus == "meshecho-clar"
                and comparator in CLAR_PRIMARY_COMPARATORS)
            or (split == "dhr-holdout" and focus == "meshecho-dhr"
                and comparator in DHR_PRIMARY_COMPARATORS)
            or (split == "bar-holdout" and focus == BAR_PROTOCOLS[0]
                and comparator in BAR_PROTOCOLS[1:])
        )
    )


def source_hashes(suite: str = "lpr") -> Dict[str, str]:
    files = {
        "dpa": DPA_SOURCE_FILES,
        "rac": RAC_SOURCE_FILES,
        "clar": CLAR_SOURCE_FILES,
        "dhr": DHR_SOURCE_FILES,
        "bar": BAR_SOURCE_FILES,
    }.get(suite, SOURCE_FILES)
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files
    }


def validate_bar_development_manifest(
    manifest_path: Path, expected_source_hashes: Dict[str, str],
) -> None:
    """Open BAR holdout only after checking its independent development gate."""

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("source_sha256") != expected_source_hashes:
        raise ValueError("BAR development source hash differs from holdout code")
    if (
        manifest.get("case") != asdict(SR_CASES["recurring_fading"])
        or manifest.get("protocols") != list(BAR_PROTOCOLS)
        or manifest.get("seeds") != list(BAR_DEVELOPMENT_SEEDS)
        or manifest.get("seed_split") != "bar-development"
        or manifest.get("application_deadline_s") != 30.0
    ):
        raise ValueError("BAR development manifest differs from frozen configuration")
    if not manifest_path.name.endswith(".manifest.json"):
        raise ValueError("BAR development manifest needs a .manifest.json suffix")
    prefix = manifest_path.with_name(manifest_path.name[:-len(".manifest.json")])
    paths = artifact_paths(prefix)
    artifact_hashes = manifest.get("artifact_sha256")
    if not isinstance(artifact_hashes, dict):
        raise ValueError("BAR development artifact hashes are missing")
    for key in ("runs", "paired", "flows", "actions"):
        artifact = paths[key]
        if (not artifact.is_file()
                or hashlib.sha256(artifact.read_bytes()).hexdigest()
                != artifact_hashes.get(key)):
            raise ValueError(f"BAR development artifact missing or hash mismatch: {key}")

    with paths["runs"].open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    expected_runs = len(BAR_DEVELOPMENT_SEEDS) * len(BAR_PROTOCOLS)
    run_counts = Counter((row.get("seed"), row.get("protocol")) for row in rows)
    if (len(rows) != expected_runs or manifest.get("runs") != expected_runs
            or any(run_counts[(str(seed), protocol)] != 1
                   for seed in BAR_DEVELOPMENT_SEEDS for protocol in BAR_PROTOCOLS)):
        raise ValueError("BAR development runs require three policy rows per seed")
    case_hash = hashlib.sha256(json.dumps(
        asdict(SR_CASES["recurring_fading"]), sort_keys=True, separators=(",", ":")
    ).encode("ascii")).hexdigest()
    traces: Dict[int, tuple[str, int]] = {}
    for row in rows:
        try:
            seed = int(row["seed"])
            scheduled = int(row["scheduled_unicast_flows"])
            valid = (
                row.get("case") == "recurring_fading"
                and row.get("case_config_sha256") == case_hash
                and row.get("seed_split") == "bar-development"
                and float(row["generation_horizon_s"]) == 600.0
                and float(row["drain_until_s"]) == 630.0
                and float(row["application_deadline_s"]) == 30.0
                and scheduled > 0
                and bool(row["scheduled_trace_sha256"])
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("BAR development run row differs from frozen case") from exc
        if not valid:
            raise ValueError("BAR development run row differs from frozen case")
        trace = (row["scheduled_trace_sha256"], scheduled)
        if seed in traces and traces[seed] != trace:
            raise ValueError("BAR development application trace differs across arms")
        traces[seed] = trace

    flow_by_key: Dict[tuple[int, str, int], Dict[str, Any]] = {}
    flow_counts: Counter[tuple[int, str]] = Counter()
    registered_counts: Counter[tuple[int, str]] = Counter()
    ack_counts: Counter[tuple[int, str]] = Counter()
    delivery_counts: Counter[tuple[int, str]] = Counter()
    late_ack_counts: Counter[tuple[int, str]] = Counter()
    late_delivery_counts: Counter[tuple[int, str]] = Counter()
    capped_delays: Dict[tuple[int, str], List[float]] = {}
    schedules: Dict[tuple[int, str], List[tuple[float, int, int, int]]] = {}
    with paths["flows"].open(encoding="utf-8") as handle:
        for line in handle:
            try:
                flow = json.loads(line)
                seed = int(flow["seed"])
                protocol = str(flow["protocol"])
                flow_id = int(flow["flow_id"])
                src = int(flow["src"])
                dst = int(flow["dst"])
                enqueued_at = float(flow["enqueued_at"])
                deadline_at = float(flow["deadline_at"])
                delivered_at = (None if flow["delivered_at"] is None
                                else float(flow["delivered_at"]))
                acked_at = (None if flow["acked_at"] is None
                            else float(flow["acked_at"]))
                capped = float(flow["completion_delay_capped_s"])
                extra_count = int(flow["bar_extra_ack_tx_count"])
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                raise ValueError("BAR development flow evidence is invalid") from exc
            identity = (seed, protocol, flow_id)
            key = (seed, protocol)
            acked = acked_at is not None and acked_at <= deadline_at
            delivered = delivered_at is not None and delivered_at <= deadline_at
            expected_capped = acked_at - enqueued_at if acked else 30.0
            timestamps = (enqueued_at, deadline_at, capped)
            observed_times = [time for time in (delivered_at, acked_at)
                              if time is not None]
            if (
                identity in flow_by_key
                or seed not in BAR_DEVELOPMENT_SEEDS
                or protocol not in BAR_PROTOCOLS
                or flow.get("case") != "recurring_fading"
                or flow.get("seed_split") != "bar-development"
                or flow_id <= 0 or src == dst
                or any(not math.isfinite(time) for time in timestamps + tuple(observed_times))
                or not 0.0 <= enqueued_at < 600.0
                or not math.isclose(deadline_at, enqueued_at + 30.0,
                                    rel_tol=0.0, abs_tol=1e-9)
                or any(time < enqueued_at for time in observed_times)
                or (acked_at is not None and
                    (delivered_at is None or acked_at < delivered_at))
                or flow.get("registered") is not True
                or flow.get("ack_by_deadline") is not acked
                or flow.get("delivery_by_deadline") is not delivered
                or flow.get("late_ack") is not (acked_at is not None and not acked)
                or flow.get("late_delivery") is not
                (delivered_at is not None and not delivered)
                or (delivered_at is not None
                    and flow.get("first_data_delivery_kind") not in {"R", "F"})
                or (delivered_at is None
                    and flow.get("first_data_delivery_kind") is not None)
            ):
                raise ValueError("BAR development flow evidence is invalid")
            if (not math.isclose(capped, expected_capped,
                                 rel_tol=0.0, abs_tol=1e-9)
                    or not 0.0 <= capped <= 30.0
                    or not 0 <= extra_count <= 1
                    or (protocol == BAR_PROTOCOLS[1] and extra_count != 0)):
                raise ValueError("BAR development flow evidence is invalid")
            flow_by_key[identity] = flow
            flow_counts[key] += 1
            registered_counts[key] += 1
            ack_counts[key] += acked
            delivery_counts[key] += delivered
            late_ack_counts[key] += acked_at is not None and not acked
            late_delivery_counts[key] += delivered_at is not None and not delivered
            capped_delays.setdefault(key, []).append(capped)
            schedules.setdefault(key, []).append((enqueued_at, src, dst, flow_id))
    schedule_by_seed: Dict[int, List[tuple[float, int, int, int]]] = {}
    for row in rows:
        key = (int(row["seed"]), row["protocol"])
        schedule = sorted(schedules.get(key, []))
        trace_hash = hashlib.sha256(json.dumps(
            schedule, separators=(",", ":")
        ).encode("ascii")).hexdigest()
        if key[0] in schedule_by_seed and schedule_by_seed[key[0]] != schedule:
            raise ValueError("BAR development flow schedules differ across arms")
        schedule_by_seed[key[0]] = schedule
        try:
            scheduled = int(row["scheduled_unicast_flows"])
            valid = (
                scheduled > 0 and flow_counts[key] == scheduled
                and registered_counts[key] == int(row["registered_unicast_flows"])
                and ack_counts[key] == int(row["ack_by_deadline"])
                and delivery_counts[key] == int(row["delivery_by_deadline"])
                and late_ack_counts[key] == int(row["late_ack_count"])
                and late_delivery_counts[key] == int(row["late_delivery_count"])
                and trace_hash == row["scheduled_trace_sha256"]
                and math.isclose(ack_counts[key] / scheduled,
                                 float(row["ack_pdr_deadline"]),
                                 rel_tol=0.0, abs_tol=1e-10)
                and math.isclose(delivery_counts[key] / scheduled,
                                 float(row["destination_pdr_deadline"]),
                                 rel_tol=0.0, abs_tol=1e-10)
                and math.isclose(statistics.fmean(capped_delays[key]),
                                 float(row["mean_completion_delay_capped_s"]),
                                 rel_tol=0.0, abs_tol=1e-9)
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("BAR development flow evidence differs from runs") from exc
        if not valid:
            raise ValueError("BAR development flow evidence differs from runs")

    comparisons = summarize_paired(rows, BAR_PROTOCOLS[0], BAR_PROTOCOLS[1:])
    if not comparisons or not all(item["bar_joint_primary_gate"] for item in comparisons):
        raise ValueError("BAR development joint primary gate did not pass")
    with paths["paired"].open(newline="", encoding="utf-8") as handle:
        saved_comparisons = list(csv.DictReader(handle))
    expected_by_comparator = {item["comparator"]: item for item in comparisons}
    if (len(saved_comparisons) != 2
            or {item.get("comparator") for item in saved_comparisons}
            != set(BAR_PROTOCOLS[1:])):
        raise ValueError("BAR development paired evidence lacks both controls")
    numeric_fields = (
        "ack_pdr_gain", "ack_pdr_ci95_low", "ack_pdr_ci95_high",
        "destination_pdr_gain", "destination_pdr_ci95_low",
        "destination_pdr_ci95_high", "relative_airtime_cost",
        "relative_airtime_ci95_low", "relative_airtime_ci95_high",
    )
    for saved in saved_comparisons:
        expected = expected_by_comparator[saved["comparator"]]
        if (
            saved.get("case") != "recurring_fading"
            or saved.get("focus_protocol") != BAR_PROTOCOLS[0]
            or saved.get("seed_split") != "bar-development"
            or saved.get("n_seeds") != str(len(BAR_DEVELOPMENT_SEEDS))
            or saved.get("gate_evaluable") != str(expected["gate_evaluable"])
            or saved.get("bar_primary_gate") != str(expected["bar_primary_gate"])
            or saved.get("bar_joint_primary_gate")
            != str(expected["bar_joint_primary_gate"])
        ):
            raise ValueError("BAR development paired evidence differs from runs")
        try:
            match = all(math.isclose(
                float(saved[field]), float(expected[field]),
                rel_tol=1e-10, abs_tol=1e-10,
            ) for field in numeric_fields)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("BAR development paired evidence lacks gate fields") from exc
        if not match:
            raise ValueError("BAR development paired evidence differs from runs")
    with paths["actions"].open(encoding="utf-8") as handle:
        try:
            actions = [json.loads(line) for line in handle]
        except json.JSONDecodeError as exc:
            raise ValueError("BAR development action evidence is invalid") from exc
    first_by_flow: Dict[tuple[int, str, int], Dict[str, Any]] = {}
    candidate_by_flow: Dict[tuple[int, str, int], Dict[str, Any]] = {}
    extra_by_flow: Dict[tuple[int, str, int], Dict[str, Any]] = {}
    action_counts: Counter[tuple[int, str, str]] = Counter()
    for event in actions:
        try:
            seed = int(event["seed"])
            protocol = str(event["protocol"])
            name = str(event["event"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("BAR development action evidence is invalid") from exc
        if (event.get("case") != "recurring_fading"
                or event.get("seed_split") != "bar-development"
                or seed not in BAR_DEVELOPMENT_SEEDS
                or protocol not in BAR_PROTOCOLS):
            raise ValueError("BAR development action evidence is invalid")
        if not name.startswith("bar_"):
            continue
        try:
            flow_id = int(event["flow_id"])
            when = float(event["time"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("BAR development action evidence is invalid") from exc
        identity = (seed, protocol, flow_id)
        flow = flow_by_key.get(identity)
        if (flow is None or protocol == BAR_PROTOCOLS[1]
                or not math.isfinite(when)
                or not isinstance(event["time"], (int, float))
                or not float(flow["enqueued_at"]) <= when <= 630.0
                or name not in {"bar_first_flood_rx", "bar_candidate",
                                "bar_extra_ack_tx"}):
            raise ValueError("BAR development action evidence is invalid")
        action_counts[(seed, protocol, name)] += 1
        if name == "bar_first_flood_rx":
            path = event.get("path")
            if (identity in first_by_flow or not isinstance(path, list)
                    or not 2 <= len(path) <= SR_CASES["recurring_fading"].max_hops + 1
                    or not all(type(node) is int for node in path)
                    or path[0] != flow["src"] or path[-1] != flow["dst"]
                    or len(set(path)) != len(path)
                    or event.get("src") != flow["src"]
                    or event.get("dst") != flow["dst"]
                    or not isinstance(event.get("tracked"), bool)):
                raise ValueError("BAR development first FLOOD evidence is invalid")
            first_by_flow[identity] = event
        elif name == "bar_candidate":
            first = first_by_flow.get(identity)
            alternate = event.get("alternate_path")
            if (identity in candidate_by_flow or first is None
                    or first.get("tracked") is not True
                    or not isinstance(alternate, list)
                    or not 2 <= len(alternate) <= SR_CASES["recurring_fading"].max_hops + 1
                    or not all(type(node) is int for node in alternate)
                    or alternate[0] != flow["src"]
                    or alternate[-1] != flow["dst"]
                    or len(set(alternate)) != len(alternate)
                    or alternate[-2] == first["path"][-2]
                    or event.get("first_path") != first["path"]
                    or event.get("repair_index") != first.get("repair_index")
                    or event.get("src") != flow["src"]
                    or event.get("dst") != flow["dst"]
                    or event.get("mode") != ("alternate" if protocol == BAR_PROTOCOLS[0]
                                             else "same")
                    or event.get("reply_path") != (
                        alternate if protocol == BAR_PROTOCOLS[0] else first["path"]
                    )
                    or not first["time"] <= when <= first["time"] + 1.0 + 1e-9):
                raise ValueError("BAR development candidate evidence is invalid")
            candidate_by_flow[identity] = event
        else:
            first = first_by_flow.get(identity)
            candidate = candidate_by_flow.get(identity)
            if (identity in extra_by_flow or first is None or candidate is None
                    or event.get("mode") != candidate["mode"]
                    or event.get("path") != candidate["reply_path"]
                    or not candidate["time"] <= when <= first["time"] + 1.0 + 1e-9):
                raise ValueError("BAR development extra ACK action is invalid")
            extra_by_flow[identity] = event
    for row in rows:
        try:
            seed = int(row["seed"])
            protocol = row["protocol"]
            extra_count = action_counts[(seed, protocol, "bar_extra_ack_tx")]
            matches = (
                int(row["bar_first_flood_receipts"])
                == action_counts[(seed, protocol, "bar_first_flood_rx")]
                and int(row["bar_candidate_events"])
                == action_counts[(seed, protocol, "bar_candidate")]
                and int(row["bar_extra_ack_tx_events"]) == extra_count
                and extra_count <= int(row["windowed_destination_ack_attempts"])
                <= int(row["windowed_ack_tx"])
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("BAR extra ACK run counts are missing") from exc
        if not matches:
            raise ValueError("BAR extra ACK run counts differ from actions")
    for identity, flow in flow_by_key.items():
        if int(flow["bar_extra_ack_tx_count"]) != int(identity in extra_by_flow):
            raise ValueError("BAR extra ACK flow counts differ from actions")
    extra = [
        event for event in actions
        if event.get("protocol") == BAR_PROTOCOLS[0]
        and event.get("event") == "bar_extra_ack_tx"
    ]
    exposed_seeds = {int(event["seed"]) for event in extra}
    exposure_gate = len(extra) >= 20 and len(exposed_seeds) >= 10
    if (
        manifest.get("bar_joint_primary_gate") is not True
        or manifest.get("bar_extra_ack_tx_events") != len(extra)
        or manifest.get("bar_extra_ack_exposed_seeds") != len(exposed_seeds)
        or manifest.get("bar_exposure_gate") is not exposure_gate
        or manifest.get("bar_project_gate") is not exposure_gate
        or manifest.get("bar_development_open_gate") is not exposure_gate
    ):
        raise ValueError("BAR development manifest gate differs from artifacts")
    if not exposure_gate:
        raise ValueError("BAR development extra ACK exposure gate did not pass")


def validate_lpr_development_manifest(path: Path, expected_source: Dict[str, str]) -> None:
    """Require the frozen LPR development evidence before opening holdout."""

    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("source_sha256") != expected_source:
        raise ValueError("LPR development source hash differs from holdout code")
    if (
        manifest.get("case") != asdict(SR_CASES["recurring_fading"])
        or manifest.get("protocols") != list(LPR_PROTOCOLS)
        or manifest.get("seeds") != list(LPR_DEVELOPMENT_SEEDS)
        or manifest.get("seed_split") != "lpr-development"
        or manifest.get("application_deadline_s") != 30.0
    ):
        raise ValueError("LPR development manifest differs from frozen configuration")
    if not path.name.endswith(".manifest.json"):
        raise ValueError("LPR development artifact manifest needs a .manifest.json suffix")
    prefix = path.with_name(path.name[:-len(".manifest.json")])
    artifact_hashes = manifest.get("artifact_sha256")
    if not isinstance(artifact_hashes, dict):
        raise ValueError("LPR development artifact hashes are missing")
    for key, suffix in (
        ("runs", ".runs.csv"), ("paired", ".paired.csv"),
        ("flows", ".flows.jsonl"), ("actions", ".actions.jsonl"),
    ):
        artifact = Path(f"{prefix}{suffix}")
        if (not artifact.is_file()
                or hashlib.sha256(artifact.read_bytes()).hexdigest()
                != artifact_hashes.get(key)):
            raise ValueError(f"LPR development artifact missing or hash mismatch: {key}")
    runs_path = Path(f"{prefix}.runs.csv")
    with runs_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    expected_count = len(LPR_DEVELOPMENT_SEEDS) * len(LPR_PROTOCOLS)
    counts = Counter((row.get("seed"), row.get("protocol")) for row in rows)
    if (len(rows) != expected_count or manifest.get("runs") != expected_count
            or any(counts[(str(seed), protocol)] != 1
                   for seed in LPR_DEVELOPMENT_SEEDS for protocol in LPR_PROTOCOLS)):
        raise ValueError("LPR development runs require five protocol rows per seed")
    case_hash = hashlib.sha256(json.dumps(
        asdict(SR_CASES["recurring_fading"]), sort_keys=True, separators=(",", ":")
    ).encode("ascii")).hexdigest()
    for row in rows:
        if (row.get("case") != "recurring_fading"
                or row.get("case_config_sha256") != case_hash
                or row.get("seed_split") != "lpr-development"
                or float(row.get("application_deadline_s", "nan")) != 30.0):
            raise ValueError("LPR development run row differs from frozen case config")
    focus_rows = [row for row in rows if row["protocol"] == LPR_PROTOCOLS[0]]
    try:
        repair_counts = [
            (int(row["repair_decisions"]), int(row["ack_confirmed_inserted_repairs"]))
            for row in focus_rows
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("LPR development repair exposure is missing") from exc
    if (any(attempts < 0 or inserts < 0 or inserts > attempts
            for attempts, inserts in repair_counts)
            or sum(attempts for attempts, _ in repair_counts) < 20
            or sum(inserts for _, inserts in repair_counts) < 10):
        raise ValueError("LPR development repair exposure is insufficient")
    try:
        recomputed = summarize_paired(rows, LPR_PROTOCOLS[0], LPR_PROTOCOLS[1:])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("LPR development paired evidence is invalid") from exc
    with Path(f"{prefix}.paired.csv").open(newline="", encoding="utf-8") as handle:
        saved = list(csv.DictReader(handle))
    expected_by_comparator = {item["comparator"]: item for item in recomputed}
    if (len(saved) != len(expected_by_comparator)
            or {item.get("comparator") for item in saved} != set(expected_by_comparator)):
        raise ValueError("LPR development paired evidence lacks four controls")
    numeric_fields = (
        "n_seeds", "ack_pdr_gain", "ack_pdr_ci95_low", "ack_pdr_ci95_high",
        "destination_pdr_gain", "destination_pdr_ci95_low",
        "destination_pdr_ci95_high", "relative_airtime_cost",
        "relative_airtime_ci95_low", "relative_airtime_ci95_high",
    )
    for item in saved:
        expected = expected_by_comparator[item["comparator"]]
        if (item.get("case") != "recurring_fading"
                or item.get("focus_protocol") != LPR_PROTOCOLS[0]
                or item.get("gate_evaluable") != str(expected["gate_evaluable"])
                or item.get("reliability_cost_gate") != str(expected["reliability_cost_gate"])
                or item.get("lpr_joint_primary_gate") != str(expected["lpr_joint_primary_gate"])):
            raise ValueError("LPR development paired evidence differs from runs")
        try:
            fields_match = all(math.isclose(
                float(item[field]), float(expected[field]), rel_tol=1e-10,
                abs_tol=1e-10,
            ) for field in numeric_fields)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("LPR development paired evidence lacks gate fields") from exc
        if not fields_match:
            raise ValueError("LPR development paired evidence differs from runs")
    if not all(expected_by_comparator[name]["reliability_cost_gate"]
               for name in LPR_PRIMARY_COMPARATORS):
        raise ValueError("LPR development joint primary gate did not pass")


def validate_dpa_development_manifest(path: Path, expected_source: Dict[str, str]) -> None:
    """Require frozen DPA development evidence before opening holdout."""

    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("source_sha256") != expected_source:
        raise ValueError("DPA development source hash differs from holdout code")
    if (
        manifest.get("case") != asdict(SR_CASES["recurring_fading"])
        or manifest.get("protocols") != list(DPA_PROTOCOLS)
        or manifest.get("seeds") != list(DPA_DEVELOPMENT_SEEDS)
        or manifest.get("seed_split") != "dpa-development"
        or manifest.get("application_deadline_s") != 30.0
    ):
        raise ValueError("DPA development manifest differs from frozen configuration")
    if not path.name.endswith(".manifest.json"):
        raise ValueError("DPA development artifact manifest needs a .manifest.json suffix")
    prefix = path.with_name(path.name[:-len(".manifest.json")])
    artifact_hashes = manifest.get("artifact_sha256")
    if not isinstance(artifact_hashes, dict):
        raise ValueError("DPA development artifact hashes are missing")
    for key, suffix in (
        ("runs", ".runs.csv"), ("paired", ".paired.csv"),
        ("flows", ".flows.jsonl"), ("actions", ".actions.jsonl"),
    ):
        artifact = Path(f"{prefix}{suffix}")
        if (not artifact.is_file()
                or hashlib.sha256(artifact.read_bytes()).hexdigest()
                != artifact_hashes.get(key)):
            raise ValueError(f"DPA development artifact missing or hash mismatch: {key}")
    with Path(f"{prefix}.runs.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    expected_count = len(DPA_DEVELOPMENT_SEEDS) * len(DPA_PROTOCOLS)
    counts = Counter((row.get("seed"), row.get("protocol")) for row in rows)
    if (len(rows) != expected_count or manifest.get("runs") != expected_count
            or any(counts[(str(seed), protocol)] != 1
                   for seed in DPA_DEVELOPMENT_SEEDS for protocol in DPA_PROTOCOLS)):
        raise ValueError("DPA development runs require three protocol rows per seed")
    case_hash = hashlib.sha256(json.dumps(
        asdict(SR_CASES["recurring_fading"]), sort_keys=True, separators=(",", ":")
    ).encode("ascii")).hexdigest()
    for row in rows:
        if (row.get("case") != "recurring_fading"
                or row.get("case_config_sha256") != case_hash
                or row.get("seed_split") != "dpa-development"
                or float(row.get("application_deadline_s", "nan")) != 30.0):
            raise ValueError("DPA development run row differs from frozen case config")
    flow_counts: Counter[tuple[int, str]] = Counter()
    ack_counts: Counter[tuple[int, str]] = Counter()
    delivery_counts: Counter[tuple[int, str]] = Counter()
    seen_flows: set[tuple[int, str, int]] = set()
    with Path(f"{prefix}.flows.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            flow = json.loads(line)
            try:
                seed = int(flow["seed"])
                protocol = str(flow["protocol"])
                flow_id = int(flow["flow_id"])
                acked = flow["ack_by_deadline"]
                delivered = flow["delivery_by_deadline"]
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("DPA development flow evidence is invalid") from exc
            identity = (seed, protocol, flow_id)
            if (flow.get("case") != "recurring_fading"
                    or flow.get("seed_split") != "dpa-development"
                    or seed not in DPA_DEVELOPMENT_SEEDS
                    or protocol not in DPA_PROTOCOLS
                    or identity in seen_flows
                    or not isinstance(acked, bool)
                    or not isinstance(delivered, bool)):
                raise ValueError("DPA development flow evidence is invalid")
            seen_flows.add(identity)
            flow_counts[(seed, protocol)] += 1
            ack_counts[(seed, protocol)] += acked
            delivery_counts[(seed, protocol)] += delivered
    for row in rows:
        key = (int(row["seed"]), row["protocol"])
        try:
            expected_flows = int(row["scheduled_unicast_flows"])
            expected_acks = int(row["ack_by_deadline"])
            expected_deliveries = int(row["delivery_by_deadline"])
            matches_pdr = (
                math.isclose(expected_acks / expected_flows,
                             float(row["ack_pdr_deadline"]), abs_tol=1e-10)
                and math.isclose(expected_deliveries / expected_flows,
                                 float(row["destination_pdr_deadline"]), abs_tol=1e-10)
            )
        except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
            raise ValueError("DPA development flow evidence is invalid") from exc
        if (expected_flows <= 0 or flow_counts[key] != expected_flows
                or ack_counts[key] != expected_acks
                or delivery_counts[key] != expected_deliveries
                or not matches_pdr):
            raise ValueError("DPA development flow evidence differs from runs")
    try:
        opportunities = [
            int(row["dpa_second_path_opportunities"])
            for row in rows if row["protocol"] == DPA_PROTOCOLS[0]
        ]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("DPA development second-path exposure is missing") from exc
    if (any(count < 0 for count in opportunities)
            or sum(opportunities) < 20
            or sum(count > 0 for count in opportunities) < 10):
        raise ValueError("DPA development second-path exposure is insufficient")
    logged_opportunities: Counter[int] = Counter()
    seen_opportunities: set[tuple[int, int]] = set()
    with Path(f"{prefix}.actions.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            event = json.loads(line)
            if (event.get("protocol") != DPA_PROTOCOLS[0]
                    or event.get("event") != "dpa_second_path"):
                continue
            try:
                seed = int(event["seed"])
                flow_id = int(event["flow_id"])
                src = int(event["src"])
                dst = int(event["dst"])
                first = event["first_path"]
                second = event["second_path"]
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("DPA development second-path action is invalid") from exc
            identity = (seed, flow_id)
            if (
                event.get("case") != "recurring_fading"
                or event.get("seed_split") != "dpa-development"
                or event.get("action") != "F"
                or seed not in DPA_DEVELOPMENT_SEEDS
                or identity in seen_opportunities
                or not isinstance(first, list)
                or not isinstance(second, list)
                or not all(isinstance(node, int) for node in first + second)
                or not (2 <= len(first) <= SR_CASES["recurring_fading"].max_hops + 1)
                or not (2 <= len(second) <= SR_CASES["recurring_fading"].max_hops + 1)
                or first[0] != src or second[0] != src
                or first[-1] != dst or second[-1] != dst
                or len(first) != len(set(first))
                or len(second) != len(set(second))
                or first[1] == second[1]
            ):
                raise ValueError("DPA development second-path action is invalid")
            seen_opportunities.add(identity)
            logged_opportunities[seed] += 1
    expected_opportunities = {
        int(row["seed"]): int(row["dpa_second_path_opportunities"])
        for row in rows if row["protocol"] == DPA_PROTOCOLS[0]
    }
    if any(logged_opportunities[seed] != expected
           for seed, expected in expected_opportunities.items()):
        raise ValueError("DPA development exposure differs from action log")
    try:
        recomputed = summarize_paired(rows, DPA_PROTOCOLS[0], DPA_PROTOCOLS[1:])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("DPA development paired evidence is invalid") from exc
    with Path(f"{prefix}.paired.csv").open(newline="", encoding="utf-8") as handle:
        saved = list(csv.DictReader(handle))
    expected_by_comparator = {item["comparator"]: item for item in recomputed}
    if (len(saved) != len(expected_by_comparator)
            or {item.get("comparator") for item in saved} != set(expected_by_comparator)):
        raise ValueError("DPA development paired evidence lacks both controls")
    numeric_fields = (
        "n_seeds", "ack_pdr_gain", "ack_pdr_ci95_low", "ack_pdr_ci95_high",
        "destination_pdr_gain", "destination_pdr_ci95_low",
        "destination_pdr_ci95_high", "relative_airtime_cost",
        "relative_airtime_ci95_low", "relative_airtime_ci95_high",
    )
    for item in saved:
        expected = expected_by_comparator[item["comparator"]]
        if (item.get("case") != "recurring_fading"
                or item.get("focus_protocol") != DPA_PROTOCOLS[0]
                or item.get("gate_evaluable") != str(expected["gate_evaluable"])
                or item.get("reliability_cost_gate") != str(expected["reliability_cost_gate"])
                or item.get("dpa_joint_primary_gate") != str(expected["dpa_joint_primary_gate"])):
            raise ValueError("DPA development paired evidence differs from runs")
        try:
            fields_match = all(math.isclose(
                float(item[field]), float(expected[field]), rel_tol=1e-10,
                abs_tol=1e-10,
            ) for field in numeric_fields)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("DPA development paired evidence lacks gate fields") from exc
        if not fields_match:
            raise ValueError("DPA development paired evidence differs from runs")
    joint_gate = all(expected_by_comparator[name]["reliability_cost_gate"]
                     for name in DPA_PRIMARY_COMPARATORS)
    if manifest.get("dpa_joint_primary_gate") is not joint_gate:
        raise ValueError("DPA development manifest joint primary gate differs from runs")
    if not joint_gate:
        raise ValueError("DPA development joint primary gate did not pass")


def validate_rac_development_manifest(path: Path, expected_source: Dict[str, str]) -> None:
    """Require frozen RAC development evidence before opening holdout."""

    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("source_sha256") != expected_source:
        raise ValueError("RAC development source hash differs from holdout code")
    if (
        manifest.get("case") != asdict(SR_CASES["recurring_fading"])
        or manifest.get("protocols") != list(RAC_PROTOCOLS)
        or manifest.get("seeds") != list(RAC_DEVELOPMENT_SEEDS)
        or manifest.get("seed_split") != "rac-development"
        or manifest.get("application_deadline_s") != 30.0
    ):
        raise ValueError("RAC development manifest differs from frozen configuration")
    if not path.name.endswith(".manifest.json"):
        raise ValueError("RAC development artifact manifest needs a .manifest.json suffix")
    prefix = path.with_name(path.name[:-len(".manifest.json")])
    artifact_hashes = manifest.get("artifact_sha256")
    if not isinstance(artifact_hashes, dict):
        raise ValueError("RAC development artifact hashes are missing")
    for key, suffix in (
        ("runs", ".runs.csv"), ("paired", ".paired.csv"),
        ("flows", ".flows.jsonl"), ("actions", ".actions.jsonl"),
    ):
        artifact = Path(f"{prefix}{suffix}")
        if (not artifact.is_file()
                or hashlib.sha256(artifact.read_bytes()).hexdigest()
                != artifact_hashes.get(key)):
            raise ValueError(f"RAC development artifact missing or hash mismatch: {key}")
    with Path(f"{prefix}.runs.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    expected_count = len(RAC_DEVELOPMENT_SEEDS) * len(RAC_PROTOCOLS)
    counts = Counter((row.get("seed"), row.get("protocol")) for row in rows)
    if (len(rows) != expected_count or manifest.get("runs") != expected_count
            or any(counts[(str(seed), protocol)] != 1
                   for seed in RAC_DEVELOPMENT_SEEDS for protocol in RAC_PROTOCOLS)):
        raise ValueError("RAC development runs require three policy rows per seed")
    case_hash = hashlib.sha256(json.dumps(
        asdict(SR_CASES["recurring_fading"]), sort_keys=True, separators=(",", ":")
    ).encode("ascii")).hexdigest()
    for row in rows:
        if (row.get("case") != "recurring_fading"
                or row.get("case_config_sha256") != case_hash
                or row.get("seed_split") != "rac-development"
                or float(row.get("application_deadline_s", "nan")) != 30.0):
            raise ValueError("RAC development run row differs from frozen case config")
    flow_counts: Counter[tuple[int, str]] = Counter()
    ack_counts: Counter[tuple[int, str]] = Counter()
    delivery_counts: Counter[tuple[int, str]] = Counter()
    flow_by_key: Dict[tuple[int, str, int], Dict[str, Any]] = {}
    with Path(f"{prefix}.flows.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            try:
                flow = json.loads(line)
                seed = int(flow["seed"])
                protocol = str(flow["protocol"])
                flow_id = int(flow["flow_id"])
                acked = flow["ack_by_deadline"]
                delivered = flow["delivery_by_deadline"]
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("RAC development flow evidence is invalid") from exc
            identity = (seed, protocol, flow_id)
            if (flow.get("case") != "recurring_fading"
                    or flow.get("seed_split") != "rac-development"
                    or seed not in RAC_DEVELOPMENT_SEEDS
                    or protocol not in RAC_PROTOCOLS
                    or identity in flow_by_key
                    or not isinstance(acked, bool)
                    or not isinstance(delivered, bool)):
                raise ValueError("RAC development flow evidence is invalid")
            flow_by_key[identity] = flow
            flow_counts[(seed, protocol)] += 1
            ack_counts[(seed, protocol)] += acked
            delivery_counts[(seed, protocol)] += delivered
    for row in rows:
        key = (int(row["seed"]), row["protocol"])
        try:
            expected_flows = int(row["scheduled_unicast_flows"])
            expected_acks = int(row["ack_by_deadline"])
            expected_deliveries = int(row["delivery_by_deadline"])
            matches_pdr = (
                math.isclose(expected_acks / expected_flows,
                             float(row["ack_pdr_deadline"]), abs_tol=1e-10)
                and math.isclose(expected_deliveries / expected_flows,
                                 float(row["destination_pdr_deadline"]), abs_tol=1e-10)
            )
        except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
            raise ValueError("RAC development flow evidence is invalid") from exc
        if (expected_flows <= 0 or flow_counts[key] != expected_flows
                or ack_counts[key] != expected_acks
                or delivery_counts[key] != expected_deliveries
                or not matches_pdr):
            raise ValueError("RAC development flow evidence differs from runs")
    exposure_by_seed: Counter[int] = Counter()
    seen_exposure: set[tuple[int, str, int, int, int, tuple[int, ...]]] = set()
    with Path(f"{prefix}.actions.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            try:
                event = json.loads(line)
            except (TypeError, ValueError) as exc:
                raise ValueError("RAC development action evidence is invalid") from exc
            if (event.get("protocol") != RAC_PROTOCOLS[0]
                    or event.get("event") != "rac_corridor_eligible"):
                continue
            try:
                seed = int(event["seed"])
                flow_id = int(event["flow_id"])
                src = int(event["src"])
                dst = int(event["dst"])
                candidate = int(event["candidate"])
                next_hop = int(event["next_hop"])
                path_nodes = event["path"]
                when = float(event["time"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("RAC development corridor action is invalid") from exc
            flow = flow_by_key.get((seed, RAC_PROTOCOLS[0], flow_id))
            if flow is None:
                raise ValueError("RAC development corridor action is invalid")
            try:
                enqueued_at = float(flow["enqueued_at"])
                deadline_at = float(flow["deadline_at"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("RAC development corridor action is invalid") from exc
            if (event.get("case") != "recurring_fading"
                    or event.get("seed_split") != "rac-development"
                    or event.get("action") != "F"
                    or seed not in RAC_DEVELOPMENT_SEEDS
                    or src != flow.get("src") or dst != flow.get("dst")
                    or flow.get("source_action") != "F"
                    or flow.get("delivery_by_deadline") is not True
                    or not math.isfinite(enqueued_at)
                    or not math.isfinite(deadline_at)
                    or not math.isclose(deadline_at - enqueued_at, 30.0,
                                        rel_tol=0.0, abs_tol=1e-9)
                    or not enqueued_at <= when < deadline_at
                    or not isinstance(path_nodes, list)
                    or not all(isinstance(node, int) for node in path_nodes)
                    or not 2 <= len(path_nodes) <= SR_CASES["recurring_fading"].max_hops + 1
                    or path_nodes[0] != src or path_nodes[-1] != dst
                    or len(path_nodes) != len(set(path_nodes))
                    or candidate in path_nodes or next_hop not in path_nodes
                    or not math.isfinite(when)):
                raise ValueError("RAC development corridor action is invalid")
            identity = (seed, flow_id, candidate, next_hop, tuple(path_nodes))
            if identity in seen_exposure:
                raise ValueError("RAC development duplicate corridor exposure")
            seen_exposure.add(identity)
            exposure_by_seed[seed] += 1
    expected_exposure = {
        int(row["seed"]): int(row["rac_corridor_eligible"])
        for row in rows if row["protocol"] == RAC_PROTOCOLS[0]
    }
    if (any(count < 0 for count in expected_exposure.values())
            or any(exposure_by_seed[seed] != expected
                   for seed, expected in expected_exposure.items())
            or manifest.get("rac_corridor_eligible_events") != sum(exposure_by_seed.values())
            or manifest.get("rac_corridor_exposed_seeds") != len(exposure_by_seed)):
        raise ValueError("RAC development exposure differs from action log")
    if (sum(exposure_by_seed.values()) < 20 or len(exposure_by_seed) < 10
            or manifest.get("rac_exposure_gate") is not True):
        raise ValueError("RAC development corridor exposure is insufficient")
    try:
        recomputed = summarize_paired(rows, RAC_PROTOCOLS[0], RAC_PROTOCOLS[1:])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("RAC development paired trace or config evidence is invalid") from exc
    with Path(f"{prefix}.paired.csv").open(newline="", encoding="utf-8") as handle:
        saved = list(csv.DictReader(handle))
    expected_by_comparator = {item["comparator"]: item for item in recomputed}
    if (len(saved) != len(RAC_PRIMARY_COMPARATORS)
            or {item.get("comparator") for item in saved}
            != set(RAC_PRIMARY_COMPARATORS)):
        raise ValueError("RAC development paired evidence lacks both controls")
    numeric_fields = (
        "n_seeds", "ack_pdr_gain", "ack_pdr_ci95_low", "ack_pdr_ci95_high",
        "destination_pdr_gain", "destination_pdr_ci95_low",
        "destination_pdr_ci95_high", "relative_airtime_cost",
        "relative_airtime_ci95_low", "relative_airtime_ci95_high",
    )
    for item in saved:
        expected = expected_by_comparator[item["comparator"]]
        if (item.get("case") != "recurring_fading"
                or item.get("focus_protocol") != RAC_PROTOCOLS[0]
                or item.get("seed_split") != "rac-development"
                or item.get("gate_evaluable") != str(expected["gate_evaluable"])
                or item.get("reliability_cost_gate")
                != str(expected["reliability_cost_gate"])
                or item.get("rac_joint_primary_gate")
                != str(expected["rac_joint_primary_gate"])):
            raise ValueError("RAC development paired evidence differs from runs")
        try:
            fields_match = all(math.isclose(
                float(item[field]), float(expected[field]), rel_tol=1e-10,
                abs_tol=1e-10,
            ) for field in numeric_fields)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("RAC development paired evidence lacks gate fields") from exc
        if not fields_match:
            raise ValueError("RAC development paired evidence differs from runs")
    joint_gate = all(expected_by_comparator[name]["reliability_cost_gate"]
                     for name in RAC_PRIMARY_COMPARATORS)
    if manifest.get("rac_joint_primary_gate") is not joint_gate:
        raise ValueError("RAC development manifest joint primary gate differs from runs")
    if not joint_gate:
        raise ValueError("RAC development joint primary gate did not pass")


def validate_clar_development_manifest(path: Path, expected_source: Dict[str, str]) -> None:
    """Require unchanged, frozen CLAR development evidence before holdout."""

    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("source_sha256") != expected_source:
        raise ValueError("CLAR development source hash differs from holdout code")
    if (
        manifest.get("case") != asdict(SR_CASES["recurring_fading"])
        or manifest.get("protocols") != list(CLAR_PROTOCOLS)
        or manifest.get("seeds") != list(CLAR_DEVELOPMENT_SEEDS)
        or manifest.get("seed_split") != "clar-development"
        or manifest.get("application_deadline_s") != 30.0
    ):
        raise ValueError("CLAR development manifest differs from frozen configuration")
    if not path.name.endswith(".manifest.json"):
        raise ValueError("CLAR development artifact manifest needs a .manifest.json suffix")
    prefix = path.with_name(path.name[:-len(".manifest.json")])
    artifact_hashes = manifest.get("artifact_sha256")
    if not isinstance(artifact_hashes, dict):
        raise ValueError("CLAR development artifact hashes are missing")
    for key, suffix in (
        ("runs", ".runs.csv"), ("paired", ".paired.csv"),
        ("flows", ".flows.jsonl"), ("actions", ".actions.jsonl"),
    ):
        artifact = Path(f"{prefix}{suffix}")
        if (not artifact.is_file()
                or hashlib.sha256(artifact.read_bytes()).hexdigest()
                != artifact_hashes.get(key)):
            raise ValueError(f"CLAR development artifact missing or hash mismatch: {key}")
    with Path(f"{prefix}.runs.csv").open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    expected_count = len(CLAR_DEVELOPMENT_SEEDS) * len(CLAR_PROTOCOLS)
    counts = Counter((row.get("seed"), row.get("protocol")) for row in rows)
    if (len(rows) != expected_count or manifest.get("runs") != expected_count
            or any(counts[(str(seed), protocol)] != 1
                   for seed in CLAR_DEVELOPMENT_SEEDS for protocol in CLAR_PROTOCOLS)):
        raise ValueError("CLAR development runs require four policy rows per seed")
    case_hash = hashlib.sha256(json.dumps(
        asdict(SR_CASES["recurring_fading"]), sort_keys=True, separators=(",", ":")
    ).encode("ascii")).hexdigest()
    for row in rows:
        try:
            valid = (
                row.get("case") == "recurring_fading"
                and row.get("case_config_sha256") == case_hash
                and row.get("seed_split") == "clar-development"
                and float(row.get("generation_horizon_s", "nan")) == 600.0
                and float(row.get("drain_until_s", "nan")) == 630.0
                and float(row.get("application_deadline_s", "nan")) == 30.0
                and int(row["scheduled_unicast_flows"]) > 0
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("CLAR development run row differs from frozen case config") from exc
        if not valid:
            raise ValueError("CLAR development run row differs from frozen case config")
    flow_counts: Counter[tuple[int, str]] = Counter()
    ack_counts: Counter[tuple[int, str]] = Counter()
    delivery_counts: Counter[tuple[int, str]] = Counter()
    flow_by_key: Dict[tuple[int, str, int], Dict[str, Any]] = {}
    with Path(f"{prefix}.flows.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            try:
                flow = json.loads(line)
                seed = int(flow["seed"])
                protocol = str(flow["protocol"])
                flow_id = int(flow["flow_id"])
                src = int(flow["src"])
                dst = int(flow["dst"])
                enqueued_at = float(flow["enqueued_at"])
                deadline_at = float(flow["deadline_at"])
                acked = flow["ack_by_deadline"]
                delivered = flow["delivery_by_deadline"]
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("CLAR development flow evidence is invalid") from exc
            identity = (seed, protocol, flow_id)
            if (flow.get("case") != "recurring_fading"
                    or flow.get("seed_split") != "clar-development"
                    or seed not in CLAR_DEVELOPMENT_SEEDS
                    or protocol not in CLAR_PROTOCOLS
                    or identity in flow_by_key
                    or not isinstance(acked, bool)
                    or not isinstance(delivered, bool)
                    or acked and not delivered
                    or flow.get("source_action") not in {"F", "R"}
                    or src == dst or not 0 <= src < SR_CASES["recurring_fading"].nodes
                    or not 0 <= dst < SR_CASES["recurring_fading"].nodes
                    or not math.isfinite(enqueued_at)
                    or not 0.0 <= enqueued_at < 600.0
                    or not math.isfinite(deadline_at)
                    or not math.isclose(deadline_at - enqueued_at, 30.0,
                                        rel_tol=0.0, abs_tol=1e-9)):
                raise ValueError("CLAR development flow evidence is invalid")
            flow_by_key[identity] = flow
            flow_counts[(seed, protocol)] += 1
            ack_counts[(seed, protocol)] += acked
            delivery_counts[(seed, protocol)] += delivered
    for row in rows:
        key = (int(row["seed"]), row["protocol"])
        try:
            scheduled = int(row["scheduled_unicast_flows"])
            acked = int(row["ack_by_deadline"])
            delivered = int(row["delivery_by_deadline"])
            valid = (
                scheduled > 0
                and 0 <= acked <= delivered <= scheduled
                and flow_counts[key] == scheduled
                and ack_counts[key] == acked
                and delivery_counts[key] == delivered
                and math.isclose(acked / scheduled, float(row["ack_pdr_deadline"]),
                                 rel_tol=0.0, abs_tol=1e-10)
                and math.isclose(delivered / scheduled,
                                 float(row["destination_pdr_deadline"]),
                                 rel_tol=0.0, abs_tol=1e-10)
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("CLAR development flow evidence differs from runs") from exc
        if not valid:
            raise ValueError("CLAR development flow evidence differs from runs")
    event_metrics = {
        "clar_candidate_eligible": "clar_candidate_eligible",
        "clar_cancel": "clar_cancellations",
        "clar_done_tx": "clar_done_tx_events",
        "clar_done_rx": "clar_done_rx_events",
        "clar_repair_tx": "clar_repair_tx_events",
        "clar_repeat_tx": "clar_repeat_tx_events",
    }
    action_counts: Counter[tuple[int, str, str]] = Counter()
    windowed_tx_actions: Counter[tuple[int, str, str]] = Counter()
    cancellation_reasons: Counter[tuple[int, str, str]] = Counter()
    accepted_counts: Counter[tuple[int, str]] = Counter()
    accepted_by_flow: Dict[tuple[int, str, int], tuple[int, float]] = {}
    exposure_by_seed: Counter[int] = Counter()
    seen_exposure: set[tuple[int, int, int, int, tuple[int, ...]]] = set()
    done_cancels = 0
    continuation_cancels = 0
    with Path(f"{prefix}.actions.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            try:
                event = json.loads(line)
                seed = int(event["seed"])
                protocol = str(event["protocol"])
                name = str(event["event"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("CLAR development action evidence is invalid") from exc
            if (event.get("case") != "recurring_fading"
                    or event.get("seed_split") != "clar-development"
                    or seed not in CLAR_DEVELOPMENT_SEEDS
                    or protocol not in CLAR_PROTOCOLS):
                raise ValueError("CLAR development action evidence is invalid")
            if not name.startswith("clar_"):
                continue
            try:
                flow_id = int(event["flow_id"])
                src = int(event["src"])
                dst = int(event["dst"])
                when = float(event["time"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("CLAR development action evidence is invalid") from exc
            flow = flow_by_key.get((seed, protocol, flow_id))
            is_tx_action = name in {
                "clar_done_tx", "clar_repair_tx", "clar_repeat_tx",
            }
            if (flow is None or src != flow["src"] or dst != flow["dst"]
                    or not math.isfinite(when)
                    or when < float(flow["enqueued_at"])
                    or (when > 630.0 and not is_tx_action)):
                raise ValueError("CLAR development action evidence is invalid")
            action_counts[(seed, protocol, name)] += 1
            if is_tx_action and when <= 630.0:
                windowed_tx_actions[(seed, protocol, name)] += 1
            if name == "clar_source_ack_rx" and event.get("accepted") is True:
                try:
                    marker = int(event["repair_index"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ValueError("CLAR development F ACK stage is invalid") from exc
                if (flow.get("source_action") != "F"
                        or flow.get("ack_by_deadline") is not True
                        or event.get("action") != "F"
                        or marker not in {0, 1, 255}
                        or when > float(flow["deadline_at"])
                        or (seed, protocol, flow_id) in accepted_by_flow):
                    raise ValueError("CLAR development F ACK stage is invalid")
                accepted_by_flow[(seed, protocol, flow_id)] = (marker, when)
                accepted_counts[(seed, protocol)] += 1
            if name == "clar_cancel" and protocol == CLAR_PROTOCOLS[0]:
                if event.get("reason") == "source-done":
                    done_cancels += 1
                elif event.get("reason") == "ack-continuation":
                    continuation_cancels += 1
            if name == "clar_cancel":
                reason = event.get("reason")
                if reason not in {"source-done", "source-done-repeat",
                                  "ack-continuation", "ack-continuation-repeat"}:
                    raise ValueError("CLAR development cancellation reason is invalid")
                cancellation_reasons[(seed, protocol, reason)] += 1
            if name != "clar_candidate_eligible":
                continue
            try:
                candidate = int(event["candidate"])
                next_hop = int(event["next_hop"])
                path_nodes = event["path"]
                valid_exposure = (
                    protocol in CLAR_PROTOCOLS[:2]
                    and event.get("action") == "F"
                    and flow["source_action"] == "F"
                    and flow.get("delivered_at") is not None
                    and isinstance(path_nodes, list)
                    and all(isinstance(node, int) for node in path_nodes)
                    and 2 <= len(path_nodes) <= SR_CASES["recurring_fading"].max_hops + 1
                    and path_nodes[0] == src and path_nodes[-1] == dst
                    and len(path_nodes) == len(set(path_nodes))
                    and candidate not in path_nodes
                    and next_hop in path_nodes[:-1]
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("CLAR development candidate action is invalid") from exc
            if not valid_exposure:
                raise ValueError("CLAR development candidate action is invalid")
            identity = (seed, protocol, flow_id, candidate, next_hop,
                        tuple(path_nodes))
            if identity in seen_exposure:
                raise ValueError("CLAR development duplicate candidate exposure")
            seen_exposure.add(identity)
            if protocol == CLAR_PROTOCOLS[0]:
                exposure_by_seed[seed] += 1
    for row in rows:
        key = (int(row["seed"]), row["protocol"])
        try:
            valid_counts = all(
                int(row[column]) == action_counts[key + (event_name,)]
                for event_name, column in event_metrics.items()
            )
            valid_counts = valid_counts and (
                int(row["clar_source_ack_accepted"]) == accepted_counts[key]
                and int(row["clar_done_cancellations"])
                    == cancellation_reasons[key + ("source-done",)]
                and int(row["clar_continuation_cancellations"])
                    == cancellation_reasons[key + ("ack-continuation",)]
                    + cancellation_reasons[key + ("ack-continuation-repeat",)]
                and int(row["windowed_done_tx"])
                    == windowed_tx_actions[key + ("clar_done_tx",)]
                and int(row["windowed_done_bytes"])
                    == 10 * windowed_tx_actions[key + ("clar_done_tx",)]
                and int(row["windowed_control_bytes"])
                    >= int(row["windowed_ack_bytes"]) + int(row["windowed_done_bytes"])
                and int(row["windowed_control_tx"])
                    >= int(row["windowed_ack_tx"]) + int(row["windowed_done_tx"])
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("CLAR development action counts differ from runs") from exc
        if not valid_counts:
            raise ValueError("CLAR development exposure differs from action log")
    stages = {255: "initial", 0: "repair", 1: "repeat"}
    for identity, flow in flow_by_key.items():
        if flow["source_action"] != "F":
            continue
        accepted = accepted_by_flow.get(identity)
        marker = accepted[0] if accepted is not None else None
        stage = (
            stages[marker] if marker is not None else
            "destination_only" if flow["delivery_by_deadline"] else "not_delivered"
        )
        acked_at = flow.get("acked_at")
        if (flow.get("f_ack_repair_index") != marker
                or flow.get("f_ack_stage") != stage
                or bool(accepted) != flow["ack_by_deadline"]
                or (accepted is not None and (
                    acked_at is None
                    or not math.isclose(float(acked_at), accepted[1],
                                        rel_tol=0.0, abs_tol=1e-9)
                ))):
            raise ValueError("CLAR development F ACK stage differs from acceptance")
    if (manifest.get("clar_candidate_eligible_events") != sum(exposure_by_seed.values())
            or manifest.get("clar_candidate_exposed_seeds") != len(exposure_by_seed)
            or manifest.get("clar_done_cancel_events") != done_cancels
            or manifest.get("clar_ack_continuation_cancel_events")
            != continuation_cancels):
        raise ValueError("CLAR development exposure differs from action log")
    if (sum(exposure_by_seed.values()) < 20 or len(exposure_by_seed) < 10
            or manifest.get("clar_exposure_gate") is not True):
        raise ValueError("CLAR development candidate exposure is insufficient")
    try:
        recomputed = summarize_paired(rows, CLAR_PROTOCOLS[0], CLAR_PROTOCOLS[1:])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("CLAR development paired trace or config evidence is invalid") from exc
    with Path(f"{prefix}.paired.csv").open(newline="", encoding="utf-8") as handle:
        saved = list(csv.DictReader(handle))
    expected_by_comparator = {item["comparator"]: item for item in recomputed}
    if (len(saved) != len(CLAR_PROTOCOLS) - 1
            or {item.get("comparator") for item in saved}
            != set(CLAR_PROTOCOLS[1:])):
        raise ValueError("CLAR development paired evidence lacks three controls")
    numeric_fields = (
        "n_seeds", "ack_pdr_gain", "ack_pdr_ci95_low", "ack_pdr_ci95_high",
        "destination_pdr_gain", "destination_pdr_ci95_low",
        "destination_pdr_ci95_high", "relative_airtime_cost",
        "relative_airtime_ci95_low", "relative_airtime_ci95_high",
    )
    for item in saved:
        expected = expected_by_comparator[item["comparator"]]
        if (item.get("case") != "recurring_fading"
                or item.get("focus_protocol") != CLAR_PROTOCOLS[0]
                or item.get("seed_split") != "clar-development"
                or item.get("gate_evaluable") != str(expected["gate_evaluable"])
                or item.get("reliability_cost_gate")
                != str(expected["reliability_cost_gate"])
                or item.get("clar_joint_primary_gate")
                != str(expected["clar_joint_primary_gate"])):
            raise ValueError("CLAR development paired evidence differs from runs")
        try:
            fields_match = all(math.isclose(
                float(item[field]), float(expected[field]), rel_tol=1e-10,
                abs_tol=1e-10,
            ) for field in numeric_fields)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("CLAR development paired evidence lacks gate fields") from exc
        if not fields_match:
            raise ValueError("CLAR development paired evidence differs from runs")
    joint_gate = all(expected_by_comparator[name]["reliability_cost_gate"]
                     for name in CLAR_PRIMARY_COMPARATORS)
    if manifest.get("clar_joint_primary_gate") is not joint_gate:
        raise ValueError("CLAR development manifest joint primary gate differs from runs")
    if not joint_gate:
        raise ValueError("CLAR development joint primary gate did not pass")


def validate_dhr_development_manifest(path: Path, expected_source: Dict[str, str]) -> None:
    """Open DHR holdout only after verifying the frozen development evidence."""

    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("source_sha256") != expected_source:
        raise ValueError("DHR development source hash differs from holdout code")
    if (
        manifest.get("case") != asdict(SR_CASES["recurring_fading"])
        or manifest.get("protocols") != list(DHR_PROTOCOLS)
        or manifest.get("seeds") != list(DHR_DEVELOPMENT_SEEDS)
        or manifest.get("seed_split") != "dhr-development"
        or manifest.get("application_deadline_s") != 30.0
    ):
        raise ValueError("DHR development manifest differs from frozen configuration")
    if not path.name.endswith(".manifest.json"):
        raise ValueError("DHR development artifact manifest needs a .manifest.json suffix")
    prefix = path.with_name(path.name[:-len(".manifest.json")])
    artifact_hashes = manifest.get("artifact_sha256")
    if not isinstance(artifact_hashes, dict):
        raise ValueError("DHR development artifact hashes are missing")
    paths = artifact_paths(prefix)
    for key in ("runs", "paired", "flows", "actions"):
        artifact = paths[key]
        if (not artifact.is_file()
                or hashlib.sha256(artifact.read_bytes()).hexdigest()
                != artifact_hashes.get(key)):
            raise ValueError(f"DHR development artifact missing or hash mismatch: {key}")
    with paths["runs"].open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    expected_count = len(DHR_DEVELOPMENT_SEEDS) * len(DHR_PROTOCOLS)
    counts = Counter((row.get("seed"), row.get("protocol")) for row in rows)
    if (len(rows) != expected_count or manifest.get("runs") != expected_count
            or any(counts[(str(seed), protocol)] != 1
                   for seed in DHR_DEVELOPMENT_SEEDS for protocol in DHR_PROTOCOLS)):
        raise ValueError("DHR development runs require four policy rows per seed")
    case_hash = hashlib.sha256(json.dumps(
        asdict(SR_CASES["recurring_fading"]), sort_keys=True, separators=(",", ":")
    ).encode("ascii")).hexdigest()
    traces: Dict[int, tuple[str, int]] = {}
    for row in rows:
        try:
            seed = int(row["seed"])
            scheduled = int(row["scheduled_unicast_flows"])
            valid = (
                row.get("case") == "recurring_fading"
                and row.get("case_config_sha256") == case_hash
                and row.get("seed_split") == "dhr-development"
                and float(row["generation_horizon_s"]) == 600.0
                and float(row["drain_until_s"]) == 630.0
                and float(row["application_deadline_s"]) == 30.0
                and scheduled > 0
                and len(row["scheduled_trace_sha256"]) > 0
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("DHR development run row differs from frozen case config") from exc
        if not valid:
            raise ValueError("DHR development run row differs from frozen case config")
        trace = (row["scheduled_trace_sha256"], scheduled)
        if seed in traces and traces[seed] != trace:
            raise ValueError("DHR development application trace differs across arms")
        traces[seed] = trace

    flow_by_key: Dict[tuple[int, str, int], Dict[str, Any]] = {}
    flow_counts: Counter[tuple[int, str]] = Counter()
    ack_counts: Counter[tuple[int, str]] = Counter()
    delivery_counts: Counter[tuple[int, str]] = Counter()
    completion_delays: Dict[tuple[int, str], List[float]] = {}
    with paths["flows"].open(encoding="utf-8") as handle:
        for line in handle:
            try:
                flow = json.loads(line)
                seed = int(flow["seed"])
                protocol = str(flow["protocol"])
                flow_id = int(flow["flow_id"])
                src = int(flow["src"])
                dst = int(flow["dst"])
                enqueued_at = float(flow["enqueued_at"])
                deadline_at = float(flow["deadline_at"])
                acked = flow["ack_by_deadline"]
                delivered = flow["delivery_by_deadline"]
                acked_at = flow.get("acked_at")
                capped = float(flow["completion_delay_capped_s"])
                expected_capped = (
                    float(acked_at) - enqueued_at if acked else 30.0
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("DHR development flow evidence is invalid") from exc
            identity = (seed, protocol, flow_id)
            if (flow.get("case") != "recurring_fading"
                    or flow.get("seed_split") != "dhr-development"
                    or seed not in DHR_DEVELOPMENT_SEEDS
                    or protocol not in DHR_PROTOCOLS
                    or identity in flow_by_key
                    or not isinstance(acked, bool)
                    or not isinstance(delivered, bool)
                    or acked and not delivered
                    or (acked and acked_at is None)
                    or src == dst or not 0 <= src < SR_CASES["recurring_fading"].nodes
                    or not 0 <= dst < SR_CASES["recurring_fading"].nodes
                    or not 0.0 <= enqueued_at < 600.0
                    or not math.isclose(deadline_at - enqueued_at, 30.0,
                                        rel_tol=0.0, abs_tol=1e-9)
                    or not math.isfinite(capped)
                    or not math.isclose(capped, expected_capped,
                                        rel_tol=0.0, abs_tol=1e-9)
                    or not 0.0 <= capped <= 30.0):
                raise ValueError("DHR development flow evidence is invalid")
            flow_by_key[identity] = flow
            key = (seed, protocol)
            flow_counts[key] += 1
            ack_counts[key] += acked
            delivery_counts[key] += delivered
            completion_delays.setdefault(key, []).append(capped)
    for row in rows:
        key = (int(row["seed"]), row["protocol"])
        try:
            scheduled = int(row["scheduled_unicast_flows"])
            acked = int(row["ack_by_deadline"])
            delivered = int(row["delivery_by_deadline"])
            valid = (
                0 <= acked <= delivered <= scheduled
                and flow_counts[key] == scheduled
                and ack_counts[key] == acked
                and delivery_counts[key] == delivered
                and math.isclose(acked / scheduled, float(row["ack_pdr_deadline"]),
                                 rel_tol=0.0, abs_tol=1e-10)
                and math.isclose(delivered / scheduled,
                                 float(row["destination_pdr_deadline"]),
                                 rel_tol=0.0, abs_tol=1e-10)
                and math.isclose(statistics.fmean(completion_delays[key]),
                                 float(row["mean_completion_delay_capped_s"]),
                                 rel_tol=0.0, abs_tol=1e-9)
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("DHR development flow evidence differs from runs") from exc
        if not valid:
            raise ValueError("DHR development flow evidence differs from runs")

    event_counts: Counter[tuple[int, str, str]] = Counter()
    marker_counts: Counter[tuple[int, str, str]] = Counter()
    guard_by_flow: Dict[tuple[int, str, int], Dict[str, Any]] = {}
    rescue_by_flow: Dict[tuple[int, str, int], Dict[str, Any]] = {}
    accepted_by_flow: Dict[tuple[int, str, int], Dict[str, Any]] = {}
    exposure_seeds: Counter[int] = Counter()
    rescue_seeds: Dict[str, Counter[int]] = {"R": Counter(), "F": Counter()}
    with paths["actions"].open(encoding="utf-8") as handle:
        for line in handle:
            try:
                event = json.loads(line)
                seed = int(event["seed"])
                protocol = str(event["protocol"])
                name = str(event["event"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("DHR development action evidence is invalid") from exc
            if (event.get("case") != "recurring_fading"
                    or event.get("seed_split") != "dhr-development"
                    or seed not in DHR_DEVELOPMENT_SEEDS
                    or protocol not in DHR_PROTOCOLS):
                raise ValueError("DHR development action evidence is invalid")
            if not name.startswith("dhr_"):
                continue
            try:
                flow_id = int(event["flow_id"])
                src = int(event["src"])
                dst = int(event["dst"])
                when = float(event["time"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("DHR development action evidence is invalid") from exc
            identity = (seed, protocol, flow_id)
            flow = flow_by_key.get(identity)
            if (flow is None or src != flow["src"] or dst != flow["dst"]
                    or not math.isfinite(when)
                    or when < float(flow["enqueued_at"]) or when > 630.0):
                raise ValueError("DHR development action evidence is invalid")
            event_counts[(seed, protocol, name)] += 1
            if name == "dhr_guard":
                admitted = event.get("admitted")
                choice = event.get("selected_action")
                if (identity in guard_by_flow or flow.get("source_action") != "R"
                        or not isinstance(admitted, bool)
                        or choice not in {"R", "F", "none"}
                        or (admitted and protocol == "meshecho-dhr"
                            and choice not in {"R", "F"})
                        or (admitted and protocol == "meshecho-dhr-none"
                            and choice != "none")
                        or (admitted and protocol == "meshecho-dhr-repeat"
                            and choice != "R")
                        or (admitted and protocol == "meshecho-dhr-flood"
                            and choice != "F")
                        or (not admitted and choice != "none")
                        or (admitted and event.get("reason") != "admitted")
                        or when > float(flow["deadline_at"])):
                    raise ValueError("DHR development guard evidence is invalid")
                guard_by_flow[identity] = event
                if admitted:
                    event_counts[(seed, protocol, "dhr_admitted_guard")] += 1
                    if protocol == DHR_PROTOCOLS[0]:
                        exposure_seeds[seed] += 1
                if choice in {"R", "F"}:
                    marker_counts[(seed, protocol, f"selected_{choice}")] += 1
            elif name == "dhr_recovery_tx":
                action = event.get("action")
                marker = event.get("repair_index")
                end = event.get("end")
                if (identity in rescue_by_flow or action not in {"R", "F"}
                        or marker != {"R": 1, "F": 2}.get(action)
                        or protocol == "meshecho-dhr-none"
                        or (protocol == "meshecho-dhr-repeat" and action != "R")
                        or (protocol == "meshecho-dhr-flood" and action != "F")
                        or end is None or not math.isfinite(float(end))
                        or float(end) <= when or when > float(flow["deadline_at"])):
                    raise ValueError("DHR development rescue action is invalid")
                rescue_by_flow[identity] = event
                marker_counts[(seed, protocol, f"rescue_{action}")] += 1
                if protocol == DHR_PROTOCOLS[0]:
                    rescue_seeds[action][seed] += 1
            elif name == "dhr_source_ack_rx" and event.get("accepted") is True:
                marker = event.get("repair_index")
                if (identity in accepted_by_flow or marker not in {None, 1, 2}
                        or flow["ack_by_deadline"] is not True
                        or not math.isclose(float(flow["acked_at"]), when,
                                            rel_tol=0.0, abs_tol=1e-9)):
                    raise ValueError("DHR development accepted ACK evidence is invalid")
                accepted_by_flow[identity] = event
                marker_counts[(seed, protocol, f"ack_{marker}")] += 1
            elif name == "dhr_destination_rx":
                if not isinstance(event.get("duplicate"), bool):
                    raise ValueError("DHR development destination reception is invalid")
                if event["duplicate"]:
                    marker_counts[(seed, protocol, "destination_duplicate")] += 1
    for identity, rescue in rescue_by_flow.items():
        guard = guard_by_flow.get(identity)
        if (guard is None or guard.get("admitted") is not True
                or guard.get("selected_action") != rescue["action"]
                or float(rescue["time"]) < float(guard["time"])):
            raise ValueError("DHR development rescue lacks admitted guard")
    for identity, event in accepted_by_flow.items():
        if event["repair_index"] in {1, 2}:
            rescue = rescue_by_flow.get(identity)
            if rescue is None or rescue["repair_index"] != event["repair_index"]:
                raise ValueError("DHR development accepted rescue ACK lacks TX")
    for row in rows:
        seed = int(row["seed"])
        protocol = row["protocol"]
        key = (seed, protocol)
        expected = {
            "dhr_guard_events": event_counts[key + ("dhr_guard",)],
            "dhr_admitted_guards": event_counts[key + ("dhr_admitted_guard",)],
            "dhr_selected_r": marker_counts[key + ("selected_R",)],
            "dhr_selected_f": marker_counts[key + ("selected_F",)],
            "dhr_selected_none": (
                event_counts[key + ("dhr_guard",)]
                - marker_counts[key + ("selected_R",)]
                - marker_counts[key + ("selected_F",)]
            ),
            "dhr_recovery_r_tx": marker_counts[key + ("rescue_R",)],
            "dhr_recovery_f_tx": marker_counts[key + ("rescue_F",)],
            "windowed_dhr_recovery_r_source_tx": marker_counts[key + ("rescue_R",)],
            "windowed_dhr_recovery_f_source_tx": marker_counts[key + ("rescue_F",)],
            "dhr_source_ack_accepted": sum(
                marker_counts[key + (f"ack_{marker}",)] for marker in (None, 1, 2)
            ),
            "dhr_source_ack_accepted_initial": marker_counts[key + ("ack_None",)],
            "dhr_source_ack_accepted_r": marker_counts[key + ("ack_1",)],
            "dhr_source_ack_accepted_f": marker_counts[key + ("ack_2",)],
            "dhr_duplicate_destination_receptions": marker_counts[
                key + ("destination_duplicate",)
            ],
        }
        expected["dhr_rejected_guards"] = (
            expected["dhr_guard_events"] - expected["dhr_admitted_guards"]
        )
        try:
            consistent = all(int(row[field]) == count for field, count in expected.items())
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("DHR development action counts differ from runs") from exc
        if not consistent or expected["dhr_source_ack_accepted"] != ack_counts[key]:
            raise ValueError("DHR development action counts differ from runs")
    exposure = {
        "dhr_admitted_guard_events": sum(exposure_seeds.values()),
        "dhr_admitted_guard_seeds": len(exposure_seeds),
        "dhr_r_rescue_events": sum(rescue_seeds["R"].values()),
        "dhr_r_rescue_seeds": len(rescue_seeds["R"]),
        "dhr_f_rescue_events": sum(rescue_seeds["F"].values()),
        "dhr_f_rescue_seeds": len(rescue_seeds["F"]),
    }
    if any(manifest.get(field) != count for field, count in exposure.items()):
        raise ValueError("DHR development exposure differs from action log")
    exposure_gate = (
        exposure["dhr_admitted_guard_events"] >= 20
        and exposure["dhr_admitted_guard_seeds"] >= 10
        and exposure["dhr_r_rescue_events"] >= 10
        and exposure["dhr_r_rescue_seeds"] >= 5
        and exposure["dhr_f_rescue_events"] >= 10
        and exposure["dhr_f_rescue_seeds"] >= 5
    )
    if manifest.get("dhr_exposure_gate") is not exposure_gate or not exposure_gate:
        raise ValueError("DHR development action exposure gate did not pass")
    try:
        recomputed = summarize_paired(rows, DHR_PROTOCOLS[0], DHR_PROTOCOLS[1:])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("DHR development paired trace or config evidence is invalid") from exc
    with paths["paired"].open(newline="", encoding="utf-8") as handle:
        saved = list(csv.DictReader(handle))
    expected_by_comparator = {item["comparator"]: item for item in recomputed}
    if (len(saved) != len(DHR_PROTOCOLS) - 1
            or {item.get("comparator") for item in saved} != set(DHR_PROTOCOLS[1:])):
        raise ValueError("DHR development paired evidence lacks three controls")
    numeric_fields = (
        "n_seeds", "ack_pdr_gain", "ack_pdr_ci95_low", "ack_pdr_ci95_high",
        "destination_pdr_gain", "destination_pdr_ci95_low",
        "destination_pdr_ci95_high", "relative_airtime_cost",
        "relative_airtime_ci95_low", "relative_airtime_ci95_high",
    )
    for item in saved:
        expected = expected_by_comparator[item["comparator"]]
        if (item.get("case") != "recurring_fading"
                or item.get("focus_protocol") != DHR_PROTOCOLS[0]
                or item.get("seed_split") != "dhr-development"
                or item.get("dhr_primary_gate") != str(expected["dhr_primary_gate"])
                or item.get("dhr_joint_primary_gate")
                != str(expected["dhr_joint_primary_gate"])):
            raise ValueError("DHR development paired evidence differs from runs")
        try:
            fields_match = all(math.isclose(
                float(item[field]), float(expected[field]), rel_tol=1e-10,
                abs_tol=1e-10,
            ) for field in numeric_fields)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("DHR development paired evidence lacks gate fields") from exc
        if not fields_match:
            raise ValueError("DHR development paired evidence differs from runs")
    joint_gate = all(expected_by_comparator[name]["dhr_primary_gate"]
                     for name in DHR_PRIMARY_COMPARATORS)
    if (manifest.get("dhr_joint_primary_gate") is not joint_gate
            or manifest.get("dhr_project_gate") is not (joint_gate and exposure_gate)
            or not joint_gate):
        raise ValueError("DHR development joint primary gate did not pass")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=SR_CASES, default="recurring_fading")
    parser.add_argument(
        "--split",
        choices=(
            "development", "holdout", "lpr-development", "lpr-holdout",
            "dpa-development", "dpa-holdout", "rac-development", "rac-holdout",
            "clar-development", "clar-holdout", "dhr-development", "dhr-holdout",
            "bar-development", "bar-holdout",
            "custom",
        ),
        default="development",
    )
    parser.add_argument("--suite", choices=("sr", "mag", "lpr", "dpa", "rac", "clar", "dhr", "bar"), default="sr")
    parser.add_argument("--deadline-s", type=float, default=30.0)
    parser.add_argument("--seed", action="append", type=int, dest="seeds")
    parser.add_argument("--protocol", action="append", dest="protocols")
    parser.add_argument("--out-prefix", type=Path)
    parser.add_argument("--development-manifest", type=Path)
    args = parser.parse_args(argv)
    if args.split == "custom":
        if not args.seeds:
            parser.error("custom split requires at least one --seed")
        args.seeds = tuple(args.seeds)
    elif args.seeds:
        parser.error("--seed is only allowed with the custom split")
    suites = {
        "sr": SR_PROTOCOLS, "mag": MAG_PROTOCOLS,
        "lpr": LPR_PROTOCOLS, "dpa": DPA_PROTOCOLS, "rac": RAC_PROTOCOLS,
        "clar": CLAR_PROTOCOLS, "dhr": DHR_PROTOCOLS,
        "bar": BAR_PROTOCOLS,
    }
    args.protocols = tuple(args.protocols or suites[args.suite])
    return args


def schedule_sr_traffic(
    sim: Simulator,
    case: SrCase,
    pairs: Sequence[tuple[int, int]],
    rng: random.Random,
) -> None:
    if case.traffic_pattern == "standard":
        schedule_probe_traffic(
            sim,
            case.duration_s,
            case.rate_per_min,
            case.traffic,
            rng,
            pairs,
            case.pair_schedule,
        )
        return
    if case.traffic_pattern != "phase-shift" or case.traffic != "unicast" or not pairs:
        raise ValueError("phase-shift requires repeated unicast pairs")
    if case.rate_per_min <= 0:
        raise ValueError("phase-shift requires positive rate_per_min")
    node_ids = sorted(sim.nodes)
    flow_id = 1
    now = 1.0
    mean_interval = 60.0 / case.rate_per_min
    while now < case.duration_s:
        if now < case.duration_s / 2:
            src, dst = pairs[(flow_id - 1) % len(pairs)]
        else:
            src = rng.choice(node_ids)
            dst = rng.choice([node_id for node_id in node_ids if node_id != src])
        sim.schedule(now, "app_send", (src, dst, flow_id))
        flow_id += 1
        now += rng.expovariate(1.0 / mean_interval)


def observed_tx_airtime(
    intervals: Sequence[tuple[float, float]], cutoff_s: float
) -> tuple[float, int]:
    """Charge complete packets actually starting within the drain window."""

    observed = [end - start for start, end in intervals if start <= cutoff_s]
    queued_future = sum(start > cutoff_s for start, _ in intervals)
    return sum(observed), queued_future


def summarize_ack_hop_observations(
    transmissions: Sequence[Transmission], decoded_tx_ids: set[int], cutoff_s: float,
) -> Dict[str, Any]:
    """Describe physical decodes on ACK packets' intended reverse hops."""

    ack_txs = [
        tx for tx in transmissions
        if tx.packet.kind == "ACK" and tx.start <= cutoff_s
    ]
    expected = [
        tx for tx in ack_txs
        if 0 <= tx.packet.path_index < len(tx.packet.path)
    ]
    completed = [tx for tx in expected if tx.end <= cutoff_s]
    failures = [tx for tx in completed if tx.tx_id not in decoded_tx_ids]
    failure_hops = Counter(
        len(tx.packet.path) - 1 - tx.packet.path_index for tx in failures
    )
    return {
        "windowed_destination_ack_attempts": sum(
            tx.sender == tx.packet.origin for tx in ack_txs
        ),
        "ack_expected_hop_observed_tx": len(completed),
        "ack_expected_hop_physical_failures": len(failures),
        "ack_expected_hop_censored_tx": len(expected) - len(completed),
        "ack_no_expected_hop_tx": len(ack_txs) - len(expected),
        "ack_physical_failures_by_reverse_hop": json.dumps(
            failure_hops, sort_keys=True, separators=(",", ":")
        ),
    }


def summarize_windowed_transmissions(
    transmissions: Sequence[Transmission], cutoff_s: float,
    app_payload_bytes: int = 32,
) -> Dict[str, Any]:
    """Count the same complete, actually started packets charged for airtime."""

    observed = [tx for tx in transmissions if tx.start <= cutoff_s]
    airtime_s, queued_future = observed_tx_airtime(
        [(tx.start, tx.end) for tx in transmissions], cutoff_s
    )
    kinds = Counter(tx.packet.kind for tx in observed)
    ack_packets = [tx.packet for tx in observed if tx.packet.kind == "ACK"]
    done_packets = [tx.packet for tx in observed if tx.packet.kind == "ACK_DONE"]
    ack_by_path_index = Counter(packet.path_index for packet in ack_packets)
    patch_tx = kinds["PATCH"]
    patch_relay_tx = kinds["PATCH_RELAY"]
    dhr_source_recovery = [
        tx for tx in observed
        if tx.packet.protocol in DHR_FAMILY_PROTOCOLS and tx.sender == tx.packet.origin
        and (tx.packet.kind, tx.packet.repair_index) in {
            ("DATA", 1), ("FLOOD", 2),
        }
    ]
    return {
        "whole_network_tx_airtime_s": airtime_s,
        "queued_future_tx_count": queued_future,
        "windowed_tx_count": len(observed),
        "windowed_data_tx": sum(not tx.packet.is_control for tx in observed),
        "windowed_control_tx": sum(tx.packet.is_control for tx in observed),
        "windowed_control_bytes": sum(
            tx.packet.wire_size_bytes(app_payload_bytes)
            for tx in observed if tx.packet.is_control
        ),
        "windowed_ack_tx": kinds["ACK"],
        "windowed_done_tx": kinds["ACK_DONE"],
        "windowed_done_bytes": sum(
            packet.wire_size_bytes(app_payload_bytes) for packet in done_packets
        ),
        "windowed_tx_bytes": sum(
            tx.packet.wire_size_bytes(app_payload_bytes) for tx in observed
        ),
        "windowed_ack_bytes": sum(
            packet.wire_size_bytes(app_payload_bytes) for packet in ack_packets
        ),
        "windowed_ack_tx_by_path_index": json.dumps(
            ack_by_path_index, sort_keys=True, separators=(",", ":")
        ),
        "windowed_rac_repair_ack_tx": sum(
            packet.protocol in RAC_PROTOCOLS and packet.repair_index == 0
            for packet in ack_packets
        ),
        "windowed_rac_repeat_ack_tx": sum(
            packet.protocol in RAC_PROTOCOLS and packet.repair_index == 1
            for packet in ack_packets
        ),
        "windowed_clar_initial_ack_tx": sum(
            packet.protocol in CLAR_PROTOCOLS and packet.repair_index == 255
            for packet in ack_packets
        ),
        "windowed_clar_repair_ack_tx": sum(
            packet.protocol in CLAR_PROTOCOLS and packet.repair_index == 0
            for packet in ack_packets
        ),
        "windowed_clar_repeat_ack_tx": sum(
            packet.protocol in CLAR_PROTOCOLS and packet.repair_index == 1
            for packet in ack_packets
        ),
        "windowed_dhr_initial_ack_tx": sum(
            packet.protocol in DHR_FAMILY_PROTOCOLS and packet.repair_index is None
            for packet in ack_packets
        ),
        "windowed_dhr_repeat_ack_tx": sum(
            packet.protocol in DHR_FAMILY_PROTOCOLS and packet.repair_index == 1
            for packet in ack_packets
        ),
        "windowed_dhr_flood_ack_tx": sum(
            packet.protocol in DHR_FAMILY_PROTOCOLS and packet.repair_index == 2
            for packet in ack_packets
        ),
        "windowed_dhr_recovery_r_source_tx": sum(
            tx.packet.repair_index == 1 for tx in dhr_source_recovery
        ),
        "windowed_dhr_recovery_f_source_tx": sum(
            tx.packet.repair_index == 2 for tx in dhr_source_recovery
        ),
        "windowed_rreq_tx": kinds["RREQ"],
        "windowed_rrep_tx": kinds["RREP"],
        "windowed_route_control_tx": kinds["RREQ"] + kinds["RREP"],
        "windowed_patch_tx": patch_tx,
        "windowed_patch_relay_tx": patch_relay_tx,
        "windowed_repair_tx": patch_tx + patch_relay_tx,
    }


def run_one_sr(
    case: SrCase,
    protocol_name: str,
    seed: int,
    deadline_s: float = 30.0,
    *,
    research_authorization: object | None = None,
    stage_authorization_path: Path | None = None,
    smoke_manifest_path: Path | None = None,
    prerequisite_manifest_path: Path | None = None,
) -> SrRun:
    """Run one policy on application sends generated before `duration_s`."""

    if deadline_s < 0:
        raise ValueError("deadline_s must be nonnegative")
    if protocol_name.startswith(("meshecho-sr", "meshecho-mag", "meshecho-lpr", "meshecho-dpa", "meshecho-rac", "meshecho-clar", "meshecho-dhr", "meshecho-bar", "meshecho-dcb")) and deadline_s <= 0:
        raise ValueError("SR/MAG/LPR/DPA/RAC/CLAR/DHR/BAR/DCB requires a positive application deadline")
    if seed in DCB_RESERVED_SEEDS:
        from tools import run_dcb_experiment as dcb

        if (type(seed) is not int
                or research_authorization is not dcb._CAPTURE_AUTHORIZATION
                or stage_authorization_path is None
                or protocol_name not in dcb.ARMS):
            raise ValueError("DCB reserved seed requires staged experiment authorization")
        mode = next(
            (name for name, selected in dcb.SEEDS_BY_MODE.items()
             if seed in selected), None,
        )
        if mode is None:
            raise ValueError("DCB reserved seed is outside its stage cohort")
        dcb._validate_stage(
            mode, dcb.SEEDS_BY_MODE[mode], case, deadline_s,
            stage_authorization_path, prerequisite_manifest_path,
        )
    if seed in DBR_RESERVED_SEEDS:
        from tools import run_dbr_experiment as dbr

        if (research_authorization is not dbr._CAPTURE_AUTHORIZATION
                or stage_authorization_path is None):
            raise ValueError("DBR reserved seed requires stage authorization")
        if protocol_name not in dbr.ARMS:
            raise ValueError("DBR reserved seed requires a registered DBR arm")
        mode = next(
            (name for name, selected in dbr.SEEDS_BY_MODE.items()
             if seed in selected), None,
        )
        if mode is None:
            raise ValueError("DBR reserved seed is outside its stage window")
        dbr._validate_stage(
            mode, dbr.SEEDS_BY_MODE[mode], case, deadline_s,
            stage_authorization_path,
        )
    if seed in FIRST_HOP_RECEIPT_RESERVED_SEEDS:
        from tools import diagnose_first_hop_receipt_screen as receipt

        if (type(seed) is not int
                or research_authorization is not receipt._RUNNER_AUTHORIZATION
                or stage_authorization_path is None
                or protocol_name != receipt.PROTOCOL
                or case != SR_CASES["recurring_fading"]
                or deadline_s != 30.0):
            raise ValueError(
                "receipt reserved seed requires staged diagnostic authorization"
            )
        receipt._validate_stage(
            receipt._stage_mode(seed), case, deadline_s,
            stage_authorization_path, smoke_manifest_path,
        )
    if seed in DESTINATION_BACKUP_RESERVED_SEEDS:
        from tools import run_destination_backup_screen as backup

        if (type(seed) is not int
                or stage_authorization_path is None
                or protocol_name != "meshecho-dhr-flood-ack-delay"
                or case != SR_CASES["recurring_fading"]
                or deadline_s != 30.0
                or research_authorization is not backup._RUNNER_AUTHORIZATION):
            raise ValueError(
                "backup reserved seed requires staged diagnostic authorization"
            )
        backup._validate_stage(
            "smoke" if seed == 46000 else "explore",
            case, deadline_s, stage_authorization_path, smoke_manifest_path,
        )
    config = make_args(case)
    config.sr_app_deadline_s = deadline_s
    nodes = generate_nodes(
        case.nodes, case.area_m, random.Random(seed), repeater_ratio=0.0
    )
    protocol = build_protocol(protocol_name, config)
    radio = make_radio(config)
    sim = RecordingSimulator(
        nodes,
        radio,
        protocol,
        seed=seed,
        max_hops=case.max_hops,
        independent_random_streams=True,
        matched_rreq_timing=case.matched_rreq_timing,
    )
    pairs = []
    if case.pair_mode == "connected-multihop":
        pairs, _ = connected_multihop_pairs(
            sim,
            random.Random(seed + 20_000),
            case.edge_prr_threshold,
            case.min_graph_hops,
            case.max_graph_hops,
            case.pair_count,
        )
        if len(pairs) != case.pair_count:
            raise ValueError(
                f"seed {seed}: selected {len(pairs)} of {case.pair_count} pairs"
            )
    elif case.pair_mode != "random":
        raise ValueError(f"unknown pair_mode: {case.pair_mode}")
    schedule_sr_traffic(sim, case, pairs, random.Random(seed + 10_000))
    scheduled = sorted(
        (when, *data)
        for when, _, kind, data in sim.events
        if kind == "app_send"
    )
    trace_hash = hashlib.sha256(
        json.dumps(scheduled, separators=(",", ":")).encode("ascii")
    ).hexdigest()
    metrics = sim.run(case.duration_s + deadline_s)
    windowed_tx = summarize_windowed_transmissions(
        sim.tx_history, case.duration_s + deadline_s, case.payload_bytes
    )
    ack_hop_summary = summarize_ack_hop_observations(
        sim.tx_history, sim.ack_expected_decodes, case.duration_s + deadline_s
    )
    observed_airtime_s = windowed_tx["whole_network_tx_airtime_s"]
    flow_rows: List[Dict[str, Any]] = []
    for when, src, dst, flow_id in scheduled:
        if dst == BROADCAST_DST:
            continue
        observed = metrics.flows.get(flow_id)
        acked_at = observed.acked_at if observed is not None else None
        delivered_at = observed.delivered_at if observed is not None else None
        deadline_at = when + deadline_s
        flow_rows.append(
            {
                "case": case.key,
                "protocol": protocol_name,
                "seed": seed,
                "flow_id": flow_id,
                "src": src,
                "dst": dst,
                "source_action": getattr(protocol, "flow_data_actions", {}).get(flow_id),
                "first_data_delivery_kind": sim.first_data_delivery_kind.get(flow_id),
                "enqueued_at": when,
                "deadline_at": deadline_at,
                "registered": observed is not None,
                "acked_at": acked_at,
                "delivered_at": delivered_at,
                "ack_by_deadline": acked_at is not None and acked_at <= deadline_at,
                "late_ack": acked_at is not None and acked_at > deadline_at,
                "delivery_by_deadline": (
                    delivered_at is not None and delivered_at <= deadline_at
                ),
                "late_delivery": (
                    delivered_at is not None and delivered_at > deadline_at
                ),
                "completion_delay_capped_s": (
                    min(acked_at - when, deadline_s)
                    if acked_at is not None and acked_at <= deadline_at
                    else deadline_s
                ),
            }
        )
    if not flow_rows:
        raise ValueError(f"case {case.key} seed {seed} scheduled no unicasts")
    ack_delays = [
        item["acked_at"] - item["enqueued_at"]
        for item in flow_rows
        if item["ack_by_deadline"]
    ]
    actions = [
        {"case": case.key, "protocol": protocol_name, "seed": seed, **event}
        for event in getattr(protocol, "action_events", [])
    ]
    bar_extra_by_flow = Counter(
        event["flow_id"] for event in actions
        if event.get("event") == "bar_extra_ack_tx"
        and event["time"] <= case.duration_s + deadline_s
    )
    for flow in flow_rows:
        flow["bar_extra_ack_tx_count"] = bar_extra_by_flow[flow["flow_id"]]
    dhr_guards = [event for event in actions if event.get("event") == "dhr_guard"]
    dhr_rescues = [event for event in actions
                   if event.get("event") == "dhr_recovery_tx"]
    dhr_accepted_acks = [event for event in actions
                         if event.get("event") == "dhr_source_ack_rx"
                         and event.get("accepted")]
    if protocol_name in RAC_PROTOCOLS or protocol_name in CLAR_PROTOCOLS:
        source_ack_event = (
            "clar_source_ack_rx" if protocol_name in CLAR_PROTOCOLS
            else "rac_source_ack_rx"
        )
        accepted_f_acks = {
            event["flow_id"]: event["repair_index"] for event in actions
            if event.get("event") == source_ack_event and event.get("accepted")
        }
        stages = {255: "initial", 0: "repair", 1: "repeat"}
        for flow in flow_rows:
            if flow["source_action"] != "F":
                continue
            marker = accepted_f_acks.get(flow["flow_id"])
            flow["f_ack_repair_index"] = marker
            flow["f_ack_stage"] = (
                stages[marker] if marker is not None else
                "destination_only" if flow["delivery_by_deadline"] else "not_delivered"
            )
    decisions = [
        event for event in actions if event.get("event", "decision") == "decision"
    ]
    commits = [event for event in actions if event.get("event") == "commit"]
    discoveries = [event for event in decisions if event.get("action") == "D"]
    cold_discoveries = [
        event for event in discoveries if "cold" in str(event.get("reason", ""))
    ]
    row = {
        "case": case.key,
        "case_config_sha256": hashlib.sha256(
            json.dumps(asdict(case), sort_keys=True, separators=(",", ":")).encode("ascii")
        ).hexdigest(),
        "protocol": protocol_name,
        "seed": seed,
        "generation_horizon_s": case.duration_s,
        "application_deadline_s": deadline_s,
        "drain_until_s": case.duration_s + deadline_s,
        "scheduled_trace_sha256": trace_hash,
        "scheduled_unicast_flows": len(flow_rows),
        "registered_unicast_flows": sum(item["registered"] for item in flow_rows),
        "ack_by_deadline": sum(item["ack_by_deadline"] for item in flow_rows),
        "late_ack_count": sum(item["late_ack"] for item in flow_rows),
        "delivery_by_deadline": sum(
            item["delivery_by_deadline"] for item in flow_rows
        ),
        "late_delivery_count": sum(item["late_delivery"] for item in flow_rows),
        "ack_pdr_deadline": sum(item["ack_by_deadline"] for item in flow_rows)
        / len(flow_rows),
        "destination_pdr_deadline": sum(
            item["delivery_by_deadline"] for item in flow_rows
        )
        / len(flow_rows),
        "p95_ack_delay_s": percentile(ack_delays, 0.95),
        "mean_completion_delay_capped_s": statistics.fmean(
            item["completion_delay_capped_s"] for item in flow_rows
        ),
        **windowed_tx,
        **ack_hop_summary,
        "tx_energy_j": (
            observed_airtime_s * radio.supply_voltage_v * radio.tx_current_ma / 1000.0
        ),
        "raw_modeled_rx_energy_j": metrics.rx_energy_j,
        "data_tx": metrics.data_tx,
        "control_tx": metrics.control_tx,
        "ack_tx": metrics.ack_tx,
        "raw_tx_count": metrics.tx_count,
        "raw_data_tx": metrics.data_tx,
        "raw_control_tx": metrics.control_tx,
        "raw_ack_tx": metrics.ack_tx,
        "route_discovery_attempts": metrics.route_discovery_attempts,
        "collision_failures": metrics.collision_fail,
        "raw_duplicate_rx": metrics.duplicate_rx,
        "dhr_guard_events": len(dhr_guards),
        "dhr_admitted_guards": sum(bool(event.get("admitted")) for event in dhr_guards),
        "dhr_rejected_guards": sum(not event.get("admitted") for event in dhr_guards),
        "dhr_selected_r": sum(event.get("selected_action") == "R"
                              for event in dhr_guards),
        "dhr_selected_f": sum(event.get("selected_action") == "F"
                              for event in dhr_guards),
        "dhr_selected_none": sum(event.get("selected_action") == "none"
                                 for event in dhr_guards),
        "dhr_guard_rejection_reasons": json.dumps(Counter(
            str(event.get("reason")) for event in dhr_guards
            if not event.get("admitted")
        ), sort_keys=True, separators=(",", ":")),
        "dhr_recovery_r_tx": sum(event.get("action") == "R"
                                 and event.get("repair_index") == 1
                                 for event in dhr_rescues),
        "dhr_recovery_f_tx": sum(event.get("action") == "F"
                                 and event.get("repair_index") == 2
                                 for event in dhr_rescues),
        "dhr_source_ack_accepted": len(dhr_accepted_acks),
        "dhr_source_ack_accepted_initial": sum(
            event.get("repair_index") is None for event in dhr_accepted_acks
        ),
        "dhr_source_ack_accepted_r": sum(
            event.get("repair_index") == 1 for event in dhr_accepted_acks
        ),
        "dhr_source_ack_accepted_f": sum(
            event.get("repair_index") == 2 for event in dhr_accepted_acks
        ),
        "dhr_duplicate_destination_receptions": sum(
            event.get("event") == "dhr_destination_rx" and event.get("duplicate")
            for event in actions
        ),
        "bar_first_flood_receipts": sum(
            event.get("event") == "bar_first_flood_rx" for event in actions
        ),
        "bar_candidate_events": sum(
            event.get("event") == "bar_candidate" for event in actions
        ),
        "bar_extra_ack_tx_events": sum(
            event.get("event") == "bar_extra_ack_tx"
            and event["time"] <= case.duration_s + deadline_s
            for event in actions
        ),
        "dpa_second_path_opportunities": sum(
            event.get("event") == "dpa_second_path" for event in actions
        ),
        "rac_corridor_eligible": sum(
            event.get("event") == "rac_corridor_eligible" for event in actions
        ),
        "rac_cancellations": sum(
            event.get("event") == "rac_cancel" for event in actions
        ),
        "rac_repair_tx_events": sum(
            event.get("event") == "rac_repair_tx" for event in actions
        ),
        "rac_repeat_tx_events": sum(
            event.get("event") == "rac_repeat_tx" for event in actions
        ),
        "rac_source_ack_accepted": sum(
            event.get("event") == "rac_source_ack_rx" and event.get("accepted")
            for event in actions
        ),
        "clar_candidate_eligible": sum(
            event.get("event") == "clar_candidate_eligible" for event in actions
        ),
        "clar_cancellations": sum(
            event.get("event") == "clar_cancel" for event in actions
        ),
        "clar_done_cancellations": sum(
            event.get("event") == "clar_cancel"
            and event.get("reason") == "source-done" for event in actions
        ),
        "clar_continuation_cancellations": sum(
            event.get("event") == "clar_cancel"
            and event.get("reason") in {"ack-continuation", "ack-continuation-repeat"}
            for event in actions
        ),
        "clar_done_tx_events": sum(
            event.get("event") == "clar_done_tx" for event in actions
        ),
        "clar_done_rx_events": sum(
            event.get("event") == "clar_done_rx" for event in actions
        ),
        "clar_repair_tx_events": sum(
            event.get("event") == "clar_repair_tx" for event in actions
        ),
        "clar_repeat_tx_events": sum(
            event.get("event") == "clar_repeat_tx" for event in actions
        ),
        "clar_source_ack_accepted": sum(
            event.get("event") == "clar_source_ack_rx" and event.get("accepted")
            for event in actions
        ),
        "repair_decisions": sum(event.get("action") == "P" for event in decisions),
        "ack_confirmed_inserted_repairs": sum(
            event.get("action") == "P" and event.get("replaced_confirmed_path")
            for event in commits
        ),
        "route_switches": sum(
            bool(event.get("replaced_confirmed_path")) for event in commits
        ),
        "action_decisions": len(decisions),
        "discovery_decisions": len(discoveries),
        "cold_discoveries": len(cold_discoveries),
        "shadow_discoveries": len(discoveries) - len(cold_discoveries),
    }
    return SrRun(row, flow_rows, actions)


def summarize_paired(
    rows: Sequence[Dict[str, Any]],
    focus_protocol: str,
    comparators: Sequence[str],
) -> List[Dict[str, Any]]:
    """Pair policy outcomes by case and topology seed, never by flow count."""

    grouped: Dict[str, Dict[int, Dict[str, Dict[str, Any]]]] = {}
    for row in rows:
        policies = grouped.setdefault(str(row["case"]), {}).setdefault(int(row["seed"]), {})
        protocol = str(row["protocol"])
        if protocol in policies:
            raise ValueError(f"duplicate run: {row['case']} seed {row['seed']} {protocol}")
        policies[protocol] = row

    summaries: List[Dict[str, Any]] = []
    for case, by_seed in sorted(grouped.items()):
        case_summary_start = len(summaries)
        config_hashes = {
            row["case_config_sha256"]
            for policies in by_seed.values()
            for row in policies.values()
        }
        if len(config_hashes) != 1:
            raise ValueError(f"paired case config differs across seeds: {case}")
        for comparator in comparators:
            ack_differences = []
            destination_differences = []
            airtime_relative_differences = []
            for seed, policies in sorted(by_seed.items()):
                if focus_protocol not in policies or comparator not in policies:
                    raise ValueError(
                        f"missing paired policy: {case} seed {seed} "
                        f"{focus_protocol}/{comparator}"
                    )
                focus = policies[focus_protocol]
                control = policies[comparator]
                if focus["case_config_sha256"] != control["case_config_sha256"]:
                    raise ValueError(f"paired case config differs: {case} seed {seed}")
                if (
                    focus["scheduled_trace_sha256"] != control["scheduled_trace_sha256"]
                    or focus["scheduled_unicast_flows"] != control["scheduled_unicast_flows"]
                    or focus["application_deadline_s"] != control["application_deadline_s"]
                ):
                    raise ValueError(f"paired trace or deadline differs: {case} seed {seed}")
                control_airtime = float(control["whole_network_tx_airtime_s"])
                if control_airtime <= 0.0:
                    raise ValueError(f"zero comparator airtime: {case} seed {seed}")
                ack_differences.append(
                    float(focus["ack_pdr_deadline"])
                    - float(control["ack_pdr_deadline"])
                )
                destination_differences.append(
                    float(focus["destination_pdr_deadline"])
                    - float(control["destination_pdr_deadline"])
                )
                airtime_relative_differences.append(
                    (float(focus["whole_network_tx_airtime_s"]) - control_airtime)
                    / control_airtime
                )
            ack_mean, ack_low, ack_high = paired_ci95(ack_differences)
            dst_mean, dst_low, dst_high = paired_ci95(destination_differences)
            air_mean, air_low, air_high = paired_ci95(airtime_relative_differences)
            gate_evaluable = len(by_seed) >= 20
            summaries.append(
                {
                    "case": case,
                    "focus_protocol": focus_protocol,
                    "comparator": comparator,
                    "n_seeds": len(by_seed),
                    "ack_pdr_gain": ack_mean,
                    "ack_pdr_ci95_low": ack_low,
                    "ack_pdr_ci95_high": ack_high,
                    "destination_pdr_gain": dst_mean,
                    "destination_pdr_ci95_low": dst_low,
                    "destination_pdr_ci95_high": dst_high,
                    "relative_airtime_cost": air_mean,
                    "relative_airtime_ci95_low": air_low,
                    "relative_airtime_ci95_high": air_high,
                    "gate_evaluable": gate_evaluable,
                    "reliability_cost_gate": gate_evaluable and ack_low > 0 and air_high < 0.10,
                }
            )
        if focus_protocol == "meshecho-lpr":
            case_summaries = summaries[case_summary_start:]
            primary = {item["comparator"]: item for item in case_summaries
                       if item["comparator"] in LPR_PRIMARY_COMPARATORS}
            joint = (len(primary) == len(LPR_PRIMARY_COMPARATORS)
                     and all(item["reliability_cost_gate"] for item in primary.values()))
            for item in case_summaries:
                item["lpr_joint_primary_gate"] = joint
        if focus_protocol == "meshecho-dpa":
            case_summaries = summaries[case_summary_start:]
            primary = {item["comparator"]: item for item in case_summaries
                       if item["comparator"] in DPA_PRIMARY_COMPARATORS}
            joint = (len(primary) == len(DPA_PRIMARY_COMPARATORS)
                     and all(item["reliability_cost_gate"] for item in primary.values()))
            for item in case_summaries:
                item["dpa_joint_primary_gate"] = joint
        if focus_protocol == "meshecho-rac":
            case_summaries = summaries[case_summary_start:]
            primary = {item["comparator"]: item for item in case_summaries
                       if item["comparator"] in RAC_PRIMARY_COMPARATORS}
            frozen_development = (
                case == "recurring_fading"
                and tuple(sorted(by_seed)) == RAC_DEVELOPMENT_SEEDS
                and all(row.get("seed_split") == "rac-development"
                        for policies in by_seed.values() for row in policies.values())
            )
            joint = (frozen_development
                     and len(primary) == len(RAC_PRIMARY_COMPARATORS)
                     and all(item["reliability_cost_gate"] for item in primary.values()))
            for item in case_summaries:
                item["rac_joint_primary_gate"] = joint
        if focus_protocol == "meshecho-clar":
            case_summaries = summaries[case_summary_start:]
            primary = {item["comparator"]: item for item in case_summaries
                       if item["comparator"] in CLAR_PRIMARY_COMPARATORS}
            frozen_development = (
                case == "recurring_fading"
                and tuple(sorted(by_seed)) == CLAR_DEVELOPMENT_SEEDS
                and all(row.get("seed_split") == "clar-development"
                        for policies in by_seed.values() for row in policies.values())
            )
            joint = (frozen_development
                     and len(primary) == len(CLAR_PRIMARY_COMPARATORS)
                     and all(item["reliability_cost_gate"] for item in primary.values()))
            for item in case_summaries:
                item["clar_joint_primary_gate"] = joint
        if focus_protocol == "meshecho-dhr":
            case_summaries = summaries[case_summary_start:]
            frozen_matrix = (
                case == "recurring_fading"
                and (
                    (tuple(sorted(by_seed)) == DHR_DEVELOPMENT_SEEDS
                     and all(row.get("seed_split") == "dhr-development"
                             for policies in by_seed.values() for row in policies.values()))
                    or (tuple(sorted(by_seed)) == DHR_HOLDOUT_SEEDS
                        and all(row.get("seed_split") == "dhr-holdout"
                                for policies in by_seed.values() for row in policies.values()))
                )
            )
            for item in case_summaries:
                comparator = item["comparator"]
                item["dhr_primary_gate"] = bool(
                    frozen_matrix
                    and (comparator == "meshecho-dhr-repeat"
                         and item["ack_pdr_ci95_low"] > 0
                         and item["ack_pdr_gain"] >= 0.02
                         and item["relative_airtime_ci95_high"] < 0.10
                         or comparator == "meshecho-dhr-flood"
                         and item["ack_pdr_ci95_low"] > -0.02
                         and item["relative_airtime_ci95_high"] < 0)
                )
            primary = {item["comparator"]: item for item in case_summaries
                       if item["comparator"] in DHR_PRIMARY_COMPARATORS}
            joint = ({item["comparator"] for item in case_summaries}
                     == set(DHR_PROTOCOLS[1:])
                     and len(primary) == len(DHR_PRIMARY_COMPARATORS)
                     and all(item["dhr_primary_gate"] for item in primary.values()))
            for item in case_summaries:
                item["dhr_joint_primary_gate"] = joint
        if focus_protocol == BAR_PROTOCOLS[0]:
            case_summaries = summaries[case_summary_start:]
            frozen_matrix = (
                case == "recurring_fading"
                and (
                    (tuple(sorted(by_seed)) == BAR_DEVELOPMENT_SEEDS
                     and all(row.get("seed_split") == "bar-development"
                             for policies in by_seed.values()
                             for row in policies.values()))
                    or (tuple(sorted(by_seed)) == BAR_HOLDOUT_SEEDS
                        and all(row.get("seed_split") == "bar-holdout"
                                for policies in by_seed.values()
                                for row in policies.values()))
                )
                and all(
                    set(policies) == set(BAR_PROTOCOLS)
                    for policies in by_seed.values()
                )
            )
            for item in case_summaries:
                comparator = item["comparator"]
                item["bar_primary_gate"] = bool(
                    frozen_matrix
                    and item["ack_pdr_ci95_low"] > 0
                    and (
                        comparator == BAR_PROTOCOLS[1]
                        and item["ack_pdr_gain"] >= 0.02
                        and item["relative_airtime_ci95_high"] < 0.08
                        and item["destination_pdr_ci95_low"] > -0.02
                        or comparator == BAR_PROTOCOLS[2]
                        and item["relative_airtime_ci95_high"] < 0.05
                    )
                )
            joint = (
                {item["comparator"] for item in case_summaries}
                == set(BAR_PROTOCOLS[1:])
                and all(item["bar_primary_gate"] for item in case_summaries)
            )
            for item in case_summaries:
                item["bar_joint_primary_gate"] = joint
    return summaries


def paired_ci95(values: Sequence[float]) -> tuple[float, float, float]:
    """Two-sided paired t interval; upper critical bounds are conservative."""

    if len(values) <= 20:
        return paired_mean_ci(values)
    mean = statistics.fmean(values)
    # t(.975, 20)=2.086 and t(.975, 39)=2.023. These rounded-up
    # critical values cover the frozen 20- and 40-seed experiment sizes.
    critical = 2.086 if len(values) < 40 else 2.024
    half = critical * statistics.stdev(values) / math.sqrt(len(values))
    return mean, mean - half, mean + half


def run_matrix(
    case: SrCase,
    protocols: Sequence[str],
    seeds: Sequence[int],
    deadline_s: float = 30.0,
    split: str = "custom",
    development_manifest: Path | None = None,
) -> SrExperiment:
    """Run a shared scenario for each policy on each independent seed."""

    if not protocols or not seeds:
        raise ValueError("protocols and seeds must both be nonempty")
    if len(set(seeds)) != len(seeds):
        raise ValueError("seed list contains duplicates")
    bar_smoke = (
        split == "custom" and tuple(protocols) == BAR_PROTOCOLS
        and tuple(seeds) == (16000,)
    )
    bar_split = (
        split in {"bar-development", "bar-holdout"}
        and tuple(protocols) == BAR_PROTOCOLS
    )
    if ((16000 in seeds and not bar_smoke)
            or (set(seeds).intersection(BAR_DEVELOPMENT_SEEDS)
                and split != "bar-development")
            or (set(seeds).intersection(BAR_HOLDOUT_SEEDS)
                and split != "bar-holdout")):
        raise ValueError("BAR reserved seeds require their frozen BAR split")
    if (split == "custom"
            and any(name in (BAR_PROTOCOLS[0], BAR_PROTOCOLS[2]) for name in protocols)
            and not bar_smoke):
        raise ValueError("BAR custom mode requires the full seed-16000 preflight suite")
    if (any(name in RAC_PROTOCOLS for name in protocols)
            and split not in {"custom", "rac-development", "rac-holdout"}):
        raise ValueError("RAC policies require a RAC split or custom mode")
    if (any(name in CLAR_PROTOCOLS for name in protocols)
            and split not in {"custom", "clar-development", "clar-holdout"}):
        raise ValueError("CLAR policies require a CLAR split or custom mode")
    if (any(name in DHR_PROTOCOLS for name in protocols)
            and split not in {"custom", "dhr-development", "dhr-holdout"}
            and not bar_split):
        raise ValueError("DHR policies require a DHR split or custom mode")
    if (split != "lpr-holdout"
            and any(name in LPR_PROTOCOLS for name in protocols)
            and set(seeds).intersection(HOLDOUT_SEEDS)):
        raise ValueError("LPR holdout policies require the lpr-holdout split")
    if (split != "dpa-holdout"
            and any(name in DPA_PROTOCOLS for name in protocols)
            and set(seeds).intersection(HOLDOUT_SEEDS)):
        raise ValueError("DPA holdout policies require the dpa-holdout split")
    if (split != "rac-holdout"
            and any(name in RAC_PROTOCOLS for name in protocols)
            and set(seeds).intersection(HOLDOUT_SEEDS)):
        raise ValueError("RAC holdout policies require the rac-holdout split")
    if (split != "clar-holdout"
            and any(name in CLAR_PROTOCOLS for name in protocols)
            and set(seeds).intersection(HOLDOUT_SEEDS)):
        raise ValueError("CLAR holdout policies require the clar-holdout split")
    if (split != "dhr-holdout"
            and any(name in DHR_PROTOCOLS for name in protocols)
            and set(seeds).intersection(DHR_HOLDOUT_SEEDS)):
        raise ValueError("DHR holdout policies require the dhr-holdout split")
    if (split == "custom"
            and any(name in RAC_PROTOCOLS for name in protocols)
            and tuple(seeds) != (7000,)):
        raise ValueError("RAC custom mode is reserved for the seed-7000 preflight")
    if (split == "custom"
            and any(name in RAC_PROTOCOLS for name in protocols)
            and tuple(protocols) != RAC_PROTOCOLS):
        raise ValueError("RAC custom mode requires the full RAC preflight suite")
    if (split == "custom"
            and any(name in CLAR_PROTOCOLS for name in protocols)
            and tuple(seeds) != (8000,)):
        raise ValueError("CLAR custom mode is reserved for the seed-8000 preflight")
    if (split == "custom"
            and any(name in CLAR_PROTOCOLS for name in protocols)
            and tuple(protocols) != CLAR_PROTOCOLS):
        raise ValueError("CLAR custom mode requires the full CLAR preflight suite")
    if (split == "custom"
            and any(name in DHR_PROTOCOLS for name in protocols)
            and not bar_smoke and tuple(seeds) != (9000,)):
        raise ValueError("DHR custom mode is reserved for the seed-9000 preflight")
    if (split == "custom"
            and any(name in DHR_PROTOCOLS for name in protocols)
            and not bar_smoke and tuple(protocols) != DHR_PROTOCOLS):
        raise ValueError("DHR custom mode requires the full DHR preflight suite")
    if split.startswith("lpr-") and tuple(protocols) != LPR_PROTOCOLS:
        raise ValueError("LPR split requires the full LPR policy suite")
    if split.startswith("dpa-") and tuple(protocols) != DPA_PROTOCOLS:
        raise ValueError("DPA split requires the full DPA policy suite")
    if split.startswith("rac-") and tuple(protocols) != RAC_PROTOCOLS:
        raise ValueError("RAC split requires the full RAC policy suite")
    if split.startswith("clar-") and tuple(protocols) != CLAR_PROTOCOLS:
        raise ValueError("CLAR split requires the full CLAR policy suite")
    if split.startswith("dhr-") and tuple(protocols) != DHR_PROTOCOLS:
        raise ValueError("DHR split requires the full DHR policy suite")
    if split.startswith("bar-") and tuple(protocols) != BAR_PROTOCOLS:
        raise ValueError("BAR split requires the full BAR policy suite")
    if split.startswith("lpr-") and case != SR_CASES["recurring_fading"]:
        raise ValueError("LPR split requires the frozen recurring_fading case")
    if split.startswith("dpa-") and case != SR_CASES["recurring_fading"]:
        raise ValueError("DPA split requires the frozen recurring_fading case")
    if split.startswith("rac-") and case != SR_CASES["recurring_fading"]:
        raise ValueError("RAC split requires the frozen recurring_fading case")
    if split.startswith("clar-") and case != SR_CASES["recurring_fading"]:
        raise ValueError("CLAR split requires the frozen recurring_fading case")
    if split.startswith("dhr-") and case != SR_CASES["recurring_fading"]:
        raise ValueError("DHR split requires the frozen recurring_fading case")
    if split.startswith("bar-") and case != SR_CASES["recurring_fading"]:
        raise ValueError("BAR split requires the frozen recurring_fading case")
    if split.startswith("lpr-") and deadline_s != 30.0:
        raise ValueError("LPR split requires the frozen 30-second deadline")
    if split.startswith("dpa-") and deadline_s != 30.0:
        raise ValueError("DPA split requires the frozen 30-second deadline")
    if split.startswith("rac-") and deadline_s != 30.0:
        raise ValueError("RAC split requires the frozen 30-second deadline")
    if split.startswith("clar-") and deadline_s != 30.0:
        raise ValueError("CLAR split requires the frozen 30-second deadline")
    if split.startswith("dhr-") and deadline_s != 30.0:
        raise ValueError("DHR split requires the frozen 30-second deadline")
    if split.startswith("bar-") and deadline_s != 30.0:
        raise ValueError("BAR split requires the frozen 30-second deadline")
    if split in {
        "development", "holdout", "lpr-development", "lpr-holdout",
            "dpa-development", "dpa-holdout", "rac-development", "rac-holdout",
            "clar-development", "clar-holdout", "dhr-development", "dhr-holdout",
            "bar-development", "bar-holdout",
    }:
        if tuple(seeds) != seeds_for_split(split):
            raise ValueError(f"{split} seeds must match the frozen seed list")
    elif split != "custom":
        raise ValueError(f"unknown seed split: {split}")
    if split == "lpr-holdout" and development_manifest is None:
        raise ValueError("LPR holdout requires a development manifest")
    if split == "dpa-holdout" and development_manifest is None:
        raise ValueError("DPA holdout requires a development manifest")
    if split == "rac-holdout" and development_manifest is None:
        raise ValueError("RAC holdout requires a development manifest")
    if split == "clar-holdout" and development_manifest is None:
        raise ValueError("CLAR holdout requires a development manifest")
    if split == "dhr-holdout" and development_manifest is None:
        raise ValueError("DHR holdout requires a development manifest")
    if split == "bar-holdout" and development_manifest is None:
        raise ValueError("BAR holdout requires a development manifest")
    source_suite = (
        "bar" if bar_smoke or bar_split else
        "dhr" if any(name in DHR_PROTOCOLS for name in protocols) else
        "clar" if any(name in CLAR_PROTOCOLS for name in protocols) else
        "rac" if any(name in RAC_PROTOCOLS for name in protocols) else
        "dpa" if any(name in DPA_PROTOCOLS for name in protocols) else "lpr"
    )
    source_sha256 = source_hashes(source_suite)
    if split == "lpr-holdout":
        validate_lpr_development_manifest(development_manifest, source_sha256)
    if split == "dpa-holdout":
        validate_dpa_development_manifest(development_manifest, source_sha256)
    if split == "rac-holdout":
        validate_rac_development_manifest(development_manifest, source_sha256)
    if split == "clar-holdout":
        validate_clar_development_manifest(development_manifest, source_sha256)
    if split == "dhr-holdout":
        validate_dhr_development_manifest(development_manifest, source_sha256)
    if split == "bar-holdout":
        validate_bar_development_manifest(development_manifest, source_sha256)
    rows: List[Dict[str, Any]] = []
    flows: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []
    for seed in seeds:
        for protocol in protocols:
            result = run_one_sr(case, protocol, seed, deadline_s)
            rows.append({**result.row, "seed_split": split})
            flows.extend({**flow, "seed_split": split} for flow in result.flows)
            actions.extend({**action, "seed_split": split} for action in result.actions)
    comparisons = summarize_paired(rows, protocols[0], protocols[1:])
    if source_hashes(source_suite) != source_sha256:
        raise RuntimeError("experiment source changed during the matrix")
    for comparison in comparisons:
        comparison["seed_split"] = split
        comparison["confirmatory_gate_eligible"] = confirmatory_comparison_eligible(
            split, case.key, protocols[0], comparison["comparator"]
        )
    return SrExperiment(
        case,
        tuple(protocols),
        tuple(seeds),
        deadline_s,
        rows,
        flows,
        actions,
        comparisons,
        split,
        source_sha256,
    )


def artifact_paths(prefix: Path) -> Dict[str, Path]:
    return {
        "runs": Path(f"{prefix}.runs.csv"),
        "paired": Path(f"{prefix}.paired.csv"),
        "flows": Path(f"{prefix}.flows.jsonl"),
        "actions": Path(f"{prefix}.actions.jsonl"),
        "manifest": Path(f"{prefix}.manifest.json"),
    }


def ensure_artifact_paths_available(prefix: Path) -> None:
    existing = [path for path in artifact_paths(prefix).values() if path.exists()]
    if existing:
        raise FileExistsError(f"experiment artifact already exists: {existing[0]}")


def write_artifacts(prefix: Path, bundle: SrExperiment) -> Dict[str, Path]:
    """Write seed-level, flow-level and action-level evidence side by side."""

    prefix.parent.mkdir(parents=True, exist_ok=True)
    ensure_artifact_paths_available(prefix)
    paths = artifact_paths(prefix)
    for key, records in (("runs", bundle.rows), ("paired", bundle.comparisons)):
        with paths[key].open("x", newline="", encoding="utf-8") as handle:
            if records:
                writer = csv.DictWriter(handle, fieldnames=list(records[0]))
                writer.writeheader()
                writer.writerows(records)
    for key, records in (("flows", bundle.flows), ("actions", bundle.actions)):
        with paths[key].open("x", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
                handle.write("\n")
    manifest = {
        "case": asdict(bundle.case),
        "protocols": list(bundle.protocols),
        "seeds": list(bundle.seeds),
        "seed_split": bundle.split,
        "application_deadline_s": bundle.deadline_s,
        "tx_cost_window": {
            "first_tx_start_s": 0.0,
            "last_tx_start_s": bundle.case.duration_s + bundle.deadline_s,
            "full_packet_toa_for_included_tx": True,
            "includes_post_flow_deadline_tx": True,
            "queued_tx_starting_after_window_excluded": True,
            "windowed_packet_counts_share_start_cutoff": True,
        },
        "raw_packet_count_fields": [
            "raw_tx_count", "raw_data_tx", "raw_control_tx", "raw_ack_tx",
        ],
        "raw_packet_count_caveat": (
            "Legacy data_tx/control_tx/ack_tx and raw_* fields include TX requests "
            "processed before drain but queued to start after the TX cost window"
        ),
        "rx_energy_caveat": (
            "raw_modeled_rx_energy_j is simulator accounting, potentially including "
            "queued TX that starts after the TX cost window; it is not a primary energy result"
        ),
        "source_sha256": bundle.source_sha256,
        "artifact_sha256": {
            key: hashlib.sha256(paths[key].read_bytes()).hexdigest()
            for key in ("runs", "paired", "flows", "actions")
        },
        "runs": len(bundle.rows),
        "scheduled_unicast_flows": sum(
            row["scheduled_unicast_flows"] for row in bundle.rows
        ),
    }
    if bundle.protocols == LPR_PROTOCOLS:
        manifest["lpr_joint_primary_gate"] = bool(
            bundle.comparisons and bundle.comparisons[0]["lpr_joint_primary_gate"]
        )
    if bundle.protocols == DPA_PROTOCOLS:
        manifest["dpa_joint_primary_gate"] = bool(
            bundle.comparisons and bundle.comparisons[0]["dpa_joint_primary_gate"]
        )
    if bundle.protocols == RAC_PROTOCOLS:
        manifest["rac_tx_count_interpretation"] = (
            "windowed_rac_repair_ack_tx counts all started marker-0 ACK hop TX, "
            "including on-path forwards; rac_repair_tx_events counts physical "
            "off-path relay starts. windowed_rac_repeat_ack_tx counts all started "
            "marker-1 ACK hop TX."
        )
        exposure = [
            event for event in bundle.actions
            if event.get("protocol") == RAC_PROTOCOLS[0]
            and event.get("event") == "rac_corridor_eligible"
        ]
        exposed_seeds = {int(event["seed"]) for event in exposure}
        manifest["rac_joint_primary_gate"] = bool(
            bundle.comparisons and bundle.comparisons[0]["rac_joint_primary_gate"]
        )
        manifest["rac_corridor_eligible_events"] = len(exposure)
        manifest["rac_corridor_exposed_seeds"] = len(exposed_seeds)
        manifest["rac_exposure_gate"] = bool(
            bundle.split == "rac-development"
            and len(exposure) >= 20 and len(exposed_seeds) >= 10
        )
    if bundle.protocols == CLAR_PROTOCOLS:
        focus_actions = [
            event for event in bundle.actions
            if event.get("protocol") == CLAR_PROTOCOLS[0]
        ]
        exposure = [
            event for event in focus_actions
            if event.get("event") == "clar_candidate_eligible"
        ]
        exposed_seeds = {int(event["seed"]) for event in exposure}
        manifest["clar_joint_primary_gate"] = bool(
            bundle.comparisons and bundle.comparisons[0]["clar_joint_primary_gate"]
        )
        manifest["clar_candidate_eligible_events"] = len(exposure)
        manifest["clar_candidate_exposed_seeds"] = len(exposed_seeds)
        manifest["clar_exposure_gate"] = bool(
            bundle.split == "clar-development"
            and len(exposure) >= 20 and len(exposed_seeds) >= 10
        )
        manifest["clar_done_cancel_events"] = sum(
            event.get("event") == "clar_cancel"
            and event.get("reason") == "source-done"
            for event in focus_actions
        )
        manifest["clar_ack_continuation_cancel_events"] = sum(
            event.get("event") == "clar_cancel"
            and event.get("reason") == "ack-continuation"
            for event in focus_actions
        )
    if bundle.protocols == DHR_PROTOCOLS:
        focus_actions = [event for event in bundle.actions
                         if event.get("protocol") == DHR_PROTOCOLS[0]]
        admitted = [event for event in focus_actions
                    if event.get("event") == "dhr_guard" and event.get("admitted")]
        r_rescues = [event for event in focus_actions
                     if event.get("event") == "dhr_recovery_tx"
                     and event.get("action") == "R"]
        f_rescues = [event for event in focus_actions
                     if event.get("event") == "dhr_recovery_tx"
                     and event.get("action") == "F"]
        manifest["dhr_joint_primary_gate"] = bool(
            bundle.comparisons and bundle.comparisons[0]["dhr_joint_primary_gate"]
        )
        manifest["dhr_admitted_guard_events"] = len(admitted)
        manifest["dhr_admitted_guard_seeds"] = len({event["seed"] for event in admitted})
        manifest["dhr_r_rescue_events"] = len(r_rescues)
        manifest["dhr_r_rescue_seeds"] = len({event["seed"] for event in r_rescues})
        manifest["dhr_f_rescue_events"] = len(f_rescues)
        manifest["dhr_f_rescue_seeds"] = len({event["seed"] for event in f_rescues})
        manifest["dhr_exposure_gate"] = bool(
            bundle.split in {"dhr-development", "dhr-holdout"}
            and len(admitted) >= 20
            and manifest["dhr_admitted_guard_seeds"] >= 10
            and len(r_rescues) >= 10
            and manifest["dhr_r_rescue_seeds"] >= 5
            and len(f_rescues) >= 10
            and manifest["dhr_f_rescue_seeds"] >= 5
        )
        manifest["dhr_project_gate"] = (
            manifest["dhr_joint_primary_gate"] and manifest["dhr_exposure_gate"]
        )
    if bundle.protocols == BAR_PROTOCOLS:
        exposure = [
            event for event in bundle.actions
            if event.get("protocol") == BAR_PROTOCOLS[0]
            and event.get("event") == "bar_extra_ack_tx"
            and event["time"] <= bundle.case.duration_s + bundle.deadline_s
        ]
        exposed_seeds = {int(event["seed"]) for event in exposure}
        manifest["bar_joint_primary_gate"] = bool(
            bundle.comparisons and bundle.comparisons[0].get("bar_joint_primary_gate")
        )
        manifest["bar_extra_ack_tx_events"] = len(exposure)
        manifest["bar_extra_ack_exposed_seeds"] = len(exposed_seeds)
        exposure_thresholds = {
            "bar-development": (20, 10),
            "bar-holdout": (40, 20),
        }
        minimum_events, minimum_seeds = exposure_thresholds.get(
            bundle.split, (math.inf, math.inf)
        )
        manifest["bar_exposure_gate"] = bool(
            len(exposure) >= minimum_events and len(exposed_seeds) >= minimum_seeds
        )
        manifest["bar_project_gate"] = (
            manifest["bar_joint_primary_gate"] and manifest["bar_exposure_gate"]
        )
        if bundle.split == "bar-development":
            manifest["bar_development_open_gate"] = manifest["bar_project_gate"]
        if bundle.split == "bar-holdout":
            manifest["bar_holdout_replication_gate"] = manifest["bar_project_gate"]
    with paths["manifest"].open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    return paths


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    case = SR_CASES[args.case]
    seeds = args.seeds if args.split == "custom" else seeds_for_split(args.split)
    prefix = args.out_prefix or ROOT / "results" / f"meshecho_sr_{case.key}_{args.split}"
    ensure_artifact_paths_available(prefix)
    bundle = run_matrix(
        case, args.protocols, seeds, args.deadline_s, args.split,
        args.development_manifest,
    )
    paths = write_artifacts(prefix, bundle)
    print(f"Runs: {paths['runs']}")
    print(f"Paired comparisons: {paths['paired']}")
    print(f"Flow and action logs: {paths['flows']}, {paths['actions']}")
    print(f"Manifest: {paths['manifest']}")
    for comparison in bundle.comparisons:
        print(
            f"{comparison['case']} vs {comparison['comparator']}: "
            f"ACK gain {comparison['ack_pdr_gain']:.4f} "
            f"[{comparison['ack_pdr_ci95_low']:.4f}, "
            f"{comparison['ack_pdr_ci95_high']:.4f}], "
            f"relative airtime {comparison['relative_airtime_cost']:.3f} "
            f"[{comparison['relative_airtime_ci95_low']:.3f}, "
            f"{comparison['relative_airtime_ci95_high']:.3f}], "
            f"gate {comparison['reliability_cost_gate']}"
        )


if __name__ == "__main__":
    main()
