# SECON 2027 development pilot v2: mechanism and cost review

Completed **72/72 planned runs, zero failed attempts** under snapshot `ee890e25030782fc01208ee4ce1f20863c6ade5322ac954ad67ae48b594056a2`; frozen plan `0c49a69a5c3725c9f72ff2e28ed870d10db1df7eec4319f6397097b84a2c85e7`. Seeds 2027000–2027002 remain exposed development seeds. This independent review re-read the full raw flow/action/request/TX/RX/ACK population and independently rebuilt physical cost, path exposure and mechanism counts after the frozen-plan audit passed. Pilot v1 stopped on a code error after 48 completed runs and one failure; its partial evidence is preserved and is not pooled here.

**Freeze assessment:** S1/S2/S3 are mechanically usable for an unchanged-method formal matrix: actual cached multi-hop traffic, blocked intended edges, repeat/recovery, ACK cancellation and elevated contention all occur. The pilot reveals a real high-load cost/reliability failure region; it does not justify a universal improvement claim. Relay-ledger capacity pressure and queue-deadline expiry are not demonstrated. Retain these zeros and the negative S3 results. Nothing in this n=3 diagnosis establishes a new algorithm as preferable or requires a speculative rewrite; component contributions still need the predeclared formal ablations, which are absent from this pilot.

## Complete descriptive results and scope

The following are equal-weight per-seed means, not pooled packet estimates or confirmatory inference. All scheduled flows remain included: N=36/28/39 for S1/S2 and 160/167/148 for S3. Default and matched CPR/legacy have identical effective parameters and outcomes; their physical duplicate runs do not double the independent sample size. Baselines remain behavioral MT-like/MC-like models, not official firmware.

| Scenario / regime | CPR ACK / delivery | CPR airtime s | Legacy ME ACK / airtime s | MT-like ACK / airtime s | MC-like ACK / airtime s |
|---|---:|---:|---:|---:|---:|
| S1 / default | 77.7% / 89.5% | 38.93 | 70.6% / 31.14 | 53.2% / 47.09 | 63.0% / 30.32 |
| S1 / matched | 77.7% / 89.5% | 38.93 | 70.6% / 31.14 | 43.1% / 47.71 | 72.9% / 28.29 |
| S2 / default | 65.0% / 74.7% | 42.87 | 56.6% / 28.18 | 42.1% / 44.50 | 50.5% / 29.05 |
| S2 / matched | 65.0% / 74.7% | 42.87 | 56.6% / 28.18 | 45.6% / 45.75 | 56.8% / 26.03 |
| S3 / default | 32.6% / 59.1% | 211.93 | 37.7% / 95.76 | 20.1% / 186.59 | 42.7% / 85.28 |
| S3 / matched | 32.6% / 59.1% | 211.93 | 37.7% / 95.76 | 20.5% / 186.44 | 36.1% / 87.33 |

CPR spends more airtime than legacy ME and MC-like in every pilot scene/regime. In S3 it also has lower timely ACK PDR than both, while destination delivery and source confirmation differ substantially. This is retained as a failure boundary, not removed as an outlier. Formal paired intervals and complete result plots are produced by the main analyzer separately; n=3 intervals remain unstable/descriptive.

## S1: cached multi-hop operation and steady-load overhead

Per regime across the three seeds, CPR has 71 R_INITIAL and 32 F_INITIAL decisions among 103 scheduled flows. The 80 accepted ACK paths comprise 47 four-hop and 33 six-hop paths; no one-hop shortcut explains completion. Physical source starts include 22 repeats and 11 recovery floods. Accepted ACK provenance is initial=63, repeat=11, recovery=6; these are stage associations, not isolated causal gains. Four recovery starts occur after destination delivery but before source confirmation; the source lacks the observer's delivery oracle, so these are not automatically erroneous actions. ACK cancellation records 16 successful cancellations / 1,373 decoded-ACK checks (1.17%); checks include ineligible cases and are not an eligible-opportunity denominator. Capacity evictions are zero.

