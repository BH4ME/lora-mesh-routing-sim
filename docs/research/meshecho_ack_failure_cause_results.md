# MeshEcho reverse-ACK failure-cause screen

Date: 2026-10-04. Status: audited negative exploratory result. This is
unchanged-protocol observation, not a trial of a new algorithm or an ICC
paper result.

## Frozen design and provenance

The preregistered contract is
`docs/research/meshecho_ack_failure_cause_diagnostic_design.md`. It fixes
seed 37000 for mechanical smoke, 37001--37003 for exploration, the 30-s
application deadline, and a necessary exposure gate of at least four
unique deadline-delivered/unACKed flows and at least 10% of all such flows.
The seven source hashes were frozen in `task_plan.md` before smoke and
remained unchanged through exploration. Complete baseline, plain replay,
and passive-observer flow/action/TX checks passed in every seed.

| Split | Report SHA-256 | Complete TX rows | First failed ACK hops |
| --- | --- | ---: | ---: |
| 37000 smoke | `ced7185f00dce7bab73db8d76f6fabbe5aa727285556a2e8eafe23e4a0afd5ed` | 648 | 12 |
| 37001--37003 exploration | `49d8ffecd7bb3e0ff10550eb175be6b8d689ba2b30029c8e53400937ef4a8ca7` | 2018 | 27 |

The report SHA-256 values match their manifests. An independent reviewer
recomputed all 39 failed-hop overlap sets, physical-cause classes, sole-
interferer and intent-commit flags, and remaining-ACK-hop deadline bounds
from the saved TX timelines, with zero discrepancies. The two reports are
under `results/meshecho_ack_causes_*_20261004.{report,manifest}.json`.

## Observations

| Split | Delivered/unACKed flows | Capture | Half-duplex | No-interference probabilistic | Broad sole same-flow overlap | Strict intent-timing opportunity |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 37000 smoke | 10 | 9 | 0 | 3 | 1 | 0 |
| 37001--37003 exploration | 24 | 17 | 1 | 9 | 1 | 1 (4.17%) |

Counts of physical failures are ACK attempts, not unique flows. All
exploratory capture interferers were same-flow FLOOD transmissions, but
the proposed intent can only affect a relay after physical decode and
before its FLOOD transmission is committed. Most overlapping FLOODs were
already in flight before first destination delivery or occurred alongside
multiple interferers. The one strict flow (seed 37001, flow 15) is an
optimistic timing opportunity only: actual intent reception, pending
handle availability, cancellation, and source ACK improvement were not
observed.

## Decision

The exploratory 1/24 opportunity misses both fixed necessary conditions:
one is fewer than four unique flows, and 4.17% is below 10%. Reject the
post-delivery `ACK_INTENT`/local-quiet/cancel branch before protocol coding.
Do not tune the intent size or threshold on these seeds or open 35001--
35040 development or 36001--36040 holdout for this rejected mechanism.

This does not rule out every possible reverse-ACK design. It does show
that this locally triggered post-delivery mechanism has too little
demonstrated leverage in the tested workload. ACK timeout at the source
still confounds forward DATA loss with reverse ACK loss. The full
MeshEcho source send/recovery controller has not been rewritten, and the
current ICC manuscript must not be promoted as if it had.
