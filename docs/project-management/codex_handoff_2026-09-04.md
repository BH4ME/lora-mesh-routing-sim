# Codex Handoff - 2026-09-04

## Objective

Revise the MeshEcho conference manuscript using the current simulator
evidence, explicitly address fairness concerns in the evaluation, bump the
repository version by one patch release, and publish only the relevant changes
to GitHub.

## Scope

- Primary manuscript:
  `paper/icct2026/icct2026_lora_mesh_preliminary.tex`
- Primary data:
  `results/meshecho_v2_1_2_50n_*.csv` and matching summaries
- Fairness evidence:
  `results/meshecho_route_conflict_fairness.csv`
  `docs/results/meshecho_route_conflict_fairness.md`
- Release metadata:
  `VERSION`, `CHANGELOG.md`, and related project notes

## Current Evidence

- All Python tests passed before this handoff: 40 tests, `OK`.
- The no-fallback confidence-threshold bug is fixed in `lora_mesh_sim.py`;
  its regression test is in `tests/test_calm_protocol.py`.
- Current main-matrix results use 50 nodes, a 3000 m square, eight repeated
  unicast pairs, 20 seeds, and seven protocol configurations.
- The main matrix is not a fully neutral benchmark:
  fixed pairs favor route caching, the default 3000 m/SF9/4 dB setting is
  relatively easy, and Smart-CALM's timeout retry/fallback budget is not
  matched by the two fixed baselines.
- A small probe confirmed that removing fixed pairs and using a sparser,
  harsher channel materially lowers MeshEcho reliability. This should be
  reported as a fairness limitation, not hidden.
- The controlled route-conflict fairness audit uses one fixed seven-node
  topology. Current 100-seed values:
  - null: paired ACK-PDR delta `0.000`
  - short branch +5 dB: paired ACK-PDR delta `0.000`
  - short branch +7.5 dB: paired ACK-PDR delta `+0.215`
  - long branch +7.5 dB reverse control: paired ACK-PDR delta `0.000`
- Fairness audit found that the current 50-node/3000 m/SF9 link budget is
  link-quality saturated: 128/129 MeshCore cached routes and 142/142 CALM
  cached routes are one hop across the 20 main seeds, and the calculated
  minimum direct-link PRR with an extra 8 dB loss is `0.9999866`.
- The ICCT manuscript now explicitly labels the main matrix as
  contention-oriented rather than a calibrated multi-hop deployment model, and
  states that MeshEcho end-to-end gains combine route admission with
  unshared fallback/recovery budget.
- Added `docs/results/meshecho_fairness_audit.md` with the full fairness
  boundary and required follow-up.

## Work Plan

1. Reconcile manuscript tables, abstract, discussion, and conclusion with the
   current CSV summaries.
2. Update the paper's fairness language:
   - separate mechanism evidence from end-to-end performance;
   - disclose fixed-pair, easy-link, and unequal-recovery-budget effects;
   - avoid attributing the full Smart-CALM gain to confidence ranking.
3. Update figure source/data and rebuild figure PDFs if needed.
4. Bump the current workspace version `2.1.7 -> 2.1.8` and add a concise
   changelog entry.
5. Compile the manuscript with the bundled LaTeX workflow and inspect page
   count, warnings, and rendered pages.
6. Run tests and diff checks.
7. Stage only the manuscript, figures, relevant evidence, metadata, tests,
   and implementation files changed for this task; commit, push, and open a
   draft PR.

## Continuation Rule

Before any context compression, update this file with completed steps,
commands, outputs, and the exact next action. After compression, read this file
before taking further action.

## Current Resume State - 2026-09-04

- The current branch is `version/v2`, based at `cc423da`, with the fairness
  revision, 2.1.9 manuscript changes, and related artifacts ready for the
  publish gate.
- `gh` was authenticated as `BH4ME` earlier; origin is
  `BH4ME/lora-mesh-routing-sim`, whose default branch is `main`. Recheck
  authentication before pushing.
- Python validation after the RNG-isolation change: 42 tests passed.
- Added opt-in `--independent-rng-streams` support in `lora_mesh_sim.py` and
  `INDEPENDENT_RNG_STREAMS=1` forwarding in `tools/run_icc_experiments.sh`.
  Legacy mode remains the default so frozen result files stay reproducible.
- Revised `paper/icct2026/icct2026_lora_mesh_preliminary.tex` to disclose
  high-PRR/one-hop saturation, fixed-pair bias, unequal recovery budgets,
  shared-stream history, the new independent-stream option, and fixed-payload
  route-header simplification.
- Repository release metadata is now `2.1.9`; the firmware prototype remains
  `meshecho-firmware-v2.1.2`.
