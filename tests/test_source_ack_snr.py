"""Behavioral checks for passive source-side ACK measurements."""

from dataclasses import asdict, replace
from unittest.mock import Mock

import pytest

from lora_mesh_sim import MeshEchoDHRDelayedAck, Node, Packet, RadioConfig, RouteEntry
from tools.run_sr_experiment import RecordingSimulator, SrCase
from tools.diagnose_source_ack_snr import (
    PassiveSourceAckSimulator, build_initial_r_cohort,
    join_source_ack_actions, run_diagnostic,
)
from tools import diagnose_source_ack_snr as ack_diagnostic


def run_direct(simulator_type):
    sim = simulator_type(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(), seed=1, max_hops=3,
        independent_random_streams=True,
    )
    packet = Packet(
        kind="FLOOD", flow_id=7, origin=0, final_dst=1, ttl=3,
        created_at=0.0, protocol=sim.protocol.name, request_id=7,
        path=(0,), app_payload=True,
    )
    sim.metrics.register_flow(7, 0, 1, 0.0)
    sim.protocol.seen_floods[0].add(packet.flood_key)
    sim.transmit_later(0, packet, 0.0)
    sim.run(5.0)
    return sim


class DropInitialRAck(PassiveSourceAckSimulator):
    def try_receive(self, tx, receiver):
        if (receiver == 0 and tx.packet.kind == "ACK"
                and tx.packet.flow_id == 8
                and tx.packet.repair_index is None):
            return None
        return super().try_receive(tx, receiver)


def test_source_ack_snr_capture_is_passive():
    stock = run_direct(RecordingSimulator)
    observed = run_direct(PassiveSourceAckSimulator)

    assert [asdict(tx) for tx in observed.tx_history] == [
        asdict(tx) for tx in stock.tx_history
    ]
    assert vars(observed.metrics) == vars(stock.metrics)
    assert observed.random.getstate() == stock.random.getstate()
    assert observed.channel_random.getstate() == stock.channel_random.getstate()
    ack = next(tx for tx in observed.tx_history if tx.packet.kind == "ACK")
    assert observed.source_ack_rxinfo[(ack.tx_id, 0)].sender == ack.sender
    assert isinstance(observed.source_ack_rxinfo[(ack.tx_id, 0)].snr_db, float)


def test_accepted_source_ack_joins_its_unique_physical_receive():
    sim = PassiveSourceAckSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(), seed=1, max_hops=3,
        independent_random_streams=True,
    )
    sim.schedule(0.0, "app_send", (0, 1, 7))
    sim.run(5.0)

    rows = join_source_ack_actions(sim)

    assert len(rows) == 1
    ack = next(tx for tx in sim.tx_history if tx.packet.kind == "ACK")
    assert rows[0]["tx_id"] == ack.tx_id
    assert rows[0]["accepted"] is True
    assert rows[0]["source"] == 0
    assert rows[0]["destination"] == 1
    assert rows[0]["path"] == [0, 1]
    assert rows[0]["snr_db"] == sim.source_ack_rxinfo[(ack.tx_id, 0)].snr_db
    commit_order = next(index for index, item in
                        enumerate(sim.protocol.action_events)
                        if item["event"] == "commit")
    assert rows[0]["action_order"] > commit_order


def test_off_index_source_ack_decode_stays_rejected():
    sim = PassiveSourceAckSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(), seed=1, max_hops=3,
        independent_random_streams=True,
    )
    sim.metrics.register_flow(7, 0, 1, 0.0)
    sim.protocol.flow_actions[7] = "F"
    sim.protocol.flow_data_actions[7] = "F"
    ack = Packet(
        kind="ACK", flow_id=7, origin=1, final_dst=0, ttl=3,
        created_at=0.0, protocol=sim.protocol.name, request_id=7,
        path=(0, 1), path_index=1, app_payload=False,
    )
    sim.transmit_later(1, ack, 0.0)
    sim.run(1.0)

    rows = join_source_ack_actions(sim)

    assert len(rows) == 1
    assert rows[0]["accepted"] is False
    assert rows[0]["path_index"] == 1
    assert sim.metrics.flows[7].acked_at is None


