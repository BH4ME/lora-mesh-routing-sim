# Progress Log

## 2026-10-06 algorithm-boundary continuation

- Read the persisted CPR plan and source boundary after context handoff.
- Read the academic-paper reviewer and PDF workflow instructions because this
  turn evaluates algorithm originality and final manuscript integrity.
- Confirmed the remaining release issue is clean provenance and staging, not a
  need to invent a second algorithm.
- Read-only PDF inspection recommends `build-2_1_27-cpr-final`; no layout or
  author-glyph defect was found.
- Full regression attempt via bare `pytest -q` stopped at collection with
  environment-only `ModuleNotFoundError` errors; `python3 -m pytest` collected
  CPR tests correctly, so the regression is being rerun through that launcher.

## 2026-10-06 final verification continuation

- Re-ran both CPR population audits; development and untouched holdout remain
  valid and passed.
- Earlier checkpoint regression completed: `1181 passed, 1 skipped` in 434.18 s.
- Built `paper/icc2027/build-cpr-balanced-5/icc2027_lora_mesh.pdf` with the
  final ledger wording and two-column reference balancing; PDF metadata reports
  five Letter pages.
- Poppler rendering of all five pages found no clipping, overlap, broken glyph,
  or Chinese author text. The extracted author names are `Zu Gao` and `Zhi
  Quan`.
- Next action is release packaging only: canonical PDF copy, version/metadata
  consistency, final diff checks, and the requested GitHub update.

## 2026-10-06 clean formal rerun complete

- Re-generated formal development and holdout after source commit
  `a013067ebf5d7ba7031d38634f7caf3bfda99dbb`; both population gate reports
  passed and raw manifests bind to that clean revision.
- Full regression through `python3 -m pytest`: `1182 passed, 1 skipped`.
- Final PDF metadata/render/CJK checks, py_compile, and diff checks passed.
- Package staging remains: formal artifacts only, then commit and push.

## 2026-10-06 CPR manuscript and PDF checkpoint

- Re-read the current plan, findings, progress, and CPR handoff after the
  context boundary; no unsynced catch-up state was reported.
- Confirmed the current CPR holdout gate is `passed=true` and the manuscript
  reports the audited values from the holdout bundle.
- Compiled `paper/icc2027/icc2027_lora_mesh.tex` successfully to a five-page
  PDF and rendered all five pages with Poppler. Pages 1--4 are visually clean;
  page 5 has a large right-column gap because the references are not balanced.
- Next action is a minimal bibliography-balancing edit, followed by a fresh
  compile/render audit. No VERSION, canonical PDF, GitHub, or EDAS update has
  been made in this checkpoint.


## 2026-10-06 - CPR Manuscript Migration Continuation

- [complete] Re-read the current v2 task plan, findings, progress log, CPR
  handoff, contracts, source module, and current ICC TeX before editing.
- [verified] CPR development and untouched holdout artifacts remain the
  authoritative evidence; the ICC source/PDF still describes old 2.1.26
  calibrated MeshEcho and therefore cannot be used as the new paper.
- [in_progress] Rebuild paper data products directly from the CPR manifests,
  then replace the ICC method/results/figures with CPR-specific content.
- [pending] Compile, render, inspect all five pages, run regression/audits,
  and only then consider the version metadata update.

## 2026-10-06 - CPR Exploratory Exposure Decision

- [complete] Final exploratory bundle
  `results/meshecho_cpr_exploratory_92020_92029_20261006.manifest.json` passed
  independent audit: 40 paired runs, 160 flows, 698 TXs, 5584 RX attempts,
  97 accepted ACKs, and no incomplete RX/TX joins.
- [NO-GO] Exposure gate failed because `R_REPEAT=0` and `F_RECOVERY=0`; only
  initial-F relay cancellation was exercised. No development cohort, paper
  edit, VERSION change, GitHub push, or EDAS action is authorized from these
  results.
- [in_progress] Draft the next exposure contract using repeated same-pair
  traffic plus frozen fading/collision settings, then run a fresh diagnostic
  only after contract and pre-run identity checks pass.
- [complete] Added and test-locked the `exposure` case profile and froze
  `docs/research/meshecho_cpr_exposure_contract_20261006.md` for seeds
  `92100..92109`; no exposure seed has run yet.
- [complete] Ran and audited exposure seeds `92100..92109`: 40 paired runs,
  1292 flows, 4803 TXs, 96060 RX attempts, 1233 accepted ACKs, zero incomplete
  joins; 16 repeats and 13 recovery FLOOD starts were physically observed.
- [decision] Exposure gates pass, so a fresh confirmatory development cohort
  is justified. This does not authorize holdout or ICC edits yet.
- [in_progress] Freeze and implement stage-aware development/holdout runner
  metadata, then run only development seeds `92200..92219`.
- [complete] Ran development `92200..92219` and wrote manifest plus gate
  report. Independent audit passed all checks: 80 runs, 40 repeats, 26
  recovery FLOOD starts, no incomplete joins, reliability lower bounds above
  `-0.05`, and airtime below both controls.
- [in_progress] Add a hard pre-run check requiring the passed development gate
  report before starting holdout `92300..92319`.
- [complete] Verified the development prerequisite, ran holdout `92300..92319`,
  and audited it with the prerequisite report. Holdout passed: 80 runs, 26
  repeats, 21 recovery FLOOD starts, no incomplete joins, ACK lower bounds
  above `-0.05`, and airtime below both controls.
- [in_progress] Begin the major ICC LaTeX/figure rewrite from holdout-only
  aggregates; preserve the validated artifacts and do not change VERSION or
  publish metadata until the PDF audit passes.

## 2026-10-06 - CPR Controller Vertical Slice 1

- [complete] Added the new `meshecho_cpr.py` source decision module. It is a
  separate successor contract, not a parameter edit to DRC/SR.
- [complete] Added public tests for the strict recovery order: a same-path
  `R_REPEAT` is selected before any FLOOD, and exactly one `F_RECOVERY` is
  eligible only after the repeat has physically started and still fits the
  original deadline.
- [verified] `python3 -m pytest -q tests/test_meshecho_cpr.py` passes (`2
  passed`); `py_compile` and `git diff --check` pass.
- [in_progress] The controller still needs the physical ACK-terminated
  pending-F cancellation slice and simulator integration. No population
  result, paper edit, version bump, GitHub push, or EDAS action is authorized
  by this slice.

## 2026-10-06 - CPR Source And Relay Vertical Slice 2

- [complete] Registered an independent `MeshEchoCPR` protocol identity and a
  matched `meshecho-cpr-nocancel` shadow. CPR is not registered as a DRC mode.
- [complete] Implemented a source-local lifecycle with physical TX-start
  state: initial confirmed-route `R`, one same-path `R_REPEAT` after an
  unACKed initial route attempt, and at most one deadline-gated recovery
  `F_RECOVERY` after the repeat physically starts.
- [complete] Added marker-aware ACK validation for initial, repeat, and
  recovery packets. An ACK is accepted only after the corresponding physical
  packet start and cancels still-queued source requests.
- [complete] Added a bounded CPR relay ledger. A physically decoded matching
  ACK can cancel an uncommitted initial or recovery FLOOD relay; wrong flow,
  endpoint, path, marker, or a committed handle cannot cancel it.
- [verified] CPR pure/controller/DRC focused tests pass (`29 passed`).
- [in_progress] Run broader regression and add a disk-backed CPR smoke/audit
  before any exploratory population experiment.

## 2026-10-06 - CPR Smoke Runner Design

- [decision] CPR evidence will use a separate runner/schema and source hash
  contract. It will pair `meshecho-cpr`, `meshecho-cpr-nocancel`,
  `meshecho-drc-no-rescue`, and `meshecho-drc` on identical topology, pair
  pool, and application trace per seed.
- [pending] Add the runner through a RED test, then implement one fresh
  nonreserved mechanical smoke. The old DRC population artifacts cannot be
  reused as CPR evidence.

## 2026-10-06 - Algorithm Boundary Clarification

- [decision] The active method is not a parameter tweak of the old
  MeshEcho-SR/DHR/DCB selector. `MeshEchoDRC` is a separate source-decision
  core: it decides at the actual physical TX start using ACK-confirmed local
  route state, complete modeled ToA bounds, and the original flow deadline;
  its actions are `R_RESERVED`, `F_INITIAL`, `R_ONLY`, `F_RECOVERY`, or an
  explicit deadline-infeasible no-start.
- [decision] Reusing the tested PHY, channel, collision, forwarding, ACK,
  ToA/energy, and ledger substrate is intentional. Rewriting those layers at
  the same time would confound a protocol comparison and invalidate matched
  controls rather than strengthen the ICC claim.
- [qualification] DRC remains an evidence-backed candidate, not a paper
  claim, until the frozen development/holdout exposure and effect gates pass.
  The exploratory `61001` run had no reserve-caused initial-F branch, so it is
  inconclusive and cannot be relabeled as DRC confirmation.
- [complete] Fixed the population entry point so `tools/run_drc_population.py`
  resolves the repository root before importing the runner when invoked as a
  script. Direct `--help`, `py_compile`, `git diff --check`, and the focused
  DRC population/runner/evidence tests (`14 passed`) are green.
- [stopped-safely] A full development attempt was started once, but was
  interrupted during the large RX-ledger audit after system swap usage reached
  roughly 15/16 GB. The partial `results/meshecho_drc_development_62001_62020_20261006.*`
  files are retained for provenance but are invalid and must not be used as a
  development manifest or paper evidence. No population gate or holdout was
  opened.

## 2026-10-06 - DRC Development Gate Result

- [complete] Replaced the memory-heavy population path with a disk-backed
  stream: `iter_matrix()` yields one seed/arm, `write_artifacts_stream()`
  appends the complete JSONL ledgers, and population results expose lazy
  evidence views. Focused DRC/population/evidence/controller tests: `40
  passed`; `py_compile` and `git diff --check` passed.
- [complete] Ran the frozen development cohort once under the new prefix
  `results/meshecho_drc_development_stream_62001_62020_20261006.*`. The run
  completed with bounded RSS and the independent artifact audit passed.
- [gate-failed] Development gate failed only `airtime_vs_no_rescue`: candidate
  mean TX airtime `36.8304512 s` versus `27.8528640 s` for no-rescue, about
  `32.2%` higher than the fixed `10%` ceiling. ACK lower bounds, destination
  lower bounds, candidate-vs-all-F cost, `689` R_RESERVED starts, `81`
  recovery-F starts, and accepted-ACK provenance all passed.
- [inconclusive] `reserve_fallback_decisions=0`; the reserve-caused initial-F
  branch was not exposed. Holdout remains closed. The development artifacts
  are valid negative evidence for this frozen DRC candidate, not a positive
  DRC result or permission to tune on holdout.

## 2026-10-06 - CPR Successor Continuation

- [verified] The DRC development failure is performance-related, not an
  evidence-ledger defect: 81 recovery-F starts added about 203.9 s aggregate
  FLOOD airtime; the candidate gained 32 ACKs over no-rescue but exceeded the
  +10% cost ceiling by a wide margin.
- [decision] Preserve DRC as a sealed negative baseline. Do not alter its
  contract or reuse `62001..62020` to evaluate a modified guard/recovery rule.
- [in_progress] Start a distinct `MeshEcho-CPR` successor contract. CPR will
  change the recovery state machine and add only physically justified,
  charged terminal-ACK cancellation of uncommitted relay FLOODs. Its source,
  relay, wire and memory rules must be tested independently before a fresh
  exploratory cohort.
- [pending] First implementation action after this checkpoint: add one RED
  public controller test and one RED end-to-end cancellation test; then make
  each GREEN with the smallest vertical slice.

## 2026-10-06 - Active Goal Continuation: DRC Runner And Evidence Closure

- [in_progress] Resumed the user-requested end-to-end objective: rewrite the
  MeshEcho-SR source decision core, run matched simulations, and revise the
  ICC manuscript only from verified artifacts. The current checkout remains
  the dirty `version/v2` worktree; no user changes were reverted.
- [verified] The algorithm boundary is now explicit: `MeshEchoDRC` replaces
  the inherited SR/DHR/DCB source selector, while the tested PHY, channel,
  forwarding, ACK transport, ToA/energy accounting and historical controls
  remain reusable infrastructure.
- [in_progress] Full repository regression is running after the DRC request,
  RX-attempt and ACK-provenance slices. A separate DRC runner and independent
  audit are being developed before any development or holdout cohort.
- [complete] Full repository regression completed after the current evidence
  slices: `1140 passed, 1 skipped` in 611.21 s. This validates existing
  behavior and the focused DRC evidence tests, but does not validate a DRC
  population effect or an ICC claim.
- [complete] Added the independent smoke-only runner
  `tools/run_drc_experiment.py` with five same-wire arms and raw
  runs/flows/actions/requests/TX/RX-attempt/ACK/paired artifacts. The fixed
  seed `91000` mechanical smoke produced 5 runs, 20 scheduled flows, 135
  requests/TX joins, 1,080 RX attempts and 5 accepted ACKs; the independent
  manifest audit passed with zero spillover/incomplete-RX records.
- [in_progress] The smoke proves artifact mechanics only. The independent
  audit still requires event-order, keyed-randomness, ACK field, and finite
  operational-state fixes before a development cohort can be frozen.
- [complete] Added a keyed DRC FLOOD-delay draw using seed/packet/receiver
  context rather than the shared event-order RNG. RED/GREEN coverage now
  verifies identical jitter after unrelated RNG consumption; the DRC-focused
  and runner tests pass (`11 passed` in the combined check).
- [complete] Added explicit simulator event priorities for equal timestamps,
  exact-deadline TX-censor coverage, ACK receive/deadline/post-commit route
  generation fields, and a 128-entry per-node pending-relay cap with eviction
  events. The focused DRC/evidence/runner check now passes (`18 passed`).
- [complete] The fixed mechanical smoke was audited before these source edits;
  its old manifest is intentionally stale after the source hash changed. A
  fresh smoke must be generated before population freezing.
- [complete] Regenerated and independently audited smoke seed `91002` after
  the source changes: 5 arms, 20 scheduled flows, 135 requests, 130 complete
  physical TXs, 1,040 RX attempts, 5 accepted ACKs, zero spillover/incomplete
  RX, and an explicit event-priority manifest.
- [in_progress] Freeze and implement the population-stage wrapper for the
  disjoint `62001..62020` development and `63001..63020` holdout cohorts.
- [blocked-by-evidence-gate] The ICC TeX, `VERSION`, GitHub and EDAS remain
  unchanged until request/start/no-start, RX, ACK and deadline accounting can
  be independently recomputed and a fresh matched development/holdout gate
  passes. Existing exploratory traces are not DRC results.

## 2026-10-06 - DRC Evidence-Closure Checkpoint

- The active user objective remains: rewrite the MeshEcho-SR decision core,
  run fair paired simulations, and substantially revise the ICC manuscript
  only from verified results. This turn resumes from the existing dirty
  `version/v2` worktree; no user changes were reverted.
- The new core is `MeshEchoDRC`, independent of `MeshEchoSR`/`MeshEchoDHR`
  source selection. It reuses the tested PHY/channel/forwarding substrate,
  but does not reuse SR's enqueue-time D/R/F choice, route-age trigger,
  RREQ/RREP branch, token/cooldown, or miss selector.
- Existing focused DRC/controller tests and Python compilation were reported
  green by the prior checkpoint. That is implementation evidence only; the
  DRC runner, full request/RX/ACK audit, development cohort, holdout cohort,
  ICC revision and final PDF remain incomplete.
- Current decision: do not edit the paper, `VERSION`, GitHub or EDAS yet.
  The next authoritative work is evidence closure, starting with a full
  regression and a red/green TX ledger/RX provenance slice.
- The first full regression reached 1139 passed, one skipped and one failure.
  The failure was a stale UGR integration fixture: it supplied a 479-s old
  ACK and a 3-hop discovery-cost budget while expecting D. The production
  utility gate correctly selected F. The fixture was corrected to use fresh
  feedback and a discovery-comparable `max_hops=12`; the targeted test then
  passed. This was not caused by the DRC ledger changes.
- RED/GREEN evidence slice 1 passed: DRC application ordinals, request
  metadata, explicit cutoff finalization, and no-phantom-TX behavior.
- RED/GREEN evidence slice 2 passed: accepted source ACKs now reference a
  physical ACK TX and successful RX attempt, while malformed sender/path
  ACKs persist a rejection reason.

## 2026-10-05 - Matched D-Trigger Branch Continuation

- Previous goal turn is classified as progress because it changed the
  authoritative 493xx interpretation and experiment contract, not merely
  restated status. The full core rewrite, new simulations and ICC revision
  remain open.
- Session catch-up with `python3` found no unsynced state; the existing dirty
  worktree and all prior artifacts were preserved. Read the plan, findings,
  progress, checkpoint and draft branch design before implementation.
- Independent read-only contract and runner-hook audits are underway. The
  next code step is a public RED/GREEN nonreserved target-replay test; no
  494xx, 47xxx or 48xxx seeds have run in this continuation.
- Added the first vertical slice for `tools/diagnose_matched_d_trigger.py`:
  old DCB reference target enumeration, D/R/F target overrides, equal token
  and discovery-timestamp accounting, target-only no-rescue primary branches,
  role-keyed channel/jitter streams, expanded prefix snapshots, and
  fail-closed artifact/seed-cohort helpers. The old production behavior
  remains unchanged by default. Five focused tests pass.
- Before smoke, fixed serialization of queued `PendingSend` and dataclass
  state in prefix hashes, and separated discovery/useful FLOOD jitter roles
  with attempt ordinals. No 494xx seed has run yet.
- The first direct 49400 smoke attempt failed immediately with
  `ModuleNotFoundError: lora_mesh_sim` before any seed simulation or output;
  the script now inserts its repository root before imports. This failed
  attempt is not data and is not being retried unchanged.

## 2026-10-05 - Independent 493xx Audit And Rewrite Decision

- Recovered the dirty research worktree and four Markdown checkpoints.
  The first catch-up attempt used unavailable `python`; `python3` succeeded
  without an unsynced-context report. No existing edits were reverted.
- Independent 493xx artifact audit finished PASS: six raw JSONL hashes,
  source hashes, 70 runs, 2,793 flows, 16,935 actions, 35,574 physical TXs
  and all 54 paired intervals reconcile; out-of-window TX count is zero.
- Scientific triage rejects treating DCB, a D-to-R/F shortcut or the
  reversible trial as the requested finished algorithm rewrite. The next
  step is a prospectively specified, same-prefix D/R/useful-F decision
  experiment with matched bookkeeping/feedback/recovery, followed by a new
  device-local source controller and same-wire causal controls.
- No further seeds, ICC paper/PDF, VERSION, GitHub or EDAS were changed in
  this continuation. The earlier 28 focused and 1101-pass/one-skip full
  regression still apply to the current protocol/capture implementation.
- Wrote the independently audited exploratory result interpretation and a
  draft common-prefix D/R/useful-F branch contract. The contract explicitly
  separates cold D, equalizes source-token accounting and target rescue,
  and pairs useful-payload randomness without pairing D's RREQ to R/F DATA.
  No new branch code or seed run has occurred.

## 2026-10-05 - Seven-Arm Diagnostic Continuation

- `planning-with-files` catch-up found no unsynced session context; inspected
  the current dirty worktree, plan, findings, progress and rewrite checkpoint.
- Preceding goal turn completed the DCB-wire trigger-F control and the first
  seven-arm capture implementation. Focused predecessor results: 64 control
  tests and 15 synthetic capture tests passed. Combined current check:
  18 passed; compilation and `git diff --check` passed.
- The current scientific decision remains NO-GO for freezing a new source
  controller. This continuation will audit capture, fill critical tests,
  then run only the prospectively fixed nonreserved 493xx diagnostic if
  ready. No 493xx/47xxx/48xxx run, ICC edit, version, upload or EDAS action.
- Inspected all seven-arm capture and synthetic-test code and the underlying
  `run_one_sr` recorder/cost path. Independent read-only capture audit,
  scoped public-behavior test additions and scientific core-criteria review
  are in progress in separate agents.
- Independent audit completed with two P1 and two P2 findings. Public tests
  reproduced each scoped capture issue before fixes: D source-ACK timeout
  misclassification, missing future-start TX, wrong-arm/flow physical TX,
  invalid windowed/queued TX counts, bound-default CLI seed rejection, and
  mixed energy scope. Their targeted GREEN checks pass; full suite remains.
- Current diagnostic/control suite: 28 passed. Python compilation and
  `git diff --check` passed. The full repository pytest session is still
  running; 493xx capture has not started. Verified no prior 493xx output
  artifact exists in `results/` and sufficient local disk space remains.
- Complete repository test run finished: 1101 passed, one skipped in 177.00 s.
  Independent post-fix capture audit found no remaining P1. Preflight
  confirmed fixed 49301--49310 seeds, seven arms, case hash, source hashes,
  no existing named output artifact and available disk space. The once-only
  public diagnostic is now the next action.
- Independent ICC paper audit confirmed that the current five-page LaTeX
  still reports the old calibrated policy and old numbers; no paper files
  were changed during this diagnostic stage.
- Ran the predeclared 49301--49310 seven-arm public diagnostic once; its
  manifest and six raw JSONL files were written under
  `results/meshecho_source_action_public_49301_49310_20261005`.
  Initial file line counts match manifest counts; saved source and case
  hashes equal the current frozen inputs. Independent artifact and science
  audits are in progress; no confirmatory conclusion or paper edit yet.
- An initial `jq` reduction of nested replacement-action objects used
  object addition (key overwrite), not numeric count addition. Its F/R
  totals were discarded; numeric aggregation corrected them to 34 R/one F
  under source-FR and 30 F/five R under trigger-F on old-DCB D identities.
- A read-only 399-flow join reports zero trial/blind first-physical-action,
  path, deadline-ACK or delivery difference. This is still an exploratory
  mechanism finding pending independent archive verification.

## 2026-10-05 - Trial Screen and Core Redesign Continuation

- Recovered the current dirty worktree with the planning catch-up script;
  preserved all pre-existing user/research changes.
- The predeclared nonreserved 49201--49210 public screen was run once and
  saved as `results/meshecho_trial_public_49201_49210.json`. Exposure is
  present (14 physical trials, 11 trial ACK commits, three guard abandons),
  but trial and blind have zero per-flow physical action/path and endpoint
  divergence. The current trial mechanism is NO-GO for freeze.
- The parallel trial-gate implementation now requires five trial-centered
  paired contrasts plus audited physical exposure/provenance; focused
  DCB/runner verification reports 87 passed. Full current-tree regression
  and independent design review remain due.
- Next: explain the trial/blind identity, specify a replacement device-local
  source policy and public RED/GREEN behavior tests, then perform new matched
  nonreserved diagnostics before any reserved development. No ICC paper/PDF,
  VERSION, GitHub, EDAS, or 47xxx/48xxx action.
- Explained structural masking of trial versus blind in code and saved
  screen. Added a separate nonreserved four-flow interleaving witness test;
  it passed and shows direct versus two-hop physical paths before the trial
  ACK. The recurring-fading result remains NO-GO.
- Ran `python3 -m pytest -q` after the runner gate edits: 1070 passed,
  one skipped in 166.81 s. The witness was added after that full run and
  passed its own focused test; a later full run should include it.
- Began a read-only exposure check for a selective split reverse-ACK path
  candidate using already-opened 46xxx artifacts. No protocol or manuscript
  behavior has been changed for that candidate.
- Completed the archived split-ACK triage. The authenticated 46xxx saved
  rows show only 3/99 age-valid nominated direct DATA receptions without
  an initial direct ACK, and no saved current DATA SINR. Wrote a separate
  NO-GO research note instead of implementing a low-exposure ACK detour.
  The forward-DATA-failure branch remains the next candidate target.
- Predeclared a seven-arm 49301--49310 nonreserved source-action diagnostic
  to separate old D, no-D and trial control behavior with full saved
  flow/action/physical-TX provenance. The seventh arm, useful-data F at
  the old D trigger, was added before any seed run. No seed in this new
  split has run.
- Independently rejoined the existing 46xxx DHR action/flow/TX archive:
  70 D decisions (67 aging), 64 candidate DATA, six timeout fallbacks,
  66/70 source ACKs; RREQ+RREP gross airtime 205.987328 s, 19.0% of
  network airtime. This is descriptive DHR evidence, not DCB causal gain.
- Independent runner review reproduced two provenance holes. TDD fixes now
  require the accepted backup ACK before a trial decision and the *first*
  physical R path to match the pending path. Focused DCB runner/protocol
  suite: 89 passed. No reserved seed ran. Full current-tree suite after
  these latest tests/fixes remains due.

## 2026-10-05 - Trial-Core Resume

- Used the planning catch-up script with `python3` after the host rejected
  `python`; it returned no unsynced-context report. Preserved the dirty tree.
- Reproduced `SyntaxError: unmatched ')'` at `lora_mesh_sim.py:3805`, removed
  the extra closing parenthesis, and verified `py_compile` plus 100 focused
  DCB/DHR/DBR/SR/airtime tests.
- Independent read-only review reproduced old-timeout and stale-active-trial
  defects with nonreserved seed 17. Each was captured as a failing public
  test before a scoped fix. Route-expiry and source-LRU boundaries pass.
- The parallel runner integrated trial/no-switch/blind arms and physical
  provenance checks; its 34 tests and nonreserved positive fixture pass.
  Full regression after behavior fixes: 1040 passed, one skipped in 163.69 s.
  The two later boundary fixtures and current combined DCB/runner suite
  pass (78 tests); compilation and `git diff --check` pass.
- The first LRU fixture failed before reaching the intended state because
  added near nodes changed FLOOD contention. Moving them far away preserved
  the four-node trial precursor; no protocol fix was made for that failure.
- The suspected runner rejection on trial abandonment was investigated with
  real seed-73/17 traces and ruled out. Two regression tests were added,
  while the audit logic remained unchanged; combined DCB/runner suite: 80
  passed. The trial-core gate is drafted but remains unimplemented/unfrozen.
- Predeclared an exploratory nonreserved 49201--49210 public mechanism
  screen in `docs/research/meshecho_trial_public_mechanism_screen.md`. Its
  script/tests are being prepared separately; no such seed has run yet.
- No reserved 47xxx/48xxx cohort, ICC source/PDF, VERSION, GitHub or EDAS
  action was taken. Trial-core performance remains unknown.

## 2026-09-04

- Read the academic-paper, LaTeX compile, GitHub publish, and file-based
  planning instructions.
- Confirmed branch `version/v2`, remote
  `https://github.com/BH4ME/lora-mesh-routing-sim.git`, and authenticated `gh`.
- Confirmed current repository version `2.1.10`; the target release for this
  revision is `2.1.11`.
- Confirmed the paper already contains the fairness audit and random-pair
  probe, but release references still need to move to `2.1.11`.
- Added the persistent planning files required for resumable work.
- Previous verification: 44 unit tests passed; Python compilation, shell
  syntax, and `git diff --check` passed before this continuation.
- Audited connected-multihop candidates and confirmed that the 15 km/18 km
  settings are route-discovery stress cases, not neutral data-plane
  benchmarks. Added route-discovery success and RREP/RREQ diagnostics to the
  simulator and probe.
- Saved diagnostic matrices:
  `results/meshecho_fair_connected90_lowload.csv` and
  `results/meshecho_fair_connected90_singleflow.csv`.
- Current verification after the diagnostic instrumentation: 45 tests passed;
  Python compilation and `git diff --check` passed.
- Revised the ICCT manuscript to use the one-shot budget-matched random-pair
  results, added a route-discovery stress-check subsection, and removed the
  unsupported confidence-only interpretation from the random probe.
- Ran 10-seed random-pair and 10-seed connected 20-node one-shot probes; the
  paired confidence intervals include zero for the confidence-only comparison.
- Rechecked fairness with exploratory 12 km and 14 km area scans. The scans
  improve the link-quality regime but do not create enough random-pair
  multi-hop routes for a clean headline benchmark. A 12 km connected-pair
  check instead exposes route-discovery imbalance, so these scans remain
  calibration evidence rather than paper headline data.
- Added explicit disclosure that the connected-pair stress check includes a
  route-reply timing asymmetry between immediate MeshCore-like RREP emission
  and MeshEcho candidate-window RREP emission.
- Confirmed the worktree release target is `2.1.11`, while the firmware
  prototype remains `meshecho-firmware-v2.1.2`.

## Next Actions

1. Stage only task-related files, commit, push, and update the draft PR.
2. Verify the remote commit, PR metadata, and final artifact checks.

## Checkpoint - 2026-09-04

- Recompiled the revised ICCT manuscript with bundled Tectonic.
- The final artifact is 8 pages, PDF version 1.5, and the root PDF matches the
  `build-2_1_11` PDF byte-for-byte.
- Visual checks covered all 8 rendered pages. No layout overlap was found.
- Final validation passed: `python3 -m pytest -q` reports 45 passed;
  Python compilation, shell syntax, and `git diff --check` passed.
- The final PDF SHA-256 is
  `b822940c36b13a084538691b526a2b72c0d32463c67ff4772e76937fa4ab9b9a`.
- The initial compile command used a nonexistent skill subdirectory; the
  correct script is
  `/Users/bh4me_macair/.codex/plugins/cache/openai-bundled/latex/0.2.6/scripts/compile_latex.py`.
- Only explicitly selected task files should be staged. Build directories,
  rendered images, temporary probes, course materials, and other unrelated
  worktree files remain excluded.

## Publish Continuation - 2026-09-04

- Rechecked the repository before publishing. Local `HEAD` is `087f84e`,
  `VERSION` is `2.1.11`, and the branch is one commit ahead of the remote.
- The complete fairness-aware manuscript revision is already committed.
- The next action is to push `version/v2`, update draft PR 1 from 2.1.9 to
  2.1.11, and verify the remote state.

## Publish Transport Note - 2026-09-04

- `git push -u origin version/v2` failed before updating the remote with an
  HTTP/2 framing-layer error. Local commits are intact.
- Retry with HTTP/1.1, then verify the remote branch and PR.

## Final Publish State - 2026-09-04

- HTTP/1.1 push succeeded; the final local and remote `version/v2` state is
  `251ba505d4763f971a647953f4ea99fe3a9399a3`.
- PR 1 is open as a draft with the updated 2.1.11 title and body:
  `https://github.com/BH4ME/lora-mesh-routing-sim/pull/1`.
- `VERSION` is `2.1.11`; the final paper is an 8-page PDF with SHA-256
  `b822940c36b13a084538691b526a2b72c0d32463c67ff4772e76937fa4ab9b9a`.
- The requested paper revision, version bump, GitHub publish, and resumable
  Markdown state tracking are complete.

## 2026-09-04 - 2.1.12 Revision Started

- Reopened the fairness question after confirming that the main 3 km/SF9 case
  is link-friendly and mostly one-hop, while the random-pair probe does not
  show a general PDR advantage.
- Confirmed the next revision should quantify the remaining recovery-budget
  asymmetry rather than only describe it.
- Planned a formal current-code audit with identical 20-seed main-scene
  inputs and two `calm-mesh` settings: default route-miss fallback versus
  route-miss fallback disabled. MeshCore-like will be retained as the fixed
  source-route reference.
- Added the explicit route-miss fallback control and the paired recovery-budget
  audit script.
- Re-ran the 20-seed audit after correcting the report's route-discovery metric
  from a raw success count to successes divided by attempts.
- Corrected mean route-discovery success rates are `0.834` for MeshCore-like,
  `0.798` for CALM with fallback, and `0.805` for CALM without fallback.
- Updated the ICCT manuscript to release `2.1.12` and state that the audit does
  not show an easier route-discovery process for MeshEcho.
- Found and quantified a second fairness issue: MeshCore-like used a `300 s`
  route-cache TTL while MeshEcho used `600 s`.
- Added configurable `--meshcore-route-ttl-s`, reran a paired 20-seed TTL
  audit, and found that matching MeshCore-like to `600 s` changes ACK PDR from
  `0.381` to `0.519`; the remaining matched-TTL MeshEcho gap is
  `+0.209 +/- 0.071`.
- Updated the paper and fairness report to identify the native TTL mismatch as
  a favorable bias and to use the matched audit as the fairer reference.

## Next Actions

1. Compile and inspect the manuscript after the TTL disclosure.
2. Run the final tests, static checks, and consistency checks.
3. Selectively commit, push, update PR 1, and verify the remote state.

## 2.1.12 Final Verification - 2026-09-04

- Added the route-cache TTL audit and changed fresh ICC matrices to use the
  matched `600 s` MeshCore-like TTL by default. Legacy `300 s` reproduction is
  still available with `MESHCORE_ROUTE_TTL_S=300`.
- Recompiled the manuscript after the TTL disclosure. It is now 9 pages,
  PDF 1.5, SHA-256
  `97a5fc593a60ea1295697d0e90df09940ade0c158c54f290c611308598b70920`.
- Latest validation: `python3 -m pytest -q` reports 47 passed; Python
  compilation, `bash -n`, CLI help, and `git diff --check` passed.
- Latest rendered pages were visually checked with no layout defects.
- Remaining actions are selective commit, push, PR update, and remote
  verification.

## 2026-09-04 - 2.1.13 Fairness-Focused Revision

- Rechecked the simulation from a fairness perspective after the user asked
  whether the data were too favorable.
- Confirmed the original matrix is a valid shared-harness comparison but is
  not a neutral multi-hop benchmark: direct-link PRR is nearly saturated,
  fixed pairs favor caching, and native MeshCore-like TTL was shorter.
- Preserved the matched-TTL audit, random-pair non-saturated probe, one-shot
  timeout-budget check, and controlled route-conflict experiment as separate
  evidence layers.
- Updated the manuscript and release metadata to `2.1.13`; no-confidence
  behavior is now explicitly disabled in both route admission and confidence
  fallback/reward paths.
- Full validation: `python3 -m pytest -q` reports 49 passed; Python
  compilation, shell syntax, and `git diff --check` pass.
- Bundled Tectonic build succeeded at
  `paper/icct2026/build-2_1_13-tectonic/icct2026_lora_mesh_preliminary.pdf`; the
  verified root PDF is 9 pages with SHA-256
  `aa2c2e5e171595256938be222a2cca7757dbbdc8bb516e4cc640dc2f2d300cbe`.
- Next: stage only the 2.1.13 files, commit, push `version/v2`, update PR 1,
  and verify the remote publication.

## 2.1.13 Final Publish State - 2026-09-04

- Committed the fairness-focused revision as `fe24d1d` and pushed it to
  `origin/version/v2`.
- Updated draft PR 1 to
  `[codex] MeshEcho 2.1.13 fairness-focused evaluation`.
- Verified PR 1 is OPEN/DRAFT with base `main` and head `version/v2`.
- Verified `VERSION=2.1.13`, 49 passing tests, and a 9-page PDF 1.5 with
  SHA-256
  `aa2c2e5e171595256938be222a2cca7757dbbdc8bb516e4cc640dc2f2d300cbe`.
- The user's fairness concern is now reflected in both the simulation defaults
  and manuscript claims; the work is complete pending any new experiment
  request.

## 2026-09-18 - 2.1.14 ICC Quality-Gate Revision

- Continued in clean clone `/tmp/lora_mesh_remote_current.iIrtPz` at remote
  `version/v2` commit `9c1562e`; the damaged original worktree was left
  untouched.
- Added per-seed `validate_non_degenerate_regime()` checks to the connected
  multihop fairness probe. The gate requires a complete requested pair pool,
  mean graph distance >= 2 hops, and at least 10% of direct links below 0.99
  static PRR; saturated or effectively one-hop evidence now fails explicitly.
- Added three regression tests covering acceptance, saturated direct links,
  incomplete pair pools, and insufficient graph distance.
- Added the automatic quality probe to `tools/run_icc_experiments.sh`; it is
  enabled by default and can be calibrated with `ICC_QUALITY_*` variables or
  disabled only for explicit legacy reproduction with
  `ICC_RUN_QUALITY_PROBE=0`.
- Bumped release metadata and documentation from `2.1.13` to `2.1.14`.
- Full test discovery passed: 52 tests. Python compilation, `bash -n`, and
  `git diff --check` passed.
- Real three-seed quality probe passed. Per-seed pair counts were 24, mean
  selected graph distance was `2.014` hops, mean direct-link PRR-below-0.99
  fraction was `0.641`, and mean PRR-below-0.50 fraction was `0.445`.
- Full ICC shell smoke passed with four matrix scenarios plus the new quality
  gate. The initial smoke invocation exposed and then fixed the public CLI
  protocol alias (`meshcore`, not internal `meshcore-like`).
- Versioned quality evidence is present in
  `docs/results/meshecho_v2_1_14_connected_multihop_quality.md` and
  `results/meshecho_v2_1_14_connected_multihop_quality.csv`.

## Next Actions

1. Run final diff/status and consistency checks, then selectively stage the
   2.1.14 implementation, tests, docs, generated quality evidence, and state
   Markdown.
2. Commit, push `version/v2`, and verify the remote commit and draft PR.

## 2.1.14 Final Publish State - 2026-09-18

- Committed the quality-gate revision as `b5de06b` and pushed it to
  `origin/version/v2`; local and remote refs match.
- Updated draft PR 1 to
  `[codex] MeshEcho 2.1.14 ICC evidence-quality gate`.
