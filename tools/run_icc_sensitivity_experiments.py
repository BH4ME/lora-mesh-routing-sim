#!/usr/bin/env python3
"""Run versioned SF and offered-load sensitivity cases for the ICC matrix."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lora_mesh_sim import ICC_PROTOCOLS
from analyze_results import aggregate
from tools.run_fair_multihop_probe import (
    validate_non_degenerate_regime,
    run_one_probe,
    write_csv,
    write_report,
)


@dataclass(frozen=True)
class SensitivityCase:
    key: str
    label: str
    sf: int
    rate_per_min: float
    area_m: float


DEFAULT_SENSITIVITY_CASES = (
    SensitivityCase(
        key="sf8",
        label="SF8 at the primary offered load",
        sf=8,
        rate_per_min=1.0,
        area_m=10000.0,
    ),
    SensitivityCase(
        key="load4",
        label="four flows per minute at the primary SF",
        sf=7,
        rate_per_min=4.0,
        area_m=8250.0,
    ),
)


def build_probe_namespace(
    case: SensitivityCase,
    *,
    seeds: int,
    seed0: int,
    scenario: Optional[str] = None,
) -> argparse.Namespace:
    """Build the same connected-multihop contract used by the ICC primary case."""

    return argparse.Namespace(
        scenario=scenario or f"icc2027_sensitivity_{case.key}",
        nodes=50,
        area_m=case.area_m,
        duration_s=600.0,
        rate_per_min=case.rate_per_min,
        traffic="mixed",
        pair_mode="connected-multihop",
        pair_count=24,
        edge_prr_threshold=0.90,
        min_graph_hops=2,
        max_graph_hops=4,
        meshcore_discovery_window_s=2.0,
        min_direct_prr_below_0_99=0.10,
        min_selected_pair_mean_graph_hops=2.0,
        sf=case.sf,
        bw_hz=125_000,
        cr=1,
        payload_bytes=32,
        tx_power_dbm=17.0,
        path_loss_exp=2.75,
        shadow_sigma_db=4.0,
        temporal_fading_sigma_db=0.0,
        temporal_fading_interval_s=60.0,
        capture_threshold_db=6.0,
        max_hops=7,
        smart_max_timeout_retries=0,
        seeds=seeds,
        seed0=seed0,
    )


def run_case(
    case: SensitivityCase,
    *,
    seeds: int,
    seed0: int,
    protocols: Sequence[str],
    out_prefix: str,
) -> tuple[Path, Path, Path]:
    args = build_probe_namespace(case, seeds=seeds, seed0=seed0)
    rows = [
        run_one_probe(args, protocol_name, seed0 + offset)
        for offset in range(seeds)
        for protocol_name in protocols
    ]
    validate_non_degenerate_regime(rows, args)

    csv_path = Path("results") / f"{out_prefix}_{case.key}.csv"
    report_path = Path("docs/results") / f"{out_prefix}_{case.key}.md"
    summary_path = Path("results") / f"{out_prefix}_{case.key}_summary.csv"
    write_csv(csv_path, rows)
    write_report(report_path, rows, args)
    grouped = defaultdict(list)
    for row in rows:
        grouped[str(row["protocol"])].append(row)
    summary_rows = aggregate(grouped)
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "protocol",
                "metric",
                "n",
                "mean",
                "sd",
                "ci95_low",
                "ci95_high",
            ],
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(summary_rows)
    return csv_path, report_path, summary_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--seed0", type=int, default=1)
    parser.add_argument(
        "--out-prefix",
        default="meshecho_v2_1_24_icc2027_sensitivity",
    )
    parser.add_argument(
        "--protocol",
        action="append",
        choices=ICC_PROTOCOLS,
        help="repeat to select protocols; defaults to all ICC configurations",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    protocols = tuple(args.protocol or ICC_PROTOCOLS)
    for case in DEFAULT_SENSITIVITY_CASES:
        csv_path, report_path, summary_path = run_case(
            case,
            seeds=args.seeds,
            seed0=args.seed0,
            protocols=protocols,
            out_prefix=args.out_prefix,
        )
        print(f"Wrote {csv_path}")
        print(f"Wrote {report_path}")
        print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
