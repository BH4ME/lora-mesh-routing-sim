import json

import pytest
from types import SimpleNamespace

from lora_mesh_sim import Packet, Transmission
from tools import screen_trial_public as screen
from tools import run_sr_experiment as sr


@pytest.mark.parametrize("seed,arm", [
    (47001, "meshecho-dcb-trial"),
    (48001, "meshecho-dcb-trial"),
    (49200, "meshecho-dcb-trial"),
    (49201, "meshecho-sr"),
])
def test_capture_rejects_any_out_of_screen_seed_or_arm(seed, arm):
    with pytest.raises(ValueError, match="public trial screen"):
        screen.capture_arm(seed, arm)


def test_capture_uses_frozen_case_and_returns_recorded_physical_transmissions(monkeypatch):
    tx = SimpleNamespace(sender=0, packet=SimpleNamespace(kind="DATA"), start=2.0)
    observed = {}

    def fake_run(case, arm, seed, deadline_s):
        observed.update(case=case, arm=arm, seed=seed, deadline_s=deadline_s)
        recorder = sr.RecordingSimulator()
        recorder.tx_history.append(tx)
        return sr.SrRun({"seed": seed}, [], [])

    monkeypatch.setattr(sr, "run_one_sr", fake_run)
    monkeypatch.setattr(screen, "make_recorder", lambda *args, **kwargs:
                        SimpleNamespace(tx_history=[]))

    result = screen.capture_arm(49201, "meshecho-dcb-trial")

    assert observed == {
        "case": sr.SR_CASES["recurring_fading"],
        "arm": "meshecho-dcb-trial", "seed": 49201, "deadline_s": 30.0,
    }
    assert result["transmissions"] == [tx]


def _matrix():
    return {
        (seed, arm): {
            "row": {
                "seed": seed, "protocol": arm,
                "case": "recurring_fading", "case_config_sha256": "same-case",
                "scheduled_trace_sha256": f"trace-{seed}",
                "scheduled_unicast_flows": 1, "application_deadline_s": 30.0,
                "ack_pdr_deadline": 1.0, "destination_pdr_deadline": 1.0,
                "whole_network_tx_airtime_s": 1.0,
            },
            "flows": [{"seed": seed, "protocol": arm, "flow_id": 1,
                       "src": 0, "dst": 3, "enqueued_at": 1.0}],
            "actions": [{"seed": seed, "protocol": arm, "event": "decision",
                         "flow_id": 1, "src": 0, "dst": 3,
                         "action": "F", "time": 1.0}],
            "transmissions": [],
        }
        for seed in screen.SEEDS for arm in screen.ARMS
    }


def _add_flow(captures, seed, flow_id, when):
    for arm in screen.ARMS:
        run = captures[(seed, arm)]
        run["row"]["scheduled_unicast_flows"] += 1
        run["flows"].append({"seed": seed, "protocol": arm,
                             "flow_id": flow_id, "src": 0, "dst": 3,
                             "enqueued_at": when})


def _trial_data(flow_id=2, start=2.0):
    packet = Packet(kind="DATA", flow_id=flow_id, origin=0, final_dst=3,
                    ttl=6, created_at=start, protocol=screen.ARMS[0],
                    request_id=flow_id, path=(0, 2, 3))
    return Transmission(flow_id, 0, packet, start, start + 0.1)


def _trial_ack(flow_id=2, end=2.5, marker=None):
    packet = Packet(kind="ACK", flow_id=flow_id, origin=3, final_dst=0,
                    ttl=6, created_at=end - 0.05, protocol=screen.ARMS[0],
                    request_id=flow_id, path=(0, 2, 3), path_index=0,
                    app_payload=False, repair_index=marker,
                    backup_epoch_id=1 if marker == 4 else None)
    return Transmission(10 + flow_id, 2, packet, end - 0.05, end)


@pytest.mark.parametrize("field,value", [
    ("case_config_sha256", "changed"),
    ("scheduled_trace_sha256", "changed"),
])
def test_summary_rejects_unpaired_case_or_application_hash(field, value):
    captures = _matrix()
    captures[(49201, screen.ARMS[1])]["row"][field] = value

    with pytest.raises(ValueError, match="paired"):
        screen.summarize_screen(captures)


def test_summary_rejects_incomplete_or_out_of_screen_matrix():
    captures = _matrix()
    captures.pop((49201, screen.ARMS[0]))
    with pytest.raises(ValueError, match="matrix"):
        screen.summarize_screen(captures)


def test_trial_exposure_counts_physical_start_not_decision_only():
    captures = _matrix()
    for seed in (49201, 49202):
        _add_flow(captures, seed, 2, 2.0)
        captures[(seed, screen.ARMS[0])]["actions"].append({
            "seed": seed, "protocol": screen.ARMS[0],
            "event": "decision", "flow_id": 2, "src": 0, "dst": 3,
            "action": "R", "reason": "ack-proven-trial", "time": 2.0,
        })
    captures[(49201, screen.ARMS[0])]["transmissions"].append(_trial_data())

    result = screen.summarize_screen(captures)

    assert result["aggregate"]["trial_decisions"] == 2
    assert result["aggregate"]["physical_trial_starts"] == 1
    assert result["aggregate"]["physical_trial_start_seeds"] == 1


