# SECON 2027 formal evaluation: complete frozen cohort

The fixed CPR policy exhibits a scenario-dependent confirmation–airtime trade-off. In S2 matched, CPR minus legacy MeshEcho is **+9.28 percentage points (pp)** timely ACK [4.42, 14.00] with a **1.604** geometric airtime ratio [1.501, 1.723]. Under S3 load, the same comparison is **−9.26 pp** [−14.13, −4.54] with **2.134** airtime [2.046, 2.236]. Relative to the S3 no-recovery control, full CPR has **−15.99 pp** timely ACK [−19.41, −12.64] and **1.665** airtime [1.581, 1.744]. These are complete-cohort descriptive results, including adverse outcomes; they do not support universal reliability or efficiency improvement.

## Population, freeze and audit boundary

The one frozen formal plan is `results/secon2027/plans/formal-v1.json`, logical SHA-256 `5f1a12fe49bf7fc0ea32cc048a3595ed0bd290811f952a47c5a33b0cded2cbb0`. Its source snapshot is `63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee`, tested version **2.1.29**, and frozen contract SHA-256 `0db4fc2e724f441e190693e3f8d37b7912e2d4baa5555515c6f132481f309eff`. All **760/760 runs completed; zero failed or missing keys**. Each of 38 case/arm populations retains all 20 predeclared seeds **2027100–2027119**.

| Frozen population | Runs | Scope |
| --- | ---: | --- |
| Main comparisons | 480 | S1/S2/S3 × default/matched × four models × 20 seeds |
| Clean controls | 120 | noackcancel/norepeat/norecovery × S2/S3 matched × 20 seeds |
| Deadline robustness | 160 | 10/60 s × four models × 20 seeds, S2 matched |
| Complete formal plan | 760 | 38 case/arm populations; no seed replacement or outcome selection |

S1 is the fault-free 8-flow/min condition; S2 uses the same offered rate with 80 dB added attenuation on edges 7–8 and 12–13 during [80,160) s; S3 is fault-free at 40 flows/min. The fixed environment is a 4×5 obstructed grid, 20 nodes, four directed endpoint pairs, 240 s of traffic generation and a six-hop limit. The main deadline is 30 s. Default and matched are separately declared configurations; matching selected forwarding-delay/cache parameters does not make behavioral protocol models equivalent to official firmware. Baseline fidelity and exclusions are in `docs/research/secon2027_baseline_fidelity.md`.

The administrative sequence is explicitly **post-start**: development gate 09:01:06 UTC, plan freeze 09:01:52 UTC, first formal start 09:06:36 UTC, and erratum 09:09:21 UTC on 2026-11-04. Dispatch paused after 43 completed runs, zero failed runs and 717 unstarted keys, with all 20 seeds exposed. The erratum documented the stale development-only opening of a contract whose later formal-freeze section was already operative. It did not rewrite the frozen bytes or change scientific settings. The same plan resumed by verifying/skipping the 43 completed keys and running the remaining 717. No partial performance summary or parameter selection occurred during that pause. See `docs/research/secon2027_formal_contract_erratum.md` and `results/secon2027/gates/formal-v1/administrative-pause.json`; this correction is not described as pre-exposure.

The completed-plan audit is `results/secon2027/gates/formal-v1/audit.json`. The independent verified raw review is `docs/research/secon2027_supervisor_formal_raw_review_verified.json`; its separately preserved initial ACK-count checker flags were corrected as checker interpretation errors, not experiment defects. The independent final statistics review, `docs/research/secon2027_supervisor_formal_statistics_review.md` and `.json`, reproduced all 1,330 summary rows, 90 paired metric contrasts and 1,800 seed-level effects. It verified the 760 completion/manifest bindings and all 24 declared analysis output hashes. Its raw-derived check covers the primary outcome/cost quantities; remaining diagnostic metrics were checked by aggregating exported per-run values, without a new raw reconstruction of every latency metric.

## Estimands and uncertainty

Every scheduled flow remains in the timely-ACK and timely-DATA denominator, including source refusal, no-start, unfinished and unsuccessful flows. ACK receipt and destination delivery are distinct outcomes. Physical airtime sums each distinct started full frame, including ACKs, flooding, discovery and duplicates; a frame starting within the cutoff is charged in full. Requests, canceled reservations and future unsent frames are not physical transmissions.

All means give equal weight to seeds. Reliability contrasts are CPR minus comparator per-seed fractions, reported in pp. Airtime contrasts are **exp(mean(log(A_CPR,s/A_comparator,s)))**, the geometric mean of paired ratios, not the ratio of arithmetic means. Intervals use the frozen **10,000 paired percentile bootstrap resamples**, analysis seed **20271104**, with deterministic case-scoped RNG draws. Every interval below is an **unadjusted descriptive 95% CI**; no significance, equivalence, noninferiority or multiplicity-controlled claim is made. Intervals overlapping zero or one are retained. Default/matched cases remain separate n=20 populations even where CPR's effective inputs and scientific records coincide; case-scoped bootstrap draws can yield slightly different bounds for equal point estimates.

