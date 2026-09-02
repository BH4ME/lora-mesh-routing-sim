# Codex Handoff - 2026-09-02

## Task Context

The current research line targets IEEE ICC 2027 IoT and Sensor Networks with
an ACK-aware Smart-CALM LoRa mesh protocol. The repository contains the
simulator, ESP32 firmware prototype, experiment scripts, results, and a
working paper. The current version boundary for the new experiment line is
`2.1.2`.

## 2.1.2 Refresh In This Turn

- Normalized CSV output writing to LF across the simulator and analysis /
  training helpers so generated result files stop producing CRLF diff noise.
- Bumped the repository release boundary to `2.1.2` in `VERSION`, `README.md`,
  firmware version strings, and the release notes.
- Re-ran the `smart_calm_v2` experiment line with
  `OUT_PREFIX=smart_calm_v2 bash tools/run_calm_experiments.sh`.
- The `results/smart_calm_v2_50n_unicast_pairs.csv`,
  `results/smart_calm_v2_50n_mixed.csv`,
  `results/smart_calm_v2_50n_mixed_shadow6.csv`, and
  `results/smart_calm_v2_50n_mixed_rate10.csv` files were overwritten with new
  LF-terminated output, along with their matching `_summary.txt` files.
- The new outputs should be treated as the current `v2` simulation line until
  a later paper-version freeze decides otherwise.
- Verification completed after the refresh:
  - `git diff --check` passed.
  - `python3 -m unittest discover -s tests -p 'test_*.py' -v` passed (`35` tests).
  - `python3 -m py_compile lora_mesh_sim.py analyze_results.py tools/*.py tests/*.py` passed.
  - `g++ -std=c++17 -Wall -Wextra -pedantic -Ifirmware/esp32_smart_calm/include firmware/esp32_smart_calm/test/controller_smoke.cpp -o /tmp/smart_calm_controller_smoke && /tmp/smart_calm_controller_smoke` passed.
  - `pio run -e esp32dev_sx1262` passed.
  - `pio run -e esp32dev_sx127x` passed.

## Completed In This Run

- Added and verified the ICC protocol matrix with seven configurations:
  `meshtastic`, `meshcore`, `calm`, `smart-calm`, `smart-calm-static`,
  `smart-calm-no-fallback`, and `smart-calm-no-confidence`.
- Completed all four 20-seed scenarios using the same topology, traffic,
  PHY, and seed settings across protocols:
  - `50n_unicast_pairs`
  - `50n_mixed`
  - `50n_mixed_shadow6`
  - `50n_mixed_rate10`
- Each raw CSV contains 140 rows: seven protocols times seeds 1 through 20.
- Each machine-readable summary contains seven protocols with `n=20` and 37
  available metrics per protocol.
- Metrics include ACK-confirmed PDR, destination DATA arrival ratio, P95 ACK
  delay, airtime, busy ratio, energy, packet reception ratio, collision rate,
  route repair, fallback forwarding, and policy telemetry.
- The test suite passes: `35` tests, `OK`.
- Python syntax compilation passes for the simulator, analyzer, and tests.

## Result Files

Raw CSV and summary files are under `results/` with prefix
`meshecho_v2_1_0_icc_50n_`:

- `unicast_pairs.csv`
- `mixed.csv`
- `mixed_shadow6.csv`
- `mixed_rate10.csv`
- Matching `_summary.csv` and `_summary.txt` files

The verified ICC summary is also published as
[docs/results/icc2027_comparison.md](/Users/bh4me_macair/Documents/Codex/lora_mesh/docs/results/icc2027_comparison.md).

The main mixed-traffic means are:

| Protocol | ACK PDR | Destination PDR | P95 ACK delay (s) | Airtime (s) |
| --- | ---: | ---: | ---: | ---: |
| meshtastic-like | 0.8522 | 0.9554 | 1.1194 | 1182.93 |
| meshcore-like | 0.3888 | 0.6613 | 0.6457 | 971.49 |
| calm-mesh | 0.7355 | 0.7693 | 2.7404 | 839.58 |
| smart-calm | 0.9373 | 0.9669 | 14.7734 | 836.56 |
| smart-calm-static | 0.9408 | 0.9570 | 15.7936 | 913.56 |
| smart-calm-no-fallback | 0.7677 | 0.7968 | 2.6084 | 828.61 |
| smart-calm-no-confidence | 0.9373 | 0.9669 | 14.7734 | 836.56 |

Interpretation: Smart-CALM improves ACK-confirmed reliability while keeping
airtime close to CALM and below managed flooding, but the reliability gain is
paid for with a substantially larger tail ACK delay and fallback cost. The
paper should present this as a reliability-airtime-delay tradeoff rather than
claiming dominance on every metric.

## Known Limitations

- `smart-calm-no-confidence` is numerically identical to `smart-calm` in the
  unicast, mixed, and shadowing summaries, and differs only slightly in the
  high-load scenario. The code path is active: it selects the shortest route
  candidate instead of the highest-confidence candidate. The current random
  topologies usually do not produce a meaningful length/confidence conflict.
  Add a targeted route-candidate unit test or a dedicated topology scenario
  before using this ablation as evidence that confidence ranking has no effect.
- The simulator is packet-level and does not replace waveform-level LoRa
  validation or board-level current measurements.
- The full paper at `paper/full2026/smart_calm_full_paper.tex` remains a
  working manuscript with author placeholders and an evaluation-plan section.
  The ICC results still need to be integrated into tables, figures, methods,
  and limitations before submission.

## Pending Publication Steps

1. Freeze the ICC result prefix and do not mix these CSVs with older
   `v1.1` or `v1.1.1` result sets.
2. Add the four scenario summaries to the manuscript and generate the final
   paper tables/figures.
3. Decide whether to add a targeted confidence-ranking scenario and rerun the
   full matrix if the ablation is required in the main claim.
4. Replace author placeholders and verify the final IEEE page limit and
   symposium choice.
5. Commit and push only after the manuscript and result version boundary are
   reviewed. No commit or push was performed in this run.

## Verification Commands

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m py_compile lora_mesh_sim.py analyze_results.py
tools/run_icc_experiments.sh
```
