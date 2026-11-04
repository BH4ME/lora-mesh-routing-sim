"""Synthetic behavior checks for the fixed-delay ACK RX diagnostic."""

import unittest
from dataclasses import replace
import hashlib
import json
import tempfile
from pathlib import Path

from lora_mesh_sim import MeshEchoDHRDelayedAck, Node, Packet, RadioConfig, Transmission
from tools.diagnose_delayed_ack_rx import (
    DiagnosticSimulator, RunEvidence, analyze_ack_receptions, assess_flows,
    capture_run, require_stock_parity, run_diagnostic, run_report, seeds_for_mode,
    validate_smoke_manifest, write_report,
)
from tools.run_sr_experiment import SrCase, SrRun
from tools import run_sr_experiment as sr


def make_sim() -> DiagnosticSimulator:
    return DiagnosticSimulator(
        [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0), Node(2, 20.0, 0.0)],
        RadioConfig(sf=7, shadow_sigma_db=0.0), MeshEchoDHRDelayedAck(),
        seed=1, max_hops=3,
    )


def ack_tx(start: float = 5.0, end: float = 5.1) -> Transmission:
    packet = Packet(
        kind="ACK", flow_id=7, origin=2, final_dst=0, ttl=3,
        created_at=0.0, protocol="meshecho-dhr-flood-ack-delay",
        request_id=7, path=(0, 1, 2), path_index=1, app_payload=False,
    )
    return Transmission(1, 2, packet, start, end)


def flow_row(deadline: float = 30.0) -> dict:
    return {
        "flow_id": 7, "src": 0, "dst": 2, "deadline_at": deadline,
        "enqueued_at": 0.0, "source_action": "F",
        "delivered_at": 4.0, "acked_at": None,
        "delivery_by_deadline": True, "ack_by_deadline": False,
    }


