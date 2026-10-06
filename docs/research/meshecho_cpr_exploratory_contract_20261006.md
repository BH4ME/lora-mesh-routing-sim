# MeshEcho-CPR Exploratory Contract

Date: 2026-10-06
Status: frozen before the `92020..92029` run; this is an exploratory
mechanism/integrity screen, not an ICC result or an acceptance estimate.

## Purpose and separation

This stage asks whether the CPR state machine is exposed by the workload and
whether its paired physical evidence is auditable. It must not be used to tune
the deadline, route TTL, FLOOD jitter, safety margin, or acceptance thresholds.
The sealed DRC development cohort and all old SR/DHR/DCB cohorts are excluded.

The physical substrate, case, application trace, topology, radio, pair pool,
deadline, and event ordering are shared within each seed. The treatment is
`meshecho-cpr`; the same-wire controls are `meshecho-cpr-nocancel`,
`meshecho-drc-no-rescue`, and `meshecho-drc`.

## Frozen inputs

- Seeds: exactly `92020..92029`, each run once.
- Case: the `CprCase` defaults in `tools/run_cpr_experiment.py`.
- Deadline: exactly `30.0 s`.
- Arms, in fixed order: `meshecho-cpr`, `meshecho-cpr-nocancel`,
  `meshecho-drc-no-rescue`, `meshecho-drc`.
- Output prefix: `results/meshecho_cpr_exploratory_92020_92029_20261006`.
- The runner must record the evidence-v2 source, contract, case, topology,
  radio, pair-pool, trace, Python, and Git revision identities.

## Primary evidence and denominators

Every scheduled unicast is retained in the deadline denominator, including
state-capacity drops, deadline-infeasible no-starts, cancellations, and late
packets. Report seed-paired deadline ACK PDR, destination PDR, complete TX
airtime, TX energy, request/TX/RX/ACK counts, and CPR action counts from the
raw artifacts. A pooled packet ratio is not an estimand.

## Exploratory gates fixed before execution

1. **Integrity gate:** every arm/seed scope exists exactly once; all paired
   case/trace/topology/radio/pair hashes match; every started request joins one
   physical TX; every TX has exactly one modeled RX attempt per node; every
   accepted ACK joins one successful RX attempt and matching ACK TX; source,
   contract, and artifact hashes validate; no duplicate IDs or unknown scopes
   occur.
2. **Exposure gate:** the CPR arm records at least one physically started
   `R_REPEAT`, at least one physically started `F_RECOVERY`, and at least one
   `cpr-cancel` event across the ten seeds. If any of these are absent, the
   mechanism is not exposed and no CPR development cohort may be opened.
3. **Cross-seed divergence gate:** at least three of ten paired seeds show a
   nonzero CPR-versus-`meshecho-cpr-nocancel` difference in physical TX count,
   complete TX airtime, or deadline ACK/delivery outcome. This is only a
   mechanism exposure condition, not a superiority claim.
4. **Catastrophic-cost screen:** if CPR mean complete TX airtime exceeds the
   `meshecho-drc-no-rescue` mean by more than `+25%`, record a no-go for this
   CPR contract and do not open development. This threshold is deliberately
   looser than the later `+10%` confirmatory ceiling; it is a stop screen, not
   a publishable effect test.

## Decision after the run

The exploratory result can only produce one of three decisions:

- **Mechanism exposed:** all integrity/exposure/divergence/cost conditions
  pass. Draft a separate development contract with fresh seeds and a fixed
  reliability/cost gate; do not use exploratory numbers as ICC claims.
- **Mechanism not exposed:** integrity passes but exposure or divergence fails.
  CPR is not frozen as a population algorithm; design work must change before
  another cohort.
- **Evidence invalid or catastrophic cost:** any integrity failure or the
  cost screen fails. Seal the artifacts as diagnostic/no-go evidence and do
  not tune on them.

No outcome from this stage authorizes a VERSION change, paper rewrite, GitHub
push, EDAS operation, or holdout run.
