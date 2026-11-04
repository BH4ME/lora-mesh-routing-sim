#!/usr/bin/env python3
"""Source-local MeshEcho route/FLOOD branch diagnostic."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import defaultdict
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import (
    MeshEchoDHR, Node, Packet, PendingSend, RxInfo, Transmission, generate_nodes,
)
from tools.run_fair_multihop_probe import (
    connected_multihop_pairs, make_args, make_radio,
)
from tools.run_sr_experiment import (
    SR_CASES, RecordingSimulator, SrCase, schedule_sr_traffic,
)


ARMS = ("R", "F", "R-F", "R-R")


def _normalized(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _normalized(item) for key, item in sorted(
            value.items(), key=lambda pair: str(pair[0])
        )}
    if isinstance(value, (list, tuple)):
        return [_normalized(item) for item in value]
    if isinstance(value, set):
        return sorted(_normalized(item) for item in value)
    return value


def _hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


class _KeyedStream:
    """Replace a scoped uniform while retaining any other RNG draws."""

    def __init__(self, original: Any, seed: int) -> None:
        self.original = original
        self.seed = seed
        self.key: tuple[Any, ...] | None = None

    def random(self) -> float:
        if self.key is None:
            return self.original.random()
        encoded = json.dumps((self.seed, *self.key), separators=(",", ":"))
        return int.from_bytes(hashlib.sha256(encoded.encode("ascii")).digest()[:8], "big") / 2**64

    def __getattr__(self, name: str) -> Any:
        return getattr(self.original, name)


class BranchSimulator(RecordingSimulator):
    """Pair each potential receive callback by flow and directed-link ordinal."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.reception_ordinals: dict[tuple[int, int, int], int] = defaultdict(int)
        self.reception_stream = _KeyedStream(self.channel_random, self.seed)
        self.channel_random = self.reception_stream
        self.protocol_stream = _KeyedStream(self.random, self.seed)
        self.random = self.protocol_stream
        self.app_event_order: dict[int, int] = {}
        self.collision_failures: list[dict[str, Any]] = []
        self.rejected_rescue_requests: list[dict[str, Any]] = []

    def schedule(self, when: float, event_type: str, data: Any) -> None:
        super().schedule(when, event_type, data)
        if event_type == "app_send":
            self.app_event_order[data[2]] = self._event_counter

    def begin_transmission(self, sender: int, packet: Packet,
                           pending: PendingSend) -> None:
        before = self.metrics.tx_count
        super().begin_transmission(sender, packet, pending)
        if (self.metrics.tx_count == before and sender == packet.origin
                and packet.repair_index in {1, 2}
                and packet.kind in {"DATA", "FLOOD"}):
            self.rejected_rescue_requests.append({
                "flow_id": packet.flow_id, "time": self.now,
                "reason": (
                    "pending_canceled" if pending.canceled
                    else "pending_start_guard_rejected"
                ),
            })

    def try_receive(self, tx: Transmission, receiver: int) -> Any:
        if receiver == tx.sender:
            return super().try_receive(tx, receiver)
        link = (tx.packet.flow_id, tx.sender, receiver)
        self.reception_ordinals[link] += 1
        self.reception_stream.key = (*link, self.reception_ordinals[link])
        try:
            before = self.metrics.collision_fail
            received = super().try_receive(tx, receiver)
            if self.metrics.collision_fail > before:
                self.collision_failures.append({
                    "tx_id": tx.tx_id, "flow_id": tx.packet.flow_id,
                    "sender": tx.sender, "receiver": receiver,
                    "tx_start": tx.start, "completed_at": self.now,
                })
            return received
        finally:
            self.reception_stream.key = None


