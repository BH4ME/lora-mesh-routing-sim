#!/usr/bin/env python3
"""Exploratory seven-arm source-action diagnostic with physical trace provenance."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_sr_experiment as sr
from lora_mesh_sim import Packet


SEEDS = tuple(range(49301, 49311))
ARMS = (
    "meshecho-dcb",
    "meshecho-dcb-source-fr",
    "meshecho-dcb-source-trigger-f",
    "meshecho-dcb-trial",
    "meshecho-dcb-trial-no-switch",
    "meshecho-dcb-trial-blind",
    "meshecho-dhr-flood-ack-delay",
)
CASE = sr.SR_CASES["recurring_fading"]
DEADLINE_S = 30.0
TX_CUTOFF_S = 630.0
TX_ACTION = {"DATA": "R", "FLOOD": "F", "RREQ": "D"}
SOURCE_FILES = (
    "lora_mesh_sim.py",
    "tools/run_sr_experiment.py",
    "tools/run_fair_multihop_probe.py",
    "tools/screen_source_action_public.py",
    "docs/research/meshecho_source_action_public_diagnostic.md",
)


class PhysicalRecordingSimulator(sr.RecordingSimulator):
    """Retain the physical request-to-start queue delay for every TX."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.tx_queue_metadata: dict[int, dict[str, float]] = {}

    def begin_transmission(self, sender: int, packet: sr.Packet, pending: sr.PendingSend) -> None:
        before = len(self.tx_history)
        requested_at = self.now
        super().begin_transmission(sender, packet, pending)
        if len(self.tx_history) > before:
            tx = self.tx_history[-1]
            self.tx_queue_metadata[tx.tx_id] = {
                "requested_at": requested_at,
                "queue_wait_s": tx.start - requested_at,
            }


make_recorder = PhysicalRecordingSimulator


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def fixed_case_hash() -> str:
    encoded = json.dumps(asdict(CASE), sort_keys=True, separators=(",", ":")).encode("ascii")
    return _sha256(encoded)


def source_hashes() -> dict[str, str]:
    return {name: _sha256((ROOT / name).read_bytes()) for name in SOURCE_FILES}


def capture_arm(seed: int, arm: str) -> dict[str, Any]:
    if type(seed) is not int or seed not in SEEDS or arm not in ARMS:
        raise ValueError("source-action capture requires a seed/arm in the fixed public matrix")
    recorders: list[PhysicalRecordingSimulator] = []

    def recording_factory(*args: Any, **kwargs: Any) -> PhysicalRecordingSimulator:
        recorder = make_recorder(*args, **kwargs)
        recorders.append(recorder)
        return recorder

    with patch.object(sr, "RecordingSimulator", recording_factory):
        result = sr.run_one_sr(CASE, arm, seed, DEADLINE_S)
    if len(recorders) != 1:
        raise ValueError("source-action capture requires exactly one physical recorder")
    recorder = recorders[0]
    transmissions = [
        {**asdict(tx), **recorder.tx_queue_metadata[tx.tx_id]}
        for tx in recorder.tx_history
    ]
    return {
        "row": result.row,
        "flows": result.flows,
        "actions": result.actions,
        "transmissions": transmissions,
    }


def _scheduled_trace(flows: Sequence[Mapping[str, Any]]) -> list[list[Any]]:
    return [list(identity) for identity in sorted(
        (flow["enqueued_at"], flow["src"], flow["dst"], flow["flow_id"])
        for flow in flows
    )]


def _scheduled_hash(flows: Sequence[Mapping[str, Any]]) -> str:
    return _sha256(json.dumps(_scheduled_trace(flows), separators=(",", ":")).encode("ascii"))


