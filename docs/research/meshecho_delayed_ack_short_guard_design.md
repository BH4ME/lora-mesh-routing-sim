# Fixed-delay ACK with short source guards (simple controls)

Date: 2026-10-04. Status: prospective source-timer controls, not a new
MeshEcho core or ICC result.

## Motivation and contract

The existing fixed-2-s destination FLOOD ACK arm keeps DHR's 15-s source
R ACK guard. A read-only join of its opened 38001--38020 artifacts found
164 physical R-to-F recovery starts. All 451 accepted initial-R ACKs
returned 0.149--0.637 s after the source's **actual R DATA TX start**;
448/451 returned within 0.5 s and 451/451 within 1 s. Two apparent
13-s delays from application enqueue were source-radio queueing, not
slow reverse ACKs. These observations motivate simple short-guard
controls but do not predict their closed-loop outcomes.

Create distinct `meshecho-dhr-flood-ack-delay-guard{1,2,4,8}` identities.
Each is exactly the existing delayed-ACK, fixed-F-recovery protocol except
its source R no-ACK guard is respectively 1, 2, 4, or 8 s after the
initial R DATA's physical TX start. The unchanged 15-s arm is the anchor.
Here "initial R" means the source's first F/R/D decision was R, not a
later R DATA fallback after an initial D route-discovery timeout. D-to-R
fallback retains the inherited 15-s source ACK timeout and has no DHR
short-guard rescue; the runner must identify the initial decision rather
than infer it from the final transmitted DATA kind.
All retain the same SR initial F/R/D rule, 2-s destination FLOOD ACK,
30-s original per-flow source deadline, DHR bounded rescue admission,
packet formats, queue/collision/energy model, and full TX accounting.
No source may treat missing ACK as a label for forward DATA loss. A guard
may request F under that uncertainty, and an eventual late initial R ACK
may cancel only an uncommitted pending F under the existing DHR contract.

The guard is **not** anchored to application enqueue. An R delayed in the
source queue must still receive the full chosen guard after its own TX
starts. A recovery F must pass the inherited actual-TX-start admission
against the original enqueue+30-s deadline; relays and destination do
not read the simulator-only `Packet.created_at` as a wire deadline.

## Test and exploration gates

Public behavior tests must cover exact physical-start guard timing,
queued initial R, ACK-before-guard suppression, same-time ordering,
deadline/queue rejection of recovery, distinct protocol identities,
no change to the original 15-s arm, and the D-to-R fallback exclusion.
The SR runner must classify all
new variants in DHR ACK/recovery buckets and include their extra physical
TX in full-network airtime and bytes.

Reserve 40000 for one mechanical smoke and 40001--40020 for a paired
*exploratory* five-arm matrix under the existing 50-node recurring-fading
case, 600-s traffic generation, original 30-s deadline, and the same
630-s TX-start cost window plus a symmetric spillover check. Freeze the
current simulator, runner, tests, and this design before smoke. Require
same scheduled trace, exact unchanged-15-s baseline replay relative to
an independently run stock arm on current code, no overwritten artifact,
source/artifact hashes, per-flow reconciliation, and actual guard-to-R-TX
timing checks. Only after smoke audit may exploratory seeds run once.
Keep 35001--35040 and 36001--36040 sealed.

Report seed-paired all-flow 30-s ACK PDR, destination PDR, capped ACK
delay, whole-network airtime/bytes, recovery F starts, late ACKs, and
queue/deadline rejections for each guard against 15 s. These four new
timers are simple controls; inspecting or selecting among them makes the
40xxx cohort development/exploration, never untouched confirmation. A
future source algorithm must beat the strongest applicable short guard,
F-first, R-only, and same-trigger R-repeat controls on a new cohort and
separate holdout. If a short fixed guard explains the putative gain,
do not claim an adaptive timeout algorithm or rewrite the ICC paper on
that basis alone.
