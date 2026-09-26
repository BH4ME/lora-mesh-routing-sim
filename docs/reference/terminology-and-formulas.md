# Terminology and Formulas

This document collects the English terms, abbreviations, metrics, and formulas
used by the LoRa Mesh Routing Simulator. It is written for developers who want
to change simulation parameters or add new routing protocols.

## Routing Terms

| Term | 中文解释 | Meaning in this project |
| --- | --- | --- |
| LoRa Mesh | LoRa 网状网络 | A multi-hop LoRa network where packets can be relayed by intermediate nodes. |
| Node | 节点 | A simulated LoRa device with a position, role, and radio state. |
| Router | 路由节点 | A normal relay-capable node. |
| Repeater | 固定中继节点 | A relay-capable node that can be given forwarding priority. |
| Unicast | 单播 | One source sends a packet to one specific destination. |
| Broadcast | 广播 | One source sends a packet intended for all reachable nodes. |
| Mixed traffic | 混合流量 | A traffic pattern containing both unicast and broadcast packets. |
| Flooding | 洪泛 | A packet is rebroadcast by relay nodes so it can spread through the mesh. |
| Managed flooding | 受控洪泛 | Flooding with delayed forwarding and suppression of redundant rebroadcasts. |
| Rebroadcast suppression | 转发抑制 | A node cancels its pending rebroadcast after hearing another copy. |
| Route discovery | 路由发现 | The source floods a route request to discover a path to the destination. |
| Route request, RREQ | 路由请求 | A control packet used to discover a path. |
| Route reply, RREP | 路由回复 | A control packet returned by the destination along the reverse path. |
| Acknowledgment, ACK | 确认包 | A unicast control packet returned to the source after the destination receives DATA. |
| Route cache | 路由缓存 | A stored path reused for later unicast packets. |
| Source route | 源路由 | A packet carries the complete path to the destination. |
| Path | 路径 | An ordered node list, such as `A -> B -> C -> D`. |
| Hop | 跳 | One wireless transmission from one node to another. |
| TTL / hop limit | 生存时间 / 最大跳数 | The maximum number of remaining relays allowed for a packet. |

## Radio and PHY Terms

| Term | 中文解释 | Meaning |
| --- | --- | --- |
| PHY | 物理层 | The radio-layer model: SF, bandwidth, coding rate, airtime, propagation, and reception. |
| SF, Spreading Factor | 扩频因子 | LoRa spreading factor. Higher SF improves sensitivity but increases airtime. |
| BW, Bandwidth | 带宽 | LoRa bandwidth in Hz, for example `125000`. |
| CR, Coding Rate | 编码率 | LoRa forward-error-correction coding-rate index in the simulator. |
| Tx power | 发射功率 | Transmit power in dBm. |
| RSSI / received power | 接收信号强度 | Simulated receive power in dBm. |
| Noise floor | 噪声底 | Receiver thermal noise plus noise figure. |
| SNR | 信噪比 | Signal-to-noise ratio in dB. |
| SINR | 信干噪比 | Signal-to-interference-plus-noise ratio in dB. Used when packets overlap. |
| SNR margin | SNR 余量 | Difference between measured SNR and the required SNR for the configured SF. |
| ToA, Time on Air | 空中时间 / 空口占用时间 | How long one packet occupies the wireless channel. |
| Half-duplex | 半双工 | A node cannot receive while it is transmitting. |
| Collision | 碰撞 | Two or more overlapping transmissions interfere at a receiver. |
| Capture effect | 捕获效应 | A strong packet can still be decoded if it is sufficiently stronger than interference. |
| PRR, Packet Reception Ratio | 包接收率 | Probability or ratio that a packet is received successfully over a link. |
| PDR, Packet Delivery Ratio | 包投递率 | Ratio of application packets delivered to their intended destination. |

## Command-Line Parameters

