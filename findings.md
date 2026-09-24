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

## 2.1.14 ICC Quality-Gate Result

- Added `validate_non_degenerate_regime()` and `ProbeRegimeError` to enforce
  connected-multihop evidence quality per seed rather than by aggregate mean.
- The gate rejects any seed with direct-link PRR-below-0.99 fraction below
  `0.10`, fewer selected pairs than requested, or mean selected graph distance
  below `2.0` hops. Random-pair probes remain diagnostic and are not forced
  through the connected-pool checks.
- Added regression tests for one accepted seed and three rejection causes;
  full discovery now reports 52 passing tests.
- The ICC shell script runs a three-seed, 180 s, 50-node, 18 km connected
  quality probe after the four matrix scenarios by default. Set
  `ICC_RUN_QUALITY_PROBE=0` for explicit legacy reproduction.
- The real 2.1.14 probe passed all seeds with 24/24 candidate pairs, mean
  graph distance `2.014` hops, direct-link PRR-below-0.99 fraction `0.641`,
  and PRR-below-0.50 fraction `0.445`.
- The complete ICC shell smoke also passed after correcting the CLI alias from
  internal `meshcore-like` to the public `meshcore` protocol choice.
- The generated versioned CSV/Markdown evidence is intentionally included in
  this release; temporary smoke outputs were moved out of the repository.

## 2.1.15 Continuation Audit

- A completed 2.1.15 experiment session produced
  `results/meshecho_v2_1_15_icc2027_50n_unicast_pairs*` and
  `results/meshecho_v2_1_15_icc2027_50n_mixed*` only.
- No `meshecho_v2_1_15_icc2027_connected_multihop_quality` or
  `meshecho_v2_1_15_icc2027_calibrated_multihop` artifacts exist yet.
- Because the ICC paper's main claim depends on the calibrated non-saturated
  multi-hop matrix and the per-seed quality gate, the current version bump is
  incomplete and must not be published as a finished release.

## 2.1.15 Evidence and Paper Findings

- The full 2.1.15 workflow completed with all expected versioned artifacts.
- The calibrated matrix is non-degenerate by construction and measurement:
  20 seeds, 24 selected pairs per seed, graph distance 2.0, direct-link
  PRR-below-0.99 fraction 0.160, and PRR-below-0.50 fraction 0.046.
- CALM/MeshEcho mean ACK PDR is 0.720 versus MeshCore-like 0.537, with mean
  airtime 28.1 s versus 38.5 s. Smart-CALM minus no-confidence is +0.181
  ACK PDR (paired 95% CI [+0.094,+0.268]); Smart-CALM minus no-fallback is
  +0.002 ([-0.020,+0.024]).
- The 18 km quality gate is deliberately harsher: it passes all three seeds
  with mean graph distance 2.014 and direct-link PRR-below-0.99 fraction
  0.641, but MeshCore-like discovery success is only 0.178. It remains a
  discovery stress diagnostic rather than a main performance table.
- The new ICC manuscript is 3 pages, uses ICC 2027 wording, and does not
  claim physical validation or topology-independent dominance.

## 2.1.15 Publish Verification

- The complete release is published through commits `fb133ba` and `2ebefd1`;
  `origin/version/v2` resolves to `2ebefd13b41fe196f0df9092fafd38714ed6b59c`.
- PR 1 is OPEN/DRAFT at
  `https://github.com/BH4ME/lora-mesh-routing-sim/pull/1` with the updated
  2.1.15 title and evidence boundary.
- GitHub reports no configured checks on `version/v2`; the local verification
  suite and versioned experiment artifacts are therefore explicitly recorded
  rather than presented as remote CI results.

## ICC Submission-Readiness Boundary

- Official ICC 2027 guidance confirms the six-page initial-submission hard
  limit, English IEEE 10-point format, PDF-only EDAS upload, and exact EDAS
  title/author-list match. It also states that accepted work must be
  registered and presented for proceedings/Xplore publication.
