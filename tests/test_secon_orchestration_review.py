"""Independent adversarial evidence review; only legacy fixture seed 92000.

No research cohort is started. Artifact fixtures use a tiny fixed traffic case;
freeze/registry checks use temporary repositories without executing workers.
"""
import copy
from dataclasses import asdict
import json
from pathlib import Path
import shutil
import socket
from types import SimpleNamespace

import pytest

from tools import run_cpr_experiment as cpr
from tools import secon2027_experiment as exp


def fixture_matrix():
    case = cpr.CprCase(key="independent-review-fixture", nodes=4, pair_count=1,
                       duration_s=2.0, sf=7, shadow_sigma_db=0.0, max_hops=3)
    return {
        "schema": exp.MATRIX_SCHEMA, "experiment_id": "review-fixture",
        "stage": "development", "cohort_id": "fixture-only", "seeds": [92000],
        "contract_path": "docs/contract.md",
        "cases": [{"id": "case", "scenario": "P0-smoke", "configuration": "smoke",
                   "case": asdict(case), "deadline_s": 30.0,
                   "environment": {"model": "grid-obstructed-v1", "columns": 2, "rows": 2,
                                   "spacing_m": 10.0, "position_jitter_fraction": 0.0,
                                   "neighbor_loss_db": 0.0, "nonneighbor_loss_db": 80.0,
                                   "endpoint_pairs": [[0, 3]], "faults": []}}],
        "arms": [{"id": "cpr", "protocol": "meshecho-cpr", "parameters": {}},
                 {"id": "mt", "protocol": "meshtastic", "parameters": {}}],
        "statistics": {"unit": "seed", "intent": "fixture-no-research"},
        "budget": {"runs": 2, "parallelism": 1},
        "failure_policy": {"max_attempts": 2, "retry": "infrastructure-only-explicit", "missing": "report-incomplete"},
    }


def fixture_source(tmp_path):
    root = tmp_path / "repo"
    for rel, content in {"VERSION": "2.1.27\n", "requirements.txt": "", "unit_fixture.py": "pass\n",
                         "tools/helper.py": "pass\n", "docs/contract.md": "deterministic fixture\n"}.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return root


def freeze_fixture(tmp_path):
    root = fixture_source(tmp_path)
    matrix = fixture_matrix()
    registry_path = root / "registry.json"
    exp.write_new(registry_path, {"cohorts": {"fixture-only": {
        "purpose": "development", "seeds": [92000], "status": "reserved"}}, "exclusions": []})
    matrix_path, plan_path = root / "matrix.json", root / "plan.json"
    exp.write_new(matrix_path, matrix)
    plan = exp.freeze(matrix_path, registry_path, root, plan_path)
    return root, plan_path, registry_path, plan


def completed_fixture(tmp_path, protocol="meshecho-cpr"):
    matrix = fixture_matrix()
    snapshot = "review-fixture-source"
    runs = exp.generate_runs(matrix, snapshot)
    spec = next(run for run in runs if run["arm"]["protocol"] == protocol)
    plan = {"plan_sha256": "fixture-plan-sha", "source_snapshot": snapshot,
            "tested_version": cpr.VERSION_PATH.read_text().strip(), "runs": runs,
            "snapshot_path": "fixture-unused-snapshot", "matrix": matrix,
            "contract_sha256": exp.sha(cpr.CONTRACT_PATH)}
    attempt = tmp_path / protocol
    attempt.mkdir()
    exp.write_new(attempt / "started.json", {"status": "running", "spec": spec,
                                           "plan_sha256": plan["plan_sha256"]})
    exp.write_new(attempt / "worker_runtime.json", {"run_key": spec["run_key"],
                                                  "plan_sha256": plan["plan_sha256"],
                                                  "fixture": True})
    for filename in ("stdout.log", "stderr.log"):
        (attempt / filename).write_text("")
    case = cpr.CprCase(**spec["case"]["case"])
    bundle = cpr.run_matrix(case, (protocol,), (92000,), spec["case"]["deadline_s"],
                            "development", registry=cpr.EXTERNAL_REGISTRY,
                            environment=spec["case"]["environment"],
                            protocol_parameters={protocol: {}})
    cpr.write_artifacts(attempt / "evidence", bundle)
    observed = exp.audit_bundle(bundle, spec)
    exp.write_new(attempt / "worker_audit.json", observed)
    record = {"status": "completed", "run_key": spec["run_key"], "source_snapshot": snapshot,
              "tested_version": plan["tested_version"], "plan_sha256": plan["plan_sha256"],
              "wall_seconds": 0.01, "audit": observed,
              "files": {p.name: exp.sha(p) for p in attempt.iterdir() if p.is_file()}}
    exp.write_new(attempt / "completion.json", record)
    return attempt, spec, plan


