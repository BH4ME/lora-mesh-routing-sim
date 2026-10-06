# MeshEcho Fair Multi-Hop Probe

This versioned probe deliberately reuses a 4-pair connected unicast workload to measure route-cache reuse and route aging. It is a secondary diagnostic, not the primary sparse-flow multi-hop estimand.

- Seeds: `20`
- Nodes / area: `50` / `8250 m square`
- Traffic: `unicast`, `4.0 flows/min`
- MeshEcho timeout-retry budget: `0`
- Route-cache TTL: `30.0 s`
- PHY: `SF7`, `17.0 dBm`, `n=2.75`, shadow sigma `4.0 dB`
- Pair mode: `connected-multihop`
- Connected-pair selection: shared link-budget graph with edge PRR >= `0.90`, graph distance `2-4` hops
- MeshCore-like discovery window: `2.00 s`
- Matched RREQ relay timing: `False`
- Channel reception RNG: independent from protocol jitter/exploration
- Quality gate: PASSED for every seed; direct-link PRR below 0.99 >= `0.10`, pair pool complete, mean graph hops >= `2.00`
- Temporal block fading: sigma `6.0 dB`, interval `60.0 s`

## Link Regime

| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.503711 | 0.997692 | 0.999990 | 1.000000 | 1.000000 | 0.176 | 0.052 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshtastic-like | 0.561 | 0.993 | 44.7 | 18256.3 | 1.60 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |
| meshcore-like | 0.170 | 0.179 | 44.3 | 21037.5 | 2.43 | 0.2 | 0.500 | 0.30 | 0.629 | 0.029 |
| etx-mesh | 0.235 | 0.243 | 54.8 | 26108.3 | 2.30 | 0.5 | 0.600 | 0.65 | 0.696 | 0.030 |
| ett-mesh | 0.235 | 0.243 | 54.8 | 26108.3 | 2.30 | 0.5 | 0.600 | 0.65 | 0.696 | 0.030 |
| minhop-mesh | 0.173 | 0.194 | 52.7 | 25327.9 | 2.42 | 0.3 | 0.500 | 0.45 | 0.697 | 0.029 |
| meshecho | 0.341 | 0.356 | 71.1 | 33127.9 | 2.47 | 1.2 | 0.542 | 1.32 | 0.825 | 0.033 |

## Application Denominators

Counts are totals across seeds; pair ranges are per-seed minima and maxima. ACK and destination counts use observed unicasts as their denominator. In the protocol-results means, each seed has equal weight; pooled flow counts below can imply a different overall ratio when seed-level flow counts vary. The CSV preserves every seed's counts.

| Protocol | Scheduled unicast | Observed unicast | Scheduled distinct pairs/seed | Observed distinct pairs/seed | ACKs / observed unicast | Destinations / observed unicast | Scheduled broadcast |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshtastic-like | 853 | 853 | 4-4 | 4-4 | 477/853 | 847/853 | 0 |
| meshcore-like | 853 | 853 | 4-4 | 4-4 | 142/853 | 150/853 | 0 |
| etx-mesh | 853 | 853 | 4-4 | 4-4 | 198/853 | 205/853 | 0 |
| ett-mesh | 853 | 853 | 4-4 | 4-4 | 198/853 | 205/853 | 0 |
| minhop-mesh | 853 | 853 | 4-4 | 4-4 | 144/853 | 162/853 | 0 |
| meshecho | 853 | 853 | 4-4 | 4-4 | 286/853 | 299/853 | 0 |

## Discovery Candidate Audit

Counts are totals across seeds. Each protocol/seed CSV row has `discovery_record_count`, `discovery_candidate_path_total`, `discovery_multi_candidate_count`, `discovery_records_json`, and `discovery_candidate_fingerprints_json`. The JSON record field contains the observed candidate and selected paths for each discovery; fingerprints support paired set comparisons.

| Protocol | Discoveries | Candidate paths | Multi-candidate discoveries |
| --- | ---: | ---: | ---: |
| meshtastic-like | 0 | 0 | 0 |
| meshcore-like | 235 | 1200 | 232 |
| etx-mesh | 289 | 1429 | 284 |
| ett-mesh | 289 | 1429 | 284 |
| minhop-mesh | 279 | 1473 | 276 |
| meshecho | 370 | 1935 | 366 |

## Paired MeshEcho Comparisons

Differences are MeshEcho minus the named baseline, paired by seed. Entries are mean deltas with two-sided 95% paired confidence intervals.

| Comparison | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshcore-like | +0.171 [+0.102,+0.241] | +0.177 [+0.105,+0.248] | +26.9 [+16.1,+37.6] |
| MeshEcho vs etx-mesh | +0.106 [+0.032,+0.181] | +0.113 [+0.037,+0.189] | +16.3 [+4.3,+28.3] |
| MeshEcho vs ett-mesh | +0.106 [+0.032,+0.181] | +0.113 [+0.037,+0.189] | +16.3 [+4.3,+28.3] |
| MeshEcho vs minhop-mesh | +0.168 [+0.109,+0.228] | +0.163 [+0.100,+0.226] | +18.4 [+8.5,+28.3] |
| MeshEcho vs meshtastic-like | -0.219 [-0.285,-0.154] | -0.637 [-0.706,-0.568] | +26.4 [+15.9,+36.9] |

## Reading the Result

- Direct-link fractions below 0.99 PRR: 0.176; below 0.50 PRR: 0.052.
- This workload intentionally cycles over four connected pairs; route-cache hits and repairs are therefore part of the estimand.
- MeshEcho is compared with managed flooding, matched source routing, ETX, ETT, min-hop under shared application traffic. Routed policies use the stated discovery window and timeout-retry budget.
- No MeshEcho component variants were run in this case.
- The raw route-hop columns should be checked before calling this a multi-hop benchmark. A low multi-hop fraction means the parameter setting is still too easy.
- Route-discovery success and RREP/RREQ transmission ratios are reported because a low discovery success rate indicates a route-discovery stress test, not an isolated data-plane comparison.

## Reproduction

```sh
python3 tools/run_icc_generalization_experiment.py \
  --case stale_fading_short_ttl \
  --seeds 20 --seed0 21 \
  --out-prefix meshecho_v2_1_23_icc2027_generalization \
  --protocol meshtastic \
  --protocol meshcore \
  --protocol etx \
  --protocol ett \
  --protocol minhop \
  --protocol meshecho
```
