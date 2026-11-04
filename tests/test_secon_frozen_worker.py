"""Real frozen-worker lifecycle using an isolated development regression fixture.

Seed 92000 is a legacy test fixture, not unseen research evidence. The temporary
registry deliberately has no historical exclusions and is never copied back.
"""
from __future__ import annotations

import shutil
import os
from pathlib import Path

import pytest

from tools import secon2027_experiment as exp


def _fixture_repository(tmp_path: Path) -> tuple[Path, Path, Path]:
    root = tmp_path / "fixture-repository"
    # Copy the actual runtime closure and tests, including the actual worker.
    # README only supplies an existing harmless inventory contract at source.
    inventory = exp.source_inventory(exp.ROOT, "README.md")
    for relative in inventory:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(exp.ROOT / relative, target)
    contract = root / "docs/fixture_contract.md"
    contract.parent.mkdir(parents=True, exist_ok=True)
    contract.write_text("Development regression fixture only. Seed 92000 is previously exposed; no performance claim.\n")
    registry = root / "configs/secon2027/fixture_seed_registry.json"
    exp.write_new(registry, {
        "schema": "secon2027-seed-registry-v1", "exclusions": [],
        "cohorts": {"fixture-development-92000": {
            "purpose": "development", "seeds": [92000], "status": "reserved",
            "seed_states": {"92000": "reserved"}, "plans": [], "planned_run_keys": [],
            "note": "Isolated regression fixture, not unseen research seed",
        }},
    })
    matrix = root / "configs/secon2027/fixture_matrix.json"
    exp.write_new(matrix, {
        "schema": exp.MATRIX_SCHEMA, "experiment_id": "frozen-worker-regression",
        "stage": "development", "cohort_id": "fixture-development-92000", "seeds": [92000],
        "contract_path": "docs/fixture_contract.md",
        "cases": [{
            "id": "grid-fixture", "scenario": "P0-smoke", "configuration": "smoke",
            "case": {"key": "grid_fixture", "nodes": 4, "area_m": 2000.0,
                     "duration_s": 20.0, "pair_count": 2, "pair_schedule": "fixed-once",
                     "sf": 7, "shadow_sigma_db": 0.0},
            "environment": {"model": "grid-obstructed-v1", "columns": 2, "rows": 2,
                            "endpoint_pairs": [[0, 3], [3, 0]]},
            "deadline_s": 30.0,
        }],
        "arms": [{"id": "cpr", "protocol": "meshecho-cpr", "parameters": {}},
                 {"id": "mt", "protocol": "meshtastic", "parameters": {}}],
        "statistics": {"unit": "seed", "intent": "regression-no-performance-inference"},
        "budget": {"max_runs": 2},
        "failure_policy": {"max_attempts": 2, "retry": "infrastructure-only-explicit",
                           "missing": "report-incomplete"},
    })
    return root, matrix, registry


def test_actual_frozen_worker_completes_resumes_and_rejects_raw_tampering(tmp_path: Path):
    root, matrix_path, registry_path = _fixture_repository(tmp_path)
    plan_path = root / "configs/secon2027/fixture_plan.json"
    plan = exp.freeze(matrix_path, registry_path, root, plan_path)
    assert len(plan["runs"]) == 2
    snapshot_source = root / plan["snapshot_path"] / "source"
    assert (snapshot_source / "tools/secon2027_experiment.py").is_file()
    assert exp.verify_snapshot(snapshot_source.parent)["snapshot_id"] == plan["source_snapshot"]
    assert exp.audit_plan(plan_path, root)["status"] == "incomplete"

    first_spec = plan["runs"][0]
    first = exp.execute_one(plan_path, root, first_spec)
    assert first["status"] == "completed"
    assert first["source_snapshot"] == plan["source_snapshot"]
    assert first["audit"]["scheduled_flows"] == 2
    registry_after_first = exp.read(registry_path)
    cohort = registry_after_first["cohorts"]["fixture-development-92000"]
    assert cohort["status"] == cohort["seed_states"]["92000"] == "exposed"

    # Exposure from one arm must not block another predeclared arm.
    second = exp.execute_one(plan_path, root, plan["runs"][1])
    assert second["status"] == "completed"
    report = exp.audit_plan(plan_path, root)
    assert report["status"] == "complete"
    assert report["expected_runs"] == len(report["completed"]) == 2
    assert report["missing"] == report["failed"] == []

    run_directory = root / "results/secon2027/runs" / first_spec["run_key"]
    attempt = run_directory / "attempt-001"
    runtime = exp.read(attempt / "worker_runtime.json")
    assert runtime["pid"] != os.getpid()
    assert runtime["run_key"] == first_spec["run_key"]
    assert runtime["plan_sha256"] == plan["plan_sha256"]
    assert set(first["files"]) == exp.REQUIRED_ATTEMPT_FILES
    completion_before = (attempt / "completion.json").read_bytes()
    original_attempts = sorted(run_directory.glob("attempt-*"))
    repeated = exp.execute_one(plan_path, root, first_spec)
    assert repeated["status"] == "verified-existing"
    assert sorted(run_directory.glob("attempt-*")) == original_attempts
    assert (attempt / "completion.json").read_bytes() == completion_before

    # Alter the saved raw package only; both resume and plan audit must reject.
    with (attempt / "evidence.transmissions.jsonl").open("ab") as stream:
        stream.write(b"\n")
    with pytest.raises(ValueError, match="artifact tampered"):
        exp.execute_one(plan_path, root, first_spec)
    with pytest.raises(ValueError, match="artifact tampered"):
        exp.audit_plan(plan_path, root)
    assert sorted(run_directory.glob("attempt-*")) == original_attempts
    assert (attempt / "completion.json").read_bytes() == completion_before
