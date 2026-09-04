# Findings

## Current Evidence

- The original 50-node, 3000 m, SF9 matrix is link-quality saturated: direct
  PRR is essentially one and almost all cached routes are one hop.
- Fixed repeated source-destination pairs favor route-cache reuse, so that
  matrix is useful as a cache-efficiency/contestion case, not a neutral
  multi-hop benchmark.
- The ten-seed random-pair probe uses an 18 km square, SF7, random pairs,
  mixed traffic at 4 flows/min, and independent channel-reception randomness.
- In that probe, MeshEcho/CALM has ACK PDR `0.413` and airtime `97.5 s`, while
  source-route caching has ACK PDR `0.456` and airtime `139.5 s`.
- The controlled route-conflict experiment supports a narrower mechanism claim:
  confidence helps when the shorter route has a materially weaker hop, but not
  under null, moderate, or reverse controls.
- Smart-CALM has extra timeout retry/fallback behavior, so its gains cannot be
  attributed to confidence ranking alone.
- The connected-pair diagnostic shows that a shared graph-level path does not
  guarantee successful route discovery under broadcast contention. In the
  50-node/15 km/0.5 flows-min case, MeshCore route-discovery success was only
  `0.063`; a 20-seed single-flow check was still only `0.050`.
- The fairness probe now reports route-discovery success and RREP/RREQ
  transmission ratios, and supports `--smart-max-timeout-retries 0` for a
  one-shot budget-matched comparison.
- `--independent-rng-streams` is now passed through `run_one()` and the ICC
  script defaults to it for fresh matrices. It reduces random-stream coupling,
  but is not event-by-event common random numbers.
- An exploratory, unregistered area scan found that 12 km and 14 km settings
  produce non-degenerate direct-link PRR distributions, but random-pair
  traffic still yields only about 6% and 4% MeshCore multi-hop cached routes,
  respectively. These scans are calibration evidence only and are not used as
  headline paper results.
- A 12 km connected-pair run makes the multi-hop fraction clearer, but MeshCore
  route-discovery success falls to about 0.21 while MeshEcho/Smart-CALM remains
  above about 0.61. This confirms that pair selection and route discovery must
  be treated as separate fairness dimensions; the result is not suitable as a
  neutral headline comparison.
- The connected-pair stress runs also contain a route-reply timing asymmetry:
  MeshCore-like replies immediately when the destination first receives an
  RREQ, while MeshEcho waits for candidate collection before sending its RREP.
  This is useful to disclose because it can affect route-discovery success in
  collision-limited floods.

## Paper Positioning

The defensible conclusion is a preliminary reliability-airtime tradeoff under
explicitly stated workload and recovery budgets. The paper must not claim
universal superiority, calibrated deployment performance, or an average
confidence-ranking benefit in arbitrary topologies.

## Publish Scope Candidate

Related files include the ICCT LaTeX/PDF, version metadata, fairness reports,
the random-pair probe script and CSV, the simulator RNG fix, its regression
test, and the ICC experiment documentation. Generated auxiliary LaTeX files,
local sessions, caches, and unrelated deliverables should remain unstaged.

## Release State

- The prior fairness revision was repository version `2.1.11`; the current
  recovery-budget revision is repository version `2.1.12`;
  firmware identity remains `meshecho-firmware-v2.1.2`.
- The paper source and release metadata are already updated in the worktree.
- The PDF has now been compiled and visually inspected successfully. It is
  8 pages, PDF 1.5, with no unresolved reference warnings.
- Final validation passed: 45 Python tests, Python compilation, shell syntax,
  and `git diff --check`.
- The remaining gates are selective staging, commit/push, and remote PR
  verification.

## Verification Checkpoint - 2026-09-04

- Final root PDF SHA-256:
  `b822940c36b13a084538691b526a2b72c0d32463c67ff4772e76937fa4ab9b9a`.
- The root PDF is byte-identical to the `build-2_1_11` output.
- The existing draft PR is still titled for `2.1.9`; after pushing the
  `2.1.11` commit, update its title and body.
- Do not stage generated LaTeX auxiliaries, rendered page images, `.venv-fig`,
  `.playwright-cli`, `tmp`, course artifacts, or unrelated documents.

## 2.1.12 Audit Questions

- Formalize the `calm-mesh` route-miss fallback setting so the recovery
  contribution can be measured without temporary monkey-patching.
- Use paired seeds and the same main-scene topology/traffic to estimate the
  effect of disabling only route-miss fallback.
- Keep the result separate from the confidence-only route-conflict experiment:
  fallback is a recovery mechanism, not evidence of confidence ranking.