There are 30 declared CPR/comparator cells: 18 main, six clean-control and six additional deadline comparisons, producing 90 metric rows and 600 distinct seed pairs (1,800 metric-pair rows). No undefined seed is removed. All paired quantities and the latency/airtime-per-delivery quantities displayed here are defined for all 20 seeds. The 74 undefined summary rows are retained as n=20/undefined_n=20 with blank means/intervals: 26 ACK-cancellation-per-decoded-check rows, 24 initial-routed counts and 24 initial-flood counts. Undefined diagnostics are not replaced by zero. There are no zero-timely-delivery runs or nonpositive airtime inputs in this cohort; this observation is not a stress test of absent edge cases.

## Main results: all arms and paired effects

`CPR`, `ME`, `MT` and `MC` denote MeshEcho-CPR, legacy MeshEcho, the Meshtastic behavioral model and the MeshCore behavioral model. In a matched case these labels select the corresponding `-matched` arm IDs. Tables show saved analyzer values rounded only for display. Arm means are not pooled flow fractions.

| Case | Arm | Timely ACK % [95% CI] | Timely DATA % [95% CI] | Full airtime s [95% CI] |
| --- | --- | ---: | ---: | ---: |
| S1-default | CPR | 81.30 [75.36, 86.74] | 94.97 [92.11, 97.19] | 33.79 [30.34, 37.33] |
| S1-default | ME | 77.31 [72.91, 81.61] | 80.10 [76.05, 84.02] | 28.83 [26.62, 30.95] |
| S1-default | MT | 58.53 [55.23, 62.04] | 88.34 [85.94, 90.72] | 44.05 [41.13, 46.84] |
| S1-default | MC | 69.10 [64.31, 73.54] | 74.58 [70.45, 78.45] | 25.73 [23.97, 27.41] |
| S1-matched | CPR | 81.30 [75.33, 86.63] | 94.97 [92.10, 97.15] | 33.79 [30.36, 37.39] |
| S1-matched | ME | 77.31 [72.88, 81.66] | 80.10 [76.02, 84.06] | 28.83 [26.67, 30.94] |
| S1-matched | MT | 55.31 [50.38, 60.39] | 89.09 [85.79, 92.02] | 44.19 [41.53, 46.81] |
| S1-matched | MC | 68.03 [63.50, 72.70] | 72.78 [68.27, 77.41] | 24.94 [23.25, 26.69] |
| S2-default | CPR | 63.96 [59.24, 68.55] | 78.45 [75.71, 81.28] | 40.55 [37.91, 43.28] |
| S2-default | ME | 54.68 [50.83, 58.80] | 56.78 [52.63, 61.18] | 25.52 [23.27, 27.71] |
| S2-default | MT | 47.98 [44.06, 52.10] | 71.74 [67.84, 75.19] | 41.38 [38.70, 43.87] |
| S2-default | MC | 45.74 [41.98, 49.55] | 49.01 [45.51, 52.59] | 22.80 [21.00, 24.60] |
| S2-matched | CPR | 63.96 [59.15, 68.57] | 78.45 [75.68, 81.19] | 40.55 [37.96, 43.28] |
| S2-matched | ME | 54.68 [50.81, 58.86] | 56.78 [52.60, 61.11] | 25.52 [23.28, 27.68] |
| S2-matched | MT | 48.47 [45.63, 51.45] | 75.61 [72.39, 78.78] | 42.62 [39.96, 45.27] |
| S2-matched | MC | 45.55 [42.26, 48.99] | 48.73 [45.25, 52.49] | 22.57 [20.62, 24.68] |
| S3-default | CPR | 38.94 [35.00, 42.88] | 67.81 [65.22, 70.24] | 207.07 [200.53, 213.49] |
| S3-default | ME | 48.20 [44.81, 51.53] | 53.29 [50.22, 56.32] | 97.34 [92.74, 101.67] |
| S3-default | MT | 23.19 [21.34, 25.11] | 61.50 [59.78, 63.19] | 185.76 [181.03, 190.24] |
| S3-default | MC | 48.73 [45.71, 52.07] | 53.44 [50.48, 56.70] | 91.18 [85.60, 97.35] |
| S3-matched | CPR | 38.94 [35.11, 42.93] | 67.81 [65.33, 70.24] | 207.07 [200.34, 213.60] |
| S3-matched | ME | 48.20 [44.81, 51.54] | 53.29 [50.27, 56.31] | 97.34 [92.82, 101.56] |
| S3-matched | MT | 23.19 [21.72, 24.60] | 61.37 [59.98, 62.71] | 186.10 [181.33, 191.00] |
| S3-matched | MC | 47.98 [44.91, 51.09] | 53.39 [50.39, 56.27] | 91.40 [84.97, 98.03] |

