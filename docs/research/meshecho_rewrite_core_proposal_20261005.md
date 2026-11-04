# MeshEcho-SR core rewrite proposal: DRC minimum contract

Date: 2026-10-05  
Status: **design and audit only; unfrozen; no new seed has been run**

This note is the independent audit requested before changing the MeshEcho-SR
algorithm. It is not a paper result, a novelty claim, a firmware validation,
or an authorization to update the ICC manuscript, VERSION, GitHub, or EDAS.
The existing simulator, PHY, accounting, application traces, and historical
protocols remain in place. This note defines the smallest successor that is
actually different from the inherited F/R/D controller and that can be
implemented and falsified without using a simulator oracle.

## 1. Audit verdict

The current implementations are components, not one verified new core:

| Component | What the code actually does | Why it is not yet the rewrite |
| --- | --- | --- |
| `MeshEchoSR` | At `send_app`, chooses `D` after a 180-s route-age/recent-demand trigger or repeated cold misses; chooses `F` without a route or after two R misses; otherwise chooses `R`. It spends a source token and starts RREQ/RREP for `D`. | The decision is made at application enqueue, not at physical TX start. It depends on route age, two-miss histories, a token/cooldown, and inherited discovery state. The source ACK guard is a fixed `ack_guard_s` timer. See `lora_mesh_sim.py:2533-2615` and `lora_mesh_sim.py:2740-2784`. |
| `MeshEchoDHR` | Inherits SR's source selector. After an unACKed routed DATA, a fixed guard admits at most one marked R or F recovery if a nominal bound fits; the adaptive choice uses `last_ack_at`, a 120-s freshness rule, and R-miss count. | This is a same-flow recovery component on the old source policy, not a replacement for the source action rule. The recovery admission is evaluated after the old action already happened. See `lora_mesh_sim.py:2851-3144`. |
| `MeshEchoDCB` | Adds a two-second destination FLOOD feedback window, an optional nominated two-hop relay, and a marked relay DATA backup (`repair_index=4`, `backup_relay_id`, `backup_epoch_id`). | `source_mode="sr"` still inherits DHR/SR. DCB changes destination/relay behavior but does not replace source control. Its feedback windows and relay pending records are bounded locally, while the inherited `seen_floods` history is not. See `lora_mesh_sim.py:3173-3678`. |
| `MeshEchoDCBPromote` | Promotes a successfully ACKed nominated backup path into the route cache. | A backup ACK proves that the backup path worked once; it does not prove that the direct DATA failed. Promotion therefore changes route state on ambiguous evidence and still inherits old source decisions. |
| `MeshEchoDCBTrial` | Uses a pending ACK-proven two-hop path for one next-flow R trial, or immediately switches in the blind arm; no route gives F, an R miss gives F, otherwise R. | This is a candidate source selector, but the public trial/blind screen had no paired action/path/ACK/delivery/airtime difference in the tested workload. It has no deadline admission and still uses inherited DHR timers/state. See `lora_mesh_sim.py:3745-3943`. |
| `MeshEchoAFS` | Cancels an uncommitted queued FLOOD relay after a valid off-path ACK decode. | It is relay-side behavior on the old DHR source scaffold. Its frozen development result saved airtime but failed the predeclared source-ACK noninferiority bound; it cannot be promoted as the new core. |

The seven-arm 493xx archive is useful mechanism evidence, not a successor
result: the old DCB arm had 376/399 source ACKs and 500.36 s complete-network
airtime, while the source-FR replacement had 373/399 and 395.95 s. The
descriptive airtime saving did not establish ACK noninferiority. Trial and
blind were identical on the saved first-action/path/endpoint outcomes. These
observations reject parameter tuning as the next step; they require a new
state machine and matched controls.

## 2. Proposed successor: MeshEcho-DRC

`DRC` means **deadline-reserved source controller**. It is a new class and a
new protocol identity, not another mode of `MeshEchoSR`, `MeshEchoDHR`, or
`MeshEchoDCB`. The implementation may reuse tested radio, route forwarding,
FLOOD duplicate handling, ACK transport, and metrics helpers, but it must not
inherit the SR/DHR `send_app`, miss sets, discovery timers, or DCB nomination
state and then selectively clear them.

