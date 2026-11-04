#!/usr/bin/env python3
"""Prospective, seed-paired AFS cancellation component experiment."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import Packet, RxInfo, Transmission
from tools import run_sr_experiment as sr


SOURCE_FILES = (
    "lora_mesh_sim.py",
    "tools/run_fair_multihop_probe.py",
    "tools/run_sr_experiment.py",
    "tools/run_afs_experiment.py",
    "docs/research/meshecho_dhr_design.md",
    "docs/research/meshecho_ack_terminated_flood_design.md",
    "tests/test_sr_experiment.py",
    "tests/test_meshecho_dhr.py",
    "tests/test_meshecho_afs.py",
    "tests/test_afs_experiment.py",
)
SPLIT_SEEDS = {
    "smoke": (23000,),
    "development": tuple(range(23001, 23041)),
    "holdout": tuple(range(24001, 24041)),
}
ARMS = ("meshecho-afs", "meshecho-afs-nocancel", "meshecho-dhr-flood")


@dataclass(frozen=True)
class AfsRun:
    row: dict[str, Any]
    flows: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    transmissions: list[dict[str, Any]]
    decodes: list[dict[str, Any]]


class AfsRecordingSimulator(sr.RecordingSimulator):
    """Tap completed ACK decodes while retaining the SR harness's TX history."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.ack_decodes: list[dict[str, Any]] = []

    def try_receive(self, tx: Transmission, receiver: int) -> RxInfo | None:
        rx = super().try_receive(tx, receiver)
        packet = tx.packet
        if rx is not None and packet.kind == "ACK":
            path = packet.path
            natural = (
                not packet.app_payload and packet.flow_id > 0
                and packet.request_id == packet.flow_id
                and 2 <= len(path) <= self.max_hops + 1
                and len(set(path)) == len(path)
                and path[0] == packet.final_dst and path[-1] == packet.origin
                and 0 <= packet.path_index < len(path) - 1
                and path[packet.path_index + 1] == rx.sender
            )
            off_path = receiver not in path
            key = (receiver, ("FLOOD", packet.final_dst,
                              packet.flow_id, packet.request_id))
            pending_by_key = getattr(self.protocol, "afs_pending", {})
            record = pending_by_key.get(key) if natural and off_path else None
            flood = record.packet if record is not None else None
            mapped = (self.protocol.pending_fallback.get(key)
                      if record is not None else None)
            strict_pending = bool(
                record is not None
                and flood.kind == "FLOOD" and flood.app_payload
                and flood.flow_id == packet.flow_id
                and flood.request_id == packet.request_id
                and flood.origin == packet.final_dst
                and flood.final_dst == packet.origin
                and flood.repair_index == packet.repair_index
                and flood.repair_index in (None, 2)
                and flood.path and flood.path[0] == flood.origin
                and flood.path[-1] == receiver
                and 2 <= len(flood.path) <= self.max_hops
                and len(set(flood.path)) == len(flood.path)
                and flood.path_index == len(flood.path) - 1
                and flood.ttl >= 1
                and mapped is record.pending
                and not record.pending.canceled
                and not record.pending.committed
                and self.now < record.received_at + 30.0
            )
            self.ack_decodes.append({
                "time": self.now, "tx_id": tx.tx_id,
                "flow_id": packet.flow_id, "receiver": receiver,
                "repair_index": packet.repair_index,
                "natural_destination_ack": natural,
                "off_path": off_path,
                "strict_pending": strict_pending,
                "rx_sender": rx.sender,
                "ack_packet": asdict(packet),
                "pending_flood_packet": asdict(flood) if flood is not None else None,
                "pending_received_at": record.received_at if record is not None else None,
                "record_handle_id": id(record.pending) if record is not None else None,
                "mapped_handle_id": id(mapped) if mapped is not None else None,
                "pending_canceled": record.pending.canceled if record is not None else None,
                "pending_committed": record.pending.committed if record is not None else None,
            })
        return rx


