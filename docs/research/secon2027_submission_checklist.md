# SECON 2027 candidate and submission checklist

This checklist tracks a reviewable manuscript and reproducibility package. No EDAS submission, registration, payment or external message has been performed. Formal numerical and PDF acceptance checks are complete on the final v3 artifact identified below; external publication is tracked separately until its exact remote SHA is verified.

## Verified venue rules

Official conference, CFP, author and submission pages were checked on **4 November 2026**. Exact URLs, excerpts and response hashes are preserved in `secon2027_official_requirements.md`.

| Item | Verified rule or unresolved detail |
| --- | --- |
| Conference | IEEE SECON 2027, Lisbon, Portugal, 5–7 May 2027. |
| Full-paper deadline | 30 November 2026. The inspected pages do not specify a time of day or time zone; do not label it AoE. |
| Earlier registration deadline | A separate abstract or paper-registration date was not established from the inspected pages. Recheck the live official submission link and EDAS registration details before any future submission. |
| Internal target | 28 November 2026, leaving time to resolve submission details. |
| Format | Standard IEEE conference template, 10-point type, with at most nine pages including every figure, reference and appendix. |
| Review | Double blind. The anonymous artifact must not reveal author names, affiliations, identifying repository links or author metadata. Describe prior and self-authored work in normal third person. |
| Submission title | The PDF title must exactly match any future EDAS registration title. |
| Submission channel | PDF through EDAS; producing this candidate does not submit it. |

Successful LaTeX compilation alone does not establish page, font, anonymity or visual compliance. Check all of them against the same latest exported PDF. Do not add an unverified statement that there was no external funding.

## Evidence and manuscript checks

Checked items below are supported by completed evidence, including the independent final v3 PDF review. Open publication items are updated only after remote verification.

- [x] Preserve the ICC manuscript independently; maintain the SECON project under `paper/secon2027/`.
- [x] Distinguish actual source snapshots and tested versions from later metadata promotions. Preserve the failed first pilot and its original evidence.
- [x] Describe the four evaluated objects as behavioral models, with their official-firmware fidelity limits, frame overhead and lack of RF calibration.
- [x] Complete the corrected 72-run development pilot and its frozen 161-test gate.
- [x] Independently restore the corrected pilot archive in a new directory, verify all 1,517 member hashes and audit all 72 runs using saved source. The successful supervisor report is `secon2027_supervisor_pilot_archive_review.md`.
- [x] Declare the formal method, scenarios, controls, statistics, sample size, failure policy and prospective claim gates before the first formal execution.
- [x] Preserve the administrative contract-wording erratum after formal execution began: 43 completed keys remained intact, all 20 seeds were exposed, and continuation used the same frozen plan. Do not describe the clarification as preceding first exposure.
- [x] Record release 2.1.29 at commit `95eee87e7757bcd8316088fee2517bc6a796801d`, with successful SSH push and matching authenticated GitHub API ref verification.
- [x] Complete all 760 formal keys and their source/event audit. Retain every negative, zero, undefined, failed or unfinished outcome in the applicable inventory.
- [x] Confirm at closeout that no formal outcome triggered algorithm tuning, replacement seeds, changes to the matrix or changes to predeclared statistics and claim criteria.
- [x] Trace every final number and plot to its audited table, run key, manifest and saved source. Report all prospective claim gates and any inadequate exposure.
- [x] Record the actual formal analysis environment, dependencies, commands, analyzer/helper hashes and output hashes. The intended environment is Python 3.9.6, NumPy 1.26.4 and Matplotlib 3.7.5; observed metadata remains authoritative.
- [x] Preserve the complete formal raw evidence in an indexed archive; independent clean restoration verified all14,667members and saved-source audit760/760.
- [x] Publish and verify complete raw archive transport parts at `30e7bd42ecee5ff3d538601df8146934eca680fa`; all114smallparts preserve the original whole archive. Final manuscript/analysis delivery commit is tracked below.
- [x] Compile the final LaTeX source into a newly saved PDF and verify a maximum of nine pages on that exact file.
- [x] Inspect every PDF page visually. Confirm readable figures, table text and equations, with no clipping, overlap or unintended blank pages.
- [x] Confirm the 10-point IEEE conference layout from source and rendered output, embedded fonts from the PDF, and resolved citations and references.
- [x] Check PDF text, annotations and metadata for author, affiliation, local user-path and identifying repository-link leakage.
- [x] Reconcile the AI-assistance disclosure with the final text, diagram code and software assistance under the applicable IEEE policy.
- [x] Record final source/PDF hashes, Tectonic0.17.0, render/font/metadata diagnostics in `paper/secon2027/manuscript_manifest.json` and `PDF_QA.md`.
- [ ] Record the final closeout commit and matching authenticated remote SHA; earlier2.1.29publication does not substitute for it.