| Parameter | Meaning |
| --- | --- |
| `--protocol` | Which protocol to run: an individual protocol, `both`, `all`, `all4`, or `icc` for the full seven-configuration comparison. |
| `--nodes` | Number of simulated nodes. |
| `--area-m` | Side length of the square simulation area in meters. |
| `--duration-s` | Simulation duration in seconds. |
| `--rate-per-min` | Average application packet generation rate. |
| `--traffic` | Traffic type: `unicast`, `broadcast`, or `mixed`. |
| `--pair-count` | Number of repeated unicast source/destination pairs. This helps test route caching. |
| `--seeds` | Number of repeated random seeds. |
| `--seed0` | First random seed. |
| `--max-hops` | Maximum relay count for a packet. |
| `--repeater-ratio` | Fraction of nodes assigned the `repeater` role. |
| `--sf` | LoRa spreading factor. |
| `--bw-hz` | LoRa bandwidth in Hz. |
| `--cr` | LoRa coding-rate index. `1` means 4/5 in the simulator. |
| `--payload-bytes` | Payload size used for airtime calculation. |
| `--tx-power-dbm` | Transmit power in dBm. |
| `--tx-current-ma` | Transmit current used for energy accounting. |
| `--rx-current-ma` | Receive/listen current used for energy accounting. |
| `--supply-voltage-v` | Supply voltage used for energy accounting. |
| `--path-loss-exp` | Path-loss exponent. Larger values mean faster signal decay with distance. |
| `--shadow-sigma-db` | Standard deviation of log-normal shadowing in dB. |
| `--capture-threshold-db` | Required signal advantage for capture during collision. |
| `--csv` | Output CSV path. |

## LoRa Airtime Formula

The simulator uses a standard LoRa time-on-air calculation. Let:

```text
SF = spreading factor
BW = bandwidth in Hz
CR = coding-rate index, where 1 means 4/5
PL = payload size in bytes
Npreamble = preamble symbols
IH = 0 for explicit header, 1 for implicit header
CRC = 1 if CRC is enabled, otherwise 0
DE = 1 when low-data-rate optimization is enabled, otherwise 0
```

Symbol time:

```text
Tsym = 2^SF / BW
```

Preamble time:

```text
Tpreamble = (Npreamble + 4.25) * Tsym
```

Payload symbol count:

```text
Npayload = 8 + max(
    ceil((8PL - 4SF + 28 + 16CRC - 20IH) / (4 * (SF - 2DE))) * (CR + 4),
    0
)
```

Packet time on air:

```text
ToA = Tpreamble + Npayload * Tsym
```

In the default configuration:

```text
SF = 9
BW = 125000 Hz
CR = 1
payload = 32 bytes
```

the simulator computes a fixed per-packet airtime and then adds that value to
`total_airtime_s` every time any node transmits a packet.

## Propagation and RSSI Formula

The simulator places nodes in a two-dimensional square area. The distance
between nodes `i` and `j` is:

```text
d_ij = sqrt((x_i - x_j)^2 + (y_i - y_j)^2)
```

The log-distance path-loss model is:

```text
PathLoss(d) = PL0 + 10 * n * log10(d / d0) + X_sigma
```

where:

```text
PL0      = free-space path loss at d0 = 1 m
n        = path-loss exponent
X_sigma  = log-normal shadowing, sampled from Normal(0, sigma)
```

Received power is:

```text
RSSI_dBm = TxPower_dBm - PathLoss(d)
```

The simulator draws one shadowing value per unordered node pair and seed, then
reuses it for every packet on that link. This keeps the propagation realization
identical across protocol runs while avoiding a full waveform model. Temporal
fading is not modeled in the current version.

## Noise, SNR, and SINR

Noise floor:

```text
NoiseFloor_dBm = -174 + 10 * log10(BW) + NoiseFigure
```

SNR without overlapping interference:

```text
SNR_dB = RSSI_dBm - NoiseFloor_dBm
```

When there are overlapping transmissions, the simulator converts dBm values to
milliwatts:

```text
P_mW = 10^(P_dBm / 10)
```

Then it computes:

```text
SINR = P_signal / (P_noise + sum(P_interference))
SINR_dB = 10 * log10(SINR)
```

## Required SNR and SNR Margin

The simulator uses approximate LoRa demodulation thresholds:

| SF | Required SNR |
| --- | ---: |
| SF7 | -7.5 dB |
| SF8 | -10.0 dB |
| SF9 | -12.5 dB |
| SF10 | -15.0 dB |
| SF11 | -17.5 dB |
| SF12 | -20.0 dB |

SNR margin:

```text
SNR_margin = SNR_dB - RequiredSNR(SF)
```

Example with SF9:

```text
RequiredSNR(SF9) = -12.5 dB
SNR = -8.0 dB
SNR_margin = -8.0 - (-12.5) = 4.5 dB
```

Higher SNR margin means the link is more stable.

## PRR Formula

The simulator maps SNR margin into packet reception probability with a logistic
function:

```text
PRR = 1 / (1 + exp(-k * SNR_margin))
```

where `k` is `prr_slope` in the radio configuration. The default value is:

```text
k = 1.15
```

This means links far above the required SNR are likely to receive successfully,
while links below the required SNR are likely to fail.

## Collision and Capture Rule

For a receiver, transmissions overlap if their time intervals intersect:

```text
tx_a.start < tx_b.end and tx_b.start < tx_a.end
```

