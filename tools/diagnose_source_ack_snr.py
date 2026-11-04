#!/usr/bin/env python3
"""Passive source-side ACK measurements for MeshEcho-SR research."""

from __future__ import annotations

import hashlib
from dataclasses import asdict
from typing import Any

from lora_mesh_sim import RxInfo, Transmission, clamp, required_snr_db
from tools import run_sr_experiment as sr
from tools.diagnose_delayed_ack_rx import capture_run, require_stock_parity
from tools.run_sr_experiment import RecordingSimulator


PROTOCOL = "meshecho-dhr-flood-ack-delay"
_RUNNER_AUTHORIZATION = object()


class PassiveSourceAckSimulator(RecordingSimulator):
    """Retain source ACK decodes from the simulator's single receive attempt."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.source_ack_rxinfo: dict[tuple[int, int], RxInfo] = {}

    def try_receive(self, tx: Transmission, receiver: int) -> RxInfo | None:
        rx = super().try_receive(tx, receiver)
        if (rx is not None and tx.packet.kind == "ACK"
                and receiver == tx.packet.final_dst):
            self.source_ack_rxinfo[(tx.tx_id, receiver)] = rx
        return rx


def join_source_ack_actions(sim: PassiveSourceAckSimulator) -> list[dict[str, Any]]:
    """Join each decoded source ACK to exactly one protocol acceptance event."""

    tx_by_id = {tx.tx_id: tx for tx in sim.tx_history}
    actions = {
        order: action for order, action in enumerate(sim.protocol.action_events)
        if action["event"] == "dhr_source_ack_rx"
    }
    matched_actions: set[int] = set()
    rows = []
    for (tx_id, receiver), rx in sorted(sim.source_ack_rxinfo.items()):
        tx = tx_by_id.get(tx_id)
        if tx is None:
            raise ValueError(f"source ACK TX {tx_id} is missing")
        packet = tx.packet
        candidates = [
            order for order, action in actions.items()
            if abs(action["time"] - tx.end) <= 1e-7
            and action["flow_id"] == packet.flow_id
            and action["src"] == receiver
            and action["dst"] == packet.origin
            and action["repair_index"] == packet.repair_index
        ]
        if len(candidates) != 1 or candidates[0] in matched_actions:
            raise ValueError(f"source ACK TX {tx_id} has no unique action")
        action_order = candidates[0]
        matched_actions.add(action_order)
        accepted = actions[action_order]["accepted"]
        if accepted and not (
            packet.path_index == 0
            and len(packet.path) >= 2
            and packet.path[0] == receiver
            and packet.path[-1] == packet.origin
            and tx.sender == packet.path[1]
            and rx.sender == tx.sender
            and packet.request_id == packet.flow_id
            and packet.protocol == sim.protocol.name
        ):
            raise ValueError(f"accepted source ACK TX {tx_id} has invalid path")
        rows.append({
            "tx_id": tx_id,
            "tx_end_s": tx.end,
            "flow_id": packet.flow_id,
            "source": receiver,
            "destination": packet.origin,
            "sender": tx.sender,
            "path": list(packet.path),
            "path_index": packet.path_index,
            "repair_index": packet.repair_index,
            "snr_db": rx.snr_db,
            "sinr_db": rx.sinr_db,
            "collided": rx.collided,
            "accepted": accepted,
            "action_order": action_order,
        })
    if len(matched_actions) != len(actions):
        raise ValueError("a source ACK action has no physical decode")
    return rows


def build_initial_r_cohort(
    sim: PassiveSourceAckSimulator, ack_rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Build initial-R decision features and separately observed outcomes."""

    rows: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
    actions = sim.protocol.action_events
    decision_flow_ids = [action["flow_id"] for action in actions
                         if action["event"] == "decision"]
    if len(decision_flow_ids) != len(set(decision_flow_ids)):
        raise ValueError("duplicate initial decision for one flow")
    origin_decisions = {
        action["flow_id"]: (order, action)
        for order, action in enumerate(actions) if action["event"] == "decision"
    }
    for decision_order, decision in enumerate(actions):
        if decision["event"] != "decision" or decision["action"] != "R":
            continue
        flow_id = decision["flow_id"]
        source, destination = decision["src"], decision["dst"]
        flow = sim.metrics.flows.get(flow_id)
        if flow is None:
            exclusions.append({"flow_id": flow_id, "reason": "unregistered_flow"})
            continue
        deadline_s = flow.created_at + sim.protocol.app_deadline_s
        starts = [
            tx for tx in sim.tx_history
            if tx.packet.kind == "DATA"
            and tx.packet.repair_index is None
            and tx.packet.flow_id == flow_id
            and tx.packet.origin == source
            and tx.packet.final_dst == destination
            and tx.sender == source
            and tx.start < deadline_s
        ]
        if len(starts) != 1:
            exclusions.append({
                "flow_id": flow_id,
                "reason": "missing_initial_r_start" if not starts
                else "nonunique_initial_r_start",
            })
            continue
        initial_tx = starts[0]
        commits = [
            (order, action) for order, action in enumerate(actions[:decision_order])
            if action["event"] == "commit"
            and action["src"] == source and action["dst"] == destination
        ]
        generation_order, commit = commits[-1] if commits else (None, None)
        path = tuple(initial_tx.packet.path)
        intervening_commit = any(
            action["event"] == "commit"
            and action["src"] == source and action["dst"] == destination
            and decision_order < order and action["time"] <= initial_tx.start
            for order, action in enumerate(actions)
        )
        feature_exclusion_reason = (
            "no_prior_commit" if commit is None else
            "path_changed_before_tx" if path != tuple(commit["path"]) else
            "route_commit_before_tx" if intervening_commit else None
        )

        def belongs_to_generation(ack: dict[str, Any]) -> bool:
            if commit is None or generation_order is None:
                return False
            if (ack["flow_id"] == commit["flow_id"]
                    and abs(ack["tx_end_s"] - commit["time"]) <= 1e-7):
                return True
            origin = origin_decisions.get(ack["flow_id"])
            return bool(
                origin is not None
                and generation_order < origin[0] < ack["action_order"]
                and origin[1]["action"] == "R"
                and origin[1]["src"] == source
                and origin[1]["dst"] == destination
            )

        prior_ack_candidates = [
            ack for ack in ack_rows
            if feature_exclusion_reason is None
            and ack["accepted"]
            and belongs_to_generation(ack)
            and generation_order < ack["action_order"] < decision_order
            and ack["tx_end_s"] < decision["time"]
            and ack["source"] == source and ack["destination"] == destination
            and tuple(ack["path"]) == path
            and ack["sender"] == path[1]
        ]
        prior_ack = max(
            prior_ack_candidates,
            key=lambda ack: (ack["tx_end_s"], ack["action_order"]),
            default=None,
        )
        if feature_exclusion_reason is None and prior_ack is None:
            feature_exclusion_reason = "no_accepted_same_generation_ack"
        previous_r = [
            action for action in actions[
                (generation_order + 1) if generation_order is not None
                else decision_order:decision_order
            ]
            if action["event"] == "decision" and action["action"] == "R"
            and action["src"] == source and action["dst"] == destination
        ]
        prior_r_miss = False
        if previous_r:
            previous_flow_id = previous_r[-1]["flow_id"]
            timed_out = any(
                action["event"] == "timeout"
                and action["flow_id"] == previous_flow_id
                for action in actions[generation_order + 1:decision_order]
            )
            later_ack = any(
                ack["accepted"] and ack["repair_index"] is None
                and ack["flow_id"] == previous_flow_id
                and ack["action_order"] < decision_order
                for ack in ack_rows
            )
            prior_r_miss = timed_out and not later_ack
        guard_end_s = min(initial_tx.start + 15.0, deadline_s)
        initial_r_ack_by_guard = any(
            ack["accepted"] and ack["repair_index"] is None
            and ack["flow_id"] == flow_id
            and ack["source"] == source and ack["destination"] == destination
            and tuple(ack["path"]) == path
            and ack["tx_end_s"] <= guard_end_s
            for ack in ack_rows
        )
        recovery_actions = [
            action for action in actions
            if action["event"] == "dhr_recovery_tx"
            and action["flow_id"] == flow_id
            and action["src"] == source and action["dst"] == destination
            and initial_tx.start < action["time"] < deadline_s
        ]
        recovery_txs = [
            tx for tx in sim.tx_history
            if tx.packet.flow_id == flow_id
            and tx.packet.origin == source and tx.packet.final_dst == destination
            and tx.packet.request_id == flow_id
            and tx.sender == source
            and (tx.packet.kind, tx.packet.repair_index) in {
                ("DATA", 1), ("FLOOD", 2),
            }
            and initial_tx.start < tx.start < deadline_s
        ]
        matched_recovery_tx_ids: set[int] = set()
        for action in recovery_actions:
            matches = [
                tx for tx in recovery_txs
                if abs(tx.start - action["time"]) <= 1e-7
                and abs(tx.end - action["end"]) <= 1e-7
                and tx.packet.repair_index == action["repair_index"]
                and action["action"] == (
                    "R" if tx.packet.repair_index == 1 else "F"
                )
            ]
            if len(matches) != 1 or matches[0].tx_id in matched_recovery_tx_ids:
                raise ValueError(f"recovery action for flow {flow_id} has no unique physical TX")
            matched_recovery_tx_ids.add(matches[0].tx_id)
        if matched_recovery_tx_ids != {tx.tx_id for tx in recovery_txs}:
            raise ValueError(f"recovery physical TX for flow {flow_id} has no unique action")
        recovery_markers = {tx.packet.repair_index for tx in recovery_txs}
        later_recovery_ack_by_deadline = any(
            ack["accepted"] and ack["repair_index"] in recovery_markers
            and ack["flow_id"] == flow_id
            and ack["source"] == source and ack["destination"] == destination
            and ack["tx_end_s"] <= deadline_s
            and any(tx.packet.repair_index == ack["repair_index"]
                    and tx.start < ack["tx_end_s"] for tx in recovery_txs)
            for ack in ack_rows
        )
        q = None if prior_ack is None else int(clamp(
            round(2 * (prior_ack["sinr_db"] - required_snr_db(sim.radio.sf))),
            -126, 126,
        ))
        rows.append({
            "flow_id": flow_id,
            "source": source,
            "destination": destination,
            "decision_order": decision_order,
            "decision_time_s": decision["time"],
            "initial_r_tx_id": initial_tx.tx_id,
            "initial_r_start_s": initial_tx.start,
            "route_generation_flow_id": commit["flow_id"] if commit else None,
            "feature_exclusion_reason": feature_exclusion_reason,
            "path": list(path),
            "path_type": "direct" if len(path) == 2 else "multihop",
            "hop_count": len(path) - 1,
            "prior_ack_tx_id": prior_ack["tx_id"] if prior_ack else None,
            "prior_ack_tx_end_s": prior_ack["tx_end_s"] if prior_ack else None,
            "prior_ack_age_s": (
                decision["time"] - prior_ack["tx_end_s"] if prior_ack else None
            ),
            "q": q,
            "q_clean": (
                int(clamp(round(2 * (
                    prior_ack["snr_db"] - required_snr_db(sim.radio.sf)
                )), -126, 126)) if prior_ack else None
            ),
            "prior_ack_collided": prior_ack["collided"] if prior_ack else None,
            "prior_r_miss": int(prior_r_miss),
            "initial_r_ack_by_guard": initial_r_ack_by_guard,
            "later_recovery_attempted": bool(recovery_txs),
            "later_recovery_ack_by_deadline": later_recovery_ack_by_deadline,
            "destination_delivery_by_deadline": (
                flow.delivered_at is not None
                and flow.delivered_at <= deadline_s
            ),
        })
    return {"rows": rows, "exclusions": exclusions}


