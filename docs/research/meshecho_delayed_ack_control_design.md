# Fixed-delay FLOOD ACK control

Date: 2026-10-04. Status: pre-implementation control contract. This is a
simple timing comparator, **not** a novel MeshEcho core or an ICC result.

## Purpose and split

The old fixed-F DHR destination emits a reverse ACK immediately after its
first valid FLOOD decode. That ACK can overlap still-running same-flow
FLOOD forwards. A 2-s wait is suggested by already inspected 37xxx
trajectories and is therefore a *chosen exploratory parameter*, not an
untuned population estimate. Test it prospectively on seed 38000 for
mechanical smoke and 38001--38020 once for exploration; do not use sealed
35001--35040 or 36001--36040. Keep the `recurring_fading` case, original
30-s source deadline, 600-s application schedule, 630-s observation drain,
and all fixed-F source/recovery behavior unchanged.

## Exact behavior

Add an explicit `meshecho-dhr-flood-ack-delay` control. It is identical to
`meshecho-dhr-flood` except that the destination schedules the **same**
single reverse `ACK` packet 2.0 s after the first valid FLOOD delivery.
The delay begins at physical FLOOD decode completion (`sim.now`), before
normal destination TX queueing; queueing may make actual ACK start later.
Routed `DATA` ACKs remain immediate. FLOOD duplicate suppression, source
actions, DHR recovery, route commit, path, request/repair marker, ACK bytes,
radio, and all relay behavior remain unchanged. Do not cancel the delayed
ACK based on simulator-global deadline or delivery state. Charge every
ACK TX starting within the declared 630-s primary window, including ones
too late for the source deadline. Count ACKs still scheduled but unstarted
at that cutoff; if any exist, report a symmetric 660-s extended-drain
airtime sensitivity for both arms. Do not call the 630-s result all
eventual cost. No new on-wire field or source state is introduced.

Implement the timing at the reverse-ACK scheduling boundary with a default
zero-delay hook, so existing protocols retain byte-identical behavior.
Use test-first vertical slices: one real FLOOD-to-ACK delay test, then
unchanged DATA-ACK timing and packet/duplicate checks. Run the full suite
before any seed. The `meshecho-dhr-flood-ack-delay` CLI registry entry must
be explicit and keep the fixed-F rescue mode.

## Audit and interpretation

Require the immediate control to match unchanged fixed-F in exact
application trace, source action log, flow timestamps, complete TX trace,
and aggregate metrics for every exploratory seed. Pair delayed and
immediate arms on each seed; report per-seed and paired 95% intervals for
source ACK PDR, destination PDR, full-network TX ToA, collision/half-duplex
counts, and ACK latency. Retain per-flow first FLOOD delivery and ACK TX
timings, complete TX hashes, source hashes, and an output manifest.

Do not infer which old lost ACKs the delay would have rescued: delaying
changes FLOOD reception, collisions, and later source actions. A positive
timing effect is a strong *simple baseline* for any proposed corridor,
not a new algorithm. A negative effect would disfavor this fixed wait but
would not rule out every locally scheduled feedback design. Any later
passive corridor recorder must observe the delayed-control arm itself;
the immediate baseline's pre-wait FLOOD decodes are not a necessary gate.
