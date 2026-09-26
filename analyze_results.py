#!/usr/bin/env python3
"""Aggregate simulator CSV output by protocol for paper-ready summaries."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from math import sqrt
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, Iterable, List, Tuple


METRICS = [
    "unicast_pdr",
    "destination_unicast_pdr",
    "broadcast_coverage",
    "avg_delay_s",
    "mean_delivery_delay_s",
    "unicast_delivery_delay_s",
    "unicast_ack_delay_s",
    "p95_unicast_delivery_delay_s",
    "p95_unicast_ack_delay_s",
    "tx_count",
    "data_tx",
    "control_tx",
    "ack_tx",
    "total_airtime_s",
    "channel_busy_time_s",
    "channel_busy_ratio",
    "tx_energy_j",
    "rx_energy_j",
    "total_energy_j",
    "energy_per_delivery_j",
    "airtime_per_delivery_s",
    "rx_attempts",
    "packet_reception_ratio",
    "collision_fail",
    "collision_rate",
    "duplicate_rx",
    "suppressed_forwards",
    "route_cache_hits",
    "route_cache_misses",
    "fallback_forward_count",
    "route_repair_count",
    "mean_path_confidence",
    "control_overhead_ratio",
    "policy_switch_count",
    "policy_update_count",
    "policy_reward_total",
    "active_profile_index",
]

# Student-t critical values for a two-sided 95% interval. The normal
# approximation is used after 30 degrees of freedom.
T_CRITICAL_95 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    11: 2.201,
    12: 2.179,
    13: 2.160,
    14: 2.145,
    15: 2.131,
    16: 2.120,
    17: 2.110,
    18: 2.101,
    19: 2.093,
    20: 2.086,
    21: 2.080,
    22: 2.074,
    23: 2.069,
    24: 2.064,
    25: 2.060,
    26: 2.056,
    27: 2.052,
    28: 2.048,
    29: 2.045,
    30: 2.042,
}


def confidence_interval_95(values: List[float]) -> Tuple[float, float]:
    """Return the mean and half-width of a two-sided 95% t interval."""

    if not values:
        return 0.0, 0.0
    mu = mean(values)
    if len(values) < 2:
        return mu, 0.0
    critical = T_CRITICAL_95.get(len(values) - 1, 1.96)
    return mu, critical * stdev(values) / sqrt(len(values))


def numeric_values(rows: Iterable[dict], metric: str) -> List[float]:
    values = []
    for row in rows:
        raw = row.get(metric)
        if raw in {None, ""}:
            continue
        try:
            values.append(float(raw))
        except (TypeError, ValueError):
            continue
    return values


def aggregate(grouped: Dict[str, List[dict]]) -> List[dict]:
    """Create one machine-readable mean/SD/95% CI row per protocol/metric."""

    summary_rows: List[dict] = []
    for protocol, rows in grouped.items():
        for metric in METRICS:
            values = numeric_values(rows, metric)
            if not values:
                continue
            mu, half_width = confidence_interval_95(values)
            summary_rows.append(
                {
                    "protocol": protocol,
                    "metric": metric,
                    "n": len(values),
                    "mean": round(mu, 9),
                    "sd": round(stdev(values), 9) if len(values) >= 2 else 0.0,
                    "ci95_low": round(mu - half_width, 9),
                    "ci95_high": round(mu + half_width, 9),
                }
            )
    return summary_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate LoRa mesh simulator CSV")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument(
        "--summary-csv",
        type=Path,
        help="optional machine-readable protocol/metric mean, SD, and 95%% CI output",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    grouped: Dict[str, List[dict]] = defaultdict(list)
    with args.csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            grouped[row["protocol"]].append(row)

    summary_rows = aggregate(grouped)
    if args.summary_csv:
        args.summary_csv.parent.mkdir(parents=True, exist_ok=True)
        with args.summary_csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
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

    for protocol, rows in grouped.items():
        print(f"\n{protocol}  n={len(rows)}")
        print("-" * (len(protocol) + 6 + len(str(len(rows)))))
        for metric in METRICS:
            values = numeric_values(rows, metric)
            if not values:
                continue
            mu, half_width = confidence_interval_95(values)
            sd = stdev(values) if len(values) >= 2 else 0.0
            print(
                f"{metric:32s} mean={mu:.6f}  sd={sd:.6f}"
                f"  ci95=[{mu - half_width:.6f}, {mu + half_width:.6f}]"
            )


if __name__ == "__main__":
    main()
