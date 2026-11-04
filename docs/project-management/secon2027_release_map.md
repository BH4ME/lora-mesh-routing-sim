# SECON tested-source and promoted-release map

## Round 1 — correctness, runners and P0 evidence

- Imported canonical working state: `a0ee4ce7bb96592c57dc5f389cf4c1958bec0069`, based on canonical `ea0af90b8146ba5b8d7d518ae43997d9550e7ca4`. Original source tree retained.
- Tested simulator version: **2.1.27**; full frozen source SHA256 identity **e8d94c29b3797a55787ee8cc5a60c3d08b4949186f2250581ed36d851ef5b1a2**.
- Frozen P0 plan: `results/secon2027/plans/p0-smoke-v3.json`, plan SHA256 `238973ce7c76a2317358cd2fa7e61acc2b7b0bf190192af7b731367cd3380ebd`.
- Frozen source verification: 142 tests passed; 21/21 mechanical development runs complete and raw-event audited; deterministic fixture replay identical. Evidence under `results/secon2027/gates/p0-v3/`. Smoke alone did not exercise repeat/recovery (all CPR flows cold); actual mechanism exposure must be checked in pilot.
- Exact recoverable archive: `artifacts/secon2027/p0-tested-2.1.27-evidence.tar.gz`, SHA256 `eebec9050dfd2f31933fe2293275eb827f78e888c8554756ab86df5ab358493d`; member hash index alongside. Archive contains all raw events, saved source, contracts, registry at completion, superseded unexecuted v1/v2 plans and frozen test evidence.
- Promotion: **2.1.28**, after the above audit. Simulator/runner/scenario runtime files match tested source; VERSION and release documentation change. The analysis tool is separately developed/tested after simulation, and is explicitly **not** described as a VERSION-only difference. Its validation and hash are appended below when closed.
- Historical simulation manifests remain unchanged and continue to identify tested2.1.27. Promotion uses correctness fixtures only; no research seed is rerun to change labels.
- GitHub target: `origin`, branch `codex/meshecho-secon2027`. Branch/v2.1.28 tag did not exist before promotion; no tag created. Commit/push SHA pending completion of scoped staging and release checks. Promoted2.1.28 regression:57 passed in2.37s, `results/secon2027/gates/p0-v3/promoted-2.1.28-regression.log`; includes actual frozen worker fixture92000, not a research-seed rerun.

## Analysis tool mapping (pending final closeout)

The raw P0 package is unaffected by analysis-only classification fixes. Every generated analysis directory is exclusive and records the analyzer source hash; superseded analysis is retained. Final analyzer unit tests and actual raw-evidence CLI run must pass before including it in this release.

### Closed analysis tool validation

- Final analyzer SHA256 `7fd757a780e9725bd3d1992790eaad4a6cc3be7b48f7adcce674a729990eeb54`;18 tests passed and actual raw-only reanalysis21/21 completed at `results/secon2027/analysis/p0-smoke-v3-analysis-v3`. A1/A2 exported enums andRREP roles corrected; A3 clean controls require effective-parameter equivalence; A4 load curves bind each distinct arm effective parameters.
- Analysis-only changes postdate the frozen simulation; no raw event or old manifest changed. v1/v2 analyses remain archived as superseded.
- Analysis/promotion recoverable archive `artifacts/secon2027/p0-analysis-and-promotion-2.1.28.tar.gz`, SHA256 `fe305df09f9c2f242c92e07ce86e1c6e4ffd58a553c7f7f6bd455d0121156309`; all member hashes verified. Includes final analyzer/tests,18-test log, three analysis revisions and57-test promoted regression evidence.
