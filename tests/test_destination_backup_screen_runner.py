"""Stage and artifact checks for the passive destination backup screen."""

import hashlib
import json
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from tools import run_destination_backup_screen as screen
from tools import run_sr_experiment as sr
from tools.diagnose_delayed_ack_rx import capture_run


def permit(tmp_path, mode, *, seeds=None, input_sha256=None, predecessors=None):
    case = sr.SR_CASES["recurring_fading"]
    document = {
        "mode": mode,
        "seeds": list(screen.seeds_for_mode(mode) if seeds is None else seeds),
        "protocol": screen.PROTOCOL,
        "case_sha256": screen._sha256_json(asdict(case)),
        "application_deadline_s": 30.0,
        "input_sha256": (
            screen._source_hashes() if input_sha256 is None else input_sha256
        ),
        "prerequisite_manifest_sha256": predecessors or {},
    }
    path = tmp_path / f"{mode}.authorization.json"
    path.write_text(json.dumps(document, sort_keys=True) + "\n", encoding="utf-8")
    return path


def fake_run(seed):
    row = {
        "seed": seed, "protocol": screen.PROTOCOL, "case": "recurring_fading",
        "scheduled_unicast_flows": 1, "scheduled_trace_sha256": "a" * 64,
        "whole_network_tx_airtime_s": 100.0,
    }
    flows = [{"flow_id": 1}]
    actions = []
    transmissions = []
    return {
        "seed": seed,
        "row": row,
        "flows": flows,
        "actions": actions,
        "transmissions": transmissions,
        "flood_decodes": [],
        "destination_ack_decodes": [],
        "candidate_epochs": [],
        "rows": [],
        "summary": {"nominated_initial_direct_r": 0},
        "parity": {
            "exact": True,
            "scheduled_trace_sha256": row["scheduled_trace_sha256"],
            "full_row_sha256": screen._sha256_json(row),
            "flow_trace_sha256": screen._sha256_json(flows),
            "action_trace_sha256": screen._sha256_json(actions),
            "full_tx_trace_sha256": screen._sha256_json(transmissions),
            "random_state_sha256": "b" * 64,
            "channel_random_state_sha256": "c" * 64,
        },
        "strict_replay_exact": True,
    }


def test_smoke_requires_stage_authorization_before_capture(tmp_path, monkeypatch):
    monkeypatch.setattr(
        screen, "_capture_seed",
        lambda *_args, **_kwargs: pytest.fail("capture started without a permit"),
    )

    with pytest.raises(ValueError, match="stage authorization is required"):
        screen.run_stage("smoke", tmp_path / "smoke")


def test_smoke_rejects_seed_substitution_before_capture(tmp_path, monkeypatch):
    stage = permit(tmp_path, "smoke", seeds=[46001])
    monkeypatch.setattr(
        screen, "_capture_seed",
        lambda *_args, **_kwargs: pytest.fail("capture started with wrong seed"),
    )

    with pytest.raises(ValueError, match="authorization differs from frozen inputs"):
        screen.run_stage(
            "smoke", tmp_path / "smoke_out", stage_authorization_path=stage,
        )


def test_smoke_rejects_stale_source_hash_before_capture(tmp_path, monkeypatch):
    hashes = screen._source_hashes()
    hashes["tools/diagnose_destination_certified_backup.py"] = "0" * 64
    stage = permit(tmp_path, "smoke", input_sha256=hashes)
    monkeypatch.setattr(
        screen, "_capture_seed",
        lambda *_args, **_kwargs: pytest.fail("capture started with stale code"),
    )

    with pytest.raises(ValueError, match="authorization differs from frozen inputs"):
        screen.run_stage(
            "smoke", tmp_path / "smoke_out", stage_authorization_path=stage,
        )


def test_existing_output_prefix_blocks_capture(tmp_path, monkeypatch):
    stage = permit(tmp_path, "smoke")
    output_prefix = tmp_path / "smoke"
    output_prefix.write_text("existing user data\n", encoding="utf-8")
    monkeypatch.setattr(
        screen, "_capture_seed",
        lambda *_args, **_kwargs: pytest.fail("capture started before output preflight"),
    )

    with pytest.raises(FileExistsError, match="output prefix already exists"):
        screen.run_stage(
            "smoke", output_prefix, stage_authorization_path=stage,
        )


def test_exploration_requires_smoke_manifest_before_capture(tmp_path, monkeypatch):
    stage = permit(tmp_path, "explore")
    monkeypatch.setattr(
        screen, "_capture_seed",
        lambda *_args, **_kwargs: pytest.fail("exploration started without smoke"),
    )

    with pytest.raises(ValueError, match="verified smoke manifest"):
        screen.run_stage(
            "explore", tmp_path / "explore_out", stage_authorization_path=stage,
        )


