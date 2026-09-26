# MeshEcho Fair Multi-Hop Probe

This versioned probe is a fairness diagnostic, not a replacement for the original repeated-pair matrix. It removes fixed-pair reuse, uses an independent channel-reception stream, and places the network in a non-saturated multi-hop regime.

- Seeds: `20`
- Nodes / area: `50` / `10000 m square`
- Traffic: `mixed`, `1.0 flows/min`
- MeshEcho timeout-retry budget: `0`
- Route-cache TTL: `600.0 s` in the matched ICC matrix
- PHY: `SF8`, `17.0 dBm`, `n=2.75`, shadow sigma `4.0 dB`
- Pair mode: `connected-multihop`
- Connected-pair selection: shared link-budget graph with edge PRR >= `0.90`, graph distance `2-4` hops
- MeshCore-like discovery window: `2.00 s`
- Channel reception RNG: independent from protocol jitter/exploration
- Quality gate: PASSED for every seed; direct-link PRR below 0.99 >= `0.10`, pair pool complete, mean graph hops >= `2.00`
- Temporal block fading: disabled (static per-link shadowing)

## Link Regime

| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.621426 | 0.998899 | 0.999995 | 1.000000 | 1.000000 | 0.151 | 0.043 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshtastic-like | 0.434 | 0.980 | 39.2 | 10276.1 | 1.16 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |
| meshcore-like | 0.162 | 0.184 | 70.3 | 16349.7 | 1.88 | 1.9 | 0.632 | 1.35 | 0.324 | 0.026 |
| etx-mesh | 0.202 | 0.225 | 57.9 | 14010.6 | 1.68 | 2.4 | 0.667 | 1.38 | 0.415 | 0.024 |
| ett-mesh | 0.202 | 0.225 | 57.9 | 14010.6 | 1.68 | 2.4 | 0.667 | 1.38 | 0.415 | 0.024 |
| minhop-mesh | 0.164 | 0.255 | 57.7 | 14081.0 | 1.70 | 2.1 | 0.628 | 1.42 | 0.413 | 0.026 |
| meshecho | 0.405 | 0.531 | 61.7 | 14420.0 | 2.39 | 3.6 | 0.904 | 1.93 | 0.722 | 0.038 |

## Paired MeshEcho Comparisons

Differences are MeshEcho minus the named baseline, paired by seed. Entries are mean deltas with two-sided 95% paired confidence intervals.

| Comparison | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshcore-like | +0.243 [+0.121,+0.365] | +0.347 [+0.198,+0.496] | -8.6 [-11.2,-6.0] |
| MeshEcho vs etx-mesh | +0.203 [+0.062,+0.345] | +0.306 [+0.148,+0.464] | +3.8 [+2.2,+5.5] |
| MeshEcho vs ett-mesh | +0.203 [+0.062,+0.345] | +0.306 [+0.148,+0.464] | +3.8 [+2.2,+5.5] |
| MeshEcho vs minhop-mesh | +0.241 [+0.125,+0.357] | +0.276 [+0.124,+0.429] | +4.0 [+2.3,+5.6] |
| MeshEcho vs meshtastic-like | -0.029 [-0.152,+0.094] | -0.449 [-0.597,-0.301] | +22.5 [+17.9,+27.0] |

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
