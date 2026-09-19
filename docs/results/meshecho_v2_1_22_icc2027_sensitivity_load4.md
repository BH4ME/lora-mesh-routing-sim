# MeshEcho Fair Multi-Hop Probe

This versioned probe is a fairness diagnostic, not a replacement for the original repeated-pair matrix. It removes fixed-pair reuse, uses an independent channel-reception stream, and places the network in a non-saturated multi-hop regime.

- Seeds: `20`
- Nodes / area: `50` / `8250 m square`
- Traffic: `mixed`, `4.0 flows/min`
- MeshEcho timeout-retry budget: `0`
- Route-cache TTL: `600.0 s` in the matched ICC matrix
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
| meshtastic-like | 0.409 | 0.985 | 50.5 | 23533.8 | 1.57 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |
| meshcore-like | 0.383 | 0.453 | 151.1 | 74270.2 | 2.46 | 11.7 | 0.695 | 1.73 | 0.586 | 0.031 |
| etx-mesh | 0.450 | 0.527 | 107.6 | 51885.8 | 2.46 | 13.3 | 0.757 | 1.80 | 0.674 | 0.033 |
| ett-mesh | 0.450 | 0.527 | 107.6 | 51885.8 | 2.46 | 13.3 | 0.757 | 1.80 | 0.674 | 0.033 |
| minhop-mesh | 0.421 | 0.484 | 106.0 | 51109.3 | 2.44 | 12.3 | 0.704 | 1.73 | 0.621 | 0.031 |
| meshecho | 0.660 | 0.721 | 111.0 | 52336.1 | 2.51 | 16.1 | 0.978 | 2.04 | 0.808 | 0.039 |

## Paired MeshEcho Comparisons

Differences are MeshEcho minus the named baseline, paired by seed. Entries are mean deltas with two-sided 95% paired confidence intervals.

| Comparison | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshcore-like | +0.277 [+0.209,+0.345] | +0.268 [+0.203,+0.333] | -40.1 [-43.6,-36.6] |
| MeshEcho vs etx-mesh | +0.210 [+0.149,+0.272] | +0.194 [+0.141,+0.246] | +3.4 [+2.4,+4.4] |
| MeshEcho vs ett-mesh | +0.210 [+0.149,+0.272] | +0.194 [+0.141,+0.246] | +3.4 [+2.4,+4.4] |
| MeshEcho vs minhop-mesh | +0.240 [+0.179,+0.301] | +0.238 [+0.173,+0.303] | +5.0 [+3.9,+6.2] |
| MeshEcho vs meshtastic-like | +0.251 [+0.175,+0.327] | -0.264 [-0.319,-0.209] | +60.4 [+54.9,+66.0] |

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
