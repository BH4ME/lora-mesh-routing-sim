# Four-Protocol Comparison Rerun

## Reproduction

The comparison was rerun with:

```text
python3 tools/run_cpr_external_comparison.py \
  --case-profile exposure \
  --out-prefix results/meshecho_four_protocol_comparison_92300_92319_20261012_rerun
```

The exposure case has 20 nodes, a 3000 m square, four directed pair slots,
8 unicast flows/min, 240 s of traffic plus a 30 s drain, SF7, and 6 dB block
fading refreshed every 60 s. Seeds `92300..92319` were run for all four arms.

The four arms are `meshecho-cpr`, legacy `meshecho`, `meshtastic`, and
`meshcore`. The result files contain 80 run rows and 60 paired rows. Every
paired row reports `trace_match=True`, `topology_match=True`, and
`pair_pool_match=True`; the sum of `incomplete_rx_tx_count` is zero. The
rerun summary is byte-identical to the previous four-protocol summary, which
confirms deterministic reproduction.

## Holdout Means

| Protocol | ACK PDR | Destination PDR | TX airtime (s) | TX energy (J) | Started TX requests |
|---|---:|---:|---:|---:|---:|
| MeshEcho-CPR | 0.9829 | 0.9984 | 6.290 | 2.491 | 81.65 |
| Legacy MeshEcho | 0.9477 | 0.9616 | 10.231 | 4.052 | 156.50 |
| Meshtastic-like | 0.9405 | 0.9886 | 29.257 | 11.586 | 318.25 |
| MeshCore-like | 0.9328 | 0.9451 | 9.896 | 3.919 | 153.10 |

Relative to CPR, the gains are:

| Comparator | ACK PDR gain | Destination PDR gain | Airtime reduction | Energy reduction | Started-TX reduction |
|---|---:|---:|---:|---:|---:|
| Legacy MeshEcho | +3.515 percentage points | +3.677 percentage points | 38.518% | 38.518% | 47.827% |
| Meshtastic-like | +4.238 percentage points | +0.978 percentage points | 78.499% | 78.499% | 74.344% |
| MeshCore-like | +5.006 percentage points | +5.333 percentage points | 36.439% | 36.439% | 46.669% |

The paired 95% intervals for CPR minus comparator ACK PDR are `[0.0192,
0.0511]` versus legacy MeshEcho, `[0.0170, 0.0677]` versus Meshtastic-like,
and `[0.0220, 0.0781]` versus MeshCore-like. The corresponding destination
PDR intervals are `[0.0213, 0.0522]`, `[0.0033, 0.0162]`, and `[0.0207,
0.0859]`. Airtime differences are negative because lower is better for CPR;
all three paired intervals exclude zero.

## Protocol Differences

- **Legacy MeshEcho:** confidence-ranked cached route with RREQ/RREP discovery
  and fallback behavior. It spends more airtime than CPR on route discovery,
  repeated forwarding, and collision exposure.
- **Meshtastic-like:** managed delayed flooding with duplicate suppression.
  It obtains high destination reachability through redundancy, but commits many
  relay transmissions and therefore has the largest airtime and energy cost.
- **MeshCore-like:** cached source routing with a first-reply RREQ/RREP miss
  path in this runner. It avoids managed flood redundancy, but a cache miss
  adds discovery cost and the first reply is not necessarily the best route.
- **MeshEcho-CPR:** confirmed-route initial send, one physically started
  same-path repeat, at most one deadline-feasible recovery flood, and
  ACK-terminated cancellation of only matching uncommitted relays.

## Breakthrough Assessment

CPR is a substantial algorithmic integration for this simulator: it changes
the source/recovery state machine and ties deadline admission, physical TX
start, route-generation validation, and relay cancellation into one charged
policy. The observed trade-off is strong in this case: roughly 3.5--5.0
percentage points higher ACK PDR and 36--78% lower started-TX airtime than the
three comparator models.

This experiment does **not** establish a breakthrough or first-of-kind result.
The retry, flooding, ACK feedback, and cancellation primitives have prior art;
the named protocols here are behavior-level simulator models rather than
official firmware or hardware runs; and the evidence covers one exposure case
with 20 seeds. A defensible breakthrough claim would require additional frozen
loads/topologies, same-information ablations, prior-art separation, and
hardware or measured-channel validation. The appropriate current claim is
“promising cost-responsive recovery policy with strong same-condition
simulation evidence,” not universal superiority.

## Artifacts

- Bar chart: `results/meshecho_four_protocol_comparison_92300_92319_20261012_rerun.png`
- Runs: `results/meshecho_four_protocol_comparison_92300_92319_20261012_rerun.runs.csv`
- Paired checks: `results/meshecho_four_protocol_comparison_92300_92319_20261012_rerun.paired.csv`
- Summary: `results/meshecho_four_protocol_comparison_92300_92319_20261012_rerun.summary.csv`

The external comparison runner writes CSV evidence rather than the formal
CPR population manifest and full JSONL ledger bundle. These results should
therefore remain labeled as paired behavior-level evidence.
