# MeshEcho Fair Multi-Hop Probe

This versioned probe is a fairness diagnostic, not a replacement for the original repeated-pair matrix. It removes fixed-pair reuse, uses an independent channel-reception stream, and places the network in a non-saturated multi-hop regime.

- Seeds: `20`
- Nodes / area: `50` / `8250 m square`
- Traffic: `mixed`, `4.0 flows/min`
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
| meshtastic-like | 0.409 | 0.985 | 50.5 | 23533.8 | 1.57 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |
| meshcore-like | 0.411 | 0.490 | 151.5 | 74402.8 | 2.45 | 12.3 | 0.683 | 1.70 | 0.622 | 0.031 |
| calm-mesh | 0.652 | 0.711 | 111.3 | 52494.1 | 2.53 | 16.1 | 0.978 | 2.05 | 0.808 | 0.040 |
| smart-calm | 0.605 | 0.675 | 110.9 | 52805.9 | 2.78 | 14.8 | 0.983 | 2.06 | 0.740 | 0.039 |
| smart-calm-static | 0.652 | 0.711 | 111.3 | 52494.1 | 2.53 | 16.1 | 0.978 | 2.05 | 0.808 | 0.040 |
| smart-calm-no-fallback | 0.581 | 0.639 | 109.5 | 52225.0 | 2.57 | 14.7 | 0.983 | 2.04 | 0.741 | 0.039 |
| smart-calm-no-confidence | 0.443 | 0.525 | 109.1 | 52541.6 | 2.92 | 12.6 | 0.653 | 1.68 | 0.623 | 0.030 |

## Paired Ablation Differences

Differences are Smart-CALM minus the named ablation, paired by seed. The interval is intentionally omitted here; the raw CSV keeps the seed-level values for a separate statistical test.

| Comparison | ACK PDR delta | Destination PDR delta | Airtime delta (s) | Collision-failure delta |
| --- | ---: | ---: | ---: | ---: |
| smart-calm vs smart-calm-no-confidence | 0.161 | 0.150 | 1.8 | 264.4 |
| smart-calm vs smart-calm-no-fallback | 0.024 | 0.036 | 1.4 | 581.0 |

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
