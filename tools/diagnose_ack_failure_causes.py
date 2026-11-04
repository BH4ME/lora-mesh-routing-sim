#!/usr/bin/env python3
"""Observe physical causes of failed ACK hops without changing MeshEcho."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import Packet, PendingSend, Simulator, Transmission, build_protocol, generate_nodes
from tools.diagnose_flood_ack_hops import AckHopSimulator, analyze_ack_hops
from tools.run_fair_multihop_probe import connected_multihop_pairs, make_args, make_radio
from tools.run_sr_experiment import (
    SR_CASES, RecordingSimulator, SrCase, run_one_sr,
    schedule_sr_traffic, summarize_windowed_transmissions,
)


PROTOCOL = "meshecho-dhr-flood"
SMOKE_SEEDS = (37000,)
EXPLORATORY_SEEDS = (37001, 37002, 37003)
SOURCE_FILES = (
    ROOT / "lora_mesh_sim.py",
    ROOT / "tools" / "run_fair_multihop_probe.py",
    ROOT / "tools" / "run_sr_experiment.py",
    ROOT / "tools" / "diagnose_flood_ack_hops.py",
    Path(__file__).resolve(),
    ROOT / "tests" / "test_ack_failure_causes.py",
    ROOT / "docs" / "research" / "meshecho_ack_failure_cause_diagnostic_design.md",
)


def seeds_for_mode(mode: str) -> tuple[int, ...]:
    if mode == "smoke":
        return SMOKE_SEEDS
    if mode == "explore":
        return EXPLORATORY_SEEDS
    raise ValueError(f"unknown ACK failure-cause diagnostic mode: {mode}")


class CauseSimulator(AckHopSimulator):
    """Retain the TX booking time while inheriting passive ACK-hop tracing."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.tx_commitment_times: dict[int, float] = {}

    def begin_transmission(
        self, sender: int, packet: Packet, pending: PendingSend,
    ) -> None:
        previous_count = self.metrics.tx_count
        committed_at = self.now
        super().begin_transmission(sender, packet, pending)
        if self.metrics.tx_count > previous_count:
            self.tx_commitment_times[self.tx_history[-1].tx_id] = committed_at


def classify_failed_hop(
    sim: Simulator, ack: Transmission, receiver: int,
    transmissions: Sequence[Transmission], commitment_times: Mapping[int, float],
    first_delivery_at_s: float | None,
) -> dict[str, Any]:
    """Classify an already observed ACK decode failure from its TX overlap."""

    overlapping = [
        other for other in transmissions
        if other.tx_id != ack.tx_id
        and other.start < ack.end and ack.start < other.end
    ]

    def evidence(other: Transmission) -> dict[str, Any]:
        return {
            "tx_id": other.tx_id,
            "sender": other.sender,
            "kind": other.packet.kind,
            "flow_id": other.packet.flow_id,
            "start_at_s": other.start,
            "end_at_s": other.end,
            "committed_at_s": commitment_times[other.tx_id],
            "same_flow": other.packet.flow_id == ack.packet.flow_id,
            "started_after_first_delivery": (
                first_delivery_at_s is not None
                and other.start > first_delivery_at_s
            ),
            "received_power_dbm": (
                None if other.sender == receiver
                else sim.rx_power_dbm(other.sender, receiver, when=other.start)
            ),
        }

    own = [evidence(other) for other in overlapping if other.sender == receiver]
    interferers = [evidence(other) for other in overlapping if other.sender != receiver]
    signal_dbm = sim.rx_power_dbm(ack.sender, receiver, when=ack.start)
    if own:
        cause = "half_duplex"
    elif interferers and signal_dbm < max(
        item["received_power_dbm"] for item in interferers
    ) + sim.radio.capture_threshold_db:
        cause = "capture_collision"
    else:
        cause = "probabilistic_with_interference" if interferers else "probabilistic_no_interference"
    intent_earliest_complete = (
        first_delivery_at_s + sim.radio.toa_s_for_bytes(11)
        if first_delivery_at_s is not None else None
    )
    sole = (
        len(overlapping) == 1
        and overlapping[0].packet.kind == "FLOOD"
        and overlapping[0].packet.flow_id == ack.packet.flow_id
        and first_delivery_at_s is not None
        and overlapping[0].start > first_delivery_at_s
    )
    remaining_ack_hops = ack.packet.path_index
    return {
        "class": cause,
        "ack_tx_id": ack.tx_id,
        "receiver": receiver,
        "ack_start_at_s": ack.start,
        "ack_end_at_s": ack.end,
        "remaining_ack_hops": remaining_ack_hops,
        "earliest_source_ack_at_s": (
            ack.end + remaining_ack_hops * sim.radio.packet_toa_s(ack.packet)
        ),
        "signal_dbm": signal_dbm,
        "capture_threshold_db": sim.radio.capture_threshold_db,
        "receiver_transmissions": own,
        "interfering_transmissions": interferers,
        "intent_earliest_complete_at_s": intent_earliest_complete,
        "sole_same_flow_post_delivery_flood": sole,
        "strict_intent_timing_upper_bound": (
            sole and commitment_times[overlapping[0].tx_id]
            > intent_earliest_complete
        ),
    }


