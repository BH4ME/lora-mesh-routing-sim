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
- Matched RREQ relay timing: `False`
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
| meshecho | 0.752 | 0.796 | 94.2 | 43268.8 | 2.51 | 20.6 | 0.990 | 2.05 | 0.856 | 0.040 |
| meshecho-no-fallback | 0.740 | 0.773 | 93.6 | 42910.7 | 2.50 | 20.4 | 0.990 | 2.05 | 0.852 | 0.040 |
| meshcore-like | 0.438 | 0.500 | 90.2 | 43315.2 | 2.48 | 14.9 | 0.609 | 1.64 | 0.623 | 0.030 |
| etx-mesh | 0.540 | 0.598 | 91.1 | 43309.9 | 2.47 | 17.5 | 0.706 | 1.73 | 0.729 | 0.032 |
| minhop-mesh | 0.410 | 0.485 | 90.4 | 43387.8 | 2.47 | 15.5 | 0.661 | 1.69 | 0.646 | 0.030 |

## Application Denominators

Counts are totals across seeds; pair ranges are per-seed minima and maxima. ACK and destination counts use observed unicasts as their denominator. In the protocol-results means, each seed has equal weight; pooled flow counts below can imply a different overall ratio when seed-level flow counts vary. The CSV preserves every seed's counts.

| Protocol | Scheduled unicast | Observed unicast | Scheduled distinct pairs/seed | Observed distinct pairs/seed | ACKs / observed unicast | Destinations / observed unicast | Scheduled broadcast |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshecho | 480 | 480 | 24-24 | 24-24 | 361/480 | 382/480 | 0 |
| meshecho-no-fallback | 480 | 480 | 24-24 | 24-24 | 355/480 | 371/480 | 0 |
| meshcore-like | 480 | 480 | 24-24 | 24-24 | 210/480 | 240/480 | 0 |
| etx-mesh | 480 | 480 | 24-24 | 24-24 | 259/480 | 287/480 | 0 |
| minhop-mesh | 480 | 480 | 24-24 | 24-24 | 197/480 | 233/480 | 0 |

## Discovery Candidate Audit

Counts are totals across seeds. Each protocol/seed CSV row has `discovery_record_count`, `discovery_candidate_path_total`, `discovery_multi_candidate_count`, `discovery_records_json`, and `discovery_candidate_fingerprints_json`. The JSON record field contains the observed candidate and selected paths for each discovery; fingerprints support paired set comparisons.

| Protocol | Discoveries | Candidate paths | Multi-candidate discoveries |
| --- | ---: | ---: | ---: |
| meshecho | 480 | 2114 | 455 |
| meshecho-no-fallback | 480 | 2123 | 456 |
| meshcore-like | 480 | 2063 | 457 |
| etx-mesh | 480 | 2058 | 455 |
| minhop-mesh | 480 | 2083 | 455 |

## Paired MeshEcho Comparisons

Differences are MeshEcho minus the named baseline, paired by seed. Entries are mean deltas with two-sided 95% paired confidence intervals.

| Comparison | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshcore-like | +0.315 [+0.255,+0.374] | +0.296 [+0.239,+0.352] | +4.0 [+3.5,+4.6] |
| MeshEcho vs etx-mesh | +0.212 [+0.150,+0.275] | +0.198 [+0.133,+0.263] | +3.1 [+2.4,+3.7] |
| MeshEcho vs minhop-mesh | +0.342 [+0.293,+0.391] | +0.310 [+0.265,+0.355] | +3.8 [+3.3,+4.4] |

## MeshEcho Component Ablations

These paired rows isolate MeshEcho components while keeping the topology, traffic, discovery budget, and reception stream unchanged.

| Ablation | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshecho-no-fallback | +0.013 [-0.002,+0.027] | +0.023 [-0.000,+0.046] | +0.7 [+0.2,+1.1] |

## Reading the Result

- Direct-link fractions below 0.99 PRR: 0.176; below 0.50 PRR: 0.052.
- Connected-multihop traffic uses a shared pair pool selected from the same static link-budget graph for every protocol.
- MeshEcho is compared with matched source routing, ETX, min-hop under shared application traffic. Routed policies use the stated discovery window and timeout-retry budget.
- The meshecho-no-* variants are component ablations.
- The raw route-hop columns should be checked before calling this a multi-hop benchmark. A low multi-hop fraction means the parameter setting is still too easy.
- Route-discovery success and RREP/RREQ transmission ratios are reported because a low discovery success rate indicates a route-discovery stress test, not an isolated data-plane comparison.

## Reproduction

```sh
python3 tools/run_fair_multihop_probe.py \
  --scenario meshecho_v2_1_23_icc2027_native_fixed_once \
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
  --protocol meshecho \
  --protocol meshecho-no-fallback \
  --protocol meshcore \
  --protocol etx \
  --protocol minhop \
  --csv results/meshecho_v2_1_23_icc2027_native_fixed_once.csv \
  --report docs/results/meshecho_v2_1_23_icc2027_native_fixed_once.md
```
