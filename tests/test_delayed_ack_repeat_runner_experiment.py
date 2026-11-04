"""Paired fixed-delay ACK repeat runner tests on synthetic/tiny cases only."""

import unittest
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lora_mesh_sim import Node, Packet, RadioConfig, build_protocol
from tools import run_delayed_ack_repeat_control as repeat
from tools.run_sr_experiment import SR_CASES, SrCase


class DelayedAckRepeatExperimentTest(unittest.TestCase):
    @staticmethod
    def tiny_case():
        return SrCase(
            key="tiny_random", nodes=2, area_m=1.0, duration_s=8.0,
            rate_per_min=60.0, pair_mode="random", pair_count=0,
            temporal_fading_sigma_db=0.0,
        )

    def tail_run(self, *, decode_before_cutoff_s, first_lag_s,
                 repeat_lag_s=None):
        case = self.tiny_case()
        primary = repeat.run_one(case, repeat.REPEAT, 7)
        extended = repeat.run_one(case, repeat.REPEAT, 7, extended=True)
        used_flows = {item["flow_id"] for item in extended.first_flood_receipts}
        flow = next(item for item in primary.flows
                    if item["flow_id"] not in used_flows)
        decode_at = case.duration_s + 60.0 - decode_before_cutoff_s
        flood_template = next(tx for tx in extended.transmissions
                              if tx["packet"]["kind"] == "FLOOD")
        ack_template = next(tx for tx in extended.transmissions
                            if tx["packet"]["kind"] == "ACK"
                            and tx["sender"] == tx["packet"]["origin"])
        next_tx_id = max(tx["tx_id"] for tx in extended.transmissions) + 1
        flood = {
            **flood_template, "tx_id": next_tx_id,
            "sender": flow["src"], "start": decode_at - 0.2,
            "end": decode_at,
            "packet": {**flood_template["packet"],
                       "flow_id": flow["flow_id"], "origin": flow["src"],
                       "final_dst": flow["dst"], "request_id": flow["flow_id"],
                       "repair_index": 2, "path": [flow["src"]]},
        }
        first_ack = {
            **ack_template, "tx_id": next_tx_id + 1,
            "sender": flow["dst"], "start": decode_at + first_lag_s,
            "end": decode_at + first_lag_s + 0.2,
            "packet": {**ack_template["packet"],
                       "flow_id": flow["flow_id"], "origin": flow["dst"],
                       "final_dst": flow["src"], "request_id": flow["flow_id"],
                       "repair_index": 2, "path": [flow["src"], flow["dst"]],
                       "path_index": 0, "created_at": decode_at},
        }
        receipt = {"flow_id": flow["flow_id"], "decode_at": decode_at,
                   "tx_id": next_tx_id, "path": [flow["src"], flow["dst"]],
                   "repair_index": 2}
        rx = {"case": case.key, "protocol": repeat.REPEAT, "seed": 7,
              "event": "dhr_destination_rx", "time": decode_at,
              "flow_id": flow["flow_id"], "src": flow["src"],
              "dst": flow["dst"], "repair_index": 2, "duplicate": True}
        transmissions = [*extended.transmissions, flood, first_ack]
        actions = [*extended.actions, rx]
        if repeat_lag_s is not None:
            repeat_start = decode_at + repeat_lag_s
            transmissions.append({
                **first_ack, "tx_id": next_tx_id + 2,
                "start": repeat_start, "end": repeat_start + 0.2,
            })
            actions.append({
                "case": case.key, "protocol": repeat.REPEAT, "seed": 7,
                "event": "delayed_ack_repeat_tx", "time": repeat_start,
                "flow_id": flow["flow_id"], "dst": flow["dst"],
                "path": [flow["src"], flow["dst"]],
            })
        extended = replace(
            extended, transmissions=transmissions, actions=actions,
            first_flood_receipts=[*extended.first_flood_receipts, receipt],
        )
        return case, primary, extended

    def test_reserved_cohorts_and_explore_requires_smoke_before_simulation(self):
        self.assertEqual(repeat.seeds_for_split("smoke"), (41000,))
        self.assertEqual(repeat.seeds_for_split("explore"), tuple(range(41001, 41021)))
        with self.assertRaises(ValueError):
            repeat.seeds_for_split("development")
        with TemporaryDirectory() as directory, patch.object(
            repeat, "run_one"
        ) as simulate:
            with self.assertRaisesRegex(ValueError, "smoke manifest"):
                repeat.run_experiment("explore", Path(directory) / "explore")
            simulate.assert_not_called()

    def test_traced_current_code_baseline_matches_independent_stock_run(self):
        case = self.tiny_case()
        traced = repeat.run_one(case, repeat.BASELINE, 7)
        stock = repeat.run_one_stock(case, 7)

        repeat.require_stock_parity(traced, stock)
        self.assertTrue(traced.transmissions)
        self.assertTrue(traced.first_flood_receipts)

    def test_real_repeat_ack_is_physical_same_path_after_actual_first_tx_end(self):
        run = repeat.run_one(self.tiny_case(), repeat.REPEAT, 7)
        records = repeat.audit_ack_contract(run)
        emitted = [item for item in records if item["repeat_ack_tx_id"] is not None]
        self.assertTrue(emitted)
        for item in emitted:
            self.assertGreaterEqual(item["first_ack_start_at"],
                                    item["first_flood_decode_at"] + 2.0 - 1e-9)
            self.assertGreaterEqual(item["repeat_ack_start_at"],
                                    item["first_ack_end_at"] + 0.5 - 1e-9)
            self.assertLessEqual(item["repeat_ack_start_at"],
                                 item["first_flood_decode_at"] + 10.0 + 1e-9)

    def test_first_recovery_flood_after_r_delivery_is_still_a_first_flood_receipt(self):
        run = repeat.run_one(SR_CASES["recurring_fading"], repeat.REPEAT, 1)
        flows = {flow["flow_id"]: flow for flow in run.flows}
        first_recovery_rx = {}
        for event in run.actions:
            if (event.get("event") == "dhr_destination_rx"
                    and event.get("repair_index") == 2):
                first_recovery_rx.setdefault(event["flow_id"], event)
        recovered = [
            event for flow_id, event in first_recovery_rx.items()
            if flows[flow_id]["source_action"] == "R"
            and flows[flow_id]["delivered_at"] < event["time"]
            and event["duplicate"]
        ]
        self.assertTrue(recovered, "seed must exercise delivered R then first recovery F")
        receipt_by_flow = {item["flow_id"]: item
                           for item in run.first_flood_receipts}
        evidence_by_flow = {item["flow_id"]: item
                            for item in repeat.audit_ack_contract(run)}
        for event in recovered:
            flow_id = event["flow_id"]
            self.assertEqual(receipt_by_flow[flow_id]["decode_at"], event["time"])
            self.assertIsNotNone(evidence_by_flow[flow_id]["first_ack_tx_id"])

    def test_ack_audit_rejects_early_first_and_changed_repeat_wire_fields(self):
        run = repeat.run_one(self.tiny_case(), repeat.REPEAT, 7)
        receipt = run.first_flood_receipts[0]
        acks = [tx for tx in run.transmissions
                if tx["packet"]["kind"] == "ACK"
                and tx["sender"] == tx["packet"]["origin"]
                and tx["packet"]["flow_id"] == receipt["flow_id"]]
        self.assertEqual(len(acks), 2)
        early = {**acks[0], "start": receipt["decode_at"] + 1.9}
        early["end"] = early["start"] + (acks[0]["end"] - acks[0]["start"])
        with self.assertRaisesRegex(ValueError, "2-s"):
            repeat.audit_ack_contract(replace(run, transmissions=[
                early if tx["tx_id"] == acks[0]["tx_id"] else tx
                for tx in run.transmissions
            ]))
        changed = {**acks[1], "packet": {**acks[1]["packet"], "ttl": 1}}
        with self.assertRaisesRegex(ValueError, "same.*packet"):
            repeat.audit_ack_contract(replace(run, transmissions=[
                changed if tx["tx_id"] == acks[1]["tx_id"] else tx
                for tx in run.transmissions
            ]))

    def test_ack_audit_rejects_missing_repeat_without_drop_or_tail_censoring(self):
        run = repeat.run_one(self.tiny_case(), repeat.REPEAT, 7)
        record = next(item for item in repeat.audit_ack_contract(run)
                      if item["repeat_ack_tx_id"] is not None)
        missing_tx_id = record["repeat_ack_tx_id"]
        missing_flow = record["flow_id"]
        altered = replace(
            run,
            transmissions=[tx for tx in run.transmissions
                           if tx["tx_id"] != missing_tx_id],
            actions=[event for event in run.actions
                     if not (event.get("event") == "delayed_ack_repeat_tx"
                             and event.get("flow_id") == missing_flow)],
        )
        with self.assertRaisesRegex(ValueError, "missing repeat"):
            repeat.audit_ack_contract(altered)

    def test_ack_audit_rejects_missing_first_ack_before_extended_cutoff(self):
        run = repeat.run_one(self.tiny_case(), repeat.REPEAT, 7)
        record = next(item for item in repeat.audit_ack_contract(run)
                      if item["repeat_ack_tx_id"] is not None)
        missing_tx_ids = {record["first_ack_tx_id"],
                          record["repeat_ack_tx_id"]}
        altered = replace(
            run,
            transmissions=[tx for tx in run.transmissions
                           if tx["tx_id"] not in missing_tx_ids],
            actions=[event for event in run.actions
                     if not (event.get("event") == "delayed_ack_repeat_tx"
                             and event.get("flow_id") == record["flow_id"])],
        )
        with self.assertRaisesRegex(ValueError, "missing first FLOOD ACK"):
            repeat.audit_ack_contract(altered)

    def test_ack_audit_rejects_early_local_window_drop(self):
        run = repeat.run_one(self.tiny_case(), repeat.REPEAT, 7)
        record = next(item for item in repeat.audit_ack_contract(run)
                      if item["repeat_ack_tx_id"] is not None)
        drop = {
            "case": run.row["case"], "protocol": run.row["protocol"],
            "seed": run.row["seed"], "event": "delayed_ack_repeat_drop",
            "time": record["first_ack_end_at"] + 0.5,
            "flow_id": record["flow_id"],
            "dst": record["first_flood_path"][-1],
            "reason": "local-window",
        }
        altered = replace(
            run,
            transmissions=[tx for tx in run.transmissions
                           if tx["tx_id"] != record["repeat_ack_tx_id"]],
            actions=[event for event in run.actions
                     if not (event.get("event") == "delayed_ack_repeat_tx"
                             and event.get("flow_id") == record["flow_id"])] + [drop],
        )
        with self.assertRaisesRegex(ValueError, "local-window drop"):
            repeat.audit_ack_contract(altered)

    def test_ack_audit_rejects_unbound_off_path_third_destination_ack(self):
        run = repeat.run_one(self.tiny_case(), repeat.REPEAT, 7)
        record = next(item for item in repeat.audit_ack_contract(run)
                      if item["repeat_ack_tx_id"] is not None)
        first = next(tx for tx in run.transmissions
                     if tx["tx_id"] == record["first_ack_tx_id"])
        extra = {
            **first,
            "tx_id": max(tx["tx_id"] for tx in run.transmissions) + 1,
            "start": first["start"] + 1.0,
            "end": first["end"] + 1.0,
            "packet": {
                **first["packet"],
                "path": [record["first_flood_path"][0], 99,
                         record["first_flood_path"][-1]],
                "created_at": first["packet"]["created_at"] + 0.1,
            },
        }
        with self.assertRaisesRegex(ValueError, "unbound destination ACK"):
            repeat.audit_ack_contract(replace(
                run, transmissions=[*run.transmissions, extra]
            ))

    def test_ack_audit_rejects_wrong_reverse_path_index_on_both_acks(self):
        run = repeat.run_one(self.tiny_case(), repeat.REPEAT, 7)
        record = next(item for item in repeat.audit_ack_contract(run)
                      if item["repeat_ack_tx_id"] is not None)
        ack_ids = {record["first_ack_tx_id"], record["repeat_ack_tx_id"]}
        altered = replace(run, transmissions=[
            {**tx, "packet": {**tx["packet"], "path_index": 1}}
            if tx["tx_id"] in ack_ids else tx
            for tx in run.transmissions
        ])
        with self.assertRaisesRegex(ValueError, "reverse path index"):
            repeat.audit_ack_contract(altered)

    def test_ack_audit_rejects_capacity_drop_without_eight_active_records(self):
        run = repeat.run_one(self.tiny_case(), repeat.REPEAT, 7)
        record = next(item for item in repeat.audit_ack_contract(run)
                      if item["repeat_ack_tx_id"] is not None)
        drop = {
            "case": run.row["case"], "protocol": run.row["protocol"],
            "seed": run.row["seed"], "event": "delayed_ack_repeat_drop",
            "time": record["first_flood_decode_at"],
            "flow_id": record["flow_id"],
            "dst": record["first_flood_path"][-1],
            "reason": "active-capacity",
        }
        altered = replace(
            run,
            transmissions=[tx for tx in run.transmissions
                           if tx["tx_id"] != record["repeat_ack_tx_id"]],
            actions=[event for event in run.actions
                     if not (event.get("event") == "delayed_ack_repeat_tx"
                             and event.get("flow_id") == record["flow_id"])] + [drop],
        )
        with self.assertRaisesRegex(ValueError, "capacity drop"):
            repeat.audit_ack_contract(altered)

    def test_ack_audit_accepts_ninth_flow_capacity_drop_with_eight_active_records(self):
        destination = 9
        sim = repeat.sr.RecordingSimulator(
            [Node(i, 0.0, 0.0, role="client") for i in range(9)]
            + [Node(destination, 10.0, 0.0, role="client")],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol(repeat.REPEAT), seed=17, max_hops=6,
            independent_random_streams=True,
        )
        sim.nodes[destination].tx_available_at = 5.0
        for src in range(9):
            sim.schedule(1.0 + 0.3 * src, "app_send", (src, destination, src + 1))
        sim.run(9.0)
        receipts = []
        for event in sim.protocol.action_events:
            if event.get("event") != "dhr_destination_rx":
                continue
            tx = next(tx for tx in sim.tx_history
                      if tx.packet.kind == "FLOOD"
                      and tx.packet.flow_id == event["flow_id"]
                      and abs(tx.end - event["time"]) <= 1e-9)
            receipts.append({
                "flow_id": event["flow_id"], "decode_at": event["time"],
                "tx_id": tx.tx_id,
                "path": list(tx.packet.path + (destination,)),
                "repair_index": tx.packet.repair_index,
            })
        run = repeat.RepeatRun(
            {"protocol": repeat.REPEAT, "drain_until_s": 9.0}, [],
            sim.protocol.action_events,
            [{"tx_id": tx.tx_id, "sender": tx.sender,
              "start": tx.start, "end": tx.end, "packet": asdict(tx.packet)}
             for tx in sim.tx_history],
            receipts,
        )

        records = repeat.audit_ack_contract(run)
        self.assertEqual(len(records), 9)
        self.assertEqual(sum(item["repeat_ack_tx_id"] is not None
                             for item in records), 8)

    def test_extended_replay_preserves_primary_prefix_and_recomputes_full_cost(self):
        case = self.tiny_case()
        for arm in repeat.ARMS:
            primary = repeat.run_one(case, arm, 7)
            extended = repeat.run_one(case, arm, 7, extended=True)
            repeat.require_extended_prefix(primary, extended)
            row = repeat.run_row(primary, extended, case)
            self.assertEqual(row["ack_by_deadline"],
                             sum(flow["ack_by_deadline"] for flow in primary.flows))
            self.assertEqual(row["delivery_by_deadline"],
                             sum(flow["delivery_by_deadline"] for flow in primary.flows))
            self.assertGreaterEqual(row["extended_tx_airtime_s"],
                                    row["whole_network_tx_airtime_s"])
            self.assertGreaterEqual(row["extended_tx_bytes"],
                                    row["windowed_tx_bytes"])
            altered = replace(extended, row={**extended.row,
                                             "scheduled_trace_sha256": "wrong"})
            with self.assertRaisesRegex(ValueError, "extended replay"):
                repeat.require_extended_prefix(primary, altered)

    def test_extended_replay_rejects_changed_pre_cutoff_action(self):
        case = self.tiny_case()
        primary = repeat.run_one(case, repeat.REPEAT, 7)
        extended = repeat.run_one(case, repeat.REPEAT, 7, extended=True)
        self.assertTrue(primary.actions)
        forged = [{**extended.actions[0], "reason": "forged"},
                  *extended.actions[1:]]
        with self.assertRaisesRegex(ValueError, "extended replay.*action"):
            repeat.require_extended_prefix(
                primary, replace(extended, actions=forged)
            )

    def test_extended_replay_rejects_changed_deadline_flow_outcome(self):
        case = self.tiny_case()
        primary = repeat.run_one(case, repeat.REPEAT, 7)
        extended = repeat.run_one(case, repeat.REPEAT, 7, extended=True)
        forged = [{**extended.flows[0],
                   "ack_by_deadline": not extended.flows[0]["ack_by_deadline"]},
                  *extended.flows[1:]]
        with self.assertRaisesRegex(ValueError, "extended replay.*flow"):
            repeat.require_extended_prefix(
                primary, replace(extended, flows=forged)
            )

    def test_extended_replay_accepts_future_dated_committed_prefix_and_late_source_action(self):
        case = self.tiny_case()
        primary = repeat.run_one(case, repeat.REPEAT, 7)
        extended = repeat.run_one(case, repeat.REPEAT, 7, extended=True)
        cutoff = case.duration_s + 30.0
        template = primary.transmissions[-1]
        future_tx = {**template,
                     "tx_id": max(tx["tx_id"] for tx in primary.transmissions) + 1,
                     "start": cutoff + 1.0, "end": cutoff + 1.1}
        future_action = {
            "case": case.key, "protocol": repeat.REPEAT, "seed": 7,
            "event": "delayed_ack_repeat_drop", "time": cutoff + 0.5,
            "flow_id": primary.flows[0]["flow_id"], "dst": primary.flows[0]["dst"],
            "reason": "local-window",
        }
        primary = replace(
            primary,
            transmissions=[*primary.transmissions, future_tx],
            actions=[*primary.actions, future_action],
            flows=[{**primary.flows[0], "source_action": None},
                   *primary.flows[1:]],
        )
        extended = replace(
            extended,
            transmissions=[*primary.transmissions,
                           *extended.transmissions[len(primary.transmissions) - 1:]],
            actions=[*primary.actions,
                     *extended.actions[len(primary.actions) - 1:]],
        )
        repeat.require_extended_prefix(primary, extended)

    def test_cost_audit_rejects_forged_airtime_and_flow_outcomes(self):
        case = self.tiny_case()
        primary = repeat.run_one(case, repeat.REPEAT, 7)
        extended = repeat.run_one(case, repeat.REPEAT, 7, extended=True)
        with self.assertRaisesRegex(ValueError, "TX cost"):
            repeat.run_row(replace(primary, row={
                **primary.row,
                "whole_network_tx_airtime_s": primary.row["whole_network_tx_airtime_s"] + 1,
            }), extended, case)
        with self.assertRaisesRegex(ValueError, "flow outcome"):
            repeat.run_row(replace(primary, row={
                **primary.row, "ack_by_deadline": primary.row["ack_by_deadline"] + 1,
            }), extended, case)

    def test_paired_seed_summary_requires_identical_trace_and_has_ci(self):
        rows = []
        for seed in (1, 2):
            for arm in repeat.ARMS:
                extra = arm == repeat.REPEAT
                rows.append({
                    "case": "synthetic", "case_config_sha256": "same",
                    "seed": seed, "protocol": arm,
                    "scheduled_trace_sha256": f"trace-{seed}",
                    "scheduled_unicast_flows": 10,
                    "application_deadline_s": 30.0,
                    "ack_pdr_deadline": 0.8 if extra else 0.7,
                    "destination_pdr_deadline": 0.9,
                    "whole_network_tx_airtime_s": 110.0 if extra else 100.0,
                    "windowed_tx_bytes": 1100 if extra else 1000,
                    "extended_tx_airtime_s": 111.0 if extra else 101.0,
                    "extended_tx_bytes": 1110 if extra else 1010,
                    "mean_completion_delay_capped_s": 8.0 if extra else 9.0,
                })
        per_seed, paired = repeat.summarize_pairs(rows)
        self.assertEqual(len(per_seed), 2)
        self.assertAlmostEqual(paired["ack_pdr_gain"], 0.1)
        self.assertAlmostEqual(paired["ack_pdr_ci95_low"], 0.1)
        self.assertAlmostEqual(paired["relative_airtime_cost"], 0.1)
        self.assertAlmostEqual(paired["relative_byte_cost"], 0.1)
        rows[0]["scheduled_trace_sha256"] = "mismatched"
        with self.assertRaisesRegex(ValueError, "trace"):
            repeat.summarize_pairs(rows)

    def test_tiny_artifacts_validate_strictly_and_reject_rehashed_tx_tampering(self):
        case = self.tiny_case()
        pairs = [
            (repeat.run_one(case, arm, 7),
             repeat.run_one(case, arm, 7, extended=True))
            for arm in repeat.ARMS
        ]
        stock = {7: repeat.run_one_stock(case, 7)}
        with TemporaryDirectory() as directory:
            prefix = Path(directory) / "tiny"
            paths = repeat.write_artifacts(
                prefix, case, "unit", pairs, stock, repeat.input_hashes()
            )
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
            self.assertTrue(manifest["stock_current_code_parity"])
            self.assertEqual(manifest["runs"], 2)
            self.assertIn("repeat_events", manifest["artifact_sha256"])
            self.assertEqual(set(manifest["artifact_sha256"]), set(paths) - {"manifest"})
            repeat.validate_manifest(
                paths["manifest"], "unit", repeat.input_hashes(),
                case=case, seeds=(7,), strict_replay=True,
            )
            with self.assertRaises(FileExistsError):
                repeat.write_artifacts(
                    prefix, case, "unit", pairs, stock, repeat.input_hashes()
                )
            tx = [json.loads(line) for line in paths["extended_tx"].read_text(
                encoding="utf-8").splitlines()]
            first = next(item for item in tx if item["protocol"] == repeat.REPEAT)
            first["end"] += 0.5
            paths["extended_tx"].write_text(
                "".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n"
                        for item in tx), encoding="utf-8"
            )
            manifest["artifact_sha256"]["extended_tx"] = hashlib.sha256(
                paths["extended_tx"].read_bytes()
            ).hexdigest()
            paths["manifest"].write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "(TX|receipt|prefix|cost|hash)"):
                repeat.validate_manifest(
                    paths["manifest"], "unit", repeat.input_hashes(),
                    case=case, seeds=(7,),
                )

    def test_explore_strictly_validates_smoke_before_any_seed_run(self):
        with TemporaryDirectory() as directory, patch.object(
            repeat, "validate_manifest", side_effect=ValueError("smoke blocked")
        ) as validate, patch.object(repeat, "run_one") as simulate:
            with self.assertRaisesRegex(ValueError, "smoke blocked"):
                repeat.run_experiment(
                    "explore", Path(directory) / "explore",
                    smoke_manifest=Path(directory) / "smoke.manifest.json",
                )
            self.assertEqual(validate.call_args.args[1], "smoke")
            self.assertTrue(validate.call_args.kwargs["strict_replay"])
            simulate.assert_not_called()

    def test_cli_help_does_not_run_a_research_seed(self):
        result = subprocess.run(
            [sys.executable, str(repeat.ROOT / "tools/run_delayed_ack_repeat_control.py"),
             "--help"], cwd=repeat.ROOT, text=True, capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--smoke-manifest", result.stdout)

    def test_tx_start_windows_charge_complete_airtime_and_bytes(self):
        sample = repeat.run_one(self.tiny_case(), repeat.BASELINE, 7)
        template = sample.transmissions[0]
        transmissions = [
            {**template, "tx_id": 10001, "start": 629.9, "end": 630.2},
            {**template, "tx_id": 10002, "start": 630.1, "end": 630.4},
        ]
        primary = repeat.physical_cost(transmissions, 630.0, 32)
        extended = repeat.physical_cost(transmissions, 660.0, 32)
        self.assertEqual(primary["tx_count"], 1)
        self.assertAlmostEqual(primary["tx_airtime_s"], 0.3)
        self.assertEqual(extended["tx_count"], 2)
        self.assertAlmostEqual(extended["tx_airtime_s"], 0.6)
        self.assertEqual(extended["tx_bytes"], primary["tx_bytes"] * 2)

    def test_physical_cost_preserves_rrep_wire_size_after_json_round_trip(self):
        packet = Packet(
            "RREP", 1, 2, 0, 6, 0.0, repeat.BASELINE,
            request_id=1, path=(2, 1, 0), learned_path=(0, 1, 2),
            app_payload=False,
        )
        transmissions = json.loads(json.dumps([{
            "start": 1.0, "end": 1.1, "packet": asdict(packet),
        }]))

        cost = repeat.physical_cost(transmissions, 630.0, 32)

        self.assertEqual(cost["tx_bytes"], packet.wire_size_bytes(32))
        self.assertEqual(cost["control_bytes"], packet.wire_size_bytes(32))

    def test_tail_flag_reports_first_ack_queued_beyond_extended_cutoff(self):
        case, primary, extended = self.tail_run(
            decode_before_cutoff_s=3.0, first_lag_s=4.0,
        )
        row = repeat.run_row(primary, extended, case)
        self.assertEqual(row["unstarted_first_ack_at_660"], 1)
        self.assertEqual(row["extended_ack_tx"],
                         repeat.physical_cost(extended.transmissions,
                                              case.duration_s + 60.0,
                                              case.payload_bytes)["ack_tx"])

    def test_repeat_count_excludes_ack_queued_beyond_extended_cutoff(self):
        case, primary, extended = self.tail_run(
            decode_before_cutoff_s=4.0, first_lag_s=2.0, repeat_lag_s=5.0,
        )
        row = repeat.run_row(primary, extended, case)
        expected_started = sum(
            item["repeat_ack_start_at"] is not None
            and item["repeat_ack_start_at"] <= case.duration_s + 60.0
            for item in repeat.audit_ack_contract(extended)
        )
        self.assertEqual(row["repeat_ack_tx"], expected_started)

    def test_smoke_entrypoint_with_injected_tiny_case_writes_valid_manifest(self):
        case = replace(self.tiny_case(), key="recurring_fading")
        with TemporaryDirectory() as directory, patch.object(
            repeat, "seeds_for_split", return_value=(7,)
        ), patch.dict(repeat.sr.SR_CASES, {"recurring_fading": case}):
            paths = repeat.run_experiment("smoke", Path(directory) / "smoke")
            repeat.validate_manifest(
                paths["manifest"], "smoke", repeat.input_hashes(),
                case=case, seeds=(7,), strict_replay=True,
            )


if __name__ == "__main__":
    unittest.main()