def test_stage_validator_rejects_case_or_deadline_change(tmp_path):
    stage = permit(tmp_path, "smoke")
    case = sr.SR_CASES["recurring_fading"]
    other_case = sr.SR_CASES["recurring_static"]

    with pytest.raises(ValueError, match="frozen case and deadline"):
        screen._validate_stage("smoke", other_case, 30.0, stage)
    with pytest.raises(ValueError, match="frozen case and deadline"):
        screen._validate_stage("smoke", case, 31.0, stage)


def test_exploration_rejects_unverified_smoke_before_capture(tmp_path, monkeypatch):
    smoke_manifest = tmp_path / "smoke.manifest.json"
    smoke_manifest.write_text("{}\n", encoding="utf-8")
    (tmp_path / "smoke.manifest.sha256").write_text(
        "invalid sidecar\n", encoding="ascii",
    )
    stage = permit(tmp_path, "explore", predecessors={
        "smoke_manifest": hashlib.sha256(smoke_manifest.read_bytes()).hexdigest(),
    })
    monkeypatch.setattr(
        screen, "_capture_seed",
        lambda *_args, **_kwargs: pytest.fail("capture started with bad smoke"),
    )

    with pytest.raises(ValueError, match="manifest SHA-256 sidecar"):
        screen.run_stage(
            "explore", tmp_path / "explore_out", stage_authorization_path=stage,
            smoke_manifest_path=smoke_manifest,
        )


def test_direct_explore_validator_strictly_replays_smoke(tmp_path, monkeypatch):
    smoke_manifest = tmp_path / "smoke.manifest.json"
    smoke_manifest.write_text("{}\n", encoding="utf-8")
    stage = permit(tmp_path, "explore", predecessors={
        "smoke_manifest": hashlib.sha256(smoke_manifest.read_bytes()).hexdigest(),
    })
    calls = []
    def validate(*_args, **kwargs):
        calls.append(kwargs["strict_replay"])
        return {}
    monkeypatch.setattr(screen, "validate_manifest", validate)

    screen._validate_stage(
        "explore", sr.SR_CASES["recurring_fading"], 30.0,
        stage, smoke_manifest,
    )

    assert calls == [True]


def test_smoke_archive_round_trip_without_reserved_capture(tmp_path, monkeypatch):
    stage = permit(tmp_path, "smoke")
    seen = []
    def capture(seed, *_args, **_kwargs):
        seen.append(seed)
        return fake_run(seed)
    monkeypatch.setattr(screen, "_capture_seed", capture)
    monkeypatch.setattr(
        screen.backup, "summarize_backup_cohort",
        lambda runs: {
            "nominated_initial_direct_r": sum(len(run["rows"]) for run in runs),
        },
    )
    monkeypatch.setattr(
        screen, "_summarize_runs",
        lambda runs, mode: {
            "nominated_initial_direct_r": sum(len(run["rows"]) for run in runs),
            "necessary_gate_passed": None,
        },
    )

    paths = screen.run_stage(
        "smoke", tmp_path / "archive", stage_authorization_path=stage,
    )
    manifest = screen.validate_manifest(
        paths["manifest"], expected_mode="smoke",
        expected_source_sha256=screen._source_hashes(), strict_replay=True,
    )

    assert seen == [46000, 46000]
    assert manifest["seeds"] == [46000]
    assert manifest["summary"]["necessary_gate_passed"] is None
    assert paths["authorization"].read_bytes() == stage.read_bytes()
    paths["rows"].write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="artifact checksum"):
        screen.validate_manifest(
            paths["manifest"], expected_mode="smoke",
            expected_source_sha256=screen._source_hashes(),
            strict_replay=False,
        )


def test_run_audit_requires_full_observer_summary(monkeypatch):
    run = fake_run(46000)
    monkeypatch.setattr(
        screen.backup, "summarize_backup_cohort",
        lambda _runs: {
            "nominated_initial_direct_r": 0,
            "candidate_f_epochs": 2,
        },
    )

    with pytest.raises(ValueError, match="parity or cohort differs"):
        screen._audit_run(run, 46000)


def test_primary_gate_cannot_be_rescued_by_half_second_sensitivity(monkeypatch):
    runs = [fake_run(seed) for seed in screen.EXPLORATORY_SEEDS]
    primary_proxy = {"count": 15}
    def observer_summary(selected):
        count = len(selected)
        return {"by_wait": {
            "2_s": {
                "failed_primary_relay_decode_le_120_s": count,
                "proxy_prr_ge_0_5_deadline_feasible_count": (
                    primary_proxy["count"] if count == 20 else 1
                ),
                "source_ack_headroom_proxy_count": 0,
                "candidate_cost_assessable": True,
                "optimistic_cost_substitution_margin_s": 6.0 * count,
            },
            "0_5_s": {
                "failed_primary_relay_decode_le_120_s": count,
                "proxy_prr_ge_0_5_deadline_feasible_count": count,
                "source_ack_headroom_proxy_count": 0,
                "candidate_cost_assessable": True,
                "optimistic_cost_substitution_margin_s": 6.0 * count,
            },
        }}
    monkeypatch.setattr(screen.backup, "summarize_backup_cohort", observer_summary)

    failed = screen._summarize_runs(runs, "explore")
    assert failed["by_wait"]["2_s"]["cost_substitution_fraction_equal_seed_mean"] == pytest.approx(0.06)
    assert failed["by_wait"]["0_5_s"]["proxy_prr_ge_0_5_deadline_feasible_count"] == 20
    assert failed["necessary_gate_passed"] is False

    primary_proxy["count"] = 16
    passed = screen._summarize_runs(runs, "explore")
    assert passed["necessary_gate_passed"] is True


