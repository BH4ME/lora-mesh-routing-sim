# MeshEcho Candidate-Set Audit

Source CSV: `results/meshecho_v2_1_23_icc2027_matched_fixed_once.csv`
Source SHA-256: `d8ce6e5f09535dfe1a119ca701a9c6dab14957a44a84cf2293250d8f3a415cf1`
Seeds: `20`

Candidate paths are compared as sets after pairing by seed and discovery key. The final column counts different route selections only when both policies observed the same set of at least two candidate paths.

| Comparator | Same candidate sets / paired keys | Different selected paths / paired keys | Different selections on same multi-candidate set / eligible keys |
| --- | ---: | ---: | ---: |
| ETX | 148/480 | 320/480 | 95/134 |
| No fallback | 469/480 | 0/480 | 0/445 |
| Budgeted | 147/480 | 227/480 | 62/138 |

## Paired MeshEcho vs Budgeted

Differences are MeshEcho minus budgeted, paired by topology seed. PDR uses integer deliveries divided by observed unicast attempts. Intervals are two-sided 95% t CIs over seed-level differences.

| Metric | Mean difference [95% CI] | Seeds |
| --- | ---: | ---: |
| ACK PDR | +0.119 [+0.082,+0.156] | 20 |
| Destination PDR | +0.075 [+0.030,+0.120] | 20 |
| Airtime (s) | +1.140 [+0.589,+1.691] | 20 |
