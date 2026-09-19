# MeshEcho Fair Multi-Hop Probe

This versioned probe is a fairness diagnostic, not a replacement for the original repeated-pair matrix. It removes fixed-pair reuse, uses an independent channel-reception stream, and places the network in a non-saturated multi-hop regime.

- Seeds: `20`
- Nodes / area: `100` / `21000 m square`
- Traffic: `unicast`, `2.0 flows/min`
- MeshEcho timeout-retry budget: `0`
- Route-cache TTL: `600.0 s` in the matched ICC matrix
- PHY: `SF7`, `17.0 dBm`, `n=2.75`, shadow sigma `4.0 dB`
- Pair mode: `connected-multihop`
- Connected-pair selection: shared link-budget graph with edge PRR >= `0.85`, graph distance `3-5` hops
- MeshCore-like discovery window: `4.00 s`
- Channel reception RNG: independent from protocol jitter/exploration
- Quality gate: PASSED for every seed; direct-link PRR below 0.99 >= `0.10`, pair pool complete, mean graph hops >= `3.00`
- Temporal block fading: disabled (static per-link shadowing)

## Link Regime

| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.000004 | 0.002665 | 0.362616 | 0.997065 | 1.000000 | 0.708 | 0.527 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshtastic-like | 0.410 | 0.988 | 32.6 | 22873.3 | 3.55 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |
| meshcore-like | 0.286 | 0.368 | 154.4 | 171318.9 | 4.71 | 10.4 | 1.000 | 2.74 | 0.503 | 0.024 |
| etx-mesh | 0.531 | 0.606 | 156.6 | 171354.1 | 4.75 | 14.4 | 0.997 | 2.87 | 0.691 | 0.026 |
| ett-mesh | 0.531 | 0.606 | 156.6 | 171354.1 | 4.75 | 14.4 | 0.997 | 2.87 | 0.691 | 0.026 |
| minhop-mesh | 0.478 | 0.540 | 155.5 | 171267.8 | 4.74 | 13.2 | 0.992 | 2.74 | 0.639 | 0.024 |
| meshecho | 0.696 | 0.756 | 160.4 | 172728.0 | 4.88 | 16.9 | 1.000 | 3.27 | 0.810 | 0.030 |

## Paired MeshEcho Comparisons

Differences are MeshEcho minus the named baseline, paired by seed. Entries are mean deltas with two-sided 95% paired confidence intervals.

| Comparison | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshcore-like | +0.410 [+0.357,+0.463] | +0.388 [+0.336,+0.440] | +6.0 [+4.7,+7.3] |
| MeshEcho vs etx-mesh | +0.165 [+0.120,+0.210] | +0.150 [+0.103,+0.197] | +3.9 [+2.2,+5.5] |
| MeshEcho vs ett-mesh | +0.165 [+0.120,+0.210] | +0.150 [+0.103,+0.197] | +3.9 [+2.2,+5.5] |
| MeshEcho vs minhop-mesh | +0.218 [+0.163,+0.274] | +0.216 [+0.169,+0.264] | +5.0 [+3.6,+6.3] |
| MeshEcho vs meshtastic-like | +0.286 [+0.223,+0.349] | -0.232 [-0.278,-0.185] | +127.8 [+117.7,+137.9] |

## Reading the Result

- The link distribution is non-degenerate: a substantial fraction of direct links are below 0.99 PRR and below 0.50 PRR.
- Connected-multihop traffic uses a shared pair pool selected from the same static link-budget graph for every protocol.
- MeshEcho is compared with managed flooding, matched source routing, min-hop, and ETX/ETT quality-metric baselines under the same pair pool and discovery budget.
- MeshEcho component variants are named `meshecho-*` and are reported only as ablations; the separate adaptive firmware line is not part of this ICC evidence.
- The raw route-hop columns should be checked before calling this a multi-hop benchmark. A low multi-hop fraction means the parameter setting is still too easy.
- Route-discovery success and RREP/RREQ transmission ratios are reported because a low discovery success rate indicates a route-discovery stress test, not an isolated data-plane comparison.

## Reproduction

```sh
python3 tools/run_fair_multihop_probe.py
```
