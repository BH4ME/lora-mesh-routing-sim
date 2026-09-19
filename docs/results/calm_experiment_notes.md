# CALM Experiment Notes

## Scenarios

The formal experiment script is:

```bash
tools/run_calm_experiments.sh
```

It runs three protocol variants:

- `meshtastic-like`: fixed managed flooding baseline
- `meshcore-like`: fixed source-route cache baseline
- `calm-mesh`: confidence-aware adaptive routing

The Smart-CALM comparison uses:

```bash
python3 lora_mesh_sim.py --protocol all4 --nodes 50 --area-m 3000 --duration-s 1200 --traffic unicast --rate-per-min 6 --pair-count 8 --seeds 20 --csv results/smart_calm_50n_unicast_pairs.csv
python3 lora_mesh_sim.py --protocol all4 --nodes 50 --area-m 3000 --duration-s 1200 --traffic mixed --rate-per-min 6 --pair-count 8 --seeds 20 --csv results/smart_calm_50n_mixed.csv
```

## Conference Interpretation

The result should be interpreted through the reliability-airtime tradeoff:

- Managed flooding is the high-redundancy reference point.
- Source-route caching is the low-redundancy reference point.
- CALM allocates limited redundancy when route confidence is low.

The important claim is not that CALM dominates every baseline in every scenario. The stronger and more honest claim is:

> Fixed forwarding modes have clear operating boundaries. Confidence-aware routing exposes and controls the redundancy budget instead of baking it into the protocol.

## Result Summary

### Repeated Unicast

Scenario:

`50 nodes / 3000 m / 1200 s / unicast / pair-count 8 / 20 seeds`

Key means:

- `meshtastic-like`: PDR `0.946`, airtime `1129 s`, collision failures `117909`
- `meshcore-like`: PDR `0.833`, airtime `335 s`, collision failures `26643`
- `calm-mesh`: PDR `0.847`, airtime `224 s`, collision failures `16619`

Interpretation:

CALM slightly improves reliability over fixed source-route caching while also reducing airtime and collisions. The main gain is efficiency, with reliability staying competitive.

### Mixed Traffic

Scenario:

`50 nodes / 3000 m / 1200 s / mixed / pair-count 8 / 20 seeds`

Key means:

- `meshtastic-like`: unicast PDR `0.948`, broadcast coverage `0.949`, airtime `1170 s`
- `meshcore-like`: unicast PDR `0.642`, broadcast coverage `0.967`, airtime `962 s`
- `calm-mesh`: unicast PDR `0.755`, broadcast coverage `0.967`, airtime `830 s`

Interpretation:

CALM recovers a meaningful part of MeshCore-like's mixed-traffic unicast reliability loss while keeping broadcast coverage high and reducing airtime.

### Higher Shadowing Check

Scenario:

`50 nodes / 3000 m / 1200 s / mixed / shadow-sigma-db 6 / pair-count 8 / 20 seeds`

Key means:

- `meshtastic-like`: unicast PDR `0.950`, broadcast coverage `0.954`, airtime `1178 s`
- `meshcore-like`: unicast PDR `0.633`, broadcast coverage `0.971`, airtime `970 s`
- `calm-mesh`: unicast PDR `0.736`, broadcast coverage `0.970`, airtime `830 s`

Interpretation:

The tuned CALM defaults stay on the same tradeoff curve under heavier shadowing: lower airtime than MeshCore-like, higher unicast PDR than MeshCore-like, and much lower airtime than flooding.

## Tuned Parameters

- Route TTL: `600 s`
- RREQ candidate collection window: `2.0 s`
- Fallback confidence threshold: `0.0`
- Fallback TTL: `2`
- Fallback delay margin: `0.6 s`
- Hop confidence penalty: `0.025`
- Route age penalty: `0.1`

The tuned result shows that the strongest improvement comes from better path admission, not from adding constant redundancy.

## Smart-CALM Online Adaptation

Smart-CALM is the firmware-oriented version of CALM. It does not require the user to manually pick a fixed parameter set after deployment. Instead, it keeps three small parameter profiles and learns which one to use from recent network feedback.

Profiles:

- `lean`: lower airtime and lower fallback redundancy.
- `balanced`: tuned CALM defaults.
- `rescue`: higher redundancy for unstable routes.

Online signals:

- Unicast delivery ratio.
- Route cache miss ratio.
- Collision pressure.
- Route repair count.
- Fallback forwarding count.
- Control overhead ratio.
- Path confidence.

The learning controller is intentionally MCU-friendly. It uses a small tabular Q-learning policy rather than a neural model. The simulator currently exposes:

- `policy_switch_count`
- `policy_update_count`
- `policy_reward_total`
- `active_profile_index`

Smoke scenario:

`30 nodes / 2500 m / 360 s / mixed / pair-count 5 / 4 seeds`

Key means:

- `calm-mesh`: unicast PDR `0.719`, broadcast coverage `0.927`, airtime `142 s`
- `smart-calm`: unicast PDR `0.727`, broadcast coverage `0.940`, airtime `144 s`
- `smart-calm`: policy updates `22.75`, policy switches `2.25`

