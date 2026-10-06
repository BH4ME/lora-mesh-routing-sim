# MeshEcho-CPR Exposure Contract

Date: 2026-10-06
Status: frozen before the `92100..92109` run; this is a mechanism-exposure
screen, not a performance result, acceptance estimate, or ICC claim.

## Purpose

The previous `92020..92029` screen was auditable but did not expose the CPR
recovery branch: each directed pair appeared only once. This contract changes
the workload to repeated same-pair traffic and temporal block fading so that a
route can be learned before a later routed DATA attempt is lost. It does not
change the CPR controller, PHY, packet format, deadline, or evidence rules.

The old `92020..92029` bundle remains sealed as a no-go for its workload. No
seed from that bundle, the CPR smoke (`92010/92011`), or the DRC cohorts is
reused here.

## Frozen case and arms

The case is exactly runner profile `CASE_PROFILES["exposure"]`:

- `nodes=20`, `area_m=3000`, `duration_s=240`, `rate_per_min=8`;
- unicast Poisson traffic, four seed-specific directed pairs cycled in order;
- `temporal_fading_sigma_db=6`, `temporal_fading_interval_s=60`;
- SF7, 32-byte payload, `max_hops=6`, route TTL 600 s;
- application deadline `30.0 s`, drain cutoff `270.0 s`.

Each seed runs the fixed arm order:

1. `meshecho-cpr`;
2. `meshecho-cpr-nocancel`;
3. `meshecho-drc-no-rescue`;
4. `meshecho-drc`.

The output prefix is
`results/meshecho_cpr_exposure_92100_92109_20261006`.

## Required estimands and integrity gate

Every scheduled unicast remains in the denominator. Report seed-paired
deadline ACK PDR, destination PDR, complete TX airtime/energy, and raw action,
request, TX, RX-attempt, and ACK counts. The evidence-v2 validator must pass
all source, contract, case, trace, topology, radio, pair, request/TX, TX/RX,
ACK, marker, and route-generation joins. Any missing arm, duplicate scope,
incomplete RX ledger, invalid accepted ACK, or hash mismatch invalidates the
bundle.

## Exposure decision gates fixed before execution

The screen may advance to a separate development contract only if all of the
following are true:

1. At least five scheduled flows per seed are present and at least three seeds
   contain two or more flows for the same directed pair.
2. Across the ten CPR runs there are at least five physically started
   `R_INITIAL` actions and at least five physically started `R_REPEAT` actions.
3. At least three physically started `F_RECOVERY` actions occur, and at least
   three seeds contain one CPR recovery decision (`R_REPEAT` or `F_RECOVERY`).
4. At least three seeds show a nonzero CPR-versus-`meshecho-cpr-nocancel`
   difference in physical TX count, complete airtime, or deadline outcome.
5. CPR mean complete TX airtime is not more than 25% above
   `meshecho-drc-no-rescue`. This is a catastrophic-cost stop screen, not a
   superiority test.

Failure of any gate means the exposure workload is not sufficient for CPR
development. It does not authorize tuning the controller or opening a
holdout. A pass only authorizes drafting a new development contract with
fresh seeds and a predeclared reliability/cost gate.

## Publication boundary

This screen cannot update the ICC LaTeX, figures, abstract, conclusions,
`VERSION`, GitHub, or EDAS. Even a passing screen is mechanism evidence only;
all numerical paper claims require a frozen development cohort and an
untouched holdout with independent artifact audits.
