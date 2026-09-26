# MeshEcho Route-Conflict Experiment

This controlled experiment isolates candidate-route admission. The short path is `0-1-2-5` and the longer path is `0-3-4-6-5`; an optional extra-shadowing condition weakens one selected branch. Online learning, timeout retry, and route-miss fallback are disabled.

- Seeds: `20`
- Unicast flows per seed: `24`
- Flow interval: `30.0 s`
- Extra shadowing on `1-2`: `7.5 dB`
- Route cache TTL: `1200 s` (one RREQ attempt per run)
- MeshEcho selects the highest-confidence candidate.
- MeshEcho no-confidence selects the shortest candidate.

| Variant | Selected short | Selected long | Both candidates seen | ACK PDR (95% CI) | Destination PDR (95% CI) | P95 ACK delay (95% CI, s) | Airtime (95% CI, s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| meshecho-confidence | 0.000 | 1.000 | 0.900 | 1.000 +/- 0.000 | 1.000 +/- 0.000 | 1.974 +/- 0.000 | 49.826 +/- 0.036 |
| meshecho-no-confidence | 0.900 | 0.100 | 0.900 | 0.779 +/- 0.096 | 0.875 +/- 0.100 | 2.443 +/- 0.555 | 34.809 +/- 4.210 |

## Paired Difference

Rows are paired by seed. Differences are MeshEcho confidence minus MeshEcho no-confidence.

| Metric | Mean difference | 95% CI |
| --- | ---: | ---: |
| ACK PDR | 0.221 | +/- 0.096 |
| Destination PDR | 0.125 | +/- 0.100 |
| Total airtime (s) | 15.017 | +/- 4.230 |

When both candidates were observed, confidence selected the long reliable path in `1.000` of seeds, while no-confidence selected the short path in `1.000` of seeds.

The route-selection result should be interpreted together with `selected_path`, `candidate_*_confidence`, and the candidate capture columns in the raw CSV. This experiment is deliberately controlled: the confidence estimate and subsequent forwarding use the same static-link model. It should complement, not replace, the random-topology ICC matrix or a time-varying-channel study.