### Research question and boundary

Can a source that has an ACK-confirmed route reserve enough of the original
application deadline for one useful-data FLOOD recovery, while using a
deadline-feasible useful FLOOD when a routed attempt cannot leave that
reserve? The core contribution, if it survives matched evidence, is the
joint source admission/recovery rule under charged packet airtime and the
original deadline. It is **not** a claim to invent source routing, ARQ,
FLOOD forwarding, route caching, or duplicate suppression.

The source removes all of the following from its primary decision:

- proactive `D`/RREQ/RREP route discovery;
- the 180-s route-age trigger;
- the source-wide discovery token and 300-s cooldown;
- the two-consecutive-R-miss selector and the 120-s adaptive rescue split;
- any model-inferred PRR, topology, destination-delivery flag, or future event.

An ACK-confirmed route remains useful state, but route age only expires the
record. It does not trigger an action. A useful-data FLOOD ACK can learn or
refresh a realized route; a missing ACK is treated as missing confirmation,
not as proof that the destination did not receive DATA.

## 3. Device-observable state and finite bounds

All limits below are protocol limits, not merely limits on diagnostic logs.
The simulator can retain richer traces for auditing, but a policy decision
must be reproducible from the bounded state listed here.

### 3.1 Source destination record (maximum eight per source)

For each `(source, destination)`, retain:

```text
phase: NO_ROUTE | READY | QUARANTINED
route_path, route_expires_at, route_generation
last_accepted_ack_time
in_deadline_miss_streak: saturating 0..2
last_used_lru_counter
```

`READY` means the route came from a valid source-decoded ACK. `QUARANTINED`
means the route is not used for an unreserved R attempt after a failed
deadline flow; the next eligible application uses useful F. Two consecutive
in-deadline no-ACK flows evict the path and return to `NO_ROUTE`. A single
guard miss never proves forward loss and never silently overwrites a newer
route generation. Eviction removes all record-local evidence and any
uncommitted request for that pair.

### 3.2 Source active-flow record (maximum eight per source)

Each tracked flow retains:

```text
flow_id, source, destination, enqueue_time, deadline = enqueue_time + L
initial_action: R | F | NONE
initial_path and route_generation (if R)
initial_physical_start (once started)
guard_time and guard_handle (for reserved R)
recovery_state: NOT_DUE | PENDING | STARTED | CANCELED | DONE
first_valid_ack_epoch/path (if accepted)
```

When capacity is full, the application flow remains in the all-scheduled
denominator but emits no untracked packet and records `state-capacity-drop`.
This is an explicit finite-device behavior, not an omission from the metric.

### 3.3 Relay and duplicate state

The primary DRC core has no DCB backup nomination and no AFS pending relay.
Relays use ordinary path-carrying FLOOD forwarding and duplicate suppression.
For a deployable finite-memory contract, every matched DRC arm must replace
the current unbounded `seen_floods` sets with the same per-node bounded LRU:

```text
at most 128 {kind, origin, flow_id, request_id, repair_index} keys
30-s expiry from local decode; deterministic LRU eviction
```

An eviction may permit a later duplicate forward and is counted. It must not
be hidden by using an unbounded simulator set in the candidate while claiming
an MCU bound. The exact 128/30-s values are design constants to freeze before
development; changing them after seeing outcomes creates a new contract.

### 3.4 Destination state

The core destination sends the inherited immediate ACK behavior. It needs
only the same bounded duplicate table; the device does not keep a second
unbounded application-flow map. If an implementation needs an explicit
delivery/ACK epoch record in addition to the duplicate table, cap it at eight
active records per destination and apply `destination-state-capacity` on
overflow. There is no DCB two-second candidate window in the minimum core.
DCB/AFS extensions must be separate factorial arms with their own state caps
and byte costs.

## 4. Observations and actions

At the **actual, immediately committable source TX start** `t`, DRC may read
only:

