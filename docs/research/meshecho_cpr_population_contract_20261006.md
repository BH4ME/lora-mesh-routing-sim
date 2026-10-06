# MeshEcho-CPR Development and Holdout Contract

Date: 2026-10-06
Status: frozen after the exposure screen passed; this contract governs fresh
development and untouched holdout artifacts. It is not an acceptance claim.

## Scope and fixed inputs

The confirmatory case is exactly runner profile `CASE_PROFILES["exposure"]`:
20 nodes in a 3000 m square, 240 s generation horizon, 8 Poisson flows/min,
four cyclic directed pairs, 6 dB temporal block fading every 60 s, SF7,
32-byte payloads, `max_hops=6`, route TTL 600 s, and a 30 s application
deadline. Each seed uses the same topology, radio, pair pool, and application
trace for all four arms:

1. `meshecho-cpr` (candidate);
2. `meshecho-cpr-nocancel` (same source state machine, relay-cancel ablation);
3. `meshecho-drc-no-rescue` (no-rescue control);
4. `meshecho-drc` (sealed DRC candidate control).

The development seeds are exactly `92200..92219`. The untouched holdout seeds
are exactly `92300..92319`. Seeds `920xx`, `921xx`, and all prior DRC/SR
cohorts are excluded. The output prefixes are
`results/meshecho_cpr_development_92200_92219_20261006` and
`results/meshecho_cpr_holdout_92300_92319_20261006`.

## Denominators and estimands

Every scheduled unicast remains in the denominator, including state-capacity
drops, canceled/no-start requests, deadline-infeasible decisions, and late
packets. The primary outcomes are seed-level deadline ACK PDR and destination
PDR. Cost is complete network TX airtime and TX energy for packets physically
started by the declared drain cutoff; late spillover is retained and flagged.
Seed-paired differences, not pooled packet ratios, are the uncertainty unit.

## Development gate, fixed before execution

All four arms must pass the evidence-v2 integrity audit, including source,
contract, case, trace, topology, radio, pair, request/TX, TX/RX, ACK, marker,
and route-generation joins. In addition, across the 20 development seeds:

- at least 20 started `R_REPEAT` and at least 10 started `F_RECOVERY` actions;
- no lower nominal two-sided 95% paired t interval for candidate ACK PDR or
  destination PDR is below `-0.05` against either no-cancel or DRC no-rescue;
- candidate mean complete TX airtime is no more than 10% above DRC no-rescue
  and is no more than no-cancel in the point estimate;
- every scheduled-flow denominator and every accepted ACK remains auditable,
  with zero incomplete RX/TX joins and no duplicate physical identifiers.

The interval procedure is fixed: compute the per-seed candidate-minus-control
differences, use the sample standard error and Student-t critical value with
`n-1` degrees of freedom, and report the point estimate and 95% interval. No
seed removal, threshold change, or alternate denominator is allowed after
observing the development results.

If any development condition fails, the holdout stays closed and CPR is a
no-go for this contract. No tuning on holdout is permitted.

## Holdout rule

The holdout may run only after the development manifest, contract hash, source
hashes, exact case, arm order, and development gate report are independently
validated. The holdout uses the identical case and arms on `92300..92319` and
is audited before any manuscript edit. A positive paper claim requires the
same direction of the predeclared reliability/cost gate on holdout; otherwise
the result is reported as inconclusive or negative.

## Publication boundary

Neither development nor holdout artifacts may change `VERSION`, GitHub, EDAS,
or the ICC LaTeX until the artifact audit, statistical recomputation, and PDF
render audit are complete. Smoke and exposure artifacts remain diagnostic and
are not pooled into confirmatory estimates.
