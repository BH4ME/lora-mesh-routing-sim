# Formal v1 final statistics review

**Pass within the numerical and provenance scope.** This independent review completed on 4 November 2026 after the full 760-run analysis was available. No simulation, experiment audit, original analyzer function or new research seed was run. The companion `secon2027_final_statistics_review.json` preserves input identities, per-run file checks, independent comparison values, the executed checker source and the review environment. Its SHA-256 is `845480e8c9e2c7771e5ddd8ef3cc05ac893e8a7df8e7823679effbb714b45f09`.

This is a statistical acceptance record. It does not certify final paper wording, rendered figure quality, the anonymous PDF, archive publication or overall task completion. Manuscript claims are reviewed separately against stable source files.

## Scope and independent reconstruction

The review verified all **24 declared analysis output files**, including byte counts and SHA-256 values, and the exact output inventory. It found **760 unique planned runs, 38 case/arm populations and all 20 seeds per population**. The exported tables contain 1,330 summary rows, 90 metric contrasts and 1,800 paired seed-effect rows. These represent 30 distinct CPR/comparator cells; the three metrics do not create 90 independent experiments.

For every run, the checker independently read and hashed the original flow, transmission, action, ACK and request JSONL files against their saved manifest: **3,800 event files**. It also checked the run CSV, identity and manifest hashes. Across **18,240 assertions**, it reconstructed 24 per-run quantities, including the scheduled denominator, timestamp-based timely ACK and DATA counts, both reliability fractions, complete physical TX airtime and count, per-delivery airtime, unfinished fractions, successful-flow latency quantiles, physical source repeats/recoveries, ACK cancellation counts, capacity events, canceled requests and queue waiting time. All matched the exported run rows. The largest airtime difference was **1.14 × 10⁻¹³ s**, consistent with summation order.

Of the 35 summary metrics, 21 were reconstructed from these raw inputs in all 38 populations. For the other 14 metrics, this pass verifies aggregation and uncertainty from exported per-run values; S2 fault populations receive the additional independent reconstruction below. This pass did not rescan the full RX ledger, repeat every ACK provenance join or rerun `audit_plan`. The completed frozen-source audit and separate independent raw review cover those broader event-integrity checks. A hash check of the ACK file alone is not presented as a fresh semantic ACK audit.

## Pairing, controls and uncertainty

All 30 comparison cells retain all 20 paired seeds. Each pair has matching scheduled denominators and the recorded traffic, topology, radio, endpoint-pool and environment identities. The six clean controls in S2/S3 matched differ from their CPR reference only in `name` and the intended true-to-false switch: `cancel_on_ack`, `enable_repeat` or `enable_recovery`. The same effective CPR and legacy-ME settings in default/matched cases produce the same checked per-seed scientific quantities; they remain separate cases and are never pooled as n=40.

The independent checker used Python **3.9.6** and NumPy **1.26.4**, matching the observed formal analysis environment (which additionally records Matplotlib **3.7.5**). It derived each case's RNG seed from canonical JSON `[20271104, [plan_sha256, case_id]]`, using the first 16 SHA-256 hexadecimal digits. It generated the prescribed 10,000 PCG64 index resamples, converted each draw into 20 seed-frequency weights, and computed weighted seed means. Bounds came from manually interpolating the sorted bootstrap means at 2.5% and 97.5%; it did not call the analyzer's resampling or quantile functions.

All **1,330 means and intervals** matched, with maximum numerical difference **5.69 × 10⁻¹⁴**. All **1,800 paired effects** and **90 paired means/intervals** matched; the maximum contrast difference was **4.45 × 10⁻¹⁶**. Airtime ratios and interval bounds also matched after exponentiation. Reliability effects are CPR minus comparator per-seed fractions. Airtime is the geometric mean of paired ratios, obtained as `exp(mean(log(A_CPR,s / A_comparator,s)))`; it is not a ratio of pooled arithmetic means.

All **74 undefined summary rows** retain the original n=20 population and blank mean/CI fields. No undefined seed is silently omitted. The intervals remain descriptive and unadjusted. This review establishes neither a powered design nor multiplicity-controlled significance or noninferiority.

A separate supervisor review, `secon2027_supervisor_formal_statistics_review.md/.json`, independently reached the same result using NumPy 2.5.3 and previously verified raw core quantities. Its scope and this pass's additional direct event reads are recorded separately; they are not counted as new experimental replication.

## Checked main-line manuscript quantities

These are evidence checks for the proposed results narrative, not a certification of wording that may still change. Differences are percentage points of timely ACK probability; intervals are unadjusted descriptive 95% intervals.

| Matched comparison: CPR versus no recovery | ACK difference (pp) | Geometric airtime ratio |
| --- | ---: | ---: |
| S2 fault scenario | +8.319 [4.905, 11.634] | 1.269 [1.223, 1.318] |
| S3 high-load scenario | −15.994 [−19.411, −12.643] | 1.665 [1.581, 1.744] |

