#!/usr/bin/env python3
"""Matched, target-only D/R/F interventions at old DCB D decisions.

This tool is deliberately separate from the production protocol and from the
older four-arm source-branch diagnostic.  It records the reference prefix
before a D decision, then replays only that target with a forced action.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import defaultdict
from dataclasses import asdict, is_dataclass, replace
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import BROADCAST_DST, MeshEchoDCB, Node, generate_nodes
from tools.run_fair_multihop_probe import connected_multihop_pairs, make_args, make_radio
from tools.run_sr_experiment import (
    RecordingSimulator, SR_CASES, SrCase, schedule_sr_traffic,
)

def _normal(value: Any) -> Any:
    if is_dataclass(value):
        if type(value).__name__ == "PendingSend":
            return {
                "type": "PendingSend",
                "canceled": bool(value.canceled),
                "committed": bool(value.committed),
                "has_guard": value.can_start_at is not None,
            }
        return _normal(asdict(value))
    if callable(value):
        return {"callable": getattr(value, "__qualname__", type(value).__name__)}
    if isinstance(value, dict):
        return {str(k): _normal(v) for k, v in sorted(value.items(), key=lambda x: str(x[0]))}
    if isinstance(value, (list, tuple)):
        return [_normal(v) for v in value]
    if isinstance(value, set):
        return sorted(_normal(v) for v in value)
    return value


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(_normal(value), sort_keys=True, separators=(",", ":")).encode("ascii")
    ).hexdigest()


class _KeyedStream:
    def __init__(self, original: Any, seed: int) -> None:
        self.original = original
        self.seed = seed
        self.key: tuple[Any, ...] | None = None

    def random(self) -> float:
        if self.key is None:
            return self.original.random()
        value = json.dumps((self.seed, *self.key), separators=(",", ":"))
        return int.from_bytes(hashlib.sha256(value.encode("ascii")).digest()[:8], "big") / 2**64

    def __getattr__(self, name: str) -> Any:
        return getattr(self.original, name)


def _rx_role(packet: Any) -> str:
    if packet.kind in {"RREQ", "RREP"}:
        return "discovery"
    if packet.kind == "ACK":
        return "ack"
    if packet.repair_index is not None:
        return "rescue"
    return "useful"


class MatchedSimulator(RecordingSimulator):
    """Recording simulator with role-separated common-random-number draws."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.reception_ordinals: dict[tuple[Any, ...], int] = defaultdict(int)
        self.reception_stream = _KeyedStream(self.channel_random, self.seed)
        self.channel_random = self.reception_stream
        self.protocol_stream = _KeyedStream(self.random, self.seed)
        self.random = self.protocol_stream
        self._flood_jitter_key: tuple[Any, ...] | None = None
        self.app_event_order: dict[int, int] = {}
        self.tx_requests: list[dict[str, Any]] = []
        self.tx_request_outcomes: list[dict[str, Any]] = []

    def schedule(self, when: float, event_type: str, data: Any) -> None:
        super().schedule(when, event_type, data)
        if event_type == "app_send":
            self.app_event_order[data[2]] = (1, self._event_counter)
        elif event_type == "tx_request":
            sender, packet, pending = data
            self.tx_requests.append({
                "request_time": when,
                "sender": sender,
                "packet": packet,
                "pending": pending,
            })

    def begin_transmission(self, sender: int, packet: Any, pending: Any) -> None:
        before = len(self.transmissions)
        super().begin_transmission(sender, packet, pending)
        if len(self.transmissions) == before:
            self.tx_request_outcomes.append({
                "request_time": self.now,
                "sender": sender,
                "packet": packet,
                "started": False,
                "reason": (
                    "canceled" if pending.canceled
                    else "pending_start_guard_rejected"
                    if pending.can_start_at is not None
                    else "not_started"
                ),
                "pending": pending,
            })

    def try_receive(self, tx: Any, receiver: int) -> Any:
        if receiver == tx.sender:
            return super().try_receive(tx, receiver)
        role = _rx_role(tx.packet)
        key = (tx.packet.flow_id, role, tx.sender, receiver)
        self.reception_ordinals[key] += 1
        self.reception_stream.key = (*key, self.reception_ordinals[key])
        try:
            return super().try_receive(tx, receiver)
        finally:
            self.reception_stream.key = None


