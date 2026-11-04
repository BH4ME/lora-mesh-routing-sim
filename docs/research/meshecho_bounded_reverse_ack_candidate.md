# Candidate ACK branch: bounded reverse-path diversity after observed floods

Date: 2026-10-04. Status: **revised pre-implementation ACK-branch prototype
contract; not a complete core rewrite**. No ICC
result, novelty, or acceptance claim follows from it. Source DHR fixed-F
is a comparison scaffold, not a validated new source policy.

## Evidence and question

The fixed-F DHR control already sends one F rescue after an admitted
unACKed R transmission. On new exploratory seeds 14001--14003, all 35
delivered-unACKed flows emitted destination ACKs and their 37 ACK attempts
physically failed on a reverse hop. Independent seeds 15001--15003 show
that 27/32 FLOOD-first delivered-unACKed flows physically decoded a second
inbound FLOOD path with a different first reverse ACK hop within 1 s.
These cohorts are not per-flow paired counterfactuals. The latter screen
does not show that any untransmitted alternate ACK would work.

Question: can a destination use an *actually decoded* duplicate FLOOD
path to add one bounded ACK on a different reverse first hop, improving
source-ACK delivery by the original deadline at acceptable whole-network
airtime, beyond simply repeating an ACK on the original path?

## Proposed device-local behavior

1. Keep every baseline destination ACK immediate, whether it follows the
   first routed DATA or the first FLOOD of that flow. This preserves the
   existing opportunity and avoids a blind collection delay.
2. Track at most eight recent *first physically decoded FLOOD receipts*
   per destination, each for 1 s from that local receipt. An earlier R
   DATA delivery does **not** disqualify the later FLOOD recovery epoch:
   the destination need only remember what FLOOD packets it decoded, not
   a simulator-global first-delivery truth. When full, keep the immediate
   ACK but decline extra-ACK tracking for the new FLOOD epoch; expired
   records are removed on receipt and by a local timer. Store the first
   FLOOD path, its repair marker, first local receipt time, and whether
   an extra ACK has been scheduled. This bounds only the **new ACK-window
   state**; the inherited `seen_floods` deduplication set is unbounded,
   so this prototype makes no whole-protocol MCU-memory claim.
3. For a subsequent physically decoded FLOOD of the **same flow** at that
   destination, consider one alternate ACK only when the complete received
   path is loop-free, within the hop limit, carries coherent on-wire
   flow ID/endpoints and the same repair marker as the first FLOOD. The
   packet's claimed last hop must equal the actual `rx.sender`, and the
   destination must not already appear in its path. Its predecessor at
   the destination must differ from the predecessor of the **first FLOOD
   ACK in this local epoch**. An earlier routed-DATA ACK for an R-first
   flow is not that reference ACK. Choose the first eligible decoded
   alternate in receive order; do not use global PRR or future packets. The model's
   `request_id` on FLOOD/ACK is not an independently charged wire field;
   for this branch it is only the existing alias of the transmitted flow
   ID, never an additional device input.
4. At most one extra ACK may start per flow. It must be triggered by a
   duplicate received no later than 1 s after the first destination FLOOD
   receipt for that flow;
   a pending extra ACK that cannot start by that local window is canceled.
   The destination uses this *local* elapsed-time window only. It cannot
   enforce the source's original `created_at + 30 s` deadline because the
   simulator's `Packet.created_at` is **not on wire**. The source retains
   its original deadline acceptance rule; any late or wasted second ACK
   must be counted. A future destination deadline gate would require an
   explicit, charged on-wire budget field and a clock/age update contract.
5. The extra ACK copies the received FLOOD path and marker exactly;
   existing source-side ACK validation, route commitment, first-valid-ACK
   semantics, and one-delivery-per-flow semantics remain enforced. The
   second ACK needs no new on-wire marker; analysis logs distinguish it.
   Never read source delivery/ACK metrics, true PRR, global event history,
   or simulator-only timestamps for this decision.
6. Inspect the newly decoded duplicate at the destination *before* the
   inherited flood-deduplication early return, but still execute the
   inherited handler exactly once so baseline delivery, duplicate counts,
   and suppression remain unchanged. Use `PendingSend.can_start_at` or an
   equivalent actual-TX-start predicate for the local 1-s limit, because
   radio queueing may push a scheduled ACK beyond the window.

This is a *candidate* ACK-side rule. Its source-side F/R/D policy and
interaction with first-hop R loss need a separate, complete core contract.
The frozen DHR threshold failed; it must not be silently reused as the
novel source decision.

## Mandatory causal controls and measurements