def analyze_failure_causes(
    sim: CauseSimulator, flow_rows: Sequence[dict[str, Any]],
    observation_cutoff_s: float,
) -> dict[str, Any]:
    """Attach receive-cause evidence only to actually failed ACK hops."""

    ack_hops = analyze_ack_hops(
        sim.tx_history, sim.ack_decodes, sim.ack_parent_tx_id, flow_rows,
        sim.first_deliveries, sim.destination_flood_decodes,
        observation_cutoff_s=observation_cutoff_s,
    )
    tx_by_id = {tx.tx_id: tx for tx in sim.tx_history}
    all_first_failures = []
    delivered_first_failures = []
    delivered_unacked = []
    broad_flows: set[int] = set()
    strict_flows: set[int] = set()
    flood_triggered_flows: set[int] = set()
    for flow in ack_hops["missing_flows"]:
        if flow["delivery_by_deadline"]:
            delivered_unacked.append(flow)
        for attempt in flow["ack_attempts"]:
            if (flow["delivery_by_deadline"]
                    and attempt["trigger_packet_kind"] == "FLOOD"):
                flood_triggered_flows.add(flow["flow_id"])
            attempt["failure_cause"] = None
            failed_hop = attempt["first_unphysical_reverse_hop"]
            if failed_hop is None:
                continue
            tx = tx_by_id[failed_hop["tx_id"]]
            cause = classify_failed_hop(
                sim, tx, failed_hop["edge"][1], sim.tx_history,
                sim.tx_commitment_times, flow["delivered_at_s"],
            )
            attempt["failure_cause"] = cause
            all_first_failures.append(cause)
            if not flow["delivery_by_deadline"]:
                continue
            delivered_first_failures.append(cause)
            if cause["earliest_source_ack_at_s"] > flow["deadline_at_s"]:
                continue
            if (cause["class"] in {"half_duplex", "capture_collision"}
                    and cause["sole_same_flow_post_delivery_flood"]):
                broad_flows.add(flow["flow_id"])
                if cause["strict_intent_timing_upper_bound"]:
                    strict_flows.add(flow["flow_id"])
    return {
        "tx_history": [
            {"tx_id": tx.tx_id, "sender": tx.sender,
             "kind": tx.packet.kind, "flow_id": tx.packet.flow_id,
             "repair_index": tx.packet.repair_index,
             "start_at_s": tx.start, "end_at_s": tx.end,
             "committed_at_s": sim.tx_commitment_times[tx.tx_id]}
            for tx in sim.tx_history
        ],
        "missing_flows": ack_hops["missing_flows"],
        "ack_hop_summary": ack_hops["summary"],
        "summary": {
            "delivered_unacked_flows": len(delivered_unacked),
            "flood_triggered_delivered_unacked_flows": len(flood_triggered_flows),
            "ack_attempts_for_delivered_unacked": sum(
                len(flow["ack_attempts"]) for flow in delivered_unacked
            ),
            "all_missing_first_physical_failures": len(all_first_failures),
            "all_missing_failure_classes": dict(sorted(Counter(
                cause["class"] for cause in all_first_failures
            ).items())),
            "delivered_unacked_first_physical_failures": len(delivered_first_failures),
            "delivered_unacked_failure_classes": dict(sorted(Counter(
                cause["class"] for cause in delivered_first_failures
            ).items())),
            "broad_overlap_unique_flows": len(broad_flows),
            "strict_eligible_unique_flows": len(strict_flows),
        },
    }


