# MeshEcho-DBR: deadline-reserved backup-route recovery (draft)

Date: 2026-10-05. Status: **unfrozen algorithm hypothesis for mechanical
tests only**. No DBR result exists. Do not update the ICC paper, PDF, VERSION,
GitHub or EDAS from this document. The 42xxx cohort motivated this design but
cannot validate it; all thresholds below were selected after inspecting old
workloads and require fresh prospective development and untouched validation.

## Question and narrow contribution boundary

Can a source use one destination-observed, first-hop-diverse backup route from
a useful-DATA FLOOD ACK to avoid an expensive same-flow recovery FLOOD after a
later routed DATA has no source ACK, without losing deadline confirmation or
destination delivery? DBR is not a claim that route caches, multipath, delayed
ACKs, or retransmissions were invented here. DSR (RFC 4728) already caches
multiple routes and switches on failure; AOMDV (DOI 10.1002/wcm.432) uses
alternate disjoint routes. The testable distinction is the *joint* LoRa
packet-byte, 2-s feedback-window, path-generation and original-deadline
admission rule, measured against a DSR-like first-alternate control with the
same observed route and wire cost. If DBR behaves like that control or does
not beat it on the frozen gate, stop the new-core claim.

The old 42xxx passive data have 820 scheduled flows, 230 destination FLOOD
epochs, 748 valid decoded paths and 483 alternatives. A read-only join found
186/201 source-confirmed F commits with a distinct backup by 2 s, and
108/141 later R no-ACK guards with a same-generation backup. The fixed-F arm
already delivered 107/108 and source-ACKed 94/108 of those 108 flows;
84/108 backups were at least 60 s old by the guard. None of these traces
transmitted DATA on a backup path. They establish exposure only, not DBR
success. A lost F ACK cannot teach the source its backup, so DBR targets
*future* routed flows, not the flow whose first F ACK was lost. The current
paper's unconditioned random-pair workload has only five route-cache hits in
813 flows; DBR is not expected to help that stratum through reuse.

## Device-visible packet and state contract

- A FLOOD ACK may carry one optional full backup forward path from source to
  destination, encoded as one path-length byte plus 16-bit node IDs. A
  3-node backup therefore adds at least seven bytes to **every** ACK hop.
  `alternate_path` is a separate `Packet` field; do not reuse RREP's
  `learned_path`. Every copy/forwarding method preserves it. No new on-wire
  quality or generation field is implied; the existing flow ID, endpoints,
  request ID alias and charged one-byte recovery marker bind the ACK.
- A source stores at most eight destination records. Each has a primary
  ACK-confirmed route, one *observed but unconfirmed* backup path, the flow
  generation that supplied both, the source-accepted ACK time and route
  expiry. At most eight active application flows per source retain original
  enqueue deadline, actual initial R start, generation, sent paths, started
  recovery markers and timers. Simulator-wide flow maps remain analysis
  instrumentation, not a firmware-memory claim.
- A destination holds at most eight active `{source, flow_id, repair_epoch}`
  FLOOD windows, each keeping at most four loop-free, unique, successfully
  decoded complete paths. A valid path starts at the claimed source, ends
  at this destination after appending it, has 2..max_hops+1 unique nodes,
  has the actual radio sender as penultimate node, and has coherent on-wire
  origin, destination, request ID and epoch fields. The destination cannot
  consult the simulator's registered application flows or authenticate a
  claimed source from these fields; malicious injection is outside this
  candidate's threat model. Simulator accounting separately refuses to
  credit a mismatched registered flow as delivered. Never use true PRR,
  future events, another node's queue or simulator delivery flags as a
  policy input.

## Destination feedback

The first valid FLOOD decode delivers the application once and opens a
2.0-s local window. Additional valid duplicate decodes in the window add
candidates but do not redeliver, reflood or schedule another ACK. At the
window close, the destination builds **one** ACK for the first decoded path
and queues it through the ordinary radio. If a distinct path with a
different source-first-hop exists, encode the shortest such path (then
lexicographically smallest for ties) as `alternate_path`; otherwise omit it.
The ACK is built at window close, not prebuilt on the first arrival. Queue
delay beyond 2 s remains possible and charged. Capacity overflow falls back
to a single first-path 2-s ACK with no backup and is counted. Routed DATA
ACKs are immediate and carry no backup. Reverse relays forward the actual
ACK bytes and do not alter the backup field.

## Source controller and original deadline

The new source controller has no proactive D/RREQ/RREP action, 180-s age
trigger, two-miss selector or discovery token. At application enqueue, if a
current ACK-confirmed primary route exists, send initial R DATA on it;
otherwise send useful-DATA F. Every flow retains `D = enqueue_time + 30 s`.
An accepted F ACK commits its realized ACK path as primary and a validated,
first-hop-diverse optional path as unconfirmed backup, bound to that F flow
generation. Initial R ACK refreshes only the exact sent/current generation.
No older ACK may roll back a newer route. A backup is kept for at most
120 s after its source-accepted carrying F ACK, and never beyond the
primary route's existing TTL; 120 s is a prospective design constant, not a
claim about the simulator's fading block.

At `actual_initial_R_start + 15 s`, do nothing if that flow already has a
valid source ACK. Otherwise consider same-flow recovery using only source
state. If the backup is still attached to the sent route generation, is
first-hop-diverse and unexpired, the source is idle, and a conservative
charged `backup DATA + reverse ACK + 2-s backup guard + F + 2-s F ACK + 1-s
margin` nominal bound fits before D, request one marked backup DATA
(`repair_index=3`). Recheck generation, ACK status, radio start time and
deadline bound at actual TX start; a queued uncommitted request can be
canceled. If no backup is admissible, request one marked useful-DATA F
(`repair_index=2`) when its own bound fits. An F ACK still commits the
realized F path and may carry a newly observed backup.