def test_ack_commit_guard_abandonment_and_blind_commit_are_physically_joined():
    captures = _matrix()
    for seed in (49201, 49202):
        _add_flow(captures, seed, 2, 2.0)
        run = captures[(seed, screen.ARMS[0])]
        run["actions"].append({"event": "decision", "flow_id": 2,
                               "src": 0, "dst": 3, "action": "R",
                               "reason": "ack-proven-trial", "time": 2.0})
        run["transmissions"].append(_trial_data())
    acked = captures[(49201, screen.ARMS[0])]
    acked["flows"][-1]["acked_at"] = 2.5
    acked["transmissions"].append(_trial_ack())
    acked["actions"].append({"event": "commit", "action": "R-trial",
                             "flow_id": 2, "src": 0, "dst": 3,
                             "path": (0, 2, 3), "time": 2.5})
    abandoned = captures[(49202, screen.ARMS[0])]
    abandoned["actions"].append({"event": "trial_abandoned",
                                 "flow_id": 2, "reason": "source-ack-guard",
                                 "time": 17.0})
    blind = captures[(49201, screen.ARMS[2])]
    blind["flows"][-1]["acked_at"] = 2.5
    blind["transmissions"].append(_trial_ack(marker=4))
    blind["actions"].extend((
        {"event": "dcb_source_ack_rx", "flow_id": 2, "accepted": True,
         "path": (0, 2, 3), "time": 2.5},
        {"event": "commit", "action": "R-backup-blind", "flow_id": 2,
         "src": 0, "dst": 3, "path": (0, 2, 3), "time": 2.5},
    ))

    result = screen.summarize_screen(captures)

    assert result["aggregate"]["ordinary_trial_ack_commits"] == 1
    assert result["aggregate"]["source_guard_abandonments"] == 1
    assert result["aggregate"]["blind_commits"] == 1
    assert result["aggregate"]["exposure_screen_pass"] is False


def test_screen_reports_five_arm_endpoints_and_descriptive_paired_differences():
    captures = _matrix()
    trial = captures[(49201, screen.ARMS[0])]["row"]
    trial.update(ack_pdr_deadline=0.75, destination_pdr_deadline=0.8,
                 whole_network_tx_airtime_s=9.0)
    for arm, ack, delivery, airtime in zip(
        screen.ARMS[1:], (0.5, 0.6, 0.7, 0.4),
        (0.6, 0.7, 0.9, 0.5), (10.0, 12.0, 15.0, 20.0),
    ):
        captures[(49201, arm)]["row"].update(
            ack_pdr_deadline=ack,
            destination_pdr_deadline=delivery,
            whole_network_tx_airtime_s=airtime,
        )

    result = screen.summarize_screen(captures)
    first = result["per_seed"][0]

    assert set(first["arm_metrics"]) == set(screen.ARMS)
    assert first["arm_metrics"][screen.ARMS[0]] == {
        "scheduled_unicast_flows": 1,
        "ack_pdr_deadline": 0.75,
        "destination_pdr_deadline": 0.8,
        "whole_network_tx_airtime_s": 9.0,
    }
    assert set(first["paired_deltas"]) == set(screen.ARMS[1:])
    assert first["paired_deltas"][screen.ARMS[1]] == pytest.approx({
        "ack_pdr_delta": 0.25,
        "destination_pdr_delta": 0.2,
        "relative_airtime_delta": -0.1,
    })
    assert result["aggregate"]["mean_paired_deltas"][screen.ARMS[1]] == pytest.approx({
        "ack_pdr_delta": 0.025,
        "destination_pdr_delta": 0.02,
        "relative_airtime_delta": -0.01,
    })


