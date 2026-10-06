# MeshEcho Fair Multi-Hop Probe

This versioned probe is a fairness diagnostic, not a replacement for the original repeated-pair matrix. It removes fixed-pair reuse, uses an independent channel-reception stream, and places the network in a non-saturated multi-hop regime.

- Seeds: `10`
- Nodes / area: `50` / `18000 m square`
- Traffic: `mixed`, `4.0 flows/min`
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
| smart-calm | 0.687 | 0.783 | 100.3 | 48204.1 | 18.99 | 11.0 | 0.336 | 1.39 | 0.556 | 0.026 |
| smart-calm-static | 0.822 | 0.929 | 103.8 | 49930.8 | 17.13 | 13.0 | 0.446 | 1.54 | 0.653 | 0.029 |
| smart-calm-no-fallback | 0.640 | 0.640 | 97.9 | 47379.7 | 17.27 | 12.8 | 0.437 | 1.52 | 0.637 | 0.029 |
| smart-calm-no-confidence | 0.638 | 0.774 | 100.8 | 48700.4 | 16.77 | 9.8 | 0.245 | 1.24 | 0.499 | 0.025 |

## Paired Ablation Differences

Differences are Smart-CALM minus the named ablation, paired by seed. The interval is intentionally omitted here; the raw CSV keeps the seed-level values for a separate statistical test.

| Comparison | ACK PDR delta | Destination PDR delta | Airtime delta (s) | Collision-failure delta |
| --- | ---: | ---: | ---: | ---: |
| smart-calm vs smart-calm-no-confidence | 0.049 | 0.009 | -0.5 | -496.3 |
| smart-calm vs smart-calm-no-fallback | 0.047 | 0.144 | 2.4 | 824.4 |

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