- The compiled paper satisfies the format/page/evidence checks, and the source
  now contains the user-provided author metadata. Exact EDAS title/author
  registration and venue actions remain the pre-submission boundary.

## 2026-09-19 - Historical ICC Hardware-Evidence Audit

- The official ICC 2027 submission guidance specifies language, IEEE format,
  page limit, EDAS/PDF handling, originality, registration, and presentation;
  it does not state a universal requirement for a physical testbed or hardware
  prototype.
- A DOI/abstract audit of ten ICC papers found both simulation/analysis-only
  evidence and simulation plus measurements. The sample is not a systematic
  acceptance-rate study, so it supports a venue-practice conclusion rather
  than a guarantee of acceptance.
- Hardware/testbed-positive examples:
  - To et al., ICC 2018, ``Simulation of LoRa in NS-3: Improving LoRa
    Performance with CSMA'', DOI `10.1109/icc.2018.8422800`: an NS-3 module
    is validated against measurements from a real-world testbed, then used for
    the CSMA study.
  - Rochester et al., ICC 2020, ``Lightweight Carrier Sensing in LoRa:
    Implementation and Performance Evaluation'', DOI
    `10.1109/icc40277.2020.9149103`: reports feasibility measurements in
    real-world LoRa networks and also uses a custom simulator.
- Analysis/simulation-positive examples:
  - Georgiou et al., ICC 2020, ``Coverage Scalability Analysis of Multi-Cell
    LoRa Networks'', DOI `10.1109/icc40277.2020.9149081`: stochastic-geometry
    model and mathematical analysis; the abstract does not claim a testbed.
  - Hamdi et al., ICC 2020, ``Dynamic Spreading Factor Assignment in LoRa
    Wireless Networks'', DOI `10.1109/icc40277.2020.9149243`: evaluates the
    proposed assignment using numerical SER simulations.
  - Afisiadis et al., ICC 2020, ``Coded LoRa Frame Error Rate Analysis'', DOI
    `10.1109/icc40277.2020.9148806`: validates analytical FER expressions with
    Monte Carlo simulations.
  - Tu et al., ICC 2020, ``A New Closed-Form Expression of the Coverage
    Probability for Different QoS in LoRa Networks'', DOI
    `10.1109/icc40277.2020.9148720`: provides closed-form analysis and Monte
    Carlo verification.
  - Benkhelifa et al., ICC 2019, ``Minimum Throughput Maximization in LoRa
    Networks Powered by Ambient Energy Harvesting'', DOI
    `10.1109/icc.2019.8761478`: derives collision/optimization results and
    compares algorithmic allocations; no physical testbed is claimed in the
    abstract.
  - Amichi et al., ICC 2019, ``Spreading Factor Allocation Strategy for LoRa
    Networks Under Imperfect Orthogonality'', DOI `10.1109/icc.2019.8761235`:
    reports numerical results for a matching-based allocation algorithm.
- Mixed application evidence also occurs: Shaafi et al., ICC 2022,
  ``Wireless Body Sensor Networks for Sign Language Recognition with
  Real-time Data Analysis'', DOI `10.1109/icc45855.2022.9838474`, reports
  acquired inertial/muscular data and experimental classification results, but
  this is an application/data experiment rather than a communications
  testbed requirement.
- Practical conclusion for MeshEcho: a simulation-only ICC submission is
  defensible if the model, parameters, baselines, statistical protocol,
  quality gates, code/data release, and limitations are explicit. Hardware
  would strengthen external validity, especially for radio sensitivity,
  interference, timing, and duty-cycle claims, but its absence is a stated
  limitation rather than an automatic disqualifier.
- The ICC manuscript should therefore say ``simulation-only evidence'' and
  propose hardware or hardware-in-the-loop validation as future work. It must
  not imply that the current results are measured on SX126x/SX127x devices.

## 2.1.17 Reviewer-Directed Findings

