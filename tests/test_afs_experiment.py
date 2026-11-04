"""Prospective AFS component-runner contract, using synthetic evidence."""

import hashlib
import json
import unittest
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tools import run_afs_experiment as afs
from tools.run_sr_experiment import SR_CASES, SrCase


class AfsExperimentTest(unittest.TestCase):
    @staticmethod
    def tiny_case():
        return SrCase(
            key="tiny_random", nodes=2, area_m=1.0, duration_s=8.0,
            rate_per_min=60.0, pair_mode="random", pair_count=0,
            temporal_fading_sigma_db=0.0,
        )

    def synthetic_reserved_smoke_runs(self):
        case = SR_CASES["recurring_fading"]
        case_hash = hashlib.sha256(json.dumps(
            asdict(case), sort_keys=True, separators=(",", ":")
        ).encode("ascii")).hexdigest()
        runs = []
        for protocol in afs.ARMS:
            actual = afs.run_one_traced(self.tiny_case(), protocol, 7)
            row = {
                **actual.row, "case": case.key,
                "case_config_sha256": case_hash, "seed": 23000,
                "generation_horizon_s": 600.0, "drain_until_s": 630.0,
            }
            def relabel(records):
                return [{**item, "case": case.key, "seed": 23000}
                        for item in records]
            tx = relabel(actual.transmissions)
            row["full_tx_trace_sha256"] = afs.tx_trace_hash(tx)
            runs.append(afs.AfsRun(row, relabel(actual.flows),
                                   relabel(actual.actions), tx,
                                   relabel(actual.decodes)))
        return case, runs

    def synthetic_passing_development_runs(self):
        case, template = self.synthetic_reserved_smoke_runs()
        runs = []
        for seed in afs.seeds_for_split("development"):
            for source in template:
                row = {**source.row, "seed": seed}
                flows = [{**item, "seed": seed} for item in source.flows]
                actions = [{**item, "seed": seed} for item in source.actions]
                tx = [{**item, "seed": seed} for item in source.transmissions]
                decodes = [{**item, "seed": seed} for item in source.decodes]
                if row["protocol"] == afs.ARMS[0]:
                    removed = next(item for item in tx
                                   if item["packet"]["kind"] == "DATA")
                    tx.remove(removed)
                    row["windowed_tx_count"] -= 1
                    row["windowed_data_tx"] -= 1
                    row["whole_network_tx_airtime_s"] -= (
                        removed["end"] - removed["start"]
                    )
                    if seed <= 23020:
                        ack_tx = next(item for item in tx
                                      if item["packet"]["kind"] == "ACK")
                        ack = ack_tx["packet"]
                        for relay in range(3, 8):
                            when = ack_tx["end"]
                            handle_id = seed * 10 + relay
                            flood = {
                                **deepcopy(ack), "kind": "FLOOD",
                                "origin": ack["final_dst"],
                                "final_dst": ack["origin"],
                                "path": [ack["final_dst"], relay],
                                "path_index": 1, "ttl": 1,
                                "app_payload": True,
                            }
                            decodes.append({
                                "case": case.key, "protocol": afs.ARMS[0],
                                "seed": seed, "time": when,
                                "tx_id": ack_tx["tx_id"],
                                "flow_id": ack["flow_id"],
                                "receiver": relay,
                                "repair_index": ack["repair_index"],
                                "natural_destination_ack": True,
                                "off_path": True, "strict_pending": True,
                                "rx_sender": ack_tx["sender"],
                                "ack_packet": deepcopy(ack),
                                "pending_flood_packet": flood,
                                "pending_received_at": when - 0.1,
                                "record_handle_id": handle_id,
                                "mapped_handle_id": handle_id,
                                "pending_canceled": False,
                                "pending_committed": False,
                            })
                            event = {
                                "case": case.key, "protocol": afs.ARMS[0],
                                "seed": seed, "time": when,
                                "flow_id": ack["flow_id"], "relay": relay,
                                "repair_index": ack["repair_index"],
                            }
                            actions.extend(({**event, "event": "afs_opportunity"},
                                            {**event, "event": "afs_cancel"}))
                    row["physical_ack_decodes"] = len(decodes)
                    row["natural_ack_decodes"] = sum(
                        item["natural_destination_ack"] for item in decodes
                    )
                    row["offpath_natural_ack_decodes"] = sum(
                        item["natural_destination_ack"] and item["off_path"]
                        for item in decodes
                    )
                    row["strict_pending_ack_decodes"] = sum(
                        item["strict_pending"] for item in decodes
                    )
                    row["afs_opportunities"] = sum(
                        item.get("event") == "afs_opportunity" for item in actions
                    )
                    row["afs_cancellations"] = sum(
                        item.get("event") == "afs_cancel" for item in actions
                    )
                    row["afs_initial_f_cancellations"] = row["afs_cancellations"]
                row["full_tx_trace_sha256"] = afs.tx_trace_hash(tx)
                runs.append(afs.AfsRun(row, flows, actions, tx, decodes))
        return case, runs

    def test_reserved_splits_and_holdout_require_a_passing_development_manifest(self):
        self.assertEqual(afs.seeds_for_split("smoke"), (23000,))
        self.assertEqual(afs.seeds_for_split("development"), tuple(range(23001, 23041)))
        self.assertEqual(afs.seeds_for_split("holdout"), tuple(range(24001, 24041)))
        with TemporaryDirectory() as directory:
            with patch.object(afs, "run_one_traced") as simulate:
                with self.assertRaisesRegex(ValueError, "development manifest"):
                    afs.run_experiment("holdout", Path(directory) / "holdout")
                with self.assertRaisesRegex(ValueError, "smoke manifest"):
                    afs.run_experiment("development", Path(directory) / "development")
            simulate.assert_not_called()

    def test_traced_no_cancel_run_mechanically_matches_fixed_f(self):
        case = self.tiny_case()
        shadow = afs.run_one_traced(case, "meshecho-afs-nocancel", 7)
        fixed_f = afs.run_one_traced(case, "meshecho-dhr-flood", 7)

        afs.require_mechanical_parity(shadow, fixed_f)
        self.assertEqual(shadow.row["full_tx_trace_sha256"],
                         fixed_f.row["full_tx_trace_sha256"])
        self.assertGreater(shadow.row["physical_ack_decodes"], 0)

    def test_development_gate_uses_paired_bounds_and_actual_cancel_exposure(self):
        rows, actions, decodes = [], [], []
        for seed in afs.seeds_for_split("development"):
            for protocol in afs.ARMS:
                rows.append({
                    "case": "recurring_fading", "case_config_sha256": "fixed",
                    "seed": seed, "protocol": protocol,
                    "seed_split": "development",
                    "scheduled_trace_sha256": f"trace-{seed}",
                    "scheduled_unicast_flows": 10,
                    "application_deadline_s": 30.0,
                    "ack_pdr_deadline": 0.9,
                    "destination_pdr_deadline": 1.0,
                    "whole_network_tx_airtime_s": (
                        90.0 if protocol == afs.ARMS[0] else 100.0
                    ),
                })
            if seed < 23021:
                for relay in range(5):
                    event = {
                        "case": "recurring_fading", "protocol": afs.ARMS[0],
                        "seed": seed, "event": "afs_cancel", "time": float(relay),
                        "flow_id": relay + 1, "relay": relay,
                        "repair_index": None,
                    }
                    actions.append(event)
                    actions.append({**event, "event": "afs_opportunity"})
                    decodes.append({
                        "case": "recurring_fading", "protocol": afs.ARMS[0],
                        "seed": seed, "time": float(relay),
                        "flow_id": relay + 1, "receiver": relay,
                        "repair_index": None, "strict_pending": True,
                    })

        comparisons, exposure = afs.evaluate_afs(rows, actions, decodes,
                                                   "development")
        primary = next(item for item in comparisons
                       if item["comparator"] == afs.ARMS[1])
        self.assertTrue(primary["afs_primary_gate"])
        self.assertEqual(exposure["cancel_events"], 100)
        self.assertEqual(exposure["cancel_seeds"], 20)

        comparisons, _ = afs.evaluate_afs(rows, actions[:198], decodes,
                                          "development")
        primary = next(item for item in comparisons
                       if item["comparator"] == afs.ARMS[1])
        self.assertFalse(primary["afs_primary_gate"])

    def test_cancellation_needs_valid_marker_and_uncommitted_ack_witness(self):
        cancel = {
            "protocol": afs.ARMS[0], "seed": 23001,
            "event": "afs_cancel", "time": 1.0,
            "flow_id": 7, "relay": 3, "repair_index": 2,
        }
        opportunity = {**cancel, "event": "afs_opportunity"}
        decode = {
            "protocol": afs.ARMS[0], "seed": 23001, "time": 1.0,
            "flow_id": 7, "receiver": 3, "repair_index": 2,
            "strict_pending": False,
        }
        with self.assertRaisesRegex(ValueError, "strict physical ACK witness"):
            afs.cancellation_exposure([cancel, opportunity], [decode])
        with self.assertRaisesRegex(ValueError, "marker"):
            afs.cancellation_exposure(
                [{**cancel, "repair_index": 1}, opportunity],
                [{**decode, "strict_pending": True}],
            )

    def test_artifacts_hash_every_input_and_raw_evidence_file(self):
        case = self.tiny_case()
        runs = [afs.run_one_traced(case, protocol, 7) for protocol in afs.ARMS]
        with TemporaryDirectory() as directory:
            prefix = Path(directory) / "smoke"
            paths = afs.write_artifacts(prefix, case, "smoke", runs,
                                        afs.input_hashes())
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
            for source, digest in manifest["source_sha256"].items():
                self.assertEqual(
                    digest,
                    hashlib.sha256((afs.ROOT / source).read_bytes()).hexdigest(),
                )
            for key, digest in manifest["artifact_sha256"].items():
                self.assertEqual(digest,
                                 hashlib.sha256(paths[key].read_bytes()).hexdigest())
            self.assertIn("tools/run_afs_experiment.py", manifest["source_sha256"])
            self.assertIn("tests/test_afs_experiment.py", manifest["source_sha256"])
            self.assertIn("tests/test_meshecho_afs.py", manifest["source_sha256"])
            self.assertIn("docs/research/meshecho_ack_terminated_flood_design.md",
                          manifest["source_sha256"])
            self.assertIn("tx", manifest["artifact_sha256"])
            self.assertIn("decodes", manifest["artifact_sha256"])

    def test_saved_smoke_rechecks_artifacts_with_mocked_replay(self):
        case, runs = self.synthetic_reserved_smoke_runs()
        by_key = {(run.row["seed"], run.row["protocol"]): run for run in runs}
        with TemporaryDirectory() as directory:
            paths = afs.write_artifacts(Path(directory) / "smoke", case,
                                        "smoke", runs, afs.input_hashes())
            with patch.object(afs, "run_one_traced",
                              side_effect=lambda _, protocol, seed:
                              by_key[(seed, protocol)]) as rerun:
                afs.validate_manifest(paths["manifest"], "smoke",
                                      afs.input_hashes())
            self.assertEqual(rerun.call_count, len(afs.ARMS))
            paired = paths["paired"]
            text = paired.read_text(encoding="utf-8")
            paired.write_text(text.replace("meshecho-afs-nocancel",
                                           "forged-comparator"), encoding="utf-8")
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
            manifest["artifact_sha256"]["paired"] = hashlib.sha256(
                paired.read_bytes()).hexdigest()
            paths["manifest"].write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "paired evidence"):
                afs.validate_manifest(paths["manifest"], "smoke",
                                      afs.input_hashes())

    def test_saved_decode_cannot_claim_strict_pending_without_local_witness(self):
        case, runs = self.synthetic_reserved_smoke_runs()
        candidate = runs[0]
        self.assertTrue(candidate.decodes)
        claimed = [{**item} for item in candidate.decodes]
        claimed[0]["strict_pending"] = True
        row = {**candidate.row, "strict_pending_ack_decodes": 1}
        runs[0] = afs.AfsRun(row, candidate.flows, candidate.actions,
                             candidate.transmissions, claimed)
        with TemporaryDirectory() as directory:
            paths = afs.write_artifacts(Path(directory) / "smoke", case,
                                        "smoke", runs, afs.input_hashes())
            with self.assertRaisesRegex(ValueError, "decode witness"):
                afs.validate_manifest(paths["manifest"], "smoke",
                                      afs.input_hashes())

    def test_saved_deadline_success_must_agree_with_flow_timestamps(self):
        case, runs = self.synthetic_reserved_smoke_runs()
        candidate = runs[0]
        flows = [{**item} for item in candidate.flows]
        flows[0]["ack_by_deadline"] = not flows[0]["ack_by_deadline"]
        count = sum(item["ack_by_deadline"] for item in flows)
        row = {**candidate.row, "ack_by_deadline": count,
               "ack_pdr_deadline": count / len(flows)}
        runs[0] = afs.AfsRun(row, flows, candidate.actions,
                             candidate.transmissions, candidate.decodes)
        with TemporaryDirectory() as directory:
            paths = afs.write_artifacts(Path(directory) / "smoke", case,
                                        "smoke", runs, afs.input_hashes())
            with self.assertRaisesRegex(ValueError, "deadline evidence"):
                afs.validate_manifest(paths["manifest"], "smoke",
                                      afs.input_hashes())

    def test_saved_tx_duration_must_match_frozen_phy_packet_toa(self):
        case, runs = self.synthetic_reserved_smoke_runs()
        candidate = runs[0]
        tx = [{**item} for item in candidate.transmissions]
        target = next(item for item in tx if item["packet"]["kind"] != "ACK")
        target["end"] += 0.001
        row = {
            **candidate.row,
            "whole_network_tx_airtime_s": (
                candidate.row["whole_network_tx_airtime_s"] + 0.001
            ),
            "full_tx_trace_sha256": afs.tx_trace_hash(tx),
        }
        runs[0] = afs.AfsRun(row, candidate.flows, candidate.actions,
                             tx, candidate.decodes)
        with TemporaryDirectory() as directory:
            paths = afs.write_artifacts(Path(directory) / "smoke", case,
                                        "smoke", runs, afs.input_hashes())
            with self.assertRaisesRegex(ValueError, "packet ToA"):
                afs.validate_manifest(paths["manifest"], "smoke",
                                      afs.input_hashes())

    def test_smoke_runs_only_reserved_seed_and_holdout_rejects_smoke_manifest(self):
        case, runs = self.synthetic_reserved_smoke_runs()
        by_protocol = {run.row["protocol"]: run for run in runs}
        with TemporaryDirectory() as directory:
            prefix = Path(directory) / "smoke"
            with patch.object(afs, "run_one_traced",
                              side_effect=lambda _, protocol, __:
                              by_protocol[protocol]) as simulate:
                paths = afs.run_experiment("smoke", prefix)
            self.assertEqual(simulate.call_count, 3)
            self.assertEqual([call.args[1:] for call in simulate.call_args_list],
                             [(protocol, 23000) for protocol in afs.ARMS])
            self.assertEqual(simulate.call_args_list[0].args[0], case)
            self.assertEqual(json.loads(paths["manifest"].read_text())["seeds"],
                             [23000])
            with patch.object(afs, "run_one_traced") as simulate:
                with self.assertRaisesRegex(ValueError, "frozen configuration"):
                    afs.run_experiment(
                        "holdout", Path(directory) / "holdout",
                        development_manifest=paths["manifest"],
                    )
                simulate.assert_not_called()

    def test_saved_development_structural_validation_with_mocked_replay(self):
        case, runs = self.synthetic_passing_development_runs()
        by_key = {(run.row["seed"], run.row["protocol"]): run for run in runs}
        with TemporaryDirectory() as directory:
            paths = afs.write_artifacts(Path(directory) / "development", case,
                                        "development", runs, afs.input_hashes())
            manifest = json.loads(paths["manifest"].read_text())
            self.assertTrue(manifest["afs_development_open_gate"])
            self.assertEqual(manifest["afs_exposure"]["cancel_events"], 100)
            with patch.object(afs, "run_one_traced",
                              side_effect=lambda _, protocol, seed:
                              by_key[(seed, protocol)]) as rerun:
                afs.validate_manifest(paths["manifest"], "development",
                                      afs.input_hashes())
            self.assertEqual(rerun.call_count,
                             len(afs.seeds_for_split("development")) * len(afs.ARMS))

    def test_pending_record_received_after_ack_is_not_a_strict_witness(self):
        case, runs = self.synthetic_passing_development_runs()
        candidate = runs[0]
        decode = next(item for item in candidate.decodes
                      if item["strict_pending"])
        future_record = {**decode, "pending_received_at": decode["time"] + 1.0}
        tx_by_id = {item["tx_id"]: item for item in candidate.transmissions}
        with self.assertRaisesRegex(ValueError, "decode witness"):
            afs.reconstruct_decode_witness(future_record, tx_by_id, case.max_hops)

    def test_fabricated_cancellations_fail_deterministic_replay(self):
        case, fabricated = self.synthetic_passing_development_runs()
        _, template = self.synthetic_reserved_smoke_runs()
        baseline = template[0]
        seed = afs.seeds_for_split("development")[0]
        def relabel(records):
            return [{**item, "seed": seed} for item in records]
        tx = relabel(baseline.transmissions)
        replay = afs.AfsRun(
            {**baseline.row, "seed": seed,
             "full_tx_trace_sha256": afs.tx_trace_hash(tx)},
            relabel(baseline.flows), relabel(baseline.actions), tx,
            relabel(baseline.decodes),
        )
        with TemporaryDirectory() as directory:
            paths = afs.write_artifacts(Path(directory) / "development", case,
                                        "development", fabricated,
                                        afs.input_hashes())
            with patch.object(afs, "run_one_traced", return_value=replay) as rerun:
                with self.assertRaisesRegex(ValueError, "replay evidence"):
                    afs.validate_manifest(paths["manifest"], "development",
                                          afs.input_hashes())
                rerun.assert_called_once_with(case, afs.ARMS[0], seed)

    def test_saved_ack_decode_cannot_repeat_same_tx_and_receiver(self):
        case, runs = self.synthetic_reserved_smoke_runs()
        candidate = runs[0]
        repeated = deepcopy(candidate.decodes[0])
        decodes = candidate.decodes + [repeated]
        row = {
            **candidate.row,
            "physical_ack_decodes": len(decodes),
            "natural_ack_decodes": sum(item["natural_destination_ack"]
                                       for item in decodes),
            "offpath_natural_ack_decodes": sum(
                item["natural_destination_ack"] and item["off_path"]
                for item in decodes
            ),
            "strict_pending_ack_decodes": sum(item["strict_pending"]
                                              for item in decodes),
        }
        runs[0] = afs.AfsRun(row, candidate.flows, candidate.actions,
                             candidate.transmissions, decodes)
        by_key = {(run.row["seed"], run.row["protocol"]): run for run in runs}
        with TemporaryDirectory() as directory:
            paths = afs.write_artifacts(Path(directory) / "smoke", case,
                                        "smoke", runs, afs.input_hashes())
            with patch.object(afs, "run_one_traced",
                              side_effect=lambda _, protocol, seed:
                              by_key[(seed, protocol)]):
                with self.assertRaisesRegex(ValueError, "duplicate physical ACK decode"):
                    afs.validate_manifest(paths["manifest"], "smoke",
                                          afs.input_hashes())

    def test_three_node_recorder_links_real_cancellations_to_ack_decodes(self):
        case = SrCase(
            key="tiny_three", nodes=3, area_m=1.0, duration_s=8.0,
            rate_per_min=60.0, pair_mode="random", pair_count=0,
            temporal_fading_sigma_db=0.0,
        )
        run = afs.run_one_traced(case, afs.ARMS[0], 7)
        self.assertGreater(run.row["afs_cancellations"], 0)
        tx_by_id = {item["tx_id"]: item for item in run.transmissions}
        strict = [item for item in run.decodes if item["strict_pending"]]
        self.assertGreaterEqual(len(strict), run.row["afs_cancellations"])
        for item in strict:
            self.assertEqual(
                afs.reconstruct_decode_witness(
                    json.loads(json.dumps(item)),
                    {key: json.loads(json.dumps(value))
                     for key, value in tx_by_id.items()},
                    case.max_hops,
                ),
                (True, True, True),
            )
        exposure = afs.cancellation_exposure(run.actions, run.decodes)
        self.assertEqual(exposure["cancel_events"], run.row["afs_cancellations"])

    def test_three_node_replay_preserves_pending_status_across_fresh_runs(self):
        case = SrCase(
            key="tiny_three", nodes=3, area_m=1.0, duration_s=8.0,
            rate_per_min=60.0, pair_mode="random", pair_count=0,
            temporal_fading_sigma_db=0.0,
        )
        original = afs.run_one_traced(case, afs.ARMS[0], 7)
        rerun = afs.run_one_traced(case, afs.ARMS[0], 7)
        saved_records = json.loads(json.dumps([
            original.flows, original.actions,
            original.transmissions, original.decodes,
        ]))
        saved_row = {key: "" if value is None else str(value)
                     for key, value in original.row.items()}
        saved = afs.AfsRun(saved_row, *saved_records)
        self.assertTrue(afs.replay_matches_saved(rerun, saved))
        strict = next(item for item in saved.decodes if item["strict_pending"])
        strict["pending_committed"] = True
        self.assertFalse(afs.replay_matches_saved(rerun, saved))


if __name__ == "__main__":
    unittest.main()
