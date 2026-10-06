import unittest

from tools.run_icc_sensitivity_experiments import (
    DEFAULT_SENSITIVITY_CASES,
    build_probe_namespace,
)


class IccSensitivityTest(unittest.TestCase):
    def test_cases_cover_spreading_factor_and_offered_load(self) -> None:
        keys = {case.key for case in DEFAULT_SENSITIVITY_CASES}
        self.assertEqual(keys, {"sf8", "load4"})

        sf_case = next(case for case in DEFAULT_SENSITIVITY_CASES if case.key == "sf8")
        load_case = next(case for case in DEFAULT_SENSITIVITY_CASES if case.key == "load4")
        self.assertEqual(sf_case.sf, 8)
        self.assertEqual(sf_case.rate_per_min, 1.0)
        self.assertEqual(sf_case.area_m, 10000.0)
        self.assertEqual(load_case.sf, 7)
        self.assertEqual(load_case.rate_per_min, 4.0)
        self.assertEqual(load_case.area_m, 8250.0)

    def test_case_namespace_preserves_primary_multihop_contract(self) -> None:
        case = next(case for case in DEFAULT_SENSITIVITY_CASES if case.key == "sf8")
        args = build_probe_namespace(case, seeds=20, seed0=1)

        self.assertEqual(args.pair_mode, "connected-multihop")
        self.assertEqual(args.pair_count, 24)
        self.assertEqual(args.area_m, 10000.0)
        self.assertEqual(args.edge_prr_threshold, 0.90)
        self.assertEqual(args.min_graph_hops, 2)
        self.assertEqual(args.max_graph_hops, 4)
        self.assertEqual(args.smart_max_timeout_retries, 0)
        self.assertEqual(args.seeds, 20)
        self.assertEqual(args.seed0, 1)
        self.assertEqual(args.sf, 8)


if __name__ == "__main__":
    unittest.main()
