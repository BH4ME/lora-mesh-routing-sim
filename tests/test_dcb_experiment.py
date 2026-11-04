"""Frozen-cohort guards and causal accounting for the DCB experiment."""

from __future__ import annotations

import json
import math
from copy import deepcopy
from dataclasses import asdict
from unittest.mock import patch

import pytest

from lora_mesh_sim import (
    Node, Packet, PendingSend, RadioConfig, RoutingProtocol, Transmission,
    build_protocol,
)
from tools import run_sr_experiment as sr
from tools import run_dcb_experiment as dcb


def _frozen_contract(tmp_path, monkeypatch):
    path = tmp_path / "dcb-contract.md"
    path.write_text("# DCB\n\nStatus: frozen\n", encoding="utf-8")
    monkeypatch.setattr(dcb, "CONTRACT_PATH", path)
    trial_path = tmp_path / "dcb-trial-contract.md"
    trial_path.write_text("# DCB trial\n\nStatus: frozen\n", encoding="utf-8")
    monkeypatch.setattr(dcb, "TRIAL_CONTRACT_PATH", trial_path)


def _permit(tmp_path, mode, predecessor_path=None):
    content = {
        "mode": mode,
        "seeds": list(dcb.SEEDS_BY_MODE[mode]),
        "protocols": list(dcb.ARMS),
        "case_sha256": dcb._hash_json(asdict(sr.SR_CASES["recurring_fading"])),
        "application_deadline_s": 30.0,
        "input_sha256": dcb.input_hashes(),
        "prerequisite_manifest_sha256": {},
    }
    if predecessor_path is not None:
        import hashlib
        content["prerequisite_manifest_sha256"] = {
            "predecessor_manifest": hashlib.sha256(predecessor_path.read_bytes()).hexdigest(),
        }
    path = tmp_path / f"{mode}.authorization.json"
    path.write_text(json.dumps(content), encoding="utf-8")
    return path


@pytest.mark.parametrize("seed", (47000, 47001, 47020, 48001, 48040))
def test_generic_sr_runner_rejects_reserved_dcb_seed_before_topology(seed):
    with patch.object(sr, "generate_nodes", side_effect=AssertionError("topology opened")):
        with pytest.raises(ValueError, match="DCB reserved seed"):
            sr.run_one_sr(sr.SR_CASES["recurring_fading"], "meshecho-dcb", seed)


@pytest.mark.parametrize(
    ("mode", "seeds"),
    (("smoke", (47001,)), ("development", (47000,)),
     ("holdout", tuple(range(48001, 48040))), ("custom", (7,))),
)
def test_dcb_preflight_rejects_noncanonical_cohorts(mode, seeds):
    with patch.object(dcb, "capture_arm", side_effect=AssertionError("simulation opened")):
        with pytest.raises(ValueError, match="mode|cohort"):
            dcb.run_experiment(mode=mode, seeds=seeds)


def test_dcb_draft_contract_keeps_smoke_closed():
    with patch.object(dcb, "capture_arm", side_effect=AssertionError("simulation opened")):
        with pytest.raises(ValueError, match="frozen"):
            dcb.run_experiment(mode="smoke")


def test_trial_draft_contract_keeps_smoke_closed_when_dcb_is_frozen(
    tmp_path, monkeypatch,
):
    path = tmp_path / "dcb-contract.md"
    path.write_text("# DCB\n\nStatus: frozen\n", encoding="utf-8")
    monkeypatch.setattr(dcb, "CONTRACT_PATH", path)
    with patch.object(dcb, "capture_arm", side_effect=AssertionError("simulation opened")):
        with pytest.raises(ValueError, match="trial contract must be frozen"):
            dcb.run_experiment(mode="smoke")


@pytest.mark.parametrize("mode", ("development", "holdout"))
def test_later_dcb_cohorts_require_predecessor_before_simulation(
    tmp_path, monkeypatch, mode,
):
    _frozen_contract(tmp_path, monkeypatch)
    permit = _permit(tmp_path, mode)
    with patch.object(dcb, "capture_arm", side_effect=AssertionError("simulation opened")):
        with pytest.raises(ValueError, match="predecessor"):
            dcb.run_experiment(
                mode=mode, stage_authorization_path=permit,
                output_dir=tmp_path / "evidence",
            )


def test_development_rejects_forged_predecessor_before_simulation(
    tmp_path, monkeypatch,
):
    _frozen_contract(tmp_path, monkeypatch)
    predecessor = tmp_path / "forged.manifest.json"
    predecessor.write_text("{}", encoding="utf-8")
    permit = _permit(tmp_path, "development", predecessor)
    with patch.object(dcb, "capture_arm", side_effect=AssertionError("simulation opened")):
        with pytest.raises(ValueError, match="predecessor"):
            dcb.run_experiment(
                mode="development", stage_authorization_path=permit,
                prerequisite_manifest_path=predecessor,
                output_dir=tmp_path / "evidence",
            )


def _paired_rows(candidate_airtime=0.90):
    rows = []
    actions = []
    for seed in dcb.SEEDS_BY_MODE["development"]:
        for protocol in dcb.ARMS:
            rows.append({
                "case": "recurring_fading", "case_config_sha256": "case",
                "protocol": protocol, "seed": seed, "seed_split": "development",
                "scheduled_trace_sha256": f"trace-{seed}",
                "scheduled_unicast_flows": 10, "application_deadline_s": 30.0,
                "ack_pdr_deadline": 0.9, "destination_pdr_deadline": 0.9,
                "whole_network_tx_airtime_s": (
                    candidate_airtime if protocol == dcb.ARMS[0] else 1.0
                ),
            })
        actions.append({
            "seed": seed, "protocol": dcb.ARMS[0], "flow_id": 1,
            "event": "dcb_backup_tx", "time": 100.0, "relay": 2,
        })
    return rows, actions


