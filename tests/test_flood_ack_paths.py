"""Public-behavior checks for the passive flood ACK-path diagnostic."""

import unittest

from lora_mesh_sim import Node, Packet, RadioConfig, build_protocol
from tools.diagnose_flood_ack_paths import (
    FloodAckPathSimulator, analyze_paths, build_report, run_diagnostic,
)
from tools.run_sr_experiment import SrCase


class FloodAckPathDiagnosticTests(unittest.TestCase):
    def test_simulated_sinr_is_not_claimed_as_device_local(self) -> None:
        observed = analyze_paths([], [])

        for field in (
            "rx_sinr_db", "enqueued_at", "deadline_at", "deadline_budget_upper_bound",
        ):
            self.assertNotIn(field, observed["device_local_receipt_fields"])
            self.assertIn(field, observed["offline_only_fields"])

    def test_report_aggregates_only_its_exploratory_runs(self) -> None:
        case = SrCase(
            key="tiny_flood_ack_report", nodes=4, area_m=100.0,
            duration_s=8.0, rate_per_min=30.0, pair_mode="random",
            pair_count=0, max_hops=3, temporal_fading_sigma_db=0.0,
        )

        report = build_report((13001,), case=case)

        self.assertEqual(report["seed_use"], "mechanical-test-only")
        self.assertEqual(report["summary"]["runs"], 1)
        self.assertEqual(
            report["summary"]["scheduled_unicast_flows"],
            report["runs"][0]["parity"]["baseline"]["scheduled_unicast_flows"],
        )
        self.assertIn("simulator", report["source_sha256"])

    def test_window_counts_distinct_paths_without_inventing_ack_success(self) -> None:
        flow_rows = [{
            "flow_id": 1, "src": 0, "dst": 3, "enqueued_at": 0.0,
            "deadline_at": 30.0, "delivered_at": 5.0, "acked_at": None,
            "delivery_by_deadline": True, "ack_by_deadline": False,
            "source_action": "F",
        }]
        receipts = [
            {"flow_id": 1, "received_at_s": when, "path": path}
            for when, path in (
                (5.0, (0, 1, 3)), (5.2, (0, 1, 3)),
                (5.3, (0, 2, 3)), (5.9, (0, 4, 3)),
                (7.1, (0, 5, 3)),
            )
        ]

        observed = analyze_paths(receipts, flow_rows)

        flow = observed["flows"][0]
        self.assertEqual(
            [flow["oracle_windows"][label]["distinct_paths"]
             for label in ("0.25s", "0.5s", "1s", "2s")],
            [1, 2, 3, 3],
        )
        self.assertEqual(observed["summary"]["delivered_unacked_flows"], 1)
        self.assertEqual(
            observed["summary"]["delivered_unacked_with_alternate_path"]["0.5s"],
            1,
        )
        self.assertFalse(flow["ack_by_deadline"])

    def test_post_deadline_decode_is_recorded_but_not_an_ack_opportunity(self) -> None:
        flow_rows = [{
            "flow_id": 2, "src": 0, "dst": 3, "enqueued_at": 0.0,
            "deadline_at": 30.0, "delivered_at": 29.8, "acked_at": None,
            "delivery_by_deadline": True, "ack_by_deadline": False,
            "source_action": "F",
        }]
        receipts = [
            {"flow_id": 2, "received_at_s": 29.8, "path": (0, 1, 3)},
            {"flow_id": 2, "received_at_s": 30.1, "path": (0, 2, 3)},
        ]

        observed = analyze_paths(receipts, flow_rows)

        self.assertEqual(len(observed["flows"][0]["flood_receipts"]), 2)
        self.assertEqual(
            observed["flows"][0]["decoded_windows"]["0.5s"]["distinct_paths"], 2,
        )
        self.assertEqual(
            observed["flows"][0]["oracle_windows"]["0.5s"]["distinct_paths"], 1,
        )
        self.assertEqual(
            observed["summary"]["delivered_unacked_with_alternate_path"]["0.5s"],
            0,
        )

    def test_actual_ack_emission_is_separate_from_alternate_path_oracle(self) -> None:
        flow_rows = [{
            "flow_id": 3, "src": 0, "dst": 3, "enqueued_at": 0.0,
            "deadline_at": 30.0, "delivered_at": 5.0, "acked_at": None,
            "delivery_by_deadline": True, "ack_by_deadline": False,
            "source_action": "F",
        }]
        receipts = [
            {"flow_id": 3, "received_at_s": 5.0, "path": (0, 1, 3),
             "repair_index": None},
            {"flow_id": 3, "received_at_s": 5.3, "path": (0, 2, 3),
             "repair_index": None},
        ]
        emitted = [{"flow_id": 3, "started_at_s": 5.0,
                    "path": (0, 1, 3), "repair_index": None}]

        observed = analyze_paths(receipts, flow_rows, emitted)

        flow = observed["flows"][0]
        self.assertEqual(len(flow["actual_destination_ack_emissions"]), 1)
        self.assertEqual(
            flow["oracle_windows"]["0.5s"]["paths"][1]["reverse_ack_hop_order"],
            [3, 2, 0],
        )
        self.assertTrue(flow["first_delivery_was_initial_flood"])
        self.assertFalse(flow["ack_by_deadline"])

    def test_alternate_paths_are_stratified_by_first_delivery_type(self) -> None:
        flow_rows = [
            {"flow_id": flow_id, "src": 0, "dst": 3,
             "enqueued_at": 0.0, "deadline_at": 30.0,
             "delivered_at": 5.0, "acked_at": None,
             "delivery_by_deadline": True, "ack_by_deadline": False,
             "source_action": source_action}
            for flow_id, source_action in ((1, "F"), (2, "R"))
        ]
        receipts = [
            {"flow_id": flow_id, "received_at_s": when, "path": path,
             "repair_index": marker}
            for flow_id, when, path, marker in (
                (1, 5.0, (0, 1, 3), None),
                (1, 5.3, (0, 2, 3), None),
                (2, 5.1, (0, 1, 3), 2),
                (2, 5.4, (0, 2, 3), 2),
            )
        ]

        observed = analyze_paths(receipts, flow_rows)["summary"]

        self.assertEqual(
            observed["delivered_unacked_first_flood_with_alternate_path"]["0.5s"],
            1,
        )
        self.assertEqual(
            observed["delivered_unacked_first_route_with_alternate_flood_path"]["0.5s"],
            1,
        )
        self.assertEqual(
            observed["one_second_alternate_first_ack_hop_deadline_budget_s"],
            {"candidate_hops": 1, "flows": 1, "min_s": 24.7, "median_s": 24.7},
        )

    def test_distinct_full_paths_can_share_the_first_ack_hop(self) -> None:
        flow_rows = [{
            "flow_id": 4, "src": 0, "dst": 3, "enqueued_at": 0.0,
            "deadline_at": 30.0, "delivered_at": 5.0, "acked_at": None,
            "delivery_by_deadline": True, "ack_by_deadline": False,
            "source_action": "F",
        }]
        receipts = [
            {"flow_id": 4, "received_at_s": 5.0, "path": (0, 1, 3),
             "repair_index": None},
            {"flow_id": 4, "received_at_s": 5.5, "path": (0, 2, 1, 3),
             "repair_index": None},
        ]

        observed = analyze_paths(receipts, flow_rows)
        window = observed["flows"][0]["oracle_windows"]["1s"]

        self.assertEqual(window["distinct_paths"], 2)
        self.assertEqual(window["distinct_first_ack_hops"], 1)
        self.assertEqual(observed["summary"]["delivered_unacked_first_delivery_flood"], 1)
        self.assertEqual(observed["summary"]["delivered_unacked_first_delivery_route"], 0)
        self.assertEqual(
            observed["summary"]["delivered_unacked_with_alternate_first_ack_hop"]["1s"],
            0,
        )

    def test_raw_flow_times_and_distinct_ack_hop_deadline_budgets(self) -> None:
        flow_rows = [{
            "flow_id": 5, "src": 0, "dst": 3, "enqueued_at": 0.0,
            "deadline_at": 10.0, "delivered_at": 5.0, "acked_at": None,
            "delivery_by_deadline": True, "ack_by_deadline": False,
            "source_action": "F",
        }]
        receipts = [
            {"flow_id": 5, "received_at_s": when, "path": path,
             "repair_index": None}
            for when, path in (
                (5.0, (0, 1, 3)), (5.2, (0, 2, 3)),
                (5.5, (0, 4, 2, 3)), (5.8, (0, 4, 3)),
            )
        ]

        observed = analyze_paths(receipts, flow_rows)
        flow = observed["flows"][0]

        self.assertEqual(flow["enqueued_at"], 0.0)
        self.assertEqual(flow["deadline_at"], 10.0)
        self.assertEqual(
            observed["summary"]["one_second_alternate_first_ack_hop_deadline_budget_s"],
            {"candidate_hops": 2, "flows": 1, "min_s": 4.2, "median_s": 4.5},
        )

    def test_records_distinct_physical_flood_decodes_after_protocol_dedup(self) -> None:
        sim = FloodAckPathSimulator(
            [Node(0, 0, 0), Node(1, 10, 0, role="client"),
             Node(2, 0, 10, role="client"), Node(3, 10, 10)],
            RadioConfig(sf=7, shadow_sigma_db=0.0),
            build_protocol("meshecho-dhr-flood"), seed=7, max_hops=3,
        )
        sim.metrics.register_flow(1, 0, 3, 0.0)
        for relay, delay in ((1, 0.0), (2, 0.5)):
            sim.transmit_later(
                relay,
                Packet(
                    kind="FLOOD", flow_id=1, origin=0, final_dst=3,
                    ttl=2, created_at=0.0, protocol="meshecho-dhr-flood",
                    request_id=1, path=(0, relay),
                ),
                delay_s=delay,
            )

        sim.run(2.0)

        self.assertEqual(
            {tuple(receipt["path"]) for receipt in sim.destination_flood_receipts},
            {(0, 1, 3), (0, 2, 3)},
        )
        self.assertTrue(all(
            receipt["rx_sinr_db"] == receipt["rx_snr_db"]
            for receipt in sim.destination_flood_receipts
        ))
        self.assertEqual(
            sum(tx.packet.kind == "ACK" and tx.sender == 3 for tx in sim.tx_history),
            1,
        )

    def test_replay_preserves_fixed_f_flow_trace_and_outcomes(self) -> None:
        case = SrCase(
            key="tiny_flood_ack", nodes=4, area_m=100.0,
            duration_s=8.0, rate_per_min=30.0, pair_mode="random",
            pair_count=0, max_hops=3, temporal_fading_sigma_db=0.0,
        )

        result = run_diagnostic(13001, case=case)

        self.assertEqual(result["protocol"], "meshecho-dhr-flood")
        self.assertEqual(result["parity"]["baseline"], result["parity"]["replay"])
        self.assertGreater(result["parity"]["baseline"]["scheduled_unicast_flows"], 0)
        self.assertTrue(result["parity"]["per_flow_exact_timestamps"])


if __name__ == "__main__":
    unittest.main()
