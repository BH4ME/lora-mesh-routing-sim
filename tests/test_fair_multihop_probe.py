import unittest
from argparse import Namespace

from tools.run_fair_multihop_probe import run_one_probe


class FairMultihopProbeTest(unittest.TestCase):
    def test_probe_reports_route_discovery_health(self) -> None:
        args = Namespace(
            scenario="test",
            nodes=8,
            area_m=12000.0,
            duration_s=10.0,
            rate_per_min=1.0,
            traffic="unicast",
            pair_mode="random",
            pair_count=0,
            edge_prr_threshold=0.9,
            min_graph_hops=2,
            max_graph_hops=4,
            sf=7,
            bw_hz=125_000,
            cr=1,
            payload_bytes=32,
            tx_power_dbm=17.0,
            path_loss_exp=2.75,
            shadow_sigma_db=4.0,
            capture_threshold_db=6.0,
            max_hops=7,
            smart_max_timeout_retries=0,
            repeater_ratio=0.0,
            independent_rng_streams=True,
            seeds=1,
            seed0=1,
        )

        row = run_one_probe(args, "meshcore", seed=1)

        self.assertIn("route_discovery_success_rate", row)
        self.assertIn("rrep_rreq_tx_ratio", row)
        self.assertGreaterEqual(float(row["route_discovery_success_rate"]), 0.0)
        self.assertLessEqual(float(row["route_discovery_success_rate"]), 1.0)
        self.assertGreaterEqual(float(row["rrep_rreq_tx_ratio"]), 0.0)
        self.assertEqual(row["smart_max_timeout_retries"], 0)


if __name__ == "__main__":
    unittest.main()
