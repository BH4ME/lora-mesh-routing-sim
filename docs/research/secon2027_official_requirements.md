# SECON 2027 official requirement recheck

Checked 2026-11-04, approximately 15:22–15:27 Asia/Shanghai. This is a read-only retrieval; no EDAS submission, registration, payment or message was sent. The four official pages below were fetched successfully with `curl -fLsS --max-time 30` using normal TLS verification. Requirements match the task-book record.

| Item | Verified requirement | Official source |
| --- | --- | --- |
| Conference | IEEE SECON 2027, Lisbon, Portugal, 5–7 May 2027; physical in-person event | [Home](https://secon2027.ieee-secon.org/) |
| Full-paper deadline | 30 November 2026 | [Authors](https://secon2027.ieee-secon.org/authors), [CFP](https://secon2027.ieee-secon.org/call-papers) |
| Notification / camera ready | 15 February / 15 March 2027 | Authors and home |
| Length | At most nine pages **including all figures, references and appendices** | [Submission guidelines](https://secon2027.ieee-secon.org/submission-guidelines) |
| Format | Font size 10 points; standard IEEE conference template linked by guidelines | Submission guidelines; [IEEE templates](https://www.ieee.org/conferences_events/conferences/publishing/templates.html) |
| Review | Double blind; identity withheld and anonymity preserved while contextualizing prior work, including own work | CFP |
| Initial submission | PDF only, through EDAS | Submission guidelines |
| Title | PDF title must exactly match EDAS registration title | Submission guidelines |
| Author metadata | EDAS must list all coauthors; author list cannot change after paper registration deadline, and accepted-paper author list cannot change in final manuscript | Submission guidelines |
| Acceptance conditions | Full author registration and author presentation (or prior TPC-approved qualified substitute); registration paid before uploading final publication-ready version | Submission guidelines |
| Originality / concurrent submission | No plagiarism or simultaneous submission to another conference | Submission guidelines |

The inspected pages do **not** specify the full-paper deadline time zone or time of day. Do not label it AoE. They do not give a separate abstract/paper-registration date; the author-list restriction cannot be interpreted as evidence that registration and full-paper deadlines coincide. The `Important Dates` menu points to `/authors`; a guessed `/important-dates` URL returned 404 and is not a source.

No uniform mandatory RF hardware experiment, artifact deposit, supplemental-material requirement or SECON-specific AI disclosure text was found on these four pages. This is a bounded observation, not an exemption from IEEE publication policy or evidence that supplements are accepted. Recheck applicable IEEE AI disclosure and double-submission policy before final submission, with appropriate anonymous wording. Preserve the ICC manuscript as history; preserving a file does not establish whether it was submitted, and concurrent-submission status must be resolved before any future submission action.

The earlier handoff records [EDAS N35491](https://edas.info/N35491). This pass confirms that guidelines require EDAS, but does not independently verify that conference-specific EDAS page or its live registration nodes; no account was opened. Reconfirm the official submission link and live deadline before submitting. Internal target remains 28 November, leaving time for unresolved registration/time-zone details.

## Retrieval fingerprints and exact excerpts

SHA-256 refers to the downloaded HTML response, not a claim that a live site remains unchanged. Full HTML was not added to the source tree; the excerpts below and URLs make the checked rules explicit.

| Page | SHA-256 |
| --- | --- |
| `/call-papers` | `bf2b7586fe729e5fe7b447f1aad6a5be1267ee65263030477321e2c69968d001` |
| `/authors` | `a074c6a7d4b458697fbb62194f7f97da0812be7a2763c4253f94a330c4cb7b43` |
| `/submission-guidelines` | `4285c3930b6f5e413805d4b1db9617cb3078ced3ddf66236ee14237b2168858f` |
| `/` | `436511dd5b7224682da1dca3a54b584d723c4f34b6edff701588b98058061281` |

> “Each submission must be no longer than 9 pages (including all the figures, references, and appendices) and in font size of 10 points.”

> “All submitted papers will be judged based on their quality and relevance through double-blind reviewing, where the identities of the authors are withheld from the reviewers.”

> “Only PDF files will be accepted for the review process, and all submissions must be done through EDAS.”

The first Python `urllib` attempt failed local issuer-certificate validation on this site. The normal system `curl` retrieval succeeded; certificate verification was not disabled. The final PDF check must inspect the actual exported PDF for page count, 10-point IEEE layout, embedded fonts, readable figures, citations, author/affiliation/acknowledgment text and identifying metadata. Successful TeX compilation alone does not satisfy that check.
