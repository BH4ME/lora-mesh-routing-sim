# Smart-CALM Simulation Versions

This file tracks simulation baselines before further optimization.

## `smart-calm-sim-v1.0`

- Git tag: `smart-calm-sim-v1.0`
- Baseline commit: `c7626c7 Add Smart-CALM simulation workflow`
- Optimization branch: `codex/smart-calm-sim-optimization`
- Purpose: freeze the current Smart-CALM simulator, trained prior, and comparison
  CSVs before the next optimization round.

Key simulation files:

- `lora_mesh_sim.py`
- `tools/train_smart_calm_prior.py`
- `tools/build_three_protocol_comparison.py`
- `results/smart_calm_50n_mixed.csv`
- `results/smart_calm_50n_mixed_shadow6.csv`
- `results/smart_calm_50n_mixed_rate10.csv`
- `results/smart_calm_50n_unicast_pairs.csv`

Key comparison docs:

- `docs/results/three_protocol_comparison.md`
- `docs/results/calm_experiment_notes.md`

Notes:

- Treat this as the reference point for future PDR, airtime, collision, and
  delay comparisons.
- Continue future Smart-CALM simulator optimization from
  `codex/smart-calm-sim-optimization`, currently aligned with commit `614d8dd`.
- Do not overwrite this baseline's CSVs when testing new ideas; write new result
  files or tag a new version once the improvement is accepted.
- New optimization runs should either update this file with a new version entry
  or create a new tag, for example `smart-calm-sim-v1.1`.
