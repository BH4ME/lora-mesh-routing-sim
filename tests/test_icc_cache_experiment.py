import unittest

from tools.run_icc_cache_experiment import (
    CACHE_CASES,
    build_cache_probe_namespace,
)


class IccCacheExperimentTest(unittest.TestCase):
    def test_cache_cases_are_unicast_reuse_workloads_with_explicit_ttl(self) -> None:
        self.assertEqual({case.key for case in CACHE_CASES}, {"ttl600", "ttl30"})
        for case in CACHE_CASES:
            args = build_cache_probe_namespace(case, seeds=1, seed0=1)
            self.assertEqual(args.traffic, "unicast")
            self.assertEqual(args.pair_mode, "connected-multihop")
            self.assertEqual(args.pair_count, 4)
            self.assertEqual(args.rate_per_min, 4.0)
            self.assertEqual(args.route_ttl_s, case.route_ttl_s)
            self.assertEqual(args.smart_max_timeout_retries, 0)


if __name__ == "__main__":
    unittest.main()
