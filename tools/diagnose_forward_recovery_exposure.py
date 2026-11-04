#!/usr/bin/env python3
"""Passive fixed-F DHR forward-recovery exposure diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import RxInfo, Transmission, build_protocol, generate_nodes
from tools.run_fair_multihop_probe import connected_multihop_pairs, make_args, make_radio
from tools.run_sr_experiment import (
    RecordingSimulator, SR_CASES, SrCase, run_one_sr, schedule_sr_traffic,
)


PROTOCOL = "meshecho-dhr-flood"
EXPLORATORY_SEEDS = (18001, 18002, 18003)
RESERVED_HOLDOUT_SEEDS = frozenset(range(17001, 17041))
HOP_DELTA_BINS = ("negative", "zero", "plus_1", "plus_2_or_more")


def _hop_delta_bin(delta: int) -> str:
    if delta < 0:
        return "negative"
    if delta == 0:
        return "zero"
    if delta == 1:
        return "plus_1"
    return "plus_2_or_more"


class ForwardRecoverySimulator(RecordingSimulator):
    """Observe successful recovery-F decodes without changing reception."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.destination_flood_decodes: list[Dict[str, Any]] = []

    def try_receive(self, tx: Transmission, receiver: int) -> RxInfo | None:
        decoded = super().try_receive(tx, receiver)
        packet = tx.packet
        if (decoded is not None and packet.kind == "FLOOD"
                and packet.repair_index == 2 and receiver == packet.final_dst):
            self.destination_flood_decodes.append({
                "flow_id": packet.flow_id,
                "tx_id": tx.tx_id,
                "time": self.now,
                "path": packet.path + (receiver,),
            })
        return decoded


