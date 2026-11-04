#!/usr/bin/env python3
"""Passively trace physical ACK reception in the fixed-2-s DHR control."""

from __future__ import annotations

import sys
import math
import hashlib
import json
import csv
import io
import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Sequence
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import RxInfo, Transmission, dbm_to_mw
from tools.diagnose_ack_failure_causes import CauseSimulator, classify_failed_hop
from tools.diagnose_flood_ack_hops import analyze_ack_hops
from tools import run_sr_experiment as sr


PROTOCOL = "meshecho-dhr-flood-ack-delay"
SMOKE_SEEDS = (39000,)
EXPLORATORY_SEEDS = tuple(range(39001, 39021))
SOURCE_FILES = (
    ROOT / "lora_mesh_sim.py",
    ROOT / "tools" / "run_fair_multihop_probe.py",
    ROOT / "tools" / "run_sr_experiment.py",
    ROOT / "tools" / "diagnose_flood_ack_hops.py",
    ROOT / "tools" / "diagnose_ack_failure_causes.py",
    Path(__file__).resolve(),
    ROOT / "tests" / "test_delayed_ack_rx_diagnostic.py",
    ROOT / "docs" / "research" / "meshecho_delayed_ack_rx_diagnostic_design.md",
)
ARTIFACT_KEYS = (
    "summary", "runs", "flows", "attempts", "actions", "transmissions", "runs_csv",
)


def seeds_for_mode(mode: str) -> tuple[int, ...]:
    if mode == "smoke":
        return SMOKE_SEEDS
    if mode == "explore":
        return EXPLORATORY_SEEDS
    raise ValueError(f"unknown delayed-ACK receive diagnostic mode: {mode}")


@dataclass(frozen=True)
class RunEvidence:
    row: dict[str, Any]
    flows: list[dict[str, Any]]
    actions: list[dict[str, Any]]
    transmissions: list[dict[str, Any]]
    random_state_sha256: str
    channel_random_state_sha256: str


def _sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("ascii")).hexdigest()


def require_stock_parity(stock: RunEvidence, observed: RunEvidence) -> dict[str, Any]:
    """Refuse physical analysis if instrumentation changes any baseline output."""

    fields = (
        "row", "flows", "actions", "transmissions", "random_state_sha256",
        "channel_random_state_sha256",
    )
    for field in fields:
        if getattr(stock, field) != getattr(observed, field):
            raise AssertionError(f"diagnostic replay differs from stock in {field}")
    return {
        "exact": True,
        "scheduled_trace_sha256": stock.row["scheduled_trace_sha256"],
        "full_row_sha256": _sha256_json(stock.row),
        "flow_trace_sha256": _sha256_json(stock.flows),
        "action_trace_sha256": _sha256_json(stock.actions),
        "full_tx_trace_sha256": _sha256_json(stock.transmissions),
        "random_state_sha256": stock.random_state_sha256,
        "channel_random_state_sha256": stock.channel_random_state_sha256,
    }


def capture_run(
    case: sr.SrCase, seed: int, simulator_type: type[sr.RecordingSimulator],
    deadline_s: float = 30.0,
    runner: Callable[[sr.SrCase, str, int, float], sr.SrRun] | None = None,
) -> tuple[RunEvidence, sr.RecordingSimulator]:
    """Use the unmodified SR runner, substituting only the recorder type."""

    captured: list[sr.RecordingSimulator] = []

    def create_simulator(*args: Any, **kwargs: Any) -> sr.RecordingSimulator:
        sim = simulator_type(*args, **kwargs)
        captured.append(sim)
        return sim

    run = runner or sr.run_one_sr
    with patch.object(sr, "RecordingSimulator", create_simulator):
        result = run(case, PROTOCOL, seed, deadline_s)
    if len(captured) != 1:
        raise AssertionError("SR runner did not construct exactly one simulator")
    sim = captured[0]
    evidence = RunEvidence(
        row=result.row,
        flows=result.flows,
        actions=result.actions,
        transmissions=[asdict(tx) for tx in sim.tx_history],
        random_state_sha256=hashlib.sha256(
            repr(sim.random.getstate()).encode("ascii")
        ).hexdigest(),
        channel_random_state_sha256=hashlib.sha256(
            repr(sim.channel_random.getstate()).encode("ascii")
        ).hexdigest(),
    )
    return evidence, sim


