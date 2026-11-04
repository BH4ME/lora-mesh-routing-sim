# MeshEcho-DRC: deadline-reserved source routing with ACK-terminated flooding

Date: 2026-10-04. Status: **rejected at passive exposure gate before
population experiments**. DRC was a candidate replacement for the current
MeshEcho-SR source policy, integrated with the locally implemented AFS relay
rule. Its incomplete test-first source tracer was removed after the exposure
screen; this document is retained as a falsified design record, not a live
protocol, measured improvement, firmware design, or ICC result.

## Pre-population no-go finding

With the frozen recurring-fading PHY, the proposed nominal bounds are
`B_F = 9.328272 s`, `B_F0 = 9.297552 s`, and `B_R = 1.149..1.637 s`
for the observed one- to four-hop confirmed routes. Even a six-hop path
has `B_R+B_F = 11.375824 s`; reservation changes an initial choice only
after more than 18.624 s of source queue delay within the 30-s deadline.
Among all 559 route-bearing initial actions in the existing fixed-F DHR
development traces (9001..9020), zero fell in the narrow reserve-caused
F-first window, and all 559 had positive reserve slack. The same traces
had 185 actual R-to-F starts, so recovery is exposed, but its proposed
route-dependent checkpoint spans only 0.488 s. A simple fixed 2.05-s early
guard makes the same historical ACK/no-ACK trigger classification; this is
a trace diagnostic, not a changed-policy counterfactual.

The predeclared mechanism gate below demands at least 20 reserve-caused
F-first decisions and an ACK gain over the reserve-blind control. Those
conditions have no observed target exposure in the available non-holdout
case, so DRC as specified is stopped before the 28000 smoke, 28001..28040
development, or 29001..29040 holdout. The unchanged ICC paper and VERSION
cannot cite this as a positive result. A future different source mechanism
requires a new design and disjoint seed cohort, not retuning this gate.

## Question and mechanism boundary

Can a source spend a short, ACK-confirmed route attempt only when the original
application deadline still reserves time for one useful-DATA FLOOD recovery,
while relays stop queued FLOOD forwarding after they physically decode a
matching terminal destination ACK? The proposed contribution is the joint
deadline/airtime behavior of this specific source and relay contract. It is
not the generic ideas of ARQ, flooding, route caching, ACKs, or rebroadcast
suppression.

This is a **source-policy rewrite**, not a new threshold on DHR's 15-s guard.
DRC removes SR's proactive `D` RREQ/RREP discovery, route-age trigger,
confidence score, and token/cooldown policy. A first useful-DATA FLOOD learns
a route only through a source-received ACK. On later flows the source chooses
an initial R, initial F, R-only, or deadline-infeasible action at the actual
source TX start using the original flow deadline and charged packet ToA. An
initial R may be followed by at most one same-flow F. AFS applies to both
initial and recovery F relays. The radio, collision model, F forwarding delay,
ordinary duplicate-F suppression, and reverse ACK path remain comparison
infrastructure.

## Device-local state and wire identity

At each source, retain at most eight LRU destination records. Each contains
the ACK-confirmed route and local expiration time, its monotone commit-flow
generation, a consecutive *in-deadline source-ACK* miss count for that route
generation, and the last-used time. The route is confirmed only by a valid
source-decoded ACK, never by destination-delivery metrics or RREQ/RREP.
Evicting a destination record also evicts its route. At most eight active
unicast flow records per source retain `{flow, endpoints, application enqueue
time, deadline, chosen initial action, initial path/generation, scheduled
guard, recovery state, first accepted ACK}`. If active capacity is full,
register the application flow but send no packet and count its failure; do
not create an untracked, unconfirmable transmission. Retire a record after
the first accepted ACK or its original deadline. The Python simulator's
unbounded action logs, `flow_data_actions`, and metrics are instrumentation,
not device-state entitlements.

At each relay, use AFS's at-most-eight live pending-F records keyed by the
relay and `FLOOD` flood key. A record holds endpoints, flow/request identity,
epoch marker, validated local path, receipt time, and the exact uncommitted
`PendingSend` handle. It expires 30 s after **local** FLOOD receipt or when
the handle is canceled, commits, or ceases to be the active pending handle.
Capacity overflow leaves ordinary F forwarding intact without AFS
enrollment. The inherited simulator `seen_floods` set is unbounded; this
contract alone does not establish bounded firmware memory.

