# SECON 2027 claim-to-evidence register

Current manuscript status: **complete formal results, bounded interpretation,
independent numeric review passed**. The anonymous manuscript is
`paper/secon2027/main.tex`. This register describes the formal population;
historical development failures below remain preserved and are not included
in formal estimates. ICC source/results are unchanged and supply no formal
SECON data. PDF rendering/metadata/font diagnostics are separately bound in
`paper/secon2027/manuscript_manifest.json` and `paper/secon2027/PDF_QA.md`.

## Frozen identity and complete evidence chain

- Formal plan: `results/secon2027/plans/formal-v1.json`; logical SHA-256
  `5f1a12fe49bf7fc0ea32cc048a3595ed0bd290811f952a47c5a33b0cded2cbb0`.
- Frozen contract SHA-256:
  `0db4fc2e724f441e190693e3f8d37b7912e2d4baa5555515c6f132481f309eff`.
- Formal source snapshot:
  `63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee`,
  tested version **2.1.29**. Later reproduction/presentation releases do
  not relabel the simulator version used in formal runs.
- All 760 keys complete on one attempt: 480 main + 120 controls + 160
  extra deadline runs. Exactly 38 case/arm cells, each with seeds
  **2027100–2027119**, n=20. Default/matched duplicates are never n=40.
- Analysis: `results/secon2027/analysis/formal-v1/analysis.json`, SHA-256
  `8ab85b0313dd99b499947b3c481bd16ab96a0ca0418dae522699de7f659156ef`.
- Analyzer `tools/analyze_secon2027.py`, SHA-256
  `7fd757a780e9725bd3d1992790eaad4a6cc3be7b48f7adcce674a729990eeb54`.
- `runs.csv` SHA-256
  `95e8f0cfded9eedd2c3235e5a2e3f092ff768161bfa3cc24bdb69540b36da425`;
  `summary.csv` SHA-256
  `748639f4a1559dbd1a922d53e93bc2717882e927386d5ee40c6c1e8d73cff639`;
  `paired_effects.csv` SHA-256
  `30323f08da14bef59b8c2e78b52dd27de74f3719a1028e691c07bfdf47c34aa3`;
  `paired_seed_effects.csv` SHA-256
  `7a2198f566b5541c6a50b935f64646b2362c218ce30b5079979792400dbb01e7`.

The chain for every empirical row is:

`paper sentence / label → formal-v2 figure source CSV or named original
CSV selectors below → analysis.json and its output hashes → frozen
plan case/arm/seeds → planned_runs.csv and runs.csv run_key/attempt_path →
completion.json hashes and evidence.manifest.json → raw physical events →
frozen source snapshot/tested VERSION`.

The private release map and Git promotion record are maintained by the
release task in `docs/project-management/secon2027_release_map.md`. The
paper makes no claim about remote publication or submission success.
No identifying local/repository links are inserted in the anonymous PDF.

## Current empirical claims

All intervals are **descriptive, unadjusted 95%**, based on 10,000 paired
seed bootstrap resamples. ACK differences are percentage points; airtime
ratios are exp(mean(log per-seed ratios)), not ratios of pooled means.
The exact selected figure rows, input and figure hashes are recorded in
`paper/secon2027/figures/formal-v2/figure_manifest.json` and four
`*_source.csv` files. No plot re-simulates, resamples, drops seeds, or
replaces undefined values.