class MatchedDCBProtocol(MeshEchoDCB):
    """DCB protocol with one target-only source action override."""

    def __init__(self, *args: Any, target_flow_id: int | None = None,
                 arm: str | None = None, **kwargs: Any) -> None:
        super().__init__(*args, relay_mode="conditional", source_mode="sr", **kwargs)
        if arm not in {None, "D", "R", "F"}:
            raise ValueError(f"unknown matched arm: {arm}")
        self.target_flow_id = target_flow_id
        self.arm = arm
        self.eligible_targets: list[dict[str, Any]] = []
        self.target_prefix: dict[str, Any] | None = None
        self.target_ledger_after: dict[str, Any] | None = None
        self._delay_packet: Any | None = None
        self._jitter_ordinals: dict[tuple[Any, ...], int] = defaultdict(int)
        self.source_action_overrides = (
            {target_flow_id: arm}
            if target_flow_id is not None and arm in {"R", "F"}
            else {}
        )
        self.equalize_forced_discovery = target_flow_id is not None

    def _prefix(self, src: int, dst: int, flow_id: int) -> dict[str, Any]:
        state = self.destination_state.get((src, dst))
        entry = self.route_cache.get(src, {}).get(dst)
        def event_data(data: Any) -> Any:
            if callable(data):
                closure = []
                for cell in (getattr(data, "__closure__", None) or ()):
                    try:
                        value = cell.cell_contents
                    except ValueError:
                        value = "<empty-cell>"
                    if value is self or value is self.sim:
                        value = {"type": type(value).__name__}
                    closure.append(_normal(value))
                return {
                    "callable": getattr(data, "__qualname__", type(data).__name__),
                    "closure": closure,
                }
            if isinstance(data, tuple):
                return [_normal(item) for item in data]
            return _normal(data)

        queued_events = [
            {"when": when, "order": order, "type": event_type,
             "data": event_data(data)}
            for when, order, event_type, data in sorted(self.sim.events)
        ]
        protocol_state = {
            "pending_data": _normal(self.pending_data),
            "flow_actions": _normal(self.flow_actions),
            "flow_data_actions": _normal(self.flow_data_actions),
            "flow_sent_paths": _normal(self.flow_sent_paths),
            "feedback_windows": _normal(self.feedback_windows),
            "relay_pending": _normal(self.relay_pending),
            "active_nominations": _normal(self.active_nominations),
            "active_flows": _normal(self.active_flows),
            "seen_floods": _normal(self.seen_floods),
            "route_cache": _normal(self.route_cache),
            "rreq_candidates": _normal(getattr(self, "rreq_candidates", {})),
            "pending_fallback": _normal(getattr(self, "pending_fallback", {})),
            "source_fallbacks": _normal(getattr(self, "source_fallbacks", {})),
            "source_expired_discoveries": _normal(
                getattr(self, "source_expired_discoveries", {})
            ),
        }
        metrics = {
            key: getattr(self.sim.metrics, key)
            for key in (
                "tx_count", "data_tx", "control_tx", "ack_tx", "rx_success",
                "rx_fail", "collision_fail", "route_requests", "route_replies",
                "route_discovery_attempts", "route_discovery_successes",
                "route_cache_hits", "route_cache_misses",
            )
        }
        rng_state = {
            "sim": _normal(self.sim.random.original.getstate()
                            if isinstance(self.sim.random, _KeyedStream)
                            else self.sim.random.getstate()),
            "channel": _normal(self.sim.channel_random.original.getstate()
                                if isinstance(self.sim.channel_random, _KeyedStream)
                                else self.sim.channel_random.getstate()),
        }
        return {
            "event": {
                "time": self.sim.now,
                "flow_id": flow_id,
                "tie_order": self.sim.app_event_order.get(flow_id),
            },
            "source": {
                "src": src,
                "dst": dst,
                "state": _normal(asdict(state)) if state is not None else None,
                "route": _normal(asdict(entry)) if entry is not None else None,
                "source_tokens": self.source_tokens[src],
                "source_app_count": self.source_app_counts[src],
            },
            "flows": _normal([asdict(item) for _, item in sorted(self.sim.metrics.flows.items())]),
            "actions": _normal(self.action_events),
            "protocol_state": protocol_state,
            "events": queued_events,
            "metrics": metrics,
            "rng_state": rng_state,
            "event_counter": self.sim._event_counter,
            "tx_counter": self.sim._tx_counter,
            "nodes": {
                node_id: {"x": node.x, "y": node.y,
                          "tx_available_at": node.tx_available_at,
                          "can_relay": node.can_relay}
                for node_id, node in sorted(self.sim.nodes.items())
            },
            "radio": _normal(asdict(self.sim.radio)),
            "shadowing": _normal(self.sim.link_shadowing_db),
            "transmissions": _normal(self.sim.transmissions),
            "tx_prefix": [
                {"tx_id": tx.tx_id, "sender": tx.sender,
                 "start": tx.start, "end": tx.end,
                 "packet": _normal(asdict(tx.packet))}
                for tx in self.sim.tx_history
            ],
        }

    def _old_d_candidate(self, src: int, dst: int) -> tuple[bool, str, Any]:
        state = self.destination_state.get((src, dst))
        entry = self.route_cache.get(src, {}).get(dst) if dst != BROADCAST_DST else None
        if entry is not None and entry.expires_at <= self.sim.now:
            entry = None
        if state is None:
            return False, "none", entry
        recent_sends = sum(when >= self.sim.now - 300.0 for when in state.send_times)
        eligible = (
            state.pending_discovery_flow is None
            and self.source_tokens[src] > 0
            and (state.last_discovery_at is None
                 or self.sim.now - state.last_discovery_at >= 300.0)
        )
        if entry is None:
            is_d = (
                dst != BROADCAST_DST and state.consecutive_f_misses >= 2
                and recent_sends >= 2 and eligible
            )
            return is_d, "cold" if is_d else "none", entry
        is_d = (
            state.consecutive_r_misses < 2
            and self.sim.now - entry.created_at >= 180.0
            and recent_sends >= 2 and eligible
            and not state.had_r_miss_since_commit
        )
        return is_d, "aging" if is_d else "none", entry

    def send_app(self, src: int, dst: int, flow_id: int) -> None:
        is_d, trigger_kind, entry = self._old_d_candidate(src, dst)
        prefix = self._prefix(src, dst, flow_id) if is_d else None
        if flow_id == self.target_flow_id:
            self.target_prefix = prefix
        super().send_app(src, dst, flow_id)
        if flow_id == self.target_flow_id:
            state_after = self.destination_state.get((src, dst))
            self.target_ledger_after = {
                "source_tokens": self.source_tokens[src],
                "last_discovery_at": (
                    state_after.last_discovery_at if state_after is not None else None
                ),
                "time": self.sim.now,
            }
        if is_d and self.arm is None:
            self.eligible_targets.append({
                "flow_id": flow_id,
                "src": src,
                "dst": dst,
                "enqueued_at": self.sim.now,
                "route_path": entry.path if entry is not None else (),
                "route_hops": len(entry.path) - 1 if entry is not None else None,
                "route_age_s": self.sim.now - entry.created_at if entry is not None else None,
                "d_trigger_kind": trigger_kind,
                "pre_app_prefix": prefix,
                "pre_app_prefix_sha256": _hash(prefix),
                "allowed_arms": ["D", "R", "F"] if entry is not None else ["D", "F"],
            })

    def expire_data_ack(self, flow_id: int) -> None:
        if flow_id == self.target_flow_id:
            previous = self.rescue_mode
            self.rescue_mode = "none"
            try:
                super().expire_data_ack(flow_id)
            finally:
                self.rescue_mode = previous
            return
        super().expire_data_ack(flow_id)

    def flood_delay(self, receiver: int | None = None,
                    rx: Any | None = None) -> float:
        if receiver is None:
            return super().flood_delay(receiver, rx)
        packet = self._delay_packet
        if packet is None:
            return super().flood_delay(receiver, rx)
        base_key = (packet.flow_id, "jitter", _rx_role(packet),
                    receiver, packet.repair_index)
        self._jitter_ordinals[base_key] += 1
        key = (*base_key, self._jitter_ordinals[base_key])
        self._flood_jitter_key = key
        self.sim.protocol_stream.key = key
        try:
            return super().flood_delay(receiver, rx)
        finally:
            self.sim.protocol_stream.key = None
            self._flood_jitter_key = None

    def on_rreq(self, receiver: int, packet: Any, rx: Any) -> None:
        previous = self._delay_packet
        self._delay_packet = packet
        try:
            super().on_rreq(receiver, packet, rx)
        finally:
            self._delay_packet = previous

    def on_fallback(self, receiver: int, packet: Any, rx: Any) -> None:
        previous = self._delay_packet
        self._delay_packet = packet
        try:
            super().on_fallback(receiver, packet, rx)
        finally:
            self._delay_packet = previous


