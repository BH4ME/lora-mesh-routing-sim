# MeshEcho-CLAR frozen development result

Date: 2026-10-04. Status: failed development hypothesis; holdout unopened.
This is simulation evidence, not an ICC acceptance estimate, a production
firmware comparison, or a hardware result.

## Frozen design and provenance

The protocol contract in `meshecho_clar_design.md` fixed four arms before
population results: CLAR, same-beacon/no-cancel, on-path ACK repeat, and
plain F/R single ACK. The primary comparison required CLAR to exceed *both*
repeat and plain F/R in seed-paired deadline source-ACK PDR, with each
two-sided nominal 95% lower CI above zero and relative complete-network
TX-airtime upper CI below +10%. The exposure gate required at least 20
eligible candidate events in at least ten seeds. Seed 8000 was a custom
non-evaluable smoke. The development run used exactly 8001--8020, the
recurring-fading case, 600-s traffic generation, 630-s TX-start cost window,
and 30-s application ACK deadline. The 4001--4040 holdout was not opened.

The frozen manifest is
`results/meshecho_clar_research_recurring_fading_dev_20261004.manifest.json`.
It records 80 runs, 797 scheduled unicasts per arm, and the original source
hashes. Independent SHA-256 checks match all four source inputs and all four
data artifacts. Within each seed the four arms have identical case and
scheduled-application-trace hashes and the same flow count. The run-source
hashes were:

| Frozen input | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `ee5749b401284b7a37647e50f0aadb7460716b28c6667ecd3bdd4aa76a5bc8a1` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `aafe1fb4c1ebdf3f5f8181a01dc5ea476b544283394659933b6c3929f6b68a88` |
| `docs/research/meshecho_clar_design.md` | `e2b56b94ba18d8b72a45171b66910345ce2ee4430031ddcd615d56b292a5078c` |

## Paired outcomes

| Arm | Deadline source ACKs | Deadline destination deliveries | Complete TX airtime, 20 runs |
| --- | ---: | ---: | ---: |
| CLAR | 518/797 | 598/797 | 622.113 s |
| Same-beacon/no-cancel | 519/797 | 595/797 | 843.355 s |
| On-path ACK repeat | 528/797 | 619/797 | 599.637 s |
| Plain F/R single ACK | 422/797 | 593/797 | 757.841 s |

| CLAR minus comparator | Paired ACK-PDR difference, nominal 95% CI | Relative full-airtime difference, nominal 95% CI | Primary pair gate |
| --- | ---: | ---: | --- |
| Same-beacon/no-cancel | -0.0069 [-0.0508,+0.0370] | -24.0% [-32.9%,-15.2%] | Diagnostic only |
| On-path ACK repeat | -0.0161 [-0.0547,+0.0226] | +7.7% [-5.5%,+21.0%] | **Fail** |
| Plain F/R single ACK | +0.1191 [+0.0665,+0.1718] | -14.3% [-24.9%,-3.7%] | Pass |

The predeclared joint gate is **false**. Candidate exposure passes with
4091 locally eligible events across all 20 seeds, but exposure cannot
replace the failed comparison with repeat. The nominal intervals are not
multiplicity-adjusted, and different policy trajectories are closed-loop;
aggregate counts must not be interpreted as per-packet causal effects.

## Mechanism and failure diagnosis

CLAR logged 3192 source-DONE cancellations, 273 ACK-continuation
cancellations, and 626 off-path repair starts. Its same-beacon/no-cancel
arm logged 3830 repair starts and cost 221.242 s more aggregate airtime.
This supports a cancellation benefit in the shared simulation model, but
the arms also changed downstream behavior (including 5469 versus 6019
DATA transmissions). Do not assign the entire airtime difference to
individual canceled timers. The 10-byte DONE, collisions, energy, and
complete TX airtime were charged through the normal packet path.

Against repeat, CLAR had 1597 versus 1137 ACK-hop transmissions, 626
off-path repair starts versus 135 repeat starts, 1739 versus 1265 control
transmissions, and 22.476 s more aggregate airtime. CLAR's F ACKs were
142 (104 initial, 38 repaired), versus repeat's 128 (92 initial, 36
repeated). That F-stage difference did not yield a whole-workflow gain:
CLAR's R ACKs were 376 versus 400 for repeat, and destination deliveries
were 598 versus 619. The matched both-F-flow subset (146 flows) had 103
CLAR ACKs versus 97 repeat ACKs, but the matched both-R subset (550 flows)
had 346 versus 362. These are descriptive conditioned subsets, not a
randomized per-flow mechanism estimate.

Among CLAR's 279 unACKed flows, 199 had no destination DATA delivery:
196 were R flows and three were F flows. The other 80 were delivered but
unACKed (30 R, 50 F). Only 13 of the 50 delivered-but-unACKed F flows
had any source-next candidate eligible to repair; 23 had any eligible
candidate. A source-initiated ACK query is therefore not a demonstrated
large rescue opportunity. The dominant observed gap is failed R DATA
delivery, which ACK-only CLAR cannot repair.

The source schedules its existing 15-s ACK guard at the actual source
DATA/FLOOD transmission start. All 279 observed CLAR ACK misses generated
a guard timeout, with at least 14.917 s before the 30-s flow deadline.
That source-local time budget makes a *new* same-flow R recovery hypothesis
plausible, but the frozen CLAR logs cannot estimate its reliability,
airtime, duplicate-delivery, or interference effect.

## Integrity note and decision

A post-run audit found that the validator omitted the legitimate repeat-arm
`source-done-repeat` cancellation reason (84 events) from its allowlist.
A test-first, validator-only correction changed the current runner SHA-256
to `e174cf2eec896c63a2d91ffcae41b2d45168578e62c845b2a4f2e7b2b51d3b57`.
The frozen artifacts and their original run-source hashes above were not
changed or rerun. With the original source-hash map supplied, validation
now passes all artifact/action checks and stops at the intended error:
`CLAR development joint primary gate did not pass`. Complete post-fix
regression: 402 passed, one skipped.

Stop CLAR as a proposed positive ICC core algorithm. Do not open its
holdout, retune against 8001--8020, or promote the current manuscript as
if CLAR beat the repeat control. A successor requires a separately frozen
device-local mechanism, an independent development split, matched simple
controls, and an unchanged holdout. Keep this negative cohort visible as
algorithm-selection history, not independent successor validation.