def test_empty_completion_cannot_certify_an_attempt(tmp_path):
    exp.write_new(tmp_path / "completion.json", {"status": "completed", "files": {}})
    with pytest.raises(ValueError):
        exp.audit_attempt(tmp_path)


def test_completed_real_fixture_validates_and_missing_rx_file_cannot_be_hidden(tmp_path):
    attempt, spec, plan = completed_fixture(tmp_path)
    exp.audit_attempt(attempt, spec=spec, plan=plan)
    record = exp.read(attempt / "completion.json")
    record["files"].pop("evidence.rx_attempts.jsonl")
    (attempt / "evidence.rx_attempts.jsonl").unlink()
    (attempt / "completion.json").write_text(json.dumps(record))
    with pytest.raises(ValueError):
        exp.audit_attempt(attempt, spec=spec, plan=plan)


def test_another_arms_completed_package_cannot_fill_a_planned_key(tmp_path, monkeypatch):
    attempt, spec, plan = completed_fixture(tmp_path)
    other = next(run for run in plan["runs"] if run["run_key"] != spec["run_key"])
    with pytest.raises(ValueError, match="identity|planned|plan"):
        exp.audit_attempt(attempt, spec=other, plan=plan)
    root = tmp_path / "root"
    wrong = root / "results/secon2027/runs" / other["run_key"] / "attempt-001"
    shutil.copytree(attempt, wrong)
    monkeypatch.setattr(exp, "verify_plan", lambda path, root: plan)
    with pytest.raises(ValueError, match="identity|planned|plan"):
        exp.audit_plan(root / "plan.json", root)
    with pytest.raises(ValueError, match="identity|planned|plan"):
        exp.execute_one(root / "plan.json", root, other)


def test_tested_version_is_bound_to_frozen_version_file(tmp_path):
    root = fixture_source(tmp_path)
    snapshot = exp.freeze_source(root, tmp_path / "snapshots", "docs/contract.md")
    directory = tmp_path / "snapshots" / snapshot["snapshot_id"]
    descriptor = exp.read(directory / "snapshot.json")
    descriptor["tested_version"] = "9.9.9"
    (directory / "snapshot.json").write_text(json.dumps(descriptor))
    with pytest.raises(ValueError, match="version"):
        exp.verify_snapshot(directory)


@pytest.mark.parametrize("field,value", [("status", "retired"), ("purpose", "validation"), ("seeds", [92001])])
def test_registry_changes_cannot_authorize_a_previously_frozen_plan(tmp_path, field, value):
    root, plan_path, registry_path, plan = freeze_fixture(tmp_path)
    registry = exp.read(registry_path)
    registry["cohorts"]["fixture-only"][field] = value
    registry_path.write_text(json.dumps(registry))
    with pytest.raises(ValueError):
        exp.verify_plan(plan_path, root)


def test_exposure_of_first_arm_keeps_other_frozen_arm_eligible(tmp_path):
    root, plan_path, registry_path, plan = freeze_fixture(tmp_path)
    spec = plan["runs"][0]
    exp.mark_exposed(root, plan, spec, root / "results/fixture-attempt")
    assert exp.read(registry_path)["cohorts"]["fixture-only"]["status"] == "exposed"
    assert exp.verify_plan(plan_path, root)["runs"][1] == plan["runs"][1]


def test_invalid_protocol_rejected_before_registration_or_exposure(tmp_path):
    root = fixture_source(tmp_path)
    matrix = fixture_matrix()
    matrix["arms"][0]["protocol"] = "invented-protocol"
    registry_path = root / "registry.json"
    initial = {"cohorts": {"fixture-only": {"purpose": "development", "seeds": [92000], "status": "reserved"}}, "exclusions": []}
    exp.write_new(registry_path, initial)
    exp.write_new(root / "matrix.json", matrix)
    with pytest.raises(ValueError):
        exp.freeze(root / "matrix.json", registry_path, root, root / "plan.json")
    assert exp.read(registry_path) == initial
    assert not (root / "plan.json").exists()


def test_impossible_destination_delivery_cannot_pass_independent_audit():
    spec = exp.generate_runs(fixture_matrix(), "fixture")[0]
    flow = dict(flow_id=1, src=0, dst=3, enqueued_at=1.0, deadline_at=31.0,
                accepted_ack_at=None, first_delivery_at=2.0,
                ack_by_deadline=False, delivery_by_deadline=True)
    row = dict(seed=92000, protocol="meshecho-cpr", scheduled_unicast_flows=1,
               ack_by_deadline=0, ack_pdr_deadline=0.0, delivery_by_deadline=1,
               delivery_pdr_deadline=1.0, started_request_count=0, tx_ledger_airtime_s=0.0)
    bundle = SimpleNamespace(flows=[flow], transmissions=[], acks=[], rx_attempts=[],
                             requests=[], actions=[], runs=[row], identities={92000: {
                                 "application_trace": [{"flow_id": 1, "src": 0, "dst": 3, "time": 1.0}]}})
    with pytest.raises(ValueError):
        exp.audit_bundle(bundle, spec)