def validate_matrix(
    captures: Mapping[tuple[int, str], Mapping[str, Any]], *,
    seeds: Sequence[int] = SEEDS,
) -> None:
    expected = {(seed, arm) for seed in seeds for arm in ARMS}
    if set(captures) != expected or not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("source-action matrix must contain each declared seed/arm exactly once")
    radio = sr.make_radio(sr.make_args(CASE))
    for seed in seeds:
        reference_trace = None
        for arm in ARMS:
            run = captures[(seed, arm)]
            row = run["row"]
            flows = run["flows"]
            if (row.get("case") != CASE.key or row.get("protocol") != arm
                    or row.get("seed") != seed
                    or row.get("case_config_sha256") != fixed_case_hash()
                    or row.get("generation_horizon_s") != CASE.duration_s
                    or row.get("application_deadline_s") != DEADLINE_S
                    or row.get("drain_until_s") != TX_CUTOFF_S):
                raise ValueError("source-action matrix has a wrong fixed case, identity, or deadline")
            if len(flows) != row.get("scheduled_unicast_flows") or not flows:
                raise ValueError("source-action saved flow count differs from scheduled count")
            trace = _scheduled_trace(flows)
            if row.get("scheduled_trace_sha256") != _scheduled_hash(flows):
                raise ValueError("source-action scheduled trace hash differs from saved flows")
            if (len({flow["flow_id"] for flow in flows}) != len(flows)
                    or any(flow["seed"] != seed or flow["protocol"] != arm
                           or flow["case"] != CASE.key
                           or flow["deadline_at"] != flow["enqueued_at"] + DEADLINE_S
                           or not 0 <= flow["enqueued_at"] < CASE.duration_s
                           for flow in flows)):
                raise ValueError("source-action saved scheduled flow identity/deadline differs")
            ack_count = sum(flow["ack_by_deadline"] for flow in flows)
            delivery_count = sum(flow["delivery_by_deadline"] for flow in flows)
            if (any(
                    flow["ack_by_deadline"] != (
                        flow["acked_at"] is not None
                        and flow["enqueued_at"] <= flow["acked_at"] <= flow["deadline_at"]
                    ) or flow["delivery_by_deadline"] != (
                        flow["delivered_at"] is not None
                        and flow["enqueued_at"] <= flow["delivered_at"] <= flow["deadline_at"]
                    ) for flow in flows)
                    or row["ack_by_deadline"] != ack_count
                    or row["delivery_by_deadline"] != delivery_count
                    or not math.isclose(row["ack_pdr_deadline"], ack_count / len(flows), abs_tol=1e-12)
                    or not math.isclose(row["destination_pdr_deadline"], delivery_count / len(flows), abs_tol=1e-12)):
                raise ValueError("source-action deadline outcome differs from timestamps or PDR")
            if reference_trace is not None and reference_trace != trace:
                raise ValueError("source-action paired scheduled traces differ across arms")
            reference_trace = trace
            charged = [tx for tx in run["transmissions"] if tx["start"] <= TX_CUTOFF_S]
            flow_ids = {flow["flow_id"] for flow in flows}
            if (len(run["transmissions"]) != row.get("raw_tx_count")
                    or len(charged) != row.get("windowed_tx_count")
                    or len(run["transmissions"]) - len(charged)
                    != row.get("queued_future_tx_count")
                    or len({tx["tx_id"] for tx in run["transmissions"]})
                    != len(run["transmissions"])
                    or any(tx["end"] < tx["start"]
                           or tx["packet"]["protocol"] != arm
                           or tx["packet"]["flow_id"] not in flow_ids
                           for tx in run["transmissions"])):
                raise ValueError("source-action physical transmission identity or duration invalid")
            airtime = sum(tx["end"] - tx["start"] for tx in charged)
            wire_bytes = sum(
                Packet(**tx["packet"]).wire_size_bytes(CASE.payload_bytes)
                for tx in charged
            )
            expected_energy = (
                airtime * radio.supply_voltage_v * radio.tx_current_ma / 1000.0
            )
            if (not math.isclose(airtime, row["whole_network_tx_airtime_s"], abs_tol=1e-8)
                    or wire_bytes != row["windowed_tx_bytes"]
                    or not math.isclose(expected_energy, row["tx_energy_j"], abs_tol=1e-8)):
                raise ValueError("source-action physical transmission archive differs from network cost")


