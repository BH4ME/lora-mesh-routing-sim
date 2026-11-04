# MeshEcho-DHR: deadline- and history-gated same-flow recovery

Date: 2026-10-04. Status: frozen hypothesis before implementation and
population simulation. DHR is a proposed replacement for the ICC paper's
core route-score claim, not a verified gain or a first invention of ARQ.

## Research question and prior-art boundary

Can a source-local decision after an unACKed routed DATA transmission retain
the reliability of a fixed-time flood rescue while spending less complete-
network LoRa airtime, and improve on a fixed-time on-route repeat? The failed
CLAR 8001--8020 cohort motivated forward-DATA recovery: 196 of its 279
unACKed flows were routed DATA that never reached the destination. Those
inspected seeds are algorithm-selection history, not DHR validation.

AODV/DSR route repair, relay ARQ, and LoRa reliable transfers precede this
work (see `meshecho_same_flow_recovery_prior_art_brief.md`). The hypothesis is
the *specific source-observable action rule and deadline/cost trade-off*, not
the generic idea of retransmission or flooding. It must beat matched simple
controls before the paper may claim a benefit.

## Unchanged data plane

All four arms inherit MeshEcho-SR's initial F/R/D decision, route discovery,
cached route, first FLOOD/DATA, PHY, traffic, 15-s source ACK guard, and 30-s
application deadline. Only a flow whose *first* application DATA was sent
on a confirmed R route is eligible for same-flow recovery. F and D-candidate
flows keep SR behavior. Every packet travels through the normal radio queue,
collision, ToA, byte, and energy accounting. The source never reads true PRR,
destination-delivery metrics, another node's state, or future events.

The source retains one `last_ack_at` timestamp per bounded SR destination
state. It records this only on the first source-accepted ACK that validates
the *currently committed* route generation/path for that destination. An old
flow's late ACK may complete its application flow but may not refresh current
route freshness or clear newer route misses. The cached path, the base SR
consecutive-R-miss state,
source radio availability, configured radio/forwarding timing, and the
application enqueue time are the other inputs. This state is per source and
destination, with SR's existing eight-destination bound.

DHR additionally keeps at most eight *active* initial-R flow records per
source. Each contains source/destination, initial path and route generation,
original application deadline, one-rescue action, and actual rescue-start
state. A ninth overlapping R flow still uses ordinary SR delivery but is
ineligible for DHR rescue and is logged as `active-capacity`. Records are
removed on first accepted ACK or at the original 30-s deadline. Historical
per-flow maps in this Python simulator are analysis instrumentation, not a
claim that the complete simulator is a bounded firmware implementation.

## Trigger, admission, and branch

At the *actual start* of an initial source R DATA transmission, schedule the
existing ACK guard for `start + 15 s`. If the source has accepted an ACK at
the guard, do nothing. Otherwise update SR's route-miss state once and
consider one same-flow rescue. A flow may have at most one rescue payload.

All arms use the same admission predicate: a valid stored initial R path;
the source radio is idle at the guard (`tx_available_at <= now`); and a
conservative nominal round-trip bound for **both** possible rescue actions
fits before `flow.created_at + 30 s`. The source estimates the R bound from
the path's hop count and charged marked-DATA/ACK ToA. It estimates the F
bound using configured maximum hops, the worst path-length packet ToA,
and per-hop flood base+jitter+0.35-s weak-link delay. Both include a fixed
1-s scheduling margin. This is an upper bound only in the absence of future
relay queueing and loss, not a delivery guarantee. A `PendingSend.can_start_at`
predicate rechecks ACK status, requires `start == now` at TX request (future
TX reservations cannot later be canceled), and rechecks deadline feasibility.

For admitted flows, DHR selects:

- F rescue if the source has no accepted ACK timestamp for the destination,
  the most recent accepted ACK is at least 120 s old, or the base SR state
  now has at least two consecutive R ACK misses on the confirmed path;
- otherwise one R repeat on the original sent path.

The 120-s freshness constant is fixed before this algorithm's development
run. It is a source-local staleness policy, not a read of the simulator's
current 60-s fading block. Sensitivity to other fading intervals and traffic
patterns is a required robustness check, not a reason to retune this cohort.
No branch uses whether the destination actually got the first DATA packet.

## Wire and route semantics

