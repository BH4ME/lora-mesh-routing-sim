# MeshEcho Fair Multi-Hop Probe

This versioned probe is a fairness diagnostic, not a replacement for the original repeated-pair matrix. It removes fixed-pair reuse, uses an independent channel-reception stream, and places the network in a non-saturated multi-hop regime.

- Seeds: `20`
- Nodes / area: `50` / `8250 m square`
- Traffic: `mixed`, `1.0 flows/min`
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
| meshtastic-like | 0.371 | 1.000 | 12.0 | 5544.1 | 0.78 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |
| meshcore-like | 0.502 | 0.636 | 38.5 | 18790.7 | 2.32 | 3.5 | 0.803 | 1.82 | 0.720 | 0.034 |
| etx-mesh | 0.661 | 0.741 | 27.6 | 13182.5 | 2.36 | 4.2 | 0.843 | 1.91 | 0.861 | 0.037 |
| ett-mesh | 0.661 | 0.741 | 27.6 | 13182.5 | 2.36 | 4.2 | 0.843 | 1.91 | 0.861 | 0.037 |
| minhop-mesh | 0.419 | 0.435 | 26.9 | 12925.1 | 2.05 | 3.4 | 0.716 | 1.67 | 0.637 | 0.031 |
| meshecho | 0.720 | 0.739 | 28.1 | 13232.5 | 2.33 | 4.5 | 0.989 | 2.03 | 0.891 | 0.040 |

## Paired MeshEcho Comparisons

Differences are MeshEcho minus the named baseline, paired by seed. Entries are mean deltas with two-sided 95% paired confidence intervals.

| Comparison | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshcore-like | +0.218 [+0.041,+0.395] | +0.103 [-0.086,+0.292] | -10.3 [-12.6,-8.1] |
| MeshEcho vs etx-mesh | +0.059 [-0.108,+0.226] | -0.002 [-0.172,+0.168] | +0.5 [+0.2,+0.9] |
| MeshEcho vs ett-mesh | +0.059 [-0.108,+0.226] | -0.002 [-0.172,+0.168] | +0.5 [+0.2,+0.9] |
| MeshEcho vs minhop-mesh | +0.301 [+0.161,+0.441] | +0.304 [+0.170,+0.438] | +1.3 [+0.9,+1.7] |
| MeshEcho vs meshtastic-like | +0.349 [+0.173,+0.525] | -0.261 [-0.376,-0.145] | +16.1 [+12.9,+19.4] |

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