def _joined_flows(run: Mapping[str, Any]) -> list[dict[str, Any]]:
    decisions = {
        event["flow_id"]: event for event in run["actions"]
        if event.get("event") == "decision"
    }
    joined = []
    for flow in run["flows"]:
        flow_id, src, dst = flow["flow_id"], flow["src"], flow["dst"]
        source_txs = sorted(
            (tx for tx in run["transmissions"]
             if tx["sender"] == src and tx["packet"]["flow_id"] == flow_id
             and tx["packet"]["origin"] == src
             and tx["packet"]["final_dst"] == dst
             and tx["start"] <= TX_CUTOFF_S),
            key=lambda tx: (tx["start"], tx["tx_id"]),
        )
        initial = next(
            (tx for tx in source_txs
             if tx["packet"]["kind"] in TX_ACTION
             and tx["packet"].get("repair_index") is None), None,
        )
        decision = decisions.get(flow_id)
        flow_actions = [
            event for event in run["actions"] if event.get("flow_id") == flow_id
        ]
        candidate_events = [
            event for event in flow_actions if event.get("event") == "candidate"
        ]
        d_timeout_events = [
            event for event in flow_actions
            if event.get("event") == "timeout" and event.get("action") == "D"
            and event.get("reason") in {"rrep-timeout", "source-state-eviction"}
        ]
        post_candidate_txs = [
            tx for tx in source_txs
            if tx["packet"]["kind"] == "DATA"
            and tx["packet"].get("repair_index") is None
            and any(
                tx["start"] >= event["time"]
                and tuple(tx["packet"]["path"]) == tuple(event["path"])
                for event in candidate_events
            )
        ]
        post_timeout_txs = [
            tx for tx in source_txs
            if tx["packet"]["kind"] in {"DATA", "FLOOD"}
            and tx["packet"].get("repair_index") is None
            and any(tx["start"] >= event["time"] for event in d_timeout_events)
        ]
        recovery = [
            {"tx_id": tx["tx_id"], "start": tx["start"],
             "action": TX_ACTION[tx["packet"]["kind"]],
             "repair_index": tx["packet"].get("repair_index"),
             "path": tx["packet"]["path"]}
            for tx in source_txs
            if ((tx["packet"]["kind"], tx["packet"].get("repair_index"))
                in {("DATA", 1), ("FLOOD", 2)}
                or tx in post_timeout_txs)
        ]
        joined.append({
            "flow_id": flow_id, "src": src, "dst": dst,
            "enqueued_at": flow["enqueued_at"], "deadline_at": flow["deadline_at"],
            "decision_action": decision.get("action") if decision else None,
            "decision_reason": decision.get("reason") if decision else None,
            "first_source_physical_action": (
                TX_ACTION[initial["packet"]["kind"]] if initial else None
            ),
            "first_source_tx_id": initial["tx_id"] if initial else None,
            "first_source_tx_start": initial["start"] if initial else None,
            "first_source_path": initial["packet"]["path"] if initial else None,
            "first_source_start_latency_s": (
                initial["start"] - flow["enqueued_at"] if initial else None
            ),
            "source_queue_wait_s": initial["queue_wait_s"] if initial else None,
            "ack_by_deadline": flow["ack_by_deadline"],
            "delivery_by_deadline": flow["delivery_by_deadline"],
            "acked_at": flow["acked_at"], "delivered_at": flow["delivered_at"],
            "eventual_recovery_source_txs": recovery,
            "rrep_candidate": bool(candidate_events),
            "d_candidate_physical": bool(post_candidate_txs),
            "d_timeout": bool(d_timeout_events),
            "d_fallback_physical": bool(post_timeout_txs),
            "accepted_backup_ack": any(
                event.get("event") == "dcb_source_ack_rx"
                and event.get("flow_id") == flow_id and event.get("accepted")
                and len(event.get("path", ())) == 3
                and any(
                    tx["packet"]["kind"] == "ACK"
                    and tx["packet"]["flow_id"] == flow_id
                    and tx["packet"].get("repair_index") == 4
                    and tx["packet"]["origin"] == dst
                    and tx["packet"]["final_dst"] == src
                    and tuple(tx["packet"]["path"]) == tuple(event["path"])
                    and tx["sender"] == event["path"][1]
                    and math.isclose(tx["end"], event["time"], abs_tol=1e-9)
                    for tx in run["transmissions"]
                )
                for event in flow_actions
            ),
        })
    return joined


