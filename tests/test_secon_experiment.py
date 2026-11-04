"""Evidence invariants: source identity, run lock, preserved failures, and seed plans."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from tools import secon2027_experiment as exp


def matrix():
    return {
        "schema": exp.MATRIX_SCHEMA, "experiment_id": "fixture", "stage": "development",
        "cohort_id": "test-development", "seeds": [2027990],
        "contract_path": "docs/contract.md",
        "cases": [{"id": "s1", "scenario": "P0-smoke", "configuration": "smoke", "case": {},
                   "environment": {}, "deadline_s": 30}],
        "arms": [{"id": "cpr", "protocol": "meshecho-cpr", "parameters": {}},
                 {"id": "mt", "protocol": "meshtastic", "parameters": {}}],
        "statistics": {"unit": "seed", "intent": "fixture-no-simulation"}, "budget": {},
        "failure_policy": {"max_attempts": 2, "retry": "infrastructure-only-explicit", "missing": "report-incomplete"},
    }


def source(tmp_path):
    root = tmp_path / "repo"
    for rel, data in {"VERSION": "2.1.27", "requirements.txt": "", "simulation.py": "import math\n",
                      "tools/helper.py": "VALUE=1\n", "docs/contract.md": "frozen contract\n"}.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
    return root


def test_source_snapshot_survives_version_promotion_and_detects_helper_tampering(tmp_path):
    root = source(tmp_path)
    desc = exp.freeze_source(root, tmp_path / "snapshots", "docs/contract.md")
    path = tmp_path / "snapshots" / desc["snapshot_id"]
    (root / "VERSION").write_text("2.1.28")
    assert exp.verify_snapshot(path)["tested_version"] == "2.1.27"
    (path / "source/tools/helper.py").write_text("VALUE=2\n")
    with pytest.raises(ValueError, match="source snapshot mismatch"):
        exp.verify_snapshot(path)


def test_snapshot_detects_untracked_dependency_injection(tmp_path):
    root = source(tmp_path)
    desc = exp.freeze_source(root, tmp_path / "snapshots", "docs/contract.md")
    path = tmp_path / "snapshots" / desc["snapshot_id"]
    (path / "source/tools/extra.py").write_text("pass\n")
    with pytest.raises(ValueError, match="extra/untracked"):
        exp.verify_snapshot(path)


def test_run_lock_refuses_duplicate_and_releases_only_holder(tmp_path):
    with exp.run_lock(tmp_path, "key"):
        with pytest.raises(FileExistsError):
            with exp.run_lock(tmp_path, "key"):
                pytest.fail("duplicate lock was acquired")
        assert (tmp_path / "results/secon2027/run_state/key.lock").exists()
    assert not (tmp_path / "results/secon2027/run_state/key.lock").exists()


def test_run_keys_bind_each_arm_seed_source_and_config():
    original = matrix()
    keys = exp.generate_runs(original, "source-a")
    assert len(keys) == 2 and keys[0]["run_key"] != keys[1]["run_key"]
    changed = copy.deepcopy(original)
    changed["cases"][0]["deadline_s"] = 60
    assert exp.generate_runs(changed, "source-a")[0]["run_key"] != keys[0]["run_key"]
    assert exp.generate_runs(original, "source-b")[0]["run_key"] != keys[0]["run_key"]


def test_closed_schema_rejects_ignored_fields_and_ungated_validation():
    data = matrix()
    exp.validate_matrix(data)
    data["typo"] = True
    with pytest.raises(ValueError, match="unknown"):
        exp.validate_matrix(data)
    data.pop("typo")
    data["stage"] = "validation"
    with pytest.raises(ValueError, match="development gate"):
        exp.validate_matrix(data)


def test_artifacts_cannot_be_overwritten_or_tampered(tmp_path):
    file = tmp_path / "raw.json"
    exp.write_new(file, {"negative_result": True})
    with pytest.raises(FileExistsError):
        exp.write_new(file, {"positive_result": True})
    exp.write_new(tmp_path / "completion.json", {"status": "completed", "files": {"raw.json": exp.sha(file)}})
    with pytest.raises(ValueError, match="required evidence"):
        exp.audit_attempt(tmp_path)
    file.write_text('{}')
    assert exp.sha(file) != exp.read(tmp_path / "completion.json")["files"]["raw.json"]


def test_registry_exception_preserves_prior_state(tmp_path):
    path = tmp_path / "registry.json"
    exp.write_new(path, {"state": "reserved"})
    with pytest.raises(RuntimeError):
        with exp.registry_edit(path) as data:
            data["state"] = "exposed"
            raise RuntimeError("failed before execution")
    assert exp.read(path) == {"state": "reserved"}


def test_path_rejects_escape(tmp_path):
    with pytest.raises(ValueError):
        exp.under(tmp_path, "../wrong")
    with pytest.raises(ValueError):
        exp.under(tmp_path, "/tmp/wrong")
