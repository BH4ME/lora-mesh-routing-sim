"""Behavioral checks for the exploratory source-action archive."""

from dataclasses import asdict
import hashlib
import json

import pytest

from lora_mesh_sim import Packet, Transmission
from tools import screen_source_action_public as screen
from tools import run_sr_experiment as sr


SEED = 17


def _tx(arm, kind="FLOOD", start=1.2, *, repair_index=None, path=(0,)):
    packet = Packet(
        kind=kind, flow_id=1, origin=0, final_dst=2, ttl=6,
        created_at=1.0, protocol=arm, request_id=1, path=path,
        repair_index=repair_index,
    )
    return {
        **asdict(Transmission(1, 0, packet, start, start + 0.1)),
        "requested_at": start - 0.05,
        "queue_wait_s": 0.05,
    }


def _trace_hash(flows):
    trace = [[flow["enqueued_at"], flow["src"], flow["dst"], flow["flow_id"]]
             for flow in flows]
    return hashlib.sha256(json.dumps(trace, separators=(",", ":")).encode("ascii")).hexdigest()


def _capture(arm):
    flows = [{
        "case": "recurring_fading", "protocol": arm, "seed": SEED,
        "flow_id": 1, "src": 0, "dst": 2, "enqueued_at": 1.0,
        "deadline_at": 31.0, "source_action": "F", "acked_at": 2.0,
        "delivered_at": 1.8, "ack_by_deadline": True,
        "delivery_by_deadline": True,
    }]
    tx = _tx(arm)
    return {
        "row": {
            "case": "recurring_fading", "protocol": arm, "seed": SEED,
            "case_config_sha256": screen.fixed_case_hash(),
            "scheduled_trace_sha256": _trace_hash(flows),
            "scheduled_unicast_flows": 1, "generation_horizon_s": 600.0,
            "application_deadline_s": 30.0, "drain_until_s": 630.0,
            "ack_by_deadline": 1, "delivery_by_deadline": 1,
            "ack_pdr_deadline": 1.0, "destination_pdr_deadline": 1.0,
            "whole_network_tx_airtime_s": 0.1,
            "windowed_tx_count": 1, "queued_future_tx_count": 0,
            "windowed_tx_bytes": Packet(**tx["packet"]).wire_size_bytes(32),
            "tx_energy_j": 0.0396, "raw_modeled_rx_energy_j": 0.0,
            "collision_failures": 0, "raw_tx_count": 1,
        },
        "flows": flows,
        "actions": [{
            "case": "recurring_fading", "protocol": arm, "seed": SEED,
            "event": "decision", "time": 1.0, "flow_id": 1,
            "src": 0, "dst": 2, "action": "F", "reason": "no-confirmed-route",
        }],
        "transmissions": [tx],
    }


def _matrix():
    return {(SEED, arm): _capture(arm) for arm in screen.ARMS}


def _set_txs(run, transmissions):
    run["transmissions"] = transmissions
    charged = [tx for tx in transmissions if tx["start"] <= screen.TX_CUTOFF_S]
    airtime = sum(tx["end"] - tx["start"] for tx in charged)
    run["row"]["whole_network_tx_airtime_s"] = airtime
    run["row"]["tx_energy_j"] = airtime * 3.3 * 0.12
    run["row"]["raw_tx_count"] = len(transmissions)
    run["row"]["windowed_tx_count"] = len(charged)
    run["row"]["queued_future_tx_count"] = len(transmissions) - len(charged)
    run["row"]["windowed_tx_bytes"] = sum(
        Packet(**tx["packet"]).wire_size_bytes(32) for tx in charged
    )


def test_synthetic_matrix_joins_first_source_wire_action_and_deadline_outcomes():
    captures = _matrix()
    old = captures[(SEED, "meshecho-dcb")]
    old["actions"][0].update(action="D", reason="repeated-cold-misses")
    old["transmissions"] = [_tx("meshecho-dcb", "RREQ")]
    old["row"]["windowed_tx_bytes"] = Packet(
        **old["transmissions"][0]["packet"]
    ).wire_size_bytes(32)

    result = screen.summarize_screen(captures, seeds=(SEED,))

    old_flow = result["joined_flows"][(SEED, "meshecho-dcb")][0]
    assert old_flow["decision_action"] == "D"
    assert old_flow["first_source_physical_action"] == "D"
    assert old_flow["first_source_tx_start"] == 1.2
    assert old_flow["ack_by_deadline"] is True
    assert result["per_seed"][0]["arms"]["meshecho-dcb"]["old_d_cold_decisions"] == 1


