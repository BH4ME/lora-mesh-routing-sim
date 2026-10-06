# Three-Protocol Comparison

Protocols compared: `Meshtastic-like`, `MeshCore-like`, and `Smart-CALM v1.1`.

Scenarios use `50 nodes / 3000 m / 1200 s / mixed traffic / pair-count 8 / 20 seeds` unless noted.

This report is pinned to the archived Smart-CALM v1.1 CSV files. The later v2 algorithm is intentionally excluded here. ACK-confirmed variants are reported separately in `results/ack_aware_comparison/`.

| Scenario | Protocol | Unicast PDR | Airtime (s) | Collision failures |
| --- | --- | ---: | ---: | ---: |
| Mixed traffic | Meshtastic-like | 0.948 | 1170 | 122048 |
| Mixed traffic | MeshCore-like | 0.642 | 962 | 82047 |
| Mixed traffic | Smart-CALM v1.1 | 0.962 | 896 | 79562 |
| High shadowing | Meshtastic-like | 0.950 | 1178 | 121836 |
| High shadowing | MeshCore-like | 0.633 | 970 | 83424 |
| High shadowing | Smart-CALM v1.1 | 0.963 | 876 | 78064 |
| High offered load | Meshtastic-like | 0.917 | 1875 | 198166 |
| High offered load | MeshCore-like | 0.488 | 1415 | 125205 |
| High offered load | Smart-CALM v1.1 | 0.937 | 1410 | 131345 |

## Meeting Takeaway

- `Meshtastic-like` keeps strong reliability, but spends the most airtime and creates the most collisions.
- `MeshCore-like` is cheaper than flooding, but loses unicast reliability in mixed and stressed traffic.
- `Smart-CALM v1.1` improves unicast PDR over `MeshCore-like` while staying materially below `Meshtastic-like` airtime in the three archived scenarios.
- Under high offered load, `Smart-CALM v1.1` stays close to managed flooding on reliability while still reducing channel occupancy.
