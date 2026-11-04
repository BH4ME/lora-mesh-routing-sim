import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tools.diagnose_source_risk_signal import (
    build_risk_records, leave_seed_out_predictions, load_frozen_screen,
    summarize_risk,
)


PROTOCOL = "meshecho-dhr-flood-ack-delay"
FROZEN_PREFIX = (
    Path(__file__).resolve().parents[1] / "results"
    / "meshecho_delayed_ack_control_explore_38001_38020_20261004"
)


def _flow(flow_id, when, acked_at=None):
    return {
        "seed": 38001, "protocol": PROTOCOL, "flow_id": flow_id,
        "src": 1, "dst": 2, "enqueued_at": when,
        "deadline_at": when + 30.0, "acked_at": acked_at,
    }


def _event(flow_id, when, event, **fields):
    return {
        "seed": 38001, "protocol": PROTOCOL, "flow_id": flow_id,
        "src": 1, "dst": 2, "time": when, "event": event, **fields,
    }


def _r_tx(flow_id, start, path=(1, 2)):
    return {
        "seed": 38001, "protocol": PROTOCOL, "sender": 1,
        "start": start, "end": start + 0.1,
        "packet": {
            "kind": "DATA", "flow_id": flow_id, "origin": 1,
            "final_dst": 2, "request_id": flow_id, "path": list(path),
            "repair_index": None,
        },
    }


def test_recovery_ack_does_not_label_initial_r_success():
    flows = [_flow(1, 1.0, 3.0), _flow(2, 10.0, 27.0)]
    actions = [
        _event(1, 1.0, "decision", action="F"),
        _event(1, 3.0, "commit", action="F", path=[1, 2]),
        _event(1, 3.0, "dhr_source_ack_rx", accepted=True, repair_index=None),
        _event(2, 10.0, "decision", action="R"),
        _event(2, 25.0, "timeout", action="R", reason="source-ack-timeout"),
        _event(2, 27.0, "commit", action="F-recovery", path=[1, 2]),
        _event(2, 27.0, "dhr_source_ack_rx", accepted=True, repair_index=2),
    ]

    records = build_risk_records(flows, actions, [_r_tx(2, 10.0)])

    assert len(records) == 1
    assert records[0]["initial_r_ack_by_guard"] is False
    assert records[0]["prior_r_miss"] is False
    assert records[0]["last_pair_ack_age_s"] == 7.0
    assert records[0]["hops"] == 1


def test_late_prior_ack_cannot_leak_into_next_r_decision():
    flows = [
        _flow(1, 1.0, 3.0), _flow(2, 10.0, 35.0),
        _flow(3, 30.0, 31.5),
    ]
    actions = [
        _event(1, 1.0, "decision", action="F"),
        _event(1, 3.0, "commit", action="F", path=[1, 2]),
        _event(1, 3.0, "dhr_source_ack_rx", accepted=True, repair_index=None),
        _event(2, 10.0, "decision", action="R"),
        _event(2, 25.0, "timeout", action="R", reason="source-ack-timeout"),
        _event(3, 30.0, "decision", action="R"),
        _event(3, 31.5, "dhr_source_ack_rx", accepted=True, repair_index=None),
        _event(2, 35.0, "dhr_source_ack_rx", accepted=True, repair_index=None),
    ]

    records = build_risk_records(flows, actions, [_r_tx(2, 10.0), _r_tx(3, 31.0)])

    assert [row["initial_r_ack_by_guard"] for row in records] == [False, True]
    assert records[1]["prior_r_miss"] is True
    assert records[1]["last_pair_ack_age_s"] == 27.0


def test_history_stops_at_initial_decision_even_when_physical_start_is_later():
    flows = [_flow(1, 0.0, 0.5), _flow(2, 1.0, 17.1), _flow(3, 17.0)]
    actions = [
        _event(1, 0.0, "decision", action="F"),
        _event(1, 0.5, "commit", action="F", path=[1, 2]),
        _event(1, 0.5, "dhr_source_ack_rx", accepted=True, repair_index=None),
        _event(2, 1.0, "decision", action="R"),
        _event(2, 16.0, "timeout", action="R", reason="source-ack-timeout"),
        _event(3, 17.0, "decision", action="R"),
        _event(2, 17.1, "dhr_source_ack_rx", accepted=True, repair_index=None),
    ]

    records = build_risk_records(
        flows, actions, [_r_tx(2, 1.0), _r_tx(3, 17.2)],
    )

    assert records[1]["prior_r_miss"] is True
    assert records[1]["last_pair_ack_age_s"] == 16.5


