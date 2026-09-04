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
