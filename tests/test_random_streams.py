import unittest
from argparse import Namespace
from unittest.mock import Mock, patch

from lora_mesh_sim import (
    MeshCoreLike,
    Node,
    RadioConfig,
    Simulator,
    independent_rng_streams_enabled,
    run_one,
)


class RandomStreamTest(unittest.TestCase):
    def test_cli_rng_flag_is_read(self) -> None:
        self.assertTrue(
            independent_rng_streams_enabled(
                Namespace(independent_rng_streams=True)
            )
        )
        self.assertTrue(
            independent_rng_streams_enabled(
                Namespace(independent_random_streams=True)
            )
        )
        self.assertFalse(independent_rng_streams_enabled(Namespace()))

    def make_simulator(self, independent: bool) -> Simulator:
        return Simulator(
            [
                Node(0, 0.0, 0.0),
                Node(1, 100.0, 0.0),
            ],
            RadioConfig(),
            MeshCoreLike(),
            seed=17,
            max_hops=3,
            independent_random_streams=independent,
        )

    def test_legacy_mode_preserves_shared_random_stream(self) -> None:
        simulator = self.make_simulator(independent=False)
        self.assertIs(simulator.random, simulator.channel_random)

    def test_split_mode_isolated_from_protocol_random_draws(self) -> None:
        with_protocol_draw = self.make_simulator(independent=True)
        without_protocol_draw = self.make_simulator(independent=True)

        with_protocol_draw.random.random()
        with_protocol_draw.random.randrange(3)

        self.assertEqual(
            with_protocol_draw.channel_random.random(),
            without_protocol_draw.channel_random.random(),
        )
        self.assertIsNot(with_protocol_draw.random, with_protocol_draw.channel_random)

    def test_run_one_passes_cli_rng_flag_to_simulator(self) -> None:
        args = Namespace(
            nodes=3,
            area_m=1000.0,
            repeater_ratio=0.0,
            sf=9,
            bw_hz=125_000,
            cr=1,
            payload_bytes=32,
            tx_power_dbm=17.0,
            tx_current_ma=120.0,
            rx_current_ma=10.3,
            supply_voltage_v=3.3,
            path_loss_exp=2.7,
            shadow_sigma_db=4.0,
            capture_threshold_db=6.0,
            max_hops=3,
            duration_s=10.0,
            rate_per_min=1.0,
            traffic="unicast",
            pair_count=1,
            independent_rng_streams=True,
        )
        fake_metrics = Mock()
        fake_metrics.summarize.return_value = {"protocol": "meshcore-like"}
        fake_simulator = Mock()
        fake_simulator.nodes = {0: None, 1: None, 2: None}
        fake_simulator.run.return_value = fake_metrics
        with patch("lora_mesh_sim.Simulator") as simulator_cls:
            simulator_cls.return_value = fake_simulator
            result = run_one(args, "meshcore", seed=3)

        self.assertEqual(result, {"protocol": "meshcore-like"})
        self.assertTrue(
            simulator_cls.call_args.kwargs["independent_random_streams"]
        )


if __name__ == "__main__":
    unittest.main()
