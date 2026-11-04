# MeshEcho source-action branch diagnostic

Date: 2026-10-04. Status: pre-implementation exploratory contract. This is
not a new protocol, a population performance result, or an ICC paper claim.
The question is whether a source-visible high-risk state offers a useful
alternative to another route send before designing a new controller.

## Entry state and arms

Use the unchanged recurring-fading topology and application scheduler from
`tools/run_sr_experiment.py`. The reference policy is `meshecho-dhr-none`:
old MeshEcho-SR initial F/R/D decisions, no same-flow recovery. At an
application send, select a target if the source has an unexpired
ACK-confirmed route to the destination, exactly one trailing R ACK miss,
no pending discovery, and the old policy would send R. These are local
source facts; do not filter using this flow's destination receipt, future
ACK, hidden link PRR, or oracle path. Record the route hop count and age;
one-hop paths are a predeclared secondary stratum, not an inclusion rule.

For each eligible target, replay the same seed and scheduled applications
four times from the start, intervening on this target flow only:

1. `R`: send one DATA on the confirmed path; no same-flow rescue.
2. `F`: send one useful-DATA FLOOD immediately; no same-flow rescue.
3. `R-F`: send the same initial R as arm 1, then allow one fixed-F DHR
   rescue at its existing 15-s ACK guard if the existing deadline,
   capacity, and source-busy guards admit it. Log non-admission; do not
   count a scheduled but unstarted FLOOD as a transmitted rescue.
4. `R-R`: send the same initial R as arm 1, then allow one same-guard
   fixed-R DHR repeat under the identical admission guards. This is the
   direct same-trigger control for generic retransmission benefit; its
   actual TX cost need not equal the F rescue's network cost.

All non-target flows use the reference policy. The first two arms are not
three-arm bandit training data; this is a targeted potential-outcome screen
under a particular controlled traffic history. The active algorithm is
never allowed to observe the diagnostic's counterfactual branches.

## Pairing and observables

The four branches must match strictly *before dispatching* the target
application event (including its event-queue tie order):
topology/configuration, scheduled application trace, source-visible route
and miss state, all completed flow/ACK records, and normalized full TX
prefix as booked by that point, including TXs committed for future physical
starts. `send_app` mutates the miss state, so a post-decision action log is
not an eligibility snapshot. A mismatched prefix invalidates the target.
Reconstruct the same
seed from scratch for each branch; do not deep-copy callbacks or event
closures. Keep the existing model's static shadowing and time-varying
fading fixed by the common seed. Enumerate targets with this same
diagnostic-keyed reference model from the start, not with the stock
sequential reception stream.

The existing simulator consumes sequential reception uniforms, so merely
reusing a seed does *not* pair exogenous reception randomness after an
intervention changes the TX count. In this diagnostic only, replace each
reception-probability uniform with a deterministic hash of
`(seed, flow_id, sender, receiver, sender-to-receiver attempt ordinal)`.
Increment the ordinal for every potential physical receive callback,
including half-duplex/collision failures. Exclude packet kind so the same
initial sender-to-receiver attempt in R and F shares a uniform. Keep the
actual packet length, timing, interference, path loss, fading, collision,
and PHY decode rules unchanged. Label this as common-random-number
pairing, not identical realized channel outcomes or an independent
hardware measurement. Flood-forwarding jitter also uses a sequential
draw in the stock simulator. In this diagnostic only, key its uniform by
`(seed, flow_id, relay, repair marker, relay attempt ordinal)` while
preserving the existing delay formula, so a target F does not move
background flows' jitter draws. A wrapper around the simulator's
reception draw and a diagnostic-only flood-delay override are acceptable;
production protocol/radio behavior must remain unchanged.

Count source ACK and destination delivery only by the target's original
application enqueue time plus 30 s. Record accepted ACK time, first
delivery time, actual source DATA/FLOOD starts, guard admission, and
actual R-F/R-R rescue starts separately. A guard-admitted but subsequently
rejected `PendingSend` is not a transmitted rescue. For every network TX
whose *start* lies in the target's `[enqueue, deadline]` window, charge
its complete packet ToA even when its end is later. Include concurrent
background traffic. Report target-flow-only ToA for all booked target
TX starts through the 630-s run, plus full-run network ToA separately;
post-deadline target spillover is excluded only from the target-window
metric, not silently erased. These are three different estimands. Count
DATA/FLOOD, other control, and ACK TX as disjoint classes, plus collision
failures in the target window;
flag TXs whose RX/collision completion is censored by the 630-s run stop.
The policy may read only local state; result analysis may inspect full
simulator metrics. An F intervention must set both source action and
actual DATA action to F so its ACK can be accepted and its realized path
committed; merely swapping a transmitted packet kind is invalid.

## Split and decision boundary

Use seed 34000 for a mechanical smoke and exactly 34001--34005 for one
exploratory diagnostic pass. These seeds are disjoint from earlier SR,
DHR, BAR, AFS and other research cohorts. Reserve 35001--35040 for a
future frozen algorithm's development, and 36001--36040 as untouched
holdout; do not run either reserved range for this diagnostic. Store the
case/trace/source hashes, all eligible targets (including non-admitted
R-F), branch rows, and enough prefix/decision evidence for independent
validation. A missing exposure is a result, not permission to change the
entry rule after seeing outcomes.

The diagnostic can establish only whether R, F, or R-F has a promising
tradeoff in the predeclared state within this simulator. It cannot prove
an online policy's whole-workflow effect, superiority over a one-miss
fixed-F heuristic, novelty, or ICC acceptance. A future core must be
separately specified, compared with same-budget simple controls, and
tested prospectively on fresh development and untouched holdout seeds.
