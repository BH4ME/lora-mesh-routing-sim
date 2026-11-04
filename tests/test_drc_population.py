from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from tools import run_drc_experiment as drc
from tools import run_drc_population as population


def _case() -> drc.DrcCase:
    return drc.DrcCase(
        key="population-test",
        nodes=2,
        area_m=10.0,
        duration_s=8.0,
        pair_count=1,
        pair_schedule="fixed-once",
        payload_bytes=8,
        shadow_sigma_db=0.0,
        temporal_fading_sigma_db=0.0,
        tx_power_dbm=20.0,
        path_loss_exp=2.0,
        max_hops=3,
    )


def _runs() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for seed, candidate, all_f, no_rescue in (
        (1, 0.80, 0.70, 0.78),
        (2, 0.70, 0.60, 0.68),
        (3, 0.90, 0.80, 0.88),
    ):
        for arm, ack, air in (
            ("meshecho-drc", candidate, 90.0),
            ("meshecho-drc-all-f", all_f, 100.0),
            ("meshecho-drc-no-rescue", no_rescue, 95.0),
            ("meshecho-drc-fixed-guard", candidate, 92.0),
            ("meshecho-drc-r-only", candidate, 91.0),
        ):
            rows.append(
                {
                    "seed": seed,
                    "protocol": arm,
                    "ack_pdr_deadline": ack,
                    "delivery_pdr_deadline": ack,
                    "tx_ledger_airtime_s": air,
                    "scheduled_trace_sha256": f"trace-{seed}",
                    "topology_sha256": f"topology-{seed}",
                    "pair_pool_sha256": f"pairs-{seed}",
                }
            )
    return rows


def _bundle() -> drc.DrcExperiment:
    runs = _runs()
    paired = drc._paired_rows(runs, population.PRIMARY_ARMS)
    return drc.DrcExperiment(
        case=_case(),
        protocols=tuple(population.PRIMARY_ARMS),
        seeds=(1, 2, 3),
        deadline_s=30.0,
        split="custom",
        runs=runs,
        flows=[],
        actions=[],
        requests=[],
        transmissions=[],
        rx_attempts=[],
        acks=[],
        paired=paired,
        source_sha256={},
        identities={},
    )


def test_population_freezes_primary_case_arms_and_seed_cohorts():
    assert population.DEVELOPMENT_SEEDS == tuple(range(62001, 62021))
    assert population.HOLDOUT_SEEDS == tuple(range(63001, 63021))
    assert population.PRIMARY_ARMS == drc.DRC_PROTOCOLS
    assert population.PRIMARY_CASE.nodes == 50
    assert population.PRIMARY_CASE.area_m == pytest.approx(8250.0)
    assert population.PRIMARY_CASE.duration_s == pytest.approx(600.0)
    assert population.PRIMARY_CASE.sf == 7
    assert population.PRIMARY_CASE.temporal_fading_sigma_db == pytest.approx(6.0)
    assert population.PRIMARY_CASE.max_hops == 6


def test_seed_paired_summary_reports_mean_and_nominal_95_interval():
    summary = population.summarize_paired(_runs(), population.PRIMARY_ARMS)
    by_arm = {row["comparator"]: row for row in summary}
    row = by_arm["meshecho-drc-all-f"]
    assert row["seed_count"] == 3
    assert row["ack_pdr_mean"] == pytest.approx(0.10)
    assert row["ack_pdr_ci_low"] < row["ack_pdr_mean"] < row["ack_pdr_ci_high"]
    assert row["airtime_mean"] == pytest.approx(-10.0)
    assert row["airtime_ci_low"] <= row["airtime_mean"] <= row["airtime_ci_high"]


def test_seed_paired_summary_rejects_tampered_saved_paired_effects():
    bundle = _bundle()
    tampered = [dict(row) for row in bundle.paired]
    tampered[0]["ack_pdr_gain"] = 999.0
    with pytest.raises(ValueError, match="paired ACK effect"):
        population.summarize_paired(bundle.runs, bundle.protocols, tampered)