| ID | Manuscript claim / location | Exact table or figure selectors | Supported scope |
| --- | --- | --- | --- |
| E1 | Abstract/Introduction/Results: recovery gain in S2 and loss in S3. | `paired_effects.csv`: case_id S2-matched/S3-matched, focus_arm meshecho-cpr-matched, comparator_arm meshecho-cpr-norecovery, metric ack_pdr_deadline / tx_ledger_airtime_s; Fig. components, component_effects_source.csv. | +8.3190 pp [4.9046,11.6338], ratio1.2690[1.2233,1.3180]; −15.9935pp[−19.4114,−12.6433], ratio1.6649[1.5814,1.7439]. The adverse S3 result is central; no uniform improvement. |
| E2 | Results main comparison, Fig. main-results. | `summary.csv`: all six S1/S2/S3-default/matched, four primary arms, ack_pdr_deadline / tx_ledger_airtime_s; paired_effects.csv same cases and baseline comparison_kind. main_results_source.csv retains all48 plotted rows. | CPR ACK81.2978/63.9595/38.9381%; airtime33.7904/40.5512/207.0668s. All matched contrasts in prose use their paired intervals. S1 versus legacy interval includes0; S3 is worse than both route-based comparators. |
| E3 | Table delivery; Results delivery/confirmation divergence. | `summary.csv`: S1/S2/S3-matched, primary arms, delivery_pdr_deadline; ACK rows for comparison. | CPR S3 delivery67.8084% versus ACK38.9381%; no claim that difference alone diagnoses ACK-channel loss. Table includes all12 matched delivery estimates/intervals. |
| E4 | Results repeat and ACK-only controls; Fig. components. | paired_effects.csv: S2/S3-matched, comparator arms meshecho-cpr-norepeat / meshecho-cpr-noackcancel, ACK and airtime; comparison_kind ablation with effective-parameter validation. | Repeat +4.3462pp/+5.4328pp; ACK-cancel airtime ratios.967829/.968195. S3 ACK-cancel confirmation interval crosses0. No-copy-count counterfactual airtime claim. |
| E5 | Results S2 exposure. | `docs/research/secon2027_supervisor_formal_exposure_review.json` and .md/.py; per-run flow/TX/RX and full reverse ACK chain records; full S2 runs.csv remains denominator. | Per regime648flows;85 initial-path crossings→82repeat78recovery24timelyDATA18timelyACK61noDATA;159 actual all-kind fault-edgeTX across87flows;4/25 pre80s initial flows later attempt fault edge. All20seeds exposed. Recovery-associated successes are not the ablation effect. |
| E6 | Results S1/S3 routed operation and pressure. | `secon2027_supervisor_formal_s1_s3_exposure.json`, combined formal_exposure_review.md; source repeat/recovery/cancellation summaries and designated-next-hop RX events. | S1 routed480/cold168, ACK526 four/six hops. S3 N3059,routed2445,cold608,repeat1890,recovery1597; intended collision/half-duplex3228/887 versus227/35. Six source-capacity refusals differ from zero relay evictions. No peak-occupancy/saturation claim. |
| E7 | Fig. robustness, finite deadline/load response. | summary.csv: R-deadline-10-S2-matched / S2-matched / R-deadline-60-S2-matched; four primary arms; robustness_source.csv. Source stage rows, and gates/formal-v1/decision-rejection-reasons.json for99. | CPR ACK57.0127/63.9595/62.7371%; not monotonic. Deadline and drain jointly change,240s generation fixed. Load8/40 is two points, not threshold.99 specifically recovery-deadline-infeasible rejections at10s; stale-route reasons separate. |
| E8 | Fig. latency-cost and Results final paragraph. | summary.csv: S1/S2/S3-matched, timely_ack_latency_p95_s, unfinished_ack_fraction, airtime_per_timely_delivery_s; cost_summary.csv packet_kind×stage; latency_cost_source.csv. | Mean of seed p95CPR4.6516/5.6976/6.6323s, with unfinished18.7022/36.0405/61.0619%. Per-delivery cost1.1053/1.6119/2.0126s. Stacks reconstruct total and include ACKs; no invented component CIs or energy claim. |

`secon2027_supervisor_formal_statistics_review.md/.json` independently
verifies all1,330 summary rows,90 paired effects,1,800 seed effects and
10,000-resample intervals;38cells each n20. It retains74 all-undefined
summary rows, not selected subsets. Its raw-derived boundary covers266
summary rows across seven metrics; remaining diagnostics were checked
from exported per-run values. The separate correctness agent independently
reconstructed 760run×24metrics and checked manuscript values. Those
scopes are distinct and are not described as repeated full raw audits.

The raw review's initial39 accepted-ACK count flags were checker errors:
all ACK rows had been compared with accepted-only manifest counts. A
separately preserved all760 targeted recheck verified23,836accepted and
78rejected ACK records without changing simulation/data. See
`secon2027_supervisor_formal_raw_review.md` and `_verified.json`; do not
claim the corrected full raw checker was rerun. The clean raw-archive
restore is independently recorded in `secon2027_supervisor_formal_archive_review.md/.json`.

