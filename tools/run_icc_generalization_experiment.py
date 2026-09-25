#!/usr/bin/env python3
"""Run MeshEcho generalization and stale-route evidence cases.

The ICC primary matrix is intentionally conditioned on a PRR-qualified pair
pool.  This runner adds three separate evidence strata:

* unconditioned random source-destination pairs;
* a larger, deeper-hop connected-multihop topology;
* repeated pairs under paired temporal block fading, with long and short
  route-cache lifetimes to expose stale-route behavior.

The cases are reported separately and are never pooled with the primary
first-discovery estimand.
"""

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
class GeneralizationCase:
    key: str
    label: str
    nodes: int
    area_m: float
    duration_s: float
    rate_per_min: float
    traffic: str
    pair_mode: str
    pair_count: int
    edge_prr_threshold: float
    min_graph_hops: int
    max_graph_hops: int
    sf: int
    route_ttl_s: float
    discovery_window_s: float = 2.0
    temporal_fading_sigma_db: float = 0.0
    temporal_fading_interval_s: float = 60.0
    report_cache_reuse: bool = False


GENERALIZATION_CASES = (
    GeneralizationCase(
        key="random_pairs",
        label="unconditioned random source-destination pairs",
        nodes=50,
        area_m=18_000.0,
        duration_s=600.0,
        rate_per_min=4.0,
        traffic="mixed",
        pair_mode="random",
        pair_count=0,
        edge_prr_threshold=0.70,
        min_graph_hops=2,
        max_graph_hops=4,
        sf=7,
        route_ttl_s=600.0,
        discovery_window_s=2.0,
    ),
    GeneralizationCase(
        key="deep_multihop",
        label="larger topology with three-to-five-hop pair selection",
        nodes=100,
        # The 20 km calibration leaves two of the 20 fixed seeds with fewer
        # than 24 eligible 3--5-hop pairs.  At 21 km every seed still has a
        # non-degenerate direct-link regime and a complete 24-pair pool.
        area_m=21_000.0,
        duration_s=600.0,
        rate_per_min=2.0,
        traffic="unicast",
        pair_mode="connected-multihop",
        pair_count=24,
        edge_prr_threshold=0.85,
        min_graph_hops=3,
        max_graph_hops=5,
        sf=7,
        route_ttl_s=600.0,
        discovery_window_s=4.0,
    ),
    GeneralizationCase(
        key="stale_fading",
        label="repeated pairs with temporal fading and long cache lifetime",
        nodes=50,
        area_m=8_250.0,
        duration_s=600.0,
        rate_per_min=4.0,
        traffic="unicast",
        pair_mode="connected-multihop",
        pair_count=4,
        edge_prr_threshold=0.90,
        min_graph_hops=2,
        max_graph_hops=4,
        sf=7,
        route_ttl_s=600.0,
        temporal_fading_sigma_db=6.0,
        temporal_fading_interval_s=60.0,
        report_cache_reuse=True,
    ),
    GeneralizationCase(
        key="stale_fading_short_ttl",
        label="repeated pairs with temporal fading and short cache lifetime",
        nodes=50,
        area_m=8_250.0,
        duration_s=600.0,
        rate_per_min=4.0,
        traffic="unicast",
        pair_mode="connected-multihop",
        pair_count=4,
        edge_prr_threshold=0.90,
        min_graph_hops=2,
        max_graph_hops=4,
        sf=7,
        route_ttl_s=30.0,
        temporal_fading_sigma_db=6.0,
        temporal_fading_interval_s=60.0,
        report_cache_reuse=True,
    ),
)


def build_generalization_namespace(
    case: GeneralizationCase,
    *,
    seeds: int,
    seed0: int,
    scenario: str | None = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        scenario=scenario or f"icc2027_generalization_{case.key}",
        nodes=case.nodes,
        area_m=case.area_m,
        duration_s=case.duration_s,
        rate_per_min=case.rate_per_min,
        traffic=case.traffic,
        pair_mode=case.pair_mode,
        pair_count=case.pair_count,
        edge_prr_threshold=case.edge_prr_threshold,
        min_graph_hops=case.min_graph_hops,
        max_graph_hops=case.max_graph_hops,
        meshcore_discovery_window_s=case.discovery_window_s,
        calm_discovery_window_s=case.discovery_window_s,
        min_direct_prr_below_0_99=0.10,
        min_selected_pair_mean_graph_hops=float(case.min_graph_hops),
        sf=case.sf,
        bw_hz=125_000,
        cr=1,
        payload_bytes=32,
        tx_power_dbm=17.0,
        path_loss_exp=2.75,
        shadow_sigma_db=4.0,
        temporal_fading_sigma_db=case.temporal_fading_sigma_db,
        temporal_fading_interval_s=case.temporal_fading_interval_s,
        capture_threshold_db=6.0,
        max_hops=8,
        route_ttl_s=case.route_ttl_s,
        smart_max_timeout_retries=0,
        seeds=seeds,
        seed0=seed0,
        report_cache_reuse=case.report_cache_reuse,
    )


def run_case(
    case: GeneralizationCase,
    *,
    seeds: int,
    seed0: int,
    protocols: Sequence[str],
    out_prefix: str,
) -> tuple[Path, Path, Path]:
    args = build_generalization_namespace(case, seeds=seeds, seed0=seed0)
    rows = [
        run_one_probe(args, protocol_name, seed0 + offset)
        for offset in range(seeds)
        for protocol_name in protocols
    ]
    if case.pair_mode == "connected-multihop":
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
        default="meshecho_v2_1_23_icc2027_generalization",
    )
    parser.add_argument(
        "--case",
        action="append",
        choices=[case.key for case in GENERALIZATION_CASES],
        help="repeat to select cases; defaults to all generalization cases",
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
    cases = tuple(
        case
        for case in GENERALIZATION_CASES
        if not args.case or case.key in args.case
    )
    protocols = tuple(args.protocol or ICC_PROTOCOLS)
    for case in cases:
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