class BranchProtocol(MeshEchoDHR):
    def __init__(self, *args: Any, target_flow_id: int | None = None,
                 arm: str = "R", **kwargs: Any) -> None:
        super().__init__(*args, rescue_mode="none", **kwargs)
        self.target_flow_id = target_flow_id
        self.arm = arm
        self.eligible_targets: list[dict[str, Any]] = []
        self.target_prefix: dict[str, Any] | None = None
        self._flood_packet: Packet | None = None
        self._flood_ordinals: dict[tuple[int, int, int | None], int] = defaultdict(int)

    def _pre_app_snapshot(self, src: int, dst: int, flow_id: int) -> dict[str, Any]:
        state = self.destination_state.get((src, dst))
        entry = self.route_cache[src].get(dst)
        flows = [
            _normalized(asdict(flow))
            for _, flow in sorted(self.sim.metrics.flows.items())
        ]
        return {
            "event": {"time": self.sim.now, "flow_id": flow_id,
                      "tie_order": self.sim.app_event_order[flow_id]},
            "nodes": [_normalized(asdict(node)) for _, node in sorted(self.sim.nodes.items())],
            "radio": _normalized(asdict(self.sim.radio)),
            "max_hops": self.sim.max_hops,
            "matched_rreq_timing": self.sim.matched_rreq_timing,
            "shadowing": _normalized(self.sim.link_shadowing_db),
            "source": {
                "src": src, "dst": dst,
                "state": _normalized(asdict(state)) if state is not None else None,
                "route": _normalized(asdict(entry)) if entry is not None else None,
                "source_tokens": self.source_tokens[src],
                "source_app_count": self.source_app_counts[src],
            },
            "flow_records": flows,
            "ack_records": _normalized([
                event for event in self.action_events
                if event.get("event") == "dhr_source_ack_rx"
            ]),
            "action_events": _normalized(self.action_events),
            "tx_prefix": [
                {"tx_id": tx.tx_id, "sender": tx.sender, "start": tx.start,
                 "end": tx.end, "packet": _normalized(asdict(tx.packet))}
                for tx in self.sim.tx_history
            ],
        }

    def send_app(self, src: int, dst: int, flow_id: int) -> None:
        state = self.destination_state.get((src, dst))
        entry = self.route_cache[src].get(dst)
        locally_eligible = (
            state is not None and entry is not None
            and entry.expires_at > self.sim.now
            and state.pending_discovery_flow is None
            and self.trailing_r_misses(state) == 1
        )
        prefix = self._pre_app_snapshot(src, dst, flow_id) if (
            locally_eligible or flow_id == self.target_flow_id
        ) else None
        if flow_id == self.target_flow_id:
            self.target_prefix = prefix
        super().send_app(src, dst, flow_id)
        reference_action = "R" if (
            flow_id == self.target_flow_id and self.arm == "F"
            and self.flow_actions.get(flow_id) == "F"
        ) else self.flow_actions.get(flow_id)
        if locally_eligible and reference_action == "R":
            self.eligible_targets.append({
                "flow_id": flow_id, "src": src, "dst": dst,
                "enqueued_at": self.sim.now,
                "route_path": entry.path,
                "route_hops": len(entry.path) - 1,
                "route_age_s": self.sim.now - entry.created_at,
                "pre_app_prefix": prefix,
                "pre_app_prefix_sha256": _hash(prefix),
            })

    def send_data_on_path(self, src: int, dst: int, flow_id: int,
                          entry: Any, candidate: bool = False) -> None:
        if flow_id == self.target_flow_id and self.arm == "F" and not candidate:
            self.flow_actions[flow_id] = "F"
            self.sim.metrics.route_cache_hits -= 1
            self.sim.metrics.route_cache_misses += 1
            decision = self.action_events[-1]
            if decision.get("event") == "decision" and decision.get("flow_id") == flow_id:
                decision["action"] = "F"
                decision["reason"] = "diagnostic-target-f"
            self.send_flood(src, dst, flow_id)
            return
        super().send_data_on_path(src, dst, flow_id, entry, candidate=candidate)

    def expire_data_ack(self, flow_id: int) -> None:
        prior_mode = self.rescue_mode
        if flow_id == self.target_flow_id:
            self.rescue_mode = {"R-F": "flood", "R-R": "repeat"}.get(self.arm, "none")
        try:
            super().expire_data_ack(flow_id)
        finally:
            self.rescue_mode = prior_mode

    def on_fallback(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
        prior_packet = self._flood_packet
        self._flood_packet = packet if packet.kind == "FLOOD" else None
        try:
            super().on_fallback(receiver, packet, rx)
        finally:
            self._flood_packet = prior_packet

    def flood_delay(self, receiver: int | None = None,
                    rx: RxInfo | None = None) -> float:
        packet = self._flood_packet
        if packet is None or receiver is None:
            return super().flood_delay(receiver, rx)
        key = (packet.flow_id, receiver, packet.repair_index)
        self._flood_ordinals[key] += 1
        self.sim.protocol_stream.key = (*key, self._flood_ordinals[key])
        try:
            return super().flood_delay(receiver, rx)
        finally:
            self.sim.protocol_stream.key = None


def _protocol(case: SrCase, target_flow_id: int | None, arm: str) -> BranchProtocol:
    config = make_args(case)
    config.sr_app_deadline_s = 30.0
    return BranchProtocol(
        target_flow_id=target_flow_id, arm=arm,
        route_ttl_s=config.calm_route_ttl_s,
        discovery_window_s=config.calm_discovery_window_s,
        app_deadline_s=config.sr_app_deadline_s,
        ack_guard_s=getattr(config, "sr_ack_guard_s", 15.0),
        rrep_wait_s=getattr(config, "sr_rrep_wait_s", 10.0),
    )


def run_trace(
    case: SrCase, seed: int, nodes: Sequence[Node],
    scheduled_trace: Sequence[tuple[float, int, int, int]],
    simulator_cls: type[BranchSimulator] = BranchSimulator,
) -> dict[str, Any]:
    """Run a supplied small trace or one generated by the standard scheduler."""
    trace = sorted(scheduled_trace, key=lambda item: item[0])
    cutoff = case.duration_s + 30.0

    def replay(target_flow_id: int | None, arm: str) -> tuple[BranchSimulator, BranchProtocol]:
        protocol = _protocol(case, target_flow_id, arm)
        sim = simulator_cls(
            [replace(node) for node in nodes], make_radio(make_args(case)),
            protocol, seed=seed, max_hops=case.max_hops,
            independent_random_streams=True,
            matched_rreq_timing=case.matched_rreq_timing,
        )
        for when, src, dst, flow_id in trace:
            sim.schedule(when, "app_send", (src, dst, flow_id))
        sim.run(cutoff)
        return sim, protocol

    _, reference = replay(None, "R")
    branches: list[dict[str, Any]] = []
    for target in reference.eligible_targets:
        for arm in ARMS:
            sim, protocol = replay(target["flow_id"], arm)
            prefix = protocol.target_prefix
            prefix_match = prefix == target["pre_app_prefix"]
            if not prefix_match:
                raise ValueError(
                    f"seed {seed} flow {target['flow_id']} arm {arm}: pre-app prefix mismatch"
                )
            source_bookings = [
                tx for tx in sim.tx_history
                if tx.sender == target["src"] and tx.packet.flow_id == target["flow_id"]
                and tx.packet.kind in {"DATA", "FLOOD"}
            ]
            source_starts = [tx for tx in source_bookings if tx.start <= cutoff]
            initial = next((tx for tx in source_starts
                            if tx.packet.repair_index is None), None)
            booked_initial = next((tx for tx in source_bookings
                                   if tx.packet.repair_index is None), None)
            expected_initial = "FLOOD" if arm == "F" else "DATA"
            if booked_initial is not None and booked_initial.packet.kind != expected_initial:
                raise ValueError(
                    f"seed {seed} flow {target['flow_id']} arm {arm}: "
                    f"expected initial {expected_initial} source TX"
                )
            deadline_at = target["enqueued_at"] + 30.0
            full_tx = [tx for tx in sim.tx_history if tx.start <= cutoff]
            window_tx = [tx for tx in full_tx
                         if target["enqueued_at"] <= tx.start <= deadline_at]
            target_full_tx = [tx for tx in full_tx
                              if tx.packet.flow_id == target["flow_id"]]
            target_window_tx = [tx for tx in window_tx
                                if tx.packet.flow_id == target["flow_id"]]
            guard_events = [event for event in protocol.action_events
                            if event.get("event") == "dhr_guard"
                            and event.get("flow_id") == target["flow_id"]]
            if len(guard_events) > 1:
                raise ValueError("target has multiple DHR guard events")
            guard = guard_events[0] if guard_events else None
            rescue_starts = [tx for tx in source_starts
                             if tx.packet.repair_index in {1, 2}]
            if len(rescue_starts) > 1:
                raise ValueError("target has multiple rescue source starts")
            rescue = rescue_starts[0] if rescue_starts else None
            flow = sim.metrics.flows[target["flow_id"]]
            initial_exposed = initial is not None and initial.start <= deadline_at
            rescue_expected = guard is not None and guard["selected_action"] in {"F", "R"}
            rescue_rejections = [
                item for item in sim.rejected_rescue_requests
                if item["flow_id"] == target["flow_id"]
            ]
            booked_rescue = next((
                tx for tx in source_bookings
                if tx.packet.repair_index in {1, 2}
            ), None)
            branches.append({
                "seed": seed, "flow_id": target["flow_id"], "arm": arm,
                "prefix_match": prefix_match,
                "pre_app_prefix_sha256": _hash(prefix) if prefix is not None else None,
                "src": target["src"], "dst": target["dst"],
                "enqueued_at": target["enqueued_at"], "deadline_at": deadline_at,
                "source_action": protocol.flow_actions[target["flow_id"]],
                "data_action": protocol.flow_data_actions[target["flow_id"]],
                "initial_source_kind": initial.packet.kind if initial else None,
                "initial_source_start_at": initial.start if initial else None,
                "booked_initial_source_kind": (
                    booked_initial.packet.kind if booked_initial else None
                ),
                "booked_initial_source_start_at": (
                    booked_initial.start if booked_initial else None
                ),
                "initial_exposed_by_deadline": initial_exposed,
                "initial_nonexposure_reason": (
                    None if initial_exposed else
                    "initial_started_after_deadline" if initial is not None else
                    "initial_queued_after_run_stop" if booked_initial is not None else
                    "initial_not_booked"
                ),
                "source_data_starts": [
                    {"kind": tx.packet.kind, "repair_index": tx.packet.repair_index,
                     "start": tx.start, "end": tx.end}
                    for tx in source_starts
                ],
                "accepted_ack_at": flow.acked_at,
                "first_delivery_at": flow.delivered_at,
                "ack_by_deadline": flow.acked_at is not None and flow.acked_at <= deadline_at,
                "delivery_by_deadline": (
                    flow.delivered_at is not None and flow.delivered_at <= deadline_at
                ),
                "guard_at": guard["time"] if guard else None,
                "guard_admitted": guard["admitted"] if guard else None,
                "guard_reason": guard["reason"] if guard else None,
                "guard_selected_action": guard["selected_action"] if guard else None,
                "rescue_started": rescue is not None,
                "rescue_source_kind": rescue.packet.kind if rescue else None,
                "rescue_source_start_at": rescue.start if rescue else None,
                "rescue_pending_rejections": rescue_rejections,
                "rescue_nonstart_reason": (
                    None if rescue is not None or not rescue_expected else
                    rescue_rejections[0]["reason"] if rescue_rejections else
                    "booked_after_run_stop" if booked_rescue is not None else
                    "pending_not_processed_by_run_stop"
                ),
                "network_window_airtime_s": sum(tx.end - tx.start for tx in window_tx),
                "target_window_airtime_s": sum(
                    tx.end - tx.start for tx in target_window_tx
                ),
                "target_flow_full_run_airtime_s": sum(
                    tx.end - tx.start for tx in target_full_tx
                ),
                "target_post_deadline_airtime_s": sum(
                    tx.end - tx.start for tx in target_full_tx
                    if tx.start > deadline_at
                ),
                "network_full_run_airtime_s": sum(
                    tx.end - tx.start for tx in full_tx
                ),
                "window_data_tx": sum(
                    not tx.packet.is_control for tx in window_tx
                ),
                "window_ack_tx": sum(
                    tx.packet.kind == "ACK" for tx in window_tx
                ),
                "window_other_control_tx": sum(
                    tx.packet.is_control and tx.packet.kind != "ACK"
                    for tx in window_tx
                ),
                "window_collision_failures": sum(
                    target["enqueued_at"] <= event["tx_start"] <= deadline_at
                    for event in sim.collision_failures
                ),
                "window_censored_tx_count": sum(
                    tx.end > cutoff for tx in window_tx
                ),
                "full_run_censored_tx_count": sum(
                    tx.end > cutoff for tx in full_tx
                ),
                "queued_after_full_run_tx_count": sum(
                    tx.start > cutoff for tx in sim.tx_history
                ),
            })
    return {
        "case": asdict(case), "seed": seed,
        "case_config_sha256": _hash(asdict(case)),
        "scheduled_trace": trace,
        "scheduled_trace_sha256": _hash(trace),
        "generation_horizon_s": case.duration_s,
        "drain_until_s": cutoff,
        "eligible_targets": reference.eligible_targets,
        "branches": branches,
    }


def run_seed(case: SrCase, seed: int) -> dict[str, Any]:
    """Use the SR experiment topology, pair pool and application scheduler."""
    nodes = generate_nodes(case.nodes, case.area_m, random.Random(seed), repeater_ratio=0.0)
    scheduler_sim = BranchSimulator(
        [replace(node) for node in nodes], make_radio(make_args(case)),
        _protocol(case, None, "R"), seed=seed, max_hops=case.max_hops,
        independent_random_streams=True,
        matched_rreq_timing=case.matched_rreq_timing,
    )
    pairs: list[tuple[int, int]] = []
    if case.pair_mode == "connected-multihop":
        pairs, _ = connected_multihop_pairs(
            scheduler_sim, random.Random(seed + 20_000),
            case.edge_prr_threshold, case.min_graph_hops,
            case.max_graph_hops, case.pair_count,
        )
        if len(pairs) != case.pair_count:
            raise ValueError(
                f"seed {seed}: selected {len(pairs)} of {case.pair_count} pairs"
            )
    elif case.pair_mode != "random":
        raise ValueError(f"unknown pair_mode: {case.pair_mode}")
    schedule_sr_traffic(
        scheduler_sim, case, pairs, random.Random(seed + 10_000)
    )
    trace = [
        (when, *data) for when, _, kind, data in sorted(scheduler_sim.events)
        if kind == "app_send"
    ]
    return run_trace(case, seed, nodes, trace)


def artifact_paths(prefix: Path) -> dict[str, Path]:
    return {
        "trace": Path(f"{prefix}.trace.jsonl"),
        "targets": Path(f"{prefix}.targets.jsonl"),
        "branches": Path(f"{prefix}.branches.jsonl"),
        "manifest": Path(f"{prefix}.manifest.json"),
    }


def source_hashes() -> dict[str, str]:
    files = (
        ROOT / "lora_mesh_sim.py",
        ROOT / "tools" / "run_fair_multihop_probe.py",
        ROOT / "tools" / "run_sr_experiment.py",
        ROOT / "tools" / "diagnose_source_branches.py",
        ROOT / "docs" / "research" / "meshecho_source_branch_diagnostic_design.md",
        ROOT / "tests" / "test_source_branches.py",
    )
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files
    }


