# MeshEcho Fair Multi-Hop Probe

This versioned probe is a fairness diagnostic, not a replacement for the original repeated-pair matrix. It removes fixed-pair reuse, uses an independent channel-reception stream, and places the network in a non-saturated multi-hop regime.

- Seeds: `10`
- Nodes / area: `50` / `18000 m square`
- Traffic: `mixed`, `4.0 flows/min`
- Smart-CALM timeout retries: `0`
- PHY: `SF7`, `17.0 dBm`, `n=2.75`, shadow sigma `4.0 dB`
- Pair mode: `random`
- Source-destination pairs: random per flow
- Channel reception RNG: independent from protocol jitter/exploration

## Link Regime

| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.000026 | 0.017577 | 0.756816 | 0.999517 | 1.000000 | 0.642 | 0.443 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshtastic-like | 0.680 | 1.000 | 37.3 | 11606.2 | 1.67 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |
| meshcore-like | 0.456 | 0.486 | 139.5 | 70969.4 | 0.56 | 10.8 | 0.102 | 1.13 | 0.539 | 0.026 |
| calm-mesh | 0.413 | 0.479 | 97.5 | 47492.3 | 2.49 | 12.9 | 0.434 | 1.51 | 0.640 | 0.029 |
| smart-calm | 0.489 | 0.557 | 98.7 | 47521.4 | 3.07 | 13.6 | 0.449 | 1.55 | 0.685 | 0.030 |
| smart-calm-static | 0.413 | 0.479 | 97.5 | 47492.3 | 2.49 | 12.9 | 0.434 | 1.51 | 0.640 | 0.029 |
| smart-calm-no-fallback | 0.465 | 0.510 | 96.4 | 46586.2 | 2.75 | 13.5 | 0.422 | 1.53 | 0.679 | 0.030 |
| smart-calm-no-confidence | 0.488 | 0.566 | 97.5 | 47151.5 | 2.97 | 12.8 | 0.328 | 1.35 | 0.639 | 0.027 |

## Paired Ablation Differences

Differences are Smart-CALM minus the named ablation, paired by seed. The interval is intentionally omitted here; the raw CSV keeps the seed-level values for a separate statistical test.

| Comparison | ACK PDR delta | Destination PDR delta | Airtime delta (s) | Collision-failure delta |
| --- | ---: | ---: | ---: | ---: |
| smart-calm vs smart-calm-no-confidence | 0.001 | -0.009 | 1.2 | 369.9 |
| smart-calm vs smart-calm-no-fallback | 0.024 | 0.047 | 2.3 | 935.2 |

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
