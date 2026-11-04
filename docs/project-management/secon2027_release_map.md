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

### Confirmed GitHub publication

Release2.1.28 commit **a64b2d92f2778089534700cbaa27d2ca453303ea** was pushed to `origin/codex/meshecho-secon2027`; `git ls-remote origin refs/heads/codex/meshecho-secon2027` returned the identical full SHA. No tag or merge performed. This checkpoint documentation follows the release commit and does not alter tested results.

### Subsequently discovered limitation of published2.1.28

The first full development pilot reached an untested high-load recovery rejection branch and terminated with NameError(CprDecision). The original P0 evidence remains21/21 but did not exercise this branch. Pilot v1 is48 complete/1 failed/23 unstarted, retained with its original frozen2.1.28 source and incident record. Published2.1.28 therefore is not validated for this recovery rejection case. The minimal fix is a new development round; no historical manifest or release result is relabeled, and no infrastructure retry is used. Next patch promotion requires corrected frozen regression and complete72-run pilot/audit.

## Round2 — recovery rejection import repair

- Tested version2.1.28, saved snapshot `ee890e25030782fc01208ee4ce1f20863c6ade5322ac954ad67ae48b594056a2`, plan `0c49a69a5c3725c9f72ff2e28ed870d10db1df7eec4319f6397097b84a2c85e7`. Production diff is the missing CprDecision import; policy/timers/parameters unchanged. Event-driven concurrent-flow regression reproduced NameError then passed; independent four invalid-route fixtures add no TX/airtime, READY allows recovery.
- Full frozenregression161passed; correcteddevelopmentpilot72/72,zero failures/missing,complete rawanalysis. All2027000..2 seeds remain development. v1 incomplete48/1/23 preserved in archive `pilot-v1-implementation-failure.tar.gz` SHA2562aaaf790ca67b05090a00aaeb3595f1f62a26cc663dabca5be4f20e492abdd1d.
- Promoted version2.1.29 changes VERSION and documentation after that verifiedsource. Correctedpilot manifests remain tested2.1.28. No firmware change. No formal validation or performance superiority claimed by this release. Promotedfixture/archive/commit/push evidence appended after actual completion.

### Round2 validation and recoverable artifacts

- Corrected pilot archive `artifacts/secon2027/pilot-v2-tested-2.1.28-evidence.tar.gz`, SHA25681e7222145e1689dc7dfeeff96264e57d33f250b5fb05a436fd2ec9e0a6df2b4,1517verifiedmembers,48442357bytes. It retains allraw72runs,source,testlogs,analysis,diagnostics andfailurecontext. The intermediate pre-report-closeout archive is retained locally and not the promoted evidence package.
- Promoted2.1.29 regression58passed; no researchseed rerun for version. Formal prospectivecontract is separately frozen and differs from the pilotcontract only in documented method/matrix/statistics/gate declarations; simulator methodfiles equal correctedpilot.
- Pre-exposure formalarchive `artifacts/secon2027/formal-v1-before-exposure.tar.gz`, SHA256192abcf1f8119db3f9ac9b07b06f5761d0a0783f0c174e0e5897e62c27827742,177verifiedmembers. It contains the full2.1.29source/newcontract,20reservedseeds,760keys and161passedfrozenchecks, withzero formalruns atpackaging.
- Formal plan5f1a12fe49bf7fc0ea32cc048a3595ed0bd290811f952a47c5a33b0cded2cbb0, source63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee. These identifiers are prospective evaluation artifacts, not completed formalresults.

### Confirmed2.1.29publication

Commit **95eee87e7757bcd8316088fee2517bc6a796801d** successfully pushed to the existing `codex/meshecho-secon2027` branch through GitHub SSH over443 after HTTPS connection failures. Authenticated official GitHub API returned the identical fullSHA. The stored origin/global network configuration was not changed. No tag/merge. Publicationlogs retain the failed HTTPSattempts and successfulSSHattempt. Formal scientific inputs166/166 match thiscommit per independentreleaseaudit.

## Round 3 — complete frozen evaluation and artifact tools

All 760 formal runs completed with zero failures on **tested2.1.29**, frozen snapshot `63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee`, plan `5f1a12fe49bf7fc0ea32cc048a3595ed0bd290811f952a47c5a33b0cded2cbb0`. Their 480 primary, 120 control and 160 extra deadline cases retain the original20seeds and one attempt per key. The administrative erratum was written after first exposure, with43keys complete; the original contract and every completed key remained unchanged. No formal result prompted tuning, replacement seeds or a new cohort.