No new deadline, generation, stop, or route-score field is transmitted.
The on-wire identity is the existing `{kind, source, destination, flow ID,
request ID, realized path, path index, TTL}` with `request_id == flow_id`
for each application DATA/FLOOD/ACK. In this simulator the request ID on
these packet kinds aliases the already charged flow ID; it is not an extra
four-byte field. `Packet.created_at` and `Packet.protocol` are simulator
metadata and cannot be used by a relay as received wire evidence. Initial R
DATA and initial F FLOOD have `repair_index=None` and no marker byte. The
single recovery F has `repair_index=2`; the destination echoes it on every
corresponding ACK, costing one byte per marked F and ACK transmission.
Only one F epoch can exist for a flow, so the current F duplicate key, which
does not include `repair_index`, cannot merge two F epochs of this policy.

Under `Packet.wire_size_bytes`, an ordinary payload frame costs base 10
bytes plus `2 + 2*len(path)` path bytes plus application payload bytes;
an ACK has the same base and path bytes without application payload. Each
marked recovery-F or its ACK adds one byte. A growing FLOOD path changes
ToA at each relay. Every actual DATA, FLOOD, ACK, and any retained legacy
control packet must use its complete charged length for ToA, collision
duration, TX energy, and full-network cost. No canceled request consumes TX
airtime; a committed or started TX cannot be retroactively discounted.

## Source decision at physical TX start

For a flow enqueued at `t0`, fix `D = t0 + 30 s`. Enqueueing registers the
flow but does not freeze its R/F choice. At an **actual, immediately
committable source TX start** `t`, read only that source's current confirmed
route, its local active-flow record, its own radio availability, the
configured PHY/max-hop/flood-delay constants, and `D`. Recheck after every
queue deferral; a route committed or expired while waiting can change the
choice. A flow gets one initial packet and at most one recovery packet.

Define `B_R(P)` for a route of `h` hops as `h` times the complete initial
R-DATA ToA plus `h` times its reverse ACK ToA, plus a fixed 1-s scheduling
margin. Define `B_F` with the *marked* recovery F/ACK sizes at the configured
maximum path length: `H * ToA(F_max) + (H-1) *
(flood_base_delay + flood_jitter + 0.35 s) + H * ToA(ACK_max) + 1 s`, where
`H = max_hops`. An initial unmarked F uses the corresponding unmarked bound
`B_F0`. Using longest-path ToA at every F hop is deliberately conservative
for serialization and configured relay delay. These are **nominal admission
bounds**, not worst-case guarantees: later relay queueing, interference,
loss, and ACK queueing are not bounded by them.

The initial action rule is fixed in this order:

1. With a current ACK-confirmed path `P`, choose R with one reserved F when
   `t + B_R(P) + B_F <= D`. Set the R checkpoint `G = t + B_R(P)`.
2. Otherwise choose an initial F when `t + B_F0 <= D`, whether the route is
   absent or the remaining time cannot fit the two-stage reservation.
3. Otherwise choose R-only if a confirmed path exists and
   `t + B_R(P) <= D`.
4. Otherwise record `deadline-infeasible` and emit no packet. The flow
   remains in the scheduled-flow denominator.

For R-with-reserve, a valid initial R ACK received by `G` completes the
flow without F. If still unACKed at `G`, request exactly one recovery F
with marker 2. At its **actual** source TX start `t_F`, recheck the active
record, absence of a prior accepted ACK, the initial-R generation, and
`t_F + B_F <= D`. Abort if any check fails. If an R ACK arrives after the
guard but before F commits, cancel the pending F; if it arrives after F
starts, that on-air F remains charged. No recovery starts after its
admission window. The source never asks whether the destination got R.

An initial F is one useful-DATA flood, not a preceding route query; it has
no same-flow rescue. R-only has no same-flow rescue. After a flow's original
deadline, no new source packet for that flow starts and its ACK cannot count
or update a route. Relays do not know `D` because it is not on the wire;
an already launched F may still create late relay TXs, which remain charged.

The current simulator does **not** expose an atomic pre-start packet-choice
callback. `on_transmit` is a notification after `begin_transmission` has
committed the handle, and `begin_transmission` can reserve a physical start
later than `sim.now` when the source is busy. `PendingSend.can_start_at`
can reject a chosen packet, but cannot by itself atomically replace that
packet with F or R using observations that arrive before a future start.
Implementation must add a verified pre-start/defer-and-retry decision point
that runs at `start == sim.now`, or equivalent source-only scheduling with a
same-time recheck before commitment. It must apply to every matched DRC arm
and preserve the shared queue and random-stream contract. The exact hook
and same-time event ordering are unresolved until packet-level tests prove
that an intervening ACK or route change is visible. Merely moving the
decision into existing `on_transmit` would violate this design.

## ACK, route, and cancellation semantics

At the destination, a valid routed DATA arrival produces the ordinary
reverse-path ACK; the first valid F reception for its F key produces an ACK
along its realized, loop-free DATA path. Ordinary F deduplication still
suppresses later F copies before another ACK. A repeated R destination
arrival may produce another R ACK under the inherited data-plane behavior;
DRC itself sends no R repeat. Destination delivery is counted once per
application flow even when R and recovery F both arrive.

