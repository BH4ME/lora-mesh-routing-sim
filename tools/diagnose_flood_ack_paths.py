#!/usr/bin/env python3
"""Passive destination FLOOD-decode diagnostic for the fixed-F DHR control."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from dataclasses import asdict
from pathlib import Path
from statistics import median
from typing import Any, Dict, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import RxInfo, Transmission, build_protocol, generate_nodes
from tools.run_fair_multihop_probe import connected_multihop_pairs, make_args, make_radio
from tools.run_sr_experiment import (
    SR_CASES, RecordingSimulator, SrCase, run_one_sr, schedule_sr_traffic,
)


PROTOCOL = "meshecho-dhr-flood"
EXPLORATORY_SEEDS = (15001, 15002, 15003)
WINDOWS_S = (("0.25s", 0.25), ("0.5s", 0.5), ("1s", 1.0), ("2s", 2.0))


def summarize_one_second_ack_hop_budgets(
    flows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    """Raw remaining deadline for each distinct alternate first ACK hop."""

    budgets = []
    candidate_flows = 0
    for flow in flows:
        if (not flow["delivery_by_deadline"] or flow["ack_by_deadline"]
                or not flow["first_delivery_was_flood"]):
            continue
        paths = flow["oracle_windows"]["1s"]["paths"]
        if not paths:
            continue
        seen_hops = {paths[0]["first_ack_hop"]}
        flow_has_candidate = False
        for path in paths[1:]:
            hop = path["first_ack_hop"]
            if hop is None or hop in seen_hops:
                continue
            seen_hops.add(hop)
            budgets.append(flow["deadline_at"] - path["first_decoded_at_s"])
            flow_has_candidate = True
        candidate_flows += flow_has_candidate
    return {
        "candidate_hops": len(budgets),
        "flows": candidate_flows,
        "min_s": min(budgets) if budgets else None,
        "median_s": median(budgets) if budgets else None,
    }


class FloodAckPathSimulator(RecordingSimulator):
    """Record decoded FLOOD frames without changing receive or protocol behavior."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.destination_flood_receipts: list[Dict[str, Any]] = []

    def try_receive(self, tx: Transmission, receiver: int) -> RxInfo | None:
        decoded = super().try_receive(tx, receiver)
        packet = tx.packet
        if (decoded is not None and packet.kind == "FLOOD"
                and receiver == packet.final_dst
                and packet.request_id == packet.flow_id):
            self.destination_flood_receipts.append({
                "flow_id": packet.flow_id,
                "tx_id": tx.tx_id,
                "received_at_s": self.now,
                "path": packet.path + (receiver,),
                "origin": packet.origin,
                "destination": packet.final_dst,
                "request_id": packet.request_id,
                "ttl": packet.ttl,
                "repair_index": packet.repair_index,
                "rx_snr_db": decoded.snr_db,
                "rx_sinr_db": decoded.sinr_db,
                "rx_power_dbm": decoded.rx_power_dbm,
            })
        return decoded


