# Smart-CALM Simulation Versions

This file tracks simulation baselines before further optimization.

The repository-wide release version is tracked separately in `VERSION`. The
current repository release is `2.1.3`; the firmware prototype remains
`2.1.2`; simulation CSV baselines keep
their existing `smart-calm-sim-v2` identity so historical comparisons remain
stable.

## `smart-calm-sim-v2.1.3`

- Status: ICC result freeze and full-paper package on 2026-09-02.
- Evidence: four correct-prefix 20-seed ICC scenarios under
  `results/meshecho_v2_1_2_50n_*`.
- Paper: `paper/full2026/smart_calm_full_paper.tex` uses this refreshed matrix.
- This repository release adds results and paper artifacts; it does not change
  firmware behavior, so the firmware version remains `2.1.2`.

## `smart-calm-sim-v2.1.2`

- Status: CSV normalization and release refresh on 2026-09-02.
- Core change: the simulator and analysis scripts now emit LF-only CSVs, so
  generated experiment files produce stable diffs across platforms.
- Keep the frozen ICC comparison line and the versioned Smart-CALM result
  prefixes unchanged; this release is a packaging and reproducibility refresh
  rather than a new algorithm baseline.

## `smart-calm-sim-v2.1.1`

- Status: ICC comparison freeze on 2026-09-02.
- Core change: the repository release metadata is aligned with the verified
  ICC 2027 matrix and the new `docs/results/icc2027_comparison.md` summary.
- Keep the `meshecho_v2_1_0_icc_50n_*` CSV prefix for the frozen ICC result
  line so the raw experiment files remain stable even though the repository
  release number advanced.

## `smart-calm-sim-v1.1`

- Status: active paper baseline; later v2 work remains separate.
- Baseline ancestry: starts from `smart-calm-sim-v1.0` and keeps the v1.0 CSVs
  untouched for comparison.
- Core change: timeout recovery now prefers a cached source-route DATA retry
  before using fallback flooding. A flow that already used fallback is not
  retried again by timeout unless `--smart-retry-after-fallback` is explicitly
  set.
- Default recovery budget: `--smart-max-timeout-retries 2`, where the first
  successful recovery opportunity is usually a directed cached-path retry, not
  an immediate flood.

Key v1.1 result files:

- `results/smart_calm_v1_1_50n_mixed.csv`
- `results/smart_calm_v1_1_50n_mixed_shadow6.csv`
- `results/smart_calm_v1_1_50n_mixed_rate10.csv`
- `results/smart_calm_v1_1_50n_mixed_summary.txt`
- `results/smart_calm_v1_1_50n_mixed_shadow6_summary.txt`
- `results/smart_calm_v1_1_50n_mixed_rate10_summary.txt`

Twenty-seed Smart-CALM deltas versus v1.0:

| Scenario | PDR delta | Airtime delta | Collision delta | Fallback delta |
| --- | ---: | ---: | ---: | ---: |
| Mixed traffic | `-0.03%` | `-4.21%` | `-4.71%` | `-29.85%` |
| High shadowing | `+0.03%` | `-4.20%` | `-4.86%` | `-34.61%` |
| High offered load | `+1.44%` | `-6.39%` | `-6.25%` | `-33.34%` |

Notes:

- Treat v1.1 as the active ICNP paper comparison baseline.
- The conference explanation should emphasize recovery discipline: Smart-CALM
  keeps reliability high by retrying along known paths first, and only spends
  fallback flooding when path knowledge is unavailable.
- The v1.1 comparison charts are generated from v1.1 result CSVs. The later v2
  timeout-rescue-radius optimization is preserved separately for a later
  release.

## `smart-calm-sim-v2`

- Status: accepted optimization candidate after v1.1.
- Core change: timeout recovery now uses the active Smart-CALM profile's
  fallback radius instead of forcing at least two fallback hops. Route-miss
  recovery still defaults to the normal full-radius recovery so first-contact
  reachability is not weakened.
- Optional experiment knob: `--smart-route-miss-fallback-ttl`; default `0`
  keeps full route-miss recovery.
- Decision: publish this as the v2 simulation baseline because it lowers airtime
  and collision failures without materially changing the reliability story.

Key v2 result files:

- `results/smart_calm_v2_50n_mixed.csv`
- `results/smart_calm_v2_50n_mixed_shadow6.csv`
- `results/smart_calm_v2_50n_mixed_rate10.csv`
- `results/smart_calm_v2_50n_mixed_summary.txt`
- `results/smart_calm_v2_50n_mixed_shadow6_summary.txt`
- `results/smart_calm_v2_50n_mixed_rate10_summary.txt`

Twenty-seed Smart-CALM deltas versus v1.1:

| Scenario | PDR delta | Airtime delta | Collision delta | Fallback delta |
| --- | ---: | ---: | ---: | ---: |
| Mixed traffic | `+0.02%` | `-7.60%` | `-7.62%` | `-71.80%` |
| High shadowing | `+0.61%` | `-6.51%` | `-6.51%` | `-71.84%` |
| High offered load | `-0.51%` | `-6.57%` | `-6.79%` | `-47.24%` |

Notes:

- The accepted explanation is "targeted timeout-rescue radius control", not
  "global flooding reduction". Route discovery failures remain conservative;
  only late timeout rescue follows the selected online profile.
- Rejected candidate runs for tighter route-miss fallback and stricter timeout
  retry budgets should remain separate from the published v2 result files.
- The current comparison charts in `results/figures/` and
  `docs/results/three_protocol_comparison.md` are generated from v1.1 result
  CSVs.

## Rejected candidate: `smart-calm-sim-v1.2`

- Archive: `archive/experiments/smart_calm_v1_2_rejected/`
- Idea tested: allow route-request packets to carry the first unicast
  application payload and limit route-miss fallback scope.
- Outcome: PDR improved slightly, but airtime increased by `64.74%` to
  `87.29%` and collision failures increased by `21.39%` to `31.53%` versus
  accepted v1.1 across the formal scenarios.
- Decision: do not use this as the meeting version. It is preserved only as a
  rejected reliability probe because it weakens the main optimization claim:
  maintain PDR while lowering collision pressure and channel occupancy.

## `smart-calm-sim-v1.0`

- Git tag: `smart-calm-sim-v1.0`
- Baseline commit: `c7626c7 Add Smart-CALM simulation workflow`
- Optimization branch: `codex/smart-calm-sim-optimization`
- Purpose: freeze the current Smart-CALM simulator, trained prior, and comparison
  CSVs before the next optimization round.

Key simulation files:

- `lora_mesh_sim.py`
- `tools/train_smart_calm_prior.py`
- `tools/build_three_protocol_comparison.py`
- `results/smart_calm_50n_mixed.csv`
- `results/smart_calm_50n_mixed_shadow6.csv`
- `results/smart_calm_50n_mixed_rate10.csv`
- `results/smart_calm_50n_unicast_pairs.csv`

Key comparison docs:

- `docs/results/three_protocol_comparison.md`
- `docs/results/calm_experiment_notes.md`

Notes:

- Treat this as the reference point for future PDR, airtime, collision, and
  delay comparisons.
- Continue future Smart-CALM simulator optimization from
  `codex/smart-calm-sim-optimization`, currently aligned with commit `614d8dd`.
- Do not overwrite this baseline's CSVs when testing new ideas; write new result
  files or tag a new version once the improvement is accepted.
- New optimization runs should either update this file with a new version entry
  or create a new tag, for example `smart-calm-sim-v1.1`.
