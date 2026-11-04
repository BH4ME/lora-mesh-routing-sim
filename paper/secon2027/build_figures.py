#!/usr/bin/env python3
"""Publication figures from the complete, audited formal-v1 analysis.

This script never simulates, bootstraps, selects seeds, or changes evidence.
All means and intervals come from the retained analyzer tables. The four
quantitative grids ask about policy trade-offs, component effects, finite
robustness, and latency/cost. No favorable conclusion is assumed.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[2]
EXPECTED_PLAN = "5f1a12fe49bf7fc0ea32cc048a3595ed0bd290811f952a47c5a33b0cded2cbb0"
EXPECTED_SNAPSHOT = "63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee"
PROTOCOLS = ("meshecho-cpr", "meshecho", "meshtastic", "meshcore")
LABELS = ("MeshEcho-CPR", "Legacy MeshEcho", "Meshtastic-like", "MeshCore-like")
COLORS = ("#21668D", "#767676", "#BD7841", "#8477A8")
MARKERS = ("o", "s", "^", "D")
MAIN = tuple(f"{s}-{r}" for s in ("S1", "S2", "S3") for r in ("default", "matched"))
METRICS = ("ack_pdr_deadline", "tx_ledger_airtime_s")
TABLES = ("planned_runs", "runs", "summary", "paired_effects", "cost_summary")
STYLE = {"font.family": "DejaVu Sans", "font.size": 7, "axes.titlesize": 8,
         "axes.labelsize": 7, "legend.fontsize": 6.7, "xtick.labelsize": 6.6,
         "ytick.labelsize": 6.6, "axes.spines.top": False, "axes.spines.right": False,
         "axes.linewidth": 0.6, "lines.linewidth": 0.9, "lines.markersize": 3.7,
         "pdf.fonttype": 42, "ps.fonttype": 42, "svg.fonttype": "none",
         "savefig.facecolor": "white", "figure.facecolor": "white"}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                      allow_nan=False).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def number(value):
    if value in (None, ""):
        return None
    value = float(value)
    require(math.isfinite(value), "Nonfinite value in source table")
    return value


def write_csv(path, rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with path.open("x", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def validate(analysis_dir, root):
    """Verify the completed audit and content hashes without running research."""
    report_path = analysis_dir / "analysis.json"
    report = json.loads(report_path.read_text())
    require(report.get("schema") == "secon2027-analysis-v1", "Unsupported analysis schema")
    require(report.get("status") == "complete" and report.get("performance_summary_created") is True,
            "Incomplete/failed analysis: no publication figures may be produced")
    require(report.get("completed_runs") == 760, "Expected the full 760-run formal population")
    require(report.get("unit") == "seed" and report.get("bootstrap_resamples") == 10000,
            "Unexpected statistical settings")
    require(report.get("no_confirmatory_or_noninferiority_claim") is True,
            "Descriptive statistical boundary missing")
    require(len(report.get("plans", [])) == 1, "Expected one formal plan; no pooling")
    ref = report["plans"][0]
    require(ref.get("plan_sha256") == EXPECTED_PLAN and ref.get("source_snapshot") == EXPECTED_SNAPSHOT,
            "Analysis does not identify the frozen formal-v1 source and plan")
    plan_path = (root / ref["path"]).resolve()
    require(root in plan_path.parents and sha(plan_path) == ref["sha256"], "Plan file/hash mismatch")
    plan = json.loads(plan_path.read_text())
    require(digest({k: v for k, v in plan.items() if k != "plan_sha256"}) == EXPECTED_PLAN,
            "Frozen plan content identity mismatch")
    matrix = plan["matrix"]
    require(matrix["stage"] == "validation" and matrix["experiment_id"] == "secon-formal-v1",
            "Development data cannot be used for formal figures")
    require(matrix["seeds"] == list(range(2027100, 2027120)), "Frozen seed population mismatch")
    specs = {r["run_key"]: r for r in plan["runs"]}
    require(len(specs) == 760, "Formal run keys are missing or duplicated")
    audit = ref["audit"]
    require(audit.get("status") == "complete" and audit.get("expected_runs") == 760
            and audit.get("plan_sha256") == EXPECTED_PLAN
            and not audit.get("failed") and not audit.get("missing"), "Formal audit is incomplete")
    completed = {r["run_key"]: r for r in audit["completed"]}
    require(len(audit["completed"]) == 760 and set(completed) == set(specs), "Audit population mismatch")
    tables, inputs = {}, {"analysis.json": {"sha256": sha(report_path), "bytes": report_path.stat().st_size},
                          ref["path"]: {"sha256": sha(plan_path), "bytes": plan_path.stat().st_size}}
    for name in TABLES:
        path = analysis_dir / (name + ".csv")
        expected = report["files"].get(path.name)
        require(expected and sha(path) == expected["sha256"] and path.stat().st_size == expected["bytes"],
                f"Missing or changed analyzed table: {path.name}")
        tables[name] = read_csv(path)
        inputs[path.name] = expected
        if name in report.get("tables", {}):
            require(len(tables[name]) == report["tables"][name], f"Row count mismatch: {name}")
    for name in ("planned_runs", "runs"):
        rows = tables[name]
        require(len(rows) == 760 and {r["run_key"] for r in rows} == set(specs), f"{name}: run coverage mismatch")
        for row in rows:
            spec = specs[row["run_key"]]
            require(row["plan_sha256"] == EXPECTED_PLAN
                    and (row["case_id"], row["arm_id"], int(row["seed"]))
                    == (spec["case_id"], spec["arm_id"], spec["seed"]), f"{name}: identity mismatch")
            require(row["attempt_path"] == completed[row["run_key"]]["attempt_path"], "Attempt mismatch")
            if name == "planned_runs":
                require(row["status"] == "completed", "A planned key has not completed")
            else:
                require(row["stage"] == "validation" and row["source_snapshot"] == EXPECTED_SNAPSHOT,
                        "Run source/stage differs from formal identity")
    for name in ("summary", "paired_effects"):
        for row in tables[name]:
            require(row["plan_sha256"] == EXPECTED_PLAN and row["stage"] == "validation"
                    and int(row["n"]) == 20, f"{name}: source/stage/sample-size mismatch")
    return report, plan, tables, inputs


class Figures:
    def __init__(self, plan, tables, out_dir):
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        self.plt = plt
        plt.rcParams.update(STYLE)
        self.plan, self.tables, self.out = plan, tables, out_dir
        self.cases = {c["id"]: c for c in plan["matrix"]["cases"]}
        self.arms = {a["id"]: a for a in plan["matrix"]["arms"]}
        self.summary, self.paired = {}, {}
        self.sources = defaultdict(list)
        self.notes = {}
        for row in tables["summary"]:
            key = (row["case_id"], row["arm_id"], row["metric"])
            require(key not in self.summary, f"Duplicate summary: {key}")
            self.summary[key] = row
        for row in tables["paired_effects"]:
            key = (row["case_id"], row["comparator_arm"], row["metric"])
            require(key not in self.paired, f"Duplicate paired effect: {key}")
            self.paired[key] = row

    def arm(self, case, protocol):
        ids = [a for a in self.cases[case]["arms"] if self.arms[a]["protocol"] == protocol]
        require(len(ids) == 1, f"Ambiguous model in case: {case}/{protocol}")
        return ids[0]

    def row(self, name, panel, case, protocol, metric):
        row = self.summary[(case, self.arm(case, protocol), metric)]
        self.sources[name].append({"panel": panel, "source_csv": "summary.csv", **row})
        return row

    def estimate(self, row, ratio=False, scale=1):
        keys = ("ratio_mean", "ratio_ci_low", "ratio_ci_high") if ratio else ("mean", "ci_low", "ci_high")
        values = [number(row[k]) for k in keys]
        if values[0] is None:
            require(int(row["undefined_n"]) > 0, "Undefined estimate without an undefined count")
            return None
        require(int(row["undefined_n"]) == 0 and all(v is not None for v in values), "Incomplete interval")
        require(values[1] <= values[2], "Inverted interval")
        if ratio:
            require(min(values) > 0, "Nonpositive airtime ratio")
        return tuple(v * scale for v in values)

    def point(self, ax, x, row, color, marker, ratio=False, scale=1, horizontal=False):
        value = self.estimate(row, ratio, scale)
        if value is None:
            if horizontal:
                ax.text(0.98, x, "undefined", transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=6)
            else:
                ax.text(x, 0.03, "undefined", transform=ax.get_xaxis_transform(), ha="center", rotation=90, fontsize=5.5)
            return math.nan
        mean, low, high = value
        # Draw independent interval endpoints; bootstrap intervals need not
        # contain the point estimate, so do not clamp negative error lengths.
        if horizontal:
            ax.plot([low, high], [x, x], color=color, lw=0.8)
            ax.plot([low, high], [x, x], "|", color=color, ms=4)
            ax.plot(mean, x, marker=marker, color=color, ls="none")
        else:
            ax.plot([x, x], [low, high], color=color, lw=0.8)
            ax.plot([x, x], [low, high], "_", color=color, ms=4)
            ax.plot(x, mean, marker=marker, color=color, ls="none")
        return mean

    def legend(self, fig, y=1.01):
        from matplotlib.lines import Line2D
        handles = [Line2D([], [], color=c, marker=m, ls="none", label=l)
                   for c, m, l in zip(COLORS, MARKERS, LABELS)]
        fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, y), ncol=4, frameon=False,
                   handletextpad=0.4, columnspacing=1.3)

    def finish(self, fig, name, note):
        self.notes[name] = note
        for ext in ("pdf", "svg", "png"):
            meta = {"Title": name, "Creator": "Reproducible publication plotting"}
            if ext == "pdf":
                meta["Author"] = ""
            fig.savefig(self.out / f"{name}.{ext}", dpi=220 if ext == "png" else 600,
                        bbox_inches="tight", pad_inches=0.035, metadata=meta)
        self.plt.close(fig)
        write_csv(self.out / f"{name}_source.csv", self.sources[name])

    def grouped(self, axes, name, cases, metrics, titles):
        for j, (metric, title) in enumerate(zip(metrics, titles)):
            ax = axes[j]
            for k, protocol in enumerate(PROTOCOLS):
                for x, case in enumerate(cases):
                    row = self.row(name, title, case, protocol, metric)
                    self.point(ax, x + (k - 1.5) * 0.16, row, COLORS[k], MARKERS[k],
                               scale=100 if metric.endswith("fraction") or "pdr" in metric else 1)
            ax.set_title(title, loc="left")
            ax.set_xticks(range(len(cases)), [c.replace("-", "\n", 1).replace("matched", "Matched").replace("default", "Default") for c in cases])
            ax.set_xlim(-0.5, len(cases) - 0.5)
            ax.grid(axis="y", color="#DDDDDD", linewidth=0.4)
            ax.set_axisbelow(True)
            if "pdr" in metric or metric.endswith("fraction"):
                ax.set_ylim(0, 102)
            else:
                ax.set_ylim(bottom=0)

    def main_results(self):
        name = "main_results"
        fig, axes = self.plt.subplots(1, 2, figsize=(7.12, 2.55))
        self.grouped(axes, name, MAIN, METRICS, ("a  Timely source ACK (%)", "b  Physical airtime (s)"))
        self.legend(fig)
        fig.subplots_adjust(left=.07, right=.99, top=.84, bottom=.22, wspace=.23)
        self.finish(fig, name, "All six main cases and four primary arms; equal-weight means of 20 seeds. Bars are existing descriptive, unadjusted 95% bootstrap intervals. No cases or adverse effects omitted.")

    def components(self):
        name = "component_effects"
        fig, axes = self.plt.subplots(1, 2, figsize=(7.12, 2.5), sharey=True)
        controls = ("noackcancel", "norepeat", "norecovery")
        labels = ("No ACK cancellation", "No repeat", "No recovery")
        ticks = []
        for s, case in enumerate(("S2-matched", "S3-matched")):
            for c, (control, label) in enumerate(zip(controls, labels)):
                y = 5 - (s * 3 + c)
                ticks.append((y, case[:2] + " · " + label))
                for j, metric in enumerate(METRICS):
                    row = self.paired[(case, "meshecho-cpr-" + control, metric)]
                    require(row["comparison_kind"] == "ablation", "A mixed-policy effect cannot be labeled a clean control")
                    require(row["focus_arm"] == "meshecho-cpr-matched", "Unexpected ablation focus")
                    self.sources[name].append({"panel": "ACK difference" if j == 0 else "Airtime ratio", "source_csv": "paired_effects.csv", **row})
                    self.point(axes[j], y, row, COLORS[0] if s == 0 else COLORS[2], "o" if s == 0 else "s",
                               ratio=j == 1, scale=100 if j == 0 else 1, horizontal=True)
        axes[0].axvline(0, color="#888888", lw=.65, ls="--")
        axes[1].axvline(1, color="#888888", lw=.65, ls="--")
        axes[1].set_xscale("log")
        axes[1].set_xticks([1.0, 1.2, 1.4, 1.6], ["1.0", "1.2", "1.4", "1.6"])
        axes[1].minorticks_off()
        axes[0].set(title="a  Full CPR − control", xlabel="Timely ACK difference (percentage points)")
        axes[1].set(title="b  Full CPR / control", xlabel="Geometric mean airtime ratio (log scale)")
        axes[0].set_yticks([x for x, _ in ticks], [x for _, x in ticks])
        for ax in axes:
            ax.set_ylim(-.6, 5.6)
            ax.axhline(2.5, color="#DDDDDD", lw=.6)
            ax.grid(axis="x", color="#DDDDDD", linewidth=.4)
        fig.subplots_adjust(left=.24, right=.98, bottom=.22, top=.86, wspace=.24)
        self.finish(fig, name, "Six clean component effects, S2/S3 matched. Positive ACK differences favor full CPR; airtime ratios below one indicate less airtime. Existing paired estimates/intervals only; negative, null, adverse and undefined effects remain visible.")

    def check_axis(self, cases, variable):
        base = self.cases[cases[0]]
        for case in cases[1:]:
            cur = self.cases[case]
            ignored = {"key", "rate_per_min"} if variable == "load" else {"key"}
            require({k: v for k, v in base["case"].items() if k not in ignored}
                    == {k: v for k, v in cur["case"].items() if k not in ignored}, "Confounded robustness cases")
            require(base["environment"] == cur["environment"], "Environment differs along curve")
            if variable == "load":
                require(base["deadline_s"] == cur["deadline_s"] and base["configuration"] == cur["configuration"],
                        "Deadline/regime differs along load curve")
        for protocol in PROTOCOLS:
            signatures = []
            for case in cases:
                rows = [r for r in self.tables["runs"] if r["case_id"] == case and r["arm_id"] == self.arm(case, protocol)]
                require(len(rows) == 20, "Incomplete effective-parameter population")
                sig = {}
                for row in rows:
                    params = json.loads(row["resolved_protocol_parameters"])
                    if variable == "deadline":
                        params.pop("app_deadline_s", None)
                    sig[int(row["seed"])] = params
                signatures.append(sig)
            require(all(s == signatures[0] for s in signatures), "Effective protocol parameters differ along curve")

    def robustness(self):
        name = "robustness"
        deadline = ("R-deadline-10-S2-matched", "S2-matched", "R-deadline-60-S2-matched")
        load = ("S1-matched", "S3-matched")
        self.check_axis(deadline, "deadline")
        self.check_axis(load, "load")
        fig, axes = self.plt.subplots(2, 2, figsize=(7.12, 3.35))
        for col, (cases, xs, title, xlabel) in enumerate(((deadline, (10, 30, 60), "S2 matched: deadline", "Deadline and drain (s)"),
                                                       (load, (8, 40), "Matched: two load points", "Offered flows/min (whole network)"))):
            for j, metric in enumerate(METRICS):
                ax = axes[j, col]
                for k, protocol in enumerate(PROTOCOLS):
                    means = []
                    for x, case in zip(xs, cases):
                        row = self.row(name, f"{title}/{metric}", case, protocol, metric)
                        means.append(self.point(ax, x, row, COLORS[k], MARKERS[k], scale=100 if j == 0 else 1))
                    ax.plot(xs, means, color=COLORS[k], lw=.7, alpha=.8)
                ax.set_xticks(xs)
                ax.set_xlim(min(xs) - 3, max(xs) + 3)
                ax.grid(axis="y", color="#DDDDDD", linewidth=.4)
                ax.set_ylabel("Timely ACK (%)" if j == 0 else "Physical airtime (s)")
                ax.set_ylim(0, 102) if j == 0 else ax.set_ylim(bottom=0)
                if j == 0:
                    ax.set_title(("a  " if col == 0 else "b  ") + title, loc="left")
                else:
                    ax.set_xlabel(xlabel)
        self.legend(fig, 1.025)
        fig.subplots_adjust(left=.08, right=.99, top=.84, bottom=.14, hspace=.24, wspace=.25)
        self.finish(fig, name, "Predeclared deadline10/30/60 and two-point load8/40 comparisons. Lines join observations only; no fitted response or intermediate measurements. Deadline changes both application horizon and drain; traffic generation remains240s. Existing all-seed intervals; identical effective parameters checked except the explicit deadline field.")

    def latency_cost(self):
        name = "latency_cost"
        cases = ("S1-matched", "S2-matched", "S3-matched")
        fig, axes = self.plt.subplots(1, 3, figsize=(7.12, 2.65))
        self.grouped(axes[:2], name, cases, ("timely_ack_latency_p95_s", "unfinished_ack_fraction"),
                     ("a  Timely ACK latency p95 (s)", "b  Unfinished ACK flows (%)"))
        stages = ("initial", "repeat", "recovery")
        stage_colors = ("#AFC6D3", "#5987A4", "#254B68")
        for x, case in enumerate(cases):
            arm = self.arm(case, "meshecho-cpr")
            cells = [r for r in self.tables["cost_summary"] if r["case_id"] == case and r["arm_id"] == arm]
            require(all(int(r["seed_count"]) == 20 and r["stage"] in stages for r in cells), "Unexpected CPR cost cell")
            total = sum(float(r["mean_airtime_s"]) for r in cells)
            ref = self.summary[(case, arm, "tx_ledger_airtime_s")]
            require(abs(total - float(ref["mean"])) < 1e-7, "Cost components do not reconstruct total")
            bottom = 0
            for stage, color in zip(stages, stage_colors):
                for ack in (False, True):
                    selected = [r for r in cells if r["stage"] == stage and (r["packet_kind"] == "ACK") == ack]
                    require(all(r["packet_kind"] in {"ACK", "DATA", "FLOOD"} for r in selected), "Unexpected CPR packet kind")
                    value = sum(float(r["mean_airtime_s"]) for r in selected)
                    axes[2].bar(x, value, bottom=bottom, width=.55, color=color, edgecolor="white", lw=.35,
                                hatch="///" if ack else None)
                    for row in selected:
                        self.sources[name].append({"panel": "CPR packet/stage airtime", "source_csv": "cost_summary.csv", **row})
                    bottom += value
        axes[2].set(title="c  CPR airtime by stage (s)", xticks=range(3), xticklabels=("S1", "S2", "S3"))
        axes[2].set_ylim(bottom=0)
        from matplotlib.patches import Patch
        handles = [Patch(facecolor=c, label=s.capitalize()) for s, c in zip(stages, stage_colors)]
        handles.append(Patch(facecolor="white", edgecolor="#666666", hatch="///", label="ACK portion"))
        axes[2].legend(handles=handles, loc="upper left", fontsize=5.6, frameon=False)
        self.legend(fig)
        fig.subplots_adjust(left=.055, right=.99, top=.82, bottom=.23, wspace=.35)
        self.finish(fig, name, "Matched cases. Latency is the mean of each seed's timely-success p95, with existing descriptive95% intervals; unfinished fraction uses every scheduled flow. Undefined success quantiles remain labeled. CPR full physical airtime decomposes existing packet/stage means; hatched segments are ACKs. Cost decomposition has no invented component intervals.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--analysis-dir", type=Path, default=Path("results/secon2027/analysis/formal-v1"))
    parser.add_argument("--out-dir", type=Path, default=Path("paper/secon2027/figures/formal-v1"))
    parser.add_argument("--validate-only", action="store_true", help="Check full formal identities and tables; write nothing")
    args = parser.parse_args()
    root = args.root.resolve()
    analysis = (root / args.analysis_dir).resolve()
    output = (root / args.out_dir).resolve()
    require(root in analysis.parents and root in output.parents, "Inputs/outputs must be inside the repository")
    report, plan, tables, inputs = validate(analysis, root)
    if args.validate_only:
        print(json.dumps({"status": "validated", "runs": 760, "plan_sha256": EXPECTED_PLAN}))
        return 0
    output.mkdir(parents=True, exist_ok=False)
    plots = Figures(plan, tables, output)
    plots.main_results()
    plots.components()
    plots.robustness()
    plots.latency_cost()
    import matplotlib
    import numpy
    manifest = {"schema": "secon2027-paper-figures-v1", "status": "complete",
                "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "script_sha256": sha(Path(__file__)), "analysis_directory": str(analysis.relative_to(root)),
                "analysis_source_sha256": report["analysis_source_sha256"], "plan_sha256": EXPECTED_PLAN,
                "source_snapshot": EXPECTED_SNAPSHOT, "complete_runs": 760, "seeds": plan["matrix"]["seeds"],
                "statistics": "Existing table means and descriptive unadjusted95% intervals; no re-bootstrap or seed selection",
                "dimensions": "7.12 inch wide vector PDF/SVG;220dpi PNG previews;TrueType PDF fonts;editable SVG text",
                "inputs": inputs, "figure_notes": plots.notes, "retained_failure_records": report.get("failures", []),
                "environment": {"python": platform.python_version(), "matplotlib": matplotlib.__version__, "numpy": numpy.__version__},
                "outputs": {p.name: {"sha256": sha(p), "bytes": p.stat().st_size} for p in sorted(output.iterdir()) if p.is_file()}}
    with (output / "figure_manifest.json").open("x") as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": "complete", "figures": list(plots.notes), "out_dir": str(output.relative_to(root))}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, FileNotFoundError) as error:
        print(f"Publication figures refused: {error}", file=sys.stderr)
        raise SystemExit(2)