- the source's current bounded destination record;
- the active-flow record for this application;
- local radio availability and the actual complete packet ToA;
- configured `max_hops`, FLOOD delay constants, and `deadline = enqueue + L`;
- whether an accepted ACK arrived before the same-time decision event.

It may not read a global graph, true PRR, destination delivery, another node's
queue, future events, aggregate airtime, or simulator-only metadata at a
relay. `Packet.created_at` and `Packet.protocol` remain instrumentation, not
wire evidence available to a receiver.

The source actions are:

```text
SEND_R(path, reserved_recovery)
SEND_F(initial)
SEND_F(recovery)
ARM_R_GUARD
QUARANTINE / EVICT
DROP_DEADLINE_INFEASIBLE
```

No source action is chosen once at enqueue and then assumed to start later.
The source registers the flow at enqueue, but evaluates this action table
again when a packet can really begin. A queued request that loses its route or
deadline before commitment is canceled and re-evaluated, not charged as the
old decision.

## 5. Source finite-state machine

Let `L` be the fixed application deadline (the current case uses 30 s), `D`
be `enqueue_time + L`, and `H` be the configured maximum FLOOD hop count.
For a confirmed route `P` with `h` hops, define conservative local admission
bounds using the actual charged packet sizes:

```text
B_R(P) = h * (ToA(unmarked R DATA on P) + ToA(unmarked ACK on P)) + M
B_F0   = H * ToA(initial F at maximum path size)
          + (H - 1) * (flood_base + flood_jitter + 0.35 s)
          + H * ToA(initial ACK at maximum path size) + M
```

`M` is a frozen local safety margin. These are admission estimates, not
guarantees under random loss, collision, or unbounded radio queueing. A
packet may start no later than `D`; a packet that starts before the cost
cutoff but ends after it is still fully charged in network cost.

At a real source start `t`, evaluate in this order:

1. If the record is `READY`, `P` is unexpired, and
   `t + B_R(P) + B_F0 <= D`, send one unmarked R DATA on `P` and set
   `G = t + B_R(P)`. This is `R_RESERVED`.
2. Otherwise, if `t + B_F0 <= D`, send one initial useful F. It has no
   same-flow second payload in the minimum core.
3. Otherwise, if a `READY` path exists and `t + B_R(P) <= D`, send one R DATA
   with no recovery reservation (`R_ONLY`).
4. Otherwise emit no packet and record `deadline-infeasible`.

For `R_RESERVED`, an accepted valid R ACK at or before `G` completes the
flow and keeps the route `READY`. If the source has no accepted ACK at `G`,
it moves the route to `QUARANTINED` and requests exactly one recovery F only
if, at its actual physical start `t_F`, all of the following hold:

```text
flow is still active and unACKed
the original R generation is still current
recovery has not started before
t_F + B_F0 <= D
```

An ACK arriving before the recovery request commits cancels that unstarted
request. An ACK arriving after recovery has physically started cannot erase
its airtime. A valid ACK for the marked recovery F completes the flow and
commits its realized path as the new `READY` route. If no ACK is accepted by
`D`, the flow retires and the route miss streak saturates at two. At `D`,
same-time physical receive events must be processed before retirement so the
contract treats `now == D` as in deadline consistently in every arm.

The source never asks the destination whether the first R DATA arrived. It
only accepts an ACK that proves a valid, physically received confirmation for
the corresponding epoch.

## 6. Packet and ACK contract

The minimum core deliberately adds no new field. Existing fields are used as
follows:

| Packet | Core identity |
| --- | --- |
| Initial R DATA | `kind=DATA`, source route in `path`, `repair_index=None`, `request_id=flow_id` |
| Initial useful F | `kind=FLOOD`, growing realized `path`, `repair_index=None`, `request_id=flow_id` |
| Recovery F | `kind=FLOOD`, growing realized `path`, `repair_index=2`, `request_id=flow_id` |
| ACK | reverse realized path, echoes `flow_id/request_id` and `repair_index`; no `backup_relay_id` or `backup_epoch_id` |

The existing one-byte `repair_index` is therefore charged for recovery F and
its ACK. Every DATA, FLOOD, ACK, and relay forward uses its complete
`Packet.wire_size_bytes` for ToA, collisions, TX energy, and full-network
airtime. No canceled uncommitted request contributes a phantom TX.