def summarize_screen(
    captures: Mapping[tuple[int, str], Mapping[str, Any]], *,
    seeds: Sequence[int] = SEEDS,
) -> dict[str, Any]:
    validate_matrix(captures, seeds=seeds)
    joined = {key: _joined_flows(run) for key, run in captures.items()}
    per_seed = []
    for seed in seeds:
        arms = {}
        for arm in ARMS:
            row = captures[(seed, arm)]["row"]
            flows = joined[(seed, arm)]
            arms[arm] = {
                "scheduled_unicast_flows": row["scheduled_unicast_flows"],
                "ack_pdr_deadline": row["ack_pdr_deadline"],
                "destination_pdr_deadline": row["destination_pdr_deadline"],
                "whole_network_tx_airtime_s": row["whole_network_tx_airtime_s"],
                "windowed_tx_bytes": row["windowed_tx_bytes"],
                "tx_energy_j": row["tx_energy_j"],
                "raw_modeled_rx_energy_j": row["raw_modeled_rx_energy_j"],
                "collision_failures": row["collision_failures"],
                "source_queue_wait_s": [flow["source_queue_wait_s"] for flow in flows],
                "whole_network_queue_wait_s": sum(
                    tx["queue_wait_s"] for tx in captures[(seed, arm)]["transmissions"]
                    if tx["start"] <= TX_CUTOFF_S
                ),
                "old_d_cold_decisions": sum(
                    flow["decision_action"] == "D"
                    and flow["decision_reason"] == "repeated-cold-misses"
                    for flow in flows
                ),
                "old_d_aging_decisions": sum(
                    flow["decision_action"] == "D"
                    and flow["decision_reason"] == "aging-confirmed-route"
                    for flow in flows
                ),
                "d_physical_rreq": sum(
                    flow["decision_action"] == "D"
                    and flow["first_source_physical_action"] == "D"
                    for flow in flows
                ),
                "d_rrep_candidates": sum(
                    flow["decision_action"] == "D" and flow["rrep_candidate"]
                    for flow in flows
                ),
                "d_rrep_candidate_physical": sum(
                    flow["decision_action"] == "D" and flow["d_candidate_physical"]
                    for flow in flows
                ),
                "d_timeouts": sum(
                    flow["decision_action"] == "D" and flow["d_timeout"]
                    for flow in flows
                ),
                "d_physical_fallbacks": sum(
                    flow["decision_action"] == "D" and flow["d_fallback_physical"]
                    for flow in flows
                ),
                "one_miss_f_decisions": sum(
                    flow["decision_action"] == "F"
                    and flow["decision_reason"] == "route-ack-miss"
                    for flow in flows
                ),
                "one_miss_f_physical_starts": sum(
                    flow["decision_action"] == "F"
                    and flow["decision_reason"] == "route-ack-miss"
                    and flow["first_source_physical_action"] == "F"
                    for flow in flows
                ),
                "accepted_backup_acks": sum(flow["accepted_backup_ack"] for flow in flows),
            }
        old_flows = {flow["flow_id"]: flow for flow in joined[(seed, ARMS[0])]}
        old_d_ids = {
            flow_id for flow_id, flow in old_flows.items()
            if flow["decision_action"] == "D"
        }
        replacements = {}
        divergence = {}
        paired_deltas = {}
        for arm in ARMS[1:]:
            current = {flow["flow_id"]: flow for flow in joined[(seed, arm)]}
            replacements[arm] = {
                "old_d_flow_count": len(old_d_ids),
                "decision_actions": dict(Counter(
                    current[flow_id]["decision_action"] or "none"
                    for flow_id in old_d_ids
                )),
                "physical_actions": dict(Counter(
                    current[flow_id]["first_source_physical_action"] or "none"
                    for flow_id in old_d_ids
                )),
            }
            action_diffs = {
                flow_id for flow_id, prior in old_flows.items()
                if prior["first_source_physical_action"]
                != current[flow_id]["first_source_physical_action"]
            }
            path_diffs = {
                flow_id for flow_id, prior in old_flows.items()
                if prior["first_source_physical_action"] == "R"
                and current[flow_id]["first_source_physical_action"] == "R"
                and prior["first_source_path"] != current[flow_id]["first_source_path"]
            }
            divergence[arm] = {
                "action": len(action_diffs),
                "route_path": len(path_diffs),
                "action_or_route_path": len(action_diffs | path_diffs),
            }
            prior_metrics, current_metrics = arms[ARMS[0]], arms[arm]
            prior_airtime = prior_metrics["whole_network_tx_airtime_s"]
            paired_deltas[arm] = {
                "ack_pdr_delta": current_metrics["ack_pdr_deadline"]
                - prior_metrics["ack_pdr_deadline"],
                "destination_pdr_delta": current_metrics["destination_pdr_deadline"]
                - prior_metrics["destination_pdr_deadline"],
                "airtime_delta_s": current_metrics["whole_network_tx_airtime_s"]
                - prior_airtime,
                "relative_airtime_delta": (
                    current_metrics["whole_network_tx_airtime_s"] / prior_airtime - 1.0
                    if prior_airtime > 0 else None
                ),
                "windowed_tx_energy_delta_j": (
                    current_metrics["tx_energy_j"] - prior_metrics["tx_energy_j"]
                ),
                "raw_modeled_rx_energy_delta_j": (
                    current_metrics["raw_modeled_rx_energy_j"]
                    - prior_metrics["raw_modeled_rx_energy_j"]
                ),
                "tx_bytes_delta": current_metrics["windowed_tx_bytes"]
                - prior_metrics["windowed_tx_bytes"],
                "collision_failures_delta": current_metrics["collision_failures"]
                - prior_metrics["collision_failures"],
                "whole_network_queue_wait_delta_s": current_metrics["whole_network_queue_wait_s"]
                - prior_metrics["whole_network_queue_wait_s"],
            }
        per_seed.append({
            "seed": seed, "arms": arms,
            "old_d_replacements": replacements,
            "physical_divergence_from_old_dcb": divergence,
            "paired_deltas_from_old_dcb": paired_deltas,
        })
    intervals = {}
    for arm in ARMS[1:]:
        metrics = per_seed[0]["paired_deltas_from_old_dcb"][arm]
        intervals[arm] = {}
        for name in metrics:
            values = [
                item["paired_deltas_from_old_dcb"][arm][name] for item in per_seed
                if item["paired_deltas_from_old_dcb"][arm][name] is not None
            ]
            mean, low, high = sr.paired_mean_ci(values)
            intervals[arm][name] = {
                "n": len(values), "mean": mean,
                "ci95_low": low, "ci95_high": high,
            }
    return {
        "fixed_inputs": {"case": asdict(CASE), "case_config_sha256": fixed_case_hash(),
                         "seeds": list(seeds), "arms": list(ARMS),
                         "application_deadline_s": DEADLINE_S,
                         "tx_start_cost_cutoff_s": TX_CUTOFF_S,
                         "independent_channel_streams": True},
        "joined_flows": joined,
        "per_seed": per_seed,
        "exploratory_intervals_from_old_dcb": intervals,
    }