def _trial_favorable_rows():
    rows, actions = _paired_rows(candidate_airtime=1.0)
    for row in rows:
        if row["protocol"] == dcb.TRIAL_ARMS[0]:
            row["whole_network_tx_airtime_s"] = 0.90
        elif row["protocol"] == dcb.TRIAL_ARMS[2]:
            row["ack_pdr_deadline"] = 0.8
    return rows, actions


def _trial_provenance_runs(backup_ack_at=8.0):
    rows, _ = _trial_favorable_rows()
    runs = [
        {"seed": row["seed"], "protocol": row["protocol"], "row": row,
         "flows": [], "actions": [], "transmissions": []}
        for row in rows
    ]
    trial = next(run for run in runs
                 if run["seed"] == 47001 and run["protocol"] == dcb.TRIAL_ARMS[0])
    trial["flows"] = [
        {"flow_id": 2, "src": 0, "dst": 2, "enqueued_at": 4.0,
         "deadline_at": 34.0, "acked_at": backup_ack_at, "source_action": "R",
         "ack_by_deadline": True},
        {"flow_id": 3, "src": 0, "dst": 2, "enqueued_at": 10.0,
         "deadline_at": 40.0, "acked_at": None, "source_action": "R",
         "ack_by_deadline": False},
    ]
    path = (0, 1, 2)
    trial["actions"] = [
        {"seed": 47001, "protocol": dcb.TRIAL_ARMS[0], "event": "decision",
         "time": 4.0, "flow_id": 2, "src": 0, "dst": 2,
         "action": "R", "reason": "confirmed-route"},
        {"seed": 47001, "protocol": dcb.TRIAL_ARMS[0],
         "event": "dhr_destination_rx", "time": backup_ack_at - 0.6,
         "flow_id": 2, "src": 0, "dst": 2, "repair_index": 4},
        {"seed": 47001, "protocol": dcb.TRIAL_ARMS[0],
         "event": "dcb_source_ack_rx", "time": backup_ack_at,
         "flow_id": 2, "accepted": True, "path": path, "epoch": 6},
        {"seed": 47001, "protocol": dcb.TRIAL_ARMS[0],
         "event": "trial_pending", "time": backup_ack_at,
         "flow_id": 2, "src": 0, "dst": 2, "path": path},
        {"seed": 47001, "protocol": dcb.TRIAL_ARMS[0], "event": "decision",
         "time": 10.0, "flow_id": 3, "src": 0, "dst": 2,
         "action": "R", "reason": "ack-proven-trial"},
    ]

    def tx(tx_id, sender, packet, start, end):
        return asdict(Transmission(tx_id, sender, packet, start, end))

    protocol = dcb.TRIAL_ARMS[0]
    trial["transmissions"] = [
        tx(1, 0, Packet("DATA", 2, 0, 2, 3, 4.0, protocol, request_id=2,
                        path=(0, 2), backup_relay_id=1, backup_epoch_id=6),
           4.0, 4.2),
        tx(2, 1, Packet("DATA", 2, 0, 2, 3, 4.0, protocol, request_id=2,
                        path=path, path_index=1, repair_index=4,
                        backup_epoch_id=6),
           backup_ack_at - 0.8, backup_ack_at - 0.6),
        tx(3, 2, Packet("ACK", 2, 2, 0, 3, 4.0, protocol, request_id=2,
                        path=path, path_index=1, repair_index=4,
                        backup_epoch_id=6, app_payload=False),
           backup_ack_at - 0.5, backup_ack_at - 0.3),
        tx(4, 1, Packet("ACK", 2, 2, 0, 3, 4.0, protocol, request_id=2,
                        path=path, path_index=0, repair_index=4,
                        backup_epoch_id=6, app_payload=False),
           backup_ack_at - 0.2, backup_ack_at),
        tx(5, 0, Packet("DATA", 3, 0, 2, 3, 10.0, protocol, request_id=3,
                        path=path), 10.0, 10.2),
    ]
    return rows, runs, trial


def test_paired_dcb_gate_uses_frozen_bounds_and_action_exposure():
    rows, actions = _paired_rows()
    result = dcb.summarize_dcb(rows, actions, "development")
    assert result["project_gate"] is True
    assert result["backup_tx_starts"] == 20
    assert result["forwarding_action_differences"] == 20
    assert len(result["comparisons"]) == len(dcb.ARMS) - 1
    assert sum(item["dcb_primary_gate"] is True
               for item in result["comparisons"]) == 4


def test_trial_core_gate_is_separate_and_fails_closed_without_physical_runs():
    rows, actions = _trial_favorable_rows()

    result = dcb.summarize_dcb(rows, actions, "development")

    comparisons = {item["comparator"]: item
                   for item in result["trial_comparisons"]}
    assert set(comparisons) == {
        dcb.TRIAL_ARMS[1], dcb.TRIAL_ARMS[2], dcb.CORE_ARMS[0],
        dcb.CORE_ARMS[3], dcb.CORE_ARMS[4],
    }
    assert all(item["focus_protocol"] == dcb.TRIAL_ARMS[0]
               for item in comparisons.values())
    assert comparisons[dcb.CORE_ARMS[0]]["relative_airtime_cost"] == pytest.approx(-0.10)
    assert comparisons[dcb.TRIAL_ARMS[2]]["ack_pdr_ci95_low"] == pytest.approx(0.10)
    assert result["trial_statistical_gate"] is True
    assert result["project_gate"] is False
    assert result["trial_exposure_gate"] is False
    assert result["trial_project_gate"] is False


def test_trial_core_gate_requires_strict_blind_ack_advantage():
    rows, actions = _trial_favorable_rows()
    for row in rows:
        if row["protocol"] == dcb.TRIAL_ARMS[2]:
            row["ack_pdr_deadline"] = 0.9

    result = dcb.summarize_dcb(rows, actions, "development")

    blind = next(item for item in result["trial_comparisons"]
                 if item["comparator"] == dcb.TRIAL_ARMS[2])
    assert blind["ack_pdr_ci95_low"] == 0.0
    assert blind["trial_primary_gate"] is False
    assert result["trial_statistical_gate"] is False


