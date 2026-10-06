# Task Plan: MeshEcho Core Rewrite and ICC Evidence

## 2026-10-06 algorithm-boundary continuation

- [complete] Confirmed from `meshecho_cpr.py` and `lora_mesh_sim.py` that CPR
  uses an independent recovery selector and independent source/relay lifecycle;
  it does not call the DRC source decision selector.
- [in_progress] Complete release closure and decide whether the remaining
  inheritance from `MeshEchoDRC` is only a substrate-reuse concern or requires
  a code refactor before publication.
- [error logged] The first planning catch-up command used `python`, which is
  unavailable in this macOS environment; use `python3` for the bundled script.
- [complete] Read-only PDF inspection found `build-2_1_27-cpr-final` clean on
  all five pages; it is preferred over `build-cpr-balanced-5` because all
  references stay on page 5.
- [error logged] Bare `pytest -q` failed during collection because the user
  site pytest launcher did not put the repository root on `sys.path`; the same
  interpreter collected CPR tests successfully with `python3 -m pytest`.
- [complete] Re-generated development and holdout artifacts after clean commit
  `a013067ebf5d7ba7031d38634f7caf3bfda99dbb`; both independent population
  audits passed and both manifests record that clean revision.
- [complete] Full regression passed with `1182 passed, 1 skipped`; py_compile,
  diff checks, PDF metadata and Unicode scans also passed.
- [in_progress] Stage only the formal CPR artifacts and commit/push the final
  package; leave exploratory, smoke, historical, and intermediate build files
  untracked and out of the release.

## 2026-10-06 release closure checkpoint

- [complete] Confirmed the requested boundary: CPR is a rewritten source,
  recovery, and relay-feedback core; the PHY/channel/event/ACK/ToA/energy
  substrate remains shared for fair controls.
- [complete] Updated `VERSION` from `2.1.26` to `2.1.27` and added the CPR
  release entry to `CHANGELOG.md`.
- [complete] Updated `README.md`, `docs/icc2027_experiment_plan.md`, and
  `docs/icc2027_submission_checklist.md` so the current release points to CPR
  and labels the old 2.1.25/2.1.26 matrices as historical.
- [complete] Copied the verified five-page CPR PDF from
  `paper/icc2027/build-cpr-balanced-5/icc2027_lora_mesh.pdf` to the canonical
  `paper/icc2027/icc2027_lora_mesh.pdf`; SHA-256 is
  `01cab1928e1eb8f583e3d42c873ff020de8518dfdf81bf45482136cebdba30`.
- [in_progress] Run the final full regression, CPR development/holdout audits,
  static stale-claim checks, and PDF metadata/render checks. Then stage only
  the CPR release package, commit, and push after reviewing the staged list.

## 2026-10-06 final verification continuation

- [complete] Re-audited CPR development and holdout manifests; both reports
  remain `passed=true` with all integrity, exposure, reliability, and cost
  checks true.
- [complete] Ran the full repository regression after the final CPR source and
  manuscript changes: `1181 passed, 1 skipped`.
- [complete] Recompiled the revised ICC source to
  `paper/icc2027/build-cpr-balanced-5/icc2027_lora_mesh.pdf`; it is a five-page
  Letter PDF. The final-page references are balanced using the vendored
  `paper/icc2027/balance.sty` macro.
- [complete] Rendered all five pages with Poppler and visually checked the
  title/authors, tables, figure, section flow, and references. No clipping,
  overlap, broken glyph, or Chinese author text was found.
- [complete] Corrected the manuscript's relay-ledger description so it matches
  the implementation's local index and stored endpoint/path validation.
- [pending] Copy the verified PDF to the canonical paper path, update release
  metadata/version, run final consistency checks, then commit and push the
  requested package to GitHub.

## 2026-10-06 CPR finalization checkpoint

- [complete] CPR source/recovery/feedback core and paired development/holdout
  artifacts are present and independently gated.
- [complete] ICC TeX has been rewritten around CPR and regenerated tables and
  figure sources use the holdout artifact bundle.
- [in_progress] Balance the IEEEtran last-page references, then recompile and
  visually inspect all five pages.
- [pending] Run the final full regression, CPR artifact audits, static stale-
  terminology checks, and consistency checks before any VERSION bump.
- [pending] Copy the verified PDF to the canonical paper path, update release
  metadata, commit, and push only after the verification gate is green.

### Current evidence

- PDF build: `paper/icc2027/build-cpr-rewrite/icc2027_lora_mesh.pdf`, 5 pages;
  no overfull boxes; one nonfatal underfull paragraph in the mechanism text.
- Holdout gate: `results/meshecho_cpr_holdout_92300_92319_20261006.gate.json`,
  passed with CPR ACK PDR `0.9829`, destination PDR `0.9984`, and mean TX
  airtime `6.2903424 s`.
- Visual review: pages 1--4 are legible and aligned; page 5 contains only the
  left reference column and must be balanced before final release.


## Active continuation (2026-10-06, CPR manuscript migration)

- [complete] Revalidated the current v2 worktree, persisted planning files, and
  recovered the CPR source/experiment state after the context boundary.
- [complete] Confirmed that `MeshEchoCPR` is the new source/recovery algorithm
  core; the preserved PHY/channel/forwarding/ACK substrate is intentionally
  shared for causal fairness. The old SR manuscript is not evidence for CPR.
- [in_progress] Rewrite `paper/icc2027/icc2027_lora_mesh.tex` from the audited
  CPR development and untouched holdout artifacts, including method, controls,
  tables, figures, limitations, and reproducibility details.
- [pending] Recompute all paper numbers directly from raw CPR artifacts and
  create only paper figures/tables whose source hashes and case metadata are
  recorded.
- [pending] Compile the ICC PDF, inspect all five rendered pages, run the full
  regression and artifact checks, then update `VERSION` only after the final
  paper package is internally consistent.

### Compression checkpoint

Before any automatic context compression, append the current phase, changed
files, command results, artifact paths/hashes, and next action to
`task_plan.md`, `findings.md`, `progress.md`, and the CPR handoff Markdown.
After compression, read those files before editing or interpreting results.

## Active continuation (2026-10-06, CPR exploratory stage)

- [complete] Restored the current worktree and re-read the persisted plan,
  findings, and progress files after the previous context boundary.
- [complete] Confirmed the algorithm boundary: CPR is a new source/recovery
  policy on the preserved PHY/channel/forwarding substrate; DRC remains a
  sealed negative control after its +32.2% airtime gate failure.
- [complete] Confirmed CPR evidence-v2 mechanical smoke and focused/full
  regression status (`18` CPR tests; `1175 passed, 1 skipped` full tree).
- [in_progress] Freeze a separate CPR exploratory contract with fresh seeds
  `92020..92029`, paired CPR/no-cancel/DRC controls, and an exposure-only
  decision gate before any development cohort.
- [error logged] The first exploratory CLI completed simulation and wrote an
  artifact bundle, but its audit rejected the bundle because a relative
  `--contract-path` produced an absolute source-hash key while audit resolved
  the same contract to a repository-relative key. The bundle is invalid and
  is retained as a diagnostic failure; normalize paths before retrying.
- [complete] Added contract-path normalization, an explicit CLI contract
  argument, and a regression test that audits an external contract file.
  Relative and absolute repository contract paths now produce identical source
  hashes. The failed bundle is quarantined before the corrected run.
- [error logged] The corrected exploratory run reached ACK provenance and
  rejected a valid multi-hop ACK because the validator assumed the ACK TX
  sender was the final destination. In the simulator an ACK is physically
  transmitted by each reverse-path relay; the audit must validate the reverse
  path hop instead.
- [complete] Added a RED/GREEN audit test using seed `92024`; the validator
  now joins ACK origin/final destination, reverse path, reverse hop, packet
  path index, and physical sender. CPR tests are `20 passed`; the invalid
  bundle is quarantined before the final retry.
- [error logged] The first quarantine command used the bare `mv` name and the
  shell reported it missing despite `/bin/mv` being present; the same explicit
  move with `/bin/mv` succeeded.
- [complete] Corrected exploratory bundle `92020..92029` passed the full
  evidence-v2 audit (`40` runs, `160` scheduled flows, `698` TXs, `5584` RX
  attempts, `97` accepted ACKs, zero incomplete joins).
- [NO-GO for current workload] The predeclared exposure gate failed: CPR had
  zero physical `R_REPEAT` and zero `F_RECOVERY` starts across all ten seeds.
  It recorded `240` initial-F `cpr-cancel` events, but the repeat-before-flood
  recovery mechanism was not exercised. Do not open development or edit the
  ICC paper from this cohort.
- [in_progress] Design a fresh exposure workload with repeated same-pair
  traffic and controlled fading/collision opportunities; this is a new
  exploratory contract, not a retune of the failed cohort.
- [complete] Added the frozen exposure profile and contract
  `docs/research/meshecho_cpr_exposure_contract_20261006.md`: 20 nodes,
  repeated Poisson pair traffic, 6 dB block fading, and seeds `92100..92109`.
- [pending] Run and independently audit the exposure contract exactly once;
  development remains closed until its exposure gates pass.
- [complete] Exposure bundle `92100..92109` passed evidence-v2 audit and all
  five predeclared exposure gates: 323 CPR flows, 279 `R_INITIAL`, 16
  `R_REPEAT`, 13 `F_RECOVERY`, 853 cancellations, repeated pairs in all ten
  seeds, and CPR mean airtime 38.1% below DRC no-rescue.
- [in_progress] Freeze the confirmatory CPR development/holdout contract with
  fresh `92200..92219` development and `92300..92319` untouched holdout seeds.
- [pending] Add explicit stage metadata to the CPR runner, run development,
  independently recompute its paired reliability/cost gates, and open holdout
  only if every gate passes.
- [complete] Development `92200..92219` completed and passed the independent
  population audit. It has 80 runs, 40 started repeats, 26 started recovery
  FLOODs, zero incomplete RX/TX joins, and all reliability/cost checks pass.
- [in_progress] Enforce the development gate report as a hard precondition for
  opening holdout `92300..92319`.
- [complete] Holdout `92300..92319` was opened only after the passed
  development report check and completed with 80 runs. Its independent audit
  passed all integrity, exposure, reliability, cost, denominator, and
  prerequisite checks; no holdout seed was reused.
- [in_progress] Rebuild the ICC manuscript and figures from the validated
  holdout artifacts, then compile/render-audit the PDF before any version or
  publication metadata change.
- [pending] Only after exploratory and then development/holdout gates pass may
  the ICC LaTeX, figures, VERSION, GitHub, or EDAS state change.

### Automatic-context checkpoint

The authoritative continuation files are `task_plan.md`, `findings.md`, and
`progress.md`. Before any automatic context compression, append the current
phase, command status, artifact paths, hashes, and next action to all three;
after compression, read all three before making a decision or editing code.

## Active continuation (2026-10-06)

- [in_progress] Continue from the persisted DRC design: finish the
  independent runner and evidence closure before claiming a simulation result.
- [in_progress] Keep the source-core rewrite separate from the reusable PHY /
  channel / forwarding substrate; do not relabel old SR/DHR/DCB numbers.
- [pending] After runner audit, run only mechanical smoke, then development;
  open holdout only if the predeclared gate passes.
- [pending] Rewrite and compile the ICC paper from raw holdout artifacts, then
  update version metadata only after the PDF and reproducibility audit.

### DRC development decision

- [complete] The frozen development cohort completed through the disk-backed
  runner and passed the independent artifact audit.
- [failed] The declared joint gate failed the candidate-vs-no-rescue airtime
  ceiling (36.8304512 s vs 27.8528640 s, about 32.2% higher).
- [closed] Holdout is closed for this DRC contract. Do not rewrite the ICC
  manuscript as a positive DRC result. Any next method must be specified as a
  successor algorithm with a new contract and fresh development seeds, or the
  paper must report this candidate as a no-go.

### Successor continuation: MeshEcho-CPR (2026-10-06)

- [complete] Read-only review confirmed the DRC failure is a recovery-cost
  failure, not a PHY/ledger failure: 81 recovery-F starts added about 203.9 s
  of aggregate FLOOD relay airtime, while the candidate gained only 32 source
  ACKs over the no-rescue control. The old DRC cohort remains sealed.
- [in_progress] Freeze a new successor contract that changes the source
  recovery state machine and relay forwarding behavior. It must use only
  packet/local observations, charge every action, and retain DRC as a negative
  control rather than silently replacing it.
- [complete] Add and implement the first public controller slice: the source
  must physically start one same-path repeat before it can request one FLOOD
  recovery, and both actions are deadline-gated.
- [complete] Add the RED test and vertical slice for physical ACK-terminated
  cancellation of an uncommitted initial or recovery FLOOD relay.
- [complete] Broaden CPR malformed-ACK/commit-boundary coverage and build a
  fresh disk-backed smoke/audit runner.
- [complete] Freeze the CPR evidence-v2 smoke contract and run fresh
  nonreserved seeds; independent request/TX/RX/ACK/action joins pass.
- [in_progress] Predeclare and run a small exploratory matrix on fresh seeds,
  independently audit source/packet/state hashes, then decide whether a
  development contract is justified. Do not
  open a confirmatory development or holdout cohort until the exploratory
  mechanism has exposure and a frozen matched-control contract.
- [pending] Only after a successor passes fresh development and untouched
  holdout may the ICC manuscript, figures, VERSION, GitHub, or EDAS be changed.

## 2026-10-06 DRC Evidence-Closure Continuation

- [complete] Recovered the current `version/v2` worktree with no unsynced
  planning state. The independent source controller is `MeshEchoDRC`; old
  SR/DHR/DCB policies remain controls and the ICC manuscript still reports
  the old 2.1.26 policy.
- [in_progress] Close the DRC evidence contract before any population claim:
  unified TX request/start/no-start ledger, per-receiver RX attempts,
  physical ACK provenance, stable application ordinals, bounded state
  snapshots, and fail-closed artifact validation.
- [pending] Add an independent DRC runner with frozen development/holdout
  manifests and same-trace paired controls. Run only a fresh mechanical
  smoke until the runner and audit pass.
- [pending] Execute development, apply the predeclared gate, and only if it
  passes execute untouched holdout. Recompute all numbers from raw artifacts.
- [pending] Rewrite the ICC LaTeX, figures, tables, limitations and
  reproducibility section from validated DRC results; compile and visually
  inspect the final PDF.
- [blocked-by-gate] Keep `VERSION`, GitHub, EDAS and final paper claims
  unchanged until the holdout and PDF audits pass. A failed DRC gate means
  retain the old paper or select a new evidence-backed core, not relabel old
  results.

### Runtime note

- The first full development invocation was stopped safely during the large
  RX-ledger audit after macOS swap usage approached its limit. Its partial
  artifacts are retained but invalid; no gate result was recorded. A future
  cohort run must stream or otherwise bound audit memory before retrying.

### Recovery checkpoint for automatic context compression

The authoritative continuation state is this section plus `progress.md` and
`findings.md`. If context is compressed, read all three files before coding.
The current decision is **not** to tune DRC on its sealed seeds. The next code
artifact must be a newly named CPR successor with public behavior tests before
any fresh population run.

## 2026-10-05 Matched D-Trigger Branch Implementation

- [classification] The preceding goal turn made authoritative progress:
  independent 493xx interpretation and a draft same-prefix branch contract
  were written and diff-checked. It did not implement the new algorithm.
- [complete] Recovered the current dirty worktree and checkpoint with the
  planning skill's `python3` catch-up; it reported no unsynced context.
- [in_progress] Independently audit the draft 494xx branch contract and
  map the current DCB/runner hooks before modifying behavior.
- [pending] TDD a nonreserved target-only D/R/F replay with exact prefix
  identity, role-keyed reception randomness, equal D-trigger bookkeeping,
  equal primary rescue budget and fail-closed physical/flow accounting.
- [in_progress] The first vertical slice is implemented: public D-trigger
  action overrides, role-separated reception/jitter keys, target-only D/R/F
  replay, cold-D arm omission, prefix state capture and artifact validation.
  Five focused tests pass; a mechanical 49400 smoke remains.
- [error logged] The first direct smoke invocation failed before simulation
  because the tool lacked a repository-root import path when executed as a
  script. No artifact was created; the entry-point path fix is applied.
- [pending] Run a mechanical smoke on a separate nonreserved seed and get
  an independent runner/contract audit. Freeze hashes and exact inputs only
  after correctness gates pass; 49401--49440 have not run.
- [pending] Execute the once-only exploratory branches, derive a truly new
  device-local source/feedback/recovery controller, then evaluate matched
  development and untouched holdout before revising the ICC manuscript.
  Preserve 47xxx/48xxx, old paper/PDF, VERSION, GitHub and EDAS meanwhile.

## 2026-10-05 Seven-Arm Diagnostic Continuation

- [classification] The preceding goal turn made authoritative progress: a
  DCB-wire useful-F-on-old-D-trigger control and a seven-arm physical capture
  tool with synthetic tests were added. It did not complete the new core.
- [complete] Session catch-up found no unsynced context. The dirty worktree
  and all pre-existing research artifacts remain preserved.
- [complete] `meshecho-dcb-source-trigger-f` is registered; its public
  behavior and wire/recovery checks passed 64 focused tests. The capture
  tool's 15 synthetic tests passed; the combined two-file check passed 18.
  Compilation and `git diff --check` passed. These are implementation checks,
  not performance evidence.
- [complete] Independent capture audit found two P1 and two P2 issues.
  RED/GREEN public tests now distinguish discovery timeout from candidate
  ACK timeout, preserve future-start TXs and packet arm/flow attribution,
  check raw/windowed/queued TX counts, exercise real seed-17 seven-arm CLI
  capture, and separate windowed TX from raw RX energy. The post-fix
  independent re-audit found no remaining scoped P1.
- [complete] The complete current test tree passed 1101 tests, one skipped
  in 177.00 s; the targeted diagnostic/control suite passed 28 tests.
  Compilation and diff whitespace checks passed. A real nonreserved seed-17
  seven-arm CLI smoke passed in the test suite. The exact 493xx fixed inputs,
  hashes and absence of an existing output artifact were checked.
- [complete] Executed the predeclared 49301--49310 seven-arm public
  diagnostic exactly once to
  `results/meshecho_source_action_public_49301_49310_20261005`.
- [complete] Independent read-only audit of the once-only 493xx archive
  passed all scoped identity, pairing, physical TX, flow, cost, ACK and
  interval checks: 70 runs, 2,793 flows and 35,574 physical TXs. There
  were no out-of-window TXs. Treat the contrasts as exploratory only.
- [decision] Rebuild the source action/feedback/recovery decision rule; do
  not present the DCB relay extension, D-to-R/F shortcut or reversible trial
  as a completed new core. Preserve the simulator and old arms as controls.
- [in_progress] Predeclare a same-prefix, same-wire D/R/useful-F branch
  experiment with matched source bookkeeping and recovery budget, then
  specify and test a genuinely new joint decision rule. No new seed has
  run for this branch experiment. Keep 47xxx/48xxx, ICC results/PDF,
  version, GitHub and EDAS closed.
- [draft complete] The target-only branch design is recorded in
  `docs/research/meshecho_d_trigger_matched_branch_design.md`. Its candidate
  49401--49440 exploratory seeds are not authorized until implementation,
  independent pre-run audit and exact hash freeze. The 493xx result note is
  `docs/research/meshecho_source_action_public_49301_49310_results.md`.

## 2026-10-05 Public Trial Screen Decision

- [complete] Ran the prospectively specified nonreserved 49201--49210
  five-arm screen once; the artifact is
  `results/meshecho_trial_public_49201_49210.json`. Fourteen physical
  trials across eight seeds, eleven ordinary trial ACK commits, and three
  source-guard abandonments pass the exposure-only screen.
- [NO-GO] Trial and blind switch had zero per-flow physical action/path
  divergence and zero ACK, delivery, or complete-network airtime difference
  on these ten seeds. This does not support the trial-specific reliability
  claim; do not freeze this trial controller or open reserved cohorts.
- [complete] The runner now has a separate trial-centered paired/exposure
  `trial_project_gate`; old DCB `project_gate` remains separate. Targeted
  DCB/runner tests passed 87 tests after provenance hardening. A full suite
  after these latest runner edits remains due.
- [in_progress] Diagnose why guard abandonment produced no subsequent
  physical divergence from blind, then design a genuinely new device-local
  source action/recovery controller with an explicit causal ablation. Keep
  47xxx/48xxx, ICC result changes, VERSION, GitHub, and EDAS closed.
- [complete] Structural diagnosis: trial and blind send the same next
  two-hop R; success converges their cache, and a miss triggers the same
  F recovery and subsequent F choice. An isolated interleaved-flow public
  witness does show path divergence when concurrent same-pair traffic is
  introduced, but the population screen did not exercise an effect.
- [complete] Full current-tree regression after runner audit: 1070 passed,
  one skipped in 166.81 s; diff whitespace check passed before the new
  test-only witness was added.
- [in_progress] Read-only calibration of certified direct-DATA/alternate
  ACK exposure in already-opened 46xxx artifacts. If a device-local trigger
  has enough support, predefine a selective split-ACK contract and same-wire
  controls, then implement one RED/GREEN protocol slice at a time.
- [complete] Archived 46xxx calibration found only 3/99 age-qualified
  nominated flows where direct DATA arrived but initial direct ACK did not.
  Current-DATA SINR was not saved, so the proposed quality trigger is
  unmeasurable there. Recorded `meshecho_selective_split_ack_triage.md`;
  reject this branch as the next full core rather than implement from an
  unvalidated threshold.
- [in_progress] Reframe the next core around the more exposed forward-DATA
  failure branch (36 age-qualified nominee decodes in 17 seeds), preserve
  proven old-D contribution as a control, and prospectively test source
  action/recovery decisions against simple same-wire alternatives.
- [in_progress] Predeclared nonreserved 49301--49310 seven-arm source-action
  diagnostic in `meshecho_source_action_public_diagnostic.md`. Implement a
  fail-closed capture/test loop, audit its fixed inputs, then run it once;
  use the resulting physical/flow evidence only to specify a new controller.
- [in_progress] Added a pre-run DCB-wire useful-F-on-D-trigger arm to
  distinguish expensive control-only D refresh from a payload-bearing
  route refresh. Implement/register/test it without changing old arms.
- [complete] Independent trial-runner audit found future-ACK and wrong-first-
  path provenance gaps. Public RED/GREEN tests now reject both; 89 DCB
  runner/protocol tests pass. Invalid provenance still intentionally aborts
  artifact creation; keep this fail-closed limitation explicit.

## 2026-10-05 Diagnostic Errors

- The host has no `python` command for session catch-up; `python3` completed
  successfully and reported no unsynced context.
- A four-file documentation patch used the wrong wrap around the energy
  sentence and failed atomically. After reading the exact lines, a narrower
  patch succeeded; no partial edit occurred on the failed attempt.
- A first `jq` query treated JSONL as one array and emitted per-line type
  errors; rerunning the read-only query with `jq -s` produced the intended
  130/99/52/0 aggregate. No file or cohort was changed by the failed query.
- A first seven-arm documentation patch failed because its expected line
  break did not match the file; rereading the exact lines and applying a
  narrower patch succeeded. No partial edit occurred on the failed patch.

## 2026-10-05 Trial-Core Resume

- [complete] Recovered the draft trial-core checkpoint and dirty worktree. The
  `python` catch-up command was unavailable on this host; `python3` succeeded
  without an unsynced-context report.
- [complete] Reproduced `lora_mesh_sim.py:3805` unmatched `)` after the prior
  commit-helper refactor, removed only the extra closing parenthesis, and
  passed compilation plus 100 neighboring DCB/DHR/DBR/SR/airtime tests.
- [complete] Independent review reproduced two stale-generation defects.
  Public tests went red then green: old R timeout after a newer F commit
  cannot taint that route; a newer F ACK cancels an older active trial.
  Route-expiry and source-LRU eviction boundary tests also pass.
- [complete] Runner now includes same-wire trial/no-switch/blind controls,
  trial event provenance audits, and a nonreserved positive fixture. Focused
  DCB/runner tests: 78 passed; full suite after the behavior fixes: 1040
  passed, one skipped. The two later test-only boundary fixtures pass.
- [in_progress] Independently audit the final staged matrix and quantitative
  gates, then decide whether a nonreserved mechanism screen justifies freeze.
  Preserve all unrelated dirty-tree changes.
- [planned] Once the runner P1 audit issue is fixed, execute exactly the
  nonreserved 49201--49210 public mechanism screen specified in
  `docs/research/meshecho_trial_public_mechanism_screen.md`; keep all
  confirmatory margins and 47xxx/48xxx closed during this diagnostic.
- [complete] Trace-backed review found the suspected trial-abandonment audit
  rejection unreachable for same-flow F recovery; cross-flow F commit passes
  the existing audit. Added two regression tests without relaxing the runner;
  combined DCB/runner suite now passes 80 tests.
- [in_progress] Drafted a separate trial-core gate in the trial contract,
  distinct from the old DCB component `project_gate`. Its physical exposure,
  paired endpoint, and holdout authorization logic still need implementation
  and independent review before any freeze.
- [NO-GO] The new source algorithm has no matched causal performance result.
  Do not open 47xxx/48xxx, revise ICC claims, bump VERSION, or publish yet.

## 2026-10-05 ACK-Gated Trial Core Phase

- [complete] Added `meshecho-dcb-trial` and same-wire
  `meshecho-dcb-trial-no-switch`; the candidate now has an independent
  F/R selector, pending one-flow path trial, ACK-only route commit and
  15-s guard abandonment. Public tests were red then green for each major
  new behavior and concurrent ACK correction.
- [complete] Focused DCB/SR/DHR/airtime regression: 74 passed; compile and
  diff whitespace checks passed. This is correctness only, not performance.
- [in_progress] Integrate trial/no-switch into the fail-closed draft runner,
  add same-source old-D and blind-promotion controls, and independently
  audit exact packet/state/action parity. A full current-tree regression
  remains due.
- [NO-GO] Inherited R/F miss sets and flood seen sets are unbounded; no
  whole-protocol MCU-memory claim. Do not freeze 47xxx/48xxx inputs or
  modify ICC, VERSION, GitHub or EDAS before matched development and
  untouched holdout validate the complete new algorithm.

## 2026-10-05 Source-Core Clarification

- [complete] Rechecked the current `MeshEchoSR.send_app` and DHR recovery:
  DCB and ACK-proven route promotion still inherit the old F/R/D selector
  and 15-s fixed-F rescue. Treat them as components, not a full rewrite.
- [complete] Post-promotion verification: 114 focused tests passed; full
  suite 1020 passed, one skipped; `git diff --check` clean. This is not
  performance evidence.
- [in_progress] Specify a device-local joint source/feedback/recovery rule,
  explicit same-wire controls and falsification gates. Do not assume a
  backup ACK means direct DATA failure; direct ACK loss is confounded.
- [NO-GO] Keep 47xxx/48xxx cohorts, ICC paper/PDF, VERSION, GitHub and EDAS
  unchanged until a frozen contract and causal result justify them.
- [complete] A public overlapping-flow test exposed stale blind promotion:
  a newer direct R ACK was overwritten by an older delayed backup ACK.
  Latest direct ACK flow tracking now prevents that; the targeted red/green
  test and two adjacent promotion tests pass.
- [in_progress] Drafted `meshecho_ack_gated_trial_source_contract.md` for
  a one-flow ACK-proven trial plus a replacement F/R selector. Implement
  one public behavior at a time, retain no-trial/old-D same-wire controls,
  and audit exposure before any 47xxx/48xxx run.

## 2026-10-05 Goal Continuation: DCB Evidence Completeness

- [classification] The immediately preceding goal turn answered the user's
  core-rewrite question but did not change authoritative state or produce new
  experimental evidence; treat it as no progress and continue the open goal.
- [decision] Preserve the simulator and baseline implementations, but do not
  treat the inherited F/R/D source controller plus DCB relay backup as a
  complete ICC-ready core rewrite. Independently specify a joint source/
  feedback/recovery decision rule while testing DCB as a candidate.
- [progress classification] The previous goal turn changed authoritative
  code, tests and the pre-freeze decision; it was progress, not a status-only
  turn. Full DCB objective remains open: core causal experiment and major ICC
  paper revision are not done.
- [complete] Add DCB-only per-committed-TX request/start queue records,
  aggregate wait statistics over TXs starting by 630 s, and an artifact audit
  that verifies every queue record joins one physical TX and its wait
  arithmetic. Keep the shared simulator/RNG behavior unchanged.
- [complete] Record peak concurrent feedback windows per destination,
  peak pending backups per relay, and inherited seen-set size per node;
  preserve an honest note that the seen set itself is unbounded.
- [complete] Persist committed request events separately from physical
  TXs and state open/close events so artifact audits can reconstruct peaks
  rather than merely check caps and row sums. Re-run full tests after all
  edits; the 1010-pass run began before the last test additions.
- [pending] Finish independent observability review and full regression,
  then implement the missing named controls before any DCB source freeze.
- [complete] Independent observability re-audit found no scoped P1/P2 and
  verified nonreserved TX/flow/RNG parity. The completed post-observability
  full suite passed 1011 tests with one skip; syntax and diff checks passed.
- [in_progress] Added a per-F TTL-2 fixed-two-hop control and registered it
  with SR-FR/LPR as contextual arms; added a DCB-wire source-FR arm as a
  source-controller control. The nine-arm nonreserved fixture and focused
  tests pass. Complete the remaining matched controls and pre-freeze audit.
- [source-core decision] Do not freeze the proposed simple no-D controller:
  archived stock data include 70 D decisions and 61/64 timely ACKs among
  exported D-candidate flows. Specify and test a full source action matrix
  with D retained as a comparator, then require real action divergence and
  same-budget causal gain before replacing the ICC method.
- [in_progress] Independently map additional source R/F, R-F, two-hop F and
  LPR-like controls to actual implementations and budgets before changing
  the staged arm matrix. No 47xxx/48xxx seed may run while the contract is
  not frozen.
- [pending] Re-run focused/full tests and independent pre-freeze audit;
  only then freeze exact inputs, create smoke-only authorization and run one
  47000 mechanical capture. Development, holdout and ICC rewrite depend on
  their predecessor evidence gates.

## 2026-10-05 DCB Continuation Check

- [NO-GO pre-freeze] Independent review found DHR's inherited active-flow
  state was created at enqueue/commit time even when physical R DATA start
  was later. A red public test reproduced it. DCB now defers the complete
  initial-R protocol activation until physical start; a second red/green
  test prevents scheduling a cleanup timer in the past when start exceeds
  the original 30-s deadline.
- [complete] Direct CLI execution previously used a distinct `__main__`
  authorization token; a red subprocess test reproduced the dispatch error
  without opening any reserved seed. The entry now calls canonical module
  `main`; adjacent 264 tests, compilation and `git diff --check` pass.
- [NO-GO contract completeness] The current five-arm runner does not include
  all additional simple controls promised by the draft contract, nor does it
  report per-packet queue wait or peak feedback/pending/seen-set state.
  Resolve these honestly before freezing. No 47xxx/48xxx seed may run yet.
- [complete] Final full regression after timing/CLI corrections: 1007 passed,
  one skipped in 162.48 s. Keep the ICC paper, version and GitHub unchanged
  because the evidence contract remains NO-GO for freezing.

- [complete] Recovered the DCB checkpoint and confirmed that the intended
  rewrite replaces destination feedback and relay backup decisions while
  retaining the simulator and the inherited F/R/D source controller. This
  remains a candidate, not a verified complete algorithm or ICC result.
- [complete] The exact ACK/relay-timer ordering test and adjacent DCB,
  packet-airtime, DHR, and DBR tests passed (60 tests). A fresh public flow
  test confirmed 120-s backup certification expiry while the direct route
  remains cached.
- [complete] Added a red/green rejection-cause test for a physically wrong
  ACK sender; the source now records the reason without accepting the ACK.
  A public late-ACK test also confirms no confirmation after the original
  30-s deadline. Simulator-inclusive full regression excluding the active
  DCB runner test module passed 982 tests with one skip in 161.96 s.
- [complete] A new red/green backup-DATA identity test prevented the
  destination from counting a marker-4 packet with mismatched request/flow
  IDs as delivery. The five-arm fail-closed staged runner is complete; its
  nonreserved fixture and focused tests passed. Full current regression:
  1005 passed, one skipped in 162.00 s; Python compilation and
  `git diff --check` passed.
- [in_progress] Independent pre-freeze audit of protocol and runner. Do not
  mark the contract frozen or open the 47000 smoke until it returns GO and
  exact source hashes/authorization are reviewed.
- [in_progress] Add remaining sender/deadline rejection tests, inspect the
  staged runner, run full regression, and freeze the causal inputs before
  considering the 47000 mechanical smoke. Reserved 47xxx/48xxx seeds remain
  unopened, and paper/PDF/version/GitHub/EDAS remain unchanged.
- [environment] The recovery helper first failed because `python` is absent
  on this host; `python3` completed successfully with no unsynced context.
- [test fixture correction] The first LRU-eviction test put extra nodes
  beside the four-node proof topology, perturbing the initial FLOOD and
  preventing trial creation. Moving only those additional destinations far
  away restored the intended physical precursor; both boundary tests pass.
- [runner RED] The in-progress five-arm artifact test raised the runner's
  intentional `NotImplementedError` after 265 adjacent tests passed. The
  runner agent owns that vertical slice; do not treat it as a simulator
  regression or open a reserved cohort before it is green and audited.

## 2026-10-05 Continuation Error

- A multi-file contract patch initially failed because its expected line
  wrapping did not match the current source. No file changed on that attempt;
  the replacement used exact context after rereading the target files.

## 2026-10-05 Active DCB Prototype Phase

- [complete] Audit 46xxx passive opportunity and preserve the clean frozen
  source snapshot; interpret its 5.528% only as a prototype-permission bound.
- [complete] Specify device-visible DCB contract, same-budget current-
  overhearing control, exact new cohorts and quantitative causal gates.
- [complete] TDD on-wire extension and first destination/source feedback
  slices, with ten focused tests passing.
- [in_progress] Implement relay current-packet reception, bounded timer and
  ACK suppression, backup DATA/ACK validation, state/overflow rules, and
  matched control variants one public red/green test at a time.
- [in_progress] Resolve independent review gaps: bounded-state wording,
  full rejection-cause logs, F overflow and malformed-packet tests, one-shot
  retention, busy-radio and same-time ordering tests.
- [in_progress] A separate agent is adding the DCB staged causal runner and
  tests without opening any reserved cohort.
- [pending] Full regression, source freeze, mechanical 47000 smoke, fresh
  paired development, untouched holdout only on a development pass.
- [pending] Rewrite ICC LaTeX/PDF from verified positive evidence, visually
  inspect five pages, then consider versioned publication separately.

## 2026-10-05 Prototype Test Errors

- Direct-ACK cancellation test failed because the nominated relay did
  physically decode the ACK, but off-path ACK filtering returned before
  local overhear recording. Reordered local recording before path forwarding
  validation; adjacent tests passed.
- Unconditional-control count test saw two marker-4 transmissions from the
  relay, one DATA and one reverse ACK. The test now filters DATA explicitly;
  protocol behavior was correct.
- Malformed F/backup-path and duplicate-R red tests exposed real acceptance
  and one-shot defects. Fixed each at its validation/state source and kept
  the failing scenarios as regression tests.

## Current Active Objective (2026-10-04)

Rewrite the MeshEcho-SR decision/recovery core as a device-observable,
prior-art-aware algorithm; test it against matched simple controls on fresh
development and untouched holdout seeds; only then replace the five-page ICC
paper's method/results and consider a versioned GitHub update. Retain the
current simulator and old protocols as infrastructure and comparators. The
AFS relay component completed frozen development and failed the source-ACK
noninferiority gate; it is not a complete new core.

Current status: the frozen fixed-2-s FLOOD ACK control completed one 38000
mechanical smoke and 38001--38020 exploratory paired comparison, both with
strict replay and independent artifact audit. It improved source-ACK PDR by
+0.2251 [95% CI +0.1725, +0.2777] and reduced per-seed relative whole-
network airtime by 16.73% [11.22%, 22.24%] against immediate fixed-F in
the inspected recurring-fading workload. This is a strong **simple
comparator**, not the requested new algorithm or untouched confirmation.
The next step is to identify a distinct device-observable ACK and source/
recovery contract that can beat this comparator and same-budget repeats,
with prior-art checks and fresh prespecified development/holdout evidence.
See `docs/research/meshecho_delayed_ack_control_explore_results.md`.
The next bounded research question and provisional FINER/scope screen are in
`docs/research/meshecho_feedback_core_rq.md`. The local-signal and source-
controller screens do not justify a quiet-window ACK as a full core rewrite;
diagnose residual ACK failures before selecting a new source/feedback contract.
No new behavior or seed is authorized by the scoping question alone.
The subsequent read-only residual screen is complete: most remaining
source-ACK misses followed on-time destination ACK transmission, not
deadline expiry. This continuation is evaluating complete, device-local
source/feedback/relay contracts against fixed-2-s and same-budget repeat;
the old calibrated paper and all sealed cohorts remain unchanged.

Current continuation gate: BAR already failed to distinguish alternate-
path extra ACK from same-trigger same-path repetition. The preregistered
39xxx passive ACK-receive diagnostic is now complete and independently
audited: only 1/47 delivered-unACKed FLOOD flows had a valid in-deadline
off-index source ACK decode, failing both necessary exposure thresholds.
Reject off-index ACK acceptance as the full new core. Complete and audit
the 40xxx short-source-guard and 41xxx same-path-repeat simple controls,
then select a device-observable joint source/feedback/recovery contract
that can beat them. Neither a diagnostic nor a simple control is itself
the requested algorithm rewrite. Paper/PDF/version/GitHub/EDAS and sealed
35001--35040/36001--36040 remain unchanged.
`docs/research/meshecho_joint_core_candidate.md` now records a complete
but untested JFC protocol hypothesis with device-visible fields, source
states, same-budget controls, and no-go gates. BAR/MAG/DRC prior negative
results make its spatial ACK and one-miss source elements high-risk;
do not implement it as a positive ICC core merely because the contract
is complete. Review the passive ACK-RX screen and fixed-delay repeat
control first, then decide whether JFC has a distinct exposed advantage
or needs replacement by a stronger source-feedback mechanism.
Two new simple controls are under test: fixed-2-s FLOOD ACK plus one
same-path repeat (`docs/research/meshecho_delayed_ack_repeat_control_design.md`,
41000 smoke / 41001--41020 exploration) and physical-R-TX-start guards
of 1/2/4/8 s against the inherited 15 s
(`docs/research/meshecho_delayed_ack_short_guard_design.md`, 40000 smoke /
40001--40020 exploration). New runners must freeze current source hashes
and independently replay unchanged baseline behavior; the archived
38xxx runner cannot accept changed simulator hashes as its original smoke.