- Verified PR 1 is OPEN/DRAFT with base `main` and head `version/v2`.
- Verified `VERSION=2.1.14`, 52 passing tests, the real three-seed gate
  result, and the full ICC shell smoke result.
- The 2.1.14 revision is complete. Future simulation/code changes must start
  from a new incremented version and repeat the test/simulation/publish cycle.

## 2026-09-18 - 2.1.15 Continuation Audit

- Resumed in clean clone `/tmp/lora_mesh_remote_current.iIrtPz` at the
  uncommitted 2.1.15 revision; the damaged original worktree remains
  untouched.
- The prior long-running command has finished and produced only the
  `50n_unicast_pairs` and `50n_mixed` 2.1.15 outputs. The shell script's
  quality and calibrated sections were not executed in that invocation.
- `python` is unavailable on this host; planning helpers and checks must use
  `python3`.
- Next action: run the missing 2.1.15 quality-gate and calibrated multi-hop
  experiments, then audit the manuscript and release metadata before any
  commit or push.

## 2026-09-18 - 2.1.15 Evidence and ICC Manuscript

- Re-ran `OUT_PREFIX=meshecho_v2_1_15_icc2027 bash tools/run_icc_experiments.sh`.
  All four legacy scenarios, the 3-seed connected-multihop quality gate, and
  the 20-seed calibrated matrix completed successfully.
- Versioned evidence now includes raw CSVs, long-format summaries, and reports
  for `50n_unicast_pairs`, `50n_mixed`, `50n_mixed_shadow6`,
  `50n_mixed_rate10`, `connected_multihop_quality`, and `calibrated_multihop`.
- Rewrote `paper/icc2027/icc2027_lora_mesh.tex` around the calibrated matrix;
  it reports the paired Smart-CALM confidence/no-fallback intervals and keeps
  the old 3000 m matrix as a declared sensitivity case.
- Bundled Tectonic compiled the ICC source to 3 pages at
  `paper/icc2027/build-2_1_15-tectonic-v2/icc2027_lora_mesh.pdf`; Poppler
  rendered all three pages and visual inspection found no clipping or overlap.
- Canonical `docs/results/icc2027_comparison.md`, the experiment plan, version
  index, and changelog now point to 2.1.15 evidence.
- Next: run tests/static checks and perform selective stage/commit/push plus
  remote PR verification. Do not stage `tmp/` or Tectonic build directories.

## 2026-09-18 - 2.1.15 Local Publish Attempt

- Final local validation completed: 53 tests passed, Python compilation,
  `bash -n`, CLI help, `git diff --check`, and 3-page PDF page-count checks
  passed.
- Selective release commit `fb133ba6ede8c7eb0ef3a08d70e98b6fa18a334c` was
  created on `version/v2`.
- `git push origin version/v2` failed after 75 seconds with
  `Failed to connect to github.com port 443`; a second read-only remote check
  and `curl` to GitHub also timed out. Remote publication and PR verification
  remain pending an available network path.
- Untracked files are limited to old 2.1.14 evidence, Tectonic build output,
  legacy paper figures, and `tmp/` renderings; none were staged.

## 2026-09-18 - 2.1.15 Remote Publish Complete

- Network access recovered and `git push origin version/v2` succeeded:
  `origin/version/v2` now points to `2ebefd13b41fe196f0df9092fafd38714ed6b59c`.
- PR 1 was updated and verified as OPEN/DRAFT, base `main`, head
  `version/v2`, title `[codex] MeshEcho 2.1.15 ICC calibrated multi-hop
  evidence`, head OID `2ebefd1`.
- `gh pr checks 1` reports no configured checks; no remote CI result is being
  implied. Local authoritative gates remain 53 passing tests, completed
  versioned experiments, and the 3-page rendered ICC manuscript.
- The 2.1.15 objective is complete. Temporary build/render files and old
  untracked 2.1.14 artifacts remain intentionally excluded from the commits.

## 2026-09-18 - ICC Submission-Readiness Audit

- Fetched the official ICC 2027 submission guidelines. Verified requirements:
  English IEEE 10-point paper, maximum six printed pages for initial review,
  PDF-only EDAS submission, exact EDAS/PDF title and author-list match, and
  no double submission/plagiarism. Registration and author presentation are
  required after acceptance for proceedings/Xplore publication.
- Added `docs/icc2027_submission_checklist.md`; it marks repository checks
  complete and leaves only the user-specific author metadata/EDAS actions
  unchecked.
- Pushed checklist commit `753a9b1786cb14bcd45b294c22ce83bd2b3bf4f0`.
- Verified PR 1 is OPEN/DRAFT with head `version/v2` at `753a9b1`.

## 2026-09-19 - 2.1.16 Five-Page ICC Revision Started

- User requested an expansion from three pages to approximately five pages and
  an evidence-based check of whether prior ICC papers require physical
  validation.
- Confirmed the clean working copy is `/tmp/lora_mesh_remote_current.iIrtPz`,
  branch `version/v2`, at remote release `2.1.15`; the original workspace has
  damaged Git tree objects and remains untouched.
- Queried Crossref/OpenAlex metadata for ten ICC papers. The sample contains
  simulation/analysis-only papers (coverage, dynamic SF, FER and closed-form
  analysis) as well as papers that add real-world measurements or testbed
  validation (NS-3 LoRa and lightweight carrier sensing).
- Recorded the source-level evidence and conservative interpretation in
  `findings.md`; the detailed citation table will be added as
  `docs/icc2027_prior-work_hardware-evidence.md`.
- A shell loop used for an exploratory metadata request emitted a zsh command
  parsing error because a diagnostic string began with `===`; no repository
  state changed. Subsequent OpenAlex requests used a corrected command.
- Next: add the detailed prior-work evidence document, extend the LaTeX paper
  with related work, algorithm details, experiment parameters, extra result
  tables/figures, and discussion while keeping the PDF at five pages or less
  than the ICC six-page hard limit; then bump the release to 2.1.16, rebuild,
  test, commit, push, and update PR 1.

## 2026-09-19 - 2.1.16 Manuscript and Audit Artifacts

- Added `docs/icc2027_prior-work_hardware-evidence.md` with ten DOI-linked ICC
  LoRa/IoT samples and conservative classifications of analytical, simulation,
  measurement, and testbed evidence.
- Expanded the ICC manuscript with related work, implementation-faithful
  confidence/recovery equations, fixed parameters, metrics/statistics, three
  evidence strata, paired ablation table, discussion, reproduction manifest,
  and hardware-in-the-loop follow-up boundary.
- Bumped release metadata and paper text to `2.1.16`; the paper explicitly
  reuses the verified 2.1.15 simulation artifacts because simulator behavior
  did not change.
- Tectonic build `build-2_1_16-tectonic-v3` succeeds and reports exactly 5
  pages. Rendered pages 1--5 were visually inspected; no clipping or table
  overlap was found.
- Updated the ICC checklist, experiment plan, comparison summary, version
  index, README, and changelog to describe the 2.1.16 paper-only revision.
- Full tests/static checks pass: 53 tests, Python compilation, shell syntax,
  `git diff --check`, and a 5-page PDF check. A 600 s one-seed calibrated
  smoke run passed the quality gate and produced nonzero protocol results.
- A redundant full runner was stopped during its second legacy scenario after
  confirming that it duplicated the complete 2.1.15 matrix without code
  changes. Partial 2.1.16 outputs remain untracked and will not be staged.
- Next: stage only the intended 2.1.16 source/docs, the new prior-work audit,
  and the final paper build artifact policy; commit, push, update PR 1, and
  verify the remote state.

## 2026-09-19 - 2.1.16 Published

- Committed the intended source/docs as `859686a` and pushed
  `origin/version/v2` successfully.
- Updated PR 1 to `[codex] MeshEcho 2.1.16 five-page ICC manuscript and
  hardware audit`; it remains OPEN/DRAFT.
- Verified the remote head OID, PR title/body, and validation summary. No
  automated GitHub checks are configured, so local tests and PDF/experiment
  gates remain authoritative.
- The remaining pre-submission item is still user-specific author metadata in
  EDAS and the LaTeX author block; no names were inferred.

## 2026-09-19 - 2.1.17 Reviewer-Directed Revision Started

- Re-read the current clean remote clone, release metadata, ICC manuscript,
  fairness probe, experiment runner, and planning files.
- Confirmed the next requested change is implementation of the prior
  assessment, not a new venue search.
- Chosen vertical slices:
  1. add a regression test for sensitivity-run configuration and implement
     the runner;
  2. run the SF/load cases and write their versioned reports;
  3. revise the ICC manuscript to include flooding, controlled-mechanism
     evidence, and conservative causal language;
  4. bump to 2.1.17, compile/test, publish, and verify.
- The local checkout remains unusable for Git operations because of missing
  tree objects; all changes stay in `/tmp/lora_mesh_remote_current.iIrtPz`.

### Next Exact Action

Inspect the public CLI/test conventions and add the first failing test for the
new sensitivity workflow before editing implementation code.

## 2026-09-19 - 2.1.17 Sensitivity Workflow Vertical Slice

- Added the first failing test for a sensitivity-case configuration, then
  implemented `tools/run_icc_sensitivity_experiments.py`.
- The runner exposes two cases: `sf8` (SF8 at 1 flow/min in a calibrated
  10 km square) and `load4` (SF7 at 4 flows/min in the primary 8.25 km
  square).
- Both cases retain 24 shared graph-selected pairs, PRR threshold `0.90`,
  graph distance 2--4 hops, direct-link PRR-below-0.99 gate `0.10`, matched
  2 s discovery, independent channel RNG, and zero Smart-CALM timeout retries.
- `tests/test_icc_sensitivity.py` passes (2 tests).
- Initial direct smoke exposed an import-path issue and an SF8 link-regime
  gate failure at 8.25 km; the first 20-seed calibration also rejected 9 km
  at seeds 10 and 14. The case is now 10 km, which passed a 20-seed
  meshcore-only quality calibration; the one-seed two-case smoke writes both
  CSV and Markdown reports successfully.

### Next Exact Action

Run the two sensitivity cases with 20 seeds and all seven ICC configurations,
then inspect the generated link-regime and protocol summaries before editing
the manuscript.

## 2026-09-19 - 2.1.17 Sensitivity Matrix and Manuscript Revision

- Completed the real two-case run with 20 seeds and all seven ICC
  configurations:
  `results/meshecho_v2_1_17_icc2027_sensitivity_sf8.csv` and
  `results/meshecho_v2_1_17_icc2027_sensitivity_load4.csv`, plus summary CSVs
  and Markdown reports.
- Both cases passed the per-seed connected-multihop quality gate. SF8 uses a
  10000 m square; SF7/load4 uses the primary 8250 m square.
- Added managed flooding to the primary manuscript table and comparison summary.
- Replaced the old legacy table in the five-page paper with a compact
  primary/SF8/load sensitivity table.
- Reworded Smart-CALM/no-confidence evidence as a complete policy-bundle
  difference; the controlled route-conflict experiment is now the surgical
  candidate-selection evidence.
- Added the optional `ICC_RUN_SENSITIVITY=1` hook to
  `tools/run_icc_experiments.sh`, the direct sensitivity command to README and
  experiment-plan docs, and bumped metadata to 2.1.17.
- Tectonic compiled
  `paper/icc2027/build-2_1_17-tectonic/icc2027_lora_mesh.pdf` successfully.
  `pdfinfo` reports exactly 5 letter-size pages; rendered pages 1, 3, 4, and 5
  were visually inspected with no clipping, overlap, or unreadable table.

### Next Exact Action

Run the full 2.1.17 test/static/consistency gates, then selectively stage the
new runner, tests, sensitivity CSV/report artifacts, paper/docs, and Markdown
state files. Do not stage partial 2.1.16 outputs or build caches.

## 2026-09-19 - 2.1.18 Metric Baseline Slice

- Started a new reviewer-directed release in the clean remote clone; the
  prior 2.1.17 release remains published and untouched.
- Added a failing test for ETX/ETT registry, monotonic cost scoring, and matched
  discovery configuration.
- Implemented `MetricMesh`, `etx`/`ett` protocol registry entries, CLI choices,
  and `icc`/`all` protocol expansion.
- The new test passes and the full suite now reports 58 passing tests.
- A one-seed, 600 s connected-multihop smoke passed the quality gate and
  produced nonzero ETX/ETT route/discovery rows. Under fixed SF/packet size,
  ETX and ETT are expected to select the same paths because ToA is constant.

### Next Exact Action

Run the full versioned 2.1.18 primary and sensitivity matrices, then revise the
manuscript around the new baseline and the paired statistical/metric wording.

## 2026-09-19 - 2.1.18 MeshEcho Identity and Component Attribution

- Added test-first MeshEcho component variants and made
  `MESHECHO_ABLATIONS` explicit:
  `meshecho-no-confidence`, `meshecho-no-fallback`,
  `meshecho-no-hop-penalty`, and `meshecho-no-age-penalty`.
- Ran the 20-seed primary matrix, SF8 sensitivity, offered-load sensitivity,
  and 20-seed component-ablation matrix. Every connected-multihop case passed
  its per-seed quality gate.
- Regenerated all 2.1.18 probe reports so the ICC evidence contains no
  Smart-CALM rows or ablation section.
- Rewrote the ICC comparison and experiment plan for MeshEcho, ETX/ETT, and
  MeshEcho-only component attribution. Bumped `VERSION` and release metadata
  to 2.1.18.
- Added the component-attribution table to the ICC manuscript and removed the
  redundant evidence-strata table to keep the PDF at five pages.
- Tectonic build `paper/icc2027/build-2_1_18-tectonic/icc2027_lora_mesh.pdf`
  succeeds with exactly five letter-size pages. All five rendered pages were
  visually inspected; no clipping, overlap, or unreadable table was found.

### Next Exact Action

Run full tests/static/report-consistency checks, selectively stage the 2.1.18
release (excluding old artifacts/build caches), commit and push `version/v2`,
then update and verify draft PR 1.

## 2026-09-19 - 2.1.18 Verification Checkpoint

- Full suite: `61 passed`.
- Python compilation, shell syntax, and `git diff --check` passed.
- Primary and component summary CSV/TXT artifacts were generated with
  `analyze_results.py`.
- Report consistency checks confirm 100 rows each for primary/SF8/load,
  180 rows for component attribution, complete pair pools, and no
  Smart-CALM text in the four ICC probe reports.
- The five-page PDF remains the inspected artifact after the final report and
  CLI naming changes.

## 2026-09-19 - 2.1.19 MeshEcho-Only Fairness Revision

- Added failing tests for legacy immediate-reply duplicate suppression and
  configured MeshEcho fallback TTL.
- Implemented both fixes in `lora_mesh_sim.py`; targeted metric-baseline tests
  now pass (`8 passed`).
- Regenerated the 20-seed primary, component-ablation, SF8/load sensitivity,
  and TTL600/TTL30 cache diagnostics after the code fixes.
- Updated the five-page ICC manuscript, ICC comparison, sensitivity defaults,
  project version index, and tests to target MeshEcho 2.1.19 only.
- Tectonic compiled the manuscript to exactly 5 letter-size pages; all five
  rendered pages were visually inspected with no clipping or overlap.

## 2026-09-19 - 2.1.20 MeshEcho Route-Conflict Attribution Revision

- Added a failing TDD identity test proving that the controlled route-conflict
  audit must instantiate `MeshEcho`, not `SmartCalmMesh`.
- Reworked `tools/run_route_conflict_experiment.py` to subclass `MeshEcho`,
  preserve the confidence/no-confidence controls, and remove adaptive profile
  and timeout-controller arguments.
- The targeted regression tests now pass (`2 passed`).
- Re-ran the controlled 20-seed route-conflict simulation. Both candidates were
  observed in 18/20 seeds; MeshEcho ACK PDR is `1.000` versus `0.779` for the
  shortest-candidate control, paired delta `+0.221 +/- 0.096`.
- Updated the ICC title to `MeshEcho: Confidence-Aware Route Admission for
  LoRa Mesh IoT` and synchronized the manuscript's route-conflict value and
  reproduction command.
- Next: bump the release and all versioned ICC evidence to 2.1.20, rebuild the
  five-page PDF, run the complete validation suite, and publish the revision.

## Next Actions

1. Run the full test/static/report-consistency gates.
2. Selectively stage only 2.1.19 source, tests, paper/docs, evidence, and
   Markdown state files; exclude historical artifacts/build caches.
3. Commit/push `version/v2`, update and verify the draft PR.

### Next Exact Action

Selectively stage the 2.1.18 source, tests, paper/docs, raw evidence, and
planning Markdown; exclude old 2.1.14/2.1.16 outputs, build directories,
figures, and `tmp/`. Then commit, push, update PR 1, and verify remote state.

## 2026-09-19 - 2.1.18 Pre-submission Assessment

- Independent methodology and venue reviews converge on **borderline ICC
  candidate / not a safe accept**. The paper is format-compliant and
  simulation-only evidence is defensible, but the main scientific risk is
  generalization and estimand alignment rather than page count or hardware.
- The primary CSV has 100 rows (5 protocols x 20 seeds); all 480 selected
  pair instances are exactly 2 hops, and every primary row has zero
  `route_cache_hits`. The current headline therefore measures sparse,
  first-discovery route admission, not cache reuse or route aging.
- The MeshEcho/no-confidence delta is an end-to-end policy-bundle difference
  because discovery success and route length also change; the fixed-candidate
  route-conflict audit is the only surgical confidence evidence.
- A code-level baseline audit found a P0 fairness issue: the matched
  source-route destination suppresses duplicate RREQs before candidate
  collection, while MeshEcho/ETX/ETT collect candidates through the same
  nominal two-second window. The +0.183 headline gap therefore needs a
  rerun with equal candidate exposure (or a narrower first-arrival baseline
  label).
- ETX and fixed-SF ETT are identical by construction. A stronger distinct
  baseline and an unconditioned random-pair/deeper-hop case are the highest
  value additions.
- The local 2.1.18 files remain staged only; remote `origin/version/v2` is
  still 2.1.17. No claim that GitHub already contains 2.1.18 should be made
  until the publish gate is complete.

### Review-driven next actions

1. Decide whether to submit the current bounded claim or make a 2.1.19
   evidence revision.
2. If revising, prioritize: repeated-pair/cache-aging experiment; unconditioned
   random-pair and deeper 3--5-hop case; matched fixed-candidate ablation;
   temporal fading/stale-route case; and one distinct standard baseline.
3. Regardless of experiment scope, clarify that all table `\pm` values are
   95% CIs, disclose the SF8 area calibration, narrow the fallback/age claims,
   publish/tag 2.1.18, and replace anonymous EDAS metadata.

## 2026-09-19 - 2.1.20 Pre-submission Review

- Read the current 2.1.20 ICC source, primary/route-conflict reports,
  submission checklist, and prior-work hardware audit.
- Confirmed the local 2.1.20 manuscript is six pages; the official ICC
  ceiling is six pages, while the project target is five pages.
- Confirmed the current root PDF still contains `Anonymous Authors`; no final
  EDAS submission should use this placeholder.
- Ran the complete local gates: 67 tests passed; Python compilation, shell
  syntax, `git diff --check`, and PDF text/metadata checks passed.
- Reviewer decision: borderline ICC candidate / weak-reject risk. The paper is
  technically reproducible and honest about limits, but the headline is
  conditioned on a PRR-qualified two-hop pair pool with zero cache hits, and
  no statistically separable advantage over ETX/ETT is shown.
- Recommended next action before EDAS: add an unconditioned random-pair and
  deeper-hop/scale case, add one distinct baseline, and test temporal fading
  or remove aging/recovery from the central claim; then compress to five pages
  and update author metadata/checklist.

### Current exact next action

Do not publish or submit the current 2.1.20 artifact yet. First choose between
the bounded ICC submission path (with tightened claims and five-page cleanup)
and one more evidence revision targeting the selection/generalization gap.

## 2026-09-19 - 2.1.21 Continuation

- Resumed from the preserved 2.1.21 state in the clean remote clone
  `/tmp/lora_mesh_remote_current.iIrtPz`; the damaged old checkout remains
  untouched.
- Confirmed `VERSION=2.1.21`, branch `version/v2`, and remote head `6d2134b`;
  the 2.1.21 work is not yet committed or pushed.
- Confirmed the min-hop baseline and deterministic temporal-fading code are
  present, and that the partially completed 2.1.21 runner produced the
  primary/sensitivity raw CSVs but not all required summary/report artifacts.
- Updated the persistent plan and findings before continuing.

### Next exact actions

1. Run the 20-seed generalization cases and complete missing 2.1.21 reports.
2. Run component attribution, cache diagnostics, and route-conflict evidence.
3. Update and compile the MeshEcho-only five-page ICC manuscript.
4. Run full verification, selectively commit/push, and verify the remote.

## 2026-09-19 - Deep-Multihop Calibration Correction

- The first 2.1.21 generalization attempt stopped at the quality gate rather
  than dropping a bad seed: at 20 km, PRR threshold 0.85, seed 12 had only
  20 of the requested 24 3--5-hop pairs.
- A deterministic scan over seeds 1--20 showed that a 21 km square yields
  complete 24-pair pools for all seeds and retains `direct_prr_below_0_99`
  above 0.67 for every seed.
- Updated the deep case in
  `tools/run_icc_generalization_experiment.py` to 21 km and started the
  corrected generalization run under the `meshecho_v2_1_22` prefix.
- The version bump to 2.1.22 will occur after this corrected simulation, in
  accordance with the repository versioning rule.

## 2026-09-19 - 2.1.22 Evidence Package Verification

- Completed the corrected 2.1.22 generalization runner:
  random pairs, 100-node 21 km 3--5-hop deep multihop, temporal fading with
  600 s TTL, and temporal fading with 30 s TTL.
- Re-ran the main ICC matrix, connected quality gate, calibrated multihop
  matrix, SF8/load4 sensitivity, MeshEcho component ablation, cache TTL
  diagnostics, and route-conflict audit under 2.1.22 prefixes.
- Bumped `VERSION`, changelog, README, docs, and tool defaults to 2.1.22.
- Rewrote the ICC manuscript around MeshEcho-only 2.1.22 evidence. Tectonic
  compiled a 5-page letter-size PDF at
  `paper/icc2027/build-2_1_22-tectonic/icc2027_lora_mesh.pdf`.
- Verification passed: `71 passed`; Python compileall; shell syntax;
  `git diff --check`; PDF metadata; key row-count checks; and no Smart-CALM
  leakage in 2.1.22 ICC reports.

### Next exact action

Selectively stage 2.1.22 source/docs/tests/evidence/state files, commit, push,
update draft PR 1, and verify remote `version/v2`.

## 2026-09-19 - 2.1.22 GitHub Publication Check

- Selectively committed and pushed the 2.1.22 ICC evidence package to
  `origin/version/v2`.
- Verified local `HEAD` and `origin/version/v2` both pointed to
  `9ccd900cbd865264f0a80bc6ef6979e8f2327091` before the PR metadata update.
- Updated draft PR 1 title to
  `[codex] MeshEcho 2.1.22 ICC generalization evidence`.
- Verified PR 1 remains open and draft, with head branch `version/v2`.

### Next exact action

If continuing toward submission, verify the exact author order and title in EDAS,
complete venue checklist items, and decide whether to add real-hardware
validation or keep the claims explicitly simulation-only.

## 2026-09-20 - ICC Author Metadata Added

- Replaced the anonymous author block in the ICC manuscript with
  `Gao Zu` and `Quan Zhi`, in that order.
- Added the shared affiliation `Shenzhen University, Shenzhen, China`.
- Initially added CJK name annotations; these were removed from the ICC
  submission PDF in the later English-only author correction.
- Updated the ICC checklist, README, plan, and findings; EDAS registration and
  exact title/author matching remain pending.

## 2026-09-20 - ICC Primary Comparison Figure Added

- Added `paper/icc2027/figures/fig_primary_comparison.tex`, a compact
  two-panel bar chart for primary ACK PDR and total airtime.
- Used the existing 2.1.22 Table II means and seed-level 95% CI half-widths;
  no simulation or reported number changed, so the release remains 2.1.22.
- Integrated the figure near the primary Results subsection and verified the
  author-updated manuscript still compiles to exactly five letter-size pages.
- Visual inspection of the rendered page found readable axes, separated
  panels, and no clipping or overlap.

## 2026-09-24 - ICC/IEEE Formatting Cleanup

- Updated `paper/icc2027/icc2027_lora_mesh.tex` to use explicit
  `conference,letterpaper,10pt` `IEEEtran` options.
- Removed manual global float spacing, table row compression, unnecessary
  `IEEEoverridecommandlockouts`, and the forced `\clearpage` before references.
- Reduced the keyword list to five IEEE-style terms and tightened Table I's
  local tabular padding to eliminate the only overfull table warning.
- Rebuilt the manuscript at
  `paper/icc2027/build-icc-format/icc2027_lora_mesh.pdf`: 5 pages, letter
  paper, no visual clipping, no page numbers, no table overflow, and no figure
  overlap in rendered-page inspection.
- The author line still contained CJK annotations at this checkpoint; the
  English-only correction and rebuilt PDF are recorded below.
- Fixed a clean-clone verification issue in
  `tests/test_metric_routing_baselines.py`: the route-conflict CI test now
  reads the current `VERSION` report instead of an old 2.1.20 report that had
  only existed as an untracked local artifact in earlier working directories.

## 2026-09-24 - ICC English-Only Author Correction

- Removed the CJK author annotations, font declaration, and now-unused
  `fontspec` package from the ICC LaTeX source. The printed names are
  `Gao Zu` and `Quan Zhi`, both at Shenzhen University.
- Updated the submission checklist and stored the final PDF at
  `paper/icc2027/icc2027_lora_mesh.pdf` for GitHub review.
- Recompiled and inspected all five Letter-size pages. Page-one text
  extraction yields both English names; the embedded-font list contains no
  Chinese font, and no clipping or overlap was visible.
- This is a paper-format correction. No simulation code or results changed,
  so the simulation release remains 2.1.22.

## 2026-09-25 - ICC 2.1.23 Revision Started

- Started a new algorithm-plus-experiment revision from clean commit
  `dd06d46` on `version/v2`; current `VERSION` is 2.1.22.
- Read the academic-paper revision, PDF, TDD, and file-based planning
  instructions and recovered the existing plan files.
- Established the acceptance checks in `task_plan.md` from the latest
  evidence-based ICC review. No 2.1.23 simulation result exists yet.
- Independent read-only design audits are checking discovery fairness,
  primary traffic coverage, and five-page manuscript structure.

## 2026-09-25 - English Author Verification and Experiment Continuation

- Inspected the stable ICC LaTeX, BibTeX, figure, all three current PDF
  copies, extracted text, embedded fonts, and a rendered first page. No
  Chinese author name or Han glyph remains; current printed names are
  `Gao Zu` and `Quan Zhi`.
- The prior `/tmp/lora_mesh_remote_current.iIrtPz` PDF location is gone.
  Opened the stable ICC PDF in Codex and asked whether the user wants an
  English given-name-first order instead.
- Fair-discovery infrastructure is complete with four dedicated passing
  tests. The traffic runner is being finished by a separate agent. Next local
  action: test and correct repeated cumulative hop-penalty subtraction.
- The user specified author names in English given-name-first order. Changed
  the ICC LaTeX author line and submission checklist to `Zu Gao` and
  `Zhi Quan`; PDF rebuild and visual/text verification follow.

## 2026-09-25 - Author PDF and Algorithm Pilot Verified

- Rebuilt the ICC PDF from the edited LaTeX. It remains five Letter-size
  pages; page-one visual inspection and whole-PDF text extraction show
  `Zu Gao` and `Zhi Quan` with no Han characters. The root PDF is byte-identical
  to the checked build output (SHA-256 `ebb045978dedce3e6a39e8cbd44995b4318f1b99bd3888ae2dfccabb6b2e616e`).
- Test-first corrected repeated hop-penalty subtraction in `MeshEcho` only;
  the new test first failed on the old third-hop result and then passed. The
  historical `CalmMesh` behavior remains unchanged.
- Completed a 3-seed fixed-once/matched-RREQ-timing pilot with seven policies
  at `/tmp/meshecho_v2_1_23_pilot.{csv,md}`. Each protocol handled 72 actual
  unicasts, 24 per seed; quality gate passed. Pilot MeshEcho minus ETX ACK
  delta +0.069 has paired 95% CI [-0.191,+0.330], so no superiority claim.
- Focused routing/discovery/probe tests: 30 passed. A separate controlled
  first-discovery test and optional budgeted-admission variant are in progress.

## 2026-09-25 - Holdout Simulation Launched

- Added exact per-discovery candidate and selected paths to the fixed-once
  CSV; the new assertion first failed on the missing field and then passed.
- The optional one-hop/0.10-confidence-gain strategy passed its focused
  tests and ran on development seeds 1--3. It gave 40/72 ACKs and 91.8 s
  mean airtime, versus corrected MeshEcho 47/72 and 93.7 s; do not promote
  it as a reliability improvement.
- A one-seed isolated-first-discovery smoke recorded 24/24 identical
  candidate sets across MeshEcho, ETX, min-hop, and matched source-route.
- Launched the 20-seed (21--40) isolated-first-discovery and matched-timing
  fixed-once full matrix; wait for both processes before interpreting or
  modifying the manuscript. Output prefixes are `meshecho_v2_1_23_icc2027_*`.

## 2026-09-25 - Holdout Matrices and Boundary Result

- Completed `results/meshecho_v2_1_23_icc2027_matched_fixed_once.csv` (220
  protocol-seed rows) and its report/summary CSV. All 11 policies handled
  480 actual unicasts. MeshEcho vs ETX ACK difference +0.137 [0.090,0.185]
  with +1.9 s [1.6,2.3] airtime; budgeted variant 275/480 ACK vs MeshEcho
  332/480. Candidate sets match for only 148/480 MeshEcho-ETX discoveries.
- Completed `results/meshecho_v2_1_23_icc2027_isolated_first_discovery.csv`
  (1920 pair-policy rows). Regenerated its report after adding seed-paired CIs
  and selected-path checks; raw CSV SHA-256 matches the first run exactly.
  All 480 candidate sets match; MeshEcho-ETX ACK delta +0.163
  [0.121,0.204], airtime +0.094 s per pair [0.078,0.110].
- Native-timing random-pair generalization finished under the 2.1.23 prefix.
  MeshEcho beats ETX on ACK but managed flooding beats MeshEcho decisively
  (0.736 vs 0.430 ACK; 39.7 vs 103.2 s). Deep and fading cases remain
  running in the same session.

## 2026-09-25 - 2.1.23 Release Assembly

- Confirmed both remaining simulation sessions exited with status 0. All
  random-pair, deep-multihop, long/short-TTL fading, and native fixed-once
  artifacts were written under the 2.1.23 prefix.
- Independent audit checked raw row counts, 20-seed paired intervals, actual
  24/24 fixed-once unicast attempts, equal-candidate isolation, and adverse
  flooding/fading boundaries. It found report-template wording errors, which
  are being fixed without rerunning or altering source CSVs.
- Added a release-default regression test: it failed on 2.1.22, then passed
  after bumping `VERSION` and current runner output defaults to 2.1.23.
- Updated README, CHANGELOG, experiment plan, and checklist to distinguish
  2.1.23 from historical 2.1.22 evidence. Changed the existing LaTeX bar
  chart's five means and seed-level confidence whiskers to 2.1.23 values.
- The paper agent recovered a transiently missing TeX source from HEAD,
  preserving the confirmed author order `Zu Gao`, `Zhi Quan`, and is rewriting
  the manuscript. Remaining gates are paper/report review, final PDF, full
  tests, selective publication, and remote verification.

## 2026-09-25 - Final PDF and Test Gate

- The manuscript was expanded with exact confidence/age equations and a
  seed-paired methodology description. It compiles naturally to five Letter
  pages without overfull boxes or undefined references. All five page PNGs
  were visually inspected, including the updated bar figure, author block,
  tables, and flowing references. The checked root PDF SHA-256 is
  `8743be24223c2837f72947006df28f83cad121a056a8aeb0bce702f51162c670`.
- Full suite initially reported two stale 2.1.22 report expectations.
  Updated them to assert the current report set and recompute the route-
  conflict seed-paired interval from the current raw CSV. Final suite:
  `111 passed`. `compileall`, `bash -n`, PDF page/font/name checks,
  candidate-audit regeneration equality, and `git diff --check` passed.
- Next: stage only the 2.1.23 release and Markdown state; exclude the
  untracked TeX build directory. Commit/push `version/v2`, update draft
  PR 1, and verify remote metadata and head.

## 2026-09-25 - Publish Checkpoint

- Staged 49 intended 2.1.23 files; the untracked Tectonic build directory
  remains outside the commit.
- The staged whitespace gate failed on all 1921 lines of the isolated
  first-discovery CSV because the CSV writer emitted CRLF line endings.
- Next: test LF output, fix only the CSV writer and existing CSV line endings,
  confirm data/report equivalence, then run the final gates and publish.
- Added LF-output assertion to the existing CLI regression test; it failed on
  the original CRLF writer and passed after setting `lineterminator="\n"`.
- Mechanically converted the existing CSV from CRLF to LF. It has no CR bytes;
  its 1920 parsed rows, canonical row hash, 330/252 MeshEcho/ETX ACK counts,
  and regenerated Markdown report are unchanged. No simulation was rerun.
- Independent read-only preflight confirms 49 intended staged files, no build
  cache in the index, and current local/remote/PR head all at `dd06d46`.
- Final local checks: 111 tests passed; Python compileall, ICC shell syntax,
  staged and unstaged whitespace checks passed. Final PDF SHA-256 remains
  `8743be24223c2837f72947006df28f83cad121a056a8aeb0bce702f51162c670`.
- Old PR 1 metadata still names 2.1.22 and includes Chinese author names;
  update the existing draft after pushing the 2.1.23 release commit.

## 2026-09-25 - 2.1.23 GitHub Publication

- Committed 49 release files as `87a6184c8cf95a91769a9533462706693f3108bd`.
- Two HTTPS push attempts timed out; GitHub's API confirmed the remote ref
  stayed at the old `dd06d46` during both failures. Authenticated SSH push
  succeeded without changing the configured origin URL.
- GitHub `version/v2` and draft PR 1 head both then matched `87a6184`.
  Updated PR title/body to 2.1.23 and removed the old Chinese/English author
  name forms. PR remains OPEN/DRAFT, base `main`, head `version/v2`.
- Final artifact remains the checked five-page English-only PDF. Only the
  untracked Tectonic build directory is left outside the release.

## 2026-09-25 - Active Goal Completion Audit Started

- Classified the prior goal turn as progress because 2.1.23 code, evidence,
  paper, and GitHub PR state changed and were verified.
- Recovered the three Markdown state files and confirmed current HEAD
  `0dc54c0`, version `2.1.23`, and a five-page Letter ICC PDF.
- Began independent read-only algorithm, evidence, and submission audits.
  Next: recompute key numbers from raw CSVs, check the implementation and
  full manuscript, then resolve any material gap before marking the goal
  complete.
- Compared the 2.1.23 simulator diff and current manuscript/reports. The
  behavioral algorithm change is the corrected per-hop confidence penalty;
  matched discovery timing and candidate logging support fairer measurement.
  The no-hop-penalty result does not establish a significant ACK benefit.
- Independently recomputed primary, isolated, random-pair, and fading
  statistics from raw CSVs; key rounded manuscript values match.
- Independent audits identified a stronger PRR-product comparator missing
  from versioned evidence, two manuscript terminology inaccuracies, a
  Tectonic Times-to-Latin-Modern font fallback, and author-only funding and
  conflict declarations. A read-only in-memory comparator pilot found no
  clear MeshEcho ACK superiority over PRR-product; no result was added to
  the paper. Next: design and version the fair comparator and any justified
  algorithm change, then rebuild the manuscript from those results.
- Current 111-test suite passes before 2.1.24 edits. Independent reviewers
  confirmed all checked 2.1.23 headline numbers match raw data, but the
  current title/PRR/min-hop wording and missing stronger baseline need work.
- Preregistered a 2.1.24 PRR-product baseline and optional ACK-feedback
  stale-route eviction study. Development seeds are 41--50; untouched
  validation seeds will be 51--70. Seeds 21--40 are already exposed.

## 2026-09-25 - Resume and Author Order Confirmed

- The user confirmed given-name-first `Zu Gao`, `Zhi Quan`. The current ICC
  LaTeX, submission checklist, GitHub release, and five-page PDF already use
  that order; PDF text extraction verifies the printed names and affiliation.
- The prior 2.1.23 result remains published. The active algorithm/paper goal
  continues at the preregistered 2.1.24 work; no new result is claimed yet.
- Started parallel PRR-product implementation, evidence-based manuscript
  wording corrections, and read-only repeated-pair fading study design.
- Inspected the simulator's transmission event path to design a guard that
  starts at actual source DATA transmission and evicts only the matching
  route entry after an unacknowledged guard period.
- Lookup note: `tests/test_meshecho_protocol.py` does not exist; applicable
  tests are `tests/test_calm_protocol.py` and the metric/experiment test files.
- Existing `stale_fading` traffic already cycles four fixed source/destination
  pairs; use it for the development/validation ACK-eviction comparison.
- `pdflatex` and `bibtex` are installed. Final PDF build can move from the
  previous Tectonic fallback to a standard IEEEtran-compatible font setup.
