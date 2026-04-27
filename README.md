# LoRa Mesh Routing Simulator

Packet-level Python simulator for LoRa mesh routing research. The repository is
intended for developers and researchers who want to reproduce baseline
experiments, change topology/PHY/traffic parameters, and add new routing
protocols for comparison.

Licensed under MIT.

This is a compact packet-level Python simulator for comparing LoRa mesh routing
ideas under a fixed SX1262-style PHY profile.

It currently implements two behavior-equivalent baselines:

- `meshtastic-like`: managed flooding with delayed rebroadcast and suppression
  when another copy is heard.
- `meshcore-like`: first unicast floods a route request, the destination replies
  on the reverse path, then later unicast packets use a cached source route.

The simulator is not a firmware clone. It is a research harness for comparing
routing behavior under the same topology, traffic, propagation, collision, and
LoRa airtime model.

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
--path-loss-exp 2.7
--shadow-sigma-db 4
--max-hops 7
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
all protocols share the same generated values, making comparisons fair.

## Metrics

The table and CSV include:

- `unicast_pdr`
- `broadcast_coverage`
- `avg_delay_s`
- `tx_count`
- `data_tx`
- `control_tx`
- `total_airtime_s`
- `airtime_per_delivery_s`
- `collision_fail`
- `duplicate_rx`
- `suppressed_forwards`
- `route_cache_hits`
- `route_cache_misses`

For a paper, repeat each scenario with many seeds and report mean values with
confidence intervals.

## Included Results

The `results/` directory contains example CSV outputs generated from the current
simulator:

- `baseline_smoke.csv`: small smoke-test run.
- `exp_50n_unicast_pairs.csv`: 50-node repeated-unicast baseline comparison.
- `exp_50n_mixed.csv`: 50-node mixed-traffic baseline comparison.

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
