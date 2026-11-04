# Formal manuscript figure contract

Backend: Python 3 / Matplotlib. These are quantitative grids at 7.12-inch
nominal width for a two-column IEEE manuscript, with editable SVG text,
embedded TrueType PDF text, and PNG previews from the same backend.

The scientific question is whether the fixed CPR policy trades timely
confirmation against physical airtime differently across the complete
prespecified settings. No direction of benefit is assumed. S3 and any
negative, null, or undefined effect remain visible.

| Output | Evidence role | Content and interpretation |
| --- | --- | --- |
| `main_results` | Whole-policy comparison | All six S1/S2/S3 default/matched cases, four primary models, timely ACK and total physical airtime. |
| `component_effects` | Mechanism comparison | Three clean controls in S2/S3 matched; full-CPR minus-control ACK percentage-point difference and full/control geometric airtime ratio. |
| `robustness` | Finite sensitivity | Deadline 10/30/60 s in S2 matched; two observed load points 8/40 flows/min in matched fault-free settings. Lines only join observations. |
| `latency_cost` | Outcome/cost context | Mean of seed-level timely-success p95 together with mean unfinished fraction; CPR airtime partitioned by source stage with hatched ACK portions. |

Every point/interval is read from the existing complete analyzer tables.
The script does not resample, simulate, select seeds, alter statistical
rules, or replace an undefined value with zero. The cost panel adds existing
packet/stage means and checks that they reconstruct the complete mean
airtime. It does not invent component confidence intervals. The deadline
scan changes application deadline **and** drain duration; generation lasts
240 s in every case. Two load points are not a fitted response curve.

The entry point is `build_figures.py`. After the complete formal analysis
exists, run from the repository root:

```bash
/usr/bin/python3 paper/secon2027/build_figures.py --validate-only
/usr/bin/python3 paper/secon2027/build_figures.py
```

The default input is `results/secon2027/analysis/formal-v1`; the default
output is an exclusive new directory `paper/secon2027/figures/formal-v1`.
Use a new `--out-dir` for a later rendering revision, preserving the old one.
No output is written by `--validate-only`. It requires the exact frozen
formal-v1 plan/source, 760 complete unique run keys, all 20 registered
seeds, a complete audit, and matching analyzed-table hashes. A development
analysis is rejected. This is publication-stage verification of the saved
audit and tables, not a replacement raw-event audit.

Each figure exports PDF/SVG/PNG and a `_source.csv` containing the exact
selected rows and panel identity. `figure_manifest.json` binds the script,
analysis report, input tables, plan/source, library versions, output hashes,
statistical limitations, and retained failure records. Its `complete` status
means all four figure artifacts were produced from the verified complete
population; visual/font/page acceptance still requires review of the actual
outputs and compiled manuscript.

Preflight on 2026-11-04: Python syntax and CLI help passed. The read-only
guard explicitly rejected the real 72-run development analysis with exit 2
and no output. No formal plot or manuscript result was generated during
preflight. Wait for the execution task's full760 audit/analysis signal.

## Completed formal rendering

The complete760 analysis passed the strict publication guard. All four
figures were generated in `figures/formal-v1`; visual review found crowded
minor tick labels on the component ratio axis. `figures/formal-v2` preserves
the identical evidence and scientific values with explicit1.0/1.2/1.4/1.6
log-axis major ticks and disabled minor labels. Its manifest binds the
revised script and16outputs. The manuscript uses formal-v2. All four
figures were visually inspected standalone and within the9-page PDF.
No statistical estimates or scientific settings changed.