- Lookup note: a `zsh` wildcard for nonexistent `run_icc2027*` produced
  `no matches found`; read the exact `tools/run_icc_experiments.sh` path.

## 2026-09-25 - 2.1.24 Comparator and ACK Eviction Implementation

- PRR-product comparator was added test-first to the main CLI, fair probe,
  and isolated first-discovery runner; related 42 tests passed. Seed-1 smoke
  gave identical candidate exposure for 24/24 pairs across five policies.
- Manuscript terminology/factual-method corrections are staged in the TeX
  source, preserving `Zu Gao` and `Zhi Quan`; performance claims still use
  2.1.23 data pending new versioned matrices.
- Added `meshecho-ack-evict` and `prr-product-ack-evict` optional variants.
  A red test first showed the missing variant, then a green test verified
  actual-TX-timed eviction. A second red test exposed missing counters;
  `Metrics.summarize` now reports invalidations and false invalidations.
  Focused tests also cover ACK preservation, replacement-route identity,
  one-shot behavior, and destination-delivered/ACK-lost diagnosis.
- Focused simulator/baseline suite: 55 passed; `git diff --check` passed.
  The generalization runner quality gate and feedback cases are in progress.
- Asked the authors to confirm funding and conflict declarations; neither
  statement may be treated as verified until they answer.

## 2026-09-25 - Development Evidence and Negative Decision

- Version default was raised test-first to 2.1.24, including ICC runner
  output prefixes; the corresponding release metadata test passed.
- Ran and completed the 41--50 development `feedback_fading`,
  `feedback_static`, and `feedback_fading_short_ttl` matrices with explicit
  2x2 feedback controls. Raw CSVs, summary CSVs, and reports are versioned
  under the `feedback_dev41_50` prefix; no 51--70 seed has been run.
- Development fading ACK PDR: MeshEcho 0.535, MeshEcho+ACK eviction 0.426,
  PRR-product 0.686, PRR-product+ACK eviction 0.607. Static ACK PDR:
  0.662, 0.573, 0.688, 0.571 respectively. Short TTL control further
  harms fading ACK completion. Do not promote the ACK-eviction variant.
- Independent review caught a custom-guard pass-through mismatch; a failing
  test reproduced it and the PRR-product branch was corrected. Default
  15-s development runs were unaffected.
- A report test first failed on overclaimed `false positives` and DATA-block
  wording; the report now says destination-delivered/ACK-unconfirmed and
  scheduled application blocks. Three reports were regenerated from the
  existing CSVs; no simulation was rerun for the wording change.
- A development-only alternate ranking hypothesis is under read-only
  scrutiny. Do not inspect or run untouched seeds 51--70 before freezing
  the algorithm/claim boundary.

## 2026-09-25 - ACK Guard Race Reproduction

- Read the current 2.1.24 plan, findings, and progress before resuming.
- The first targeted pytest node used an incorrect class name and collected
  no tests; retry with `MeshEchoAckEvictionTest` failed as expected because
  a later same-route ACK does not stop an older guard from deleting the route.
- Traced the failure through `on_ack` (clears only its own flow) and
  `expire_unacknowledged_route` (checks only its own ACK and entry identity).
  Next: record actual DATA start per guard and cancel only older same-entry
  guards upon a later confirmed flow.
- Implemented the actual-start ordering rule and added the reverse case in
  which an older delayed ACK must not cancel a newer unconfirmed flow.
  `python3 -m pytest -q tests/test_meshecho_ack_eviction.py`: 9 passed;
  `git diff --check` passed. Existing development CSVs remain untouched.
- Full suite: 131 passed, 2 failed because two historical report tests
  constructed 2.1.24 artifact paths that do not exist; a separate scoped
  test correction is in progress. No simulation result was altered.
- Independent read-only reviews found a score-driven direct-route bias,
  identified the calibrated max-min PRR candidate above, and flagged the
  current paper's missing PRR-product evidence and ambiguous route-repair
  wording. The 41--50 hypothesis and rejection rules are now frozen in the
  plan before implementation or new runs.
- Added optional `meshecho-calibrated` with model-derived RREQ SINR PRR,
  zero hop penalty, and no 0.98 saturation; wired dynamic and isolated
  runners. Related focused tests and a one-seed smoke passed.
- Completed new 41--50 fading and static matrices, plus 1440 isolated
  single-flow simulations. Original pre-fix CSVs were not overwritten.
  Fading candidate ACK improved from 0.535 to 0.689 at +4.1 s airtime;
  static candidate ACK was 0.694 versus 0.662 with interval crossing zero.
  Isolated candidate sets match 240/240, but its +0.013 ACK difference over
  old MeshEcho has interval crossing zero. Short-TTL process remains live.
- A separate scoped fix pinned historical report tests to 2.1.23 files;
  report wording now labels ACK-eviction variants accurately. The focused
  tests for both changes pass. A full suite is still required after all code
  edits and simulations.
- The short-TTL 41--50 matrix completed under a new prefix; calibrated ACK
  PDR was 0.272, old MeshEcho 0.251, PRR-product 0.272, with no convincing
  paired improvement and higher calibrated airtime. No 51--70 run has begun.
- Full suite after the calibrated variant and report edits: 138 passed;
  Python compilation and whitespace checks passed. A later comparator edit
  requires a fresh suite before holdout.
- Added test-first PRR-product-fallback control with identical PRR-product
  score and MeshEcho TTL-2 route-miss recovery budget/timing. Corrected an
  initial mistaken test expectation that FALLBACK would not count as DATA;
  the targeted behavior and registry tests pass. Fading/static 41--50
  control runs are currently live under a separate new prefix.
- Completed the 41--50 matched-fallback PRR-product controls: rounded fading
  ACK 0.689 and static ACK 0.694, matching calibrated MeshEcho's rounded
  values; old MeshEcho remains 0.535/0.662. This prevents a strong-baseline
  superiority claim. The candidate remains frozen with no parameter tuning.
- Pre-holdout final gate: 139 tests passed, Python compilation and
  `git diff --check` passed, and no holdout-prefix files existed. Recorded
  exact frozen code hashes and fixed 51--70 protocol/case list in
  `task_plan.md`; next action is the one-time holdout run.

## 2026-09-25 - Holdout Fading Completion and Author Confirmation

- Resumed from the three Markdown state files and verified the authoritative
  `version/v2` checkout. The older `lora_mesh` checkout has an unreadable Git
  tree; it was not modified.
- The user explicitly confirmed the English given-name-first author order
  `Zu Gao`, `Zhi Quan`. The current ICC TeX and existing five-page PDF already
  contain that exact order, with Shenzhen University affiliation.
- Polled the already-running seeds 51--70 `feedback_fading` session once; it
  exited 0 and wrote raw, summary, and report files. No rerun was started and
  no holdout result has yet been promoted into the manuscript.
- Next: complete the frozen static/short-TTL/isolated controls, audit raw
  evidence, revise and verify the PDF, then release to GitHub.
- Launched the three remaining frozen controls concurrently under unique
  suffixes with explicit `--case` and six `--protocol` selections where
  applicable. Live session IDs are static `90316`, short TTL `11946`, and
  isolated first discovery `53033`. The generalization runner overwrites
  outputs on rerun, so do not repeat a case without checking these sessions.
- Static and isolated sessions finished successfully; short-TTL is still
  running. A separate read-only agent independently recomputed fading
  holdout counts, matched application traces, candidate exposure, and paired
  confidence intervals from the raw CSV. The candidate improves over the
  old heuristic but is statistically indistinguishable from the matched
  PRR-product comparator. No paper edit has used these results yet.
- Asked the authors to confirm funding and conflicts of interest because
  the existing paper asserts none without verified author input.
- Independent static and isolated raw-CSV checks completed. Both support a
  null/uncertain calibrated ACK difference from the old method in those
  settings, and the isolated 480/480 candidate sets match. The short-TTL
  process completed after this check; none of the holdout cases should rerun.
- Selected Python for the paper figure under the user's earlier discretion,
  then found `matplotlib` missing in both local and bundled runtimes. Asked
  whether to install it in a project-specific virtual environment; figure
  work pauses until the answer. Paper-text analysis can continue.
- Updated the ICC Introduction, method scoring, and experimental-design
  sections to describe the frozen 2.1.24 policy split and exact holdout
  estimands. The first larger TeX patch failed an exact-context match without
  modifying source; a narrower patch succeeded. Results and abstract still
  carry 2.1.23 text and must be replaced before building or releasing.
- Short-TTL 51--70 control exited 0 and produced its raw CSV, summary and
  report; independent seed-paired audit is now in progress.
- Independent short-TTL raw-CSV audit passed: calibrated 30-s versus 600-s
  ACK difference -0.3043 [-0.3932,-0.2154], airtime +41.05 s
  [31.40,50.70], with matching traces and 793 unicasts per policy.
- Rewrote the ICC results, discussion, reproducibility, conclusion, and
  abstract around audited 2.1.24 evidence. The first pdfLaTeX build failed
  on missing Courier `pcrr7t.tfm` at one `\texttt` phrase; confirmed the
  cause and removed that optional formatting. The subsequent BibTeX build
  succeeded at five 10-pt Letter IEEEtran pages. PDF text and font checks
  passed, but visual QA found a sparse references-only fifth page; final
  layout and any new figure remain to be resolved.

## 2026-09-25 - Author Order and Final Layout Continuation

- The user confirmed the final given-name-first order `Zu Gao`, `Zhi Quan`.
  Source and rebuilt PDF already had that order; no name mutation was made.
- Corrected ETT wording (identical ranking, not identical numerical cost)
  and replaced an overstrong preregistration claim with `prespecified`.
- Used IEEEtran's reference trigger at [11] to balance final-page columns.
  Rebuilt with pdfLaTeX/BibTeX; all five pages were visually reviewed.
- A read-only audit recomputed the main manuscript numbers from frozen raw
  CSVs. Final full test suite: 139 passed; `git diff --check` and shell syntax
  pass. The root PDF is still stale 2.1.23 pending final content/layout.
- Next: add a compact secondary-metrics table from the existing 51--70 CSV,
  rebuild/review the PDF, then replace the root artifact and publish 2.1.24.
- Added Table V of descriptive fading diagnostics from the frozen CSV;
  independently checked row means and caveats. The final manuscript is five
  pages, with no overfull boxes or missing references, and the root PDF now
  matches the reviewed build (SHA-256 `42df9f02cf7c6306c32566fb18017a31d6906da89d984f7fc72c45084d6b6f72`).
- `python3 -m pytest -q`: 139 passed. `bash -n` and `git diff --check` pass.
  Next: stage only versioned 2.1.24 source/tests/evidence/paper/checkpoints,
  commit, push, update draft PR 1, and verify the remote head.
- Staged only 61 task files, excluding both untracked LaTeX build directories;
  staged whitespace check passed. Committed the release as `76b40429ed1b6511246c885001317c63fa9d3729` and pushed over SSH.
- Verified GitHub branch and OPEN/DRAFT PR 1 at that SHA, updated its title
  and body for the 2.1.24 evidence boundary, and confirmed the remote PDF
  Git blob matches the local file. A content API query without the branch
  reference returned 404 because the default branch differs; specifying
  `ref=version/v2` resolved it.
- The 2.1.24 repository release is complete. The only untracked paths are
  local PDF build intermediates. EDAS submission, funding/conflict statements,
  and any later Python-rendered figure require separate author decisions.

## 2026-09-26 - ICC Pre-submission Plan

- Resumed from the authoritative `lora_mesh_current_version_v2` checkout and
  read the existing plan/findings/progress checkpoints. `version/v2` is at
  `bc6b502`, matching `origin/version/v2`; no tracked edits were present.
- Read the planning-with-files and academic-paper plan-mode instructions.
- Started read-only parallel audits of experiment feasibility, manuscript
  evidence gaps, and official submission/overlap gates. No algorithm change,
  simulation rerun, or manuscript revision is authorized in this phase.
- Next: inspect runner options and existing results, then write and verify a
  deadline-ordered strengthening plan in repository Markdown.
- Inspected `docs/icc2027_experiment_plan.md`, the generic fairness probe,
  generalization and sensitivity runners, the prior random-pair report, and
  the ICC submission checklist. Found a no-algorithm-change CLI path for
  fresh random-pair comparisons, but not a directly comparable 2.1.24 SF
  sensitivity matrix from the existing sensitivity runner.
- Completed three read-only audits of experiment feasibility, paper evidence,
  and official submission gates. Prepared
  `docs/icc2027_pre_submission_strengthening_plan.md` with a frozen
  independent-seed random-pair contract, simulation-cell costs, result-based
  manuscript branches, deadline calendar, author-only gates, and recovery
  instructions. No simulation was launched and no manuscript/source code was
  modified in this planning phase.
- Independent scientific/CLI review found the first 8.25-km random-pair
  scene would mostly exercise saturated direct links and eliminate cache
  reuse. Revised P1 to a previously documented 18-km non-saturated
  random-per-flow stress stratum, explicitly not a one-factor cache test;
  separated null from adverse strong-baseline results and marked secondary
  contrasts exploratory. The repeated-pair generalization need is recorded
  as optional scoped implementation work, not implied by P1.
- Final plan review passed: the proposed CLI flags are supported, the
  2001--2020 cohort and output prefix are absent from inspected results,
  `git diff --check` passes, and the existing ICC PDF remains five Letter
  pages. Only this planning document and the three checkpoint Markdown
  files changed; unrelated untracked LaTeX builds remain untouched.
- Next execution phase, only after a new user request: confirm ICCT status
  and EDAS closing time with the authors, freeze the experiment contract,
  time a separate exposed-seed pilot, then run new seeds once if feasible.
  The plan is complete; no simulation, version bump, manuscript edit, commit,
  push, or EDAS action occurred in this planning turn.

## 2026-09-26 - Plan Completion Re-audit

- Ran the planning skill's session catchup, re-read the three root checkpoint
  files and full strengthening plan, and confirmed the authoritative
  `version/v2` worktree. `git diff --check` passed before this checkpoint.
- Independently verified ICC 2024/2025 official Technical Symposia language
  as "less than 40%" and rechecked the 2.1.24 manuscript's strong-baseline
  risk. The existing P1 contract includes ETX and flooding and is still
  explicitly future work, not a completed experiment.
- Only checkpoint Markdown was updated in this continuation. No paper,
  algorithm, simulation, version, GitHub, or EDAS action was taken.
- An independent completion audit confirmed the plan-only deliverable and
  identified overlapping P2 result branches; the plan now explicitly says
  to report simultaneous outcomes together. P1 execution and author-only
  submission checks remain future work.

## 2026-09-26 - Near-50% Strategy Intake

- Resumed from the three repository-root checkpoints and the published
  ICC strengthening plan. Read the academic-paper plan-mode and
  planning-with-files instructions, checked current branch/result state,
  and reverified the official 2026-10-02 deadline.
- Started independent read-only novelty, implementation-feasibility, and
  reviewer-bar audits. No simulation, paper edit, algorithm edit, or GitHub
  action has occurred in this planning turn.
- Wrote `docs/icc2027_high_confidence_submission_strategy.md` with G0--G4
  evidence gates, a six-day ICC 2027 go/no-go path, and a separate longer
  research path. Corrected the prior P1 plan to label its direct PRR as a
  static diagnostic and to predefine comparable chosen-path exposure.
- Two independent re-reviews identified and resolved an ungrounded mapping
  from gates to 50%, unfair path-attribution risk, an overly broad raw-trace
  claim, and missing independent-review time. No code, simulation, paper,
  PDF, version, GitHub, or EDAS action was taken in this turn.
- After context recovery, ran the planning catch-up with `python3` (plain
  `python` is unavailable), re-read the three checkpoint files and both ICC
  plans, and checked the current manuscript and frozen report. Updated the
  recovery notes for the two prespecified G2 claim options. The only intended
  changes remain local Markdown planning records; P1 and all author-only
  submission checks are still pending.
- An independent read-only statistical review found ambiguous +0.03 and
  cost-first pass criteria plus a route-attribution confound. Tightened both
  strategy documents: point target versus inferential lower bound, paired
  cost/noninferiority limits, and fixed-input score checks are now explicit.

## 2026-10-02 - ICC EDAS Submission

- Recovered the 2.1.24 worktree and read the previous checkpoints. Local time
  at intake was 15:47 CST. The official deadline was extended to 16 October
  2026; the exact EDAS clock remains to be checked.
- The user logged into the EDAS IoT symposium form and reported the ICCT
  submission was withdrawn or rejected. A read-only paper audit found a
  five-page format-compliant PDF but one internal TODO disclosure sentence,
  significant ICCT simulator-platform wording overlap, and a sparse final
  reference page. No EDAS certification, registration, or upload has occurred.
- Next: inspect and minimally correct the source, obtain factual author and
  disclosure confirmation, rebuild/verify the PDF, then continue EDAS.
- Revised only two ICC TeX sentences, compiled with latexmk into a fresh
  isolated `/tmp/icc2027_submission.xUkbbX` directory, and rendered/inspected
  all five pages. The compiled PDF has no fatal, undefined-citation, or
  overfull-box diagnostics. The repository root PDF has not yet been replaced;
  EDAS registration and upload remain untouched pending author facts.
- Confirmed the logged-in EDAS profile is Zu Gao at Shenzhen University and
  that there is no existing ICC IoT submission under this account. Prepared
  the registration form's title, abstract, and four topics but left the
  certification and submit button untouched. Waiting on coauthor email and
  author/disclosure confirmations.
- Replaced the tracked ICC PDF with the verified five-page build. The source
  and PDF now omit the internal TODO, and `pdftotext` confirms Zu Gao / Zhi
  Quan plus the corrected strong-baseline wording. Temporary and repository
  PDFs have identical SHA-256
  `26c67e1391dd6221927370ef725de064260ede310d6a927c3003a1415db2ad24`.
  No EDAS registration or PDF upload has occurred.
- The user asked to defer Zhi Quan's EDAS details until acceptance and to
  omit no-funding boilerplate. The PDF has no no-funding statement. Official
  ICC guidelines and EDAS author-change FAQs confirm that all authors must
  be entered at initial submission; the submission is paused before the
  certification/registration action until Zhi Quan can be added correctly.

## 2026-10-03 - ICC EDAS Submission Continuation

- The user supplied `zquan@szu.edu.cn`, confirmed no other overlapping paper
  is under review, and confirmed Zhi Quan agrees to the coauthor role.
- Verified that the MASS 2026 program lists the accepted MeshEcho poster as
  PD02 for 21 October 2026. The ICC manuscript now cites it as an accepted,
  not-yet-published poster and distinguishes its online Q-learning redundancy
  control from the ICC fixed route-score correction and new ACK-confirmed
  fading holdouts. The pre-existing packet-level harness is no longer claimed
  as a new standalone contribution.
- Recompiled and inspected all five pages of the ICC Letter/10-point PDF in
  `/tmp/icc2027-submit.6GnBLW`, confirmed embedded Type 1 fonts and no
  undefined citation or overfull box, and replaced the repository PDF with
  that build. `git diff --check` passes. Version remains 2.1.24 because this
  is a manuscript/citation correction, not a new simulation release.
- The logged-in EDAS ICC 2027 IoT form (`https://edas.info/N35508`) now holds
  the PDF title and abstract, plus the protocol, multi-hop IoT, and modeling
  topics and the uploader-as-author option. The policy certification is NOT
  checked, the paper is NOT registered, Zhi Quan is NOT added, and the PDF is
  NOT uploaded. Waiting for the submitting author to attest to the EDAS
  originality/author/attendance declaration before proceeding.
- The user then requested no MASS citation, saying it had not been submitted.
  A live refresh of their EDAS MASS 2026 paper #126 (`1571304744`) instead
  showed an uploaded manuscript, Zu Gao as author, reviews, and status
  `Accepted as poster`; its presentation status is not specified. ICC 2027
  guidelines do not explicitly require an unpublished poster citation, so
  the MASS paragraph and BibTeX entry were removed at the user's request.
  The replacement ICC PDF is again five Letter pages, visually inspected,
  with no MASS text, undefined citations, or overfull boxes. This removal
  does not establish that the MASS submission never existed or was withdrawn.
  ICC registration/certification/upload remain untouched pending a factual
  reconciliation of the MASS record and submitting-author declaration.

## 2026-10-03 - ICC Submission Resume After Reported MASS Withdrawal

- The user now reports the MASS poster was withdrawn and explicitly requests
  ICC submission. Reopened the submission plan, recovered the current dirty
  worktree without discarding any changes, and confirmed the no-MASS-citation
  ICC PDF is five Letter pages. Live MASS status, EDAS declaration, author
  registration, and PDF upload are the remaining gates; none is yet complete.
- Refreshed MASS EDAS paper `1571304744` at 11:14 CST; it still shows
  `Accepted as poster`, not withdrawn. Asked whether the organizer confirmed
  withdrawal and whether an IEEE CPS final file was submitted. The user's
  report may be true while EDAS has not yet updated, but the page does not
  independently confirm it.
- Verified the ICC IoT registration form remains filled but unsubmitted; its
  policy checkbox is unchecked. A separate "My papers and proposals" check
  showed no existing ICC IoT submission under this account. Independent PDF
  audit passed: five Letter/10-point pages, embedded fonts, exact title and
  Zu Gao / Zhi Quan order, no MASS citation, no visual/layout blocker.
- Asked the submitting author to confirm the EDAS certification and authorize
  checking it immediately before registration. No answer yet. Do not claim
  the paper has been registered, the coauthor added, or the PDF uploaded.
- The user then explicitly confirmed and directed registration without more
  questions. Checked the EDAS declaration and registered the paper in ICC
  2027 IoT & Sensor Networks. EDAS created paper `1571361802`, title
  `MeshEcho: Confidence-Aware Route Selection for LoRa Mesh IoT`, with Zu Gao
  as the sole listed author so far. EDAS status is `Pending (no manuscript)`;
  coauthor addition and manuscript upload are still required.
## 2026-10-03 - Baseline-Centered ICC Manuscript Revision

- User requested revising the ICC paper around current MeshEcho versus
  Meshtastic-like and MeshCore-like, not old MeshEcho as the lead comparator.
- Read the academic-paper, planning-with-files, and PDF workflows; ran
  planning session catch-up. Current worktree is dirty with prior paper,
  checklist, and checkpoint edits; preserve them.
- Reproduced one saved 2.1.24 calibrated holdout seed in memory, then reran
  20 same-seed Meshtastic-like and MeshCore-like cases without writing files.
  The script's first pass used a nonexistent `observed_unicast_flows` key;
  inspection of the CSV/schema showed the correct field is `unicast_flows`.
  The corrected run passed trace-hash and denominator checks and yielded the
  values recorded in `findings.md`.
- Next: version durable three-way data, add a separate unconditioned case,
  revise LaTeX with balanced metrics and model limitations, compile/render,
  and verify. EDAS is untouched.
- Generated 2.1.25 repeated-fading CSV, summary CSV, and report for calibrated
  MeshEcho, Meshtastic-like, MeshCore-like, and matched-fallback PRR-product;
  the script completed successfully. A separate numerical audit is pending.
- Independent raw-CSV audit passed 80-row completeness, duplicate-key,
  denominator, trace, count-derived PDR, and 2.1.24 identity checks. Paired
  intervals for ACK, destination, aggregate airtime, and modeled energy are
  recorded in `findings.md`.
- Started a fresh unconditioned random-pair, 6-dB block-fading comparison on
  seeds 2001--2020 with the same four policies. Process is still running;
  output/interpretation not yet available at this checkpoint.

## 2026-10-03 - 2.1.25 Continuation

- Resumed from the three root Markdown checkpoints and preserved all existing
  worktree changes. The random-pair run completed, and an independent raw-CSV
  audit passed 80-row/20-seed completeness, matched traces/denominators, and
  count-derived PDR checks; key results are in `findings.md`.
- `VERSION` and four ICC experiment default prefixes now say `2.1.25`; the
  targeted release-metadata test passed. The paper, references, and PDF still
  need revision.
- Next exact action: test/fix missing fading flags in the report reproduction
  command, regenerate its Markdown only, then revise the ICC TeX with both
  baseline scenarios and explicit negative findings. EDAS remains untouched.

## 2026-10-03 - 2.1.25 Verified And Published

- Added a failing test for the missing temporal-fading report flags, fixed
  `write_report()`, and passed the focused test. Patched the existing
  random-case Markdown reproduction command without rerunning the CSV.
- Rewrote the ICC manuscript and official-protocol citations. Retained
  author order Zu Gao, Zhi Quan; removed old MeshEcho from the central
  comparison. The main tables cover both workloads and a matched-recovery
  score control. A new figure was not drawn because the figure workflow
  requires a user-selected Python or R backend; no mock or substitute figure
  was created.
- Rebuilt and visually inspected all five PDF pages; all fonts are embedded,
  no overfull or undefined-reference warnings remain, and the root PDF
  matches the build artifact byte-for-byte (SHA-256
  `fe2899dbbeec32e42428e5883e8baccf0058b76a897375eb58be44a12269cbd4`).
- `python3 -m pytest -q`: 140 passed. Staged diff whitespace check passed.
  An independent numerical audit of the two four-policy CSVs verified seed
  coverage, shared traffic hashes and denominators, and paired differences.
- Committed 20 selected release files as `0d3d72497ff9d442a29b7f1318112417aa49d032`,
  pushed `version/v2`, verified the GitHub branch points to the same SHA,
  and updated draft PR 1 to
  `[codex] MeshEcho 2.1.25 protocol-family comparison`.
- Left unrelated/unpublished user strategy drafts and old/new build folders
  untouched. The three root checkpoint Markdown files remain local dirty
  state for recovery. EDAS was not changed; ICC paper `1571361802` remains
  `Pending (no manuscript)` with only Zu Gao listed so far.

## 2026-10-03 - 2.1.26 Baseline Presentation Continuation

- Re-read the three root checkpoints and current TeX/PDF, verified current
  remote `version/v2` is `0d3d724`, the five-page PDF SHA-256 matches the
  2.1.25 record, and 140 tests pass. Existing unrelated dirty files and build
  directories remain untouched.
- An independent audit identified a material naming ambiguity: the evaluated
  CSV row is optional `meshecho-calibrated`, whereas the paper's `MeshEcho`
  shorthand could be read as default `meshecho`.
- Chose Python for the previously delegated comparison figure. Confirmed
  Matplotlib/SciPy absent from system and bundled Python, then installed them
  only into an isolated `uv` run environment; versions are 3.11.2/1.18.1.
- Next: red/green test for traceable three-protocol figure data, generate
  figure, clarify policy identity, update 2.1.26 metadata, compile/QA, run
  simulator smoke and tests, then publish selectively.

## 2026-10-03 - 2.1.26 Verification Checkpoint

- Added a test-first Python chart generator and figure-source CSV. The
  first two focused tests passed after red/green implementation; the vector
  export test passed in the isolated Matplotlib environment. Figure PNG was
  viewed at full size and the final PDF chart was viewed on page 5.
- Revised the manuscript to map its shorthand explicitly to optional
  `meshecho-calibrated`; title and author order are unchanged. Added the
  three-model delivery figure while keeping PRR+fb in the full tables.
- Advanced VERSION, new-run CLI prefixes, release test, README, comparison
  note, changelog, and checklist to 2.1.26 without changing frozen CSVs.
- First LaTeX build failed on missing Courier metric `pcrr7t` for a new
  `\texttt`; replaced it with ordinary quoted text. Final build succeeds:
  5 pages, Letter, 10-point IEEEtran; SHA-256
  `25bf5d25c70816c457640f232c2e657ba546e4d3f4d420c053824af11eb8443a`.
  No overfull or unresolved-reference warning. All pages visually inspected.
- `python3 -m pytest -q`: 142 passed, 1 skipped. The isolated Matplotlib
  focused suite: 3 passed. Python compilation and `git diff --check` pass.
- One-seed feedback-fading simulator smoke with all four policies wrote
  only to `/tmp/meshecho-2_1_26-smoke.OXhks1/` and matched every seed-51
  frozen raw CSV field. Existing project CSVs were not overwritten.
- Next: receive independent audit, selectively stage/commit the 2.1.26
  changes while leaving unrelated dirty files/build directories untouched,
  push `version/v2`, update PR 1, verify remote state.

## 2026-10-03 - 2.1.26 Release Candidate

- Independent review verified all chart means/intervals and five-page layout;
  it caught a clean-checkout blocker because global `*.pdf` ignored the new
  figure PDF. Added a narrow exception and confirmed Git stages that asset.
- The first staged whitespace check failed on generated SVG trailing spaces
  and CRLF chart-source CSV. Added a red/green export-format test, normalized
  both outputs in the generator, regenerated assets, and passed
  `git diff --cached --check` and SVG XML parsing.
- The final root/build PDF SHA-256 is
  `25bf5d25c70816c457640f232c2e657ba546e4d3f4d420c053824af11eb8443a`.
  It is still five Letter pages. Its fifth-page PNG is byte-identical to the
  prior reviewed candidate's fifth-page PNG.
- Only 19 related files are staged; pre-existing strategy drafts, root
  checkpoint Markdown, and all build directories remain unstaged.
- Next: rerun final tests after export normalization, commit, push, update
  PR 1, and verify remote clean-checkout figure inclusion.

## 2026-10-03 - 2.1.26 Published

- Final suite after export normalization: 142 passed, 1 skipped with system
  Python; Matplotlib 3.11.2 figure suite: 3 passed. Staged whitespace check
  passes.
- Committed 19 selected files as
  `78ffb6ebf33d5dc51eaf65057321c76c8ab5391e` and pushed `version/v2`.
  GitHub API confirms the same branch head; draft PR 1 title/body now
  describe 2.1.26 and retain the EDAS-pending warning.
- Verified the remote figure PDF blob SHA matches the local committed SHA.
  Extracted only committed `paper/icc2027` files with `git archive`; fresh
  `latexmk` compilation succeeded to five Letter pages, without overfull
  or unresolved-reference warnings.
- Root PDF SHA-256:
  `25bf5d25c70816c457640f232c2e657ba546e4d3f4d420c053824af11eb8443a`.
  Unrelated local edits and build outputs remain untouched/uncommitted.

## 2026-10-03 - Distinct MeshEcho Variant Research

- Classified the prior turn as substantive research progress: it located
  the discovery/cache bottleneck, fixed-32-byte airtime assumption, and
  product mechanisms that invalidate flood-first caching as novelty.
- Rechecked current Git state and resumed the existing planning files using
  the planning-with-files catch-up script. No source, experiment, paper, PDF,
  GitHub, or EDAS mutation has occurred in this goal turn.
- Two independent read-only audits are underway: product/prior-art
  differentiation and simulator feasibility/alternative design.
- Next: synthesize a policy with device-local inputs and an explicit
  falsification comparison, then decide whether to implement a prototype.

### Continued Research Checkpoint

- The user refined the objective to a genuinely distinct algorithm and named
  nRF52/ESP32-S3 as deployment targets; ML/TinyML is optional.
- Re-read the academic-paper-reviewer and planning-with-files skill
  instructions, ran planning session catch-up, and verified `version/v2` is
  at `78ffb6e` with only pre-existing dirty Markdown/strategy/build files.
- Confirmed the latest manuscript's random and recurring protocol contrasts
  and the simulator's fixed 32-byte packet accounting. Independent read-only
  audits are refining a source-local F/R/D rule and challenging its novelty.
- Next: inspect packet/event API, settle a deterministic device-feasible
  algorithm, write a standalone research specification, and define tests and
  falsification gates. No code, experiment, paper, PDF, GitHub, or EDAS action
  has occurred during this continuation.
- Inspected simulator packet, send, receive, ACK, and timeout hooks plus the
  ESP32 firmware's fixed-array Q-learning controller. The first proposed D
  trigger was only post-loss; independent audit corrected it to an aging-
  route shadow refresh with ACK-gated promotion and a hard discovery budget.
  Firmware/hardware source parity for nRF52 and ESP32-S3 is still unverified.
- Wrote `docs/research/meshecho_shadow_refresh.md` as a research proposal
  with F/R/D state machine, validity gates, prior-art boundaries, and device
  constraints. Corrected the nRF52840 artifact claim: the manifest is
  planned with no flashable files; the current C++ target is `esp32dev`, not
  ESP32-S3. Added a separately measured cold-D branch for repeated F ACK
  misses. No simulator, firmware, manuscript, or EDAS modification occurred.
- A read-only red-team review caught a source-versus-destination route
  selection error in the new research brief. Corrected it to the existing
  destination-collected RREQ candidate set and one returned RREP, with
  matched PHY-aware discovery deadlines. The source only chooses F/R/D.
- Completed the independent novelty, simulator, and embedded-feasibility
  reviews. Revised the research brief to disclose D's current-packet risk,
  require a same-trigger age-gated F comparator, distinguish standardized
  source confirmation from product-native ACKs, fix route-age/TTL/eviction
  rules, and require paired reliability/airtime gates. The fallback to a
  separate PROBE/ACK design was considered but deferred as a higher-cost,
  longer-term variant; it is not represented as tested.
- Final research outcome is the standalone MeshEcho-SR specification, not a
  validated algorithm or an ICC manuscript change. `git diff --check` and
  trailing-whitespace checks pass. Only the new research Markdown and the
  three existing checkpoint files were edited in this continuation; all
  pre-existing dirty strategy files and build directories remain untouched.

## 2026-10-03 - SR Simulation and Manuscript Revision Intake

- The user requested a major ICC paper revision and new simulations based
  on the MeshEcho-SR research specification. The previous research turn is
  classified as progress, not completed implementation.
- Ran planning session catch-up, read the current SR specification and ICC
  source, and verified `version/v2` still points at `78ffb6e`; the worktree
  has existing uncommitted strategy/checkpoint Markdown and LaTeX builds.
- Read the planning-with-files, TDD, academic-paper revision, and PDF skill
  instructions. The paper remains five-page 2.1.26 calibrated-MeshEcho
  evidence; SR is unimplemented and has no results yet.
- Started one agent on test-first variable-length packet airtime and one
  read-only agent on the SR experiment contract. A third spawn hit the
  concurrency limit; the root will inspect paper structure directly.
- Next: freeze the experiments and paper evidence map, inspect simulator
  hooks/tests without editing the airtime-owned code, then implement SR
  after packet-cost work is integrated. No paper, PDF, GitHub, or EDAS edit
  has occurred in this new goal yet.

## 2026-10-03 - SR Prototype Progress

- Packet-cost agent implemented frame-length-aware ToA/energy/overlap and
  fallback timing in `lora_mesh_sim.py`, with `tests/test_packet_airtime.py`.
  Its focused 68 tests passed; root independently ran full pytest before SR
  edits: 147 passed, 1 skipped, plus clean `git diff --check`.
- Root added `tests/test_meshecho_sr.py` in vertical red/green slices and
  registered four SR mechanism policies in `lora_mesh_sim.py`. Eight SR tests
  currently pass for first F/ACK cache, R reuse, pre-failure D, D failure
  fallback, R miss-triggered F, cold D, same-trigger variants, and periodic
  refresh without repeated-demand gate.
- Read-only contract and manuscript architecture reviews completed. The
  runner agent is building isolated SR simulation output/paired inference.
  Next exact code actions: deadline/late ACK and RREP-loss tests, bounded
  destination state, full regression suite, runner integration. Do not use
  old 2.1.26 paper numbers as new SR evidence; no new simulation matrix,
  manuscript edit, version bump, push, or EDAS action has occurred yet.

## 2026-10-03 - Recovered SR Work and New User Question

- Resumed from the 2.1.26 `version/v2` checkout, re-read all three project
  checkpoint files and Git status, and ran the planning catch-up helper.
- Reviewed the current ICC LaTeX and SR research brief. The published paper
  is still the five-page calibrated-score comparison; it does not contain SR.
- The SR runner agent completed a tiny paired smoke and 14 focused runner
  tests; no full development/holdout run has occurred.
- The independent validity audit found premature failed-discovery fallback
  and pre-transmission ACK-miss timing. Root will add reproducing tests and
  fix these in separate red/green slices before trusting any SR numbers.
- The user's improvement question prompted an algorithm comparison: useful
  DATA flooding at the same age/demand trigger may be stronger and cheaper
  than RREQ/RREP shadow refresh. No acceptance-rate claim is warranted yet.

### Development-Only Validation Update

- Added failing reproductions for destination-side oracle fallback and
  pre-transmission ACK-miss timing, then fixed them in the SR source path.
- Integrated the two common-ACK product-inspired controls into protocol
  construction and CLI names. Added a late-ACK-before-application-deadline
  test and a queued-TX test; both controls now match SR's 30-s application
  confirmation boundary while retaining a 15-s route timeout guard.
- Ran the 20-seed SR recurring-fading development matrix (80 policy-seed
  runs). Positive paired ACK effects did not clear the predeclared +10%
  airtime CI upper-bound criteria, and periodic D matched SR exactly.
- Independent read-only timing audit found that the current 2-s source-started
  destination collection window suppresses typical four-hop candidates and
  has no source-timestamp wire support. Do not open the holdout or rewrite
  the paper until this model contract is corrected and development rerun.
- Latest verification: `python3 -m pytest -q` gives 185 passed, 1 skipped;
  `git diff --check` passes. No version bump, GitHub push, PDF rewrite, or
  EDAS action was performed in this continuation.

