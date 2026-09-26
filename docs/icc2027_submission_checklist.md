# ICC 2027 Submission Checklist

This checklist tracks the 2.1.24 MeshEcho revision for ICC 2027. The official
sources are the [submission guidelines](https://icc2027.ieee-icc.org/submission-guidelines)
and [symposium-paper dates](https://icc2027.ieee-icc.org/authors), which list
2 October 2026 as the paper deadline. Confirm the exact closing time in EDAS.

## Verified In Repository

- [x] Initial manuscript is in English.
- [x] Source uses the IEEE conference LaTeX class at 10-point conference
  format.
- [x] Manuscript source avoids manual page-margin, column-width, global
  float-spacing, and global row-spacing compression; the source requests
  `IEEEtran` conference mode with letter paper and 10-point text.
- [x] The paper source names `Zu Gao` and `Zhi Quan` in that order, both at
  Shenzhen University. Keep the same spelling and order in the final PDF
  and EDAS record.
- [x] The 2.1.24 development seeds are 41--50; the once-frozen 51--70
  fading/static holdout and isolated comparison have versioned raw CSVs and
  reports. Fading calibrated-minus-original ACK is +0.1154
  [+0.0307,+0.2001] at +2.467 s airtime, while calibrated-minus-matched-
  fallback PRR-product is +0.0026 [-0.0055,+0.0107]. Static and isolated
  intervals include zero; ACK-timeout eviction is an adverse control.
- [x] The 51--70 short-TTL control was independently audited with 793
  observed unicasts per policy. Calibrated MeshEcho at 30 s TTL has 0.320
  ACK PDR/64.8 s airtime versus 0.624/23.7 s at 600 s; the seed-paired
  30-minus-600 s differences are -0.3043 ACK PDR
  (95% CI [-0.3932,-0.2154]) and +41.05 s airtime ([31.40,50.70]).
  Its 30 s ACK difference from original MeshEcho is not conclusive:
  +0.0215 [-0.0227,+0.0657].
- [x] Prior ICC practice evidence is recorded in
  `docs/icc2027_prior-work_hardware-evidence.md`; no universal physical-testbed
  requirement was found in the official guidelines or the sampled papers.

## Release And Manuscript Checks

- [x] Revise the manuscript's abstract, methods, tables, discussion,
  and conclusion around the 2.1.24 holdout. Distinguish the optional
  `meshecho-calibrated` variant from original `meshecho`; include PRR-product
  with and without matched fallback, the static null result, equal-candidate
  isolated result, and adverse ACK-eviction control without claiming physical
  validation or strong-baseline superiority.
- [x] Rebuild and inspect the 2.1.24 PDF. Verify English text, exact
  `Zu Gao` / `Zhi Quan` order, embedded fonts, legible tables, and
  at most six printed pages in 10-point IEEE conference format. The final
  manuscript is five pages; the unused 2.1.23 figure is not part of it.
- [x] Run final repository checks and confirm the versioned source, tests,
  raw CSVs, summaries, reports, and reproduction commands in the 2.1.24
  release package. The full suite has 139 passing tests.

## Must Be Completed In EDAS

- [ ] Register the exact final title and the exact same author order in EDAS;
  ICC states that a mismatch can withdraw the paper from review.
- [ ] Upload only the compiled PDF through EDAS, not the `.tex` source.
- [ ] Confirm the paper is not simultaneously submitted elsewhere and that
  all text/figures satisfy IEEE originality and plagiarism requirements.
- [ ] Have Zu Gao and Zhi Quan verify the exact funding and conflict-of-
  interest statements. Do not assume either declaration is "none" before
  author confirmation.
- [ ] Before final publication, arrange the required author registration and
  conference presentation; these are conditions for proceedings/Xplore
  publication after acceptance.

The repository PDF is the 2.1.24 preparation artifact. EDAS registration and
PDF upload remain pending.