The source accepts only the first physically decoded, in-deadline ACK for
an active matching flow. `now == D` is in-deadline: retirement at `D` must
run after same-time receive events or otherwise preserve this inclusive
ordering in every arm. Require control-only ACK, `request_id == flow_id`,
reversed endpoints, path length `2..max_hops+1`, a loop-free path beginning
at the source and ending at the destination, source path index zero, and an
actual radio sender equal to the encoded next node on that path. An
unmarked ACK is valid only for the chosen initial R on its exact sent path
or for the chosen initial F on the realized F path. Marker 2 is valid only
after this flow's recovery F actually started, on a valid realized F path.
An old R ACK can win after F started; it remains an R ACK and cannot be
attributed to the F epoch. Any duplicate, wrong marker, wrong flow/path,
unstarted-epoch, or late ACK is ignored for application confirmation and
route state. Existing `on_ack_packet` lacks `RxInfo`; checking the physical
ACK sender requires validation in `on_receive` or another explicitly added
receive path, not an invented argument to that callback.

An accepted initial-F or recovery-F ACK may install the ACK's **realized
DATA path** and a new local TTL, only if its flow generation is newer than
the destination's last committed flow and the active record still exists.
An accepted R ACK refreshes local success/miss evidence only for its exact
current route generation; it neither changes the route path nor resurrects
an expired/evicted route. On original-deadline expiry without any valid ACK,
increment that generation's miss streak once; two consecutive such flows
evict its route. Do not treat a guard miss alone as proof of DATA loss or
immediately evict a route. A newer route commit makes older ACKs ineligible
to overwrite or clear its state, although an older still-active flow may
receive its own first valid in-deadline application ACK.

AFS cancellation runs only when a relay **physically decodes** an ACK while
holding an identical, still-uncommitted pending F handle. Validate the
ACK's flow/request IDs, reversed endpoints, unique source-to-destination
path, indexed actual radio sender, and exact epoch marker (`None` for an
initial F, `2` for recovery F). The relay must be outside that ACK path.
Reconstruct the local F key from the ACK's `final_dst`, flow, and request
instead of using `ACK.flood_key`. If all checks pass, cancel just that
pending F handle and continue ordinary ACK handling. A recovery-F relay
cannot be canceled by a late unmarked R ACK: it is terminal evidence for
the *application* but not a certificate that the F epoch reached the
destination. Conversely, a marker-2 ACK cannot cancel an initial-F handle.
The current AFS code excludes on-path ACK receivers and committed handles,
including committed future-start requests; this contract keeps those
limits. No global delivery flag, topology/PRR oracle, future event, or
source state may enter a relay's predicate.

## Matched controls and validation before any cohort

All DRC arms use identical source/relay state caps, PHY, application trace,
route TTL, packet fields, actual-start scheduler, F delay, one-F-epoch cap,
ACK validation, and original deadline. Shadow AFS registration and decoding
must run even in no-cancel arms without adding random draws.

| Arm | Only deliberate difference from DRC + AFS |
| --- | --- |
| `drc-afs` | Full source rule and off-path terminal-ACK cancellation. |
| `drc-nocancel` | Same source decisions and AFS shadow records; final pending-handle cancellation disabled. Isolates the relay rule. |
| `drc-reserve-blind` | On a confirmed route, first send R whenever `B_R` fits; use the same `G` and try one F at `G` only if its actual start passes `B_F`. Otherwise use initial F if `B_F0` fits, or send nothing. Isolates the initial reserve admission decision. |
| `drc-all-f` | Send one initial F whenever `B_F0` fits, otherwise nothing, with the same AFS rule. This is the simple reliability/airtime control. |
| `drc-no-rescue` | Same initial reservation decision as `drc-afs`, but suppress its guard-triggered recovery F. Isolates same-flow rescue; retain identical initial bytes. |

The unchanged `meshecho-sr` and `meshecho-dhr-flood` may be shown as
historical/context arms, with their differing discovery and trigger
semantics labeled; they are not substitutes for the controls above.
Meshtastic/MeshCore-like arms remain simulator abstractions, not product
firmware parity claims.

Before population runs, test exact packet bytes/ToA, destination once-only
delivery, ACK marker echo and source validation, route-generation ordering,
deadline equality/queue boundaries, active-state overflow, and same-time
ACK-versus-TX ordering. Prove `drc-nocancel` is packet-trace equivalent to
`drc-afs` when no cancelable ACK is decoded. Test an off-path initial-F and
recovery-F cancellation, a wrong-epoch R ACK, a committed-future-start F,
and ordinary duplicate-F suppression. A deterministic test must place an
ACK or route change between an initial decision request and delayed actual
source start; the resulting action must use the later local state. A second
test must defer the recovery F until its bound no longer fits and verify no
recovery TX. These tests are prerequisites, not current pass claims.

