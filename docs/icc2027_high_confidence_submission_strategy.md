# MeshEcho: Strategy for a More Competitive ICC Submission

Status: decision plan only, prepared 2026-09-26. No new simulation, algorithm,
manuscript, or PDF is implied by this document. The baseline remains release
2.1.24. The [existing ICC 2027 strengthening plan](icc2027_pre_submission_strengthening_plan.md)
contains the frozen near-term experiment contract and remains authoritative
for that experiment.

Date correction (2026-10-04): the live [ICC 2027 symposium CFP](https://icc2027.ieee-icc.org/authors/call-symposium-papers) lists **16 October
2026** for symposium paper submission. The six-day timeline below was an
older planning snapshot and must not be read as current deadline guidance;
confirm the exact EDAS closing time before any upload.

## What "50%" Can Mean

No editor, experiment, or review simulator can guarantee an individual
paper's acceptance probability. The ICC [2024](https://icc2024.ieee-icc.org/authors/instructions-presenters)
and [2025](https://icc2025.ieee-icc.org/authors/instructions-presenters)
official presenter pages say fewer than 40% of Technical Symposia
submissions were accepted; that
venue-wide fraction is not a probability for MeshEcho. "50%" is an
aspirational target from the authors, not an estimand. The gates below
address known rejection risks; passing them would permit a fresh subjective
assessment, but no evidence maps them to a numerical acceptance chance.

The current five-page draft does not pass those gates. On frozen seeds 51--70,
calibrated MeshEcho improves ACK PDR over its old heuristic by +0.1154
([+0.0307,+0.2001]), but differs from matched-fallback PRR-product by only
+0.0026 ([-0.0055,+0.0107]). The latter two choose the same path in 78/80
both-selected live discoveries and 453/480 isolated first discoveries.
The new score is a familiar max-min modeled hop PRR. Its primary workload
conditions on four graph-qualified recurring pairs per seed, SF7, and
synthetic block fading. These are scientific limits, not formatting issues.

## Readiness Gates

These gates define the evidence needed to reconsider competitiveness;
none guarantees acceptance or establishes a 50% probability.

| Gate | Evidence required | Current status |
| --- | --- | --- |
| G0: Submission integrity | Authors confirm ICCT 2026's actual review/publication status and clear any simultaneous-submission issue. Prepare an ICCT-versus-ICC overlap table for contributions, prose, figures, and data, with citations/disclosures where needed; match PDF/EDAS title and authors. | Author confirmation pending. |
| G1: Distinct contribution | One deployable, testable route-selection or cache-recovery mechanism that is demonstrably different from both PRR-product and repository Smart-CALM/ACK-eviction behavior. A prior-art check must cover existing LoRa opportunistic and multi-SF/airtime routing. Show a causal ablation and actual decision differences; renaming max-min is not enough. | Not met by 2.1.24. |
| G2: Fair, useful gain | Before new holdout data, select one primary claim: reliability gain with bounded cost, **or** lower airtime with prespecified ACK noninferiority. Compare against PRR-product with the *same* discovery, fallback, cache, retry, and candidate budget. For reliability first, use +0.03 absolute ACK PDR as an illustrative point-estimate target, require the seed-paired 95% CI lower bound above zero, and require the paired relative airtime **and** modeled-energy CI upper bounds below a prespecified +10% cost limit. This proves a positive gain, not a gain of at least +0.03; the latter claim needs a CI lower bound above +0.03. For cost first, set the ACK margin `Delta_ACK` and desired airtime saving `delta_cost` before data; require the ACK-difference CI lower bound above `-Delta_ACK` and the relative-airtime-difference CI upper bound below `-delta_cost` (below zero for any demonstrated saving). Set an energy safety limit too. Do not switch claims after results. These are author planning margins, not ICC rules or guarantees; retain adverse baselines. | Current strong-baseline ACK difference is +0.0026 with CI crossing zero and no demonstrated cost benefit. |
| G3: External validity | At least one independent unconditioned, non-saturated traffic stratum and one repeated-pair/cache-use stratum, with enough observed multihop use and comparable route-choice disagreement to test the claimed mechanism. Retain disconnected attempts. Include a second radio/load condition or independently sourced channel evidence where feasible. For a *new method*, fix validation settings before its untouched holdout; the existing P1 was selected after earlier results and is a post-holdout robustness check. | Frozen primary stratum is graph-qualified; P1 is unrun. |
| G4: Auditability and presentation | Fresh development/holdout separation for any new method, per-seed summary CSVs, application-trace hashes, discovery/candidate records, paired intervals, exact control budgets, negative results, reproducible code, and a six-page-or-shorter IEEE PDF. Add packet-level trace logging only if a new claim requires it; the current runner does not save full packet traces. Correct "statistically indistinguishable" to "no demonstrated advantage" when a CI crosses zero. Obtain at least one independent domain review before submission. | Reproducibility is strong, but the contribution and external-validity gates remain open. |

For score-mechanism attribution, compare only identical discovery keys with
identical candidate sets and a selected route from both policies; other
path differences may arise from changed interference. Before P1 outcomes
are inspected, set a diagnostic exposure gate of at least 100 such
both-selected comparisons and 30 different chosen paths over its 20 seeds.
Below either count, report whole-policy outcomes but do not claim the score
mechanism was adequately tested. These counts are planning diagnostics,
not a significance test or an ICC acceptance rule. Even above these counts,
different RREQ SINR inputs can confound attribution: a score-mechanism claim
also needs an isolated first-discovery or fixed-candidate replay comparison
using the same candidate scores for both policies.

Hardware is not an ICC submission requirement. A small radio test or measured
trace can improve confidence in the link model, but it cannot replace G1--G3.
Do not claim that simulator-derived PRR has been empirically calibrated.

## ICC 2027: Six-Day Decision Path

1. **Sep 26--27: integrity and timing.** Authors resolve G0 and confirm the
   exact EDAS closing time. Time the existing P1 command on already exposed
   seed(s), with separate pilot outputs. Freeze the 20-seed, five-policy
   contract before opening seeds 2001--2020.
2. **Sep 27--29: run and audit P1 only if it can finish.** Its 100 policy-seed
   runs test whole-policy behavior under 18-km unconditioned random-per-flow
   traffic. Verify complete rows, paired application traces, denominators,
   static link-budget PRR distribution, actual multihop use, candidate sets,
   comparable chosen-path disagreement, ACK PDR, airtime, and energy.
   Compute the calibrated-minus-matched-PRR+fallback paired interval
   independently.
   Preserve every adverse result. P1 cannot by itself prove a new mechanism
   or isolate stale-cache behavior, because geometry and pair reuse change.
3. **Sep 29: scientific go/no-go.** If the strong-baseline interval crosses
   zero, is adverse, or route-score exposure is sparse, do not claim G2 or
   infer a 50% chance. Either submit the bounded 2.1.24-style comparison
   honestly or postpone a stronger method paper. If P1 is favorable, inspect
   actual route disagreements and cost; it strengthens G3 but still does not
   make the familiar max-min score satisfy G1.
4. **Sep 29--30: independent review and revision.** Ask a domain colleague
   to challenge novelty, comparator fairness, the ICCT overlap table, and
   every result claim; reserve time to fix supported objections.
5. **Sep 30--Oct 1: final paper only from audited data.** State the exact
   scenario, effect and interval, trade-off, prior-work relationship, and
   limits; rebuild and visually check the PDF, then have authors verify
   EDAS metadata and upload. The old Oct 2 date has been superseded on the
   live symposium page by Oct 16; verify EDAS's exact cutoff separately.
   A new figure or polished prose cannot substitute for G1/G2.

There is no responsible plan to *promise* 50% for ICC 2027 from the present
code in six days. Do not launch an unvalidated new algorithm on the frozen
51--70 holdout, tune it on P1, hide an unfavorable flooding result, or
present an unfinished mechanism as established.

## Longer Research Path if 50% Is the Priority

After the 2027 decision, use a separate development cohort and versioned
outputs to investigate **one** mechanism, not a bundle of heuristic knobs.
Two candidate hypotheses need a prior-art screen before implementation:

- **Time-horizon route ranking:** estimate link uncertainty from information
  a real node could obtain, and rank the probability that a route remains
  useful over its cache horizon. A static-channel limit should reduce to a
  standard PRR-product policy. Using the simulator's hidden fading variance
  as an oracle would invalidate a deployment claim.
- **Budgeted stale-route response:** require corroborated evidence across
  ACK history and new link observations before rediscovery or one route
  switch. A missing ACK alone is ambiguous; the existing single-ACK
  eviction control is adverse. Compare with PRR-product granted the same
  detection logic, alternative paths, retry count, and control airtime.

First check the mechanism against existing Smart-CALM, MeshEcho fallback,
and published LoRa routing work. Then write tests, use development seeds
for design, freeze the policy and primary endpoint, and run a new untouched
holdout in multiple traffic/channel strata. Measure ACK PDR, airtime per
successful ACK, energy, route churn, candidate/backup availability, and
actual route-choice divergence. An independent measured trace or small
testbed is useful for model validity if available. If G1--G4 survive an
adversarial review, the main known objections would be reduced and the
submission can be reassessed. No numerical chance follows from these gates.