Initial packets and their ACKs retain the existing wire format. Rescue R
DATA carries charged one-byte `repair_index=1`; rescue F FLOOD carries
`repair_index=2`. Each destination ACK must explicitly echo the received
marker and pay its charged byte; the inherited ACK constructor does not
currently echo this field, so implementation and a packet-level test are
required. Other on-wire identifiers remain the original flow ID,
endpoints, path, TTL, and request ID. Simulator-only timestamps and protocol
names are not extra wire fields. Flood duplicate suppression uses the
existing flow key; the first routed DATA did not consume that FLOOD key.

At the source, an unmarked ACK is valid only for the initial sent route,
marker 1 only for an actually started R repeat on that same path, and marker
2 only for an actually started F rescue with a loop-free realized path from
source to destination inside the hop bound. All require coherent endpoints,
request ID, path index, source pending flow, and the original 30-s deadline.
The first valid in-deadline ACK completes the application flow; duplicates
do not count twice. An initial or repeated R ACK clears the R-miss state only
when its path/flow generation still identifies the current committed route;
it never replaces that route. An F-rescue ACK may replace the cached
route with its *actual* realized DATA path, subject to SR's monotone
`last_commit_flow` rule; a late original ACK must not be misattributed to F.
`mark_delivered` remains once per application flow even if the destination
receives more than one DATA copy, but the destination may ACK each valid
copy. No rescue can schedule another ACK guard or a second rescue.

The source logs guard exposure, admission/rejection reason, selected action,
actual rescue TX start/end and marker, accepted ACK marker, and any route
commit. These logs are diagnostics, not packet-oracle inputs.

## Frozen comparisons and evidence gates

1. `meshecho-dhr`: the above local action rule.
2. `meshecho-dhr-none`: identical initial SR and guard, no same-flow rescue.
3. `meshecho-dhr-repeat`: identical admission and trigger, always one R
   repeat when admitted.
4. `meshecho-dhr-flood`: identical admission and trigger, always one F rescue
   when admitted.

All arms share the same marker semantics, deadline, radio parameters,
source-local admission, application trace, and one-rescue cap. Changing
interference may make later closed-loop decisions diverge; do not interpret
aggregate action differences as a per-packet causal counterfactual.

Use seed 9000 only for non-evaluable mechanics and artifact smoke. Run the
single preregistered development matrix on seeds 9001--9020 in the existing
`recurring_fading` case with 600-s generation, 630-s full-TX-cost start
window, and 30-s deadline. Seeds 10001--10040 are a once-only DHR holdout;
the previously reserved 4001--4040 are not used. Before either matrix,
record design, simulator, scenario, and runner SHA-256 values and verify
that every seed has all four arms with identical case and scheduled traffic
hashes. Any material code/design change after development needs a new named
cohort; do not rerun 9001--9020 as independent proof.

The primary endpoint is all-scheduled-unicast source ACK PDR by the original
30-s deadline, paired by topology seed. The complete-network TX airtime is
the sum of full packet ToA for every TX starting by 630 s; no packet class is
free. For each seed, ACK-PDR difference is DHR minus comparator and relative
airtime is `(DHR airtime - comparator airtime) / comparator airtime`; each
reported estimate is the arithmetic mean of these within-seed differences
with the runner's two-sided paired-t 95% CI, not a ratio of pooled totals.
The author-chosen joint project gate is:

- DHR minus fixed repeat: two-sided nominal 95% paired ACK-PDR lower bound
  `> 0`, point estimate `>= +0.02`, and relative-airtime upper bound `< +10%`;
- DHR minus fixed flood: ACK-PDR lower bound `> -0.02` (noninferiority
  margin of two percentage points) and relative-airtime upper bound `< 0`;
- at least 20 admitted R-miss episodes in at least ten seeds, with at least
  ten actual R rescues and ten actual F rescues across at least five seeds
  each, so an action-choice claim has visible exposure.

Report DHR versus no recovery even if unfavorable. Also report destination
delivery PDR, per-flow capped completion time (`min(ACK delay, 30 s)`, or
30 s when no in-deadline ACK), successful-ACK p95 delay separately,
collision count, complete TX bytes/ToA/energy, control packets, duplicate
destination receptions, and recovery admission/branch counts. The 95%
intervals are nominal, not multiplicity-adjusted; the gate is an internal
research criterion, not an ICC rule or acceptance probability.

Only an unchanged mechanism passing development may open the once-only
holdout. A passing holdout then warrants separately labeled static fading,
random-pair, different fading-interval, and load/PHY sensitivity checks.
If development or holdout fails, report the failure and stop positive DHR
claims; the existing ICC paper/PDF, VERSION, GitHub and submission state
must not be advanced on a smoke run or favorable subset.
