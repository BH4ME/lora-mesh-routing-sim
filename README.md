# LoRa Mesh Routing Simulator

Packet-level Python simulator for LoRa mesh routing research. The repository is
intended for developers and researchers who want to reproduce baseline
experiments, change topology/PHY/traffic parameters, and add new routing
protocols for comparison.

Licensed under MIT.

Current repository release: `2.1.13` (paper/results package; firmware prototype
remains `meshecho-firmware-v2.1.2`).

This is a compact packet-level Python simulator for comparing LoRa mesh routing
ideas under a fixed SX1262-style PHY profile.

It currently implements two behavior-equivalent baselines and the CALM family:

- `meshtastic-like`: managed flooding with delayed rebroadcast and suppression
  when another copy is heard.
- `meshcore-like`: first unicast floods a route request, the destination replies
  on the reverse path, then later unicast packets use a cached source route.
- `calm-mesh`: confidence-aware source routing with bounded fallback forwarding.
- `smart-calm`: MCU-friendly profile-based online adaptation, plus explicit
  `smart-calm-static`, `smart-calm-no-fallback`, and
  `smart-calm-no-confidence` ablations.

The simulator is not a firmware clone. It is a research harness for comparing
routing behavior under the same topology, traffic, propagation, collision, and
LoRa airtime model.

## Documentation

The Markdown documents are organized under [docs/README.md](docs/README.md).
Research plans, result narratives, firmware notes, and project-history files are
kept in separate folders so the repository root stays focused on the simulator
entry point.

For source-file ownership and folder purposes, see
[Source Layout](docs/source-layout.md).

See [Terminology and Formulas](docs/reference/terminology-and-formulas.md) for
the English terms, abbreviations, metrics, and formulas used by the simulator.

## Firmware Prototype

The `firmware/esp32_smart_calm/` directory contains a burnable ESP32/PlatformIO
prototype for the Smart-CALM control layer on directly attached LoRa radios. It
is our own controller and compact over-the-air frame format built on top of
RadioLib, not a Meshtastic or MeshCore fork.

The current firmware supports ESP32 + SX1262 and ESP32 + SX127x/RFM9x build
targets. It sends/receives CRC-protected Smart-CALM frames, status beacons, and
a custom `RREQ/RREP/DATA/ACK` mesh data plane. The `2.1.2` firmware release
keeps the bounded fallback delivery with reverse-path ACKs, prevents
post-ACK timeout retries, emits LF-normalized experiment CSVs, and exposes
richer delivery and route-aging telemetry while preserving the ICC comparison
freeze.

Detailed firmware notes are in
[ESP32 Smart-CALM Direct-LoRa Firmware](docs/firmware/esp32_smart_calm.md).

```bash
cd firmware/esp32_smart_calm
pio run -e esp32dev_sx1262
pio run -e esp32dev_sx127x
```

If you want the current trained prior in the firmware header, run:

```bash
python3 tools/generate_smart_calm_prior_header.py
```

## Run

Clone and enter the project:

```bash
git clone https://github.com/BH4ME/lora-mesh-routing-sim.git
cd lora-mesh-routing-sim
```

No third-party Python package is required at the moment. Python 3.9+ is enough.

```bash
python3 lora_mesh_sim.py --protocol both --nodes 40 --duration-s 1800 --traffic unicast --seeds 3
```

Use repeated unicast conversations, which is the scenario where MeshCore-style
route caching should help:

```bash
python3 lora_mesh_sim.py --protocol both --nodes 40 --duration-s 1800 --traffic unicast --pair-count 6 --seeds 5
```

Write CSV:

```bash
python3 lora_mesh_sim.py --protocol both --nodes 80 --duration-s 3600 --traffic mixed --pair-count 10 --seeds 20 --csv results/baselines.csv
```

Aggregate a multi-seed CSV:

```bash
python3 analyze_results.py results/baselines.csv
```

Run the controlled route-conflict experiment, which isolates confidence-based
candidate selection from online learning and fallback recovery:

