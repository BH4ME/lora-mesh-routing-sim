"""Behavioral checks for the passive first-edge ACK-signal diagnostic."""

import unittest
from dataclasses import asdict, replace
import tempfile
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from lora_mesh_sim import (
    MeshEchoDHRDelayedAck, Node, Packet, RadioConfig, Transmission,
)
from tools.diagnose_first_edge_ack_signal import (
    PassiveFirstEdgeSimulator, analyze_first_edge, evaluate_q_predictor,
    fit_q_predictor, main, run_diagnostic, run_report, seeds_for_mode,
    trace_actual_ack, validate_manifest, write_report,
)
from tools import diagnose_first_edge_ack_signal as diagnostic
from tools.run_sr_experiment import RecordingSimulator, SrCase


def scheduled_direct(simulator_type):
    sim = simulator_type(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(), seed=1, max_hops=3,
        independent_random_streams=True,
    )
    packet = Packet(
        kind="FLOOD", flow_id=7, origin=0, final_dst=1, ttl=3,
        created_at=0.0, protocol=sim.protocol.name, request_id=7,
        path=(0,), app_payload=True,
    )
    sim.metrics.register_flow(7, 0, 1, 0.0)
    sim.protocol.seen_floods[0].add(packet.flood_key)
    sim.transmit_later(0, packet, 0.0)
    sim.run(5.0)
    return sim


def scheduled_three_node_flood():
    sim = PassiveFirstEdgeSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0),
         Node(2, 20.0, 0.0)],
        RadioConfig(sf=7, tx_power_dbm=-45.0, shadow_sigma_db=0.0),
        MeshEchoDHRDelayedAck(), seed=1, max_hops=3,
        independent_random_streams=True,
    )
    packet = Packet(
        kind="FLOOD", flow_id=7, origin=0, final_dst=2, ttl=3,
        created_at=0.0, protocol=sim.protocol.name, request_id=7,
        path=(0,), min_forward_margin_q=-126,
    )
    sim.metrics.register_flow(7, 0, 2, 0.0)
    sim.protocol.seen_floods[0].add(packet.flood_key)
    sim.transmit_later(0, packet, 0.0)
    sim.run(5.0)
    return sim


FLOW_ROW = {
    "flow_id": 7, "src": 0, "dst": 2, "enqueued_at": 0.0,
    "deadline_at": 30.0, "source_action": "F",
    "delivery_by_deadline": True, "ack_by_deadline": False,
}