- Keep the original frozen matrix unchanged; the new audit is a sensitivity
  result for the 2.1.12 revision.

## 2.1.12 Audit Result

- The recovery-budget script now reports route-discovery success rate as
  `route_discovery_successes / route_discovery_attempts` and includes the
  attempt count in the Markdown table.
- In the paired 20-seed main-scene replay, mean route-discovery success rates
  were `0.834` for MeshCore-like, `0.798` for CALM with route-miss fallback,
  and `0.805` for CALM without route-miss fallback.
- The corrected rate metric does not change the PDR or airtime results:
  fallback versus no fallback is `+0.009 +/- 0.018` ACK PDR and
  `+0.023 +/- 0.023` destination PDR, with `+15.9 s` airtime.
- This supports the narrower conclusion that MeshEcho was not favored by an
  easier route-discovery process in this replay, while the comparison remains
  a sensitivity audit rather than a fully budget-matched baseline study.

## 2.1.12 Route-TTL Audit Result

- The native main matrix uses a `300 s` MeshCore-like route-cache TTL and a
  `600 s` CALM/MeshEcho TTL. Because the workload reuses eight fixed pairs,
  this is a real favorable bias toward MeshEcho.
- After matching MeshCore-like to `600 s`, its ACK PDR rose from `0.381` to
  `0.519`, destination PDR from `0.652` to `0.722`, and airtime fell from
  `970.9 s` to `905.5 s`.
- The paired TTL effect was `+0.138 +/- 0.031` ACK PDR and
  `-65.4 +/- 14.1 s` airtime. The remaining matched-TTL MeshEcho difference
  was `+0.209 +/- 0.071` ACK PDR and `-58.2 +/- 19.2 s` airtime.
- Therefore the native `+0.347` ACK-PDR gap overstates the more comparable
  matched-TTL bundle difference by `0.138` in this replay. The current paper
  now reports the matched audit and does not present the native gap as a
  strategy-only effect.

## 2.1.12 Final Verification

- The updated manuscript compiles to 9 pages after adding the TTL fairness
  audit. The root PDF is PDF 1.5 with SHA-256
  `97a5fc593a60ea1295697d0e90df09940ade0c158c54f290c611308598b70920`.
- The latest rendered pages were visually inspected; no clipping, overlap, or
  unreadable table/figure was found.
- Final checks report `47 passed`; Python compilation, shell syntax, CLI help,
  and `git diff --check` passed.

## 2.1.13 Fairness Recheck

- The user's concern is justified for the original headline setup: the
  3 km/SF9/fixed-pair matrix is favorable to route caching and too easy to
  expose link-quality conflicts. It should remain labeled as a
  contention-oriented operating point.
- The favorable TTL bias is quantified rather than hidden: matching
  MeshCore-like from 300 s to 600 s raises its ACK PDR from 0.381 to 0.519,
  leaving a matched protocol-bundle difference of 0.209 rather than the native
  0.347.
- The random-pair non-saturated probe removes pair reuse and retains an
  airtime advantage for MeshEcho, but its ACK PDR is 0.413 versus 0.456 for
  source-route caching. The one-shot Smart-CALM versus no-confidence delta is
  +0.001 with a 95% interval containing zero.
- The controlled route-conflict experiment supports only a bounded mechanism
  claim: confidence helps when the shorter candidate contains a materially
  weaker hop, not as a general topology-independent advantage.
- The revised conclusion is therefore fairer: shared-harness comparison is
  valid, but the scenario is not a neutral deployment benchmark and the
  evidence does not establish universal confidence-ranking superiority.
- The 2.1.13 paper compiles to 9 pages with bundled Tectonic; root PDF SHA-256
  is `aa2c2e5e171595256938be222a2cca7757dbbdc8bb516e4cc640dc2f2d300cbe`.
- Final validation reports 49 passing tests, successful Python and shell
  checks, clean diff whitespace, and no unresolved citation warnings.

## 2.1.13 Final Publish Verification

- Commit `fe24d1d` is synchronized with `origin/version/v2`.
- PR 1 is OPEN/DRAFT and now describes the 2.1.13 fairness-focused
  evaluation.
- The root PDF is 9 pages, PDF 1.5, and matches the verified Tectonic build
  with SHA-256
  `aa2c2e5e171595256938be222a2cca7757dbbdc8bb516e4cc640dc2f2d300cbe`.
- The fairness revision is complete. The evidence boundary remains:
  fair shared harness, biased frozen workload, matched-TTL sensitivity,
  non-dominant random-pair result, and bounded route-conflict mechanism
  evidence.
