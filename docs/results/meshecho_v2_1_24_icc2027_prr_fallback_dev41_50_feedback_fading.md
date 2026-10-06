# MeshEcho Fair Multi-Hop Probe

This matched-discovery, repeated-pair feedback workload measures route-cache reuse and recovery across channel time blocks. It is reported separately from the sparse first-discovery experiment.

- Seeds: `10`
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
| 0.544995 | 0.998362 | 0.999991 | 1.000000 | 1.000000 | 0.170 | 0.048 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshecho | 0.535 | 0.578 | 21.4 | 7434.9 | 1.78 | 3.2 | 0.625 | 1.58 | 0.785 | 0.032 |
| meshecho-calibrated | 0.689 | 0.706 | 25.5 | 7421.7 | 2.04 | 3.2 | 0.969 | 2.38 | 0.785 | 0.043 |
| prr-product-mesh | 0.686 | 0.698 | 25.6 | 7404.1 | 2.05 | 3.2 | 0.969 | 2.43 | 0.785 | 0.045 |
| prr-product-fallback-mesh | 0.689 | 0.704 | 25.7 | 7438.1 | 2.05 | 3.2 | 0.969 | 2.43 | 0.785 | 0.045 |

## Application Denominators

Counts are totals across seeds; pair ranges are per-seed minima and maxima. ACK and destination counts use observed unicasts as their denominator. In the protocol-results means, each seed has equal weight; pooled flow counts below can imply a different overall ratio when seed-level flow counts vary. The CSV preserves every seed's counts.

| Protocol | Scheduled unicast | Observed unicast | Scheduled distinct pairs/seed | Observed distinct pairs/seed | ACKs / observed unicast | Destinations / observed unicast | Scheduled broadcast |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshecho | 394 | 394 | 4-4 | 4-4 | 214/394 | 232/394 | 0 |
| meshecho-calibrated | 394 | 394 | 4-4 | 4-4 | 274/394 | 281/394 | 0 |
| prr-product-mesh | 394 | 394 | 4-4 | 4-4 | 273/394 | 278/394 | 0 |
| prr-product-fallback-mesh | 394 | 394 | 4-4 | 4-4 | 274/394 | 280/394 | 0 |

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
| meshecho | 28.6 | 10.8 | 4.1 | 3.2 | 0.1 | 0.0 | 0.0 | 42.3 | 0.46 |
| meshecho-calibrated | 28.4 | 11.0 | 4.1 | 3.2 | 0.1 | 0.0 | 0.0 | 50.7 | 0.57 |
| prr-product-mesh | 28.4 | 11.0 | 4.1 | 3.2 | 0.1 | 0.0 | 0.0 | 51.0 | 0.58 |
| prr-product-fallback-mesh | 28.4 | 11.0 | 4.1 | 3.2 | 0.1 | 0.0 | 0.0 | 51.2 | 0.58 |

## Discovery Candidate Audit

Counts are totals across seeds. Each protocol/seed CSV row has `discovery_record_count`, `discovery_candidate_path_total`, `discovery_multi_candidate_count`, `discovery_records_json`, and `discovery_candidate_fingerprints_json`. The JSON record field contains the observed candidate and selected paths for each discovery; fingerprints support paired set comparisons.

| Protocol | Discoveries | Candidate paths | Multi-candidate discoveries |
| --- | ---: | ---: | ---: |
| meshecho | 41 | 192 | 39 |
| meshecho-calibrated | 41 | 190 | 39 |
| prr-product-mesh | 41 | 187 | 39 |
| prr-product-fallback-mesh | 41 | 187 | 39 |

## Paired MeshEcho Comparisons

Differences are MeshEcho minus the named comparator, paired by seed. Entries are mean deltas with two-sided 95% paired confidence intervals.

| Comparison | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshecho-calibrated | -0.154 [-0.256,-0.052] | -0.128 [-0.241,-0.015] | -4.1 [-6.1,-2.1] |
| MeshEcho vs prr-product-mesh | -0.151 [-0.255,-0.047] | -0.120 [-0.234,-0.005] | -4.3 [-6.4,-2.1] |
| MeshEcho vs prr-product-fallback-mesh | -0.154 [-0.256,-0.052] | -0.125 [-0.238,-0.013] | -4.3 [-6.4,-2.3] |

## Reading the Result

- Direct-link fractions below 0.99 PRR: 0.170; below 0.50 PRR: 0.048.
- This workload intentionally cycles over four connected pairs; route-cache hits and legacy repair events are part of the estimand.
- MeshEcho is compared with PRR-product, PRR-product with matched fallback under shared application traffic. Routed policies use the stated discovery window and timeout-retry budget.
- PRR-product ranks observed routes by multiplying each hop's model-derived PRR from received RREQ SINR, using the same link observation as ETX. The standard comparator has no retry or fallback; under concurrent traffic, candidate sets can still differ after protocol-specific control/data transmissions.
- PRR-product with matched fallback retains the same path score but enables MeshEcho's TTL-2 route-miss recovery without a same-flow timeout retry.
- The calibrated max-min PRR variant ranks paths by the weakest model-inferred RREQ hop PRR, without an extra hop penalty; it is an experimental MeshEcho variant, not a standard baseline.
- The raw route-hop columns should be checked before calling this a multi-hop benchmark. A low multi-hop fraction means the parameter setting is still too easy.
- Route-discovery success and RREP/RREQ transmission ratios are reported because a low discovery success rate indicates a route-discovery stress test, not an isolated data-plane comparison.

## Reproduction

```sh
python3 tools/run_icc_generalization_experiment.py \
  --case feedback_fading \
  --seeds 10 --seed0 41 \
  --out-prefix meshecho_v2_1_24_icc2027_prr_fallback_dev41_50 \
  --protocol meshecho \
  --protocol meshecho-calibrated \
  --protocol prr-product \
  --protocol prr-product-fallback
```
