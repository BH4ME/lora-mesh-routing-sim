from __future__ import annotations

from lora_mesh_sim import (
    DRC_MAX_PENDING_FALLBACKS_PER_NODE,
    EVENT_PRIORITY,
    Node,
    Packet,
    PendingSend,
    RadioConfig,
    RxInfo,
    Simulator,
    build_protocol,
)


def _line_sim(protocol_name: str = "meshecho-drc"):
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


def test_drc_is_an_independent_protocol_identity():
    protocol, _ = _line_sim()

    assert protocol.name == "meshecho-drc"
    assert protocol.__class__.__name__ == "MeshEchoDRC"
    assert not isinstance(protocol, type(build_protocol("meshecho-sr")))


def test_drc_re_evaluates_initial_action_at_physical_start():
    protocol, sim = _line_sim()
    sim.schedule(1.0, "app_send", (0, 1, 1))
    sim.nodes[0].tx_available_at = 40.0

    sim.run(45.0)

    flow = sim.metrics.flows[1]
    assert flow.acked_at is None
    assert protocol.action_events[0]["event"] == "decision"
    assert protocol.action_events[0]["time"] >= 40.0
    assert protocol.action_events[0]["reason"] == "deadline-infeasible"
    assert sim.transmissions == []


def test_drc_censors_a_request_whose_physical_start_is_exactly_at_deadline():
    protocol, sim = _line_sim()
    sim.schedule(1.0, "app_send", (0, 1, 1))
    # The application deadline is 1 + 30 s.  Queue availability at exactly
    # that instant must not create a physical packet start.
    sim.nodes[0].tx_available_at = 31.0

    sim.run(40.0)

    assert sim.transmissions == []
    flow = sim.metrics.flows[1]
    assert flow.acked_at is None
    decisions = [event for event in protocol.action_events if event["event"] == "decision"]
    assert decisions
    assert decisions[0]["time"] == 31.0
    assert decisions[0]["reason"] == "deadline-infeasible"


def test_drc_equal_time_event_priority_contract_is_explicit():
    assert EVENT_PRIORITY["tx_end"] < EVENT_PRIORITY["protocol_timer"]
    assert EVENT_PRIORITY["protocol_timer"] == EVENT_PRIORITY["app_send"]
    assert EVENT_PRIORITY["tx_request"] > EVENT_PRIORITY["protocol_timer"]


def test_drc_learns_a_flood_route_then_reserves_a_route_attempt():
    protocol, sim = _line_sim()
    sim.schedule(1.0, "app_send", (0, 1, 1))
    sim.schedule(3.0, "app_send", (0, 1, 2))

    metrics = sim.run(20.0)

    assert metrics.flows[1].acked_at is not None
    assert metrics.flows[2].acked_at is not None
    decisions = [
        event["action"] for event in protocol.action_events
        if event["event"] == "decision"
    ]
    assert decisions == ["F_INITIAL", "R_RESERVED"]
    assert metrics.route_requests == 0
    assert metrics.route_replies == 0


def test_drc_reserves_one_marked_flood_recovery_after_route_miss():
    class DropInitialRouteData(Simulator):
        def try_receive(self, tx, receiver):
            if tx.packet.flow_id == 2 and tx.packet.kind == "DATA":
                return None
            return super().try_receive(tx, receiver)

    protocol = build_protocol("meshecho-drc")
    sim = DropInitialRouteData(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
        seed=17, max_hops=3, independent_random_streams=True,
    )
    sim.schedule(1.0, "app_send", (0, 1, 1))
    sim.schedule(3.0, "app_send", (0, 1, 2))

    metrics = sim.run(20.0)

    assert metrics.flows[2].acked_at is not None
    assert metrics.flows[2].acked_at <= 33.0
    recovery = [
        event for event in protocol.action_events
        if event.get("event") == "recovery-start" and event["flow_id"] == 2
    ]
    assert len(recovery) == 1
    assert recovery[0]["repair_index"] == 2
    accepted = [
        event for event in protocol.action_events
        if event.get("event") == "ack-accept" and event["flow_id"] == 2
    ]
    assert accepted[0]["repair_index"] == 2


def test_drc_rejects_an_ack_with_a_sender_that_is_not_the_encoded_next_hop():
    protocol, sim = _line_sim()
    sim.schedule(1.0, "app_send", (0, 1, 1))
    sim.run(1.01)

    fake_ack = Packet(
        kind="ACK", flow_id=1, origin=1, final_dst=0, ttl=3,
        created_at=1.0, protocol=protocol.name, request_id=1,
        path=(0, 1), path_index=0, app_payload=False,
    )
    protocol.on_receive(
        0, fake_ack,
        RxInfo(sender=99, rx_power_dbm=0.0, snr_db=0.0, sinr_db=0.0,
               collided=False),
    )

    assert sim.metrics.flows[1].acked_at is None


def test_drc_applies_the_eight_active_flow_capacity_at_enqueue():
    protocol, sim = _line_sim()
    for flow_id in range(1, 10):
        sim.schedule(1.0, "app_send", (0, 1, flow_id))

    sim.run(1.01)

    drops = [
        event for event in protocol.action_events
        if event.get("reason") == "state-capacity-drop"
    ]
    assert len(drops) == 1
    assert drops[0]["flow_id"] == 9


def test_drc_flood_delay_is_keyed_to_packet_context_not_shared_rng_order():
    protocol_a, sim_a = _line_sim()
    protocol_b, sim_b = _line_sim()
    packet = Packet(
        kind="FLOOD", flow_id=7, origin=0, final_dst=1, ttl=3,
        created_at=1.0, protocol="meshecho-drc", request_id=7,
        path=(0,), repair_index=None,
    )
    rx = RxInfo(
        sender=0, rx_power_dbm=-90.0, snr_db=8.0, sinr_db=8.0,
        collided=False, tx_id=1, attempt_id=1,
    )

    # A control arm can consume a different number of unrelated draws.  The
    # same packet/receiver context must still get the same forwarding jitter.
    for _ in range(37):
        sim_b.random.random()
    first = protocol_a._flood_delay(1, rx, packet)
    second = protocol_b._flood_delay(1, rx, packet)
    assert second == first


def test_drc_pending_relay_state_is_bounded_and_evicts_old_requests():
    protocol, sim = _line_sim()
    pending = []
    for index in range(DRC_MAX_PENDING_FALLBACKS_PER_NODE + 3):
        handle = PendingSend()
        pending.append(handle)
        protocol._store_pending_fallback(1, ("FLOOD", 0, index, index, None), handle)

    retained = [key for key in protocol.pending_fallback if key[0] == 1]
    assert len(retained) == DRC_MAX_PENDING_FALLBACKS_PER_NODE
    assert all(handle.canceled for handle in pending[:3])
    assert any(event.get("event") == "state-eviction"
               for event in protocol.action_events)
