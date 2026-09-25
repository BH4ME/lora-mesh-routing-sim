# LoRa Mesh Routing Simulator

Packet-level Python simulator for LoRa mesh routing research. The repository is
intended for developers and researchers who want to reproduce baseline
experiments, change topology/PHY/traffic parameters, and add new routing
protocols for comparison.

Licensed under MIT.

Current simulator version: `2.1.24` (model-informed route-score controls and
frozen repeated-pair ICC holdout; firmware prototype remains
`meshecho-firmware-v2.1.2`).

This is a compact packet-level Python simulator for comparing LoRa mesh routing
ideas under a fixed SX1262-style PHY profile.

It currently implements two behavior-equivalent baselines, standard quality
metric baselines, and MeshEcho:

- `meshtastic-like`: managed flooding with delayed rebroadcast and suppression
  when another copy is heard.
- `meshcore-like`: first unicast floods a route request, the destination replies
  on the reverse path, then later unicast packets use a cached source route.
- `meshecho`: confidence-aware source routing with bounded fallback forwarding
  (the legacy `calm` CLI name remains supported).
- `meshecho-calibrated`: optional MeshEcho variant that ranks a route by its
  weakest model-inferred per-hop PRR, without an extra hop penalty.
- `etx-mesh`: source routing that selects candidates by accumulated ETX
  (`1/PRR`) cost.
- `ett-mesh`: source routing that selects candidates by accumulated ETT
  (`ToA/PRR`) cost. In the fixed-SF ICC matrix, ETT is intentionally a sanity
  baseline and coincides numerically with ETX.
- `prr-product-mesh`: model-informed comparator that multiplies the per-hop
  PRRs inferred from received route requests; it has no route-miss fallback.
- `prr-product-fallback-mesh`: the same PRR-product score with MeshEcho's
  matched TTL-2 route-miss fallback budget.
- `minhop-mesh`: matched-discovery shortest-path baseline that ignores link
  quality after candidate exposure.
- `meshecho-ack-evict` and `prr-product-ack-evict-mesh`: optional ACK-timeout
  route-invalidation controls. They reduced ACK completion in the 2.1.24
  fading holdout and are not promoted as the default policy.
- `meshecho-no-confidence`, `meshecho-no-fallback`,
  `meshecho-no-hop-penalty`, and `meshecho-no-age-penalty`: MeshEcho
  component ablations used only for mechanism attribution.
- `meshecho-budgeted`: an optional one-extra-hop admission rule used as a
  reliability--airtime trade-off control, not a reliability improvement.
- The historical adaptive firmware/simulator line is retained for traceability
  but is not part of the ICC MeshEcho protocol matrix.

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

The historical 2.1.23 raw rows and paired summary are archived at
`results/meshecho_v2_1_23_icc2027_route_conflict.csv` and
`docs/results/meshecho_v2_1_23_icc2027_route_conflict.md`. The current
runner uses a 2.1.24 output prefix by default.

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

It compares the current MeshEcho route-miss fallback with the same MeshEcho
line after that fallback is disabled, using shared 20-seed main-scenario
inputs. The result is a sensitivity check, not a fully budget-matched
source-route comparison.

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

This runs six MeshEcho-facing configurations (`meshtastic`, `meshcore`, `etx`,
`ett`, `minhop`, and `meshecho`) over repeated-unicast, mixed traffic,
stronger-shadowing, and higher-load scenarios. Each scenario writes a
raw CSV, a text summary, and a long-format summary CSV with mean, standard
deviation, and 95% confidence intervals. See
[ICC 2027 Experiment Plan](docs/icc2027_experiment_plan.md) for the table
layout and reproducibility rules. The verified matrix is summarized in
[ICC 2027 Comparison](docs/results/icc2027_comparison.md).

The frozen 2.1.24 study uses seeds 41--50 only for development and untouched
seeds 51--70 for its holdout. Its primary holdout cycles four connected pairs
over 793 observed unicasts across 20 topology seeds, with matched RREQ timing,
6 dB temporal fading every 60 s, and a 600 s route TTL. The optional
`meshecho-calibrated` variant reaches 0.624 ACK PDR at 23.7 s airtime versus
0.509/21.2 s for the original `meshecho`. Its paired ACK gain is +0.1154
(95% CI [+0.0307,+0.2001]) at +2.467 s airtime. Against PRR-product with
matched fallback, the ACK difference is only +0.0026
[-0.0055,+0.0107]; no strong-baseline superiority follows. In the matching
static control, the calibrated-minus-original ACK difference is +0.0004
[-0.0741,+0.0748]. An isolated first-discovery check exposes identical
candidate sets for all 480 pairs: calibrated-minus-original is +0.0208
[-0.0129,+0.0546], and calibrated-minus-PRR-product is +0.0021
[-0.0056,+0.0098]. Both isolated intervals include zero. ACK-timeout route
eviction is adverse in the fading holdout (0.471 ACK PDR and 41.1 s airtime
for the MeshEcho variant). In the independently audited 30 s route-TTL
control on the same 793-unicast trace, calibrated MeshEcho falls to 0.320
ACK PDR and rises to 64.8 s airtime, versus 0.624/23.7 s at 600 s TTL.
The seed-paired 30-minus-600 s differences are -0.3043 ACK PDR
(95% CI [-0.3932,-0.2154]) and +41.05 s airtime
([31.40,50.70]). At 30 s TTL, its ACK difference from original MeshEcho
is +0.0215 [-0.0227,+0.0657], with no clear gain. See the
[short-TTL holdout](docs/results/meshecho_v2_1_24_icc2027_holdout51_70_feedback_fading_short_ttl.md),
[fading holdout](docs/results/meshecho_v2_1_24_icc2027_holdout51_70_feedback_fading.md),
[static control](docs/results/meshecho_v2_1_24_icc2027_holdout51_70_feedback_static.md),
and [isolated comparison](docs/results/meshecho_v2_1_24_icc2027_holdout51_70_isolated_first_discovery.md).

