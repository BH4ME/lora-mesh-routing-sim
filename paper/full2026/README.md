# Smart-CALM Full Paper Working Notes

This directory is for the full-paper manuscript, separate from the MASS poster abstract.

## Version Boundary

- Manuscript evidence line: MeshEcho repository release `2.1.3`, using the
  correct-prefix ICC refresh generated from the `2.1.2` simulator state.
- The paper uses only `results/meshecho_v2_1_2_50n_*` files in its main tables
  and discussion.
- The older `meshecho_v2_1_0_icc_50n_*` files remain frozen for historical
  comparison and are not mixed into the current tables.
- Firmware behavior is not claimed as hardware validation; the prototype
  version remains `meshecho-firmware-v2.1.2`.

## Current Evidence Set

Current ICC simulation files:

- `results/meshecho_v2_1_2_50n_unicast_pairs.csv`
- `results/meshecho_v2_1_2_50n_mixed.csv`
- `results/meshecho_v2_1_2_50n_mixed_shadow6.csv`
- `results/meshecho_v2_1_2_50n_mixed_rate10.csv`
- Matching `_summary.csv`, `_summary.txt`, and the versioned report at
  `docs/results/icc2027_comparison_v2_1_2.md`.

Poster-only reference material may be reused for wording or notation, but the full paper should have its own structure, figures, and contribution framing.

## Target Framing

The paper should be framed as a full simulation and protocol study of ACK-aware online redundancy control for LoRa mesh networks:

1. Problem: static flooding/source-routing choices expose a reliability-airtime tradeoff.
2. Design: Smart-CALM uses ACK-confirmed delivery and channel-pressure signals to select among lean, balanced, and rescue profiles.
3. Algorithm: six-state tabular Q-learning controller with explicit state, action, reward, and update definitions.
4. Mechanism: source-routed unicast, end-to-end ACK, fallback forwarding, and bounded profile switching.
5. Evaluation: 50-node ACK-aware packet-level LoRa simulator under repeated unicast, mixed traffic, heavier shadowing, and higher offered load.
6. Implementation plausibility: ESP32- or nRF52-class MCU nodes paired with LoRa transceivers; airtime as energy/duty-cycle proxy, not board-level current measurement.

## Submission Notes

- Use IEEE conference LaTeX unless a specific target venue later requires another template.
- Keep author placeholders until final author order is confirmed.
- Do not claim hardware validation unless measurements are added.
- Do not claim scalability beyond the evaluated 50-node setting without adding experiments.
