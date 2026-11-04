# SECON 2027 paper blueprint and citation map

Prepared 2026-11-04. **Internal writing document; not a submission-ready
manuscript or a performance report.** The independent English SECON paper is
to use IEEE conference format at 10 points and no more than nine pages,
including figures, references and appendices. The user has already authorized
that configuration. This pass applies the `academic-paper` skill in
revision/citation-check mode to existing verified research material; it does
not run the full writing pipeline or create a TeX file.

The method anchor is `secon2027_algorithm_spec.md`, describing tested version
2.1.27 and source snapshot
`e8d94c29b3797a55787ee8cc5a60c3d08b4949186f2250581ed36d851ef5b1a2`.
The implementation may change during development. Before drafting a final
method section, reconcile this blueprint with the method and source frozen
for formal evaluation. The present pass makes no inference from development
results and imports no historical ICC numerical results. Formal performance
claims remain unavailable until the complete frozen evaluation is audited.

## 1. Paper identity and scientific question

Working title: **MeshEcho-CPR: Deadline-Aware Recovery and ACK-Driven Relay
Cancellation for LoRa Mesh Networks**. This names the method without claiming
optimality, a latency guarantee, firmware compatibility or measured savings.

Primary research question:

> Under a shared packet-level LoRa mesh model, when does a finite sequence
> of ACK-confirmed source routing, one same-path repeat and one locally
> deadline-admitted recovery flood improve the trade-off between timely
> source confirmation and physical transmit airtime, and how much does
> cancellation of uncommitted relay copies contribute?

The question must allow a negative answer. The extra repeat can consume
airtime without restoring a broken path; a recovery flood can increase
contention; ACK cancellation may have few eligible opportunities; source
admission can leave a flow unstarted. Report these cases in the full planned
population. Neither a scenario label nor a configured hop limit establishes
that its intended mechanism occurred.

Supporting questions, mapped to the planned evaluation:

1. **Stable operation (S1):** What costs arise when a cached path still works,
   and how often does an initial FLOOD rather than a cached route serve a
   message? Report repeat/recovery activity even when its cost is unhelpful.
2. **Path disruption (S2):** When the common environment disrupts a path and
   provides a structural alternative, do admitted recovery actions deliver
   and obtain a timely ACK? Keep flows with no reachable alternative in the
   denominator and distinguish offline reachability from observed reception.
3. **Contention (S3):** How do physical transmissions, collisions, queues,
   expiry and ledger evictions change the benefit of feedback-based
   suppression? Separate decoded ACK checks from successful cancellation.
4. **Components and robustness:** What changes when only ACK cancellation,
   only the repeat or only recovery is disabled? Does the conclusion survive
   the limited robustness axis frozen after development?

Proposed contribution language is conditional on its evidence class:

- **Implementation-supported now:** A precisely specified controller linking
  local deadline admission, message-level ACK validation, route-cache
  confirmation and pre-commit relay cancellation, with explicit finite
  source transmission bounds and component state limits.
- **Evaluation contribution, not yet a result:** A common-environment study
  of four explicit behavioral models under both their implemented defaults
  and a declared parameter-matching rule, with clean component controls and
  separate destination-delivery/source-confirmation outcomes.
- **Evidence infrastructure, supported by its own records:** Physical
  request/TX/RX/ACK provenance and reconstruction of all started-frame
  airtime. This is an auditability contribution, not a claim that new logging
  alone establishes a novel routing algorithm or a calibrated radio model.

The final abstract and introduction need at least one concrete measured
finding, including its scenario and uncertainty, before they can claim an
empirical contribution. Until then, use these as internal intentions only.

## 2. Novelty and comparison boundary

Source routing, cache reuse, finite ARQ, flooding, duplicate suppression and
ACK-assisted forwarding coordination are established mechanisms. DSR, the
broadcast-storm literature, Trickle, ExOR and truncated ARQ are direct
antecedents, not decorative background. The reviewed official Meshtastic
release contains next-hop learning, retransmission and final-retry flooding;
MeshCore's pinned FAQ describes first-message DATA flooding, delivery-report
path learning and broken-route retry/flood fallback. **Do not claim that
retry followed by flooding, or ACK-assisted suppression in general, first
appears in CPR.**

