# ICC 2027 MeshEcho Pre-submission Strengthening Plan

Status: plan only, prepared 2026-09-26. This planning phase does not run a
simulation or revise the manuscript. Baseline is `version/v2` at
`bc6b50269fdde6c5702fbaf94509f0e312f637a3`, repository version 2.1.24.
The reviewed five-page PDF is
[`paper/icc2027/icc2027_lora_mesh.pdf`](../paper/icc2027/icc2027_lora_mesh.pdf).

## Decision and Evidence Boundary

The paper fits the [ICC 2027 IoT & Sensor Networks symposium](https://icc2027.ieee-icc.org/sites/default/files/downloads/2026-06/icc-2027-cfp_iotsn_0.pdf)
and the [initial submission format](https://icc2027.ieee-icc.org/submission-guidelines):
English, IEEE conference 10-point, PDF via EDAS, no more than six printed
pages. The [symposium deadline](https://icc2027.ieee-icc.org/authors/call-symposium-papers)
is 2026-10-02; the submitting author must check the exact EDAS closing time.
There is no universal hardware-testbed gate in those instructions.

Scientific risk is higher than format risk. The frozen 51--70 fading holdout
shows calibrated minus old MeshEcho ACK PDR +0.1154 (seed-paired 95% CI
[+0.0307,+0.2001]), at +2.467 s airtime and +5.09 J modeled energy per
run. Calibrated minus matched-fallback PRR-product is +0.0026
[-0.0055,+0.0107]. Static-channel and isolated equal-candidate ACK
intervals also include zero. The score is a familiar max-min modeled hop
PRR; the model uses successful-RREQ SINR, not independently calibrated radio
measurements. The main result conditions on four graph-qualified recurring
pairs per seed, SF7, and synthetic 6-dB/60-s block fading. The historical
2.1.23 unconditioned random-pair run evaluated only the old score and found
managed flooding ahead of it; it cannot validate the calibrated policy.

The objective before the deadline is to test this external-validity boundary
once with a fresh, explicitly specified comparison, then make the final
claim match the result. More tables or a figure cannot by themselves solve
the novelty concern.

The frozen 8.25-km case has only 0.158 of direct node-pair links below 0.99
modeled PRR, so an unconditioned sample at the same geometry is likely to
be dominated by easy direct links. The earlier 18-km random-pair case has
0.641 below 0.99. Use that previously documented non-saturated geometry
for the new independent-seed stress stratum, while keeping the current
paper's unicast load, fading, and matched relay timing. This choice was
made after seeing old results and is not a new pristine preregistration.

## Non-negotiable Controls

1. Preserve the 41--50 development data and one-time 51--70 holdout as
   immutable history. Do not rerun, overwrite, re-label, or tune against
   them. The new scenario is a post-holdout, independent-seed robustness
   check, not the original prespecified holdout.
2. Freeze the current route score, fallback rule, simulator, command,
   primary contrast, and interpretation gates before the new seeds run.
   Record the exact code commit/hash and raw-output prefix. Any bug fix
   after opening the new cohort invalidates a claim that it is untouched;
   disclose the fix and use a further unused cohort for confirmation.
3. Use unique paths and check that they do not exist before running. Both
   the generic probe and generalization runner write their output paths on
   execution; neither is a safe overwrite-proof archive.
4. Pair comparisons by topology seed, not by packet. Keep scheduled and
   observed unicast denominators, shared application-trace hashes, direct
   PRR quantiles, discovery success, cached-route hop distributions,
   candidate-set agreement, ACK PDR, destination PDR, airtime, and modeled
   energy. Do not discard disconnected random pairs or apply the
   graph-qualified pair gate to the random-pair denominator.
5. Do not call a confidence interval crossing zero evidence of equivalence.
   Do not call model-predicted PRR a measured radio PRR. Hardware is useful
   future validation, not a six-day submission prerequisite.

## Priority and Calendar

| Priority / due | Action | Compute / work cost | Completion gate |
| --- | --- | --- | --- |
| P0, Sep 26--27 | Authors verify ICCT 2026's actual submission/publication status, prior-text/data overlap, final title/name/order/affiliation, funding, conflicts, and AI-use statement. Log into the [IoT track in EDAS](https://edas.info/N35508) and confirm its exact closing time. | Author decisions; no simulation. | No prohibited concurrent submission or unexplained reuse; final EDAS metadata can match PDF exactly. |
| P1, Sep 26--29 | Freeze and run the non-saturated, unconditioned random-pair stress check below on unused seeds 2001--2020. | 20 seeds x 5 policies = 100 full policy-seed runs, plus 5 runs for a separate timing pilot. Actual wall time has not been measured; time the pilot before reserving compute. | Complete raw CSV/report, independent paired audit, and all adverse results retained. |
| P2, Sep 29--30 | Revise the claim, results, limits, and figure from audited data. Use one paired-difference/95% CI plot if it improves comprehension; do not use the stale 2.1.23 bar figure as 2.1.24 evidence. | No new simulation; analysis, LaTeX, and visual QA. | Strong-baseline wording passes the decision rules below; PDF stays within the user's five-page target if feasible and always within ICC's six-page ceiling. |
| P3, only if P1 is audited early and the paper schedule is secure | A separately named unconditioned repeated-pair check would address route-cache generalization but needs a small runner extension and tests. SF8 or 100-node deep cases are lower priority. | At least 20 x 4 = 80 more policy-seed runs per four-policy stratum, plus implementation/test time for repeated-pair sampling. A historical 100-node case had about 2.7x the receiver-attempt count of the random-pair case, not a measured wall-time multiplier. | Freeze the new sampling and seeds before outcome inspection; retain all random pairs in denominators. Report actual hop/candidate exposure and do not claim four/five-hop evidence if only three-hop paths occur. |
| Submission, Oct 1 internal target | Full paper/build/data audit and EDAS upload by the authors. Keep Oct 2 as buffer, not the internal start date. | Formatting, review, and author upload. | Final PDF, EDAS title/all authors, originality, and page count verified; upload confirmation retained. |

If the timing pilot predicts that P1 cannot finish with an independent audit
before Sep 30, skip P3. If P1 itself cannot finish cleanly, submit only the
audited 2.1.24 result with its current bounded claim; do not insert partial
new data or silently shrink the cohort after seeing results.

## P1 Experimental Contract

Question: how does the frozen calibrated **whole policy** compare with a
matched-fallback PRR-product policy under non-saturated, unconditioned,
mostly one-shot source-destination traffic? This stratum keeps the current
paper's 50 nodes, 600 s, SF7, 4 unicast flows/min, 4-dB static shadowing,
6-dB/60-s fading, 2-s candidate window, 600-s route TTL, no adaptive
timeout retry, and matched RREQ timing, but uses an 18-km square and samples
a new random source-destination pair per flow instead of four repeated
graph-qualified pairs. It changes both geometry and cache-reuse exposure.
It does **not** isolate pair-selection bias or stale-route scoring; the
random schedule also consumes different RNG draws. Do not pair its events
with the 51--70 traces or call it a one-factor causal ablation.

- Fresh cohort: seeds 2001--2020, checked against existing result artifacts
  at planning time. No seed replacement after inspecting results.
- Policies: old MeshEcho, calibrated MeshEcho, matched-fallback PRR-product,
  ETX, and managed flooding. The first three address the core score and
  recovery comparison; ETX is a standard metric and flooding exposes a
  different reliability/airtime operating point.
- Primary contrast: calibrated MeshEcho minus matched-fallback PRR-product
  on seed-level ACK PDR. Secondary exploratory contrasts: calibrated minus
  old MeshEcho and calibrated minus flooding. Destination PDR, airtime, modeled energy,
  route-discovery success, and actual multi-hop use are secondary outcomes.
- Inference: two-sided 95% Student-t CI over 20 seed-level paired
  differences, with a complete seed-by-policy matrix. Do not infer on all
  packets as independent replicates. If seed-level traffic counts differ,
  retain per-seed PDR denominators and report pooled counts descriptively.
- Interpretation: a detected strong-baseline ACK advantage requires the
  calibrated-minus-matched-PRR CI lower bound above zero. An exploratory
  old-score contrast with its CI lower bound above zero is supportive but
  not a second confirmatory primary endpoint. A positive delivery result
  with extra airtime/energy is a trade-off, not Pareto dominance. If the
  primary CI crosses zero, state "no detected advantage" rather than
  "equivalent"; if its upper bound is below zero, state a detected
  disadvantage. Keep an adverse flooding result in the paper or limits,
  not only the repository report. Sparse multi-candidate or multihop
  exposure makes the route-score mechanism inconclusive even if the whole-
  policy PDR comparison is valid.

The current generic CLI already supports this configuration. The following
is a **future execution recipe**, not a command run during planning. Before
using it, reserve a 2.1.25 evidence revision and verify both output paths
are absent. A one-seed pilot on an already exposed seed, with distinct pilot
paths, may be used solely to measure wall time; never tune the policy from
it. The full run is:

```sh
python3 tools/run_fair_multihop_probe.py \
  --scenario icc2027_random_sparse_fading_unconditioned \
  --nodes 50 --area-m 18000 --duration-s 600 \
  --rate-per-min 4 --traffic unicast --pair-mode random \
  --sf 7 --max-hops 8 --matched-rreq-timing \
  --temporal-fading-sigma-db 6 \
  --temporal-fading-interval-s 60 \
  --max-timeout-retries 0 \
  --seeds 20 --seed0 2001 \
  --protocol meshecho \
  --protocol meshecho-calibrated \
  --protocol prr-product-fallback \
  --protocol etx \
  --protocol meshtastic \
  --csv results/meshecho_v2_1_25_icc2027_random_sparse_fading_2001_2020.csv \
  --report docs/results/meshecho_v2_1_25_icc2027_random_sparse_fading_2001_2020.md
```

The CLI defaults to 32-byte payload, 17 dBm, 125 kHz, coding rate 4/5,
path-loss exponent 2.75, 4-dB shadowing, 6-dB capture threshold, and 2-s
MeshEcho/metric discovery. Route TTL defaults to 600 s for the selected
routing policies. `--max-timeout-retries 0` is explicit for reproducibility;
the selected MeshEcho and PRR-product policies do not use Smart-CALM's
adaptive timeout-retry controller.

Before interpreting the run, confirm 100 rows, 20 distinct planned seeds,
exactly five policies per seed, matching `scheduled_trace_sha256` and
scheduled/observed unicast counts within each seed, no duplicate rows, and
no non-finite metrics. The generic report's paired table uses **old**
MeshEcho as the left-hand policy; it does not calculate the primary
calibrated-minus-PRR+fallback contrast. Compute that contrast separately
from the raw CSV with the repository's `paired_mean_ci()` and independently
recompute the published numbers. `analyze_results.py` gives per-policy CIs,
which cannot substitute for paired-difference CIs.

Report the observed direct-link PRR distribution, cached-route multihop
fraction, discovery success, and multi-candidate discovery count before
interpreting score behavior. This random-per-flow mode is expected to have
little cache reuse. If candidate competition is rare, a null effect is low
mechanism exposure, not proof that the score fails on stale routes. Do not
switch geometry, drop seeds, or filter random pairs after seeing ACK results.
The 2.1.23 random-pair output used static channel, mixed traffic, unmatched
RREQ timing, and the old score; do not pool its numbers with this stratum.

## P2 Manuscript Decision Tree

| Audited P1 outcome | Permitted claim and paper action |
| --- | --- |
| Calibrated > matched PRR+fallback with paired ACK CI lower bound > 0 | Report the exact scenario, magnitude, CI, and airtime/energy cost. Verify candidate exposure before attributing the effect solely to scoring. The result strengthens the submission but does not prove physical validity or universal superiority. |
| Primary CI includes zero, but exploratory calibrated-old CI lower bound > 0 | State a possible correction relative to the old heuristic in this stratum, with the exact CI, but no detected advantage over PRR+fallback. Do not call the two policies equivalent. Novelty remains a major ICC risk. |
| Primary CI upper bound < 0 | State that calibrated MeshEcho underperforms matched PRR+fallback in this stratum; do not describe their performance as similar or interchangeable. |
| No detected calibrated-old gain or sparse route-score exposure | Limit the positive claim to the existing graph-qualified repeated-pair fading case. Disclose the new population result and its exposure limits without calling a null a failure; do not redesign the score using this cohort and still call it fresh. |
| Flooding dominates ACK completion | State that routed methods trade reliability for other metrics in that regime; do not hide the comparison or call MeshEcho generally more reliable. |

These rows are not mutually exclusive: apply every relevant row and report
joint outcomes together. For example, a detected advantage over PRR+fallback
does not erase an adverse comparison with flooding or a low-exposure warning.

Whichever branch applies, correct any wording that reads a zero-crossing CI
as equivalence. In particular, replace the current manuscript's
"statistically indistinguishable" shorthand with the exact difference,
CI, and "no demonstrated advantage". A concise paired-effect plot is more informative than
decorative mean bars; the current final page has secondary diagnostics and
references but ample whitespace. Keep labels, denominators, and 95% CIs
legible. The preferred figure uses audited frozen 51--70 data plus P1 only
after its independent audit; otherwise plot frozen 51--70 alone. The current
PDF has no new 2.1.24 figure. Rebuild with the existing IEEEtran toolchain,
check font embedding/citations/overfull boxes, render all pages, and compare
every plotted number with raw CSVs. No library installation is necessary
for the plan; a TeX-native plot or existing environment may be used later.

## P3 Scope and Stop Rule

The generic probe's random mode selects a new pair on every flow; its
`--pair-count` flag cannot create an unqualified repeated-pair pool. A
direct cache/aging generalization check would therefore require a scoped,
test-first runner extension: uniformly draw a fixed small pool of directed
pairs without filtering for reachability, repeat that pool across fading
blocks, retain every scheduled attempt in the denominator, and log pair
graph-hop/reachability strata only for interpretation. Freeze its own
independent seed range and complete run before any manuscript claim. Do
not squeeze this new implementation in at the cost of a verified P1 paper.

An SF8 check can use the generic fair probe because the dedicated
`run_icc_sensitivity_experiments.py` does not accept the calibrated or
PRR-product-fallback policies. The historical SF8 case also changes area
to 10 km and offered load to 1 flow/min, so call it a separate operating
point, not an isolated SF effect. A 100-node deep-multihop case already
exists in `run_icc_generalization_experiment.py`, but prior selected paths
were three hops even though the configured eligible range was 3--5. Both
options need fresh output paths, a complete planned seed set, quality-gate
review, and the same raw-CSV paired analysis; neither is required if it
would endanger the P1 audit or Oct 1 submission target.

Do not attempt a new ACK-eviction rule, threshold search, hardware testbed,
or a new routing algorithm in the remaining days unless a separate fully
tested study can be finished before the internal freeze. The existing
negative ACK-eviction and short-TTL results must remain visible.

## Submission and Release Gates

- The ICCT 2026 TeX says "Paper submitted", but the repository does not
  prove its actual EDAS, review, or publication status. If it is under
  concurrent review, resolve the dual-submission issue before ICC. If it
  was published, cite it and show the new method/evidence and non-overlap
  explicitly; do not present reused harness, prose, figures, or results as
  wholly new. If incremental novelty is insufficient, do not misrepresent
  it to pass review.
- Zu Gao and Zhi Quan must approve their exact names/order, Shenzhen
  University affiliation, contributions, funding and conflicts, and the
  accuracy of the AI-use disclosure. The PDF title and full author list
  must match EDAS exactly; ICC says mismatches can withdraw a paper from
  review. EDAS upload and final submission remain author actions.
- If a new experiment or code change is executed, release it separately
  from frozen 2.1.24: increment repository version, keep raw CSV/report
  paths versioned, run affected and full tests, check source-to-paper
  numbers and PDF layout, then selectively commit/push the verified
  release to GitHub under the existing version workflow. A planning-only
  Markdown edit does not claim a new simulation version.
- Accepted work requires author registration and presentation for
  proceedings/IEEE Xplore publication. ICC 2027 is fully in-person.

Recovery: read repository-root `task_plan.md`, `findings.md`, and
`progress.md` before continuing after context compression, then this
document. Update those three checkpoints before any later compression.
