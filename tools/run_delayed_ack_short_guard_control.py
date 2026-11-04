#!/usr/bin/env python3
"""Paired fixed-2-s FLOOD ACK controls with 1/2/4/8-s source R guards."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import argparse
import csv
import hashlib
import json
from pathlib import Path
import math
import sys
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_sr_experiment as sr
from lora_mesh_sim import Packet


BASELINE = "meshecho-dhr-flood-ack-delay"
ARMS = (BASELINE,) + tuple(
    f"meshecho-dhr-flood-ack-delay-guard{seconds}" for seconds in (1, 2, 4, 8)
)
SPLIT_SEEDS = {
    "smoke": (40000,),
    "explore": tuple(range(40001, 40021)),
}
SOURCE_FILES = (
    "lora_mesh_sim.py",
    "tools/run_fair_multihop_probe.py",
    "tools/run_sr_experiment.py",
    "tools/run_delayed_ack_short_guard_control.py",
    "docs/research/meshecho_dhr_design.md",
    "docs/research/meshecho_delayed_ack_control_design.md",
    "docs/research/meshecho_delayed_ack_short_guard_design.md",
    "tests/test_meshecho_dhr.py",
    "tests/test_delayed_flood_ack_control.py",
    "tests/test_delayed_ack_short_guard.py",
    "tests/test_delayed_ack_short_guard_runner.py",
    "tests/test_delayed_ack_short_guard_experiment.py",
)


@dataclass(frozen=True)
class GuardRun:
    row: dict[str, Any]
    flows: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    transmissions: list[dict[str, Any]]


class TracingSimulator(sr.RecordingSimulator):
    """Separate trace implementation for stock-current-code parity checks."""


class ExtendedTracingSimulator(TracingSimulator):
    def run(self, until_s: float) -> Any:
        return super().run(until_s + 30.0)


def seeds_for_split(split: str) -> tuple[int, ...]:
    try:
        return SPLIT_SEEDS[split]
    except KeyError as exc:
        raise ValueError(f"unknown short-guard split: {split}") from exc


def _capture(
    case: sr.SrCase, protocol: str, seed: int,
    simulator_type: type[sr.RecordingSimulator],
) -> GuardRun:
    captured: list[sr.RecordingSimulator] = []

    def create(*args: Any, **kwargs: Any) -> sr.RecordingSimulator:
        simulator = simulator_type(*args, **kwargs)
        captured.append(simulator)
        return simulator

    with patch.object(sr, "RecordingSimulator", create):
        result = sr.run_one_sr(case, protocol, seed, deadline_s=30.0)
    if len(captured) != 1:
        raise RuntimeError("SR runner did not create exactly one simulator")
    transmissions = [
        {
            "case": case.key, "protocol": protocol, "seed": seed,
            "tx_id": tx.tx_id, "sender": tx.sender,
            "start": tx.start, "end": tx.end, "packet": asdict(tx.packet),
        }
        for tx in captured[0].tx_history
    ]
    return GuardRun(result.row, result.flows, result.actions, transmissions)


def run_one(
    case: sr.SrCase, protocol: str, seed: int, *, extended: bool = False,
) -> GuardRun:
    if protocol not in ARMS:
        raise ValueError(f"unknown short-guard arm: {protocol}")
    simulator_type = ExtendedTracingSimulator if extended else TracingSimulator
    return _capture(case, protocol, seed, simulator_type)


def run_one_stock(case: sr.SrCase, seed: int) -> GuardRun:
    return _capture(case, BASELINE, seed, sr.RecordingSimulator)


def require_stock_parity(traced: GuardRun, stock: GuardRun) -> None:
    if (traced.row.get("protocol") != BASELINE
            or stock.row.get("protocol") != BASELINE
            or traced.row != stock.row or traced.flows != stock.flows
            or traced.actions != stock.actions
            or traced.transmissions != stock.transmissions):
        raise ValueError("15-s anchor differs from independent stock current-code run")


def _guard_seconds(protocol: str) -> int:
    if protocol == BASELINE:
        return 15
    if protocol not in ARMS:
        raise ValueError(f"unknown short-guard arm: {protocol}")
    return int(protocol.rsplit("guard", 1)[1])


def audit_guard_contract(
    run: GuardRun, *, observed_until_s: float | None = None,
) -> list[dict[str, Any]]:
    """Join source-local guard decisions to actual initial R and recovery F TXs."""
    protocol = run.row["protocol"]
    guard_s = _guard_seconds(protocol)
    cutoff = (float(run.row["drain_until_s"])
              if observed_until_s is None else observed_until_s)
    by_flow = {flow["flow_id"]: flow for flow in run.flows}
    if len(by_flow) != len(run.flows):
        raise ValueError("duplicate all-flow evidence")
    routed_flows = {flow_id: flow for flow_id, flow in by_flow.items()
                    if flow["source_action"] == "R"}
    initial_decisions: dict[int, str] = {}
    for action in run.actions:
        flow_id = action.get("flow_id")
        if action.get("event") != "decision" or flow_id not in routed_flows:
            continue
        flow = routed_flows[flow_id]
        if (flow_id in initial_decisions or action.get("action") not in {"R", "D"}
                or action.get("src") != flow["src"]
                or action.get("dst") != flow["dst"]):
            raise ValueError("invalid initial decision for routed DATA flow")
        initial_decisions[flow_id] = action["action"]
    if set(initial_decisions) != set(routed_flows):
        raise ValueError("missing initial decision for routed DATA flow")
    direct_r_flows = {flow_id for flow_id, action in initial_decisions.items()
                      if action == "R"}
    initial_r: dict[int, dict[str, Any]] = {}
    recovery_f: dict[int, dict[str, Any]] = {}
    for tx in run.transmissions:
        packet = tx["packet"]
        if packet["protocol"] != protocol:
            raise ValueError("physical TX has wrong protocol identity")
        if tx["sender"] != packet["origin"]:
            continue
        flow_id = packet["flow_id"]
        if packet["kind"] == "DATA" and packet["repair_index"] is None:
            flow = by_flow.get(flow_id)
            if flow is None or flow_id not in routed_flows:
                continue
            if flow_id in initial_r:
                raise ValueError("multiple initial R source TXs for one flow")
            if (packet["origin"] != flow["src"]
                    or packet["final_dst"] != flow["dst"]
                    or packet["request_id"] != flow_id
                    or not math.isclose(packet["created_at"], flow["enqueued_at"],
                                        rel_tol=0.0, abs_tol=1e-9)
                    or not packet["path"]
                    or packet["path"][0] != flow["src"]
                    or packet["path"][-1] != flow["dst"]):
                raise ValueError("initial R physical TX differs from flow identity")
            initial_r[flow_id] = tx
        elif packet["kind"] == "FLOOD" and packet["repair_index"] == 2:
            if flow_id in recovery_f:
                raise ValueError("multiple recovery F source TXs for one flow")
            recovery_f[flow_id] = tx
    guards: dict[int, dict[str, Any]] = {}
    for action in run.actions:
        if action.get("event") != "dhr_guard":
            continue
        flow_id = action["flow_id"]
        if flow_id in guards:
            raise ValueError("multiple R guards for one flow")
        if flow_id not in direct_r_flows:
            raise ValueError("R guard on noninitial R flow")
        tx = initial_r.get(flow_id)
        if tx is None:
            raise ValueError("R guard lacks an initial physical R TX")
        if not math.isclose(action["time"], tx["start"] + guard_s,
                            rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("R guard is not anchored to physical R TX start")
        if (action["src"] != tx["sender"]
                or action["dst"] != tx["packet"]["final_dst"]
                or bool(action["admitted"]) != (
                    action["selected_action"] == "F"
                )):
            raise ValueError("R guard action or selected F is inconsistent")
        guards[flow_id] = action
    recovery_events: dict[int, dict[str, Any]] = {}
    for action in run.actions:
        if action.get("event") != "dhr_recovery_tx":
            continue
        flow_id = action["flow_id"]
        if flow_id in recovery_events:
            raise ValueError("multiple recovery source action events")
        tx = recovery_f.get(flow_id)
        admitted = guards.get(flow_id)
        if (tx is None or admitted is None or not admitted["admitted"]
                or action["action"] != "F" or action["repair_index"] != 2
                or action["src"] != tx["sender"]
                or not math.isclose(action["time"], tx["start"],
                                    rel_tol=0.0, abs_tol=1e-9)
                or not math.isclose(action["end"], tx["end"],
                                    rel_tol=0.0, abs_tol=1e-9)
                or tx["start"] + 1e-9 < admitted["time"]):
            raise ValueError("recovery F event lacks an admitted physical TX")
        recovery_events[flow_id] = action
    if set(recovery_events) != set(recovery_f):
        raise ValueError("recovery F physical TX and action events differ")
    records = []
    for flow in run.flows:
        if flow["flow_id"] not in routed_flows:
            continue
        flow_id = flow["flow_id"]
        tx = initial_r.get(flow_id)
        decision = guards.get(flow_id)
        recovery = recovery_f.get(flow_id)
        direct_r = flow_id in direct_r_flows
        expected_guard_s = guard_s if direct_r else 15
        source_timeouts = [action for action in run.actions
                           if action.get("flow_id") == flow_id
                           and action.get("event") == "timeout"
                           and action.get("reason") == "source-ack-timeout"]
        if len(source_timeouts) > 1:
            raise ValueError("multiple source ACK timeouts for one routed flow")
        source_timeout_at = (source_timeouts[0]["time"]
                             if source_timeouts else None)
        if tx is None and (decision is not None or recovery is not None):
            raise ValueError("R guard or recovery lacks an initial physical R TX")
        if tx is not None:
            due = tx["start"] + expected_guard_s
            acked = flow["acked_at"]
            if direct_r and decision is not None and acked is not None and acked < due - 1e-9:
                raise ValueError("R guard fired after an earlier source ACK")
            if (direct_r and due <= cutoff + 1e-9 and decision is None
                    and (acked is None or acked > due + 1e-9)):
                raise ValueError("missing R guard after physical R TX start")
            if not direct_r:
                if decision is not None or recovery is not None:
                    raise ValueError("D-to-R fallback must not use DHR guard or recovery")
                if source_timeout_at is not None and (
                    not math.isclose(source_timeout_at, due,
                                     rel_tol=0.0, abs_tol=1e-9)
                    or (acked is not None and acked < due - 1e-9)
                ):
                    raise ValueError("D-to-R fallback source timeout is not 15 s")
                if (due <= cutoff + 1e-9 and source_timeout_at is None
                        and (acked is None or acked > due + 1e-9)):
                    raise ValueError("missing D-to-R fallback 15-s source timeout")
        records.append({
            "flow_id": flow_id, "src": flow["src"], "dst": flow["dst"],
            "guard_scope": "initial-R" if direct_r else "discovery-fallback-R",
            "r_guard_s": expected_guard_s,
            "initial_r_tx_id": tx["tx_id"] if tx else None,
            "initial_r_start_at": tx["start"] if tx else None,
            "source_timeout_at": source_timeout_at,
            "guard_at": decision["time"] if decision else None,
            "guard_admitted": decision["admitted"] if decision else None,
            "guard_rejection_reason": (
                decision["reason"] if decision and not decision["admitted"] else None
            ),
            "recovery_f_tx_id": recovery["tx_id"] if recovery else None,
            "recovery_f_start_at": recovery["start"] if recovery else None,
        })
    return records


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":")
    ).encode("ascii")).hexdigest()


def require_extended_prefix(primary: GuardRun, extended: GuardRun) -> None:
    shared = (
        "case", "case_config_sha256", "protocol", "seed",
        "generation_horizon_s", "application_deadline_s", "drain_until_s",
        "scheduled_trace_sha256", "scheduled_unicast_flows",
    )
    if (any(primary.row[name] != extended.row[name] for name in shared)
            or primary.transmissions
               != extended.transmissions[:len(primary.transmissions)]
            or primary.actions != extended.actions[:len(primary.actions)]):
        raise ValueError("extended replay changed the primary TX or action prefix")
    if len(primary.flows) != len(extended.flows):
        raise ValueError("extended replay changed the scheduled flow set")
    cutoff = float(primary.row["drain_until_s"])
    stable = (
        "case", "protocol", "seed", "flow_id", "src", "dst",
        "enqueued_at", "deadline_at", "registered", "ack_by_deadline",
        "delivery_by_deadline", "completion_delay_capped_s",
    )
    for before, after in zip(primary.flows, extended.flows):
        if (any(before.get(name) != after.get(name) for name in stable)
                or before["acked_at"] != (
                    after["acked_at"] if after["acked_at"] is not None
                    and after["acked_at"] <= cutoff else None
                )
                or before["delivered_at"] != (
                    after["delivered_at"] if after["delivered_at"] is not None
                    and after["delivered_at"] <= cutoff else None
                )
                or (before["delivered_at"] is not None
                    and before["first_data_delivery_kind"]
                    != after["first_data_delivery_kind"])):
            raise ValueError("extended replay changed a pre-cutoff flow outcome")


def physical_cost(
    transmissions: list[dict[str, Any]], cutoff_s: float,
    payload_bytes: int,
) -> dict[str, Any]:
    observed = [tx for tx in transmissions if tx["start"] <= cutoff_s]
    packets = []
    for tx in observed:
        fields = tx["packet"]
        packet = Packet(**{
            **fields,
            "path": tuple(fields["path"]),
            "learned_path": tuple(fields["learned_path"]),
        })
        packets.append((tx, packet))
    return {
        "tx_airtime_s": sum(tx["end"] - tx["start"] for tx in observed),
        "tx_bytes": sum(packet.wire_size_bytes(payload_bytes)
                        for _, packet in packets),
        "control_bytes": sum(packet.wire_size_bytes(payload_bytes)
                             for _, packet in packets if packet.is_control),
        "ack_bytes": sum(packet.wire_size_bytes(payload_bytes)
                         for _, packet in packets if packet.kind == "ACK"),
        "tx_count": len(observed),
        "ack_tx": sum(packet.kind == "ACK" for _, packet in packets),
        "flood_ack_tx": sum(
            packet.kind == "ACK" and packet.repair_index == 2
            for _, packet in packets
        ),
        "recovery_f_source_tx": sum(
            packet.kind == "FLOOD" and packet.repair_index == 2
            and tx["sender"] == packet.origin for tx, packet in packets
        ),
    }


def _require_flow_outcomes(run: GuardRun) -> None:
    flows, row = run.flows, run.row
    if (len(flows) != int(row["scheduled_unicast_flows"])
            or len({flow["flow_id"] for flow in flows}) != len(flows)):
        raise ValueError("all-flow outcome count differs from scheduled flows")
    scheduled = sorted((flow["enqueued_at"], flow["src"], flow["dst"],
                        flow["flow_id"]) for flow in flows)
    if _sha256_json(scheduled) != row["scheduled_trace_sha256"]:
        raise ValueError("all-flow scheduled trace differs from run")
    for flow in flows:
        deadline_at = flow["enqueued_at"] + 30.0
        ack = flow["acked_at"]
        delivery = flow["delivered_at"]
        if (not math.isclose(flow["deadline_at"], deadline_at,
                             rel_tol=0.0, abs_tol=1e-9)
                or flow["ack_by_deadline"] is not (
                    ack is not None and ack <= deadline_at
                )
                or flow["delivery_by_deadline"] is not (
                    delivery is not None and delivery <= deadline_at
                )
                or flow["late_ack"] is not (
                    ack is not None and ack > deadline_at
                )
                or flow["late_delivery"] is not (
                    delivery is not None and delivery > deadline_at
                )
                or not math.isclose(flow["completion_delay_capped_s"],
                                    ack - flow["enqueued_at"]
                                    if flow["ack_by_deadline"] else 30.0,
                                    rel_tol=0.0, abs_tol=1e-9)):
            raise ValueError("all-flow deadline outcome differs from timestamps")
    expected = {
        "registered_unicast_flows": sum(flow["registered"] for flow in flows),
        "ack_by_deadline": sum(flow["ack_by_deadline"] for flow in flows),
        "delivery_by_deadline": sum(flow["delivery_by_deadline"] for flow in flows),
        "late_ack_count": sum(flow["late_ack"] for flow in flows),
        "late_delivery_count": sum(flow["late_delivery"] for flow in flows),
        "ack_pdr_deadline": sum(flow["ack_by_deadline"] for flow in flows) / len(flows),
        "destination_pdr_deadline": sum(flow["delivery_by_deadline"]
                                        for flow in flows) / len(flows),
        "mean_completion_delay_capped_s": sum(
            flow["completion_delay_capped_s"] for flow in flows
        ) / len(flows),
    }
    for name, expected_value in expected.items():
        if not math.isclose(float(row[name]), expected_value,
                            rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"all-flow outcome differs from run metric: {name}")


def run_row(primary: GuardRun, extended: GuardRun, case: sr.SrCase) -> dict[str, Any]:
    require_extended_prefix(primary, extended)
    if (float(primary.row["generation_horizon_s"]) != case.duration_s
            or float(primary.row["application_deadline_s"]) != 30.0
            or float(primary.row["drain_until_s"]) != case.duration_s + 30.0
            or primary.row["case_config_sha256"] != _sha256_json(asdict(case))):
        raise ValueError("run uses wrong case, deadline, or TX cutoff")
    _require_flow_outcomes(primary)
    records = audit_guard_contract(primary)
    audit_guard_contract(extended, observed_until_s=case.duration_s + 60.0)
    main = physical_cost(primary.transmissions, case.duration_s + 30.0,
                         case.payload_bytes)
    long = physical_cost(extended.transmissions, case.duration_s + 60.0,
                         case.payload_bytes)
    reported_fields = (
        ("tx_airtime_s", "whole_network_tx_airtime_s"),
        ("tx_bytes", "windowed_tx_bytes"),
        ("control_bytes", "windowed_control_bytes"),
        ("ack_bytes", "windowed_ack_bytes"),
        ("tx_count", "windowed_tx_count"),
        ("ack_tx", "windowed_ack_tx"),
        ("flood_ack_tx", "windowed_dhr_flood_ack_tx"),
        ("recovery_f_source_tx", "windowed_dhr_recovery_f_source_tx"),
    )
    for physical, reported in reported_fields:
        if not math.isclose(main[physical], float(primary.row[reported]),
                            rel_tol=0.0, abs_tol=1e-8):
            raise ValueError(f"physical TX cost differs from run metric: {reported}")
    guard_events = [event for event in primary.actions
                    if event.get("event") == "dhr_guard"]
    recovery_events = [event for event in primary.actions
                       if event.get("event") == "dhr_recovery_tx"]
    if (len(guard_events) != int(primary.row["dhr_guard_events"])
            or len(recovery_events) != int(primary.row["dhr_recovery_f_tx"])):
        raise ValueError("guard or recovery action count differs from run metric")
    return {
        **primary.row,
        "guard_s": _guard_seconds(primary.row["protocol"]),
        "extended_tx_airtime_s": long["tx_airtime_s"],
        "extended_tx_bytes": long["tx_bytes"],
        "extended_control_bytes": long["control_bytes"],
        "extended_ack_bytes": long["ack_bytes"],
        "extended_tx_count": long["tx_count"],
        "extended_ack_tx": long["ack_tx"],
        "extended_flood_ack_tx": long["flood_ack_tx"],
        "extended_recovery_f_source_tx": long["recovery_f_source_tx"],
        "post_cutoff_tx": long["tx_count"] - main["tx_count"],
        "post_cutoff_airtime_s": long["tx_airtime_s"] - main["tx_airtime_s"],
        "post_cutoff_bytes": long["tx_bytes"] - main["tx_bytes"],
        "physical_initial_r_starts": sum(
            item["initial_r_tx_id"] is not None
            and item["initial_r_start_at"] <= case.duration_s + 30.0
            for item in records
        ),
        "discovery_fallback_r_starts": sum(
            item["guard_scope"] == "discovery-fallback-R"
            and item["initial_r_tx_id"] is not None
            and item["initial_r_start_at"] <= case.duration_s + 30.0
            for item in records
        ),
        "physical_recovery_f_starts": sum(
            item["recovery_f_tx_id"] is not None
            and item["recovery_f_start_at"] <= case.duration_s + 30.0
            for item in records
        ),
        "guard_source_busy_rejections": sum(
            item["guard_rejection_reason"] == "source-busy" for item in records
        ),
        "guard_deadline_budget_rejections": sum(
            item["guard_rejection_reason"] == "deadline-budget" for item in records
        ),
        "guard_admitted_unstarted_f": sum(
            item["guard_admitted"] is True
            and item["recovery_f_tx_id"] is None for item in records
        ),
        "full_tx_trace_sha256": _sha256_json(primary.transmissions),
        "extended_tx_trace_sha256": _sha256_json(extended.transmissions),
        "full_action_trace_sha256": _sha256_json(primary.actions),
        "extended_action_trace_sha256": _sha256_json(extended.actions),
        "full_flow_trace_sha256": _sha256_json(primary.flows),
        "guard_trace_sha256": _sha256_json(records),
    }


def summarize_pairs(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_seed: dict[int, dict[str, dict[str, Any]]] = {}
    for row in rows:
        seed, arm = int(row["seed"]), row["protocol"]
        arms = by_seed.setdefault(seed, {})
        if arm not in ARMS or arm in arms:
            raise ValueError(f"duplicate or unknown short-guard arm: {seed} {arm}")
        arms[arm] = row
    if not by_seed:
        raise ValueError("paired short-guard summary requires at least one seed")
    per_seed = []
    shared = (
        "case", "case_config_sha256", "scheduled_trace_sha256",
        "scheduled_unicast_flows", "application_deadline_s",
    )
    for seed, arms in sorted(by_seed.items()):
        if set(arms) != set(ARMS):
            raise ValueError(f"missing paired short-guard arm: seed {seed}")
        baseline = arms[BASELINE]
        for arm in ARMS[1:]:
            focus = arms[arm]
            if any(baseline[name] != focus[name] for name in shared):
                raise ValueError(f"paired case or application trace differs: seed {seed}")
            for field in (
                "whole_network_tx_airtime_s", "windowed_tx_bytes",
                "extended_tx_airtime_s", "extended_tx_bytes",
            ):
                if float(baseline[field]) <= 0:
                    raise ValueError(f"zero baseline TX cost: seed {seed} {field}")
            per_seed.append({
                "case": baseline["case"], "seed": seed,
                "focus_protocol": arm, "comparator": BASELINE,
                "scheduled_trace_sha256": baseline["scheduled_trace_sha256"],
                "ack_pdr_gain": float(focus["ack_pdr_deadline"])
                                - float(baseline["ack_pdr_deadline"]),
                "destination_pdr_gain": float(focus["destination_pdr_deadline"])
                                        - float(baseline["destination_pdr_deadline"]),
                "capped_ack_delay_delta_s": float(focus["mean_completion_delay_capped_s"])
                                            - float(baseline["mean_completion_delay_capped_s"]),
                "relative_airtime_cost": float(focus["whole_network_tx_airtime_s"])
                                         / float(baseline["whole_network_tx_airtime_s"]) - 1,
                "relative_byte_cost": float(focus["windowed_tx_bytes"])
                                      / float(baseline["windowed_tx_bytes"]) - 1,
                "extended_relative_airtime_cost": float(focus["extended_tx_airtime_s"])
                                                  / float(baseline["extended_tx_airtime_s"]) - 1,
                "extended_relative_byte_cost": float(focus["extended_tx_bytes"])
                                               / float(baseline["extended_tx_bytes"]) - 1,
                "recovery_f_starts_delta": int(focus["physical_recovery_f_starts"])
                                           - int(baseline["physical_recovery_f_starts"]),
                "late_ack_delta": int(focus["late_ack_count"])
                                  - int(baseline["late_ack_count"]),
                "source_busy_rejection_delta": int(focus["guard_source_busy_rejections"])
                                               - int(baseline["guard_source_busy_rejections"]),
                "deadline_budget_rejection_delta": int(focus["guard_deadline_budget_rejections"])
                                                  - int(baseline["guard_deadline_budget_rejections"]),
            })
    if len({item["case"] for item in per_seed}) != 1:
        raise ValueError("paired cases differ across seeds")
    paired = []
    fields = (
        ("ack_pdr_gain", "ack_pdr"),
        ("destination_pdr_gain", "destination_pdr"),
        ("capped_ack_delay_delta_s", "capped_ack_delay"),
        ("relative_airtime_cost", "relative_airtime"),
        ("relative_byte_cost", "relative_byte"),
        ("extended_relative_airtime_cost", "extended_relative_airtime"),
        ("extended_relative_byte_cost", "extended_relative_byte"),
        ("recovery_f_starts_delta", "recovery_f_starts"),
        ("late_ack_delta", "late_ack"),
        ("source_busy_rejection_delta", "source_busy_rejection"),
        ("deadline_budget_rejection_delta", "deadline_budget_rejection"),
    )
    for arm in ARMS[1:]:
        paired_arm = [item for item in per_seed if item["focus_protocol"] == arm]
        result: dict[str, Any] = {
            "case": paired_arm[0]["case"], "focus_protocol": arm,
            "comparator": BASELINE, "n_seeds": len(paired_arm),
        }
        for field, prefix in fields:
            mean, low, high = sr.paired_ci95([item[field] for item in paired_arm])
            result[field] = mean
            result[f"{prefix}_ci95_low"] = low
            result[f"{prefix}_ci95_high"] = high
        paired.append(result)
    return per_seed, paired


def input_hashes() -> dict[str, str]:
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
            for name in SOURCE_FILES}


def artifact_paths(prefix: Path) -> dict[str, Path]:
    return {
        "runs": Path(f"{prefix}.runs.csv"),
        "per_seed": Path(f"{prefix}.per_seed.csv"),
        "paired": Path(f"{prefix}.paired.csv"),
        "flows": Path(f"{prefix}.flows.jsonl"),
        "extended_flows": Path(f"{prefix}.extended_flows.jsonl"),
        "actions": Path(f"{prefix}.actions.jsonl"),
        "extended_actions": Path(f"{prefix}.extended_actions.jsonl"),
        "tx": Path(f"{prefix}.tx.jsonl"),
        "extended_tx": Path(f"{prefix}.extended_tx.jsonl"),
        "guards": Path(f"{prefix}.guards.jsonl"),
        "manifest": Path(f"{prefix}.manifest.json"),
    }


def ensure_paths_available(prefix: Path) -> None:
    for path in artifact_paths(prefix).values():
        if path.exists():
            raise FileExistsError(f"short-guard artifact already exists: {path}")


GUARD_FIELDS = (
    "guard_scope", "r_guard_s", "initial_r_tx_id", "initial_r_start_at",
    "source_timeout_at", "guard_at", "guard_admitted",
    "guard_rejection_reason", "recovery_f_tx_id", "recovery_f_start_at",
)


def _tag(item: dict[str, Any], run: GuardRun, split: str) -> dict[str, Any]:
    return {**item, "case": run.row["case"], "protocol": run.row["protocol"],
            "seed": int(run.row["seed"]), "seed_split": split}


def _enriched_flows(
    run: GuardRun, split: str, guards: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_flow = {item["flow_id"]: item for item in guards}
    return [
        _tag({**flow, **{field: by_flow.get(flow["flow_id"], {}).get(field)
                         for field in GUARD_FIELDS}}, run, split)
        for flow in run.flows
    ]


def write_artifacts(
    prefix: Path, case: sr.SrCase, split: str,
    pairs: list[tuple[GuardRun, GuardRun]],
    stock_runs: dict[int, GuardRun], source_sha256: dict[str, str],
) -> dict[str, Path]:
    ensure_paths_available(prefix)
    if source_sha256 != input_hashes():
        raise RuntimeError("short-guard source inputs changed before artifact write")
    by_key: dict[tuple[int, str], tuple[GuardRun, GuardRun]] = {}
    for primary, extended in pairs:
        seed, arm = int(primary.row["seed"]), primary.row["protocol"]
        key = (seed, arm)
        if (key in by_key or arm not in ARMS or primary.row["case"] != case.key
                or primary.row["case_config_sha256"] != _sha256_json(asdict(case))):
            raise ValueError("invalid short-guard run matrix")
        require_extended_prefix(primary, extended)
        by_key[key] = (primary, extended)
    seeds = sorted({seed for seed, _ in by_key})
    if (not seeds or len(by_key) != len(seeds) * len(ARMS)
            or set(stock_runs) != set(seeds)):
        raise ValueError("short-guard evidence needs five arms and stock per seed")
    for seed in seeds:
        require_stock_parity(by_key[(seed, BASELINE)][0], stock_runs[seed])
    ordered = [by_key[(seed, arm)] for seed in seeds for arm in ARMS]
    rows = [{**run_row(primary, extended, case), "seed_split": split}
            for primary, extended in ordered]
    per_seed, paired = summarize_pairs(rows)
    per_seed = [{**item, "seed_split": split} for item in per_seed]
    paired = [{**item, "seed_split": split} for item in paired]
    records: dict[str, list[dict[str, Any]]] = {
        key: [] for key in artifact_paths(prefix)
        if key not in {"runs", "per_seed", "paired", "manifest"}
    }
    for primary, extended in ordered:
        guards = audit_guard_contract(primary)
        records["flows"].extend(_enriched_flows(primary, split, guards))
        for key, items in (
            ("extended_flows", extended.flows),
            ("actions", primary.actions),
            ("extended_actions", extended.actions),
            ("tx", primary.transmissions),
            ("extended_tx", extended.transmissions),
            ("guards", guards),
        ):
            records[key].extend(_tag(item, primary, split) for item in items)
    if source_sha256 != input_hashes():
        raise RuntimeError("short-guard source inputs changed during experiment")
    paths = artifact_paths(prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    for key, values in (("runs", rows), ("per_seed", per_seed), ("paired", paired)):
        with paths[key].open("x", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(values[0]))
            writer.writeheader()
            writer.writerows(values)
    for key, values in records.items():
        with paths[key].open("x", encoding="utf-8") as handle:
            for item in values:
                handle.write(json.dumps(item, sort_keys=True,
                                        separators=(",", ":")) + "\n")
    manifest = {
        "case": asdict(case), "protocols": list(ARMS), "seeds": seeds,
        "seed_split": split, "runs": len(rows),
        "application_deadline_s": 30.0,
        "generation_horizon_s": case.duration_s,
        "primary_tx_start_cutoff_s": case.duration_s + 30.0,
        "extended_tx_start_cutoff_s": case.duration_s + 60.0,
        "fixed_flood_ack_delay_s": 2.0,
        "r_guard_seconds": {arm: _guard_seconds(arm) for arm in ARMS},
        "complete_packet_toa_for_included_tx": True,
        "stock_current_code_parity": True,
        "extended_cost_window_limited": True,
        "source_sha256": source_sha256,
        "artifact_sha256": {
            key: hashlib.sha256(path.read_bytes()).hexdigest()
            for key, path in paths.items() if key != "manifest"
        },
    }
    with paths["manifest"].open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    return paths


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _same_csv_record(saved: dict[str, str], expected: dict[str, Any]) -> bool:
    return saved == {key: "" if value is None else str(value)
                     for key, value in expected.items()}


def validate_manifest(
    manifest_path: Path, expected_split: str,
    expected_source_sha256: dict[str, str], *,
    case: sr.SrCase | None = None, seeds: tuple[int, ...] | None = None,
    strict_replay: bool = False,
) -> None:
    case = case or sr.SR_CASES["recurring_fading"]
    seeds = seeds if seeds is not None else seeds_for_split(expected_split)
    if not manifest_path.name.endswith(".manifest.json"):
        raise ValueError("short-guard manifest needs .manifest.json suffix")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    paths = artifact_paths(Path(str(manifest_path)[:-len(".manifest.json")]))
    expected_static = {
        "case": asdict(case), "protocols": list(ARMS), "seeds": list(seeds),
        "seed_split": expected_split, "runs": len(seeds) * len(ARMS),
        "application_deadline_s": 30.0,
        "generation_horizon_s": case.duration_s,
        "primary_tx_start_cutoff_s": case.duration_s + 30.0,
        "extended_tx_start_cutoff_s": case.duration_s + 60.0,
        "fixed_flood_ack_delay_s": 2.0,
        "r_guard_seconds": {arm: _guard_seconds(arm) for arm in ARMS},
        "complete_packet_toa_for_included_tx": True,
        "stock_current_code_parity": True,
        "extended_cost_window_limited": True,
        "source_sha256": expected_source_sha256,
    }
    if any(manifest.get(key) != value for key, value in expected_static.items()):
        raise ValueError("short-guard manifest differs from frozen configuration")
    if expected_source_sha256 != input_hashes():
        raise ValueError("short-guard source hashes differ from current code")
    expected_artifacts = set(paths) - {"manifest"}
    if (not isinstance(manifest.get("artifact_sha256"), dict)
            or set(manifest["artifact_sha256"]) != expected_artifacts):
        raise ValueError("short-guard artifact hash manifest is incomplete")
    for key in expected_artifacts:
        if (not paths[key].is_file()
                or hashlib.sha256(paths[key].read_bytes()).hexdigest()
                != manifest["artifact_sha256"][key]):
            raise ValueError(f"short-guard artifact hash mismatch: {key}")
    with paths["runs"].open(newline="", encoding="utf-8") as handle:
        saved_rows = list(csv.DictReader(handle))
    with paths["per_seed"].open(newline="", encoding="utf-8") as handle:
        saved_per_seed = list(csv.DictReader(handle))
    with paths["paired"].open(newline="", encoding="utf-8") as handle:
        saved_paired = list(csv.DictReader(handle))
    if len(saved_rows) != len(seeds) * len(ARMS):
        raise ValueError("short-guard saved run matrix is incomplete")
    row_by_key = {(int(row["seed"]), row["protocol"]): row for row in saved_rows}
    expected_keys = {(seed, arm) for seed in seeds for arm in ARMS}
    if set(row_by_key) != expected_keys or len(row_by_key) != len(saved_rows):
        raise ValueError("short-guard saved run matrix has duplicate or alien arms")
    record_kinds = (
        "flows", "extended_flows", "actions", "extended_actions",
        "tx", "extended_tx", "guards",
    )
    grouped: dict[str, dict[tuple[int, str], list[dict[str, Any]]]] = {}
    for kind in record_kinds:
        by_key: dict[tuple[int, str], list[dict[str, Any]]] = {}
        for item in _read_jsonl(paths[kind]):
            key = (int(item["seed"]), item["protocol"])
            if (key not in expected_keys or item.get("case") != case.key
                    or item.get("seed_split") != expected_split):
                raise ValueError(f"short-guard {kind} has alien evidence")
            by_key.setdefault(key, []).append(item)
        grouped[kind] = by_key
    case_hash = _sha256_json(asdict(case))
    for key, saved in row_by_key.items():
        if (saved["case"] != case.key or saved["seed_split"] != expected_split
                or saved["case_config_sha256"] != case_hash
                or float(saved["generation_horizon_s"]) != case.duration_s
                or float(saved["application_deadline_s"]) != 30.0
                or float(saved["drain_until_s"]) != case.duration_s + 30.0):
            raise ValueError("short-guard saved run differs from frozen case")
        strip = lambda item: {name: value for name, value in item.items()
                              if name != "seed_split"}
        saved_flows = grouped["flows"].get(key, [])
        primary_flows = [
            {name: value for name, value in item.items()
             if name not in GUARD_FIELDS and name != "seed_split"}
            for item in saved_flows
        ]
        extended_flows = [strip(item) for item in grouped["extended_flows"].get(key, [])]
        primary = GuardRun(
            saved, primary_flows,
            [strip(item) for item in grouped["actions"].get(key, [])],
            [strip(item) for item in grouped["tx"].get(key, [])],
        )
        extended = GuardRun(
            saved, extended_flows,
            [strip(item) for item in grouped["extended_actions"].get(key, [])],
            [strip(item) for item in grouped["extended_tx"].get(key, [])],
        )
        expected = {**run_row(primary, extended, case), "seed_split": expected_split}
        if not _same_csv_record(saved, expected):
            raise ValueError(f"short-guard run metric, TX, flow, or hash mismatch: {key}")
        guards = audit_guard_contract(primary)
        if (grouped["guards"].get(key, [])
                != [_tag(item, primary, expected_split) for item in guards]):
            raise ValueError("short-guard physical guard evidence differs from TX")
        if saved_flows != _enriched_flows(primary, expected_split, guards):
            raise ValueError("short-guard per-flow guard evidence differs from TX")
    expected_per_seed, expected_paired = summarize_pairs(saved_rows)
    expected_per_seed = [{**item, "seed_split": expected_split}
                         for item in expected_per_seed]
    expected_paired = [{**item, "seed_split": expected_split}
                       for item in expected_paired]
    if (len(saved_per_seed) != len(expected_per_seed)
            or any(not _same_csv_record(saved, expected)
                   for saved, expected in zip(saved_per_seed, expected_per_seed))
            or len(saved_paired) != len(expected_paired)
            or any(not _same_csv_record(saved, expected)
                   for saved, expected in zip(saved_paired, expected_paired))):
        raise ValueError("short-guard paired evidence differs from saved runs")
    if strict_replay:
        for seed in seeds:
            for arm in ARMS:
                key = (seed, arm)
                primary = run_one(case, arm, seed)
                extended = run_one(case, arm, seed, extended=True)
                expected = {**run_row(primary, extended, case),
                            "seed_split": expected_split}
                if not _same_csv_record(row_by_key[key], expected):
                    raise ValueError(f"strict replay metrics differ: {seed} {arm}")
                guards = audit_guard_contract(primary)
                evidence = {
                    "flows": _enriched_flows(primary, expected_split, guards),
                    "extended_flows": [_tag(item, primary, expected_split)
                                       for item in extended.flows],
                    "actions": [_tag(item, primary, expected_split)
                                for item in primary.actions],
                    "extended_actions": [_tag(item, primary, expected_split)
                                         for item in extended.actions],
                    "tx": [_tag(item, primary, expected_split)
                           for item in primary.transmissions],
                    "extended_tx": [_tag(item, primary, expected_split)
                                    for item in extended.transmissions],
                    "guards": [_tag(item, primary, expected_split)
                               for item in guards],
                }
                if any(_sha256_json(evidence[kind])
                       != _sha256_json(grouped[kind].get(key, []))
                       for kind in record_kinds):
                    raise ValueError(f"strict replay evidence differs: {seed} {arm}")
            require_stock_parity(
                run_one(case, BASELINE, seed), run_one_stock(case, seed)
            )
        if input_hashes() != expected_source_sha256:
            raise ValueError("strict replay source hashes changed during validation")


def run_experiment(
    split: str, out_prefix: Path, *, smoke_manifest: Path | None = None,
) -> dict[str, Path]:
    seeds = seeds_for_split(split)
    if split == "explore" and smoke_manifest is None:
        raise ValueError("explore requires a smoke manifest")
    ensure_paths_available(out_prefix)
    case = sr.SR_CASES["recurring_fading"]
    source_sha256 = input_hashes()
    if split == "explore":
        validate_manifest(
            smoke_manifest, "smoke", source_sha256, strict_replay=True,
        )
    pairs: list[tuple[GuardRun, GuardRun]] = []
    stock_runs: dict[int, GuardRun] = {}
    for seed in seeds:
        for arm in ARMS:
            primary = run_one(case, arm, seed)
            extended = run_one(case, arm, seed, extended=True)
            if (primary.row.get("case") != case.key
                    or primary.row.get("protocol") != arm
                    or int(primary.row.get("seed", -1)) != seed):
                raise ValueError("short-guard runner returned wrong case, arm, or seed")
            require_extended_prefix(primary, extended)
            pairs.append((primary, extended))
        stock = run_one_stock(case, seed)
        require_stock_parity(pairs[-len(ARMS)][0], stock)
        stock_runs[seed] = stock
    if input_hashes() != source_sha256:
        raise RuntimeError("short-guard source inputs changed during experiment")
    return write_artifacts(
        out_prefix, case, split, pairs, stock_runs, source_sha256,
    )


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=tuple(SPLIT_SEEDS), required=True)
    parser.add_argument("--out-prefix", type=Path, required=True)
    parser.add_argument("--smoke-manifest", type=Path)
    args = parser.parse_args(argv)
    if args.split == "explore" and args.smoke_manifest is None:
        parser.error("explore requires --smoke-manifest")
    paths = run_experiment(
        args.split, args.out_prefix, smoke_manifest=args.smoke_manifest,
    )
    print(f"Short-guard control manifest: {paths['manifest']}")


if __name__ == "__main__":
    main()
