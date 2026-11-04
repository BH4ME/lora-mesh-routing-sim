from __future__ import annotations

from lora_mesh_sim import Node, RadioConfig, RouteEntry, Simulator, build_protocol


def line_sim(protocol_name: str):
    protocol = build_protocol(protocol_name)
    sim = Simulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        protocol,
        seed=17,
        max_hops=3,
        independent_random_streams=True,
        matched_rreq_timing=True,
    )
    return protocol, sim


def test_ugr_is_registered_as_a_distinct_mesh_echo_core():
    protocol = build_protocol("meshecho-ugr")

    assert protocol.name == "meshecho-ugr"
    assert protocol.__class__.__name__ == "MeshEchoUGR"


def test_ugr_confirms_a_flood_then_reuses_a_healthy_route():
    protocol, sim = line_sim("meshecho-ugr")
    sim.schedule(1.0, "app_send", (0, 1, 1))
    sim.schedule(3.0, "app_send", (0, 1, 2))

    metrics = sim.run(20.0)

    assert metrics.flows[1].acked_at is not None
    assert metrics.flows[2].acked_at is not None
    assert [event["action"] for event in protocol.action_events
            if event["event"] == "decision"] == ["F", "R"]


def test_ugr_uses_discovery_only_when_feedback_posterior_justifies_it():
    protocol, sim = line_sim("meshecho-ugr")
    protocol.bind(sim)
    # The integration fixture must make discovery cost comparable to flood
    # cost; otherwise the production deadline/cost gate correctly rejects D.
    sim.max_hops = 12
    protocol.route_cache[0][1] = RouteEntry(
        created_at=0.0, expires_at=600.0, path=(0, 1), confidence=1.0,
    )
    state = protocol.source_state(0, 1)
    state.utility_attempts.update({"R": 10, "F": 10, "D": 8})
    state.utility_acks.update({"R": 2, "F": 8, "D": 8})
    state.acked_margins_q[:] = [-5]
    state.last_ack_at = 400.0
    state.send_times[:] = [400.0, 401.0]
    protocol.source_app_counts[0] = 9
    sim.now = 480.0
    sim.schedule(480.0, "app_send", (0, 1, 1))

    sim.run(480.0)

    assert protocol.flow_actions[1] == "D"
