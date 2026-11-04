# Source-local R-ACK risk signal gate

Date: 2026-10-04. Status: **frozen observational design before diagnostic
implementation**. This is an exploratory screen of already-opened traces,
not a new MeshEcho algorithm, a counterfactual action comparison, an ICC
result, or evidence of novelty. The shared planning files are maintained by
the parent task; this bounded subtask records its design and results here.

## Question and cohort

Among flows whose **initial source decision was R** under the fixed-2-s
FLOOD-ACK policy, do source-visible prior R ACK misses and confirmed-path
hop count predict failure to receive the initial R ACK by its 15-s guard?
Does hop count add out-of-seed predictive information beyond a simple
one-prior-miss rule? Last accepted pair ACK age is a predeclared secondary
feature. This asks whether a source decision signal exists under the newer
ACK contract. It cannot tell which alternative action would work.

Use exactly seeds 38001--38020 of the existing `recurring_fading` 50-node
exploration, only protocol `meshecho-dhr-flood-ack-delay`. No simulation,
replay, new seeds, or protocol behavior change is part of this screen. The
source provenance is the archived manifest, not today's modified source
tree. The diagnostic must reject a manifest with a different seed list,
case, policy pair, 30-s application deadline, 2-s FLOOD ACK delay, or frozen
source-hash map. It must verify byte SHA-256 of each used saved artifact.

Frozen prefix: `results/meshecho_delayed_ack_control_explore_38001_38020_20261004`.

| Input | Frozen SHA-256 |
| --- | --- |
| `manifest.json` | `2164ac0ad4850e6be52a55b0af62893a25cd8e029e61b442a65c7bbf6c7608d7` |
| `actions.jsonl` | `48fead601fb04e430f23af6c92be988b030b4cc8a0e79cc2b714030b32aff90b` |
| `flows.jsonl` | `a90a698ab516866d1fc58dc7ecc40ec668a89f7db0837e805ea309c1f806a0e7` |
| `tx.jsonl` | `23502d73584923bc10c107a8553d288b7a669f34129ca46953cdffa4821b6413` |

