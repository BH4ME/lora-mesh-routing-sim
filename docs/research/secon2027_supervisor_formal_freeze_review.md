# SECON 2027 supervisor formal-freeze boundary review

Status: frozen chain verified; documentation finding F1 closed by a transparent administrative erratum. Initial observation: 2026-11-04T09:07:11.282867+00:00; erratum verification: 2026-11-04T09:12:00.354550+00:00. Execution tree: `/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo`.

The formal plan contains exactly **760 unique runs: 480 primary + 120 controls + 160 deadline/drain robustness**, using exactly **20 seeds, 2027100–2027119**. All 760 complete run records and keys were independently reconstructed from the matrix. The 166-file saved source inventory, logical plan/matrix digests, contract, method decision, embedded development gate and full pilot references match. The seven method files are byte-identical to the corrected, completed pilot. No scientific population or method-binding mismatch was found.

## Finding F1 — closed by transparent administrative erratum

The frozen contract `docs/research/secon2027_experiment_contract.md`, SHA-256 `0db4fc2e724f441e190693e3f8d37b7912e2d4baa5555515c6f132481f309eff`, retains “development draft” in its title and, at line 3, “executable source/config/run-key freeze pending” and **“This document authorizes no formal validation cohort.”** Its later one-time formal freeze section (lines 55 onward) specifies the exact formal method, cohort and 760-run matrix. Both formal-v1 and the gate bind this same file. Hash consistency does not remove the textual contradiction.

At 09:05:54Z the registry remained reserved with no formal starts. During the final read-only verification, formal execution began: the earliest observed actual `started.json` is **2026-11-04T09:06:36.647153+00:00**, after the 09:01:06Z gate and 09:01:52Z plan freeze. By the 2026-11-04T09:07:11.282867+00:00 observation, 35 formal starts across all 20 seeds were present, each tied to the original plan. Consequently, a pre-exposure correction/re-freeze can no longer describe this batch.

The executor recorded `docs/research/secon2027_formal_contract_erratum.md` at **2026-11-04T09:09:21.850292+00:00**, explicitly after exposure. It identifies the stale opening statements, treats the already-frozen formal section as the operative specification, preserves every original identity and excludes any method, population, parameter, statistic or result change. Its SHA-256 is `24cb723f156e45e9ed44b1a9bbfb4f40346dbca8457a22803927216f1f0ea0e4`. The final reproducibility package and manuscript must retain the chronology and cite this notice.

Independent follow-up verified that the original plan, gate, contract and method-decision byte hashes remain unchanged. `results/secon2027/gates/formal-v1/administrative-pause.json` (SHA-256 `84c11038a3f2aa59e46d4129c4b292a7a64a30f5e257a7ba129f6246093f603f`) records **43 completed / 0 failed / 717 unstarted**, with all 20 seeds exposed. All 43 saved completion hashes still match, each key still has only `attempt-001`, and each corresponding resume log reports `verified-existing`. The sampled resume commands bind the original plan, contain no retry flag and only reference planned keys. Resume preserves concurrency 4 and all 760 keys.

**F1 is closed as a transparent administrative erratum.** The immutable contract retains its original text; the correction is documented alongside it rather than rewriting history. No new scientific-boundary issue was found in this follow-up. This closure does not certify incomplete formal outcomes.

## Frozen chain

| Record | Identity / observation |
| --- | --- |
| Gate frozen | 2026-11-04T09:01:06.320060+00:00 |
| Cohort registered | 2026-11-04T09:01:06.320879+00:00 |
| Formal plan frozen | 2026-11-04T09:01:52.961637+00:00 |
| Formal plan logical SHA-256 | `5f1a12fe49bf7fc0ea32cc048a3595ed0bd290811f952a47c5a33b0cded2cbb0` |
| Formal plan file SHA-256 | `e738c34f726718027c46ff832aea8ca1bb095fa1e4a9cb5c8d25f271012e4052` |
| Matrix canonical SHA-256 | `3cc6bab3de7c7767c3fbf845deb156f945db13d98361f0dc5b7bf7e769cc6ea3` |
| Matrix file SHA-256 | `8cc1d79ddb1a91007bd124c1c1fa43f74b667657b024521882dde1fabcd034a0` |
| Formal source snapshot | `63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee` |
| Formal tested version | 2.1.29 |
| Pilot plan logical SHA-256 | `0c49a69a5c3725c9f72ff2e28ed870d10db1df7eec4319f6397097b84a2c85e7` |
| Pilot source snapshot / tested version | `ee890e25030782fc01208ee4ce1f20863c6ade5322ac954ad67ae48b594056a2` / 2.1.28 |

