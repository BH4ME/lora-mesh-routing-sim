#!/usr/bin/env python3
"""Run MeshEcho cache-reuse and route-aging diagnostics for ICC evidence."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analyze_results import aggregate
from lora_mesh_sim import ICC_PROTOCOLS
from tools.run_fair_multihop_probe import (
    run_one_probe,
    validate_non_degenerate_regime,
    write_csv,
    write_report,
)


@dataclass(frozen=True)
class CacheCase:
    key: str
    label: str
    route_ttl_s: float


CACHE_CASES = (
    CacheCase("ttl600", "long route-cache lifetime", 600.0),
    CacheCase("ttl30", "short route-cache lifetime", 30.0),
)


def build_cache_probe_namespace(
    case: CacheCase,
    *,
    seeds: int,
    seed0: int,
) -> argparse.Namespace:
    """Build a repeated-pair unicast workload with an explicit cache TTL."""

    return argparse.Namespace(
        scenario=f"icc2027_cache_{case.key}",
        nodes=50,
        area_m=8250.0,
        duration_s=600.0,
        rate_per_min=4.0,
        traffic="unicast",
        pair_mode="connected-multihop",
        pair_count=4,
        edge_prr_threshold=0.90,
        min_graph_hops=2,
        max_graph_hops=4,
        meshcore_discovery_window_s=2.0,
        min_direct_prr_below_0_99=0.10,
        min_selected_pair_mean_graph_hops=2.0,
        sf=7,
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
        route_ttl_s=case.route_ttl_s,
        smart_max_timeout_retries=0,
        seeds=seeds,
        seed0=seed0,
        report_cache_reuse=True,
    )


def run_case(
    case: CacheCase,
    *,
    seeds: int,
    seed0: int,
    protocols: Sequence[str],
    out_prefix: str,
) -> tuple[Path, Path, Path]:
    args = build_cache_probe_namespace(case, seeds=seeds, seed0=seed0)
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
        default="meshecho_v2_1_24_icc2027_cache",
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
    for case in CACHE_CASES:
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
