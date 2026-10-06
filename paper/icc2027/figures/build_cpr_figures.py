#!/usr/bin/env python3
"""Build ICC tables and figures directly from audited MeshEcho-CPR runs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


ARMS = (
    "meshecho-cpr",
    "meshecho-cpr-nocancel",
    "meshecho-drc-no-rescue",
    "meshecho-drc",
)
COMPARATORS = ARMS[1:]
SEED_COUNT = 20
T_CRITICAL_19 = 2.093024054408263
IDENTITY_FIELDS = (
    "case_sha256",
    "scheduled_trace_sha256",
    "topology_sha256",
    "radio_sha256",
    "pair_pool_sha256",
    "scheduled_unicast_flows",
)
METRICS = {
    "ack": "ack_pdr_deadline",
    "delivery": "delivery_pdr_deadline",
    "airtime": "tx_ledger_airtime_s",
    "energy": "tx_ledger_energy_j",
    "tx_count": "tx_count",
    "rx_attempts": "rx_attempt_count",
    "collisions": "collision_fail",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _ci(values: Sequence[float]) -> dict[str, float | int]:
    if not values:
        raise ValueError("cannot summarize an empty sample")
    mean = statistics.fmean(values)
    if len(values) == 1:
        half_width = 0.0
    else:
        half_width = T_CRITICAL_19 * statistics.stdev(values) / math.sqrt(len(values))
    return {
        "n": len(values),
        "mean": mean,
        "ci_low": mean - half_width,
        "ci_high": mean + half_width,
    }


def _validate_rows(rows: Sequence[Mapping[str, str]], manifest: Mapping[str, Any]) -> list[int]:
    if tuple(manifest.get("protocols", ())) != ARMS:
        raise ValueError("manifest arm order is not the frozen CPR order")
    seeds = sorted({int(row["seed"]) for row in rows})
    if len(seeds) != SEED_COUNT:
        raise ValueError(f"expected {SEED_COUNT} seeds, got {len(seeds)}")
    expected_scopes = {(seed, arm) for seed in seeds for arm in ARMS}
    actual_scopes = {(int(row["seed"]), row["protocol"]) for row in rows}
    if actual_scopes != expected_scopes:
        raise ValueError("runs CSV has an incomplete or duplicate arm/seed scope")
    for seed in seeds:
        paired = [row for row in rows if int(row["seed"]) == seed]
        for field in IDENTITY_FIELDS:
            values = {row[field] for row in paired}
            if len(values) != 1:
                raise ValueError(f"seed {seed} is not paired for {field}")
    manifest_seeds = tuple(sorted(int(seed) for seed in manifest.get("seeds", ())))
    if manifest_seeds != tuple(seeds):
        raise ValueError("manifest seed list does not match runs CSV")
    return seeds


def _arm_summary(rows: Sequence[Mapping[str, str]], seeds: Sequence[int]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for label, field in METRICS.items():
        by_seed = {int(row["seed"]): float(row[field]) for row in rows}
        if set(by_seed) != set(seeds):
            raise ValueError(f"missing {label} rows in arm summary")
        result[label] = _ci([by_seed[seed] for seed in seeds])
    result["scheduled_flows"] = sum(
        int(row["scheduled_unicast_flows"]) for row in rows
    )
    return result


def _paired_summary(
    rows_by_scope: Mapping[tuple[int, str], Mapping[str, str]],
    seeds: Sequence[int],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for comparator in COMPARATORS:
        comparator_result: dict[str, Any] = {}
        for label, field in METRICS.items():
            deltas = [
                float(rows_by_scope[(seed, ARMS[0])][field])
                - float(rows_by_scope[(seed, comparator)][field])
                for seed in seeds
            ]
            comparator_result[label] = _ci(deltas)
        result[comparator] = comparator_result
    return result


def summarize_population(
    *, runs_path: Path, actions_path: Path, manifest_path: Path,
) -> dict[str, Any]:
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = list(csv.DictReader(Path(runs_path).open(newline="", encoding="utf-8")))
    seeds = _validate_rows(rows, manifest)
    rows_by_scope = {(int(row["seed"]), row["protocol"]): row for row in rows}
    arms = {
        arm: _arm_summary(
            [row for row in rows if row["protocol"] == arm], seeds,
        )
        for arm in ARMS
    }
    actions = {
        action: sum(
            event.get("protocol") == ARMS[0]
            and event.get("event") == "decision"
            and event.get("action") == action
            for event in _read_jsonl(Path(actions_path))
        )
        for action in ("F_INITIAL", "R_INITIAL", "R_REPEAT", "F_RECOVERY")
    }
    actions["cpr-cancel"] = sum(
        event.get("protocol") == ARMS[0]
        and event.get("event") == "cpr-cancel"
        for event in _read_jsonl(Path(actions_path))
    )
    return {
        "schema": "meshecho-cpr-icc-summary-v1",
        "stage": manifest.get("experiment_stage", manifest.get("seed_split")),
        "seed_count": len(seeds),
        "seeds": seeds,
        "case": manifest.get("case", {}),
        "manifest_sha256": sha256(manifest_path),
        "runs_sha256": sha256(Path(runs_path)),
        "actions_sha256": sha256(Path(actions_path)),
        "arms": arms,
        "paired": _paired_summary(rows_by_scope, seeds),
        "actions": actions,
    }


def _write_table_csv(path: Path, summary: Mapping[str, Any]) -> None:
    fields = ["stage", "arm", "metric", "n", "mean", "ci_low", "ci_high"]
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for arm in ARMS:
            for metric in METRICS:
                values = summary["arms"][arm][metric]
                writer.writerow({
                    "stage": summary["stage"],
                    "arm": arm,
                    "metric": metric,
                    **values,
                })
        for comparator in COMPARATORS:
            for metric in METRICS:
                values = summary["paired"][comparator][metric]
                writer.writerow({
                    "stage": summary["stage"],
                    "arm": f"meshecho-cpr-minus-{comparator}",
                    "metric": metric,
                    **values,
                })


def render_figure(summaries: Sequence[Mapping[str, Any]], output_prefix: Path) -> None:
    holdout = next(summary for summary in summaries if summary["stage"] == "holdout")
    arms = list(ARMS)
    output_prefix = Path(output_prefix)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    colors = ("CPRblue", "CPRorange", "CPRteal", "CPRred")
    labels = (r"CPR", r"CPR\\no cancel", r"DRC\\no rescue", r"DRC")
    panels = (
        ("ack", "(a) Deadline ACK PDR", 0.85, 1.01, ("0.85", "0.90", "0.95", "1.00")),
        ("delivery", "(b) Destination PDR", 0.85, 1.01, ("0.85", "0.90", "0.95", "1.00")),
        ("airtime", "(c) TX airtime (s)", 0.0, 13.0, ("0", "4", "8", "12")),
    )
    width = 2.72
    height = 2.05
    shift = 3.05
    bar_positions = (0.18, 0.78, 1.38, 1.98)
    bar_width = 0.38
    chunks = [
        r"\begin{tikzpicture}[font=\sffamily\scriptsize, line join=round]",
        r"\definecolor{CPRblue}{HTML}{0077BB}",
        r"\definecolor{CPRorange}{HTML}{EE7733}",
        r"\definecolor{CPRteal}{HTML}{009988}",
        r"\definecolor{CPRred}{HTML}{CC3311}",
        r"\definecolor{CPRgrid}{HTML}{D9D9D9}",
    ]
    for panel_index, (metric, title, ymin, ymax, ticks) in enumerate(panels):
        xshift = panel_index * shift
        chunks.append(rf"\begin{{scope}}[xshift={xshift:.2f}cm]")
        chunks.append(rf"\draw[draw=black!55, line width=0.35pt] (0,0) rectangle ({width:.2f},{height:.2f});")
        for tick in ticks:
            value = float(tick)
            y = (value - ymin) / (ymax - ymin) * height
            chunks.append(rf"\draw[CPRgrid, line width=0.25pt] (0,{y:.4f}) -- ({width:.2f},{y:.4f});")
            chunks.append(rf"\node[anchor=east, font=\tiny] at (-0.05,{y:.4f}) {{{tick}}};")
        chunks.append(rf"\node[anchor=south west, font=\scriptsize\bfseries] at (0,{height + 0.08:.2f}) {{{title}}};")
        for index, arm in enumerate(arms):
            values = holdout["arms"][arm][metric]
            mean = float(values["mean"])
            low = float(values["ci_low"])
            high = float(values["ci_high"])
            # The chart origin represents the lower bound of each panel.
            bar_bottom = 0.0
            bar_top = (mean - ymin) / (ymax - ymin) * height
            low_y = (low - ymin) / (ymax - ymin) * height
            high_y = (high - ymin) / (ymax - ymin) * height
            x = bar_positions[index]
            chunks.append(rf"\fill[{colors[index]}] ({x:.2f},{bar_bottom:.4f}) rectangle ({x + bar_width:.2f},{bar_top:.4f});")
            center = x + bar_width / 2
            chunks.append(rf"\draw[black, line width=0.3pt] ({center:.2f},{low_y:.4f}) -- ({center:.2f},{high_y:.4f});")
            chunks.append(rf"\draw[black, line width=0.3pt] ({center - 0.07:.2f},{low_y:.4f}) -- ({center + 0.07:.2f},{low_y:.4f});")
            chunks.append(rf"\draw[black, line width=0.3pt] ({center - 0.07:.2f},{high_y:.4f}) -- ({center + 0.07:.2f},{high_y:.4f});")
            chunks.append(rf"\node[anchor=north, align=center, font=\tiny] at ({center:.2f},-0.08) {{{labels[index]}}};")
        chunks.append(rf"\end{{scope}}")
    chunks.append(r"\end{tikzpicture}")
    output_prefix.with_suffix(".tex").write_text("\n".join(chunks) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development-prefix", type=Path, required=True)
    parser.add_argument("--holdout-prefix", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()
    summaries = []
    for prefix in (args.development_prefix, args.holdout_prefix):
        summary = summarize_population(
            runs_path=prefix.with_suffix(".runs.csv"),
            actions_path=prefix.with_suffix(".actions.jsonl"),
            manifest_path=prefix.with_suffix(".manifest.json"),
        )
        summaries.append(summary)
    output_prefix = Path(args.output_prefix)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    for summary in summaries:
        stage_prefix = output_prefix.with_name(
            f"{output_prefix.name}_{summary['stage']}"
        )
        stage_prefix.with_suffix(".json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _write_table_csv(stage_prefix.with_suffix(".csv"), summary)
    render_figure(summaries, output_prefix)


if __name__ == "__main__":
    main()