def test_trial_gate_rejects_backup_ack_after_trial_decision_and_start():
    rows, runs, _ = _trial_provenance_runs(backup_ack_at=12.0)
    actions = [event for run in runs for event in run["actions"]]

    result = dcb.summarize_dcb(rows, actions, "development", physical_runs=runs)

    assert result["trial_provenance_gate"] is False


def test_trial_gate_rejects_first_r_path_mismatch_despite_later_matching_tx():
    rows, runs, trial = _trial_provenance_runs()
    first = trial["transmissions"][-1]
    first["packet"]["path"] = (0, 3, 2)
    later = deepcopy(first)
    later["tx_id"] = 6
    later["packet"]["path"] = (0, 1, 2)
    later["start"] = 10.5
    later["end"] = 10.7
    trial["transmissions"].append(later)
    actions = [event for run in runs for event in run["actions"]]

    result = dcb.summarize_dcb(rows, actions, "development", physical_runs=runs)

    assert result["trial_exposure"]["physical_trial_starts"] == 0
    assert result["trial_provenance_gate"] is False


def test_trial_exposure_thresholds_require_each_count_and_seed_floor():
    exposure = {
        "physical_evidence_complete": True,
        "physical_trial_starts": 20,
        "physical_trial_starts_seeds": 10,
        "ordinary_trial_ack_commits": 10,
        "ordinary_trial_ack_commits_seeds": 5,
        "guard_divergent_followups": 10,
        "guard_divergent_followups_seeds": 5,
        "initial_source_decision_differences": 20,
        "initial_source_decision_differences_seeds": 10,
    }
    assert dcb._trial_exposure_gate(exposure, evaluable=True) is True
    assert dcb._trial_exposure_gate(exposure, evaluable=False) is False
    for field in tuple(exposure):
        if field == "physical_evidence_complete":
            continue
        below = {**exposure, field: exposure[field] - 1}
        assert dcb._trial_exposure_gate(below, evaluable=True) is False


def test_holdout_requires_trial_core_gate_even_when_old_dcb_passes(
    tmp_path, monkeypatch,
):
    _frozen_contract(tmp_path, monkeypatch)
    predecessor = tmp_path / "development.manifest.json"
    predecessor.write_text("{}", encoding="utf-8")
    permit = _permit(tmp_path, "holdout", predecessor)
    monkeypatch.setattr(dcb, "audit_artifacts", lambda *args, **kwargs: {
        "project_gate": True, "trial_project_gate": False,
    })

    with patch.object(dcb, "capture_arm", side_effect=AssertionError("simulation opened")):
        with pytest.raises(ValueError, match="trial.*gate"):
            dcb.run_experiment(
                mode="holdout", stage_authorization_path=permit,
                prerequisite_manifest_path=predecessor,
                output_dir=tmp_path / "holdout-evidence",
            )


def test_holdout_preflight_does_not_require_old_dcb_component_gate(
    tmp_path, monkeypatch,
):
    _frozen_contract(tmp_path, monkeypatch)
    predecessor = tmp_path / "development.manifest.json"
    predecessor.write_text("{}", encoding="utf-8")
    permit = _permit(tmp_path, "holdout", predecessor)
    monkeypatch.setattr(dcb, "audit_artifacts", lambda *args, **kwargs: {
        "project_gate": False, "trial_project_gate": True,
    })

    frozen_hashes, authorization = dcb._validate_stage(
        "holdout", dcb.SEEDS_BY_MODE["holdout"],
        sr.SR_CASES["recurring_fading"], 30.0, permit, predecessor,
    )

    assert frozen_hashes == dcb.input_hashes()
    assert authorization == permit.read_bytes()


def test_contextual_arms_are_recorded_without_becoming_same_budget_gates():
    assert set(dcb.CONTEXT_ARMS) == {
        "meshecho-dhr-flood-ack-delay-flood2",
        "meshecho-sr-fr",
        "meshecho-lpr",
    }
    rows, actions = _paired_rows()

    result = dcb.summarize_dcb(rows, actions, "development")

    contextual = {item["comparator"]: item for item in result["comparisons"]
                  if item["comparator"] in dcb.CONTEXT_ARMS}
    assert set(contextual) == set(dcb.CONTEXT_ARMS)
    assert all(item["dcb_primary_gate"] is None
               and item["comparison_role"] == "contextual"
               for item in contextual.values())


def test_same_wire_source_fr_control_is_distinct_from_contextual_sr_fr():
    assert dcb.SOURCE_ARMS == ("meshecho-dcb-source-fr",)
    rows, actions = _paired_rows()

    result = dcb.summarize_dcb(rows, actions, "development")

    source = next(item for item in result["comparisons"]
                  if item["comparator"] == dcb.SOURCE_ARMS[0])
    assert source["comparison_role"] == "source-control"
    assert source["dcb_primary_gate"] is None


def test_trial_and_no_switch_are_paired_same_wire_source_arms():
    assert dcb.TRIAL_ARMS == (
        "meshecho-dcb-trial", "meshecho-dcb-trial-no-switch",
        "meshecho-dcb-trial-blind",
    )
    rows, actions = _paired_rows()

    result = dcb.summarize_dcb(rows, actions, "development")

    comparisons = {item["comparator"]: item for item in result["comparisons"]}
    assert comparisons[dcb.TRIAL_ARMS[0]]["comparison_role"] == "source-candidate"
    assert comparisons[dcb.TRIAL_ARMS[1]]["comparison_role"] == "source-control"
    assert all(comparisons[arm]["dcb_primary_gate"] is None
               for arm in dcb.TRIAL_ARMS)