- `fixed-F`: unchanged same-trigger DHR F-rescue protocol.
- `same-path-extra-ACK`: on the *same observed alternate FLOOD and timing
  predicate*, send one extra ACK on the path of this FLOOD epoch's first
  ACK, even if an earlier routed-DATA ACK exists for the flow. Match the
  state cap, one-extra limit, and actual TX-start window. This separates
  spatial diversity from the value of a second ACK attempt.
- `alternate-path-extra-ACK`: the candidate above. Both extra-ACK arms
  use the same local-window gate and full packet accounting; actual packet
  length/path airtime may differ and must be reported.
- The control and candidate share a rule, not necessarily identical
  per-flow receptions. Added ACK traffic changes half-duplex collisions,
  later routing state, and the path set each arm observes. Paired whole-run
  effects are closed-loop policy comparisons, not packet-level
  counterfactuals on the same traffic history.
- Retain simple R-repeat/no-recovery controls for the complete core study.
  Compare with old SR and protocol-inspired Meshtastic/MeshCore in the
  manuscript, with honest workload and candidate-set caveats.

Primary metrics are all-scheduled-unicast source-ACK PDR by original
30-s deadline and complete-network TX airtime/energy. Also report
  destination PDR, ACK attempts and physical failure hops, capped per-flow
delay, collisions, full TX bytes, admission coverage, duplicate FLOOD
receipts, and route commits. Stratify extra-ACK exposure and outcomes by
whether the flow's first DATA delivery was R or F, using offline analysis
only (not protocol decisions). Use per-seed paired effects and confidence
intervals; do not select a favorable seed subset or infer an alternate
path's effect from read-only traces.

The fixed development case is `recurring_fading` from `run_sr_experiment.py`:
50 nodes, 8250-m square, connected multi-hop repeated pairs, 4 flows/min,
600-s application generation, 30-s per-flow ACK deadline, and TX starts
observed through 630 s. Reserve mechanical seed 16000, development seeds
16001--16020, and untouched holdout 17001--17040. Use identical
application trace and static configuration per seed across the three arms.
Freeze simulator, runner, design, and test source hashes before the matrix;
any behavior-affecting change requires a new named cohort.

The **prospective ACK-branch development gate**, chosen by the authors,
requires all of the following using seed-paired nominal two-sided 95%
confidence intervals on per-seed ratios/costs:

- Alternate versus fixed-F: ACK-PDR point gain at least +0.02, interval
  lower bound above zero, and relative complete-network airtime interval
  upper bound below +8%.
- Alternate versus same-path-extra-ACK: ACK-PDR interval lower bound above
  zero and relative complete-network airtime interval upper bound below +5%.
- Destination-PDR difference versus fixed-F: interval lower bound above
  -0.02. At least 20 extra alternate ACK transmissions in at least ten
  development seeds, so the mechanism has visible exposure.

These are internal go/no-go criteria, not an ICC requirement or publication
probability. Report every arm and adverse metric. If development fails,
stop this ACK-branch claim, do not open the holdout, and do not promote the
old ICC paper/PDF/version. If it passes, open the unchanged holdout once,
using the same three arms, case, packet rules, source hashes, and paired
thresholds above. The 40-seed holdout also requires at least 40 actual
alternate extra-ACK transmissions spanning at least 20 seeds. A failed
holdout blocks a positive manuscript claim even if development passed.
Only after holdout replication should the evaluation test unconditioned
random pairs, fading interval, load, and PHY sensitivity before revising
the manuscript. Passing this branch alone does not complete the promised
source-side core rewrite.

This pre-implementation revision resolves an observability conflict in the
first draft: excluding R-first flows would require a separate bounded
destination route-first tombstone or a forbidden read of simulator delivery
metrics. The revised mechanism uses the first FLOOD receipt as its own
local epoch, admits R-first flows only after their actual F recovery, and
keeps R-first/F-first as evaluation strata. No population seeds were run
between the draft and this revision.

## Prior-art boundary

Multipath forwarding and ACKs are established. Lee et al. (2020), DOI
`10.1155/2020/8839541`, explicitly uses multi-route DATA/ACK propagation
and ACK-copy-path-aware waiting in underwater sensor networks. Joy and
Branch (ITNAC 2024), DOI `10.1109/ITNAC62915.2024.10815298`, study LoRa
flooding duplicates. AODV reverse replies and DSR passive/explicit ACKs
also predate this work. The possible contribution is only the precise
receiver-observed, bounded alternate-first-hop ACK decision under LoRa
airtime/half-duplex constraints, with source-side deadline accounting, *if*
a matched evaluation shows
an advantage. This limited search does not establish originality.
