# MeshEcho Fair Multi-Hop Probe

This versioned probe is a fairness diagnostic, not a replacement for the original repeated-pair matrix. It removes fixed-pair reuse, uses an independent channel-reception stream, and places the network in a non-saturated multi-hop regime.

- Seeds: `20`
- Nodes / area: `50` / `8250 m square`
- Traffic: `mixed`, `1.0 flows/min`
- Smart-CALM timeout retries: `0`
- PHY: `SF7`, `17.0 dBm`, `n=2.75`, shadow sigma `4.0 dB`
- Pair mode: `connected-multihop`
- Connected-pair selection: shared link-budget graph with edge PRR >= `0.90`, graph distance `2-4` hops
- MeshCore-like discovery window: `2.00 s`
- Channel reception RNG: independent from protocol jitter/exploration
- Quality gate: PASSED for every seed; direct-link PRR below 0.99 >= `0.10`, pair pool complete, mean graph hops >= `2.00`

## Link Regime

| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.573108 | 0.998611 | 0.999994 | 1.000000 | 1.000000 | 0.160 | 0.046 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshtastic-like | 0.371 | 1.000 | 12.0 | 5544.1 | 0.78 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |
| meshcore-like | 0.537 | 0.679 | 38.5 | 18784.8 | 2.44 | 3.5 | 0.775 | 1.80 | 0.741 | 0.033 |
| calm-mesh | 0.720 | 0.739 | 28.1 | 13238.4 | 2.33 | 4.5 | 0.989 | 2.03 | 0.891 | 0.040 |
| smart-calm | 0.563 | 0.630 | 28.6 | 13636.1 | 2.39 | 4.0 | 1.000 | 2.13 | 0.801 | 0.040 |
| smart-calm-static | 0.720 | 0.739 | 28.1 | 13238.4 | 2.33 | 4.5 | 0.989 | 2.03 | 0.891 | 0.040 |
| smart-calm-no-fallback | 0.561 | 0.607 | 28.0 | 13360.1 | 2.34 | 4.0 | 1.000 | 2.11 | 0.811 | 0.040 |
| smart-calm-no-confidence | 0.382 | 0.470 | 27.8 | 13429.2 | 1.79 | 3.1 | 0.730 | 1.61 | 0.589 | 0.031 |

## Paired Ablation Differences

Differences are Smart-CALM minus the named ablation, paired by seed. The interval is intentionally omitted here; the raw CSV keeps the seed-level values for a separate statistical test.

| Comparison | ACK PDR delta | Destination PDR delta | Airtime delta (s) | Collision-failure delta |
| --- | ---: | ---: | ---: | ---: |
| smart-calm vs smart-calm-no-confidence | 0.181 | 0.159 | 0.7 | 206.8 |
| smart-calm vs smart-calm-no-fallback | 0.002 | 0.023 | 0.5 | 275.9 |

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
