# Historical seed and dependency inventory

Read-only audit of `/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2`, HEAD `ea0af90b8146ba5b8d7d518ae43997d9550e7ca4`, performed 2026-11-04. No simulator imported or run. The canonical tree was not edited.

`historical_seed_inventory.json` records every result JSON/JSONL/CSV containing a seed field, seed lists, SHA-256 and size, source-document range mentions, authorizations and a preservation list. `legacy_registry_import.json` is the curated status interpretation. `dependency_closure.json` is a static local-import closure from the CPR runner/comparison/auditor, with current file hashes. `inventory.py` reproduces the raw scan; curated decisions are deliberately separate.

The result scan found 496 seed-bearing files and 614 distinct artifact seed IDs, all at or below 92319, with zero parse failures. This is an artifact inventory, not a count of independent experiments. Repeated attempts and invalidated artifacts remain exposed. Documented in-memory and temporary-file experiments add exposed IDs beyond this artifact list.

Use a conservative SECON fence excluding all `0..999999` from new research cohorts. This does not claim all those seeds ran: it protects historical exposed, closed, reserved and ambiguous ranges without silently repurposing another contract's holdout. A scan-confirmed disjoint proposal for development is `[2027000, 2027001, 2027002]`; these have not been registered or run by this audit. Freeze their exact authorized uses in the new registry/contract before execution. Do not allocate the final validation cohort merely from this proposal.

Reserved/closed cohorts include 4001–4040, 10001–10040, 17001–17040, 24001–24040, 28000–28040, 29001–29040, 35001–35040, 36001–36040, 42101–42120, 43101–43120, 44001–44020, 44101–44140, 44200, 47000–47020, 48001–48040, 49401–49440 and 63001–63020. Exact source pointers appear in the curated JSON. Old documents calling 92200–92219/92300–92319 untouched are superseded by saved result evidence; they are exposed.

Important exceptions:

- 43000 was run in memory during an earlier audit. No result archive was saved, but it is exposed (`meshecho_source_ack_snr_signal_gate.md:29`).
- The first receipt attempt ran seed 45001 before failure and produced no result archive; the later complete 45001–45020 run does not erase that attempt (`meshecho_first_hop_receipt_explore_results.md:27`).
- A filename and progress entry call a DRC smoke `91002`, but that manifest and its seed hashes actually identify 91000. Preserve this inconsistency and exclude both IDs; do not infer execution seed from filenames.
- The raw mention extractor intentionally over-collects nearby numeric ranges, including some code/page ranges. Do not use all mentions as semantic cohort registrations. The curated JSON plus broad exclusion is the machine guard basis.

## Isolation preservation

The actual minimal local Python dependency closure comprises `lora_mesh_sim.py`, `meshecho_cpr.py`, `meshecho_drc.py`, `meshecho_utility.py`, `tools/run_cpr_experiment.py`, `tools/run_cpr_external_comparison.py`, `tools/audit_cpr_population.py`, `tools/run_drc_experiment.py` and `tools/run_drc_population.py`. The last three runner-related files include existing untracked dependencies, so an old HEAD checkout alone is incomplete. `requirements.txt` currently declares standard-library-only simulation; pytest and plotting/PDF tooling are separate validation/authoring dependencies.

For a reproducible current-state baseline, preserve all root Python files, `tools/`, `tests/`, requirements/configuration, `VERSION`, documentation/contracts/authorizations, root planning logs, current ICC TeX/Bib/figure inputs and verified literature evidence. Preserve firmware source/include/test/platformio/VERSION separately if it is part of the baseline; `.pio`, compile databases, historical `build-*` folders, caches and package directories are not source dependencies. The current git tree has ~243 MB of tracked result files; retain them through the normal worktree and overlay needed current files, rather than copying the entire 3.5 GB historical results tree.

For seed provenance, preserve all historical manifests, authorization JSON, gate JSON, source contracts and this inventory. The explicit `preserve_evidence` list also includes compact seed-bearing CSVs, totaling about 15 MB. Large historic JSONL can remain in the canonical tree with recorded hashes unless needed as a selected evidence dependency. Do not claim unavailable temporary `/tmp` artifacts were recovered. New SECON raw events must be archived completely under their own run IDs.

The old `_source_hashes()` omits imported `tools/run_drc_experiment.py` (and external comparison code when used); snapshot validation must use the full dependency closure or a broader frozen source manifest, not copy this incomplete historical hash list.
