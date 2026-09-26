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
