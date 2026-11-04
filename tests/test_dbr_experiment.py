"""Safety and physical-accounting tests for the provisional DBR harness."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

import pytest

from tools import run_dbr_experiment as dbr
from tools.run_sr_experiment import SrCase
from lora_mesh_sim import Packet, Transmission


def _smoke_permit(tmp_path):
    case = SrCase(key="recurring_fading")
    case_json = json.dumps(asdict(case), sort_keys=True, separators=(",", ":"))
    content = {
        "mode": "smoke",
        "seeds": [44200],
        "protocols": list(dbr.ARMS),
        "case_sha256": hashlib.sha256(case_json.encode("ascii")).hexdigest(),
        "application_deadline_s": 30.0,
        "input_sha256": dbr.input_hashes(),
        "prerequisite_manifest_sha256": {},
    }
    path = tmp_path / "smoke.authorization.json"
    path.write_text(json.dumps(content, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _run_fixture_smoke(tmp_path, monkeypatch):
    case = SrCase(
        key="recurring_fading", nodes=4, area_m=1000.0,
        duration_s=10.0, rate_per_min=6.0, pair_mode="random",
        pair_count=0, max_hops=3,
    )
    monkeypatch.setitem(dbr.sr.SR_CASES, "recurring_fading", case)
    monkeypatch.setitem(dbr.SEEDS_BY_MODE, "smoke", (73,))
    monkeypatch.setattr(dbr.sr, "DBR_RESERVED_SEEDS", frozenset({73}))
    frozen = tmp_path / "frozen.md"
    frozen.write_text("# DBR\n\nStatus: frozen\n", encoding="utf-8")
    monkeypatch.setattr(dbr, "CONTRACT_PATH", frozen)
    permit = _smoke_permit(tmp_path)
    permit_data = json.loads(permit.read_text(encoding="utf-8"))
    permit_data["seeds"] = [73]
    permit_data["case_sha256"] = dbr._case_hash(case)
    permit.write_text(json.dumps(permit_data), encoding="utf-8")
    output_dir = tmp_path / "fixture-evidence"
    report = dbr.run_experiment(
        mode="smoke", seeds=(73,), case=case,
        stage_authorization_path=permit, output_dir=output_dir,
    )
    return report, output_dir, case


def _rewrite_artifact_with_matching_hash(output_dir, name, records):
    path = output_dir / name
    path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_sha256"][name] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8")


def test_draft_contract_cannot_open_smoke(monkeypatch):
    def unexpected_capture(*_args, **_kwargs):
        pytest.fail("a draft contract must not start simulation")

    monkeypatch.setattr(dbr, "capture_arm", unexpected_capture)
    with pytest.raises(ValueError, match="frozen"):
        dbr.run_experiment(mode="smoke")


@pytest.mark.parametrize(
    ("mode", "seeds"),
    [
        ("smoke", (44001,)),
        ("development", (44200,)),
        ("holdout", (44001,)),
        ("custom", (73,)),
    ],
)
def test_only_exact_reserved_seed_windows_can_reach_capture(
    tmp_path, monkeypatch, mode, seeds,
):
    frozen = tmp_path / "frozen.md"
    frozen.write_text("# DBR\n\nStatus: frozen\n", encoding="utf-8")
    monkeypatch.setattr(dbr, "CONTRACT_PATH", frozen)
    monkeypatch.setattr(
        dbr, "capture_arm",
        lambda *_args, **_kwargs: pytest.fail("invalid seed must not run"),
    )
    with pytest.raises(ValueError, match="mode|seed"):
        dbr.run_experiment(mode=mode, seeds=seeds)


@pytest.mark.parametrize("mode", ("smoke", "development", "holdout"))
def test_every_real_stage_requires_authorization_before_simulation(
    tmp_path, monkeypatch, mode,
):
    frozen = tmp_path / "frozen.md"
    frozen.write_text("# DBR\n\nStatus: frozen\n", encoding="utf-8")
    monkeypatch.setattr(dbr, "CONTRACT_PATH", frozen)
    monkeypatch.setattr(
        dbr, "capture_arm",
        lambda *_args, **_kwargs: pytest.fail("unlicensed stage must not run"),
    )
    with pytest.raises(ValueError, match="stage authorization"):
        dbr.run_experiment(mode=mode)


def test_real_stage_rejects_changed_case_or_deadline_before_simulation(
    tmp_path, monkeypatch,
):
    frozen = tmp_path / "frozen.md"
    frozen.write_text("# DBR\n\nStatus: frozen\n", encoding="utf-8")
    monkeypatch.setattr(dbr, "CONTRACT_PATH", frozen)
    monkeypatch.setattr(
        dbr, "capture_arm",
        lambda *_args, **_kwargs: pytest.fail("changed case must not run"),
    )
    with pytest.raises(ValueError, match="case|deadline"):
        dbr.run_experiment(mode="smoke", case=SrCase(key="other"))
    with pytest.raises(ValueError, match="case|deadline"):
        dbr.run_experiment(mode="smoke", deadline_s=31.0)


def test_forged_stage_authorization_cannot_start_simulation(tmp_path, monkeypatch):
    frozen = tmp_path / "frozen.md"
    frozen.write_text("# DBR\n\nStatus: frozen\n", encoding="utf-8")
    permit = tmp_path / "smoke.authorization.json"
    permit.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(dbr, "CONTRACT_PATH", frozen)
    monkeypatch.setattr(
        dbr, "capture_arm",
        lambda *_args, **_kwargs: pytest.fail("forged permit must not run"),
    )
    with pytest.raises(ValueError, match="stage authorization"):
        dbr.run_experiment(mode="smoke", stage_authorization_path=permit)


def test_full_transmission_json_round_trip_restores_all_paths(tmp_path):
    transmissions = [
        Transmission(
            tx_id=1, sender=1,
            packet=Packet(
                kind="DATA", flow_id=9, origin=1, final_dst=3, ttl=6,
                created_at=1.0, protocol="meshecho-dbr", request_id=9,
                path=(1, 2, 3), repair_index=3,
            ),
            start=4.0, end=4.21,
        ),
        Transmission(
            tx_id=2, sender=3,
            packet=Packet(
                kind="ACK", flow_id=9, origin=3, final_dst=1, ttl=6,
                created_at=4.21, protocol="meshecho-dbr", request_id=9,
                path=(1, 2, 3), learned_path=(3, 2, 1),
                alternate_path=(1, 4, 3), app_payload=False,
            ),
            start=4.25, end=4.39,
        ),
    ]
    path = tmp_path / "tx.jsonl"

    dbr.write_transmissions(path, transmissions)
    loaded = dbr.load_transmissions(path)

    assert loaded == transmissions
    assert isinstance(loaded[1].packet.path, tuple)
    assert isinstance(loaded[1].packet.learned_path, tuple)
    assert isinstance(loaded[1].packet.alternate_path, tuple)


def test_loaded_marker3_tx_and_ack_backup_bytes_recompute_physical_cost(tmp_path):
    backup = Packet(
        kind="DATA", flow_id=12, origin=1, final_dst=3, ttl=6,
        created_at=610.0, protocol="meshecho-dbr", request_id=12,
        path=(1, 4, 3), repair_index=3,
    )
    ack = Packet(
        kind="ACK", flow_id=12, origin=3, final_dst=1, ttl=6,
        created_at=629.8, protocol="meshecho-dbr", request_id=12,
        path=(1, 2, 3), learned_path=(3, 2, 1),
        alternate_path=(1, 4, 3), app_payload=False,
    )
    transmissions = [
        Transmission(1, 1, backup, 629.90, 630.12),
        Transmission(2, 3, ack, 629.95, 630.11),
        Transmission(3, 4, backup, 630.01, 630.23),
    ]
    path = tmp_path / "physical.jsonl"
    dbr.write_transmissions(path, transmissions)

    cost = dbr.physical_cost(dbr.load_transmissions(path), 630.0, 32)

    assert cost["windowed_tx_count"] == 2
    assert cost["whole_network_tx_airtime_s"] == pytest.approx(0.38)
    assert cost["windowed_tx_bytes"] == (
        backup.wire_size_bytes(32) + ack.wire_size_bytes(32)
    )
    assert cost["windowed_ack_bytes"] == ack.wire_size_bytes(32)
    assert cost["windowed_ack_backup_field_bytes"] == 7
    assert cost["windowed_backup_data_source_tx"] == 1
    assert cost["windowed_backup_data_tx"] == 1


def test_authorized_smoke_requires_new_output_directory_before_capture(
    tmp_path, monkeypatch,
):
    frozen = tmp_path / "frozen.md"
    frozen.write_text("# DBR\n\nStatus: frozen\n", encoding="utf-8")
    monkeypatch.setattr(dbr, "CONTRACT_PATH", frozen)
    permit = _smoke_permit(tmp_path)
    monkeypatch.setattr(
        dbr, "capture_arm",
        lambda *_args, **_kwargs: pytest.fail("missing output must not run"),
    )
    with pytest.raises(ValueError, match="output directory"):
        dbr.run_experiment(mode="smoke", stage_authorization_path=permit)
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(ValueError, match="output directory"):
        dbr.run_experiment(
            mode="smoke", stage_authorization_path=permit, output_dir=existing,
        )


def test_direct_capture_cannot_bypass_stage_gate(monkeypatch):
    monkeypatch.setattr(
        dbr.sr, "run_one_sr",
        lambda *_args, **_kwargs: pytest.fail("reserved seed must not run"),
    )
    with pytest.raises(ValueError, match="frozen|authorization"):
        dbr.capture_arm(
            SrCase(key="recurring_fading"), "meshecho-dbr", 44200, 30.0,
        )


def test_imported_capture_token_cannot_bypass_draft_contract(monkeypatch):
    monkeypatch.setattr(
        dbr.sr, "run_one_sr",
        lambda *_args, **_kwargs: pytest.fail("reserved seed must not run"),
    )
    with pytest.raises(ValueError, match="frozen|authorization"):
        dbr.capture_arm(
            SrCase(key="recurring_fading"), "meshecho-dbr", 44200, 30.0,
            research_authorization=dbr._CAPTURE_AUTHORIZATION,
        )


@pytest.mark.parametrize(
    ("protocol", "seed"),
    (
        ("meshecho-dbr", 44200),
        ("meshtastic", 44001),
        ("meshecho-dbr-fixed-f", 44101),
    ),
)
def test_generic_sr_entry_rejects_unlicensed_reserved_dbr_seed_before_topology(
    monkeypatch, protocol, seed,
):
    monkeypatch.setattr(
        dbr.sr, "generate_nodes",
        lambda *_args, **_kwargs: pytest.fail("reserved topology must not generate"),
    )
    with pytest.raises(ValueError, match="frozen|authorization"):
        dbr.sr.run_one_sr(
            dbr.sr.SR_CASES["recurring_fading"], protocol, seed, 30.0,
        )


def test_generic_sr_entry_rejects_direct_call_even_with_fixture_permit(
    tmp_path, monkeypatch,
):
    case = dbr.sr.SR_CASES["recurring_fading"]
    monkeypatch.setitem(dbr.SEEDS_BY_MODE, "smoke", (73,))
    monkeypatch.setattr(dbr.sr, "DBR_RESERVED_SEEDS", frozenset({73}))
    frozen = tmp_path / "frozen.md"
    frozen.write_text("# DBR\n\nStatus: frozen\n", encoding="utf-8")
    monkeypatch.setattr(dbr, "CONTRACT_PATH", frozen)
    permit = _smoke_permit(tmp_path)
    permit_data = json.loads(permit.read_text(encoding="utf-8"))
    permit_data["seeds"] = [73]
    permit.write_text(json.dumps(permit_data), encoding="utf-8")
    monkeypatch.setattr(
        dbr.sr, "generate_nodes",
        lambda *_args, **_kwargs: pytest.fail("direct call must not generate topology"),
    )

    with pytest.raises(ValueError, match="stage authorization"):
        dbr.sr.run_one_sr(
            case, "meshecho-dbr", 73, 30.0,
            stage_authorization_path=permit,
        )


def test_authorization_hashes_include_algorithm_behavior_tests():
    assert "tests/test_meshecho_dbr.py" in dbr.input_hashes()


def test_strict_replay_rejects_changed_raw_capture(tmp_path, monkeypatch):
    frozen = tmp_path / "frozen.md"
    frozen.write_text("# DBR\n\nStatus: frozen\n", encoding="utf-8")
    monkeypatch.setattr(dbr, "CONTRACT_PATH", frozen)
    permit = _smoke_permit(tmp_path)
    count = 0

    def changing_capture(_case, protocol, seed, _deadline_s, **_kwargs):
        nonlocal count
        count += 1
        return {"protocol": protocol, "seed": seed, "tx_trace": [count]}

    monkeypatch.setattr(dbr, "capture_arm", changing_capture)
    with pytest.raises(ValueError, match="strict DBR replay"):
        dbr.run_experiment(
            mode="smoke", stage_authorization_path=permit,
            output_dir=tmp_path / "replay",
        )
    assert count == 2


@pytest.mark.parametrize("mode", ("development", "holdout"))
def test_later_cohorts_remain_closed_without_predecessor_audit(
    tmp_path, monkeypatch, mode,
):
    frozen = tmp_path / "frozen.md"
    frozen.write_text("# DBR\n\nStatus: frozen\n", encoding="utf-8")
    monkeypatch.setattr(dbr, "CONTRACT_PATH", frozen)
    smoke = _smoke_permit(tmp_path)
    permit_data = json.loads(smoke.read_text(encoding="utf-8"))
    permit_data["mode"] = mode
    permit_data["seeds"] = list(dbr.SEEDS_BY_MODE[mode])
    later_permit = tmp_path / f"{mode}.authorization.json"
    later_permit.write_text(json.dumps(permit_data), encoding="utf-8")
    monkeypatch.setattr(
        dbr, "capture_arm",
        lambda *_args, **_kwargs: pytest.fail("later cohort must stay closed"),
    )
    with pytest.raises(ValueError, match="predecessor artifact audit"):
        dbr.run_experiment(mode=mode, stage_authorization_path=later_permit)


def test_small_nonreserved_fixture_captures_complete_five_arm_evidence(
    tmp_path, monkeypatch,
):
    report, output_dir, _case = _run_fixture_smoke(tmp_path, monkeypatch)

    assert len(report["runs"]) == 5
    assert all(run["row"]["scheduled_unicast_flows"] >= 1
               for run in report["runs"])
    assert all(run["transmissions"] and run["flows"]
               and run["random_state_sha256"]
               and run["channel_random_state_sha256"]
               for run in report["runs"])
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    for name in ("runs.jsonl", "flows.jsonl", "actions.jsonl", "transmissions.jsonl"):
        payload = (output_dir / name).read_bytes()
        assert payload
        assert manifest["artifact_sha256"][name] == hashlib.sha256(payload).hexdigest()
    assert report["manifest_path"] == str(output_dir / "manifest.json")
    assert report["audit"] == dbr.audit_artifacts(output_dir / "manifest.json")


def test_reloaded_fixture_manifest_verifies_all_artifact_hashes(
    tmp_path, monkeypatch,
):
    _report, output_dir, _case = _run_fixture_smoke(tmp_path, monkeypatch)

    audit = dbr.audit_artifacts(output_dir / "manifest.json")

    assert audit["runs"] == 5
    assert audit["scheduled_unicast_flows"] > 0
    with (output_dir / "transmissions.jsonl").open("a", encoding="utf-8") as output:
        output.write("{}\n")
    with pytest.raises(ValueError, match="SHA-256|hash"):
        dbr.audit_artifacts(output_dir / "manifest.json")


def test_archived_manifest_requires_exact_replay_claim(tmp_path, monkeypatch):
    _report, output_dir, _case = _run_fixture_smoke(tmp_path, monkeypatch)
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["strict_replay_exact"] = False
    manifest_path.write_text(json.dumps(manifest, sort_keys=True) + "\n",
                             encoding="utf-8")

    with pytest.raises(ValueError, match="strict replay"):
        dbr.audit_artifacts(manifest_path)


def test_reloaded_tx_recomputes_physical_cost_even_after_rehash(
    tmp_path, monkeypatch,
):
    _report, output_dir, _case = _run_fixture_smoke(tmp_path, monkeypatch)
    run_records = [json.loads(line) for line in
                   (output_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all("physical" in record for record in run_records)
    tx_records = [json.loads(line) for line in
                  (output_dir / "transmissions.jsonl").read_text(encoding="utf-8").splitlines()]
    tx_records[0]["end"] += 0.1
    _rewrite_artifact_with_matching_hash(output_dir, "transmissions.jsonl", tx_records)

    with pytest.raises(ValueError, match="physical|airtime"):
        dbr.audit_artifacts(output_dir / "manifest.json")


def test_reloaded_tx_checks_reported_airtime_even_after_rehash(
    tmp_path, monkeypatch,
):
    _report, output_dir, _case = _run_fixture_smoke(tmp_path, monkeypatch)
    runs = [json.loads(line) for line in
            (output_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    runs[0]["row"]["whole_network_tx_airtime_s"] += 1.0
    _rewrite_artifact_with_matching_hash(output_dir, "runs.jsonl", runs)

    with pytest.raises(ValueError, match="physical row"):
        dbr.audit_artifacts(output_dir / "manifest.json")


def test_reloaded_flows_enforce_all_scheduled_denominator_after_rehash(
    tmp_path, monkeypatch,
):
    _report, output_dir, _case = _run_fixture_smoke(tmp_path, monkeypatch)
    flows = [json.loads(line) for line in
             (output_dir / "flows.jsonl").read_text(encoding="utf-8").splitlines()]
    flows.pop(0)
    _rewrite_artifact_with_matching_hash(output_dir, "flows.jsonl", flows)

    with pytest.raises(ValueError, match="scheduled|denominator|flow"):
        dbr.audit_artifacts(output_dir / "manifest.json")


def test_reloaded_arms_require_the_same_scheduled_trace_after_rehash(
    tmp_path, monkeypatch,
):
    _report, output_dir, _case = _run_fixture_smoke(tmp_path, monkeypatch)
    flows = [json.loads(line) for line in
             (output_dir / "flows.jsonl").read_text(encoding="utf-8").splitlines()]
    runs = [json.loads(line) for line in
            (output_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    focus = flows[0]
    focus["src"] += 100
    trace = sorted((flow["enqueued_at"], flow["src"], flow["dst"], flow["flow_id"])
                   for flow in flows if flow["protocol"] == focus["protocol"])
    for run in runs:
        if run["protocol"] == focus["protocol"]:
            run["row"]["scheduled_trace_sha256"] = hashlib.sha256(
                json.dumps(trace, separators=(",", ":")).encode("ascii")
            ).hexdigest()
    _rewrite_artifact_with_matching_hash(output_dir, "flows.jsonl", flows)
    _rewrite_artifact_with_matching_hash(output_dir, "runs.jsonl", runs)

    with pytest.raises(ValueError, match="paired|cross-arm|trace parity"):
        dbr.audit_artifacts(output_dir / "manifest.json")


def test_manifest_audits_the_full_strict_replay_digest_after_rehash(
    tmp_path, monkeypatch,
):
    _report, output_dir, _case = _run_fixture_smoke(tmp_path, monkeypatch)
    runs = [json.loads(line) for line in
            (output_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all(len(run["strict_replay_sha256"]) == 64 for run in runs)
    runs[0]["strict_replay_sha256"] = "0" * 64
    _rewrite_artifact_with_matching_hash(output_dir, "runs.jsonl", runs)

    with pytest.raises(ValueError, match="strict replay"):
        dbr.audit_artifacts(output_dir / "manifest.json")


def _append_action_and_reseal(output_dir, forged):
    runs = [json.loads(line) for line in
            (output_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    flows = [json.loads(line) for line in
             (output_dir / "flows.jsonl").read_text(encoding="utf-8").splitlines()]
    actions = [json.loads(line) for line in
               (output_dir / "actions.jsonl").read_text(encoding="utf-8").splitlines()]
    transmissions = [json.loads(line) for line in
                     (output_dir / "transmissions.jsonl").read_text(encoding="utf-8").splitlines()]
    key = (forged["seed"], forged["protocol"])
    run = next(item for item in runs
               if (item["seed"], item["protocol"]) == key)
    actions.append(forged)
    replay_record = {
        **{name: value for name, value in run.items()
           if name != "strict_replay_sha256"},
        "flows": [flow for flow in flows
                  if (flow["seed"], flow["protocol"]) == key],
        "actions": [action for action in actions
                    if (action["seed"], action["protocol"]) == key],
        "transmissions": [
            {name: value for name, value in tx.items()
             if name not in {"seed", "protocol"}}
            for tx in transmissions
            if (tx["seed"], tx["protocol"]) == key
        ],
    }
    run["strict_replay_sha256"] = dbr._json_hash(replay_record)
    _rewrite_artifact_with_matching_hash(output_dir, "actions.jsonl", actions)
    _rewrite_artifact_with_matching_hash(output_dir, "runs.jsonl", runs)


def test_reloaded_backup_action_requires_a_matching_physical_start(
    tmp_path, monkeypatch,
):
    _report, output_dir, case = _run_fixture_smoke(tmp_path, monkeypatch)
    _append_action_and_reseal(output_dir, {
        "case": case.key, "seed": 73, "protocol": "meshecho-dbr",
        "event": "dbr_backup_tx", "flow_id": 999999,
        "src": 0, "dst": 3, "time": 1.0, "end": 1.1,
        "path": [0, 2, 3],
    })

    with pytest.raises(ValueError, match="backup action|physical TX"):
        dbr.audit_artifacts(output_dir / "manifest.json")


def test_reloaded_flood_recovery_action_requires_a_matching_physical_start(
    tmp_path, monkeypatch,
):
    _report, output_dir, case = _run_fixture_smoke(tmp_path, monkeypatch)
    _append_action_and_reseal(output_dir, {
        "case": case.key, "seed": 73, "protocol": "meshecho-dbr",
        "event": "dhr_recovery_tx", "flow_id": 999999,
        "src": 0, "dst": 3, "time": 1.0, "end": 1.1,
        "action": "F", "repair_index": 2,
    })

    with pytest.raises(ValueError, match="recovery action|physical TX"):
        dbr.audit_artifacts(output_dir / "manifest.json")


def test_reloaded_tx_recomputes_tx_energy_without_claiming_rx_energy(
    tmp_path, monkeypatch,
):
    _report, output_dir, _case = _run_fixture_smoke(tmp_path, monkeypatch)
    runs = [json.loads(line) for line in
            (output_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert all("windowed_backup_data_source_tx" in run["physical"] for run in runs)
    runs[0]["row"]["tx_energy_j"] += 1.0
    _rewrite_artifact_with_matching_hash(output_dir, "runs.jsonl", runs)

    with pytest.raises(ValueError, match="TX energy"):
        dbr.audit_artifacts(output_dir / "manifest.json")


def test_archived_stage_authorization_matches_manifest_after_rehash(
    tmp_path, monkeypatch,
):
    _report, output_dir, _case = _run_fixture_smoke(tmp_path, monkeypatch)
    authorization_path = output_dir / "authorization.json"
    assert authorization_path.exists()
    authorization = json.loads(authorization_path.read_text(encoding="utf-8"))
    authorization["mode"] = "holdout"
    authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(authorization_path.read_bytes()).hexdigest()
    manifest["artifact_sha256"]["authorization.json"] = digest
    manifest["stage_authorization_sha256"] = digest
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="authorization"):
        dbr.audit_artifacts(manifest_path)


def test_reloaded_tx_duration_matches_packet_toa_after_rehash(
    tmp_path, monkeypatch,
):
    _report, output_dir, _case = _run_fixture_smoke(tmp_path, monkeypatch)
    tx_records = [json.loads(line) for line in
                  (output_dir / "transmissions.jsonl").read_text(encoding="utf-8").splitlines()]
    tx_records[0]["end"] += 0.1
    _rewrite_artifact_with_matching_hash(output_dir, "transmissions.jsonl", tx_records)

    with pytest.raises(ValueError, match="ToA"):
        dbr.audit_artifacts(output_dir / "manifest.json")