## 2026-10-04 Current Scheduler and Simple-Control Smoke Freeze

- [complete] The same-time ACK/guard red test is green after ordering physical
  `tx_end` before protocol timers and `tx_request` after them. Three additional
  public boundary tests cover RREQ collection, RREP discovery, and SmartCalm
  ACK completion at exact timer ties. The current full suite passed 675 tests
  with one skipped; Python compilation and `git diff --check` passed.
- [decision] This is a shared event-scheduler semantic change. All new arms
  must be compared against stock protocols on **this** source hash, not pooled
  with pre-change 38xxx/39xxx data. Historical frozen artifacts remain valid
  only for their original versions.
- [complete] Independent read-only pre-smoke audits gave GO for exactly one
  40000 short-guard smoke and one 41000 repeat smoke. They did not open any
  reserved seed. Explore cohorts remain closed pending separate smoke
  artifact and strict-replay audits.
- [frozen-before-40000] Short-guard input SHA-256 values:

| Input | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `165fff13ac3839045b41bf39a8e9451503c50e0c66ca4cc39c92709e5eaf2875` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `f61b2bccb154c7ec3f7603c51dd47ff2b8271d68db4baa69e2ccee5a4a1d0d1c` |
| `tools/run_delayed_ack_short_guard_control.py` | `a50aea0968debbf41640d601aa51332402147190aa07169e92cef9c0b9eea185` |
| `docs/research/meshecho_dhr_design.md` | `862e7f307db6ac992235e90c34bfb7e3793e69d3168ee91d133d1db636a26d59` |
| `docs/research/meshecho_delayed_ack_control_design.md` | `86396835b850d9dfd7fc5753acb414a5c12208aafba1e9602fe0dca93c1d8441` |
| `docs/research/meshecho_delayed_ack_short_guard_design.md` | `3d7696dbf4dea4d6d74cb9d1fa6c58039ea3efd828aa038615efc5a15746c8ea` |
| `tests/test_meshecho_dhr.py` | `0f6825b1bae3222a1bd6a2275f515887087600f27d055de7cf9b8e0e31d1d7b8` |
| `tests/test_delayed_flood_ack_control.py` | `ff0a75b45617a92883d2665549c70d2c0f1598f096077194abef644b1a344bda` |
| `tests/test_delayed_ack_short_guard.py` | `f7752a8f33f0e15b4c9d9a375770979fccd510122ce646263a5b6295ae3c42a3` |
| `tests/test_delayed_ack_short_guard_runner.py` | `170237398aeca756c70d8d0ae9a48e9787b4a6c74798a9bd99220aaf89b09b04` |
| `tests/test_delayed_ack_short_guard_experiment.py` | `66eebf7cc3e63588df0187350c71f346262000f5e9c70df783138a6fcc61800b` |

- [frozen-before-41000] Same-path-repeat input SHA-256 values:

| Input | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `165fff13ac3839045b41bf39a8e9451503c50e0c66ca4cc39c92709e5eaf2875` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `f61b2bccb154c7ec3f7603c51dd47ff2b8271d68db4baa69e2ccee5a4a1d0d1c` |
| `tools/run_delayed_ack_repeat_control.py` | `df95af5416505ce474cf9107537c5ecfadc0d51013f7bc8fe111ca81960e2e46` |
| `docs/research/meshecho_delayed_ack_repeat_control_design.md` | `78c106d4acdc8b78dcce26c716021d7eb0aad18829be9dc9285286e4dde1e9e8` |
| `tests/test_delayed_ack_repeat_control.py` | `95ca717e84b7573cf4ba1956f4efc7c7c6c4e164cff36e3397b90ada628a12f2` |
| `tests/test_delayed_ack_repeat_runner.py` | `9467a494a497ad6198b1aa73612a397870c2efd4a75dac1d28b6035fd0406f20` |
| `tests/test_delayed_ack_repeat_runner_experiment.py` | `caa56bdb7a41e4a3756cb15a4f06f30b313001786229b1e492f77fa687dac2a3` |

- [NO-GO] The first 40000 and 41000 mechanical smoke commands completed,
  but independent saved-artifact validation found a physical-byte replay
  mismatch. JSON turns packet `path` and `learned_path` tuples into lists;
  both runners reconstruct `Packet(**saved_packet)` without normalizing
  them, so `wire_size_bytes` falsely charges a RREP's redundant reverse
  learned path. For 41000 this is exactly +69 reconstructed bytes per arm;
  for 40000 it is +95 or +108 bytes by guard arm. This is a runner reload
  defect, not a claimed protocol effect. Both first-smoke artifacts are
  preserved and neither exploration cohort may open from their manifests.
- [in_progress] Add a saved-JSON red regression, normalize reconstructed
  packet tuple fields in each runner, rerun all relevant tests, freeze the
  *new* hashes, then use distinct new output prefixes for one corrected
  mechanical smoke per runner. An independent audit must pass before either
  40001--40020 or 41001--41020 opens.
- [complete] Both runner reload fixes had a failing JSON round-trip RREP
  regression before implementation and passed their focused suites after
  normalizing `path` and `learned_path` to tuples. The shared simulator and
  physical protocol were not changed. Full current suite: 677 passed,
  one skipped; `git diff --check` passed.
- [frozen-before-40000-v2] The 12-entry 40000 input table above remains
  identical except exactly these two entries. This fully specifies the
  second freeze; all other ten listed hashes were rechecked unchanged:

| Input | SHA-256 |
| --- | --- |
| `tools/run_delayed_ack_short_guard_control.py` | `bfd59ff4a8ad2bcefd73b62c0227ac756555698a8c01e3c81e7ee78f9d347c60` |
| `tests/test_delayed_ack_short_guard_runner.py` | `79573b784b31dcaca9cfcd5724f49664fa6c18137f785270c4f6d12bb814dea9` |

- [frozen-before-41000-v2] The 8-entry 41000 input table above remains
  identical except exactly these two entries. All other six listed hashes
  were rechecked unchanged:

| Input | SHA-256 |
| --- | --- |
| `tools/run_delayed_ack_repeat_control.py` | `031a82ff0b56a0ed43617b38594202cbc800b2b199424a54b5333dccbc84e798` |
| `tests/test_delayed_ack_repeat_runner_experiment.py` | `c7370485d3ccf4be33dc18894c1c12c3662b00b0e45e56862fb1846e68455736` |

- [complete] The corrected 40000-v2 and 41000-v2 mechanical smokes used
  distinct new prefixes; each `.runs.csv` is byte-identical to its first
  smoke, confirming the runner repair did not alter simulation outcomes.
  Independent audits verified all 12/8 frozen input hashes and 10/11 data
  artifact hashes respectively, official strict manifest replay, stock
  current-code baseline parity, physical guard/ACK timing, and 630/660-s
  full-TX accounting. Neither had post-630 transmissions. Manifests:
  `results/meshecho_delayed_ack_short_guard_smoke_seed40000_v2_20261004.manifest.json`
  and `results/meshecho_delayed_ack_repeat_smoke_seed41000_v2_20261004.manifest.json`.
- [GO] Open exactly 40001--40020 and 41001--41020 once via their respective
  v2 smoke manifests while all frozen inputs remain unchanged. These are
  exploratory simple controls, not a new core or confirmation cohort;
  35001--35040 and 36001--36040 remain sealed.
- [complete] The 41001--41020 same-path-repeat exploration completed once
  under the v2 smoke gate. Independent audit verified all 8/8 frozen inputs,
  11/11 artifact hashes, every all-flow denominator and physical repeat,
  current-code stock parity, and strict replay of all 40 arm runs. Repeat
  minus fixed-2-s single ACK: paired ACK-PDR +0.01956 (nominal 95% CI
  +0.00012 to +0.03899), destination PDR -0.00572 (-0.01146 to +0.00002),
  relative whole-network airtime +1.769% (-2.891% to +6.429%). It is a
  strong simple comparator, not a new core or holdout result. Manifest:
  `results/meshecho_delayed_ack_repeat_explore_41001_41020_20261004.manifest.json`.
- [NO-GO pending diagnosis] The one planned 40001--40020 short-guard
  execution reached result assembly but wrote no artifact: its own
  `audit_guard_contract` raised `missing R guard after physical R TX start`.
  Do not reuse that failed execution as data, bypass the guard, or rerun
  the full cohort unchanged. Locate the first seed/arm/flow and determine
  whether the protocol or audit contract is wrong, write a red public
  regression, and refreeze before a new named run only if justified.
- [root cause] The first failure is seed 40005, guard2, flow 19: initial
  decision D at 287.021964 s, RREQ, then RREP timeout and fallback R DATA
  at 300.327308 s. DHR's short guard intentionally applies only when the
  original action and transmitted DATA are both R; inherited D-to-R
  fallback instead has the normal 15-s source ACK timeout. The runner
  incorrectly inferred initial R from final `flow.source_action=R` and
  demanded a guard at 302.327308 s. This is an audit classification false
  positive; initial behavior and source ACK remain unchanged. Add a strict
  decision-event classifier and red D-to-R test; clarify the design, then
  refreeze/re-smoke. The opened 400xx cohort stays exploratory, never an
  untouched replicate after a quality-control rerun.
- [complete] TDD audit fix now joins each final routed DATA flow to a unique
  logged initial decision, records `guard_scope` for D-to-R fallback, checks
  its inherited 15-s timeout when observable, and still rejects missing
  guards on true initial-R flows. Actual seed 40005 guard2/flow19 preflight
  passes without changing protocol behavior. Three new regression cases,
  29 focused tests, full 680-pass/1-skip suite, compilation, and diff check
  passed. Independent read-only pre-smoke re-audit gave GO for one new
  40000 mechanical smoke under new hashes. All eight 41xxx frozen inputs
  remain unchanged.
- [frozen-before-40000-v3] The 12-entry 40000-v2 input set above remains
  identical except these three entries; all other nine were rechecked:

| Input | SHA-256 |
| --- | --- |
| `tools/run_delayed_ack_short_guard_control.py` | `5b73ae522ac2fff21fda4927f36347af8d17293248decde8e73db95f832b967f` |
| `docs/research/meshecho_delayed_ack_short_guard_design.md` | `038c333f6b36f2d4b065f8545d0a41f6c3a4a88fc968d7131c2ea3d0a71156d8` |
| `tests/test_delayed_ack_short_guard_experiment.py` | `e783025b8c808cccc072fda0f1e752dd9c1c9bd5fb0323d0742992b6c86f9001` |

- [next] Run a single new 40000-v3 mechanical smoke at a unique prefix,
  independently audit its official strict replay and D-to-R evidence,
  then perform a documented quality-control rerun of the already-opened
  40001--40020 exploratory cohort. Never label that rerun independent
  confirmation. Keep all earlier failed-run and smoke provenance.
- [complete] The 40000-v3 mechanical smoke ran at
  `results/meshecho_delayed_ack_short_guard_smoke_seed40000_v3_20261004.manifest.json`.
  Independent audit matched all 12 frozen inputs and 10 data artifacts,
  official strict replay, live current-code stock parity, 36 all-flow
  denominators per arm, physical 15/1/2/4/8-s guards and 630/660-s costs.
  There was no post-630 TX. This seed has no D-to-R fallback, so targeted
  tests and the next cohort's saved flow evidence must check that case.
- [GO] Run exactly one quality-control rerun of the already-opened
  40001--40020 exploratory five-arm cohort via the v3 smoke manifest and
  a new output prefix; require explicit 40005 guard2 flow19 D-to-R scope,
  physical start+15-s timeout, no DHR guard/recovery, and strict replay.
  The earlier aborted cohort wrote no artifact and is not an independent
  sample. Do not open sealed 350xx/360xx seeds.

## 2026-10-04 Passive ACK-RX Diagnostic Freeze

- [complete] Independent read-only audit found no blocker to **39000 only**;
  all 13 focused tests passed. The runner compares the stock and passive
  recorder's complete metrics, flow/action/TX traces, and both RNG states.
- [frozen-before-39000] Input SHA-256 values:

| Input | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `ca21f85cbeb360ff4dee5fbb5282653b30f5bdff91c57b7b7bdca3edf94053e4` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `f61b2bccb154c7ec3f7603c51dd47ff2b8271d68db4baa69e2ccee5a4a1d0d1c` |
| `tools/diagnose_flood_ack_hops.py` | `b587af3f48f8c1de2c3896be00e3603e3d34516ace893eec06419bddbd3c243f` |
| `tools/diagnose_ack_failure_causes.py` | `777c83db614758855418618ea39ba115640b454b133f37f9f73e076785dd06b5` |
| `tools/diagnose_delayed_ack_rx.py` | `7493ee072697845673ee66fbe7a2c537f247e1ac1f43733043d094906d16e4c1` |
| `tests/test_delayed_ack_rx_diagnostic.py` | `85b984e4128b367ae10fd478f284934a73053397a32c5869a72ed169db2a1746` |
| `docs/research/meshecho_delayed_ack_rx_diagnostic_design.md` | `ac5fcf6c1c9183264a6b1aced812256d913e0a330da5952feaf358b9b182c1ba` |

- [complete] One 39000 mechanical smoke ran at
  `results/meshecho_delayed_ack_rx_smoke_seed39000_20261004` under these
  exact input hashes. The manifest reports exact stock parity, 25/25
  deadline source ACKs/deliveries, 56 expected-next-hop ACK receive attempts,
  and 31 source off-index attempts. It has zero delivered-unACKed flows, so
  it is a mechanical check only, not a mechanism estimate.
- [complete] Independent 39000 audit checked all eight input hashes and seven
  artifact hashes, passed `validate_smoke_manifest`, recomputed 25/25
  delivery and ACK plus 87 ACK receive attempts, and matched one strict
  deterministic replay including both RNG states and canonical action/TX
  traces. GO for the exact 39001--39020 exploratory cohort while frozen
  inputs remain unchanged. The smoke has no delivered-unACKed FLOOD flow.
- [complete] Ran the exact 39001--39020 exploratory cohort once through the
  smoke-manifest gate. An independent audit verified all eight frozen input
  hashes, seven artifact hashes, the smoke manifest link, all 816 scheduled
  flows/per-seed denominators, saved attempt/flow/action/TX reconciliation,
  and strict deterministic replay of all 20 runs. Deadline destination
  deliveries were 810/816 and source ACKs 763/816. Of 47 delivered-unACKed
  FLOOD flows, one had a valid in-deadline off-index source ACK decode
  (1/47=2.13%; seed 39007 flow 18), below both preregistered >=4-flow and
  >=10% necessary gates. **NO-GO** for this branch as the full core. First
  failed ACK-hop causes: 23 capture collisions, 2 half-duplex, and 22
  probabilistic failures without interference; 36/47 had a final reverse
  ACK TX by deadline. `flood_ack_path_categories` counts ACK attempts;
  every failed flow here has one such attempt, so 25 direct/22 multihop
  also equal the distinct-flow counts in this cohort.
- [next] Use the audited physical-failure distribution to evaluate the
  strong simple 40xxx and 41xxx controls. Do not promote an off-index
  acceptance, quiet-only timer, or the untested JFC hypothesis to the ICC
  manuscript; choose a new full source/feedback/recovery contract only
  after the simple-control frontier is measured.

Earlier diagnostic context: the frozen 37000 ACK-cause smoke and
predeclared 37001--37003 exploration passed independent artifact audits.
The strict post-delivery `ACK_INTENT`/quiet/cancel opportunity is only
1/24 deadline-delivered/unACKed flows (4.17%), failing both preregistered
necessary gates (>=4 flows and >=10%). **Reject this branch before
protocol coding**. Two earlier independent design screens also found
no defensible complete new core contract: a hop switch is a simple
control, while source STATUS/relay-cache repair cannot cheaply resolve
missing DATA versus missing ACK or duplicate repairs and overlaps
DSR/ExOR-like prior art. Do not code or claim these as new algorithms.
The earlier phase tested whether a bounded, locally observed reverse certificate
can reach the source at lower cost than ordinary same-path ACK repetition.
The source-side observability audit is complete: a DATA loss and a delivered
DATA with lost reverse ACK can give identical source histories through the
15-s guard, so no source-only timeout rule on current packets can classify
the cause. Any new source policy needs an added source-decoded destination
certificate or must explicitly act under that ambiguity. Require a
packet/state/timer contract that materially differs from existing
priority forwarding, fixed delay, fixed R-F, same-path ACK repeat, and
old SR/DHR. If a credible contract exists, predeclare fresh development
and untouched holdout tests before implementation; otherwise document the
gap and evaluate a narrower systems/evaluation-paper pivot with the user.
Both screens completed negative pre-code feasibility checks: source ACK
silence is not a forward/reverse loss label, and the apparent 1.3-s ACK
slot is fitted to inspected paths while an analytic six-hop bound is
~9.38 s before queueing. Do not code these rules or open reserved seeds
on that basis. A separate read-only short-ACK-flood/corridor screen found
only a conditional timing opportunity, not a validated new core: delaying
a destination ACK by 2 s would follow the old same-flow FLOOD tail in
18/21 F-first delivered/unACKed flows, but the opened artifacts lack relay
reception histories needed to establish a device-observable reverse
corridor or its airtime. Lee et al. 2020 already describe multipath DATA/ACK
flooding with ACK-copy waiting. An independent audit invalidated the draft
unchanged-baseline corridor no-go gate: a 2-s ACK delay itself changes
pre-ACK FLOOD decodes. The draft is marked superseded without code or 38xxx
seeds. First implement and compare a simple fixed-2-s delayed single-ACK
control. A corridor must then beat that control and same-path repetition;
neither timing nor corridor alone is the source-controller replacement.
Do not fit or claim a new algorithm from five exploratory seeds.
The previous phase specified test-first implementation and audit of the fixed-delay
single-ACK control under
`docs/research/meshecho_delayed_ack_control_design.md`, then one mechanical
38000 smoke and a frozen 38001--38020 exploratory paired comparison. Do not
code ACK_FLOOD or change the paper from that simple-control result alone.
The protocol-side control and three focused tests were implemented;
focused tests passed. The exploratory runner was implemented separately.
The first full-suite attempt saw only a concurrent runner-module import
error while that file was still being created; rerun after handoff, then
independently audit hashes/parity before opening seed 38000.
Core-side independent audit found no behavioral blocker and exposed two
accounting/runtime issues. Root fixed DHR-family classification for the new
arm and made `Simulator.run(until)` preserve its first future event, each
with a red-green regression test. Eight focused delayed-ACK tests and 194
existing SR/DHR tests passed. At that point the runner was still in progress
and no 38xxx seed had been opened.
The paired runner audit defects have been repaired with adversarial tests,
receipt/ACK reconstruction, and strict deterministic replay. Root's stable
full suite passed 596 tests (1 skipped); syntax and diff checks passed.
Independent read-only re-audit found no blocker. The nine input hashes below
were frozen before the one permitted 38000 mechanical smoke. The smoke,
strict replay, and independent artifact audit passed; the predeclared
38001--38020 exploration subsequently completed. The 660-s window remains bounded sensitivity,
not all eventual airtime. This control is not a rewritten core algorithm.
The ACK-cause tool's 15 focused tests and 569-pass full suite passed
before its source hash freeze. The older 340xx branch artifacts summarize
post-target costs but need deterministic replay to recompute exact packet
costs independently.
35001--35040 development and 36001--36040 holdout remain sealed. AFS
failed source-ACK noninferiority and is not the core; Meshtastic already
has similar ACK cancellation. The new algorithm must replace the old
source decision/recovery rule rather than tune its threshold. Do not freeze
a budgeted source rule or change the ICC manuscript/PDF, VERSION, GitHub,
or EDAS until a genuinely new core passes matched controls on fresh
development and untouched holdout evidence.

## 2026-10-04 Joint-Core Prior-Art Quick Brief

- [complete] Answer the bounded research question: under the existing
  30-s deadline and complete TX-airtime accounting, is there a locally
  observable MeshEcho mechanism that jointly handles R forward loss and
  reverse ACK loss while differing materially from fixed R-F plus a
  same-path second ACK?
- [complete] Verify 5--8 directly relevant literature/product sources
  with exact claims and counterexamples. Inspect only current code and
  already-opened exploratory artifacts; do not open 35001--35040 or
  36001--36040, run new simulation seeds, or change paper/VERSION/remote.
- [complete] The targeted eight-paper prior-art check verified identifiers
  and bounded claims; immediate LoRa ACK, multipath ACK waiting, prioritized
  forwarding, and ACK-triggered queue cancellation have close precedents.
  A narrow combined mechanism still needs an exposure and distinct-control
  test; absence of an identical search hit does not establish originality.
- [complete] Independently review the test-first, unchanged-protocol
  ACK-failure-cause recorder against the preregistered contract. Only after
  focused/full regression, exact baseline replay, source-hash freeze, and
  artifact checks may seed 37000 run as mechanical smoke. Keep 37001--37003
  closed until that review passes, and keep 35001--35040/36001--36040 sealed.
- [decision] Independent pre-code screen rejects ACK_INTENT/quiet/cancel as
  a full source-plus-reverse core at present. Only the predeclared 37xxx
  necessary-exposure gate can reopen it as a conditional component. Any
  implementation must additionally establish local intent decode and
  uncommitted pending-handle reachability, compare equal-cost controls,
  and replace the source decision rule separately.
- [resolved-before-smoke] Independent tool review found a deadline exposure
  bug: a DATA flow delivered by 30 s could count a same-flow ACK collision
  whose first failed ACK hop occurs after its deadline. The strict/broad
  quiet-window opportunity must exclude post-deadline failed hops; add a
  red/green synthetic test and rerun validation before any 37000 smoke.
- [resolved-before-smoke] Strengthened the preregistered necessary bound
  before any new seed: the failed ACK hop plus zero-queue ToA for remaining
  reverse hops must fit the original 30-s deadline. The saved report must
  include a complete compact TX timeline to verify sole-overlap claims.
  These are audit-driven conservative refinements, not results-driven
  tuning; both require red/green tests and re-review before smoke.
- [complete] Audit fixes passed 15 focused tests and root's independent
  full suite (569 passed, 1 skipped). A separate read-only reviewer found
  no remaining blocker to mechanical smoke; gate interpretation remains
  optimistic only. Seven input hashes were frozen before seed 37000:

| 37000 smoke input | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `4d51d09660f06b536cbc2939e0d9410e405786b899c3f12818afacab41d00b23` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `ac12adf568714e766cff2efd67b1ba2ab6d1fc9ca4530cdd5f195e3d7f3c21b7` |
| `tools/diagnose_flood_ack_hops.py` | `b587af3f48f8c1de2c3896be00e3603e3d34516ace893eec06419bddbd3c243f` |
| `tools/diagnose_ack_failure_causes.py` | `777c83db614758855418618ea39ba115640b454b133f37f9f73e076785dd06b5` |
| `tests/test_ack_failure_causes.py` | `b11a50a6e4c5109435eae824a3255e8f9ebeb73ffefb1eaf2b7efa984d088d8c` |
| `docs/research/meshecho_ack_failure_cause_diagnostic_design.md` | `53c3118754136f74e766f2c0fa8e5fba2cf3d22bdb7cbdb7eac506710e24be11` |

- [complete] Seed 37000 mechanical smoke ran once with the frozen seven
  inputs. Plain/instrumented complete TX hashes and scheduled traces match,
  as do exact source actions and per-flow timestamps. The saved report and
  manifest SHA-256 agree; all 12 failed ACK-hop overlap sets recompute
  from the 648-row compact TX timeline with zero discrepancy.
- [smoke observation only] Ten deadline-delivered flows lacked a source
  ACK; 12 emitted ACK attempts first failed physically (9 capture, 3
  probabilistic with no interference). One flow had a sole same-flow
  post-delivery FLOOD overlap, but its TX commitment preceded the earliest
  possible 11-byte intent completion. Strict eligibility is 0/10. This
  does not apply the exploratory gate or establish an effect estimate.
- [complete] With the mechanical audit passed and frozen inputs unchanged, run
  the predeclared 37001--37003 exploratory split once. Apply the fixed
  >=4 unique flows and >=10% deadline-delivered-unACKed exposure gate;
  reject this ACK-quiet branch if either condition fails. Preserve
  35001--35040 development and 36001--36040 holdout sealed.
- [complete] No qualifying ACK_INTENT candidate: the independently
  audited strict trigger appears in only 1/24 relevant flows and fails
  both necessary exposure thresholds. The concrete observability gap is
  that post-delivery feedback cannot reach or cancel enough of the
  already committed/in-flight same-flow FLOOD interferers, while source
  timeout cannot separate forward DATA failure from reverse ACK failure.
  The negative result is in
  `docs/research/meshecho_ack_failure_cause_results.md`.

The historical plan and checkpoints below remain for provenance.

## 2026-10-04 Source-Branch Smoke Input Freeze

Seed 34000 only; prefix
`results/meshecho_source_branches_smoke_seed34000_20261004` was absent
before execution. All 15 focused diagnostic tests, 554 full-suite tests
(1 skipped), and `git diff --check` passed before the freeze.

| Input | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `4d51d09660f06b536cbc2939e0d9410e405786b899c3f12818afacab41d00b23` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `ac12adf568714e766cff2efd67b1ba2ab6d1fc9ca4530cdd5f195e3d7f3c21b7` |
| `tools/diagnose_source_branches.py` | `ab70b6c3af7cfd303ac8ebe31c319ba6cd51e781c37ac77d827c7501a0e9f74d` |
| `docs/research/meshecho_source_branch_diagnostic_design.md` | `13fa7ae2678a4d9e8dfe4f04ddeec57d35a7ae51f34c6d7658fb194d56683da3` |
| `tests/test_source_branches.py` | `d4b63ddfbfbc613b688bb9d75a7de58e61ab8a20e690e8753b7cde1ec7c8468a` |

## Goal

Revise the ICCT/ICC-facing MeshEcho paper using the fairness audit,
non-saturated random-pair simulation, connected route-discovery diagnostics,
and one-shot budget check; increment the repository version by one
for traceability, preserve resumable work in Markdown, verify the artifacts,
and publish the intended changes to GitHub.

## Phases

- [completed] Audit current paper, simulation evidence, worktree, and remote.
- [completed] Revise paper and release metadata to version 2.1.11.
- [completed] Record checkpoint state and compile/inspect the PDF.
- [completed] Run tests and consistency checks.
- [completed] Push the committed task-related files and update the draft PR.
- [completed] Verify remote commit, PR metadata, and final artifact state.

## Scope Rules

- Keep the frozen 3 km matrix clearly labeled as a contention-oriented,
  link-friendly case.
- Keep the random-pair multi-hop probe as diagnostic evidence; do not claim
  universal MeshEcho superiority.
- Distinguish MeshEcho confidence ranking from Smart-CALM recovery and learning.
- Treat connected-multihop runs with low route-discovery success as stress checks,
  not as neutral headline comparisons.
- Use `--smart-max-timeout-retries 0` for the budget-matched mechanism line.
- Do not stage unrelated user-generated files or build caches.
- Before any context compression, update this file, `findings.md`, and
  `progress.md`; after resuming, read all three before taking action.

## Errors Encountered

| Error | Attempt | Resolution |
| --- | --- | --- |
| `academic-paper-reviewer` path under `.agents` was missing | 1 | Used the available `.codex/skills/academic-paper-reviewer/SKILL.md` path. |
| Initial random-stream regression test lacked mocked simulator nodes | 1 | Added `nodes` and used a complete fake simulator; all tests pass. |
| One `rg` heading query had an invalid regular expression | 1 | Treat as command syntax error and use simpler file inspection. |
| PDF skill path under bundled runtime was missing | 1 | Use the listed primary-runtime PDF skill path and continue with LaTeX verification. |
| First artifact marker path was the spreadsheet implementation | 1 | Use the PDF-specific marker implementation; spreadsheet marker only accepts spreadsheet formats. |
| Rebuild command containing `rm -rf` was rejected | 1 | Reuse the existing build directory and run the compiler without destructive cleanup. |
| Initial LaTeX script path was wrong | 1 | Located the bundled compiler at `.../latex/0.2.6/scripts/compile_latex.py`. |
| Second concurrent design-agent spawn hit the thread limit | 1 | Continued local design review and spawned the bounded design screen after another agent completed. |
| Planning catch-up invoked with unavailable `python` during the 2026-10-04 continuation | 1 | Re-ran with `python3`; catch-up completed with no unsynced output. |
| Three-file research checkpoint patch missed a wrapped `task_plan.md` context | 1 | Re-read the exact lines and applied smaller hunks; the failed patch changed no files. |
| Corridor-design audit patch included a nonmatching extra context | 1 | Re-read the file and applied the valid audit-stop hunk; no 38xxx run occurred. |
| Delayed-control cost-window patch missed a wrapped line | 1 | Re-read the exact paragraph and applied the narrower replacement. |
| First new DHR accounting test expected the recovery-F bucket for an initial-F ACK | 1 | Corrected the expectation to `windowed_dhr_initial_ack_tx`; the test failed against missing family registration, then passed after the targeted fix. |
| First search for tests used a literal newline in an `rg` regex | 1 | Switched to simple targeted searches and direct source inspection. |
| First repeat-control design wording patch missed a wrapped line | 1 | Re-read exact lines and applied a narrower patch; no other file changed. |

## Checkpoint - 2026-09-04

- The revised manuscript compiled successfully with bundled Tectonic.
- Final PDF: 8 pages, PDF 1.5, root artifact
  `paper/icct2026/icct2026_lora_mesh_preliminary.pdf`.
- Root PDF and `paper/icct2026/build-2_1_11/` PDF have SHA-256
  `b822940c36b13a084538691b526a2b72c0d32463c67ff4772e76937fa4ab9b9a`.
- Rendered pages were visually checked; no text, table, or figure overlap was
  found. Remaining diagnostics are font fallback and underfull boxes; there
  are no unresolved reference warnings in the final log.
- `python3 -m pytest -q`: 45 passed.
- Python compilation, `bash -n tools/run_icc_experiments.sh`, and
  `git diff --check` passed.
- The worktree contains unrelated untracked caches, course materials, and
  generated build outputs. They must remain unstaged.

## Next Exact Actions

1. Stage only the manuscript/PDF, fairness evidence and probe, simulator/test
   changes, release metadata, and this task's Markdown records.
2. Commit the `2.1.11` fairness and budget-matched revision.
3. Push `version/v2` and update draft PR 1's title/body from `2.1.9` to
   `2.1.11`.
4. Verify the remote commit, PR metadata, and final artifact checks.

## Current Revision - 2.1.18 MeshEcho Identity and Attribution

- [completed] Make MeshEcho the explicit ICC method identity and keep the
  adaptive firmware/history line outside the ICC protocol matrix.
- [completed] Add ETX/ETT baselines and four MeshEcho component ablations.
- [completed] Run the 20-seed primary, SF/load sensitivity, and component
  ablation matrices with shared connected-multihop gates.
- [completed] Rewrite ICC reports, experiment plan, comparison summary, and
  checklist around MeshEcho rather than Smart-CALM.
- [completed] Extend the five-page ICC manuscript with component attribution
  and ACK-vs-destination metric boundaries.
- [in_progress] Run final tests/static checks, review the staged file set,
  commit and push version 2.1.18, and verify the draft PR.

### Current Exact Next Actions

1. Run the complete test, Python, shell, whitespace, page-count, and
   report-consistency checks.
2. Selectively stage only 2.1.18 source/docs/evidence and Markdown state files;
   exclude old artifacts, build directories, figures, and `tmp/`.
3. Commit, push `version/v2`, update the draft PR, and verify the remote head.

## 2.1.18 Pre-submission Decision Gate

- [complete] Run an independent methodology/venue review of the five-page
  ICC manuscript and the versioned evidence.
- [complete] Record the primary evidence boundary: 20 seeds, 24 selected
  pairs, all selected pairs exactly two hops, and zero primary route-cache
  hits.
- [in_progress] Decide whether to publish the current bounded ICC claim or
  open a 2.1.19 evidence revision before publishing.

### Decision criteria

- Current version is a borderline ICC candidate, not a safe accept.
- A stronger revision should prioritize an unconditioned random-pair case,
  repeated-pair/cache-aging evidence, deeper multi-hop or larger-network
  topologies, fixed-candidate confidence isolation, temporal fading/stale
  routes, and one distinct standard baseline.
- Regardless of decision, disclose the SF8 calibration, mark all table
  `\pm` values as 95% CIs, narrow fallback/age claims, publish/tag 2.1.18,
  and replace anonymous EDAS metadata.

## Publish Continuation - 2026-09-04

- The final local `HEAD` is `251ba50`, version `2.1.11`, and matches
  `origin/version/v2`.
- The relevant files are already committed; the remaining publish gate is
  `git push` followed by updating and verifying draft PR 1.

## Publish Transport Note - 2026-09-04

- The first push attempt failed at the HTTP/2 transport layer before any
  remote update. Retry with HTTP/1.1; no local commit was lost.

## Final Publish State - 2026-09-04

- Push completed successfully with HTTP/1.1.
- Local and remote `version/v2` both point to `251ba50`.
- Draft PR 1 is open and updated to the 2.1.11 fairness/budget-matched
  revision.
- Final artifact and validation checks passed.

## New Revision - 2026-09-04 (2.1.12 recovery-budget audit)

- The user requested another fairness-aware paper revision based on the
  current simulation, with a patch-version increment and GitHub publication.
- The current `2.1.11` evidence is honest about fixed-pair/link-quality bias,
  but the recovery-budget contribution is not yet represented by a formal
  command-line experiment for the `calm-mesh` line.
- Planned `2.1.12` work:
  - add an explicit `--calm-disable-route-miss-fallback` control;
  - run a paired 20-seed recovery-budget sensitivity audit under the main
    scenario using independent channel-reception randomness;
  - revise the manuscript to distinguish route admission from route-miss
    recovery and static-channel confidence evidence;
  - bump repository metadata from `2.1.11` to `2.1.12`;
  - compile and inspect the PDF, run tests, selectively commit, push, update
    PR 1, and verify the remote state.
- Unrelated untracked build outputs, caches, course material, and user
  documents remain out of scope.

## 2.1.12 Progress

- Completed the explicit CALM route-miss fallback control.
- Completed and re-ran the 20-seed recovery-budget audit.
- Corrected the audit's route-discovery metric to report successes divided by
  attempts, with attempts shown in the report.
- Updated the paper and fairness notes with the corrected rates and the
  conservative interpretation.
- Found and quantified the native route-cache TTL mismatch: MeshCore-like
  uses `300 s`, while MeshEcho uses `600 s`.
- Added a configurable MeshCore-like TTL and the paired
  `tools/run_route_ttl_audit.py` experiment. Matching TTL raises MeshCore-like
  ACK PDR from `0.381` to `0.519`; the remaining matched-TTL gap is
  `+0.209 +/- 0.071`.
- Updated the manuscript, README, changelog, and fairness report to disclose
  the TTL mismatch and report the matched audit.
- Remaining gates are PDF compilation/inspection, final tests, selective
  commit, push, PR update, and remote verification.

## 2.1.12 Verification

- A previous Tectonic compilation of the recovery-only revision succeeded with
  an 8-page PDF; the TTL disclosure requires a fresh compilation.
- `python3 -m pytest -q` reported 47 passed before the TTL paper edits.
- Python compilation, shell syntax, and `git diff --check` passed.
- Remaining gates are fresh PDF compilation/inspection, final validation,
  selective commit, push, PR update, and remote verification.

## 2.1.12 Final Verification Update

- Recompiled after the TTL disclosure; the paper is 9 pages, PDF 1.5, with
  SHA-256 `97a5fc593a60ea1295697d0e90df09940ade0c158c54f290c611308598b70920`.
- Visually inspected the latest rendered pages, including the abstract,
  fairness audit, limitations, conclusion, and references.
- `python3 -m pytest -q`: 47 passed.
- Python compilation, shell syntax, CLI help, and `git diff --check` passed.
- Remaining gates are selective staging, commit, push, PR update, and remote
  verification.

## 2.1.13 Fairness-Focused Verification

- Reframed the frozen 50-node matrix as a contention-oriented repeated-pair
  case because direct-link PRR is saturated and cached routes are mostly one
  hop.
- Kept the matched 600 s MeshCore-like TTL, random-pair non-saturated probe,
  one-shot timeout budget check, and controlled route-conflict experiment
  separate in the manuscript.
- Updated `VERSION`, release notes, experiment-plan notes, simulator defaults,
  regression tests, and the ICCT manuscript to `2.1.13`.
- `python3 -m pytest -q`: 49 passed. Python compilation, shell syntax, and
  `git diff --check` pass.
- Bundled Tectonic rebuilt the manuscript to 9 pages. Root PDF SHA-256:
  `aa2c2e5e171595256938be222a2cca7757dbbdc8bb516e4cc640dc2f2d300cbe`.
- Rendered pages 1, 6, and 9 were inspected directly; PDF text extraction,
  citation checks, and page metadata confirm a complete artifact.
- Remaining actions are selective staging, commit, push, PR update, and
  remote verification.

## 2.1.13 Final Publish Verification

- Commit `fe24d1d` is pushed to `origin/version/v2`.
- PR 1 is OPEN and DRAFT with the title
  `[codex] MeshEcho 2.1.13 fairness-focused evaluation`.
- The final root PDF is 9 pages, PDF 1.5, SHA-256
  `aa2c2e5e171595256938be222a2cca7757dbbdc8bb516e4cc640dc2f2d300cbe`.
