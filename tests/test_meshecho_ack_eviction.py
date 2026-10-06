from argparse import Namespace
import unittest
from unittest.mock import patch

from lora_mesh_sim import Node, RadioConfig, RouteEntry, Simulator, build_protocol


class MeshEchoAckEvictionTest(unittest.TestCase):
    def make_unacknowledged_send(self, until_s: float):
        protocol = build_protocol("meshecho-ack-evict")
        sim = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 4000.0, 0.0)],
            RadioConfig(tx_power_dbm=0.0, path_loss_exp=4.0, shadow_sigma_db=0.0),
            protocol,
            seed=3,
            max_hops=3,
        )
        entry = RouteEntry(
            created_at=0.0,
            expires_at=100.0,
            path=(0, 1),
            confidence=0.9,
        )
        protocol.route_cache[0][1] = entry
        sim.nodes[0].tx_available_at = 10.0
        sim.schedule(0.0, "app_send", (0, 1, 1))
        sim.run(until_s)
        return sim, protocol, entry

    def test_guard_starts_at_actual_source_transmission(self) -> None:
        early_sim, early_protocol, entry = self.make_unacknowledged_send(24.9)
        self.assertIs(early_protocol.route_cache[0][1], entry)
        self.assertEqual(early_sim.metrics.data_tx, 1)

        late_sim, late_protocol, _ = self.make_unacknowledged_send(25.1)
        self.assertNotIn(1, late_protocol.route_cache[0])
        self.assertEqual(late_sim.metrics.data_tx, 1)

    def test_timeout_records_invalidation_without_retransmission(self) -> None:
        sim, _, _ = self.make_unacknowledged_send(25.1)
        summary = sim.metrics.summarize("meshecho-ack-evict", 3, 25.1)

        self.assertEqual(summary["ack_timeout_invalidations"], 1)
        self.assertEqual(summary["timeout_invalidations_after_destination_delivery"], 0)
        self.assertEqual(summary["unicast_flows"], 1)
        self.assertEqual(summary["data_tx"], 1)

    def test_confirmed_ack_preserves_cached_route(self) -> None:
        protocol = build_protocol("meshecho-ack-evict")
        sim = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(shadow_sigma_db=0.0),
            protocol,
            seed=3,
            max_hops=3,
        )
        entry = RouteEntry(0.0, 100.0, (0, 1), 0.9)
        protocol.route_cache[0][1] = entry
        sim.schedule(0.0, "app_send", (0, 1, 1))
        sim.run(30.0)

        self.assertIs(protocol.route_cache[0][1], entry)
        self.assertIsNotNone(sim.metrics.flows[1].acked_at)
        self.assertEqual(sim.metrics.ack_timeout_invalidations, 0)

    def test_old_guard_does_not_evict_a_replacement_route(self) -> None:
        protocol = build_protocol("meshecho-ack-evict")
        sim = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 4000.0, 0.0)],
            RadioConfig(tx_power_dbm=0.0, path_loss_exp=4.0, shadow_sigma_db=0.0),
            protocol,
            seed=3,
            max_hops=3,
        )
        original = RouteEntry(0.0, 100.0, (0, 1), 0.9)
        replacement = RouteEntry(12.0, 112.0, (0, 1), 0.9)
        protocol.route_cache[0][1] = original
        sim.schedule(0.0, "app_send", (0, 1, 1))
        sim.schedule(
            12.0,
            "protocol_timer",
            lambda: protocol.route_cache[0].__setitem__(1, replacement),
        )
        sim.run(26.0)

        self.assertIs(protocol.route_cache[0][1], replacement)
        self.assertEqual(sim.metrics.ack_timeout_invalidations, 0)

    def test_prr_product_can_use_the_same_ack_eviction_rule(self) -> None:
        protocol = build_protocol("prr-product-ack-evict")
        sim = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 4000.0, 0.0)],
            RadioConfig(tx_power_dbm=0.0, path_loss_exp=4.0, shadow_sigma_db=0.0),
            protocol,
            seed=3,
            max_hops=3,
        )
        protocol.route_cache[0][1] = RouteEntry(0.0, 100.0, (0, 1), 0.9)
        sim.schedule(0.0, "app_send", (0, 1, 1))
        sim.run(16.0)

        self.assertEqual(protocol.name, "prr-product-ack-evict-mesh")
        self.assertFalse(protocol.route_miss_recovery_enabled)
        self.assertNotIn(1, protocol.route_cache[0])
        self.assertEqual(sim.metrics.ack_timeout_invalidations, 1)

    def test_both_feedback_variants_respect_the_same_guard_configuration(self) -> None:
        args = Namespace(ack_guard_s=7.0)

        self.assertEqual(build_protocol("meshecho-ack-evict", args).ack_guard_s, 7.0)
        self.assertEqual(build_protocol("prr-product-ack-evict", args).ack_guard_s, 7.0)

    def test_lost_ack_after_data_delivery_is_counted_as_false_invalidation(self) -> None:
        protocol = build_protocol("meshecho-ack-evict")
        sim = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(shadow_sigma_db=0.0),
            protocol,
            seed=3,
            max_hops=3,
        )
        protocol.route_cache[0][1] = RouteEntry(0.0, 100.0, (0, 1), 0.9)
        receive = sim.try_receive

        def drop_ack(tx, receiver):
            return None if tx.packet.kind == "ACK" else receive(tx, receiver)

        sim.schedule(0.0, "app_send", (0, 1, 1))
        with patch.object(sim, "try_receive", side_effect=drop_ack):
            sim.run(16.0)

        self.assertIsNotNone(sim.metrics.flows[1].delivered_at)
        self.assertIsNone(sim.metrics.flows[1].acked_at)
        self.assertNotIn(1, protocol.route_cache[0])
        self.assertEqual(sim.metrics.ack_timeout_invalidations, 1)
        self.assertEqual(sim.metrics.timeout_invalidations_after_destination_delivery, 1)

    def test_later_ack_on_same_route_cancels_older_failure_guard(self) -> None:
        protocol = build_protocol("meshecho-ack-evict")
        sim = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(shadow_sigma_db=0.0),
            protocol,
            seed=3,
            max_hops=3,
        )
        entry = RouteEntry(0.0, 100.0, (0, 1), 0.9)
        protocol.route_cache[0][1] = entry
        receive = sim.try_receive

        def drop_first_ack(tx, receiver):
            if tx.packet.kind == "ACK" and tx.packet.flow_id == 1:
                return None
            return receive(tx, receiver)

        sim.schedule(0.0, "app_send", (0, 1, 1))
        sim.schedule(1.0, "app_send", (0, 1, 2))
        with patch.object(sim, "try_receive", side_effect=drop_first_ack):
            sim.run(17.0)

        self.assertIsNone(sim.metrics.flows[1].acked_at)
        self.assertIsNotNone(sim.metrics.flows[2].acked_at)
        self.assertIs(protocol.route_cache[0][1], entry)
        self.assertEqual(sim.metrics.ack_timeout_invalidations, 0)

    def test_delayed_older_ack_does_not_cancel_newer_failure_guard(self) -> None:
        protocol = build_protocol("meshecho-ack-evict")
        sim = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(shadow_sigma_db=0.0),
            protocol,
            seed=3,
            max_hops=3,
        )
        protocol.route_cache[0][1] = RouteEntry(0.0, 100.0, (0, 1), 0.9)
        transmit_later = sim.transmit_later
        receive = sim.try_receive

        def delay_first_ack(sender, packet, delay_s, pending=None):
            if packet.kind == "ACK" and packet.flow_id == 1:
                delay_s += 2.0
            return transmit_later(sender, packet, delay_s, pending)

        def drop_second_ack(tx, receiver):
            if tx.packet.kind == "ACK" and tx.packet.flow_id == 2:
                return None
            return receive(tx, receiver)

        sim.schedule(0.0, "app_send", (0, 1, 1))
        sim.schedule(1.0, "app_send", (0, 1, 2))
        with patch.object(sim, "transmit_later", side_effect=delay_first_ack), patch.object(
            sim, "try_receive", side_effect=drop_second_ack
        ):
            sim.run(17.0)

        self.assertIsNotNone(sim.metrics.flows[1].acked_at)
        self.assertIsNone(sim.metrics.flows[2].acked_at)
        self.assertNotIn(1, protocol.route_cache[0])
        self.assertEqual(sim.metrics.ack_timeout_invalidations, 1)


if __name__ == "__main__":
    unittest.main()
