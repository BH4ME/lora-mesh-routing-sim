"""Behavioral checks for the passive first-hop receipt feasibility screen."""

import hashlib
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from lora_mesh_sim import (
    MeshEchoDHRDelayedAck, Node, Packet, RadioConfig, RouteEntry,
)
from tools.diagnose_first_hop_receipt_screen import (
    PassiveFirstHopSimulator, analyze_screen, run_diagnostic, run_report,
    seeds_for_mode, validate_manifest, write_report,
)
from tools.diagnose_delayed_ack_rx import capture_run
from tools import diagnose_first_hop_receipt_screen as receipt_screen
from tools import run_sr_experiment as sr
from tools.run_sr_experiment import SR_CASES


def stage_permit(tmp_path, mode, *, prerequisite_sha256=None):
    case = SR_CASES["recurring_fading"]
    permit = {
        "mode": mode,
        "seeds": list(seeds_for_mode(mode)),
        "protocol": receipt_screen.PROTOCOL,
        "case_sha256": receipt_screen._sha256_json(asdict(case)),
        "application_deadline_s": 30.0,
        "input_sha256": receipt_screen._source_hashes(),
        "prerequisite_manifest_sha256": prerequisite_sha256 or {},
    }
    path = tmp_path / f"{mode}.authorization.json"
    path.write_text(json.dumps(permit, sort_keys=True) + "\n", encoding="utf-8")
    return path


def routed_fixture(*, cutoff_s=5.0, count=1, tx_power_dbm=17.0,
                   source_available_at_s=0.0,
                   second_at_first_early=False, second_at_s=None):
    sim = PassiveFirstHopSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0), Node(2, 20.0, 0.0)],
        RadioConfig(sf=7, tx_power_dbm=tx_power_dbm, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(), seed=73, max_hops=3,
        independent_random_streams=True,
    )
    sim.protocol.route_cache[0][2] = RouteEntry(
        created_at=0.0, expires_at=100.0, path=(0, 1, 2), confidence=1.0,
    )
    sim.nodes[0].tx_available_at = source_available_at_s
    for flow_id in range(1, count + 1):
        at = 0.0
        if flow_id == 2 and second_at_s is not None:
            at = second_at_s
        if flow_id == 2 and second_at_first_early:
            first = Packet(
                kind="DATA", flow_id=1, origin=0, final_dst=2,
                ttl=3, created_at=0.0, protocol=sim.protocol.name,
                request_id=1, path=(0, 1, 2),
            )
            at = sim.radio.packet_toa_s(first) + 1.0
        sim.schedule(at, "app_send", (0, 2, flow_id))
    sim.run(cutoff_s)
    flows = [{
        "flow_id": flow_id, "src": 0, "dst": 2,
        "registered": True,
        "enqueued_at": sim.metrics.flows[flow_id].created_at,
        "deadline_at": sim.metrics.flows[flow_id].created_at + 30.0,
        "acked_at": sim.metrics.flows[flow_id].acked_at,
        "ack_by_deadline": (
            sim.metrics.flows[flow_id].acked_at is not None
            and sim.metrics.flows[flow_id].acked_at
            <= sim.metrics.flows[flow_id].created_at + 30.0
        ),
        "delivery_by_deadline": (
            sim.metrics.flows[flow_id].delivered_at is not None
            and sim.metrics.flows[flow_id].delivered_at
            <= sim.metrics.flows[flow_id].created_at + 30.0
        ),
    } for flow_id in range(1, count + 1)]
    return sim, flows


def test_seed73_passive_screen_has_stock_parity_and_exact_replay():
    result = run_diagnostic(73, case=SR_CASES["recurring_fading"])

    assert result["parity"]["exact"] is True
    assert result["strict_replay_exact"] is True
    assert result["row"]["scheduled_unicast_flows"] == len(result["flows"])
    assert result["protocol"] == "meshecho-dhr-flood-ack-delay"


