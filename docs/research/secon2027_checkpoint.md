# SECON 2027 执行检查点

更新时间：2026-11-04 Asia/Shanghai。完整持续目标：任务书所有必需 P0/P1、可复现 GitHub 发布与实际匿名 IEEE10pt ≤9 页 PDF；未完成，不得在阶段结束时标为完成。

## 实际工作位置
- Canonical source remains `/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2`, source files untouched.
- Active isolated Git checkout: `/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo`.
- Branch `codex/meshecho-secon2027`; imported actual sources baseline `a0ee4ce7bb96592c57dc5f389cf4c1958bec0069`; VERSION 2.1.27 / firmware 0.1.4.
- Managed create_worktree tool remains pending (functions cell g14:4), no operationId returned. After extended delay, normal Git worktree fallback created. attach_worktree explicitly refused fallback as unmanaged; no attachment success claimed. Continue work in explicit path, resolve app attachment when service returns. No source edits removed.
- Remote origin/version/v2 is `6a050c3df892743001a4c627fe3ff3b507b17049`, version 2.1.27; own work branch avoids altering it.

## Completed
- Read task book, audit, source planning/handoffs and required contracts. Persistent goal active in this thread.
- Copied and SHA-verified 488 source/test/document/firmware/paper assets; preserved executable modes. Import ledger `docs/research/secon2027_provenance/source_import.json`; 73 historical manifest/authorization files plus seed inventory preserved. Original ICC .tex/.bib/PDF copied unchanged; no new SECON PDF yet.
- Historical seed audit: 581 result files, 3.77 GB, 614 artifact seed IDs, zero parse failures. Conservative exclusion 0..999999; development candidates 2027000..2027002 unexecuted.
- Source import commit includes prior untracked runtime helper and tests, plus raw verified literature sources. Historical whitespace in raw HTML/docs deliberately retained; initial diff --check failed on those bytes, scoped whitespace exemption used only for import. No implementation verification claimed by import.

## In progress / ownership
- correctness_audit agent: CPR source/flow ACK correctness + clean controls, deterministic regressions. Owns CPR sections lora_mesh_sim.py, meshecho_cpr.py, optional meshecho_drc.py, correctness tests.
- evidence_audit agent: run_cpr_experiment/external, explicit registry, full ACK/RX/TX evidence, common environment/scenarios, tests.
- seed_inventory agent: registry/development contract/baseline fidelity/official requirement documents.
- root: snapshot/freeze/run-key-lock/cohort runner/audit and integration. Added Simulator.channel_uniform hook preserving historic default, enabling common environment override.

## Evidence / seeds / execution
No new performance simulation yet. No seed declared holdout. Existing tests may use deterministic fixture seeds only; test evidence kept distinct from registered new research runs. No long running simulation processes. No GitHub push yet.

## Next actions
Implement new `tools/secon2027_experiment.py` and schema/tests; integrate agent changes, register complete development run keys + freeze source before smoke. Run task-book focused tests, audit full evidence, then promote patch with explicit tested snapshot mapping and verify remote SHA. Pilot measured costs/exposures precede formal method/matrix freeze.

## Limits
No RF hardware connected or validation claimed. Official rules recheck pending. Academic-pipeline stage confirmations are superseded by user's explicit continuous-work authorization; actual integrity gates remain required. Do not invoke EDAS/payment/email.