def test_ambiguous_source_ack_action_is_not_silently_matched():
    sim = run_direct(PassiveSourceAckSimulator)
    action = next(item for item in sim.protocol.action_events
                  if item["event"] == "dhr_source_ack_rx")
    sim.protocol.action_events.append(dict(action))

    with pytest.raises(ValueError, match="no unique action"):
        join_source_ack_actions(sim)


def test_initial_r_row_uses_only_prior_ack_in_current_route_generation():
    sim = PassiveSourceAckSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(), seed=1, max_hops=3,
        independent_random_streams=True,
    )
    sim.schedule(0.0, "app_send", (0, 1, 7))
    sim.schedule(5.0, "app_send", (0, 1, 8))
    sim.run(25.0)
    acknowledgments = join_source_ack_actions(sim)

    cohort = build_initial_r_cohort(sim, acknowledgments)

    assert cohort["exclusions"] == []
    assert len(cohort["rows"]) == 1
    row = cohort["rows"][0]
    prior_ack = next(ack for ack in acknowledgments if ack["flow_id"] == 7)
    assert row["flow_id"] == 8
    assert row["path"] == [0, 1]
    assert row["prior_ack_tx_id"] == prior_ack["tx_id"]
    assert row["prior_ack_age_s"] > 0
    assert row["q"] is not None
    assert row["initial_r_ack_by_guard"] is True
    assert row["route_generation_flow_id"] == 7


def test_full_diagnostic_has_stock_parity_and_strict_replay():
    case = SrCase(
        key="ack_quality_fixture", nodes=4, area_m=500.0,
        duration_s=45.0, rate_per_min=8.0, pair_mode="random",
        pair_count=0, max_hops=3, shadow_sigma_db=0.0,
        temporal_fading_sigma_db=0.0,
    )

    result = run_diagnostic(seed=73, case=case)

    assert result["parity"]["exact"] is True
    assert result["strict_replay_exact"] is True
    assert len(result["flows"]) == result["row"]["scheduled_unicast_flows"]
    assert result["protocol"] == "meshecho-dhr-flood-ack-delay"


@pytest.mark.parametrize("seed", (
    35000, 35099, 36000, 36099, 42000, 42999, 43000, 43999,
))
def test_direct_diagnostic_blocks_research_seeds_before_capture(
    monkeypatch, seed,
):
    capture = Mock(side_effect=AssertionError("reserved seed reached simulation"))
    monkeypatch.setattr(ack_diagnostic, "capture_run", capture)

    with pytest.raises(ValueError, match="reserved research seed"):
        run_diagnostic(seed)

    capture.assert_not_called()


def test_boolean_research_authorization_cannot_open_reserved_seed(monkeypatch):
    capture = Mock(side_effect=AssertionError("reserved seed reached simulation"))
    monkeypatch.setattr(ack_diagnostic, "capture_run", capture)

    with pytest.raises(ValueError, match="reserved research seed"):
        run_diagnostic(43000, research_authorization=True)

    capture.assert_not_called()


def test_runner_capability_reaches_mock_capture_only(monkeypatch):
    capture = Mock(side_effect=RuntimeError("mock capture reached"))
    monkeypatch.setattr(ack_diagnostic, "capture_run", capture)

    with pytest.raises(RuntimeError, match="mock capture reached"):
        run_diagnostic(
            43000, research_authorization=ack_diagnostic._RUNNER_AUTHORIZATION,
        )

    capture.assert_called_once()
    assert capture.call_args.args[1] == 43000


