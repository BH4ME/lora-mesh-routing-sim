# MeshEcho-DCB prototype contract

Date: 2026-10-05. Status: implemented prototype, *not frozen*; this remains a
development hypothesis, not a measured protocol result or an ICC method claim.
The passive 46xxx screen in
`meshecho_destination_certified_backup_explore_results.md` only permits a
test-first prototype. The protocol must use fresh development seeds; 46xxx
is not a causal or holdout cohort.

This five-arm design isolates the destination-feedback/relay component while
retaining the old F/R/D source controller. Even a positive component gate
does not validate a rewritten source algorithm or authorize an ICC core claim;
a later same-byte source-controller factorial test must establish source
action divergence and causal benefit before the manuscript method is replaced.

## Device-visible state and wire format

The `meshecho-dcb` family retains the fixed-2-s F ACK wait, the existing
F/R/D source controller, and the initial-R physical-start + 15-s fixed-F
recovery of `meshecho-dhr-flood-ack-delay`. It changes the destination
feedback, the source's next direct R header, and the nominated relay's
same-flow forwarding decision. It must have a distinct protocol name and
cannot read the simulator's true PRR, global delivery/ACK state, future
events, or another node's private protocol state for any decision.

Add optional 16-bit `backup_relay_id` and 32-bit `backup_epoch_id` packet
fields. Charge one extension/flags byte whenever either exists, plus two
or four bytes respectively. These fields must survive ordinary `Packet` copy
operations. The existing one-byte `repair_index=4` is the explicit backup
DATA/ACK marker and is charged separately. `request_id` on DATA/ACK is
simulator metadata in the present wire model and cannot replace any of
these charged bytes. Thus a nominated F ACK adds three bytes, a nominated
initial R DATA adds seven, and backup DATA/reverse ACK each add the five-
byte epoch extension plus the one-byte marker. This is intentionally more
conservative than the passive screen's minimum 2/6/1-byte costs. Constructing
backup DATA intentionally removes `backup_relay_id` because its three-node
path already names the relay; the reverse ACK echoes only the epoch and marker.
A direct-path R ACK does not echo either extension field.

At a destination, collect at most four distinct physically decoded F
paths per flow in a two-second window after the first valid decode, with
at most eight concurrent windows per destination. Construct exactly one
ACK *when the window closes*, using the first valid path as primary. Only
when that path is `(source,destination)`, choose the earliest-decoded
distinct two-hop `(source,relay,destination)` alternative, breaking an
exact-time tie by relay ID. Put only its relay ID in the ACK. If capacity
is full, send one immediate primary ACK without a nominee and remember that
flow in the existing duplicate-suppression set; the full-window
exception does not allocate a ninth window. If no valid alternative is seen
in an admitted window, send the primary ACK without a nominee. Initial F and
marked same-flow F recovery use this
same rule; late or duplicate paths never create a second ACK.
The inherited flood duplicate-suppression set is not bounded in this
simulator. The eight-window cap is only a feedback-window bound: report the
peak inherited seen-set size and make no whole-protocol bounded-memory claim.

A source stores a certified backup only from an actually received and
accepted F ACK whose primary path is direct and whose relay ID differs
from both endpoints. The stored source-local record is `(destination,
primary path, relay ID, F flow ID, ACK acceptance time)`, within the
existing eight-destination source-state bound. A later direct initial R
DATA is nominated only if the latest accepted route generation is that F
flow and the backup age is at most 120 s **at DATA enqueue**. The queued R
DATA immutably carries the relay ID and F epoch. `begin_transmission` can
commit a packet before its future physical start and call `on_transmit`
early: this callback may schedule activation, but must not activate the
source record or timer before the actual R start. At that start event, bind
the immutable packet identity to the current flow, nominee, epoch and
original application deadline. A newer route commit neither changes an
already queued packet nor retroactively alters an active flow's ACK identity.

## Relay and ACK transition