def test_divergence_joins_same_flow_decisions_to_initial_physical_source_path():
    captures = _matrix()
    seed = 49201
    for arm in (screen.ARMS[0], screen.ARMS[1], screen.ARMS[3]):
        captures[(seed, arm)]["actions"][0].update(action="R", reason="confirmed-route")
    captures[(seed, screen.ARMS[3])]["actions"][0].update(action="D", reason="aging")
    for arm, path in ((screen.ARMS[0], (0, 2, 3)),
                      (screen.ARMS[1], (0, 3))):
        packet = Packet(kind="DATA", flow_id=1, origin=0, final_dst=3,
                        ttl=6, created_at=1.0, protocol=arm,
                        request_id=1, path=path)
        captures[(seed, arm)]["transmissions"].append(
            Transmission(1, 0, packet, 1.0, 1.1)
        )
    rreq = Packet(kind="RREQ", flow_id=1, origin=0, final_dst=3,
                  ttl=6, created_at=1.0, protocol=screen.ARMS[3],
                  request_id=1, path=(0,))
    captures[(seed, screen.ARMS[3])]["transmissions"].append(
        Transmission(2, 0, rreq, 1.0, 1.1)
    )

    result = screen.summarize_screen(captures)
    first = result["per_seed"][0]
    no_switch = first["flow_divergences"][screen.ARMS[1]]
    old_dcb = first["flow_divergences"][screen.ARMS[3]]

    assert no_switch == [{
        "flow_id": 1,
        "trial_decision_action": "R", "control_decision_action": "R",
        "trial_physical_action": "R", "control_physical_action": "R",
        "trial_initial_path": (0, 2, 3), "control_initial_path": (0, 3),
        "decision_action_differs": False,
        "physical_action_differs": False, "physical_path_differs": True,
    }]
    assert old_dcb[0]["decision_action_differs"] is True
    assert old_dcb[0]["physical_action_differs"] is True
    assert old_dcb[0]["physical_path_differs"] is False
    assert old_dcb[0]["control_physical_action"] == "D"
    assert first["flow_divergence_counts"][screen.ARMS[1]] == {
        "decision_action": 0,
        "physical_action": 0,
        "physical_path": 1,
        "physical_action_or_path": 1,
    }
    assert first["flow_divergence_counts"][screen.ARMS[3]] == {
        "decision_action": 1,
        "physical_action": 1,
        "physical_path": 0,
        "physical_action_or_path": 1,
    }
    assert result["aggregate"]["flow_divergence_counts"][screen.ARMS[1]][
        "physical_path"
    ] == 1


@pytest.mark.parametrize("field,value", [
    ("case", "random_pairs"),
    ("application_deadline_s", 15.0),
])
def test_summary_rejects_uniformly_wrong_frozen_input(field, value):
    captures = _matrix()
    for run in captures.values():
        run["row"][field] = value

    with pytest.raises(ValueError, match="fixed"):
        screen.summarize_screen(captures)


def test_summary_rejects_config_hash_that_changes_between_seeds():
    captures = _matrix()
    for arm in screen.ARMS:
        captures[(49202, arm)]["row"]["case_config_sha256"] = "second-case"

    with pytest.raises(ValueError, match="case config"):
        screen.summarize_screen(captures)


def test_summary_rejects_claimed_flow_count_without_saved_flow_records():
    captures = _matrix()
    for arm in screen.ARMS:
        captures[(49201, arm)]["row"]["scheduled_unicast_flows"] = 2

    with pytest.raises(ValueError, match="flow count"):
        screen.summarize_screen(captures)


def test_cli_writes_fixed_matrix_and_provenance_without_replacing_output(monkeypatch, tmp_path):
    captures = _matrix()
    calls = []

    def fake_capture(seed, arm):
        calls.append((seed, arm))
        return captures[(seed, arm)]

    monkeypatch.setattr(screen, "capture_arm", fake_capture)
    monkeypatch.setattr(screen, "fixed_case_hash", lambda: "same-case")
    out = tmp_path / "public-screen.json"

    screen.main(["--run-public-screen", "--out", str(out)])
    payload = json.loads(out.read_text(encoding="utf-8"))

    assert calls == [(seed, arm) for seed in screen.SEEDS for arm in screen.ARMS]
    assert payload["fixed_inputs"]["seeds"] == list(screen.SEEDS)
    assert payload["fixed_inputs"]["arms"] == list(screen.ARMS)
    assert payload["fixed_inputs"]["case_config_sha256"] == "same-case"
    assert set(payload["provenance"]["source_sha256"]) == {
        "lora_mesh_sim.py", "tools/run_sr_experiment.py",
        "tools/screen_trial_public.py",
        "docs/research/meshecho_trial_public_mechanism_screen.md",
    }
    assert all(len(digest) == 64 for digest in payload["provenance"]["source_sha256"].values())
    assert len(payload["per_seed"]) == 10
    with pytest.raises(FileExistsError):
        screen.main(["--run-public-screen", "--out", str(out)])
    assert len(calls) == 50


def test_cli_requires_explicit_run_flag_before_capture(monkeypatch, tmp_path):
    monkeypatch.setattr(screen, "capture_arm", lambda *_: pytest.fail("capture started"))

    with pytest.raises(SystemExit):
        screen.main(["--out", str(tmp_path / "screen.json")])


def test_cli_refuses_output_if_source_changes_during_capture(monkeypatch, tmp_path):
    captures = _matrix()
    monkeypatch.setattr(screen, "capture_arm", lambda seed, arm: captures[(seed, arm)])
    monkeypatch.setattr(screen, "fixed_case_hash", lambda: "same-case")
    hashes = iter(({"source": "before"}, {"source": "after"}))
    monkeypatch.setattr(screen, "source_hashes", lambda: next(hashes))
    out = tmp_path / "screen.json"

    with pytest.raises(ValueError, match="changed during capture"):
        screen.main(["--run-public-screen", "--out", str(out)])
    assert not out.exists()
