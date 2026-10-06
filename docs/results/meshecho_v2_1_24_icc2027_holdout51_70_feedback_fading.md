# MeshEcho Fair Multi-Hop Probe

This matched-discovery, repeated-pair feedback workload measures route-cache reuse and recovery across channel time blocks. It is reported separately from the sparse first-discovery experiment.

- Seeds: `20`
- Nodes / area: `50` / `8250 m square`
- Traffic: `unicast`, `4.0 flows/min`
- MeshEcho timeout-retry budget: `0`
- Route-cache TTL: `600.0 s`
- PHY: `SF7`, `17.0 dBm`, `n=2.75`, shadow sigma `4.0 dB`
- Pair mode: `connected-multihop`
- Connected-pair selection: shared link-budget graph with edge PRR >= `0.90`, graph distance `2-4` hops
- MeshCore-like discovery window: `2.00 s`
- Matched RREQ relay timing: `True`
- Channel reception RNG: independent from protocol jitter/exploration
- Quality gate: PASSED for every seed; direct-link PRR below 0.99 >= `0.10`, pair pool complete, mean graph hops >= `2.00`
- Repeated-pair gate: every selected pair has at least two scheduled application unicasts across at least two scheduled time blocks; application flow counts and paired traffic traces match. Actual DATA transmission and route reuse are reflected separately by delivery and cache metrics.
- Temporal block fading: sigma `6.0 dB`, interval `60.0 s`

## Link Regime

| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.582805 | 0.998742 | 0.999994 | 1.000000 | 1.000000 | 0.158 | 0.044 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshecho | 0.509 | 0.535 | 21.2 | 7551.1 | 1.49 | 3.0 | 0.705 | 1.73 | 0.745 | 0.033 |
| meshecho-calibrated | 0.624 | 0.633 | 23.7 | 7531.4 | 1.80 | 3.0 | 1.000 | 2.31 | 0.722 | 0.042 |
| prr-product-mesh | 0.627 | 0.638 | 23.8 | 7516.9 | 1.73 | 2.9 | 1.000 | 2.33 | 0.712 | 0.042 |
| prr-product-fallback-mesh | 0.621 | 0.633 | 23.8 | 7535.9 | 1.74 | 3.0 | 1.000 | 2.34 | 0.722 | 0.042 |
| meshecho-ack-evict | 0.471 | 0.495 | 41.1 | 17717.0 | 2.41 | 1.8 | 0.944 | 1.89 | 0.750 | 0.033 |
| prr-product-ack-evict-mesh | 0.526 | 0.538 | 33.7 | 13101.6 | 2.44 | 2.0 | 1.000 | 2.22 | 0.676 | 0.041 |

## Application Denominators

Counts are totals across seeds; pair ranges are per-seed minima and maxima. ACK and destination counts use observed unicasts as their denominator. In the protocol-results means, each seed has equal weight; pooled flow counts below can imply a different overall ratio when seed-level flow counts vary. The CSV preserves every seed's counts.

| Protocol | Scheduled unicast | Observed unicast | Scheduled distinct pairs/seed | Observed distinct pairs/seed | ACKs / observed unicast | Destinations / observed unicast | Scheduled broadcast |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshecho | 793 | 793 | 4-4 | 4-4 | 402/793 | 423/793 | 0 |
| meshecho-calibrated | 793 | 793 | 4-4 | 4-4 | 490/793 | 498/793 | 0 |
| prr-product-mesh | 793 | 793 | 4-4 | 4-4 | 492/793 | 501/793 | 0 |
| prr-product-fallback-mesh | 793 | 793 | 4-4 | 4-4 | 488/793 | 498/793 | 0 |
| meshecho-ack-evict | 793 | 793 | 4-4 | 4-4 | 374/793 | 393/793 | 0 |
| prr-product-ack-evict-mesh | 793 | 793 | 4-4 | 4-4 | 411/793 | 420/793 | 0 |

## Repeated-Pair Audit

Each seed uses one application trace shared by all protocols. The CSV also preserves `scheduled_pair_counts_json` and the full `scheduled_trace_sha256` for per-pair inspection.

| Seed | Scheduled/observed application unicasts | Selected pairs | Min scheduled unicasts/pair | Min scheduled blocks/pair |
| ---: | ---: | ---: | ---: | ---: |
| 51 | 35/35 | 4 | 8 | 6 |
| 52 | 53/53 | 4 | 13 | 8 |
| 53 | 35/35 | 4 | 8 | 7 |
| 54 | 41/41 | 4 | 10 | 8 |
| 55 | 31/31 | 4 | 7 | 6 |
| 56 | 41/41 | 4 | 10 | 9 |
| 57 | 39/39 | 4 | 9 | 7 |
| 58 | 43/43 | 4 | 10 | 7 |
| 59 | 40/40 | 4 | 10 | 7 |
| 60 | 39/39 | 4 | 9 | 8 |
| 61 | 34/34 | 4 | 8 | 7 |
| 62 | 37/37 | 4 | 9 | 8 |
| 63 | 35/35 | 4 | 8 | 7 |
| 64 | 30/30 | 4 | 7 | 5 |
| 65 | 49/49 | 4 | 12 | 8 |
| 66 | 46/46 | 4 | 11 | 7 |
| 67 | 37/37 | 4 | 9 | 7 |
| 68 | 41/41 | 4 | 10 | 8 |
| 69 | 46/46 | 4 | 11 | 7 |
| 70 | 41/41 | 4 | 10 | 8 |