- The current primary ICC table omits `meshtastic-like` even though the
  connected-multihop raw report contains it. The omission makes the comparison
  look selective; the revised primary table should include managed flooding
  with the same shared topology and traffic trace.
- The Smart-CALM/no-confidence ablation changes candidate admission and route
  discovery success (`0.801` versus `0.589` in the reused calibrated report),
  so the end-to-end `+0.181` ACK-PDR difference cannot be called a confidence-
  only causal effect. It should be labeled a complete policy-bundle effect.
- The controlled route-conflict experiment is the appropriate surgical
  evidence: it holds the candidate set fixed and shows confidence selecting
  a longer reliable path only when the shorter path is artificially weakened.
  The manuscript should point to that experiment and keep it distinct from the
  full-network ablation.
- The current paper has one powered non-saturated regime. A versioned
  sensitivity runner should add at least SF variation and offered-load
  variation under the same connected-pair selection and quality gate.
- New sensitivity outputs must be inspected for gate failures and reported as
  robustness evidence, not silently pooled with the primary estimand.

## 2.1.17 Implementation Findings

- `tools/run_icc_sensitivity_experiments.py` now reuses
  `run_one_probe()`, `validate_non_degenerate_regime()`, `write_csv()`, and
  `write_report()` instead of duplicating simulator logic.
- The SF8 case initially used 8.25 km and then 9 km, but the 20-seed gate
  rejected seed 10 and seed 14 at those settings. A 10 km area passes all 20
  seeds while preserving the connected-pair and graph-hop contract; this
  calibration choice is recorded in the runner, not hidden in the paper.
- A one-seed smoke produced both sensitivity reports with all seven protocol
  configurations. No quantitative paper claim is based on that smoke.

## 2.1.17 Sensitivity Results

- The 20-seed SF8/10-km case passed all per-seed gates. Means:
  managed flooding `0.434` ACK PDR / `39.2 s` airtime, MeshCore-like
  `0.160` / `70.4 s`, CALM `0.435` / `61.7 s`, Smart-CALM `0.402` /
  `61.4 s`, and no-confidence `0.299` / `59.8 s`.
- The 20-seed SF7/4-flows-per-minute case passed all per-seed gates. Means:
  managed flooding `0.409` / `50.5 s`, MeshCore-like `0.411` /
  `151.5 s`, CALM `0.652` / `111.3 s`, Smart-CALM `0.605` /
  `110.9 s`, and no-confidence `0.443` / `109.1 s`.
- The SF8 case is a boundary case: flooding and CALM have nearly equal PDR,
  but flooding uses less airtime. The load case preserves a CALM PDR
  advantage while flooding remains the lower-airtime reference.
- The compiled 2.1.17 paper is still exactly five letter-size pages; the new
  robustness table fits without overfull-box or unresolved-reference warnings.

## 2.1.18 Metric-Baseline Revision

- Added two external quality-aware route-selection baselines to the simulator:
  `etx-mesh` minimizes the sum of `1/PRR` hop costs and `ett-mesh` minimizes
  `ToA/PRR` costs. Both use the same 2-s discovery window, 600 s route TTL,
  shared packet model, and no route-miss fallback.
- The baselines carry a bounded higher-is-better route score through the
  existing RREQ/RREP path field; no simulator channel or delivery semantics
  were changed.
- Test-first coverage is in `tests/test_metric_routing_baselines.py`; the
  first red run failed because `MetricMesh` was not yet implemented, and the
  implementation now passes the new tests and the existing suite.
- A one-seed 600 s connected-multihop smoke produced nonzero ETX/ETT rows and
  confirmed that the fixed-SF configuration makes ETX and ETT numerically
  equivalent, as expected because every packet has the same ToA. The paper
  should report this as a fixed-SF sanity baseline rather than imply an
  independent ToA advantage.

## 2.1.16 Manuscript Revision Findings

- The ICC source now contains related work, an implementation-faithful CALM
  confidence equation, a fixed-parameter table, metric/statistical definitions,
  evidence strata, paired ablation table, discussion, artifact manifest, and
  hardware external-validity boundary.
