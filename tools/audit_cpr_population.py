#!/usr/bin/env python3
"""Independently audit CPR development or holdout population artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_cpr_experiment as cpr  # noqa: E402
from tools.run_drc_population import nominal_ci95  # noqa: E402


POPULATION_CONTRACT = ROOT / "docs" / "research" / "meshecho_cpr_population_contract_20261006.md"
ARMS = cpr.CPR_PROTOCOLS
CANDIDATE = "meshecho-cpr"
CONTROL_NO_CANCEL = "meshecho-cpr-nocancel"
CONTROL_NO_RESCUE = "meshecho-drc-no-rescue"
EXPECTED_SEEDS = {
    "development": tuple(range(92200, 92220)),
    "holdout": tuple(range(92300, 92320)),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonl(path: Path) -> List[Dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _load(manifest_path: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    manifest = cpr.audit_artifacts(manifest_path)
    prefix = Path(str(manifest_path)[:-len(".manifest.json")])
    runs = list(csv.DictReader((Path(f"{prefix}.runs.csv")).open(newline="", encoding="utf-8")))
    flows = _jsonl(Path(f"{prefix}.flows.jsonl"))
    actions = _jsonl(Path(f"{prefix}.actions.jsonl"))
    requests = _jsonl(Path(f"{prefix}.requests.jsonl"))
    return manifest, runs, flows, actions, requests


def _validate_stage(manifest: Mapping[str, Any], runs: Sequence[Mapping[str, Any]], stage: str) -> None:
    if manifest.get("experiment_stage") != stage or manifest.get("seed_split") != stage:
        raise ValueError("CPR manifest stage does not match audit stage")
    if tuple(sorted(int(seed) for seed in manifest.get("seeds", []))) != EXPECTED_SEEDS[stage]:
        raise ValueError("CPR population seed list differs from frozen contract")
    if tuple(manifest.get("protocols", [])) != ARMS:
        raise ValueError("CPR population arm order differs from frozen contract")
    if manifest.get("case", {}).get("key") != cpr.CASE_PROFILES["exposure"].key:
        raise ValueError("CPR population case is not the frozen exposure profile")
    if len(runs) != len(EXPECTED_SEEDS[stage]) * len(ARMS):
        raise ValueError("CPR population run count is incomplete")
    scopes = {(int(row["seed"]), str(row["protocol"])) for row in runs}
    expected = {(seed, arm) for seed in EXPECTED_SEEDS[stage] for arm in ARMS}
    if scopes != expected:
        raise ValueError("CPR population run scopes are incomplete")
    for seed in EXPECTED_SEEDS[stage]:
        rows = [row for row in runs if int(row["seed"]) == seed]
        for field in ("case_sha256", "scheduled_trace_sha256", "topology_sha256", "radio_sha256", "pair_pool_sha256"):
            if len({row[field] for row in rows}) != 1:
                raise ValueError(f"paired identity mismatch for seed {seed}: {field}")


def _validate_development_report(report_path: Path) -> Dict[str, Any]:
    report_path = Path(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if (
        report.get("schema") != "meshecho-cpr-population-audit-v1"
        or report.get("stage") != "development"
        or report.get("passed") is not True
    ):
        raise ValueError("development report is not a passed CPR population audit")
    manifest_path = Path(str(report.get("manifest", "")))
    if not manifest_path.exists():
        raise ValueError("development report references a missing manifest")
    if report.get("manifest_sha256") != _sha256(manifest_path):
        raise ValueError("development manifest changed after the gate report")
    if not all(report.get("checks", {}).values()):
        raise ValueError("development report contains a failed check")
    return report


def _started_action_counts(actions: Sequence[Mapping[str, Any]], requests: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    request_kind = {
        "R_INITIAL": "CPR_REQUEST",
        "R_REPEAT": "CPR_REPEAT_REQUEST",
        "F_RECOVERY": "CPR_RECOVERY_REQUEST",
    }
    started = Counter()
    for action in actions:
        if (
            action.get("protocol") != CANDIDATE
            or action.get("event") != "decision"
            or action.get("action") not in request_kind
        ):
            continue
        key = (int(action["seed"]), int(action["flow_id"]))
        if any(
            int(request["seed"]) == key[0]
            and request.get("protocol") == CANDIDATE
            and int(request["flow_id"]) == key[1]
            and request.get("packet_kind") == request_kind[action["action"]]
            and request.get("status") == "started"
            for request in requests
        ):
            started[str(action["action"])] += 1
    return dict(started)


def _paired_summary(runs: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    by_key = {(int(row["seed"]), str(row["protocol"])): row for row in runs}
    seeds = sorted({int(row["seed"]) for row in runs})
    result: List[Dict[str, Any]] = []
    for comparator in (CONTROL_NO_CANCEL, CONTROL_NO_RESCUE):
        ack = [
            float(by_key[(seed, CANDIDATE)]["ack_pdr_deadline"])
            - float(by_key[(seed, comparator)]["ack_pdr_deadline"])
            for seed in seeds
        ]
        delivery = [
            float(by_key[(seed, CANDIDATE)]["delivery_pdr_deadline"])
            - float(by_key[(seed, comparator)]["delivery_pdr_deadline"])
            for seed in seeds
        ]
        airtime = [
            float(by_key[(seed, CANDIDATE)]["tx_ledger_airtime_s"])
            - float(by_key[(seed, comparator)]["tx_ledger_airtime_s"])
            for seed in seeds
        ]
        relative_airtime = [
            airtime_value / float(by_key[(seed, comparator)]["tx_ledger_airtime_s"])
            for seed, airtime_value in zip(seeds, airtime)
        ]
        ack_ci = nominal_ci95(ack)
        delivery_ci = nominal_ci95(delivery)
        airtime_ci = nominal_ci95(airtime)
        relative_ci = nominal_ci95(relative_airtime)
        result.append({
            "comparator": comparator,
            "seed_count": len(seeds),
            "ack_pdr_mean": ack_ci["mean"],
            "ack_pdr_ci_low": ack_ci["ci_low"],
            "ack_pdr_ci_high": ack_ci["ci_high"],
            "delivery_pdr_mean": delivery_ci["mean"],
            "delivery_pdr_ci_low": delivery_ci["ci_low"],
            "delivery_pdr_ci_high": delivery_ci["ci_high"],
            "airtime_mean": airtime_ci["mean"],
            "airtime_ci_low": airtime_ci["ci_low"],
            "airtime_ci_high": airtime_ci["ci_high"],
            "relative_airtime_mean": relative_ci["mean"],
            "relative_airtime_ci_low": relative_ci["ci_low"],
            "relative_airtime_ci_high": relative_ci["ci_high"],
        })
    return result


def evaluate_population(
    manifest_path: Path,
    stage: str,
    development_report: Path | None = None,
) -> Dict[str, Any]:
    manifest, runs, flows, actions, requests = _load(Path(manifest_path))
    _validate_stage(manifest, runs, stage)
    prerequisite = None
    if stage == "holdout":
        if development_report is None:
            raise ValueError("holdout audit requires a passed development report")
        prerequisite = _validate_development_report(development_report)
    exposure = _started_action_counts(actions, requests)
    candidate_flows = [row for row in flows if row.get("protocol") == CANDIDATE]
    paired = _paired_summary(runs)
    by_comparator = {row["comparator"]: row for row in paired}
    candidate_rows = [row for row in runs if row["protocol"] == CANDIDATE]
    no_cancel_rows = [row for row in runs if row["protocol"] == CONTROL_NO_CANCEL]
    no_rescue_rows = [row for row in runs if row["protocol"] == CONTROL_NO_RESCUE]
    candidate_airtime = statistics.fmean(float(row["tx_ledger_airtime_s"]) for row in candidate_rows)
    no_cancel_airtime = statistics.fmean(float(row["tx_ledger_airtime_s"]) for row in no_cancel_rows)
    no_rescue_airtime = statistics.fmean(float(row["tx_ledger_airtime_s"]) for row in no_rescue_rows)
    checks = {
        "artifact_audit": True,
        "repeat_exposure": exposure.get("R_REPEAT", 0) >= 20,
        "recovery_exposure": exposure.get("F_RECOVERY", 0) >= 10,
        "ack_lower_bounds": all(
            by_comparator[name]["ack_pdr_ci_low"] >= -0.05
            for name in (CONTROL_NO_CANCEL, CONTROL_NO_RESCUE)
        ),
        "delivery_lower_bounds": all(
            by_comparator[name]["delivery_pdr_ci_low"] >= -0.05
            for name in (CONTROL_NO_CANCEL, CONTROL_NO_RESCUE)
        ),
        "airtime_vs_no_rescue": candidate_airtime <= 1.10 * no_rescue_airtime,
        "airtime_vs_no_cancel": candidate_airtime <= no_cancel_airtime,
        "scheduled_flow_denominator": len(candidate_flows) == sum(
            int(row["scheduled_unicast_flows"]) for row in candidate_rows
        ),
        "incomplete_rx_tx_zero": sum(int(row["incomplete_rx_tx_count"]) for row in runs) == 0,
    }
    return {
        "schema": "meshecho-cpr-population-audit-v1",
        "stage": stage,
        "manifest": str(Path(manifest_path)),
        "manifest_sha256": _sha256(Path(manifest_path)),
        "audit_tool_sha256": _sha256(Path(__file__).resolve()),
        "exposure": exposure,
        "paired_statistics": paired,
        "airtime_means": {
            CANDIDATE: candidate_airtime,
            CONTROL_NO_CANCEL: no_cancel_airtime,
            CONTROL_NO_RESCUE: no_rescue_airtime,
        },
        "checks": checks,
        "development_prerequisite": (
            {
                "report": str(Path(development_report)),
                "report_sha256": _sha256(Path(development_report)),
                "manifest_sha256": prerequisite["manifest_sha256"],
            }
            if prerequisite is not None
            else None
        ),
        "passed": all(checks.values()),
    }


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--stage", choices=tuple(EXPECTED_SEEDS), required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--development-report", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    result = evaluate_population(args.manifest, args.stage, args.development_report)
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True, indent=2))
    if not result["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