class FirstEdgeAckSignalTests(unittest.TestCase):
    def test_direct_first_edge_and_delayed_ack_are_passively_observed(self):
        stock = scheduled_direct(RecordingSimulator)
        observed = scheduled_direct(PassiveFirstEdgeSimulator)

        self.assertEqual([asdict(tx) for tx in observed.tx_history],
                         [asdict(tx) for tx in stock.tx_history])
        self.assertEqual(observed.random.getstate(), stock.random.getstate())
        self.assertEqual(observed.channel_random.getstate(),
                         stock.channel_random.getstate())
        self.assertEqual(observed.flood_decodes[1][1].sender, 0)
        self.assertEqual(observed.destination_flood_decodes[0], (1, 1))
        ack = next(tx for tx in observed.tx_history if tx.packet.kind == "ACK")
        self.assertEqual(observed.ack_parent_tx_id[ack.tx_id], 1)

    def test_forwarded_path_uses_causal_parent_and_first_edge_rx(self):
        sim = scheduled_three_node_flood()

        forwarded = next(tx for tx in sim.tx_history
                         if tx.packet.kind == "FLOOD" and tx.sender == 1)
        self.assertEqual(sim.flood_parent_tx_id[forwarded.tx_id], 1)
        analysis = analyze_first_edge(sim, [FLOW_ROW], observation_cutoff_s=5.0)
        paths = {tuple(item["path"]): item for item in analysis["paths"]}
        self.assertIn((0, 1, 2), paths)
        self.assertEqual(paths[(0, 1, 2)]["causal_tx_ids"], [1, forwarded.tx_id])
        self.assertEqual(paths[(0, 1, 2)]["first_edge_rx_snr_db"],
                         sim.flood_decodes[1][1].snr_db)
        self.assertNotEqual(paths[(0, 1, 2)]["first_edge_q"], -126)

    def test_nested_screen_charges_complete_candidate_ack_paths(self):
        sim = scheduled_three_node_flood()
        result = analyze_first_edge(sim, [FLOW_ROW], observation_cutoff_s=5.0)

        epoch = result["epochs"][0]
        self.assertEqual(epoch["original_path"], [0, 2])
        alternate = next(item for item in epoch["alternatives"]
                         if item["path"] == [0, 1, 2])
        self.assertTrue(alternate["A_distinct_first_edge"])
        self.assertEqual(alternate["B_within_two_original_ack_copies"],
                         alternate["ack_cost_s"] <= 2 * epoch["original_ack_cost_s"])
        self.assertEqual(alternate["C_first_edge_q_gain_at_least_6"],
                         alternate["B_within_two_original_ack_copies"]
                         and alternate["first_edge_q"] - epoch["first_edge_q"] >= 6)
        self.assertEqual(alternate["two_ack_pair_cost_s"],
                         alternate["ack_cost_s"] + epoch["original_ack_cost_s"])
        self.assertAlmostEqual(
            alternate["nominal_ack2_requested_at_s"],
            epoch["first_destination_decode_at_s"] + 2.0
            + epoch["original_ack_cost_s"] / (len(epoch["original_path"]) - 1)
            + 0.5,
        )
        self.assertEqual(
            alternate["nominal_ack2_completion_at_s"],
            alternate["nominal_ack2_requested_at_s"] + alternate["ack_cost_s"],
        )
        self.assertGreaterEqual(
            alternate["serial_nonoverlap_pair_completion_at_s"],
            alternate["nominal_both_acks_complete_at_s"],
        )
        self.assertGreater(alternate["ack_cost_s"],
                           2 * sim.radio.packet_toa_s(next(
                               tx.packet for tx in sim.tx_history
                               if tx.packet.kind == "ACK"
                           )))
        self.assertEqual(
            sum(bin_row["samples"] for bin_row in result["summary"]["predictor_by_q_bin"].values()),
            result["summary"]["final_hop_predictor_samples"],
        )

    def test_missing_parent_rejects_same_looking_forwarded_path(self):
        sim = scheduled_three_node_flood()
        forwarded = next(tx for tx in sim.tx_history
                         if tx.packet.kind == "FLOOD" and tx.sender == 1)
        sim.flood_parent_tx_id.pop(forwarded.tx_id)

        result = analyze_first_edge(sim, [FLOW_ROW], observation_cutoff_s=5.0)

        self.assertNotIn([0, 1, 2], [item["path"] for item in result["paths"]])
        self.assertIn({"dest_tx_id": forwarded.tx_id,
                       "reason": "missing_or_cyclic_causal_parent"},
                      result["rejected_paths"])

    def test_ambiguous_causal_parent_excludes_entire_flood_epoch(self):
        sim = scheduled_three_node_flood()
        forwarded = next(tx for tx in sim.tx_history
                         if tx.packet.kind == "FLOOD" and tx.sender == 1)
        sim.flood_parent_tx_id.pop(forwarded.tx_id)

        result = analyze_first_edge(sim, [FLOW_ROW], observation_cutoff_s=5.0)

        self.assertEqual(result["summary"]["destination_flood_epochs"], 1)
        self.assertEqual(result["summary"]["epochs_with_causal_ack"], 0)
        self.assertEqual(result["summary"]["final_hop_predictor_samples"], 0)
        self.assertEqual(result["epochs"][0]["reason"], "ambiguous_causal_epoch")

    def test_ack_without_source_adjacent_tx_is_censored_not_link_failure(self):
        sim = scheduled_three_node_flood()
        packet = Packet(
            kind="ACK", flow_id=7, origin=2, final_dst=0, ttl=3,
            created_at=0.0, protocol=sim.protocol.name, request_id=7,
            path=(0, 1, 2), path_index=1, app_payload=False,
        )
        root = Transmission(99, 2, packet, 6.0, 6.1)
        sim.tx_history.append(root)
        sim.ack_decodes[(99, 1)] = True

        censored = trace_actual_ack(sim, root, 30.0, 30.0)

        self.assertEqual(censored["termination"], "decoded_no_matching_forward")
        self.assertFalse(censored["final_hop_attempted"])
        self.assertIsNone(censored["final_hop_decoded_by_deadline"])
        self.assertIsNone(censored["first_unphysical_hop"])

        final_tx = Transmission(
            100, 1, replace(packet, path_index=0), 6.2, 6.3,
        )
        sim.tx_history.append(final_tx)
        sim.ack_parent_tx_id[100] = 99
        sim.ack_decodes[(100, 0)] = False
        failed = trace_actual_ack(sim, root, 30.0, 30.0)

        self.assertTrue(failed["final_hop_attempted"])
        self.assertFalse(failed["final_hop_decoded_by_deadline"])
        self.assertEqual(failed["first_unphysical_hop"]["edge"], [1, 0])
        self.assertTrue(failed["source_final_first_failure"])

    def test_late_final_ack_is_censored_for_link_predictor(self):
        sim = scheduled_three_node_flood()
        packet = Packet(
            kind="ACK", flow_id=7, origin=2, final_dst=0, ttl=3,
            created_at=0.0, protocol=sim.protocol.name, request_id=7,
            path=(0, 2), path_index=0, app_payload=False,
        )
        late = Transmission(99, 2, packet, 29.95, 30.05)
        sim.tx_history.append(late)
        sim.ack_decodes[(99, 0)] = True

        result = trace_actual_ack(sim, late, deadline_at_s=30.0,
                                  observation_cutoff_s=31.0)

        self.assertTrue(result["final_hop_attempted"])
        self.assertTrue(result["final_hop_physically_decoded"])
        self.assertTrue(result["final_hop_after_deadline"])
        self.assertIsNone(result["final_hop_decoded_by_deadline"])

    def test_final_ack_ending_after_observation_cutoff_still_counts_as_late(self):
        sim = scheduled_three_node_flood()
        packet = Packet(
            kind="ACK", flow_id=7, origin=2, final_dst=0, ttl=3,
            created_at=0.0, protocol=sim.protocol.name, request_id=7,
            path=(0, 2), path_index=0, app_payload=False,
        )
        late = Transmission(99, 2, packet, 30.95, 31.05)
        sim.tx_history.append(late)

        result = trace_actual_ack(sim, late, deadline_at_s=30.0,
                                  observation_cutoff_s=31.0)

        self.assertTrue(result["final_hop_attempted"])
        self.assertTrue(result["final_hop_after_deadline"])
        self.assertIsNone(result["final_hop_physically_decoded"])
        self.assertIsNone(result["final_hop_decoded_by_deadline"])
        self.assertEqual(result["termination"], "observation_censored")

    def test_seed_one_strict_stock_parity_and_diagnostic_replay(self):
        case = SrCase(
            key="tiny_first_edge", nodes=4, area_m=100.0,
            duration_s=8.0, rate_per_min=30.0, pair_mode="random",
            pair_count=0, max_hops=3, temporal_fading_sigma_db=0.0,
        )

        run = run_diagnostic(seed=1, case=case)

        self.assertTrue(run["parity"]["exact"])
        self.assertTrue(run["strict_replay_exact"])
        self.assertEqual(run["row"]["scheduled_trace_sha256"],
                         run["parity"]["scheduled_trace_sha256"])
        self.assertEqual(run["summary"]["scheduled_flows"],
                         run["row"]["scheduled_unicast_flows"])

    def test_analysis_must_not_advance_channel_rng_after_stock_parity(self):
        case = SrCase(
            key="tiny_first_edge", nodes=4, area_m=100.0,
            duration_s=8.0, rate_per_min=30.0, pair_mode="random",
            pair_count=0, max_hops=3, temporal_fading_sigma_db=0.0,
        )
        real_analyze = diagnostic.analyze_first_edge

        def bad_analyze(sim, flows, cutoff):
            result = real_analyze(sim, flows, cutoff)
            sim.channel_random.random()
            return result

        with patch.object(diagnostic, "analyze_first_edge", bad_analyze):
            with self.assertRaises(AssertionError):
                run_diagnostic(seed=1, case=case)

    def test_fixed_q_predictor_beats_constant_on_independent_seeds(self):
        def rows(start_seed):
            return [
                {"seed": seed, "first_edge_q": -20 if index < 4 else 20,
                 "success_by_deadline": index >= 4,
                 "path_type": "direct"}
                for seed in range(start_seed, start_seed + 10)
                for index in range(10)
            ]

        model = fit_q_predictor(rows(1))
        validation = evaluate_q_predictor(model, rows(101))

        self.assertEqual(validation["samples"], 100)
        self.assertLess(validation["brier_model"],
                        validation["brier_training_constant"])
        self.assertGreater(validation["seed_bootstrap_auc_95_lower"], 0.5)
        self.assertTrue(validation["sample_gate_passed"])
        self.assertTrue(validation["prediction_gate_passed"])
        self.assertEqual(validation["validated_path_types"], ["direct"])
        self.assertFalse(validation["by_path_type"]["multihop"]["prediction_gate_passed"])

    def test_pooled_signal_cannot_certify_unvalidated_multihop_stratum(self):
        def rows(start_seed):
            result = []
            for seed in range(start_seed, start_seed + 10):
                result.extend({
                    "seed": seed, "first_edge_q": -20 if index < 8 else 20,
                    "success_by_deadline": index >= 8,
                    "path_type": "direct",
                } for index in range(20))
                result.extend({
                    "seed": seed, "first_edge_q": 0,
                    "success_by_deadline": index >= 5,
                    "path_type": "multihop",
                } for index in range(10))
            return result

        model = fit_q_predictor(rows(1))
        validation = evaluate_q_predictor(model, rows(101))

        self.assertTrue(validation["by_path_type"]["direct"]["prediction_gate_passed"])
        self.assertTrue(validation["by_path_type"]["multihop"]["sample_gate_passed"])
        self.assertFalse(validation["by_path_type"]["multihop"]["prediction_gate_passed"])
        self.assertEqual(validation["validated_path_types"], ["direct"])
        self.assertTrue(validation["any_validated_path_type"])
        self.assertEqual(validation["claim_scope"], "direct")

    def test_path_type_claim_requires_training_support_in_that_type(self):
        training = [
            {"seed": seed, "first_edge_q": -20 if index < 10 else 20,
             "success_by_deadline": index >= 10, "path_type": "multihop"}
            for seed in range(1, 11) for index in range(20)
        ]
        training.append({
            "seed": 1, "first_edge_q": 20,
            "success_by_deadline": True, "path_type": "direct",
        })
        validation_rows = [
            {"seed": seed, "first_edge_q": -20 if index < 5 else 20,
             "success_by_deadline": index >= 5, "path_type": "direct"}
            for seed in range(101, 111) for index in range(10)
        ]

        result = evaluate_q_predictor(fit_q_predictor(training), validation_rows)

        self.assertTrue(result["by_path_type"]["direct"]["sample_gate_passed"])
        self.assertFalse(result["by_path_type"]["direct"]["training_sample_gate_passed"])
        self.assertFalse(result["by_path_type"]["direct"]["prediction_gate_passed"])
        self.assertEqual(result["claim_scope"], "none")

    def test_cli_cohorts_are_fixed_and_synthetic_mode_cannot_open_reserved_seeds(self):
        self.assertEqual(seeds_for_mode("smoke"), (42000,))
        self.assertEqual(seeds_for_mode("explore"), tuple(range(42001, 42021)))
        self.assertEqual(seeds_for_mode("validation"), tuple(range(42101, 42121)))
        with self.assertRaises(ValueError):
            seeds_for_mode("development")
        with self.assertRaises(ValueError):
            run_report((42000,), mode="synthetic")

    def test_cli_refuses_existing_output_before_opening_smoke_seed(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "first-edge"
            prefix.with_name(prefix.name + ".summary.json").touch()
            with patch.object(diagnostic, "run_report",
                              side_effect=AssertionError("opened seed")) as run:
                with self.assertRaises(FileExistsError):
                    main(["--mode", "smoke", "--output-prefix", str(prefix)])
            run.assert_not_called()

    def test_seed_one_report_writes_hash_verified_nonoverwriting_artifacts(self):
        case = SrCase(
            key="tiny_first_edge", nodes=4, area_m=100.0,
            duration_s=8.0, rate_per_min=30.0, pair_mode="random",
            pair_count=0, max_hops=3, temporal_fading_sigma_db=0.0,
        )
        report = run_report((1,), case=case, mode="synthetic")
        self.assertEqual(report["summary"]["predictor_by_q_bin"],
                         report["runs"][0]["summary"]["predictor_by_q_bin"])
        self.assertEqual(report["summary"]["screen_by_original_path_type"],
                         report["runs"][0]["summary"]["screen_by_original_path_type"])

        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "first-edge"
            paths = write_report(report, prefix)
            verified = validate_manifest(
                paths["manifest"], expected_mode="synthetic",
                expected_source_sha256=report["source_sha256"],
                expected_case_sha256=report["case_sha256"],
            )
            self.assertEqual(verified["seeds"], [1])
            self.assertIn("paths", paths)
            self.assertIn("transmissions", paths)
            with self.assertRaises(FileExistsError):
                write_report(report, prefix)
            paths["paths"].write_bytes(paths["paths"].read_bytes() + b"\n")
            with self.assertRaises(ValueError):
                validate_manifest(
                    paths["manifest"], expected_mode="synthetic",
                    expected_source_sha256=report["source_sha256"],
                    expected_case_sha256=report["case_sha256"],
                )

    def test_manifest_rejects_rehashed_run_claim_with_failed_parity(self):
        case = SrCase(
            key="tiny_first_edge", nodes=4, area_m=100.0,
            duration_s=8.0, rate_per_min=30.0, pair_mode="random",
            pair_count=0, max_hops=3, temporal_fading_sigma_db=0.0,
        )
        report = run_report((1,), case=case, mode="synthetic")
        with tempfile.TemporaryDirectory() as directory:
            paths = write_report(report, Path(directory) / "forged")
            run = json.loads(paths["runs"].read_text())
            run["parity"]["exact"] = False
            runs_bytes = (json.dumps(run, sort_keys=True, separators=(",", ":"))
                          + "\n").encode()
            paths["runs"].write_bytes(runs_bytes)
            manifest = json.loads(paths["manifest"].read_text())
            manifest["artifacts"]["runs"]["sha256"] = hashlib.sha256(
                runs_bytes
            ).hexdigest()
            manifest_bytes = (json.dumps(manifest, sort_keys=True, indent=2)
                              + "\n").encode()
            paths["manifest"].write_bytes(manifest_bytes)
            paths["manifest_sha256"].write_text(
                hashlib.sha256(manifest_bytes).hexdigest()
                + "  " + paths["manifest"].name + "\n"
            )

            with self.assertRaises(ValueError):
                validate_manifest(
                    paths["manifest"], expected_mode="synthetic",
                    expected_source_sha256=report["source_sha256"],
                    expected_case_sha256=report["case_sha256"],
                )

    def test_manifest_rejects_rehashed_training_support_claim(self):
        case = SrCase(
            key="tiny_first_edge", nodes=4, area_m=100.0,
            duration_s=8.0, rate_per_min=30.0, pair_mode="random",
            pair_count=0, max_hops=3, temporal_fading_sigma_db=0.0,
        )
        report = run_report((1,), case=case, mode="synthetic")
        self.assertFalse(report["summary"]["predictor_training_support"]["passed"])
        with tempfile.TemporaryDirectory() as directory:
            paths = write_report(report, Path(directory) / "forged-support")
            metadata = json.loads(paths["summary"].read_text())
            metadata["summary"]["predictor_training_support"]["passed"] = True
            summary_bytes = (json.dumps(metadata, sort_keys=True, indent=2)
                             + "\n").encode()
            paths["summary"].write_bytes(summary_bytes)
            manifest = json.loads(paths["manifest"].read_text())
            manifest["summary"]["predictor_training_support"]["passed"] = True
            manifest["artifacts"]["summary"]["sha256"] = hashlib.sha256(
                summary_bytes
            ).hexdigest()
            manifest_bytes = (json.dumps(manifest, sort_keys=True, indent=2)
                              + "\n").encode()
            paths["manifest"].write_bytes(manifest_bytes)
            paths["manifest_sha256"].write_text(
                hashlib.sha256(manifest_bytes).hexdigest()
                + "  " + paths["manifest"].name + "\n"
            )

            with self.assertRaises(ValueError):
                validate_manifest(
                    paths["manifest"], expected_mode="synthetic",
                    expected_source_sha256=report["source_sha256"],
                    expected_case_sha256=report["case_sha256"],
                )

    def test_manifest_rejects_predictor_model_outside_training_split(self):
        case = SrCase(
            key="tiny_first_edge", nodes=4, area_m=100.0,
            duration_s=8.0, rate_per_min=30.0, pair_mode="random",
            pair_count=0, max_hops=3, temporal_fading_sigma_db=0.0,
        )
        report = run_report((1,), case=case, mode="synthetic")
        report["predictor_model"] = fit_q_predictor(
            report["runs"][0]["predictor_rows"]
        )
        with tempfile.TemporaryDirectory() as directory:
            paths = write_report(report, Path(directory) / "model-outside-training")

            with self.assertRaises(ValueError):
                validate_manifest(
                    paths["manifest"], expected_mode="synthetic",
                    expected_source_sha256=report["source_sha256"],
                    expected_case_sha256=report["case_sha256"],
                )

    def test_manifest_rejects_predictor_row_seed_different_from_run(self):
        case = SrCase(
            key="tiny_first_edge", nodes=4, area_m=100.0,
            duration_s=8.0, rate_per_min=30.0, pair_mode="random",
            pair_count=0, max_hops=3, temporal_fading_sigma_db=0.0,
        )
        report = run_report((1,), case=case, mode="synthetic")
        self.assertTrue(report["runs"][0]["predictor_rows"])
        report["runs"][0]["predictor_rows"][0]["seed"] = 2
        report["summary"]["predictor_training_support"]["seeds"] = 2
        with tempfile.TemporaryDirectory() as directory:
            paths = write_report(report, Path(directory) / "misattributed-row")

            with self.assertRaises(ValueError):
                validate_manifest(
                    paths["manifest"], expected_mode="synthetic",
                    expected_source_sha256=report["source_sha256"],
                    expected_case_sha256=report["case_sha256"],
                )


if __name__ == "__main__":
    unittest.main()
