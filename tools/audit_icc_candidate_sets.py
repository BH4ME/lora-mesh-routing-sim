#!/usr/bin/env python3
"""Audit matched MeshEcho route discoveries from a recorded ICC CSV."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_fair_multihop_probe import paired_mean_ci  # noqa: E402


COMPARATORS = (
    ("ETX", "etx-mesh"),
    ("No fallback", "meshecho-no-fallback"),
    ("Budgeted", "meshecho-budgeted"),
)


def load_matrix(path: Path) -> Dict[int, Dict[str, Dict[str, Any]]]:
    by_seed: Dict[int, Dict[str, Dict[str, Any]]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            seed = int(row["seed"])
            protocol = row["protocol"]
            protocols = by_seed.setdefault(seed, {})
            if protocol in protocols:
                raise ValueError(f"duplicate protocol {protocol} for seed {seed}")
            records = {}
            for record in json.loads(row["discovery_records_json"]):
                key = tuple(record["key"])
                if key in records:
                    raise ValueError(f"duplicate discovery key {key} for {protocol}, seed {seed}")
                records[key] = {
                    "candidate_paths": frozenset(
                        tuple(path) for path in record["candidate_paths"]
                    ),
                    "selected_path": (
                        tuple(record["selected_path"])
                        if record["selected_path"] is not None
                        else None
                    ),
                }
            protocols[protocol] = {"row": row, "records": records}
    if len(by_seed) < 2:
        raise ValueError("paired 95% CIs require at least two seeds")
    required = {"meshecho", *(protocol for _, protocol in COMPARATORS)}
    for seed, protocols in by_seed.items():
        missing = required - protocols.keys()
        if missing:
            raise ValueError(f"seed {seed} missing protocols: {sorted(missing)}")
    return by_seed


def candidate_counts(
    matrix: Dict[int, Dict[str, Dict[str, Any]]],
    comparator: str,
) -> Tuple[int, int, int, int, int, int]:
    same = paired = different_selection = same_multi_different = same_multi = 0
    for seed, protocols in matrix.items():
        echo_records = protocols["meshecho"]["records"]
        other_records = protocols[comparator]["records"]
        if echo_records.keys() != other_records.keys():
            raise ValueError(f"seed {seed}: discovery keys differ for {comparator}")
        for key, echo in echo_records.items():
            other = other_records[key]
            paired += 1
            equal_candidates = echo["candidate_paths"] == other["candidate_paths"]
            same += equal_candidates
            different_selection += echo["selected_path"] != other["selected_path"]
            if equal_candidates and len(echo["candidate_paths"]) >= 2:
                same_multi += 1
                same_multi_different += (
                    echo["selected_path"] != other["selected_path"]
                )
    return same, paired, different_selection, paired, same_multi_different, same_multi


def render_report(path: Path) -> str:
    matrix = load_matrix(path)
    try:
        source_path = path.resolve().relative_to(ROOT)
    except ValueError:
        source_path = path
    lines = [
        "# MeshEcho Candidate-Set Audit",
        "",
        f"Source CSV: `{source_path}`",
        f"Source SHA-256: `{hashlib.sha256(path.read_bytes()).hexdigest()}`",
        f"Seeds: `{len(matrix)}`",
        "",
        "Candidate paths are compared as sets after pairing by seed and discovery key. "
        "The final column counts different route selections only when both "
        "policies observed the same set of at least two candidate paths.",
        "",
        "| Comparator | Same candidate sets / paired keys | "
        "Different selected paths / paired keys | "
        "Different selections on same multi-candidate set / eligible keys |",
        "| --- | ---: | ---: | ---: |",
    ]
    for label, protocol in COMPARATORS:
        same, paired, changed, _, changed_same_multi, eligible = candidate_counts(
            matrix, protocol
        )
        lines.append(
            f"| {label} | {same}/{paired} | {changed}/{paired} | "
            f"{changed_same_multi}/{eligible} |"
        )
    lines.extend(
        [
            "",
            "## Paired MeshEcho vs Budgeted",
            "",
            "Differences are MeshEcho minus budgeted, paired by topology seed. "
            "PDR uses integer deliveries divided by observed unicast attempts. "
            "Intervals are two-sided 95% t CIs over seed-level differences.",
            "",
            "| Metric | Mean difference [95% CI] | Seeds |",
            "| --- | ---: | ---: |",
        ]
    )
    for label, metric in (
        ("ACK PDR", "unicast_acks"),
        ("Destination PDR", "unicast_deliveries"),
        ("Airtime (s)", "total_airtime_s"),
    ):
        deltas = []
        for protocols in matrix.values():
            echo = protocols["meshecho"]["row"]
            budgeted = protocols["meshecho-budgeted"]["row"]
            if metric == "total_airtime_s":
                delta = float(echo[metric]) - float(budgeted[metric])
            else:
                echo_attempts = int(echo["unicast_flows"])
                budgeted_attempts = int(budgeted["unicast_flows"])
                if echo_attempts <= 0 or echo_attempts != budgeted_attempts:
                    raise ValueError("paired protocols need equal positive unicast denominators")
                delta = (
                    int(echo[metric]) / echo_attempts
                    - int(budgeted[metric]) / budgeted_attempts
                )
            deltas.append(delta)
        mean, lower, upper = paired_mean_ci(deltas)
        lines.append(
            f"| {label} | {mean:+.3f} [{lower:+.3f},{upper:+.3f}] | "
            f"{len(deltas)} |"
        )
    return "\n".join(lines) + "\n"


def write_report(source: Path, target: Path) -> None:
    content = render_report(source)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8") as handle:
        handle.write(content)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--csv",
        type=Path,
        default=ROOT / "results/meshecho_v2_1_23_icc2027_matched_fixed_once.csv",
    )
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    write_report(args.csv, args.report)
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
