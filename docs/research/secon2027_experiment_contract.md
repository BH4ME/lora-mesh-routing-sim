# SECON 2027 experiment contract — development draft

Registered 2026-11-04 (Asia/Shanghai). Status: **development scope registered; executable source/config/run-key freeze pending**. This document authorizes no formal validation cohort and reports no experimental outcome. The execution plan `secon2027_codex_execution_plan_20261104.md` remains the full delivery scope.

## Research question and stage boundary

Evaluate how deadline-constrained repeat/recovery and pre-commit ACK cancellation affect timely delivery and complete transmission airtime under steady traffic, path disruption with alternatives, and high contention. Four primary behavioral models are MeshEcho-CPR, legacy MeshEcho, Meshtastic-like and MeshCore-like. Default-model and matched-parameter comparisons are distinct regimes; neither is an official firmware benchmark.

Correctness and reproducibility must pass independently of whether CPR improves performance. Keep adverse, null, unreachable and failed cases. Algorithm selection is confined to development. After the once-only formal freeze, evaluation cannot trigger silent tuning or selective replacement of seeds, scenarios, controls or estimands.

## Cohort and run identity

The machine registry is `configs/secon2027/seed_registry.json`, schema `secon2027-seed-registry-v1`. Cohort `secon2027-development-v1` reserves exactly **2027000, 2027001 and 2027002** for development only. Existing seeds 0–999999 are excluded by a conservative namespace fence; the referenced historical inventory distinguishes actual exposure from closed/reserved ranges. At the prospective formal freeze below, validation cohort secon2027-validation-v1 reserves seeds2027100–2027119. They are distinct from all historical/development exposures and are not executed until the frozen gate and plan exist.

Each cohort records purpose, explicit seeds, scenarios, contract, source/config identities, registration and first-run times, artifacts and state. Its seed exposure state is separate from run execution state. A planned run key is `(cohort_id, frozen_config_sha256, arm, seed)`; the immutable configuration must contain scenario and default/matched regime, so different configurations cannot collide. A cryptographic digest of the canonical tuple may name its lock directory. Attempt IDs distinguish failed/retried executions of the same planned key.

Before a process starts, bind contract hash, full source snapshot hash, source version, exact configuration and planned keys; take an exclusive atomic key lock and persist the running/exposed record. The first observed arm exposes the seed but does not block other predeclared arms. Development additions are allowed only as explicit new frozen configurations/keys with retained exposure history. Formal keys may not be added after their outcomes become visible. Neither a `--split holdout` string nor an empty planned-key list grants permission to run.

## Fixed development scope

1. Complete deterministic unit/integration gates for source-return FLOOD suppression; same-endpoint concurrent ACKs; flow/epoch/marker/generation validation; timer ties; cancellation before/after commit; repeat/recovery bounds; complete scheduled denominators; unique TX joins; bounded-ledger overflow; overwrite and lock rejection. Fixtures are correctness checks, not performance evidence.
2. Freeze one P0 mechanical-smoke configuration and its exact planned keys using the registered development seeds. A seed used for smoke remains development when later used in the pilot; it is never described as untouched validation. Record complete events and independent reconstruction before progressing.
3. Freeze the pilot configurations for S1, S2 and S3 before running them. Use all three development seeds, all four primary models, and both default and matched regimes: **3 × 3 × 4 × 2 = 72 pilot runs**, excluding mechanical smoke. If unchanged CPR or other arms produce identical effective default/matched configurations, reuse is allowed only by explicit identical-source/config/seed aliases with one physical run and no relabeling.
4. Measure wall time, peak memory and event/archive bytes per run; audit common environments and mechanism exposure. Pilot is diagnostic. It may support recorded development revisions and at most one evidence-motivated new algorithm direction, but not confirmatory claims or repeated new-seed selection until gains appear.
5. After review, write the formal method/matrix freeze once: exact seeds, scenarios, numerical settings, arms/ablations, sample size, costs, statistics, scenario validity criteria and failure handling. The proposed 20-seed scale is a budget starting point, not an approved or completed experiment.

