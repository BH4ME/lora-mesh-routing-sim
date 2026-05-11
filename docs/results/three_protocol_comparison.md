# Three-Protocol Comparison

Protocols compared: `Meshtastic-like`, `MeshCore-like`, and `Smart-CALM`.

Scenarios use `50 nodes / 3000 m / 1200 s / mixed traffic / pair-count 8 / 20 seeds` unless noted.

| Scenario | Protocol | Unicast PDR | Airtime (s) | Collision failures |
| --- | --- | ---: | ---: | ---: |
| Mixed traffic | Meshtastic-like | 0.948 | 1170 | 122048 |
| Mixed traffic | MeshCore-like | 0.642 | 962 | 82047 |
| Mixed traffic | Smart-CALM | 0.962 | 828 | 73496 |
| High shadowing | Meshtastic-like | 0.950 | 1178 | 121836 |
| High shadowing | MeshCore-like | 0.633 | 970 | 83424 |
| High shadowing | Smart-CALM | 0.969 | 819 | 72980 |
| High offered load | Meshtastic-like | 0.917 | 1875 | 198166 |
| High offered load | MeshCore-like | 0.488 | 1415 | 125205 |
| High offered load | Smart-CALM | 0.932 | 1318 | 122431 |

## Meeting Takeaway

- `Meshtastic-like` keeps strong reliability, but spends the most airtime and creates the most collisions.
- `MeshCore-like` is cheaper than flooding, but loses unicast reliability in mixed and stressed traffic.
- `Smart-CALM v1.1.1` keeps the reliability target while reducing both airtime and collision failures below the MeshCore-like baseline in all three scenarios.
- Under high offered load, `Smart-CALM v1.1.1` trades about half a PDR point versus v1.1 for a clear reduction in channel occupancy and collisions.