## Feedback Diagnostics

Counts and energy are means per seed. `Legacy repair events` mix cache expiry and failed discovery; they are not successful repairs. Invalidations after destination DATA are a simulator-only diagnostic of destination-delivered but ACK-unconfirmed flows; they do not prove the path remained valid at timeout and are never policy input.

| Protocol | Route-cache hits | Cache misses | Route discoveries | Discovery successes | Legacy repair events | ACK timeout invalidations | Invalidations after destination DATA | Total energy (J) | Mean ACK delay (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshecho | 27.3 | 12.3 | 4.2 | 3.0 | 0.1 | 0.0 | 0.0 | 42.1 | 0.46 |
| meshecho-calibrated | 26.2 | 13.4 | 4.2 | 3.0 | 0.1 | 0.0 | 0.0 | 47.2 | 0.54 |
| prr-product-mesh | 25.8 | 13.8 | 4.2 | 2.9 | 0.1 | 0.0 | 0.0 | 47.3 | 0.52 |
| prr-product-fallback-mesh | 26.2 | 13.4 | 4.2 | 3.0 | 0.1 | 0.0 | 0.0 | 47.5 | 0.54 |
| meshecho-ack-evict | 17.1 | 22.6 | 9.8 | 7.6 | 0.2 | 5.8 | 0.7 | 80.7 | 0.84 |
| prr-product-ack-evict-mesh | 18.7 | 20.9 | 7.3 | 5.2 | 0.1 | 3.1 | 0.4 | 66.6 | 0.74 |

## Discovery Candidate Audit

Counts are totals across seeds. Each protocol/seed CSV row has `discovery_record_count`, `discovery_candidate_path_total`, `discovery_multi_candidate_count`, `discovery_records_json`, and `discovery_candidate_fingerprints_json`. The JSON record field contains the observed candidate and selected paths for each discovery; fingerprints support paired set comparisons.

| Protocol | Discoveries | Candidate paths | Multi-candidate discoveries |
| --- | ---: | ---: | ---: |
| meshecho | 83 | 386 | 78 |
| meshecho-calibrated | 83 | 394 | 76 |
| prr-product-mesh | 83 | 402 | 76 |
| prr-product-fallback-mesh | 83 | 395 | 76 |
| meshecho-ack-evict | 196 | 948 | 187 |
| prr-product-ack-evict-mesh | 145 | 713 | 136 |

## Paired MeshEcho Comparisons

Differences are MeshEcho minus the named comparator, paired by seed. Entries are mean deltas with two-sided 95% paired confidence intervals.

| Comparison | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshecho-calibrated | -0.115 [-0.200,-0.031] | -0.098 [-0.181,-0.016] | -2.5 [-3.7,-1.2] |
| MeshEcho vs prr-product-mesh | -0.118 [-0.197,-0.040] | -0.102 [-0.179,-0.026] | -2.5 [-3.8,-1.3] |
| MeshEcho vs prr-product-fallback-mesh | -0.113 [-0.196,-0.029] | -0.098 [-0.180,-0.016] | -2.6 [-3.9,-1.4] |

## Reading the Result

- Direct-link fractions below 0.99 PRR: 0.158; below 0.50 PRR: 0.044.
- This workload intentionally cycles over four connected pairs; route-cache hits and legacy repair events are part of the estimand.
- MeshEcho is compared with PRR-product, PRR-product with matched fallback under shared application traffic. Routed policies use the stated discovery window and timeout-retry budget.
- PRR-product ranks observed routes by multiplying each hop's model-derived PRR from received RREQ SINR, using the same link observation as ETX. The standard comparator has no retry or fallback; under concurrent traffic, candidate sets can still differ after protocol-specific control/data transmissions.
- PRR-product with matched fallback retains the same path score but enables MeshEcho's TTL-2 route-miss recovery without a same-flow timeout retry.
- The ACK-timeout route-invalidation variant is an optional comparator, not a meshecho-no-* component ablation.
- The calibrated max-min PRR variant ranks paths by the weakest model-inferred RREQ hop PRR, without an extra hop penalty; it is an experimental MeshEcho variant, not a standard baseline.
- The raw route-hop columns should be checked before calling this a multi-hop benchmark. A low multi-hop fraction means the parameter setting is still too easy.
- Route-discovery success and RREP/RREQ transmission ratios are reported because a low discovery success rate indicates a route-discovery stress test, not an isolated data-plane comparison.

## Reproduction

```sh
python3 tools/run_icc_generalization_experiment.py \
  --case feedback_fading \
  --seeds 20 --seed0 51 \
  --out-prefix meshecho_v2_1_24_icc2027_holdout51_70 \
  --protocol meshecho \
  --protocol meshecho-calibrated \
  --protocol prr-product \
  --protocol prr-product-fallback \
  --protocol meshecho-ack-evict \
  --protocol prr-product-ack-evict
```
