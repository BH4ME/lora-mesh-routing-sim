# SECON frozen statistical specification review

Reviewed 2026-11-04T09:11:16.595155+00:00. Read-only source review; no performance results or additional simulation used.

- Plan `5f1a12fe49bf7fc0ea32cc048a3595ed0bd290811f952a47c5a33b0cded2cbb0`; snapshot `63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee`; analyzer SHA-256 `7fd757a780e9725bd3d1992790eaad4a6cc3be7b48f7adcce674a729990eeb54`. Current analyzer is identical to this frozen file.
- `aggregate_runs` groups by plan, case and arm, requires every planned seed once, and sorts seeds before estimation. Default/matched cases remain separate; equal configurations do not become n=40.
- `summarize_run` uses all scheduled flow records in each seed's denominator and requires physical-event ledger agreement. Zero timely deliveries yield null airtime-per-delivery. Successful-flow latency is conditional on success; unfinished fractions are separately retained.
- `paired_effect` aligns exact seed IDs and computes per-seed CPR minus comparator for reliability, and log(CPR airtime/comparator airtime) for cost. `bootstrap_mean` resamples these paired effects, not independent arm samples. Reported `ratio_mean` is exp(mean(log ratio)), a geometric mean ratio; it must not be labeled ratio-of-arithmetic-means.
- 10,000 resamples, equal-weight per-seed means and linear percentile bounds at .025/.975 match the frozen descriptive specification. RNG derives from analysis seed + plan + case hash, independent of simulation seeds. Intervals are explicitly unadjusted/descriptive; no confirmatory significance claim follows from them.
- Any undefined seed leaves the all-seed mean/interval undefined and records its count. Nonpositive airtime produces an explicit undefined log ratio rather than dropping that seed.
- Pairing checks traffic, topology, radio, endpoint-pool and environment identities. Clean component comparisons require resolved parameters to differ only in name and the declared toggle; otherwise they remain mixed-policy comparisons rather than clean ablations.
- Existing focused tests cover fixed paired log ratios, undefined inputs, missing/duplicate seeds, zero-success costs, component isolation and case identities. These tests were included in the 161-test frozen gate; this review did not repeat the passed suite.

No new mathematical/estimand mismatch found. Final tables/figures and paper still require numeric validation against completed formal data. Note that per-arm CI bars and paired-effect CIs answer different questions; overlapping arm bars do not determine a paired-effect conclusion. Latency CDF pools timely successful flows descriptively, while primary estimands remain seed-weighted.