def analyze_forward_recovery(
    flow_rows: Sequence[Dict[str, Any]],
    actions: Sequence[Dict[str, Any]],
    transmissions: Sequence[Transmission],
    flood_decodes: Sequence[Dict[str, Any]],
    cutoff_s: float,
) -> Dict[str, Any]:
    """Attribute only actually observed route/FLOOD events and charged TXs."""

    events_by_flow: Dict[int, list[Dict[str, Any]]] = defaultdict(list)
    tx_by_flow: Dict[int, list[Transmission]] = defaultdict(list)
    decodes_by_flow: Dict[int, list[Dict[str, Any]]] = defaultdict(list)
    for event in actions:
        if "flow_id" in event:
            events_by_flow[event["flow_id"]].append(event)
    for tx in transmissions:
        if tx.start <= cutoff_s:
            tx_by_flow[tx.packet.flow_id].append(tx)
    for decode in flood_decodes:
        decodes_by_flow[decode["flow_id"]].append(decode)

    depth: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"tx": 0, "airtime_s": 0.0,
                 "tx_after_first_f_decode": 0,
                 "airtime_after_first_f_decode_s": 0.0,
                 "relay_tx_after_first_destination_delivery": 0,
                 "relay_airtime_after_first_destination_delivery_s": 0.0}
    )
    records = []
    for flow in flow_rows:
        flow_id = flow["flow_id"]
        flow_events = events_by_flow[flow_id]
        flow_txs = tx_by_flow[flow_id]
        guards = [item for item in flow_events if item.get("event") == "dhr_guard"]
        if len(guards) > 1:
            raise AssertionError(f"flow {flow_id} has multiple DHR guards")
        guard = guards[0] if guards else None
        first_r_source = next((
            tx for tx in flow_txs
            if tx.sender == flow["src"] and tx.packet.kind == "DATA"
            and tx.packet.repair_index is None
        ), None)
        first_r_receipts = sorted(
            item["time"] for item in flow_events
            if item.get("event") == "dhr_destination_rx"
            and item.get("repair_index") is None
            and item["time"] <= flow["deadline_at"]
        )
        f_source = next((
            tx for tx in flow_txs
            if tx.sender == flow["src"] and tx.packet.kind == "FLOOD"
            and tx.packet.repair_index == 2
        ), None)
        decoded = sorted(
            decodes_by_flow[flow_id], key=lambda item: (item["time"], item["tx_id"])
        )
        protocol_f_receipts = sorted(
            item["time"] for item in flow_events
            if item.get("event") == "dhr_destination_rx"
            and item.get("repair_index") == 2
        )
        if protocol_f_receipts != sorted(item["time"] for item in decoded):
            raise AssertionError(f"flow {flow_id} F decode attribution differs")
        timely_decoded = [
            item for item in decoded if item["time"] <= flow["deadline_at"]
        ]
        f_first_delivery = bool(
            f_source is not None and timely_decoded
            and flow["delivery_by_deadline"]
            and abs(timely_decoded[0]["time"] - flow["delivered_at"]) <= 1e-9
        )
        f_txs = [
            tx for tx in flow_txs
            if tx.packet.kind == "FLOOD" and tx.packet.repair_index == 2
        ]
        first_f_decode_at = decoded[0]["time"] if decoded else None
        after_first_f_decode = [
            tx for tx in f_txs
            if first_f_decode_at is not None and tx.start > first_f_decode_at + 1e-9
        ]
        relay_after_first_delivery = [
            tx for tx in f_txs
            if tx.sender != flow["src"] and flow["delivered_at"] is not None
            and tx.start > flow["delivered_at"] + 1e-9
        ]
        for tx in f_txs:
            bucket = depth[str(len(tx.packet.path) - 1)]
            bucket["tx"] += 1
            bucket["airtime_s"] += tx.end - tx.start
            if tx in after_first_f_decode:
                bucket["tx_after_first_f_decode"] += 1
                bucket["airtime_after_first_f_decode_s"] += tx.end - tx.start
            if tx in relay_after_first_delivery:
                bucket["relay_tx_after_first_destination_delivery"] += 1
                bucket["relay_airtime_after_first_destination_delivery_s"] += (
                    tx.end - tx.start
                )
        records.append({
            "flow_id": flow_id,
            "src": flow["src"],
            "dst": flow["dst"],
            "source_action": flow["source_action"],
            "deadline_at_s": flow["deadline_at"],
            "guard_at_s": guard["time"] if guard else None,
            "guard_admitted": bool(guard and guard["admitted"]),
            "guard_reason": guard["reason"] if guard else None,
            "deadline_remaining_at_guard_s": (
                flow["deadline_at"] - guard["time"] if guard else None
            ),
            "source_known_initial_path_hops": (
                len(first_r_source.packet.path) - 1 if first_r_source else None
            ),
            "initial_r_destination_rx_at_s": first_r_receipts,
            "initial_r_delivered_before_guard": bool(
                guard and first_r_receipts and first_r_receipts[0] <= guard["time"]
            ),
            "f_recovery_source_tx_at_s": f_source.start if f_source else None,
            "deadline_remaining_at_f_tx_s": (
                flow["deadline_at"] - f_source.start if f_source else None
            ),
            "f_recovery_first_decode_at_s": decoded[0]["time"] if decoded else None,
            "deadline_remaining_at_first_f_decode_s": (
                flow["deadline_at"] - decoded[0]["time"] if decoded else None
            ),
            "f_recovery_decoded_path_hops": [
                len(item["path"]) - 1 for item in decoded
            ],
            "f_recovery_timely_decoded_path_hops": [
                len(item["path"]) - 1 for item in timely_decoded
            ],
            "f_recovery_first_delivery_path_hops": (
                len(timely_decoded[0]["path"]) - 1 if f_first_delivery else None
            ),
            "f_recovery_any_destination_decode": bool(timely_decoded),
            "f_recovery_first_delivery": f_first_delivery,
            "f_recovery_tx": len(f_txs),
            "f_recovery_relay_tx": sum(tx.sender != flow["src"] for tx in f_txs),
            "f_recovery_airtime_s": sum(tx.end - tx.start for tx in f_txs),
            "f_recovery_tx_after_first_f_decode": len(after_first_f_decode),
            "f_recovery_airtime_after_first_f_decode_s": sum(
                tx.end - tx.start for tx in after_first_f_decode
            ),
            "f_recovery_relay_tx_after_first_destination_delivery": (
                len(relay_after_first_delivery)
            ),
            "f_recovery_relay_airtime_after_first_destination_delivery_s": sum(
                tx.end - tx.start for tx in relay_after_first_delivery
            ),
            "delivered_at_s": flow["delivered_at"],
            "acked_at_s": flow["acked_at"],
        })
    admitted = [item for item in records if item["guard_admitted"]]
    return {
        "summary": {
            "scheduled_unicast_flows": len(records),
            "r_timeout_guards": sum(item["guard_at_s"] is not None for item in records),
            "admitted_r_timeouts": len(admitted),
            "initial_r_delivered_before_guard": sum(
                item["initial_r_delivered_before_guard"] for item in admitted
            ),
            "f_recovery_source_tx": sum(
                item["f_recovery_source_tx_at_s"] is not None for item in admitted
            ),
            "f_recovery_any_destination_decode": sum(
                item["f_recovery_any_destination_decode"] for item in admitted
            ),
            "f_recovery_first_delivery": sum(
                item["f_recovery_first_delivery"] for item in admitted
            ),
            "f_recovery_tx": sum(item["f_recovery_tx"] for item in records),
            "f_recovery_relay_tx": sum(item["f_recovery_relay_tx"] for item in records),
            "f_recovery_airtime_s": sum(item["f_recovery_airtime_s"] for item in records),
            "f_recovery_tx_after_first_f_decode": sum(
                item["f_recovery_tx_after_first_f_decode"] for item in records
            ),
            "f_recovery_airtime_after_first_f_decode_s": sum(
                item["f_recovery_airtime_after_first_f_decode_s"]
                for item in records
            ),
            "f_recovery_relay_tx_after_first_destination_delivery": sum(
                item["f_recovery_relay_tx_after_first_destination_delivery"]
                for item in records
            ),
            "f_recovery_relay_airtime_after_first_destination_delivery_s": sum(
                item["f_recovery_relay_airtime_after_first_destination_delivery_s"]
                for item in records
            ),
            "first_f_path_minus_initial_hops": {
                category: sum(
                    item["f_recovery_first_delivery"]
                    and item["source_known_initial_path_hops"] is not None
                    and _hop_delta_bin(
                        item["f_recovery_first_delivery_path_hops"]
                        - item["source_known_initial_path_hops"]
                    ) == category for item in records
                ) for category in HOP_DELTA_BINS
            },
        },
        "flood_tx_by_depth": dict(sorted(depth.items(), key=lambda item: int(item[0]))),
        "flows": records,
    }


