# Final manuscript numerical-claim review

**Pass within the checked source and numerical scope; no actionable discrepancy found.** This review binds the five TeX files listed below and the formal-v2 figure manifest. It follows the independent complete statistics review. It does not certify the final PDF's page count, visual layout, font embedding, anonymity or publication state.

The machine-readable record is `secon2027_final_paper_claims_review.json`, SHA-256 `239b6b429ffe4f38907e88dcd6316aa1cdb6ac98edfadc6a8bcab7949ec644ae`. It records source hashes, the numerical evidence rows, figure inputs and outputs, check scope and limitations. The original analysis and paper files were read only.

## Numerical claims checked

The abstract, Introduction, Results and Discussion consistently describe the recovery reversal **within the declared matched scenarios**. Full CPR versus no recovery yields +8.32 percentage points of timely ACK in S2, with descriptive 95% interval [4.90, 11.63] and geometric airtime ratio 1.27. In S3 it yields −15.99 points [−19.41, −12.64], with ratio 1.66. The full Results section also retains the corresponding ratio bounds and the opposing destination-delivery behavior. These numbers agree with the independently checked paired seed effects and intervals.

The review checked:

- The three CPR main-case means and all 18 matched primary-model ACK/airtime contrast rows. All default-regime point directions agree with the corresponding matched results, as the text states.
- All six matched S2/S3 component comparisons, including the repeat and ACK-cancellation effects, ratio bounds and the S3 cancellation interval that spans both confirmation-effect directions.
- All 12 matched destination-delivery table cells and their rounded bounds, the S3 full/no-recovery confirmation and delivery values, and their arithmetic mean airtime values.
- The means of seed-level timely-success p95 latencies, unfinished ACK fractions and per-delivery airtime for S1/S2/S3. The text keeps success-only latency distinct from unfinished populations.
- All CPR deadline/drain means, intervals, repeat/recovery counts, zero recovery at 10 s and the 99 decisions specifically labeled `recovery-deadline-infeasible`. The three comparator point means are unchanged across the deadline cases, as stated. The text correctly avoids monotonic improvement and accounts for the changed drain/cutoff.
- The 760-key first-attempt population, 20 seeds per case/arm, retained adverse results, separate default/matched populations, and post-start administrative erratum after 43 completions.

The reported intervals remain descriptive and unadjusted. The reviewed prose makes no multiplicity-controlled significance, noninferiority, measured hardware/energy benefit or official-firmware superiority claim. Contention-aware admission remains a future direction; it is not described as an evaluated new policy.

## Exposure populations and mechanism interpretation

The S2 paragraph uses **85 initial carried-path crossings** as the denominator for 82 physical repeats, 78 recovery starts, 24 timely deliveries, 18 timely ACKs and 61 flows without timely delivery. The same-generation pre-fault ACK evidence and the 23 avoiding-path deliveries/17 ACKs during the fault are supported by the independent supervisor exposure record. Stage associations are distinguished from the separate no-recovery policy comparison.

The next paragraph correctly uses a different population: **159 physical intended-edge transmissions spanning 87 flows**, consisting of 78 initial DATA, 80 repeat DATA and one ACK. Its **4 of 25** pre-fault-initial active flows uses all intended-hop packet kinds. The earlier mechanism report's **86 flows and 3 pre-fault flows** restrict the population to DATA-edge attempts; the paper does not mix those narrower counts with the new denominators. The direct reconstruction in `secon2027_final_statistics_review.json` and the supervisor exposure JSON agree on these definitions.

The S1/S3 routed/flood starts, scheduled counts, repeated/recovery TXs, accepted ACK hop distributions, intended-hop collision and half-duplex counts, six source-state refusals and 52 protocol-no-start requests all match the complete mechanism and supervisor exposure records. Zero relay eviction is explicitly separated from unknown peak occupancy. The prose does not infer exclusive flow-level causation from a receiver-opportunity count or label stale-route rejection as deadline shortage.

## Figure data and provenance

Every row in each figure source CSV matches its original analysis-table row, including means, bounds, sample counts, identities and component-validation metadata:

| Figure source | Checked rows | Original source |
| --- | ---: | --- |
| `main_results_source.csv` | 48 | `summary.csv` |
| `component_effects_source.csv` | 12 | `paired_effects.csv` |
| `robustness_source.csv` | 40 | `summary.csv` |
| `latency_cost_source.csv` | 45 | 24 summary rows and 21 packet/stage cost rows |

All **145 figure-data rows**, all declared input hashes and all **16 output hashes/sizes** in the formal-v2 manifest matched. The output set contains four PDF/SVG/PNG figure families and their four source CSVs. This establishes data linkage and artifact integrity, not visual quality. Final PDF rendering remains a separate check.

## Bound source files

| Manuscript source | SHA-256 at review |
| --- | --- |
| `paper/secon2027/main.tex` | `48d3d1c2ec8f4cbf81cbfb48ff270ed7ed38d4ff1f88bc7294715462325d9b14` |
| `paper/secon2027/introduction.tex` | `95df18ed9765bc7ff9c97c967c0849f6284baf7796ff3c62c8e9a1700083243f` |
| `paper/secon2027/evaluation.tex` | `5937712fcce08e2d10c02f90689518064e4b9a565f2499e5f06b76f6001ff19d` |
| `paper/secon2027/results.tex` | `bdf6253411123237995935b0f3a7780fd7743dc4e75a428d4a4c9786146dff3b` |
| `paper/secon2027/discussion.tex` | `e50f0e968c410f89f78e7361092d0ac896528c654ba76a22e72239e0c666dc92` |

Subsequent numerical or interpretive edits require a new claim check. Layout-only edits should retain a documented relationship to these reviewed sources and the latest exported PDF. The final manuscript, reproducibility package and remote publication still require their own artifact acceptance; a correct numerical narrative is one completed part of that process.