Only the named relay may buffer a direct initial R DATA that it physically
decodes from the source and whose charged nominee/epoch fields are valid.
Keep at most four pending nominated flows per relay; on overflow drop the
newest. The relay sets a local timer for two seconds after that physical
DATA reception. It marks a pending flow quiet only if it itself physically
decodes a direct-path destination ACK with matching flow/endpoints and
actual ACK sender before the relay radio start. It does not read the
source's ACK status or remote deadline. At the timer, after same-time
physical receptions, it sends at most one backup DATA if no matching ACK
was heard and its radio is idle. If busy, skip rather than commit a queued
transmission whose actual start would be later than the two-second bound.
The `tx_request` rechecks the same local state and exact current start;
the timer does not claim a successful delivery. A no-forward control
keeps all fields/state but never sends. An unconditional control uses the
same nominee/timer and ignores the overheard ACK gate, while retaining
the same radio-busy rule.
Flow IDs are monotonic for each source within this simulation/session. A
relay keeps a per-source high-water mark of flows for which it physically
started a backup TX and ignores that flow ID and older late duplicates;
this gives one-shot forwarding without an unbounded completed-flow set.

Backup DATA has path `(source,relay,destination)`, path index one, marker
four, and the echoed F epoch. The destination may deliver it once and
returns a reverse ACK on the traversed path with the same marker and
epoch. Every reverse hop checks the actual physical sender against the
next node in that path. A source accepts a backup ACK only if its locally
active flow matches the source/destination, nominee, echoed F epoch,
three-node path, marker, current flow ID and original 30-s deadline.
There is no source-side read of a global relay-transmitted flag: the ACK
is generated only from a physically received marked backup DATA, and
instrumentation independently verifies that provenance. A backup ACK
confirms the flow and can clear a current R miss, but does not commit the
two-hop backup as a future primary route. Direct R and F ACK behavior
otherwise retains existing route-generation rules. If a newer route generation
has committed, the older flow may still be ACKed, but its ACK cannot clear
the newer generation's miss counters or replace that route.

## Controls, observations, and falsification

First implement `meshecho-dcb-no-forward` as a same-field parity/overhead
control, `meshecho-dcb-unconditional` as the ACK-gate ablation, and
`meshecho-dcb` as the conditional candidate. An IOMC-like current-packet
overhearing contender must receive the same packet-byte and two-second
time budget but choose forwarding from its own local receptions rather
than a destination-certified nominee. Identical nominee/timer/gate arms
are a parity check, not evidence of superiority. Also compare fixed-2-s
F, fixed-time source R/F and R-F, two-hop F, and LPR-like repair using
matched sources/deadlines and complete-network costs.

The current staged matrix has five component arms (DCB, no-forward,
unconditional, current-overhear, and fixed-2-s F), one DCB-wire source
control (`meshecho-dcb-source-fr`), and three contextual controls
(`meshecho-dhr-flood-ack-delay-flood2`, `meshecho-sr-fr`, `meshecho-lpr`).
The source-FR arm keeps DCB feedback, nomination bytes, relay rule and
15-s R-to-F recovery, but replaces only D-triggered initial decisions with
F/R. The two-hop arm limits useful-DATA F packets, both initial and recovery,
to TTL 2 without reducing global RREQ/RREP route budget. Ordinary SR-FR
has immediate F ACKs and no same-flow R rescue; LPR has different packet
fields and timing. These three are explicitly contextual, not same-budget
mechanism gates. The DCB-wire matched LPR-like and additional fixed-source
controls promised above are still absent, so the contract remains draft.

