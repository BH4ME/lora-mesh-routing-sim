# MeshEcho Fair Multi-Hop Probe

This probe cycles through a selected connected-pair pool on a Poisson application schedule. Pairs may repeat, and some selected pairs may not be observed. Channel reception uses an independent random stream.

- Seeds: `20`
- Nodes / area: `100` / `21000 m square`
- Traffic: `unicast`, `2.0 flows/min`
- MeshEcho timeout-retry budget: `0`
- Route-cache TTL: `600.0 s` in the matched ICC matrix
- PHY: `SF7`, `17.0 dBm`, `n=2.75`, shadow sigma `4.0 dB`
- Pair mode: `connected-multihop`
- Connected-pair selection: shared link-budget graph with edge PRR >= `0.85`, graph distance `3-5` hops
- MeshCore-like discovery window: `4.00 s`
- Matched RREQ relay timing: `False`
- Channel reception RNG: independent from protocol jitter/exploration
- Quality gate: PASSED for every seed; direct-link PRR below 0.99 >= `0.10`, pair pool complete, mean graph hops >= `3.00`
- Temporal block fading: disabled (static per-link shadowing)

## Link Regime

| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.000003 | 0.001801 | 0.278727 | 0.996102 | 1.000000 | 0.718 | 0.543 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshtastic-like | 0.389 | 0.992 | 30.5 | 21401.7 | 3.28 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |
| meshcore-like | 0.310 | 0.385 | 149.2 | 166029.4 | 4.70 | 10.4 | 1.000 | 2.73 | 0.531 | 0.024 |
| etx-mesh | 0.551 | 0.621 | 151.6 | 166024.5 | 4.75 | 14.4 | 0.993 | 2.85 | 0.719 | 0.026 |
| ett-mesh | 0.551 | 0.621 | 151.6 | 166024.5 | 4.75 | 14.4 | 0.993 | 2.85 | 0.719 | 0.026 |
| minhop-mesh | 0.441 | 0.510 | 150.7 | 166577.4 | 4.70 | 13.1 | 0.989 | 2.74 | 0.650 | 0.024 |
| meshecho | 0.724 | 0.758 | 154.9 | 166157.5 | 4.88 | 15.9 | 1.000 | 3.41 | 0.796 | 0.032 |

## Application Denominators

Counts are totals across seeds; pair ranges are per-seed minima and maxima. ACK and destination counts use observed unicasts as their denominator. In the protocol-results means, each seed has equal weight; pooled flow counts below can imply a different overall ratio when seed-level flow counts vary. The CSV preserves every seed's counts.

| Protocol | Scheduled unicast | Observed unicast | Scheduled distinct pairs/seed | Observed distinct pairs/seed | ACKs / observed unicast | Destinations / observed unicast | Scheduled broadcast |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshtastic-like | 418 | 418 | 12-24 | 12-24 | 162/418 | 414/418 | 0 |
| meshcore-like | 418 | 418 | 12-24 | 12-24 | 127/418 | 157/418 | 0 |
| etx-mesh | 418 | 418 | 12-24 | 12-24 | 227/418 | 256/418 | 0 |
| ett-mesh | 418 | 418 | 12-24 | 12-24 | 227/418 | 256/418 | 0 |
| minhop-mesh | 418 | 418 | 12-24 | 12-24 | 181/418 | 211/418 | 0 |
| meshecho | 418 | 418 | 12-24 | 12-24 | 300/418 | 315/418 | 0 |

## Discovery Candidate Audit

Counts are totals across seeds. Each protocol/seed CSV row has `discovery_record_count`, `discovery_candidate_path_total`, `discovery_multi_candidate_count`, `discovery_records_json`, and `discovery_candidate_fingerprints_json`. The JSON record field contains the observed candidate and selected paths for each discovery; fingerprints support paired set comparisons.

| Protocol | Discoveries | Candidate paths | Multi-candidate discoveries |
| --- | ---: | ---: | ---: |
| meshtastic-like | 0 | 0 | 0 |
| meshcore-like | 403 | 2341 | 400 |
| etx-mesh | 403 | 2374 | 398 |
| ett-mesh | 403 | 2374 | 398 |
| minhop-mesh | 403 | 2390 | 398 |
| meshecho | 403 | 2251 | 394 |

## Paired MeshEcho Comparisons

Differences are MeshEcho minus the named baseline, paired by seed. Entries are mean deltas with two-sided 95% paired confidence intervals.

| Comparison | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshcore-like | +0.414 [+0.379,+0.448] | +0.373 [+0.330,+0.416] | +5.7 [+4.1,+7.3] |
| MeshEcho vs etx-mesh | +0.172 [+0.124,+0.220] | +0.138 [+0.080,+0.195] | +3.3 [+2.3,+4.3] |
| MeshEcho vs ett-mesh | +0.172 [+0.124,+0.220] | +0.138 [+0.080,+0.195] | +3.3 [+2.3,+4.3] |
| MeshEcho vs minhop-mesh | +0.282 [+0.237,+0.327] | +0.248 [+0.211,+0.285] | +4.1 [+2.4,+5.8] |
| MeshEcho vs meshtastic-like | +0.335 [+0.290,+0.380] | -0.234 [-0.275,-0.192] | +124.3 [+113.6,+135.1] |

## Reading the Result

- Direct-link fractions below 0.99 PRR: 0.718; below 0.50 PRR: 0.543.
- Connected-multihop traffic uses a shared pair pool selected from the same static link-budget graph for every protocol.
- MeshEcho is compared with managed flooding, matched source routing, ETX, ETT, min-hop under shared application traffic. Routed policies use the stated discovery window and timeout-retry budget.
- No MeshEcho component variants were run in this case.
- The raw route-hop columns should be checked before calling this a multi-hop benchmark. A low multi-hop fraction means the parameter setting is still too easy.
- Route-discovery success and RREP/RREQ transmission ratios are reported because a low discovery success rate indicates a route-discovery stress test, not an isolated data-plane comparison.

## Reproduction

```sh
python3 tools/run_icc_generalization_experiment.py \
  --case deep_multihop \
  --seeds 20 --seed0 21 \
  --out-prefix meshecho_v2_1_23_icc2027_generalization \
  --protocol meshtastic \
  --protocol meshcore \
  --protocol etx \
  --protocol ett \
  --protocol minhop \
  --protocol meshecho
```
