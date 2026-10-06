import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from lora_mesh_sim import Node, RadioConfig, RxInfo, Simulator, build_protocol
from tools.run_fair_multihop_probe import (
    FAIR_PROBE_PROTOCOLS,
    run_one_probe,
    write_report,
)
from tools.run_icc_generalization_experiment import (
    GENERALIZATION_CASES,
    build_generalization_namespace,
)
from tools.run_isolated_first_discovery import PROTOCOLS, make_protocol


class MeshEchoCalibratedTest(unittest.TestCase):
    def test_rreq_score_uses_uncapped_model_prr_and_no_hop_penalty(self) -> None:
        protocol = build_protocol("meshecho-calibrated")
        sim = Simulator(
            [Node(0, 0.0, 0.0), Node(1, 10.0, 0.0)],
            RadioConfig(shadow_sigma_db=0.0),
            protocol,
            seed=3,
            max_hops=3,
        )
        rx = RxInfo(0, -100.0, 20.0, 10.0, True)
        expected = sim.prr_from_snr(rx.sinr_db)

        self.assertEqual(protocol.name, "meshecho-calibrated")
        self.assertTrue(protocol.route_miss_recovery_enabled)
        self.assertEqual(protocol.hop_penalty_per_hop, 0.0)
        self.assertAlmostEqual(protocol.link_confidence(rx), expected)
        self.assertAlmostEqual(
            protocol.path_confidence((0, 1, 2), 0.997), 0.997
        )

    def test_generalization_runner_accepts_calibrated_variant(self) -> None:
        self.assertIn("meshecho-calibrated", FAIR_PROBE_PROTOCOLS)

    def test_isolated_runner_includes_calibrated_variant(self) -> None:
        self.assertIn("meshecho-calibrated", PROTOCOLS)
        protocol = make_protocol("meshecho-calibrated", 2.0)
        self.assertEqual(protocol.name, "meshecho-calibrated")
        self.assertFalse(protocol.route_miss_recovery_enabled)

    def test_report_pairs_calibrated_variant_with_original(self) -> None:
        case = next(case for case in GENERALIZATION_CASES if case.key == "feedback_fading")
        args = build_generalization_namespace(case, seeds=1, seed0=41)
        rows = [
            run_one_probe(args, name, 41)
            for name in ("meshecho", "meshecho-calibrated")
        ]
        with TemporaryDirectory() as directory:
            report = Path(directory) / "comparison.md"
            write_report(report, rows, args)
            content = report.read_text(encoding="utf-8")

        self.assertIn("MeshEcho vs meshecho-calibrated", content)
        self.assertIn("calibrated max-min PRR", content)


if __name__ == "__main__":
    unittest.main()