## 2026-10-03 - Updated Core-Algorithm Goal Intake

- The user explicitly added core-algorithm rewriting to the persistent SR
  simulation and ICC manuscript goal. Classified the previous turn as real
  progress (code fixes, 20-seed development evidence, model-validity audit)
  rather than completion.
- Re-read checkpoint Markdown and Git status in the v2 checkout; the branch
  remains `version/v2`, with the prior dirty files and exploration outputs
  preserved. Planning catch-up completed without an unsynced report.
- Delegated a bounded TDD discovery-timing fix in the simulator and a
  separate read-only controller-design review. Root is analyzing the
  development trace and preparing the new decision/evaluation contract;
  holdout seeds remain unopened.

### Controller Rewrite Clarification

- Confirmed the active goal is a new source decision algorithm, not further threshold tuning of SR. The existing F/R/D packet and ACK machinery is reusable infrastructure, while the fixed-age/2-send selection rule must be replaced and retained as an experimental comparator.
- The independent controller review proposed a measured-margin and packet-cost gate; root is checking on-wire feasibility and fairness before implementation. A separate agent is fixing discovery timing test-first. No holdout run, paper rewrite, version bump, GitHub push, or EDAS action has occurred for this goal.
- Corrected the bibliography-location error in the plan: the ICC source uses `paper/icc2027/references.bib`.
- Added `docs/research/meshecho_mag_design.md` with a source-observable margin/airtime-gated decision and explicit falsification controls. Added the first packet-field regression in `tests/test_meshecho_mag.py`; it fails as expected because `Packet` has no margin field yet. The timing agent still owns a separate simulator region, so root has not edited simulator code concurrently.
- Independent feasibility audit confirmed source-feedback, byte-accounting, and bounded-state caveats; recorded them in `findings.md`. Discovery timing's targeted suite passed, while its full regression exposed a separate native source-wait mismatch that the timing agent is correcting. No new controller matrix or holdout has run.
- Discovery timing agent completed a PHY/hop-aware collection and source-wait fix, including native-control queue expiry. Its pre-MAG suite was 191 passed, one skipped. Root then completed five MAG behavior tests in red/green steps: optional field/byte charge; two-hop F and R margin ACK return; prefailure D on ACKed low margin; lost-ACK feedback isolation; and slow-PHY deadline fallback to F.
- Root's first full regression after those slices: `python3 -m pytest -q` 196 passed, one skipped in 20.96 s. `git diff --check` and `py_compile` pass. No corrected development matrix, holdout, manuscript rewrite, version bump, GitHub push, or EDAS action has occurred.
- Added matched MAG F/R-only, same-trigger F, and equal-token periodic D modes; added an out-of-order ACK regression and rejected stale margin samples. The runner now recognizes MAG's positive deadline and limits confirmatory flags to MAG versus its two primary matched controls on the holdout. Full suite before development: 202 passed, one skipped; static checks passed.
- One recurring-fading smoke seed (3001) produced 37 scheduled unicasts per policy. MAG ACK PDR 0.730 / TX airtime 39.17 s / four D decisions; F/R-only 0.757 / 22.03 s / zero D; same-trigger F 0.541 / 50.64 s; periodic D 0.865 / 35.93 s. This single-seed diagnostic cannot support a population claim and raises an airtime concern.
- Ran the complete corrected-timing MAG development matrix: 20 seeds x four policies, 80 runs, 798 scheduled unicasts per policy. Wrote raw run, paired, flow, action, and manifest evidence under `results/meshecho_mag_research_recurring_fading_dev_20261003.*` without touching holdout seeds.
- Development gate failed MAG versus F/R-only on airtime (+32.1%, upper 95% CI +40.5% versus +10% allowed), despite +0.135 ACK PDR gain. MAG beats same-trigger F on the development gate but ties periodic D in ACK and costs more. No manuscript, PDF, version, GitHub, or EDAS change followed these numbers. Next action: test-first revision of rejected-risk action from F to R, then a separately named development replay and decision; keep holdout closed.
- Development revision 2 changed only rejected-risk F to R; 203 tests passed, one skipped. The replay reduced mean MAG airtime to 43.89 s but still failed the F/R cost upper bound (+13.2%, CI upper +21.6%) while ACK gain was +0.139. No holdout was opened.
- Added a test-first route-length-bounded RREQ hook for MAG and its periodic control. First patch accidentally matched MeshCore's method; restored MeshCore and targeted the CalmMesh hook. The new TTL test plus matched discovery tests pass (9 tests). Next: full regression and dev3 matrix under a distinct prefix; stop algorithm tuning if the predeclared gate still fails.
- Ran full regression after TTL cap: 204 passed, one skipped; static checks passed. Completed the separate 20-seed dev3 matrix and preserved run, paired, flow, action, and manifest files. MAG vs F/R-only gives +0.156 ACK PDR [0.107, 0.205] but +5.0% airtime [-2.7%, +12.8%], so the +10% 95% upper-bound gate still fails. Holdout 4001--4040 remains untouched.

### 2026-10-03 Active-Goal Resume

- Classified the prior turn as progress: read-only algorithm/evidence review
  established that the core route-acquisition mechanism must change for a
  stronger method paper; no code or paper file was changed in that turn.
- Recovered the dirty `version/v2` worktree and all three checkpoint files;
  `session-catchup.py` reported no unsynced context. No files were cleaned or
  reverted. The current five-page paper and release remain 2.1.26.
- Read the `academic-paper` revision, `tdd`, `planning-with-files`, and `pdf`
  skill contracts. The paper revision must follow evidence; behavior changes
  will use one red/green test slice at a time. PDF authoring has not started.
- Started independent read-only protocol-design and experiment audits. Next:
  resolve a single wire/action contract and falsification plan, then write
  the first failing behavioral test. Do not open holdout seeds 4001--4040.
- Completed independent design and experiment audits; verified the 49/71 and
  46/66 single-insertion counts directly from the dev3 JSONL with `jq`.
  Added `docs/research/meshecho_lpr_design.md` as a provisional, falsifiable
  source/packet/relay/ACK/experiment contract. Next action: first red test
  for ACK-carried weakest-hop index and its byte cost, followed by minimal
  implementation. No holdout, paper, PDF, version, or remote change yet.
- First vertical TDD slice: added an end-to-end two-hop ACK test for the
  weakest successful forward-hop index and its one-byte wire cost. Initial
  red was unknown `meshecho-lpr`; the first implementation exposed a second
  red at the CalmMesh flood packet-copy path (ACK index `None`). Patched that
  copy path; the focused test and full regression still need rerun.
- First TDD slice is green: the two-hop ACK carries the weakest successful
  forward-hop index, with one modeled byte charged. Full regression after
  this slice: 205 passed, 1 skipped. Wrote the next red test for useful
  local P DATA at an ACK-indexed risky edge with no RREQ/RREP; implementation
  remains pending.
- Second TDD slice is green: a risky confirmed edge selects P, sends the
  current DATA to the predecessor, broadcasts it once locally, and receives
  an ACK without RREQ/RREP. The initial test fixture tied both hop margins;
  corrected it to make the intended second edge uniquely weak.
- Third TDD slice is green: a five-node deterministic diamond blocks the old
  weak edge; an off-path node with a recent decoded successor transmission
  relays the payload once, and the source commits the inserted path only after
  its ACK. The first implementation uses an eight-entry passive neighbor LRU
  and a bounded 128-flow target duplicate list. Full regression: 207 passed,
  1 skipped; Python compile and `git diff --check` pass. This is mechanism
  feasibility, not a population result or finalized memory proof.
- Started an independent read-only safety review. Next TDD slices: lost/late
  and malformed ACK refusal, source-origin P timer, candidate suppression,
  stale-neighbor gating, then matched controls and a fresh-development runner.
  Holdout 4001--4040 remains unopened; manuscript/PDF/version/remote unchanged.
- Stopped further tuning of this F/R/D design on development seeds. No ICC source/PDF, release version, GitHub branch, or EDAS action was changed. Next safe research step requires a separately specified low-overhead discovery/data-probe mechanism and fresh evidence; do not silently convert development results into submission claims.

### 2026-10-03 LPR Safety Continuation

- Classified the previous turn as progress because the independent protocol
  review exposed concrete defects and changed the next safe action.
- Re-read the three project checkpoint files and LPR design in the dirty
  `version/v2` checkout; `session-catchup.py` found no unsynced context.
- Read the TDD, systematic-debugging, and planning-with-files instructions.
  The focused LPR suite reports four passing tests, including source-origin
  PATCH timeout behavior; no full-suite rerun followed that fourth slice.
- Delegated the relay-cancellation test/fix and a separate read-only runner
  audit. An additional literature-agent request was rejected at the thread
  limit, so the root agent retains that audit. No new development/holdout
  simulation, manuscript, PDF, version, GitHub, or EDAS action yet.
- Added `tests/test_meshecho_lpr_safety.py`: wrong-origin P ACK and missing P
  route-cache hit each failed before a one-line fix in `lora_mesh_sim.py` and
  passed afterward. The focused two-test safety run is green; the relay agent
  is concurrently editing distinct LPR receive/cancellation code.
- Runner audit identified incompatible unwindowed packet counts and missing
  LPR control/seed/freeze support. A bounded follow-up agent is adding only
  window-consistent packet-kind metrics and tests; no LPR matrix has run.
- Independent relay agent completed cancellation and accounting tests (then
  8 LPR tests passed); the runner agent completed windowed per-kind packet
  counters with 19 runner tests and 215 overall tests at its checkpoint.
- Added red/green source-index release tests for accepted P ACK and missing
  P ACK past the application deadline. Added red/green assertions that
  canceled and committed relay handles leave no pending-map entries. The 10
  focused LPR tests pass after these changes. Next: full integrated suite,
  runner schema review, then test-first matched LPR control policies.
- Full integrated suite after safety and runner metric work: 216 passed,
  1 skipped; `py_compile` and `git diff --check` passed.
- Wrote exact LPR control definitions into the research contract and delegated
  their test-first simulator implementation. Root added runner suite/seed
  selection, a full-suite guard, complete case-config pairing hashes,
  existing-artifact refusal, and an under-20-seed non-evaluable gate through
  separate red/green tests. No LPR population run, holdout, paper, version,
  GitHub, or EDAS action followed.

## 2026-10-03 - Clarifying the Core Rewrite

- Re-read the three checkpoint files, LPR contract, current simulator/runner,
  and Git status after continuation. The current ICC release is still 2.1.26.
- LPR and its four matched controls are integrated; a fresh full run reports
  229 passed, one skipped in 21.23 s, with clean `git diff --check`.
- Corrected the research-contract status from unimplemented to simulator
  prototype. The algorithmic contribution remains unvalidated by population
  evidence; no LPR development or holdout run, ICC edit, version bump, push,
  or EDAS submission has occurred.
- Two read-only audits are checking the core novelty/safety and experiment
  eligibility gates. Next: add exact LPR freeze and joint-comparator checks
  test-first, then a custom smoke and fresh development matrix only.
- Added a failing four-flow regression for P-ACK feedback freshness. It
  reproduced an unnecessary F at 321 s after a successful P repair; a
  one-line timestamp update now yields the expected R. Focused LPR tests:
  17 passed; static whitespace check passes. Full suite awaits runner edits.
- Frozen a pre-development exposure sufficiency rule in the LPR research
  contract. Runner guard work is in progress; one negative deadline test
  briefly entered a 20-seed development call before being stopped, with no
  artifact written and no holdout seed used. Further guard tests mock the
  per-run entry to prevent accidental population runs.
- Independent prior-art audit found a close local-repair precursor, Bypass
  Routing (2006), plus AODV-BR/NSR/ExOR. Added a conservative novelty boundary
  to the LPR contract. No literature claim or new result has been inserted
  into the ICC manuscript.
- Added a late P-ACK regression that injects a captured ACK just after the
  30-s application deadline but before source-index cleanup; it passes and
  confirms no late flow acknowledgment or route commit. No simulator change
  was needed for this boundary.
- Runner freeze/preflight work completed test-first in its owned files;
  parent integration reported 248 passed, one skipped before exposure fields.
  A new run-row test failed on the missing `repair_decisions` field, then
  passed after adding P, inserted-route, switch, and collision counts.
  A separate holdout test failed because a zero-P synthetic development
  bundle reached simulation; it passed after adding the predeclared
  20-P/10-inserted-route sufficiency guard. Focused tests are green; full
  integration and any LPR population run remain next.
- Full integrated suite after exposure fields: 250 passed, one skipped;
  Python compile and `git diff --check` pass. Ran only custom seed 5000
  with all five LPR policies, storing runs/paired/flows/actions/manifest at
  `results/meshecho_lpr_smoke_seed5000_20261003.*`. All four artifact SHA-256
  values match the manifest. LPR triggered P three times but committed no
  inserted path; this smoke cannot support a benefit claim. Next: run the
  frozen 5001--5020 development matrix once under a new output prefix.
- Ran the exact 20-seed/five-policy LPR development matrix once to completion
  under `results/meshecho_lpr_research_recurring_fading_dev_20261003.*`.
  Verified 100 run rows, 834 common flows per policy, matching per-seed
  trace hashes, and four artifact SHA-256 values against the manifest.
  The joint primary reliability/airtime gate is false; only seven of 69 P
  decisions produced ACK-committed inserted paths. Recorded the negative
  outcome in `docs/research/meshecho_lpr_dev_results.md`. No holdout,
  manuscript, PDF, VERSION, GitHub, or EDAS action followed.

## 2026-10-03 - New Core-Mechanism Intake

- Classified the previous turn as substantive progress: a complete LPR
  development matrix, failed predeclared gate, frozen artifacts, and a
  corrected route-repair/ACK timestamp bug changed the next algorithm
  decision. The active goal remains full core rewrite, credible simulation,
  and only then a major ICC paper revision.
- Re-read planning, TDD, and academic-paper skill instructions, ran planning
  catch-up, and inspected dirty `version/v2` worktree, all three checkpoint
  files, LPR contract, code, and frozen development outputs. The current
  paper/release remain 2.1.26; no source, result, or manuscript mutation
  occurred during recovery.
- Rejoined frozen LPR action/flow logs. Among 69 P decisions, 52 got ACK,
  11 delivered without ACK, six did not deliver; only seven of 52 ACKed P
  flows committed an inserted path. A read-only forensic agent is checking
  details and a separate design audit is examining a new device-local
  mechanism. No 4001--4040 holdout was opened.
- Extended the development-only diagnosis by F/R action and reason. F
  delivered without ACK 155 times out of 288 decisions, whereas R had 25
  destination-only deliveries but 170 no-delivery failures. This focuses
  candidate redesign on ACK-confirmed DATA-first route acquisition, while
  preserving that R still needs forward-route failure handling. No new
  simulation was run and no positive result was inferred.

## 2026-10-03 - Post-LPR Algorithm Redesign Continuation

- Classified the preceding answer/forensic work as progress: two independent
  read-only audits identified route-repair outcomes, FLOOD duplicate-path
  suppression, and a queued-relay cancellation boundary that change the
  next algorithm decision. Re-read all three recovery files; `python3`
  planning catch-up completed. The initial `python` catch-up command failed
  because this shell has no `python` executable.
- Re-read planning, systematic-debugging, TDD, and academic-paper skill
  instructions. Existing ICC paper and VERSION remain 2.1.26. No new
  simulation, holdout, manuscript, release, GitHub, or EDAS action yet.
- Next exact action: reproduce the queued PATCH_RELAY cancellation boundary
  through the simulator's public flow path and add observability for each
  candidate/ACK stage. Use that evidence to freeze one separately named
  core-algorithm hypothesis and fresh development seeds before implementation.
- Independent read-only audits converged on a DATA-first dual-path ACK
  hypothesis. Passive diagnostics on already-seen 5001--5003 found 37 F
  flows with a second distinct destination path 0.228--1.974 s after the
  first; instrumentation left unmodified and instrumented run/flow/action
  outputs exactly equal. This is exposure, not an expected success gain.
- Wrote `docs/research/meshecho_dpa_design.md` before code: 3-s local
  window, at most one alternate ACK, first-path retransmission control,
  single-ACK control, fresh 6001--6020 development, and explicit joint
  ACK/airtime and exposure gates. No holdout or paper modification.
- Added three vertical red/green integration tests and minimal DPA class/
  factory support: actual two-branch FLOOD yields two distinct reverse ACK
  paths, same-trigger repeat uses the first path, and single-ACK F/R sends
  one. `python3 -m pytest -q tests/test_meshecho_dpa.py`: 3 passed. Next:
  late/duplicate/capacity/source safety tests, full regression, runner.
- Added a failing late-path/state-expiry test, then a destination-local
  cleanup timer; added a failing nine-flow capacity test, then oldest-window
  eviction at eight active windows. Focused DPA suite: five passed. Full
  repository suite: 255 passed, one skipped in 20.93 s; `git diff --check`
  passes. No fresh development, holdout, ICC source/PDF, version, remote,
  or EDAS changes. Next exact action: same-first-hop/third-path and source
  duplicate-ACK safety tests, then runner integration with 6001--6020 only.
- Added one red/green `dpa_second_path` action-event slice for the runner's
  mechanism exposure count. Added passing real-packet tests for rejecting
  a different path with the same source-adjacent hop, limiting a third
  distinct path to two ACKs total, and recovering from a first-path ACK
  failure through the second realized path while the two controls fail.
  These are deterministic feasibility/safety cases, not population results.
- Delegated DPA runner/holdout-gate integration to a separate agent owning
  only `tools/run_sr_experiment.py` and runner tests; root retains simulator
  and protocol tests. No DPA development or holdout simulation has run.
- Added a failing synthetic malformed-path test: an ACK was emitted for a
  FLOOD whose claimed path began at node 9 while `origin=0`; fixed by
  requiring source/path identity. A separate failing looped-path test then
  drove a distinct-node check. Same-first-hop and third-path real-reception
  tests passed without implementation changes. Focused DPA suite: ten
  passed. Next: source ACK validation, full regression, and runner gate.
- Added a wrong-origin F ACK integration test; it failed by confirming an
  invalid route, then passed after a DPA-local source-origin check shared by
  all three arms. Focused DPA suite: 11 passed. A `list_agents` status call
  failed to parse its arguments and had no repository effect; continue with
  direct agent messages rather than repeating that call.
- Added CLI choices for all three DPA arms after a red argparse test.
  Passing safety tests now confirm first ACK commits once, later ACK cannot
  overwrite, and a second ACK after the 30-s application deadline does not
  confirm. Added red/green first-path, second-path, actual destination ACK
  TX, and source ACK RX audit events. Source RX records both physical
  overhearing and on-path arrival, with separate `on_path`/`accepted` fields.
  Focused DPA suite: 14 passed. No population result, ICC rewrite, version
  bump, GitHub push, or EDAS change.
- Added a red test for an ACK whose path ends at a different node despite a
  correct destination `origin`; DPA now requires source/destination endpoints
  to match the registered flow. Focused suite: 15 passed. Python compilation
  and whitespace check pass. Independent prior-art check found DSR and AOMDV
  conceptual overlap; recorded a conservative novelty boundary in the DPA
  contract. Runner integration remains in progress; no fresh DPA matrix run.
- Re-read the academic-paper mode and workflow references while waiting for
  runner integration. The existing five-page ICC manuscript calls for a
  revision-mode evidence map, but no abstract/results/conclusion rewrite is
  justified until a frozen new algorithm passes development and holdout.
- Re-read the planning, TDD, and systematic-debugging instructions after
  context recovery. Reviewed current DPA code and runner contract.
- Reproduced the malformed first-path ACK defect in a real-packet test,
  then validated the destination's realized path before inherited delivery.
  Added an actual-last-sender regression; all 17 DPA tests pass.
- Full regression: 294 passed, one skipped in 21.34 s. Python compile and
  whitespace check pass. Runner agent reports 72 focused runner tests pass.
- Next exact step: run a seed-6000 DPA smoke, inspect artifacts, then run
  the frozen 6001--6020 development matrix only if the smoke is coherent.
- Seed-6000 DPA custom smoke completed: all three arms have 35 scheduled
  unicasts and identical scheduled-trace hashes; DPA logged nine eligible
  second-path events. DPA/FR/repeat ACKs are 17/18/20 of 35, and full TX
  airtime is 26.32/34.26/23.22 s. This is a non-evaluable smoke and must
  not be used to estimate a population effect.
- Next exact step: run frozen 6001--6020 DPA development once, then inspect
  paired gates and source/artifact integrity before any holdout decision.
- Completed frozen DPA development on seeds 6001--6020. All 60 run rows,
  2451 flow records, 6391 action records, three-arm seed trace/config
  equivalence, and source/artifact SHA-256 values were checked.
- DPA beats single ACK in the seed-paired primary comparison, but fails the
  required comparison against same-trigger first-path repeat. The manifest
  records `dpa_joint_primary_gate=false`; holdout 4001--4040 remains closed.
- Wrote `docs/research/meshecho_dpa_dev_results.md`. No ICC manuscript/PDF,
  VERSION, GitHub, or EDAS action was taken. The next research action, if
  authorized, is a separately named structural algorithm proposal with fresh
  development seeds, not parameter tuning on this failed cohort.

## 2026-10-03 - Active Goal Continuation

- Classified the prior turn as progress: it fixed a DPA path-validity defect,
  ran the frozen development matrix, and produced a negative result that
  changes the next algorithm choice.
- Re-read `task_plan.md`, `findings.md`, `progress.md`, Git status, the
  current MeshEcho-SR source action/ACK/commit code, and the complete ICC
  paper structure. Planning catch-up had no unsynced context output.
- Selected `academic-paper` revision mode for later evidence-backed
  manuscript restructuring; the existing ICC 2027 English IEEE draft is
  the source document. No claims or numbers are being rewritten before a
  new algorithm earns them.
- Two read-only independent audits are running: DPA per-flow failure
  forensics and device-local algorithm/prior-art feasibility. The next step
  is to reconcile them with the SR state machine and freeze a fresh design.
- Wrote `docs/research/icc_core_rewrite_revision_map.md` to map each current
  manuscript claim/table/figure to the evidence required for a core rewrite.
  This is a revision architecture, not a numerical paper edit.
- Independent DPA forensics joined action/flow logs and located the observed
  DPA/repeat gap mainly in later R reuse rather than immediate F ACK return.
  Recorded exact path-length and matched-episode limits in `findings.md`;
  this motivates a new ACK-transport/route-commit decoupling hypothesis but
  does not establish it.
- Prior-art audit confirmed DSR already separates route-reply transport from
  discovered forward route, so A/B decoupling alone is weak novelty. Chose
  a DATA-conditioned reverse ACK corridor with a same-time local ACK repeat
  control. Wrote the pre-implementation contract in
  `docs/research/meshecho_rac_design.md`; no RAC code or population result
  exists at this checkpoint.
- Resumed after context transition; `session-catchup.py` found no unsynced
  context. Read all three recovery Markdown files and preserved the dirty
  `version/v2` worktree. The prior unrecorded RAC implementation added the
  three protocol arms and three real-packet tests. Focused suite now reports
  3 passed. No RAC population simulation, holdout, ICC paper/version change,
  push, or EDAS submission has occurred. An independent read-only audit and
  a separate RAC runner implementation are active.
- Completed RAC safety/accounting vertical slices: TTL charging, on-path
  duplicate suppression, deadline refusal, observation and pending-state
  caps/expiry, one repair/repeat per flow-hop, distinct ACK marker values,
  deterministic candidate backoff, malformed-path rejection, no-observation
  refusal, per-hop event diagnostics, and CLI registration. A same-slot
  two-candidate test confirms collisions remain possible. Focused RAC suite:
  22 passed. No RAC population run, holdout, paper/PDF, VERSION, GitHub, or
  EDAS action yet; full integration awaits runner completion.
- Full integrated regression after runner integration: 347 passed, one
  skipped; Python compilation and `git diff --check` passed. Ran only
  custom seed 7000 with the three RAC arms. The three run rows share one
  scheduled traffic hash; four artifact hashes match the manifest. RAC had
  75 eligible corridor events and 48 off-path repair TX events, but all
  three arms had 32/43 deadline ACKs. This smoke is non-evaluable. Before
  development, runner owner is closing seed-isolation and exposure-identity
  validation gaps found in independent read-only review. Holdout unopened.
- Runner audit gaps were closed with test-first negative cases: custom RAC
  is seed-7000/full-suite only, generic development and holdout are blocked,
  the joint gate is scoped to the exact 7001--7020 matrix, and exposure
  validation checks unique candidate identity plus linked F delivery and
  deadline timing. Final full suite: 357 passed, one skipped. Four RAC source
  hashes were frozen in `task_plan.md` before development. No holdout used.
- Completed the exact 7001--7020 RAC development matrix once. Verified 60
  run rows, 816 flow records per policy, 15686 action records, shared
  per-seed traffic/config hashes, four artifact SHA-256 values, and frozen
  source hashes. RAC improved ACK-PDR versus both controls but exceeded the
  +10% upper-CI full-airtime budget against both; `rac_joint_primary_gate`
  is false. Wrote `docs/research/meshecho_rac_dev_results.md`. Holdout,
  ICC paper/PDF, VERSION, GitHub, and EDAS remain untouched. Independent
  read-only forensics and next-structure assessment are running.
- Independent read-only forensics matched every repair start to its local
  exposure and identified 3647/3708 source-next repairs, none canceled;
  3497/3708 started after source acceptance in hindsight. Recorded the
  architectural suppression gap and the prototype's global-state validity
  flaw in the frozen development report. A charged ACK-closure beacon is
  only a new hypothesis; no further code, seed, holdout, paper, release,
  GitHub, or EDAS action followed.

## 2026-10-03 - Core-Rewrite Goal Continuation

- Classified the preceding question-only turn as read-only progress: it
  identified that the ICC contribution needs a core algorithm rewrite, while
  the simulator, PHY, and matched-test framework can be retained. It did not
  change authoritative code or manuscript state.
- Re-ran planning catch-up (no unsynced context), read the latest three
  recovery records, inspected the dirty worktree, current ICC method/results,
  RAC implementation, and frozen negative development report.
- Read `planning-with-files`, `tdd`, `academic-paper`, and
  `systematic-debugging` instructions. The academic-paper skill is selected
  in revision mode for evidence-backed manuscript work; no manuscript claim
  changes until a new mechanism passes experiments. Existing user direction
  not to add a vacuous no-external-funding statement takes precedence.
- Device-locality audit found global state reads at non-source nodes and
  recommended a one-hop, explicitly charged ACK_DONE as the smallest
  source-closure hypothesis. Prior-art audit is running. No new simulation,
  code, paper, version, GitHub, or EDAS action has occurred yet.
- Created the pre-implementation `docs/research/meshecho_clar_design.md`
  contract with four matched arms, actual wire/airtime accounting, bounded
  local-state rules, fresh 8001--8020 development seeds, 8000 smoke, and a
  joint ACK-PDR/full-airtime gate. This is research design, not a result.
  Close prior art already limits the claimed novelty; legacy holdout remains
  closed. Source and runner implementation have not started.
- Audited frozen RAC action timestamps against an ideal 10-byte SF7 DONE:
  3497/3708 repair starts were later than accepted source ACK plus 0.041216 s.
  This is not a causal savings estimate. Tightened the CLAR contract to
  retain a bounded locally decoded closure token if DONE arrives before a
  candidate's ACK observation. Added verified close prior-art limitations.
- Added the first public-behavior CLAR red test: a direct F ACK accepted by
  the source must cause one real ACK_DONE and suppress an off-path candidate
  that decoded both the F FLOOD and ACK. Its expected failure is `unknown
  protocol: meshecho-clar`; next step is the minimum local-state protocol
  slice and rerun, without touching frozen RAC semantics.
- First CLAR red/green slice is complete: `meshecho-clar` is registered;
  candidate observations use actually decoded FLOOD prefixes, source
  first-acceptance sends a 10-byte one-hop ACK_DONE through the ordinary TX
  path, and a locally decoded matching DONE closes a pending repair. The
  focused real-packet test is green (1 passed). This proves only one path;
  multihop cancellation, adverse failures, controls, bounds, and runner
  integration remain unverified.
- The second real-packet test is RED: a multihop candidate sent a redundant
  repair even though it physically decoded the on-path ACK continuation.
  Tracing `Simulator.try_receive` confirmed successful receipt; the failure
  lies in applying new-candidate eligibility to a cancellation signal.
  Next edit separates those predicates, then reruns the focused suite.
- Split pending-repair cancellation from new-candidate eligibility and
  required an exact flow/path plus actual next-hop radio sender. The same
  multihop test is now green; CLAR focused suite: 2 passed. No population
  simulation or ICC manuscript change has occurred.
- Added real-packet adverse checks: one direct ACK deliberately lost at the
  source is rescued by an off-path candidate and then produces exactly one
  DONE; when DONE is deliberately lost at the candidate, repair is not
  canceled. Focused CLAR suite: 4 passed. This establishes causal mechanics,
  not net performance or novelty.
- Added same-beacon/no-cancel arm via a red/green public test. The first
  implementation left `closed_flows` set before the no-cancel branch, so
  the timer still suppressed repair; the red test caught that partial
  ablation. Moving the local closure mutation after the mode check made the
  intended repair occur. Focused CLAR suite: 5 passed.
- Added plain single-ACK F/R control with the same charged F ACK marker but
  no repair or DONE beacon. Focused CLAR suite: 6 passed. A separate runner
  agent is integrating four-arm CLAR split/gate/artifact support without
  touching simulator or manuscript files.
- Added on-path repeat comparator through a red/green packet-level test:
  one lost initial destination ACK copy is rescued by one repeat from the
  same sender, without an off-path candidate. The source then emits the
  same charged DONE. Four strategy names now construct; focused CLAR suite:
  7 passed. Source ACK event semantics and deeper safety remain next.
- Added a red/green source-ACK event contract: a real repaired ACK received
  by the source emits `clar_source_ack_rx` with `accepted=true`, path-position
  and repair marker; this event is separate from physical reception and can
  support runner exposure validation. Focused CLAR suite: 8 passed. Runner
  agent was notified of stable event names and fields.
- Added a no-oracle real-packet test: with no simulator `FlowRecord` and no
  source action map, a candidate that decoded source FLOOD and destination
  ACK still emits one repair. Added cost accounting test proving a DONE is
  10 bytes, counted as control, and its ToA/TX energy contribute to whole
  network totals. Focused CLAR suite: 10 passed. Runner agent reports
  four-arm split, preflight, hash and control-byte tests green; paired gate
  and holdout guard integration remain in progress.
- A packet-level high-rate capacity test exposed 40 live candidate attempt
  guards at one node despite the predeclared 32-entry cap. A red/green fix
  now refuses new repair attempts when 32 unexpired guards are present,
  preserving old duplicate guards. Focused CLAR suite: 11 passed. The
  analogous repeat and forwarded-ACK histories remain to be checked.
- The corresponding repeat-arm stress test exposed 40 live repeat guards.
  A red/green 32-entry admission cap now refuses new repeat attempts without
  evicting still-valid guards. Focused CLAR suite: 12 passed. Forwarded-ACK
  duplicate-history capacity is the remaining bounded-state check.
- The first forwarded-ACK stress setup exercised only 20 valid receptions
  because of half-duplex timing, so it was not a valid cap test. With wider
  spacing and a reception-count precondition, 40 ACKs produced 40 history
  entries (red). The first cap patch accidentally matched old RAC; that hunk
  was removed and the exact CLAR block capped at 32 with a `clar_state_drop`
  event. CLAR plus frozen RAC focused suites: 35 passed. No population run.
- Added duplicate-destination-ACK safety: two real source receptions produce
  `[accepted=true, accepted=false]` and only one source DONE. CLAR focused
  suite: 14 passed. Next run is full regression/compile/diff check, followed
  by runner integration audit before any smoke or development matrix.
- First full regression during runner TDD: 384 passed, one skipped, one
  runner-owned intentionally red tamper test. The runner owner reports the
  paired-CSV revalidation now recomputes from 80 run rows and that focused
  test is green; complete runner handoff is pending. Python compilation and
  whitespace/diff check passed. No CLAR smoke or population matrix yet.
- Added F/R and terminal-repeat packet-level checks: the later confirmed
  route R flow does not send ACK_DONE, and a decoded source DONE cancels a
  pending final-hop on-path ACK repeat. Focused CLAR suite: 16 passed.
  Runner integration is still active; do not open 8001--8020 until its
  complete tests and manifest guards are stable.
- A deterministic real-packet test exposed an unforwardable `ttl=1` ACK
  poisoning intermediate duplicate history and suppressing a later valid
  copy. Moved the intermediate TTL check before history insertion; CLAR+RAC
  focused suites: 39 passed. Local observation-expiry timing is the next
  safety boundary to test.
- A late real-packet ACK test exposed a repair after the candidate's local
  FLOOD observation had expired. Rebased pending repair and attempt-guard
  expiry on the original local FLOOD expiry. CLAR+RAC focused suites: 40
  passed. No fresh CLAR simulation seeds have been opened.

## 2026-10-03 - CLAR Queue-Boundary Continuation

- Recovered from the previous answer and read the current plan, findings,
  protocol contract, scheduler, and CLAR implementation. The prior answer
  did not run a CLAR simulation or change the ICC paper.
- Runner handoff is complete: its focused runner suite reported 134 passed;
  complete integrated regression remains to be run.
- Identified a specific possible timer-to-radio-queue expiry gap. A
  read-only independent audit is also checking candidate locality and
  cancellation. Next local action is one deterministic red/green queue test.
- Added the public-behavior queue test. A corrected targeted pytest selector
  fails at the no-repair assertion after confirming both eligibility and
  queue occupancy beyond the local expiry; this is a reproduced validity
  bug, not merely a source-inspection concern.
- Added a `PendingSend` actual-start predicate and used it for CLAR repair;
  the repair queue test passed. A symmetric CLAR repeat queue test then
  failed as intended. The first repeat fix accidentally matched frozen RAC,
  detected by three RAC failures; it was removed from RAC and applied to
  CLAR with distinct signature context. Focused verification is next.
- Corrected the repeat patch and reran CLAR+RAC focused suites: 42 passed.
  Added a real-packet malformed-continuation test; it failed as expected
  because `ttl=0` ACK canceled a candidate. Tightened cancellation's own
  path, endpoint, payload, and TTL checks without requiring unrelated
  candidate FLOOD state. Focused verification is next.
- CLAR+RAC focused suites now pass 43/43, including the malformed ACK and
  both real queue-expiry tests. Complete `python3 -m pytest -q` passed:
  399 passed, 1 skipped in 21.47 s. Python compilation and
  `git diff --check` passed. The CLAR contract status now reflects
  implemented/pre-development rather than pre-implementation. No CLAR
  population simulation or ICC manuscript/PDF change yet.
- Runner audit identified a concrete 630-s boundary mismatch between raw
  action events and windowed TX metrics. Delegated a test-first correction
  confined to runner and runner tests. Checked that no `meshecho_clar`
  result artifacts yet exist; hash freeze and smoke are deferred until the
  runner correction is verified.
- Runner owner completed the window-accounting correction with two focused
  tests. Independent inspection confirmed raw CLAR TX actions after 630 s
  are preserved but excluded from the windowed DONE count/bytes. Complete
  regression after integration: 401 passed, one skipped in 21.82 s.
  No CLAR smoke/development/holdout result yet.
- Froze final CLAR input SHA-256 values in `task_plan.md`; post-integration
  `py_compile` and `git diff --check` both pass. Next execution is only the
  seed-8000 custom, non-evaluable four-arm smoke. The four frozen inputs
  must not be edited during it or the development matrix.
- Ran the exact seed-8000 four-arm custom smoke and independently matched
  its four data artifact SHA-256 values to the manifest. Four rows have
  identical trace and case hashes and 42 unicasts each. CLAR action paths
  exercised 164 eligible candidates, 143 DONE cancellations, and 13 repairs.
  No inference or tuning was drawn from this one seed; next is the single
  frozen 8001--8020 development matrix.
- Completed the frozen 8001--8020 CLAR development matrix in 84 s.
  Independently verified four data-artifact hashes, four input hashes, 80
  rows, 20 seed-paired scenario/trace identities, and 797 scheduled flows
  per arm. CLAR fails its preregistered joint gate against on-path repeat:
  ACK-PDR difference -0.0161 [-0.0547,+0.0226], airtime +7.7%
  [-5.5%,+21.0%]. The 4001--4040 holdout remains sealed. A read-only
  forensic agent is examining mechanism logs; no source retuning or paper
  promotion follows the failed development result.
- Read-only forensic validation exposed a post-run runner allowlist defect:
  84 actual `source-done-repeat` cancellations are rejected by the current
  CLAR manifest validator. A narrow test-first runner fix is delegated;
  original development artifacts and frozen input hashes remain untouched.
  The result already fails the prespecified joint gate, so the same seeds
  will not be rerun as confirmatory evidence.
- Validator-only red/green fix now accepts `source-done-repeat`; its 137
  focused tests and the full 402-pass/one-skip suite are green. Calling
  validation on the unchanged frozen manifest with its original run-source
  hash map reaches the expected failed joint-gate error, proving no earlier
  artifact/accounting rejection. Current runner hash changed after the run;
  original frozen provenance remains in the manifest and result report.
