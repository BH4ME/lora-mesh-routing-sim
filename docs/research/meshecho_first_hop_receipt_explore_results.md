# First-hop receipt passive screen: exploratory result

Date: 2026-10-05. Decision: **NO-GO** for a first-hop-receipt MeshEcho
successor on the prespecified `recurring_fading` workload. This is a passive
necessary-condition screen, not a protocol treatment experiment, a paper
result, or an estimate of acceptance probability.

## Frozen provenance

- Stock protocol: `meshecho-dhr-flood-ack-delay`, original 30-s application
  deadline, seeds 45001--45020. The frozen exposure, cost and stop rules are
  in `meshecho_first_hop_receipt_screen_design.md`.
- The separately audited v3 seed-45000 smoke manifest is
  `results/meshecho_first_hop_receipt_smoke_seed45000_v3_20261005.manifest.json`
  (SHA-256 `7290acd265a1cf9ded4850eac1fc13d6351fa93b1f694e79240f0b5385b73631`).
  The exploratory authorization binds that manifest and the eight source
  inputs (SHA-256
  `ded7b8cd5b1d6fe2f39879fe87330be2cfa0593335f03d57b8656a0981328b91`).
- The formal CLI completed and archived
  `results/meshecho_first_hop_receipt_explore_45001_45020_v2_20261005.manifest.json`
  (SHA-256 `7c12f8b00e08cba4c2f96a9c22d76aaf129e0ece93474260ab3c2d31e1142109`).
  The CLI strictly replayed the saved cohort before returning successfully.
  An independent read-only audit checked the sidecar, every artifact digest,
  archived permit, predecessor, frozen inputs, 20 seeds, per-seed stock
  parity and replay flags, source decisions, first-hop decodes, flows, full
  TXs and aggregate airtime. Its raw-row gate calculation matched the report.
- A preceding attempt under the old source hash completed one seed-45001
  stock simulation but failed in nested capture before archiving any result;
  45002--45020 were not started in that attempt. The deterministic retry
  used the same preregistered seeds after a nonreserved-fixture red/green
  provenance fix. Seed 45001 is not an untouched validation seed.

## Prespecified gates

| Necessary gate | Frozen requirement | Observed | Decision |
| --- | --- | --- | --- |
| First-hop failure exposure | At least 20 multihop initial-R/no-guard-ACK failures across eight seeds and at least 15% of multihop initial-R/no-guard-ACK flows | 57 of 90 (63.3%) across 19 seeds | Pass |
| Residual, feasible opportunity | At least 10 original-deadline source-unACKed failures with nominal early-F admission across five seeds, idle source and no active-capacity exclusion | 10 across seven seeds, all already delivered to the destination by deadline; none undelivered | Pass for source ACK only |
| Receipt lower-bound network cost | Mean per-seed receipt airtime at most 10% of whole-network physical TX airtime | 2.3604%; 442 decoded multihop first hops incur at least 22.743552 s nominal receipt ToA versus 982.212096 s network TX airtime | Pass |
| Optimistic all-flow ACK ceiling | Equal-seed mean `gate_2_count / scheduled_unicast_flows` at least 0.02 | 0.0128713 (pooled 10/783 = 0.0127714); destination-delivery ceiling 0 | **Fail** |

All four gates were required. The result is therefore **NO-GO**, even
though the first three pass. This is a ceiling under optimistic timing and
receipt assumptions, not an observed benefit. A physical receipt would also
experience loss, queueing, collisions and added energy. Early F had no
deadline admission exclusive to it over stock fixed F in these rows.

## Failure structure and implication

The cohort scheduled 783 unicasts: 778 arrived at the destination by the
original deadline, while 742 obtained a source ACK. Thus 36 flows were
delivered but source-unACKed and only five were undelivered. Among 612
initial-R flows, 499 were multihop and 113 direct. All 57 multihop
first-hop failures with no initial-R ACK by guard eventually reached the
destination under stock recovery; 47 became source-ACKed and ten remained
delivered but source-unACKed. There was no failed-first-hop,
deadline-undelivered flow for receipt-based forward rescue to recover. Four
additional multihop initial-R flows had a decoded first hop and no source
ACK by deadline; all four also reached their destinations by deadline.

Do not implement or present a receipt-conditioned early-F rule, or the
conditional first-hop-cache/suffix-rescue hypothesis, as the new ICC core on
this evidence. The latter changes the rescue origin but has no observed
forward-delivery target here and is close to local repair/packet salvage
prior art. Do not tune the receipt gate to these results, open holdout seeds,
update `VERSION`, or rewrite the manuscript's title, numerical abstract,
tables or claims. A new device-observable research question should focus on
the physical reverse-ACK bottleneck and compare any charged feedback or
repair with the strong fixed-2-s ACK control and matched simple ACK repeats.
