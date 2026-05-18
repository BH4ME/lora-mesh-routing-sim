# Task Plan: Conference-Ready LoRa Mesh Routing Study

## Goal

Turn the current LoRa Mesh simulator into a clean conference-ready research project:

- Keep the repository tidy and easy to explain.
- Reframe the work as a confidence-aware routing optimization problem, not a simple fusion of two protocols.
- Implement and evaluate a proposed third protocol against the two existing baselines.
- Produce reproducible simulation results and meeting-ready material.

## Current Status

| Phase | Status | Notes |
| --- | --- | --- |
| 1. Inspect existing project | complete | Existing simulator, baseline results, docs, and report assets have been reviewed. |
| 2. Write research plan | complete | Formal conference plan added in `docs/research/conference-research-plan.md`. |
| 3. Clean directory layout | complete | Old papers, PPTs, previews, and legacy report tools were moved into `archive/`. |
| 4. Implement proposed protocol | complete | Added `calm-mesh` with confidence-aware route admission and emergency fallback. |
| 5. Run simulations | complete | Generated 50-node repeated-unicast and mixed-traffic CSVs with 20 seeds. |
| 6. Analyze and summarize results | complete | Wrote summary TXT outputs and experiment notes for conference interpretation. |
| 7. Add online adaptive firmware variant | complete | Added `smart-calm` with small tabular online learning over routing profiles. |
| 8. Continue stress simulations | complete | Added Smart-CALM comparisons under high shadowing and higher offered load. |
| 9. Optimize Smart-CALM significance | complete | Added per-flow policy selection, redundant fallback cancellation, and updated formal three-scenario comparison. |
| 10. Train high-reliability Smart-CALM mode | complete | Added offline prior tooling and a learned timeout-retry action that raises unicast PDR in all three formal scenarios. |
| 11. Build ESP32 direct-LoRa firmware prototype | complete | Added a PlatformIO ESP32 prototype with Smart-CALM controller, explicit CRC-protected over-the-air frame encoding, and SX1262/SX127x build targets. |
| 12. Port first mesh data plane to firmware | complete | Added Smart-CALM-owned RREQ/RREP/DATA/ACK source-route behavior and serial-triggered application sends, inspired by MeshCore/Meshtastic mechanics but not their protocols. |
| 13. Optimize Smart-CALM recovery overhead | complete | Added v1.1 cached-path timeout retry before fallback flooding, then accepted v1.1.1 timeout-rescue radius control after three 20-seed comparison scenarios. |
| 14. Add firmware reliability refinements | pending | Port v1.1.1 timeout recovery, persistent route aging, neighbor/link-quality tables, and richer delivery telemetry for online policy learning. |

## Proposed Protocol Framing

Avoid saying "combine Meshtastic and MeshCore." The research framing is:

> Fixed forwarding modes expose a reliability-airtime tradeoff in LoRa Mesh. The proposed method treats forwarding redundancy as an adaptive resource allocated according to path confidence.

Working name:

**CALM: Confidence-Aware LoRa Mesh Routing**

Core mechanism:

- High-confidence path: source-route forwarding with low redundancy.
- Medium-confidence path: source-route forwarding with limited backup relay behavior.
- Low-confidence path: bounded managed flooding with rank-based suppression.

Tuned defaults after parameter search:

- `calm_route_ttl_s = 600`
- `calm_discovery_window_s = 2.0`
- `calm_fallback_confidence_threshold = 0.0`
- `calm_fallback_ttl = 2`
- `calm_fallback_delay_margin_s = 0.6`
- `calm_hop_penalty_per_hop = 0.025`
- `calm_route_age_penalty = 0.1`

Online adaptive extension:

- `smart-calm` chooses among `lean`, `balanced`, and `rescue` profiles.
- State is based on recent reliability and congestion buckets.
- The active profile is selected per unicast flow, so MCU firmware can react to current conditions instead of waiting for a manual reconfiguration cycle.
- A learned high-reliability mode first retries a timed-out unicast over cached
  source-route DATA, then uses bounded fallback only when path knowledge is
  unavailable.
- v1.1.1 keeps route-miss recovery conservative while shrinking late timeout
  rescue according to the active online profile, reducing airtime and collision
  pressure without materially changing PDR.