def run_diagnostic(
    seed: int, case: sr.SrCase = sr.SR_CASES["recurring_fading"],
    deadline_s: float = 30.0,
    *, research_authorization: object | None = None,
) -> dict[str, Any]:
    """Run stock/parity and two exact passive replays before returning rows."""

    if research_authorization is not _RUNNER_AUTHORIZATION and (
        35000 <= seed <= 35099 or 36000 <= seed <= 36099
        or 42000 <= seed <= 43999
    ):
        raise ValueError("reserved research seed requires explicit authorization")
    stock, _ = capture_run(case, seed, sr.RecordingSimulator, deadline_s)
    observed, sim = capture_run(case, seed, PassiveSourceAckSimulator, deadline_s)
    parity = require_stock_parity(stock, observed)

    def analyze(current_sim: PassiveSourceAckSimulator) -> dict[str, Any]:
        acknowledgments = join_source_ack_actions(current_sim)
        cohort = build_initial_r_cohort(current_sim, acknowledgments)
        return {"ack_rows": acknowledgments, "cohort": cohort}

    analysis = analyze(sim)
    if (hashlib.sha256(repr(sim.random.getstate()).encode("ascii")).hexdigest()
            != observed.random_state_sha256
            or hashlib.sha256(
                repr(sim.channel_random.getstate()).encode("ascii")
            ).hexdigest() != observed.channel_random_state_sha256):
        raise AssertionError("source ACK analysis consumed RNG")
    replay, replay_sim = capture_run(
        case, seed, PassiveSourceAckSimulator, deadline_s,
    )
    if observed != replay or analysis != analyze(replay_sim):
        raise AssertionError("source ACK diagnostic strict replay differed")
    return {
        "seed": seed,
        "case": asdict(case),
        "protocol": PROTOCOL,
        "parity": parity,
        "strict_replay_exact": True,
        "row": observed.row,
        "flows": observed.flows,
        "actions": observed.actions,
        "transmissions": observed.transmissions,
        **analysis,
    }