The defensible distinction to investigate is the exact interaction among:
stage-specific local admission budgets; separation of a live message's ACK
validity from a shared route-cache generation; monotonic same-path
confirmation revisions; and cancellation of a matching off-path relay's
still-uncommitted send. These rules are currently an implemented design
combination. The existing 26-source corpus supports antecedents and
boundaries; it does not establish an exhaustive novelty search or a
first-ever claim for the combination.

Use the labels **MeshEcho-CPR**, **legacy MeshEcho**, **Meshtastic-like** and
**MeshCore-like** in all manuscript text, legends and captions. The latter
two are simplified behavioral models, not executions of official firmware.
Their omitted retry and learning mechanisms make a CPR advantage against
them insufficient evidence of superiority to the products. The clean CPR
controls are necessary for component interpretation, but do not repair every
external-baseline fidelity limitation.

Two regimes must remain distinct. “Default” means each implemented model's
resolved constructor/factory settings under common PHY and workload, not
official device defaults. “Matched” aligns only parameters with equivalent
meaning: MC route TTL to 600 s and MT/MC flood base/jitter to 0.45/0.65 s in
the current contract. It retains route discovery semantics, SNR delay
functions, retries and other genuine policy differences. The frozen formal
contract governs the final values; matching a base delay does not make the
total forwarding delay equal.

## 3. Nine-page allocation and evidence-led structure

The following is a layout budget, not a measured PDF page count. Reserve
0.20 page for line wrapping and final reference/disclosure changes. Do not
shrink margins, body font or line spacing to force a fit.

| Content | Target pages | Purpose and required evidence |
| --- | ---: | --- |
| Title, anonymous block, abstract, keywords | 0.45 | Problem, method, final quantitative finding and scope; write abstract last. |
| I. Introduction | 0.70 | Explain airtime versus timely confirmation; state RQ, actual contributions and product-model boundary. |
| II. Related work | 0.60 | Multi-hop LoRa objectives; recovery/suppression antecedents; official product behavior. |
| III. System model and comparison scope | 0.75 | Flow/deadline/outcomes, full-frame accounting, local inputs; compact four-model table. |
| IV. MeshEcho-CPR | 1.60 | Budgets, FSM/timing diagram, ACK/cache separation, relay rule, bounds and clean controls. |
| V. Experimental method | 1.05 | Frozen source/cohorts, S1–S3 validity, defaults/matching, PHY/config table, seed-level analysis. |
| VI. Results | 2.10 | Complete main comparison, ablations, mechanism costs, latency and predeclared robustness. |
| VII. Limitations and conclusion | 0.40 | Model and firmware limitations; bounded answer to the RQ. |
| Anonymous AI-use disclosure | 0.10 | Follow applicable IEEE policy; final scope and section names verified. |
| References | 1.05 | Verified sources actually cited; no bibliography padding. |
| **Planned content** | **8.80** | Plus 0.20-page contingency, total at most 9.00. |

Keep manuscript sections III–V reproducible within the paper; an unavailable
anonymous supplement cannot carry essential definitions. This plan assumes
no appendix. Consolidate visual panels, but never omit a planned comparison
only to improve appearance or hide an unfavorable outcome.

Suggested visual inventory:

- **Figure 1:** Source stages plus a relay timing inset showing request,
  commitment and reserved physical start. Label the cold branch separately;
  an ACK cannot cancel a committed future-start packet.
- **Table I:** Four-model fidelity table. Include cold start, path learning,
  source retry, ACK behavior and known official features omitted by models.
- **Table II:** Actual frozen scenario/radio/statistical settings and the
  default-to-matched parameter changes. Include payload and full-frame
  encoding convention, hop limit and observed hop distributions elsewhere.
- **Figure 2:** Timely source ACK, timely destination delivery and physical
  airtime across S1–S3 and both regimes, with seed-level intervals. Use a
  coherent multi-panel figure; avoid combining regimes into a pooled mean.
- **Figure 3:** Clean paired ablation effects together with packet-kind ×
  stage cost partition and actual stage/cancellation exposure. The old
  whole-ledger `nocancel` policy cannot be labeled an ACK-only ablation.
- **Figure 4:** Predeclared load or scale/deadline curve, and successful-flow
  latency accompanied by the unfinished fraction. Draw a load curve only
  when the cases differ solely in the declared workload axis.

## 4. Minimal useful mathematics

