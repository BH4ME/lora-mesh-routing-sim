# MeshEcho-JFC: joint source recovery and receiver-observed ACK feedback

Date: 2026-10-04. Status: **untested candidate contract, not an ICC method or
result**. This document specifies one falsifiable full-core successor to
MeshEcho-SR. It does not authorize a paper claim, a new VERSION, a remote
upload, or use of the sealed 35001--35040 / 36001--36040 cohorts. All
numbers below are design constants or previously opened exploratory
observations, not JFC performance.

**2026-10-04 audit correction: NO-GO for implementation as written.** The
`P2` rule below diversifies the destination-adjacent edge (`P[-2]`), not
the source-adjacent `P[1]` edge that terminates the last reverse ACK hop;
36/47 earlier unACKed-FLOOD cases failed at that source-final hop. The
`min_forward_margin_q` below is a whole-path minimum, not a measured
first-edge predictor, and its logistic reverse-success score has not been
calibrated. Under current SF7 packet charging, a two-hop alternate ACK
costs 0.113152 s versus 0.051456 s for one direct ACK, already above a
two-copy direct-path budget. The audited 8-s fixed guard control also did
not beat its 15-s comparator. Preserve the following as rejected design
history; do not code or claim JFC until a new, independently screened
contract replaces these assumptions.

## Evidence boundary and reason to try

The currently tested SR source selects F/R/D using a confirmed route,
misses, route age, and discovery tokens. DHR adds a 15-s no-ACK R recovery.
Its fixed-F arm with immediate FLOOD ACK is weak at source confirmation;
delaying that one destination ACK by 2 s improved paired deadline ACK-PDR
by 0.2251 and lowered whole-network airtime by 16.73% on *exploratory*
seeds 38001--38020. That is a strong simple control, not a new algorithm.
After fixed 2 s, 55/781 flows still lacked source ACK; 44 reached the
destination, 42 had a FLOOD ACK, and 37 of those ACKs reached a final
transmission toward the source. Forty of the 42 had a second locally
decoded FLOOD path, but 79/89 alternatives were longer; saved packets did
not carry path-margin values. Alternative-path success cannot be inferred
from these traces.

Previous BAR alternate ACKs gained 0.1513 ACK-PDR versus a single-ACK
fixed-F arm, but only 0.0021 (95% CI -0.0292 to +0.0334) versus the
same-trigger same-path second ACK, while airtime was higher and uncertain.
MAG's source margin gate and DHR's recovery rule also failed their
predeclared joint development gates; AFS failed ACK noninferiority.
An additional physical-start join of the opened fixed-2-s arm found all
451 accepted initial-R ACKs within 0.149--0.637 s of their actual source
R TX start. The apparent 13-s enqueue-to-ACK outliers were queueing.
Consequently the proposed 8-s guard has no timing-novelty basis; fixed
1/2/4/15-s R guards with the same ACK contract are mandatory controls.
Consequently JFC **must not** be presented as novelty from ACK delay,
path diversity, route quarantine, or retransmission separately. Its
possibly useful question is narrower: can *one receiver-observed path
selection and conditional second ACK*, coupled to a source policy that
does not repeatedly use an unconfirmed route, jointly reach the fixed-2-s
control's reliability with less complete-network airtime, and outperform
the identical-copy-budget same-path repeat?

The source cannot distinguish an undelivered DATA from a delivered DATA
whose reverse ACK was lost if neither yielded a source-decodable signal.
JFC makes no such classification. Its no-ACK action is a conservative
useful-DATA recovery, and its source state records only ACK observations.

## On-wire contract and admissible observations

Unicast identities are `{kind, source, destination, flow_id, epoch}`.
`epoch=0` denotes an initial routed DATA or initial useful-DATA FLOOD;
`epoch=1` denotes the sole same-flow recovery FLOOD. It must be a real
charged byte on F/ACK when nonzero; the current `repair_index=2` can encode
the recovery epoch without a second field. `request_id == flow_id` is an
alias, not four independently charged bytes. A destination may reply to
the first physically decoded recovery FLOOD even if it already decoded
the earlier routed DATA; application delivery is still counted once.

