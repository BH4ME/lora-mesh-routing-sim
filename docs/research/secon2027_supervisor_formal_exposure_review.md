# SECON 2027 formal mechanism-exposure review

Status: **all preregistered primary-CPR exposure gates observed; no targeted-review discrepancy**. Summary written 2026-11-04T09:52:38.094595+00:00. This review reads the 40 primary CPR S2 runs and the complementary 80 primary CPR S1/S3 runs, retaining all 20 seeds in both regimes. It performs no simulation, seed registration, parameter change or execution-tree write, and does not repeat the full 760-run raw audit.

The plan is `5f1a12fe49bf7fc0ea32cc048a3595ed0bd290811f952a47c5a33b0cded2cbb0`, source snapshot `63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee`, frozen contract `0db4fc2e724f441e190693e3f8d37b7912e2d4baa5555515c6f132481f309eff`. The original contract and post-exposure administrative erratum remain preserved. The criteria below are the frozen **claim gates**, not seed filters. Every scheduled flow remains in the primary denominator; the explicitly labeled S2 subsets only describe mechanism exposure.

## S2: actual cached-route disruption and recovery

Both default and matched meet the gate separately. Per regime, there are **648 scheduled flows**, 193 enqueued within [80,160) s and 218 whose lifetimes overlap that interval. **85 physical routed initial sends** start during the fault and carry a path containing edge 7–8 or 12–13. All 85 have a prior accepted ACK before 80 s on the same path and route generation. All 20 seeds exhibit at least one such path and at least one actual blocked intended-edge transmission.

There are **159 actual fault-edge TX attempts across 87 flows**: 78 initial DATA, 80 repeat DATA and one initial-stage ACK. The designated receivers decode none: 130 PRR failures, 27 capture-collision outcomes and two half-duplex outcomes. Collision/half-duplex labels are not proof of fault causation. DATA/RREP designate `path[index+1]`; ACK designates `path[index]`. Exposure uses TX start in [80,160), not frame overlap or flow lifetime alone. No outside-start frame merely overlaps the fault interval in these runs.

Of 25 fault-active flows whose initial TX starts before 80 s, **four do make later actual fault-edge attempts**. This differs from the development pilot and is retained. The 85 active-path crossings and 87 physically blocked flows overlap in 83 flows; their union is 89. These populations must not be silently substituted for one another or for the full N=648 denominator.

For the **85 initial-path-crossing flows**, 82 start a repeat and 78 start recovery. **24 deliver on time, 18 receive a timely ACK, six deliver without a timely ACK, and 61 do not deliver on time.** All 24 timely first deliveries and all 18 timely ACKs are associated with recovery marker 2; none has a timely repeat ACK. Twenty-three recovery first deliveries occur during the active fault along paths that avoid the blocked edges, and 17 recovery ACKs complete within the active fault on avoiding paths. A late-in-window success is not automatically active-fault recovery.

For the distinct **87 actual blocked-edge flows**, 84 repeat, 80 recover, 26 deliver on time and 19 receive a timely ACK; seven deliver without timely ACK and 61 lack timely delivery. Two timely first deliveries come from the initial stage; one of those flows later starts recovery, while the other has no recovery start. Source confirmation and destination delivery therefore remain separate, without granting the source a delivery oracle.

All first destination deliveries for the 40 runs are matched to physical decoded destination RX. For the exposed union, the script additionally reconstructs every successful first-delivery forward path and every accepted ACK's full reverse path plus its matching forward stage. There are 90 forward-chain reconstructions and 38 complete reverse-ACK chains across the two regimes, with zero failures. These are observed stage associations; isolated benefit/cost still comes from the frozen controls, not from treating recovery-associated success as a counterfactual gain.

The following table is per seed, **for each regime separately**. Default and matched scientific records are identical and are not pooled as n=40. The last two columns apply only to the initial-path-crossing subset.

| Seed | All scheduled N | Active initial path crosses | Actual blocked-edge TX | Repeat / recovery flows | Timely delivery / ACK |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2027100 | 33 | 3 | 6 | 3 / 2 | 1 / 1 |
| 2027101 | 36 | 1 | 2 | 1 / 1 | 0 / 0 |
| 2027102 | 35 | 6 | 12 | 6 / 6 | 3 / 2 |
| 2027103 | 33 | 6 | 12 | 6 / 6 | 0 / 0 |
| 2027104 | 31 | 8 | 16 | 8 / 8 | 2 / 1 |
| 2027105 | 31 | 4 | 8 | 4 / 4 | 1 / 1 |
| 2027106 | 38 | 4 | 6 | 4 / 4 | 1 / 1 |
| 2027107 | 35 | 4 | 8 | 4 / 4 | 1 / 1 |
| 2027108 | 25 | 3 | 7 | 3 / 3 | 1 / 1 |
| 2027109 | 36 | 6 | 10 | 6 / 4 | 0 / 0 |
| 2027110 | 35 | 4 | 8 | 4 / 4 | 3 / 1 |
| 2027111 | 39 | 5 | 9 | 5 / 5 | 2 / 2 |
| 2027112 | 25 | 5 | 10 | 5 / 5 | 2 / 2 |
| 2027113 | 36 | 5 | 7 | 4 / 4 | 1 / 0 |
| 2027114 | 24 | 1 | 2 | 1 / 1 | 1 / 1 |
| 2027115 | 31 | 4 | 8 | 4 / 4 | 2 / 2 |
| 2027116 | 38 | 4 | 7 | 3 / 2 | 0 / 0 |
| 2027117 | 30 | 2 | 4 | 2 / 2 | 0 / 0 |
| 2027118 | 30 | 4 | 8 | 4 / 4 | 1 / 1 |
| 2027119 | 27 | 6 | 9 | 5 / 5 | 2 / 1 |