- Wrote `docs/research/meshecho_clar_dev_results.md`. Forensics found 196
  of 279 unACKed CLAR flows were undelivered R data; an ACK-only query has
  narrow exposure. The next structural hypothesis should address same-flow
  R data recovery, with new seeds and controls. ICC source/PDF, version,
  GitHub, and EDAS remain untouched.
- Used targeted deep-research quick-brief workflow to verify six close
  external sources and wrote
  `docs/research/meshecho_same_flow_recovery_prior_art_brief.md`. The
  literature rules out a broad novelty claim for route repair/ARQ; the
  next implementation must first freeze a specific device-local decision
  rule and same-trigger controls.

## 2026-10-04 - Goal Resume and Algorithm Boundary

- Re-read current plan/findings/progress, audited the dirty worktree, and ran
  the planning skill's session catch-up script (no unsynced output). No old
  development artifacts, holdout seeds, ICC manuscript, version, or GitHub
  state were changed in this recovery step.
- Confirmed that the new core must target source-local same-flow R-DATA
  failure: CLAR failed its frozen repeat comparison and 196/279 unACKed
  flows had undelivered R DATA. Retain tested simulation/accounting plumbing.
- Read the planning, test-first, and academic-paper skill instructions.
  Next: freeze a new prior-art-aware mechanism and evaluation contract,
  implement public-behavior tests first, then run fresh-seed experiments.

- Froze the new `meshecho_dhr_design.md` before new-code population runs.
  A public packet test for dropped initial R DATA was RED (unknown protocol)
  then GREEN (one marked R rescue; 1 passed). A rejected multi-operation
  patch attempt made no changes; a single-file two-hunk patch succeeded.
- Independent adversarial review identified ACK marker loss, stale-route
  ACK history poisoning, underbudgeted F forwarding delay/path bytes, and
  future-queue reservation. Corrected the design contract before further
  implementation. Runner integration is delegated on separate files;
  no development or holdout seeds have been opened.

- Added `MeshEchoDHR` and one-byte recovery marker echo through real ACK
  packets. Red/green cycles covered R DATA failure, stale-route F recovery,
  alternate-path F ACK commit, queue-busy deadline refusal, active capacity,
  and matched control actions. Focused DHR suite: 6 passed. These are
  mechanism tests only, not evidence of population gain.
- A separate runner agent owns only `tools/run_sr_experiment.py` and
  `tests/test_sr_experiment.py`; protocol/source tests remain locally owned.
  No DHR seed-9000 smoke, 9001--9020 development, or 10001--10040 holdout
  has been run. ICC LaTeX/PDF, VERSION, GitHub, and EDAS are unchanged.

- Rechecked the algorithm boundary after the user's question: a small
  threshold tweak to old CLAR is not the plan. DHR rewrites the same-flow
  recovery decision while retaining the tested SR data plane and simulator;
  its 120-s branch is still an unvalidated heuristic and may fail the ICC
  contribution bar. Targeted DHR tests: 9 passed. Whole suite: 430 passed,
  one skipped. `py_compile` and `git diff --check` pass. Runner integration
  is present but final owner check and frozen-input smoke remain pending.
- Runner final suite passed 157 tests. Froze four source/design/scenario/runner
  hashes in `task_plan.md` and ran the seed-9000 custom DHR smoke only.
  Independent `shasum` matches all four manifest data hashes; four arms have
  the same 44 scheduled flows, case hash, and application-trace hash. DHR
  exercised eight R and two F rescues. The single-seed paired figures are
  non-evaluable. Next is one frozen 9001--9020 development matrix.
- Completed the frozen DHR 9001--9020 matrix and independent provenance,
  artifact, pairing, and action-count checks. The manifest validator reaches
  the expected failed joint gate. Relative to fixed R, DHR's ACK-PDR gain
  is +0.0227 [-0.0179,+0.0632] with +16.4% [7.8%,25.0%] airtime;
  relative to fixed F, ACK-PDR is +0.0005 [-0.0515,+0.0524] with -13.9%
  [-21.4%,-6.4%] airtime. The exposure gate passes, but both primary
  comparisons fail. Wrote `docs/research/meshecho_dhr_dev_results.md` and
  stopped. Holdout, ICC paper/PDF, VERSION, GitHub, and EDAS remain untouched.

## 2026-10-04 - Active Goal Continues After DHR Stop

- Recovered the three planning files and current dirty worktree; the prior
  turn made real progress by falsifying DHR's primary claim. Read the
  planning-with-files, TDD, and academic-paper skills and ran the session
  catch-up script (no unsynced output). The active goal still requires a
  distinct core algorithm, simulations, and a major ICC paper revision.
- Read the ICC rewrite map and frozen DPA result; DPA also lost to a simple
  on-path ACK-repeat control. A zsh glob-based `rg` query failed with no
  matches and changed nothing; the next search will use a literal path.
- Read the frozen RAC/LPR results and received a targeted independent
  prior-art audit. RAC's ACK corridor improved reliability but exceeded
  airtime limits; LPR produced only seven ACK-committed insertions after
  207 relay transmissions. ExOR, WAR/Bypass, and LoRa opportunistic routing
  cover the broad passive-overhearing/local-repair idea, so it cannot be
  relabeled as a novel core. The next decision requires a narrower mechanism
  and stronger controls or a candid pivot in the paper's claim.
- An independent frozen-artifact analysis decomposed fixed F's 229
  delivered-unACKed flows: 224 had no source ACK callback, and flood
  duplicate delivery did not cause extra ACKs. Wrote
  `docs/research/meshecho_core_feasibility_gate.md` to freeze the questions
  for a non-mechanism observability diagnostic before choosing another
  algorithm. A separate agent owns only new diagnostic tool/test files;
  frozen DHR source and cohorts remain untouched.
- The same read-only join on DHR's own action log found 109 R rescues
  (45 deadline deliveries, 32 ACKs) and 66 F rescues (66 deliveries,
  24 ACKs). This supports measuring both directions of reliability,
  without treating selected-action subgroups as a causal comparison.
- Terminal DNS failed on an ICC CFP curl, so the in-app browser was used.
  The official live symposium page lists 16 October 2026, not the older
  2 October date, with IoT track EDAS N35508. Updated the older strategy
  document to mark its deadline/timeline as superseded; no EDAS or paper
  state changed.
- Read the live official submission guidelines: initial PDF must be English,
  10-point, at most six pages; PDF and EDAS title/complete author list must
  match, and simultaneous submission is prohibited. The new observability
  diagnostic now has separate tool/test files in progress. No submission or
  manuscript mutation has occurred.
- The diagnostic owner completed five behavior tests and a seed-11001
  replication: identical trace hash, 33 flows, 23 deadline ACKs, and 27
  deadline deliveries versus the existing runner. Initial-R hop reception
  was 27/35, and an explicitly oracle-only one-relay detour screen found
  candidates at all eight missed hops. More seeds and ACK-hop tracing remain
  in progress; this single seed is not a gain estimate.

- The diagnostic owner completed 12 focused tests and exploratory seeds
  11001--11003; the source and runner trace/count comparisons agree. Final
  diagnostic JSON is `/tmp/sr_observability_11001_11003_guard_20261004.json`.
  Across 134 first-R hops, 32 failed intended reception and an oracle detour
  exists for all 32 after the passive guard; five successful hops would be
  falsely treated as failures. Initial reverse ACK physical hops failed
  20/143 times. These are observability and feasibility measurements, not
  demonstrated recovery gains. The old ICC paper/PDF, VERSION, GitHub,
  holdouts, and EDAS remain unchanged.
- Reassessed the user's rewrite question: the failed route-score and DHR
  controls argue for redesigning the core reliability decision, not another
  parameter adjustment. Keep the verified simulation/data-plane infrastructure.
  Next: independent code/test verification, then either a genuinely distinct
  device-local algorithm contract with fresh controls/seeds or a candid paper
  pivot if no such contract survives the prior-art gate.
- Independent focused verification completed: 12/12 observability tests pass,
  `git diff --check` passes, and SHA-256 of the diagnostic script, simulator,
  and runner matches the JSON provenance. No release, paper, holdout, or
  submission state was changed by this assessment.

## 2026-10-04 - Core-Redesign Continuation

- Classified the previous turn as progress. Re-read planning records and
  dirty worktree after session catch-up (no unsynced output), and loaded the
  planning, TDD, academic-paper, and deep-research skill instructions.
- Reviewed frozen LPR, RAC, and CLAR contracts/results. LPR's useful DATA
  repair yield was seven ACK-confirmed insertions after 207 relay TX;
  RAC's ACK gain exceeded its airtime gate; CLAR's closure did not beat
  matched on-path repeat. An independent prior-art/algorithm audit is
  underway. No development/holdout seeds, ICC source, version, or EDAS
  state were touched in this continuation so far.
- Tested the first checkpoint idea against exploratory hop strata:
  27/32 initial-R failures occurred on path index 0, before an on-path
  checkpoint can hold the payload. Sent the independent auditor this
  counter-evidence. The candidate remains unselected pending flow-level
  ACK-loss exposure and cost analysis; no code was started.
- Independent audit agreed that checkpoint-only rescue lacks primary
  exposure. Next concrete action is a test-first, read-only first-hop
  witness screen using actual prior receptions at the intended relay;
  classify locally nominated versus oracle-only candidates before any
  protocol rewrite. The existing observability JSON and failed cohorts
  remain immutable historical evidence.
- Delegated the isolated witness diagnostic in new files only. Independently
  checked the 2023 peer-reviewed LoRa opportunistic-routing DOI/abstract:
  per-hop candidate diversity is established prior art. A second literature
  delegation hit the thread limit; local literature checks continue without
  restarting the existing agent. No candidate protocol has been frozen.
- Crossref verified a 2020 LPWAN opportunistic/on-demand network-coding
  paper (DOI 10.3390/s20205792), limiting any generic coded-fork novelty
  claim. Requested the witness diagnostic also count flow-level delivered-
  but-unACKed R cases with source-observed first-hop progress and first-
  relay ACK reception. That exposure check precedes any on-demand ACK-query
  design; no such algorithm is yet claimed.
- The first-hop diagnostic's initial 2/2 TDD tests are green. It requires
  an actual route-confirming ACK and candidate FLOOD observation at the
  first relay before that ACK's upstream TX, avoiding post-commit local
  knowledge. Agent is adding deterministic nomination and flow strata
  before fresh exploratory seeds. A broad ACK-query OpenAlex query failed
  to yield parseable results, so novelty remains unresolved.
- Asked for a direct-versus-multihop split in the diagnostic. For a direct
  R path, missing destination ACK gives the source no positive DATA-progress
  evidence; only a decoded on-path relay DATA forward can support the
  hypothetical on-demand ACK-query branch.
- Calculated exact current wire-model ToA for a 3-node route: 50-byte DATA
  versus a hypothetical 19-byte marked query is 0.097536 versus 0.051456 s
  at SF7 and 2.301952 versus 1.318912 s at SF12. The full query-response
  path is unmeasured; no performance claim follows.
- Checked RFC 4728 directly: DSR uses passive forwarding evidence and
  network-layer ACK requests, so the generic query primitive is established
  prior art. Tightened the proposed boundary to source-level cached
  destination proof and selective suffix action, contingent on exposure
  and a DSR-style control. No algorithm implementation started.
- The separate witness diagnostic's first 8/8 TDD tests and three fresh
  exploratory seeds yielded 86 initial R first hops, 22 intended losses,
  and eight actually decoding nominated candidates under an unlimited
  prior-history screen. The ACK-query target set was three flows and none
  was delivered. The agent found many stale local witnesses; requested
  30/120/300-s expiry strata and an expiry test before final interpretation.
  This remains an unvalidated feasibility screen, not a mechanism result.
- Flagged a second bounded hypothesis: F destination delivery greatly
  exceeds source ACK, so evaluate whether multiple locally decoded FLOOD
  paths are available before the current immediate ACK. A separate agent
  spawn hit the thread limit; no F-path diagnostic or protocol change was
  started yet.

## 2026-10-04 - Evidence-Guided Core Rewrite Continuation

- The latest user clarification was answered from an independent read-only
  audit: rewrite the SR routing/recovery/feedback decisions, keep the PHY,
  packet-event, accounting, and matched-run harness. No protocol or paper
  change occurred in that turn, so it is classified as no progress toward
  the open full goal.
- Planning-with-files session catch-up completed with `python3` and no
  unsynced context output. The first attempt with `python` failed because
  that executable is unavailable; the plan records the error.
- Re-read the active dirty worktree and final first-hop JSON. Seeds
  12001--12003 show 0/5/8 actually decoding locally nominated candidates
  among 22 intended first-hop failures for 30/120/300-s local history;
  three source-observed-forward/unACKed multihop R flows were undelivered.
- Delegated a test-first, behavior-preserving F inbound-path diagnostic in
  isolated new files. The next local work is independent source/artifact
  verification and prior-art-aware evaluation of whether an observable
  destination ACK-path choice is viable. The paper, version, GitHub, EDAS,
  and holdout remain untouched.
- Independent first-hop provenance check matched SHA-256 for the simulator,
  SR runner, and both diagnostic scripts to the JSON manifest. The focused
  witness suite passed 10/10 tests. Source inspection confirms each
  decoded FLOOD copy reaches `on_receive`, but `on_fallback` deduplicates
  before re-ACKing; the upcoming observer can count local alternatives
  without altering protocol behavior.
- Created `docs/research/meshecho_flood_ack_path_feasibility.md` before
  population results. It fixes the observable-path definition, four short
  windows, baseline-reproduction checks, deadline accounting, and a
  descriptive go/no-go boundary. A broad Crossref search was inconclusive
  on close prior art; no novelty statement was added to the paper.
- A broad `/tmp` file search hit two permission-denied entries. Narrow
  searches showed no accessible DHR per-flow JSONL despite hashes in the
  report, so no per-flow reverse-path attribution was inferred from DHR
  aggregates.
- Reviewed the frozen DHR design and ICC bibliography. The new mechanism's
  eventual evaluation must include same-trigger simple recovery controls
  under full packet airtime and 30-s ACK deadlines, and the paper will need
  verified close prior art before any novelty wording. No candidate was
  frozen from aggregate data alone.
- Independent literature agent began a focused reverse-ACK screen. Crossref
  DOI/title/venue checks confirmed two adjacent LoRa routing/flooding papers
  (ITNAC 2024 and IEACon 2025), but their abstracts do not establish the
  exact duplicate-DATA ACK-path decision. Novelty is still unresolved.
- The focused prior-art agent completed a DOI/abstract check of Directed
  Diffusion, LoRa flooding, AODV reverse routes, and a 2020 multipath
  DATA/ACK flood paper. I independently verified the latter's Crossref
  abstract. The feasibility memo now excludes broad "first multipath ACK"
  claims; exact LoRa receiver-side selection remains unverified.
- Two independent, behavior-preserving exploratory replays reached
  provisional outputs. The path observer is refining full-path versus
  immediate ACK-next-hop diversity; the ACK-hop observer is finalizing
  where reverse transmissions failed. Both report exact per-flow replay
  equivalence to their baseline, but final JSON, focused tests, hashes,
  and independent review are pending. No protocol candidate is frozen.
- Independently reviewed `diagnose_flood_ack_hops.py` and ran its focused
  suite: 5/5 pass. Its JSON on 14001--14003 reports 138/138 destination
  deliveries, 103/138 source ACKs, and 37 physically failed ACK attempts
  among 35 delivered-unACKed flows. The observer records decode results
  from the existing `try_receive` call and preserves per-flow baseline
  timestamps; it does not add random draws or simulate alternate ACKs.
- Independently reviewed the final path-diversity diagnostic and ran the
  combined focused suite: 25/25 tests pass. Final path JSON on fresh
  15001--15003 has 27/32 FLOOD-first delivered-unACKed flows with a
  different decoded reverse first hop within 1 s; offline deadline slack
  min/median is 12.09/13.80 s. Its four source hashes match live files.
- Corrected a draft algorithm assumption before implementation:
  `Packet.created_at` is simulator metadata, not an on-wire field, so
  destination cannot gate on source's absolute deadline. The candidate
  now uses only a destination-local 1-s observation window; source still
  accepts ACK only by its original deadline. No protocol, paper, version,
  GitHub, EDAS, or holdout change was made in this diagnostic phase.
- Froze the ACK-branch prototype design (hash recorded in `task_plan.md`)
  and delegated test-first implementation. The frozen candidate is still
  not a full source-side core rewrite. Runner review identified hardcoded
  DHR custom/split guards, so BAR requires its own exact three-arm suite,
  smoke/development/holdout split validation, and independent gate; old
  DHR results and seeds must remain untouched.
- After the user's core-rewrite question, confirmed from the ICC source and
  failed DHR development report that a new source-side decision is needed;
  the ACK branch alone is insufficient. Refroze the ACK-branch design at
  SHA-256 `0fd1dc3f267e4d38bba604371c9c38c84c97ce5b4d1a90cc2a8273f09b24e332`
  with the R-first/F-rescue epoch rule, actual inbound last-hop check, and
  explicit unbounded inherited FLOOD dedup caveat. No BAR smoke, development,
  or holdout seed has been run; ICC paper/PDF, VERSION, GitHub, and EDAS
  remain unchanged.
- BAR protocol implementation is in progress under isolated ownership.
  Seven focused public-behavior tests are green so far, including a RED/GREEN
  exact 1.000-s expiry-order regression and R-first delivery followed by F
  recovery with ACK acceptance and route commit. Runner split/provenance/gate
  tests are being implemented separately; neither mechanical nor population
  seeds have run. The protocol and runner hashes are not yet frozen.
- BAR protocol owner finished two exact arms and eight behavior tests.
  Independent re-run of BAR/DHR/SR focused suites passed 34/34, and SHA-256
  matched the owner's report: simulator
  `41626c2d559088f00f2758edc782b31649359bb3e26afdc199d7be6803f70f45`,
  BAR tests `975219ab008c0526382ccf0aeaecda9a19d1034502a1926bb53d6677b099a188`,
  design `0fd1dc3f267e4d38bba604371c9c38c84c97ce5b4d1a90cc2a8273f09b24e332`.
  The runner is still in progress; no seed run has started.
- Before BAR smoke, added a prospective 40-seed holdout replication
  criterion to the ACK-branch design: same paired thresholds and at least
  40 actual alternate extra ACK TXs across 20 seeds. Current design hash
  is `285667e4e1b531e7bc5d67bfcbb2f5257a553020e667d226338c93027a3ddb9b`;
  runner owner was notified to add a test-first holdout report/gate.
  Earlier design hashes remain historical. No seed has been run.
- BAR runner implementation completed. Independent full unittest discovery
  passed 505 tests with one skip in 28.8 s; `git diff --check` passed.
  Independently matched all six BAR source/design/test hashes listed in
  `task_plan.md` and froze them before any BAR seed. Next exact action is
  seed-16000 three-arm mechanical smoke only, followed by manifest/hash
  and per-flow/action reconciliation. ICC paper/PDF, VERSION, GitHub,
  EDAS, development seeds, and holdout remain untouched.
- Ran the exact three-arm seed-16000 smoke in 7.8 s. Manifest input hashes
  match the six frozen BAR inputs; all artifact hashes independently match
  the generated runs/paired/flows/actions files. Three arms share the same
  43 scheduled flows, case hash, and trace hash. Per-flow totals reconcile
  to run rows; alternate and same-path arms recorded 8 and 11 actual extra
  ACK transmissions on unique flows. The single-seed comparison is
  non-evaluable and was not used to tune the mechanism. Next exact action:
  run one frozen 16001--16020 BAR development matrix, then independently
  validate its manifest and predeclared joint gate before touching holdout.
- Ran one frozen 16001--16020 BAR development matrix (60 arm-runs, 778
  unicasts/arm). Independent SHA-256 and pairing checks passed; the
  validator reached only the expected failed joint-gate error after
  flow reconciliation. The alternate ACK rule beats fixed F but does not
  beat the same-trigger same-path repeat: +0.0021 ACK-PDR with a CI spanning
  zero and a +9.4% airtime upper bound against the +5% budget. Actual
  alternate extra ACK exposure was 248 transmissions across all 20 seeds.
  Wrote `docs/research/meshecho_bar_dev_results.md` and stopped BAR's
  positive claim. Holdout, ICC manuscript/PDF, VERSION, GitHub, and EDAS
  remain unchanged. The next exact research action is a new source/
  feedback core contract with fresh controls/seeds or an explicit paper
  pivot; do not tune on this BAR development cohort.
- New continuation classified the prior turn as progress, ran the
  planning-with-files catch-up script, and re-read the three records plus
  dirty worktree. A read-only BAR action-log screen found only 31 of 248
  actual extra-ACK flows had two or more F-marker source ACK callbacks;
  their paths are not logged, so this is an upper bound on usable
  multi-path source-selection exposure, not a mechanism result. The next
  algorithm must target a higher-exposure decision, not merely retune BAR.
- Read-only BAR fixed-F action stratification rejected an unconditional
  ACK-query-first design: among 194 admitted R-timeout rescues, only 17
  initial R DATA copies had reached the destination by the guard. The
  remaining 177 needed forward DATA recovery. No new protocol, seed, or
  paper claim was made from this offline diagnostic.

## 2026-10-04 - Prospective Forward-Recovery Continuation

- Classified the preceding clarification-only goal turn as no progress
  toward the full algorithm/experiment/manuscript objective. Re-ran the
  planning-with-files catch-up script with `python3` (no unsynced output),
  inspected the dirty worktree, and re-read the current plan/findings/
  progress and the old ICC method. No existing user changes were reverted.
- Delegated two independent bounded tasks: a test-first, behavior-preserving
  DHR fixed-F forward-recovery diagnostic on new exploratory seeds
  18001--18003 (new files only), and a read-only close-prior-art check.
  A third design-review spawn hit the agent limit, so local design review
  continues without retrying it. BAR holdout remains sealed.
- Next exact action: independently inspect the diagnostic's provenance and
  controls, review prior-art findings, then decide whether a distinct
  device-local recovery contract can be frozen. The ICC manuscript/PDF,
  VERSION, GitHub, and EDAS have not changed in this continuation.
- The focused original-source screen ruled out bare path-hop TTL and
  last-retry DATA flooding as novelty (AODV RFC 3561, DSR RFC 4728,
  Meshtastic official mesh algorithm). Recorded mandatory fixed TTL,
  expanding-radius, full-F, R-repeat, and product-like controls. The
  exploratory forward-recovery diagnostic continues only to measure
  opportunity and cost, not to authorize a new paper claim.
- A separate bounded ACK-cancellation idea emerged from the preliminary
  post-delivery FLOOD tail. Prior-art search found generic rebroadcast
  suppression but no verified exact LoRa ACK-overhear version; originality
  is unresolved. Before implementation, a new passive diagnostic must
  measure actual normal ACK decodes at still-pending F relays, not merely
  offline post-delivery airtime. No mechanism code or new claim yet.
- Assigned an isolated, test-first ACK-overhear feasibility tool/report on
  seeds 22001--22003, using only physically decoded natural ACKs and
  uncommitted pending-F handles. The source/runner are left unchanged while
  both diagnostics run. This is a passive opportunity check, not a protocol
  performance test.
- Finalized the separate forward-recovery diagnostic and read its report.
  Independently matched SHA-256 for its JSON/tool/tests and four source
  inputs; re-ran the seven focused tests successfully. A structured query of
  the immutable JSON split post-delivery relay tail: 310 TX/30.456 s on
  F-first flows, 52 TX/5.072 s on two R-first flows. The final report is
  `docs/research/meshecho_forward_recovery_exposure_18001_18003.md` and
  JSON SHA-256 is `89e67a1f58bb258ed6c424b0564576871e7c95f943623743dfce9d085908c5b2`.
  No protocol/paper/version/remote change follows from this passive result.
- Local source review found an internal LPR precedent for ACK/DATA-overheard
  cancellation of queued patch relays (`lora_mesh_sim.py:3533--3554`).
  Recorded that a terminal-ACK FLOOD-tail rule by itself is insufficient
  as the goal's rewritten core; it first needs measurable strict exposure
  and then integration into a source-side decision tested against controls.
- The ACK-overhear diagnostic agent reported a baseline-matched preliminary
  22001 seed with substantial strict pending-F overlap; requested per-stage
  marker matching and initial-F/recovery-F strata before any design freeze.
  No protocol implementation or population performance run has started.

- The next goal turn completed a read-only source/evidence audit and clarified
  the full-scope decision: retain the simulator scaffold but redesign the
  source-side F/R/D policy. This is progress through evidence, not a code or
  paper revision. The final ACK-overhear report is now available with 1,120
  strict handles, 591 later TXs, and 57.915136 s potential local airtime;
  its three-seed diagnostic is not a performance estimate.
- Ran planning-with-files session catch-up (`python3`), which reported no
  unsynced context. Re-read current simulator/ACK scheduling semantics and
  the draft ACK-terminated FLOOD contract. Two read-only parallel audits are
  checking the component contract and the required source-core design.
  Next exact action: reconcile their findings, correct/freeze a full
  device-local algorithm contract and controls, then start one public-
  behavior TDD slice before any new population run. No ICC paper/PDF,
  VERSION, GitHub, EDAS, or holdout change has occurred.
- Corrected the ACK-terminated FLOOD draft contract after independent audit.
  Added the `MeshEchoAFS` fixed-F candidate and identical-shadow no-cancel
  arm in `lora_mesh_sim.py` plus public simulation tests in
  `tests/test_meshecho_afs.py`. The first test was observed red (unknown
  protocol) before implementation and green after it. Three focused tests
  pass; full pytest is 520 passed, 1 skipped in 37.22 s; whitespace check
  passes. No AFS population simulation, ICC paper rewrite, version bump,
  GitHub upload, EDAS action, or reserved holdout run occurred.
- Next exact action: inspect the independent integrated source-core contract,
  resolve the actual-TX-start choice mechanism, then add a source-level
  public-behavior test first. Do not claim AFS-alone satisfies the goal.
- An integrated DRC source contract was drafted and one cold-F/next-R test
  went red (unknown protocol) then green on a temporary source tracer.
  Before adding its recovery behavior or running a population, an
  independent non-holdout trace audit found zero reserve-caused F-first
  exposure among 559 route-bearing flows and only a 0.488-s route-bound
  checkpoint spread. Rejected DRC as specified, removed only this turn's
  incomplete `MeshEchoDRC` class/registration/test, and retained the
  documented negative design. AFS focused tests still pass (3/3). No
  28000 smoke, 280xx development, 290xx holdout, paper, version, remote,
  or EDAS change occurred.
- Next exact action: freeze and run a baseline-parity AFS mechanical smoke,
  then a prospective AFS component matrix if parity holds; in parallel,
  seek a source-side mechanism with a real device-observable decision
  exposure. Keep the ICC manuscript unchanged until a complete successor
  passes fresh development and untouched holdout.
- Added two AFS public negative/metadata tests via observed red-green
  cycles. Marker-1 F could previously be canceled and is now ineligible;
  `Packet.protocol` metadata no longer gates an otherwise matching ACK.
  `python3 -m pytest -q tests/test_meshecho_afs.py`: 5 passed. Complete
  suite: 523 passed, 1 skipped in 37.29 s. A separate runner agent is
  implementing new-file mechanical/prospective AFS tooling without seed
  runs; a read-only source-signal agent is screening non-holdout feedback.
  Attempted extra AFS audit delegation hit the agent-thread limit and was
  not retried. Next exact action: review runner/test/source contracts,
  record frozen hashes, then run seed 23000 mechanical smoke only.
- Added a committed-future-start AFS queue test; six focused tests pass.
  Read `docs/research/meshecho_dhr_source_signal_screen.md`, which finds
  a descriptive one-hop ACK-risk signal but explicitly no action-benefit
  inference. The AFS runner/test owner reports a completed new-file runner
  with seven synthetic tests and no reserved seed run; independently inspect
  its source and validator before source-hash freeze. ICC paper/PDF, VERSION,
  GitHub, EDAS, and all reserved holdouts remain unchanged.

## 2026-10-04 - Rewrite Scope Clarification

- Recovered context with the planning skill's `session-catchup.py` using
  `python3` (the initial `python` command was unavailable). Inspected the
  dirty worktree and latest plan/findings/progress. Started read-only
  independent algorithm-boundary and AFS-runner audits.
- Current conclusion to communicate: rewrite the MeshEcho source policy and
  recovery decision as an explicitly testable algorithm, but retain the
  validated simulator and common baselines. AFS can be evaluated as one
  component, not presented as a complete algorithm or ICC improvement.
- No reserved seed, new population run, manuscript/PDF, VERSION, GitHub,
  or EDAS change was made in this continuation.
- Independent AFS-runner audit reported three evidence-validation defects
  before seed 23000: strict-pending witness reconstruction, deadline
  timestamp/flag consistency, and PHY airtime consistency. Logged these as
  pre-smoke blockers; no code or seed run followed from the audit.
- Read the frozen DHR and BAR development reports and an independent
  architecture audit. Both failed their predeclared simplest-control joint
  gates, so neither can be recast as the new core. Assigned the AFS runner
  owner a test-first repair of the evidence validator in its two files,
  explicitly without running reserved seeds. The source-core design remains
  unresolved; the old ICC manuscript is still not evidence for it.
- Inspected `MeshEchoSR.send_app`, DHR's recovery guard, and the AFS class.
  Confirmed the new component inherits the old threshold-driven initial
  policy and fixed-F rescue; it is not an end-to-end core rewrite. The
  existing ICC abstract continues to disclose its negative matched-score
  and random-pair comparisons.
- Independent read-only hypothesis screen found no currently supported
  full source-controller replacement. High exposure is initial R forward
  failure, but missing ACK cannot distinguish that from reverse loss.
  Recorded the go/no-go requirement for a fresh, bounded device-local
  progress signal; AFS remains a separate cost-component experiment.
- AFS runner owner added packet/handle receive-time snapshots and
  independent predicate reconstruction, timestamp-based deadline checks,
  and frozen-PHY TX-ToA checks in its runner/test files. It reports 12
  runner unit tests and 18 combined tests passing, no reserved seeds run.
  Root reran `python3 -m pytest -q`: 535 passed, 1 skipped in 37.45 s.
  Independent runner review is still pending before hash freeze/smoke.
- The independent read-only reviewer found a false-positive provenance path
  and duplicate-decode count inflation despite the green tests. Canceled
  the prospective seed-23000 freeze/smoke; assigned the runner owner a
  test-first deterministic-replay and unique-decode fix, plus a real
  multi-node cancellation recorder test. No reserved seed has run.
- A second read-only source-feedback screen bounded a STATUS_REQ/NACK/ACK
  branch against old BAR traces and PHY packet ToA. Only 17/194 guards
  offer positive delivered-only diagnosis; 177 need forward DATA rescue,
  and the query adds airtime and delay. Rejected this as the next core
  candidate before code or new seeds; source redesign remains open.
- AFS runner now replays every prerequisite seed/arm with all saved rows,
  flows, actions, TX, and ACK decodes (ephemeral handle numerals normalized),
  and rejects duplicate physical ACK decode identities. The fabricated
  100-cancel fixture fails replay; a real 3-node seed-7 test observed four
  verified cancellations. Independent reviewer found no blocker. Root
  full pytest: 539 passed, 1 skipped; `git diff --check`, `py_compile`, and
  CLI help pass. Recorded ten frozen SHA-256 values in `task_plan.md` before
  running reserved smoke seed 23000; development/holdout remain unopened.
- Ran only frozen AFS smoke seed 23000, then separately validated its saved
  manifest by deterministic replay. Three-arm parity passed. AFS saved
  8.507136 s TX airtime and canceled 353 pending relays, but one-seed
  source ACK count fell 29 to 26 of 39; destination delivery stayed 38.
  This does not pass/fail the prospective 40-seed joint effect gate. Next:
  run frozen development 23001--23040 once and stop if its gate fails.
- Ran the frozen 40-seed, three-arm AFS development matrix once. The saved
  validator passed evidence and paired checks but exited before replay at
  the expected failed development gate. Therefore independently replayed
  every one of the 120 arms read-only; rows, flows, actions, full TX and
  decodes all matched. AFS saved ~19.5% paired airtime but failed the ACK
  noninferiority bound. Wrote
  `docs/research/meshecho_afs_dev_results.md` with six artifact hashes,
  pooled/paired separation, limitations, and stop rule. Holdout sealed;
  manuscript/PDF, VERSION, GitHub, and EDAS unchanged.
- Separate read-only audit confirmed 10/10 input hashes, 6/6 artifact hashes,
  40/40 paired application traces and fixed-F parity, and the same failed
  ACK noninferiority bound. Updated the plan's current-next-action header
  away from AFS continuation toward a new core mechanism or an explicit
  paper-scope pivot. No further seeds or code changes followed.

## 2026-10-04 - New-Core Research Continuation

- Classified the preceding goal turn as substantive progress, ran
  `session-catchup.py` with `python3` (no unsynced output), re-read the
  latest plan/findings/progress and dirty worktree. Corrected a stale
  pre-smoke sentence in the plan top; no simulation source, result,
  manuscript, version, GitHub, or EDAS change yet this turn.
- Selected a targeted quick research brief to verify the nearest prior art
  and possible feedback mechanisms before proposing another protocol.
- Started bounded read-only prior-art and local-feedback checks in parallel.
  A third design-agent spawn hit the thread limit; the root keeps that work.
  No code, seed, paper, version, or remote change occurred.
- Inspected MAG's feedback contract and the current ACK construction.
  Forward minimum SNR in ACK has already been explored and failed its
  development cost/comparator gate; reverse ACK `path_index` is a local
  relay progress observation, not a source-side forward-delivery label.
  Next: inspect matched fixed-R versus fixed-F flow outcomes without
  treating closed-loop cross-arm differences as per-flow causal effects.
- Independently joined existing DHR fixed-R-repeat and fixed-F-rescue
  flow/action histories; stricter local-state screen confirms no clear
  source feature that makes R repeat preferable to F for the high-exposure
  missed-DATA branch. Local-feedback agent cross-checked the join and
  reported low passive first-hop witness reach. Read prior fixed-F ACK-hop
  diagnostic; now screening a costed reverse-confirmation mechanism.

## 2026-10-04 - Prior-Art Correction and Core Boundary

- Classified the preceding turn as substantive progress: independent
  source-code verification found a direct Meshtastic firmware precedent
  for canceling pending direct-message rebroadcast after overhearing a
  decodable ACK/reply. This narrows AFS novelty and changes the next
  algorithm decision. Recovered project state with the planning skill's
  `session-catchup.py`; the worktree remains dirty and was not cleaned.
- Re-read MeshEcho-SR source policy, DHR timeout recovery, AFS component,
  and the frozen AFS result. Confirmed that the current core still uses
  fixed miss/age rules and AFS inherits fixed-F recovery; the AFS
  development gate failed source-ACK noninferiority despite lower airtime.
- Next exact action: inspect whether last-hop ACK repetition can be
  triggered using local device state and whether it beats a same-path
  second-ACK control under full airtime/deadline accounting. No new seed,
  paper/PDF, VERSION, GitHub, EDAS, or holdout action occurred.
- Completed the last-hop ACK read-only screen and rejected it as a
  standalone core rewrite. The saved diagnostic confirms 37 failed ACK
  attempts, 23 final-hop failures, and only 16 with a source-adjacent
  relay; receiver-side success is invisible to that relay. Existing
  RAC/CLAR repeat arms are close controls, and an exact final-hop-only
  trial has not been run. A new bounded source-controller design screen
  is in progress. No protocol or seed was changed or run.
- Completed independent source-policy and route-anchored-F prior-art
  screens. The former found a high-exposure one-prior-R-miss risk stratum
  but no validated better alternative action; the latter found close
  priority-forwarding and ACK-suppression predecessors. Therefore no new
  algorithm is frozen yet. Next implement a test-first, single-flow
  branch diagnostic on fresh exploratory seeds with explicit keyed
  reception-draw pairing and entry-state checks. This is mechanism
  selection, not confirmatory population evidence; all old development
  and holdout splits remain untouched.
- Wrote `docs/research/meshecho_source_branch_diagnostic_design.md`
  before implementation. It fixes the source-visible one-prior-R-miss
  entry state, target-only R/F/R-F/R-R arms, keyed reception and flood
  jitter pairing, strict pre-app prefix parity, original 30-s deadline,
  actual rescue starts, and disjoint TX/censoring costs. Seed 34000 is
  mechanical smoke; 34001--34005 are exploratory only; future 35001--35040
  development and 36001--36040 holdout are reserved and unopened.
- An independent read-only contract review found six design/implementation
  hazards: post-app miss-state mutation, global rescue prefix divergence,
  sequential flood jitter, missing R-R comparator, guard-admission versus
  actual TX, and late/censored cost boundaries. The contract was amended
  before any reserved seed. A test-first agent is implementing only a new
  diagnostic tool and tests; its first synthetic no-exposure slice passed.
- Next exact action: independently review the completed tool/tests,
  verify baseline and branch prefix parity plus artifact integrity, then
  run only mechanical seed 34000. Do not run exploratory 34001--34005
  until smoke validates; do not run 35001--35040 or 36001--36040.

## 2026-10-04 - Core-Rewrite Clarification

- Confirmed for the user's question that the intended work is a new
  MeshEcho source-decision/recovery algorithm, not further tuning of the
  existing R/F/D thresholds or treating AFS ACK cancellation as the core.
  Retain the radio simulator, traffic harness, accounting, and old SR/DHR
  policies as infrastructure and controls.
