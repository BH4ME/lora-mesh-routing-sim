# MeshEcho Fair Multi-Hop Probe

This versioned probe is a fairness diagnostic, not a replacement for the original repeated-pair matrix. It removes fixed-pair reuse, uses an independent channel-reception stream, and places the network in a non-saturated multi-hop regime.

- Seeds: `20`
- Nodes / area: `50` / `15000 m square`
- Traffic: `unicast`, `0.5 flows/min`
- PHY: `SF7`, `17.0 dBm`, `n=2.75`, shadow sigma `4.0 dB`
- Pair mode: `connected-multihop`
- Connected-pair selection: shared link-budget graph with edge PRR >= `0.90`, graph distance `2-4` hops
- Channel reception RNG: independent from protocol jitter/exploration

## Link Regime

| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.000540 | 0.244171 | 0.979394 | 0.999966 | 1.000000 | 0.520 | 0.307 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshtastic-like | 0.325 | 1.000 | 1.1 | 350.9 | 0.60 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |
| meshcore-like | 0.050 | 0.050 | 3.6 | 1838.3 | 0.01 | 0.1 | 0.000 | 0.05 | 0.050 | 0.024 |
| calm-mesh | 0.325 | 0.375 | 3.9 | 1904.2 | 0.76 | 0.5 | 1.000 | 1.20 | 0.500 | 0.036 |
| smart-calm | 0.350 | 0.400 | 3.9 | 1913.0 | 5.27 | 0.2 | 1.000 | 0.50 | 0.250 | 0.033 |
| smart-calm-static | 0.650 | 0.925 | 4.4 | 2122.2 | 6.95 | 0.5 | 1.000 | 1.20 | 0.500 | 0.036 |
| smart-calm-no-fallback | 0.250 | 0.250 | 3.8 | 1884.2 | 3.75 | 0.2 | 1.000 | 0.50 | 0.250 | 0.033 |
| smart-calm-no-confidence | 0.225 | 0.300 | 3.8 | 1894.0 | 3.14 | 0.1 | 1.000 | 0.20 | 0.100 | 0.027 |

## Paired Ablation Differences

Differences are Smart-CALM minus the named ablation, paired by seed. The interval is intentionally omitted here; the raw CSV keeps the seed-level values for a separate statistical test.

| Comparison | ACK PDR delta | Destination PDR delta | Airtime delta (s) | Collision-failure delta |
| --- | ---: | ---: | ---: | ---: |
| smart-calm vs smart-calm-no-confidence | 0.125 | 0.100 | 0.1 | 19.0 |
| smart-calm vs smart-calm-no-fallback | 0.100 | 0.150 | 0.1 | 28.9 |

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