def recovery_fixture(tmp_path, monkeypatch):
    root, key = tmp_path / "recovery", "fixture-run-key"
    spec = {"run_key": key, "seed": 92000, "arm": {"protocol": "meshecho-cpr"}}
    plan = {"runs": [spec], "plan_sha256": "review-plan"}
    monkeypatch.setattr(exp, "verify_plan", lambda path, repo: plan)
    monkeypatch.setattr(exp, "process_alive", lambda pid: False)
    monkeypatch.setattr(exp.subprocess, "check_output", lambda *args, **kwargs: "")
    lock = root / "results/secon2027/run_state" / (key + ".lock")
    exp.write_new(lock, {"pid": 40001, "hostname": socket.gethostname(), "run_key": key})
    attempt = root / "results/secon2027/runs" / key / "attempt-001"
    exp.write_new(attempt / "started.json", {"spec": spec, "plan_sha256": "review-plan"})
    (attempt / "stdout.log").write_text("partial output retained\n")
    return root, key, spec, lock, attempt


def test_dead_process_recovery_preserves_partial_evidence_and_archives_lock(tmp_path, monkeypatch):
    root, key, spec, lock, attempt = recovery_fixture(tmp_path, monkeypatch)
    holder = exp.read(lock)
    result = exp.recover_interrupted(root / "plan.json", root, key, "test process interruption")
    assert not lock.exists()
    assert not result["completed_preserved"]
    assert (attempt / "stdout.log").read_text() == "partial output retained\n"
    assert exp.read(attempt / "failure.json")["kind"] == "infrastructure"
    archive = root / "results/secon2027/recoveries" / key
    assert exp.read(archive / "attempt-001.lock") == holder
    assert exp.read(archive / "attempt-001.json")["reason"] == "test process interruption"


@pytest.mark.parametrize("live", ["parent", "recorded-worker", "unrecorded-worker"])
def test_recovery_refuses_any_live_parent_or_worker(tmp_path, monkeypatch, live):
    root, key, spec, lock, attempt = recovery_fixture(tmp_path, monkeypatch)
    if live == "parent":
        monkeypatch.setattr(exp, "process_alive", lambda pid: pid == 40001)
    elif live == "recorded-worker":
        exp.write_new(attempt / "worker_runtime.json", {"pid": 40002, "hostname": socket.gethostname(),
                                                       "run_key": key, "plan_sha256": "review-plan"})
        monkeypatch.setattr(exp, "process_alive", lambda pid: pid == 40002)
    else:
        monkeypatch.setattr(exp.subprocess, "check_output", lambda *args, **kwargs:
                            "40003 python frozen.py _worker --run-key " + key)
    with pytest.raises(ValueError):
        exp.recover_interrupted(root / "plan.json", root, key, "fixture")
    assert lock.exists()
    assert not (attempt / "failure.json").exists()


def test_recovery_cannot_reclassify_scientific_failure(tmp_path, monkeypatch):
    root, key, spec, lock, attempt = recovery_fixture(tmp_path, monkeypatch)
    failure = {"kind": "scientific-or-worker", "error": "bad invariant"}
    exp.write_new(attempt / "failure.json", failure)
    with pytest.raises(ValueError):
        exp.recover_interrupted(root / "plan.json", root, key, "fixture")
    assert exp.read(attempt / "failure.json") == failure
    assert lock.exists()


def test_recovery_cannot_bless_an_attempt_from_a_different_planned_key(tmp_path, monkeypatch):
    root, key, spec, lock, attempt = recovery_fixture(tmp_path, monkeypatch)
    wrong = copy.deepcopy(spec)
    wrong["run_key"] = "another-key"
    (attempt / "started.json").write_text(json.dumps({"spec": wrong, "plan_sha256": "review-plan"}))
    with pytest.raises(ValueError):
        exp.recover_interrupted(root / "plan.json", root, key, "fixture")
    assert lock.exists()
    assert not (attempt / "failure.json").exists()