The following 18 main comparisons retain all three comparators in both regimes. Positive reliability differences favor CPR; airtime below one denotes lower CPR physical airtime.

| Case | Comparator | n | ACK difference pp [95% CI] | DATA difference pp [95% CI] | Airtime ratio [95% CI] |
| --- | --- | ---: | ---: | ---: | ---: |
| S1-default | ME | 20 | 3.99 [-1.52, 9.17] | 14.86 [11.25, 18.66] | 1.157 [1.053, 1.268] |
| S1-default | MT | 20 | 22.77 [16.22, 28.69] | 6.63 [2.91, 10.06] | 0.754 [0.702, 0.807] |
| S1-default | MC | 20 | 12.20 [6.11, 18.17] | 20.39 [16.89, 24.49] | 1.293 [1.168, 1.433] |
| S1-matched | ME | 20 | 3.99 [-1.61, 9.08] | 14.86 [11.21, 18.76] | 1.157 [1.056, 1.269] |
| S1-matched | MT | 20 | 25.99 [18.51, 33.31] | 5.88 [2.61, 8.98] | 0.751 [0.696, 0.807] |
| S1-matched | MC | 20 | 13.27 [8.04, 18.43] | 22.19 [18.25, 26.08] | 1.334 [1.204, 1.474] |
| S2-default | ME | 20 | 9.28 [4.50, 13.98] | 21.68 [17.77, 25.44] | 1.604 [1.497, 1.723] |
| S2-default | MT | 20 | 15.98 [10.15, 21.39] | 6.71 [3.41, 10.44] | 0.979 [0.938, 1.020] |
| S2-default | MC | 20 | 18.22 [12.76, 23.36] | 29.45 [25.25, 33.31] | 1.789 [1.649, 1.939] |
| S2-matched | ME | 20 | 9.28 [4.42, 14.00] | 21.68 [17.79, 25.50] | 1.604 [1.501, 1.723] |
| S2-matched | MT | 20 | 15.49 [10.26, 20.74] | 2.84 [-0.89, 6.78] | 0.951 [0.915, 0.989] |
| S2-matched | MC | 20 | 18.41 [14.50, 22.33] | 29.72 [27.02, 32.49] | 1.813 [1.687, 1.951] |
| S3-default | ME | 20 | -9.26 [-14.11, -4.48] | 14.52 [11.42, 17.68] | 2.134 [2.045, 2.239] |
| S3-default | MT | 20 | 15.75 [11.96, 19.51] | 6.31 [3.94, 8.65] | 1.114 [1.094, 1.133] |
| S3-default | MC | 20 | -9.79 [-13.65, -5.64] | 14.37 [11.70, 17.09] | 2.289 [2.143, 2.444] |
| S3-matched | ME | 20 | -9.26 [-14.13, -4.54] | 14.52 [11.38, 17.66] | 2.134 [2.046, 2.236] |
| S3-matched | MT | 20 | 15.75 [12.25, 19.51] | 6.43 [4.35, 8.54] | 1.112 [1.088, 1.134] |
| S3-matched | MC | 20 | -9.04 [-12.62, -4.88] | 14.42 [12.00, 17.12] | 2.290 [2.121, 2.460] |

S1 has higher mean timely ACK than each comparator, but the CPR–ME ACK interval crosses zero in both regimes; its airtime ratio to ME exceeds one. In S2, the CPR–MT delivery interval crosses zero for matched settings, and the default airtime interval includes one. In S3, CPR delivers more DATA on average than each main comparator but confirms fewer messages than ME and MC while using more airtime than all three models. A delivery-only narrative would conceal this confirmation and cost loss.

## All clean component controls

Each control keeps the other resolved parameters equal and changes only its declared component/name fields. `noackcancel` disables decoded-ACK cancellation while retaining capacity policy; `norepeat` retains the reserved observation slot without an actual repeat; `norecovery` prevents recovery requests/starts while retaining repeat. These are the frozen controls, not the historical broader `nocancel` policy. Every reference seed has nonzero activity of the component being disabled; all disabled-component event counts are zero. See `prospective-criteria-and-comparisons.json` and `secon2027_formal_mechanisms.md` for the full isolation/exposure gate evidence.