An auditable success example, selected as the first qualifying flow in seed/flow order, is seed 2027100, flow 15 (10→14), run `ffbd30cbc519bed7a13a60d4203dcaeb2a2af14a917e7d684acdf65054c3cbae`. Its initial path 10→11→12→7→8→13→14 physically attempts 7→8 at 107.304356 s and repeats that edge at 108.632628 s; both intended RXs fail. Recovery starts at 109.622212 s, travels 10→11→12→17→18→13→14, reaches the destination at 114.622223 s, and returns a six-hop ACK at 115.023119 s before the 136.965668 s deadline. Forward TX IDs 210/212/214/218/223/227 and reverse ACK TX IDs 228–233 are tied to their decoded RXs in the JSON.

A retained cross-boundary failure is seed 2027106, flow 15: its initial send starts at 79.520476 s, a repeat reaches blocked 7→8 at 81.187436 s, recovery starts at 82.177020 s, and neither destination delivery nor accepted ACK follows. Successful examples are illustrative, not a selection rule.

The structural alternative context is unchanged from the reviewed pilot/formal matrix: the same grid, fault edges, endpoint pairs and H=6 give the previously checked six-hop alternatives. This review does not rerun BFS or imply structural reachability guarantees RF success.

## S1 and S3: full seed populations and observed pressure

The companion S1/S3 review retains full per-seed initial-mode and actual path/ACK-hop distributions, physical stages, request statuses, queue waits, action/reason counts and zeros. Each regime has:

| Quantity | S1 | S3 |
| --- | ---: | ---: |
| Scheduled flows | 648 | 3059 |
| Physical routed initial | 480 | 2,445 |
| Physical cold initial | 168 | 608 |
| Accepted ACK, all ≥2 hops | 526 | 1,181 |
| Accepted ACK 4-hop / 6-hop | 440 / 86 | 703 / 478 |
| Physical repeat / recovery | 135 / 91 | 1,890 / 1,597 |
| Intended-hop capture collision / half duplex | 227 / 35 | 3,228 / 887 |
| Successful ACK cancellation | 205 | 685 |
| Source-state capacity refusal | 0 | 6 |
| Relay eviction / pending capacity cancel | 0 / 0 | 0 / 0 |
| Protocol-no-start requests | 2 | 52 |
| Mean of per-seed queue-wait means, s | 0.254951 | 0.345067 |
| Mean of per-seed queue-wait p95, s | 0.991642 | 1.033965 |

For every seed and regime, S3 offered N exceeds its matched S1 N (ratios 3.857–6.167). Intended-hop contention is nonzero in both regimes. The six source refusals occur at seeds 2027105 and 2027111, three each; all remain in N. They are not relay eviction. Zero relay eviction does not establish peak occupancy below capacity; peak occupancy remains unobserved. Queue waits and protocol-no-start requests do not establish queue saturation or a dominant deadline-expiry cause. RX opportunities are correlated across hops and attempts, not independent application failures.

S2's full reference populations also contain 182 physical repeats, 142 recoveries and 204 successful ACK cancellations per regime. Thus the S2/S3 matched reference populations expose each predeclared component. This makes their controls interpretable; it does not prove a positive component effect. The matched/default duplicates provide no additional independent seeds.

## Reproducibility and cross-check boundary

The final verified full-raw summary `secon2027_supervisor_formal_raw_review_verified.json` has no unresolved issues. All **120 targeted primary CPR run summaries** match it on the checked completion hashes, populations, physical stages and applicable ACK-hop, cancellation, relay-eviction and contention counts. This is a comparison of saved summaries, not a second 760-run audit. The initial full-raw checker's 39 accepted-ACK count flags were corrected in its separately preserved correction chain; they were not experiment defects and are not treated as open findings here.

Artifacts:

- `secon2027_supervisor_formal_exposure_review.json`: all 40 S2 per-run/per-flow records, exact path intersections, fault TX/RX IDs, delivery/ACK chains, claim-gate summaries and companion/cross-check hashes.
- `secon2027_supervisor_formal_s1_s3_exposure.json`: all 80 S1/S3 per-run records and all 40 within-seed load comparisons.
- `secon2027_supervisor_formal_exposure_review.py` and `secon2027_supervisor_formal_s1_s3_exposure.py`: standard-library read-only raw extractors. Run the S1/S3 script first, then this script after the independently verified full-raw summary exists. `--summary-only` rebuilds this combined summary from the existing targeted evidence without reading raw logs again.

All 20 formal seeds are retained. The review establishes the registered exposure conditions for these populations, not universal efficiency, positive causal gain, calibrated RF validity, cache-expiry behavior, memory optimization, complete manuscript accuracy or submission readiness. The formal default/matched comparisons, controls and deadline/drain response require their own complete descriptive analysis and claim review.
