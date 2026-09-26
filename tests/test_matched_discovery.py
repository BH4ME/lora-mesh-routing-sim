import unittest

from lora_mesh_sim import (
    MeshCoreLike,
    MeshEcho,
    MetricMesh,
    MinHopMesh,
    Node,
    Packet,
    RadioConfig,
    Simulator,
)


class DiamondSimulator(Simulator):
    EDGES = {
        frozenset((0, 1)),
        frozenset((0, 2)),
        frozenset((1, 3)),
        frozenset((2, 3)),
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rreq_tx_times = []

    def begin_transmission(self, sender, packet, pending):
        super().begin_transmission(sender, packet, pending)
        if packet.kind == "RREQ" and not pending.canceled:
            self.rreq_tx_times.append((sender, self.transmissions[-1].start))

    def try_receive(self, tx, receiver):
        if frozenset((tx.sender, receiver)) not in self.EDGES:
            return None
        return super().try_receive(tx, receiver)


class MatchedDiscoveryTest(unittest.TestCase):
    def test_native_rreq_timing_remains_the_default(self) -> None:
        for protocol_type in (MeshCoreLike, MeshEcho):
            def relay_times(matched):
                protocol = protocol_type(discovery_window_s=2.0)
                kwargs = {} if matched is None else {"matched_rreq_timing": matched}
                sim = DiamondSimulator(
                    [
                        Node(0, 0.0, 0.0),
                        Node(1, 1000.0, 1000.0),
                        Node(2, 1000.0, -1000.0),
                        Node(3, 2000.0, 0.0),
                    ],
                    RadioConfig(sf=7, shadow_sigma_db=0.0),
                    protocol,
                    seed=31,
                    max_hops=3,
                    independent_random_streams=True,
                    **kwargs,
                )
                sim.schedule(0.1, "app_send", (0, 3, 1))
                sim.run(3.0)
                return tuple(
                    (sender, start)
                    for sender, start in sim.rreq_tx_times
                    if sender in (1, 2)
                )

            native = relay_times(None)
            self.assertEqual(native, relay_times(False))
            self.assertNotEqual(native, relay_times(True))

    def test_late_rreq_cannot_reopen_closed_discovery(self) -> None:
        for protocol in (
            MeshCoreLike(discovery_window_s=0.05),
            MeshEcho(
                discovery_window_s=0.05,
                route_miss_recovery_enabled=False,
            ),
            MetricMesh("etx", discovery_window_s=0.05),
        ):
            nodes = [
                Node(0, 0.0, 0.0),
                Node(1, 1000.0, 1000.0),
                Node(2, 1000.0, -1000.0),
                Node(3, 2000.0, 0.0),
            ]
            sim = DiamondSimulator(
                nodes,
                RadioConfig(sf=7, shadow_sigma_db=0.0),
                protocol,
                seed=31,
                max_hops=3,
                independent_random_streams=True,
                matched_rreq_timing=True,
            )
            sim.schedule(0.1, "app_send", (0, 3, 1))
            metrics = sim.run(3.0)

            self.assertEqual(len(protocol.discovery_records), 1, protocol.name)
            record = protocol.discovery_records[0]
            self.assertEqual(record.candidate_paths, ())
            self.assertIsNone(record.selected_path)
            self.assertEqual(protocol.rreq_candidates, {})
            self.assertEqual(metrics.route_replies, 0)

    def test_first_discovery_exposes_same_candidate_paths_to_all_policies(self) -> None:
        candidates = []
        for protocol in (
            MeshCoreLike(discovery_window_s=2.0),
            MeshEcho(discovery_window_s=2.0),
            MetricMesh("etx", discovery_window_s=2.0),
            MetricMesh("ett", discovery_window_s=2.0),
            MinHopMesh(discovery_window_s=2.0),
        ):
            nodes = [
                Node(0, 0.0, 0.0),
                Node(1, 1000.0, 1000.0),
                Node(2, 1000.0, -1000.0),
                Node(3, 2000.0, 0.0),
            ]
            sim = DiamondSimulator(
                nodes,
                RadioConfig(sf=7, shadow_sigma_db=0.0),
                protocol,
                seed=31,
                max_hops=3,
                independent_random_streams=True,
                matched_rreq_timing=True,
            )
            sim.schedule(0.1, "app_send", (0, 3, 1))
            sim.run(3.0)
            self.assertEqual(len(protocol.discovery_records), 1, protocol.name)
            record = protocol.discovery_records[0]
            self.assertEqual(record.key, (0, 3, 1))
            self.assertAlmostEqual(record.started_at, 0.1)
            self.assertAlmostEqual(record.closed_at, 2.1)
            self.assertIn(record.selected_path, record.candidate_paths)
            candidates.append(record.candidate_paths)

        self.assertEqual(
            candidates,
            [((0, 1, 3), (0, 2, 3))] * len(candidates),
        )

    def test_rreq_delay_is_stable_across_protocols_and_event_order(self) -> None:
        nodes = [Node(0, 0.0, 0.0), Node(1, 1.0, 0.0)]
        packet = Packet(
            kind="RREQ",
            flow_id=7,
            origin=0,
            final_dst=1,
            ttl=3,
            created_at=0.0,
            protocol="meshecho",
            request_id=7,
            path=(0,),
        )
        first = Simulator(
            nodes,
            RadioConfig(),
            MeshEcho(),
            seed=31,
            max_hops=3,
            matched_rreq_timing=True,
        )
        second = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 1.0, 0.0)],
            RadioConfig(),
            MeshCoreLike(),
            seed=31,
            max_hops=3,
            matched_rreq_timing=True,
        )

        expected = first.rreq_forward_delay(packet, 1)
        first.random.random()
        second.random.random()
        second.random.random()
        self.assertEqual(expected, first.rreq_forward_delay(packet, 1))
        self.assertEqual(expected, second.rreq_forward_delay(packet, 1))
        self.assertNotEqual(expected, second.rreq_forward_delay(packet, 0))


if __name__ == "__main__":
    unittest.main()