def _replay(
    case: SrCase, seed: int, deadline_s: float, observed: bool,
) -> tuple[RecordingSimulator, str]:
    config = make_args(case)
    config.sr_app_deadline_s = deadline_s
    nodes = generate_nodes(
        case.nodes, case.area_m, random.Random(seed), repeater_ratio=0.0
    )
    simulator_class = ForwardRecoverySimulator if observed else RecordingSimulator
    sim = simulator_class(
        nodes, make_radio(config), build_protocol(PROTOCOL, config),
        seed=seed, max_hops=case.max_hops, independent_random_streams=True,
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
    trace_sha256 = hashlib.sha256(
        json.dumps(scheduled, separators=(",", ":")).encode("ascii")
    ).hexdigest()
    sim.run(case.duration_s + deadline_s)
    return sim, trace_sha256


def _tx_trace_sha256(transmissions: Sequence[Transmission]) -> str:
    trace = [
        (tx.tx_id, tx.sender, tx.start, tx.end, asdict(tx.packet))
        for tx in transmissions
    ]
    return hashlib.sha256(
        json.dumps(trace, sort_keys=True, separators=(",", ":")).encode("ascii")
    ).hexdigest()


def _verify_against_baseline(
    sim: RecordingSimulator, baseline: Any, case: SrCase, seed: int,
) -> None:
    for expected in baseline.flows:
        flow = sim.metrics.flows.get(expected["flow_id"])
        if (flow is None or flow.src != expected["src"]
                or flow.dst != expected["dst"]
                or flow.created_at != expected["enqueued_at"]
                or flow.delivered_at != expected["delivered_at"]
                or flow.acked_at != expected["acked_at"]
                or sim.protocol.flow_data_actions.get(flow.flow_id)
                != expected["source_action"]):
            raise AssertionError(
                f"fixed-F seed {seed} flow {expected['flow_id']} differs from baseline"
            )
    expected_actions = [
        {"case": case.key, "protocol": PROTOCOL, "seed": seed, **event}
        for event in sim.protocol.action_events
    ]
    if expected_actions != baseline.actions:
        raise AssertionError(f"fixed-F seed {seed} protocol actions differ from baseline")
    for name, actual in (
        ("raw_tx_count", sim.metrics.tx_count),
        ("raw_data_tx", sim.metrics.data_tx),
        ("raw_control_tx", sim.metrics.control_tx),
        ("collision_failures", sim.metrics.collision_fail),
    ):
        if baseline.row[name] != actual:
            raise AssertionError(f"fixed-F seed {seed} {name} differs from baseline")


def run_diagnostic(
    seed: int, case: SrCase = SR_CASES["recurring_fading"],
    deadline_s: float = 30.0,
) -> Dict[str, Any]:
    """Run a passive replay and refuse any baseline or TX-trace divergence."""

    if seed in RESERVED_HOLDOUT_SEEDS:
        raise ValueError("BAR holdout seeds 17001-17040 are reserved")
    if case == SR_CASES["recurring_fading"] and seed not in EXPLORATORY_SEEDS:
        raise ValueError(f"only exploratory seeds {EXPLORATORY_SEEDS} are allowed")
    baseline = run_one_sr(case, PROTOCOL, seed, deadline_s=deadline_s)
    plain, plain_trace = _replay(case, seed, deadline_s, observed=False)
    instrumented, observed_trace = _replay(case, seed, deadline_s, observed=True)
    if not (baseline.row["scheduled_trace_sha256"] == plain_trace == observed_trace):
        raise AssertionError(f"fixed-F seed {seed} application trace differs")
    for sim in (plain, instrumented):
        _verify_against_baseline(sim, baseline, case, seed)
    plain_tx_sha = _tx_trace_sha256(plain.tx_history)
    observed_tx_sha = _tx_trace_sha256(instrumented.tx_history)
    if plain_tx_sha != observed_tx_sha:
        raise AssertionError(f"fixed-F seed {seed} complete TX trace differs")
    return {
        "seed": seed,
        "case": asdict(case),
        "protocol": PROTOCOL,
        "parity": {
            "baseline_scheduled_trace_sha256": baseline.row["scheduled_trace_sha256"],
            "plain_scheduled_trace_sha256": plain_trace,
            "observed_scheduled_trace_sha256": observed_trace,
            "plain_full_tx_trace_sha256": plain_tx_sha,
            "observed_full_tx_trace_sha256": observed_tx_sha,
            "per_flow_exact_timestamps": True,
            "action_events_exact": True,
            "full_tx_trace_exact": True,
        },
        "baseline_row": baseline.row,
        "analysis": analyze_forward_recovery(
            baseline.flows, baseline.actions, instrumented.tx_history,
            instrumented.destination_flood_decodes,
            cutoff_s=case.duration_s + deadline_s,
        ),
    }


def build_report(
    seeds: Sequence[int] = EXPLORATORY_SEEDS,
    case: SrCase = SR_CASES["recurring_fading"],
    deadline_s: float = 30.0,
) -> Dict[str, Any]:
    """Collect the unchanged fixed-F observations with source provenance."""

    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be nonempty and unique")
    source_paths = (
        ROOT / "lora_mesh_sim.py",
        ROOT / "tools" / "run_fair_multihop_probe.py",
        ROOT / "tools" / "run_sr_experiment.py",
        ROOT / "docs" / "research" / "meshecho_dhr_design.md",
        Path(__file__).resolve(),
        ROOT / "tests" / "test_forward_recovery_exposure.py",
    )

    def source_hashes() -> Dict[str, str]:
        return {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in source_paths
        }

    before = source_hashes()
    runs = [run_diagnostic(seed, case=case, deadline_s=deadline_s) for seed in seeds]
    if source_hashes() != before:
        raise RuntimeError("diagnostic source changed during exploratory replays")
    numeric_keys = (
        key for key, value in runs[0]["analysis"]["summary"].items()
        if isinstance(value, (int, float))
    )
    all_flows = [flow for run in runs for flow in run["analysis"]["flows"]]
    depth: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "tx": 0, "airtime_s": 0.0,
        "tx_after_first_f_decode": 0,
        "airtime_after_first_f_decode_s": 0.0,
        "relay_tx_after_first_destination_delivery": 0,
        "relay_airtime_after_first_destination_delivery_s": 0.0,
    })
    for run in runs:
        for hop_depth, counts in run["analysis"]["flood_tx_by_depth"].items():
            for key, value in counts.items():
                depth[hop_depth][key] += value
    admitted = [flow for flow in all_flows if flow["guard_admitted"]]
    first_f_deliveries = [
        flow for flow in admitted if flow["f_recovery_first_delivery"]
    ]
    guard_slack = [flow["deadline_remaining_at_guard_s"] for flow in admitted]
    f_decode_slack = [
        flow["deadline_remaining_at_first_f_decode_s"] for flow in admitted
        if flow["f_recovery_any_destination_decode"]
    ]

    def distribution(values: Sequence[float]) -> Dict[str, Any]:
        return {
            "count": len(values),
            "min": min(values) if values else None,
            "median": statistics.median(values) if values else None,
            "max": max(values) if values else None,
        }

    return {
        "analysis_type": "passive actual fixed-F DHR forward recovery exposure",
        "counterfactual_estimates": None,
        "seed_use": (
            "fresh-exploratory-not-development-or-holdout"
            if case == SR_CASES["recurring_fading"] else "mechanical-test-only"
        ),
        "seeds": list(seeds),
        "case": asdict(case),
        "deadline_s": deadline_s,
        "source_sha256": before,
        "summary": {
            **{key: sum(run["analysis"]["summary"][key] for run in runs)
               for key in numeric_keys},
            "source_known_initial_path_hops_admitted": dict(sorted(Counter(
                str(flow["source_known_initial_path_hops"]) for flow in admitted
            ).items())),
            "f_recovery_decoded_path_hops_all": dict(sorted(Counter(
                str(hops) for flow in admitted
                for hops in flow["f_recovery_decoded_path_hops"]
            ).items())),
            "f_recovery_first_delivery_path_hops": dict(sorted(Counter(
                str(flow["f_recovery_first_delivery_path_hops"])
                for flow in first_f_deliveries
            ).items())),
            "first_f_path_minus_initial_hops": {
                category: sum(
                    run["analysis"]["summary"]["first_f_path_minus_initial_hops"][category]
                    for run in runs
                ) for category in HOP_DELTA_BINS
            },
            "first_f_hop_delta_by_initial_hops": {
                str(initial_hops): {
                    category: sum(
                        _hop_delta_bin(
                            flow["f_recovery_first_delivery_path_hops"] - initial_hops
                        ) == category
                        for flow in first_f_deliveries
                        if flow["source_known_initial_path_hops"] == initial_hops
                    ) for category in HOP_DELTA_BINS
                }
                for initial_hops in sorted({
                    flow["source_known_initial_path_hops"]
                    for flow in first_f_deliveries
                })
            },
            "first_f_without_timely_decoded_path_within_initial_hops": sum(
                all(hops > flow["source_known_initial_path_hops"]
                    for hops in flow["f_recovery_timely_decoded_path_hops"])
                for flow in first_f_deliveries
            ),
            "deadline_remaining_at_guard_s": distribution(guard_slack),
            "deadline_remaining_at_first_f_decode_s": distribution(f_decode_slack),
        },
        "flood_tx_by_depth": dict(sorted(depth.items(), key=lambda item: int(item[0]))),
        "interpretation_boundary": (
            "Observed outcomes and full-network transmissions only. Path, first-"
            "delivery and deadline comparisons are offline diagnostics, not source-"
            "observable inputs or causal estimates of a different flood radius. "
            "Post-decode transmissions may have been queued or already on air."
        ),
        "runs": runs,
    }


def write_report(report: Dict[str, Any], path: Path) -> str:
    """Write one immutable JSON artifact and return its SHA-256 digest."""

    data = (json.dumps(report, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode("ascii")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(data)
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report()
    digest = write_report(report, args.output)
    print(f"Report: {args.output}")
    print(f"SHA-256: {digest}")
    print(json.dumps(report["summary"], sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
