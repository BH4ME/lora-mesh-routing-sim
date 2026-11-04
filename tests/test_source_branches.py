import copy
import hashlib
import json
import unittest
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from lora_mesh_sim import Node
from tools.run_sr_experiment import SR_CASES, SrCase
from tools.diagnose_source_branches import BranchSimulator, run_trace, write_artifacts


class SourceBranchDiagnosticTest(unittest.TestCase):
    def synthetic_case(self) -> SrCase:
        return SrCase(
            key="synthetic", nodes=2, area_m=20.0, duration_s=25.0,
            rate_per_min=1.0, pair_mode="random", pair_count=0,
            shadow_sigma_db=0.0, temporal_fading_sigma_db=0.0,
        )

    def test_no_local_exposure_is_a_recorded_result(self) -> None:
        case = self.synthetic_case()
        trace = [(1.0, 0, 1, 1)]

        result = run_trace(
            case, 17, [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)], trace,
        )

        self.assertEqual(result["scheduled_trace"], trace)
        self.assertEqual(result["eligible_targets"], [])
        self.assertEqual(result["branches"], [])

    def test_one_source_ack_miss_opens_all_four_target_only_branches(self) -> None:
        class ScriptedChannel(BranchSimulator):
            def try_receive(self, tx, receiver):
                rx = super().try_receive(tx, receiver)
                if (tx.packet.flow_id == 2 and tx.packet.kind == "ACK"
                        and receiver == 0):
                    return None
                if (tx.packet.flow_id == 3 and tx.packet.kind == "DATA"
                        and tx.packet.repair_index is None and receiver == 1):
                    return None
                return rx

        result = run_trace(
            self.synthetic_case(), 17,
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            [(1.0, 0, 1, 1), (3.0, 0, 1, 2), (20.0, 0, 1, 3)],
            simulator_cls=ScriptedChannel,
        )

        self.assertEqual([row["flow_id"] for row in result["eligible_targets"]], [3])
        self.assertEqual(result["eligible_targets"][0]["route_hops"], 1)
        self.assertEqual({row["arm"] for row in result["branches"]},
                         {"R", "F", "R-F", "R-R"})
        self.assertTrue(all(row["prefix_match"] for row in result["branches"]))
        self.assertEqual(
            {row["arm"]: row["initial_source_kind"] for row in result["branches"]},
            {"R": "DATA", "F": "FLOOD", "R-F": "DATA", "R-R": "DATA"},
        )

    def test_guard_and_actual_rescue_starts_are_distinct_observations(self) -> None:
        class DropInitialTargetData(BranchSimulator):
            def try_receive(self, tx, receiver):
                rx = super().try_receive(tx, receiver)
                if (tx.packet.flow_id == 2 and tx.packet.kind == "ACK"
                        and receiver == 0):
                    return None
                if (tx.packet.flow_id == 3 and tx.packet.kind == "DATA"
                        and tx.packet.repair_index is None and receiver == 1):
                    return None
                return rx

        result = run_trace(
            self.synthetic_case(), 17,
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            [(1.0, 0, 1, 1), (3.0, 0, 1, 2), (20.0, 0, 1, 3)],
            simulator_cls=DropInitialTargetData,
        )
        rows = {row["arm"]: row for row in result["branches"]}

        self.assertFalse(rows["R"]["ack_by_deadline"])
        self.assertTrue(rows["F"]["ack_by_deadline"])
        self.assertTrue(rows["R-F"]["guard_admitted"])
        self.assertEqual(rows["R-F"]["rescue_source_kind"], "FLOOD")
        self.assertTrue(rows["R-R"]["guard_admitted"])
        self.assertEqual(rows["R-R"]["rescue_source_kind"], "DATA")
        self.assertEqual(rows["R-F"]["rescue_started"], True)
        self.assertGreaterEqual(rows["R-F"]["network_window_airtime_s"],
                                rows["R-F"]["target_window_airtime_s"])
        self.assertGreaterEqual(rows["R-F"]["network_full_run_airtime_s"],
                                rows["R-F"]["network_window_airtime_s"])

    def test_artifacts_keep_empty_exposure_and_verifiable_provenance(self) -> None:
        result = run_trace(
            self.synthetic_case(), 17,
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            [(1.0, 0, 1, 1)],
        )
        with TemporaryDirectory() as directory:
            paths = write_artifacts(Path(directory) / "branches", [result], "synthetic")
            manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))

            self.assertEqual(manifest["seeds"], [17])
            self.assertEqual(manifest["eligible_targets"], 0)
            self.assertEqual(manifest["branch_rows"], 0)
            self.assertEqual(paths["targets"].read_text(encoding="utf-8"), "")
            self.assertEqual(paths["branches"].read_text(encoding="utf-8"), "")
            saved_trace = json.loads(paths["trace"].read_text(encoding="utf-8"))
            self.assertEqual(saved_trace["seed"], 17)
            self.assertEqual(saved_trace["scheduled_trace"],
                             json.loads(json.dumps(result["scheduled_trace"])))
            self.assertEqual(saved_trace["scheduled_trace_sha256"],
                             result["scheduled_trace_sha256"])
            self.assertEqual(
                manifest["artifact_sha256"]["targets"],
                hashlib.sha256(b"").hexdigest(),
            )
            self.assertEqual(
                manifest["artifact_sha256"]["trace"],
                hashlib.sha256(paths["trace"].read_bytes()).hexdigest(),
            )
            self.assertIn("tools/diagnose_source_branches.py", manifest["source_sha256"])
            self.assertEqual(manifest["runs"][0]["scheduled_trace_sha256"],
                             result["scheduled_trace_sha256"])
            with self.assertRaises(FileExistsError):
                write_artifacts(Path(directory) / "branches", [result], "synthetic")

    def test_artifacts_reject_incomplete_or_mismatched_branch_evidence(self) -> None:
        class DropAck(BranchSimulator):
            def try_receive(self, tx, receiver):
                rx = super().try_receive(tx, receiver)
                return None if (tx.packet.flow_id == 2 and tx.packet.kind == "ACK"
                                and receiver == 0) else rx

        result = run_trace(
            self.synthetic_case(), 17,
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            [(1.0, 0, 1, 1), (3.0, 0, 1, 2), (20.0, 0, 1, 3)],
            simulator_cls=DropAck,
        )
        self.assertEqual(len(result["branches"]), 4)
        with TemporaryDirectory() as directory:
            incomplete = copy.deepcopy(result)
            incomplete["branches"].pop()
            with self.assertRaisesRegex(ValueError, "four branch arms"):
                write_artifacts(Path(directory) / "incomplete", [incomplete], "synthetic")

            wrong_prefix = copy.deepcopy(result)
            wrong_prefix["branches"][0]["pre_app_prefix_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "prefix"):
                write_artifacts(Path(directory) / "prefix", [wrong_prefix], "synthetic")

            wrong_trace = copy.deepcopy(result)
            wrong_trace["scheduled_trace_sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "trace"):
                write_artifacts(Path(directory) / "trace", [wrong_trace], "synthetic")

    def test_booked_future_source_tx_is_not_a_physical_exposure(self) -> None:
        class QueuedTarget(BranchSimulator):
            def schedule(self, when, event_type, data):
                if event_type == "app_send" and data[2] == 3:
                    super().schedule(
                        19.9, "protocol_timer",
                        lambda: setattr(self.nodes[0], "tx_available_at", 80.0),
                    )
                super().schedule(when, event_type, data)

            def try_receive(self, tx, receiver):
                rx = super().try_receive(tx, receiver)
                return None if (tx.packet.flow_id == 2 and tx.packet.kind == "ACK"
                                and receiver == 0) else rx

        result = run_trace(
            self.synthetic_case(), 17,
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            [(1.0, 0, 1, 1), (3.0, 0, 1, 2), (20.0, 0, 1, 3)],
            simulator_cls=QueuedTarget,
        )

        self.assertEqual(len(result["branches"]), 4)
        for row in result["branches"]:
            self.assertTrue(row["prefix_match"])
            self.assertFalse(row["initial_exposed_by_deadline"])
            self.assertIsNone(row["initial_source_kind"])
            self.assertFalse(row["rescue_started"])
            self.assertEqual(row["source_data_starts"], [])
            self.assertGreaterEqual(row["queued_after_full_run_tx_count"], 1)

    def test_standard_scheduler_rebuilds_the_same_small_trace(self) -> None:
        from tools.diagnose_source_branches import run_seed

        first = run_seed(self.synthetic_case(), 17)
        second = run_seed(self.synthetic_case(), 17)

        self.assertEqual(first["scheduled_trace"], second["scheduled_trace"])
        self.assertEqual(first["scheduled_trace_sha256"],
                         second["scheduled_trace_sha256"])
        self.assertTrue(first["scheduled_trace"])
        self.assertTrue(all(when < self.synthetic_case().duration_s
                            for when, _, _, _ in first["scheduled_trace"]))

    def test_cli_exposes_only_the_declared_smoke_and_exploratory_splits(self) -> None:
        from tools.diagnose_source_branches import parse_args

        smoke = parse_args(["--split", "smoke", "--out-prefix", "smoke-out"])
        exploratory = parse_args([
            "--split", "exploratory", "--out-prefix", "explore-out",
        ])

        self.assertEqual(smoke.seeds, (34000,))
        self.assertEqual(exploratory.seeds, tuple(range(34001, 34006)))

    def test_cli_refuses_to_label_results_with_changed_source(self) -> None:
        from tools.diagnose_source_branches import main

        with (patch("tools.diagnose_source_branches.source_hashes",
                    side_effect=[{"source": "before"}, {"source": "after"}]),
              patch("tools.diagnose_source_branches.run_seed",
                    return_value={"eligible_targets": [], "branches": []}),
              patch("tools.diagnose_source_branches.write_artifacts",
                    return_value={"manifest": Path("unused")}) as writer):
            with self.assertRaisesRegex(RuntimeError, "source files changed"):
                main(["--split", "smoke", "--out-prefix", "unused"])
            writer.assert_not_called()

    def test_manifest_split_requires_frozen_case_and_exact_seed_set(self) -> None:
        result = run_trace(
            self.synthetic_case(), 17,
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            [(1.0, 0, 1, 1)],
        )
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "frozen recurring_fading case"):
                write_artifacts(Path(directory) / "wrong-case", [result], "smoke")

            wrong_seed = copy.deepcopy(result)
            wrong_seed["case"] = asdict(SR_CASES["recurring_fading"])
            wrong_seed["case_config_sha256"] = hashlib.sha256(
                json.dumps(wrong_seed["case"], sort_keys=True,
                           separators=(",", ":")).encode("ascii")
            ).hexdigest()
            with self.assertRaisesRegex(ValueError, "exact exploratory seeds"):
                write_artifacts(Path(directory) / "wrong-seed", [wrong_seed],
                                "exploratory")

    def test_admitted_guard_with_rejected_pending_send_has_no_rescue_start(self) -> None:
        class RejectPendingRescue(BranchSimulator):
            def try_receive(self, tx, receiver):
                rx = super().try_receive(tx, receiver)
                if (tx.packet.flow_id == 2 and tx.packet.kind == "ACK"
                        and receiver == 0):
                    return None
                if (tx.packet.flow_id == 3 and tx.packet.kind == "DATA"
                        and tx.packet.repair_index is None and receiver == 1):
                    return None
                return rx

            def transmit_later(self, sender, packet, delay_s, pending=None):
                if (packet.flow_id == 3 and packet.repair_index in {1, 2}
                        and sender == 0):
                    self.nodes[sender].tx_available_at = self.now + 1.0
                return super().transmit_later(sender, packet, delay_s, pending)

        result = run_trace(
            self.synthetic_case(), 17,
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            [(1.0, 0, 1, 1), (3.0, 0, 1, 2), (20.0, 0, 1, 3)],
            simulator_cls=RejectPendingRescue,
        )

        rows = {row["arm"]: row for row in result["branches"]}
        for arm in ("R-F", "R-R"):
            self.assertTrue(rows[arm]["guard_admitted"])
            self.assertFalse(rows[arm]["rescue_started"])
            self.assertIsNone(rows[arm]["rescue_source_kind"])
            self.assertEqual(rows[arm]["rescue_nonstart_reason"],
                             "pending_start_guard_rejected")

    def test_post_deadline_source_start_is_charged_to_full_run_only(self) -> None:
        class LateTarget(BranchSimulator):
            def schedule(self, when, event_type, data):
                if event_type == "app_send" and data[2] == 3:
                    super().schedule(
                        19.9, "protocol_timer",
                        lambda: setattr(self.nodes[0], "tx_available_at", 51.0),
                    )
                super().schedule(when, event_type, data)

            def try_receive(self, tx, receiver):
                rx = super().try_receive(tx, receiver)
                return None if (tx.packet.flow_id == 2 and tx.packet.kind == "ACK"
                                and receiver == 0) else rx

        result = run_trace(
            self.synthetic_case(), 17,
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            [(1.0, 0, 1, 1), (3.0, 0, 1, 2), (20.0, 0, 1, 3)],
            simulator_cls=LateTarget,
        )

        for row in result["branches"]:
            self.assertFalse(row["initial_exposed_by_deadline"])
            self.assertEqual(row["initial_nonexposure_reason"],
                             "initial_started_after_deadline")
            self.assertEqual(row["target_window_airtime_s"], 0.0)
            self.assertGreater(row["target_post_deadline_airtime_s"], 0.0)
            self.assertGreaterEqual(row["target_flow_full_run_airtime_s"],
                                    row["target_post_deadline_airtime_s"])

    def test_guard_denial_keeps_target_in_four_arm_results(self) -> None:
        class BusyAtGuard(BranchSimulator):
            def schedule(self, when, event_type, data):
                if event_type == "app_send" and data[2] == 3:
                    super().schedule(
                        34.9, "protocol_timer",
                        lambda: setattr(self.nodes[0], "tx_available_at", 60.0),
                    )
                super().schedule(when, event_type, data)

            def try_receive(self, tx, receiver):
                rx = super().try_receive(tx, receiver)
                if (tx.packet.flow_id == 2 and tx.packet.kind == "ACK"
                        and receiver == 0):
                    return None
                if (tx.packet.flow_id == 3 and tx.packet.kind == "DATA"
                        and tx.packet.repair_index is None and receiver == 1):
                    return None
                return rx

        result = run_trace(
            self.synthetic_case(), 17,
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            [(1.0, 0, 1, 1), (3.0, 0, 1, 2), (20.0, 0, 1, 3)],
            simulator_cls=BusyAtGuard,
        )

        rows = {row["arm"]: row for row in result["branches"]}
        self.assertEqual(set(rows), {"R", "F", "R-F", "R-R"})
        for arm in ("R-F", "R-R"):
            self.assertFalse(rows[arm]["guard_admitted"])
            self.assertEqual(rows[arm]["guard_reason"], "source-busy")
            self.assertFalse(rows[arm]["rescue_started"])
            self.assertIsNone(rows[arm]["rescue_nonstart_reason"])

    def test_background_flood_relay_delay_survives_an_earlier_flood(self) -> None:
        from lora_mesh_sim import RadioConfig
        from tools.diagnose_source_branches import BranchProtocol

        def later_flood_delay(with_earlier_flood):
            protocol = BranchProtocol()
            sim = BranchSimulator(
                [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0), Node(2, 20.0, 0.0)],
                RadioConfig(sf=7, shadow_sigma_db=0.0,
                            temporal_fading_sigma_db=0.0),
                protocol, seed=17, max_hops=6,
                independent_random_streams=True, matched_rreq_timing=True,
            )
            if with_earlier_flood:
                sim.schedule(1.0, "app_send", (0, 2, 1))
            sim.schedule(10.0, "app_send", (2, 0, 2))
            sim.run(20.0)
            source = next(tx for tx in sim.tx_history
                          if tx.packet.flow_id == 2 and tx.sender == 2
                          and tx.packet.kind == "FLOOD")
            relay = next(tx for tx in sim.tx_history
                         if tx.packet.flow_id == 2 and tx.sender == 1
                         and tx.packet.kind == "FLOOD")
            return relay.start - source.end

        self.assertEqual(later_flood_delay(False), later_flood_delay(True))

    def test_reception_pairing_excludes_packet_kind_and_counts_half_duplex(self) -> None:
        from lora_mesh_sim import Packet, RadioConfig, Transmission
        from tools.diagnose_source_branches import BranchProtocol

        def simulator():
            return BranchSimulator(
                [Node(0, 0.0, 0.0), Node(1, 12_000.0, 0.0)],
                RadioConfig(sf=7, shadow_sigma_db=0.0,
                            temporal_fading_sigma_db=0.0),
                BranchProtocol(), seed=17, max_hops=6,
                independent_random_streams=True,
            )

        def outcomes(kind):
            sim = simulator()
            values = []
            for flow_id in range(1, 17):
                packet = Packet(
                    kind=kind, flow_id=flow_id, origin=0, final_dst=1,
                    ttl=6, created_at=1.0, protocol="synthetic", path=(0, 1),
                )
                tx = Transmission(flow_id, 0, packet, 1.0, 1.1)
                values.append(sim.try_receive(tx, 1) is not None)
            return values

        data_outcomes = outcomes("DATA")
        self.assertEqual(data_outcomes, outcomes("FLOOD"))
        self.assertIn(True, data_outcomes)
        self.assertIn(False, data_outcomes)

        sim = simulator()
        packet = Packet(
            kind="DATA", flow_id=99, origin=0, final_dst=1,
            ttl=6, created_at=1.0, protocol="synthetic", path=(0, 1),
        )
        tx = Transmission(99, 0, packet, 1.0, 1.1)
        sim.transmissions = [Transmission(100, 1, packet, 1.0, 1.1)]
        self.assertIsNone(sim.try_receive(tx, 1))
        sim.transmissions = []
        sim.try_receive(tx, 1)
        self.assertEqual(sim.reception_ordinals[(99, 0, 1)], 2)