def write_artifacts(
    prefix: Path,
    captures: Mapping[tuple[int, str], Mapping[str, Any]],
    summary: Mapping[str, Any],
    source_sha256: Mapping[str, str],
) -> dict[str, Path]:
    """Write lossless JSONL records and a manifest without replacing prior evidence."""
    seeds = tuple(summary["fixed_inputs"]["seeds"])
    validate_matrix(captures, seeds=seeds)
    if (summary["fixed_inputs"]["case_config_sha256"] != fixed_case_hash()
            or tuple(summary["fixed_inputs"]["arms"]) != ARMS
            or len(summary["per_seed"]) != len(seeds)):
        raise ValueError("source-action summary differs from validated matrix")
    paths = {name: Path(f"{prefix}.{name}.jsonl") for name in (
        "runs", "flows", "actions", "transmissions", "joined_flows", "per_seed",
    )}
    paths["manifest"] = Path(f"{prefix}.manifest.json")
    if not prefix.parent.is_dir():
        raise FileNotFoundError(f"output directory does not exist: {prefix.parent}")
    for path in paths.values():
        if path.exists():
            raise FileExistsError(f"source-action artifact already exists: {path}")

    records: dict[str, list[dict[str, Any]]] = {name: [] for name in paths if name != "manifest"}
    for seed in seeds:
        for arm in ARMS:
            run = captures[(seed, arm)]
            records["runs"].append(dict(run["row"]))
            records["flows"].extend(dict(flow) for flow in run["flows"])
            records["actions"].extend(dict(event) for event in run["actions"])
            records["transmissions"].extend(
                {"seed": seed, "protocol": arm, **tx} for tx in run["transmissions"]
            )
            records["joined_flows"].extend(
                {"seed": seed, "protocol": arm, **flow}
                for flow in summary["joined_flows"][(seed, arm)]
            )
    records["per_seed"] = [dict(row) for row in summary["per_seed"]]

    artifact_hashes = {}
    for name, rows in records.items():
        path = paths[name]
        with path.open("x", encoding="utf-8", newline="\n") as output:
            for row in rows:
                output.write(json.dumps(row, sort_keys=True, separators=(",", ":"), allow_nan=False))
                output.write("\n")
        artifact_hashes[name] = _sha256(path.read_bytes())

    manifest = {
        "status": "exploratory mechanism diagnostic; not confirmation or per-flow counterfactual",
        "fixed_inputs": summary["fixed_inputs"],
        "scheduled_trace_sha256": {
            str(seed): captures[(seed, ARMS[0])]["row"]["scheduled_trace_sha256"]
            for seed in seeds
        },
        "source_sha256": dict(source_sha256),
        "artifact_sha256": artifact_hashes,
        "record_counts": {name: len(rows) for name, rows in records.items()},
        "exploratory_intervals_from_old_dcb": summary["exploratory_intervals_from_old_dcb"],
    }
    with paths["manifest"].open("x", encoding="utf-8", newline="\n") as output:
        json.dump(manifest, output, sort_keys=True, indent=2, allow_nan=False)
        output.write("\n")
    return paths


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-public-screen", action="store_true")
    parser.add_argument("--out-prefix", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.run_public_screen:
        parser.error("explicit --run-public-screen is required")
    if not args.out_prefix.parent.is_dir():
        raise FileNotFoundError(f"output directory does not exist: {args.out_prefix.parent}")
    suffixes = (
        "runs.jsonl", "flows.jsonl", "actions.jsonl", "transmissions.jsonl",
        "joined_flows.jsonl", "per_seed.jsonl", "manifest.json",
    )
    for suffix in suffixes:
        path = Path(f"{args.out_prefix}.{suffix}")
        if path.exists():
            raise FileExistsError(f"source-action artifact already exists: {path}")

    hashes_before = source_hashes()
    captures = {
        (seed, arm): capture_arm(seed, arm)
        for seed in SEEDS for arm in ARMS
    }
    summary = summarize_screen(captures, seeds=SEEDS)
    if hashes_before != source_hashes():
        raise ValueError("source-action source files changed during capture")
    paths = write_artifacts(args.out_prefix, captures, summary, hashes_before)
    print(paths["manifest"])


if __name__ == "__main__":
    main()
