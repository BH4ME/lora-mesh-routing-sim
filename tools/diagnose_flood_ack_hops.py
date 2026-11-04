#!/usr/bin/env python3
"""Passive reverse-ACK hop tracing for the fixed-F DHR control."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
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
    SR_CASES, RecordingSimulator, SrCase, run_one_sr, schedule_sr_traffic,
)


PROTOCOL = "meshecho-dhr-flood"
EXPLORATORY_SEEDS = (14001, 14002, 14003)


class AckHopSimulator(RecordingSimulator):
    """Record already-computed ACK decodes without changing protocol delivery."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.ack_decodes: dict[int, set[int]] = {}
        self.ack_parent_tx_id: dict[int, int] = {}
        self.first_deliveries: dict[int, dict[str, Any]] = {}
        self.destination_flood_decodes: set[int] = set()
        self._pending_ack_parents: dict[int, int] = {}
        self._handling_tx_id: int | None = None

    def transmit_later(self, sender: int, packet: Any, delay_s: float,
                       pending: Any = None) -> Any:
        handle = super().transmit_later(sender, packet, delay_s, pending)
        if packet.kind == "ACK" and self._handling_tx_id is not None:
            self._pending_ack_parents[id(handle)] = self._handling_tx_id
        return handle

    def begin_transmission(self, sender: int, packet: Any, pending: Any) -> None:
        previous_count = self.metrics.tx_count
        super().begin_transmission(sender, packet, pending)
        parent = self._pending_ack_parents.pop(id(pending), None)
        if self.metrics.tx_count > previous_count and packet.kind == "ACK" and parent is not None:
            self.ack_parent_tx_id[self.tx_history[-1].tx_id] = parent

    def handle_tx_end(self, tx: Transmission) -> None:
        self._handling_tx_id = tx.tx_id
        try:
            super().handle_tx_end(tx)
        finally:
            self._handling_tx_id = None

    def try_receive(self, tx: Transmission, receiver: int) -> RxInfo | None:
        decoded = super().try_receive(tx, receiver)
        if decoded is not None and tx.packet.kind == "ACK":
            self.ack_decodes.setdefault(tx.tx_id, set()).add(receiver)
        if (decoded is not None and tx.packet.kind == "FLOOD"
                and receiver == tx.packet.final_dst):
            self.destination_flood_decodes.add(tx.packet.flow_id)
        return decoded

    def mark_delivered(self, flow_id: int, receiver: int, packet: Any) -> None:
        flow = self.metrics.flows.get(flow_id)
        if (flow is not None and receiver == flow.dst
                and flow.delivered_at is None):
            self.first_deliveries[flow_id] = {
                "kind": packet.kind,
                "repair_index": packet.repair_index,
                "received_at_s": self.now,
            }
        super().mark_delivered(flow_id, receiver, packet)


