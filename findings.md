# Findings

## Current Evidence

- The original 50-node, 3000 m, SF9 matrix is link-quality saturated: direct
  PRR is essentially one and almost all cached routes are one hop.
- Fixed repeated source-destination pairs favor route-cache reuse, so that
  matrix is useful as a cache-efficiency/contestion case, not a neutral
  multi-hop benchmark.
- The ten-seed random-pair probe uses an 18 km square, SF7, random pairs,
  mixed traffic at 4 flows/min, and independent channel-reception randomness.
- In that probe, MeshEcho/CALM has ACK PDR `0.413` and airtime `97.5 s`, while
  source-route caching has ACK PDR `0.456` and airtime `139.5 s`.
- The controlled route-conflict experiment supports a narrower mechanism claim:
  confidence helps when the shorter route has a materially weaker hop, but not
  under null, moderate, or reverse controls.
- Smart-CALM has extra timeout retry/fallback behavior, so its gains cannot be
  attributed to confidence ranking alone.
- The connected-pair diagnostic shows that a shared graph-level path does not
  guarantee successful route discovery under broadcast contention. In the
  50-node/15 km/0.5 flows-min case, MeshCore route-discovery success was only
  `0.063`; a 20-seed single-flow check was still only `0.050`.
- The fairness probe now reports route-discovery success and RREP/RREQ
  transmission ratios, and supports `--smart-max-timeout-retries 0` for a
  one-shot budget-matched comparison.
- `--independent-rng-streams` is now passed through `run_one()` and the ICC
  script defaults to it for fresh matrices. It reduces random-stream coupling,
  but is not event-by-event common random numbers.
- An exploratory, unregistered area scan found that 12 km and 14 km settings
  produce non-degenerate direct-link PRR distributions, but random-pair
  traffic still yields only about 6% and 4% MeshCore multi-hop cached routes,
  respectively. These scans are calibration evidence only and are not used as
  headline paper results.
- A 12 km connected-pair run makes the multi-hop fraction clearer, but MeshCore
  route-discovery success falls to about 0.21 while MeshEcho/Smart-CALM remains
  above about 0.61. This confirms that pair selection and route discovery must
  be treated as separate fairness dimensions; the result is not suitable as a
  neutral headline comparison.
- The connected-pair stress runs also contain a route-reply timing asymmetry:
  MeshCore-like replies immediately when the destination first receives an
  RREQ, while MeshEcho waits for candidate collection before sending its RREP.
  This is useful to disclose because it can affect route-discovery success in
  collision-limited floods.

## Paper Positioning

The defensible conclusion is a preliminary reliability-airtime tradeoff under
explicitly stated workload and recovery budgets. The paper must not claim
universal superiority, calibrated deployment performance, or an average
confidence-ranking benefit in arbitrary topologies.

## Publish Scope Candidate

Related files include the ICCT LaTeX/PDF, version metadata, fairness reports,
the random-pair probe script and CSV, the simulator RNG fix, its regression
test, and the ICC experiment documentation. Generated auxiliary LaTeX files,
local sessions, caches, and unrelated deliverables should remain unstaged.

## Release State

- The intended release for this revision is repository version `2.1.11`;
  firmware identity remains `meshecho-firmware-v2.1.2`.
- The paper source and release metadata are already updated in the worktree.
- The PDF has now been compiled and visually inspected successfully. It is
  8 pages, PDF 1.5, with no unresolved reference warnings.
- Final validation passed: 45 Python tests, Python compilation, shell syntax,
  and `git diff --check`.
- The remaining gates are selective staging, commit/push, and remote PR
  verification.

## Verification Checkpoint - 2026-09-04

- Final root PDF SHA-256:
  `b822940c36b13a084538691b526a2b72c0d32463c67ff4772e76937fa4ab9b9a`.
- The root PDF is byte-identical to the `build-2_1_11` output.
- The existing draft PR is still titled for `2.1.9`; after pushing the
  `2.1.11` commit, update its title and body.
- Do not stage generated LaTeX auxiliaries, rendered page images, `.venv-fig`,
  `.playwright-cli`, `tmp`, course artifacts, or unrelated documents.
