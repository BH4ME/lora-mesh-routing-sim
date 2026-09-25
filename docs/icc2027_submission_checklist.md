# ICC 2027 Submission Checklist

This checklist records the venue requirements checked against the 2.1.23
MeshEcho package. The official source is the [ICC 2027 submission
guidelines](https://icc2027.ieee-icc.org/submission-guidelines).

## Verified In Repository

- [x] Initial manuscript is in English.
- [x] Source uses the IEEE conference LaTeX class at 10-point conference
  format.
- [x] Manuscript source avoids manual page-margin, column-width, global
  float-spacing, and global row-spacing compression; the final build uses
  `IEEEtran` conference mode with letter paper and 10-point text.
- [x] Compiled initial-submission PDF is at or below 5 printed pages, below the six-page
  hard limit. A submission longer than six pages is rejected without review.
- [x] The paper reports the calibrated multi-hop matrix, managed-flooding,
  ETX, fixed-SF ETT, and min-hop baselines, per-seed quality gate, SF/load
  sensitivity, random-pair and deeper-hop generalization, temporal-fading
  stale-route diagnostics, MeshEcho component ablations, controlled
  route-selection evidence, fairness boundary, and simulation limitations.
- [x] Versioned code, tests, raw CSVs, summary CSVs, Markdown reports, and
  reproduction commands are prepared under the `2.1.23` release prefix.
- [x] Prior ICC practice evidence is recorded in
  `docs/icc2027_prior-work_hardware-evidence.md`; no universal physical-testbed
  requirement was found in the official guidelines or the sampled papers.
- [x] No claim of physical validation or topology-independent dominance is
  made.

## Must Be Completed In EDAS

- [x] Replace `Anonymous Authors` in
  `paper/icc2027/icc2027_lora_mesh.tex` with the English-only names
  `Zu Gao` and `Zhi Quan`, both affiliated with Shenzhen University.
- [x] Rebuild `paper/icc2027/icc2027_lora_mesh.pdf` from the corrected
  source; verify its first-page text extraction and embedded fonts.
- [ ] Register the exact final title and the exact same author order in EDAS;
  ICC states that a mismatch can withdraw the paper from review.
- [ ] Upload only the compiled PDF through EDAS, not the `.tex` source.
- [ ] Confirm the paper is not simultaneously submitted elsewhere and that
  all text/figures satisfy IEEE originality and plagiarism requirements.
- [ ] Before final publication, arrange the required author registration and
  conference presentation; these are conditions for proceedings/Xplore
  publication after acceptance.

The current PDF is a technically verified preparation artifact. It is not an
EDAS submission until the author metadata and venue registration checks above
are completed.