## P0 implementation and independent review update
- Source/core: initial red suite 13 failures; first fixes green; independent supervisor found old timeout invalidating same-generation fresh route. Added per-route confirmation revision and per-flow captured revision; focused core suite 78 passed including cancellation checks (no research seed).
- Runner/scenarios: explicit registry, time/link common field, full generic ACK and delivery physical joins, required source closure, actual TX cutoff aliases, retained legacy_reserved_* counters; 26 fixture tests passed.
- Orchestration: full dependency snapshots, registry plans, exclusive per-key lock, immutable attempts, frozen subprocess worker, original/event audit before completion, exact mandatory evidence inventory, started/worker/manifest/CSV/spec/plan/source links. Supervisor swapped-package and empty-inventory counterexamples now rejected. Added explicit dead-process recovery preserving failed attempt and lock evidence, no implicit retries.
- Full integration command using /usr/bin/python3: 107 passed / 2 failed; both failures were review fixture missing newly mandatory worker_runtime.json, agent adapting fixture. Homebrew python3 3.14 has no pytest; /usr/bin/python3 3.9 has pytest. End-to-end frozen worker fixture under independent agent review.
- Development registry exists (2027000..2027002 reserved), smoke matrix defines 21 runs across seven arms, no performance execution yet. No source snapshot frozen until review tests pass.
- Baseline fidelity and official rules checked; latest official firmware has retry/fallback features missing from the -like models. Paper must not claim first-ever retry-before-flood or official product superiority.
- Analysis script delegated; uses raw physical TX, paired seed-level descriptive bootstrap, explicit undefined costs.
- User supplied supervisor runner review + 95-item acceptance matrix copied to local docs/research for final independent coverage audit. Full task remains active; no release promotion or push yet.

## Before registered P0 smoke
Frozen source e8d94c29b3797a55787ee8cc5a60c3d08b4949186f2250581ed36d851ef5b1a2; tested VERSION 2.1.27. Frozen test suite 142 passed in 4.88s, log results/secon2027/gates/p0-v3/frozen-tests.log. Plan 238973ce7c76a2317358cd2fa7e61acc2b7b0bf190192af7b731367cd3380ebd has 21 predeclared runs; 2027000..2027002 still reserved before launch. Earlier v1/v2 snapshots and failed-test log preserved, plans superseded-before-exposure; zero research runs under them. Next command /usr/bin/python3 tools/secon2027_experiment.py run --plan results/secon2027/plans/p0-smoke-v3.json (serial, abort on integrity error). No release bump yet.

## P0 smoke completed
- Registered plan p0-smoke-v3: 21/21 completed, 0 failed/missing. Runtime total 9.300804417s, peak worker RSS 43,466,752 bytes, 1,399 physical TX. All events retained; raw 18 MB.
- Independent event/plan audit complete: results/secon2027/gates/p0-v3/audit.json. Deterministic replay fixture92000 compares every row/flow/action/request/TX/RX/ACK/identity collection exactly; report deterministic-replay.json. This fixture is not new research evidence.
- Recoverable archive artifacts/secon2027/p0-tested-2.1.27-evidence.tar.gz, SHA256 eebec9050dfd2f31933fe2293275eb827f78e888c8554756ab86df5ab358493d (3,176,486 bytes, 887 files), every archived member SHA checked.
- Cohort2027000..2027002 exposed as development; no formal cohort exists. Pilot config is ready (72 runs, Poisson total offered rates8/8/40 per minute, 240s, S2 fault80..160s), not frozen/executed yet.
- Remote branch/tag conflict checks found no codex/meshecho-secon2027 branch or v2.1.28 tag. P0 release staging next; no new performance claim. Analyzer development changes will be separately tested/mapped rather than called VERSION-only.

## Resumed after service429 interruption
- Same task and isolated work/repo; no simulation/pytest workers running at recovery. User explicitly resumed complete P0/P1 scope. Goal tool currently reports blocked from failed service turns; operational work continues under renewed request (do not create replacement goal/chat).
- Managed create_worktree failed per supervisor; continue existing independent checkout, no further app-attachment wait.
- VERSION2.1.28 promoted locally after57 regression tests; uncommitted/unpushed. Last commit a0ee4ce import. Exact P0 data remains21/21, dev seeds2027000..2 exposed,42 start/completion history events, no pilot/formal run yet.
- Analyzer A1/A2/A3 fixes tested15/15; v2 analysis retained. A4 load curve effective-arm identity still open; agent owns fix+tests now. This changes analysis only, not raw P0 events.
- Reassigned paper blueprint and pilot read-only preflight after429 agent errors; no duplicate simulation. Next: close analysisA4, archive independently tested analyzer+outputs, scopedcommit/push2.1.28 verifySHA; freeze72-runpilot with current runtime, run serial then diagnose actual cached-path fault/pressure exposure.