## S2: real blocked-edge exposure, alternatives and retained failures

Faults are the predeclared 80 dB attenuation on edges 7–8 and 12–13 during [80,160) s. Radio attenuation is evaluated at each TX's start time. Physical directed-edge attempts use DATA/RREP `path[index+1]` and ACK `path[index]`, joined to the intended receiver's RX row. Broadcast prefixes/FLOODs are not misclassified as intended routed edges. Frame overlap alone is not fault exposure, and collision/half-duplex labels do not prove fault causation.

The following CPR counts are per seed in default; matched is identical and is not additional independent evidence. A "warm intersecting" path is reconstructed from the last logged cache install/refresh before 80 s, its TTL and later timeout invalidation/quarantine events. The actual source-DATA and intended-edge columns provide direct physical exposure evidence.

| Seed | Enqueued in fault | Active during fault | Active, initial before 80 | Warm intersecting pairs | Initial DATA path intersects fault | Physical blocked-edge TX | All-scenario source repeat / recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2027000 | 12 | 12 | 0 | 3 / 4 | 5 | 8 | 11 / 7 |
| 2027001 | 11 | 12 | 1 | 3 / 4 | 5 | 9 | 10 / 8 |
| 2027002 | 7 | 12 | 5 | 1 / 4 | 1 | 2 | 6 / 2 |

Across seeds per regime, 30 flows enqueue during the fault, 36 overlap it, and six had an initial source TX before 80 s. **Eleven distinct CPR flows actually attempt the blocked intended DATA edge, producing 19 TX attempts: 11 initial-stage and eight repeat-stage.** Intended RX outcomes are 15 PRR failures and four capture-collision failures, with no decodes. All 11 exposed flows start repeat and recovery; five deliver by deadline, four obtain a timely recovery ACK on a six-hop alternate path, one delivers without a timely ACK, and six never deliver. All 36 active flows have an offline six-hop structural alternative within the configured hop limit; that does not guarantee RF success. Actual blocked-edge attempts by flows starting before 80 are **zero**, despite six broad lifetime overlaps; no omitted cross-boundary attempt was discovered. There are also zero frames whose blocked-edge interval overlaps the fault while their TX start lies outside it.

For context, physical blocked intended-edge DATA attempts per three seeds are legacy ME=25 in each regime, MC-like=20 default/22 matched, and MT-like=0 routed intended-edge attempts. MT-like's zero reflects broadcast DATA semantics and is not absence of broadcast exposure to the fault. CPR's pre-fault intersecting ready-path pairs are 3/4, 3/4 and 1/4; other pairs have no confirmed path or already avoid the failed edge. Do not claim every pair begins with a guaranteed faulted warm route.

## S3: contention, state capacity and source-confirmation gap

All 475 scheduled CPR flows per regime partition into **156 timely destination deliveries with timely source ACK, 125 timely deliveries without timely ACK, and 194 without timely destination delivery**. The per-seed population is retained below; matched is identical and is not pooled as additional independent evidence.

| Seed | Scheduled | Timely DATA + ACK | Timely DATA without timely ACK | No timely DATA |
|---|---:|---:|---:|---:|
| 2027000 | 160 | 46 | 46 | 68 |
| 2027001 | 167 | 68 | 34 | 65 |
| 2027002 | 148 | 42 | 45 | 61 |

This partition identifies a source-confirmation gap without attributing every missing ACK to one radio cause. Intended DATA receiver opportunities separately yield collision=357, half-duplex=102, PRR-fail=23, success=1,453; intended ACK opportunities yield 114, 27, 13 and 1,024 respectively. They span multiple hops and stages, so a per-flow loss cause cannot be inferred by treating each receiver outcome as an independent failed application.