Use the algorithm specification's A1–A12 as the authoritative detailed
definitions. Approximately six displayed equation groups plus short inline
wire/budget definitions are sufficient. Do not reproduce the ICC's long
equation sequence solely to create an appearance of theory.

**M1 — Objective and outcomes.** For all N scheduled flows, define
`D_i = a_i + Delta_i`, first eligible destination delivery `t_i^D`, and first
accepted source ACK `t_i^A`; absent times are infinity. Then

\[
P_D=N^{-1}\sum_i\mathbf1[t_i^D\le D_i],\qquad
P_A=N^{-1}\sum_i\mathbf1[t_i^A\le D_i].
\]

The objective is to characterize the `(P_A, P_D, A)` trade-off under a fixed
workload/deadline. A reliability-constrained minimization may express an
application preference, but CPR does not solve an optimization problem or
guarantee feasibility for an arbitrary reliability target. Preserve capacity
rejections, no-start flows and deadline misses in N.

**M2 — Complete physical cost.** For fixed accounting cutoff C,

\[
A=\sum_{q:t_q\le C}T(L_q),\qquad
C_D=\frac{A}{\sum_i\mathbf1[t_i^D\le D_i]}.
\]

Here q denotes a distinct physical TX and T is complete-frame LoRa ToA.
`C_D` is undefined when the denominator is zero. Charge a started frame's
full duration even when its end crosses C. Cite `augustin2016study` for the
standard ToA calculation, not for the custom wire layout. Give inline CPR
lengths `L_DATA/FLOOD=12+2n+P+1[marker present]` and
`L_ACK=12+2n+1[marker present]`; n counts carried node IDs. Cache generation
and confirmation revision are local, not extra wire bytes. If displaying
the full LoRa symbol equation is necessary for reproducibility, copy A4–A5
exactly and remove another nonessential equation rather than inventing a
new approximation.

**M3 — Local admission.** Let h be cached-path hops, H the maximum hops,
epsilon the safety margin, and b/j the flood base delay/jitter width:

\[
\begin{split}
B_R(p,m)&=h\{T(L_D(h+1,m))+T(L_A(h+1,m))\}+\epsilon,\\
B_F(m)&=H\{T(L_F(H+1,m))+T(L_A(H+1,m))\}\\
&\quad +(H-1)(b+j+0.35)+\epsilon,\\
\operatorname{fits}(t,B,D)&\iff t<D\ \land\ t+B\le D.
\end{split}
\]

Define the literal 0.35-s maximum weak-link delay term and actual configured
b/j/epsilon. Initial admission uses an unmarked packet; repeat observations
and admission use marked `m=1` lengths. These are local budget estimates,
not bounds on all relay queues, interference or successful ACK return time.
Recovery still requires the saved route generation to be current and READY.

**M4 — Finite source work.** For the original source's DATA/FLOOD count,

\[
N_i(m)\le1\quad(m\in\{\varnothing,1,2\}),\qquad
N_i^{\mathrm{source}}\le
\begin{cases}1,&\text{initial-FLOOD branch},\\3,&\text{initial-route branch}.
\end{cases}
\]

The argument follows unique flow identity, at-most-once stage flags and
source-return rejection; spell out those assumptions in one paragraph.
This excludes ACKs and other nodes' forwarding and is not a network-wide
three-transmission bound. The cold branch includes absent, expired,
quarantined or locally infeasible cached routes, not just first contact.

**M5 — Cancellation boundary.** State `t_q=max(k_q,b_v)` and

\[
\operatorname{cancel}(v,q,a)=
\operatorname{decoded}(v,a)\land\operatorname{match}(q,a)
\land[v\notin\operatorname{path}(a)]
\land\operatorname{uncommitted}(q)
\land\neg\operatorname{canceled}(q).
\]

Define `match` in prose using endpoints, flow/request IDs, supported marker,
simple ACK path, reverse-hop index and decoded sender. Request creation,
commitment k and reserved start t are different. Once committed, q is not
cancelable even if its start lies in the future. This is an honest-packet
simulation validity rule, not cryptographic authentication. Canceled-copy
counts are not counterfactual network airtime savings.

**M6 — Paired estimands.** For each scenario/regime and n seeds, define

