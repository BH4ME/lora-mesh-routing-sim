import unittest

from lora_mesh_sim import (
    MeshCoreLike,
    MeshEcho,
    Node,
    Packet,
    RadioConfig,
    RouteEntry,
    Simulator,
)


class PacketAirtimeTest(unittest.TestCase):
    def test_route_growth_increases_serialized_request_size(self) -> None:
        request = Packet(
            kind="RREQ",
            flow_id=7,
            origin=0,
            final_dst=3,
            ttl=4,
            created_at=0.0,
            protocol="meshecho",
            request_id=7,
            path=(0,),
            app_payload=False,
        )

        self.assertEqual(request.wire_size_bytes(32), 18)
        self.assertEqual(request.append_path(1).wire_size_bytes(32), 20)

    def test_control_and_data_frames_charge_only_fields_on_the_wire(self) -> None:
        common = dict(
            flow_id=7,
            origin=0,
            final_dst=3,
            ttl=4,
            created_at=0.0,
            protocol="meshecho",
            path=(0, 1, 3),
        )
        ack = Packet(kind="ACK", app_payload=False, **common)
        request = Packet(kind="RREQ", request_id=7, app_payload=False, **common)
        reply = Packet(
            kind="RREP",
            request_id=7,
            app_payload=False,
            path=(3, 1, 0),
            learned_path=(0, 1, 3),
            **{key: value for key, value in common.items() if key != "path"},
        )
        data = Packet(kind="DATA", **common)
        fallback = Packet(kind="FALLBACK", **common)
        flood = Packet(kind="FLOOD", **common)

        self.assertEqual(ack.wire_size_bytes(32), 18)
        self.assertEqual(request.wire_size_bytes(32), 22)
        self.assertEqual(
            Packet(kind="RREQ", request_id=7, path_confidence=0.5,
                   app_payload=False, **common).wire_size_bytes(32),
            23,
        )
        self.assertEqual(reply.wire_size_bytes(32), 22)
        self.assertEqual(data.wire_size_bytes(32), 50)
        self.assertEqual(fallback.wire_size_bytes(32), 50)
        self.assertEqual(flood.wire_size_bytes(32), 50)

    def test_ack_backup_path_is_charged_and_survives_reverse_forwarding(self) -> None:
        common = dict(
            kind="ACK", flow_id=7, origin=3, final_dst=0, ttl=4,
            created_at=0.0, protocol="meshecho-dbr", request_id=7,
            path=(0, 1, 3), path_index=1, app_payload=False,
        )
        plain = Packet(**common)
        with_backup = Packet(alternate_path=(0, 2, 3), **common)

        self.assertEqual(with_backup.wire_size_bytes(32),
                         plain.wire_size_bytes(32) + 7)
        self.assertEqual(with_backup.retreat_path().alternate_path, (0, 2, 3))
        self.assertEqual(with_backup.with_ttl(3).alternate_path, (0, 2, 3))
        radio = RadioConfig(sf=7)
        self.assertGreater(radio.packet_toa_s(with_backup),
                           radio.packet_toa_s(plain))

    def test_certified_backup_fields_are_charged_on_the_wire(self) -> None:
        common = dict(
            kind="DATA", flow_id=7, origin=0, final_dst=3, ttl=4,
            created_at=0.0, protocol="meshecho-dcb", path=(0, 3),
        )
        plain = Packet(**common)
        nominee = Packet(backup_relay_id=2, **common)
        epoch = Packet(backup_epoch_id=1, **common)
        both = Packet(backup_relay_id=2, backup_epoch_id=1, **common)

        self.assertEqual(nominee.wire_size_bytes(32), plain.wire_size_bytes(32) + 3)
        self.assertEqual(epoch.wire_size_bytes(32), plain.wire_size_bytes(32) + 5)
        self.assertEqual(both.wire_size_bytes(32), plain.wire_size_bytes(32) + 7)

    def test_certified_backup_fields_survive_packet_path_transforms(self) -> None:
        packet = Packet(
            kind="ACK", flow_id=7, origin=3, final_dst=0, ttl=4,
            created_at=0.0, protocol="meshecho-dcb", path=(0, 2, 3),
            path_index=1, app_payload=False,
            backup_relay_id=2, backup_epoch_id=1,
        )

        for transformed in (
            packet.with_ttl(3), packet.append_path(4),
            packet.advance_path(), packet.retreat_path(),
        ):
            self.assertEqual(transformed.backup_relay_id, 2)
            self.assertEqual(transformed.backup_epoch_id, 1)

    def test_certified_backup_fields_reject_values_outside_wire_width(self) -> None:
        common = dict(
            kind="DATA", flow_id=7, origin=0, final_dst=3, ttl=4,
            created_at=0.0, protocol="meshecho-dcb", path=(0, 3),
        )
        for value in (-1, 65536):
            with self.subTest(relay=value), self.assertRaises(ValueError):
                Packet(backup_relay_id=value, **common)
        for value in (-1, 2**32):
            with self.subTest(epoch=value), self.assertRaises(ValueError):
                Packet(backup_epoch_id=value, **common)

    def test_frame_lengths_drive_airtime_and_radio_energy(self) -> None:
        radio = RadioConfig(sf=9, payload_bytes=32, shadow_sigma_db=0.0)
        common = dict(
            flow_id=7,
            origin=0,
            final_dst=1,
            ttl=3,
            created_at=0.0,
            protocol="meshcore",
        )
        ack = Packet(kind="ACK", app_payload=False, **common)
        data = Packet(kind="DATA", **common)

        def transmit(packet):
            sim = Simulator(
                [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
                radio,
                MeshCoreLike(),
                seed=1,
                max_hops=3,
            )
            sim.transmit_later(0, packet, delay_s=0.0)
            metrics = sim.run(3.0)
            tx = sim.transmissions[0]
            return tx.end - tx.start, metrics

        ack_duration, ack_metrics = transmit(ack)
        data_duration, data_metrics = transmit(data)
        self.assertLess(ack_duration, data_duration)
        for duration, metrics in (
            (ack_duration, ack_metrics),
            (data_duration, data_metrics),
        ):
            self.assertAlmostEqual(metrics.total_airtime_s, duration)
            self.assertAlmostEqual(
                metrics.tx_energy_j,
                radio.supply_voltage_v * radio.tx_current_ma / 1000.0 * duration,
            )
            self.assertAlmostEqual(
                metrics.rx_energy_j,
                radio.supply_voltage_v * radio.rx_current_ma / 1000.0 * duration,
            )

    def test_short_interferer_still_collides_with_long_packet(self) -> None:
        class ObservedSimulator(Simulator):
            long_rx = object()

            def try_receive(self, tx, receiver):
                result = super().try_receive(tx, receiver)
                if tx.sender == 0 and tx.packet.flow_id == 1 and receiver == 2:
                    self.long_rx = result
                return result

        sim = ObservedSimulator(
            [Node(0, 0.0, 0.0), Node(1, 0.0, 1.0), Node(2, 1.0, 0.0)],
            RadioConfig(sf=9, payload_bytes=32, shadow_sigma_db=0.0),
            MeshCoreLike(),
            seed=1,
            max_hops=50,
        )
        long_data = Packet(
            kind="DATA", flow_id=1, origin=0, final_dst=2, ttl=50,
            created_at=0.0, protocol="meshcore", path=(0,) + tuple(range(10, 59)),
        )
        short_ack = Packet(
            kind="ACK", flow_id=2, origin=1, final_dst=2, ttl=3,
            created_at=0.0, protocol="meshcore", app_payload=False,
        )
        sim.transmit_later(0, long_data, delay_s=0.0)
        sim.transmit_later(1, short_ack, delay_s=0.01)

        sim.run(2.0)
        self.assertIsNone(sim.long_rx)

    def test_fallback_wait_uses_source_routed_data_airtime(self) -> None:
        protocol = MeshEcho(
            fallback_confidence_threshold=0.9,
            fallback_delay_margin_s=0.1,
        )
        radio = RadioConfig(payload_bytes=32)
        sim = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 1.0, 0.0), Node(2, 2.0, 0.0)],
            radio,
            protocol,
            seed=1,
            max_hops=3,
        )
        sim.metrics.register_flow(7, 0, 2, 0.0)
        route = RouteEntry(0.0, 600.0, (0, 1, 2), 0.2)

        protocol.send_data_on_path(0, 2, 7, route)

        data = next(event[3][1] for event in sim.events if event[3][1].kind == "DATA")
        fallback_at = next(
            event[0] for event in sim.events if event[3][1].kind == "FALLBACK"
        )
        self.assertAlmostEqual(fallback_at, 2 * radio.packet_toa_s(data) + 0.1)


if __name__ == "__main__":
    unittest.main()
