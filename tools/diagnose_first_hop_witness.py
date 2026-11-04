#!/usr/bin/env python3
"""Read-only first-hop witness diagnostic on fresh exploratory DHR seeds."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import RxInfo, Transmission, build_protocol, generate_nodes
from tools.diagnose_sr_observability import (
    ObservabilitySimulator, analyze_observability, oracle_detours,
)
from tools.run_fair_multihop_probe import (
    connected_multihop_pairs, make_args, make_radio,
)
from tools.run_sr_experiment import SR_CASES, schedule_sr_traffic


EXPLORATORY_SEEDS = (12001, 12002, 12003)


class WitnessSimulator(ObservabilitySimulator):
    """Also retain FLOOD and discovery-route ACK decodes for local history."""

    def try_receive(self, tx: Transmission, receiver: int) -> RxInfo | None:
        decoded = super().try_receive(tx, receiver)
        if decoded is not None and tx.packet.kind in {"FLOOD", "ACK"}:
            self.successful_decodes.setdefault(tx.tx_id, {})[receiver] = (
                self.nodes[receiver].tx_available_at
            )
        return decoded


def analyze_first_hop_witness(
    sim: WitnessSimulator, cutoff_s: float,
) -> Dict[str, Any]:
    """Reconstruct one ACK-carriable candidate from first-hop local history."""

    hops = []
    for tx in sim.tx_history:
        packet = tx.packet
        if (packet.kind != "DATA" or packet.path_index != 0
                or packet.repair_index is not None
                or sim.protocol.flow_data_actions.get(packet.flow_id) != "R"
                or len(packet.path) < 2 or tx.sender != packet.origin
                or packet.path[0] != tx.sender
                or packet.path[-1] != packet.final_dst):
            continue
        src, dst = packet.origin, packet.final_dst
        next_hop = packet.path[1]
        first_hop_type = "direct" if next_hop == dst else "multihop"
        flow = sim.metrics.flows.get(packet.flow_id)
        selected_at = flow.created_at if flow is not None else packet.created_at
        decodes = sim.successful_decodes.get(tx.tx_id, {})
        truth = next_hop in decodes if tx.end <= cutoff_s else None
        off_path = sorted(node for node in decodes if node not in packet.path)
        commits = [
            event for event in sim.protocol.action_events
            if event.get("event") == "commit"
            and event.get("src") == src and event.get("dst") == dst
            and tuple(event.get("path", ())) == packet.path
            and event.get("time", float("inf")) < min(selected_at, tx.start) - 1e-9
        ]
        commit = max(commits, key=lambda event: event["time"]) if commits else None
        confirming_ack = None
        if commit is not None:
            matches = [
                earlier for earlier in sim.tx_history
                if earlier.packet.kind == "ACK"
                and earlier.packet.flow_id == commit["flow_id"]
                and earlier.packet.path == packet.path
                and earlier.packet.path_index == 0
                and earlier.sender == next_hop
                and earlier.packet.origin == dst
                and earlier.packet.final_dst == src
                and src in sim.successful_decodes.get(earlier.tx_id, {})
                and abs(earlier.end - commit["time"]) <= 1e-6
            ]
            confirming_ack = min(matches, key=lambda item: item.tx_id) if matches else None

        history = []
        if confirming_ack is not None:
            history = [
                earlier for earlier in sim.tx_history
                if earlier.packet.kind == "FLOOD"
                and earlier.packet.origin == src
                and earlier.packet.final_dst == dst
                and earlier.packet.path
                and earlier.packet.path[-1] == earlier.sender
                and earlier.sender not in packet.path
                and next_hop in sim.successful_decodes.get(earlier.tx_id, {})
                and earlier.end < confirming_ack.start - 1e-9
            ]
        witnessed = (
            max(history, key=lambda item: (item.end, -item.sender, -item.tx_id))
            if history else None
        )
        candidate = witnessed.sender if witnessed is not None else None
        deadline_at = selected_at + sim.protocol.app_deadline_s
        guard_end = min(tx.start + sim.protocol.ack_guard_s, deadline_at)
        guard_oracle = None
        if truth is False and candidate is not None:
            guard_oracle = next((
                item for item in oracle_detours(sim, tx, deadline_at, guard_end)
                if item["candidate"] == candidate
            ), None)
        hops.append({
            "flow_id": packet.flow_id,
            "tx_id": tx.tx_id,
            "src": src,
            "dst": dst,
            "path": packet.path,
            "next_hop": next_hop,
            "first_hop_type": first_hop_type,
            "intended_next_hop_decoded": truth,
            "off_path_decoders": off_path if truth is not None else None,
            "off_path_relay_decoders": (
                [node for node in off_path if sim.nodes[node].can_relay]
                if truth is not None else None
            ),
            "route_commit_flow_id": commit["flow_id"] if commit else None,
            "route_commit_at_s": commit["time"] if commit else None,
            "confirming_ack_tx_id": (
                confirming_ack.tx_id if confirming_ack else None
            ),
            "confirming_ack_start_s": (
                confirming_ack.start if confirming_ack else None
            ),
            "nominated_candidate": candidate,
            "nomination_history_tx_id": witnessed.tx_id if witnessed else None,
            "nomination_history_at_s": witnessed.end if witnessed else None,
            "history_age_at_ack_s": (
                confirming_ack.start - witnessed.end if witnessed else None
            ),
            "nominated_candidate_decoded_current": (
                candidate in decodes if candidate is not None and truth is not None
                else None
            ),
            "guard_end_s": guard_end,
            "deadline_at_s": deadline_at,
            "guard_oracle_eligible": (
                guard_oracle is not None if truth is False and candidate is not None
                else None
            ),
            "guard_oracle_detail": guard_oracle,
        })
    failed = [hop for hop in hops if hop["intended_next_hop_decoded"] is False]
    nominated_failed = [hop for hop in failed if hop["nominated_candidate"] is not None]

    def witness_counts(rows: list[Dict[str, Any]]) -> Dict[str, int]:
        return {
            "nominated_failed_hops": len(rows),
            "current_decode": sum(
                hop["nominated_candidate_decoded_current"] is True for hop in rows
            ),
            "guard_oracle": sum(
                hop["guard_oracle_eligible"] is True for hop in rows
            ),
        }

    ttl_strata = {}
    for label, ttl_s in (("no_ttl_upper_bound", None), ("30s", 30.0),
                         ("120s", 120.0), ("300s", 300.0)):
        retained = [
            hop for hop in nominated_failed
            if ttl_s is None or hop["history_age_at_ack_s"] <= ttl_s
        ]
        ttl_strata[label] = {
            **witness_counts(retained),
            "by_first_hop_type": {
                kind: witness_counts([
                    hop for hop in retained if hop["first_hop_type"] == kind
                ]) for kind in ("direct", "multihop")
            },
        }
    direct_outcomes = {
        "total": 0, "delivered": 0, "not_delivered": 0,
        "censored_deadlines": 0,
    }
    seen_direct_flows = set()
    for hop in hops:
        flow_id = hop["flow_id"]
        if hop["first_hop_type"] != "direct" or flow_id in seen_direct_flows:
            continue
        seen_direct_flows.add(flow_id)
        flow = sim.metrics.flows.get(flow_id)
        if flow is None:
            continue
        deadline_at = flow.created_at + sim.protocol.app_deadline_s
        if deadline_at > cutoff_s:
            direct_outcomes["censored_deadlines"] += 1
        elif flow.acked_at is None or flow.acked_at > deadline_at:
            direct_outcomes["total"] += 1
            key = ("delivered" if flow.delivered_at is not None
                   and flow.delivered_at <= deadline_at else "not_delivered")
            direct_outcomes[key] += 1
    return {
        "hops": hops,
        "summary": {
            "initial_r_first_hops": len(hops),
            "direct_first_hops": sum(
                hop["first_hop_type"] == "direct" for hop in hops
            ),
            "multihop_first_hops": sum(
                hop["first_hop_type"] == "multihop" for hop in hops
            ),
            "direct_decode_failures": sum(
                hop["first_hop_type"] == "direct"
                and hop["intended_next_hop_decoded"] is False for hop in hops
            ),
            "multihop_decode_failures": sum(
                hop["first_hop_type"] == "multihop"
                and hop["intended_next_hop_decoded"] is False for hop in hops
            ),
            "intended_decode_successes": sum(
                hop["intended_next_hop_decoded"] is True for hop in hops
            ),
            "intended_decode_failures": len(failed),
            "censored": sum(hop["intended_next_hop_decoded"] is None for hop in hops),
            "nominated_hops": sum(
                hop["nominated_candidate"] is not None for hop in hops
            ),
            "nominated_failed_hops": len(nominated_failed),
            "nominated_failed_hops_current_decode": sum(
                hop["nominated_candidate_decoded_current"] is True
                for hop in nominated_failed
            ),
            "nominated_failed_hops_guard_oracle": sum(
                hop["guard_oracle_eligible"] is True for hop in nominated_failed
            ),
            "local_observation_ttl_strata": ttl_strata,
            "direct_unacked_flow_outcomes": direct_outcomes,
        },
        "interpretation": (
            "Nomination reconstructs only prior same-pair FLOOD packets actually "
            "decoded at the next hop before it transmitted the route-confirming "
            "ACK. No nomination was carried or charged on that ACK. Current DATA "
            "decode is separate; guard feasibility uses hidden PRR and optimistic "
            "remaining DATA/ACK ToA, not realized or device-executable recovery. "
            "The no-TTL stratum is a loose upper bound; 30/120/300-s observation "
            "TTLs are descriptive filters at ACK transit, not tuned policies. "
            "Source-side retention after the ACK is not modeled."
            " Direct-path delivered/unACKed counts are post-hoc destination truth, "
            "not source-observable states."
        ),
    }


def summarize_ack_query_stratum(
    sim: WitnessSimulator, cutoff_s: float,
) -> Dict[str, Any]:
    """Stratify source-heard R progress without feeding outcome into decisions."""

    by_delivery = {
        label: {
            "flows": 0, "relay_ack_decoded": 0,
            "relay_ack_not_decoded": 0, "no_ack_emitted": 0,
            "ack_censored": 0,
        }
        for label in ("delivered", "not_delivered")
    }
    rows = []
    censored_deadlines = 0
    transmissions = {tx.tx_id: tx for tx in sim.tx_history}
    seen_flows = set()
    for hop in analyze_observability(sim, cutoff_s)["hops"]:
        if (hop["path_index"] != 0 or hop["evidence_kind"] != "forward"
                or hop["passive_observed_by_guard"] is not True
                or hop["flow_id"] in seen_flows):
            continue
        tx = transmissions[hop["tx_id"]]
        packet = tx.packet
        if len(packet.path) < 3:
            continue
        flow = sim.metrics.flows.get(packet.flow_id)
        if flow is None:
            continue
        deadline_at = flow.created_at + sim.protocol.app_deadline_s
        if deadline_at > cutoff_s:
            censored_deadlines += 1
            continue
        if flow.acked_at is not None and flow.acked_at <= deadline_at:
            continue
        seen_flows.add(packet.flow_id)
        relay = packet.path[1]
        ack_transmissions = [
            later for later in sim.tx_history
            if later.packet.kind == "ACK"
            and later.packet.flow_id == packet.flow_id
            and later.packet.request_id == packet.request_id
            and later.packet.origin == flow.dst
            and later.packet.final_dst == flow.src
            and tx.end <= later.start <= deadline_at
        ]
        complete = [later for later in ack_transmissions
                    if later.end <= deadline_at]
        decoded = [later for later in complete
                   if relay in sim.successful_decodes.get(later.tx_id, {})]
        if decoded:
            ack_status = "relay_ack_decoded"
        elif complete:
            ack_status = "relay_ack_not_decoded"
        elif ack_transmissions:
            ack_status = "ack_censored"
        else:
            ack_status = "no_ack_emitted"
        initial_on_path = [
            later for later in complete
            if later.packet.repair_index is None
            and later.packet.path == packet.path
            and later.packet.path_index == 1
            and later.sender == packet.path[2]
        ]
        delivered = (flow.delivered_at is not None
                     and flow.delivered_at <= deadline_at)
        label = "delivered" if delivered else "not_delivered"
        by_delivery[label]["flows"] += 1
        by_delivery[label][ack_status] += 1
        rows.append({
            "flow_id": packet.flow_id,
            "first_hop_tx_id": tx.tx_id,
            "source_observed_forward_tx_id": hop["evidence_tx_id"],
            "first_relay": relay,
            "destination_delivery_by_deadline": delivered,
            "source_ack_by_deadline": False,
            "first_relay_destination_ack_status": ack_status,
            "destination_ack_tx_count": len(ack_transmissions),
            "first_relay_initial_on_path_ack_decoded": any(
                relay in sim.successful_decodes.get(later.tx_id, {})
                for later in initial_on_path
            ),
        })
    return {
        "flows": rows,
        "summary": {
            "source_observed_unacked_r_flows": len(rows),
            "censored_flow_deadlines": censored_deadlines,
        },
        "by_destination_delivery": by_delivery,
        "interpretation": (
            "Rows require a multihop initial R DATA forward decoded at the source "
            "within its guard, and no source ACK by the original deadline. "
            "Destination delivery and first-relay ACK decode are offline outcome "
            "strata, never inputs to the local nomination rule. ACK status includes "
            "any emitted destination-origin ACK for that flow; the separate "
            "initial-on-path field excludes recovery paths."
        ),
    }


def run_diagnostic(seed: int) -> Dict[str, Any]:
    """Replay frozen DHR on fresh seeds with only receive-side instrumentation."""

    if seed not in EXPLORATORY_SEEDS:
        raise ValueError(f"only fresh exploratory seeds {EXPLORATORY_SEEDS} are allowed")
    case = SR_CASES["recurring_fading"]
    deadline_s = 30.0
    config = make_args(case)
    config.sr_app_deadline_s = deadline_s
    nodes = generate_nodes(
        case.nodes, case.area_m, random.Random(seed), repeater_ratio=0.0,
    )
    protocol = build_protocol("meshecho-dhr", config)
    sim = WitnessSimulator(
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
    flows = list(metrics.flows.values())
    return {
        "case": case.key,
        "protocol": "meshecho-dhr",
        "seed": seed,
        "deadline_s": deadline_s,
        "cutoff_s": cutoff_s,
        "scheduled_trace_sha256": trace_hash,
        "scheduled_flows": len(scheduled),
        "registered_flows": len(flows),
        "ack_by_deadline": sum(
            flow.acked_at is not None
            and flow.acked_at <= flow.created_at + deadline_s
            for flow in flows
        ),
        "delivery_by_deadline": sum(
            flow.delivered_at is not None
            and flow.delivered_at <= flow.created_at + deadline_s
            for flow in flows
        ),
        "first_hop_witness": analyze_first_hop_witness(sim, cutoff_s),
        "ack_query_stratum": summarize_ack_query_stratum(sim, cutoff_s),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, choices=EXPLORATORY_SEEDS,
                        default=EXPLORATORY_SEEDS)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.output is not None and args.output.exists():
        parser.error(f"output already exists: {args.output}")
    sources = {
        "first_hop_diagnostic": Path(__file__).resolve(),
        "sr_observability_diagnostic": ROOT / "tools" / "diagnose_sr_observability.py",
        "simulator": ROOT / "lora_mesh_sim.py",
        "runner": ROOT / "tools" / "run_sr_experiment.py",
        "probe_helpers": ROOT / "tools" / "run_fair_multihop_probe.py",
    }
    result = {
        "source_sha256": {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in sources.items()
        },
        "runs": [run_diagnostic(seed) for seed in args.seeds],
    }
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(encoded, end="")
    else:
        with args.output.open("x", encoding="utf-8") as output:
            output.write(encoded)


if __name__ == "__main__":
    main()