The matrix hash stored in the plan/gate is the canonical JSON digest, not the file-byte digest; their difference is expected. All eight case populations are exact: S1 default/matched 80 each; S2 default 80/matched 140; S3 default 80/matched 140; deadline10 and deadline60 80 each. The deadline30 reference reuses main S2-matched rows. Cases, arms and seeds match the independently inspected candidate; only the measured resource-budget object changed.

The full pilot audit is 72 completed, 0 failed, 0 missing, and its completed key set exactly equals the pilot plan. Saved pilot and formal test records report 161 passed. The formal saved-source command exits 0 against snapshot `63e380…`; its log records 161 passed, 11 warnings in 14.26 s. This reviewer only read these records and did not rerun tests. Gate method, decision and mechanism-report hashes resolve to the expected files, and the formal embedded gate equals the gate file.

## Prospective interpretation and analysis boundaries

- The corrected fixed CPR policy was chosen before formal exposure. Negative S3 pilot results remain explicit; no universal advantage is claimed.
- Every scheduled flow enters the common denominator, and all 20 seeds stay in the population. Missing/incomplete keys block a complete aggregate. Undefined seed quantities propagate to undefined all-seed estimands; successful subsets do not replace the full population.
- The analysis specification separates plan/case/source identities and default/matched regimes. Identical effective CPR/ME configurations are never pooled into n=40.
- Primary endpoints are timely ACK fraction and full physical TX airtime. Statistics use equal-weight seed means, paired fraction differences, mean paired log airtime ratios, 10,000 paired percentile bootstrap resamples and 95% unadjusted descriptive intervals with analysis-only seed 20271104. There is no significance, multiplicity-controlled inference, noninferiority, guaranteed precision or power claim.
- n=20 is a finite descriptive replication budget. No sequential precision stopping or seed replacement is allowed.
- The deadline axis jointly changes deadline, drain and accounting horizon: 240 s generation plus 10/30/60 s gives 250/270/300 s cutoff. Full ToA is charged for frames starting by cutoff. CPR admission deadlines change while other source policies retain their declared behavior. Cross-deadline airtime cannot be attributed only to a timer.
- S1 multihop/cache, S2 actual fault-edge/path intersection, S3 offered-load/contention and physical component exposure criteria limit claims; they never filter seeds or authorize replacement.
- S1/S3 is only a two-point load response. No saturation threshold, calibrated RF, official-firmware equivalence, hardware validation or memory optimization claim follows.

The S3-default CPR pilot has **5, 0, 0 source-state capacity refusals** (`state-capacity-drop`) on development seeds 2027000/1/2, while relay capacity evictions are **0, 0, 0**. These mechanisms must remain separate. Zero relay evictions does not establish an absence of source capacity pressure; peak relay occupancy is unknown.

## Resource and failure boundary

Independently reconstructed pilot totals are 301.925714167 serial wall seconds, 706,194,269 raw bytes and 360,251,392 bytes maximum worker RSS for all 72 runs. Case/arm means reproduce the frozen estimates: 3,314.8214624901243 serial seconds and 7,511,290,148.641974 raw bytes for 760 runs; controls use the corresponding CPR mean and robustness scales by cutoff/270. The ideal four-worker time is 828.7053656225311 seconds. Four times measured RSS is 1,441,005,568 bytes on a 16 GiB host; twice estimated raw storage is 13.990868159834248 GiB under the 18 GiB cap.

These are estimates, not upper bounds. The frozen policy caps concurrency at 4, records 2× reserves and a 4 h envelope, stops new submissions on failure, preserves in-flight/failed evidence, and permits only explicit bounded infrastructure retries (maximum 2 attempts). It does not permit scientific retries or silently shrinking the matrix.

## Scope and remaining work

This review was read-only against the execution tree. It did not run simulations, register seeds, freeze plans, alter execution files or ICC sources, rerun constructor/BFS checks, or repeat the 18 analysis tests. Full machine-readable checks, file hashes, method hashes, pre-exposure evidence and the observed start records are in the companion JSON.

The original pre-exposure seed review at 09:00:43Z found 142 development starts, no formal seed hits, and no overlap with prior cohorts or the historical exclusion namespace. The later formal starts occurred after the recorded method/plan freezes. Live registry/run counts are timestamped observations and are not a final formal audit.

Pending: separately verify the complete 760-run result audit, realized exposure and final analyses. The erratum and same-plan continuation have been verified; no freeze-review issue remains open. This report does not certify formal results or overall P0/P1 completion.

