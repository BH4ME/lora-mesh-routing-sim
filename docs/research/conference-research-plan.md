# Conference Research Plan: Confidence-Aware LoRa Mesh Routing

## 1. Motivation

LoRa Mesh routing faces a structural tradeoff. Redundant forwarding improves delivery under weak and uncertain links, but LoRa's low data rate and half-duplex shared channel make unnecessary retransmissions expensive. Source-route caching reduces transmissions, but a cached route can become fragile when one hop has poor SNR, collision exposure, or stale link information.

The key research question is therefore:

> How should a LoRa Mesh node allocate forwarding redundancy when path quality is uncertain and airtime is scarce?

This framing avoids presenting the method as a simple combination of existing protocols. The two existing protocols are used as fixed-mode baselines that expose the limits of static forwarding behavior.

## 2. Baseline Observations

The current simulator compares:

- `meshtastic-like`: managed flooding with delayed rebroadcast and duplicate suppression.
- `meshcore-like`: RREQ/RREP route discovery with cached source routes.

Existing 50-node experiments show:

- In repeated unicast, route caching greatly reduces transmissions and airtime, but PDR drops compared with managed flooding.
- In mixed traffic, broadcast coverage remains high, but unicast PDR drops sharply under source-route caching.

These results suggest that neither fixed redundancy nor fixed source routing is enough. The routing decision should depend on route confidence.

## 3. Proposed Method

Working name:

**CALM: Confidence-Aware LoRa Mesh Routing**

Firmware-oriented extension:

**Smart-CALM: Online Adaptive Confidence-Aware Routing**

Core idea:

> Treat forwarding redundancy as a controllable network resource. Use low-redundancy source routing when the path is confident, and introduce bounded redundancy only when uncertainty is high.

The proposed method contains three mechanisms:

1. Confidence-aware path selection
2. Airtime-aware route cost
3. Controlled fallback redundancy

## 4. Link And Path Confidence

For a candidate link from node `i` to node `j`, estimate a link cost:

```text
LinkCost(i,j) =
  w1 * ToA
+ w2 * PER_est(i,j)
+ w3 * Congestion(j)
+ w4 * RouteAge(i,j)
- w5 * SNRMargin(i,j)
```

Where:

- `ToA` is the packet time-on-air.
- `PER_est` is estimated from SNR margin and recent reception history.
- `Congestion` is estimated from recent collision or channel busy observations.
- `RouteAge` penalizes stale cached information.
- `SNRMargin` is measured SNR minus the LoRa required SNR threshold.

Path cost is the sum of link costs:

```text
PathCost(P) = sum LinkCost(i,j)
```

Path confidence is inversely related to path cost and weak-hop count.

## 5. Route Discovery

The baseline source-route protocol accepts the first discovered RREQ path. CALM should instead collect candidate paths during a short discovery window and select the path with the best reliability-airtime cost.

Candidate path selection should consider:

- Minimum path cost
- Weakest-hop SNR margin
- Hop count
- Path age
- Whether the path shares overloaded relays

This changes the contribution from "route caching" to "quality-aware route admission."

## 6. Forwarding Strategy

Forwarding mode depends on route confidence:

```text
High confidence:
  Use cached source route.

Medium confidence:
  Use cached source route with limited backup forwarding.

Low confidence:
  Use bounded managed flooding with rank-based delay and duplicate suppression.
```

The important claim is that redundancy is not always enabled. It is allocated only when the current path confidence does not justify pure source routing.

The current tuned prototype uses conservative defaults:

- Route TTL: `600 s`
- RREQ candidate collection window: `2.4 s`
- Fallback confidence threshold: `0.0`
- Fallback TTL: `2`
- Hop confidence penalty: `0.025` per extra hop
- Route age penalty: `0.1`

This means the first optimization target is quality-aware route admission. Fallback flooding is kept as an emergency mechanism for failed discovery rather than a normal forwarding mode.

## 7. Firmware-Side Online Adaptation

Smart-CALM removes the need for manual field tuning. Instead of fixing one parameter set before deployment, each node keeps a tiny online-learning controller that selects among three prevalidated profiles:

- `lean`: longer route lifetime, low fallback redundancy, lowest airtime.
- `balanced`: tuned CALM defaults.
- `rescue`: shorter route lifetime, longer discovery window, more fallback redundancy for unstable links.

The controller observes only MCU-available signals:

- Recent unicast delivery ratio.
- Route cache miss and route repair frequency.
- Collision pressure.
- Control packet ratio.
- Path confidence from SNR margin and hop count.
- Delivery delay when an ACK or end-to-end confirmation is available.

The learning rule is tabular Q-learning over a small state/action space. This is intentionally not a neural network. With 6 states and 3 actions, the policy table is tiny and can be stored in RAM or EEPROM. The firmware can update it once every tens of seconds, so the CPU and memory cost stay practical for LoRa-class microcontrollers.

State:

```text
state = reliability_bucket x congestion_bucket
```

Action:

```text
action in {lean, balanced, rescue}
```

Reward:

```text
reward =
  delivery_gain
- airtime/control overhead penalty
- collision penalty
- route repair penalty
- fallback redundancy penalty
```

This turns the contribution from "one optimized parameter set" into "a self-adapting routing controller that can be burned into firmware and continue tuning itself after deployment."

## 8. Evaluation Plan

Compare four protocols:

- `meshtastic-like`: fixed managed flooding baseline
- `meshcore-like`: fixed route-cache/source-route baseline
- `calm-mesh`: proposed confidence-aware adaptive routing
- `smart-calm`: firmware-oriented online adaptive CALM

Primary scenarios:

- Repeated unicast, 50 nodes, 3000 m area, 1200 s, 8 fixed pairs, 20 seeds
- Mixed traffic, 50 nodes, 3000 m area, 1200 s, 8 fixed pairs, 20 seeds
- Stress mixed traffic with larger shadowing or area

Primary metrics:

- Unicast PDR
- Broadcast coverage
- Average delay
- Total transmissions
- Total airtime
- Airtime per delivery
- Collision failures
- Control overhead
- Route cache hit/miss behavior

Expected outcome:

- Compared with managed flooding, CALM should reduce transmissions, airtime, and collisions.
- Compared with source-route caching, CALM should recover part of the lost PDR in mixed or unstable traffic.

## 8. Conference Contribution Wording

Suggested contribution statement:

> This work formulates LoRa Mesh routing as a confidence-aware reliability-airtime optimization problem. We design an adaptive forwarding mechanism that estimates path confidence from SNR margin, route age, and congestion indicators, then allocates forwarding redundancy only when path uncertainty is high.

Suggested title:

> Confidence-Aware Adaptive Routing for Airtime-Constrained LoRa Mesh Networks

Short Chinese version:

> 面向空口受限 LoRa Mesh 的置信度感知自适应路由机制

## 9. Next Engineering Steps

1. Add `calm-mesh` as a third protocol in `lora_mesh_sim.py`.
2. Add route confidence and candidate path scoring.
3. Add bounded fallback forwarding for low-confidence routes.
4. Run the three-protocol comparison and save reproducible CSV outputs.
5. Update slides so the story is "optimization framework and evidence," not "protocol fusion."
