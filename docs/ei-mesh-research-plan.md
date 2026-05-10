# EI-Oriented Research Plan: Adaptive Intelligence for LoRa Mesh Routing

## 1. Current Problem in This Project

The current simulator already compares two useful baselines:

- `meshtastic-like`: managed flooding with delayed rebroadcast and duplicate suppression.
- `meshcore-like`: RREQ/RREP route discovery with cached source routes.

The existing 50-node results show a clear research gap:

- In repeated unicast, `meshcore-like` reduces transmissions from about 4575 to 1356 and airtime from about 1129 s to 335 s, but unicast PDR drops from about 0.946 to 0.833.
- In mixed traffic, `meshcore-like` keeps broadcast coverage high, but unicast PDR drops sharply from about 0.948 to 0.642.

This means the mesh problem is not simply "flooding or routing". The hard problem is adaptive control under LoRa constraints: low data rate, half duplex, high collision cost, changing link quality, and sparse control information.

## 2. Proposed Direction

Use a new protocol direction:

**ALARM: Adaptive Link-quality and Airtime-aware Reinforcement Mesh Routing for LoRa**

The core idea is to keep the reliability of flooding only where uncertainty is high, while using quality-aware cached routes when the network has enough evidence. Each relay decision is based on a dynamic path cost rather than hop count.

The protocol combines four mechanisms:

1. Link-quality-aware routing metric
2. Airtime and congestion-aware relay selection
3. Lightweight online learning for route choice
4. Controlled opportunistic redundancy for weak links

This is more advanced than only adding AODV, DSDV, or static shortest path, because it treats LoRa mesh as a joint routing and wireless-resource optimization problem.

## 3. Routing Metric

For a candidate link from node `i` to node `j`, define:

```text
LinkCost(i,j) =
  w1 * ToA(sf,bw,cr,payload)
+ w2 * PER_est(i,j)
+ w3 * Congestion(j)
+ w4 * EnergyRisk(j)
+ w5 * RouteAge(i,j)
- w6 * SNRMargin(i,j)
```

Where:

- `ToA` is LoRa time-on-air.
- `PER_est` is estimated packet error rate from SNR/SINR history.
- `Congestion` is estimated by recent collision failures, queue delay, or channel busy ratio.
- `EnergyRisk` penalizes nodes with low battery or too much relay load.
- `RouteAge` penalizes stale cached paths.
- `SNRMargin = observed_snr - required_snr(sf)`.

Path cost is the sum of link costs:

```text
PathCost(P) = sum LinkCost(i,j), for every hop in path P
```

The selected path is not necessarily the shortest-hop path. It is the path with the best reliability-airtime tradeoff.

## 4. Lightweight Learning Layer

A full deep reinforcement learning model is usually too heavy for embedded LoRa nodes, so the practical EI-friendly design should use a lightweight learner:

**Contextual Multi-Armed Bandit Routing**

Each node treats candidate next hops as arms. The context includes:

- SNR margin
- SINR or collision flag
- hop distance to destination
- route-cache age
- relay congestion
- recent delivery ACK success

The reward can be:

```text
Reward =
  alpha * DeliverySuccess
- beta  * AirtimeCost
- gamma * Delay
- delta * CollisionObserved
- eta   * RelayEnergyCost
```

This gives the paper a modern "AI for networking" angle, while remaining implementable in this Python simulator and later on SX1262-class hardware.

## 5. Mesh Protocol Behavior

### 5.1 Route Discovery

Instead of accepting the first RREQ path, the destination waits for a short collection window and evaluates several candidate paths.

The destination replies with the best `k` paths:

- Primary path: minimum learned cost
- Backup path: node-disjoint or partially disjoint if possible
- Emergency path: controlled flood fallback

### 5.2 Data Forwarding

For normal links:

- Use cached source route.
- Forward only by the next hop.
- Update link statistics from every successful receive.

For uncertain or weak links:

- Use opportunistic two-relay forwarding.
- Only the best one or two relays forward after a rank-based delay.
- Duplicate suppression prevents uncontrolled flooding.

### 5.3 Route Maintenance

Routes expire by both time and quality:

- Hard TTL: route expires after a fixed time.
- Soft TTL: route decays faster after collision, low SNR margin, or delivery failure.
- Fast repair: intermediate node can switch to backup next hop before the source repeats discovery.