def test_trial_events_and_no_switch_pair_are_reported_separately():
    rows, actions = _paired_rows()
    actions.extend((
        {"seed": 47001, "protocol": dcb.TRIAL_ARMS[0], "flow_id": 2,
         "event": "trial_pending", "time": 100.0},
        {"seed": 47001, "protocol": dcb.TRIAL_ARMS[0], "flow_id": 3,
         "event": "decision", "action": "R", "reason": "ack-proven-trial",
         "time": 101.0},
        {"seed": 47001, "protocol": dcb.TRIAL_ARMS[0], "flow_id": 3,
         "event": "commit", "action": "R-trial", "time": 102.0},
        {"seed": 47002, "protocol": dcb.TRIAL_ARMS[0], "flow_id": 4,
         "event": "trial_abandoned", "time": 105.0},
        {"seed": 47001, "protocol": dcb.TRIAL_ARMS[2], "flow_id": 2,
         "event": "commit", "action": "R-backup-blind", "time": 100.0},
    ))

    result = dcb.summarize_dcb(rows, actions, "development")

    assert result["trial_vs_no_switch"]["focus_protocol"] == dcb.TRIAL_ARMS[0]
    assert result["trial_vs_no_switch"]["comparator"] == dcb.TRIAL_ARMS[1]
    assert result["trial_vs_blind"]["focus_protocol"] == dcb.TRIAL_ARMS[0]
    assert result["trial_vs_blind"]["comparator"] == dcb.TRIAL_ARMS[2]
    assert "reliability_cost_gate" not in result["trial_vs_no_switch"]
    assert result["trial_events"] == {
        "pending": 1, "attempted": 1, "committed": 1, "abandoned": 1,
        "blind_committed": 1,
    }


def test_dcb_gate_rejects_airtime_saving_below_fixed_f_margin():
    rows, actions = _paired_rows(candidate_airtime=0.96)
    result = dcb.summarize_dcb(rows, actions, "development")
    gates = {item["comparator"]: item["dcb_primary_gate"]
             for item in result["comparisons"]}
    assert gates[dcb.ARMS[4]] is False
    assert result["project_gate"] is False


def test_dcb_equivalence_requires_entire_paired_interval_inside_margins():
    rows, actions = _paired_rows(candidate_airtime=0.99)
    result = dcb.summarize_dcb(rows, actions, "development")
    assert result["equivalent_to_current_overhear"] is True
    rows[0]["whole_network_tx_airtime_s"] = 1.2
    result = dcb.summarize_dcb(rows, actions, "development")
    assert result["equivalent_to_current_overhear"] is False


def test_dcb_pairing_rejects_changed_application_trace():
    rows, actions = _paired_rows()
    rows[1]["scheduled_trace_sha256"] = "different"
    with pytest.raises(ValueError, match="paired trace"):
        dcb.summarize_dcb(rows, actions, "development")


def test_forwarding_difference_counts_one_divergent_flow_once():
    rows, actions = _paired_rows()
    actions.extend({
        "seed": seed, "protocol": dcb.ARMS[3], "flow_id": 1,
        "event": "dcb_backup_tx", "time": 100.0, "relay": 3,
    } for seed in dcb.SEEDS_BY_MODE["development"])
    result = dcb.summarize_dcb(rows, actions, "development")
    assert result["forwarding_action_differences"] == 20


def test_accepted_backup_ack_requires_destination_decode_provenance():
    def tx(tx_id, sender, packet, start, end):
        return asdict(Transmission(tx_id, sender, packet, start, end))

    initial = Packet(
        "DATA", 7, 0, 2, 3, 0.0, dcb.ARMS[0], request_id=7,
        path=(0, 2), backup_relay_id=1, backup_epoch_id=6,
    )
    backup = Packet(
        "DATA", 7, 0, 2, 3, 0.0, dcb.ARMS[0], request_id=7,
        path=(0, 1, 2), path_index=1, repair_index=4, backup_epoch_id=6,
    )
    ack = Packet(
        "ACK", 7, 2, 0, 3, 2.2, dcb.ARMS[0], request_id=7,
        path=(0, 1, 2), path_index=1, repair_index=4,
        backup_epoch_id=6, app_payload=False,
    )
    run = {
        "protocol": dcb.ARMS[0],
        "flows": [{"flow_id": 7, "src": 0, "dst": 2,
                   "deadline_at": 30.0, "acked_at": 2.6,
                   "ack_by_deadline": True}],
        "actions": [
            {"event": "dhr_destination_rx", "flow_id": 7, "src": 0,
             "dst": 2, "repair_index": 4, "time": 2.2},
            {"event": "dcb_source_ack_rx", "flow_id": 7,
             "accepted": True, "path": [0, 1, 2], "epoch": 6, "time": 2.6},
        ],
        "transmissions": [
            tx(1, 0, initial, 0.0, 0.2),
            tx(2, 1, backup, 2.0, 2.2),
            tx(3, 2, ack, 2.3, 2.4),
            tx(4, 1, ack, 2.5, 2.6),
        ],
    }
    assert dcb._invalid_accepted_ack_count([run]) == 0
    run["flows"][0]["acked_at"] = 2.4
    assert dcb._invalid_accepted_ack_count([run]) == 1
    run["flows"][0]["acked_at"] = 2.6
    run["actions"].pop(0)
    assert dcb._invalid_accepted_ack_count([run]) == 1


def test_dcb_recorder_pairs_a_future_physical_start_with_its_request_time():
    sim = dcb.DcbRecordingSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0), RoutingProtocol(),
        seed=73, max_hops=3,
    )
    sim.now = 1.0
    sim.nodes[0].tx_available_at = 2.0
    packet = Packet(
        "DATA", 1, 0, 1, 3, 1.0, "base", request_id=1, path=(0, 1),
    )

    sim.begin_transmission(0, packet, PendingSend())

    assert len(sim.tx_history) == 1
    assert sim.tx_history[0].start == 2.0
    assert sim.tx_request_times == {sim.tx_history[0].tx_id: 1.0}
    record = {**asdict(sim.tx_history[0]), "request_time": 1.0, "queue_wait_s": 1.0}
    assert dcb.queue_wait_metrics([record], 2.0) == {
        "queued_tx_count": 1,
        "tx_queue_wait_mean_s": 1.0,
        "tx_queue_wait_p95_s": 1.0,
        "tx_queue_wait_max_s": 1.0,
    }


