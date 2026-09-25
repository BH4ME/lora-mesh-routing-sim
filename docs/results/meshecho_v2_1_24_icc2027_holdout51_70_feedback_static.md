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
- Temporal block fading: disabled (static per-link shadowing)

## Link Regime

| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.582805 | 0.998742 | 0.999994 | 1.000000 | 1.000000 | 0.158 | 0.044 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshecho | 0.716 | 0.737 | 24.2 | 7816.0 | 1.95 | 3.0 | 1.000 | 2.04 | 0.723 | 0.039 |
| meshecho-calibrated | 0.717 | 0.728 | 25.4 | 7825.6 | 2.18 | 3.0 | 1.000 | 2.42 | 0.716 | 0.042 |
| prr-product-mesh | 0.715 | 0.725 | 25.1 | 7659.9 | 2.19 | 3.0 | 1.000 | 2.41 | 0.720 | 0.043 |
| prr-product-fallback-mesh | 0.727 | 0.739 | 25.6 | 7830.8 | 2.17 | 3.0 | 1.000 | 2.41 | 0.728 | 0.043 |
| meshecho-ack-evict | 0.690 | 0.705 | 28.8 | 10324.1 | 2.38 | 2.8 | 1.000 | 2.03 | 0.713 | 0.039 |
| prr-product-ack-evict-mesh | 0.714 | 0.724 | 28.4 | 9346.1 | 2.39 | 3.0 | 1.000 | 2.32 | 0.733 | 0.042 |

## Application Denominators

Counts are totals across seeds; pair ranges are per-seed minima and maxima. ACK and destination counts use observed unicasts as their denominator. In the protocol-results means, each seed has equal weight; pooled flow counts below can imply a different overall ratio when seed-level flow counts vary. The CSV preserves every seed's counts.

| Protocol | Scheduled unicast | Observed unicast | Scheduled distinct pairs/seed | Observed distinct pairs/seed | ACKs / observed unicast | Destinations / observed unicast | Scheduled broadcast |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshecho | 793 | 793 | 4-4 | 4-4 | 572/793 | 588/793 | 0 |
| meshecho-calibrated | 793 | 793 | 4-4 | 4-4 | 566/793 | 574/793 | 0 |
| prr-product-mesh | 793 | 793 | 4-4 | 4-4 | 566/793 | 573/793 | 0 |
| prr-product-fallback-mesh | 793 | 793 | 4-4 | 4-4 | 574/793 | 583/793 | 0 |
| meshecho-ack-evict | 793 | 793 | 4-4 | 4-4 | 548/793 | 560/793 | 0 |
| prr-product-ack-evict-mesh | 793 | 793 | 4-4 | 4-4 | 565/793 | 572/793 | 0 |

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
| meshecho | 27.2 | 12.4 | 4.2 | 3.0 | 0.2 | 0.0 | 0.0 | 48.0 | 0.48 |
| meshecho-calibrated | 26.4 | 13.2 | 4.2 | 3.0 | 0.2 | 0.0 | 0.0 | 50.5 | 0.55 |
| prr-product-mesh | 26.4 | 13.2 | 4.2 | 3.0 | 0.2 | 0.0 | 0.0 | 49.9 | 0.55 |
| prr-product-fallback-mesh | 26.9 | 12.8 | 4.2 | 3.0 | 0.2 | 0.0 | 0.0 | 50.8 | 0.55 |
| meshecho-ack-evict | 24.8 | 14.9 | 5.6 | 4.0 | 0.3 | 1.2 | 0.3 | 56.7 | 0.55 |
| prr-product-ack-evict-mesh | 25.5 | 14.2 | 5.2 | 4.0 | 0.2 | 0.9 | 0.2 | 56.3 | 0.60 |

## Discovery Candidate Audit

Counts are totals across seeds. Each protocol/seed CSV row has `discovery_record_count`, `discovery_candidate_path_total`, `discovery_multi_candidate_count`, `discovery_records_json`, and `discovery_candidate_fingerprints_json`. The JSON record field contains the observed candidate and selected paths for each discovery; fingerprints support paired set comparisons.

| Protocol | Discoveries | Candidate paths | Multi-candidate discoveries |
| --- | ---: | ---: | ---: |
| meshecho | 85 | 301 | 74 |
| meshecho-calibrated | 85 | 299 | 74 |
| prr-product-mesh | 85 | 298 | 74 |
| prr-product-fallback-mesh | 85 | 301 | 74 |
| meshecho-ack-evict | 112 | 398 | 98 |
| prr-product-ack-evict-mesh | 104 | 388 | 93 |

## Paired MeshEcho Comparisons

Differences are MeshEcho minus the named comparator, paired by seed. Entries are mean deltas with two-sided 95% paired confidence intervals.

| Comparison | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshecho-calibrated | -0.000 [-0.075,+0.074] | +0.010 [-0.066,+0.086] | -1.2 [-2.3,-0.1] |
| MeshEcho vs prr-product-mesh | +0.001 [-0.090,+0.092] | +0.012 [-0.080,+0.105] | -0.9 [-2.4,+0.6] |
| MeshEcho vs prr-product-fallback-mesh | -0.011 [-0.097,+0.076] | -0.002 [-0.090,+0.086] | -1.3 [-2.6,-0.1] |

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
  --case feedback_static \
  --seeds 20 --seed0 51 \
  --out-prefix meshecho_v2_1_24_icc2027_holdout51_70 \
  --protocol meshecho \
  --protocol meshecho-calibrated \
  --protocol prr-product \
  --protocol prr-product-fallback \
  --protocol meshecho-ack-evict \
  --protocol prr-product-ack-evict
```
