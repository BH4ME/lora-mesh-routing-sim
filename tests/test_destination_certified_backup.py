"""Public-behavior checks for the passive destination-certified backup screen."""

import json
import math
from copy import deepcopy
from dataclasses import asdict

from lora_mesh_sim import MeshEchoDHRDelayedAck, Node, Packet, RadioConfig
from tools.run_sr_experiment import RecordingSimulator
from tools.diagnose_destination_certified_backup import (
    PassiveBackupSimulator,
    analyze_backup_exposure,
    analyze_candidate_epochs,
    run_diagnostic,
    summarize_backup_cohort,
)


def two_path_fixture(simulator_type, cutoff_s=10.0, sf=7):
    sim = simulator_type(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0), Node(2, 20.0, 0.0)],
        RadioConfig(sf=sf, tx_power_dbm=17.0, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(flood_base_delay_s=0.2, flood_jitter_s=0.0),
        seed=73, max_hops=3, independent_random_streams=True,
    )
    sim.schedule(0.1, "app_send", (0, 2, 7))
    sim.schedule(4.0, "app_send", (0, 2, 8))
    sim.run(cutoff_s)
    return sim


def jammed_primary_fixture(cutoff_s=7.0):
    sim = PassiveBackupSimulator(
        [Node(0, 0.0, 0.0), Node(1, 1.0, 0.0),
         Node(2, 20.0, 0.0), Node(3, 20.0, 0.0, role="client")],
        RadioConfig(sf=7, tx_power_dbm=17.0, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(flood_base_delay_s=0.2, flood_jitter_s=0.0),
        seed=73, max_hops=3, independent_random_streams=True,
    )
    sim.schedule(0.1, "app_send", (0, 2, 7))
    sim.schedule(4.0, "app_send", (0, 2, 8))
    interferer = Packet(
        kind="NOISE", flow_id=99, origin=3, final_dst=2, ttl=1,
        created_at=4.0, protocol="cochannel", path=(3,),
    )
    sim.transmit_later(3, interferer, delay_s=4.0)
    sim.run(cutoff_s)
    return sim


def test_accepted_direct_f_with_two_hop_alternate_exposes_later_r_relay():
    stock = two_path_fixture(RecordingSimulator)
    observed = two_path_fixture(PassiveBackupSimulator)
    rows = analyze_backup_exposure(observed)

    assert [asdict(tx) for tx in observed.tx_history] == [
        asdict(tx) for tx in stock.tx_history
    ]
    assert observed.random.getstate() == stock.random.getstate()
    assert observed.channel_random.getstate() == stock.channel_random.getstate()
    assert observed.protocol.action_events == stock.protocol.action_events
    assert {flow_id: asdict(flow) for flow_id, flow in observed.metrics.flows.items()} == {
        flow_id: asdict(flow) for flow_id, flow in stock.metrics.flows.items()
    }
    assert len(rows) == 1
    row = rows[0]
    assert row["flow_id"] == 8
    assert row["commit_flow_id"] == 7
    assert row["primary_path"] == (0, 2)
    assert row["backup_path"] == (0, 1, 2)
    assert row["relay_decoded_current_r"] is True
    assert row["destination_decoded_current_r"] is True
    assert row["relay_decoded_destination_ack_by_0_5_s"] is True
    assert row["relay_decoded_destination_ack_by_2_s"] is True


def test_real_case_observer_preserves_stock_and_replays_exactly():
    result = run_diagnostic(73)

    assert result["parity"]["exact"] is True
    assert result["strict_replay_exact"] is True
    assert len(result["rows"]) == result["summary"]["nominated_initial_direct_r"]
    assert result["parity"]["scheduled_trace_sha256"] == (
        result["row"]["scheduled_trace_sha256"]
    )
    assert "flood_decodes" in result
    assert "destination_ack_decodes" in result
    assert "candidate_epochs" in result
    json.dumps(result["flood_decodes"])
    json.dumps(result["destination_ack_decodes"])
    json.dumps(result["candidate_epochs"])


def test_ninth_concurrent_f_window_cannot_certify_a_relay():
    sim = PassiveBackupSimulator(
        [Node(node_id, float(node_id), 0.0) for node_id in range(11)],
        RadioConfig(sf=7, tx_power_dbm=17.0, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(flood_base_delay_s=10.0, flood_jitter_s=0.0),
        seed=73, max_hops=3, independent_random_streams=True,
    )
    for src in range(9):
        sim.schedule(0.1 + 0.2 * src, "app_send", (src, 9, src + 1))
    alternate = Packet(
        kind="FLOOD", flow_id=9, origin=8, final_dst=9, ttl=2,
        created_at=1.7, protocol=sim.protocol.name, request_id=9,
        path=(8, 10),
    )
    sim.transmit_later(10, alternate, delay_s=1.9)
    sim.schedule(5.0, "app_send", (8, 9, 10))
    sim.run(7.0)

    assert sim.protocol.flow_actions[10] == "R"
    assert any(item.flow_id == 9 and item.path == (8, 10, 9)
               for item in sim.flood_decodes)
    assert not any(row["flow_id"] == 10 for row in analyze_backup_exposure(sim))


def test_unfinished_r_reception_is_censored_not_counted_as_a_failure():
    sim = two_path_fixture(PassiveBackupSimulator, cutoff_s=4.02)

    row, = analyze_backup_exposure(sim)
    assert row["r_receive_censored"] is True
    assert row["relay_decoded_current_r"] is None
    assert row["destination_decoded_current_r"] is None


def test_f_window_capacity_is_local_to_each_destination():
    sim = PassiveBackupSimulator(
        [Node(node_id, float(node_id), 0.0) for node_id in range(13)],
        RadioConfig(sf=7, tx_power_dbm=17.0, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(flood_base_delay_s=10.0, flood_jitter_s=0.0),
        seed=73, max_hops=3, independent_random_streams=True,
    )
    for src in range(8):
        sim.schedule(0.1 + 0.2 * src, "app_send", (src, 9, src + 1))
    sim.schedule(1.7, "app_send", (8, 11, 9))
    alternate = Packet(
        kind="FLOOD", flow_id=9, origin=8, final_dst=11, ttl=2,
        created_at=1.7, protocol=sim.protocol.name, request_id=9,
        path=(8, 12),
    )
    sim.transmit_later(12, alternate, delay_s=1.9)
    sim.schedule(5.0, "app_send", (8, 11, 10))
    sim.run(7.0)

    assert sim.protocol.flow_actions[10] == "R"
    row, = [row for row in analyze_backup_exposure(sim) if row["flow_id"] == 10]
    assert row["backup_path"] == (8, 12, 11)


def test_wrong_request_epoch_is_not_an_initial_r_exposure():
    sim = two_path_fixture(PassiveBackupSimulator)
    invalid = Packet(
        kind="DATA", flow_id=8, origin=0, final_dst=2, ttl=3,
        created_at=4.0, protocol=sim.protocol.name, request_id=999,
        path=(0, 2),
    )
    sim.transmit_later(0, invalid, delay_s=0.0)
    sim.run(12.0)

    assert [row["flow_id"] for row in analyze_backup_exposure(sim)] == [8]


def test_duplicate_source_data_does_not_double_count_initial_r():
    sim = two_path_fixture(PassiveBackupSimulator)
    duplicate = Packet(
        kind="DATA", flow_id=8, origin=0, final_dst=2, ttl=3,
        created_at=4.0, protocol=sim.protocol.name, request_id=8,
        path=(0, 2),
    )
    sim.transmit_later(0, duplicate, delay_s=0.0)
    sim.run(12.0)

    assert [row["flow_id"] for row in analyze_backup_exposure(sim)] == [8]


def test_relay_can_decode_r_when_destination_cannot_and_no_ack_exists():
    sim = jammed_primary_fixture()

    row, = [row for row in analyze_backup_exposure(sim) if row["flow_id"] == 8]
    assert row["relay_decoded_current_r"] is True
    assert row["destination_decoded_current_r"] is False
    assert row["relay_decoded_destination_ack_by_0_5_s"] is False
    assert row["relay_decoded_destination_ack_by_2_s"] is False
    assert not any(tx.packet.kind == "ACK" and tx.packet.flow_id == 8
                   and tx.sender == 2 for tx in sim.tx_history)


def test_stock_f_rescue_airtime_is_separate_from_source_ack_headroom():
    sim = jammed_primary_fixture(cutoff_s=40.0)

    row, = [row for row in analyze_backup_exposure(sim) if row["flow_id"] == 8]
    assert row["destination_decoded_current_r"] is False
    assert row["relay_decoded_current_r"] is True
    assert row["stock_source_ack_by_deadline"] is True
    assert row["stock_destination_delivered_by_deadline"] is True
    assert row["stock_f_recovery_tx_airtime_s"] > 0.0
    assert row["stock_source_ack_headroom"] is False
    assert row["stock_f_rescue_cost_potential"] is True
    assert row["nominal_cost_substitution_eligible_0_5_s"] is True
    assert row["nominal_cost_substitution_eligible_2_s"] is True


def test_missed_ack_overhear_exposes_redundant_relay_start_and_age_bins():
    sim = PassiveBackupSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0), Node(2, 20.0, 0.0)],
        RadioConfig(sf=7, tx_power_dbm=17.0, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(flood_base_delay_s=0.2, flood_jitter_s=0.0),
        seed=73, max_hops=3, independent_random_streams=True,
    )
    sim.schedule(0.1, "app_send", (0, 2, 7))
    sim.schedule(4.0, "app_send", (0, 2, 8))
    busy_relay = Packet(
        kind="NOISE", flow_id=99, origin=1, final_dst=2, ttl=1,
        created_at=4.11, protocol="other-traffic", path=(1,),
    )
    sim.transmit_later(1, busy_relay, delay_s=4.11)
    sim.run(7.0)

    row, = analyze_backup_exposure(sim)
    assert row["relay_decoded_current_r"] is True
    assert row["destination_decoded_current_r"] is True
    assert row["relay_decoded_destination_ack_by_0_5_s"] is False
    assert row["relay_decoded_destination_ack_by_2_s"] is False
    assert row["backup_age_at_r_enqueue_le_60_s"] is True
    assert row["backup_age_at_r_enqueue_le_120_s"] is True
    assert row["nominal_redundant_relay_start_0_5_s"] is True
    assert row["nominal_redundant_relay_start_2_s"] is True


def test_nominal_deadline_slack_and_collision_free_prr_are_offline_proxies():
    sim = jammed_primary_fixture(cutoff_s=40.0)
    row, = [row for row in analyze_backup_exposure(sim) if row["flow_id"] == 8]
    first_r = next(tx for tx in sim.tx_history if tx.tx_id == row["r_tx_id"])
    source_field_delta_s = (
        sim.radio.toa_s_for_bytes(
            first_r.packet.wire_size_bytes(sim.radio.payload_bytes) + 6
        ) - sim.radio.packet_toa_s(first_r.packet)
    )
    relay_data = Packet(
        kind="DATA", flow_id=8, origin=0, final_dst=2, ttl=3,
        created_at=4.0, protocol=sim.protocol.name, request_id=8,
        path=(0, 1, 2), repair_index=4,
    )
    reverse_ack = Packet(
        kind="ACK", flow_id=8, origin=2, final_dst=0, ttl=3,
        created_at=4.0, protocol=sim.protocol.name, request_id=8,
        path=(0, 1, 2), app_payload=False, repair_index=4,
    )
    expected_half_slack = 34.0 - (
        first_r.end + source_field_delta_s + 0.5
        + sim.radio.packet_toa_s(relay_data)
        + 2 * sim.radio.packet_toa_s(reverse_ack)
    )
    expected_guard_slack = first_r.start + 15.0 - (
        first_r.end + source_field_delta_s + 0.5
        + sim.radio.packet_toa_s(relay_data)
        + 2 * sim.radio.packet_toa_s(reverse_ack)
    )

    assert math.isclose(row["nominal_source_ack_slack_0_5_s"], expected_half_slack)
    assert math.isclose(row["nominal_f_guard_slack_0_5_s"], expected_guard_slack)
    assert row["nominal_before_f_guard_0_5_s"] is True
    assert math.isclose(
        row["nominal_source_ack_slack_0_5_s"]
        - row["nominal_source_ack_slack_2_s"], 1.5,
    )
    for key in (
        "oracle_collision_free_relay_to_dst_prr_0_5_s",
        "oracle_collision_free_dst_to_relay_ack_prr_0_5_s",
        "oracle_collision_free_relay_to_src_ack_prr_0_5_s",
        "oracle_collision_free_round_trip_prr_0_5_s",
    ):
        assert 0.0 <= row[key] <= 1.0
    assert math.isclose(
        row["oracle_collision_free_round_trip_prr_0_5_s"],
        row["oracle_collision_free_relay_to_dst_prr_0_5_s"]
        * row["oracle_collision_free_dst_to_relay_ack_prr_0_5_s"]
        * row["oracle_collision_free_relay_to_src_ack_prr_0_5_s"],
    )


def test_field_bytes_and_nominal_relay_airtime_are_charged_by_packet_toa():
    sim = jammed_primary_fixture(cutoff_s=40.0)
    row, = [row for row in analyze_backup_exposure(sim) if row["flow_id"] == 8]
    f_ack_txs = [tx for tx in sim.tx_history
                 if tx.packet.kind == "ACK" and tx.packet.flow_id == 7
                 and tx.packet.path == (0, 2)]
    r_tx = next(tx for tx in sim.tx_history if tx.tx_id == row["r_tx_id"])
    expected_f_ack_delta = sum(
        sim.radio.toa_s_for_bytes(
            tx.packet.wire_size_bytes(sim.radio.payload_bytes) + 2
        ) - sim.radio.packet_toa_s(tx.packet)
        for tx in f_ack_txs
    )
    expected_r_delta = sim.radio.toa_s_for_bytes(
        r_tx.packet.wire_size_bytes(sim.radio.payload_bytes) + 6
    ) - sim.radio.packet_toa_s(r_tx.packet)

    assert row["f_ack_relay_field_min_wire_bytes"] == 2 * len(f_ack_txs)
    assert math.isclose(row["f_ack_relay_field_min_extra_toa_s"],
                        expected_f_ack_delta)
    assert row["r_nomination_min_wire_bytes"] == 6
    assert math.isclose(row["r_nomination_min_extra_toa_s"], expected_r_delta)
    assert row["nominal_relay_would_start_0_5_s"] is True
    assert row["nominal_relay_data_airtime_0_5_s"] > 0.0
    assert row["nominal_success_reverse_ack_airtime_0_5_s"] > 0.0
    assert row["nominal_redundant_relay_data_airtime_0_5_s"] == 0.0


def test_unused_f_candidate_still_charges_its_ack_field():
    sim = PassiveBackupSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0), Node(2, 20.0, 0.0)],
        RadioConfig(sf=7, tx_power_dbm=17.0, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(flood_base_delay_s=0.2, flood_jitter_s=0.0),
        seed=73, max_hops=3, independent_random_streams=True,
    )
    sim.schedule(0.1, "app_send", (0, 2, 7))
    sim.run(4.0)

    epoch, = analyze_candidate_epochs(sim)
    assert epoch["flow_id"] == 7
    assert epoch["primary_path"] == (0, 2)
    assert epoch["backup_path"] == (0, 1, 2)
    assert epoch["source_commit_accepted"] is True
    assert epoch["f_ack_relay_field_min_wire_bytes"] == 2
    assert epoch["f_ack_relay_field_min_extra_toa_s"] >= 0.0
    assert analyze_backup_exposure(sim) == []