Add these two fields to JFC DATA, FLOOD, and ACK and to every policy-isolation
control, charging them at every transmission:

- `budget_q`: unsigned 16-bit remaining original application lifetime in
  10-ms units. At a source's *physical* TX start `t`, set
  `floor((t_app+30-t)/0.01)`. A receiver at its successful RX completion
  computes `b_rx = 0.01*budget_q - packet_ToA`. Before its own TX start
  `t'`, it subtracts local elapsed time since that RX and rounds down
  again. This relative-lifetime transfer needs monotone local clocks, not
  synchronized absolute clocks. It never reads simulator-only
  `Packet.created_at` at a relay or destination. Source ACK acceptance
  still uses the source's exact `t_app+30` deadline. Clock drift and
  propagation are model limitations and need an explicit safety allowance
  before any firmware claim.
- `min_margin_q`: signed one-byte minimum *successfully decoded forward-hop*
  SNR margin in 0.5-dB units, initialized to sentinel 127 and updated on
  each DATA/FLOOD receive as `min(old, clamp(round(2*(rx.snr_db -
  required_snr_db(sf))), -126, 126))`. ACK echoes its selected received
  path's value. A node may use its own `RxInfo` only after a successful
  physical decode. This is neither a true reverse-link PRR nor an oracle
  collision outcome. The existing MAG field is a relevant prior
  implementation pattern, not independent validation of this predictor.
  Reuse the existing charged `Packet.min_forward_margin_q` slot for this
  field; do not add a duplicate byte or use `min_forward_margin_hop`.

Path, hop index, TTL, flow ID, and the epoch marker remain charged per
`Packet.wire_size_bytes`. `Packet.protocol` and `Packet.created_at` are
simulator metadata, not wire evidence. There is no ACK-success beacon,
global route table, true PRR, future FLOOD count, or access to another
node's queue. The destination sees only decoded copies, their carried
paths/margins/budgets, physical senders, and its local clock. The source
sees its queued application, accepted ACKs, local timers and route state.

## Bounded state and validity

- Each source holds at most eight LRU destination records with
  `{phase, ACK-confirmed route, route-expiry, generation, last-ACK time}`.
  Phases are `NO_ROUTE`, `READY`, and `QUARANTINED`. It also holds at most
  eight active flows with their original deadline, chosen initial action,
  path/generation, physical first-TX time, guard handle, recovery-start
  flag, and first valid ACK. At capacity, register the application flow
  but emit no untrackable packet; count the failure. Eviction invalidates
  a route and cancels only still-uncommitted local sends for its flow.
- Each destination holds at most eight active FLOOD ACK windows, keyed
  by `{source, flow_id, epoch}`, each with first local receipt time, up to
  four valid distinct realized paths, their carried `min_margin_q` and
  remaining budget, one selected ACK handle, and at most one second-ACK
  handle. Keep the first path, then the three highest scored alternatives;
  deterministic score/ID ties decide replacement. Expire 3 s after first
  receipt or after both pending starts are resolved. On capacity overflow,
  send an immediate first-path single ACK with no new timer or candidate
  record; separately count this different timing/cost branch. Ordinary
  same-epoch FLOOD deduplication must still prevent later extra ACKs.
- Each relay keeps existing pending-F handle and duplicate suppression.
  For a firmware-memory claim, replace the simulator's unbounded
  `seen_floods` with an at-most-128-entry, 30-s LRU/tombstone cache in
  **all** matched arms. Eviction may permit a second relay forward and
  must be measured. Until that change is implemented/tested, only JFC's
  incremental state is bounded; no whole-protocol MCU claim is valid.

At every decoded F, validate loop-free path length `2..H+1` after
appending the destination, `path[0]==source`, `path[-2]==rx.sender`,
`destination` absent before append, coherent TTL/flow/epoch, and
`budget_q>0`. R DATA and ACK require the path-index receiver to match and
the physically decoded sender to be the encoded adjacent hop. Intermediate
nodes must not validate against `sim.metrics.flows`, source action maps,
or hidden delivery state. The source accepts only the first physically
decoded matching ACK at or before its original deadline; an R ACK must
match the exact started R path, and a recovery-F ACK requires that epoch's
source FLOOD to have physically started. A late/duplicate ACK cannot
commit a route. A newer flow's committed route cannot be overwritten by
an older still-active flow, though that older flow can still be marked
ACKed by its own valid in-deadline ACK.

