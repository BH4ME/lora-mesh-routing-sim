#!/usr/bin/env python3
"""Passive exposure screen for terminal-ACK cancellation of queued FLOOD relays."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import Packet, PendingSend, RxInfo, Transmission, build_protocol, generate_nodes
from tools.run_fair_multihop_probe import connected_multihop_pairs, make_args, make_radio
from tools.run_sr_experiment import (
    RecordingSimulator, SR_CASES, SrCase, run_one_sr, schedule_sr_traffic,
)

PROTOCOL = "meshecho-dhr-flood"
EXPLORATORY_SEEDS = (22001, 22002, 22003)
RESERVED_HOLDOUT_SEEDS = frozenset(range(17001, 17041))


def _epoch_name(repair_index: Optional[int]) -> str:
    if repair_index is None:
        return "initial_f"
    if repair_index == 2:
        return "same_flow_recovery_f"
    raise AssertionError(f"unexpected fixed-F FLOOD marker: {repair_index}")


def natural_destination_ack(ack_tx: Transmission, max_hops: int) -> bool:
    ack = ack_tx.packet
    path = ack.path
    return bool(
        ack.kind == "ACK"
        and not ack.app_payload
        and ack.flow_id > 0
        and ack.request_id == ack.flow_id
        and 2 <= len(path) <= max_hops + 1
        and len(set(path)) == len(path)
        and path[0] == ack.final_dst
        and path[-1] == ack.origin
        and 0 <= ack.path_index < len(path) - 1
        and ack_tx.sender == path[ack.path_index + 1]
    )


def cancelable_flood_forward(
    ack_tx: Transmission, receiver: int, flood: Packet,
    pending: PendingSend, protocol_pending: PendingSend | None,
    max_hops: int,
) -> bool:
    """Check only wire-visible ACK/FLOOD identity and local pending state."""

    return bool(
        matching_ack_flood(ack_tx, receiver, flood, max_hops)
        and pending is protocol_pending
        and not pending.canceled
        and not pending.committed
    )


def matching_ack_flood(
    ack_tx: Transmission, receiver: int, flood: Packet, max_hops: int,
) -> bool:
    """Match a destination ACK to an off-path relay's local FLOOD epoch."""

    ack = ack_tx.packet
    return bool(
        natural_destination_ack(ack_tx, max_hops)
        and flood.kind == "FLOOD"
        and flood.app_payload
        and flood.path
        and flood.path[-1] == receiver
        and flood.path[0] == flood.origin
        and 2 <= len(flood.path) <= max_hops
        and len(set(flood.path)) == len(flood.path)
        and flood.path_index == len(flood.path) - 1
        and flood.ttl >= 1
        and receiver != flood.origin
        and receiver not in ack.path
        and ack.protocol == flood.protocol
        and ack.flow_id == flood.flow_id
        and ack.request_id == flood.request_id == flood.flow_id
        and ack.repair_index == flood.repair_index
        and ack.origin == flood.final_dst
        and ack.final_dst == flood.origin
    )


