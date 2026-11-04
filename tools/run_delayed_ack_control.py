#!/usr/bin/env python3
"""Frozen paired fixed-delay FLOOD ACK timing control."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from bisect import bisect_left
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_sr_experiment as sr


SOURCE_FILES = (
    "lora_mesh_sim.py",
    "tools/run_fair_multihop_probe.py",
    "tools/run_sr_experiment.py",
    "tools/run_delayed_ack_control.py",
    "docs/research/meshecho_dhr_design.md",
    "docs/research/meshecho_delayed_ack_control_design.md",
    "tests/test_meshecho_dhr.py",
    "tests/test_delayed_flood_ack_control.py",
    "tests/test_delayed_ack_control_runner.py",
)

SPLIT_SEEDS = {
    "smoke": (38000,),
    "explore": tuple(range(38001, 38021)),
}
IMMEDIATE = "meshecho-dhr-flood"
DELAYED = "meshecho-dhr-flood-ack-delay"
ARMS = (DELAYED, IMMEDIATE)


@dataclass(frozen=True)
class ControlRun:
    row: dict[str, Any]
    flows: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    transmissions: list[dict[str, Any]]
    flood_receipts: list[dict[str, Any]]
    half_duplex_failures: int = 0


class TracingSimulator(sr.RecordingSimulator):
    """Instrumentation must leave the fixed-F simulator behavior unchanged."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.first_flood_receipts: dict[int, dict[str, Any]] = {}
        self.half_duplex_failures = 0

    def try_receive(self, tx: Any, receiver: int) -> Any:
        if (receiver != tx.sender
                and self.receiver_is_transmitting(receiver, tx.start, tx.end)):
            self.half_duplex_failures += 1
        return super().try_receive(tx, receiver)

    def handle_tx_end(self, tx: Any) -> None:
        packet = tx.packet
        target = packet.final_dst
        eligible = (
            packet.kind == "FLOOD" and target in self.nodes
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


class ExtendedDrainSimulator(TracingSimulator):
    """Fresh symmetric replay for post-primary-cutoff physical TX cost."""

    def run(self, until_s: float) -> Any:
        return super().run(until_s + 30.0)


def seeds_for_split(split: str) -> tuple[int, ...]:
    try:
        return SPLIT_SEEDS[split]
    except KeyError as exc:
        raise ValueError(f"unknown delayed-ACK split: {split}") from exc


def _run_with_simulator(
    case: sr.SrCase, protocol: str, seed: int, simulator_type: type[sr.RecordingSimulator],
) -> ControlRun:
    captured: list[sr.RecordingSimulator] = []

    def create_simulator(*args: Any, **kwargs: Any) -> sr.RecordingSimulator:
        simulator = simulator_type(*args, **kwargs)
        captured.append(simulator)
        return simulator

    with patch.object(sr, "RecordingSimulator", create_simulator):
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
    receipts = list(getattr(captured[0], "first_flood_receipts", {}).values())
    return ControlRun(
        result.row, result.flows, result.actions, transmissions, receipts,
        getattr(captured[0], "half_duplex_failures", 0),
    )


def run_one_traced(case: sr.SrCase, protocol: str, seed: int) -> ControlRun:
    if protocol not in ARMS:
        raise ValueError(f"unknown delayed-ACK arm: {protocol}")
    return _run_with_simulator(case, protocol, seed, TracingSimulator)


def run_one_stock(case: sr.SrCase, protocol: str, seed: int) -> ControlRun:
    if protocol != IMMEDIATE:
        raise ValueError("stock parity is only defined for the immediate arm")
    return _run_with_simulator(case, protocol, seed, sr.RecordingSimulator)


def run_one_extended(case: sr.SrCase, protocol: str, seed: int) -> ControlRun:
    if protocol not in ARMS:
        raise ValueError(f"unknown delayed-ACK arm: {protocol}")
    return _run_with_simulator(case, protocol, seed, ExtendedDrainSimulator)


def require_stock_parity(traced: ControlRun, stock: ControlRun) -> None:
    if (traced.row["protocol"] != IMMEDIATE or stock.row["protocol"] != IMMEDIATE
            or traced.row["seed"] != stock.row["seed"]):
        raise ValueError("stock parity received wrong arm or seed")
    if traced.row != stock.row:
        raise ValueError("immediate run metrics differ from stock fixed-F")
    if traced.flows != stock.flows:
        raise ValueError("immediate per-flow evidence differs from stock fixed-F")
    if traced.actions != stock.actions:
        raise ValueError("immediate source actions differ from stock fixed-F")
    if traced.transmissions != stock.transmissions:
        raise ValueError("immediate complete TX trace differs from stock fixed-F")


def require_extended_prefix(primary: ControlRun, extended: ControlRun) -> None:
    shared = (
        "case", "case_config_sha256", "protocol", "seed",
        "generation_horizon_s", "application_deadline_s", "drain_until_s",
        "scheduled_trace_sha256", "scheduled_unicast_flows",
    )
    if (any(primary.row[field] != extended.row[field] for field in shared)
            or primary.transmissions != extended.transmissions[:len(primary.transmissions)]
            or primary.flood_receipts != [
                item for item in extended.flood_receipts
                if item["decode_at"] <= float(primary.row["drain_until_s"])
            ]):
        raise ValueError("extended replay changes the primary complete TX prefix")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":")
    ).encode("ascii")).hexdigest()