@pytest.mark.parametrize("markers", [(None, None), (None, 2)])
def test_cold_source_cannot_transmit_duplicate_stage_or_recovery(markers):
    spec = exp.generate_runs(fixture_matrix(), "fixture")[0]
    flow = dict(flow_id=1, src=0, dst=3, enqueued_at=1.0, deadline_at=31.0,
                accepted_ack_at=None, first_delivery_at=None, initial_action="F_INITIAL",
                ack_by_deadline=False, delivery_by_deadline=False)
    txs = [dict(tx_id=i + 1, path=[0], sender=0, flow_id=1, origin=0, final_dst=3,
                packet_kind="FLOOD", repair_index=marker, start=float(i + 1), end=float(i + 2))
           for i, marker in enumerate(markers)]
    row = dict(seed=92000, protocol="meshecho-cpr", scheduled_unicast_flows=1,
               ack_by_deadline=0, ack_pdr_deadline=0.0, delivery_by_deadline=0,
               delivery_pdr_deadline=0.0, started_request_count=2, tx_ledger_airtime_s=2.0)
    bundle = SimpleNamespace(flows=[flow], transmissions=txs, acks=[], rx_attempts=[],
                             requests=[], actions=[], runs=[row], identities={92000: {
                                 "application_trace": [{"flow_id": 1, "src": 0, "dst": 3, "time": 1.0}]}})
    with pytest.raises(ValueError):
        exp.audit_bundle(bundle, spec)


def test_formal_gate_cannot_accept_three_scenarios_without_full_baseline_coverage(tmp_path, monkeypatch):
    root = fixture_source(tmp_path)
    for rel in exp.METHOD_FILES:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# deterministic method fixture\n")
    pilot_matrix = fixture_matrix()
    pilot_matrix["arms"] = pilot_matrix["arms"][:1]
    pilot_matrix["cases"] = [dict(pilot_matrix["cases"][0], id=scenario,
                                 scenario=scenario, configuration="default") for scenario in ("S1", "S2", "S3")]
    pilot = {"matrix": pilot_matrix, "runs": exp.generate_runs(pilot_matrix, "pilot-source"),
             "snapshot_path": "pilot-snapshot"}
    monkeypatch.setattr(exp, "verify_plan", lambda path, repo: pilot)
    monkeypatch.setattr(exp, "audit_plan", lambda path, repo: {
        "status": "complete", "plan_sha256": "pilot-plan", "completed": [{"wall_seconds": 1.0}] * 3})
    gate = {"status": "passed", "method_frozen": True,
            "method_source_sha256": {rel: exp.sha(root / rel) for rel in exp.METHOD_FILES},
            "pilot_plan_path": "pilot-plan.json", "pilot_plan_sha256": "pilot-plan",
            "pilot_budget": {"completed_runs": 3, "total_wall_seconds": 3.0}}
    exp.write_new(root / "gate.json", gate)
    matrix = fixture_matrix()
    matrix.update(stage="validation", seeds=[92001], development_gate="gate.json")
    exp.write_new(root / "matrix.json", matrix)
    exp.write_new(root / "registry.json", {"cohorts": {"fixture-only": {
        "purpose": "validation", "seeds": [92001], "status": "reserved"}}, "exclusions": []})
    with pytest.raises(ValueError, match="coverage"):
        exp.freeze(root / "matrix.json", root / "registry.json", root, root / "plan.json")
    assert not (root / "plan.json").exists()


def test_overheard_routed_data_is_not_destination_delivery():
    spec = exp.generate_runs(fixture_matrix(), "fixture")[0]
    flow = dict(flow_id=1, src=0, dst=3, enqueued_at=1.0, deadline_at=31.0,
                accepted_ack_at=None, first_delivery_at=2.0, initial_action="R_INITIAL",
                ack_by_deadline=False, delivery_by_deadline=True)
    # Node 3 overhears the 0->1 hop; the DATA receive FSM cannot deliver it
    # until a packet's next path node is node 3.
    tx = dict(tx_id=1, path=[0, 1, 3], path_index=0, sender=0, flow_id=1,
              origin=0, final_dst=3, packet_kind="DATA", repair_index=None,
              start=1.0, end=2.0)
    decoded = dict(tx_id=1, receiver=3, sender=0, decoded=True, reason="success", end=2.0)
    row = dict(seed=92000, protocol="meshecho-cpr", scheduled_unicast_flows=1,
               ack_by_deadline=0, ack_pdr_deadline=0.0, delivery_by_deadline=1,
               delivery_pdr_deadline=1.0, started_request_count=1, tx_ledger_airtime_s=1.0)
    bundle = SimpleNamespace(flows=[flow], transmissions=[tx], acks=[], rx_attempts=[decoded],
                             requests=[], actions=[], runs=[row], identities={92000: {
                                 "application_trace": [{"flow_id": 1, "src": 0, "dst": 3, "time": 1.0}]}})
    with pytest.raises(ValueError):
        exp.audit_bundle(bundle, spec)
