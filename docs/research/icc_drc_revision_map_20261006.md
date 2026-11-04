# ICC 2027 DRC revision map

Date: 2026-10-06  
Scope: read-only audit of `paper/icc2027` against the MeshEcho-DRC
contract.  This file is a revision map, not a manuscript edit and not an
authorization to change `VERSION`, run a holdout, publish a PDF, upload to
GitHub, or submit to EDAS.

## Executive decision

The current ICC manuscript is a five-page, version-2.1.26 report of the old
calibrated max-min-PRR policy.  It is **not** a DRC paper.  The DRC candidate
is currently not eligible to replace the manuscript: the design record says
that its passive exposure gate failed before the reserved smoke/development/
holdout cohorts were opened.  In particular, the available traces had zero
reserve-caused initial-F decisions, while the frozen gate requires at least
20 across the development set.  See
`docs/research/meshecho_deadline_reserved_core_design.md` (status and
pre-population no-go finding) and
`docs/research/meshecho_rewrite_core_proposal_20261005.md` (unfrozen design
status).

Therefore:

1. No DRC numbers, acceptance claims, or DRC novelty language may be added to
   the TeX now.
2. Existing 2.1.26 results must not be relabeled as DRC results.  They use
   RREQ/RREP discovery, max-min PRR route scoring, a TTL-2 fallback, and
   protocol-family models; DRC removes those source decisions.
3. If a future successor passes a separately frozen development gate and an
   untouched holdout, use the section/table/figure plan below.  If it does
   not, retain the current paper as an old-policy report or select a new core;
   do not force a DRC rewrite around a failed candidate.

## Current manuscript inventory

