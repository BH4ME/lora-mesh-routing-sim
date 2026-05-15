# Anti-Cherrypick Stress Test Report

This report checks whether `smart-calm-sim-v1.1.1` still looks credible when
the simulator is pushed beyond the original meeting scenarios.

The runs were generated from a clean detached worktree at commit `284cf25`
(`version/v1.1.1`) so unrelated working-tree experiments did not affect the
results.

## Stress Scenarios

| Scenario | Purpose | Seeds | Notes |
| --- | --- | ---: | --- |
| `shadow8` | Stronger channel uncertainty | 10 | `shadow-sigma-db 8` |
| `sparse4k` | Sparser topology | 10 | `area-m 4000` |
| `rate14` | Higher offered load | 10 | `rate-per-min 14` |
| `dense80_smoke` | Higher density smoke check | 3 | `80 nodes / 600 s / rate-per-min 8`; the full `80 nodes / 1200 s / 10 seeds` run was too slow for this simulator budget |

All 10-seed scenarios use `50 nodes / 3000 m / 1200 s / mixed traffic /
pair-count 8 / protocol all4` unless noted.

## Mean Results

| Scenario | Protocol | Unicast PDR | Airtime (s) | Collision failures | Fallback forwards | Avg delay (s) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| shadow8 | Meshtastic-like | 0.958 | 1158 | 121195 | 0 | 0.5 |
| shadow8 | MeshCore-like | 0.625 | 928 | 80082 | 0 | 0.4 |
| shadow8 | CALM | 0.761 | 809 | 72824 | 66 | 0.9 |
| shadow8 | Smart-CALM v1.1.1 | 0.963 | 777 | 69492 | 72 | 9.2 |
| sparse4k | Meshtastic-like | 0.963 | 1177 | 122567 | 0 | 0.6 |
| sparse4k | MeshCore-like | 0.630 | 929 | 79237 | 0 | 0.4 |
| sparse4k | CALM | 0.775 | 810 | 72661 | 58 | 0.9 |
| sparse4k | Smart-CALM v1.1.1 | 0.963 | 793 | 70578 | 103 | 6.6 |
| rate14 | Meshtastic-like | 0.861 | 2419 | 265471 | 0 | 1.1 |
| rate14 | MeshCore-like | 0.379 | 1779 | 161661 | 0 | 0.4 |
| rate14 | CALM | 0.513 | 1575 | 149862 | 109 | 0.7 |
| rate14 | Smart-CALM v1.1.1 | 0.884 | 1740 | 168778 | 799 | 13.8 |
| dense80_smoke | Meshtastic-like | 0.959 | 1368 | 237421 | 0 | 0.7 |
| dense80_smoke | MeshCore-like | 0.679 | 1146 | 176088 | 0 | 0.5 |
| dense80_smoke | CALM | 0.706 | 984 | 146434 | 55 | 1.0 |
| dense80_smoke | Smart-CALM v1.1.1 | 0.925 | 1028 | 151950 | 240 | 8.8 |

## Interpretation

These runs do not support a "Smart-CALM wins everything" claim.

- In `shadow8` and `sparse4k`, Smart-CALM v1.1.1 remains strong: it has the
  highest unicast PDR and the lowest airtime and collision failures.
- In `rate14`, Smart-CALM keeps the best PDR, but it loses the airtime and
  collision metrics to CALM. The fallback count rises to `799`, which means the
  online rescue policy becomes expensive under heavy offered load.
- In `dense80_smoke`, Smart-CALM does not beat managed flooding on PDR and does
  not beat CALM on airtime or collisions. It is still more reliable than
  MeshCore-like and CALM, but the reliability comes with extra delay and
  fallback traffic.
- Smart-CALM's average delay is consistently much higher than the other
  protocols because timed-out flows can be recovered later by the rescue path.
  This is useful for delivery ratio, but it is not a free win.

## Credibility Boundary

The v1.1.1 meeting result is not obviously inflated by scenario retuning: under
two harsher 10-seed scenarios, the same mechanism still reduces airtime and
collisions while preserving high PDR. However, the anti-cherrypick suite also
shows the weak point clearly: under very high load or denser deployments,
Smart-CALM can over-spend fallback recovery.

Use the conservative claim:

> Smart-CALM v1.1.1 improves reliability under the same simulator and remains
> efficient under stronger shadowing and sparser topology, but high offered load
> exposes a reliability-efficiency tradeoff. The next optimization target should
> be a congestion-aware cap on timeout rescue.

## Result Files

- `results/anti_cherrypick_stress/shadow8.csv`
- `results/anti_cherrypick_stress/shadow8_summary.txt`
- `results/anti_cherrypick_stress/sparse4k.csv`
- `results/anti_cherrypick_stress/sparse4k_summary.txt`
- `results/anti_cherrypick_stress/rate14.csv`
- `results/anti_cherrypick_stress/rate14_summary.txt`
- `results/anti_cherrypick_stress/dense80_smoke.csv`
- `results/anti_cherrypick_stress/dense80_smoke_summary.txt`
- `results/anti_cherrypick_stress/stress_means.csv`
