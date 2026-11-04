# MeshEcho-DHR frozen development result

Date: 2026-10-04. Decision: **stop positive DHR claims**. The prospective
joint gate in `meshecho_dhr_design.md` failed. This report records one
development run, not an ICC acceptance estimate or hardware result.

## Provenance and pairing

The four-arm `dhr-development` matrix used exactly seeds 9001--9020,
the frozen `recurring_fading` case, 600-s application generation, a 30-s
per-flow ACK deadline, and full-packet TX airtime for transmissions starting
by 630 s. Each seed has all four arms on the same case and scheduled traffic;
the manifest has 80 runs and 803 scheduled unicasts per arm. The four source
hashes match the pre-smoke freeze in `task_plan.md`. Independent `shasum`
checks match all four manifest artifact hashes. The development manifest's
validator passes source, artifact, pairing, flow, event, and aggregate-count
checks, then stops at `DHR development joint primary gate did not pass`.

| Input | Frozen SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `94f4c428afd022b86c8d3c51a6da1a32fe113e7b17e0615540915964be5a9299` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `tools/run_sr_experiment.py` | `c9f81a0d33effb362fb489d884bb816e6a7052fa21da4084c7e749fd853faf15` |
| `docs/research/meshecho_dhr_design.md` | `862e7f307db6ac992235e90c34bfb7e3793e69d3168ee91d133d1db636a26d59` |

| Development artifact | SHA-256 |
| --- | --- |
| runs CSV | `6b45b8ac5f39c6672dfdd243dbb8bfa4b4158f7b7b3cfcf154946be0a4c396b2` |
| paired CSV | `fad5c385dcf04800e9b14281cd6de01836ba6318857fa6e43ff833bbe912f147` |
| flows JSONL | `c0a3fd1dda32de8bbf26f37b96452ba2549cbeab953016699e5e9f4bed9a54cb` |
| actions JSONL | `70614ee47f20fe28faa5704b7a081858e10ece8b80243ddd7c8e45e6274b212f` |

## Primary comparison

The following effects are the mean of seed-paired differences, with the
runner's nominal two-sided 95% paired-t intervals. ACK-PDR is by each
flow's original 30-s deadline; airtime is complete-network TX ToA.

| Comparator | DHR minus comparator ACK-PDR | Relative TX airtime | Gate |
| --- | ---: | ---: | --- |
| No same-flow recovery | +0.0924 [0.0336, 0.1512] | +16.7% [10.0%, 23.4%] | Descriptive control |
| Fixed R repeat | +0.0227 [-0.0179, 0.0632] | +16.4% [7.8%, 25.0%] | Fail |
| Fixed F fallback | +0.0005 [-0.0515, 0.0524] | -13.9% [-21.4%, -6.4%] | Fail |

Against fixed R repeat, the nominal ACK-PDR lower bound is below zero and
the airtime upper bound exceeds the prespecified +10% ceiling. Against
fixed F fallback, the nominal ACK-PDR lower bound is below the -0.02
noninferiority margin, despite lower airtime. Both mandatory primary
comparisons fail. The exposure gate passes: DHR had 175 admitted guards
in 20 seeds, 109 physical R rescues in 20 seeds, and 66 physical F rescues
in 19 seeds. Exposure cannot override failed outcomes.

Raw pooled totals are descriptive, not the paired estimand: DHR 578/803
deadline ACKs, 736/803 destination deliveries, and 1008.662 s total TX
airtime; no recovery 497/803, 651/803, 873.498 s; fixed R 557/803,
703/803, 881.451 s; fixed F 570/803, 799/803, 1202.994 s. Fixed F
delivered substantially more DATA to destinations than DHR, even though
their source-ACK totals are similar; the paper must not conflate them.

## Interpretation and stop rule

DHR's fixed 120-s ACK-freshness/miss threshold is a source-local heuristic,
not a derived optimal controller. It spent more airtime than fixed R
without a statistically resolved ACK advantage, and it did not establish
noninferiority to fixed F. These results do not justify replacing the ICC
manuscript's core with DHR or claiming a higher acceptance probability.
Do not tune DHR on seeds 9001--9020, rerun them as independent evidence,
open the 10001--10040 holdout, or advance the paper/PDF, VERSION, GitHub,
or EDAS on these results.

A successor should be a distinct, prior-art-aware mechanism, not a new
threshold fitted to this cohort. It needs a formal decision objective and
source-observable evidence for choosing recovery action, explicit deadline
and full-network airtime costs, same-trigger simple controls, public-packet
safety tests, and a new named seed cohort. Simulation calibration or small
hardware measurements remain separate evidence requirements for a strong
ICC systems claim.
