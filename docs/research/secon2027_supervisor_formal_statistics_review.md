# SECON 2027 formal statistics independent review

Status: **PASS within the numerical/provenance scope; no discrepancy found.** Review time: 2026-11-04T09:58:31.109661+00:00. The execution tree was read only; the original analyzer and simulator were neither imported nor run. Existing independent raw reconstructions were used, rather than re-auditing the full event population.

## Population and numerical findings

The frozen formal plan and analysis contain exactly **760 unique runs**, **38 case/arm groups**, and **20 seeds per group**, with all seed IDs 2027100–2027119 present once in each group. No default/matched pool with n=40 exists. The 30 declared CPR/comparator combinations yield **90 metric contrasts** and **1,800 seed-level effect rows**: 24 baseline combinations and six clean-control combinations, each for timely ACK, timely destination delivery and physical airtime.

For every run, independent verified raw values reproduce the exported scheduled N, timely ACK count, timely destination-delivery count, physical TX count and full airtime. Fractions, unfinished proportions and airtime per timely delivery were independently derived from those quantities. All identity fields and the exact run-key population match the plan. Count differences are exactly zero; the largest floating difference is **1.0232×10⁻¹¹**, consistent with numeric summation/serialization differences, well within the stated 10⁻⁹ absolute plus 10⁻¹² relative tolerance.

All **1,330 summary rows (38×35 metrics)** have the expected mean, n, undefined count, status and independently reconstructed 95% bootstrap bounds. Of these, **266 rows across seven metrics** use values independently derived from the saved raw review: timely ACK fraction, timely destination-delivery fraction, full airtime, physical TX count, airtime per timely delivery and both unfinished fractions. For the remaining 28 metrics, this review verifies aggregation and uncertainty from the exported per-run values; it does not claim to independently reconstruct every latency/diagnostic metric from event logs again.

All **1,800 exported paired seed effects** match independent values from the verified raw review. Timely ACK and delivery effects are CPR minus comparator, preserving exact seed pairing. All **90 paired means and intervals** match, including **30 geometric airtime ratios and their bounds**. The largest contrast-bound discrepancy is 5.72×10⁻¹⁴ and the largest exponentiated-ratio discrepancy is 8.44×10⁻¹⁴. These are descriptive effects, without significance, noninferiority or multiplicity-controlled conclusions.

## Independent resampling reconstruction

The frozen fields are unit=seed, analysis-only seed **20271104**, **10,000 resamples**, n=20, and a **95% unadjusted descriptive percentile interval**. The simulator seeds are not used as an analysis RNG. For each case, the scoped RNG seed is the first eight SHA-256 bytes, interpreted big-endian, of canonical JSON `[20271104, [plan_sha256, case_id]]`.

The checker generated the prescribed integer draws with `Generator(PCG64(scoped_seed))`, converted each resample into a 20-column seed-frequency vector, and multiplied those counts by each metric's values to obtain resample means. Point means use `math.fsum(values)/20`. It sorted bootstrap means and manually linearly interpolated positions `0.025×9999` and `0.975×9999`; it did not call the original analyzer's bootstrap or quantile functions. The same case draw set was applied across arms and metrics, as frozen. NumPy 2.5.3 was used for independent verification; the original analysis records NumPy 1.26.4.

For airtime, the individual effect is `log(A_CPR,s / A_comparator,s)`. The checker averages and bootstraps those paired log effects, then exponentiates the point and bounds. This verifies the **geometric mean of paired ratios**, not the ratio of pooled arithmetic means. Reliability effects are directly paired differences of per-seed fractions. Default/matched cases remain separate; their deterministic bootstrap draws are scoped by case ID, even when effective CPR inputs and point values coincide.

## Undefined values remain in the population

Exactly **74 summary rows are undefined**, and all have **n=20, undefined_n=20**, with blank mean/CI fields and `undefined-all-seed-estimand` status:

| Metric | Undefined case/arm summary rows |
| --- | ---: |
| ACK cancellation successes / decoded ACK checks | 26 |
| Initial routed-flow count | 24 |
| Initial flood-flow count | 24 |

The companion JSON retains every affected case/arm/metric and its seed IDs. No selected subset is used to construct a mean or interval. There are no zero-timely-delivery runs or nonpositive-airtime inputs in the actual reviewed primary data, and no partially undefined summary population occurs here. This review therefore does not claim a new stress test of those unobserved edge cases.

## Provenance and output integrity

A separate read-only provenance check found:

- Analysis, plan and verified raw audit have identical 760-key populations, with no failed or missing key.
- All **760 completion hashes** match the analysis record, independently verified raw summary and current completion files; all **760 manifest hashes** match `runs.csv`, completion evidence and current files.
- All **24 declared output files** match SHA-256 and byte size (31,511,118 bytes total). The six PDF and six SVG outputs exist. All 11 declared table row counts match, and `planned_runs.csv` has 760 rows.
- Analyzer and orchestration source fingerprints match the saved formal snapshot. The frozen statistics, tested version, source and contract identities match. `analysis.json`'s `created_at` is the analysis start time, which precedes its internal audit completion as implemented.

| Record | SHA-256 / identity |
| --- | --- |
| Frozen plan logical hash | `5f1a12fe49bf7fc0ea32cc048a3595ed0bd290811f952a47c5a33b0cded2cbb0` |
| Frozen source snapshot | `63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee` |
| Frozen contract | `0db4fc2e724f441e190693e3f8d37b7912e2d4baa5555515c6f132481f309eff` |
| Analyzer | `7fd757a780e9725bd3d1992790eaad4a6cc3be7b48f7adcce674a729990eeb54` |
| analysis.json | `8ab85b0313dd99b499947b3c481bd16ab96a0ca0418dae522699de7f659156ef` |
| Verified independent raw review | `9dadbb649d49e3d62b6a8ba556a21f00cbd36407a4b430d92d6ce6733685907a` |
| runs.csv | `95e8f0cfded9eedd2c3235e5a2e3f092ff768161bfa3cc24bdb69540b36da425` |
| summary.csv | `748639f4a1559dbd1a922d53e93bc2717882e927386d5ee40c6c1e8d73cff639` |
| paired_effects.csv | `30323f08da14bef59b8c2e78b52dd27de74f3719a1028e691c07bfdf47c34aa3` |
| paired_seed_effects.csv | `7a2198f566b5541c6a50b935f64646b2362c218ce30b5079979792400dbb01e7` |

The machine-readable review contains all independently recalculated summary values, paired effects, group seed populations, scoped RNG seeds, numeric error maxima and check counts. It uses `secon2027_supervisor_formal_raw_review_verified.json`; the earlier full-raw checker's accepted-ACK false positives remain documented separately and are not treated as experiment defects.

This result verifies formal analysis numbers and recorded provenance. It does not certify figure visual quality, final manuscript claims, anonymous-PDF layout, remote publication state or overall project completion. No execution-tree artifact or scientific setting was modified.
