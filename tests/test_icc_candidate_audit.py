import csv
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.audit_icc_candidate_sets import render_report, write_report


def record(key, candidates, selected):
    return {
        "key": key,
        "candidate_paths": candidates,
        "selected_path": selected,
    }


class IccCandidateAuditTest(unittest.TestCase):
    def write_matrix(self, path: Path) -> None:
        echo_seed1 = [
            record([0, 3, 1], [[0, 1, 3], [0, 2, 3]], [0, 1, 3]),
            record([1, 4, 2], [[1, 3, 4]], [1, 3, 4]),
        ]
        etx_seed1 = [
            record([1, 4, 2], [[1, 2, 4], [1, 3, 4]], [1, 2, 4]),
            record([0, 3, 1], [[0, 2, 3], [0, 1, 3]], [0, 2, 3]),
        ]
        echo_seed2 = [record([0, 3, 1], [[0, 2, 3]], [0, 2, 3])]
        rows = []
        for seed, echo_records, etx_records in (
            (1, echo_seed1, etx_seed1),
            (2, echo_seed2, echo_seed2),
        ):
            for protocol, records in (
                ("meshecho", echo_records),
                ("etx-mesh", etx_records),
                ("meshecho-no-fallback", echo_records),
                ("meshecho-budgeted", echo_records),
            ):
                rows.append(
                    {
                        "protocol": protocol,
                        "seed": seed,
                        "unicast_flows": 2,
                        "unicast_acks": 2 if protocol == "meshecho" and seed == 1 else 1,
                        "unicast_deliveries": 2 if protocol == "meshecho" and seed == 1 else 1,
                        "total_airtime_s": (
                            10 if protocol == "meshecho" and seed == 1 else 9
                        ),
                        "discovery_records_json": json.dumps(records),
                    }
                )
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def test_pairs_discoveries_by_seed_and_key_then_compares_candidate_sets(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "matrix.csv"
            self.write_matrix(source)
            report = render_report(source)

        self.assertIn("| ETX | 2/3 | 2/3 | 1/1 |", report)

    def test_reports_seed_paired_budgeted_metric_intervals(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "matrix.csv"
            self.write_matrix(source)
            report = render_report(source)

        self.assertIn("## Paired MeshEcho vs Budgeted", report)
        self.assertIn("| ACK PDR | +0.250 [-2.926,+3.426] | 2 |", report)
        self.assertIn("| Destination PDR | +0.250 [-2.926,+3.426] | 2 |", report)
        self.assertIn("| Airtime (s) | +0.500 [-5.853,+6.853] | 2 |", report)

    def test_existing_report_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "matrix.csv"
            target = Path(directory) / "audit.md"
            self.write_matrix(source)
            target.write_text("keep original\n", encoding="utf-8")

            with self.assertRaises(FileExistsError):
                write_report(source, target)

            self.assertEqual(target.read_text(encoding="utf-8"), "keep original\n")

    def test_cli_writes_report_to_requested_new_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "matrix.csv"
            target = Path(directory) / "audit.md"
            self.write_matrix(source)
            script = Path(__file__).resolve().parents[1] / "tools/audit_icc_candidate_sets.py"

            result = subprocess.run(
                [sys.executable, str(script), "--csv", str(source), "--report", str(target)],
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("# MeshEcho Candidate-Set Audit", target.read_text(encoding="utf-8"))

    def test_report_identifies_the_exact_source_csv(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "matrix.csv"
            self.write_matrix(source)
            expected_hash = hashlib.sha256(source.read_bytes()).hexdigest()

            report = render_report(source)

        self.assertIn(f"Source SHA-256: `{expected_hash}`", report)

    def test_repository_source_path_is_portable(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=root) as directory:
            source = Path(directory) / "matrix.csv"
            self.write_matrix(source)

            report = render_report(source)

            self.assertIn(f"Source CSV: `{source.relative_to(root)}`", report)
            self.assertNotIn(str(root), report)


if __name__ == "__main__":
    unittest.main()
