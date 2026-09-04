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