def _scheduled_sim(
    seed: int, case: SrCase, deadline_s: float,
    sim_class: type[RecordingSimulator],
) -> tuple[RecordingSimulator, list[tuple[Any, ...]], str]:
    config = make_args(case)
    config.sr_app_deadline_s = deadline_s
    sim = sim_class(
        generate_nodes(case.nodes, case.area_m, random.Random(seed), repeater_ratio=0.0),
        make_radio(config), build_protocol(PROTOCOL, config), seed=seed,
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
    return sim, scheduled, trace_hash


def _tx_trace_sha256(transmissions: Sequence[Transmission]) -> str:
    encoded = [
        {"tx_id": tx.tx_id, "sender": tx.sender, "start": tx.start,
         "end": tx.end, "packet": asdict(tx.packet)}
        for tx in transmissions
    ]
    return hashlib.sha256(
        json.dumps(encoded, sort_keys=True, separators=(",", ":")).encode("ascii")
    ).hexdigest()


def _assert_baseline_parity(
    sim: RecordingSimulator, baseline: Any, case: SrCase,
    seed: int, deadline_s: float, trace_hash: str,
) -> None:
    if trace_hash != baseline.row["scheduled_trace_sha256"]:
        raise AssertionError(f"fixed-F application trace differs at seed {seed}")
    for expected in baseline.flows:
        observed = sim.metrics.flows.get(expected["flow_id"])
        if (observed is None or observed.created_at != expected["enqueued_at"]
                or observed.delivered_at != expected["delivered_at"]
                or observed.acked_at != expected["acked_at"]
                or sim.protocol.flow_data_actions.get(expected["flow_id"])
                != expected["source_action"]
                or sim.first_data_delivery_kind.get(expected["flow_id"])
                != expected["first_data_delivery_kind"]):
            raise AssertionError(f"fixed-F flow {expected['flow_id']} differs at seed {seed}")
    if len(sim.metrics.flows) != len(baseline.flows):
        raise AssertionError(f"fixed-F flow count differs at seed {seed}")
    actions = [
        {"case": case.key, "protocol": PROTOCOL, "seed": seed, **event}
        for event in sim.protocol.action_events
    ]
    if actions != baseline.actions:
        raise AssertionError(f"fixed-F action trace differs at seed {seed}")
    windowed = summarize_windowed_transmissions(
        sim.tx_history, case.duration_s + deadline_s, case.payload_bytes,
    )
    if any(baseline.row[key] != value for key, value in windowed.items()):
        raise AssertionError(f"fixed-F TX accounting differs at seed {seed}")
    if (sim.metrics.tx_count != baseline.row["raw_tx_count"]
            or sim.metrics.collision_fail != baseline.row["collision_failures"]):
        raise AssertionError(f"fixed-F raw TX/collision counts differ at seed {seed}")


def run_diagnostic(
    seed: int, case: SrCase = SR_CASES["recurring_fading"],
    deadline_s: float = 30.0,
) -> dict[str, Any]:
    """Pair an unchanged fixed-F run with a fully audited passive replay."""

    baseline = run_one_sr(case, PROTOCOL, seed, deadline_s=deadline_s)
    plain, plain_schedule, plain_trace = _scheduled_sim(
        seed, case, deadline_s, RecordingSimulator,
    )
    observed, observed_schedule, observed_trace = _scheduled_sim(
        seed, case, deadline_s, CauseSimulator,
    )
    if plain_schedule != observed_schedule:
        raise AssertionError(f"fixed-F scheduled events differ at seed {seed}")
    cutoff = case.duration_s + deadline_s
    plain.run(cutoff)
    observed.run(cutoff)
    _assert_baseline_parity(plain, baseline, case, seed, deadline_s, plain_trace)
    _assert_baseline_parity(observed, baseline, case, seed, deadline_s, observed_trace)
    plain_tx_hash = _tx_trace_sha256(plain.tx_history)
    observed_tx_hash = _tx_trace_sha256(observed.tx_history)
    if plain_tx_hash != observed_tx_hash:
        raise AssertionError(f"instrumented TX trace differs at seed {seed}")
    if len(observed.tx_history) != len(observed.tx_commitment_times):
        raise AssertionError(f"missing TX commitment times at seed {seed}")
    analysis = analyze_failure_causes(observed, baseline.flows, cutoff)
    return {
        "seed": seed,
        "case": asdict(case),
        "protocol": PROTOCOL,
        "parity": {
            "scheduled_trace_sha256": observed_trace,
            "baseline_trace_sha256": baseline.row["scheduled_trace_sha256"],
            "plain_tx_sha256": plain_tx_hash,
            "observed_tx_sha256": observed_tx_hash,
            "flows_exact": True,
            "actions_exact": True,
            "baseline_case_sha256": baseline.row["case_config_sha256"],
        },
        **analysis,
    }


def _source_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in SOURCE_FILES
    }


