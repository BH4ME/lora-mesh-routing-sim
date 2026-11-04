# MeshEcho-LPR development decision (2026-10-03)

Status: negative development result. This is not an ICC manuscript result or
an untouched holdout evaluation. The 4001--4040 holdout seeds were not run.

## Frozen comparison

- Scenario: canonical `recurring_fading` in `tools/run_sr_experiment.py`;
  50 nodes, 600 s generation, 30 s application deadline, 630 s TX-cost
  start window, and 32-byte application payload.
- Seeds: 5001--5020, 20 independent topology/channel seeds, 834 scheduled
  unicasts per policy. All five policies have the same per-seed application
  trace hash and complete case-configuration hash.
- Policies: LPR, F/R-only, same-trigger useful-DATA F, equal-budget periodic
  P, and deterministic unobserved-edge P. Feedback fields and radio model
  are shared. The comparison is within the simulator, not a firmware test.
- Evidence: `results/meshecho_lpr_research_recurring_fading_dev_20261003.*`;
  the manifest records source and artifact SHA-256 hashes. Full regression
  before the run: 250 passed, one skipped.

| Policy | Mean deadline ACK PDR | Mean destination PDR | Mean TX airtime (s/run) | P decisions | ACK-committed inserted paths | PATCH_RELAY TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| LPR | 0.5629 | 0.7880 | 41.69 | 69 | 7 | 207 |
| F/R-only | 0.5548 | 0.7531 | 40.25 | 0 | 0 | 0 |
| Same-trigger F | 0.5244 | 0.7564 | 47.77 | 0 | 0 | 0 |
| Periodic P | 0.5330 | 0.7473 | 41.68 | 70 | 7 | 187 |
| Unobserved-edge P | 0.5672 | 0.7913 | 40.60 | 72 | 7 | 237 |

Paired LPR differences below are seed-level means with nominal two-sided
95% intervals. Relative TX-airtime cost is paired within each seed.

| Comparator | ACK-PDR difference [95% CI] | Relative airtime [95% CI] | Prespecified gate |
| --- | ---: | ---: | --- |
| F/R-only | +0.0081 [-0.0245, +0.0407] | +4.8% [-2.7%, +12.2%] | Fail |
| Same-trigger F | +0.0385 [-0.0003, +0.0772] | -13.1% [-19.8%, -6.4%] | Fail |
| Periodic P | +0.0299 [-0.0073, +0.0671] | +1.7% [-5.1%, +8.5%] | Descriptive |
| Unobserved-edge P | -0.0043 [-0.0184, +0.0099] | +2.8% [-1.5%, +7.2%] | Descriptive |

The predeclared primary rule required the ACK-PDR 95% lower bound above
zero and the relative-airtime 95% upper bound below +10% against **both**
F/R-only and same-trigger F. Neither primary comparison passes. The
predeclared mechanism-sufficiency rule required at least 20 P decisions
and 10 ACK-confirmed inserted paths; the latter also fails (7).
Unobserved-edge P is statistically indistinguishable from LPR on the
reported ACK and airtime intervals, so these data do not isolate a benefit
from ACK-indexed edge selection. The four intervals are marginal, not a
multiplicity-adjusted simultaneous claim.

## Decision

Stop this LPR hypothesis at development. Do not tune its thresholds on
5001--5020, open 4001--4040, rewrite the ICC paper around a positive LPR
claim, or describe these exploratory numbers as confirmatory. A new
algorithm would need a separately frozen mechanism and fresh development
seeds. The largest observed failure mode is low useful-repair yield:
207 candidate-relay transmissions accompany only seven ACK-committed
insertions. Investigate why relays rarely produce usable routes before
choosing a replacement mechanism. A matched classic local-query bypass
baseline is still needed for any superiority claim over prior local repair.
