# Passive reverse-ACK corridor feasibility diagnostic

Date: 2026-10-04. Status: **superseded before code or seeds**. The draft
below is retained for audit history, not executable as a rejection gate.
This was an unchanged-protocol opportunity proposal, not a new MeshEcho
algorithm, a counterfactual ACK result, or an ICC claim.

## Audit stop

An unchanged immediate-ACK baseline cannot supply a necessary reception
gate for a proposed 2-s delayed ACK: removing the immediate ACK changes
half-duplex and interference, so the FLOOD decode set before 2 s may change.
The proposed `+0.1 s/hop` and `+1 s` guard and an observed FLOOD tail ending
by `T` are descriptive/safety conditions, not physical necessities; their
failure cannot reject the branch. A cross-node minimum-cost path union is
also an offline oracle, not a destination-local route choice. No 380xx seed
was opened and no protocol code was written under this draft. Next, test a
fixed-2-s delayed single-ACK control against unchanged immediate ACK; only
then design a passive corridor observer on that control's actual decodes.

## Question and cohort

Can physically decoded FLOOD copies leave a bounded, device-local set of
breadcrumbs that could support a second reverse path to the source after
a fixed 2-s destination ACK deferral, at an optimistic cost below two
same-path ACKs and within the original 30-s application deadline?

Use the unchanged `meshecho-dhr-flood` arm in the frozen
`recurring_fading` case: 600-s application generation, 630-s drain,
independent channel RNG streams, and the existing connected-multihop pair
selection. Seed 38000 is mechanical smoke only; seeds 38001--38020 are a
single exploratory split. These have not been opened. Do not use sealed
35001--35040 or 36001--36040 or retune the design after inspecting 38xxx.

## Passive recorder and local-state emulation

Override only `RecordingSimulator.try_receive`: call its parent exactly
once and, after a physical FLOOD decode, append an observation without
calling RNG, scheduling events, changing metrics, or invoking protocol
behavior. Include duplicate copies that the protocol later suppresses.
Save TX ID, sender, receiver, receive completion time, origin, destination,
flow/request IDs, repair marker, TTL, transmitted path, locally derived
`path + (receiver,)`, SNR/SINR, and a full-packet TX trace hash. A usable
breadcrumb requires `request_id == flow_id`, a source-rooted simple path
ending at the actual TX sender, a receiver not already in that path, and
the marker of the destination's ACK-triggering FLOOD epoch. Protocol name
and `Packet.created_at` are simulator metadata, not over-the-air evidence.

Replay these observations as a *hypothetical* bounded relay cache keyed by
`(origin, destination, flow_id, request_id, repair_index)`: at most eight
live flow/epoch keys per node and the first two distinct upstream prefixes
per key. A key expires 30 s after its first local decode; expire lazily on
the next local decode or at an evaluated ACK time. If full, evict the key
with the oldest first-decode time, then lexicographically smallest key.
Do not refresh expiry or replace an admitted prefix because a later copy
looks better. The raw observer log may retain every decode for audit;
the candidate graph uses only prefixes still in this bounded cache at
the hypothetical ACK time.

The candidate graph reverses only *observed* FLOOD receptions. Its vertices
are `(node, retained source-rooted prefix)`, not merely node IDs; a prefix
at a receiver points to the same prefix without its last node at the
actual prior sender. Every edge strictly shortens the prefix, so these
prefix-state edges form a DAG even when the union of physical nodes contains
a cycle. Require the corresponding prior-sender prefix to have been
retained locally before using that edge. No simulator-global PRR or
unobserved reverse link is a device-local edge. Reverse radio success
remains unknown; this graph is optimistic even when every forward decode
was physical.

## Per-flow necessary conditions

Select flows first delivered by a FLOOD by their original deadline but
without a source ACK by that deadline. Use the epoch of the actual first
destination FLOOD decode. Let `t0` be its physical completion, `T=t0+2 s`,
`h` the original decoded path's edge count, and `A` the modeled SF7 ToA
of a full-path ACK carrying that original route and epoch marker. The
offline diagnostic may use flow/deadline and complete TX histories for
evaluation, but the hypothetical protocol cannot see them unless encoded.

A flow qualifies only if all of the following hold:

1. At `T`, the retained reverse-prefix DAG contains the original
   destination-to-source path and another path whose source-adjacent
   relay differs from the original path's source-adjacent relay. Both
   paths must have at most six edges and strictly decrease source-depth.
2. For each alternative, take the union of actual transmitter node IDs
   along it and the original route, including the destination but
   excluding the source. The minimum union cost `C_union` is the sum of
   full-path ACK packet ToA at each unique transmitter, optimistically
   one broadcast per node. Require `C_union < 2 * h * A`, the two
   same-path ACK TX budget. Report `N_union` as the corresponding count.
   Ignore all other relays in this lower bound; actual flooding can only
   cost more. The original DATA path remains immutable in the ACK frame
   for source route commit; reverse corridor rank/transport must be
   separately encoded and charged in any later protocol implementation.
3. The longest of those two paths fits the original source deadline even
   with `T + path_edges * (A + 0.1 s) + 1 s <= created_at + 30 s`.
   This still omits radio queueing and stochastic reverse loss and is only
   a necessary bound. The hypothetical protocol would need a charged
   deadline/time-budget field if it acted on a remote source deadline.
4. The complete *observed* same-flow, same-epoch FLOOD TX tail ends by
   `T`. This is an offline timing check, never a locally available signal.

Report each condition separately, the intersection, source-neighbor pairs,
path lengths, `N_union`, ACK packet bytes/ToA, latest same-flow FLOOD end,
deadline slack, cache evictions, and all raw FLOOD decode rows needed for
independent reconstruction. Denominator is **all** F-first delivered but
unACKed flows in the exploratory split, not only flows with a path pair.
The proposed `ACK_FLOOD` kind would require explicit control classification,
receive handling, duplicate suppression, and wire-byte accounting; none
exists merely because this passive diagnostic names it.

The preregistered necessary exposure gate passes only if the intersection
contains at least 20 unique flows, spans at least 10 of the 20 exploratory
seeds, and covers at least 10% of the denominator. Any failure rejects
this corridor branch before behavior code. Passing merely permits a
protocol prototype, not a positive result or source-core claim.

## Reproduction and downstream controls

For every seed, run the stock baseline, plain `RecordingSimulator`, and
passive observer on identical topology/pairs/traffic. Require exact
scheduled trace, per-flow timestamps, source actions, full normalized
TX trace, TX/collision metrics, and final random-generator states across
plain and observer runs. Hash the design, code/tests, case, output, and
all input sources before 38000; validate every physical decode against
saved TX intervals and receiver identity. The smoke only checks mechanics.

If the necessary gate passes, freeze a new complete packet/state/timer
contract and fresh development/untouched holdout cohorts. Paired controls
must include immediate single same-path ACK, fixed-2-s delayed single ACK,
immediate plus same-path second ACK at 2 s, equal-airtime same-path ACK
repetitions, unrestricted TTL-matched ACK flood, bounded corridor with
zero and 2-s waits, old SR, fixed R/F, and R-F/R-R. Compare source ACK,
destination delivery, original-deadline success, complete-network TX ToA,
state, and packet bytes. A successful reverse component still needs a
separate full-core source/recovery design. Lee et al. 2020, DOI
`10.1155/2020/8839541`, already cover multipath DATA/ACK and ACK-copy
waiting, so a broad novelty claim is not available.