def _validate_result(result: dict[str, Any]) -> None:
    if result["case_config_sha256"] != _hash(result["case"]):
        raise ValueError("case configuration hash mismatch")
    if result["scheduled_trace_sha256"] != _hash(result["scheduled_trace"]):
        raise ValueError("scheduled trace hash mismatch")
    targets: dict[int, dict[str, Any]] = {}
    for target in result["eligible_targets"]:
        flow_id = target["flow_id"]
        if flow_id in targets:
            raise ValueError("duplicate eligible target")
        if target["pre_app_prefix_sha256"] != _hash(target["pre_app_prefix"]):
            raise ValueError("target prefix hash mismatch")
        targets[flow_id] = target
    seen: set[tuple[int, str]] = set()
    for branch in result["branches"]:
        flow_id, arm = branch["flow_id"], branch["arm"]
        target = targets.get(flow_id)
        if target is None or arm not in ARMS or (flow_id, arm) in seen:
            raise ValueError("invalid or duplicate branch arm")
        if (branch["seed"] != result["seed"]
                or branch["pre_app_prefix_sha256"] != target["pre_app_prefix_sha256"]
                or branch["prefix_match"] is not True):
            raise ValueError("branch prefix mismatch")
        seen.add((flow_id, arm))
    if seen != {(flow_id, arm) for flow_id in targets for arm in ARMS}:
        raise ValueError("each target requires exactly four branch arms")


