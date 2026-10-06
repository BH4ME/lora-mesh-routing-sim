# MeshEcho Core Rewrite Handoff

## 2026-10-06 final verification continuation

- CPR development and holdout audits both pass after re-audit; the complete
  repository regression is `1181 passed, 1 skipped`.
- The final source build is
  `paper/icc2027/build-cpr-balanced-5/icc2027_lora_mesh.pdf`, a five-page
  Letter PDF rendered and visually checked on all pages. The last-page
  references are balanced with the local `balance.sty` package.
- The paper's relay-ledger wording now matches the implementation: the local
  handle index and stored endpoint/path validation are described separately.
- Before any automatic context compression, update these four files again if
  release packaging advances. After compression, read them before acting.
- Remaining release work: copy the final PDF to the canonical path, update
  VERSION/release metadata, run the final package consistency audit, and push
  only the verified changes to GitHub. Do not operate EDAS in this phase.

## 2026-10-06 final PDF verification checkpoint

- CPR development and untouched holdout artifacts have passed their declared
  integrity, exposure, reliability, and cost gates.
- The ICC TeX has been migrated to CPR and the current build is a valid
  five-page PDF. Poppler rendering found no clipping or overlap; the remaining
  issue is IEEEtran last-page reference-column balancing.
- Before the next compression, record the result of the balance-package
  rebuild, final tests, canonical PDF copy, VERSION decision, and Git state
  here together with `task_plan.md`, `findings.md`, and `progress.md`.


## 2026-10-06 CPR manuscript-migration checkpoint

- Current active phase: replace the old ICC 2.1.26 manuscript with a CPR
  manuscript sourced only from the audited development and holdout artifacts.
- CPR code and experiments are complete enough for paper drafting: the
  independent source/recovery FSM, physical ACK-gated relay cancellation,
  development cohort `92200..92219`, and untouched holdout `92300..92319`
  have passed their declared audits.
- Current ICC TeX/PDF, `VERSION`, GitHub, and EDAS have not been changed in
  this continuation. Do not reuse legacy 2.1.26 tables or figures.
- Next action: regenerate paper aggregates/figures from the CPR manifests,
  rewrite the five-page ICC source, compile and inspect the PDF, then run the
  full regression and final consistency audit.
- Before automatic context compression, update this handoff together with
  `task_plan.md`, `findings.md`, and `progress.md`; after compression, read all
  four files before making edits or interpreting evidence.

Updated: 2026-10-05

## Objective

Rewrite the MeshEcho-SR protocol core, validate it with fair paired simulations,
and revise the ICC manuscript only from verified development and untouched
holdout evidence. Preserve resumable state here before context compression.

## Current Truth

- The simulator, LoRa PHY, accounting, historical controls and old manuscript
  are preserved in the dirty `version/v2` worktree.
- `MeshEchoSR` still owns the inherited F/R/D source controller; DHR/DCB/Trial
  are components or exploratory variants, not a demonstrated new full core.
- The 492xx/493xx screens are exploratory. They do not justify a paper claim,
  VERSION bump, GitHub push or EDAS update.
- The current ICC PDF/TeX still reports the 2.1.26 calibrated max-min policy.
- The 49400 smoke and 49401--49440 cohort are closed.

## Scientific Decision

Reuse the simulation platform, but replace the joint source action, feedback
interpretation and failure-recovery decision core. The candidate must use only
device-observable state, preserve charged wire cost, use bounded state, and be
tested against same-wire no-change and simple recovery controls. A fixed timeout
or renamed PRR score is not a sufficient rewrite.

## Immediate Gates

1. Complete an explicit protocol contract and prior-art boundary.
2. Add one public RED test, implement one minimal vertical slice, then repeat.
3. Close runner evidence gaps: request/outcome joins, collision callbacks,
   queue wait/no-start/deadline censoring, equal-time event order, full mutable
   prefix state, and fail-closed artifact recomputation.
