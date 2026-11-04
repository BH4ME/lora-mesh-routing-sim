# ICC 2027 core-rewrite evidence map

Date: 2026-10-05. Status: revision architecture only. The separately named
MeshEcho-DBR candidate has public-behavior tests but failed its scientific
go/no-go review before any prospective population run: it is not a selected
paper core. This file authorizes no positive DBR claim in the manuscript.
The current five-page LaTeX/PDF remain version 2.1.26 and still describe
the old calibrated policy.

## Current manuscript boundary

| Source location | Current claim or material | Required treatment after a core rewrite |
| --- | --- | --- |
| `paper/icc2027/icc2027_lora_mesh.tex:14-40` | Title and abstract frame calibrated confidence scoring and 2.1.25 protocol-family numbers. | Replace the method identity, question, and numerical abstract only from new, verified experiment artifacts. Keep an adverse result if it remains. |
| `:47-79` | Introduction presents the old complete policy and three comparison-oriented contributions. | State the new device-local decision rule and its specific improvement claim; separate protocol contribution from evaluation contribution. |
| `:81-95` | Related work covers LoRa mesh and ETX but not the close multipath-response/local-repair predecessors. | Verify and cite directly relevant DSR/AOMDV, opportunistic forwarding, LoRa mesh, and product behavior; avoid a broad first-of-kind claim. |
| `:96-167` | Network model and old RREQ/max-min PRR policy mapping. | Preserve the radio-model description if unchanged. Replace the old algorithm subsection with exact packet fields, per-node bounded state, event/timeout rules, route commitment, and airtime accounting. Retain old SR as a named control where useful. |
| `:169-224` | Conditioned recurring and unconditioned random workloads, seed-paired inference. | Declare fresh development and untouched holdout splits, exact controls, metrics, and exposure gates. Identify old 51--70 and 2001--2020 analyses as exploratory history, not independent validation of a new mechanism. |
| `:226-381` | Tables and figure compare the calibrated policy, stylized Meshtastic/MeshCore, and a score control. | Recompute every table and figure from the new policy's frozen runs. Include the simplest same-budget mechanism control, source-ACK and destination PDR, complete TX airtime/energy, delay, collisions, and mechanism exposure; retain negative comparisons. |
| `:382-447` | TTL sensitivity and scope limitations. | Retain relevant physical/model limitations, explain any failure or narrow operating regime, and distinguish protocol-inspired baselines from firmware measurements. |
| `:448-470` | Reproducibility and conclusion name 2.1.26 and old artifacts. | Update only after source/tests/CSV/figure/PDF hashes are verified. Do not present development tuning or inspected old seeds as a new holdout. |

## Required evidence chain

1. Record a separately named core algorithm contract before implementation:
   device-observable inputs, on-wire bytes, bounded state, safety rules,
   deadline behavior, mechanism-specific prediction, and prior-art boundary.
2. Implement a public-behavior vertical slice with a deterministic failure
   and a matched simple control. Validate packet sizes, airtime, energy,
   duplicate delivery, ACK acceptance, and route commit before population
   claims.
3. Freeze fresh development seeds and at least two primary comparators:
   the simple same-trigger/same-feedback alternative and the relevant old
   F/R or SR policy. Preserve identical application traces/configuration
   hashes and record action/flow evidence.
4. If development supports the predeclared claim, open a once-only holdout
   using unchanged source/design hashes. Add random-pair and PHY/load
   robustness; separate selected-pair and unconditioned estimands.
5. Rewrite LaTeX from evidence, compile an ICC-format PDF within the page
   limit, inspect rendered pages, audit citations, and keep author names in
   English (`Zu Gao`, `Zhi Quan`).

The negative LPR 5001--5020 and DPA 6001--6020 development cohorts are
algorithm-selection history, not independent validation. The old paper's
score control already shows no demonstrated max-min advantage. No acceptance
probability follows from these simulations.

## Candidate-specific revision gate: MeshEcho-DBR

The current candidate replaces the old score/threshold controller with a
source-confirmed F/R policy, one destination-observed backup path carried in
a charged FLOOD ACK, and backup-then-F recovery admitted against the original
30-s application deadline. Its 2-s destination collection, 15-s initial R
guard, 2-s backup guard, 120-s backup-age limit, route generations and
actual-radio-start checks are all protocol decisions, not measured gains.
See `meshecho_deadline_backup_core_draft.md` for the unfrozen contract.

The next manuscript revision must satisfy these evidence dependencies:

