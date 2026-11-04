"""Fixed-delay ACK control runner tests using only tiny or synthetic data."""

import csv
import unittest
from dataclasses import replace
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tools import run_delayed_ack_control as control
from tools.run_sr_experiment import SrCase


class DelayedAckControlRunnerTest(unittest.TestCase):
    @staticmethod
    def tiny_case():
        return SrCase(
            key="tiny_random", nodes=2, area_m=1.0, duration_s=8.0,
            rate_per_min=60.0, pair_mode="random", pair_count=0,
            temporal_fading_sigma_db=0.0,
        )

    @staticmethod
    def _unit_artifacts(prefix, case):
        pairs = [
            (control.run_one_traced(case, arm, 7),
             control.run_one_extended(case, arm, 7))
            for arm in control.ARMS
        ]
        stock = {7: control.run_one_stock(case, control.IMMEDIATE, 7)}
        return control.write_artifacts(
            prefix, case, "unit", pairs, stock, control.input_hashes()
        )

    @staticmethod
    def _read_jsonl(path):
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]

    @staticmethod
    def _write_jsonl(path, records):
        path.write_text("".join(json.dumps(item, sort_keys=True,
                                       separators=(",", ":")) + "\n"
                                for item in records), encoding="utf-8")

    @staticmethod
    def _rewrite_csv(path, rows):
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    @staticmethod
    def _rehash_manifest(paths):
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
        for key in manifest["artifact_sha256"]:
            manifest["artifact_sha256"][key] = hashlib.sha256(
                paths[key].read_bytes()
            ).hexdigest()
        paths["manifest"].write_text(json.dumps(manifest, sort_keys=True,
                                                indent=2) + "\n", encoding="utf-8")

    def test_frozen_seed_splits_and_explore_requires_smoke(self):
        self.assertEqual(control.seeds_for_split("smoke"), (38000,))
        self.assertEqual(control.seeds_for_split("explore"), tuple(range(38001, 38021)))
        with self.assertRaises(ValueError):
            control.seeds_for_split("development")
        with TemporaryDirectory() as directory, patch.object(
            control, "run_one_traced"
        ) as simulate:
            with self.assertRaisesRegex(ValueError, "smoke manifest"):
                control.run_experiment("explore", Path(directory) / "explore")
            simulate.assert_not_called()

    def test_cli_help_works_as_a_direct_script_without_running_seeds(self):
        result = subprocess.run(
            [sys.executable, str(control.ROOT / "tools/run_delayed_ack_control.py"),
             "--help"],
            cwd=control.ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--smoke-manifest", result.stdout)

    def test_instrumented_immediate_arm_exactly_matches_stock_sr(self):
        case = self.tiny_case()
        traced = control.run_one_traced(case, control.IMMEDIATE, 7)
        stock = control.run_one_stock(case, control.IMMEDIATE, 7)
        control.require_stock_parity(traced, stock)
        self.assertEqual(traced.transmissions, stock.transmissions)
        self.assertTrue(traced.transmissions)

    def test_first_flood_receipt_is_linked_to_actual_destination_ack_tx(self):
        run = control.run_one_traced(self.tiny_case(), control.IMMEDIATE, 7)
        per_flow = control.flow_records(run)
        flood_flows = [item for item in per_flow
                       if item["first_flood_decode_at"] is not None]
        self.assertTrue(flood_flows)
        for flow in flood_flows:
            self.assertIsNotNone(flow["first_flood_tx_id"])
            self.assertIsNotNone(flow["first_flood_ack_tx_start_at"])
            self.assertGreaterEqual(flow["first_flood_ack_tx_start_at"],
                                    flow["first_flood_decode_at"])
            matching_tx = [
                tx for tx in run.transmissions
                if tx["tx_id"] == flow["first_flood_tx_id"]
            ]
            self.assertEqual(len(matching_tx), 1)
            self.assertEqual(matching_tx[0]["packet"]["kind"], "FLOOD")

    def test_real_tiny_delayed_arm_waits_two_seconds_after_flood_decode(self):
        run = control.run_one_traced(self.tiny_case(), control.DELAYED, 7)
        flood_flows = [flow for flow in control.flow_records(run)
                       if flow["first_flood_decode_at"] is not None]
        self.assertTrue(flood_flows)
        for flow in flood_flows:
            self.assertIsNotNone(flow["first_flood_ack_tx_start_at"])
            self.assertGreaterEqual(
                flow["first_flood_ack_tx_start_at"]
                - flow["first_flood_decode_at"], 2.0 - 1e-9,
            )

    def test_first_flood_ack_matching_ignores_earlier_same_key_ack(self):
        sample = control.run_one_traced(self.tiny_case(), control.IMMEDIATE, 7)
        receipt = sample.flood_receipts[0]
        ack = next(tx for tx in sample.transmissions
                   if tx["packet"]["kind"] == "ACK"
                   and tx["packet"]["flow_id"] == receipt["flow_id"]
                   and tuple(tx["packet"]["path"]) == tuple(receipt["path"])
                   and tx["packet"]["repair_index"] == receipt["repair_index"]
                   and tx["sender"] == tx["packet"]["origin"])
        before = {**ack, "tx_id": 9000,
                  "start": receipt["decode_at"] - 1.0,
                  "end": receipt["decode_at"] - 0.9}
        after = {**ack, "tx_id": 9001,
                 "start": receipt["decode_at"] + 2.0,
                 "end": receipt["decode_at"] + 2.1}
        fake = replace(sample, transmissions=[before, after])
        flow = next(item for item in control.flow_records(fake)
                    if item["flow_id"] == receipt["flow_id"])
        self.assertEqual(flow["first_flood_ack_tx_id"], 9001)

    def test_symmetric_extended_replay_has_exact_primary_tx_prefix(self):
        case = self.tiny_case()
        primary = control.run_one_traced(case, control.IMMEDIATE, 7)
        extended = control.run_one_extended(case, control.IMMEDIATE, 7)
        control.require_extended_prefix(primary, extended)
        sensitivity = control.extended_sensitivity(primary, extended, 38.0, 68.0)
        self.assertEqual(sensitivity["post_cutoff_ack_tx"], 0)
        self.assertGreaterEqual(sensitivity["extended_airtime_s"],
                                primary.row["whole_network_tx_airtime_s"])
        altered = replace(extended, row={
            **extended.row, "scheduled_trace_sha256": "wrong-trace"
        })
        with self.assertRaisesRegex(ValueError, "extended replay"):
            control.require_extended_prefix(primary, altered)

    def test_extended_replay_charges_first_flood_ack_starting_after_630(self):
        case = self.tiny_case()
        sample = control.run_one_traced(case, control.IMMEDIATE, 7)
        ack = next(tx for tx in sample.transmissions
                   if tx["packet"]["kind"] == "ACK"
                   and tx["sender"] == tx["packet"]["origin"])
        first = {
            "flow_id": ack["packet"]["flow_id"], "decode_at": 629.5,
            "tx_id": 1, "path": ack["packet"]["path"],
            "repair_index": ack["packet"]["repair_index"],
        }
        after = {**ack, "tx_id": 2, "start": 631.5, "end": 631.7}
        primary = replace(sample, transmissions=[], flood_receipts=[first])
        extended = replace(primary, transmissions=[after])
        result = control.extended_sensitivity(primary, extended, 630.0, 660.0)
        self.assertEqual(result["pending_first_flood_ack_at_cutoff"], 1)
        self.assertEqual(result["post_cutoff_ack_tx"], 1)
        self.assertAlmostEqual(result["post_cutoff_airtime_s"], 0.2)

    def test_paired_seed_rows_and_intervals_reject_trace_mismatch(self):
        rows = []
        for seed in (1, 2):
            for protocol in control.ARMS:
                delayed = protocol == control.DELAYED
                rows.append({
                    "case": "synthetic", "case_config_sha256": "same",
                    "seed": seed, "protocol": protocol,
                    "scheduled_trace_sha256": f"trace-{seed}",
                    "scheduled_unicast_flows": 10,
                    "application_deadline_s": 30.0,
                    "ack_pdr_deadline": (0.8 if delayed else 0.7),
                    "destination_pdr_deadline": (0.9 if delayed else 0.8),
                    "whole_network_tx_airtime_s": (90.0 if delayed else 100.0),
                    "extended_airtime_s": (91.0 if delayed else 101.0),
                    "collision_failures": (5 if delayed else 7),
                    "half_duplex_failures": (3 if delayed else 4),
                    "mean_completion_delay_capped_s": (8.0 if delayed else 9.0),
                })
        per_seed, paired = control.summarize_pairs(rows)
        self.assertEqual(len(per_seed), 2)
        self.assertAlmostEqual(per_seed[0]["ack_pdr_gain"], 0.1)
        self.assertAlmostEqual(per_seed[0]["relative_airtime_cost"], -0.1)
        self.assertAlmostEqual(paired["ack_pdr_gain"], 0.1)
        self.assertAlmostEqual(paired["ack_pdr_ci95_low"], 0.1)
        self.assertAlmostEqual(paired["extended_relative_airtime_cost"],
                               -10.0 / 101.0)
        rows[0]["scheduled_trace_sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "trace"):
            control.summarize_pairs(rows)

    def test_run_row_hashes_complete_evidence_and_records_extended_cost(self):
        case = self.tiny_case()
        primary = control.run_one_traced(case, control.IMMEDIATE, 7)
        extended = control.run_one_extended(case, control.IMMEDIATE, 7)
        row = control.run_row(primary, extended, case.duration_s + 30.0)
        expected_tx_hash = hashlib.sha256(json.dumps(
            primary.transmissions, sort_keys=True, separators=(",", ":")
        ).encode("ascii")).hexdigest()
        self.assertEqual(row["full_tx_trace_sha256"], expected_tx_hash)
        self.assertEqual(len(row["source_action_trace_sha256"]), 64)
        self.assertEqual(len(row["extended_tx_trace_sha256"]), 64)
        self.assertEqual(row["primary_future_start_tx"], 0)
        self.assertGreaterEqual(row["half_duplex_failures"], 0)
        self.assertEqual(row["half_duplex_failures"],
                         control.count_half_duplex_from_tx(
                             primary.transmissions, case.nodes,
                             case.duration_s + 30.0))
        self.assertGreaterEqual(row["extended_airtime_s"],
                                row["whole_network_tx_airtime_s"])

    def test_half_duplex_is_recomputed_from_overlapping_physical_tx(self):
        tx = [
            {"sender": 0, "start": 0.0, "end": 2.0},
            {"sender": 1, "start": 1.0, "end": 3.0},
        ]
        self.assertEqual(control.count_half_duplex_from_tx(tx, 2, 3.0), 2)
        self.assertEqual(control.count_half_duplex_from_tx(tx, 2, 1.0), 0)

    def test_artifacts_hash_inputs_and_raw_evidence_without_overwrite(self):
        case = self.tiny_case()
        pairs = [
            (control.run_one_traced(case, arm, 7),
             control.run_one_extended(case, arm, 7))
            for arm in control.ARMS
        ]
        stock = {7: control.run_one_stock(case, control.IMMEDIATE, 7)}
        with TemporaryDirectory() as directory:
            prefix = Path(directory) / "unit"
            paths = control.write_artifacts(
                prefix, case, "unit", pairs, stock, control.input_hashes()
            )
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
            self.assertTrue(manifest["stock_fixed_f_parity"])
            self.assertEqual(manifest["runs"], 2)
            self.assertIn("extended_tx", manifest["artifact_sha256"])
            self.assertIn("per_seed", manifest["artifact_sha256"])
            for name, digest in manifest["source_sha256"].items():
                self.assertEqual(digest, hashlib.sha256(
                    (control.ROOT / name).read_bytes()
                ).hexdigest())
            for key, digest in manifest["artifact_sha256"].items():
                self.assertEqual(digest, hashlib.sha256(paths[key].read_bytes()).hexdigest())
            control.validate_manifest(
                paths["manifest"], "unit", control.input_hashes(),
                case=case, seeds=(7,), strict_replay=True,
            )
            with self.assertRaises(FileExistsError):
                control.write_artifacts(
                    prefix, case, "unit", pairs, stock, control.input_hashes()
                )
            paths["tx"].write_text(paths["tx"].read_text(encoding="utf-8") + "\n",
                                   encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "hash"):
                control.validate_manifest(
                    paths["manifest"], "unit", control.input_hashes(),
                    case=case, seeds=(7,),
                )

    def test_manifest_flags_post_cutoff_relay_tx_outside_primary_window(self):
        case = self.tiny_case()
        pairs = [
            (control.run_one_traced(case, arm, 7),
             control.run_one_extended(case, arm, 7))
            for arm in control.ARMS
        ]
        primary, extended = pairs[0]
        self.assertEqual(control.run_row(primary, extended, 38.0)["post_cutoff_tx"], 0)
        late = {**extended.transmissions[-1],
                "tx_id": max(item["tx_id"] for item in extended.transmissions) + 1,
                "start": 39.0, "end": 39.1}
        pairs[0] = (primary, replace(
            extended, transmissions=extended.transmissions + [late]
        ))
        stock = {7: control.run_one_stock(case, control.IMMEDIATE, 7)}
        with TemporaryDirectory() as directory:
            paths = control.write_artifacts(
                Path(directory) / "tail", case, "unit", pairs, stock,
                control.input_hashes(),
            )
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
            self.assertTrue(manifest["primary_cost_window_limited"])
            self.assertIn("bounded", manifest["extended_airtime_scope"])
            control.validate_manifest(paths["manifest"], "unit", control.input_hashes(),
                                      case=case, seeds=(7,))
            manifest["primary_cost_window_limited"] = False
            paths["manifest"].write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cost window"):
                control.validate_manifest(
                    paths["manifest"], "unit", control.input_hashes(),
                    case=case, seeds=(7,),
                )

    def test_validator_rejects_rehashed_receipt_without_destination_rx_action(self):
        case = self.tiny_case()
        with TemporaryDirectory() as directory:
            paths = self._unit_artifacts(Path(directory) / "action", case)
            receipt = next(item for item in self._read_jsonl(paths["receipts"])
                           if item["protocol"] == control.DELAYED)
            actions = self._read_jsonl(paths["actions"])
            matching = [item for item in actions
                        if item["protocol"] == control.DELAYED
                        and item["event"] == "dhr_destination_rx"
                        and item["flow_id"] == receipt["flow_id"]
                        and item["time"] == receipt["decode_at"]]
            self.assertEqual(len(matching), 1)
            actions.remove(matching[0])
            self._write_jsonl(paths["actions"], actions)
            with paths["runs"].open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            delayed = next(row for row in rows if row["protocol"] == control.DELAYED)
            delayed_actions = [
                {key: value for key, value in item.items() if key != "seed_split"}
                for item in actions if item["protocol"] == control.DELAYED
            ]
            delayed["full_action_trace_sha256"] = hashlib.sha256(json.dumps(
                delayed_actions, sort_keys=True, separators=(",", ":")
            ).encode("ascii")).hexdigest()
            self._rewrite_csv(paths["runs"], rows)
            self._rehash_manifest(paths)
            with self.assertRaisesRegex(ValueError, "destination.*action"):
                control.validate_manifest(
                    paths["manifest"], "unit", control.input_hashes(),
                    case=case, seeds=(7,),
                )

    def test_validator_recomputes_per_flow_first_flood_ack_fields(self):
        case = self.tiny_case()
        with TemporaryDirectory() as directory:
            paths = self._unit_artifacts(Path(directory) / "flow", case)
            flows = self._read_jsonl(paths["flows"])
            target = next(item for item in flows
                          if item["protocol"] == control.DELAYED
                          and item["first_flood_decode_at"] is not None)
            target["first_flood_ack_tx_start_at"] = target["first_flood_decode_at"] + 0.1
            self._write_jsonl(paths["flows"], flows)
            self._rehash_manifest(paths)
            with self.assertRaisesRegex(ValueError, "first-FLOOD per-flow"):
                control.validate_manifest(
                    paths["manifest"], "unit", control.input_hashes(),
                    case=case, seeds=(7,),
                )

    def test_strict_replay_rejects_rehashed_forged_collision_metric(self):
        case = self.tiny_case()
        with TemporaryDirectory() as directory:
            paths = self._unit_artifacts(Path(directory) / "replay", case)
            with paths["runs"].open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            delayed = next(row for row in rows if row["protocol"] == control.DELAYED)
            delayed["collision_failures"] = str(int(delayed["collision_failures"]) + 1)
            self._rewrite_csv(paths["runs"], rows)
            per_seed, paired = control.summarize_pairs(rows)
            self._rewrite_csv(paths["per_seed"], [
                {**item, "seed_split": "unit"} for item in per_seed
            ])
            self._rewrite_csv(paths["paired"], [{**paired, "seed_split": "unit"}])
            self._rehash_manifest(paths)
            control.validate_manifest(
                paths["manifest"], "unit", control.input_hashes(),
                case=case, seeds=(7,),
            )
            with self.assertRaisesRegex(ValueError, "strict replay"):
                control.validate_manifest(
                    paths["manifest"], "unit", control.input_hashes(),
                    case=case, seeds=(7,), strict_replay=True,
                )

    def test_validator_rejects_rehashed_early_delayed_ack_tx(self):
        case = self.tiny_case()
        with TemporaryDirectory() as directory:
            paths = self._unit_artifacts(Path(directory) / "early", case)
            receipt = next(item for item in self._read_jsonl(paths["receipts"])
                           if item["protocol"] == control.DELAYED)
            extended_tx = self._read_jsonl(paths["extended_tx"])
            ack = next(item for item in extended_tx
                       if item["protocol"] == control.DELAYED
                       and item["packet"]["kind"] == "ACK"
                       and item["sender"] == item["packet"]["origin"]
                       and item["packet"]["flow_id"] == receipt["flow_id"]
                       and item["packet"]["path"] == receipt["path"]
                       and item["packet"]["repair_index"] == receipt["repair_index"])
            duration = ack["end"] - ack["start"]
            ack["start"] = receipt["decode_at"] + 1.9
            ack["end"] = ack["start"] + duration
            self._write_jsonl(paths["extended_tx"], extended_tx)
            flows = self._read_jsonl(paths["flows"])
            target = next(item for item in flows
                          if item["protocol"] == control.DELAYED
                          and item["flow_id"] == receipt["flow_id"])
            target["first_flood_ack_extended_tx_start_at"] = ack["start"]
            self._write_jsonl(paths["flows"], flows)
            with paths["runs"].open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            delayed = next(row for row in rows if row["protocol"] == control.DELAYED)
            stripped = [{key: value for key, value in item.items()
                         if key != "seed_split"}
                        for item in extended_tx if item["protocol"] == control.DELAYED]
            delayed["extended_tx_trace_sha256"] = hashlib.sha256(json.dumps(
                stripped, sort_keys=True, separators=(",", ":")
            ).encode("ascii")).hexdigest()
            self._rewrite_csv(paths["runs"], rows)
            self._rehash_manifest(paths)
            with self.assertRaisesRegex(ValueError, "2-s timer"):
                control.validate_manifest(
                    paths["manifest"], "unit", control.input_hashes(),
                    case=case, seeds=(7,),
                )

    def test_smoke_workflow_uses_only_injected_tiny_seed_and_checks_paths_first(self):
        case = replace(self.tiny_case(), key="recurring_fading")
        with TemporaryDirectory() as directory, patch.object(
            control, "seeds_for_split", return_value=(7,)
        ), patch.dict(control.sr.SR_CASES, {"recurring_fading": case}):
            prefix = Path(directory) / "smoke"
            paths = control.run_experiment("smoke", prefix)
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
            self.assertEqual(manifest["seeds"], [7])
            self.assertEqual(manifest["protocols"], list(control.ARMS))
            control.validate_manifest(
                paths["manifest"], "smoke", control.input_hashes(),
                case=case, seeds=(7,),
            )
            with patch.object(control, "run_one_traced") as simulate:
                with self.assertRaises(FileExistsError):
                    control.run_experiment("smoke", prefix)
                simulate.assert_not_called()

    def test_explore_requires_strict_smoke_replay_before_any_simulation(self):
        with TemporaryDirectory() as directory, patch.object(
            control, "seeds_for_split", return_value=(7,)
        ), patch.object(control, "validate_manifest",
                        side_effect=ValueError("smoke blocked")) as validate, patch.object(
            control, "run_one_traced"
        ) as simulate:
            with self.assertRaisesRegex(ValueError, "smoke blocked"):
                control.run_experiment(
                    "explore", Path(directory) / "explore",
                    smoke_manifest=Path(directory) / "smoke.manifest.json",
                )
            self.assertTrue(validate.call_args.kwargs["strict_replay"])
            simulate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