class DiagnosticSimulator(CauseSimulator):
    """Observe ACK results after the simulator's sole physical decode attempt."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.ack_rx_outcomes: dict[tuple[int, int], bool] = {}
        self.ack_candidate_checks: dict[tuple[int, int], dict[str, bool]] = {}

    def off_index_candidate_checks(
        self, tx: Transmission, receiver: int,
    ) -> dict[str, bool]:
        packet = tx.packet
        flow = self.metrics.flows.get(packet.flow_id)
        path = packet.path
        index = packet.path_index
        initial_action = self.protocol.flow_data_actions.get(packet.flow_id)
        initial_path = self.protocol.flow_sent_paths.get(packet.flow_id)
        active = self.protocol.active_flows.get(packet.flow_id)
        if packet.repair_index is None:
            marker_valid = initial_action is not None and (
                initial_action != "R" or path == initial_path
            )
        elif packet.repair_index == 1:
            marker_valid = (
                initial_action == "R" and path == initial_path
                and active is not None and active.started_marker == 1
            )
        elif packet.repair_index == 2:
            marker_valid = (
                initial_action == "R" and active is not None
                and active.started_marker == 2
            )
        else:
            marker_valid = False
        return {
            "flow_identity": bool(
                flow is not None and receiver == flow.src
                and packet.final_dst == flow.src
                and packet.request_id == packet.flow_id
                and packet.protocol == self.protocol.name
            ),
            "destination_origin": bool(flow is not None and packet.origin == flow.dst),
            "repair_marker": bool(marker_valid),
            "path_continuity": bool(
                flow is not None and 2 <= len(path) <= self.max_hops + 1
                and path[0] == flow.src and path[-1] == flow.dst
                and len(set(path)) == len(path)
                and 0 <= index < len(path) - 1
                and tx.sender == path[index + 1]
            ),
            "within_deadline": bool(
                flow is not None
                and tx.end <= flow.created_at + self.protocol.app_deadline_s
            ),
            "not_already_acknowledged": bool(flow is not None and flow.acked_at is None),
        }

    def try_receive(self, tx: Transmission, receiver: int) -> RxInfo | None:
        rx = super().try_receive(tx, receiver)
        packet = tx.packet
        if packet.kind == "ACK":
            intended = (
                packet.path[packet.path_index]
                if 0 <= packet.path_index < len(packet.path) else None
            )
            if receiver == intended or (
                receiver == packet.final_dst and receiver != intended
                and receiver != tx.sender
            ):
                self.ack_rx_outcomes[(tx.tx_id, receiver)] = rx is not None
                if receiver != intended:
                    self.ack_candidate_checks[(tx.tx_id, receiver)] = (
                        self.off_index_candidate_checks(tx, receiver)
                    )
        return rx


def _physical_model_evidence(
    sim: DiagnosticSimulator, tx: Transmission, receiver: int,
) -> dict[str, Any]:
    overlapping = [
        other for other in sim.tx_history
        if other.tx_id != tx.tx_id
        and other.start < tx.end and tx.start < other.end
    ]
    own_tx = [other.tx_id for other in overlapping if other.sender == receiver]
    interference = [
        {"tx_id": other.tx_id, "sender": other.sender,
         "power_dbm": sim.rx_power_dbm(other.sender, receiver, when=other.start)}
        for other in overlapping if other.sender != receiver
    ]
    signal = sim.rx_power_dbm(tx.sender, receiver, when=tx.start)
    capture_failed = bool(interference) and signal < (
        max(item["power_dbm"] for item in interference)
        + sim.radio.capture_threshold_db
    )
    if own_tx or capture_failed:
        sinr = None
        prr = None
    elif interference:
        sinr = 10.0 * math.log10(
            dbm_to_mw(signal) /
            (dbm_to_mw(sim.radio.noise_floor_dbm)
             + sum(dbm_to_mw(item["power_dbm"]) for item in interference))
        )
        prr = sim.prr_from_snr(sinr)
    else:
        sinr = sim.snr_from_power(signal)
        prr = sim.prr_from_snr(sinr)
    return {
        "signal_power_dbm": signal,
        "interfering_powers_dbm": interference,
        "receiver_overlapping_tx_ids": own_tx,
        "model_sinr_db": sinr,
        "model_prr": prr,
    }


def analyze_ack_receptions(
    sim: DiagnosticSimulator, flow_rows: Sequence[dict[str, Any]],
    observation_cutoff_s: float,
) -> dict[str, Any]:
    """List observed intended-hop and off-index source ACK receive attempts."""

    flow_by_id = {flow["flow_id"]: flow for flow in flow_rows}
    attempts = []
    for tx in sim.tx_history:
        if tx.packet.kind != "ACK" or tx.start > observation_cutoff_s:
            continue
        packet = tx.packet
        intended = (
            packet.path[packet.path_index]
            if 0 <= packet.path_index < len(packet.path) else None
        )
        targets = []
        if intended in sim.nodes and intended != tx.sender:
            targets.append((intended, "intended_next_hop"))
        if (packet.final_dst in sim.nodes and packet.final_dst != intended
                and packet.final_dst != tx.sender):
            targets.append((packet.final_dst, "source_off_index"))
        for receiver, role in targets:
            censored = tx.end > observation_cutoff_s
            decoded = None if censored else sim.ack_rx_outcomes.get((tx.tx_id, receiver))
            if not censored and decoded is None:
                raise AssertionError(
                    f"missing physical ACK receive observation: TX {tx.tx_id}, node {receiver}"
                )
            flow = flow_by_id.get(packet.flow_id)
            failure_cause = (
                classify_failed_hop(
                    sim, tx, receiver, sim.tx_history, sim.tx_commitment_times,
                    flow.get("delivered_at") if flow else None,
                ) if decoded is False else None
            )
            checks = (
                sim.ack_candidate_checks.get((tx.tx_id, receiver))
                if role == "source_off_index" and not censored else None
            )
            model = (
                _physical_model_evidence(sim, tx, receiver)
                if not censored else {
                    "signal_power_dbm": None,
                    "interfering_powers_dbm": [],
                    "receiver_overlapping_tx_ids": [],
                    "model_sinr_db": None,
                    "model_prr": None,
                }
            )
            attempts.append({
                "tx_id": tx.tx_id,
                "flow_id": packet.flow_id,
                "sender": tx.sender,
                "receiver": receiver,
                "role": role,
                "path_index": packet.path_index,
                "ack_path": list(packet.path),
                "repair_index": packet.repair_index,
                "start_at_s": tx.start,
                "end_at_s": tx.end,
                "physically_decoded": decoded,
                "outcome": (
                    "censored" if censored else "decoded" if decoded
                    else failure_cause["class"]
                ),
                "failure_cause": failure_cause,
                **model,
                "protocol_path_index_matches": receiver == intended,
                "observation_censored": censored,
                "decoded_by_flow_deadline": (
                    decoded and tx.end <= flow["deadline_at"] if flow else None
                ),
                "candidate_checks": checks,
                "identity_valid_in_deadline_candidate": bool(
                    decoded is True and checks is not None and all(checks.values())
                ),
            })
    counts = Counter(item["role"] for item in attempts)
    return {
        "attempts": attempts,
        "summary": {
            "intended_next_hop_attempts": counts["intended_next_hop"],
            "intended_next_hop_decodes": sum(
                item["physically_decoded"] is True for item in attempts
                if item["role"] == "intended_next_hop"
            ),
            "source_off_index_attempts": counts["source_off_index"],
            "source_off_index_decodes": sum(
                item["physically_decoded"] is True for item in attempts
                if item["role"] == "source_off_index"
            ),
        },
    }


def assess_flows(
    flow_rows: Sequence[dict[str, Any]], attempts: Sequence[dict[str, Any]],
    ack_hops: dict[str, Any], transmissions: Sequence[Transmission],
    observation_cutoff_s: float,
) -> dict[str, Any]:
    """Keep the all-flow denominator while screening actual FLOOD-ACK exposure."""

    hop_by_flow = {
        item["flow_id"]: item for item in ack_hops["missing_flows"]
    }
    attempted_rx = {
        (item["tx_id"], item["receiver"]): item for item in attempts
    }
    off_index_by_flow: dict[int, list[dict[str, Any]]] = {}
    for item in attempts:
        if item["role"] == "source_off_index":
            off_index_by_flow.setdefault(item["flow_id"], []).append(item)
    assessed = []
    first_failures: Counter[str] = Counter()
    root_hops: Counter[str] = Counter()
    for flow in flow_rows:
        flow_id = flow["flow_id"]
        missing = hop_by_flow.get(flow_id, {})
        flood_attempts = [
            item for item in missing.get("ack_attempts", [])
            if item.get("trigger_packet_kind") == "FLOOD"
        ]
        flood_ack_tx_ids = {
            hop["tx_id"] for item in flood_attempts
            for hop in item.get("reverse_hops", [])
        }
        stages = {
            "r_to_f" if item.get("repair_index") == 2 else "initial_f"
            for item in flood_attempts
            if item.get("repair_index") in {None, 2}
        }
        stage = "r_to_f" if "r_to_f" in stages else (
            "initial_f" if "initial_f" in stages else None
        )
        unacked_flood = bool(
            flow["delivery_by_deadline"] and not flow["ack_by_deadline"]
            and flood_attempts
        )
        candidates = [
            item for item in off_index_by_flow.get(flow_id, [])
            if item["tx_id"] in flood_ack_tx_ids
            and item["identity_valid_in_deadline_candidate"]
        ]
        first_failure_class = None
        if flood_attempts:
            failed = flood_attempts[0].get("first_unphysical_reverse_hop")
            if failed is not None:
                receiver = failed["edge"][1]
                physical = attempted_rx.get((failed["tx_id"], receiver))
                if physical is None:
                    raise AssertionError(
                        f"missing classified ACK hop for flow {flow_id}"
                    )
                first_failure_class = physical["outcome"]
            elif flood_attempts[0].get("termination"):
                first_failure_class = flood_attempts[0]["termination"]
        if unacked_flood and first_failure_class is not None:
            first_failures[first_failure_class] += 1
        if unacked_flood:
            root_hops.update(
                "direct" if item["ack_path_hops"] == 1 else "multihop"
                for item in flood_attempts
            )
        final_hop = [
            tx for tx in transmissions
            if tx.packet.kind == "ACK" and tx.packet.flow_id == flow_id
            and tx.tx_id in flood_ack_tx_ids
            and tx.start <= observation_cutoff_s
            and tx.packet.path_index == 0 and len(tx.packet.path) >= 2
            and tx.sender == tx.packet.path[1]
        ]
        assessed.append({
            **flow,
            "flood_stage": stage,
            "flood_ack_path_hops": [
                item["ack_path_hops"] for item in flood_attempts
            ],
            "first_flood_ack_failure_class": first_failure_class,
            "flood_ack_final_hop_tx": bool(final_hop),
            "flood_ack_final_hop_tx_by_deadline": any(
                tx.end <= flow["deadline_at"] for tx in final_hop
            ),
            "valid_off_index_flood_candidate": bool(unacked_flood and candidates),
            "valid_off_index_flood_candidate_tx_ids": [
                item["tx_id"] for item in candidates
            ],
        })
    unacked_flood_flows = [
        item for item in assessed
        if item["delivery_by_deadline"] and not item["ack_by_deadline"]
        and item["flood_ack_path_hops"]
    ]
    denominator = len(unacked_flood_flows)
    valid = sum(item["valid_off_index_flood_candidate"]
                for item in unacked_flood_flows)
    return {
        "flows": assessed,
        "summary": {
            "scheduled_unicast_flows": len(flow_rows),
            "ack_by_deadline": sum(flow["ack_by_deadline"] for flow in flow_rows),
            "delivery_by_deadline": sum(
                flow["delivery_by_deadline"] for flow in flow_rows
            ),
            "delivered_unacked_flows": sum(
                flow["delivery_by_deadline"] and not flow["ack_by_deadline"]
                for flow in flow_rows
            ),
            "delivered_unacked_flood_flows": denominator,
            "delivered_unacked_initial_f": sum(
                item["flood_stage"] == "initial_f" for item in unacked_flood_flows
            ),
            "delivered_unacked_r_to_f": sum(
                item["flood_stage"] == "r_to_f" for item in unacked_flood_flows
            ),
            "valid_off_index_flood_candidates": valid,
            "valid_off_index_flood_candidate_fraction": (
                valid / denominator if denominator else None
            ),
            "candidate_gate_passed": (
                valid >= 4 and denominator > 0 and valid / denominator >= 0.10
            ),
            "flood_ack_path_categories": dict(sorted(root_hops.items())),
            "first_flood_ack_failure_classes": dict(sorted(first_failures.items())),
            "flood_ack_final_hop_tx_flows": sum(
                item["flood_ack_final_hop_tx"] for item in unacked_flood_flows
            ),
            "flood_ack_final_hop_tx_by_deadline_flows": sum(
                item["flood_ack_final_hop_tx_by_deadline"]
                for item in unacked_flood_flows
            ),
        },
    }


def run_diagnostic(
    seed: int, case: sr.SrCase = sr.SR_CASES["recurring_fading"],
    deadline_s: float = 30.0,
    capture: Callable[..., tuple[RunEvidence, sr.RecordingSimulator]] | None = None,
) -> dict[str, Any]:
    """Pair unchanged stock and instrumented fixed-delay runs before analysis."""

    if deadline_s <= 0.0:
        raise ValueError("fixed-delay ACK diagnostic needs a positive deadline")
    replay = capture or capture_run
    stock, _ = replay(case, seed, sr.RecordingSimulator, deadline_s)
    observed, sim = replay(case, seed, DiagnosticSimulator, deadline_s)
    parity = require_stock_parity(stock, observed)
    cutoff = case.duration_s + deadline_s
    receptions = analyze_ack_receptions(sim, observed.flows, cutoff)
    ack_hops = analyze_ack_hops(
        sim.tx_history, sim.ack_decodes, sim.ack_parent_tx_id, observed.flows,
        sim.first_deliveries, sim.destination_flood_decodes,
        observation_cutoff_s=cutoff,
    )
    assessed = assess_flows(
        observed.flows, receptions["attempts"], ack_hops, sim.tx_history,
        observation_cutoff_s=cutoff,
    )
    return {
        "seed": seed,
        "row": stock.row,
        "parity": parity,
        "summary": {**assessed["summary"], **receptions["summary"]},
        "ack_hop_summary": ack_hops["summary"],
        "flows": assessed["flows"],
        "attempts": receptions["attempts"],
        "actions": observed.actions,
        "transmissions": observed.transmissions,
    }


def _source_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in SOURCE_FILES
    }


def validate_smoke_manifest(
    manifest_path: Path, expected_source_sha256: dict[str, str],
    expected_case_sha256: str, deadline_s: float, drain_until_s: float,
) -> dict[str, Any]:
    """Independently verify the 39000 smoke artifacts before exploration."""

    manifest_path = Path(manifest_path)
    if not manifest_path.name.endswith(".manifest.json"):
        raise ValueError("smoke manifest needs a .manifest.json suffix")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            manifest.get("mode") != "smoke"
            or manifest.get("protocol") != PROTOCOL
            or manifest.get("seeds") != list(SMOKE_SEEDS)
            or manifest.get("case_sha256") != expected_case_sha256
            or manifest.get("source_sha256") != expected_source_sha256
            or manifest.get("application_deadline_s") != deadline_s
            or manifest.get("drain_until_s") != drain_until_s
            or manifest.get("parity_exact_all") is not True
        ):
            raise ValueError("smoke manifest differs from the frozen diagnostic")
        names = manifest["artifact_files"]
        hashes = manifest["artifact_sha256"]
        if set(names) != set(ARTIFACT_KEYS) or set(hashes) != set(ARTIFACT_KEYS):
            raise ValueError("smoke manifest is missing required artifacts")
        artifact_paths = {}
        for key in ARTIFACT_KEYS:
            name = names[key]
            if not isinstance(name, str) or Path(name).name != name:
                raise ValueError(f"invalid smoke artifact path: {key}")
            path = manifest_path.parent / name
            if hashlib.sha256(path.read_bytes()).hexdigest() != hashes[key]:
                raise ValueError(f"smoke artifact hash mismatch: {key}")
            artifact_paths[key] = path
        summary = json.loads(artifact_paths["summary"].read_text(encoding="utf-8"))
        if any(summary.get(key) != value for key, value in {
            "mode": "smoke", "protocol": PROTOCOL,
            "seeds": list(SMOKE_SEEDS), "source_sha256": expected_source_sha256,
            "case_sha256": expected_case_sha256,
            "application_deadline_s": deadline_s,
            "drain_until_s": drain_until_s,
        }.items()):
            raise ValueError("smoke summary metadata does not match manifest")
        run_lines = [json.loads(line) for line in
                     artifact_paths["runs"].read_text(encoding="utf-8").splitlines()]
        if len(run_lines) != 1 or run_lines[0].get("seed") != SMOKE_SEEDS[0]:
            raise ValueError("smoke must contain exactly one reserved run")
        run = run_lines[0]
        row = run["row"]
        parity = run["parity"]
        if (
            parity.get("exact") is not True
            or row.get("protocol") != PROTOCOL
            or row.get("seed") != SMOKE_SEEDS[0]
            or row.get("case_config_sha256") != expected_case_sha256
            or row.get("application_deadline_s") != deadline_s
            or row.get("drain_until_s") != drain_until_s
            or row.get("scheduled_unicast_flows", 0) <= 0
            or parity.get("full_row_sha256") != _sha256_json(row)
        ):
            raise ValueError("smoke run or baseline parity metadata is invalid")
        denominator_keys = (
            "scheduled_unicast_flows", "delivered_unacked_flows",
            "delivered_unacked_flood_flows",
        )
        expected_denominators = {
            key: run["summary"][key] for key in denominator_keys
        }
        if (
            manifest.get("per_seed_denominators")
            != {str(SMOKE_SEEDS[0]): expected_denominators}
            or expected_denominators["scheduled_unicast_flows"]
            != row["scheduled_unicast_flows"]
            or any(summary["summary"][key] != value
                   for key, value in expected_denominators.items())
        ):
            raise ValueError("smoke denominators disagree across artifacts")
        flows = [json.loads(line) for line in
                 artifact_paths["flows"].read_text(encoding="utf-8").splitlines()]
        if (len(flows) != row["scheduled_unicast_flows"]
                or any(flow.get("seed") != SMOKE_SEEDS[0] for flow in flows)
                or len({flow.get("flow_id") for flow in flows}) != len(flows)):
            raise ValueError("smoke per-flow artifact does not match denominator")
        actions = [json.loads(line)["action"] for line in
                   artifact_paths["actions"].read_text(encoding="utf-8").splitlines()]
        transmissions = [json.loads(line)["transmission"] for line in
                         artifact_paths["transmissions"].read_text(encoding="utf-8").splitlines()]
        if (
            parity.get("action_trace_sha256") != _sha256_json(actions)
            or parity.get("full_tx_trace_sha256") != _sha256_json(transmissions)
        ):
            raise ValueError("smoke action or TX trace differs from parity hashes")
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("smoke manifest or artifact is unreadable") from exc
    return manifest


def run_report(
    seeds: Sequence[int], case: sr.SrCase = sr.SR_CASES["recurring_fading"],
    mode: str = "smoke", deadline_s: float = 30.0,
    diagnose: Callable[[int, sr.SrCase, float], dict[str, Any]] | None = None,
    smoke_manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Run only preregistered cohorts and aggregate passive observations."""

    if tuple(seeds) != seeds_for_mode(mode):
        raise ValueError(f"{mode} requires its exact preregistered seed cohort")
    if mode == "explore" and smoke_manifest_path is None:
        raise ValueError("exploration requires the independently verified smoke manifest")
    source_sha256 = _source_hashes()
    case_sha256 = _sha256_json(asdict(case))
    smoke_manifest_sha256 = None
    if mode == "explore":
        validate_smoke_manifest(
            smoke_manifest_path, source_sha256, case_sha256,
            deadline_s, case.duration_s + deadline_s,
        )
        smoke_manifest_sha256 = hashlib.sha256(
            Path(smoke_manifest_path).read_bytes()
        ).hexdigest()
    one = diagnose or run_diagnostic
    runs = []
    for seed in seeds:
        run = one(seed, case, deadline_s)
        if run["seed"] != seed or run["parity"]["exact"] is not True:
            raise AssertionError(f"invalid diagnostic replay at seed {seed}")
        if _source_hashes() != source_sha256:
            raise RuntimeError("diagnostic source changed during the cohort")
        runs.append(run)
    count_keys = (
        "scheduled_unicast_flows", "ack_by_deadline", "delivery_by_deadline",
        "delivered_unacked_flows", "delivered_unacked_flood_flows",
        "delivered_unacked_initial_f", "delivered_unacked_r_to_f",
        "valid_off_index_flood_candidates", "flood_ack_final_hop_tx_flows",
        "flood_ack_final_hop_tx_by_deadline_flows",
        "intended_next_hop_attempts", "intended_next_hop_decodes",
        "source_off_index_attempts", "source_off_index_decodes",
    )
    summary = {
        key: sum(run["summary"].get(key, 0) for run in runs)
        for key in count_keys
    }
    for key in ("flood_ack_path_categories", "first_flood_ack_failure_classes"):
        categories: Counter[str] = Counter()
        for run in runs:
            categories.update(run["summary"].get(key, {}))
        summary[key] = dict(sorted(categories.items()))
    denominator = summary["delivered_unacked_flood_flows"]
    valid = summary["valid_off_index_flood_candidates"]
    summary["valid_off_index_flood_candidate_fraction"] = (
        valid / denominator if denominator else None
    )
    summary["candidate_gate_passed"] = (
        valid >= 4 and denominator > 0 and valid / denominator >= 0.10
        if mode == "explore" else None
    )
    return {
        "analysis_type": "passive physical ACK reception under unchanged fixed-2-s control",
        "counterfactual_estimates": None,
        "protocol": PROTOCOL,
        "mode": mode,
        "case": asdict(case),
        "case_sha256": case_sha256,
        "seeds": list(seeds),
        "application_deadline_s": deadline_s,
        "drain_until_s": case.duration_s + deadline_s,
        "source_sha256": source_sha256,
        "smoke_manifest_sha256": smoke_manifest_sha256,
        "summary": summary,
        "runs": runs,
    }


