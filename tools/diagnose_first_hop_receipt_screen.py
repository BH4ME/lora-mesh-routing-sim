#!/usr/bin/env python3
"""Passive first-hop receipt exposure and nominal cost screen for fixed-F DHR."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import Packet, RxInfo, Transmission
from tools import run_sr_experiment as sr
from tools.diagnose_delayed_ack_rx import capture_run, require_stock_parity


# Nested predecessor replay must not resolve the outer capture's patched factory.
_STOCK_RECORDING_SIMULATOR = sr.RecordingSimulator
PROTOCOL = "meshecho-dhr-flood-ack-delay"
SMOKE_SEEDS = (45000,)
EXPLORATORY_SEEDS = tuple(range(45001, 45021))
SOURCE_FILES = (
    ROOT / "lora_mesh_sim.py",
    ROOT / "tools" / "run_fair_multihop_probe.py",
    ROOT / "tools" / "run_sr_experiment.py",
    ROOT / "tools" / "diagnose_delayed_ack_rx.py",
    Path(__file__).resolve(),
    ROOT / "tests" / "test_first_hop_receipt_screen.py",
    ROOT / "tests" / "test_receipt_seed_guard.py",
    ROOT / "docs" / "research" / "meshecho_first_hop_receipt_screen_design.md",
)
ARTIFACT_KEYS = (
    "summary", "runs", "initial_r_rows", "flows", "actions",
    "transmissions", "first_hop_decodes",
)
_RUNNER_AUTHORIZATION = object()


def seeds_for_mode(mode: str) -> tuple[int, ...]:
    if mode == "smoke":
        return SMOKE_SEEDS
    if mode == "explore":
        return EXPLORATORY_SEEDS
    raise ValueError(f"unknown first-hop receipt screen mode: {mode}")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode("ascii")).hexdigest()


def _source_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in SOURCE_FILES
    }


def _stage_mode(seed: int) -> str:
    if seed in SMOKE_SEEDS:
        return "smoke"
    if seed in EXPLORATORY_SEEDS:
        return "explore"
    raise ValueError("receipt reserved seed is outside its stage window")


def _validate_stage(
    mode: str, case: sr.SrCase, deadline_s: float,
    stage_authorization_path: Path | None,
    smoke_manifest_path: Path | None = None,
) -> tuple[dict[str, str], bytes, dict[str, str]]:
    if mode not in {"smoke", "explore"}:
        raise ValueError(f"unknown receipt screen stage: {mode}")
    if case != sr.SR_CASES["recurring_fading"] or deadline_s != 30.0:
        raise ValueError("receipt screen stage requires the frozen case and deadline")
    if stage_authorization_path is None:
        raise ValueError(f"{mode} stage authorization is required")
    try:
        authorization_data = Path(stage_authorization_path).read_bytes()
        authorization = json.loads(authorization_data)
    except (OSError, ValueError) as exc:
        raise ValueError(f"{mode} stage authorization cannot be read") from exc
    source_sha256 = _source_hashes()
    prerequisite_sha256 = {}
    if smoke_manifest_path is not None:
        if mode != "explore":
            raise ValueError("smoke stage cannot have a predecessor")
        prerequisite_sha256["smoke_manifest"] = hashlib.sha256(
            Path(smoke_manifest_path).read_bytes()
        ).hexdigest()
    expected = {
        "mode": mode,
        "seeds": list(seeds_for_mode(mode)),
        "protocol": PROTOCOL,
        "case_sha256": _sha256_json(asdict(case)),
        "application_deadline_s": deadline_s,
        "input_sha256": source_sha256,
        "prerequisite_manifest_sha256": prerequisite_sha256,
    }
    if (authorization != expected
            or not isinstance(authorization.get("seeds"), list)
            or any(type(seed) is not int for seed in authorization["seeds"])):
        raise ValueError(f"{mode} stage authorization differs from frozen inputs")
    if mode == "explore":
        if smoke_manifest_path is None:
            raise ValueError("exploration requires a verified smoke manifest")
        validate_manifest(
            smoke_manifest_path, expected_mode="smoke",
            expected_source_sha256=source_sha256,
            expected_case_sha256=expected["case_sha256"],
            expected_deadline_s=deadline_s, strict_replay=True,
        )
        if (hashlib.sha256(Path(smoke_manifest_path).read_bytes()).hexdigest()
                != prerequisite_sha256["smoke_manifest"]):
            raise RuntimeError("smoke manifest changed during predecessor audit")
    return source_sha256, authorization_data, prerequisite_sha256


class PassiveFirstHopSimulator(sr.RecordingSimulator):
    """Remember the result of each existing initial source DATA receive attempt."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.first_hop_decodes: dict[tuple[int, int], bool] = {}

    def try_receive(self, tx: Transmission, receiver: int) -> RxInfo | None:
        rx = super().try_receive(tx, receiver)
        packet = tx.packet
        if (packet.kind == "DATA" and packet.repair_index is None
                and tx.sender == packet.origin and len(packet.path) >= 2
                and self.protocol.flow_actions.get(packet.flow_id) == "R"
                and self.protocol.flow_data_actions.get(packet.flow_id) == "R"
                and receiver == packet.path[1]):
            key = (tx.tx_id, receiver)
            if key in self.first_hop_decodes:
                raise AssertionError(f"duplicate physical first-hop attempt: {key}")
            self.first_hop_decodes[key] = rx is not None
        return rx