def reconstruct_decode_witness(
    decode: dict[str, Any], tx_by_id: dict[int, dict[str, Any]],
    max_hops: int,
) -> tuple[bool, bool, bool]:
    """Rebuild the ACK/path/handle predicate from saved receive-time facts."""
    try:
        ack = decode["ack_packet"]
        tx = tx_by_id[int(decode["tx_id"])]
        path = ack["path"]
        receiver = int(decode["receiver"])
        when = float(decode["time"])
        sender = int(decode["rx_sender"])
        if (tx["packet"] != ack or tx["sender"] != sender
                or tx["end"] != when or ack["kind"] != "ACK"):
            raise ValueError("ACK transcript differs from physical decode")
        natural = bool(
            not ack["app_payload"] and ack["flow_id"] > 0
            and ack["request_id"] == ack["flow_id"]
            and 2 <= len(path) <= max_hops + 1
            and len(set(path)) == len(path)
            and path[0] == ack["final_dst"] and path[-1] == ack["origin"]
            and 0 <= ack["path_index"] < len(path) - 1
            and path[ack["path_index"] + 1] == sender
        )
        off_path = receiver not in path
        flood = decode["pending_flood_packet"]
        flood_path = flood["path"] if flood is not None else ()
        strict = bool(
            natural and off_path and flood is not None
            and flood["kind"] == "FLOOD" and flood["app_payload"]
            and flood["flow_id"] == ack["flow_id"]
            and flood["request_id"] == ack["request_id"]
            and flood["origin"] == ack["final_dst"]
            and flood["final_dst"] == ack["origin"]
            and flood["repair_index"] == ack["repair_index"]
            and flood["repair_index"] in (None, 2)
            and flood_path and flood_path[0] == flood["origin"]
            and flood_path[-1] == receiver
            and 2 <= len(flood_path) <= max_hops
            and len(set(flood_path)) == len(flood_path)
            and flood["path_index"] == len(flood_path) - 1
            and flood["ttl"] >= 1
            and decode["record_handle_id"] is not None
            and decode["record_handle_id"] == decode["mapped_handle_id"]
            and decode["pending_canceled"] is False
            and decode["pending_committed"] is False
            and 0.0 <= float(decode["pending_received_at"]) <= when
            and when < float(decode["pending_received_at"]) + 30.0
        )
        if (decode["flow_id"] != ack["flow_id"]
                or decode["repair_index"] != ack["repair_index"]
                or decode["natural_destination_ack"] is not natural
                or decode["off_path"] is not off_path
                or decode["strict_pending"] is not strict):
            raise ValueError("saved ACK decode witness differs from packet and local state")
    except (KeyError, TypeError, IndexError) as exc:
        raise ValueError("saved ACK decode witness is incomplete") from exc
    return natural, off_path, strict