def analyze_ack_hops(
    transmissions: Sequence[Transmission], ack_decodes: dict[int, set[int]],
    ack_parent_tx_id: dict[int, int], flow_rows: Sequence[dict[str, Any]],
    first_deliveries: dict[int, dict[str, Any]] | None = None,
    destination_flood_decodes: set[int] | None = None,
    observation_cutoff_s: float | None = None,
) -> Dict[str, Any]:
    """Describe actual ACK transmissions and physical reverse-hop decodes."""

    first_deliveries = first_deliveries or {}
    destination_flood_decodes = destination_flood_decodes or set()
    all_txs = {tx.tx_id: tx for tx in transmissions}
    ack_txs = {tx_id: tx for tx_id, tx in all_txs.items() if tx.packet.kind == "ACK"}
    source_flood_flows = {
        tx.packet.flow_id for tx in transmissions
        if tx.packet.kind == "FLOOD" and tx.sender == tx.packet.origin
    }
    children: dict[int, list[Transmission]] = defaultdict(list)
    for tx_id, parent_id in ack_parent_tx_id.items():
        if tx_id in ack_txs:
            children[parent_id].append(ack_txs[tx_id])
    for descendants in children.values():
        descendants.sort(key=lambda tx: (tx.start, tx.tx_id))
    roots_by_flow: dict[int, list[Transmission]] = defaultdict(list)
    for tx in ack_txs.values():
        if tx.sender == tx.packet.origin:
            roots_by_flow[tx.packet.flow_id].append(tx)
    for roots in roots_by_flow.values():
        roots.sort(key=lambda tx: (tx.start, tx.tx_id))

    missing_flows = []
    for flow in flow_rows:
        if flow["ack_by_deadline"]:
            continue
        flow_id, src, dst = flow["flow_id"], flow["src"], flow["dst"]
        deadline = flow["deadline_at"]
        attempts = []
        for root in roots_by_flow.get(flow_id, []):
            packet = root.packet
            path = packet.path
            trigger_tx = all_txs.get(ack_parent_tx_id.get(root.tx_id))
            attempt: dict[str, Any] = {
                "ack_tx_id": root.tx_id,
                "repair_index": packet.repair_index,
                "trigger_tx_id": trigger_tx.tx_id if trigger_tx else None,
                "trigger_packet_kind": trigger_tx.packet.kind if trigger_tx else None,
                "trigger_packet_repair_index": (
                    trigger_tx.packet.repair_index if trigger_tx else None
                ),
                "ack_path": list(path),
                "ack_path_hops": len(path) - 1,
                "destination_ack_started_at_s": root.start,
                "emitted_after_deadline": root.start > deadline,
                "reverse_hops": [],
                "first_unphysical_reverse_hop": None,
                "source_physically_decoded": False,
                "source_decode_at_s": None,
                "source_decode_after_deadline": None,
            }
            if (len(path) < 2 or path[0] != src or path[-1] != dst
                    or root.sender != dst or packet.path_index != len(path) - 2):
                attempt["termination"] = "invalid_ack_path"
                attempts.append(attempt)
                continue
            current = root
            visited: set[int] = set()
            while current.tx_id not in visited:
                visited.add(current.tx_id)
                index = current.packet.path_index
                intended = path[index]
                censored = (observation_cutoff_s is not None
                            and current.end > observation_cutoff_s)
                physically_decoded = intended in ack_decodes.get(current.tx_id, set())
                hop = {
                    "tx_id": current.tx_id,
                    "edge": [current.sender, intended],
                    "received_at_s": current.end,
                    "physically_decoded": None if censored else physically_decoded,
                    "observation_censored": censored,
                    "after_deadline": current.end > deadline,
                }
                attempt["reverse_hops"].append(hop)
                if censored:
                    attempt["termination"] = "censored_at_observation_cutoff"
                    break
                if not physically_decoded:
                    attempt["first_unphysical_reverse_hop"] = hop
                    attempt["termination"] = "physical_decode_failure"
                    break
                if intended == src:
                    attempt["source_physically_decoded"] = True
                    attempt["source_decode_at_s"] = current.end
                    attempt["source_decode_after_deadline"] = current.end > deadline
                    attempt["termination"] = "source_physically_decoded"
                    break
                next_hops = [
                    child for child in children.get(current.tx_id, [])
                    if child.sender == intended and child.packet.flow_id == flow_id
                    and child.packet.path == path
                    and child.packet.path_index == index - 1
                    and child.packet.repair_index == packet.repair_index
                ]
                if len(next_hops) != 1:
                    attempt["termination"] = (
                        "decoded_no_matching_forward" if not next_hops
                        else "ambiguous_matching_forwards"
                    )
                    break
                current = next_hops[0]
            attempts.append(attempt)
        row = {
            "flow_id": flow_id, "src": src, "dst": dst,
            "source_action": flow.get("source_action"),
            "enqueued_at_s": flow["enqueued_at"],
            "deadline_at_s": deadline,
            "delivered_at_s": flow.get("delivered_at"),
            "delivery_by_deadline": flow["delivery_by_deadline"],
            "first_delivery_kind": first_deliveries.get(flow_id, {}).get("kind"),
            "first_delivery_repair_index": first_deliveries.get(flow_id, {}).get("repair_index"),
            "destination_flood_physically_decoded": (
                flow_id in destination_flood_decodes
                or first_deliveries.get(flow_id, {}).get("kind") == "FLOOD"
            ),
            "source_flood_started": flow_id in source_flood_flows,
            "acked_at_s": flow.get("acked_at"),
            "source_ack_accepted": flow.get("acked_at") is not None,
            "destination_emitted_ack": bool(attempts),
            "source_physically_decoded": any(
                item["source_physically_decoded"] for item in attempts
            ),
            "source_physically_decoded_by_deadline": any(
                item["source_physically_decoded"]
                and not item["source_decode_after_deadline"] for item in attempts
            ),
            "ack_attempts": attempts,
        }
        missing_flows.append(row)
    termination_counts = Counter(
        attempt["termination"] for flow in missing_flows
        for attempt in flow["ack_attempts"]
    )
    ack_path_hops = Counter(
        attempt["ack_path_hops"] for flow in missing_flows
        for attempt in flow["ack_attempts"]
    )
    return {
        "missing_flows": missing_flows,
        "summary": {
            "missing_source_acks_by_deadline": len(missing_flows),
            "delivered_unacked_by_deadline": sum(
                flow["delivery_by_deadline"] for flow in missing_flows
            ),
            "no_destination_ack_emission": sum(
                not flow["destination_emitted_ack"] for flow in missing_flows
            ),
            "destination_ack_attempts": sum(
                len(flow["ack_attempts"]) for flow in missing_flows
            ),
            "missing_with_source_flood_started": sum(
                flow["source_flood_started"] for flow in missing_flows
            ),
            "missing_with_destination_flood_decode": sum(
                flow["destination_flood_physically_decoded"] for flow in missing_flows
            ),
            "delivered_unacked_with_destination_flood_decode": sum(
                flow["delivery_by_deadline"] and flow["destination_flood_physically_decoded"]
                for flow in missing_flows
            ),
            "first_delivered_by_flood": sum(
                flow["first_delivery_kind"] == "FLOOD" for flow in missing_flows
            ),
            "flood_triggered_ack_attempts": sum(
                attempt["trigger_packet_kind"] == "FLOOD"
                for flow in missing_flows for attempt in flow["ack_attempts"]
            ),
            "source_physically_decoded_after_deadline": sum(
                any(attempt["source_decode_after_deadline"] is True
                    for attempt in flow["ack_attempts"])
                for flow in missing_flows
            ),
            "ack_attempt_terminations": dict(sorted(termination_counts.items())),
            "ack_path_hops": dict(sorted(ack_path_hops.items())),
        },
        "interpretation": (
            "All ACK transmissions and intended-hop decodes are observed in the "
            "unchanged simulator. A physical decode is not necessarily a protocol-"
            "accepted source ACK. Missing counterfactual transmissions or alternate "
            "routes are not inferred from these records."
        ),
    }