def analyze_screen(
    sim: PassiveFirstHopSimulator, flows: list[dict[str, Any]],
    actions: list[dict[str, Any]], cutoff_s: float,
) -> dict[str, Any]:
    """Join all initial R sends without allowing hidden decodes into the policy."""

    flow_by_id = {flow["flow_id"]: flow for flow in flows}
    if len(flow_by_id) != len(flows):
        raise ValueError("duplicate scheduled flow ID")
    if any("event" not in action for action in actions):
        raise ValueError("receipt screen action is missing event")
    decisions = [action for action in actions
                 if action["event"] == "decision"]
    decision_by_id = {action["flow_id"]: action for action in decisions}
    if len(decision_by_id) != len(decisions):
        raise ValueError("duplicate initial decision for one flow")
    source_starts: dict[int, list[Transmission]] = {}
    for tx in sim.tx_history:
        packet = tx.packet
        if (packet.kind == "DATA" and packet.repair_index is None
                and tx.sender == packet.origin):
            source_starts.setdefault(packet.flow_id, []).append(tx)
    physical_r_ids = {
        flow_id for flow_id in source_starts
        if sim.protocol.flow_actions.get(flow_id) == "R"
        and sim.protocol.flow_data_actions.get(flow_id) == "R"
    }
    decision_r_ids = {
        action["flow_id"] for action in decisions if action["action"] == "R"
    }
    if physical_r_ids != decision_r_ids:
        raise ValueError(
            "unmatched physical initial R DATA and decision: "
            f"TX-only={sorted(physical_r_ids - decision_r_ids)}, "
            f"decision-only={sorted(decision_r_ids - physical_r_ids)}"
        )
    if any(tx.start > cutoff_s for tx in sim.tx_history):
        raise ValueError("TX history extends beyond the drain window")
    physical_airtime_s = sum(tx.end - tx.start for tx in sim.tx_history)
    if not math.isclose(
        physical_airtime_s, sim.metrics.total_airtime_s, rel_tol=0.0,
        abs_tol=1e-7,
    ):
        raise ValueError("complete physical TX airtime differs from metrics")

    # Marker 4 charges one explicit receipt byte; this packet is never sent.
    nominal_receipt = Packet(
        kind="ACK", flow_id=0, origin=1, final_dst=0, ttl=sim.max_hops,
        created_at=0.0, protocol=PROTOCOL, request_id=0,
        path=(0, 1), app_payload=False, repair_index=4,
    )
    receipt_bytes = nominal_receipt.wire_size_bytes(sim.radio.payload_bytes)
    receipt_toa_s = sim.radio.packet_toa_s(nominal_receipt)
    if receipt_bytes != 17:
        raise AssertionError("nominal first-hop receipt is not 17 bytes")

    rows = []
    for decision in decisions:
        if decision["action"] != "R":
            continue
        flow_id = decision["flow_id"]
        flow = flow_by_id.get(flow_id)
        if (flow is None or flow["registered"] is not True
                or flow["src"] != decision["src"]
                or flow["dst"] != decision["dst"]):
            raise ValueError(f"initial R flow {flow_id} has no registered enqueue")
        starts = source_starts.get(flow_id, [])
        if len(starts) != 1:
            raise ValueError(f"initial R flow {flow_id} has {len(starts)} source DATA starts")
        tx = starts[0]
        packet = tx.packet
        path = packet.path
        if not (
            packet.protocol == PROTOCOL and packet.flow_id == flow_id
            and packet.request_id == flow_id and packet.origin == flow["src"]
            and packet.final_dst == flow["dst"]
            and packet.path_index == 0
            and 2 <= len(path) <= sim.max_hops + 1
            and path[0] == flow["src"] and path[-1] == flow["dst"]
            and len(set(path)) == len(path)
            and math.isclose(packet.created_at, flow["enqueued_at"], abs_tol=1e-7)
            and flow["enqueued_at"] <= decision["time"] <= tx.start
        ):
            raise ValueError(f"initial R flow {flow_id} has an incoherent DATA path")
        next_hop = path[1]
        decode_key = (tx.tx_id, next_hop)
        censored = tx.end > cutoff_s
        if not censored and decode_key not in sim.first_hop_decodes:
            raise ValueError(f"initial R flow {flow_id} lacks a physical first-hop result")
        if censored and decode_key in sim.first_hop_decodes:
            raise ValueError(f"censored initial R flow {flow_id} has a decode")
        decoded = None if censored else sim.first_hop_decodes[decode_key]
        state_drops = [action for action in actions
                       if action.get("event") == "dhr_state_drop"
                       and action["flow_id"] == flow_id]
        if len(state_drops) > 1 or any(
            action["reason"] != "active-capacity"
            or action["src"] != flow["src"]
            or action["dst"] != flow["dst"]
            or not math.isclose(action["time"], tx.start, abs_tol=1e-7)
            for action in state_drops
        ):
            raise ValueError(f"initial R flow {flow_id} has an invalid state drop")
        state_dropped = bool(state_drops)
        accepted_initial = [action for action in actions
                            if action.get("event") == "dhr_source_ack_rx"
                            and action["flow_id"] == flow_id
                            and action["repair_index"] is None
                            and action["accepted"] is True]
        accepted_any = [action for action in actions
                        if action.get("event") == "dhr_source_ack_rx"
                        and action["flow_id"] == flow_id
                        and action["accepted"] is True]
        if len(accepted_any) > 1 or (
            (accepted_any[0]["time"] if accepted_any else None) != flow["acked_at"]
        ):
            raise ValueError(f"initial R flow {flow_id} source ACK join differs")
        guard_at = min(tx.start + 15.0, flow["deadline_at"])
        initial_ack_by_guard = any(
            action["time"] <= guard_at + 1e-9 for action in accepted_initial
        )
        early_at = tx.end + 1.0
        fixed_at = tx.start + 15.0
        base_bound_s = sim.protocol.rescue_round_trip_bound_s(path)
        nominal_flood = Packet(
            kind="FLOOD", flow_id=flow_id, origin=flow["src"],
            final_dst=flow["dst"], ttl=sim.max_hops,
            created_at=flow["enqueued_at"], protocol=PROTOCOL,
            request_id=flow_id, path=(flow["src"],), repair_index=2,
        )
        hold_s = sim.protocol.reverse_ack_delay_s(nominal_flood)
        bound_s = base_bound_s + hold_s
        source_busy_early = None if early_at > cutoff_s else any(
            other.sender == flow["src"]
            and other.start <= early_at < other.end
            for other in sim.tx_history
        )
        source_busy_fixed = None if fixed_at > cutoff_s else any(
            other.sender == flow["src"]
            and other.start <= fixed_at < other.end
            and not (
                other.packet.flow_id == flow_id
                and other.packet.kind == "FLOOD"
                and other.packet.repair_index == 2
                and math.isclose(other.start, fixed_at, abs_tol=1e-9)
            )
            for other in sim.tx_history
        )
        source_unacked_early = None if early_at > cutoff_s else (
            flow["acked_at"] is None or flow["acked_at"] > early_at
        )
        source_unacked_deadline = not flow["ack_by_deadline"]
        multihop = len(path) > 2
        eligible = multihop and decoded is False and not initial_ack_by_guard
        early_fit = early_at + bound_s <= flow["deadline_at"] + 1e-9
        fixed_fit = fixed_at + bound_s <= flow["deadline_at"] + 1e-9
        early_admitted = (
            eligible and source_unacked_early is True
            and source_busy_early is False
            and early_fit
        )
        fixed_admitted = eligible and source_busy_fixed is False and fixed_fit
        rows.append({
            "seed": sim.seed, "flow_id": flow_id,
            "src": flow["src"], "dst": flow["dst"],
            "decision": "R", "decision_at_s": decision["time"],
            "enqueued_at_s": flow["enqueued_at"],
            "deadline_at_s": flow["deadline_at"],
            "first_tx_id": tx.tx_id, "initial_r_start_at_s": tx.start,
            "initial_r_end_at_s": tx.end,
            "initial_r_started_by_deadline": tx.start <= flow["deadline_at"],
            "decision_to_r_start_queue_s": tx.start - decision["time"],
            "path": list(path), "first_hop": next_hop,
            "path_type": "direct" if not multihop else "multihop",
            "first_hop_decoded": decoded,
            "first_hop_censored": censored,
            "initial_r_guard_at_s": guard_at,
            "initial_r_source_ack_by_guard": initial_ack_by_guard,
            "source_ack_by_deadline": flow["ack_by_deadline"],
            "destination_delivery_by_deadline": flow["delivery_by_deadline"],
            "source_unacked_at_early_trigger": source_unacked_early,
            "source_unacked_by_deadline": source_unacked_deadline,
            "failed_multihop_no_initial_ack": eligible,
            "dhr_state_drop_at_initial_start": state_dropped,
            "nominal_early_trigger_at_s": early_at,
            "nominal_fixed_trigger_at_s": fixed_at,
            "dhr_base_round_trip_bound_s": base_bound_s,
            "delayed_f_ack_hold_s": hold_s,
            "nominal_delayed_f_round_trip_bound_s": bound_s,
            "source_busy_at_early_trigger": source_busy_early,
            "source_busy_at_fixed_trigger": source_busy_fixed,
            "nominal_early_deadline_fit": early_fit,
            "nominal_fixed_deadline_fit": fixed_fit,
            "nominal_early_f_admitted": early_admitted,
            "nominal_fixed_f_admitted": fixed_admitted,
            "early_only_deadline_admission": (
                eligible and early_fit and not fixed_fit
            ),
            "early_only_available_admission": (
                early_admitted and not fixed_admitted
            ),
            "residual_unacked_early_opportunity": (
                early_admitted and source_unacked_deadline and not state_dropped
            ),
        })
    multihop_rows = [row for row in rows if row["path_type"] == "multihop"]
    failed_no_ack = [row for row in multihop_rows
                     if row["failed_multihop_no_initial_ack"]]
    decoded_multihop = sum(row["first_hop_decoded"] is True for row in multihop_rows)
    lower_cost = decoded_multihop * receipt_toa_s
    upper_cost = len(multihop_rows) * receipt_toa_s
    return {
        "initial_r_rows": rows,
        "summary": {
            "initial_r_flows": len(rows),
            "direct_initial_r_flows": len(rows) - len(multihop_rows),
            "multihop_initial_r_flows": len(multihop_rows),
            "late_initial_r_starts": sum(
                not row["initial_r_started_by_deadline"] for row in rows
            ),
            "direct_first_hop_failures": sum(
                row["first_hop_decoded"] is False for row in rows
                if row["path_type"] == "direct"
            ),
            "censored_direct_initial_r_flows": sum(
                row["first_hop_censored"] for row in rows
                if row["path_type"] == "direct"
            ),
            "censored_multihop_initial_r_flows": sum(
                row["first_hop_censored"] for row in multihop_rows
            ),
            "decoded_multihop_first_hops": decoded_multihop,
            "multihop_initial_r_no_guard_ack": sum(
                not row["initial_r_source_ack_by_guard"] for row in multihop_rows
            ),
            "failed_multihop_no_guard_ack": len(failed_no_ack),
            "failed_multihop_no_guard_ack_source_acked_by_deadline": sum(
                row["source_ack_by_deadline"] for row in failed_no_ack
            ),
            "failed_multihop_no_guard_ack_delivered_by_deadline": sum(
                row["destination_delivery_by_deadline"] for row in failed_no_ack
            ),
            "failed_multihop_no_guard_ack_delivered_unacked": sum(
                row["destination_delivery_by_deadline"]
                and row["source_unacked_by_deadline"] for row in failed_no_ack
            ),
            "failed_multihop_no_guard_ack_undelivered_unacked": sum(
                not row["destination_delivery_by_deadline"]
                and row["source_unacked_by_deadline"] for row in failed_no_ack
            ),
            "source_busy_at_early_trigger_failures": sum(
                row["source_busy_at_early_trigger"] is True
                for row in failed_no_ack
            ),
            "source_busy_at_fixed_trigger_failures": sum(
                row["source_busy_at_fixed_trigger"] is True
                for row in failed_no_ack
            ),
            "already_source_acked_at_early_trigger_failures": sum(
                row["source_unacked_at_early_trigger"] is False
                for row in failed_no_ack
            ),
            "active_capacity_excluded_failures": sum(
                row["dhr_state_drop_at_initial_start"] for row in failed_no_ack
            ),
            "nominal_early_f_admissions": sum(
                row["nominal_early_f_admitted"] for row in failed_no_ack
            ),
            "nominal_fixed_f_admissions": sum(
                row["nominal_fixed_f_admitted"] for row in failed_no_ack
            ),
            "early_only_deadline_admissions": sum(
                row["early_only_deadline_admission"] for row in failed_no_ack
            ),
            "early_only_available_admissions": sum(
                row["early_only_available_admission"] for row in failed_no_ack
            ),
            "both_deadline_admissions": sum(
                row["nominal_early_deadline_fit"]
                and row["nominal_fixed_deadline_fit"]
                for row in failed_no_ack
            ),
            "fixed_only_deadline_admissions": sum(
                not row["nominal_early_deadline_fit"]
                and row["nominal_fixed_deadline_fit"]
                for row in failed_no_ack
            ),
            "neither_deadline_admissions": sum(
                not row["nominal_early_deadline_fit"]
                and not row["nominal_fixed_deadline_fit"]
                for row in failed_no_ack
            ),
            "residual_unacked_early_opportunities": sum(
                row["residual_unacked_early_opportunity"] for row in failed_no_ack
            ),
            "residual_unacked_early_delivered": sum(
                row["residual_unacked_early_opportunity"]
                and row["destination_delivery_by_deadline"]
                for row in failed_no_ack
            ),
            "residual_unacked_early_undelivered": sum(
                row["residual_unacked_early_opportunity"]
                and not row["destination_delivery_by_deadline"]
                for row in failed_no_ack
            ),
            "decision_to_r_start_queue_mean_s": (
                sum(row["decision_to_r_start_queue_s"] for row in rows) / len(rows)
                if rows else None
            ),
            "receipt_wire_bytes": receipt_bytes,
            "receipt_toa_s": receipt_toa_s,
            "whole_network_tx_airtime_s": physical_airtime_s,
            "receipt_lower_bound_airtime_s": lower_cost,
            "receipt_lower_bound_airtime_fraction": (
                lower_cost / physical_airtime_s if physical_airtime_s else None
            ),
            "receipt_upper_coverage_airtime_s": upper_cost,
            "receipt_upper_coverage_airtime_fraction": (
                upper_cost / physical_airtime_s if physical_airtime_s else None
            ),
        },
    }