- The 2.1.13 fairness revision is complete; unrelated untracked worktree
  artifacts remain excluded.

## Continuation Rule

Before any context compression, append completed commands/results and the
exact next action to this file, `findings.md`, and `progress.md`. After
resuming, read all three before taking further action.

## 2.1.14 Revision - ICC Quality Gate

- [completed] Add TDD coverage for saturated direct links, incomplete pair
  pools, and insufficient graph-hop distance.
- [completed] Implement a per-seed connected-multihop quality gate in the
  fairness probe.
- [completed] Integrate the gate into `tools/run_icc_experiments.sh` with
  calibration and legacy-reproduction environment variables.
- [completed] Bump release metadata and document the evidence contract.
- [completed] Run the real three-seed quality probe and the full ICC shell
  smoke flow.
- [completed] Commit only the 2.1.14 task files, push `version/v2`, and
  verify the remote branch and draft PR.

### 2.1.14 Verification Snapshot

- Full unittest discovery: 52 passed.
- `bash -n`, Python compilation, and `git diff --check` passed.
- Three-seed connected-multihop probe passed: 24/24 pairs per seed, mean
  selected graph distance `2.014` hops, and mean direct-link PRR-below-0.99
  fraction `0.641`.
- ICC shell smoke passed with four matrix scenarios followed by the quality
  gate; smoke artifacts were moved to `/tmp` and are not release files.
- Version is `2.1.14`; generated evidence is in
  `docs/results/meshecho_v2_1_14_connected_multihop_quality.md` and
  `results/meshecho_v2_1_14_connected_multihop_quality.csv`.

### 2.1.14 Final Publish State

- Commit `b5de06b` is pushed and matches `origin/version/v2`.
- Draft PR 1 is OPEN with title
  `[codex] MeshEcho 2.1.14 ICC evidence-quality gate`.
- The task is complete; future work should start from a new versioned
  revision rather than modifying this release in place.

## 2.1.15 ICC Revision - In Progress

- [in_progress] Complete the full 2.1.15 ICC experiment workflow, including
  the quality gate and calibrated multi-hop matrix.
- [pending] Rename/copy calibrated evidence to the 2.1.15 release prefix and
  update the manuscript to ICC 2027 with an initial-submission limit of six
  pages.
- [pending] Rebuild and inspect the paper, run all tests/static checks, and
  selectively publish the release to `version/v2` and draft PR 1.

### Errors Encountered

| Error | Attempt | Resolution |
|---|---|---|
| `python: command not found` while running the planning session catch-up | 1 | Re-ran the helper with `python3`; no session data was lost. |

### Current Evidence Gap

The initial 2.1.15 run produced only `50n_unicast_pairs` and `50n_mixed`
artifacts. This gap was closed by a full rerun: the calibrated multi-hop
matrix and quality-gate artifacts now exist under the 2.1.15 prefix.

### 2.1.15 Experiment and Paper Phase

- [complete] Run all four ICC legacy scenarios, the 3-seed quality gate, and
  the 20-seed calibrated multi-hop matrix.
- [complete] Replace the copied ICCT draft with an ICC 2027 initial-submission
  manuscript and verify the PDF page limit and rendering.
- [complete] Run final automated checks, stage only release files, publish
  `version/v2`, and verify the draft PR.

### 2.1.15 Verification Snapshot

- Quality gate passed for every seed: 24/24 pairs, mean graph distance 2.014
  hops, direct-link PRR-below-0.99 fraction 0.641 in the 18 km diagnostic.
- Calibrated 20-seed matrix passed: 24/24 pairs per seed, mean selected graph
  distance 2.0 hops, direct-link PRR-below-0.99 fraction 0.160, and PRR-below-
  0.50 fraction 0.046.
- Tectonic compiled `paper/icc2027/icc2027_lora_mesh.tex` to 3 pages, below
  the ICC initial-submission maximum of 6 pages. Rendered pages 1--3 were
  inspected for clipping, overlap, table integrity, and stale ICCT text.

### Final Publish Verification

- [complete] Local release commit created as `fb133ba`.
- [complete] Follow-up status commit created as `2ebefd1`.
- [complete] `origin/version/v2` matches `2ebefd1`.
- [complete] PR 1 is OPEN/DRAFT with title
  `[codex] MeshEcho 2.1.15 ICC calibrated multi-hop evidence`.
- [complete] No automated checks are configured for `version/v2`; local test,
  experiment, and PDF verification are the authoritative gates for this draft.

### Submission Readiness Boundary

- [complete] Add `docs/icc2027_submission_checklist.md` with the official
  six-page, English, PDF/EDAS, originality, registration, and presentation
  requirements.
- [pending user metadata] Replace `Anonymous Authors` with the final EDAS
  author list and affiliations before actual submission. This cannot be
  inferred safely from the repository.
- [complete] Checklist commit `753a9b1` is pushed and PR 1 points to it.

## 2.1.16 Five-Page and Hardware-Evidence Revision

- [in_progress] Add a traceable historical ICC paper sample and determine
  whether physical validation is a hard requirement.
- [pending] Expand `paper/icc2027/icc2027_lora_mesh.tex` from 3 pages to about
  5 pages with substantive related work, method detail, parameter table,
  evidence tables, and discussion; remain at or below 6 pages.
- [pending] Bump release metadata to 2.1.16 and update the ICC checklist,
  README/index references, and PR description.
- [pending] Rebuild and inspect the PDF, run tests/static checks and a
  reproduction smoke check, selectively commit/push, and verify PR 1.

### Research Boundary

- The historical audit uses DOI metadata and abstracts from Crossref/OpenAlex
  plus the official ICC 2027 submission guidance. It is a practice sample,
  not a systematic census of all ICC acceptances.
- The defensible conclusion is that ICC accepts both simulation/analysis-only
  and hardware/testbed-supported communications work; hardware increases
  external validity but is not a universal submission gate.

### 2.1.16 Completed Research and Drafting

- [complete] Add ten DOI-linked prior ICC samples and the conservative
  simulation-versus-hardware interpretation in `findings.md` and
  `docs/icc2027_prior-work_hardware-evidence.md`.
- [complete] Expand the manuscript to five printed pages with substantive
  method, evidence, and discussion content; fresh Tectonic build passes and
  stays below six pages.
- [complete] Bump source/release metadata to 2.1.16 and state that the
  verified 2.1.15 simulation artifacts are reused because no simulator code
  changed.
- [complete] Run the full local test/static/PDF gates and a 600 s one-seed
  calibrated smoke. A redundant full matrix rerun was stopped after confirming
  it only duplicated unchanged 2.1.15 data; partial outputs remain unstaged.
- [complete] Commit `859686a`, push `version/v2`, update PR 1 to the 2.1.16
  five-page/hardware-audit title and body, and verify the remote head.

### Final 2.1.16 Boundary

- The paper and evidence revision is complete and published.
- The LaTeX source still uses `Anonymous Authors`; replacing it with the final
  EDAS author list is intentionally pending user metadata and is not inferred.

## 2.1.17 Reviewer-Directed Revision

The user asked to implement the remaining reviewer-directed improvements
identified after the 2.1.16 assessment.

- [in_progress] Add managed flooding to the primary comparison and narrow
  confidence-ablation language to the complete policy-bundle effect.
- [in_progress] Add a reproducible SF/load sensitivity workflow and run the
  versioned connected-multihop sensitivity cases before putting any new
  numbers in the paper.
- [pending] Update the manuscript, experiment plan, README, changelog, and
  release metadata to 2.1.17; preserve the five-page ICC limit.
- [pending] Run tests, sensitivity experiments, LaTeX compilation, and
  consistency checks; selectively commit/push and verify PR 1.

## 2.1.17 Scope Decisions

- No physical hardware claim will be added. The paper remains explicit that
  the evidence is packet-level simulation only.
- A controlled route-selection experiment already exists in
  `tools/run_route_conflict_experiment.py`; this revision will cite it as
  surgical mechanism evidence and will not overclaim the end-to-end ablation.
- New sensitivity numbers will be generated by the current simulator with
  matched pair pools, independent channel streams, and per-seed quality gates.
- Untracked historical artifacts, partial 2.1.16 outputs, build directories,
  and `tmp/` remain out of scope.

### Errors Encountered

| Error | Attempt | Resolution |
| --- | ---: | --- |
| `python: command not found` during session catch-up | 1 | Re-ran with `python3`; no state was lost. |
| Local workspace Git tree contains missing objects | existing | Continue in clean remote clone `/tmp/lora_mesh_remote_current.iIrtPz`; do not reset the damaged checkout. |
| Direct execution of sensitivity runner could not import root simulator | 1 | Added the repository root to `sys.path`, matching the existing probe. |
| SF8 at 8.25 km failed the 0.10 PRR-below-0.99 gate for seed 1 | 1 | Calibrated only that sensitivity case to a 9 km area; smoke now passes with the same connected-pair contract. |

## 2.1.18 ICC Reviewer-Directed Revision

Goal: implement the reviewer-directed improvements for MeshEcho itself rather
than turning the ICC paper into a Smart-CALM paper. The release must retain
the five-page ICC limit, add fair quality-aware routing baselines, make the
primary statistical claim explicit, and produce a layout-clean artifact.

- [in_progress] Add test-first ETX/PRR and airtime-aware ETT route-selection
  baselines that share the existing discovery, topology, and traffic harness;
  expose MeshEcho as the primary protocol name.
- [pending] Re-run the primary and SF/load matrices with the new baselines and
  retain versioned raw CSV/summary/report evidence.
- [pending] Revise the manuscript to report paired CIs, distinguish ACK
  completion from destination delivery, treat Smart-CALM as an exploratory
  negative result, and cite the new baselines.
- [pending] Fix the Table IV two-column overflow, rebuild/render all pages, run
  tests and static checks, bump metadata to 2.1.18, publish, and verify PR 1.

### 2.1.18 Guardrails

- Keep the existing managed-flooding and MeshCore-like rows; do not hide
  negative or boundary cases.
- Use matched 2 s discovery, 600 s route TTL, zero timeout retries, and the
  same shared pair pool for the new metric baselines.
- Do not claim hardware validation or topology-independent dominance.
- Do not stage old build directories, partial 2.1.16 outputs, or `tmp/`.
- Keep Smart-CALM code available for its separate firmware/history line, but
  exclude it from the primary ICC protocol set and do not present it as the
  MeshEcho contribution.

## 2.1.19 MeshEcho-Only Fairness Revision

Goal: continue the ICC revision as MeshEcho, not Smart-CALM. The release must
use the corrected equal-candidate-exposure source-route baseline, make the
fallback implementation match its configured TTL, regenerate every ICC-facing
artifact, and synchronize the five-page manuscript to the corrected evidence.

- [complete] Add TDD coverage for matched-window candidate exposure,
  legacy immediate-reply duplicate suppression, and configured fallback TTL.
- [complete] Implement the source-route candidate-pool fix and configured
  MeshEcho fallback TTL.
- [complete] Regenerate the 20-seed primary, component, SF/load sensitivity,
  and cache-reuse diagnostics under the 2.1.19 prefix.
- [complete] Rewrite all ICC manuscript tables, results, discussion, conclusion,
  and reproduction metadata to remove stale 2.1.18 values.
- [complete] Rebuild and inspect the five-page PDF.
- [in_progress] Run full tests/static and consistency gates.
- [pending] Selectively commit/push version 2.1.19 and verify the draft PR.

### 2.1.19 Guardrails

- MeshEcho is the named ICC method; Smart-CALM remains a separate historical
  firmware/simulator line and must not appear in ICC method tables, ablations,
  or primary claims.
- The primary estimand is first-discovery route admission because its
  `route_cache_hits` are zero; cache TTL results remain a secondary diagnostic.
- `meshecho-no-confidence` is an end-to-end policy-bundle ablation, not a
  fixed-candidate causal estimate.
- All table `\pm` values must be labeled as two-sided 95% CI half-widths.
- Do not claim topology-independent dominance, physical validation, or a
  universal advantage over ETX/ETT.

## 2.1.20 MeshEcho Route-Conflict Attribution Revision

Goal: correct the controlled route-conflict audit so it exercises the named
MeshEcho core, then version and republish the ICC evidence package.

- [complete] Add a failing identity regression test for the route-conflict
  harness.
- [complete] Replace the Smart-CALM-derived harness with a MeshEcho-specific
  harness while preserving the confidence/no-confidence controls.
- [complete] Re-run the 20-seed route-conflict simulation and record the new
  paired result.
- [in_progress] Bump all release-facing metadata to 2.1.20, regenerate the
  ICC evidence prefixes, and synchronize the five-page manuscript.
- [pending] Run the full test/static/PDF gates, selectively commit, push, and
  verify the draft PR.

### 2.1.20 Guardrails

- The ICC method and controlled audit are MeshEcho only.
- Smart-CALM remains available only in its historical simulator/firmware
  namespace and archived documents.
- The route-conflict report must be reproducible from the versioned command and
  must not inherit Smart-CALM timeout/profile behavior.
- Preserve the simulation-only evidence boundary and do not imply hardware
  validation.

## 2.1.20 Pre-submission Assessment - 2026-09-19

- [complete] Inspect the current six-page PDF, source, versioned reports, and
  release state.
- [complete] Run the reviewer-style quality gate: tests, static checks, metric
  consistency, and venue-fit assessment.
- [pending] Decide whether to publish 2.1.20 as an ICC candidate or make one
  more evidence revision before submission.

### Assessment decision

- Current status: borderline ICC candidate / weak-reject risk, not a safe
  accept.
- The strongest supported claim is a bounded first-discovery ACK-completion
  and airtime operating point versus the matched source-route baseline.
- The result does not establish a statistically separable advantage over
  ETX/ETT, a destination-delivery gain, topology-independent dominance, or
  hardware validity.
- The primary matrix is conditioned on a PRR-qualified pair pool; all selected
  pairs are exactly two hops and route-cache hits are zero. This is the main
  scientific risk.
- The current root PDF is six pages. This meets the official ICC six-page
  ceiling but does not meet the project's five-page target and leaves no
  layout margin. The submission checklist still incorrectly says five pages.
- The manuscript still contains `Anonymous Authors`; final EDAS metadata is
  pending.

### Highest-value next revisions

1. Add an unconditioned random-pair case and a deeper 3--5-hop or larger-node
   case, preserving shared seeds and reporting the selection rule.
2. Add one distinct baseline beyond fixed-SF ETX/ETT (e.g. min-hop/RSSI-only,
   RPL/ORPL-style, or a clearly defined oracle upper/lower bound).
3. Add a temporal-fading/stale-route case, or remove/soften route-aging and
   recovery claims from the central contribution.
4. Reframe the headline around source-confirmed completion and keep destination
   PDR as a co-primary negative/boundary result.
5. Compress the paper to five pages, correct the checklist, replace author
   placeholders, and rerun the full publish gate.

## 2.1.21 MeshEcho Generalization and Temporal-Fading Revision

Goal: close the highest-value ICC reviewer gaps while keeping MeshEcho as the
only ICC method. Add a genuinely distinct min-hop baseline, unconditioned
random-pair evidence, a deeper 3--5-hop case, and temporal-fading/cache-age
diagnostics; keep Smart-CALM only in its historical simulator/firmware
namespace and out of ICC methods, ablations, primary experiments, and claims.

- [complete] Verify the partially generated 2.1.21 primary/sensitivity
  artifacts and complete any missing summaries.
- [complete] Run the 20-seed random-pair, deep-multihop, and long/short-TTL
  temporal-fading generalization cases with per-seed quality gates.
- [complete] Run MeshEcho component attribution, cache diagnostics, and
  MeshEcho-only route-conflict evidence under the 2.1.21 prefix.
- [complete] Rewrite the ICC manuscript and result docs around the new evidence,
  narrow claims to source-confirmed completion/airtime operating points, and
  compress the final PDF to exactly five pages.
- [in_progress] Run full tests/static/report-consistency/PDF gates, selectively
  stage 2.1.21 files, commit/push, update the draft PR, and verify remote OID.

### 2.1.21 Guardrails

- The ICC protocol matrix is MeshEcho, managed flooding, matched source route,
  ETX, ETT, and min-hop; Smart-CALM is not an ICC protocol.
- The primary estimand is first-discovery route admission. Cache-hit and
  temporal-fading results are secondary diagnostics, not universal aging
  claims.
- Every `\pm` number in the paper is a two-sided 95% CI half-width.
- Do not claim topology-independent dominance, hardware validation, or
  universal superiority over ETX/ETT.
- Do not stage old release artifacts, build caches, figures, or `tmp/`.
- Before context compression, update `task_plan.md`, `findings.md`, and
  `progress.md`; after resuming, read all three before action.

### Calibration correction

- The initial deep-multihop calibration at 20 km and PRR threshold 0.85
  failed seed 12 with only 20 eligible pairs. This failure is retained as a
  recorded design issue, not discarded.
- The corrected calibration uses a 21 km square with the same 100 nodes,
  3--5-hop range, PRR threshold, 24 requested pairs, and per-seed quality
  gate. Because this changes the experiment code, the corrected evidence is
  being generated under the next version prefix `2.1.22`.

### 2.1.22 verification checkpoint

- Completed all required 2.1.22 evidence strata: main ICC matrix, calibrated
  multihop, quality gate, SF/load sensitivity, component attribution,
  cache TTL 600/30, route-conflict, random-pair, deep-multihop, and temporal
  fading TTL 600/30.
- Tectonic compiled `paper/icc2027/icc2027_lora_mesh.tex` to a 5-page
  letter-size PDF under `paper/icc2027/build-2_1_22-tectonic/`.
- `python3 -m pytest -q`: 71 passed.
- Python compileall, `bash -n tools/run_icc_experiments.sh`,
  `git diff --check`, PDF metadata, key CSV row-count checks, and 2.1.22
  report Smart-CALM leakage checks passed.
- Author metadata is populated as `Gao Zu` and `Quan Zhi` in English only,
  both at Shenzhen University; EDAS registration and exact metadata matching
  remain pending.
- Added a compact two-panel primary-result bar figure with existing means and
  95% CIs; the figure is presentation-only and does not require a version
  bump.
- Restored stricter IEEE conference formatting: explicit 10-point letterpaper
  `IEEEtran`, no manual global spacing compression, natural bibliography flow,
  and no overfull table boxes in the final format build.
- Remaining submission action: register the exact title and author order in
  EDAS, then complete venue registration/presentation checks.

## 2.1.23 ICC Algorithm and Manuscript Revision

Goal: strengthen MeshEcho against the identified ICC reviewer objections,
rerun the affected simulations, and deliver a new five-page paper using only
verified 2.1.23 outputs. Preserve 2.1.22 as a historical baseline.

- [complete] Audit current implementation, runner, raw evidence, and
  manuscript claims; select a controlled experimental design before coding.
- [complete] Add tests and implement comparable route-discovery scheduling and
  per-discovery candidate-path evidence.
- [complete] Add tests and implement a primary workload that actually exercises
  all selected source-destination pairs, with explicit unicast denominators.
- [complete] Run pilot and full versioned simulations; audit raw CSVs, paired
  intervals, negative cases, and whether the algorithm helps under control.
- [complete] Revise the ICC LaTeX paper, figure/tables, and related work around
  supported claims; retain the English-only authors and IEEE format.
- [complete] Verify tests, reproducibility, five-page PDF layout, versioned
  outputs, GitHub branch/PR, and clean final status.

Guardrails: no invented data; no post-hoc claim of an ETX advantage if the
controlled result does not show one; report flooding and recovery negatives;
keep the previous 2.1.22 outputs untouched. Before compaction, update this
plan, `findings.md`, and `progress.md`; reread all three after resuming.

### 2026-09-25 Author-name check

- [complete] Inspect the stable ICC LaTeX source, figure, BibTeX, three PDF
  copies, extracted text, fonts, and rendered first page for Chinese names.
- [complete] Confirm all current ICC author lines are English-only:
  `Gao Zu`, `Quan Zhi`, and `Shenzhen University, Shenzhen, China`.
- [complete] The user confirmed the English given-name-first order
  `Zu Gao` / `Zhi Quan`. Update the source, checklist, and final PDF to match.
  The old temporary PDF path no longer exists.

### 2.1.23 Experiment checkpoint

- [complete] Add optional shared RREQ forwarding timing and per-discovery
  candidate-path records, with dedicated regression tests.
- [in_progress] Finish fixed-once 24-pair traffic and expose the discovery
  audit through the probe runner.
- [in_progress] Correct the repeated per-hop confidence penalty using a
  test-first behavioral check; retain old 2.1.22 evidence unchanged.
- [complete] Correct MeshEcho's repeated hop-penalty subtraction without
  changing the historical CALM implementation; targeted tests pass.
- [complete] Run a three-seed fixed-once/matched-timing pilot with 24 actual
  unicasts per seed and seven policies; the pipeline passes its quality gate.
- [in_progress] Test an optional bounded-confidence admission variant on
  development seeds before choosing the final policy. Do not present pilot
  means as a 20-seed result.
- [complete] Development seeds 1--3 showed the optional one-hop/0.10-gain
  budgeted variant saved about 1.9 s mean airtime but lost 7/72 ACKs versus
  MeshEcho. Keep it as an explicit negative comparator, not the headline.
- [in_progress] Run a frozen 20-seed holdout (seeds 21--40) for both the
  matched-timing, fixed-once workload and an isolated-first-discovery study.
  Count seeds, not 480 flows, as independent statistical units.
- [complete] Both 20-seed holdout workloads finished with complete raw CSVs,
  quality gates, and seed-paired reports. The isolated report was regenerated
  with paired CIs and same-selected-path checks; the raw CSV matched its
  pre-report-generation hash exactly.
- [in_progress] Run 20-seed native-timing random-pair, 100-node/deep-hop, and
  temporal-fading generalization cases before rewriting the five-page paper.
- [complete] Finish all four 2.1.23 generalization cases and native-timing
  fixed-once run; all processes exited successfully and raw/reports exist.
- [complete] Audit 480/480 fixed-once attempts and 480/480 equal-candidate
  isolated first discoveries; distinguish these two estimands in the paper.
- [complete] Confirm the final English author order `Zu Gao`, `Zhi Quan` in
  the ICC source, checklist, and pre-revision five-page PDF.
- [in_progress] Update the five-page manuscript and primary bar chart using
  only 2.1.23 holdout values. The TeX file was transiently missing during
  handoff; it has been recovered from HEAD with the confirmed author order.
- [in_progress] Correct report boilerplate and exact reproduction commands,
  then verify all generated Markdown against the immutable raw CSVs.
- [in_progress] Complete release metadata, full tests, PDF layout, selective
  commit/push, and GitHub draft-PR verification.

### 2.1.23 Exact Next Actions

1. Receive the revised TeX and report-generator corrections from their
   owners; check all claims against the 20-seed reports and adverse cases.
2. Rebuild the final ICC PDF, render and inspect five pages, check author
   order, no Han glyphs, page size, fonts, figure values, and LaTeX warnings.
3. Run all tests and static checks; stage only task files and versioned
   evidence, commit/push `version/v2`, update draft PR 1, and verify remote.

### 2.1.23 Final Local Verification

- [complete] Rebuild the revised paper: five Letter-size IEEEtran pages,
  Zu Gao and Zhi Quan in English only, no Han characters, embedded fonts,
  no overfull boxes or undefined references. All five rendered pages were
  inspected; the final root PDF matches the checked build PDF by SHA-256.
- [complete] Correct the 2.1.23 report template and regenerate six Markdown
  reports from unchanged raw CSVs. Candidate audit output has a portable
  repository-relative source path and unchanged source SHA-256.
- [complete] Full test suite: 111 passed. Python compilation, shell syntax,
  PDF metadata/text/font checks, and `git diff --check` passed.
- [in_progress] Selective commit/push, draft PR metadata, remote verification.

### 2.1.23 Verification Errors Resolved

- First expanded manuscript built to four pages; adding exact score
  recurrence and evaluation procedure produced five pages without forced
  page breaks or global spacing changes.
- Initial parameter table overran its column by 8.5 pt; local table width
  adjustment removed all overfull warnings.
- Two old tests assumed that every new version generated the 2.1.22 report
  family and retained its 0.221 route-conflict gain. Current tests instead
  verify the 2.1.23 report set and recompute the paired interval from the
  current route-conflict CSV.
- The first PDF build did not retain a log; a final Tectonic run with
  `--keep-logs` supplied warning verification.

Next exact action: stage only listed 2.1.23 release files, excluding
`paper/icc2027/build-2_1_23-tectonic/`; inspect staged diff, commit, push,
update draft PR 1, and compare local/remote commit IDs.

### 2.1.23 Publication Checkpoint - 2026-09-25

- All 49 intended release files are staged; the untracked Tectonic build
  directory remains excluded.
- `git diff --cached --check` found CRLF line endings in the 1921-line
  isolated-first-discovery CSV. The CSV writer uses Python's default CRLF.
- [complete] Add a regression check for LF-only CSV output, change the
  writer's line terminator, and mechanically normalize the existing CSV.
- [complete] Confirm parsed CSV rows and statistical report are unchanged.
- [complete] Rerun tests and staged-diff checks, then commit/push and
  verify PR 1.
- Do not rerun the completed 20-seed simulations for this formatting fix.

### 2.1.23 Final Pre-publish Gate

- `python3 -m pytest -q`: 111 passed. Python compilation, shell syntax,
  staged/unstaged whitespace checks, PDF SHA-256, and 49-file scope check pass.
- Staged ICC manuscript, checklist, and release notes contain `Zu Gao` and
  `Zhi Quan`; no old name order or Han author characters were found there.
- PR 1 is still draft on 2.1.22 and its old body mentions Chinese names.
  Replace its title and body after the new commit is pushed.

### 2.1.23 Published State

- Release commit `87a6184c8cf95a91769a9533462706693f3108bd` reached
  GitHub `version/v2`; the draft PR head matched this commit on verification.
- PR 1 title/body now describe 2.1.23 and use only `Zu Gao` / `Zhi Quan`.
- Two HTTPS push attempts timed out before remote update. An authenticated
  SSH push to the same repository succeeded; the permanent origin URL was
  not changed.
- The only remaining untracked path is the intentionally excluded Tectonic
  build directory. EDAS registration and author/title matching remain with
  the submitting authors.

## Active Goal Completion Audit - 2026-09-25

Objective: verify that the 2.1.23 algorithm revision and rewritten ICC paper
actually satisfy the original request to improve the identified weaknesses
without inventing results. Do not treat publication alone as proof.

- [in_progress] Compare MeshEcho implementation and tests with the prior
  release; determine whether the algorithm change is real and correctly
  represented in the manuscript.
- [in_progress] Recompute the main, isolated, and adverse-case evidence from
  raw versioned CSVs; check manuscript claims and confidence intervals.
- [in_progress] Audit the PDF, citations, limitations, and remaining external
  submission obligations.
- [pending] Add and version a fair per-hop PRR-product comparator, rerun the
  affected isolated and system comparisons under a new version, and rewrite
  the claim boundary if its result remains close to MeshEcho.
- [pending] Repair manuscript terminology (`route admission` versus actual
  selection, and model-inferred versus observed PRR) and resolve the font
  fallback in the final PDF if a standard IEEE build is available.
- [pending] Repair any other material mismatch with test-first changes and
  rerun only affected simulations under a new version if behavior changes.
- [pending] Decide completion from source, raw data, compiled paper, and
  remote state; keep this goal active if any required evidence remains weak.

The previous goal turn made progress: it published the 2.1.23 release and
corrected author metadata. Resume from this plan, `findings.md`, and
`progress.md` after any context compression.

### Audit Issues Discovered

- A read-only in-memory PRR-product route comparator on the current isolated
  20-seed pairs reached 322/480 ACKs against MeshEcho's 330/480, with a paired
  difference whose 95% CI crosses zero. This exploratory result is not a
  versioned artifact or paper evidence; it exposes a stronger-baseline gap.
- The PDF is five-page Letter and visually clean, but the Tectonic log shows
  Times font-shape fallback to Latin Modern. Standard pdfLaTeX is installed;
  verify a template-faithful build before final publication.
- Paper funding/conflict assertions require author confirmation; an optional
  non-blocking question has been sent. Initial nested question-tool call
  failed because that tool is direct-only; the direct call succeeded.

## 2.1.24 Preregistered Revision

The current paper's numbers are reproducible, but the default algorithm's
advantage over a model-informed no-retry PRR-product comparator is unproven.
The next revision must not reuse exposed seeds 21--40 as a fresh holdout.

1. Add `prr-product` as a matched RREQ, no-fallback, no-retry comparator using
   the same RREQ SINR-to-PRR model as ETX; test route scoring and CLI wiring.
2. Test an optional ACK-feedback stale-route eviction policy. It may only
   invalidate the exact cached path after an ACK guard expires; no same-flow
   retransmission, no future-channel oracle, and no eviction of a replacement
   route. Preserve one-shot behavior.
3. Use development seeds 41--50 for mechanism checks, freeze the policy and
   comparator, then run untouched seeds 51--70 for the repeated-pair fading
   primary check plus matching controls. Keep 21--40 as historical evidence.
4. Report ACK/destination PDR, airtime, energy, collisions, route repairs,
   discovery count, delay, and paired seed-level CIs. Include adverse and null
   findings. Do not promote the optional policy without evidence.
5. Revise the ICC title/text to route selection, explain model-inferred PRR,
   correct min-hop tie-breaking, state the random-pair denominators and deep
   stratum confounding, and rebuild with an IEEE-compatible font stack.
6. Run all tests and consistency/PDF gates, update release metadata, and
   publish only verified versioned artifacts to the existing draft PR.

No 2.1.24 simulation result exists yet. Do not cite the in-memory comparator
pilot in the manuscript as a released experiment.

### 2.1.24 Resume Checkpoint

- [complete] Verify `Zu Gao` and `Zhi Quan` in source and current five-page PDF.
- [in_progress] Add PRR-product comparator with test-first implementation.
- [in_progress] Correct manuscript terminology and method descriptions without
  touching result claims until versioned simulations are audited.
- [in_progress] Specify repeated-pair fading workload and observable metrics.
- [pending] Implement and test actual-transmission-timed, route-identity-safe
  ACK stale-route eviction as an optional MeshEcho variant.
- [pending] Run development seeds 41--50, freeze a justified policy, then
  validate on untouched seeds 51--70 and revise/rebuild/publish the paper.

### 2.1.24 Implementation Checkpoint

- [complete] PRR-product explicit comparator and isolated/fair runner wiring;
  42 related tests and one-seed equal-candidate smoke passed.
- [complete] ACK-eviction 2-by-2 protocol variants and simulator metrics;
  first failing tests were observed, and 55 focused tests now pass.
- [in_progress] Add matched-timing fading/static/short-TTL runner cases and
  repeated-pair/trace quality gate; retain all selected seeds.
- [pending] Bump current release defaults to 2.1.24 before versioned runs.
- [pending] Run 41--50 development matrix, document decision, then freeze
  and run untouched 51--70 validation plus isolated PRR-product comparator.
- [pending] Reconcile every new claim and figure with raw CSVs, build/review
  five-page ICC PDF, run full gates, and publish verified release to GitHub.

### 2.1.24 Development Decision

- [complete] Run seeds 41--50 for fading, static, and short-TTL controls with
  identical application traces and repeated-pair quality gates.
- [complete] Reject single-failure 15-s ACK eviction as the proposed default:
  it reduces development ACK completion and raises airtime even in static
  control. Preserve the optional policy and negative result transparently.
- [in_progress] Examine one mechanistic ranking alternative using only
  41--50; do not implement it without evidence that its decision rule
  addresses the observed failure mode. No additional parameter fishing.
- [pending] Freeze a truthful 2.1.24 protocol/claim set, then perform a
  one-time untouched 51--70 validation and isolated PRR-product comparison.

### 2.1.24 ACK Feedback Race Check

- [complete] Fix the same-route old-guard race test-first: a later
  acknowledged DATA transmission must cancel earlier unacknowledged guards
  for that exact cached route, without canceling a newer transmission's guard.
- [complete] Re-run focused tests: 9 ACK-eviction tests pass, including the
  new reverse-timing boundary; `git diff --check` passes.
- [pending] Re-run affected development variants under new result prefixes;
  preserve the existing CSVs unchanged. The pre-fix ACK-eviction rows are
  historical diagnostics, not evidence about the fixed implementation.

### 2.1.24 Frozen Development Hypothesis

- Test exactly one new candidate on 41--50: calibrated max-min per-hop PRR
  from observed RREQ SINR, with no arbitrary hop penalty. Keep MeshEcho's
  RREQ timing, TTL, fallback, traffic, and no-retry budget unchanged; do not
  enable ACK eviction in this candidate.
- Compare against original MeshEcho and PRR-product in fading and static
  repeated-pair development cases, then inspect same-candidate route choices.
  The prior 41--50 results justify this test, not a claim of improvement.
- Reject the candidate if it does not reduce direct-route bias on matched
  candidate sets, does not show a convincing fading ACK gain, or raises
  airtime/energy substantially without commensurate delivery. Do not tune
  slope/threshold/hop penalty after seeing these development outcomes.
- Full suite currently has 131 passes and two missing-artifact failures:
  historical report tests derive their prefix from the bumped `VERSION`.
  Correct those tests to reference 2.1.23 artifacts explicitly; never
  relabel old CSVs as 2.1.24 evidence.

### 2.1.24 Development Results So Far

- [complete] Implement calibrated max-min PRR as an optional variant, with
  uncapped model-derived RREQ SINR score, zero hop penalty, and no change to
  MeshEcho's discovery, fallback, or retry budget. Focused score/runner/
  isolated/report tests pass; one-seed smoke is non-inferential.
- [complete] Run 41--50 fading and static repeated-pair matrices under the
  new `calibrated_dev41_50` prefix, preserving all pre-fix raw CSVs.
- [complete] Run 41--50 isolated first-discovery matrix: 240/240 candidate
  sets match across six policies, 225 expose multiple candidates.
- [in_progress] Short-TTL development control is computing; do not infer its
  result before the process completes.
- [pending] Audit seed-paired contrasts and same-candidate route choices,
  then freeze or reject the candidate once. Only then run 51--70 untouched
  validation and rebuild the manuscript.
- [in_progress] Add a PRR-product comparator with the same TTL-2 route-miss
  fallback budget and timing, leaving its PRR-product score unchanged. This
  control addresses the dynamic fallback mismatch; it is not a second
  candidate algorithm. Run it on 41--50 fading and static before the holdout.
- The first behavior test assumed FALLBACK was not counted in `data_tx`;
  source inspection showed every non-control packet, including FALLBACK, is
  counted. Corrected the assertion to detect extra plain DATA transmission;
  focused control tests now pass.

### 2.1.24 Holdout Freeze - 2026-09-25

- [complete] Freeze calibrated max-min PRR as the only new candidate. Its
  41--50 fading gain over old MeshEcho is paired +0.154 ACK PDR at +4.09 s
  airtime; equal-candidate direct selections fall from 11 to 1 in 21
  both-selected fading discoveries. Static and isolated ACK intervals cross
  zero; short-TTL control remains adverse. PRR-product with matched fallback
  reaches the same rounded fading/static ACK as the candidate. Do not claim
  strong-baseline superiority or tune the candidate further.
- [complete] Pre-holdout gate: 139 tests pass, Python compile and
  `git diff --check` pass. No 51--70 result prefix exists yet.
- Frozen code SHA-256: `lora_mesh_sim.py`
  `ac2b74f2f3b28cb029e39a883bdf313b1a9f000c4d76cbc6dd1054f80b55bf21`;
  fair runner `4e51ad137c0f3174803c62e052abffe78aa10979594975681e37608619e9d612`;
  generalization runner `83c19208dc32cdae2adc401e8cfb85c5cfbdf1f761efc5707272c5fd84f831ac`;
  isolated runner `577886627907e39872812765c86f553b671c7fcdda1a608b8b06c91bf79d9318`.
- [in_progress] Run the untouched 51--70 holdout once under prefix
  `meshecho_v2_1_24_icc2027_holdout51_70`: fading (primary), static and
  short-TTL controls, and isolated first discovery. Dynamic protocol list:
  old MeshEcho, calibrated variant, PRR-product without/with matched
  route-miss fallback, and both ACK-eviction negative variants. Preserve
  failed or null findings. If a post-holdout implementation bug requires a
  change, do not reuse 51--70 as an independent holdout.
- [pending] Independently recompute all holdout seed-level intervals and
  candidate-set evidence, rewrite the ICC paper honestly, rebuild/inspect a
  five-page PDF, run final tests, then publish only verified versioned files.
- The first targeted pytest command used a stale class name and collected no
  tests. The corrected node reproduced the expected `KeyError` at the cached
  route assertion; this is an implementation failure, not a data result.

### 2.1.24 Holdout Resume - 2026-09-25

- [complete] Confirm the current ICC TeX author block and five-page PDF print
  `Zu Gao` and `Zhi Quan` in that order, both at Shenzhen University. The
  latest user clarification confirms this given-name-first spelling.
- [complete] The one-time seeds 51--70 `feedback_fading` process exited 0 and
  wrote the raw CSV, summary CSV, and report under
  `meshecho_v2_1_24_icc2027_holdout51_70_feedback_fading`; do not rerun or
  overwrite this primary holdout stratum.
- [in_progress] Run the preregistered static, short-TTL, and isolated-first-
  discovery 51--70 controls with unique output paths, then independently
  audit all seed-level estimates and candidate-set evidence.
- [in_progress] The three controls were launched once with explicit case and
  protocol selections: static session `90316`, short-TTL session `11946`,
  isolated session `53033`. Their paths were absent before launch and do not
  overlap the completed fading files. Poll these sessions before any retry.
- [complete] Static session `90316`, isolated session `53033`, and short-TTL
  session `11946` all exited 0 with their respective raw results and reports.
  Do not rerun or overwrite these frozen holdout files.
- [complete] Independent fading raw-CSV audit verified 20 seeds x 6 policies,
  shared scheduled traces, and seed-paired intervals. Calibrated minus old
  MeshEcho ACK is +0.1154 [0.0307,0.2001]; calibrated minus matched-fallback
  PRR-product is +0.0026 [-0.0055,0.0107]. This does not show strong-baseline
  superiority.
