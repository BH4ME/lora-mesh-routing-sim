# ICC comparison and mathematics revision

Date: 2026-10-13
Mode: academic-paper revision; existing IEEE conference manuscript.
Source: paper/icc2027/icc2027_lora_mesh.tex (same open editor document).

## Latest recovery audit and visibility edit

- Recovered the already completed 30-equation revision; do not duplicate
  the formula additions or resume firmware based on an older summary.
- Made legacy MeshEcho, Meshtastic-like and MeshCore-like explicit in the
  introduction, with their redundancy/discovery/recovery cost distinctions.
- Replaced the Related Work assertion of isolated component effects with a
  direct guide to the MT, MC and CPR equations and the common TX ledger.
  The four-arm aggregate alone is not a component ablation.
- Final edited source compiled successfully with the built-in compiler;
  confirmed again on 2026-11-04 after the interrupted turn was resumed.
- Four existing figure-data, author and release-metadata checks passed in
  the preceding continuation. The final source retains 30 equation groups.
- Independent baseline audit verified the numerical table, gains, paired
  intervals and delivery costs. The complete four-arm evidence is
  `results/meshecho_four_protocol_comparison_92300_92319_20261012_rerun.*`;
  the older `20261006 external_comparison` package contains only three arms.
- Applied both audit wording fixes: MT suppression ends at commitment, and
  the CPR table explicitly includes initial routed DATA before its repeat.
- The additional implementation recheck dispatched just before interruption
  returned no result; no new independent formula-audit result is claimed.
- An atomic patch failed on an unnecessary documentation context hunk and
  changed no files. The corrected source-only patch applied successfully.
- No numerical values, equations, figures, references or author order changed.
- Completion: this manuscript revision is done. The source/preview is current;
  no separate PDF was exported and no final page-count claim is made.

## Recovery verification of the same request

The completed manuscript revision below was already present after recovery.
No additional formula-count inflation or replacement source was needed.
The current source was read in full and recompiled successfully using the
desktop editor compiler. Four author/figure/release checks pass. The same
30 numbered equation groups, comparison tables, chart and interpretation
paragraphs remain in place; no new experiment or PDF export was performed.
Both independent read-only checks completed with no required revision:
MT/MC/CPR mathematics match the evaluated Python implementations; the existing
80-run/60-pair CSV supports table means, gains, intervals and delivery costs.
All 34 labels and five cited bibliography keys resolve without duplicates.
TikZ coordinate rounding is approximately 0.001 plot unit and does not change
the table values. Product-like results remain behavior-level simulation only.

## Latest user follow-up: full names and implementation-backed derivation

Status: complete. Preserve the earlier completed revision below.

- Make full protocol names visible in the performance table and numerical
  interpretation, not just in model subsections or abbreviated chart labels.
- Ground airtime in the simulator's wire lengths and explain CPR relay delay
  versus the separately configured Meshtastic-like delay.
- Correct the cancellation contrast: both policies retain duplicate suppression;
  CPR additionally accepts matching terminal-ACK cancellation before commitment.
- Do not rerun simulations, promote versions, export a separate PDF or make
  GitHub/EDAS changes. Compile only the same editor source.
- First compiler check found a new left/right delimiter pair crossing an
  aligned row in eq:cpr-relay-delay. Replaced only that pair with fixed-size
  delimiters; compilation is the regression check. No math definition changed.
- A targeted test-path probe used two nonexistent old figure-test filenames;
  located the current tests with rg --files instead.
- Checkpoint patch initially used a nonexistent handoff heading; the atomic
  patch was not applied. Re-read the exact heading and applied the corrected patch.

### Latest changes and verification

| Issue | Location | Resolution | Status |
| --- | --- | --- | --- |
| Baseline names hidden by abbreviations | Results table, figure caption and three comparison paragraphs | Full protocol names and separate formula-linked interpretation | RESOLVED |
| Airtime lacks explicit byte accounting | Common path and physical cost, eq:wire-length | Base/path/application/optional bytes and CPR DATA/FLOOD/ACK specialization | RESOLVED |
| CPR waiting term lacks derivation | Commit-time admission, eq:cpr-relay-delay | Margin/jitter/role delay and maximum forwarding-wait interpretation | RESOLVED |
| Duplicate suppression appears mutually exclusive with ACK cancellation | ACK-terminated pending relay suppression | CPR retains duplicate-FLOOD suppression and adds terminal-ACK cancellation | RESOLVED |

