#!/usr/bin/env python3
"""Independent paired experiment for fixed-2-s ACK and one same-path repeat."""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import Packet
from tools import run_sr_experiment as sr


BASELINE = "meshecho-dhr-flood-ack-delay"
REPEAT = "meshecho-dhr-flood-ack-delay-repeat"
ARMS = (BASELINE, REPEAT)
SOURCE_FILES = (
    "lora_mesh_sim.py",
    "tools/run_fair_multihop_probe.py",
    "tools/run_sr_experiment.py",
    "tools/run_delayed_ack_repeat_control.py",
    "docs/research/meshecho_delayed_ack_repeat_control_design.md",
    "tests/test_delayed_ack_repeat_control.py",
    "tests/test_delayed_ack_repeat_runner.py",
    "tests/test_delayed_ack_repeat_runner_experiment.py",
)


SPLIT_SEEDS = {
    "smoke": (41000,),
    "explore": tuple(range(41001, 41021)),
}


@dataclass(frozen=True)
class RepeatRun:
    row: dict[str, Any]
    flows: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    transmissions: list[dict[str, Any]]
    first_flood_receipts: list[dict[str, Any]]


class TracingSimulator(sr.RecordingSimulator):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.first_flood_receipts: dict[int, dict[str, Any]] = {}

    def handle_tx_end(self, tx: Any) -> None:
        packet = tx.packet
        target = packet.final_dst
        eligible = (
            packet.kind == "FLOOD"
            and target in self.nodes
            and packet.flow_id not in self.first_flood_receipts
            and packet.flood_key not in self.protocol.seen_floods[target]
        )
        before = len(self.protocol.action_events) if eligible else 0
        super().handle_tx_end(tx)
        if eligible and any(
            event.get("event") == "dhr_destination_rx"
            and event.get("flow_id") == packet.flow_id
            and event.get("dst") == target
            for event in self.protocol.action_events[before:]
        ):
            self.first_flood_receipts[packet.flow_id] = {
                "flow_id": packet.flow_id,
                "decode_at": self.now,
                "tx_id": tx.tx_id,
                "path": list(packet.path + (target,)),
                "repair_index": packet.repair_index,
            }


class ExtendedTracingSimulator(TracingSimulator):
    def run(self, until_s: float) -> Any:
        return super().run(until_s + 30.0)


def _capture(
    case: sr.SrCase, protocol: str, seed: int,
    simulator_type: type[sr.RecordingSimulator],
) -> RepeatRun:
    captured: list[sr.RecordingSimulator] = []

    def create(*args: Any, **kwargs: Any) -> sr.RecordingSimulator:
        sim = simulator_type(*args, **kwargs)
        captured.append(sim)
        return sim

    with patch.object(sr, "RecordingSimulator", create):
        result = sr.run_one_sr(case, protocol, seed, deadline_s=30.0)
    if len(captured) != 1:
        raise RuntimeError("SR runner did not create exactly one simulator")
    sim = captured[0]
    transmissions = [
        {"case": case.key, "protocol": protocol, "seed": seed,
         "tx_id": tx.tx_id, "sender": tx.sender,
         "start": tx.start, "end": tx.end, "packet": asdict(tx.packet)}
        for tx in sim.tx_history
    ]
    receipts = list(getattr(sim, "first_flood_receipts", {}).values())
    return RepeatRun(result.row, result.flows, result.actions, transmissions, receipts)


def seeds_for_split(split: str) -> tuple[int, ...]:
    try:
        return SPLIT_SEEDS[split]
    except KeyError as exc:
        raise ValueError(f"unknown repeat-control split: {split}") from exc


def run_one(
    case: sr.SrCase, protocol: str, seed: int, *, extended: bool = False,
) -> RepeatRun:
    if protocol not in ARMS:
        raise ValueError(f"unknown delayed-ACK repeat arm: {protocol}")
    return _capture(case, protocol, seed,
                    ExtendedTracingSimulator if extended else TracingSimulator)


def run_one_stock(case: sr.SrCase, seed: int) -> RepeatRun:
    return _capture(case, BASELINE, seed, sr.RecordingSimulator)


def require_stock_parity(traced: RepeatRun, stock: RepeatRun) -> None:
    if (traced.row.get("protocol") != BASELINE
            or stock.row.get("protocol") != BASELINE
            or traced.row.get("seed") != stock.row.get("seed")
            or traced.row != stock.row
            or traced.flows != stock.flows
            or traced.actions != stock.actions
            or traced.transmissions != stock.transmissions):
        raise ValueError("traced baseline differs from independent stock current-code run")