- [complete] Independent static and isolated audits found no clear calibrated
  ACK advantage over the old heuristic or PRR-product. Static calibrated minus
  old is +0.0004 [-0.0741,+0.0748]; isolated is +0.0208
  [-0.0129,+0.0546], with 480/480 equal candidate sets. These are holdout
  controls, not tunable development results.
- The first ICC TeX patch failed its exact context check at the Related Work
  paragraph; no source bytes changed. Re-read the current lines and retry
  narrower hunks rather than repeating the same patch.
- [in_progress] Revise the ICC source around the now-audited 2.1.24 primary,
  static and isolated evidence. The short-TTL report is present, but its
  paired interpretation still needs independent raw-CSV verification.
- The first pdfLaTeX build failed on missing `pcrr7t.tfm` at the manuscript's
  sole `\texttt{}` usage. `kpsewhich` confirmed the Courier metric is absent
  while standard `cmtt10` exists. Replaced the optional monospaced prefix
  with prose; rerun the exact build to verify the isolated hypothesis.
- [complete] pdfLaTeX/BibTeX now compile with IEEEtran 10-pt Letter to five
  pages, all fonts Type 1 embedded, English-only authors `Zu Gao` and
  `Zhi Quan`, and no unresolved citations/references or overfull boxes.
- [in_progress] Visual page QA found the fifth page contains only the latter
  bibliography entries with excessive blank space. Improve content/float
  balance before copying the new PDF to the repository root or publishing.
- [pending] Revise/rebuild the ICC paper from audited evidence, run final
  gates, and publish the verified versioned release.

### 2.1.24 Final Layout Gate - 2026-09-25

- [complete] Confirm the manuscript and rebuilt PDF print `Zu Gao` and
  `Zhi Quan` in the requested order; no author-name edit was needed.
- [complete] Correct the ETX/ETT wording and replace `preregistered` with
  `prespecified`, consistent with the recorded pre-holdout freeze.
- [complete] Rebuild a five-page IEEEtran 10-pt Letter PDF with Type 1 embedded
  fonts and balanced final-page reference columns; the repository PDF still
  needs replacement after final content and visual checks.
- [complete] Add a compact, traceable secondary-metrics table using the
  already frozen 51--70 fading CSV, then recheck page balance and citations.
- [complete] Replace the root PDF with the rebuilt five-page artifact;
  source and root PDF print `Zu Gao`, `Zhi Quan`, and root/build SHA-256 match:
  `42df9f02cf7c6306c32566fb18017a31d6906da89d984f7fc72c45084d6b6f72`.
- [complete] Selectively commit/push 2.1.24 and verify the remote PR.
- A new Python-rendered plot is paused because `matplotlib` is unavailable
  and the earlier installation question has not been answered. Do not insert
  the unused 2.1.23 TikZ figure as 2.1.24 evidence.

### 2.1.24 Final Publication - 2026-09-25

- The source, tests, frozen CSVs/reports, five-page PDF, and Markdown state
  were committed as `76b40429ed1b6511246c885001317c63fa9d3729` and
  pushed to GitHub `version/v2`. The remote branch and draft PR 1 head were
  independently verified at that exact SHA.
- PR 1 remains OPEN/DRAFT with title
  `[codex] MeshEcho 2.1.24 ICC fading holdout and score audit`.
- GitHub's PDF blob SHA matches the local tracked PDF blob; the reviewed PDF
  is five 10-pt Letter IEEEtran pages, English-only, with `Zu Gao` and
  `Zhi Quan` in the requested order.
- Author confirmation of funding/conflict declarations, final EDAS metadata,
  registration, and submission remain outside this repository release.
- A default-branch GitHub content lookup returned 404 for the PDF; repeating
  it with `ref=version/v2` found the exact matching blob. The first lookup
  did not indicate a failed push.

## ICC 2027 Pre-submission Strengthening Plan - 2026-09-26

- [complete] Audit the current 2.1.24 manuscript, experiment runners,
  result coverage, and the live ICC 2027 deadline/format requirements.
- [complete] Create a deadline-ordered strengthening plan with exact evidence
  gaps, feasible commands or required implementation work, runtime estimates,
  independent seed rules, decision thresholds, and fallback manuscript claims.
- [complete] Verify the plan against frozen holdout integrity and current
  repository state; record the final handoff in `findings.md` and `progress.md`.

Draft deliverable: `docs/icc2027_pre_submission_strengthening_plan.md`.
Runtime is specified as simulation-cell counts because no measured wall-clock
benchmark exists; the future execution protocol requires a timing pilot.

Verification edit note: the first large plan-revision patch failed an exact
context match and changed no files. Continue with narrow patches against the
read-back document; do not repeat that failed patch.

Final planning result: the documented P1 is a 20-seed, five-policy,
non-saturated 18-km random-per-flow stress check with a unique 2.1.25
future output prefix, explicit interpretation limits, and author-only
submission gates. Scientific and CLI audits of the revised plan are complete.
No new simulation or manuscript/code edit was performed; 2.1.24 remains
the released evidence baseline. The plan and checkpoints are local Markdown
changes, not a new GitHub release.

Scope: planning and read-only checks only. Do not edit the algorithm, rerun
seeds 51--70, overwrite versioned results, or treat the overall ICC acceptance
rate as this manuscript's probability of acceptance. Preserve the unrelated
untracked LaTeX build directories. Before context compression, update all
three root checkpoint Markdown files; after resuming, read them first.

### 2026-09-26 Plan Completion Re-audit

- [complete] Re-read the three root checkpoints and the full strengthening
  plan after context recovery; `git diff --check` passes. The plan covers
  evidence limits, prioritized experiments, frozen seeds/outputs, inference,
  manuscript branches, deadline, compliance, and versioned release gates.
- [complete] Verify that ICC 2024 and 2025 official presenter pages say
  Technical Symposia acceptance was less than 40%; no ICC 2027 acceptance
  rate or paper-specific probability exists yet.
- [pending execution, outside the planning deliverable] The proposed P1
  random-pair cohort has not run; author checks of ICCT status and EDAS
  closing time remain open. Do not represent the plan as new evidence.

## ICC 2027 High-Confidence Submission Strategy - 2026-09-26

- [complete] Assess the current evidence and contribution gap without
  mapping any quality gate to a guaranteed or calibrated 50% probability.
- [complete] Separate the feasible Oct 2 submission path from a longer
  research path for a new mechanism and independent validation.
- [complete] Record concrete G0--G4 readiness gates, P1 go/no-go rules,
  prior-work/ICCT overlap checks, and versioned future work in
  `docs/icc2027_high_confidence_submission_strategy.md`. Independent
  scientific and CLI reviews corrected probability, exposure, metric, and
  timeline wording. No algorithm change or simulation was authorized or run.
- [complete] Restore the plan after context compression and confirm G2 offers
  two prespecified alternatives: an ACK-reliability gain with bounded airtime
  and energy, or an ACK-noninferior airtime/energy improvement. The authors
  must select one before a future new-method holdout; neither implies a
  calibrated 50% acceptance probability.
- [complete] Recheck the current paper and frozen fading report; the
  strong-baseline advantage remains unproven. P1 seeds 2001--2020 have not
  run, and ICCT status plus the exact EDAS closing time still require author
  confirmation. This turn remains a planning-only handoff.
- [complete] Apply independent statistical review to G2: distinguish the
  +0.03 point target from a proved lower bound, use paired cost and ACK
  noninferiority intervals, and require fixed-input evidence before causal
  score attribution. The strategy and P1 plan now agree on these limits.
- Recovery note: the planning skill's `python` catch-up command failed because
  only `python3` is available; rerunning with `python3` succeeded.

## ICC 2027 EDAS Submission - 2026-10-02

Goal: submit the verified MeshEcho manuscript to the ICC 2027 IoT & Sensor
Networks Technical Symposium, without certifying facts not confirmed by the
authors or uploading a stale PDF.

- [complete] Recover repository state and verify official deadline update:
  the ICC site now says 16 October 2026, not the old 2 October date.
- [complete] Open the logged-in EDAS IoT & Sensor Networks registration form;
  the new-paper workflow is available. Exact EDAS closing time is unverified.
- [in_progress] Audit the current PDF/source, author list, originality/ICCT
  status, and final disclosure wording. The user reports ICCT was withdrawn
  or rejected, but both authors' approval and funding/conflict facts remain
  to be recorded. EDAS profile confirms the submitting account is Zu Gao.
- [complete] Make two necessary manuscript wording corrections, rebuild and
  inspect the five-page PDF, and replace the repository PDF with the exact
  verified build (SHA-256 `26c67e1391dd6221927370ef725de064260ede310d6a927c3003a1415db2ad24`).
- [pending] Confirm author facts and whether a funding/conflict statement
  must be added; rebuild if any final manuscript text changes.
- [pending] Register the EDAS paper, add both authors in the correct order,
  upload the verified review PDF, and capture a submission confirmation.

Current EDAS account shown in the UI: bh4me@chinaham.org. Do not infer that
this account is one of the two authors. Do not check the EDAS certification
until author-list accuracy, simultaneous-submission status, and final PDF
are verified. Preserve two unrelated untracked LaTeX build directories.

## ICC 2027 Submission Resume - 2026-10-03

Goal: register and upload the current five-page no-MASS-citation MeshEcho PDF
to ICC 2027 IoT & Sensor Networks, with Zu Gao first and Zhi Quan second.

- [in_progress] Check the user's reported MASS withdrawal against the live
  EDAS record and reconcile any conflicting status before certifying no
  simultaneous submission. Live EDAS still says `Accepted as poster`; the
  user's organizer confirmation and CPS final-file status are outstanding.
- [complete] Verify the exact local PDF, title, author order, and current ICC
  registration form; preserve unrelated worktree changes. Independent PDF
  audit passed; the ICC account has no existing paper in this symposium.
- [pending] Register the paper, add Zhi Quan using the supplied institutional
  email, and verify both EDAS author records match the PDF.
- [pending] Upload the verified PDF and confirm EDAS shows a valid submission
  with a paper ID and both authors.
- [pending] Record the final state in progress/findings/checklist; do not
  describe the paper as submitted until EDAS confirms the upload.

The submitting author explicitly confirmed the EDAS declaration and directed
registration. EDAS created paper `1571361802`, with Zu Gao as first author;
its current status is `Pending (no manuscript)`. Zhi Quan and the PDF are not
yet added, so registration is not a completed submission.

## ICC 2027 Baseline-Centered Manuscript Revision - 2026-10-03

Goal: revise the five-page ICC manuscript around the current calibrated
MeshEcho policy versus the repository's Meshtastic-like and MeshCore-like
behavior models. The user explicitly does not want the old MeshEcho score used
as the main comparison. Preserve the scientific PRR-product control and all
adverse results; do not claim evaluation of either project's actual firmware.

- [in_progress] Audit the dirty worktree, current manuscript, baseline models,
  and existing 2.1.24 artifacts without discarding prior changes.
- [in_progress] Run and version same-seed, same-traffic three-way evidence for
  the 51--70 repeated-pair fading case and a separate unconditioned
  random-pair case; inspect per-seed denominators, trace hashes, paired
  confidence intervals, and metric semantics. Label any reused holdout
  comparison as exploratory. The repeated-pair CSV/summary/report exist under
  `meshecho_v2_1_25_icc2027_baseline_feedback_fading`; independent numerical
  audit passed. The unconditioned random-pair case is running under seeds
  2001--2020; its outcome remains unknown at this checkpoint.
- [pending] Revise the LaTeX abstract, motivation, methods, results, limits,
  and conclusion using the two behavior-model baselines and balanced ACK,
  destination-delivery, airtime, and modeled-energy comparisons. Keep within
  the ICC initial-submission page limit and verify citations.
- [pending] Rebuild and inspect the PDF, run relevant tests/data checks, update
  versioned evidence and submission checklist, and record final state in all
  three checkpoint Markdown files.

Current EDAS paper 1571361802 remains `Pending (no manuscript)`. Do not alter
EDAS or author records during this manuscript-revision task. Before any context
compression, update `task_plan.md`, `findings.md`, and `progress.md`; after
compression, read them before resuming.

### 2.1.25 Continuation Checkpoint

- [complete] Save and independently audit both four-policy datasets. The
  random sparse-fading experiment finished on seeds 2001--2020 with 813
  unicasts per policy. It is an unconditioned random-pair stress case, not a
  guaranteed multihop or candidate-controlled test.
- [complete] Bump `VERSION` and ICC script default prefixes to `2.1.25`; the
  release-metadata regression test passes. No ICC PDF has been rebuilt yet.
- [in_progress] Correct the random report's omitted fading CLI flags with a
  failing test first, then regenerate only the Markdown report.
- [pending] Rewrite the five-page paper around calibrated MeshEcho versus
  Meshtastic-like and MeshCore-like; retain PRR+fallback as the score-novelty
  control, update citations and limitations, compile/render, and run checks.
- [pending] Update release notes/checklist and record final artifact status.

In the random stress case, Meshtastic-like exceeds MeshEcho in ACK and
destination delivery while using much less aggregate TX airtime. This negative
result is mandatory in the abstract/results. The 51--70 baseline additions
were run after inspecting those holdout seeds and must be called exploratory.

### 2.1.25 Final State - 2026-10-03

- [complete] Correct the fading reproduction command with a red-then-green
  regression test and update the existing random-case report without rerunning
  or overwriting simulation CSVs.
- [complete] Center the ICC manuscript on three protocol ideas (current
  MeshEcho, Meshtastic-like, MeshCore-like) plus PRR-product with matched
  fallback as an internal score control. Include both workloads and the
  adverse random-pair result; retain the five-page IEEE PDF format.
- [complete] Verify 140 tests, no LaTeX overfull/undefined warnings, embedded
  fonts, all rendered PDF pages, and exact root/build PDF SHA-256
  `fe2899dbbeec32e42428e5883e8baccf0058b76a897375eb58be44a12269cbd4`.
- [complete] Commit only related release files as `0d3d724` and push
  `version/v2`; remote and local SHA match. Draft PR 1 title/body now say
  2.1.25. Unrelated strategy drafts, checkpoint Markdown changes, and
  LaTeX build directories remain uncommitted and were not removed.
- [pending outside this revision] EDAS paper `1571361802` still says
  `Pending (no manuscript)`; add Zhi Quan, update its abstract, upload the
  revised PDF, and verify submission only when the user resumes that task.

The optional new-figure subtask is paused under the figure skill because a
Python-or-R backend was not selected. Exact comparison tables remain in the
verified manuscript; no graph was generated or inserted.

### 2.1.26 Baseline Presentation and Identity Revision - 2026-10-03

- [complete] Clarify in the ICC manuscript that the evaluated MeshEcho row
  is the optional `meshecho-calibrated` variant, not the legacy/default CLI
  policy. Keep the two named baselines labeled as stylized models and PRR+fb
  as an internal score control.
- [complete] Add a Python-generated, CSV-traceable two-panel delivery figure
  for the three protocol-family models only. Preserve the exact paired
  comparisons and PRR+fb control in tables; do not rerun or overwrite the
  frozen 2.1.25 full experiment CSVs.
- [complete] Bump release metadata to 2.1.26, add focused tests and a current
  one-seed simulator smoke, rebuild/inspect the five-page PDF, and run the
  full suite.
- [complete] Selectively commit and push `version/v2` and update draft PR 1.
- [complete] Independently check the figure data and PDF page count/legibility.

The user previously delegated whether to add a bar figure. Python is selected
for this revision because the simulation pipeline and source data are Python
and CSV. Matplotlib/SciPy were initially missing from both local Python
runtimes; an isolated `uv run --with matplotlib --with scipy` environment now
works. Before any future context compression, update all three root
checkpoint Markdown files; after resuming, read them first.

Compilation attempt 1 failed because TinyTeX lacks the Courier `pcrr7t`
font required by a new `\texttt` phrase. Replace only that markup with
ordinary quoted CLI names and rerun; no simulation or result changed.

The final candidate PDF is five pages, US Letter, 10-point IEEEtran,
SHA-256 `25bf5d25c70816c457640f232c2e657ba546e4d3f4d420c053824af11eb8443a`.
All five pages were inspected; no clipping or overlap. `pdffonts` shows
embedded Type 1 text and embedded TrueType chart fonts. The root/build PDF
hashes match and the final log has no overfull/undefined warnings.
`python3 -m pytest -q`: 142 passed, 1 skipped (Matplotlib absent from system
Python); isolated Matplotlib 3.11.2 focused run: 3 passed. Seed-51 smoke
matches every field of all four frozen 2.1.25 rows.

Independent audit recomputed all six chart rows and flagged that the global
`*.pdf` ignore rule hid the new included figure PDF. A narrow exception for
`paper/icc2027/figures/fig_baseline_delivery.pdf` has been added; verify it
is staged before committing so a clean checkout can rebuild the manuscript.
The first combined patch failed because its task-plan context did not match
the actual line wrap; no files changed in that attempt, and the corrected
patch applied successfully.

The first staged `git diff --check` failed on Matplotlib SVG path-line
whitespace and CSV CRLF. A red/green export test now enforces clean SVG
line endings and LF CSV; the generator was updated, figure/PDF regenerated,
and the staged whitespace check passes. The latest PDF hash above differs
from the prior candidate due to regenerated figure metadata, but the
final-page raster is byte-identical to its predecessor. All five pages had
already been inspected in the prior build.

### 2.1.26 Final Publication State

- Committed only the 19 intended release files as `78ffb6e` and pushed
  `version/v2`. GitHub reports remote head
  `78ffb6ebf33d5dc51eaf65057321c76c8ab5391e`.
- Draft PR 1 title/body are updated to 2.1.26, with the negative random-pair
  result, model limitations, and EDAS pending state retained.
- GitHub serves the included figure PDF at blob
  `21bf59b3fd437edbaf357b93d7ee138a21d45449`, matching the local
  committed object. A clean `git archive HEAD paper/icc2027` builds the
  manuscript to five Letter pages with no overfull/undefined warnings.
- Final validation after the export normalization: 142 passed, 1 skipped in
  standard Python; 3 focused figure tests passed with Matplotlib. The final
  root PDF SHA-256 is
  `25bf5d25c70816c457640f232c2e657ba546e4d3f4d420c053824af11eb8443a`.
- Existing user strategy drafts, checkpoint Markdown files, and LaTeX build
  directories remain local dirty/untracked state. No EDAS change was made.
- A GitHub Contents query first failed because unquoted `?` was expanded by
  zsh; the quoted query succeeded. An optional `git ls-remote` check was
  briefly slow, then exited; GitHub API/PR state supplied remote proof.

## 2026-10-03 - Distinct MeshEcho Variant Research

Goal: research one falsifiable MeshEcho variant whose actual forwarding and
recovery decisions differ materially from current Meshtastic and MeshCore,
without treating a renamed known metric or flood-first caching as novelty.
This research does not change the submitted ICC manuscript or EDAS record.

- [in_progress] Verify current 2.1.26 behavior, packet-cost model, official
  product mechanisms, and relevant prior art.
- [pending] Specify one implementable, source-observable policy with explicit
  state, decisions, packet exchanges, and resource bounds.
- [pending] Challenge novelty and simulator validity; define strong product-
  inspired controls and a frozen evaluation contract.
- [pending] Produce a research artifact and decide whether a prototype and
  new versioned simulation are justified by the evidence.

Initial evidence: random traffic has 807 route discoveries for 813 flows and
only five cache hits, while recurring traffic has 525 cache hits. Both current
Meshtastic and MeshCore already learn routes after initial flooding. The
simulator charges every packet as 32 bytes regardless of kind or path length.
Do not claim that a basic flood-first cache is a new MeshEcho contribution.
Preserve all pre-existing dirty files and build directories.

### Research Error Log

| Error | Attempt | Resolution |
| --- | --- | --- |
| GitHub raw FAQ `curl` reset the connection | 1 | Opened the official GitHub FAQ in the in-app browser and verified sections 5.3--5.4 there. |
| First shadow-refresh research patch missed a wrapped line | 1 | Inspected exact context and applied a smaller patch; no partial changes from the failed attempt. |
| Research-audit patch missed a wrapped paragraph | 1 | Inspected exact current text and applied smaller context-specific edits; no partial changes from the failed attempt. |

### Updated Research Objective and Recovery

The user now wants a distinct *new algorithm* for MeshEcho, with nRF52 and
ESP32-S3 as deployment targets; lightweight online learning is acceptable but
must earn its complexity. Before any automatic context compression, write the
current hypothesis, evidence, limitations, and next action to this file,
`findings.md`, and `progress.md`. After compression, read all three plus
`git status` before continuing. The 2.1.26 manuscript is not to be silently
rewritten to describe an unimplemented algorithm.

- [completed] Recover the 2.1.26 state and verify the route-discovery and
  official Meshtastic/MeshCore mechanism boundaries.
- [completed] Specify source-local F/R/D decisions, observables, packet
  costs, and memory/compute envelope for nRF52/ESP32-S3 in the standalone
  research brief.
- [completed] Review the brief's novelty objections, faithful baselines,
  experiment pass/fail gates, and staged prototype decision.

### Research Completion and Next Execution Gate

- Research artifact: `docs/research/meshecho_shadow_refresh.md`. Candidate
  MeshEcho-SR uses source-local F/R/D action selection. D has a demand-gated
  cold-discovery case and a pre-failure aging-route case; the destination
  still selects one RREQ candidate and sends one RREP. Candidate DATA is
  sent once, and the old route is replaced only after source ACK. The current
  D flow can be harmed; this is explicitly measured rather than hidden.
- The artifact distinguishes its mechanism from *documented* Meshtastic and
  MeshCore behavior but does not claim global firstness or measured gain.
  The strongest same-trigger alternative is F, which sends useful DATA and
  can learn a route in one flood. F/R-only, age-triggered F, equal-budget
  periodic refresh, and product-faithful controls are mandatory.
- Start a prototype only after packet-type/path-length ToA and ACK semantics
  are corrected. Then implement F/R/D with source-only observables, paired
  controls, frozen independent workloads, and physical tests on the exact
  nRF52 and ESP32-S3 boards. Drop D if it does not repay control cost and
  current-flow harm. No prototype, simulation, manuscript, version bump,
  GitHub push, or EDAS action was authorized or performed in this research
  phase.

## 2026-10-03 - MeshEcho-SR Simulation and ICC Manuscript Revision

Goal: implement and independently evaluate the specified MeshEcho-SR policy,
then substantially revise the existing five-page ICC 2027 LaTeX/PDF around
the *measured* result, including negative findings if SR does not win. This
goal does not authorize EDAS upload or changing product firmware. The prior
goal turn made progress by producing a reviewed algorithm specification;
it did not implement or validate the policy.

Paper configuration inherited from the existing artifact: English,
IEEEtran conference/US Letter/10 pt, five pages, IEEE citations, authors
Zu Gao and Zhi Quan at Shenzhen University. Preserve confirmed authorship
and avoid unsupported funding or hardware claims.

- [in_progress] Revalidate current source, paper, test runner, and dirty
  worktree; freeze packet-size, ACK, workload, and comparator contracts.
- [pending] Test-first packet-length-aware LoRa airtime, collision, and energy
  accounting; independently audit the changed legacy outputs.
- [pending] Test-first SR F/R/D state machine with sender-only feedback,
  tentative route promotion, token/cooldown rules, and per-flow action logs.
- [pending] Add F/R-only, same-trigger F, equal-budget periodic refresh,
  and current/fair product-inspired comparisons without changing ACK
  semantics silently.
- [pending] Run development and untouched holdout scenarios with paired
  seeds, analyze both reliability and complete airtime costs, and preserve
  reproducible versioned raw evidence.
- [pending] Rewrite the ICC manuscript, tables/figure and references to
  match actual SR evidence; rebuild/inspect all pages and validate limits.
- [pending] Run focused/full tests, release metadata consistency, numerical
  audit, and final requirement-by-requirement completion review.

Before automatic context compression, update this plan plus `findings.md`
and `progress.md` with exact completed work and next action. On resumption,
read those three files and `git status` before doing new work. Existing
dirty strategy drafts, unrelated builds, and EDAS state remain untouched.

### Current Work Division

- `packet_airtime_impl` owns simulator packet/radio airtime code and focused
  tests until it reports completion; root must not edit those lines in
  parallel.
- `sr_experiment_contract` performs read-only runner/evaluation audit.
- Root owns planning, manuscript evidence map, later SR implementation and
  paper edits. A third agent request was rejected by the thread limit; the
  root performs manuscript architecture locally instead.

### 2026-10-03 SR Prototype Checkpoint

- [complete] Test-first byte-aware transmission, energy, and collision-window
  correction; 147 passed, 1 skipped before SR edits. This changes the old
  paper's numerical basis, so 2.1.26 airtime/energy results cannot be reused.
- [in_progress] Test-first SR state machine and four registered mechanism
  policies (`meshecho-sr`, `-fr`, `-trigger-f`, `-periodic`). Eight focused SR
  tests pass; candidate/ACK and fallback behavior still need edge-case tests.
- [in_progress] Separate test-first SR experiment runner, owned by
  `sr_experiment_contract`; root owns `lora_mesh_sim.py` and SR tests.
- [pending] Product-faithful behavioral controls, full simulation matrices,
  independent numerical audit, five-page manuscript/PDF, versioned publish.
- The official ICC 2027 deadline was verified earlier as 2026-10-16; the old
  October 2 date in an untracked strategy draft is stale.

Next: test delayed/invalid ACK and source RREP timeout, cap source state to
eight destinations, integrate the runner, run full tests, then freeze the
development/holdout matrix before inspecting results. No SR results or paper
claims exist yet; no EDAS/GitHub action in this continuation.

### 2026-10-03 SR Validity Gate After Context Recovery

- [complete] Re-read this plan, `findings.md`, `progress.md`, and Git status in
  the `lora_mesh_current_version_v2` checkout. The dirty worktree and prior
  2.1.26 commit remain intact; no release or EDAS action has occurred.
- [complete] Integrate the four-policy SR experiment runner and its focused
  tests. It has not run the full development or holdout matrices.
- [in_progress] Fix two source-observability bugs before using SR results:
  destination-side empty-candidate closure currently triggers DATA fallback
  before the sender's RREP deadline; queued source DATA can be marked as an
  ACK miss before its actual TX start.
- [pending] Recheck fixed-memory state, PHY-dependent discovery timing, and
  common-ACK product controls; then rerun focused/full tests and freeze the
  experiment contract.
- [pending] Run all development seeds first, assess D exposure and fair
  comparators, and only then run untouched holdout seeds once. Rewrite the
  ICC manuscript only if the new evidence supports its precise claim.

The user has asked whether a better algorithm could improve ICC prospects.
Treat age-triggered useful-DATA flooding as a serious alternative to D:
its first transmission delivers payload and can learn a route without
RREQ/RREP. Neither option has demonstrated a population-level advantage.
Do not promise or assign a numerical acceptance probability from a pilot.

### Development-Only Decision, 2026-10-03

- [complete] Red/green-fix premature no-candidate fallback and ACK timeout
  before source TX start. Add common-ACK product-control registration and
  align late-ACK/application-deadline handling. Full suite: 185 passed,
  1 skipped; `git diff --check` passes.
- [complete] Run the fixed development cohort once: 20 seeds x 4 SR policies.
  SR has positive paired ACK gains over F/R-only and same-trigger F, but
  fails both prespecified +10% relative-airtime upper-bound gates. Its
  output equals the periodic-D control exactly in this repeated-pair case.
- [blocked pending model correction] Independent timing audit found the
  source-started 2-s destination candidate window excludes nearly all
  four-hop RREQs and cannot be implemented at the destination without a
  transmitted start time. Move window start to first destination RREQ,
  choose a PHY/hop-valid window and source deadline, and apply the same
  contract to matched discovery policies before treating new results as
  manuscript evidence. This is a scientific validity gate, not a lack of
  computational resources.
- [pending] After timing correction, rerun development; retain the previous
  output as invalidated exploratory data. Keep holdout seeds 4001--4040
  untouched until controller and timing contracts are frozen.

No ICC manuscript/PDF rewrite, version bump, GitHub push, or EDAS change has
been made for SR. The existing paper still describes the 2.1.26 model.

## 2026-10-03 Updated Goal: Rewrite Core SR Controller

The user explicitly expanded the active goal: major ICC paper revision and
new simulations based on MeshEcho-SR now also require rewriting the **core
algorithm**, not merely tuning the 180-s/2-send age rule. Retain the packet,
ACK, and F/R/D harness where valid; replace the source decision policy with
one explicit, deployable, airtime-aware rule. Do not claim a benefit until a
fresh development rerun and untouched holdout verify it.

- [complete] Agent-owned test-first destination-local discovery timer and
  PHY/hop-valid source wait; corrected matched native-discovery source wait.
- [complete] Independent review of a replacement controller, with
  source-only observations, fixed memory, and a clear distinction from
  periodic refresh and product flood/cache behavior.
- [in_progress] Implement replacement controller test-first, retaining old SR
  as a named comparator. Initial MAG F/R/D rule and feedback tests pass; next
  add matched no-D, same-trigger F, and periodic-D controls and runner gates.
- [pending] Run corrected development matrices, then once-only untouched
  holdout and robustness scenarios; audit complete TX airtime, deadline PDR,
  D exposure, route changes, and adverse outcomes.
- [pending] Major rewrite of five-page ICC source and figure/table, compiled
  PDF inspection, citations/prior-work disclosure, versioned result release,
  tests, and numerical audit. No EDAS upload is authorized by this goal.

### Updated-Goal Error Log

| Error | Attempt | Resolution |
| --- | --- | --- |
| Assumed `paper/icc2027/icc2027_lora_mesh.bib` existed | 1 | `rg --files paper/icc2027` confirms the bibliography is `paper/icc2027/references.bib`; the `.tex` source uses `\\bibliography{references}`. |
| Requested an additional novelty-audit agent after reaching the thread limit | 1 | Continue the source/literature audit locally; existing timing and feasibility agents remain independent. |
| First discovery-TTL patch matched MeshCore's same-named method | 1 | Restored MeshCore's original max-hop TTL and applied the hook only in CalmMesh/MAG; targeted MAG and matched-discovery tests pass. |

### Controller Decision Gate - 2026-10-03

- Rewriting the core means replacing SR's fixed-age/2-send F/R/D selection rule, not discarding the tested packet, relay, ACK, and route-candidate machinery.
- Candidate replacement: source-observable route-risk signal plus a packet-airtime, demand, deadline, and token gate for proactive D; preserve the old SR rule as a comparator. A measured forward-hop SNR margin returned by ACK may be needed, but its on-wire bytes and baseline parity must be implemented and tested before it can be an algorithm input.
- Primary falsification remains the same-trigger useful-DATA flood and F/R-only. A positive discovery-vs-periodic distinction alone is insufficient. Retain seeds 4001--4040 untouched until timing, wire format, thresholds, and endpoints are frozen.
- The draft algorithm and comparator contract is in `docs/research/meshecho_mag_design.md`; it is a hypothesis, not evidence of performance. One failing packet-field regression test has been added as the first TDD slice; do not run the matrix while it is red.
- Timing handoff passed 191 tests, one skip before MAG tests. Root's MAG slices now include one-byte optional margin, two-hop ACK feedback, measured-risk D, lost-ACK isolation, and slow-PHY deadline gate. Full suite: 196 passed, one skipped; no new matrix run yet. The earlier "red" statement above records the initial TDD state, now resolved.
- The matched MAG F/R-only, same-trigger useful-DATA F, and equal-token periodic D variants are implemented with the same feedback byte and candidate scorer. An out-of-order older R ACK no longer contaminates a newer confirmed route's margin history. Runner marks only holdout MAG-vs-F/R and MAG-vs-trigger-F as confirmatory. Full pre-development regression: 202 passed, one skipped; one-seed smoke is diagnostic only and shows meaningful D exposure but large cost.

### MAG Development Gate 1 - 2026-10-03

- [complete] Run 20 development seeds x four MAG/matched policies with corrected discovery timing and byte-accounted margin feedback. Artifacts: `results/meshecho_mag_research_recurring_fading_dev_20261003.{runs.csv,paired.csv,flows.jsonl,actions.jsonl,manifest.json}`. Source hashes are in the manifest.
- [failed] MAG versus F/R-only: ACK PDR gain +0.1349, 95% paired CI [0.0859, 0.1839], but relative whole-network TX-airtime cost +0.3207 [0.2361, 0.4053], exceeding the prespecified +0.10 upper-bound gate.
- [passed on development only] MAG versus same-trigger F: ACK gain +0.1371 [0.0915, 0.1828], relative airtime -0.1191 [-0.1728, -0.0654]. This does not rescue the failed F/R gate.
- [not distinctive in outcome] MAG versus periodic D: ACK gain +0.0083 [-0.0487, 0.0652], relative airtime +0.1357 [0.0748, 0.1965]. Both policies use about four D decisions per run; only nine of their 76/78 D decisions occur on the same seed/flow id.
- Do not run holdout or rewrite the ICC paper around this failed version. One development-informed rule revision is justified: when measured risk exists but D's demand/cost/deadline gate rejects it and the old confirmed route has not met the failure/staleness trigger, use R instead of another expensive F. Test this change first and rerun development under a separate artifact prefix. Keep 4001--4040 untouched.

### MAG Development Gate 2 - 2026-10-03

- [complete] TDD revision of rejected-risk action F to R; full suite 203 passed, one skipped before replay. The separate `dev2` matrix is saved under `results/meshecho_mag_research_recurring_fading_dev2_20261003.*` with source hashes.
- [failed] MAG vs F/R-only: ACK gain +0.1386 [0.0886, 0.1887], relative airtime +0.132 [0.048, 0.216]. Upper bound still exceeds +0.10. MAG vs same-trigger F passes development; MAG vs periodic D has ACK gain +0.0120 [-0.0345, 0.0585] and relative airtime -0.028 [-0.087, 0.030], neither distinguishable.
- [in_progress] One structural, test-first cost reduction: cap proactive RREQ to the confirmed path's hops plus one, shared with periodic-D and accounted in the source cost proxy. This is an existing constrained-discovery idea, not a standalone novelty claim. Run full regression, then a separately named dev3 matrix. If it still fails, stop tuning and do not open holdout or rewrite the paper as a positive MAG result.

### MAG Development Gate 3 and Stop Decision - 2026-10-03

- [complete] Test-first route-length-bounded RREQ, with identical cap in MAG and periodic-D. Full suite before dev3: 204 passed, one skipped; `git diff --check` and `py_compile` passed. Dev3 outputs are under `results/meshecho_mag_research_recurring_fading_dev3_20261003.*` with source hashes.
- [failed narrowly] MAG vs F/R-only deadline ACK gain +0.1556 [0.1066, 0.2045]; relative whole-network TX-airtime +0.050 [-0.027, 0.128]. The 95% upper bound +0.128 is above the prespecified +0.10 budget, despite a lower +0.050 mean.
- [development only] MAG vs same-trigger F: ACK gain +0.1691 [0.1180, 0.2203], relative airtime -0.074 [-0.127, -0.022]. MAG vs periodic D: ACK gain +0.0274 [-0.0215, 0.0763], relative airtime -0.070 [-0.129, -0.010]; no distinguishable reliability gain over periodic D.
- Stop tuning this F/R/D discovery design on the 20 development seeds. Keep holdout 4001--4040 closed. The remaining route to a stronger algorithm is a separately specified low-overhead discovery or useful-data probing mechanism, not post hoc relaxation of the +10% gate. That is a new design/evaluation phase; the current five-page ICC manuscript and published 2.1.26 release remain unchanged until a valid new claim exists.

## 2026-10-03 Core-Mechanism Redesign (active goal continuation)

Goal: replace MeshEcho-SR's core route-acquisition/repair algorithm, run a
falsifiable simulation evaluation, and substantially revise the ICC manuscript
only from verified evidence. The previous read-only decision turn established
that threshold tuning of MAG is insufficient; it changed the next action but
made no code or paper edits. This section is the active plan, not a claim of
completion.

- [in_progress] Specify one source-observable, bounded-memory, low-overhead
  useful-DATA discovery/repair mechanism. Audit prior art and define its
  packet, duplicate, ACK, timeout, and route-commit behavior before coding.
- [pending] Implement vertical test-first behavior slices while preserving SR,
  MAG, F/R-only, same-trigger useful-DATA flood, and equal-budget periodic
  controls as named comparators. Keep packet bytes and PHY airtime explicit.
- [pending] Freeze endpoint, scenarios, controls, cost budget, and stop rules;
  run new development artifacts with source hashes and paired seed analysis.
  Preserve failed hypotheses and do not tune on holdout seeds 4001--4040.
- [pending] If the development mechanism survives its declared gates, freeze
  the code and run the untouched holdout once; inspect unconditioned random
  pairs and an independent PHY/load stratum as robustness, including adverse
  results and actual route-choice exposure.
- [pending] Major-rewrite ICC title, abstract, method, evaluation, figures,
  tables, related work, and limitations to match audited evidence; compile,
  render, and inspect the PDF, then run full tests and numerical/citation
  consistency checks. Version and publish only a verified release. No EDAS
  submission is authorized by this goal.

Current constraints: the worktree is dirty with prior task work; do not clean
or discard it. The current paper/PDF and VERSION remain 2.1.26. Preserve the
negative dev1/dev2/dev3 MAG evidence. Before each context compaction, update
this file, `findings.md`, and `progress.md`; after resuming, read all three and
`git status` before further task actions.

### LPR Implementation Error Log

| Error | Attempt | Resolution |
| --- | --- | --- |
| First indexed-ACK red test failed because `meshecho-lpr` was unregistered | 1 | Registered an LPR foundation subclass and added the indexed field/wire cost. |
| Indexed-ACK test then found the index missing after useful-DATA flood relay | 1 | Located the distinct CalmMesh `on_fallback()` packet reconstruction and copied the index there as well. |
| Direct-P tracer expected repair at hop 2 but assigned equal weak margins to both hops | 1 | Corrected the test fixture to make the first hop strong and the second hop weak; tie-breaking itself was behaving as specified. |

### 2026-10-03 LPR Recovery and Safety Gate