def _protocol(case: SrCase, target_flow_id: int | None, arm: str | None) -> MatchedDCBProtocol:
    args = make_args(case)
    args.sr_app_deadline_s = 30.0
    return MatchedDCBProtocol(
        target_flow_id=target_flow_id,
        arm=arm,
        route_ttl_s=getattr(args, "calm_route_ttl_s", 600.0),
        discovery_window_s=getattr(args, "calm_discovery_window_s", 2.0),
        app_deadline_s=args.sr_app_deadline_s,
        ack_guard_s=getattr(args, "sr_ack_guard_s", 15.0),
        rrep_wait_s=getattr(args, "sr_rrep_wait_s", 10.0),
    )


def _replay(case: SrCase, seed: int, nodes: Sequence[Node], trace: Sequence[tuple[float, int, int, int]],
            target_flow_id: int | None, arm: str | None,
            simulator_cls: type[MatchedSimulator] = MatchedSimulator,
            ) -> tuple[MatchedSimulator, MatchedDCBProtocol]:
    protocol = _protocol(case, target_flow_id, arm)
    sim = simulator_cls(
        [replace(node) for node in nodes], make_radio(make_args(case)), protocol,
        seed=seed, max_hops=case.max_hops, independent_random_streams=True,
        matched_rreq_timing=case.matched_rreq_timing,
    )
    for when, src, dst, flow_id in trace:
        sim.schedule(when, "app_send", (src, dst, flow_id))
    sim.run(case.duration_s + 30.0)
    return sim, protocol