def test_artifact_archives_exact_raw_records_with_verifiable_hashes(tmp_path):
    captures = _matrix()
    tx = captures[(SEED, screen.ARMS[0])]["transmissions"][0]
    tx["packet"]["backup_relay_id"] = 7
    tx["packet"]["backup_epoch_id"] = 101
    captures[(SEED, screen.ARMS[0])]["row"]["windowed_tx_bytes"] = Packet(
        **tx["packet"]
    ).wire_size_bytes(32)
    result = screen.summarize_screen(captures, seeds=(SEED,))

    paths = screen.write_artifacts(
        tmp_path / "source-action", captures, result, {"sim.py": "a" * 64},
    )
    manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    saved_tx = [json.loads(line) for line in paths["transmissions"].read_text().splitlines()]
    saved_flows = [json.loads(line) for line in paths["flows"].read_text().splitlines()]
    saved_actions = [json.loads(line) for line in paths["actions"].read_text().splitlines()]

    assert len(saved_flows) == len(screen.ARMS)
    assert len(saved_actions) == len(screen.ARMS)
    assert len(saved_tx) == len(screen.ARMS)
    assert saved_tx[0]["packet"] == json.loads(json.dumps(tx["packet"]))
    assert saved_tx[0]["start"] == tx["start"]
    assert manifest["source_sha256"] == {"sim.py": "a" * 64}
    assert manifest["scheduled_trace_sha256"][str(SEED)] == _trace_hash(
        captures[(SEED, screen.ARMS[0])]["flows"]
    )
    assert manifest["exploratory_intervals_from_old_dcb"] == result[
        "exploratory_intervals_from_old_dcb"
    ]
    for name in ("flows", "actions", "transmissions", "joined_flows", "per_seed"):
        assert manifest["artifact_sha256"][name] == hashlib.sha256(paths[name].read_bytes()).hexdigest()
    with pytest.raises(FileExistsError):
        screen.write_artifacts(tmp_path / "source-action", captures, result, {"sim.py": "a" * 64})


def test_validation_rejects_truncated_physical_transmission_archive():
    captures = _matrix()
    captures[(SEED, screen.ARMS[1])]["transmissions"].clear()

    with pytest.raises(ValueError, match="physical transmission"):
        screen.summarize_screen(captures, seeds=(SEED,))


def test_validation_rejects_lost_transmission_beyond_cost_window():
    captures = _matrix()
    run = captures[(SEED, screen.ARMS[1])]
    late = _tx(screen.ARMS[1], start=631.0)
    late["tx_id"] = 2
    run["transmissions"].append(late)
    run["row"]["raw_tx_count"] = 2
    run["row"]["queued_future_tx_count"] = 1
    screen.summarize_screen(captures, seeds=(SEED,))

    run["transmissions"].pop()
    with pytest.raises(ValueError, match="physical transmission"):
        screen.summarize_screen(captures, seeds=(SEED,))


@pytest.mark.parametrize("count_field,wrong_count", [
    ("windowed_tx_count", 0),
    ("queued_future_tx_count", 1),
])
def test_validation_rejects_windowed_or_queued_tx_count_mismatch(
    count_field, wrong_count,
):
    captures = _matrix()
    captures[(SEED, screen.ARMS[1])]["row"][count_field] = wrong_count

    with pytest.raises(ValueError, match="physical transmission"):
        screen.summarize_screen(captures, seeds=(SEED,))


@pytest.mark.parametrize("packet_field,wrong_value", [
    ("protocol", "meshecho-dcb"),
    ("flow_id", 999),
])
def test_validation_rejects_physical_transmission_from_another_arm_or_flow(
    packet_field, wrong_value,
):
    captures = _matrix()
    run = captures[(SEED, screen.ARMS[1])]
    run["transmissions"][0]["packet"][packet_field] = wrong_value

    with pytest.raises(ValueError, match="physical transmission"):
        screen.summarize_screen(captures, seeds=(SEED,))


def test_validation_rejects_deadline_outcome_claim_that_disagrees_with_timestamps():
    captures = _matrix()
    captures[(SEED, screen.ARMS[2])]["flows"][0]["ack_by_deadline"] = False

    with pytest.raises(ValueError, match="deadline outcome"):
        screen.summarize_screen(captures, seeds=(SEED,))


def test_validation_rejects_self_consistent_but_unpaired_scheduled_trace():
    captures = _matrix()
    run = captures[(SEED, screen.ARMS[1])]
    run["flows"][0]["enqueued_at"] = 1.05
    run["flows"][0]["deadline_at"] = 31.05
    run["row"]["scheduled_trace_sha256"] = _trace_hash(run["flows"])

    with pytest.raises(ValueError, match="paired scheduled traces"):
        screen.summarize_screen(captures, seeds=(SEED,))


