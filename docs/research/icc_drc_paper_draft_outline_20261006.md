# ICC 2027 DRC paper rewrite template

Date: 2026-10-06
Status: planning template only; no TeX, VERSION, GitHub, or EDAS change.
Scope: a holdout-gated rewrite plan for `paper/icc2027/icc2027_lora_mesh.tex`.

## 0. Evidence guardrail

The current manuscript is the version-2.1.26 report of the old calibrated
max-min-PRR policy. It is not a DRC manuscript. The current DRC design has not
earned permission to replace it: the recorded passive-exposure screen found no
reserve-caused initial-F decisions, while the proposed development gate needs
at least 20. No DRC result, effect size, acceptance statement, or novelty claim
may be filled into this template until all of the following are true:

1. Packet/state tests and the independent artifact audit pass.
2. Source, runner, contract, tests, radio/case configuration, and hashes are
   frozen before development.
3. Development is run on its predeclared seeds and passes every joint gate,
   including the mechanism-exposure floor.
4. The unchanged-hash, once-only holdout is opened only after development
   passes, and its raw artifacts independently recompute the reported metrics.
5. The holdout does not trigger a positive claim if any declared gate fails or
   if the mechanism exposure is too sparse; the paper must then report a no-go
   or inconclusive result.

The old 2.1.26 CSVs and the current protocol-family comparison are historical
context only. They must never be relabeled as DRC evidence.

## 1. Current-to-future section map

The line references below refer to the current file at the time of this audit.
They are a rewrite map, not instructions to edit those lines now.

| Current section | Keep/rewrite after a valid holdout | Required evidence or decision |
| --- | --- | --- |
| Title, `:14` | Rewrite title around the validated DRC controller only after the contribution is supported. | Do not call the method “confidence-aware route selection” if route scoring is no longer the method. |
| Authors, `:16-19` | Reuse author order and affiliation as-is unless the authors explicitly change it. | No algorithm evidence is involved. |
| Abstract, `:23-40` | Replace as one atomic block. | Use only holdout denominators, deadline PDRs, complete TX cost, exposure, and an adverse/negative result if present. No old number may survive by copy-paste. |
| Introduction, `:47-79` | Rewrite problem statement, question, and contributions. | Motivate deadline admission and bounded redundancy under a local-information constraint; distinguish the method from ARQ, flooding, route salvage, and ACKs. State simulation scope. |
| Related Work, `:81-95` | Retain LoRa/mesh background where accurate; add a targeted prior-art boundary. | Cover deadline-aware forwarding/admission, opportunistic forwarding, route salvage/local repair, ACK-gated forwarding, duplicate suppression, and cancellation. Do not claim first invention. |
| Network model, `:96-109` | Reuse PHY/channel equations only after checking that the code and artifacts still match. | Add actual-start scheduling, complete charged bytes/ToA, deadline/cutoff windows, queueing, RX-attempt reasons, and finite state caps. |
| Routing policies, `:111-148` | Replace the MeshEcho subsection with the DRC state machine. Keep old SR/DHR/DCB only as clearly marked context controls. | Define `R_RESERVED`, initial useful `F`, `R_ONLY`, deadline-infeasible, one recovery `F`, ACK validation, route generations, and same-time ordering. |
| `tab:policy`, `:150-167` | Replace with a DRC action/wire table. | Every action, bound, marker, packet byte charge, route/ACK rule, and state limit must match code and packet-byte tests. |
| Experimental design, `:169-224` | Replace post-hoc recurring/random workloads with smoke/development/holdout contract. | Include seed split, trace/topology/radio hashes, original deadline, all-scheduled-flow denominator, drain/cutoff, controls, and estimands. Old 51--70 and 2001--2020 cannot be called untouched DRC holdout. |
| `tab:main` and `tab:paired`, `:233-282` | Recompute from DRC artifacts only. | Report seed-level paired ACK PDR, destination PDR, complete TX airtime/bytes/energy, deadline misses, delay, and control contrasts. |
| Result prose, `:284-321` | Replace with exposure first, effect second. | Report action/path divergence and mechanism counts before interpreting delivery/cost; report adverse outcomes and failed gates. |
| `tab:events` and figure, `:323-380` | Replace pooled discovery/cache diagnostics and old baseline figure. | Use auditable flow/action/TX/RX/ACK/deadline records and a paired-effect or exposure plot. |
| Route-lifetime sensitivity, `:382-392` | Retain only as old-policy context if useful. | It is not a DRC ablation. Add DRC guard/deadline/cost sensitivity only when predeclared and independently sourced. |
| Discussion/limitations, `:394-447` | Rewrite around the validated estimand and finite state. | Preserve simulation-only limitations and no firmware/hardware equivalence. Discuss no-go/inconclusive branches honestly. |
| Reproducibility, `:448-457` | Rewrite last, after artifact audit and PDF verification. | Include final version, Git state, contract/source hashes, runtime, dependencies, seed split, schema, commands, artifact inventory, and figure/PDF hashes. |
| Conclusion, `:459-467` | Replace only from holdout evidence. | A failed gate yields no positive DRC conclusion. |