If there is interference, the desired packet is dropped unless it is stronger
than the strongest interferer by at least the capture threshold:

```text
Signal_dBm >= StrongestInterference_dBm + CaptureThreshold_dB
```

If the capture condition holds, the simulator computes SINR and applies the PRR
formula to decide whether the packet is received.

## Delivery Metrics

Unicast PDR:

```text
unicast_pdr = ack_confirmed_unicast_flows / total_unicast_flows
```

Destination unicast PDR:

```text
destination_unicast_pdr = destination_data_arrivals / total_unicast_flows
```

Broadcast coverage:

```text
broadcast_coverage =
    total_broadcast_receivers / (broadcast_flows * (node_count - 1))
```

Average unicast delay:

```text
avg_delay_s =
    mean(ack_time - created_time for each ACK-confirmed unicast flow)
```

Total airtime:

```text
total_airtime_s = sum(ToA for every transmitted packet)
```

Airtime per delivered packet:

```text
airtime_per_delivery_s =
    total_airtime_s / (ack_confirmed_unicast_flows + total_broadcast_receivers)
```

This metric is important because it shows how much channel time the network
spends for each successful delivery.

## CSV Metrics

| CSV column | Meaning |
| --- | --- |
| `protocol` | Protocol name. |
| `seed` | Random seed used for topology, traffic, and random radio effects. |
| `duration_s` | Simulated time in seconds. |
| `flows` | Total application-level flows generated. |
| `unicast_flows` | Number of unicast flows. |
| `broadcast_flows` | Number of broadcast flows. |
| `unicast_pdr` | ACK-confirmed unicast packet delivery ratio. |
| `destination_unicast_pdr` | Destination DATA arrival ratio before ACK confirmation. |
| `broadcast_coverage` | Broadcast delivery coverage. |
| `avg_delay_s` | Average delay of delivered unicast flows. |
| `tx_count` | Total number of packet transmissions. |
| `data_tx` | Number of data-packet transmissions. |
| `control_tx` | Number of control-packet transmissions, including RREQ, RREP, and unicast ACK. |
| `ack_tx` | Number of ACK transmissions. |
| `total_airtime_s` | Sum of all packet time-on-air values. |
| `airtime_per_delivery_s` | Airtime cost per successful delivery. |
| `rx_success` | Successful packet receptions at receivers. |
| `rx_fail` | Failed receive attempts. |
| `collision_fail` | Receive failures caused by collision without capture. |
| `duplicate_rx` | Duplicate receptions or duplicate flooded packets. |
| `suppressed_forwards` | Pending forwards canceled after hearing another copy. |
| `route_requests` | RREQ transmissions. |
| `route_replies` | RREP transmissions. |
| `route_cache_hits` | Times a cached route is reused. |
| `route_cache_misses` | Times a route discovery is needed. |

Compatibility note: legacy CSV artifacts generated before ACK-aware metrics
used `unicast_pdr` to mean destination DATA arrival ratio. Re-run those
experiments if you need strict comparability with current ACK-confirmed
`unicast_pdr`.

## Baseline Protocol Logic

### Meshtastic-like Managed Flooding

The simulator model:

```text
1. A source transmits a DATA packet.
2. A relay-capable node that hears a new DATA packet schedules a delayed rebroadcast.
3. If the node hears another copy before its scheduled rebroadcast, it cancels its own forwarding.
4. A packet stops when TTL reaches zero or the destination receives it.
```

Forwarding delay includes random jitter and an SNR-based penalty:

```text
SNR_penalty = clamp((8 - SNR_margin) / 8, 0, 1) * 0.6
Delay = base_delay + SNR_penalty + random_jitter - role_discount
```

This gives stronger or more suitable relays a chance to forward earlier.

### MeshCore-like Path Cache / Source Route

The simulator model:

```text
1. If the source has no cached route, it floods an RREQ.
2. The destination returns an RREP along the reverse discovered path.
3. The source caches the discovered path.
4. Later unicast DATA packets carry the complete source route.
5. Only the next node on the source route forwards the packet.
6. The destination returns an ACK along the reverse source route.
```

This reduces redundant transmissions when repeated unicast pairs reuse the same
path, but a weak hop can reduce delivery probability because the model does not
currently include per-hop retransmission or local route repair. ACKs are counted
as control transmissions and contribute to total airtime.

## Random Seed

`seed` controls the random number generator. It affects:

```text
node positions
traffic generation times
source/destination pairs
shadowing samples
probabilistic packet reception
forwarding jitter
```

Running many seeds is necessary because one random topology can be unusually
easy or unusually difficult. For paper-style experiments, report mean and
standard deviation over many seeds.