CPR makes 351 R_INITIAL, 119 F_INITIAL and five initial DROP decisions among 475 scheduled flows per regime. Physical source repeats rise to 282 and recovery floods to 241; ACK-stage associations are initial=88, repeat=34, recovery=34. Forty-two recovery starts follow observed destination delivery. Intended-hop RX opportunities have capture-collision=471, half-duplex=129, PRR-fail=36, success=2,477. The collision+half-duplex fraction is 600/3,113 = 19.27%, versus 28/820 = 3.41% in S1. Neighbor-listener opportunities independently show 3,991 collision and 1,410 half-duplex failures, compared with 368 and 34 in S1. These are correlated receiver opportunities, not independent-flow samples.

Mean per-seed CPR queue wait rises from 0.266 s (S1) to 0.373 s (S3), but the mean seed p95 is only 1.043 s and no queue/deadline-expiry status occurs. S3 CPR requests are 6,574 started, 544 canceled-before-start and 11 protocol-no-start per regime. Five **source-state capacity** drops occur at seed 2027000; they are distinct from the relay cancellation ledger. Relay-ledger eviction/pending-capacity-cancel counts stay **zero** for every run. Its configured capacity is eight records per relay, while exact peak occupancy is unobserved because enroll/retire/occupancy events are not emitted; zero eviction does not establish peak occupancy below eight.

Cancellation succeeds 80 times across 3,401 decoded-ACK checks (2.35%) per regime; these counts do not establish the benefit relative to disabling cancellation. Successful-flow latency must remain paired with failures: the mean seed timely-ACK p95 is 4.803 s in S1, 5.977 s in S2 and 7.369 s in S3, while timely ACK PDR falls to 32.6% in S3. Do not compare success-only delay as if it included unfinished flows.

Decision enum and reason are retained separately. S3 contains four `DROP` and seven `DROP_DEADLINE_INFEASIBLE` decision events with reason `stale-route-generation` per regime. They are **stale-route rejections**, not evidence that eleven flows lacked deadline budget; action-event counts also need not equal initial-flow categories. The five initial `DROP/state-capacity-drop` decisions are a separate population. Full `(event, action, reason)` and `(initial action, decision reason)` tables remain in the diagnostic JSON.

## Additive physical cost and resource budget

Each physical TX is counted once at its full modeled ToA, including ACK and control frames; totals reconcile to frozen ledger summaries. The following stage partition includes every packet kind and sums to total airtime. Means are over three seeds, default; CPR matched is identical.

| Scenario | Initial-stage s | Repeat-stage s | Recovery-stage s | Total s |
|---|---:|---:|---:|---:|
| S1 | 29.662 | 4.368 | 4.896 | 38.926 |
| S2 | 30.442 | 5.129 | 7.300 | 42.871 |
| S3 | 90.652 | 36.172 | 85.103 | 211.927 |

The full pilot used 301.926 summed worker wall seconds (5.03 min), 706,194,269 bytes (673.48 MiB) of raw attempt files, and 701,813,646 bytes of event JSONL. Maximum worker RSS was 360,251,392 bytes (343.56 MiB). These are measured serial-run costs, not a guarantee for larger topology/deadline settings; audit/plot/archive time and v1 failed-batch storage are additional. At the identical scene/model mix, 480 main-comparison runs scale to approximately 33.55 min worker wall time and 4.71 GB raw storage, before ablations, robustness, retries and audit margin. CPU/host load can vary; default/matched duplicate effective runs had different wall times despite identical scientific outcomes.

