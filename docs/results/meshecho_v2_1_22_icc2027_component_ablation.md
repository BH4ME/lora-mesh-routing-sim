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
| meshecho | 0.720 | 0.739 | 28.1 | 13232.5 | 2.33 | 4.5 | 0.989 | 2.03 | 0.891 | 0.040 |
| meshecho-no-confidence | 0.572 | 0.635 | 27.7 | 13228.5 | 2.32 | 3.7 | 0.757 | 1.81 | 0.775 | 0.033 |
| meshecho-no-fallback | 0.720 | 0.732 | 28.1 | 13200.5 | 2.33 | 4.5 | 0.989 | 2.03 | 0.891 | 0.040 |
| meshecho-no-hop-penalty | 0.669 | 0.696 | 28.3 | 13285.4 | 2.42 | 4.3 | 0.989 | 2.22 | 0.854 | 0.043 |
| meshecho-no-age-penalty | 0.720 | 0.739 | 28.1 | 13232.5 | 2.33 | 4.5 | 0.989 | 2.03 | 0.891 | 0.040 |

## Paired MeshEcho Comparisons

Differences are MeshEcho minus the named baseline, paired by seed. Entries are mean deltas with two-sided 95% paired confidence intervals.

| Comparison | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |

## MeshEcho Component Ablations

These paired rows isolate MeshEcho components while keeping the topology, traffic, discovery budget, and reception stream unchanged.

| Ablation | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshecho-no-confidence | +0.148 [+0.052,+0.244] | +0.104 [-0.014,+0.222] | +0.4 [+0.0,+0.8] |
| MeshEcho vs meshecho-no-fallback | +0.000 [+0.000,+0.000] | +0.007 [-0.008,+0.022] | +0.1 [-0.1,+0.2] |
| MeshEcho vs meshecho-no-hop-penalty | +0.050 [-0.029,+0.130] | +0.043 [-0.044,+0.131] | -0.2 [-0.4,+0.0] |
| MeshEcho vs meshecho-no-age-penalty | +0.000 [+0.000,+0.000] | +0.000 [+0.000,+0.000] | +0.0 [+0.0,+0.0] |

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
