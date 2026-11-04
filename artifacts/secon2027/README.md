# SECON 2027 reproducible evidence

The anonymous review candidate is `paper/secon2027/meshecho-secon2027-anonymous.pdf`. The complete research materials below retain source paths and repository identity; they are separate from the anonymous PDF.

| Package | Transport | Whole SHA-256 |
| --- | --- | --- |
| Complete formal raw evidence,475828160bytes |114 files `formal-v1-raw-evidence.transport4m.tar.gz.part-001` through `114`; ordered index `formal-v1-raw-evidence.transport4m.parts.index.json` | `81776e12501e56945dd8aad6a37bb68e5f6e4b41d66c88ae041e7689e490d067` |
| Final statistics, paper and reviews,9978264bytes |3 files `formal-v1-analysis-paper-2.1.30.tar.gz.part-001` through `003`; ordered index `formal-v1-analysis-paper-2.1.30.parts.index.json` | `d60a67eb549905af087968b3c1ab496851ef78ebf38f8e9be6c26c29584e66e9` |

Each transport part is at most4MiB. Concatenate parts in the listed order and verify the whole hash, then restore using `reproduction_helpers/restore_evidence.py` and the matching `.index.json` into a new empty destination. The raw package contains14667verifiedmembers and the exact frozen2.1.29source; its independent clean restore passed all760runs. The analysis/paper package contains1230verifiedmembers, all complete statistical tables, both paper figure-rendering revisions, finalv3PDF/source, compiler diagnostics and independent reviews. It excludes live checkpoint, acceptance/submission checklists and final publication receipts, which remain ordinary repository documents to avoid recursive self-indexing.

Large raw-event files and large diagnosticJSON reports are distributed inside these recoverable archives. A freshGit checkout therefore needs restoration before commands that inspect those individual files. Standalone paper source and figures are also committed directly. `docs/reproducibility/secon2027_reproduce.md` gives exact saved-source audit, analysis and figure commands. `formal-v1-raw-evidence.transport-history.json` preserves the original local45MiBtransport commit, original mapping and reason for moving to smaller parts; the gzip and scientific evidence were not changed.

The fixed formal plan was simulated on2.1.29. The delivery release2.1.30 adds post-simulation presentation/reproduction tools and metadata; it does not relabel formal results or imply a performance improvement. EarlierP0/pilot packages and the failedpilot-v1record remain available alongside these final packages. No RF-device validation or EDASsubmission is claimed.