| Case | Arm | Timely ACK % [95% CI] | Timely DATA % [95% CI] | Full airtime s [95% CI] |
| --- | --- | ---: | ---: | ---: |
| S2-matched | noackcancel | 61.76 [56.77, 66.64] | 78.03 [74.99, 80.83] | 41.86 [39.27, 44.53] |
| S2-matched | norepeat | 59.61 [54.36, 64.86] | 78.11 [74.80, 81.32] | 39.25 [36.69, 41.75] |
| S2-matched | norecovery | 55.64 [50.03, 60.90] | 69.51 [65.61, 73.22] | 31.89 [30.00, 33.65] |
| S3-matched | noackcancel | 40.23 [36.15, 44.45] | 69.52 [67.04, 72.03] | 214.26 [205.45, 222.88] |
| S3-matched | norepeat | 33.51 [30.14, 36.93] | 64.50 [62.20, 66.81] | 191.65 [185.12, 197.86] |
| S3-matched | norecovery | 54.93 [51.03, 58.61] | 64.94 [61.86, 67.92] | 125.21 [117.82, 132.86] |

| Case | Comparator | n | ACK difference pp [95% CI] | DATA difference pp [95% CI] | Airtime ratio [95% CI] |
| --- | --- | ---: | ---: | ---: | ---: |
| S2-matched | noackcancel | 20 | 2.20 [0.36, 4.38] | 0.42 [-0.61, 1.39] | 0.968 [0.950, 0.986] |
| S2-matched | norepeat | 20 | 4.35 [1.48, 7.51] | 0.34 [-1.48, 2.30] | 1.033 [1.007, 1.060] |
| S2-matched | norecovery | 20 | 8.32 [4.90, 11.63] | 8.94 [6.04, 11.85] | 1.269 [1.223, 1.318] |
| S3-matched | noackcancel | 20 | -1.29 [-5.99, 3.38] | -1.71 [-3.72, 0.32] | 0.968 [0.942, 0.995] |
| S3-matched | norepeat | 20 | 5.43 [2.23, 9.01] | 3.30 [1.18, 5.58] | 1.081 [1.051, 1.110] |
| S3-matched | norecovery | 20 | -15.99 [-19.41, -12.64] | 2.86 [0.49, 5.15] | 1.665 [1.581, 1.744] |

The S2 recovery comparison raises mean confirmation and delivery at an airtime ratio of 1.269. In S3, full CPR versus no-recovery instead lowers timely ACK by 15.99 pp while increasing delivery by 2.86 pp and airtime by a factor of 1.665. Full CPR versus noackcancel has negative S3 ACK and DATA point differences (−1.29 and −1.71 pp); their intervals include zero, while the airtime ratio is 0.968. The repeat comparisons have higher mean ACK and airtime in both S2 and S3. These results constrain the claimed benefit of each component; observed component use alone does not establish improvement. Successful cancellation counts cannot be multiplied by nominal frame duration to estimate net causal airtime saving.

## Complete finite robustness results

The two added deadline settings retain all models and all 20 seeds. The 30 s condition is the existing S2-matched main population, not an extra independent batch. Therefore the deadline-response display contains 240 run rows (10/30/60 s × four arms × 20 seeds) but adds only 160 runs to the formal plan.

| Case | Arm | Timely ACK % [95% CI] | Timely DATA % [95% CI] | Full airtime s [95% CI] |
| --- | --- | ---: | ---: | ---: |
| R-deadline-10-S2-matched | CPR | 57.01 [51.75, 61.85] | 71.51 [68.21, 74.56] | 33.22 [31.18, 35.20] |
| R-deadline-10-S2-matched | ME | 54.68 [50.78, 58.80] | 56.78 [52.63, 61.16] | 25.52 [23.29, 27.61] |
| R-deadline-10-S2-matched | MT | 48.47 [45.67, 51.45] | 75.61 [72.41, 78.75] | 42.62 [39.90, 45.19] |
| R-deadline-10-S2-matched | MC | 45.55 [42.20, 49.06] | 48.73 [45.28, 52.56] | 22.57 [20.61, 24.72] |
| R-deadline-60-S2-matched | CPR | 62.74 [57.32, 67.93] | 78.04 [74.84, 81.08] | 41.05 [38.00, 44.08] |
| R-deadline-60-S2-matched | ME | 54.68 [50.91, 58.77] | 56.78 [52.69, 61.11] | 25.52 [23.32, 27.70] |
| R-deadline-60-S2-matched | MT | 48.47 [45.73, 51.42] | 75.61 [72.44, 78.80] | 42.62 [39.92, 45.27] |
| R-deadline-60-S2-matched | MC | 45.55 [42.20, 49.05] | 48.73 [45.28, 52.44] | 22.57 [20.62, 24.74] |

