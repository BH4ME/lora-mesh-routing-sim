# MeshEcho Fair Multi-Hop Probe

This versioned probe is a fairness diagnostic, not a replacement for the original repeated-pair matrix. It removes fixed-pair reuse, uses an independent channel-reception stream, and places the network in a non-saturated multi-hop regime.

- Seeds: `3`
- Nodes / area: `50` / `18000 m square`
- Traffic: `mixed`, `4.0 flows/min`
- Smart-CALM timeout retries: `0`
- PHY: `SF7`, `17.0 dBm`, `n=2.75`, shadow sigma `4.0 dB`
- Pair mode: `connected-multihop`
- Connected-pair selection: shared link-budget graph with edge PRR >= `0.70`, graph distance `2-4` hops
- Channel reception RNG: independent from protocol jitter/exploration
- Quality gate: PASSED for every seed; direct-link PRR below 0.99 >= `0.10`, pair pool complete, mean graph hops >= `2.00`

## Link Regime

| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.000032 | 0.014824 | 0.766087 | 0.999388 | 1.000000 | 0.641 | 0.445 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshcore-like | 0.037 | 0.074 | 46.8 | 24026.3 | 0.10 | 1.3 | 0.250 | 0.78 | 0.222 | 0.034 |

## Paired Ablation Differences

Differences are Smart-CALM minus the named ablation, paired by seed. The interval is intentionally omitted here; the raw CSV keeps the seed-level values for a separate statistical test.

| Comparison | ACK PDR delta | Destination PDR delta | Airtime delta (s) | Collision-failure delta |
| --- | ---: | ---: | ---: | ---: |

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
