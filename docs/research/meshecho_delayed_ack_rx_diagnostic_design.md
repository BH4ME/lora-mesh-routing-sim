# Fixed-delay ACK receive diagnostic (pre-run contract)

Date: 2026-10-04. Status: prospective passive diagnostic, not a new
MeshEcho protocol, performance result, or ICC claim.

## Question and population

Under the existing `meshecho-dhr-flood-ack-delay` policy, why do
destination-emitted ACKs fail to become source-confirmed by the original
30-s per-flow deadline? In particular, does the source physically decode
valid same-flow ACKs addressed to an earlier path index but reject them
solely because `ack_next_hop_matches` is false? The already opened 38xxx
artifacts establish 42 delivered-but-unACKed FLOOD cases, but they do not
contain per-receiver physical outcomes or SNR. They cannot answer this
question retrospectively.

The diagnostic must observe every existing ACK transmission's expected
next-hop receive attempt and the source's receive attempt if distinct from
that next hop. The source is the `final_dst` in the ACK packet. For each
attempt, save seed, flow, ACK TX ID, sender, receiver, path/index, TX start
and end, actual physical-decode result, signal power, overlapping
interferer powers, SINR/PRR model values when applicable, and one of:
`half_duplex`, `capture_collision`, `probabilistic_with_interference`,
`probabilistic_no_interference`, or `decoded`. A decoded off-index ACK is
only a *candidate*: separately verify flow identity, destination origin,
repair marker, path continuity, and in-deadline source arrival. A source
ACK already accepted on the normal path is not a rescue opportunity.

The recorder must not call the PHY receive function twice, draw extra RNG,
schedule/cancel TX, alter packets, or change protocol state. Classification
uses the same existing transmission overlap and power model, after the
one ordinary receive attempt. Do not infer a counterfactual reverse path
or hardware performance from symmetric simulated link powers.

## Frozen execution and integrity gates

- Use the existing `recurring_fading` case, unchanged protocol/radio/traffic,
  independent random streams, 600-s generation, original 30-s application
  deadline, and 630-s primary drain.
- Reserve seed 39000 for one mechanical smoke. After the code and focused
  tests pass, freeze source/test/design SHA-256 values. Run the instrumented
  and stock fixed-delay policy on seed 39000. Require identical scheduled
  trace hash, full metrics row, per-flow outcomes, protocol action list,
  and complete TX trace including packet fields and timestamps. Resolve
  any discrepancy before exploratory seeds.
- If smoke and independent artifact checks pass, run seeds 39001--39020
  once as a passive exploration. Preserve 35001--35040 and 36001--36040
  sealed. Save JSONL/CSV plus a manifest with source hashes, artifact
  hashes, cohort, configuration, parity status, and per-seed denominators.
  Replaying a seed is an integrity check, never an independent observation.
- Report all scheduled-flow deadline source ACK and destination delivery,
  then stratify delivered-but-unACKed cases by initial-F versus R-to-F,
  direct versus multihop ACK, expected-hop first failure class, actual
  final-hop TX, and in-deadline off-index source PHY decode. Maintain the
  all-flow denominator; do not condition a performance comparison on a
  post-treatment receipt.

## Decision gate

The zero-extra-TX off-index acceptance branch is worth a prospective
protocol trial only if at least four distinct deadline-delivered,
source-unACKed FLOOD flows, and at least 10% of that stratum, have a
physically decoded, identity-valid, in-deadline off-index ACK at the
source. Both thresholds are necessary, not sufficient: the source must
also safely accept the packet without a route or repair-marker error, and
an implemented branch must beat an unchanged fixed-2-s control on fresh
paired development and untouched holdout seeds. If either diagnostic
threshold fails, stop this branch as the full-core mechanism. In either
case, the full requested rewrite still needs a source-side decision and
recovery contract and a same-time/same-budget ACK-repeat control.

This exposure screen does not justify writing a positive ICC mechanism
claim or changing the current manuscript, PDF, VERSION, GitHub, or EDAS.
