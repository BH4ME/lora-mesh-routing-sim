# MeshEcho Route-Conflict Fairness Audit

This audit checks whether the confidence ablation produces a gain only when the route-quality condition supports it. It is a fairness and sensitivity check, not a general network-performance benchmark.

- Seeds per condition: `100`
- Flows per seed: `24`
- Flow interval: `30.0 s`
- One route-discovery attempt is tracked separately from cache misses.

| Condition | Confidence ACK PDR | No-confidence ACK PDR | Paired delta | Confidence selected long | No-confidence selected short | Paired airtime delta (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| No extra shadowing (`0.0 dB`) | 1.000 +/- 0.000 | 1.000 +/- 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |
| Short branch weak, moderate gap (`5.0 dB`) | 0.980 +/- 0.020 | 0.980 +/- 0.020 | 0.000 | 0.020 | 0.980 | 0.000 |
| Short branch weak, large gap (`7.5 dB`) | 0.999 +/- 0.001 | 0.784 +/- 0.044 | 0.215 | 1.000 | 0.880 | 15.148 |
| Long branch weak, reverse control (`7.5 dB`) | 1.000 +/- 0.000 | 1.000 +/- 0.000 | 0.000 | 0.000 | 1.000 | 0.000 |

## Interpretation

- The null condition should have approximately zero paired delta.
- The short-weak condition is the mechanism case in which confidence is expected to prefer the longer but more reliable route.
- The long-weak reverse condition checks that confidence does not blindly prefer the longer route.
- These controls do not remove the need for random topologies, time-varying links, concurrent traffic, and stronger baselines in the ICC evaluation.
