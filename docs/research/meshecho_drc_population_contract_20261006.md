# MeshEcho-DRC Population Contract

Date: 2026-10-06  
Status: frozen for the next development run; this is a research contract, not
an ICC result or an acceptance claim.

## Scope

This contract evaluates the independent `MeshEchoDRC` source controller. It
does not reuse the rejected AFS-integrated design or relabel any old SR/DHR/DCB
numbers. The simulator PHY, channel, forwarding, ACK transport, packet ToA,
energy accounting, and application scheduler are shared infrastructure. The
source action and recovery rule are the treatment; the other DRC arms are
same-wire controls.

## Frozen arms

The arm order is fixed:

1. `meshecho-drc`: deadline-reserved R with at most one same-flow F recovery.
2. `meshecho-drc-no-rescue`: identical initial decision, recovery disabled.
3. `meshecho-drc-fixed-guard`: identical initial decision, fixed 15 s guard.
4. `meshecho-drc-all-f`: one useful initial F whenever its bound fits.
5. `meshecho-drc-r-only`: DRC initial decision with `R_RESERVED` changed to
   route-only and no recovery.

All arms use the same topology, pair pool, application trace, deadline,
packet fields, max hops, route TTL, bounded duplicate table, keyed FLOOD
jitter, and physical-start request hook. A paired contrast is invalid if any
input identity hash differs.

## Frozen case and cohorts

The primary case is a 50-node, 8,250 m square with 600 s application
generation, 4 flows/min, four directed pairs selected from the seed-specific
pair pool, SF7, 32-byte payloads, 4 dB static shadowing, 6 dB block fading
with a 60 s block, `max_hops=6`, and an original 30 s per-flow deadline. The
drain/cost window is `generation_horizon + deadline = 630 s`.

The exploratory seed `61001` is excluded from all confirmatory claims. The
development cohort is exactly `62001..62020`; the untouched holdout is exactly
`63001..63020`. No seed is reused across stages. The runner must save the full
time-plus-application-ordinal trace and topology/radio/pair hashes for every
arm.

## Estimands and denominators

Every scheduled unicast remains in the denominator, including state-capacity
drops and deadline-infeasible no-starts. Primary outcomes are ACK PDR and
destination PDR by the original deadline. Cost is complete network TX
airtime, TX bytes, and modeled TX energy for every packet whose physical start
is at or before 630 s; a packet that starts before the cutoff but ends after it
is retained and separately flagged as spillover. RX energy is reported
separately because it uses a different accounting window in the current
simulator. Seed-paired differences and nominal two-sided 95% intervals are
the uncertainty unit; pooled packet ratios are not primary evidence.

## Development gates, fixed before running

The candidate must be evaluated against every same-wire control. The
development gate is joint:

* no lower 95% paired bound for ACK PDR is below -0.05 versus `all-f` or
  `no-rescue`;
* no lower 95% paired bound for destination PDR is below -0.05 versus any
  control;
* the candidate's mean TX airtime is no more than 10% above `no-rescue` and
  is lower than `all-f` by at least 5% in the point estimate;
* at least 20 `R_RESERVED` starts and at least 10 actual `F_RECOVERY` starts
  occur across the 20 development seeds; every accepted ACK must have valid
  physical provenance;
* all request/TX joins, RX attempts, ACK joins, deadline classes, ToA/energy
  recomputations, paired hashes, and zero-event seed records pass the
  fail-closed artifact audit.

The reserve-caused initial-F branch (a confirmed route exists but the joint
R-plus-recovery bound does not fit) is reported as a mechanism diagnostic. It
is not silently counted as exposed when it is zero. If it is zero, conclusions
about that fallback branch are explicitly inconclusive even if aggregate gates
pass. This change is predeclared because the rejected 2026-10-04 design used
an unexposed AFS/reserve branch and is not this protocol.

If any development gate fails, no positive DRC claim is made and the holdout
remains closed. There is no retuning on holdout data.

## Holdout rule

The holdout can run only after a development manifest, its artifact hash, this
contract hash, the source hashes, and the exact arm/case/seed lists are
validated. Holdout results are descriptive unless the same joint gate passes
without changing the contract. Static-fading, random-pair, load, and PHY
sensitivity cases are secondary and cannot rescue a failed primary gate.

## Event and memory contract

At equal timestamps, physical TX end/RX processing has priority over protocol
timers and application events, and TX requests are committed last. A source
TX must start strictly before its deadline; an ACK received at the exact
deadline is eligible if it has a successful physical RX attempt. The runner
records all queued, canceled, rejected, started, and cutoff-censored requests.

The policy state is bounded at eight route records and eight active flows per
source, a 128-entry/30 s per-node duplicate table, and 128 pending relay
fallback handles per node. Long-lived action, flow, and physical evidence
collections in Python are diagnostic artifacts, not claimed MCU state; the
runner hashes and audits them but they do not alter the controller decision.

## Artifact requirement

Each arm/seed must emit runs, flows, actions, requests, physical TXs, RX
attempts, ACK provenance, paired effects, and a manifest containing source,
contract, case, radio, topology, pair, trace, Python, and Git revision hashes.
The independent reader must be able to recompute all published counts and
reject any missing arm, duplicate join, stale source hash, incomplete RX
ledger, post-cutoff unclassified request, or invalid accepted ACK.
