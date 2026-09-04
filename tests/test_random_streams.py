import unittest

from lora_mesh_sim import MeshCoreLike, Node, RadioConfig, Simulator


class RandomStreamTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