4. Run only a mechanical smoke after independent audit and exact hash freeze.
5. Run disjoint development seeds, apply frozen gates, then an untouched holdout.
6. Rewrite the manuscript, compile and visually inspect the PDF, bump VERSION,
   run the full regression and publish only after all gates pass.

## Active Work

- `tools/diagnose_matched_d_trigger.py`: diagnostic infrastructure only; no
  accepted new online controller yet.
- `docs/research/meshecho_d_trigger_matched_branch_design.md`: draft matched
  branch contract; candidate seeds remain unopened.
- `docs/research/meshecho_core_rewrite_checkpoint_20261005.md`: longer audit
  history and prior NO-GO decisions.
- Parallel audits: core algorithm proposal and experiment-contract review.

## Recovery Rule

After any automatic context compression, read this file first, then read
`task_plan.md`, `findings.md`, `progress.md`, the core checkpoint, and the active
design/audit files before taking further actions. Do not infer completion from
old test counts or prior summaries.

## Last Verified State

- No new seed has been run in this continuation.
- No ICC manuscript, VERSION, GitHub or EDAS update has been made.
- Existing dirty-tree changes belong to the ongoing research task and must be
  preserved; do not reset or discard unrelated files.

## 2026-10-06 DRC Pure Decision Slice

- Added `meshecho_drc.py` as a simulator-independent source controller. Its
  public `choose_start_action(DrcObservation)` evaluates at the physical TX
  start and exposes `R_RESERVED`, initial `F`, `R_ONLY`, recovery `F`, and
  `DROP_DEADLINE_INFEASIBLE` branches. A reserved route is selected only when
  `now + B_R + B_F0 <= deadline`; recovery requires the original route
  generation and a fresh `now + B_F0 <= deadline` check.
- Added `DrcSourceState` with bounded eight-entry route and eight-entry active
  flow records, deterministic LRU route eviction, state-capacity registration
  drops, and explicit route quarantine/recovery state transitions.
- Added `tests/test_meshecho_drc_controller.py`; the focused suite currently
  passes 12 tests. The first test was run RED before creating the module, then
  the minimal implementation was made GREEN. `python3 -m py_compile
  meshecho_drc.py` passes.
- The parent DRC integration now wires this slice into a separate
  `MeshEchoDRC` class in `lora_mesh_sim.py`; focused DRC integration tests and
  the controller suite pass. The request/RX/ACK artifact ledger, paired
  experiment runner, ICC manuscript, VERSION, GitHub, and EDAS remain
  unfinished. No development or holdout seed was run.
- `DrcSourceState.accept_valid_ack()` now commits a source-validated ACK,
  cancels a pending unstarted recovery, or installs a realized F path as a
  new route. The caller remains responsible for physical sender/path/marker
  validation; the pure module does not read simulator topology or delivery
  flags.
- `DrcSourceState.record_in_deadline_miss()` quarantines a matching route
  generation and evicts it after the second in-deadline miss; stale
  generations cannot mutate a newer route.
## 2026-10-06 continuation note

The current user question asks whether CPR should be replaced by a wholly new
algorithm. Code review confirms that the source/recovery core is already a
successor algorithm; only the physical simulation substrate is shared with DRC
for fair controls. `MeshEchoCPR` still inherits the DRC implementation class,
so release review must distinguish policy independence from implementation
reuse and decide whether to refactor that base before committing.

The release decision is to retain the CPR core and shared physical substrate;
no second algorithm rewrite is justified by the audited evidence. Clean formal
development/holdout reruns completed on commit `a013067` with all population
gates and the full test suite passing. Final packaging should include only the
CPR source, contract, paper, formal artifacts, and gate reports.

The package was subsequently committed as `7d2753c` plus verification commit
`ad24baa` and pushed to `origin/version/v2`. The two large RX-attempt ledgers
were accepted by GitHub with a recommended-size warning.
