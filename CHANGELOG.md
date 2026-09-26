# Changelog

## 2.1.24 - Model-informed route scores and frozen fading holdout

- Add optional `meshecho-calibrated` (maximum weakest modeled hop PRR), a
  PRR-product comparator with and without matched TTL-2 route-miss fallback,
  and optional ACK-timeout route-invalidation controls. Keep the original
  `meshecho` behavior distinct from the experimental calibrated variant.
- Freeze the scoring decision using only development seeds 41--50, then run
  untouched seeds 51--70 for repeated-pair fading and static controls. The
  2.1.23 seeds 21--40 remain historical evidence, not a fresh 2.1.24 holdout.
- In the 20-seed fading holdout (793 observed unicasts), calibrated MeshEcho
  reaches 0.624 ACK PDR/23.7 s versus original MeshEcho's 0.509/21.2 s:
  seed-paired ACK difference +0.1154, 95% CI [+0.0307,+0.2001], at +2.467 s
  airtime. Its ACK difference from PRR-product with matched fallback is only
  +0.0026 [-0.0055,+0.0107].
- Preserve null and adverse checks: static calibrated-minus-original ACK
  difference +0.0004 [-0.0741,+0.0748]; isolated first discovery has 480/480
  equal candidate sets and differences +0.0208 [-0.0129,+0.0546] against
  original MeshEcho and +0.0021 [-0.0056,+0.0098] against PRR-product.
  ACK-timeout eviction lowers fading ACK completion and raises airtime.
- Independently audit the 51--70 short-TTL control (793 observed unicasts
  per policy). At 30 s TTL, calibrated MeshEcho reaches 0.320 ACK PDR and
  64.8 s airtime versus 0.624/23.7 s at 600 s TTL. Seed-paired
  30-minus-600 s differences are -0.3043 ACK PDR
  (95% CI [-0.3932,-0.2154]) and +41.05 s airtime ([31.40,50.70]).
  Its 30 s ACK advantage over original MeshEcho is uncertain:
  +0.0215 [-0.0227,+0.0657].
- Rebuild the five-page ICC draft with `Zu Gao`, `Zhi Quan`, the 2.1.24
  holdout tables, and a descriptive fading-diagnostics table. Keep the
  unused 2.1.23 figure out of the manuscript.

## 2.1.23 - MeshEcho fixed-once and candidate-exposure audit

- Correct MeshEcho's cumulative hop-penalty accounting while leaving the
  historical CALM implementation and 2.1.22 outputs unchanged.
- Add shared RREQ relay timing, per-discovery candidate-path records, and a
  24-distinct-pair fixed-once unicast schedule with an explicit quality gate.
- Run 20 held-out topology seeds (21--40). In the fixed-once matrix, MeshEcho
  reaches 332/480 ACKs versus ETX's 266/480; seed-paired ACK-PDR difference
  is +0.137 (95% CI [+0.090,+0.185]) at +1.9 s [+1.6,+2.3] airtime.
- Isolate first discovery with fresh simulator state per pair/policy. All
  480 candidate sets match; MeshEcho versus ETX has a seed-paired ACK-PDR
  difference of +0.163 [+0.121,+0.204] and +0.094 s
  [+0.078,+0.110] airtime per pair.
- Preserve adverse comparisons: the budgeted rule reduces airtime but loses
  ACKs, and managed flooding beats MeshEcho on ACKs and airtime in the
  unconditioned random-pair case. Report native-timing, deep-hop, and
  temporal-fading cases separately from the fixed-candidate test.
- Set ICC paper author names to `Zu Gao` and `Zhi Quan`, both at Shenzhen
  University, with an English-only five-page IEEE conference manuscript.

## 2.1.22 - MeshEcho calibrated generalization correction

- Correct the deep generalization calibration from 20 km to 21 km after the
  per-seed gate caught an incomplete 3--5-hop pair pool for seed 12.
- Preserve the 100-node, 24-pair, PRR-qualified, 3--5-hop contract and rerun
  all 20 seeds rather than dropping the failed seed.
- Version the corrected random-pair, deep-multihop, temporal-fading,
  cache-aging, route-conflict, and MeshEcho component evidence under the
  `2.1.22` prefix.
- Keep the ICC contribution MeshEcho-only and simulation-only; Smart-CALM
  remains a historical simulator/firmware namespace.
- Add a compact primary-matrix bar figure with seed-level 95% confidence
  intervals; this is a presentation-only refinement and does not change the
  simulation version or reported estimates.
