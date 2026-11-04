# Fixed-delay FLOOD ACK exploratory result

Date: 2026-10-04. Decision: retain the 2-s delay as a strong **simple
control**, not a new MeshEcho core or an ICC manuscript result. The delay was
chosen after inspection of earlier 37xxx traces, so this 20-seed comparison
is exploratory and cannot be relabeled an untouched confirmation.

## Frozen comparison and audit

The preregistered `recurring_fading` comparison used seeds 38001--38020,
600-s application generation, a 30-s source deadline, 630-s primary TX-start
cutoff, and a symmetric bounded 660-s sensitivity. Both arms use the same
fixed-F DHR source/recovery rules; only the first valid destination FLOOD
ACK is deferred by 2.0 s in the delayed arm. Every seed has both arms on
the same case and application trace (781 paired unicasts total).

The nine input hashes match the pre-smoke freeze in `task_plan.md` and the
manifest; all eight saved artifact hashes match. Independent validation of
`validate_manifest(..., "explore", input_hashes(), strict_replay=True)`
passed for all 40 runs, including exact immediate-arm stock fixed-F parity
and saved metrics, actions, flow records, and complete TX traces. The 251
delayed-arm first-FLOOD ACKs with observed starts began 2.0 s after their
destination decode; 380 immediate-arm counterparts began at decode. Neither
arm has an observed TX start after 630 s. The 660-s window remains explicitly
bounded, not proof of all eventual cost.

Manifest: `results/meshecho_delayed_ack_control_explore_38001_38020_20261004.manifest.json`.

## Paired exploratory outcomes

Effects below are delayed minus immediate, averaged over 20 matched seeds;
intervals are nominal two-sided 95% paired-t intervals. The airtime effect
is the mean per-seed relative difference, not the ratio of pooled totals.

| Measure | Paired effect [95% CI] |
| --- | ---: |
| Deadline source-ACK PDR | +0.2251 [+0.1725, +0.2777] |
| Deadline destination PDR | +0.0024 [-0.0040, +0.0087] |
| Complete-network TX airtime | -16.73% [-22.24%, -11.22%] |
| Capped ACK-completion delay | -4.89 s [-6.35, -3.43] |

Pooled descriptive counts: source ACKs 726/781 delayed versus 548/781
immediate; destination deliveries 770/781 versus 768/781; whole-network
airtime 1006.568448 versus 1233.093120 s. Source-ACK PDR improved in
20/20 seeds and airtime fell in 19/20. On paired flows, 204 became ACKed
and 26 lost ACK status, for net +178. Destination status changed +8/-6.
Network TX counts were 12,548 versus 14,610, and source FLOOD recoveries
164 versus 194. These changes reflect closed-loop protocol trajectories,
not a per-packet causal attribution to one avoided collision. First-FLOOD
receipts differed (251 versus 380), so the immediate arm's old reception
trace cannot be used to infer the delayed arm's counterfactual ACK path.

## Interpretation and next gate

The result makes immediate reverse-ACK timing a high-value research target
in this simulator and workload. It does **not** establish novelty, hardware
validity, a general optimum at 2 s, or an ICC acceptance probability. A
fixed ACK wait is an established/simple timing control, and neither the
source's F/R/D policy nor its recovery state machine was rewritten here.

Before promoting a successor, define a distinct device-observable ACK and
source/recovery contract, verify its boundary against prior ACK-waiting and
LoRa flooding work, and compare it prospectively against this fixed-2-s
control plus same-budget repeats across fresh development and untouched
holdout splits. Include random-pair/load/PHY stress and, for a strong
systems claim, a calibrated radio or small physical validation. Keep the
current ICC manuscript/PDF, VERSION, GitHub, and EDAS unchanged meanwhile.