- Re-read the exact current SR and DHR implementation and the prospective
  branch-diagnostic contract. SR uses fixed confirmed-route, two-R-miss,
  and route-age rules; DHR adds a same-flow ACK-guard rescue. The branch
  diagnostic under development is a mechanism-selection instrument, not
  the proposed final algorithm or ICC evidence.
- The diagnostic tool/test agent is finishing synthetic semantics and has
  run no diagnostic population seed. Independently observed that future
  committed TX must be separated from starts inside the run; requested an
  explicit pending-start rejection label, which the agent reports tested.
- Next: receive agent handoff, independently review tool and tests, run
  focused/full regression checks, freeze exact hashes, then only seed 34000
  mechanical smoke if the implementation passes. Reserved 35001--35040
  and 36001--36040 remain unopened.
- The diagnostic tool and 14 synthetic tests were handed off; independent
  static review found no blocking mechanical-smoke issue. Two provenance
  weaknesses were corrected test-first: full application traces are now
  stored as a hashed JSONL artifact, and the CLI pins source hashes before
  replay and refuses mid-run drift. The targeted test went red then green.
  Focused suite: 15 passed. Root full suite: 554 passed, 1 skipped.
- No 34000/34001--34005, 35001--35040, or 36001--36040 seeds have run
  as of this checkpoint. Next freeze six diagnostic source/test hashes and
  run only seed 34000 via the fixed `smoke` CLI with a unique output prefix.
- Frozen six diagnostic source/test hashes in `task_plan.md`; unique
  smoke prefix was absent. Ran only 34000 once: six eligible targets,
  24 branch rows, 40 scheduled applications. The manifest records matching
  frozen hashes, and all three artifact-file hashes match direct SHA-256.
  Local structured checks found 24/24 common prefixes, zero source/data
  action mismatches, zero impossible rescue starts, and zero deadline or
  airtime ordering contradictions. A separate read-only artifact auditor
  is checking replay provenance and accounting before any exploratory run.
- Independent read-only smoke audit matched all six live/frozen/manifest
  source hashes, three artifact hashes, 40 unique ordered applications,
  six target eligibility states, 24 four-arm prefix links, guard/rescue
  markers, deadlines, and reported cost identities. No structural blocker
  remains for the predeclared 34001--34005 exploratory split. Post-target
  individual TX histories are not in the saved artifacts, so exact aggregate
  cost recomputation requires deterministic replay. No reserved development
  or holdout seed was opened.
- Ran the fixed 34001--34005 exploratory split once with unchanged frozen
  source files: per-seed targets 5, 5, 6, 6, 7; total 29 targets and 116
  branch rows. Manifest and all three artifact hashes matched direct
  SHA-256. Local branch aggregation and route-hop inspection are recorded
  in `findings.md`. Two read-only agents are independently auditing artifact
  integrity and interpreting whether a state-dependent, same-budget core
  is feasible. Development 35001--35040 and holdout 36001--36040 remain
  unopened; paper/PDF, VERSION, GitHub, and EDAS remain unchanged.
- Independent exploratory auditors found no malformed seed, target,
  arm, state, action, deadline, or hash evidence. The interpretation audit
  found hop-observable heterogeneity but no novel algorithm or stable
  source-ACK advantage sufficient to freeze a core. Next: write a new
  forward-plus-confirmation algorithm contract, explicitly distinguishing
  it from a simple hop switch, DHR fallback, and same-path ACK repeat;
  preserve 35001--35040 and 36001--36040 unopened until it is frozen.
- Completed two independent read-only design/adversarial screens. Both
  concluded that core rewriting is needed for a stronger ICC algorithm
  claim, but the present branch data do not identify a defensible new
  mechanism. Rejected immediate coding of a STATUS-flood/cache-repair
  idea because its local closure, cost, and prior-art distinction are
  unresolved. The next work is a targeted pre-code feasibility and
  literature screen, not a claim that any new algorithm passed. No paper,
  PDF, VERSION, GitHub, EDAS, or reserved seed was changed this turn.

## 2026-10-04 - Joint-Core Quick Research Continuation

- Classified the previous goal turn as real progress: it implemented and
  tested a branch diagnostic, ran frozen 34000 smoke and 34001--34005
  exploration, audited artifacts, and ruled out simple hop-switch/ACK-
  repeat labeling as a new core. Planning catch-up returned no unsynced
  context. Re-read the three Markdown records and dirty worktree; no
  previous user changes were reverted.
- Started a bounded deep-research quick brief on locally observable joint
  forward-delivery/reverse-confirmation mechanisms. Fixed the question,
  controls, deadline, airtime boundary, and no-seed rule in `task_plan.md`.
  Two read-only agents are checking verified literature and simulator
  feasibility independently. Re-read prior-art, source-signal, and reverse
  ACK opportunity notes; a broad Crossref phrase search was noisy and
  yielded no usable novelty conclusion. No new seeds or core code run.
- Inspected the already-opened 14001--14003 flood ACK-hop artifact and
  current `Simulator.try_receive` failure branches. The artifact locates
  first reverse-hop failures but does not classify physical causes, so an
  ACK-protection schedule cannot yet be justified. No new diagnostic was
  coded or run. Literature/source-verification agents remain active.
- Wrote an explicit, pre-implementation ACK-failure-cause diagnostic
  contract with disjoint 37000/37001--37003 exploratory seeds and a
  stricter intent-commit timing upper bound. Delegated a TDD-only new
  tool/test implementation; no population seed or protocol algorithm is
  authorized in that subtask. Verified 11-byte SF7 ToA as 0.041216 s and
  checked two literature DOI records through Crossref; the latter has a
  directly relevant ACK-copy waiting-time abstract. Bibliography review
  is still in progress.
- Ran two broader literature search queries; their hits were noisy and
  were not used to claim novelty. Waiting for the source-verification
  brief and the TDD synthetic diagnostic implementation. No seeds run.
- Recovered the active work using planning-with-files catch-up (`python3`;
  `python` was unavailable), re-read the current plan/findings/progress,
  checked the dirty worktree, and inspected the current SR/DHR source and
  preregistered ACK-cause contract. No existing changes were reverted.
- Received the verified eight-paper prior-art brief. It narrows any claim
  beyond ordinary ACK priority, multipath ACK, or redundant-forward cancel.
  The diagnostic owner reports six synthetic red-green tests, including
  commitment-before-physical-start and unique-flow accounting, but has not
  completed the baseline replay/hash/CLI gates or run any 37xxx seed.
- Next: receive the diagnostic implementation, independently review it and
  its tests, run regressions, then freeze inputs before only 37000 smoke.
- Inspected the current ICC TeX source and confirmed that it evaluates the
  older calibrated PRR route scorer; source-local SR/DHR is not the paper's
  tested core. The diagnostic owner reports a no-extra-receive-call
  recorder, retained complete TX history, exact plain/instrumented replay
  checks, and an explicit strict intent timing predicate. CLI/manifest
  testing is still in progress; no 37xxx seed has run.
- A separate read-only prior-art/feasibility reviewer judged ACK_INTENT
  insufficient as a full core and listed the concrete packet, visibility,
  half-duplex, commitment, and AFS safety gaps. This does not cancel the
  preregistered unchanged-protocol cause diagnostic; it constrains what a
  positive result could mean. The diagnostic owner is finishing CLI and
  manifest tests; no 37xxx seed or paper/version/remote change occurred.
- Diagnostic owner handed off the tool and 12 synthetic tests; root reran
  full pytest (566 passed, 1 skipped), Python compilation, CLI help, and
  `git diff --check`, all passing. An independent read-only review then
  found a post-deadline failed-ACK-hop exposure bug; a red/green fix is in
  progress and no 37xxx seed has been opened.
- Independent audit additionally found that a TX hash plus selected overlap
  rows cannot prove the absence of another overlapping transmission from
  the saved JSON. Before any new seed, amended the contract to save a full
  compact TX timeline and to require an optimistic remaining-ACK-hop
  airtime lower bound within the 30-s deadline. Assigned test-first
  implementation; 37000 and exploration remain unopened.
- Owner finished all audit fixes test-first; 15 focused tests and 569 full
  tests (1 skipped) passed, confirmed independently by root's full run.
  A separate read-only reviewer found no remaining smoke blocker. Root
  froze seven exact input hashes in `task_plan.md`; next check unique
  output absence and run only seed 37000 mechanical smoke.
- Ran frozen 37000 mechanical smoke once to a unique prefix. Its complete
  plain/instrumented replay and manifest hashes passed; direct SHA-256 of
  the report matches the manifest, seven input hashes match the freeze,
  and a separate `jq` join recomputed every failed-hop overlap set from
  the 648 saved transmissions with zero mismatch. Strict opportunity was
  0/10 delivered-unACKed flows; this is not the exploratory decision.
- Next: only the preregistered 37001--37003 exploration with unchanged
  hashes, then artifact audit and fixed necessary exposure gate. No paper,
  VERSION, GitHub, EDAS, development, or holdout action has occurred.
- Ran the once-only frozen 37001--37003 exploration; exact baseline/observer
  parity and manifest hashes passed. Independently recomputed all 27
  failed ACK-hop records from 2018 saved TX rows with zero mismatch.
  Strict opportunity is 1/24 (4.17%), so both predeclared exposure gates
  fail. Wrote `docs/research/meshecho_ack_failure_cause_results.md` and
  stopped the ACK_INTENT branch before protocol coding. A first `jq`
  pattern query used an undefined `$top` variable; corrected it by
  binding the report's intent-completion field and did not change data.
- No new full-core algorithm, ICC manuscript/PDF edit, VERSION bump,
  GitHub/EDAS action, or 35001--35040/36001--36040 run followed. The
  remaining task is a different prospective mechanism with a distinct
  device-observable trigger, or an explicit narrower-paper decision.

## 2026-10-04 - Goal Continuation After Negative Intent Screen

- Classified the preceding goal turn as substantive progress: it added an
  audited ACK-failure-cause diagnostic, ran frozen 37000 smoke and
  37001--37003 exploration once, and rejected post-delivery ACK_INTENT on
  its prespecified necessary gate. This changes the next mechanism choice.
- Ran planning-with-files catch-up (`python3`, no unsynced output), read the
  current plan/findings/progress and dirty worktree without reverting any
  changes. Read the academic-paper revision and deep-research quick-mode
  skills for the later evidence-to-manuscript sequence; no paper drafting
  is warranted before a valid core/evaluation exists.
- Started two bounded read-only screens in parallel: a pre-delivery
  ACK/forwarding schedule opportunity audit from already-opened traces,
  and a source-core local-observability/adversarial contract screen.
  A third prior-art agent spawn hit the thread limit; continue that check
  locally and do not retry allocation. No new seed, protocol behavior,
  manuscript, version, remote, or EDAS action occurred this turn yet.
- Re-read the BAR negative development result and ICC core-rewrite
  evidence map. Same-path second ACK is an unusually strong mandatory
  control, whereas alternate ACK routing has no resolved increment.
  The current paper remains a calibrated-route evaluation; its source
  and claims have not been edited in this continuation.
- Re-read the actual FLOOD and ACK receive/send paths in `lora_mesh_sim.py`.
  The immediate destination ACK and already-enqueued delayed relay FLOOD
  create the forward/reverse collision interval. A candidate cannot use
  simulator-global delivery state to decide at relays; only a precommit
  local observation or explicitly signaled time reservation is admissible.
- The source-core independent agent completed a read-only no-candidate
  screen and specified the missing destination certificate, the BAR/AFS
  interaction risk, and the necessary same-seed factorial controls. A
  targeted Crossref/OpenAlex check verified DG-LoRa's group ACK slots and
  a 2025 multi-copy LoRa mesh/handshake prototype, constraining the
  novelty of any predeclared slot proposal. The proactive ACK schedule
  opportunity audit remains in progress; no new seeds or protocol edits.
- Checked the prior MAG contract/results and Smart-CALM learning code path.
  Returned min-forward-SNR gating, fixed-budget discovery, and generic
  online profile selection have already been explored or implemented;
  neither may be relabeled as the new MeshEcho-SR core without a distinct
  observable signal and matched superiority evidence.
- The proactive ACK-slot agent completed an independent read-only cause
  decomposition: 17 capture attempts involve 72 overlapping same-flow
  FLOOD TXs, mostly mixed pre/post trigger; a 1.3-s slot fits only the
  inspected traces and an analytic six-hop bound is ~9.38 s before
  queuing. Rejected immediate slot coding. Started one more bounded
  read-only short ACK-flood/corridor feasibility screen, without seeds.
- A first three-file status patch failed because its findings.md context
  did not match the actual last line; no file was changed by that attempt.
  Re-read the exact tail and applied smaller append hunks.
- Resumed with planning-with-files catch-up; `python` was absent, while
  `python3` completed without unsynced output. Inspected the dirty worktree,
  MeshEcho-SR source decision/timer/ACK code, and frozen AFS/ACK-cause
  reports. No source code, seed, paper, version, GitHub, or EDAS action.
- The final read-only short-ACK/corridor screen found timing exposure but no
  observed device-local corridor or demonstrated advantage over delayed
  same-path ACK repetition. Recorded its conditional no-code decision in
  `task_plan.md` and `findings.md`. The user-facing distinction remains:
  rewrite the source/recovery algorithm if claiming a new protocol, while
  retaining the simulator and old policy as comparison infrastructure.
- Active-goal continuation classified the prior turn as progress because it
  incorporated the last negative feasibility screen into the authoritative
  Markdown records. Planning catch-up returned no unsynced output and the
  dirty worktree was preserved. Two read-only independent screens examined
  corridor instrumentation and source-policy observability; neither ran
  seeds or changed protocol/paper/remote state.
- The source-policy screen established a one-hop indistinguishability
  argument for forward DATA loss versus reverse ACK loss under current
  packets. Updated the plan to stop source-only threshold/controller
  proposals and require a separately charged source-decodable certificate
  with an equal-budget same-path ACK control.
- Drafted a passive corridor diagnostic, then independent pre-code review
  found that changing immediate ACK timing changes future FLOOD decodes,
  invalidating its proposed necessary no-go gate. Marked the draft
  superseded; no 380xx seed, ACK_FLOOD code, or paper change occurred.
- Wrote `docs/research/meshecho_delayed_ack_control_design.md` for a
  fixed-2-s single-FLOOD-ACK timing control and dispatched separate TDD
  implementation and paired-runner work. Both tasks are restricted to
  synthetic tests until root reviews source hashes and opens only smoke.
- Protocol implementation owner added the fixed-2-s FLOOD ACK control and
  reported the expected red-first unknown-protocol test, then three passing
  focused behavior tests. Root inspected the zero-delay base hook, subclass,
  registry mapping, and public tests; no core-design mismatch found yet.
  A concurrent full-suite run saw a runner-test import error because the
  separate runner module did not yet exist. Root will rerun once both
  independent edits are complete; no 38xxx seed has run.
- Independent core audit found the new arm missing from DHR packet-category
  accounting and `Simulator.run()` dropping its first post-cutoff event.
  Root added red/green tests and narrow fixes in `run_sr_experiment.py` and
  `lora_mesh_sim.py`. Added marked-recovery, queue-busy, late-ACK, and
  cutoff-continuation behavior tests. Eight delayed-control tests and 194
  existing SR/DHR tests pass. Runner implementation is still in progress;
  no 38xxx seed, paper, VERSION, GitHub, or EDAS action occurred.
- Paired runner owner completed a 13-test synthetic suite and source/manifest
  writer without using research seeds. Root independently ran the stable
  full suite: 590 passed, one skipped (37.41 s). Independent runner audit
  found cost-window and saved-ACK-evidence validation gaps; root stopped
  seed 38000 and returned these to the owner for test-first repair.
- Clarified the user's algorithm question against current source and paper:
  the ICC manuscript evaluates calibrated MeshEcho, while SR/DHR are later
  experimental controllers. A stronger algorithm paper requires a substantive
  new source/ACK/recovery mechanism, not threshold tuning or the fixed-delay
  ACK control. Preserve the simulator, PHY/event/metric harness, and old
  policies as comparators; no candidate core has passed its gate yet.
- Resumed the planning record after context handoff. The skill catch-up's
  `python` invocation failed because the command is unavailable here;
  `python3` succeeded with no unsynced output. The dirty worktree was
  inspected and preserved. Runner repair continues without 38xxx runs.
- Runner owner repaired the 630/660-s cost-window flags, linked saved
  first-FLOOD receipts to destination receive actions and ACK starts,
  enforced the 2-s delay, and added strict per-seed deterministic replay.
  Root independently ran the full suite: 596 passed, 1 skipped (37.97 s);
  `git diff --check` and `py_compile` pass. A separate read-only re-audit is
  pending; no 38xxx run has been opened.
- Independent re-audit found no blocker. Frozen nine source/test/design
  SHA-256 values in `task_plan.md`, then ran only seed 38000 mechanical
  smoke once. Its manifest validates and strict deterministic replay passes.
  Delayed/immediate one-seed source ACKs are 34/29 of 36, destination
  deliveries 36/36, airtime 43.099136/50.773248 s. An independent
  read-only artifact audit is pending before the already frozen 38001--38020
  exploration. No new core algorithm, paper/VERSION/GitHub/EDAS change, or
  sealed development/holdout run occurred.
- Independent smoke audit gave GO. Ran the predeclared 38001--38020 paired
  exploration once with source hashes unchanged. Its saved manifest passed
  local validation; a separate read-only auditor verified all input and
  artifact hashes, exact immediate-arm stock parity, physical 2-s ACK
  timing, paired statistics, and strict replay of all 40 runs. Wrote
  `docs/research/meshecho_delayed_ack_control_explore_results.md` with
  +0.2251 paired ACK-PDR gain and -16.73% relative airtime as exploratory
  results only. The control is not a core rewrite; paper/PDF, VERSION,
  GitHub, EDAS, and sealed 350xx/360xx cohorts remain untouched.
- Classified that prior turn as progress, ran planning catch-up with no
  unsynced output, and preserved the dirty worktree. Used the research
  skill's quick scoping stage to frame the next full-core question in
  `docs/research/meshecho_feedback_core_rq.md`; novelty remains a gate,
  not an assumed property. Two independent read-only audits are examining
  local ACK-timing signals and source-controller feasibility. No new
  simulation seed, behavior code, paper, version, or remote action yet.
- Independent source audit rejected freezing a source-only timeout/hop
  selector as a new core. Local ACK audit joined already saved 38xxx
  actions and receipts, finding 235/251 first FLOODs with a destination-
  decoded duplicate inside 2 s, and documented both post-ACK copies and
  inaccessible simulator-only signals in
  `docs/research/meshecho_local_ack_quiescence_exposure.md`. Close prior-
  art review is still in progress. No new seed, behavior code, or paper
  change followed this passive screen.
- Completed a targeted quick prior-art screen with seven verified DOIs,
  five inspected original sources, and explicit full-text gaps for Lee
  2020 and Solé 2026. Wrote
  `docs/research/meshecho_ack_timing_prior_art_quick_brief.md`; it rejects
  broad delayed-ACK/overhearing novelty claims while leaving a narrow
  local-decode quiet-rule hypothesis unverified. No simulation or paper
  claim was changed.
- Resumed with planning-with-files catch-up (`python` unavailable;
  `python3` succeeded), checked the existing dirty worktree, and received
  two independent quiet-ACK audits. Both judge quiet-only ACK insufficient
  as a new MeshEcho-SR core. Dispatched read-only residual ACK diagnosis
  and source-core contract screens; no behavior code, seed, paper, version,
  GitHub, or EDAS action has occurred in this continuation.
- Inspected the current SR/DHR source and ICC LaTeX: the manuscript still
  presents calibrated route scoring; the fixed-delay arm does not replace
  source F/R/D or its 15-s timeout. A further independent prior-art agent
  could not be spawned because the thread limit was reached; do not retry
  that allocation in this continuation. `git diff --check` passes.
- Received residual reverse-ACK diagnosis and source-design review. Wrote
  the read-only fixed-delay residual screen and recorded quiet-only/path-
  choice NO-GO as a full core. No new simulation seed, behavior source,
  manuscript/PDF, VERSION, GitHub, or EDAS action was taken.
- Independently recomputed the delayed-arm flow denominators with `jq`:
  781 total, 55 source misses, 44 delivered misses, 42 FLOOD ACK misses.
  `git diff --check` passes. The residual screen records that all saved
  FLOOD forward-margin fields are null; alternative ACK path quality is
  therefore not inferable from these artifacts.
- Continued the active full-core/ICC goal after that substantive diagnostic
  progress. Read the planning, academic-paper and TDD skill instructions,
  ran planning catch-up with no unsynced report, and preserved the dirty
  `version/v2` worktree. Started two independent read-only full-core
  mechanism screens; no new seed, behavior code, manuscript, version,
  GitHub, or EDAS action has occurred in this continuation yet.
- Inspected packet serialization, the ACK route/receive path, and the
  fading model to set implementation constraints for a complete rewrite.
  ACK path-index enforcement and one-ACK flood deduplication are currently
  shared behavior; changing either needs explicit public-behavior tests.
- Independently grouped saved 38xxx delayed-arm residual FLOOD cases by
  recovery marker using `jq`: 12 initial-F and 30 recovery-F of 42. Added
  this decomposition to the residual research note; it is an exposure
  result, not a closed-loop earlier-recovery trial.
- Inspected `RadioConfig`, desired/interference RX-power calculation,
  fixed-current TX-energy accounting, and the recurring-fading case for
  a locally measured reverse ACK power-control candidate. Asked two
  independent read-only reviewers for feasibility/prior-art objections;
  no power behavior or new seed has been changed or run.
- Resumed the active core-rewrite goal after a clarification-only turn.
  Planning catch-up produced no unsynced report; `git diff --stat` shows
  substantial existing research changes, which remain preserved. The
  previous goal turn answered the user's boundary question but made no
  authoritative algorithm or paper progress. Dispatched a bounded joint-
  core contract draft, an adversarial read-only screen, and an independent
  alternative screen. No new simulation seed, core behavior, manuscript,
  version, GitHub, or EDAS change has occurred in this continuation yet.
- Re-read the active plan and latest findings. The fixed-2-s ACK policy is
  now the strong simple control; 35001--35040 and 36001--36040 remain sealed.
  The opened 38xxx residuals show ACK-path and 30-s repair-budget questions,
  but no causal proof that path diversity, extra ACK, or power adaptation
  works. Candidate design must be judged against these facts before code.
- Independent adversarial and alternative screens both declined to freeze
  delayed-path JFC as a new core: BAR already tested alternate-path extra
  ACK against same-trigger same-path repetition and failed its incremental
  gate. The strongest safe next action is a behavior-preserving per-ACK-RX
  diagnostic on fresh exploratory seeds, followed by a fixed-2-s equal-
  budget repeat control before choosing a full joint source/feedback policy.
  Existing 38xxx receipts expose path/time but not SNR, per-receiver failure
  cause, or off-index source decodes. No new seed has run yet.
- Added prospective `meshecho_delayed_ack_rx_diagnostic_design.md` with
  39000 mechanical smoke, 39001--39020 passive exploration, exact stock
  parity and off-index exposure no-go gates. Added a fixed-2-s one-repeat
  comparator design with a destination-local 10-s queued-start cap;
  destination cannot use simulator-only source `created_at` as a deadline.
  Dispatched test-first implementations of the diagnostic and control.
  An independent designer added `meshecho_joint_core_candidate.md`, a
  full but untested JFC contract; it is retained as a falsifiable
  hypothesis, not a paper contribution. Existing artifact aggregation
  also found 164 R-to-F recovery starts and 129 accepted recovery ACKs
  in the 38xxx delayed arm. No new seed has run yet.
- Inspected the shared SR runner before integrating the new simple control.
  `summarize_windowed_transmissions` uses an explicit `DHR_FAMILY_PROTOCOLS`
  list for ACK and source-recovery subcategories. A new fixed-delay repeat
  protocol will require a red/green regression test and registration in
  that list; otherwise component counts under-report it despite total
  airtime counting every physical TX. Added a single synthetic test in
  `tests/test_delayed_ack_repeat_runner.py`; it failed on the missing DHR
  recovery bucket as expected. Registered the new repeat protocol in
  `tools/run_sr_experiment.py`; the test and all 19 delayed-control runner
  tests now pass. No research seed was run by this change.
- The fixed-2-s same-path repeat protocol and 12 public behavior tests are
  implemented; 29 focused tests passed. Independent read-only audit found
  no protocol blocker but confirmed old 38xxx runner hashes cannot validate
  current code and its two-arm structure cannot evaluate the repeat arm.
  Corrected the comparator design's invalid destination-flow-completion
  cleanup wording to local repeat/expiry only, reserved 41000/41001--41020,
  and dispatched a fresh test-first paired runner with independent stock
  parity. A first wording patch missed a wrapped line; the narrowed retry
  succeeded. No repeat research seed, manuscript, or remote action occurred.
- Source-timing review found all 451 accepted initial R ACKs within
  0.149--0.637 s of actual source R TX start. Added a prospective
  short-guard simple-control design with 1/2/4/8-s arms against 15 s,
  reserved 40000/40001--40020, and dispatched test-first implementation.
  These are controls, not the requested new source algorithm.
- Added a single synthetic runner classification test for all four
  short-guard labels. It failed for each missing DHR recovery bucket;
  adding the four identities to `DHR_FAMILY_PROTOCOLS` made it and the
  repeat-runner classification test pass. The protocol owner identified
  that globally changing `ack_guard_s` would also alter initial F and D
  timeout state, so the short-guard variant now targets only an R-specific
  early timer while inherited 15-s non-R semantics remain unchanged.

## 2026-10-04 - Core-rewrite clarification and control handoff

- Rechecked the user's algorithm question against the current ICC LaTeX and
  frozen evidence. A stronger algorithm-centered ICC claim needs a genuinely
  new source/feedback/recovery core, not retuning the existing route score,
  source thresholds, or a fixed ACK timer. Retain the simulator, radio/event
  model, complete-network accounting, and old protocols as matched controls.
  The JFC design remains an untested hypothesis, not a paper contribution.
- The passive 39xxx ACK-RX diagnostic, 40xxx fixed short-guard controls, and
  41xxx fixed-delay same-path repeat control/paired runner now have focused
  synthetic tests. No 39000/40000/41000 smoke or exploration seed has run;
  the ICC manuscript/PDF, VERSION, GitHub, and EDAS remain unchanged.
- Root verification after the parallel edits and runner audit fixes:
  `python3 -m pytest -q` reported 649 passed and 1 skipped; Python
  compilation and `git diff --check` passed.
- Independent runner audit found and the owner reproduced a pre-smoke
  blocker: first recovery FLOOD after an already-delivered R DATA is logged
  `dhr_destination_rx.duplicate=True` even though it is that FLOOD's first
  decode and emits ACK. A red public-runner regression exposed the missing
  receipt/orphan repeat; the receipt capture and ACK audit now include it.
  A real nonreserved seed-1 replay of this path passes.
- A second red regression exposed false 630/660 replay failures when a TX
  or action is appended before cutoff but has a later physical/logged time.
  The validator now compares TX/action/receipt append-order prefixes and
  permits later `source_action` resolution while retaining deadline-outcome
  checks. The focused runner suite passed 29/29. Research smoke 41000 and
  all 39xxx/40xxx/41xxx explorations remain unopened; no experimental GO,
  manuscript, version, GitHub, or EDAS claim follows from unit tests alone.

## 2026-10-04 - Passive ACK-RX Diagnostic Continuation

- Classified the prior goal turn as progress: it completed three simple
  control/diagnostic implementations, 649-pass full regression, and a
  runner audit that changed the next safe action. Session catch-up found
  no unsynced context; the existing dirty worktree was preserved.
- Re-read the academic-paper, planning-with-files, and TDD instructions.
  Kept the ICC manuscript/PDF unchanged because no new core algorithm or
  validated population result exists yet.
- Independent read-only diagnostic audit and 13 focused tests gave GO for
  seed 39000 only. Froze eight input SHA-256 values in `task_plan.md` before
  the run. The one-seed smoke produced exact stock parity and 25/25 deadline
  ACKs/deliveries; it had no delivered-unACKed FLOOD case. Seven artifact
  hashes, all eight input hashes, manifest validation, saved-file counts,
  and one strict deterministic same-seed replay passed independent audit.
- Opened the exact preregistered 39001--39020 passive exploration once via
  that smoke manifest. Initial saved summary: 816 scheduled flows, 810
  deadline deliveries, 763 deadline source ACKs, 47 delivered-unACKed FLOOD
  flows, and one identity-valid in-deadline off-index source ACK decode
  (1/47=2.13%, below the predeclared 4-flow/10% necessary gate). This
  result is **pending independent artifact and replay audit**; it is not a
  positive core claim. ACK path-category counters count attempts, not
  distinct flows. The 350xx/360xx cohorts and ICC paper/VERSION/remote
  remain untouched.
- A separate read-only 41xxx audit found that the repeat runner could accept
  missing-repeat/no-drop evidence and omit extra off-path ACKs, with a
  660-s future-start cost flag gap. A test-first repair is in progress;
  41000 is NO-GO until it passes. The 40xxx paired runner is also in
  progress without reserved seed runs.
- Independent 39xxx exploration audit completed: all eight frozen inputs,
  seven artifacts, smoke-link SHA-256, 816 flow denominators, 13,312 TX,
  4,272 actions, 2,426 ACK reception attempts, and all 20 same-seed strict
  replays passed. The predeclared off-index exposure gate failed at one
  valid candidate among 47 delivered-unACKed FLOOD flows (2.13%). Logged
  the NO-GO and failure-class breakdown in `task_plan.md` and `findings.md`.
  No new core has been selected and the ICC paper/PDF/VERSION/remote remain
  unchanged.

## 2026-10-04 - Same-time ACK/guard verification

- Resumed from the three planning files and preserved the existing dirty
  worktree. `python3` planning catch-up reported no unsynced context.
- A previously red public test exposed that a source guard could run before
  an ACK whose physical TX completed at the identical timestamp. The pending
  scheduler change orders `tx_end` before protocol timers and `tx_request`
  after them at a tied time, preserving registration order within each class.
  The exact guard-boundary test now passes.
- On this current worktree, the full suite passed (672 passed, 1 skipped in
  40.52 s); `py_compile` of simulator and both new runners and
  `git diff --check` passed. Independent review of shared event-order effects
  and the 40xxx pre-smoke gate is still pending. Old 39xxx artifacts remain
  evidence for their frozen source hash, not the current scheduler version.
- The 41xxx repeat runner owner reports 38 focused tests, syntax, and diff
  checks passing after tightening ACK and capacity audits. No 40000/41000
  reserved seed or 350xx/360xx holdout run has occurred here; no new core,
  ICC paper/PDF, VERSION, GitHub, or EDAS change follows from these tests.

## 2026-10-04 - Simple-control mechanical smokes

- Added public same-time receive/timer regression tests for RREQ, RREP, and
  SmartCalm ACK boundaries in `tests/test_simultaneous_rx_timers.py`.
  The full current suite passed (675 passed, 1 skipped in 40.67 s);
  `git diff --check` passed. Independent scheduler review found no direct
  fault and warned that old pre-change cohorts are not current-code controls.
- Independent pre-smoke reviews gave GO for exactly seeds 40000 and 41000.
  Frozen the current input SHA-256 lists in `task_plan.md` before execution.
- Ran one 40000 short-guard mechanical smoke with five arms and one 41000
  same-path-repeat mechanical smoke with two arms, each at a distinct new
  result prefix. Both runner commands exited successfully and wrote manifests
  at `results/meshecho_delayed_ack_short_guard_smoke_seed40000_20261004`
  and `results/meshecho_delayed_ack_repeat_smoke_seed41000_20261004`.
  Their manifest input hashes match the pre-run freeze. Independent artifact,
  stock-parity, and strict-replay audits are in progress; 40001--40020 and
  41001--41020 remain closed until those audits give GO. Smoke performance
  numbers are not a population result or a new algorithm claim.
- No new core, ICC paper/PDF, VERSION, GitHub, EDAS, or sealed 350xx/360xx
  cohort change was made in this phase.
- Independent saved-artifact audits then stopped both smoke gates: JSON
  reload changes `path`/`learned_path` tuples to lists, causing the runners'
  RREP byte reconstruction to overcharge the redundant learned path.
  Strict manifest validation fails for 41000 by 69 bytes per arm and for
  40000 by 95 or 108 bytes by arm. Both original result prefixes are kept
  as failed smoke artifacts; neither exploration cohort has run. Parallel
  test-first fixes are limited to each runner's packet reconstruction and
  its regression tests, followed by fresh hashes and distinct smoke prefixes.
- Targeted deep-research fact-check closed the Solé et al. 2026 full-text
  gap using its open UPC PDF and retained a clearly marked Lee et al. 2020
  full-text gap. The narrowed mechanism/prior-art boundary is recorded in
  `findings.md`; it does not promote JFC or change the ICC manuscript.
- Both JSON-type runner fixes passed red-to-green tests and the full suite
  (677 passed, 1 skipped). The shared simulator hash is unchanged. Froze
  second-version runner/test hashes in `task_plan.md`, then ran one new
  mechanical smoke per control with `*_v2_20261004` result prefixes.
- Independent v2 audits gave GO: 40000 has 12/12 source and 10/10 artifact
  hashes, five-arm strict replay and stock parity; 41000 has 8/8 source
  and 11/11 artifact hashes, two-arm strict replay and stock parity.
  Physical timing, 630/660-s full-TX cost, and per-flow records reconciled;
  there was no post-630 TX. Only the preregistered 40001--40020 and
  41001--41020 exploratory cohorts are now open. The old failed smoke
  artifacts remain preserved and no sealed cohort was touched.
- Ran each preregistered 20-seed simple-control exploration once via its
  v2 smoke manifest, without editing frozen inputs. The 41xxx repeat arm
  completed; independent 8/8 input, 11/11 artifact, 40-run strict-replay,
  stock-parity, physical-timing, and per-flow audits passed. Its small
  exploratory gain and uncertainty are recorded in `findings.md` and
  `task_plan.md` as a comparator, not a new algorithm.
- The 40xxx short-guard run failed before writing results when
  `audit_guard_contract` could not find a guard action after a physical R
  TX. No 40xxx exploratory artifact exists. Root-cause investigation is
  in progress; the full cohort must not be rerun or treated as evidence
  until the exact flow and contract are resolved with a red regression.
- Read-only root-cause replay located the first 40xxx failure at seed
  40005, guard2, flow 19. Original decision D fell back to physical R
  DATA after a discovery timeout. The audit wrongly used final
  `source_action=R` as evidence that the R-specific short guard was owed;
  actual protocol only arms it for an initial R decision. The normal
  15-s timeout fired as inherited. This is a runner contract error, not
  yet a source behavior change. Test-first strict decision classification
  is underway; the 400xx cohort will remain exploratory after any rerun.
- Fixed the 40xxx runner audit test-first without changing protocol or
  shared simulator behavior. It now uses each flow's unique logged initial
  decision, records D-to-R scope/15-s timeout and excludes that path from
  DHR recovery, while still rejecting true initial-R missing guards.
  Seed 40005 guard2/flow19 preflight and 29 focused tests passed; root's
  full suite passed 680 tests (one skipped), compilation and diff checks
  passed. Independent static review gave GO for one newly frozen smoke.
  The three changed 40xxx input hashes are frozen in `task_plan.md` as v3;
  41xxx frozen hashes and audited results remain unchanged.
- Ran the newly frozen 40000-v3 mechanical smoke at a distinct prefix.
  Independent review verified 12/12 input and 10/10 artifact hashes,
  official strict replay, current stock parity, five-arm all-flow and
  guard timing audits, and 630/660-s cost parity; GO for one documented
  quality-control rerun of opened 40001--40020 only. The smoke itself has
  no D-to-R fallback, so the rerun must explicitly verify 40005/guard2
  flow19. No sealed seed or paper/remote change followed this smoke.
- The 40001--40020 v3 quality-control rerun completed and produced its
  distinct manifest. An independent read-only audit is checking all
  hashes, strict replay, stock parity, and the 40005/guard2/flow19 D-to-R
  case before any result interpretation.
- Recovered the session using the planning skill; its documented `python`
  command was unavailable locally, while `python3` completed with no
  unsynced context. Re-read the three research records and preserved the
  dirty worktree. Clarified for the user that the algorithmic core needs
  replacement while the simulator and baseline harness remain reusable.
- Independent 40001--40020 QC-v3 audit finished successfully: all 12 input
  and 10 artifact hashes, 200 strict arm replays, and 20 current-code stock
  checks passed. The seed-40005 guard2 flow19 D-to-R/15-s/no-recovery
  contract also passed. Short guards did not beat guard15 on ACK PDR or
  whole-network airtime; the opened QC cohort remains exploratory. No
  manuscript/PDF, VERSION, GitHub or EDAS action was taken.
- Began the next core-feasibility phase with planning, academic-paper and
  TDD instructions re-read. Planning catch-up found no unsynced context;
  inspected the dirty worktree and the two existing diagnostics. Dispatched
  independent read-only first-edge contract and adversarial algorithm
  reviews. No protocol behavior, seed, paper, or remote action yet.
