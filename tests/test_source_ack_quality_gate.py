"""Frozen artifact gate for the passive source ACK-quality screen."""

import hashlib
import json
from dataclasses import asdict

import pytest

from lora_mesh_sim import required_snr_db
from tools import run_source_ack_quality_gate as gate
from tools.run_sr_experiment import SrCase


def _digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()


def _stage_authorization(tmp_path, mode, case, predecessors):
    authorization = {
        "mode": mode,
        "seeds": list(gate.seeds_for_mode(mode)),
        "protocol": gate.PROTOCOL,
        "case_sha256": _digest(asdict(case)),
        "application_deadline_s": 30.0,
        "source_sha256": gate._source_hashes(),
        "prerequisite_manifest_sha256": predecessors,
    }
    path = tmp_path / f"{mode}.authorization.json"
    path.write_text(json.dumps(authorization, sort_keys=True) + "\n")
    return path


def _stub_diagnostic(seed, case, deadline_s, **_kwargs):
    protocol = "meshecho-dhr-flood-ack-delay"
    actions = [
        {"event": "decision", "time": 0.0, "flow_id": 1,
         "src": 0, "dst": 1, "action": "F"},
        {"event": "commit", "time": 1.0, "flow_id": 1,
         "src": 0, "dst": 1, "path": [0, 1]},
        {"event": "dhr_source_ack_rx", "time": 1.0, "flow_id": 1,
         "src": 0, "dst": 1, "repair_index": None, "accepted": True},
        {"event": "decision", "time": 5.0, "flow_id": 2,
         "src": 0, "dst": 1, "action": "R"},
        {"event": "dhr_source_ack_rx", "time": 6.0, "flow_id": 2,
         "src": 0, "dst": 1, "repair_index": None, "accepted": True},
    ]
    flows = [
        {"flow_id": 1, "enqueued_at": 0.0, "deadline_at": deadline_s,
         "delivered_at": 0.5},
        {"flow_id": 2, "enqueued_at": 5.0, "deadline_at": 5.0 + deadline_s,
         "delivered_at": 5.5},
    ]

    def packet(kind, flow_id, origin, final_dst):
        return {
            "kind": kind, "flow_id": flow_id, "origin": origin,
            "final_dst": final_dst, "repair_index": None,
            "path": [0, 1], "path_index": 0,
            "request_id": flow_id, "protocol": protocol,
        }

    transmissions = [
        {"tx_id": 1, "sender": 1, "start": 0.9, "end": 1.0,
         "packet": packet("ACK", 1, 1, 0)},
        {"tx_id": 2, "sender": 0, "start": 5.0, "end": 5.1,
         "packet": packet("DATA", 2, 0, 1)},
        {"tx_id": 3, "sender": 1, "start": 5.9, "end": 6.0,
         "packet": packet("ACK", 2, 1, 0)},
    ]
    ack_rows = [
        {"tx_id": tx_id, "tx_end_s": end, "flow_id": flow_id,
         "source": 0, "destination": 1, "sender": 1,
         "path": [0, 1], "path_index": 0, "repair_index": None,
         "snr_db": 10.0, "sinr_db": 10.0, "collided": False,
         "accepted": True, "action_order": order}
        for tx_id, end, flow_id, order in ((1, 1.0, 1, 2), (3, 6.0, 2, 4))
    ]
    q = round(2 * (10.0 - required_snr_db(case.sf)))
    cohort = {"rows": [{
        "flow_id": 2, "source": 0, "destination": 1,
        "decision_order": 3, "decision_time_s": 5.0,
        "initial_r_tx_id": 2, "initial_r_start_s": 5.0,
        "route_generation_flow_id": 1, "feature_exclusion_reason": None,
        "path": [0, 1], "path_type": "direct", "hop_count": 1,
        "prior_ack_tx_id": 1, "prior_ack_tx_end_s": 1.0,
        "prior_ack_age_s": 4.0,
        "q": q, "q_clean": q, "prior_ack_collided": False,
        "prior_r_miss": 0, "initial_r_ack_by_guard": True,
        "destination_delivery_by_deadline": True,
        "later_recovery_attempted": False,
        "later_recovery_ack_by_deadline": False,
    }], "exclusions": []}
    row = {
        "scheduled_trace_sha256": hashlib.sha256(
            f"stub-schedule-{seed}".encode()
        ).hexdigest(),
        "scheduled_unicast_flows": 2,
    }
    return {
        "seed": seed, "case": asdict(case), "protocol": protocol,
        "parity": {
            "exact": True,
            "scheduled_trace_sha256": row["scheduled_trace_sha256"],
            "full_row_sha256": _digest(row),
            "flow_trace_sha256": _digest(flows),
            "action_trace_sha256": _digest(actions),
            "full_tx_trace_sha256": _digest(transmissions),
            "random_state_sha256": "stub-rng",
            "channel_random_state_sha256": "stub-channel-rng",
        },
        "strict_replay_exact": True, "row": row,
        "flows": flows, "actions": actions, "transmissions": transmissions,
        "ack_rows": ack_rows, "cohort": cohort,
    }