def audit_ack_contract(run: RepeatRun) -> list[dict[str, Any]]:
    """Bind destination ACK actions to physical TXs for each first FLOOD decode."""
    by_tx_id = {tx["tx_id"]: tx for tx in run.transmissions}
    if len(by_tx_id) != len(run.transmissions):
        raise ValueError("duplicate physical TX identifier")
    data_ack_origins = {
        (packet["flow_id"], packet["request_id"], packet["repair_index"],
         tuple(packet["path"]), tx["end"])
        for tx in run.transmissions
        for packet in (tx["packet"],)
        if (packet["kind"] == "DATA" and len(packet["path"]) >= 2
            and packet["final_dst"] == packet["path"][-1]
            and tx["sender"] == packet["path"][-2]
            and packet["path_index"] == len(packet["path"]) - 2)
    }
    destination_rx = {
        (event["flow_id"], event["dst"], event["repair_index"], event["time"])
        for event in run.actions if event.get("event") == "dhr_destination_rx"
    }
    repeat_events = [event for event in run.actions
                     if event.get("event") == "delayed_ack_repeat_tx"]
    drop_events = [event for event in run.actions
                   if event.get("event") == "delayed_ack_repeat_drop"]
    if run.row["protocol"] == BASELINE and (repeat_events or drop_events):
        raise ValueError("baseline emitted a repeat event")
    seen_events: set[int] = set()
    seen_drops: set[int] = set()
    records: list[dict[str, Any]] = []
    seen_flows: set[int] = set()
    active_records: list[tuple[int, float]] = []
    cutoff_s = float(run.row["drain_until_s"]) + 30.0
    for receipt in run.first_flood_receipts:
        flow_id = receipt["flow_id"]
        if flow_id in seen_flows:
            raise ValueError("multiple first FLOOD decodes for one flow")
        if records and receipt["decode_at"] < records[-1]["first_flood_decode_at"]:
            raise ValueError("first FLOOD receipts are out of event order")
        seen_flows.add(flow_id)
        flood = by_tx_id.get(receipt["tx_id"])
        if (flood is None or flood["packet"]["kind"] != "FLOOD"
                or flood["packet"]["flow_id"] != flow_id
                or flood["packet"]["repair_index"] != receipt["repair_index"]
                or list(flood["packet"]["path"]) + [flood["packet"]["final_dst"]]
                   != receipt["path"]
                or not math.isclose(flood["end"], receipt["decode_at"],
                                    rel_tol=0.0, abs_tol=1e-9)):
            raise ValueError("first FLOOD receipt lacks physical TX")
        rx_events = [event for event in run.actions
                     if event.get("event") == "dhr_destination_rx"
                     and event.get("flow_id") == flow_id
                     and event.get("dst") == receipt["path"][-1]
                     and event.get("repair_index") == receipt["repair_index"]
                     and math.isclose(event["time"], receipt["decode_at"],
                                      rel_tol=0.0, abs_tol=1e-9)]
        if len(rx_events) != 1:
            raise ValueError("first FLOOD receipt lacks unique destination RX action")
        acks = []
        for tx in run.transmissions:
            packet = tx["packet"]
            if (packet["kind"] != "ACK" or tx["sender"] != receipt["path"][-1]
                    or packet["flow_id"] != flow_id):
                continue
            data_origin = (
                flow_id, packet["request_id"], packet["repair_index"],
                tuple(packet["path"]), packet["created_at"],
            )
            if (packet["origin"] == receipt["path"][-1]
                    and packet["final_dst"] == receipt["path"][0]
                    and data_origin in data_ack_origins
                    and (flow_id, receipt["path"][-1], packet["repair_index"],
                         packet["created_at"]) in destination_rx):
                continue
            if (packet["origin"] != receipt["path"][-1]
                    or packet["final_dst"] != receipt["path"][0]
                    or packet["request_id"] != flow_id
                    or packet["repair_index"] != receipt["repair_index"]
                    or tuple(packet["path"]) != tuple(receipt["path"])
                    or not math.isclose(packet["created_at"], receipt["decode_at"],
                                        rel_tol=0.0, abs_tol=1e-9)):
                raise ValueError("unbound destination ACK for first FLOOD decode")
            acks.append(tx)
        acks.sort(key=lambda tx: (tx["start"], tx["tx_id"]))
        maximum = 1 if run.row["protocol"] == BASELINE else 2
        if len(acks) > maximum:
            raise ValueError("more than one repeat ACK per flow")
        first = acks[0] if acks else None
        second = acks[1] if len(acks) == 2 else None
        if (first is not None
                and first["packet"]["path_index"] != len(receipt["path"]) - 2):
            raise ValueError("first FLOOD ACK has wrong reverse path index")
        if first is not None and first["start"] + 1e-9 < receipt["decode_at"] + 2.0:
            raise ValueError("first FLOOD ACK starts before its 2-s timer")
        events = [(index, event) for index, event in enumerate(repeat_events)
                  if event.get("flow_id") == flow_id
                  and event.get("dst") == receipt["path"][-1]]
        drops = [(index, event) for index, event in enumerate(drop_events)
                 if event.get("flow_id") == flow_id
                 and event.get("dst") == receipt["path"][-1]]
        if len(events) > 1:
            raise ValueError("more than one repeat action per flow")
        if len(drops) > 1:
            raise ValueError("more than one repeat drop per flow")
        if bool(second) != bool(events):
            raise ValueError("repeat action and physical TX do not match")
        if first is None and receipt["decode_at"] + 2.0 <= cutoff_s:
            raise ValueError("missing first FLOOD ACK before extended cutoff")
        if second is not None and drops:
            raise ValueError("repeat ACK also has a drop action")
        repeat_due = first["end"] + 0.5 if first is not None else None
        window_end = receipt["decode_at"] + 10.0
        if drops:
            index, drop = drops[0]
            seen_drops.add(index)
            if drop.get("reason") == "active-capacity":
                active_count = sum(
                    dst == receipt["path"][-1] and release_at >= receipt["decode_at"]
                    for dst, release_at in active_records
                )
                if (not math.isclose(drop["time"], receipt["decode_at"],
                                     rel_tol=0.0, abs_tol=1e-9)
                        or active_count < 8):
                    raise ValueError("capacity drop lacks eight active repeat records")
            elif drop.get("reason") == "local-window":
                if (repeat_due is None or drop["time"] + 1e-9 < repeat_due
                        or drop["time"] <= window_end):
                    raise ValueError("local-window drop lacks expired physical start")
            else:
                raise ValueError("unknown repeat drop reason")
        if (run.row["protocol"] == REPEAT and first is not None
                and second is None and not drops
                and (repeat_due <= cutoff_s or repeat_due > window_end)):
            raise ValueError("missing repeat ACK without a drop action")
        if second is not None:
            index, event = events[0]
            seen_events.add(index)
            if second["packet"] != first["packet"]:
                raise ValueError("repeat ACK is not the same wire packet")
            if (not math.isclose(event["time"], second["start"],
                                 rel_tol=0.0, abs_tol=1e-9)
                    or tuple(event["path"]) != tuple(receipt["path"])):
                raise ValueError("repeat action differs from physical TX or path")
            if second["start"] + 1e-9 < first["end"] + 0.5:
                raise ValueError("repeat ACK starts before actual first TX end + 0.5 s")
            if second["start"] > receipt["decode_at"] + 10.0 + 1e-9:
                raise ValueError("repeat ACK starts after local 10-s window")
        if not drops or drops[0][1].get("reason") != "active-capacity":
            release_at = window_end
            if repeat_due is not None:
                release_at = min(
                    window_end,
                    receipt["decode_at"] + 2.0
                    if repeat_due > window_end else repeat_due,
                )
            active_records.append((receipt["path"][-1], release_at))
        records.append({
            "flow_id": flow_id,
            "first_flood_decode_at": receipt["decode_at"],
            "first_flood_tx_id": receipt["tx_id"],
            "first_flood_path": receipt["path"],
            "first_flood_repair_index": receipt["repair_index"],
            "first_ack_tx_id": first["tx_id"] if first else None,
            "first_ack_start_at": first["start"] if first else None,
            "first_ack_end_at": first["end"] if first else None,
            "repeat_ack_tx_id": second["tx_id"] if second else None,
            "repeat_ack_start_at": second["start"] if second else None,
            "repeat_ack_end_at": second["end"] if second else None,
            "repeat_queue_lag_s": (second["start"] - first["end"] - 0.5
                                    if second else None),
        })
    if len(seen_events) != len(repeat_events):
        raise ValueError("orphan repeat ACK action")
    if len(seen_drops) != len(drop_events):
        raise ValueError("orphan repeat drop action")
    return records


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":")
    ).encode("ascii")).hexdigest()


