# Progress Log

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
  `Gao Zu (高足)` and `Quan Zhi (全智)`, in that order.
- Added the shared affiliation `Shenzhen University, Shenzhen, China`.
- Added the CJK font declaration needed to render the Chinese names in the
  Tectonic PDF while keeping EDAS-friendly Latin spellings.
- Updated the ICC checklist, README, plan, and findings; EDAS registration and
  exact title/author matching remain pending.
