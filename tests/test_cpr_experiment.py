"""Contract tests for the independent CPR smoke artifact runner."""

import json
from pathlib import Path

import pytest

from tools import run_cpr_experiment as cpr


def _refresh_artifact_hash(paths, manifest_path, key):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifacts"][key]["sha256"] = cpr._file_sha256(paths[key])
    manifest["artifacts"][key]["records"] = sum(
        1 for line in paths[key].read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )


def test_cpr_smoke_matrix_pairs_fresh_arms_and_audits_artifacts(tmp_path: Path):
    case = cpr.CprCase(
        key="cpr_test",
        nodes=4,
        area_m=80.0,
        duration_s=20.0,
        pair_count=2,
        pair_schedule="fixed-once",
    )
    bundle = cpr.run_matrix(case, seeds=(92000,), deadline_s=30.0, split="smoke")

    assert bundle.protocols == cpr.CPR_PROTOCOLS
    assert len(bundle.runs) == len(cpr.CPR_PROTOCOLS)
    assert len(bundle.flows) == 2 * len(cpr.CPR_PROTOCOLS)
    assert all(
        row["scheduled_trace_sha256"] == bundle.runs[0]["scheduled_trace_sha256"]
        for row in bundle.runs
    )

    paths = cpr.write_artifacts(tmp_path / "cpr_smoke", bundle)
    manifest = cpr.audit_artifacts(paths["manifest"])
    assert manifest["schema"] == cpr.SCHEMA
    assert manifest["counts"]["rx_attempts"] > 0
    assert manifest["contract_path"] == "docs/research/meshecho_cpr_smoke_contract_20261006.md"
    assert manifest["sim_version"] == (cpr.VERSION_PATH).read_text(encoding="utf-8").strip()
    assert all(row["seed_split"] == "smoke" for row in bundle.runs)


def test_cpr_artifacts_bind_to_explicit_contract_path(tmp_path: Path):
    contract = tmp_path / "exploratory_contract.md"
    contract.write_text("exploratory contract v1\n", encoding="utf-8")
    case = cpr.CprCase(
        key="cpr_contract_path", nodes=4, area_m=80.0,
        duration_s=20.0, pair_count=2, pair_schedule="fixed-once",
    )
    bundle = cpr.run_matrix(
        case, seeds=(92004,), deadline_s=30.0, split="custom",
        contract_path=contract,
    )
    assert bundle.contract_path == contract
    paths = cpr.write_artifacts(tmp_path / "contract_bound", bundle)
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert manifest["contract_sha256"] == cpr._file_sha256(contract)
    assert cpr.audit_artifacts(paths["manifest"])["contract_path"] == str(contract)


def test_cpr_audit_accepts_multihop_reverse_path_ack(tmp_path: Path):
    bundle = cpr.run_matrix(cpr.CprCase(), seeds=(92024,), deadline_s=30.0)
    paths = cpr.write_artifacts(tmp_path / "multihop_ack", bundle)
    assert cpr.audit_artifacts(paths["manifest"])["counts"]["accepted_acks"] > 0


def test_cpr_exposure_profile_is_repeated_and_fading():
    case = cpr.CASE_PROFILES["exposure"]
    assert case.pair_schedule == "poisson"
    assert case.rate_per_min == 8.0
    assert case.duration_s == 240.0
    assert case.temporal_fading_sigma_db == 6.0
    assert case.temporal_fading_interval_s == 60.0
    assert case.pair_count == 4


def test_cpr_runner_preserves_confirmatory_split_metadata(tmp_path: Path):
    case = cpr.CprCase(
        key="cpr_split", nodes=4, area_m=80.0,
        duration_s=20.0, pair_count=2, pair_schedule="fixed-once",
    )
    bundle = cpr.run_matrix(case, seeds=(92005,), split="development")
    assert bundle.split == "development"
    paths = cpr.write_artifacts(tmp_path / "development_stage", bundle)
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    assert manifest["experiment_stage"] == "development"
    assert manifest["seed_split"] == "development"
    assert all(row["seed_split"] == "development" for row in bundle.runs)
    assert manifest["gates"] == {
        "mechanical_smoke": False, "development": False, "holdout": False,
    }


def test_cpr_source_hashes_cover_runtime_dependency_and_version():
    hashes = cpr._source_hashes()
    assert "meshecho_utility.py" in hashes
    assert "VERSION" in hashes


def test_cpr_audit_rejects_duplicate_accepted_ack_attempt(tmp_path: Path):
    case = cpr.CprCase(
        key="cpr_duplicate_ack", nodes=4, area_m=80.0,
        duration_s=20.0, pair_count=2, pair_schedule="fixed-once",
    )
    bundle = cpr.run_matrix(case, seeds=(92001,), deadline_s=30.0, split="smoke")
    paths = cpr.write_artifacts(tmp_path / "duplicate_ack", bundle)
    rows = [
        json.loads(line) for line in paths["acks"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    accepted = next(row for row in rows if row.get("accepted"))
    rows.append(dict(accepted))
    paths["acks"].write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest_path = paths["manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["counts"]["accepted_acks"] += 1
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    _refresh_artifact_hash(paths, manifest_path, "acks")

    with pytest.raises(ValueError, match="duplicate accepted CPR ACK"):
        cpr.audit_artifacts(manifest_path)


def test_cpr_audit_rejects_ack_marker_without_started_matching_packet(tmp_path: Path):
    case = cpr.CprCase(
        key="cpr_marker_join", nodes=4, area_m=80.0,
        duration_s=20.0, pair_count=2, pair_schedule="fixed-once",
    )
    bundle = cpr.run_matrix(case, seeds=(92002,), deadline_s=30.0, split="smoke")
    paths = cpr.write_artifacts(tmp_path / "marker_join", bundle)
    rows = [
        json.loads(line) for line in paths["acks"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    accepted = next(row for row in rows if row.get("accepted"))
    accepted["repair_index"] = 1 if accepted.get("repair_index") != 1 else 2
    paths["acks"].write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest_path = paths["manifest"]
    _refresh_artifact_hash(paths, manifest_path, "acks")

    with pytest.raises(ValueError, match="accepted CPR ACK marker/TX mismatch"):
        cpr.audit_artifacts(manifest_path)


def test_cpr_audit_rejects_started_action_without_matching_decision(tmp_path: Path):
    case = cpr.CprCase(
        key="cpr_action_join", nodes=4, area_m=80.0,
        duration_s=20.0, pair_count=2, pair_schedule="fixed-once",
    )
    bundle = cpr.run_matrix(case, seeds=(92003,), deadline_s=30.0, split="smoke")
    paths = cpr.write_artifacts(tmp_path / "action_join", bundle)
    rows = [
        json.loads(line) for line in paths["actions"].read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    target = next(
        row for row in rows
        if row.get("protocol") == "meshecho-cpr"
        and row.get("event") == "decision"
        and row.get("action") in {"R_INITIAL", "F_INITIAL"}
    )
    rows.remove(target)
    paths["actions"].write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest_path = paths["manifest"]
    _refresh_artifact_hash(paths, manifest_path, "actions")

    with pytest.raises(ValueError, match="CPR started request lacks action decision"):
        cpr.audit_artifacts(manifest_path)
