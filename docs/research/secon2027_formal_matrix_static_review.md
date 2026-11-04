# Formal matrix candidate: independent static review

Reviewed 2026-11-04. Candidate:
`work/formal-matrix-candidate.json`, SHA-256
`9f0420323392c3c23cb91a823786865aa80bbe589d057afd7336c1d6c0ccb22f`.

**Conclusion:** No structural configuration, constructor, pairing or clean
ablation defect found in this candidate. It covers the required finite
scope. It is not yet freeze-ready: the intentionally pending complete-pilot
gate, measured resource budget, sample-size rationale and prospective
scenario/claim criteria must be completed before the first validation run.
No configuration was changed by this review.

## Coverage and static checks

| Population | Count | Finding |
| --- | ---: | --- |
| S1/S2/S3 × default/matched × four primary models × 20 seeds | 480 | Complete; cases use the intended CPR, legacy ME, MT-like and MC-like protocol IDs. |
| Three CPR controls × S2/S3 matched × 20 seeds | 120 | Complete; reference CPR is already present within those same cases. |
| S2 matched deadline 10/60 s × four models × 20 seeds | 160 | Deadline 30 s reference is the main S2-matched case; no extra duplicate reference run needed. |
| **Total** | **760** | No duplicate `(case_id, arm_id, seed)` tuples. |

`validate_matrix`, every `CprCase` constructor, all eleven arm parameter
validators and protocol constructors passed. Constructors were exercised
without binding or constructing a simulator. Proposed seeds 2027100–2027119
have no overlap with the registry's current cohorts or historical exclusions;
the proposed cohort is not registered. The analysis seed 20271104 is a
separate resampling identifier. This review did not register/expose seeds,
resolve a seeded environment, generate traffic/channel traces, call
`Simulator.run`, execute an experiment, freeze a plan, or alter pilot state.

S1 and S3 differ only in case label and offered rate (8 versus 40 flows/min)
within each regime; their environment, PHY, deadline and effective primary
model parameters agree. They support a two-point load comparison under the
existing analyzer. Two points do not establish a saturation threshold or a
detailed load-response shape. Rate is total offered application load across
the endpoint pool, not rate per pair: the runner starts one flow at 1 s,
then samples interarrival intervals and cycles through the four ordered
pairs.

The two robustness cases have the same case/environment settings as
S2-matched except their label and deadline. The unseeded 5×4 grid's four
ordered endpoint pairs each have shortest structural distance 4 hops
normally and 6 hops while edges (7,8) and (12,13) are removed. This is within
the resolved six-hop limit. It confirms a structural alternative, not an
actual received route, fault exposure or successful recovery. Faults occupy
the half-open interval [80,160) s with 80 dB added attenuation. Pilot exposure
must still show what happened to active/carried paths and physical actions.

## Overrides and controls

Resolved pre-bind primitive parameters show exactly these default→matched
differences:

| Model | Differences |
| --- | --- |
| CPR | None. Explicit 600-s TTL and 0.45/0.65-s base/jitter equal existing defaults. |
| Legacy ME | None; same effective values. |
| MT-like | `base_delay_s`: 0.75→0.45; `jitter_s`: 0.75→0.65. |
| MC-like | `route_ttl_s`: 300→600; flood base: 0.50→0.45; flood jitter: 0.70→0.65. |

In both S2-matched and S3-matched, comparison against CPR-matched yields
only `name` plus one intended difference:

- `noackcancel`: `cancel_on_ack` true→false; ledger, eviction, source ACK
  behavior and other parameters remain enabled/equal.
- `norepeat`: `enable_repeat` true→false; the source keeps its nominal
  skipped-repeat observation slot before recovery.
- `norecovery`: `enable_recovery` true→false; repeat remains enabled.

These satisfy the analyzer's clean-control parameter checks. The historical
whole-ledger `nocancel` and supplemental common-ACK protocols are absent.
No hidden substitution of those policies was found. The four primary arms
remain simplified models; the matrix does not address their documented
official-firmware fidelity gaps.

All 760 run tuples are currently explicit physical runs, not aliases.
Identical CPR/ME default/matched settings do not create independent new
scientific replication: report 20 seeds per case and do not pool the two
regimes as n=40. The analyzer keeps case/plan/arm identities separate. Any
later cost-saving reuse would need a declared hash-checked alias before
freeze; the current 760 count assumes no such reuse.

## Deadline and accounting semantics to freeze explicitly