- Final source has 30 numbered equation groups; all labels/citations resolve
  with no duplicates or uncited bibliography entries.
- Built-in compiler succeeds for the same open source after the final edit.
- Four existing author, figure-data and release-metadata tests pass.
- 69 direct implementation-backed assertions verify wire lengths/ToA for
  1..6 hops and three markers plus relay-delay bounds/role discount. These are
  unit-level checks, not new simulation results or hardware validation.
- Independent read-only audit confirmed byte arithmetic and delay; resolved
  its sole wording concern by using encoded path count n_P, distinguishing
  routed full paths from FLOOD's growing path and maximum-length budget.
- Numerical table values and plot coordinates are unchanged. No new references,
  experiments, PDF export/page-count assertion, version bump, push or EDAS action.

## Revision tracking

| Issue | Section | Action | Status |
| --- | --- | --- | --- |
| Meshtastic and MeshCore comparison is not sufficiently visible | Protocol models and Results | Full protocol names and formula navigation in comparison table; MC discovery versus CPR initial DATA flood | RESOLVED |
| Mathematical explanation should be central, not isolated equations | Models and CPR | Four new equation groups, with conditions and explanatory interpretation | RESOLVED |
| Keep evidence honest | Experiments and Results | Correct commit/start distinction and counter semantics; reuse only existing paired artifacts | RESOLVED |
| Preserve open document and verify | Entire source | Built-in compiler success; four metadata/data tests pass; label/citation and delivery-cost checks pass | RESOLVED |

## Boundaries

No new simulation, algorithm implementation, firmware change, PDF export,
release/version promotion, GitHub write or EDAS action belongs to this revision.
Retain existing author order and omit unsupported funding statements.

## Initial observations

The recovered source already contains 24 equation groups, both named-product
model sections, a four-arm mechanism table, and the paired bar chart. Do not
repeat old equations merely to inflate their count. Added mathematics should
explain an actual decision rule or derive an observable consequence.

## Changes and verification

- Source now has 28 equation groups, not an inflated set of duplicate formulas.
- Added eq:cpr-epochs, eq:cpr-route-lifecycle, eq:cpr-marginal-gain and
  eq:delivery-cost. All new symbols have conditions or adjacent definitions.
- Corrected the MT suppression boundary to request commitment, not its
  possibly later air start. CPR evaluates scheduled-start feasibility at
  commitment; a later ACK cannot undo an already reserved TX.
- Clarified MC discovery success as a matching source-side RREP before its
  timeout and defined the conditional cache-hit success probability.
- Clarified legacy collision input as successfully captured overlap, and MT
  suppression counters as flags rather than necessarily saved TX airtime.
- Kept the existing four-arm results, bar chart, authors, IEEEtran class and
  five verified references. Added no citations, new runs or deployment claims.
- Recomputed pooled airtime per deadline-delivered flow from existing CSVs:

| Arm | Airtime sum (s) | Deadline deliveries | Cost (s/delivery) |
| --- | ---: | ---: | ---: |
| CPR | 125.806848 | 667 | 0.188615964 |
| Legacy ME | 204.623360 | 641 | 0.319225211 |
| Meshtastic-like | 585.130240 | 660 | 0.886560970 |
| MeshCore-like | 197.929472 | 630 | 0.314173765 |

The built-in compiler returned success for the edited open source. All label
references and citations resolve, and there are no duplicate labels. Four
existing author/figure/release metadata tests passed. Existing ResourceWarnings
for unclosed figure-data file handles are nonfatal and were not changed.

Compilation is not a standalone PDF export or rendered-page inspection. The
older on-disk PDF must not be described as this revised preview.

Final independent formula review: no required corrections. Added explicit
first-applicable-branch precedence to the route lifecycle equation.