def require_extended_prefix(primary: RepeatRun, extended: RepeatRun) -> None:
    shared = (
        "case", "case_config_sha256", "protocol", "seed",
        "generation_horizon_s", "application_deadline_s", "drain_until_s",
        "scheduled_trace_sha256", "scheduled_unicast_flows",
    )
    cutoff = float(primary.row["drain_until_s"])
    if (any(primary.row[name] != extended.row[name] for name in shared)
            or primary.transmissions != extended.transmissions[:len(primary.transmissions)]
            or primary.first_flood_receipts
               != extended.first_flood_receipts[:len(primary.first_flood_receipts)]):
        raise ValueError("extended replay changed the primary run or TX prefix")
    if primary.actions != extended.actions[:len(primary.actions)]:
        raise ValueError("extended replay changed the pre-cutoff action prefix")
    stable_flow_fields = (
        "case", "protocol", "seed", "flow_id", "src", "dst",
        "enqueued_at", "deadline_at", "registered",
        "ack_by_deadline", "delivery_by_deadline", "completion_delay_capped_s",
    )
    if len(primary.flows) != len(extended.flows):
        raise ValueError("extended replay changed the scheduled flow set")
    for before, after in zip(primary.flows, extended.flows):
        if (any(before.get(name) != after.get(name) for name in stable_flow_fields)
                or before["acked_at"] != (
                    after["acked_at"] if after["acked_at"] is not None
                    and after["acked_at"] <= cutoff else None
                )
                or before["delivered_at"] != (
                    after["delivered_at"] if after["delivered_at"] is not None
                    and after["delivered_at"] <= cutoff else None
                )
                or (before["delivered_at"] is not None
                    and before.get("first_data_delivery_kind")
                    != after.get("first_data_delivery_kind"))):
            raise ValueError("extended replay changed pre-cutoff flow outcomes")