- Restore stricter IEEE conference formatting in the ICC manuscript by using
  explicit 10-point letterpaper `IEEEtran`, removing manual float/row-spacing
  compression, and allowing references to flow without a forced page break.

## 2.1.21 - MeshEcho generalization and stale-route evidence

- Keep MeshEcho as the only ICC method identity; the historical adaptive
  firmware line is excluded from the ICC protocol matrix and conclusions.
- Add a matched min-hop baseline so the paper compares MeshEcho with a
  genuinely different path policy in addition to fixed-SF ETX/ETT.
- Add unconditioned random-pair and 100-node, three-hop generalization cases.
- Add deterministic paired temporal block fading and long-versus-short
  route-cache diagnostics for stale-route behavior.
- Re-run the ICC primary, sensitivity, component, generalization, and route
  conflict evidence under the `2.1.21` release prefix.
- Tighten the ICC manuscript to a five-page, simulation-only,
  first-discovery route-admission claim with explicit external-validity limits.

## 2.1.20 - MeshEcho route-conflict attribution correction

- Correct the controlled route-conflict audit to instantiate the named
  `MeshEcho` policy rather than the historical adaptive controller.
- Preserve the confidence/no-confidence candidate-selection controls without
  importing adaptive profile or timeout behavior.
- Re-run the 20-seed route-conflict audit; both candidates appear in 90% of
  seeds and the paired MeshEcho ACK-PDR difference is `+0.221` with a 95%
  interval half-width of `0.096`.
- Narrow the ICC manuscript title to route admission because airtime is an
  evaluated operating-point metric, not a direct term in MeshEcho's score.

## 2.1.19 - MeshEcho fairness and cache-reuse revision

- Equalize matched source-route candidate exposure by collecting every
  destination RREQ seen during the configured discovery window, as MeshEcho
  and the metric baselines already do.
- Preserve one-reply duplicate suppression in the legacy immediate-reply
  source-route mode while leaving the matched-window collector unchanged.
- Make MeshEcho route-miss fallback honor the configured `fallback_ttl` instead
  of silently expanding to the simulator's maximum hop count.
- Rerun the calibrated ICC matrix, SF/load sensitivities, and MeshEcho
  component attribution after the fairness fix; the primary MeshEcho versus
  source-route ACK-PDR delta is now `+0.218` with paired 95% CI
  `[+0.041,+0.395]`.
- Add a repeated-pair unicast cache-reuse diagnostic at 600 s and 30 s route
  TTLs so route-cache hits and aging are measured separately from the sparse
  first-discovery primary estimand.
- Keep MeshEcho as the ICC method identity; Smart-CALM remains a separate
  firmware/history line and is not part of the ICC matrix.

## 2.1.18 - MeshEcho mechanism attribution revision

- Make MeshEcho the explicit ICC method identity; Smart-CALM remains outside
  the ICC protocol matrix as a separate firmware/history line.
- Add matched ETX and fixed-SF ETT external baselines to the ICC experiment
  contract and retain the conservative non-dominance interpretation.
- Add four MeshEcho component controls for confidence ranking, route-miss
  fallback, hop penalty, and route-age penalty.
- Rerun the 20-seed calibrated primary matrix, SF/load sensitivity cases, and
  component-ablation matrix under versioned `2.1.18` artifacts.
- Extend the five-page ICC manuscript with component attribution and clarify
  that ACK-confirmed completion is distinct from destination delivery.

## 2.1.17 - Reviewer-directed ICC evidence revision

- Add managed flooding to the primary calibrated comparison instead of
  omitting a raw protocol row.
- Add a reproducible 20-seed SF8 sensitivity case and a 20-seed offered-load
  case, both using the connected-pair quality gate and matched discovery budget.
- Narrow the Smart-CALM/no-confidence interpretation to a complete
  policy-bundle effect and cite the controlled route-conflict experiment as the
  surgical candidate-selection evidence.
- Keep the five-page ICC manuscript, prior-work hardware audit, and
  simulation-only external-validity boundary.

## 2.1.16 - Five-page ICC manuscript and prior-work hardware audit

- Expand the ICC 2027 manuscript from three pages to five pages with related
  work, explicit confidence/recovery equations, fixed parameters, metrics,
  evidence strata, paired ablations, discussion, and a hardware-validation
  boundary.
- Add `docs/icc2027_prior-work_hardware-evidence.md`, documenting a traceable
  sample of prior ICC LoRa/IoT papers that use analysis/simulation alone or
  combine simulation with measurements.