- Fresh Tectonic compilation at
  `paper/icc2027/build-2_1_16-tectonic-v3/icc2027_lora_mesh.pdf` produces
  exactly 5 letter-size pages, within the ICC six-page initial-submission cap.
- Rendered pages show no clipping or table overlap. References continue onto a
  fifth page, but the manuscript remains readable and uses the requested five
  printed pages rather than artificial spacing.
- Version `2.1.16` is a paper/evidence revision: the calibrated 2.1.15 CSVs
  remain the underlying simulation results and are explicitly identified as
  reused. A fresh reproduction with `OUT_PREFIX=meshecho_v2_1_16_icc2027`
  will create a new output prefix if desired.
- A 600 s, one-seed calibrated connected-multihop smoke run passed the quality
  gate and produced nonzero protocol results (CALM ACK PDR 0.667 versus
  MeshCore-like 0.333 for seed 1). A separate 120 s gate-only smoke was not
  used for quantitative interpretation.
- A redundant full 2.1.16 runner was started but safely stopped during its
  second legacy 20-seed scenario after confirming that the no-code-change
  revision would only duplicate the verified 2.1.15 matrix. Its partial
  untracked outputs are intentionally excluded from the release; the paper
  cites the complete 2.1.15 matrix and the new smoke as the 2.1.16 validation.

## 2.1.16 Publish Verification

- Commit `859686a` is pushed to `origin/version/v2`.
- PR 1 is OPEN/DRAFT with title `[codex] MeshEcho 2.1.16 five-page ICC
  manuscript and hardware audit` and head OID `859686a08f6f47a606851ff309f3b8fbb621516c`.
- The PR body records 53 passing tests, the five-page PDF, the one-seed smoke,
  the hardware-evidence conclusion, and the simulation-only boundary.
- Unrelated old build/render outputs, old 2.1.14 artifacts, partial 2.1.16
  runner outputs, and `tmp/` remain untracked and were not published.

## 2.1.14 Final Publish Verification

- Commit `b5de06b` is present locally and on `origin/version/v2`.
- PR 1 is OPEN/DRAFT with title
  `[codex] MeshEcho 2.1.14 ICC evidence-quality gate`.
- The code, evidence artifacts, version metadata, tests, documentation, and
  resumable state files are published; no further action is pending for this
  revision.

## 2.1.18 MeshEcho Identity and Attribution Findings

- The ICC method is now explicitly `meshecho`; the default ICC protocol tuple
  contains only managed flooding, matched source routing, ETX, ETT, and
  MeshEcho. The adaptive firmware/history line is not part of the ICC matrix.
- Added `MESHECHO_ABLATIONS` with four within-policy controls:
  `meshecho-no-confidence`, `meshecho-no-fallback`,
  `meshecho-no-hop-penalty`, and `meshecho-no-age-penalty`.
- Completed a 20-seed component matrix under the same 50-node/8250-m/SF7
  connected-multihop contract. MeshEcho minus no-confidence is `+0.148`
  ACK PDR with paired 95% CI `[+0.052,+0.244]`; minus no-hop-penalty is
  `+0.050` with `[-0.029,+0.130]`; no-fallback and no-age-penalty are
  `0.000` in this workload.
- The no-fallback and no-age results are reported as workload-specific
  evidence boundaries, not universal component conclusions.
- Regenerated the primary and SF/load reports with no adaptive-firmware
  protocol rows. Added a report regression test that rejects Smart-CALM
  leakage into the 2.1.18 ICC evidence reports.
- Extended the ICC manuscript with the component-attribution result while
  keeping it at exactly five letter-size pages. The final render was checked
  page-by-page; tables and references are readable with only underfull-box
  warnings.
- `VERSION` and ICC-facing docs now target `2.1.18`; the final remote publish
  is still pending.

## 2.1.19 MeshEcho-Only Fairness Revision Findings