def test_candidate_without_observed_ack_tx_has_unassessable_not_zero_cost():
    sim = PassiveBackupSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0), Node(2, 20.0, 0.0)],
        RadioConfig(sf=7, tx_power_dbm=17.0, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(flood_base_delay_s=0.2, flood_jitter_s=0.0),
        seed=73, max_hops=3, independent_random_streams=True,
    )
    sim.schedule(0.1, "app_send", (0, 2, 7))
    sim.run(1.0)

    epoch, = analyze_candidate_epochs(sim)
    assert epoch["source_commit_accepted"] is False
    assert epoch["f_ack_cost_assessable"] is False
    assert epoch["f_ack_relay_field_min_wire_bytes"] is None
    assert epoch["f_ack_relay_field_min_extra_toa_s"] is None


def test_cohort_keeps_reliability_ceiling_separate_from_cost_substitution():
    sim = jammed_primary_fixture(cutoff_s=40.0)
    summary = summarize_backup_cohort([{
        "seed": 73,
        "flows": [{"flow_id": 7}, {"flow_id": 8}],
        "rows": analyze_backup_exposure(sim),
        "candidate_epochs": analyze_candidate_epochs(sim),
    }])

    assert summary["scheduled_unicast_flows"] == 2
    assert summary["candidate_f_epochs"] == 2
    assert summary["f_ack_min_wire_bytes_known"] == 4
    primary = summary["by_wait"]["2_s"]
    sensitivity = summary["by_wait"]["0_5_s"]
    assert primary["failed_primary_relay_decode_le_120_s"] == 1
    assert primary["source_ack_headroom_proxy_count"] == 0
    assert primary["source_ack_headroom_ceiling_fraction"] == 0.0
    assert primary["nominal_cost_substitution_eligible_count"] == 1
    assert primary["stock_f_recovery_airtime_eligible_s"] > 0.0
    assert primary["candidate_nominal_success_added_airtime_s"] > 0.0
    assert sensitivity["nominal_cost_substitution_eligible_count"] == 1


