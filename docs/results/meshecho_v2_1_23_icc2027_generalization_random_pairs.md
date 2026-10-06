# MeshEcho Fair Multi-Hop Probe

This probe samples source-destination pairs per flow instead of cycling through a selected pool. Channel reception uses an independent random stream.

- Seeds: `20`
- Nodes / area: `50` / `18000 m square`
- Traffic: `mixed`, `4.0 flows/min`
- MeshEcho timeout-retry budget: `0`
- Route-cache TTL: `600.0 s` in the matched ICC matrix
- PHY: `SF7`, `17.0 dBm`, `n=2.75`, shadow sigma `4.0 dB`
- Pair mode: `random`
- Source-destination pairs: random per flow
- MeshCore-like discovery window: `2.00 s`
- Matched RREQ relay timing: `False`
- Channel reception RNG: independent from protocol jitter/exploration
- Quality gate: not required for random-pair mode
- Temporal block fading: disabled (static per-link shadowing)

## Link Regime

| Direct PRR p05 | p25 | p50 | p75 | p95 | Below 0.99 | Below 0.50 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.000027 | 0.017621 | 0.744882 | 0.999430 | 1.000000 | 0.641 | 0.447 |

## Protocol Results

| Protocol | ACK PDR | Destination PDR | Airtime (s) | Collision failures | P95 ACK delay (s) | Cached routes | Multi-hop route fraction | Mean cached hops | Discovery success | RREP/RREQ TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshtastic-like | 0.736 | 0.995 | 39.7 | 12156.0 | 2.06 | 0.0 | 0.000 | 0.00 | 0.000 | 0.000 |
| meshcore-like | 0.262 | 0.298 | 151.6 | 78271.9 | 2.35 | 10.4 | 0.282 | 1.33 | 0.492 | 0.026 |
| etx-mesh | 0.293 | 0.316 | 103.0 | 50654.9 | 2.40 | 11.6 | 0.368 | 1.44 | 0.541 | 0.026 |
| ett-mesh | 0.293 | 0.316 | 103.0 | 50654.9 | 2.40 | 11.6 | 0.368 | 1.44 | 0.541 | 0.026 |
| minhop-mesh | 0.296 | 0.314 | 100.4 | 49065.8 | 2.34 | 11.3 | 0.291 | 1.30 | 0.536 | 0.025 |
| meshecho | 0.430 | 0.461 | 103.2 | 50247.6 | 2.47 | 14.0 | 0.432 | 1.49 | 0.659 | 0.028 |

## Application Denominators

Counts are totals across seeds; pair ranges are per-seed minima and maxima. ACK and destination counts use observed unicasts as their denominator. In the protocol-results means, each seed has equal weight; pooled flow counts below can imply a different overall ratio when seed-level flow counts vary. The CSV preserves every seed's counts.

| Protocol | Scheduled unicast | Observed unicast | Scheduled distinct pairs/seed | Observed distinct pairs/seed | ACKs / observed unicast | Destinations / observed unicast | Scheduled broadcast |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshtastic-like | 424 | 424 | 16-29 | 16-29 | 310/424 | 421/424 | 421 |
| meshcore-like | 424 | 424 | 16-29 | 16-29 | 112/424 | 127/424 | 421 |
| etx-mesh | 424 | 424 | 16-29 | 16-29 | 126/424 | 136/424 | 421 |
| ett-mesh | 424 | 424 | 16-29 | 16-29 | 126/424 | 136/424 | 421 |
| minhop-mesh | 424 | 424 | 16-29 | 16-29 | 125/424 | 133/424 | 421 |
| meshecho | 424 | 424 | 16-29 | 16-29 | 183/424 | 196/424 | 421 |

## Discovery Candidate Audit

Counts are totals across seeds. Each protocol/seed CSV row has `discovery_record_count`, `discovery_candidate_path_total`, `discovery_multi_candidate_count`, `discovery_records_json`, and `discovery_candidate_fingerprints_json`. The JSON record field contains the observed candidate and selected paths for each discovery; fingerprints support paired set comparisons.

| Protocol | Discoveries | Candidate paths | Multi-candidate discoveries |
| --- | ---: | ---: | ---: |
| meshtastic-like | 0 | 0 | 0 |
| meshcore-like | 420 | 1742 | 384 |
| etx-mesh | 420 | 1751 | 391 |
| ett-mesh | 420 | 1751 | 391 |
| minhop-mesh | 420 | 1789 | 394 |
| meshecho | 420 | 1900 | 397 |

## Paired MeshEcho Comparisons

Differences are MeshEcho minus the named baseline, paired by seed. Entries are mean deltas with two-sided 95% paired confidence intervals.

| Comparison | ACK PDR delta [95% CI] | Destination PDR delta [95% CI] | Airtime delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| MeshEcho vs meshcore-like | +0.168 [+0.119,+0.217] | +0.163 [+0.107,+0.219] | -48.4 [-53.8,-43.0] |
| MeshEcho vs etx-mesh | +0.137 [+0.097,+0.178] | +0.145 [+0.095,+0.194] | +0.2 [-0.9,+1.2] |
| MeshEcho vs ett-mesh | +0.137 [+0.097,+0.178] | +0.145 [+0.095,+0.194] | +0.2 [-0.9,+1.2] |
| MeshEcho vs minhop-mesh | +0.134 [+0.069,+0.199] | +0.146 [+0.077,+0.216] | +2.8 [+1.4,+4.2] |
| MeshEcho vs meshtastic-like | -0.305 [-0.368,-0.243] | -0.534 [-0.597,-0.472] | +63.5 [+57.5,+69.5] |

## Reading the Result

- Direct-link fractions below 0.99 PRR: 0.641; below 0.50 PRR: 0.447.
- Random-pair traffic removes the main cache-reuse advantage of the original eight-pair workload.
- MeshEcho is compared with managed flooding, matched source routing, ETX, ETT, min-hop under shared application traffic. Routed policies use the stated discovery window and timeout-retry budget.
- No MeshEcho component variants were run in this case.
- The raw route-hop columns should be checked before calling this a multi-hop benchmark. A low multi-hop fraction means the parameter setting is still too easy.
- Route-discovery success and RREP/RREQ transmission ratios are reported because a low discovery success rate indicates a route-discovery stress test, not an isolated data-plane comparison.

## Reproduction

```sh
python3 tools/run_icc_generalization_experiment.py \
  --case random_pairs \
  --seeds 20 --seed0 21 \
  --out-prefix meshecho_v2_1_23_icc2027_generalization \
  --protocol meshtastic \
  --protocol meshcore \
  --protocol etx \
  --protocol ett \
  --protocol minhop \
  --protocol meshecho
```