- The legacy source-route immediate-reply branch had a regression after the
  matched-window candidate-exposure fix: duplicate destination RREQs could
  emit multiple RREPs. A test now locks the historical one-reply behavior.
- `CalmMesh.route_miss_recovery_ttl()` previously returned `sim.max_hops`
  despite a configured `fallback_ttl`; it now delegates to
  `fallback_ttl_for(flow_id)`, and a test verifies the configured value.
- Targeted regression status after the red-green cycle: `8 passed`.
- All subsequent 2.1.19 evidence must be regenerated after this code change;
  existing 2.1.19 CSVs are not yet authoritative until rerun.
- The corrected reruns completed for the primary, component, SF8/load, and
  cache TTL cases. Primary means are MeshEcho `0.719719` ACK PDR /
  `28.141 s` airtime, matched source-route `0.501558` / `38.461 s`, and
  ETX/ETT `0.660888` / `27.627 s`; the paired MeshEcho-source-route ACK
  delta remains `+0.218` with CI `[+0.041,+0.395]`.
- The corrected fallback TTL changes the cache diagnostic: MeshEcho at TTL600
  is `0.786` ACK PDR / `0.806` destination PDR / `25.7 s`, while TTL30 is
  `0.472` / `0.490` / `88.5 s`, with `18.5` route repairs. These are
  descriptive secondary results, not a causal age-penalty claim.
- The ICC source now compiles to exactly five pages after a concise related-work
  rewrite; rendered pages 1--5 were inspected and are layout-clean.

## 2.1.20 MeshEcho Route-Conflict Attribution Findings

- The controlled route-conflict harness was still subclassing
  `SmartCalmMesh`, despite the ICC manuscript naming MeshEcho as the method.
  This was a semantic evidence mismatch, not merely a label issue.
- Added a regression test that requires `RecordingConflictMesh` to be a
  `MeshEcho` instance and rejects `SmartCalmMesh` as its implementation.
- Replaced the harness base class with `MeshEcho`, retained the explicit
  confidence/no-confidence selector, and removed adaptive profile/timeout
  constructor arguments.
- A fresh 20-seed route-conflict run reports both candidates in 90% of seeds;
  MeshEcho selects the longer path in all observed conflicts and improves ACK
  PDR by `+0.221 +/- 0.096` over the shortest-candidate control.
- The new result is stored in
  `results/meshecho_v2_1_19_icc2027_route_conflict.csv` and
  `docs/results/meshecho_v2_1_19_icc2027_route_conflict.md` pending the
  version-2.1.20 evidence regeneration.
- The manuscript title is being narrowed from “Airtime-Aware” to
  “Confidence-Aware Route Admission” because MeshEcho reports airtime as an
  operating-point metric but does not directly optimize ToA in its score.

## 2026-09-19 - 2.1.20 Acceptance Assessment

- Validation is technically clean: `python3 -m pytest -q` reports 67 passed;
  Python compilation, shell syntax, and `git diff --check` pass.
- The current ICC PDF has six letter-size pages. Six pages is within the
  official ICC initial-submission ceiling, but the project requirement remains
  five pages and the repository checklist is stale because it claims the PDF
  is already five pages.
- The paper is a credible ICC submission candidate but should be scored as
  borderline/weak-reject risk rather than safe accept. The strongest evidence
  is the paired MeshEcho versus matched source-route ACK-PDR/airtime result:
  `+0.218` ACK PDR with 95% CI `[+0.041,+0.395]` and `-10.3 s` airtime.
- The strongest limitation is estimand/generalization: the 20-seed primary
  matrix is conditioned on a PRR-qualified pair pool, every selected pair is
  exactly two hops, and every protocol has zero route-cache hits. It therefore
  measures first-discovery route admission, not general cache reuse or route
  aging.
- MeshEcho versus ETX/ETT is not statistically separated
  (`+0.059`, 95% CI `[-0.108,+0.226]`), and destination-PDR differences also
  include zero. The paper must not imply general reliability dominance.