- [complete] Re-read `task_plan.md`, `findings.md`, `progress.md`, the LPR
  contract, and Git status after context recovery. The previous turn yielded
  an independent safety review that changes the next implementation actions.
- [complete] The fourth focused test confirms a source-origin PATCH starts an
  ACK timer and a lost ACK does not commit a route. Four LPR tests pass; the
  full suite has not been rerun since this timer change.
- [in_progress] Red/green repair of candidate relay cancellation, ACK origin
  validation, P cache-hit accounting, and per-flow state cleanup. Do not run
  population simulations while any of these contract gaps remain.
- [pending] Add LPR matched variants, align packet counts with the 630-s TX
  window, freeze runner/gates, and run fresh development seeds 5001--5020.
- [pending] Open holdout 4001--4040 only after the mechanism and analysis
  contract are frozen and development passes; then evaluate robustness and
  rewrite/verify/publish the ICC paper if evidence supports a valid claim.

The independent safety review found pending relays never canceled, growing
per-flow maps, missing P cache-hit counts, and wrong-origin ACK acceptance.
The relay-cancellation implementation is delegated in isolated LPR code/tests;
the root agent owns the remaining safety/runner integration. An attempted
additional literature agent hit the thread limit; continue that audit locally.

Safety-slice progress: wrong-origin P ACK acceptance and missing P cache-hit
accounting each reproduced with a failing integration test, then fixed with
one guard/counter update. Both tests now pass. Relay cancellation is still in
progress with a separate agent; per-flow state cleanup is next. A runner audit
found that LPR needs separate 5001--5020 development seeds, four equal-feedback
controls, window-consistent packet counts, and an exact frozen-config joint
holdout gate before any confirmatory label. A runner agent owns only the
timestamped packet-window metric slice, not the protocol/seed controls.

Safety cleanup progress: ACKed P flows release the source repair index;
unacknowledged P flows release it just after the 30-s application deadline.
Pending local relay handles are removed when canceled or transmitted, while a
bounded per-node recent-flow list preserves once-per-flow suppression during
that list's horizon. Direct and competing-relay cases each failed on retained
handles before cleanup and now pass. All 10 focused LPR tests pass. Runner
windowed-kind metrics are implemented separately; full integrated regression
and LPR control policies remain next.

Integrated regression after safety and windowed metrics: 216 passed, one
skipped; Python compilation and `git diff --check` passed. The LPR design now
fixes four exact control-policy semantics. Runner entry has an explicit
five-policy LPR suite, fresh 5001--5020 development split, and strict policy
suite check. Paired rows now carry the complete case-config hash and reject
within- or between-seed config mixing. The artifact writer refuses existing
output paths, and an under-20-seed smoke cannot pass the reliability/cost gate.
Next: finish the four LPR controls, add exact-case/freeze and manifest
integrity gates, then run only a custom smoke and development matrix.

### 2026-10-03 Core-Rewrite Clarification

- [complete] Confirm that improving the ICC method claim requires replacing
  the route-acquisition/repair decision, not another SR/MAG threshold change.
  LPR's ACK-indexed useful-payload segment repair is that candidate core
  rewrite; packet/radio simulation and F/R baselines remain shared test
  infrastructure.
- [complete] Integrated LPR plus four matched controls pass the full local
  regression: 229 passed, one skipped; `git diff --check` passes.
- [in_progress] Freeze exact LPR holdout eligibility and joint comparator
  gate; audit relay/ACK safety before population simulation. No LPR
  development or holdout matrix has run yet.
- [complete] Runner now requires exact LPR scenario/deadline/suite/seeds,
  verifies source and development artifact hashes plus all policy rows,
  recomputes paired gates, rejects generic holdout bypass, reports the
  two-control joint gate, and preflights output paths before CLI simulation.
- [complete] Added per-seed P exposure, ACK-confirmed inserted-repair,
  route-switch, and collision counts. Holdout validation enforces the
  predeclared 20-decision/10-inserted-route development sufficiency rule.
- [complete] Reproduced and fixed a P-ACK feedback freshness defect: a
  successful P commit now refreshes the source ACK timestamp. The new
  regression failed F versus expected R before the fix; 17 LPR tests pass.
- [pending] Run one custom smoke, then development seeds 5001--5020.
  Open untouched 4001--4040 only if the predeclared development gate holds.
  Rewriting the ICC paper and publishing a new version remain evidence-gated.
- [complete] Custom seed-5000 LPR smoke completed for all five policies,
  with hash-checked artifacts; it is non-evaluable and never a population
  result. LPR made three P decisions, five PATCH_RELAY transmissions, and
  zero ACK-confirmed inserted-route commits. The development matrix is next.
- [failed; stopped] The frozen 5001--5020 LPR development matrix completed
  (100 runs, 834 unicasts/policy). LPR vs F/R-only ACK gain is +0.0081
  [-0.0245, +0.0407], airtime +4.8% [-2.7%, +12.2%]; vs same-trigger F,
  ACK gain +0.0385 [-0.0003, +0.0772]. Only seven inserted paths were
  ACK-committed, below the prespecified ten. The joint gate is false.
- [blocked by evidence, not execution] Keep LPR holdout 4001--4040 closed;
  do not rewrite/publish the ICC paper as an LPR success. A separate core
  algorithm hypothesis and fresh development split are needed if the user
  wants to continue toward a stronger method paper.

### 2026-10-03 Post-LPR Redesign Continuation

- [complete] Read-only failure audit resolved P outcomes: 69 P decisions,
  45 ACKs on the unchanged path, seven ACK-confirmed inserted paths, 11
  destination-only deliveries, and six non-deliveries. The current LPR
  result remains negative; 4001--4040 holdout seeds remain unopened.
- [complete] Code audit found that `PendingSend.committed` is set at TX
  request time, before a locally queued packet's actual airtime begins.
  This can prevent later cancellation of queued patch relays; the saved
  aggregate artifacts cannot determine its frequency or effect.
- [complete] Independent forensic and passive-reception audits identified
  genuine destination-decoded path diversity on old development seeds and
  selected bounded destination reverse-ACK diversity as the next falsifiable
  hypothesis. A single standby bridge remains a separate, untested idea;
  neither mechanism has proven novelty or performance benefit.
- [in_progress] Prioritize a separately named data-first dual-path ACK
  hypothesis for the next vertical slice: passive destination decodes on
  already-examined 5001--5003 show actual distinct FLOOD paths. Freeze exact
  extra-ACK timing, one- versus two-path policy, equal-ACK-budget control,
  byte accounting, and source duplicate-ACK semantics before fresh seeds.
  Do not treat these exploratory decodes as a gain estimate.
- [pending] Write a new explicit device-local packet/state/timeout contract,
  implement one red/green vertical slice at a time, and freeze matched
  controls plus a fresh development seed split. The previously inspected
  5001--5020 cohort cannot serve as independent validation.
- [complete] Recorded the MeshEcho-DPA destination-local, 3-s/two-ACK
  development contract before code in `docs/research/meshecho_dpa_design.md`.
  Its three modes (diverse, same-trigger first-path repeat, single ACK) now
  pass separate red/green two-branch end-to-end tests. A fourth test drove
  3-s state expiry and a fifth drove the eight-window destination cap.
  Full regression: 255 passed, one skipped; whitespace check passed. This
  is only mechanism feasibility. Same-first-hop/third-path/source ACK
  safety, runner integration, and population experiments remain pending.
- [complete] Added deterministic safety coverage for actual first-path ACK
  failure and second-path rescue, same-source-adjacent rejection, third ACK
  suppression, wrong-source second path, and looped second path. Ten focused
  DPA tests pass. Source-origin/late ACK safety and the independently owned
  runner are next; no DPA population result exists yet.
- [pending] Run the new development matrix, preserve adverse results, and
  open 4001--4040 once only if the predeclared eligibility gate passes.
  Revise the ICC paper/PDF, version, and release only from verified evidence.

Error log: `python` was unavailable for planning catch-up in this shell;
`python3` completed the catch-up without output.
An extra bridge-feasibility subagent request hit the thread limit; continue
that bounded code audit locally while the two active read-only audits finish.
One findings-file patch missed the exact context and made no change; re-read
the file tail and applied the corrected append successfully.
CLI audit found the three DPA names present in `build_protocol` but missing
from `parse_args --protocol` choices; a focused red CLI regression is being
added before registry alignment.

### 2026-10-03 DPA Core-Algorithm Clarification and Safety Gate

- [complete] Clarified that improving the ICC method claim requires a core
  decision-mechanism rewrite, while reusing the packet/PHY simulator and
  matched baseline infrastructure. DPA is a new candidate, not a proven
  algorithmic improvement or a threshold-only tweak.
- [complete] Reproduced first-path ACK emission for a malformed FLOOD path,
  then moved realized-path validation before delivery/ACK. Added source and
  physical-last-hop regression cases; 17 focused DPA tests pass.
- [complete] The integrated suite has 294 passed, one skipped; Python compile
  and `git diff --check` pass. The DPA runner is integrated and tested.
- [in_progress] Run only seed-6000 DPA smoke, then the frozen 6001--6020
  development matrix if smoke artifacts are coherent. Do not open holdout or
  revise/publish the ICC paper unless prespecified evidence gates pass.
- [complete] Seed-6000 custom smoke produced all three policy rows plus
  action/flow/paired/manifest artifacts with source and artifact hashes.
  It is non-evaluable; DPA had nine second-path opportunities and no
  prespecified gate result can be inferred from one seed.
- [in_progress] Freeze code/design/runner hashes and run 6001--6020 once.
- [failed; stopped] The frozen 6001--6020 DPA development matrix completed
  (60 runs, 817 unicasts/policy). Versus single ACK, paired ACK gain is
  +0.1104 [+0.0455,+0.1753] with -15.0% TX airtime. Versus same-trigger
  first-path repeat, ACK gain is -0.0258 [-0.0835,+0.0319] and relative
  airtime is +7.6% [-7.0%,+22.2%]. The joint gate is false.
- [complete] Source/artifact hashes, 20 shared per-seed traffic/config
  signatures, and 179 eligible second-path opportunities across all seeds
  were verified. The 4001--4040 holdout remains unopened.
- [blocked by evidence, not execution] Stop this DPA hypothesis without
  paper/version/GitHub/EDAS promotion. Any structural replacement needs a
  new frozen mechanism and independent development seeds.

### Active Goal Continuation: MeshEcho-SR Core Rewrite and ICC Major Revision

- [complete] Re-read recovery Markdown, current worktree, SR decision code,
  the ICC manuscript, and the negative LPR/DPA development reports.
- [in_progress] Diagnose the DPA-versus-repeat failure at flow/action level
  and verify a structurally different, device-local route/ACK mechanism with
  prior-art boundaries. Two independent read-only audits are running.
- [complete] Independent forensics and prior-art audit converged on a
  DATA-conditioned reverse ACK corridor as the next core hypothesis.
  Recorded its exact local-state, packet, controls, fresh-seed and stop
  contract in `docs/research/meshecho_rac_design.md` before implementation.
- [in_progress] Implement the first RAC real-packet vertical slice through
  a failing integration test; do not run population seeds until safety and
  accounting tests pass.
- [pending] Freeze a new algorithm contract, fresh development split, and
  matched controls before writing implementation or opening new results.
- [pending] Implement with public-behavior red/green tests, full regression,
  one smoke, and a complete frozen seed-paired development matrix.
- [pending] Only a surviving mechanism enters untouched holdout and wider
  robustness checks. Major ICC manuscript/PDF revision follows verified
  evidence, with no unsupported novelty or acceptance claim.
- [pending] Preserve checkpoint Markdown before context compaction and read
  all three records on recovery.

### 2026-10-03 RAC implementation checkpoint

- [complete] First three real-packet RAC slices pass: off-path rescue,
  cancellation after normal continuation, and registered repeat/single-ACK
  controls (`python3 -m pytest -q tests/test_meshecho_rac.py`: 3 passed).
- [in_progress] Add failing behavioral tests and minimal fixes for RAC
  state bounds/expiry, duplicate ACK suppression, validity, and charged
  off-path hop budget. Run full regression before any RAC simulation.
- [complete] Simulator RAC safety and accounting slices: 22 focused tests
  pass, including a collision counterexample. Full integrated regression
  and runner gate integration remain pending.
- [in_progress] RAC runner support is delegated to a separate agent owning
  only `tools/run_sr_experiment.py` and `tests/test_sr_experiment.py`.
- [pending] Run seed-7000 smoke, freeze source/runner/design hashes, then
  run the 7001--7020 development matrix once. Keep holdout 4001--4040 closed
  unless the predeclared joint gate and exposure gate both pass.
- [complete] Seed-7000 RAC smoke ran with all three arms and matching traffic
  hashes; four artifact SHA-256 values match its manifest. It is explicitly
  non-evaluable. Runner seed-isolation and exposure-identity audit fixes are
  required before the 7001--7020 development matrix.
- [complete] Runner audit fixes and final full regression pass: 357 passed,
  one skipped. Frozen RAC source SHA-256 values are recorded below. The next
  exact action is one `rac-development` run of 7001--7020; do not edit these
  four hashed inputs during the matrix.

| Frozen input | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `fd3c47f69c5e9b6dbd79fa36dc39a08d8a3b30aa6226ba9d1a1f6c98c035b1bc` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `be22ed8b35720e44c7e1d6a0f318c652a59733e5499e7f8f633a64e284769cba` |
| `docs/research/meshecho_rac_design.md` | `1b0e5c9a844ba5062b2ef81bd7e33696b142038f8270e29d2d5729cae32e43fd` |
- [pending] Revise ICC manuscript, PDF, and version only after new evidence
  supports an honest core-algorithm claim; no EDAS or GitHub action yet.
- [failed; stopped] The exact 7001--7020 RAC development matrix completed.
  ACK gain passed against both controls, but the full-network TX-airtime
  upper CI exceeded +10% against both; `rac_joint_primary_gate=false`.
  Exposure was sufficient (4181 events over all 20 seeds). Do not open
  4001--4040 or tune RAC on these seeds. See
  `docs/research/meshecho_rac_dev_results.md`.
- [in_progress] Read-only failure forensics and a structurally distinct,
  separately named mechanism assessment. No paper/version release is
  justified by RAC's failed joint gate.
- [complete] Forensics traced RAC cost to missing source-hop cancellation:
  3647/3708 repairs target the ACK-terminating source, and no source-next
  candidate canceled. A successor cannot rely on global flow/action state
  at candidate nodes. An explicit, charged source ACK-closure beacon is a
  plausible but untested structural hypothesis; no claim or fresh run yet.

RAC error log: one combined code/design patch missed the exact design-file
context and applied no changes; the corrected patch matched the actual lines.

### 2026-10-03 Core-Rewrite Continuation: Source ACK Closure

- [complete] Recovered the active goal from `task_plan.md`, `findings.md`,
  and `progress.md`; `session-catchup.py` reported no unsynced context.
  The preceding answer was a read-only clarification, not a completed
  algorithm, simulation, or manuscript revision.
- [complete] Independent device-locality audit confirmed that RAC candidate
  and intermediate-node decisions consult simulator-global flow metrics and
  source-only action maps. This invalidates any firmware-ready interpretation
  of the RAC prototype. Its 3647/3708 source-next repairs cannot be canceled
  by the current continuation-only rule.
- [in_progress] Assess a *new, separately named* source-closure-assisted
  ACK-repair mechanism. The minimal candidate is a single charged one-hop
  ACK_DONE sent only after a source accepts the ACK; a candidate cancels only
  after locally decoding the matching DONE. Preserve the normal ACK-forward
  overhearing cancellation for intermediate hops. This is a hypothesis, not
  a proven gain or an ICC novelty claim.
- [complete] Recorded the falsifiable `MeshEcho-CLAR` pre-implementation
  contract in `docs/research/meshecho_clar_design.md`. Its four arms include
  same-beacon/no-cancel, on-path repeat, and plain single ACK. Prior art
  already rules out calling the ACK_DONE beacon itself novel.
- [complete] Froze packet fields, device-local state/deadlines, causal event
  rules, exact same-beacon/no-cancel ablation, on-path repeat and single-ACK
  controls, fresh development seeds, airtime gate, and prior-art boundary
  *before* new implementation or population results. Do not retune RAC on
  7001--7020 or open the 4001--4040 holdout.
- [in_progress] Implement one red/green end-to-end test at a time, run full
  regression, one non-evaluable smoke, then exactly one frozen development
  matrix. Only a mechanism that passes predeclared safety and joint benefit
  gates may enter an untouched holdout and the ICC manuscript rewrite.

Continuation error log: a second parallel read-only audit could not start
because the agent thread limit was reached. The completed local-state audit
was asked to exit; timing feasibility remains to be checked locally or after
a slot becomes available. A subsequent retry still hit the same thread limit;
do not retry without a changed agent-status indication.

CLAR test log: a first forwarded-ACK history cap test passed unexpectedly
because the proposed high-rate packet schedule yielded only 20 valid
forwards under real half-duplex timing. This did not exercise the 32-entry
bound. Widen packet spacing and assert exposure before treating the result
as a capacity check.
The first seen-ACK cap patch matched an earlier identical-looking block in
the frozen RAC class. The CLAR test stayed red. The unintended hunk was
removed from RAC, placed in CLAR with class-specific context, and focused
CLAR+RAC tests passed; the old RAC semantics were restored.
The first full-suite run overlapped runner TDD and found one intended red
holdout-manifest tamper test (384 passed, one skipped). The runner owner has
implemented recomputation from run rows and reports it green; rerun the full
suite only after runner integration finishes. Python compile and
`git diff --check` both passed.

Queue-boundary test log: the first targeted pytest invocation used the wrong
test class name (`TestMeshEchoCLAR` instead of `MeshEchoCLARTest`) and
collected no test. The corrected targeted invocation failed as intended:
the candidate was locally eligible, ten real queued ACK_DONE frames kept its
radio busy beyond local expiry, yet one `clar_repair_tx` was recorded. Root
cause: CLAR timer checks expiry before `transmit_later`, while
`begin_transmission` computes a later actual start without a request-level
validity gate.
The first repeat-boundary patch matched the structurally similar frozen RAC
method rather than CLAR, causing three RAC `NameError` failures while the
new CLAR repeat test remained red. Corrected with class-specific method
signature context; verify both focused suites before population simulation.
Two combined checkpoint patches then missed context (first a non-existent
design footer, then out-of-order hunks in this plan file); neither applied
changes. Separate, ordered file patches resolved the record update.

### 2026-10-03 CLAR queue-boundary continuation

- [complete] Recovered the active core-rewrite goal and inspected current
  worktree, CLAR contract, simulator scheduling, and recovery records. The
  preceding answer was a clarification, not completion of the goal.
- [complete] Runner owner delivered four-arm CLAR runner integration;
  `tests/test_sr_experiment.py` reported 134 passed. Full regression after
  that handoff is still pending.
- [in_progress] Test the real TX queue boundary: the CLAR candidate timer
  currently calls `transmit_later` before its local FLOOD evidence expires,
  but `begin_transmission` can reserve an actual start after that expiry.
  First reproduce with a public-behavior queue scenario; then fix at the
  actual-start gate without changing other protocols' semantics.
- [complete] Real queued repair and repeat tests failed before fixes and pass
  after a `PendingSend` actual-start gate. A malformed TTL-0 ACK continuation
  test failed before independent cancellation validation and passes after it.
  CLAR+RAC focused suites: 43 passed.
- [complete] Complete integrated regression: 399 passed, one skipped.
  `py_compile` and `git diff --check` pass after the boundary fixes.
- [in_progress] Independent read-only runner audit, final frozen SHA-256
  recording, and seed-8000 smoke artifact validation before any development
  run. The old ICC paper/PDF remains unchanged.
- [in_progress] Fix a runner CLAR window validator bug before freeze: raw
  future-start action events can exceed 630 s while windowed TX totals
  rightly exclude them. A runner-owned agent is writing a deterministic
  queued-future ACK_DONE test and aligning validation/counts; do not open
  development seeds until it passes full regression.
- [complete] Runner window boundary fixed with both a real queued-future
  ACK_DONE test and a hashed development-artifact validation test. Raw
  events remain in the log; windowed counts use actual TX starts <=630 s.
  Runner suite: 136 passed; complete suite: 401 passed, one skipped.
- [in_progress] Freeze final four CLAR source/design/runner hashes and run
  only seed-8000 non-evaluable smoke. Check all five artifacts, per-arm
  case/trace hashes, and action/flow accounting before opening development.

CLAR pre-smoke frozen inputs (SHA-256, 2026-10-04):

| Input | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `ee5749b401284b7a37647e50f0aadb7460716b28c6667ecd3bdd4aa76a5bc8a1` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `aafe1fb4c1ebdf3f5f8181a01dc5ea476b544283394659933b6c3929f6b68a88` |
| `docs/research/meshecho_clar_design.md` | `e2b56b94ba18d8b72a45171b66910345ce2ee4430031ddcd615d56b292a5078c` |

The full suite has 401 passes and one skip; compile and `git diff --check`
pass. Do not edit these four inputs during smoke/development. Plan/findings/
progress Markdown are outside the hashed experiment inputs.

Seed-8000 CLAR smoke (custom, non-evaluable) completed with four runs and
42 scheduled unicast flows per arm. All four arms share trace SHA-256
`4183a5048ce476dfdda906264a1436c05857d77beb8998bfa231d63c231ebd16`
and case SHA-256
`b3cfb113aded1b1487cf2a5426225cb1188143384a6fe90b770b855e5273b491`.
Manifest source hashes match the frozen table; all four data artifact hashes
match the independent `shasum` calculation. CLAR recorded 164 eligible
candidate events, 143 source-DONE cancellations, and 13 physical repair
starts; all four strategy arms executed. Single-seed paired intervals are
degenerate and *must not* be interpreted as gain evidence. Smoke output:
`results/meshecho_clar_smoke_seed8000_20261004.*`.

| Smoke artifact | SHA-256 |
| --- | --- |
| runs CSV | `40d13f7115607747e73c70afe6d7db6e7838afd097338194d712682765b18c30` |
| paired CSV | `8d1f10613e3b6ce21df2e16725feac243c06e750099f60b22938ee58bfdf7d79` |
| flows JSONL | `fd83f9bf1d2375a2959c9ac0c7f6b382552f1c65aec1cebe8bc8252870ff1a0d` |
| actions JSONL | `7d437cb331803b2bdb2a4bcb44f2f220587461bf43a9db4d46eea67517a13f0d` |
| manifest JSON | `df035bd81ba7f61dcabad4945f8e7e966bfff74920673ee2e000b2b256dda337` |

- [complete] Seed-8000 smoke and artifact integrity gate.
- [in_progress] Run exactly one frozen `clar-development` 8001--8020 matrix
  with all four arms, same recurring-fading case and 30-s deadline. Do not
  edit the four frozen inputs while it runs. Afterward independently verify
  source/artifact hashes, matched traces/configurations, and joint gates.
- [failed; stopped] The exact frozen 8001--8020 CLAR development matrix
  completed (80 runs, 797 scheduled unicasts per arm). CLAR versus same-
  trigger on-path repeat: paired ACK-PDR difference -0.0161 with 95% CI
  [-0.0547,+0.0226] and relative full-network TX airtime +7.7% with 95%
  CI [-5.5%,+21.0%]; both primary gate requirements fail. Against plain
  F/R single ACK, gain +0.1191 [0.0665,0.1718] and airtime -14.3%
  [-24.9%,-3.7%] pass, but the joint gate remains false. Exposure passes
  (4091 eligible events in all 20 seeds); it cannot override the failed
  repeat comparison. Do not open 4001--4040 or promote this mechanism to
  ICC manuscript/version/GitHub. Frozen CLAR inputs remain unchanged.
- [complete] Independent manifest/source/artifact SHA-256 verification and
  20-seed/80-row trace/config/flow pairing check. Development artifacts:
  `results/meshecho_clar_research_recurring_fading_dev_20261004.*`.
- [in_progress] Conduct read-only flow/action forensics and prior-art-aware
  structural replacement assessment. A new hypothesis needs a distinct
  contract, fresh seeds, public-behavior tests, and its own locked controls;
  the failed CLAR cohort is exploratory history, not an independent test of
  a successor. The ICC LaTeX/PDF still contain the old score-policy paper.
- [in_progress] Repair a post-run validator-only mismatch found by the
  forensic audit: the frozen repeat arm legitimately emits 84
  `source-done-repeat` cancellations, but the CLAR manifest validator
  rejects that reason. Preserve frozen 8001--8020 artifact/source hashes;
  add a failing synthetic-manifest test and fix the allowlist, then validate
  against the manifest's original expected hashes. Do not rerun the cohort
  or relabel it as fresh validation.
- [complete] Validator reason allowlist corrected by red/green synthetic
  manifest test. Current runner SHA-256 is
  `e174cf2eec896c63a2d91ffcae41b2d45168578e62c845b2a4f2e7b2b51d3b57`;
  the frozen run provenance remains the original `aafe1f...` hash. The
  untouched development manifest, validated against its own frozen source
  map, now reaches exactly `CLAR development joint primary gate did not
  pass`. Complete regression: 402 passed, one skipped; `git diff --check`
  passes. No same-seed rerun.