If the marked backup DATA starts and no matching source ACK is accepted by
`actual_backup_start + 2 s`, request one marked F only if its conservative
bound still fits D at its actual source TX start. This gives at most one
backup probe and one F rescue on the same original flow. A matching backup
ACK accepted before D commits that *actually ACKed* path as primary; a
backup transmission alone never does. If a late initial R ACK arrives, it
may acknowledge the flow but cannot overwrite a newer backup/F commit. The
first accepted ACK completes a flow; later ACK copies do not change its route
commit. Thus an R ACK accepted first also prevents a later backup/F ACK from
switching the route for that completed flow.
DATA duplicates count once as destination application delivery, while each
valid distinct transmission may elicit its own matching ACK. Missing ACK
never proves forward DATA loss.

If the source becomes busy between a recovery decision and physical TX start,
the unstarted request is canceled and logged. Only a new decision timer is
placed at the earliest observed radio-idle time, and a marked F is requested
there only if the flow is still unACKed, its active flow record remains
current, and the original deadline bound still fits. Unlike a cached backup
DATA probe, useful-DATA F may remain valid after another flow commits a new
route generation. The same timer-only recheck
applies when the source is already busy at the R guard or when an F request
is delayed by radio queueing. No future physical TX slot is reserved.
FLOOD admission charges a maximum-length optional backup path in its
worst-case reverse ACK; routed DATA ACKs carry no backup field.

The bound is an **admission estimate**, not a guarantee under unbounded
queueing, stochastic loss or interference. Every failed admission remains in
the all-scheduled-flow denominator with a logged reason. Original DHR and
fixed-2-s variants remain untouched comparators, not the new policy.

## Required controls and prospective evidence

All new controls share the same no-D initial F/R rule, 2-s destination
collection, on-wire ACK path bytes, actual-start guards, deadlines and
application traces. Modes differ only in the recovery decision:

1. DBR: fresh first-hop-diverse backup probe, then F when admissible.
2. Same-path: same two-stage trigger/guard/F reserve, but probe the original
   route; receive an equal-size backup field and ignore its routing content.
3. First-alternate: DSR-like first available backup probe then F under the
   same nominal deadline bound, without DBR's 120-s freshness gate.
4. Fixed-F: one F at the original R guard, no probe. Run both a naturally
   short ACK and a byte-padded/observed-backup ACK version to isolate cost.
5. Context: old MeshEcho-SR/DHR, stylized Meshtastic-like/MeshCore-like and
   the paper's PRR-product control, with explicit different-policy caveats.

Before *any* population run, finish public-packet tests for byte/ToA/energy,
duplicate candidate collection and one ACK, capacity, source generation,
late ACK, physically started recovery, guard ties, queueing and deadline.
Freeze source/contract/runner/case hashes; use one mechanical smoke on a
fresh seed. Candidate reserved but **not authorized** IDs are 44200 smoke,
44001--44020 development and 44101--44140 untouched holdout. Verify no
saved artifact or prior in-memory use before authorization. Do not retune
the same development cohort after a failure and call it new evidence.

Primary estimands are per-seed paired differences in all-scheduled-flow
source ACK PDR by D, destination PDR by D, and whole-network physical TX
airtime through the fixed drain window, with nominal 95% paired intervals.
For seed s and arm a, use the same scheduled unicast count N_s in every arm:
ACK PDR is on-time source ACKs divided by N_s; destination PDR is on-time
DATA deliveries divided by N_s. Airtime is the sum of complete physical TX
durations for packets starting no later than `duration_s + 30 s`, including
any transmission that finishes after that cutoff. Compare airtime per seed
as `(DBR_s - control_s) / control_s`, not a pooled packet-level ratio.
Compute modeled TX energy from the same TX window and configured voltage/
current; raw always-listening RX accounting is secondary because it can
include post-cutoff radio activity. The independent unit for uncertainty is
the topology/application seed, not its individual flows. A two-sided
seed-paired t interval is descriptive; all joint gates below must be
prespecified and reported with adverse comparisons retained.
Provisional joint development/holdout gate (must be finalized before the
smoke) is: against byte-padded fixed-F, ACK-PDR lower bound > -0.02,
destination-PDR lower bound > -0.01 and relative airtime upper bound < 0;
against same-path, ACK-PDR lower bound > 0 with airtime upper bound < +0.10;
against first-alternate, relative-airtime upper bound < 0 with ACK-PDR
lower bound > -0.01. Require at least 20 physical backup starts in ten
seeds and at least 20 DBR-versus-first-alternate branch differences before
claiming a selective decision benefit. These are internal research gates,
not ICC rules or an acceptance-probability estimate.

Report complete TX bytes/ToA and modeled energy, source ACK and destination
delivery separately, collision/half-duplex losses, capped completion delay,
recovery starts/admissions, duplicate deliveries, ACK backup-field exposure,
backup age and route length. Count per-flow guard reasons, canceled
unstarted B/F requests and feedback-window capacity fallback separately from
physical starts. After a passed untouched recurring-pair holdout,
run unconditioned random-pair, load, fading-interval, link-asymmetry and PHY
sensitivity. State the expected random-pair reuse limitation and that these
are packet-level simulations, not firmware or hardware measurements. A
positive ICC method/results rewrite is permitted only after this evidence
chain passes independent artifact and citation review.
