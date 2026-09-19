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
- Temporal block fading: sigma `6.0 dB`, interval `60.0 s`

## Link Regime

| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.573108 | 0.998611 | 0.999994 | 1.000000 | 1.000000 | 0.160 | 0.046 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshtastic-like | 0.554 | 0.992 | 46.1 | 19155.8 | 1.59 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |
| meshcore-like | 0.441 | 0.487 | 20.1 | 7135.2 | 1.76 | 3.1 | 0.435 | 1.51 | 0.775 | 0.029 |
| etx-mesh | 0.450 | 0.494 | 20.2 | 7227.6 | 1.78 | 3.1 | 0.435 | 1.50 | 0.770 | 0.028 |
| ett-mesh | 0.450 | 0.494 | 20.2 | 7227.6 | 1.78 | 3.1 | 0.435 | 1.50 | 0.770 | 0.028 |
| minhop-mesh | 0.453 | 0.477 | 20.1 | 7282.0 | 1.83 | 2.9 | 0.500 | 1.44 | 0.708 | 0.029 |
| meshecho | 0.526 | 0.555 | 21.2 | 7214.1 | 1.99 | 3.4 | 0.529 | 1.54 | 0.840 | 0.031 |

## Paired MeshEcho Comparisons

Differences are MeshEcho minus the named baseline, paired by seed. Entries are mean deltas with two-sided 95% paired confidence intervals.

| Comparison | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshcore-like | +0.085 [+0.020,+0.150] | +0.069 [-0.002,+0.140] | +1.1 [+0.1,+2.2] |
| MeshEcho vs etx-mesh | +0.076 [-0.000,+0.152] | +0.061 [-0.024,+0.146] | +0.9 [-0.2,+2.0] |
| MeshEcho vs ett-mesh | +0.076 [-0.000,+0.152] | +0.061 [-0.024,+0.146] | +0.9 [-0.2,+2.0] |
| MeshEcho vs minhop-mesh | +0.072 [-0.012,+0.157] | +0.079 [-0.018,+0.175] | +1.1 [-0.1,+2.3] |
| MeshEcho vs meshtastic-like | -0.028 [-0.106,+0.049] | -0.437 [-0.523,-0.350] | -25.0 [-27.9,-22.0] |

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