def test_optimistic_margin_charges_ack_only_to_credited_rescues():
    sim = jammed_primary_fixture(cutoff_s=40.0)
    rescued, = analyze_backup_exposure(sim)
    redundant = deepcopy(rescued)
    redundant["flow_id"] = 9
    redundant["destination_decoded_current_r"] = True
    redundant["stock_f_recovery_tx_airtime_s"] = 0.0
    redundant["nominal_cost_substitution_eligible_0_5_s"] = False
    redundant["nominal_cost_substitution_eligible_2_s"] = False
    redundant["nominal_redundant_relay_start_0_5_s"] = True
    redundant["nominal_redundant_relay_start_2_s"] = True
    summary = summarize_backup_cohort([{
        "seed": 73,
        "flows": [{"flow_id": 7}, {"flow_id": 8}, {"flow_id": 9}],
        "rows": [rescued, redundant],
        "candidate_epochs": analyze_candidate_epochs(sim),
    }])["by_wait"]["2_s"]

    credited_ack = rescued["relay_success_reverse_ack_min_toa_s"]
    assert math.isclose(summary["nominal_credited_reverse_ack_airtime_s"],
                        credited_ack)
    assert math.isclose(summary["nominal_success_reverse_ack_airtime_s"],
                        2 * credited_ack)
    assert math.isclose(
        summary["candidate_nominal_all_start_success_added_airtime_s"]
        - summary["candidate_nominal_optimistic_added_airtime_s"],
        credited_ack,
    )
    assert math.isclose(
        summary["optimistic_cost_substitution_margin_s"],
        summary["stock_f_recovery_airtime_eligible_s"]
        - summary["candidate_nominal_optimistic_added_airtime_s"],
    )


