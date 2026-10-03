# MeshEcho Fair Multi-Hop Probe

This probe samples source-destination pairs per flow instead of cycling through a selected pool. Channel reception uses an independent random stream.

- Seeds: `20`
- Nodes / area: `50` / `18000 m square`
- Traffic: `unicast`, `4.0 flows/min`
- MeshEcho timeout-retry budget: `0`
- Route-cache TTL: `600.0 s` in the matched ICC matrix
- PHY: `SF7`, `17.0 dBm`, `n=2.75`, shadow sigma `4.0 dB`
- Pair mode: `random`
- Source-destination pairs: random per flow
- MeshCore-like discovery window: `2.00 s`
- Matched RREQ relay timing: `True`
- Channel reception RNG: independent from protocol jitter/exploration
- Quality gate: not required for random-pair mode

- Temporal block fading: sigma `6.0 dB`, interval `60.0 s`

## Link Regime

| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.000038 | 0.024975 | 0.769220 | 0.999588 | 1.000000 | 0.634 | 0.435 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshecho-calibrated | 0.486 | 0.515 | 152.8 | 76859.8 | 2.61 | 27.6 | 0.750 | 1.96 | 0.689 | 0.035 |
| meshtastic-like | 0.708 | 0.995 | 38.9 | 11542.9 | 1.84 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |
| meshcore-like | 0.381 | 0.408 | 148.4 | 75531.1 | 2.43 | 24.7 | 0.328 | 1.35 | 0.613 | 0.026 |
| prr-product-fallback-mesh | 0.486 | 0.514 | 153.0 | 76950.6 | 2.64 | 27.4 | 0.750 | 1.97 | 0.683 | 0.036 |

## Application Denominators

Counts are totals across seeds; pair ranges are per-seed minima and maxima. ACK and destination counts use observed unicasts as their denominator. In the protocol-results means, each seed has equal weight; pooled flow counts below can imply a different overall ratio when seed-level flow counts vary. The CSV preserves every seed's counts.

| Protocol | Scheduled unicast | Observed unicast | Scheduled distinct pairs/seed | Observed distinct pairs/seed | ACKs / observed unicast | Destinations / observed unicast | Scheduled broadcast |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshecho-calibrated | 813 | 813 | 30-54 | 30-54 | 393/813 | 415/813 | 0 |
| meshtastic-like | 813 | 813 | 30-54 | 30-54 | 573/813 | 809/813 | 0 |
| meshcore-like | 813 | 813 | 30-54 | 30-54 | 306/813 | 328/813 | 0 |
| prr-product-fallback-mesh | 813 | 813 | 30-54 | 30-54 | 395/813 | 416/813 | 0 |

## Discovery Candidate Audit

Counts are totals across seeds. Each protocol/seed CSV row has `discovery_record_count`, `discovery_candidate_path_total`, `discovery_multi_candidate_count`, `discovery_records_json`, and `discovery_candidate_fingerprints_json`. The JSON record field contains the observed candidate and selected paths for each discovery; fingerprints support paired set comparisons.

| Protocol | Discoveries | Candidate paths | Multi-candidate discoveries |
| --- | ---: | ---: | ---: |
| meshecho-calibrated | 804 | 3901 | 766 |
| meshtastic-like | 0 | 0 | 0 |
| meshcore-like | 804 | 3984 | 762 |
| prr-product-fallback-mesh | 804 | 3923 | 763 |

## Reading the Result

- Direct-link fractions below 0.99 PRR: 0.634; below 0.50 PRR: 0.435.
- Random-pair traffic removes the main cache-reuse advantage of the original eight-pair workload.
- The controlled route-conflict experiment is the surgical candidate-selection test.

- PRR-product with matched fallback retains the same path score but enables MeshEcho's TTL-2 route-miss recovery without a same-flow timeout retry.
- The calibrated max-min PRR variant ranks paths by the weakest model-inferred RREQ hop PRR, without an extra hop penalty; it is an experimental MeshEcho variant, not a standard baseline.
- The raw route-hop columns should be checked before calling this a multi-hop benchmark. A low multi-hop fraction means the parameter setting is still too easy.
- Route-discovery success and RREP/RREQ transmission ratios are reported because a low discovery success rate indicates a route-discovery stress test, not an isolated data-plane comparison.

## Reproduction

```sh
python3 tools/run_fair_multihop_probe.py \
  --scenario icc2027_random_sparse_fading_unconditioned \
  --nodes 50 \
  --area-m 18000.0 \
  --duration-s 600.0 \
  --rate-per-min 4.0 \
  --traffic unicast \
  --pair-mode random \
  --pair-count 24 \
  --pair-schedule poisson \
  --edge-prr-threshold 0.7 \
  --min-graph-hops 2 \
  --max-graph-hops 4 \
  --meshcore-discovery-window-s 2.0 \
  --min-selected-pair-mean-graph-hops 2.0 \
  --min-direct-prr-below-0-99 0.1 \
  --sf 7 \
  --tx-power-dbm 17.0 \
  --path-loss-exp 2.75 \
  --shadow-sigma-db 4.0 \
  --temporal-fading-sigma-db 6.0 \
  --temporal-fading-interval-s 60.0 \
  --max-hops 8 \
  --max-timeout-retries 0 \
  --seeds 20 \
  --seed0 2001 \
  --matched-rreq-timing \
  --protocol meshecho-calibrated \
  --protocol meshtastic \
  --protocol meshcore \
  --protocol prr-product-fallback \
  --csv results/meshecho_v2_1_25_icc2027_random_sparse_fading_2001_2020.csv \
  --report docs/results/meshecho_v2_1_25_icc2027_random_sparse_fading_2001_2020.md
```