def _stub_with_missing_q(seed, case, deadline_s, **_kwargs):
    run = _stub_diagnostic(seed, case, deadline_s)
    run["actions"].append({
        "event": "decision", "time": 7.0, "flow_id": 3,
        "src": 2, "dst": 3, "action": "R",
    })
    run["flows"].append({
        "flow_id": 3, "enqueued_at": 7.0,
        "deadline_at": 7.0 + deadline_s, "delivered_at": None,
    })
    run["transmissions"].append({
        "tx_id": 4, "sender": 2, "start": 7.0, "end": 7.1,
        "packet": {
            "kind": "DATA", "flow_id": 3, "origin": 2,
            "final_dst": 3, "repair_index": None,
            "path": [2, 3], "path_index": 0,
            "request_id": 3, "protocol": run["protocol"],
        },
    })
    run["cohort"]["rows"].append({
        "flow_id": 3, "source": 2, "destination": 3,
        "decision_order": 5, "decision_time_s": 7.0,
        "initial_r_tx_id": 4, "initial_r_start_s": 7.0,
        "route_generation_flow_id": None,
        "feature_exclusion_reason": "no_prior_commit",
        "path": [2, 3], "path_type": "direct", "hop_count": 1,
        "prior_ack_tx_id": None, "prior_ack_tx_end_s": None,
        "prior_ack_age_s": None,
        "q": None, "q_clean": None, "prior_ack_collided": None,
        "prior_r_miss": 0, "initial_r_ack_by_guard": False,
        "destination_delivery_by_deadline": False,
        "later_recovery_attempted": False,
        "later_recovery_ack_by_deadline": False,
    })
    run["row"]["scheduled_unicast_flows"] = 3
    run["parity"].update({
        "full_row_sha256": _digest(run["row"]),
        "flow_trace_sha256": _digest(run["flows"]),
        "action_trace_sha256": _digest(run["actions"]),
        "full_tx_trace_sha256": _digest(run["transmissions"]),
    })
    return run


@pytest.fixture(autouse=True)
def no_real_seeded_runs(monkeypatch):
    monkeypatch.setattr(gate, "run_diagnostic", _stub_diagnostic)


@pytest.mark.parametrize(
    "seed", [35001, 36001, 42000, 42101, 43000, 43001, 43020, 43101, 43120, 43200],
)
def test_synthetic_mode_cannot_open_reserved_ack_quality_seeds(seed, monkeypatch):
    monkeypatch.setattr(
        gate, "run_diagnostic",
        lambda *_args, **_kwargs: pytest.fail("must not open reserved seed"),
    )
    with pytest.raises(ValueError, match="reserved"):
        gate.run_report((seed,), mode="synthetic")


def test_modes_use_exact_frozen_cohorts():
    assert gate.seeds_for_mode("smoke") == (43200,)
    assert gate.seeds_for_mode("explore") == tuple(range(43001, 43021))
    assert gate.seeds_for_mode("validation") == tuple(range(43101, 43121))
    with pytest.raises(ValueError, match="exact"):
        gate.run_report((43002,), mode="explore")


def test_synthetic_report_preserves_full_passive_evidence():
    case = SrCase(
        key="ack_quality_gate_fixture", nodes=4, area_m=500.0,
        duration_s=45.0, rate_per_min=8.0, pair_mode="random",
        pair_count=0, max_hops=3, shadow_sigma_db=0.0,
        temporal_fading_sigma_db=0.0,
    )

    report = gate.run_report((73,), mode="synthetic", case=case)

    assert report["seeds"] == [73]
    assert report["case"]["key"] == case.key
    assert report["application_deadline_s"] == 30.0
    assert report["source_sha256"]
    assert report["case_sha256"]
    assert report["summary"]["initial_r_decisions"] == len(
        report["runs"][0]["cohort"]["rows"]
    )
    assert report["runs"][0]["parity"]["exact"] is True
    assert report["runs"][0]["strict_replay_exact"] is True
    assert report["runs"][0]["flows"]
    assert report["runs"][0]["actions"]
    assert report["runs"][0]["transmissions"]


def test_missing_q_initial_r_stays_in_full_denominator(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "run_diagnostic", _stub_with_missing_q)
    report = gate.run_report((73,), mode="synthetic")
    paths = gate.write_report(report, tmp_path / "missing_q")

    verified = gate.validate_manifest(
        paths["manifest"], expected_mode="synthetic",
        case=gate.sr.SR_CASES["recurring_fading"],
    )

    assert verified["summary"]["initial_r_decisions"] == 2
    assert verified["summary"]["eligible_decisions"] == 1
    assert verified["summary"]["missing_q_decisions"] == 1
    assert verified["summary"]["initial_r_ack_successes"] == 1
    assert verified["summary"]["by_seed"]["73"] == {
        "initial_r_decisions": 2,
        "eligible_decisions": 1,
        "eligible_r_ack_successes": 1,
        "eligible_r_ack_misses": 0,
        "full_r_ack_successes": 1,
        "full_r_ack_misses": 1,
    }