def analyze_paths(
    receipts: Sequence[Dict[str, Any]], flow_rows: Sequence[Dict[str, Any]],
    actual_destination_acks: Sequence[Dict[str, Any]] = (),
) -> Dict[str, Any]:
    """Count post-delivery decoded paths; future-window grouping is oracle-only."""

    by_flow: Dict[int, list[Dict[str, Any]]] = {}
    for receipt in receipts:
        by_flow.setdefault(receipt["flow_id"], []).append(receipt)
    acks_by_flow: Dict[int, list[Dict[str, Any]]] = {}
    for ack in actual_destination_acks:
        acks_by_flow.setdefault(ack["flow_id"], []).append(ack)
    records = []
    for flow in flow_rows:
        delivered_at = flow["delivered_at"] if flow["delivery_by_deadline"] else None
        decoded = sorted(
            by_flow.get(flow["flow_id"], []),
            key=lambda item: (item["received_at_s"], item.get("tx_id", 0)),
        )
        first_flood_decodes = [
            item for item in decoded
            if delivered_at is not None
            and abs(item["received_at_s"] - delivered_at) <= 1e-9
        ]
        decoded_windows = {}
        oracle_windows = {}
        for label, width_s in WINDOWS_S:
            for target, deadline_at in (
                (decoded_windows, None), (oracle_windows, flow["deadline_at"])
            ):
                first_by_path: Dict[tuple[int, ...], float] = {}
                if delivered_at is not None:
                    for receipt in decoded:
                        received_at = receipt["received_at_s"]
                        if (delivered_at - 1e-9 <= received_at <= delivered_at + width_s + 1e-9
                                and (deadline_at is None
                                     or received_at <= deadline_at + 1e-9)):
                            path = tuple(receipt["path"])
                            first_by_path.setdefault(path, received_at)
                paths = [
                    {"forward_data_path": list(path),
                     "reverse_ack_hop_order": list(reversed(path)),
                     "first_ack_hop": path[-2] if len(path) >= 2 else None,
                     "first_decoded_at_s": first_at,
                     "after_first_delivery_s": first_at - delivered_at}
                    for path, first_at in sorted(
                        first_by_path.items(), key=lambda item: (item[1], item[0])
                    )
                ]
                first_ack_hops = sorted(
                    {path[-2] for path in first_by_path if len(path) >= 2}
                )
                target[label] = {
                    "distinct_paths": len(paths),
                    "additional_paths": max(0, len(paths) - 1),
                    "distinct_first_ack_hops": len(first_ack_hops),
                    "additional_first_ack_hops": max(0, len(first_ack_hops) - 1),
                    "first_ack_hops": first_ack_hops,
                    "paths": paths,
                }
        records.append({
            "flow_id": flow["flow_id"],
            "src": flow["src"],
            "dst": flow["dst"],
            "enqueued_at": flow["enqueued_at"],
            "deadline_at": flow["deadline_at"],
            "source_action": flow["source_action"],
            "first_data_delivery_at_s": delivered_at,
            "delivery_by_deadline": flow["delivery_by_deadline"],
            "ack_by_deadline": flow["ack_by_deadline"],
            "first_delivery_was_flood": bool(first_flood_decodes),
            "first_delivery_was_initial_flood": any(
                item.get("repair_index") is None for item in first_flood_decodes
            ),
            "first_delivery_was_recovery_flood": any(
                item.get("repair_index") == 2 for item in first_flood_decodes
            ),
            "flood_receipts": decoded,
            "actual_destination_ack_emissions": acks_by_flow.get(flow["flow_id"], []),
            "decoded_windows": decoded_windows,
            "oracle_windows": oracle_windows,
        })
    unacked_delivered = [
        flow for flow in records
        if flow["delivery_by_deadline"] and not flow["ack_by_deadline"]
    ]
    return {
        "flows": records,
        "summary": {
            "scheduled_unicast_flows": len(records),
            "one_second_alternate_first_ack_hop_deadline_budget_s": (
                summarize_one_second_ack_hop_budgets(records)
            ),
            "destination_flood_decodes": len(receipts),
            "initial_flood_decodes": sum(
                item.get("repair_index") is None for item in receipts
            ),
            "recovery_flood_decodes": sum(
                item.get("repair_index") == 2 for item in receipts
            ),
            "delivered_unacked_flows": len(unacked_delivered),
            "delivered_unacked_with_flood_decode": sum(
                bool(flow["flood_receipts"]) for flow in unacked_delivered
            ),
            "delivered_unacked_first_delivery_flood": sum(
                flow["first_delivery_was_flood"] for flow in unacked_delivered
            ),
            "delivered_unacked_first_delivery_route": sum(
                not flow["first_delivery_was_flood"] for flow in unacked_delivered
            ),
            "delivered_unacked_first_delivery_initial_flood": sum(
                flow["first_delivery_was_initial_flood"] for flow in unacked_delivered
            ),
            "delivered_unacked_first_delivery_recovery_flood": sum(
                flow["first_delivery_was_recovery_flood"] for flow in unacked_delivered
            ),
            "delivered_unacked_actual_destination_ack_emissions": sum(
                len(flow["actual_destination_ack_emissions"])
                for flow in unacked_delivered
            ),
            "delivered_unacked_with_multiple_decoded_paths": {
                label: sum(
                    flow["decoded_windows"][label]["additional_paths"] > 0
                    for flow in unacked_delivered
                ) for label, _ in WINDOWS_S
            },
            "delivered_unacked_with_alternate_path": {
                label: sum(
                    flow["oracle_windows"][label]["additional_paths"] > 0
                    for flow in unacked_delivered
                ) for label, _ in WINDOWS_S
            },
            "delivered_unacked_first_flood_with_alternate_path": {
                label: sum(
                    flow["first_delivery_was_flood"]
                    and flow["oracle_windows"][label]["additional_paths"] > 0
                    for flow in unacked_delivered
                ) for label, _ in WINDOWS_S
            },
            "delivered_unacked_first_route_with_alternate_flood_path": {
                label: sum(
                    not flow["first_delivery_was_flood"]
                    and flow["oracle_windows"][label]["additional_paths"] > 0
                    for flow in unacked_delivered
                ) for label, _ in WINDOWS_S
            },
            "delivered_unacked_with_alternate_first_ack_hop": {
                label: sum(
                    flow["oracle_windows"][label]["additional_first_ack_hops"] > 0
                    for flow in unacked_delivered
                ) for label, _ in WINDOWS_S
            },
            "delivered_unacked_first_flood_with_alternate_first_ack_hop": {
                label: sum(
                    flow["first_delivery_was_flood"]
                    and flow["oracle_windows"][label]["additional_first_ack_hops"] > 0
                    for flow in unacked_delivered
                ) for label, _ in WINDOWS_S
            },
            "delivered_unacked_first_route_with_alternate_first_ack_hop": {
                label: sum(
                    not flow["first_delivery_was_flood"]
                    and flow["oracle_windows"][label]["additional_first_ack_hops"] > 0
                    for flow in unacked_delivered
                ) for label, _ in WINDOWS_S
            },
        },
        "device_local_receipt_fields": [
            "flow_id", "origin", "destination", "request_id", "ttl",
            "repair_index", "path", "receive_order_or_elapsed_time",
            "rx_snr_db", "rx_power_dbm",
        ],
        "offline_only_fields": [
            "tx_id", "global_simulator_timestamp", "rx_sinr_db",
            "first_data_delivery_truth",
            "enqueued_at", "deadline_at", "source_ack_outcome",
            "posthoc_window_path_set", "deadline_budget_upper_bound",
        ],
        "interpretation": (
            "Each FLOOD receipt is a physical destination decode. The device can "
            "observe packet path/IDs/TTL/repair marker, receive order and radio "
            "RSSI/SNR after decoding; the saved RSSI/SNR numbers are uncalibrated "
            "model proxies. SINR is calculated from overlapping simulator "
            "transmissions, not claimed as a device-local observation. "
            "Absolute simulator time and TX ID are offline "
            "metadata. Decoded windows report physical receptions after first DATA "
            "delivery; oracle windows additionally require the original flow "
            "deadline. Both groupings are retrospective. A reverse path is "
            "only a candidate: distinct full paths may share the same first "
            "reverse ACK hop, and no alternate ACK is sent or credited as success. "
            "For FLOOD-first delivered-unacked flows, the 1s alternate-hop "
            "deadline budget is the original deadline minus each distinct "
            "candidate hop's first decode time. This is an offline feasibility "
            "upper bound before any ACK transmission or relay delay; packet "
            "created_at is simulator-only, not a device-local deadline input."
        ),
    }