| Location | What is present now | Evidence implication |
| --- | --- | --- |
| `paper/icc2027/icc2027_lora_mesh.tex:14-19` | Title is “Confidence-Aware Route Selection”; authors are `Zu Gao` and `Zhi Quan`, Shenzhen University. | Author formatting is already English and consistent with the current file. DRC would require a new method title only after evidence. |
| `:23-40` | Abstract reports calibrated MeshEcho, Meshtastic-like, MeshCore-like, and PRR+fb values from recurring/random exploratory workloads. | Every method name, number, denominator, and adverse result must be replaced together if a new core is validated. Do not insert provisional DRC values. |
| `:47-79` | Introduction frames max-min PRR and three comparison contributions; it explicitly calls the baseline extension exploratory. | Rewrite the research question and contribution list around one frozen controller plus matched controls, not around a product-superiority claim. Preserve the adverse-stratum disclosure. |
| `:81-95` | Related work covers LoRa mesh, flooding, source routing, ETX, and protocol-inspired Meshtastic/MeshCore models. | Add direct prior-art boundary for deadline admission, route salvage/local repair, opportunistic forwarding, ACK-gated forwarding, and duplicate suppression before any DRC novelty statement. Existing references do not establish DRC novelty. |
| `:96-109` | Shared packet-level PHY, path loss/shadowing, capture, collision, aggregate TX airtime, and modeled energy. | Much can remain if the simulator is unchanged, but a DRC revision must add physical-start scheduling, complete charged packet sizes, request/no-start states, RX-attempt evidence, deadline windows, and finite-state bounds. |
| `:111-148` | Policy descriptions for Meshtastic-like, MeshCore-like, calibrated max-min PRR, and PRR-product fallback. | Replace the MeshEcho subsection with a formal DRC state machine only after implementation. Keep old SR/DCB/DHR and product-inspired rows explicitly labeled as context controls, not same-wire controls. |
| `:150-167` (`tab:policy`) | Four-policy mapping with RREQ/RREP, cached routes, source ACK, and TTL-2 fallback. | Rebuild as a DRC wire/action table: `R_RESERVED`, initial useful F, `R_ONLY`, deadline-infeasible; one recovery F; ACK epoch/marker; same-wire controls. Include charged bytes and no-start semantics. |
| `:169-224` | Two post-hoc exploratory workloads, 20 seeds each, seed-paired CIs, 2-s discovery, 600-s TTL. | Replace with frozen smoke/development/holdout splits, exact seed hashes, all-scheduled-flow denominators, original deadline, actual-start rule, and independent artifact audit. Old 51--70 and 2001--2020 rows cannot validate DRC. |
| `:226-282` (`tab:main`, `tab:paired`) | Main means and paired CIs for calibrated MeshEcho and three stylized/context rows. | Recompute from new raw artifacts only. Primary paired contrasts must be DRC minus `drc-all-f`, `drc-reserve-blind`/fixed-guard as specified by the frozen contract, and `drc-no-rescue`; retain delivery/cost trade-offs. |
| `:284-321` | Recurring/random performance interpretation and PRR-score attribution. | Replace with deadline ACK/destination results, action/path exposure, reserve-caused F and R-to-F counts, complete TX cost, delay/deadline misses, and mechanism-attribution limits. Do not call a zero CI “equivalent.” |
| `:323-380` (`tab:events`, figure) | Pooled destination-only, discovery/cache events, baseline bar figure, modeled energy. | Replace pooled diagnostic table with auditable action/flow/TX/RX/deadline table. A DRC figure must show paired effects or action/exposure; the current three-protocol bar figure cannot be reused as DRC evidence. |
| `:382-392` | Route-TTL sensitivity (old calibrated policy). | Retain only as historical/context sensitivity if useful. It is not a DRC ablation because DRC has no proactive discovery/TTL-triggered source action. Add DRC deadline/guard/cost sensitivity only with predeclared, independent evidence. |
| `:394-447` | Discussion of workload trade-off, stylized product models, statistical/physical limits. | Rewrite claims around the validated estimand, finite state, physical-start semantics, negative results, and simulation-only scope. Keep no firmware/hardware equivalence claims. |
| `:448-457` | Reproducibility says version 2.1.26 and exploratory CSVs; AI-assisted drafting/code review disclosed. | Update only after source/runner/tests/raw artifacts/figures/PDF hashes are audited. Add version, Git revision, runtime, contract hash, seed split, schema, and immutable artifact inventory. |
| `:459-467` | Conclusion says MeshEcho has workload-dependent trade-offs and no score novelty or firmware superiority. | Replace only from holdout evidence. A failed DRC gate must produce a no-go/limitations statement, not a positive DRC conclusion. |

## DRC method section that would be required after validation

The following is a content checklist, not prose to paste into the current
paper. It is derived from the DRC proposal and must be reconciled with the
final implementation and audit artifacts.

### Source decision rule

At the actual, immediately committable source TX start `t`, a flow with
original deadline `D` may use only bounded local state, a locally confirmed
route, local radio availability, complete charged packet ToA, configured
forwarding constants, and the original deadline. It must not use topology,
true PRR, destination-delivery state, aggregate airtime, future events, or
another node's queue.

The method subsection must define, with symbols and one deterministic order:

* `R_RESERVED`: use an ACK-confirmed route only when the route plus one
  admissible F recovery fits before `D`;
* initial useful-data F when the reserved route action does not fit but F does;
* `R_ONLY` when only the routed packet fits;
* no packet with an all-scheduled-flow denominator when no action fits;
* one same-flow recovery F only after the reserved-R guard, with a second
  physical-start deadline check;
* first valid, physically decoded in-deadline ACK semantics and route
  generation updates.

The paper must state that these are nominal admission bounds, not guarantees
against queueing, loss, collision, or interference. It must describe the
same-time ordering at the original deadline and distinguish a queued request,
a canceled/no-start request, and a physically started TX.

### Bounded state and wire identity

The method section must specify source destination records, active flow
records, relay duplicate state, route generations, route expiry/quarantine,
state-capacity drops, and all finite limits actually implemented. The
simulator's unbounded logs cannot be presented as device memory.