\[
\overline{\delta P_A}=n^{-1}\sum_s(P_{A,s}^{\mathrm{CPR}}-P_{A,s}^{c}),
\quad
G_A=\exp\!\left[n^{-1}\sum_s\log(A_s^{\mathrm{CPR}}/A_s^{c})\right].
\]

Use the frozen 10,000-resample paired percentile bootstrap and describe its
95% intervals as descriptive and unadjusted. The airtime estimate is a
geometric mean of per-seed ratios, not a pooled-mean ratio. An undefined
seed-level cost/ratio remains undefined in the all-seed summary; do not
select only defined seeds. `glasserman1992crn` motivates common-scenario
pairing but gives no unconditional guarantee of variance reduction here.

Do not add independent-loss products, success-probability closed forms,
energy optimality, deadline guarantees or asymptotic network-wide memory
theorems. If a conditional stage-success identity is helpful, identify it as
probability bookkeeping and condition each later stage on prior failure and
actual admission. No independence assumption is needed for the present
empirical estimands.

## 5. Methods prose ready for adaptation

The following English paragraphs describe the current specified method.
They require reconciliation with the final frozen source, not numerical
placeholders in a submission PDF.

**System and measurements.**

> Each scheduled application message has a fixed deadline measured from its
> enqueue time. We distinguish the first eligible reception at the
> destination from the first valid acknowledgment received by the source.
> Every scheduled message remains in both denominators, including a message
> rejected by a local capacity limit or never admitted to the radio. Radio
> cost is the sum of full-frame time on air for distinct transmissions that
> start within the common accounting window. Routing fields determine the
> frame length supplied to the standard LoRa airtime calculation
> \cite{augustin2016study}. Discovery, feedback and duplicate transmissions
> are charged by the same rule.

**Source controller.**

> At its initial transmission opportunity, the source uses a cached path
> only while that path is READY, unexpired and locally feasible before the
> message deadline. Otherwise it attempts an initial DATA flood. A routed
> message can request one repeat on the same saved path after an ACK
> observation interval; only after that repeat has a recorded physical start
> can full CPR request a recovery flood. Every additional stage rechecks
> its deadline budget at the proposed physical start and retains the same
> application identity. An initial-flood message has no repeat or recovery
> stage. These rules bound original-source DATA transmissions but do not
> guarantee end-to-end delivery or bound all relay traffic.

**ACK validity and shared cache.**

> A source accepts an ACK against the live message's endpoints, stage,
> recorded start and saved path, within its fixed deadline. It does not
> reject an otherwise valid in-flight ACK solely because another message
> updated the shared cache. Message completion and cache mutation are
> separate: a valid old-message ACK may complete its message without
> replacing a newer different route. A same-path refresh advances a local
> confirmation revision while preserving the route generation. A timeout
> may quarantine that route only when both captured values still match,
> preventing an older failed message from invalidating newer confirmation.

**Relay cancellation.**

> Each relay keeps a bounded ledger of pending flood copies. A locally
> decoded, structurally valid ACK can cancel the exact matching handle only
> when the relay is outside the ACK path and the handle remains
> uncommitted. Commitment reserves a physical radio interval, so an ACK
> arriving before a reserved start can still be too late to cancel that
> transmission. The ledger uses only local received fields and pending
> state; it does not observe a global destination-delivery flag. Duplicate
> suppression and capacity eviction remain distinct mechanisms.

**Controls and accounting.**

> The ACK-cancellation control disables only cancellation triggered by ACK
> reception, retaining the ledger capacity and eviction rule. The no-repeat
> control emits no physical repeat and keeps the nominal repeat observation
> slot unavailable before recovery. The no-recovery control retains the
> initial transmission and repeat. We inspect resolved parameters to ensure
> that each clean control changes only its intended switch. A separate
> historical control removes the entire ledger policy and therefore measures
> a broader policy difference. Counts of decoded ACK cancellation checks,
> successful cancellations and capacity evictions are reported separately.

For the no-repeat control, if exact timing is needed, specify recovery's
earliest observation as `t_0 + 2 B_R(p,1)`. Queues can make subsequent event
times differ across policies; this control does not guarantee identical
transmission timelines.

**Statistical design, to use only after its execution record exists.**