Frozen source hashes in that manifest (historical artifacts; do not demand
that today's edited worktree match them):

| Source | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `cfc7e36b7c2c78096eaefaa27b49f70b877e4d43fa76fbaef6d34d5b16d2d383` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `8dfdb0fdb487144923e1854f803c76f7302d7b4743081a5b3fbfb9d493c74508` |
| `tools/run_delayed_ack_control.py` | `566f593fbfa07b8459ebcebbb101ff8a1cab170a09c819b4a7b433e603427108` |
| `docs/research/meshecho_dhr_design.md` | `862e7f307db6ac992235e90c34bfb7e3793e69d3168ee91d133d1db636a26d59` |
| `docs/research/meshecho_delayed_ack_control_design.md` | `86396835b850d9dfd7fc5753acb414a5c12208aafba1e9602fe0dca93c1d8441` |
| `tests/test_meshecho_dhr.py` | `0f6825b1bae3222a1bd6a2275f515887087600f27d055de7cf9b8e0e31d1d7b8` |
| `tests/test_delayed_flood_ack_control.py` | `ff0a75b45617a92883d2665549c70d2c0f1598f096077194abef644b1a344bda` |
| `tests/test_delayed_ack_control_runner.py` | `742e4134d8f54e5d00708840e2f2694746b9671fde4471dc3e051c96ce814852` |

## Flow and time contract

Join rows by `(seed, protocol, flow_id)`. Require exactly one initial
`decision=R`, one matching source-origin `DATA` physical TX with no
`repair_index`, and one flow record per included flow. Do not classify
an initial D decision that later falls back to R as initial R. Require the
physical R start to be at or after the application enqueue and the original
deadline to equal enqueue plus 30 s. Its source path gives hop count.

At **strictly before** that physical R TX start, reconstruct only same-source,
same-destination local events: prior initial-R decisions, their source ACK
timeouts, accepted source ACKs, and route commits. Current/future ACKs,
destination decode/delivery, PHY success, and later repairs are forbidden
inputs. `prior_r_miss=1` when the latest *earlier* initial-R flow in the
current committed-route generation has timed out without a subsequently
accepted unmarked R ACK; a new accepted F/recovery-F route commit clears
that history. `last_pair_ack_age_s` is elapsed time since the last accepted
ACK for that pair, irrespective of path; record missing age explicitly.
At exact TX-start ties, ignore the event conservatively to avoid relying
on an ambiguous cross-file event order. The current R path/hop count is
already known to the source at its physical start.

Label `initial_r_ack_by_guard=1` only if an accepted
`dhr_source_ack_rx` action with `repair_index=null` for that flow occurs at
or before both `R_tx_start+15 s` and its **original** application deadline.
Otherwise label zero. In particular a final `flows.acked_at` caused by
the marker-2 recovery FLOOD is **not** an initial-R success. Validate any
positive label against the saved flow's first ACK time. A guard event is
not itself proof of DATA loss. Keep the denominator all initial-R physical
starts; report separately any late or missing-start exclusions as data
quality faults rather than quietly dropping them.

The archived action log has 613 initial-R decisions and 74 initial-D
decisions, whereas the final flow table shows 615 `source_action=R` and
72 `D-candidate`: two initial-D flows later fell back to R. This screen's
strict initial-decision denominator is therefore **613**, not 615.

## Frozen analysis and stop rule

Compare three source-visible risk scores for `Y=1` meaning **no initial R
ACK by guard**: `M0` stratifies by prior miss (two cells); `M1` adds
`one_hop=(hops==1)` (four cells); `M2` adds
`old_ack=(last_pair_ack_age_s>=120 s or missing)` (eight cells). The 120-s
cut is the existing DHR freshness constant, not chosen from this screen.
For each held-out seed, fit each cell probability on the other 19 seeds
using `(failures+1)/(records+2)`; score all test rows by squared-error
Brier loss. Report the equal-seed mean Brier and paired 95% t interval for
`M0-M1` and `M1-M2` using the 20 per-seed differences. This leave-one-seed-
out design also leaves out that seed's generated source-destination pairs.
Report all cell N, number of contributing seeds, failure count and rate.

An **actionable-risk prerequisite**, not an algorithm GO, requires: all
four `M1` cells have at least 20 records and eight contributing seeds;
`M1` improves `M0` mean Brier by at least 0.005 with the paired 95% lower
bound above zero; and the one-hop minus multihop failure rate is positive
within each prior-miss stratum. Otherwise this source-only risk direction
is no-go under this screen. `M2` is independently supported only if all
eight cells have at least 20 records/eight seeds and its incremental mean
Brier gain is at least 0.005 with lower bound above zero; otherwise age
adds no demonstrated signal. These arbitrary internal thresholds were
fixed before looking at this diagnostic's outcomes; they are not ICC rules.

Even a passing risk screen predicts only the *observed R action* under a
policy-selected initial-R cohort. It does not identify F/R-repeat/F-rescue
counterfactuals, delivery of DATA after a lost ACK, whole-network airtime
saved by switching, or an original research contribution. The older
34001--34005 four-branch screen used a different ACK contract and cannot
fill that gap. A later algorithm would still need a fresh matched
same-contract action experiment and beat fixed F, fixed R, one-miss F,
R-to-F, R-to-R, fixed-2-s single ACK and equal-budget repeat, with separate
deadline source ACK, destination delivery and whole-network airtime gates.

## Frozen-artifact screen result

The implemented read-only diagnostic verified the frozen manifest, all
three used artifact byte hashes and the historical source-hash map. Across
20 seeds it found 613 initial-R decisions with physical starts. Exactly
449 had an accepted unmarked R ACK by the 15-s guard and original 30-s
deadline; 164 did not. A marker-2 recovery-F ACK never changes that
initial-R label. The two initial-D-to-R fallbacks are excluded as designed.

| Prior R miss | Confirmed path | N / seeds | Initial R no-ACK by guard |
| --- | --- | ---: | ---: |
| No | Multihop | 461 / 20 | 90/461 (19.5%) |
| No | One hop | 125 / 19 | 61/125 (48.8%) |
| Yes | Multihop | 19 / 16 | 9/19 (47.4%) |
| Yes | One hop | 8 / 7 | 4/8 (50.0%) |

The 27 prior-miss observations are sparse because accepted recovery-F
route commits clear that source state; these data cannot calibrate a
four-cell action rule. The descriptive one-hop excess is positive in
both miss strata, but the latter has too little support.

Equal-seed leave-one-seed-out Brier scores are 0.19743 (`M0`, prior miss),
0.18589 (`M1`, plus hop), and 0.18563 (`M2`, plus 120-s ACK age). Paired
`M0-M1` gain is +0.01154 with nominal 95% interval [+0.00295, +0.02013].
Paired `M1-M2` gain is +0.00026 [-0.00351, +0.00404]. The **frozen full
actionable-risk prerequisite fails** because the prior-miss/multihop and
prior-miss/one-hop cells have only 19 and eight records, and the latter
spans only seven seeds (versus 20 records/eight seeds required per cell).
The age incremental gate also fails both support and predictive gain.
These are exploratory, nominal intervals on policy-selected R actions,
not corrected multiple tests or estimates of F/R-R/R-F outcomes.

Decision: **NO-GO for a source-only controller claim from this evidence**.
The observed hop signal may motivate a *simple hop-based control* in a
future same-feedback counterfactual experiment, but it is not a new
algorithm or a reason to revise ICC numerical claims now. The current
source-only history cannot distinguish lost forward DATA from lost
reverse ACK, and the saved traces do not reveal which different action
would have improved source confirmation, delivery, and network airtime.

## Post-screen audit correction

An independent review found that the first diagnostic version ended
feature history at physical R TX start, although the old SR policy chose
R at application enqueue. The QC revision now ends source-history
features and measures last-ACK age at the original `decision` event;
actual TX start still anchors the 15-s guard label. It also rejects an
R physical start after the original 30-s deadline. Only one archived R
start lagged its decision (seed 38016, flow 10, by 0.086120 s), with no
same-pair event in that gap; no archived R started after its deadline.
The archived screen's cell assignments, Brier results and NO-GO are
unchanged. A future policy that chooses at physical start would need a
tested pre-start decision hook; this screen does not assume one exists.
