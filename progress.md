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
