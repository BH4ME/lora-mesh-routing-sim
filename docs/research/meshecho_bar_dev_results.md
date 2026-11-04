# MeshEcho-BAR frozen development result

Date: 2026-10-04. Decision: **stop the positive alternate-path ACK claim**.
The predeclared three-arm development gate in
`meshecho_bounded_reverse_ack_candidate.md` failed. BAR is a prototype
ACK branch over the fixed-F source scaffold, not a completed source-side
core rewrite or an ICC acceptance estimate.

## Provenance and pairing

The only development run used seeds 16001--16020 and the frozen
`recurring_fading` case: 50 nodes, 600-s application generation, original
30-s per-flow ACK deadlines, and TX starts counted through 630 s. Each
seed has alternate-path BAR, unchanged fixed-F, and same-trigger same-path
BAR on one application trace and case configuration. The manifest has
60 rows and 778 scheduled unicasts per arm. Its six input hashes match
the pre-smoke freeze in `task_plan.md`; independent SHA-256 checks match
all four artifact hashes. The development validator completes source,
artifact, run pairing, and flow reconciliation, then stops at the
expected `BAR development joint primary gate did not pass` error. An
independent count of the unmodified action log matches 248 alternate and
258 same-path actual extra-ACK transmissions, each on a unique seed-flow.
The preliminary seed-16000 smoke was mechanical only, not part of these
intervals.

## Primary comparison

Effects are means of 20 seed-paired differences with the runner's nominal
two-sided 95% paired-t intervals. ACK-PDR uses the original per-flow
deadline; cost is whole-network TX airtime, not only the extra ACK bytes.

| Comparator | Alternate minus comparator ACK-PDR | Relative TX airtime | Gate |
| --- | ---: | ---: | --- |
| Fixed F, no extra ACK | +0.1513 [0.1048, 0.1978] | -3.6% [-9.3%, +2.1%] | Pass this comparison |
| Same-trigger same-path extra ACK | +0.0021 [-0.0292, +0.0334] | +2.3% [-4.7%, +9.4%] | **Fail** |

The second ACK attempt is valuable in this workload: pooled deadline ACKs
are 665/778 for alternate BAR, 663/778 for same-path BAR, and 551/778
for fixed F. But the alternate-first-hop rule has no resolved advantage
over simply repeating the ACK on the first FLOOD path, and its relative
airtime upper bound exceeds the predeclared +5% ceiling. The joint gate
therefore fails despite adequate mechanism exposure: 248 alternate extra
ACK transmissions spanning all 20 development seeds, above the
20-transmission/10-seed minimum.

Destination deliveries are 772/778, 774/778, and 774/778 for alternate,
fixed F, and same-path respectively. Total TX airtime across the 20 runs
is 1166.361, 1215.636, and 1149.639 s in that same order. These pooled
figures are descriptive; the table's paired estimand governs the gate.
Added ACK traffic changes collisions, route commits, and later packets,
so different arms need not have identical per-flow receptions even with
the same scheduled traffic. Physical ACK-hop failure counts cannot by
themselves establish why one untransmitted alternate would have worked.

## Stop and next research boundary

Do not tune BAR on 16001--16020, rerun these seeds as independent evidence,
open the reserved 17001--17040 holdout, or promote the old ICC manuscript,
PDF, VERSION, GitHub branch, or EDAS submission using this result. The
same-path arm suggests time diversity/repetition explains most observed
ACK improvement; that is a finding, not a distinct alternate-path
algorithm contribution. Any successor needs a new device-local mechanism,
same-trigger controls, and fresh prospective seeds. The source-side
R/F/D decision still requires a separate complete contract and test.

This is packet-level simulation only. The inherited FLOOD deduplication
set is unbounded in the simulator, and no MCU memory or field deployment
claim follows from the eight-entry added ACK window.
