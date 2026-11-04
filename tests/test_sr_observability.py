import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from lora_mesh_sim import Node, Packet, RadioConfig, Transmission, build_protocol
from tools.run_sr_experiment import RecordingSimulator, SR_CASES, run_one_sr
from tools.diagnose_sr_observability import (
    ObservabilitySimulator,
    analyze_observability,
    run_diagnostic,
    summarize_ack_hops,
)


class SrObservabilityTest(unittest.TestCase):
    def test_cli_refuses_to_overwrite_existing_output(self):
        script = Path(__file__).resolve().parents[1] / "tools" / "diagnose_sr_observability.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "existing.json"
            output.write_text("sentinel", encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(script), "--seeds", "11001",
                 "--output", str(output)],
                capture_output=True, text=True, timeout=30,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertEqual(output.read_text(encoding="utf-8"), "sentinel")

    def test_cli_records_source_hashes(self):
        script = Path(__file__).resolve().parents[1] / "tools" / "diagnose_sr_observability.py"
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "diagnostic.json"
            completed = subprocess.run(
                [sys.executable, str(script), "--seeds", "11001",
                 "--output", str(output)],
                capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            actual = json.loads(output.read_text(encoding="utf-8"))["source_sha256"]
        sources = {
            "diagnostic_script": script,
            "simulator": script.parents[1] / "lora_mesh_sim.py",
            "runner": script.with_name("run_sr_experiment.py"),
        }
        expected = {
            name: hashlib.sha256(path.read_bytes()).hexdigest()
            for name, path in sources.items()
        }
        self.assertEqual(actual, expected)

    def test_runner_rejects_non_diagnostic_seed_before_simulating(self):
        with self.assertRaisesRegex(ValueError, "diagnostic seeds"):
            run_diagnostic(9001)

    def test_diagnostic_replays_runner_trace_and_deadline_outcomes(self):
        observed = run_diagnostic(11001)
        frozen = run_one_sr(SR_CASES["recurring_fading"], "meshecho-dhr", 11001).row

        self.assertEqual(observed["scheduled_trace_sha256"],
                         frozen["scheduled_trace_sha256"])
        self.assertEqual(observed["scheduled_flows"],
                         frozen["scheduled_unicast_flows"])
        self.assertEqual(observed["ack_by_deadline"], frozen["ack_by_deadline"])
        self.assertEqual(observed["delivery_by_deadline"],
                         frozen["delivery_by_deadline"])

    def make_sim(self):
        sim = ObservabilitySimulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0),
             Node(2, 20.0, 0.0), Node(3, 15.0, 5.0)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol("meshecho-dhr"), seed=11001, max_hops=6,
            independent_random_streams=True,
        )
        sim.metrics.register_flow(1, 0, 2, 0.0)
        sim.protocol.flow_data_actions[1] = "R"
        return sim

    def test_rx_tap_records_actual_decode_without_consuming_extra_randomness(self):
        nodes = [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0),
                 Node(2, 20.0, 0.0)]
        radio = RadioConfig(
            sf=7, shadow_sigma_db=0.0, temporal_fading_sigma_db=0.0,
        )
        observed = ObservabilitySimulator(
            nodes, radio, build_protocol("meshecho-dhr"), seed=11001,
            max_hops=6, independent_random_streams=True,
        )
        control = RecordingSimulator(
            nodes, radio, build_protocol("meshecho-dhr"), seed=11001,
            max_hops=6, independent_random_streams=True,
        )
        packet = Packet(
            "DATA", 1, 0, 2, 6, 0.0, "meshecho-dhr",
            request_id=1, path=(0, 1, 2),
        )
        tx = Transmission(1, 0, packet, 0.0, radio.packet_toa_s(packet))
        for sim in (observed, control):
            sim.protocol.flow_data_actions[1] = "R"

        tapped = observed.try_receive(tx, 1)
        baseline = control.try_receive(tx, 1)

        self.assertEqual(tapped is not None, baseline is not None)
        self.assertEqual(observed.channel_random.getstate(),
                         control.channel_random.getstate())
        self.assertEqual(observed.metrics.rx_success, control.metrics.rx_success)
        self.assertEqual(observed.metrics.rx_fail, control.metrics.rx_fail)
        self.assertIn(1, observed.successful_decodes[tx.tx_id])

    def test_rx_tap_includes_marked_flood_ack_decodes(self):
        sim = self.make_sim()
        sim.protocol.flow_data_actions[1] = "F"
        ack = Packet("ACK", 1, 2, 0, 6, 0.0, "meshecho-dhr",
                     request_id=1, path=(0, 1, 2), path_index=1,
                     repair_index=2, app_payload=False)
        tx = Transmission(1, 2, ack, 1.0, 1.1)

        self.assertIsNotNone(sim.try_receive(tx, 1))
        self.assertIn(1, sim.successful_decodes[tx.tx_id])

    def test_passive_forward_and_last_hop_ack_are_observed_at_predecessor(self):
        sim = self.make_sim()
        data = Packet("DATA", 1, 0, 2, 6, 0.0, "meshecho-dhr",
                      request_id=1, path=(0, 1, 2))
        forwarded = Packet("DATA", 1, 0, 2, 6, 0.0, "meshecho-dhr",
                           request_id=1, path=(0, 1, 2), path_index=1)
        ack = Packet("ACK", 1, 2, 0, 6, 1.0, "meshecho-dhr",
                     request_id=1, path=(0, 1, 2), path_index=1,
                     app_payload=False)
        sim.tx_history = [
            Transmission(1, 0, data, 1.0, 1.1),
            Transmission(2, 1, forwarded, 1.2, 1.3),
            Transmission(3, 2, ack, 1.4, 1.5),
        ]
        sim.successful_decodes = {
            1: {1: 0.0}, 2: {0: 0.0, 2: 0.0}, 3: {1: 0.0},
        }

        result = analyze_observability(sim, cutoff_s=30.0)

        self.assertEqual(len(result["hops"]), 2)
        self.assertTrue(all(hop["next_hop_decoded"] for hop in result["hops"]))
        self.assertTrue(all(hop["passive_observed_by_guard"] for hop in result["hops"]))
        self.assertEqual([hop["evidence_kind"] for hop in result["hops"]],
                         ["forward", "ack"])
        self.assertEqual(result["summary"]["true_positive"], 2)
        self.assertEqual(result["summary"]["false_failure"], 0)

    def test_false_observations_have_truth_denominators_and_unfinished_hops_are_censored(self):
        sim = self.make_sim()
        for flow_id in (2, 3, 4):
            sim.metrics.register_flow(flow_id, 0, 2, 0.0)
            sim.protocol.flow_data_actions[flow_id] = "R"
        def data(flow_id, index=0):
            return Packet("DATA", flow_id, 0, 2, 6, 0.0, "meshecho-dhr",
                          request_id=flow_id, path=(0, 1, 2), path_index=index)
        sim.tx_history = [
            Transmission(1, 0, data(1), 1.0, 1.1),
            Transmission(2, 0, data(2), 2.0, 2.1),
            Transmission(3, 1, data(2, 1), 3.0, 3.1),
            Transmission(6, 2, Packet(
                "ACK", 2, 2, 0, 6, 3.1, "meshecho-dhr",
                request_id=2, path=(0, 1, 2), path_index=1,
                app_payload=False,
            ), 4.0, 4.1),
            Transmission(4, 0, data(3), 24.0, 24.1),
            Transmission(5, 0, data(4), 24.9, 25.1),
        ]
        sim.successful_decodes = {
            1: {1: 0.0}, 3: {0: 0.0, 2: 0.0},
            6: {1: 0.0}, 4: {1: 0.0},
        }

        result = analyze_observability(sim, cutoff_s=25.0)

        self.assertEqual(result["summary"]["false_failure"], 1)
        self.assertEqual(result["summary"]["false_failure_denominator"], 2)
        self.assertEqual(result["summary"]["false_success"], 1)
        self.assertEqual(result["summary"]["false_success_denominator"], 1)
        self.assertEqual(result["summary"]["censored_hops"], 2)
        self.assertIsNone(result["hops"][4]["next_hop_decoded"])

    def test_failed_hop_has_oracle_detour_only_through_actual_off_path_decoder(self):
        sim = self.make_sim()
        packet = Packet("DATA", 1, 0, 2, 6, 0.0, "meshecho-dhr",
                        request_id=1, path=(0, 1, 2))
        sim.tx_history = [Transmission(1, 0, packet, 1.0, 1.1)]
        sim.successful_decodes = {1: {3: 0.0}}

        result = analyze_observability(sim, cutoff_s=30.0)

        self.assertEqual(result["hops"][0]["oracle_eligible_candidates"], [3])
        self.assertEqual(result["summary"]["failed_hops_with_oracle_detour"], 1)
        self.assertEqual(result["summary"]["oracle_failed_hop_denominator"], 1)

    def test_guard_delayed_oracle_excludes_detour_that_only_immediate_action_can_fit(self):
        sim = self.make_sim()
        sim.protocol.app_deadline_s = 2.0
        packet = Packet("DATA", 1, 0, 2, 6, 0.0, "meshecho-dhr",
                        request_id=1, path=(0, 1, 2))
        sim.tx_history = [Transmission(1, 0, packet, 1.0, 1.1)]
        sim.successful_decodes = {1: {3: 0.0}}

        result = analyze_observability(sim, cutoff_s=30.0)

        self.assertEqual(result["hops"][0]["oracle_eligible_candidates"], [3])
        self.assertEqual(result["hops"][0]["oracle_guard_eligible_candidates"], [])
        self.assertEqual(result["summary"]["failed_hops_with_guard_detour"], 0)

    def test_oracle_detour_rejects_a_queued_or_unreliable_relay(self):
        sim = self.make_sim()
        packet = Packet("DATA", 1, 0, 2, 6, 0.0, "meshecho-dhr",
                        request_id=1, path=(0, 1, 2))
        sim.tx_history = [Transmission(1, 0, packet, 1.0, 1.1)]
        sim.successful_decodes = {1: {3: 29.95}}
        self.assertEqual(
            analyze_observability(sim, cutoff_s=30.0)["hops"][0]
            ["oracle_eligible_candidates"], [],
        )
        sim.successful_decodes = {1: {3: 0.0}}
        sim.nodes[3].x = 100_000_000.0
        self.assertEqual(
            analyze_observability(sim, cutoff_s=30.0)["hops"][0]
            ["oracle_eligible_candidates"], [],
        )

    def test_ack_summary_counts_actual_f_and_r_hops_and_first_phy_failure(self):
        sim = self.make_sim()
        sim.metrics.register_flow(2, 0, 2, 0.0)
        sim.protocol.flow_data_actions[2] = "F"
        def ack(flow_id, index, repair_index=None):
            return Packet("ACK", flow_id, 2, 0, 6, 0.0, "meshecho-dhr",
                          request_id=flow_id, path=(0, 1, 2),
                          path_index=index, app_payload=False,
                          repair_index=repair_index)
        sim.tx_history = [
            Transmission(1, 2, ack(1, 1), 1.0, 1.1),
            Transmission(2, 1, ack(1, 0), 1.2, 1.3),
            Transmission(3, 2, ack(2, 1), 2.0, 2.1),
            Transmission(4, 2, ack(2, 1), 3.0, 3.1),
            Transmission(5, 1, ack(2, 0), 3.2, 3.3),
            Transmission(6, 2, ack(1, 1, repair_index=2), 4.0, 4.1),
        ]
        sim.successful_decodes = {
            1: {1: 0.0}, 4: {1: 0.0}, 5: {0: 0.0}, 6: {1: 0.0},
        }

        result = summarize_ack_hops(sim, cutoff_s=30.0)

        self.assertEqual(result["by_initial_action"]["R"]["failed"], 1)
        self.assertEqual(result["by_initial_action"]["F"]["transmitted"], 3)
        self.assertEqual(result["by_initial_action"]["F"]["decoded"], 2)
        self.assertEqual(result["by_ack_phase"]["f_rescue"]["decoded"], 1)
        self.assertEqual(result["by_ack_phase"]["initial"]["failed"], 2)
        self.assertEqual(
            [(row["flow_id"], row["tx_id"])
             for row in result["first_failed_hops"]], [(1, 2), (2, 3)],
        )