| Case | Comparator | n | ACK difference pp [95% CI] | DATA difference pp [95% CI] | Airtime ratio [95% CI] |
| --- | --- | ---: | ---: | ---: | ---: |
| R-deadline-10-S2-matched | ME | 20 | 2.34 [-2.68, 7.03] | 14.73 [11.21, 18.05] | 1.316 [1.238, 1.402] |
| R-deadline-10-S2-matched | MT | 20 | 8.54 [4.07, 12.90] | -4.10 [-8.13, -0.19] | 0.780 [0.754, 0.806] |
| R-deadline-10-S2-matched | MC | 20 | 11.47 [7.36, 15.50] | 22.78 [19.58, 26.18] | 1.487 [1.398, 1.574] |
| R-deadline-60-S2-matched | ME | 20 | 8.06 [2.61, 13.46] | 21.26 [16.74, 25.60] | 1.619 [1.515, 1.727] |
| R-deadline-60-S2-matched | MT | 20 | 14.26 [8.12, 20.38] | 2.43 [-1.46, 6.51] | 0.959 [0.926, 0.992] |
| R-deadline-60-S2-matched | MC | 20 | 17.19 [12.75, 21.77] | 29.30 [26.12, 32.58] | 1.830 [1.692, 1.966] |

At 10 s, CPR has **zero physical recovery starts**; its timely DATA difference versus MT is **−4.10 pp [−8.13, −0.19]**, retained alongside its higher ACK point estimate. Within the narrower DATA-attempt fault-exposed subset, 54 flows yield zero timely ACKs, one timely DATA-only outcome and 53 without timely DATA. This subset is not the full 648-flow denominator and is not the broader all-kind exposure population described below. At 60 s the full CPR population contains 188 recoveries; increasing the allowed deadline does not establish monotonic confirmation improvement in these observations.

Deadline and drain change together: accounting cutoffs are 250, 270 and 300 s for deadlines 10, 30 and 60 s. Airtime differences across this axis include tail-accounting exposure and cannot be attributed only to local timing. No unregistered across-deadline inferential contrast is added. The predeclared matched load display joins only the observed fault-free 8 and 40 flows/min points (S1 and S3), with each arm's full 20 seeds. Two points are not a fitted response curve, a threshold estimate or evidence about unseen loads.

## Mechanism exposure, with explicit population definitions

The frozen scene gates and six component isolation/exposure gates all pass. These are interpretation gates, not evidence filters or performance success tests. The unchanged original diagnostic report is `docs/results/secon2027_formal_mechanisms.md` (SHA-256 `2aa78f87bd03ec297931663c8b3328a468519643598009c9cdf5081faf777441`). The later supervisor extraction, `docs/research/secon2027_supervisor_formal_exposure_review.md` and `.json`, provides the broader S2 sets and independently reconstructed physical forward/ACK chains. Its definitions supplement the original report; its populations must not silently replace the narrower original DATA-attempt subset.

For **each** S2 regime separately, all 648 scheduled flows remain in the primary denominator; 193 were enqueued during the fault and 218 have lifetimes overlapping it. Exposure requires an actual TX start in [80,160), not overlap alone. DATA/RREP designate `path[index+1]` and ACK designates `path[index]`; physical TX and intended receiver RX are joined by TX ID and receiver. Initial-path crossings additionally require an initial routed source send during the fault whose carried full path contains a faulted undirected edge.

| S2 CPR population, per regime | Flows | Repeat / recovery | Timely DATA | Timely ACK | DATA-only | No timely DATA |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| All scheduled flows | 648 | 182 / 142 | 508 | 415 | 93 | 140 |
| Initial routed path crosses an active fault | 85 | 82 / 78 | 24 | 18 | 6 | 61 |
| Any-kind actual intended fault-edge attempt | 87 | 84 / 80 | 26 | 19 | 7 | 61 |
| DATA-attempt-only subset in original mechanism report | 86 | See original per-flow data | 25 | 19 | 6 | 61 |
| Union of initial-path and any-kind actual-attempt sets | 89 | 85 / 81 | 26 | 19 | 7 | 63 |

All 85 initial-path crossings have a prior accepted ACK before 80 s on the same path **and route generation**. All 20 seeds have at least one initial-path crossing and one physical blocked-edge attempt. The initial-path set and all-kind attempt set intersect in 83 flows, with union 89. The 159 actual fault-edge transmissions are **78 initial DATA + 80 repeat DATA + one initial-stage ACK**. None is decoded at its designated receiver: 130 PRR failures, 27 capture-collision outcomes and two half-duplex outcomes. Those RX labels do not establish exclusive fault causation.

Among 25 fault-active flows with initial TX before 80 s, **four** later make any-kind fault-edge attempts. The unchanged original report's **three** counts only DATA-attempt-exposed flows, just as its **86** flow count is narrower than 87. Its adjacent **159 TX** count includes all kinds. No outside-start frame merely overlaps the fault in these runs. These differences reflect explicit membership rules, not a changed simulation or dropped flow.

All 24 timely first deliveries and 18 timely ACKs in the 85-path subset are associated with recovery marker 2. Of these, 23 first deliveries and 17 ACKs occur during the active fault along paths avoiding the blocked edges. In the broader 87-attempt subset, two first deliveries use the initial stage and one of those flows later starts recovery. Thus an ACK-lost flow can already have delivered without supplying a delivery oracle to the source. The supervisor report reconstructs 90 successful forward chains and 38 reverse-ACK chains across the two regimes, with no reconstruction failure. Associations with recovery do not substitute for the paired no-recovery comparison.