- Keep the 2.1.15 calibrated experiment data unchanged; this release updates
  the paper and submission evidence rather than changing simulator behavior.

## 2.1.15 - Matched route-discovery timing and calibrated ICC multi-hop matrix

- Add an explicit MeshCore-like route-discovery collection-window parameter;
  fresh ICC runs match the CALM 2 s window while legacy immediate-reply
  behavior remains reproducible with `0 s`.
- Add a 20-seed calibrated connected-multihop ICC matrix at 8.25 km/SF7 with
  PRR-qualified pair selection and one flow per minute.
- Preserve per-seed link-regime, graph-hop, route-discovery, ACK-PDR, airtime,
  and ablation diagnostics for the paper's primary mechanism table.
- Keep the 18 km connected probe as a clearly labeled route-discovery stress
  test rather than a headline performance claim.
- Replace the former 9-page ICCT draft with a 3-page ICC 2027 initial-
  submission draft that is below the six-page hard limit and reports the
  calibrated matrix as the primary evidence.

## 2.1.14 - ICC non-degenerate multi-hop quality gate

- Add a per-seed connected-multihop quality gate that rejects direct-link PRR
  saturation, incomplete pair pools, and effectively one-hop pair selections.
- Run the quality gate automatically after the four ICC matrix scenarios, with
  environment-variable overrides for calibration and legacy reproduction.
- Add regression tests for accepted and rejected probe regimes and document the
  gate as evidence-quality control rather than a performance claim.

## 2.1.13 - Fairness-focused paper revision

- Reframe the ICCT manuscript so the frozen repeated-pair matrix is treated as
  a contention-oriented operating point rather than a neutral multi-hop
  benchmark.
- Add an explicit fairness judgment that separates shared-harness fairness,
  matched-TTL sensitivity, random-pair external-validity evidence, and
  controlled route-conflict mechanism evidence.
- Align manuscript, experiment-plan, and release documentation with the
  current fairness boundary and the matched 600 s MeshCore-like default.
- Retain all historical CSVs and the firmware prototype at
  `meshecho-firmware-v2.1.2`.

## 2.1.12 - Recovery-budget sensitivity audit

- Add the explicit `--calm-disable-route-miss-fallback` control for
  current-code recovery-budget sensitivity checks.
- Add a paired 20-seed main-scenario audit with raw CSV and Markdown report.
- Add a configurable MeshCore-like route-cache TTL and a paired 20-seed
  native-versus-matched TTL audit.
- Make fresh ICC matrices use the matched 600 s MeshCore-like TTL by default;
  legacy 300 s reproduction remains available through
  `MESHCORE_ROUTE_TTL_S=300`.
- Revise the ICCT manuscript to quantify route-miss recovery separately from
  confidence-based route admission, quantify the route-cache TTL mismatch, and
  retain the conservative fairness boundary.
- Preserve the firmware prototype at `meshecho-firmware-v2.1.2`.

## 2.1.11 - Fairness diagnostics and budget-matched probe

- Add route-discovery attempt/success metrics and RREP/RREQ transmission
  diagnostics to the simulator and fairness probe.
- Add independent connected-pair low-load and single-flow stress matrices that
  show when a multi-hop setting is dominated by route-discovery contention.
- Add `--smart-max-timeout-retries 0` for a one-shot Smart-CALM mechanism
  comparison with no extra timeout retries.
- Revise the ICCT manuscript to use the one-shot budget-matched random-pair
  result and to avoid attributing recovery-driven gains to confidence ranking.
- Preserve the firmware prototype at `meshecho-firmware-v2.1.2`.

## 2.1.10 - Random-pair fairness evidence

- Integrate the ten-seed random-pair, non-saturated multi-hop probe into the
  ICCT manuscript.
- Report that MeshEcho retains an airtime advantage outside the frozen
  repeated-pair matrix, but does not establish a general ACK-PDR advantage.
- Report that the adaptive Smart-CALM variant is not unconditionally better than
  its fixed-profile control in the fairness probe.
- Preserve the frozen 3 km matrix and document the new probe as diagnostic
  evidence rather than silently replacing the original result line.

## 2.1.9 - Fairness-aware manuscript and RNG isolation

- Revise the ICCT manuscript to state the verified fairness boundary of the
  frozen simulation matrix.
- Document fixed-pair bias, high-PRR link saturation, unequal recovery budgets,
  and the fixed-payload airtime simplification.
- Add an opt-in independent channel-reception random stream for new fairness
  reruns while preserving legacy result reproducibility by default.
