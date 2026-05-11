import argparse
import json
import tempfile
import unittest
from pathlib import Path

from lora_mesh_sim import (
    CalmMesh,
    FlowDecision,
    Node,
    RadioConfig,
    RouteEntry,
    Simulator,
    SmartCalmMesh,
    build_protocol,
    run_one,
)


class CalmProtocolTest(unittest.TestCase):
    def test_calm_protocol_runs_and_reports_confidence_metrics(self) -> None:
        protocol = build_protocol("calm")
        self.assertEqual(protocol.name, "calm-mesh")

        args = argparse.Namespace(
            nodes=12,
            area_m=1200.0,
            duration_s=90.0,
            rate_per_min=8.0,
            traffic="unicast",
            pair_count=2,
            max_hops=6,
            repeater_ratio=0.0,
            sf=9,
            bw_hz=125_000,
            cr=1,
            payload_bytes=32,
            tx_power_dbm=17.0,
            path_loss_exp=2.7,
            shadow_sigma_db=4.0,
            capture_threshold_db=6.0,
            calm_route_ttl_s=600.0,
            calm_discovery_window_s=2.4,
            calm_flood_base_delay_s=0.45,
            calm_flood_jitter_s=0.65,
            calm_fallback_ttl=2,
            calm_fallback_confidence_threshold=0.0,
            calm_fallback_delay_margin_s=0.6,
            calm_hop_penalty_per_hop=0.025,
            calm_route_age_penalty=0.1,
        )

        row = run_one(args, "calm", seed=3)

        self.assertEqual(row["protocol"], "calm-mesh")
        self.assertIn("mean_path_confidence", row)
        self.assertIn("fallback_forward_count", row)
        self.assertIn("control_overhead_ratio", row)
        self.assertGreaterEqual(row["mean_path_confidence"], 0.0)
        self.assertLessEqual(row["mean_path_confidence"], 1.0)

    def test_calm_parameters_are_applied_from_run_args(self) -> None:
        args = argparse.Namespace(
            nodes=18,
            area_m=1800.0,
            duration_s=500.0,
            rate_per_min=12.0,
            traffic="unicast",
            pair_count=3,
            max_hops=6,
            repeater_ratio=0.0,
            sf=9,
            bw_hz=125_000,
            cr=1,
            payload_bytes=32,
            tx_power_dbm=17.0,
            path_loss_exp=2.7,
            shadow_sigma_db=5.0,
            capture_threshold_db=6.0,
            calm_route_ttl_s=600.0,
            calm_discovery_window_s=2.4,
            calm_flood_base_delay_s=0.45,
            calm_flood_jitter_s=0.65,
            calm_fallback_ttl=2,
            calm_fallback_confidence_threshold=1.0,
            calm_fallback_delay_margin_s=0.6,
            calm_hop_penalty_per_hop=0.025,
            calm_route_age_penalty=0.1,
        )
        aggressive = run_one(args, "calm", seed=7)

        args.calm_fallback_confidence_threshold = 0.0
        conservative = run_one(args, "calm", seed=7)

        self.assertGreater(
            aggressive["fallback_forward_count"],
            conservative["fallback_forward_count"],
        )

    def test_smart_calm_runs_and_updates_policy_online(self) -> None:
        protocol = build_protocol("smart-calm")
        self.assertEqual(protocol.name, "smart-calm")

        args = argparse.Namespace(
            nodes=18,
            area_m=1800.0,
            duration_s=420.0,
            rate_per_min=12.0,
            traffic="mixed",
            pair_count=3,
            max_hops=6,
            repeater_ratio=0.0,
            sf=9,
            bw_hz=125_000,
            cr=1,
            payload_bytes=32,
            tx_power_dbm=17.0,
            path_loss_exp=2.7,
            shadow_sigma_db=5.0,
            capture_threshold_db=6.0,
            calm_route_ttl_s=600.0,
            calm_discovery_window_s=2.4,
            calm_flood_base_delay_s=0.45,
            calm_flood_jitter_s=0.65,
            calm_fallback_ttl=2,
            calm_fallback_confidence_threshold=0.0,
            calm_fallback_delay_margin_s=0.6,
            calm_hop_penalty_per_hop=0.025,
            calm_route_age_penalty=0.1,
            smart_update_interval_s=60.0,
            smart_learning_rate=0.35,
            smart_exploration=0.2,
        )

        row = run_one(args, "smart-calm", seed=11)

        self.assertEqual(row["protocol"], "smart-calm")
        self.assertGreater(row["policy_update_count"], 0)
        self.assertGreaterEqual(row["policy_switch_count"], 0)
        self.assertIn(row["active_profile_index"], {0, 1, 2})

    def test_smart_calm_records_decision_context_before_transmission(self) -> None:
        protocol = SmartCalmMesh(update_interval_s=999.0, exploration=0.0)
        nodes = [
            Node(0, 0.0, 0.0),
            Node(1, 100.0, 0.0),
        ]
        Simulator(nodes, RadioConfig(), protocol, seed=1, max_hops=3)

        protocol.route_cache[0][1] = RouteEntry(
            created_at=0.0,
            expires_at=100.0,
            path=(0, 1),
            confidence=0.82,
        )
        protocol.send_app(0, 1, flow_id=1)
        self.assertGreater(protocol.flow_decisions[1].confidence, 0.8)

        protocol.route_cache[0].clear()
        protocol.send_app(0, 1, flow_id=2)
        self.assertEqual(protocol.flow_decisions[2].route_miss, 1)

    def test_smart_calm_selects_policy_for_each_unicast_flow(self) -> None:
        protocol = SmartCalmMesh(update_interval_s=999.0, exploration=0.0)
        nodes = [
            Node(0, 0.0, 0.0),
            Node(1, 100.0, 0.0),
        ]
        sim = Simulator(nodes, RadioConfig(), protocol, seed=2, max_hops=3)
        protocol.q_values[(0, 2)] = 1.0

        protocol.send_app(0, 1, flow_id=1)

        self.assertEqual(protocol.active_profile_index, 2)
        self.assertEqual(protocol.flow_decisions[1].action_index, 2)
        self.assertEqual(sim.metrics.policy_switch_count, 1)

    def test_smart_calm_retries_undelivered_unicast_after_timeout(self) -> None:
        protocol = SmartCalmMesh(
            update_interval_s=999.0,
            exploration=0.0,
            flow_timeout_s=0.3,
            max_timeout_retries=1,
        )
        nodes = [
            Node(0, 0.0, 0.0),
            Node(1, 4000.0, 0.0),
        ]
        sim = Simulator(
            nodes,
            RadioConfig(tx_power_dbm=0.0, path_loss_exp=4.0, shadow_sigma_db=0.0),
            protocol,
            seed=3,
            max_hops=3,
        )

        protocol.send_app(0, 1, flow_id=1)
        sim.run(until_s=1.0)

        summary = sim.metrics.summarize(protocol.name, seed=3, duration_s=1.0)
        self.assertEqual(summary["fallback_forward_count"], 1)

    def test_smart_calm_prefers_cached_path_retry_before_timeout_fallback(self) -> None:
        protocol = SmartCalmMesh(
            update_interval_s=999.0,
            exploration=0.0,
            flow_timeout_s=0.3,
            max_timeout_retries=1,
        )
        nodes = [
            Node(0, 0.0, 0.0),
            Node(1, 4000.0, 0.0),
        ]
        sim = Simulator(
            nodes,
            RadioConfig(tx_power_dbm=0.0, path_loss_exp=4.0, shadow_sigma_db=0.0),
            protocol,
            seed=8,
            max_hops=3,
        )
        protocol.route_cache[0][1] = RouteEntry(
            created_at=0.0,
            expires_at=100.0,
            path=(0, 1),
            confidence=0.95,
        )

        protocol.send_app(0, 1, flow_id=1)
        sim.run(until_s=1.0)

        summary = sim.metrics.summarize(protocol.name, seed=8, duration_s=1.0)
        self.assertEqual(summary["data_tx"], 2)
        self.assertEqual(summary["fallback_forward_count"], 0)

    def test_smart_calm_timeout_fallback_uses_active_profile_radius(self) -> None:
        protocol = SmartCalmMesh(
            update_interval_s=999.0,
            exploration=0.0,
            flow_timeout_s=0.3,
            max_timeout_retries=1,
        )
        nodes = [
            Node(0, 0.0, 0.0),
            Node(1, 80.0, 0.0),
            Node(2, 160.0, 0.0),
            Node(3, 5000.0, 0.0),
        ]
        sim = Simulator(
            nodes,
            RadioConfig(tx_power_dbm=0.0, path_loss_exp=4.0, shadow_sigma_db=0.0),
            protocol,
            seed=12,
            max_hops=7,
        )
        protocol.apply_profile(0)

        protocol.flow_decisions[1] = FlowDecision(
            src=0,
            dst=3,
            state_index=0,
            action_index=0,
            profile_name="lean",
            created_at=0.0,
        )
        sim.metrics.register_flow(1, 0, 3, 0.0)
        protocol.on_flow_completion(flow_id=1, delivered=False, now=0.3)
        sim.run(until_s=2.0)

        summary = sim.metrics.summarize(protocol.name, seed=12, duration_s=2.0)
        self.assertEqual(summary["fallback_forward_count"], 1)

    def test_smart_calm_does_not_stack_timeout_retry_after_route_miss_fallback(self) -> None:
        protocol = SmartCalmMesh(
            update_interval_s=999.0,
            exploration=0.0,
            flow_timeout_s=2.5,
            max_timeout_retries=1,
        )
        nodes = [
            Node(0, 0.0, 0.0),
            Node(1, 4000.0, 0.0),
        ]
        sim = Simulator(
            nodes,
            RadioConfig(tx_power_dbm=0.0, path_loss_exp=4.0, shadow_sigma_db=0.0),
            protocol,
            seed=4,
            max_hops=3,
        )

        protocol.send_app(0, 1, flow_id=1)
        sim.run(until_s=3.0)

        summary = sim.metrics.summarize(protocol.name, seed=4, duration_s=3.0)
        self.assertEqual(summary["fallback_forward_count"], 1)

    def test_smart_calm_bounds_route_miss_fallback_scope(self) -> None:
        protocol = SmartCalmMesh(
            update_interval_s=999.0,
            exploration=0.0,
            flow_timeout_s=5.0,
            route_miss_fallback_ttl=1,
        )
        nodes = [
            Node(0, 0.0, 0.0),
            Node(1, 80.0, 0.0),
            Node(2, 160.0, 0.0),
            Node(3, 5000.0, 0.0),
        ]
        sim = Simulator(
            nodes,
            RadioConfig(tx_power_dbm=0.0, path_loss_exp=4.0, shadow_sigma_db=0.0),
            protocol,
            seed=9,
            max_hops=7,
        )

        protocol.send_app(0, 3, flow_id=1)
        sim.run(until_s=3.0)

        summary = sim.metrics.summarize(protocol.name, seed=9, duration_s=3.0)
        self.assertEqual(summary["fallback_forward_count"], 1)

    def test_smart_calm_uses_full_route_miss_recovery_by_default(self) -> None:
        protocol = SmartCalmMesh(
            update_interval_s=999.0,
            exploration=0.0,
            flow_timeout_s=5.0,
        )
        nodes = [
            Node(0, 0.0, 0.0),
            Node(1, 80.0, 0.0),
            Node(2, 160.0, 0.0),
            Node(3, 5000.0, 0.0),
        ]
        sim = Simulator(
            nodes,
            RadioConfig(tx_power_dbm=0.0, path_loss_exp=4.0, shadow_sigma_db=0.0),
            protocol,
            seed=9,
            max_hops=7,
        )

        protocol.send_app(0, 3, flow_id=1)
        sim.run(until_s=5.0)

        summary = sim.metrics.summarize(protocol.name, seed=9, duration_s=3.0)
        self.assertGreater(summary["fallback_forward_count"], 1)

    def test_smart_calm_profiles_are_built_from_run_args(self) -> None:
        args = argparse.Namespace(
            smart_update_interval_s=60.0,
            smart_learning_rate=0.35,
            smart_exploration=0.18,
            calm_route_ttl_s=720.0,
            calm_discovery_window_s=3.1,
            calm_flood_base_delay_s=0.45,
            calm_flood_jitter_s=0.65,
            calm_fallback_ttl=4,
            calm_fallback_confidence_threshold=0.35,
            calm_fallback_delay_margin_s=0.8,
            calm_hop_penalty_per_hop=0.05,
            calm_route_age_penalty=0.2,
        )

        protocol = build_protocol("smart-calm", args)

        self.assertIsInstance(protocol, SmartCalmMesh)
        self.assertEqual(protocol.profiles[1].route_ttl_s, 720.0)
        self.assertEqual(protocol.profiles[1].discovery_window_s, 3.1)
        self.assertEqual(protocol.profiles[1].fallback_ttl, 4)
        self.assertEqual(protocol.profiles[1].fallback_confidence_threshold, 0.35)
        self.assertEqual(protocol.profiles[1].fallback_delay_margin_s, 0.8)

    def test_smart_calm_default_learning_parameters_are_fast_and_conservative(self) -> None:
        calm = build_protocol("calm")
        protocol = build_protocol("smart-calm")

        self.assertIsInstance(calm, CalmMesh)
        self.assertEqual(calm.discovery_window_s, 2.0)
        self.assertIsInstance(protocol, SmartCalmMesh)
        self.assertEqual(protocol.update_interval_s, 30.0)
        self.assertEqual(protocol.learning_rate, 0.45)
        self.assertLessEqual(protocol.exploration, 0.02)
        self.assertEqual(protocol.flow_timeout_s, 35.0)
        self.assertEqual(protocol.max_timeout_retries, 2)
        self.assertEqual(protocol.discovery_window_s, 2.0)

    def test_partial_run_args_use_cli_discovery_window_default(self) -> None:
        args = argparse.Namespace()

        calm = build_protocol("calm", args)
        protocol = build_protocol("smart-calm", args)

        self.assertIsInstance(calm, CalmMesh)
        self.assertEqual(calm.discovery_window_s, 2.0)
        self.assertIsInstance(protocol, SmartCalmMesh)
        self.assertEqual(protocol.profiles[1].discovery_window_s, 2.0)
        self.assertEqual(protocol.discovery_window_s, 2.0)

    def test_smart_calm_can_load_a_policy_prior(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            prior_path = Path(tmpdir) / "smart_prior.json"
            prior_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "q_values": [
                            {"state": 2, "action": 1, "value": 3.5},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            args = argparse.Namespace(
                smart_prior_json=prior_path,
                smart_update_interval_s=60.0,
                smart_learning_rate=0.35,
                smart_exploration=0.18,
                smart_flow_timeout_s=35.0,
                calm_route_ttl_s=720.0,
                calm_discovery_window_s=3.1,
                calm_flood_base_delay_s=0.45,
                calm_flood_jitter_s=0.65,
                calm_fallback_ttl=4,
                calm_fallback_confidence_threshold=0.35,
                calm_fallback_delay_margin_s=0.8,
                calm_hop_penalty_per_hop=0.05,
                calm_route_age_penalty=0.2,
            )

            protocol = build_protocol("smart-calm", args)
            nodes = [
                Node(0, 0.0, 0.0),
                Node(1, 10.0, 0.0),
            ]
            Simulator(nodes, RadioConfig(), protocol, seed=4, max_hops=3)

            self.assertIn((2, 1), protocol.q_values)
            self.assertEqual(protocol.q_values[(2, 1)], 3.5)

    def test_calm_cancels_delayed_fallback_after_route_delivery(self) -> None:
        protocol = CalmMesh(fallback_confidence_threshold=1.0, fallback_ttl=2)
        nodes = [
            Node(0, 0.0, 0.0),
            Node(1, 1.0, 0.0),
        ]
        sim = Simulator(
            nodes,
            RadioConfig(shadow_sigma_db=0.0),
            protocol,
            seed=5,
            max_hops=3,
        )
        protocol.route_cache[0][1] = RouteEntry(
            created_at=0.0,
            expires_at=100.0,
            path=(0, 1),
            confidence=0.5,
        )

        protocol.send_app(0, 1, flow_id=1)
        sim.run(until_s=2.0)

        summary = sim.metrics.summarize(protocol.name, seed=5, duration_s=2.0)
        self.assertEqual(summary["unicast_pdr"], 1.0)
        self.assertEqual(summary["fallback_forward_count"], 0)

    def test_calm_delays_fallback_by_configured_grace_margin(self) -> None:
        def build_sim() -> Simulator:
            protocol = CalmMesh(
                fallback_confidence_threshold=1.0,
                fallback_delay_margin_s=1.0,
                fallback_ttl=2,
            )
            nodes = [
                Node(0, 0.0, 0.0),
                Node(1, 4000.0, 0.0),
            ]
            sim = Simulator(
                nodes,
                RadioConfig(tx_power_dbm=0.0, path_loss_exp=4.0, shadow_sigma_db=0.0),
                protocol,
                seed=6,
                max_hops=3,
            )
            protocol.route_cache[0][1] = RouteEntry(
                created_at=0.0,
                expires_at=100.0,
                path=(0, 1),
                confidence=0.5,
            )
            protocol.send_app(0, 1, flow_id=1)
            return sim

        early_sim = build_sim()
        early_sim.run(until_s=0.9)
        early_summary = early_sim.metrics.summarize(
            early_sim.protocol.name,
            seed=6,
            duration_s=0.9,
        )
        self.assertEqual(early_summary["fallback_forward_count"], 0)

        late_sim = build_sim()
        late_sim.run(until_s=1.4)
        late_summary = late_sim.metrics.summarize(
            late_sim.protocol.name,
            seed=6,
            duration_s=1.4,
        )
        self.assertEqual(late_summary["fallback_forward_count"], 1)


if __name__ == "__main__":
    unittest.main()