def run_diagnostic(
    seed: int, case: sr.SrCase = sr.SR_CASES["recurring_fading"],
    deadline_s: float = 30.0, *, research_authorization: object | None = None,
    stage_authorization_path: Path | None = None,
    smoke_manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Pair stock and passive captures, then independently replay observations."""

    if seed >= 35000 and seed not in sr.FIRST_HOP_RECEIPT_RESERVED_SEEDS:
        raise ValueError("reserved research seed requires a verified stage")
    if seed in sr.FIRST_HOP_RECEIPT_RESERVED_SEEDS:
        if type(seed) is not int:
            raise ValueError("receipt reserved seed requires integer stage identity")
        if research_authorization is not _RUNNER_AUTHORIZATION:
            raise ValueError("reserved research seed requires stage authorization")
        _validate_stage(
            _stage_mode(seed), case, deadline_s,
            stage_authorization_path, smoke_manifest_path,
        )
    if deadline_s <= 0:
        raise ValueError("receipt screen requires a positive application deadline")
    def authorized_runner(
        runner_case: sr.SrCase, protocol: str, runner_seed: int,
        runner_deadline_s: float,
    ) -> sr.SrRun:
        return sr.run_one_sr(
            runner_case, protocol, runner_seed, runner_deadline_s,
            research_authorization=_RUNNER_AUTHORIZATION,
            stage_authorization_path=stage_authorization_path,
            smoke_manifest_path=smoke_manifest_path,
        )

    runner = (
        authorized_runner if research_authorization is _RUNNER_AUTHORIZATION
        else None
    )
    stock, _ = capture_run(
        case, seed, _STOCK_RECORDING_SIMULATOR, deadline_s, runner=runner,
    )
    observed, sim = capture_run(
        case, seed, PassiveFirstHopSimulator, deadline_s, runner=runner,
    )
    parity = require_stock_parity(stock, observed)
    analysis = analyze_screen(
        sim, observed.flows, observed.actions, case.duration_s + deadline_s,
    )
    replay, replay_sim = capture_run(
        case, seed, PassiveFirstHopSimulator, deadline_s, runner=runner,
    )
    replay_analysis = analyze_screen(
        replay_sim, replay.flows, replay.actions,
        case.duration_s + deadline_s,
    )
    if (observed != replay
            or sim.first_hop_decodes != replay_sim.first_hop_decodes
            or analysis != replay_analysis):
        raise AssertionError("first-hop screen strict replay differs")
    for current_sim, evidence in ((sim, observed), (replay_sim, replay)):
        if (hashlib.sha256(repr(current_sim.random.getstate()).encode("ascii")).hexdigest()
                != evidence.random_state_sha256
                or hashlib.sha256(
                    repr(current_sim.channel_random.getstate()).encode("ascii")
                ).hexdigest() != evidence.channel_random_state_sha256):
            raise AssertionError("passive analysis consumed RNG")
    return {
        "seed": seed, "case": asdict(case), "protocol": PROTOCOL,
        "parity": parity, "strict_replay_exact": True,
        "row": observed.row, "flows": observed.flows,
        "actions": observed.actions, "transmissions": observed.transmissions,
        "first_hop_decodes": sorted(
            (tx_id, receiver, decoded)
            for (tx_id, receiver), decoded in sim.first_hop_decodes.items()
        ),
        **analysis,
    }


def summarize_cohort(runs: list[dict[str, Any]], mode: str) -> dict[str, Any]:
    """Aggregate exposure and optimistic ceilings without effect claims."""

    if not runs:
        raise ValueError("cannot summarize an empty receipt screen")
    count_keys = (
        "initial_r_flows", "direct_initial_r_flows", "multihop_initial_r_flows",
        "late_initial_r_starts",
        "censored_direct_initial_r_flows", "censored_multihop_initial_r_flows",
        "direct_first_hop_failures", "decoded_multihop_first_hops",
        "multihop_initial_r_no_guard_ack", "failed_multihop_no_guard_ack",
        "failed_multihop_no_guard_ack_source_acked_by_deadline",
        "failed_multihop_no_guard_ack_delivered_by_deadline",
        "failed_multihop_no_guard_ack_delivered_unacked",
        "failed_multihop_no_guard_ack_undelivered_unacked",
        "source_busy_at_early_trigger_failures",
        "source_busy_at_fixed_trigger_failures",
        "already_source_acked_at_early_trigger_failures",
        "active_capacity_excluded_failures", "nominal_early_f_admissions",
        "nominal_fixed_f_admissions", "early_only_deadline_admissions",
        "early_only_available_admissions", "both_deadline_admissions",
        "fixed_only_deadline_admissions", "neither_deadline_admissions",
        "residual_unacked_early_opportunities",
        "residual_unacked_early_delivered",
        "residual_unacked_early_undelivered",
    )
    summary = {
        key: sum(run["summary"][key] for run in runs) for key in count_keys
    }
    scheduled = sum(run["row"]["scheduled_unicast_flows"] for run in runs)
    gate2 = summary["residual_unacked_early_opportunities"]
    denominator = summary["multihop_initial_r_no_guard_ack"]
    receipt_fractions = [
        run["summary"]["receipt_lower_bound_airtime_fraction"] for run in runs
    ]
    if any(fraction is None for fraction in receipt_fractions):
        raise ValueError("a seed has no whole-network physical TX airtime")
    summary.update({
        "all_scheduled_unicast_flows": scheduled,
        "failed_multihop_no_guard_ack_seed_count": sum(
            run["summary"]["failed_multihop_no_guard_ack"] > 0 for run in runs
        ),
        "failed_multihop_fraction_of_multihop_no_guard_ack": (
            summary["failed_multihop_no_guard_ack"] / denominator
            if denominator else None
        ),
        "gate_2_residual_unacked_early_opportunities": gate2,
        "gate_2_seed_count": sum(
            run["summary"]["residual_unacked_early_opportunities"] > 0
            for run in runs
        ),
        "gate_2_delivered_unacked": summary["residual_unacked_early_delivered"],
        "gate_2_undelivered_unacked": summary["residual_unacked_early_undelivered"],
        "receipt_wire_bytes": runs[0]["summary"]["receipt_wire_bytes"],
        "receipt_toa_s": runs[0]["summary"]["receipt_toa_s"],
        "whole_network_tx_airtime_s": sum(
            run["summary"]["whole_network_tx_airtime_s"] for run in runs
        ),
        "receipt_lower_bound_airtime_s": sum(
            run["summary"]["receipt_lower_bound_airtime_s"] for run in runs
        ),
        "receipt_upper_coverage_airtime_s": sum(
            run["summary"]["receipt_upper_coverage_airtime_s"] for run in runs
        ),
        "receipt_lower_bound_airtime_fraction_equal_seed_mean": (
            sum(receipt_fractions) / len(runs)
        ),
        "receipt_upper_coverage_airtime_fraction_equal_seed_mean": (
            sum(run["summary"]["receipt_upper_coverage_airtime_fraction"]
                for run in runs) / len(runs)
        ),
        "optimistic_source_ack_pdr_gain_equal_seed_mean": (
            sum(run["summary"]["residual_unacked_early_opportunities"]
                / run["row"]["scheduled_unicast_flows"] for run in runs) / len(runs)
        ),
        "optimistic_source_ack_pdr_gain_pooled": gate2 / scheduled,
        "optimistic_destination_pdr_gain_equal_seed_mean": (
            sum(run["summary"]["residual_unacked_early_undelivered"]
                / run["row"]["scheduled_unicast_flows"] for run in runs) / len(runs)
        ),
        "optimistic_destination_pdr_gain_pooled": (
            summary["residual_unacked_early_undelivered"] / scheduled
        ),
    })
    if mode == "explore":
        gate1 = (
            summary["failed_multihop_no_guard_ack"] >= 20
            and summary["failed_multihop_no_guard_ack_seed_count"] >= 8
            and denominator > 0
            and summary["failed_multihop_no_guard_ack"] / denominator >= 0.15
        )
        gate2_passed = gate2 >= 10 and summary["gate_2_seed_count"] >= 5
        gate3 = summary["receipt_lower_bound_airtime_fraction_equal_seed_mean"] <= 0.10
        gate4 = summary["optimistic_source_ack_pdr_gain_equal_seed_mean"] >= 0.02
    else:
        gate1 = gate2_passed = gate3 = gate4 = None
    summary.update({
        "gate_1_exposure_passed": gate1,
        "gate_2_residual_opportunity_passed": gate2_passed,
        "gate_3_receipt_cost_passed": gate3,
        "gate_4_optimistic_ceiling_passed": gate4,
        "necessary_gate_passed": (
            all((gate1, gate2_passed, gate3, gate4)) if mode == "explore" else None
        ),
    })
    return summary


def run_report(
    seeds: tuple[int, ...], *, mode: str,
    case: sr.SrCase = sr.SR_CASES["recurring_fading"],
    deadline_s: float = 30.0,
    smoke_manifest_path: Path | None = None,
    stage_authorization_path: Path | None = None,
) -> dict[str, Any]:
    """Run only the prespecified stage after verifying its predecessor."""

    seeds = tuple(seeds)
    if any(type(seed) is not int for seed in seeds):
        raise ValueError("receipt screen requires exact integer seed identity")
    if mode == "synthetic":
        if seeds != (73,):
            raise ValueError("synthetic mode is limited to the seed-73 fixture")
    elif seeds != seeds_for_mode(mode):
        raise ValueError(f"{mode} requires its exact preregistered seed cohort")
    if mode != "synthetic" and (
        case != sr.SR_CASES["recurring_fading"] or deadline_s != 30.0
    ):
        raise ValueError("receipt screen stage requires the frozen case and deadline")
    if mode == "explore":
        if smoke_manifest_path is None:
            raise ValueError("exploration requires a verified smoke manifest")
    case_sha256 = _sha256_json(asdict(case))
    if mode == "synthetic":
        source_sha256 = _source_hashes()
        authorization_data = None
        prerequisite_sha256: dict[str, str] = {}
    else:
        source_sha256, authorization_data, prerequisite_sha256 = _validate_stage(
            mode, case, deadline_s,
            stage_authorization_path, smoke_manifest_path,
        )
    runs = []
    for seed in seeds:
        run = run_diagnostic(
            seed, case, deadline_s,
            research_authorization=_RUNNER_AUTHORIZATION,
            stage_authorization_path=stage_authorization_path,
            smoke_manifest_path=smoke_manifest_path,
        )
        if run["parity"]["exact"] is not True or run["strict_replay_exact"] is not True:
            raise AssertionError(f"seed {seed} has incomplete stock parity or replay")
        if _source_hashes() != source_sha256:
            raise RuntimeError("receipt screen source changed during the cohort")
        if (authorization_data is not None
                and Path(stage_authorization_path).read_bytes()
                != authorization_data):
            raise RuntimeError("receipt screen stage authorization changed during the cohort")
        if (mode == "explore"
                and hashlib.sha256(Path(smoke_manifest_path).read_bytes()).hexdigest()
                != prerequisite_sha256["smoke_manifest"]):
            raise RuntimeError("receipt screen predecessor changed during the cohort")
        runs.append(run)
    summary = summarize_cohort(runs, mode)
    report = {
        "analysis_type": "passive first-hop exposure and nominal receipt cost",
        "counterfactual_timing_bounds_only": True,
        "observed_receipt_transmissions": 0,
        "mode": mode, "protocol": PROTOCOL,
        "case": asdict(case), "case_sha256": case_sha256,
        "seeds": list(seeds), "application_deadline_s": deadline_s,
        "drain_until_s": case.duration_s + deadline_s,
        "source_sha256": source_sha256,
        "prerequisite_manifest_sha256": prerequisite_sha256,
        "summary": summary, "runs": runs,
    }
    if authorization_data is not None:
        report["stage_authorization_sha256"] = hashlib.sha256(
            authorization_data
        ).hexdigest()
        report["_stage_authorization_data"] = authorization_data
    return report


def _artifact_paths(prefix: Path) -> dict[str, Path]:
    paths = {
        key: prefix.with_name(prefix.name + (
            ".summary.json" if key == "summary" else f".{key}.jsonl"
        )) for key in ARTIFACT_KEYS
    }
    paths["authorization"] = prefix.with_name(prefix.name + ".authorization.json")
    paths["manifest"] = prefix.with_name(prefix.name + ".manifest.json")
    paths["manifest_sha256"] = prefix.with_name(prefix.name + ".manifest.sha256")
    return paths


def write_report(report: dict[str, Any], output_prefix: Path) -> dict[str, Path]:
    """Save complete evidence under exclusive, content-hashed artifact names."""

    prefix = Path(output_prefix)
    paths = _artifact_paths(prefix)
    if prefix.exists() or any(path.exists() for path in paths.values()):
        raise FileExistsError(f"receipt screen output prefix already exists: {prefix}")
    if _source_hashes() != report["source_sha256"]:
        raise ValueError("receipt screen source changed before artifact writing")
    if not all(
        run["parity"]["exact"] is True and run["strict_replay_exact"] is True
        for run in report["runs"]
    ):
        raise ValueError("receipt screen cannot save an unverified run")

    def json_line(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"

    artifact_keys = ARTIFACT_KEYS + (
        ("authorization",) if report["mode"] != "synthetic" else ()
    )
    metadata = {
        key: value for key, value in report.items()
        if key not in {"runs", "_stage_authorization_data"}
    }
    data = {
        "summary": (json.dumps(metadata, sort_keys=True, indent=2) + "\n").encode()
    }
    separated = set(ARTIFACT_KEYS) - {"summary", "runs"}
    data["runs"] = "".join(json_line({
        key: value for key, value in run.items() if key not in separated
    }) for run in report["runs"]).encode()
    for key in separated:
        data[key] = "".join(
            json_line({"seed": run["seed"], "item": item})
            for run in report["runs"] for item in run[key]
        ).encode()
    if report["mode"] != "synthetic":
        data["authorization"] = report["_stage_authorization_data"]
        if (hashlib.sha256(data["authorization"]).hexdigest()
                != report["stage_authorization_sha256"]):
            raise ValueError("receipt screen stage authorization changed before writing")
    manifest = {
        "mode": report["mode"], "protocol": report["protocol"],
        "seeds": report["seeds"], "case_sha256": report["case_sha256"],
        "application_deadline_s": report["application_deadline_s"],
        "drain_until_s": report["drain_until_s"],
        "source_sha256": report["source_sha256"],
        "prerequisite_manifest_sha256": report["prerequisite_manifest_sha256"],
        "summary": report["summary"],
        "artifacts": {
            key: {"file": paths[key].name,
                  "sha256": hashlib.sha256(data[key]).hexdigest()}
            for key in artifact_keys
        },
    }
    if report["mode"] != "synthetic":
        manifest["stage_authorization_sha256"] = report[
            "stage_authorization_sha256"
        ]
    manifest_data = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    sidecar = (
        hashlib.sha256(manifest_data).hexdigest()
        + "  " + paths["manifest"].name + "\n"
    ).encode("ascii")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    for key in artifact_keys:
        with paths[key].open("xb") as output:
            output.write(data[key])
    with paths["manifest"].open("xb") as output:
        output.write(manifest_data)
    with paths["manifest_sha256"].open("xb") as output:
        output.write(sidecar)
    return paths


def validate_manifest(
    manifest_path: Path, *, expected_mode: str,
    expected_source_sha256: dict[str, str], expected_case_sha256: str,
    expected_deadline_s: float | None = None, strict_replay: bool = True,
    smoke_manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Audit prior artifacts and optionally compare all rows to fresh captures."""

    manifest_path = Path(manifest_path)
    if not manifest_path.name.endswith(".manifest.json"):
        raise ValueError("receipt screen manifest needs .manifest.json suffix")
    prefix = manifest_path.with_name(
        manifest_path.name[:-len(".manifest.json")]
    )
    paths = _artifact_paths(prefix)
    manifest_data = manifest_path.read_bytes()
    expected_sidecar = (
        hashlib.sha256(manifest_data).hexdigest()
        + "  " + manifest_path.name + "\n"
    )
    if paths["manifest_sha256"].read_text(encoding="ascii") != expected_sidecar:
        raise ValueError("receipt screen manifest SHA-256 sidecar differs")
    manifest = json.loads(manifest_data)
    if expected_mode == "explore" and smoke_manifest_path is None:
        raise ValueError("explore archive requires its smoke manifest")
    artifact_keys = ARTIFACT_KEYS + (
        ("authorization",) if expected_mode != "synthetic" else ()
    )
    if (
        manifest.get("mode") != expected_mode
        or manifest.get("protocol") != PROTOCOL
        or manifest.get("case_sha256") != expected_case_sha256
        or manifest.get("source_sha256") != expected_source_sha256
        or _source_hashes() != expected_source_sha256
        or set(manifest.get("artifacts", {})) != set(artifact_keys)
    ):
        raise ValueError("receipt screen manifest frozen source, case or mode differs")
    if (expected_deadline_s is not None
            and manifest.get("application_deadline_s") != expected_deadline_s):
        raise ValueError("receipt screen manifest deadline differs")
    if (expected_mode == "smoke"
            and manifest.get("prerequisite_manifest_sha256") != {}):
        raise ValueError("receipt screen smoke cannot claim a prior stage")
    if expected_mode == "explore" and (
        not isinstance(manifest.get("prerequisite_manifest_sha256"), dict)
        or set(manifest["prerequisite_manifest_sha256"]) != {"smoke_manifest"}
    ):
        raise ValueError("receipt screen explore predecessor scope differs")
    if expected_mode == "synthetic":
        expected_seeds = (73,)
    else:
        expected_seeds = seeds_for_mode(expected_mode)
    if (tuple(manifest["seeds"]) != expected_seeds
            or any(type(seed) is not int for seed in manifest["seeds"])):
        raise ValueError("receipt screen manifest seeds differ from frozen cohort")
    data = {}
    for key in artifact_keys:
        descriptor = manifest["artifacts"][key]
        if descriptor.get("file") != paths[key].name:
            raise ValueError(f"receipt screen artifact path differs: {key}")
        data[key] = paths[key].read_bytes()
        if hashlib.sha256(data[key]).hexdigest() != descriptor.get("sha256"):
            raise ValueError(f"receipt screen artifact checksum differs: {key}")
    if expected_mode != "synthetic":
        authorization = json.loads(data["authorization"])
        expected_authorization = {
            "mode": expected_mode,
            "seeds": list(expected_seeds),
            "protocol": PROTOCOL,
            "case_sha256": expected_case_sha256,
            "application_deadline_s": manifest["application_deadline_s"],
            "input_sha256": expected_source_sha256,
            "prerequisite_manifest_sha256": manifest[
                "prerequisite_manifest_sha256"
            ],
        }
        if (authorization != expected_authorization
                or not isinstance(authorization.get("seeds"), list)
                or any(type(seed) is not int for seed in authorization["seeds"])
                or hashlib.sha256(data["authorization"]).hexdigest()
                != manifest.get("stage_authorization_sha256")):
            raise ValueError("receipt screen archived stage authorization differs")
        if (expected_mode == "explore" and smoke_manifest_path is not None
                and hashlib.sha256(Path(smoke_manifest_path).read_bytes()).hexdigest()
                != manifest["prerequisite_manifest_sha256"].get("smoke_manifest")):
            raise ValueError("receipt screen predecessor manifest checksum differs")
    metadata = json.loads(data["summary"])
    if (
        metadata.get("analysis_type")
        != "passive first-hop exposure and nominal receipt cost"
        or metadata.get("counterfactual_timing_bounds_only") is not True
        or metadata.get("observed_receipt_transmissions") != 0
    ):
        raise ValueError("receipt screen passive analysis labels differ")
    for key in (
        "mode", "protocol", "seeds", "case_sha256", "application_deadline_s",
        "drain_until_s", "source_sha256", "prerequisite_manifest_sha256",
        "summary", "stage_authorization_sha256",
    ):
        if metadata.get(key) != manifest.get(key):
            raise ValueError(f"receipt screen summary/manifest differs in {key}")
    if _sha256_json(metadata["case"]) != expected_case_sha256:
        raise ValueError("receipt screen saved case differs from frozen case")
    if (expected_mode != "synthetic"
            and metadata["case"] != asdict(sr.SR_CASES["recurring_fading"])):
        raise ValueError("receipt screen saved case differs from frozen stage")
    if metadata["drain_until_s"] != (
        metadata["case"]["duration_s"] + metadata["application_deadline_s"]
    ):
        raise ValueError("receipt screen saved drain window differs")
    saved_runs = [json.loads(line) for line in data["runs"].splitlines()]
    if [run["seed"] for run in saved_runs] != manifest["seeds"]:
        raise ValueError("receipt screen run seeds differ from manifest")
    grouped: dict[str, dict[int, list[Any]]] = {}
    for key in ARTIFACT_KEYS:
        if key in {"summary", "runs"}:
            continue
        grouped[key] = {seed: [] for seed in expected_seeds}
        for line in data[key].splitlines():
            wrapper = json.loads(line)
            if wrapper["seed"] not in grouped[key]:
                raise ValueError(f"receipt screen {key} has an unknown seed")
            item = wrapper["item"]
            if isinstance(item, dict) and item.get("seed", wrapper["seed"]) != wrapper["seed"]:
                raise ValueError(f"receipt screen {key} row seed differs")
            grouped[key][wrapper["seed"]].append(item)
    archived_runs = []
    for saved in saved_runs:
        seed = saved["seed"]
        run = {**saved, **{key: grouped[key][seed] for key in grouped}}
        parity = run["parity"]
        if (
            parity.get("exact") is not True
            or run.get("strict_replay_exact") is not True
            or run["protocol"] != PROTOCOL
            or run["row"]["seed"] != seed
            or run["row"]["scheduled_trace_sha256"]
            != parity["scheduled_trace_sha256"]
            or _sha256_json(run["row"]) != parity["full_row_sha256"]
            or _sha256_json(run["flows"]) != parity["flow_trace_sha256"]
            or _sha256_json(run["actions"]) != parity["action_trace_sha256"]
            or _sha256_json(run["transmissions"]) != parity["full_tx_trace_sha256"]
            or len(run["flows"]) != run["row"]["scheduled_unicast_flows"]
            or len(run["initial_r_rows"]) != run["summary"]["initial_r_flows"]
        ):
            raise ValueError(f"receipt screen archived parity differs at seed {seed}")
        archived_runs.append(run)
    if summarize_cohort(archived_runs, expected_mode) != manifest["summary"]:
        raise ValueError("receipt screen cohort summary differs from archived runs")
    if strict_replay:
        case = sr.SrCase(**metadata["case"])
        for archived in archived_runs:
            live = run_diagnostic(
                archived["seed"], case, metadata["application_deadline_s"],
                research_authorization=_RUNNER_AUTHORIZATION,
                stage_authorization_path=(
                    paths["authorization"] if expected_mode != "synthetic" else None
                ),
                smoke_manifest_path=smoke_manifest_path,
            )
            if archived != json.loads(json.dumps(live)):
                raise ValueError(
                    f"receipt screen strict replay differs at seed {archived['seed']}"
                )
    return manifest


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("smoke", "explore"))
    parser.add_argument("--output-prefix", required=True, type=Path)
    parser.add_argument("--stage-authorization", required=True, type=Path)
    parser.add_argument("--smoke-manifest", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if (args.output_prefix.exists() or any(
        path.exists() for path in _artifact_paths(args.output_prefix).values()
    )):
        raise FileExistsError(
            f"receipt screen output prefix already exists: {args.output_prefix}"
        )
    report = run_report(
        seeds_for_mode(args.mode), mode=args.mode,
        smoke_manifest_path=args.smoke_manifest,
        stage_authorization_path=args.stage_authorization,
    )
    paths = write_report(report, args.output_prefix)
    validate_manifest(
        paths["manifest"], expected_mode=args.mode,
        expected_source_sha256=report["source_sha256"],
        expected_case_sha256=report["case_sha256"],
        expected_deadline_s=30.0, strict_replay=True,
        smoke_manifest_path=args.smoke_manifest,
    )
    print(json.dumps({
        "artifacts": {key: str(path) for key, path in paths.items()},
        "summary": report["summary"],
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    from tools import diagnose_first_hop_receipt_screen as receipt_screen

    receipt_screen.main()