## Source finite-state controller

Remove SR's proactive D/RREQ/RREP action, two-miss reuse, route-age D
trigger, and discovery-token/cooldown logic. A useful-data F learns a
candidate route only from a valid source-received F ACK. Route TTL is
120 s from its last accepted ACK; expiration or one R no-ACK guard moves
the record to `QUARANTINED`. An accepted F ACK installs the returned
realized path and moves it to `READY`; an accepted R ACK refreshes that
exact route and restores `READY`. This is a deliberately simple source
rule, not a claimed invention of route repair.

For application enqueue at `t_app`, set `D=t_app+30`. Do not choose or
instantiate its initial packet until the source radio can actually start
one at time `t`; re-evaluate route generation and D then. Let `H` be the
configured max hops. Compute conservative nominal bounds using *charged
JFC packet lengths*: `B_R(P)=h*(T_RDATAmax(P)+T_RACKmax(P))+1 s`, and
`B_F2=H*T_Fmax+(H-1)*(flood_base+flood_jitter+0.35 s)+2 s+
2*H*T_ACKmax+0.5 s+1 s`. The F bound allows the full 2-s hold and two
serial reverse ACK attempts. These are admission estimates, not
guarantees under unbounded radio queueing, stochastic losses, or
interference.

At physical start choose in this order:

1. If phase is `READY`, the path is unexpired, and `t+8+B_F2 <= D`, send
   one routed R DATA and schedule an 8-s guard from its *physical* start.
2. Otherwise, if `t+B_F2 <= D`, send one useful-data F immediately.
3. Otherwise, if a valid `READY` route exists and `t+B_R(P) <= D`, send
   one R with no same-flow recovery.
4. Otherwise, send nothing, retain the flow in the denominator, and log
   `deadline-infeasible`. There is no route-discovery-only packet.

For R-with-reserve, at `G=t_R+8 s`, if no ACK has been accepted, set the
route generation `QUARANTINED` and request exactly one recovery F for the
same flow with epoch 1. At its *actual* source TX start `t_F`, require the
same active flow, no accepted ACK, unchanged R generation, no previous
recovery start, and `t_F+B_F2 <= D`; otherwise cancel. If an R ACK arrives
before F commits, cancel F and restore `READY`. If F already starts, it
remains charged, and the first valid R or F ACK can confirm the flow.
An R ACK may restore only the same still-current route generation; a later
F ACK may replace it. No ACK by D leaves the route quarantined. An initial
F has no second payload recovery in this contract. A source never treats
no ACK as proof of forward DATA loss.

## Destination ACK controller and relay behavior

On the first valid F decode for `{source,flow,epoch}` at local time `u`,
deliver the application once and start one window closing at `u+2 s`.
Additional *successfully decoded* same-epoch F copies arriving through
that inclusive boundary can enter the bounded candidate set even though
ordinary F forwarding deduplication returns early. They do not cause
another delivery or immediate ACK. Freeze candidates at `u+2 s`; later
copies do not alter this ACK epoch. A valid R DATA decode still emits its
one immediate path ACK, independent of a later F recovery window.

For each candidate path of `h` hops and carried margin `q != 127`, define
`p_hat(P)=logistic(1.15*q/2)^h`. This is an intentionally crude
model-derived ranking, **not** a calibrated probability: it uses the
minimum observed forward margin for every reverse hop and assumes a
symmetric large-scale link. Select `P1` by maximum `p_hat`, then lower
total ACK path ToA, then lexicographic node IDs. If all q values are
invalid, use the first received path. At the first ACK's actual TX start,
require its locally decremented `budget_q` to cover the complete chosen
reverse path's nominal ACK ToA plus 1 s; otherwise drop and log the
reason. Echo P1's path, q, epoch and refreshed budget. Each ACK relay
rechecks at actual TX start that its own remaining budget covers the
remaining reverse ACK ToA; forwarding remains strict path-indexed.