An illustrative success selected by first qualifying seed/flow order is seed 2027100, flow 15, run `ffbd30cbc519bed7a13a60d4203dcaeb2a2af14a917e7d684acdf65054c3cbae`: initial and repeated 7→8 attempts at 107.304356 and 108.632628 s fail; recovery starts at 109.622212 s on 10→11→12→17→18→13→14, DATA arrives at 114.622223 s and the ACK at 115.023119 s before deadline 136.965668 s. The retained cross-boundary failure is seed 2027106, flow 15: initial at 79.520476 s, repeated blocked edge at 81.187436 s, recovery at 82.177020 s, and no destination delivery or accepted ACK. Both examples are trace explanations, not seed-selection criteria. Offline six-hop alternatives describe structural feasibility, not realized RF success.

For S1/S3, the companion `secon2027_supervisor_formal_s1_s3_exposure.json` retains all 80 primary CPR run records. The following are sums over 20 seeds in each regime; duplicate default/matched records do not create n=40.

| CPR diagnostic, per regime | S1 | S3 |
| --- | ---: | ---: |
| Scheduled flows | 648 | 3,059 |
| Timely DATA+ACK / DATA-only / no timely DATA | 526 / 88 / 34 | 1,181 / 884 / 994 |
| Routed / cold / other initial outcomes | 480 / 168 / 0 | 2,445 / 608 / 6 |
| Accepted 4-hop / 6-hop ACKs | 440 / 86 | 703 / 478 |
| Physical source repeat / recovery | 135 / 91 | 1,890 / 1,597 |
| Intended capture-collision / half-duplex RX opportunities | 227 / 35 | 3,228 / 887 |
| Successful ACK cancellations | 205 | 685 |
| Source-state capacity refusals | 0 | 6 |
| Relay evictions / pending capacity cancellations | 0 / 0 | 0 / 0 |
| Protocol-no-start requests | 2 | 52 |
| Mean seed queue wait / mean seed queue-wait p95, s | 0.254951 / 0.991642 | 0.345067 / 1.033965 |

Every S3 seed has more scheduled flows than its paired S1 seed (ratios 3.857–6.167). S3's six source-state refusals occur in seeds 2027105 and 2027111 (three each) and remain in the scheduled denominator. They are distinct from relay eviction. Correlated RX opportunities do not count independent packets or application failures. The observations show contention exposure, but do not establish queue saturation or a dominant deadline-expiry cause. Exact relay-ledger peak occupancy is unobserved; zero eviction does not prove occupancy stayed below eight. `DROP_DEADLINE_INFEASIBLE` with reason `stale-route-generation` denotes stale-route rejection, not proof of insufficient deadline slack.

## Latency, unfinished outcomes and physical cost

The table below retains all 38 case/arm populations. Latencies are **means of per-seed p95 among timely successes**, not all-flow percentiles or deadline guarantees. Each success-conditioned statistic is accompanied by its full-denominator unfinished fraction. Saved unadjusted intervals for these secondary quantities remain in `summary.csv`; no new paired latency hypothesis test is introduced. Airtime per timely delivery is the equal-seed mean of each seed's full physical airtime divided by its timely DATA count.