def test_backup_marker_bytes_cross_lora_toa_steps_for_data_and_ack():
    sim = two_path_fixture(PassiveBackupSimulator, sf=8)
    row, = analyze_backup_exposure(sim)
    unmarked_data = Packet(
        kind="DATA", flow_id=8, origin=0, final_dst=2, ttl=3,
        created_at=4.0, protocol=sim.protocol.name, request_id=8,
        path=(0, 1, 2), path_index=1,
    )
    unmarked_ack = Packet(
        kind="ACK", flow_id=8, origin=2, final_dst=0, ttl=3,
        created_at=4.0, protocol=sim.protocol.name, request_id=8,
        path=(0, 1, 2), path_index=1, app_payload=False,
    )

    assert row["relay_data_min_wire_bytes"] == 51
    assert row["relay_success_reverse_ack_min_wire_bytes"] == 2 * 19
    assert math.isclose(row["relay_data_min_toa_s"],
                        sim.radio.toa_s_for_bytes(51))
    assert math.isclose(row["relay_success_reverse_ack_min_toa_s"],
                        2 * sim.radio.toa_s_for_bytes(19))
    assert row["relay_data_min_toa_s"] > sim.radio.packet_toa_s(unmarked_data)
    assert row["relay_success_reverse_ack_min_toa_s"] > (
        2 * sim.radio.packet_toa_s(unmarked_ack)
    )


