# MeshEcho Fair Multi-Hop Probe

This one-shot multihop workload sends one unicast for each selected directed pair. It measures first-discovery behavior with no repeated source-destination pair.

- Seeds: `20`
- Nodes / area: `50` / `8250 m square`
- Traffic: `unicast`, `2.4 scheduled flows/min` (`fixed-once`)
- MeshEcho timeout-retry budget: `0`
- Route-cache TTL: `600.0 s` in the matched ICC matrix
- PHY: `SF7`, `17.0 dBm`, `n=2.75`, shadow sigma `4.0 dB`
- Pair mode: `connected-multihop`
- Connected-pair selection: shared link-budget graph with edge PRR >= `0.90`, graph distance `2-4` hops
- MeshCore-like discovery window: `2.00 s`
- Matched RREQ relay timing: `True`
- Channel reception RNG: independent from protocol jitter/exploration
- Quality gate: PASSED for every seed; direct-link PRR below 0.99 >= `0.10`, pair pool complete, mean graph hops >= `2.00`
- Temporal block fading: disabled (static per-link shadowing)

## Link Regime

| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.503711 | 0.997692 | 0.999990 | 1.000000 | 1.000000 | 0.176 | 0.052 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshecho | 0.692 | 0.708 | 93.3 | 43540.8 | 2.51 | 19.9 | 0.997 | 2.06 | 0.829 | 0.041 |
| meshecho-budgeted | 0.573 | 0.633 | 92.2 | 43685.6 | 2.50 | 18.4 | 0.826 | 1.86 | 0.767 | 0.035 |
| meshecho-no-confidence | 0.479 | 0.540 | 90.9 | 43473.2 | 2.47 | 16.7 | 0.647 | 1.68 | 0.696 | 0.031 |
| meshecho-no-fallback | 0.690 | 0.704 | 93.3 | 43523.3 | 2.51 | 19.8 | 0.997 | 2.07 | 0.825 | 0.041 |
| meshecho-no-hop-penalty | 0.681 | 0.710 | 94.4 | 43658.7 | 2.66 | 20.1 | 0.995 | 2.31 | 0.838 | 0.044 |
| meshecho-no-age-penalty | 0.692 | 0.708 | 93.3 | 43540.8 | 2.51 | 19.9 | 0.997 | 2.06 | 0.829 | 0.041 |
| meshcore-like | 0.425 | 0.494 | 90.5 | 43323.6 | 2.47 | 15.2 | 0.678 | 1.73 | 0.633 | 0.031 |
| etx-mesh | 0.554 | 0.604 | 91.4 | 43383.4 | 2.48 | 18.4 | 0.717 | 1.76 | 0.767 | 0.033 |
| ett-mesh | 0.554 | 0.604 | 91.4 | 43383.4 | 2.48 | 18.4 | 0.717 | 1.76 | 0.767 | 0.033 |
| minhop-mesh | 0.475 | 0.537 | 90.8 | 43404.3 | 2.47 | 16.7 | 0.653 | 1.69 | 0.696 | 0.031 |
| meshtastic-like | 0.444 | 0.992 | 27.8 | 12425.5 | 1.63 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |

## Application Denominators

Counts are totals across seeds; pair ranges are per-seed minima and maxima. ACK and destination counts use observed unicasts as their denominator. In the protocol-results means, each seed has equal weight; pooled flow counts below can imply a different overall ratio when seed-level flow counts vary. The CSV preserves every seed's counts.

| Protocol | Scheduled unicast | Observed unicast | Scheduled distinct pairs/seed | Observed distinct pairs/seed | ACKs / observed unicast | Destinations / observed unicast | Scheduled broadcast |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshecho | 480 | 480 | 24-24 | 24-24 | 332/480 | 340/480 | 0 |
| meshecho-budgeted | 480 | 480 | 24-24 | 24-24 | 275/480 | 304/480 | 0 |
| meshecho-no-confidence | 480 | 480 | 24-24 | 24-24 | 230/480 | 259/480 | 0 |
| meshecho-no-fallback | 480 | 480 | 24-24 | 24-24 | 331/480 | 338/480 | 0 |
| meshecho-no-hop-penalty | 480 | 480 | 24-24 | 24-24 | 327/480 | 341/480 | 0 |
| meshecho-no-age-penalty | 480 | 480 | 24-24 | 24-24 | 332/480 | 340/480 | 0 |
| meshcore-like | 480 | 480 | 24-24 | 24-24 | 204/480 | 237/480 | 0 |
| etx-mesh | 480 | 480 | 24-24 | 24-24 | 266/480 | 290/480 | 0 |
| ett-mesh | 480 | 480 | 24-24 | 24-24 | 266/480 | 290/480 | 0 |
| minhop-mesh | 480 | 480 | 24-24 | 24-24 | 228/480 | 258/480 | 0 |
| meshtastic-like | 480 | 480 | 24-24 | 24-24 | 213/480 | 476/480 | 0 |

## Discovery Candidate Audit

Counts are totals across seeds. Each protocol/seed CSV row has `discovery_record_count`, `discovery_candidate_path_total`, `discovery_multi_candidate_count`, `discovery_records_json`, and `discovery_candidate_fingerprints_json`. The JSON record field contains the observed candidate and selected paths for each discovery; fingerprints support paired set comparisons.