def run_report(
    seeds: Sequence[int], case: SrCase = SR_CASES["recurring_fading"],
    mode: str = "explore", deadline_s: float = 30.0,
) -> dict[str, Any]:
    """Build a provenance-checked report; only CLI selects reserved seeds."""

    if mode == "smoke" and tuple(seeds) != SMOKE_SEEDS:
        raise ValueError("smoke requires exactly seed 37000")
    if mode == "explore" and tuple(seeds) != EXPLORATORY_SEEDS:
        raise ValueError("exploration requires exactly seeds 37001--37003")
    if mode not in {"smoke", "explore", "synthetic"}:
        raise ValueError(f"unknown diagnostic report mode: {mode}")
    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("diagnostic seeds must be nonempty and unique")
    frozen_hashes = _source_hashes()
    runs = []
    for seed in seeds:
        runs.append(run_diagnostic(seed, case, deadline_s=deadline_s))
        if _source_hashes() != frozen_hashes:
            raise RuntimeError("diagnostic source changed during replay")
    totals = Counter()
    all_class_counts = Counter()
    delivered_class_counts = Counter()
    for run in runs:
        totals.update({
            key: value for key, value in run["summary"].items()
            if key not in {"all_missing_failure_classes", "delivered_unacked_failure_classes"}
        })
        all_class_counts.update(run["summary"]["all_missing_failure_classes"])
        delivered_class_counts.update(run["summary"]["delivered_unacked_failure_classes"])
    denominator = totals["delivered_unacked_flows"]
    strict = totals["strict_eligible_unique_flows"]
    gate = (
        strict >= 4 and denominator > 0 and strict / denominator >= 0.10
        if mode == "explore" else None
    )
    summary: dict[str, Any] = dict(sorted(totals.items()))
    summary["all_missing_failure_classes"] = dict(sorted(all_class_counts.items()))
    summary["delivered_unacked_failure_classes"] = dict(sorted(delivered_class_counts.items()))
    summary["strict_eligible_fraction_of_delivered_unacked"] = (
        strict / denominator if denominator else None
    )
    summary["quiet_window_exposure_gate_passed"] = gate
    return {
        "analysis_type": "observed unchanged fixed-F simulation only",
        "counterfactual_estimates": None,
        "mode": mode,
        "protocol": PROTOCOL,
        "case": asdict(case),
        "case_sha256": hashlib.sha256(
            json.dumps(asdict(case), sort_keys=True, separators=(",", ":")).encode("ascii")
        ).hexdigest(),
        "seeds": list(seeds),
        "application_deadline_s": deadline_s,
        "drain_until_s": case.duration_s + deadline_s,
        "source_sha256": frozen_hashes,
        "summary": summary,
        "runs": runs,
    }


def write_report(report: Mapping[str, Any], output_prefix: Path) -> dict[str, Path]:
    """Write a report and hash manifest without replacing existing artifacts."""

    prefix = Path(output_prefix)
    report_path = prefix.with_name(prefix.name + ".report.json")
    manifest_path = prefix.with_name(prefix.name + ".manifest.json")
    if prefix.exists() or report_path.exists() or manifest_path.exists():
        raise FileExistsError(f"diagnostic output prefix already exists: {prefix}")
    payload = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8")
    manifest = {
        "analysis_type": report.get("analysis_type"),
        "mode": report.get("mode"),
        "seeds": report.get("seeds"),
        "case_sha256": report.get("case_sha256"),
        "source_sha256": report["source_sha256"],
        "report_file": report_path.name,
        "report_sha256": hashlib.sha256(payload).hexdigest(),
    }
    manifest_payload = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("xb") as handle:
        handle.write(payload)
    with manifest_path.open("xb") as handle:
        handle.write(manifest_payload)
    return {"report": report_path, "manifest": manifest_path}


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("smoke", "explore"))
    parser.add_argument("--output-prefix", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    prefix = args.output_prefix
    if (prefix.exists() or prefix.with_name(prefix.name + ".report.json").exists()
            or prefix.with_name(prefix.name + ".manifest.json").exists()):
        raise FileExistsError(f"diagnostic output prefix already exists: {prefix}")
    report = run_report(seeds_for_mode(args.mode), mode=args.mode)
    if _source_hashes() != report["source_sha256"]:
        raise RuntimeError("diagnostic source changed before artifact writing")
    paths = write_report(report, prefix)
    print(json.dumps({
        "report": str(paths["report"]),
        "manifest": str(paths["manifest"]),
        "summary": report["summary"],
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