## 2. Future paper skeleton (placeholders, not manuscript prose)

The following is the intended structure once the evidence gates pass. Bracketed
tokens are mandatory evidence slots; they must be filled from immutable raw
artifacts or removed, never guessed.

### Abstract

1. Problem: LoRa mesh source decisions must trade deadline success against
   airtime under uncertain links and sparse local feedback.
2. Method: MeshEcho-DRC makes a bounded source decision at actual physical TX
   start, optionally reserves one recovery F, and uses ACK-confirmed route state
   plus epoch-safe cancellation.
3. Evaluation: state `[case]`, `[development/holdout seed counts]`,
   `[all-scheduled-flow denominator]`, and matched controls.
4. Results: insert only `[holdout paired ACK/destination effects]`,
   `[complete TX-airtime effect]`, and `[exposure counts]` after recomputation.
5. Qualification: state `[gate pass/fail/inconclusive]` and that this is a
   packet-level simulation, not firmware or hardware validation.

### 1. Introduction

Frame one falsifiable question: does the DRC source policy improve the
reliability/airtime trade-off over same-wire controls under the declared
deadline and workload? Make the contribution list no larger than the evidence:

* a precisely bounded source admission/recovery policy;
* an auditable packet/RX/ACK ledger and matched-control evaluation;
* a seed-paired result including exposure, adverse cases, and limits.

Do not claim that DRC beats Meshtastic or MeshCore firmware. Product-inspired
arms, if retained, belong in a separate context paragraph or panel.

### 2. Related work and novelty boundary

Organize by (a) LoRa multihop routing and airtime, (b) source routing and route
repair, (c) opportunistic/duplicate-suppressed forwarding, (d) ACK and
deadline-aware reliability, and (e) cancellation/forwarding coordination.
Explicitly state which ingredients are prior art and define the narrower
research question: the measured joint behavior of this source deadline reserve
and epoch-safe terminal-ACK FLOOD cancellation in the stated simulator.

### 3. System model and protocol

#### 3.1 Shared radio model

State topology, packet sizes, PHY parameters, path loss/shadowing, PRR,
half-duplex/capture/collision behavior, ToA, energy accounting, queueing, and
the measurement window. Define whether a metric is deadline-censored or
cutoff-censored.

#### 3.2 DRC state and bounded local information

Describe source destination records, active flow records, relay pending-F
records, route generations/expiry, duplicate state, and state-capacity drops.
Separate finite device-local limits from unbounded simulator logs. State the
wire identity and exact byte charge for R-DATA, F, recovery-F marker, and ACK.

#### 3.3 Source action rule

At an actual immediately committable source TX start `t`, with original
deadline `D`, define nominal bounds `B_R(P)`, `B_F0`, and `B_F`. Apply exactly:

1. `R_RESERVED` if a confirmed route plus one admissible recovery F fits.
2. Initial useful-data `F` if the reserve case does not fit but `F` fits.
3. `R_ONLY` if only the confirmed routed packet fits.
4. Deadline-infeasible/no packet otherwise, while retaining the flow in the
   scheduled denominator.

At the reserve guard, allow at most one recovery F and recheck at its actual
physical start. State that the bounds are nominal admission bounds, not
worst-case guarantees against queueing, loss, collision, or interference.

#### 3.4 ACK, route, and cancellation semantics

Define physical ACK decode, flow/request identity, reversed endpoints, loop-free
path and indexed sender checks, marker/epoch validity, deadline inclusion, first
accepted ACK, route-generation update, stale/duplicate rejection, and relay
off-path cancellation. Explicitly distinguish “destination delivered” from
“source ACK accepted.” Explain same-time ACK/deadline/TX ordering.

#### 3.5 Matched controls

Use the frozen control names and definitions in the DRC contract, for example:

| Arm | Deliberate difference |
| --- | --- |
| `drc-afs` | Full DRC source rule plus off-path terminal-ACK cancellation. |
| `drc-nocancel` | Same source rule and shadow records, but no final pending-handle cancellation. |
| `drc-reserve-blind` | Same wire and guard, but no selective reserve admission. |
| `drc-all-f` | Initial useful F whenever its bound fits. |
| `drc-no-rescue` | Same initial decision, but no guard-triggered recovery F. |