| Paper element | Evidence before replacement |
| --- | --- |
| Title, abstract, contributions | A prospectively tested DBR-vs-control mechanism with nontrivial physical decision divergence; no first-of-kind claim for alternate routes or local repair. |
| Protocol section and policy table | Verified packet field and hop-byte cost, bounded source/destination state, first accepted ACK and generation semantics, physical-start/deadline admission, and explicit five-arm control mapping. |
| Experiment design | Frozen source/contract/runner/case hashes, saved complete TX and flow/action artifacts, exact seed windows, same-schedule pairing, preregistered primary estimands and no-go gates. |
| Main result table and figure | Fresh development followed by one untouched holdout, with seed-paired all-scheduled-flow source ACK and destination PDR, complete-network airtime and modeled energy; show byte-padded fixed-F, same-path, and DSR-like first-alternate alongside DBR. |
| Mechanism and limitations | Physical backup starts, DBR-versus-first-alternate branch differences, backup age, ACK field bytes, route commits, deadline misses, collisions/queueing, SF/load/random-pair sensitivity, and any adverse result. |
| Related work | Directly verify and cite DSR/AOMDV and close LoRa/ACK-recovery studies; the current bibliography does not yet establish DBR novelty. |

DBR and first-alternate currently make the same backup choice while the
backup is within 120 s; their main branch difference is that age cutoff.
The runner's later provenance review found no new P0/P1 accounting defect,
but mechanical readiness does not cure the missing scientific distinction.
DBR therefore remains NO-GO: do not rebrand the old ICC manuscript around
it or open reserved 44xxx seeds. Redesign the source/feedback/recovery rule
and obtain a separate untouched validation set before any paper-result
replacement.

## Conditional cost-first successor: destination-certified relay

The candidate in `meshecho_destination_certified_backup_screen.md` is not
the rejected source-side DBR probe. It would carry one destination-observed
two-hop alternative in an F ACK, nominate that relay on a later direct R
DATA, and let the relay suppress one early local forward after hearing the
destination ACK. The already inspected 42xxx stock archive offers at most
an 11.7% gross whole-network airtime pool among ACKed direct-R/F-recovery
flows before candidate eligibility or new costs; only 8/131 direct initial
R flows were deadline-unACKed. This motivates an airtime-first hypothesis
with source-ACK noninferiority, not an ACK-PDR uplift claim. The 46xxx
physical exposure screen has not supplied a candidate result.

| Future paper location | Required evidence before rewriting |
| --- | --- |
| Title, abstract, contribution list | A fixed algorithm identity, paired whole-network airtime reduction with a prespecified interval, source-ACK noninferiority, and an untouched holdout. Do not state the old 42xxx pool as measured saving. |
| Related work | Directly cite and compare IOMC (DOI 10.3390/s23083874), ExOR (10.1145/1080091.1080108), DSR (RFC 4728), AOMDV (10.1002/wcm.432), and LoRa opportunistic/relay work. ACK-gated relay or cached alternate routes alone are established. |
| Protocol/model | Exact ACK/DATA fields and per-hop ToA, F duplicate-collection window, source route generation, nominated-relay local ACK observation, one-shot timer, route/ACK identity, original deadline, capacity/expiry, and no oracle inputs. |
| Experiments | Same traffic/PHY source traces, fixed-2-s F recovery, same-byte no-forward, unconditional same-relay, IOMC-style local/overheard candidate selection with matched budget, and LPR-like controls; predeclare the cost endpoint and ACK noninferiority margin. Identical nominee/timer/ACK-gate and same-eligibility first-alternate arms are parity checks, not superiority targets. |
| Results/figure | Replace every old table/plot from fresh development and untouched holdout CSVs: all-flow source ACK and destination PDR, complete TX airtime/energy, deadline delay, recovery counts, redundant relay starts, collisions, bytes and source/relay state. Show adverse strata. |
| Limits/reproducibility | Keep stylized Meshtastic/MeshCore caveats, physical-model limits, exact seed split and artifact hashes; distinguish simulation from firmware or hardware measurements. |

Do not modify the five-page LaTeX or PDF with hypothetical successor
numbers. If the passive gate fails or the protocol has no advantage over
the IOMC-like/same-information controls, return to algorithm selection
instead of calling the old score policy a rewritten core.

## Current successor screen: first-hop receipt

`meshecho_first_hop_receipt_screen_design.md` prespecifies a passive,
charged first-hop receipt feasibility screen. It asks whether an initial
multihop R first-hop failure leaves enough still-unACKed deadline failures
to justify adding a 17-byte receipt on successful R first hops. Passing
its exposure, all-flow ceiling and airtime gates would **not** establish
an algorithm or paper result; receipt-conditioned early F is itself a
simple prior-art-adjacent control. A future full protocol must beat both
same-receipt and receipt-free fixed-F/early-F/R-repeat controls, disclose
direct-route limitations, and show physical receipt/forwarding effects on
fresh development plus untouched holdout. Until then, keep current ICC
method, numerical abstract, tables, figure and PDF unchanged.