def test_seed73_reports_every_initial_r_and_charges_nominal_receipts():
    result = run_diagnostic(73, case=SR_CASES["recurring_fading"])
    expected = {
        action["flow_id"] for action in result["actions"]
        if action.get("event", "decision") == "decision"
        and action["action"] == "R"
    }
    rows = result["initial_r_rows"]

    assert expected == {row["flow_id"] for row in rows}
    assert len(rows) == len(expected) == result["summary"]["initial_r_flows"]
    assert len(result["first_hop_decodes"]) == sum(
        not row["first_hop_censored"] for row in rows
    )
    assert all(isinstance(row["first_hop_decoded"], bool) for row in rows)
    assert result["summary"]["receipt_wire_bytes"] == 17
    assert result["summary"]["receipt_toa_s"] == pytest.approx(0.051456)
    assert result["summary"]["receipt_lower_bound_airtime_s"] == pytest.approx(
        result["summary"]["decoded_multihop_first_hops"] * 0.051456
    )
    assert result["summary"]["receipt_upper_coverage_airtime_s"] == pytest.approx(
        result["summary"]["multihop_initial_r_flows"] * 0.051456
    )


def test_late_ending_initial_r_is_censored_not_physical_failure():
    sim, flows = routed_fixture(cutoff_s=30.0, source_available_at_s=29.99)

    result = analyze_screen(
        sim, flows, sim.protocol.action_events, cutoff_s=30.0,
    )

    assert len(result["initial_r_rows"]) == 1
    row = result["initial_r_rows"][0]
    assert row["first_hop_censored"] is True
    assert row["first_hop_decoded"] is None
    assert result["summary"]["censored_multihop_initial_r_flows"] == 1
    assert result["summary"]["failed_multihop_no_guard_ack"] == 0


def test_queued_initial_r_starting_after_deadline_stays_in_denominator():
    sim, flows = routed_fixture(
        cutoff_s=31.0, source_available_at_s=30.01,
        tx_power_dbm=-120.0,
    )

    result = analyze_screen(
        sim, flows, sim.protocol.action_events, cutoff_s=31.0,
    )

    row = result["initial_r_rows"][0]
    assert row["initial_r_start_at_s"] > row["deadline_at_s"]
    assert row["initial_r_started_by_deadline"] is False
    assert row["nominal_early_f_admitted"] is False
    assert result["summary"]["late_initial_r_starts"] == 1


def test_active_capacity_drop_remains_exposed_but_cannot_pass_gate2():
    sim, flows = routed_fixture(
        cutoff_s=30.0, count=9, tx_power_dbm=-60.0,
    )
    drops = [action for action in sim.protocol.action_events
             if action["event"] == "dhr_state_drop"]
    assert len(drops) == 1

    result = analyze_screen(
        sim, flows, sim.protocol.action_events, cutoff_s=30.0,
    )

    row = next(row for row in result["initial_r_rows"]
               if row["flow_id"] == drops[0]["flow_id"])
    assert row["failed_multihop_no_initial_ack"] is True
    assert row["dhr_state_drop_at_initial_start"] is True
    assert row["residual_unacked_early_opportunity"] is False
    assert result["summary"]["active_capacity_excluded_failures"] == 1


def test_same_time_source_tx_blocks_nominal_early_start():
    sim, flows = routed_fixture(
        cutoff_s=5.0, count=2, tx_power_dbm=-120.0,
        second_at_first_early=True,
    )

    result = analyze_screen(
        sim, flows, sim.protocol.action_events, cutoff_s=5.0,
    )

    first = next(row for row in result["initial_r_rows"]
                 if row["flow_id"] == 1)
    assert first["failed_multihop_no_initial_ack"] is True
    assert first["source_busy_at_early_trigger"] is True
    assert first["nominal_early_deadline_fit"] is True
    assert first["residual_unacked_early_opportunity"] is False
    assert result["summary"]["source_busy_at_early_trigger_failures"] >= 1


def test_fixed_trigger_busy_does_not_create_an_early_only_deadline_gain():
    sim, flows = routed_fixture(
        cutoff_s=16.0, count=2, tx_power_dbm=-120.0,
        second_at_s=14.99,
    )

    result = analyze_screen(
        sim, flows, sim.protocol.action_events, cutoff_s=16.0,
    )

    first = next(row for row in result["initial_r_rows"]
                 if row["flow_id"] == 1)
    assert first["nominal_early_deadline_fit"] is True
    assert first["nominal_fixed_deadline_fit"] is True
    assert first["source_busy_at_fixed_trigger"] is True
    assert first["early_only_deadline_admission"] is False
    assert first["early_only_available_admission"] is True


