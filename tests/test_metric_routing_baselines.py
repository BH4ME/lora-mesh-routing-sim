import argparse
import csv
import math
import statistics
import unittest
from pathlib import Path
from types import SimpleNamespace

from lora_mesh_sim import (
    CalmMesh,
    ICC_PROTOCOLS,
    MESHECHO_ABLATIONS,
    MeshCoreLike,
    MeshEcho,
    MinHopMesh,
    MetricMesh,
    Node,
    Packet,
    RadioConfig,
    RxInfo,
    Simulator,
    build_protocol,
    required_snr_db,
)
from tools.run_fair_multihop_probe import FAIR_PROBE_PROTOCOLS


# These audits belong to the published 2.1.23 release, not the current VERSION.
PUBLISHED_ICC_AUDIT_PREFIX = "meshecho_v2_1_23_icc2027"


class MetricRoutingBaselineTest(unittest.TestCase):
    def test_prr_product_uses_the_etx_model_prr_without_fallback(self) -> None:
        baseline = build_protocol("prr-product")
        sim = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 100.0, 0.0)],
            RadioConfig(sf=7),
            baseline,
            seed=3,
            max_hops=3,
            matched_rreq_timing=True,
        )
        threshold = required_snr_db(sim.radio.sf)
        rx = RxInfo(0, -100.0, threshold, threshold, False)

        self.assertEqual(baseline.name, "prr-product-mesh")
        self.assertFalse(baseline.route_miss_recovery_enabled)
        self.assertEqual(baseline.fallback_confidence_threshold, 0.0)
        self.assertAlmostEqual(baseline.extend_metric(1.0, rx), 0.5)
        self.assertAlmostEqual(baseline.extend_metric(0.5, rx), 0.25)

    def test_prr_product_can_match_meshecho_route_miss_fallback_budget(self) -> None:
        self.assertIn("prr-product-fallback", FAIR_PROBE_PROTOCOLS)
        baseline = build_protocol("prr-product-fallback")
        sim = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 4000.0, 0.0)],
            RadioConfig(tx_power_dbm=0.0, path_loss_exp=4.0, shadow_sigma_db=0.0),
            baseline,
            seed=3,
            max_hops=3,
            matched_rreq_timing=True,
        )
        sim.schedule(0.0, "app_send", (0, 1, 1))
        sim.run(5.0)

        self.assertEqual(baseline.name, "prr-product-fallback-mesh")
        self.assertEqual(baseline.metric_kind, "prr-product")
        self.assertTrue(baseline.route_miss_recovery_enabled)
        self.assertEqual(baseline.route_miss_recovery_ttl(), 2)
        self.assertGreater(sim.metrics.fallback_forward_count, 0)
        self.assertEqual(sim.metrics.data_tx, sim.metrics.fallback_forward_count)

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

    def test_meshecho_hop_penalty_is_charged_once_per_added_hop(self) -> None:
        protocol = MeshEcho(hop_penalty_per_hop=0.025)
        first = protocol.path_confidence((0, 1), 0.8)
        second = protocol.path_confidence((0, 1, 2), first)
        third = protocol.path_confidence((0, 1, 2, 3), second)

        self.assertAlmostEqual(first, 0.8)
        self.assertAlmostEqual(second, 0.775)
        self.assertAlmostEqual(third, 0.75)

        legacy = CalmMesh(hop_penalty_per_hop=0.025)
        legacy_second = legacy.path_confidence((0, 1, 2), 0.8)
        self.assertAlmostEqual(
            legacy.path_confidence((0, 1, 2, 3), legacy_second), 0.725
        )

    def test_icc_probe_reports_do_not_use_smart_calm_as_a_method(self) -> None:
        root = Path(__file__).resolve().parents[1]
        report_paths = tuple(
            root / f"docs/results/{PUBLISHED_ICC_AUDIT_PREFIX}_{suffix}.md"
            for suffix in (
                "matched_fixed_once",
                "native_fixed_once",
                "isolated_first_discovery",
                "candidate_set_audit",
                "generalization_random_pairs",
                "generalization_deep_multihop",
                "generalization_stale_fading",
                "generalization_stale_fading_short_ttl",
                "route_conflict",
            )
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
        """The versioned audit must report the paired seed-level interval."""

        root = Path(__file__).resolve().parents[1]
        with (root / f"results/{PUBLISHED_ICC_AUDIT_PREFIX}_route_conflict.csv").open(
            newline="", encoding="utf-8"
        ) as handle:
            rows = list(csv.DictReader(handle))
        by_seed = {}
        for row in rows:
            by_seed.setdefault(int(row["seed"]), {})[row["protocol"]] = row
        self.assertEqual(len(by_seed), 20)
        deltas = [
            float(variants["meshecho-confidence"]["unicast_pdr"])
            - float(variants["meshecho-no-confidence"]["unicast_pdr"])
            for variants in by_seed.values()
        ]
        half_width = 2.093 * statistics.stdev(deltas) / math.sqrt(len(deltas))
        report = (
            root
            / f"docs/results/{PUBLISHED_ICC_AUDIT_PREFIX}_route_conflict.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            f"| ACK PDR | {statistics.fmean(deltas):.3f} | +/- {half_width:.3f} |",
            report,
        )


if __name__ == "__main__":
    unittest.main()