- The route-conflict audit is useful surgical evidence (`+0.221 +/- 0.096`)
  but is a seven-node controlled topology; it cannot substitute for
  unconditioned random-pair or deeper-hop evidence.
- Hardware is not the main blocker. The ICC practice sample includes
  analytical and simulation-only work, but the paper must keep the
  simulation-only boundary explicit.
- Before submission, prioritize: unconditioned random pairs; 3--5-hop or
  100/200-node scale; one distinct routing baseline; temporal fading/stale
  routes; five-page compression; and final EDAS title/author metadata.

## 2026-09-19 - 2.1.18 Pre-submission Review

The current five-page manuscript is a credible ICC submission candidate, but
it is borderline rather than a safe accept. The strongest evidence is the
matched-harness ACK-completion/airtime tradeoff against the source-route
baseline; the evidence does not establish a statistically separable advantage
over ETX/ETT or a general destination-delivery gain.

The most important reviewer risks are:

1. The calibrated matrix selects 24 graph pairs per seed and all 480 selected
   pair observations are exactly two hops. Each run has only about 5.1
   unicast flows and `route_cache_hits` is zero for every primary row, so the
   experiment estimates first-discovery/route-admission behavior rather than
   route-cache reuse or route-aging behavior. The paper should either add a
   repeated-pair/cache-aging estimand or remove cache/age claims from the main
   contribution.
2. The `meshecho-no-confidence` delta is not a fixed-candidate causal effect:
   discovery success, cached-route count, and selected route length also
   change. It must be described as an end-to-end policy-bundle effect unless a
   fixed-candidate replay/control is added.
3. ETX and ETT are mathematically identical under fixed SF and fixed payload
   time-on-air. They are a sanity check, not two independent strong baselines;
   a min-hop/shortest-path or online ETX/RPL-style baseline would make the
   comparison more convincing.
4. The selected-pair quality gate is useful for a controlled non-degenerate
   case, but it conditions the headline result on a PRR-qualified graph and
   provides only a two-hop topology. A 20-seed unconditioned random-pair
   matrix and a deeper 3--5-hop or larger-network case would address
   generalization and selection bias.
5. Static shadowing makes discovery-time confidence closely aligned with the
   forwarding channel. A temporal fading/stale-route case is more important
   for this mechanism than a generic extra plot; hardware/HIL would strengthen
   external validity but is not an ICC hard requirement.
6. The SF8 robustness case was post-hoc calibrated from 8.25 km/9 km to
   10 km after quality-gate failures. This is acceptable as a calibration
   diagnostic only if the selection process is disclosed and the case is not
   presented as an untouched robustness test.
7. A code-level fairness audit finds that the matched source-route baseline
   still suppresses duplicate RREQs at the destination before adding
   candidates, whereas MeshEcho/ETX/ETT collect candidates during the
   two-second window. Thus the `+0.183` MeshEcho--source-route difference can
   mix confidence selection with a larger candidate pool. The baseline should
   be changed to collect the same candidate set (then choose first/shortest),
   or the comparison must be explicitly downgraded to a first-arrival
   behavior baseline and rerun.
8. In the primary configuration, route-miss fallback adds transmissions but
   has zero ACK-PDR effect; the paper should either show a workload where the
   recovery mechanism matters or remove it from the central contribution.

The current local `2.1.18` worktree is staged but not published:
`origin/version/v2` still reports `2.1.17`. Before any EDAS submission, push a
tagged 2.1.18 artifact and replace `Anonymous Authors` with the exact EDAS
author list/title.

## 2.1.22 Author Metadata Update

- The ICC manuscript now lists `Gao Zu` and `Quan Zhi` in that order, in
  English only, both affiliated with Shenzhen University, Shenzhen, China.
- The paper remains simulation-only; adding author metadata does not change the
  2.1.22 simulation evidence or require a release-version bump.
- The exact same title and author order still need to be entered in EDAS before
  submission.

## 2.1.22 Presentation Refinement

