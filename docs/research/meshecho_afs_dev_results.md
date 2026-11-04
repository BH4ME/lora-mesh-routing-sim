# MeshEcho-AFS frozen development result

Date: 2026-10-04. Decision: **stop the positive AFS component claim**. The
predeclared joint development gate in
`meshecho_ack_terminated_flood_design.md` failed. AFS remains a tested
relay-side component on the old fixed-F source scaffold, not the requested
full MeshEcho core rewrite or an ICC acceptance estimate.

## Provenance and split

The only development matrix used seeds 23001--23040, the frozen
`recurring_fading` case, 600-s application generation, the original 30-s
per-flow ACK deadline, and whole-network airtime for full TXs starting by
630 s. Each seed paired AFS, identical no-cancel shadow, and unchanged
fixed-F on the same scheduled traffic. There are 120 runs and 1,623
scheduled unicasts per arm. Seed 23000 was used only for mechanical smoke;
the no-cancel shadow matched unchanged fixed-F in flow records, source
actions, metrics, and normalized complete TX traces. The ten input hashes
were frozen in `task_plan.md` before seed 23000 and match the development
manifest. The six saved artifact SHA-256 values independently match the
manifest. The validator passed source, artifact, schedule, flow, deadline,
packet-ToA, physical-decode, cancellation, paired-evidence, and mechanical
parity checks, then stopped at the expected development-gate failure.
Separately, every one of the 120 development seed/arm runs was re-executed
from the frozen code and matched saved rows, flows, actions, full TX, and
ACK-decode evidence, normalizing only process-local handle numerals.

| Artifact | SHA-256 |
| --- | --- |
| runs CSV | `8cb60b3120e9f3bae6abd23930ad6c1138ce9ce4b09ecaf5497e499a4ec6ec77` |
| paired CSV | `2b8f15628e349be1f3c89c43853590c0f5ce710a33abfd84e46c375f566237e3` |
| flows JSONL | `e33027eaf911bb44a64692f3e29c9496098f996c82c48a9497948998b8f8f57e` |
| actions JSONL | `4a3920f85ed53255ba6e877c83116157cd4e929cfa25346964b9b6832db24c16` |
| TX JSONL | `12864cf14188b5a99244599cf1e42d0ed7620048a3ed549c71ae640b3adca79e` |
| ACK decodes JSONL | `74359ca4c2926893cc370e7c6d1f3e5cdcc3b9df7e5d1d55a956faa75d741af5` |

## Predeclared primary comparison

Effects are means of 40 seed-paired differences for AFS minus no-cancel,
with the runner's nominal two-sided 95% paired-t intervals. Source ACK and
destination delivery are counted by the original 30-s deadline; airtime
includes complete-network TX ToA, not just canceled relay DATA.

| Effect | Paired estimate and 95% interval | Prespecified requirement | Result |
| --- | ---: | ---: | --- |
| Source ACK-PDR difference | -0.00143 [-0.04257, +0.03971] | Lower bound > -0.02 | **Fail** |
| Destination-PDR difference | +0.00141 [-0.00410, +0.00692] | Lower bound > -0.01 | Pass |
| Relative TX airtime | -19.53% [-23.80%, -15.26%] | Upper bound < -5% | Pass |
| Strict actual cancellations | 9,728 across 40 seeds, zero invalid | >=100 across >=20 seeds | Pass |

AFS canceled 5,954 initial-F and 3,774 recovery-F pending forwards. It
lowered whole-network airtime in 38/40 seeds. ACK counts improved in 18
seeds, worsened in 17, and tied in five. The ACK noninferiority requirement
fails because the lower confidence bound permits a 4.26-percentage-point
loss, not because a reliable negative mean effect was established.

Pooled totals are descriptive and weight high-flow seeds differently from
the paired estimand: AFS 1,156/1,623 deadline ACKs, 1,613/1,623 destination
deliveries, and 2,002.494 s TX airtime; both no-cancel and unchanged fixed-F
had 1,147/1,623 ACKs, 1,611/1,623 deliveries, and 2,531.461 s airtime.
The pooled nine-ACK increase does **not** override the predeclared paired
noninferiority failure. One-seed smoke had 26 versus 29 source ACKs and
52.883 versus 61.390 s airtime; it was never a population estimate.

## Stop rule and interpretation

Do not tune AFS on seeds 23001--23040, rerun them as independent
confirmation, open the sealed 24001--24040 holdout, or promote the ICC
manuscript/PDF, VERSION, GitHub, or EDAS with a positive AFS claim. AFS
demonstrates a substantial simulated cost-reduction mechanism, but under
this predeclared reliability margin it has not established that source
confirmation is preserved. Closed-loop interference and changed future
traffic mean a cancellation can affect more than its own TX airtime; the
aggregate comparison cannot assign each ACK difference to one canceled
relay. The current LoRa radio model is not hardware-validated, and the
whole-protocol FLOOD duplicate set remains unbounded in this simulator.

The source-side F/R/D and recovery controller remains the old threshold
policy. A complete core rewrite still requires a new device-observable
decision mechanism, close prior-art comparison, matched simple controls,
fresh development/holdout splits, and separate validation. This failed
component test does not imply any ICC acceptance probability.