- Tectonic rebuilt the manuscript to 7 pages at
  `paper/icct2026/build-2_1_9/icct2026_lora_mesh_preliminary.pdf`. The root PDF
  was refreshed, has PDF version 1.5, and all 7 rendered pages under
  `paper/icct2026/rendered_final_2_1_9/` were visually inspected. Remaining
  diagnostics are font fallback and underfull boxes; no unresolved reference
  was found after the rerun.
- `git diff --cached --check` is clean after normalizing
  `results/meshecho_route_conflict_fairness.csv` to LF.

## Status

- [x] Workspace and process state inspected
- [x] Existing fairness evidence reviewed
- [x] Manuscript numbers and claims updated
- [x] Figure sources patched for PDF-version compatibility
- [x] Figures force-rebuilt and metadata checked
- [x] Final paper PDF rebuilt and rendered-page checked
- [x] Version bumped from 2.1.7 to 2.1.8
- [x] Version bumped from 2.1.8 to 2.1.9
- [x] Tests and diff checks rerun after final edits
- [ ] Relevant files committed and pushed
- [ ] Draft PR opened

## Next Action

The final checks passed: 42 Python tests, `git diff --check`, version/paper
consistency, and PDF metadata/render inspection. Stage the modified 2.1.9
manuscript/PDF and release files, recheck `gh auth status`, commit as the
`2.1.9` fairness-aware manuscript release, push `version/v2`, and open a draft
PR against `main`. Do not add build directories, caches, temporary probes,
course materials, or unrelated worktree changes. If context is compressed
again, read this file first and continue from the publish gate.

## Final Publish State - 2026-09-04

- Commit: `a94aaee` (`Prepare 2.1.9 fairness-aware paper release`).
- Remote: `origin/version/v2` points to the same commit as local `HEAD`.
- Draft PR: `https://github.com/BH4ME/lora-mesh-routing-sim/pull/1`.
- PR state: OPEN and DRAFT; base branch `main`, head branch `version/v2`.
- Final verification: 42 tests passed; Python compilation and shell syntax
  checks passed; staged diff check passed.
- Final paper: 7 pages, PDF 1.5, root artifact at
  `paper/icct2026/icct2026_lora_mesh_preliminary.pdf`; seven rendered pages
  were inspected.
- Untracked build outputs, caches, temporary probes, course materials, and
  unrelated documents remain outside the published commit by design.
- The goal is complete unless the user requests additional revision or a new
  fair multi-hop result matrix.

## Current Resume State - 2026-09-04 (2.1.10 fairness-probe revision)

- User requested that the ICCT manuscript be revised using the fairness
  findings, that the repository version be incremented for traceability, and
  that the resulting changes be uploaded to GitHub.
- The manuscript source now includes a random-pair, non-saturated multi-hop
  probe section and table. It reports the ten-seed direct-link PRR quantiles,
  ACK PDR, destination PDR, airtime, P95 ACK delay, and cached-route hop
  fraction. The abstract, traffic model, discussion, limitations, future work,
  and conclusion were updated to match the evidence.
- The manuscript preserves the frozen 3 km repeated-pair matrix and labels it
  as a contention-oriented high-PRR case. It does not claim universal
  MeshEcho or Smart-CALM superiority.
- Repository version is now `2.1.10`; `CHANGELOG.md`,
  `README.md`, `docs/icc2027_experiment_plan.md`, and
  `docs/project-management/smart_calm_sim_versions.md` were updated.
- The fairness audit now describes the random-pair probe as an initial check
  that should be expanded, rather than as an absent future experiment.
- The next exact actions are: compile the revised manuscript using the
  `latex-compile` skill, inspect page count and diagnostics, run the Python
  tests and diff checks, stage only the relevant manuscript/probe/evidence/
  release files, commit as a 2.1.10 fairness-probe revision, push
  `version/v2`, update draft PR 1, and verify the remote state.
- Do not stage build directories, caches, temporary probes, course materials,
  or unrelated worktree changes. If context is compressed again, read this
  section first and continue from the compile/verification step.

## Current Resume State - 2026-09-04 (2.1.11 fairness and budget revision)

- The user requested that the ICCT paper be updated using the fairness audit,
  that the repository version increase by one for traceability, and that the
  changes be uploaded to GitHub. The user also requested that ongoing state be
  written to Markdown before context compression and read back after resume.
- The current branch remains `version/v2`; the remote is
  `BH4ME/lora-mesh-routing-sim`; the existing draft PR is PR 1 against `main`.
- The repository version has been changed from `2.1.10` to `2.1.11`. The
  firmware prototype remains `meshecho-firmware-v2.1.2`.
