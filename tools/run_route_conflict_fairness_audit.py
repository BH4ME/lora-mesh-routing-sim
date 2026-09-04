#!/usr/bin/env python3
"""Run null, favorable, and reverse route-conflict controls.

This audit is deliberately separate from the main controlled experiment. It
checks that confidence does not create a gain when both routes are equivalent,
and that it does not force the longer route when the long branch is weaker.
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.run_route_conflict_experiment import (
    LONG_WEAK_EDGE,
    SHORT_WEAK_EDGE,
    run_case,
)


CASES = (
    ("null", None, 0.0, "No extra shadowing"),
    ("short-weak-5db", SHORT_WEAK_EDGE, 5.0, "Short branch weak, moderate gap"),
    ("short-weak-7.5db", SHORT_WEAK_EDGE, 7.5, "Short branch weak, large gap"),
    ("long-weak-7.5db", LONG_WEAK_EDGE, 7.5, "Long branch weak, reverse control"),
)


def mean_ci(values: Sequence[float]) -> Tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if len(values) == 1:
        return values[0], 0.0
    critical = 2.010 if len(values) == 50 else 1.984
    return (
        statistics.fmean(values),
        critical * statistics.stdev(values) / math.sqrt(len(values)),
    )


def write_csv(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_report(path: Path, rows: Sequence[Dict[str, object]], seeds: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# MeshEcho Route-Conflict Fairness Audit",
        "",
        "This audit checks whether the confidence ablation produces a gain "
        "only when the route-quality condition supports it. It is a fairness "
        "and sensitivity check, not a general network-performance benchmark.",
        "",
        f"- Seeds per condition: `{seeds}`",
        "- Flows per seed: `24`",
        "- Flow interval: `30.0 s`",
        "- One route-discovery attempt is tracked separately from cache misses.",
        "",
        "| Condition | Confidence ACK PDR | No-confidence ACK PDR | Paired delta | Confidence selected long | No-confidence selected short | Paired airtime delta (s) |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for case_name, _, shadowing_db, description in CASES:
        case_rows = [row for row in rows if row["case"] == case_name]
        confidence = [
            row for row in case_rows if row["protocol"] == "meshecho-confidence"
        ]
        no_confidence = [
            row for row in case_rows if row["protocol"] == "meshecho-no-confidence"
        ]
        by_seed = {}
        for row in case_rows:
            by_seed.setdefault(int(row["seed"]), {})[row["protocol"]] = row
        paired = [
            pair
            for pair in by_seed.values()
            if len(pair) == 2
        ]
        pdr_c, pdr_c_ci = mean_ci([float(row["unicast_pdr"]) for row in confidence])
        pdr_n, pdr_n_ci = mean_ci([float(row["unicast_pdr"]) for row in no_confidence])
        pdr_delta, _ = mean_ci(
            [
                float(pair["meshecho-confidence"]["unicast_pdr"])
                - float(pair["meshecho-no-confidence"]["unicast_pdr"])
                for pair in paired
            ]
        )
        airtime_delta, _ = mean_ci(
            [
                float(pair["meshecho-confidence"]["total_airtime_s"])
                - float(pair["meshecho-no-confidence"]["total_airtime_s"])
                for pair in paired
            ]
        )
        selected_long = sum(
            row["selected_route_class"] == "long" for row in confidence
        ) / len(confidence)
        selected_short = sum(
            row["selected_route_class"] == "short" for row in no_confidence
        ) / len(no_confidence)
        lines.append(
            f"| {description} (`{shadowing_db:.1f} dB`) | "
            f"{pdr_c:.3f} +/- {pdr_c_ci:.3f} | "
            f"{pdr_n:.3f} +/- {pdr_n_ci:.3f} | "
            f"{pdr_delta:.3f} | {selected_long:.3f} | "
            f"{selected_short:.3f} | {airtime_delta:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The null condition should have approximately zero paired delta.",
            "- The short-weak condition is the mechanism case in which confidence "
            "is expected to prefer the longer but more reliable route.",
            "- The long-weak reverse condition checks that confidence does not "
            "blindly prefer the longer route.",
            "- These controls do not remove the need for random topologies, "
            "time-varying links, concurrent traffic, and stronger baselines in "
            "the ICC evaluation.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=50)
    parser.add_argument("--seed0", type=int, default=1)
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("results/meshecho_route_conflict_fairness.csv"),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=Path("docs/results/meshecho_route_conflict_fairness.md"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows: List[Dict[str, object]] = []
    for case_name, weak_edge, shadowing_db, _ in CASES:
        for offset in range(args.seeds):
            seed = args.seed0 + offset
            for confidence_enabled in (True, False):
                row = run_case(
                    seed=seed,
                    confidence_enabled=confidence_enabled,
                    flow_count=24,
                    flow_interval_s=30.0,
                    weak_link_shadowing_db=shadowing_db,
                    weak_edge=weak_edge,
                )
                row["case"] = case_name
                rows.append(row)
    write_csv(args.csv, rows)
    write_report(args.report, rows, args.seeds)
    print(f"Wrote {args.csv}")
    print(f"Wrote {args.report}")


if __name__ == "__main__":
    main()