class DelayedAckRxDiagnosticTests(unittest.TestCase):
    def test_intended_hop_and_off_index_source_decode_are_distinct(self) -> None:
        sim = make_sim()
        ack = ack_tx()
        sim.transmissions = [ack]
        sim.tx_history = [ack]
        sim.tx_commitment_times = {ack.tx_id: ack.start}

        self.assertIsNotNone(sim.try_receive(ack, 1))
        self.assertIsNotNone(sim.try_receive(ack, 0))
        result = analyze_ack_receptions(sim, [flow_row()], observation_cutoff_s=30.0)

        by_role = {item["role"]: item for item in result["attempts"]}
        self.assertEqual(set(by_role), {"intended_next_hop", "source_off_index"})
        self.assertTrue(by_role["intended_next_hop"]["physically_decoded"])
        self.assertTrue(by_role["source_off_index"]["physically_decoded"])
        self.assertFalse(by_role["source_off_index"]["protocol_path_index_matches"])
        self.assertEqual(result["summary"]["source_off_index_decodes"], 1)
        self.assertEqual(by_role["intended_next_hop"]["outcome"], "decoded")
        self.assertEqual(by_role["intended_next_hop"]["ack_path"], [0, 1, 2])
        self.assertAlmostEqual(
            by_role["intended_next_hop"]["signal_power_dbm"],
            sim.rx_power_dbm(2, 1, when=ack.start),
        )
        self.assertEqual(by_role["intended_next_hop"]["interfering_powers_dbm"], [])
        self.assertIsNotNone(by_role["intended_next_hop"]["model_sinr_db"])
        self.assertGreater(by_role["intended_next_hop"]["model_prr"], 0.0)

    def test_intended_hop_half_duplex_failure_uses_actual_overlap(self) -> None:
        sim = make_sim()
        ack = ack_tx()
        own = Transmission(2, 1, Packet(
            kind="FLOOD", flow_id=7, origin=0, final_dst=2, ttl=2,
            created_at=0.0, protocol="meshecho-dhr-flood-ack-delay",
            request_id=7,
        ), 5.05, 5.15)
        sim.transmissions = [ack, own]
        sim.tx_history = [ack, own]
        sim.tx_commitment_times = {1: 5.0, 2: 5.05}

        self.assertIsNone(sim.try_receive(ack, 1))
        sim.try_receive(ack, 0)
        result = analyze_ack_receptions(sim, [flow_row()], observation_cutoff_s=30.0)

        intended = next(item for item in result["attempts"]
                        if item["role"] == "intended_next_hop")
        self.assertEqual(intended["failure_cause"]["class"], "half_duplex")
        self.assertEqual(intended["outcome"], "half_duplex")
        self.assertIsNone(intended["model_prr"])
        self.assertEqual(
            [tx["tx_id"] for tx in intended["failure_cause"]["receiver_transmissions"]],
            [2],
        )

    def test_capture_failure_uses_existing_interferer_power(self) -> None:
        sim = make_sim()
        ack = ack_tx()
        interferer = Transmission(2, 0, Packet(
            kind="FLOOD", flow_id=8, origin=0, final_dst=2, ttl=2,
            created_at=0.0, protocol="meshecho-dhr-flood-ack-delay",
            request_id=8,
        ), 5.02, 5.12)
        sim.transmissions = [ack, interferer]
        sim.tx_history = [ack, interferer]
        sim.tx_commitment_times = {1: 5.0, 2: 5.02}

        self.assertIsNone(sim.try_receive(ack, 1))
        sim.try_receive(ack, 0)
        result = analyze_ack_receptions(sim, [flow_row()], observation_cutoff_s=30.0)

        intended = next(item for item in result["attempts"]
                        if item["role"] == "intended_next_hop")
        self.assertEqual(intended["failure_cause"]["class"], "capture_collision")
        self.assertEqual(
            [tx["tx_id"] for tx in intended["failure_cause"]["interfering_transmissions"]],
            [2],
        )

    def test_probabilistic_failure_diagnosis_draws_no_additional_randomness(self) -> None:
        sim = make_sim()
        sim.nodes[1].x = 100000.0
        ack = ack_tx()
        sim.transmissions = [ack]
        sim.tx_history = [ack]
        sim.tx_commitment_times = {1: 5.0}

        self.assertIsNone(sim.try_receive(ack, 1))
        sim.try_receive(ack, 0)
        before = sim.channel_random.getstate()
        result = analyze_ack_receptions(sim, [flow_row()], observation_cutoff_s=30.0)

        intended = next(item for item in result["attempts"]
                        if item["role"] == "intended_next_hop")
        self.assertEqual(intended["failure_cause"]["class"],
                         "probabilistic_no_interference")
        self.assertEqual(sim.channel_random.getstate(), before)

    def test_late_decode_and_censored_receive_are_not_deadline_successes(self) -> None:
        ack = ack_tx(start=29.99, end=30.1)
        late = make_sim()
        late.transmissions = [ack]
        late.tx_history = [ack]
        late.tx_commitment_times = {1: 29.99}
        late.try_receive(ack, 1)
        late.try_receive(ack, 0)

        completed = analyze_ack_receptions(
            late, [flow_row(deadline=30.0)], observation_cutoff_s=31.0,
        )
        self.assertTrue(all(item["physically_decoded"] for item in completed["attempts"]))
        self.assertTrue(all(item["decoded_by_flow_deadline"] is False
                            for item in completed["attempts"]))

        censored = make_sim()
        censored.tx_history = [ack]
        result = analyze_ack_receptions(
            censored, [flow_row(deadline=30.0)], observation_cutoff_s=30.0,
        )
        self.assertTrue(all(item["observation_censored"] for item in result["attempts"]))
        self.assertTrue(all(item["physically_decoded"] is None
                            and item["failure_cause"] is None
                            for item in result["attempts"]))

    def test_off_index_candidate_requires_identity_marker_path_and_deadline(self) -> None:
        sim = make_sim()
        sim.metrics.register_flow(7, 0, 2, 0.0)
        sim.protocol.flow_data_actions[7] = "F"
        ack = ack_tx()
        sim.transmissions = [ack]
        sim.tx_history = [ack]
        sim.tx_commitment_times = {1: 5.0}
        sim.try_receive(ack, 1)
        sim.try_receive(ack, 0)

        result = analyze_ack_receptions(sim, [flow_row()], observation_cutoff_s=30.0)
        off_index = next(item for item in result["attempts"]
                         if item["role"] == "source_off_index")

        self.assertEqual(off_index["candidate_checks"], {
            "flow_identity": True,
            "destination_origin": True,
            "repair_marker": True,
            "path_continuity": True,
            "within_deadline": True,
            "not_already_acknowledged": True,
        })
        self.assertTrue(off_index["identity_valid_in_deadline_candidate"])

    def test_decoded_off_index_ack_with_wrong_identity_or_repair_is_not_candidate(self) -> None:
        sim = make_sim()
        sim.metrics.register_flow(7, 0, 2, 0.0)
        sim.protocol.flow_data_actions[7] = "F"
        bad = Transmission(
            1, 2, replace(ack_tx().packet, request_id=99, repair_index=2,
                          path=(0, 2, 1)), 5.0, 5.1,
        )
        sim.transmissions = [bad]
        sim.tx_history = [bad]
        sim.tx_commitment_times = {1: 5.0}

        self.assertIsNotNone(sim.try_receive(bad, 0))
        result = analyze_ack_receptions(
            sim, [flow_row()], observation_cutoff_s=30.0,
        )
        overheard = result["attempts"][0]

        self.assertTrue(overheard["physically_decoded"])
        self.assertFalse(overheard["candidate_checks"]["flow_identity"])
        self.assertFalse(overheard["candidate_checks"]["repair_marker"])
        self.assertFalse(overheard["candidate_checks"]["path_continuity"])
        self.assertFalse(overheard["identity_valid_in_deadline_candidate"])

    def test_parity_gate_checks_row_flows_actions_tx_and_both_rng_streams(self) -> None:
        stock = RunEvidence(
            row={"ack_by_deadline": 1, "scheduled_trace_sha256": "same"},
            flows=[{"flow_id": 7, "acked_at": 5.0}],
            actions=[{"event": "dhr_source_ack_rx", "accepted": True}],
            transmissions=[{"tx_id": 1, "packet": {"kind": "ACK"}}],
            random_state_sha256="protocol-rng",
            channel_random_state_sha256="channel-rng",
        )

        parity = require_stock_parity(stock, replace(stock))

        self.assertTrue(parity["exact"])
        self.assertEqual(parity["scheduled_trace_sha256"], "same")
        for changed in (
            replace(stock, row={"ack_by_deadline": 0}),
            replace(stock, flows=[{"flow_id": 7, "acked_at": None}]),
            replace(stock, actions=[]),
            replace(stock, transmissions=[]),
            replace(stock, random_state_sha256="other"),
            replace(stock, channel_random_state_sha256="other"),
        ):
            with self.subTest(changed=changed), self.assertRaises(AssertionError):
                require_stock_parity(stock, changed)

    def test_flood_candidate_uses_delivered_unacked_flow_denominator(self) -> None:
        sim = make_sim()
        sim.metrics.register_flow(7, 0, 2, 0.0)
        sim.protocol.flow_data_actions[7] = "F"
        ack = ack_tx()
        sim.transmissions = [ack]
        sim.tx_history = [ack]
        sim.tx_commitment_times = {1: 5.0}
        sim.try_receive(ack, 1)
        sim.try_receive(ack, 0)
        observed = analyze_ack_receptions(
            sim, [flow_row()], observation_cutoff_s=30.0,
        )
        ack_hops = {"missing_flows": [{
            "flow_id": 7,
            "ack_attempts": [{
                "trigger_packet_kind": "FLOOD", "repair_index": None,
                "ack_path_hops": 2, "reverse_hops": [{"tx_id": 1}],
                "first_unphysical_reverse_hop": None,
                "termination": "decoded_no_matching_forward",
            }],
        }]}

        assessed = assess_flows(
            [flow_row()], observed["attempts"], ack_hops, [ack],
            observation_cutoff_s=30.0,
        )

        self.assertEqual(assessed["summary"]["scheduled_unicast_flows"], 1)
        self.assertEqual(assessed["summary"]["delivered_unacked_flood_flows"], 1)
        self.assertEqual(assessed["summary"]["valid_off_index_flood_candidates"], 1)
        self.assertEqual(assessed["flows"][0]["flood_stage"], "initial_f")
        self.assertEqual(assessed["flows"][0]["flood_ack_path_hops"], [2])
        self.assertFalse(assessed["summary"]["candidate_gate_passed"])

        unrelated_final_hop = Transmission(
            2, 1, replace(ack.packet, path_index=0), 5.2, 5.3,
        )
        reassessed = assess_flows(
            [flow_row()], observed["attempts"], ack_hops,
            [ack, unrelated_final_hop], observation_cutoff_s=30.0,
        )
        self.assertFalse(reassessed["flows"][0]["flood_ack_final_hop_tx"])

    def test_reserved_modes_and_nonoverwriting_hashed_artifacts(self) -> None:
        self.assertEqual(seeds_for_mode("smoke"), (39000,))
        self.assertEqual(seeds_for_mode("explore"), tuple(range(39001, 39021)))
        with self.assertRaises(ValueError):
            seeds_for_mode("holdout")
        report = {
            "mode": "smoke", "seeds": [39000],
            "protocol": "meshecho-dhr-flood-ack-delay",
            "case_sha256": "case-hash", "source_sha256": {"tool": "source-hash"},
            "application_deadline_s": 30.0, "drain_until_s": 630.0,
            "summary": {"scheduled_unicast_flows": 1,
                        "delivered_unacked_flows": 1,
                        "delivered_unacked_flood_flows": 1,
                        "valid_off_index_flood_candidates": 0},
            "runs": [{
                "seed": 39000,
                "row": {
                    "seed": 39000, "ack_by_deadline": 0,
                    "protocol": "meshecho-dhr-flood-ack-delay",
                    "case_config_sha256": "case-hash",
                    "application_deadline_s": 30.0,
                    "drain_until_s": 630.0,
                    "scheduled_unicast_flows": 1,
                    "scheduled_trace_sha256": "synthetic-trace",
                },
                "parity": {"exact": True},
                "summary": {
                    "scheduled_unicast_flows": 1,
                    "delivered_unacked_flows": 1,
                    "delivered_unacked_flood_flows": 1,
                },
                "flows": [{"flow_id": 7}],
                "attempts": [{"tx_id": 1, "flow_id": 7}],
                "actions": [{"event": "decision", "flow_id": 7}],
                "transmissions": [{"tx_id": 1, "packet": {"kind": "ACK"}}],
            }],
        }
        def digest(value):
            return hashlib.sha256(json.dumps(
                value, sort_keys=True, separators=(",", ":")
            ).encode("ascii")).hexdigest()
        report["runs"][0]["parity"].update({
            "full_row_sha256": digest(report["runs"][0]["row"]),
            "action_trace_sha256": digest(report["runs"][0]["actions"]),
            "full_tx_trace_sha256": digest(report["runs"][0]["transmissions"]),
        })
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "unique-diagnostic"
            paths = write_report(report, prefix)
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))

            self.assertEqual(set(manifest["artifact_sha256"]),
                             {"summary", "runs", "flows", "attempts",
                              "actions", "transmissions", "runs_csv"})
            for name, digest in manifest["artifact_sha256"].items():
                self.assertEqual(hashlib.sha256(paths[name].read_bytes()).hexdigest(),
                                 digest)
            self.assertTrue(manifest["parity_exact_all"])
            self.assertEqual(manifest["per_seed_denominators"]["39000"], {
                "scheduled_unicast_flows": 1,
                "delivered_unacked_flows": 1,
                "delivered_unacked_flood_flows": 1,
            })
            verified = validate_smoke_manifest(
                paths["manifest"], report["source_sha256"],
                report["case_sha256"], 30.0, 630.0,
            )
            self.assertEqual(verified["seeds"], [39000])
            with self.assertRaises(FileExistsError):
                write_report(report, prefix)
            original_manifest = paths["manifest"].read_bytes()
            manifest["per_seed_denominators"]["39000"]["scheduled_unicast_flows"] = 99
            paths["manifest"].write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(ValueError):
                validate_smoke_manifest(
                    paths["manifest"], report["source_sha256"],
                    report["case_sha256"], 30.0, 630.0,
                )
            paths["manifest"].write_bytes(original_manifest)
            with paths["attempts"].open("ab") as handle:
                handle.write(b"tampered\n")
            with self.assertRaises(ValueError):
                validate_smoke_manifest(
                    paths["manifest"], report["source_sha256"],
                    report["case_sha256"], 30.0, 630.0,
                )

    def test_capture_run_uses_existing_runner_without_new_radio_attempts(self) -> None:
        case = SrCase(key="synthetic", nodes=3, pair_mode="random", pair_count=0)
        created = []

        def fake_runner(given_case, protocol, seed, deadline_s):
            self.assertIs(given_case, case)
            self.assertEqual(protocol, "meshecho-dhr-flood-ack-delay")
            self.assertEqual((seed, deadline_s), (17, 30.0))
            sim = sr.RecordingSimulator(
                [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0), Node(2, 20.0, 0.0)],
                RadioConfig(sf=7, shadow_sigma_db=0.0),
                MeshEchoDHRDelayedAck(), seed=seed, max_hops=3,
            )
            created.append(sim)
            sim.tx_history = [ack_tx()]
            return SrRun({"scheduled_trace_sha256": "synthetic"}, [flow_row()], [])

        evidence, observed = capture_run(
            case, 17, DiagnosticSimulator, runner=fake_runner,
        )

        self.assertIs(observed, created[0])
        self.assertIsInstance(observed, DiagnosticSimulator)
        self.assertEqual(evidence.transmissions[0]["packet"]["kind"], "ACK")
        self.assertEqual(evidence.row["scheduled_trace_sha256"], "synthetic")
        self.assertEqual(observed.metrics.rx_success, 0)

    def test_run_diagnostic_requires_stock_parity_before_reporting(self) -> None:
        case = SrCase(key="synthetic", duration_s=0.0)
        sim = make_sim()
        ack = ack_tx()
        sim.tx_history = [ack]
        sim.transmissions = [ack]
        sim.tx_commitment_times = {1: 5.0}
        sim.try_receive(ack, 1)
        sim.try_receive(ack, 0)
        evidence = RunEvidence(
            row={"scheduled_trace_sha256": "same"}, flows=[flow_row()],
            actions=[], transmissions=[{"tx_id": 1, "packet": {"kind": "ACK"}}],
            random_state_sha256="rng", channel_random_state_sha256="channel",
        )
        used = []

        def matching_capture(given_case, seed, simulator_type, deadline_s):
            used.append(simulator_type)
            return evidence, sim

        result = run_diagnostic(
            17, case=case, capture=matching_capture,
        )

        self.assertEqual(used, [sr.RecordingSimulator, DiagnosticSimulator])
        self.assertTrue(result["parity"]["exact"])
        self.assertEqual(result["summary"]["scheduled_unicast_flows"], 1)
        self.assertEqual(len(result["attempts"]), 2)
        self.assertEqual(result["transmissions"], evidence.transmissions)
        self.assertEqual(result["actions"], evidence.actions)

        def diverging_capture(given_case, seed, simulator_type, deadline_s):
            if simulator_type is DiagnosticSimulator:
                return replace(evidence, transmissions=[]), sim
            return evidence, sim

        with self.assertRaises(AssertionError):
            run_diagnostic(17, case=case, capture=diverging_capture)

    def test_report_aggregates_frozen_cohort_without_running_the_simulator(self) -> None:
        case = SrCase(key="synthetic", duration_s=0.0)
        case_hash = hashlib.sha256(json.dumps(
            case.__dict__, sort_keys=True, separators=(",", ":")
        ).encode("ascii")).hexdigest()

        def digest(value):
            return hashlib.sha256(json.dumps(
                value, sort_keys=True, separators=(",", ":")
            ).encode("ascii")).hexdigest()

        def fake_diagnostic(seed, given_case, deadline_s):
            self.assertIs(given_case, case)
            self.assertEqual(deadline_s, 30.0)
            row = {
                "seed": seed, "protocol": "meshecho-dhr-flood-ack-delay",
                "case_config_sha256": case_hash,
                "application_deadline_s": 30.0, "drain_until_s": 30.0,
                "scheduled_unicast_flows": 2,
                "scheduled_trace_sha256": "synthetic-trace",
            }
            return {
                "seed": seed, "row": row,
                "parity": {
                    "exact": True,
                    "full_row_sha256": digest(row),
                    "action_trace_sha256": digest([]),
                    "full_tx_trace_sha256": digest([]),
                },
                "summary": {
                    "scheduled_unicast_flows": 2,
                    "ack_by_deadline": 1,
                    "delivery_by_deadline": 2,
                    "delivered_unacked_flows": 1,
                    "delivered_unacked_flood_flows": 1,
                    "valid_off_index_flood_candidates": 1,
                    "first_flood_ack_failure_classes": {"capture_collision": 1},
                },
                "flows": [{"flow_id": 1}, {"flow_id": 2}],
                "attempts": [], "actions": [], "transmissions": [],
            }

        report = run_report(
            seeds_for_mode("smoke"), case=case, mode="smoke",
            diagnose=fake_diagnostic,
        )

        self.assertEqual(report["summary"]["scheduled_unicast_flows"], 2)
        self.assertEqual(report["summary"]["valid_off_index_flood_candidates"], 1)
        self.assertIsNone(report["summary"]["candidate_gate_passed"])
        self.assertIn("lora_mesh_sim.py", report["source_sha256"])
        self.assertIn("tools/diagnose_delayed_ack_rx.py", report["source_sha256"])
        with self.assertRaises(ValueError):
            run_report((39001,), case=case, mode="explore", diagnose=fake_diagnostic)
        with self.assertRaises(ValueError):
            run_report(seeds_for_mode("explore"), case=case, mode="explore",
                       diagnose=fake_diagnostic)
        with tempfile.TemporaryDirectory() as directory:
            paths = write_report(report, Path(directory) / "synthetic-smoke")
            exploratory = run_report(
                seeds_for_mode("explore"), case=case, mode="explore",
                diagnose=fake_diagnostic, smoke_manifest_path=paths["manifest"],
            )
            self.assertEqual(exploratory["summary"]["delivered_unacked_flood_flows"], 20)
            self.assertEqual(exploratory["summary"]["valid_off_index_flood_candidates"], 20)
            self.assertTrue(exploratory["summary"]["candidate_gate_passed"])
            self.assertEqual(exploratory["smoke_manifest_sha256"],
                             hashlib.sha256(paths["manifest"].read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
