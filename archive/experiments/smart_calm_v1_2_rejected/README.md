# Smart-CALM v1.2 Rejected Candidate

This folder preserves the rejected `smart-calm-sim-v1.2` experiment so future
optimization can avoid repeating the same tradeoff.

## Experiment

- Idea: let Smart-CALM route requests carry the first unicast application
  payload, and use a smaller route-miss fallback TTL.
- Motivation: improve unicast PDR by allowing successful RREQ reception at the
  destination to count as first-packet delivery.
- Decision: not adopted as the active meeting version.

## Result Summary

Compared with accepted `smart-calm-sim-v1.1`, the v1.2 candidate improved PDR
slightly but increased airtime and collisions too much for the current goal.

| Scenario | PDR change vs v1.1 | Airtime change vs v1.1 | Collision change vs v1.1 |
| --- | ---: | ---: | ---: |
| Mixed traffic | `+1.01%` | `+75.78%` | `+23.76%` |
| High shadowing | `+1.95%` | `+87.29%` | `+31.53%` |
| High offered load | `+0.38%` | `+64.74%` | `+21.39%` |

## Interpretation

The piggyback route-request idea is useful as a reliability stress probe, but it
weakens the conference argument because it buys PDR by spending much more
channel time. The accepted v1.1 story is stronger: preserve high PDR while
reducing fallback forwarding, airtime, and collision pressure.

## Files

- `smart_calm_v1_2_50n_mixed.csv`
- `smart_calm_v1_2_50n_mixed_summary.txt`
- `smart_calm_v1_2_50n_mixed_shadow6.csv`
- `smart_calm_v1_2_50n_mixed_shadow6_summary.txt`
- `smart_calm_v1_2_50n_mixed_rate10.csv`
- `smart_calm_v1_2_50n_mixed_rate10_summary.txt`