At a source, an ACK is accepted only if all of these checks pass:

- physically decoded by the source before or at `D`;
- control-only ACK with `request_id == flow_id`, reversed endpoints, path
  length `2..H+1`, loop-free path beginning at source and ending at
  destination, and `path_index == 0`;
- actual radio sender equals the encoded next path node (`path[1]`);
- unmarked ACK matches the exact initial R path, or a realized initial-F path;
- marker `2` is accepted only after this flow's recovery F physically began;
- the flow and route generation are still active; duplicate, wrong-sender,
  wrong-marker, stale, late, or unstarted-epoch ACKs are ignored.

The current `on_ack_packet(receiver, packet)` interface does not receive
`RxInfo`; source validation must therefore happen in `on_receive` with the
actual `rx.sender`, or the callback contract must be changed explicitly.
Inventing a sender argument at a higher layer without preserving physical
receive evidence is not acceptable.

## 7. Same-wire ablations

The primary candidate and controls must use the same bounded state caps,
packet format, source-start hook, PHY, application trace, route expiry,
FLOOD delay, and random-stream roles. No arm may draw extra randomness merely
to record a shadow decision.

| Arm | Deliberate difference |
| --- | --- |
| `drc` | Full deadline-reserved R plus one admissible recovery F. |
| `drc-no-rescue` | Same initial decision, bytes, guards, and route updates, but suppresses the guard recovery F. Isolates the same-flow recovery contribution. |
| `drc-fixed-guard` | Same source/route state and initial R/F branches, but derives the recovery guard from one frozen fixed timeout `g_fixed` rather than `B_R(P)`. It still checks `t_F + B_F0 <= D` at the actual recovery start. Isolates a deadline-derived guard from “wait then retry” without permitting an after-deadline packet. |
| `drc-all-f` | Same finite state and immediate ACK contract, but sends one initial useful F whenever `B_F0` fits; no R reservation. Isolates route use versus FLOOD. |
| `drc-r-only` | Same initial route/F admission but never sends recovery; retained only as a simple route-only context control if the runner needs it. It is not a substitute for `drc-no-rescue`. |
| `drc-afs` / `drc-nocancel` | Optional secondary factorial only after source-only DRC passes: identical DRC source and wire behavior, with off-path terminal-ACK cancellation enabled/disabled. It is not part of the minimum-core claim because the old AFS scaffold failed its ACK noninferiority gate. |

The unchanged `meshecho-sr`, `meshecho-dhr`, DCB, and Trial arms are useful
historical/context comparators. They are not same-wire substitutes because
they have different source state, discovery semantics, timers, or packet
fields. Meshtastic/MeshCore-like models remain simulator abstractions, not
firmware parity claims.

## 8. Required observability and metrics

Every run must persist, with stable flow and packet identifiers:

- all scheduled flows, including state-capacity and deadline-infeasible drops;
- decision request time, actual physical TX start/end, chosen action, path,
  route generation, and queue wait/no-start reason;
- `R_RESERVED`, `R_ONLY`, initial F, recovery admission/cancel/start, and
  guard reason counts;
- valid and rejected ACKs with rejection reason, actual sender, marker,
  path, generation, and source acceptance time;
- route `READY -> QUARANTINED -> EVICTED` transitions and LRU/seen-key
  evictions;
- deadline source-ACK PDR and destination PDR separately, capped completion
  delay, duplicate deliveries, collision/half-duplex failures, and ACK delay;
- complete physical TX count, bytes, ToA, control/data/ACK breakdown, and
  modeled TX energy on the same start-time window. Raw RX energy is reported
  separately if its accounting window differs;
- peak source active records, destination records, relay duplicate keys, and
  any optional AFS pending records.

The artifact validator must recompute these values from raw flow/action/TX
records and reject an arm if an action has no matching physical request or if
an accepted recovery ACK lacks a matching started recovery packet. It must
also reject TXs after a flow deadline, invalid path/sender joins, out-of-window
cost rows, and stale source-generation commits.