Names and exact semantics must be frozen before development. Old SR/DHR/DCB
and protocol-inspired arms are context only, not same-wire causal controls.

### 4. Experimental contract and analysis

Report the smoke seed separately. For the prospective experiment, state the
predeclared development and once-only holdout seeds, case, original deadline,
drain/cutoff, state caps, radio settings, packet trace schema/hash, topology
hashes, and every arm. Use all scheduled unicasts as denominators, including
state-capacity and deadline-infeasible flows. Report seed as the uncertainty
unit; flows within a seed are not independent replicates.

Predeclare primary and secondary estimands:

* ACK PDR by original deadline;
* destination PDR by original deadline;
* complete network TX airtime, bytes, and modeled TX energy;
* capped completion delay, successful-ACK p95, deadline/no-start/spillover;
* collisions, half-duplex/capture/PRR failures;
* action and mechanism exposure (R-reserved, F-first, R-to-F, cancel/start).

Apply the frozen joint gates exactly. Do not retune on development and call
the resulting holdout confirmatory. If an exposure floor is missed, label the
mechanism claim inconclusive even if an aggregate interval looks favorable.

### 5. Results

Use this order:

1. **Evidence integrity:** manifest/hash/audit status, complete arm coverage,
   zero-event seeds, and denominator counts.
2. **Mechanism exposure:** action rates, actual physical starts, recovery
   starts/cancels, route transitions, and invalid-event counts.
3. **Primary effects:** seed means and paired intervals for delivery/cost and
   exact gate decisions.
4. **Diagnostics:** RX failure reasons, queue/no-start, deadline/cutoff
   classification, and flow-level outcomes.
5. **Robustness/context:** only predeclared independent scenarios; retain every
   adverse outcome and label its estimand separately.

Do not pool flows as independent replicates. Do not call a CI crossing zero
“equivalent.” Do not infer a mechanism effect from aggregate PDR if exposure is
absent or packet traces diverge outside the stated control.

### 6. Discussion, limitations, reproducibility, conclusion

Discuss what the holdout supports, what it does not, and any failed or
inconclusive gate. Keep the following limitations explicit: packet-level
simulation, modeled energy, no waveform/antenna/duty-cycle validation, finite
scenario coverage, nominal rather than guaranteed bounds, and no firmware
parity. Finish with a narrow conclusion tied to the declared estimands.

## 3. Old content retirement and reuse matrix

### Must delete or replace as DRC claims

* The old abstract values and denominators (`:23-40`), including calibrated
  max-min-PRR, PRR+fb, recurring 51--70, and random 2001--2020 claims.
* The old max-min score equations and RREQ/RREP/TTL-2 source policy (`:128-148`).
* The old four-row policy table (`:150-167`) as the method definition.
* The post-hoc workload selection and “holdout” framing (`:169-224`).
* Old main/paired/event numbers and the three-protocol bar figure (`:226-380`).
* Route-TTL sensitivity as a DRC ablation (`:382-392`).
* Conclusions that imply a DRC advantage, score novelty, or product comparison.

Existing values may remain only in a clearly separated historical appendix or
context paragraph, with version, policy, seed status, and exploratory status
preserved. They must not share DRC table labels, captions, or abstract claims.

### Reusable with audit and wording changes

* Author block and affiliation.
* General LoRa motivation and correctly cited multihop background.
* Shared PHY equations, if source hashes and packet-byte tests confirm them.
* Definitions separating destination delivery from source-confirmed ACK.
* Seed-paired interval convention, after replacing old denominators and
  correcting the uncertainty unit.
* Simulation-only, modeled-energy, no-firmware/no-hardware limitations.
* Reproducibility/disclosure language, after replacing version and artifact
  inventory with the final audited release.

## 4. Required raw artifacts before filling any slot

The paper must be reproducible from raw records, not only summary metrics.
Every seed/arm must have exactly one manifest and complete records for:

### Flow ledger

`flow_id`, stable application ordinal, source/destination, enqueue time,
original deadline, action decision time/reason, initial action, route generation,
initial/recovery request IDs, physical starts, first delivery, accepted ACK,
deadline/cutoff labels, capped delay, `state_capacity_drop`,
`deadline_infeasible`, and all-scheduled-flow inclusion.

### Request ledger

`tx_request_id`, request time, stable event ordinal, sender, flow/request ID,
packet kind, marker/path/path index, action, route/generation/guard IDs,
status (`started`, `canceled`, `guard_rejected`, `not_processed_by_cutoff`,
`state_capacity_drop`), reason/time, joined `tx_id`, start/end/ToA, queue wait,
deadline class, and cutoff class. Every started request joins exactly one TX;
unstarted requests cannot disappear at drain.

### Transmission ledger

