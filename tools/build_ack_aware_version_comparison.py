#!/usr/bin/env python3
"""Build Smart-CALM version comparison tables and SVG bar charts."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Optional, Sequence


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUTPUT_DIR = RESULTS / "ack_aware_comparison"
FIGURE_DIR = OUTPUT_DIR / "figures"

SMART_CALM = "smart-calm"


@dataclass(frozen=True)
class Scenario:
    key: str
    label: str
    suffix: str


@dataclass(frozen=True)
class RunSpec:
    key: str
    label: str
    folder: Path
    prefix: str
    ack_aware: bool

    def csv_path(self, scenario: Scenario) -> Path:
        return self.folder / f"{self.prefix}_{scenario.suffix}.csv"


SCENARIOS = (
    Scenario("mixed", "Mixed traffic", "50n_mixed"),
    Scenario("shadow6", "High shadowing", "50n_mixed_shadow6"),
    Scenario("rate10", "High offered load", "50n_mixed_rate10"),
)

RUNS = (
    RunSpec("v1_1_previous", "v1.1 previous", RESULTS, "smart_calm_v1_1", False),
    RunSpec("v1_1_ack", "v1.1 ACK-aware", OUTPUT_DIR, "smart_calm_v1_1_ack", True),
    RunSpec("v1_1_1_previous", "v1.1.1 previous", RESULTS, "smart_calm_v1_1_1", False),
    RunSpec("latest_ack", "Latest ACK-aware", OUTPUT_DIR, "smart_calm_v1_1_1_ack", True),
)

METRICS = {
    "unicast_pdr": {
        "label": "ACK-confirmed Unicast PDR",
        "unit": "",
        "precision": 3,
    },
    "destination_unicast_pdr": {
        "label": "Destination DATA Arrival Ratio",
        "unit": "",
        "precision": 3,
    },
    "total_airtime_s": {
        "label": "Total Airtime",
        "unit": "s",
        "precision": 0,
    },
    "collision_fail": {
        "label": "Collision Failures",
        "unit": "",
        "precision": 0,
    },
    "fallback_forward_count": {
        "label": "Fallback Forwards",
        "unit": "",
        "precision": 0,
    },
    "ack_tx": {
        "label": "ACK Transmissions",
        "unit": "",
        "precision": 0,
    },
}

COLORS = {
    "v1_1_previous": "#6d7885",
    "v1_1_ack": "#2f6f73",
    "v1_1_1_previous": "#c77d32",
    "latest_ack": "#1f4e8c",
}


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def metric_mean(rows: Iterable[Dict[str, str]], metric: str, path: Path) -> Optional[float]:
    smart_rows = [row for row in rows if row.get("protocol") == SMART_CALM]
    if not smart_rows:
        raise ValueError(f"Missing {SMART_CALM} rows in {path}")
    values = [
        float(row[metric])
        for row in smart_rows
        if row.get(metric) not in {None, ""}
    ]
    if not values:
        return None
    return mean(values)


def collect() -> Dict[str, Dict[str, Dict[str, Optional[float]]]]:
    data: Dict[str, Dict[str, Dict[str, Optional[float]]]] = {}
    for scenario in SCENARIOS:
        data[scenario.key] = {}
        for run in RUNS:
            path = run.csv_path(scenario)
            rows = read_rows(path)
            data[scenario.key][run.key] = {
                metric: metric_mean(rows, metric, path)
                for metric in METRICS
            }
    return data


def fmt(value: Optional[float], precision: int, unit: str = "") -> str:
    if value is None:
        return "n/a"
    if precision == 0:
        text = f"{value:.0f}"
    else:
        text = f"{value:.{precision}f}"
    return f"{text} {unit}".rstrip()


def delta(
    data: Dict[str, Dict[str, Dict[str, Optional[float]]]],
    scenario_key: str,
    newer_key: str,
    older_key: str,
    metric: str,
) -> Optional[float]:
    newer = data[scenario_key][newer_key][metric]
    older = data[scenario_key][older_key][metric]
    if newer is None or older is None:
        return None
    return newer - older


def write_summary_csv(data: Dict[str, Dict[str, Dict[str, Optional[float]]]]) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "smart_calm_version_means.csv"
    fieldnames = ["scenario", "run", "ack_aware", *METRICS.keys()]
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for scenario in SCENARIOS:
            for run in RUNS:
                row = {
                    "scenario": scenario.key,
                    "run": run.key,
                    "ack_aware": str(run.ack_aware).lower(),
                }
                row.update(
                    {
                        metric: "" if value is None else f"{value:.9g}"
                        for metric, value in data[scenario.key][run.key].items()
                    }
                )
                writer.writerow(row)
    return out_path


def write_markdown(data: Dict[str, Dict[str, Dict[str, Optional[float]]]]) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUTPUT_DIR / "ack_aware_version_comparison.md"
    lines = [
        "# ACK-Aware Smart-CALM Version Comparison",
        "",
        "This report compares only `Smart-CALM`. The `previous` rows are archived non-ACK CSVs where `unicast_pdr` means destination DATA arrival; the `ACK-aware` rows are regenerated so `unicast_pdr` means source-side ACK confirmation.",
        "",
        "Scenarios use `50 nodes / 3000 m / 1200 s / mixed traffic / pair-count 8 / 20 seeds` unless noted.",
        "",
        "| Scenario | Run | ACK-confirmed PDR | Destination DATA PDR | Airtime (s) | Collision failures | Fallback forwards | ACK tx |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for scenario in SCENARIOS:
        for run in RUNS:
            row = data[scenario.key][run.key]
            lines.append(
                "| "
                f"{scenario.label} | "
                f"{run.label} | "
                f"{fmt(row['unicast_pdr'], 3)} | "
                f"{fmt(row['destination_unicast_pdr'], 3)} | "
                f"{fmt(row['total_airtime_s'], 0)} | "
                f"{fmt(row['collision_fail'], 0)} | "
                f"{fmt(row['fallback_forward_count'], 0)} | "
                f"{fmt(row['ack_tx'], 0)} |"
            )

    lines.extend(
        [
            "",
            "## Deltas",
            "",
            "| Scenario | v1.1 ACK PDR delta | Latest ACK PDR delta | Latest ACK vs v1.1 ACK PDR | Latest ACK vs v1.1 ACK airtime |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for scenario in SCENARIOS:
        lines.append(
            "| "
            f"{scenario.label} | "
            f"{fmt(delta(data, scenario.key, 'v1_1_ack', 'v1_1_previous', 'unicast_pdr'), 3)} | "
            f"{fmt(delta(data, scenario.key, 'latest_ack', 'v1_1_1_previous', 'unicast_pdr'), 3)} | "
            f"{fmt(delta(data, scenario.key, 'latest_ack', 'v1_1_ack', 'unicast_pdr'), 3)} | "
            f"{fmt(delta(data, scenario.key, 'latest_ack', 'v1_1_ack', 'total_airtime_s'), 0, 's')} |"
        )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def svg_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_metric_svg(
    data: Dict[str, Dict[str, Dict[str, Optional[float]]]],
    metric: str,
) -> Path:
    metric_info = METRICS[metric]
    width = 1180
    height = 640
    left = 126
    right = 56
    top = 90
    bottom = 128
    chart_w = width - left - right
    chart_h = height - top - bottom
    active_runs = [
        run
        for run in RUNS
        if any(data[scenario.key][run.key][metric] is not None for scenario in SCENARIOS)
    ]
    values = [
        data[scenario.key][run.key][metric]
        for scenario in SCENARIOS
        for run in active_runs
        if data[scenario.key][run.key][metric] is not None
    ]
    max_value = max(values) if values else 1.0
    y_max = max_value * 1.14 if max_value else 1.0
    group_w = chart_w / len(SCENARIOS)
    bar_w = min(48.0, group_w / (len(active_runs) + 1.6))

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text{font-family:Georgia,'Times New Roman',serif;fill:#17212b}",
        ".title{font-size:28px;font-weight:700}",
        ".subtitle{font-size:15px;fill:#5c6873}",
        ".axis{stroke:#26323d;stroke-width:1.2}",
        ".grid{stroke:#d9e0e6;stroke-width:1}",
        ".tick{font-size:13px;fill:#64717d}",
        ".label{font-size:14px;font-weight:600}",
        ".value{font-size:12px;fill:#17212b}",
        ".legend{font-size:13px}",
        "</style>",
        '<rect width="100%" height="100%" fill="#fbf8ef"/>',
        '<rect x="22" y="22" width="1136" height="596" rx="18" fill="#fffdf8" stroke="#e1d7c2"/>',
        f'<text x="{left}" y="56" class="title">{svg_escape(metric_info["label"])}: Smart-CALM Version Comparison</text>',
        f'<text x="{left}" y="80" class="subtitle">Previous archived CSVs vs regenerated ACK-aware simulations</text>',
    ]

    for i in range(6):
        value = y_max * i / 5
        y = top + chart_h - (value / y_max) * chart_h
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + chart_w}" y2="{y:.1f}" class="grid"/>')
        parts.append(
            f'<text x="{left - 12}" y="{y + 4:.1f}" text-anchor="end" class="tick">'
            f'{svg_escape(fmt(value, metric_info["precision"], metric_info["unit"]))}</text>'
        )

    parts.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + chart_h}" class="axis"/>')
    parts.append(f'<line x1="{left}" y1="{top + chart_h}" x2="{left + chart_w}" y2="{top + chart_h}" class="axis"/>')

    for scenario_index, scenario in enumerate(SCENARIOS):
        group_left = left + scenario_index * group_w
        bars_w = len(active_runs) * bar_w
        group_x = group_left + (group_w - bars_w) / 2
        for run_index, run in enumerate(active_runs):
            value = data[scenario.key][run.key][metric]
            if value is None:
                continue
            bar_h = (value / y_max) * chart_h
            x = group_x + run_index * bar_w
            y = top + chart_h - bar_h
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w * 0.72:.1f}" height="{bar_h:.1f}" '
                f'rx="5" fill="{COLORS[run.key]}"/>'
            )
            parts.append(
                f'<text x="{x + bar_w * 0.36:.1f}" y="{y - 7:.1f}" text-anchor="middle" class="value">'
                f'{svg_escape(fmt(value, metric_info["precision"]))}</text>'
            )
        parts.append(
            f'<text x="{group_left + group_w / 2:.1f}" y="{height - 82}" '
            f'text-anchor="middle" class="label">{svg_escape(scenario.label)}</text>'
        )

    legend_y = height - 42
    legend_gap = 250 if len(active_runs) > 2 else 270
    legend_x = left
    for run_index, run in enumerate(active_runs):
        x = legend_x + run_index * legend_gap
        parts.append(f'<rect x="{x}" y="{legend_y - 13}" width="18" height="18" rx="4" fill="{COLORS[run.key]}"/>')
        parts.append(f'<text x="{x + 26}" y="{legend_y + 2}" class="legend">{svg_escape(run.label)}</text>')

    parts.append("</svg>")
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = FIGURE_DIR / f"smart_calm_versions_{metric}.svg"
    out_path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return out_path


def main() -> None:
    data = collect()
    written = [write_summary_csv(data), write_markdown(data)]
    written.extend(write_metric_svg(data, metric) for metric in METRICS)
    for path in written:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