Complete analysis is `results/secon2027/analysis/formal-v1`; analyzer SHA `7fd757a780e9725bd3d1992790eaad4a6cc3be7b48f7adcce674a729990eeb54`, Python3.9.6/NumPy1.26.4/Matplotlib3.7.5. All38cells use n20;10,000 seed-paired bootstrap resamples give descriptive unadjusted95% intervals. Independent supervisor raw/exposure/statistics reports and execution-side final statistics review are preserved under `docs/research/`. The raw-review checker's initial accepted-versus-all-ACK comparison was corrected transparently, retaining both versions; it was not a simulator defect.

The final research-artifact promotion is **2.1.30**. The pre-promotion regression passed161tests; post-promotion controller/frozen-worker/analyzer fixtures passed34tests. `closeout-tested-inputs.json` and `promoted-source-comparison.json` bind the mapping: of166formal inputs,165remain byte-identical and onlyVERSION changes. Additional archive/restore/inspection tools and manuscript rendering code are post-simulation utilities; they are not claimed as a VERSION-only change across the entire repository. The formal dataset is never labeled as simulated on2.1.30. Firmware stays0.1.4. No research seed was rerun for promotion.

Complete raw archive SHA256 `81776e12501e56945dd8aad6a37bb68e5f6e4b41d66c88ae041e7689e490d067`,475828160bytes,14667verifiedmembers. Eleven45MiB-or-smaller parts and their ordered checksum index are committed in `1e487d2327d27ae21fc000449a5f254c1621d92c`. The whole475MBtar is retained locally and excluded fromGitHub file staging. Its separate member index is included in the final closeout. A distinct final analysis/paper archive avoids duplicating the raw events.

This is a reproducible research release, not a demonstrated universal performance improvement. In particular, S3 recovery has adverse source-confirmation and airtime effects; the result reports and paper preserve them. No tag or merge is created. Final publication proof is recorded separately from the scientific source identity, with exact local and authenticated remote commit hashes.

### Verified raw delivery after transport repackaging

GitHub main work branch `codex/meshecho-secon2027` now contains exact commit **30e7bd42ecee5ff3d538601df8146934eca680fa** (parent95eee87), verified2026-11-04T10:53:28Z. Original local1e487d2 was not uploaded: single large pushes and45MiBrequests failed. User-authorized transport repackaging created114parts≤4MiB from the identical475828160-byte gzip, with the same whole/member hashes. No scientific evidence was recompressed or changed. Original1e is protected by local archive ref, and its commit bytes/blob mapping are retained in `formal-v1-raw-evidence.transport-history.json`; historical11part index and files remain intact. The new commit preserves all original small helper/erratum files and adds the unchanged member index. Nonforce official GitDatabaseAPI publication verified123blobs, exacttree and exactcommit. The source checkout was moved onto this verified lineage only after confirming empty staging and unchanged hashes of all current working files.

### Final2.1.30artifact publication verified

Release commit **e653315803c46abf80fb6d3476eee3b5f7fd34a4** was published without force on `codex/meshecho-secon2027`; the authenticated official GitHub ref returned that exact fullSHA. Its parent is the verified4MiBrawdelivery30e7bd42. The exact tree and every changed blob were verified through GitDatabaseAPI. The durable receipt is `docs/project-management/secon2027_publication_receipt.json`. A subsequent documentation-only commit closes the live95-item checklist and records this verification; it does not alter the scientific source, statistical outputs, finalPDF or archives. The final metadata-tip verification is included with user-facing outputs.

Final PDF:186064B,9Letterpages,IEEE10pt,26embeddedfonts,27resolvedreferences; SHA256 `e477617e417a5c089bfeac3f4725e40e54e39e666071a1711c5c0e0f749eb1fd`. Finalanalysis/paperarchive:9978264B/1230verifiedmembers, SHA256 `d60a67eb549905af087968b3c1ab496851ef78ebf38f8e9be6c26c29584e66e9`, published as3parts≤4MiB. Cleanrestoration andfourCSV/fourPNGbyte-identical re-renderpassed. Large raw/diagnostic files are recoverable from the indexed packages, not omitted evidence. Local whole archives, original45MiBparts and the original1e archivalref are intentionally retained. No tag/merge or EDASsubmission occurred.
