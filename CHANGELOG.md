# Changelog

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