> We freeze the method, scenario matrix, seed cohort and analysis settings
> before the formal comparison. Arms share hashed topology, scheduled
> traffic and exogenous channel/fault fields; protocol-dependent event
> streams may differ. Each seed is one inferential unit. We report
> equal-weight seed means and paired effects with descriptive, unadjusted
> 95% percentile bootstrap intervals. Common-random-number methods motivate
> the shared environment, although their variance benefit depends on the
> system \cite{glasserman1992crn}. Results are computed only from complete,
> independently audited planned batches; failed attempts and undefined
> metrics remain visible.

## 6. Related-work prose and citation-to-claim map

Use the verified BibTeX keys from `paper/icc2027/references.bib`; copy that
corpus into the future independent SECON project without editing ICC. Its
audit reports 26 sources: 23 academic papers, one routing book chapter and
two official project documents; 23 verified DOIs. Trickle has no verified
DOI, which must remain absent rather than fabricated. Do not use unpublished
MASS material. Do not cite a source merely to retain a target reference
count; the following map provides a legitimate use for every corpus item.

Reading scope below is inherited from the saved 2026-11-04 audit, not a
claim that this pass retrieved and reread every original full text. **F**
means relevant full-text sections were inspected; **A** means an indexed or
publisher abstract was inspected; **O** means official documentation/source.
The narrow supported claims follow those access limits. The corpus's
metadata/citation-relationship checks are not a current retraction-database
clearance, exhaustive literature review or proof of originality.

| Verified key | Scope | Manuscript location and supported claim | Boundary |
| --- | --- | --- | --- |
| `augustin2016study` | F | III, M2: LoRa symbol timing, payload-symbol count and full-frame ToA. | Does not define CPR's custom header, admission budgets or new protocol. |
| `bor2016scale` | F, corrected author version | I/II: airtime, configuration, timing and capture affect LoRa capacity. | Do not reuse conflicting original/corrected density numbers; no mesh calibration claim. |
| `georgiou2017scale` | F, arXiv v2 | I/II: single-gateway load/interference scalability motivates cost accounting. | Do not transfer its single-gateway coverage equation to multi-hop CPR. |
| `wong2024multihop` | A | II: LoRa multi-hop/mesh work spans routing, access and energy concerns. | Survey classification, not exhaustive novelty certification; use formal 2024 metadata. |
| `cotrim2020lorawanmesh` | F, relevant PMC sections | II/III: relay/router and LoRaWAN multi-hop architectures differ. | Peer-to-peer LoRa mesh is not automatically a LoRaWAN deployment. |
| `decouto2003etx` | F, author manuscript §3.1 | II/III: DATA and reverse ACK reception both matter to transaction cost. | ETX is prior art; CPR does not implement an ETX estimator or assume its link-probability model. |
| `croce2018orthogonality` | A | VII: different spreading factors are not perfectly orthogonal. | A fixed-SF study does not evaluate inter-SF performance or validate a SIR matrix. |
| `rahmadhani2018concurrent` | A | II/VII: LoRaWAN collision/capture experiments motivate reception-model limits. | WiNTECH workshop, not MobiCom main conference; no borrowed capture thresholds. |
| `heusse2023capacity` | A | VII: capture with multiple interferers may depend on summed interference and noise dependence. | Do not claim that this model is implemented or calibrated here. |
| `to2018lorans3` | A | II/V: LoRa ns-3/CSMA and measurement comparison are simulation-method precedents. | Their validation is not validation of this Python simulator. |
| `vandenabeele2017scalability` | F, author manuscript | I/III: received DATA and confirmed communication differ; ACK resources matter. | LoRaWAN gateway/downlink constraints differ from mesh reverse-path ACKs. |
| `ahmar2022smarthop` | A | II: Smart-Hop combines low-overhead multi-hop routing with SF-dependent range to target latency. | Do not attribute CPR's fixed-PHY recovery or deadline guarantee to it. |
| `feng2022cost` | A | II: MLoRa targets cost-effective coverage and balanced energy use. | INFOCOM Workshops, not main conference; no transferred energy percentages. |
| `zhu2019improving` | A | II: SF clustering balances airtime and connectivity in a mesh design. | Different control dimension from fixed-PHY source recovery. |
| `pueyo2024minimalistic` | A | II: distance-vector routing uses a ToA metric and FLoRa/OMNeT++ evaluation. | Do not equate its metric or implementation with CPR or official products. |
| `sole2022implementation` | A | II/VII: proactive LoRa mesh library evaluated on ESP32 embedded boards. | Its hardware evidence is not hardware evidence for this study. |
| `tian2023lorahop` | A | II: LoRaHop supports bidirectional LoRaWAN multi-hop relaying and reports an outdoor implementation. | Gateway-oriented architecture; not a same-condition peer-to-peer baseline. |
| `johnson1996dsr` | Publisher A; later RFC separately checked | II: source-route discovery/reuse is established prior art. | The later RFC is not the 1996 chapter; no identity with MeshCore is claimed. |
| `ni1999broadcaststorm` | A | I/II: naive flooding creates redundancy, contention and collisions. | Does not prove each locally canceled copy reduces total network cost. |
| `levis2004trickle` | A | II: overhearing consistent information can suppress redundant dissemination. | Different dissemination objective; no invented DOI or detailed unverified timer claim. |
| `biswas2005exor` | F, author manuscript passages | II: opportunistic forwarding and ACK coordination can avoid redundant transmissions. | ACK-assisted suppression is antecedent; its 802.11b gains do not transfer to LoRa. |
| `meshtasticdocs` | O; prior webpage plus pinned release source audit | II/III: managed flooding and next-hop mechanisms; source audit establishes retry/flood antecedent. | The model omits official behavior; retain the webpage's actual earlier access date. |
| `meshcore` | O, pinned FAQ audit | II/III: first-message DATA flood, delivery-report route learning and retry/flood fallback. | The simplified model uses RREQ/RREP and omits official retries. |
| `liu2004truncated` | A | II: finite ARQ expresses a delay/reliability trade-off. | Not a derivation of CPR's multi-hop budgets or a LoRa result. |
| `srinivasan2008beta` | A | II/VII: low-power wireless reception can be bursty. | General motivation for avoiding independent-retry assumptions; not LoRa calibration. |
| `glasserman1992crn` | Publisher/index A | V, M6: common-random-number comparison and its conditional variance benefits. | Same seed alone is insufficient; no claimed optimal coupling or guaranteed variance reduction. |

