# Source Layout

This file explains where project source files, generated artifacts, and
documentation live. Use it as the first stop before continuing Smart-CALM
optimization.

## Root Entry Points

- `README.md`: project overview and common commands.
- `lora_mesh_sim.py`: packet-level simulator and routing protocol models.
- `analyze_results.py`: CSV aggregation helper.
- `requirements.txt`: optional Python dependency list.
- `LICENSE`: project license.

## Simulation Source

- `lora_mesh_sim.py`: main simulator.
- Smart-CALM simulation model: search for `SmartCalmProtocol` and `smart-calm`
  inside `lora_mesh_sim.py`.
- CALM baseline model: search for `CalmMeshProtocol` and `calm-mesh` inside
  `lora_mesh_sim.py`.

## Firmware Source

- `firmware/esp32_smart_calm/platformio.ini`: PlatformIO build targets for
  `esp32dev_sx1262` and `esp32dev_sx127x`.
- `firmware/esp32_smart_calm/src/main.cpp`: ESP32 runtime entry point.
- `firmware/esp32_smart_calm/include/smart_calm_types.hpp`: wire-frame and
  shared data types.
- `firmware/esp32_smart_calm/include/smart_calm_wire.hpp`: encode/decode and
  CRC logic.
- `firmware/esp32_smart_calm/include/smart_calm_controller.hpp`: MCU-friendly
  online policy controller.
- `firmware/esp32_smart_calm/include/smart_calm_mesh.hpp`: Smart-CALM-owned
  `RREQ/RREP/DATA/ACK` mesh data plane.
- `firmware/esp32_smart_calm/include/smart_calm_prior.hpp`: generated offline
  prior embedded into firmware.
- `firmware/esp32_smart_calm/test/controller_smoke.cpp`: host C++ smoke test for
  controller, packet encoding, and mesh data-plane behavior.

## Tools

- `tools/tune_calm_parameters.py`: CALM parameter search.
- `tools/train_smart_calm_prior.py`: Smart-CALM prior training experiments.
- `tools/build_three_protocol_comparison.py`: comparison markdown and chart
  generation.
- `tools/run_calm_experiments.sh`: reproducible CALM experiment runner.
- `tools/generate_smart_calm_prior_header.py`: converts trained prior JSON into
  firmware header form.

## Tests

- `tests/test_calm_protocol.py`: simulator behavior tests for CALM/Smart-CALM.
- `tests/test_three_protocol_comparison.py`: comparison report generation tests.
- `firmware/esp32_smart_calm/test/controller_smoke.cpp`: firmware-side C++
  smoke test.

## Results And Generated Artifacts

- `results/*.csv`: simulation raw result tables.
- `results/*summary.txt`: aggregate text summaries.
- `results/figures/`: generated comparison figures.
- `results/prior_model_comparison/`: prior-training comparison outputs.

Human-readable result narratives are kept under `docs/results/`, not in
`results/`.

## Documentation

- `docs/README.md`: documentation index.
- `docs/research/`: research framing and conference plan.
- `docs/results/`: result interpretation and meeting summaries.
- `docs/firmware/`: firmware design and build notes.
- `docs/reference/`: terminology, formulas, and stable references.
- `docs/project-history/`: working findings and progress log.
- `docs/project-management/`: planning and version records.
- `docs/meta/`: migration and documentation-maintenance logs.

## Archive

- `archive/research-drafts/`: old research drafts kept for traceability.
- `archive/report-drafts/`: old generated report decks and PDFs.
- `archive/report-previews/`: old slide previews.
- `archive/references/`: external reference files.
- `archive/legacy-tools/`: old helper scripts no longer part of the active
  workflow.