Interpretation:

Smart-CALM already closes the automatic-adaptation loop: nodes observe recent delivery and channel pressure, update the policy, and switch among routing profiles without manual parameter configuration.

### Formal Smart-CALM Comparison: Repeated Unicast

Scenario:

`50 nodes / 3000 m / 1200 s / unicast / pair-count 8 / 20 seeds`

Key means:

- `meshtastic-like`: PDR `0.946`, airtime `1129 s`, collision failures `117909`
- `meshcore-like`: PDR `0.833`, airtime `335 s`, collision failures `26643`
- `calm-mesh`: PDR `0.847`, airtime `224 s`, collision failures `16619`
- `smart-calm`: PDR `0.856`, airtime `366 s`, collision failures `29748`, policy updates `138.75`, policy switches `3.55`

Interpretation:

Smart-CALM improves delivery over MeshCore-like source-route caching, but currently spends more airtime and creates more collision pressure than both MeshCore-like and tuned CALM in this repeated-unicast case. This is useful diagnostically: the online learner is responding with real per-flow context, but the reward is still slightly rescue-biased and should penalize unnecessary fallback more strongly.

### Smart-CALM v2 Comparison: Mixed Traffic

Scenario:

`50 nodes / 3000 m / 1200 s / mixed / pair-count 8 / 20 seeds`

Key means:

- `meshtastic-like`: unicast PDR `0.948`, broadcast coverage `0.949`, airtime `1170 s`, collision failures `122048`
- `meshcore-like`: unicast PDR `0.642`, broadcast coverage `0.967`, airtime `962 s`, collision failures `82047`
- `calm-mesh`: unicast PDR `0.768`, broadcast coverage `0.970`, airtime `835 s`, collision failures `73923`
- `smart-calm`: unicast PDR `0.962`, broadcast coverage `0.968`, airtime `828 s`, collision failures `73496`

Interpretation:

In mixed traffic, Smart-CALM v2 raises unicast PDR from MeshCore-like's `0.642` to `0.962`. Compared with v1.1, it keeps PDR effectively unchanged while cutting airtime by `7.60%`, collision failures by `7.62%`, and fallback forwarding by `71.80%`.

Conference phrasing:

> Smart-CALM should not be presented as simply combining MeshCore and Meshtastic. The stronger claim is that it converts a static protocol-choice problem into a local online control problem: each device adjusts its redundancy and route-admission policy from observed delivery, cache misses, and channel pressure.

### Smart-CALM v2 Stress Check: Higher Shadowing

Scenario:

`50 nodes / 3000 m / 1200 s / mixed / shadow-sigma-db 6 / pair-count 8 / 20 seeds`

Key means:

- `meshtastic-like`: unicast PDR `0.950`, broadcast coverage `0.954`, airtime `1178 s`, collision failures `121836`
- `meshcore-like`: unicast PDR `0.633`, broadcast coverage `0.971`, airtime `970 s`, collision failures `83424`
- `calm-mesh`: unicast PDR `0.733`, broadcast coverage `0.975`, airtime `830 s`, collision failures `74048`
- `smart-calm`: unicast PDR `0.969`, broadcast coverage `0.975`, airtime `819 s`, collision failures `72980`

Interpretation:

Under stronger shadowing, Smart-CALM v2 still exceeds MeshCore-like and managed flooding on unicast PDR while using less airtime than both baselines. Compared with v1.1, PDR improves by `0.61%` while airtime drops by `6.51%`, collision failures drop by `6.51%`, and fallback forwarding drops by `71.84%`.

### Smart-CALM v2 Stress Check: Higher Offered Load

Scenario:

`50 nodes / 3000 m / 1200 s / mixed / rate-per-min 10 / pair-count 8 / 20 seeds`

Key means:

- `meshtastic-like`: unicast PDR `0.917`, broadcast coverage `0.915`, airtime `1875 s`, collision failures `198166`
- `meshcore-like`: unicast PDR `0.488`, broadcast coverage `0.936`, airtime `1415 s`, collision failures `125205`
- `calm-mesh`: unicast PDR `0.596`, broadcast coverage `0.939`, airtime `1233 s`, collision failures `113447`
- `smart-calm`: unicast PDR `0.932`, broadcast coverage `0.935`, airtime `1318 s`, collision failures `122431`

Interpretation:

Higher load shows the main tradeoff of the v2 recovery change. Smart-CALM raises unicast PDR from MeshCore-like's `0.488` to `0.932`, still above managed flooding's `0.917`, while reducing airtime and collision failures below MeshCore-like. Compared with v1.1, PDR drops by `0.51%`, but airtime drops by `6.57%`, collision failures drop by `6.79%`, and fallback forwarding drops by `47.24%`.

### Training Note

The first offline training experiment generated a direct Q-table prior in `results/smart_calm_prior.json`, but A/B testing showed that unconstrained Q transfer over-selected rescue/fallback behavior. The adopted training outcome is therefore more constrained: the firmware keeps the online profile learner and uses timeout-triggered recovery with a cached-path retry before fallback flooding.
