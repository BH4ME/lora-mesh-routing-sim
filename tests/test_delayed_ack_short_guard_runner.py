import unittest
from dataclasses import asdict
import json

from lora_mesh_sim import Packet, Transmission
from tools.run_delayed_ack_short_guard_control import physical_cost
from tools.run_sr_experiment import summarize_windowed_transmissions


class DelayedAckShortGuardRunnerTest(unittest.TestCase):
    def test_saved_reverse_path_rrep_has_same_physical_cost_as_packet(self):
        packet = Packet(
            "RREP", 1, 2, 0, 6, 0.0, "meshecho-dhr-flood-ack-delay",
            request_id=1, path=(2, 1, 0), learned_path=(0, 1, 2),
            app_payload=False,
        )
        saved = json.loads(json.dumps({
            "tx_id": 1, "sender": 2, "start": 1.0, "end": 1.2,
            "packet": asdict(packet),
        }))

        cost = physical_cost([saved], 630.0, 32)

        self.assertEqual(cost["tx_bytes"], packet.wire_size_bytes(32))
        self.assertEqual(cost["control_bytes"], packet.wire_size_bytes(32))

    def test_short_guard_controls_count_recovery_and_ack_transmissions(self):
        for guard in (1, 2, 4, 8):
            with self.subTest(guard=guard):
                protocol = f"meshecho-dhr-flood-ack-delay-guard{guard}"
                flood = Packet(
                    "FLOOD", 1, 0, 2, 6, 0.0, protocol,
                    request_id=1, path=(0,), repair_index=2,
                )
                ack = Packet(
                    "ACK", 1, 2, 0, 6, 1.0, protocol,
                    request_id=1, path=(0, 1, 2), path_index=1,
                    app_payload=False, repair_index=2,
                )
                summary = summarize_windowed_transmissions(
                    [Transmission(1, 0, flood, 0.0, 0.5),
                     Transmission(2, 2, ack, 1.0, 1.5)],
                    cutoff_s=2.0,
                )

                self.assertEqual(summary["windowed_dhr_recovery_f_source_tx"], 1)
                self.assertEqual(summary["windowed_dhr_flood_ack_tx"], 1)
                self.assertEqual(summary["windowed_ack_tx"], 1)


if __name__ == "__main__":
    unittest.main()