def run_diagnostic(
    seed: int, case: SrCase = SR_CASES["recurring_fading"],
    deadline_s: float = 30.0,
) -> Dict[str, Any]:
    """Replay one fixed-F seed, refusing any change in the baseline outcomes."""

    baseline = run_one_sr(case, PROTOCOL, seed, deadline_s=deadline_s)
    config = make_args(case)
    config.sr_app_deadline_s = deadline_s
    nodes = generate_nodes(case.nodes, case.area_m, random.Random(seed), repeater_ratio=0.0)
    sim = AckHopSimulator(
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
    flows = [sim.metrics.flows.get(flow_id) for _, _, dst, flow_id in scheduled if dst >= 0]
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
    if replay != baseline_parity:
        raise AssertionError(f"fixed-F replay differs from baseline at seed {seed}")
    outcome_by_flow = {item["flow_id"]: item for item in baseline.flows}
    for flow in flows:
        if flow is None:
            continue
        expected = outcome_by_flow[flow.flow_id]
        if (flow.delivered_at != expected["delivered_at"]
                or flow.acked_at != expected["acked_at"]
                or sim.protocol.flow_data_actions.get(flow.flow_id) != expected["source_action"]
                or (flow.delivered_at is not None and flow.delivered_at <= flow.created_at + deadline_s)
                != expected["delivery_by_deadline"]
                or (flow.acked_at is not None and flow.acked_at <= flow.created_at + deadline_s)
                != expected["ack_by_deadline"]):
            raise AssertionError(f"fixed-F flow {flow.flow_id} differs at seed {seed}")
    analysis = analyze_ack_hops(
        sim.tx_history, sim.ack_decodes, sim.ack_parent_tx_id, baseline.flows,
        sim.first_deliveries, sim.destination_flood_decodes,
        observation_cutoff_s=case.duration_s + deadline_s,
    )
    return {
        "seed": seed, "case": asdict(case), "protocol": PROTOCOL,
        "parity": {"baseline": baseline_parity, "replay": replay},
        **analysis,
    }


def run_exploration(
    seeds: Sequence[int] = EXPLORATORY_SEEDS,
    case: SrCase = SR_CASES["recurring_fading"],
    deadline_s: float = 30.0,
) -> Dict[str, Any]:
    """Collect exact baseline-matched observations on new exploratory seeds."""

    source_files = (
        ROOT / "lora_mesh_sim.py",
        ROOT / "tools" / "run_fair_multihop_probe.py",
        ROOT / "tools" / "run_sr_experiment.py",
        Path(__file__),
    )

    def source_hashes() -> dict[str, str]:
        return {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in source_files
        }

    before = source_hashes()
    runs = [run_diagnostic(seed, case, deadline_s) for seed in seeds]
    if source_hashes() != before:
        raise RuntimeError("simulation source changed during exploratory run")
    attempts = [
        attempt for run in runs for flow in run["missing_flows"]
        for attempt in flow["ack_attempts"]
    ]
    first_failures = [
        attempt for attempt in attempts
        if attempt["first_unphysical_reverse_hop"] is not None
    ]
    path_hops = Counter(attempt["ack_path_hops"] for attempt in attempts)
    fail_positions = Counter(
        len(attempt["reverse_hops"]) for attempt in first_failures
    )
    totals = {
        "scheduled_unicast_flows": sum(
            run["parity"]["baseline"]["scheduled_unicast_flows"] for run in runs
        ),
        "delivery_by_deadline": sum(
            run["parity"]["baseline"]["delivery_by_deadline"] for run in runs
        ),
        "ack_by_deadline": sum(
            run["parity"]["baseline"]["ack_by_deadline"] for run in runs
        ),
        "missing_source_acks_by_deadline": sum(
            run["summary"]["missing_source_acks_by_deadline"] for run in runs
        ),
        "delivered_unacked_by_deadline": sum(
            run["summary"]["delivered_unacked_by_deadline"] for run in runs
        ),
        "missing_without_destination_ack_emission": sum(
            run["summary"]["no_destination_ack_emission"] for run in runs
        ),
        "destination_ack_attempts_for_missing_flows": len(attempts),
        "missing_with_source_flood_started": sum(
            run["summary"]["missing_with_source_flood_started"] for run in runs
        ),
        "missing_with_destination_flood_decode": sum(
            run["summary"]["missing_with_destination_flood_decode"] for run in runs
        ),
        "missing_first_delivered_by_flood": sum(
            run["summary"]["first_delivered_by_flood"] for run in runs
        ),
        "flood_triggered_ack_attempts": sum(
            run["summary"]["flood_triggered_ack_attempts"] for run in runs
        ),
        "source_physically_decoded_by_deadline_but_unaccepted": sum(
            flow["source_physically_decoded_by_deadline"]
            for run in runs for flow in run["missing_flows"]
        ),
        "source_physically_decoded_after_deadline": sum(
            run["summary"]["source_physically_decoded_after_deadline"] for run in runs
        ),
        "ack_emissions_after_deadline": sum(
            attempt["emitted_after_deadline"] for attempt in attempts
        ),
        "first_physical_failures_after_deadline": sum(
            attempt["first_unphysical_reverse_hop"]["after_deadline"]
            for attempt in first_failures
        ),
        "first_physical_reverse_hop_failures": len(first_failures),
        "first_failure_at_final_hop_to_source": sum(
            attempt["first_unphysical_reverse_hop"]["edge"][1]
            == flow["src"]
            for run in runs for flow in run["missing_flows"]
            for attempt in flow["ack_attempts"]
            if attempt["first_unphysical_reverse_hop"] is not None
        ),
        "censored_ack_attempts": sum(
            attempt["termination"] == "censored_at_observation_cutoff"
            for attempt in attempts
        ),
        "ack_path_hops": dict(sorted(path_hops.items())),
        "first_failure_hop_from_destination": dict(sorted(fail_positions.items())),
        "ack_attempt_terminations": dict(sorted(Counter(
            attempt["termination"] for attempt in attempts
        ).items())),
    }
    if totals["scheduled_unicast_flows"] - totals["ack_by_deadline"] != totals["missing_source_acks_by_deadline"]:
        raise AssertionError("missing-flow count does not reconcile with baseline")
    return {
        "analysis_type": "observed unchanged fixed-F simulation only",
        "counterfactual_estimates": None,
        "protocol": PROTOCOL,
        "case": asdict(case),
        "seeds": list(seeds),
        "application_deadline_s": deadline_s,
        "drain_until_s": case.duration_s + deadline_s,
        "source_sha256": before,
        "summary": totals,
        "runs": runs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "results" / "meshecho_flood_ack_hops_seed14001_14003_20261004.json",
    )
    args = parser.parse_args()
    report = run_exploration()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "summary": report["summary"]}, indent=2))


if __name__ == "__main__":
    main()