The old PHY suggestion file contains draft aliases
`rahmadhani2018collide` and `heusse2023aloha`. Those are **not** keys in the
verified final BibTeX corpus. Use `rahmadhani2018concurrent` and
`heusse2023capacity` as above. In the final TeX, require exact equality
between used citation keys and emitted bibliography entries; no `nocite`.
Keep IEEE first-appearance numbering and all verified DOI fields. Do not
introduce unverified new references during prose polishing.

Suggested English related-work paragraphs:

> Multi-hop LoRa systems address different network roles and performance
> goals. Surveys distinguish relay and router architectures and organize
> work on routing, access and energy use
> \cite{cotrim2020lorawanmesh,wong2024multihop}. Smart-Hop uses
> spreading-factor-dependent range in a low-latency multi-hop design
> \cite{ahmar2022smarthop}, whereas MLoRa targets economical coverage and
> balanced energy use \cite{feng2022cost}. Other approaches use SF
> clustering to balance airtime \cite{zhu2019improving} or a time-on-air
> metric in distance-vector routing \cite{pueyo2024minimalistic}. An ESP32
> mesh library and LoRaHop provide implementation evidence for proactive
> routing and bidirectional LoRaWAN relaying, respectively
> \cite{sole2022implementation,tian2023lorahop}. These architectures do
> not constitute interchangeable baselines for deadline-limited
> peer-to-peer messages.

> Source-route reuse is established by DSR \cite{johnson1996dsr}, and
> finite ARQ has long exposed a delay-reliability trade-off
> \cite{liu2004truncated}. DATA and reverse ACK reception jointly enter
> established link-cost measures such as ETX \cite{decouto2003etx}.
> Wireless reception can also be bursty \cite{srinivasan2008beta}, so a
> second attempt should not be treated as an independent repetition of the
> first. CPR uses observed missing confirmation and local time budgets;
> its evaluation measures conditional outcomes without an independent-loss
> approximation.

> Redundant rebroadcasting increases contention and collision opportunities
> \cite{ni1999broadcaststorm}. Trickle suppresses transmissions after
> overhearing consistent summaries \cite{levis2004trickle}, while ExOR
> coordinates opportunistic forwarding using acknowledgment information
> \cite{biswas2005exor}. Official Meshtastic and MeshCore mechanisms also
> combine learned routes, retries and flooding
> \cite{meshtasticdocs,meshcore}. Thus neither retry-to-flood recovery nor
> ACK-assisted suppression is new in isolation. This study examines their
> specific interaction with deadline admission, live-message confirmation
> and the point at which a pending relay becomes irrevocably committed.