def test_summary_keeps_full_path_denominators_and_later_recovery():
    run = _stub_with_missing_q(
        73, gate.sr.SR_CASES["recurring_fading"], 30.0,
    )
    first, second = run["cohort"]["rows"]
    first["later_recovery_attempted"] = False
    first["later_recovery_ack_by_deadline"] = False
    second["later_recovery_attempted"] = True
    second["later_recovery_ack_by_deadline"] = True

    summary = gate._summary_from_runs([run])

    assert summary["later_recovery_attempts"] == 1
    assert summary["later_recovery_ack_successes"] == 1
    assert summary["by_path_type"]["direct"]["initial_r_decisions"] == 2
    assert summary["by_path_type"]["direct"]["full_r_ack_successes"] == 1
    assert summary["by_path_type"]["direct"]["full_r_ack_misses"] == 1
    assert summary["by_path_type"]["direct"]["later_recovery_attempts"] == 1
    assert summary["by_path_type"]["direct"]["later_recovery_ack_successes"] == 1


def test_summary_reports_offline_age_interference_and_fading_strata():
    run = _stub_diagnostic(73, gate.sr.SR_CASES["recurring_fading"], 30.0)
    fresh = run["cohort"]["rows"][0]
    old = {**fresh, "flow_id": 9, "initial_r_tx_id": 9,
           "decision_time_s": 125.0, "initial_r_start_s": 126.0,
           "prior_ack_tx_end_s": 90.0, "prior_ack_age_s": 35.0,
           "prior_ack_collided": True,
           "initial_r_ack_by_guard": False}
    run["cohort"]["rows"].append(old)

    diagnostics = gate._summary_from_runs([run])["eligible_diagnostics"]

    assert diagnostics["ack_age_s"]["at_most_30"]["r_ack_successes"] == 1
    assert diagnostics["ack_age_s"]["over_30"]["r_ack_misses"] == 1
    assert diagnostics["prior_ack_interference"]["none"]["records"] == 1
    assert diagnostics["prior_ack_interference"]["captured"]["records"] == 1
    assert diagnostics["fading_block"]["same"]["records"] == 1
    assert diagnostics["fading_block"]["different"]["records"] == 1


def test_fading_stratum_uses_exact_prior_ack_end_at_block_boundary():
    run = _stub_diagnostic(73, gate.sr.SR_CASES["recurring_fading"], 30.0)
    row = run["cohort"]["rows"][0]
    row["decision_time_s"] = 180.1
    row["prior_ack_tx_end_s"] = 59.99999999999999
    row["prior_ack_age_s"] = 180.1 - row["prior_ack_tx_end_s"]
    row["initial_r_start_s"] = 60.0

    fading = gate._summary_from_runs([run])["eligible_diagnostics"]["fading_block"]

    assert fading["different"]["records"] == 1
    assert fading["same"]["records"] == 0


def test_saved_cohort_rejects_recovery_action_without_physical_tx():
    case = gate.sr.SR_CASES["recurring_fading"]
    run = _stub_diagnostic(73, case, 30.0)
    run["actions"].append({
        "event": "dhr_recovery_tx", "time": 20.0, "end": 20.1,
        "flow_id": 2, "src": 0, "dst": 1,
        "action": "F", "repair_index": 2,
    })

    with pytest.raises(ValueError, match="recovery action"):
        gate._recompute_saved_cohort(run, 30.0, case.sf)


def test_saved_manifest_verifies_lossless_report_and_refuses_overwrite(tmp_path):
    case = SrCase(
        key="ack_quality_manifest_fixture", nodes=4, area_m=500.0,
        duration_s=45.0, rate_per_min=8.0, pair_mode="random",
        pair_count=0, max_hops=3, shadow_sigma_db=0.0,
        temporal_fading_sigma_db=0.0,
    )
    report = gate.run_report((73,), mode="synthetic", case=case)
    prefix = tmp_path / "ack_quality_synthetic"

    paths = gate.write_report(report, prefix)
    verified = gate.validate_manifest(
        paths["manifest"], expected_mode="synthetic", case=case,
        deadline_s=30.0,
    )

    assert verified["summary"] == report["summary"]
    assert verified["runs"] == report["runs"]
    assert paths["manifest_sha256"].is_file()
    with pytest.raises(FileExistsError):
        gate.write_report(report, prefix)


