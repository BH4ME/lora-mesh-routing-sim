from __future__ import annotations

from lora_mesh_sim import Node, RadioConfig, Simulator, build_protocol


def _sim(protocol_name: str = "meshecho-drc"):
    protocol = build_protocol(protocol_name)
    sim = Simulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        protocol,
        seed=29,
        max_hops=3,
        independent_random_streams=True,
    )
    return protocol, sim


def test_started_request_has_one_to_one_physical_tx_record():
    _, sim = _sim()
    sim.schedule(1.0, "app_send", (0, 1, 1))

    sim.run(10.0)

    started = [record for record in sim.tx_requests if record["status"] == "started"]
    assert started
    assert all(record["tx_id"] is not None for record in started)
    assert all(record["start"] >= record["requested_at"] for record in started)
    assert all(record["end"] > record["start"] for record in started)
    assert len({record["request_id"] for record in started}) == len(started)


def test_protocol_no_start_is_recorded_without_a_phantom_transmission():
    protocol, sim = _sim()
    sim.nodes[0].tx_available_at = 40.0
    sim.schedule(1.0, "app_send", (0, 1, 1))

    sim.run(45.0)

    no_start = [
        record for record in sim.tx_requests
        if record["packet_kind"] == "DRC_REQUEST"
    ]
    assert len(no_start) == 1
    assert no_start[0]["status"] == "protocol-no-start"
    assert no_start[0]["tx_id"] is None
    assert sim.metrics.tx_count == 0