def run_trace(case: SrCase, seed: int, nodes: Sequence[Node],
              scheduled_trace: Sequence[tuple[float, int, int, int]],
              *, cold_target: bool = False,
              simulator_cls: type[MatchedSimulator] = MatchedSimulator,
              ) -> dict[str, Any]:
    trace = sorted(scheduled_trace, key=lambda item: item[0])
    reference, reference_protocol = _replay(
        case, seed, nodes, trace, None, None, simulator_cls,
    )
    targets = [
        target for target in reference_protocol.eligible_targets
        if not cold_target or target["d_trigger_kind"] == "cold"
    ]
    branches: list[dict[str, Any]] = []
    for target in targets:
        for arm in target["allowed_arms"]:
            sim, protocol = _replay(
                case, seed, nodes, trace, target["flow_id"], arm, simulator_cls,
            )
            prefix = protocol.target_prefix
            if prefix != target["pre_app_prefix"]:
                raise ValueError(
                    f"seed {seed} flow {target['flow_id']} arm {arm}: prefix mismatch"
                )
            deadline = target["enqueued_at"] + 30.0
            full_tx = [tx for tx in sim.tx_history if tx.start <= case.duration_s + 30.0]
            window_tx = [tx for tx in full_tx
                         if target["enqueued_at"] <= tx.start <= deadline]
            source_tx = [tx for tx in full_tx
                         if tx.sender == target["src"]
                         and tx.packet.flow_id == target["flow_id"]
                         and tx.packet.kind in {"DATA", "FLOOD"}]
            initial = next((tx for tx in source_tx if tx.packet.repair_index is None), None)
            flow = sim.metrics.flows[target["flow_id"]]
            state = protocol.destination_state[(target["src"], target["dst"])]
            branches.append({
                "seed": seed,
                "flow_id": target["flow_id"],
                "arm": arm,
                "prefix_match": True,
                "pre_app_prefix_sha256": _hash(prefix),
                "discovery_ledger_equalized": (
                    protocol.target_ledger_after is not None
                    and protocol.target_ledger_after["source_tokens"] == (
                        target["pre_app_prefix"]["source"]["source_tokens"] - 1
                    )
                    and protocol.target_ledger_after["last_discovery_at"] == target["enqueued_at"]
                ),
                "target_ledger_after": protocol.target_ledger_after,
                "source_action": protocol.flow_actions.get(target["flow_id"]),
                "data_action": protocol.flow_data_actions.get(target["flow_id"]),
                "initial_source_kind": initial.packet.kind if initial else None,
                "initial_source_start_at": initial.start if initial else None,
                "ack_by_deadline": flow.acked_at is not None and flow.acked_at <= deadline,
                "delivery_by_deadline": flow.delivered_at is not None and flow.delivered_at <= deadline,
                "accepted_ack_at": flow.acked_at,
                "first_delivery_at": flow.delivered_at,
                "network_window_airtime_s": sum(tx.end - tx.start for tx in window_tx),
                "network_full_run_airtime_s": sum(tx.end - tx.start for tx in full_tx),
                "target_flow_full_run_airtime_s": sum(
                    tx.end - tx.start for tx in full_tx
                    if tx.packet.flow_id == target["flow_id"]
                ),
                "window_tx_count": len(window_tx),
                "window_rreq_tx": sum(tx.packet.kind == "RREQ" for tx in window_tx),
                "window_rrep_tx": sum(tx.packet.kind == "RREP" for tx in window_tx),
                "raw_physical_tx": [
                    {"tx_id": tx.tx_id, "sender": tx.sender,
                     "start": tx.start, "end": tx.end,
                     "packet": _normal(asdict(tx.packet))}
                    for tx in sim.tx_history
                ],
                "action_events": _normal(protocol.action_events),
                "flow_record": _normal(asdict(flow)),
                "metrics": _normal({
                    "tx_count": sim.metrics.tx_count,
                    "data_tx": sim.metrics.data_tx,
                    "control_tx": sim.metrics.control_tx,
                    "ack_tx": sim.metrics.ack_tx,
                    "tx_energy_j": sim.metrics.tx_energy_j,
                    "rx_energy_j": sim.metrics.rx_energy_j,
                    "rx_success": sim.metrics.rx_success,
                    "rx_fail": sim.metrics.rx_fail,
                    "collision_fail": sim.metrics.collision_fail,
                }),
            })
    return {
        "case": asdict(case),
        "seed": seed,
        "scheduled_trace": trace,
        "scheduled_trace_sha256": _hash(trace),
        "eligible_targets": targets,
        "branches": branches,
        "source_sha256": source_hashes(),
    }