def test_authorized_nonreserved_fixture_captures_complete_physical_run(
    tmp_path, monkeypatch,
):
    case = sr.SrCase(
        key="recurring_fading", nodes=4, area_m=1000.0,
        duration_s=10.0, rate_per_min=6.0, pair_mode="random", pair_count=0,
        max_hops=3,
    )
    monkeypatch.setitem(sr.SR_CASES, "recurring_fading", case)
    monkeypatch.setitem(dcb.SEEDS_BY_MODE, "smoke", (73,))
    monkeypatch.setattr(sr, "DCB_RESERVED_SEEDS", frozenset({73}))
    _frozen_contract(tmp_path, monkeypatch)
    permit = _permit(tmp_path, "smoke")
    run = dcb.capture_arm(
        case, dcb.ARMS[0], 73, 30.0,
        stage_authorization_path=permit, mode="smoke",
    )
    assert run["row"]["protocol"] == dcb.ARMS[0]
    assert run["row"]["scheduled_unicast_flows"] == len(run["flows"])
    assert run["row"]["whole_network_tx_airtime_s"] == pytest.approx(
        sum(tx["end"] - tx["start"] for tx in run["transmissions"]
            if tx["start"] <= 40.0)
    )
    included = [tx for tx in run["transmissions"] if tx["start"] <= 40.0]
    assert included
    assert all(tx["request_time"] <= tx["start"] for tx in run["transmissions"])
    assert all(tx["queue_wait_s"] == pytest.approx(
        tx["start"] - tx["request_time"]
    ) for tx in run["transmissions"])
    waits = [tx["queue_wait_s"] for tx in included]
    assert run["row"]["queued_tx_count"] == sum(wait > 1e-12 for wait in waits)
    assert run["row"]["tx_queue_wait_mean_s"] == pytest.approx(sum(waits) / len(waits))
    assert run["row"]["tx_queue_wait_p95_s"] == pytest.approx(
        sorted(waits)[math.ceil(0.95 * len(waits)) - 1]
    )
    assert run["row"]["tx_queue_wait_max_s"] == pytest.approx(max(waits))
    state = run["state"]
    assert set(state) == {
        "peak_feedback_windows_by_destination",
        "peak_pending_backups_by_relay",
        "peak_seen_floods_by_node",
        "seen_floods_unbounded",
    }
    assert state["seen_floods_unbounded"] is True
    assert run["row"]["feedback_window_sum_of_node_peaks"] == sum(
        state["peak_feedback_windows_by_destination"].values()
    )
    assert run["row"]["relay_pending_sum_of_node_peaks"] == sum(
        state["peak_pending_backups_by_relay"].values()
    )
    assert run["row"]["seen_floods_final_total"] == sum(
        state["peak_seen_floods_by_node"].values()
    )


@pytest.fixture
def fixture_stage(tmp_path, monkeypatch):
    case = sr.SrCase(
        key="recurring_fading", nodes=4, area_m=1000.0,
        duration_s=10.0, rate_per_min=6.0, pair_mode="random", pair_count=0,
        max_hops=3,
    )
    monkeypatch.setitem(sr.SR_CASES, "recurring_fading", case)
    monkeypatch.setitem(dcb.SEEDS_BY_MODE, "smoke", (73,))
    monkeypatch.setattr(sr, "DCB_RESERVED_SEEDS", frozenset({73}))
    _frozen_contract(tmp_path, monkeypatch)
    permit = _permit(tmp_path, "smoke")
    output_dir = tmp_path / "evidence"
    report = dcb.run_experiment(
        mode="smoke", seeds=(73,), case=case,
        stage_authorization_path=permit, output_dir=output_dir,
    )
    return report, output_dir


