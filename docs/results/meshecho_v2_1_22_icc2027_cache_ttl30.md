# MeshEcho Fair Multi-Hop Probe

This versioned probe deliberately reuses a four-pair connected unicast workload to measure route-cache reuse and route aging. It is a secondary diagnostic, not the primary sparse-flow multi-hop estimand.

- Seeds: `20`
- Nodes / area: `50` / `8250 m square`
- Traffic: `unicast`, `4.0 flows/min`
- MeshEcho timeout-retry budget: `0`
- Route-cache TTL: `30.0 s`
- PHY: `SF7`, `17.0 dBm`, `n=2.75`, shadow sigma `4.0 dB`
- Pair mode: `connected-multihop`
- Connected-pair selection: shared link-budget graph with edge PRR >= `0.90`, graph distance `2-4` hops
- MeshCore-like discovery window: `2.00 s`
- Channel reception RNG: independent from protocol jitter/exploration
- Quality gate: PASSED for every seed; direct-link PRR below 0.99 >= `0.10`, pair pool complete, mean graph hops >= `2.00`
- Temporal block fading: disabled (static per-link shadowing)

## Link Regime

| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.573108 | 0.998611 | 0.999994 | 1.000000 | 1.000000 | 0.160 | 0.046 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshtastic-like | 0.404 | 0.981 | 50.8 | 22959.3 | 1.65 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |
| meshcore-like | 0.158 | 0.170 | 42.2 | 19939.0 | 2.21 | 0.2 | 1.000 | 0.50 | 0.549 | 0.032 |
| etx-mesh | 0.236 | 0.255 | 54.9 | 25745.5 | 2.46 | 0.6 | 1.000 | 1.07 | 0.679 | 0.033 |
| ett-mesh | 0.236 | 0.255 | 54.9 | 25745.5 | 2.46 | 0.6 | 1.000 | 1.07 | 0.679 | 0.033 |
| minhop-mesh | 0.132 | 0.142 | 39.6 | 18818.5 | 2.40 | 0.2 | 1.000 | 0.40 | 0.546 | 0.031 |
| meshecho | 0.472 | 0.490 | 88.5 | 40123.2 | 2.53 | 1.2 | 0.958 | 1.71 | 0.845 | 0.040 |

## Paired MeshEcho Comparisons

Differences are MeshEcho minus the named baseline, paired by seed. Entries are mean deltas with two-sided 95% paired confidence intervals.

| Comparison | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshcore-like | +0.313 [+0.226,+0.401] | +0.320 [+0.231,+0.408] | +46.2 [+33.1,+59.4] |
| MeshEcho vs etx-mesh | +0.236 [+0.145,+0.327] | +0.234 [+0.141,+0.327] | +33.6 [+18.7,+48.5] |
| MeshEcho vs ett-mesh | +0.236 [+0.145,+0.327] | +0.234 [+0.141,+0.327] | +33.6 [+18.7,+48.5] |
| MeshEcho vs minhop-mesh | +0.339 [+0.266,+0.412] | +0.348 [+0.271,+0.424] | +48.9 [+37.4,+60.3] |
| MeshEcho vs meshtastic-like | +0.068 [-0.027,+0.162] | -0.491 [-0.563,-0.420] | +37.6 [+26.1,+49.1] |

## Reading the Result

- The link distribution is non-degenerate: a substantial fraction of direct links are below 0.99 PRR and below 0.50 PRR.
- This workload intentionally cycles over four connected pairs; route-cache hits and repairs are therefore part of the estimand.
- MeshEcho is compared with managed flooding, matched source routing, min-hop, and ETX/ETT quality-metric baselines under the same pair pool and discovery budget.
- MeshEcho component variants are named `meshecho-*` and are reported only as ablations; the separate adaptive firmware line is not part of this ICC evidence.
- The raw route-hop columns should be checked before calling this a multi-hop benchmark. A low multi-hop fraction means the parameter setting is still too easy.
- Route-discovery success and RREP/RREQ transmission ratios are reported because a low discovery success rate indicates a route-discovery stress test, not an isolated data-plane comparison.

## Reproduction

```sh
python3 tools/run_icc_cache_experiment.py
```
