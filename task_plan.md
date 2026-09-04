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
- [in_progress] Push the committed task-related files and update the draft PR.
- [pending] Verify remote commit, PR metadata, and final artifact state.

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

- Local `HEAD` is `087f84e`, version `2.1.11`, and is one commit ahead of
  `origin/version/v2`.
- The relevant files are already committed; the remaining publish gate is
  `git push` followed by updating and verifying draft PR 1.
