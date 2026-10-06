# MeshEcho Fair Multi-Hop Probe

This versioned probe is a fairness diagnostic, not a replacement for the original repeated-pair matrix. It removes fixed-pair reuse, uses an independent channel-reception stream, and places the network in a non-saturated multi-hop regime.

- Seeds: `20`
- Nodes / area: `50` / `18000 m square`
- Traffic: `mixed`, `4.0 flows/min`
- MeshEcho timeout-retry budget: `0`
- Route-cache TTL: `600.0 s` in the matched ICC matrix
- PHY: `SF7`, `17.0 dBm`, `n=2.75`, shadow sigma `4.0 dB`
- Pair mode: `random`
- Source-destination pairs: random per flow
- MeshCore-like discovery window: `2.00 s`
- Channel reception RNG: independent from protocol jitter/exploration
- Quality gate: not required for random-pair mode
- Temporal block fading: disabled (static per-link shadowing)

## Link Regime

| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.000044 | 0.030001 | 0.810423 | 0.999589 | 1.000000 | 0.627 | 0.423 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshtastic-like | 0.696 | 1.000 | 38.8 | 12344.5 | 1.67 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |
| meshcore-like | 0.245 | 0.273 | 144.6 | 74552.8 | 2.18 | 9.7 | 0.247 | 1.25 | 0.492 | 0.025 |
| etx-mesh | 0.308 | 0.344 | 98.1 | 48235.8 | 2.36 | 11.5 | 0.322 | 1.33 | 0.580 | 0.025 |
| ett-mesh | 0.308 | 0.344 | 98.1 | 48235.8 | 2.36 | 11.5 | 0.322 | 1.33 | 0.580 | 0.025 |
| minhop-mesh | 0.280 | 0.320 | 96.3 | 46980.9 | 2.38 | 10.1 | 0.302 | 1.32 | 0.506 | 0.025 |
| meshecho | 0.404 | 0.458 | 99.5 | 48649.4 | 2.49 | 12.3 | 0.389 | 1.45 | 0.622 | 0.028 |

## Paired MeshEcho Comparisons

Differences are MeshEcho minus the named baseline, paired by seed. Entries are mean deltas with two-sided 95% paired confidence intervals.

| Comparison | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshcore-like | +0.159 [+0.115,+0.202] | +0.186 [+0.151,+0.220] | -45.1 [-50.0,-40.3] |
| MeshEcho vs etx-mesh | +0.096 [+0.056,+0.136] | +0.115 [+0.070,+0.159] | +1.3 [+0.1,+2.5] |
| MeshEcho vs ett-mesh | +0.096 [+0.056,+0.136] | +0.115 [+0.070,+0.159] | +1.3 [+0.1,+2.5] |
| MeshEcho vs minhop-mesh | +0.124 [+0.078,+0.170] | +0.139 [+0.102,+0.175] | +3.2 [+2.1,+4.2] |
| MeshEcho vs meshtastic-like | -0.292 [-0.357,-0.226] | -0.542 [-0.594,-0.489] | +60.7 [+55.1,+66.3] |

## Reading the Result

- The link distribution is non-degenerate: a substantial fraction of direct links are below 0.99 PRR and below 0.50 PRR.
- Random-pair traffic removes the main cache-reuse advantage of the original eight-pair workload.
- MeshEcho is compared with managed flooding, matched source routing, min-hop, and ETX/ETT quality-metric baselines under the same pair pool and discovery budget.
- MeshEcho component variants are named `meshecho-*` and are reported only as ablations; the separate adaptive firmware line is not part of this ICC evidence.
- The raw route-hop columns should be checked before calling this a multi-hop benchmark. A low multi-hop fraction means the parameter setting is still too easy.
- Route-discovery success and RREP/RREQ transmission ratios are reported because a low discovery success rate indicates a route-discovery stress test, not an isolated data-plane comparison.

## Reproduction

```sh
python3 tools/run_fair_multihop_probe.py
```