| Case | Model | Mean wall s/run | Peak RSS MiB | Raw attempt MiB / 3 runs | Event JSONL MiB / 3 runs |
|---|---|---:|---:|---:|---:|
| S1-default | MC-like | 2.30 | 96.7 | 13.68 | 13.53 |
| S1-default | Legacy ME | 2.12 | 94.2 | 13.38 | 13.22 |
| S1-default | CPR | 2.59 | 94.4 | 15.59 | 15.43 |
| S1-default | MT-like | 2.70 | 107.4 | 17.75 | 17.60 |
| S1-matched | MC-like | 1.55 | 87.5 | 12.52 | 12.36 |
| S1-matched | Legacy ME | 1.55 | 93.3 | 13.38 | 13.22 |
| S1-matched | CPR | 1.94 | 93.9 | 15.59 | 15.43 |
| S1-matched | MT-like | 2.08 | 110.7 | 17.78 | 17.62 |
| S2-default | MC-like | 3.11 | 95.9 | 12.92 | 12.76 |
| S2-default | Legacy ME | 1.54 | 89.8 | 12.06 | 11.90 |
| S2-default | CPR | 2.40 | 93.6 | 16.56 | 16.40 |
| S2-default | MT-like | 2.96 | 103.9 | 16.58 | 16.42 |
| S2-matched | MC-like | 1.75 | 84.5 | 11.40 | 11.24 |
| S2-matched | Legacy ME | 2.34 | 90.7 | 12.06 | 11.90 |
| S2-matched | CPR | 3.47 | 94.9 | 16.56 | 16.40 |
| S2-matched | MT-like | 2.90 | 99.2 | 17.04 | 16.88 |
| S3-default | MC-like | 5.03 | 170.8 | 35.15 | 34.95 |
| S3-default | Legacy ME | 5.14 | 181.0 | 37.45 | 37.24 |
| S3-default | CPR | 9.54 | 343.6 | 78.37 | 78.16 |
| S3-default | MT-like | 11.20 | 315.5 | 68.69 | 68.48 |
| S3-matched | MC-like | 5.00 | 173.8 | 34.64 | 34.44 |
| S3-matched | Legacy ME | 6.18 | 181.1 | 37.45 | 37.24 |
| S3-matched | CPR | 11.12 | 342.4 | 78.37 | 78.16 |
| S3-matched | MT-like | 10.15 | 311.8 | 68.51 | 68.30 |

## Freeze boundary and reproducible records

Freeze the unchanged method only with the full S1/S2/S3 scope, the explicit S3 failure region, separate default/matched interpretation, the three component ablations on prospectively selected cases, a finite robustness axis, fresh formal seeds and fixed statistics/budget/failure rules. The pilot does not validate cache expiry (240 s horizon versus 300/600 s TTL), broad topology robustness, relay-ledger overflow, hardware/RF or a uniform advantage. Any decision to revise method/scenario is development work requiring a recorded new identity; no formal seed should be selected or discarded by its result.

For task-book §9, the concrete development decision supported by this review is **retain fixed CPR for characterization and clean component tests**. High-load repetitions/recovery correlate with substantial airtime and a poor ACK outcome, but there is no controlled per-flow causal counterfactual or validated locally observable backoff/admission rule establishing a better candidate. A speculative new algorithm is not justified merely to improve the narrative; the formal evaluation should test the existing bounded mechanism and state its failure region.

Records under `results/secon2027/gates/pilot-v2/`: `mechanism-inspection.json` (all 72 per-run diagnostic records and audit), `fault-exposed-flow-details.json` (every exposed CPR flow in both regimes), `resources-by-case-protocol.csv`, and the exact `pilot-mechanism-inspection.py` used. The copied script's original working assumption is the chat's `work/` location; invoke its preserved original path or set `ROOT` explicitly when relocating it. The inspection source SHA is `c69a4f967875e5208abb785e0861ddffac4d14923de868a1347ca5f666553b5b`. Raw attempt files and earlier analyses were not modified. The standalone command was:

```sh
python3 work/pilot-mechanism-inspection.py --plan results/secon2027/plans/development-pilot-v2.json --out work/pilot-mechanism-inspection-v2.json
```

This document reports development diagnosis, including negative outcomes; it is not the formal evaluation, a completed ablation package or the final paper.
