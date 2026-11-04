# First-hop receipt successor screen (pre-implementation)

Date: 2026-10-05. Status: passive exposure/cost design frozen before the
45000 smoke; exact source hashes and stage authorization are recorded in
`task_plan.md`. This is **not** a selected MeshEcho algorithm, an efficacy
result, or an ICC paper claim.

## Research question and prior-art boundary

Can an explicitly charged first-hop progress receipt on an initial routed
DATA transmission give the source enough timely information to make a
different same-flow recovery decision under the original 30-s deadline?
The passive screen measures only a necessary opportunity. A source cannot
observe the physical first-hop decode without adding a receipt, and a
missing receipt would conflate first-hop DATA loss with receipt loss.
DSR software ACK, link ARQ, cached backup routes, and conditional retry are
prior art. A later protocol would need to beat receipt-equipped simple
controls, not claim those ingredients as novel. The already-audited
fixed-2-s-ACK short-source-guard comparison did not improve deadline
source-ACK PDR at 1/2/4/8 s against 15 s, and tended toward higher
whole-network airtime. It was an unconditional simple control, not a
test of receipt-conditioned timing, but it raises the bar for the latter.

## Frozen passive population

Use the unchanged `recurring_fading` case and
`meshecho-dhr-flood-ack-delay` (one fixed 2-s FLOOD ACK, fixed-F recovery),
with the stock 30-s application deadline. Seed 45000 is one mechanical
smoke; 45001--45020 are one exploratory pass only after smoke source,
stock-parity, artifact, and strict-replay audits pass. These IDs have not
been used in the repository as of design freeze. No validation or holdout
IDs are assigned yet. In particular, 35001--35040, 36001--36040,
42101--42120, 43101--43120, and 44200/44001--44020/44101--44140 remain
closed. Do not use historical 120xx outcomes to tune this screen.

The observer calls the normal `try_receive` exactly once. For each actual
source-origin initial `R` DATA physical start, capture whether the intended
first hop decoded that DATA by the physical TX end; retain failed attempts
and direct paths. Do not add packets, timers, RNG draws or policy inputs.
The observer must exactly match stock complete metrics, scheduled flows,
actions, full physical TXs, and both RNG states for each seed. Only the
analysis may inspect destination delivery and intended-hop decode.

## Row and cost contract

Join by seed, flow ID, source, destination, first TX ID and initial
`decision=R`. Exclude an initial D-to-R fallback. Require one unmarked
source DATA start on a coherent path and a registered application enqueue.
Report every initial R row; stratify direct versus multihop instead of
silently discarding direct routes. Retain a `censored` first-hop outcome
if its DATA TX ends beyond the 630-s observation cutoff; never equate
missing reception observation with physical failure. For each row save
first-hop decode, initial R source ACK by
`min(actual_R_start+15 s, enqueue+30 s)`, any
source ACK by the original deadline, and destination delivery by that
deadline. The latter three are outcomes, never candidate inputs. Missing
or duplicate joins fail the audit rather than reducing the denominator.

The proposed *nominal* one-hop receipt is an ACK-shaped, no-payload packet
with a 2-node path, 32-bit flow ID, and a charged one-byte receipt marker.
In the current wire model it is 17 bytes and at the case's SF7/BW125/CR1
costs 0.051456 s per transmission. Charge one such TX for **every**
successfully decoded multihop initial R first hop, including flows that
already get an end-to-end ACK. This is a lower bound: actual receipt loss,
queueing, forwarding delay, collisions, and retransmissions require a
later protocol run. Also report an all-multihop-R upper-coverage budget.
Use complete physical network TX airtime through the 630-s drain window
as the denominator, not target-only DATA airtime. Direct-path receipt
overhead and behavior are out of scope for this first candidate and must
be reported separately as a limitation.

For a failed first-hop multihop R with no source ACK by guard, compute a
strictly nominal early-F check at `actual_R_end+1 s` and a nominal fixed-F
check at `actual_R_start+15 s`. Add the fixed destination FLOOD-ACK 2-s
hold to the existing DHR round-trip admission bound, which omits that
delay, and use the same original enqueue+30-s deadline for both.
Report early-only deadline admissions, both-admitted, neither-admitted,
and source-busy-at-trigger separately from physical outcomes. Determine
stock source-radio busy from the complete physical TX timeline at the
early trigger, conservatively counting a TX starting exactly then as busy.
Record decision-to-physical-R-start queue delay, whether the original
flow was already source-ACKed at the early trigger, and any `dhr_state_drop`
active-capacity event for that flow. Stratify residual deadline-unACKed
flows by whether the destination actually received the application by
the deadline. These are counterfactual timing *bounds*, not actual
transmissions or recovered
flows: a new receipt could itself change queueing, active-flow capacity,
interference and ACK arrival. No source decision may use the hidden
first-hop decode in this run.

## Preregistered necessary gate and next experiment

The receipt direction is NO-GO before behavior code if any condition fails:

1. At least 20 distinct multihop initial-R flows with no initial-R source
   ACK by guard have an intended-first-hop decode failure, over at least
   eight of the 20 exploratory seeds and at least 15% of all multihop
   initial-R no-ACK flows.
2. At least ten of those failures across at least five seeds remain without
   any source ACK by the original deadline under stock fixed-F, while a
   nominal early F fits the original deadline, the original flow is still
   source-unACKed at the early trigger, has no `dhr_state_drop`, and the
   source radio is idle there on the stock complete-TX timeline. Separately
   report the narrower early-only admission count, source-busy and
   active-capacity exclusions, and delivered/unACKed versus undelivered
   strata; none estimates actual early-F starts. A pass composed only of
   already delivered flows cannot support a forward-delivery claim.
3. The 17-byte receipt lower-bound airtime on all successfully decoded
   multihop initial-R first hops is at most 10% of stock whole-network
   physical TX airtime, computed per seed then averaged equally by seed.
4. The equal-seed mean optimistic maximum source-ACK PDR gain from the
   gate-2 flows, `mean_s(gate_2_count_s / scheduled_unicast_flows_s)`, is
   at least 0.02. Also report the pooled count ratio. Report the
   corresponding equal-seed and pooled destination-delivery ceilings
   using only gate-2 flows still undelivered by deadline. Neither ceiling
   is an observed gain.

These thresholds are internal feasibility filters, not ICC requirements
or treatment-effect estimates. A pass authorizes only a later frozen
protocol hypothesis and development experiment. That experiment must
physically transmit every receipt and compare against same-wire controls:
fixed early F, fixed 15-s F, same-path R retry, receipt-conditioned early F,
and a DSR-like first-alternate route policy wherever available. Also compare
with receipt-free stock fixed-15-s F, fixed early F and same-path R retry;
otherwise a policy could beat equally burdened controls but lose to a simpler
one. Report all-scheduled-flow deadline source ACK and destination PDR plus complete
network airtime/energy with seed-paired intervals, and retain adverse
scenarios. A merely receipt-conditioned early F is a simple control, not
itself a sufficient new-core contribution. No ICC method/results rewrite,
VERSION change, GitHub publication, or EDAS action follows from this
passive screen.