def test_initial_r_start_after_original_deadline_is_rejected():
    with pytest.raises(ValueError, match="after original deadline"):
        build_risk_records(
            [_flow(1, 1.0)],
            [_event(1, 1.0, "decision", action="R")],
            [_r_tx(1, 31.1)],
        )


def test_initial_d_to_r_fallback_is_not_an_initial_r_observation():
    flows = [_flow(1, 1.0, 1.5), _flow(2, 10.0)]
    actions = [
        _event(1, 1.0, "decision", action="R"),
        _event(1, 1.5, "dhr_source_ack_rx", accepted=True, repair_index=None),
        _event(2, 10.0, "decision", action="D"),
    ]

    records = build_risk_records(flows, actions, [_r_tx(1, 1.0), _r_tx(2, 20.0)])

    assert [(row["flow_id"], row["initial_r_ack_by_guard"]) for row in records] == [(1, True)]


def test_held_out_seed_does_not_train_its_own_risk_probability():
    records = [
        {"seed": 1, "prior_r_miss": False, "hops": 1,
         "last_pair_ack_age_s": 30.0, "initial_r_ack_by_guard": True},
        {"seed": 2, "prior_r_miss": False, "hops": 1,
         "last_pair_ack_age_s": 30.0, "initial_r_ack_by_guard": False},
    ]

    predictions = leave_seed_out_predictions(records, (1, 2))

    assert predictions[0]["M0"] == 2 / 3
    assert predictions[1]["M0"] == 1 / 3
    assert predictions[0]["M1"] == 2 / 3
    assert predictions[1]["M1"] == 1 / 3


def test_hop_gate_requires_predictive_gain_and_age_gate_needs_its_own_support():
    rows = []
    for seed in range(1, 21):
        for miss in (False, True):
            for one_hop in (False, True):
                rows.append({
                    "seed": seed, "prior_r_miss": miss,
                    "hops": 1 if one_hop else 3,
                    "last_pair_ack_age_s": 180.0 if seed % 2 else 30.0,
                    "initial_r_ack_by_guard": not one_hop,
                })

    report = summarize_risk(rows, range(1, 21))

    assert report["gates"]["hop_actionable_risk_prerequisite"] is True
    assert report["comparisons"]["M0_minus_M1"]["mean_gain"] > 0.005
    assert report["gates"]["age_incremental_support"] is False
    assert report["gates"]["age_incremental_signal"] is False
    assert all(cell["n"] == 20 for cell in report["cells"]["M1"])


def test_sparse_hop_gap_is_reported_but_does_not_pass_support_gate():
    rows = []
    for seed in range(1, 21):
        for one_hop in (False, True):
            rows.append({
                "seed": seed, "prior_r_miss": False,
                "hops": 1 if one_hop else 3,
                "last_pair_ack_age_s": 30.0,
                "initial_r_ack_by_guard": not one_hop,
            })
    for one_hop in (False, True):
        rows.append({
            "seed": 1, "prior_r_miss": True,
            "hops": 1 if one_hop else 3,
            "last_pair_ack_age_s": 30.0,
            "initial_r_ack_by_guard": not one_hop,
        })

    gates = summarize_risk(rows, range(1, 21))["gates"]

    assert gates["hop_gap_in_both_miss_strata"] is True
    assert gates["hop_support"] is False
    assert gates["hop_actionable_risk_prerequisite"] is False


def test_frozen_screen_rejects_a_changed_archived_action(tmp_path):
    prefix = tmp_path / "archived"
    for suffix in ("manifest.json", "actions.jsonl", "flows.jsonl", "tx.jsonl"):
        shutil.copyfile(
            Path(f"{FROZEN_PREFIX}.{suffix}"), Path(f"{prefix}.{suffix}"),
        )
    report = load_frozen_screen(prefix)
    assert report["n_initial_r"] == 613
    assert report["n_initial_r_ack_by_guard"] == 449
    assert report["comparisons"]["M0_minus_M1"]["mean_gain"] == pytest.approx(0.011538133154)

    with Path(f"{prefix}.actions.jsonl").open("ab") as output:
        output.write(b"\n")
    with pytest.raises(ValueError, match="actions SHA-256"):
        load_frozen_screen(prefix)


def test_cli_reports_frozen_screen_without_writing_artifacts():
    tool = Path(__file__).resolve().parents[1] / "tools" / "diagnose_source_risk_signal.py"
    completed = subprocess.run(
        [sys.executable, str(tool), "--prefix", str(FROZEN_PREFIX)],
        check=True, capture_output=True, text=True,
    )

    report = json.loads(completed.stdout)
    assert report["n_initial_r"] == 613
    assert report["gates"]["hop_actionable_risk_prerequisite"] is False
    assert report["provenance"]["observational_only"] is True
