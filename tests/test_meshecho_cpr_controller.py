"""Behavioral contract for the MeshEcho-CPR simulator protocol."""

import lora_mesh_sim
from meshecho_cpr import CprAction, CprDecision, CprFlowRecord
from lora_mesh_sim import Node, Packet, RadioConfig, RxInfo, Simulator, build_protocol


class RecordingSimulator(Simulator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tx_history = []

    def begin_transmission(self, sender, packet, pending):
        count = self.metrics.tx_count
        super().begin_transmission(sender, packet, pending)
        if self.metrics.tx_count > count:
            self.tx_history.append(self.transmissions[-1])


class DropRoutedData(RecordingSimulator):
    def try_receive(self, tx, receiver):
        if (tx.packet.flow_id == 2 and tx.packet.kind == "DATA"
                and tx.packet.repair_index in {None, 1}):
            return None
        return super().try_receive(tx, receiver)


def _line_sim(protocol_name: str = "meshecho-cpr"):
    protocol = build_protocol(protocol_name)
    sim = Simulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        protocol,
        seed=23,
        max_hops=3,
        independent_random_streams=True,
    )
    return protocol, sim


def test_cpr_is_an_independent_protocol_identity():
    protocol, sim = _line_sim()

    assert protocol.name == "meshecho-cpr"
    assert protocol.__class__.__name__ == "MeshEchoCPR"
    assert not isinstance(protocol, type(build_protocol("meshecho-sr")))
    assert sim.record_rx_attempts


def test_cpr_starts_a_repeat_before_one_recovery_flood():
    protocol = build_protocol("meshecho-cpr")
    sim = DropRoutedData(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
        seed=17, max_hops=3, independent_random_streams=True,
    )
    sim.schedule(1.0, "app_send", (0, 1, 1))
    sim.schedule(3.0, "app_send", (0, 1, 2))

    sim.run(40.0)

    source_data = [
        (tx.packet.kind, tx.packet.repair_index)
        for tx in sim.tx_history
        if tx.sender == 0 and tx.packet.flow_id == 2
    ]
    assert source_data[:3] == [("DATA", None), ("DATA", 1), ("FLOOD", 2)]
    assert sum(marker == 1 for _, marker in source_data) == 1
    assert sum(marker == 2 for _, marker in source_data) == 1


def test_cpr_ack_before_repeat_start_prevents_both_recovery_actions():
    protocol = build_protocol("meshecho-cpr")
    sim = RecordingSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
        seed=23, max_hops=3, independent_random_streams=True,
    )
    sim.schedule(1.0, "app_send", (0, 1, 1))
    sim.schedule(3.0, "app_send", (0, 1, 2))

    sim.run(10.0)

    source_data = [
        (tx.packet.kind, tx.packet.repair_index)
        for tx in sim.tx_history
        if tx.sender == 0 and tx.packet.flow_id == 2
    ]
    assert source_data == [("DATA", None)]


def _run_direct_flood(protocol_name: str):
    protocol = build_protocol(protocol_name)
    sim = RecordingSimulator(
        [
            Node(0, 0.0, 0.0),
            Node(1, 10.0, 0.0, role="router"),
            Node(2, 20.0, 0.0),
        ],
        RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
        seed=17, max_hops=4, independent_random_streams=True,
    )
    protocol.send_app(0, 2, 1)
    sim.run(3.0)
    return sim


def test_cpr_terminal_ack_cancels_an_uncommitted_initial_flood_relay():
    candidate = _run_direct_flood("meshecho-cpr")
    shadow = _run_direct_flood("meshecho-cpr-nocancel")

    assert candidate.metrics.flows[1].acked_at is not None
    assert shadow.metrics.flows[1].acked_at is not None
    assert not any(
        tx.sender == 1 and tx.packet.kind == "FLOOD"
        for tx in candidate.tx_history
    )
    assert any(
        event["event"] == "cpr-cancel" and event["relay"] == 1
        for event in candidate.protocol.action_events
    )
    assert any(
        tx.sender == 1 and tx.packet.kind == "FLOOD"
        for tx in shadow.tx_history
    )


def _run_recovery_flood(protocol_name: str):
    protocol = build_protocol(protocol_name)
    sim = DropRoutedData(
        [
            Node(0, 0.0, 0.0),
            Node(1, 10.0, 0.0, role="router"),
            Node(2, 20.0, 0.0),
        ],
        RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
        seed=17, max_hops=4, independent_random_streams=True,
    )
    sim.schedule(1.0, "app_send", (0, 2, 1))
    sim.schedule(3.0, "app_send", (0, 2, 2))
    sim.run(10.0)
    return sim