For precise official-source claims, preserve the release/commit identities
from `secon2027_baseline_fidelity.md` in the future SECON bibliography notes
or source audit reference. The corpus's generic project webpages alone
should not silently stand in for every pinned code-level assertion. Public
third-party project URLs are ordinary scholarly sources; omit identifying
URLs for this study's authors or artifact repository in the review PDF.

## 7. Results-to-text contract

No numeric result sentence is ready in this blueprint. Do not promote P0
smoke tests, deterministic replay, development pilots or old ICC results to
fresh formal validation. Keep these evidence roles separate:

| Intended statement | Required evidence before it enters the paper | Disallowed shortcut |
| --- | --- | --- |
| CPR changes timely confirmation/airtime in a named setting | Complete frozen four-arm cases, both regimes; paired effects, intervals, run/source/config identities. | Best seed, pooled packet sample size, incomplete plan or old-version number. |
| Recovery helps after path disruption | Physical source stage starts, accepted ACK/delivery provenance, common fault exposure and offline alternative-path diagnostics. | A `recovery-request` event or scenario name alone. |
| ACK cancellation changes total airtime | Clean `noackcancel` resolved-parameter comparison and component exposure. | Number of canceled copies × nominal ToA as a network-wide causal saving. |
| Repeating or flooding is unnecessary in some regime | Clean `norepeat`/`norecovery` controls, retained adverse effects and the no-repeat slot rule. | Skipping a stage while simultaneously advancing the next opportunity. |
| Robustness across load, scale or deadlines | Completed, predeclared limited axis with confounders fixed or disclosed. | Connecting unrelated points or interpreting a hop cap as actual path depth. |
| Component state is bounded | Algorithm-spec capacities and overflow semantics. | Eight-entry ledger implies constant entire simulator/firmware memory. |
| Real hardware or battery improvement | Actual RF/energy measurements with documented setup. | Native tests, board compilation, citations to others' hardware or TX-only energy conversion. |

For each final result, write the setting first, the effect with its
uncertainty second, and the mechanism evidence/limitation next. A success-only
latency curve must state the unfinished fraction. The count ratio for ACK
cancellation is “successes per decoded ACK cancellation check”; a zero
denominator is undefined, not zero. Delivery without timely confirmation
is an observed outcome, not automatically evidence of an ACK-channel cause.

An internal abstract scaffold can be: motivation; precise method; completed
evaluation scope; one primary effect and one condition where the benefit
weakens; model/implementation limitation. Any internal `[result pending]`
marker must be removed by inserting audited evidence or deleting the claim
before exporting a review PDF.

## 8. Anonymous manuscript and official AI-use policy

The public review PDF must contain no author names, affiliations, emails,
identifying repository links, grant names or identifying PDF metadata. Do
not copy the ICC author block, acknowledgments or private author details.
Do not invent a funding statement, including “no external funding.” Do not
invent author contributions, conflict declarations, ethics approvals or
data-release promises to satisfy a generic writing template. The user's
anonymous English conference requirements take precedence over the skill's
generic bilingual-abstract/CRediT/funding sections. Preserve actual source
availability and funding details privately for the appropriate final stage.

### Official retrieval, 2026-11-04

