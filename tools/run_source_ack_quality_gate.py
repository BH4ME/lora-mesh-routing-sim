#!/usr/bin/env python3
"""Artifact gate for the passive source ACK-quality signal screen."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import asdict
from math import floor, isfinite
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_sr_experiment as sr
from lora_mesh_sim import clamp, required_snr_db
from tools.diagnose_source_ack_snr import (
    PROTOCOL, _RUNNER_AUTHORIZATION, run_diagnostic,
)
from tools.source_ack_quality_model import (
    ModelFitError, fit_exploration, score_validation,
)


SMOKE_SEEDS = (43200,)
EXPLORATORY_SEEDS = tuple(range(43001, 43021))
VALIDATION_SEEDS = tuple(range(43101, 43121))
ARTIFACT_KEYS = ("summary", "runs")
CONTRACT_PATH = ROOT / "docs" / "research" / "meshecho_source_ack_snr_signal_gate.md"
SOURCE_FILES = (
    ROOT / "lora_mesh_sim.py",
    ROOT / "tools" / "run_fair_multihop_probe.py",
    ROOT / "tools" / "run_sr_experiment.py",
    ROOT / "tools" / "diagnose_delayed_ack_rx.py",
    ROOT / "tools" / "diagnose_source_ack_snr.py",
    ROOT / "tools" / "source_ack_quality_model.py",
    Path(__file__).resolve(),
    ROOT / "tests" / "test_source_ack_snr.py",
    ROOT / "tests" / "test_source_ack_quality_model.py",
    ROOT / "tests" / "test_source_ack_quality_gate.py",
    CONTRACT_PATH,
)


def _require_frozen_contract() -> None:
    status_lines = [line for line in CONTRACT_PATH.read_text(encoding="utf-8").splitlines()[:15]
                    if "Status:" in line]
    if (len(status_lines) != 1 or not re.search(
        r"\bStatus:\s*frozen\b", status_lines[0], flags=re.IGNORECASE,
    )):
        raise ValueError("ACK-quality contract is not explicitly frozen")


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _source_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in SOURCE_FILES
    }


def _stage_authorization_hash(
    authorization_path: Path | None, *, mode: str, case: sr.SrCase,
    deadline_s: float, source_sha256: dict[str, str],
    predecessors: dict[str, str],
) -> str:
    if authorization_path is None:
        raise ValueError(f"{mode} stage authorization is required")
    data = Path(authorization_path).read_bytes()
    authorization = json.loads(data)
    expected = {
        "mode": mode,
        "seeds": list(seeds_for_mode(mode)),
        "protocol": PROTOCOL,
        "case_sha256": _sha256_json(asdict(case)),
        "application_deadline_s": deadline_s,
        "source_sha256": source_sha256,
        "prerequisite_manifest_sha256": predecessors,
    }
    if authorization != expected:
        raise ValueError(f"{mode} stage authorization differs from frozen inputs")
    return hashlib.sha256(data).hexdigest()


def _require_saved_exploration_authorization_hash(
    explore_manifest_path: Path, authorization_sha256: str,
) -> None:
    manifest = json.loads(Path(explore_manifest_path).read_bytes())
    if manifest.get("stage_authorization_sha256") != authorization_sha256:
        raise ValueError("exploration stage authorization hash differs from saved manifest")


def _summary_from_runs(runs: Sequence[dict[str, Any]]) -> dict[str, Any]:
    rows = [row for run in runs for row in run["cohort"]["rows"]]
    eligible = [row for row in rows if row["q"] is not None]
    age_groups = {"at_most_30": [], "over_30": []}
    interference_groups = {"none": [], "captured": []}
    fading_groups = {"same": [], "different": []}
    for run in runs:
        interval = run["case"]["temporal_fading_interval_s"]
        if not isfinite(interval) or interval <= 0:
            raise ValueError("fading interval must be positive and finite")
        for row in run["cohort"]["rows"]:
            if row["q"] is None:
                continue
            age = row["prior_ack_age_s"]
            if age is None or not isfinite(age) or age < 0:
                raise ValueError("eligible row lacks valid prior ACK age")
            collided = row["prior_ack_collided"]
            if type(collided) is not bool:
                raise ValueError("eligible row lacks prior ACK capture flag")
            prior_ack_end = row["prior_ack_tx_end_s"]
            if (prior_ack_end is None or not isfinite(prior_ack_end)
                    or abs(row["decision_time_s"] - prior_ack_end - age) > 1e-7):
                raise ValueError("eligible row lacks a consistent physical ACK end")
            age_groups["at_most_30" if age <= 30 else "over_30"].append(row)
            interference_groups["captured" if collided else "none"].append(row)
            same = floor(prior_ack_end / interval) == floor(
                row["initial_r_start_s"] / interval
            )
            fading_groups["same" if same else "different"].append(row)

    def group_counts(groups: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        return {
            key: {
                "records": len(part),
                "r_ack_successes": sum(row["initial_r_ack_by_guard"] for row in part),
                "r_ack_misses": sum(not row["initial_r_ack_by_guard"] for row in part),
            }
            for key, part in groups.items()
        }

    return {
        "initial_r_decisions": len(rows),
        "eligible_decisions": len(eligible),
        "missing_q_decisions": len(rows) - len(eligible),
        "initial_r_ack_successes": sum(row["initial_r_ack_by_guard"] for row in rows),
        "initial_r_ack_misses": sum(not row["initial_r_ack_by_guard"] for row in rows),
        "later_recovery_attempts": sum(row["later_recovery_attempted"] for row in rows),
        "later_recovery_ack_successes": sum(
            row["later_recovery_ack_by_deadline"] for row in rows
        ),
        "eligible_r_ack_successes": sum(row["initial_r_ack_by_guard"] for row in eligible),
        "eligible_r_ack_misses": sum(not row["initial_r_ack_by_guard"] for row in eligible),
        "eligible_diagnostics": {
            "ack_age_s": group_counts(age_groups),
            "prior_ack_interference": group_counts(interference_groups),
            "fading_block": group_counts(fading_groups),
        },
        "by_seed": {
            str(run["seed"]): {
                "initial_r_decisions": len(run["cohort"]["rows"]),
                "eligible_decisions": sum(
                    row["q"] is not None for row in run["cohort"]["rows"]
                ),
                "eligible_r_ack_successes": sum(
                    row["q"] is not None and row["initial_r_ack_by_guard"]
                    for row in run["cohort"]["rows"]
                ),
                "eligible_r_ack_misses": sum(
                    row["q"] is not None and not row["initial_r_ack_by_guard"]
                    for row in run["cohort"]["rows"]
                ),
                "full_r_ack_successes": sum(
                    row["initial_r_ack_by_guard"]
                    for row in run["cohort"]["rows"]
                ),
                "full_r_ack_misses": sum(
                    not row["initial_r_ack_by_guard"]
                    for row in run["cohort"]["rows"]
                ),
            }
            for run in runs
        },
        "exclusions": sum(len(run["cohort"]["exclusions"]) for run in runs),
        "by_path_type": {
            path_type: {
                "initial_r_decisions": sum(row["path_type"] == path_type for row in rows),
                "eligible_decisions": sum(row["path_type"] == path_type for row in eligible),
                "full_r_ack_successes": sum(
                    row["path_type"] == path_type and row["initial_r_ack_by_guard"]
                    for row in rows
                ),
                "full_r_ack_misses": sum(
                    row["path_type"] == path_type and not row["initial_r_ack_by_guard"]
                    for row in rows
                ),
                "later_recovery_attempts": sum(
                    row["path_type"] == path_type and row["later_recovery_attempted"]
                    for row in rows
                ),
                "later_recovery_ack_successes": sum(
                    row["path_type"] == path_type
                    and row["later_recovery_ack_by_deadline"] for row in rows
                ),
                "eligible_r_ack_successes": sum(
                    row["path_type"] == path_type and row["initial_r_ack_by_guard"]
                    for row in eligible
                ),
                "eligible_r_ack_misses": sum(
                    row["path_type"] == path_type and not row["initial_r_ack_by_guard"]
                    for row in eligible
                ),
            }
            for path_type in ("direct", "multihop")
        },
    }


def _model_rows(runs: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"seed": run["seed"], **row}
        for run in runs for row in run["cohort"]["rows"]
    ]


def _json_value(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


def _fit_saved_exploration(
    runs: Sequence[dict[str, Any]], seeds: Sequence[int],
    *, quality_field: str = "q",
) -> dict[str, Any]:
    try:
        return _json_value(fit_exploration(
            _model_rows(runs), seeds, quality_field=quality_field,
        ))
    except ModelFitError as error:
        return {
            "status": "no_go", "reason": str(error),
            "support": {"ready_for_validation": False},
            "quality_field": quality_field,
        }


def _audit_saved_model(report: dict[str, Any]) -> None:
    mode = report["mode"]
    fit = report["exploration_fit"]
    score = report["validation_score"]
    sensitivity_fit = report["sensitivity_fit"]
    sensitivity_score = report["sensitivity_validation_score"]
    if mode == "explore":
        if (score is not None or sensitivity_score is not None
                or fit != _fit_saved_exploration(report["runs"], report["seeds"])
                or sensitivity_fit != _fit_saved_exploration(
                    report["runs"], report["seeds"], quality_field="q_clean",
                )):
            raise ValueError("exploration model differs from saved cohort rows")
    elif mode == "validation":
        if (not isinstance(fit, dict)
                or fit["support"]["ready_for_validation"] is not True
                or not isinstance(sensitivity_fit, dict)):
            raise ValueError("validation lacks a frozen exploration model")
        expected = _json_value(score_validation(
            _model_rows(report["runs"]), report["seeds"], fit,
        ))
        expected_sensitivity = _json_value(score_validation(
            _model_rows(report["runs"]), report["seeds"], sensitivity_fit,
            quality_field="q_clean",
        ))
        if score != expected or sensitivity_score != expected_sensitivity:
            raise ValueError("validation score differs from saved cohort rows")
    elif any(value is not None for value in
             (fit, score, sensitivity_fit, sensitivity_score)):
        raise ValueError("non-model split contains an exploration model or score")


def _verify_run_evidence(run: dict[str, Any], protocol: str) -> None:
    parity = run["parity"]
    if (parity.get("exact") is not True
            or run.get("strict_replay_exact") is not True
            or run["protocol"] != protocol
            or run["row"]["scheduled_trace_sha256"]
            != parity["scheduled_trace_sha256"]
            or _sha256_json(run["row"]) != parity["full_row_sha256"]
            or _sha256_json(run["flows"]) != parity["flow_trace_sha256"]
            or _sha256_json(run["actions"]) != parity["action_trace_sha256"]
            or _sha256_json(run["transmissions"])
            != parity["full_tx_trace_sha256"]
            or len(run["flows"]) != run["row"]["scheduled_unicast_flows"]):
        raise ValueError(f"run {run.get('seed')} parity/replay evidence differs")


def _audit_saved_ack_rows(run: dict[str, Any]) -> None:
    """Tie every saved successful source decode to a physical TX and action."""

    tx_by_id = {tx["tx_id"]: tx for tx in run["transmissions"]}
    if len(tx_by_id) != len(run["transmissions"]):
        raise ValueError("duplicate physical TX IDs in saved ACK-quality run")
    action_orders = set()
    ack_tx_ids = set()
    for ack in run["ack_rows"]:
        tx_id, order = ack["tx_id"], ack["action_order"]
        if tx_id in ack_tx_ids or order in action_orders:
            raise ValueError("duplicate source ACK physical/action join")
        ack_tx_ids.add(tx_id)
        action_orders.add(order)
        tx = tx_by_id.get(tx_id)
        if tx is None or not 0 <= order < len(run["actions"]):
            raise ValueError("source ACK physical/action join is missing")
        packet, action = tx["packet"], run["actions"][order]
        if (packet["kind"] != "ACK"
                or action["event"] != "dhr_source_ack_rx"
                or action["accepted"] is not ack["accepted"]
                or action["flow_id"] != packet["flow_id"]
                or action["src"] != packet["final_dst"]
                or action["dst"] != packet["origin"]
                or action["repair_index"] != packet["repair_index"]
                or abs(action["time"] - tx["end"]) > 1e-7
                or ack["tx_end_s"] != tx["end"]
                or ack["flow_id"] != packet["flow_id"]
                or ack["source"] != packet["final_dst"]
                or ack["destination"] != packet["origin"]
                or ack["sender"] != tx["sender"]
                or ack["path"] != packet["path"]
                or ack["path_index"] != packet["path_index"]
                or ack["repair_index"] != packet["repair_index"]
                or type(ack["accepted"]) is not bool
                or type(ack["collided"]) is not bool
                or not all(isfinite(ack[key]) for key in ("sinr_db", "snr_db"))):
            raise ValueError("source ACK saved row differs from physical/action trace")
        if ack["accepted"] and not (
            packet["path_index"] == 0
            and len(packet["path"]) >= 2
            and packet["path"][0] == ack["source"]
            and packet["path"][-1] == ack["destination"]
            and tx["sender"] == packet["path"][1]
            and packet["request_id"] == packet["flow_id"]
            and packet["protocol"] == PROTOCOL
        ):
            raise ValueError("accepted source ACK saved path is invalid")
    source_actions = {
        order for order, action in enumerate(run["actions"])
        if action["event"] == "dhr_source_ack_rx"
    }
    if action_orders != source_actions:
        raise ValueError("saved ACK rows do not cover source decode actions")


def _recompute_saved_cohort(
    run: dict[str, Any], deadline_s: float, sf: int,
) -> dict[str, list[dict[str, Any]]]:
    """Independently reconstruct the initial-R denominator and prior-only q."""

    actions = run["actions"]
    ack_rows = run["ack_rows"]
    flows = {flow["flow_id"]: flow for flow in run["flows"]}
    rows: list[dict[str, Any]] = []
    exclusions: list[dict[str, Any]] = []
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
        flow = flows.get(flow_id)
        if flow is None:
            exclusions.append({"flow_id": flow_id, "reason": "unregistered_flow"})
            continue
        deadline_at = flow["enqueued_at"] + deadline_s
        if flow["deadline_at"] != deadline_at:
            raise ValueError("saved flow application deadline differs")
        starts = [
            tx for tx in run["transmissions"]
            if tx["packet"]["kind"] == "DATA"
            and tx["packet"]["repair_index"] is None
            and tx["packet"]["flow_id"] == flow_id
            and tx["packet"]["origin"] == source
            and tx["packet"]["final_dst"] == destination
            and tx["sender"] == source and tx["start"] < deadline_at
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
        path = initial_tx["packet"]["path"]
        intervening_commit = any(
            action["event"] == "commit"
            and action["src"] == source and action["dst"] == destination
            and decision_order < order and action["time"] <= initial_tx["start"]
            for order, action in enumerate(actions)
        )
        feature_exclusion_reason = (
            "no_prior_commit" if commit is None else
            "path_changed_before_tx" if path != commit["path"] else
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
        prior_candidates = [
            ack for ack in ack_rows
            if feature_exclusion_reason is None
            and ack["accepted"]
            and belongs_to_generation(ack)
            and generation_order < ack["action_order"] < decision_order
            and ack["tx_end_s"] < decision["time"]
            and ack["source"] == source and ack["destination"] == destination
            and ack["path"] == path and ack["sender"] == path[1]
        ]
        prior_ack = max(
            prior_candidates,
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
        guard_end_s = min(initial_tx["start"] + 15.0, deadline_at)
        ack_by_guard = any(
            ack["accepted"] and ack["repair_index"] is None
            and ack["flow_id"] == flow_id
            and ack["source"] == source and ack["destination"] == destination
            and ack["path"] == path and ack["tx_end_s"] <= guard_end_s
            for ack in ack_rows
        )
        recovery_actions = [
            action for action in actions
            if action["event"] == "dhr_recovery_tx"
            and action["flow_id"] == flow_id
            and action["src"] == source and action["dst"] == destination
            and initial_tx["start"] < action["time"] < deadline_at
        ]
        recovery_starts = [
            tx for tx in run["transmissions"]
            if tx["packet"]["flow_id"] == flow_id
            and tx["packet"]["origin"] == source
            and tx["packet"]["final_dst"] == destination
            and tx["packet"]["request_id"] == flow_id
            and (tx["packet"]["kind"], tx["packet"]["repair_index"])
            in {("DATA", 1), ("FLOOD", 2)}
            and tx["sender"] == source
            and initial_tx["start"] < tx["start"] < deadline_at
        ]
        matched_recovery_tx_ids: set[int] = set()
        for action in recovery_actions:
            matches = [
                tx for tx in recovery_starts
                if abs(tx["start"] - action["time"]) <= 1e-7
                and abs(tx["end"] - action["end"]) <= 1e-7
                and tx["packet"]["repair_index"] == action["repair_index"]
                and action["action"] == (
                    "R" if tx["packet"]["repair_index"] == 1 else "F"
                )
            ]
            if len(matches) != 1 or matches[0]["tx_id"] in matched_recovery_tx_ids:
                raise ValueError("recovery action has no unique physical TX")
            matched_recovery_tx_ids.add(matches[0]["tx_id"])
        if matched_recovery_tx_ids != {tx["tx_id"] for tx in recovery_starts}:
            raise ValueError("recovery physical TX has no unique action")
        recovery_markers = {
            tx["packet"]["repair_index"] for tx in recovery_starts
        }
        later_recovery_ack = any(
            ack["accepted"] and ack["repair_index"] in recovery_markers
            and ack["flow_id"] == flow_id
            and ack["source"] == source and ack["destination"] == destination
            and ack["tx_end_s"] <= deadline_at
            and any(tx["packet"]["repair_index"] == ack["repair_index"]
                    and tx["start"] < ack["tx_end_s"] for tx in recovery_starts)
            for ack in ack_rows
        )
        q = None if prior_ack is None else int(clamp(
            round(2 * (prior_ack["sinr_db"] - required_snr_db(sf))),
            -126, 126,
        ))
        rows.append({
            "flow_id": flow_id, "source": source,
            "destination": destination,
            "decision_order": decision_order,
            "decision_time_s": decision["time"],
            "initial_r_tx_id": initial_tx["tx_id"],
            "initial_r_start_s": initial_tx["start"],
            "route_generation_flow_id": commit["flow_id"] if commit else None,
            "feature_exclusion_reason": feature_exclusion_reason,
            "path": path,
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
                    prior_ack["snr_db"] - required_snr_db(sf)
                )), -126, 126)) if prior_ack else None
            ),
            "prior_ack_collided": prior_ack["collided"] if prior_ack else None,
            "prior_r_miss": int(prior_r_miss),
            "initial_r_ack_by_guard": ack_by_guard,
            "later_recovery_attempted": bool(recovery_starts),
            "later_recovery_ack_by_deadline": later_recovery_ack,
            "destination_delivery_by_deadline": (
                flow["delivered_at"] is not None
                and flow["delivered_at"] <= deadline_at
            ),
        })
    return {"rows": rows, "exclusions": exclusions}


def _audit_saved_run(
    run: dict[str, Any], *, protocol: str, deadline_s: float, sf: int,
) -> None:
    _verify_run_evidence(run, protocol)
    _audit_saved_ack_rows(run)
    if _recompute_saved_cohort(run, deadline_s, sf) != run["cohort"]:
        raise ValueError(f"run {run['seed']} cohort differs from saved causal evidence")


def _artifact_paths(prefix: Path) -> dict[str, Path]:
    return {
        "summary": prefix.with_name(prefix.name + ".summary.json"),
        "runs": prefix.with_name(prefix.name + ".runs.jsonl"),
        "manifest": prefix.with_name(prefix.name + ".manifest.json"),
        "manifest_sha256": prefix.with_name(prefix.name + ".manifest.sha256"),
    }


def write_report(report: dict[str, Any], output_prefix: Path) -> dict[str, Path]:
    """Save every diagnostic field with SHA-256 descriptors, without overwrite."""

    prefix = Path(output_prefix)
    paths = _artifact_paths(prefix)
    if prefix.exists() or any(path.exists() for path in paths.values()):
        raise FileExistsError(f"ACK-quality output prefix already exists: {prefix}")
    if _source_hashes() != report["source_sha256"]:
        raise RuntimeError("diagnostic source changed before artifact writing")
    if [run["seed"] for run in report["runs"]] != report["seeds"]:
        raise ValueError("report runs and seeds differ")
    for run in report["runs"]:
        _audit_saved_run(
            run, protocol=report["protocol"],
            deadline_s=report["application_deadline_s"],
            sf=report["case"]["sf"],
        )
    if _summary_from_runs(report["runs"]) != report["summary"]:
        raise ValueError("summary differs from raw cohort rows")
    _audit_saved_model(report)

    def json_line(value: Any) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          allow_nan=False) + "\n"

    metadata = {key: value for key, value in report.items() if key != "runs"}
    data = {
        "summary": (json.dumps(metadata, sort_keys=True, indent=2,
                               allow_nan=False) + "\n").encode("utf-8"),
        "runs": "".join(json_line(run) for run in report["runs"]).encode("utf-8"),
    }
    manifest = {
        "mode": report["mode"], "protocol": report["protocol"],
        "seeds": report["seeds"], "case_sha256": report["case_sha256"],
        "application_deadline_s": report["application_deadline_s"],
        "drain_until_s": report["drain_until_s"],
        "python_minor": report["python_minor"],
        "source_sha256": report["source_sha256"],
        "prerequisite_manifest_sha256": report["prerequisite_manifest_sha256"],
        "stage_authorization_sha256": report["stage_authorization_sha256"],
        "summary": report["summary"],
        "exploration_fit": report["exploration_fit"],
        "validation_score": report["validation_score"],
        "sensitivity_fit": report["sensitivity_fit"],
        "sensitivity_validation_score": report["sensitivity_validation_score"],
        "artifacts": {
            key: {"file": paths[key].name,
                  "sha256": hashlib.sha256(data[key]).hexdigest()}
            for key in ARTIFACT_KEYS
        },
    }
    manifest_data = (json.dumps(manifest, sort_keys=True, indent=2,
                                allow_nan=False) + "\n").encode("utf-8")
    sidecar_data = (
        hashlib.sha256(manifest_data).hexdigest()
        + "  " + paths["manifest"].name + "\n"
    ).encode("ascii")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    for key in ARTIFACT_KEYS:
        with paths[key].open("xb") as output:
            output.write(data[key])
    with paths["manifest"].open("xb") as output:
        output.write(manifest_data)
    with paths["manifest_sha256"].open("xb") as output:
        output.write(sidecar_data)
    return paths


def validate_manifest(
    manifest_path: Path, *, expected_mode: str, case: sr.SrCase,
    deadline_s: float = 30.0,
    smoke_manifest_path: Path | None = None,
    explore_manifest_path: Path | None = None,
    stage_authorization_path: Path | None = None,
    explore_authorization_path: Path | None = None,
    replay: bool = False,
) -> dict[str, Any]:
    """Audit frozen inputs, causal rows and actual predecessor manifests."""

    path = Path(manifest_path)
    if expected_mode in {"explore", "validation"} and smoke_manifest_path is None:
        raise ValueError("exploration and validation require the actual smoke manifest")
    if expected_mode == "validation" and explore_manifest_path is None:
        raise ValueError("validation requires the actual exploration manifest")
    if expected_mode != "synthetic":
        if not replay:
            raise ValueError("real manifest validation requires explicit replay")
        _require_frozen_contract()
    manifest_data = path.read_bytes()
    sidecar = path.with_suffix(".sha256")
    if sidecar.read_text(encoding="ascii") != (
        hashlib.sha256(manifest_data).hexdigest() + "  " + path.name + "\n"
    ):
        raise ValueError("manifest SHA-256 sidecar differs")
    manifest = json.loads(manifest_data)
    if (manifest["mode"] != expected_mode
            or manifest["protocol"] != PROTOCOL
            or manifest["source_sha256"] != _source_hashes()
            or manifest["case_sha256"] != _sha256_json(asdict(case))
            or manifest["application_deadline_s"] != deadline_s
            or manifest["drain_until_s"] != case.duration_s + deadline_s
            or manifest["python_minor"] != list(sys.version_info[:2])
            or set(manifest["artifacts"]) != set(ARTIFACT_KEYS)):
        raise ValueError("manifest source, case, deadline or protocol differs")
    predecessors = manifest["prerequisite_manifest_sha256"]
    if expected_mode in {"explore", "validation"}:
        actual_smoke_hash = hashlib.sha256(
            Path(smoke_manifest_path).read_bytes()
        ).hexdigest()
        expected_predecessors = {"smoke_manifest": actual_smoke_hash}
        if expected_mode == "validation":
            if explore_authorization_path is None:
                raise ValueError("exploration stage authorization is required")
            expected_predecessors["explore_manifest"] = hashlib.sha256(
                Path(explore_manifest_path).read_bytes()
            ).hexdigest()
            explore_authorization_sha256 = _stage_authorization_hash(
                explore_authorization_path, mode="explore", case=case,
                deadline_s=deadline_s, source_sha256=_source_hashes(),
                predecessors={"smoke_manifest": actual_smoke_hash},
            )
            _require_saved_exploration_authorization_hash(
                explore_manifest_path, explore_authorization_sha256,
            )
        stage_hash = _stage_authorization_hash(
            stage_authorization_path, mode=expected_mode, case=case,
            deadline_s=deadline_s, source_sha256=_source_hashes(),
            predecessors=expected_predecessors,
        )
        if manifest.get("stage_authorization_sha256") != stage_hash:
            raise ValueError("manifest stage authorization differs")
    elif expected_mode in {"smoke", "synthetic"}:
        if manifest.get("stage_authorization_sha256") is not None:
            raise ValueError("smoke/synthetic manifest has stage authorization")
    if expected_mode in {"explore", "validation"}:
        validate_manifest(
            smoke_manifest_path, expected_mode="smoke", case=case,
            deadline_s=deadline_s, replay=replay,
        )
        actual_smoke_hash = hashlib.sha256(
            Path(smoke_manifest_path).read_bytes()
        ).hexdigest()
        if predecessors.get("smoke_manifest") != actual_smoke_hash:
            raise ValueError("smoke manifest link differs")
    elif predecessors:
        raise ValueError("smoke/synthetic report cannot name a predecessor")
    if expected_mode == "validation":
        explore_report = validate_manifest(
            explore_manifest_path, expected_mode="explore", case=case,
            deadline_s=deadline_s, smoke_manifest_path=smoke_manifest_path,
            stage_authorization_path=explore_authorization_path,
            replay=replay,
        )
        actual_explore_hash = hashlib.sha256(
            Path(explore_manifest_path).read_bytes()
        ).hexdigest()
        if predecessors.get("explore_manifest") != actual_explore_hash:
            raise ValueError("exploration manifest link differs")
    elif expected_mode == "explore" and set(predecessors) != {"smoke_manifest"}:
        raise ValueError("exploration predecessor keys differ")
    if expected_mode != "synthetic" and tuple(manifest["seeds"]) != seeds_for_mode(expected_mode):
        raise ValueError("manifest seeds differ from exact frozen cohort")
    data = {}
    for key in ARTIFACT_KEYS:
        descriptor = manifest["artifacts"][key]
        artifact_path = path.parent / descriptor["file"]
        if artifact_path.parent != path.parent or artifact_path.name != descriptor["file"]:
            raise ValueError(f"artifact path escapes manifest directory: {key}")
        data[key] = artifact_path.read_bytes()
        if hashlib.sha256(data[key]).hexdigest() != descriptor["sha256"]:
            raise ValueError(f"artifact SHA-256 differs: {key}")
    report = json.loads(data["summary"])
    report["runs"] = [json.loads(line) for line in data["runs"].splitlines()]
    if ([run["seed"] for run in report["runs"]] != manifest["seeds"]
            or report["seeds"] != manifest["seeds"]
            or report["case"] != asdict(case)
            or report["case_sha256"] != manifest["case_sha256"]
            or report["source_sha256"] != manifest["source_sha256"]
            or report["protocol"] != manifest["protocol"]
            or report["python_minor"] != manifest["python_minor"]
            or report["application_deadline_s"] != deadline_s
            or report["drain_until_s"] != manifest["drain_until_s"]
            or report["mode"] != manifest["mode"]
            or report["summary"] != manifest["summary"]
            or report["exploration_fit"] != manifest["exploration_fit"]
            or report["validation_score"] != manifest["validation_score"]
            or report["sensitivity_fit"] != manifest["sensitivity_fit"]
            or report["sensitivity_validation_score"]
            != manifest["sensitivity_validation_score"]
            or report["prerequisite_manifest_sha256"]
            != manifest["prerequisite_manifest_sha256"]
            or report["stage_authorization_sha256"]
            != manifest["stage_authorization_sha256"]):
        raise ValueError("manifest and saved report metadata differ")
    if (expected_mode == "validation"
            and report["exploration_fit"] != explore_report["exploration_fit"]):
        raise ValueError("validation model differs from actual exploration manifest")
    if (expected_mode == "validation"
            and report["sensitivity_fit"] != explore_report["sensitivity_fit"]):
        raise ValueError("validation sensitivity model differs from actual exploration manifest")
    for run in report["runs"]:
        if run["case"] != asdict(case):
            raise ValueError(f"run {run['seed']} case differs")
        _audit_saved_run(
            run, protocol=report["protocol"], deadline_s=deadline_s,
            sf=case.sf,
        )
    if _summary_from_runs(report["runs"]) != report["summary"]:
        raise ValueError("summary differs from saved cohort rows")
    _audit_saved_model(report)
    if expected_mode != "synthetic":
        for run in report["runs"]:
            replay = _json_value(run_diagnostic(
                run["seed"], case, deadline_s,
                research_authorization=_RUNNER_AUTHORIZATION,
            ))
            if replay != run:
                raise ValueError(
                    f"run {run['seed']} differs from independent replay"
                )
    return report


def seeds_for_mode(mode: str) -> tuple[int, ...]:
    if mode == "smoke":
        return SMOKE_SEEDS
    if mode == "explore":
        return EXPLORATORY_SEEDS
    if mode == "validation":
        return VALIDATION_SEEDS
    raise ValueError(f"unknown ACK-quality mode: {mode}")


def run_report(
    seeds: Sequence[int], *, mode: str = "synthetic",
    case: sr.SrCase = sr.SR_CASES["recurring_fading"],
    deadline_s: float = 30.0,
    smoke_manifest_path: Path | None = None,
    explore_manifest_path: Path | None = None,
    stage_authorization_path: Path | None = None,
    explore_authorization_path: Path | None = None,
) -> dict[str, Any]:
    seed_tuple = tuple(seeds)
    if not seed_tuple or len(set(seed_tuple)) != len(seed_tuple):
        raise ValueError("seeds must be nonempty and unique")
    if mode == "synthetic":
        if any(35001 <= seed <= 35040 or 36001 <= seed <= 36040
               or 42000 <= seed <= 42020 or 42101 <= seed <= 42120
               or 43000 <= seed <= 43020 or 43101 <= seed <= 43120
               or seed == 43200
               for seed in seed_tuple):
            raise ValueError("synthetic mode cannot open reserved ACK-quality seeds")
    elif seed_tuple != seeds_for_mode(mode):
        raise ValueError(f"{mode} requires its exact frozen cohort")
    if mode != "synthetic":
        if case != sr.SR_CASES["recurring_fading"] or deadline_s != 30.0:
            raise ValueError("real ACK-quality cohorts require frozen case and deadline")
        _require_frozen_contract()
    source_sha256 = _source_hashes()
    prerequisite_sha256: dict[str, str] = {}
    stage_authorization_sha256 = None
    if mode in {"explore", "validation"}:
        if smoke_manifest_path is None:
            raise ValueError("exploration and validation require a verified smoke manifest")
        prerequisite_sha256["smoke_manifest"] = hashlib.sha256(
            Path(smoke_manifest_path).read_bytes()
        ).hexdigest()
        if mode == "validation":
            if explore_manifest_path is None:
                raise ValueError("validation requires a verified exploration manifest")
            if explore_authorization_path is None:
                raise ValueError("validation requires exploration stage authorization")
            prerequisite_sha256["explore_manifest"] = hashlib.sha256(
                Path(explore_manifest_path).read_bytes()
            ).hexdigest()
            explore_authorization_sha256 = _stage_authorization_hash(
                explore_authorization_path, mode="explore", case=case,
                deadline_s=deadline_s, source_sha256=source_sha256,
                predecessors={
                    "smoke_manifest": prerequisite_sha256["smoke_manifest"],
                },
            )
            _require_saved_exploration_authorization_hash(
                explore_manifest_path, explore_authorization_sha256,
            )
        stage_authorization_sha256 = _stage_authorization_hash(
            stage_authorization_path, mode=mode, case=case,
            deadline_s=deadline_s, source_sha256=source_sha256,
            predecessors=prerequisite_sha256,
        )
        validate_manifest(
            smoke_manifest_path, expected_mode="smoke", case=case,
            deadline_s=deadline_s, replay=True,
        )
    explore_report = None
    if mode == "validation":
        explore_report = validate_manifest(
            explore_manifest_path, expected_mode="explore", case=case,
            deadline_s=deadline_s, smoke_manifest_path=smoke_manifest_path,
            stage_authorization_path=explore_authorization_path,
            replay=True,
        )
        if (explore_report["prerequisite_manifest_sha256"].get("smoke_manifest")
                != prerequisite_sha256["smoke_manifest"]):
            raise ValueError("exploration manifest belongs to a different smoke run")
        if explore_report["exploration_fit"]["support"]["ready_for_validation"] is not True:
            raise ValueError("exploration support/model gate did not authorize validation")
        if (not isinstance(explore_report["sensitivity_fit"], dict)
                or explore_report["sensitivity_fit"].get("status") == "no_go"
                or explore_report["sensitivity_fit"]["support"]["ready_for_validation"]
                is not True):
            raise ValueError("exploration sensitivity model did not authorize validation")
    runs = []
    for seed in seed_tuple:
        run = run_diagnostic(
            seed, case, deadline_s,
            research_authorization=(
                _RUNNER_AUTHORIZATION if mode != "synthetic" else None
            ),
        )
        if (run["seed"] != seed or run["case"] != asdict(case)
                or run["protocol"] != PROTOCOL
                or run["parity"]["exact"] is not True
                or run["strict_replay_exact"] is not True):
            raise AssertionError(f"ACK-quality parity or replay failed at seed {seed}")
        if _source_hashes() != source_sha256:
            raise RuntimeError("diagnostic source changed during the cohort")
        runs.append(json.loads(json.dumps(run, allow_nan=False)))
    exploration_fit = (
        _fit_saved_exploration(runs, seed_tuple) if mode == "explore" else None
    )
    sensitivity_fit = (
        _fit_saved_exploration(runs, seed_tuple, quality_field="q_clean")
        if mode == "explore" else None
    )
    validation_score = (
        _json_value(score_validation(
            _model_rows(runs), seed_tuple, explore_report["exploration_fit"],
        )) if mode == "validation" else None
    )
    sensitivity_validation_score = (
        _json_value(score_validation(
            _model_rows(runs), seed_tuple, explore_report["sensitivity_fit"],
            quality_field="q_clean",
        )) if mode == "validation" else None
    )
    return {
        "analysis_type": "passive source ACK quality under fixed DHR control",
        "mode": mode, "protocol": PROTOCOL,
        "case": asdict(case), "case_sha256": _sha256_json(asdict(case)),
        "seeds": list(seed_tuple), "application_deadline_s": deadline_s,
        "drain_until_s": case.duration_s + deadline_s,
        "python_minor": list(sys.version_info[:2]),
        "source_sha256": source_sha256,
        "prerequisite_manifest_sha256": prerequisite_sha256,
        "stage_authorization_sha256": stage_authorization_sha256,
        "summary": _summary_from_runs(runs),
        "exploration_fit": (
            explore_report["exploration_fit"] if mode == "validation"
            else exploration_fit
        ),
        "validation_score": validation_score,
        "sensitivity_fit": (
            explore_report["sensitivity_fit"] if mode == "validation"
            else sensitivity_fit
        ),
        "sensitivity_validation_score": sensitivity_validation_score,
        "runs": runs,
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", required=True, choices=("smoke", "explore", "validation"),
    )
    parser.add_argument("--output-prefix", required=True, type=Path)
    parser.add_argument("--smoke-manifest", type=Path)
    parser.add_argument("--explore-manifest", type=Path)
    parser.add_argument("--stage-authorization", type=Path)
    parser.add_argument("--explore-authorization", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    prefix = args.output_prefix
    if prefix.exists() or any(
        path.exists() for path in _artifact_paths(prefix).values()
    ):
        raise FileExistsError(f"ACK-quality output prefix already exists: {prefix}")
    report = run_report(
        seeds_for_mode(args.mode), mode=args.mode,
        smoke_manifest_path=args.smoke_manifest,
        explore_manifest_path=args.explore_manifest,
        stage_authorization_path=args.stage_authorization,
        explore_authorization_path=args.explore_authorization,
    )
    if _source_hashes() != report["source_sha256"]:
        raise RuntimeError("diagnostic source changed before artifact writing")
    paths = write_report(report, prefix)
    print(json.dumps({
        "artifacts": {key: str(path) for key, path in paths.items()},
        "summary": report["summary"],
        "exploration_support": (
            report["exploration_fit"]["support"]
            if args.mode == "explore" else None
        ),
        "validation_gate": (
            report["validation_score"]["gate"]
            if args.mode == "validation" else None
        ),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
