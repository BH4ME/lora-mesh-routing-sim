# Isolated First-Discovery Comparison

- Seeds: 20
- Selected pairs per seed: 24
- Simulations: 2880; one unicast and a fresh simulator per row
- RREQ relay timing: matched across all 6 policies
- MeshEcho route-miss fallback: disabled for this isolation test
- PRR-product: product of model-derived PRR from received RREQ SINR, with no retry or fallback
- `meshcore-like` is the matched-window shortest-candidate source-route comparator
- Pair selection uses an analytical PRR graph only to choose shared source-destination pairs; route policies do not receive that graph

## Candidate Exposure

480/480 pairs had identical candidate sets across all 6 policies.
458 matched pairs exposed at least two candidates.

All recorded candidate sets matched. Selected-path contrasts condition on the same observed choices; ACK and airtime also include route-reply and data-plane behavior.

## Descriptive Outcomes

Each row below is a mean over isolated single-unicast pairs. Pairs in one seed share topology and are not independent statistical replicates.

| Policy | ACK completion | Destination delivery | Airtime per pair (s) |
| --- | ---: | ---: | ---: |
| meshecho | 0.681 | 0.708 | 3.886 |
| meshecho-calibrated | 0.702 | 0.719 | 3.920 |
| etx-mesh | 0.546 | 0.594 | 3.803 |
| prr-product-mesh | 0.700 | 0.715 | 3.923 |
| minhop-mesh | 0.452 | 0.512 | 3.772 |
| meshcore-like | 0.429 | 0.498 | 3.766 |

## Seed-Paired Differences

MeshEcho minus each comparator; each seed contributes one mean over its selected pairs. Intervals are two-sided 95% paired t intervals across seeds, not across individual flows.

| Comparator | ACK delta [95% CI] | Destination delta [95% CI] | Airtime per pair delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| meshecho-calibrated | -0.021 [-0.055,+0.013] | -0.010 [-0.042,+0.021] | -0.034 [-0.046,-0.022] |
| etx-mesh | +0.135 [+0.078,+0.193] | +0.115 [+0.060,+0.169] | +0.083 [+0.064,+0.103] |
| prr-product-mesh | -0.019 [-0.055,+0.017] | -0.006 [-0.039,+0.027] | -0.036 [-0.050,-0.023] |
| minhop-mesh | +0.229 [+0.187,+0.271] | +0.196 [+0.155,+0.237] | +0.114 [+0.097,+0.130] |
| meshcore-like | +0.252 [+0.207,+0.297] | +0.210 [+0.166,+0.254] | +0.120 [+0.104,+0.137] |

## Selected-Path Attribution Check

For pairs where MeshEcho and a comparator selected the same path, the table counts any ACK, destination, or airtime mismatch. Zero mismatches supports a route-choice explanation in this isolated simulator, conditional on identical candidate exposure.

| Comparator | Different selected path | Same selected path | Same-path outcome mismatches |
| --- | ---: | ---: | ---: |
| meshecho-calibrated | 270 | 210 | 0 |
| etx-mesh | 290 | 190 | 0 |
| prr-product-mesh | 275 | 205 | 0 |
| minhop-mesh | 224 | 256 | 0 |
| meshcore-like | 341 | 139 | 0 |

Paired intervals treat seeds, not individual flows, as independent statistical units.
