# MeshEcho Fair Multi-Hop Probe

This matched-discovery, repeated-pair feedback workload measures route-cache reuse and recovery across channel time blocks. It is reported separately from the sparse first-discovery experiment.

- Seeds: `10`
- Nodes / area: `50` / `8250 m square`
- Traffic: `unicast`, `4.0 flows/min`
- MeshEcho timeout-retry budget: `0`
- Route-cache TTL: `30.0 s`
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
| 0.544995 | 0.998362 | 0.999991 | 1.000000 | 1.000000 | 0.170 | 0.048 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshecho | 0.251 | 0.269 | 59.3 | 28189.7 | 2.26 | 0.7 | 0.714 | 0.95 | 0.711 | 0.032 |
| meshecho-calibrated | 0.272 | 0.281 | 62.6 | 28886.0 | 2.61 | 0.5 | 1.000 | 1.00 | 0.735 | 0.041 |
| prr-product-mesh | 0.272 | 0.278 | 61.1 | 28221.5 | 2.61 | 0.5 | 1.000 | 0.95 | 0.729 | 0.041 |
| meshecho-ack-evict | 0.252 | 0.267 | 60.4 | 28708.6 | 2.25 | 0.5 | 0.800 | 0.80 | 0.707 | 0.032 |
| prr-product-ack-evict-mesh | 0.257 | 0.263 | 60.5 | 28050.4 | 2.61 | 0.2 | 1.000 | 0.50 | 0.714 | 0.041 |

## Application Denominators

Counts are totals across seeds; pair ranges are per-seed minima and maxima. ACK and destination counts use observed unicasts as their denominator. In the protocol-results means, each seed has equal weight; pooled flow counts below can imply a different overall ratio when seed-level flow counts vary. The CSV preserves every seed's counts.

| Protocol | Scheduled unicast | Observed unicast | Scheduled distinct pairs/seed | Observed distinct pairs/seed | ACKs / observed unicast | Destinations / observed unicast | Scheduled broadcast |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshecho | 394 | 394 | 4-4 | 4-4 | 96/394 | 103/394 | 0 |
| meshecho-calibrated | 394 | 394 | 4-4 | 4-4 | 106/394 | 110/394 | 0 |
| prr-product-mesh | 394 | 394 | 4-4 | 4-4 | 105/394 | 108/394 | 0 |
| meshecho-ack-evict | 394 | 394 | 4-4 | 4-4 | 96/394 | 102/394 | 0 |
| prr-product-ack-evict-mesh | 394 | 394 | 4-4 | 4-4 | 99/394 | 102/394 | 0 |

## Repeated-Pair Audit

Each seed uses one application trace shared by all protocols. The CSV also preserves `scheduled_pair_counts_json` and the full `scheduled_trace_sha256` for per-pair inspection.

| Seed | Scheduled/observed application unicasts | Selected pairs | Min scheduled unicasts/pair | Min scheduled blocks/pair |
| ---: | ---: | ---: | ---: | ---: |
| 41 | 39/39 | 4 | 9 | 7 |
| 42 | 50/50 | 4 | 12 | 8 |
| 43 | 32/32 | 4 | 8 | 6 |
| 44 | 35/35 | 4 | 8 | 6 |
| 45 | 41/41 | 4 | 10 | 8 |
| 46 | 30/30 | 4 | 7 | 6 |
| 47 | 42/42 | 4 | 10 | 7 |
| 48 | 46/46 | 4 | 11 | 7 |
| 49 | 44/44 | 4 | 11 | 8 |
| 50 | 35/35 | 4 | 8 | 6 |

## Feedback Diagnostics

Counts and energy are means per seed. `Legacy repair events` mix cache expiry and failed discovery; they are not successful repairs. Invalidations after destination DATA are a simulator-only diagnostic of destination-delivered but ACK-unconfirmed flows; they do not prove the path remained valid at timeout and are never policy input.

