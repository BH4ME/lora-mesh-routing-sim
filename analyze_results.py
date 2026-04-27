#!/usr/bin/env python3
"""Aggregate simulator CSV output by protocol."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, List


METRICS = [
    "unicast_pdr",
    "broadcast_coverage",
    "avg_delay_s",
    "tx_count",
    "data_tx",
    "control_tx",
    "total_airtime_s",
    "airtime_per_delivery_s",
    "collision_fail",
    "duplicate_rx",
    "suppressed_forwards",
    "route_cache_hits",
    "route_cache_misses",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Aggregate LoRa mesh simulator CSV")
    parser.add_argument("csv_path", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    grouped: Dict[str, List[dict]] = defaultdict(list)
    with args.csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            grouped[row["protocol"]].append(row)

    for protocol, rows in grouped.items():
        print(f"\n{protocol}  n={len(rows)}")
        print("-" * (len(protocol) + 6 + len(str(len(rows)))))
        for metric in METRICS:
            values = [float(row[metric]) for row in rows]
            mu = mean(values)
            if len(values) >= 2:
                sd = stdev(values)
                print(f"{metric:24s} mean={mu:.6f}  sd={sd:.6f}")
            else:
                print(f"{metric:24s} mean={mu:.6f}")


if __name__ == "__main__":
    main()