## Prospective experiment and joint gates

Reserve seed `28000` for mechanics and artifact smoke only. Use fresh
development seeds `28001..28040` and an untouched, once-only holdout
`29001..29040`; a repository search on this date found no use of these
ranges in research designs, tools, or tests. They are disjoint from the
inspected 3001/5001/6001/7001/8001/9001/10001/14001/15001/16001/
17001/18001/22001 cohorts and the separately reserved 230xx/240xx AFS
component cohorts. Freeze this design, source, runner, tests, case config,
and source hashes before development; a material change requires a newly
named cohort. No holdout seed is available for tuning.

Primary case: the existing 50-node `recurring_fading` configuration,
600-s application generation, original 30-s per-flow deadline, and 630-s
drain. Each seed must have all five arms with identical topology/case and
scheduled application trace hashes. Count every complete packet ToA for
every network TX starting at or before 630 s, even if it ends afterward;
report complete TX bytes, control bytes, and modeled TX energy on the same
window. Report raw RX energy separately because its present simulator
accounting is not the same window. Outcome denominators are **all scheduled
unicasts**, including state-capacity and deadline-infeasible drops. Source
ACK PDR and destination PDR require arrival by each flow's original
deadline. Also report capped completion delay (30 s for a missed ACK),
successful-ACK p95 separately, collisions, route changes, first-F versus
recovery-F outcomes, actual R-then-F starts, reserve-caused F-first actions,
and AFS opportunities/cancellations by epoch. Include zero-event seeds.

For each comparator and seed, compute candidate-minus-control ACK-PDR and
destination-PDR differences, and relative whole-network TX-airtime change
`(candidate - control) / control`. Report means of seed-paired differences
with nominal two-sided 95% paired intervals, not ratios of pooled totals.
The following are predeclared **joint** internal gates; every row must pass
in both development and unchanged-hash holdout:

| Comparison | ACK-PDR lower bound | Destination-PDR lower bound | Relative airtime upper bound |
| --- | ---: | ---: | ---: |
| `drc-afs` minus `drc-all-f` | `> -0.02` | `> -0.01` | `< -0.05` |
| `drc-afs` minus `drc-reserve-blind` | `> 0` and point gain `>= 0.02` | `> -0.01` | `< +0.10` |
| `drc-afs` minus `drc-nocancel` | `> -0.02` | `> -0.01` | `< -0.05` |

The `drc-no-rescue` comparison is required in every artifact and reported
even if adverse; its role is attribution, not a post hoc escape from a
failed primary gate. The mechanism-exposure gate additionally requires at
least 20 actual R-to-F starts across ten development seeds, at least 20
reserve-caused first-F decisions across ten seeds, and at least 100 actual
AFS cancellations across 20 seeds, including both initial and recovery F.
Any cancellation with an invalid marker/path/handle must be zero. Sparse
exposure makes the joint claim inconclusive even if aggregate intervals
pass. These thresholds and nominal intervals are author-chosen research
criteria, not conference acceptance rules or multiplicity-adjusted tests.

Open the untouched holdout only if development passes without changing the
algorithm. A passing holdout warrants separate unconditioned random-pair,
static-fading, altered fade interval, load, and PHY checks; label their
estimands separately and report failure. A failed development or holdout
gate stops positive DRC claims. No old manuscript/PDF, version, release, or
submission change follows from this design or smoke tests.

## Novelty and remaining implementation risks

ExOR's opportunistic candidate coordination, DSR route salvage, AODV local
repair, implicit-ACK forwarding, and managed-flood duplicate suppression
precede this design. The local repository also already contains LPR
pending-relay cancellation, DHR same-flow recovery, and implemented AFS
off-path terminal-ACK cancellation. A targeted prior-art screen in the
adjacent research notes is not exhaustive. The defensible question is
whether this *joint deadline-reserved source policy plus epoch-safe
terminal-ACK FLOOD cancellation* has a measured advantage over its matched
simple controls in the stated LoRa simulator. Do not claim first invention
or superiority to real Meshtastic/MeshCore firmware or hardware.

The unresolved actual-start hook is a correctness dependency. Further risks
are nominal bounds missing relay queueing, F deduplication preventing a
second ACK after some destination receptions, R ACK loss being
indistinguishable from R DATA loss at the source, and a late R ACK being
unable to cancel recovery-F relay handles under the exact epoch rule.
Closed-loop interference changes later receptions and source route state;
an offline canceled-handle count is an exposure bound, not a per-flow
counterfactual saving. The candidate must survive the frozen end-to-end
gate before any method or novelty language enters the ICC manuscript.