def run_seed(case: SrCase, seed: int) -> dict[str, Any]:
    nodes = generate_nodes(
        case.nodes, case.area_m, random.Random(seed), repeater_ratio=0.0,
    )
    scheduler = MatchedSimulator(
        [replace(node) for node in nodes], make_radio(make_args(case)),
        _protocol(case, None, None), seed=seed, max_hops=case.max_hops,
        independent_random_streams=True, matched_rreq_timing=case.matched_rreq_timing,
    )
    pairs: list[tuple[int, int]] = []
    if case.pair_mode == "connected-multihop":
        pairs, _ = connected_multihop_pairs(
            scheduler, random.Random(seed + 20_000), case.edge_prr_threshold,
            case.min_graph_hops, case.max_graph_hops, case.pair_count,
        )
        if len(pairs) != case.pair_count:
            raise ValueError(f"seed {seed}: insufficient connected pairs")
    schedule_sr_traffic(scheduler, case, pairs, random.Random(seed + 10_000))
    trace = [
        (when, *data) for when, _, kind, data in sorted(scheduler.events)
        if kind == "app_send"
    ]
    return run_trace(case, seed, nodes, trace)


SMOKE_SEEDS = (49400,)
EXPLORATORY_SEEDS = tuple(range(49401, 49441))
SOURCE_FILES = (
    ROOT / "lora_mesh_sim.py",
    ROOT / "tools" / "run_fair_multihop_probe.py",
    ROOT / "tools" / "run_sr_experiment.py",
    ROOT / "tools" / "diagnose_matched_d_trigger.py",
    ROOT / "docs" / "research" / "meshecho_d_trigger_matched_branch_design.md",
    ROOT / "tests" / "test_matched_d_trigger.py",
    ROOT / "tests" / "test_matched_d_trigger_branches.py",
)


