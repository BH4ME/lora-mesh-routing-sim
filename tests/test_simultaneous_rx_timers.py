import unittest

from lora_mesh_sim import (
    MeshCoreLike,
    MeshEcho,
    MetricMesh,
    Node,
    Packet,
    RadioConfig,
    RouteEntry,
    Simulator,
    SmartCalmMesh,
)


class RecordingSimulator(Simulator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tx_history = []

    def begin_transmission(self, sender, packet, pending):
        before = self.metrics.tx_count
        super().begin_transmission(sender, packet, pending)
        if self.metrics.tx_count > before:
            self.tx_history.append(self.transmissions[-1])


class SimultaneousReceiveTimerTest(unittest.TestCase):
    def test_rreq_received_at_collection_close_is_a_candidate(self):
        for protocol in (
            MeshCoreLike(discovery_window_s=2.0),
            MeshEcho(discovery_window_s=2.0, route_miss_recovery_enabled=False),
            MetricMesh("etx", discovery_window_s=2.0),
        ):
            with self.subTest(protocol=protocol.name):
                sim = RecordingSimulator(
                    [Node(i, i * 10.0, 0.0, role="client") for i in range(4)],
                    RadioConfig(sf=7, shadow_sigma_db=0.0),
                    protocol, seed=31, max_hops=3,
                    independent_random_streams=True,
                )
                first = Packet(
                    kind="RREQ", flow_id=9, origin=0, final_dst=3,
                    ttl=3, created_at=0.0, protocol=protocol.name,
                    request_id=9, path=(0, 1), app_payload=False,
                )
                second = Packet(
                    kind="RREQ", flow_id=9, origin=0, final_dst=3,
                    ttl=3, created_at=0.0, protocol=protocol.name,
                    request_id=9, path=(0, 2), app_payload=False,
                )
                self.assertEqual(
                    sim.radio.packet_toa_s(first),
                    sim.radio.packet_toa_s(second),
                )
                sim.transmit_later(1, first, delay_s=0.0)
                sim.run(0.1)
                first_end = next(tx.end for tx in sim.tx_history
                                 if tx.packet is first)
                close = first_end + sim.discovery_collection_window_s(2.0)
                sim.transmit_later(
                    2, second,
                    delay_s=2.0 - sim.now,
                )

                sim.run(6.0)

                second_end = next(tx.end for tx in sim.tx_history
                                  if tx.packet is second)
                self.assertEqual(second_end, close)
                self.assertEqual(len(protocol.discovery_records), 1)
                record = protocol.discovery_records[0]
                self.assertEqual(record.closed_at, close)
                self.assertEqual(
                    record.candidate_paths,
                    ((0, 1, 3), (0, 2, 3)),
                )

    def test_rrep_received_at_source_discovery_deadline_sends_queued_data(self):
        protocol = MeshCoreLike(discovery_window_s=0.0, rrep_wait_s=2.0)
        sim = RecordingSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            protocol, seed=31, max_hops=3,
            independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 9))
        sim.run(1.0)
        request = next(tx for tx in sim.tx_history
                       if tx.packet.kind == "RREQ")
        deadline = request.start + sim.route_discovery_rrep_wait_s(
            2.0, 0.0, protocol.flood_base_delay_s + protocol.flood_jitter_s,
        )
        reply = Packet(
            kind="RREP", flow_id=9, origin=1, final_dst=0,
            ttl=3, created_at=0.0, protocol=protocol.name,
            request_id=9, path=(1, 0), learned_path=(0, 1),
            app_payload=False,
        )
        sim.nodes[1].tx_available_at = deadline - sim.radio.packet_toa_s(reply)

        metrics = sim.run(4.0)

        actual_reply = next(tx for tx in sim.tx_history
                            if tx.packet.kind == "RREP")
        self.assertEqual(actual_reply.end, deadline)
        self.assertEqual(metrics.route_discovery_successes, 1)
        self.assertIsNotNone(metrics.flows[9].delivered_at)

    def test_ack_received_at_flow_timeout_counts_as_confirmed(self):
        protocol = SmartCalmMesh(
            update_interval_s=1000.0, exploration=0.0,
            flow_timeout_s=2.0, max_timeout_retries=0,
            fixed_profile_index=0,
        )
        sim = RecordingSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            protocol, seed=31, max_hops=3,
            independent_random_streams=True,
        )
        protocol.route_cache[0][1] = RouteEntry(
            created_at=0.0, expires_at=100.0,
            path=(0, 1), confidence=0.95,
        )
        sim.schedule(1.0, "app_send", (0, 1, 9))
        deadline = 3.0
        ack = Packet(
            kind="ACK", flow_id=9, origin=1, final_dst=0,
            ttl=3, created_at=0.0, protocol=protocol.name,
            path=(0, 1), app_payload=False,
        )
        sim.nodes[1].tx_available_at = deadline - sim.radio.packet_toa_s(ack)

        metrics = sim.run(4.0)

        actual_ack = next(tx for tx in sim.tx_history
                          if tx.packet.kind == "ACK")
        self.assertEqual(actual_ack.end, deadline)
        self.assertEqual(metrics.flows[9].acked_at, deadline)
        self.assertEqual(metrics.unicast_acks, 1)
        self.assertEqual(metrics.policy_update_count, 1)
        self.assertGreater(metrics.policy_reward_total, 0.0)


if __name__ == "__main__":
    unittest.main()