The runner computes `cutoff = duration_s + deadline_s` and every scheduled
flow's measurement deadline as enqueue time plus `deadline_s`. Thus this
matrix resolves:

| Deadline / drain | Generation horizon | Accounting cutoff |
| ---: | ---: | ---: |
| 10 s | 240 s | 250 s |
| 30 s | 240 s | 270 s |
| 60 s | 240 s | 300 s |

Only CPR's controller parameter `app_deadline_s` changes with these cases.
Legacy ME, MT-like and MC-like constructors have no corresponding deadline
change; all arms nevertheless share the measurement horizon within each
case. This is the registered behavioral comparison, not identical
source-expiry policies. Describe the robustness axis as changing application
deadline and associated drain/accounting window. Cross-deadline airtime
differences cannot be attributed solely to a CPR timer, since more tail
transmissions may be charged at longer cutoffs. Preserve post-deadline and
no-start diagnostics and do not truncate late-cost evidence differently by
arm. Full ToA is charged for a frame starting within its case's cutoff.

Inherited case defaults are fixed by the eventual source snapshot but
should be explicit in the freeze report/config table: 32-byte useful payload,
SF7, 125 kHz BW, CR index 1, 17 dBm, six hops, path-loss exponent 2.75,
6-dB capture threshold, 0.25-s safety margin, and the custom full-frame
encoding. Radio defaults additionally imply 915 MHz, explicit header, CRC
and an eight-symbol preamble. All grid nodes have `router` role; the nominal
5000-m area is not a uniform-random square deployment because grid spacing
and dimensions determine actual positions. Do not infer regional duty-cycle
compliance or hardware calibration.

The 240-s generation horizon and at most 300-s cutoff do not exercise normal
expiry of a 600-s matched cache; the 300-s default MC TTL also exceeds its
270-s cutoff after route learning. Report cache behavior without claiming
that this matrix estimates the causal effect of TTL expiration.

## Remaining pre-freeze work

1. Complete and audit the replacement pilot's full 72 keys. The referenced
   `development-method-freeze.json` does not yet exist, as expected. Bind
   the selected method hashes to the completed pilot and freeze once before
   validation exposure. Keep pilot-v1's scientific failure and superseded
   snapshot distinct from this evidence.
2. Replace candidate resource limits (four workers, four hours, 12 GiB)
   with a budget derived from completed pilot measurements by scenario/arm,
   including peak RSS, raw/archive bytes, the two longer/shorter drain cases,
   controls and infrastructure-retry/audit headroom. Concurrency must follow
   measured memory, not the candidate number alone.
3. Record why n=20 is the selected finite descriptive budget and the
   intended precision limits. The current statement rules out outcome
   selection/precision stopping but does not itself provide a precision/cost
   rationale. Do not claim reliable power from a three-seed pilot.
4. Freeze scenario-validity and claim rules from pilot diagnostics before
   examining validation outcomes: actual multi-hop depth, S2 carried-path
   fault/alternative exposure, S3 contention/queue/eviction exposure and
   each control's physical action exposure. Weak or zero exposure must
   narrow the conclusion, not remove validation seeds or trigger new-seed
   searches. Update the contract's stale “zero runs/not run/pending” freeze
   table to the actual completed evidence before hashing it.
5. Preserve the specified seed-level, 10,000-resample, descriptive
   unadjusted 95% analysis and all undefined metrics. The selected metric
   names exist in the analyzer. Its paired effects are within each case;
   a deadline-response plot may combine the three declared case summaries
   descriptively, but cross-deadline paired contrasts would need a separate
   predeclared analysis rather than being inferred from existing within-case
   comparisons.

With those records complete, the finite scope covers task-book requirements
for default/matched main comparisons, three essential controls in two
scenarios, one limited robustness axis, and a load comparison. Capacity
sensitivity is conditional on observed eviction exposure or a memory-benefit
claim; no unconditional firmware-memory or broad topology/channel-generalization
claim is justified by this candidate.

Read-only references: task-book §§6–8; acceptance D01–D11/E01–E13/F01–F08;
`secon2027_baseline_fidelity.md`; `secon2027_experiment_contract.md`;
`tools/secon2027_experiment.py`; `tools/run_cpr_experiment.py`;
`tools/run_drc_experiment.py`; `tools/secon2027_scenarios.py`;
`tools/analyze_secon2027.py`; protocol constructors in `lora_mesh_sim.py`.
