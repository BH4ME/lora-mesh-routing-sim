# MeshEcho reverse-ACK physical-failure cause diagnostic

Date: 2026-10-04. Status: pre-implementation exploratory contract. This is
an unchanged-protocol observation, not a new algorithm, counterfactual
success estimate, or ICC result.

## Question and fixed setting

Could preventing same-flow FLOOD tail transmissions plausibly protect a
reverse ACK under the current 30-s deadline? Reproduce the frozen
`recurring_fading` case with `meshecho-dhr-flood`, 600-s application
generation, 630-s drain, and complete TX ToA accounting. Use seed 37000
only for mechanical smoke and 37001--37003 once for exploration. These
seeds are disjoint from all prior candidate cohorts and from unopened
35001--35040 development and 36001--36040 holdout. No source/relay/
destination policy behavior may change.

Run the stock baseline and the instrumented replay on identical topology,
selected pairs, and application trace. Require exact per-flow delivery and
ACK timestamps and source actions, not just matching aggregate rates.
Record case, scheduled-trace, source, and artifact hashes before drawing
mechanism conclusions. Include all delivered-but-unACKed flows, not only
those whose first DATA was a FLOOD; report the FLOOD-triggered subset too.

## Cause classification

For each emitted ACK attempt, follow its actual intended reverse hops as
in `diagnose_flood_ack_hops.py`. At its first physically undecoded hop,
reconstruct the simulator's receive decision from complete TX history:

1. `half_duplex`: the intended receiver was transmitting during any part
   of this ACK TX. This precedes all capture/PRR checks in the model.
2. `capture_collision`: absent half-duplex, an overlapping transmitter's
   received power made ACK signal power less than strongest interference
   plus the configured capture threshold.
3. `probabilistic_with_interference`: neither condition above held, but
   weaker overlapping transmissions reduced SINR and the ACK failed the
   model's probabilistic decode draw.
4. `probabilistic_no_interference`: no overlapping interferer existed and
   the ACK failed the probabilistic decode draw.

Do not label class 3 as a proven collision cause: without replaying the
same receive uniform without interferers, the ACK might still fail.
For classes 1--3, save each overlapping TX's sender, kind, flow ID, start,
end, whether it matches the failed ACK flow, and whether its start was
after first destination delivery. Record the receiver's own TX separately
for half-duplex. Count ACK attempts and unique delivered-unACKed flows;
do not multiply several failed attempts on one flow into several eligible
flows. Preserve packet-level evidence sufficient to independently
recompute the class from radio parameters and the saved overlap list.
Also save a compact complete TX timeline (ID, sender, kind, flow, start,
end, and commitment time) so the absence of any additional overlap can
be independently checked; keep the existing full-packet TX hash for
baseline parity.
Also record each overlapping TX's actual `begin_transmission` commitment
time separately from its possibly later scheduled physical start.

## Feasibility boundary

A same-flow FLOOD TX overlapping an ACK after first destination delivery
is only an **offline upper-bound** opportunity. The relay cannot observe
global destination delivery unless an on-wire signal reaches it, and a
committed future TX may not be cancelable through the present API. A
proactive quiet timer could defer a relay before an ACK exists, but may
also delay the only useful forward path; no benefit is inferred from the
classification alone. Report unrelated-flow interference, half-duplex,
and probabilistic losses separately.

For a stricter *possible intent-cancellation* upper bound, assume an
11-byte `ACK_INTENT` starts at first destination delivery and cannot be
decoded by any relay before its complete SF7 ToA. Count a sole same-flow
FLOOD interferer only if its commitment time is later than that earliest
completion time. This is deliberately optimistic: it does not assert the
relay could physically decode the intent, that it knows the globally
successful path, or that suppressing the FLOOD would preserve delivery.
Count a candidate only if its first failed ACK hop completes before the
flow's original deadline and even zero-queue forward progress could reach
the source by that deadline: `failed_hop_end + remaining_ack_hops * ACK_ToA
<= deadline`. Record both the remaining-hop count and this optimistic
earliest source-ACK time. Report both the broad physical overlap and
stricter intent-timing upper bound after applying this deadline condition.

Reject an ACK-quiet-window core before coding if fewer than four unique
delivered-unACKed flows, or fewer than 10% of all delivered-unACKed flows,
have a first failed ACK hop in class 1 or 2 with a sole overlapping
same-flow FLOOD passing the stricter intent-timing upper bound. Passing that *necessary
exposure screen* is not sufficient: a later rule must show a device-local
trigger and beat fixed R-F, same-path ACK repeat, ACK cancellation (AFS),
and a simple fixed forwarding delay under original deadline, delivery,
source-ACK, and full-network airtime metrics. SOAR/PRIOR-style prioritized
forwarding and Meshtastic ACK cancellation are close precedents, not
automatically cleared novelty.
