# First-edge ACK signal and path-cost feasibility gate

Date: 2026-10-04. Status: frozen diagnostic design only. This is not a new
MeshEcho algorithm, counterfactual ACK experiment, or ICC result. The
target arm is current `meshecho-dhr-flood-ack-delay` with its fixed 2-s
FLOOD ACK. It does not change protocol packets, forwarding or timers.

## Questions and populations

Two independent questions are whether a destination-decoded alternative
FLOOD path could avoid a failed source-final reverse ACK hop at defensible
cost, and whether the first forward-edge signal predicts that final-hop
outcome well enough to target a same-path ACK repeat. Analyze every scheduled flow,
then the deadline-delivered/source-unACKed FLOOD-ACK stratum, then the
subset whose actual first failed ACK hop terminates at the source.
Separately report direct and multihop original paths, initial F and
R-to-F recovery epochs, destination-adjacent and source-adjacent path
diversity, and ACK attempts that never reach the source-adjacent hop.
These are nested exposures, not causal treatment effects.

## Passive observations and identity

Call the inherited physical `try_receive(tx, receiver)` exactly once and
record its returned `RxInfo` only after it succeeds. Record source-origin
FLOOD first-hop decodes, every successful destination FLOOD decode
(including protocol-ignored duplicates), and actual ACK intended-hop
decode outcomes. Do not consume new RNG draws or ask the protocol for
hidden link quality. Keep full physical TXs and both final RNG states.

Join by `(seed, source, destination, flow_id, request_id=flow_id,
repair_index)` and a unique source-origin FLOOD TX for that epoch. Reject
epochs with multiple source FLOOD TXs or ambiguous causal parents. For a
destination decode, realized path is `P=packet.path+(destination,)`;
require `P[0]=source`, `P[-2]=tx.sender`, no repeated nodes, coherent
epoch/TTL, and `2<=len(P)<=max_hops+1`. A forwarded FLOOD TX must have
one causally earlier successfully decoded parent whose path is its exact
prefix; the relay's actual TX must start after that receive completed.
Capture the pending-send/parent TX relationship without changing the
scheduler so a same-looking duplicate cannot be guessed as the parent.
If any physically decoded destination path in an epoch has missing or
incoherent causal provenance, exclude the whole epoch from exposure and
predictor analysis; retain rejected-decode reasons for audit.

The first-edge observation is the successful `RxInfo` at `P[1]` on the
source's FLOOD TX causally leading to P; for direct P it is the
destination's decode of that TX. Compute
`q=clamp(round(2*(rx.snr_db-required_snr_db(sf))),-126,126)` in 0.5-dB
units. Do not substitute the existing whole-path `min_forward_margin_q`,
destination last-hop SNR, geometry, inferred PRR or later ACK result.
This passive q is **not** currently available at the destination; a
future protocol must carry and charge a separate field.

## Window, budget and prediction

For each epoch, set `u` to its first physical destination FLOOD decode,
not application `delivered_at` (R DATA can deliver first). Admit valid
candidate paths decoded by `u+2 s` inclusive; deduplicate exact paths
by earliest decode. The original path is the one whose decode triggered
the actual destination ACK. A source-final-hop remedy requires
`P_alt[1] != P_first[1]`; also report the weaker
`P_alt[-2] != P_first[-2]` diagnostic separately.

