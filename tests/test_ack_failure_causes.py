"""Synthetic checks for passive reverse-ACK failure classification."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from lora_mesh_sim import (
    MeshEchoDHR, Node, Packet, PendingSend, RadioConfig, Simulator, Transmission,
)
from tools.diagnose_ack_failure_causes import (
    CauseSimulator, analyze_failure_causes, classify_failed_hop, run_diagnostic,
    parse_args, run_report, seeds_for_mode, write_report,
)
from tools.run_sr_experiment import SrCase


def radio_sim() -> Simulator:
    return Simulator(
        [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0), Node(2, 100.0, 10.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0), MeshEchoDHR(rescue_mode="flood"),
        seed=1, max_hops=3,
    )


def tx(tx_id: int, sender: int, kind: str, flow_id: int,
       start: float, end: float) -> Transmission:
    packet = Packet(
        kind=kind, flow_id=flow_id, origin=sender, final_dst=0,
        ttl=3, created_at=0.0, protocol="meshecho-dhr-flood",
        request_id=flow_id, app_payload=kind == "FLOOD",
    )
    return Transmission(tx_id, sender, packet, start, end)


class AckFailureCauseTests(unittest.TestCase):
    def test_half_duplex_precedes_capture_and_records_own_transmission(self) -> None:
        sim = radio_sim()
        ack = tx(1, 1, "ACK", 9, 2.0, 2.1)
        own = tx(2, 0, "FLOOD", 9, 2.05, 2.15)
        interferer = tx(3, 2, "FLOOD", 8, 2.02, 2.12)
        sim.transmissions = [ack, own, interferer]

        self.assertIsNone(sim.try_receive(ack, 0))

        cause = classify_failed_hop(
            sim, ack, 0, [ack, own, interferer],
            {1: 2.0, 2: 2.0, 3: 2.0}, first_delivery_at_s=1.0,
        )

        self.assertEqual(cause["class"], "half_duplex")
        self.assertEqual([item["tx_id"] for item in cause["receiver_transmissions"]], [2])
        self.assertEqual([item["tx_id"] for item in cause["interfering_transmissions"]], [3])

    def test_capture_collision_uses_received_power_and_threshold(self) -> None:
        sim = radio_sim()
        ack = tx(1, 1, "ACK", 9, 2.0, 2.1)
        interferer = tx(2, 2, "FLOOD", 8, 2.02, 2.12)
        sim.transmissions = [ack, interferer]

        self.assertIsNone(sim.try_receive(ack, 0))

        cause = classify_failed_hop(
            sim, ack, 0, [ack, interferer], {1: 2.0, 2: 2.02},
            first_delivery_at_s=1.0,
        )

        self.assertEqual(cause["class"], "capture_collision")
        self.assertLess(
            cause["signal_dbm"],
            cause["interfering_transmissions"][0]["received_power_dbm"]
            + cause["capture_threshold_db"],
        )

    def test_probabilistic_classes_distinguish_weak_interference_from_none(self) -> None:
        sim = radio_sim()
        sim.nodes[2].x = 1000.0
        ack = tx(1, 1, "ACK", 9, 2.0, 2.1)
        weak = tx(2, 2, "FLOOD", 8, 2.02, 2.12)

        with_interference = classify_failed_hop(
            sim, ack, 0, [ack, weak], {1: 2.0, 2: 2.02},
            first_delivery_at_s=1.0,
        )
        without_interference = classify_failed_hop(
            sim, ack, 0, [ack], {1: 2.0}, first_delivery_at_s=1.0,
        )

        self.assertEqual(with_interference["class"], "probabilistic_with_interference")
        self.assertEqual(without_interference["class"], "probabilistic_no_interference")
        self.assertFalse(without_interference["interfering_transmissions"])

    def test_strict_intent_bound_uses_commit_time_not_later_physical_start(self) -> None:
        sim = radio_sim()
        ack = tx(1, 1, "ACK", 9, 1.30, 1.40)
        flood = tx(2, 2, "FLOOD", 9, 1.32, 1.42)

        late_commit = classify_failed_hop(
            sim, ack, 0, [ack, flood], {1: 1.30, 2: 1.06},
            first_delivery_at_s=1.0,
        )
        early_commit = classify_failed_hop(
            sim, ack, 0, [ack, flood], {1: 1.30, 2: 1.03},
            first_delivery_at_s=1.0,
        )

        self.assertEqual(late_commit["class"], "capture_collision")
        self.assertTrue(late_commit["sole_same_flow_post_delivery_flood"])
        self.assertTrue(late_commit["strict_intent_timing_upper_bound"])
        self.assertAlmostEqual(late_commit["intent_earliest_complete_at_s"], 1.041216)
        self.assertTrue(early_commit["sole_same_flow_post_delivery_flood"])
        self.assertFalse(early_commit["strict_intent_timing_upper_bound"])
        self.assertEqual(early_commit["interfering_transmissions"][0]["committed_at_s"], 1.03)

    def test_recorded_tx_commitment_can_precede_reserved_physical_start(self) -> None:
        sim = CauseSimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            MeshEchoDHR(rescue_mode="flood"), seed=1, max_hops=3,
        )
        sim.now = 1.0
        sim.nodes[1].tx_available_at = 2.0
        packet = tx(1, 1, "FLOOD", 9, 1.0, 1.1).packet

        sim.begin_transmission(1, packet, PendingSend())

        actual = sim.tx_history[-1]
        self.assertEqual(actual.start, 2.0)
        self.assertEqual(sim.tx_commitment_times[actual.tx_id], 1.0)

    def test_two_failed_ack_attempts_count_one_eligible_flow(self) -> None:
        sim = CauseSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0), Node(2, 100.0, 10.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            MeshEchoDHR(rescue_mode="flood"), seed=1, max_hops=3,
        )
        ack_packet = Packet(
            kind="ACK", flow_id=9, origin=1, final_dst=0, ttl=3,
            created_at=0.0, protocol="meshecho-dhr-flood", request_id=9,
            path=(0, 1), path_index=0, app_payload=False,
        )
        ack1 = Transmission(1, 1, ack_packet, 1.30, 1.40)
        ack2 = Transmission(2, 1, ack_packet, 1.50, 1.60)
        flood1 = tx(3, 2, "FLOOD", 9, 1.32, 1.42)
        flood2 = tx(4, 2, "FLOOD", 9, 1.52, 1.62)
        sim.tx_history = [ack1, ack2, flood1, flood2]
        sim.tx_commitment_times = {1: 1.30, 2: 1.50, 3: 1.06, 4: 1.20}
        flow = {
            "flow_id": 9, "src": 0, "dst": 1, "enqueued_at": 0.0,
            "deadline_at": 30.0, "delivered_at": 1.0, "acked_at": None,
            "delivery_by_deadline": True, "ack_by_deadline": False,
            "source_action": "F",
        }

        result = analyze_failure_causes(sim, [flow], observation_cutoff_s=30.0)

        self.assertEqual(result["summary"]["delivered_unacked_flows"], 1)
        self.assertEqual(result["summary"]["ack_attempts_for_delivered_unacked"], 2)
        self.assertEqual(result["summary"]["strict_eligible_unique_flows"], 1)
        attempts = result["missing_flows"][0]["ack_attempts"]
        self.assertEqual([a["failure_cause"]["class"] for a in attempts],
                         ["capture_collision", "capture_collision"])

    def test_tiny_replay_preserves_flow_actions_and_complete_tx_trace(self) -> None:
        case = SrCase(
            key="tiny_ack_failure_cause", nodes=4, area_m=100.0,
            duration_s=8.0, rate_per_min=30.0, pair_mode="random",
            pair_count=0, max_hops=3, temporal_fading_sigma_db=0.0,
        )

        result = run_diagnostic(seed=17, case=case)

        self.assertTrue(result["parity"]["flows_exact"])
        self.assertTrue(result["parity"]["actions_exact"])
        self.assertEqual(result["parity"]["plain_tx_sha256"],
                         result["parity"]["observed_tx_sha256"])
        self.assertEqual(result["parity"]["scheduled_trace_sha256"],
                         result["parity"]["baseline_trace_sha256"])

    def test_cli_modes_have_only_predeclared_smoke_and_exploratory_seeds(self) -> None:
        self.assertEqual(seeds_for_mode("smoke"), (37000,))
        self.assertEqual(seeds_for_mode("explore"), (37001, 37002, 37003))
        with self.assertRaises(ValueError):
            seeds_for_mode("development")

    def test_tiny_report_records_source_and_replay_provenance(self) -> None:
        case = SrCase(
            key="tiny_ack_failure_cause", nodes=4, area_m=100.0,
            duration_s=8.0, rate_per_min=30.0, pair_mode="random",
            pair_count=0, max_hops=3, temporal_fading_sigma_db=0.0,
        )

        report = run_report((17,), case=case, mode="synthetic")

        self.assertEqual(report["seeds"], [17])
        self.assertIn("lora_mesh_sim.py", report["source_sha256"])
        self.assertIn("tools/diagnose_ack_failure_causes.py", report["source_sha256"])
        self.assertTrue(report["runs"][0]["parity"]["flows_exact"])
        self.assertEqual(report["summary"]["delivered_unacked_flows"],
                         report["runs"][0]["summary"]["delivered_unacked_flows"])
        self.assertIsNone(report["summary"]["quiet_window_exposure_gate_passed"])

    def test_artifact_manifest_hashes_report_and_never_overwrites_prefix(self) -> None:
        report = {
            "source_sha256": {"lora_mesh_sim.py": "frozen"},
            "case": {"key": "tiny"}, "seeds": [17], "mode": "synthetic",
            "summary": {"delivered_unacked_flows": 0},
        }
        with tempfile.TemporaryDirectory() as directory:
            paths = write_report(report, Path(directory) / "unique-cause")
            saved = paths["report"].read_bytes()
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))

            self.assertEqual(manifest["report_sha256"], hashlib.sha256(saved).hexdigest())
            self.assertEqual(manifest["source_sha256"], report["source_sha256"])
            with self.assertRaises(FileExistsError):
                write_report(report, Path(directory) / "unique-cause")

    def test_late_delivery_failure_is_not_in_deadline_exposure_denominator(self) -> None:
        sim = CauseSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0), Node(2, 100.0, 10.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            MeshEchoDHR(rescue_mode="flood"), seed=1, max_hops=3,
        )
        ack_packet = Packet(
            kind="ACK", flow_id=9, origin=1, final_dst=0, ttl=3,
            created_at=0.0, protocol="meshecho-dhr-flood", request_id=9,
            path=(0, 1), path_index=0, app_payload=False,
        )
        sim.tx_history = [
            Transmission(1, 1, ack_packet, 31.30, 31.40),
            tx(2, 2, "FLOOD", 9, 31.32, 31.42),
        ]
        sim.tx_commitment_times = {1: 31.30, 2: 31.06}
        flow = {
            "flow_id": 9, "src": 0, "dst": 1, "enqueued_at": 0.0,
            "deadline_at": 30.0, "delivered_at": 31.0, "acked_at": None,
            "delivery_by_deadline": False, "ack_by_deadline": False,
            "source_action": "F",
        }

        summary = analyze_failure_causes(
            sim, [flow], observation_cutoff_s=40.0,
        )["summary"]

        self.assertEqual(summary["all_missing_first_physical_failures"], 1)
        self.assertEqual(summary["all_missing_failure_classes"], {"capture_collision": 1})
        self.assertEqual(summary["delivered_unacked_first_physical_failures"], 0)
        self.assertEqual(summary["delivered_unacked_failure_classes"], {})
        self.assertEqual(summary["delivered_unacked_flows"], 0)
        self.assertEqual(summary["strict_eligible_unique_flows"], 0)

    def test_post_deadline_ack_failure_is_not_a_recoverable_overlap(self) -> None:
        sim = CauseSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0), Node(2, 100.0, 10.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            MeshEchoDHR(rescue_mode="flood"), seed=1, max_hops=3,
        )
        ack_packet = Packet(
            kind="ACK", flow_id=9, origin=1, final_dst=0, ttl=3,
            created_at=0.0, protocol="meshecho-dhr-flood", request_id=9,
            path=(0, 1), path_index=0, app_payload=False,
        )
        sim.tx_history = [
            Transmission(1, 1, ack_packet, 31.30, 31.40),
            tx(2, 2, "FLOOD", 9, 31.32, 31.42),
        ]
        sim.tx_commitment_times = {1: 31.30, 2: 31.06}
        flow = {
            "flow_id": 9, "src": 0, "dst": 1, "enqueued_at": 0.0,
            "deadline_at": 30.0, "delivered_at": 1.0, "acked_at": None,
            "delivery_by_deadline": True, "ack_by_deadline": False,
            "source_action": "F",
        }

        result = analyze_failure_causes(sim, [flow], observation_cutoff_s=40.0)
        summary = result["summary"]

        self.assertEqual(summary["delivered_unacked_first_physical_failures"], 1)
        self.assertEqual(summary["delivered_unacked_flows"], 1)
        self.assertEqual(summary["broad_overlap_unique_flows"], 0)
        self.assertEqual(summary["strict_eligible_unique_flows"], 0)
        self.assertTrue(result["missing_flows"][0]["ack_attempts"][0]
                        ["first_unphysical_reverse_hop"]["after_deadline"])

    def test_saved_complete_tx_history_proves_sole_overlap(self) -> None:
        sim = CauseSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0), Node(2, 100.0, 10.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            MeshEchoDHR(rescue_mode="flood"), seed=1, max_hops=3,
        )
        ack_packet = Packet(
            kind="ACK", flow_id=9, origin=1, final_dst=0, ttl=3,
            created_at=0.0, protocol="meshecho-dhr-flood", request_id=9,
            path=(0, 1), path_index=0, app_payload=False,
        )
        sim.tx_history = [
            Transmission(1, 1, ack_packet, 1.30, 1.40),
            tx(2, 2, "FLOOD", 9, 1.32, 1.42),
            tx(3, 2, "FLOOD", 8, 1.50, 1.60),
        ]
        sim.tx_commitment_times = {1: 1.30, 2: 1.06, 3: 1.50}
        flow = {
            "flow_id": 9, "src": 0, "dst": 1, "enqueued_at": 0.0,
            "deadline_at": 30.0, "delivered_at": 1.0, "acked_at": None,
            "delivery_by_deadline": True, "ack_by_deadline": False,
            "source_action": "F",
        }

        result = analyze_failure_causes(sim, [flow], observation_cutoff_s=30.0)
        cause = result["missing_flows"][0]["ack_attempts"][0]["failure_cause"]
        history = result["tx_history"]
        ack = next(item for item in history if item["tx_id"] == cause["ack_tx_id"])
        overlap_ids = {
            item["tx_id"] for item in history
            if item["tx_id"] != ack["tx_id"]
            and item["start_at_s"] < ack["end_at_s"]
            and ack["start_at_s"] < item["end_at_s"]
        }
        evidence_ids = {
            item["tx_id"] for item in cause["receiver_transmissions"]
            + cause["interfering_transmissions"]
        }

        self.assertEqual({item["tx_id"] for item in history}, {1, 2, 3})
        self.assertEqual(overlap_ids, evidence_ids)
        self.assertEqual(overlap_ids, {2})
        self.assertEqual(next(item for item in history if item["tx_id"] == 2)
                         ["committed_at_s"], 1.06)

    def test_remaining_ack_hop_excludes_nominally_predeadline_failure(self) -> None:
        sim = CauseSimulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0), Node(2, 100.0, 10.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            MeshEchoDHR(rescue_mode="flood"), seed=1, max_hops=3,
        )
        ack_packet = Packet(
            kind="ACK", flow_id=9, origin=1, final_dst=0, ttl=3,
            created_at=0.0, protocol="meshecho-dhr-flood", request_id=9,
            path=(0, 2, 1), path_index=1, app_payload=False,
        )
        sim.tx_history = [
            Transmission(1, 1, ack_packet, 29.90, 29.97),
            tx(2, 2, "FLOOD", 9, 29.92, 30.02),
        ]
        sim.tx_commitment_times = {1: 29.90, 2: 29.80}
        flow = {
            "flow_id": 9, "src": 0, "dst": 1, "enqueued_at": 0.0,
            "deadline_at": 30.0, "delivered_at": 1.0, "acked_at": None,
            "delivery_by_deadline": True, "ack_by_deadline": False,
            "source_action": "F",
        }

        result = analyze_failure_causes(sim, [flow], observation_cutoff_s=31.0)
        cause = result["missing_flows"][0]["ack_attempts"][0]["failure_cause"]

        self.assertEqual(cause["class"], "half_duplex")
        self.assertEqual(cause["remaining_ack_hops"], 1)
        self.assertAlmostEqual(cause["earliest_source_ack_at_s"],
                               29.97 + sim.radio.packet_toa_s(ack_packet))
        self.assertGreater(cause["earliest_source_ack_at_s"], flow["deadline_at"])
        self.assertEqual(result["summary"]["broad_overlap_unique_flows"], 0)
        self.assertEqual(result["summary"]["strict_eligible_unique_flows"], 0)

    def test_cli_requires_mode_and_unique_prefix_without_seed_override(self) -> None:
        args = parse_args([
            "--mode", "smoke", "--output-prefix", "/tmp/ack-cause-unit",
        ])
        self.assertEqual(args.mode, "smoke")
        self.assertEqual(args.output_prefix, Path("/tmp/ack-cause-unit"))
        with self.assertRaises(SystemExit):
            parse_args([
                "--mode", "smoke", "--output-prefix", "/tmp/ack-cause-unit",
                "--seed", "36001",
            ])
        with self.assertRaises(SystemExit):
            parse_args(["--mode", "explore"])


if __name__ == "__main__":
    unittest.main()
