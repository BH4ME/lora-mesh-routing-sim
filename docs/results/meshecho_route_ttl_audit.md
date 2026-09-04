# MeshEcho Route-Cache Lifetime Sensitivity Audit

This paired audit isolates the effect of the source-route cache lifetime in the current harness. Topology, application trace, PHY settings, and seed values are shared across variants. The matched comparison equalizes cache lifetime only; it does not equalize discovery timing or recovery behavior.

- Seeds: `20`
- Main scenario: `50 nodes / 3000 m square / 1200 s / mixed / 8 fixed pairs`
- Offered load: `6.0 flows/min`
- Independent channel-reception stream: enabled

## Variant Results

| Variant | Route TTL (s) | ACK PDR | Destination PDR | Airtime (s) | Route-cache hits | Route-cache misses |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| meshcore-native-ttl-300 | 300 | 0.381 | 0.652 | 970.9 | 27.9 | 33.5 |
| meshcore-matched-ttl-600 | 600 | 0.519 | 0.722 | 905.5 | 37.8 | 23.7 |
| meshecho-ttl-600 | 600 | 0.728 | 0.766 | 847.3 | 38.7 | 22.8 |

## Paired Differences

Values are first variant minus second variant, paired by seed; the interval is a two-sided 95% t interval.

| Comparison | ACK-PDR delta | Destination-PDR delta | Airtime delta (s) |
| --- | ---: | ---: | ---: |
| meshcore-matched-ttl-600 minus meshcore-native-ttl-300 | +0.138 +/- 0.031 | +0.070 +/- 0.034 | -65.4 +/- 14.1 |
| meshecho-ttl-600 minus meshcore-matched-ttl-600 | +0.209 +/- 0.071 | +0.045 +/- 0.084 | -58.2 +/- 19.2 |
| meshecho-ttl-600 minus meshcore-native-ttl-300 | +0.347 +/- 0.061 | +0.115 +/- 0.084 | -123.6 +/- 26.8 |

## Interpretation

- The 300 s versus 600 s MeshCore-like comparison estimates the effect of cache lifetime without changing its routing logic.
- The 600 s CALM/MeshEcho versus 600 s MeshCore-like comparison removes the route-lifetime mismatch from the headline comparison, but remains a protocol-bundle comparison.
- This audit does not remove the fixed-pair, high-PRR/one-hop, or native-recovery limitations of the main matrix.

## Reproduction

```sh
python3 tools/run_route_ttl_audit.py
```