def test_late_initial_r_ack_is_not_a_guard_success():
    class DelayedRResponse(MeshEchoDHRDelayedAck):
        def reverse_ack_delay_s(self, packet):
            return 16.0 if packet.kind == "DATA" else super().reverse_ack_delay_s(packet)

    sim = PassiveSourceAckSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        DelayedRResponse(), seed=1, max_hops=3,
        independent_random_streams=True,
    )
    sim.schedule(0.0, "app_send", (0, 1, 7))
    sim.schedule(5.0, "app_send", (0, 1, 8))
    sim.run(30.0)

    rows = build_initial_r_cohort(sim, join_source_ack_actions(sim))["rows"]

    assert len(rows) == 1
    assert rows[0]["flow_id"] == 8
    assert rows[0]["initial_r_ack_by_guard"] is False
    assert sim.metrics.flows[8].acked_at is not None
    assert sim.metrics.flows[8].acked_at > rows[0]["initial_r_start_s"] + 15.0


def test_later_recovery_requires_physical_attempt_and_accepted_ack():
    sim = DropInitialRAck(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(), seed=1, max_hops=3,
        independent_random_streams=True,
    )
    sim.schedule(0.0, "app_send", (0, 1, 7))
    sim.schedule(5.0, "app_send", (0, 1, 8))
    sim.run(40.0)
    acknowledgments = join_source_ack_actions(sim)

    row = build_initial_r_cohort(sim, acknowledgments)["rows"][0]

    assert row["flow_id"] == 8
    assert row["initial_r_ack_by_guard"] is False
    assert any(action["event"] == "dhr_recovery_tx"
               and action["flow_id"] == 8 for action in sim.protocol.action_events)
    assert any(tx.packet.kind == "FLOOD" and tx.packet.repair_index == 2
               and tx.sender == 0 and tx.packet.flow_id == 8
               for tx in sim.tx_history)
    assert any(ack["accepted"] and ack["repair_index"] == 2
               and ack["flow_id"] == 8 for ack in acknowledgments)
    assert row["later_recovery_attempted"] is True
    assert row["later_recovery_ack_by_deadline"] is True


def test_recovery_actions_cannot_reuse_one_physical_tx():
    sim = DropInitialRAck(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(), seed=1, max_hops=3,
        independent_random_streams=True,
    )
    sim.schedule(0.0, "app_send", (0, 1, 7))
    sim.schedule(5.0, "app_send", (0, 1, 8))
    sim.run(40.0)
    acknowledgments = join_source_ack_actions(sim)
    action = next(action for action in sim.protocol.action_events
                  if action["event"] == "dhr_recovery_tx"
                  and action["flow_id"] == 8)
    tx = next(tx for tx in sim.tx_history
              if tx.packet.flow_id == 8 and tx.packet.repair_index == 2
              and tx.sender == 0)
    sim.protocol.action_events.append(dict(action))
    sim.tx_history.append(replace(
        tx, tx_id=max(item.tx_id for item in sim.tx_history) + 1,
        start=tx.start + 1.0, end=tx.end + 1.0,
    ))

    with pytest.raises(ValueError, match="no unique physical TX"):
        build_initial_r_cohort(sim, acknowledgments)


def test_timeout_without_physical_recovery_keeps_full_r_row():
    protocol = MeshEchoDHRDelayedAck()
    protocol.app_deadline_s = 17.0
    sim = DropInitialRAck(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        protocol, seed=1, max_hops=3,
        independent_random_streams=True,
    )
    sim.schedule(0.0, "app_send", (0, 1, 7))
    sim.schedule(5.0, "app_send", (0, 1, 8))
    sim.run(30.0)

    row = build_initial_r_cohort(sim, join_source_ack_actions(sim))["rows"][0]

    assert row["flow_id"] == 8
    assert row["initial_r_ack_by_guard"] is False
    assert any(action["event"] == "dhr_guard" and action["flow_id"] == 8
               and not action["admitted"] for action in sim.protocol.action_events)
    assert not any(action["event"] == "dhr_recovery_tx"
                   and action["flow_id"] == 8 for action in sim.protocol.action_events)
    assert row["later_recovery_attempted"] is False
    assert row["later_recovery_ack_by_deadline"] is False