def test_fixed_trigger_tie_counts_other_tx_but_not_own_stock_recovery():
    stock_sim, stock_flows = routed_fixture(
        cutoff_s=16.0, tx_power_dbm=-120.0,
    )
    stock_result = analyze_screen(
        stock_sim, stock_flows, stock_sim.protocol.action_events,
        cutoff_s=16.0,
    )
    stock_row = stock_result["initial_r_rows"][0]
    assert any(
        tx.packet.flow_id == 1 and tx.packet.kind == "FLOOD"
        and tx.packet.repair_index == 2
        and tx.start == stock_row["nominal_fixed_trigger_at_s"]
        for tx in stock_sim.tx_history
    )
    assert stock_row["source_busy_at_fixed_trigger"] is False

    busy_sim, busy_flows = routed_fixture(
        cutoff_s=16.0, count=2, tx_power_dbm=-120.0,
        second_at_s=15.0,
    )
    busy_result = analyze_screen(
        busy_sim, busy_flows, busy_sim.protocol.action_events,
        cutoff_s=16.0,
    )
    busy_row = next(row for row in busy_result["initial_r_rows"]
                    if row["flow_id"] == 1)
    assert any(
        tx.packet.flow_id == 2
        and tx.start == busy_row["nominal_fixed_trigger_at_s"]
        for tx in busy_sim.tx_history
    )
    assert busy_row["source_busy_at_fixed_trigger"] is True


def test_missing_action_event_cannot_be_treated_as_initial_decision():
    sim, flows = routed_fixture()
    actions = [dict(action) for action in sim.protocol.action_events]
    next(action for action in actions if action["event"] == "decision").pop("event")

    with pytest.raises(ValueError, match="missing event"):
        analyze_screen(sim, flows, actions, cutoff_s=5.0)


def test_physical_initial_r_without_decision_fails_reverse_join():
    sim, flows = routed_fixture()
    actions = [action for action in sim.protocol.action_events
               if action["event"] != "decision"]

    with pytest.raises(ValueError, match="unmatched physical initial R"):
        analyze_screen(sim, flows, actions, cutoff_s=5.0)


def test_nominal_flood_deadline_bound_includes_fixed_ack_hold():
    sim, flows = routed_fixture(tx_power_dbm=-120.0)

    result = analyze_screen(
        sim, flows, sim.protocol.action_events, cutoff_s=5.0,
    )

    row = result["initial_r_rows"][0]
    base = sim.protocol.rescue_round_trip_bound_s(tuple(row["path"]))
    flood = Packet(
        kind="FLOOD", flow_id=row["flow_id"], origin=0, final_dst=2,
        ttl=3, created_at=0.0, protocol=sim.protocol.name,
        request_id=row["flow_id"], path=(0,), repair_index=2,
    )
    hold = sim.protocol.reverse_ack_delay_s(flood)

    assert hold == 2.0
    assert row["dhr_base_round_trip_bound_s"] == base
    assert row["delayed_f_ack_hold_s"] == hold
    assert row["nominal_delayed_f_round_trip_bound_s"] == base + hold
    assert row["nominal_early_deadline_fit"] is (
        row["nominal_early_trigger_at_s"] + base + hold
        <= row["deadline_at_s"]
    )


def test_seed73_synthetic_summary_keeps_all_flow_ceilings_and_stage_closed():
    report = run_report((73,), mode="synthetic")

    assert report["seeds"] == [73]
    assert report["summary"]["all_scheduled_unicast_flows"] == 41
    assert report["summary"]["gate_2_residual_unacked_early_opportunities"] == 1
    assert report["summary"]["gate_2_delivered_unacked"] == 1
    assert report["summary"]["gate_2_undelivered_unacked"] == 0
    assert report["summary"]["optimistic_source_ack_pdr_gain_equal_seed_mean"] == pytest.approx(1 / 41)
    assert report["summary"]["optimistic_destination_pdr_gain_equal_seed_mean"] == 0
    assert report["summary"]["necessary_gate_passed"] is None


