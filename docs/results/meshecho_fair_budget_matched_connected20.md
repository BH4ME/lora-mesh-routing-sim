# MeshEcho Fair Multi-Hop Probe

This versioned probe is a fairness diagnostic, not a replacement for the original repeated-pair matrix. It removes fixed-pair reuse, uses an independent channel-reception stream, and places the network in a non-saturated multi-hop regime.

- Seeds: `10`
- Nodes / area: `20` / `15000 m square`
- Traffic: `unicast`, `0.5 flows/min`
- Smart-CALM timeout retries: `0`
- PHY: `SF7`, `17.0 dBm`, `n=2.75`, shadow sigma `4.0 dB`
- Pair mode: `connected-multihop`
- Connected-pair selection: shared link-budget graph with edge PRR >= `0.90`, graph distance `2-4` hops
- Channel reception RNG: independent from protocol jitter/exploration

## Link Regime

| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.000946 | 0.239917 | 0.978146 | 0.999980 | 1.000000 | 0.526 | 0.303 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshtastic-like | 0.715 | 1.000 | 3.9 | 237.2 | 1.62 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |
| meshcore-like | 0.060 | 0.124 | 9.8 | 1402.6 | 0.09 | 1.6 | 0.125 | 0.95 | 0.249 | 0.070 |
| calm-mesh | 0.626 | 0.636 | 11.3 | 1415.0 | 2.65 | 4.8 | 0.958 | 2.17 | 0.730 | 0.098 |
| smart-calm | 0.368 | 0.397 | 10.9 | 1496.6 | 2.41 | 3.7 | 0.973 | 1.86 | 0.540 | 0.087 |
| smart-calm-static | 0.626 | 0.636 | 11.3 | 1415.0 | 2.65 | 4.8 | 0.958 | 2.17 | 0.730 | 0.098 |
| smart-calm-no-fallback | 0.391 | 0.410 | 10.8 | 1468.8 | 2.26 | 3.9 | 0.974 | 1.89 | 0.565 | 0.090 |
| smart-calm-no-confidence | 0.298 | 0.358 | 10.7 | 1450.4 | 2.24 | 3.1 | 0.774 | 1.39 | 0.401 | 0.077 |

## Paired Ablation Differences

Differences are Smart-CALM minus the named ablation, paired by seed. The interval is intentionally omitted here; the raw CSV keeps the seed-level values for a separate statistical test.

| Comparison | ACK PDR delta | Destination PDR delta | Airtime delta (s) | Collision-failure delta |
| --- | ---: | ---: | ---: | ---: |
| smart-calm vs smart-calm-no-confidence | 0.070 | 0.038 | 0.1 | 46.2 |
| smart-calm vs smart-calm-no-fallback | -0.024 | -0.014 | 0.1 | 27.8 |

## Reading the Result

- The link distribution is non-degenerate: a substantial fraction of direct links are below 0.99 PRR and below 0.50 PRR.
- Connected-multihop traffic uses a shared pair pool selected from the same static link-budget graph for every protocol.
- A positive Smart-CALM result cannot be attributed to confidence ranking alone when it differs from `smart-calm-no-fallback`; timeout recovery must be reported as a separate mechanism.
- The raw route-hop columns should be checked before calling this a multi-hop benchmark. A low multi-hop fraction means the parameter setting is still too easy.
- Route-discovery success and RREP/RREQ transmission ratios are reported because a low discovery success rate indicates a route-discovery stress test, not an isolated data-plane comparison.

## Reproduction

```sh
python3 tools/run_fair_multihop_probe.py
```
