# Isolated First-Discovery Comparison

- Seeds: 10
- Selected pairs per seed: 24
- Simulations: 1440; one unicast and a fresh simulator per row
- RREQ relay timing: matched across all 6 policies
- MeshEcho route-miss fallback: disabled for this isolation test
- PRR-product: product of model-derived PRR from received RREQ SINR, with no retry or fallback
- `meshcore-like` is the matched-window shortest-candidate source-route comparator
- Pair selection uses an analytical PRR graph only to choose shared source-destination pairs; route policies do not receive that graph

## Candidate Exposure

240/240 pairs had identical candidate sets across all 6 policies.
225 matched pairs exposed at least two candidates.

All recorded candidate sets matched. Selected-path contrasts condition on the same observed choices; ACK and airtime also include route-reply and data-plane behavior.

## Descriptive Outcomes

Each row below is a mean over isolated single-unicast pairs. Pairs in one seed share topology and are not independent statistical replicates.

| Policy | ACK completion | Destination delivery | Airtime per pair (s) |
| --- | ---: | ---: | ---: |
| meshecho | 0.683 | 0.704 | 3.883 |
| meshecho-calibrated | 0.696 | 0.704 | 3.919 |
| etx-mesh | 0.529 | 0.579 | 3.801 |
| prr-product-mesh | 0.692 | 0.700 | 3.917 |
| minhop-mesh | 0.471 | 0.537 | 3.784 |
| meshcore-like | 0.467 | 0.529 | 3.783 |

## Seed-Paired Differences

MeshEcho minus each comparator; each seed contributes one mean over its selected pairs. Intervals are two-sided 95% paired t intervals across seeds, not across individual flows.

| Comparator | ACK delta [95% CI] | Destination delta [95% CI] | Airtime per pair delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| meshecho-calibrated | -0.013 [-0.050,+0.025] | +0.000 [-0.034,+0.034] | -0.035 [-0.050,-0.021] |
| etx-mesh | +0.154 [+0.090,+0.219] | +0.125 [+0.043,+0.207] | +0.082 [+0.066,+0.098] |
| prr-product-mesh | -0.008 [-0.048,+0.031] | +0.004 [-0.034,+0.043] | -0.033 [-0.053,-0.014] |
| minhop-mesh | +0.212 [+0.125,+0.300] | +0.167 [+0.072,+0.261] | +0.099 [+0.074,+0.124] |
| meshcore-like | +0.217 [+0.119,+0.315] | +0.175 [+0.069,+0.281] | +0.100 [+0.073,+0.127] |

## Selected-Path Attribution Check

For pairs where MeshEcho and a comparator selected the same path, the table counts any ACK, destination, or airtime mismatch. Zero mismatches supports a route-choice explanation in this isolated simulator, conditional on identical candidate exposure.

| Comparator | Different selected path | Same selected path | Same-path outcome mismatches |
| --- | ---: | ---: | ---: |
| meshecho-calibrated | 130 | 110 | 0 |
| etx-mesh | 150 | 90 | 0 |
| prr-product-mesh | 133 | 107 | 0 |
| minhop-mesh | 104 | 136 | 0 |
| meshcore-like | 167 | 73 | 0 |

Paired intervals treat seeds, not individual flows, as independent statistical units.