def count_half_duplex_from_tx(
    transmissions: list[dict[str, Any]], node_count: int, cutoff_s: float,
) -> int:
    """Rebuild failed TX-end receive attempts from on-air node intervals."""
    by_sender: dict[int, list[dict[str, Any]]] = {node: [] for node in range(node_count)}
    for tx in transmissions:
        by_sender[tx["sender"]].append(tx)
    starts = {}
    ends = {}
    for sender, items in by_sender.items():
        ordered = sorted(items, key=lambda item: item["start"])
        starts[sender] = [item["start"] for item in ordered]
        ends[sender] = [item["end"] for item in ordered]
    failures = 0
    for tx in transmissions:
        if tx["end"] > cutoff_s:
            continue
        for receiver in range(node_count):
            if receiver == tx["sender"]:
                continue
            index = bisect_left(starts[receiver], tx["end"]) - 1
            failures += index >= 0 and ends[receiver][index] > tx["start"]
    return failures


def run_row(primary: ControlRun, extended: ControlRun, cutoff_s: float) -> dict[str, Any]:
    require_extended_prefix(primary, extended)
    if float(primary.row["drain_until_s"]) != cutoff_s:
        raise ValueError("primary TX cutoff differs from the frozen drain")
    source_events = [
        event for event in primary.actions
        if event.get("event") in {
            "decision", "timeout", "commit", "dhr_guard", "dhr_recovery_tx",
            "dhr_source_ack_rx", "dhr_state_drop",
        }
    ]
    source_actions = {
        "flows": [(flow["flow_id"], flow["source_action"]) for flow in primary.flows],
        "events": source_events,
    }
    return {
        **primary.row,
        **extended_sensitivity(primary, extended, cutoff_s, cutoff_s + 30.0),
        "half_duplex_failures": primary.half_duplex_failures,
        "first_flood_receipts": len(primary.flood_receipts),
        "primary_future_start_tx": sum(
            item["start"] > cutoff_s for item in primary.transmissions
        ),
        "full_tx_trace_sha256": _sha256_json(primary.transmissions),
        "extended_tx_trace_sha256": _sha256_json(extended.transmissions),
        "source_action_trace_sha256": _sha256_json(source_actions),
        "full_action_trace_sha256": _sha256_json(primary.actions),
    }


def extended_sensitivity(
    primary: ControlRun, extended: ControlRun, cutoff_s: float, extended_until_s: float,
) -> dict[str, Any]:
    """Charge physical TX starts and identify unstarted first-FLOOD ACKs."""
    if extended_until_s <= cutoff_s:
        raise ValueError("extended drain must follow the primary cutoff")
    tx = extended.transmissions
    ack_starts = [
        (ack["start"] if (ack := _first_ack_for_receipt(item, tx)) else None)
        for item in primary.flood_receipts if item["decode_at"] <= cutoff_s
    ]
    return {
        "extended_airtime_s": sum(
            item["end"] - item["start"] for item in tx
            if item["start"] <= extended_until_s
        ),
        "post_cutoff_airtime_s": sum(
            item["end"] - item["start"] for item in tx
            if cutoff_s < item["start"] <= extended_until_s
        ),
        "post_cutoff_tx": sum(cutoff_s < item["start"] <= extended_until_s
                              for item in tx),
        "post_cutoff_ack_tx": sum(
            item["packet"]["kind"] == "ACK"
            and cutoff_s < item["start"] <= extended_until_s for item in tx
        ),
        "pending_first_flood_ack_at_cutoff": sum(
            when is None or when > cutoff_s for when in ack_starts
        ),
        "first_flood_ack_unstarted_at_extended_cutoff": sum(
            when is None or when > extended_until_s for when in ack_starts
        ),
        "tx_start_after_extended_cutoff": sum(
            item["start"] > extended_until_s for item in tx
        ),
    }


