# Progress Log

## 2026-05-10

- Reviewed repository structure.
- Confirmed that the project contains a LoRa Mesh packet-level simulator, example CSV results, docs, old PPT outputs, and report-generation tools.
- Read existing docs and confirmed the prior optimization idea: use the two existing protocols as baselines to motivate a confidence-aware adaptive routing mechanism.
- Ran existing result aggregation for `results/exp_50n_unicast_pairs.csv` and `results/exp_50n_mixed.csv`.
- Started persistent planning files for the conference-ready work.
- Created `docs/conference-research-plan.md` and reframed the work as confidence-aware routing optimization.
- Moved old reports, previews, conflict copies, and reference PDFs into `archive/`.
- Implemented `calm-mesh` in `lora_mesh_sim.py`.
- Added CALM metrics: fallback forwards, route repairs, mean path confidence, and control overhead ratio.
- Added tests in `tests/test_calm_protocol.py`.
- Added `tools/tune_calm_parameters.py` for reproducible parameter search.
- Tuned CALM defaults to route TTL `600 s`, discovery window `2.0 s`, fallback threshold `0.0`, fallback TTL `2`, fallback delay margin `0.6 s`, hop penalty `0.025`, route age penalty `0.1`.
- Ran formal 50-node repeated-unicast and mixed-traffic simulations with 20 seeds.
- Added `smart-calm`, an MCU-friendly online adaptive routing variant that learns among lean, balanced, and rescue profiles.
- Added learning metrics: policy switches, policy updates, cumulative policy reward, and active profile index.
- Ran a 30-node mixed-traffic smoke comparison showing Smart-CALM performs online policy updates and switches without manual parameter tuning.
- Fixed Smart-CALM learning-context capture so per-flow route miss, fallback, and confidence signals are recorded before CALM send logic runs.
- Rebuilt Smart-CALM profiles from CLI CALM baseline parameters so command-line tuning affects the online-learning profile set.
- Re-ran formal 50-node repeated-unicast and mixed-traffic Smart-CALM comparisons after the learning fix.
- Started continuation stress simulations focused on Smart-CALM versus MeshCore/Meshtastic under high shadowing and other harsher scenarios.
- Ran high-shadowing mixed traffic stress test: `shadow-sigma-db 6`, 50 nodes, 20 seeds, all4 protocols.
- Ran high-offered-load mixed traffic stress test: `rate-per-min 10`, 50 nodes, 20 seeds, all4 protocols.
- Updated findings and experiment notes with the two new stress summaries.
- Optimized Smart-CALM defaults to conservative exploration `0.02`, fast update interval `30 s`, and learning rate `0.45`.
- Added cancellation of delayed fallback packets after successful source-route delivery to avoid redundant airtime.
- Added per-flow Smart-CALM policy selection so each unicast flow can use the current learned profile.
- Re-ran formal 50-node mixed, high-shadowing, and high-offered-load comparisons with 20 seeds.
- Regenerated `results/three_protocol_comparison.md` and SVG charts for the three-protocol meeting view.
- Added `tools/train_smart_calm_prior.py` for offline Smart-CALM prior training experiments.
- Trained a small Smart-CALM prior and found that unconstrained Q-table transfer overfits to rescue/fallback choices.
- Added learned timeout-triggered bounded fallback retry as the high-reliability training outcome.
- Re-ran three formal 50-node mixed/stress comparisons with the high-reliability training mode and regenerated summaries/charts.