def test_fixture_stage_persists_auditable_arm_matrix(fixture_stage):
    report, output_dir = fixture_stage
    assert len(report["runs"]) == len(dcb.ARMS)
    assert report["summary"]["project_gate"] is False
    requests = [json.loads(line) for line in
                (output_dir / "tx_requests.jsonl").read_text(encoding="utf-8").splitlines()]
    physical = [json.loads(line) for line in
                (output_dir / "transmissions.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(requests) == len(physical)
    assert {(item["seed"], item["protocol"], item["tx_id"])
            for item in requests} == {
                (item["seed"], item["protocol"], item["tx_id"])
                for item in physical
            }
    state_records = [json.loads(line) for line in
                     (output_dir / "state.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(state_records) == len(dcb.ARMS)
    assert all(record["state"]["seen_floods_unbounded"] for record in state_records)
    assert dcb.audit_artifacts(output_dir / "manifest.json")["runs"] == len(dcb.ARMS)


def test_fixture_stage_captures_trial_and_both_same_wire_controls(fixture_stage):
    report, output_dir = fixture_stage
    trial_runs = {
        run["protocol"]: run for run in report["runs"]
        if run["protocol"] in dcb.TRIAL_ARMS
    }

    assert set(trial_runs) == set(dcb.TRIAL_ARMS)
    assert trial_runs[dcb.TRIAL_ARMS[0]]["row"]["scheduled_trace_sha256"] == (
        trial_runs[dcb.TRIAL_ARMS[1]]["row"]["scheduled_trace_sha256"]
    )
    assert dcb.audit_artifacts(output_dir / "manifest.json")["runs"] == len(dcb.ARMS)


def test_nonreserved_stage_audits_a_physical_trial_and_blind_control(
    tmp_path, monkeypatch,
):
    case = sr.SrCase(
        key="recurring_fading", nodes=4, area_m=1000.0,
        duration_s=12.0, rate_per_min=6.0, pair_mode="random", pair_count=0,
        max_hops=6,
    )
    monkeypatch.setitem(sr.SR_CASES, "recurring_fading", case)
    monkeypatch.setitem(dcb.SEEDS_BY_MODE, "smoke", (73,))
    monkeypatch.setattr(sr, "DCB_RESERVED_SEEDS", frozenset({73}))
    monkeypatch.setattr(sr, "generate_nodes", lambda *args, **kwargs: [
        Node(i, i * 10.0, 0.0) for i in range(4)
    ])

    def schedule_three_flows(sim, *args):
        for flow_id, when in enumerate((1.0, 5.0, 10.0), start=1):
            sim.schedule(when, "app_send", (0, 3, flow_id))

    monkeypatch.setattr(sr, "schedule_sr_traffic", schedule_three_flows)
    original_receive = dcb.DcbRecordingSimulator.try_receive

    def drop_second_direct(self, tx, receiver):
        if (tx.packet.flow_id == 2 and tx.packet.kind == "DATA"
                and tx.packet.repair_index is None
                and tx.sender == 0 and receiver == 3):
            return None
        return original_receive(self, tx, receiver)

    monkeypatch.setattr(dcb.DcbRecordingSimulator, "try_receive", drop_second_direct)
    _frozen_contract(tmp_path, monkeypatch)
    permit = _permit(tmp_path, "smoke")
    report = dcb.run_experiment(
        mode="smoke", seeds=(73,), case=case,
        stage_authorization_path=permit, output_dir=tmp_path / "trial-evidence",
    )

    candidate = next(run for run in report["runs"]
                     if run["protocol"] == dcb.TRIAL_ARMS[0])
    blind = next(run for run in report["runs"]
                 if run["protocol"] == dcb.TRIAL_ARMS[2])
    assert any(event["event"] == "trial_pending"
               for event in candidate["actions"])
    assert any(event["event"] == "decision"
               and event.get("reason") == "ack-proven-trial"
               for event in candidate["actions"])
    assert any(event["event"] == "commit" and event.get("action") == "R-trial"
               for event in candidate["actions"])
    assert any(event["event"] == "commit"
               and event.get("action") == "R-backup-blind"
               for event in blind["actions"])
    exposure = report["summary"]["trial_exposure"]
    assert exposure["accepted_backup_acks"] >= 1
    assert exposure["physical_trial_starts"] == 1
    assert exposure["ordinary_trial_ack_commits"] == 1
    assert exposure["guard_divergent_followups"] == 0
    assert report["audit"]["trial_project_gate"] is False
    assert dcb.audit_artifacts(report["manifest_path"])["runs"] == len(dcb.ARMS)

    missing_tx_runs = deepcopy(report["runs"])
    missing_trial = next(run for run in missing_tx_runs
                         if run["protocol"] == dcb.TRIAL_ARMS[0])
    missing_trial["transmissions"] = [
        tx for tx in missing_trial["transmissions"]
        if not (tx["sender"] == 0 and tx["packet"]["kind"] == "DATA"
                and tx["packet"]["flow_id"] == 3
                and tx["packet"]["repair_index"] is None)
    ]
    without_tx = dcb.summarize_dcb(
        [run["row"] for run in missing_tx_runs],
        [event for run in missing_tx_runs for event in run["actions"]],
        "smoke", physical_runs=missing_tx_runs,
    )
    assert without_tx["trial_exposure"]["physical_trial_starts"] == 0
    assert without_tx["trial_exposure_gate"] is False

    missing_ack_runs = deepcopy(report["runs"])
    missing_ack_trial = next(run for run in missing_ack_runs
                             if run["protocol"] == dcb.TRIAL_ARMS[0])
    missing_ack_trial["transmissions"] = [
        tx for tx in missing_ack_trial["transmissions"]
        if not (tx["packet"]["kind"] == "ACK"
                and tx["packet"]["flow_id"] == 3
                and tx["packet"]["repair_index"] is None
                and tx["sender"] == tx["packet"]["path"][1])
    ]
    without_ack = dcb.summarize_dcb(
        [run["row"] for run in missing_ack_runs],
        [event for run in missing_ack_runs for event in run["actions"]],
        "smoke", physical_runs=missing_ack_runs,
    )
    assert without_ack["trial_exposure"]["ordinary_trial_ack_commits"] == 0


def test_nonreserved_stage_audits_trial_guard_before_same_flow_f_recovery(
    tmp_path, monkeypatch,
):
    case = sr.SrCase(
        key="recurring_fading", nodes=4, area_m=1000.0,
        duration_s=31.0, rate_per_min=6.0, pair_mode="random", pair_count=0,
        max_hops=6,
    )
    monkeypatch.setitem(sr.SR_CASES, "recurring_fading", case)
    monkeypatch.setitem(dcb.SEEDS_BY_MODE, "smoke", (73,))
    monkeypatch.setattr(sr, "DCB_RESERVED_SEEDS", frozenset({73}))
    monkeypatch.setattr(sr, "generate_nodes", lambda *args, **kwargs: [
        Node(i, i * 10.0, 0.0) for i in range(4)
    ])

    def schedule_four_flows(sim, *args):
        for flow_id, when in enumerate((1.0, 5.0, 10.0, 30.0), start=1):
            sim.schedule(when, "app_send", (0, 3, flow_id))

    monkeypatch.setattr(sr, "schedule_sr_traffic", schedule_four_flows)
    original_receive = dcb.DcbRecordingSimulator.try_receive

    def drop_trial_data(self, tx, receiver):
        if (tx.packet.kind == "DATA" and receiver == 3
                and ((tx.packet.flow_id == 2 and tx.sender == 0
                      and tx.packet.repair_index is None)
                     or (tx.packet.protocol == dcb.TRIAL_ARMS[0]
                         and tx.packet.flow_id == 3
                         and tx.packet.repair_index is None))):
            return None
        return original_receive(self, tx, receiver)

    monkeypatch.setattr(dcb.DcbRecordingSimulator, "try_receive", drop_trial_data)
    _frozen_contract(tmp_path, monkeypatch)
    permit = _permit(tmp_path, "smoke")
    report = dcb.run_experiment(
        mode="smoke", seeds=(73,), case=case,
        stage_authorization_path=permit, output_dir=tmp_path / "recovery-evidence",
    )

    trial = next(run for run in report["runs"]
                 if run["protocol"] == dcb.TRIAL_ARMS[0])
    abandoned = next(event for event in trial["actions"]
                     if event["event"] == "trial_abandoned"
                     and event["reason"] == "source-ack-guard")
    flow_id = abandoned["flow_id"]
    flow = next(item for item in trial["flows"] if item["flow_id"] == flow_id)
    assert flow_id == 3
    recovery = next(event for event in trial["actions"]
                    if event["event"] == "commit"
                    and event["action"] == "F-recovery"
                    and event["flow_id"] == flow_id)
    assert abandoned["time"] < recovery["time"]
    assert flow["acked_at"] == pytest.approx(recovery["time"])
    assert not any(event["event"] == "trial_abandoned"
                   and event["reason"] == "new-route-commit"
                   and event["flow_id"] == flow_id
                   for event in trial["actions"])
    assert any(tx["packet"]["kind"] == "ACK"
               and tx["packet"]["repair_index"] == 2
               and tx["packet"]["flow_id"] == flow_id
               and tx["end"] == pytest.approx(recovery["time"])
               for tx in trial["transmissions"])
    exposure = report["summary"]["trial_exposure"]
    assert exposure["physical_trial_starts"] == 1
    assert exposure["ordinary_trial_ack_commits"] == 0
    assert exposure["source_guard_abandonments"] == 1
    assert exposure["guard_divergent_followups"] == 1
    assert exposure["guard_divergent_followups_seeds"] == 1
    assert dcb.audit_artifacts(report["manifest_path"])["runs"] == len(dcb.ARMS)

    shifted_runs = deepcopy(report["runs"])
    shifted_trial = next(run for run in shifted_runs
                         if run["protocol"] == dcb.TRIAL_ARMS[0])
    shifted_guard = next(event for event in shifted_trial["actions"]
                         if event["event"] == "trial_abandoned"
                         and event["reason"] == "source-ack-guard")
    shifted_guard["time"] += 1.0
    shifted = dcb.summarize_dcb(
        [run["row"] for run in shifted_runs],
        [event for run in shifted_runs for event in run["actions"]],
        "smoke", physical_runs=shifted_runs,
    )
    assert shifted["trial_exposure"]["source_guard_abandonments"] == 0
    assert shifted["invalid_trial_actions"] > 0

    after_deadline_runs = deepcopy(report["runs"])
    late_trial = next(run for run in after_deadline_runs
                      if run["protocol"] == dcb.TRIAL_ARMS[0])
    next(flow for flow in late_trial["flows"] if flow["flow_id"] == 3)["deadline_at"] = 24.0
    after_deadline = dcb.summarize_dcb(
        [run["row"] for run in after_deadline_runs],
        [event for run in after_deadline_runs for event in run["actions"]],
        "smoke", physical_runs=after_deadline_runs,
    )
    assert after_deadline["trial_exposure"]["source_guard_abandonments"] == 0

    import hashlib

    actions_path = tmp_path / "recovery-evidence" / "actions.jsonl"
    archived_actions = [json.loads(line) for line in
                        actions_path.read_text(encoding="utf-8").splitlines()]
    archived_guard = next(event for event in archived_actions
                          if event["protocol"] == dcb.TRIAL_ARMS[0]
                          and event["event"] == "trial_abandoned"
                          and event["reason"] == "source-ack-guard")
    archived_guard["time"] += 1.0
    actions_path.write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in archived_actions),
        encoding="utf-8",
    )
    manifest_path = tmp_path / "recovery-evidence" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_sha256"]["actions.jsonl"] = hashlib.sha256(
        actions_path.read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="trial action provenance"):
        dcb.audit_artifacts(manifest_path)


def test_nonreserved_stage_joins_old_d_source_decision_to_physical_starts(
    tmp_path, monkeypatch,
):
    case = sr.SrCase(
        key="recurring_fading", nodes=4, area_m=1000.0,
        duration_s=201.0, rate_per_min=6.0, pair_mode="random", pair_count=0,
        max_hops=6,
    )
    monkeypatch.setitem(sr.SR_CASES, "recurring_fading", case)
    monkeypatch.setitem(dcb.SEEDS_BY_MODE, "smoke", (73,))
    monkeypatch.setattr(sr, "DCB_RESERVED_SEEDS", frozenset({73}))
    monkeypatch.setattr(sr, "generate_nodes", lambda *args, **kwargs: [
        Node(i, i * 10.0, 0.0) for i in range(4)
    ])

    def schedule_age_crossing(sim, *args):
        for flow_id, when in enumerate((1.0, 20.0, 200.0), start=1):
            sim.schedule(when, "app_send", (0, 3, flow_id))

    monkeypatch.setattr(sr, "schedule_sr_traffic", schedule_age_crossing)
    _frozen_contract(tmp_path, monkeypatch)
    permit = _permit(tmp_path, "smoke")
    report = dcb.run_experiment(
        mode="smoke", seeds=(73,), case=case,
        stage_authorization_path=permit, output_dir=tmp_path / "age-evidence",
    )

    exposure = report["summary"]["trial_exposure"]
    assert exposure["initial_source_decision_differences"] == 1
    assert exposure["initial_source_decision_differences_seeds"] == 1
    assert exposure["initial_actions"]["trial"]["R"] >= 1
    assert exposure["initial_actions"]["old_dcb"]["D"] >= 1
    assert dcb.audit_artifacts(report["manifest_path"])["trial_project_gate"] is False

    wrong_decision_runs = deepcopy(report["runs"])
    trial = next(run for run in wrong_decision_runs
                 if run["protocol"] == dcb.TRIAL_ARMS[0])
    decision = next(event for event in trial["actions"]
                    if event["event"] == "decision" and event["flow_id"] == 3)
    decision["src"] = 1
    wrong_decision = dcb.summarize_dcb(
        [run["row"] for run in wrong_decision_runs],
        [event for run in wrong_decision_runs for event in run["actions"]],
        "smoke", physical_runs=wrong_decision_runs,
    )
    assert wrong_decision["trial_exposure"]["initial_source_decision_differences"] == 0


def test_nonreserved_other_flow_commit_abandons_trial_before_ack():
    class NewRouteCommitSimulator(dcb.DcbRecordingSimulator):
        def try_receive(self, tx, receiver):
            if (tx.packet.flow_id == 2 and receiver == 3
                    and tx.packet.kind in {"DATA", "FLOOD"}):
                return None
            if (receiver == 3 and tx.packet.kind == "DATA"
                    and ((tx.packet.flow_id == 3 and tx.sender == 0)
                         or (tx.packet.flow_id == 4 and tx.sender == 2)
                         or (tx.packet.flow_id == 6 and tx.sender == 0))):
                return None
            return super().try_receive(tx, receiver)

    protocol = build_protocol(dcb.TRIAL_ARMS[0])
    protocol.flood_base_delay_s = 0.5
    protocol.flood_jitter_s = 0.0
    sim = NewRouteCommitSimulator(
        [Node(i, i * 10.0, 0.0) for i in range(4)],
        RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
        seed=17, max_hops=6, independent_random_streams=True,
    )
    for flow_id, when in enumerate(
        (1.0, 4.0, 7.0, 10.0, 20.0, 22.3, 24.9), start=1,
    ):
        sim.schedule(when, "app_send", (0, 3, flow_id))
    metrics = sim.run(31.0)

    abandoned = next(event for event in protocol.action_events
                     if event["event"] == "trial_abandoned"
                     and event["reason"] == "new-route-commit")
    assert metrics.flows[abandoned["flow_id"]].acked_at is None
    assert any(event["event"] == "commit" and event["action"] == "F"
               and event["time"] == pytest.approx(abandoned["time"])
               and event["flow_id"] != abandoned["flow_id"]
               for event in protocol.action_events)
    run = {
        "protocol": dcb.TRIAL_ARMS[0],
        "flows": [{**asdict(flow), "deadline_at": flow.created_at + 30.0}
                  for flow in metrics.flows.values()],
        "actions": protocol.action_events,
        "transmissions": [asdict(tx) for tx in sim.tx_history],
    }
    assert dcb._invalid_trial_action_count([run]) == 0


def test_rehashed_airtime_claim_is_rejected_by_physical_audit(fixture_stage):
    import hashlib

    _, output_dir = fixture_stage
    runs_path = output_dir / "runs.jsonl"
    runs = [json.loads(line) for line in runs_path.read_text(encoding="utf-8").splitlines()]
    runs[0]["row"]["whole_network_tx_airtime_s"] += 1.0
    runs_path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in runs),
        encoding="utf-8",
    )
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_sha256"]["runs.jsonl"] = hashlib.sha256(
        runs_path.read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="physical cost"):
        dcb.audit_artifacts(manifest_path)


