# MeshEcho Route-Conflict Experiment

This controlled experiment isolates candidate-route admission. The short path is `0-1-2-5` and the longer path is `0-3-4-6-5`; an optional extra-shadowing condition weakens one selected branch. Online learning, timeout retry, and route-miss fallback are disabled.

- Seeds: `100`
- Unicast flows per seed: `24`
- Flow interval: `30.0 s`
- Extra shadowing on `1-2`: `7.5 dB`
- Route cache TTL: `1200 s` (one RREQ attempt per run)
- MeshEcho selects the highest-confidence candidate.
- MeshEcho no-confidence selects the shortest candidate.

| Variant | Selected short | Selected long | Both candidates seen | ACK PDR (95% CI) | Destination PDR (95% CI) | P95 ACK delay (95% CI, s) | Airtime (95% CI, s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshecho-confidence | 0.000 | 1.000 | 0.880 | 0.999 +/- 0.001 | 1.000 +/- 0.001 | 1.974 +/- 0.000 | 49.803 +/- 0.028 |
| meshecho-no-confidence | 0.880 | 0.120 | 0.880 | 0.784 +/- 0.044 | 0.858 +/- 0.045 | 2.050 +/- 0.198 | 34.656 +/- 1.918 |

## Paired Difference

Rows are paired by seed. Differences are MeshEcho confidence minus MeshEcho no-confidence.

| Metric | Mean difference | 95% CI |
| --- | ---: | ---: |
| ACK PDR | 0.215 | +/- 0.044 |
| Destination PDR | 0.141 | +/- 0.045 |
| Total airtime (s) | 15.148 | +/- 1.927 |

When both candidates were observed, confidence selected the long reliable path in `1.000` of seeds, while no-confidence selected the short path in `1.000` of seeds.

The route-selection result should be interpreted together with `selected_path`, `candidate_*_confidence`, and the candidate capture columns in the raw CSV. This experiment is deliberately controlled: the confidence estimate and subsequent forwarding use the same static-link model. It should complement, not replace, the random-topology ICC matrix or a time-varying-channel study.

## Fairness Boundary

The companion audit in `meshecho_route_conflict_fairness.md` includes null,
moderate, and reverse controls:

| Condition | Paired ACK-PDR delta |
| --- | ---: |
| No extra shadowing | `0.000` |
| Short branch weak by `5.0 dB` | `0.000` |
| Short branch weak by `7.5 dB` | `+0.215` |
| Long branch weak by `7.5 dB` | `0.000` |

Therefore, the `7.5 dB` result is evidence for the route-selection mechanism
under a deliberately constructed weak-short-path condition, not evidence that
MeshEcho wins in all topologies. The experiment uses one fixed seven-node
topology, zero stochastic shadowing, staggered route-request timing, and a
30-second inter-flow interval; it does not model general congestion or
time-varying channel estimation. The 100 seeds are repeated stochastic trials
on this controlled topology rather than 100 independent topologies.
