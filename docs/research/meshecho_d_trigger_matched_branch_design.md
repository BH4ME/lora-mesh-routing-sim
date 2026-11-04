# Matched D-trigger branch diagnostic for the MeshEcho core rewrite

Date: 2026-10-05. Status: draft prospective exploratory design. No seed in
this design has run. This is not a protocol, confirmation cohort, ICC result
or authorization to open the sealed 47xxx/48xxx cohorts.

## Question and entry state

The audited 493xx whole-policy comparison shows D has high control cost,
but it cannot identify whether a particular D was preferable to an R or F
from the same state. Use old DCB as a keyed-randomness reference. Immediately
before a `send_app` event that the unchanged old DCB rule would classify as
D, capture the full pre-decision state; do not infer eligibility from a
post-decision action event. Include every eligible D, not only successful
ones. Aging D with an unexpired old route permits D/R/F; cold D without a
route permits D/F only. Never fabricate a cached route for cold D.

The candidate nonreserved diagnostic range is 49401--49440, subject to
pre-run global inventory, implementation tests, input/source hash freeze and
independent audit. It must be run once only after those checks. A mechanical
smoke uses a separate nonreserved seed. No online policy is tuned or evaluated
on sealed 47xxx/48xxx here.

## Matched interventions

Reconstruct each target from the start under the same old-DCB reference
until the target application's exact event-queue position. From that prefix:

1. D: execute original RREQ/RREP discovery and its candidate useful DATA;
   if discovery times out, its original fallback F is the first useful
   payload. Charge all physical discovery/control transmissions.
2. R: send one useful DATA on the pre-decision ACK-confirmed old route.
3. F: send one useful DATA FLOOD immediately, with the actual DCB useful-F
   TTL and packet/ACK format.

For the primary contrast, all arms retain DCB destination feedback, relay
backup, route-cache/ACK validation and packet format, but allow no target
same-flow rescue after the first useful payload. Use the original enqueue
time plus 30 s as the common deadline. Debit one source discovery token and
set `last_discovery_at` at the D opportunity in *every* arm, so later source
bookkeeping does not confound the physical D/R/F contrast. The override must
record the true F/R/D action and useful-payload action for ACK acceptance.
All non-target flows remain under unchanged old DCB. Do not inject the route
found by D into another arm or suppress real collisions/interference.

A separately labeled, predeclared secondary 3 x 2 contrast can cross the
initial D/R/F choice with zero or one identical fixed-F rescue. If enabled,
start the 15-s ACK guard from the first *physical useful-payload* start in
every arm and apply the same capacity, busy-radio and original-deadline
guards; log admission, queued attempts and actual physical rescue starts.
Do not compare an R-only rescue against D/F without this same opportunity.

## Pairing and audit

Preserve the same topology, application schedule, shadowing, time-varying
fading and exogenous random draw identity. Pair reception uniforms by
`(seed, flow, role, sender, receiver, role-link attempt ordinal)`, incremented
on every potential receive callback even if half-duplex/collision prevents
decoding. Roles distinguish discovery control, initial useful payload, ACK
and rescue; the initial useful-payload role deliberately excludes packet
kind, so D candidate DATA, R DATA and F FLOOD share a draw on a matching
directed-link attempt. Key FLOOD relay jitter independently by flow, relay,
role and attempt. Keep actual packet length, timing, interference, channel
and PHY-decode rules; common random numbers do not imply identical received
outcomes. The earlier `tools/diagnose_source_branches.py` is a pattern for
replay, not a drop-in protocol or ACK contract for DCB.

Require exact pre-target equality of source state and route, source token
and discovery ledger, completed flow/ACK/action history, scheduled trace,
topology/radio parameters, physical and committed-future TX prefix, target
event tie order and relevant simulator state. Save case/trace/source hashes.
Abort an entire affected target on any prefix mismatch; do not relabel an
invalid branch as a failed delivery. Audit first useful physical start,
actual D candidate/fallback and any rescue start before interpreting a
branch. Count no-start and deadline-censored targets explicitly.

## Outcomes and decision boundary

Primary paired outcomes per target are source ACK and destination delivery
by the original 30-s deadline. Charge complete packet ToA for every network
TX whose start lies in the target's enqueue-to-deadline window. Also report
target-flow full-run ToA, full-run network ToA, TX energy with its declared
cutoff, raw modeled RX energy separately, bytes, collision *receive-attempt*
failures, queue wait and post-deadline spillover. Report both target-level
paired differences and seed-clustered intervals; a targeted branch effect
is not automatically a whole-policy effect.

Log only pre-decision source-visible candidate modifiers, especially old
route hop count and the most recent accepted pair-ACK age. The audited 493xx
history had only two of 34 aging D triggers with an ACK age >=120 s, so this
threshold is not a supported policy discriminator. Route hop count was 10
one-hop versus 24 multihop triggers, still too little to select a rule now.
Require at least 80 aging targets across 20 seeds for an overall exploratory
branch reading; require at least 30 targets across 10 seeds per subgroup
before discussing a subgroup tradeoff. If a floor fails, report NO-GO for
that inference and do not retune thresholds after seeing outcomes.

An observed D ACK where matched R and F both fail is descriptive
"D-only success" for that target, not a classifier. A future device-local
source/feedback/recovery state machine is justified only if a pre-decision
signal predicts a reproducible reliability/cost tradeoff against simple
same-wire rules. Freeze that complete rule and quantitative gates *before*
new whole-policy development and untouched holdout. Rewrite ICC method,
results and claims only if that later evaluation passes.
