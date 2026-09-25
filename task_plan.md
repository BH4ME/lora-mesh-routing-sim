# Task Plan: MeshEcho Fairness Revision and GitHub Publish

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
- [in_progress] Verify tests, reproducibility, five-page PDF layout, versioned
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
- [in_progress] Rerun tests and staged-diff checks, then commit/push and
  verify PR 1.
- Do not rerun the completed 20-seed simulations for this formatting fix.

### 2.1.23 Final Pre-publish Gate

- `python3 -m pytest -q`: 111 passed. Python compilation, shell syntax,
  staged/unstaged whitespace checks, PDF SHA-256, and 49-file scope check pass.
- Staged ICC manuscript, checklist, and release notes contain `Zu Gao` and
  `Zhi Quan`; no old name order or Han author characters were found there.
- PR 1 is still draft on 2.1.22 and its old body mentions Chinese names.
  Replace its title and body after the new commit is pushed.
