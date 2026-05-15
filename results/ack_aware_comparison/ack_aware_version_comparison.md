# ACK-Aware Smart-CALM Version Comparison

This report compares only `Smart-CALM`. The `previous` rows are archived non-ACK CSVs where `unicast_pdr` means destination DATA arrival; the `ACK-aware` rows are regenerated so `unicast_pdr` means source-side ACK confirmation.

Scenarios use `50 nodes / 3000 m / 1200 s / mixed traffic / pair-count 8 / 20 seeds` unless noted.

| Scenario | Run | ACK-confirmed PDR | Destination DATA PDR | Airtime (s) | Collision failures | Fallback forwards | ACK tx |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Mixed traffic | v1.1 previous | 0.962 | n/a | 896 | 79562 | 406 | n/a |
| Mixed traffic | v1.1 ACK-aware | 0.956 | n/a | 884 | 78531 | 309 | 63 |
| Mixed traffic | v1.1.1 previous | 0.962 | n/a | 828 | 73496 | 114 | n/a |
| Mixed traffic | Latest ACK-aware | 0.957 | n/a | 846 | 75265 | 140 | 63 |
| High shadowing | v1.1 previous | 0.963 | n/a | 876 | 78064 | 337 | n/a |
| High shadowing | v1.1 ACK-aware | 0.965 | n/a | 912 | 82024 | 413 | 62 |
| High shadowing | v1.1.1 previous | 0.969 | n/a | 819 | 72980 | 95 | n/a |
| High shadowing | Latest ACK-aware | 0.959 | n/a | 858 | 76804 | 202 | 62 |
| High offered load | v1.1 previous | 0.937 | n/a | 1410 | 131345 | 841 | n/a |
| High offered load | v1.1 ACK-aware | 0.912 | n/a | 1445 | 134234 | 848 | 103 |
| High offered load | v1.1.1 previous | 0.932 | n/a | 1318 | 122431 | 444 | n/a |
| High offered load | Latest ACK-aware | 0.920 | n/a | 1380 | 128378 | 577 | 104 |

## Deltas

| Scenario | v1.1 ACK PDR delta | Latest ACK PDR delta | Latest ACK vs v1.1 ACK PDR | Latest ACK vs v1.1 ACK airtime |
| --- | ---: | ---: | ---: | ---: |
| Mixed traffic | -0.005 | -0.005 | 0.000 | -38 s |
| High shadowing | 0.001 | -0.010 | -0.006 | -54 s |
| High offered load | -0.024 | -0.012 | 0.008 | -65 s |