For each packet class, show the exact charged fields and byte costs. DRC's
minimum contract uses the existing flow/request identity and an epoch/repair
marker only for the recovery F and corresponding ACK; every DATA, F, ACK,
relay forward, ToA, collision duration, and energy value must use the actual
wire size. A canceled uncommitted request contributes no TX cost.

### ACK and route validity

The paper must explain that source ACK acceptance requires physical decode,
matching flow/request and reversed endpoints, valid loop-free path, correct
path index/actual sender, correct initial/recovery epoch, current active flow,
and deadline inclusion. It must not infer delivery from a missing ACK, and it
must not use destination delivery as a source routing oracle. Accepted ACKs
must be independently joinable to an RX-attempt and an ACK TX path in the
artifacts.

## Required experiment and evidence replacement

### Evidence gates before any TeX edit

The implementation must first pass mechanical packet/state tests and an
independent artifact audit. Then freeze source, contract, runner, tests, case,
radio configuration, trace generation, and hashes before a development run.
Only a development gate pass may open one unchanged-hash holdout. The
holdout must remain untouched during design/tuning.

The DRC design's proposed gates are author-chosen falsification criteria, not
ICC acceptance rates. They include paired ACK/destination non-inferiority and
airtime bounds versus simple controls, plus mechanism exposure floors (actual
R-to-F starts, reserve-caused initial-F decisions, and valid AFS cancellations
if that relay extension is included). A sparse exposure makes a null
mechanism result inconclusive even if an aggregate interval looks favorable.

### Required raw artifacts

Every seed/arm must preserve enough information to recompute the published
metrics, including:

* all scheduled flows, original enqueue/deadline, state-capacity and
  deadline-infeasible outcomes;
* every action request with stable identity, request time, event order, actual
  start/end, queue wait, and one terminal status (`started`, `canceled`,
  guard/deadline rejected, or not processed by cutoff);
* complete physical TX records with packet class, path, bytes, ToA, energy,
  deadline/cutoff classification, and flow/generation joins;
* complete `(TX, receiver)` RX-attempt records with success, collision,
  half-duplex, capture, or PRR-failure reason and enough identity to verify
  accepted ACKs;
* accepted/rejected ACK records with marker, physical sender, path, reason,
  source acceptance time, and generation;
* route state transitions, duplicate-cache capacity/evictions, recovery
  admissions/cancels/starts, and zero-event seeds;
* immutable manifest containing schema, `VERSION`, Git revision, runtime,
  dependencies, command, source/contract hashes, seed split, case/radio/
  topology/trace hashes, prerequisite manifest hash, artifact inventory, and
  record counts.

The current audit notes that the generic runner and matched-D/DCB tools do
not yet close the request/no-start ledger, complete RX-attempt ledger,
deadline censoring/spillover, full prefix state, or artifact recomputation
requirements. Those gaps block DRC manuscript evidence; they are not reasons
to silently weaken the paper's estimand.

## Table replacement plan

| New table | Required content | Current source to retire | Acceptance condition |
| --- | --- | --- | --- |
| Method/action table | DRC actions, admission bounds, recovery guard, ACK epoch, wire bytes, state caps. | `tab:policy` (`:150-167`) | Matches implementation and packet-byte/ToA tests exactly. |
| Experiment contract table | Development/holdout seeds, workloads, trace hashes, deadline, PHY, controls, primary/secondary estimands. | `tab:params` (`:197-212`) | Manifest and manuscript values agree; no inspected seed is called untouched. |
| Primary results table | Seed means plus paired CIs for ACK PDR, destination PDR, complete TX airtime/energy, deadline delay/misses. | `tab:main` (`:233-258`) | Recomputed from immutable raw artifacts; all scheduled flows remain denominators. |
| Paired-effect table | DRC minus each matched same-wire control, endpoint and CI interpretation. | `tab:paired` (`:260-282`) | Uses seed as uncertainty unit and reports zero-crossing CIs as “no demonstrated advantage,” never equivalence. |
| Mechanism/exposure table | R-reserved, R-only, initial-F, R-to-F starts, recovery cancel/start, route transitions, collisions, queue/no-start, state-capacity drops. | `tab:events` (`:335-359`) | Counts recompute from action/request/TX/RX ledgers and include zero-event seeds. |
| Context table (optional) | Old SR/DHR/DCB and stylized Meshtastic/MeshCore rows, clearly marked as different packet contracts. | Current baseline rows | Never used as same-wire causal controls or firmware measurements. |