Freeze `meshecho-dcb-current-overhear` as a selector ablation, not a faithful
IOMC implementation. It uses identical F ACK/R DATA wire fields and source
eligibility but ignores the carried nominee. Any router/repeater other than
the endpoints that physically decodes the current direct R DATA from the
actual source may contend. Each relay retains at most eight `(sender, RX
time)` entries from its own physically successful receptions. If the
destination was decoded within 120 s before current DATA reception, the
relay uses an early slot 0--3; otherwise it uses slot 4--7. The slot within
each group is CRC32 of network-order `(32-bit current flow ID, 32-bit F epoch
ID, 16-bit relay ID)` modulo four. Attempt at DATA-RX time plus
`0.25 * (slot + 1)` seconds, never later than 2 s. Suppress on a physically
decoded matching destination direct ACK or another relay's valid marked
backup DATA; skip when the radio is busy at the timer or exact TX request.
Multiple contenders and collisions remain real measured costs. The source
accepts a marked backup ACK via whichever relay actually forwarded, with
the same flow/epoch/path/sender/deadline checks except for DCB's nominee
equality. Giving this arm the DCB nominee/timer/gate unchanged is merely a
trace-parity control.

Public behavior tests must cover charged bytes and copy preservation;
window close/ties/capacity; source ACK-only certification and generation
expiry; relay current-packet physical decode, ACK overhear, same-time
ordering, busy-radio cancellation and one-shot capacity; backup DATA
delivery, sender/path/epoch/deadline ACK validation; and unchanged fixed-F
recovery on a missed backup. Log packet, local state, actual radio start,
and every acceptance/rejection cause without changing the radio RNG.

The older screen's suggestion that a source checks a remote relay's actual
TX start is superseded: a source cannot observe that event. Only local
packet/flow identity may accept an ACK; separate instrumentation checks
physical provenance without affecting protocol decisions.

Reserve 47000 for a mechanical smoke, 47001--47020 for fresh development,
and unopened 48001--48040 for a once-only holdout after a development pass.
Use the same recurring-fading case, 600-s generation, original 30-s flow
deadline and all network TXs starting by 630 s. Pair complete scheduled
application traces by seed and verify identical case/traffic hashes. For
each seed and each arm, divide deadline source ACKs and destination deliveries
by all scheduled unicasts, and measure complete-network TX airtime. Compare
DCB minus each control with equal-weight paired seed means and two-sided
95% paired-t intervals; for airtime use `T_DCB/T_control - 1` per seed.

The strict development gate requires, versus fixed-2-s F, lower ACK-PDR
interval bound greater than -0.02, lower destination-PDR bound greater than
-0.01, upper airtime interval bound below zero and mean relative airtime at
most -0.05. Versus current-overhear, require the same two reliability bounds,
upper airtime bound below zero and mean relative airtime at most -0.02.
Versus same-byte no-forward, require both reliability bounds and upper
airtime bound below zero. Versus unconditional same-nominee forwarding,
require upper airtime bound below zero as an ACK-suppression mechanism check.
Require at least 20 actual DCB backup TX starts across ten seeds, at least
20 DCB/current-overhear forwarding-action differences across ten seeds, and
zero accepted invalid flow/path/epoch/deadline ACKs. Report energy, bytes,
latency, collisions, and queueing even on failure. For every committed TX,
record the request-event time and physical start beside the packet record;
over TXs starting by 630 s, report queued-TX count, mean, p95 and maximum
`start - request` wait. Use nearest-rank p95 over all included TX waits,
including zeros; report zero for an empty set. Persist committed request
events separately and join them one-to-one to physical TX IDs during artifact
audit. Report peak concurrent feedback windows per
destination, peak pending flows per relay, and the final/peak inherited
`seen_floods` entries per node, plus their network totals. The seen set is
add-only after bind in the current simulator, so its final size equals its
peak. Audit feedback and relay peaks by replaying each open/close transition,
not just checking capacity bounds. The seen set is not bounded; no
whole-protocol memory-bound claim follows from the two DCB window caps. These thresholds
are author-chosen research gates, not ICC acceptance criteria. An unchanged
mechanism must pass the same gate once on the untouched 40-seed holdout before
its measured results enter the ICC manuscript. Operational equivalence to
current-overhear requires its entire paired 95% airtime interval inside
[-0.02, 0.02] and ACK-PDR interval inside [-0.01, 0.01]; crossing zero alone
is inconclusive, not equivalence. A negative or marginal causal result is
NO-GO for this candidate even though the passive screen passed; do not
rewrite ICC numbers or claim novelty from the opportunity bound.