## Implementation and measurement claims

These statements bind to the formal snapshot above. Deterministic tests
establish exercised invariants, not hardware validity or empirical gain.

| ID | Claim and paper location | Implementation / deterministic evidence | Boundary |
| --- | --- | --- | --- |
| M1 | All scheduled flows in denominators; Eq.outcomes. | tools/secon2027_experiment.py:audit_bundle, application-trace/flow-set check, analyzer event reconstruction. | Includes source capacity/no-start/deadline misses. |
| M2 | All distinct started physical frames charged; Eq.physical-cost. | lora_mesh_sim.py request/commit/TX export; audit_bundle; additive analyzer ledger. | Full duration charged if start≤cutoff; requests/reservations are not TX. |
| M3 | At most initial/repeat/recovery at original source; Eq.source-bound. | _cpr_start_initial/_repeat/_recovery; test_source_physical_stage_bound_and_recovery_seen_key; test_source_return_is_rejected_even_after_seen_entry_expires. | Excludes ACKs/relays; unique flow identities and honest simulator guards. |
| M4 | Live ACK confirmation distinct from cache update. | _cpr_ack_rejection_reason/_cpr_on_ack_packet; concurrent/stale-valid ACK regressions. | Flow/endpoints/path/stage/start/deadline still checked; no authentication claim. |
| M5 | Old timeout cannot quarantine newer same-path confirmation. | refresh_same_ready_route, _cpr_expire_deadline; revision and equal-timestamp regression tests. | Later unconfirmed flow can still quarantine. |
| M6 | Exact off-path uncommitted relay handle can be ACK-canceled. | _cpr_cancel_relay, ledger matching, committed/uncommitted fixtures, decoded-check versus success test. | Committed future-start send cannot cancel; check denominator≠eligible copies. |
| M7 | Three clean controls change only named switch. | noackcancel capacity-preservation, no-repeat reserved-slot, no-recovery retained-repeat tests; all formal effective-parameter checks. | Historical whole-ledger-off is broader; not used as ACK-only control. |
| M8 | Explicit bounded component state and O(H)/O(nodesK) costs. | meshecho_cpr.py route/flow/ledger/epoch/retired-ring limits; algorithm spec. | Not whole event/evidence/firmware memory or measured occupancy. |
| M9 | Shared exogenous traces per paired seed. | tools/secon2027_scenarios.py; evidence.identities.json; audit_plan. | Different TX times/interference still give different outcomes. |
| M10 | Seed means/paired bootstrap/undefined handling. | tools/analyze_secon2027.py; tests/test_secon_analysis.py; independent final statistics review. | Descriptive unadjusted; no confirmatory significance/noninferiority. |
| M11 | Recovery action enum is not rejection cause. | _cpr_start_recovery; quarantined-generation fixture; formal reason table. | DROP_DEADLINE_INFEASIBLE with stale-route-generation can have sufficient slack and does not immediately erase live flow. |

## Literature, anonymity, and unsupported extensions

The27 used references are the26-entry verified ICC corpus plus the pinned
Meshtastic source; none is invented and no ICC numerical result is reused.
Reading/claim scope is in `icc_citation_audit_20261104.md`, its four
literature source maps, the paper blueprint, and baseline fidelity report.
This is not a new exhaustive novelty/retraction search.

Pinned Meshtastic release commit
`54e0d8d0ab2ff56b3a9ce967e53f79e49af560fb` (v2.7.26.54e0d8d)
NextHopRouter.cpp was refetched through normal-TLS GitHub API and matched
SHA `f73923666cbe55e2404e2fed74ff226e6c918c478557db52c30534b363134dac`.
MeshCore commit `81dbae592ffad40b4212bc0b37e82b38da08f4bc`
(companion-v1.18.0) FAQ matched
`72bf92b9bf78be9520103533c43782e49d5c80ca26e1296e686debaa3e0e1d64`.
The exact URLs appear in references; the narrow supported claims concern
retry/flood fallback and route-learning semantics, not executed firmware.
SECON bibliography SHA is
`b16a95a04468dcdb20749564c218ec130956b8575064bd761c526bf990a6e6d3`;
ICC bibliography is unchanged at
`fed8fa5fc877f98b4ae2a8865c982cc8ca711a94ddd014dc524d195513abc0a5`.