- Added one compact two-panel bar figure to the ICC manuscript: ACK-confirmed
  PDR and total airtime for the primary calibrated matrix.
- Bars use the existing Table II means and whiskers use the existing
  seed-level two-sided 95% CI half-widths; no new experiment or estimate was
  introduced.
- ETX and fixed-SF ETT are shown as one bar because they coincide under the
  shared packet-time model. The figure improves scanability without turning
  the paper into a collection of disconnected plots.
- Tectonic compilation remains at five letter-size pages with no figure
  clipping or label overlap in the inspected page.

## 2.1.22 ICC Formatting Cleanup

- Tightened the ICC LaTeX source toward the official IEEE conference template:
  explicit `conference,letterpaper,10pt` document class; no manual page-margin,
  column-width, global float-spacing, or global table-row compression.
- Removed the unnecessary `IEEEoverridecommandlockouts` directive and the
  forced `\clearpage` before references, allowing the bibliography to flow
  naturally in the IEEE two-column layout.
- Reduced keywords to five IEEE-style terms and adjusted Table I locally to
  remove the remaining overfull table warning without changing margins.
- Final Tectonic build remains five letter-size pages. Visual page inspection
  found no clipped text, page numbers, table overflow, or figure overlap.

## 2.1.21 Continuation State

- The active clean worktree is `/tmp/lora_mesh_remote_current.iIrtPz` on
  branch `version/v2`, with local and remote currently at `6d2134b`
  (published 2.1.17 state); the local worktree contains unpublished 2.1.21
  changes.
- `VERSION` is `2.1.21`.
- The 2.1.21 primary/sensitivity raw CSVs exist for the legacy matrix, but
  calibrated multihop and connected-quality outputs do not yet have complete
  summary artifacts.
- `minhop-mesh` is registered as a distinct shortest-candidate baseline and
  is present in the 2.1.21 probe reports.
- Temporal block fading is deterministic by seed, unordered link, and time
  block; protocol runs share the same fading realization for a given seed.
- The 2.1.21 generalization runner defines unconditioned random pairs,
  100-node 3--5-hop deep multihop, and long/short route-TTL temporal-fading
  cases; these are not yet formally completed.
- The first deep-multihop run exposed a valid per-seed failure at 20 km:
  seed 12 had only 20 eligible 3--5-hop pairs. A 21 km calibration scan
  produced complete 24-pair pools for all 20 seeds while retaining a
  strongly non-degenerate direct-link regime, so the corrected run is being
  versioned as 2.1.22.

## 2.1.22 Evidence Findings

- Primary calibrated matrix remains: MeshEcho 0.720 ACK PDR / 0.739
  destination PDR / 28.1 s airtime; matched source-route 0.502 / 0.636 /
  38.5 s; ETX/ETT 0.661 / 0.741 / 27.6 s; min-hop 0.419 / 0.435 / 26.9 s.
- Paired MeshEcho deltas: +0.218 ACK PDR over matched source-route
  `[+0.041,+0.395]`; +0.059 over ETX/ETT `[-0.108,+0.226]`; +0.301 over
  min-hop `[+0.161,+0.441]`.
- Component attribution: removing confidence changes ACK PDR by +0.148
  `[+0.052,+0.244]`; fallback and age are zero-effect in the sparse primary
  workload; hop penalty is +0.050 with a CI crossing zero.
- Generalization: unconditioned random pairs give MeshEcho 0.404 ACK PDR /
  99.5 s and ETX 0.308 / 98.1 s; 100-node 3--5-hop gives MeshEcho
  0.696 / 160.4 s and ETX 0.531 / 156.6 s.
- Temporal fading: long TTL gives MeshEcho 0.526 / 21.2 s, short TTL gives
  0.324 / 71.3 s. This supports a stale-route boundary diagnostic, not a
  claim that age scoring universally solves fading.
- The rewritten ICC paper now makes a bounded simulation claim, stays
  MeshEcho-only, keeps `Anonymous Authors`, and compiles to 5 pages.