def test_d_candidate_data_is_not_counted_as_timeout_fallback_recovery():
    captures = _matrix()
    old = captures[(SEED, "meshecho-dcb")]
    old["actions"][0].update(action="D", reason="aging-confirmed-route")
    old["actions"].append({
        "case": "recurring_fading", "protocol": "meshecho-dcb", "seed": SEED,
        "event": "candidate", "time": 1.5, "flow_id": 1,
        "src": 0, "dst": 2, "action": "D", "path": (0, 2),
    })
    candidate = _tx("meshecho-dcb", "DATA", 1.6, path=(0, 2))
    candidate["tx_id"] = 2
    _set_txs(old, [_tx("meshecho-dcb", "RREQ"), candidate])

    result = screen.summarize_screen(captures, seeds=(SEED,))
    flow = result["joined_flows"][(SEED, "meshecho-dcb")][0]

    assert flow["rrep_candidate"] is True
    assert flow["d_candidate_physical"] is True
    assert flow["d_fallback_physical"] is False
    assert flow["eventual_recovery_source_txs"] == []
    assert result["per_seed"][0]["arms"]["meshecho-dcb"]["d_rrep_candidate_physical"] == 1


def test_candidate_ack_timeout_is_not_counted_as_discovery_timeout():
    captures = _matrix()
    old = captures[(SEED, "meshecho-dcb")]
    old["actions"][0].update(action="D", reason="aging-confirmed-route")
    old["actions"].extend([
        {
            "case": "recurring_fading", "protocol": "meshecho-dcb", "seed": SEED,
            "event": "candidate", "time": 1.5, "flow_id": 1,
            "src": 0, "dst": 2, "action": "D", "path": (0, 2),
        },
        {
            "case": "recurring_fading", "protocol": "meshecho-dcb", "seed": SEED,
            "event": "timeout", "time": 1.8, "flow_id": 1,
            "src": 0, "dst": 2, "action": "D", "reason": "source-ack-timeout",
        },
    ])
    candidate = _tx("meshecho-dcb", "DATA", 1.6, path=(0, 2))
    candidate["tx_id"] = 2
    _set_txs(old, [_tx("meshecho-dcb", "RREQ"), candidate])

    result = screen.summarize_screen(captures, seeds=(SEED,))
    flow = result["joined_flows"][(SEED, "meshecho-dcb")][0]

    assert flow["rrep_candidate"] is True
    assert flow["d_candidate_physical"] is True
    assert flow["d_timeout"] is False
    assert flow["d_fallback_physical"] is False
    assert result["per_seed"][0]["arms"]["meshecho-dcb"]["d_timeouts"] == 0


def test_queue_wait_uses_physical_request_time_not_application_latency():
    result = screen.summarize_screen(_matrix(), seeds=(SEED,))

    flow = result["joined_flows"][(SEED, screen.ARMS[0])][0]
    assert flow["first_source_start_latency_s"] == pytest.approx(0.2)
    assert flow["source_queue_wait_s"] == pytest.approx(0.05)
    assert result["per_seed"][0]["arms"][screen.ARMS[0]]["whole_network_queue_wait_s"] == pytest.approx(0.05)


@pytest.mark.parametrize("seed,arm", [
    (17, "meshecho-dcb"),
    (47001, "meshecho-dcb"),
    (48001, "meshecho-dcb"),
    (49300, "meshecho-dcb"),
    (49311, "meshecho-dcb"),
    (49301, "meshecho-sr"),
])
def test_capture_rejects_any_seed_or_arm_outside_fixed_public_matrix(monkeypatch, seed, arm):
    monkeypatch.setattr(sr, "run_one_sr", lambda *_: pytest.fail("runner called"))

    with pytest.raises(ValueError, match="fixed public matrix"):
        screen.capture_arm(seed, arm)


def test_capture_on_nonreserved_seed_records_real_physical_queue_wait(monkeypatch):
    monkeypatch.setattr(screen, "SEEDS", (SEED,))

    capture = screen.capture_arm(SEED, "meshecho-dcb")

    assert capture["row"]["scheduled_trace_sha256"] == _trace_hash(capture["flows"])
    assert capture["row"]["scheduled_unicast_flows"] == len(capture["flows"])
    assert capture["transmissions"]
    for tx in capture["transmissions"]:
        assert tx["requested_at"] <= tx["start"]
        assert tx["queue_wait_s"] == pytest.approx(tx["start"] - tx["requested_at"])