| Case | Arm | ACK p95 s / unfinished ACK % | DATA p95 s / unfinished DATA % | Airtime / timely DATA, s |
| --- | --- | ---: | ---: | ---: |
| S1-default | CPR | 4.652 / 18.70 | 4.230 / 5.03 | 1.105 |
| S1-default | ME | 5.508 / 22.69 | 5.525 / 19.90 | 1.125 |
| S1-default | MT | 6.656 / 41.47 | 6.443 / 11.66 | 1.542 |
| S1-default | MC | 2.264 / 30.90 | 2.923 / 25.42 | 1.080 |
| S1-matched | CPR | 4.652 / 18.70 | 4.230 / 5.03 | 1.105 |
| S1-matched | ME | 5.508 / 22.69 | 5.525 / 19.90 | 1.125 |
| S1-matched | MT | 4.945 / 44.69 | 4.726 / 10.91 | 1.541 |
| S1-matched | MC | 2.345 / 31.97 | 2.490 / 27.22 | 1.078 |
| S2-default | CPR | 5.698 / 36.04 | 5.361 / 21.55 | 1.612 |
| S2-default | ME | 5.899 / 45.32 | 5.881 / 43.22 | 1.411 |
| S2-default | MT | 7.079 / 52.02 | 6.771 / 28.26 | 1.802 |
| S2-default | MC | 3.460 / 54.26 | 3.592 / 50.99 | 1.464 |
| S2-matched | CPR | 5.698 / 36.04 | 5.361 / 21.55 | 1.612 |
| S2-matched | ME | 5.899 / 45.32 | 5.881 / 43.22 | 1.411 |
| S2-matched | MT | 5.390 / 51.53 | 5.097 / 24.39 | 1.752 |
| S2-matched | MC | 3.330 / 54.45 | 3.159 / 51.27 | 1.458 |
| S3-default | CPR | 6.632 / 61.06 | 6.808 / 32.19 | 2.013 |
| S3-default | ME | 1.025 / 51.80 | 0.680 / 46.71 | 1.215 |
| S3-default | MT | 7.602 / 76.81 | 7.275 / 38.50 | 1.984 |
| S3-default | MC | 0.987 / 51.27 | 0.639 / 46.56 | 1.125 |
| S3-matched | CPR | 6.632 / 61.06 | 6.808 / 32.19 | 2.013 |
| S3-matched | ME | 1.025 / 51.80 | 0.680 / 46.71 | 1.215 |
| S3-matched | MT | 5.761 / 76.81 | 5.473 / 38.63 | 1.989 |
| S3-matched | MC | 0.945 / 52.02 | 0.612 / 46.61 | 1.131 |
| S2-matched | noackcancel | 5.637 / 38.24 | 5.506 / 21.97 | 1.673 |
| S2-matched | norepeat | 6.033 / 40.39 | 5.837 / 21.89 | 1.570 |
| S2-matched | norecovery | 4.463 / 44.36 | 4.159 / 30.49 | 1.446 |
| S3-matched | noackcancel | 6.741 / 59.77 | 6.901 / 30.48 | 2.028 |
| S3-matched | norepeat | 7.261 / 66.49 | 6.953 / 35.50 | 1.955 |
| S3-matched | norecovery | 2.916 / 45.07 | 3.189 / 35.06 | 1.277 |
| R-deadline-10-S2-matched | CPR | 4.516 / 42.99 | 4.292 / 28.49 | 1.455 |
| R-deadline-10-S2-matched | ME | 5.899 / 45.32 | 5.881 / 43.22 | 1.411 |
| R-deadline-10-S2-matched | MT | 5.390 / 51.53 | 5.097 / 24.39 | 1.752 |
| R-deadline-10-S2-matched | MC | 3.330 / 54.45 | 3.159 / 51.27 | 1.458 |
| R-deadline-60-S2-matched | CPR | 5.847 / 37.26 | 5.890 / 21.96 | 1.637 |
| R-deadline-60-S2-matched | ME | 5.899 / 45.32 | 5.881 / 43.22 | 1.411 |
| R-deadline-60-S2-matched | MT | 5.390 / 51.53 | 5.097 / 24.39 | 1.752 |
| R-deadline-60-S2-matched | MC | 3.330 / 54.45 | 3.159 / 51.27 | 1.458 |

Full CPR airtime is decomposed below by source stage and frame kind, using `cost_summary.csv`. Each entry is mean seconds per seed. These additive means reconstruct total airtime; no component intervals are invented. ACK airtime is charged even when confirmation is not received in time.

| Main matched case | Initial DATA/FLOOD + ACK | Repeat DATA + ACK | Recovery FLOOD + ACK | Total |
| --- | ---: | ---: | ---: | ---: |
| S1-matched | 19.023 + 5.967 | 2.337 + 0.684 | 4.916 + 0.863 | 33.790 |
| S2-matched | 22.532 + 5.436 | 3.279 + 0.751 | 7.559 + 0.994 | 40.551 |
| S3-matched | 71.715 + 12.416 | 31.572 + 5.668 | 77.360 + 8.337 | 207.067 |

## Evidence trace, artifacts and reproducibility

The numerical source is `results/secon2027/analysis/formal-v1/analysis.json`, analysis SHA-256 `8ab85b0313dd99b499947b3c481bd16ab96a0ca0418dae522699de7f659156ef`. Analyzer SHA-256 is `7fd757a780e9725bd3d1992790eaad4a6cc3be7b48f7adcce674a729990eeb54`; recorded runtime is Python 3.9.6, NumPy 1.26.4 and Matplotlib 3.7.5. The independent statistics review used its own bootstrap reconstruction and found no numerical/provenance discrepancy within its stated scope.