## 6. Implementation Plan in This Repository

### Phase 1: Add Protocol Class

Add a new class in `lora_mesh_sim.py`:

```python
class AlarmMesh(RoutingProtocol):
    name = "alarm-mesh"
```

Register it in `build_protocol()` and extend `--protocol` choices.

### Phase 2: Add Link Statistics

Maintain per-node link tables:

```text
link_stats[node][neighbor] = {
  snr_ema,
  sinr_ema,
  rx_success,
  rx_fail,
  collision_seen,
  last_seen_at,
  learned_cost
}
```

The current `RxInfo` already exposes `snr_db`, `sinr_db`, and `collided`, so this phase fits the current simulator cleanly.

### Phase 3: Replace First-Path Route Selection

Current `meshcore-like` replies immediately when the destination receives the first RREQ. For ALARM, keep a small candidate buffer:

```text
rreq_candidates[(origin, dst, request_id)] = [
  path_1,
  path_2,
  ...
]
```

After a collection window, reply with the minimum-cost path.

### Phase 4: Add Adaptive Forwarding

Forwarding decision:

- If route confidence is high: source-route unicast.
- If route confidence is medium: source-route plus backup relay.
- If route confidence is low: bounded managed flood with rank-based delays.

### Phase 5: Add Evaluation Metrics

Add these metrics to CSV:

- `route_repair_count`
- `backup_forward_count`
- `learned_route_switches`
- `mean_path_cost`
- `link_snr_margin_mean`
- `control_overhead_ratio`
- `energy_fairness_jain`

These metrics help the EI paper show mechanism-level evidence, not only PDR and delay.

## 7. Experiment Design for EI Paper

Use the existing baselines:

- Meshtastic-like managed flooding
- MeshCore-like route cache
- Proposed ALARM-Mesh

Recommended scenarios:

- Node scale: 30, 50, 80, 120
- Area: 2000 m, 3000 m, 5000 m
- Traffic: unicast, broadcast, mixed
- Pair reuse: 0, 4, 8, 16
- Channel condition: shadow sigma 2, 4, 6, 8 dB
- Mobility/failure: random relay failure or SNR drift
- PHY: fixed SF first, then multi-SF extension

Main metrics:

- Unicast PDR
- Broadcast coverage
- Average delay
- Total transmissions
- Total airtime
- Airtime per delivery
- Collision failures
- Control overhead
- Energy balance

Expected claim:

```text
Compared with managed flooding, ALARM-Mesh should reduce airtime and collisions.
Compared with source-route caching, ALARM-Mesh should recover part of the lost PDR in mixed and unstable traffic.
```

## 8. Paper Innovation Points

The EI paper can frame the contributions as:

1. A packet-level LoRa mesh simulator that jointly models ToA, half duplex, SNR-based PRR, capture effect, and route behavior.
2. An adaptive LoRa mesh routing metric combining airtime, SNR margin, congestion, route age, and relay energy.
3. A lightweight contextual bandit route-selection mechanism suitable for low-power mesh nodes.
4. A hybrid forwarding strategy that switches between source routing, backup relay, and bounded flooding according to route confidence.
5. Multi-scenario evaluation showing the reliability-airtime tradeoff against managed flooding and RREQ/RREP route caching baselines.

## 9. Related Work Anchors

Useful recent directions to cite:

- Reinforcement learning has recently been used for energy-efficient multi-hop LoRa broadcasting.
- Deep reinforcement learning has been explored for QoS-aware LoRa transmission policy and multi-hop routing.
- LoRa mesh studies often combine routing with TDMA, channel activity detection, capture effect, or spreading-factor adaptation.
- Recent work also explores energy-aware, position-aware, and minimalistic distance-vector routing for LoRa mesh.

The differentiator for this project should be:

```text
not only selecting relays, and not only discovering routes,
but adaptively selecting the forwarding mode based on learned link quality and airtime cost.
```

## 10. Recommended Next Step

The best next engineering step is to implement `alarm-mesh` as a third protocol in this simulator and run it against the two existing baselines. After that, the PPT and paper can be upgraded from "baseline comparison" to "proposed algorithm with experimental validation".