def test_recovery_ack_decoded_after_deadline_is_not_a_success():
    class LateRecoveryAck(MeshEchoDHRDelayedAck):
        def reverse_ack_delay_s(self, packet):
            if packet.kind == "FLOOD" and packet.flow_id == 8:
                return 16.0
            return super().reverse_ack_delay_s(packet)

    sim = DropInitialRAck(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        LateRecoveryAck(), seed=1, max_hops=3,
        independent_random_streams=True,
    )
    sim.schedule(0.0, "app_send", (0, 1, 7))
    sim.schedule(5.0, "app_send", (0, 1, 8))
    sim.run(55.0)
    acknowledgments = join_source_ack_actions(sim)

    row = build_initial_r_cohort(sim, acknowledgments)["rows"][0]
    late_ack = next(ack for ack in acknowledgments
                    if ack["flow_id"] == 8 and ack["repair_index"] == 2)

    assert late_ack["tx_end_s"] > 35.0
    assert late_ack["accepted"] is False
    assert row["later_recovery_attempted"] is True
    assert row["later_recovery_ack_by_deadline"] is False


def test_old_generation_late_r_ack_cannot_replace_new_commit_ack():
    class DelayedRResponse(MeshEchoDHRDelayedAck):
        def reverse_ack_delay_s(self, packet):
            return 16.0 if packet.kind == "DATA" else super().reverse_ack_delay_s(packet)

    sim = PassiveSourceAckSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        DelayedRResponse(), seed=1, max_hops=3,
        independent_random_streams=True,
    )
    sim.schedule(0.0, "app_send", (0, 1, 7))
    sim.schedule(5.0, "app_send", (0, 1, 8))
    sim.schedule(9.0, "protocol_timer", lambda: setattr(
        sim.protocol.destination_state[(0, 1)], "consecutive_r_misses", 2
    ))
    sim.schedule(10.0, "app_send", (0, 1, 9))
    sim.schedule(23.0, "app_send", (0, 1, 10))
    sim.run(30.0)
    acknowledgments = join_source_ack_actions(sim)

    cohort = build_initial_r_cohort(sim, acknowledgments)

    assert sim.protocol.flow_actions[9] == "F"
    assert sim.protocol.flow_actions[10] == "R"
    old_ack = next(ack for ack in acknowledgments
                   if ack["flow_id"] == 8 and ack["accepted"])
    new_ack = next(ack for ack in acknowledgments
                   if ack["flow_id"] == 9 and ack["accepted"])
    assert old_ack["tx_end_s"] > new_ack["tx_end_s"]
    flow10 = next(row for row in cohort["rows"] if row["flow_id"] == 10)
    assert flow10["route_generation_flow_id"] == 9
    assert flow10["prior_ack_tx_id"] == new_ack["tx_id"]


def test_recommit_while_r_is_queued_preserves_full_denominator():
    sim = PassiveSourceAckSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(), seed=1, max_hops=3,
        independent_random_streams=True,
    )
    sim.schedule(0.0, "app_send", (0, 1, 7))
    sim.schedule(4.9, "protocol_timer", lambda: setattr(
        sim.nodes[0], "tx_available_at", 8.0
    ))
    sim.schedule(5.0, "app_send", (0, 1, 8))

    def recommit_same_path():
        sim.metrics.register_flow(9, 0, 1, 5.5)
        sim.protocol.flow_actions[9] = "F"
        sim.protocol.flow_data_actions[9] = "F"
        packet = Packet(
            kind="ACK", flow_id=9, origin=1, final_dst=0, ttl=3,
            created_at=5.5, protocol=sim.protocol.name, request_id=9,
            path=(0, 1), path_index=0, app_payload=False,
        )
        sim.transmit_later(1, packet, 0.0)

    sim.schedule(6.0, "protocol_timer", recommit_same_path)
    sim.run(15.0)

    cohort = build_initial_r_cohort(sim, join_source_ack_actions(sim))

    flow8 = next(row for row in cohort["rows"] if row["flow_id"] == 8)
    assert flow8["initial_r_start_s"] >= 8.0
    assert flow8["route_generation_flow_id"] == 7
    assert flow8["q"] is None
    assert flow8["feature_exclusion_reason"] == "route_commit_before_tx"