def test_alternate_decoded_after_two_second_close_is_not_nominated():
    sim = PassiveBackupSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0), Node(2, 20.0, 0.0)],
        RadioConfig(sf=7, tx_power_dbm=17.0, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(flood_base_delay_s=3.0, flood_jitter_s=0.0),
        seed=73, max_hops=3, independent_random_streams=True,
    )
    sim.schedule(0.1, "app_send", (0, 2, 7))
    sim.schedule(5.0, "app_send", (0, 2, 8))
    sim.run(8.0)

    paths = [item for item in sim.flood_decodes if item.flow_id == 7]
    assert {item.path for item in paths} >= {(0, 2), (0, 1, 2)}
    assert max(item.decoded_at_s for item in paths) > min(
        item.decoded_at_s for item in paths
    ) + 2.0
    assert sim.protocol.flow_actions[8] == "R"
    assert analyze_backup_exposure(sim) == []


def test_later_accepted_discovery_commit_invalidates_old_f_backup_generation():
    sim = PassiveBackupSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0), Node(2, 20.0, 0.0)],
        RadioConfig(sf=7, tx_power_dbm=17.0, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(flood_base_delay_s=0.2, flood_jitter_s=0.0),
        seed=73, max_hops=3, independent_random_streams=True,
    )
    for when, flow_id in ((0.1, 7), (4.0, 8), (200.0, 9), (210.0, 10)):
        sim.schedule(when, "app_send", (0, 2, flow_id))
    sim.run(230.0)

    assert sim.protocol.flow_actions[9] == "D"
    assert sim.protocol.flow_actions[10] == "R"
    assert any(event["event"] == "commit" and event["flow_id"] == 9
               and event["action"] == "D"
               for event in sim.protocol.action_events)
    assert [row["flow_id"] for row in analyze_backup_exposure(sim)] == [8]
