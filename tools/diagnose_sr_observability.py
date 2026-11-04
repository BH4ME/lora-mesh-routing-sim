#!/usr/bin/env python3
"""Passive initial-R hop observability diagnostic; no protocol behavior changes."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import Packet, RxInfo, Transmission, build_protocol, generate_nodes
from tools.run_fair_multihop_probe import (
    connected_multihop_pairs, make_args, make_radio,
)
from tools.run_sr_experiment import (
    DHR_PROTOCOLS, SR_CASES, RecordingSimulator, schedule_sr_traffic,
)


DIAGNOSTIC_SEEDS = (11001, 11002, 11003)


class ObservabilitySimulator(RecordingSimulator):
    """Tap successful PHY decodes after the simulator's usual receive attempt."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.successful_decodes: Dict[int, Dict[int, float]] = {}

    def try_receive(self, tx: Transmission, receiver: int) -> RxInfo | None:
        decoded = super().try_receive(tx, receiver)
        packet = tx.packet
        action = getattr(self.protocol, "flow_data_actions", {}).get(packet.flow_id)
        if (decoded is not None and action in {"F", "R"}
                and (packet.kind == "ACK" or packet.kind == "DATA"
                     and action == "R" and packet.repair_index is None)):
            self.successful_decodes.setdefault(tx.tx_id, {})[receiver] = (
                self.nodes[receiver].tx_available_at
            )
        return decoded


def oracle_detours(
    sim: ObservabilitySimulator, tx: Transmission, deadline_at: float,
    not_before_s: float,
) -> list[Dict[str, Any]]:
    """Optimistic one-relay insertion bound, using hidden channel knowledge."""

    packet = tx.packet
    index = packet.path_index
    next_hop = packet.path[index + 1]
    eligible = []
    for candidate, available_at in sim.successful_decodes.get(tx.tx_id, {}).items():
        if (candidate in packet.path or not sim.nodes[candidate].can_relay):
            continue
        path = packet.path[:index + 1] + (candidate,) + packet.path[index + 1:]
        if len(set(path)) != len(path) or len(path) - 1 > sim.max_hops:
            continue
        start = max(tx.end, available_at, not_before_s)
        snr = sim.snr_from_power(sim.rx_power_dbm(candidate, next_hop, when=start))
        prr = sim.prr_from_snr(snr)
        if prr < 0.90:
            continue
        detour_data = replace(packet, path=path, path_index=index + 1)
        return_ack = Packet(
            kind="ACK", flow_id=packet.flow_id, origin=packet.final_dst,
            final_dst=packet.origin, ttl=sim.max_hops,
            created_at=start, protocol=packet.protocol,
            request_id=packet.request_id, path=path,
            path_index=len(path) - 2, app_payload=False,
            min_forward_margin_q=packet.min_forward_margin_q,
            min_forward_margin_hop=packet.min_forward_margin_hop,
        )
        data_hops_remaining = len(path) - index - 2
        optimistic_ack_at = (
            start
            + data_hops_remaining * sim.radio.packet_toa_s(detour_data)
            + (len(path) - 1) * sim.radio.packet_toa_s(return_ack)
        )
        if optimistic_ack_at <= deadline_at:
            eligible.append({
                "candidate": candidate,
                "detour_path": path,
                "prr_to_intended_next_hop": prr,
                "queue_available_at_s": available_at,
                "optimistic_ack_at_s": optimistic_ack_at,
            })
    return sorted(eligible, key=lambda item: item["candidate"])