def normalized_tx_trace(transmissions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for item in transmissions:
        record = {key: value for key, value in item.items() if key != "protocol"}
        record["packet"] = {key: value for key, value in item["packet"].items()
                            if key != "protocol"}
        normalized.append(record)
    return normalized


def tx_trace_hash(transmissions: list[dict[str, Any]]) -> str:
    payload = json.dumps(normalized_tx_trace(transmissions),
                         sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def seeds_for_split(split: str) -> tuple[int, ...]:
    try:
        return SPLIT_SEEDS[split]
    except KeyError as exc:
        raise ValueError(f"unknown AFS split: {split}") from exc


def run_one_traced(case: sr.SrCase, protocol: str, seed: int) -> AfsRun:
    if protocol not in ARMS:
        raise ValueError(f"unknown AFS arm: {protocol}")
    captured: list[AfsRecordingSimulator] = []

    class CapturingSimulator(AfsRecordingSimulator):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)
            captured.append(self)

    with patch.object(sr, "RecordingSimulator", CapturingSimulator):
        result = sr.run_one_sr(case, protocol, seed, deadline_s=30.0)
    if len(captured) != 1:
        raise RuntimeError("SR runner did not create exactly one simulator")
    sim = captured[0]
    transmissions = [
        {
            "case": case.key, "protocol": protocol, "seed": seed,
            "tx_id": tx.tx_id, "sender": tx.sender,
            "start": tx.start, "end": tx.end,
            "packet": asdict(tx.packet),
        }
        for tx in sim.tx_history
    ]
    decodes = [
        {"case": case.key, "protocol": protocol, "seed": seed, **decode}
        for decode in sim.ack_decodes
    ]
    actions = result.actions
    cancellations = [event for event in actions if event.get("event") == "afs_cancel"]
    opportunities = [event for event in actions
                     if event.get("event") == "afs_opportunity"]
    windowed = [tx for tx in sim.tx_history
                if tx.start <= case.duration_s + 30.0]
    acks = [tx.packet for tx in windowed if tx.packet.kind == "ACK"]
    source_recovery = [tx for tx in windowed
                       if tx.sender == tx.packet.origin
                       and (tx.packet.kind, tx.packet.repair_index)
                       in {("DATA", 1), ("FLOOD", 2)}]
    row = {
        **result.row,
        "windowed_dhr_initial_ack_tx": sum(packet.repair_index is None
                                            for packet in acks),
        "windowed_dhr_repeat_ack_tx": sum(packet.repair_index == 1
                                           for packet in acks),
        "windowed_dhr_flood_ack_tx": sum(packet.repair_index == 2
                                          for packet in acks),
        "windowed_dhr_recovery_r_source_tx": sum(
            tx.packet.repair_index == 1 for tx in source_recovery
        ),
        "windowed_dhr_recovery_f_source_tx": sum(
            tx.packet.repair_index == 2 for tx in source_recovery
        ),
        "full_tx_trace_sha256": tx_trace_hash(transmissions),
        "physical_ack_decodes": len(decodes),
        "natural_ack_decodes": sum(event["natural_destination_ack"]
                                   for event in decodes),
        "offpath_natural_ack_decodes": sum(
            event["natural_destination_ack"] and event["off_path"]
            for event in decodes
        ),
        "strict_pending_ack_decodes": sum(event["strict_pending"]
                                          for event in decodes),
        "afs_opportunities": len(opportunities),
        "afs_cancellations": len(cancellations),
        "afs_initial_f_cancellations": sum(event.get("repair_index") is None
                                            for event in cancellations),
        "afs_recovery_f_cancellations": sum(event.get("repair_index") == 2
                                             for event in cancellations),
    }
    return AfsRun(row, result.flows, actions, transmissions, decodes)


def require_mechanical_parity(shadow: AfsRun, baseline: AfsRun) -> None:
    """Require the no-cancel control to replay fixed-F at every observable level."""
    if (shadow.row["protocol"] != ARMS[1]
            or baseline.row["protocol"] != ARMS[2]
            or shadow.row["seed"] != baseline.row["seed"]):
        raise ValueError("no-cancel parity received the wrong arms or seed")

    def comparable_row(row: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value for key, value in row.items()
            if key != "protocol" and not key.startswith("afs_")
            and key != "strict_pending_ack_decodes"
        }

    def comparable_records(records: list[dict[str, Any]],
                           drop_afs: bool = False) -> list[dict[str, Any]]:
        return [
            {key: value for key, value in record.items() if key != "protocol"}
            for record in records
            if not drop_afs or not str(record.get("event", "")).startswith("afs_")
        ]

    if comparable_row(shadow.row) != comparable_row(baseline.row):
        raise ValueError("no-cancel run metrics differ from fixed-F")
    if comparable_records(shadow.flows) != comparable_records(baseline.flows):
        raise ValueError("no-cancel per-flow evidence differs from fixed-F")
    if comparable_records(shadow.actions, True) != comparable_records(
        baseline.actions, True
    ):
        raise ValueError("no-cancel source actions differ from fixed-F")
    if normalized_tx_trace(shadow.transmissions) != normalized_tx_trace(
        baseline.transmissions
    ):
        raise ValueError("no-cancel complete TX trace differs from fixed-F")


def _event_identity(event: dict[str, Any], relay_key: str) -> tuple[Any, ...]:
    return (
        int(event["seed"]), str(event["protocol"]), float(event["time"]),
        int(event["flow_id"]), int(event[relay_key]), event["repair_index"],
    )


def cancellation_exposure(
    actions: list[dict[str, Any]], decodes: list[dict[str, Any]],
) -> dict[str, int]:
    """Audit every reported cancellation against its on-air pending witness."""
    witnesses = Counter(
        _event_identity(item, "receiver") for item in decodes
        if item.get("strict_pending")
    )
    opportunities = Counter(
        _event_identity(item, "relay") for item in actions
        if item.get("event") == "afs_opportunity"
    )
    cancellations = [item for item in actions if item.get("event") == "afs_cancel"]
    canceled = Counter(_event_identity(item, "relay") for item in cancellations)
    if any(item["protocol"] != ARMS[0] for item in cancellations):
        raise ValueError("only the AFS candidate may cancel pending FLOODs")
    if any(item.get("repair_index") not in (None, 2) for item in cancellations):
        raise ValueError("invalid AFS cancellation marker")
    if any(count > opportunities[key] or count > witnesses[key]
           for key, count in canceled.items()):
        raise ValueError("AFS cancellation lacks a strict physical ACK witness")
    return {
        "cancel_events": len(cancellations),
        "cancel_seeds": len({int(item["seed"]) for item in cancellations}),
        "initial_f_cancellations": sum(item["repair_index"] is None
                                        for item in cancellations),
        "recovery_f_cancellations": sum(item["repair_index"] == 2
                                         for item in cancellations),
        "invalid_cancellations": 0,
    }


def evaluate_afs(
    rows: list[dict[str, Any]], actions: list[dict[str, Any]],
    decodes: list[dict[str, Any]], split: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Apply the prospective four-part AFS cost and reliability gate."""
    seeds = seeds_for_split(split)
    comparisons = sr.summarize_paired(rows, ARMS[0], ARMS[1:])
    exposure = cancellation_exposure(actions, decodes)
    coverage = Counter((int(row["seed"]), row["protocol"]) for row in rows)
    frozen_matrix = (
        split in {"development", "holdout"}
        and len(rows) == len(seeds) * len(ARMS)
        and all(coverage[(seed, protocol)] == 1
                for seed in seeds for protocol in ARMS)
        and all(row.get("case") == "recurring_fading"
                and row.get("seed_split") == split
                and float(row.get("application_deadline_s", -1)) == 30.0
                for row in rows)
    )
    exposure_gate = (
        exposure["cancel_events"] >= 100
        and exposure["cancel_seeds"] >= 20
        and exposure["invalid_cancellations"] == 0
    )
    for item in comparisons:
        item["seed_split"] = split
        item["afs_primary_gate"] = bool(
            frozen_matrix and item["comparator"] == ARMS[1]
            and item["relative_airtime_ci95_high"] < -0.05
            and item["ack_pdr_ci95_low"] > -0.02
            and item["destination_pdr_ci95_low"] > -0.01
            and exposure_gate
        )
        item["afs_exposure_gate"] = bool(frozen_matrix and exposure_gate)
    return comparisons, exposure


def input_hashes() -> dict[str, str]:
    """Freeze the simulator, runner, design, and direct test inputs together."""
    return {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in SOURCE_FILES
    }


def artifact_paths(prefix: Path) -> dict[str, Path]:
    return {
        "runs": Path(f"{prefix}.runs.csv"),
        "paired": Path(f"{prefix}.paired.csv"),
        "flows": Path(f"{prefix}.flows.jsonl"),
        "actions": Path(f"{prefix}.actions.jsonl"),
        "tx": Path(f"{prefix}.tx.jsonl"),
        "decodes": Path(f"{prefix}.decodes.jsonl"),
        "manifest": Path(f"{prefix}.manifest.json"),
    }


def ensure_paths_available(prefix: Path) -> None:
    for path in artifact_paths(prefix).values():
        if path.exists():
            raise FileExistsError(f"AFS artifact already exists: {path}")


def write_artifacts(
    prefix: Path, case: sr.SrCase, split: str, runs: list[AfsRun],
    source_sha256: dict[str, str],
) -> dict[str, Path]:
    """Persist complete seed, flow, action, TX, and physical-decode evidence."""
    ensure_paths_available(prefix)
    by_seed = {(int(run.row["seed"]), run.row["protocol"]): run for run in runs}
    for seed in {int(run.row["seed"]) for run in runs}:
        require_mechanical_parity(by_seed[(seed, ARMS[1])], by_seed[(seed, ARMS[2])])
    rows = [{**run.row, "seed_split": split} for run in runs]
    records = {
        "flows": [{**item, "seed_split": split}
                  for run in runs for item in run.flows],
        "actions": [{**item, "seed_split": split}
                    for run in runs for item in run.actions],
        "tx": [{**item, "seed_split": split}
               for run in runs for item in run.transmissions],
        "decodes": [{**item, "seed_split": split}
                    for run in runs for item in run.decodes],
    }
    comparisons, exposure = evaluate_afs(
        rows, records["actions"], records["decodes"], split
    )
    paths = artifact_paths(prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    for key, values in (("runs", rows), ("paired", comparisons)):
        with paths[key].open("x", newline="", encoding="utf-8") as handle:
            if values:
                writer = csv.DictWriter(handle, fieldnames=list(values[0]))
                writer.writeheader()
                writer.writerows(values)
    for key in ("flows", "actions", "tx", "decodes"):
        with paths[key].open("x", encoding="utf-8") as handle:
            for record in records[key]:
                handle.write(json.dumps(record, sort_keys=True,
                                        separators=(",", ":")) + "\n")
    primary = next(item for item in comparisons
                   if item["comparator"] == ARMS[1])
    manifest = {
        "case": asdict(case),
        "protocols": list(ARMS),
        "seeds": sorted({int(run.row["seed"]) for run in runs}),
        "seed_split": split,
        "application_deadline_s": 30.0,
        "tx_cost_window": {
            "last_tx_start_s": case.duration_s + 30.0,
            "full_packet_toa_for_included_tx": True,
        },
        "source_sha256": source_sha256,
        "artifact_sha256": {
            key: hashlib.sha256(paths[key].read_bytes()).hexdigest()
            for key in ("runs", "paired", "flows", "actions", "tx", "decodes")
        },
        "runs": len(rows),
        "no_cancel_fixed_f_mechanical_parity": True,
        "afs_exposure": exposure,
        "afs_project_gate": primary["afs_primary_gate"],
    }
    if split == "development":
        manifest["afs_development_open_gate"] = primary["afs_primary_gate"]
    if split == "holdout":
        manifest["afs_holdout_replication_gate"] = primary["afs_primary_gate"]
    with paths["manifest"].open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    return paths


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def _decode_without_object_ids(decode: dict[str, Any]) -> dict[str, Any]:
    record_id = decode["record_handle_id"]
    mapped_id = decode["mapped_handle_id"]
    return {
        **{key: value for key, value in decode.items()
           if key not in {"record_handle_id", "mapped_handle_id", "seed_split"}},
        "record_handle_present": record_id is not None,
        "mapped_handle_present": mapped_id is not None,
        "same_pending_handle": record_id is not None and record_id == mapped_id,
    }


def replay_matches_saved(run: AfsRun, saved: AfsRun) -> bool:
    """Compare every observable result while normalizing process-local IDs."""
    replay_flows, replay_actions, replay_tx, replay_decodes = json.loads(
        json.dumps([run.flows, run.actions, run.transmissions, run.decodes])
    )
    saved_row = {key: value for key, value in saved.row.items()
                 if key != "seed_split"}
    expected_row = {key: "" if value is None else str(value)
                    for key, value in run.row.items()}
    saved_records = [
        [{key: value for key, value in item.items() if key != "seed_split"}
         for item in records]
        for records in (saved.flows, saved.actions, saved.transmissions)
    ]
    return (
        expected_row == saved_row
        and [replay_flows, replay_actions, replay_tx] == saved_records
        and [_decode_without_object_ids(item) for item in replay_decodes]
        == [_decode_without_object_ids(item) for item in saved.decodes]
    )


def validate_flow_deadlines(
    flows: list[dict[str, Any]], row: dict[str, Any], case: sr.SrCase,
) -> None:
    """Derive deadline outcomes and delay statistics from raw flow times."""
    seen_ids: set[int] = set()
    capped_delays: list[float] = []
    ack_delays: list[float] = []
    late_acks = late_deliveries = 0
    for flow in flows:
        try:
            flow_id = int(flow["flow_id"])
            enqueued = float(flow["enqueued_at"])
            deadline = float(flow["deadline_at"])
            delivered = (None if flow["delivered_at"] is None
                         else float(flow["delivered_at"]))
            acked = (None if flow["acked_at"] is None
                     else float(flow["acked_at"]))
            observed = [time for time in (delivered, acked) if time is not None]
            ack_by_deadline = acked is not None and acked <= deadline
            delivery_by_deadline = delivered is not None and delivered <= deadline
            capped = acked - enqueued if ack_by_deadline else 30.0
            valid = (
                flow_id > 0 and flow_id not in seen_ids
                and math.isfinite(enqueued) and math.isfinite(deadline)
                and 0.0 <= enqueued < case.duration_s
                and math.isclose(deadline, enqueued + 30.0,
                                 rel_tol=0.0, abs_tol=1e-9)
                and all(math.isfinite(time) and time >= enqueued
                        for time in observed)
                and (acked is None or delivered is not None and acked >= delivered)
                and flow["ack_by_deadline"] is ack_by_deadline
                and flow["delivery_by_deadline"] is delivery_by_deadline
                and flow["late_ack"] is (acked is not None and not ack_by_deadline)
                and flow["late_delivery"] is (
                    delivered is not None and not delivery_by_deadline
                )
                and math.isclose(float(flow["completion_delay_capped_s"]),
                                 capped, rel_tol=0.0, abs_tol=1e-9)
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("AFS prerequisite flow deadline evidence is invalid") from exc
        if not valid:
            raise ValueError("AFS prerequisite flow deadline evidence is invalid")
        seen_ids.add(flow_id)
        capped_delays.append(capped)
        if ack_by_deadline:
            ack_delays.append(acked - enqueued)
        late_acks += acked is not None and not ack_by_deadline
        late_deliveries += delivered is not None and not delivery_by_deadline
    if (
        not flows
        or late_acks != int(row["late_ack_count"])
        or late_deliveries != int(row["late_delivery_count"])
        or not math.isclose(sum(capped_delays) / len(flows),
                            float(row["mean_completion_delay_capped_s"]),
                            rel_tol=0.0, abs_tol=1e-9)
        or not math.isclose(sr.percentile(ack_delays, 0.95),
                            float(row["p95_ack_delay_s"]),
                            rel_tol=0.0, abs_tol=1e-9)
    ):
        raise ValueError("AFS prerequisite flow deadline evidence differs from runs")


def validate_manifest(
    manifest_path: Path, expected_split: str,
    expected_source_sha256: dict[str, str],
) -> None:
    """Recompute prerequisite evidence before any protected seed is simulated."""
    if expected_split not in {"smoke", "development"}:
        raise ValueError("only smoke and development can open later AFS splits")
    if not manifest_path.name.endswith(".manifest.json"):
        raise ValueError("AFS prerequisite needs a .manifest.json file")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    case = sr.SR_CASES["recurring_fading"]
    seeds = seeds_for_split(expected_split)
    if manifest.get("source_sha256") != expected_source_sha256:
        raise ValueError("AFS prerequisite source/design/test hashes differ")
    if (
        manifest.get("case") != asdict(case)
        or manifest.get("protocols") != list(ARMS)
        or manifest.get("seeds") != list(seeds)
        or manifest.get("seed_split") != expected_split
        or manifest.get("application_deadline_s") != 30.0
        or manifest.get("no_cancel_fixed_f_mechanical_parity") is not True
        or manifest.get("runs") != len(seeds) * len(ARMS)
    ):
        raise ValueError("AFS prerequisite manifest differs from frozen configuration")
    prefix = manifest_path.with_name(manifest_path.name[:-len(".manifest.json")])
    paths = artifact_paths(prefix)
    hashes = manifest.get("artifact_sha256")
    if not isinstance(hashes, dict):
        raise ValueError("AFS prerequisite artifact hashes are missing")
    for key in ("runs", "paired", "flows", "actions", "tx", "decodes"):
        if (not paths[key].is_file()
                or hashlib.sha256(paths[key].read_bytes()).hexdigest()
                != hashes.get(key)):
            raise ValueError(f"AFS prerequisite artifact hash mismatch: {key}")
    with paths["runs"].open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    with paths["paired"].open(newline="", encoding="utf-8") as handle:
        saved_paired = list(csv.DictReader(handle))
    records = {key: _read_jsonl(paths[key])
               for key in ("flows", "actions", "tx", "decodes")}
    coverage = Counter((int(row["seed"]), row["protocol"]) for row in rows)
    if (len(rows) != len(seeds) * len(ARMS)
            or any(coverage[(seed, protocol)] != 1
                   for seed in seeds for protocol in ARMS)):
        raise ValueError("AFS prerequisite lacks one run per frozen seed and arm")
    case_hash = hashlib.sha256(json.dumps(
        asdict(case), sort_keys=True, separators=(",", ":")
    ).encode("ascii")).hexdigest()
    radio = sr.make_radio(sr.make_args(case))
    by_kind: dict[str, dict[tuple[int, str], list[dict[str, Any]]]] = {}
    for kind, items in records.items():
        groups: dict[tuple[int, str], list[dict[str, Any]]] = {}
        for item in items:
            key = (int(item["seed"]), item["protocol"])
            if (coverage[key] != 1 or item.get("case") != case.key
                    or item.get("seed_split") != expected_split):
                raise ValueError(f"AFS prerequisite {kind} evidence has alien records")
            groups.setdefault(key, []).append(item)
        by_kind[kind] = groups
    trace_by_seed: dict[int, tuple[str, int]] = {}
    run_by_key: dict[tuple[int, str], AfsRun] = {}
    for row in rows:
        seed = int(row["seed"])
        protocol = row["protocol"]
        key = (seed, protocol)
        if (
            row.get("case") != case.key
            or row.get("case_config_sha256") != case_hash
            or row.get("seed_split") != expected_split
            or float(row["generation_horizon_s"]) != case.duration_s
            or float(row["application_deadline_s"]) != 30.0
            or float(row["drain_until_s"]) != case.duration_s + 30.0
            or int(row["scheduled_unicast_flows"]) <= 0
        ):
            raise ValueError("AFS prerequisite run differs from frozen case")
        trace = (row["scheduled_trace_sha256"],
                 int(row["scheduled_unicast_flows"]))
        if seed in trace_by_seed and trace_by_seed[seed] != trace:
            raise ValueError("AFS prerequisite application traces differ across arms")
        trace_by_seed[seed] = trace
        flows = by_kind["flows"].get(key, [])
        scheduled = sorted((float(item["enqueued_at"]), int(item["src"]),
                            int(item["dst"]), int(item["flow_id"]))
                           for item in flows)
        trace_hash = hashlib.sha256(json.dumps(
            scheduled, separators=(",", ":")
        ).encode("ascii")).hexdigest()
        if (len(flows) != int(row["scheduled_unicast_flows"])
                or trace_hash != trace[0]
                or any(item.get("registered") is not True for item in flows)):
            raise ValueError("AFS prerequisite flow schedule differs from runs")
        validate_flow_deadlines(flows, row, case)
        ack_count = sum(item["ack_by_deadline"] is True for item in flows)
        destination_count = sum(item["delivery_by_deadline"] is True
                                for item in flows)
        if (
            ack_count != int(row["ack_by_deadline"])
            or destination_count != int(row["delivery_by_deadline"])
            or abs(ack_count / len(flows) - float(row["ack_pdr_deadline"])) > 1e-10
            or abs(destination_count / len(flows)
                   - float(row["destination_pdr_deadline"])) > 1e-10
        ):
            raise ValueError("AFS prerequisite deadline outcomes differ from flows")
        tx = [{name: value for name, value in item.items()
               if name != "seed_split"} for item in by_kind["tx"].get(key, [])]
        if tx_trace_hash(tx) != row["full_tx_trace_sha256"]:
            raise ValueError("AFS prerequisite complete TX trace differs from runs")
        for item in tx:
            try:
                packet_data = {**item["packet"]}
                packet_data["path"] = tuple(packet_data["path"])
                packet_data["learned_path"] = tuple(packet_data["learned_path"])
                packet = Packet(**packet_data)
                duration = float(item["end"]) - float(item["start"])
                valid_toa = (
                    math.isfinite(duration) and float(item["start"]) >= 0.0
                    and math.isclose(duration, radio.packet_toa_s(packet),
                                     rel_tol=0.0, abs_tol=1e-9)
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError("AFS prerequisite packet ToA is invalid") from exc
            if not valid_toa:
                raise ValueError("AFS prerequisite packet ToA differs from frozen PHY")
        windowed = [item for item in tx if float(item["start"])
                    <= case.duration_s + 30.0]
        if (
            any(float(item["end"]) < float(item["start"]) for item in tx)
            or len(windowed) != int(row["windowed_tx_count"])
            or abs(sum(float(item["end"]) - float(item["start"])
                       for item in windowed)
                   - float(row["whole_network_tx_airtime_s"])) > 1e-8
        ):
            raise ValueError("AFS prerequisite TX cost differs from transcript")
        decodes = by_kind["decodes"].get(key, [])
        tx_by_id = {int(item["tx_id"]): item for item in tx}
        if len(tx_by_id) != len(tx):
            raise ValueError("AFS prerequisite duplicate TX identifiers")
        decode_keys = [(int(item["tx_id"]), int(item["receiver"]))
                       for item in decodes]
        if len(set(decode_keys)) != len(decode_keys):
            raise ValueError("AFS prerequisite duplicate physical ACK decode")
        for decode in decodes:
            reconstruct_decode_witness(decode, tx_by_id, case.max_hops)
        if (
            len(decodes) != int(row["physical_ack_decodes"])
            or sum(item["natural_destination_ack"] for item in decodes)
            != int(row["natural_ack_decodes"])
            or sum(item["natural_destination_ack"] and item["off_path"]
                   for item in decodes) != int(row["offpath_natural_ack_decodes"])
            or sum(item["strict_pending"] for item in decodes)
            != int(row["strict_pending_ack_decodes"])
        ):
            raise ValueError("AFS prerequisite physical decode counts differ")
        actions = by_kind["actions"].get(key, [])
        if (
            sum(item.get("event") == "afs_opportunity" for item in actions)
            != int(row["afs_opportunities"])
            or sum(item.get("event") == "afs_cancel" for item in actions)
            != int(row["afs_cancellations"])
        ):
            raise ValueError("AFS prerequisite cancellation counts differ")
        run_by_key[key] = AfsRun(row, flows, actions, tx, decodes)
    for seed in seeds:
        require_mechanical_parity(run_by_key[(seed, ARMS[1])],
                                  run_by_key[(seed, ARMS[2])])
    comparisons, exposure = evaluate_afs(
        rows, records["actions"], records["decodes"], expected_split
    )
    expected_paired = [{key: str(value) for key, value in item.items()}
                       for item in comparisons]
    if saved_paired != expected_paired:
        raise ValueError("AFS prerequisite paired evidence differs from runs")
    primary = next(item for item in comparisons if item["comparator"] == ARMS[1])
    if (manifest.get("afs_exposure") != exposure
            or manifest.get("afs_project_gate") is not primary["afs_primary_gate"]):
        raise ValueError("AFS prerequisite gate differs from evidence")
    if (expected_split == "development"
            and (manifest.get("afs_development_open_gate") is not True
                 or not primary["afs_primary_gate"])):
        raise ValueError("AFS development gate did not pass; holdout remains closed")
    for seed in seeds:
        for protocol in ARMS:
            replay = run_one_traced(case, protocol, seed)
            if not replay_matches_saved(replay, run_by_key[(seed, protocol)]):
                raise ValueError(
                    f"AFS prerequisite replay evidence differs: seed {seed} {protocol}"
                )
    if input_hashes() != expected_source_sha256:
        raise RuntimeError("AFS source, design, or tests changed during replay")


def run_experiment(
    split: str, out_prefix: Path, *, smoke_manifest: Path | None = None,
    development_manifest: Path | None = None,
) -> dict[str, Path]:
    seeds = seeds_for_split(split)
    if split == "holdout" and development_manifest is None:
        raise ValueError("holdout requires a passing development manifest")
    if split == "development" and smoke_manifest is None:
        raise ValueError("development requires a smoke manifest")
    case = sr.SR_CASES["recurring_fading"]
    source_sha256 = input_hashes()
    if split == "development":
        validate_manifest(smoke_manifest, "smoke", source_sha256)
    if split == "holdout":
        validate_manifest(development_manifest, "development", source_sha256)
    ensure_paths_available(out_prefix)
    runs = []
    for seed in seeds:
        for protocol in ARMS:
            result = run_one_traced(case, protocol, seed)
            if (result.row.get("case") != case.key
                    or result.row.get("protocol") != protocol
                    or int(result.row.get("seed", -1)) != seed):
                raise ValueError("AFS run returned the wrong case, arm, or seed")
            runs.append(result)
        require_mechanical_parity(runs[-2], runs[-1])
    if input_hashes() != source_sha256:
        raise RuntimeError("AFS source, design, or tests changed during the matrix")
    return write_artifacts(out_prefix, case, split, runs, source_sha256)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=tuple(SPLIT_SEEDS), required=True)
    parser.add_argument("--out-prefix", type=Path, required=True)
    parser.add_argument("--smoke-manifest", type=Path)
    parser.add_argument("--development-manifest", type=Path)
    args = parser.parse_args(argv)
    if args.split == "development" and args.smoke_manifest is None:
        parser.error("development requires --smoke-manifest")
    if args.split == "holdout" and args.development_manifest is None:
        parser.error("holdout requires --development-manifest")
    paths = run_experiment(
        args.split, args.out_prefix,
        smoke_manifest=args.smoke_manifest,
        development_manifest=args.development_manifest,
    )
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    print(f"AFS manifest: {paths['manifest']}")
    print(f"AFS project gate: {manifest['afs_project_gate']}")


if __name__ == "__main__":
    main()