def write_artifacts(
    prefix: Path, results: Sequence[dict[str, Any]], split: str,
    expected_source_sha256: dict[str, str] | None = None,
) -> dict[str, Path]:
    """Persist every exposure and branch, including a seed with none."""
    if not results:
        raise ValueError("at least one seed result is required")
    if split not in {"smoke", "exploratory", "synthetic"}:
        raise ValueError(f"unknown diagnostic split: {split}")
    case = results[0]["case"]
    if any(result["case"] != case for result in results):
        raise ValueError("mixed case configurations")
    seeds = [result["seed"] for result in results]
    if len(seeds) != len(set(seeds)):
        raise ValueError("duplicate seed")
    if split in {"smoke", "exploratory"}:
        if case != asdict(SR_CASES["recurring_fading"]):
            raise ValueError("split requires the frozen recurring_fading case")
        if split == "smoke" and seeds != [34000]:
            raise ValueError("smoke requires exact smoke seed 34000")
        if split == "exploratory" and seeds != list(range(34001, 34006)):
            raise ValueError("exploratory requires exact exploratory seeds 34001--34005")
    for result in results:
        _validate_result(result)
    current_source_sha256 = source_hashes()
    if (expected_source_sha256 is not None
            and current_source_sha256 != expected_source_sha256):
        raise RuntimeError("source files changed during diagnostic run")
    paths = artifact_paths(prefix)
    for path in paths.values():
        if path.exists():
            raise FileExistsError(path)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    targets = [
        {"seed": result["seed"],
         "case_config_sha256": result["case_config_sha256"],
         "scheduled_trace_sha256": result["scheduled_trace_sha256"],
         **target}
        for result in results for target in result["eligible_targets"]
    ]
    branches = [
        {"case_config_sha256": result["case_config_sha256"],
         "scheduled_trace_sha256": result["scheduled_trace_sha256"],
         **branch}
        for result in results for branch in result["branches"]
    ]
    traces = [
        {"seed": result["seed"], "case_config_sha256": result["case_config_sha256"],
         "scheduled_trace_sha256": result["scheduled_trace_sha256"],
         "scheduled_trace": result["scheduled_trace"]}
        for result in results
    ]
    for key, records in (("trace", traces), ("targets", targets),
                         ("branches", branches)):
        with paths[key].open("x", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
                handle.write("\n")
    manifest = {
        "split": split,
        "case": case,
        "case_config_sha256": _hash(case),
        "seeds": seeds,
        "runs": [
            {"seed": result["seed"],
             "scheduled_trace_sha256": result["scheduled_trace_sha256"],
             "scheduled_applications": len(result["scheduled_trace"]),
             "eligible_targets": len(result["eligible_targets"]),
             "branch_rows": len(result["branches"])}
            for result in results
        ],
        "eligible_targets": len(targets),
        "branch_rows": len(branches),
        "arms": list(ARMS),
        "reference_policy": "meshecho-dhr-none",
        "pairing": (
            "Common random numbers keyed by seed, flow, directed link and receive "
            "attempt; FLOOD relay jitter keyed by seed, flow, relay, repair "
            "marker and relay attempt. Realized channels need not match."
        ),
        "airtime_estimates": {
            "network_window_airtime_s": "all complete packet ToA with start in [enqueue, deadline]",
            "target_flow_full_run_airtime_s": "target-flow complete packet ToA with start through run stop",
            "network_full_run_airtime_s": "all complete packet ToA with start through run stop",
        },
        "source_sha256": current_source_sha256,
        "artifact_sha256": {
            key: hashlib.sha256(paths[key].read_bytes()).hexdigest()
            for key in ("trace", "targets", "branches")
        },
    }
    with paths["manifest"].open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    return paths


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", choices=("smoke", "exploratory"), required=True)
    parser.add_argument("--out-prefix", type=Path, required=True)
    args = parser.parse_args(argv)
    args.seeds = (
        (34000,) if args.split == "smoke" else tuple(range(34001, 34006))
    )
    return args


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    frozen_source_sha256 = source_hashes()
    results = []
    for seed in args.seeds:
        results.append(run_seed(SR_CASES["recurring_fading"], seed))
        if source_hashes() != frozen_source_sha256:
            raise RuntimeError("source files changed during diagnostic run")
    paths = write_artifacts(
        args.out_prefix, results, args.split,
        expected_source_sha256=frozen_source_sha256,
    )
    print(json.dumps({
        "seeds": args.seeds,
        "eligible_targets": sum(len(result["eligible_targets"]) for result in results),
        "branch_rows": sum(len(result["branches"]) for result in results),
        "manifest": str(paths["manifest"]),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