- Independent reviews identified the JFC `P[-2]` versus `P[1]` target
  mismatch, direct-to-two-hop ACK airtime disadvantage, weak ACK-selector
  headroom versus fixed-2-s repeat, and uncalibrated margin score. Marked
  JFC NO-GO as written and created a frozen passive first-edge signal/cost
  gate. Dispatched test-first diagnostic implementation and a separate
  formal source-controller design review. No reserved seed opened.
- The formal source review advised against freezing a source-only new
  core. Dispatched a bounded read-only risk-signal analysis using existing
  38xxx artifacts, with decision-time-only features and initial-R ACK
  before guard as its label. Existing flow/action artifacts were inspected
  to avoid treating recovery-F final ACK as initial-R success. No new seed
  or protocol behavior was changed.
- Reviewed the first-edge diagnostic implementation in progress and
  corrected the pre-seed contract: path-exposure and same-path-repeat
  predictor gates are independent; ACK2 nominal spacing is 0.5 s; late
  final-hop ACKs cannot be channel-predictor failures; the frozen q-only
  logistic and training support are explicit. The test-first agent reports
  10 focused tests passing without reserved seeds. A separate TDD source
  screen confirmed 613 true initial-R starts versus 615 final R labels.
- Completed the source-local risk screen on previously opened 38xxx
  artifacts with exact historical provenance, eight focused tests and
  a documented NO-GO support result. The source-only policy remains
  unimplemented; no new seed, paper claim, version or remote action.
- Independent first-edge code review found an ACK2 timing-bound mismatch
  and missing per-path-type predictor gates; implementation and frozen
  contract are being corrected before the 42000 mechanical smoke.
- Root independently ran the source risk tool against the frozen 38xxx
  artifacts and its eight focused tests. The script output reproduced
  613/449 initial-R counts, all three Brier scores, paired intervals and
  failed support gates; `docs/research/meshecho_source_risk_signal_gate.md`
  records the complete result. No simulation or new seed was run.
- Classified the last clarification-only turn as no new implementation or
  experimental progress, then resumed the active core-rewrite goal.
  Planning catch-up found no unsynced context; existing worktree changes
  were preserved. Re-read the planning, TDD and academic-paper skill
  instructions and dispatched read-only first-edge and core-design audits.
- Ran the post-correction source risk focused suite: 10 passed. Re-ran
  `tools/diagnose_source_risk_signal.py` on archived, hash-verified 38xxx
  artifacts: 613 initial R, 449 initial-R ACKs, identical Brier/CI values
  and unchanged NO-GO support gates. The full suite then passed 704 tests
  with one skipped in 40.96 s. No reserved seed or policy behavior changed.
- Ran 14 focused first-edge diagnostic tests, all passing, then an
  independent read-only reviewer found cutoff-late final-hop count,
  path-type training-support and manifest semantic-integrity gaps. ACK2
  timing was confirmed. Dispatched test-first repairs without opening
  any 42xxx seed or changing the current protocol.
- An independent read-only 41xxx artifact screen rejected the provisional
  ACK-copy-informed fragile-route full core on exposure: 16 ACK2-first
  accepts, 13 clean subsequent source decisions, and 12 tail-reachable
  decisions across seven seeds. No wire-level copy index exists in the
  old control, so this is forensic opportunity only. Recorded the
  provisional NO-GO without adding policy code, manuscript claims or
  new simulation seeds.
- The first-edge diagnostic owner completed four TDD repairs across its
  tool, test and contract files: late final-hop exposure, whole-epoch
  causality rejection, type-specific train/validation support, and
  hash-valid manifest/model recomputation. Focused tests passed 20/20;
  root reran all tests via `pytest` (710 passed, one skipped, 40.98 s)
  and compiled the tool/test files. A separate pre-smoke audit is pending.
- Started a narrow deep-research prior-art fact-check. Its preliminary
  verified sources indicate hop ACK repeat, ACK/signal-based link-quality
  estimation and route repair are not independently novel; no citation or
  ICC claim is being promoted before the final source audit.
- Independent pre-smoke reviewer gave GO for exactly one 42000 mechanical
  first-edge run. Froze nine input SHA-256 values in `task_plan.md`, then
  ran that single seed at a new prefix. The runner saved a manifest and
  artifacts, reporting 49 flows and 10 final-hop predictor samples; an
  independent saved-artifact and strict-replay audit is underway. No
  exploratory/validation or sealed seed has been opened.
- A read-only source-ACK-SNR feasibility audit identified a higher-
  availability device-local signal not saved in current artifacts, and
  proposed a separate passive 430xx split. No SNR feature or behavior
  was implemented and no 430xx seed was run; prior-art and contract
  review precede any such work.
- Completed the narrow deep-research fact-check and saved the verified
  citation/mechanism boundary in
  `docs/research/meshecho_feedback_prior_art_boundary.md`. Lee et al.
  full-text access remains an explicit gap. The check ruled out claims of
  novelty for individual ACK repeat, ACK-SNR route quality and R-to-F
  repair primitives; no paper citation or result was changed.
- [error resolved] An attempted read of nonexistent
  `docs/research/meshecho_mag_dev_results.md` returned no such file.
  `docs/research/meshecho_mag_design.md` contains the revision-3
  development outcome and was read instead; no file was modified by
  the failed read.
- Independent 42000 smoke audit passed all frozen input/artifact hashes,
  official manifest validation, complete saved metrics/flow/action/TX/
  path/epoch/predictor counts, strict replay and both RNG states. It
  recomputed ACK costs and confirmed that the two smoke candidate paths
  satisfy a single-alternative-versus-two-repeat budget only, not an
  original-plus-alternative equal-budget claim. Authorized the exact
  42001--42020 passive exploration; 42101--42120 remains gated.
- Ran exactly the prespecified 42001--42020 first-edge passive exploration
  via the verified smoke manifest and a new output prefix. The runner
  saved artifacts; built-in explore manifest validation passed. Initial
  counts fail both the alternate-path eight-flow minimum (6/20 source-
  final failures meet all A/B/C/deadline conditions) and direct/multihop
  predictor training support. Independent 20-seed strict-replay audit is
  in progress. Kept predictor validation 42101--42120 sealed.
- Drafted (but did not freeze or run) a separate source-local accepted-ACK
  SNR observational gate in
  `docs/research/meshecho_source_ack_snr_signal_gate.md`. It defines
  decision-time-only features, R-before-guard labels, 430xx split,
  same-route/source-neighbor joins, simple predictor controls, support
  stops and symmetric-PHY limitations. It needs independent contract and
  fitting review before any seed or behavior implementation.
- [error] `python3 -c 'import scipy, sklearn'` failed because SciPy is
  absent in the current Python environment. The prospective source-SNR
  contract therefore does not assume those packages; NumPy 2.0.2 is
  available, but any fitting implementation still needs deterministic
  tests and an independently checked reference.
- Independent read-only 42001--42020 audit passed nine source hashes,
  eight artifact hashes, smoke link, official manifest validation and
  strict replays of all 20 seeds. Its independent 12,632-TX/748-path/
  483-alternative arithmetic confirmed both predeclared research branches
  NO-GO: six fully eligible path flows versus eight required, and no
  direct/multihop q-predictor training support. Preserved 42101--42120,
  350xx and 360xx unopened; no protocol, paper, version or remote action.
- Resumed the persistent core-rewrite goal after a clarification-only turn,
  which made no implementation or experimental progress. Re-read the three
  planning files and relevant planning/TDD/paper instructions. The session
  catch-up script reported no unsynced context. Independent reviews are
  examining the source-ACK-SNR contract and a distinct joint core candidate;
  no 430xx seed, protocol behavior, manuscript, or remote state has changed.
- Added a first red/green passive ACK-SNR capture slice: a test first failed
  because the new diagnostic module was absent, then a minimal subclass
  recorded source ACK `RxInfo` from the original single `try_receive` call.
  The first green attempt exposed a test-only error (`Metrics` is not a
  dataclass, so `asdict` raised `TypeError`); the test now compares its
  actual fields. No protocol behavior or research seed was changed.
- Completed two passive-capture TDD slices: the direct ACK fixture confirms
  full TX/metric/both-RNG parity, and a second red/green fixture strictly
  joins an accepted source ACK to its unique physical TX and RxInfo. Focused
  `tests/test_source_ack_snr.py` is 2/2 green. The join rejects missing or
  ambiguous actions and invalid accepted paths; further rejection,
  generation, and full-run replay tests remain before any 430xx smoke.
- A same-time commit-order test initially failed because its hand-built
  FLOOD fixture had no source destination state, so the accepted ACK could
  not commit a route. Replaced that fixture with the public `app_send`
  event path; the failed hand-built fixture is not evidence about DHR
  event ordering.
- The real `app_send` fixture then failed as intended on missing
  `action_order`; passive joins now retain global action order and verify
  commit precedes its ACK-acceptance event. Added a decision-time initial-R
  cohort builder and real F-then-R test, requiring the prior same-generation
  ACK and original-guard ACK label. A non-research small-case `run_diagnostic`
  test now passes stock/passive full-row, flow, action, TX, both-RNG parity
  and a second exact passive replay. Current focused suite: 6 passed. No
  430xx seed was run; no algorithm policy or ICC manuscript changed.
- Ran one ordinary software-QC seed 1 on the current recurring-fading case,
  explicitly outside the reserved 430xx cohorts. It produced 47 flows,
  61 physically decoded source ACK rows and 39 initial-R rows, with zero
  structural exclusions, exact stock parity and exact passive replay.
  The 39 rows split 29 multihop/10 direct and include 30 initial-R ACKs by
  guard; these inspected data are only a diagnostic fixture, not training,
  holdout, or evidence for a policy effect. No source or paper claim was
  selected from this seed.
- Independent capture audit found two P1 errors. A real late-old-R-ACK
  after a same-path recommit failed its red test by selecting the old TX;
  q selection now follows the originating R decision's generation (or the
  exact commit-triggering ACK). A queued R across a same-path recommit
  failed its red denominator test by disappearing; it now remains a full
  row with q missing and `route_commit_before_tx`. A provisional route
  with no prior commit is likewise retained with `no_prior_commit`.
  A duplicate-decision red test now fails closed. Current focused capture
  suite: 11 passed. No 430xx seed or protocol-behavior change.
- Capture focused tests and the first-edge diagnostic suite passed together
  (31 tests). Ordinary seed 1 still yields 39 initial-R rows with exact
  stock parity and strict replay after the P1 fixes. A real timeout-before-
  late-ACK fixture passed and sets the next R's `prior_r_miss=1`. The
  independent capture rereview found no further P0/P1 in q provenance,
  denominator or ordinary guard labeling, but exact guard-tie, duplicate/
  late ACK and later-recovery reporting checks remain before freeze.
- [review correction] A concern that the q-only AUC implementation inverted
  ranks was my reading error: Python's ascending sort on `-q` places high-q
  successes first, yielding AUC 1 for the perfect low-q-failure example.
  The model owner added explicit perfect/reverse fixtures to guard this.
- [integrity incident] A parallel no-overwrite/seed-guard red test invoked
  reserved seed 35001 and part of 36001 before rejection was implemented;
  it also completed 42101 and repeated the already-opened 42000 in memory.
  The test called `run_report`, never `write_report`; root found no matching
  saved artifact or active diagnostic/pytest process. No outcome
  interpretation is permitted. Mark 35001, 36001, and 42101 contaminated
  for future untouched-holdout purposes; 42000 adds no independent data.
  Subsequent guard tests stub `run_diagnostic`, and 20 focused tests passed
  without simulation. Other reserved seeds stay closed.
- Answered the user's algorithm-boundary question with a correction: a new
  ICC algorithm contribution requires rewriting MeshEcho-SR's core F/R/D
  and recovery decisions, while preserving the simulator, PHY, scheduler,
  accounting and old protocols as controls. Independent read-only review
  found no existing candidate justified for positive manuscript promotion.
- Repaired the passive ACK-quality gate in red/green slices without opening
  430xx: added physical later-recovery attribution and a direct reserved-
  seed guard, same-row clean-SNR sensitivity fitting/scoring, complete-path
  denominator and offline age/interference/fading summaries, and validation
  against actual smoke/exploration manifest files. The focused gate suite
  passed 25 tests; capture and model owners reported 26 and 21 respectively.
  The contract remains draft; 43000 is still closed pending integrated audit.
- [error resolved] The first documentation patch included a nonexistent
  trailing context line and applied to no file. Re-read the exact contract
  text and applied smaller patches successfully; no experiment or seed was
  affected.
- [integrity incident] An independent auditor's fake-smoke test was racing
  the new manifest replay implementation. The code invoked the real 43000
  stock/passive/replay diagnostic once, then rejected the fake artifact.
  Auditor inspected no 43000 performance values and wrote no project result;
  root confirmed no active process or 43000/43200 result file. 43000 is
  contaminated as an untouched smoke. Re-registered unused 43200 and kept
  all real cohorts closed. Added a red/green test and explicit `replay=True`
  gate so passive manifest inspection cannot implicitly run a real seed.
- Root cause of one nonreserved seed-1 integration check was a test caller
  passing raw tuple-valued `Packet.path` to an audit of JSON-normalized
  saved rows. Applying the same JSON normalization as the runner resolved
  the mismatch; the real seed-1 passive/stock/strict replay and saved-row
  recomputation then passed (39 initial R, 30 guard ACKs, nine recovery
  starts, eight recovery ACKs). This is software QC, not paper evidence.
- After the 43000 incident, tightened real-manifest validation so it
  rejects before reading a file unless the caller explicitly asks for
  `replay=True`; the runner passes that only after frozen contract, exact
  mode/seed and predecessor checks. Changed planned smoke to 43200 and
  blocked it from synthetic mode. No 43200/43001--43020/43101--43120
  real run has occurred. Focused ACK-quality tests passed 79, full suite
  789 passed/one skipped, compilation and `git diff --check` passed.
  A final static-only independent review is pending; status stays draft.
- Resumed the persistent core-rewrite goal after a clarification-only turn,
  classified as no implementation or experiment progress. Re-ran planning
  session catch-up (no unsynced context) and inspected the dirty v2 worktree.
  The latest known gate remains draft; 43200 and both 43xxx research cohorts
  are unopened. A newly added `summary.by_seed` assertion may invalidate a
  forged-smoke test fixture before its intended replay check, so the next
  step is a stub-only focused reproduction and root-cause repair. No paper,
  protocol policy, version, remote, or research seed action was taken here.
- Reproduced the forged-smoke fixture failure with `python3 -m pytest`: the
  fixture renamed its saved run to seed 43200 but kept a summary keyed by
  seed 73, so `write_report` correctly rejected it before independent
  replay. Recomputed the fixture summary from its altered runs; the intended
  stub-only replay rejection test now passes. A bare `pytest` invocation
  first failed during collection because it omitted the project root from
  `sys.path`; `python3 -m pytest` is the working entry point. No real seed
  was run and no production gate was weakened.
- After the fixture repair, the focused passive ACK-quality suite passed
  79/79, Python compilation and `git diff --check` passed, and the full
  `python3 -m pytest -q` suite passed 789 with one skip (42.81 s). A fresh
  independent static pre-freeze review is underway. The contract remains
  draft; no 43200, exploration, or validation run has been started.
- Independent static audit returned NO-GO for a smoke-only freeze: the
  `Status: frozen` gate plus a valid smoke manifest would also allow the
  runner to open 43001--43020, contrary to the contract's smoke-only
  wording. Next action is a test-first, separate immutable authorization
  artifact for each later stage, checked before any real seed by both
  `run_report` and explicit-replay `validate_manifest`. Stage artifacts
  must remain outside the frozen source hashes so later approval does not
  invalidate the 43200 smoke manifest. No stage was opened.
- Added two red/green stage-authorization slices without research seeds:
  missing exploration authorization now fails before even replaying smoke,
  and a valid exact-mode/seed/source/case/deadline/predecessor JSON permit
  is hash-recorded in the exploration report. Work remains to enforce the
  permit in saved-manifest validation, validation-mode recursion, CLI and
  adversarial tests before freezing the contract.
- Completed the stage-authorization gate across `run_report`, recursive
  `validate_manifest`, saved report/manifest, and CLI. Separate immutable
  explore/validation permits bind exact stage, cohort, source/case hashes,
  deadline and actual predecessor manifest hashes; validation preflights
  the saved exploration permit byte hash before any predecessor replay.
  Added missing, mismatched, changed-byte and CLI stub tests, and documented
  the contract. The focused suite passed 91, compilation and diff checks
  passed, and the full suite passed 801 with one skip (44.92 s). No real
  research seed or paper/protocol change occurred. An independent re-audit
  is pending; contract status remains draft.
- Independent static re-audit gave GO for one 43200 smoke and no P0/P1
  stage-gate concern. Made the unfrozen-contract test use its own draft
  fixture, changed the contract status to frozen-for-smoke-only, and reran
  the full suite on those exact sources: 801 passed, one skipped in 46.15 s.
  Frozen eleven input hashes plus the case hash are recorded in
  `task_plan.md`. Exploration/validation permits have not been created,
  and no real 43xxx seed has yet run.
- Ran the frozen 43200 mechanical smoke once at a new non-overwriting
  prefix. Saved manifest, sidecar, summary and full-run JSONL; the manifest
  SHA-256 is `97513ee5378446836a05e82b4e2ef3618fb1684f55bdc72ddcea3ec0522fefd1`.
  The reporter gave 38/38 eligible initial R decisions with 32 guard ACKs
  and six misses, plus six later recovery attempts/five recovery ACKs.
  These are smoke bookkeeping only. `rg --files results` masked ignored
  artifacts; `rg --files --no-ignore results` verified exactly these four
  43200 files and no 43001--43020/43101--43120 output. The runner's
  exclusive writes prevent overwriting an existing exact prefix. An
  independent saved-artifact and explicit-replay audit is underway;
  exploration and validation remain unauthorized.
- Independent 43200 saved-artifact and official explicit-replay audit passed:
  all eleven frozen inputs, case, manifest and artifact hashes match; the
  saved 47-flow/625-TX/219-action trace and 38-row ACK cohort reconcile,
  including exact stock/passive/RNG parity. Created only the separate
  exploration authorization JSON for exact seeds 43001--43020, tied to
  smoke manifest SHA-256 `97513ee5378446836a05e82b4e2ef3618fb1684f55bdc72ddcea3ec0522fefd1`.
  No exploration/validation seed has run at this point and no validation
  permit exists.
- Resumed after an interrupted CLI-stage-gate edit. The CLI flags, contract
  schema and adversarial permit tests were present on disk; planning
  catch-up reported no unsynced context and no 43xxx results existed.
  The first focused gate run exposed a genuine missing pre-replay check:
  validation accepted a semantically identical but byte-changed exploration
  permit until it had already begun smoke replay. The saved exploration
  manifest-hash check is now applied before any predecessor replay. That
  red test passed on rerun; all 85 related ACK-quality tests, compilation
  and `git diff --check` passed. The full suite passed 801 tests with one
  skip in 44.70 s. An independent read-only post-repair gate audit is
  pending. The contract remains draft and no 43200/exploration/validation
  seed has been run.

## 2026-10-05 Core-Algorithm Continuation

- The preceding clarification turn was read-only and did not advance the
  active core-rewrite goal. Revalidated the current dirty v2 worktree and
  ran the planning session-catchup helper (no unsynced output).
- Corrected the stale planning tail: 43200 smoke and 43001--43020
  exploration are actually saved and audited. The official q/q_clean fit
  remains numerical NO-GO, and 43101--43120 has no authorization or run.
- Before any code change, archived the exact eleven frozen inputs to
  `docs/research/meshecho_source_ack_quality_frozen_20261004.tar.gz`
  (SHA-256 `81383931bf305758b5699a8c789868bbb84ee32ea03b96ec4427b6b7c5669c60`).
  All eleven current file hashes match the saved exploration manifest.
  The archive preserves the old runner/model/contract for audit and replay.
- Next: synthetic public-API red regression for the near-stationary logistic
  fit, a stable mathematical fix, independent review, then a new prospective
  freeze. No old research seed is to be reclassified as confirmation.
- Added a four-row synthetic M0 public-API regression. It failed on the
  frozen solver with `ridge-logistic Newton solver did not converge`; this
  reproduces the near-stationary loss-cancellation defect without a research
  seed. A direct, compensated candidate-minus-current objective calculation
  now drives the unchanged mathematical Armijo rule and rejects no-op steps.
  The new regression passes; the three ACK-quality test modules pass 92/92.
  An independent post-edit numerical review is pending. No 43xxx seed was
  rerun or validation authorization created.
- Independent post-edit review found no P0/P1 numerical issue and reproduced
  the stable loss difference against high-precision synthetic arithmetic.
  Full regression passed: 802 tests, one skipped, in 42.95 s; targeted Python
  compilation and `git diff --check` also passed.
- Loaded only the already-saved 43001--43020 cohort for software diagnosis,
  without rerunning any simulation. Two initial extraction attempts failed
  because `cohort` is an object and its rows omit `seed`; corrected the
  structured `jq` extraction to add the enclosing run's seed. Both q and
  q_clean now complete all 20 LOSO folds. This does **not** change the
  frozen NO-GO, and no validation authorization exists.
- Old-row exploratory diagnostics: q LOSO mean Brier gain over M0 is
  0.002972 and over the selected threshold T is 0.004080; q_clean gives
  0.003024/0.004133. Primary q-only rank AUC is 0.658058. These are
  inspected development diagnostics, below the predeclared 0.005 validation
  mean-gain threshold, not a pass or an ICC claim. Reassess whether a new
  signal cohort is worth running before selecting a core policy.
- Used deep-research in targeted fact-check mode for ACK/feedback primitives.
  Checked official RFC 4728 text and independently matched three paper DOI
  records against Semantic Scholar and Crossref; saved a scoped verification
  note with limits. It does not certify MeshEcho novelty. Screening a
  source-adjacent/local ACK-protection hypothesis and rejecting an
  unconditional status-query branch remain in progress.
- Read-only independent screens now reject unconditional STATUS query as a
  distinctive full-core candidate and limit source-adjacent tail-only ACK
  reinforcement to five multihop relay opportunities among 20 historical
  source-final failures. No protocol code or research seed was changed.
  A separate ACK-borne backup *forward-route* exposure check is underway;
  this is not the previously rejected alternate reverse-ACK branch.
- A read-only `jq` probe of the audited 420xx `epochs.jsonl` mistakenly
  indexed each JSON object as an array and printed per-line errors. No file
  or simulation changed. The actual line shape is `{seed, item}`; `.item`
  holds `ack_attempt`, `alternatives`, `original_path`, and deadline fields.
  Subsequent structured inspection must use that shape rather than
  repeating the failing query.
- Continued the persistent core-rewrite goal after clarifying that algorithm
  decisions must be redesigned while the simulator can be reused. The prior
  turn produced a read-only 42xxx backup-route feasibility audit, so it was
  research progress, not a completed algorithm or experiment. Re-read the
  current dirty v2 worktree and planning files; no existing edits were
  reverted. The planning skill's catch-up helper succeeded with `python3`
  after `python` was unavailable and reported no unsynced context.
- Recorded the provisional matched-generation backup-path exposure and the
  fixed-F rescue ceiling in the planning files. Started independent read-only
  novelty and implementation audits. No new seed, protocol behavior, paper,
  PDF, version or remote submission has been changed in this continuation.
- Independent novelty audit ruled out a bare backup-route-failover claim:
  DSR/AOMDV are close predecessors. Wrote the unfrozen DBR contract with
  DSR-like, same-route and byte-padded fixed-F controls; it reserves but does
  not authorize 44200/44001--44020/44101--44140. The first TDD test failed
  on absent `alternate_path`, then passed after charging 1+2*N bytes and
  propagating the field through Packet copy/forward operations.
- The DBR feedback test first failed on unknown protocol and then passed:
  the destination collects two physically decoded FLOOD paths for 2 s,
  emits one ACK on the first path with the first-hop-diverse backup, and the
  source ACK arrives. The source-recovery test first found no backup DATA,
  then passed after implementing a no-D F/R choice, generation-bound backup
  state, marker-3 backup DATA, and ACK-only route promotion. A further red/
  green test added a marker-2 F after an unACKed backup within the original
  30-s deadline.
- A busy-source red test found that candidate recovery could reserve a TX
  start in the future before later ACK cancellation. Both backup and F
  pending-send predicates now require actual start equal to the current
  request time; the test passed. One full regression at this point passed
  807/807 tests with one skip in 44.45 s; compilation and diff check passed.
- A later forged-adjacent-hop ACK test failed as expected (wrong radio sender
  completed a flow). DBR now validates the actual sender at each ACK hop;
  focused packet/DBR suite passed 11 tests. No fresh research seed, PDF,
  version, GitHub or EDAS action occurred. Full regression must be rerun
  after this latest receive-hook edit.
- Added the same-path, first-alternate, padded fixed-F and plain fixed-F
  recovery comparison modes with red/green public-behavior tests. The
  first-alternate control demonstrably uses an old backup that the selective
  DBR rule rejects; padded versus plain fixed-F differs by seven ACK bytes
  in the tested three-node example, while the selected recovery action is
  identical. No reserved DBR experiment seed was run.
- On continuation, reran `python3 -m pytest -q`: 812 passed, one skipped
  in 44.44 s. Python compilation of the simulator and DBR tests, plus
  `git diff --check`, passed. The DBR draft
  remains unfrozen; no new paper, PDF, VERSION, GitHub or EDAS change was
  made. The immediate question is whether the core must be rewritten: yes,
  the old score/threshold policy is not a defensible new ICC algorithm;
  only the simulation infrastructure and old controls should be reused.

## 2026-10-05 DBR Correctness Continuation

- The planning catch-up helper returned no unsynced context. Read the
  planning files and current dirty worktree; did not revert user edits.
  Used the planning, TDD, and academic-paper skills. The paper skill keeps
  new manuscript claims behind verified citations and new results; this
  continuation did not alter the paper.
- Added and ran three failing public DBR tests one at a time, then made each
  green: stale backup fallback emits one `dbr_guard` reason; a primary route
  expiring between initial R and the guard cannot authorize backup DATA;
  a malformed FLOOD with the wrong source cannot deliver another flow or
  generate an ACK. The original failures were respectively a missing event,
  an actual marker-3 send after TTL, and a false `delivered_at` timestamp.
- Independent read-only code and runner audits identified further P1/P2
  issues: canceled recovery requests, late initial R ACK interleaving,
  incomplete ACK-byte deadline estimate, capacity-event gaps and missing
  DBR marker-3/strict-replay reporting. No 44xxx seed, PDF, VERSION, GitHub
  or EDAS action occurred. Next: test/fix ACK interleaving and queued
  recovery behavior, then complete the dedicated provenance runner.
- Added red/green SF12 deadline-budget coverage: six-hop FLOOD admission
  initially underestimated a maximum-size backup ACK by 2.94912 s; the
  correct FLOOD estimator now includes that field. The first manual patch
  accidentally targeted the adjacent backup-DATA estimator; an immediate
  source inspection caught and corrected it before the focused suite ran.
- Added red/green nine-window capacity coverage. Nine destination deliveries
  still produce a single plain ACK for the overflow flow, and the ninth
  window now emits `dbr_feedback_capacity_overflow`. No DBR experiment seed
  or ICC manuscript/release action was taken.
- Full regression after the five DBR slices: 817 passed, one skipped in
  49.15 s. Python compilation of the simulator/DBR tests and
  `git diff --check` passed. A separate subtask is implementing only a
  fail-closed DBR runner/TX tuple-replay foundation; no real 44xxx run or
  stage permit is authorized by this verification.
- Added public red/green interleaving tests for a B TX request canceled
  between guard and actual start, an F request postponed by a busy source,
  and a source already busy at the guard. DBR now logs canceled requests,
  schedules only re-evaluation timers at the next radio-idle time, and
  admits F only after a fresh ACK/active-flow/deadline check. A follow-up
  late-R-ACK test passed without further implementation and proves the
  deferred F does not fire after flow confirmation.
- Added a red/green reordering test in which older flow 2's F ACK updates
  the route after flow 3's B has started, then flow 3's B ACK arrives. The
  previous code changed the route to the stale backup despite newer F
  generation; the new generation check preserves the F route while still
  ACKing flow 3. The DBR contract was updated with first-accepted-ACK,
  radio-idle recheck and full FLOOD ACK-byte accounting semantics. Focused
  DBR tests passed after each fix; broad regression remains to run.
- Tightened the successful B-route end-to-end test to require exactly one
  source-accepted marker-3 event; it first failed because DBR bypassed the
  DHR ACK logger, then passed after adding `dbr_source_ack_rx`. The current
  focused DBR plus packet-airtime suite is 24 passed; Python compilation and
  `git diff --check` passed. Independent post-fix audit is active. No
  population seed or paper/release/remote action occurred.
- Resumed after context compaction and re-read the plan, findings, progress,
  DBR draft and current dirty worktree; the planning catch-up helper reported
  no unsynced context. Independent DBR protocol and runner audits returned.
  Protocol normal-path review found no reproduced P0/P1 but identified two
  missing ordering tests and a short SF10 guard margin. Runner review found
  a stage-gate bypass and incomplete artifact/audit path. These are now
  recorded as NO-GO for reserved DBR simulation, not as performance results.
- Clarified the algorithm direction in response to the user: rewrite the
  source/feedback/recovery decision core, reuse the simulator and prior
  protocols as infrastructure/controls, and reject or redesign DBR if its
  fresh-backup rule cannot separate from first-alternate and fixed-F.
  No paper, PDF, VERSION, GitHub, EDAS or 44xxx-seed action was taken.
- Full repository regression passed 840 tests with one skipped in 43.77 s;
  `git diff --check` passed. The successful suite does not reopen reserved
  DBR seeds or change the runner NO-GO/novelty assessment.
- Updated `docs/research/icc_core_rewrite_revision_map.md` with a DBR-specific
  manuscript evidence gate while leaving the LaTeX/PDF and results unchanged.
  Read-only structured 42xxx joins found 105 strictly matched candidate
  backup exposures, 32 older than 120 s over 20 seeds, and 17 in the first
  ten; this raises concern about DBR/first-alternate divergence but cannot
  establish efficacy. The first `jq` attempt returned an empty set because
  epoch rows keep `seed` in the outer `{seed,item}` record; corrected the join
  to add the enclosing seed before calculating counts.
- The DBR protocol boundary subtask added end-to-end ordering/contention
  tests and removed a destination policy read of global flow registration.
  A red malformed-origin test led to accounting-only identity validation in
  `Simulator.mark_delivered`, while a destination may still send a physical
  ACK to an unauthenticated claim. Its focused suite passed 24/24. A full
  suite during the parallel runner's RED phase had one expected runner-test
  failure; rerun after the runner finishes. No reserved seed ran.
- Updated the unfrozen DBR contract to remove the impossible destination
  global-flow identity check, state the non-adversarial threat model, and
  define scheduled-flow PDR, seed-paired relative complete-network airtime,
  TX-energy and independent-unit accounting. A shared accounting follow-up
  tested wrong-origin then valid-origin DATA/FLOOD delivery callbacks.
- The runner subtask completed direct-capture stage validation, fresh
  output/manifest persistence, complete TX serialization and disk audit of
  flow denominators, ToA/bytes/airtime/TX energy, marker-3 source starts,
  cross-arm trace parity and strict replay digest. It ran only nonreserved
  fixture seed 73. The merged full suite passed 857 tests with one skipped
  in 43.60 s; compilation and `git diff --check` passed. Independent runner
  review remains open; no contract freeze, 44xxx simulation, paper/PDF,
  VERSION, GitHub or EDAS change occurred.
- The independent runner review now identifies a P1 generic-entry bypass for
  every reserved DBR seed. Reproduced the preexisting red regression:
  `run_one_sr(..., "meshecho-dbr", 44200)` reached the `generate_nodes`
  failure stub before authorization. A separate subtask is tightening
  archived manifest/row identity. No reserved seed was actually simulated;
  next is a guarded-entry red/green fix and full regression.
- Red/green guarded-entry fix completed: DBR, Meshtastic comparator and
  holdout-arm representative reserved seeds now fail before `generate_nodes`;
  the dedicated runner supplies a validated token/permit for an intentionally
  protected seed-73 fixture. `tests/test_dbr_experiment.py` passed 33/33,
  Python compilation and `git diff --check` passed. The current source files
  are untracked in this pre-existing worktree, so `git diff -- <file>` alone
  does not display their changes. Archived artifact identity work is still
  in progress; no 44xxx population run, manuscript/release or remote action.
- Independent read-only DBR locality review found no current channel/future-
  event oracle in routing decisions; source `Metrics.flows` remains a P2
  architectural coupling to replace with source-local state. Added a public
  rehashed-archive regression for a forged `dbr_backup_tx`; it is RED because
  the current audit accepts the nonexistent physical start. The concurrent
  archived manifest/row identity slice is in final verification.
- The archived identity subtask finished with 14 new tests passing, including
  canonical mode/seed/arm/case/deadline and row identity/horizon checks. Then
  added two red/green rehashed-archive tests: invented marker-3 backup and
  marker-2 F-recovery action events now fail unless an identical source TX
  exists. Added the new identity suite to frozen input hashes. The combined
  DBR tests passed 74/74; the whole repository passed 877 tests with one
  skip in 43.15 s, and compilation/whitespace checks passed. A later exact-
  replay-manifest red/green test also passes; rerun broad regression after it.
  An independent post-fix audit is pending. No DBR population seed, PDF,
  VERSION, GitHub or EDAS action occurred.
- Final post-flag regression: 878 passed, one skipped in 43.14 s; Python
  compilation and `git diff --check` passed. Independent post-fix runner
  audit found no new P0/P1 and confirmed no DBR 44xxx artifacts/processes,
  but only a future frozen mechanical smoke is technically ready. Independent
  scientific review recommends NO-GO for current DBR development/holdout
  because its selective branch is largely just a 120-s cutoff relative to
  first-alternate, with limited old-trace divergence. Kept draft unfrozen and
  all reserved 44xxx seeds unopened. Next: redesign core decision hypothesis
  before any prospective population run or ICC manuscript/result rewrite.
- The scientific audit supplied two bounded alternatives for a successor
  exposure screen: source-local accepted-ACK quality and an on-wire charged
  first-hop receipt. Neither is ready to code as the paper core: inspected
  q gains are below the prior signal target and observed overheard progress
  is sparse/close to DSR and link ARQ. Recorded exact screening boundary in
  task_plan/findings. The academic-paper evidence rules therefore keep the
  old ICC manuscript untouched pending a new verified algorithm and matched
  simulation, as the user requested a major real revision rather than a
  cosmetic rewrite. No 44xxx seed or remote submission/publish action.
- 2026-10-05 continuation: classified the preceding goal turn as no progress;
  it clarified the rewrite boundary but changed no authoritative state. Re-read
  the project plan, findings, DBR draft, simulator policy and current ICC claims.
  Planning recovery script ran under `python3`; its first `python` invocation
  failed because this host has no `python` command. Current DBR remains NO-GO,
  the ICC source/PDF and reserved 44xxx seeds remain untouched. Next action is
  a passive, device-observable signal/physical-cost screen for a genuinely
  distinct source/feedback/recovery mechanism before implementation.
- Added a pre-implementation first-hop receipt screen design and logged its
  measured prior exposure (86 R starts over three old seeds), nominal
  17-byte/0.051456-s receipt cost, same-wire comparator requirement and
  45000/45001--45020 prospective stage boundary. Corrected the second
  necessary gate before any seed opening: a residual deadline-unACKed
  opportunity is required, while early-only nominal admission remains a
  separate descriptive count. Independent design review and a test-first
  passive diagnostic implementation are underway. No new protocol behavior,
  population simulation, paper/release or remote action was performed.
- Incorporated independent design findings before any 45xxx seed use:
  source-radio busy and dropped active state cannot count as early-F
  opportunities; direct-route and destination-delivery ceilings are explicit;
  late-ending R TXs are censored; and receipt-free controls are mandatory.
  Updated the ICC revision map to mark DBR scientific NO-GO despite its
  mechanically audited runner and to retain the old manuscript until a
  successor has verified new results. `git diff --check` passed after the
  documentation edits. A guessed 43xxx `.runs.csv` lookup failed; the
  archived format is `.runs.jsonl`, with no data modification.
- Independent read-only review rejected destination-local quiet-window ACK
  timing as a complete new core: its old-trace timer branches do not expose
  new source-visible information, and the residual fixed-2-s misses are
  primarily physical reverse-ACK reception. Logged the NO-GO in the plan
  and findings; no quiet-window protocol or seed was run. The first-hop
  receipt diagnostic remains in test-first implementation on fixture seed
  73 only, with no 45xxx run.
- Completed the passive first-hop receipt diagnostic and protected the shared
  SR experiment entry from bypassing reserved 45xxx stage authorization.
  Audit-driven regressions now reject a missing complete R decision for an
  actual physical R start and rehashed false passive metadata. The focused
  suite passed 19 tests; the full repository suite passed 903 with one
  skipped in 109.89 s. Python compilation and `git diff --check` passed.
  Only fixture seed 73 was used. No 45xxx simulation, candidate selection,
  manuscript/PDF, VERSION, GitHub, or EDAS action occurred.

## 2026-10-05 Goal Continuation: Receipt Pre-Smoke Audit

