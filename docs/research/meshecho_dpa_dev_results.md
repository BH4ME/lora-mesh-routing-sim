# MeshEcho-DPA development decision (2026-10-03)

Status: negative joint-gate result. These are development data, not an ICC
manuscript result or an untouched holdout evaluation. Seeds 4001--4040 were
not run.

## Frozen comparison

- Scenario: the `recurring_fading` case in `tools/run_sr_experiment.py`, with
  50 nodes, 600 s traffic generation, a 30 s application deadline, and a
  630 s TX-cost start window.
- Seeds: 6001--6020, with 817 scheduled unicasts per policy. All three
  policies share the same per-seed application-trace and case-config hashes.
- Policies: `meshecho-dpa` (two actually decoded, source-adjacent-diverse ACK
  paths), `meshecho-dpa-fr` (single ACK), and `meshecho-dpa-repeat` (second
  ACK on the first path at the same eligible second-copy event).
- Evidence: `results/meshecho_dpa_research_recurring_fading_dev_20261003.*`.
  The manifest records source and artifact SHA-256 hashes, all independently
  matched after the run. The full pre-run regression had 294 passing tests
  and one skip.

| Policy | Mean deadline ACK PDR | Mean destination PDR | Mean TX airtime (s/run) | Eligible second paths | Seeds with exposure | Total windowed ACK TX |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| DPA | 0.6507 | 0.7836 | 34.08 | 179 | 20 | 1461 |
| Single ACK | 0.5402 | 0.7715 | 40.89 | 0 | 0 | 978 |
| First-path repeat | 0.6764 | 0.8065 | 33.20 | 173 | 20 | 1350 |

The policy means are averages of the 20 seed-level rates and costs. The
scheduled unicast count is identical within each seed; total in-deadline ACK
counts are 532, 448, and 553, respectively. Different subsequent ACK/route
outcomes alter later traffic, so the total number of extra ACK transmissions
need not be equal across the two closed-loop policies.

| Comparator | Paired ACK-PDR difference [nominal 95% CI] | Paired relative TX-airtime change [nominal 95% CI] | Prespecified primary gate |
| --- | ---: | ---: | --- |
| Single ACK | +0.1104 [+0.0455, +0.1753] | -15.0% [-23.3%, -6.7%] | Pass |
| First-path repeat | -0.0258 [-0.0835, +0.0319] | +7.6% [-7.0%, +22.2%] | Fail |

The development exposure condition passes (179 opportunities across all 20
seeds). The joint primary gate fails because DPA does not improve ACK PDR
over same-trigger first-path repeat, and the latter comparison's airtime upper
bound exceeds the predeclared +10% limit. These intervals are marginal,
seed-paired t intervals and are not multiplicity-adjusted. DPA versus single
ACK suggests that extra feedback can help this simulated regime, but the
current data do not isolate a benefit from alternate-path ACK selection.

## Decision

Stop this DPA hypothesis at development. Do not tune its path window or
eligibility threshold on 6001--6020, open holdout 4001--4040, rewrite the
ICC paper around a positive DPA result, or claim multipath-ACK novelty.
A new core algorithm needs a separately recorded mechanism and fresh
development split; matching a simple same-trigger retransmission remains a
necessary control. No physical-device performance is inferred here.