The nonidentifying AI acknowledgment uses the location explicitly required
by the retained IEEE policy (paper_blueprint §8), while omitting human or
funding acknowledgments; PDF_QA records the taskbook wording and policy
resolution. It names Codex and actual manuscript/diagram/quantitative
figure/software assistance. It does not invent human review, funding,
authorship, ethics approval, or submission declarations. The manuscript
claims no first-ever retry-to-flood design, optimality, deadline guarantee,
product superiority, RF validation, energy saving, or accepted submission.
ICC submission/overlap status remains an author-side fact, not inferred.

## Preserved historical development and administrative records

These are historical boundaries, superseded as current paper status by
the complete formal evidence above. Their seeds are not fresh validation.

- P0 smoke-v3:21/21 runs, tested2.1.27 snapshot
  `e8d94c29b3797a55787ee8cc5a60c3d08b4949186f2250581ed36d851ef5b1a2`;
  all48CPR flows initial-flood, so no repeat/recovery performance evidence.
- Pilot v1:72planned,48complete,1failed, remaining unstarted. Plan
  `3729b05d983845dda0ecca1804f1b4307c2e5869402656a5896ec32e91c1232f`,
  snapshot `b212b2f0e56920646581d2e2561247caf284d0815b5260c78cd404c5334fae81`,
  tested2.1.28. Failed key
  `79351a989e26b20a449f1d5522fa2303ad7b9ad2a181ecd5c58bc7c54a1a6577`,
  attempt001, S3-defaultCPRseed2027000, at08:35:46UTC. Missing CprDecision
  import was a code defect, not an infrastructure retry. Failure artifacts
  and partial population remain; no complete-effect claim uses them.
- Corrected pilot v2:72complete on separately frozen plan
  `0c49a69a5c3725c9f72ff2e28ed870d10db1df7eec4319f6397097b84a2c85e7`,
  snapshot `ee890e25030782fc01208ee4ce1f20863c6ade5322ac954ad67ae48b594056a2`,
  161frozen tests. Seeds2027000–2027002 remain development-only.
- Formal contract's stale development wording was clarified **after**
  first start09:06:36UTC and43 completed runs, at09:09:21UTC. All20seeds
  had exposure; no partial performance summary/tuning occurred at the
  pause. The scientific source/760keys/settings/seeds were unchanged.
  See `secon2027_formal_contract_erratum.md`; this is not presented as
  a pre-exposure editorial correction.
- Earlier mechanism summary86/3 counts are DATA-attempt-only. Final paper
  uses all-kind87/4 from the independent exposure review; neither record
  is silently overwritten or mistaken for85initial-path crossings.
- Figure formal-v1 had overlapping log-axis minor tick labels. The purely
  graphical correction is formal-v2; all scientific rows are identical,
  both revisions preserved. The pilot72 figure guard rejected development
  input with exit2 before any formal plot was generated.
- Temporary pre-results PDF was6pages. First complete PDF was10pages and
  rejected for the9page limit. Redundant prose was shortened, with no
  font-size/margin reduction or removal of adverse results; current final
  candidate is9pages. Exact final checks are in PDF_QA and manifest.

## Final manuscript acceptance

The exact nine-page PDF SHA-256 is
`e477617e417a5c089bfeac3f4725e40e54e39e666071a1711c5c0e0f749eb1fd`.
The complete paper sources, final figure manifest and PDF are bound in
`paper/secon2027/manuscript_manifest.json`; all9pages were rendered and
visually inspected, fonts embedded,10ptbody verified, no final unresolved
references or overfull boxes, and author metadata blank. The independent
claims review is `secon2027_final_paper_claims_review.md/.json`.
No submission action was performed.

Final PDFv3 adds explicit915MHz and no duty-cycle/LBT enforcement
statements from the frozen model. It changes no experiment or numeric
claim. The final manifest carries v3source hashes and identifies the
independent quantitative review's unchanged scope despite its v2hashes.
