# Destination-certified conditional backup: pre-implementation screen

Date: 2026-10-05. Status: **algorithm hypothesis and necessary exposure
screen**, not an implemented protocol, causal estimate, novelty claim, or
ICC result. This successor is distinct from the rejected DBR source-side
backup probe: a previously certified relay would conditionally forward
the *current* routed DATA soon after overhearing it, before the source's
15-s F fallback. It is also distinct from LPR's source-selected weak-edge
PATCH, but must beat LPR-like and plain opportunistic controls.

## Research question and prior-art boundary

Can a destination report one actually decoded two-hop alternative during
a useful-DATA FLOOD ACK, enabling a later one-hop routed DATA packet to
carry a single relay nomination, so the nominated relay forwards only
when it does not locally decode the destination ACK? The objective is to
replace a late, network-wide F rescue with at most one early local DATA
forward while preserving original-deadline source confirmation.

Opportunistic forwarding, overhearing, implicit-ACK suppression, local
bypass and multipath route caching are established (ExOR,
DOI 10.1145/1080091.1080108; LoRa opportunistic routing,
DOI 10.1109/WoWMoM57956.2023.00065; DSR, RFC 4728). LPR and DBR in this
repository are close negative controls. A defensible contribution would
need to be the specific *destination-observed candidate feedback plus
device-local ACK-gated early relay and source-deadline contract*, with a
measured advantage over those simpler mechanisms. No absence of an
identical title or code path proves novelty. Full-text comparison remains
required before manuscript claims.

Mugerwa et al., *Implicit Overhearing Node-Based Multi-Hop Communication
Scheme in IoT LoRa Networks* (Sensors 2023, DOI 10.3390/s23083874), already
use LoRa overhearing relays and suppress pending retransmissions when a
destination ACK is overheard. ACK-gated forwarding alone is therefore not
a novelty claim. An IOMC-like same-information/same-budget control is
required only as an *equivalence check* if it receives the same nominated
relay, timer and ACK rule: that policy is behaviorally identical to this
candidate. The useful IOMC-style comparator chooses its relay from
current-packet overhearing/local information while receiving the same
packet-byte and time budget. The feedback-selection ablation instead keeps
the charged fields but ignores the historical destination certification.
Check the exact routing and ACK contracts before claiming a distinction.

## Provisional device contract to falsify

- The destination may remember at most four distinct, physically decoded
  FLOOD paths during a bounded 2-s local window, with at most eight active
  windows. It sends one charged ACK containing the first valid path and,
  only if observed, one two-hop alternative `(source, relay, destination)`
  with a distinct first hop. The ACK must carry the relay ID and an epoch
  binding; the source cannot infer an alternative from hidden simulator
  traces. A source stores at most eight ACK-confirmed primary/backup
  records with original ACK time and route generation.
- When a source has a current one-hop confirmed primary and eligible
  two-hop backup from that same generation, it sends a routed DATA with
  a charged backup-relay ID/epoch field. It may retain the existing
  original-deadline F recovery as a safety arm, but that fixed 15-s rule
  is a comparator, not the novel part. A source never treats nomination
  or a relay TX as an ACK or route commit.
- Only the nominated relay that physically decodes this DATA may buffer
  it. It uses an at-most-2-s local timer, suppressing its pending one-shot
  backup DATA if it physically decodes a valid destination ACK for this
  flow before the actual radio start. Off-path ACK reception must be a
  real PHY decode, not a destination-delivery flag. A forwarded backup
  DATA carries an explicit marker and `(source, relay, destination)` path.
  The source accepts its reverse ACK only when the flow identity, nominated
  relay, earlier F epoch, marker, actual backup TX start and reverse path
  all match the active record before the original deadline. The source cannot
  observe a remote relay TX start, so this early screening clause is
  superseded by the implementable local validation in
  `meshecho_dcb_protocol_contract.md`; independent instrumentation must check
  physical TX provenance. A backup TX
  alone cannot commit a route or replace a newer generation. No relay reads
  source ACK status, destination delivery metrics, global queues, true PRR, or the remote
  source deadline. If it transmits, the destination may deliver once and
  return an ACK on the actually traversed path. Every duplicate, control
  byte, queue wait, collision and full-network TX airtime is charged.

