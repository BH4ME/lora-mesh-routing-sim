from __future__ import annotations

from lora_mesh_sim import Node, Packet, RadioConfig, Simulator, build_protocol


def _sim():
    protocol = build_protocol("meshecho-drc")
    return Simulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        protocol,
        seed=71,
        max_hops=3,
        independent_random_streams=True,
        record_rx_attempts=True,
    )


def test_drc_records_equal_time_application_order_and_request_wire_metadata():
    sim = _sim()
    sim.schedule(1.0, "app_send", (0, 1, 1))
    sim.schedule(1.0, "app_send", (0, 1, 2))

    sim.run(40.0)

    assert [event["ordinal"] for event in sim.application_events] == [1, 2]
    assert [event["flow_id"] for event in sim.application_events] == [1, 2]
    started = [row for row in sim.tx_requests if row["status"] == "started"]
    assert started
    assert all(row["event_ordinal"] >= 1 for row in started)
    source_requests = [
        row for row in started
        if row["sender"] == 0 and row["packet_kind"] == "DRC_REQUEST"
    ]
    assert source_requests
    assert all(row["application_ordinal"] in {1, 2} for row in source_requests)
    assert all(row["wire_request_id"] == row["flow_id"] for row in source_requests)
    assert all(isinstance(row["path"], tuple) for row in source_requests)


def test_drc_records_one_rx_attempt_for_each_receiver_with_explicit_reason():
    sim = _sim()
    sim.schedule(1.0, "app_send", (0, 1, 1))

    sim.run(40.0)

    assert sim.rx_attempts
    assert all(row["reason"] in {
        "success", "half_duplex", "capture_collision", "prr_fail", "self",
    } for row in sim.rx_attempts)
    assert all(row["tx_id"] is not None for row in sim.rx_attempts)
    assert any(row["reason"] == "success" and row["decoded"] for row in sim.rx_attempts)


def test_request_ledger_can_finalize_future_requests_without_phantom_tx():
    sim = _sim()
    sim.transmit_later(
        0,
        Packet(
            kind="DRC_REQUEST", flow_id=1, origin=0, final_dst=1, ttl=3,
            created_at=0.0, protocol="meshecho-drc", request_id=1,
            path=(0,), app_payload=False,
        ),
        delay_s=20.0,
    )

    sim.run(10.0)
    sim.finalize_request_ledger()

    rows = [row for row in sim.tx_requests if row["packet_kind"] == "DRC_REQUEST"]
    assert len(rows) == 1
    assert rows[0]["status"] == "not_processed_by_cutoff"
    assert rows[0]["tx_id"] is None
    assert sim.metrics.tx_count == 0


def test_accepted_source_ack_has_physical_tx_and_rx_provenance():
    sim = _sim()
    sim.schedule(1.0, "app_send", (0, 1, 1))

    sim.run(40.0)

    accepted = [row for row in sim.ack_provenance if row["accepted"]]
    assert accepted
    event = accepted[0]
    assert event["ack_tx_id"] is not None
    assert event["ack_rx_attempt_id"] is not None
    attempts = {
        row["rx_attempt_id"]: row for row in sim.rx_attempts
    }
    assert attempts[event["ack_rx_attempt_id"]]["reason"] == "success"
    assert attempts[event["ack_rx_attempt_id"]]["tx_id"] == event["ack_tx_id"]
    assert event["receiver"] == 0
    assert event["ack_rx_at"] == event["accepted_at"]
    assert event["deadline_at"] == sim.metrics.flows[1].created_at + 30.0
    assert event["route_generation_after"] is not None


def test_rejected_source_ack_is_recorded_with_a_reason():
    sim = _sim()
    sim.schedule(1.0, "app_send", (0, 1, 1))
    sim.run(1.01)

    from lora_mesh_sim import Packet, RxInfo

    sim.protocol.on_receive(
        0,
        Packet(
            kind="ACK", flow_id=1, origin=1, final_dst=0, ttl=3,
            created_at=1.0, protocol="meshecho-drc", request_id=1,
            path=(0, 1), path_index=0, app_payload=False,
        ),
        RxInfo(
            sender=99, rx_power_dbm=0.0, snr_db=0.0, sinr_db=0.0,
            collided=False, tx_id=77, attempt_id=88,
        ),
    )

    rejected = [row for row in sim.ack_provenance if not row["accepted"]]
    assert rejected
    assert rejected[-1]["ack_tx_id"] == 77
    assert rejected[-1]["ack_rx_attempt_id"] == 88
    assert rejected[-1]["rejection_reason"] == "path-or-sender-mismatch"
