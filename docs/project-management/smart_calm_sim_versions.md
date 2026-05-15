# Smart-CALM Simulation Versions

This file tracks simulation baselines before further optimization.

## `smart-calm-sim-v1.1`

- Status: superseded baseline on branch `codex/smart-calm-sim-optimization`.
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

- Treat v1.1 as the historical optimization base for v1.1.1.
- The conference explanation should emphasize recovery discipline: Smart-CALM
  keeps reliability high by retrying along known paths first, and only spends
  fallback flooding when path knowledge is unavailable.
- The v1.1 comparison charts were generated from v1.1 result CSVs before the
  v1.1.1 timeout-rescue-radius optimization.

## `smart-calm-sim-v1.1.1`

- Status: accepted optimization candidate after v1.1.
- Core change: timeout recovery now uses the active Smart-CALM profile's
  fallback radius instead of forcing at least two fallback hops. Route-miss
  recovery still defaults to the normal full-radius recovery so first-contact
  reachability is not weakened.
- Optional experiment knob: `--smart-route-miss-fallback-ttl`; default `0`
  keeps full route-miss recovery.
- Decision: use this as the next simulation baseline because it lowers airtime
  and collision failures without materially changing the reliability story.

Key v1.1.1 result files:

- `results/smart_calm_v1_1_1_50n_mixed.csv`
- `results/smart_calm_v1_1_1_50n_mixed_shadow6.csv`
- `results/smart_calm_v1_1_1_50n_mixed_rate10.csv`
- `results/smart_calm_v1_1_1_50n_mixed_summary.txt`
- `results/smart_calm_v1_1_1_50n_mixed_shadow6_summary.txt`
- `results/smart_calm_v1_1_1_50n_mixed_rate10_summary.txt`

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
  retry budgets are archived under
  `archive/experiments/smart_calm_v1_1_1_candidates/`.
- The current comparison charts in `results/figures/` and
  `docs/results/three_protocol_comparison.md` are generated from v1.1.1 result
  CSVs.

## `smart-calm-sim-v1.1.2`

- Status: current optimization candidate on branch `version/v1.1.2`.
- Core change: timeout rescue is now congestion-aware. When the active profile
  is already the rescue profile and the recent channel pressure is clearly
  high, Smart-CALM caps timeout fallback TTL to avoid over-spreading rescue
  floods.
- Design intent: keep the reliability of the rescue path, but stop it from
  escalating airtime and collision pressure in already congested conditions.
- Current evidence:
  - `rate14` improves unicast PDR from about `0.884` to `0.904`, while total
    airtime drops from about `1740 s` to `1626 s`, collisions drop from about
    `168778` to `157536`, and fallback forwards drop from about `799` to `357`.
  - `shadow8` stays effectively unchanged.
  - `sparse4k` shows a small PDR decrease of about `0.23%`, with a slight
    airtime increase, so this version is still the active tuning candidate
    rather than the final accepted baseline.
- Key result files:
  - `results/v1_1_2_rate14_smart.csv`
  - `results/v1_1_2_shadow8_smart.csv`
  - `results/v1_1_2_sparse4k_smart.csv`
- Notes:
  - Keep this candidate as the next step for the conference narrative, but do
    not relabel it as the final baseline until the sparse-load regression is
    either explained or eliminated.
  - The intended conference framing is "congestion-aware rescue throttling,"
    not "more aggressive flooding."

## `smart-calm-sim-v1.1.3`

- Status: literature-backed control candidate on branch `version/v1.1.3`.
- Core change: replaces instant fallback thresholds with FBC, a fallback budget
  controller using smoothed pressure, fast guard triggers, and hysteresis.
- Literature basis:
  - RPL metric guidance motivates smoothed dynamic metrics and multiple
    thresholds.
  - MRHOF motivates hysteresis to avoid control churn.
  - Trickle and broadcast-storm work motivate suppressing redundant rescue
    transmissions under stable or congested state.
  - ETX motivates reliability/cost-aware forwarding decisions instead of pure
    hop-count behavior.
- Current evidence versus v1.1.2 on `rate14`:
  - PDR stays about `0.904`.
  - Collision failures are slightly lower, about `157335` versus `157536`.
  - Airtime is slightly higher, about `1627 s` versus `1626 s`.
  - Fallback forwards are slightly higher, about `361` versus `357`.
- Decision: keep v1.1.3 as the more defensible algorithmic branch, while
  retaining v1.1.2 as the slightly stronger fallback-count metric point.

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