## 9. Prospective evidence gate

No cohort is authorized by this note. After implementation and independent
review, choose fresh disjoint development and holdout seeds and freeze source,
runner, case, and hash manifests before any mechanical smoke. The previously
inspected 492xx/493xx screens and closed 494xx candidate range cannot validate
DRC. The 47xxx/48xxx cohorts remain closed.

Use seed-paired differences, with all-scheduled-flow denominators and nominal
two-sided 95% intervals over seeds. Never use pooled flow totals as the
uncertainty unit. The following are internal stop/gate criteria to freeze
before the development run:

| Comparison | ACK-PDR lower bound | Destination-PDR lower bound | Relative complete TX-airtime upper bound |
| --- | ---: | ---: | ---: |
| `drc - drc-all-f` | `> -0.02` | `> -0.01` | `< 0` |
| `drc - drc-fixed-guard` | `> 0` and point gain `>= 0.02` | `> -0.01` | `< +0.10` |
| `drc - drc-no-rescue` | `> -0.02` | `> -0.01` | report as attribution; no rescue from a failed primary gate |

The mechanism exposure floor is at least 20 actual R-to-F recovery starts
and at least 20 reserve-caused initial-F decisions across at least ten
development seeds. A passing aggregate interval with sparse exposure is
inconclusive. A failed development gate stops positive DRC claims and leaves
the holdout untouched. A passed development gate permits one unchanged-hash
holdout only; it does not imply an ICC acceptance probability.

## 10. Implementation blockers before coding the core

1. **Atomic physical-start choice (blocking).** `Simulator.begin_transmission`
   computes `start = max(now, tx_available_at)` and then calls only
   `PendingSend.can_start_at`. That predicate can cancel a queued packet but
   cannot atomically replace it with F or R after an intervening ACK or route
   update. Add and test a source-only pre-start decision callback, or an
   equivalent defer-and-retry event at `start == sim.now`. Merely moving the
   current `send_app` code into `on_transmit` is too late and violates this
   contract.
2. **Physical ACK sender evidence (blocking).** The source callback currently
   lacks `RxInfo`. Validate path adjacency and sender in `on_receive` or
   explicitly thread `RxInfo` through the callback.
3. **Finite inherited state (blocking for deployability).** SR miss sets,
   flood seen sets, and diagnostic maps are not all bounded by the existing
   eight-entry route LRU. Implement the DRC caps and make every matched arm
   use the same duplicate-cache policy before claiming finite-device behavior.
4. **Generation and equal-time ordering (blocking for correctness).** Test
   an old R timeout after a newer F commit, a late old ACK after quarantine,
   an ACK exactly at `D`, an ACK between queued request and physical start,
   and a recovery request canceled at the same timestamp as its ACK.
5. **Accounting and runner parity.** Preserve complete packet ToA for every
   started TX, join queued requests to contiguous physical TX IDs, record
   queue wait/no-start censoring, and use role-keyed random streams. A shadow
   arm must not consume random numbers or alter packet scheduling.
6. **Prior-art and hardware boundary.** DHR, AODV/DSR local repair, ExOR,
   Bypass Routing, implicit-ACK forwarding, and LoRa opportunistic routing
   are relevant prior art. The proposed combination needs a targeted
   literature review and positive matched evidence; the simulator alone is
   not a radio deployment or hardware certification.

## 11. Decision and next safe action

**Decision: GO for design implementation after the blockers are resolved;
NO-GO for experiments, paper edits, versioning, GitHub, or EDAS now.**

The correct engineering scope is to keep the tested simulator and historical
controls, but write a new `MeshEchoDRC` source/recovery core from a clean
finite-state contract. Do not patch thresholds into SR, promote DCB/Trial
components, or reuse old exploratory effect sizes as evidence. The first
implementation slice must be public tests for physical-start re-evaluation,
deadline-boundary ordering, recovery cancellation, ACK sender/marker checks,
generation safety, state-capacity behavior, and packet-byte/ToA parity.
Only after those tests pass and an independent audit signs off may a fresh
mechanical smoke, development matrix, holdout, and ICC manuscript rewrite be
considered.
