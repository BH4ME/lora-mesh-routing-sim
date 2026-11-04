"""Paired short-R-guard experiment tests on synthetic or tiny cases only."""

import unittest
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import subprocess
import sys

from tools import run_delayed_ack_short_guard_control as guard
from tools.run_sr_experiment import SrCase


class DelayedAckShortGuardExperimentTest(unittest.TestCase):
    @staticmethod
    def tiny_case():
        return SrCase(
            key="tiny_random", nodes=2, area_m=1.0, duration_s=8.0,
            rate_per_min=60.0, pair_mode="random", pair_count=0,
            temporal_fading_sigma_db=0.0,
        )

    def test_reserved_arms_and_explore_requires_strict_smoke_gate(self):
        self.assertEqual(guard.seeds_for_split("smoke"), (40000,))
        self.assertEqual(guard.seeds_for_split("explore"), tuple(range(40001, 40021)))
        self.assertEqual(guard.ARMS, (
            "meshecho-dhr-flood-ack-delay",
            "meshecho-dhr-flood-ack-delay-guard1",
            "meshecho-dhr-flood-ack-delay-guard2",
            "meshecho-dhr-flood-ack-delay-guard4",
            "meshecho-dhr-flood-ack-delay-guard8",
        ))
        with self.assertRaises(ValueError):
            guard.seeds_for_split("development")
        with TemporaryDirectory() as directory, patch.object(guard, "run_one") as simulate:
            with self.assertRaisesRegex(ValueError, "smoke manifest"):
                guard.run_experiment("explore", Path(directory) / "explore")
            simulate.assert_not_called()

    def test_traced_15_second_anchor_matches_independent_stock_current_code(self):
        case = self.tiny_case()
        traced = guard.run_one(case, guard.BASELINE, 7)
        stock = guard.run_one_stock(case, 7)
        guard.require_stock_parity(traced, stock)
        self.assertTrue(traced.transmissions)
        self.assertEqual(traced.row, stock.row)
        self.assertEqual(traced.flows, stock.flows)
        self.assertEqual(traced.actions, stock.actions)
        self.assertEqual(traced.transmissions, stock.transmissions)

    def test_guard_audit_links_each_initial_r_to_physical_tx_start(self):
        case = self.tiny_case()
        for arm in guard.ARMS:
            with self.subTest(arm=arm):
                run = guard.run_one(case, arm, 7)
                records = guard.audit_guard_contract(run)
                by_flow = {item["flow_id"]: item for item in records}
                routed = [flow for flow in run.flows if flow["source_action"] == "R"]
                self.assertTrue(routed)
                self.assertEqual(set(by_flow), {flow["flow_id"] for flow in routed})
                expected_guard = 15 if arm == guard.BASELINE else int(arm.rsplit("guard", 1)[1])
                for item in records:
                    self.assertEqual(item["r_guard_s"], expected_guard)
                    self.assertIsNotNone(item["initial_r_tx_id"])
                    self.assertIsNone(item["guard_at"])
                    self.assertIsNone(item["recovery_f_tx_id"])

    def test_guard_audit_rejects_event_before_physical_r_start_plus_guard(self):
        run = guard.run_one(self.tiny_case(), guard.ARMS[1], 7)
        record = guard.audit_guard_contract(run)[0]
        bad = {"case": run.row["case"], "protocol": run.row["protocol"],
               "seed": run.row["seed"], "event": "dhr_guard",
               "flow_id": record["flow_id"], "time": record["initial_r_start_at"] + 0.5,
               "src": record["src"], "dst": record["dst"],
               "admitted": True, "reason": "admitted", "selected_action": "F"}
        with self.assertRaisesRegex(ValueError, "physical R TX start"):
            guard.audit_guard_contract(replace(run, actions=[*run.actions, bad]))

    def test_discovery_fallback_r_keeps_original_guard_without_dhr_rescue(self):
        case = replace(self.tiny_case(), duration_s=230.0)
        original_receive = guard.TracingSimulator.try_receive

        def schedule_three_flows(simulator, *args):
            for flow_id, when in enumerate((1.0, 20.0, 200.0), start=1):
                simulator.schedule(when, "app_send", (0, 1, flow_id))

        def drop_discovery_reply_and_ack(simulator, tx, receiver):
            if (tx.packet.flow_id == 3 and receiver == 0
                    and tx.packet.kind in {"RREP", "ACK"}):
                simulator.metrics.rx_fail += 1
                return None
            return original_receive(simulator, tx, receiver)

        with patch.object(guard.sr, "schedule_sr_traffic", schedule_three_flows), \
                patch.object(guard.TracingSimulator, "try_receive",
                             drop_discovery_reply_and_ack):
            run = guard.run_one(case, guard.ARMS[2], 17)
            extended = guard.run_one(case, guard.ARMS[2], 17, extended=True)

        flow = next(item for item in run.flows if item["flow_id"] == 3)
        initial = next(tx for tx in run.transmissions
                       if tx["sender"] == 0 and tx["packet"]["flow_id"] == 3
                       and tx["packet"]["kind"] == "DATA")
        timeout = next(event for event in run.actions
                       if event.get("flow_id") == 3 and event["event"] == "timeout"
                       and event["reason"] == "source-ack-timeout")
        self.assertEqual(flow["source_action"], "R")
        self.assertTrue(any(event.get("flow_id") == 3
                            and event["event"] == "decision"
                            and event["action"] == "D" for event in run.actions))
        self.assertAlmostEqual(timeout["time"] - initial["start"], 15.0)
        self.assertFalse(any(event.get("flow_id") == 3
                             and event["event"] in {"dhr_guard", "dhr_recovery_tx"}
                             for event in run.actions))
        fallback = next(item for item in guard.audit_guard_contract(run)
                        if item["flow_id"] == 3)
        self.assertEqual(fallback["guard_scope"], "discovery-fallback-R")
        self.assertEqual(fallback["r_guard_s"], 15)
        self.assertAlmostEqual(fallback["source_timeout_at"], timeout["time"])
        self.assertIsNone(fallback["guard_at"])
        self.assertIsNone(fallback["recovery_f_tx_id"])
        enriched = guard._enriched_flows(run, "unit", guard.audit_guard_contract(run))
        self.assertEqual(next(item for item in enriched if item["flow_id"] == 3)
                         ["guard_scope"], "discovery-fallback-R")
        self.assertEqual(guard.run_row(run, extended, case)
                         ["discovery_fallback_r_starts"], 1)

    def test_guard_audit_requires_one_valid_initial_decision_for_routed_data(self):
        run = guard.run_one(self.tiny_case(), guard.ARMS[2], 7)
        flow_id = next(flow["flow_id"] for flow in run.flows
                       if flow["source_action"] == "R")
        decision = next(event for event in run.actions
                        if event.get("flow_id") == flow_id
                        and event["event"] == "decision")
        missing = [event for event in run.actions if event is not decision]
        with self.assertRaisesRegex(ValueError, "missing initial decision"):
            guard.audit_guard_contract(replace(run, actions=missing))
        with self.assertRaisesRegex(ValueError, "invalid initial decision"):
            guard.audit_guard_contract(replace(
                run, actions=[*run.actions, decision],
            ))
        unknown = [{**event, "action": "unknown"} if event is decision else event
                   for event in run.actions]
        with self.assertRaisesRegex(ValueError, "invalid initial decision"):
            guard.audit_guard_contract(replace(run, actions=unknown))

    def test_true_initial_r_missing_guard_still_fails_audit(self):
        original_receive = guard.TracingSimulator.try_receive

        def drop_flow_four_ack(simulator, tx, receiver):
            if (tx.packet.kind == "ACK" and tx.packet.flow_id == 4
                    and receiver == tx.packet.final_dst):
                simulator.metrics.rx_fail += 1
                return None
            return original_receive(simulator, tx, receiver)

        with patch.object(guard.TracingSimulator, "try_receive", drop_flow_four_ack):
            run = guard.run_one(self.tiny_case(), guard.ARMS[2], 7)

        flow_id = 4
        self.assertTrue(any(event.get("flow_id") == flow_id
                            and event["event"] == "decision"
                            and event["action"] == "R" for event in run.actions))
        self.assertTrue(any(event.get("flow_id") == flow_id
                            and event["event"] == "dhr_guard"
                            for event in run.actions))
        without_guard = [event for event in run.actions
                         if not (event.get("flow_id") == flow_id
                                 and event["event"] in {"dhr_guard", "dhr_recovery_tx"})]
        without_recovery = [tx for tx in run.transmissions
                            if not (tx["packet"]["flow_id"] == flow_id
                                    and tx["sender"] == tx["packet"]["origin"]
                                    and tx["packet"]["repair_index"] == 2)]
        with self.assertRaisesRegex(ValueError, "missing R guard"):
            guard.audit_guard_contract(replace(
                run, actions=without_guard, transmissions=without_recovery,
            ))

    def test_symmetric_extended_replay_preserves_primary_and_full_tx_cost(self):
        case = self.tiny_case()
        for arm in guard.ARMS:
            with self.subTest(arm=arm):
                primary = guard.run_one(case, arm, 7)
                extended = guard.run_one(case, arm, 7, extended=True)
                guard.require_extended_prefix(primary, extended)
                row = guard.run_row(primary, extended, case)
                self.assertEqual(row["ack_by_deadline"], sum(
                    flow["ack_by_deadline"] for flow in primary.flows
                ))
                self.assertEqual(row["delivery_by_deadline"], sum(
                    flow["delivery_by_deadline"] for flow in primary.flows
                ))
                self.assertGreaterEqual(row["extended_tx_airtime_s"],
                                        row["whole_network_tx_airtime_s"])
                self.assertGreaterEqual(row["extended_tx_bytes"],
                                        row["windowed_tx_bytes"])

    def test_physical_cost_charges_complete_packet_if_tx_starts_by_cutoff(self):
        sample = guard.run_one(self.tiny_case(), guard.BASELINE, 7)
        template = sample.transmissions[0]
        tx = [
            {**template, "tx_id": 10001, "start": 629.9, "end": 630.2},
            {**template, "tx_id": 10002, "start": 630.1, "end": 630.4},
        ]
        primary = guard.physical_cost(tx, 630.0, 32)
        extended = guard.physical_cost(tx, 660.0, 32)
        self.assertEqual(primary["tx_count"], 1)
        self.assertAlmostEqual(primary["tx_airtime_s"], 0.3)
        self.assertEqual(extended["tx_count"], 2)
        self.assertAlmostEqual(extended["tx_airtime_s"], 0.6)
        self.assertEqual(extended["tx_bytes"], primary["tx_bytes"] * 2)

    def test_five_arm_seed_pairs_require_same_schedule_and_report_costs(self):
        rows = []
        for seed in (1, 2):
            for index, arm in enumerate(guard.ARMS):
                rows.append({
                    "case": "synthetic", "case_config_sha256": "same",
                    "seed": seed, "protocol": arm,
                    "scheduled_trace_sha256": f"trace-{seed}",
                    "scheduled_unicast_flows": 10,
                    "application_deadline_s": 30.0,
                    "ack_pdr_deadline": 0.5 + 0.1 * index,
                    "destination_pdr_deadline": 0.6 + 0.05 * index,
                    "mean_completion_delay_capped_s": 12.0 - index,
                    "whole_network_tx_airtime_s": 100.0 + 10 * index,
                    "windowed_tx_bytes": 1000 + 100 * index,
                    "extended_tx_airtime_s": 101.0 + 10 * index,
                    "extended_tx_bytes": 1010 + 100 * index,
                    "physical_recovery_f_starts": index,
                    "late_ack_count": index,
                    "guard_source_busy_rejections": index,
                    "guard_deadline_budget_rejections": index,
                })
        per_seed, paired = guard.summarize_pairs(rows)
        self.assertEqual(len(per_seed), 8)
        self.assertEqual(len(paired), 4)
        self.assertAlmostEqual(per_seed[0]["ack_pdr_gain"], 0.1)
        self.assertAlmostEqual(per_seed[0]["relative_airtime_cost"], 0.1)
        self.assertEqual(per_seed[0]["recovery_f_starts_delta"], 1)
        self.assertAlmostEqual(paired[0]["ack_pdr_gain"], 0.1)
        self.assertAlmostEqual(paired[0]["ack_pdr_ci95_low"], 0.1)
        rows[1]["scheduled_trace_sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "trace"):
            guard.summarize_pairs(rows)

    def test_tiny_artifacts_strictly_replay_and_reject_rehashed_tx_change(self):
        case = self.tiny_case()
        pairs = [
            (guard.run_one(case, arm, 7), guard.run_one(case, arm, 7, extended=True))
            for arm in guard.ARMS
        ]
        stock = {7: guard.run_one_stock(case, 7)}
        with TemporaryDirectory() as directory:
            prefix = Path(directory) / "tiny"
            paths = guard.write_artifacts(
                prefix, case, "unit", pairs, stock, guard.input_hashes()
            )
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
            self.assertTrue(manifest["stock_current_code_parity"])
            self.assertEqual(manifest["runs"], 5)
            self.assertEqual(set(manifest["artifact_sha256"]), set(paths) - {"manifest"})
            guard.validate_manifest(
                paths["manifest"], "unit", guard.input_hashes(),
                case=case, seeds=(7,), strict_replay=True,
            )
            with self.assertRaises(FileExistsError):
                guard.write_artifacts(
                    prefix, case, "unit", pairs, stock, guard.input_hashes()
                )
            items = [json.loads(line) for line in paths["extended_tx"].read_text(
                encoding="utf-8"
            ).splitlines()]
            items[0]["end"] += 0.5
            paths["extended_tx"].write_text(
                "".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n"
                        for item in items), encoding="utf-8",
            )
            manifest["artifact_sha256"]["extended_tx"] = hashlib.sha256(
                paths["extended_tx"].read_bytes()
            ).hexdigest()
            paths["manifest"].write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "(TX|cost|prefix|hash)"):
                guard.validate_manifest(
                    paths["manifest"], "unit", guard.input_hashes(),
                    case=case, seeds=(7,),
                )

    def test_explore_strictly_validates_smoke_before_any_seed_run(self):
        with TemporaryDirectory() as directory, patch.object(
            guard, "validate_manifest", side_effect=ValueError("smoke blocked")
        ) as validate, patch.object(guard, "run_one") as simulate:
            with self.assertRaisesRegex(ValueError, "smoke blocked"):
                guard.run_experiment(
                    "explore", Path(directory) / "explore",
                    smoke_manifest=Path(directory) / "smoke.manifest.json",
                )
            self.assertEqual(validate.call_args.args[1], "smoke")
            self.assertTrue(validate.call_args.kwargs["strict_replay"])
            simulate.assert_not_called()

    def test_real_ack_drop_guard_fires_from_physical_r_start(self):
        original = guard.TracingSimulator.try_receive

        def drop_flow_four_ack(simulator, tx, receiver):
            if (tx.packet.kind == "ACK" and tx.packet.flow_id == 4
                    and receiver == tx.packet.final_dst):
                simulator.metrics.rx_fail += 1
                return None
            return original(simulator, tx, receiver)

        with patch.object(guard.TracingSimulator, "try_receive", drop_flow_four_ack):
            for arm in guard.ARMS:
                with self.subTest(arm=arm):
                    run = guard.run_one(self.tiny_case(), arm, 7)
                    record = next(item for item in guard.audit_guard_contract(run)
                                  if item["flow_id"] == 4)
                    self.assertIsNotNone(record["guard_at"])
                    self.assertAlmostEqual(record["guard_at"] - record["initial_r_start_at"],
                                           record["r_guard_s"])
                    self.assertTrue(any(
                        event["event"] == "timeout" and event["flow_id"] == 4
                        and event["reason"] == "source-ack-timeout"
                        and event["time"] == record["guard_at"]
                        for event in run.actions
                    ))

    def test_run_row_rejects_forged_physical_cost_and_all_flow_outcome(self):
        case = self.tiny_case()
        primary = guard.run_one(case, guard.ARMS[1], 7)
        extended = guard.run_one(case, guard.ARMS[1], 7, extended=True)
        with self.assertRaisesRegex(ValueError, "TX cost"):
            guard.run_row(replace(primary, row={
                **primary.row,
                "whole_network_tx_airtime_s": primary.row["whole_network_tx_airtime_s"] + 1,
            }), extended, case)
        with self.assertRaisesRegex(ValueError, "all-flow outcome"):
            guard.run_row(replace(primary, row={
                **primary.row, "ack_by_deadline": primary.row["ack_by_deadline"] + 1,
            }), extended, case)
        with self.assertRaisesRegex(ValueError, "TX cost"):
            guard.run_row(replace(primary, row={
                **primary.row,
                "windowed_dhr_flood_ack_tx": primary.row["windowed_dhr_flood_ack_tx"] + 1,
            }), extended, case)

    def test_guard_audit_rejects_initial_r_with_wrong_destination(self):
        run = guard.run_one(self.tiny_case(), guard.ARMS[1], 7)
        record = guard.audit_guard_contract(run)[0]
        changed = []
        for tx in run.transmissions:
            if tx["tx_id"] == record["initial_r_tx_id"]:
                changed.append({**tx, "packet": {
                    **tx["packet"], "final_dst": record["src"],
                }})
            else:
                changed.append(tx)
        with self.assertRaisesRegex(ValueError, "initial R.*flow"):
            guard.audit_guard_contract(replace(run, transmissions=changed))

    def test_smoke_entrypoint_with_injected_tiny_case_and_cli_help(self):
        case = replace(self.tiny_case(), key="recurring_fading")
        with TemporaryDirectory() as directory, patch.object(
            guard, "seeds_for_split", return_value=(7,)
        ), patch.dict(guard.sr.SR_CASES, {"recurring_fading": case}):
            paths = guard.run_experiment("smoke", Path(directory) / "smoke")
            guard.validate_manifest(
                paths["manifest"], "smoke", guard.input_hashes(),
                case=case, seeds=(7,), strict_replay=True,
            )
        result = subprocess.run(
            [sys.executable, str(guard.ROOT / "tools/run_delayed_ack_short_guard_control.py"),
             "--help"], cwd=guard.ROOT, text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--smoke-manifest", result.stdout)


if __name__ == "__main__":
    unittest.main()
