import argparse
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from lora_mesh_sim import ICC_PROTOCOLS, MeshEcho, RxInfo, build_protocol, parse_args


class MeshEchoBudgetedTest(unittest.TestCase):
    def test_accepts_one_extra_hop_at_exact_confidence_threshold(self) -> None:
        policy = build_protocol("meshecho-budgeted")
        candidates = [
            ((0, 1, 4), 0.70),
            ((0, 2, 3, 4), 0.80),
        ]

        self.assertEqual(
            policy.select_route_candidate(candidates, flow_id=1),
            candidates[1],
        )

    def test_exact_decimal_threshold_is_not_lost_to_rounding(self) -> None:
        policy = build_protocol("meshecho-budgeted")
        candidates = [
            ((0, 1, 4), 0.75),
            ((0, 2, 3, 4), 0.85),
        ]

        self.assertEqual(
            policy.select_route_candidate(candidates, flow_id=1),
            candidates[1],
        )

    def test_cli_exposes_optional_protocol_outside_default_icc_matrix(self) -> None:
        with patch("sys.argv", ["lora_mesh_sim.py", "--protocol", "meshecho-budgeted"]):
            args = parse_args()

        self.assertEqual(args.protocol, "meshecho-budgeted")
        self.assertNotIn("meshecho-budgeted", ICC_PROTOCOLS)

    def test_keeps_shortest_route_when_gain_is_below_threshold(self) -> None:
        policy = build_protocol("meshecho-budgeted")
        candidates = [
            ((0, 1, 4), 0.70),
            ((0, 2, 3, 4), 0.799),
        ]

        self.assertEqual(
            policy.select_route_candidate(candidates, flow_id=1),
            candidates[0],
        )

    def test_ignores_candidates_more_than_one_hop_longer(self) -> None:
        policy = build_protocol("meshecho-budgeted")
        candidates = [
            ((0, 1, 5), 0.60),
            ((0, 2, 3, 5), 0.75),
            ((0, 2, 3, 4, 5), 0.98),
        ]

        self.assertEqual(
            policy.select_route_candidate(candidates, flow_id=1),
            candidates[1],
        )

    def test_equal_confidence_uses_hop_count_then_path_tuple(self) -> None:
        policy = build_protocol("meshecho-budgeted")
        shorter_tie = [
            ((0, 3, 4, 5), 0.85),
            ((0, 2, 5), 0.85),
            ((0, 1, 5), 0.60),
        ]
        path_tie = [
            ((0, 3, 4, 5), 0.85),
            ((0, 2, 4, 5), 0.85),
            ((0, 1, 5), 0.60),
        ]

        self.assertEqual(
            policy.select_route_candidate(shorter_tie, flow_id=1),
            shorter_tie[1],
        )
        self.assertEqual(
            policy.select_route_candidate(path_tie, flow_id=1),
            path_tie[1],
        )

    def test_original_meshecho_still_selects_highest_confidence(self) -> None:
        original = build_protocol("meshecho")
        budgeted = build_protocol("meshecho-budgeted")
        candidates = [
            ((0, 1, 5), 0.60),
            ((0, 2, 3, 4, 5), 0.61),
        ]

        self.assertIs(type(original), MeshEcho)
        self.assertEqual(original.select_route_candidate(candidates, flow_id=1), candidates[1])
        self.assertEqual(budgeted.select_route_candidate(candidates, flow_id=1), candidates[0])

    def test_inherits_meshecho_observation_and_recovery_configuration(self) -> None:
        args = argparse.Namespace(
            calm_route_ttl_s=45.0,
            calm_discovery_window_s=3.0,
            calm_fallback_ttl=3,
            calm_fallback_confidence_threshold=0.4,
            calm_route_age_penalty=0.2,
            calm_disable_route_miss_fallback=True,
        )
        original = build_protocol("meshecho", args)
        budgeted = build_protocol("meshecho-budgeted", args)
        observation = RxInfo(0, -110.0, -3.0, -3.0, False)
        sim = SimpleNamespace(nodes={}, radio=SimpleNamespace(sf=7))
        original.bind(sim)
        budgeted.bind(sim)

        for attr in (
            "route_ttl_s",
            "discovery_window_s",
            "fallback_ttl",
            "fallback_confidence_threshold",
            "route_age_penalty",
            "route_miss_recovery_enabled",
        ):
            self.assertEqual(getattr(budgeted, attr), getattr(original, attr))
        self.assertEqual(budgeted.link_confidence(observation), original.link_confidence(observation))
