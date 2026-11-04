# SECON formal raw-evidence independent review

Status: **passed after correcting a reviewer-only ACK-count assertion**. Verified 2026-11-04T09:45:19.374240+00:00. This is raw-data integrity review, not a claim of protocol superiority or complete paper delivery.

- Full immutable plan `5f1a12fe49bf7fc0ea32cc048a3595ed0bd290811f952a47c5a33b0cded2cbb0`:760/760 runs; snapshot `63e3809a1929e2bf1816c3192b7a9a4096aac90a0a85ac8196b72996c57ccdee`; tested2.1.29. All original completion records are present with one completed attempt and no failed attempts.
- Independent script reads raw JSONL/CSV/manifests and source inventory without importing the repository or running a simulator. It performed 77 types of checks and 49,592,170 check invocations, including166 frozen inputs, planned keys, full artifact hashes, physical request/TX/RX/ACK joins, deadlines, denominators, complete airtime, pairing and resolved component parameters.
- Across all760 arm/case/seed run instances: 51,145 scheduled flow instances, 23,836 timely accepted ACKs, 32,925 timely destination deliveries, 574,959 physical transmissions, 11,499,180 receiver opportunities and 51774.079744000s summed airtime. These aggregate counts include repeated common workloads across arms/regimes and are not independent sample sizes; inference remains20 paired seeds per case.
- All source-stage bounds, no-repeat/no-recovery physical-stage exclusions and ACK-cancel-off checks pass. The no-repeat check independently reconstructs marked DATA/ACK wire lengths and LoRaToA, verifies nominal skipped-slot timing and recovery request/physical-TX ordering, and treats future reservations separately from actual transmissions. 2758 routed-initial no-repeat slot records were reconstructed.
- Common topology/traffic/radio/channel identities match for every paired case, including control arms. Default/matched inputs remain separately identified. Three clean controls differ from their CPR reference only in name and the declared toggle.

## Reviewer assertion correction and retained history

The initial checker incorrectly compared manifest `counts.accepted_acks` to the number of all ACK event rows. Frozen producer code at `tools/run_cpr_experiment.py:730` counts only `accepted=true`, and its audit at line965 uses that same meaning. The complete first pass reported39 discrepancies, all and only this assertion, exactly the39 runs containing rejected ACK events. All other checks passed.

A targeted second pass read all760 ACK JSONL files and manifests, verified their hashes against the unchanged completion hashes from the first pass, and confirmed 23,836 accepted and 78 rejected ACK events. Every manifest count is correct. The simulator, archived data and science specification were not changed; no new simulation or full raw rerun was needed. The reviewer source assertion is fixed and now returns nonzero on discrepancies.

Preserved initial evidence: `secon2027_supervisor_formal_raw_review_initial.py`, original `.log` and `secon2027_supervisor_formal_raw_review.json` (initial status discrepancies). Corrected final evidence: `secon2027_supervisor_formal_ack_count_recheck.json` and **`secon2027_supervisor_formal_raw_review_verified.json`**. The verified report explicitly records the original executed script hash, correction source hash, all760 targeted rechecks and reuse of unaffected original checks; it does not claim the corrected full script was rerun.

## Remaining independent gates

Raw per-run counts and means are available in the verified JSON. Formal paired confidence intervals, realized S1/S2/S3 interpretation gates, paper number/claim mapping, actual anonymous ≤9-page PDF rendering and final recoverable remote publication still require their separate acceptance. Adverse performance must remain in the manuscript.