def test_trial_project_gate_cannot_be_forged_in_manifest(fixture_stage):
    _, output_dir = fixture_stage
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["gate_summary"]["trial_project_gate"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="paired results or gates"):
        dcb.audit_artifacts(manifest_path)


def test_rehashed_no_switch_trial_event_is_rejected_by_action_audit(fixture_stage):
    import hashlib

    _, output_dir = fixture_stage
    actions_path = output_dir / "actions.jsonl"
    with actions_path.open("a", encoding="utf-8") as output:
        output.write(json.dumps({
            "seed": 73, "protocol": dcb.TRIAL_ARMS[1],
            "event": "trial_pending", "flow_id": 1,
            "src": 0, "dst": 1, "path": [0, 2, 1], "time": 1.0,
        }) + "\n")
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_sha256"]["actions.jsonl"] = hashlib.sha256(
        actions_path.read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="trial action provenance"):
        dcb.audit_artifacts(manifest_path)


def test_rehashed_queue_wait_claim_is_rejected_by_physical_audit(fixture_stage):
    import hashlib

    _, output_dir = fixture_stage
    tx_path = output_dir / "transmissions.jsonl"
    records = [json.loads(line) for line in tx_path.read_text(encoding="utf-8").splitlines()]
    records[0]["request_time"] -= 1.0
    tx_path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_sha256"]["transmissions.jsonl"] = hashlib.sha256(
        tx_path.read_bytes()
    ).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="committed request/TX join|queue wait"):
        dcb.audit_artifacts(manifest_path)