def test_stage_bundle_relabels_every_evidence_row_without_changing_inputs():
    staged = population.stage_bundle(_bundle(), "development", strict=False)
    assert staged.split == "development"
    for records in (
        staged.runs,
        staged.flows,
        staged.actions,
        staged.requests,
        staged.transmissions,
        staged.rx_attempts,
        staged.acks,
    ):
        assert all(row.get("seed_split") == "development" for row in records)
    assert staged.runs[0]["seed"] == _bundle().runs[0]["seed"]


def test_stage_bundle_strict_mode_rejects_empty_or_partial_population():
    with pytest.raises(ValueError, match="seed list|run matrix|flow evidence"):
        population.stage_bundle(_bundle(), "development")


def test_development_gate_is_joint_and_fails_closed_on_exposure_or_cost():
    bundle = _bundle()
    good = population.evaluate_development_gates(
        bundle,
        paired_summary=population.summarize_paired(bundle.runs, bundle.protocols),
        exposure={"r_reserved_starts": 20, "f_recovery_starts": 10},
        artifact_audit=True,
    )
    assert good["passed"] is True

    bad_exposure = population.evaluate_development_gates(
        bundle,
        paired_summary=population.summarize_paired(bundle.runs, bundle.protocols),
        exposure={"r_reserved_starts": 19, "f_recovery_starts": 10},
        artifact_audit=True,
    )
    assert bad_exposure["passed"] is False
    assert bad_exposure["checks"]["r_reserved_exposure"] is False

    bad_audit = population.evaluate_development_gates(
        bundle,
        paired_summary=population.summarize_paired(bundle.runs, bundle.protocols),
        exposure={"r_reserved_starts": 20, "f_recovery_starts": 10},
        artifact_audit=False,
    )
    assert bad_audit["passed"] is False
    assert bad_audit["checks"]["artifact_audit"] is False


def test_holdout_prerequisite_rejects_wrong_manifest_identity(tmp_path: Path):
    manifest = {
        "schema": population.POPULATION_SCHEMA,
        "population_stage": "development",
        "seed_split": "development",
        "seeds": list(population.DEVELOPMENT_SEEDS[:-1]),
        "protocols": list(population.PRIMARY_ARMS),
        "case": {"key": population.PRIMARY_CASE.key},
        "case_sha256": "wrong",
        "population_contract_sha256": population.population_contract_sha256(),
        "population_source_sha256": population.population_source_hashes(),
        "gates": {"development": True},
    }
    path = tmp_path / "development.manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="seed|case|manifest"):
        population.validate_development_manifest(path)


def test_run_population_streams_population_stage_and_keeps_evidence_file_backed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A small frozen cohort exercises the production streaming path."""

    case = _case()
    monkeypatch.setattr(population, "PRIMARY_CASE", case)
    monkeypatch.setattr(population, "CASE", case)
    monkeypatch.setattr(population, "DEVELOPMENT_SEEDS", (91006,))
    monkeypatch.setattr(population, "HOLDOUT_SEEDS", (91007,))
    monkeypatch.setattr(
        population,
        "SPLIT_SEEDS",
        {"development": (91006,), "holdout": (91007,)},
    )

    result = population.run_population(
        "development",
        tmp_path / "population-stream",
        case=case,
        seeds=(91006,),
    )

    assert result.manifest["population_stage"] == "development"
    assert result.manifest["seed_split"] == "development"
    assert result.bundle.split == "development"
    assert len(result.bundle.runs) == len(population.PRIMARY_ARMS)
    # Evidence is streamed to JSONL and exposed lazily rather than retained as
    # a giant list on the returned bundle.
    assert not isinstance(result.bundle.rx_attempts, list)
    assert len(result.bundle.rx_attempts) > 0
    assert all(
        row["seed_split"] == "development"
        for row in result.bundle.flows
    )
