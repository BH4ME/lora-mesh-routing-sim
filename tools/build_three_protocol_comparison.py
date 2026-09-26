#!/usr/bin/env python3
"""Build three-protocol comparison tables and SVG charts from simulator CSVs."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Sequence


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
DOCS_RESULTS = ROOT / "docs" / "results"
OUT_DIR = RESULTS / "figures"


PROTOCOLS = ("meshtastic-like", "meshcore-like", "smart-calm")
PROTOCOL_LABELS = {
    "meshtastic-like": "Meshtastic-like",
    "meshcore-like": "MeshCore-like",
    "smart-calm": "Smart-CALM v1.1",
}
COLORS = {
    "meshtastic-like": "#2f6f73",
    "meshcore-like": "#c77d32",
    "smart-calm": "#1f4e8c",
}


@dataclass(frozen=True)
class Scenario:
    key: str
    label: str
    csv_path: Path


SCENARIOS = (
    Scenario(
        key="mixed",
        label="Mixed traffic",
        csv_path=RESULTS / "smart_calm_v1_1_50n_mixed.csv",
    ),
    Scenario(
        key="shadow6",
        label="High shadowing",
        csv_path=RESULTS / "smart_calm_v1_1_50n_mixed_shadow6.csv",
    ),
    Scenario(
        key="rate10",
        label="High offered load",
        csv_path=RESULTS / "smart_calm_v1_1_50n_mixed_rate10.csv",
    ),
)


METRICS = {
    "unicast_pdr": {
        "label": "Unicast PDR",
        "unit": "",
        "scale": 1.0,
        "precision": 3,
    },
    "total_airtime_s": {
        "label": "Total Airtime",
        "unit": "s",
        "scale": 1.0,
        "precision": 0,
    },
    "collision_fail": {
        "label": "Collision Failures",
        "unit": "",
        "scale": 1.0,
        "precision": 0,
    },
}


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def metric_mean(
    rows: Iterable[Dict[str, str]],
    protocol: str,
    metric: str,
    scenario: Scenario,
) -> float:
    values = [
        float(row[metric])
        for row in rows
        if row["protocol"] == protocol and row.get(metric) not in {None, ""}
    ]
    if not values:
        raise ValueError(
            f"Missing {metric} values for {protocol} in {scenario.csv_path}"
        )
    return mean(values)


def validate_rows(rows: Sequence[Dict[str, str]], scenario: Scenario) -> None:
    if not rows:
        raise ValueError(f"No rows found in {scenario.csv_path}")
    missing_protocols = sorted(set(PROTOCOLS) - {row.get("protocol", "") for row in rows})
    if missing_protocols:
        raise ValueError(
            f"Missing protocol rows in {scenario.csv_path}: {', '.join(missing_protocols)}"
        )
    missing_metrics = [
        metric
        for metric in METRICS
        if any(metric not in row for row in rows)
    ]
    if missing_metrics:
        raise ValueError(
            f"Missing metric columns in {scenario.csv_path}: {', '.join(missing_metrics)}"
        )


def collect() -> Dict[str, Dict[str, Dict[str, float]]]:
    data: Dict[str, Dict[str, Dict[str, float]]] = {}
    for scenario in SCENARIOS:
        rows = read_rows(scenario.csv_path)
        validate_rows(rows, scenario)
        data[scenario.key] = {
            protocol: {
                metric: metric_mean(rows, protocol, metric, scenario)
                for metric in METRICS
            }
            for protocol in PROTOCOLS
        }
    return data


def fmt(value: float, precision: int, unit: str = "") -> str:
    if precision == 0:
        text = f"{value:.0f}"
    else:
        text = f"{value:.{precision}f}"
    return f"{text} {unit}".rstrip()


def write_markdown(data: Dict[str, Dict[str, Dict[str, float]]]) -> Path:
    DOCS_RESULTS.mkdir(parents=True, exist_ok=True)
    out_path = DOCS_RESULTS / "three_protocol_comparison.md"
    lines = [
        "# Three-Protocol Comparison",
        "",
        "Protocols compared: `Meshtastic-like`, `MeshCore-like`, and `Smart-CALM v1.1`.",
        "",
        "Scenarios use `50 nodes / 3000 m / 1200 s / mixed traffic / pair-count 8 / 20 seeds` unless noted.",
        "",
        "This report is pinned to the archived Smart-CALM v1.1 CSV files. The later v2 algorithm is intentionally excluded here. ACK-confirmed variants are reported separately in `results/ack_aware_comparison/`.",
        "",
        "| Scenario | Protocol | Unicast PDR | Airtime (s) | Collision failures |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for scenario in SCENARIOS:
        for protocol in PROTOCOLS:
            row = data[scenario.key][protocol]
            lines.append(
                "| "
                f"{scenario.label} | "
                f"{PROTOCOL_LABELS[protocol]} | "
                f"{row['unicast_pdr']:.3f} | "
                f"{row['total_airtime_s']:.0f} | "
                f"{row['collision_fail']:.0f} |"
            )
    lines.extend(
        [
            "",
            "## Meeting Takeaway",
            "",
            "- `Meshtastic-like` keeps strong reliability, but spends the most airtime and creates the most collisions.",
            "- `MeshCore-like` is cheaper than flooding, but loses unicast reliability in mixed and stressed traffic.",
            "- `Smart-CALM v1.1` improves unicast PDR over `MeshCore-like` while staying materially below `Meshtastic-like` airtime in the three archived scenarios.",
            "- Under high offered load, `Smart-CALM v1.1` stays close to managed flooding on reliability while still reducing channel occupancy.",
        ]
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
    data: Dict[str, Dict[str, Dict[str, float]]],
    metric: str,
) -> Path:
    metric_info = METRICS[metric]
    width = 1100
    height = 620
    left = 120
    right = 60
    top = 86
    bottom = 118
    chart_w = width - left - right
    chart_h = height - top - bottom
    values = [
        data[scenario.key][protocol][metric]
        for scenario in SCENARIOS
        for protocol in PROTOCOLS
    ]
    max_value = max(values) if values else 1.0
    y_max = max_value * 1.12 if max_value else 1.0
    group_w = chart_w / len(SCENARIOS)
    bar_w = group_w / 5.0

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text{font-family:Georgia,'Times New Roman',serif;fill:#17212b}",
        ".title{font-size:30px;font-weight:700}",
        ".subtitle{font-size:15px;fill:#5c6873}",
        ".axis{stroke:#26323d;stroke-width:1.3}",
        ".grid{stroke:#d9e0e6;stroke-width:1}",
        ".tick{font-size:13px;fill:#64717d}",
        ".label{font-size:14px;font-weight:600}",
        ".value{font-size:13px;fill:#17212b}",
        ".legend{font-size:14px}",
        "</style>",
        '<rect width="100%" height="100%" fill="#fbf8ef"/>',
        '<rect x="24" y="24" width="1052" height="572" rx="22" fill="#fffdf8" stroke="#e1d7c2"/>',
        f'<text x="{left}" y="54" class="title">{svg_escape(metric_info["label"])}: Three-Protocol Comparison</text>',
        f'<text x="{left}" y="78" class="subtitle">50 nodes, 3000 m area, 1200 s, 20 seeds</text>',
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
        group_x = left + scenario_index * group_w + group_w * 0.22
        for protocol_index, protocol in enumerate(PROTOCOLS):
            value = data[scenario.key][protocol][metric]
            bar_h = (value / y_max) * chart_h
            x = group_x + protocol_index * bar_w
            y = top + chart_h - bar_h
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w * 0.78:.1f}" height="{bar_h:.1f}" '
                f'rx="6" fill="{COLORS[protocol]}"/>'
            )
            parts.append(
                f'<text x="{x + bar_w * 0.39:.1f}" y="{y - 8:.1f}" text-anchor="middle" class="value">'
                f'{svg_escape(fmt(value, metric_info["precision"]))}</text>'
            )
        parts.append(
            f'<text x="{left + scenario_index * group_w + group_w / 2:.1f}" y="{height - 72}" '
            f'text-anchor="middle" class="label">{svg_escape(scenario.label)}</text>'
        )

    legend_x = left
    legend_y = height - 38
    for protocol_index, protocol in enumerate(PROTOCOLS):
        x = legend_x + protocol_index * 245
        parts.append(f'<rect x="{x}" y="{legend_y - 13}" width="18" height="18" rx="4" fill="{COLORS[protocol]}"/>')
        parts.append(f'<text x="{x + 26}" y="{legend_y + 2}" class="legend">{PROTOCOL_LABELS[protocol]}</text>')

    parts.append("</svg>")
    out_path = OUT_DIR / f"three_protocol_{metric}.svg"
    out_path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return out_path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = collect()
    written = [write_markdown(data)]
    written.extend(write_metric_svg(data, metric) for metric in METRICS)
    for path in written:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