If `p_hat(P1)<0.90` and a second decoded candidate has a different
predecessor at the destination, choose `P2` by highest `p_hat`, then
lower ACK ToA/lexicographic ID. Queue **at most one** second ACK for its
own path at least 0.5 s after ACK1's physical TX end. It may start only
if ACK1 actually started, the local window is still the same epoch, and
its decremented budget covers its reverse path. The destination cannot
know whether ACK1 reached the source; ACK2 is fully charged even if
redundant. Different first reverse hops do not imply independent
end-to-end failures. No P2 means no second ACK. The threshold, 2-s hold,
0.5-s spacing and four-path capacity are fixed here, not selected after
JFC outcomes.

F relays retain the existing deterministic delay formula and duplicate
suppression, but at actual TX start decrement/refresh budget and drop a
F whose remaining lifetime cannot cover its own ToA. Relay forwarding
does **not** infer destination receipt, cancel an already committed TX,
or use AFS's failed terminal-ACK cancellation rule. Every started F/ACK
counts full wire bytes, ToA, collision exposure and modeled energy.

## Scheduler contract and failure semantics

The current `Simulator.begin_transmission` computes a future physical
`start=max(now,node.tx_available_at)` and marks `PendingSend.committed`
*at request time*. `on_transmit` is post-commit. Therefore a mere
`PendingSend.can_start_at` check cannot implement the above actual-start
packet choice, lifetime update, or intervening-ACK cancellation. A JFC
implementation needs a tested pre-start/defer-and-retry hook: when busy,
leave the handle uncommitted and wake at the radio-free time; immediately
before physical start, run the source/relay/ACK decision and rebuild the
charged packet. Apply that hook identically to policy-isolation controls.
At a shared timestamp, order completed physical RX callbacks, then
protocol timers, then TX-start commit; make a source ACK at exactly D
eligible before deadline retirement. A committed or on-air TX cannot be
retroactively canceled or removed from cost. Tests must cover queue
deferral, same-time ACK/timer ties, capacity overflow, late ACK, stale
generation, duplicate F paths, malformed path/budget, and every byte/ToA
change before any population run.

## Controls, measurements, and no-go rules

Use fresh, disjoint, named seeds; freeze code/design/runner/test hashes
before a mechanical smoke and a prospectively paired development matrix.
Do not open 35001--35040 or 36001--36040. The primary run is the existing
50-node recurring-fading workload with identical topology/application
trace per seed, original 30-s source deadline, 600-s generation, and all
full TXs starting by at least 630 s counted. Use a symmetric later cutoff
to detect delayed spillover. Repeat the unchanged design on random-pair,
load, and PHY-stress cases, then one untouched holdout only after a
predeclared development gate passes.

Policy-isolation arms all carry the same budget/margin bytes, lifetime
checks, scheduler and finite caches:

| Arm | Source | Destination F feedback |
| --- | --- | --- |
| `J0` | JFC | first path, one ACK at 2 s |
| `J1` | JFC | best observed path, one ACK at 2 s |
| `J2` | JFC | best path; conditional second ACK on the same P1, on JFC's exact P2 trigger/time |
| `J3` | JFC | full candidate: P1 then conditional diverse P2 |
| `S0` | fixed R-to-F 8-s guard; keep the route ready after one R miss and quarantine after two consecutive R misses | same J3 feedback |
| `Sg` | same JFC packet, route-state, and feedback contract, but fixed initial-R guard `g` in `{1,2,4,15}` s from actual source R TX start | same J3 feedback |
| `F0` | useful-data F first, no R or payload rescue | first path, one ACK at 2 s |
| `F2` | useful-data F first | first path, unconditional same-path second ACK at the JFC second-ACK spacing |

`J2` versus `J3` uses the same local second-ACK *rule and copy cap*;
the closed-loop policies may observe different copies on an individual
flow. Actual path lengths and airtime may differ and must be reported
rather than called equal-airtime. `J0`/`J1` have exactly one ACK per F and equal
field sizes. `F2` is a stronger, higher-resource simple comparator, not
an equal-airtime arm. Also report the unchanged old SR, immediate/fixed-2-s
DHR, Meshtastic-like and MeshCore-like baselines as context, clearly
separating their packet contracts from isolation arms.