S1 is steady low/moderate load; report cold/cache hits, completed path hop distribution and unnecessary recovery. S2 uses a shared predeclared link/fault trace and records actual route failures and alternative reachability, repeat/recovery starts, and DATA/ACK losses. Topology and failure analysis cannot be exposed to the source algorithm or used to remove flows. S3 raises offered traffic on the same topology construction and reports contention/collision, queue expiry, ledger eviction and cancellation. Numerical topology, arrivals, horizon/drain, radio and fault settings belong in each frozen pilot configuration; no unspecified setting is permission to run.

## Fairness and ablations

The fidelity and override specification is `secon2027_baseline_fidelity.md`. All arms share topology, traffic arrivals/endpoints, PHY, application deadline and common exogenous channel/fault process. Merely sharing the top-level seed is insufficient. Freeze independently derived topology/traffic/channel/protocol streams or a common environment table and record their hashes; check that protocol event counts do not consume or shift the exogenous sequence.

Charge every physically started DATA, ACK, FLOOD/FALLBACK, RREQ and RREP at the complete modeled wire ToA. Retain different routing and ACK mechanisms where matching would change protocol identity. Do not substitute `*-common-ack` arms under original names. Their use, if selected, is a separate supplemental policy comparison.

Key CPR controls to implement before formal freeze are ACK-only cancellation disabled, repeat disabled, and recovery disabled. Keep source FSM, packet identity and accounting otherwise fixed. Record the exact time/budget treatment when an action is disabled: a skipped repeat must not become an unrecorded immediate recovery advantage. Capacity eviction must be independently controlled or held fixed. The old `meshecho-cpr-nocancel` disables more than ACK overhearing and cannot be called an ACK-only ablation. Add capacity sensitivity only if eviction exposure or a memory claim warrants it.

## Metrics and prospective statistical specification

Every scheduled unicast enters the common per-seed denominator N, including no-start, unreachable, queue-expired and incomplete flows. Report ACK-by-deadline/N and destination-delivery-by-deadline/N separately; also preserve any historical unlimited-delivery metric under a distinct name. A flow completes at most once. Endpoint identity and ACK eligibility must reconcile to physical RX/TX records.

Complete airtime A is the sum of full ToA for all frames physically starting within the fixed generation-plus-drain accounting window. Queued/canceled requests are not physical transmissions; a frame already started cannot be subtracted after ACK arrival. Break cost down by packet kind × stage, or in two independent partitions that each sum to A. `A / timely deliveries` is null/undefined when there are zero timely deliveries, and the zero-success case remains reported. TX-only fixed-current energy is a derived airtime quantity, not measured device energy.

Report successful-flow delay quantiles together with unfinished proportions, actual repeat/recovery starts, requested/successful cancellations, capacity evictions and cache/discovery events. Report actual multi-hop and alternative-path exposure, not only a configured hop limit.

Development summaries use seed-level paired differences and descriptive uncertainty only; N=3 does not justify stable confirmatory intervals. Before formal validation, freeze the primary metric/comparison families and one uncertainty method. Candidate specification: equal-weight per-seed CPR-minus-comparator differences for reliability and log airtime ratios, paired bootstrap with 10,000 resamples and an analysis-only RNG seed recorded in configuration. Bootstrap randomness must never be used as a simulator cohort. Unless multiplicity-adjusted inference is explicitly frozen, intervals are descriptive and must be labeled unadjusted; no confirmatory significance or noninferiority claim is permitted. No noninferiority margin is inherited from the old −5-point/110%-cost contract.

## Failure, audit and artifact rules

Create results under new `results/secon2027/<run_id>/` directories. Preserve flow/action/request/transmission/RX/ACK JSONL, common environment/configuration, manifests, process log and timing/memory measurements. Manifest state becomes completed only after every required file is closed, hashed and audited. Failed attempts remain failed and cannot silently fill a complete matrix. A retry gets a new attempt ID and explicit reason; incomplete keys remain visible in the matrix summary.