- Classified the preceding goal turn as progress: it added the guarded
  passive diagnostic, reverse R-start join and metadata checks, with 903
  passing tests. The actual core rewrite and ICC revision remain open.
- Recovered the current plan/findings/progress and inspected the diagnostic
  source, stage guards, stock-parity capture, archive verifier, and public
  fixture tests. The tool observes post-`try_receive` outcomes and requires
  equality of stock and observed metrics, flows, actions, complete TXs and
  both RNG states; this remains a necessary screen, not an algorithm.
- Started a fresh focused test run and independent read-only post-fix audit.
  No reserved 45xxx seed has been opened in this continuation.
- Fresh focused receipt/seed-guard verification passed 25 tests. An
  independent read-only post-fix audit returned NO-GO for 45000 because
  the importable token bypasses stage order and smoke has no prior frozen
  input permit. A bounded TDD implementation is now repairing that stage
  boundary; no reserved seed has been run.
- Separate mechanism review found no qualified full-core successor, even
  conditional on a positive passive receipt screen. This changes the next
  interpretation: the screen may qualify a component for a later distinct
  joint-state hypothesis, but cannot by itself trigger an ICC rewrite.
- Read-only paper baseline audit identified directed next-hop learning,
  DATA-first route discovery/retry, reverse ACK/report routing, and relay
  role mix as required sensitivity checks for any new MeshEcho comparison.
  This did not change the present manuscript or run a new seed.
- Stage permit red/green implementation completed. The new gate binds
  protocol, exact seed cohort, case, 30-s deadline, source hashes and a
  strictly replayed smoke predecessor for exploration. The CLI archives
  permit bytes and checks their hash on replay. Focused receipt tests:
  36 passed. Full suite: 914 passed, one skipped in 139.45 s. Compilation
  and whitespace checks passed. No 45xxx seed or new ICC manuscript result.
- Froze the first eight-input smoke permit and had its hashes independently
  checked. The formal CLI attempt failed before topology or artifact writing
  because direct `__main__` execution re-imported the diagnostic module
  during a temporary simulator-class patch. A red subprocess test reproduced
  the exception; routing the script entry through canonical module `main()`
  made the same test green. The old permit is invalid after source edits and
  is retained only as audit history. No 45xxx simulation has occurred.

## 2026-10-05 Goal Continuation: Canonical Entry Verification

- Classified the preceding question-answer turn as no authoritative research
  progress: it clarified that the ICC goal needs a new core decision rule, but
  did not change algorithm, evidence, or manuscript state.
- Recovered the existing plan/findings/progress and the pending focused-test
  session. Its final result was 37 passed. The source and manuscript still
  have no selected new core or ICC rewrite.
- Started the full repository regression for the direct-script entry fix;
  Python compilation and `git diff --check` passed. Independent read-only
  entry/stage audit is in progress. The historical 45000 permit remains
  invalid and no reserved receipt seed has run in this continuation.
- Full regression passed 915 tests with one skipped in 140.54 s. The new v2
  permit was frozen and independently approved for only seed 45000. The
  formal CLI then completed the one mechanical smoke and wrote complete
  artifacts. Independent archive/strict-replay audit passed, including
  stock parity and 34 initial-R row/decode reconciliation. The single seed
  has no residual gate-2 early-F opportunity; this is not a population
  verdict. A new exact-scope 45001--45020 exploratory permit was created,
  bound to the smoke manifest and successfully stage-validated. No new
  protocol behavior, manuscript/PDF, VERSION, GitHub, or EDAS action yet.
- The first 45001--45020 exploratory CLI attempt failed during seed 45001
  stock capture: predecessor strict replay nested inside the outer simulator
  patch, causing the outer capture to count both predecessor and 45001
  simulator instances. Seed 45001 stock simulation did complete once, but
  the command exited before result archiving and did not start 45002--45020.
  No exploration result files exist. A nonreserved seed-73 regression failed
  with the same assertion, then passed after binding the genuine stock
  simulator class at canonical diagnostic-module import. Focused tests
  passed 38/38; independent code review found no P0/P1. Full regression is
  running; old smoke/explore permits are invalid after the source/test edit.
- Full post-fix repository regression passed 916 tests with one skipped in
  151.66 s; compilation and `git diff --check` passed. Eight inputs and the
  case were re-frozen, a distinct v3 45000 permit was stage-validated and
  independently approved, then the formal smoke CLI completed. Its manifest
  sidecar verified. Comparing v2/v3 manifests found identical summary
  values and identical digests for runs, initial-R rows, flows, actions,
  complete transmissions, and first-hop decodes; only permit/source-summary
  metadata changed. Independent v3 archive strict-replay audit is pending.
- Independent v3 smoke audit subsequently passed, including sidecar,
  artifacts, archived permit, stock parity and strict replay. A distinct
  v2 exploration permit bound to v3 smoke was frozen and independently
  approved for exactly seeds 45001--45020. The formal CLI exploration is
  currently running under unified exec session `96934` (observed OS PID
  `66819`), with output prefix
  `results/meshecho_first_hop_receipt_explore_45001_45020_v2_20261005`.
  It had not produced a final report at this checkpoint; do not restart on
  an observation timeout. Poll that exact live session/process to terminal.
  The aborted prior 45001 stock attempt remains disclosed separately.
- Unified exec session `96934` completed successfully with the formal
  45001--45020 exploration archive. CLI strict replay and a separate
  no-rerun artifact/row audit passed. The frozen necessary gate is NO-GO:
  gate 4 optimistic ACK ceiling 0.0128713 < 0.02, even though exposure,
  residual count and receipt-cost gates pass. All ten residual candidates
  were already destination-delivered; destination gain ceiling and early-
  only deadline opportunities were zero. Wrote the detailed result note and
  updated task_plan/findings. No receipt behavior algorithm was implemented,
  and ICC source/PDF, VERSION, GitHub and EDAS remain unchanged. Next work
  must identify a different device-observable reverse-ACK core and test it
  prospectively against simple same-cost controls; the full user goal remains
  open.

## 2026-10-05 Goal Continuation: Reverse-ACK Opportunity Audit

- The preceding question-answer turn made no new authoritative research
  progress: it clarified that the SR source/feedback/recovery core needs a
  substantive rewrite, while simulator infrastructure can be reused.
- Recovered the current plan, findings, and progress. The planning skill's
  catch-up helper first failed because this shell has no `python` command;
  rerunning it with `python3` completed without an unsynced-context report.
- Current worktree is already dirty with ongoing research artifacts; no
  unrelated file was reverted. The ICC manuscript remains the old calibrated
  variant. The successful 45001--45020 receipt archive has complete flow,
  action, and transmission JSONL files available for a no-rerun reverse-ACK
  feasibility audit. No new protocol, seed, manuscript result, version,
  GitHub update, or EDAS action has been authorized by this inspection.

## 2026-10-05 Goal Continuation: Forward Backup Core Screen

- The prior question-answer turn produced an independent 42xxx join check
  and identified a P1 benefit-gate error, but no new algorithm or paper.
  `session-catchup.py` run with `python3` reported no unsynced session state.
- Corrected `meshecho_destination_certified_backup_screen.md` before any
  46xxx run: only stock deadline-unACKed flows contribute to potential ACK
  gain; stock-ACKed F rescues form a separate, charged airtime-substitution
  opportunity. Added the IOMC prior-art boundary, minimum explicit field
  bytes, and unconditional/IOMC-like controls. These are pre-implementation
  rules, not a result. Two failed patch contexts and two guessed missing
  DBR paths were corrected without changing data.
- A passive observer implementation is in progress in separate new files.
  No 46xxx seed, new protocol behavior, ICC PDF, VERSION, GitHub or EDAS
  action has occurred in this continuation.
- A structured, no-rerun 42xxx stock join corrected an initial jq-context
  mistake (133 vs 131) and found eight deadline-unACKed among 131 direct
  initial R flows. ACKed direct-R/F-recovery flows used 116.945152 s in
  marked F TX out of 999.575552 s complete network TX. This is a broad
  historical gross opportunity, not achievable saving. The candidate gate
  was narrowed to cost-first, source-ACK-noninferior before opening 46xxx.
- A prior-art/contract review verified IOMC's ACK-gated LoRa relay and
  corrected the future control design: the fully identical informed arm is
  a parity check, while local/overheard relay choice and unconditional
  forwarding are real ablations. The draft now requires exact backup ACK
  identity, epoch, physical-start, path and deadline validation. No
  positive manuscript claim follows from this design work.
- The observer review found stock fixed-2-s ACKs are packet-built on first
  destination decode, not at the window close. Candidate backup fields are
  therefore prospective only, even if later F paths were physically seen.
  The design note now states this explicitly and records the SF7 discrete
  ToA change for minimum 2-byte F ACK and 6-byte nominated R DATA fields.
- Independent verification of the new passive observer ran
  `python3 -m pytest -q tests/test_destination_certified_backup.py`
  (10 passed in 6.47 s), `python3 -m py_compile` for its tool, and
  `git diff --check` (both passed). The source retains stock parity and
  a >=35000 seed guard; no authorized 46xxx gate runner or new protocol
  exists yet. The new files are untracked in the pre-existing dirty worktree.

## 2026-10-05 Goal Continuation: Backup Timing Gate

- The preceding turn only clarified that the protocol core, not the
  simulator infrastructure, needs rewriting; it produced no new algorithm
  or experimental evidence. Session catch-up found no unsynced context.
- Rechecked fixed-F DHR code: recovery is triggered at initial R physical
  start + 15 s, while the application deadline is flow creation + 30 s.
  Updated the unopened 46xxx passive design to require nominal candidate
  reverse ACK before the F guard to credit complete F-recovery airtime.
  Froze 2 s as primary relay wait and 0.5 s as sensitivity; this is still an
  optimistic opportunity screen, not a causal result.
- Observer cost/deadline calculations and exact-scope staged runner are
  being implemented in separate files by separate agents. No 46xxx seed,
  new protocol behavior, ICC source/PDF, VERSION, GitHub, or EDAS action.
- Test-first generic SR guard: eight red tests proved reserved 46xxx seeds
  reached topology generation without authorization. Added the reserved
  cohort and pre-topology stage check in `tools/run_sr_experiment.py`.
  An intermediate green run failed while the parallel runner module had not
  yet defined its token; reordering fail-closed checks resolved it. Nine
  focused tests now pass, including invalid-permit rejection. No 46xxx
  simulation was run by these tests.
- Neighbor regression after the guard: 208 tests passed across backup seed
  guard, existing receipt seed guard, and SR experiment tests. Python
  compilation and `git diff --check` passed. This covers the guard and
  adjacent behavior, not the still-in-progress observer/runner archive.
- Post-handoff observer audit found two opposing primary-cost-bound errors:
  unconditional success-ACK charge for every nominal relay start and an
  uncharged mandatory backup marker on relay DATA/ACK. Corrected the
  still-unopened 46xxx design note before any permit; observer agent is
  writing tests and repairs. This is not a performance result.
- Runner interim audit found a signature mismatch in its cohort-wrapper and
  the prior nested-capture hazard during smoke predecessor strict replay.
  Runner agent is fixing both with tests before source freeze. No new seed
  or artifact was opened by this inspection.

## 2026-10-05 Goal Continuation: Backup Screen Pre-Freeze

- Classified the preceding explanation-only goal turn as no new algorithm,
  experiment, or paper progress. Recovered the checkpoint and project planning
  files; session catch-up found no unsynced context.
- The passive observer and staged runner are now present. A separate read-only
  audit found no P0/P1 issue in the numeric gate, charged airtime, reserved-seed
  stage protection, or nested strict replay. The resumed adjacent test suite
  passed 241 tests. No permit has been created and no 46xxx seed has run.
- Next: full regression; freeze/independently verify the ten source inputs;
  authorize only the 46000 mechanical smoke; inspect its complete archive
  before considering the separate 46001--46020 passive exploration.
- Full repository regression passed 958 tests with one skip in 160.79 s;
  Python compilation and whitespace checks passed. Independent source audit
  matched all ten SHA-256 values, the recurring-fading case hash, exact
  protocol/deadline, and confirmed no pre-existing 46xxx permit/output.
- Froze the ten hashes in `task_plan.md` and created a smoke-only JSON permit
  for exactly seed 46000. Its stage validation and formal run are pending;
  no reserved seed has been opened by these planning edits.
- The smoke permit SHA-256 is
  `6dcd78725d1b183399d684a9f6c9f370917ed97511a3c09808c1701839273796`.
  The local pre-topology validator passed, and a separate read-only auditor
  matched its ten hashes and confirmed the selected output prefix is empty.
  Formal 46000 capture is now authorized once; exploration is still closed.
- The formal direct CLI rejected the smoke authorization inside
  `run_one_sr` before topology generation. The runner's `__main__` token
  differed from the canonical imported module token. No result artifact was
  written. Added a subprocess regression that must reach a patched topology
  guard through the exact direct-script entry; it is pending a red run.
- The subprocess regression failed red with the reserved-seed token rejection
  and passed green after `__main__` forwarded into the canonical imported
  runner. Adjacent tests passed 242/242; full regression passed 959 with one
  skipped in 160.42 s. Python compilation and `git diff --check` passed.
  Separate read-only review confirmed no artifact from the failed first
  attempt and no remaining direct-entry token split.
- Re-froze the ten runner inputs: only the runner and its test changed from
  the v1 freeze. Created a distinct v2 46000 smoke permit and empty planned
  v2 prefix. The first permit remains an invalid historical artifact; no
  reserved seed has actually simulated yet.
- V2 smoke permit pre-run SHA-256 is
  `abaeed71ddf0619fb3f6451df12c61be234f5716093276fee16700faf940385a`.
  Local and independent read-only stage validation both passed; the separate
  audit confirmed all twelve v2 output paths absent. GO for exactly one
  v2 mechanical smoke; 46001--46020 remain closed.
- Formal direct CLI completed the 46000 v2 passive smoke once and wrote a
  twelve-file archive. Manifest SHA-256 is
  `2481924958228b44686f1e5c2571175cdb94c15137a8748a8a04fdabe5b24b31`.
  The one-seed summary records 40 scheduled flows, four nominations, three
  exposed failed primaries, zero source-ACK headroom, and 0.1117769
  optimistic cost-substitution fraction. This is no treatment estimate;
  independent artifact and strict-replay verification is underway.
- Independent smoke audit passed official strict replay, all source/artifact
  hashes, archived permit, stock parity, four row/flow/F-epoch/R-TX joins,
  and an independent 6.462976 - 0.637184 = 5.825792 s airtime calculation.
  Smoke gate fields stay null. Created a separate exact 46001--46020
  exploration permit bound to the audited v2 smoke SHA-256; its stage
  validation and formal run remain pending.
- The exploration permit SHA-256 is
  `a4c046bd8bec1f7a6753ce539ff3682138397eb4723b2c92667655411d266ad9`.
  Local `_validate_stage('explore')` passed, strictly replaying the frozen
  smoke; the selected fresh output prefix is empty. Independent pre-run
  permit audit is pending; no 46001--46020 simulation has started.
- Independent pre-run audit returned GO for exactly the frozen 46001--46020
  passive cohort. The formal direct CLI is running under unified exec
  session `76573`, observed OS PID `95929`, with output prefix
  `results/meshecho_destination_backup_explore_46001_46020_20261005`.
  At this checkpoint it has not returned or written a final report. Poll
  the same live session/process to terminal; do not restart it on a wait
  timeout. No protocol behavior, paper/PDF, VERSION, GitHub or EDAS action.
- Unified exec session `76573` completed successfully; the one authorized
  46001--46020 passive CLI wrote a full twelve-file archive. Manifest SHA-256
  is `c51e55cbac2c8a5ae00de23001f008b3402360c3357430ff212d0f213ed9a385`.
  Local no-rerun `validate_manifest` passed. Saved primary screen has 872
  flows, 130 nominations, 36 physically exposed failed primaries across 17
  seeds, 36 PRR/deadline proxy-feasible, and 0.0552837 equal-seed optimistic
  cost-substitution fraction; gate fields say true. Independent no-rerun
  row/cost audit and protocol-contract review are in progress. None of
  these values is a measured treatment effect or ICC manuscript result.
- Independent no-rerun cohort audit passed all hashes, 130 row joins,
  13,338 TX/630-s accounting, and the prespecified exposure/cost arithmetic.
  The candidate is GO-to-prototype only: 5.528% optimistic equal-seed cost
  ceiling is just 0.528 points over the 5% gate; 6/872 is the source-ACK
  headroom proxy. Created a dedicated result note preserving provenance,
  limitations and next causal controls. New protocol implementation and ICC
  revision remain open.
- Before changing any frozen simulator input, archived the ten exact 46xxx
  source files and two effective permits to
  `docs/research/meshecho_destination_backup_frozen_20261005.tar.gz`
  (SHA-256 `a76b3b66f25ffbc54afed822a1eb393c2938a9942e6cbee27039fff2f90524a1`).
  The apparent member list hid macOS AppleDouble and PAX entries: raw tar
  inspection found 36 members, so this first archive is invalid as a clean
  snapshot. Preserved it for provenance, then created
  `docs/research/meshecho_destination_backup_frozen_v2_20261005.tar.gz`
  with `COPYFILE_DISABLE=1` and ustar format. Independent raw-member audit
  verified exactly twelve regular files, all ten source hashes and both
  permits against the frozen manifests. V2 SHA-256:
  `143245144414d66c547ca9e285c475be1e5ef16d6d39ac31460bb76f193568cd`.
- Drafted a separate DCB prototype contract with charged on-wire fields,
  source/relay/destination local state, actual-start ACK cancellation,
  a strict backup ACK echo/path/deadline rule, and matched controls. No
  behavior code or fresh protocol simulation has run yet.

## 2026-10-05 Goal Continuation: DCB Contract Audit

- Confirmed the current ICC paper still reports no max-min PRR score advantage
  over a matched PRR-product control; an algorithm-core rewrite remains the
  goal, while the tested simulator remains reusable infrastructure.
- Independent read-only DCB review identified pre-implementation contract
  gaps in physical-start activation, overflow ACK behavior, intentional
  backup field transformation, remote-TX observability, matched control
  definition, and quantitative causal gates.
- Revised the DCB contract to distinguish immutable enqueue nomination from
  actual-start activation, define immediate no-nominee ACK on window
  overflow, specify extension propagation/removal and stale-generation ACK
  handling, and supersede the impossible remote-TX source check. No DCB
  behavior has been implemented or simulated yet. The IOMC-like selector
  and quantitative gates are still being independently designed.
- TDD packet-wire slices are green: optional 16-bit relay and 32-bit epoch
  extensions charge 3/5/7 bytes including flags and survive all four Packet
  path/TTL transformations. Eight packet-airtime tests passed.
- TDD destination/source slices are green: `meshecho-dcb` collects physically
  decoded FLOOD paths before constructing one charged ACK, then nominates a
  direct next R only from its actually accepted F ACK. The two new end-to-end
  tests passed with ten combined DCB/packet-airtime tests. Relay forwarding,
  backup ACK validation, causal simulation and paper revision are still open.
- Independent control review delivered a same-budget current-overhearing
  selector and quantitative development/holdout gates; those are now frozen
  in the candidate contract before fresh protocol seed runs.
- Implemented and tested local nominated-relay buffering, a 2-s timer,
  busy-radio precheck, current direct-ACK overhear cancellation, a marked
  two-hop backup DATA/reverse ACK, actual-start source nomination activation,
  strict source ACK matching, and no route commit from backup ACK.
- Added test-first no-forward and unconditional controls plus a current-
  overhearing selector with deterministic CRC32 contention slots and
  acceptance through the relay actually used. The selector ignores the
  carried historic nominee while retaining its bytes and source eligibility.
- Fixed three real red-test failures: off-path direct ACK overhear was
  filtered before relay suppression; malformed F path indices and repeated-
  endpoint marked backup paths produced invalid delivery/ACK; and duplicate
  current DATA caused multiple backup TXs. A test-only failure that counted
  relay ACK forwarding as backup DATA was corrected after TX-kind diagnosis.
- Current focused packet/DCB and adjacent SR/DHR/DBR regression: 69 passed
  before the latest malformed-packet/one-shot additions; rerun the expanded
  suite before any source freeze. No 47xxx/48xxx run or ICC edit.

## 2026-10-05 DCB Continuation Check

- Recovered the contract, checkpoint and planning files. The planning skill's
  catch-up script succeeded with `python3`; initial `python` invocation was
  unavailable on this macOS host.
- Focused DCB, packet-airtime, DHR and DBR tests passed 60/60, including the
  just-added same-time ACK/relay-timer test. Added and ran a 120-s expiry
  public-flow test; it passed 1/1. No reserved seed was opened.
- The candidate remains unproven, and the existing ICC manuscript was not
  changed.
- Added an ACK physical-sender rejection logging test (red), implemented the
  source-side reason event, then passed the test with its adjacent epoch
  rejection case (2/2). A natural late-ACK-after-deadline case passed 1/1.
- Adjacent DCB/runner suite reported 265 passed and one expected runner RED:
  `run_experiment` still raised its `NotImplementedError` in the new
  five-arm persistence test. The separate runner agent is completing it.
- Full repository regression excluding that actively edited runner test
  module passed 982 tests, one skipped, in 161.96 s. No 47xxx/48xxx seed,
  paper/PDF, version, GitHub or EDAS action occurred.
- A new marked backup-DATA identity test failed red because a mismatched
  request ID was counted as delivery; a one-condition destination validation
  fix made it pass. The runner agent completed its fail-closed five-arm
  capture and physical provenance audit with nonreserved fixtures only.
- Current full suite passed 1005 tests with one skip in 162.00 s. Python
  compilation and `git diff --check` passed. Independent pre-freeze review
  remains pending; no reserved DCB seed has run.
- Independent review found active recovery state allocated before a queued
  R DATA's physical start. Expanded the public activation test to reproduce
  this red, then deferred DCB initial-R state activation to actual start;
  the focused test turned green. A second red/green test prevented a timer
  from being scheduled in the past when physical start is after the app
  deadline.
- A no-seed subprocess test reproduced direct CLI dispatch to a separate
  `__main__` module; canonical entry dispatch fixed the token identity.
  Adjacent protocol/runner tests passed 264/264, Python compilation and
  `git diff --check` passed. A final full suite is running.
- The independent contract audit identifies remaining additional comparator,
  per-packet queue-wait and peak-state reporting gaps. Draft status is
  retained; no 47000, development, holdout, ICC, version or GitHub change.
- Final full regression after the audit-driven fixes: 1007 tests passed,
  one skipped in 162.48 s. This is implementation verification only, not
  DCB causal performance evidence.

## 2026-10-05 Goal Continuation: Evidence Completeness

- TDD observability: a nonreserved capture test first failed on absent TX
  request time, then passed after a DCB-local recorder and nearest-rank p95
  queue summary were added. A live-state peak test first failed on absent
  attributes, then passed after update-on-admission counters. A persistence
  test first failed on absent `state.jsonl`, then passed with hashed state
  artifacts and cap/sum audit. A forced future-start test and rehashed queue
  tamper test passed. Focused DCB/airtime tests: 55 passed.
- An independent review found the remaining provenance gap: archived state
  peaks cannot yet be reconstructed from open/close transitions, and queue
  request times need separate committed-request records. The full suite
  reported 1010 passed, one skipped, but it began before the last tests were
  added and will be rerun after final changes. No 47xxx/48xxx seed opened.
- A rehashed state-peak tamper test failed against the first range-only audit,
  then passed after live open/close events and replayed peak reconstruction.
  A separate `tx_requests.jsonl` now joins committed requests to contiguous
  physical TX IDs with matching sender/flow/kind and a request time within
  the run window. Its fixture test was red before the artifact existed. The
  previous queue-tamper assertion needed a message update because the
  stronger request/TX join rejects corruption earlier. Focused tests passed
  58/58. A red/green ACK provenance test now requires an accepted backup ACK
  event to equal the flow's first `acked_at` timestamp.
- The first multi-file documentation patch did not match the contract's
  wrapping and changed nothing. The exact-context retry applied the note.
- The independent re-audit found no remaining scoped P1/P2 and verified
  nonreserved stock/new-recorder TX, flow and RNG parity. The final
  post-observability full suite passed 1011 tests, one skipped, in 162.54 s;
  `py_compile` and `git diff --check` passed.
- A red test for the absent fixed-two-hop useful-DATA F arm turned green
  after introducing a default-preserving F-TTL hook and registering the
  two-hop delayed-ACK control. The original fixed-F initial/recovery TTL
  stayed at six in the public test. A second red/green test introduced the
  DCB-wire source-FR control and verified D becomes R on a controlled aged
  route while F/R decisions remain unchanged. Its F ACK and nominated R
  packet wire fields match stock DCB in a separate test.
- The staged runner now records nine arms: five component, one DCB-wire
  source control, and three contextual controls (two-hop F, SR-FR, LPR).
  Contextual/source rows are reported but excluded from the four-component
  pass gate. Nonreserved nine-arm artifact fixture and 68 adjacent tests
  passed; 47xxx/48xxx remain unopened. A first combined implementation patch
  failed because the simulator CLI choice list did not contain DCB names;
  the exact constructor-only retry succeeded without changing CLI choices.
- Read-only 46xxx archive count: 70 D/96 F/706 R decisions; 64 exported
  D-candidate flows had 61 deadline ACKs. This is descriptive selection,
  not a D-vs-F effect. It makes a naive no-D rewrite scientifically unsafe.
- The immediately previous question-answer turn made no authoritative-state
  change, so this continuation revalidated the worktree and resumed the full
  algorithm/evidence goal. The planning catch-up script reported no unsynced
  context. Current paper still admits no measured max-min advantage; DCB
  contract remains draft and reserved 47xxx/48xxx are closed.
- Independent read-only mapping found the absent fixed two-hop F and
  unmatched SR-FR/LPR budgets. This is recorded before any comparator or
  seed-run change. A separate read-only source-core design review is running.
- The previous goal turn is classified as progress: it changed protocol and
  runner behavior, added failing-to-passing tests, and established an
  independent NO-GO pre-freeze gate. No causal DCB cohort or ICC revision has
  occurred.
- Recovered the checkpoint and planning files with `python3` session catch-up
  (no unsynced state). Began DCB queue/state observability design and an
  independent read-only comparator mapping. All 47xxx/48xxx seeds remain
  closed while the contract is draft.

## 2026-10-05 Core-Algorithm Continuation

- The preceding answer-only turn was **no authoritative-state progress**:
  it correctly distinguished rewriting the source decision core from
  replacing the tested simulator, but changed no algorithm or evidence.
- Revalidated the dirty worktree and checkpoint with the planning skill's
  `session-catchup.py`; it reported no unsynced context. The DCB contract is
  still draft; no 47000/47001--47020/48001--48040 run is authorized.
- Independent inspection confirmed DCB still inherits SR's F/R/D initial
  choice and DHR's fixed recovery controller. The 5.528% 46xxx passive
  opportunity is not protocol treatment effect. A source-core redesign is
  required before claiming the user-requested algorithm rewrite.
- A P2 fairness defect was identified in the new two-hop useful-DATA F
  contextual control: recovery admission still estimates a six-hop flood
  even though its actual FLOOD TTL is two. A test-first correction and a
  separate read-only new-core design audit are in progress. Do not freeze
  the nine-arm matrix or revise ICC numerical claims until both are resolved.
- The two-hop bound correction passed one RED-to-GREEN public deadline-edge
  test, 19 focused tests, and a full `python3 -m pytest -q` run with 1017
  passed and one skipped in 161.92 s. `py_compile` and `git diff --check`
  passed. Flood2's nominal bound fell from 10.778272 s to 4.208224 s;
  no reserved seed was opened. The matrix remains draft for source/control
  design reasons, not for this comparator defect.
- Ran the predeclared, nonreserved 49101--49103 three-seed exploratory
  component pilot once with identical schedule hashes across DCB and
  fixed-2-s-ACK/fixed-F arms. Per seed, both arms had identical deadline
  ACK/delivery counts: 54/55, 28/29, and 44/45. Whole-network airtime was
  DCB/fixed-F 55.162112/67.399168 s, 36.506112/36.500992 s, and
  50.718208/50.615808 s. DCB backup starts were 2, 0, 0. This is sparse
  exploratory mechanism exposure, not a paired population effect, a frozen
  DCB gate, a source-core result, or ICC evidence; these seeds cannot later
  be called untouched validation.
- An independent read-only source-design audit rejected blanket F when a
  direct route lacks a fresh backup certificate: 45 archived candidate
  decisions are mostly already successful, and a descriptive F substitution
  suggests a substantial airtime penalty. Drafted a distinct ACK-proven
  route-promotion candidate contract and started a public end-to-end TDD
  slice. It remains a component hypothesis; no full new F/R/D controller,
  frozen cohort or paper update has been produced.

## 2026-10-05 - Source-Core Clarification

- Inspected the current SR/DCB/DHR source and ACK paths in the dirty
  worktree. Confirmed DCB and ACK-proven route promotion do not replace
  F/R/D source selection. A backup ACK alone cannot locate direct DATA
  versus direct ACK failure.
- Independent regression after the route-promotion slice: 114 focused
  passed; full suite 1020 passed, one skipped in 161.71 s; diff check clean.
  No reserved cohort, ICC/PDF, VERSION, GitHub or EDAS change.
- Recorded NO-GO for presenting the component as the core rewrite. A
  device-local joint source/feedback/recovery rule and matched causal
  controls remain required before manuscript revision.
- Added a public concurrent-flow regression for a newer direct ACK
  preceding an older backup ACK. It failed on the blind-promotion route;
  source-local latest-direct-ACK tracking made it and two adjacent tests
  pass. No reserved seed was used.
- Independent tri-state feedback audit found feasibility but no actual
  `seen`-backup evidence in prior passive traces. Wrote a draft one-flow
  ACK-gated trial source contract that replaces the inherited F/R/D
  selector while retaining same-flow fixed-F recovery as a control.
- Implemented and registered trial/no-switch variants with public
  RED/GREEN tests for one-flow trial, ACK-only commit, old D removal,
  one-miss F, same-wire control, late ACK, stale backup ACK, concurrent
  trials, nontrailing unresolved miss, and queued newer direct ACK.
  Independent audit findings drove the concurrency tests. Current focused
  DCB/SR/DHR/airtime suite: 74 passed; compile and diff check pass. Full
  current-tree suite not yet run; runner integration remains in progress.
- Corrected the trial contract's state-bound language: inherited miss and
  flood seen sets are unbounded. No 47xxx/48xxx, ICC/PDF, VERSION, GitHub
  or EDAS action was taken.

## 2026-10-06 - Decision on Full Rewrite vs Substrate Reuse

- Decision: preserve the validated PHY/channel/event/ledger substrate, but
  rewrite the source recovery core as the separately named MeshEcho-CPR
  successor. Do not continue tuning DRC or relabel old SR/DHR/DCB results.
- The decision is supported by the DRC development gate: candidate mean TX
  airtime `36.8304512 s` versus no-rescue `27.8528640 s` (+32.2%). This is a
  recovery-state-machine failure, not evidence that the physical simulator
  must be discarded.
- CPR remains in correctness/audit phase. Before any fresh development or
  ICC revision, fix stale overlapping-flow ACK admission, quarantined-route
  checks, strict no-cancel ledger semantics, bounded state retention, and
  action-to-request/TX plus route-generation provenance.

## 2026-10-06 - CPR Correctness Repair 1

- [complete] Added destination epoch snapshots and stale ACK rejection for
  overlapping same-pair flows.
- [complete] Added CPR timeout quarantine and `READY`-only initial/repeat
  route admission.
- [complete] Routed recovery through the public CPR controller and made relay
  ledger eviction explicit; no-cancel no longer enrolls ACK-cancellable
  records.
- [complete] Added ACK event-ID provenance linkage and route generation before
  and after commit.
- [complete] Focused tests: `15` CPR tests and `32` CPR/DRC tests passed;
  `py_compile` and `git diff --check` passed.
- [in_progress] Strengthen the independent CPR artifact audit, then run one
  fresh mechanical smoke. No development or holdout cohort is authorized
  yet.

## 2026-10-06 - CPR Mechanical Smoke 92010

- [complete] Strengthened runner scope, counts, duplicate accepted-ACK,
  physical marker/TX, deadline, endpoint/path, and generation provenance
  checks.
- [complete] Ran fresh nonreserved mechanical smoke `92010` to
  `results/meshecho_cpr_smoke_seed92010_20261006.manifest.json`; independent
  audit passed with zero incomplete RX TX joins.
- [pending] Add/verify a bounded-state and full action-to-request/TX audit,
  then run a predeclared exploratory matrix. Development and holdout remain
  closed.

## 2026-10-06 - CPR Evidence v2 Smoke 92011

- [complete] Bumped the CPR evidence schema to v2 and documented closed-world
  run scopes plus action/request/TX/ACK joins.
- [complete] Fresh seed `92011` passed the v2 runner and independent audit;
  `incomplete_rx_tx_count=0` for every arm.
- [error logged] A follow-up CSV display queried `incomplete_rx_tx`, which is
  not a CSV field; the corrected query used `incomplete_rx_tx_count` and
  returned zero for all four arms. No artifact was modified by the failed
  display command.
- [pending] Run the full current-tree regression and complete a bounded-state
  audit before opening exploratory seeds.

## 2026-10-06 - Full Regression Gate

- [complete] Full current-tree regression passed `1175` tests with `1` skip in
  `534.33 s`.
- [complete] `py_compile` and `git diff --check` remain clean after the CPR
  evidence-v2 changes.
- [in_progress] Write the exploratory CPR contract and run only fresh
  nonreserved exploratory seeds; no development/holdout or paper update is
  authorized by this regression alone.
# 2026-10-06 - CPR Exploratory Resume

# 2026-10-06 - CPR Release Closure

- Re-read the persisted planning files and confirmed the current goal remains
  the full MeshEcho-SR core rewrite, fair experiments, and major ICC revision.
- Promoted the audited CPR package to repository release `2.1.27` by updating
  `VERSION`, `CHANGELOG.md`, README/current experiment documentation, and the
  ICC submission checklist.
- Replaced the canonical PDF with the five-page
  `build-cpr-balanced-5` artifact. `cmp` passed and the canonical SHA-256 is
  `01cab1928e1eb8f583e3d42c873ff020de8518dfdf81bf45482136cebdba30`.
- Updated the release metadata regression to require `2.1.27` while retaining
  the old runner prefixes as explicitly historical 2.1.26 reproduction paths.
- Next command gate: run `python3 -m pytest -q`, `py_compile`, both CPR
  population audits, `git diff --check`, PDF text/page/hash checks, and a
  staged-file review. Only after all pass should the release be committed and
  pushed.

- [complete] Re-read the file-based checkpoint after automatic-context resume.
- [verified] Current branch is `version/v2`; CPR smoke `92011` is a valid
  evidence-v2 mechanical artifact with zero incomplete RX/TX joins, while the
  full tree reports `1175 passed, 1 skipped`.
- [complete] Independent architecture review reconfirmed that CPR replaces
  the source recovery decision core; preserving the radio simulator is needed
  for matched controls and does not mean retaining the old SR selector.
- [in_progress] Write the CPR exploratory contract and run only fresh seeds
  `92020..92029`. This stage is exposure/integrity screening, not a paper
  result or permission to revise ICC claims.
- [error] First exploratory invocation reached `audit_artifacts()` and failed
  with `ValueError: CPR source hash mismatch`. Diagnosis showed relative vs
  absolute contract-path labels; the generated bundle is invalid and must not
  be interpreted or overwritten silently.
- [complete] Normalized contract paths in source hashing and audit, added the
  CLI `--contract-path`, and passed all five CPR artifact tests plus compile.
  The invalid first bundle will be moved to a quarantine prefix before retry.
- [complete] Quarantined all nine invalid first-run artifacts under
  `results/invalid_cpr_path_audit_20261006/`; no invalid bundle remains at the
  formal exploratory prefix. The initial bare `mv` lookup failed, so the
  recoverable move used explicit `/bin/mv`.
- [error] The corrected exploratory run failed at `accepted CPR ACK TX identity
  mismatch` on seed `92024`: a valid reverse-path relay ACK had `sender=2` and
  destination `5`, while the source receiver was `6`. Add a public audit test
  and validate the physical reverse hop instead of requiring the destination to
  be the ACK transmitter.
- [complete] Added the reverse-path ACK join test and fixed the validator;
  CPR/runner tests now pass `20`, compilation and diff checks pass. Quarantined
  the second invalid bundle under
  `results/invalid_cpr_multihop_ack_20261006/` before the next run.
- [pending] Independently audit the exploratory bundle, then either freeze a
  development contract or record a CPR no-go without touching VERSION,
  GitHub, EDAS, or the final PDF.

## 2026-10-06 - Current release state after metadata promotion

- The prior exploratory entries above are historical checkpoints. The current
  authoritative state is the completed CPR development/holdout pair and the
  five-page CPR manuscript described at the top of this log.
- `VERSION` is `2.1.27`; the canonical PDF matches the checked build artifact
  byte-for-byte with SHA-256
  `01cab1928e1eb8f583e3d42c873ff020de8518dfdf81bf45482136cebdba30`.
- Release documentation now points to CPR and explicitly labels old
  protocol-family matrices as historical. No new seeds are to be run.
- Next action is verification and staged release review, followed by commit and
  push only if every audit and test passes.
