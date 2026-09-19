import unittest

from tools.run_icc_generalization_experiment import (
    GENERALIZATION_CASES,
    build_generalization_namespace,
)


class IccGeneralizationExperimentTest(unittest.TestCase):
    def test_cases_include_unconditioned_random_and_deeper_multihop(self) -> None:
        keys = {case.key for case in GENERALIZATION_CASES}
        self.assertIn("random_pairs", keys)
        self.assertIn("deep_multihop", keys)
        self.assertIn("stale_fading", keys)

        random_args = build_generalization_namespace(
            next(case for case in GENERALIZATION_CASES if case.key == "random_pairs"),
            seeds=1,
            seed0=1,
        )
        self.assertEqual(random_args.pair_mode, "random")
        self.assertEqual(random_args.pair_count, 0)

        deep_args = build_generalization_namespace(
            next(case for case in GENERALIZATION_CASES if case.key == "deep_multihop"),
            seeds=1,
            seed0=1,
        )
        self.assertEqual(deep_args.pair_mode, "connected-multihop")
        self.assertGreaterEqual(deep_args.min_graph_hops, 3)
        self.assertGreaterEqual(deep_args.nodes, 100)

    def test_stale_fading_cases_have_paired_temporal_channel_and_ttl_control(self) -> None:
        long_case = next(
            case for case in GENERALIZATION_CASES if case.key == "stale_fading"
        )
        short_case = next(
            case
            for case in GENERALIZATION_CASES
            if case.key == "stale_fading_short_ttl"
        )
        long_args = build_generalization_namespace(long_case, seeds=1, seed0=1)
        short_args = build_generalization_namespace(short_case, seeds=1, seed0=1)
        self.assertGreater(long_args.temporal_fading_sigma_db, 0.0)
        self.assertGreater(long_args.temporal_fading_interval_s, 0.0)
        self.assertGreater(long_args.route_ttl_s, short_args.route_ttl_s)


if __name__ == "__main__":
    unittest.main()