def test_unknown_source_ack_outcome_has_no_numeric_equal_seed_ceiling(monkeypatch):
    run = fake_run(46000)
    def observer_summary(_selected):
        return {"by_wait": {
            suffix: {
                "failed_primary_relay_decode_le_120_s": 0,
                "proxy_prr_ge_0_5_deadline_feasible_count": 0,
                "source_ack_headroom_proxy_count": 0,
                "source_ack_outcome_unassessable_count": 1,
                "candidate_cost_assessable": True,
                "optimistic_cost_substitution_margin_s": 0.0,
            } for suffix in ("2_s", "0_5_s")
        }}
    monkeypatch.setattr(screen.backup, "summarize_backup_cohort", observer_summary)

    summary = screen._summarize_runs([run], "smoke")

    assert summary["by_wait"]["2_s"]["source_ack_gain_ceiling_equal_seed_mean"] is None


def test_age_views_keep_outcomes_separate(monkeypatch):
    run = fake_run(46000)
    run["rows"] = [{
        "backup_age_at_r_enqueue_s": 80.0,
        "relay_decoded_current_r": True,
        "destination_decoded_current_r": False,
        "stock_source_ack_by_deadline": False,
        "oracle_collision_free_relay_to_dst_prr_2_s": 0.7,
        "oracle_collision_free_relay_to_dst_prr_0_5_s": 0.7,
        "nominal_source_ack_slack_2_s": 1.0,
        "nominal_source_ack_slack_0_5_s": 2.5,
        "nominal_cost_substitution_eligible_2_s": False,
        "nominal_cost_substitution_eligible_0_5_s": False,
    }]
    def observer_summary(_selected):
        return {"by_wait": {
            suffix: {
                "failed_primary_relay_decode_le_120_s": 1,
                "proxy_prr_ge_0_5_deadline_feasible_count": 1,
                "source_ack_headroom_proxy_count": 1,
                "source_ack_outcome_unassessable_count": 0,
                "candidate_cost_assessable": True,
                "optimistic_cost_substitution_margin_s": 0.0,
            } for suffix in ("2_s", "0_5_s")
        }}
    monkeypatch.setattr(screen.backup, "summarize_backup_cohort", observer_summary)

    summary = screen._summarize_runs([run], "smoke")

    assert summary["by_age"]["no_age_limit"]["2_s"]["proxy_feasible_count"] == 1
    assert summary["by_age"]["le_120_s"]["2_s"]["proxy_feasible_count"] == 1
    assert summary["by_age"]["le_60_s"]["2_s"]["proxy_feasible_count"] == 0


def test_nested_nonreserved_replay_captures_one_simulator():
    case = sr.SR_CASES["recurring_fading"]
    inner = []
    def outer_runner(selected_case, protocol, seed, deadline_s):
        nested = screen._capture_seed(
            73, case, 30.0, stage_authorization_path=Path("/dev/null"),
            smoke_manifest_path=None,
        )
        inner.append(nested["strict_replay_exact"])
        return sr.run_one_sr(selected_case, protocol, seed, deadline_s)

    evidence, _sim = capture_run(
        case, 73, screen.backup.PassiveBackupSimulator, 30.0,
        runner=outer_runner,
    )

    assert inner == [True]
    assert evidence.row["seed"] == 73


def test_direct_script_reaches_topology_guard_with_canonical_stage_token(tmp_path):
    script = Path(__file__).resolve().parents[1] / "tools" / "run_destination_backup_screen.py"
    stage = permit(tmp_path, "smoke")
    code = """
import runpy
import sys
from tools import run_sr_experiment as sr

def stop_before_topology(*args, **kwargs):
    raise RuntimeError("topology guard reached")

sr.generate_nodes = stop_before_topology
script, stage, output = sys.argv[1:]
sys.argv = [script, "--mode", "smoke", "--stage-authorization", stage,
            "--output-prefix", output]
runpy.run_path(script, run_name="__main__")
"""
    completed = subprocess.run(
        [sys.executable, "-c", code, str(script), str(stage),
         str(tmp_path / "backup_direct_smoke")],
        capture_output=True, text=True, check=False,
        cwd=script.parents[1],
    )

    assert completed.returncode != 0
    assert "topology guard reached" in completed.stderr
    assert "backup reserved seed requires staged diagnostic authorization" not in completed.stderr
