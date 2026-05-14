#!/usr/bin/env python3
"""Build Smart-CALM v1.1.2 candidate comparison charts."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
OUT_DIR = RESULTS / "figures" / "smart_calm_v1_1_2"
SMART_PROTOCOL = "smart-calm"


@dataclass(frozen=True)
class Scenario:
    key: str
    label: str
    old_csv: Path
    new_csv: Path


SCENARIOS = (
    Scenario(
        key="rate14",
        label="High load",
        old_csv=RESULTS / "anti_cherrypick_stress" / "rate14.csv",
        new_csv=RESULTS / "v1_1_2_rate14_smart.csv",
    ),
    Scenario(
        key="shadow8",
        label="High shadow",
        old_csv=RESULTS / "anti_cherrypick_stress" / "shadow8.csv",
        new_csv=RESULTS / "v1_1_2_shadow8_smart.csv",
    ),
    Scenario(
        key="sparse4k",
        label="Sparse",
        old_csv=RESULTS / "anti_cherrypick_stress" / "sparse4k.csv",
        new_csv=RESULTS / "v1_1_2_sparse4k_smart.csv",
    ),
)


METRICS = {
    "unicast_pdr": ("Unicast PDR", 3),
    "total_airtime_s": ("Total Airtime (s)", 0),
    "collision_fail": ("Collision Failures", 0),
    "fallback_forward_count": ("Fallback Forwards", 0),
}


def rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            row
            for row in csv.DictReader(handle)
            if row.get("protocol") == SMART_PROTOCOL
        ]


def metric_mean(input_rows: Iterable[Dict[str, str]], metric: str) -> float:
    values = [float(row[metric]) for row in input_rows]
    if not values:
        raise ValueError(f"missing values for {metric}")
    return mean(values)


def collect() -> Dict[str, Dict[str, Dict[str, float]]]:
    data: Dict[str, Dict[str, Dict[str, float]]] = {}
    for scenario in SCENARIOS:
        data[scenario.key] = {}
        old_rows = rows(scenario.old_csv)
        new_rows = rows(scenario.new_csv)
        for version, source_rows in (("v1.1.1", old_rows), ("v1.1.2", new_rows)):
            data[scenario.key][version] = {
                metric: metric_mean(source_rows, metric)
                for metric in METRICS
            }
    return data


def fmt(value: float, precision: int) -> str:
    return f"{value:.0f}" if precision == 0 else f"{value:.{precision}f}"


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_svg(data: Dict[str, Dict[str, Dict[str, float]]]) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    width = 1280
    height = 940
    panel_w = 560
    panel_h = 350
    margin_x = 90
    margin_y = 110
    gap_x = 70
    gap_y = 90
    colors = {"v1.1.1": "#7c8794", "v1.1.2": "#b15b1a"}

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text{font-family:Georgia,'Times New Roman',serif;fill:#17212b}",
        ".title{font-size:32px;font-weight:700}",
        ".subtitle{font-size:15px;fill:#596674}",
        ".panel-title{font-size:20px;font-weight:700}",
        ".axis{stroke:#26323d;stroke-width:1.2}",
        ".grid{stroke:#d9e0e6;stroke-width:1}",
        ".tick{font-size:11px;fill:#65717d}",
        ".label{font-size:13px;font-weight:600}",
        ".value{font-size:11px;fill:#17212b}",
        ".legend{font-size:14px;font-weight:600}",
        "</style>",
        '<rect width="100%" height="100%" fill="#fbf8ef"/>',
        '<rect x="24" y="24" width="1232" height="892" rx="24" fill="#fffdf8" stroke="#e1d7c2"/>',
        '<text x="72" y="68" class="title">Smart-CALM v1.1.2 Candidate vs v1.1.1</text>',
        '<text x="72" y="94" class="subtitle">Mean over fixed stress seeds; lower is better for airtime, collisions, and fallback.</text>',
    ]

    legend_x = 840
    for i, version in enumerate(("v1.1.1", "v1.1.2")):
        x = legend_x + i * 150
        parts.append(f'<rect x="{x}" y="50" width="20" height="14" rx="3" fill="{colors[version]}"/>')
        parts.append(f'<text x="{x + 28}" y="63" class="legend">{version}</text>')

    metric_items = list(METRICS.items())
    for metric_index, (metric, (metric_label, precision)) in enumerate(metric_items):
        col = metric_index % 2
        row = metric_index // 2
        x0 = margin_x + col * (panel_w + gap_x)
        y0 = margin_y + row * (panel_h + gap_y)
        chart_left = x0 + 70
        chart_top = y0 + 48
        chart_w = panel_w - 105
        chart_h = panel_h - 105
        max_value = max(
            data[scenario.key][version][metric]
            for scenario in SCENARIOS
            for version in ("v1.1.1", "v1.1.2")
        )
        y_max = max_value * 1.15 if max_value else 1.0
        group_w = chart_w / len(SCENARIOS)
        bar_w = group_w * 0.24

        parts.append(f'<text x="{x0}" y="{y0 + 24}" class="panel-title">{esc(metric_label)}</text>')
        for tick in range(5):
            value = y_max * tick / 4
            y = chart_top + chart_h - (value / y_max) * chart_h
            parts.append(f'<line x1="{chart_left}" y1="{y:.1f}" x2="{chart_left + chart_w}" y2="{y:.1f}" class="grid"/>')
            parts.append(
                f'<text x="{chart_left - 10}" y="{y + 4:.1f}" text-anchor="end" class="tick">'
                f'{esc(fmt(value, precision))}</text>'
            )
        parts.append(f'<line x1="{chart_left}" y1="{chart_top}" x2="{chart_left}" y2="{chart_top + chart_h}" class="axis"/>')
        parts.append(f'<line x1="{chart_left}" y1="{chart_top + chart_h}" x2="{chart_left + chart_w}" y2="{chart_top + chart_h}" class="axis"/>')

        for scenario_index, scenario in enumerate(SCENARIOS):
            center = chart_left + scenario_index * group_w + group_w / 2
            for version_index, version in enumerate(("v1.1.1", "v1.1.2")):
                value = data[scenario.key][version][metric]
                h = (value / y_max) * chart_h
                x = center + (version_index - 0.5) * (bar_w + 8) - bar_w / 2
                y = chart_top + chart_h - h
                parts.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" '
                    f'rx="5" fill="{colors[version]}"/>'
                )
                parts.append(
                    f'<text x="{x + bar_w / 2:.1f}" y="{y - 6:.1f}" text-anchor="middle" class="value">'
                    f'{esc(fmt(value, precision))}</text>'
                )
            parts.append(
                f'<text x="{center:.1f}" y="{chart_top + chart_h + 28}" text-anchor="middle" class="label">'
                f'{esc(scenario.label)}</text>'
            )

    out_path = OUT_DIR / "v1_1_2_candidate_comparison.svg"
    parts.append("</svg>")
    out_path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return out_path


def main() -> None:
    out_path = write_svg(collect())
    print(out_path.relative_to(ROOT))


if __name__ == "__main__":
    main()