The S3 timely-DATA difference is +2.865 pp [0.486, 5.155] even though timely source confirmation falls. A narrative should retain that distinction and avoid collapsing DATA and ACK outcomes into one reliability measure. These controlled comparisons characterize the fixed implementation in these scenarios; their sign is not a universal effect of recovery.

The CPR deadline/drain response on S2 matched is:

| Deadline and drain | Timely ACK seed mean | Timely DATA seed mean | Mean TX airtime |
| --- | ---: | ---: | ---: |
| 10 s | 57.013% | 71.511% | 33.224704 s |
| 30 s | 63.960% | 78.452% | 40.551219 s |
| 60 s | 62.737% | 78.037% | 41.046861 s |

The 30 s rows are the existing main S2-matched runs, not another experiment. ACK and DATA point estimates are not monotonic over this axis. The accounting cutoffs are 250, 270 and 300 s, so a change in airtime includes a change in the drain/accounting window. No new across-deadline inferential contrast is introduced.

## Fault exposure: separate populations and denominators

Direct flow/TX reconstruction produced the following counts **within each of S2-default and S2-matched CPR**, using the same 20 seeds separately. Both regimes match the new supervisor exposure review exactly. Identical counts across regimes do not make twice as many independent observations.

| Definition | Count per regime |
| --- | ---: |
| Initial routed DATA source path intersects a fault edge, with the initial physical send during the active fault interval | 85 flows |
| Physically started DATA/ACK/RREP at its intended faulted next hop during the active interval | 159 TX, spanning 87 flows |
| Restrict the preceding flow population to a physical **DATA** attempt on a faulted next hop | 86 flows |
| Initial TX before 80 s and the source flow remains active into the fault window | 25 flows |
| Among those 25, a later fault-edge attempt of any intended-hop packet kind | 4 flows |
| Among those 25, a later fault-edge **DATA** attempt | 3 flows |
| Within the 85 initial-path crossings: timely destination delivery / timely source ACK / no timely destination delivery | 24 / 18 / 61 flows |

An intended edge uses DATA/RREP `path[index+1]` or ACK `path[index]`, joined to the physical transmitter. Fault exposure is evaluated at the physical TX start in the half-open interval [80, 160) s. A source path crossing, a flow-lifetime overlap and an actual attempt on a failed edge are different observations.

The earlier mechanism report's **86** and **3** are the narrower DATA-attempt populations; the corresponding **87** and **4** include all intended-hop packet kinds. The earlier report is preserved rather than rewritten. The 85-crossing outcome proportions must not use 87 or 86 as their denominator. This pass cross-checked the new supervisor report's corresponding definitions and per-regime totals; the JSON retains per-seed flow-ID sets for the reconstructed populations.

## Mechanism and resource cross-checks

For all 760 runs, reconstructed core counts, source actions, cancellation/capacity quantities and queue means matched the complete mechanism report. The absolute difference between each packet-kind/stage airtime partition and the analyzed whole-network airtime was at most **1.14 × 10⁻¹³ s**. Resource totals reconstructed from completion records and actual attempt files also matched:

- Summed worker wall time: **4,423.191694785 s**. This is not four-worker elapsed time.
- Peak single-worker RSS: **398,163,968 bytes**.
- Raw attempt files: **7,098,305,927 bytes**, including **7,052,691,761 bytes** of event JSONL.

Across the complete plan, the records contain 51,145 scheduled flows, 23,836 timely source ACKs, 32,925 timely destination deliveries, 574,959 physical TXs, 8,551 physical source repeats, 7,577 source recoveries, 4,057 successful ACK cancellations and zero capacity evictions. These are inventory totals across all cases, regimes and controls. They include repeated effective settings and are not a pooled performance estimand or an independent sample size. Zero eviction does not establish unused capacity or a memory advantage.

## Frozen identities and limits

| Record | Identity |
| --- | --- |
| Formal logical plan SHA-256 | `5f1a12fe49bf7fc0ea32cc048a3595ed0bd290811f952a47c5a33b0cded2cbb0` |
| Formal saved source | `63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee` |
| Analyzer SHA-256 | `7fd757a780e9725bd3d1992790eaad4a6cc3be7b48f7adcce674a729990eeb54` |
| Original analysis.json SHA-256 | `8ab85b0313dd99b499947b3c481bd16ab96a0ca0418dae522699de7f659156ef` |
| Executed independent checker SHA-256 | `fa39a22d1eed4d6014dd41234b1921c902f98f898e055dfdba5a63d6ff3ef538` |

The companion JSON embeds the exact checker source and records its execution directory, supporting inspection without relying on a temporary script remaining available. The checked output files and original scientific inputs were not changed. The administrative erratum remains post-start; no result here backdates it, changes the frozen method or authorizes new tuning or seed replacement. The final manuscript and reproducibility closeout must preserve these boundaries.