- The simulator and fairness probe now expose
  `route_discovery_attempts`, `route_discovery_successes`,
  `route_discovery_success_rate`, and `rrep_rreq_tx_ratio`. The probe also
  accepts `--smart-max-timeout-retries 0` for a one-shot mechanism check.
- New preserved diagnostics:
  - `results/meshecho_fair_connected90_lowload.csv`
  - `results/meshecho_fair_connected90_singleflow.csv`
  - `results/meshecho_fair_budget_matched.csv`
  - `results/meshecho_fair_budget_matched_connected20.csv`
  - matching Markdown reports under `docs/results/`
- The one-shot random-pair table now uses:
  - MeshEcho ACK-PDR `0.413`, airtime `97.5 s`;
  - source-route cache ACK-PDR `0.456`, airtime `139.5 s`;
  - Smart-CALM ACK-PDR `0.489`;
  - Smart-CALM-no-confidence ACK-PDR `0.488`;
  - paired full-vs-no-confidence ACK-PDR delta `+0.001`, 95% CI
    `[-0.105, 0.108]`.
- The paper source
  `paper/icct2026/icct2026_lora_mesh_preliminary.tex` has been revised to:
  - label the original 3 km/SF9 matrix as link-friendly and cache-friendly;
  - use the one-shot budget-matched random-pair result instead of the
    recovery-heavy Smart-CALM result;
  - add a route-discovery stress-check subsection;
  - state that general confidence-ranking superiority is not established;
  - update the repository release string to `2.1.11`.
- Release documentation updated:
  `VERSION`, `README.md`, `CHANGELOG.md`,
  `docs/icc2027_experiment_plan.md`,
  `docs/project-management/smart_calm_sim_versions.md`,
  `docs/results/meshecho_fairness_audit.md`,
  `findings.md`, `progress.md`, and `task_plan.md`.
- The compatibility patch for the probe uses a default of two timeout retries
  when called with an older `argparse.Namespace` that lacks the new field.
- Validation already completed before this handoff update:
  targeted tests `45 passed`; full `pytest -q` also passed when invoked with
  `python3 -m pytest -q`; Python compilation and `git diff --check` passed.
  A bare `pytest -q` failed during collection because the repository root was
  not placed on `sys.path`; do not use that command as the final test command.
- Final validation after this handoff checkpoint is complete:
  `python3 -m pytest -q` reports 45 passed; Python compilation, shell syntax,
  and `git diff --check` passed.
- The revised manuscript compiled successfully with bundled Tectonic to 8 pages.
  All 8 rendered pages were visually checked. The final log contains only
  font fallback and underfull-box diagnostics, with no unresolved references.
  The root PDF is byte-identical to the `build-2_1_11` PDF and has SHA-256
  `b822940c36b13a084538691b526a2b72c0d32463c67ff4772e76937fa4ab9b9a`.
- Remaining exact actions:
  1. Stage only the related paper, result, fairness, simulator, test, probe,
     release, and planning files; do not stage unrelated build outputs or
     user-generated documents.
  2. Commit as a `2.1.11` fairness/budget-matched revision and push
     `version/v2`.
  3. Update draft PR 1 from `2.1.9` to `2.1.11` and verify remote state.
- If context is compressed again, read this section plus `task_plan.md`,
  `findings.md`, and `progress.md` before continuing. Do not restart the
  analysis or silently replace the frozen main matrix.

## Publish Continuation - 2026-09-04

- The current local `HEAD` is `087f84e`
  (`Update MeshEcho paper with fairness-aware evaluation`), and it contains
  the complete 2.1.11 manuscript, fairness evidence, simulator diagnostics,
  tests, and release metadata.
- `VERSION` is `2.1.11`; the firmware prototype identity remains
  `meshecho-firmware-v2.1.2`.
- The local branch is `version/v2`, one commit ahead of
  `origin/version/v2`. The remote branch still points to the earlier 2.1.9
  publish commit, and draft PR 1 still has the 2.1.9 title.
- Validation already confirmed: `python3 -m pytest -q` reported 45 passed,
  Python compilation passed, shell syntax passed, `git diff --check` passed,
  and the final paper is an 8-page PDF with SHA-256
  `b822940c36b13a084538691b526a2b72c0d32463c67ff4772e76937fa4ab9b9a`.
- Untracked build outputs, caches, temporary files, course materials, and
  unrelated documents remain intentionally outside the commit.
- Exact next action: push `version/v2`, update draft PR 1 to describe the
  2.1.11 fairness/budget-matched revision, then verify remote commit, PR
  metadata, and final artifact state.