def analyze_observability(
    sim: ObservabilitySimulator, cutoff_s: float,
) -> Dict[str, Any]:
    """Compare passive predecessor evidence with actual initial-R hop decodes."""

    hops = []
    transmissions = sim.tx_history
    for tx in transmissions:
        packet = tx.packet
        index = packet.path_index
        if (packet.kind != "DATA" or packet.repair_index is not None
                or sim.protocol.flow_data_actions.get(packet.flow_id) != "R"
                or len(packet.path) < 2 or not 0 <= index < len(packet.path) - 1
                or packet.path[index] != tx.sender
                or packet.path[0] != packet.origin
                or packet.path[-1] != packet.final_dst):
            continue

        next_hop = packet.path[index + 1]
        flow = sim.metrics.flows.get(packet.flow_id)
        deadline_at = (flow.created_at if flow is not None else packet.created_at)
        deadline_at += sim.protocol.app_deadline_s
        guard_end = min(tx.start + sim.protocol.ack_guard_s, deadline_at)
        evidence_kind = None
        evidence_tx_id = None
        for later in transmissions:
            if (later.start < tx.end - 1e-9 or later.end > min(guard_end, cutoff_s)
                    or later.sender != next_hop
                    or tx.sender not in sim.successful_decodes.get(later.tx_id, {})):
                continue
            observed = later.packet
            if (observed.flow_id != packet.flow_id
                    or observed.request_id != packet.request_id
                    or observed.path != packet.path
                    or observed.repair_index is not None):
                continue
            if (index + 1 < len(packet.path) - 1
                    and observed.kind == "DATA"
                    and observed.path_index == index + 1):
                evidence_kind = "forward"
            elif (index + 1 == len(packet.path) - 1
                  and observed.kind == "ACK"
                  and observed.path_index == index):
                evidence_kind = "ack"
            if evidence_kind is not None:
                evidence_tx_id = later.tx_id
                break

        truth = (next_hop in sim.successful_decodes.get(tx.tx_id, {})
                 if tx.end <= cutoff_s else None)
        observed_by_guard = evidence_kind is not None
        evaluable = truth is not None and (observed_by_guard or guard_end <= cutoff_s)
        detours = (
            oracle_detours(sim, tx, deadline_at, tx.end)
            if truth is False else []
        )
        guard_detours = (
            oracle_detours(sim, tx, deadline_at, guard_end)
            if truth is False else []
        )
        hops.append({
            "flow_id": packet.flow_id,
            "tx_id": tx.tx_id,
            "sender": tx.sender,
            "next_hop": next_hop,
            "path_index": index,
            "next_hop_decoded": truth,
            "passive_observed_by_guard": observed_by_guard if evaluable else None,
            "evidence_kind": evidence_kind,
            "evidence_tx_id": evidence_tx_id,
            "guard_end_s": guard_end,
            "censored": not evaluable,
            "oracle_eligible_candidates": [item["candidate"] for item in detours],
            "oracle_candidate_details": detours,
            "oracle_guard_eligible_candidates": [
                item["candidate"] for item in guard_detours
            ],
            "oracle_guard_candidate_details": guard_detours,
        })

    evaluated = [hop for hop in hops if not hop["censored"]]
    true_positive = sum(hop["next_hop_decoded"] and hop["passive_observed_by_guard"]
                        for hop in evaluated)
    false_failure = sum(hop["next_hop_decoded"] and not hop["passive_observed_by_guard"]
                        for hop in evaluated)
    false_success = sum(not hop["next_hop_decoded"] and hop["passive_observed_by_guard"]
                        for hop in evaluated)
    true_negative = sum(not hop["next_hop_decoded"] and not hop["passive_observed_by_guard"]
                        for hop in evaluated)
    summary = {
        "attempted_hops": len(hops),
        "evaluated_hops": len(evaluated),
        "censored_hops": len(hops) - len(evaluated),
        "true_positive": true_positive,
        "false_failure": false_failure,
        "false_success": false_success,
        "true_negative": true_negative,
        "false_failure_denominator": true_positive + false_failure,
        "false_success_denominator": true_negative + false_success,
        "failed_hops_with_oracle_detour": sum(
            bool(hop["oracle_eligible_candidates"])
            for hop in hops if hop["next_hop_decoded"] is False
        ),
        "oracle_failed_hop_denominator": sum(
            hop["next_hop_decoded"] is False for hop in hops
        ),
        "failed_hops_with_guard_detour": sum(
            bool(hop["oracle_guard_eligible_candidates"])
            for hop in hops if hop["next_hop_decoded"] is False
        ),
        "oracle_interpretation": (
            "oracle_eligible_candidates assumes zero detection delay after the failed "
            "receive; oracle_guard_eligible_candidates waits until the passive "
            "guard end. Both are optimistic upper bounds for one off-path relay "
            "inserted before the intended next hop, not realized delivery or "
            "deployable knowledge"
        ),
    }
    return {"hops": hops, "summary": summary}


