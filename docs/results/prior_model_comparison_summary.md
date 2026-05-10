# Smart-CALM Prior Comparison

Evaluation setup: `50 nodes / 3000 m / 1200 s / pair-count 8 / 20 seeds`

Compared priors:
- `lean_balanced`
- `low_state_rescue`
- `reliability_balanced`

## Mixed Traffic

| Model | Unicast PDR | Airtime (s) | Collision failures | Fallback forwards | Policy switches |
| --- | ---: | ---: | ---: | ---: | ---: |
| Lean balanced | 0.945498 | 974.49 | 87589 | 642 | 3.90 |
| Low-state rescue | 0.945768 | 987.83 | 88624 | 718 | 5.55 |
| Reliability balanced | 0.947428 | 977.99 | 88011 | 644 | 3.35 |

## High Shadowing

| Model | Unicast PDR | Airtime (s) | Collision failures | Fallback forwards | Policy switches |
| --- | ---: | ---: | ---: | ---: | ---: |
| Lean balanced | 0.952318 | 963.27 | 86596 | 595 | 4.05 |
| Low-state rescue | 0.951013 | 970.68 | 87221 | 631 | 5.30 |
| Reliability balanced | 0.956881 | 967.76 | 87329 | 614 | 3.35 |

## High Offered Load

| Model | Unicast PDR | Airtime (s) | Collision failures | Fallback forwards | Policy switches |
| --- | ---: | ---: | ---: | ---: | ---: |
| Lean balanced | 0.909254 | 1556.32 | 144461 | 1422 | 6.00 |
| Low-state rescue | 0.924025 | 1553.47 | 144150 | 1405 | 6.90 |
| Reliability balanced | 0.912075 | 1559.01 | 144719 | 1417 | 5.95 |

## Takeaway

- `reliability_balanced` is the best general-purpose prior for mixed and shadowed traffic, with the highest PDR and the fewest policy switches.
- `lean_balanced` is the lightest option under mixed and shadowed load, with slightly lower airtime and collisions.
- `low_state_rescue` is the strongest choice under high offered load, where it gives the best PDR and the lowest airtime/collision among the three.