Primary outcomes are source ACK-PDR and destination PDR by each flow's
original 30-s deadline, plus complete-network TX airtime and TX energy
through the bounded horizon. Secondary outcomes: capped source ACK delay,
per-class/epoch TX counts and bytes, collisions, physical ACK-hop failures,
F recovery admissions/starts, source phase transitions, candidate-path
count and changed-path starts, ACK2 triggers/starts, overflow/drop causes,
late spillover, per-source fairness, and route-commit correctness.
Stratify initial-F versus R-to-F flows and one-/multi-hop paths offline;
do not use those global labels in protocol decisions. Analyze paired
per-seed differences and CIs, not pooled-flow pseudo-replication or
per-packet counterfactual claims from divergent closed-loop arms.

Freeze these author-chosen development gates in the runner before opening
the 40-seed development split, and apply the same gates once to a separate
40-seed untouched holdout. Effects are JFC minus comparator, with
seed-paired nominal two-sided 95% intervals; ACK/destination differences
are absolute PDR points and airtime is a per-seed relative difference:

1. J3 versus F0: ACK-PDR lower CI > -0.02, destination-PDR lower CI >
   -0.01, and whole-network airtime upper CI < -5%. J3 versus the
   higher-resource F2 additionally requires ACK-PDR lower CI > -0.02
   and airtime upper CI < -5%.
2. J1 versus J0: ACK-PDR lower CI > 0 and airtime upper CI < +5%.
   This is the one-copy receiver path-selection gate.
3. J3 versus J2: ACK-PDR lower CI > 0 and airtime upper CI < +5%.
   This is the same-trigger, same-copy-cap spatial-diversity gate that
   BAR previously failed. Both arms' actual path-length ToA remains in
   the denominator; equal copies are not necessarily equal airtime.
4. J3 versus S0: ACK-PDR lower CI > 0, destination-PDR lower CI >
   -0.01, and airtime upper CI < +10%. This isolates one-miss source
   quarantine from a fixed two-miss R-to-F controller.
   Against every predeclared `Sg` arm, J3 must also be noninferior in
   ACK-PDR (lower CI > -0.02) and destination PDR (lower CI > -0.01),
   with relative airtime upper CI < +10%. If a shorter fixed guard is
   at least as reliable and no more costly, JFC's 8-s source timer has
   no demonstrated incremental value and cannot be claimed as one.
5. At least 40 actual non-first-path ACK1 starts and 40 actual P2 ACK
   starts, each spanning at least 20 development seeds, with zero
   malformed, over-budget, post-deadline source, or wrong-epoch accepts.

These margins are internal falsification choices, not ICC rules or a
forecast of acceptance. The multiplicity of gates is deliberately
conservative; their nominal individual intervals are not an adjusted
familywise significance claim. A lone gain against immediate ACK, old
SR, or a one-ACK fixed-F arm is not enough. If J3 is indistinguishable
from J2, BAR's negative result remains the parsimonious explanation:
ordinary ACK repetition. If J1 does not improve J0 and J3 does not
improve J2, reject the feedback selector rather than rename a fixed 2-s
delay as JFC. If S0 matches J3 at lower/equal cost, reject the one-miss
source controller. If fields, bounded caches, or the actual-start
scheduler break baseline parity or materially degrade reliability, stop
before holdout. A failed development gate is a no-go; do not retune on
those seeds or promote the paper/PDF/VERSION/GitHub/EDAS.

Even positive simulation gates would not establish originality or radio
transfer. Delayed LoRa ACK, ACK-copy waiting, opportunistic paths,
same-flow ARQ, and route quarantine have prior art; Lee et al. (2020)
and Solé et al. (2026) need full-text rechecking before any novelty claim.
The present radio model uses symmetric large-scale fading and simplified
Meshtastic/MeshCore analogues, not device-firmware comparisons. A strong
ICC systems claim would additionally need PHY/calibration sensitivity or
small real-radio validation. Only after prospective evidence and this
prior-art audit should the ICC manuscript be rewritten around JFC.
