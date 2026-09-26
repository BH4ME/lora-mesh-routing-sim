import unittest

from tools.run_route_conflict_fairness_audit import CASES
from tools.run_route_conflict_experiment import (
    LONG_PATH,
    SHORT_PATH,
    LONG_WEAK_EDGE,
    run_case,
)


class RouteConflictExperimentTest(unittest.TestCase):
    def test_confidence_prefers_reliable_long_candidate(self) -> None:
        confidence = run_case(
            seed=2,
            confidence_enabled=True,
            flow_count=12,
            flow_interval_s=18.0,
        )
        no_confidence = run_case(
            seed=2,
            confidence_enabled=False,
            flow_count=12,
            flow_interval_s=18.0,
        )

        self.assertEqual(confidence["selected_path"], "-".join(map(str, LONG_PATH)))
        self.assertEqual(no_confidence["selected_path"], "-".join(map(str, SHORT_PATH)))
        self.assertEqual(confidence["candidate_count"], 2)
        self.assertEqual(confidence["short_candidate_seen"], 1)
        self.assertEqual(confidence["long_candidate_seen"], 1)
        self.assertEqual(confidence["route_discovery_attempts"], 1)
        self.assertEqual(no_confidence["route_discovery_attempts"], 1)
        self.assertGreater(
            confidence["long_candidate_confidence"],
            confidence["short_candidate_confidence"],
        )
        self.assertGreater(
            confidence["unicast_pdr"],
            no_confidence["unicast_pdr"],
        )

    def test_null_control_has_no_confidence_effect(self) -> None:
        confidence = run_case(
            seed=2,
            confidence_enabled=True,
            flow_count=12,
            flow_interval_s=18.0,
            weak_link_shadowing_db=0.0,
            weak_edge=None,
        )
        no_confidence = run_case(
            seed=2,
            confidence_enabled=False,
            flow_count=12,
            flow_interval_s=18.0,
            weak_link_shadowing_db=0.0,
            weak_edge=None,
        )
        self.assertEqual(confidence["unicast_pdr"], no_confidence["unicast_pdr"])
        self.assertEqual(confidence["total_airtime_s"], no_confidence["total_airtime_s"])
        self.assertEqual(confidence["selected_path"], "-".join(map(str, SHORT_PATH)))

    def test_reverse_condition_does_not_create_a_false_confidence_gain(self) -> None:
        confidence = run_case(
            seed=2,
            confidence_enabled=True,
            flow_count=12,
            flow_interval_s=18.0,
            weak_link_shadowing_db=7.5,
            weak_edge=LONG_WEAK_EDGE,
        )
        no_confidence = run_case(
            seed=2,
            confidence_enabled=False,
            flow_count=12,
            flow_interval_s=18.0,
            weak_link_shadowing_db=7.5,
            weak_edge=LONG_WEAK_EDGE,
        )
        self.assertEqual(confidence["selected_path"], "-".join(map(str, SHORT_PATH)))
        self.assertEqual(no_confidence["selected_path"], "-".join(map(str, SHORT_PATH)))
        self.assertEqual(confidence["unicast_pdr"], no_confidence["unicast_pdr"])

    def test_fairness_audit_has_null_and_reverse_controls(self) -> None:
        case_names = {case[0] for case in CASES}
        self.assertEqual(
            case_names,
            {"null", "short-weak-5db", "short-weak-7.5db", "long-weak-7.5db"},
        )


if __name__ == "__main__":
    unittest.main()
