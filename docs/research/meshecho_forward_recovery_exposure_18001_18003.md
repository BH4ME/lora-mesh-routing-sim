# Fixed-F forward-recovery exposure: exploratory seeds 18001--18003

Date: 2026-10-04. Status: passive diagnostic, not a new protocol result or
counterfactual flood-radius experiment. The earlier `...20261004.json` is an
intermediate output; the final artifact is
`results/forward_recovery_exposure_18001_18003_20261004_v2.json` with SHA-256
`89e67a1f58bb258ed6c424b0564576871e7c95f943623743dfce9d085908c5b2`.
The JSON lives in ignored `results/` and was not used to update the ICC paper.

## Replay and provenance

The unchanged `meshecho-dhr-flood` control ran the frozen `recurring_fading`
case at fresh exploratory seeds 18001--18003, with 600 s of application
generation, a 30-s original per-flow deadline, and all TXs starting by 630 s
charged at their complete packet ToA. The diagnostic made three runs per
seed: the existing uninstrumented `run_one_sr` baseline, a plain
`RecordingSimulator`, and a passive `try_receive` observer. Each seed exactly
matched the baseline's scheduled application trace, all per-flow enqueue,
destination-delivery and source-ACK timestamps, source actions, every protocol
action event, and raw TX, data-TX, control-TX and collision counts. The plain
and observed full TX histories had identical SHA-256 hashes (packet contents,
sender, start/end times, and TX IDs). The observer's recovery-F destination
decode times also exactly matched protocol receipt events. Source hashes were
unchanged before and after the runs. Seven focused tests pass.

| Seed | Scheduled | Admitted R guards / F starts | First delivery via F | Application trace SHA-256 | Full TX SHA-256 |
| --- | ---: | ---: | ---: | --- | --- |
| 18001 | 39 | 12 / 12 | 11 | `7604800745e7280be62b5f0386ed24ed9b7ce7c73b59c0c367e48e282a37e041` | `4f5bafae999e3310093596e9216dbc7564fc00bef3c7f762305d0fff82df6708` |
| 18002 | 38 | 5 / 5 | 5 | `f0a868cd5583800192edde4832b5da591ca290749ebb1db11c86f0fa73fbfee5` | `d57b3f40ab585f7b6d725bfb6002e84d31eb14a95b3aa7ac1e1e9e03393b8a50` |
| 18003 | 30 | 11 / 11 | 10 | `03fd88b1f604d7a9f92da5f295afeec313fdb0a2cf978bfac896cf7ea3b15f62` | `b78606d6d1fde73d5a7174960d85ea957688a5cea2eeec8e71b4a664b70c1815` |

| Source | SHA-256 |
| --- | --- |
| `lora_mesh_sim.py` | `41626c2d559088f00f2758edc782b31649359bb3e26afdc199d7be6803f70f45` |
| `tools/run_sr_experiment.py` | `ac12adf568714e766cff2efd67b1ba2ab6d1fc9ca4530cdd5f195e3d7f3c21b7` |
| `tools/run_fair_multihop_probe.py` | `0fce2adbf1ec610276618ae2d1f17ee8a5adb4511d316c461ec2f2a1142f8b1e` |
| `docs/research/meshecho_dhr_design.md` | `862e7f307db6ac992235e90c34bfb7e3793e69d3168ee91d133d1db636a26d59` |
| `tools/diagnose_forward_recovery_exposure.py` | `bcd218d6da3d39446906d6b9d9d7b373ccc83288a5db94a6b43858bece749c18` |
| `tests/test_forward_recovery_exposure.py` | `cc22067177777774813e7b19b23d54a14c4e021948ba1e2ebdcb20f9d3fe6a9b` |

## Forward exposure and paths

There were 107 scheduled unicasts and 28 admitted initial-R ACK timeouts.
All 28 launched a recovery F, and all 28 had at least one physical recovery-F
decode at the destination within the original deadline. Two initial routed
DATA copies had reached the destination before their source guard, while 26
flows were first delivered by recovery F. Only 13 of the 28 admitted flows
received a source ACK by the original deadline; destination arrival and source
ACK are distinct endpoints. Initial confirmed source-route lengths for the 28
flows were 15 one-hop, nine two-hop, and four three-hop. Guard deadline slack
was 14.993--15.000 s (median 15.000 s); at the first F destination decode it
was 12.763--14.908 s (median 14.280 s).

For the 26 F-first deliveries, the difference between the first decoded F
path's hop count and the source-known initial confirmed R path was:

| Initial R hops | Shorter F path | Same | F +1 hop | F +2 or more | F-first total |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0 | 2 | 9 | 2 | 13 |
| 2 | 6 | 3 | 0 | 0 | 9 |
| 3 | 3 | 1 | 0 | 0 | 4 |
| Total | 9 | 6 | 9 | 2 | 26 |

The 80 physical recovery-F destination decodes had path lengths of one hop
(11), two (39), three (23), and four (7). The first F deliveries had path
lengths one (9), two (14), and three (3). Eleven of 26 F-first deliveries
used a longer first path than the initial confirmed R path; none of those
eleven had any *observed, timely* F decode at or below that initial hop count
under this unchanged full-flood run. Thus a retrospective path filter capped
at the initial R hop count covers at most 15 of these 26 observed F-first
flows. This is a coverage warning about the observed trace, **not** an
estimate or mathematical bound on capped-flood delivery: a real TTL change
alters contention, queueing, and the set of paths that can decode.

## Charged recovery-F airtime

Recovery F produced 693 complete-packet TX starts, 28 at sources and 665 at
relays, totaling 67.690 s of full-network TX ToA. By path depth at the
transmitting node:

| Depth from source | TX starts | Full TX ToA (s) | Relay TX starts after first destination delivery | Their full ToA (s) |
| ---: | ---: | ---: | ---: | ---: |
| 0 (source) | 28 | 2.588 | 0 | 0 |
| 1 | 618 | 60.277 | 319 | 31.114 |
| 2 | 38 | 3.901 | 34 | 3.490 |
| 3 | 9 | 0.924 | 9 | 0.924 |
| Total | 693 | 67.690 | 362 | 35.528 |

First-depth relays account for about 89% of recovery-F TX airtime. About
54.6% of relay recovery-F airtime belongs to transmissions that *started*
after the first destination delivery of that same flow. This is measured
after-the-fact; those relays had no free global completion signal, and some
forwarding may already have been queued. It is not a realizable cancellation
saving without a separately specified and charged feedback/control mechanism.

## Decision boundary

Do not replace full F with `TTL = initial confirmed R hop count` on this
evidence. The observed shorter-radius path coverage misses eleven of 26
F-first flows, while most charged airtime is at first-depth relays rather
than deep expansion. A candidate must specify source/relay-observable state,
packet overhead, ACK deadline and full-network airtime accounting, then face
same-trigger fixed-TTL and full-F controls on a new cohort. These three
exploratory seeds are not DHR/BAR development or holdout evidence and do not
support an ICC paper claim, hardware claim, or acceptance-probability estimate.