The historical 2.1.23 ICC primary matrix uses 50 nodes in an 8.25 km square,
SF7,
analytical pair-edge PRR >= 0.90, and 24 distinct directed pairs per seed.
It schedules exactly one unicast per pair over 600 s for each policy, using
holdout seeds 21--40 and a shared 2 s RREQ relay schedule. All 480 attempted
unicasts are reported, rather than describing the 24-pair pool as if it were
24 observed flows in a sparse Poisson workload. MeshEcho has 332/480
ACK-confirmed completions versus 266/480 for ETX; the paired seed-level
difference is +0.137 (95% CI [+0.090,+0.185]) with +1.9 s
[+1.6,+2.3] mean airtime per run. Candidate sets still match in only
148/480 sequential discoveries, so this is a system-level comparison, not
an isolated route-ranking estimate.

That release's separate isolated-first-discovery audit uses fresh simulator
state for each pair/policy. Candidate sets match in all 480 comparisons, and MeshEcho
minus ETX ACK completion is +0.163 [+0.121,+0.204] across the 20 topology
seeds. Under unconditioned random pairs, managed flooding outperforms
MeshEcho on ACK completion (0.736 versus 0.430) and airtime (39.7 versus
103.2 s); the paper retains this negative boundary. See the
[fixed-once report](docs/results/meshecho_v2_1_23_icc2027_matched_fixed_once.md),
[isolation report](docs/results/meshecho_v2_1_23_icc2027_isolated_first_discovery.md),
and [candidate-set audit](docs/results/meshecho_v2_1_23_icc2027_candidate_set_audit.md).

Run the current spreading-factor and offered-load sensitivity cases with the
same connected-pair quality contract:

```bash
python3 tools/run_icc_sensitivity_experiments.py
```

The runner uses a 2.1.24 output prefix by default. Historical 2.1.22
20-seed SF8 and higher-load results are archived under the
`meshecho_v2_1_22_icc2027_sensitivity_*` prefix. The cases are robustness
evidence and are not pooled with the fading holdout.

Run the repeated-pair cache-reuse and route-aging diagnostic:

```bash
python3 tools/run_icc_cache_experiment.py
```

This uses four connected pairs, unicast traffic at four flows/min, and
compares 600 s and 30 s route-cache TTLs. It reports cache hits, discovery
repairs, ACK/destination PDR, and airtime separately from the sparse primary
matrix; it is not pooled with the primary estimand.

At the 2.1.23 source revision, the unconditioned, deep-hop, and
temporal-fading generalization cases were run with:

```bash
python3 tools/run_icc_generalization_experiment.py \
  --seed0 21 --seeds 20 \
  --out-prefix meshecho_v2_1_23_icc2027_generalization
```

Do not use that historical output prefix from the current 2.1.24 checkout;
it would overwrite the archived 2.1.23 artifacts. The old runner wrote
separate 20-seed reports for random pairs, a 100-node
3--5-hop case, and repeated-pair temporal fading with 600 s and 30 s route
TTLs. The deep case uses a 21 km square because the earlier 20 km calibration
failed the per-seed 24-pair completeness gate for seed 12; that failed
calibration is retained in the state log.

Before submitting, use the [ICC 2027 submission checklist](docs/icc2027_submission_checklist.md)
to verify that the EDAS title and author order match the
[compiled manuscript](paper/icc2027/icc2027_lora_mesh.pdf).

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

For a one-shot MeshEcho mechanism check with the timeout-retry budget set to
zero, add:

```bash
python3 tools/run_fair_multihop_probe.py \
  --max-timeout-retries 0 \
  --csv results/meshecho_fair_budget_matched.csv \
  --report docs/results/meshecho_fair_budget_matched.md
```

The historical `--smart-max-timeout-retries` spelling remains accepted for
older scripts; the MeshEcho-facing name is `--max-timeout-retries`.

The probe also reports route-discovery attempts, source-side route-discovery
success rate, and the RREP/RREQ transmission ratio. Connected-pair runs with
very low discovery success are route-discovery stress checks, not neutral
data-plane benchmarks.

The ICC matrix script also runs a short connected-multihop quality gate by
default. It checks every seed before accepting the probe output: at least 10%
of direct links must have static PRR below 0.99, the requested connected pair
pool must be fully constructible, and its mean graph distance must be at least
2 hops. Override the probe with `ICC_QUALITY_*` variables, or set
`ICC_RUN_QUALITY_PROBE=0` only when reproducing an older run without the gate.
The generated diagnostic files use the matrix prefix plus
`_connected_multihop_quality`.

To run the gate directly:

```bash
python3 tools/run_fair_multihop_probe.py \
  --pair-mode connected-multihop \
  --min-direct-prr-below-0-99 0.10 \
  --min-selected-pair-mean-graph-hops 2.0
```

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
--min-direct-prr-below-0-99 0.10
--min-selected-pair-mean-graph-hops 2.0
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
