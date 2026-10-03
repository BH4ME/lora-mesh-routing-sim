"""Summarize the frozen ICC protocol-family delivery comparison."""

from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path
from statistics import fmean, stdev


PROTOCOLS = (
    "meshecho-calibrated",
    "meshtastic-like",
    "meshcore-like",
)
T_CRITICAL_19 = 2.093024054408263


def summarize_csv(path: Path) -> dict[str, dict[str, float | int]]:
    rows: dict[str, dict[int, dict[str, str]]] = {name: {} for name in PROTOCOLS}
    with Path(path).open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            protocol = row["protocol"]
            if protocol not in rows:
                continue
            seed = int(row["seed"])
            if seed in rows[protocol]:
                raise ValueError(f"duplicate {protocol} seed {seed}")
            rows[protocol][seed] = row

    seeds = set(rows[PROTOCOLS[0]])
    if len(seeds) != 20 or any(set(rows[name]) != seeds for name in PROTOCOLS):
        raise ValueError("figure requires 20 matched seeds for each protocol model")
    for seed in seeds:
        if len({rows[name][seed]["scheduled_trace_sha256"] for name in PROTOCOLS}) != 1:
            raise ValueError(f"traffic trace differs for seed {seed}")
        if len({rows[name][seed]["unicast_flows"] for name in PROTOCOLS}) != 1:
            raise ValueError(f"unicast denominator differs for seed {seed}")

    summary: dict[str, dict[str, float | int]] = {}
    for protocol in PROTOCOLS:
        item: dict[str, float | int] = {"n": len(seeds)}
        for field, prefix in (
            ("unicast_pdr", "ack"),
            ("destination_unicast_pdr", "destination"),
        ):
            values = [float(rows[protocol][seed][field]) for seed in sorted(seeds)]
            mean = fmean(values)
            half_width = T_CRITICAL_19 * stdev(values) / math.sqrt(len(seeds))
            item[f"{prefix}_mean"] = mean
            item[f"{prefix}_ci_low"] = mean - half_width
            item[f"{prefix}_ci_high"] = mean + half_width
        summary[protocol] = item
    return summary


def write_source_data(
    path: Path,
    recurring: dict[str, dict[str, float | int]],
    random: dict[str, dict[str, float | int]],
) -> None:
    fields = (
        "workload",
        "protocol",
        "n",
        "ack_mean",
        "ack_ci_low",
        "ack_ci_high",
        "destination_mean",
        "destination_ci_low",
        "destination_ci_high",
    )
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for workload, summary in (("Recurring", recurring), ("Random", random)):
            for protocol in PROTOCOLS:
                writer.writerow({"workload": workload, "protocol": protocol, **summary[protocol]})


def render_figure(recurring_csv: Path, random_csv: Path, output_prefix: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    recurring = summarize_csv(recurring_csv)
    random = summarize_csv(random_csv)
    output_prefix = Path(output_prefix)
    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    write_source_data(
        output_prefix.with_name(output_prefix.name + "_source.csv"),
        recurring,
        random,
    )

    matplotlib.rcParams.update(
        {
            "font.family": "sans-serif",
            "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
            "font.size": 7,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
            "axes.linewidth": 0.6,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "hatch.linewidth": 0.5,
        }
    )
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.45), sharey=True)
    palette = ("#0077BB", "#EE7733", "#009988")
    hatches = ("", "//", "..")
    labels = ("MeshEcho (calibrated)", "Meshtastic-like", "MeshCore-like")
    workloads = (recurring, random)
    x = np.array([0.0, 1.0])
    width = 0.22

    for axis, (metric, title) in zip(
        axes,
        (("ack", "(a) Source ACK"), ("destination", "(b) Destination DATA")),
    ):
        for index, protocol in enumerate(PROTOCOLS):
            means = [float(workload[protocol][f"{metric}_mean"]) for workload in workloads]
            lows = [
                max(0.0, float(workload[protocol][f"{metric}_ci_low"]))
                for workload in workloads
            ]
            highs = [
                min(1.0, float(workload[protocol][f"{metric}_ci_high"]))
                for workload in workloads
            ]
            axis.bar(
                x + (index - 1) * width,
                means,
                width,
                yerr=(np.subtract(means, lows), np.subtract(highs, means)),
                color=palette[index],
                edgecolor="#202020",
                linewidth=0.45,
                hatch=hatches[index],
                capsize=2,
                error_kw={"elinewidth": 0.75, "capthick": 0.75},
                label=labels[index],
                zorder=3,
            )
        axis.set_title(title, loc="left", fontsize=7.5, fontweight="bold")
        axis.set_xticks(x, ("Recurring pairs", "Random pairs"))
        axis.set_ylim(0, 1.05)
        axis.set_yticks((0, 0.25, 0.5, 0.75, 1.0))
        axis.set_ylabel("PDR" if axis is axes[0] else "")
        axis.grid(axis="y", color="#D9D9D9", linewidth=0.45, zorder=0)
        axis.tick_params(axis="both", labelsize=6.6, width=0.5, length=2.5)

    handles, legend_labels = axes[0].get_legend_handles_labels()
    fig.legend(
        handles,
        legend_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.985),
        ncol=3,
        frameon=False,
        fontsize=6.8,
        handlelength=1.5,
        columnspacing=1.7,
    )
    fig.subplots_adjust(left=0.07, right=0.99, top=0.80, bottom=0.18, wspace=0.18)
    fig.savefig(output_prefix.with_suffix(".pdf"))
    svg_path = output_prefix.with_suffix(".svg")
    fig.savefig(svg_path)
    svg_path.write_text(
        "\n".join(line.rstrip() for line in svg_path.read_text(encoding="utf-8").splitlines())
        + "\n",
        encoding="utf-8",
    )
    fig.savefig(output_prefix.with_suffix(".png"), dpi=300)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--recurring", type=Path, required=True)
    parser.add_argument("--random", type=Path, required=True)
    parser.add_argument("--output-prefix", type=Path, required=True)
    args = parser.parse_args()
    render_figure(args.recurring, args.random, args.output_prefix)


if __name__ == "__main__":
    main()