An implementation bug invalidates affected experimental evidence and requires a new source/config identity; existing manifests remain immutable. Already exposed seeds remain exposed. A source/config change in development is recorded as development, while a formal-stage change requires ending/invalidation of the affected formal batch and explicit new research boundaries, not an automatic search for favorable confirmation.

An independent audit reconstructs scheduled denominators, deadline classifications, started TX uniqueness/airtime, request–TX–RX–ACK joins, source lifecycle invariants, run completeness, pairing/environment hashes and source hashes. Deterministic replay must use the frozen source version. Preserve source snapshot → tested version → promoted release mapping per task-book §13; metadata-only version promotion does not authorize rerunning formal seeds or rewriting their tested version.

## One-time formal method and matrix freeze

Recorded 2026-11-04 before any formal validation run. The completed replacement pilot, source defect repair, resource evidence and explicit task-book §9 decision are documented in `secon2027_method_decision.md` and `../results/secon2027_development_pilot.md`. Retain the corrected fixed CPR policy; no new algorithm candidate is introduced. Adverse high-load development outcomes motivate measurement and clean controls, not a claim of improvement.

The new matrix is `configs/secon2027/experiment_matrix.json`, experiment `secon-formal-v1`, stage `validation`, cohort `secon2027-validation-v1`, exactly2027100–2027119. It contains760 explicit runs:480 primary (S1/S2/S3 × default/matched × four models ×20seeds),120 key controls (ACK-cancel-off/repeat-off/recovery-off ×S2/S3matched ×20),160 finite robustness runs (S2matched deadline10/60s ×fourmodels ×20). Deadline30s references are the same mainS2matched rows. CPR/ME identical default/matched effective configurations are reported separately and never pooled as n40. No new key, parameter or seed may be added after validation exposure.

All numeric topology/PHY/traffic/fault settings are carried from the audited pilot in the main cases:5×4grid,1000mspacing,±2.5%positionjitter,neighbor20dB/nonneighbor80dB obstruction,20routernodes;network-total Poisson8/8/40flows/min forS1/S2/S3;240s generation;four ordered endpoint pairs5→9,9→5,10→14,14→10;S2extra80dB on(7,8)/(12,13) during80≤t<160s. SF7/BW125kHz/CRindex1,17dBm,32Bapp payload,H6,capture6dB,shadow/fading sigma2dB,60sfadingblocks,10ms keyed reception field. Radio defaults resolved from the saved source include915MHz,explicit header,CRC,eight-symbol preamble,path-loss exponent2.75. The synthetic obstruction grid is not calibrated RF or a uniform5000m-square deployment. No duty-cycle/LBT compliance or official firmware equivalence is claimed.

Main deadline/drain30s gives accounting cutoff270s. Robustness changes both application deadline and drain/cutoff:10s→250s,60s→300s. CPR changes its local admission deadline; the other model controllers retain their original source policies and share each case's measurement deadline/cutoff. Every physically started frame by that cutoff is charged in full, even if its end crosses the cutoff. Cross-deadline airtime changes include changed tail-accounting exposure and are not attributed solely to a timer. No cache-TTL-expiry claim is made because the horizon does not expose normal600s expiry.

### Prospective exposure and interpretation rules

These criteria are fixed before formal outcomes. They are claim gates, not filters, and every scheduled flow and every planned seed remains included regardless of whether they pass.

