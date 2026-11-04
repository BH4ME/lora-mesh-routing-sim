import unittest
from dataclasses import replace

from lora_mesh_sim import Node, Packet, RadioConfig, Simulator, build_protocol


class MeshEchoCLARTest(unittest.TestCase):
    def run_direct_with_candidate(
        self, protocol_name, drop_initial_ack_at_source=False,
        drop_done_at_candidate=False, duplicate_initial_ack=False,
        second_flow_at=None,
    ):
        class TraceSimulator(Simulator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.sent = []
                self.duplicated_ack = False

            def begin_transmission(self, sender, packet, pending):
                before = self.metrics.tx_count
                super().begin_transmission(sender, packet, pending)
                if self.metrics.tx_count > before:
                    self.sent.append((sender, packet))
                    if (duplicate_initial_ack and not self.duplicated_ack
                            and sender == 1 and packet.kind == "ACK"
                            and packet.repair_index == 255):
                        self.duplicated_ack = True
                        self.transmit_later(sender, packet, delay_s=1.0)

            def try_receive(self, tx, receiver):
                if (drop_initial_ack_at_source and tx.packet.kind == "ACK"
                        and tx.packet.repair_index == 255
                        and tx.sender == 1 and receiver == 0):
                    return None
                if (drop_done_at_candidate and tx.packet.kind == "ACK_DONE"
                        and receiver == 2):
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol(protocol_name)
        protocol.flood_delay = lambda receiver=None, rx=None: (
            10.0 if receiver == 2 else 0.1
        )
        sim = TraceSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0),
             Node(2, 5.0, 10.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 1, 1))
        if second_flow_at is not None:
            sim.schedule(second_flow_at, "app_send", (0, 1, 2))
        metrics = sim.run(max(3.0, (second_flow_at or 0.0) + 2.0))
        return metrics, sim.sent, protocol

    def run_multihop_with_candidate(self, protocol_name):
        class TraceSimulator(Simulator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.sent = []

            def begin_transmission(self, sender, packet, pending):
                before = self.metrics.tx_count
                super().begin_transmission(sender, packet, pending)
                if self.metrics.tx_count > before:
                    self.sent.append((sender, packet))

            def try_receive(self, tx, receiver):
                if tx.packet.kind == "FLOOD" and (tx.sender, receiver) in {
                    (0, 2), (0, 3), (2, 3),
                }:
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol(protocol_name)
        protocol.flood_delay = lambda receiver=None, rx=None: (
            10.0 if receiver == 2 else 0.1
        )
        sim = TraceSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0),
             Node(2, 150.0, 100.0), Node(3, 200.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        metrics = sim.run(3.0)
        return metrics, sim.sent, protocol

    def test_source_closure_suppresses_locally_observed_repair(self):
        metrics, sent, _ = self.run_direct_with_candidate("meshecho-clar")

        self.assertIsNotNone(metrics.flows[1].acked_at)
        self.assertEqual(
            [(sender, packet.kind) for sender, packet in sent
             if packet.kind == "ACK_DONE"],
            [(0, "ACK_DONE")],
        )
        self.assertFalse(any(sender == 2 and packet.kind == "ACK"
                             for sender, packet in sent))

    def test_candidate_repairs_lost_direct_ack(self):
        metrics, sent, _ = self.run_direct_with_candidate(
            "meshecho-clar", drop_initial_ack_at_source=True,
        )

        self.assertIsNotNone(metrics.flows[1].acked_at)
        self.assertEqual(
            [packet.repair_index for sender, packet in sent
             if sender == 2 and packet.kind == "ACK"],
            [0],
        )
        self.assertEqual(
            sum(packet.kind == "ACK_DONE" for _, packet in sent), 1,
        )

    def test_lost_source_closure_does_not_cancel_candidate(self):
        metrics, sent, _ = self.run_direct_with_candidate(
            "meshecho-clar", drop_done_at_candidate=True,
        )

        self.assertIsNotNone(metrics.flows[1].acked_at)
        self.assertEqual(
            [packet.repair_index for sender, packet in sent
             if sender == 2 and packet.kind == "ACK"],
            [0],
        )

    def test_same_beacon_without_cancellation_keeps_repair(self):
        metrics, sent, _ = self.run_direct_with_candidate(
            "meshecho-clar-nocancel",
        )

        self.assertIsNotNone(metrics.flows[1].acked_at)
        self.assertEqual(
            sum(packet.kind == "ACK_DONE" for _, packet in sent), 1,
        )
        self.assertEqual(
            [packet.repair_index for sender, packet in sent
             if sender == 2 and packet.kind == "ACK"],
            [0],
        )

    def test_plain_single_ack_control_has_no_repair_or_beacon(self):
        metrics, sent, _ = self.run_direct_with_candidate("meshecho-clar-fr")

        self.assertIsNotNone(metrics.flows[1].acked_at)
        self.assertEqual(
            [packet.repair_index for _, packet in sent
             if packet.kind == "ACK"],
            [255],
        )
        self.assertFalse(any(packet.kind == "ACK_DONE" for _, packet in sent))

    def test_onpath_repeat_control_rescues_one_lost_ack_copy(self):
        metrics, sent, _ = self.run_direct_with_candidate(
            "meshecho-clar-repeat", drop_initial_ack_at_source=True,
        )

        self.assertIsNotNone(metrics.flows[1].acked_at)
        self.assertEqual(
            [packet.repair_index for sender, packet in sent
             if sender == 1 and packet.kind == "ACK"],
            [255, 1],
        )
        self.assertFalse(any(sender == 2 and packet.kind == "ACK"
                             for sender, packet in sent))
        self.assertEqual(
            sum(packet.kind == "ACK_DONE" for _, packet in sent), 1,
        )

    def test_source_ack_event_marks_first_acceptance(self):
        metrics, _, protocol = self.run_direct_with_candidate(
            "meshecho-clar", drop_initial_ack_at_source=True,
        )

        self.assertIsNotNone(metrics.flows[1].acked_at)
        receptions = [event for event in protocol.action_events
                      if event["event"] == "clar_source_ack_rx"]
        self.assertEqual(len(receptions), 1)
        self.assertEqual(
            (receptions[0]["accepted"], receptions[0]["repair_index"],
             receptions[0]["on_path"]),
            (True, 0, True),
        )

    def test_duplicate_ack_does_not_emit_second_done(self):
        metrics, sent, protocol = self.run_direct_with_candidate(
            "meshecho-clar", duplicate_initial_ack=True,
        )

        self.assertIsNotNone(metrics.flows[1].acked_at)
        self.assertEqual(
            sum(packet.kind == "ACK_DONE" for _, packet in sent), 1,
        )
        self.assertEqual(
            [event["accepted"] for event in protocol.action_events
             if event["event"] == "clar_source_ack_rx"],
            [True, False],
        )

    def test_confirmed_route_flow_does_not_emit_done(self):
        metrics, sent, protocol = self.run_direct_with_candidate(
            "meshecho-clar", second_flow_at=2.0,
        )

        self.assertIsNotNone(metrics.flows[2].acked_at)
        self.assertTrue(any(
            event["event"] == "decision" and event["flow_id"] == 2
            and event["action"] == "R"
            for event in protocol.action_events
        ))
        self.assertEqual(
            [packet.flow_id for _, packet in sent
             if packet.kind == "ACK_DONE"],
            [1],
        )

    def test_source_done_cancels_terminal_onpath_repeat(self):
        metrics, sent, protocol = self.run_direct_with_candidate(
            "meshecho-clar-repeat",
        )

        self.assertIsNotNone(metrics.flows[1].acked_at)
        self.assertEqual(
            [packet.repair_index for sender, packet in sent
             if sender == 1 and packet.kind == "ACK"],
            [255],
        )
        self.assertTrue(any(
            event["event"] == "clar_cancel"
            and event["reason"] == "source-done-repeat"
            for event in protocol.action_events
        ))

    def test_unforwardable_ack_does_not_block_later_valid_copy(self):
        class LowTtlFirstAck(Simulator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.duplicated = False
                self.forwarded_from_one = 0

            def try_receive(self, tx, receiver):
                if (tx.packet.kind == "FLOOD" and tx.sender == 0
                        and receiver == 3):
                    return None
                return super().try_receive(tx, receiver)

            def begin_transmission(self, sender, packet, pending):
                if (sender == 3 and packet.kind == "ACK"
                        and not self.duplicated):
                    self.duplicated = True
                    self.transmit_later(sender, packet, delay_s=0.3)
                    packet = replace(packet, ttl=1)
                before = self.metrics.tx_count
                super().begin_transmission(sender, packet, pending)
                if (self.metrics.tx_count > before and sender == 1
                        and packet.kind == "ACK"):
                    self.forwarded_from_one += 1

        protocol = build_protocol("meshecho-clar-fr")
        protocol.flood_delay = lambda receiver=None, rx=None: 0.1
        sim = LowTtlFirstAck(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0),
             Node(3, 200.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.schedule(1.0, "app_send", (0, 3, 1))
        metrics = sim.run(3.0)

        self.assertEqual(sim.forwarded_from_one, 1)
        self.assertIsNotNone(metrics.flows[1].acked_at)

    def test_candidate_does_not_repair_after_local_flood_observation_expires(self):
        class LateAckSimulator(Simulator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.repair_starts = 0

            def try_receive(self, tx, receiver):
                if tx.packet.kind == "FLOOD" and receiver == 3:
                    return None
                return super().try_receive(tx, receiver)

            def begin_transmission(self, sender, packet, pending):
                before = self.metrics.tx_count
                super().begin_transmission(sender, packet, pending)
                if (self.metrics.tx_count > before and sender == 2
                        and packet.kind == "ACK"):
                    self.repair_starts += 1

        protocol = build_protocol("meshecho-clar")
        protocol.flood_delay = lambda receiver=None, rx=None: 40.0
        sim = LateAckSimulator(
            [Node(0, 0.0, 0.0), Node(2, 5.0, 10.0),
             Node(3, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.transmit_later(0, Packet(
            kind="FLOOD", flow_id=1, origin=0, final_dst=3,
            ttl=6, created_at=1.0, protocol="meshecho-clar",
            request_id=1, path=(0,), app_payload=True,
        ), delay_s=1.0)
        sim.transmit_later(3, Packet(
            kind="ACK", flow_id=1, origin=3, final_dst=0,
            ttl=6, created_at=30.8, protocol="meshecho-clar",
            request_id=1, path=(0, 3), path_index=0,
            app_payload=False, repair_index=255,
        ), delay_s=30.8)
        sim.run(32.0)

        self.assertEqual(sim.repair_starts, 0)

    def test_queued_repair_does_not_start_after_local_observation_expires(self):
        class NoDestinationFlood(Simulator):
            def try_receive(self, tx, receiver):
                if tx.packet.kind == "FLOOD" and receiver == 3:
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-clar")
        protocol.flood_delay = lambda receiver=None, rx=None: 40.0
        sim = NoDestinationFlood(
            [Node(0, 0.0, 0.0), Node(2, 5.0, 10.0),
             Node(3, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.transmit_later(0, Packet(
            kind="FLOOD", flow_id=1, origin=0, final_dst=3,
            ttl=6, created_at=1.0, protocol="meshecho-clar",
            request_id=1, path=(0,), app_payload=True,
        ), delay_s=1.0)
        sim.transmit_later(3, Packet(
            kind="ACK", flow_id=1, origin=3, final_dst=0,
            ttl=6, created_at=30.2, protocol="meshecho-clar",
            request_id=1, path=(0, 3), path_index=0,
            app_payload=False, repair_index=255,
        ), delay_s=30.2)
        for flow_id in range(100, 110):
            sim.transmit_later(2, Packet(
                kind="ACK_DONE", flow_id=flow_id, origin=2, final_dst=3,
                ttl=1, created_at=30.8, protocol="meshecho-clar",
                request_id=flow_id, app_payload=False,
            ), delay_s=30.8)
        sim.run(32.0)

        local_expiry = 1.0 + sim.radio.packet_toa_s(Packet(
            kind="FLOOD", flow_id=1, origin=0, final_dst=3,
            ttl=6, created_at=1.0, protocol="meshecho-clar",
            request_id=1, path=(0,), app_payload=True,
        )) + protocol.local_lifetime_s
        busy_ends = [event["end"] for event in protocol.action_events
                     if event["event"] == "clar_done_tx"
                     and event["src"] == 2]
        self.assertEqual(len(busy_ends), 10)
        self.assertGreater(max(busy_ends), local_expiry)
        self.assertTrue(any(event["event"] == "clar_candidate_eligible"
                            for event in protocol.action_events))
        self.assertFalse(any(event["event"] == "clar_repair_tx"
                             for event in protocol.action_events))

    def test_queued_repeat_does_not_start_after_local_ack_expires(self):
        protocol = build_protocol("meshecho-clar-repeat")
        protocol.local_lifetime_s = 0.3
        sim = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 5.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        initial_ack = Packet(
            kind="ACK", flow_id=1, origin=1, final_dst=0,
            ttl=6, created_at=1.0, protocol="meshecho-clar-repeat",
            request_id=1, path=(0, 1), path_index=0,
            app_payload=False, repair_index=255,
        )
        sim.transmit_later(1, initial_ack, delay_s=1.0)
        for flow_id in range(100, 108):
            sim.transmit_later(1, Packet(
                kind="ACK_DONE", flow_id=flow_id, origin=1, final_dst=0,
                ttl=1, created_at=1.1, protocol="meshecho-clar-repeat",
                request_id=flow_id, app_payload=False,
            ), delay_s=1.1)
        sim.run(2.0)

        local_expiry = 1.0 + sim.radio.packet_toa_s(initial_ack) + 0.3
        busy_ends = [event["end"] for event in protocol.action_events
                     if event["event"] == "clar_done_tx"
                     and event["src"] == 1]
        self.assertEqual(len(busy_ends), 8)
        self.assertGreater(max(busy_ends), local_expiry)
        self.assertFalse(any(event["event"] == "clar_repeat_tx"
                             for event in protocol.action_events))

    def test_candidate_uses_packets_without_global_flow_record(self):
        class TraceSimulator(Simulator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.sent = []

            def begin_transmission(self, sender, packet, pending):
                before = self.metrics.tx_count
                super().begin_transmission(sender, packet, pending)
                if self.metrics.tx_count > before:
                    self.sent.append((sender, packet))

            def try_receive(self, tx, receiver):
                if (tx.packet.kind == "FLOOD" and tx.sender == 0
                        and receiver == 3):
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-clar")
        protocol.flood_delay = lambda receiver=None, rx=None: 10.0
        sim = TraceSimulator(
            [Node(0, 0.0, 0.0), Node(2, 5.0, 10.0),
             Node(3, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.transmit_later(0, Packet(
            kind="FLOOD", flow_id=1, origin=0, final_dst=3,
            ttl=6, created_at=1.0, protocol="meshecho-clar",
            request_id=1, path=(0,), app_payload=True,
        ), delay_s=1.0)
        sim.transmit_later(3, Packet(
            kind="ACK", flow_id=1, origin=3, final_dst=0,
            ttl=6, created_at=1.5, protocol="meshecho-clar",
            request_id=1, path=(0, 3), path_index=0,
            app_payload=False, repair_index=255,
        ), delay_s=1.5)
        sim.run(3.0)

        self.assertFalse(sim.metrics.flows)
        self.assertEqual(
            [packet.repair_index for sender, packet in sim.sent
             if sender == 2 and packet.kind == "ACK"],
            [0],
        )

    def test_done_bytes_airtime_and_energy_are_charged(self):
        metrics, sent, _ = self.run_direct_with_candidate("meshecho-clar")
        radio = RadioConfig(sf=7, shadow_sigma_db=0.0)
        done = [packet for _, packet in sent if packet.kind == "ACK_DONE"]

        self.assertEqual(len(done), 1)
        self.assertEqual(done[0].wire_size_bytes(radio.payload_bytes), 10)
        self.assertTrue(done[0].is_control)
        self.assertEqual(metrics.control_tx, sum(
            packet.is_control for _, packet in sent
        ))
        self.assertAlmostEqual(metrics.total_airtime_s, sum(
            radio.packet_toa_s(packet) for _, packet in sent
        ))
        self.assertAlmostEqual(
            metrics.tx_energy_j,
            radio.supply_voltage_v * radio.tx_current_ma / 1000.0
            * metrics.total_airtime_s,
        )

    def test_candidate_attempt_history_is_bounded_per_node(self):
        class NoDestinationDecode(Simulator):
            def try_receive(self, tx, receiver):
                if tx.packet.kind == "FLOOD" and receiver == 100:
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-clar")
        protocol.flood_delay = lambda receiver=None, rx=None: 10.0
        protocol.relay_wait_s = 10.0
        nodes = [Node(0, 0.0, 0.0), Node(2, 5.0, 0.0),
                 Node(100, 10.0, 0.0, role="client")]
        nodes.extend(Node(sender, 5.0, 0.0, role="client")
                     for sender in range(3, 43))
        sim = NoDestinationDecode(
            nodes, RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.transmit_later(0, Packet(
            kind="FLOOD", flow_id=1, origin=0, final_dst=100,
            ttl=6, created_at=1.0, protocol="meshecho-clar",
            request_id=1, path=(0,), app_payload=True,
        ), delay_s=1.0)
        for offset, sender in enumerate(range(3, 43)):
            sim.transmit_later(sender, Packet(
                kind="ACK", flow_id=1, origin=100, final_dst=0,
                ttl=6, created_at=1.2, protocol="meshecho-clar",
                request_id=1, path=(0, sender, 100), path_index=0,
                app_payload=False, repair_index=255,
            ), delay_s=1.2 + 0.1 * offset)
        sim.run(6.0)

        self.assertLessEqual(
            sum(key[0] == 2 for key in protocol.attempted_repairs), 32,
        )

    def test_repeat_attempt_history_is_bounded_per_node(self):
        protocol = build_protocol("meshecho-clar-repeat")
        sim = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 5.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for offset, flow_id in enumerate(range(1, 41)):
            sim.transmit_later(1, Packet(
                kind="ACK", flow_id=flow_id, origin=1, final_dst=0,
                ttl=6, created_at=1.0, protocol="meshecho-clar-repeat",
                request_id=flow_id, path=(0, 1), path_index=0,
                app_payload=False, repair_index=255,
            ), delay_s=1.0 + 0.1 * offset)
        sim.run(10.0)

        self.assertLessEqual(
            sum(key[0] == 1 for key in protocol.attempted_repeats), 32,
        )

    def test_forwarded_ack_history_is_bounded_per_node(self):
        class NoDirectFlood(Simulator):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.ack_receipts = 0

            def try_receive(self, tx, receiver):
                if (tx.packet.kind == "FLOOD" and tx.sender == 0
                        and receiver == 2):
                    return None
                result = super().try_receive(tx, receiver)
                if (result is not None and tx.packet.kind == "ACK"
                        and tx.sender == 2 and receiver == 1):
                    self.ack_receipts += 1
                return result

        protocol = build_protocol("meshecho-clar")
        protocol.flood_delay = lambda receiver=None, rx=None: 10.0
        sim = NoDirectFlood(
            [Node(0, 0.0, 0.0), Node(1, 5.0, 0.0),
             Node(2, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        for offset, flow_id in enumerate(range(1, 41)):
            at = 1.0 + 0.5 * offset
            sim.transmit_later(0, Packet(
                kind="FLOOD", flow_id=flow_id, origin=0, final_dst=2,
                ttl=6, created_at=at, protocol="meshecho-clar",
                request_id=flow_id, path=(0,), app_payload=True,
            ), delay_s=at)
            sim.transmit_later(2, Packet(
                kind="ACK", flow_id=flow_id, origin=2, final_dst=0,
                ttl=6, created_at=at + 0.2, protocol="meshecho-clar",
                request_id=flow_id, path=(0, 1, 2), path_index=1,
                app_payload=False, repair_index=255,
            ), delay_s=at + 0.2)
        sim.run(23.0)

        self.assertGreaterEqual(sim.ack_receipts, 33)
        self.assertLessEqual(
            sum(key[0] == 1 for key in protocol.seen_ack_hops), 32,
        )

    def test_forwarded_ack_cancels_multihop_candidate(self):
        metrics, sent, _ = self.run_multihop_with_candidate("meshecho-clar")

        self.assertIsNotNone(metrics.flows[1].acked_at)
        self.assertFalse(any(sender == 2 and packet.kind == "ACK"
                             for sender, packet in sent))

    def test_invalid_ack_continuation_does_not_cancel_pending_repair(self):
        class DropValidContinuationAtCandidate(Simulator):
            def try_receive(self, tx, receiver):
                if tx.packet.kind == "FLOOD" and receiver == 3:
                    return None
                if (tx.packet.kind == "ACK" and tx.sender == 1
                        and receiver == 2 and tx.packet.ttl > 0):
                    return None
                return super().try_receive(tx, receiver)

        protocol = build_protocol("meshecho-clar")
        protocol.flood_delay = lambda receiver=None, rx=None: 40.0
        sim = DropValidContinuationAtCandidate(
            [Node(0, 0.0, 0.0), Node(1, 5.0, 0.0),
             Node(2, 5.0, 5.0), Node(3, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0), protocol,
            seed=17, max_hops=6, independent_random_streams=True,
        )
        sim.transmit_later(0, Packet(
            kind="FLOOD", flow_id=1, origin=0, final_dst=3,
            ttl=6, created_at=1.0, protocol="meshecho-clar",
            request_id=1, path=(0,), app_payload=True,
        ), delay_s=1.0)
        sim.transmit_later(1, Packet(
            kind="FLOOD", flow_id=1, origin=0, final_dst=3,
            ttl=5, created_at=1.5, protocol="meshecho-clar",
            request_id=1, path=(0, 1), app_payload=True,
        ), delay_s=1.5)
        initial_ack = Packet(
            kind="ACK", flow_id=1, origin=3, final_dst=0,
            ttl=6, created_at=2.0, protocol="meshecho-clar",
            request_id=1, path=(0, 1, 3), path_index=1,
            app_payload=False, repair_index=255,
        )
        sim.transmit_later(3, initial_ack, delay_s=2.0)
        sim.transmit_later(1, replace(
            initial_ack, ttl=0, path_index=0,
        ), delay_s=2.2)
        sim.run(3.0)

        self.assertTrue(any(event["event"] == "clar_candidate_eligible"
                            for event in protocol.action_events))
        self.assertFalse(any(event["event"] == "clar_cancel"
                             and event["reason"] == "ack-continuation"
                             for event in protocol.action_events))
        self.assertTrue(any(event["event"] == "clar_repair_tx"
                            for event in protocol.action_events))


if __name__ == "__main__":
    unittest.main()