Do not add a table merely to make the paper appear more complete. The table
set should fit the ICC page limit and should prefer paired effects and
mechanism exposure over decorative pooled counts.

## Figure replacement plan

The current figure at `paper/icc2027/figures/fig_baseline_delivery.pdf` is
generated by `plot_baseline_delivery.py`, whose protocol list contains only
`meshecho-calibrated`, `meshtastic-like`, and `meshcore-like`. Its source CSV
likewise contains only those three rows. It cannot be relabeled as DRC.

After verified DRC evidence, choose one of the following, based on the
estimand and available page space:

1. **Preferred:** a two-panel seed-paired effect plot showing DRC minus each
   same-wire control for ACK PDR, destination PDR, and relative complete TX
   airtime, with nominal 95% paired intervals and the prespecified margins.
2. **Mechanism companion:** stacked action/exposure rates by arm (R-reserved,
   initial F, R-to-F recovery, no-start, and accepted ACK), with denominators
   stated. This is useful only if the exposure floor passes.
3. **Context panel:** old SR and protocol-inspired baselines in a visibly
   separate panel, labeled exploratory and not firmware measurements.

Every plotted number needs a source CSV/hash and an independent recomputation
check. Keep the current figure only as historical evidence for the old
version, not as support for DRC.

## Results writing rules

If the development and holdout gates pass, the results section must report:

* the exact seed split and all-scheduled-flow denominators;
* ACK PDR and destination PDR by original deadline, not pooled packet counts;
* complete network TX airtime/bytes/energy and the accounting window;
* capped completion delay, successful-ACK delay, deadline misses, queue wait,
  late/post-cutoff spillover, collisions and half-duplex failures;
* DRC action/path divergence and exposure counts before interpreting any
  mechanism effect;
* all negative or adverse workload/PHY/load results, with separate estimands;
* paired seed-level CIs and exact gate decisions.

If any primary gate fails, report the failure and stop positive DRC claims.
Do not retune on the development outcomes and call the resulting numbers a
holdout. If exposure is below the frozen floor, call the mechanism claim
inconclusive rather than treating a null as proof of no effect.

## Version, reproducibility, and release checks

The current root `VERSION` is `2.1.26`, while the current workload table
caption says `2.1.25` (`icc2027_lora_mesh.tex:197-200`). This mismatch must be
resolved in a later evidence-backed release; it is not fixed by this map.

For a future DRC release, the order is:

1. pass unit/integration/ledger audits;
2. freeze and run development;
3. independently recompute and apply the declared gate;
4. run untouched holdout only if permitted;
5. rewrite TeX/tables/figures from audited CSVs;
6. compile and visually inspect the ICC PDF, including page count, fonts,
   overfull boxes, references, labels, and author order;
7. increment `VERSION` only for the verified code/experiment release;
8. run regression tests and then consider GitHub publication.

No manuscript, version, GitHub, or EDAS update is justified by the current
DRC design, the rejected passive exposure screen, or old 2.1.26 artifacts.

## Source records

* `paper/icc2027/icc2027_lora_mesh.tex`
* `paper/icc2027/figures/plot_baseline_delivery.py`
* `paper/icc2027/figures/fig_baseline_delivery_source.csv`
* `docs/research/meshecho_rewrite_core_proposal_20261005.md`
* `docs/research/meshecho_deadline_reserved_core_design.md`
* `docs/research/meshecho_rewrite_experiment_audit_20261005.md`
* `docs/research/meshecho_core_rewrite_handoff_20261005.md`
* `docs/research/icc_core_rewrite_revision_map.md`

