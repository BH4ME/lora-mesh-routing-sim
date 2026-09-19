import argparse
import unittest
from pathlib import Path
from types import SimpleNamespace

from lora_mesh_sim import (
    ICC_PROTOCOLS,
    MESHECHO_ABLATIONS,
    MeshCoreLike,
    MeshEcho,
    MinHopMesh,
    MetricMesh,
    Packet,
    build_protocol,
)


class MetricRoutingBaselineTest(unittest.TestCase):
    def test_meshecho_is_primary_and_has_explicit_component_ablations(self) -> None:
        self.assertIn("meshecho", ICC_PROTOCOLS)
        self.assertNotIn("smart-calm", ICC_PROTOCOLS)
        self.assertEqual(
            set(MESHECHO_ABLATIONS),
            {
                "meshecho-no-confidence",
                "meshecho-no-fallback",
                "meshecho-no-hop-penalty",
                "meshecho-no-age-penalty",
            },
        )

        for name in MESHECHO_ABLATIONS:
            protocol = build_protocol(name)
            self.assertIsInstance(protocol, MeshEcho)
            self.assertTrue(protocol.name.startswith("meshecho-"))

        no_confidence = build_protocol("meshecho-no-confidence")
        no_fallback = build_protocol("meshecho-no-fallback")
        no_hop_penalty = build_protocol("meshecho-no-hop-penalty")
        no_age_penalty = build_protocol("meshecho-no-age-penalty")
        candidates = [
            ((0, 1, 2), 0.95),
            ((0, 3), 0.70),
        ]
        self.assertEqual(
            no_confidence.select_route_candidate(candidates, flow_id=1)[0],
            (0, 3),
        )
        self.assertFalse(no_fallback.route_miss_recovery_enabled)
        self.assertEqual(no_hop_penalty.hop_penalty_per_hop, 0.0)
        self.assertEqual(no_age_penalty.route_age_penalty, 0.0)

    def test_icc_registry_exposes_etx_and_airtime_metric_baselines(self) -> None:
        self.assertIn("etx", ICC_PROTOCOLS)
        self.assertIn("ett", ICC_PROTOCOLS)

        etx = build_protocol("etx")
        ett = build_protocol("ett")

        self.assertIsInstance(etx, MetricMesh)
        self.assertIsInstance(ett, MetricMesh)
        self.assertEqual(etx.name, "etx-mesh")
        self.assertEqual(ett.name, "ett-mesh")
        self.assertEqual(etx.metric_kind, "etx")
        self.assertEqual(ett.metric_kind, "ett")
        self.assertFalse(etx.route_miss_recovery_enabled)
        self.assertFalse(ett.route_miss_recovery_enabled)

    def test_icc_registry_exposes_distinct_min_hop_baseline(self) -> None:
        self.assertIn("minhop", ICC_PROTOCOLS)
        baseline = build_protocol("minhop")
        self.assertIsInstance(baseline, MinHopMesh)
        self.assertEqual(baseline.name, "minhop-mesh")
        self.assertFalse(baseline.route_miss_recovery_enabled)
        candidates = [
            ((0, 1, 2), 0.98),
            ((0, 3), 0.55),
        ]
        self.assertEqual(
            baseline.select_route_candidate(candidates, flow_id=1)[0],
            (0, 3),
        )

    def test_metric_scores_are_monotone_and_airtime_aware(self) -> None:
        etx = build_protocol("etx")
        ett = build_protocol("ett")

        # A larger ETX/ETT cost must produce a lower route score.
        self.assertGreater(etx.score_from_cost(1.0), etx.score_from_cost(3.0))
        self.assertGreater(ett.score_from_cost(1.0), ett.score_from_cost(3.0))

        # ETT must distinguish the same reliability cost at different ToA.
        self.assertGreater(
            ett.cost_from_link(prr=0.8, toa_s=0.05),
            ett.cost_from_link(prr=0.8, toa_s=0.01),
        )
        # ETX is intentionally independent of ToA for the fixed-SF baseline.
        self.assertAlmostEqual(
            etx.cost_from_link(prr=0.8, toa_s=0.05),
            etx.cost_from_link(prr=0.8, toa_s=0.01),
        )

    def test_metric_baselines_accept_matched_discovery_configuration(self) -> None:
        args = argparse.Namespace(
            meshcore_route_ttl_s=600.0,
            meshcore_discovery_window_s=2.0,
        )
        etx = build_protocol("etx", args)
        ett = build_protocol("ett", args)
        self.assertEqual(etx.discovery_window_s, 2.0)
        self.assertEqual(ett.discovery_window_s, 2.0)
        self.assertEqual(etx.route_ttl_s, 600.0)
        self.assertEqual(ett.route_ttl_s, 600.0)

    def test_meshcore_collects_all_destination_candidates_in_matched_window(self) -> None:
        """Matched source routing must expose the same candidate pool as MeshEcho."""

        class FakeMetrics:
            duplicate_rx = 0

        class FakeSimulator:
            max_hops = 8
            now = 0.0
            metrics = FakeMetrics()
            nodes = {
                node_id: SimpleNamespace(can_relay=True)
                for node_id in range(4)
            }

        protocol = MeshCoreLike(discovery_window_s=2.0)
        protocol.bind(FakeSimulator())
        first = Packet(
            kind="RREQ",
            flow_id=9,
            origin=0,
            final_dst=2,
            ttl=8,
            created_at=0.0,
            protocol=protocol.name,
            request_id=9,
            path=(0, 1),
            app_payload=False,
        )
        second = Packet(
            kind="RREQ",
            flow_id=9,
            origin=0,
            final_dst=2,
            ttl=8,
            created_at=0.0,
            protocol=protocol.name,
            request_id=9,
            path=(0, 3),
            app_payload=False,
        )

        protocol.on_rreq(2, first)
        protocol.on_rreq(2, second)

        candidates = protocol.rreq_candidates[(0, 2, 9)]
        self.assertEqual(candidates, [(0, 1, 2), (0, 3, 2)])

    def test_meshcore_immediate_reply_suppresses_duplicate_destination_rreq(self) -> None:
        """The legacy immediate-reply mode must answer only the first RREQ."""

        class FakeMetrics:
            duplicate_rx = 0

        class FakeSimulator:
            max_hops = 8
            now = 0.0
            metrics = FakeMetrics()
            nodes = {
                node_id: SimpleNamespace(can_relay=True)
                for node_id in range(4)
            }

            def __init__(self) -> None:
                self.sent = []

            def transmit_later(self, sender, packet, delay_s):
                self.sent.append((sender, packet, delay_s))
                return None

        simulator = FakeSimulator()
        protocol = MeshCoreLike(discovery_window_s=0.0)
        protocol.bind(simulator)
        first = Packet(
            kind="RREQ",
            flow_id=9,
            origin=0,
            final_dst=2,
            ttl=8,
            created_at=0.0,
            protocol=protocol.name,
            request_id=9,
            path=(0, 1),
            app_payload=False,
        )
        duplicate = Packet(
            kind="RREQ",
            flow_id=9,
            origin=0,
            final_dst=2,
            ttl=8,
            created_at=0.0,
            protocol=protocol.name,
            request_id=9,
            path=(0, 3),
            app_payload=False,
        )

        protocol.on_rreq(2, first)
        protocol.on_rreq(2, duplicate)

        self.assertEqual(len(simulator.sent), 1)
        self.assertEqual(simulator.sent[0][1].kind, "RREP")

    def test_meshecho_recovery_uses_configured_fallback_ttl(self) -> None:
        protocol = MeshEcho(fallback_ttl=2)
        class FakeSimulator:
            max_hops = 7
            nodes = {0: SimpleNamespace()}
        protocol.bind(FakeSimulator())
        self.assertEqual(protocol.route_miss_recovery_ttl(flow_id=1), 2)

    def test_icc_probe_reports_do_not_use_smart_calm_as_a_method(self) -> None:
        root = Path(__file__).resolve().parents[1]
        version = (root / "VERSION").read_text(encoding="utf-8").strip().replace(
            ".", "_"
        )
        prefix = f"meshecho_v{version}_icc2027"
        report_paths = (
            root / f"docs/results/{prefix}_calibrated_multihop.md",
            root / f"docs/results/{prefix}_sensitivity_sf8.md",
            root / f"docs/results/{prefix}_sensitivity_load4.md",
            root / f"docs/results/{prefix}_component_ablation.md",
            root / f"docs/results/{prefix}_cache_ttl600.md",
            root / f"docs/results/{prefix}_cache_ttl30.md",
            root / f"docs/results/{prefix}_route_conflict.md",
        )
        for path in report_paths:
            text = path.read_text(encoding="utf-8").lower()
            self.assertNotIn("smart-calm", text, path.name)

    def test_route_conflict_harness_uses_meshecho_core(self) -> None:
        """The surgical candidate-selection audit must exercise MeshEcho."""

        from tools.run_route_conflict_experiment import RecordingConflictMesh

        protocol = RecordingConflictMesh(
            protocol_name="meshecho-confidence",
            confidence_enabled=True,
        )
        self.assertIsInstance(protocol, MeshEcho)
        self.assertNotEqual(type(protocol).__name__, "SmartCalmMesh")

    def test_route_conflict_report_uses_twenty_seed_paired_ci(self) -> None:
        """The versioned 20-seed audit must use the 20-df t critical value."""

        root = Path(__file__).resolve().parents[1]
        report = (
            root
            / "docs/results/meshecho_v2_1_20_icc2027_route_conflict.md"
        ).read_text(encoding="utf-8")
        self.assertIn("| ACK PDR | 0.221 | +/- 0.096 |", report)


if __name__ == "__main__":
    unittest.main()