def run_diagnostic(
    seed: int, case: SrCase = SR_CASES["recurring_fading"],
    deadline_s: float = 30.0,
) -> Dict[str, Any]:
    """Replay one fixed-F seed and require exact application/outcome parity."""

    if case == SR_CASES["recurring_fading"] and seed not in EXPLORATORY_SEEDS:
        raise ValueError(f"only fresh exploratory seeds {EXPLORATORY_SEEDS} are allowed")
    baseline = run_one_sr(case, PROTOCOL, seed, deadline_s=deadline_s)
    config = make_args(case)
    config.sr_app_deadline_s = deadline_s
    nodes = generate_nodes(case.nodes, case.area_m, random.Random(seed), repeater_ratio=0.0)
    sim = FloodAckPathSimulator(
        nodes, make_radio(config), build_protocol(PROTOCOL, config), seed=seed,
        max_hops=case.max_hops, independent_random_streams=True,
        matched_rreq_timing=case.matched_rreq_timing,
    )
    pairs = []
    if case.pair_mode == "connected-multihop":
        pairs, _ = connected_multihop_pairs(
            sim, random.Random(seed + 20_000), case.edge_prr_threshold,
            case.min_graph_hops, case.max_graph_hops, case.pair_count,
        )
        if len(pairs) != case.pair_count:
            raise ValueError(f"seed {seed}: selected {len(pairs)} of {case.pair_count} pairs")
    elif case.pair_mode != "random":
        raise ValueError(f"unknown pair_mode: {case.pair_mode}")
    schedule_sr_traffic(sim, case, pairs, random.Random(seed + 10_000))
    scheduled = sorted(
        (when, *data) for when, _, kind, data in sim.events if kind == "app_send"
    )
    trace_hash = hashlib.sha256(
        json.dumps(scheduled, separators=(",", ":")).encode("ascii")
    ).hexdigest()
    sim.run(case.duration_s + deadline_s)
    flows = [
        sim.metrics.flows.get(flow_id) for _, _, dst, flow_id in scheduled
        if dst >= 0
    ]
    replay = {
        "scheduled_trace_sha256": trace_hash,
        "scheduled_unicast_flows": len(flows),
        "delivery_by_deadline": sum(
            flow is not None and flow.delivered_at is not None
            and flow.delivered_at <= flow.created_at + deadline_s for flow in flows
        ),
        "ack_by_deadline": sum(
            flow is not None and flow.acked_at is not None
            and flow.acked_at <= flow.created_at + deadline_s for flow in flows
        ),
    }
    baseline_parity = {key: baseline.row[key] for key in replay}
    if baseline_parity != replay:
        raise AssertionError(f"fixed-F replay differs from baseline at seed {seed}")
    outcome_by_flow = {item["flow_id"]: item for item in baseline.flows}
    for flow in flows:
        if flow is None:
            raise AssertionError(f"fixed-F replay omitted a scheduled flow at seed {seed}")
        expected = outcome_by_flow[flow.flow_id]
        if (flow.created_at != expected["enqueued_at"]
                or flow.delivered_at != expected["delivered_at"]
                or flow.acked_at != expected["acked_at"]):
            raise AssertionError(f"fixed-F flow {flow.flow_id} differs at seed {seed}")
    actual_destination_acks = [
        {"flow_id": tx.packet.flow_id, "started_at_s": tx.start,
         "ended_at_s": tx.end, "path": tx.packet.path,
         "repair_index": tx.packet.repair_index}
        for tx in sim.tx_history
        if tx.packet.kind == "ACK" and tx.sender == tx.packet.origin
    ]
    return {
        "seed": seed,
        "case": asdict(case),
        "protocol": PROTOCOL,
        "parity": {"baseline": baseline_parity, "replay": replay,
                   "per_flow_exact_timestamps": True},
        "destination_flood_receipts": sim.destination_flood_receipts,
        "path_analysis": analyze_paths(
            sim.destination_flood_receipts, baseline.flows, actual_destination_acks,
        ),
    }