| Protocol | Route-cache hits | Cache misses | Route discoveries | Discovery successes | Legacy repair events | ACK timeout invalidations | Invalidations after destination DATA | Total energy (J) | Mean ACK delay (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshecho | 1.5 | 37.9 | 15.5 | 12.1 | 11.5 | 0.0 | 0.0 | 115.8 | 1.95 |
| meshecho-calibrated | 1.5 | 37.9 | 16.0 | 12.4 | 12.0 | 0.0 | 0.0 | 122.2 | 2.22 |
| prr-product-mesh | 1.3 | 38.1 | 15.6 | 12.0 | 11.6 | 0.0 | 0.0 | 119.3 | 2.26 |
| meshecho-ack-evict | 1.1 | 38.3 | 15.8 | 12.4 | 8.2 | 3.8 | 0.6 | 117.9 | 1.97 |
| prr-product-ack-evict-mesh | 1.0 | 38.4 | 15.5 | 11.8 | 8.8 | 2.9 | 0.3 | 118.1 | 2.33 |

## Discovery Candidate Audit

Counts are totals across seeds. Each protocol/seed CSV row has `discovery_record_count`, `discovery_candidate_path_total`, `discovery_multi_candidate_count`, `discovery_records_json`, and `discovery_candidate_fingerprints_json`. The JSON record field contains the observed candidate and selected paths for each discovery; fingerprints support paired set comparisons.

| Protocol | Discoveries | Candidate paths | Multi-candidate discoveries |
| --- | ---: | ---: | ---: |
| meshecho | 155 | 751 | 150 |
| meshecho-calibrated | 159 | 753 | 154 |
| prr-product-mesh | 155 | 715 | 150 |
| meshecho-ack-evict | 158 | 764 | 153 |
| prr-product-ack-evict-mesh | 154 | 705 | 149 |

## Paired MeshEcho Comparisons

Differences are MeshEcho minus the named comparator, paired by seed. Entries are mean deltas with two-sided 95% paired confidence intervals.

| Comparison | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshecho-calibrated | -0.022 [-0.138,+0.095] | -0.013 [-0.135,+0.110] | -3.3 [-20.8,+14.2] |
| MeshEcho vs prr-product-mesh | -0.021 [-0.121,+0.079] | -0.009 [-0.117,+0.098] | -1.8 [-16.5,+12.9] |

## Reading the Result

- Direct-link fractions below 0.99 PRR: 0.170; below 0.50 PRR: 0.048.
- This workload intentionally cycles over four connected pairs; route-cache hits and repairs are therefore part of the estimand.
- MeshEcho is compared with PRR-product under shared application traffic. Routed policies use the stated discovery window and timeout-retry budget.
- PRR-product ranks observed routes by multiplying each hop's model-derived PRR from received RREQ SINR, using the same link observation as ETX. It has no retry or fallback; under concurrent traffic, candidate sets can still differ after protocol-specific control/data transmissions.
- The ACK-timeout route-invalidation variant is an optional comparator, not a meshecho-no-* component ablation.
- The calibrated max-min PRR variant ranks paths by the weakest model-inferred RREQ hop PRR, without an extra hop penalty; it is an experimental MeshEcho variant, not a standard baseline.
- The raw route-hop columns should be checked before calling this a multi-hop benchmark. A low multi-hop fraction means the parameter setting is still too easy.
- Route-discovery success and RREP/RREQ transmission ratios are reported because a low discovery success rate indicates a route-discovery stress test, not an isolated data-plane comparison.

## Reproduction

```sh
python3 tools/run_icc_generalization_experiment.py \
  --case feedback_fading_short_ttl \
  --seeds 10 --seed0 41 \
  --out-prefix meshecho_v2_1_24_icc2027_calibrated_dev41_50 \
  --protocol meshecho \
  --protocol meshecho-calibrated \
  --protocol prr-product \
  --protocol meshecho-ack-evict \
  --protocol prr-product-ack-evict
```