class AckOverhearSimulator(RecordingSimulator):
    """Observe physically decoded ACKs and pending relays without mutations."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.pending_floods_by_flow: Dict[int, list[tuple[int, Packet, PendingSend]]] = defaultdict(list)
        self.opportunities: list[Dict[str, Any]] = []
        self.committed_future_opportunities: list[Dict[str, Any]] = []
        self._opportunity_by_handle: Dict[int, Dict[str, Any]] = {}
        self._committed_future_by_handle: Dict[int, Dict[str, Any]] = {}
        self._committed_flood_tx_by_handle: Dict[int, Transmission] = {}
        self.natural_ack_decodes = 0
        self.strict_candidate_ack_decode_events = 0
        self.strict_candidate_pairs = 0

    def transmit_later(
        self, sender: int, packet: Packet, delay_s: float,
        pending: Optional[PendingSend] = None,
    ) -> PendingSend:
        handle = super().transmit_later(sender, packet, delay_s, pending)
        if packet.kind == "FLOOD" and sender != packet.origin:
            self.pending_floods_by_flow[packet.flow_id].append((sender, packet, handle))
        return handle

    def observe_ack_decode(self, ack_tx: Transmission, receiver: int) -> None:
        if not natural_destination_ack(ack_tx, self.max_hops):
            return
        self.natural_ack_decodes += 1
        strict_candidates_this_decode = 0
        for relay, flood, handle in self.pending_floods_by_flow.get(ack_tx.packet.flow_id, ()):
            if relay != receiver or not matching_ack_flood(
                ack_tx, receiver, flood, self.max_hops,
            ):
                continue
            local_handle = self.protocol.pending_fallback.get((relay, flood.flood_key))
            if local_handle is not handle:
                continue
            if handle.committed:
                tx = self._committed_flood_tx_by_handle.get(id(handle))
                if (tx is not None and tx.start > self.now
                        and id(handle) not in self._committed_future_by_handle):
                    event = {
                        "flow_id": flood.flow_id,
                        "relay": relay,
                        "repair_index": flood.repair_index,
                        "detected_at_s": self.now,
                        "ack_tx_id": ack_tx.tx_id,
                        "baseline_relay_tx_id": tx.tx_id,
                        "already_committed": True,
                        "canceled_flag": handle.canceled,
                        "future_tx_start_s": tx.start,
                        "future_tx_airtime_s": tx.end - tx.start,
                    }
                    self.committed_future_opportunities.append(event)
                    self._committed_future_by_handle[id(handle)] = event
                continue
            if handle.canceled:
                continue
            strict_candidates_this_decode += 1
            if id(handle) in self._opportunity_by_handle:
                continue
            event = {
                "flow_id": flood.flow_id,
                "source": flood.origin,
                "destination": flood.final_dst,
                "relay": relay,
                "repair_index": flood.repair_index,
                "detected_at_s": self.now,
                "ack_tx_id": ack_tx.tx_id,
                "ack_sender": ack_tx.sender,
                "ack_path": list(ack_tx.packet.path),
                "pending_flood_path": list(flood.path),
                "baseline_relay_tx_id": None,
                "baseline_relay_tx_start_s": None,
                "potential_avoidable_airtime_s": 0.0,
            }
            self.opportunities.append(event)
            self._opportunity_by_handle[id(handle)] = event
        if strict_candidates_this_decode:
            self.strict_candidate_ack_decode_events += 1
            self.strict_candidate_pairs += strict_candidates_this_decode

    def try_receive(self, tx: Transmission, receiver: int) -> Optional[RxInfo]:
        decoded = super().try_receive(tx, receiver)
        if decoded is not None and tx.packet.kind == "ACK":
            self.observe_ack_decode(tx, receiver)
        return decoded

    def begin_transmission(self, sender: int, packet: Packet, pending: PendingSend) -> None:
        previous = len(self.tx_history)
        super().begin_transmission(sender, packet, pending)
        event = self._opportunity_by_handle.get(id(pending))
        if event is None or len(self.tx_history) == previous:
            if (len(self.tx_history) > previous and packet.kind == "FLOOD"
                    and sender != packet.origin):
                self._committed_flood_tx_by_handle[id(pending)] = self.tx_history[-1]
            return
        tx = self.tx_history[-1]
        self._committed_flood_tx_by_handle[id(pending)] = tx
        if tx.sender != event["relay"] or tx.packet.kind != "FLOOD":
            raise AssertionError("an exposed FLOOD handle committed to another packet")
        flow = self.metrics.flows.get(packet.flow_id)
        if flow is None or flow.delivered_at is None:
            raise AssertionError("natural destination ACK preceded destination delivery")
        if not tx.start > max(event["detected_at_s"], flow.delivered_at):
            raise AssertionError("exposed relay TX did not follow ACK and delivery")
        event["baseline_relay_tx_id"] = tx.tx_id
        event["baseline_relay_tx_start_s"] = tx.start
        event["potential_avoidable_airtime_s"] = tx.end - tx.start


def _replay(
    case: SrCase, seed: int, deadline_s: float, observed: bool,
) -> tuple[RecordingSimulator, str]:
    config = make_args(case)
    config.sr_app_deadline_s = deadline_s
    nodes = generate_nodes(
        case.nodes, case.area_m, random.Random(seed), repeater_ratio=0.0,
    )
    simulator_class = AckOverhearSimulator if observed else RecordingSimulator
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


def _tx_trace_sha256(transmissions: list[Transmission]) -> str:
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
    if len(sim.metrics.flows) != len(baseline.flows):
        raise AssertionError(f"seed {seed}: flow population differs")
    for expected in baseline.flows:
        flow = sim.metrics.flows.get(expected["flow_id"])
        if (flow is None or flow.src != expected["src"]
                or flow.dst != expected["dst"]
                or flow.created_at != expected["enqueued_at"]
                or flow.delivered_at != expected["delivered_at"]
                or flow.acked_at != expected["acked_at"]
                or sim.protocol.flow_data_actions.get(flow.flow_id)
                != expected["source_action"]):
            raise AssertionError(f"seed {seed}: flow {expected['flow_id']} differs")
    actions = [
        {"case": case.key, "protocol": PROTOCOL, "seed": seed, **event}
        for event in sim.protocol.action_events
    ]
    if actions != baseline.actions:
        raise AssertionError(f"seed {seed}: protocol actions differ")
    for field, actual in (
        ("raw_tx_count", sim.metrics.tx_count),
        ("raw_data_tx", sim.metrics.data_tx),
        ("raw_control_tx", sim.metrics.control_tx),
        ("collision_failures", sim.metrics.collision_fail),
    ):
        if baseline.row[field] != actual:
            raise AssertionError(f"seed {seed}: {field} differs")


def run_diagnostic(
    seed: int, case: SrCase = SR_CASES["recurring_fading"],
    deadline_s: float = 30.0,
) -> Dict[str, Any]:
    """Replay unchanged fixed-F DHR and verify passive observer parity."""

    if seed in RESERVED_HOLDOUT_SEEDS:
        raise ValueError("BAR holdout seeds 17001-17040 are reserved")
    if case == SR_CASES["recurring_fading"] and seed not in EXPLORATORY_SEEDS:
        raise ValueError(f"only exploratory seeds {EXPLORATORY_SEEDS} are allowed")
    baseline = run_one_sr(case, PROTOCOL, seed, deadline_s=deadline_s)
    plain, plain_trace = _replay(case, seed, deadline_s, observed=False)
    observed, observed_trace = _replay(case, seed, deadline_s, observed=True)
    if not (baseline.row["scheduled_trace_sha256"] == plain_trace == observed_trace):
        raise AssertionError(f"seed {seed}: application schedule differs")
    _verify_against_baseline(plain, baseline, case, seed)
    _verify_against_baseline(observed, baseline, case, seed)
    plain_tx_sha = _tx_trace_sha256(plain.tx_history)
    observed_tx_sha = _tx_trace_sha256(observed.tx_history)
    if plain_tx_sha != observed_tx_sha:
        raise AssertionError(f"seed {seed}: complete TX trace differs")
    cutoff = case.duration_s + deadline_s
    strict = [
        event for event in observed.opportunities
        if event["baseline_relay_tx_start_s"] is not None
        and event["baseline_relay_tx_start_s"] <= cutoff
    ]
    committed_future = [
        event for event in observed.committed_future_opportunities
        if event["future_tx_start_s"] <= cutoff
    ]
    post_delivery_relay_txs = [
        tx for tx in observed.tx_history
        if tx.packet.kind == "FLOOD" and tx.sender != tx.packet.origin
        and tx.start <= cutoff
        and (flow := observed.metrics.flows.get(tx.packet.flow_id)) is not None
        and flow.delivered_at is not None
        and tx.start > flow.delivered_at
    ]
    by_epoch = {}
    for name, marker in (("initial_f", None), ("same_flow_recovery_f", 2)):
        epoch_opportunities = [
            event for event in observed.opportunities
            if event["repair_index"] == marker
        ]
        epoch_strict = [event for event in strict if event["repair_index"] == marker]
        epoch_post_delivery = [
            tx for tx in post_delivery_relay_txs
            if tx.packet.repair_index == marker
        ]
        by_epoch[name] = {
            "strict_unique_pending_handles": len(epoch_opportunities),
            "strict_potential_avoidable_relay_tx": len(epoch_strict),
            "strict_potential_avoidable_airtime_s": sum(
                event["potential_avoidable_airtime_s"] for event in epoch_strict
            ),
            "post_delivery_flood_relay_tx": len(epoch_post_delivery),
            "post_delivery_flood_relay_airtime_s": sum(
                tx.end - tx.start for tx in epoch_post_delivery
            ),
        }
    for event in observed.opportunities:
        _epoch_name(event["repair_index"])
    if sum(item["strict_unique_pending_handles"] for item in by_epoch.values()) != len(observed.opportunities):
        raise AssertionError("FLOOD epoch accounting is incomplete")
    summary = {
        "scheduled_unicast_flows": len(baseline.flows),
        "delivered_by_deadline": sum(flow["delivery_by_deadline"] for flow in baseline.flows),
        "acked_by_deadline": sum(flow["ack_by_deadline"] for flow in baseline.flows),
        "natural_destination_ack_decodes": observed.natural_ack_decodes,
        "strict_candidate_ack_decode_events": observed.strict_candidate_ack_decode_events,
        "strict_candidate_pairs": observed.strict_candidate_pairs,
        "strict_cancelable_pending_relays": len(observed.opportunities),
        "strict_potential_avoidable_relay_tx": len(strict),
        "strict_potential_avoidable_airtime_s": sum(
            item["strict_potential_avoidable_airtime_s"] for item in by_epoch.values()
        ),
        "committed_future_pending_relays_upper_bound": len(observed.committed_future_opportunities),
        "committed_future_relay_tx_within_horizon": len(committed_future),
        "committed_future_airtime_upper_bound_s": sum(
            event["future_tx_airtime_s"] for event in committed_future
        ),
        "post_delivery_flood_relay_tx": len(post_delivery_relay_txs),
        "post_delivery_flood_relay_airtime_s": sum(
            tx.end - tx.start for tx in post_delivery_relay_txs
        ),
        "by_flood_epoch": by_epoch,
    }
    if summary["strict_potential_avoidable_airtime_s"] > (
        summary["post_delivery_flood_relay_airtime_s"] + 1e-9
    ):
        raise AssertionError("strict opportunity exceeds post-delivery relay airtime")
    return {
        "seed": seed,
        "protocol": PROTOCOL,
        "case": asdict(case),
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
        "summary": summary,
        "strict_opportunities": observed.opportunities,
        "committed_future_upper_bound": observed.committed_future_opportunities,
    }


def build_report(
    seeds: tuple[int, ...] = EXPLORATORY_SEEDS,
    case: SrCase = SR_CASES["recurring_fading"],
    deadline_s: float = 30.0,
) -> Dict[str, Any]:
    """Collect three passive replays under a source-hash freeze."""

    if not seeds or len(set(seeds)) != len(seeds):
        raise ValueError("seeds must be nonempty and unique")
    if any(seed in RESERVED_HOLDOUT_SEEDS for seed in seeds):
        raise ValueError("BAR holdout seeds 17001-17040 are reserved")
    source_paths = (
        ROOT / "lora_mesh_sim.py",
        ROOT / "tools" / "run_fair_multihop_probe.py",
        ROOT / "tools" / "run_sr_experiment.py",
        Path(__file__).resolve(),
        ROOT / "tests" / "test_ack_overhear_cancel_exposure.py",
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
    summaries = [run["summary"] for run in runs]
    numeric_keys = (
        key for key, value in summaries[0].items() if isinstance(value, (int, float))
    )
    summary = {
        key: (
            math.fsum(run[key] for run in summaries)
            if isinstance(summaries[0][key], float)
            else sum(run[key] for run in summaries)
        ) for key in numeric_keys
    }
    summary["by_flood_epoch"] = {
        epoch: {
            key: (
                math.fsum(run["by_flood_epoch"][epoch][key] for run in summaries)
                if isinstance(summaries[0]["by_flood_epoch"][epoch][key], float)
                else sum(run["by_flood_epoch"][epoch][key] for run in summaries)
            )
            for key in summaries[0]["by_flood_epoch"][epoch]
        }
        for epoch in ("initial_f", "same_flow_recovery_f")
    }
    return {
        "analysis_type": "passive terminal-ACK overhear / pending-F cancellation exposure",
        "counterfactual_outcomes": None,
        "seed_use": "fresh-exploratory-not-development-or-holdout",
        "seeds": list(seeds),
        "protocol": PROTOCOL,
        "case": asdict(case),
        "deadline_s": deadline_s,
        "source_sha256": before,
        "summary": summary,
        "interpretation_boundary": (
            "Strict opportunities require a physically decoded natural destination "
            "ACK, locally matching flow and FLOOD repair marker, an off-ACK-path "
            "relay, and the protocol's identical uncanceled and uncommitted "
            "PendingSend handle. Potentially avoidable airtime counts only such "
            "handles that later actually transmit after destination delivery. "
            "This is a local transmission opportunity bound, not realized "
            "network airtime savings or a causal reliability result. Already "
            "committed future-start handles are reported separately and cannot "
            "be canceled under the current API. MeshEchoLPR already suppresses "
            "pending PATCH_RELAY on successor DATA/ACK overhearing; terminal "
            "destination-ACK suppression of general FLOOD forwarding is the "
            "narrow candidate, not ACK-based suppression in general."
        ),
        "runs": runs,
    }


def write_report(report: Dict[str, Any], path: Path) -> str:
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