`tx_id`, request ID, packet class, physical sender, flow/request ID, repair marker,
full path/path index, exact bytes, ToA, start/end, TX energy, deadline/cutoff
classification, and complete join to flow/action. Include post-deadline TX cost
if it starts within the accounting window.

### RX-attempt ledger

One row per `(tx_id, receiver)` with `rx_attempt_id`, sender/receiver,
flow/request ID, packet class/marker/path, times, signal/SNR/SINR,
interference TX IDs, decoded flag, and reason (`success`, `half_duplex`,
`capture_collision`, `prr_fail`, `self`, or invalid-path). It must allow the
auditor to recompute collision/failure counts and accepted ACK candidates.

### ACK provenance ledger

`ack_event_id`, flow/source/destination, ACK TX ID, physical ACK RX-attempt ID,
reverse path/hop, marker, generation, decode/acceptance time, deadline class,
accepted flag, and rejection reason. Route commits must reference accepted
physical ACKs; destination delivery cannot substitute for an ACK.

### Action/route/audit records

Action state transitions, route commits/expiry/miss streaks/evictions, duplicate
cache capacity/evictions, recovery admission/start/cancel, invalid marker/path
events, zero-event seeds, and independent recomputation outputs.

### Immutable manifest

Schema and contract hashes; `VERSION`; Git revision or explicit dirty marker;
runtime/dependency versions; command; source/runner/test hashes; case/radio/
topology/application-trace hashes; seed split; prerequisite manifest hash;
artifact inventory and record counts; gate status; and figure/PDF source hashes.

## 5. Table and figure replacement specification

### Tables

| Future table | Evidence source | What it must show |
| --- | --- | --- |
| Method/action/wire table | source + packet-byte tests | Actions, admission bounds, guard, ACK epoch, bytes, state caps. |
| Experiment contract | manifest | Smoke/development/holdout split, trace hashes, deadline, PHY, controls, estimands. |
| Primary results | flows + TX + independent recomputation | ACK/destination deadline PDR, complete TX airtime/bytes/energy, delay/misses. |
| Paired effects | seed-level derived CSV | DRC minus each same-wire control with nominal intervals and gate margins. |
| Mechanism exposure | actions + requests + TX + ACK | R-reserved, F-first, R-to-F, starts/cancels, no-start, route/ACK events, zero-event seeds. |
| Diagnostics (space permitting) | RX + ACK provenance | Failure causes, queue wait, spillover, rejected/late ACKs. |

### Figures

Preferred primary figure: two panels of seed-paired DRC-minus-control effects
for ACK PDR, destination PDR, and relative complete TX airtime, with nominal
95% paired intervals and predeclared gate margins. A second, smaller panel may
show action/exposure rates only if the exposure floor passes. A separate context
panel may show old SR or protocol-inspired rows, visibly labeled historical or
exploratory; it must not be the DRC evidence figure.

Every plotted value must point to a source CSV/manifest hash and pass an
independent recomputation check. The current
`figures/fig_baseline_delivery.pdf` and its three-row source CSV cannot be
relabeled as DRC.

## 6. Rewrite and verification checklist

Before editing the TeX after holdout:

- [ ] DRC implementation, ledger, and mechanical smoke are green.
- [ ] Independent audit proves request/start/no-start, TX, RX, ACK, deadline,
      and route joins for every smoke/development/holdout arm.
- [ ] Development manifest and gate decision are immutable.
- [ ] Holdout manifest confirms unchanged hashes and once-only use.
- [ ] All result values in the draft have a raw-artifact source and a
      recomputation test.
- [ ] Negative, adverse, failed-gate, and sparse-exposure outcomes are retained.

After editing:

- [ ] Compile with the ICC/IEEE template; inspect page count, overfull boxes,
      fonts, figures, references, labels, and author order.
- [ ] Run tests, `py_compile`, `git diff --check`, and the independent figure
      regeneration/recompute.
- [ ] Update `VERSION` only for the verified source/experiment release.
- [ ] Only after all checks, consider GitHub publication; EDAS is a separate
      user-authorized action.

If development or holdout fails, stop the positive DRC rewrite. Preserve this
template and write a no-go/inconclusive report instead of selecting favorable
subsets or relabeling the old paper.

## 7. Source records

This template is derived from:

* `paper/icc2027/icc2027_lora_mesh.tex`
* `docs/research/icc_drc_revision_map_20261006.md`
* `docs/research/meshecho_drc_runner_contract_20261006.md`
* `docs/research/meshecho_rewrite_core_proposal_20261005.md`
* `docs/research/meshecho_deadline_reserved_core_design.md`

It contains no DRC performance result and does not authorize a paper, version,
release, GitHub, or EDAS update.