def physical_cost(
    transmissions: list[dict[str, Any]], cutoff_s: float,
    payload_bytes: int,
) -> dict[str, Any]:
    observed = [tx for tx in transmissions if tx["start"] <= cutoff_s]
    packets = [
        (tx, Packet(**{
            **tx["packet"],
            "path": tuple(tx["packet"]["path"]),
            "learned_path": tuple(tx["packet"]["learned_path"]),
        }))
        for tx in observed
    ]
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
    }


def _require_flow_outcomes(run: RepeatRun) -> None:
    flows = run.flows
    row = run.row
    if len(flows) != int(row["scheduled_unicast_flows"]):
        raise ValueError("all-flow outcome count differs from scheduled flows")
    if len({flow["flow_id"] for flow in flows}) != len(flows):
        raise ValueError("duplicate all-flow outcome")
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
                    ack is not None and ack <= deadline_at)
                or flow["delivery_by_deadline"] is not (
                    delivery is not None and delivery <= deadline_at)
                or flow["late_ack"] is not (
                    ack is not None and ack > deadline_at)
                or flow["late_delivery"] is not (
                    delivery is not None and delivery > deadline_at)
                or not math.isclose(flow["completion_delay_capped_s"],
                                    ack - flow["enqueued_at"]
                                    if flow["ack_by_deadline"] else 30.0,
                                    rel_tol=0.0, abs_tol=1e-9)):
            raise ValueError("all-flow deadline outcome differs from timestamps")
    expected = {
        "ack_by_deadline": sum(flow["ack_by_deadline"] for flow in flows),
        "delivery_by_deadline": sum(flow["delivery_by_deadline"] for flow in flows),
        "late_ack_count": sum(flow["late_ack"] for flow in flows),
        "late_delivery_count": sum(flow["late_delivery"] for flow in flows),
        "registered_unicast_flows": sum(flow["registered"] for flow in flows),
        "ack_pdr_deadline": sum(flow["ack_by_deadline"] for flow in flows) / len(flows),
        "destination_pdr_deadline": sum(flow["delivery_by_deadline"] for flow in flows)
        / len(flows),
        "mean_completion_delay_capped_s": sum(
            flow["completion_delay_capped_s"] for flow in flows) / len(flows),
    }
    for name, value in expected.items():
        if not math.isclose(float(row[name]), value, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError(f"all-flow outcome differs from run metric: {name}")


def run_row(primary: RepeatRun, extended: RepeatRun, case: sr.SrCase) -> dict[str, Any]:
    require_extended_prefix(primary, extended)
    if (float(primary.row["generation_horizon_s"]) != case.duration_s
            or float(primary.row["application_deadline_s"]) != 30.0
            or float(primary.row["drain_until_s"]) != case.duration_s + 30.0):
        raise ValueError("run uses the wrong 30-s flow deadline or TX cutoff")
    _require_flow_outcomes(primary)
    main = physical_cost(primary.transmissions, case.duration_s + 30.0,
                         case.payload_bytes)
    for physical, reported in (
        ("tx_airtime_s", "whole_network_tx_airtime_s"),
        ("tx_bytes", "windowed_tx_bytes"),
        ("control_bytes", "windowed_control_bytes"),
        ("ack_bytes", "windowed_ack_bytes"),
        ("tx_count", "windowed_tx_count"),
        ("ack_tx", "windowed_ack_tx"),
    ):
        if not math.isclose(main[physical], float(primary.row[reported]),
                            rel_tol=0.0, abs_tol=1e-8):
            raise ValueError(f"physical TX cost differs from run metric: {reported}")
    records = audit_ack_contract(extended)
    long = physical_cost(extended.transmissions, case.duration_s + 60.0,
                         case.payload_bytes)
    return {
        **primary.row,
        "extended_tx_airtime_s": long["tx_airtime_s"],
        "extended_tx_bytes": long["tx_bytes"],
        "extended_control_bytes": long["control_bytes"],
        "extended_ack_bytes": long["ack_bytes"],
        "extended_tx_count": long["tx_count"],
        "extended_ack_tx": long["ack_tx"],
        "post_cutoff_tx": long["tx_count"] - main["tx_count"],
        "post_cutoff_airtime_s": long["tx_airtime_s"] - main["tx_airtime_s"],
        "post_cutoff_bytes": long["tx_bytes"] - main["tx_bytes"],
        "first_flood_receipts": len(extended.first_flood_receipts),
        "repeat_ack_tx": sum(item["repeat_ack_start_at"] is not None
                             and item["repeat_ack_start_at"] <= case.duration_s + 60.0
                             for item in records),
        "repeat_drop_events": sum(event.get("event") == "delayed_ack_repeat_drop"
                                  for event in extended.actions),
        "unstarted_first_ack_at_660": sum(
            item["first_ack_start_at"] is None
            or item["first_ack_start_at"] > case.duration_s + 60.0
            for item in records
        ),
        "full_tx_trace_sha256": _sha256_json(primary.transmissions),
        "extended_tx_trace_sha256": _sha256_json(extended.transmissions),
        "full_action_trace_sha256": _sha256_json(primary.actions),
        "extended_action_trace_sha256": _sha256_json(extended.actions),
        "full_flow_trace_sha256": _sha256_json(primary.flows),
    }


def summarize_pairs(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_seed: dict[int, dict[str, dict[str, Any]]] = {}
    for row in rows:
        seed = int(row["seed"])
        arm = row["protocol"]
        arms = by_seed.setdefault(seed, {})
        if arm not in ARMS or arm in arms:
            raise ValueError(f"duplicate or unknown repeat-control arm: {seed} {arm}")
        arms[arm] = row
    if not by_seed:
        raise ValueError("paired repeat-control summary requires at least one seed")
    per_seed = []
    shared = (
        "case", "case_config_sha256", "scheduled_trace_sha256",
        "scheduled_unicast_flows", "application_deadline_s",
    )
    for seed, arms in sorted(by_seed.items()):
        if set(arms) != set(ARMS):
            raise ValueError(f"missing paired repeat-control arm: seed {seed}")
        baseline, repeat = arms[BASELINE], arms[REPEAT]
        if any(baseline[name] != repeat[name] for name in shared):
            raise ValueError(f"paired case or application trace differs: seed {seed}")
        for field in ("whole_network_tx_airtime_s", "windowed_tx_bytes",
                      "extended_tx_airtime_s", "extended_tx_bytes"):
            if float(baseline[field]) <= 0:
                raise ValueError(f"zero baseline TX cost: seed {seed} {field}")
        per_seed.append({
            "case": baseline["case"], "seed": seed,
            "focus_protocol": REPEAT, "comparator": BASELINE,
            "scheduled_trace_sha256": baseline["scheduled_trace_sha256"],
            "ack_pdr_gain": float(repeat["ack_pdr_deadline"])
                            - float(baseline["ack_pdr_deadline"]),
            "destination_pdr_gain": float(repeat["destination_pdr_deadline"])
                                    - float(baseline["destination_pdr_deadline"]),
            "relative_airtime_cost": float(repeat["whole_network_tx_airtime_s"])
                                     / float(baseline["whole_network_tx_airtime_s"]) - 1,
            "relative_byte_cost": float(repeat["windowed_tx_bytes"])
                                  / float(baseline["windowed_tx_bytes"]) - 1,
            "extended_relative_airtime_cost": float(repeat["extended_tx_airtime_s"])
                                              / float(baseline["extended_tx_airtime_s"]) - 1,
            "extended_relative_byte_cost": float(repeat["extended_tx_bytes"])
                                           / float(baseline["extended_tx_bytes"]) - 1,
            "capped_ack_delay_delta_s": float(repeat["mean_completion_delay_capped_s"])
                                        - float(baseline["mean_completion_delay_capped_s"]),
        })
    if len({item["case"] for item in per_seed}) != 1:
        raise ValueError("paired cases differ across seeds")
    paired: dict[str, Any] = {
        "case": per_seed[0]["case"], "focus_protocol": REPEAT,
        "comparator": BASELINE, "n_seeds": len(per_seed),
    }
    for field, prefix in (
        ("ack_pdr_gain", "ack_pdr"),
        ("destination_pdr_gain", "destination_pdr"),
        ("relative_airtime_cost", "relative_airtime"),
        ("relative_byte_cost", "relative_byte"),
        ("extended_relative_airtime_cost", "extended_relative_airtime"),
        ("extended_relative_byte_cost", "extended_relative_byte"),
        ("capped_ack_delay_delta_s", "capped_ack_delay"),
    ):
        mean, low, high = sr.paired_ci95([item[field] for item in per_seed])
        paired[field] = mean
        paired[f"{prefix}_ci95_low"] = low
        paired[f"{prefix}_ci95_high"] = high
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
        "actions": Path(f"{prefix}.actions.jsonl"),
        "extended_actions": Path(f"{prefix}.extended_actions.jsonl"),
        "tx": Path(f"{prefix}.tx.jsonl"),
        "extended_tx": Path(f"{prefix}.extended_tx.jsonl"),
        "receipts": Path(f"{prefix}.receipts.jsonl"),
        "extended_receipts": Path(f"{prefix}.extended_receipts.jsonl"),
        "repeat_events": Path(f"{prefix}.repeat_events.jsonl"),
        "manifest": Path(f"{prefix}.manifest.json"),
    }


def ensure_paths_available(prefix: Path) -> None:
    for path in artifact_paths(prefix).values():
        if path.exists():
            raise FileExistsError(f"repeat-control artifact already exists: {path}")


def _tag(item: dict[str, Any], run: RepeatRun, split: str) -> dict[str, Any]:
    return {**item, "case": run.row["case"], "protocol": run.row["protocol"],
            "seed": run.row["seed"], "seed_split": split}


def write_artifacts(
    prefix: Path, case: sr.SrCase, split: str,
    pairs: list[tuple[RepeatRun, RepeatRun]],
    stock_runs: dict[int, RepeatRun], source_sha256: dict[str, str],
) -> dict[str, Path]:
    ensure_paths_available(prefix)
    if source_sha256 != input_hashes():
        raise RuntimeError("repeat-control source inputs changed before artifact write")
    by_key: dict[tuple[int, str], tuple[RepeatRun, RepeatRun]] = {}
    for primary, extended in pairs:
        seed, arm = int(primary.row["seed"]), primary.row["protocol"]
        key = (seed, arm)
        if (key in by_key or arm not in ARMS or primary.row["case"] != case.key
                or primary.row["case_config_sha256"] != _sha256_json(asdict(case))):
            raise ValueError("invalid repeat-control run matrix")
        require_extended_prefix(primary, extended)
        by_key[key] = (primary, extended)
    seeds = sorted({seed for seed, _ in by_key})
    if (not seeds or len(by_key) != len(seeds) * len(ARMS)
            or set(stock_runs) != set(seeds)):
        raise ValueError("repeat-control evidence needs both arms and stock per seed")
    for seed in seeds:
        require_stock_parity(by_key[(seed, BASELINE)][0], stock_runs[seed])
    ordered = [by_key[(seed, arm)] for seed in seeds for arm in ARMS]
    rows = [{**run_row(primary, extended, case), "seed_split": split}
            for primary, extended in ordered]
    per_seed, paired = summarize_pairs(rows)
    per_seed = [{**item, "seed_split": split} for item in per_seed]
    paired = {**paired, "seed_split": split}
    records: dict[str, list[dict[str, Any]]] = {
        key: [] for key in artifact_paths(prefix) if key not in {
            "runs", "per_seed", "paired", "manifest"
        }
    }
    for primary, extended in ordered:
        ack_by_flow = {item["flow_id"]: item for item in audit_ack_contract(extended)}
        for flow in primary.flows:
            evidence = ack_by_flow.get(flow["flow_id"], {})
            records["flows"].append(_tag({
                **flow,
                **{key: evidence.get(key) for key in (
                    "first_flood_decode_at", "first_flood_tx_id", "first_flood_path",
                    "first_flood_repair_index", "first_ack_tx_id",
                    "first_ack_start_at", "first_ack_end_at", "repeat_ack_tx_id",
                    "repeat_ack_start_at", "repeat_ack_end_at", "repeat_queue_lag_s",
                )},
            }, primary, split))
        for key, items in (
            ("actions", primary.actions),
            ("extended_actions", extended.actions),
            ("tx", primary.transmissions),
            ("extended_tx", extended.transmissions),
            ("receipts", primary.first_flood_receipts),
            ("extended_receipts", extended.first_flood_receipts),
            ("repeat_events", [item for item in extended.actions
                               if item.get("event") in {
                                   "delayed_ack_repeat_tx", "delayed_ack_repeat_drop"
                               }]),
        ):
            records[key].extend(_tag(item, primary, split) for item in items)
    if source_sha256 != input_hashes():
        raise RuntimeError("repeat-control source inputs changed during experiment")
    paths = artifact_paths(prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    for key, values in (("runs", rows), ("per_seed", per_seed),
                        ("paired", [paired])):
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
        "same_path_repeat_wait_s": 0.5,
        "repeat_local_window_s": 10.0,
        "complete_packet_toa_for_included_tx": True,
        "stock_current_code_parity": True,
        "extended_cost_window_limited": True,
        "unstarted_first_ack_at_extended_cutoff": any(
            row["unstarted_first_ack_at_660"] for row in rows
        ),
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


FLOW_ACK_FIELDS = (
    "first_flood_decode_at", "first_flood_tx_id", "first_flood_path",
    "first_flood_repair_index", "first_ack_tx_id", "first_ack_start_at",
    "first_ack_end_at", "repeat_ack_tx_id", "repeat_ack_start_at",
    "repeat_ack_end_at", "repeat_queue_lag_s",
)


def _core_flow(flow: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in flow.items()
            if key not in FLOW_ACK_FIELDS and key != "seed_split"}


def validate_manifest(
    manifest_path: Path, expected_split: str,
    expected_source_sha256: dict[str, str], *,
    case: sr.SrCase | None = None, seeds: tuple[int, ...] | None = None,
    strict_replay: bool = False,
) -> None:
    case = case or sr.SR_CASES["recurring_fading"]
    seeds = seeds if seeds is not None else seeds_for_split(expected_split)
    if not manifest_path.name.endswith(".manifest.json"):
        raise ValueError("repeat-control manifest needs .manifest.json suffix")
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
        "same_path_repeat_wait_s": 0.5,
        "repeat_local_window_s": 10.0,
        "complete_packet_toa_for_included_tx": True,
        "stock_current_code_parity": True,
        "extended_cost_window_limited": True,
        "source_sha256": expected_source_sha256,
    }
    if any(manifest.get(name) != value for name, value in expected_static.items()):
        raise ValueError("repeat-control manifest differs from frozen configuration")
    if expected_source_sha256 != input_hashes():
        raise ValueError("repeat-control source hashes differ from current code")
    expected_artifacts = set(paths) - {"manifest"}
    artifact_hashes = manifest.get("artifact_sha256")
    if (not isinstance(artifact_hashes, dict)
            or set(artifact_hashes) != expected_artifacts):
        raise ValueError("repeat-control artifact hashes are incomplete")
    for key in expected_artifacts:
        if (not paths[key].is_file()
                or hashlib.sha256(paths[key].read_bytes()).hexdigest()
                != artifact_hashes[key]):
            raise ValueError(f"repeat-control artifact hash mismatch: {key}")
    with paths["runs"].open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    with paths["per_seed"].open(newline="", encoding="utf-8") as handle:
        saved_per_seed = list(csv.DictReader(handle))
    with paths["paired"].open(newline="", encoding="utf-8") as handle:
        saved_paired = list(csv.DictReader(handle))
    expected_keys = {(seed, arm) for seed in seeds for arm in ARMS}
    row_by_key = {(int(row["seed"]), row["protocol"]): row for row in rows}
    if len(rows) != len(expected_keys) or set(row_by_key) != expected_keys:
        raise ValueError("repeat-control saved run matrix is incomplete or duplicated")
    raw = {key: _read_jsonl(paths[key]) for key in (
        "flows", "actions", "extended_actions", "tx", "extended_tx",
        "receipts", "extended_receipts", "repeat_events",
    )}
    grouped: dict[str, dict[tuple[int, str], list[dict[str, Any]]]] = {}
    for kind, items in raw.items():
        by_key: dict[tuple[int, str], list[dict[str, Any]]] = {}
        for item in items:
            key = (int(item["seed"]), item["protocol"])
            if (key not in expected_keys or item.get("case") != case.key
                    or item.get("seed_split") != expected_split):
                raise ValueError(f"repeat-control {kind} contains alien evidence")
            by_key.setdefault(key, []).append(item)
        grouped[kind] = by_key
    case_hash = _sha256_json(asdict(case))
    for key in sorted(expected_keys):
        row = row_by_key[key]
        if (row["case"] != case.key
                or row["case_config_sha256"] != case_hash
                or row["seed_split"] != expected_split
                or float(row["generation_horizon_s"]) != case.duration_s
                or float(row["application_deadline_s"]) != 30.0
                or float(row["drain_until_s"]) != case.duration_s + 30.0):
            raise ValueError("repeat-control saved run differs from frozen case")
        strip = lambda item: {name: value for name, value in item.items()
                              if name != "seed_split"}
        strip_receipt = lambda item: {name: value for name, value in item.items()
                                      if name not in {
                                          "case", "protocol", "seed", "seed_split"
                                      }}
        flows = grouped["flows"].get(key, [])
        primary = RepeatRun(
            row, [_core_flow(item) for item in flows],
            [strip(item) for item in grouped["actions"].get(key, [])],
            [strip(item) for item in grouped["tx"].get(key, [])],
            [strip_receipt(item) for item in grouped["receipts"].get(key, [])],
        )
        extended = RepeatRun(
            row, primary.flows,
            [strip(item) for item in grouped["extended_actions"].get(key, [])],
            [strip(item) for item in grouped["extended_tx"].get(key, [])],
            [strip_receipt(item)
             for item in grouped["extended_receipts"].get(key, [])],
        )
        repeat_events = [item for item in grouped["extended_actions"].get(key, [])
                         if item.get("event") in {
                             "delayed_ack_repeat_tx", "delayed_ack_repeat_drop"
                         }]
        if repeat_events != grouped["repeat_events"].get(key, []):
            raise ValueError("repeat events differ from complete action trace")
        expected_row = {**run_row(primary, extended, case),
                        "seed_split": expected_split}
        if not _same_csv_record(row, expected_row):
            raise ValueError("repeat-control TX, action, flow or cost evidence differs")
        ack_by_flow = {item["flow_id"]: item for item in audit_ack_contract(extended)}
        if len(flows) != int(row["scheduled_unicast_flows"]):
            raise ValueError("all scheduled flow records are required")
        for flow in flows:
            evidence = ack_by_flow.get(flow["flow_id"], {})
            if any(flow.get(name) != evidence.get(name) for name in FLOW_ACK_FIELDS):
                raise ValueError("saved per-flow ACK evidence differs from physical TX")
    expected_per_seed, expected_paired = summarize_pairs(rows)
    expected_per_seed = [{**item, "seed_split": expected_split}
                         for item in expected_per_seed]
    expected_paired = {**expected_paired, "seed_split": expected_split}
    if (len(saved_per_seed) != len(expected_per_seed)
            or any(not _same_csv_record(saved, expected)
                   for saved, expected in zip(saved_per_seed, expected_per_seed))
            or len(saved_paired) != 1
            or not _same_csv_record(saved_paired[0], expected_paired)):
        raise ValueError("repeat-control paired statistics differ from saved runs")
    if manifest.get("unstarted_first_ack_at_extended_cutoff") is not any(
        int(row["unstarted_first_ack_at_660"]) for row in rows
    ):
        raise ValueError("repeat-control extended-cost tail flag differs")
    if strict_replay:
        for seed in seeds:
            for arm in ARMS:
                primary = run_one(case, arm, seed)
                extended = run_one(case, arm, seed, extended=True)
                key = (seed, arm)
                expected_row = {**run_row(primary, extended, case),
                                "seed_split": expected_split}
                if not _same_csv_record(row_by_key[key], expected_row):
                    raise ValueError(f"strict replay metrics differ: {seed} {arm}")
                for kind, replayed in (
                    ("flows", primary.flows), ("actions", primary.actions),
                    ("extended_actions", extended.actions),
                    ("tx", primary.transmissions),
                    ("extended_tx", extended.transmissions),
                    ("receipts", primary.first_flood_receipts),
                    ("extended_receipts", extended.first_flood_receipts),
                ):
                    saved = grouped[kind].get(key, [])
                    if kind == "flows":
                        saved = [_core_flow(item) for item in saved]
                    elif "receipts" in kind:
                        saved = [{name: value for name, value in item.items()
                                  if name not in {
                                      "case", "protocol", "seed", "seed_split"
                                  }} for item in saved]
                    else:
                        saved = [{name: value for name, value in item.items()
                                  if name != "seed_split"} for item in saved]
                    if _sha256_json(saved) != _sha256_json(replayed):
                        raise ValueError(f"strict replay {kind} differs: {seed} {arm}")
            require_stock_parity(run_one(case, BASELINE, seed),
                                 run_one_stock(case, seed))
        if expected_source_sha256 != input_hashes():
            raise ValueError("strict replay source inputs changed")


def run_experiment(split: str, out_prefix: Path, *, smoke_manifest: Path | None = None):
    seeds = seeds_for_split(split)
    if split == "explore" and smoke_manifest is None:
        raise ValueError("explore requires a smoke manifest")
    ensure_paths_available(out_prefix)
    case = sr.SR_CASES["recurring_fading"]
    source_sha256 = input_hashes()
    if split == "explore":
        validate_manifest(smoke_manifest, "smoke", source_sha256,
                          strict_replay=True)
    pairs: list[tuple[RepeatRun, RepeatRun]] = []
    stocks: dict[int, RepeatRun] = {}
    for seed in seeds:
        for arm in ARMS:
            primary = run_one(case, arm, seed)
            extended = run_one(case, arm, seed, extended=True)
            if (primary.row.get("case") != case.key
                    or primary.row.get("protocol") != arm
                    or int(primary.row.get("seed", -1)) != seed):
                raise ValueError("repeat-control runner returned wrong case, arm or seed")
            run_row(primary, extended, case)
            pairs.append((primary, extended))
        stock = run_one_stock(case, seed)
        require_stock_parity(pairs[-2][0], stock)
        stocks[seed] = stock
    if input_hashes() != source_sha256:
        raise RuntimeError("repeat-control source inputs changed during experiment")
    return write_artifacts(out_prefix, case, split, pairs, stocks, source_sha256)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=tuple(SPLIT_SEEDS), required=True)
    parser.add_argument("--out-prefix", type=Path, required=True)
    parser.add_argument("--smoke-manifest", type=Path)
    args = parser.parse_args(argv)
    if args.split == "explore" and args.smoke_manifest is None:
        parser.error("explore requires --smoke-manifest")
    paths = run_experiment(
        args.split, args.out_prefix, smoke_manifest=args.smoke_manifest
    )
    print(f"Repeat-control manifest: {paths['manifest']}")


if __name__ == "__main__":
    main()
