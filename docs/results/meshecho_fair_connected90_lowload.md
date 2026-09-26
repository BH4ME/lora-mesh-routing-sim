# MeshEcho Fair Multi-Hop Probe

This versioned probe is a fairness diagnostic, not a replacement for the original repeated-pair matrix. It removes fixed-pair reuse, uses an independent channel-reception stream, and places the network in a non-saturated multi-hop regime.

- Seeds: `10`
- Nodes / area: `50` / `15000 m square`
- Traffic: `unicast`, `0.5 flows/min`
- PHY: `SF7`, `17.0 dBm`, `n=2.75`, shadow sigma `4.0 dB`
- Pair mode: `connected-multihop`
- Connected-pair selection: shared link-budget graph with edge PRR >= `0.90`, graph distance `2-4` hops
- Channel reception RNG: independent from protocol jitter/exploration

## Link Regime

| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.000323 | 0.168436 | 0.972297 | 0.999960 | 1.000000 | 0.539 | 0.327 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshtastic-like | 0.353 | 1.000 | 5.8 | 1861.6 | 1.64 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |
| meshcore-like | 0.049 | 0.049 | 21.8 | 11053.3 | 0.09 | 0.4 | 0.000 | 0.30 | 0.063 | 0.027 |
| calm-mesh | 0.319 | 0.384 | 23.5 | 11854.4 | 2.23 | 3.5 | 1.000 | 2.09 | 0.579 | 0.036 |
| smart-calm | 0.526 | 0.631 | 24.3 | 11877.9 | 13.83 | 3.0 | 1.000 | 2.16 | 0.462 | 0.037 |
| smart-calm-static | 0.540 | 0.925 | 26.6 | 13094.4 | 15.46 | 2.7 | 1.000 | 1.95 | 0.446 | 0.034 |
| smart-calm-no-fallback | 0.448 | 0.448 | 23.3 | 11550.3 | 14.13 | 3.0 | 1.000 | 2.24 | 0.448 | 0.036 |
| smart-calm-no-confidence | 0.472 | 0.635 | 25.2 | 12537.9 | 13.67 | 1.7 | 0.941 | 1.68 | 0.273 | 0.032 |

## Paired Ablation Differences

Differences are Smart-CALM minus the named ablation, paired by seed. The interval is intentionally omitted here; the raw CSV keeps the seed-level values for a separate statistical test.

| Comparison | ACK PDR delta | Destination PDR delta | Airtime delta (s) | Collision-failure delta |
| --- | ---: | ---: | ---: | ---: |
| smart-calm vs smart-calm-no-confidence | 0.054 | -0.003 | -1.0 | -660.0 |
| smart-calm vs smart-calm-no-fallback | 0.078 | 0.183 | 1.0 | 327.6 |

## Reading the Result

- The link distribution is non-degenerate: a substantial fraction of direct links are below 0.99 PRR and below 0.50 PRR.
- Random-pair traffic removes the main cache-reuse advantage of the original eight-pair workload.
- A positive Smart-CALM result cannot be attributed to confidence ranking alone when it differs from `smart-calm-no-fallback`; timeout recovery must be reported as a separate mechanism.
- The raw route-hop columns should be checked before calling this a multi-hop benchmark. A low multi-hop fraction means the parameter setting is still too easy.
- Route-discovery success and RREP/RREQ transmission ratios are reported because a low discovery success rate indicates a route-discovery stress test, not an isolated data-plane comparison.

## Reproduction

```sh
python3 tools/run_fair_multihop_probe.py
```