| Claim/display | Exact saved row selector | Physical provenance |
| --- | --- | --- |
| Main/control/deadline arm means | `summary.csv`: `case_id, arm_id, metric`; all rows use the one formal plan | `runs.csv` filtered to the same case/arm gives all 20 seeds/run keys and attempt paths |
| Paired tables | `paired_effects.csv`: `case_id, focus_arm, comparator_arm, metric`; paired source in `paired_seed_effects.csv` | Join case/arm/seed to `runs.csv` for both run keys and identity hashes; paired rows retain resolved-parameter differences |
| Latency/unfinished/cost context | `summary.csv` metrics named above; `flow_diagnostics.csv`; `cost_summary.csv` and `cost_kind_stage.csv` | Timely destination/accepted ACK timestamps and started physical TX ledgers |
| S2 exposure populations | `secon2027_supervisor_formal_exposure_review.json`: `S2_regimes[].counters`, `crossing_flow_outcomes`, `actual_blocked_flow_outcomes`, `exposed_union_outcomes`; individual `runs[].flows` | Run key, completion hash, source TX, intended RX, physical forward and reverse ACK TX chains |
| Original DATA-only exposure and all controls | `gates/formal-v1/mechanism-inspection.json`, `prospective-criteria-and-comparisons.json`, `deadline-response-rows.json` | Full per-run diagnostic provenance retained under the same plan |
| S1/S3 exposure and refusals | `secon2027_supervisor_formal_s1_s3_exposure.json`; combined JSON `S1_S3_review.aggregates` | All 80 primary CPR runs, action reasons and physical-stage/RX joins |

The complete trace is **claim → exact table selector → all 20 run keys → attempt directory → `evidence.manifest.json` and completion/raw hashes → frozen source snapshot and tested version**. `runs.csv` carries the manifest hash, source, version and topology/radio/pair-pool/environment/scheduled-trace hashes. The full private release/remote map is maintained in `docs/project-management/secon2027_release_map.md`; this report does not invent a promotion commit or remote verification.

| Numerical table | SHA-256 |
| --- | --- |
| `runs.csv` | `95e8f0cfded9eedd2c3235e5a2e3f092ff768161bfa3cc24bdb69540b36da425` |
| `summary.csv` | `748639f4a1559dbd1a922d53e93bc2717882e927386d5ee40c6c1e8d73cff639` |
| `paired_effects.csv` | `30323f08da14bef59b8c2e78b52dd27de74f3719a1028e691c07bfdf47c34aa3` |
| `paired_seed_effects.csv` | `7a2198f566b5541c6a50b935f64646b2362c218ce30b5079979792400dbb01e7` |

The supervisor exposure `.md/.json/.py` and its S1/S3 `.json/.py` companions were copied unchanged from the sibling canonical repository's `docs/research/`; source paths and extraction provenance embedded in them remain unchanged. They were not re-executed for this report. Copied file hashes are:

| Copied evidence | SHA-256 |
| --- | --- |
| `secon2027_supervisor_formal_exposure_review.md` | `db12f4eaea6ff19c1e71e7b24a34b6c7e97e0a17a77993fc27db24799cbf3c05` |
| `secon2027_supervisor_formal_exposure_review.json` | `1cec389f560eabcbf2c6c41da8af8cbeacfc6f53950d3314849d2a309b0446c2` |
| `secon2027_supervisor_formal_exposure_review.py` | `cb478b8602ce3ea4001a5b86522956ecff4b8a57879402c6b16a6be818a0905c` |
| `secon2027_supervisor_formal_s1_s3_exposure.json` | `d182c299c2eb8b51ad0a2db815e447400061ff4fd596a23bbb2e07f34e0875d6` |
| `secon2027_supervisor_formal_s1_s3_exposure.py` | `46fc3c0421364119bb445564f5740263219c9f98e69476458ef34ec95fedd9ac` |

The analyzer's six figure families (`main_results`, `paired_effects`, `ablation_effects`, `latency`, `cost_decomposition`, `load_curve`) each have PDF and SVG under the analysis directory. The manuscript figure contract is `paper/secon2027/FIGURES.md`; `build_figures.py` reads the verified existing tables into `main_results`, `component_effects`, `robustness` and `latency_cost` panels without resampling. Figure existence/statistical correctness is separate from visual and final PDF acceptance, which is recorded by the manuscript task.

Observed summed worker wall time is **4,423.192 s (73.72 min)**; maximum single-worker duration is **20.901 s**. Peak worker RSS is **398,163,968 B (379.72 MiB)**. Raw attempts occupy **7,098,305,927 B**, including **7,052,691,761 B** of event JSONL. Worker wall sum is not elapsed four-worker runtime; pause, audit, analysis and archive costs are additional. All 38 case/arm resource cells are retained in `results/secon2027/gates/formal-v1/mechanism-resource-costs.json`.

These results evaluate a fixed simulator policy on the finite registered environment, controls and deadline/drain axis. They do not establish official-firmware superiority, calibrated RF/hardware performance, device-energy savings, deadline guarantees, cache-TTL-expiry behavior, optimal ledger sizing, whole-system memory bounds or general performance across other topologies and loads. No tuning, new candidate, seed substitution or rescued claim is authorized by the favorable subsets. Manuscript/PDF acceptance, anonymous artifact publication and submission readiness require their own recorded checks.
