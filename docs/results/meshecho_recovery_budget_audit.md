# MeshEcho Recovery-Budget Sensitivity Audit

This paired audit isolates the contribution of CALM route-miss fallback. Topology, application trace, PHY settings, and seed values are shared across variants. It is a sensitivity experiment, not a claim that MeshCore-like has an identical recovery implementation.

- Seeds: `20`
- Main scenario: `50 nodes / 3000 m square / 1200 s / mixed / 8 fixed pairs`
- Offered load: `6.0 flows/min`
- Independent channel-reception stream: enabled

## Variant Results

| Variant | ACK PDR | Destination PDR | Airtime (s) | Collision failures | Fallback forwards | Route-discovery attempts | Route-discovery success rate |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| meshcore-reference | 0.381 | 0.652 | 970.9 | 82390.1 | 0.0 | 19.6 | 0.834 |
| calm-route-miss-fallback | 0.728 | 0.766 | 847.3 | 75526.9 | 62.4 | 15.9 | 0.798 |
| calm-no-route-miss-fallback | 0.719 | 0.744 | 831.4 | 73162.6 | 0.0 | 15.7 | 0.805 |

## Paired Differences

Values are first variant minus second variant, paired by seed; the interval is a two-sided 95% t interval.

| Comparison | ACK-PDR delta | Destination-PDR delta | Airtime delta (s) | Fallback-forward delta |
| --- | ---: | ---: | ---: | ---: |
| calm-route-miss-fallback minus calm-no-route-miss-fallback | +0.009 +/- 0.018 | +0.023 +/- 0.023 | +15.9 +/- 9.1 | +62.4 +/- 27.3 |
| calm-route-miss-fallback minus meshcore-reference | +0.347 +/- 0.061 | +0.115 +/- 0.084 | -123.6 +/- 26.8 | +62.4 +/- 27.3 |

## Interpretation

- The CALM default versus no-route-miss-fallback line estimates how much route-miss recovery changes the end-to-end result under the same CALM route admission logic.
- The CALM versus MeshCore-like comparison remains a protocol-bundle comparison because MeshCore-like has no equivalent recovery controller in this harness.
- This audit does not remove the main matrix's fixed-pair and high-PRR/one-hop limitations.

## Reproduction

```sh
python3 tools/run_recovery_budget_audit.py
```
