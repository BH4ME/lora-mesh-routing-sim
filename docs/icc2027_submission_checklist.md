# ICC 2027 Submission Checklist

This checklist tracks the 2.1.27 MeshEcho-CPR manuscript revision for ICC 2027,
which uses independently audited CPR development and untouched holdout data.
The older 2.1.25/2.1.26 MeshEcho comparison remains historical. The official
sources are the [submission guidelines](https://icc2027.ieee-icc.org/submission-guidelines)
and [symposium-paper dates](https://icc2027.ieee-icc.org/authors). On
2 October 2026, the live author pages list 16 October, while the older
official CFP PDFs still say 2 October. The logged-in EDAS IoT submission form
is currently open; confirm its exact closing time rather than relying on
either published date alone.

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
- [x] The current ICC method is `MeshEcho-CPR`, a new source/recovery and
  relay-feedback core on the shared packet-level LoRa substrate. The paired
  arms are CPR, CPR-no-cancel, DRC-no-rescue, and sealed DRC controls.
- [x] CPR development seeds are `92200..92219`; untouched holdout seeds are
  `92300..92319`. Both manifests pass the evidence-v2 and population audits,
  with complete request/TX/RX/ACK joins and fixed scheduled-flow denominators.
- [x] The untouched holdout reports CPR ACK PDR `0.9829`, destination PDR
  `0.9984`, and mean TX airtime `6.290 s`. The paired CPR-minus-DRC-no-rescue
  ACK interval is `[+0.0172,+0.0495]`, destination interval is
  `[+0.0191,+0.0538]`, and mean airtime is lower by `3.143 s`.

The following checks preserve independently audited historical evidence; they
are not inputs to the current CPR manuscript:

- [x] The separate 20-seed, 813-unicast random-pair case reports the
  adverse result: Meshtastic-like exceeds MeshEcho in ACK PDR
  (0.708 versus 0.486) and destination PDR (0.995 versus 0.515) while
  using much less aggregate TX airtime (38.9 versus 152.8 s). The
  scenario was designed after the earlier holdout and is not a
  preregistered confirmatory test. MeshEcho has no demonstrated ACK
  advantage over matched-recovery PRR-product in either case.
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
  and conclusion around the CPR state machine, ACK-terminated relay ledger,
  paired controls, and declared simulation limits. Present ACK and destination
  delivery separately and identify that the result is not hardware validation.
- [x] Rebuild and inspect the 2.1.27 PDF. Verify English text, exact
  `Zu Gao` / `Zhi Quan` order, embedded fonts, legible tables, and
  at most six printed pages in 10-point IEEE conference format. The final
  manuscript is five pages and includes the CPR performance figure; historical
  three-model delivery figures are not part of it.
- [x] Run the full repository regression and confirm the versioned source,
  raw CPR streams, summaries, manifests, gate reports, and reproduction
  commands in the 2.1.27 release package. The final regression reports
  `1181 passed, 1 skipped`; the five-page Letter PDF was rendered and checked.

## Must Be Completed In EDAS

- [x] Register the exact title in EDAS. Paper `1571361802` lists Zu Gao
  as the first author and is currently `Pending (no manuscript)`.
- [ ] Add Zhi Quan as second author in EDAS and verify that both names
  match the final PDF exactly; ICC warns about author-list mismatches.
- [ ] Update the EDAS abstract to match the revised, baseline-centered PDF.
- [ ] Upload only the compiled PDF through EDAS, not the `.tex` source.
- [ ] Confirm the paper is not simultaneously submitted elsewhere and that
  all text/figures satisfy IEEE originality and plagiarism requirements.
- [ ] Have Zu Gao and Zhi Quan verify the exact funding and conflict-of-
  interest statements. Do not assume either declaration is "none" before
  author confirmation.
- [ ] Before final publication, arrange the required author registration and
  conference presentation; these are conditions for proceedings/Xplore
  publication after acceptance.

The repository PDF is the 2.1.27 preparation artifact. EDAS registration is
partial: Zhi Quan and the manuscript PDF are not yet present, so the paper
is not submitted for review.
