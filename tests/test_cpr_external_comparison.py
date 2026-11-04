from __future__ import annotations

from tools.run_cpr_external_comparison import run_comparison
from tools.run_cpr_experiment import CprCase

FIXTURE = CprCase(key="external_regression_fixture", nodes=4, area_m=80.0, duration_s=20.0, pair_count=2)


def test_external_comparison_preserves_paired_trace_and_reports_both_baselines() -> None:
    result = run_comparison(
        case=FIXTURE,
        protocols=("meshecho-cpr", "meshtastic", "meshcore"),
        seeds=(92000,),
        split="custom",
    )

    assert [row["protocol"] for row in result.runs] == [
        "meshecho-cpr",
        "meshtastic",
        "meshcore",
    ]
    assert all(
        item["trace_match"] and item["topology_match"] and item["pair_pool_match"]
        for item in result.paired
    )
    assert {row["protocol"] for row in result.summary} == {
        "meshecho-cpr",
        "meshtastic",
        "meshcore",
    }


def test_external_comparison_defaults_to_four_protocol_family_matrix() -> None:
    result = run_comparison(case=FIXTURE, seeds=(92000,), split="custom")

    assert [row["protocol"] for row in result.runs] == [
        "meshecho-cpr",
        "meshecho",
        "meshtastic",
        "meshcore",
    ]


def test_external_evidence_contains_physical_acks_and_preserves_registry(tmp_path):
    from tools import run_cpr_experiment as cpr
    original = cpr.CPR_PROTOCOLS
    from dataclasses import replace
    result = run_comparison(case=replace(FIXTURE, nodes=2, pair_count=1), seeds=(92000,), split="custom")
    assert cpr.CPR_PROTOCOLS is original
    for arm in ("meshecho", "meshtastic", "meshcore"):
        accepted = [row for row in result.bundle.acks if row["protocol"] == arm and row["accepted"]]
        flows = [row for row in result.bundle.flows if row["protocol"] == arm and row["accepted_ack_at"] is not None]
        assert len(accepted) == len(flows) > 0
        assert all(row["ack_tx_id"] is not None and row["ack_rx_attempt_id"] is not None for row in accepted)
    paths = cpr.write_artifacts(tmp_path / "external", result.bundle)
    assert cpr.audit_artifacts(paths["manifest"])["status"] == "completed"


def test_external_unknown_arm_does_not_mutate_registry():
    import pytest
    from tools import run_cpr_experiment as cpr
    original = dict(cpr.EXTERNAL_REGISTRY)
    with pytest.raises(ValueError, match="unknown CPR arm"):
        run_comparison(case=FIXTURE, seeds=(92000,), protocols=("meshecho-cpr", "typo"))
    assert dict(cpr.EXTERNAL_REGISTRY) == original
    with pytest.raises(TypeError):
        cpr.EXTERNAL_REGISTRY["typo"] = cpr.ProtocolSpec("typo")


def test_external_requires_explicit_seeds_and_effective_parameters():
    import pytest
    from tools import run_cpr_experiment as cpr
    with pytest.raises(TypeError):
        run_comparison(case=FIXTURE)
    with pytest.raises(ValueError, match="unsupported parameter"):
        cpr.validate_parameters("meshtastic", {"flood_base_delay_s": 0.45})
    with pytest.raises(ValueError, match="invalid protocol parameter"):
        cpr.validate_parameters("meshcore", {"route_ttl_s": float("nan")})
    result = run_comparison(case=FIXTURE, seeds=(92000,), protocol_parameters={
        "meshtastic": {"base_delay_s": 0.45, "jitter_s": 0.65},
        "meshcore": {"route_ttl_s": 600.0, "flood_base_delay_s": 0.45, "flood_jitter_s": 0.65},
    })
    actual = result.bundle.identities[92000]["protocol_parameters_by_arm"]
    assert actual["meshtastic"]["base_delay_s"] == 0.45
    assert actual["meshcore"]["route_ttl_s"] == 600.0
    assert actual["meshcore"]["discovery_window_s"] == 0.0
