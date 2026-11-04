# Source ACK-quality exploration: audited numerical NO-GO

Date: 2026-10-04. Status: audited exploratory result, not a validated
signal or a new MeshEcho algorithm. Do not open 43101--43120 from this fit.

## Provenance

The frozen `recurring_fading` 30-s-deadline runner opened exactly seeds
43001--43020 once after the independently audited 43200 mechanical smoke.
The exploration authorization SHA-256 is
`354f9a25619899b8cfc4b7d161ea5014e6867f528af0d35012fb2c26da44cc32`;
the smoke predecessor manifest SHA-256 is
`97513ee5378446836a05e82b4e2ef3618fb1684f55bdc72ddcea3ec0522fefd1`.
The exploration manifest is
`results/meshecho_source_ack_quality_explore_43001_43020_20261004.manifest.json`
(SHA-256 `8ce26a6e6d44d00660934993b1c1e44d881b1be144015de6162b45f0267a6192`).
Its summary and runs SHA-256 values are respectively
`bfb4567df36155b0a3d1edd08ff3533023b84a4181bc15d9824630312f17a4d9`
and `fb9903a16732ffc13dd2ffe186203949c7fcc49e329f6a2f4a284a22d38dd9cd`.

An independent saved-artifact audit checked all 11 frozen source hashes,
the case/permit/predecessor/artifact hashes and sidecar, per-seed and
path-type arithmetic, and saved canonical flow/action/TX digests. The
official `validate_manifest(..., expected_mode="explore", replay=True)`
completed for all 20 seeds with exact stock/passive, both-RNG and strict
replay parity. No validation seed or authorization was opened.

## Exposure and stop

The saved cohort has 866 scheduled flows, 13,343 physical TX, 4,501
actions and 1,163 source ACK decode rows. It has 697 initial R decisions,
all with eligible prior source ACK quality; 508 received an initial R ACK
by the original guard and 189 did not. There were 189 physical later
recovery attempts and 156 accepted later recovery ACKs; exclusions were
zero. Direct routes contribute 140 eligible rows (79 successes, 61 misses)
across 19 seeds; multihop routes contribute 557 (429/128) across 20 seeds.
Thus feature and label support exceed the predeclared exploration minima.

Nevertheless both primary post-interference q and clean-SNR sensitivity
fits are saved as `status: no_go`, `ready_for_validation: false`, reason
`ridge-logistic Newton solver did not converge`. The first failing fit is
the shared M0 baseline in the leave-one-seed-out fold holding out 43001:
669 training rows, 485 successes and 184 misses. This is upstream of q
and is not evidence that q lacks predictive information.

## Numerical diagnosis and decision

A read-only trace found that, near iteration 7, the accepted iterate had
maximum absolute gradient about `2.16e-7`. A full Newton candidate reduced
it to about `2.53e-15`, but absolute loss accumulation reported the
candidate about `1.08e-12` worse at loss near 378. A stable differential
calculation estimated a decrease about `2.76e-15`; the Armijo right-hand
decrease rounded away in binary64. The line search rejected the stationary
full step, accepted near-null steps, and exhausted its 100-iteration limit.
This is an exploratory numerical root-cause diagnosis, not a retroactive
change to the frozen model result.

Keep the official 43xxx result as NO-GO and 43101--43120 sealed. Any
solver amendment must have an independent numerical justification and
red/green synthetic regression, a new frozen source/contract hash, and
fresh prospective exploration and validation seed splits. These inspected
43001--43020 rows may debug software but cannot become a new untouched
confirmation. No ICC method, figure, PDF, VERSION or GitHub claim follows.