- [complete] Wrote `docs/research/meshecho_clar_dev_results.md` with paired
  outcomes, event/flow failure diagnosis, provenance, limitations, and stop
  decision. The next algorithm should target same-flow R DATA non-delivery
  (196 of CLAR's 199 undelivered missed flows), not more F ACK-only repair.

| Frozen CLAR development artifact | SHA-256 |
| --- | --- |
| runs CSV | `3ae1f6b8b8b100a5e85fe00e082ea50d176473dc3599001073f159e418e5fd76` |
| paired CSV | `0f7bc834fb11e8e558a857a26ffa52955382bcc24063ded324eb77737bb41e1a` |
| flows JSONL | `a60bb6e4f7aa19b884bf3e4c3411a14ec8dfe41b4dc6ee572bc96c1ddd834316` |
| actions JSONL | `2927886cb27359dc03130b6597afff03b81a0a07ea985025b7182e3383fae8c0` |
| manifest JSON | `fdb77e3aacd3c787bd6c60ef3789220a9a0422f6129a793a48c09312559ae960` |
- [pending] Run complete regression, compile and diff checks, freeze
  source/design/runner hashes, seed-8000 non-evaluable smoke and artifact
  integrity checks, then one frozen 8001--8020 development matrix.
- [pending] Open holdout and rewrite/compile/inspect the ICC paper only if
  the prespecified CLAR safety, exposure, reliability, and airtime gates
  survive. No CLAR population result or paper claim exists yet.

## 2026-10-04 Resumed Core-Algorithm Decision

- [complete] Recovered this goal from the existing plan/findings/progress
  files and audited the current worktree. The frozen CLAR development gate
  failed; the old ICC LaTeX/PDF remains a route-score manuscript. CLAR must
  not be presented as a positive result or tuned on 8001--8020.
- [decision] Rewrite the core same-flow reliability decision that acts on
  routed DATA loss. Preserve tested simulator, packet/airtime accounting,
  F/R plumbing, and experiment infrastructure; this is not a ground-up PHY
  or simulator rewrite. Unconditional retry/flood is a comparator, not an
  originality claim.
- [in_progress] Freeze a distinct source-local, deadline- and cost-bounded
  R-DATA recovery contract with public-packet safety tests and equal-trigger
  no-recovery, R-repeat, and F-fallback controls. Use fresh development
  seeds; keep 4001--4040 sealed. Only verified favorable evidence can
  authorize the subsequent ICC manuscript rewrite and PDF.
- [error] A multi-file progress-note patch failed because its findings.md
  context did not match; no files were changed by that attempt. Reapplied
  with exact end-of-file contexts.
- [complete] Added `docs/research/meshecho_dhr_design.md` for DHR and its
  matched no-recovery/R-repeat/F-fallback arms, fresh seeds, and prospective
  evidence gate. Independent review found four safety/accounting gaps;
  corrected the contract before population data.
- [in_progress] TDD implementation. The first real-packet R-DATA-loss test
  failed because DHR was unregistered, then passed after the first narrow
  protocol slice. ACK marker propagation, F branch/route commit, deadline
  admission, and runner validation remain incomplete.
- [error] An initial apply_patch call tried two operations on the same file
  and was rejected without edits. Reapplied as one update with two hunks.

### DHR Implementation Checkpoint

- [complete] Contract adversarial review and amendment: ACK attempt echo,
  current-route freshness, worst-path F timing, immediate-start reservation,
  per-source active-flow cap, and exact paired-airtime estimator are stated
  before DHR development runs.
- [complete] Six public-packet DHR tests are green after test-first slices:
  lost initial R DATA recovers once; recovery ACK echoes a charged marker;
  stale route selects F; alternate F ACK commits its realized path; busy
  source does not reserve post-deadline recovery; ninth overlapping R flow
  is refused; four controls share guard/admission and select declared actions.
- [in_progress] Add deadline-slow-PHY, ACK-only-loss/duplicate-delivery,
  late/invalid ACK and route-generation tests, plus diagnostic destination
  receptions. Runner integration and full regression are still pending.
- [pending] Freeze DHR source/runner/design hashes and run only seed-9000
  non-evaluable smoke after runner and protocol invariants are verified.

### DHR Resume Check - 2026-10-04

- [complete] Re-read the three checkpoint files, DHR contract, CLAR failure
  report, prior-art brief, and current DHR implementation. The new rule
  changes same-flow recovery after an initial R DATA miss; it does not
  replace MeshEcho-SR's first-send route policy or claim a new PHY.
- [complete] Added tests for lost ACK duplicate delivery, stale original ACK
  after alternate-path F commit, and SF12 deadline refusal. DHR targeted
  suite: 9 passed. Complete integrated regression: 430 passed, one skipped.
  Python compilation and `git diff --check` pass.
- [in_progress] Runner owner has integrated the four-arm DHR suite and
  manifest checks in `tools/run_sr_experiment.py` and its tests, with final
  runner verification pending. No DHR smoke, development, or holdout seed
  has been run.
- [pending] Freeze source/design/scenario/runner hashes, run only seed-9000
  mechanical smoke, validate its artifacts, then decide whether the frozen
  9001--9020 development matrix is ready. The ICC manuscript/PDF, VERSION,
  GitHub, and submission stay unchanged until independently verified gains.

DHR pre-smoke frozen inputs (SHA-256, 2026-10-04):

| Input | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `94f4c428afd022b86c8d3c51a6da1a32fe113e7b17e0615540915964be5a9299` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `c9f81a0d33effb362fb489d884bb816e6a7052fa21da4084c7e749fd853faf15` |
| `docs/research/meshecho_dhr_design.md` | `862e7f307db6ac992235e90c34bfb7e3793e69d3168ee91d133d1db636a26d59` |

Do not edit these four inputs during smoke or development. The final runner
suite passed 157 tests; DHR packet tests passed 9 and the complete suite
passed 430 with one skip. No DHR result artifact existed at freeze time.

- [complete] The exact four-arm seed-9000 custom smoke generated 44 scheduled
  flows per arm, a common application trace SHA-256
  `97f69e26e481bfda71a914a882215ac357c4735eba9a0d3c88a0f56fff70cd2e`,
  and case SHA-256
  `b3cfb113aded1b1487cf2a5426225cb1188143384a6fe90b770b855e5273b491`.
  The frozen four source hashes and all four artifact hashes match independent
  `shasum` output. DHR logged 10 admitted guards, eight R and two F actual
  rescues. The single-seed paired figures are not effect estimates.
- [in_progress] Run one frozen `dhr-development` 9001--9020 matrix with all
  four arms, then independently verify hashes, complete pairing, marker/action
  accounting, and the prospective joint gate. Do not edit frozen inputs or
  open holdout during this run.

| Seed-9000 smoke artifact | SHA-256 |
| --- | --- |
| runs CSV | `45c1b5b7f4097041d872140001d1d2a9021d3718e555930b69b61f57e9ebab49` |
| paired CSV | `8be57a70d510beb2dd2354d130d1b87dcde167d0a74f9cfd0948022a64b62e12` |
| flows JSONL | `e6a30d33b2c8904854151c745a6283943ef3c1b5f8b31a477e287333a2a78adf` |
| actions JSONL | `c1e67a307f924f0f707b54f38ff431bf694266ce1926322481047f89f4699dc1` |

- [failed; stopped] One frozen `dhr-development` 9001--9020 matrix finished
  with 80 runs and 803 scheduled unicasts per arm. DHR minus fixed R ACK-PDR
  is +0.0227 [-0.0179,+0.0632] with paired relative airtime +16.4%
  [7.8%,25.0%]; DHR minus fixed F is +0.0005 [-0.0515,+0.0524] ACK-PDR
  with airtime -13.9% [-21.4%,-6.4%]. Both primary comparisons fail their
  prospective joint requirements, though exposure passes (175 admitted
  guards, 109 R and 66 F rescues). Do not open 10001--10040, retune the
  120-s threshold on these seeds, or promote DHR to the ICC paper.
- [complete] Independent source/artifact SHA-256 checks and the manifest
  validator's full provenance/flow/action/paired checks reach only the
  expected failed-joint-gate verdict. The standalone result report is
  `docs/research/meshecho_dhr_dev_results.md`.

| Frozen DHR development artifact | SHA-256 |
| --- | --- |
| runs CSV | `6b45b8ac5f39c6672dfdd243dbb8bfa4b4158f7b7b3cfcf154946be0a4c396b2` |
| paired CSV | `fad5c385dcf04800e9b14281cd6de01836ba6318857fa6e43ff833bbe912f147` |
| flows JSONL | `c0a3fd1dda32de8bbf26f37b96452ba2549cbeab953016699e5e9f4bed9a54cb` |
| actions JSONL | `70614ee47f20fe28faa5704b7a081858e10ece8b80243ddd7c8e45e6274b212f` |

## 2026-10-04 Goal Continuation: New Core After DHR Failure

- [complete] Classified the preceding goal turn as progress: DHR's frozen
  development evidence changed the algorithm decision and its failure was
  recorded; no holdout or manuscript promotion occurred.
- [in_progress] Diagnose the shared bottleneck across frozen SR, DPA, CLAR,
  and DHR results using their actual artifacts and close prior art. Separate
  application DATA delivery from reverse-ACK delivery and avoid inferring a
  per-flow counterfactual from closed-loop arm totals.
- [complete] Record prior-art and observability questions before writing a
  successor: `docs/research/meshecho_core_feasibility_gate.md`. The bounded
  diagnostic tool is delegated in new files and will use exploratory seeds
  11001--11003 only; it cannot validate a future mechanism.
- [pending] Write a distinct core-algorithm contract with device-observable
  inputs, an explicit loss/airtime/deadline objective, packet/state budget,
  strongest same-trigger controls, and a new untouched seed split.
- [pending] Implement behavior test-first, validate full packet accounting,
  freeze inputs, run smoke and one development cohort. Only a passing frozen
  mechanism may open holdout and trigger the ICC five-page LaTeX rewrite,
  PDF inspection, and citation/integrity checks.
- [error] An exploratory `rg` command used a zsh glob with no matching
  `meshecho_sr_*` file and failed before reading. Use literal directory
  searches and `rg --files` filtering instead; no file was changed.
- [error] Terminal `curl` to the initially guessed ICC 2027 CFP path failed
  DNS resolution. The in-app browser reached the official site; the guessed
  `/authors/call-papers` path was a 404, then `/authors` and
  `/authors/call-symposium-papers` supplied the live dates. No external
  submission state changed.

### 2026-10-04 Observability Diagnostic and Decision Boundary

- [complete] The isolated SR observability tool and 12 focused tests are
  finished. Exploratory seeds 11001--11003 reproduce the runner's application
  traces, scheduled flows, deadline ACKs, and deliveries; source SHA-256 values
  are recorded in `/tmp/sr_observability_11001_11003_guard_20261004.json`.
- [complete] Across 134 initial R physical DATA hops, 102 intended next hops
  decoded and 32 did not. Passive progress detection gave five false-failure
  indications among 102 successful hops and no false-success indication among
  32 failed hops. All 32 failures have a single-relay detour in an oracle
  guard-time screen, which is an optimistic opportunity bound, not a realized
  or device-observable rescue rate.
- [decision] A minor score/threshold adjustment is not justified by the
  frozen failed cohorts. The research path is to redesign the core routing/
  recovery/feedback decision while reusing verified simulator, PHY, packet,
  accounting, and matched-run infrastructure. A new device-local contract and
  fresh controlled evidence are still pending; do not claim algorithm gain or
  rewrite the ICC manuscript from this diagnostic alone.
- [error] A first `jq` inspection mixed array length with object-key filters
  and failed without changing data; a corrected schema query succeeded.

### 2026-10-04 Core Redesign Continuation

- [complete] Classified the previous goal turn as progress: the completed
  reproducible observability diagnostic and recorded decision boundary change
  the algorithm search; the full goal remains open.
- [in_progress] Select one distinct, device-local core decision rule from
  the frozen LPR/RAC/CLAR/DHR failures and exploratory hop evidence. Keep
  first-send routing, forward DATA recovery, and reverse ACK accounting
  causally separate in the mechanism contract and ablations.
- [pending] Freeze mechanism, controls, fresh seed split, predeclared joint
  outcome/cost gate, and implementation invariants before population runs.
- [pending] Test-first implementation, mechanical smoke, one development
  cohort, independent integrity checks, untouched holdout if warranted,
  then major ICC manuscript/PDF revision from verified evidence.
- [decision] Reject a pure downstream relay-checkpoint/suffix-replay core:
  27/32 exploratory first-R failed hops are source-adjacent, before that
  checkpoint could hold the payload. Next run an isolated first-hop witness
  feasibility screen: distinguish actual off-path decoders from candidates
  that the intended first relay could nominate using its own prior packet
  observations. Keep all such screens exploratory, not performance tests.
- [error] A second parallel prior-art follow-up hit the agent-thread limit;
  continue local source verification and await the already running first-hop
  diagnostic instead of retrying the same delegation.
- [error] One broad OpenAlex ACK-query search returned no parseable
  `.results` despite a later 200 response to a header-only check. Treat
  targeted ACK-query novelty as unverified; do not infer literature absence.
- [decision] RFC 4728 already covers passive ACK plus separate ACK request.
  Do not freeze a generic source-progress/query mechanism as a new core.
  Require flow-level exposure and an end-to-end confirmation/suffix-action
  distinction, with a DSR-like comparator, before coding or paper claims.
- [in_progress] First-hop witness exploratory tool reproduces SR traces and
  initially finds only eight actual nominated decoders among 22 failed
  first hops; three source-progress/unACKed multihop flows are all
  undelivered. The nomination evidence was initially unbounded in age;
  require fixed descriptive TTL strata before using this screen. No
  replacement algorithm is authorized by these preliminary counts.
- [error] A separate flood-ACK path analysis agent could not be spawned
  because the thread limit remained reached. Keep that as a future bounded
  diagnostic; do not repeatedly retry agent creation.
- [candidate, not frozen] Analyze whether a destination that decoded
  multiple F DATA paths before a short ACK window can choose a better
  reverse ACK path using only local inbound observations. Measure path
  multiplicity and delay on fresh exploratory seeds before implementation;
  compare with first-arrival and matched PRR-product/shortest-path controls.

### 2026-10-04 Continuation: Core Algorithm, Not Threshold Tuning

- [decision] The previous clarification turn did not change files or produce
  a new mechanism; it confirmed that the desired ICC contribution requires a
  new routing/recovery/feedback decision rule, while the tested simulator and
  experiment harness should remain as infrastructure. Treat that turn as no
  progress toward the still-open full goal.
- [complete] Final first-hop witness exploratory artifact is
  `/tmp/first_hop_witness_12001_12003_ttl_direct_20261004.json`. It contains
  86 initial R first hops, 22 failed intended receptions, and only 0/5/8
  failed hops with an actually decoding locally nominated candidate under
  30/120/300-s prior-observation windows. The three source-observed-forward,
  unACKed multihop flows were all undelivered; direct unACKed R flows split
  6 delivered versus 8 undelivered. These are diagnostic strata, not repair
  outcomes or a candidate algorithm.
- [complete] Run a read-only, test-first F reverse-ACK path diversity
  diagnostic on new exploratory seeds. Count distinct paths physically
  decoded at the destination within predeclared short windows and separate
  local observations from offline path-quality or hypothetical ACK success.
  Final artifact: `/tmp/flood_ack_paths_15001_15003_20261004_hops_budget_v3.json`.
  Among 37 delivered-unACKed flows, 32 were FLOOD-first and 27 of those
  had a distinct first reverse ACK hop within 1 s. Raw offline remaining
  deadline across 43 candidate hops has min 12.09 s, median 13.80 s.
- [complete] The second isolated reverse-ACK hop trace uses independent
  exploratory seeds to locate actual ACK losses. Its final artifact and
  counts are listed below; it is not a counterfactual success study.
- [complete] The fixed-F ACK-hop trace on new seeds 14001--14003 is in
  `results/meshecho_flood_ack_hops_seed14001_14003_20261004.json`. The
  observer reproduces baseline traces and per-flow outcomes. All 35
  delivered-unACKed flows emitted a destination ACK; all 37 attempts had
  an observed physical reverse-hop decode failure (19 at hop 1 from the
  destination, 18 at hop 2), with no deadline/censoring explanation. Five
  focused tests pass independently. These are actual failure locations,
  not estimated success of an untransmitted alternate ACK.
- [in_progress] Exposure supports testing a bounded alternate-ACK candidate,
  but close prior art rules out a generic multipath-ACK novelty claim. The
  draft in `docs/research/meshecho_bounded_reverse_ack_candidate.md` is not
  yet a frozen full core. Finalize exact device-local state, same-trigger
  same-path control, development/holdout seeds, and joint outcome/cost gate
  before test-first implementation. The first SR failure branch still needs
  a complete source-side contract.
- [in_progress] Drafted `docs/research/meshecho_bounded_reverse_ack_candidate.md`
  as a falsifiable ACK-side candidate with one extra ACK, distinct physical
  reverse first hop, local 1-s trigger window, and same-trigger same-path
  repeat control. It is **not** yet a complete source/feedback core contract
  or a frozen development specification; first confirm remaining deadline
  budget from the updated path diagnostic.
- [decision] Source `Packet.created_at` is simulator-only and cannot be a
  destination-side deadline input. Removed that invalid gate from the
  draft candidate; the source's original deadline still governs accepted
  ACKs and the destination's optional extra TX must be fully charged.
- [complete] Froze the ACK-branch prototype contract before implementation:
  local 1-s window, eight active FLOOD receipt epochs per destination,
  one extra ACK on the first decoded distinct reverse first hop, matching
  same-trigger same-path control, full packet accounting, and prospective
  paired development gates. This is only an ACK-side vertical slice;
  a source-side algorithm rewrite is still required for the full goal.
- [decision] An independent code audit found the initial FLOOD-first-only
  rule would require destination-local R-first tombstones; reading
  `metrics.flows[].delivered_at` would be a forbidden oracle. Before any
  protocol edit or population run, revised the contract to start its
  1-s local epoch at the first actual FLOOD receipt, including F recovery
  after earlier routed DATA. Results will stratify R-first/F-first offline.
  The initial design hash below is historical; record a new freeze hash.
- [in_progress] Test-first implementation delegated in the simulator,
  new public-behavior tests, and an independent BAR runner split. Smoke
  seed 16000 may be used; development 16001--16020 and holdout
  17001--17040 remain unopened until implementation and provenance freeze.
- [decision] Refroze the ACK-branch contract after independent review:
  the reference ACK path is the first ACK of the current FLOOD epoch,
  including when a routed-DATA ACK preceded F rescue; validate the claimed
  last hop against actual `rx.sender` and reject a destination already in
  the inbound path. The eight-entry cap applies only to new ACK-window
  state, not the inherited unbounded `seen_floods` set. Freeze hash below
  replaces the historical draft hash before any implementation or seeds.

| Frozen ACK-branch input before code | SHA-256 |
| --- | --- |
| design | `c08662547e8e5d6bfd7fd7d43e8b643b1e123faddc5b5b427d8e09f0beca74dd` |
| simulator | `94f4c428afd022b86c8d3c51a6da1a32fe113e7b17ee0615540915964be5a9299` |
| SR runner | `c9f81a0d33effb362fb489d884bb816e6a7052fa21da4084c7e749fd853faf15` |
| probe helpers | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |

Refrozen pre-implementation ACK-branch design SHA-256:
`0fd1dc3f267e4d38bba604371c9c38c84c97ce5b4d1a90cc2a8273f09b24e332`.
The prior `c086...` hash is historical and must not identify the BAR run.
- [decision] Before any BAR seed, preregistered holdout replication:
  the same three-arm paired ACK/airtime/destination thresholds on 40
  holdout seeds, plus at least 40 actual alternate extra ACK TXs in at
  least 20 holdout seeds. The second design freeze SHA-256 is
  `285667e4e1b531e7bc5d67bfcbb2f5257a553020e667d226338c93027a3ddb9b`;
  both earlier design hashes are historical, not BAR run provenance.
- [complete] BAR protocol/runner implementation and mechanical-source
  freeze. Independent full unittest discovery: 505 passed, 1 skipped;
  `git diff --check` passed. The six exact input hashes below are frozen
  before smoke seed 16000. Do not edit them during smoke/development;
  any behavior-affecting edit requires a new named cohort.
- [complete] Run seed-16000 BAR three-arm smoke, verify all artifact hashes,
  trace/case pairing, flow/action consistency, and exposure counts.
- [complete] Run exactly one frozen 16001--16020 development matrix after
  valid smoke; its joint gate failed, so do not open 17001--17040.
- [complete] Seed-16000 BAR mechanical smoke. Three arms share identical
  case and scheduled-trace hashes, each has 43 scheduled/registered flows,
  and all four artifact hashes match the manifest. Flow-level ACK/delivery
  totals match the runs: alternate 38/42, fixed-F 29/43, same-path 34/42.
  Actual extra ACK action/flow counts match: alternate 8, same-path 11.
  These are one-seed mechanics only; no paired inference or gate claim.
- [complete] Ran the single frozen BAR development matrix on 16001--16020
  in about 95 s. Artifact hashes, source hashes, 60-row pairing, 778
  scheduled flows/arm, and action counts were independently checked.
  Alternate versus fixed F passes, but alternate versus same-path repeat
  fails: ACK-PDR +0.0021 [-0.0292,+0.0334], airtime +2.3%
  [-4.7%,+9.4%]. The source validator reaches the expected failed joint
  gate after flow reconciliation. Exposure passes (248 actual extra ACKs
  in 20 seeds). Record in `docs/research/meshecho_bar_dev_results.md`.
- [decision] Stop BAR's positive alternate-path claim and keep holdout
  17001--17040 sealed. No BAR result is promoted to ICC paper, VERSION,
  GitHub, or EDAS. The active full goal now needs a distinct source/
  feedback core; reusing BAR's inspected development set would be tuning.
- [error] A quick airtime aggregation used CSV field 20, which is the
  queued-future count, not field 19 airtime. Header inspection corrected
  the index; the validated aggregate is 1166.361/1215.636/1149.639 s.
- [error] A one-line structured CSV audit had an f-string backslash syntax
  error. A different dictionary-comprehension command succeeded; it
  independently matched pooled flows, ACKs, deliveries, airtime, and
  extra-ACK event counts.

| Frozen BAR input before seed 16000 | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `41626c2d559088f00f2758edc782b31649359bb3e26afdc199d7be6803f70f45` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `ac12adf568714e766cff2efd67b1ba2ab6d1fc9ca4530cdd5f195e3d7f3c21b7` |
| `docs/research/meshecho_bounded_reverse_ack_candidate.md` | `285667e4e1b531e7bc5d67bfcbb2f5257a553020e667d226338c93027a3ddb9b` |
| `tests/test_meshecho_bar.py` | `975219ab008c0526382ccf0aeaecda9a19d1034502a1926bb53d6677b099a188` |
| `tests/test_sr_experiment.py` | `087657fff5faaf14b7c1036c1120359ebccd79a449262db89aa3f18a10a8a966` |
- [error] An intermediate ACK-hop JSON was inspected while its diagnostic
  source was still being finalized, so its recorded script SHA briefly
  differed from the live file. The agent regenerated the final artifact;
  independent `shasum` now matches every source entry. Do not use the
  intermediate JSON in claims.
- [error] Session-catchup's first invocation used `python`, which is absent
  here; rerunning the same script with `python3` succeeded with no unsynced
  context reported. Do not retry the missing `python` executable.
- [error] A broad `rg --files /tmp` scan encountered permission-denied
  RustDesk entries. Narrow searches of the known project `results/` and
  top-level `/tmp` found no DHR per-flow JSONL; use new exploratory runs
  rather than relying on inaccessible or absent old traces.
- [error] Two attempts to allocate an additional independent source-policy
  design agent failed at the agent-thread limit. The BAR protocol and
  runner owners remain active; continue source-side review locally and
  do not retry the same delegation while this limit remains.

## 2026-10-04 Continuation: Prospective Forward-Recovery Core

- [decision] The preceding goal turn was read-only clarification and did not
  advance the active algorithm/paper objective. Revalidated the dirty worktree,
  current ICC manuscript, BAR result, and source-side implementation before
  taking the next research action. The current five-page manuscript is still
  the old calibrated route-score study, not an SR/BAR core-rewrite paper.
- [complete] Run a behavior-preserving fixed-F forward-recovery exposure
  diagnostic on fresh exploratory seeds 18001--18003. Distinguish initial R
  DATA delivery, actual F rescue delivery/path length, source-known old-route
  length, deadline slack, and whole-network forwarding cost. This is a
  feasibility screen, not a candidate performance estimate.
- [in_progress] Verify prior art for hop/deadline-bounded same-flow flooding,
  including fixed-TTL, expanding-ring, and local-repair precedents. Do not
  freeze a new core until the device-local decision and a specific novelty
  boundary survive this check.
- [pending] If the opportunity is material and the mechanism is distinct,
  freeze a new source/feedback contract, same-trigger fixed TTL/F/R controls,
  joint ACK/destination/airtime gate, and wholly fresh development/holdout
  seeds before behavior code or population runs. Otherwise reject this
  candidate and evaluate a different high-exposure core.
- [pending] Only after a successful prospective mechanism and untouched
  validation: replace the ICC title/abstract/method/figures/conclusion,
  compile and inspect the PDF, and verify citations and evidence hashes.
- [error] A third independent design-agent allocation hit the agent-thread
  limit. Two bounded tasks (forward exposure and prior art) are active; do
  not retry additional allocation while they run.
- [error] The first three-file checkpoint patch used an inexact findings.md
  context and applied to none of the files. Corrected with exact tail
  context; no prior user changes were touched.
- [guard] BAR holdout 17001--17040 stays sealed; the BAR development cohort
  is inspected algorithm-selection history, not confirmation for a successor.
- [decision] Focused prior-art check rejects bare `recovery TTL = confirmed
  route hops + constant` as the core contribution. AODV RFC 3561 already
  uses known hop count plus TTL increment for repair search, DSR RFC 4728
  salvages same-flow DATA, and Meshtastic documents a final-attempt managed
  DATA flood after an unheard next-hop relay. Path/cost diagnostics remain
  useful, but a successor must add and isolate a substantive device-local
  timing/deadline/airtime decision and beat matched fixed-radius/full-F/
  last-retry controls. Do not code a bare TTL variant as the paper method.
- [candidate, not frozen] Explore whether a relay with a queued same-flow
  FLOOD forward physically decodes the destination's normal reverse ACK
  before its TX start, so that ACK can serve as a local terminal-delivery
  certificate and cancel the queued DATA TX without a new STOP packet.
  An exact LoRa precedent was not verified in a bounded search; novelty is
  unproven. First run a behavior-preserving ACK-overhear exposure diagnostic
  on fresh exploratory seeds, counting only validated local packet fields,
  queued pending forwards, and actual physical decodes. If exposure is low,
  reject before protocol code. If material, freeze a cost-primary contract
  against the same ACK behavior without cancellation plus ordinary duplicate
  suppression, and inspect whether source ACK/delivery is harmed.
- [in_progress] Run that ACK-overhear exposure diagnostic separately on
  fresh exploratory seeds 22001--22003, with exact uninstrumented replay
  and source/artifact hashes. Count only `PendingSend` handles with both
  `committed=False` and `canceled=False` when a valid ACK is actually decoded;
  the simulator commits a TX request before its possible future physical
  start, so a committed handle is not cancelable through the present API.
- [provisional] The first new ACK-overhear exploratory seed reproduced its
  baseline and showed substantial physically decoded ACK / uncommitted-F
  overlap, but final counts and the two other seeds are pending. Require
  distinct unique pending handles and actual later TX airtime, stratified
  by initial F versus R-timeout recovery F; a routed-stage ACK may not
  cancel a later F-stage recovery because that F can still close the source.
- [guard] The repository's older `MeshEchoLPR.on_receive` already cancels
  queued `PATCH_RELAY` sends after overhearing successor DATA/ACK, subject
  to `not pending.committed`. A general ACK-triggered cancellation principle
  is therefore not new even within this project. Any successor must isolate
  terminal destination-ACK cancellation of ordinary FLOOD tails and then
  integrate it into a genuinely revised source/recovery policy; cancellation
  alone is not yet the full requested core rewrite.
- [decision] Final 18001--18003 fixed-F diagnostic disproves the simplistic
  `TTL = old route hops` rationale: 11/26 F-first deliveries used longer
  paths, with no observed timely <=old-hop F decode for those 11. Among
  F-first flows, 310 relay FLOOD transmissions/30.456 s TX ToA started
  after first destination delivery (362/35.528 s including two R-first
  delivered flows). These are offline tails, not realizable savings. The
  final JSON hash and seven focused tests were independently checked.

## 2026-10-04 Core-Rewrite Continuation

- [complete] Re-read the live worktree, current MeshEcho-SR source, ICC
  manuscript, failed development gates, and both passive recovery/ACK
  diagnostics. The preceding goal turn produced a read-only source/evidence
  audit that changed the next action: a new source-side decision mechanism is
  required; threshold tuning or a relay-only cancellation feature is not a
  full algorithm rewrite.
- [complete] The final ACK-overhear exposure report on 22001--22003 shows
  1,120 distinct strict pending-F handles reached by physically decoded,
  matching off-path destination ACKs; 591 later transmitted, accounting for
  57.915136 s of potential local TX airtime. This is passive opportunity,
  not a closed-loop saving, novelty result, or ICC claim. Artifact SHA-256:
  `3d5df0c10887fdbb9f611bd8337f060a364788024970a151361b242cb6b12a31`.
- [in_progress] Independently audit and correct the ACK-terminated FLOOD
  component contract. In parallel, derive a genuinely revised device-local
  source policy with matched simple controls. Only then perform test-first
  implementation and mechanical no-cancel parity smoke.
- [guard] The existing ICC manuscript/PDF and VERSION remain unchanged until
  a full-core candidate passes a prospective development gate and untouched
  holdout. BAR holdout 17001--17040 and the proposed new holdout
  24001--24040 remain unopened. Do not reuse inspected development cohorts
  for independent confirmation.
- [error] The first ACK-contract patch used an inexact multiline context at
  its source-metrics sentence and applied to none of the file. Re-read the
  exact paragraph and applied smaller hunks; no protocol behavior changed.
- [complete] Corrected the standalone ACK-terminated FLOOD component
  contract's path, marker, pending-handle, on-wire alias, and shadow-control
  requirements. Implemented a new `meshecho-afs` / `meshecho-afs-nocancel`
  fixed-F relay slice with an eight-record cap and local 30-s retirement.
  The behavior is not yet the requested source-core rewrite.
- [complete] Test-first red/green: the first public three-node test failed
  because `meshecho-afs` was unknown, then passed after implementation.
  Added fixed-F shadow parity and R-ACK/F-marker isolation tests; all three
  pass. Full `python3 -m pytest -q`: 520 passed, 1 skipped (37.22 s), and
  `git diff --check` passed. No population AFS run or holdout was opened.
- [in_progress] Freeze the integrated deadline-reserved source policy only
  after specifying the actual-TX-start decision hook and same-admission
  fixed-guard controls. A read-only independent proposal warns this may be
  classified as ordinary deadline-aware ARQ unless it beats that control.
- [decision] Rejected the proposed DRC full-core design before population:
  all 559 route-bearing initial actions in inspected fixed-F DHR development
  traces satisfy its reserve test, giving zero observed reserve-caused F-first
  exposures. Its 1.149--1.637 s variable checkpoint has the same historical
  ACK/no-ACK classification as a fixed 2.05-s early guard. This is a passive
  feasibility result, not a DRC outcome estimate. Removed the incomplete
  `MeshEchoDRC` tracer and its test (both written in this turn); kept the
  complete AFS relay component and its tests. No 280xx/290xx run occurred.
- [pending] Continue toward a genuinely differentiated source decision with
  device-observable high-exposure evidence; separately measure AFS's
  closed-loop cost/reliability effect against unchanged fixed-F before
  considering it as part of another core. No manuscript promotion yet.
- [complete] AFS safety TDD found and fixed two predicate errors. A marker-1
  FLOOD/ACK pair had incorrectly enrolled and canceled a pending forward;
  only initial F (`None`) and recovery F (`2`) now enroll. A matching ACK
  with different `Packet.protocol` metadata had incorrectly been rejected;
  the relay predicate no longer reads this non-wire field. Both tests were
  observed red before fixes and green after. Five focused tests pass; full
  pytest is 523 passed, 1 skipped (37.29 s).
- [in_progress] A separate new-file AFS runner/test is being built without
  opening seed 23000 or any population cohort. A separate read-only screen
  is checking whether source-local pre-send feedback predicts R failure.
  Freeze hashes and run only the mechanical 23000 smoke after runner review.
- [error] An extra independent AFS audit agent could not be allocated because
  the agent thread limit was reached; no retry was made. Local predicate
  review found and fixed the two issues above.
- [complete] Added a queue-boundary AFS test: an already committed relay
  FLOOD with future physical start is not cancelable by a later matching
  ACK. Six focused AFS tests pass. A separate source-signal report from
  already inspected DHR-none development actions found a strong descriptive
  one-hop failure association but no causal action benefit; do not promote
  a hop-based rule without a fresh matched test.
- [in_progress] The AFS experiment runner and synthetic tests have been
  drafted in new files. Independently review mechanical parity, witness
  reconciliation, gate fields, and manifest requirements before freezing
  and opening seed 23000; the runner owner reports seven focused tests and
  no reserved seed run.

## 2026-10-04 - Algorithm-Rewrite Clarification

- [decision] User challenged whether the algorithm itself must be rewritten.
  Answer: yes, the source-side send/recovery decision needs a genuinely new,
  device-observable rule if the ICC paper is to claim a new protocol. Reuse
  the simulator, radio/queue model, accounting, and matched baseline harness;
  AFS is a tested relay-side component, not a complete replacement core.
- [in_progress] Read-only independent audit of the AFS runner and algorithm
  boundary before any seed 23000 smoke or ICC manuscript change. The runner
  currently lacks saved local pending-handle evidence sufficient to
  recompute every strict-pending witness from the artifact alone.
- [guard] No AFS reserved seed, development/holdout run, manuscript update,
  VERSION bump, GitHub upload, or EDAS action is implied by this clarification.
- [error] Planning skill catch-up invoked with unavailable `python` once;
  `python3` succeeded with no unsynced context.
- [finding] Independent runner audit before smoke found three provenance
  gaps: decode records cannot reconstruct strict pending cancellation,
  deadline flags are not checked against timestamps, and recorded TX
  intervals are not checked against frozen PHY ToA. Repair and test these
  before freezing or opening seed 23000; no-cancel parity was confirmed to
  compare full normalized TX trace and matched actions/flows/metrics.
- [decision] Independent architecture audit confirms the rewrite boundary:
  preserve the Packet/Simulator/radio/accounting/baseline scaffold and old
  protocol as a comparator, replace the threshold-driven source F/R/D and
  recovery state machine only after a device-observable rule and matched
  simple controls are specified. DHR and BAR development failures preclude
  promoting those candidates; AFS remains a component under test.
- [decision] An independent read-only source-candidate screen found no
  currently defensible complete new source/recovery controller in the
  existing evidence. The target is initial R forward non-delivery, but ACK
  timeout at the source cannot identify forward versus reverse failure.
  Hop count is correlational; DRC, ACK query, first-hop witness bypass, DHR,
  and BAR each failed a feasibility or matched-control gate. Before coding
  another controller, specify and pass a diagnostic for fresh bounded local
  progress evidence (or explicitly pivot the paper to a narrower systems
  optimization). Do not claim a known winning algorithm or edit the ICC
  manuscript based on candidate intuition.
- [complete] AFS runner owner fixed the three preregistration/validation
  defects with red-green tests and added a synthetic passing development
  manifest test; 12 focused runner tests and 18 combined AFS tests passed.
  Root reran the full suite: 535 passed, 1 skipped (37.45 s).
- [in_progress] Separate independent read-only review of the repaired AFS
  runner is pending. No seed 23000 or cohort may run before it is resolved,
  whitespace/static checks pass, and source/design/runner/test hashes freeze.
- [finding] Independent review rejected the repaired runner for final
  qualification: saved ACK/pending snapshots are not tied to actual prior
  FLOOD reception/enrollment, and duplicate `(seed,arm,tx_id,receiver)` ACK
  decode rows can inflate the 100-cancel gate. The synthetic passing gate
  fixture demonstrated that fabricated witnesses can pass without an F
  receipt. It also found no real 3+ node recorder cancellation test.
- [in_progress] Add deterministic replay of every prerequisite seed/arm in
  `validate_manifest`, comparing complete results with only ephemeral Python
  handle IDs normalized; reject duplicate decode identities; add an actual
  multi-node recorder integration test. This doubles prerequisite simulation
  work but is simpler and stronger than new action-log lifecycle machinery.
  Seed 23000 remains unopened until this work and tests pass.
- [decision] Bounded in-band STATUS_REQ/ACK/NACK feasibility screen is not a
  promising full-core branch: only 17/194 inspected R guards had initial
  destination receipt before the guard, while 177 need forward DATA rescue;
  even the source query alone consumes >=9.982 s aggregate TX ToA across
  those guards, before relays/replies. Silence remains ambiguous and DSR
  documents ACK requests. Do not implement or claim this as novel. The
  core-source mechanism remains an unresolved research problem.
- [complete] Independent review of deterministic replay and duplicate-decode
  checks found no blocker; real three-node recorder tests exercise actual
  cancellations. Root full suite: 539 passed, 1 skipped (37.80 s).
  `git diff --check`, Python compilation, and AFS CLI help pass.
- [frozen] AFS input SHA-256 immediately before mechanical seed 23000:

| Input | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `4d51d09660f06b536cbc2939e0d9410e405786b899c3f12818afacab41d00b23` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `ac12adf568714e766cff2efd67b1ba2ab6d1fc9ca4530cdd5f195e3d7f3c21b7` |
| `tools/run_afs_experiment.py` | `1bedc728d463057d93f9f0b517adb35a72c0170c2c845d056acf68cbcca4ddf7` |
| `docs/research/meshecho_dhr_design.md` | `862e7f307db6ac992235e90c34bfb7e3793e69d3168ee91d133d1db636a26d59` |
| `docs/research/meshecho_ack_terminated_flood_design.md` | `47e37befa70dbe66885c1d4c5e120982c0b910b1cc0ff46dc17624afd8f3f242` |
| `tests/test_sr_experiment.py` | `087657fff5faaf14b7c1036c1120359ebccd79a449262db89aa3f18a10a8a966` |
| `tests/test_meshecho_dhr.py` | `0f6825b1bae3222a1bd6a2275f515887087600f27d055de7cf9b8e0e31d1d7b8` |
| `tests/test_meshecho_afs.py` | `879c26ec6284562cc0c2031dd547cc06ba663ff7663b5ea0ac089bea0c0a7f1a` |
| `tests/test_afs_experiment.py` | `c85b2e59a26aed23713327e0195b16bdf7295328c018b2c26592ce2c2c74aa87` |

- [in_progress] Run only seed 23000 mechanical smoke with these inputs;
  independently validate manifest and old fixed-F/no-cancel parity before
  any 23001--23040 development cohort. Keep 24001--24040 sealed.
- [complete] Seed 23000 AFS mechanical smoke produced three matched arms;
  manifest validator replayed all three arms and passed all hashes, flow,
  action, decode, complete-TX, and no-cancel/fixed-F parity checks. AFS
  canceled 353 pending FLOODs (90 initial F, 263 recovery F). Descriptive
  one-seed ACKs: AFS 26/39, no-cancel 29/39; destination deliveries 38/39
  in both; whole-network airtime 52.8832 vs 61.390336 s. The manifest's
  project gate is false because smoke is not the development split. The
  three-ACK loss is a safety warning, not an estimated population effect.
  Manifest: `results/meshecho_afs_smoke_seed23000_20261004.manifest.json`.
- [in_progress] Run the already frozen 23001--23040 development matrix once,
  then independently validate and apply the predeclared joint gate. Do not
  open 24001--24040 if development fails; do not retune on those seeds.
- [complete] The frozen AFS 23001--23040 development matrix and an explicit
  read-only deterministic replay of all 120 seed/arm runs completed. The
  prospective cost, destination, and cancellation gates pass, but ACK-PDR
  noninferiority fails: paired difference -0.00143 with 95% CI
  [-0.04257, +0.03971] versus required lower bound > -0.02. Relative
  whole-network airtime is -19.53% [-23.80%, -15.26%]. The validator
  reaches the expected `AFS development gate did not pass; holdout remains
  closed` error after artifact/metric checks; it exits before replay on a
  failed gate, so the explicit independent replay was run separately.
- [decision] Stop positive AFS claims. Keep 24001--24040 sealed; no AFS
  tuning on 23001--23040 or manuscript/VERSION/GitHub/EDAS promotion. Full
  result and six artifact hashes are in
  `docs/research/meshecho_afs_dev_results.md`.
- [complete] A separate read-only auditor confirmed all ten frozen input
  hashes and six artifact hashes, 40/40 application-trace pairings and
  no-cancel/fixed-F parity, the paired confidence intervals, and 9,728
  witnessed cancellations. This independently corroborates the negative
  development-gate interpretation; no holdout was opened.

## 2026-10-04 - New-Core Research Continuation

- [complete] Classified the previous goal turn as progress: it completed
  frozen AFS development, full read-only replay, independent audit, and a
  negative result that changes algorithm selection. Planning catch-up
  returned no unsynced context; re-read the three Markdown records and
  inspected the dirty worktree without reverting user changes.
- [in_progress] Targeted quick research question: which bounded, device-
  observable LoRa mesh source/relay feedback could improve deadline source
  ACK and destination delivery over same-trigger fixed R/F and matched
  packet-budget controls, without merely renaming established ARQ,
  opportunistic routing, or ACK flooding? Verify close prior art and local
  exposure before freezing behavior code or fresh seeds.
- [guard] AFS 24001--24040 and all prior failed-candidate holdouts stay
  sealed. The old ICC manuscript/PDF and VERSION remain unchanged until a
  new core passes its own prospective development and untouched holdout.
- [error] The first top-of-plan status patch used an inexact context and
  applied to none of the file. Re-read the exact lines and applied this
  narrower correction; no source or experiment artifact changed.
- [in_progress] Two bounded read-only checks run in parallel: verified
  nearest prior art and source/relay local feedback availability. Locally,
  screen inspected fixed-R versus fixed-F development arms for stable
  per-pair decision heterogeneity before proposing an online selector.
- [error] A third independent full-core-design agent could not be spawned
  because the agent-thread limit was reached. Do not retry allocation;
  continue that design analysis locally while the two active checks run.
- [complete] The local-feedback screen found no supported source-only
  R-versus-F classifier: fixed F rescued substantially more destination
  deliveries in matched inspected histories, and passive first-hop
  progress/backup evidence has low exposure. These are exploratory, not a
  new algorithm trial. Source-only threshold/bandit variations are deprioritized.
- [in_progress] Screen a bounded reverse-confirmation core element: can a
  relay on the final reverse ACK hop use only its on-wire path position,
  locally received RSSI/SNR, and limited state to improve source ACKs at
  less whole-network cost than a destination's same-path second ACK?
  First quantify the physical failure/collision exposure and verify prior
  link-layer/ACK-repetition literature; do not code from the 23/37 count.

## 2026-10-04 - Fixed-Delay ACK Control Smoke Gate

- [decision] The user clarified that the algorithm core must be rewritten.
  The current calibrated-MeshEcho ICC paper and threshold-driven SR/DHR
  controllers do not yet supply that new core. Reuse the simulator and
  baseline harness; the fixed-delay ACK arm is only a simple comparator.
- [complete] Runner audit defects were repaired with tests; root full suite:
  596 passed, 1 skipped. Python compilation and `git diff --check` pass.
  Independent read-only re-audit found no blocker to mechanical seed 38000.
- [frozen] Source SHA-256 before seed 38000:

| Input | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `cfc7e36b7c2c78096eaefaa27b49f70b877e4d43fa76fbaef6d34d5b16d2d383` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `8dfdb0fdb487144923e1854f803c76f7302d7b4743081a5b3fbfb9d493c74508` |
| `tools/run_delayed_ack_control.py` | `566f593fbfa07b8459ebcebbb101ff8a1cab170a09c819b4a7b433e603427108` |
| `docs/research/meshecho_dhr_design.md` | `862e7f307db6ac992235e90c34bfb7e3793e69d3168ee91d133d1db636a26d59` |
| `docs/research/meshecho_delayed_ack_control_design.md` | `86396835b850d9dfd7fc5753acb414a5c12208aafba1e9602fe0dca93c1d8441` |
| `tests/test_meshecho_dhr.py` | `0f6825b1bae3222a1bd6a2275f515887087600f27d055de7cf9b8e0e31d1d7b8` |
| `tests/test_delayed_flood_ack_control.py` | `ff0a75b45617a92883d2665549c70d2c0f1598f096077194abef644b1a344bda` |
| `tests/test_delayed_ack_control_runner.py` | `742e4134d8f54e5d00708840e2f2694746b9671fde4471dc3e051c96ce814852` |

- [complete] Seed 38000 mechanical smoke ran once under the frozen inputs.
  The saved manifest passed full validation and strict deterministic replay;
  the two arms have the same 36-flow application trace and immediate-arm
  stock fixed-F parity. Delayed/immediate: deadline source ACKs 34/29 of 36,
  destination deliveries 36/36, and whole-network TX airtime 43.099136 /
  50.773248 s. Both have no observed post-630 TX; 660 s is still bounded.
  These one-seed numbers are not a population effect or a core-algorithm
  result. Manifest: `results/meshecho_delayed_ack_control_smoke_seed38000_20261004.manifest.json`.
- [complete] Independent read-only artifact audit verified all nine frozen
  source hashes, eight artifact hashes, strict replay, stock fixed-F parity,
  and physical 2-s ACK timing. Both arms have no post-630 TX in this smoke.
- [complete] Ran the frozen 38001--38020 exploratory pair once. Independent
  audit confirmed all nine source hashes, eight artifact hashes, 20 paired
  identical application traces, 40 strict deterministic replays, stock
  fixed-F parity, and physical ACK timing. The saved manifest validator
  passed. No observed post-630 TX; 660 s remains a bounded sensitivity.
- [finding] Delayed minus immediate seed-paired ACK PDR: +0.2251 [95% CI
  +0.1725, +0.2777]; relative complete-network TX airtime -16.73%
  [-22.24%, -11.22%]. Destination PDR +0.0024 [-0.0040, +0.0087]
  is unresolved. Source ACKs 726/781 versus 548/781, 20/20 seeds
  favorable on ACK, 19/20 lower on airtime. These are exploratory
  selected-parameter results, not a new core or ICC acceptance evidence.
  Full interpretation: `docs/research/meshecho_delayed_ack_control_explore_results.md`.
- [in_progress] Design-screen a genuinely differentiated device-local
  ACK/source-recovery mechanism that must beat fixed-2-s delay and
  same-budget ACK repeat. Verify close prior art and information available
  at decision time before coding. Keep 35001--35040 development and
  36001--36040 holdout sealed; no ICC manuscript/PDF, VERSION, GitHub,
  or EDAS promotion yet.
- [decision] A destination-local quiet-window ACK is NO-GO as the complete
  new core. In the fixed-2-s exploratory arm, 42/251 first-FLOOD receipts
  lacked source ACK; only 14 of those had a later locally decoded FLOOD
  after ACK start, and only 9 had same-flow FLOOD TX overlap during ACK.
  These are exposure counts, not causal upper bounds. A quiet-only timer
  leaves the old source F/R/D and 15-s ambiguity unchanged. Continue a
  read-only residual ACK-path diagnosis and source/feedback contract screen
  on already opened artifacts; do not open sealed cohorts or code a timer
  as the promised algorithm.
- [error] On this continuation, `python` was unavailable for the skill's
  catch-up script; `python3` succeeded with no unsynced output.
- [error] A third independent reverse-ACK-path prior-art screen could not
  be spawned because the agent thread limit was reached. Continue with
  local sources and the two active read-only screens; do not retry the
  same allocation.
- [finding] The saved fixed-2-s arm has 55/781 source-ACK misses: 11
  destination non-deliveries and 44 delivered/unACKed. Of 42 FLOOD cases,
  all destination ACKs were on time; 37 reached a final reverse TX toward
  the source, 25 had some TX overlap there, and 17 did not. The local
  duplicate-path exposure is 40/42, but 79/89 alternatives are longer
  and no alternative ACK outcome is observed. See
  `docs/research/meshecho_fixed_delay_ack_residual_screen.md`.
- [decision] No current destination ACK timing/path selector or source
  timeout variant has a defensible full-core claim. Retain simulator and
  baseline controls, but require a new jointly specified feedback and
  source-recovery state machine with device-visible inputs before behavior
  code or new seeds. The next manuscript/PDF/version/remote step remains
  contingent on prospective matched results.

## 2026-10-04 - Full-Core Contract Continuation

- [complete] Classified the prior goal turn as progress: it added a read-
  only residual ACK-path screen and independently verified the 781/55/44/42
  flow counts. Planning catch-up returned no unsynced context; the dirty
  worktree was preserved.
- [in_progress] Two independent read-only screens examine complete
  source/feedback/relay contracts, including physical-TX-start and finite-
  state semantics. Neither may change behavior code, open new seeds, or
  promote the ICC manuscript. Root is comparing against the historical
  DHR, BAR, MAG and fixed-delay evidence and prior-art boundary.
- [guard] Follow the academic-paper evidence chain for the later ICC
  revision: no new abstract, numerical table, figure, or novelty claim
  before a tested core and prospectively matched artifacts exist. Apply
  test-first vertical slices to any eventual behavior implementation.

## 2026-10-04 - Algorithm-Rewrite Clarification and Short-Guard QC

- [decision] Answer the user's clarification explicitly: the MeshEcho
  source/feedback/recovery algorithm needs a new, testable core. Reuse the
  simulator, radio/event model, accounting and baseline harness; do not
  present route-score tuning, a fixed ACK delay, a short R guard or a
  same-path ACK repeat as the new core.
- [complete] The documented quality-control rerun of already opened
  40001--40020 short-guard seeds exited successfully and wrote
  `results/meshecho_delayed_ack_short_guard_explore_40001_40020_qc_v3_20261004.manifest.json`.
  It is not an independent cohort. Its frozen-input/artifact/strict-replay
  audit and the seed-40005 guard2 D-to-R fallback check are in progress.
- [decision] Do not freeze the earlier passive first-edge screen's 1.5x
  alternate-ACK airtime cap. Screen timely alternative first hops, then
  charge exact complete reverse-path ACK ToA against the two-copy
  same-path budget, then assess a predeclared 3-dB first-edge margin
  difference. Any ACK1+ACK2 implementation must account for the sum of
  both paths' airtime. The existing whole-path minimum margin does not
  supply a separate first-edge measurement; this is still an untested
  feasibility question, not a paper claim.
- [guard] Keep 35001--35040 and 36001--36040 sealed. No ICC manuscript,
  PDF, VERSION, GitHub or EDAS promotion from this control experiment.
- [error] A multi-file audit-record patch used an inexact findings.md
  context and applied to none of the files. Re-read the exact tail and
  used this narrower patch; no experiment or source code changed.
- [complete] Independent 40001--40020 QC-v3 audit passed 12 frozen input
  hashes, 10 artifact hashes, saved-evidence validation, 200 strict
  main/extended replays and 20 current-code stock parity checks. Seed
  40005 guard2 flow19 is initial D followed by D-to-R DATA, a 15-s
  timeout, and no DHR recovery. Across 825 flows per arm, guard1/2/4/8
  versus guard15 source-ACK differences are -0.01105/-0.01454/-0.01111/
  -0.00024; all paired 95% intervals cross zero. Relative complete-network
  airtime differences are +4.05/+2.48/+4.29/+3.08%; all intervals cross
  zero. A fixed short guard is NO-GO as a claimed new core. This QC rerun
  is not a new independent sample.

## 2026-10-04 - New-Core Feasibility Phase

- [complete] Classified the previous goal turn as progress: it completed
  the independent 40xxx QC-v3 strict audit and changed the algorithm
  decision. Planning catch-up reported no unsynced context; the dirty
  worktree remains preserved.
- [in_progress] Independently review a behavior-preserving first-edge
  FLOOD/ACK path witness diagnostic and an adversarial core-algorithm
  alternative. No reserved seed or behavioral policy is authorized by a
  design sketch alone. Root will freeze an exact observable/byte/cost
  contract before test-first implementation.
- [guard] The current ICC manuscript evaluates calibrated route scoring,
  not the proposed new source/feedback/recovery core. Under the academic
  paper claim-evidence workflow, do not rewrite its methods or numerical
  claims until the new protocol passes matched development and untouched
  validation. Keep 35001--35040 and 36001--36040 sealed.
- [decision] JFC as written is NO-GO for direct implementation: its P2
  diversity is on the destination-adjacent edge rather than the
  source-final ACK edge, whole-path minimum margin is not a calibrated
  first-edge/reverse predictor, direct-to-two-hop ACK exceeds even a
  two-copy direct ACK nominal airtime budget, and fixed 8-s guard showed
  no improvement over 15 s in audited 40xxx. Retain the draft as
  rejected design history, not an ICC method.
- [complete] Froze the read-only first-edge signal/cost gate in
  `docs/research/meshecho_first_edge_ack_signal_gate.md`: causal parent
  join, physical first-edge RxInfo, 2-s destination window, complete
  charged reverse ToA, predictor validation, stock parity, separate
  42000/42001--42020/42101--42120 ranges, and predeclared no-go.
- [in_progress] Implement the frozen passive diagnostic test-first without
  changing protocol behavior or opening reserved seeds. Independently
  design a formal source-local R/F/R-to-F decision candidate; neither
  branch is a paper result yet.
- [decision] The independent source review found no credible proven
  source-only novelty in a Bayesian/threshold controller given sparse
  per-pair history and no-ACK ambiguity. Before any source behavior code,
  run one read-only decision-time signal screen on already-opened 38xxx
  fixed-2-s artifacts; then require fresh same-feedback four-action
  branches and strong simple-policy controls if signal survives.
- [in_progress] Implement that bounded source risk screen in new files
  only, with no new seed or protocol change. Its prediction target is an
  accepted initial-R ACK before the 15-s guard, not eventual flow ACK
  after F recovery.
- [error] A refinement patch for the first-edge gate used an inexact
  wrapped paragraph and applied to none of the files. Re-read the exact
  text and applied a narrower correction; no code or experiment changed.
- [decision] Separate the alternative-path cost/exposure gate from a
  first-edge-margin predictor for selective same-path ACK repeat. Failure
  of cost-feasible path diversity must not silently veto the independent
  predictor screen; any eventual adaptive-repeat claim must beat the
  fixed 2-s one-repeat control under charged airtime.
- [error] A first-edge contract refinement patch missed the wrapped ACK2
  timing paragraph and applied to none of the files. Re-read exact lines
  and applied a narrower patch; no protocol or seed changed.
- [complete] The read-only source risk screen of archived 38001--38020
  artifacts passed frozen manifest/artifact/source-provenance checks and
  eight focused tests. Strict initial-R cohort: 613, with 449 accepted
  initial-R ACKs by guard. Adding hop count improved equal-seed Brier
  by 0.01154 [0.00295, 0.02013], but prior-miss cells had only 19 and
  eight records (the latter seven seeds), failing the predeclared 20/
  eight support gate. ACK-age added 0.00026 [-0.00351, 0.00404] and also
  failed support/gain. Source-only risk candidate is NO-GO; this is not
  a counterfactual action-value experiment or ICC novelty.

## 2026-10-04 - Decision-Time Source Screen QC

- [complete] Classified the preceding algorithm-boundary answer as no new
  implementation or experimental progress. Recovered the current dirty
  worktree with the planning skill; no unsynced context was reported.
- [complete] After the decision-time feature and post-deadline R-start QC
  correction, `tests/test_source_risk_signal.py` passed 10/10. The read-only
  archived 38xxx screen reproduced 613 true initial R, 449 initial-R ACKs,
  all three Brier scores and the sparse 19/8-cell NO-GO. The complete
  current regression suite passed 704 tests with one skipped.
- [in_progress] Independently audit the first-edge passive diagnostic's
  ACK2 schedule, path-type predictor gates, manifest validation, stock
  parity and strict replay before opening seed 42000. A separate read-only
  algorithm feasibility review is in progress. No 42000, 42001--42020,
  42101--42120 or sealed 350xx/360xx seed has been run in this phase.
- [NO-GO before smoke] Independent review found three diagnostic blockers:
  cutoff-late physical final-hop TXs are not counted, per-path-type
  validation can pass without adequate type-specific training support,
  and a hash-valid but semantically inconsistent exploration summary can
  falsely open validation. Ambiguous causal decodes also need an explicit
  whole-epoch rule. ACK2 spacing itself matches the frozen contract.
  Test-first repair is in progress; 42000 remains closed until independent
  re-audit, full regression, exact input freeze and one mechanical smoke.
- [exploratory NO-GO] A read-only forensic screen of audited 41001--41020
  same-path-repeat artifacts found 16 ACK2-first source accepts from 250
  destination repeat starts across 10 seeds. Fourteen had a later same-pair
  decision; 13 across eight seeds had no intervening route-confirming ACK;
  only 12 across seven seeds also had an ACK1 tail-hop opportunity for a
  source-adjacent repeat. This is below the provisional >=20 decisions /
  >=10 seeds feasibility threshold for a copy-index-driven fragile-route
  full core. The current ACK copies are wire-identical, so this is offline
  forensic exposure, not source-observable feedback or counterfactual gain.
  Do not implement this candidate as the new ICC core from this screen.
- [complete pending independent pre-smoke audit] The first-edge diagnostic
  now counts cutoff-late final-hop TXs while censoring their decode,
  rejects entire causally ambiguous epochs, requires train and validation
  support within each claimed path type, and recomputes exploration support
  and model from hashed predictor rows. These changes were red/green tested:
  20 focused tests passed. Root's current full `pytest` suite passed 710
  with one skipped; compilation passed. Exactly one 42000 mechanical smoke
  remains closed until a separate read-only pre-smoke GO and input freeze.
- [GO for 42000 only] Independent read-only review confirmed all four
  diagnostic repairs, 20 focused tests, source parity and strict replay.
  It authorized exactly one 42000 mechanical smoke under the hashes below,
  followed by a separate saved-artifact audit. It did not authorize
  42001--42020 or 42101--42120. Malformed identity/path/TTL rejection
  and complete exposure-summary recomputation remain post-smoke audit
  checks, not affirmative population results.

| Frozen 42000 input | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `165fff13ac3839045b41bf39a8e9451503c50e0c66ca4cc39c92709e5eaf2875` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `f61b2bccb154c7ec3f7603c51dd47ff2b8271d68db4baa69e2ccee5a4a1d0d1c` |
| `tools/diagnose_flood_ack_hops.py` | `b587af3f48f8c1de2c3896be00e3603e3d34516ace893eec06419bddbd3c243f` |
| `tools/diagnose_ack_failure_causes.py` | `777c83db614758855418618ea39ba115640b454b133f37f9f73e076785dd06b5` |
| `tools/diagnose_delayed_ack_rx.py` | `7493ee072697845673ee66fbe7a2c537f247e1ac1f43733043d094906d16e4c1` |
| `tools/diagnose_first_edge_ack_signal.py` | `d0a3e5746002ba06f6a3cbf20f6fa286cc7be5a7bf1cfe4d7642ec90400f0d91` |
| `tests/test_first_edge_ack_signal.py` | `3a5318345eb23c2550e606fa59e48089c5338576a43a36ad1236aa4f45d5733e` |
| `docs/research/meshecho_first_edge_ack_signal_gate.md` | `1fc1ea54c0962e88ef80e8aef9c5d0546c96f39525b1fec01bf407938587d5ef` |

- [smoke audit pending] Ran exactly one 42000 passive mechanical smoke at
  `results/meshecho_first_edge_ack_signal_smoke_seed42000_20261004` under
  the frozen inputs. It exited successfully and saved eight artifacts plus
  a manifest and sidecar. Its self-reported mechanics are 49 scheduled
  flows, 37 valid destination path decodes in 10 FLOOD epochs, 10 in-time
  final-hop predictor attempts (eight decodes, two failures), and zero
  rejected paths. The one-seed 2/2 alternate-path opportunity is not a
  population estimate. An independent saved-artifact, parity and strict-
  replay audit is in progress; 42001--42020 remains closed pending GO.
- [smoke audit complete / GO for exploration only] Independent 42000 audit
  matched all 9 frozen input hashes and 8 data-artifact hashes, official
  manifest validation, saved 49 flows/219 actions/684 physical TX/37 paths/
  10 epochs/10 predictor rows, stock parity, both RNG states and a strict
  full-field replay. All 684 TX ToA and 49 original 30-s deadlines/status
  were recomputed; 37 destination decodes have valid causal paths. Two
  source-final failed flows satisfy A/B/C under the one-byte ACK charge,
  but an original direct ACK plus one two-hop alternative costs 0.154368 s
  versus 0.102912 s for two direct same-path ACKs. This is not equal-cost
  two-ACK evidence. Open exactly 42001--42020 once under the unchanged
  smoke-manifest gate; 42101--42120 and sealed cohorts remain closed.
  If malformed identity/path/TTL paths appear, stop interpretation and
  resolve their whole-epoch scope before a population claim.
- [exploration audit pending] Ran the exact frozen 42001--42020 passive
  cohort once via the audited 42000 smoke manifest. Official manifest
  validation passes. Self-reported evidence: 820 scheduled flows, 230
  FLOOD ACK epochs, 748 valid destination path decodes, 29 delivered/
  unACKed FLOOD flows, 20 source-final failed flows. Nested alternate-
  path exposure A/B/C/deadline is 18/8/6/6; the >=8-flow gate fails even
  though 6/20=30% exceeds its 20% fraction. Pooled predictor training
  has 221 attempts, 201 successes and 20 failures, but direct training
  has only 85 attempts/15 failures and multihop only five failures. Both
  path-type training support gates fail, so the prespecified scoped
  predictor claim cannot pass and 42101--42120 should remain unopened.
  Await independent artifact, strict-replay and arithmetic audit before
  treating these as a confirmed NO-GO. No core behavior/paper change.
- [audited NO-GO] Independent 42001--42020 exploration audit matched all
  9 frozen source hashes, 8 artifact hashes, smoke-manifest link and all
  20 stock/passive/strict replays including both RNG states and full
  metrics/flow/action/TX/path/epoch/predictor rows. It independently
  checked 820 scheduled flows, 12,632 physical TX, 748 valid paths,
  230 epochs and 483 alternative paths with complete ACK ToA/deadline
  arithmetic; no rejected or malformed path occurred and no post-630 TX
  was observed. Only 6 of 20 delivered-unACKed source-final failed flows
  satisfy A/B/C/original deadline, below the preregistered minimum 8.
  Only two of those six have an original-plus-alternative ACK pair no
  costlier than two original copies. Direct predictor training has
  85/70/15 samples/successes/failures and multihop 136/131/5; both
  fail type-specific support although pooled 221/201/20 barely passes.
  Both research branches are NO-GO. Keep 42101--42120 unopened and do
  not promote JFC, adaptive ACK selection or the ICC manuscript from this.
- [candidate screen, no behavior code] A source-local accepted-ACK SNR
  feature has higher raw availability than ACK-copy identity: all 654
  initial R decisions in the old 41xxx fixed-2-s single-ACK arm had a
  prior same-pair ACK, but only 177 prior ACK/decision times shared an
  offline 60-s fading block, and old artifacts saved no source RxInfo.
  A new passive 430xx screen could test its predictive value without a
  wire byte; it must not use model fading truth as an online feature or
  claim causal F/R action benefit. Freeze design only after prior-art and
  measurement-contract review.
- [guard] No new core behavior or ICC manuscript/PDF, VERSION, GitHub or
  EDAS update until a device-observable contract and matched evidence pass.

## 2026-10-04 Source-ACK Quality Continuation

- [complete] Previous clarification-only goal turn was classified as no
  algorithm/paper progress. Recovered the current dirty worktree and all
  three planning files; session catch-up reported no unsynced context.
- [complete] Revised the prospective 430xx gate's statistical and temporal
  contract after independent review: correct Armijo/KKT signs, one-class
  and empty-seed NO-GO, deterministic bootstrap, both simple-comparator
  deltas for path claims, route-generation matching and post-interference
  SINR as primary q. An independent read-only rereview found no remaining
  P0 for test-first passive collection; exact-deadline start, same-time
  commit ordering and offline `collided` capture are now explicit.
- [in_progress] Implement a passive ACK-quality measurement and decision-
  time cohort in red/green vertical slices. The first two slices pass four
  focused tests: single receive-call capture with TX/metrics/both-RNG
  parity, unique accepted action join, rejected off-index decode and
  ambiguous-action rejection. No 430xx seed has been run. Next: validate
  route-generation/guard labels and full-run strict stock parity/replay,
  then implement/freeze the prespecified model and manifest before a
  mechanical 43000 smoke. Only after separate smoke audit may 43001--43020
  exploration open; 43101--43120 remains sealed pending its support gates.
- [boundary] The candidate ACK-quality source controller is not an
  algorithm result: historical 649 initial-R decisions have usable prior
  ACKs, but only 176 share the next R's fading block. Source q predictive
  gain and F/repeat action value remain unknown. The new core, paper/PDF,
  VERSION, remote GitHub and EDAS are unchanged.
- [holdout integrity incident] During a parallel runner guard red test,
  reserved seed 35001 was accidentally simulated and 36001 was partially
  entered before an abort. The same test completed 42101 and reran the
  previously opened 42000 in memory. The parametrized tests called
  `run_report` only, never `write_report`; no artifacts were saved and no
  effect estimate was promoted. **35001, 36001, and 42101 are no longer
  untouched** and must be excluded from any future holdout claim. 42000
  was already an opened mechanical smoke, not a holdout. Actual seeded
  guard tests are stopped; subsequent tests stub `run_diagnostic` before
  asserting rejection (20 focused tests pass without simulation). Keep
  other reserved seeds closed and pre-register fresh disjoint holdouts if
  a new core ever reaches validation.
- [core decision] Independent source/experiment review confirms the ICC draft
  still evaluates calibrated max-min route scoring, with no demonstrated
  gain against same-recovery PRR-product. The JFC candidate and other
  tested repairs did not pass their own gates. A substantive core rewrite
  remains required; no current candidate is justified as that new core.
  Continue the passive source-ACK-quality signal screen only as a bounded
  feasibility diagnostic, not as an algorithm or paper result.
- [in_progress] Independent 430xx pre-freeze audit found missing recovery
  reporting, complete-denominator path outcomes, offline age/interference/
  fading strata, clean-SNR sensitivity, direct diagnostic seed guarding,
  and actual predecessor-manifest checking. Test-first repairs are in the
  diagnostic, model, runner and tests; 430xx remains closed pending a
  fresh independent audit, full regression and exact input freeze.
- [integrity incident / supersedes 43000 smoke plan] During an adversarial
  saved-manifest audit, a temporary fake smoke report triggered the newly
  added independent replay on declared seed 43000. It completed one
  stock/passive/strict-replay diagnostic in memory, then rejected the fake
  report. No 43000 result was saved or interpreted, but **43000 is no longer
  untouched** and cannot serve as the prospective mechanical smoke. No
  process or project result artifact remained. Reserve previously unused
  **43200** as the replacement smoke, with 43001--43020 exploration and
  43101--43120 validation still unopened. The contract remains draft and
  all real 43xxx seeds are closed until re-audit and re-freeze.
- [safety change] A read-only-looking `validate_manifest` call must never
  launch a real seed implicitly. It now requires `replay=True` for real
  manifests before even reading the file; the frozen runner supplies this
  explicitly after seed/mode/contract checks. Adversarial replay tests stub
  `run_diagnostic`; no further 43xxx run is authorized by this change.

## 2026-10-04 ACK-Quality Smoke-Only Freeze

- [complete] The forged-smoke fixture was repaired without weakening the
  writer. A separate per-stage JSON authorization gate now rejects missing,
  mismatched or changed exploration/validation permits before any seed or
  predecessor replay. Later permits remain outside the frozen source set;
  the smoke does not require or create one. An independent static audit gave
  GO for exactly one 43200 mechanical smoke, not for 43001--43020 or
  43101--43120. The frozen-source full suite passed 801 tests with one
  skip in 46.15 s, Python compilation and `git diff --check` passed.
- [frozen-before-43200] Case: `recurring_fading`, deadline 30 s, exact smoke
  seed `(43200,)`, case SHA-256
  `b3cfb113aded1b1487cf2a5426225cb1188143384a6fe90b770b855e5273b491`.

| Frozen input | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `165fff13ac3839045b41bf39a8e9451503c50e0c66ca4cc39c92709e5eaf2875` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `f61b2bccb154c7ec3f7603c51dd47ff2b8271d68db4baa69e2ccee5a4a1d0d1c` |
| `tools/diagnose_delayed_ack_rx.py` | `7493ee072697845673ee66fbe7a2c537f247e1ac1f43733043d094906d16e4c1` |
| `tools/diagnose_source_ack_snr.py` | `a7937f42e8ad2ab820f0d73e1f9223b6bc1e2647337580e2051252073aaeb451` |
| `tools/source_ack_quality_model.py` | `8d494ad565179309863e1121f9504148837889146b2e68a520c247cc29ed84a0` |
| `tools/run_source_ack_quality_gate.py` | `48ec73815a1e91284aeb465702510881b12e1e1e0648ecd0ac2ce2016fbb3f52` |
| `tests/test_source_ack_snr.py` | `fef7b420b5fb463d985c0412ce2dc3436969d18a2c4a94ffefe1d42cb45f9213` |
| `tests/test_source_ack_quality_model.py` | `256b62a3aa960e2ae5c0fcc03745670550be3569764ca031c67b4b84d73d0995` |
| `tests/test_source_ack_quality_gate.py` | `27229e954304693d4278b24c21fa71267d87912a49cb17985b6ade432670222e` |
| `docs/research/meshecho_source_ack_snr_signal_gate.md` | `dde63707612511b94e53ba684b206e35a4542f05f7e3d5f8d9bc9242f7652192` |

- [next] Run the exact 43200 mechanical smoke once at a new, non-overwriting
  output prefix. Require independent saved-artifact, source-hash, stock/
  passive parity and strict-replay audit before considering a separate
  exploration authorization. Keep all 43001--43020 and 43101--43120 seeds
  closed meanwhile. No core behavior or ICC manuscript claim follows from a
  smoke alone.
- [smoke saved / audit pending] Ran exactly seed 43200 once through the
  frozen runner at `results/meshecho_source_ack_quality_smoke_seed43200_20261004`.
  The writer created four no-overwrite artifacts. Manifest SHA-256:
  `97513ee5378446836a05e82b4e2ef3618fb1684f55bdc72ddcea3ec0522fefd1`;
  summary `ef9944f551a410bd2a2bad5e62b9fc8123f2e0c85566106c3f8891fbd0a1ad25`;
  runs `3cf7bcfae4dd20a74ec116213cfd2459201c2ea833081b6a15c789872bfe7651`.
  The smoke reports 38 initial R decisions, 38 eligible, 32 guard ACKs,
  six guard misses, six later recovery starts and five recovery ACKs;
  these are software smoke counts, not evidence for a population or
  manuscript claim. An independent artifact/strict-replay audit is active.
  `results/` is ignored by default `rg --files` and Git status, so use
  `rg --files --no-ignore results` for absence checks; the runner itself
  checks each exact output path and uses exclusive creation. No 43xxx
  exploration or validation artifact exists.
- [smoke independently audited / GO for exploration only] The saved
  manifest, sidecar, summary and runs matched all 11 frozen source hashes,
  case hash and artifact hashes. Official explicit-replay validation passed
  for 43200; saved flow/action/TX/ACK/cohort digests and both RNG states
  matched stock/passive and strict replay. Independent recount confirmed
  47 flows, 625 TX, 219 actions, 63 source ACK decode rows, 38 initial R,
  38 eligible, 32 guard ACKs, six misses, six physical recoveries and five
  recovery ACKs. Opened a separate immutable exploration permit at
  `docs/research/meshecho_source_ack_quality_explore_43001_43020.authorization.json`
  binding exactly 43001--43020 to the frozen source/case and audited smoke
  manifest. This is not a validation permit or algorithm result.

## 2026-10-04 Stage Authorization Continuation

- [complete] Repaired the forged-smoke test fixture's `summary.by_seed` after
  a seed rename; the intended independent replay rejection now passes.
- [complete] Added separate exact-input JSON stage permits for exploration
  and validation outside `SOURCE_FILES`. The runner and explicit manifest
  replay require them before any seed or predecessor replay, record the
  current permit byte hash, and compare validation's exploration permit
  byte hash against the saved exploration manifest. CLI flags and the
  draft contract describe the permit schema. No permit exists for a real
  cohort yet.
- [verified] 85 related tests and the full suite (801 passed, one skipped)
  passed; compilation and `git diff --check` passed. The 43200 smoke and
  43001--43020/43101--43120 research cohorts remain unopened.
- [in_progress] Obtain independent read-only pre-freeze GO, then freeze
  exact source/contract/case hashes for at most one 43200 mechanical smoke.
  Audit that smoke before any exploration permit is created. A passive
  signal, even if supported, is not the requested new core algorithm or
  a paper result; action-level controls and untouched validation remain.

## 2026-10-05 ACK-Quality Numerical Continuation

- [supersedes stale stage notes above] The frozen 43200 smoke and authorized
  43001--43020 exploration are complete and independently artifact/replay
  audited. The exploration has 697/697 eligible initial R decisions, 508
  guard ACKs and 189 misses. Both primary q and clean-SNR fits are official
  NO-GO because their shared leave-one-seed-out M0 fit failed to converge.
  See `docs/research/meshecho_source_ack_quality_explore_results.md`.
- [boundary] The 430xx observations diagnose a numerical fit failure, not
  whether q predicts future ACK outcomes. Keep the saved frozen artifacts
  immutable. 43101--43120 and their validation authorization remain unopened.
- [in_progress] Preserve the old frozen source snapshot; reproduce the
  near-stationary Armijo issue on synthetic rows; make a test-first,
  numerically justified solver fix and independent review. Then freeze a
  revised contract/source with fresh, disjoint smoke/exploration/validation
  seeds. The inspected 430xx rows may debug but cannot validate the fix.
- [complete] Saved an exact frozen-source archive, added a synthetic red
  regression, repaired direct objective-difference Armijo arithmetic, and
  passed independent review plus 802-test full regression. Recomputed only
  saved 430xx rows as a software diagnostic; both fits finish, but q's
  exploratory mean LOSO gains (0.002972 vs M0, 0.004080 vs T) are below
  the prespecified 0.005 validation mean gate. Frozen result stays NO-GO.
- [in_progress] Screen stronger device-observable core mechanisms and
  controls before spending fresh prospective seeds on q. Do not open
  validation or promote any ICC claim from the repaired old-row fit.
- [later] Only a supported signal can motivate a separately named,
  device-observable MeshEcho-SR source/feedback/recovery core. Match its
  physical airtime and deadline against fixed-2-s single ACK, equal-budget
  repeat and old F/R controls on fresh development and untouched holdout;
  rewrite the ICC method/results only from passed evidence. Paper/PDF,
  VERSION, GitHub and EDAS remain unchanged at this stage.

## 2026-10-05 Forward-Backup Core Screen (current continuation)

- [goal boundary] The user reaffirmed that a publishable MeshEcho-SR revision
  needs a rewritten core algorithm, not another parameter tweak. Retain the
  tested simulator and old policies as infrastructure and comparators; the
  current ICC paper still describes the old calibrated route-score policy.
- [provisional exposure, not efficacy] A read-only join of the already audited
  42xxx paths found distinct duplicate-F routes in 186/201 source-confirmed F
  ACKs and a matching-generation backup at 108/141 later initial-R no-ACK
  guards. Existing fixed-F rescue already delivered 107/108 and source-ACKed
  94/108 of those exposed flows. In 84/108 cases the backup observation was
  at least 60 s old by the guard. These are historical opportunities, not
  backup-R counterfactual successes or an ICC claim. Independent contract and
  code audits are in progress.
- [in_progress] Specify one *separately named* device-observable source/
  feedback/recovery contract, including ACK-carried backup bytes, bounded
  destination/source state, route generation, physical-start/deadline guards,
  duplicate handling, and a prior-art-limited hypothesis. Preregister the
  simplest fixed-2-s single-ACK/F-rescue and same-budget R-repeat controls.
  Do not use any old inspected cohort as prospective validation.
- [pending] After independent critique, implement one public-behavior TDD
  vertical slice, then fresh development and untouched holdout only under
  an explicitly frozen contract and source hash. Rewrite the LaTeX, figures,
  PDF and version only from verified outcomes. Do not claim a benefit simply
  because a candidate compiles or passes mechanics tests.
- [error log] `python` is absent in this shell for the planning catch-up
  helper; `python3` succeeded with no unsynced-context report. An additional
  experiment-audit subagent could not start because the thread agent limit
  was reached; the root agent is doing that audit locally.
- [draft contract] `docs/research/meshecho_deadline_backup_core_draft.md`
  specifies the proposed no-D F/R source policy, charged ACK-borne backup,
  bounded destination collection, staged backup-then-F recovery, DSR-like
  same-wire controls and prospective gates. Independent novelty review says
  bare alternate-route failover is prior art; no novelty or outcome is
  asserted. The draft is not frozen and 44xxx seed IDs are not authorized.
- [mechanics in progress] Added an isolated `meshecho-dbr` protocol type and
  explicit charged `Packet.alternate_path`. Four red/green public-behavior
  slices cover backup ACK collection/bytes, backup R with ACK-only route
  promotion, backup miss followed by F under the original deadline, and no
  future-TX reservation when the source is busy. A fifth slice rejects ACKs
  from a radio sender not adjacent on the encoded reverse path. The old
  protocols and ICC paper have not been rewritten or used as new results.
- [verification] Packet/DBR focused suite: 11 passed. A full suite after
  the first four slices passed 807 tests, one skipped; compilation and
  `git diff --check` passed. Re-run full regression after subsequent edits.
- [next] Test route-generation and malformed alternate-path rejection,
  destination candidate/capacity edge cases and delayed ACK cancellation;
  add a provenance-checked runner before any mechanical smoke. Independently
  audit contract and source; freeze only if no correctness/novelty blocker.
- [controls complete mechanically] The four matched comparison modes are now implemented:
  same-path probe, first-alternate probe, backup-byte-padded fixed-F, and
  plain fixed-F. Public tests cover each mode's recovery action and the
  seven-byte ACK difference in a three-node backup example. This completes
  only the initial control implementation, not the provenance runner or
  prospective evidence gate. The latest full suite is 812 passed, one skipped;
  compilation and `git diff --check` pass. The 44200/440xx/441xx cohorts
  remain unauthorized and unopened.
- [decision clarification] The research target is a rewritten source/
  feedback/recovery decision core, not a parameter adjustment to the old
  calibrated route score. Reuse the simulator and old protocols as tested
  infrastructure and comparators. DBR itself is provisional: if it cannot
  distinguish itself from byte-matched fixed-F and DSR-like first-alternate
  on fresh data, reject this candidate rather than relabel it a new algorithm.
- [independent review risk] Current DBR and first-alternate use the same
  backup when it is fresh, so the 120-s staleness refusal may be the only
  frequent branch difference. Finish event/reason accounting and boundary
  tests before freeze; require prospective branch divergence and a real
  paired advantage, or redesign the core mechanism.

## 2026-10-05 DBR Correctness and Runner Audit Continuation

- [complete] Three public red/green slices now require a per-flow DBR guard
  reason, reject backup recovery after primary-route TTL expiry, and reject
  a destination FLOOD whose claimed endpoints disagree with the registered
  flow. These are correctness/observability fixes, not new performance data.
- [complete] A fourth slice corrected FLOOD deadline admission to include
  the largest charged ACK-carried backup path; a fifth records the ninth
  concurrent destination feedback window's capacity fallback. No protocol
  benefit is inferred from these mechanical tests.
- [in_progress] Resolve the remaining independent-audit P1 cases: canceled
  recovery TX requests without a truthful reason or fallback, and late
  initial R ACK interleaving with backup/F ACK. Add capacity and ACK-byte
  bound tests and complete actual-start/rejection event accounting.
- [runner boundary] `tools/run_sr_experiment.py` misses DBR marker-3 recovery
  in its DHR-specific counters, can mis-bind DBR to LPR source hashes, and
  does not save all physical transmissions. Build a separate DBR runner with
  exact stage authorization, tuple-normalized saved packets, full-TX replay,
  all-scheduled-flow denominators, and five fixed same-wire arms. The 44200
  smoke and 440xx/441xx cohorts are still unauthorized and unopened.
- [error log] The first ACK-byte patch matched the adjacent backup-DATA
  round-trip estimator, not the FLOOD estimator. Inspection caught it before
  a green test; the field was moved to FLOOD and removed from routed DATA.
  All focused DBR tests must pass before broad regression.
- [complete] Recovery requests now distinguish a guard decision from a
  physical start. Red/green interleaving tests cover canceled B requests,
  canceled/queued F requests, radio-busy guards and a late initial R ACK
  canceling a deferred F timer. An actual-start recheck may schedule a new
  decision timer at radio idle but never reserves a future TX slot.
- [complete] A red/green reordered-ACK test reproduced an old-generation B
  ACK overwriting a newer F route commit; B now acknowledges that flow but
  skips route promotion unless the originally sent primary generation still
  matches current source state. Add remaining malformed-path/source-capacity
  and event-reconciliation tests before freezing.
- [complete] A source-accepted marker-3 ACK now emits its own DBR event; the
  old DHR ACK logger did not see it. Focused DBR/packet-airtime verification
  is 24 passed, with Python compilation and whitespace checks passing.
  Independent post-fix audit and a full regression are pending.
- [audit complete, 2026-10-05] Independent protocol review found no reproduced
  duplicate-F or route-rollback P0/P1 on the normal event path, but still
  requires same-time multi-request and competing R/B/F ACK-order tests.
  A 2-s backup guard has only about 0.11-s nominal headroom at SF10 with a
  two-hop path; PHY/queue sensitivity remains a prospective risk.
- [runner NO-GO] The initial dedicated DBR runner is only a fail-closed
  foundation. Direct `capture_arm` access bypasses its stage gate; it lacks
  saved manifest/full-TX replay, all-flow/cross-arm audits, physical-cost
  reconciliation and paired statistics. Its TX writer also mismatches the
  captured dictionary shape. Do not open 44200/440xx/441xx from this runner.
- [decision] A publishable rewrite means replacing the old source/feedback/
  recovery policy, while retaining the simulator as measurement machinery.
  DBR remains a provisional candidate, not an accepted final algorithm: if
  its only meaningful difference from first-alternate is a 120-s freshness
  cutoff or it cannot beat byte-matched fixed-F, redesign it instead of
  changing the paper to fit an unsupported claim.
- [verification] The full suite after the `decision_admitted` rename and
  runner foundation passed 840 tests with one skipped; `git diff --check`
  passed. This verifies mechanics only, not efficacy or novelty.
- [next] Close the protocol boundary tests and runner audit gaps. Freeze only
  after independent review; the ICC
  paper/PDF, VERSION, GitHub, EDAS and all reserved DBR seeds remain unchanged.
- [read-only risk screen] A stricter latest-F-commit/first-hop-diverse join of
  the already inspected 42xxx diagnostic artifacts found 105 candidate
  guards, only 32 with backup age above 120 s (17 in the first ten seeds).
  This is not a DBR counterfactual, but it sharpens the novelty/exposure
  risk: after mechanics and runner audits, require prospective branch
  divergence before spending an untouched holdout or rewriting positive
  claims. The first `jq` join mistakenly dropped outer epoch seed; a
  corrected structured join produced these counts.
- [protocol audit] Clarify DBR's destination use of the simulator-wide flow
  registry before freezing a device-local algorithm claim. Preserve honest
  metrics identity for malformed packets without pretending a real device
  can consult that registry.
- [complete] Public DBR tests now cover coincident idle-time F rechecks,
  R/B ACKs at their guard boundaries, F-first ACK completion, and old R ACK
  after a newer F route commit. No new normal-path P0/P1 was reproduced.
  Destination ACK policy no longer consults global flow registration; the
  simulator accounting layer rejects mismatched-origin delivery credit.
  This is not authentication; the paper must state a non-adversarial model.
  DBR-focused tests passed 24/24. A temporary full-suite failure was in a
  runner test concurrently RED and is being resolved by its owner.
- [runner foundation complete] The dedicated DBR smoke harness now validates
  stage inputs even for direct `capture_arm`, requires a fresh output
  directory, persists runs/flows/actions/full physical TX/authorization plus
  a hashed manifest, and reopens artifacts to reconcile per-flow deadlines,
  paired traffic, packet ToA, complete-network airtime, bytes, marker-3 starts
  and TX energy. Development/holdout remain intentionally closed pending a
  predecessor-manifest gate and independent audit. No real stage permit or
  reserved 44xxx seed has been used.
- [verification] After the destination accounting follow-up and runner
  completion, full suite: 857 passed, one skipped in 43.60 s. Python
  compilation and `git diff --check` passed. The runner's independent
  post-implementation review is still pending; passing tests do not freeze
  the contract or authorize the 44200 smoke.
- [in_progress, 2026-10-05] Independent runner audit found the generic
  `run_one_sr` path can start a reserved 44xxx seed before the dedicated DBR
  gate, including on a non-DBR comparator. Its public red regression is now
  reproduced. Guard every reserved seed before topology generation, pass
  stage authorization only from the dedicated runner, then rerun targeted and
  full tests. Separately verify archived stage/row identity and action-to-TX
  consistency before contract freeze. All 44xxx seeds remain unopened.
- [complete, 2026-10-05] Generic `run_one_sr` now checks every DBR reserved
  seed before node generation, regardless of policy, and requires the DBR
  capture token plus a validated stage permit for a registered arm. The
  dedicated capture path passes both. Parametrized bypass regressions and
  a protected nonreserved fixture pass (33 DBR-runner tests); full suite
  remains to rerun after concurrent artifact-audit edits settle.
- [complete, 2026-10-05] Persisted DBR evidence now checks canonical
  stage/seed/arm/case/deadline identity and each run row's identity/timing;
  backup DATA and F/R recovery action events must match complete physical
  source TX records one-to-one. The manifest must assert exact strict replay.
  DBR-focused verification reached 74 passed before the final replay-flag
  slice; full regression then passed 877 with one skip. Re-run after that
  final slice and collect independent post-fix audit before any freeze.
- [complete, 2026-10-05] Finished a prospective DBR go/no-go review: confirmed policy-local
  state, matched control equivalence, event/physical exposure and novelty
  boundary. The scientific result is NO-GO for this candidate, so no freeze
  or stage permit was created. Development/holdout predecessor gates, paired
  statistics, and external trust anchoring remain unresolved; do not open
  44xxx seeds.
- [decision, 2026-10-05] Post-fix independent runner review found no new
  P0/P1 provenance/accounting defect and judged the harness mechanically
  smoke-ready only after an explicit contract freeze. A separate scientific
  review recommends NO-GO for current DBR as the paper's core: selective and
  first-alternate take the same action for every fresh backup and differ
  mainly on the 120-s age cutoff; old exposure is too narrow and noncausal to
  justify consuming prospective development/holdout. Do not freeze DBR or
  open 44200/440xx/441xx while selecting a more distinct mechanism.
- [in_progress] Revisit device-observable failure evidence and prior art to
  define a redesigned source/feedback/recovery decision rule with a clear
  comparator divergence and pre-implementation exposure gate. Retain DBR
  code and tests as a provisional negative/control candidate, not a paper
  result. Current ICC LaTeX/PDF, VERSION, GitHub and EDAS stay unchanged.
- [next exact action] Before any successor implementation, write a compact
  source-visible mechanism contract and run a passive exposure/cost screen
  on a newly named exploratory cohort, with a simple matched action and
  prior-art boundary. Two leads are prior accepted-ACK quality and a charged
  first-hop receipt. Do not promote either without cross-seed predictive or
  branch/cost support; old 430xx q diagnostics and three-seed overhearing
  evidence are not independent validation. Reserve new untouched
  development/holdout IDs only after a candidate passes this screen.

## 2026-10-05 Successor First-Hop Receipt Feasibility Screen

- [complete] Re-read current worktree, recovery files, relevant skills,
  first-hop and ACK diagnostics, code-level SR/DHR/DBR decision rules, and
  current ICC claims. The preceding goal turn was a status clarification,
  not research progress. The current DBR remains scientific NO-GO; no
  44xxx seed, paper/PDF, VERSION, GitHub or EDAS action occurred.
- [complete] Independent signal/prior-art screens found no already validated
  full successor. Old first-hop witness data have 86 R starts over only
  three seeds, including eight multihop intended-first-hop misses; source
  ACK quality and alternate reverse ACK path gates were negative. DSR,
  ARQ and alternate routing remain close prior art.
- [design in review] Added
  `docs/research/meshecho_first_hop_receipt_screen_design.md`: passive
  fixed-2-s DHR first-hop decode/receipt-airtime screen, with 45000
  mechanical smoke and 45001--45020 prospective exploration, explicit
  17-byte/0.051456-s nominal receipt and predeclared exposure/cost stop
  rules. These seeds are **not authorized yet**. A new diagnostic and public
  tests are under independent implementation; no real 45xxx seed has run.
  Passing this passive gate would authorize only a new protocol hypothesis,
  not an ICC claim; a receipt-conditioned early F is itself a simple control.
- [design audit incorporated] An independent review found that nominal
  early-F deadline fit could count a busy source or a flow whose DHR state
  was dropped at capacity. It also flagged direct-route coverage, already-
  delivered/unACKed residuals, the 630-s receive censoring edge, and the
  need for receipt-free controls. The design now requires stock radio-idle,
  active-flow and residual-source-ACK opportunity; reports delivered and
  direct strata plus an all-scheduled-flow gain ceiling; preserves censored
  TX rows; and requires both same-wire and receipt-free controls. This
  remains an optimistic screen, not a candidate efficacy result.
- [NO-GO for alternate full core] A separate read-only review of
  destination-local quiet-window ACK timing found real timer exposure but
  no new source-visible recovery information: a min-1-s/quiet-0.5-s/max-
  3-s hypothesis could change timing for many old FLOOD receipts, yet the
  fixed-2-s control is already strong and residual failures are mainly
  reverse-ACK reception, not deadline-late ACK starts. This is at most a
  feedback component with prior-art-adjacent waiting, not a complete core
  rewrite. Do not code or promote it from the inspected 38xxx artifacts.
- [next] Independently review the design and diagnostic, freeze all input
  hashes, then allow exactly one 45000 mechanical smoke if parity/strict
  replay can be guaranteed. Audit its artifacts before opening 45001--45020.
  If the passive gate fails, reject the receipt branch without behavior code
  and revisit other device-observable mechanisms. Keep all named holdouts
  unopened until a distinct complete algorithm and controls are frozen.
- [error] The planning recovery command `python .../session-catchup.py`
  failed because `python` is absent; `python3` succeeded. A guessed
  `meshecho_first_hop_witness_diagnostic_design.md` path was absent; file
  discovery located the actual witness tool and related research notes. A
  guessed 43xxx `.runs.csv` path was also absent; the saved run archive is
  `.runs.jsonl`. No source data were changed by either lookup error.

## 2026-10-05 Receipt Diagnostic Implementation Checkpoint

- [complete] Implemented the passive first-hop receipt diagnostic and a
  generic-runner guard for reserved 45000/45001--45020 seeds. The staged
  diagnostic alone may pass authorization; generic `run_one_sr` calls fail
  before topology generation. Fixture tests use only unreserved seed 73.
- [complete] Independent audit found and the implementation closed a missing
  reverse join: every actual unmarked source-origin initial R DATA start must
  have exactly one R decision event. The archive also rejects rehashed false
  passive-analysis labels. The physical timing bound includes the fixed 2-s
  FLOOD ACK hold and handles a competing physical TX at the exact trigger.
- [verified] Focused receipt tests: 19 passed. Full repository regression:
  903 passed, one skipped; Python compilation and `git diff --check` passed.
  No 45xxx seed was run, so there is no exposure result or selected successor
  algorithm. The DBR scientific NO-GO and paper/PDF/VERSION/GitHub/EDAS
  freeze remain in force.
- [next] Independently freeze/audit diagnostic inputs and artifact contract
  before considering exactly one 45000 mechanical smoke. Its strict-replay
  audit is a separate gate before any 45001--45020 exploration. Even a
  positive passive screen only licenses a distinct protocol hypothesis,
  matched simple controls, and fresh development/holdout evidence.

## 2026-10-05 Receipt Stage Audit NO-GO

- [verified] Fresh focused tests passed 25/25; current `VERSION` is 2.1.26
  and there are no 45xxx receipt artifacts. The seven diagnostic input
  hashes were computed but are not yet a pre-exposure freeze.
- [P1] Independent read-only audit found that importing the private runner
  token can bypass stage order at the generic SR entry and directly in the
  diagnostic. The existing smoke route also has no prior frozen-input
  permit. Therefore 45000 and 45001--45020 remain closed.
- [in_progress] Add and test exact-scope stage authorization before topology
  generation, with the explored cohort requiring a checksum-matched,
  strictly replayed smoke predecessor. Pass this stage through every stock,
  observed and replay capture; persist its provenance and independently
  re-audit before a single 45000 mechanical run.
- [science boundary] A separate mechanism review found no qualified full
  successor even if the passive receipt screen passes. First-hop receipt
  plus conditional early F is a simple control, while status queries and
  backup routes have close prior art. Use the screen only to decide whether
  its component has enough physical opportunity and cost headroom to merit
  a distinct later joint state-machine hypothesis.
- [paper baseline audit] Retain explicit "protocol-inspired" labels for the
  existing Meshtastic-like/MeshCore-like arms. Before any new headline
  comparison, include trace-matched Meshtastic next-hop learning,
  MeshCore DATA-first discovery/retry, reverse-ACK/report-route and node-role
  sensitivity arms. The recurring-pair and source-ACK claims are especially
  sensitive to these omissions; do not infer firmware-level dominance.
- [error] A three-file planning-note patch failed because its expected
  `findings.md` line wrapping did not match the worktree. No part of that
  patch was applied; the actual tails were read before this narrower edit.

## 2026-10-05 Receipt Stage Gate Verification

- [complete] Exact-scope frozen-input authorization is required for 45xxx
  smoke/exploration at the generic SR entry, diagnostic entry, and staged
  report. Exploration checks a checksum-matched smoke predecessor with
  strict replay before topology. Authorization bytes/hash are saved and
  verified with the report; the CLI requires `--stage-authorization`.
- [verified] Focused receipt tests passed 36/36. The full repository suite
  passed 914 with one skipped in 139.45 s; Python compilation and
  `git diff --check` passed. No 45xxx seed has been simulated, and no permit
  or receipt result artifact exists yet.
- [boundary] A holder of the valid permit and internal Python capability can
  call a low-level runner without the formal CLI's archival workflow. These
  are trusted in-process APIs, not a sandbox/security boundary. The intended
  one-time smoke must use the CLI, save all artifacts, and pass independent
  strict-replay audit; do not describe the permit as tamper-proof provenance.
- [next] Wait for final independent code audit. If it finds no gate-affecting
  P0/P1, change the design's status to frozen, compute final input hashes,
  record them before data, write the exact smoke permit, and run exactly one
  45000 mechanical smoke via the CLI.

## Frozen Before Receipt Smoke 45000 (2026-10-05)

- [GO, bounded] Independent post-fix audit found no P0/P1 in the normal
  stage-authorized CLI path. This freezes only one mechanical 45000 smoke,
  not the 45001--45020 exploration or a new protocol algorithm. The
  `recurring_fading` case SHA-256 is
  `b3cfb113aded1b1487cf2a5426225cb1188143384a6fe90b770b855e5273b491`.
- [source freeze] Eight permit inputs were hashed after the design status
  was updated and before any 45xxx simulation:

| Input | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `3c4e3e4ad878083ae28ea48079363948aba87b5f050817ac191bac819fb4f74e` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `acac07c6fa4bb441a97dbb046111b3429fbe5c8693a291df897e36f2093ad1e8` |
| `tools/diagnose_delayed_ack_rx.py` | `7493ee072697845673ee66fbe7a2c537f247e1ac1f43733043d094906d16e4c1` |
| `tools/diagnose_first_hop_receipt_screen.py` | `d49da176680aeed4590a50e630ded6bb893c87b2b0856785ec36007d46f2669e` |
| `tests/test_first_hop_receipt_screen.py` | `5bb7787dcef753fc7e0b84553721755bea3a7b3881a226f54ca1ad4054bbf764` |
| `tests/test_receipt_seed_guard.py` | `613a11545833366d93b0760539eb864b69a4e5e73d387eb3304aede3b62518ed` |
| `docs/research/meshecho_first_hop_receipt_screen_design.md` | `3d5744130bf12275ea8ce2e5b9b1928cf7ad4f2ffd4ce35f07fc474182b6034b` |

- [permit] Exact-scope smoke authorization is
  `docs/research/meshecho_first_hop_receipt_smoke.authorization.json`;
  its pre-run SHA-256 is
  `403e08a6afa3ac6c73db5ff1c50971bfa19a9ae36e2d1d81b7fd3e4e55308aae`.
  it binds the above hashes, the case hash, the fixed 30-s deadline,
  protocol and sole seed 45000, with no predecessor. The selected fresh
  output prefix is
  `results/meshecho_first_hop_receipt_smoke_seed45000_20261005`.

## 2026-10-05 Smoke CLI Pre-Topology Failure

- [error, no seed exposure] The authorized direct-script command failed
  before `generate_nodes` and produced no artifact. During stock capture,
  `RecordingSimulator` was patched to a factory function. The generic
  runner then imported the diagnostic by its canonical package name while
  the executing script was a separate `__main__` module, so its class
  definition tried to subclass that function and raised `TypeError`.
- [red/green] A subprocess regression reproduced the exact import failure
  while replacing topology generation with an error guard. The script
  entry now calls the canonical module's `main()`, so the same regression
  reaches the topology guard and passes without simulating 45000.
- [invalidated] The original smoke permit and source table above remain as
  historical pre-attempt evidence, but the edited diagnostic and test hashes
  make that permit unusable. Do not reuse or overwrite it. Complete focused
  and full tests plus independent entrypoint audit, then record a new
  freeze and create a distinct v2 permit before any 45000 retry.

## Receipt Smoke 45000 V2 Freeze (2026-10-05)

- [GO, bounded] The canonical-entry focused suite passed 37/37 and the full
  repository suite passed 915 with one skipped. Python compilation and
  `git diff --check` passed. Independent read-only audit found no P0/P1
  stage or entrypoint defect. The original permit remains invalid history.
- [case] The independently recomputed `recurring_fading` case SHA-256 is
  `b3cfb113aded1b1487cf2a5426225cb1188143384a6fe90b770b855e5273b491`.
  The frozen application deadline is 30 s, protocol is
  `meshecho-dhr-flood-ack-delay`, and the sole authorized seed is 45000.
- [source freeze] Recomputed after regression and before any receipt seed run:

| Input | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `3c4e3e4ad878083ae28ea48079363948aba87b5f050817ac191bac819fb4f74e` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `acac07c6fa4bb441a97dbb046111b3429fbe5c8693a291df897e36f2093ad1e8` |
| `tools/diagnose_delayed_ack_rx.py` | `7493ee072697845673ee66fbe7a2c537f247e1ac1f43733043d094906d16e4c1` |
| `tools/diagnose_first_hop_receipt_screen.py` | `db7e19d888d934501f5246a2337ecc50d457557b000785aaf3862e32d02a623e` |
| `tests/test_first_hop_receipt_screen.py` | `5a9903928db0bcb49e0d5b005b2c9caa48f9c92b3f57a834a12a977100e7ea0c` |
| `tests/test_receipt_seed_guard.py` | `613a11545833366d93b0760539eb864b69a4e5e73d387eb3304aede3b62518ed` |
| `docs/research/meshecho_first_hop_receipt_screen_design.md` | `3d5744130bf12275ea8ce2e5b9b1928cf7ad4f2ffd4ce35f07fc474182b6034b` |

- [permit/prefix] Issue a distinct exact-scope permit at
  `docs/research/meshecho_first_hop_receipt_smoke_v2.authorization.json`.
  Its pre-run SHA-256 is
  `6e1a32b050fd5dce3c89b75b4493b982fa747e108f38184dec70f34ba3925d3b`;
  `_validate_stage` accepted its exact scope before topology.
  Its selected fresh output prefix is
  `results/meshecho_first_hop_receipt_smoke_seed45000_v2_20261005`.
  No matching result artifact existed before the permit. A successful
  mechanical smoke must be archived and independently strict-replayed before
  any 45001--45020 exploration; this GO does not select a new algorithm.
- [audit command error] The first manual `shasum -c` invocation used the
  repository root, while the checksum line names the manifest relative to
  `results/`; it reported a missing file without inspecting the digest.
  Re-run from `results/` and retain the exact command context.

## Receipt Smoke Audit and Exploration Freeze (2026-10-05)

- [smoke complete] The formally authorized v2 seed-45000 CLI completed and
  archived all eight data artifacts plus permit, manifest and sidecar. The
  manifest SHA-256 is
  `0df22ee4f7f411c524bc8d5048cf5d1c9a0dffea01a90dd858a99590ff98bba5`.
  Running the sidecar check from `results/` succeeded. Independent audit
  verified every artifact digest, archived permit bytes, current eight
  source hashes and case hash, stock parity, RNG states, and exact strict
  replay. It found no archive/row discrepancy.
- [science boundary] This is one mechanical seed, not a population gate:
  3 multihop initial-R first-hop failures without guard ACK all became
  source-ACKed by the original deadline under stock fixed-F. Its gate-2
  residual count is 0 and nominal receipt lower-bound cost is 2.125% of
  complete-network TX airtime. No new algorithm follows from this row.
- [GO, exploration only] Independent audit permits exactly the frozen
  45001--45020 passive exploratory cohort, conditioned on a fresh permit
  bound to the above smoke manifest digest and the unchanged eight source
  hashes/case/protocol/deadline. Use output prefix
  `results/meshecho_first_hop_receipt_explore_45001_45020_20261005`,
  confirmed empty before authorization. This is not a paper holdout and
  cannot validate a successor algorithm. Do not open any other reserved
  population or rewrite the ICC method/results based on the screen alone.
- [explore permit] The exact-scope permit is
  `docs/research/meshecho_first_hop_receipt_explore_45001_45020.authorization.json`;
  pre-run SHA-256 is
  `60f834775789751a7913c6b77e9147e6182b89168c25ea45be9d379246df135b`.
  `_validate_stage` accepted it and strictly replayed its predecessor
  before any exploratory topology was generated.

## Receipt Exploration Capture Failure (2026-10-05)

- [error, no archive] The formal exploration CLI failed during seed 45001
  stock capture with `AssertionError: SR runner did not construct exactly one
  simulator`. No exploration result-prefix files were written and 45002--45020
  were not started. The 45001 topology and stock simulation did run once,
  so this attempted exposure must remain disclosed, although no outcome row
  was saved or inspected. Do not silently treat the later retry as a first
  physical execution.
- [root cause] During the outer `capture_run`, generic `run_one_sr` strictly
  replays the smoke predecessor. The nested smoke `run_diagnostic` resolves
  `sr.RecordingSimulator` while it is temporarily patched to the outer
  capture factory. Its inner stock simulator is therefore appended to the
  outer captured list; the actual 45001 simulator makes two and trips the
  one-simulator assertion. This is a capture-composition error, not an
  efficacy result. Add a nonreserved-seed red regression for nested replay,
  then fix only the stock simulator identity; re-run focused/full tests,
  freeze new source hashes, re-smoke and re-audit before a new exploration
  permit. All current receipt permits/manifests become historical evidence
  after source edits and must not be overwritten.

## Receipt Smoke 45000 V3 Freeze (2026-10-05)

- [GO, bounded] The nonreserved nested-replay regression failed before the
  stable-stock-class fix and passed after it. Focused receipt tests passed
  38/38; the full repository suite passed 916 with one skipped in 151.66 s.
  Python compilation and `git diff --check` passed. Independent post-fix
  audit found no P0/P1. The prior v2 smoke and exploration permits are
  historical only; do not reuse or overwrite them.
- [case/scope] The independently recomputed case SHA-256 remains
  `b3cfb113aded1b1487cf2a5426225cb1188143384a6fe90b770b855e5273b491`.
  The sole v3 smoke seed is 45000 on `recurring_fading` with protocol
  `meshecho-dhr-flood-ack-delay` and the original 30-s deadline.
- [source freeze] Eight inputs after regression and before v3 smoke:

| Input | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `3c4e3e4ad878083ae28ea48079363948aba87b5f050817ac191bac819fb4f74e` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `acac07c6fa4bb441a97dbb046111b3429fbe5c8693a291df897e36f2093ad1e8` |
| `tools/diagnose_delayed_ack_rx.py` | `7493ee072697845673ee66fbe7a2c537f247e1ac1f43733043d094906d16e4c1` |
| `tools/diagnose_first_hop_receipt_screen.py` | `66dddf7747dbbef477797e9317d707f8d13f40d96bf66b318811d6cceac269b7` |
| `tests/test_first_hop_receipt_screen.py` | `7b793a00390d95cbad410b60dc46964111ea733f873ca67e058e0d6431d3c003` |
| `tests/test_receipt_seed_guard.py` | `613a11545833366d93b0760539eb864b69a4e5e73d387eb3304aede3b62518ed` |
| `docs/research/meshecho_first_hop_receipt_screen_design.md` | `3d5744130bf12275ea8ce2e5b9b1928cf7ad4f2ffd4ce35f07fc474182b6034b` |

- [permit/prefix] Create
  `docs/research/meshecho_first_hop_receipt_smoke_v3.authorization.json`
  for this exact scope only. Pre-run SHA-256 is
  `de76ff1bec60de8b716f5079aeed20b198799c93769b69ada12d50c4dcedbe65`;
  `_validate_stage` accepted it before topology. Selected fresh output prefix is
  `results/meshecho_first_hop_receipt_smoke_seed45000_v3_20261005`,
  confirmed empty before the permit. The v3 smoke must pass strict replay
  and independent artifact audit before any renewed exploration permit.
- [smoke run, audit pending] The formal v3 CLI completed. Manifest SHA-256 is
  `7290acd265a1cf9ded4850eac1fc13d6351fa93b1f694e79240f0b5385b73631`;
  its sidecar check passed. V2/v3 summary values and digests for all run-data
  artifacts (excluding authorization and summary metadata) are identical.
  Independent strict-replay/archive review remains the exploration gate.

## Receipt Exploration V2 Authorization (2026-10-05)

- [GO, bounded] Independent v3 smoke audit verified sidecar, every artifact,
  archived permit, all eight current source hashes, case/deadline/seed,
  stock parity and strict replay. The six physical evidence files are
  byte-identical to the v2 smoke. This opens only the prespecified passive
  45001--45020 exploratory cohort, not a new protocol or ICC result.
- [retry disclosure] The previous cohort command completed one seed-45001
  stock simulation before a capture error; it yielded no result artifact or
  inspected outcome. Keep its aborted-attempt record. The new cohort is a
  deterministic retry of the same prespecified seeds after a provenance
  fix, not a fresh untouched validation set. Do not call 45001 unexposed.
- [scope] Bind a new permit at
  `docs/research/meshecho_first_hop_receipt_explore_45001_45020_v2.authorization.json`
  (pre-run SHA-256
  `ded7b8cd5b1d6fe2f39879fe87330be2cfa0593335f03d57b8656a0981328b91`;
  `_validate_stage` accepted it and strictly replayed the predecessor)
  to v3 smoke manifest SHA-256
  `7290acd265a1cf9ded4850eac1fc13d6351fa93b1f694e79240f0b5385b73631`,
  the unchanged eight v3 source hashes, `recurring_fading` case, protocol,
  deadline 30 s, and exactly seeds 45001--45020. New output prefix
  `results/meshecho_first_hop_receipt_explore_45001_45020_v2_20261005`
  was confirmed empty before permit creation. All other reserved windows
  and paper/VERSION/publication actions remain closed.
- [minor edit error] An in-progress `progress.md` checkpoint patch initially
  missed the file's actual line wrapping and applied nothing. The tail was
  read and the exact-context patch succeeded. It did not alter any frozen
  source input or running simulator state.

## First-Hop Receipt Screen NO-GO (2026-10-05)

- [complete] The repaired, exactly authorized 45001--45020 passive CLI
  completed and returned after strict replay. Manifest SHA-256 is
  `7c12f8b00e08cba4c2f96a9c22d76aaf129e0ece93474260ab3c2d31e1142109`.
  Independent no-rerun audit verified its sidecar and eight artifact hashes,
  archived permit, v3 smoke predecessor, source/case/deadline/20-seed scope,
  per-seed stock parity and replay flags, 783 flow/612 initial-R/12346 TX
  joins, and the gate arithmetic. Detailed result and disclosure of the
  aborted prior 45001 stock run are in
  `docs/research/meshecho_first_hop_receipt_explore_results.md`.
- [decision] Frozen gates 1--3 passed (57 first-hop failures across 19 seeds,
  ten residual opportunities across seven seeds, 2.3604% nominal receipt
  airtime), but gate 4 failed: optimistic equal-seed all-flow source-ACK gain
  ceiling 0.0128713 versus required 0.02. The ten residual flows were all
  destination-delivered, destination-delivery ceiling is zero, and early-only
  deadline admissions are zero. The necessary gate is false. No receipt
  behavior code, first-hop-cache/suffix-rescue (RCR), reserved holdout,
  manuscript/PDF, VERSION, GitHub or EDAS progression is licensed.
- [next research question] Focus on the dominant delivered-but-unACKed
  reverse-confirmation loss using only evidence available to an actual
  sender/ACK relay before its action. Screen physical last-hop failures,
  deadline slack, and charged local feedback/retry opportunity against the
  fixed-2-s ACK and same-time/same-byte repeat controls. Do not claim a new
  core from ACK waiting, ACK-of-ACK, or a status query alone. A separate
  read-only review rejected per-pair three-arm Bayesian/bandit F/R/D here:
  80 pairs have only 6--13 flows each and just one pair sees two of every
  initial F/R/D action; the old policy's action assignment is confounded.
- [AFS boundary] A read-only AFS integration audit found no qualified full
  source/relay core: AFS saved 19.53% paired airtime but failed its frozen
  source-ACK noninferiority CI, and the drafted DRC+AFS source rule had zero
  reserve-caused first-F branches in its earlier exposure screen. Of 9,728
  AFS cancellations, 6,979 occurred at the same timestamp as source ACK
  acceptance, so a later source DONE signal cannot inherit them as timely
  opportunities. A source-visible/staged-cancel branch needs its own
  charged timing screen before any implementation; stacking AFS onto old
  F/R/D is not this goal's core rewrite.
- [lookup error] A `zsh` glob for a guessed `docs/research/meshecho_sr*`
  path failed with `no matches found`; `rg --files` confirmed no such
  research note exists. No file or source data changed from the lookup.

## 2026-10-05 Destination-Certified Backup Continuation

- [progress classification] The preceding question-answer turn independently
  rechecked the 42xxx 131/125/53/47 exposure join and found a P1 flaw in
  the candidate's ACK-benefit gate. It changed the next action; it did not
  implement or validate a new core.
- [complete] Corrected the unopened 46xxx passive screen before any seed
  run. Stock flows already source-ACKed by fixed F cannot count toward an
  ACK gain ceiling; a distinct cost-substitution potential now charges the
  minimum relay/ACK/field/redundant-TX airtime. The candidate is cost-first:
  physical exposure plus >=0.05 optimistic whole-network airtime potential
  is required; report ACK headroom without switching endpoints. This is a
  prospective exploratory prototype gate, not a treatment effect or ICC rule.
- [old-data screen] In 42xxx stock rows, 131 initial direct R flows include
  only eight deadline-unACKed. All 49 ACKed among 57 direct-R/F-recovery
  flows incurred 116.945152 s marked-F TX airtime out of 999.575552 s
  complete network airtime. The 11.7% gross superset target ignores backup
  availability and extra costs; it motivated cost focus but validates nothing.
- [prior-art boundary] IOMC (Sensors 2023, DOI 10.3390/s23083874) already
  suppresses LoRa overhearing-relay retransmissions on a destination ACK.
  ACK-gated forwarding by itself is not the novel core; include an IOMC-like
  control with matched information and cost if this candidate reaches trial.
- [in progress] Add a parity-preserving passive observer with test-first
  slices, then independently audit its contract and frozen inputs. Do not
  run 46000 or 46001--46020 before that audit. The earlier 42xxx/45xxx
  archives lack the current R off-path receive/ACK-overhear records needed
  to decide this candidate. Current paper/PDF/VERSION/remote remain old.
- [observer slice complete] New `tools/diagnose_destination_certified_backup.py`
  and `tests/test_destination_certified_backup.py` implement an observer-only
  first vertical slice. Independent focused run: 10 tests passed; Python
  compilation and `git diff --check` passed. Seed-73 parity/replay covers
  complete stock outputs and both RNG streams; boundary tests cover source
  generation, physically failed direct DATA, ACK overhear, window capacity,
  late alternatives, duplicate R, and cutoff censoring. Reserved 46xxx is
  rejected by this diagnostic and has not run. This is not yet a complete
  gate runner or protocol algorithm.
- [next observer work] Add PRR/deadline/field-byte and redundant-TX cost
  calculations, an exact-scope staged CLI with manifests, independent audit,
  then one 46000 smoke. Only after smoke parity and artifact audit may the
  passive 46001--46020 exploratory screen run. Neither stage is an ICC
  causal or holdout result.
- [next] If the passive gate passes, freeze an implementable packet/state
  contract, test the new protocol against same-information simple controls,
  run fresh development and untouched holdout, then rewrite the ICC LaTeX
  from verified results and render/inspect the PDF. If it fails, record
  NO-GO and select a different core without claiming a new ICC result.
- [errors] Two attempted patches for the candidate note failed because the
  hunk/context did not match; a corrected exact-context patch succeeded.
  Guessed `meshecho_dbr_design.md` and `meshecho_dbr_dev_results.md` paths
  did not exist; `rg --files` located the actual DBR draft. An initial jq
  membership filter accidentally used `index(.)` in the array context and
  counted two D-to-R fallbacks as initial R; binding the flow key explicitly
  recovered the correct 131. No protected seed changed from these errors.

## 2026-10-05 Backup Screen Continuation

- [complete] Classified the preceding explanation-only turn as no progress;
  resumed from the existing checkpoint and ran session catch-up.
- [complete] Before opening 46xxx, clarified the cost gate: complete stock F
  recovery airtime is an optimistic substitution only if nominal candidate
  ACK completion precedes the R-start + 15-s F guard. The 30-s application
  deadline alone does not establish cancellation. Primary relay timer is
  frozen at 2 s, with 0.5 s sensitivity only.
- [complete] The parity-preserving observer now computes charged cost and
  nominal slack fields; the exact-scope stage runner writes a hashed archive
  and strictly replays its smoke predecessor. Independent read-only review
  found no P0/P1 defects. A resumed adjacent suite passed 241 tests. No 46xxx
  seed has run and this does not establish a new protocol effect.
- [complete] Full repository regression: 958 passed, one skipped in 160.79 s;
  Python compilation and `git diff --check` passed. Independent read-only
  audit matched all ten runner input hashes and found no existing 46xxx
  permit/output. Frozen case hash is
  `b3cfb113aded1b1487cf2a5426225cb1188143384a6fe90b770b855e5273b491`.
- [frozen-before-46000] The ten runner inputs, in `SOURCE_FILES` order:

| Input | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `3c4e3e4ad878083ae28ea48079363948aba87b5f050817ac191bac819fb4f74e` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `af629d801c6b7df1932d18a1dcedd506de3bcbc926d3c45fe09dc6e98b90934d` |
| `tools/diagnose_delayed_ack_rx.py` | `7493ee072697845673ee66fbe7a2c537f247e1ac1f43733043d094906d16e4c1` |
| `tools/diagnose_destination_certified_backup.py` | `8f5fe6dcb4e6df88ae5de8de482aa3ee5e26a9078484cf9db8e24346c390a42e` |
| `tools/run_destination_backup_screen.py` | `57d7cd33d7fdef03f90e0e496f79c010bf5f6acceed3f2a1222f6cf0b35eb64c` |
| `tests/test_destination_certified_backup.py` | `e1670c264b60cc634f86a79df9b56203c94441f303f206815e22213091cac84a` |
| `tests/test_destination_backup_screen_runner.py` | `67ebaf416cbeb842b02a74e245a8054451cf2de627395d2b51bffbe1a7dff865` |
| `tests/test_destination_backup_seed_guard.py` | `61bf945532ec9ce344c75fab105d7c58c6a8d293d235b4f79c32cd0c44d9dc21` |
| `docs/research/meshecho_destination_certified_backup_screen.md` | `dbc73dbab2b434476ec130f044987501fadc7a665fb466ecb4d3b3afc43906fb` |

- [in progress] Smoke-only permit:
  `docs/research/meshecho_destination_backup_smoke_46000.authorization.json`.
  Pre-run permit SHA-256:
  `6dcd78725d1b183399d684a9f6c9f370917ed97511a3c09808c1701839273796`.
  Planned fresh prefix:
  `results/meshecho_destination_backup_smoke_seed46000_20261005`.
  The direct pre-topology stage validation passed; an independent read-only
  audit returned GO after matching all ten hashes and confirming no target
  output exists. Capture exactly 46000 once, then independently verify
  archive and strict replay before exploration.
- [NO-GO first attempt] The formal direct-script 46000 smoke failed before
  topology generation or artifact writing: `run_one_sr` rejected its backup
  authorization identity. Direct execution loaded the runner as `__main__`,
  while the SR guard imported `tools.run_destination_backup_screen`, yielding
  two distinct `_RUNNER_AUTHORIZATION` objects. The earlier permit is now
  invalid because a regression test and entry repair change frozen inputs;
  preserve it as audit history and use a new v2 permit/prefix only after red,
  green, full regression, and new source freeze. The first attempt opened no
  reserved simulation outcome.
- [complete] The direct-script red regression reproduced the token mismatch;
  routing `__main__` through the canonical imported module made it green.
  Adjacent tests: 242 passed. Full suite: 959 passed, one skipped in
  160.42 s; compilation and whitespace checks passed. Independent read-only
  review confirmed the first prefix has no files and the guard still checks
  scope before topology. The v1 permit remains historical and invalid.
- [frozen-before-46000-v2] The ten-input table above is unchanged except
  exactly these two independently rehashed entries; the other eight were
  rechecked byte-identical:

| Input | SHA-256 |
| --- | --- |
| `tools/run_destination_backup_screen.py` | `ff0dd326bc353f2bc6ba7219e8d78d74b08029026192fa4e542a66f617294eca` |
| `tests/test_destination_backup_screen_runner.py` | `b6265f5143e2653ff22f8ea69b7577cfef59859269b30e22c2005b57a06a3db6` |

- [in progress] New smoke-only permit:
  `docs/research/meshecho_destination_backup_smoke_46000_v2.authorization.json`;
  pre-run SHA-256
  `abaeed71ddf0619fb3f6451df12c61be234f5716093276fee16700faf940385a`;
  planned fresh output prefix:
  `results/meshecho_destination_backup_smoke_seed46000_v2_20261005`.
  Local stage validation passed. A separate read-only audit independently
  matched all ten hashes and confirmed all twelve target files absent;
  GO for one new mechanical smoke.
- [smoke archive GO] The formal v2 direct CLI captured
  exactly seed 46000 and wrote all twelve expected artifacts under the v2
  prefix. Manifest SHA-256 is
  `2481924958228b44686f1e5c2571175cdb94c15137a8748a8a04fdabe5b24b31`.
  The saved summary has 40 scheduled unicasts, four nominated direct-R
  flows, three physically exposed failed primaries, and zero stock-unACKed
  proxy headroom. Its 11.1777% optimistic whole-network airtime substitution
  is a one-seed opportunity bound, not a protocol effect or population gate.
  Independent audit passed official strict replay, all artifact/source
  hashes, archived permit, stock flow/action/TX/RNG parity, four row joins,
  and the independent airtime sum: 6.462976 s stock F potential minus
  0.637184 s minimum new cost = 5.825792 s margin over 52.119808 s
  whole-network airtime. GO only as an exploration predecessor, not an
  algorithm or ICC result.
- [in progress] Created an exact 46001--46020 passive exploration permit at
  `docs/research/meshecho_destination_backup_explore_46001_46020.authorization.json`,
  pre-run SHA-256
  `a4c046bd8bec1f7a6753ce539ff3682138397eb4723b2c92667655411d266ad9`,
  bound to v2 smoke manifest SHA-256
  `2481924958228b44686f1e5c2571175cdb94c15137a8748a8a04fdabe5b24b31`
  and the unchanged v2 ten-input freeze. Planned fresh prefix:
  `results/meshecho_destination_backup_explore_46001_46020_20261005`.
  Local stage validation passed, including strict smoke replay; output path
  is empty. Independently pre-audit permit and output path before one formal
  cohort run.
- [exploration complete, independent audit pending] A separate read-only
  pre-run audit returned GO for the exact frozen scope. The formal direct
  CLI completed once and wrote all twelve artifacts. Manifest SHA-256:
  `c51e55cbac2c8a5ae00de23001f008b3402360c3357430ff212d0f213ed9a385`.
  Local no-rerun manifest validation passed (20 seeds, ten archived artifact
  classes). Its saved primary 2-s screen reports 872 scheduled unicasts,
  130 nominated direct R flows, 36 exposed failed primaries across 17
  seeds, 36 proxy/deadline feasible, and equal-seed optimistic net whole-
  network airtime fraction 0.0552837. Both necessary gates are marked true,
  but these are passive optimistic screen results, not a causal algorithm
  effect, superiority, novelty, or ICC evidence. Independent row/cost
  arithmetic audit must pass before protocol implementation decisions.
- [GO-to-prototype, NO-GO-to-paper] Independent archive audit passed all
  frozen hashes, stock/observer parity evidence, 130 unique nomination joins,
  13,338 complete TXs and the charged gate arithmetic. It independently
  recomputed 36 exposed flows in 17 seeds, 30 creditable F rescues,
  61.564928 s optimistic net margin, and 0.055283726 equal-seed fraction.
  The gate clears 5% by just 0.528 points. Exploratory archive flags/digests
  were checked but the 20 seeds were not independently re-simulated. Detailed
  provenance and caveats are in
  `docs/research/meshecho_destination_certified_backup_explore_results.md`.
- [next] Freeze complete packet/state/timer and acceptance semantics for an
  independent destination-certified conditional-backup protocol; use one
  red/green public-behavior test per vertical slice. Do not run the new
  protocol on 46xxx, write its numerical ICC claims, update VERSION or
  publish until fresh same-budget causal development and untouched holdout.
- [contract drafted] `docs/research/meshecho_dcb_protocol_contract.md`
  fixes conservative extension bytes (3/7/5 plus marker), a 120-s source
  age at R enqueue, a 2-s local relay timer with busy-radio skip, an echoed
  F epoch on marked backup DATA/ACK, ACK-only source certification, and
  no future route commit from a backup ACK. Independent contract review and
  public red tests are next. The first frozen source tarball included hidden
  AppleDouble/PAX members and is invalid as an exact-member snapshot. The
  corrected `docs/research/meshecho_destination_backup_frozen_v2_20261005.tar.gz`
  has exactly twelve regular members, independently byte-checked against
  both manifests, SHA-256
  `143245144414d66c547ca9e285c475be1e5ef16d6d39ac31460bb76f193568cd`.
- [pending] If smoke and artifact/replay audits pass, authorize exactly
  46001--46020 once; apply the prespecified exposure and cost gates. A pass
  permits protocol implementation and matched causal development, not an
  ICC claim. A failure is NO-GO for this candidate, not for the full rewrite.
- [complete] Added a generic SR-runner guard for 46000/46001--46020 before
  topology generation. Nine focused tests pass: unpermitted direct calls,
  float alias, wrong protocol, imported token without a permit, and an
  invalid permit all fail closed. Authorized stage validation remains to be
  integration-tested after the runner agent finishes.
- [error resolved] The first green run accessed the still-in-progress
  runner's missing token attribute before noticing an absent permit. The
  guard now checks the missing permit and scope first; the runner has since
  exposed the agreed token and validation signature. No reserved seed ran.
- [verification] Neighbor tests: 208 passed (`test_destination_backup_seed_guard`,
  `test_receipt_seed_guard`, `test_sr_experiment`); Python compilation and
  whitespace check passed. Full observer/runner integration and archival
  checks remain pending, so no permit or 46xxx execution yet.

## 2026-10-05 Rewritten-Core Continuation

- [goal] Keep the full user objective: replace the MeshEcho-SR decision core,
  run fair causal simulations, then substantially revise the ICC manuscript
  only from validated results. Reuse the tested radio/simulator and retain
  old policies as controls; DCB by itself is not the completed rewrite.
- [complete] Corrected the two-hop F recovery-admission bound by a public
  red/green deadline-edge test. Focused 19-test and full 1017-pass/one-skip
  regressions, compilation and whitespace check passed. Global RREQ budget
  remains six hops; no reserved seed was opened.
- [in_progress] Independently specify a device-local source decision rule
  that actually differs from inherited F/R/D and DHR choices. Retain D as
  a tested alternative until a same-byte causal ablation justifies removal.
- [pending] Complete matched comparator contract, independent review and
  source freeze before the single 47000 smoke. Development 47001--47020 and
  untouched holdout 48001--48040 remain closed behind their stage gates.
- [pending] Revise ICC LaTeX, figures and PDF only after the rewritten core
  passes the predeclared evidence gate; do not update VERSION/GitHub/EDAS
  from prototype mechanics or passive opportunity estimates.
- [exploratory pilot, not evidence gate] Run exactly public nonreserved seeds
  49101--49103 once on the unchanged recurring-fading case, comparing the
  current `meshecho-dcb` component with fixed-2-s ACK/fixed-F recovery.
  Inspect all-scheduled-flow deadline ACK/delivery, whole-network TX airtime,
  and actual backup starts. These rows are design diagnostics only: do not
  tune a final gate on them, label them holdout, or put them in ICC results.
- [in_progress] Test an ACK-proven source route-promotion vertical slice in
  a separately named protocol, keeping DCB no-promotion as a same-wire
  control. The candidate contract is
  `docs/research/meshecho_ack_proven_route_promotion_candidate.md`; it
  explicitly remains a component until a new F/R/D source FSM and causal
  advantage are demonstrated. Do not open 47xxx/48xxx for this candidate.