This contract is provisional: packet-byte layout, relay priority if more
than one candidate is ever allowed, expiry, and ACK-route validation must
be finalized and public-behavior tested before any population trial.
The passive cost screen uses at least two charged bytes for a relay ID in
the F ACK (that ACK's existing 32-bit flow ID can bind its own epoch) and
at least six charged bytes in each nominated R DATA copy (16-bit relay ID
plus the earlier F epoch's 32-bit flow ID). The existing `request_id` is
not charged on DATA or ACK in the simulator's current wire model, so it
cannot silently stand in for this new field. Any final presence marker,
generation or authentication bytes must increase the modeled packet size.
The backup relay's DATA and every hop of its reverse ACK must each carry
at least the one-byte explicit backup marker required by the acceptance
rule. If the eventual packet contract needs the F epoch on these packets
instead of binding it through the active source flow record, its added
bytes must be charged too.
At SF7/BW125/CR4/5 in the current model, a direct 16-byte ACK remains
0.051456 s after the minimum two bytes (18 bytes), whereas direct R DATA
increases from 48 bytes/0.097536 s to 54 bytes/0.102656 s with six bytes.
Actual cost must use the complete path-specific packet size at every TX;
LoRa symbol steps mean added bytes do not always add ToA.

## Existing exploratory exposure, not treatment evidence

The already opened 42001--42020 fixed-2-s-ACK archive has 131 one-hop
initial R DATA sends. A saved-row join to the **latest earlier accepted
source route commit** finds 125 whose committing F epoch had a physically
decoded two-hop alternative within its destination window. Of those 125,
53 did not get an accepted initial R ACK by its physical-start + 15-s
guard; 47 were first delivered by the later F rescue. These are offline
candidate paths not present in the original ACK bytes, so the source and
relay did **not** know them in the tested protocol. The stock delayed-ACK
implementation constructs the ACK at first destination decode and only
delays its transmission; it does not rebuild the ACK at the 2-s window
close. A successor must explicitly change that construction point, with
changed byte/queue/interference effects measured causally. The
45001--45020 cohort separately had 113 one-hop initial R sends, 53 without
an initial accepted R ACK; 47 were first delivered by later F. Among those 47 F
deliveries, ACK paths had 11 direct, 34 two-hop and two longer paths.
These cohorts cannot be combined flow by flow or interpreted as a
counterfactual early-backup success estimate.

A separate read-only 42xxx stock-row check found that all 131 one-hop
initial R flows include only eight without a source ACK by deadline and
one without destination delivery. Fifty-seven had a later F recovery;
49 of those were source-ACKed, and their complete marked-F physical TXs
used 116.945152 s in 999.575552 s total network TX airtime across the
20 seeds. This is an intentionally broad superset before matching a
destination-certified candidate and before subtracting nomination,
relay, ACK or redundant-TX costs. It does not estimate achievable savings.
It makes this candidate a *cost-first, source-ACK-noninferior* hypothesis,
not a plausible 0.02 ACK-PDR uplift claim in the inspected workload.

An older three-seed first-hop witness observer found 14 direct intended-
receiver decode failures, and all 14 had at least one off-path relay
decode of the DATA. But the *locally nominated* candidate from older
history decoded in only 0/5/8 failed hops under 30/120/300-s windows.
The new destination-carried candidate could change that exposure; the
older figures do not prove it will. Flood-path alternatives may be stale
by a later R send, and source ACK of the F carrying the candidate may
itself be lost.

## Necessary passive gate before behavior code

Reserve seed 46000 for one mechanical smoke and exactly 46001--46020 for
one prospective passive exploration; neither range has been opened by
this note. Do not use sealed 35001--35040/36001--36040 or any prior 42xxx
or 45xxx result as independent validation. Use the frozen recurring-fading
case and fixed-2-s FLOOD ACK, 30-s original source deadline, 600-s
application generation and 630-s TX-start accounting window.

Use a separately frozen, non-holdout recurring-fading diagnostic. Observe
only successful physical receptions after the simulator's normal one
decode attempt; recording must leave stock flows, actions, complete TX,
and both RNG streams exactly unchanged. For every one-hop initial R DATA
whose source has a latest *accepted* direct-path F commit with a two-hop
alternative, select the shortest then earliest-decoded then lowest-ID
relay from that F window, without looking at the future R outcome. Audit
source-route generation and the optional backup age at R enqueue. Report
separately no age limit, <=120 s, and <=60 s; do not choose the best after
seeing outcomes.

For each nominated relay, record whether it physically decoded the
current initial DATA; whether the intended destination decoded; whether
the relay locally decoded the destination's actual ACK before a nominal
0.5-s/2-s pending-forward window; both original-deadline and initial-R-
physical-start-plus-15-s F-guard slack; and the
collision-free modeled relay-to-destination PRR at the candidate time.
The last PRR is an **offline upper-bound proxy**, not a local decision or
counterfactual reception. Count every nominated flow, including success
cases where a relay TX would be redundant, and estimate minimum field
bytes/ToA over all forward and reverse hops. Keep direct and multihop R
outcomes, final source ACK and destination delivery separate.

Predeclared necessary exposure for a prototype: across at least ten
independent seeds, at least 20 one-hop R flows with an accepted <=120-s
backup must show *both* intended-destination decode failure and nominated-
relay decode, and at least 16 of those must have collision-free modeled
relay-to-destination PRR >=0.5 with enough nominal time for one relay DATA
and reverse ACK before the original 30-s deadline. These are author-chosen
feasibility thresholds, not ICC rules.

Keep two possible benefits separate. The optimistic all-scheduled-flow
**source-ACK gain ceiling** counts only qualifying flows that the stock
fixed-F policy did *not* source-ACK by their original deadline. A flow
already ACKed by stock F can have earlier confirmation or lower cost, but
cannot be counted as an additional ACK success. Separately, the optimistic
**cost-substitution potential** includes only qualifying flows that stock
F source-ACKed by deadline and whose post-R-guard F transmissions could in
principle be canceled by an earlier relay ACK. Its numerator is their
observed complete F-recovery TX airtime less the minimum relay DATA and
reverse-ACK airtime, the minimum charged backup fields across *all* flows,
and the minimum redundant relay transmissions on successful primaries whose
nominated relay did not hear the destination ACK. Divide by each seed's
complete-network TX airtime and average equally across seeds. This is an
optimistic, stock-trace opportunity calculation, not a counterfactual
airtime saving; if any required byte cost cannot be bounded, the cost
branch is unassessable, not zero-cost.
Charge the two-hop reverse ACK for each flow whose F airtime is credited as
replaced. Do not assume that every other nominal relay start succeeds and
generates an ACK; doing so would turn this necessary optimistic ceiling into
an overly pessimistic, different quantity. Report any all-start-ACK charge
separately as sensitivity, not as the primary gate.

This candidate's predeclared primary direction is cost, not an either-or
endpoint choice: after exposure passes, proceed to behavior code only if
the cost-substitution potential is >=0.05. Use the 2-s relay timer for the
primary gate and report 0.5 s only as a prespecified sensitivity, not a
post-hoc rescue. Credit a stock flow's complete F-recovery TX airtime only
when the candidate's queue-free nominal reverse ACK would reach the source
before the initial R physical-start + 15-s F guard. This is still an
optimistic opportunity: the real candidate must account for changed queueing,
interference, ACK timing, and cancellation at actual radio start. A reverse
ACK that merely arrives before the 30-s application deadline cannot erase
F transmissions already started at the guard. Report the corrected ACK-gain
ceiling, but do not use it to rescue a failed cost gate after looking at
46xxx outcomes. The later causal trial must test source-ACK noninferiority
alongside whole-network airtime reduction on fresh paired runs. Failing
exposure or the cost gate means **NO-GO for this candidate**. Passing only permits a
complete packet/state contract and fresh same-trace development, not a
performance or novelty claim. Report all successful-primary nominations,
including those whose relay would not overhear ACK and would add a
redundant TX. This correction was made before any 46xxx seed was opened;
the previously inspected 42xxx/45xxx traces remain hypothesis history.
The 0.05 screen threshold was selected with 42xxx already inspected; a
passing 46xxx screen is exploratory permission to prototype, never
independent confirmation.

The subsequent causal matrix, if permitted, must include fixed-2-s SR/DHR,
same-byte but no-forward backup field, unconditional early forwarding by
the *same* nominated relay, a same-byte local/overheard relay-selection
ablation, same-time source R/F and R-F, fixed
two-hop F, LPR-like local patch, an IOMC-like overhearing control, and the
conditional-
relay candidate, with original-deadline source ACK,
destination delivery, capped delay, complete network airtime/energy,
queueing, bytes and state. Preserve untouched full-core development and
holdout cohorts; inspected 12xxx/42xxx/45xxx data are hypothesis history.
An informed arm with the identical nominee, timer and ACK gate is a parity
check, not a target for superiority. A positive physical screen remains
GO-to-prototype only and NO-GO-to-ICC-claim until causal comparisons,
near-prior-art full-method review and an untouched holdout are complete.
Because all eligible reported backups here have two hops, "shortest then
earliest-decoded" reduces to the first decoded eligible alternative. A
first-alternative arm with that same eligibility is another identity
check, not independent evidence of route-selection value.