def test_rehashed_cohort_q_tampering_fails_semantic_audit(tmp_path):
    case = SrCase(
        key="ack_quality_tamper_fixture", nodes=4, area_m=500.0,
        duration_s=45.0, rate_per_min=8.0, pair_mode="random",
        pair_count=0, max_hops=3, shadow_sigma_db=0.0,
        temporal_fading_sigma_db=0.0,
    )
    report = gate.run_report((73,), mode="synthetic", case=case)
    paths = gate.write_report(report, tmp_path / "tampered")
    runs = [json.loads(line) for line in paths["runs"].read_text().splitlines()]
    assert runs[0]["cohort"]["rows"]
    runs[0]["cohort"]["rows"][0]["q"] += 1
    altered = "".join(json.dumps(run, sort_keys=True) + "\n" for run in runs)
    paths["runs"].write_text(altered)
    manifest = json.loads(paths["manifest"].read_text())
    manifest["artifacts"]["runs"]["sha256"] = hashlib.sha256(
        altered.encode()
    ).hexdigest()
    manifest_text = json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    paths["manifest"].write_text(manifest_text)
    paths["manifest_sha256"].write_text(
        hashlib.sha256(manifest_text.encode()).hexdigest()
        + "  " + paths["manifest"].name + "\n"
    )

    with pytest.raises(ValueError, match="cohort|ACK quality"):
        gate.validate_manifest(
            paths["manifest"], expected_mode="synthetic", case=case,
        )


@pytest.mark.parametrize(
    "field, altered", [("python_minor", [0, 0]), ("drain_until_s", -1.0)],
)
def test_rehashed_report_metadata_must_match_manifest(tmp_path, field, altered):
    report = gate.run_report((73,), mode="synthetic")
    paths = gate.write_report(report, tmp_path / field)
    summary = json.loads(paths["summary"].read_text())
    summary[field] = altered
    summary_text = json.dumps(summary, sort_keys=True, indent=2) + "\n"
    paths["summary"].write_text(summary_text)
    manifest = json.loads(paths["manifest"].read_text())
    manifest["artifacts"]["summary"]["sha256"] = hashlib.sha256(
        summary_text.encode()
    ).hexdigest()
    manifest_text = json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    paths["manifest"].write_text(manifest_text)
    paths["manifest_sha256"].write_text(
        hashlib.sha256(manifest_text.encode()).hexdigest()
        + "  " + paths["manifest"].name + "\n"
    )

    with pytest.raises(ValueError, match="metadata"):
        gate.validate_manifest(
            paths["manifest"], expected_mode="synthetic",
            case=gate.sr.SR_CASES["recurring_fading"],
        )