def test_uncommitted_candidate_route_keeps_initial_r_in_denominator():
    sim = PassiveSourceAckSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(), seed=1, max_hops=3,
        independent_random_streams=True,
    )
    sim.protocol.route_cache[0][1] = RouteEntry(
        created_at=0.0, expires_at=600.0, path=(0, 1), confidence=1.0,
    )
    sim.schedule(0.0, "app_send", (0, 1, 7))
    sim.run(5.0)

    cohort = build_initial_r_cohort(sim, join_source_ack_actions(sim))

    assert cohort["exclusions"] == []
    assert len(cohort["rows"]) == 1
    row = cohort["rows"][0]
    assert row["flow_id"] == 7
    assert row["initial_r_ack_by_guard"] is True
    assert row["later_recovery_attempted"] is False
    assert row["later_recovery_ack_by_deadline"] is False
    assert row["q"] is None
    assert row["feature_exclusion_reason"] == "no_prior_commit"


def test_duplicate_initial_decisions_are_rejected():
    sim = PassiveSourceAckSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(), seed=1, max_hops=3,
        independent_random_streams=True,
    )
    sim.schedule(0.0, "app_send", (0, 1, 7))
    sim.schedule(5.0, "app_send", (0, 1, 8))
    sim.run(10.0)
    decisions = [event for event in sim.protocol.action_events
                 if event["event"] == "decision" and event["flow_id"] == 8]
    sim.protocol.action_events.append(dict(decisions[0]))

    with pytest.raises(ValueError, match="duplicate initial decision"):
        build_initial_r_cohort(sim, join_source_ack_actions(sim))


def test_prior_r_miss_uses_only_timeout_visible_before_decision():
    class DelayedRResponse(MeshEchoDHRDelayedAck):
        def reverse_ack_delay_s(self, packet):
            return 16.0 if packet.kind == "DATA" else super().reverse_ack_delay_s(packet)

    sim = PassiveSourceAckSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        DelayedRResponse(), seed=1, max_hops=3,
        independent_random_streams=True,
    )
    sim.schedule(0.0, "app_send", (0, 1, 7))
    sim.schedule(5.0, "app_send", (0, 1, 8))
    sim.schedule(20.5, "app_send", (0, 1, 9))
    sim.run(30.0)

    cohort = build_initial_r_cohort(sim, join_source_ack_actions(sim))

    flow9 = next(row for row in cohort["rows"] if row["flow_id"] == 9)
    assert flow9["prior_r_miss"] == 1
    assert flow9["prior_ack_tx_id"] == next(
        ack["tx_id"] for ack in join_source_ack_actions(sim)
        if ack["flow_id"] == 7 and ack["accepted"]
    )


def test_r_ack_at_exact_guard_is_counted_before_timeout():
    class GuardBoundaryResponse(MeshEchoDHRDelayedAck):
        def reverse_ack_delay_s(self, packet):
            if packet.kind != "DATA":
                return super().reverse_ack_delay_s(packet)
            ack = replace(
                packet, kind="ACK", origin=packet.final_dst,
                final_dst=packet.origin, path_index=packet.path_index - 1,
                app_payload=False,
            )
            return (15.0 - self.sim.radio.packet_toa_s(packet)
                    - self.sim.radio.packet_toa_s(ack))

    sim = PassiveSourceAckSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        GuardBoundaryResponse(), seed=1, max_hops=3,
        independent_random_streams=True,
    )
    sim.schedule(0.0, "app_send", (0, 1, 7))
    sim.schedule(5.0, "app_send", (0, 1, 8))
    sim.run(25.0)

    row = next(item for item in build_initial_r_cohort(
        sim, join_source_ack_actions(sim),
    )["rows"] if item["flow_id"] == 8)
    ack = next(item for item in sim.tx_history
               if item.packet.kind == "ACK" and item.packet.flow_id == 8)

    assert abs(ack.end - (row["initial_r_start_s"] + 15.0)) <= 1e-7
    assert row["initial_r_ack_by_guard"] is True
    assert not any(item["event"] == "timeout" and item["flow_id"] == 8
                   for item in sim.protocol.action_events)