def source_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in SOURCE_FILES
    }


def artifact_paths(prefix: Path) -> dict[str, Path]:
    return {
        "targets": Path(f"{prefix}.targets.jsonl"),
        "branches": Path(f"{prefix}.branches.jsonl"),
        "evidence": Path(f"{prefix}.evidence.jsonl"),
        "traces": Path(f"{prefix}.traces.jsonl"),
        "manifest": Path(f"{prefix}.manifest.json"),
    }


def _validate_result(result: dict[str, Any]) -> None:
    if result["scheduled_trace_sha256"] != _hash(result["scheduled_trace"]):
        raise ValueError("scheduled trace hash mismatch")
    targets = {target["flow_id"]: target for target in result["eligible_targets"]}
    if len(targets) != len(result["eligible_targets"]):
        raise ValueError("duplicate target flow")
    seen: set[tuple[int, str]] = set()
    for target in result["eligible_targets"]:
        if target["pre_app_prefix_sha256"] != _hash(target["pre_app_prefix"]):
            raise ValueError("target prefix hash mismatch")
        if target["allowed_arms"] not in (["D", "F"], ["D", "R", "F"]):
            raise ValueError("invalid target arm set")
    for row in result["branches"]:
        key = (row["flow_id"], row["arm"])
        target = targets.get(row["flow_id"])
        if target is None or row["arm"] not in target["allowed_arms"] or key in seen:
            raise ValueError("invalid or duplicate branch arm")
        if (row["prefix_match"] is not True
                or row["pre_app_prefix_sha256"] != target["pre_app_prefix_sha256"]
                or row["discovery_ledger_equalized"] is not True
                or not isinstance(row.get("target_ledger_after"), dict)
                or row["target_ledger_after"].get("time") != target["enqueued_at"]):
            raise ValueError("branch provenance or ledger mismatch")
        expected_kinds = (
            {"FLOOD"} if row["arm"] == "F" else
            {"DATA", "FLOOD"} if row["arm"] == "D" else
            {"DATA"}
        )
        if row["initial_source_kind"] not in expected_kinds | {None}:
            raise ValueError("initial source packet does not match arm")
        if not isinstance(row.get("raw_physical_tx"), list):
            raise ValueError("raw physical TX evidence missing")
        if not isinstance(row.get("action_events"), list):
            raise ValueError("action evidence missing")
        if not isinstance(row.get("flow_record"), dict):
            raise ValueError("flow evidence missing")
        seen.add(key)
    expected = {(flow_id, arm) for flow_id, target in targets.items()
                for arm in target["allowed_arms"]}
    if seen != expected:
        raise ValueError("each target requires every allowed arm")