def test_forged_smoke_seed_is_rejected_by_independent_replay(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(gate, "_require_frozen_contract", lambda: None)
    monkeypatch.setattr(gate, "seeds_for_mode", lambda _mode: (43200,))
    small = SrCase(
        key="ack_quality_forgery_fixture", nodes=4, area_m=500.0,
        duration_s=45.0, rate_per_min=8.0, pair_mode="random",
        pair_count=0, max_hops=3, shadow_sigma_db=0.0,
        temporal_fading_sigma_db=0.0,
    )
    forged = gate.run_report((73,), mode="synthetic", case=small)
    frozen = gate.sr.SR_CASES["recurring_fading"]
    forged["mode"] = "smoke"
    forged["seeds"] = [43200]
    forged["case"] = asdict(frozen)
    forged["case_sha256"] = _digest(forged["case"])
    forged["drain_until_s"] = frozen.duration_s + 30.0
    forged["runs"][0]["seed"] = 43200
    forged["runs"][0]["case"] = asdict(frozen)
    forged["summary"] = gate._summary_from_runs(forged["runs"])
    saved = gate.write_report(forged, tmp_path / "forged_smoke")
    monkeypatch.setattr(gate, "run_diagnostic", _stub_diagnostic)

    with pytest.raises(ValueError, match="independent replay"):
        gate.validate_manifest(
            saved["manifest"], expected_mode="smoke", case=frozen,
            replay=True,
        )


def test_real_manifest_requires_explicit_replay_before_file_or_seed(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(gate, "_require_frozen_contract", lambda: None)
    monkeypatch.setattr(
        gate, "run_diagnostic",
        lambda *_args, **_kwargs: pytest.fail("seed must remain closed"),
    )

    with pytest.raises(ValueError, match="explicit replay"):
        gate.validate_manifest(
            tmp_path / "untrusted.manifest.json", expected_mode="smoke",
            case=gate.sr.SR_CASES["recurring_fading"],
        )


def test_later_cohorts_reject_missing_predecessor_before_simulation(monkeypatch):
    monkeypatch.setattr(gate, "_require_frozen_contract", lambda: None, raising=False)
    monkeypatch.setattr(
        gate, "run_diagnostic",
        lambda *_args, **_kwargs: pytest.fail("must not open a seed"),
    )
    with pytest.raises(ValueError, match="smoke manifest"):
        gate.run_report(gate.EXPLORATORY_SEEDS, mode="explore")
    with pytest.raises(ValueError, match="smoke manifest"):
        gate.run_report(gate.VALIDATION_SEEDS, mode="validation")


def test_exploration_requires_stage_authorization_before_any_replay(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(gate, "_require_frozen_contract", lambda: None)
    monkeypatch.setattr(
        gate, "seeds_for_mode", {"smoke": (73,), "explore": (74,)}.__getitem__,
    )
    case = gate.sr.SR_CASES["recurring_fading"]
    smoke = gate.write_report(
        gate.run_report((73,), mode="smoke", case=case), tmp_path / "smoke",
    )
    monkeypatch.setattr(
        gate, "run_diagnostic",
        lambda *_args, **_kwargs: pytest.fail("no seed may run before authorization"),
    )

    with pytest.raises(ValueError, match="stage authorization"):
        gate.run_report(
            (74,), mode="explore", case=case,
            smoke_manifest_path=smoke["manifest"],
        )


def test_exploration_records_exact_stage_authorization(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "_require_frozen_contract", lambda: None)
    monkeypatch.setattr(
        gate, "seeds_for_mode", {"smoke": (73,), "explore": (74,)}.__getitem__,
    )
    case = gate.sr.SR_CASES["recurring_fading"]
    smoke = gate.write_report(
        gate.run_report((73,), mode="smoke", case=case), tmp_path / "smoke",
    )
    permit = _stage_authorization(tmp_path, "explore", case, {
        "smoke_manifest": hashlib.sha256(smoke["manifest"].read_bytes()).hexdigest(),
    })

    report = gate.run_report(
        (74,), mode="explore", case=case,
        smoke_manifest_path=smoke["manifest"],
        stage_authorization_path=permit,
    )

    assert report["stage_authorization_sha256"] == hashlib.sha256(
        permit.read_bytes()
    ).hexdigest()


@pytest.mark.parametrize("field", [
    "mode", "seeds", "protocol", "case_sha256", "source_sha256",
    "prerequisite_manifest_sha256",
])
def test_exploration_rejects_mismatched_permit_before_any_replay(
    tmp_path, monkeypatch, field,
):
    monkeypatch.setattr(gate, "_require_frozen_contract", lambda: None)
    monkeypatch.setattr(
        gate, "seeds_for_mode", {"smoke": (73,), "explore": (74,)}.__getitem__,
    )
    case = gate.sr.SR_CASES["recurring_fading"]
    smoke = gate.write_report(
        gate.run_report((73,), mode="smoke", case=case), tmp_path / "smoke",
    )
    permit = _stage_authorization(tmp_path, "explore", case, {
        "smoke_manifest": hashlib.sha256(smoke["manifest"].read_bytes()).hexdigest(),
    })
    content = json.loads(permit.read_text())
    content[field] = "changed"
    permit.write_text(json.dumps(content, sort_keys=True) + "\n")
    monkeypatch.setattr(
        gate, "run_diagnostic",
        lambda *_args, **_kwargs: pytest.fail("bad permit must stop all replay"),
    )

    with pytest.raises(ValueError, match="stage authorization differs"):
        gate.run_report(
            (74,), mode="explore", case=case,
            smoke_manifest_path=smoke["manifest"],
            stage_authorization_path=permit,
        )


def test_exploration_manifest_requires_authorization_before_any_replay(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(gate, "_require_frozen_contract", lambda: None)
    monkeypatch.setattr(
        gate, "seeds_for_mode", {"smoke": (73,), "explore": (74,)}.__getitem__,
    )
    case = gate.sr.SR_CASES["recurring_fading"]
    smoke = gate.write_report(
        gate.run_report((73,), mode="smoke", case=case), tmp_path / "smoke",
    )
    permit = _stage_authorization(tmp_path, "explore", case, {
        "smoke_manifest": hashlib.sha256(smoke["manifest"].read_bytes()).hexdigest(),
    })
    explore = gate.write_report(
        gate.run_report(
            (74,), mode="explore", case=case,
            smoke_manifest_path=smoke["manifest"],
            stage_authorization_path=permit,
        ),
        tmp_path / "explore",
    )
    monkeypatch.setattr(
        gate, "run_diagnostic",
        lambda *_args, **_kwargs: pytest.fail("no seed may run before authorization"),
    )

    with pytest.raises(ValueError, match="stage authorization"):
        gate.validate_manifest(
            explore["manifest"], expected_mode="explore", case=case,
            smoke_manifest_path=smoke["manifest"], replay=True,
        )


def test_validation_requires_both_stage_authorizations_before_any_replay(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(gate, "_require_frozen_contract", lambda: None)
    monkeypatch.setattr(
        gate, "seeds_for_mode",
        {"smoke": (73,), "explore": (74,), "validation": (75,)}.__getitem__,
    )
    case = gate.sr.SR_CASES["recurring_fading"]
    smoke = gate.write_report(
        gate.run_report((73,), mode="smoke", case=case), tmp_path / "smoke",
    )
    smoke_hash = hashlib.sha256(smoke["manifest"].read_bytes()).hexdigest()
    explore_permit = _stage_authorization(
        tmp_path, "explore", case, {"smoke_manifest": smoke_hash},
    )
    explore = gate.write_report(
        gate.run_report(
            (74,), mode="explore", case=case,
            smoke_manifest_path=smoke["manifest"],
            stage_authorization_path=explore_permit,
        ),
        tmp_path / "explore",
    )
    validation_permit = _stage_authorization(tmp_path, "validation", case, {
        "smoke_manifest": smoke_hash,
        "explore_manifest": hashlib.sha256(
            explore["manifest"].read_bytes()
        ).hexdigest(),
    })
    monkeypatch.setattr(
        gate, "run_diagnostic",
        lambda *_args, **_kwargs: pytest.fail("no seed may run before both permits"),
    )

    with pytest.raises(ValueError, match="exploration stage authorization"):
        gate.run_report(
            (75,), mode="validation", case=case,
            smoke_manifest_path=smoke["manifest"],
            explore_manifest_path=explore["manifest"],
            stage_authorization_path=validation_permit,
        )


def test_validation_rejects_changed_exploration_permit_before_any_replay(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(gate, "_require_frozen_contract", lambda: None)
    monkeypatch.setattr(
        gate, "seeds_for_mode",
        {"smoke": (73,), "explore": (74,), "validation": (75,)}.__getitem__,
    )
    case = gate.sr.SR_CASES["recurring_fading"]
    smoke = gate.write_report(
        gate.run_report((73,), mode="smoke", case=case), tmp_path / "smoke",
    )
    smoke_hash = hashlib.sha256(smoke["manifest"].read_bytes()).hexdigest()
    explore_permit = _stage_authorization(
        tmp_path, "explore", case, {"smoke_manifest": smoke_hash},
    )
    explore = gate.write_report(
        gate.run_report(
            (74,), mode="explore", case=case,
            smoke_manifest_path=smoke["manifest"],
            stage_authorization_path=explore_permit,
        ),
        tmp_path / "explore",
    )
    validation_permit = _stage_authorization(tmp_path, "validation", case, {
        "smoke_manifest": smoke_hash,
        "explore_manifest": hashlib.sha256(
            explore["manifest"].read_bytes()
        ).hexdigest(),
    })
    explore_permit.write_bytes(explore_permit.read_bytes() + b"\n")
    monkeypatch.setattr(
        gate, "run_diagnostic",
        lambda *_args, **_kwargs: pytest.fail("changed permit must stop all replay"),
    )

    with pytest.raises(ValueError, match="exploration stage authorization hash"):
        gate.run_report(
            (75,), mode="validation", case=case,
            smoke_manifest_path=smoke["manifest"],
            explore_manifest_path=explore["manifest"],
            stage_authorization_path=validation_permit,
            explore_authorization_path=explore_permit,
        )


def test_exploration_no_go_manifest_cannot_open_validation(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "_require_frozen_contract", lambda: None, raising=False)
    case = gate.sr.SR_CASES["recurring_fading"]
    frozen = {"smoke": (73,), "explore": (74,), "validation": (75,)}
    monkeypatch.setattr(gate, "seeds_for_mode", frozen.__getitem__)
    smoke = gate.write_report(
        gate.run_report((73,), mode="smoke", case=case),
        tmp_path / "smoke",
    )
    smoke_hash = hashlib.sha256(smoke["manifest"].read_bytes()).hexdigest()
    explore_permit = _stage_authorization(
        tmp_path, "explore", case, {"smoke_manifest": smoke_hash},
    )
    exploration = gate.run_report(
        (74,), mode="explore", case=case,
        smoke_manifest_path=smoke["manifest"],
        stage_authorization_path=explore_permit,
    )
    assert exploration["exploration_fit"]["support"]["ready_for_validation"] is False
    assert exploration["sensitivity_fit"]["support"]["ready_for_validation"] is False
    explore_paths = gate.write_report(exploration, tmp_path / "explore")
    with pytest.raises(ValueError, match="smoke manifest"):
        gate.validate_manifest(
            explore_paths["manifest"], expected_mode="explore", case=case,
        )
    verified_explore = gate.validate_manifest(
        explore_paths["manifest"], expected_mode="explore", case=case,
        smoke_manifest_path=smoke["manifest"],
        stage_authorization_path=explore_permit, replay=True,
    )
    assert verified_explore["exploration_fit"] == exploration["exploration_fit"]
    validation_permit = _stage_authorization(tmp_path, "validation", case, {
        "smoke_manifest": smoke_hash,
        "explore_manifest": hashlib.sha256(
            explore_paths["manifest"].read_bytes()
        ).hexdigest(),
    })
    def no_validation_seed(seed, case, deadline_s, **kwargs):
        if seed == 75:
            pytest.fail("must not open validation seed")
        return _stub_diagnostic(seed, case, deadline_s, **kwargs)
    monkeypatch.setattr(
        gate, "run_diagnostic", no_validation_seed,
    )

    with pytest.raises(ValueError, match="support/model gate"):
        gate.run_report(
            (75,), mode="validation", case=case,
            smoke_manifest_path=smoke["manifest"],
            explore_manifest_path=explore_paths["manifest"],
            stage_authorization_path=validation_permit,
            explore_authorization_path=explore_permit,
        )


def test_clean_sensitivity_fit_failure_blocks_validation_before_seed(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(gate, "_require_frozen_contract", lambda: None)
    monkeypatch.setattr(
        gate, "seeds_for_mode",
        {"smoke": (73,), "explore": (74,), "validation": (75,)}.__getitem__,
    )
    monkeypatch.setattr(gate, "_audit_saved_model", lambda _report: None)
    case = gate.sr.SR_CASES["recurring_fading"]
    smoke = gate.write_report(
        gate.run_report((73,), mode="smoke", case=case), tmp_path / "smoke",
    )
    smoke_hash = hashlib.sha256(smoke["manifest"].read_bytes()).hexdigest()
    explore_permit = _stage_authorization(
        tmp_path, "explore", case, {"smoke_manifest": smoke_hash},
    )
    exploration = gate.run_report(
        (74,), mode="explore", case=case,
        smoke_manifest_path=smoke["manifest"],
        stage_authorization_path=explore_permit,
    )
    exploration["exploration_fit"]["support"]["ready_for_validation"] = True
    explore = gate.write_report(exploration, tmp_path / "explore")
    validation_permit = _stage_authorization(tmp_path, "validation", case, {
        "smoke_manifest": smoke_hash,
        "explore_manifest": hashlib.sha256(
            explore["manifest"].read_bytes()
        ).hexdigest(),
    })
    def no_validation_seed(seed, case, deadline_s, **kwargs):
        if seed == 75:
            pytest.fail("validation seed must remain closed")
        return _stub_diagnostic(seed, case, deadline_s, **kwargs)
    monkeypatch.setattr(
        gate, "run_diagnostic", no_validation_seed,
    )

    with pytest.raises(ValueError, match="sensitivity model"):
        gate.run_report(
            (75,), mode="validation", case=case,
            smoke_manifest_path=smoke["manifest"],
            explore_manifest_path=explore["manifest"],
            stage_authorization_path=validation_permit,
            explore_authorization_path=explore_permit,
        )


def test_rehashed_exploration_model_tampering_fails_recomputation(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(gate, "_require_frozen_contract", lambda: None, raising=False)
    case = gate.sr.SR_CASES["recurring_fading"]
    frozen = {"smoke": (73,), "explore": (74,), "validation": (75,)}
    monkeypatch.setattr(gate, "seeds_for_mode", frozen.__getitem__)
    smoke = gate.write_report(
        gate.run_report((73,), mode="smoke", case=case), tmp_path / "smoke",
    )
    explore_permit = _stage_authorization(tmp_path, "explore", case, {
        "smoke_manifest": hashlib.sha256(
            smoke["manifest"].read_bytes()
        ).hexdigest(),
    })
    explore = gate.write_report(
        gate.run_report(
            (74,), mode="explore", case=case,
            smoke_manifest_path=smoke["manifest"],
            stage_authorization_path=explore_permit,
        ), tmp_path / "explore",
    )
    metadata = json.loads(explore["summary"].read_text())
    metadata["exploration_fit"]["support"]["ready_for_validation"] = True
    altered_summary = json.dumps(metadata, sort_keys=True, indent=2) + "\n"
    explore["summary"].write_text(altered_summary)
    manifest = json.loads(explore["manifest"].read_text())
    manifest["exploration_fit"] = metadata["exploration_fit"]
    manifest["artifacts"]["summary"]["sha256"] = hashlib.sha256(
        altered_summary.encode()
    ).hexdigest()
    altered_manifest = json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    explore["manifest"].write_text(altered_manifest)
    explore["manifest_sha256"].write_text(
        hashlib.sha256(altered_manifest.encode()).hexdigest()
        + "  " + explore["manifest"].name + "\n"
    )

    with pytest.raises(ValueError, match="exploration model"):
        gate.validate_manifest(
            explore["manifest"], expected_mode="explore", case=case,
            smoke_manifest_path=smoke["manifest"],
            stage_authorization_path=explore_permit, replay=True,
        )


def test_validation_manifest_requires_actual_exploration_fit(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(gate, "_require_frozen_contract", lambda: None)
    monkeypatch.setattr(
        gate, "seeds_for_mode",
        {"smoke": (73,), "explore": (74,), "validation": (75,)}.__getitem__,
    )
    monkeypatch.setattr(gate, "_audit_saved_model", lambda _report: None)
    monkeypatch.setattr(
        gate, "score_validation",
        lambda _rows, _seeds, _fit, **_kwargs: {"gate": {"go": False}},
    )
    case = gate.sr.SR_CASES["recurring_fading"]
    smoke = gate.write_report(
        gate.run_report((73,), mode="smoke", case=case), tmp_path / "smoke",
    )
    smoke_hash = hashlib.sha256(smoke["manifest"].read_bytes()).hexdigest()
    explore_permit = _stage_authorization(
        tmp_path, "explore", case, {"smoke_manifest": smoke_hash},
    )
    exploration = gate.run_report(
        (74,), mode="explore", case=case,
        smoke_manifest_path=smoke["manifest"],
        stage_authorization_path=explore_permit,
    )
    exploration["exploration_fit"]["support"]["ready_for_validation"] = True
    exploration["sensitivity_fit"] = {
        "quality_field": "q_clean", "support": {"ready_for_validation": True},
    }
    explore = gate.write_report(exploration, tmp_path / "explore")
    validation_permit = _stage_authorization(tmp_path, "validation", case, {
        "smoke_manifest": smoke_hash,
        "explore_manifest": hashlib.sha256(
            explore["manifest"].read_bytes()
        ).hexdigest(),
    })
    validation = gate.run_report(
        (75,), mode="validation", case=case,
        smoke_manifest_path=smoke["manifest"],
        explore_manifest_path=explore["manifest"],
        stage_authorization_path=validation_permit,
        explore_authorization_path=explore_permit,
    )
    validation["exploration_fit"] = {
        **validation["exploration_fit"], "threshold_cut": 12,
    }
    saved = gate.write_report(validation, tmp_path / "validation")

    monkeypatch.setattr(
        gate, "run_diagnostic",
        lambda *_args, **_kwargs: pytest.fail("no replay without validation permit"),
    )
    with pytest.raises(ValueError, match="validation stage authorization"):
        gate.validate_manifest(
            saved["manifest"], expected_mode="validation", case=case,
            smoke_manifest_path=smoke["manifest"],
            explore_manifest_path=explore["manifest"],
            explore_authorization_path=explore_permit, replay=True,
        )
    monkeypatch.setattr(gate, "run_diagnostic", _stub_diagnostic)

    with pytest.raises(ValueError, match="actual exploration manifest"):
        gate.validate_manifest(
            saved["manifest"], expected_mode="validation", case=case,
            smoke_manifest_path=smoke["manifest"],
            explore_manifest_path=explore["manifest"],
            stage_authorization_path=validation_permit,
            explore_authorization_path=explore_permit,
            replay=True,
        )


def test_cli_existing_output_stops_before_opening_reserved_seed(tmp_path, monkeypatch):
    prefix = tmp_path / "taken"
    prefix.with_name(prefix.name + ".manifest.json").write_text("existing")
    monkeypatch.setattr(
        gate, "run_diagnostic",
        lambda *_args, **_kwargs: pytest.fail("must not open smoke seed"),
    )

    with pytest.raises(FileExistsError, match="already exists"):
        gate.main(["--mode", "smoke", "--output-prefix", str(prefix)])


def test_cli_passes_stage_authorization_paths_without_simulating(
    tmp_path, monkeypatch,
):
    captured = {}

    def fake_run_report(_seeds, **kwargs):
        captured.update(kwargs)
        return {
            "source_sha256": gate._source_hashes(),
            "summary": {},
            "exploration_fit": {"support": {"ready_for_validation": False}},
        }

    monkeypatch.setattr(gate, "run_report", fake_run_report)
    monkeypatch.setattr(gate, "write_report", lambda *_args: {})
    gate.main([
        "--mode", "explore", "--output-prefix", str(tmp_path / "unused"),
        "--smoke-manifest", str(tmp_path / "smoke.manifest.json"),
        "--stage-authorization", str(tmp_path / "explore.authorization.json"),
        "--explore-authorization", str(tmp_path / "earlier.authorization.json"),
    ])

    assert captured["stage_authorization_path"] == (
        tmp_path / "explore.authorization.json"
    )
    assert captured["explore_authorization_path"] == (
        tmp_path / "earlier.authorization.json"
    )


def test_unfrozen_contract_blocks_smoke_before_diagnostic(tmp_path, monkeypatch):
    draft_contract = tmp_path / "draft_contract.md"
    draft_contract.write_text("# Test contract\n\nStatus: draft\n")
    monkeypatch.setattr(gate, "CONTRACT_PATH", draft_contract)
    monkeypatch.setattr(gate, "seeds_for_mode", lambda _mode: (73,))
    monkeypatch.setattr(
        gate, "run_diagnostic",
        lambda *_args, **_kwargs: pytest.fail("draft must not start a seed"),
    )

    with pytest.raises(ValueError, match="frozen"):
        gate.run_report((73,), mode="smoke")


def test_real_cohort_rejects_case_or_deadline_change_before_seed(monkeypatch):
    monkeypatch.setattr(gate, "seeds_for_mode", lambda _mode: (73,))
    monkeypatch.setattr(gate, "_require_frozen_contract", lambda: None, raising=False)
    monkeypatch.setattr(
        gate, "run_diagnostic",
        lambda *_args, **_kwargs: pytest.fail("changed inputs must not run"),
    )
    altered_case = SrCase(key="wrong_case")

    with pytest.raises(ValueError, match="frozen case|deadline"):
        gate.run_report((73,), mode="smoke", case=altered_case)
    with pytest.raises(ValueError, match="frozen case|deadline"):
        gate.run_report((73,), mode="smoke", deadline_s=31.0)