For every path P, reconstruct an ACK with its exact path, marker, and
the proposed one-byte first-edge signal in both candidate and comparator
arms. Charge complete nominal reverse airtime as the sum of the LoRa
packet ToA at every hop. Report separate nested counts for: (A) timely
valid distinct `P[1]`; (B) among A, one alternative ACK airtime no more
than two same-path original ACK copies; (C) among B, `q_alt-q_first>=6`
(3 dB), with both q values known. Report deadline feasibility using the
original `application_enqueue+30 s` separately: nominal earliest ACK1
completion is `u+2 s+C(P)` and any ACK2 includes its spacing and both
full path costs. A two-ACK path pair must also show
`C(P1)+C(P2)` versus `2*C(P_first)`; two packets are not automatically
equal airtime. The fixed same-path repeat comparator waits 0.5 s after
the first **destination** ACK TX ends before requesting its second ACK.
Report both the optimistic schedule-compatible ACK2 finish
`u+2+T_dest(P1)+0.5+C(P2)` and conservative serial bound
`u+2+C(P1)+0.5+C(P2)`; neither is a measured counterfactual. Charge
the complete airtime sum separately from these wall-clock bounds.
Real queueing/collisions and the changed ToA from actually
adding a field can only be established by a later implemented protocol,
not by this passive screen. Sensitivity-charge an extra two-byte lifetime
field without selecting its result post hoc.

Independently of the alternate-path exposure gate, for actual first-path
ACKs with a physical source-adjacent final TX ending by the original
deadline, label whether the source physically decoded that TX, distinct
from protocol ACK acceptance. Report final-hop TXs ending after the
deadline separately and exclude them from channel-quality fitting;
time exhaustion is not a physical link failure. Treat an ACK that never
reached this hop as censored for the final-hop predictor. Report q bins,
direct/multihop paths, collisions, half-duplex, no-interference failures,
and fading-block crossings.
An already-started final-hop TX ending beyond the simulation observation
cutoff still counts as after-deadline, while its physical decode remains
unobserved and excluded from fitting.

Fit only on the exploratory split a monotone logistic score
`p=logistic(b0+b1*q/12)` with `b1>=0`, unpenalized intercept, and unit
L2 penalty on `b1`; use the exploratory empirical success rate as the
constant reference. Do not open predictor validation unless training
has at least 100 unambiguous in-deadline final-hop attempts, 20 successes,
20 failures, and 10 seeds. On untouched validation require the same
support; report pooled Brier against that frozen constant and a
seed-resampled (1000 replicates) AUC 95% lower bound. These pooled
statistics are descriptive, not a substitute for path-type validation.
For each path type, require the same support on both exploratory training
and untouched validation, Brier better than that type's frozen exploratory
success-rate constant, and AUC lower bound
above 0.5. Failure for both path types rejects both a
margin-based path-quality selector and a margin-triggered same-path
repeat claim; no alternative path has an observed ACK outcome. A passing
direct-only predictor permits only a direct-path follow-on experiment;
multihop requires its own independent gate. A pooled-only improvement
authorizes neither path type.

## Frozen split and no-go

Reserve seed 42000 for a mechanical smoke; 42001--42020 for passive
exposure/training; 42101--42120 for predictor validation only after the
smoke, parity and prespecified training/sample-support gate pass. A
path-diversity cost failure does not cancel independent same-path repeat
predictor validation. These ranges are distinct from prior research
and sealed 35001--35040 / 36001--36040. Freeze source, design, test and
config SHA-256 before any seed. For every diagnostic run, exact stock
parity is required for the complete metrics row, all flow/action/TX
records, scheduled traffic hash and both RNG states. Save and hash the
manifest and all artifacts; strictly replay each opened seed. Before opening
the next split, verify artifact hashes and row seed attribution, then
recompute sample support and the exploratory fitted model from saved
predictor rows rather than trusting summary flags.

The alternate-path selector branch is NO-GO unless **both** at least eight
distinct source-final-hop failed flows and at least 20% of that failure
stratum meet A, B, C and nominal original-deadline feasibility. Report
the separate attrition at each condition and do not relax the budget to
rescue a failing screen. Independently, a same-path ACK-repeat selector
requires the held-out q-prediction gate; fixed 2-s one-repeat is a
mandatory control before any benefit claim. Even a GO means only
observable exposure and a plausible signal; full source/feedback behavior still needs a new
contract, simple same-budget controls, prospective development and an
untouched holdout before paper claims.
