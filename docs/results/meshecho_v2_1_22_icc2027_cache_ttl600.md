# MeshEcho Fair Multi-Hop Probe

This versioned probe deliberately reuses a four-pair connected unicast workload to measure route-cache reuse and route aging. It is a secondary diagnostic, not the primary sparse-flow multi-hop estimand.

- Seeds: `20`
- Nodes / area: `50` / `8250 m square`
- Traffic: `unicast`, `4.0 flows/min`
- MeshEcho timeout-retry budget: `0`
- Route-cache TTL: `600.0 s`
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
| meshcore-like | 0.471 | 0.497 | 20.7 | 7295.9 | 1.41 | 2.2 | 0.864 | 1.79 | 0.550 | 0.033 |
| etx-mesh | 0.577 | 0.601 | 21.9 | 7387.9 | 1.57 | 2.6 | 0.846 | 1.86 | 0.647 | 0.033 |
| ett-mesh | 0.577 | 0.601 | 21.9 | 7387.9 | 1.57 | 2.6 | 0.846 | 1.86 | 0.647 | 0.033 |
| minhop-mesh | 0.480 | 0.506 | 20.6 | 7339.9 | 1.47 | 2.2 | 0.778 | 1.81 | 0.555 | 0.031 |
| meshecho | 0.786 | 0.806 | 25.7 | 7613.5 | 1.96 | 3.4 | 1.000 | 2.04 | 0.811 | 0.039 |

## Paired MeshEcho Comparisons

Differences are MeshEcho minus the named baseline, paired by seed. Entries are mean deltas with two-sided 95% paired confidence intervals.

| Comparison | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshcore-like | +0.315 [+0.206,+0.423] | +0.309 [+0.199,+0.419] | +5.0 [+3.4,+6.7] |
| MeshEcho vs etx-mesh | +0.209 [+0.106,+0.312] | +0.206 [+0.105,+0.307] | +3.8 [+1.9,+5.7] |
| MeshEcho vs ett-mesh | +0.209 [+0.106,+0.312] | +0.206 [+0.105,+0.307] | +3.8 [+1.9,+5.7] |
| MeshEcho vs minhop-mesh | +0.305 [+0.211,+0.400] | +0.300 [+0.204,+0.396] | +5.1 [+3.5,+6.7] |
| MeshEcho vs meshtastic-like | +0.382 [+0.278,+0.486] | -0.175 [-0.257,-0.093] | -25.1 [-28.4,-21.8] |

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