def test_rehashed_state_peak_requires_matching_live_transitions(fixture_stage):
    import hashlib

    _, output_dir = fixture_stage
    state_path = output_dir / "state.jsonl"
    states = [json.loads(line) for line in state_path.read_text(encoding="utf-8").splitlines()]
    counts = states[0]["state"]["peak_feedback_windows_by_destination"]
    node_id = next(node for node, value in counts.items() if value < 8)
    counts[node_id] += 1
    state_path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in states),
        encoding="utf-8",
    )
    runs_path = output_dir / "runs.jsonl"
    runs = [json.loads(line) for line in runs_path.read_text(encoding="utf-8").splitlines()]
    runs[0]["row"]["feedback_window_sum_of_node_peaks"] += 1
    runs_path.write_text(
        "".join(json.dumps(record, sort_keys=True) + "\n" for record in runs),
        encoding="utf-8",
    )
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name in ("state.jsonl", "runs.jsonl"):
        manifest["artifact_sha256"][name] = hashlib.sha256(
            (output_dir / name).read_bytes()
        ).hexdigest()
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="state peak|transition"):
        dcb.audit_artifacts(manifest_path)


def test_direct_script_dispatches_through_canonical_module_without_a_seed():
    import subprocess
    import sys
    from pathlib import Path

    script = Path(dcb.__file__).resolve()
    code = """
import runpy
import sys
from tools import run_dcb_experiment as dcb

def canonical_main():
    print("canonical DCB entry reached")

dcb.main = canonical_main
runpy.run_path(sys.argv[1], run_name="__main__")
"""
    completed = subprocess.run(
        [sys.executable, "-c", code, str(script)],
        cwd=script.parents[1], capture_output=True, text=True, check=False,
    )

    assert completed.returncode == 0
    assert "canonical DCB entry reached" in completed.stdout
