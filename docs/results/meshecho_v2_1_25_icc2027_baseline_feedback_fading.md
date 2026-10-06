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
| meshecho-calibrated | 0.624 | 0.633 | 23.7 | 7531.4 | 1.80 | 3.0 | 1.000 | 2.31 | 0.722 | 0.042 |
| meshtastic-like | 0.505 | 0.989 | 42.4 | 17621.2 | 1.51 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |
| meshcore-like | 0.410 | 0.448 | 19.5 | 7237.1 | 1.41 | 2.8 | 0.564 | 1.57 | 0.688 | 0.029 |
| prr-product-fallback-mesh | 0.621 | 0.633 | 23.8 | 7535.9 | 1.74 | 3.0 | 1.000 | 2.34 | 0.722 | 0.042 |

## Application Denominators

Counts are totals across seeds; pair ranges are per-seed minima and maxima. ACK and destination counts use observed unicasts as their denominator. In the protocol-results means, each seed has equal weight; pooled flow counts below can imply a different overall ratio when seed-level flow counts vary. The CSV preserves every seed's counts.

| Protocol | Scheduled unicast | Observed unicast | Scheduled distinct pairs/seed | Observed distinct pairs/seed | ACKs / observed unicast | Destinations / observed unicast | Scheduled broadcast |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshecho-calibrated | 793 | 793 | 4-4 | 4-4 | 490/793 | 498/793 | 0 |
| meshtastic-like | 793 | 793 | 4-4 | 4-4 | 400/793 | 784/793 | 0 |
| meshcore-like | 793 | 793 | 4-4 | 4-4 | 328/793 | 357/793 | 0 |
| prr-product-fallback-mesh | 793 | 793 | 4-4 | 4-4 | 488/793 | 498/793 | 0 |

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
| meshecho-calibrated | 26.2 | 13.4 | 4.2 | 3.0 | 0.1 | 0.0 | 0.0 | 47.2 | 0.54 |
| meshtastic-like | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 85.3 | 0.57 |
| meshcore-like | 24.9 | 14.8 | 4.0 | 2.8 | 0.0 | 0.0 | 0.0 | 38.6 | 0.47 |
| prr-product-fallback-mesh | 26.2 | 13.4 | 4.2 | 3.0 | 0.1 | 0.0 | 0.0 | 47.5 | 0.54 |

## Discovery Candidate Audit

Counts are totals across seeds. Each protocol/seed CSV row has `discovery_record_count`, `discovery_candidate_path_total`, `discovery_multi_candidate_count`, `discovery_records_json`, and `discovery_candidate_fingerprints_json`. The JSON record field contains the observed candidate and selected paths for each discovery; fingerprints support paired set comparisons.

| Protocol | Discoveries | Candidate paths | Multi-candidate discoveries |
| --- | ---: | ---: | ---: |
| meshecho-calibrated | 83 | 394 | 76 |
| meshtastic-like | 0 | 0 | 0 |
| meshcore-like | 80 | 369 | 73 |
| prr-product-fallback-mesh | 83 | 395 | 76 |

## Reading the Result

- Direct-link fractions below 0.99 PRR: 0.158; below 0.50 PRR: 0.044.
- This workload intentionally cycles over four connected pairs; route-cache hits and legacy repair events are part of the estimand.
- The controlled route-conflict experiment is the surgical candidate-selection test.

- PRR-product with matched fallback retains the same path score but enables MeshEcho's TTL-2 route-miss recovery without a same-flow timeout retry.
- The calibrated max-min PRR variant ranks paths by the weakest model-inferred RREQ hop PRR, without an extra hop penalty; it is an experimental MeshEcho variant, not a standard baseline.
- The raw route-hop columns should be checked before calling this a multi-hop benchmark. A low multi-hop fraction means the parameter setting is still too easy.
- Route-discovery success and RREP/RREQ transmission ratios are reported because a low discovery success rate indicates a route-discovery stress test, not an isolated data-plane comparison.

## Reproduction

```sh
python3 tools/run_icc_generalization_experiment.py \
  --case feedback_fading \
  --seeds 20 --seed0 51 \
  --out-prefix meshecho_v2_1_25_icc2027_baseline \
  --protocol meshecho-calibrated \
  --protocol meshtastic \
  --protocol meshcore \
  --protocol prr-product-fallback
```