def write_report(report: dict[str, Any], output_prefix: Path) -> dict[str, Path]:
    """Save independently hashable evidence files without replacing earlier runs."""

    prefix = Path(output_prefix)
    paths = {
        "summary": prefix.with_name(prefix.name + ".summary.json"),
        "runs": prefix.with_name(prefix.name + ".runs.jsonl"),
        "flows": prefix.with_name(prefix.name + ".flows.jsonl"),
        "attempts": prefix.with_name(prefix.name + ".attempts.jsonl"),
        "actions": prefix.with_name(prefix.name + ".actions.jsonl"),
        "transmissions": prefix.with_name(prefix.name + ".transmissions.jsonl"),
        "runs_csv": prefix.with_name(prefix.name + ".runs.csv"),
        "manifest": prefix.with_name(prefix.name + ".manifest.json"),
    }
    if prefix.exists() or any(path.exists() for path in paths.values()):
        raise FileExistsError(f"diagnostic output prefix already exists: {prefix}")
    if not all(run["parity"]["exact"] for run in report["runs"]):
        raise AssertionError("cannot save a diagnostic with failed stock parity")
    metadata = {key: value for key, value in report.items() if key != "runs"}

    def json_line(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"

    data: dict[str, bytes] = {}
    data["summary"] = (json.dumps(metadata, sort_keys=True, indent=2) + "\n").encode("utf-8")
    data["runs"] = "".join(json_line({
        key: value for key, value in run.items()
        if key not in {"flows", "attempts", "actions", "transmissions"}
    }) for run in report["runs"]).encode("utf-8")
    data["flows"] = "".join(
        json_line({"seed": run["seed"], **flow})
        for run in report["runs"] for flow in run["flows"]
    ).encode("utf-8")
    data["attempts"] = "".join(
        json_line({"seed": run["seed"], **attempt})
        for run in report["runs"] for attempt in run["attempts"]
    ).encode("utf-8")
    data["actions"] = "".join(
        json_line({"seed": run["seed"], "action": action})
        for run in report["runs"] for action in run["actions"]
    ).encode("utf-8")
    data["transmissions"] = "".join(
        json_line({"seed": run["seed"], "transmission": transmission})
        for run in report["runs"] for transmission in run["transmissions"]
    ).encode("utf-8")
    csv_rows = [
        {**run["row"], **{f"rx_{key}": value for key, value in run["summary"].items()}}
        for run in report["runs"]
    ]
    fieldnames = sorted({key for row in csv_rows for key in row})
    csv_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(csv_rows)
    data["runs_csv"] = csv_buffer.getvalue().encode("utf-8")
    manifest = {
        "mode": report["mode"],
        "protocol": report["protocol"],
        "seeds": report["seeds"],
        "case_sha256": report["case_sha256"],
        "source_sha256": report["source_sha256"],
        "application_deadline_s": report["application_deadline_s"],
        "drain_until_s": report["drain_until_s"],
        "smoke_manifest_sha256": report.get("smoke_manifest_sha256"),
        "parity_exact_all": True,
        "per_seed_denominators": {
            str(run["seed"]): {
                key: run["summary"][key] for key in (
                    "scheduled_unicast_flows", "delivered_unacked_flows",
                    "delivered_unacked_flood_flows",
                )
            }
            for run in report["runs"]
        },
        "artifact_files": {key: paths[key].name for key in data},
        "artifact_sha256": {
            key: hashlib.sha256(content).hexdigest() for key, content in data.items()
        },
    }
    data["manifest"] = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    for name, content in data.items():
        with paths[name].open("xb") as handle:
            handle.write(content)
    return paths


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("smoke", "explore"))
    parser.add_argument("--output-prefix", required=True, type=Path)
    parser.add_argument("--smoke-manifest", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    report = run_report(
        seeds_for_mode(args.mode), mode=args.mode,
        smoke_manifest_path=args.smoke_manifest,
    )
    if _source_hashes() != report["source_sha256"]:
        raise RuntimeError("diagnostic source changed before writing artifacts")
    paths = write_report(report, args.output_prefix)
    print(json.dumps({
        "summary": report["summary"],
        "files": {key: str(path) for key, path in paths.items()},
    }, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