| Protocol | Discoveries | Candidate paths | Multi-candidate discoveries |
| --- | ---: | ---: | ---: |
| meshecho | 480 | 2063 | 456 |
| meshecho-budgeted | 480 | 1994 | 457 |
| meshecho-no-confidence | 480 | 2001 | 457 |
| meshecho-no-fallback | 480 | 2058 | 456 |
| meshecho-no-hop-penalty | 480 | 2052 | 454 |
| meshecho-no-age-penalty | 480 | 2063 | 456 |
| meshcore-like | 480 | 2029 | 456 |
| etx-mesh | 480 | 2060 | 452 |
| ett-mesh | 480 | 2060 | 452 |
| minhop-mesh | 480 | 1995 | 458 |
| meshtastic-like | 0 | 0 | 0 |

## Paired MeshEcho Comparisons

Differences are MeshEcho minus the named baseline, paired by seed. Entries are mean deltas with two-sided 95% paired confidence intervals.

| Comparison | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshcore-like | +0.267 [+0.208,+0.325] | +0.215 [+0.156,+0.273] | +2.8 [+2.4,+3.2] |
| MeshEcho vs etx-mesh | +0.137 [+0.090,+0.185] | +0.104 [+0.051,+0.157] | +1.9 [+1.6,+2.3] |
| MeshEcho vs ett-mesh | +0.137 [+0.090,+0.185] | +0.104 [+0.051,+0.157] | +1.9 [+1.6,+2.3] |
| MeshEcho vs minhop-mesh | +0.217 [+0.160,+0.273] | +0.171 [+0.112,+0.229] | +2.5 [+2.1,+2.9] |
| MeshEcho vs meshtastic-like | +0.248 [+0.162,+0.334] | -0.283 [-0.342,-0.225] | +65.5 [+64.7,+66.2] |

## MeshEcho Component Ablations

These paired rows isolate MeshEcho components while keeping the topology, traffic, discovery budget, and reception stream unchanged.

| Ablation | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshecho-no-confidence | +0.212 [+0.160,+0.265] | +0.169 [+0.115,+0.223] | +2.4 [+2.0,+2.8] |
| MeshEcho vs meshecho-no-fallback | +0.002 [-0.002,+0.006] | +0.004 [-0.005,+0.013] | +0.0 [-0.1,+0.1] |
| MeshEcho vs meshecho-no-hop-penalty | +0.010 [-0.037,+0.058] | -0.002 [-0.053,+0.049] | -1.1 [-1.6,-0.6] |
| MeshEcho vs meshecho-no-age-penalty | +0.000 [+0.000,+0.000] | +0.000 [+0.000,+0.000] | +0.0 [+0.0,+0.0] |

## Reading the Result

- Direct-link fractions below 0.99 PRR: 0.176; below 0.50 PRR: 0.052.
- Connected-multihop traffic uses a shared pair pool selected from the same static link-budget graph for every protocol.
- MeshEcho is compared with managed flooding, matched source routing, ETX, ETT, min-hop under shared application traffic. Routed policies use the stated discovery window and timeout-retry budget.
- The budgeted variant is an optional comparator; meshecho-no-* variants are component ablations.
- The raw route-hop columns should be checked before calling this a multi-hop benchmark. A low multi-hop fraction means the parameter setting is still too easy.
- Route-discovery success and RREP/RREQ transmission ratios are reported because a low discovery success rate indicates a route-discovery stress test, not an isolated data-plane comparison.

## Reproduction

```sh
python3 tools/run_fair_multihop_probe.py \
  --scenario meshecho_v2_1_23_icc2027_matched_fixed_once \
  --nodes 50 \
  --area-m 8250.0 \
  --duration-s 600.0 \
  --rate-per-min 2.4 \
  --traffic unicast \
  --pair-mode connected-multihop \
  --pair-count 24 \
  --pair-schedule fixed-once \
  --edge-prr-threshold 0.9 \
  --min-graph-hops 2 \
  --max-graph-hops 4 \
  --meshcore-discovery-window-s 2.0 \
  --min-selected-pair-mean-graph-hops 2.0 \
  --min-direct-prr-below-0-99 0.1 \
  --sf 7 \
  --tx-power-dbm 17.0 \
  --path-loss-exp 2.75 \
  --shadow-sigma-db 4.0 \
  --max-hops 7 \
  --max-timeout-retries 0 \
  --seeds 20 \
  --seed0 21 \
  --matched-rreq-timing \
  --protocol meshecho \
  --protocol meshecho-budgeted \
  --protocol meshecho-no-confidence \
  --protocol meshecho-no-fallback \
  --protocol meshecho-no-hop-penalty \
  --protocol meshecho-no-age-penalty \
  --protocol meshcore \
  --protocol etx \
  --protocol ett \
  --protocol minhop \
  --protocol meshtastic \
  --csv results/meshecho_v2_1_23_icc2027_matched_fixed_once.csv \
  --report docs/results/meshecho_v2_1_23_icc2027_matched_fixed_once.md
```