The exact audit, analysis, figure and archive-restoration commands are documented in `../reproducibility/secon2027_reproduce.md`. Its standalone utilities are under `artifacts/secon2027/reproduction_helpers/`.

## Declarations and interpretation boundaries

The current draft names **OpenAI Codex** and describes assistance with literature organization, drafting the abstract and Introduction through Discussion, the controller-timing diagram code, and simulation and analysis software. Its outputs were used as drafts and implementation suggestions. Match the final disclosure to the actual retained contributions and the IEEE requirement to identify the system, affected content and level of use. Do not invent author contributions, conflicts of interest, funding, ethics approval or completed human verification.

This is a simulated-network study without new RF-device, human-participant or user-traffic measurements. It provides no battery-life or whole-device energy measurement. Preserved firmware version 0.1.4 is not equivalent to the repaired Python controller. The internal evidence package may contain historical machine paths or identifying repository information; an anonymous review artifact requires a separate identity check.

The unadjusted 95% intervals are descriptive. They do not support multiplicity-controlled significance, noninferiority or universal product-superiority claims. Keep the grid, fault, PHY and workload scope explicit, and distinguish destination delivery from timely source confirmation. Deadline sensitivity changes both the deadline and drain/accounting window. The two offered-load points do not establish a saturation threshold. Post hoc patterns may be reported as observations, without being converted into predeclared hypotheses or used to trigger new validation seeds.

## Items before any future actual submission

The current task produces a candidate and does not operate EDAS. Before any later submission, the responsible authors must verify originality, concurrent-submission status, author consent and metadata, exact title equality, live deadlines and registration policy, and the latest AI-disclosure rules. An archived ICC file does not establish whether that manuscript was submitted or whether its content can be submitted concurrently.

The existing private author record is Zu Gao and Zhi Quan, Shenzhen University. Keep that information in private author metadata and out of the anonymous PDF. No author-order or funding change is inferred. The conference author-list restriction must be checked against the actual registration deadline before submission. These submission actions remain separate from producing and inspecting the requested reviewable candidate.

## Final v3 PDF evidence

The final anonymous file is `paper/secon2027/meshecho-secon2027-anonymous.pdf`, **186,064bytes**, SHA-256 `e477617e417a5c089bfeac3f4725e40e54e39e666071a1711c5c0e0f749eb1fd`. It is **9Letter pages**, using the standard IEEEconference10pt source and an observed dominant9.963PDF-point body font. All26fonts are embedded, with noType3 fonts. All27references resolve. The compiler's final pass has no overfull boxes, undefined references or font warnings. All9rendered pages were inspected; no clipping, overlapping text, illegible figures or unexpected blank pages were found.

Independent execution-side and supervisor reviews agree. `results/secon2027/gates/formal-v1/final-pdf-qa-v3.json`, `docs/research/secon2027_supervisor_final_pdf_review.json` and the manuscript manifest bind the exact file and source hashes. PDFmetadata author is blank; extracted text, annotations and the6public-reference links reveal no author names, affiliation, email, personal repository or local path. The final radio row explicitly states915MHz and the limitations explicitly state that no duty-cycle or listen-before-talk enforcement is modeled.

The sole Acknowledgment paragraph is the nonidentifying AI-assistance disclosure. The recorded IEEEpolicy explicitly requires this disclosure in the acknowledgments section; no human/funding acknowledgments or invented declarations are included. The v1ten-page draft and v2without the explicit radio-scope sentence are superseded internal builds, not the delivered manuscript. NoEDASsubmission occurred.
