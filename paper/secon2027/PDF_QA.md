# Final manuscript PDF acceptance

The exact accepted PDF is the third complete formal build:
`work/paper-final-build-v3/main.pdf` relative to the chat workspace.
Its SHA-256 is
`e477617e417a5c089bfeac3f4725e40e54e39e666071a1711c5c0e0f749eb1fd`.
The release task copies this exact file into the final output package;
it must retain the hash rather than rebuilding or substituting an old PDF.
The full source/input/PDF hash chain is `manuscript_manifest.json`.

## Actual-file checks

- Tectonic0.17.0 completed with exit0; actual PDF has **9 letter-size
  pages**, including figures and27references. Class is IEEEtran conference
  **10pt**, with unchanged standard margins and two-column text.
- All9pages were rendered at1.4× and visually inspected. Equations,
  controller diagram, all4quantitative figures, tables, captions and
  references are readable. No clipping, overlapping labels or unintended
  blank pages were found. The root reviewer independently inspected all9v2pages; v3 review is
  recorded separately by that reviewer.
- All26 referenced font resources are embedded; none is Type3. Main text
  is embedded Times-compatible NimbusRomNo9L at9.963PDFpoints, the
  normal10TeXpoint conversion. Figure font is embedded DejaVuSans.
- Final TeX pass has no undefined citations/references, no overfull box,
  and no font-substitution warning. Initial-pass cross-reference warnings
  resolved in Tectonic's automatic rerun. Remaining underfull warnings
  concern justification and long pinned URLs; actual pages were inspected.
- Static check:27cited keys and27bibliography entries, no unused or
  undefined key, no duplicate label, no undefined reference, no nocite.
- PDF author metadata is blank. Title/subject are nonidentifying. Text,
  annotations and metadata contain no human author/affiliation, user-path,
  or identifying project-repository link. Official external baseline links
  are retained as citations.

## AI disclosure and anonymous review

The taskbook says the anonymous review PDF should contain no acknowledgments.
The exact IEEE
Conference Author Center policy retained in
`docs/research/secon2027_paper_blueprint.md` §8 says generated text/figures/code
**“shall be disclosed in the acknowledgments section of any article
submitted to an IEEE publication.”** Its recorded page response SHA is
`7951cdcfff6e0acb68bea9417110e4ae7893b283a9d479527bf3099f175e346a`.
No SECON waiver was found in the recorded official requirements review.
Accordingly the unnumbered ACKNOWLEDGMENT contains only nonidentifying
AI-use disclosure: Codex, actual abstract/SectionsI–VII, figure code,
simulation/analysis software assistance. It includes no human, institution,
funding, grant, author-contribution or invented human-review statement.
A renamed generic heading would not follow the policy's explicit wording.

## Evidence and revision history

Formal results use all760prespecified keys,20seeds per cell, tested2.1.29
and snapshot63e3809a…; no development result enters these estimates.
`docs/research/secon2027_final_paper_claims_review.md/.json` verifies the
numeric text and145figure source rows against analysis; all16figure output
hashes match. Separate raw/statistics/exposure reviews and the claim
register delimit what each check establishes.

The first complete PDF had10pages and was rejected. This9page version
shortens redundant introduction/evaluation/discussion prose; it does not
shrink the10pt body, change margins, remove adverse findings, or alter
any numerical result. Loading T1 font encoding before IEEEtran removes
XeTeX class-initialization font warnings. Figure formal-v2 corrects minor
tick-label crowding only; formal-v1 and the rejected10page build remain
preserved as development artifacts.

PDF acceptance is a file/layout/evidence check. It is not EDAS submission,
acceptance, independent hardware validation, or certification of private
authorship/funding/overlap declarations.

The third build explicitly adds the frozen915MHz carrier and the absence
of duty-cycle/LBT enforcement. All9v3pages were newly rendered and
inspected. Source and PDF hashes were refreshed; quantitative prose and
figure inputs/outputs are unchanged. The prior numeric review retains its
original v2source hashes; the v3manifest records this scope delta.
