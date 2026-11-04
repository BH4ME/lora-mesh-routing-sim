#!/usr/bin/env python3
"""Render a publication-ready bar chart from the four-protocol run CSV."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


PROTOCOLS = ("meshecho-cpr", "meshecho", "meshtastic", "meshcore")
LABELS = ("MeshEcho-CPR", "Legacy MeshEcho", "Meshtastic-like", "MeshCore-like")
COLORS = ("#0077BB", "#EE7733", "#009988", "#CC3311")
T_CRITICAL_19 = 2.093024054408263


def read_runs(path: Path) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            grouped[row["protocol"]].append(row)
    missing = set(PROTOCOLS) - set(grouped)
    if missing:
        raise ValueError(f"missing protocols: {sorted(missing)}")
    seed_counts = {protocol: len(grouped[protocol]) for protocol in PROTOCOLS}
    if len(set(seed_counts.values())) != 1:
        raise ValueError(f"unpaired seed counts: {seed_counts}")
    return grouped


def mean_ci(rows: list[dict[str, str]], field: str) -> tuple[float, float]:
    values = [float(row[field]) for row in rows]
    mean = statistics.fmean(values)
    if len(values) < 2:
        return mean, 0.0
    half_width = T_CRITICAL_19 * statistics.stdev(values) / math.sqrt(len(values))
    return mean, half_width


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs_csv", type=Path)
    parser.add_argument("output_png", type=Path)
    args = parser.parse_args()
    grouped = read_runs(args.runs_csv)

    panels = (
        ("ack_pdr_deadline", "Deadline ACK PDR", (0.85, 1.01)),
        ("delivery_pdr_deadline", "Destination PDR", (0.85, 1.01)),
        ("tx_ledger_airtime_s", "Started-TX airtime (s)", (0.0, 32.0)),
    )
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.35), constrained_layout=True)
    x = range(len(PROTOCOLS))
    for ax, (field, title, limits) in zip(axes, panels):
        means = []
        errors = []
        for protocol in PROTOCOLS:
            mean, half_width = mean_ci(grouped[protocol], field)
            means.append(mean)
            errors.append(half_width)
        bars = ax.bar(
            list(x), means, yerr=errors, capsize=3.0, width=0.66,
            color=COLORS, edgecolor="#222222", linewidth=0.45,
            error_kw={"elinewidth": 0.7, "capthick": 0.7},
        )
        ax.set_title(title, fontsize=10, pad=7)
        ax.set_ylim(*limits)
        ax.set_xticks(list(x), LABELS, rotation=24, ha="right", fontsize=8)
        ax.tick_params(axis="y", labelsize=8)
        ax.grid(axis="y", color="#D9D9D9", linewidth=0.55)
        ax.set_axisbelow(True)
        for bar, value in zip(bars, means):
            format_value = f"{value:.3f}" if "pdr" in field else f"{value:.2f}"
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + (limits[1] - limits[0]) * 0.025,
                format_value,
                ha="center", va="bottom", fontsize=7,
            )
    fig.suptitle(
        "Four-protocol behavior-level simulation: 20 paired holdout seeds",
        fontsize=11, y=1.03,
    )
    fig.text(
        0.5, -0.025,
        "Error bars: paired-seed 95% t intervals; protocols are simulator models, not hardware measurements.",
        ha="center", fontsize=8,
    )
    args.output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.output_png, dpi=300, bbox_inches="tight")
    print(args.output_png)


if __name__ == "__main__":
    main()
