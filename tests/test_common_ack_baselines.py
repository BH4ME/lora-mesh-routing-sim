import unittest

from lora_mesh_sim import (
    MeshCoreCommonAck,
    MeshtasticCommonAck,
    Node,
    RadioConfig,
    Simulator,
    build_protocol,
)


class LineSimulator(Simulator):
    EDGES = {frozenset((0, 1)), frozenset((1, 2))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sent = []

    def begin_transmission(self, sender, packet, pending):
        super().begin_transmission(sender, packet, pending)
        if not pending.canceled:
            self.sent.append((sender, packet))

    def try_receive(self, tx, receiver):
        if frozenset((tx.sender, receiver)) not in self.EDGES:
            return None
        return super().try_receive(tx, receiver)


def line_sim(protocol):
    return LineSimulator(
        [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0), Node(2, 200.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        protocol,
        seed=1,
        max_hops=3,
        independent_random_streams=True,
    )


class LostAckLineSimulator(LineSimulator):
    drop_ack_flow = 2

    def try_receive(self, tx, receiver):
        if (
            tx.packet.kind == "ACK"
            and tx.packet.flow_id == self.drop_ack_flow
            and receiver == 0
        ):
            return None
        return super().try_receive(tx, receiver)


class CommonAckBaselineTest(unittest.TestCase):
    def test_common_ack_variants_are_buildable(self) -> None:
        self.assertIsInstance(build_protocol("meshtastic-common-ack"), MeshtasticCommonAck)
        self.assertIsInstance(build_protocol("meshcore-common-ack"), MeshCoreCommonAck)

    def test_ack_after_guard_but_before_application_deadline_confirms_route(self) -> None:
        class DelayFirstAck(LineSimulator):
            def transmit_later(self, sender, packet, delay_s, pending=None):
                if sender == 2 and packet.kind == "ACK" and packet.flow_id == 1:
                    delay_s += 16.0
                return super().transmit_later(sender, packet, delay_s, pending)

        for protocol_type in (MeshtasticCommonAck, MeshCoreCommonAck):
            with self.subTest(protocol=protocol_type.__name__):
                protocol = protocol_type(base_delay_s=0.05, jitter_s=0.0)
                sim = DelayFirstAck(
                    [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0),
                     Node(2, 200.0, 0.0)],
                    RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
                    seed=1, max_hops=3, independent_random_streams=True,
                )
                sim.schedule(0.0, "app_send", (0, 2, 1))
                sim.schedule(20.0, "app_send", (0, 2, 2))

                metrics = sim.run(40.0)

                source_data = [packet for sender, packet in sim.sent
                               if sender == 0 and packet.kind in {"DATA", "DIRECT"}]
                self.assertIsNotNone(metrics.flows[1].acked_at)
                self.assertLess(metrics.flows[1].acked_at, 30.0)
                self.assertEqual([packet.kind for packet in source_data], ["DATA", "DIRECT"])

    def test_confirmed_cache_expires_before_later_flow(self) -> None:
        for protocol_type in (MeshtasticCommonAck, MeshCoreCommonAck):
            with self.subTest(protocol=protocol_type.__name__):
                protocol = protocol_type(
                    route_ttl_s=1.0, base_delay_s=0.05, jitter_s=0.0,
                )
                sim = line_sim(protocol)
                sim.schedule(0.0, "app_send", (0, 2, 1))
                sim.schedule(5.0, "app_send", (0, 2, 2))

                sim.run(10.0)

                source_data = [packet for sender, packet in sim.sent
                               if sender == 0 and packet.kind in {"DATA", "DIRECT"}]
                self.assertEqual([packet.kind for packet in source_data], ["DATA", "DATA"])

    def test_ack_after_application_deadline_cannot_create_source_route(self) -> None:
        for protocol_type in (MeshtasticCommonAck, MeshCoreCommonAck):
            with self.subTest(protocol=protocol_type.__name__):
                protocol = protocol_type(
                    ack_guard_s=0.1, app_deadline_s=0.1,
                    base_delay_s=0.05, jitter_s=0.0,
                )
                sim = line_sim(protocol)
                sim.schedule(0.0, "app_send", (0, 2, 1))
                sim.schedule(5.0, "app_send", (0, 2, 2))

                metrics = sim.run(10.0)

                source_data = [packet for sender, packet in sim.sent
                               if sender == 0 and packet.kind in {"DATA", "DIRECT"}]
                self.assertEqual([packet.kind for packet in source_data], ["DATA", "DATA"])
                self.assertIsNone(metrics.flows[1].acked_at)

    def test_queued_data_is_not_timed_out_before_source_transmission(self) -> None:
        for protocol_type in (MeshtasticCommonAck, MeshCoreCommonAck):
            with self.subTest(protocol=protocol_type.__name__):
                protocol = protocol_type()
                sim = line_sim(protocol)
                sim.nodes[0].tx_available_at = 100.0
                sim.schedule(1.0, "app_send", (0, 2, 1))

                sim.run(40.0)

                self.assertEqual(sim.metrics.transmission_intervals[0][0], 100.0)
                self.assertNotIn(1, protocol.timed_out_flows)

    def test_destination_delivery_without_source_ack_does_not_build_cache(self) -> None:
        for protocol_type in (MeshtasticCommonAck, MeshCoreCommonAck):
            with self.subTest(protocol=protocol_type.__name__):
                protocol = protocol_type(base_delay_s=0.05, jitter_s=0.0)
                sim = LostAckLineSimulator(
                    [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0),
                     Node(2, 200.0, 0.0)],
                    RadioConfig(sf=7, shadow_sigma_db=0.0),
                    protocol,
                    seed=1,
                    max_hops=3,
                    independent_random_streams=True,
                )
                sim.drop_ack_flow = 1
                sim.schedule(0.0, "app_send", (0, 2, 1))
                sim.schedule(5.0, "app_send", (0, 2, 2))

                metrics = sim.run(10.0)

                source_data = [packet for sender, packet in sim.sent
                               if sender == 0 and packet.kind in {"DATA", "DIRECT"}]
                self.assertEqual([packet.kind for packet in source_data], ["DATA", "DATA"])
                self.assertIsNotNone(metrics.flows[1].delivered_at)
                self.assertIsNone(metrics.flows[1].acked_at)
                self.assertEqual(metrics.route_cache_hits, 0)

    def test_lost_source_ack_floods_only_the_next_flow(self) -> None:
        for protocol_type in (MeshtasticCommonAck, MeshCoreCommonAck):
            with self.subTest(protocol=protocol_type.__name__):
                protocol = protocol_type(
                    ack_guard_s=1.0, base_delay_s=0.05, jitter_s=0.0,
                )
                sim = LostAckLineSimulator(
                    [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0),
                     Node(2, 200.0, 0.0)],
                    RadioConfig(sf=7, shadow_sigma_db=0.0),
                    protocol,
                    seed=1,
                    max_hops=3,
                    independent_random_streams=True,
                )
                for when, flow_id in ((0.0, 1), (5.0, 2), (7.0, 3)):
                    sim.schedule(when, "app_send", (0, 2, flow_id))

                metrics = sim.run(10.0)

                source_data = [packet for sender, packet in sim.sent
                               if sender == 0 and packet.kind in {"DATA", "DIRECT"}]
                self.assertEqual(
                    [(packet.flow_id, packet.kind) for packet in source_data],
                    [(1, "DATA"), (2, "DIRECT"), (3, "DATA")],
                )
                self.assertIsNotNone(metrics.flows[2].delivered_at)
                self.assertIsNone(metrics.flows[2].acked_at)
                self.assertEqual(metrics.ack_timeout_invalidations, 1)
                self.assertEqual(
                    metrics.timeout_invalidations_after_destination_delivery, 1,
                )

    def test_meshtastic_learns_per_relay_next_hops(self) -> None:
        protocol = MeshtasticCommonAck(base_delay_s=0.05, jitter_s=0.0)
        sim = line_sim(protocol)
        sim.schedule(0.0, "app_send", (0, 2, 1))
        sim.schedule(5.0, "app_send", (0, 2, 2))

        metrics = sim.run(10.0)

        source_data = [packet for sender, packet in sim.sent
                       if sender == 0 and packet.kind in {"DATA", "DIRECT"}]
        relay_directed = [packet for sender, packet in sim.sent
                          if sender == 1 and packet.kind == "DIRECT"]
        self.assertEqual([packet.path for packet in source_data], [(0,), (0, 1)])
        self.assertEqual([packet.path for packet in relay_directed], [(0, 1, 2)])
        self.assertEqual(source_data[1].wire_size_bytes(32), 48)
        self.assertEqual(relay_directed[0].wire_size_bytes(32), 50)
        self.assertEqual(metrics.unicast_acks, 2)

    def test_meshcore_first_data_flood_then_confirmed_source_route(self) -> None:
        protocol = MeshCoreCommonAck(base_delay_s=0.05, jitter_s=0.0)
        sim = line_sim(protocol)
        sim.schedule(0.0, "app_send", (0, 2, 1))
        sim.schedule(5.0, "app_send", (0, 2, 2))

        metrics = sim.run(10.0)

        source_data = [packet for sender, packet in sim.sent
                       if sender == 0 and packet.kind in {"DATA", "DIRECT"}]
        self.assertEqual([packet.kind for packet in source_data], ["DATA", "DIRECT"])
        self.assertEqual([packet.path for packet in source_data], [(0,), (0, 1, 2)])
        self.assertEqual(source_data[1].wire_size_bytes(32), 50)
        self.assertEqual(metrics.unicast_acks, 2)
        self.assertEqual(metrics.route_requests, 0)
        self.assertEqual(metrics.route_replies, 0)


if __name__ == "__main__":
    unittest.main()