def summarize_pairs(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Pair only identical topology/application traces, then use paired t CIs."""
    by_seed: dict[int, dict[str, dict[str, Any]]] = {}
    for row in rows:
        seed = int(row["seed"])
        arms = by_seed.setdefault(seed, {})
        protocol = row["protocol"]
        if protocol not in ARMS or protocol in arms:
            raise ValueError(f"duplicate or unknown delayed-ACK arm: {seed} {protocol}")
        arms[protocol] = row
    if not by_seed:
        raise ValueError("paired summary requires at least one seed")
    paired_rows = []
    for seed, arms in sorted(by_seed.items()):
        if set(arms) != set(ARMS):
            raise ValueError(f"missing paired delayed-ACK arm: seed {seed}")
        delayed, immediate = (arms[DELAYED], arms[IMMEDIATE])
        for field in ("case", "case_config_sha256", "scheduled_trace_sha256",
                      "scheduled_unicast_flows", "application_deadline_s"):
            if delayed[field] != immediate[field]:
                raise ValueError(f"paired case or application trace differs: seed {seed}")
        if float(immediate["whole_network_tx_airtime_s"]) <= 0.0:
            raise ValueError(f"zero primary comparator airtime: seed {seed}")
        if float(immediate["extended_airtime_s"]) <= 0.0:
            raise ValueError(f"zero extended comparator airtime: seed {seed}")
        paired_rows.append({
            "case": delayed["case"], "seed": seed,
            "focus_protocol": DELAYED, "comparator": IMMEDIATE,
            "scheduled_trace_sha256": delayed["scheduled_trace_sha256"],
            "ack_pdr_gain": (float(delayed["ack_pdr_deadline"])
                             - float(immediate["ack_pdr_deadline"])),
            "destination_pdr_gain": (float(delayed["destination_pdr_deadline"])
                                     - float(immediate["destination_pdr_deadline"])),
            "relative_airtime_cost": (
                float(delayed["whole_network_tx_airtime_s"])
                / float(immediate["whole_network_tx_airtime_s"]) - 1.0
            ),
            "extended_relative_airtime_cost": (
                float(delayed["extended_airtime_s"])
                / float(immediate["extended_airtime_s"]) - 1.0
            ),
            "collision_failure_delta": (int(delayed["collision_failures"])
                                        - int(immediate["collision_failures"])),
            "half_duplex_failure_delta": (int(delayed["half_duplex_failures"])
                                          - int(immediate["half_duplex_failures"])),
            "capped_ack_delay_delta_s": (
                float(delayed["mean_completion_delay_capped_s"])
                - float(immediate["mean_completion_delay_capped_s"])
            ),
        })
    if len({item["case"] for item in paired_rows}) != 1:
        raise ValueError("paired case differs across seeds")
    aggregate: dict[str, Any] = {
        "case": paired_rows[0]["case"],
        "focus_protocol": DELAYED, "comparator": IMMEDIATE,
        "n_seeds": len(paired_rows),
    }
    fields = (
        ("ack_pdr_gain", "ack_pdr"),
        ("destination_pdr_gain", "destination_pdr"),
        ("relative_airtime_cost", "relative_airtime"),
        ("extended_relative_airtime_cost", "extended_relative_airtime"),
        ("collision_failure_delta", "collision_failure"),
        ("half_duplex_failure_delta", "half_duplex_failure"),
        ("capped_ack_delay_delta_s", "capped_ack_delay"),
    )
    for field, prefix in fields:
        mean, low, high = sr.paired_ci95([item[field] for item in paired_rows])
        aggregate[field] = mean
        aggregate[f"{prefix}_ci95_low"] = low
        aggregate[f"{prefix}_ci95_high"] = high
    return paired_rows, aggregate


def _first_ack_for_receipt(
    receipt: dict[str, Any], transmissions: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Match an actual destination ACK after this FLOOD's physical decode."""
    path = tuple(receipt["path"])
    matches = [
        tx for tx in transmissions
        if tx["packet"]["kind"] == "ACK"
        and tx["sender"] == tx["packet"]["origin"] == path[-1]
        and tx["packet"]["final_dst"] == path[0]
        and tx["packet"]["flow_id"] == receipt["flow_id"]
        and tx["packet"]["request_id"] == receipt["flow_id"]
        and tx["packet"]["repair_index"] == receipt["repair_index"]
        and tuple(tx["packet"]["path"]) == path
        and tx["start"] >= receipt["decode_at"]
    ]
    return min(matches, key=lambda tx: (tx["start"], tx["tx_id"])) if matches else None


def flow_records(run: ControlRun) -> list[dict[str, Any]]:
    """Attach physical first-FLOOD and matching destination ACK starts."""
    receipts = {item["flow_id"]: item for item in run.flood_receipts}
    result = []
    for flow in run.flows:
        receipt = receipts.get(flow["flow_id"])
        ack = _first_ack_for_receipt(receipt, run.transmissions) if receipt else None
        result.append({
            **flow,
            "first_flood_decode_at": receipt["decode_at"] if receipt else None,
            "first_flood_tx_id": receipt["tx_id"] if receipt else None,
            "first_flood_path": receipt["path"] if receipt else None,
            "first_flood_repair_index": receipt["repair_index"] if receipt else None,
            "first_flood_ack_tx_id": ack["tx_id"] if ack else None,
            "first_flood_ack_tx_start_at": ack["start"] if ack else None,
            "first_flood_ack_tx_end_at": ack["end"] if ack else None,
        })
    return result


def require_receipt_evidence(
    receipts: list[dict[str, Any]], actions: list[dict[str, Any]],
    primary_tx: list[dict[str, Any]], extended_tx: list[dict[str, Any]],
    protocol: str,
) -> None:
    """Tie each first FLOOD to one destination action and its ACK timing."""
    by_id = {item["tx_id"]: item for item in primary_tx}
    if len(by_id) != len(primary_tx):
        raise ValueError("duplicate physical TX identifier")
    for receipt in receipts:
        original = by_id.get(receipt["tx_id"])
        if (original is None or original["packet"]["kind"] != "FLOOD"
                or original["packet"]["flow_id"] != receipt["flow_id"]
                or original["packet"]["repair_index"] != receipt["repair_index"]
                or list(original["packet"]["path"]) + [
                    original["packet"]["final_dst"]] != receipt["path"]
                or original["end"] != receipt["decode_at"]):
            raise ValueError("first-FLOOD receipt lacks physical TX")
        packet = original["packet"]
        matches = [
            item for item in actions
            if item.get("event") == "dhr_destination_rx"
            and item.get("time") == receipt["decode_at"]
            and item.get("flow_id") == receipt["flow_id"]
            and item.get("src") == packet["origin"]
            and item.get("dst") == packet["final_dst"]
            and item.get("repair_index") == receipt["repair_index"]
        ]
        possible_txs = [
            item for item in primary_tx
            if item["packet"]["kind"] in {"DATA", "FLOOD"}
            and item["packet"]["flow_id"] == receipt["flow_id"]
            and item["packet"]["final_dst"] == packet["final_dst"]
            and item["packet"]["repair_index"] == receipt["repair_index"]
            and item["end"] == receipt["decode_at"]
        ]
        if len(matches) != 1 or len(possible_txs) != 1:
            raise ValueError("first-FLOOD receipt has missing or ambiguous destination RX action")
        ack = _first_ack_for_receipt(receipt, extended_tx)
        if (protocol == DELAYED and ack is not None
                and ack["start"] + 1e-9 < receipt["decode_at"] + 2.0):
            raise ValueError("delayed FLOOD ACK starts before its 2-s timer")


def input_hashes() -> dict[str, str]:
    return {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in SOURCE_FILES
    }


def artifact_paths(prefix: Path) -> dict[str, Path]:
    return {
        "runs": Path(f"{prefix}.runs.csv"),
        "per_seed": Path(f"{prefix}.per_seed.csv"),
        "paired": Path(f"{prefix}.paired.csv"),
        "flows": Path(f"{prefix}.flows.jsonl"),
        "actions": Path(f"{prefix}.actions.jsonl"),
        "tx": Path(f"{prefix}.tx.jsonl"),
        "extended_tx": Path(f"{prefix}.extended_tx.jsonl"),
        "receipts": Path(f"{prefix}.receipts.jsonl"),
        "manifest": Path(f"{prefix}.manifest.json"),
    }


def ensure_paths_available(prefix: Path) -> None:
    for path in artifact_paths(prefix).values():
        if path.exists():
            raise FileExistsError(f"delayed-ACK artifact already exists: {path}")


def write_artifacts(
    prefix: Path, case: sr.SrCase, split: str,
    pairs: list[tuple[ControlRun, ControlRun]],
    stock_runs: dict[int, ControlRun], source_sha256: dict[str, str],
) -> dict[str, Path]:
    """Write immutable, independently hashable run and physical-TX evidence."""
    ensure_paths_available(prefix)
    if source_sha256 != input_hashes():
        raise RuntimeError("delayed-ACK source inputs changed before artifact write")
    by_key: dict[tuple[int, str], tuple[ControlRun, ControlRun]] = {}
    for primary, extended in pairs:
        seed = int(primary.row["seed"])
        arm = primary.row["protocol"]
        key = (seed, arm)
        if (key in by_key or arm not in ARMS or primary.row["case"] != case.key
                or float(primary.row["generation_horizon_s"]) != case.duration_s
                or float(primary.row["application_deadline_s"]) != 30.0
                or float(primary.row["drain_until_s"]) != case.duration_s + 30.0):
            raise ValueError("invalid delayed-ACK run matrix")
        require_extended_prefix(primary, extended)
        by_key[key] = (primary, extended)
    seeds = sorted({seed for seed, _ in by_key})
    if (not seeds or len(by_key) != len(seeds) * len(ARMS)
            or set(stock_runs) != set(seeds)):
        raise ValueError("delayed-ACK evidence requires both arms and stock per seed")
    for seed in seeds:
        require_stock_parity(by_key[(seed, IMMEDIATE)][0], stock_runs[seed])
    ordered = [by_key[(seed, arm)] for seed in seeds for arm in ARMS]
    rows = [
        {**run_row(primary, extended, case.duration_s + 30.0), "seed_split": split}
        for primary, extended in ordered
    ]
    per_seed, paired = summarize_pairs(rows)
    per_seed = [{**item, "seed_split": split} for item in per_seed]
    paired = {**paired, "seed_split": split}
    records: dict[str, list[dict[str, Any]]] = {
        "flows": [], "actions": [], "tx": [], "extended_tx": [], "receipts": [],
    }
    for primary, extended in ordered:
        require_receipt_evidence(
            primary.flood_receipts, primary.actions, primary.transmissions,
            extended.transmissions, primary.row["protocol"],
        )
        receipts_by_flow = {item["flow_id"]: item for item in primary.flood_receipts}
        for flow in flow_records(primary):
            receipt = receipts_by_flow.get(flow["flow_id"])
            later_ack = (_first_ack_for_receipt(receipt, extended.transmissions)
                         if receipt else None)
            records["flows"].append({
                **flow, "seed_split": split,
                "first_flood_ack_extended_tx_start_at":
                    later_ack["start"] if later_ack else None,
                "first_flood_ack_unstarted_at_630": (
                    flow["first_flood_decode_at"] is not None
                    and (flow["first_flood_ack_tx_start_at"] is None
                         or flow["first_flood_ack_tx_start_at"]
                         > case.duration_s + 30.0)
                ),
            })
        for key, entries in (
            ("actions", primary.actions), ("tx", primary.transmissions),
            ("extended_tx", extended.transmissions),
            ("receipts", primary.flood_receipts),
        ):
            records[key].extend({**item, "case": case.key,
                                 "protocol": primary.row["protocol"],
                                 "seed": primary.row["seed"],
                                 "seed_split": split} for item in entries)
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
        "seed_split": split, "application_deadline_s": 30.0,
        "generation_horizon_s": case.duration_s,
        "primary_tx_start_cutoff_s": case.duration_s + 30.0,
        "extended_tx_start_cutoff_s": case.duration_s + 60.0,
        "fixed_flood_ack_delay_s": 2.0,
        "complete_packet_toa_for_included_tx": True,
        "stock_fixed_f_parity": True,
        "extended_airtime_scope": "bounded 660-s TX-start sensitivity, not all eventual TX",
        "primary_cost_window_limited": any(
            row["pending_first_flood_ack_at_cutoff"]
            or row["primary_future_start_tx"]
            or row["post_cutoff_tx"]
            or row["tx_start_after_extended_cutoff"] for row in rows
        ),
        "extended_cost_window_limited": True,
        "extended_observed_tail_unstarted": any(
            row["first_flood_ack_unstarted_at_extended_cutoff"]
            or row["tx_start_after_extended_cutoff"] for row in rows
        ),
        "runs": len(rows),
        "source_sha256": source_sha256,
        "artifact_sha256": {
            key: hashlib.sha256(paths[key].read_bytes()).hexdigest()
            for key in paths if key != "manifest"
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
    """Verify a frozen prerequisite from its saved physical evidence."""
    case = case or sr.SR_CASES["recurring_fading"]
    seeds = seeds if seeds is not None else seeds_for_split(expected_split)
    if not manifest_path.name.endswith(".manifest.json"):
        raise ValueError("delayed-ACK manifest needs .manifest.json suffix")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    paths = artifact_paths(Path(str(manifest_path)[:-len(".manifest.json")]))
    expected_static = {
        "case": asdict(case), "protocols": list(ARMS), "seeds": list(seeds),
        "seed_split": expected_split, "application_deadline_s": 30.0,
        "generation_horizon_s": case.duration_s,
        "primary_tx_start_cutoff_s": case.duration_s + 30.0,
        "extended_tx_start_cutoff_s": case.duration_s + 60.0,
        "fixed_flood_ack_delay_s": 2.0,
        "complete_packet_toa_for_included_tx": True,
        "stock_fixed_f_parity": True,
        "extended_airtime_scope": "bounded 660-s TX-start sensitivity, not all eventual TX",
        "extended_cost_window_limited": True,
        "runs": len(seeds) * len(ARMS),
        "source_sha256": expected_source_sha256,
    }
    if any(manifest.get(key) != value for key, value in expected_static.items()):
        raise ValueError("delayed-ACK manifest differs from frozen configuration")
    if expected_source_sha256 != input_hashes():
        raise ValueError("delayed-ACK source hash differs from manifest")
    expected_artifacts = set(paths) - {"manifest"}
    artifact_hashes = manifest.get("artifact_sha256")
    if not isinstance(artifact_hashes, dict) or set(artifact_hashes) != expected_artifacts:
        raise ValueError("delayed-ACK artifact hash manifest is incomplete")
    for key in expected_artifacts:
        artifact = paths[key]
        if (not artifact.is_file()
                or hashlib.sha256(artifact.read_bytes()).hexdigest()
                != artifact_hashes[key]):
            raise ValueError(f"delayed-ACK artifact hash mismatch: {key}")
    with paths["runs"].open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    with paths["per_seed"].open(newline="", encoding="utf-8") as handle:
        saved_per_seed = list(csv.DictReader(handle))
    with paths["paired"].open(newline="", encoding="utf-8") as handle:
        saved_paired = list(csv.DictReader(handle))
    if len(rows) != len(seeds) * len(ARMS):
        raise ValueError("delayed-ACK saved run matrix is incomplete")
    row_by_key = {(int(row["seed"]), row["protocol"]): row for row in rows}
    if set(row_by_key) != {(seed, arm) for seed in seeds for arm in ARMS}:
        raise ValueError("delayed-ACK saved run matrix has alien or duplicate arms")
    records = {key: _read_jsonl(paths[key])
               for key in ("flows", "actions", "tx", "extended_tx", "receipts")}
    grouped: dict[str, dict[tuple[int, str], list[dict[str, Any]]]] = {}
    for kind, items in records.items():
        by_key: dict[tuple[int, str], list[dict[str, Any]]] = {}
        for item in items:
            key = (int(item["seed"]), item["protocol"])
            if (key not in row_by_key or item.get("case") != case.key
                    or item.get("seed_split") != expected_split):
                raise ValueError(f"delayed-ACK {kind} evidence has alien records")
            by_key.setdefault(key, []).append(item)
        grouped[kind] = by_key
    case_hash = _sha256_json(asdict(case))
    for key, row in row_by_key.items():
        if (row.get("case") != case.key
                or row.get("case_config_sha256") != case_hash
                or row.get("seed_split") != expected_split
                or float(row["generation_horizon_s"]) != case.duration_s
                or float(row["application_deadline_s"]) != 30.0
                or float(row["drain_until_s"]) != case.duration_s + 30.0):
            raise ValueError("delayed-ACK saved run differs from frozen case")
        strip = lambda item: {name: value for name, value in item.items()
                              if name != "seed_split"}
        tx = [strip(item) for item in grouped["tx"].get(key, [])]
        extended_tx = [strip(item) for item in grouped["extended_tx"].get(key, [])]
        actions = [strip(item) for item in grouped["actions"].get(key, [])]
        receipts = [
            {name: value for name, value in item.items()
             if name not in {"case", "protocol", "seed", "seed_split"}}
            for item in grouped["receipts"].get(key, [])
        ]
        flows = grouped["flows"].get(key, [])
        if (_sha256_json(tx) != row["full_tx_trace_sha256"]
                or _sha256_json(extended_tx) != row["extended_tx_trace_sha256"]
                or _sha256_json(actions) != row["full_action_trace_sha256"]):
            raise ValueError("delayed-ACK complete TX or action hash differs from runs")
        source_actions = {
            "flows": [(flow["flow_id"], flow["source_action"]) for flow in flows],
            "events": [event for event in actions if event.get("event") in {
                "decision", "timeout", "commit", "dhr_guard", "dhr_recovery_tx",
                "dhr_source_ack_rx", "dhr_state_drop",
            }],
        }
        if _sha256_json(source_actions) != row["source_action_trace_sha256"]:
            raise ValueError("delayed-ACK source action hash differs from runs")
        if (len(flows) != int(row["scheduled_unicast_flows"])
                or len(receipts) != int(row["first_flood_receipts"])
                or sum(flow["ack_by_deadline"] is True for flow in flows)
                   != int(row["ack_by_deadline"])
                or sum(flow["delivery_by_deadline"] is True for flow in flows)
                   != int(row["delivery_by_deadline"])):
            raise ValueError("delayed-ACK flow evidence differs from runs")
        schedule = sorted((float(flow["enqueued_at"]), int(flow["src"]),
                           int(flow["dst"]), int(flow["flow_id"]))
                          for flow in flows)
        if _sha256_json(schedule) != row["scheduled_trace_sha256"]:
            raise ValueError("delayed-ACK flow application trace differs from runs")
        for flow in flows:
            deadline_at = float(flow["deadline_at"])
            acked_at = flow["acked_at"]
            delivered_at = flow["delivered_at"]
            if (not math.isclose(deadline_at, float(flow["enqueued_at"]) + 30.0,
                                 rel_tol=0.0, abs_tol=1e-9)
                    or flow["ack_by_deadline"] is not (
                        acked_at is not None and acked_at <= deadline_at)
                    or flow["delivery_by_deadline"] is not (
                        delivered_at is not None and delivered_at <= deadline_at)):
                raise ValueError("delayed-ACK flow deadline evidence differs")
        require_receipt_evidence(receipts, actions, tx, extended_tx, row["protocol"])
        if len({item["flow_id"] for item in receipts}) != len(receipts):
            raise ValueError("duplicate first-FLOOD per-flow receipt")
        recomputed = flow_records(ControlRun(row, flows, actions, tx, receipts))
        receipts_by_flow = {item["flow_id"]: item for item in receipts}
        first_fields = (
            "first_flood_decode_at", "first_flood_tx_id", "first_flood_path",
            "first_flood_repair_index", "first_flood_ack_tx_id",
            "first_flood_ack_tx_start_at", "first_flood_ack_tx_end_at",
        )
        for saved, expected in zip(flows, recomputed):
            receipt = receipts_by_flow.get(saved["flow_id"])
            later_ack = (_first_ack_for_receipt(receipt, extended_tx)
                         if receipt else None)
            extended_start = later_ack["start"] if later_ack else None
            unstarted = bool(
                receipt is not None
                and (expected["first_flood_ack_tx_start_at"] is None
                     or expected["first_flood_ack_tx_start_at"]
                     > case.duration_s + 30.0)
            )
            if (any(saved.get(field) != expected[field] for field in first_fields)
                    or saved.get("first_flood_ack_extended_tx_start_at")
                       != extended_start
                    or saved.get("first_flood_ack_unstarted_at_630") is not unstarted):
                raise ValueError("first-FLOOD per-flow ACK evidence differs from TX")
        fake_primary = ControlRun(row, [], [], tx, receipts)
        fake_extended = ControlRun(row, [], [], extended_tx, receipts)
        sensitivity = extended_sensitivity(
            fake_primary, fake_extended,
            case.duration_s + 30.0, case.duration_s + 60.0,
        )
        if (any(not math.isclose(float(row[name]), float(value),
                                 rel_tol=0.0, abs_tol=1e-8)
                for name, value in sensitivity.items())
                or int(row["primary_future_start_tx"])
                   != sum(item["start"] > case.duration_s + 30.0 for item in tx)
                or int(row["half_duplex_failures"])
                   != count_half_duplex_from_tx(
                       tx, case.nodes, case.duration_s + 30.0)
                or not math.isclose(float(row["whole_network_tx_airtime_s"]),
                                    sum(item["end"] - item["start"] for item in tx
                                        if item["start"] <= case.duration_s + 30.0),
                                    rel_tol=0.0, abs_tol=1e-8)):
            raise ValueError("delayed-ACK saved TX cost differs from physical evidence")
    expected_per_seed, expected_paired = summarize_pairs(rows)
    expected_per_seed = [{**item, "seed_split": expected_split}
                         for item in expected_per_seed]
    expected_paired = {**expected_paired, "seed_split": expected_split}
    if (len(saved_per_seed) != len(expected_per_seed)
            or any(not _same_csv_record(saved, expected)
                   for saved, expected in zip(saved_per_seed, expected_per_seed))
            or len(saved_paired) != 1
            or not _same_csv_record(saved_paired[0], expected_paired)):
        raise ValueError("delayed-ACK paired evidence differs from saved runs")
    primary_limited = any(
        int(row["pending_first_flood_ack_at_cutoff"])
        or int(row["primary_future_start_tx"])
        or int(row["post_cutoff_tx"])
        or int(row["tx_start_after_extended_cutoff"])
        for row in rows
    )
    observed_tail = any(
        int(row["first_flood_ack_unstarted_at_extended_cutoff"])
        or int(row["tx_start_after_extended_cutoff"])
        for row in rows
    )
    if (manifest.get("primary_cost_window_limited") is not bool(primary_limited)
            or manifest.get("extended_observed_tail_unstarted") is not bool(observed_tail)):
        raise ValueError("delayed-ACK cost window manifest differs from saved TX")
    if strict_replay:
        for seed in seeds:
            replayed_immediate = None
            for arm in ARMS:
                key = (seed, arm)
                primary = run_one_traced(case, arm, seed)
                if arm == IMMEDIATE:
                    replayed_immediate = primary
                extended = run_one_extended(case, arm, seed)
                expected_row = {
                    **run_row(primary, extended, case.duration_s + 30.0),
                    "seed_split": expected_split,
                }
                if not _same_csv_record(row_by_key[key], expected_row):
                    raise ValueError(f"strict replay run metrics differ: {seed} {arm}")
                saved_actions = [
                    {name: value for name, value in item.items()
                     if name != "seed_split"}
                    for item in grouped["actions"].get(key, [])
                ]
                saved_tx = [
                    {name: value for name, value in item.items()
                     if name != "seed_split"}
                    for item in grouped["tx"].get(key, [])
                ]
                saved_extended_tx = [
                    {name: value for name, value in item.items()
                     if name != "seed_split"}
                    for item in grouped["extended_tx"].get(key, [])
                ]
                saved_receipts = [
                    {name: value for name, value in item.items()
                     if name not in {"case", "protocol", "seed", "seed_split"}}
                    for item in grouped["receipts"].get(key, [])
                ]
                saved_flows = grouped["flows"].get(key, [])
                try:
                    saved_core_flows = [
                        {name: item[name] for name in primary.flows[0]}
                        for item in saved_flows
                    ]
                except (IndexError, KeyError) as exc:
                    raise ValueError("strict replay per-flow evidence is incomplete") from exc
                if any(
                    _sha256_json(saved) != _sha256_json(actual)
                    for saved, actual in (
                        (saved_actions, primary.actions),
                        (saved_tx, primary.transmissions),
                        (saved_extended_tx, extended.transmissions),
                        (saved_receipts, primary.flood_receipts),
                        (saved_core_flows, primary.flows),
                    )
                ):
                    raise ValueError(f"strict replay physical or flow evidence differs: {seed} {arm}")
            require_stock_parity(
                replayed_immediate,
                run_one_stock(case, IMMEDIATE, seed),
            )
        if input_hashes() != expected_source_sha256:
            raise ValueError("strict replay source hashes changed during validation")


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
    pairs: list[tuple[ControlRun, ControlRun]] = []
    stock_runs: dict[int, ControlRun] = {}
    for seed in seeds:
        for arm in ARMS:
            primary = run_one_traced(case, arm, seed)
            extended = run_one_extended(case, arm, seed)
            if (primary.row.get("case") != case.key
                    or primary.row.get("protocol") != arm
                    or int(primary.row.get("seed", -1)) != seed):
                raise ValueError("delayed-ACK runner returned wrong case, arm, or seed")
            require_extended_prefix(primary, extended)
            pairs.append((primary, extended))
        stock = run_one_stock(case, IMMEDIATE, seed)
        require_stock_parity(pairs[-1][0], stock)
        stock_runs[seed] = stock
    if input_hashes() != source_sha256:
        raise RuntimeError("delayed-ACK inputs changed during the experiment")
    return write_artifacts(out_prefix, case, split, pairs, stock_runs, source_sha256)


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
    print(f"Delayed-ACK control manifest: {paths['manifest']}")


if __name__ == "__main__":
    main()