def summarize_ack_hops(
    sim: ObservabilitySimulator, cutoff_s: float,
) -> Dict[str, Any]:
    """Report actual F/R ACK transmissions and their intended-hop PHY outcome."""

    by_action = {
        action: {"transmitted": 0, "decoded": 0, "failed": 0, "censored": 0}
        for action in ("F", "R")
    }
    by_phase = {
        phase: {"transmitted": 0, "decoded": 0, "failed": 0, "censored": 0}
        for phase in ("initial", "r_rescue", "f_rescue", "other")
    }
    hops = []
    first_failed = {}
    for tx in sorted(sim.tx_history, key=lambda item: (item.start, item.tx_id)):
        packet = tx.packet
        action = sim.protocol.flow_data_actions.get(packet.flow_id)
        index = packet.path_index
        if (packet.kind != "ACK" or action not in by_action
                or not 0 <= index < len(packet.path) - 1
                or packet.path[index + 1] != tx.sender
                or packet.path[0] != packet.final_dst
                or packet.path[-1] != packet.origin):
            continue
        receiver = packet.path[index]
        decoded = (receiver in sim.successful_decodes.get(tx.tx_id, {})
                   if tx.end <= cutoff_s else None)
        phase = {None: "initial", 1: "r_rescue", 2: "f_rescue"}.get(
            packet.repair_index, "other",
        )
        row = {
            "flow_id": packet.flow_id,
            "tx_id": tx.tx_id,
            "initial_action": action,
            "repair_index": packet.repair_index,
            "ack_phase": phase,
            "sender": tx.sender,
            "intended_receiver": receiver,
            "path_index": index,
            "start_s": tx.start,
            "intended_decoded": decoded,
            "source_hop": index == 0,
        }
        hops.append(row)
        counts = by_action[action]
        counts["transmitted"] += 1
        counts["censored" if decoded is None else
               "decoded" if decoded else "failed"] += 1
        phase_counts = by_phase[phase]
        phase_counts["transmitted"] += 1
        phase_counts["censored" if decoded is None else
                     "decoded" if decoded else "failed"] += 1
        key = (packet.flow_id, packet.repair_index)
        if decoded is False and key not in first_failed:
            first_failed[key] = row
    return {
        "hops": hops,
        "by_initial_action": by_action,
        "by_ack_phase": by_phase,
        "first_failed_hops": list(first_failed.values()),
        "interpretation": (
            "first_failed_hops is the earliest observed failed PHY ACK transmission "
            "per flow and repair marker; duplicate ACK attempts can later succeed"
        ),
    }


def run_diagnostic(seed: int, protocol_name: str = "meshecho-dhr") -> Dict[str, Any]:
    """Replay the frozen recurring-fading construction on diagnostic seeds only."""

    if seed not in DIAGNOSTIC_SEEDS:
        raise ValueError(f"only diagnostic seeds {DIAGNOSTIC_SEEDS} are allowed")
    if protocol_name not in DHR_PROTOCOLS:
        raise ValueError(f"only DHR protocols {DHR_PROTOCOLS} are allowed")
    case = SR_CASES["recurring_fading"]
    deadline_s = 30.0
    config = make_args(case)
    config.sr_app_deadline_s = deadline_s
    nodes = generate_nodes(
        case.nodes, case.area_m, random.Random(seed), repeater_ratio=0.0,
    )
    protocol = build_protocol(protocol_name, config)
    sim = ObservabilitySimulator(
        nodes, make_radio(config), protocol, seed=seed,
        max_hops=case.max_hops, independent_random_streams=True,
        matched_rreq_timing=case.matched_rreq_timing,
    )
    pairs, _ = connected_multihop_pairs(
        sim, random.Random(seed + 20_000), case.edge_prr_threshold,
        case.min_graph_hops, case.max_graph_hops, case.pair_count,
    )
    if len(pairs) != case.pair_count:
        raise ValueError(f"seed {seed}: selected {len(pairs)} of {case.pair_count} pairs")
    schedule_sr_traffic(sim, case, pairs, random.Random(seed + 10_000))
    scheduled = sorted(
        (when, *data) for when, _, kind, data in sim.events
        if kind == "app_send"
    )
    trace_hash = hashlib.sha256(
        json.dumps(scheduled, separators=(",", ":")).encode("ascii")
    ).hexdigest()
    cutoff_s = case.duration_s + deadline_s
    metrics = sim.run(cutoff_s)
    flow_records = list(metrics.flows.values())
    return {
        "case": case.key,
        "protocol": protocol_name,
        "seed": seed,
        "deadline_s": deadline_s,
        "cutoff_s": cutoff_s,
        "scheduled_trace_sha256": trace_hash,
        "scheduled_flows": len(scheduled),
        "registered_flows": len(flow_records),
        "ack_by_deadline": sum(
            flow.acked_at is not None
            and flow.acked_at <= flow.created_at + deadline_s
            for flow in flow_records
        ),
        "delivery_by_deadline": sum(
            flow.delivered_at is not None
            and flow.delivered_at <= flow.created_at + deadline_s
            for flow in flow_records
        ),
        "observability": analyze_observability(sim, cutoff_s),
        "ack_hops": summarize_ack_hops(sim, cutoff_s),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, choices=DIAGNOSTIC_SEEDS,
                        default=DIAGNOSTIC_SEEDS)
    parser.add_argument("--protocol", choices=DHR_PROTOCOLS,
                        default="meshecho-dhr")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output is not None and args.output.exists():
        parser.error(f"output already exists: {args.output}")
    sources = {
        "diagnostic_script": Path(__file__).resolve(),
        "simulator": ROOT / "lora_mesh_sim.py",
        "runner": ROOT / "tools" / "run_sr_experiment.py",
    }
    result = {
        "source_sha256": {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in sources.items()
        },
        "runs": [run_diagnostic(seed, args.protocol) for seed in args.seeds],
    }
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        with args.output.open("x", encoding="utf-8") as output:
            output.write(encoded)


if __name__ == "__main__":
    main()
