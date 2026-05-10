# Three-Protocol Comparison

Protocols compared: `Meshtastic-like`, `MeshCore-like`, and `Smart-CALM`.

Scenarios use `50 nodes / 3000 m / 1200 s / mixed traffic / pair-count 8 / 20 seeds` unless noted.

| Scenario | Protocol | Unicast PDR | Airtime (s) | Collision failures |
| --- | --- | ---: | ---: | ---: |
| Mixed traffic | Meshtastic-like | 0.948 | 1170 | 122048 |
| Mixed traffic | MeshCore-like | 0.642 | 962 | 82047 |
| Mixed traffic | Smart-CALM | 0.962 | 935 | 83492 |
| High shadowing | Meshtastic-like | 0.950 | 1178 | 121836 |
| High shadowing | MeshCore-like | 0.633 | 970 | 83424 |
| High shadowing | Smart-CALM | 0.963 | 914 | 82047 |
| High offered load | Meshtastic-like | 0.917 | 1875 | 198166 |
| High offered load | MeshCore-like | 0.488 | 1415 | 125205 |
| High offered load | Smart-CALM | 0.923 | 1506 | 140102 |

## Meeting Takeaway

- `Meshtastic-like` keeps the highest reliability, but spends the most airtime and creates the most collisions.
- `MeshCore-like` is cheaper than flooding, but loses unicast reliability in mixed and stressed traffic.
- `Smart-CALM` is strongest under stress: it improves unicast PDR over MeshCore-like while staying far below Meshtastic-like airtime.