The IEEE Conference Author Center's
[Submission Policies](https://conferences.ieeeauthorcenter.ieee.org/author-ethics/guidelines-and-policies/submission-policies/)
was successfully retrieved at **08:29:39 UTC / 16:29:39 Asia/Shanghai** using
`curl -fLsS --max-time 30` with normal TLS verification. Response: 71,545
bytes; SHA-256
`7951cdcfff6e0acb68bea9417110e4ae7893b283a9d479527bf3099f175e346a`.
The HTML was read without adding a downloaded file to the source tree. The
fingerprint identifies that response, not a promise that the live page will
remain unchanged.

Under “Guidelines for Artificial Intelligence (AI)-Generated Text,” it says:

> “The use of content generated by artificial intelligence (AI) in an
> article (including but not limited to text, figures, images, and code)
> shall be disclosed in the acknowledgments section of any article
> submitted to an IEEE publication.”

> “The AI system used shall be identified, and specific sections of the
> article that use AI-generated content shall be identified and accompanied
> by a brief explanation regarding the level at which the AI system was
> used to generate the content.”

The same page states that AI editing/grammar enhancement is generally
outside the policy's intent, so disclosure for that use is recommended but
not required, and it calls for double checking AI-generated results. This
project's assistance extends to substantive drafting and research software,
so it should not be described as grammar editing alone. The official
[journal policy page](https://journals.ieeeauthorcenter.ieee.org/become-an-ieee-journal-author/publishing-ethics/guidelines-and-policies/submission-and-peer-review-policies/)
was also retrieved and contains the same author-disclosure rule; its
87,738-byte response had SHA-256
`1599c6bb51a5e9a6f4af559c3aa97df8e12888bf4de86100239c06893b94aeff`.
The conference page is the direct relevant source.

The first guessed conference URL ending
`submission-and-peer-review-policies/` returned 404. The actual URL above
was discovered through the official Author Ethics navigation; the failed
URL is not supporting evidence. No account, EDAS action or external message
was used. `secon2027_official_requirements.md` found no SECON-specific AI
waiver or disclosure text on the four inspected conference pages. Therefore
retain the general IEEE disclosure requirement; do not infer an exemption.

For the anonymous review version, a non-identifying acknowledgment can name
the AI tool and its uses without naming any human author, affiliation,
funding source or identifying repository. Candidate wording to finalize
only after the manuscript's actual AI-use scope and section numbers are
known:

> **AI assistance.** OpenAI Codex assisted with literature organization,
> drafting portions of the related-work and methods sections, and
> developing the simulation and analysis software described in this paper.
> Its outputs were used as drafts and implementation suggestions.

Add any other actually used AI systems and their specific roles; identify
all final sections containing generated material. If AI-generated figure
code or manuscript text is used in additional sections, expand the
disclosure accordingly. Add a claim of author review/verification only
after that review has occurred. Naming the tool does not satisfy the whole
policy if the specific sections or level of use are left vague. Keep this
candidate in the internal blueprint until it accurately describes the final
paper; avoid a generic assertion that all results were validated by humans.

The conference policy page also says that the work should be original and
not concurrently under consideration elsewhere, and that use of previously
published/submitted work as a basis requires explaining the differences.
Preserving ICC files establishes neither publication nor submission status.
Before any eventual submission, resolve actual ICC status and overlap;
anonymity does not excuse misrepresenting related prior work. This task
authorizes preparation, not EDAS submission or external correspondence.

## 9. Handoff and completion conditions

This pass changes only this blueprint. It creates no final paper, changes
no ICC source or bibliography, runs no simulations and makes no submission.
The parent owns creation of the independent LaTeX project, formal-evidence
selection and final artifact validation.

Before final manuscript export:

1. Reconcile method and equations with the actual formal snapshot; retain
   the implementation-to-test map and finite-bound assumptions.
2. Complete every frozen main, control and robustness case; resolve
   audit failures and link each empirical sentence to its complete evidence.
3. Copy only verified references actually used; correct the two stale draft
   keys noted above; preserve DOI/venue/reading-scope boundaries.
4. Write abstract and conclusion from completed results, including adverse
   or null findings. Remove all planning language and pending placeholders.
5. Finalize accurate anonymous AI disclosure and resolve actual prior-work
   submission status. No fabricated funding or authorship declarations.
6. Compile and export the same current source; inspect actual PDF page
   count, embedded fonts, extracted text, metadata and every rendered page.
   The target is at most nine pages with readable IEEE 10-point layout;
   this blueprint's allocation does not certify that target.

Source records used: `secon2027_official_requirements.md`,
`secon2027_baseline_fidelity.md`, `secon2027_algorithm_spec.md`,
`secon2027_analysis_spec.md`, `secon2027_acceptance_matrix.md`,
`secon2027_codex_execution_plan_20261104.md`,
`icc_citation_audit_20261104.md`, `icc_literature_revision_20261104.md`, the
four `icc_literature_20261104/*_sources.md` reports and the verified ICC
BibTeX corpus. These are internal provenance paths, not author-identifying
links to insert into the anonymous review PDF.