```bash
python3 tools/run_route_conflict_experiment.py
```

It writes raw per-seed rows to `results/meshecho_route_conflict.csv` and the
paired summary to `docs/results/meshecho_route_conflict.md`.

Run the fairness audit with null, moderate, and reverse weak-link controls:

```bash
python3 tools/run_route_conflict_fairness_audit.py
```

It writes `results/meshecho_route_conflict_fairness.csv` and
`docs/results/meshecho_route_conflict_fairness.md`. The audit is a controlled
mechanism check and does not replace random-topology or high-load evaluation.

Run the paired recovery-budget sensitivity audit:

```bash
python3 tools/run_recovery_budget_audit.py
```

It compares the current CALM route-miss fallback with the same CALM line after
that fallback is disabled, using shared 20-seed main-scenario inputs. The
result is a sensitivity check, not a fully budget-matched MeshCore comparison.

Run the paired route-cache lifetime audit:

```bash
python3 tools/run_route_ttl_audit.py
```

It matches MeshCore-like's route-cache lifetime to MeshEcho's 600 s setting and
reports the native-versus-matched source-route result separately.

For the ICC comparison matrix, run:

```bash
tools/run_icc_experiments.sh
```

Fresh matrices from this script use a 600 s MeshCore-like route-cache TTL to
match MeshEcho. Set `MESHCORE_ROUTE_TTL_S=300` only to reproduce the legacy
native baseline.

This runs seven configurations (`meshtastic`, `meshcore`, `calm`, full
`smart-calm`, and three Smart-CALM ablations) over repeated-unicast, mixed
traffic, stronger-shadowing, and higher-load scenarios. Each scenario writes a
raw CSV, a text summary, and a long-format summary CSV with mean, standard
deviation, and 95% confidence intervals. See
[ICC 2027 Experiment Plan](docs/icc2027_experiment_plan.md) for the table
layout and reproducibility rules. The verified matrix is summarized in
[ICC 2027 Comparison](docs/results/icc2027_comparison.md).

New ICC matrices use an isolated channel-reception stream by default, keeping
it separate from forwarding jitter and learning exploration. To make that
explicit, run:

```bash
INDEPENDENT_RNG_STREAMS=1 OUT_PREFIX=meshecho_fair \
  tools/run_icc_experiments.sh
```

Set `INDEPENDENT_RNG_STREAMS=0` only when reproducing legacy frozen result
files. The split mode improves experimental isolation, but it does not make
protocol executions event-by-event identical when they generate different
numbers of transmissions.

Run the non-saturated random-pair fairness probe:

```bash
python3 tools/run_fair_multihop_probe.py
```

The default probe uses 50 nodes in an 18 km square, SF7, random
source-destination pairs, 10 seeds, and independent channel-reception
randomness. It writes direct-link PRR quantiles, cached-route hop diagnostics,
protocol metrics, and paired ablation values to
`results/meshecho_fair_multihop_probe.csv` and
`docs/results/meshecho_fair_multihop_probe.md`. Use this probe to check whether
the conclusion survives outside the fixed-pair, link-friendly main matrix.

For a one-shot mechanism check with Smart-CALM timeout retries disabled, add:

```bash
python3 tools/run_fair_multihop_probe.py \
  --smart-max-timeout-retries 0 \
  --csv results/meshecho_fair_budget_matched.csv \
  --report docs/results/meshecho_fair_budget_matched.md
```

The probe also reports route-discovery attempts, source-side route-discovery
success rate, and the RREP/RREQ transmission ratio. Connected-pair runs with
very low discovery success are route-discovery stress checks, not neutral
data-plane benchmarks.

Useful parameters:

```bash
--nodes 80
--area-m 3000
--duration-s 3600
--rate-per-min 6
--traffic unicast|broadcast|mixed
--pair-count 10
--seeds 30
--sf 9
--bw-hz 125000
--cr 1
--payload-bytes 32
--tx-power-dbm 17
--tx-current-ma 120
--rx-current-ma 10.3
--supply-voltage-v 3.3
--path-loss-exp 2.7
--shadow-sigma-db 4
--max-hops 7
--independent-rng-streams
```

