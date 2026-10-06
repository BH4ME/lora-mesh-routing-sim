# Isolated First-Discovery Comparison

- Seeds: 20
- Selected pairs per seed: 24
- Simulations: 1920; one unicast and a fresh simulator per row
- RREQ relay timing: matched across the four policies
- MeshEcho route-miss fallback: disabled for this isolation test
- `meshcore-like` is the matched-window shortest-candidate source-route comparator
- Pair selection uses an analytical PRR graph only to choose shared source-destination pairs; route policies do not receive that graph

## Candidate Exposure

480/480 pairs had identical candidate sets across all four policies.
447 matched pairs exposed at least two candidates.

All recorded candidate sets matched. Selected-path contrasts condition on the same observed choices; ACK and airtime also include route-reply and data-plane behavior.

## Descriptive Outcomes

Each row below is a mean over isolated single-unicast pairs. Pairs in one seed share topology and are not independent statistical replicates.

| Policy | ACK completion | Destination delivery | Airtime per pair (s) |
| --- | ---: | ---: | ---: |
| meshecho | 0.688 | 0.706 | 3.884 |
| etx-mesh | 0.525 | 0.573 | 3.791 |
| minhop-mesh | 0.458 | 0.517 | 3.769 |
| meshcore-like | 0.433 | 0.496 | 3.762 |

## Seed-Paired Differences

MeshEcho minus each comparator; each seed contributes one mean over its selected pairs. Intervals are two-sided 95% paired t intervals across seeds, not across individual flows.

| Comparator | ACK delta [95% CI] | Destination delta [95% CI] | Airtime per pair delta (s) [95% CI] |
| --- | ---: | ---: | ---: |
| etx-mesh | +0.163 [+0.121,+0.204] | +0.133 [+0.085,+0.182] | +0.094 [+0.078,+0.110] |
| minhop-mesh | +0.229 [+0.183,+0.275] | +0.190 [+0.139,+0.240] | +0.116 [+0.098,+0.133] |
| meshcore-like | +0.254 [+0.209,+0.300] | +0.210 [+0.159,+0.262] | +0.122 [+0.105,+0.139] |

## Selected-Path Attribution Check

For pairs where MeshEcho and a comparator selected the same path, the table counts any ACK, destination, or airtime mismatch. Zero mismatches supports a route-choice explanation in this isolated simulator, conditional on identical candidate exposure.

| Comparator | Different selected path | Same selected path | Same-path outcome mismatches |
| --- | ---: | ---: | ---: |
| etx-mesh | 311 | 169 | 0 |
| minhop-mesh | 230 | 250 | 0 |
| meshcore-like | 330 | 150 | 0 |

Paired intervals treat seeds, not individual flows, as independent statistical units.