def build_report(
    seeds: Sequence[int], case: SrCase = SR_CASES["recurring_fading"],
) -> Dict[str, Any]:
    """Collect passive runs with explicit provenance and descriptive totals."""

    runs = [run_diagnostic(seed, case=case) for seed in seeds]
    sources = {
        "diagnostic": Path(__file__).resolve(),
        "simulator": ROOT / "lora_mesh_sim.py",
        "runner": ROOT / "tools" / "run_sr_experiment.py",
        "probe_helpers": ROOT / "tools" / "run_fair_multihop_probe.py",
    }
    summaries = [run["path_analysis"]["summary"] for run in runs]
    return {
        "protocol": PROTOCOL,
        "seed_use": (
            "fresh-exploratory-not-development-or-holdout"
            if case == SR_CASES["recurring_fading"] else "mechanical-test-only"
        ),
        "seeds": list(seeds),
        "case": asdict(case),
        "source_sha256": {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in sources.items()
        },
        "summary": {
            "runs": len(runs),
            "scheduled_unicast_flows": sum(
                run["parity"]["baseline"]["scheduled_unicast_flows"] for run in runs
            ),
            "destination_delivered_by_deadline": sum(
                run["parity"]["baseline"]["delivery_by_deadline"] for run in runs
            ),
            "source_acked_by_deadline": sum(
                run["parity"]["baseline"]["ack_by_deadline"] for run in runs
            ),
            **{
                key: sum(item[key] for item in summaries)
                for key in (
                    "destination_flood_decodes", "initial_flood_decodes",
                    "recovery_flood_decodes", "delivered_unacked_flows",
                    "delivered_unacked_with_flood_decode",
                    "delivered_unacked_first_delivery_flood",
                    "delivered_unacked_first_delivery_route",
                    "delivered_unacked_first_delivery_initial_flood",
                    "delivered_unacked_first_delivery_recovery_flood",
                    "delivered_unacked_actual_destination_ack_emissions",
                )
            },
            **{
                key: {
                    label: sum(item[key][label] for item in summaries)
                    for label, _ in WINDOWS_S
                }
                for key in (
                    "delivered_unacked_with_multiple_decoded_paths",
                    "delivered_unacked_with_alternate_path",
                    "delivered_unacked_first_flood_with_alternate_path",
                    "delivered_unacked_first_route_with_alternate_flood_path",
                    "delivered_unacked_with_alternate_first_ack_hop",
                    "delivered_unacked_first_flood_with_alternate_first_ack_hop",
                    "delivered_unacked_first_route_with_alternate_first_ack_hop",
                )
            },
            "one_second_alternate_first_ack_hop_deadline_budget_s": (
                summarize_one_second_ack_hop_budgets([
                    flow for run in runs for flow in run["path_analysis"]["flows"]
                ])
            ),
        },
        "runs": runs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, choices=EXPLORATORY_SEEDS,
                        default=EXPLORATORY_SEEDS)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"output already exists: {args.output}")
    report = build_report(args.seeds)
    with args.output.open("x", encoding="utf-8") as output:
        json.dump(report, output, indent=2, sort_keys=True)
        output.write("\n")
    print(json.dumps(report["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
