# Smart-CALM Simulation Versions

This file tracks simulation baselines before further optimization.

The repository-wide release version is tracked separately in `VERSION`. The
current repository release is `2.1.13`; the firmware prototype remains
`2.1.2`; simulation CSV baselines keep
their existing `smart-calm-sim-v2` identity so historical comparisons remain
stable.

## `smart-calm-sim-v2.1.13`

- Status: fairness-focused manuscript revision on 2026-09-04.
- Reframe the frozen repeated-pair matrix as a contention-oriented operating
  point rather than a neutral multi-hop benchmark.
- Add an explicit fairness judgment separating shared-harness construction,
  matched-TTL sensitivity, random-pair external validity, and controlled
  route-conflict mechanism evidence.
- Keep historical CSVs unchanged and retain the firmware prototype at
  `meshecho-firmware-v2.1.2`.

## `smart-calm-sim-v2.1.12`

- Status: recovery-budget sensitivity revision on 2026-09-04.
- Added the explicit `--calm-disable-route-miss-fallback` control and the
  paired 20-seed `tools/run_recovery_budget_audit.py` experiment.
- Added `--meshcore-route-ttl-s` and the paired 20-seed
  `tools/run_route_ttl_audit.py` experiment. Matching MeshCore-like from
  `300 s` to `600 s` raised ACK PDR from `0.381` to `0.519`.
- In the current main mixed-scene replay, disabling route-miss fallback changed
  CALM ACK PDR from `0.728` to `0.719` and destination PDR from `0.766` to
  `0.744`, while reducing airtime from `847.3 s` to `831.4 s`.
- The paired ACK-PDR difference was `+0.009 +/- 0.018`, so the manuscript
  reports this as a small, statistically unresolved recovery effect rather
  than as a confidence-only gain.
- The frozen 3 km matrix and firmware prototype remain unchanged.

## `smart-calm-sim-v2.1.11`

- Status: fairness diagnostics and budget-matched paper revision on
  2026-09-04.
- Added route-discovery attempt/success counters and RREP/RREQ transmission
  diagnostics to the simulator and fairness probe.
- Added connected-pair low-load and single-flow stress matrices. These
  demonstrate that graph-level pair connectivity does not guarantee operational
  route discovery under a broadcast-collision model.
- Added a zero-timeout-retry probe mode and revised the ICCT manuscript so
  confidence-only claims are based on one-shot paired results rather than on
  Smart-CALM's extra recovery budget.
- The frozen 3 km matrix remains unchanged. The firmware prototype remains
  `meshecho-firmware-v2.1.2`.

## `smart-calm-sim-v2.1.10`

- Status: random-pair fairness evidence integrated into the ICCT manuscript on
  2026-09-04.
- Added the ten-seed non-saturated multi-hop probe to the paper's evidence
  chain. The probe removes fixed-pair reuse and uses independent
  channel-reception randomness.
- The probe preserves MeshEcho's airtime advantage over source-route caching
  but does not establish a general ACK-PDR advantage. Full Smart-CALM also
  does not outperform its fixed-profile control in this setting.
- The frozen 3 km matrix remains unchanged and is still labeled as a
  contention-oriented, high-PRR case. The firmware prototype remains
  `meshecho-firmware-v2.1.2`.

## `smart-calm-sim-v2.1.9`

- Status: fairness-aware manuscript and reproducibility refinement on
  2026-09-04.
- Added the opt-in `--independent-rng-streams` simulator mode and documented
  its scope: it separates channel-reception draws from protocol jitter and
  learning exploration, but does not create event-by-event common random
  numbers when protocols generate different transmission counts.
- The ICCT manuscript now states that the frozen matrix is a contention-oriented
  high-PRR case, discloses fixed-pair and recovery-budget effects, and records
  the fixed-payload limitation for source-route header airtime.
- The frozen result files are retained; no post-hoc harder parameter sweep is
  substituted into the published tables.
- The firmware prototype remains `meshecho-firmware-v2.1.2`.

## `smart-calm-sim-v2.1.8`

- Status: final fairness-traceable ICCT paper package and no-fallback fix on
  2026-09-04.
- Evidence: the revised
  `paper/icct2026/icct2026_lora_mesh_preliminary.tex`,
  `docs/results/meshecho_fairness_audit.md`, and the regression test in
  `tests/test_calm_protocol.py`.
- The frozen three-protocol main matrix is retained. Smart-CALM ablation rows
  generated before the no-fallback fix remain historical and require a fresh
  rerun before being used as current quantitative evidence.
- The firmware prototype remains `meshecho-firmware-v2.1.2`.

## `smart-calm-sim-v2.1.7`

- Status: fairness-bounded paper revision and reproducibility correction on
  2026-09-04.
- Evidence: the revised
  `paper/icct2026/icct2026_lora_mesh_preliminary.tex`,
  `docs/results/meshecho_fairness_audit.md`, and the corrected shadowing-model
  terminology documentation.
- The frozen simulation CSVs are retained. This release does not silently
  replace the 3000 m matrix with the harder diagnostic probes.
- The firmware prototype remains `meshecho-firmware-v2.1.2`.

## `smart-calm-sim-v2.1.6`

- Status: fairness-aware ICCT manuscript package and release traceability on
  2026-09-04.
- Evidence: the revised
  `paper/icct2026/icct2026_lora_mesh_preliminary.tex` and
  `docs/results/meshecho_fairness_audit.md`.
- The frozen simulation CSVs are retained; this release does not silently
  replace the 3000 m matrix with the harder diagnostic probes.
- The firmware prototype remains `meshecho-firmware-v2.1.2`.

## `smart-calm-sim-v2.1.5`

- Status: fairness audit and ICCT manuscript revision on 2026-09-04.
- Evidence: `docs/results/meshecho_fairness_audit.md` and the revised
  `paper/icct2026/icct2026_lora_mesh_preliminary.tex`.
- Finding: the common seed/topology/traffic harness is shared, but the current
  matrix is link-quality saturated, almost entirely one-hop, and not fully
  budget-matched at the recovery-mechanism level.
- The firmware prototype remains `meshecho-firmware-v2.1.2`.

## `smart-calm-sim-v2.1.4`

- Status: controlled route-conflict experiment added on 2026-09-03.
- Evidence: `results/meshecho_route_conflict.csv` and
  `docs/results/meshecho_route_conflict.md`.
- Scope: isolates confidence-based candidate admission from online learning and
  fallback recovery; it does not replace the random-topology ICC matrix.

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
