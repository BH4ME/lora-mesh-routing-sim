# Smart-CALM Simulation Versions

This file tracks simulation baselines before further optimization.

## `smart-calm-sim-v1.1`

- Status: working version on branch `codex/smart-calm-sim-optimization`.
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

- Treat v1.1 as the active optimization base for the next round.
- The conference explanation should emphasize recovery discipline: Smart-CALM
  keeps reliability high by retrying along known paths first, and only spends
  fallback flooding when path knowledge is unavailable.
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
