#!/usr/bin/env python3
"""Build a tag-indexed Smart-CALM result gallery with per-version bar charts."""

from __future__ import annotations

import csv
import subprocess
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, List, Sequence


ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
DOCS_RESULTS = ROOT / "docs" / "results"
OUT_DIR = RESULTS / "figures" / "smart_calm_tags"

SMART_PROTOCOL = "smart-calm"


@dataclass(frozen=True)
class Scenario:
    key: str
    label: str
    suffix: str


@dataclass(frozen=True)
class Version:
    key: str
    tag: str
    label: str
    result_prefix: str
    note: str
    commit_ref: str | None = None

    def csv_path(self, scenario: Scenario) -> Path:
        return RESULTS / f"{self.result_prefix}_{scenario.suffix}.csv"


SCENARIOS = (
    Scenario("mixed", "Mixed traffic", "mixed"),
    Scenario("shadow6", "High shadowing", "mixed_shadow6"),
    Scenario("rate10", "High offered load", "mixed_rate10"),
)

VERSIONS = (
    Version(
        key="v1_0",
        tag="smart-calm-sim-v1.0",
        label="v1.0",
        result_prefix="smart_calm_50n",
        note="Frozen Smart-CALM simulator baseline.",
    ),
    Version(
        key="v1_1",
        tag="smart-calm-sim-v1.1",
        label="v1.1",
        result_prefix="smart_calm_v1_1_50n",
        note="Cached-path timeout retry before fallback flooding.",
    ),
    Version(
        key="v2",
        tag="smart-calm-sim-v2",
        label="v2",
        result_prefix="smart_calm_v2_50n",
        note="Timeout-rescue radius follows the active online profile.",
        commit_ref="release tag",
    ),
)