def test_preregistered_seed_windows_reject_unstaged_or_direct_runs(monkeypatch):
    monkeypatch.setattr(
        sr, "generate_nodes",
        lambda *_args, **_kwargs: pytest.fail("reserved topology generated"),
    )
    assert seeds_for_mode("smoke") == (45000,)
    assert seeds_for_mode("explore") == tuple(range(45001, 45021))
    with pytest.raises(ValueError, match="reserved research seed"):
        run_diagnostic(45000)
    with pytest.raises(ValueError, match="exact preregistered seed"):
        run_report((73,), mode="smoke")
    with pytest.raises(ValueError, match="smoke manifest"):
        run_report(seeds_for_mode("explore"), mode="explore")
    with pytest.raises(ValueError, match="stage authorization"):
        run_report(seeds_for_mode("smoke"), mode="smoke")


def test_internal_capture_passes_stage_permit_through_all_three_runs(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(receipt_screen, "SMOKE_SEEDS", (73,))
    monkeypatch.setattr(sr, "FIRST_HOP_RECEIPT_RESERVED_SEEDS", frozenset({73}))
    permit_path = stage_permit(tmp_path, "smoke")
    original = sr.run_one_sr
    captured = []

    def guarded_runner(case, protocol, seed, deadline_s,
                       *, research_authorization=None,
                       stage_authorization_path=None,
                       smoke_manifest_path=None):
        captured.append((research_authorization, stage_authorization_path))
        if research_authorization is not receipt_screen._RUNNER_AUTHORIZATION:
            raise ValueError("missing stage capability")
        return original(
            case, protocol, seed, deadline_s,
            research_authorization=research_authorization,
            stage_authorization_path=stage_authorization_path,
            smoke_manifest_path=smoke_manifest_path,
        )

    monkeypatch.setattr(sr, "run_one_sr", guarded_runner)

    result = run_diagnostic(
        73, research_authorization=receipt_screen._RUNNER_AUTHORIZATION,
        stage_authorization_path=permit_path,
    )

    assert result["strict_replay_exact"] is True
    assert captured == [
        (receipt_screen._RUNNER_AUTHORIZATION, permit_path)
    ] * 3


def test_seed73_smoke_report_requires_and_records_stage_permit(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(receipt_screen, "SMOKE_SEEDS", (73,))
    monkeypatch.setattr(sr, "FIRST_HOP_RECEIPT_RESERVED_SEEDS", frozenset({73}))
    permit_path = stage_permit(tmp_path, "smoke")

    report = run_report(
        (73,), mode="smoke", stage_authorization_path=permit_path,
    )

    assert report["stage_authorization_sha256"] == hashlib.sha256(
        permit_path.read_bytes()
    ).hexdigest()
    assert report["prerequisite_manifest_sha256"] == {}


def test_seed73_smoke_archive_preserves_and_audits_stage_permit(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(receipt_screen, "SMOKE_SEEDS", (73,))
    monkeypatch.setattr(sr, "FIRST_HOP_RECEIPT_RESERVED_SEEDS", frozenset({73}))
    permit_path = stage_permit(tmp_path, "smoke")
    report = run_report(
        (73,), mode="smoke", stage_authorization_path=permit_path,
    )

    paths = write_report(report, tmp_path / "receipt_smoke")
    validated = validate_manifest(
        paths["manifest"], expected_mode="smoke",
        expected_source_sha256=report["source_sha256"],
        expected_case_sha256=report["case_sha256"],
        expected_deadline_s=30.0, strict_replay=True,
    )

    assert paths["authorization"].read_bytes() == permit_path.read_bytes()
    assert validated["stage_authorization_sha256"] == report[
        "stage_authorization_sha256"
    ]

    changed_permit = json.loads(paths["authorization"].read_bytes())
    changed_permit["mode"] = "explore"
    changed_bytes = (json.dumps(changed_permit, sort_keys=True) + "\n").encode()
    paths["authorization"].write_bytes(changed_bytes)
    manifest = json.loads(paths["manifest"].read_bytes())
    changed_sha256 = hashlib.sha256(changed_bytes).hexdigest()
    manifest["artifacts"]["authorization"]["sha256"] = changed_sha256
    manifest["stage_authorization_sha256"] = changed_sha256
    manifest_data = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    paths["manifest"].write_bytes(manifest_data)
    paths["manifest_sha256"].write_text(
        hashlib.sha256(manifest_data).hexdigest()
        + "  " + paths["manifest"].name + "\n",
        encoding="ascii",
    )
    with pytest.raises(ValueError, match="archived stage authorization"):
        validate_manifest(
            paths["manifest"], expected_mode="smoke",
            expected_source_sha256=report["source_sha256"],
            expected_case_sha256=report["case_sha256"],
            expected_deadline_s=30.0, strict_replay=False,
        )


def test_explore_audits_matching_smoke_at_stage_entry_without_explore_simulation(
    tmp_path, monkeypatch,
):
    monkeypatch.setattr(receipt_screen, "SMOKE_SEEDS", (73,))
    smoke_permit = stage_permit(tmp_path, "smoke")
    smoke_report = run_report(
        (73,), mode="smoke", stage_authorization_path=smoke_permit,
    )
    smoke_paths = write_report(smoke_report, tmp_path / "receipt_smoke")
    smoke_manifest = smoke_paths["manifest"]
    explore_permit = stage_permit(
        tmp_path, "explore",
        prerequisite_sha256={
            "smoke_manifest": hashlib.sha256(smoke_manifest.read_bytes()).hexdigest()
        },
    )
    original = receipt_screen.run_diagnostic
    entered = []

    def stop_explore(seed, *args, **kwargs):
        entered.append(seed)
        if seed in receipt_screen.EXPLORATORY_SEEDS:
            raise RuntimeError("protected explore capture intercepted")
        return original(seed, *args, **kwargs)

    monkeypatch.setattr(receipt_screen, "run_diagnostic", stop_explore)
    with pytest.raises(RuntimeError, match="protected explore capture intercepted"):
        run_report(
            seeds_for_mode("explore"), mode="explore",
            smoke_manifest_path=smoke_manifest,
            stage_authorization_path=explore_permit,
        )
    assert entered == [73, 45001]

    smoke_manifest.write_bytes(smoke_manifest.read_bytes() + b" ")
    monkeypatch.setattr(
        sr, "generate_nodes",
        lambda *_args, **_kwargs: pytest.fail("invalid predecessor generated topology"),
    )
    entered.clear()
    with pytest.raises(ValueError, match="authorization"):
        run_report(
            seeds_for_mode("explore"), mode="explore",
            smoke_manifest_path=smoke_manifest,
            stage_authorization_path=explore_permit,
        )
    assert entered == []


def test_seed73_archive_is_hashed_and_strictly_replayed(tmp_path):
    report = run_report((73,), mode="synthetic")
    paths = write_report(report, tmp_path / "receipt_seed73")

    validated = validate_manifest(
        paths["manifest"], expected_mode="synthetic",
        expected_source_sha256=report["source_sha256"],
        expected_case_sha256=report["case_sha256"], strict_replay=True,
    )

    assert validated["summary"] == report["summary"]
    assert paths["manifest_sha256"].exists()
    assert {"initial_r_rows", "flows", "actions", "transmissions",
            "first_hop_decodes"} <= set(paths)
    with pytest.raises(FileExistsError):
        write_report(report, tmp_path / "receipt_seed73")


def test_strict_replay_rejects_rehashed_forged_decode(tmp_path):
    report = run_report((73,), mode="synthetic")
    paths = write_report(report, tmp_path / "receipt_seed73")
    lines = paths["initial_r_rows"].read_text().splitlines()
    first = json.loads(lines[0])
    first["item"]["first_hop_decoded"] = not first["item"]["first_hop_decoded"]
    lines[0] = json.dumps(first, sort_keys=True, separators=(",", ":"))
    altered = ("\n".join(lines) + "\n").encode()
    paths["initial_r_rows"].write_bytes(altered)
    manifest = json.loads(paths["manifest"].read_bytes())
    manifest["artifacts"]["initial_r_rows"]["sha256"] = hashlib.sha256(
        altered
    ).hexdigest()
    manifest_data = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    paths["manifest"].write_bytes(manifest_data)
    paths["manifest_sha256"].write_text(
        hashlib.sha256(manifest_data).hexdigest()
        + "  " + paths["manifest"].name + "\n"
    )

    with pytest.raises(ValueError, match="strict replay"):
        validate_manifest(
            paths["manifest"], expected_mode="synthetic",
            expected_source_sha256=report["source_sha256"],
            expected_case_sha256=report["case_sha256"], strict_replay=True,
        )


def test_archive_stage_rejects_changed_deadline_before_replay(tmp_path):
    report = run_report((73,), mode="synthetic")
    paths = write_report(report, tmp_path / "receipt_seed73")

    with pytest.raises(ValueError, match="deadline"):
        validate_manifest(
            paths["manifest"], expected_mode="synthetic",
            expected_source_sha256=report["source_sha256"],
            expected_case_sha256=report["case_sha256"],
            expected_deadline_s=29.0, strict_replay=False,
        )


def test_archive_rejects_rehashed_false_passive_label(tmp_path):
    report = run_report((73,), mode="synthetic")
    paths = write_report(report, tmp_path / "receipt_seed73")
    metadata = json.loads(paths["summary"].read_bytes())
    metadata["observed_receipt_transmissions"] = 1
    summary_data = (json.dumps(metadata, sort_keys=True, indent=2) + "\n").encode()
    paths["summary"].write_bytes(summary_data)
    manifest = json.loads(paths["manifest"].read_bytes())
    manifest["artifacts"]["summary"]["sha256"] = hashlib.sha256(
        summary_data
    ).hexdigest()
    manifest_data = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
    paths["manifest"].write_bytes(manifest_data)
    paths["manifest_sha256"].write_text(
        hashlib.sha256(manifest_data).hexdigest()
        + "  " + paths["manifest"].name + "\n"
    )

    with pytest.raises(ValueError, match="passive"):
        validate_manifest(
            paths["manifest"], expected_mode="synthetic",
            expected_source_sha256=report["source_sha256"],
            expected_case_sha256=report["case_sha256"], strict_replay=False,
        )


def test_direct_cli_exposes_staged_smoke_and_exploration_without_running():
    script = Path(__file__).resolve().parents[1] / "tools" / "diagnose_first_hop_receipt_screen.py"

    completed = subprocess.run(
        [sys.executable, str(script), "--help"],
        capture_output=True, text=True, check=True,
    )

    assert "--mode" in completed.stdout
    assert "--stage-authorization" in completed.stdout
    assert "--smoke-manifest" in completed.stdout
    assert "--output-prefix" in completed.stdout


def test_direct_script_reaches_topology_guard_without_duplicate_module_import(tmp_path):
    script = Path(__file__).resolve().parents[1] / "tools" / "diagnose_first_hop_receipt_screen.py"
    permit = stage_permit(tmp_path, "smoke")
    code = """
import runpy
import sys
from tools import run_sr_experiment as sr

def stop_before_topology(*args, **kwargs):
    raise RuntimeError("topology guard reached")

sr.generate_nodes = stop_before_topology
script, permit, output = sys.argv[1:]
sys.argv = [script, "--mode", "smoke", "--stage-authorization", permit,
            "--output-prefix", output]
runpy.run_path(script, run_name="__main__")
"""
    completed = subprocess.run(
        [sys.executable, "-c", code, str(script), str(permit),
         str(tmp_path / "receipt_script_smoke")],
        capture_output=True, text=True, check=False,
        cwd=script.parents[1],
    )

    assert completed.returncode != 0
    assert "topology guard reached" in completed.stderr
    assert "TypeError: function() argument 'code'" not in completed.stderr


def test_nested_predecessor_replay_does_not_pollute_current_capture(tmp_path, monkeypatch):
    case = SR_CASES["recurring_fading"]
    smoke_manifest = tmp_path / "smoke.manifest.json"
    smoke_manifest.write_text("{}\n", encoding="ascii")
    predecessor = {"smoke_manifest": hashlib.sha256(smoke_manifest.read_bytes()).hexdigest()}
    permit = stage_permit(tmp_path, "explore", prerequisite_sha256=predecessor)
    original_runner = sr.run_one_sr

    def replay_predecessor(*args, **kwargs):
        nested = run_diagnostic(73, case=case)
        assert nested["parity"]["exact"] is True

    monkeypatch.setattr(receipt_screen, "validate_manifest", replay_predecessor)

    def staged_fixture_runner(runner_case, protocol, seed, deadline_s):
        receipt_screen._validate_stage(
            "explore", runner_case, deadline_s, permit, smoke_manifest,
        )
        return original_runner(runner_case, protocol, seed, deadline_s)

    evidence, sim = capture_run(
        case, 73, sr.RecordingSimulator, runner=staged_fixture_runner,
    )

    assert type(sim) is sr.RecordingSimulator
    assert evidence.row["seed"] == 73