def test_report_counts_replacement_and_physical_divergence_without_flow_counterfactuals():
    captures = _matrix()
    old = captures[(SEED, "meshecho-dcb")]
    old["actions"][0].update(action="D", reason="aging-confirmed-route")
    _set_txs(old, [_tx("meshecho-dcb", "RREQ")])
    fr = captures[(SEED, "meshecho-dcb-source-fr")]
    fr["actions"][0].update(action="R", reason="aging-confirmed-route-fr-control")
    _set_txs(fr, [_tx("meshecho-dcb-source-fr", "DATA", path=(0, 2))])
    trigger = captures[(SEED, "meshecho-dcb-source-trigger-f")]
    trigger["actions"][0].update(action="F", reason="aging-confirmed-route-trigger-f")
    trial = captures[(SEED, "meshecho-dcb-trial")]
    trial["actions"][0].update(action="F", reason="route-ack-miss")
    trial["flows"][0].update(acked_at=None, ack_by_deadline=False)
    trial["row"].update(ack_by_deadline=0, ack_pdr_deadline=0.0)

    result = screen.summarize_screen(captures, seeds=(SEED,))
    seed = result["per_seed"][0]

    assert seed["old_d_replacements"]["meshecho-dcb-source-fr"]["decision_actions"] == {"R": 1}
    assert seed["old_d_replacements"]["meshecho-dcb-source-trigger-f"]["physical_actions"] == {"F": 1}
    assert seed["physical_divergence_from_old_dcb"]["meshecho-dcb-source-fr"]["action"] == 1
    assert seed["arms"]["meshecho-dcb-trial"]["one_miss_f_decisions"] == 1
    assert seed["paired_deltas_from_old_dcb"]["meshecho-dcb-trial"]["ack_pdr_delta"] == -1.0
    assert result["exploratory_intervals_from_old_dcb"]["meshecho-dcb-trial"]["ack_pdr_delta"]["mean"] == -1.0


def test_paired_energy_keeps_windowed_tx_and_raw_rx_accounting_separate():
    captures = _matrix()
    captures[(SEED, screen.ARMS[0])]["row"]["raw_modeled_rx_energy_j"] = 10.0
    captures[(SEED, screen.ARMS[1])]["row"]["raw_modeled_rx_energy_j"] = 15.0

    paired = screen.summarize_screen(captures, seeds=(SEED,))["per_seed"][0][
        "paired_deltas_from_old_dcb"
    ][screen.ARMS[1]]

    assert paired["windowed_tx_energy_delta_j"] == pytest.approx(0.0)
    assert paired["raw_modeled_rx_energy_delta_j"] == pytest.approx(5.0)
    assert "modeled_energy_delta_j" not in paired


def test_backup_ack_count_requires_matching_physical_ack_end():
    captures = _matrix()
    old = captures[(SEED, "meshecho-dcb")]
    old["actions"].append({
        "case": "recurring_fading", "protocol": "meshecho-dcb", "seed": SEED,
        "event": "dcb_source_ack_rx", "time": 2.0, "flow_id": 1,
        "accepted": True, "path": (0, 1, 2),
    })
    assert screen.summarize_screen(captures, seeds=(SEED,))["per_seed"][0]["arms"]["meshecho-dcb"]["accepted_backup_acks"] == 0

    packet = Packet(
        kind="ACK", flow_id=1, origin=2, final_dst=0, ttl=6,
        created_at=1.9, protocol="meshecho-dcb", request_id=1,
        path=(0, 1, 2), path_index=0, app_payload=False,
        repair_index=4, backup_epoch_id=101,
    )
    ack = {
        **asdict(Transmission(2, 1, packet, 1.95, 2.0)),
        "requested_at": 1.95, "queue_wait_s": 0.0,
    }
    _set_txs(old, [old["transmissions"][0], ack])

    assert screen.summarize_screen(captures, seeds=(SEED,))["per_seed"][0]["arms"]["meshecho-dcb"]["accepted_backup_acks"] == 1


def test_cli_requires_explicit_run_flag_before_any_capture(monkeypatch, tmp_path):
    monkeypatch.setattr(screen, "capture_arm", lambda *_: pytest.fail("capture started"))

    with pytest.raises(SystemExit):
        screen.main(["--out-prefix", str(tmp_path / "source-action")])


def test_cli_captures_seven_arms_and_writes_verifiable_artifacts_on_nonreserved_seed(
    monkeypatch, tmp_path, capsys,
):
    monkeypatch.setattr(screen, "SEEDS", (SEED,))
    prefix = tmp_path / "source-action"

    screen.main(["--run-public-screen", "--out-prefix", str(prefix)])

    manifest_path = tmp_path / "source-action.manifest.json"
    assert capsys.readouterr().out.strip() == str(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["fixed_inputs"]["seeds"] == [SEED]
    assert manifest["fixed_inputs"]["arms"] == list(screen.ARMS)
    assert manifest["record_counts"]["runs"] == len(screen.ARMS)
    assert manifest["record_counts"]["transmissions"] > 0
    for name, digest in manifest["artifact_sha256"].items():
        saved = tmp_path / f"source-action.{name}.jsonl"
        assert hashlib.sha256(saved.read_bytes()).hexdigest() == digest