def write_artifacts(
    prefix: Path, results: Sequence[dict[str, Any]], split: str,
    expected_source_sha256: dict[str, str] | None = None,
) -> dict[str, Path]:
    if split not in {"smoke", "exploratory"}:
        raise ValueError(f"unknown split: {split}")
    if not results:
        raise ValueError("at least one result is required")
    case = results[0]["case"]
    if any(result["case"] != case for result in results):
        raise ValueError("mixed case configurations")
    seeds = [result["seed"] for result in results]
    expected_seeds = list(SMOKE_SEEDS if split == "smoke" else EXPLORATORY_SEEDS)
    if seeds != expected_seeds:
        raise ValueError("exact matched-D seed cohort required")
    for result in results:
        _validate_result(result)
    current_hashes = source_hashes()
    if expected_source_sha256 is not None and current_hashes != expected_source_sha256:
        raise RuntimeError("source files changed during matched-D run")
    paths = artifact_paths(prefix)
    if any(path.exists() for path in paths.values()):
        raise FileExistsError(str(prefix))
    prefix.parent.mkdir(parents=True, exist_ok=True)
    targets = [
        {"seed": result["seed"], "scheduled_trace_sha256": result["scheduled_trace_sha256"], **target}
        for result in results for target in result["eligible_targets"]
    ]
    branches = [
        {"seed": result["seed"], "scheduled_trace_sha256": result["scheduled_trace_sha256"], **row}
        for result in results for row in result["branches"]
    ]
    evidence = [
        {"seed": result["seed"], "flow_id": row["flow_id"], "arm": row["arm"],
         "raw_physical_tx": row["raw_physical_tx"],
         "action_events": row["action_events"],
         "flow_record": row["flow_record"], "metrics": row["metrics"]}
        for result in results for row in result["branches"]
    ]
    traces = [
        {"seed": result["seed"], "scheduled_trace_sha256": result["scheduled_trace_sha256"],
         "scheduled_trace": result["scheduled_trace"]}
        for result in results
    ]
    for key, records in (("targets", targets), ("branches", branches),
                         ("evidence", evidence), ("traces", traces)):
        with paths[key].open("x", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(_normal(record), sort_keys=True, separators=(",", ":")) + "\n")
    manifest = {
        "split": split,
        "case": case,
        "case_sha256": _hash(case),
        "seeds": seeds,
        "reference_policy": "meshecho-dcb",
        "arms": ["D", "R", "F"],
        "target_count": len(targets),
        "branch_count": len(branches),
        "evidence_count": len(evidence),
        "pairing": "role-keyed reception: discovery/useful/ack/rescue; initial useful excludes packet kind",
        "source_sha256": current_hashes,
        "artifact_sha256": {
            key: hashlib.sha256(paths[key].read_bytes()).hexdigest()
            for key in ("targets", "branches", "evidence", "traces")
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
    args.seeds = SMOKE_SEEDS if args.split == "smoke" else EXPLORATORY_SEEDS
    return args


if __name__ == "__main__":
    args = parse_args()
    frozen = source_hashes()
    results = []
    for seed in args.seeds:
        results.append(run_seed(SR_CASES["recurring_fading"], seed))
        if source_hashes() != frozen:
            raise RuntimeError("source files changed during matched-D run")
    paths = write_artifacts(
        Path(args.out_prefix), results, args.split,
        expected_source_sha256=frozen,
    )
    print(json.dumps({
        "seeds": list(args.seeds),
        "targets": sum(len(result["eligible_targets"]) for result in results),
        "branches": sum(len(result["branches"]) for result in results),
        "manifest": str(paths["manifest"]),
    }, sort_keys=True))