Example scenarios:

```bash
# Repeated unicast conversations, where route caching should help.
python3 lora_mesh_sim.py --protocol both --nodes 50 --area-m 3000 --duration-s 1200 --traffic unicast --rate-per-min 6 --pair-count 8 --seeds 20 --csv results/exp_50n_unicast_pairs.csv

# Mixed traffic, with both broadcast and unicast messages.
python3 lora_mesh_sim.py --protocol both --nodes 50 --area-m 3000 --duration-s 1200 --traffic mixed --rate-per-min 6 --pair-count 8 --seeds 20 --csv results/exp_50n_mixed.csv
```

## Model

The PHY model uses:

- Log-distance path loss plus log-normal shadowing.
- Fixed LoRa SF/BW/CR for every node.
- LoRa time-on-air.
- Half-duplex radios.
- Collision failure unless the desired signal exceeds the strongest interferer
  by the capture threshold.
- Probabilistic reception from SNR margin.

The simulator produces virtual RSSI/SNR values from the propagation model. A
real deployment would obtain those values from the SX1262 driver; in simulation,
all protocols share the same topology, traffic trace, and static per-link
shadowing realization for a given seed.

## Metrics

The table and CSV include:

- `unicast_pdr` ACK-confirmed source delivery ratio
- `destination_unicast_pdr` destination DATA arrival ratio
- `broadcast_coverage`
- `avg_delay_s`
- `tx_count`
- `data_tx`
- `control_tx`
- `ack_tx`
- `total_airtime_s`
- `channel_busy_ratio`
- `total_energy_j`
- `energy_per_delivery_j`
- `airtime_per_delivery_s`
- `packet_reception_ratio`
- `collision_fail`
- `collision_rate`
- `duplicate_rx`
- `suppressed_forwards`
- `route_cache_hits`
- `route_cache_misses`

For a paper, repeat each scenario with many seeds and report mean values with
confidence intervals.

The current release treats the original 50-node, 3000 m, fixed-pair matrix as
a contention-oriented cache-efficiency case. It is not a neutral multi-hop
benchmark because the default direct links are nearly all high-PRR and the
native recovery budgets differ. Use the matched-TTL audit and the random-pair
fairness probe before making general routing claims. See
[ICC 2027 Experiment Plan](docs/icc2027_experiment_plan.md).

## Included Results

The `results/` directory contains example CSV outputs generated from the current
simulator:

- `baseline_smoke.csv`: small smoke-test run.
- `exp_50n_unicast_pairs.csv`: 50-node repeated-unicast baseline comparison.
- `exp_50n_mixed.csv`: 50-node mixed-traffic baseline comparison.

Historical note: CSV files generated before the ACK-aware update use the old
`unicast_pdr` definition (destination DATA arrival). New runs treat
`unicast_pdr` as source ACK-confirmed delivery and expose the old view as
`destination_unicast_pdr`, so avoid directly mixing old/new CSVs in one plot.

Regenerate or replace them with your own scenarios as the routing model evolves.

## Adding a Protocol

Add a new class that inherits from `RoutingProtocol` in `lora_mesh_sim.py`, then
register it in `build_protocol()`.

The key methods are:

```python
def send_app(self, src: int, dst: int, flow_id: int) -> None:
    ...

def on_receive(self, receiver: int, packet: Packet, rx: RxInfo) -> None:
    ...
```

`RxInfo` contains simulated receive information such as RSSI-like receive power,
SNR, SINR, and collision status. This is where an airtime-aware or SNR-aware
routing policy can make forwarding decisions.

## Scope

This is a packet-level simulator, not a physical waveform simulator and not a
line-by-line clone of Meshtastic or MeshCore firmware. The included baselines
are behavior-equivalent research models designed for fair comparison under the
same PHY/channel/traffic assumptions.