def test_cpr_terminal_ack_cancels_an_uncommitted_recovery_flood_relay():
    candidate = _run_recovery_flood("meshecho-cpr")
    shadow = _run_recovery_flood("meshecho-cpr-nocancel")

    assert candidate.metrics.flows[2].acked_at is not None
    assert shadow.metrics.flows[2].acked_at is not None
    assert any(
        tx.sender == 0 and tx.packet.repair_index == 2
        for tx in candidate.tx_history
    )
    assert not any(
        tx.sender == 1 and tx.packet.kind == "FLOOD"
        and tx.packet.repair_index == 2
        for tx in candidate.tx_history
    )
    assert any(
        tx.sender == 1 and tx.packet.kind == "FLOOD"
        and tx.packet.repair_index == 2
        for tx in shadow.tx_history
    )


class DropAllFlowTwoPayloads(RecordingSimulator):
    def try_receive(self, tx, receiver):
        if tx.packet.flow_id == 2 and tx.packet.kind in {"DATA", "FLOOD"}:
            return None
        return super().try_receive(tx, receiver)


def test_cpr_timeout_quarantines_failed_route_and_next_flow_does_not_reuse_it():
    protocol = build_protocol("meshecho-cpr")
    sim = DropAllFlowTwoPayloads(
        [
            Node(0, 0.0, 0.0),
            Node(1, 10.0, 0.0, role="router"),
            Node(2, 20.0, 0.0),
        ],
        RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
        seed=17, max_hops=4, independent_random_streams=True,
    )
    sim.schedule(1.0, "app_send", (0, 2, 1))
    sim.schedule(3.0, "app_send", (0, 2, 2))
    sim.run(34.0)

    state = protocol.flow_states[2]
    route = state.routes.get(2)
    assert route is not None
    assert route.phase.value == "QUARANTINED"
    sim.schedule(35.0, "app_send", (0, 2, 3))
    sim.run(66.0)
    flow3_decisions = [
        event for event in protocol.action_events
        if event.get("event") == "decision" and event.get("flow_id") == 3
    ]
    assert flow3_decisions
    assert flow3_decisions[0]["action"] == "F_INITIAL"


def test_cpr_recovery_ack_rejects_route_epoch_changed_by_newer_flow():
    protocol = build_protocol("meshecho-cpr")
    sim = Simulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
        seed=23, max_hops=3, independent_random_streams=True,
    )
    sim.metrics.register_flow(1, 0, 1, 0.0)
    sim.metrics.register_flow(2, 0, 1, 1.0)
    state = protocol._state(0)
    first_route = state.install_route(1, (0, 1), now=0.0, ttl_s=100.0)
    old_flow = CprFlowRecord(
        flow_id=1, source=0, destination=1, enqueue_at=0.0, deadline=30.0,
        initial_action="R", initial_path=(0, 1),
        route_generation=first_route.generation,
        initial_started_at=1.0, repeat_started_at=2.0,
        recovery_started_at=3.0,
    )
    protocol.cpr_flows[1] = old_flow
    protocol.flow_states[1] = state
    state.install_route(1, (0, 1), now=4.0, ttl_s=100.0)
    sim.now = 5.0
    packet = Packet(
        kind="ACK", flow_id=1, origin=1, final_dst=0, ttl=3,
        created_at=0.0, protocol=protocol.name, request_id=1,
        path=(0, 1), path_index=0, repair_index=2, app_payload=False,
    )
    rejection = protocol._cpr_ack_rejection_reason(
        old_flow, packet,
        RxInfo(sender=1, rx_power_dbm=0.0, snr_db=0.0,
               sinr_db=0.0, collided=False),
    )

    assert rejection == "stale-route-generation"


def test_cpr_recovery_start_uses_public_controller(monkeypatch):
    protocol = build_protocol("meshecho-cpr")
    sim = Simulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
        seed=23, max_hops=3, independent_random_streams=True,
    )
    sim.schedule(1.0, "app_send", (0, 1, 1))
    sim.schedule(3.0, "app_send", (0, 1, 2))
    original = lora_mesh_sim.choose_recovery_action

    def reject_flood(observation):
        decision = original(observation)
        if observation.repeat_started:
            return CprDecision(
                CprAction.DROP_DEADLINE_INFEASIBLE,
                "test-controller-rejection",
            )
        return decision

    monkeypatch.setattr(lora_mesh_sim, "choose_recovery_action", reject_flood)
    sim.run(40.0)

    assert not any(
        tx.packet.flow_id == 2 and tx.packet.repair_index == 2
        for tx in sim.transmissions
    )


def test_cpr_accepted_ack_provenance_records_post_commit_generation():
    sim = _run_direct_flood("meshecho-cpr")
    accepted = [row for row in sim.ack_provenance if row.get("accepted")]

    assert accepted
    assert all(row.get("route_generation_after") is not None for row in accepted)
    decisions = [
        event for event in sim.protocol.action_events
        if event.get("event") == "decision"
    ]
    assert decisions
    assert all("route_generation" in event for event in decisions)