- Current ACK-aware simulation treats `unicast_pdr` as source-confirmed delivery;
  `destination_unicast_pdr` remains available to diagnose packets that reached
  the destination but failed to ACK back to the sender.
- Reward penalizes control overhead, collision pressure, route repairs, fallback redundancy, and delay.
- The controller uses a tiny Q table suitable for MCU firmware rather than a neural network.
- The ESP32 prototype should keep the controller logic separate from the radio driver so the same policy can later be adapted to different LoRa chips.
- The first direct-LoRa firmware milestone now has a compact Smart-CALM wire frame with magic/version/type, source/destination/sequence, TTL, confidence, payload length, and CRC-16.
- The first mesh data-plane milestone borrows general source-route discovery and managed-fallback mechanics, while keeping all frame definitions and payload encodings Smart-CALM-specific.

## Directory Policy

Do not delete old material. Move old or bulky material into archive folders:

- `archive/references/` for downloaded papers and external PDFs.
- `archive/report-drafts/` for old PPT/PDF deliverables and conflict copies.
- `archive/report-previews/` for generated slide PNG previews.
- `archive/legacy-tools/` for old report repair scripts or conflict-copy scripts that are not part of the simulator.

Keep visible at project root:

- `README.md`
- `lora_mesh_sim.py`
- `analyze_results.py`
- `docs/`
- `results/`
- `tools/` only for reusable scripts

## Implementation Plan

1. Add protocol support:
   - Add `calm-mesh` or `confidence-aware` protocol option.
   - Keep existing `meshtastic` and `meshcore` unchanged as baselines.

2. Add link/path confidence:
   - Estimate link confidence from received SNR margin and collision observations.
   - Penalize stale routes and weak links.
   - Track route confidence alongside cached paths.

3. Improve route discovery:
   - Collect candidate RREQ paths for a short window.
   - Select the path with best cost instead of accepting the first path.

4. Add controlled redundancy:
   - Use normal source routing for strong paths.
   - Use bounded fallback forwarding for weak or stale paths.

5. Add metrics:
   - `mean_path_confidence`
   - `fallback_forward_count`
   - `route_repair_count`
   - `control_overhead_ratio`

## Experiment Plan

Primary scenarios:

- Repeated unicast: `50 nodes / 3000 m / 1200 s / pair-count 8 / 20 seeds`
- Mixed traffic: `50 nodes / 3000 m / 1200 s / pair-count 8 / 20 seeds`
- Stress mixed traffic: higher shadowing or larger area to expose weak-link behavior

Continuation scenarios:

- High-shadowing mixed traffic: `50 nodes / 3000 m / 1200 s / mixed / shadow-sigma-db 6 / pair-count 8 / 20 seeds / all4 protocols`
- Candidate next stress checks: higher offered load or larger area, selected after the high-shadowing result is available.

Main metrics:

- Unicast PDR
- Broadcast coverage
- Average delay
- Total transmissions
- Total airtime
- Airtime per delivery
- Collision failures
- Duplicate receptions
- Control overhead

## Success Criteria

The proposed protocol should show at least one conference-worthy pattern:

- Recover part of MeshCore-like PDR loss while keeping airtime far below managed flooding.
- Reduce collision failures compared with managed flooding.
- Show better stability under mixed traffic or high shadowing.

## Errors Encountered

| Error | Attempt | Resolution |
| --- | --- | --- |
| `analyze_results.py` failed on old CSVs after new metrics were added | Analyze old baseline CSV | Made metric aggregation skip missing columns. |
| Parameter tuning script could not import `lora_mesh_sim` from `tools/` | Run tuning smoke | Added project root to `sys.path` in the tuning script. |
| Initial parameter-injection test did not trigger fallback | Unit test | Reworked the test scenario and confirmed parameters flow through `run_one()`. |
| Host firmware smoke test failed on `SmartCalmController(Settings = Settings{})` | C++17 compile check | Split the default constructor from the parameterized constructor for compiler compatibility. |
| Host firmware smoke test expected the wrong low-reliability state bucket | C++ smoke test | Corrected the test expectation to match the controller's state mapping. |