- Keep the frozen result files unchanged and retain the firmware prototype at
  `meshecho-firmware-v2.1.2`.

## 2.1.8 - Fairness audit traceability and no-fallback fix

- Finalize the MeshEcho ICCT manuscript with explicit common-harness,
  scenario-neutrality, and recovery-budget limitations.
- Record that the frozen 3000 m matrix is a contention-oriented high-PRR case,
  not a calibrated multi-hop deployment benchmark.
- Fix the Smart-CALM no-fallback confidence-threshold branch and add regression
  coverage; pre-fix Smart-CALM ablation CSVs are retained as historical
  artifacts and are not treated as current evidence.
- Add an opt-in independent channel-reception random stream for new fairness
  matrices while preserving legacy result reproducibility by default.
- Preserve the main three-protocol result tables while documenting the
  separate controlled route-conflict mechanism experiment.

## 2.1.7 - Fairness-bounded paper revision

- Revise the MeshEcho ICCT manuscript to distinguish common-harness fairness
  from scenario neutrality and recovery-budget symmetry.
- State that the frozen 3000 m matrix is a high-PRR, contention-oriented case
  with almost no multi-hop cached routes.
- Clarify that the frozen CALM line uses route-recovery fallback, while the
  confidence-triggered fallback and Smart-CALM timeout policies are separate
  capabilities or exploratory variants.
- Correct the terminology documentation to match the simulator's static
  per-link shadowing implementation.

## 2.1.6 - Fairness-aware ICCT manuscript package

- Integrate the link-budget and common-randomness fairness audit into the
  MeshEcho ICCT manuscript.
- Record direct-link PRR saturation, fixed-pair bias, multi-hop coverage, and
  unequal recovery-budget limitations without replacing the frozen results.
- Repair the controlled route-conflict table layout and preserve reproducible
  source, figure, and PDF artifacts for publication.

## 2.1.5 - Simulation fairness audit and paper revision

- Revise the ICCT manuscript to separate common-harness evidence from
  scenario and recovery-budget limitations.
- Document that the current 50-node matrix is link-quality saturated and
  produces almost no multi-hop cached routes.
- Add a reproducible fairness-audit note and correct the route-conflict paired
  delta to `+0.215`.

## 2.1.4 - Controlled route-conflict experiment

- Add a reproducible topology with short weak-link and long strong-link
  candidate routes.
- Add a confidence-versus-shortest-route A/B experiment with paired seed
  results and 95% confidence intervals.
- Add unit coverage proving that confidence selects the reliable long route
  when both candidates are available.

## 2.1.3 - ICC result and full-paper package

- Add the correct-prefix four-scenario ICC matrix under
  `meshecho_v2_1_2_50n_*`, with raw per-seed CSVs and long-format summaries.
- Add the versioned ICC comparison report for the refreshed matrix.
- Expand the Smart-CALM manuscript into a five-page IEEE conference draft with
  methods, equations, result tables, limitations, and verified references.
- Keep the firmware prototype at `meshecho-firmware-v2.1.2`; no firmware source
  behavior changed in this release.

## 2.1.2 - CSV normalization and release refresh

- Normalize generated CSV outputs to LF line endings across simulator and
  analysis scripts.
- Refresh the ICC comparison and versioned Smart-CALM comparison artifacts.
- Bump firmware and project release metadata to `2.1.2`.

## 2.1.1 - ICC comparison freeze

- Add the verified ICC 2027 comparison report and handoff note.
- Freeze the new ICC raw CSVs and long-format summaries under the
  `meshecho_v2_1_0_icc_50n_*` prefix.
- Add a deterministic unit test covering the Smart-CALM no-confidence route
  selection branch.
- Bump firmware and project release metadata to `2.1.1`.

## 2.1.0 - Firmware reliability and telemetry

- Complete Smart-CALM fallback delivery with reverse-path ACK generation.
- Clear completed pending flows so an acknowledged packet is not retried after
  the ACK timeout.
- Preserve the original application timestamp across route retries and
  fallback recovery for end-to-end ACK delay telemetry.
- Enforce terminal-hop TTL handling for route discovery and source-route
  replies.
- Bind retry profile parameters to the flow that selected them.
- Add bounded duplicate suppression for fallback forwarding.
- Expose receive failures, route aging, neighbor aging, fallback deliveries,
  ACK delivery counts, ACK delay, and learning counters through `show`.
- Add host smoke coverage for direct route ACK completion and fallback ACK
  completion.