- S1 multihop/cache exposure: each reported regime must contain at least one CPR routed initial send and one accepted ACK path of at least two hops; report the actual full hop/cold/routed distributions byseed. If absent, withhold cached-multihop claims for that population.
- S2 disruption exposure: each regime must have at least one physically started intended-hop DATA/ACK/RREP transmission on a faulted edge during80≤TXstart<160, and at least one CPR routed-initial carried path intersecting the fault while active. Structural shortest alternatives must remain≤H6 for all four endpoint pairs; this is offline context, not algorithm input or RF success. Show actual repeat/recovery and fault-exposed outcomes. If no realized intersection occurs, label inadequate cached-route disruption exposure; do not discard or replace seeds. A lifetime time-overlap alone is not a fault-edge attempt.
- S3 contention exposure: for each seed, offered S3flowcount must exceed its matchedS1count; each regime must show nonzero intended-hop collision/half-duplex reception opportunities. Report queuewaits,source-state refusal,protocol rejection,relayevictions and cancellations even whenzero. No claim that queues or ledger are saturated without supporting observations. Ledger peak occupancy is unknown.
- A component effect requires actual physical repeat/recovery or successful ACK cancellation in its CPRreference population. If exposure iszero, report the comparison with its zero-exposure limitation; do not invent benefit. Controls preserve every resolved non-componentparameter and denominator. No-repeat retains the nominal observation slot; ACK-onlyoff retains capacity enforcement. No capacity sweep or memory-benefitclaim is selected after zero pilot relayevictions; any formal evictions remain explicitly reported and capacity optimization remains untested.

### Sample size, statistics and resource policy

Twenty seeds is a finite descriptive replication budget, not a powered noninferiority or multiplicity-controlled design. The three-seed pilot is too small to establish a reliable variance/power model; n20 increases the independent seed replication and permits descriptive uncertainty while staying within measured resources. No sequential precision stopping, seed replacement, confirmatory p-value or guaranteed precision is claimed.

Primary endpoints are per-seed timely ACK fraction and full physicalTXairtime. Pair CPR with each primary comparator within eachscenario/regime; three clean controls withinS2/S3matched form separate descriptive families. Report timely destination delivery,undefined-per-deliveryairtime,successful-flowlatency with incompletefraction and mechanismcosts. Use equal-weightseedmeans and paired differences for fractions,meanpairedlogairtimeratios (geometricratios),10,000paired percentilebootstrapresamples,95%unadjusted descriptiveintervals,analysis-onlyseed20271104 with deterministic perplan/casehashing as implemented/documented. Report all intervals without significance/star/noninferiorityclaims. Undefined all-seed estimands remainundefined; do not omit unsuccessfulseeds. Deadline10/30/60 is a descriptive response display of eachfrozen case; no unregistered acrossdeadline inferential contrast. S1/S3 yield only a two-point loadcurve, not a saturation threshold.

Measuredpilot72runs consumed301.925714167s summedserialwall,706194269 rawattemptbytes and360251392B peakworkerRSS. Case/armmeans predict3314.82146249s serial and7511290148.64rawbytes for760runs; controls use the correspondingCPRmean and robustness scales by its accountinghorizon/270. These are estimates, not upperbounds. Fourworkers have measured peakRSS estimate1441005568B on17179869184Bhost memory. Freezeconcurrency4,2×time/storage reserve,18GiBrawbudget and4h timeenvelope. Audit/retrytime can exceed idealfourworker828.705s. On resource/integrity failure, stopnewsubmissions and preserve in-flight outcomes; do not silently shrinkthematrix. Any infrastructureattemptretry isexplicit andbounded; an implementationdefect invalidates affectedbatch and requiresnewrecordedboundaries.

| Field | Frozen record |
| --- | --- |
| Development exposure | P0completed21;pilotv1incomplete48/1/23preserved;pilotv2complete72/72 |
| Corrected tested pilot source | ee890e25030782fc01208ee4ce1f20863c6ade5322ac954ad67ae48b594056a2;tested2.1.28 |
| Pilot plan | 0c49a69a5c3725c9f72ff2e28ed870d10db1df7eec4319f6397097b84a2c85e7 |
| Method choice | Fixed correctedCPR;no newcandidate;methoddecisionrecordbeforeformalexposure |
| Formal specification | experiment_matrix.json;760runs;20freshpredeclaredseeds;new source/contractsnapshotbound by freezeCLI |
| Development gate | results/secon2027/gates/development-method-freeze.json records methodhashes/pilotaudit/measuredcost |
| Statistics | Seedpaired10000bootstrap,unadjusteddescriptive95%;no significance/noninferiorityclaim |
| Hardware/RF | Notperformed;conditionalP2only |
