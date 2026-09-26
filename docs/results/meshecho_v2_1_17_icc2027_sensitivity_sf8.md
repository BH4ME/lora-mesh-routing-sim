# MeshEcho Fair Multi-Hop Probe

This versioned probe is a fairness diagnostic, not a replacement for the original repeated-pair matrix. It removes fixed-pair reuse, uses an independent channel-reception stream, and places the network in a non-saturated multi-hop regime.

- Seeds: `20`
- Nodes / area: `50` / `10000 m square`
- Traffic: `mixed`, `1.0 flows/min`
- Smart-CALM timeout retries: `0`
- PHY: `SF8`, `17.0 dBm`, `n=2.75`, shadow sigma `4.0 dB`
- Pair mode: `connected-multihop`
- Connected-pair selection: shared link-budget graph with edge PRR >= `0.90`, graph distance `2-4` hops
- MeshCore-like discovery window: `2.00 s`
- Channel reception RNG: independent from protocol jitter/exploration
- Quality gate: PASSED for every seed; direct-link PRR below 0.99 >= `0.10`, pair pool complete, mean graph hops >= `2.00`

## Link Regime

| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.621426 | 0.998899 | 0.999995 | 1.000000 | 1.000000 | 0.151 | 0.043 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshtastic-like | 0.434 | 0.980 | 39.2 | 10276.1 | 1.16 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |
| meshcore-like | 0.160 | 0.187 | 70.4 | 16342.0 | 1.73 | 2.1 | 0.667 | 1.34 | 0.340 | 0.027 |
| calm-mesh | 0.435 | 0.557 | 61.7 | 14450.4 | 2.54 | 3.5 | 0.930 | 1.91 | 0.710 | 0.038 |
| smart-calm | 0.402 | 0.462 | 61.4 | 14476.5 | 2.74 | 3.1 | 0.921 | 1.85 | 0.599 | 0.034 |
| smart-calm-static | 0.435 | 0.557 | 61.7 | 14450.4 | 2.54 | 3.5 | 0.930 | 1.91 | 0.710 | 0.038 |
| smart-calm-no-fallback | 0.349 | 0.361 | 59.1 | 13886.3 | 2.41 | 3.0 | 0.918 | 1.86 | 0.576 | 0.034 |
| smart-calm-no-confidence | 0.299 | 0.371 | 59.8 | 14178.2 | 2.41 | 2.7 | 0.574 | 1.53 | 0.506 | 0.027 |

## Paired Ablation Differences

Differences are Smart-CALM minus the named ablation, paired by seed. The interval is intentionally omitted here; the raw CSV keeps the seed-level values for a separate statistical test.

| Comparison | ACK PDR delta | Destination PDR delta | Airtime delta (s) | Collision-failure delta |
| --- | ---: | ---: | ---: | ---: |
| smart-calm vs smart-calm-no-confidence | 0.102 | 0.091 | 1.6 | 298.4 |
| smart-calm vs smart-calm-no-fallback | 0.053 | 0.101 | 2.3 | 590.2 |

## Reading the Result

- The link distribution is non-degenerate: a substantial fraction of direct links are below 0.99 PRR and below 0.50 PRR.
- Connected-multihop traffic uses a shared pair pool selected from the same static link-budget graph for every protocol.
- The Smart-CALM/no-confidence line is a complete disabled-policy comparison because confidence changes route admission and discovery; the controlled route-conflict experiment is the surgical candidate-selection test.
- The raw route-hop columns should be checked before calling this a multi-hop benchmark. A low multi-hop fraction means the parameter setting is still too easy.
- Route-discovery success and RREP/RREQ transmission ratios are reported because a low discovery success rate indicates a route-discovery stress test, not an isolated data-plane comparison.

## Reproduction

```sh
python3 tools/run_fair_multihop_probe.py
```