METRICS = {
    "unicast_pdr": {
        "label": "Unicast PDR",
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
}

VERSION_COLORS = {
    "v1_0": "#8a5a44",
    "v1_1": "#2f6f73",
    "v2": "#1f4e8c",
}


def read_rows(path: Path) -> List[Dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate_rows(rows: Sequence[Dict[str, str]], version: Version, scenario: Scenario) -> None:
    if not rows:
        raise ValueError(f"No rows found for {version.tag} / {scenario.label}")
    protocols = {row.get("protocol", "") for row in rows}
    if SMART_PROTOCOL not in protocols:
        raise ValueError(f"Missing {SMART_PROTOCOL} rows in {version.csv_path(scenario)}")
    missing_metrics = [
        metric
        for metric in METRICS
        if any(metric not in row for row in rows)
    ]
    if missing_metrics:
        raise ValueError(
            f"Missing metric columns in {version.csv_path(scenario)}: {', '.join(missing_metrics)}"
        )


def metric_mean(rows: Iterable[Dict[str, str]], metric: str, version: Version, scenario: Scenario) -> float:
    values = [
        float(row[metric])
        for row in rows
        if row.get("protocol") == SMART_PROTOCOL and row.get(metric) not in {None, ""}
    ]
    if not values:
        raise ValueError(f"Missing {metric} values for {version.tag} / {scenario.label}")
    return mean(values)


def collect() -> Dict[str, Dict[str, Dict[str, float]]]:
    data: Dict[str, Dict[str, Dict[str, float]]] = {}
    for version in VERSIONS:
        data[version.key] = {}
        for scenario in SCENARIOS:
            rows = read_rows(version.csv_path(scenario))
            validate_rows(rows, version, scenario)
            data[version.key][scenario.key] = {
                metric: metric_mean(rows, metric, version, scenario)
                for metric in METRICS
            }
    return data


def resolve_tag_commit(tag: str) -> str:
    try:
        commit = subprocess.check_output(
            ["git", "rev-list", "-n", "1", tag],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"
    return commit[:7] if commit else "unknown"


def version_commit_ref(version: Version) -> str:
    return version.commit_ref or resolve_tag_commit(version.tag)


def fmt(value: float, precision: int, unit: str = "") -> str:
    if precision == 0:
        text = f"{value:.0f}"
    else:
        text = f"{value:.{precision}f}"
    return f"{text} {unit}".rstrip()


def svg_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def write_version_metric_svg(
    data: Dict[str, Dict[str, Dict[str, float]]],
    version: Version,
    metric: str,
) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    metric_info = METRICS[metric]
    width = 980
    height = 560
    left = 110
    right = 56
    top = 86
    bottom = 112
    chart_w = width - left - right
    chart_h = height - top - bottom
    values = [data[version.key][scenario.key][metric] for scenario in SCENARIOS]
    max_value = max(values) if values else 1.0
    y_max = max_value * 1.12 if max_value else 1.0
    group_w = chart_w / len(SCENARIOS)
    bar_w = group_w * 0.42

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<style>",
        "text{font-family:Georgia,'Times New Roman',serif;fill:#17212b}",
        ".title{font-size:28px;font-weight:700}",
        ".subtitle{font-size:14px;fill:#5c6873}",
        ".axis{stroke:#26323d;stroke-width:1.3}",
        ".grid{stroke:#d9e0e6;stroke-width:1}",
        ".tick{font-size:12px;fill:#64717d}",
        ".label{font-size:14px;font-weight:600}",
        ".value{font-size:13px;fill:#17212b}",
        ".note{font-size:13px;fill:#5c6873}",
        "</style>",
        '<rect width="100%" height="100%" fill="#fbf8ef"/>',
        '<rect x="22" y="22" width="936" height="516" rx="22" fill="#fffdf8" stroke="#e1d7c2"/>',
        f'<text x="{left}" y="54" class="title">{svg_escape(version.label)} {svg_escape(metric_info["label"])}</text>',
        f'<text x="{left}" y="77" class="subtitle">{svg_escape(version.tag)} · 50 nodes, 3000 m, 1200 s, 20 seeds</text>',
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
        value = data[version.key][scenario.key][metric]
        bar_h = (value / y_max) * chart_h
        x = left + scenario_index * group_w + group_w / 2 - bar_w / 2
        y = top + chart_h - bar_h
        parts.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" '
            f'rx="7" fill="{VERSION_COLORS[version.key]}"/>'
        )
        parts.append(
            f'<text x="{x + bar_w / 2:.1f}" y="{y - 8:.1f}" text-anchor="middle" class="value">'
            f'{svg_escape(fmt(value, metric_info["precision"]))}</text>'
        )
        parts.append(
            f'<text x="{left + scenario_index * group_w + group_w / 2:.1f}" y="{height - 70}" '
            f'text-anchor="middle" class="label">{svg_escape(scenario.label)}</text>'
        )

    parts.append(f'<text x="{left}" y="{height - 36}" class="note">{svg_escape(version.note)}</text>')
    parts.append("</svg>")
    out_path = OUT_DIR / f"{version.key}_{metric}.svg"
    out_path.write_text("\n".join(parts) + "\n", encoding="utf-8")
    return out_path


def write_markdown(
    data: Dict[str, Dict[str, Dict[str, float]]],
    outputs: Dict[str, Dict[str, Path]],
) -> Path:
    DOCS_RESULTS.mkdir(parents=True, exist_ok=True)
    out_path = DOCS_RESULTS / "smart_calm_tag_gallery.md"
    lines = [
        "# Smart-CALM Tag Gallery",
        "",
        "Versioned Smart-CALM simulation tags and their bar charts.",
        "",
        "Formal scenarios use `50 nodes / 3000 m / 1200 s / mixed traffic / pair-count 8 / 20 seeds` unless noted.",
        "",
        "| Tag | Commit / ref | Version focus | Mixed PDR | Mixed airtime (s) | Mixed collisions | High-load PDR | High-load airtime (s) | High-load collisions |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for version in VERSIONS:
        mixed = data[version.key]["mixed"]
        rate10 = data[version.key]["rate10"]
        lines.append(
            "| "
            f"`{version.tag}` | "
            f"`{version_commit_ref(version)}` | "
            f"{version.note} | "
            f"{mixed['unicast_pdr']:.3f} | "
            f"{mixed['total_airtime_s']:.0f} | "
            f"{mixed['collision_fail']:.0f} | "
            f"{rate10['unicast_pdr']:.3f} | "
            f"{rate10['total_airtime_s']:.0f} | "
            f"{rate10['collision_fail']:.0f} |"
        )

    for version in VERSIONS:
        lines.extend(
            [
                "",
                f"## `{version.tag}`",
                "",
                version.note,
                "",
            ]
        )
        for metric in METRICS:
            chart_path = outputs[version.key][metric]
            relative_path = chart_path if not chart_path.is_absolute() else chart_path.relative_to(ROOT)
            lines.append(f"![{version.label} {METRICS[metric]['label']}](../../{relative_path.as_posix()})")
            lines.append("")
    out_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return out_path


def build() -> tuple[Path, Dict[str, Dict[str, Path]]]:
    data = collect()
    outputs = {
        version.key: {
            metric: write_version_metric_svg(data, version, metric)
            for metric in METRICS
        }
        for version in VERSIONS
    }
    markdown_path = write_markdown(data, outputs)
    return markdown_path, outputs


def main() -> None:
    markdown_path, outputs = build()
    print(markdown_path.relative_to(ROOT))
    for version in VERSIONS:
        for metric in METRICS:
            print(outputs[version.key][metric].relative_to(ROOT))


if __name__ == "__main__":
    main()
