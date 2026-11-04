import unittest

from lora_mesh_sim import Packet, Transmission
from tools.run_sr_experiment import summarize_windowed_transmissions


class DelayedAckRepeatRunnerTest(unittest.TestCase):
    def test_repeat_control_is_counted_in_dhr_recovery_and_ack_buckets(self):
        protocol = "meshecho-dhr-flood-ack-delay-repeat"
        flood = Packet(
            "FLOOD", 1, 0, 2, 6, 0.0, protocol,
            request_id=1, path=(0,), repair_index=2,
        )
        ack = Packet(
            "ACK", 1, 2, 0, 6, 1.0, protocol,
            request_id=1, path=(0, 1, 2), path_index=1,
            app_payload=False, repair_index=2,
        )
        transmissions = [
            Transmission(1, 0, flood, 0.0, 0.5),
            Transmission(2, 2, ack, 1.0, 1.5),
            Transmission(3, 2, ack, 2.0, 2.5),
        ]

        summary = summarize_windowed_transmissions(transmissions, cutoff_s=3.0)

        self.assertEqual(summary["windowed_dhr_recovery_f_source_tx"], 1)
        self.assertEqual(summary["windowed_dhr_flood_ack_tx"], 2)
        self.assertEqual(summary["windowed_ack_tx"], 2)


if __name__ == "__main__":
    unittest.main()
