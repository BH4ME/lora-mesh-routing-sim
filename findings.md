# Findings

## 2026-10-06 algorithm-boundary review

- `meshecho_cpr.py:199` exposes `choose_recovery_action`, whose strict order is
  `R_REPEAT` before `F_RECOVERY`, with deadline checks at the actual TX start.
- `lora_mesh_sim.py:3840` defines a separate `MeshEchoCPR` source/recovery
  lifecycle; its initial, repeat, recovery, ACK validation, and relay ledger
  hooks are CPR-specific. The CPR path does not call `choose_start_action`.
- `MeshEchoCPR(MeshEchoDRC)` is implementation inheritance for route records,
  PHY-facing forwarding, and shared ledgers. It is not evidence that CPR uses
  DRC's source policy, but the inheritance should be described explicitly or
  refactored into a neutral substrate if publication optics require it.

## 2026-10-06 PDF visual review

- `paper/icc2027/build-2_1_27-cpr-final/icc2027_lora_mesh.pdf` is five-page
  Letter, has embedded Type 1 fonts, no CJK characters, and clean two-column
  layout on pages 1--5. Use it as the final build source.
- `paper/icc2027/build-cpr-balanced-5/icc2027_lora_mesh.pdf` is also valid but
  begins references at the bottom of page 4; it is not the preferred visual
  artifact.

## 2026-10-06 regression launcher diagnosis

- Bare `/Users/bh4me_macair/Library/Python/3.9/bin/pytest` failed at test
  collection because its launcher did not expose the repository root.
- `/usr/bin/python3 -m pytest` collected `tests/test_meshecho_cpr.py` normally;
  rerun the full regression through the module launcher.

## 2026-10-06 clean formal rerun

- Development and holdout manifests both record clean revision
  `a013067ebf5d7ba7031d38634f7caf3bfda99dbb`, version `2.1.27`, and the
  expected split/stage. Independent audits pass all checks.
- Full regression is `1182 passed, 1 skipped`. The final PDF is five-page
  Letter with embedded fonts, `HAS_CJK=False`, and authors `Zu Gao`/`Zhi Quan`.
- Only formal development/holdout artifacts and gate reports belong in the
  release commit; exploratory/smoke artifacts and intermediate PDF builds are
  excluded.

## 2026-10-06 release closure checkpoint

- The current release metadata is now `2.1.27`; the previous 2.1.25/2.1.26
  protocol-family comparison remains historical and is not used as CPR
  evidence.
- The canonical ICC PDF is byte-identical to the visually checked
  `build-cpr-balanced-5` artifact, has five Letter pages, and has SHA-256
  `01cab1928e1eb8f583e3d42c873ff020de8518dfdf81bf45482136cebdba30`.
- README, experiment plan, submission checklist, and release metadata now
  identify MeshEcho-CPR as the current method and point to the audited
  development/holdout manifests.
- Remaining proof obligations are command-level verification and a careful
  staged-file review; no new algorithm tuning or holdout rerun is allowed.

## 2026-10-06 final verification continuation

- CPR development audit passed again for `92200..92219`; holdout audit passed
  again for `92300..92319` with the development prerequisite hash.
- The full regression completed with `1181 passed, 1 skipped`.
- The final manuscript build is
  `paper/icc2027/build-cpr-balanced-5/icc2027_lora_mesh.pdf`, five Letter
  pages. Rendered pages show balanced final references and no visible layout
  defect.
- The relay-ledger sentence in the manuscript now states the actual local
  index `(relay, origin, flow, request, marker)` and separately describes the
  stored endpoint/path checks; no algorithm or artifact was changed by this
  wording repair.
- No VERSION, canonical PDF, Git commit, GitHub push, or EDAS action has been
  performed yet.

## CPR PDF finalization (2026-10-06)

- The current ICC source is a CPR paper, not the old SR paper. The title,
  abstract, method, controls, tables, figure, limitations, and conclusion all
  use CPR holdout evidence.
- `pdftoppm` rendered the current build successfully at 150 dpi. The PDF has
  five letter-size pages and no visible clipping, overlap, or broken glyphs.
- Page 5 is visibly unbalanced: references occupy only the left column. Add
  IEEEtran-compatible `balance` support immediately before the bibliography,
  then rebuild and re-render.
- The only reported LaTeX warning is an `Underfull \\hbox` in the mechanism
  paragraph around source lines 277--287; it is not an overfull or clipped box.
- Repository-wide old SR/PRR terms remain in historical planning documents;
  this is acceptable only if the final manuscript and release metadata do not
  accidentally retain them as CPR claims.


## 2026-10-06 - CPR Manuscript Migration Checkpoint

- The current ICC source is still the old 2.1.26 calibrated max-min paper;
  it must not be edited by replacing numbers in place without changing the
  method and claim boundary.
- The new paper must describe CPR as the source/recovery state machine plus
  physically ACK-terminated relay cancellation, and must retain DRC as a
  negative control rather than presenting it as the method.
- Paper numbers will be regenerated from the audited CPR development and
  holdout manifests, not from the existing `paper/icc2027` figures or legacy
  CSVs. No version bump or publication update is authorized yet.

## 2026-10-06 - CPR Exploratory Exposure Decision

- The corrected exploratory bundle
  `results/meshecho_cpr_exploratory_92020_92029_20261006.manifest.json` is
  evidence-v2 valid: 40 paired runs, 160 scheduled flows, 698 transmissions,
  5584 RX attempts, 97 accepted ACKs, and zero incomplete RX/TX joins.
- It fails the predeclared mechanism exposure gate. Across all ten CPR seeds,
  `R_REPEAT=0` and `F_RECOVERY=0`; the only distinctive events are 240
  initial-F relay cancellations. This workload has one fixed flow per pair in
  a dense eight-node case, so it mostly measures initial FLOOD cancellation,
  not recovery after an unACKed routed DATA.
- This is a no-go for the current workload, not a positive CPR effect and not
  evidence against the preserved simulator substrate. No development cohort,
  paper claim, VERSION bump, GitHub push, or EDAS action is authorized.
- A follow-up contract must create repeated same-pair flows after a route is
  learned and include frozen device-local fading/collision opportunities that
  can expose an unACKed routed DATA. The contract must be written before new
  seeds are run.
- The follow-up exposure contract is now frozen in
  `docs/research/meshecho_cpr_exposure_contract_20261006.md`. The runner has a
  named `CASE_PROFILES["exposure"]` so the case is executable and hashed rather
  than reconstructed from ad hoc command-line values.
- The exposure bundle
  `results/meshecho_cpr_exposure_92100_92109_20261006.manifest.json` passed
  evidence-v2 validation with 40 runs, 1292 scheduled flows, 4803 physical
  transmissions, 96060 RX attempts, 1233 accepted ACKs, and zero incomplete
  joins. It exposed 279 started `R_INITIAL`, 16 `R_REPEAT`, 13 `F_RECOVERY`,
  and 853 `cpr-cancel` events; every seed had repeated directed pairs and
  candidate/control divergence. CPR mean TX airtime was `6.3533824 s` versus
  `10.2718464 s` for DRC no-rescue (-38.15%), and its mean deadline ACK PDR
  was `0.97518` versus `0.91634`.
- These numbers are exposure evidence only. They justify a predeclared
  development cohort, not a paper claim; the confirmatory gate remains to be
  computed independently on fresh seeds.
- Development manifest
  `results/meshecho_cpr_development_92200_92219_20261006.manifest.json` and
  report `results/meshecho_cpr_development_92200_92219_20261006.gate.json`
  pass independent audit. The candidate has 40 started repeats and 26 started
  recovery FLOODs. Against no-rescue, ACK-PDR delta is `+0.03837`
  (95% CI `[+0.02072,+0.05602]`), delivery delta is `+0.03757`
  (`[+0.01900,+0.05615]`), and mean airtime is `7.0546176 s` versus
  `9.8823296 s` (about `-28.23%`). Against no-cancel, both reliability lower
  bounds remain above `-0.05` and airtime is about `-32.69%`.
- Development is still not a paper claim. Holdout must be run with a checked
  development report and audited independently before any ICC rewrite.
- Holdout manifest
  `results/meshecho_cpr_holdout_92300_92319_20261006.manifest.json` and report
  `results/meshecho_cpr_holdout_92300_92319_20261006.gate.json` pass the full
  audit, including the development report SHA. The candidate has 26 started
  repeats and 21 started recovery FLOODs. Against no-rescue, ACK-PDR delta is
  `+0.03337` (95% CI `[+0.01720,+0.04954]`), delivery delta is `+0.03644`
  (`[+0.01907,+0.05381]`), and mean airtime is `6.2903424 s` versus
  `9.4334592 s` (about `-33.32%`). Against no-cancel, ACK and delivery lower
  bounds are `-0.00281` and `-0.00485`, both above the `-0.05` margin, while
  mean airtime is about `-40.95%`.
- The CPR result now has development and untouched holdout support. It can be
  used to rewrite the ICC manuscript, but claims must remain conditional on
  this exact case and should state that the contribution is the source/recovery
  state machine plus ACK-terminated relay suppression, not a new PHY.

## 2026-10-06 - CPR Controller Slice 1

- The successor is now represented by a new public module, `meshecho_cpr.py`,
  with a source-local `CprObservation` and `choose_recovery_action` API.
- The first invariant is intentionally stronger than a DRC guard tweak:
  CPR cannot start FLOOD recovery before a same-path repeat has physically
  started. A deadline-infeasible repeat yields a no-start decision rather than
  silently skipping to an unbounded recovery action.
- This is behavior-level implementation evidence only. It does not establish
  a network effect, novelty, or ICC-ready result; the physical relay path,
  ledger, matched controls, and fresh experiments remain to be implemented.

## 2026-10-06 - CPR Source/Relay Slice 2

- `MeshEchoCPR` now has an independent simulator protocol identity and a
  no-cancel shadow. It reuses the packet/PHY/channel substrate but does not
  invoke DRC's reservation guard or marker-2-only ACK validator.
- In a matched two-node failure fixture, the source TX order is physically
  `DATA(None) -> DATA(1) -> FLOOD(2)`, and the recovery marker-2 FLOOD appears
  only after the marker-1 repeat has started. A normal marker-none ACK before
  the repeat prevents both later actions.
- In a three-node line, a destination ACK overheard by an off-path relay
  cancels both an initial marker-none and a recovery marker-2 pending relay
  before commit; the no-cancel shadow still transmits the relay copy.
- These are deterministic behavior fixtures, not population effects. The
  ledger still needs broader malformed-ACK/commit-boundary tests and a
  stream-backed artifact runner before CPR can be compared scientifically.

## 2026-10-06 - CPR Smoke Runner Boundary

- The CPR runner must have its own schema, source hashes, case hash, and
  manifest. Reusing DRC's artifact label would make an independent algorithm
  look like a parameter arm and would allow stale DRC results to be confused
  with CPR evidence.
- The first paired smoke will include CPR cancellation, CPR no-cancel shadow,
  DRC no-rescue, and DRC candidate controls. It will freeze all input identity
  fields per seed and persist physical request/TX/RX/ACK evidence before any
  effect interpretation.

## 2026-10-06 - DRC Evidence Boundary

- A defensible rewrite is a new source-control state machine on the existing
  physical simulator, not a wholesale rewrite of the radio model. The old
  MeshEcho-SR implementation makes its source decision at application
  enqueue and depends on inherited discovery/aging/miss state; parameter
  changes would not establish a new algorithm.
- `MeshEchoDRC` currently provides the intended independent actions
  (`R_RESERVED`, initial `F`, `R_ONLY`, recovery `F`, and deadline no-start),
  but the current integration is not yet a population result. A controller
  unit test cannot replace an auditable physical TX/RX/ACK artifact.
- The next evidence must be paired by identical case/topology/application
  trace and stable event ordinal, include all scheduled flows in the
  denominator, and distinguish started, canceled, rejected, and cutoff
  requests. Late spillover remains charged to network cost while deadline
  success is censored at the original flow deadline.
- Do not use the existing 2.1.26 charts or CSVs as DRC evidence. The ICC
  manuscript can be rewritten only after a frozen development gate and an
  untouched holdout both pass their declared integrity checks.

## 2026-10-06 - DRC Development Gate Outcome

- The frozen development cohort `62001..62020` completed with the stream
  runner and its full request/TX/RX/ACK audit passed. The final manifest is
  `results/meshecho_drc_development_stream_62001_62020_20261006.manifest.json`.
- The joint gate failed on the predeclared cost comparison against
  `meshecho-drc-no-rescue`: candidate mean TX airtime was `36.8304512 s`,
  control mean was `27.8528640 s`, exceeding the 10% ceiling. It passed the
  ACK lower-bound, destination lower-bound, all-F cost, R_RESERVED exposure,
  recovery-F exposure, and accepted-ACK provenance checks.
- The candidate produced `689` R_RESERVED starts and `81` actual recovery-F
  starts, but zero reserve-caused initial-F decisions. Therefore the specific
  reserve admission fallback is unexposed, and the aggregate result cannot
  support a claim about that branch.
- No holdout is authorized. The development result is a valid negative gate
  for this frozen DRC candidate. A successor must be a declared algorithm
  redesign or a documented no-go, not a post-hoc retuning of the holdout.

## 2026-10-06 - Successor Design Boundary After DRC Failure

- The DRC result is not a simulator or artifact failure. Its complete audit
  passed, and its reliability effect is real in the frozen development trace,
  but the recovery action is too expensive: 81 recovery-F starts produced 32
  deadline source ACKs, 47 deadline deliveries without a source ACK, and two
  flows with neither outcome. The candidate mean TX airtime was 36.8304512 s
  versus 27.8528640 s for no-rescue (+32.2%).
- The next implementation is therefore a new successor contract, not a guard,
  TTL, safety-margin, or cost-threshold tweak. The sealed `62001..62020`
  artifacts cannot be reused as performance evidence for that successor.
- The selected research hypothesis is **MeshEcho-CPR** (cost-responsive
  recovery): a new source recovery FSM with an explicit bounded recovery
  budget, plus a device-local terminal-ACK cancellation rule for still-
  uncommitted FLOOD relay handles. Cancellation is allowed only after a real
  physical ACK decode with matching flow, marker, endpoints, path and sender;
  no delivery oracle or future event may be read.
- CPR is not yet a result or novelty claim. It must first pass public RED/GREEN
  behavior tests, a fresh mechanical smoke, independent artifact checks, and a
  new exploratory exposure screen. If the cost/reliability tradeoff fails, the
  correct outcome is a documented no-go rather than further tuning.

## 2026-10-05 Verified 493xx Archive And Core Decision

- An independent read-only audit passed: all six JSONL files and five source
  hashes match the manifest; 70 seed-arm runs, 2,793 scheduled/joined flows,
  16,935 actions and 35,574 physical TXs reconcile, as do 54 paired
  intervals. There were no TXs outside the declared window. This establishes
  archive integrity, not treatment causality or ICC-ready performance.
- Across ten exploratory seeds, old DCB had 376/399 source ACKs and 500.36 s
  complete-network airtime; replacing D with R/F had 373/399 and 395.95 s.
  Equal-seed relative airtime changed -20.97% (descriptive 95% interval
  [-30.88%, -11.06%]), while ACK changed -0.73 percentage points
  ([-3.33, +1.87]); ACK noninferiority is not established.
- All 35 old-DCB D actions obtained candidate DATA and none had discovery
  timeout fallback. Their RREQ/RREP used 20.6% of old-DCB network airtime.
  This is a plausible efficiency target, not proof that D is dispensable.
- The trial and blind arms had identical first source actions, paths, ACKs,
  delivery and normalized physical TX traces across the 399 paired flows.
  The reversible trial therefore cannot currently support a distinct core
  contribution. The simple no-switch arm differed and sometimes did better.
- The existing trigger-F control consumes a source token and updates the
  discovery timestamp as D does, whereas source-FR does not. A new D/R/F
  branch experiment must match or factorize that bookkeeping, as well as
  source state, feedback and recovery budget; the seven-arm run alone cannot
  attribute the difference to R versus useful-F physical action.
- A corrected accepted-ACK join found 32/34 aging-D opportunities with a
  same-pair ACK younger than 120 s, not the initial 28/34 count that omitted
  marked backup ACKs. Thus a 120-s staleness split has almost no support in
  these seeds. Ten old routes were one hop and 24 multihop; neither split
  alone authorizes an online classifier. The draft branch design is in
  `docs/research/meshecho_d_trigger_matched_branch_design.md`.
- The first matched-D implementation slice captures queued event and protocol
  state using stable dataclass/callback summaries. A target prefix can contain
  future `tx_request` events whose `PendingSend` callbacks are not directly
  JSON serializable. Initial useful, discovery, ACK and rescue reception
  streams are role-separated; FLOOD jitter also uses role and attempt ordinal.

## 2026-10-05 Seven-Arm Diagnostic Readiness

- The new `meshecho-dcb-source-trigger-f` control sends a payload-bearing F
  at the old D aging trigger while retaining DCB ACK feedback and recovery.
  Public tests establish the intended wire contrast, but no population run
  yet establishes an endpoint or airtime effect.
- The new source-action capture tool records seven arms, raw flow/action/TX
  archives and hashes. Its synthetic tests pass, but positive capture/CLI,
  paired-trace rejection and a physical recorder smoke still need checking
  before interpreting any 493xx output.
- The preceding goal turn was progress in code/tests, not a finished core
  rewrite or a paper update. No 493xx or reserved seed has run.
- Initial source review confirms the capture tool separately joins RREP
  candidate DATA and post-timeout fallback DATA/F, retains raw TX records,
  and checks a scheduled-trace hash against saved flows. These checks have
  synthetic coverage; actual runner/CLI capture and an independent audit are
  still required before trusting the 493xx artifact.
- `run_one_sr` generates the public case with independent reception streams,
  600-s application generation and 630-s drain for a 30-s deadline. Its row
  uses physical TX starts through the drain cutoff for airtime, bytes and
  modeled TX energy. The new capture tool reconstructs these costs from its
  saved physical TX archive; the real-recorder positive test remains pending.
- Independent audit confirmed a P1 diagnostic classifier error: D-candidate
  DATA can later log `timeout/action=D/reason=source-ack-timeout`; that is not
  an RREP discovery timeout. `_joined_flows` currently accepts every D
  timeout and can miscount `d_timeouts` and physical fallback. The new
  reason-filter test went RED, then GREEN after the scoped fix.
- The audit also found that the first validator checked only windowed
  airtime/bytes/TX energy, so it could lose a future-start TX or accept a
  wrong-arm/flow packet. Public RED/GREEN tests now require raw/windowed/
  queued TX counts and packet attribution. A real seed-17 seven-arm CLI
  capture uncovered a default-bound seed bug; it too went RED then GREEN.
- Paired energy previously mixed windowed TX and raw/unwindowed RX model
  energy. The summary now reports their deltas separately; the design note
  forbids treating their sum as one endpoint. No 493xx run has begun.
- Post-fix independent re-audit found no remaining P1 in capture,
  provenance and energy scope; the full suite passed 1101 tests with one
  skip. The fixed seven-arm inputs are 49301--49310 on `recurring_fading`,
  30-s deadline, 630-s cost cutoff and case hash
  `b3cfb113aded1b1487cf2a5426225cb1188143384a6fe90b770b855e5273b491`.
- The current ICC five-page manuscript still states the old calibrated
  algorithm and old 793/813-flow result numbers. A new core requires
  replacing its abstract, method, policy table, result tables, figure,
  numerical discussion and conclusion from fresh verified evidence.
  Prior-art coverage for route repair/alternate ACK/LoRa opportunism is
  incomplete. Do not transfer old effect sizes to the rewritten core.
- The once-only 49301--49310 seven-arm artifact was created and its initial
  manifest inspection found 70 runs, 2793 flow records and 35574 physical
  TX records, with per-file hashes and current source/case hashes matching.
  Independent raw-archive verification is still in progress.
- Initial exploratory totals (399 scheduled unicasts per arm): old DCB
  376 ACK / 397 delivered / 500.36 s airtime; source-FR 373 / 399 /
  395.95 s; D-trigger useful-F 367 / 397 / 451.50 s; trial and blind
  each 368 / 398 / 422.86 s; no-switch 374 / 399 / 421.14 s; fixed-2-s-F
  contextual arm 381 / 398 / 497.66 s. The 10-seed mean relative airtime
  versus DCB is -20.97% for source-FR, -9.33% for trigger-F and -15.52%
  for trial. Trial and blind aggregate counts and cost are identical again.
  These are exploratory descriptions, not accepted new-core effects.
- Old DCB made 35 D decisions (34 aging, one cold); all 35 began RREQ and
  physically sent candidate DATA, with no RREP timeout fallback. A first
  ad hoc `jq` sum of replacement-action objects merged keys instead of
  adding counts; its displayed F/R values were invalid. A corrected numeric
  reduction finds that those same application identities are 34 R/one F in
  source-FR, versus 30 F/five R in trigger-F. Earlier closed-loop state can
  differ, so these are identity-aligned descriptions, not per-flow
  counterfactual effects.
- A read-only join across the saved 493xx flows finds zero trial-versus-
  blind differences in first source physical action, first path, deadline
  ACK or destination delivery across 399 shared identities. Their all-flow
  airtime totals also match exactly. This replicates the 492xx mechanism
  NO-GO and is evidence against retaining reversible trial as the core.
- Earlier archived source-risk work found a descriptive one-hop/R-miss
  association but failed its prespecified cell-support gate; it cannot be
  promoted into a new decision rule. The rejected JFC contract also rested
  on an uncalibrated reverse-ACK predictor and an expensive alternate-ACK
  path. A new source decision needs a same-state, same-wire D/R/F branch
  comparison and a separate untouched prospective evaluation.

## 2026-10-05 Public Trial Screen

- The prospectively specified 49201--49210 nonreserved five-arm screen is
  complete. It observed 14 physically started two-hop R trials across eight
  seeds, 11 ordinary trial ACK commits, and three source-guard abandonments.
  These counts pass its exposure-only floor, not an effect gate.
- On all ten seeds, trial versus same-wire blind switch had zero measured
  source action/path divergence and zero paired source-ACK, destination-PDR,
  and whole-network-airtime difference. Thus the current reversible-trial
  branch has no demonstrated causal value against blind promotion in this
  workload; this is a reason to diagnose or redesign, not to open holdout.
- Exploratory trial-versus-old-DCB means were -18.09% relative whole-network
  airtime and -2.49 percentage points source-ACK PDR; versus fixed-2-s F,
  -23.20% airtime and -2.09 percentage points ACK PDR. These ten-seed
  descriptions are not confirmatory or ICC performance claims.
- A separate trial-centered quantitative/physical-provenance gate now exists
  in the draft runner, and holdout requires its audited result. The old DCB
  component gate cannot substitute for it. Latest focused runner/DCB tests:
  87 passed; full regression after this edit remains outstanding.
- The full current tree passed 1070 tests with one skipped after the gate
  edits. A later isolated interleaved-flow witness passes separately.
- Trial/blind identity has a structural explanation: both send the same
  first two-hop R after a marked ACK; trial success converges the route
  state, and a trial miss makes both arms select the same F recovery and
  next F action. The screen saved initial actions/paths and aggregate
  endpoints, not full 492xx physical traces, so complete packet-trace
  equality is unproven. A deterministic overlapping same-pair test shows
  the trial and blind paths can differ while the first trial is active.
- Archived 46xxx passive evidence rejects selective split-ACK as the next
  full-core bet: of 99 age-valid nominated direct R sends, 52 direct DATA
  packets reached the destination and only three missed the initial direct
  ACK. Current received SINR was not saved, so no device-local threshold
  can be checked from this archive. Thirty-six age-valid failed direct
  DATA sends had nominee reception across 17 seeds; that forward-failure
  branch has substantially greater necessary exposure, though still no
  measured treatment effect. See `meshecho_selective_split_ack_triage.md`.
- The independently rejoined 46xxx DHR archive has 70 source D decisions:
  67 age-triggered and three cold-triggered. All 70 physically sent an
  RREQ; 64 produced candidate DATA, six timed out to the old R path.
  D-decision flows were source-ACKed 66/70 and destination-delivered
  68/70; candidate DATA flows were ACKed 61/64. Network RREQ and RREP
  airtime totals were 196.789504 s and 9.197824 s, jointly 19.0% of
  1084.446208 s complete-network airtime. These are selected DHR flows
  and gross control cost, not an avoidable causal saving in DCB.
- Among 61 age-triggered D candidates, 54 chose a different path from
  the old route, seven the same; eight shortened, 35 kept hop count, and
  18 lengthened. The new seven-arm 493xx diagnostic includes DCB-wire
  payload-bearing F at the old D trigger to measure a simple refresh
  alternative before a new source controller is designed.

## 2026-10-05 Trial-Core Resume

- The prior unfinished refactor left one extra `)` in the newer-direct-ACK
  route-commit call. `py_compile` reproduced it at line 3805; removing the
  unmatched bracket restored compilation and 100 adjacent tests. This was a
  syntax issue, not evidence of algorithm performance.
- The trial source's distinct actions are observable in code: pending backup
  ACK evidence leads to one two-hop R trial, an ordinary R ACK commits it,
  and one unresolved R miss selects F. The old simulator/PHY remains the
  matched test infrastructure. Causal benefit and MCU boundedness remain
  unproven; full regression and independent semantic audit are pending.
- Independent review reproduced two real stale-generation paths. A delayed
  old R timeout could set the miss flag after a new F ACK route commit; a
  new F ACK could leave an old active trial occupying the pair. Both now
  have public RED/GREEN timelines, and independent re-audit found no new
  defect in the scoped fixes. Same-flow recovery remains active.
- The staged runner's trial/no-switch/blind controls and event-provenance
  checks pass their 34-test module, including a nonreserved physical positive
  fixture. The full suite passed 1040 tests, one skipped, after the behavior
  fixes; two later route-expiry/LRU tests passed separately. None of this is
  a matched population effect or ICC acceptance estimate.
- A suspected runner false rejection was checked against two real physical
  traces. Same-flow F recovery follows its guard-abandonment event, so it
  cannot generate the feared ACKed-at-abandonment event. A cross-flow F
  commit does emit new-route-commit abandonment while the trial is unACKed;
  the unchanged audit accepts it. Two tests document the invariant.
- The current staged `project_gate` applies only to old DCB. Trial/no-switch
  and blind comparisons are descriptive; a trial-negative development set
  could otherwise unlock holdout through an unrelated DCB pass. A separate
  draft trial-core gate is now written in the trial contract but not coded
  or frozen. The nonreserved 49201--49210 screen is exploratory only.

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

- The prior fairness revision was repository version `2.1.11`; the current
  recovery-budget revision is repository version `2.1.12`;
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

## 2.1.12 Audit Questions

- Formalize the `calm-mesh` route-miss fallback setting so the recovery
  contribution can be measured without temporary monkey-patching.
- Use paired seeds and the same main-scene topology/traffic to estimate the
  effect of disabling only route-miss fallback.
- Keep the result separate from the confidence-only route-conflict experiment:
  fallback is a recovery mechanism, not evidence of confidence ranking.
- Keep the original frozen matrix unchanged; the new audit is a sensitivity
  result for the 2.1.12 revision.

## 2.1.12 Audit Result

- The recovery-budget script now reports route-discovery success rate as
  `route_discovery_successes / route_discovery_attempts` and includes the
  attempt count in the Markdown table.
- In the paired 20-seed main-scene replay, mean route-discovery success rates
  were `0.834` for MeshCore-like, `0.798` for CALM with route-miss fallback,
  and `0.805` for CALM without route-miss fallback.
- The corrected rate metric does not change the PDR or airtime results:
  fallback versus no fallback is `+0.009 +/- 0.018` ACK PDR and
  `+0.023 +/- 0.023` destination PDR, with `+15.9 s` airtime.
- This supports the narrower conclusion that MeshEcho was not favored by an
  easier route-discovery process in this replay, while the comparison remains
  a sensitivity audit rather than a fully budget-matched baseline study.

## 2.1.12 Route-TTL Audit Result

- The native main matrix uses a `300 s` MeshCore-like route-cache TTL and a
  `600 s` CALM/MeshEcho TTL. Because the workload reuses eight fixed pairs,
  this is a real favorable bias toward MeshEcho.
- After matching MeshCore-like to `600 s`, its ACK PDR rose from `0.381` to
  `0.519`, destination PDR from `0.652` to `0.722`, and airtime fell from
  `970.9 s` to `905.5 s`.
- The paired TTL effect was `+0.138 +/- 0.031` ACK PDR and
  `-65.4 +/- 14.1 s` airtime. The remaining matched-TTL MeshEcho difference
  was `+0.209 +/- 0.071` ACK PDR and `-58.2 +/- 19.2 s` airtime.
- Therefore the native `+0.347` ACK-PDR gap overstates the more comparable
  matched-TTL bundle difference by `0.138` in this replay. The current paper
  now reports the matched audit and does not present the native gap as a
  strategy-only effect.

## 2.1.12 Final Verification

- The updated manuscript compiles to 9 pages after adding the TTL fairness
  audit. The root PDF is PDF 1.5 with SHA-256
  `97a5fc593a60ea1295697d0e90df09940ade0c158c54f290c611308598b70920`.
- The latest rendered pages were visually inspected; no clipping, overlap, or
  unreadable table/figure was found.
- Final checks report `47 passed`; Python compilation, shell syntax, CLI help,
  and `git diff --check` passed.

## 2.1.13 Fairness Recheck

- The user's concern is justified for the original headline setup: the
  3 km/SF9/fixed-pair matrix is favorable to route caching and too easy to
  expose link-quality conflicts. It should remain labeled as a
  contention-oriented operating point.
- The favorable TTL bias is quantified rather than hidden: matching
  MeshCore-like from 300 s to 600 s raises its ACK PDR from 0.381 to 0.519,
  leaving a matched protocol-bundle difference of 0.209 rather than the native
  0.347.
- The random-pair non-saturated probe removes pair reuse and retains an
  airtime advantage for MeshEcho, but its ACK PDR is 0.413 versus 0.456 for
  source-route caching. The one-shot Smart-CALM versus no-confidence delta is
  +0.001 with a 95% interval containing zero.
- The controlled route-conflict experiment supports only a bounded mechanism
  claim: confidence helps when the shorter candidate contains a materially
  weaker hop, not as a general topology-independent advantage.
- The revised conclusion is therefore fairer: shared-harness comparison is
  valid, but the scenario is not a neutral deployment benchmark and the
  evidence does not establish universal confidence-ranking superiority.
- The 2.1.13 paper compiles to 9 pages with bundled Tectonic; root PDF SHA-256
  is `aa2c2e5e171595256938be222a2cca7757dbbdc8bb516e4cc640dc2f2d300cbe`.
- Final validation reports 49 passing tests, successful Python and shell
  checks, clean diff whitespace, and no unresolved citation warnings.

## 2.1.13 Final Publish Verification

- Commit `fe24d1d` is synchronized with `origin/version/v2`.
- PR 1 is OPEN/DRAFT and now describes the 2.1.13 fairness-focused
  evaluation.
- The root PDF is 9 pages, PDF 1.5, and matches the verified Tectonic build
  with SHA-256
  `aa2c2e5e171595256938be222a2cca7757dbbdc8bb516e4cc640dc2f2d300cbe`.
- The fairness revision is complete. The evidence boundary remains:
  fair shared harness, biased frozen workload, matched-TTL sensitivity,
  non-dominant random-pair result, and bounded route-conflict mechanism
  evidence.

## 2.1.14 ICC Quality-Gate Result

- Added `validate_non_degenerate_regime()` and `ProbeRegimeError` to enforce
  connected-multihop evidence quality per seed rather than by aggregate mean.
- The gate rejects any seed with direct-link PRR-below-0.99 fraction below
  `0.10`, fewer selected pairs than requested, or mean selected graph distance
  below `2.0` hops. Random-pair probes remain diagnostic and are not forced
  through the connected-pool checks.
- Added regression tests for one accepted seed and three rejection causes;
  full discovery now reports 52 passing tests.
- The ICC shell script runs a three-seed, 180 s, 50-node, 18 km connected
  quality probe after the four matrix scenarios by default. Set
  `ICC_RUN_QUALITY_PROBE=0` for explicit legacy reproduction.
- The real 2.1.14 probe passed all seeds with 24/24 candidate pairs, mean
  graph distance `2.014` hops, direct-link PRR-below-0.99 fraction `0.641`,
  and PRR-below-0.50 fraction `0.445`.
- The complete ICC shell smoke also passed after correcting the CLI alias from
  internal `meshcore-like` to the public `meshcore` protocol choice.
- The generated versioned CSV/Markdown evidence is intentionally included in
  this release; temporary smoke outputs were moved out of the repository.

## 2.1.15 Continuation Audit

- A completed 2.1.15 experiment session produced
  `results/meshecho_v2_1_15_icc2027_50n_unicast_pairs*` and
  `results/meshecho_v2_1_15_icc2027_50n_mixed*` only.
- No `meshecho_v2_1_15_icc2027_connected_multihop_quality` or
  `meshecho_v2_1_15_icc2027_calibrated_multihop` artifacts exist yet.
- Because the ICC paper's main claim depends on the calibrated non-saturated
  multi-hop matrix and the per-seed quality gate, the current version bump is
  incomplete and must not be published as a finished release.

## 2.1.15 Evidence and Paper Findings

- The full 2.1.15 workflow completed with all expected versioned artifacts.
- The calibrated matrix is non-degenerate by construction and measurement:
  20 seeds, 24 selected pairs per seed, graph distance 2.0, direct-link
  PRR-below-0.99 fraction 0.160, and PRR-below-0.50 fraction 0.046.
- CALM/MeshEcho mean ACK PDR is 0.720 versus MeshCore-like 0.537, with mean
  airtime 28.1 s versus 38.5 s. Smart-CALM minus no-confidence is +0.181
  ACK PDR (paired 95% CI [+0.094,+0.268]); Smart-CALM minus no-fallback is
  +0.002 ([-0.020,+0.024]).
- The 18 km quality gate is deliberately harsher: it passes all three seeds
  with mean graph distance 2.014 and direct-link PRR-below-0.99 fraction
  0.641, but MeshCore-like discovery success is only 0.178. It remains a
  discovery stress diagnostic rather than a main performance table.
- The new ICC manuscript is 3 pages, uses ICC 2027 wording, and does not
  claim physical validation or topology-independent dominance.

## 2.1.15 Publish Verification

- The complete release is published through commits `fb133ba` and `2ebefd1`;
  `origin/version/v2` resolves to `2ebefd13b41fe196f0df9092fafd38714ed6b59c`.
- PR 1 is OPEN/DRAFT at
  `https://github.com/BH4ME/lora-mesh-routing-sim/pull/1` with the updated
  2.1.15 title and evidence boundary.
- GitHub reports no configured checks on `version/v2`; the local verification
  suite and versioned experiment artifacts are therefore explicitly recorded
  rather than presented as remote CI results.

## ICC Submission-Readiness Boundary

- Official ICC 2027 guidance confirms the six-page initial-submission hard
  limit, English IEEE 10-point format, PDF-only EDAS upload, and exact EDAS
  title/author-list match. It also states that accepted work must be
  registered and presented for proceedings/Xplore publication.
- The compiled paper satisfies the format/page/evidence checks, and the source
  now contains the user-provided author metadata. Exact EDAS title/author
  registration and venue actions remain the pre-submission boundary.

## 2026-09-19 - Historical ICC Hardware-Evidence Audit

- The official ICC 2027 submission guidance specifies language, IEEE format,
  page limit, EDAS/PDF handling, originality, registration, and presentation;
  it does not state a universal requirement for a physical testbed or hardware
  prototype.
- A DOI/abstract audit of ten ICC papers found both simulation/analysis-only
  evidence and simulation plus measurements. The sample is not a systematic
  acceptance-rate study, so it supports a venue-practice conclusion rather
  than a guarantee of acceptance.
- Hardware/testbed-positive examples:
  - To et al., ICC 2018, ``Simulation of LoRa in NS-3: Improving LoRa
    Performance with CSMA'', DOI `10.1109/icc.2018.8422800`: an NS-3 module
    is validated against measurements from a real-world testbed, then used for
    the CSMA study.
  - Rochester et al., ICC 2020, ``Lightweight Carrier Sensing in LoRa:
    Implementation and Performance Evaluation'', DOI
    `10.1109/icc40277.2020.9149103`: reports feasibility measurements in
    real-world LoRa networks and also uses a custom simulator.
- Analysis/simulation-positive examples:
  - Georgiou et al., ICC 2020, ``Coverage Scalability Analysis of Multi-Cell
    LoRa Networks'', DOI `10.1109/icc40277.2020.9149081`: stochastic-geometry
    model and mathematical analysis; the abstract does not claim a testbed.
  - Hamdi et al., ICC 2020, ``Dynamic Spreading Factor Assignment in LoRa
    Wireless Networks'', DOI `10.1109/icc40277.2020.9149243`: evaluates the
    proposed assignment using numerical SER simulations.
  - Afisiadis et al., ICC 2020, ``Coded LoRa Frame Error Rate Analysis'', DOI
    `10.1109/icc40277.2020.9148806`: validates analytical FER expressions with
    Monte Carlo simulations.
  - Tu et al., ICC 2020, ``A New Closed-Form Expression of the Coverage
    Probability for Different QoS in LoRa Networks'', DOI
    `10.1109/icc40277.2020.9148720`: provides closed-form analysis and Monte
    Carlo verification.
  - Benkhelifa et al., ICC 2019, ``Minimum Throughput Maximization in LoRa
    Networks Powered by Ambient Energy Harvesting'', DOI
    `10.1109/icc.2019.8761478`: derives collision/optimization results and
    compares algorithmic allocations; no physical testbed is claimed in the
    abstract.
  - Amichi et al., ICC 2019, ``Spreading Factor Allocation Strategy for LoRa
    Networks Under Imperfect Orthogonality'', DOI `10.1109/icc.2019.8761235`:
    reports numerical results for a matching-based allocation algorithm.
- Mixed application evidence also occurs: Shaafi et al., ICC 2022,
  ``Wireless Body Sensor Networks for Sign Language Recognition with
  Real-time Data Analysis'', DOI `10.1109/icc45855.2022.9838474`, reports
  acquired inertial/muscular data and experimental classification results, but
  this is an application/data experiment rather than a communications
  testbed requirement.
- Practical conclusion for MeshEcho: a simulation-only ICC submission is
  defensible if the model, parameters, baselines, statistical protocol,
  quality gates, code/data release, and limitations are explicit. Hardware
  would strengthen external validity, especially for radio sensitivity,
  interference, timing, and duty-cycle claims, but its absence is a stated
  limitation rather than an automatic disqualifier.
- The ICC manuscript should therefore say ``simulation-only evidence'' and
  propose hardware or hardware-in-the-loop validation as future work. It must
  not imply that the current results are measured on SX126x/SX127x devices.

## 2.1.17 Reviewer-Directed Findings

- The current primary ICC table omits `meshtastic-like` even though the
  connected-multihop raw report contains it. The omission makes the comparison
  look selective; the revised primary table should include managed flooding
  with the same shared topology and traffic trace.
- The Smart-CALM/no-confidence ablation changes candidate admission and route
  discovery success (`0.801` versus `0.589` in the reused calibrated report),
  so the end-to-end `+0.181` ACK-PDR difference cannot be called a confidence-
  only causal effect. It should be labeled a complete policy-bundle effect.
- The controlled route-conflict experiment is the appropriate surgical
  evidence: it holds the candidate set fixed and shows confidence selecting
  a longer reliable path only when the shorter path is artificially weakened.
  The manuscript should point to that experiment and keep it distinct from the
  full-network ablation.
- The current paper has one powered non-saturated regime. A versioned
  sensitivity runner should add at least SF variation and offered-load
  variation under the same connected-pair selection and quality gate.
- New sensitivity outputs must be inspected for gate failures and reported as
  robustness evidence, not silently pooled with the primary estimand.

## 2.1.17 Implementation Findings

- `tools/run_icc_sensitivity_experiments.py` now reuses
  `run_one_probe()`, `validate_non_degenerate_regime()`, `write_csv()`, and
  `write_report()` instead of duplicating simulator logic.
- The SF8 case initially used 8.25 km and then 9 km, but the 20-seed gate
  rejected seed 10 and seed 14 at those settings. A 10 km area passes all 20
  seeds while preserving the connected-pair and graph-hop contract; this
  calibration choice is recorded in the runner, not hidden in the paper.
- A one-seed smoke produced both sensitivity reports with all seven protocol
  configurations. No quantitative paper claim is based on that smoke.

## 2.1.17 Sensitivity Results

- The 20-seed SF8/10-km case passed all per-seed gates. Means:
  managed flooding `0.434` ACK PDR / `39.2 s` airtime, MeshCore-like
  `0.160` / `70.4 s`, CALM `0.435` / `61.7 s`, Smart-CALM `0.402` /
  `61.4 s`, and no-confidence `0.299` / `59.8 s`.
- The 20-seed SF7/4-flows-per-minute case passed all per-seed gates. Means:
  managed flooding `0.409` / `50.5 s`, MeshCore-like `0.411` /
  `151.5 s`, CALM `0.652` / `111.3 s`, Smart-CALM `0.605` /
  `110.9 s`, and no-confidence `0.443` / `109.1 s`.
- The SF8 case is a boundary case: flooding and CALM have nearly equal PDR,
  but flooding uses less airtime. The load case preserves a CALM PDR
  advantage while flooding remains the lower-airtime reference.
- The compiled 2.1.17 paper is still exactly five letter-size pages; the new
  robustness table fits without overfull-box or unresolved-reference warnings.

## 2.1.18 Metric-Baseline Revision

- Added two external quality-aware route-selection baselines to the simulator:
  `etx-mesh` minimizes the sum of `1/PRR` hop costs and `ett-mesh` minimizes
  `ToA/PRR` costs. Both use the same 2-s discovery window, 600 s route TTL,
  shared packet model, and no route-miss fallback.
- The baselines carry a bounded higher-is-better route score through the
  existing RREQ/RREP path field; no simulator channel or delivery semantics
  were changed.
- Test-first coverage is in `tests/test_metric_routing_baselines.py`; the
  first red run failed because `MetricMesh` was not yet implemented, and the
  implementation now passes the new tests and the existing suite.
- A one-seed 600 s connected-multihop smoke produced nonzero ETX/ETT rows and
  confirmed that the fixed-SF configuration makes ETX and ETT numerically
  equivalent, as expected because every packet has the same ToA. The paper
  should report this as a fixed-SF sanity baseline rather than imply an
  independent ToA advantage.

## 2.1.16 Manuscript Revision Findings

- The ICC source now contains related work, an implementation-faithful CALM
  confidence equation, a fixed-parameter table, metric/statistical definitions,
  evidence strata, paired ablation table, discussion, artifact manifest, and
  hardware external-validity boundary.
- Fresh Tectonic compilation at
  `paper/icc2027/build-2_1_16-tectonic-v3/icc2027_lora_mesh.pdf` produces
  exactly 5 letter-size pages, within the ICC six-page initial-submission cap.
- Rendered pages show no clipping or table overlap. References continue onto a
  fifth page, but the manuscript remains readable and uses the requested five
  printed pages rather than artificial spacing.
- Version `2.1.16` is a paper/evidence revision: the calibrated 2.1.15 CSVs
  remain the underlying simulation results and are explicitly identified as
  reused. A fresh reproduction with `OUT_PREFIX=meshecho_v2_1_16_icc2027`
  will create a new output prefix if desired.
- A 600 s, one-seed calibrated connected-multihop smoke run passed the quality
  gate and produced nonzero protocol results (CALM ACK PDR 0.667 versus
  MeshCore-like 0.333 for seed 1). A separate 120 s gate-only smoke was not
  used for quantitative interpretation.
- A redundant full 2.1.16 runner was started but safely stopped during its
  second legacy 20-seed scenario after confirming that the no-code-change
  revision would only duplicate the verified 2.1.15 matrix. Its partial
  untracked outputs are intentionally excluded from the release; the paper
  cites the complete 2.1.15 matrix and the new smoke as the 2.1.16 validation.

## 2.1.16 Publish Verification

- Commit `859686a` is pushed to `origin/version/v2`.
- PR 1 is OPEN/DRAFT with title `[codex] MeshEcho 2.1.16 five-page ICC
  manuscript and hardware audit` and head OID `859686a08f6f47a606851ff309f3b8fbb621516c`.
- The PR body records 53 passing tests, the five-page PDF, the one-seed smoke,
  the hardware-evidence conclusion, and the simulation-only boundary.
- Unrelated old build/render outputs, old 2.1.14 artifacts, partial 2.1.16
  runner outputs, and `tmp/` remain untracked and were not published.

## 2.1.14 Final Publish Verification

- Commit `b5de06b` is present locally and on `origin/version/v2`.
- PR 1 is OPEN/DRAFT with title
  `[codex] MeshEcho 2.1.14 ICC evidence-quality gate`.
- The code, evidence artifacts, version metadata, tests, documentation, and
  resumable state files are published; no further action is pending for this
  revision.

## 2.1.18 MeshEcho Identity and Attribution Findings

- The ICC method is now explicitly `meshecho`; the default ICC protocol tuple
  contains only managed flooding, matched source routing, ETX, ETT, and
  MeshEcho. The adaptive firmware/history line is not part of the ICC matrix.
- Added `MESHECHO_ABLATIONS` with four within-policy controls:
  `meshecho-no-confidence`, `meshecho-no-fallback`,
  `meshecho-no-hop-penalty`, and `meshecho-no-age-penalty`.
- Completed a 20-seed component matrix under the same 50-node/8250-m/SF7
  connected-multihop contract. MeshEcho minus no-confidence is `+0.148`
  ACK PDR with paired 95% CI `[+0.052,+0.244]`; minus no-hop-penalty is
  `+0.050` with `[-0.029,+0.130]`; no-fallback and no-age-penalty are
  `0.000` in this workload.
- The no-fallback and no-age results are reported as workload-specific
  evidence boundaries, not universal component conclusions.
- Regenerated the primary and SF/load reports with no adaptive-firmware
  protocol rows. Added a report regression test that rejects Smart-CALM
  leakage into the 2.1.18 ICC evidence reports.
- Extended the ICC manuscript with the component-attribution result while
  keeping it at exactly five letter-size pages. The final render was checked
  page-by-page; tables and references are readable with only underfull-box
  warnings.
- `VERSION` and ICC-facing docs now target `2.1.18`; the final remote publish
  is still pending.

## 2.1.19 MeshEcho-Only Fairness Revision Findings

- The legacy source-route immediate-reply branch had a regression after the
  matched-window candidate-exposure fix: duplicate destination RREQs could
  emit multiple RREPs. A test now locks the historical one-reply behavior.
- `CalmMesh.route_miss_recovery_ttl()` previously returned `sim.max_hops`
  despite a configured `fallback_ttl`; it now delegates to
  `fallback_ttl_for(flow_id)`, and a test verifies the configured value.
- Targeted regression status after the red-green cycle: `8 passed`.
- All subsequent 2.1.19 evidence must be regenerated after this code change;
  existing 2.1.19 CSVs are not yet authoritative until rerun.
- The corrected reruns completed for the primary, component, SF8/load, and
  cache TTL cases. Primary means are MeshEcho `0.719719` ACK PDR /
  `28.141 s` airtime, matched source-route `0.501558` / `38.461 s`, and
  ETX/ETT `0.660888` / `27.627 s`; the paired MeshEcho-source-route ACK
  delta remains `+0.218` with CI `[+0.041,+0.395]`.
- The corrected fallback TTL changes the cache diagnostic: MeshEcho at TTL600
  is `0.786` ACK PDR / `0.806` destination PDR / `25.7 s`, while TTL30 is
  `0.472` / `0.490` / `88.5 s`, with `18.5` route repairs. These are
  descriptive secondary results, not a causal age-penalty claim.
- The ICC source now compiles to exactly five pages after a concise related-work
  rewrite; rendered pages 1--5 were inspected and are layout-clean.

## 2.1.20 MeshEcho Route-Conflict Attribution Findings

- The controlled route-conflict harness was still subclassing
  `SmartCalmMesh`, despite the ICC manuscript naming MeshEcho as the method.
  This was a semantic evidence mismatch, not merely a label issue.
- Added a regression test that requires `RecordingConflictMesh` to be a
  `MeshEcho` instance and rejects `SmartCalmMesh` as its implementation.
- Replaced the harness base class with `MeshEcho`, retained the explicit
  confidence/no-confidence selector, and removed adaptive profile/timeout
  constructor arguments.
- A fresh 20-seed route-conflict run reports both candidates in 90% of seeds;
  MeshEcho selects the longer path in all observed conflicts and improves ACK
  PDR by `+0.221 +/- 0.096` over the shortest-candidate control.
- The new result is stored in
  `results/meshecho_v2_1_19_icc2027_route_conflict.csv` and
  `docs/results/meshecho_v2_1_19_icc2027_route_conflict.md` pending the
  version-2.1.20 evidence regeneration.
- The manuscript title is being narrowed from “Airtime-Aware” to
  “Confidence-Aware Route Admission” because MeshEcho reports airtime as an
  operating-point metric but does not directly optimize ToA in its score.

## 2026-09-19 - 2.1.20 Acceptance Assessment

- Validation is technically clean: `python3 -m pytest -q` reports 67 passed;
  Python compilation, shell syntax, and `git diff --check` pass.
- The current ICC PDF has six letter-size pages. Six pages is within the
  official ICC initial-submission ceiling, but the project requirement remains
  five pages and the repository checklist is stale because it claims the PDF
  is already five pages.
- The paper is a credible ICC submission candidate but should be scored as
  borderline/weak-reject risk rather than safe accept. The strongest evidence
  is the paired MeshEcho versus matched source-route ACK-PDR/airtime result:
  `+0.218` ACK PDR with 95% CI `[+0.041,+0.395]` and `-10.3 s` airtime.
- The strongest limitation is estimand/generalization: the 20-seed primary
  matrix is conditioned on a PRR-qualified pair pool, every selected pair is
  exactly two hops, and every protocol has zero route-cache hits. It therefore
  measures first-discovery route admission, not general cache reuse or route
  aging.
- MeshEcho versus ETX/ETT is not statistically separated
  (`+0.059`, 95% CI `[-0.108,+0.226]`), and destination-PDR differences also
  include zero. The paper must not imply general reliability dominance.
- The route-conflict audit is useful surgical evidence (`+0.221 +/- 0.096`)
  but is a seven-node controlled topology; it cannot substitute for
  unconditioned random-pair or deeper-hop evidence.
- Hardware is not the main blocker. The ICC practice sample includes
  analytical and simulation-only work, but the paper must keep the
  simulation-only boundary explicit.
- Before submission, prioritize: unconditioned random pairs; 3--5-hop or
  100/200-node scale; one distinct routing baseline; temporal fading/stale
  routes; five-page compression; and final EDAS title/author metadata.

## 2026-09-19 - 2.1.18 Pre-submission Review

The current five-page manuscript is a credible ICC submission candidate, but
it is borderline rather than a safe accept. The strongest evidence is the
matched-harness ACK-completion/airtime tradeoff against the source-route
baseline; the evidence does not establish a statistically separable advantage
over ETX/ETT or a general destination-delivery gain.

The most important reviewer risks are:

1. The calibrated matrix selects 24 graph pairs per seed and all 480 selected
   pair observations are exactly two hops. Each run has only about 5.1
   unicast flows and `route_cache_hits` is zero for every primary row, so the
   experiment estimates first-discovery/route-admission behavior rather than
   route-cache reuse or route-aging behavior. The paper should either add a
   repeated-pair/cache-aging estimand or remove cache/age claims from the main
   contribution.
2. The `meshecho-no-confidence` delta is not a fixed-candidate causal effect:
   discovery success, cached-route count, and selected route length also
   change. It must be described as an end-to-end policy-bundle effect unless a
   fixed-candidate replay/control is added.
3. ETX and ETT are mathematically identical under fixed SF and fixed payload
   time-on-air. They are a sanity check, not two independent strong baselines;
   a min-hop/shortest-path or online ETX/RPL-style baseline would make the
   comparison more convincing.
4. The selected-pair quality gate is useful for a controlled non-degenerate
   case, but it conditions the headline result on a PRR-qualified graph and
   provides only a two-hop topology. A 20-seed unconditioned random-pair
   matrix and a deeper 3--5-hop or larger-network case would address
   generalization and selection bias.
5. Static shadowing makes discovery-time confidence closely aligned with the
   forwarding channel. A temporal fading/stale-route case is more important
   for this mechanism than a generic extra plot; hardware/HIL would strengthen
   external validity but is not an ICC hard requirement.
6. The SF8 robustness case was post-hoc calibrated from 8.25 km/9 km to
   10 km after quality-gate failures. This is acceptable as a calibration
   diagnostic only if the selection process is disclosed and the case is not
   presented as an untouched robustness test.
7. A code-level fairness audit finds that the matched source-route baseline
   still suppresses duplicate RREQs at the destination before adding
   candidates, whereas MeshEcho/ETX/ETT collect candidates during the
   two-second window. Thus the `+0.183` MeshEcho--source-route difference can
   mix confidence selection with a larger candidate pool. The baseline should
   be changed to collect the same candidate set (then choose first/shortest),
   or the comparison must be explicitly downgraded to a first-arrival
   behavior baseline and rerun.
8. In the primary configuration, route-miss fallback adds transmissions but
   has zero ACK-PDR effect; the paper should either show a workload where the
   recovery mechanism matters or remove it from the central contribution.

The current local `2.1.18` worktree is staged but not published:
`origin/version/v2` still reports `2.1.17`. Before any EDAS submission, push a
tagged 2.1.18 artifact and replace `Anonymous Authors` with the exact EDAS
author list/title.

## 2.1.22 Author Metadata Update

- The ICC manuscript now lists `Gao Zu` and `Quan Zhi` in that order, in
  English only, both affiliated with Shenzhen University, Shenzhen, China.
- The paper remains simulation-only; adding author metadata does not change the
  2.1.22 simulation evidence or require a release-version bump.
- The exact same title and author order still need to be entered in EDAS before
  submission.

## 2.1.22 Presentation Refinement

- Added one compact two-panel bar figure to the ICC manuscript: ACK-confirmed
  PDR and total airtime for the primary calibrated matrix.
- Bars use the existing Table II means and whiskers use the existing
  seed-level two-sided 95% CI half-widths; no new experiment or estimate was
  introduced.
- ETX and fixed-SF ETT are shown as one bar because they coincide under the
  shared packet-time model. The figure improves scanability without turning
  the paper into a collection of disconnected plots.
- Tectonic compilation remains at five letter-size pages with no figure
  clipping or label overlap in the inspected page.

## 2.1.22 ICC Formatting Cleanup

- Tightened the ICC LaTeX source toward the official IEEE conference template:
  explicit `conference,letterpaper,10pt` document class; no manual page-margin,
  column-width, global float-spacing, or global table-row compression.
- Removed the unnecessary `IEEEoverridecommandlockouts` directive and the
  forced `\clearpage` before references, allowing the bibliography to flow
  naturally in the IEEE two-column layout.
- Reduced keywords to five IEEE-style terms and adjusted Table I locally to
  remove the remaining overfull table warning without changing margins.
- Final Tectonic build remains five letter-size pages. Visual page inspection
  found no clipped text, page numbers, table overflow, or figure overlap.

## 2.1.21 Continuation State

- The active clean worktree is `/tmp/lora_mesh_remote_current.iIrtPz` on
  branch `version/v2`, with local and remote currently at `6d2134b`
  (published 2.1.17 state); the local worktree contains unpublished 2.1.21
  changes.
- `VERSION` is `2.1.21`.
- The 2.1.21 primary/sensitivity raw CSVs exist for the legacy matrix, but
  calibrated multihop and connected-quality outputs do not yet have complete
  summary artifacts.
- `minhop-mesh` is registered as a distinct shortest-candidate baseline and
  is present in the 2.1.21 probe reports.
- Temporal block fading is deterministic by seed, unordered link, and time
  block; protocol runs share the same fading realization for a given seed.
- The 2.1.21 generalization runner defines unconditioned random pairs,
  100-node 3--5-hop deep multihop, and long/short route-TTL temporal-fading
  cases; these are not yet formally completed.
- The first deep-multihop run exposed a valid per-seed failure at 20 km:
  seed 12 had only 20 eligible 3--5-hop pairs. A 21 km calibration scan
  produced complete 24-pair pools for all 20 seeds while retaining a
  strongly non-degenerate direct-link regime, so the corrected run is being
  versioned as 2.1.22.

## 2.1.22 Evidence Findings

- Primary calibrated matrix remains: MeshEcho 0.720 ACK PDR / 0.739
  destination PDR / 28.1 s airtime; matched source-route 0.502 / 0.636 /
  38.5 s; ETX/ETT 0.661 / 0.741 / 27.6 s; min-hop 0.419 / 0.435 / 26.9 s.
- Paired MeshEcho deltas: +0.218 ACK PDR over matched source-route
  `[+0.041,+0.395]`; +0.059 over ETX/ETT `[-0.108,+0.226]`; +0.301 over
  min-hop `[+0.161,+0.441]`.
- Component attribution: removing confidence changes ACK PDR by +0.148
  `[+0.052,+0.244]`; fallback and age are zero-effect in the sparse primary
  workload; hop penalty is +0.050 with a CI crossing zero.
- Generalization: unconditioned random pairs give MeshEcho 0.404 ACK PDR /
  99.5 s and ETX 0.308 / 98.1 s; 100-node 3--5-hop gives MeshEcho
  0.696 / 160.4 s and ETX 0.531 / 156.6 s.
- Temporal fading: long TTL gives MeshEcho 0.526 / 21.2 s, short TTL gives
  0.324 / 71.3 s. This supports a stale-route boundary diagnostic, not a
  claim that age scoring universally solves fading.
- The rewritten ICC paper now makes a bounded simulation claim, stays
  MeshEcho-only, keeps `Anonymous Authors`, and compiles to 5 pages.

## 2.1.23 Revision Starting Evidence

- The 2.1.22 primary CSV has 20 seeds but only 102 actual unicast flows in
  total (1--11 per seed); its 24 selected pairs per seed form a pool, not
  24 observed transmissions. All selected primary pairs are two hops and
  route-cache hits are zero.
- A shared two-second discovery window does not guarantee the same candidate
  path set: MeshEcho adjusts RREQ forwarding delay using SNR and relay role,
  while source-route and ETX/ETT use another delay rule.
- In the primary matrix MeshEcho minus ETX ACK PDR is +0.059 with paired 95%
  CI [-0.108,+0.226], while airtime increases by +0.5 s [+0.2,+0.9].
- In unconditioned random pairs, managed flooding reaches 0.696 ACK PDR at
  38.8 s versus MeshEcho 0.404 at 99.5 s. The previous generalization table
  omitted this comparison.
- With the default threshold of zero, low-confidence-path fallback cannot
  trigger; failed-discovery route-miss fallback may still occur. The primary
  no-fallback and no-age-penalty ACK ablations both show zero effect.
- The new paper must distinguish fixed-candidate ranking, discovery timing,
  route-miss recovery, and system-level outcomes; claims depend on new runs.

## 2026-09-25 ICC Author Audit

- Current `paper/icc2027/icc2027_lora_mesh.tex` has `Gao Zu` and `Quan Zhi`
  on the author line and an English Shenzhen University affiliation. The
  source, bibliography, and figure contain no Han characters.
- All three current ICC PDF copies extract English-only author names and no
  Han characters, use no CJK font, and are byte-identical. The rendered first
  page visibly shows only the English names. The prior `/tmp` PDF path no
  longer exists, so a stale preview or old path can explain the complaint.
- Do not change the legal author order without confirmation because EDAS and
  the PDF must match exactly.
- The user confirmed `Zu Gao` and `Zhi Quan` as the intended English author
  order; the previous `Gao Zu` / `Quan Zhi` form is no longer the target.

## 2.1.23 Controlled Pilot

- The new fixed-once schedule observed all 24 selected unicast pairs per
  seed for each protocol; its rate is 2.4 flows/min over a 600-s run.
- A three-seed pilot (`/tmp/meshecho_v2_1_23_pilot.csv`) gives MeshEcho
  47/72 ACKs, ETX 42/72, shortest source route 40/72, and flooding 32/72.
  MeshEcho versus ETX seed-paired ACK-PDR delta is +0.069 with 95% CI
  [-0.191,+0.330]; this pilot is too small for a superiority claim.
- Pilot MeshEcho airtime is 93.7 s versus ETX 91.6 s and flooding 26.9 s.
  Flooding reaches 71/72 destinations despite only 32/72 source ACKs,
  emphasizing the reverse-path metric distinction.
- Under matched RREQ relay timing, live candidate sets still diverge:
  the one-seed smoke found only 8/24 identical sets for MeshEcho versus ETX.
  The pilot totals also differ (301 vs 298 candidate paths). Later protocol
  transmissions change collision histories; shared timing is not strict
  fixed-candidate exposure.
- The MeshEcho-specific hop-penalty correction deducts 0.025 once per
  additional hop, instead of repeatedly deducting the entire path-length
  penalty. Legacy CALM retains its old behavior for historical reproduction.
- A predeclared optional admission variant allows at most one extra hop and
  requires at least +0.10 observed confidence over the shortest candidate.
  On development seeds 1--3 it gives 40/72 ACKs and 91.8 s mean airtime,
  versus corrected MeshEcho 47/72 and 93.7 s. It is a reliability--airtime
  tradeoff, not a demonstrated improvement.
- The fixed-once CSV now includes the exact candidate and selected paths in
  `discovery_records_json`, not only fingerprints, so set comparisons are
  independently auditable.
- An isolated per-pair smoke using a fresh simulator for each policy and pair
  observed equal candidate sets for all 24 seed-1 pairs. This removes the
  sequential collision-history confound for a narrower ranking test, but
  one seed is descriptive only. The 20-seed holdout is running.

## 2.1.23 Holdout Results (Seeds 21--40)

- Matched-timing fixed-once main matrix: every policy scheduled and observed
  24 distinct unicasts per seed (480 total). MeshEcho ACK is 332/480 (0.692),
  ETX/ETT 266/480 (0.554), matched source route 204/480 (0.425), flooding
  213/480 (0.444), and budgeted MeshEcho 275/480 (0.573). MeshEcho minus ETX
  paired ACK delta is +0.137 [0.090,0.185], with +1.9 s [1.6,2.3] mean
  airtime per 600-s run. Flooding reaches 476/480 destinations, illustrating
  the ACK/destination metric boundary.
- Live sequential candidate sets remain nonidentical under matched relay
  delays: MeshEcho versus ETX matches on 148/480 discoveries, versus
  no-fallback MeshEcho on 469/480. Thus the main matrix is a system-level
  strategy comparison, not a pure ranking experiment.
- Isolated first-discovery holdout reruns each pair/policy in a fresh simulator
  with route-miss fallback disabled. All 480/480 candidate sets match across
  MeshEcho, ETX, min-hop, and source route; 447/480 expose at least two
  choices. MeshEcho ACK 0.688 vs ETX 0.525 gives seed-paired +0.163
  [0.121,0.204], at +0.094 s [0.078,0.110] airtime per pair. When MeshEcho
  and ETX choose the same path (169/480), ACK, destination, and airtime all
  agree; 311/480 selections differ. This supports a ranking-mechanism effect
  within the isolated simulation, not hardware or topology-independent gain.
- Native-timing random-pair case on seeds 21--40: MeshEcho ACK 0.430 versus
  ETX 0.293, paired +0.137 [0.097,0.178] at +0.2 s [-0.9,1.2]. Managed
  flooding dominates this particular random-pair case: ACK 0.736, 39.7 s,
  versus MeshEcho 0.430, 103.2 s. This negative result must be in the paper.

## 2.1.23 Independent Evidence and Metadata Audit

- Independent CSV recomputation confirms 20 holdout topology seeds. The
  fixed-once matrix has 220 rows across 11 policies, 480 actual unicasts per
  policy, and MeshEcho minus ETX seed-paired ACK delta +0.1375
  [0.0901,0.1849] with +1.931 [1.558,2.305] s airtime per run.
- Native-timing fixed-once runs show MeshEcho 361/480 ACKs versus ETX
  259/480, but candidate sets are not equal; do not replace controlled
  ranking evidence with this more favorable sequential result.
- Deep-case eligibility is 3--5 graph hops, but selected-pair mean graph
  distance is exactly 3.0 for every holdout seed. MeshEcho mean ACK 0.724
  versus ETX 0.551, seed-paired +0.172 [+0.124,+0.220] at +3.3
  [+2.3,+4.3] s airtime. Do not claim observed 4--5-hop performance.
- In fading, MeshEcho ACK is 0.581 at TTL 600 s and 0.341 at TTL 30 s;
  managed flooding is 0.561 and 0.561, respectively. The short-TTL case
  is an adverse boundary, not a general aging benefit.
- The raw report template previously claimed every case had managed
  flooding/ETT and every connected-pool case had no pair reuse; these are
  false for the native fixed-once and deep Poisson outputs. The report owner
  is correcting conditional wording and exact reproduction commands.
- `VERSION` and current runner default output prefixes now target 2.1.23.
  Historical 2.1.22 result files and sensitivity references remain labeled
  as historical, not silently rebranded.

## 2.1.23 Final Artifact Audit

- The final manuscript compiles to exactly five 612-by-792-point Letter
  pages, with IEEEtran conference/10-point options, all fonts embedded, no
  overfull boxes and no undefined citations/references. Two underfull box
  warnings have no visible clipping or overlap in the rendered five pages.
- Printed authors are `Zu Gao` and `Zhi Quan`, followed by `Shenzhen
  University, Shenzhen, China`. Full PDF extraction finds no Han glyph and
  neither old English name order. Root and checked build PDF SHA-256 are
  `8743be24223c2837f72947006df28f83cad121a056a8aeb0bce702f51162c670`.
- The updated two-panel bar chart uses 2.1.23 fixed-once seed means and
  seed-level 95% confidence whiskers. Visual inspection found no text,
  figure, table, or reference overlap on any page.
- Current methodology boundary remains explicit: sequential candidate sets
  differ for 332/480 MeshEcho--ETX discoveries, while the isolated
  first-discovery matrix matches all 480/480. Flooding outperforms MeshEcho
  in the random-pair case; the paper does not claim general superiority or
  physical verification.

## 2.1.23 Publication Formatting Finding

- The isolated first-discovery runner uses `csv.DictWriter` with its default
  CRLF line terminator. Its 1921-line versioned CSV is parseable, but Git's
  staged whitespace check treats every added CRLF line as trailing whitespace.
- This is an output-format issue, not a simulation-data discrepancy. Normalize
  only that CSV to LF and retain its parsed rows and report statistics.
- Before and after normalization, parsed rows had the same SHA-256
  `c1bb2e874eb0dbe740a26b5e978afc600227d9a94a2d15412e765709a414a2d9`;
  1920 data rows, MeshEcho/ETX ACK counts 330/252, and regenerated report
  equality were unchanged. The normalized CSV SHA-256 is
  `9a8715e1fbc7eda9fb2dd41ee0e0fc5588c1192dd7418f932f34825fa26700f5`.
- The old GitHub draft PR body still describes 2.1.22 and names the authors
  in Chinese; repository source and PDF have already moved to English-only
  `Zu Gao` / `Zhi Quan`. PR metadata must be synchronized on publication.
- PR 1 was synchronized after SSH publication: it remains OPEN/DRAFT on
  `version/v2`, is titled for 2.1.23, and its body contains the new English
  author order with neither the old English order nor Chinese names.

## Active Goal Audit - Initial Evidence

- Current authoritative checkout is `version/v2` at `0dc54c0`, version
  `2.1.23`; the only untracked path is an excluded LaTeX build directory.
- The current five-page ICC manuscript explicitly separates the 480-flow
  sequential system comparison from 480 isolated equal-candidate tests and
  reports adverse flooding and short-TTL outcomes. Raw-data recomputation
  and implementation-to-text checks are still in progress.
- Source diff from the prior release confirms MeshEcho now charges a 0.025
  confidence penalty once for each added hop, with a regression test; matched
  RREQ timing and candidate-path records are controlled-evaluation support,
  not a demonstrated algorithmic performance gain by themselves.
- The primary report's no-hop-penalty ACK delta is +0.010 with 95% CI
  [-0.037,+0.058]. Do not describe the corrected penalty as empirically
  improving ACK completion on this evidence alone.
- Independent parsing of the versioned CSVs reproduces primary MeshEcho
  332/480 ACKs, ETX delta +0.1375 [0.0901,0.1849], isolated equal candidate
  sets 480/480 and ACK delta +0.1625 [0.1206,0.2044], random-pair flooding
  0.7355/39.66 s versus MeshEcho 0.4302/103.17 s, and short-TTL MeshEcho
  0.3414/71.13 s. These support the rounded paper numbers.
- The paper calls the default policy `route admission`, although it selects
  the highest-scoring candidate and the default fallback threshold is zero.
  `Route selection` or `candidate ranking` is the literal behavior. ETX PRR
  is inferred from a successful RREQ's SINR via the simulator model, not
  directly observed as empirical per-hop PRR.
- A read-only, ephemeral 20-seed isolated experiment with a PRR-product
  comparator produced 322/480 ACKs versus MeshEcho 330/480; the paired
  MeshEcho difference was +0.0167 [-0.0199,+0.0532]. This cannot enter the
  paper until the comparator, test, raw CSV, and report are versioned and
  independently audited. It materially weakens an ETX-only novelty claim.
- Current PDF embeds Latin Modern text after Tectonic's missing Times-shape
  warnings. Standard pdfLaTeX and `times.sty` are available locally, so a
  more template-faithful build can be tested. Funding/conflict assertions
  need confirmation from the authors.
- The source has no ACK-timeout invalidation for an unexpired MeshEcho route.
  Under repeated-pair fading, a path can remain cached after an unconfirmed
  DATA send; the default zero fallback threshold means age decay alone cannot
  trigger a duplicate. An optional path-identity-checked ACK guard is a
  principled bounded mechanism to test, not yet a proven improvement.
- Any ACK guard must start after the actual source DATA transmission, not
  when `send_data_on_path` merely queues it, and must not delete a newer
  cache entry or retransmit the same flow implicitly.

## 2.1.24 Resume - ACK Guard Interface

- `Simulator.begin_transmission` computes the actual `start` after respecting
  `node.tx_available_at`; `send_data_on_path` only queues a `tx_request`.
  A source-DATA transmission hook at this boundary can start a guard at
  `start + 15 s` without mistiming busy-node sends.
- `RouteEntry` is an immutable object in `CalmMesh.route_cache[src][dst]`.
  An ACK timeout must compare the current cache entry by identity with the
  entry used for the flow, so a newer route is never evicted by an old timer.
- `FlowRecord` exposes both `delivered_at` and `acked_at`. An unconfirmed
  destination delivery is observable as a false eviction in simulation and
  should be counted rather than silently treated as a failed DATA delivery.
- The existing `stale_fading` generalization case already reuses four
  directed multihop pairs per seed under 6-dB/60-s block fading for 600 s.
  With TTL 600 s it recorded only four discoveries per seed, so the new
  variant can be tested against a meaningful stale-cache baseline without
  replacing the topology or traffic generator.
- `pdflatex`, `bibtex`, `IEEEtran.cls`, and `times.sty` are available in
  TinyTeX. The final build should use that toolchain to avoid Tectonic's
  unsupported `TU/ptm` fallback found in the previous log.
- A PRR-product comparator now uses the same RREQ SINR-to-PRR model as ETX
  and has no retry/fallback. A 24-pair seed-1 smoke retained identical
  candidate sets across all five isolated policies. This smoke is not a
  manuscript result; only versioned full matrices may be cited.
- A test-first optional ACK-eviction implementation starts its 15-s guard at
  actual source DATA transmission. It evicts only the same `RouteEntry` if
  ACK is still absent, never retransmits that flow, and records both total
  invalidations and the simulated false-invalidation diagnostic when DATA
  reached the destination but ACK did not return. The same rule is available
  for both MeshEcho and PRR-product, enabling a 2-by-2 comparison.
- Read-only schedule preflight of seeds 41--70 found all four selected pairs
  recur at least twice across at least two 60-s fading blocks; the existing
  Poisson repeated-pair trace can be retained with a stronger runner gate.

## 2.1.24 Development Matrix (Seeds 41--50 Only)

- Three versioned development strata now exist under
  `meshecho_v2_1_24_icc2027_feedback_dev41_50`: 600-s TTL/6-dB fading,
  600-s TTL/static, and 30-s TTL/6-dB fading. Each seed schedules/observes
  the same 4-pair application trace across protocols; all selected pairs
  recur in multiple scheduled time blocks. The gate checks scheduled
  application times, not actual source DATA transmission times.
- In fading, MeshEcho ACK PDR is 0.535 versus PRR-product 0.686; the paired
  PRR-product minus MeshEcho delta is +0.1510, 95% CI [+0.0471,+0.2549].
  MeshEcho+ACK-evict falls to 0.426 and adds 18.52 s airtime per seed
  relative to MeshEcho (paired ACK delta -0.1092
  [-0.2139,-0.0045]). PRR-product+ACK-evict falls to 0.607 and adds
  12.57 s airtime; its paired ACK delta is -0.0787 [-0.1806,+0.0233].
- In static control, MeshEcho ACK PDR is 0.662, PRR-product 0.688,
  MeshEcho+ACK-evict 0.573, and PRR-product+ACK-evict 0.571. ACK-evict
  worsens both protocols without temporal fading; this is not merely a
  stale-cache recovery opportunity. The 30-s TTL fading control is adverse:
  MeshEcho 0.251 ACK PDR/59.3 s airtime, PRR-product 0.272/61.1 s.
- Development outcomes reject promoting 15-s single-failure ACK eviction.
  It remains a negative optional ablation. Because PRR-product has no
  route-miss fallback while MeshEcho does, dynamic cross-policy differences
  are complete-protocol comparisons, not pure ranking effects. The new
  isolated first-discovery matrix will handle same-candidate ranking.
- Independent review found the ACK guard timing, route-identity protection,
  ACK cancellation, and no-oracle decision path sound. A custom guard
  forwarding asymmetry was fixed test-first. Reports were regenerated from
  unchanged raw CSVs to label scheduled application blocks precisely and
  avoid calling destination-delivered/ACK-unconfirmed invalidations proven
  false positives.

## 2.1.24 ACK Guard Race Finding

- A two-flow regression test reproduces an old-guard race: flow 1 loses its
  ACK, flow 2 later receives an ACK on the same `RouteEntry`, yet flow 1's
  timer still evicts that route at 15 s. The failure is a missing cross-flow
  acknowledgment check in `AckRouteEviction`, not an RF-model effect.
- A confirming ACK should cancel only pending guards for the same entry whose
  source DATA transmission started no later than the confirmed DATA; an older
  delayed ACK must not cancel a newer flow's guard. Route identity and actual
  source-transmission time must remain the comparison boundary.
- The fix records actual source DATA start on the pending guard and cancels
  older same-entry guards when a later DATA flow is ACKed. Both the original
  race and delayed-older-ACK reverse case pass. Because the old development
  ACK-eviction simulations predate this change, their affected rows require
  reruns before any publication claim.

## 2.1.24 Scoring Hypothesis Before New Runs

- In 41 common fading discovery events, only 22 candidate sets match between
  MeshEcho and PRR-product. Among 21 both-selected equal-candidate events,
  MeshEcho selected a direct path 12 times versus PRR-product once. This
  implicates ranking but is not a per-flow causal explanation of the ACK gap.
- The single frozen candidate uses `sim.prr_from_snr(rx.sinr_db)` from a
  successfully received RREQ and the minimum modeled hop PRR across the path,
  with zero additional hop penalty. It keeps one scalar score and adds no
  packet. This may over-select long paths; success must be tested against
  both delivery and airtime/energy, not asserted from route choices alone.
- The current ICC manuscript is still ETX-centered. It must explicitly
  include the stronger PRR-product comparison and mark 41--50 as development
  data; 51--70 remains untouched until policy freeze.

## 2.1.24 Calibrated Development Evidence (Partial)

- In 41--50 fading repeated-pair runs, calibrated max-min PRR has mean ACK
  PDR 0.689 versus old MeshEcho 0.535 and PRR-product 0.686. The paired
  calibrated-minus-old ACK difference is +0.154 with 95% CI [+0.052,+0.256],
  at +4.1 s airtime per seed (95% CI [+2.1,+6.1]). The candidate is close
  to PRR-product; no stronger-baseline superiority follows from the means.
- In 41--50 static control, candidate ACK is 0.694 versus old 0.662 and
  PRR-product 0.688. Candidate-minus-old is +0.032 with interval
  [-0.052,+0.115], at +1.7 s airtime. This is not a clear static gain.
- In 41--50 isolated first discovery, all 240 candidate sets match across
  six policies, and 225 have multiple candidates. Candidate ACK is 0.696
  versus old 0.683 and PRR-product 0.692; old-minus-candidate paired
  interval is -0.013 [-0.050,+0.025]. Same-path outcomes never differ,
  supporting a route-choice mechanism but not a reliable isolated ACK gain.
- ACK eviction remains adverse after the old-guard race fix: fading ACK is
  0.437 versus old MeshEcho 0.535, with airtime 40.4 versus 21.4 s. Static
  ACK is 0.573 versus 0.662. These remain development findings only.
- Independent raw-CSV audit found that 41--50 fading used 8 TTL-2 fallback
  transmissions each for old and calibrated MeshEcho, but zero for standard
  PRR-product. Static calibrated MeshEcho used 27 while standard PRR-product
  used zero. A matched-fallback PRR-product control is necessary before any
  dynamic comparison can be interpreted as scoring evidence; even then,
  candidate-set exposure is not guaranteed identical.
- The short-TTL development control is adverse for all route policies:
  calibrated ACK is 0.272 versus old 0.251 and PRR-product 0.272, with
  calibrated airtime 62.6 s versus old 59.3 s. Its paired old-versus-
  calibrated ACK interval crosses zero; do not claim a robust TTL benefit.

## 2.1.24 Frozen Interpretation Boundary

- The matched TTL-2 fallback PRR-product control yields fading ACK 0.689,
  calibrated MeshEcho 0.689, old MeshEcho 0.535; static ACK 0.694, 0.694,
  and 0.662 respectively on 41--50. It uses the same score as standard
  PRR-product and a matched route-miss recovery budget, but dynamic candidate
  histories still need not match; the isolated test is the stronger scoring
  check.
- The new candidate is a model-calibrated max-min route score, a familiar
  bottleneck metric. The paper must not present it as a novel proof of
  superiority over PRR-product. The defensible contribution is an honest,
  reproducible protocol comparison, calibrated score correction relative
  to the old heuristic, and explicit limits under fading and short TTL.
- The 51--70 holdout has not been read or run as of this freeze. Its outcome
  will determine whether the development improvement generalizes; it will
  not trigger score/threshold tuning on the same seeds.

## 2.1.24 Holdout Execution Note

- The first frozen 51--70 case, `feedback_fading`, has completed with process
  exit code 0 and produced its raw CSV, summary CSV, and Markdown report.
  Numerical results are not accepted until an independent raw-CSV audit.
- Current ICC TeX and the existing five-page PDF already print `Zu Gao` and
  `Zhi Quan` in the user-confirmed order; historical mentions of `Gao Zu`
  and `Quan Zhi` in development notes are not current author metadata.
- Independent fading audit checked 120 unique seed-policy rows (51--70,
  six protocols), identical per-seed application traces and 793 observed
  unicasts per policy. Calibrated minus old MeshEcho seed-mean ACK PDR is
  +0.11539465 [0.03067250,0.20011680], destination PDR +0.09827080
  [0.01550016,0.18104144], airtime +2.4674048 s [1.2321439,3.7026657],
  and energy +5.0890247 J [2.5455696,7.6324798].
- Versus matched-fallback PRR-product on that same fading holdout,
  calibrated ACK PDR is +0.00257160 [-0.00553051,0.01067371], destination
  PDR +0.00026510 [-0.00674963,0.00727983], airtime -0.1330816 s
  [-0.3564747,0.0903115], and energy -0.2733710 J
  [-0.7319269,0.1851849]. Candidate sets match 81/83 discoveries and
  chosen paths match 78/80 both-selected events; no strong-baseline win.
- Static and isolated control files completed, but their numerical
  interpretation awaits independent raw-CSV verification. Short-TTL remains
  live. The paper's current no-funding/no-conflict assertion lacks author
  confirmation and must not be carried into the revised submission PDF.
- Independent static audit verified matching 20 seed-level application
  traces, 793 scheduled/observed unicasts per policy, and count-derived PDRs.
  Calibrated minus old ACK is +0.00036760 [-0.07410402,+0.07483922],
  destination -0.00967265 [-0.08582691,+0.06648161], airtime +1.2157184 s
  [+0.0891793,+2.3422575], energy +2.5034038 J
  [+0.1875352,+4.8192724]. Against matched-fallback PRR-product, ACK is
  -0.01025640 [-0.03172305,+0.01121025].
- The independent isolated-first-discovery audit verified 2880 rows: 20 seeds
  x 24 pairs x six policies. All 480 pairs expose identical candidate sets;
  458 have multiple candidates. Calibrated minus old ACK is +0.02083
  [-0.01294,+0.05461], destination +0.01042 [-0.02114,+0.04197], airtime
  per pair +0.03387 s [+0.02158,+0.04616]. Calibrated minus PRR-product
  ACK is +0.00208 [-0.00560,+0.00977]. When two policies select the same
  path, their simulated ACK, destination, and airtime outcomes match.
- The Python figure backend is selected because the user previously asked
  the assistant to choose; system and bundled Python runtimes both lack
  `matplotlib`. A non-blocking question asks whether installation into an
  isolated environment is acceptable. Figure rendering is paused pending
  that answer; no backend substitution is allowed by the figure workflow.
- The first 2.1.24 pdfLaTeX build failed because IEEEtran mapped the sole
  `\texttt` phrase to missing Courier `pcrr7t.tfm`. Removing that optional
  monospace phrase resolved the failure; no class/font override was needed.
  A full BibTeX build now yields five Letter pages with embedded Type 1
  Nimbus Roman and Computer Modern fonts, no unresolved citations or
  references, and the confirmed English author order on page 1.
- Visual QA of all five rendered pages found no clipped text or overlapping
  table cells, but page 5 holds only references [7]--[15] in the left column,
  leaving most of the page blank. This is a presentation defect to resolve
  before final artifact replacement. The current PDF still lacks a 2.1.24
  figure because the chosen Python plotting backend is unavailable.

## 2.1.24 Final PDF and Secondary Metrics

- The rebuilt pdfLaTeX manuscript already prints `Zu Gao` then `Zhi Quan`;
  the top-level repository PDF remains the older 2.1.23 artifact until copied.
- `\IEEEtriggeratref{11}` balances the fifth-page references into two columns,
  but that page is still sparse. All five pages are legible with no overlap;
  the paper remains five-page Letter, 10-pt IEEEtran with embedded Type 1 fonts.
- A read-only audit independently reproduced the main 51--70 raw-CSV means,
  paired intervals, candidate-set counts, and isolated path agreements.
- The existing holdout report and summary CSV provide seed-mean ACK delay,
  P95 ACK delay, collision rate, route discoveries, cache hits, and ACK-guard
  invalidations. ACK delays condition on ACKed flows, collision rate divides
  receiver collision failures by reception attempts, and the legacy repair
  count mixes expiry with failed discovery; these definitions matter in any
  compact secondary-metrics table.
- The final descriptive diagnostics table is sourced from all 120 fading
  rows (six policies x seeds 51--70). The two discovery numbers are separate
  per-seed means, not a pooled success fraction. The last-page references
  are balanced at [10]; no overfull boxes or unresolved references remain.
- Root and build PDFs have identical SHA-256
  `42df9f02cf7c6306c32566fb18017a31d6906da89d984f7fc72c45084d6b6f72`.
- The 2.1.24 release commit `76b40429ed1b6511246c885001317c63fa9d3729`
  is on GitHub `version/v2` and is the head of OPEN/DRAFT PR 1. The remote
  PDF Git blob equals local blob `453b48f9247a79ea35864f1aaeb102059426624a`.

## ICC 2027 Planning Intake - 2026-09-26

- The authoritative local branch is `version/v2` at `bc6b502`; only two
  untracked LaTeX build directories appear in `git status`.
- The five-page 2.1.24 manuscript is format-eligible for ICC 2027, but its
  calibrated-minus-matched-fallback PRR-product ACK interval includes zero.
  The planning target is stronger independent evidence or a narrower claim,
  not retuning the frozen 51--70 holdout.
- The official ICC 2027 symposium deadline is 2 October 2026. The IoT &
  Sensor Networks CFP explicitly includes LPWAN/LoRa and IoT protocol/design
  evaluation. Confirm the exact EDAS closing time before scheduling runs.
- Official ICC 2024 and 2025 presenter pages each state that fewer than 40%
  of Technical Symposia submissions were accepted for presentation; neither
  provides an exact fraction or predicts this paper's result.
- `tools/run_fair_multihop_probe.py` already accepts `meshecho-calibrated`,
  `prr-product-fallback`, original MeshEcho, and flooding/ETX comparators.
  It can specify unconditioned random pairs, matched RREQ timing, fading,
  zero timeout retries, and fresh seed/output paths via the CLI. Its random
  mode intentionally has no graph-conditioned quality gate.
- `tools/run_icc_generalization_experiment.py` exposes a preexisting
  `random_pairs` case, but that case is 18 km, mixed traffic, static channel,
  and unmatched RREQ timing, unlike the 2.1.24 fading primary workload.
  Compare it as a separate stress stratum, not as a one-variable ablation.
- `tools/run_icc_sensitivity_experiments.py` accepts only `ICC_PROTOCOLS`;
  it does not include `meshecho-calibrated` or PRR-product. Fresh SF/load
  evidence for the 2.1.24 candidate requires another runner/configuration.
- The generic probe's report calculates old MeshEcho minus its comparators,
  not calibrated minus matched-fallback PRR-product. A primary new-score
  contrast needs an independent seed-paired raw-CSV calculation.
- Existing ICC artifacts use seeds 1--70; other recorded studies extend to
  100 or 1401. No use of seeds 2001--2020 or the reserved new output prefix
  was found in the inspected artifacts. No tracked wall-clock benchmark
  exists, so an actual-hour estimate would be invented; report simulation
  cell counts and time an already exposed one-seed pilot at execution.
- ICCT source says "Paper submitted to ICCT 2026", but that statement alone
  does not prove actual submission or publication. The submitting authors
  must verify status and overlap before ICC EDAS upload.
- Independent plan review identified an exposure problem with an 8.25-km
  random-pair P1: the frozen 51--70 link regime has only 0.158 of direct
  links below 0.99 model PRR. The historical 18-km random case has 0.641
  below 0.99; the plan now chooses that non-saturated geometry before new
  seeds. It changes geometry and pair reuse relative to the primary case,
  so it is a separate whole-policy robustness stratum, not a causal
  pair-selection-only or stale-cache test.
- The revised plan uses calibrated minus matched-fallback PRR-product ACK
  PDR as its single primary new contrast. Old-score and flooding contrasts
  are exploratory; zero-crossing, positive, and negative primary intervals
  lead to different manuscript language. Low multihop/multi-candidate
  exposure limits mechanism inference even when whole-policy PDR is valid.
- The current manuscript's "statistically indistinguishable" phrasing can
  imply equivalence without an equivalence margin. The plan requires the
  next manuscript revision to report the exact delta/CI and "no demonstrated
  advantage" instead. No manuscript change was made in this planning turn.

## Plan Completion Re-audit - 2026-09-26

- The reviewed 2.1.24 PDF is five Letter pages in IEEE conference 10-point
  format, and the official ICC 2027 symposium deadline remains 2026-10-02.
  The IoT & Sensor Networks scope fits LoRa mesh; simulation-only work is
  eligible, though hardware would strengthen external validity.
- Official ICC 2024 and 2025 presenter instructions each say fewer than 40%
  of Technical Symposia submissions were accepted for presentation:
  https://icc2024.ieee-icc.org/authors/instructions-presenters and
  https://icc2025.ieee-icc.org/authors/instructions-presenters. This is not
  an exact rate, an ICC 2027 rate, or this paper's acceptance probability.
- The current scientific risk is novelty/generalization: calibrated versus
  old MeshEcho ACK PDR is +0.1154 on the frozen fading holdout, but versus
  matched-fallback PRR-product it is +0.0026 with a 95% CI crossing zero.
  The repeated-pair primary workload is graph-qualified; current main-table
  network-level evidence does not compare flooding or ETX on that same
  stratum. The plan's five-policy unconditioned check addresses this gap,
  but it has not run and cannot by itself isolate cache-aging effects.

## Near-50% Strategy Intake - 2026-09-26

- Current `version/v2` has no tracked changes after the documentation-only
  `fb6d188` publication; `VERSION` remains 2.1.24. The planned 2.1.25
  random-pair result files are absent. Two untracked LaTeX build directories
  are unrelated and must be preserved.
- The current method is max-min *simulator-modeled* hop PRR; the frozen
  calibrated-minus-matched-PRR+fallback ACK difference is only +0.0026
  with a zero-crossing 95% CI. This is the central contribution gap, not a
  figure-count or manuscript-format problem.
- ICC 2027's official symposium deadline is 2026-10-02. A near-50%
  manuscript-specific probability cannot be measured or promised; a plan
  should define falsifiable research/readiness gates and stop rules.

## Near-50% Strategy Review - 2026-09-26

- The new strategy is `docs/icc2027_high_confidence_submission_strategy.md`.
  It defines G0--G4: submission integrity, distinct contribution, fair
  strong-baseline gain, external validity, and auditability/presentation.
  Passing those gates removes known objections but cannot be converted into
  a numeric acceptance probability. The suggested +0.03 ACK-PDR and +10%
  airtime/energy limits are prospective author design targets, not ICC rules.
- Live calibrated versus matched-PRR+fallback paths agree in 78/80
  both-selected discoveries; isolated paths agree in 453/480 pairs. A P1
  score-mechanism claim now requires at least 100 matched-key, identical-
  candidate, both-selected comparisons and 30 differing choices, fixed
  before opening P1 outcomes. Other path differences can reflect changed
  interference and candidate exposure; whole-policy results remain valid.
- The existing P1 18-km scenario was selected after inspecting earlier
  results and changes geometry plus pair reuse. It is a post-holdout
  robustness stratum, not a pristine prospective new-method holdout. The
  probe's direct-link PRR diagnostic omits temporal fading; label it a
  static link-budget quantity. The runner saves per-seed summaries, trace
  hashes, and discovery records, not complete packet-level raw traces.
- The current ACK-eviction control is adverse, and Smart-CALM already has
  adaptive recovery behavior. Any new time-horizon score or budgeted
  route-response mechanism must pass prior-art and same-budget comparator
  checks; simple ACK absence or adding a backup is not new evidence.
- With six days to the Oct 2 deadline, P1 plus honest revision is feasible
  only after a timing pilot; a new mechanism with fair controls, a fresh
  holdout, and external validation cannot responsibly be promised for ICC
  2027. The longer research path is conditional, not a planned code change.
- G2 now explicitly permits one of two primary hypotheses, frozen before
  future outcome inspection: improve ACK PDR with bounded airtime and modeled
  energy, or lower cost while meeting a prespecified ACK noninferiority
  margin. The example +0.03 ACK-PDR and +10% cost boundaries are author design
  targets, not venue criteria and not a probability model.
- Resume verification found the current manuscript and frozen fading report
  still support the central limitation: calibrated ACK PDR 0.624 versus old
  MeshEcho 0.509, while the matched-fallback PRR-product mean is 0.621. The
  seed-paired strong-baseline interval remains zero-crossing. No new P1
  results or candidate method can be inferred from this check.
- Independent G2 review clarified the inferential gates: a +0.03 point
  estimate with CI lower bound above zero supports some positive ACK gain,
  not a statistically established gain of at least +0.03. Reliability-first
  cost limits should use paired relative-cost CI upper bounds; cost-first
  noninferiority needs the ACK CI lower bound above the negative prespecified
  margin and the airtime CI upper bound below the negative saving target.
  Matching discovery keys/candidate sets does not fix differing RREQ SINR;
  score causality needs fixed-input replay or an isolated discovery control.

## ICC 2027 Submission Intake - 2026-10-02

- Official ICC Call for Symposium Papers HTML now states 16 October 2026
  (`https://icc2027.ieee-icc.org/authors/call-symposium-papers`). Its embedded
  time element is not sufficient to establish an EDAS closing time or zone.
- Logged-in `https://edas.info/N35508?c=35508` is an active new-paper form
  for ICC 2027 IoT & Sensor Networks, with title, 20--250-word abstract,
  1--4 topics, a mandatory author/originality/double-submission certification,
  author-entry step, and PDF-upload step. The visible EDAS account is
  `bh4me@chinaham.org`; no identity mapping to Zu Gao or Zhi Quan is proven.
- The user reports that ICCT 2026 was withdrawn or rejected. This removes a
  currently concurrent review only if final status is as stated, but an
  overlap/originality check is still needed. The current ICC PDF is five-page
  IEEEtran Letter with embedded fonts, Zu Gao and Zhi Quan at Shenzhen
  University. It has an internal author-disclosure TODO sentence near the
  end and a sparse table-and-bibliography fifth page; these should be corrected
  before upload.
- Deadline sources conflict: the live official ICC web pages say 16 October,
  while the official June 2026 CFP PDFs still print 2 October. The EDAS new
  submission form is currently active, but its exact closure clock is not
  exposed on the form. Treat today's live EDAS availability as actionable,
  without asserting a confirmed extension time zone.
- The user logged into EDAS and reported ICCT was withdrawn or rejected.
  The logged-in form has a mandatory certification of complete author names,
  no plagiarism, and no concurrent submission; author approvals and both
  EDAS email identities are still pending user response.
- A minimal TeX edit removed the internal final-metadata TODO and replaced
  an unsupported equivalence implication ("statistically indistinguishable")
  with "no demonstrated ACK advantage." Fresh pdfLaTeX/BibTeX compilation
  produced a five-page Letter PDF with no unresolved references or overfull
  boxes. All five rendered pages were inspected: no clipping/overlap; the
  fifth page contains Table V and references with much blank lower space.
- EDAS profile ID 2554722 displays `Mr. Zu Gao`, `Shenzhen University`,
  `Shenzhen, China`, and login email `bh4me@chinaham.org`; the identity of
  the submitting account as first author is now verified. The account's
  ICC IoT "My papers and proposals" page shows no existing entry.
- The unsent registration form now holds the exact manuscript title, a
  plain-text rendition of its abstract, and four relevant topics (IoT
  protocols/architectures, low-power systems, multihop dissemination, and
  modeling/performance). The certification box is unchecked; no paper was
  registered or uploaded yet.
- ICC's live submission guidelines explicitly require every coauthor on the
  initial EDAS registration page, with exact PDF title/author-list match;
  mismatch may withdraw a paper from review. EDAS FAQ 1198 says most
  conferences do not permit adding authors after acceptance, and FAQ 651
  says IEEE may disallow author changes after initial submission. Thus the
  user's proposal to provide Zhi Quan's EDAS details only after acceptance
  cannot support a compliant submission of this two-author PDF.
- The user explicitly does not want a boilerplate no-external-funding
  statement in the PDF. None has been added; do not invent one.

## 2026-10-03 MASS Withdrawal Verification

- The user reports MASS withdrawal. A live refresh of their EDAS MASS paper
  `1571304744` at 11:14 CST still displays `Accepted as poster`, Zu Gao as
  sole author, a submitted manuscript PDF, and reviewer feedback. EDAS does
  not show withdrawal or a final camera-ready PDF. Because MASS final files
  use IEEE CPS rather than EDAS, that absence does not establish whether a
  final file was submitted. Asked the user whether the organizers confirmed
  withdrawal and whether an IEEE CPS final file exists; ICC registration
  remains pending this reconciliation.
- The ICC 2027 IoT EDAS form still contains the exact title and a 164-word
  abstract, with three relevant topics selected and the submitting account
  marked as author. Its policy box remains unchecked, and the Add authors /
  Upload manuscript steps remain disabled because no paper is registered.
  Opened a separate ICC papers tab to check for a duplicate registration;
  the original form was not changed.
- The ICC IoT "My papers and proposals" page on 3 October shows no paper in
  this conference. An independent read-only audit confirmed the current ICC
  PDF is five Letter pages in 10-point IEEEtran, with all fonts embedded,
  exact title and Zu Gao / Zhi Quan order, no MASS/poster wording, no visual
  overlap, and text identical to a fresh compile. ICC's official limit is
  six initial-submission pages; format is not the remaining blocker.
- EDAS accepted the author's explicit declaration and registered ICC 2027
  IoT paper `1571361802` at 12:26 CST. Its detail page shows Zu Gao,
  Shenzhen University, as the first author, the exact PDF title, selected
  three topics, and `Pending (no manuscript)`. EDAS explicitly offers Add
  author and Upload review manuscript actions; do not count this as a full
  submission until Zhi Quan and the PDF are present.

## 2026-10-03 Baseline-Centered Revision Intake

- The current `2.1.24` ICC PDF does not contain a full repeated-pair comparison
  of calibrated MeshEcho with Meshtastic-like and MeshCore-like. Its isolated
  first-discovery control contains MeshCore-like only: calibrated ACK 0.702
  versus MeshCore-like 0.429 over 480 matched candidate sets; it does not
  establish the repeated-pair result.
- A read-only in-memory rerun of both baselines on the frozen 51--70
  `feedback_fading` case reproduced a saved calibrated seed exactly and then
  matched every per-seed application-trace hash and unicast denominator.
  Seed-mean calibrated ACK/destination/airtime/energy are
  0.623965/0.633492/23.702912 s/47.190849 J. Meshtastic-like gives
  0.504999/0.988891/42.402675 s/85.268815 J; MeshCore-like gives
  0.410218/0.447598/19.487462 s/38.557018 J. Paired calibrated-minus-
  Meshtastic ACK is +0.118966 [0.010956,0.226977], destination -0.355399
  [-0.459981,-0.250818], airtime -18.699763 s [-21.814145,-15.585381].
  Paired calibrated-minus-MeshCore ACK is +0.213748 [0.115276,0.312220],
  destination +0.185894 [0.086071,0.285717], airtime +4.215450 s
  [2.647815,5.783084]. These diagnostics are not yet versioned artifacts.
- `README.md` explicitly calls Meshtastic-like and MeshCore-like behavior
  models, not firmware clones. Meshtastic-like has a large destination-to-ACK
  gap under the simulator's reverse-path ACK semantics; MeshCore-like lacks
  MeshEcho's route-miss fallback. Interpret network-level differences as
  policy-bundle comparisons, not isolated route-score effects or real-device
  claims. Keep the PRR-product comparator for the separate novelty question.
- The 2.1.25 repeated-fading four-policy artifact is now saved as
  `results/meshecho_v2_1_25_icc2027_baseline_feedback_fading.csv`, its
  `_summary.csv`, and
  `docs/results/meshecho_v2_1_25_icc2027_baseline_feedback_fading.md`.
  Each protocol has 793 scheduled/observed unicasts, no broadcasts, matched
  2-s RREQ timing for routed policies, and 600-s routed cache TTL. The
  Meshtastic-like row has 784/793 destination deliveries but only 400/793
  source ACKs; omitting either metric would misstate the trade-off.
- Official Meshtastic documentation says version 2.6+ direct messages learn
  next-hop routes after initial managed flooding. The local managed-flooding
  model omits that feature. Official MeshCore FAQ says an initial flooded
  message and its delivery report seed a path, whereas the local model uses
  a separate RREQ/RREP before DATA and simplifies roles/retries. Cite the
  official sources and call both policies stylized `-like` models.
- Independent audit of the formal 2.1.25 fading CSV found exactly 80 unique
  rows (20 seeds x 4 policies), matched per-seed traffic traces/denominators,
  and 793 observed/scheduled unicasts per policy. All 40 calibrated and
  PRR+fallback rows are field-for-field identical to the 2.1.24 originals.
  Paired calibrated-minus-Meshtastic ACK is +0.118966
  [0.010955,0.226978], destination -0.355399 [-0.459982,-0.250816],
  aggregate TX airtime -18.699763 s [-21.814181,-15.585345], and modeled
  energy -38.077966 J [-44.329428,-31.826504]. Versus MeshCore-like:
  ACK +0.213748 [0.115275,0.312221], destination +0.185894
  [0.086069,0.285718], airtime +4.215450 s [2.647797,5.783102], and
  modeled energy +8.633832 J [5.453004,11.814659]. Versus PRR+matched
  fallback, ACK +0.002572 [-0.005531,0.010674].
- `total_airtime_s` is aggregate transmission time, not union channel-busy
  time. Modeled energy assumes all non-transmitting nodes listen during each
  packet; do not imply measured device energy. Baseline additions to the
  previously inspected 51--70 holdout are exploratory, not part of the
  original predeclared comparison set.

## 2026-10-03 Random Sparse-Fading Baseline Audit

- The new `2.1.25` random-pair CSV/report cover 20 seeds (2001--2020), 50
  nodes, an 18-km square, SF7, 600 s, 4 flows/min, and 6-dB fading every
  60 s. All four policies share each seed's traffic hash and denominator;
  each has 813 observed/scheduled unicasts overall.
- Seed-mean ACK PDR/destination PDR/aggregate TX airtime are MeshEcho
  `0.486/0.515/152.8 s`, Meshtastic-like `0.708/0.995/38.9 s`,
  MeshCore-like `0.381/0.408/148.4 s`, and PRR+fallback
  `0.486/0.514/153.0 s`. Meshtastic-like dominates MeshEcho on these
  measured metrics in this stress case.
- Paired MeshEcho-minus-Meshtastic-like ACK difference is `-0.222`
  (95% CI `[-0.273,-0.171]`); destination difference is `-0.481`
  (`[-0.525,-0.436]`); airtime difference is `+113.8 s`
  (`[105.0,122.6]`). Against MeshCore-like, ACK is `+0.105`
  (`[0.077,0.133]`) at `+4.40 s` airtime. Against PRR+fallback,
  ACK is `-0.0002` (`[-0.0259,0.0255]`).
- The random-pair case has no graph-hop/pair-feasibility gate. Its discovery
  keys match across routed policies, but candidate sets can diverge after
  forwarding changes interference. It cannot isolate a route-score effect.
- Root cause of the report reproducibility defect: the probe CLI accepts
  temporal fading flags, but `write_report()` omits them in its ordinary
  reproduction command. Add a regression test and include both flags.

## 2026-10-03 Final 2.1.25 Evidence Boundary

- The PDF uses three simulated protocol ideas plus one score control, not
  four independent product protocols. Meshtastic-like omits current
  direct-message next-hop learning; MeshCore-like uses a separate RREQ/RREP
  instead of initial DATA flooding and delivery-report learning.
- Pooled destination-delivered-but-not-source-ACK counts are 8/384/29/10
  for MeshEcho/Meshtastic-like/MeshCore-like/PRR+fallback on recurring pairs,
  and 22/236/22/21 on random pairs. Route-cache hits collapse from 525
  (MeshEcho recurring) to 5 (MeshEcho random), so workload choice changes
  route-state exposure materially.
- The manuscript explicitly discloses post-hoc baseline additions, random
  scenario design after earlier holdout inspection, nominal paired CIs,
  non-equivalence of product firmware, aggregate TX airtime, and modeled
  always-listening energy. It does not claim a proven score advantage over
  matched PRR-product or universal reliability superiority.
- Official protocol sources were checked at
  `https://meshtastic.org/docs/overview/mesh-algo/` and
  `https://github.com/meshcore-dev/MeshCore/blob/main/docs/faq.md`.
- Verified final ICC artifact is a five-page, English, US Letter, 10-point
  IEEEtran PDF with embedded fonts and no visual overlap. Root PDF SHA-256
  `fe2899dbbeec32e42428e5883e8baccf0058b76a897375eb58be44a12269cbd4`.

## 2026-10-03 Figure Contract and Identity Audit

- A read-only audit found that the paper calls the evaluated row simply
  `MeshEcho`, but raw CSVs and simulator name it `meshecho-calibrated`;
  `README.md` says this is an optional variant distinct from the default
  `meshecho` policy. The manuscript should explicitly map its shorthand to
  this evaluated variant, without making old MeshEcho a main comparator.
- Core conclusion for a figure: delivery ranking changes between conditioned
  recurring conversations and unconstrained random-pair traffic, and
  source-ACK versus destination PDR can rank flooding differently.
- Figure archetype: quantitative grid. Hero evidence: source-ACK PDR; second
  panel: destination PDR. Three plotted models: evaluated calibrated
  MeshEcho, Meshtastic-like, MeshCore-like. PRR+fb remains a table-only
  internal score control.
- Backend: Python only. Output contract: double-column vector PDF and SVG,
  plus PNG preview, sourced directly from the two existing 20-seed CSVs.
  Bars are seed means with nominal 95% t intervals across topology seeds;
  paired-difference intervals stay in the manuscript table.
- Reviewer risks: do not imply these are product firmware or that unpaired
  mean CIs test paired superiority; label both workloads and the `n=20`
  independent-unit definition. No data exclusions or image processing.

## 2026-10-03 Final Figure Evidence

- Six-row chart source CSV uses only calibrated MeshEcho, Meshtastic-like,
  and MeshCore-like; the PRR-product matched-fallback score control stays
  in the manuscript tables. Recurring ACK means are 0.6239653, 0.50499885,
  0.41021755; random ACK means are 0.4858964, 0.7082183, 0.38089485.
  Destination means match the 2.1.25 main table to three decimals.
- The chart PDF/SVG contain selectable text and the final manuscript embeds
  the vector chart. The final five-page PDF passes page-by-page layout review;
  full-run paired-difference CIs remain in the table, while chart whiskers
  are per-policy seed-mean 95% t intervals, bounded to the PDR range.
- A one-seed 2.1.26 recurring-fading simulator smoke on seed 51 produced
  exactly the same four raw policy records as the frozen 2.1.25 CSV.
- PDF SHA-256 is
  `25bf5d25c70816c457640f232c2e657ba546e4d3f4d420c053824af11eb8443a`;
  source/build PDFs match. The first LaTeX attempt failed solely because
  TinyTeX lacked Courier metrics for a new `\texttt` phrase; ordinary
  quoted CLI names resolved it without changing scientific content.
- Independent figure audit recomputed all six source rows and their seed-mean
  t intervals exactly, confirmed the calibrated/default distinction, and
  found no final-PDF visual defect. Its one release blocker was the ignored
  included figure PDF; the narrow `.gitignore` exception now makes it
  stageable and part of the release.
- The committed paper archive, without any working-tree build files,
  compiles to five pages. GitHub serves the figure PDF at the same blob SHA
  as local HEAD, so the new PDF inclusion is reproducible from the release.

## 2026-10-03 Distinct-Variant Research Intake

- Authoritative checkout: `version/v2` at `78ffb6e` in
  `/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2`.
  The nominal `lora_mesh` directory has a missing Git tree; do not use it for
  edits. Existing dirty strategy/checkpoint Markdown and LaTeX builds are
  user state, not cleanup targets.
- The 2.1.26 random workload has 807 discoveries for 813 application flows
  and five MeshEcho cache hits; the recurring workload has 525 cache hits.
  The matched PRR-product route score is nearly identical to calibrated
  MeshEcho. Discovery amortization, not another path score, is the measured
  bottleneck requiring study.
- Official Meshtastic 2.6+ and MeshCore descriptions both include first-
  message flooding followed by learned directed forwarding and a fallback.
  Thus flood-first/cache alone does not distinguish a new policy.
- `RadioConfig.payload_bytes` is fixed at 32 and `begin_transmission()` uses
  the same `radio.toa_s` for every packet, so any route-learning proposal
  must account for packet type and path-header bytes before airtime claims.
- Prior-art search in the preceding turn verified ETX, ETT/WCETT, LoRa *ToA,
  conservative link estimation, and online wireless routing. No global
  novelty claim is justified from these sources alone.
- Re-read the Meshtastic official 2.8 documentation in-browser on this turn:
  since firmware 2.6, direct messages begin with managed flooding, a returned
  response can establish a per-hop next-hop, and a missing next-hop can cause
  a last-retransmission flood fallback. Source:
  https://meshtastic.org/docs/overview/mesh-algo/#direct-messages-using-next-hop-routing
- Re-read MeshCore's official FAQ sections 5.3--5.4 in-browser: first DATA
  floods, a delivery report with repeaters returns by flood, later packets
  embed the learned path, and a broken path can revert to flood after failed
  retries. Source:
  https://github.com/meshcore-dev/MeshCore/blob/main/docs/faq.md
- These are documented mechanisms, not an exhaustive firmware-code audit.
  A proposed controller should be differentiated by a reproducible decision
  rule and state, not by the generic flood/route modes it contains.

## 2026-10-03 Distinct Algorithm Continuation

- User deployment targets are nRF52 and ESP32-S3. A small fixed-memory online
  controller is preferable as the first candidate; TinyML is not required by
  the evidence and would need an independent quality/overhead win.
- The 2.1.26 paper reports, in the unconditioned random-pair case, calibrated
  MeshEcho ACK PDR 0.486 and aggregate TX airtime 152.8 s versus its stylized
  Meshtastic-like 0.708 and 38.9 s. In recurring-pair traffic, calibrated
  MeshEcho ACK PDR is 0.624 versus Meshtastic-like 0.505, but its destination
  PDR is lower (0.633 versus 0.989). These are model comparisons, not real
  product measurements.
- Source-local F/R/D remains a *hypothesis*: F is DATA flood, R is ACK-
  confirmed cached-route DATA, D is proactive RREQ/RREP refresh. It must
  differ by explicit decision rule and pre-failure behavior, not by the
  existence of flood/cache primitives already documented in products.
- A prior-art audit found LoRa *ToA routing, conservative reliability
  estimation, proactive route maintenance, and online wireless route
  optimization. Do not assert global firstness. A simple amortization
  threshold with the same observations is an essential comparator.
- The simulator currently charges the same 32-byte packet airtime for every
  type. Correct packet length and account for DATA, control, ACK, retries,
  and route headers before asserting airtime or energy gains. Current
  Meshtastic-like/MeshCore-like models are not faithful modern firmware
  implementations; upgrade them for a paper-grade comparison.
- Existing ESP32 Smart-CALM firmware has a 6-state/3-action tabular
  Q-learning controller (`firmware/esp32_smart_calm/include/smart_calm_controller.hpp`),
  with 8 tracked active flows and fixed arrays. It is firmware version
  2.1.2, distinct from the current 2.1.26 simulator/paper. A new generic
  Q-learning profile switch would overlap this prior work and is not an
  automatic novelty gain. The inspected source tree contains this ESP32
  prototype but no nRF52 source. The nRF52840 web manifest is marked
  `planned` with `files: []`; no flashable image was found there. The
  PlatformIO target is `esp32dev`, not ESP32-S3.
- Corrected D definition: it is a *shadow refresh* before a confirmed route
  has failed, gated by past-only repeat demand, route age, cooldown, and a
  source discovery-token budget. Keep the old route while probing, send this
  flow's DATA exactly once, and promote the tentative new route only upon
  source ACK. A D action that occurs only after route loss would not support
  a preemptive-refresh claim. Compare against F/R-only and a periodic refresh
  with the same RREQ budget; abandon D if it rarely triggers or fails to
  repay its full control cost.
- A bounded cold-D branch is also in the research brief: after two F
  attempts without source ACK to the same destination and at least two
  earlier sends in 300 s, a third flow may spend one discovery token. Cold
  discovery and pre-failure shadow refresh must be reported separately.
- Target-device analysis found existing ESP32 C++ route/pending/neighbor
  capacities of 8/4/16. The node-wide Q table's `collision_per_tx > 18.0`
  bucket appears unreachable under its current ratio definition, and the
  firmware's `collision_fail` is incremented on local transmit errors, not
  measured RF collisions; do not reuse it as a real congestion feature.
- The source policy must not read `flow_confirmed()` because its default
  implementation checks simulator-only destination delivery; local ACK and
  send timers are the valid feedback. Global aggregate airtime is an external
  evaluation metric, not a source-local decision input.
- Independent algorithm review caught a discovery-location error in the
  first research brief: current calibrated MeshEcho collects/selects RREQ
  candidates at the destination and sends one RREP. The corrected SR proposal
  keeps destination-side route selection and one RREP; only the decision to
  start D is source-local. Source collection of multiple RREPs would be a
  different protocol and must not be smuggled into the comparison.
- Final red-team issues are now explicit in the research artifact: candidate
  DATA in D can lose the *current* flow even if the old route works; retained
  cache protects only later flows. The same-trigger age-gated F baseline may
  dominate D because a DATA flood both delivers and learns. Native product
  acknowledgement semantics differ, so a common application confirmation
  contract is needed for mechanism comparisons, and native behavior is
  reported separately. Route age starts at ACK-confirmed commit; failed D
  does not refresh it. The experiment gate counts scheduled flows from
  application enqueue, including discovery delay and all packet airtime.
- Hardware audit: the available C++ source targets original `esp32dev` with
  RadioLib, 8 route slots, 4 pending flows, and 16 neighbors. No verified
  ESP32-S3 build or nRF52 source/flashable image exists in this checkout;
  the nRF52840 manifest is planned. nRF52 SKU memory varies, so fixed-array
  size, stack, timer rollover, sleep/reboot, RF current and duty cycle must
  be measured on the actual boards. A neural network is not required; a
  per-destination bandit is scientifically weak under the observed sparse
  feedback even though small tables are computationally feasible.
- Research conclusion: the mechanism is distinguishable from the *documented*
  product state machines, but ICC-grade value is conditional on independent
  gains over F/R-only and age-triggered F under corrected packet accounting
  and faithful product models. No acceptance-probability increase can be
  quantified from this unimplemented variant.

## 2026-10-03 SR Implementation Findings

- `Packet.wire_size_bytes()` and packet-specific ToA now charge DATA, control,
  route paths, radio energy, and collision duration separately. This is a
  modeled wire schema, not actual firmware serialization. ETT still uses a
  nominal 32-byte ToA for ranking and must not be described as path-aware.
- SR's source-only action is now explicit in code: F sends useful DATA and
  learns only from source ACK; R sends on the ACK-confirmed path; D obtains a
  destination-selected candidate but does not install it on RREP. A failed D
  uses one DATA on the retained R path or F if cold. Distinguish intended D
  from the actual fallback DATA action or fallback R ACK can falsely refresh
  route age.
- Current focused tests show the four mechanism variants differ at the same
  aging-route trigger, but no population-level gain has been measured. Route
  state deadlines, out-of-order feedback, fixed memory capacity, and product
  baselines remain open validation tasks.
- The old 2.1.26 manuscript reports fixed-size-packet simulation; all old
  TX-airtime/energy/collision numbers are frozen legacy evidence, not results
  from the corrected simulator. Recompute before any ICC SR manuscript claim.

## 2026-10-03 SR Validity Audit and Algorithm Choice

- The experimental runner now has four paired SR variants, 30-s common
  application deadlines, development seeds 3001--3020, untouched holdout
  seeds 4001--4040, flow/action records, and source hashes. A two-seed smoke
  passed, but no complete matrix or independent SR effect estimate exists.
- A one-seed development pilot gave SR ACK PDR 0.7297 / TX airtime 29.66 s,
  versus F/R-only 0.7568 / 21.91 s. This is diagnostic only, not a conclusion.
- Source-only violation: the destination's 2-s RREQ candidate-window closure
  calls SR's failed-discovery fallback immediately, even though the source
  has a 10-s RREP wait. A no-candidate example sends DATA at about 202 s
  instead of at or after 210 s. The missing RREP must be learned only at the
  source deadline.
- ACK timing violation: `begin_transmission()` reserves a queued TX at request
  time and calls `on_transmit` with its future start. SR currently takes the
  minimum of TX-start-plus-guard and application deadline, allowing an ACK
  miss at 31 s for DATA whose actual TX start is 100 s. Route-failure feedback
  must not precede the actual source transmission.
- A previous out-of-order R ACK bug was repaired with the recent-R-flow list;
  the 14 focused SR tests now pass. Other open issues are flow-state growth
  despite eight destination slots, fixed 2-s discovery windows at slow PHYs,
  broadcast traffic incorrectly consuming unicast token/slot budget, and
  external score/input mismatch versus the proposed device algorithm.
- Research direction: fixed-age D is not automatically better than a
  pre-failure, age/demand/token-gated DATA flood. F carries useful payload
  while refreshing a route; D pays RREQ/RREP before its one DATA. Compare
  both with F/R-only and equal-budget periodic controls under common ACK,
  full packet airtime and unchanged application deadlines. Product F/R
  primitives are not new; any novelty would lie in a defensible decision rule
  and demonstrated conditional benefit.

### Development matrix and timing caveat

- The first 20-seed, 80-run recurring-fading development matrix is saved at
  `results/meshecho_sr_research_recurring_fading_dev_20261003.*` with a source
  hash in its manifest. Means: SR ACK PDR 0.609 / 41.53 s TX airtime;
  F/R-only 0.547 / 38.36 s; same-trigger F 0.554 / 39.71 s. SR minus F/R
  ACK gain is +0.0615 [0.0184, 0.1047], relative airtime +0.102
  [0.018, 0.187]. SR minus same-trigger F ACK gain is +0.0549
  [0.0211, 0.0888], relative airtime +0.052 [0.003, 0.102]. Thus both
  predefined +10% airtime upper-bound gates fail even on development seeds.
- SR and periodic-D rows are identical: demand gating is not exposed by
  this repeated-pair workload. Across 20 SR seeds there are 46 D decisions
  (31 pre-failure, 15 cold), 36 candidate events, 24 different candidate
  paths, and 23 ACK-confirmed replacements. These are descriptive action
  counts, not independent replicates or causal per-action effects.
- An independent physical-timing audit found that, at SF7 with the current
  frame sizes, a four-hop RREQ needs about 1.73--3.83 s to arrive (typical
  2.78 s) before queueing, so the source-started 2-s candidate window
  admits only about 0.94% of four-hop attempts under independent uniform
  relay delays. The destination cannot know source time zero because that
  timestamp is not transmitted. Start its collection window on first RREQ
  arrival and use a hop/PHY-valid window and source RREP deadline before
  interpreting or publishing these development effects.
- The full suite after source-only, queued-TX, and common-ACK fixes reports
  185 passed and 1 skipped. The new product-inspired common-ACK classes are
  not firmware-equivalent, and even their flood-delay function is not yet
  identical to SR's; product-family comparisons remain secondary.

### Controller-redesign evidence boundary

- The user now requires replacing SR's core fixed-age/2-send decision rule,
  not just tuning it. Preserve the F/R/D machinery only as implementation
  infrastructure and the original SR policy as an explicit comparator.
- In the prior development trace, D-exposed flows were 31 shadow and 15
  cold; source ACK by deadline was 29/31 and 11/15 for SR. On those same
  flow ids, F/R-only recorded 13/31 and 5/15, and same-trigger F 11/31 and
  5/15. These are **not** causal per-action effects: prior policy histories
  diverge and induce different interference and cache state.
- Of 36 successful candidate returns, 12 were cold and 24 had an old route;
  all 24 old-route returns selected a different path. This is exposure
  evidence only and must be rechecked after the destination-window fix.
- The new controller should demonstrably choose differently from matched
  periodic D in a frozen workload, use only source-local history and
  packet-cost estimates, and bound per-source/per-destination RAM. If it
  cannot clear matched F/R-only and same-trigger F reliability/cost gates,
  the paper must not present it as a superior protocol.
- The current ICC manuscript has 472 LaTeX lines and its old policy/model,
  exploratory tables, six-row bar chart, and discussion occupy almost all
  sections. Packet-cost and discovery-timing changes invalidate old airtime
  and collision/energy numbers. A major rewrite must replace its abstract,
  algorithm specification, experiment table, result figure, and limits from
  newly audited evidence; swapping only title or abstract is insufficient.
- A possible stronger controller may need route-risk information not present
  in the fixed age/2-send rule. The currently available source-local inputs
  are route age/path length, recent application sends, ACK outcomes/timing,
  source radio configuration, and bounded token state. Simulator-global
  delivery, future traffic, true PRR, and whole-network airtime cannot be
  decision inputs. A new on-wire SNR-margin feedback field would require
  explicit packet-byte accounting and fairness controls; it is not yet part
  of the protocol or a demonstrated improvement.

### 2026-10-03 Controller Review

- An independent read-only review proposed a margin-and-airtime-gated F/R/D controller. Each successful DATA ACK would return a quantized minimum forward-hop SNR margin measured at receivers. Missing ACKs are ambiguous forward/reverse failures and must not be treated as observed forward-link deterioration.
- D would be eligible only for a confirmed but low/falling-margin route with projected reuse, enough deadline, token/cooldown allowance, and an explicitly modeled complete-RREQ/RREP/DATA/ACK cost no worse than a defined useful-DATA-flood budget. Otherwise the controller uses R on healthy paths or F to send useful DATA and learn a route.
- This is a design hypothesis, not an implemented or validated gain. Network-wide airtime is an outcome measured by the simulator, not information available to the sender; local ToA cost estimates need calibration and disclosure. The decisive comparator is the same-trigger F action, plus F/R-only and equal-budget periodic D.
- `paper/icc2027/references.bib` is the actual bibliography file; the prior checkpoint's statement that references were inline was incorrect.
- Feasibility audit: `RxInfo.snr_db` exists only at successful receivers. `Packet.path_confidence` cannot be reused for signed SNR margin because zero currently means absent in RREQ logic. MAG needs a separate optional one-byte field preserved across all packet-copy paths and returned by ACK; successful-ACK margins and missing-ACK outcomes must remain distinct signals.
- The simulator's eight destination slots do not bound diagnostic per-flow maps, miss-flow sets, flood de-duplication sets, or destination candidate lists. A source-state design can target fixed arrays on nRF52/ESP32-S3, but no current code or measurements prove a bounded firmware footprint.
- The current bibliography already covers LoRa mesh, product documentation, ETX, and ICC simulation/testbed examples. The prior research brief identifies proactive route maintenance (Dai and Wu, ICC 2005, DOI `10.1109/ICC.2005.1494544`) and reliability-constrained link metrics (Mathews and Gotzhein, WCNC 2021, DOI `10.1109/WCNC49053.2021.9417117`) as close related work; these must be verified and distinguished before a novelty claim.
- Timing correction passed full regression before MAG: destination candidates are collected from first arrival with a max-hop/PHY-aware window; RREP wait starts at actual RREQ transmission and covers the return path. The bound excludes unbounded queue congestion. At SF12/max_hops=6 the derived source wait is about 44.43 s, exceeding the common 30-s application deadline; MAG's deadline gate must therefore choose F in that configuration.
- MAG's current tested source rule reacts to ACK-carried measured minimum forward SNR margin, not simulator-global PRR. A source may overhear an ACK that is not its next hop; only the protocol-accepted ACK updates feedback. A lost reverse ACK reveals no forward margin, so a single R ACK miss does not fabricate low-margin risk.

### 2026-10-03 MAG Development Matrix 1

- Corrected-timing, 20-seed, four-policy development matrix has 80 runs and 798 scheduled unicasts per policy. Mean MAG deadline ACK PDR / whole-network TX airtime is 0.677 / 51.10 s; matched F/R-only 0.542 / 39.35 s; same-trigger F 0.540 / 58.89 s; equal-token periodic D 0.669 / 45.21 s.
- Seed-paired MAG minus F/R-only ACK gain is +0.1349 [0.0859, 0.1839], with +32.1% [23.6%, 40.5%] relative airtime. The precommitted +10% airtime upper bound fails. MAG minus same-trigger F passes development reliability/cost, but MAG minus periodic D has no clear ACK gain and costs more airtime. No holdout has been opened.
- MAG actions: 76 D decisions (69 ACKed in its own policy history), 83 risk-F decisions when D gate rejects, 446 R decisions, and 150 no-route F decisions. Periodic D has 78 D decisions. D-outcome comparisons on selected flow IDs are descriptive only because policy histories diverge; they cannot establish per-action causal gains.
- The current rule's risk-F fallback adds broadcasts even while an ACK-confirmed route remains. Revising that gate to R is a predeclared development-informed cost reduction, not a result to present as independently confirmed. A new development replay must retain the original matrix as provenance.
- Development revision 2 (same seeds, separate manifest) lowers MAG airtime to 43.89 s/run from 51.10 s/run while retaining ACK PDR 0.681; F/R-only remains 39.35 s/run, ACK PDR 0.542. MAG minus F/R airtime is still +13.2% with 95% CI upper +21.6%, failing the +10% criterion. It has 70 D decisions in 798 flows and roughly 241 control TX/run versus F/R's 46.5. Cost is dominated by discovery, not just rejected-risk floods.
- A third, structural development variant caps proactive RREQ to confirmed route hops plus one and applies the same cap to periodic-D. This may miss longer alternatives; candidate exposure, ACK reliability, and actual control TX must all be audited. The agent must not treat a lower RREQ count alone as a success.
- Development revision 3 reduces mean MAG control TX from 241.3 to 223.9 per run and mean whole-network airtime from 43.89 to 40.82 s, while ACK PDR rises from 0.681 to 0.698. The matched F/R-only remains 39.35 s and 0.542 ACK PDR. MAG discovers 74 times across 798 flows, receives 71 candidate returns, and ACK-commits 66 candidate routes; periodic D has 77/71/68 respectively.
- The dev3 paired MAG-vs-F/R airtime result is +5.0% with 95% CI [-2.7%, +12.8%]. The predefined +10% upper bound is still unmet. MAG beats same-trigger F in development, and uses about 7% less airtime than periodic D with no clear ACK difference. These do not prove a distinct reliability benefit from margin gating. No holdout was opened, and no positive-result ICC paper rewrite is justified.

### 2026-10-03 Redesign Decision

- The previous goal turn was a read-only evidence review that changed the next
  action: a stronger ICC algorithm paper needs a different route-acquisition
  mechanism, not another MAG risk, age, or cooldown threshold. The validated
  packet/radio simulator, source-route forwarding, ACK feedback, and matched
  comparisons are reusable research infrastructure, not the new contribution.
- Current MAG still launches RREQ/RREP before candidate DATA. Capping proactive
  RREQ to the confirmed path plus one hop reduces mean airtime but cannot
  establish the prespecified cost gate; its ACK gain over periodic D remains
  uncertain. A useful-payload, bounded discovery/repair design is a hypothesis
  to specify and test, not an established novelty or gain.
- The five-page ICC manuscript still describes the published 2.1.26 calibrated
  route scorer, whose frozen comparison with matched-fallback PRR-product is
  near zero. Neither MAG nor a future mechanism is in that paper yet.
- The 4001--4040 holdout is untouched. Reusing any 3001--3020 development
  outcomes for design is permissible only with transparent provenance; it is
  not independent confirmation. No MAG development number belongs in a new
  positive ICC claim.
- An independent protocol/experiment audit selected a testable LPR hypothesis:
  ACK-indexed weakest *successful* hop plus useful-DATA one-relay segment
  repair, with no preliminary RREQ/RREP. The existing F already carries
  payload, so a mere DATA-probe rename would not be a new mechanism. The
  detailed provisional contract and falsification gates are in
  `docs/research/meshecho_lpr_design.md`.
- Independently recomputed dev3 MAG action shapes with `jq`: 49/71 candidate
  returns and 46/66 ACK-committed D candidates are single-node insertions
  into the old route; 48/71 candidates change a direct old edge to two hops.
  This is exploratory path-shape feasibility only, not predicted LPR success.
- `tools/run_sr_experiment.py` windows TX airtime by actual TX start through
  630 s, but its raw control/data/ACK counts and RX energy can include queued
  starts outside that window. The LPR runner must align new packet counts
  with the airtime window or disclose the mismatch.
- A deterministic simulator diamond test now proves only *feasibility*: an
  ACK-indexed P DATA can cross one old edge through a passively eligible
  off-path relay and return an ACK carrying the realized inserted path. It
  says nothing yet about frequency, contention cost, or benefit in the
  50-node development distribution. Candidate suppression and timeout safety
  are still incomplete and should precede any matrix run.
- The fourth LPR regression now covers a source-origin PATCH ACK timer and
  lost-ACK noncommit; all four focused tests pass. A later full-suite rerun is
  still required.
- Independent LPR review identified four pre-matrix validity gaps: a queued
  relay never cancels on successor/earlier-candidate continuation; pending
  relay and repair-index maps retain completed flows; P omits the existing
  confirmed-route cache-hit metric; and P ACK acceptance does not verify the
  ACK origin is the flow destination. These are protocol/metric defects, not
  evidence of algorithm performance. Fresh development and holdout remain
  unopened for LPR.
- An end-to-end wrong-origin ACK test reproduced the P acceptance defect:
  with flow 3 delivered, an ACK whose claimed origin was node 2 instead of
  destination node 1 still set `acked_at`. Requiring `packet.origin == flow.dst`
  makes the same test pass without changing other ACK paths.
- A three-flow F/R/P test reproduced P cache-hit undercount (one observed
  versus two expected confirmed-route uses); counting P as a hit makes it pass.
- Runner audit: existing `tools/run_sr_experiment.py` is MAG/SR-oriented and
  cannot label LPR evidence confirmatory. TX airtime is windowed by actual TX
  start through 630 s, but raw packet counters are not; LPR needs per-kind
  counts computed from the same start window. The LPR primary gate must be
  joint against F/R-only and same-trigger F under exact frozen case/config,
  full 40-seed holdout, and identical feedback bytes. Periodic P and an
  unobserved-edge P ablation test localization, not the primary cost gate.
- LPR cancellation now observes a successor DATA/ACK or an earlier valid
  candidate transmission and suppresses an uncommitted local relay. It does
  not count an already committed relay as suppressed. Canceled/sent relay
  handles are released, with a bounded 128-flow per-node recent-relay list
  retaining duplicate suppression. A source P repair index persists only
  until its accepted ACK or just beyond its application deadline. This does
  not prove the whole Python simulator has fixed memory: older diagnostic
  per-flow maps still retain history for output, and the recent-flow list is
  a finite duplicate horizon.
- The runner's new `windowed_*` TX-kind counters and `raw_*` aliases share
  the same actual-TX-start window as whole-network airtime. This fixes a
  reporting mismatch but does not itself validate LPR's performance.
- A paired analysis keyed only by `case` text and trace hash can silently mix
  payload/PHY configurations. Run rows now include a SHA-256 of the complete
  `SrCase`; summary rejects mismatches both inside one seed and across seeds.
- Existing output files were previously overwritten by `write_artifacts`.
  Exclusive creation now refuses an existing prefix, preserving prior
  development attempts. The generic reliability/cost gate is non-evaluable
  below 20 independent seeds, so a one-seed smoke cannot be labeled passed.

### 2026-10-03 LPR Integrated Prototype Check

- The new LPR source action and PATCH/PATCH_RELAY forwarding code are present
  in `lora_mesh_sim.py`, as are all four same-feedback comparison modes.
  This is a core-mechanism replacement of pre-DATA RREQ/RREP refresh, not a
  completed proof of algorithmic advantage or deployable firmware.
- Full regression after control integration: 229 passed, one skipped in
  21.23 s; `git diff --check` passes. No LPR population output exists yet.
- The runner still marks only MAG primary comparisons as confirmatory.
  LPR exact-case, 30-s deadline, 40-seed and joint-two-control eligibility
  must be implemented before any LPR holdout can be labeled confirmatory.
- A confirmed P ACK reached `MeshEchoSR.on_ack` to commit the path, but
  `MeshEchoMAG.on_ack` returned before setting `last_ack_at` for action P.
  LPR then stored the new margin/index without its timestamp. A fourth flow
  281 s after P ACK was incorrectly sent by F because the older R feedback
  had expired. Refreshing `last_ack_at` on a committed P ACK fixes the
  observable route-use regression.
- Before seeing LPR development results, the contract now requires at least
  20 P decisions and 10 ACK-confirmed inserted paths across 20 seeds for a
  mechanism-specific claim; lower exposure remains reportable but
  inconclusive, even if an aggregate ACK/airtime gate passes.
- A read-only prior-art audit identified Bypass Routing (Sengul and
  Kravets, *Ad Hoc Networks* 2006, DOI 10.1016/j.adhoc.2004.10.004) as a
  close precursor with one-hop bypass, overheard state, DATA salvage, and
  destination confirmation. AODV-BR, Neighborhood Aware Source Routing,
  and ExOR cover other passive/repair/coordination ingredients. The exact
  LPR combination may be distinct but is not proven novel or superior.
  The five current simulator controls cannot establish superiority to a
  matched classic local-query repair method.
- The runner now refuses a fake LPR holdout unless the development manifest
  and all four artifacts match their hashes, all 100 run rows cover the
  canonical five-policy/20-seed case, recomputed paired summaries agree,
  both primary gates pass, and observed P/inserted-route counts meet the
  prespecified sufficiency rule. It checks output collisions before CLI
  simulation. This protects experiment labeling, not the simulator model.
- A single custom recurring-fading seed 5000 has 41 scheduled unicasts per
  policy. LPR: ACK PDR 13/41, 48.25 s TX airtime, three P decisions, five
  PATCH_RELAY transmissions, zero ACK-confirmed inserted paths. F/R-only:
  11/41 ACKs, 58.49 s; same-trigger F: 14/41 ACKs, 54.79 s. The smoke is
  non-evaluable and gives no population or causal claim. No source-hash or
  artifact-hash mismatch was found.
- The complete 20-seed LPR development run has 834 identical scheduled
  unicasts per policy and no within-seed trace mismatches. Source and all
  four artifact hashes match its manifest. LPR vs F/R-only: paired ACK gain
  +0.0081 [-0.0245, +0.0407], relative airtime +4.8% [-2.7%, +12.2%].
  LPR vs same-trigger F: ACK gain +0.0385 [-0.0003, +0.0772], airtime
  -13.1% [-19.8%, -6.4%]. Both fail the primary ACK lower-bound rule;
  F/R-only also fails the +10% airtime upper-bound rule. The joint gate is
  false. LPR made 69 P decisions but only seven ACK-committed inserted
  paths, below the predeclared ten. Periodic and unobserved-edge controls
  do not establish a localization advantage. See
  `docs/research/meshecho_lpr_dev_results.md` for the complete bounded
  result table. Holdout 4001--4040 remains untouched.

### 2026-10-03 Post-LPR Failure Diagnosis

- Rejoined frozen LPR action and flow JSONL by `(seed, flow_id)` without
  rerunning any simulation. Of 69 P decisions, 52 got an in-deadline ACK,
  11 delivered DATA without a source ACK, and six had no in-deadline
  destination delivery. Of the 52 ACK-confirmed P flows, only seven
  committed an inserted relay path; the other 45 used the old direct edge.
  This narrows the next mechanism question to ineffective relay selection
  and reverse confirmation, not simply the P trigger threshold.
- The entire LPR development case has mean destination PDR 0.788 versus
  source-ACK PDR 0.563; the gap is present in matched controls too. Source
  cannot observe destination delivery without an ACK, so a new decision
  rule may not use that oracle signal. A reverse-ACK repair/confirmation
  design is a hypothesis, not an established gain or unique contribution.
- Action/flow joins identify a larger ACK-confirmation opportunity in F:
  173 `no-confirmed-route` F flows produced 80 ACKs, 92 destination-only
  deliveries, and one no-delivery; 115 `route-ack-misses` F flows produced
  52 ACKs and 63 destination-only deliveries. Thus 155 of 288 useful-DATA
  floods delivered DATA without a source ACK. This is a development-set
  diagnosis, not independent validation. It suggests studying destination
  selection of one or a bounded number of reverse ACK paths from *actually
  received* DATA copies, rather than speculative forward P relays.
- R flows are less obviously an ACK-only opportunity: of 477 R decisions,
  282 had ACK, 25 delivered without ACK, and 170 did not deliver. Any next
  algorithm must not imply that better ACKs alone fix broken forward routes.

### 2026-10-03 Independent LPR Failure and Replacement Audit

- A read-only audit of the frozen 5001--5020 output confirmed the 69 P
  decisions split into 45 ACKs on the old route, seven ACKs on inserted
  routes, 11 destination-only deliveries, and six non-deliveries. All 69
  generated PATCH TX. The 11 destination-only flows reached the destination
  within 1.17 s, so their missing source ACKs are not explained by the
  30-s application deadline alone. Per-candidate receive/collision logs are
  absent, so the 207 PATCH_RELAY TX cannot be assigned a single loss cause.
- The old successor accepts PATCH immediately, whereas off-path candidates
  defer. This direct-first ordering explains why many P ACKs retain the old
  route, but stale observations/collisions are not ruled out. A queued relay
  becomes `PendingSend.committed` at `tx_request`, before its actual air
  start; after that, successor-continuation reception cannot cancel it.
  This is a code-level semantic issue, not yet a quantified cause of the
  population result.
- `CalmMesh.on_fallback` suppresses later FLOOD copies by flow key before
  destination path inspection, so the destination has only the first
  accepted realized reverse path. A bounded distinct-path ACK window is
  implementable in principle, but current artifacts do not show whether
  distinct paths would reach the destination or whether extra ACKs help.
- A new device-local hypothesis is a one-bridge ACK proposal based on
  passive two-sided reception, followed by at most one designated payload
  relay that cancels when the old successor continues. Its likely prior art
  includes bypass routing and cooperative ARQ; no global novelty or gain is
  established. It must be compared against matched local-query repair,
  random bridge selection, and same-byte F/R/useful-DATA flood controls.
- `Simulator.begin_transmission` currently sets `pending.committed = True`
  and books the future `Transmission`, TX counters, airtime, and energy at
  `tx_request` even when `start = node.tx_available_at > now`. LPR's
  cancellation check requires `not pending.committed`; its `on_transmit`
  also removes the pending relay handle immediately. A focused public-flow
  reproduction is needed before changing this shared simulator behavior.
- Existing LPR cancellation tests cover direct-success and earlier-relay
  suppression while a candidate still has an uncommitted delay timer. They
  do not cover cancellation after its TX request has entered a busy node's
  queue but before the reserved airtime actually begins.
- A busy node with `tx_available_at > now` may have contiguous already-booked
  transmissions covering its queue wait; `receiver_is_transmitting` would
  prevent overhearing in that interval. Therefore the request-time commit
  boundary is not yet proven to be a protocol or PHY error. Do not patch the
  shared simulator solely from static inspection.
- Two independent read-only audits confirmed that `on_fallback()` checks
  `seen_floods` before destination path inspection: only the first useful
  FLOOD path generates a reverse ACK. An in-memory passive diagnostic on
  already-examined seeds 5001--5003 saw at least two distinct destination-
  decoded F paths in 18/22, 12/12, and 7/7 delivered F flows respectively.
  Among F destination-only flows the counts were 12/15, 6/6, and 0/0.
  All 18 later distinct paths in those destination-only cases arrived before
  deadline; 17 had different source-adjacent hops. These observations show
  candidate exposure only: additional ACK transmissions will change radio
  collisions, half-duplex reception, and airtime.
- Source ACK acceptance for F is already deadline-limited and permits any
  realized F path (`MeshEchoSR.on_ack_packet`); `Metrics` records the first
  source ACK only, and that first ACK commits its carried path. This makes a
  bounded second ACK a plausible isolated receiver-side algorithm change,
  but second ACKs must not cause duplicate delivery or silently change the
  first-confirmed route. The equal-extra-ACK control should retransmit on
  the first path at the same second-path decode event/time.
- `Packet.created_at` is simulator metadata and is excluded from modeled
  wire length. A destination-local ACK-diversity policy may start a fixed
  window from its own first successful FLOOD reception, but it must not use
  `created_at` as if the device knew the source's 30-s application deadline.

### 2026-10-03 MeshEcho-DPA Deterministic Feasibility

- Three named DPA arms now share F/R source behavior: an alternate real-path
  ACK, a same-trigger repeat of the first ACK path, and a single-ACK control.
  A four-node two-branch packet simulation observes the expected two, two,
  and one destination ACK transmissions respectively.
- The first eligible second-path event is recorded once as
  `event="dpa_second_path"` with both actually decoded paths. Same-first-hop
  paths and third distinct paths do not trigger extra ACKs. State expires
  after the 3-s local window and is capped at eight active destination
  windows per node.
- In a deterministic test that blocks only the first path's ACK at the
  source, DPA receives the second-path ACK and commits `(0,2,3)`; matched
  first-path ACK repeat and single-ACK arms remain unconfirmed. This proves
  a feasible rescue case, not prevalence, average reliability gain, novelty,
  or acceptable airtime cost in a population.
- A DPA F ACK with `origin` changed from the real destination to another
  node was previously accepted by inherited SR source logic and committed a
  route. An end-to-end red test reproduced it; DPA now rejects any ACK whose
  claimed origin differs from the registered flow destination. All three
  DPA arms share this guard, so the matched comparison stays aligned.
- In the two-branch broadcast-radio test, the source physically decodes
  both the destination's off-path direct ACK and the relayed on-path ACK
  for each path. The former is rejected by `ack_next_hop_matches`, so raw
  source ACK reception events are not the same as valid route confirmations.
  DPA action logs now mark `on_path` and `accepted` separately, alongside
  first/second destination paths and actual destination ACK TX times.
- Independent DOI/RFC prior-art check found a close conceptual precursor in
  DSR (RFC 4728, DOI 10.17487/RFC4728): the destination can reply to multiple
  path-carrying route requests on reverse paths, and small DATA can be
  piggybacked on discovery. AOMDV (10.1002/wcm.432) establishes multipath
  route acquisition; LoRa flooding (10.1109/ITNAC62915.2024.10815298)
  and opportunistic LoRa mesh routing
  (10.1109/WoWMoM57956.2023.00065) cover additional ingredients. This
  rules out broad "novel multipath feedback" language. The exact bounded
  delivery-ACK combination was not verified in a bounded search, which is
  not evidence that it is globally new. Any paper claim must rest on
  comparison against matched ACK repeat, single ACK, and discovery controls.

### 2026-10-03 DPA Pre-Development Safety Audit

- The current ICC manuscript reports 0.624 versus 0.621 ACK PDR for
  calibrated MeshEcho versus matched-recovery PRR-product on recurring pairs,
  and 0.486 versus 0.486 on random pairs. It explicitly says the max-min
  score has no demonstrated benefit. More threshold tuning is therefore not
  a supported route to a stronger algorithm claim.
- The original DPA first-path branch called `CalmMesh.on_fallback` before
  validating the claimed path. A real-packet test changed sender 1's FLOOD
  path to `(9, 1)`; the destination emitted an ACK on `(9, 1, 3)`. The DPA
  receiver now checks source origin, physical last sender, loop freedom, and
  hop bound before parent delivery/ACK. A later valid path may still become
  the first accepted path. This fixes a contract violation in malformed
  inputs; it does not establish any performance gain in honest traffic.
- The runner supports three DPA arms, exact 6001--6020 development seeds,
  manifest integrity and a gated 4001--4040 holdout. No DPA population
  experiment had run at the time of this checkpoint.

### 2026-10-03 DPA Development Result

- The frozen 6001--6020 matrix covers 817 scheduled unicasts per policy on
  20 seeds with identical per-seed case and application-trace hashes. DPA had
  179 eligible second-path events across all 20 seeds, so low exposure does
  not explain the negative joint result.
- DPA versus single ACK: paired deadline ACK-PDR gain +0.1104 with nominal
  95% CI [+0.0455,+0.1753]; relative full TX-airtime change -15.0% with
  CI [-23.3%,-6.7%]. This passes one prespecified comparison.
- DPA versus same-trigger first-path ACK repeat: paired ACK-PDR difference
  -0.0258 with CI [-0.0835,+0.0319]; relative TX-airtime +7.6% with CI
  [-7.0%,+22.2%]. This fails the second comparison and the joint gate.
- The DPA result does not establish that path diversity beats a simple
  retransmission. It cannot justify the ICC algorithm claim or opening the
  untouched 4001--4040 holdout. Full details are in
  `docs/research/meshecho_dpa_dev_results.md`.

### 2026-10-03 ICC Core-Rewrite Evidence Map

- The current five-page manuscript's title, abstract, contribution list,
  policy equation, tables, figure, and conclusion all refer to calibrated
  max-min route selection, not a new MeshEcho-SR core mechanism. Keeping its
  old numbers under a new title would be misleading.
- The network/PHY model, seed-paired inference definition, stylized-product
  caveats, and physical limitations can be reused if unchanged. Every new
  mechanism result and plot must be recomputed from fresh complete runs.
- `docs/research/icc_core_rewrite_revision_map.md` records section-by-section
  replacements and the evidence chain for a major manuscript revision.

### 2026-10-03 DPA Flow-Level Forensics

- Independent read-only join of frozen DPA action/flow logs found that DPA
  and same-trigger repeat have nearly equal F ACK counts (137/210 versus
  136/209); their observed total ACK difference mainly follows later R
  flows (395/607 versus 417/608). Closed-loop decisions make these counts
  descriptive, not a causal matched-route comparison.
- Across DPA's 179 second-path opportunities, the alternate B path was
  never shorter than the first A path: 73 equal-hop, 95 one-hop longer,
  nine two-hop longer, and two three-hop longer. The source accepted 50 B
  ACKs; 19 of those B routes were longer than A. Actual ACK hop TX totaled
  1461 for DPA versus 1350 for repeat across 20 runs.
- A strict same-seed/flow, same-first-path and both-F-success subset has
  only ten episodes and 40 subsequent R flows before either policy next
  floods: DPA ACKed 26/40, repeat 30/40. This is too small and still subject
  to interference divergence to prove cache-path causation. Pooled DPA
  post-B R success (171/231) actually exceeds pooled post-A (224/376), a
  strong warning against claiming B routes are intrinsically worse.
- The observed paired ACK-PDR interval versus repeat crosses zero; the
  20 seeds split 10/10 by which arm has more total ACKs. The defensible
  conclusion is failure of DPA's prespecified superiority gate, not a
  population-level proof that repeat is superior.

### 2026-10-03 RAC implementation status

- MeshEcho-RAC currently has three passing real-packet tests for a diamond
  rescue, normal-ACK cancellation, and registered repeat/single controls.
  These are deterministic feasibility checks, not a gain estimate.
- The first implementation still lacks its promised per-node state caps and
  expiry, on-path duplicate ACK suppression, and TTL charging for the
  additional off-path hop. These are pre-simulation safety gates, not paper
  results. The 4001--4040 holdout remains unopened.

### 2026-10-03 RAC pre-development smoke

- Seed 7000 is a non-evaluable smoke, not part of either the development or
  holdout split. Three arms shared the exact scheduled traffic hash and had
  43 unicast flows each. All four generated artifact hashes match the
  manifest in `results/meshecho_rac_smoke_seed7000_20261003.*`.
- RAC recorded 75 eligible candidate events, 48 actual off-path repair TX
  events, and 32/43 deadline ACKs. Repeat and single ACK also each had
  32/43. Complete-network TX airtime was 29.88 s (RAC), 27.53 s (repeat),
  and 31.58 s (single). These single-seed values cannot estimate population
  gain; they show only that the code path and cost instrumentation ran.
- Of RAC's F flows, three were source-ACKed with repair marker 0. Matched
  policy actions had already diverged for some flows, so this is mechanism
  feasibility rather than a causal population comparison.
- Independent runner audit found pre-development integrity gaps: custom and
  generic splits could expose reserved development seeds, and action events
  were counted without unique candidate/flow/timing validation. The runner
  owner is adding test-first guards before the frozen matrix.

### 2026-10-03 RAC frozen development result

- Exact 7001--7020/three-policy matrix completed with 60 run rows, 816
  shared scheduled flows per arm, matching per-seed traffic/config hashes,
  and four artifact hashes matching the manifest. There were 4181 eligible
  corridor events across all 20 seeds and 3708 actual off-path relay starts.
- Seed-paired RAC ACK-PDR gain vs on-path repeat is +0.0606, nominal 95% CI
  [+0.0065,+0.1148]; relative full TX airtime is +23.2%, CI
  [+8.0%,+38.4%]. Against single ACK, the ACK gain is +0.1512, CI
  [+0.0961,+0.2063], but relative airtime is +6.0%, CI [-3.9%,+15.9%].
- Reliability passed both comparisons, yet both airtime upper bounds failed
  the predeclared +10% gate. The joint gate is false; holdout 4001--4040
  remains unopened. `docs/research/meshecho_rac_dev_results.md` preserves
  full interpretation and limitations. No ICC paper/version promotion.
- Independent action-log join found 3647/3708 physical repairs targeted the
  source, where no forwarding continuation exists to cancel a candidate.
  All 473 cancellations occurred at intermediate hops. In hindsight,
  3497/3708 repairs started after source acceptance, but that acceptance is
  not locally visible to a candidate; no such savings can be claimed from
  the current protocol. A source ACK_DONE beacon is a distinct, untested
  hypothesis that would need a fresh development cohort and charged airtime.
- RAC's current candidate/intermediate validity check consults global
  `sim.metrics.flows` and source-side `flow_data_actions`. It is not yet a
  device-local protocol implementation; a successor must replace those
  lookups with packet-carried and locally observed state before ICC use.

### 2026-10-03 Device-Local Source-Closure Audit

- The simulator-global access is at `lora_mesh_sim.py:3378-3392`,
  `3399-3414`, `3460-3504`, and `3559-3602`: candidate/intermediate
  validation, expiry, and transmission gating depend on `metrics.flows` or
  source-only `flow_data_actions`. Source-side ACK acceptance may legitimately
  use source-local pending/accepted state; non-source nodes may not.
- Among the frozen RAC repairs, 3647/3708 had the source as next ACK hop.
  A minimal closure mechanism can therefore test one-hop ACK_DONE first;
  multi-hop closure forwarding is not required by this specific failure.
  It must be sent only on a valid first ACK acceptance, and a candidate may
  cancel only after actually decoding a matching DONE. Loss, collision, or
  late arrival must leave the candidate eligible to repair.
- The current `Packet.created_at` is not serialized on wire, so it cannot
  give intermediate devices the source creation deadline. New packet/state
  rules must derive expiry from locally observed time and/or explicitly
  charged bytes. A path-free, one-hop ACK_DONE would be 10 bytes under the
  current wire-size model, but its transmission, energy, and collisions
  still need real accounting. Timing feasibility remains unmeasured.
- `Packet.wire_size_bytes` starts with 10 bytes for kind/TTL/flow ID/endpoints;
  `created_at` and `protocol` are simulator metadata. `Packet.is_control`
  currently recognizes only RREQ/RREP/ACK, so ACK_DONE requires an explicit
  control classification. `MeshEchoSR.on_ack_packet` already checks source
  pending-flow identity and deadline before route commit; those checks are
  legitimately source-local, unlike RAC candidate checks.
- `Simulator.mark_acknowledged` invokes `protocol.on_ack` only for the first
  accepted source ACK. This callback is the causal point for scheduling a
  source ACK_DONE, whereas receipt of an arbitrary ACK at the source is not.
  `Simulator.begin_transmission` charges every scheduled packet's actual
  TX airtime, TX/RX energy, and collision exposure; an ACK_DONE must enter
  through this ordinary packet path. `CalmMesh.on_receive` handles only
  RREQ/RREP/DATA/FALLBACK/ACK, so an ACK_DONE subclass handler must consume
  it explicitly and must never forward a TTL-1 closure packet.
- A candidate can compare the ACK path prefix ending at the intended next
  hop with the exact FLOOD prefix it previously decoded from that hop. This
  is stronger and more device-local than RAC's sender-only observation.
  The on-path recipient can validate against its own decoded FLOOD prefix;
  `ack_next_hop_matches` alone checks path index, not physical ACK sender.
- Prior-art search identified Jang, Choi & Lim, *Wireless Communications and
  Mobile Computing* 11(7), 939--953 (2011), DOI 10.1002/wcm.991: the prior
  forwarder informs adjacent nodes after relay forwarding to suppress
  duplicates. OFA (DOI 10.1109/IB2COM.2011.6217923) likewise uses an
  intermediate ACK on behalf of a forwarder when the direct ACK fails.
  These precedents prohibit a broad "first cancellation beacon" or "first
  cooperative ACK relay" claim. The CLAR paper would need a much narrower
  validated LoRa-specific trade-off and direct comparison.
- FSA (ICC 2009, DOI 10.1109/ICC.2009.5199042), piggybacked duplicate
  suppression (IEEE Communications Letters 2012, DOI
  10.1109/LCOMM.2012.022112.120203), and slotted ACK coordination
  (IEEE/ACM ToN 2016, DOI 10.1109/TNET.2014.2387440) are further close
  candidate-coordination precedents. The prior-art audit is ongoing; CLAR
  must be framed as a tested LoRa-specific combination, not invention of
  candidate suppression. Existing RAC JSONL action logs have candidate
  eligibility, source ACK acceptance, and physical repair-start timestamps,
  which can bound timing opportunities but cannot predict CLAR outcomes.
- A structured join of the frozen RAC JSONL found 144 accepted first F ACKs.
  At SF7 the proposed 10-byte ACK_DONE has 0.041216-s modeled ToA. Across
  *all* 3708 RAC repair starts, 3497 started later than source acceptance
  plus one ideal ACK_DONE airtime; the same 3497 had started after acceptance.
  This is a loose temporal upper bound only. The repair-start JSONL lacks
  path-index detail, so a join to candidate eligibility yielded 3650
  source-next starts while the independent packet-level audit found 3647;
  use the packet-level 3647 for exact breakdown and do not promote this
  diagnostic into a CLAR effect estimate. Source queueing, receiver loss,
  collision, and changed flow trajectories are not covered.
- First multihop CLAR test reproduced a local-state cancellation bug:
  candidate 2 decoded node 1's real forwarded ACK at 1.392864 s, yet later
  sent an off-path repair at 1.991408 s. The ACK had moved to path index 0;
  using the *new-repair eligibility* predicate required a FLOOD from source
  0 that candidate 2 did not need for its already pending repair to node 1.
  Cancellation needs a separate, strict physical-sender/path match against
  the pending record before new eligibility validation.
- A real multihop low-TTL counterexample found a second CLAR safety flaw:
  the first F ACK reached an intermediate with `ttl=1`, which could not
  forward, but it entered `seen_ack_hops` and blocked a later copy with
  sufficient TTL. The non-source TTL guard now precedes deduplication;
  source reception of the final `ttl=1` hop remains allowed.
- A late-ACK counterexample found candidate pending repair expiring 30 s
  after the ACK instead of the FLOOD it depended on. A FLOOD decoded near
  1 s expired near 31 s; an ACK at 30.8 s had scheduled a repair after that
  local observation expired. The pending timer and attempt guard now inherit
  the exact locally decoded FLOOD observation expiry, so the timer cannot
  send after evidence expires. No source deadline oracle was added.

### 2026-10-03 CLAR Queue-Start Boundary

- `relay_ack_if_pending` and `repeat_ack_if_pending` check locally observed
  expiry at the timer event and then call `Simulator.transmit_later`.
  `Simulator.begin_transmission` immediately computes actual TX start as
  `max(now, node.tx_available_at)` and charges/registers that future TX.
  Therefore a valid timer decision can still lead to a physical TX after
  the observation expires. This is a suspected contract violation, not yet
  a reproduced failure or a measured population effect.
- A deterministic real-queue test should establish whether actual TX start
  crosses the local expiry; any fix must use the predicted actual start,
  preserve real airtime accounting, and avoid simulator-global information
  at a candidate node.
- The new `test_queued_repair_does_not_start_after_local_observation_expires`
  reproduces this: 10 genuine short transmissions from the candidate fill
  its radio queue past the FLOOD observation expiry, CLAR records candidate
  eligibility, and the current implementation still records `clar_repair_tx`.
  The first pytest selector had the wrong class name and collected no test;
  the corrected selector produced the expected assertion failure.
- An independent device-local audit found a separate false-cancellation
  path: `on_receive` applies `cancel_on_ack_continuation` before new ACK
  eligibility validation. A physically decoded matching on-path ACK with
  `ttl=0` could delete a pending repair although the ACK cannot reach or be
  accepted at the source. A deterministic multihop public-packet test
  reproduced `clar_cancel` and missing repair. Cancellation must validate
  continuation fields independently, because requiring the candidate's
  *new* off-path eligibility would reject valid intermediate-hop
  continuations it can overhear.

### 2026-10-04 CLAR Runner Window Audit

- The runner currently keeps raw `on_transmit` action events even when the
  simulator reserves a TX start after the 630-s cost window. Its windowed
  transmission counter correctly excludes such starts, but CLAR manifest
  validation rejects action timestamps beyond 630 and compares all raw
  `clar_done_tx` events to windowed DONE counts. A legitimate queued-future
  frame could therefore make a development artifact self-invalid. A
  read-only one-frame reproduction was reported: requested at 629 s with
  sender busy until 631 s, `clar_done_tx.time=631`, windowed DONE count 0.
  Runner-owned test-first correction is underway; no CLAR seeds opened.
- The runner correction retains raw TX actions after the 630-s cutoff but
  compares `windowed_done_tx` and bytes only to action starts within the
  cutoff. A real queued-future ACK_DONE test and a hashed-manifest test pass;
  the complete suite is 401 passed, one skipped.
- Seed-8000 custom smoke is mechanism-only: all four arms each scheduled 42
  same-trace unicasts; all four source and data-artifact hashes verify.
  CLAR had 164 eligible candidates, 143 source-DONE cancellations, and 13
  off-path repair starts. Its 29/42 deadline ACKs and 34.615-s full airtime
  versus repeat's 30/42 and 29.187 s are single-seed descriptions, not a
  population estimate or a reason to retune the frozen mechanism. F/R
  source decisions diverged after the shared application trace because
  protocols feed back through different interference/ACK outcomes.

### 2026-10-04 Frozen CLAR Development Result

- Exact `clar-development` 8001--8020 four-arm matrix completed. Manifest
  lists 80 runs, 3188 arm-scheduled unicasts (797 per arm), all four frozen
  source/design/runner hashes, and four data artifact hashes; independent
  SHA-256 calculations match every value. Every seed has four arms with
  identical application-trace hash, case hash, and scheduled flow count.
- Deadline ACK totals: CLAR 518/797, same-beacon/no-cancel 519/797,
  on-path repeat 528/797, plain single ACK 422/797. Destination delivery:
  598, 595, 619, and 593/797 respectively. Aggregate full-network TX
  airtime across 20 runs: 622.113, 843.355, 599.637, and 757.841 s.
- Seed-paired CLAR minus repeat ACK-PDR is -0.0161 with nominal two-sided
  95% CI [-0.0547,+0.0226]; relative airtime +7.7%, CI [-5.5%,+21.0%].
  CLAR minus plain single ACK is +0.1191 [0.0665,0.1718] ACK-PDR and
  -14.3% [-24.9%,-3.7%] airtime. CLAR minus no-cancel is -0.0069
  [-0.0508,+0.0370] ACK-PDR and -24.0% [-32.9%,-15.2%] airtime.
  The predeclared joint primary gate is false because CLAR does not beat
  repeat and its relative-airtime upper CI exceeds +10%. No holdout.
- Mechanism exposure is real: CLAR logged 4091 eligible candidates over all
  20 seeds, 3192 source-DONE cancellations, 273 ACK-continuation
  cancellations, and 626 off-path repair starts. The same-beacon/no-cancel
  arm logged 3830 repair starts, but closed-loop arms diverge, so this is
  a descriptive ablation, not a per-event counterfactual. CLAR versus
  repeat remains the decisive unfavorable comparison.
- Post-run forensic validation found a runner allowlist omission: the
  frozen repeat arm emitted 84 legitimate `clar_cancel` events with reason
  `source-done-repeat`; `validate_clar_development_manifest` currently
  rejects them before it reaches the known failed-gate verdict. Other
  cancellation reasons in the frozen action log are CLAR 3192
  `source-done` and 273 `ack-continuation`, no-cancel 318
  `ack-continuation`, and repeat 71 `ack-continuation-repeat`.
  The frozen source/artifact hashes and paired outcome calculations remain
  unchanged, but the self-validation gap must be fixed and disclosed as a
  post-run validator correction.
- Targeted Crossref/OpenAlex/RFC Editor source checks confirm that AODV
  local repair, DSR packet salvaging, relay-assisted ARQ, multipath mesh
  redundancy, LoRa opportunistic forwarding, and implemented reliable
  LoRaMesher data transfer all precede a proposed same-flow R rescue.
  `docs/research/meshecho_same_flow_recovery_prior_art_brief.md` records
  six external verified references plus the frozen local evidence. A
  successor cannot claim generic retry or route repair as original; it
  needs a distinct source-local rule, matched same-trigger controls, and
  independent evaluation.

### 2026-10-04 Resumed Structural Decision

- The current SR source-local 15-s ACK guard updates route state for later
  flows; it does not recover the same DATA flow (`lora_mesh_sim.py`,
  `MeshEchoSR.on_transmit` and `expire_data_ack`). CLAR acts on F ACKs and
  cannot resolve the dominant 196 unacknowledged R flows whose DATA never
  reached the destination in the frozen development results.
- This supports replacing the paper's core reliability decision, not
  further CLAR timer/beacon tuning. Preserve the simulator and measurement
  path, but compare any new decision with R-repeat and F-fallback triggered
  at the same source-local time and charged at full network cost.
- These development observations select a research direction only. They do
  not establish a successor's gain, novelty, or ICC acceptance odds.

### 2026-10-04 DHR Implementation Findings

- The inherited reverse ACK constructor dropped `repair_index`; the
  test-first one-line echo now makes a rescue ACK one charged byte longer.
  Existing unmarked ACKs keep their size. A F-rescue ACK on an alternate
  realized path was rejected by SR's original-path check; DHR now validates
  marker 2 separately and commits only that confirmed path.
- `Simulator.begin_transmission` books future queued transmissions when
  handling the request; later ACKs cannot cancel already booked future TX.
  DHR therefore requires the source radio idle at guard and `start == now`
  at the TX request. Its nominal bound prices both possible rescue actions,
  including a max-length F path and +0.35 s per weak-link relay.
- DHR's additional operational flow table is capped at eight active R flows
  per source, with admission refusal on overflow and expiry after the
  original deadline. Inherited simulator history maps remain instrumentation,
  not a full firmware-memory claim. No population effect is known yet.
- DHR currently inherits the initial MeshEcho-SR F/R/D decision and adds a
  source-local branch after an unACKed initial R DATA: one R repeat or one F
  fallback, selected by accepted-ACK freshness and consecutive R misses.
  Thus this is a new same-flow recovery mechanism on a reused simulator/data
  plane, not a ground-up routing algorithm. Generic retry and route repair
  have clear prior art; any ICC claim needs matched-control gains and a
  carefully delimited decision-rule contribution.
- All nine DHR packet/guard tests pass, including duplicate delivery after
  ACK loss, late original ACK after F-route commit, and SF12 budget refusal.
  Complete regression is 430 passed, one skipped. These tests establish
  implementation behavior only; they do not establish gain or novelty.

### 2026-10-04 Frozen DHR Development Result

- The one frozen four-arm 9001--9020 development matrix is complete: 80
  runs, 803 scheduled unicasts per arm, verified source/artifact hashes, and
  complete trace/config/flow/action pairing. Manifest validation reaches
  the expected joint-gate failure after passing integrity checks.
- DHR versus fixed R repeat has paired ACK-PDR +0.0227 with nominal 95% CI
  [-0.0179,+0.0632] and full-network airtime +16.4% [7.8%,25.0%].
  Versus fixed F fallback, ACK-PDR is +0.0005 [-0.0515,+0.0524] and
  airtime -13.9% [-21.4%,-6.4%]. The prespecified joint gate fails;
  exposure passes (175 guards, 109 R and 66 F actual rescues).
- Fixed F delivered 799/803 packets at destinations versus DHR's 736/803;
  source ACK totals were 570/803 versus 578/803. This distinction matters
  when interpreting the apparent ACK/airtime trade-off. The 120-s local
  heuristic has no demonstrated advantage over both simple controls.
- This is evidence for a genuinely different core decision mechanism, not
  a threshold retune on inspected seeds. The DHR holdout stays sealed and
  the old ICC manuscript/PDF, VERSION, GitHub, and EDAS stay untouched.

### 2026-10-04 New-Core Scoping

- The current ICC manuscript's route-score comparison already reports no
  distinct advantage over a PRR-product control. DHR's same-flow recovery
  heuristic also failed its two simple frozen controls. The full user goal
  therefore remains open; the existing paper cannot merely be relabeled.
- Frozen DPA evidence independently failed against an on-path ACK repeat:
  paired ACK-PDR -0.0258 [-0.0835,+0.0319] and airtime +7.6% with a
  +22.2% upper bound. This rules out citing generic second-path ACKs as a
  demonstrated gain in the present simulator. It does not rule out a
  structurally different, cost-aware forwarding/feedback mechanism.
- A fresh targeted prior-art audit found that passive next-hop overhearing,
  witness-based replacement of overheard DATA, local bypass repair, and
  candidate coordination are not new primitives: ExOR (SIGCOMM 2005,
  DOI 10.1145/1080091.1080108), WAR/AODV-BR as discussed in Bypass Routing
  (Ad Hoc Networks 2006, DOI 10.1016/j.adhoc.2004.10.004), and LoRa
  opportunistic routing (WoWMoM 2023, DOI 10.1109/WoWMoM57956.2023.00065)
  are close. An ICC claim must isolate a specific LoRa deadline/airtime/
  half-duplex decision and compare against established candidate/local-
  repair controls, not claim implicit ACK or local repair as first-of-kind.
- In the frozen DHR arm, a read-only (seed, flow_id) join gives 109 physical
  R rescues with 45 in-deadline destination deliveries and 32 source ACKs;
  66 physical F rescues with 66 deliveries and 24 ACKs. Thirteen R-rescued
  and 42 F-rescued flows were delivered but unACKed. These are within-arm
  descriptive outcomes on different histories, not causal R-versus-F
  effects. The F arm's 224/229 delivered-unACKed flows with no source ACK
  callback further implicate the reverse feedback path.
- On 2026-10-04, the live official ICC 2027 symposium CFP at
  `https://icc2027.ieee-icc.org/authors/call-symposium-papers` lists paper
  submission deadline 16 October 2026, acceptance notification 15 January
  2027, and camera-ready due 19 February 2027. It links IoT & Sensor
  Networks to EDAS `https://edas.info/N35508`. The old 2 October date in
  some PDF/strategy snapshots is stale; exact EDAS closing time still needs
  confirmation before submission.
- The live official ICC 2027 submission guidelines at
  `https://icc2027.ieee-icc.org/submission-guidelines` require initial
  English papers of at most six printed 10-point pages, PDF-only EDAS
  submission, and exact author-list/title agreement between PDF and EDAS.
  They prohibit simultaneous submission and require presentation after
  acceptance for proceedings/Xplore publication. The old five-page PDF
  passes page count alone; it remains methodologically unready as a new
  algorithm paper.
- Preliminary observability diagnostic on exploratory seed 11001 exactly
  reproduced the existing SR runner's application trace hash and 33 flows,
  23 deadline ACKs, and 27 deadline destination deliveries. It observed
  35 initial-R physical DATA hops: 27 intended receivers decoded and eight
  did not. Passive forwarding/last-hop-ACK evidence had no false positive
  or false negative on this seed. All eight failed hops had a candidate
  under the diagnostic's *oracle* single-relay/path-PRR/timing test; this
  is not a device-observable rescue count or measured algorithm success.
  Two further seeds and reverse-ACK hop tracing are still pending.

### Completed Exploratory SR Observability Diagnostic

- The isolated tool `tools/diagnose_sr_observability.py` and its 12 focused
  tests now cover seeds 11001--11003. Each run matches the existing runner's
  application trace, flow count, deadline ACK count, and destination delivery
  count. This validates diagnostic reproducibility, not a new protocol.
- Across the three seeds, 134 first-R physical DATA hops were evaluable:
  102 intended next hops decoded and 32 failed. Passive progress evidence
  falsely signaled failure on 5/102 successful hops and never falsely
  signaled success on 0/32 failed hops. The oracle single-relay screen found
  a guard-time candidate for 32/32 failed hops, but assumes knowledge and
  ignores future collisions; it is an optimistic upper bound only.
- Initial reverse ACK hops also fail: 20 of 143 initial ACK transmissions
  were not decoded across these seeds. This is a hop-level count, not a
  count of distinct affected flows or a causal attribution of source ACK
  failures. A source timeout cannot by itself identify whether DATA or ACK
  was lost.
- The diagnostic does not establish novelty or advantage against R-repeat,
  F-fallback, local bypass, or opportunistic forwarding. It supports the
  scope of a core decision redesign on the existing validated simulator,
  followed by new packet tests and fresh matched experiments.

### Failure-Synthesis Boundary for Next Core

- Frozen LPR had 207 `PATCH_RELAY` transmissions but only seven ACK-committed
  inserted paths across 20 seeds; its ACK-PDR confidence interval versus
  F/R-only crossed zero. Simply adding off-path DATA relays does not yet
  yield a usable reliability advantage in this implementation.
- Frozen RAC improved ACK-PDR versus an on-path repeat by +0.0606
  [+0.0065,+0.1148], but incurred +23.2% full-network airtime with upper
  confidence bound +38.4%. Its source-next repairs dominated extra cost.
  CLAR's charged source closure canceled many pending repairs, yet its
  paired ACK-PDR difference versus repeat was -0.0161
  [-0.0547,+0.0226]. A closure signal alone did not create an advantage.
- These results support a new decision rule conditioned on actual local
  forward/reverse evidence and complete path cost, not a renamed local
  relay or another source timeout. They do not identify a validated new
  algorithm or justify a manuscript claim.

### Checkpoint Hypothesis Exposure Check

- The exploratory SR hop diagnostic splits 134 initial-R physical DATA hops
  by path index: index 0 has 80 hops and 27 failed intended receptions;
  index 1 has 37 hops and five failures; index 2 has 17 hops and no failures.
  Thus 27/32 observed first-R hop losses occur before an on-path relay
  could retain a payload. A pure relay-checkpoint/suffix-replay mechanism
  could directly target at most five observed downstream failures, plus
  delivered-but-unACKed flows; it cannot replace first-hop recovery.
- A receipt-guided suffix mechanism is therefore a conditional hypothesis,
  not the selected core. Its receipt/command airtime must be justified by
  flow-level ACK-loss and deadline exposure before implementation. The
  offline oracle detour count does not prove that any chosen candidate can
  signal or repair at low cost.
- Independent algorithm audit withdrew the checkpoint idea as the primary
  contribution given this exposure. A coded fork/merge could address the
  first hop, but coding, multipath, and bypass are established primitives;
  any candidate first needs branch availability, timing, airtime, and
  locally selectable backup evidence. The current three-seed oracle alone
  cannot establish a deployable replacement algorithm.
- In the exploratory first-hop failures, the offline screen lists 2--39
  guard-feasible off-path decoders per missed hop (27 hops, mean 29.9), but
  these are **oracle** candidate sets, not a single locally nominatible
  backup or measured repair successes. Large candidate multiplicity also
  raises coordination/airtime concerns.
- The verified abstract of Rösler et al. (WoWMoM 2023, DOI
  10.1109/WoWMoM57956.2023.00065) explicitly describes per-hop
  opportunistic candidate sets exploiting spatial diversity under LoRa
  temporal fading. A generic nominated backup or diversity claim would
  overlap that prior work; the exact LoRa band/model differs and the
  abstract alone does not settle a narrower mechanism's novelty.
- Tanjung et al., *Sensors* 2020, "Opportunistic and On-Demand Network
  Coding-Based Solutions for LPWAN Forwarding" (DOI 10.3390/s20205792),
  explicitly combines relay forwarding, opportunistic/on-demand coding,
  header compression, and reliability/capacity evaluation. This verified
  Crossref abstract rules out a generic "LPWAN network coding" novelty
  claim for a fork/merge idea. It does not evaluate this project's exact
  route/ACK contract.
- A more targeted conditional hypothesis is a source-pulled confirmation
  branch: after an R source ACK timeout, *if* the source locally overheard
  the first relay forwarding that flow, a compact query could solicit a
  bounded cached destination ACK or relay state before retransmitting
  DATA. Missing overheard progress is unknown, not proof of DATA loss. This
  may reduce blind DATA duplication on ACK-loss flows, but its exposure,
  wire cost, deadline feasibility, and prior-art distinction remain
  unverified. Flow-level exploratory strata have been requested; no
  candidate has been frozen or implemented.
- That source-progress branch only applies to a multihop first relay. A
  direct source-to-destination R path has no downstream DATA forward to
  overhear; if its ACK is missing, it supplies no positive progress bit.
  The diagnostic must report direct and multihop first hops separately.
- A wire-model-only check for a three-node path and 32-byte application
  payload gives 50-byte DATA, 18-byte ACK, and 19-byte hypothetical marked
  query (10-byte base plus path and one marker). At SF7, their modeled ToA
  values are 0.097536, 0.051456, and 0.051456 s; at SF12 they are
  2.301952, 1.318912, and 1.318912 s. This is **not** a network-cost
  result: a query plus any response/relay DATA, queues, and collisions may
  exceed a simple repeat, and the hypothetical query is not implemented.
- RFC 4728 (DSR; DOI 10.17487/RFC4728), Secs. 3.4 and 8.3.2--8.3.3,
  explicitly uses overheard forwarding as passive ACK and a separate
  network-layer ACK request when passive confirmation fails. Generic
  "listen, then request ACK" is prior art, not a claimable invention. A
  potential source-level *destination-proof cache plus selective suffix
  rescue* would need a precise distinction from DSR route maintenance
  and a matched DSR-like comparator; its novelty remains unverified.

### Fresh First-Hop Exploratory Screen (Preliminary)

- Seeds 12001--12003 reproduce SR runner trace hashes and per-seed scheduled
  flows/ACK/delivery totals. There are 86 initial R first hops: 31 direct
  and 55 multihop. Intended reception failed for 14 direct and eight
  multihop hops (22 total). The strict route-confirming-ACK-before-local-
  nomination screen found a candidate for all eight failed multihop hops
  and six failed direct hops; only four in each stratum actually decoded
  the current DATA (eight of 22 total failures). Guard-time PRR/ToA
  eligibility for those eight still uses an oracle and ignores future
  control traffic/collisions. These are not realized rescue outcomes.
- Source-observed first-relay progress with no source ACK applied to just
  three multihop R flows; all three were not destination-delivered and
  generated no destination ACK. Thus this small exploratory sample does
  not support an ACK-only query benefit. It may leave a suffix-repair
  question, which is close to established relay ARQ/DSR salvage.
- The witness tool initially allowed any prior qualifying FLOOD observation
  before the confirming ACK, without a local expiry. Of 62 nominated
  first hops, 27 witnesses were older than 120 s and nine older than
  300 s at commitment. Two of the four failed-multihop guard-oracle
  candidates had about 195/224-s-old witness evidence. The 4/8 branch
  coverage is therefore an overgenerous history/PHY upper bound. Fixed
  30/120/300-s descriptive TTL strata and tests are being added before
  any candidate decision.
- The earlier fixed-F development control delivered 799/803 flows but
  source-ACKed only 570/803; that gap makes destination-side reverse-path
  choice after useful-DATA FLOOD a candidate diagnostic target. The
  current `on_fallback` ACKs the first delivered copy and then returns on
  duplicates, so it does not compare candidate reverse paths. A delayed
  choice would need an explicit local collection window and all later ACK
  transmissions charged. It is not yet an algorithm gain or novelty claim.

### Final First-Hop Witness Strata and Next Diagnostic

- The completed exploratory witness JSON at
  `/tmp/first_hop_witness_12001_12003_ttl_direct_20261004.json` covers seeds
  12001--12003 and reproduced the SR runner's trace hashes, flow counts,
  deadline ACKs, and deadline deliveries. Ten focused tests passed in the
  preceding continuation. Its 86 initial R first hops split 31 direct and
  55 multihop; intended first-hop reception failed 14 direct and eight
  multihop times.
- Of the 22 failed first hops, prior local witness nomination plus actual
  current DATA decode covered 0 under a 30-s history window, five under
  120 s, and eight under 300 s. The eight are **not** measured forward
  rescues: path feasibility and future interference were not run as a
  protocol. The unlimited-history eight-of-22 headline is not a deployable
  gain estimate.
- All three multihop R flows with source-observed first-relay forwarding
  but no source ACK were undelivered. Among 14 unACKed direct-R flows,
  offline outcomes were six delivered and eight undelivered; the source
  cannot infer this split from its missing ACK.
- Therefore a nominated-first-hop witness and a generic ACK query lack
  demonstrated exposure. The next bounded screen concerns F flows already
  delivered to the destination but unACKed at the source, asking whether
  the destination actually hears multiple distinct inbound FLOOD paths
  before a short, explicitly charged ACK decision window. No new core has
  been selected or implemented.
- `Simulator.handle_tx_end()` invokes `protocol.on_receive()` on every
  physically decoded packet, including repeated FLOOD copies; current
  `CalmMesh.on_fallback()` instead returns immediately when the flood key
  was already seen. Thus a behavior-preserving observer can count locally
  decoded distinct inbound paths, but any delayed selection would change
  on-wire timing and must be tested as a separate protocol with all
  transmissions charged. Received `RxInfo` contains sender, RSSI, SNR,
  SINR, and collision status; offline path PRR is not a local observation.
- A preliminary Crossref phrase search for reverse-ACK path selection
  returned generic wireless-mesh multipath results, not a sufficiently
  close, verified mechanism source. Novelty remains unverified; no citation
  or first-of-kind claim follows from that search. The exact exploratory
  exposure screen is frozen in
  `docs/research/meshecho_flood_ack_path_feasibility.md` before its results.
- The DHR report records 803-flow aggregate outcomes and hashes for
  per-flow/action JSONL, but the accessible repository `results/` contains
  only DHR run/paired CSVs and the known top-level `/tmp` listing contains
  no DHR JSONL. Aggregate totals alone cannot localize an individual
  reverse-ACK failure; the new diagnostic must collect that evidence anew.
- The DHR report's `meshecho-dhr-flood` control uses F as a fixed recovery
  action, not necessarily for first delivery of every flow. Its aggregate
  delivered-unACKed count cannot be treated as the denominator of a
  destination-FLOOD path-diversity claim. The exploratory contract now
  requires both all-flow and actual-FLOOD strata.
- The frozen DHR comparator contract confirms all arms share initial SR
  action, 15-s ACK guard, 30-s application deadline, admission, marker
  semantics, and one-rescue cap; only the admitted recovery action differs.
  Its failed joint gate is a stronger benchmark than comparison with no
  recovery. Any new core must compare against same-trigger simple choices
  and charge complete-network packet ToA, not only count rescued deliveries.
- The current ICC bibliography contains general LoRa mesh, ETX, PHY, and
  simulator sources but not the close DSR/ExOR/local-bypass/LoRa
  opportunistic-routing sources already identified for a core rewrite.
  The manuscript's related work must be revised and each new citation
  verified before making novelty claims.
- Crossref DOI metadata independently verifies Joy and Branch,
  "Flooding in LoRa Mesh Networks," ITNAC 2024,
  DOI `10.1109/ITNAC62915.2024.10815298`, and "AODV-inspired Routing with
  Next-Hop Caching and Path Selection for LoRa Mesh Networks," IEACon
  2025, DOI `10.1109/IEACON64690.2025.11254006`. An independent abstract
  screen found the former concerns repeated LoRa flood copies and the
  latter multi-route memory/weighted selection; neither abstract alone
  verifies an exact destination DATA-duplicate-to-reverse-ACK rule. These
  are adjacent prior art, not proof of novelty or equivalence.
- Crossref DOI/title/venue/abstract also verifies Lee et al., "Avoiding
  Spurious Retransmission over Flooding-Based Routing Protocol for
  Underwater Sensor Networks," *Wireless Communications and Mobile
  Computing* (2020), DOI `10.1155/2020/8839541`. Its registered abstract
  explicitly says DATA and ACK traverse multiple flood routes and uses
  ACK-copy path similarity to adjust a waiting time. This is a direct
  multipath-ACK precedent in a different PHY. RFC 3561 already uses
  reverse routes for replies. Neither source proves that an exact LoRa
  destination-side path selector is known, but both forbid broad first-of-
  kind claims; absence of an exact hit in this limited search proves nothing.
- `Packet.created_at` is simulator metadata and `wire_size_bytes()` does
  not charge it. A destination-side rule may not read that timestamp as
  device-local knowledge. The draft alternate-ACK contract was corrected:
  destination uses only its own 1-s window; source still enforces its 30-s
  ACK deadline, and all late/ineffective ACK costs remain counted. Adding
  a destination deadline gate later would need a charged on-wire budget and
  age-update semantics, not an implicit shared clock.
- Independent contract review found the model's FLOOD/ACK `request_id`
  field is not separately counted by `Packet.wire_size_bytes`; the
  candidate may only use it as an alias/invariant of the charged flow ID,
  not claim an additional packet field. It must inspect each actually
  decoded duplicate before `on_fallback`'s early return while preserving
  that handler's baseline effects, and enforce the 1-s local window at
  actual TX start. Across closed-loop arms, identical trigger *rules* do
  not imply identical per-flow duplicate receptions or ACK opportunities.
- Preliminary, not yet independently verified: a three-seed fixed-F
  read-only replay on 15001--15003 saw 122/122 deadline destination
  deliveries, 85 source ACKs, and 37 delivered-unACKed flows; 27 of 37
  had a second physically decoded *full FLOOD path* within 1 s. The
  diagnostic is being refined to require a distinct immediate reverse
  ACK next hop; full-path diversity alone may not give a useful first
  alternative. Separately, an independent 14001--14003 ACK-hop replay
  provisionally reports 35 unACKed deliveries with destination ACKs
  emitted and 37 failed ACK attempts. These separate seeds cannot be
  joined per flow and do not estimate alternate-ACK success.
- Final path-diversity exploratory artifact at
  `/tmp/flood_ack_paths_15001_15003_20261004_hops_budget_v3.json`
  matches the uninstrumented fixed-F runner's trace hashes and exact
  per-flow outcome timestamps. It covers 122 scheduled/delivered flows,
  85 source ACKs, and 37 delivered-unACKed flows. Thirty-two of the 37
  were first delivered by FLOOD; 27 of those 32 had a physically decoded
  distinct *first reverse ACK hop* within 1 s (4/19/27/29 at
  0.25/0.5/1/2 s). The other five were route-first and saw no timely
  FLOOD alternative in those windows. This is retrospective exposure,
  not a realized ACK rescue.
- The 27 FLOOD-first flows had 43 distinct alternate-first-hop candidates
  within 1 s. The raw original-deadline time remaining when those packets
  were decoded was min 12.0943 s, median 13.7976 s. These are offline
  upper bounds: `Packet.created_at`, enqueued/deadline times, and
  model-computed SINR are not on-wire destination inputs, and future ACK
  queueing/collisions are unmeasured. Device-observable proxies include
  path/IDs/marker, receive order, and local RSSI/SNR. Ten focused path
  tests pass; combined with five ACK-hop and ten first-hop witness tests,
  the independent relevant suite passes 25/25.
- Final ACK-hop exploratory artifact for fixed-F seeds 14001--14003 records
  138 scheduled unicasts, 138 deadline destination deliveries, and 103
  deadline source ACKs. Of 35 delivered-unACKed flows, all emitted a
  destination ACK; their 37 ACK attempts all terminated at an observed
  physical reverse-hop decode failure, with 19 failures at the first
  reverse hop and 18 at the second. Twenty-three failed at the final hop
  into the source. None was an ACK emitted after deadline, a source decode
  after deadline, or a censored ACK transmission. The diagnostic observes
  actual baseline events only and cannot predict an alternate ACK route's
  success. Its five focused tests pass.
- Independent ACK-branch review found an R-first/F-rescue ambiguity: an
  earlier routed-DATA ACK can precede the first ACK of a later FLOOD epoch.
  Alternate-path eligibility and the same-path control must use that
  FLOOD epoch's first ACK path, not the flow's globally first ACK path.
  Inbound path validation must also match `packet.path[-1]` to actual
  `rx.sender`. The inherited `seen_floods` set is unbounded, so an eight-
  entry added window does not establish bounded whole-protocol memory.
  These points are now explicit in the design; no population result changed.
- The present source-side SR decision (`lora_mesh_sim.py`, `MeshEchoSR.send_app`)
  selects R/F/D from cache presence, two consecutive missing R ACKs, a
  180-s route-age trigger, and discovery tokens. DHR's same-flow choice
  adds a 120-s last-ACK threshold. Those heuristic rules cannot be called
  a new ICC core by retaining their thresholds and changing the label.
  A successor must use packet/local-time observations and compare its
  whole-run ACK/airtime effect against same-trigger fixed R and F actions.
- The prior MAG source-policy study is not a validated shortcut: its third
  development revision improved ACK-PDR over F/R-only by +0.1556 (paired
  95% CI [0.1066, 0.2045]) but missed the prespecified +10% airtime
  ceiling because the relative-airtime CI reached +12.8%, and it had no
  clear ACK gain over an equal-token periodic-discovery control. Reusing
  its margin trigger without a new mechanism and fresh controls would not
  establish a distinct core contribution.
- Source-side missing ACK alone is observationally ambiguous: an R DATA
  failure and a delivered DATA whose reverse ACK failed can both leave the
  source with the same timeout signal. Without an independently observable
  progress/feedback signal, changing a source timeout or age threshold
  cannot correctly classify those cases. This motivates testing the
  destination-observed BAR branch, while keeping its performance and
  originality claims conditional on matched experiments and prior art.
- The frozen 16001--16020 BAR development matrix falsifies the
  alternate-first-hop advantage in this workload. Versus unchanged fixed F,
  alternate BAR has paired ACK-PDR +0.1513 [0.1048,0.1978] with airtime
  -3.6% [-9.3%,+2.1%]. Versus identical-trigger same-path ACK repetition,
  it has only +0.0021 [-0.0292,+0.0334] ACK-PDR and +2.3%
  [-4.7%,+9.4%] airtime, failing both required interval conditions.
  Both added-ACK arms close many more flows than fixed F, so temporal
  repetition, not spatial ACK-path diversity, is the supported explanation.
  These are closed-loop seed-paired effects, not per-flow counterfactuals.
  Holdout 17001--17040 remains unopened.
- Read-only BAR action-log screen for a multi-ACK source-route selector:
  among 248 alternate-arm flows with an actual extra ACK TX, 182 had any
  source ACK callback, 49 had at least two callbacks of any marker, and
  only 31 had at least two callbacks carrying the F-recovery marker.
  `dhr_source_ack_rx` does not record paths, so these are only optimistic
  upper bounds on *distinct returned path* exposure. They do not justify
  a new path-scoring core or estimate its outcome. Any path-level screen
  would require fresh exploratory instrumentation, not BAR holdout use.
- A short ACK-query-before-F source rewrite has poor observed target
  exposure in the inspected BAR fixed-F development arm. Of 194 admitted
  same-flow R timeouts, only 17 had an initial routed DATA destination
  receipt before the guard; 177 did not. The latter need DATA recovery,
  so an unconditional ACK-only query would add control airtime and consume
  deadline slack for most candidates. This classification is offline
  diagnostic history, not a causal trial of a query; no query protocol
  was implemented. The earlier source-observable first-hop witness screen
  also found very few reliable locally nominated opportunities, limiting
  a selective query based on passive progress.
- A fresh read of the current ICC LaTeX confirms it still describes the
  calibrated max-min PRR route-score variant, not MeshEcho-SR or BAR. Its
  abstract explicitly reports no clear advantage over matched PRR-product
  and an adverse unconditioned random-pair workload. A genuine new core
  requires replacing the protocol claim and main numerical evidence, not
  adding an SR/BAR paragraph or retuning 180/120-s thresholds.
- The highest-exposure unresolved branch appears to be forward DATA failure
  after an R timeout, not an unconditional ACK query: the inspected fixed-F
  cohort had 177/194 admitted rescues without initial destination receipt.
  This is an offline descriptive classification only. A hop/deadline-bounded
  recovery idea remains a hypothesis until new behavior-preserving path/cost
  diagnostics, close prior art, and fixed-TTL controls establish a real
  differentiator.
- Original-source prior-art boundary: AODV RFC 3561 Sections 6.4 and 6.12
  seed and bound local repair search TTL from the last known destination hop
  count; DSR RFC 4728 Section 3.4.1 salvages the same DATA packet using an
  alternate cached route with bounded salvage count. Meshtastic's official
  mesh-algorithm documentation says direct DATA can fall back to managed
  flooding on the last retransmission when the next-hop relay was not
  heard. Thus hop-count-capped DATA FLOOD or passive-triggered last-retry F
  alone is not defensible as a novel ICC core. A LoRa-specific joint
  when/whether/radius/deadline/airtime rule remains a hypothesis, with
  fixed TTL, full F, R repeat, expanding radius, and product-like fallback
  required controls. No performance outcome follows from this prior art.
- Bounded prior-art search did not verify an exact LoRa protocol where an
  off-path relay cancels queued useful-DATA FLOOD forwarding after decoding
  the destination's naturally emitted application ACK. Meshtastic already
  suppresses a scheduled rebroadcast after hearing another DATA rebroadcast,
  so generic suppression is prior art; absence of an exact search hit proves
  no novelty. The distinct testable question is whether a valid terminal
  ACK is physically overheard by still-pending off-path relays under this
  half-duplex model. An oracle count of post-delivery TX cannot answer it.
- `Simulator.begin_transmission()` marks a `PendingSend` committed when its
  TX request is processed, even if node busy time pushes the physical TX
  start into the future. Therefore a strict ACK-overhear feasibility screen
  may count only matching pending FLOOD handles that are neither committed
  nor canceled at actual decoded ACK reception. Counting all future-start
  transmissions as cancelable would overstate opportunity without a queue
  cancellation redesign.
- The existing `MeshEchoLPR.on_receive` in `lora_mesh_sim.py` already uses
  decoded successor DATA/ACK to cancel a pending `PATCH_RELAY` transmission
  before commitment. Therefore an ACK-overhear FLOOD-tail study must not
  claim the generic overhear-to-cancel idea as new even relative to this
  repository. Its narrower technical distinction is terminal destination
  receipt proof for queued ordinary useful-DATA FLOOD forwards, with the
  source/recovery decision still to be redesigned separately.
- Preliminary ACK-overhear replay on exploratory seed 22001 reproduced its
  baseline and reported 259 physical ACK-decode instances at matching
  uncommitted pending-F relays, with 151 distinct handles later transmitting
  after destination delivery (14.835 s TX ToA). The denominator's total
  post-delivery F relay airtime was 25.436 s on that seed. These are not
  realized savings, may include repeated ACK decodes per handle, and are
  not yet a three-seed validated result. Marker/epoch validation and F
  initial-versus-recovery strata are required before selecting a contract.
- The final passive forward-recovery diagnostic on fresh seeds 18001--18003
  exactly replays baseline flow timestamps/actions, application traces, and
  full TX hashes. It observed 107 scheduled flows, 28 admitted R timeouts
  with actual F rescue, 26 first destination deliveries by F, but only
  13/28 source ACKs. Eleven of the 26 F-first paths were longer than the
  source-known old route; no <=old-hop F decode was observed in those eleven
  under full flooding. This rejects `TTL = old hops` as a safe shortcut in
  the observed trace but is not a changed-TTL counterfactual.
- Recovery F caused 693 TX starts/67.690 s complete-network airtime. Of
  these, 362 relay TXs/35.528 s started after the flow's first destination
  delivery; a read-only split of the final JSON shows 310/30.456 s on the
  26 F-first flows and 52/5.072 s on the two initially R-delivered flows.
  This is potential tail exposure, not evidence that an ACK is overheard by
  a still-cancelable relay or that removing the tail preserves source ACK.

- The finalized 22001--22003 passive ACK-overhear screen exactly matched
  unchanged fixed-F baseline action, flow, and TX traces. It found 1,120
  distinct off-ACK-path, uncommitted pending-F handles physically reached by
  a matching destination ACK; 591 later transmitted for 57.915136 s of
  local TX airtime. This is an opportunity upper bound, not realized savings
  or a causal comparison. Its same-flow `request_id` is an alias of the
  already charged `flow_id`, not an additional paid on-wire field.
- A read-only source audit confirms that MeshEcho-SR currently chooses F/R/D
  through fixed miss counts, a 180-s route age, recent-send count, and a
  source token. The reusable simulator, packet accounting, RREQ/RREP, FLOOD,
  and ACK machinery are distinct from that decision algorithm. Current ICC
  LaTeX still evaluates calibrated max-min PRR; a new-method claim requires
  replacing the source policy and independently validating the resulting
  mechanism, not merely editing the manuscript or adding ACK cancellation.
- The added AFS fixed-F slice now cancels only off-path, physically decoded,
  matching destination ACKs while the relay FLOOD handle is uncommitted.
  `request_id == flow_id` is enforced as an alias, initial-F `None` and
  recovery-F `2` markers do not cross-cancel, and an identical no-cancel
  shadow arm preserves the old fixed-F trace in a three-node test. This is
  a tested local behavior, not a measured network-level gain or novelty.
- A source-core design audit proposed deadline-reserved R-then-F with
  ACK-confirmed paths, one contingent same-flow full F rescue, and AFS
  relay cancellation. It must be compared to same-admission fixed early
  and 15-s guards; otherwise a variable guard is only deadline-aware ARQ.
  `begin_transmission` commits a queued packet before its possible future
  physical start, so choosing the packet in `on_transmit` would be too late.
- The independent pre-population DRC exposure audit rejected that specific
  source design in the existing recurring-fading case. Its nominal recovery
  F bound is 9.328272 s and a maximum six-hop `B_R+B_F` is 11.375824 s,
  requiring >18.624 s queue delay for reservation to change the first
  action. None of 559 route-bearing initial actions in inspected fixed-F
  DHR development traces reached that window. The 185 actual R-to-F starts
  show recovery exposure, but `B_R` varies only 0.488 s over observed paths
  and a fixed 2.05-s guard gives the same historical ACK/no-ACK trigger
  classification. Closed-loop DRC could differ, but the distinctive branch
  lacks observed exposure; no 280xx/290xx seeds were opened.
- AFS packet admission must reject FLOOD `repair_index=1` even when a
  physically decoded ACK bears the same marker: DHR's only eligible F
  epochs are initial `None` and recovery `2`. A packet's `protocol` string
  is simulator metadata and cannot be an ACK match predicate. Both cases
  were exposed by failing public simulation tests and corrected without
  changing the ordinary same-protocol wire trace.
- In the already inspected DHR-none development arm, 510 initial confirmed-
  route R decisions across 20 seeds/80 pairs yielded 172 source-ACK misses
  and 150 destination non-deliveries. Prior R miss=1 was associated with
  61/102 ACK failures versus 111/408 with miss=0. One-hop cached routes had
  102/183 ACK failures versus 70/327 on two/three-hop routes; the excess
  persists within a simple ACK-age-or-miss stratification and in 17/20
  seeds. This is a selected, clustered, enqueue-time-proxy development
  association, not a validated predictor or proof that a hop-aware F action
  improves ACK/delivery/airtime. The report is
  `docs/research/meshecho_dhr_source_signal_screen.md`.

- Algorithm-boundary clarification: the current MeshEcho-SR source rule is
  still threshold-driven F/R/D selection; AFS only removes eligible queued
  FLOOD relay sends after a physically decoded matching destination ACK.
  Neither isolated cancellation nor descriptive one-hop ACK-failure
  association establishes a new end-to-end core. The existing simulator
  and matched experiment infrastructure remain reusable while a new source
  decision contract is developed and tested prospectively.
- AFS runner independent read-only audit: the saved `strict_pending` Boolean
  lacks local ACK/FLOOD/pending-handle snapshots needed to reconstruct its
  validity; recorded deadline booleans are not cross-checked with timestamps;
  and stored TX durations are not independently checked against PHY ToA.
  Its no-cancel arm does enforce matched flows/actions/metrics and normalized
  full-TX parity. These gaps must be closed before using the runner's gate.
- Exact source boundary: `MeshEchoSR.send_app` still uses miss counts,
  180-second age, recent sends, and discovery token to choose F/R/D;
  `MeshEchoDHR.expire_data_ack` waits for the 15-second guard and its adaptive
  arm uses a 120-second ACK-age split. `MeshEchoAFS` inherits DHR's fixed-F
  rescue mode and changes only relay cancellation after ACK overhearing.
  Thus AFS network results, even if positive, would not validate a revised
  source policy. The current ICC abstract explicitly acknowledges no clear
  route-score advantage over matched PRR-product and random-pair losses.
- Independent source-candidate screen: 150/510 initial R decisions in the
  old no-rescue cohort missed destination delivery, while 177/194 fixed-F
  R-timeout flows had not reached the destination before the guard. These
  are high-exposure *forward* failures, but a source ACK timeout alone does
  not reveal them. Earlier first-hop passive progress witness, ACK query,
  DRC timing reserve, DHR age/miss selection, BAR alternate ACK, and simple
  hop-risk ideas do not currently establish a differentiated controller.
  No demonstrated new source algorithm exists yet; further design requires
  a bounded locally observable progress signal and a falsifiable matched
  control, or a narrower paper claim.
- Independent runner review found the first repaired `validate_manifest`
  still admits serialized strict-pending witnesses with no actual prior
  FLOOD reception/enrollment. The synthetic passing-development test creates
  100 such events from one ACK and passes. Duplicate physical ACK decode
  rows for the same TX/receiver are not rejected and can inflate the count.
  Deterministic re-execution of each saved seed/arm and a unique-decode
  constraint are needed before using this runner as a provenance gate; the
  existing real runner tests exercise only two-node, non-canceling traces.
- An explicit source STATUS query would not resolve the main failure in the
  inspected BAR fixed-F cohort: only 17/194 R guards had an initial DATA
  destination receipt before the guard, so positive delivered-only status
  covers at most 2.2% of all 778 scheduled flows even with perfect response.
  At SF7/125 kHz/CR4/5, a source QUERY alone costs at least 0.051456 s per
  guard (>=9.982 s aggregate), with relay/reply costs and deadline delay
  extra. Missing response is still ambiguous. DSR RFC 4728 already specifies
  network ACK requests, so this is neither a high-exposure nor clearly novel
  core candidate. This is a feasibility calculation, not a trial result.
- The frozen AFS seed-23000 smoke mechanically matches no-cancel to
  unchanged fixed-F and passes artifact hash/replay checks. It observed
  353 actual off-path pending-F cancellations and -8.507136 s of complete-
  network TX airtime (52.8832 vs 61.390336 s), but source ACKs decreased
  from 29/39 to 26/39 with both arms at 38/39 destination delivery.
  This is one reserved *mechanical* seed, not a confidence interval; it
  warns that cancellation may harm ACK closure despite reducing DATA tails.
- The frozen 40-seed AFS development comparison did not satisfy its joint
  gate. AFS saved paired mean whole-network airtime of 19.53% (95% CI
  15.26--23.80% less), but its source ACK-PDR difference was -0.00143 with
  95% CI [-0.04257, +0.03971], missing the prespecified -0.02
  noninferiority lower bound. Destination-PDR difference passed its margin;
  9,728 strict cancellations spanned all 40 seeds. Pooled ACKs (1,156 vs
  1,147 of 1,623) are not the equal-seed paired estimand and cannot rescue
  the failed claim. All 120 arms were explicitly replayed and matched the
  saved evidence. Holdout 24001--24040 remains unopened.
- New-core research screen: the existing MAG candidate already carries a
  receiver-updated minimum forward SNR margin in DATA/FLOOD and returns it
  in ACK. Its revision-3 development result beats F/R-only on source ACK
  but fails the +10% airtime upper-bound gate and has no clear advantage
  over equal-token periodic D. A new source rule cannot merely repackage
  that one-byte forward-margin trigger. The ordinary reverse ACK stores
  its next intended path position in `Packet.path_index`; relays can locally
  infer how far an ACK progressed, but this field alone does not identify
  initial R DATA forward failure at the source.
- Matched fixed-R-repeat versus fixed-F-rescue DHR development histories
  contain 110 flows with both admitted guards; only 90 also have the same
  most recently committed path. An independent stricter join requiring
  matching guard time, path, latest route commit, and latest accepted source
  ACK leaves 77: R/F deadline source ACKs 13/30 and destination deliveries
  27/76. At the first recovery opportunity per seed, 20 cases had R/F
  source ACKs 3/8 and destination deliveries 7/20. These are descriptive
  cross-arm closed-loop contrasts, not per-flow causal counterfactuals;
  they do not identify a source-local state where R is reliably better.
- Existing passive first-hop evidence has little reach: only three
  unACKed multihop flows had a source-observed first-hop continuation, all
  still undelivered; a 30-second local-candidate history nominated no
  actually decoding backup among 22 failed first hops. Source ACK age and
  route-hop signals alone do not justify a new R-vs-F classifier.
- The prior fixed-F ACK-hop diagnostic found 37 emitted ACK attempts for
  35 delivered-but-unACKed flows, all ending at observed reverse-hop
  physical failure; 23 of 37 failed on the final hop into the source.
  This suggests a high-exposure reverse-confirmation branch to screen,
  but does not show that repeating a final-hop ACK would succeed or be
  novel relative to link-layer ARQ.
- Prior-art correction (2026-10-04): Meshtastic firmware already invokes
  `Router::cancelSending` after an overheard decodable ACK/reply for a
  direct message (`FloodingRouter.cpp` lines 160--168 at commit
  `d6b12ea3f1fc83afcff63a7fb511d54c52cc871a`). This is a close
  precedent for AFS's queued FLOOD cancellation; path/epoch conditions
  may differ, but ACK-terminated rebroadcast is not a standalone novelty
  claim. The firmware branch requires a decoded ACK/reply and does not
  establish behavior for opaque encrypted payloads. Source:
  https://github.com/meshtastic/firmware/blob/d6b12ea3f1fc83afcff63a7fb511d54c52cc871a/src/mesh/FloodingRouter.cpp#L160-L168
- Additional close controls for any redesigned core: MeshCore's documented
  known-route retry then last-retry flood, Meshtastic's route/flood fallback,
  AODV expanding-ring and local repair (RFC 3561), and DSR packet salvage
  and acknowledgments (RFC 4728). A general adaptive-retransmission or
  redundancy-learning claim is also constrained by ICCW 2013 DOI
  10.1109/ICCW.2013.6649259 and EAI 2018 DOI
  10.4108/eai.20-3-2018.154369. These references limit broad novelty
  language; they do not prove or disprove a precise new mechanism.
- Last-hop ACK repeat screen (2026-10-04): among the old fixed-F
  diagnostic's 37 failed ACK attempts, 23 first failed on the final hop,
  but seven of these paths were direct destination-to-source. Only 16
  failures on 16 flows had a source-adjacent relay that could locally
  repeat the ACK. This is *opportunity*, not expected benefit. The relay
  can identify its last-hop role from the on-wire ACK path/index but has
  no local evidence whether the source decoded its first transmission;
  without a charged source ACK_DONE, the second send is unconditional.
  Existing RAC/CLAR on-path ACK-repeat controls and relay-assisted ARQ
  limit novelty. One two-hop ACK costs 0.051456 s TX airtime at the
  diagnostic SF7 PHY before queue/interference effects. Do not promote
  this narrower repeat into the requested core rewrite. Evidence:
  `results/meshecho_flood_ack_hops_seed14001_14003_20261004.json`,
  `docs/research/meshecho_rac_dev_results.md`, and
  `docs/research/meshecho_clar_dev_results.md`.
- The DHR recurring-fading development action log contains 803 source
  decisions: 542 R, 190 F, and 71 D. Grouping by seed/source/destination
  yields 80 pair histories with six to 14 flows each. This gives a real
  per-pair feedback opportunity, but it does not show that any online
  source policy beats fixed-action or old SR controls. A candidate must
  optimize the observable source ACK outcome without using hidden
  destination delivery or full-network airtime as its *input*; those
  quantities remain evaluation metrics.
- A source-side online-control screen found 102 later R sends after exactly
  one prior R ACK miss; 61 of these later R sends missed source ACK. This
  is a device-visible risk stratum, but not evidence that F, repeated R,
  or D would improve those same flows. The 80 recurring pair histories
  have only six to 14 flows each, making a generic per-pair three-arm
  bandit underexposed. Current Smart-CALM firmware already contains online
  action selection. A fixed-prior-one-miss branch comparison on fresh
  exploratory seeds is required before freezing an adaptive controller.
- Route-anchored fast-primary/slow-backup FLOOD is not a clear new core:
  SOAR (IEEE TMC 2009, DOI 10.1109/TMC.2009.82) and PRIOR (IEICE 2017,
  DOI 10.1587/transcom.2016cqp0008) already describe prioritized
  timer-based opportunistic forwarding and duplicate reduction; PRIOR's
  abstract also describes an explicit-ACK variant. Meshtastic firmware
  supplies the close destination ACK queue-cancellation precedent above.
  These abstract-level sources do not prove an identical combined protocol,
  but any claim must isolate a narrow contract and beat full F+AFS,
  path-delay/no-cancel, and R-then-F controls. The candidate is not frozen.

- Core-rewrite boundary (2026-10-04): the existing SR source policy is a
  fixed R/F/D state machine keyed by confirmed route, consecutive R misses,
  age, and discovery tokens; DHR adds an ACK-guard same-flow rescue. AFS is
  relay-tail cancellation and failed its ACK noninferiority gate. Improving
  ICC method novelty therefore requires replacing the source decision and
  recovery core with a device-observable rule, not merely changing a miss
  threshold. Keep Simulator/PHY/packet accounting and old SR/DHR as matched
  infrastructure and controls. The four-arm source-branch diagnostic is
  hypothesis selection only, not a new algorithm or acceptance estimate.
- Independent post-implementation review found no blocker for mechanical
  seed 34000. The diagnostic now persists each full scheduled application
  trace, pins source hashes before the first replay, checks for drift after
  every seed and before artifact writing, and distinguishes booked future
  TX from starts within the 630-s run. A future algorithm must still beat
  fixed one-miss F, R-F, R-R, old SR, and product-inspired baselines under
  source-ACK/destination/whole-network cost accounting; otherwise reject
  this direction. The alternate relay-progress/local-repair direction is
  close to existing LPR/SOAR/PRIOR/DSR precedents and remains secondary.
- Mechanical smoke 34000 produced 40 scheduled applications, six
  source-visible eligible targets (three one-hop, three three-hop), and
  exactly 24 target-only branch rows. All pre-app prefixes matched;
  source/data action, initial physical TX kind, guard/rescue starts,
  deadline outcome, and airtime ordering passed local consistency checks.
  Artifact and frozen source hashes match the manifest. Descriptive
  *one-seed* counts: R ACK/delivery 4/6 and 4/6; F 2/6 and 6/6; R-F
  5/6 and 6/6; R-R 5/6 and 5/6. Only two targets actually started a
  rescue in R-F/R-R. These are smoke diagnostics, not a population effect
  or a basis to freeze an algorithm. Independent artifact review remains
  pending before exploratory seeds are opened.
- The once-only predeclared 34001--34005 exploratory branch diagnostic
  completed under the same six frozen source hashes. It observed 29
  eligible source states and 116 branch rows. Direct byte SHA-256 matches
  the manifest for saved trace, targets, and branches. Descriptive totals
  across target branches: R had 13/29 source ACK and 15/29 destination
  deliveries; F 14/29 ACK and 29/29 deliveries; R-F 15/29 ACK and 29/29
  deliveries; R-R 16/29 ACK and 18/29 deliveries. Mean whole-network
  target-window airtime was respectively 1.676, 3.472, 2.910, and
  1.776 s. Sixteen of 29 R-F/R-R target guards produced actual rescues.
  These are targeted exploratory potential outcomes, not independent
  population claims or an algorithm.
- A device-visible route-hop stratification in these five exploratory
  seeds is suggestive but unvalidated: among 13 one-hop confirmed routes
  after one prior R ACK miss, R delivered 3, F 13, R-F 13, R-R 4; among
  11 three-hop routes, R delivered 9, F/R-F 11, R-R 10. The one-hop
  stratum appears in all five seeds, but thresholds or policies fitted
  from these small data would require wholly new prospective validation.
  F and R-F also differ sharply in source ACK versus delivery, so a
  destination-only objective would misstate the problem. Independent
  artifact and interpretation audits have since passed. The one-hop F
  median delivery time was about 0.93 s versus R-F's 15.67 s; this is a
  useful latency hypothesis but only a simple hop-based control, not a
  defensible novel core. The F-vs-R ACK losses in this small set all
  occurred on three-hop routes. Route age did not separate actions clearly.
  Fixed F and R-F both delivered 29/29 yet produced only 14 and 15
  deadline source ACKs, so the new-core design must address reverse
  confirmation as well as forward repair. Past BAR/CLAR results show that
  naive same-path ACK repetition is a strong comparator, not itself a
  novel solution.
- Independent exploratory artifact audit verified the six frozen live/
  manifest hashes, three artifact hashes, all five canonical trace hashes,
  29 canonical target prefix hashes, exact seed/arm completeness,
  eligibility, action bookkeeping, physical starts, guard/rescue parity,
  deadline flags, and cost identities. No blocker was found. Limitation:
  the branch artifact does not preserve full post-target packet-level TX
  histories, so exact network-airtime and collision totals need a frozen
  deterministic replay to be independently recomputed. Neither smoke nor
  exploration supports a population effect, final algorithm, hardware
  claim, or ICC acceptance estimate.
- Two independent post-analysis design screens found no validated new
  forward-plus-reverse core. The strongest observability obstacle is that
  an absent source ACK conflates forward loss and reverse-confirmation
  loss; in the previous no-rescue DHR arm, 150 of 172 initial-R ACK misses
  were actual forward non-deliveries. A hop-conditioned action is a strong
  *simple baseline* but not novel alone. BAR showed alternate-path ACK had
  essentially no resolved advantage over same-trigger same-path repetition.
  A source STATUS flood with relay-cached repair is device-observable in
  principle, but without extra signaling relays cannot suppress duplicate
  repairs or know whether the destination already received DATA; with
  signaling it may violate the 30-s/airtime budget and overlaps DSR
  salvage/ExOR-style mechanisms. Do not promote it without a separate
  pre-code feasibility gate and prior-art distinction.
- Joint-core quick-brief scoping (2026-10-04): the local DHR signal screen
  identifies 150 forward non-deliveries among 172 initial-R source-ACK
  misses; a source-only ACK timeout cannot classify the two failure modes.
  The prior fixed-F arm delivered 799/803 but obtained 570/803 source
  ACKs; duplicate FLOOD arrivals currently return before another ACK is
  sent. Existing verified close literature includes AODV/DSR local repair,
  relay ARQ, opportunistic LoRa forwarding, and flooding with ACK copies;
  the earlier brief is `meshecho_same_flow_recovery_prior_art_brief.md`.
  A broad Crossref query for forward/reverse ACK ambiguity was too noisy
  (including unrelated TCP/Bayesian results), so mechanism-specific source
  verification is needed before any novelty claim.
- A separate already-opened flood ACK-hop diagnostic (`14001--14003`)
  observed 35 delivered-but-unACKed flows and 37 emitted ACK attempts,
  all first failing at a physical reverse hop (23 at the final hop into
  the source). Its saved per-hop records report decode success/failure,
  not whether a failure was due to half-duplex, capture collision, or
  probabilistic channel decoding. Thus the present evidence cannot say
  whether an ACK-protected quiet interval would address the failures;
  it remains a conditional hypothesis, not a mechanism to implement.
- Predeclared a read-only ACK physical-failure cause diagnostic in
  `meshecho_ack_failure_cause_diagnostic_design.md` for new 37000 smoke
  and 37001--37003 exploration; no seed has run. It distinguishes
  half-duplex, capture collision, and probabilistic decode failure with
  or without weaker interference. The strict optimistic `ACK_INTENT`
  opportunity requires an 11-byte intent to complete before a sole
  same-flow post-delivery FLOOD interferer is committed. Current SF7
  `RadioConfig.toa_s_for_bytes(11)` returns 0.041216 s; queueing and
  decoding make any real benefit less optimistic. This is an upper-bound
  exposure gate, not a proposed full core.
- Crossref independently verifies Suzuki et al.'s 2013 VTC paper as
  DOI `10.1109/VTCSpring.2013.6692624`, but Crossref did not return an
  abstract, so no method detail is attributed from that record alone.
  Crossref verifies Lee et al., *Wireless Communications and Mobile
  Computing* (2020), DOI `10.1155/2020/8839541`; its abstract explicitly
  states flooding transports both DATA and ACK on multiple routes and
  dynamically adjusts ACK-copy waiting time by path similarity. This
  blocks a broad claim that timed/multipath ACK handling is new.
- Additional broad Crossref/OpenAlex title/text queries for ACK-priority
  flooding returned mostly unrelated WSN surveys, localization, and
  generic flooding papers. Absence of a direct hit is **not** novelty
  clearance. Mechanism-specific verified DOI/abstract and, where
  available, full-text comparison remain necessary.
- Targeted peer-reviewed prior-art check (2026-10-04): Lee et al. 2020
  (DOI `10.1155/2020/8839541`) explicitly discuss multipath DATA/ACK and
  ACK-copy waiting; Suzuki et al. 2013 Choco (DOI
  `10.1109/VTCSpring.2013.6692624`) schedule reliable Glossy collection;
  JMAC (DOI `10.3390/s20236893`, full text PMC7730183) sends a hop ACK
  immediately after `UP_DATA` yet reports gateway ACK interference without
  a dedicated receive window. Berto et al. 2021 (DOI
  `10.3390/s21134314`) identify expensive retransmissions after missing
  payload or ACK. DFOR (DOI `10.1109/LCOMM.2012.022112.120203`), SOAR
  (DOI `10.1109/TMC.2009.82`), LoRa opportunistic routing (DOI
  `10.1109/WoWMoM57956.2023.00065`), and LoRa flooding (DOI
  `10.1109/ITNAC62915.2024.10815298`) constrain broad novelty claims.
  These sources do not establish an identical device-local ACK-intent plus
  pending-F cancellation rule. A targeted search found no identical
  peer-reviewed method; that is not proof of novelty. No ACK-timeout-only
  policy can infer which direction lost the packet.
- The current five-page ICC source still presents the optional calibrated
  MeshEcho route scorer and explicitly reports no clear source-ACK advantage
  over a matched PRR-product scorer. It does not present MeshEcho-SR/DHR as
  its tested core. A successful new protocol would require replacement of
  the paper's method, evidence, figures, and conclusion, not a paragraph
  added to the current calibrated-route manuscript.
- Independent pre-code ACK_INTENT screen (2026-10-04) is a conditional
  **no-go as the full new core**. A valid implementation would need a
  physically decoded, explicitly encoded same-flow/epoch 11-byte intent
  before the ordinary ACK, with only an uncommitted matching relay send
  eligible for a bounded quiet/cancel action. Its SF7 TX ToA is 0.041216 s
  per transmission, before any relay/signaling overhead. Single-hop
  reachability, half-duplex reception, and commitment timing are not
  established by the optimistic offline exposure test. Destination DATA
  receipt does not prove source ACK receipt; early tail cancellation might
  remove useful reverse diversity. AFS already saved airtime but failed
  its source-ACK noninferiority gate. Even a positive 37xxx exposure screen
  would justify only a controlled prototype, not a complete source-policy
  rewrite or paper claim. Controls must include R-F, AFS, fixed F delay,
  equal-airtime same-path ACK, intent-cost shadow, and quiet/cancel ablations.
- Independent ACK-cause tool audit found that deadline-delivered flows may
  have emitted reverse ACK attempts after their 30-s application deadline.
  Counting a post-deadline first failed ACK hop as an intent-protectable
  opportunity would inflate the necessary exposure gate. The gate must
  require the actual failed hop to complete no later than the flow deadline.
  This finding is being fixed test-first before seed 37000.
- Frozen seed-37000 ACK-cause smoke passed exact baseline and plain/observed
  TX parity. The report's 648 compact TX rows independently reproduce all
  12 failed-hop overlap sets; its SHA-256 `ced7185f00dce7bab73db8d76f6fabbe5aa727285556a2e8eafe23e4a0afd5ed`
  matches the manifest. Of ten deadline-delivered but unACKed flows, nine
  ACK attempts first failed by capture and three by clean-channel
  probabilistic decode. One unique flow had a sole post-delivery same-flow
  FLOOD overlap, but that FLOOD committed before the optimistic 11-byte
  intent could have completed; strict opportunity was 0/10. This is a
  single mechanical seed, not an exposure estimate or algorithm result.
- Frozen 37001--37003 exploration passed independent audit: 2018 complete
  TX rows and 27 first failed ACK hops recomputed with zero overlap/cause/
  timing discrepancies; all three seeds have exact source-action, flow,
  trace, and complete-TX parity. Report SHA-256 is
  `49d8ffecd7bb3e0ff10550eb175be6b8d689ba2b30029c8e53400937ef4a8ca7`.
  Among 24 deadline-delivered/unACKed flows, there were 17 capture, one
  half-duplex, and nine no-interference probabilistic first failures
  across 27 ACK attempts. Broad sole same-flow FLOOD overlap and strict
  intent-timing eligibility each occurred on one unique flow. The strict
  1/24 (4.17%) fails both preregistered >=4-flow and >=10% gates. Reject
  this post-delivery ACK_INTENT/quiet/cancel branch as a new core. All 17
  capture failures overlapped same-flow FLOODs, but most were already in
  flight before delivery or involved multiple interferers; this leaves
  other proactive designs as untested hypotheses, not rescued claims.
- Current continuation cross-check: frozen BAR development had an
  alternate-path extra-ACK ACK-PDR gain of +0.1513 [0.1048, 0.1978]
  against fixed F, but only +0.0021 [-0.0292, +0.0334] against its
  same-trigger same-path second-ACK control. Thus time diversity/one
  extra ACK is a strong simple comparator; a joint controller cannot
  claim originality or causal benefit from its ACK component alone.
  The ICC revision map confirms the current five-page manuscript is
  version 2.1.26 calibrated-route work and requires replacement of
  title/abstract, method, baselines, numerical tables/figure, limits,
  and reproducibility text only after a new core is validated.
- Source-code mechanism boundary rechecked: `CalmMesh.on_fallback` enqueues
  a delayed relay FLOOD as soon as a relay first physically decodes one,
  while destination receipt calls `send_ack_on_reverse_path` immediately.
  Thus the return ACK can overlap FLOOD transmissions that were already
  locally scheduled before destination delivery. A post-delivery signal
  cannot retroactively cancel `PendingSend.committed`; a prospective rule
  must act from relay-local precommit state or predeclared packet timing,
  with any extra wire fields and waiting airtime/deadline effects charged.
- Independent source-core screen found no defensible full replacement from
  the current local signals: source 15-s no-ACK is observationally identical
  for forward DATA failure and reverse ACK failure; 34001--34005 targeted
  F/R-F arms each delivered 29/29 but received only 14/29 and 15/29
  source ACKs. A fixed R-F + BAR same-path extra ACK + AFS stack is
  testable engineering, not a new source decision rule. BAR's extra ACK
  needs a later duplicate F receipt; AFS may suppress that duplicate.
  The separate BAR and AFS development effects must not be added as a
  combined-arm prediction. A same-seed BAR(on/off) x AFS(on/off) factorial
  would be necessary to measure interaction but insufficient alone for a
  new source-core claim. An actually source-decoded destination-delivery
  certificate is the minimum extra signal to disambiguate its two
  no-ACK worlds; the prior CLAR ACK_DONE signal already failed versus
  simple same-path ACK repetition.
- Targeted peer-reviewed source check for proactive slots: DG-LoRa by
  Junhee Lee et al. (Sensors 2021, DOI `10.3390/s21041444`) explicitly
  uses a time-synchronized frame structure with deterministic group ACK
  timeslots in LoRaWAN, so ACK-slot allocation is not broadly new. The
  ICRAMET 2025 paper *Multi-copy, Spatially-Confined Broadcast Routing to
  Support Message Delivery with Handshaking in Multi-hop LoRa Network*
  (DOI `10.1109/icramet67419.2025.11350147`; Crossref metadata and
  OpenAlex abstract verified) reports local slotted Aloha, sender-aware
  forwarding, handshaking, and LoRa mesh prototypes. Its abstract does
  not prove an identical MeshEcho rule, but it directly constrains a
  broad multi-copy/slotted/handshake novelty claim and raises the bar for
  simulation-only evidence. Smart-Hop (DCOSS 2022, DOI
  `10.1109/dcoss54816.2022.00014`) is verified as a multi-hop LoRa MAC
  using spreading-factor diversity, not evidence of the exact ACK slot.
- A source policy based only on returned minimum forward SNR is not a
  fresh core: MAG already charged the on-wire min-margin bytes and, in
  its revision-3 development, gained +0.1556 ACK PDR versus F/R-only but
  failed its +10% airtime upper-bound gate (95% upper bound +12.8%) and
  showed no clear ACK gain over equal-token periodic discovery. The repo's
  Smart-CALM already uses tabular Q-learning; a generic contextual
  bandit/profile selector would need a substantive new local signal and
  robust evidence, not merely renamed online learning.
- Independent pre-delivery ACK-slot screen on the frozen 37001--37003
  report: the 17 capture-failed ACK attempts are 17 distinct flows with
  72 overlapping same-flow FLOOD TXs, of which 50 cross the configured
  capture threshold. Relative to each ACK-triggering destination receipt,
  two attempts had only pre-trigger overlaps, 13 mixed pre/post, and two
  post-trigger only. Only one capture has every threshold-breaking FLOOD
  still uncommitted after a hypothetical post-trigger 41.216-ms intent;
  it would require two separate relay receptions. The earlier 1/24 strict
  record used a first DATA delivery 15.8 s before its later recovery-F
  ACK, overstating that intent's causal timing. An in-sample source-F-
  relative 1.3-s ACK slot would follow the observed successful trigger
  transmissions but was fitted post hoc; a conservative no-queue six-hop
  bound is about 9.38 s plus unknown queueing. This does not establish a
  locally safe, novel, low-latency predeclared slot. Fixed ACK delay and
  same-path ACK repetition remain mandatory comparators.
- Read-only short-ACK corridor screen (2026-10-04): in the opened 37xxx
  trajectories, 21 F-first delivered/unACKed flows remained; a fixed 2-s
  destination ACK deferral would follow the final same-flow FLOOD TX in
  18/21, and all tails ended by about 2.763 s. This is only timing exposure,
  not a closed-loop success or savings estimate. The traces lack physical
  relay FLOOD reception history, so no device-local reverse-corridor DAG or
  realizable cost can be reconstructed. A full-path ACK costs 51.456--
  61.696 ms per SF7 TX (up to 66.816 ms with the recovery marker); a
  pathless 10--11-byte ACK costs 41.216 ms but loses source route commit.
  A 50-node unrestricted ACK flood can cost much more than two same-path
  ACKs. The candidate remains no-go for implementation without prospective
  passive exposure and matched fixed-delay/equal-airtime controls. Lee et
  al. 2020 (DOI `10.1155/2020/8839541`) directly constrains broad
  novelty claims for multipath DATA/ACK and ACK waiting.
- Independent source-policy indistinguishability check (2026-10-04): with
  the current on-wire packets, one-hop execution A can lose DATA at the
  destination and execution B can deliver DATA but lose its reverse ACK.
  The source has identical DATA send, queue, timer, and no-ACK history in
  both through its 15-s guard, so any source-only decision function must
  choose the same action. First-hop continuation overhearing does not
  certify end-to-end delivery. A new source-side failure classifier requires
  an additional source-decoded destination certificate (functionally a
  second ACK), which must beat a same-time, equal-airtime same-path ACK
  repeat. Existing CLAR/BAR candidate controls did not establish that.
- Independent corridor-design audit invalidated the draft immediate-ACK
  passive no-go gate before any 38xxx run: removing the original immediate
  ACK by waiting 2 s changes half-duplex/interference and thus the very
  FLOOD reception set the diagnostic would inspect. A missing alternative
  in unchanged fixed-F is not a necessary impossibility under delayed ACK.
  Also, an extra 0.1-s/hop plus 1-s guard and a completed FLOOD tail are
  not physical necessities; the minimum-cost cross-node path union is an
  offline oracle. Marked that draft superseded and froze a simpler fixed-
  2-s delayed single-ACK control as the next prospective comparison.
- Control audit found `DHR_FAMILY_PROTOCOLS` omitted the new delayed arm;
  generic ACK airtime was charged, but DHR-specific initial/recovery ACK
  counts would have been zero. A public accounting test failed before the
  classification fix and now passes. `Simulator.run(630)` also discarded
  its first post-cutoff event, hiding a delayed ACK; a real-flow test failed
  before preserving that heap event and now passes for `run(630)` followed
  by `run(660)`. The exploratory runner still uses an independent fresh
  660-s replay for cost sensitivity, since continuing the same simulator
  is weaker evidence of deterministic reproduction.
- Independent paired-runner audit (before 38000) found two provenance
  defects despite 590 passing full tests: primary cost-window limitation
  was inferred from the 630-s run's own future-start TXs rather than the
  fresh 660-s replay, missing post-cutoff events that had not yet been
  scheduled; and manifest validation only linked first-FLOOD receipts to
  a physical TX, not to a matching destination receive action or the
  saved per-flow ACK timing. These defects can let the summary look
  stronger than the saved evidence. Smoke remains closed until new
  adversarial tests and exact reconstruction pass. The 660-s window is
  always a bounded sensitivity, not proof of all eventual airtime.
- The runner defects above were repaired and independently re-audited before
  the 38000 smoke. Strict deterministic replay now compares saved metrics,
  actions, physical TX, receipts, and flows; the first-FLOOD receipt is tied
  to a unique destination action and actual ACK timing. The frozen 38000
  smoke passed that replay and matched the stock immediate fixed-F arm.
  Its 34/36 versus 29/36 ACKs and 43.099136 versus 50.773248 s airtime
  are one-seed mechanical observations, not an efficacy estimate. A 2-s
  fixed ACK delay remains a simple control, not a new MeshEcho core.
- The frozen 38001--38020 fixed-delay ACK exploration passed independent
  artifact/source hash audit and strict replay on all 40 runs. Against
  immediate fixed-F, 2-s delay raised paired deadline source-ACK PDR by
  0.2251 [95% CI 0.1725, 0.2777], reduced per-seed relative complete-
  network TX airtime by 16.73% [11.22%, 22.24%], and had unresolved
  destination PDR difference 0.0024 [-0.0040, 0.0087]. It is a selected
  exploratory timing baseline, not proof of a novel algorithm, general
  optimum, hardware performance, or an ICC acceptance probability. The
  delayed arm had 251 versus 380 first-FLOOD receipts, showing the timing
  change altered subsequent network trajectories; old-arm ACK failures
  cannot be counted as directly rescued packets. Full report is in
  `docs/research/meshecho_delayed_ack_control_explore_results.md`.
- Independent source-core design audit after the delay-control result found
  no ready-to-freeze source mechanism. Source-local missing ACK at 15 s has
  identical histories under forward DATA loss and reverse ACK loss. A
  hop/miss/age selector or one-shot F rescue is implementable with existing
  bytes but overlaps ordinary ARQ/route repair and has not beaten fixed F,
  R-F, or other simple controls. A destination-local quiet-window ACK
  schedule could be investigated only if decoded duplicate FLOODs offer
  sufficient local exposure; by itself it is still not a source-core
  rewrite and must beat fixed 2 s and equal-airtime ACK repetition. A
  STATUS query adds bytes and leaves silence ambiguous. Do not code any of
  these as a claimed new algorithm from present evidence.
- A read-only join of the already saved delayed-arm 38001--38020 receipts
  and destination action log found 235/251 first-FLOOD deliveries with at
  least one further locally decoded copy within 2 s, across all 20 seeds.
  The last-decode-to-fixed-ACK quiet gap was >=0.5 s for 180/251; 47/251
  still had a later successful decode after the 2-s ACK started. This is
  enough observable variation to draft a falsifiable local timing
  component, not to claim a causal improvement or finished FLOOD wave.
  `Packet.created_at` is not on wire, and the existing DHR rescue-round-
  trip admission bound omits ACK holding time. Full evidence and scope are
  in `docs/research/meshecho_local_ack_quiescence_exposure.md`.
- A targeted AI-assisted prior-art quick screen checked seven DOI-bearing
  studies, five against accessible original text. LoRa preset delayed ACK,
  flooding ACK-copy waiting, synchronized group ACK slots, multihop hop
  ACKs, and reliable LoRa mesh all have direct precedents. No checked source
  exactly matched destination-local successful-FLOOD-decode quiet gating
  of one reverse ACK, but Lee 2020 and Solé 2026 full texts were not
  accessible and a limited search cannot establish originality. The narrow
  comparison boundary, source links, and caveats are in
  `docs/research/meshecho_ack_timing_prior_art_quick_brief.md`.
- Independent quiet-window design and adversarial audits reject it as a
  standalone core rewrite. Among 42 residual source-ACK misses following
  a first FLOOD receipt with fixed-2-s ACK, 14 had a later destination-
  decoded same-flow FLOOD and 9 had a same-flow FLOOD TX overlapping the
  destination ACK (intersection 3). These observations neither prove
  failure cause nor cover reverse-path later collisions. A timer would not
  change the source F/R/D decision or separate forward DATA loss from
  reverse ACK loss; it must not be promoted as an ICC contribution alone.
- Current ICC LaTeX still evaluates the optional calibrated MeshEcho route
  score, not SR/DHR. In the simulator, `MeshEchoSR.send_app` chooses F/R/D
  from confirmed route, recent misses and aging; `expire_data_ack` labels
  a missing source ACK after 15 s. `MeshEchoDHR` later adds same-flow
  R/F recovery, and `MeshEchoDHRDelayedAck` changes only the destination
  FLOOD ACK delay. A publishable SR-core replacement would need a joint
  feedback/recovery policy and entirely new matched manuscript results;
  retaining simulator PHY/events, packets, metrics and old policies as
  comparators is different from retaining the old algorithm.
- A read-only 38xxx residual audit found 42 delivered-but-unACKed FLOOD
  cases with on-time destination ACKs, of which 37 reached a final reverse
  TX toward the source; 25 had some TX overlap and 17 did not. The logs do
  not classify physical reception loss or counterfactual path reliability.
  Forty had destination-decoded alternative FLOOD paths within 2 s, but
  79/89 alternatives were longer than the first path. This supplies a
  destination-local path-choice hypothesis, not a proven ACK repair or a
  source decision rule. See
  `docs/research/meshecho_fixed_delay_ack_residual_screen.md`.
- Current reverse ACK delivery is strictly path-indexed: the destination
  echoes the first accepted FLOOD copy's realized path, each relay
  decrements `path_index`, and an ACK receiver off that expected index
  neither accepts nor forwards it. Later duplicate FLOOD decodes return
  before a second ACK in the base path. The recurring-fading model uses
  deterministic link fading blocks (default 60 s) plus a stochastic RX
  draw, so short same-path ACK repeats can gain a new receive draw but
  cannot be assumed to escape a persistently weak link. Any new reverse
  mechanism must compare against same-time/same-budget repetition and
  charge all additional wire bytes and TXs.
- A direct `jq` grouping of the 42 fixed-delay, delivered-but-unACKed
  FLOOD cases by `first_flood_repair_index` gives 12 initial-F and 30
  R-to-F recovery cases. This makes the inherited 15-s source guard a
  concrete deadline-budget issue for any further feedback repair; it does
  not show that an earlier guard is causally better. A new full-core trial
  should separate initial-F and recovery-F estimands and recheck physical
  TX-start slack against the original 30-s deadline.
- A new, untested per-hop reverse ACK transmit-power hypothesis is feasible
  to screen in this model because each successful forward receive exposes
  local `RxInfo.snr_db`; path loss, shadowing and 60-s temporal fading are
  symmetric by unordered link. The current `RadioConfig.tx_power_dbm` is
  global (17 dBm in `recurring_fading`), `try_receive` applies that same
  power to desired and interfering transmissions, and TX electrical energy
  uses one fixed 120-mA current. A valid per-packet-power experiment must
  change desired/interference power and use a stated power-dependent energy
  model or explicitly avoid electrical-energy claims. Compare adaptive
  ACK power with uniform high-power ACK under the same PHY/cost budget;
  broad LoRa ADR/TPC novelty cannot be assumed.
- Continuation code check: `Packet.created_at` and `protocol` are simulator
  metadata, not wire bytes. `PendingSend.can_start_at` is evaluated against
  the actual queue-adjusted physical TX start, which makes it the correct
  admission point for a 30-s deadline rule. ACK route choice must remain
  packet-visible (`path`, `path_index`) and its physical TX/airtime must be
  charged by `Simulator.begin_transmission`; a timer firing before 30 s is
  insufficient if radio queueing pushes its actual start past the deadline.
- JFC design risk: the existing MeshEcho-BAR prototype already transmits an
  extra ACK on a destination-decoded alternate FLOOD path. On frozen 16001--
  16020 development, its advantage over the same-trigger same-path extra
  ACK was only +0.0021 source-ACK PDR (95% CI -0.0292 to +0.0334) with
  +2.3% relative whole-network airtime (CI -4.7% to +9.4%); the joint
  preregistered gate failed. Adding the proven simple fixed-2-s delay does
  not by itself make path diversity a new core. Any joint successor must
  isolate a source-policy contribution and beat the delayed single-ACK
  and equal-budget repeat controls on new paired seeds.
- Read-only `jq` aggregation of the already opened fixed-2-s delayed arm
  (38001--38020) gives 781 flows: 615 initial R (580 deadline ACKs, 612
  destination deliveries, 32 delivered-but-unACKed), 94 initial F (80
  ACKs, 92 deliveries, 12 delivered-but-unACKed), and 72 D-candidate
  sends (66 ACKs/deliveries, zero delivered-but-unACKed). These are
  within-arm descriptive strata, not counterfactual action comparisons.
  They show that a new core cannot focus only on cold-start F/R selection;
  R recovery and reverse confirmation dominate the remaining misses.
- On that same already opened delayed arm, the action log contains 164
  admitted R-to-F guard decisions and 164 matching recovery-F physical
  starts; 129 recovery-index-2 ACK callbacks were accepted at the source.
  The other accepted ACK callbacks (597 with null repair marker) include
  initial F/R/D outcomes. This is strong exposure for a source/recovery
  redesign, but not evidence that an earlier F decision or a different
  guard would improve the net reliability-airtime trade-off. Compare
  complete flows and whole-network cost under paired policies.
- Destination-side admission cannot use the source's original application
  deadline without adding and charging an on-wire age/deadline field.
  `Packet.created_at` is simulator-only, and ACK `created_at` is assigned
  locally at the destination. The fixed-delay one-repeat comparator now
  specifies a destination-local first-decode+10-s physical-start window;
  source deadline acceptance remains unchanged and late repeat airtime
  stays charged. This distinction applies to any proposed adaptive ACK
  scheduling as well as the simple control.
- Earlier DHR development (9001--9020) compared adaptive R/F rescue under
  immediate ACK timing and failed its joint gate: fixed F delivered 799/803
  packets but source-confirmed only 570/803, while adaptive DHR obtained
  578/803 ACKs with less airtime. The newer fixed-2-s ACK policy changes
  closed-loop trajectories and raises source confirmation, so the old DHR
  action rankings cannot be transferred to a new source controller. Any
  source rewrite must be evaluated anew atop the same fixed-delay ACK
  contract as its strongest simple comparator.
- Source-timing audit on the opened fixed-delay arm found 164 R-to-F starts,
  143/615 initial-R flows first delivered via recovery F, and 129 accepted
  recovery-F ACKs. Among 580 ACKed initial-R flows, 449 ACKed within 1 s
  of enqueue, two further apparent 1--15-s outliers had DATA physical
  starts only after ~13.305 s of source queueing and returned R ACKs
  ~0.30/~0.15 s after actual start; the remaining 129 ACKs came from
  recovery F. Thus an enqueue-anchored ACK-delay learner would mistake
  source queue time for reverse-path delay. A simple fixed 2/4-s guard
  from physical R TX start is a mandatory comparator before any adaptive
  ACK-hazard or belief controller; these within-arm timing counts do not
  prove its counterfactual performance.

## 2026-10-04 - Passive ACK Reception Result

- Frozen 39001--39020 recurring-fading diagnostic, independently audited
  against stock parity and strict replay of all 20 seeds: 816 scheduled
  flows, 810 deadline destination deliveries, 763 deadline source ACKs.
  Forty-seven deadline-delivered, source-unACKed flows had a FLOOD ACK
  attempt. Only one (seed 39007, flow 18, R-to-F recovery) had an
  identity-valid, in-deadline ACK physically decoded by the source at an
  earlier path index. Exposure is 1/47=2.13%, failing both predeclared
  necessary gates of at least four distinct flows and at least 10%.
  Merely allowing off-index ACK acceptance cannot be the new core.
- Of those 47 failed source confirmations, first reverse-hop failure was
  classified as capture collision for 23, half-duplex for two, and a
  probabilistic PHY miss without overlapping interference for 22. Thirty-
  six had a final reverse ACK TX toward the source by the original flow
  deadline. These are observations in the simplified radio model, not
  counterfactual success estimates or measured hardware failure rates.
  The saved path-category field counts ACK attempts; each failed flow in
  this cohort has one attempt, so its 25 direct/22 multihop totals also
  happen to equal distinct-flow counts.
- An independent per-hop re-audit split the 47 failed ACKs into 36 whose
  first failed reverse hop ended at the source and 11 at a relay. At the
  source these were 21 no-interference probabilistic misses and 15 capture
  failures; relay failures were eight capture, two half-duplex, and one
  probabilistic miss. The 22 no-interference failed-hop model PRRs ranged
  from 0.04 to 0.981. A universal source timeout cannot infer either a
  physical failure cause or link quality from ACK silence.
- One unvalidated successor hypothesis is to carry a charged, relay-
  measured first forward-edge SNR margin with FLOOD. A destination would
  compare only paths it actually decoded within the existing 2-s window,
  and any source route transition would depend only on a genuinely decoded
  ACK and its own clock/state. A *passive*, behavior-preserving prospective
  screen should first ask whether at least eight distinct source-final-hop
  ACK failures and at least 20% of that stratum have a timely decoded
  alternate first-relay path with >=3-dB better measured first-edge margin
  and <=1.5x nominal ACK airtime. This is a necessary exposure threshold,
  not proof of counterfactual ACK success, novelty, or a complete core.
  BAR's near-zero advantage over a same-trigger same-path ACK repeat makes
  this branch high-risk; measure the repeat and short-guard controls first.

## 2026-10-04 - Close-Prior-Art Verification Update

- Lee et al. (2020), DOI `10.1155/2020/8839541`, is verified by Crossref
  and Semantic Scholar metadata/abstract. The abstract says DATA and ACK
  flood over multiple paths, and ACK-copy waiting time changes with the
  paths' similarity to reduce spurious retransmission. Publisher full text
  and XML were not accessible in this check. The waiting node, formula,
  and complete recovery state machine remain unverified; do not assert
  that Lee lacks destination ACK path selection or local copy handling.
- Solé et al. (2026), DOI `10.1016/j.comcom.2025.108404`, has an openly
  accessible CC BY [UPC full text](https://upcommons.upc.edu/bitstreams/55c698b0-c18a-4d2a-b202-0a08bdfe2d27/download). Sections 2.1 and
  2.5--2.6 and Figures 5--6 describe proactive LoRaMesher NextHop
  routing, per-chunk end-to-end stop-and-wait ACK, source SYNC retransmit
  after missing ACK, and receiver LOST_P/NAK plus repeats for missing
  chunks. Its RTT-based timeout uses a 20-s experimental minimum and
  default `MAX_TIMEOUTS=10`. The paper does not describe collecting
  same-FLOOD alternate paths for ACK1/conditional ACK2 selection, but
  exact ACK-return routing and duplicate-DATA ACK behavior are not fully
  specified; absence from the implementation is not established.
- Thus delayed ACK, end-to-end LoRa ACK, timeout retransmission, ACK-copy
  waiting, and multipath ACK are not broad novelty claims. The proposed
  destination-local observed-path selector coupled to source ACK-confirmed
  route state and one useful-DATA repair is a narrow, still-unproven
  differentiation. It needs a passive exposure gate, decisive same-copy-
  budget controls, and current-code population results before paper claims.

## 2026-10-04 - Same-Path ACK Repeat Exploration

- The frozen v2 41001--41020 20-seed paired recurring-fading experiment was
  independently audited with strict replay of all 40 arm runs, all input
  and artifact hashes, all 823 scheduled flows per arm, and physical ACK
  timing. Fixed-2-s same-path repeat minus fixed-2-s single ACK gave
  +0.01956 deadline source ACK-PDR (nominal paired 95% CI +0.00012 to
  +0.03899), -0.00572 destination PDR (-0.01146 to +0.00002), and
  +1.769% relative whole-network TX airtime (-2.891% to +6.429%). Pooled
  source confirmations were 799/823 versus 782/823; deliveries 814/823
  versus 819/823. All 250 eligible first-FLOOD records in the repeat arm
  produced one physical same-path repeat, 0 local drops. These effects are
  closed-loop, exploratory, and scenario-specific; the narrow ACK CI lower
  bound and delivery loss prohibit a broad reliability claim. The repeat
  arm is a mandatory simple comparator for a new ACK-selection core, not
  an ICC novelty result. Manifest:
  `results/meshecho_delayed_ack_repeat_explore_41001_41020_20261004.manifest.json`.

## 2026-10-04 - New-Core Boundary and First-Edge Screen Correction

- The source's F/R/D selection and DHR's 15-s R no-ACK recovery are the
  current algorithmic core. The simulator's PHY, scheduler, packets,
  metric accounting, and matched runners are reusable research
  infrastructure. Rewriting the core does not require rewriting that
  infrastructure; changing only a route-score threshold or ACK timer
  does not satisfy the requested algorithm rewrite.
- The earlier proposed 1.5x alternate-ACK airtime cap is superseded as a
  fairness screen: 25 of 36 source-final-hop ACK failures in the opened
  39xxx diagnostic followed direct source-destination ACK paths, so a
  two-hop alternative often cannot meet 1.5x even before its longer
  header is charged. Predeclare separate counts for timely distinct
  first-hop visibility, complete alternate-ACK ToA no greater than two
  copies of the original ACK, and among those a quantized first-edge
  margin at least 3 dB better. These are necessary exposure screens, not
  measured counterfactual success or novelty.
- An ACK1+ACK2 selector must charge both full reverse paths; comparison
  with a same-path two-copy control cannot call the alternatives equal
  airtime merely because they use two packets. The existing
  `min_forward_margin_q` is a whole-path minimum, so a first-edge
  predictor would need a separate on-wire, charged field and an
  independently validated prediction study.

## 2026-10-04 - Short R-Guard Control Result

- Independent audit of the 40001--40020 QC-v3 rerun passed all 12 frozen
  source hashes, 10 artifact hashes, 200 strict deterministic arm replays,
  and 20 stock comparisons. The 15-s baseline yielded 787/825 deadline
  source ACKs and 823/825 destination deliveries. Guard 1/2/4/8 s yielded
  777/775/776/787 source ACKs; paired source-ACK differences were
  -0.01105, -0.01454, -0.01111, and -0.00024, respectively, with every
  nominal 95% CI crossing zero. Whole-network airtime changes were
  +4.05%, +2.48%, +4.29%, and +3.08%, also all uncertain. The shorter
  guards shortened capped ACK delay but did not show better reliability.
  This is a quality-control rerun of opened exploratory seeds, not a new
  validation cohort. No short-guard novelty or ICC acceptance claim follows.

## 2026-10-04 - Diagnostic Reuse Boundary

- `tools/diagnose_first_hop_witness.py` reconstructs an old R-DATA
  first-hop witness/history question; it does not collect the destination's
  same-FLOOD alternative paths or a per-path first-edge margin for the
  proposed reverse-ACK selector. It cannot directly answer the new gate.
- `tools/diagnose_delayed_ack_rx.py` demonstrates an appropriate
  behavior-preserving pattern: call the simulator's physical decode once,
  record observations afterward, and demand exact stock parity for full
  metrics, flow/action/TX traces, and both RNG states. Reusing that
  verification pattern is valid; old 39xxx results are frozen to their
  older source hash and cannot replace fresh current-code evidence.
- `Simulator.handle_tx_end` attempts physical reception at every node,
  then calls `protocol.on_receive` only for successful decodes. A passive
  recorder can capture the successful source-FLOOD first-edge `RxInfo`
  after one `super().try_receive` without affecting RNG/metrics. The
  successful `RxInfo.snr_db` is a local observation; hidden PRR or later
  ACK success is not an admissible online selector input.
- `Packet.wire_size_bytes` charges path length, hop index, optional
  quantized margin bytes, and the repair marker. A reverse-ACK
  alternative must therefore be costed with its actual reconstructed
  packet for every physical hop; counting ACK copies or hop count alone
  is not an equal-airtime comparison.
- The base `on_fallback` returns on an already-seen FLOOD before the
  destination can emit another ACK. The diagnostic therefore must record
  every successful destination FLOOD physical decode before that
  protocol-level deduplication, while identifying the first decode that
  actually triggered the fixed-2-s ACK. R DATA may have delivered the
  application earlier; application `delivered_at` is not the FLOOD-window
  origin.
- The base reverse ACK copies the decoded FLOOD's realized path and
  `repair_index`; relays enforce `path_index` and forward by decrementing
  it. Current DHR delay ACK packets carry no independent first-edge
  margin. Adding such a charged field would alter F/ACK ToA and possibly
  collision outcomes, so a passive cost screen cannot itself predict
  the new protocol's end-to-end PDR.
- The current JFC draft's `P2` diversity condition tests a different
  destination predecessor (`P[-2]`), which diversifies the ACK's first
  reverse hop, not its final hop into the source. Historical 39xxx
  failures concentrated at that source-final hop (36/47). A remedy for
  that stratum requires a distinct `P[1]` (the source-adjacent forward
  edge), with source-adjacent and destination-adjacent diversity reported
  separately. This is a contract defect in the untested candidate, not
  an implemented algorithm result.
- At SF7 under the current charged packet format, a one-hop ACK costs
  0.051456 s and a two-hop alternative costs 0.113152 s in complete
  reverse-path airtime. The latter is about 2.20 times one direct ACK,
  so it exceeds even a two-copy direct-path ACK budget. Since 25/36
  observed source-final-hop failures had a direct original path, the
  equal-airtime branch has a structural exposure ceiling before any
  margin-quality filter; no post-hoc budget relaxation is justified.
- The audited 41xxx fixed-2-s same-path repeat confirmed 799/823 flows
  and delivered 814/823; on that policy trajectory only 15 flows were
  delivered but not source-confirmed. This limits the aggregate headroom
  for a more elaborate ACK-path selector against its mandatory repeat
  comparator. It does not establish a causal upper bound because a new
  closed-loop policy changes later traffic and collisions.
- In earlier opened 9001--9020 DHR-none histories, a prior R miss was
  associated with 61/102 subsequent no-ACK outcomes versus 111/408
  without a prior miss; one-hop cached R routes had 102/183 no-ACK
  versus 70/327 multihop. A small, selected 34001--34005 target screen
  also favored F or R-to-F delivery over R after one miss. These are
  hypothesis-generating strata, not causal policy effects or a new
  validated threshold. A source controller must compare against simple
  one-miss-F and R-to-F/R-to-R controls under the same feedback contract.
- `PendingSend` is a mutable handle created by `transmit_later`; the
  simulator commits a TX with physical `start=max(now,tx_available_at)`
  when handling its request. `handle_tx_end` later performs physical
  receives and `on_receive` callbacks. A passive causal parent map may
  observe the parent TX context during these callbacks, but must bind
  a child's actual TX ID only when its pending handle commits and verify
  `child.start>=parent.end`. Timer/request time is not a valid substitute
  for physical start, particularly for 30-s deadline screening.
- In the already-opened 38xxx saved flow table, final `acked_at` can be
  supplied by a later same-flow recovery FLOOD rather than the initial R
  DATA. A source decision-time risk screen must select true initial-R
  `decision` events, find actual source R TX start and accepted initial-R
  ACK (`dhr_source_ack_rx` with null repair marker) before its 15-s guard;
  D-to-R discovery fallbacks and later F ACKs cannot become initial-R
  successes. Features must be reconstructed strictly before that
  decision or physical start, never from final delivery truth.
- The 38xxx fixed-2-s saved arm has 613 initial `decision=R`, 94 initial
  F and 74 initial D among 781 scheduled flows. Its final flow table
  instead labels 615 as R and 72 as D-candidate because two initial-D
  flows fell back to R. All 613 true initial-R decisions have one
  matching unmarked source DATA physical start. The source risk screen's
  denominator is 613, not the earlier 615 final-action count.
- The first-edge passive diagnostic now keeps late physically decoded
  final ACK hops separate from in-deadline channel-outcome predictor
  samples. This prevents deadline exhaustion from masquerading as a
  low-quality reverse link. Alternative-path cost exposure and q-based
  selective same-path-repeat prediction are independently gated; path
  cost no-go cannot by itself reject the predictor question.
- The frozen 38xxx source-local risk screen was independently rerun from
  hash-verified archived artifacts: 613 true initial R starts, 449
  accepted initial-R ACKs before guard and 164 misses. Equal-seed
  leave-one-seed-out Brier is 0.19743 for prior-miss alone, 0.18589
  after adding one-hop status, and 0.18563 after adding ACK age.
  Hop-status gain is +0.01154 [nominal 95% CI +0.00295,+0.02013], but
  prior-miss/multihop and prior-miss/one-hop cells have only 19 and eight
  records, the latter across seven seeds. This fails the prespecified
  20-record/eight-seed support prerequisite. ACK age adds only +0.00026
  [-0.00351,+0.00404] Brier gain and also fails support. The NO-GO is
  for a source-only algorithm claim, not proof that hop count contains
  no signal; these observed-R data identify no F or R-repeat action value.
- Independent first-edge diagnostic review corrected an ACK2 timing
  overestimate: the actual repeat control requests ACK2 0.5 s after the
  destination's own ACK1 TX end, not after ACK1 traverses its full
  reverse route. Report schedule-compatible optimistic and serial
  nonoverlap bounds separately from complete charged airtime. A pooled
  q predictor can also be confounded by direct/multihop composition;
  only a path type passing its own held-out support, Brier and AUC gates
  can support a scoped later controller experiment.
- Post-correction verification of the read-only source risk screen passed
  10 focused tests and the 704-pass/1-skip full suite. Rerunning the
  historical hash-verified 38xxx analysis left 613 initial-R starts, 449
  guard-time ACKs, Brier gains and the 19/8 sparse-cell NO-GO unchanged.
  The correction therefore improves temporal validity without supplying
  evidence for a new source-only algorithm or a counterfactual F/R choice.
- Independent first-edge code review found that late source-final ACK TXs
  can disappear from the cutoff-late count, path-type predictor success
  can be declared without adequate type-specific training support, and
  exploration summary/support fields are trusted without recomputation
  from the saved hashed predictor rows. These are pre-seed provenance and
  gate defects, not measured protocol effects. The actual ACK2 timing
  formula matches the frozen 0.5-s-after-destination-TX contract.
- An exploratory forensic join of the already-audited 41xxx same-path
  repeat arm found 16 first-accepted source ACKs traceable to the second
  destination ACK among 250 repeat starts (eight direct, eight multihop).
  Fourteen had a later same-pair decision, 13 across eight seeds had no
  intervening accepted ACK/commit, and only 12 across seven seeds also
  had an ACK1 source-adjacent final-hop opportunity for a tail-only relay
  repeat. The existing ACK1/ACK2 packets are wire-identical; identifying
  the second copy required offline physical TX/action traces. Any online
  fragile-route policy needs a charged copy-index field. This old-policy
  opportunity count is too small for the provisional >=20/10 feasibility
  gate and cannot estimate a new policy's effect. The read-only count has
  not yet been independently scripted/replayed as a population artifact.
- Test-first first-edge diagnostic QC now treats a late physical final-hop
  TX as observed exposure even if its decode is censored by the simulation
  cutoff, excludes an entire FLOOD epoch on ambiguous causal parentage,
  gates claimed direct/multihop predictor success on both split-specific
  support levels, and recomputes training support/model from saved hashed
  rows before allowing validation. These are measurement/provenance fixes;
  710 current `pytest` tests pass with one skipped, but no 42xxx seed has
  supplied a signal or algorithm result.
- The 42000 first-edge passive mechanical smoke recorded 49 scheduled
  flows and 10 source-final ACK attempts (eight physical decodes, two
  failures); its independent artifact/replay audit is pending. Two
  source-final failed flows satisfy the A/B/C path-exposure filters in
  this one seed, which is deliberately not a population inference.
- The first 42001--42020 passive exploration manifest passed its built-in
  hash/semantic validation and reported 20 source-final failed flows:
  A/B/C/deadline candidate attrition 18/8/6/6. Six clears the 20%
  fraction but not the preregistered eight-flow minimum. The 221 pooled
  in-deadline final-hop predictor samples meet pooled training support,
  yet direct has 85 samples/15 failures and multihop 136 samples/five
  failures. Neither path type meets its own training support gate, so
  pooled fit cannot justify path-scoped validation. This interpretation
  remains provisional until independent strict replay of all 20 seeds.
- Independent artifact and strict-replay audit confirmed the 42xxx
  exploration attrition and its NO-GO. All 20 saved runs, 12,632 physical
  TX, 748 causal paths, 230 epochs and 483 alternative costs/timings
  reconciled exactly; there were zero rejected paths. Among 20 source-
  final failed, delivered/unACKed flows, A=18, B=8 and C+deadline=6
  (30%), below the frozen eight-flow minimum. Only two of those six
  preserve the two-copy same-path total budget if both original and
  alternative ACK are transmitted; adding two lifetime bytes leaves
  only three single alternatives within the B budget. Pooled q training
  has 221 attempts but neither direct nor multihop reaches its own
  100/20/20/10 support. The untouched 421xx validation is therefore
  intentionally sealed; these data cannot support the JFC design.
- Accepted source ACK `RxInfo.snr_db` is local device-visible data at
  `on_receive` and needs no new packet byte, unlike a destination-carried
  first-edge margin. Historical 41xxx logs contain 654 initial R decisions
  with a prior same-pair accepted ACK, but omit its RxInfo. Only 177
  ACK/decision timestamp pairs share the simulator's offline 60-s fading
  block; the value does not establish later physical TX-time reciprocity.
  SNR is success-selected, cannot predict downstream failures or capture
  from itself, and the symmetric fading model may overstate portability.
  A fresh passive signal screen must precede any source policy or ICC claim.
- Targeted verified prior-art check (`docs/research/meshecho_feedback_prior_art_boundary.md`)
  found existing hop ACK/retransmission, ACK/physical-signal link estimation,
  delayed/multipath ACK and route repair precedents. Only a specifically
  defined and empirically superior joint rule could be a plausible narrow
  contribution; a targeted search cannot certify novelty. Source-ACK-SNR
  transfer is especially vulnerable to the simulator's symmetric-link
  assumption and the real-world asymmetry concern documented by Sang et al.
- The current `PassiveFirstEdgeSimulator.try_receive` already records the
  result of exactly one delegated physical receive attempt, including ACK
  `RxInfo`, without requesting a second random draw. That is an implementation
  precedent for a passive source-ACK-SNR capture, not evidence that the SNR
  predicts the next source action or improves a policy.
- `Simulator.handle_tx_end` calls `try_receive` once per receiver and then
  immediately calls protocol `on_receive` at the TX end time. DHR logs a
  `dhr_source_ack_rx` accepted/rejected action in `on_ack_packet` after the
  identity, deadline, path and repair-marker checks. A passive diagnostic
  can therefore join physical source ACK decode to acceptance, but must
  reject missing/multiple same-time identity matches rather than silently
  infer acceptance from physical decode alone.
- Independent read-only review of the already-opened 42xxx action traces
  found 649 initial R decisions with a prior same-route accepted ACK; direct
  paths had 74 timely R ACKs and 57 misses among 131 decisions, and multihop
  paths had 434/84 among 518. Only 176/649 prior-ACK/next-R pairs shared a
  60-s fading block. Existing artifacts do not contain ACK `RxInfo`; these
  counts support measurement feasibility, not q predictive value or action
  benefit. `RxInfo.snr_db` is clean pre-interference SNR while `sinr_db`
  includes interference, so the draft gate now proposes effective SINR as
  the primary observational feature and clean SNR as sensitivity only.
- Independent review of the new cohort code exposed two temporal-denominator
  traps, both reproduced in public simulation callbacks. An initial-R ACK
  from an old route generation may arrive after a same-path recommit and be
  accepted without belonging to the new generation; acceptance time alone
  cannot assign q provenance. Separately, R can start on a provisional
  route before any commit, or queue across a later commit. Both cases must
  stay in the all-valid-start denominator with q missing and an explicit
  feature-ineligibility reason. The revised cohort code now derives R ACK
  generation from its originating R decision and keeps those rows.
- A runner guard test accidentally invoked reserved seeds 35001 and part of
  36001 before the guard existed, and completed 42101 and a repeat of the
  already-opened 42000 in memory. The tests never called `write_report`;
  no saved results were found and no ongoing process remained when checked.
  This is an integrity boundary, not a performance finding: 35001, 36001,
  and 42101 cannot be called untouched or used in a future holdout. The
  42000 repeat adds no independent evidence. All subsequent guard tests
  stub `run_diagnostic` before exercising seed rejection.
- Independent review of the existing ICC evidence found no demonstrated
  advantage of calibrated MeshEcho over a matched PRR-product comparator:
  20-seed paired ACK-PDR difference +0.002572, nominal 95% interval
  [-0.005531, +0.010674]. The five-page ICC draft is about that scoring
  policy, not an already verified new SR/DHR core. Fixed 2-s ACK delay is
  a strong simple timing control, while JFC and screened repair candidates
  are NO-GO. Rewriting the core is required for a new algorithm claim, but
  a positive mechanism cannot be asserted before device-visible signal and
  matched-action evidence exist.
- The prospective source-ACK-quality gate's first independent audit was
  NO-GO for freeze or 43000: its draft code omitted later-recovery and
  full-denominator path reporting, offline strata and clean-SNR sensitivity;
  direct diagnostic calls could bypass the runner's seed guard, and isolated
  validation-manifest review did not follow actual predecessor files. These
  are implementation/provenance gaps, not negative or positive signal data.
- A forged smoke manifest revealed that self-hashed run rows and a self-
  reported strict-replay flag cannot prove a declared seed/case produced
  those rows. A real-manifest validator must compare a fresh deterministic
  run of the exact seed/case/unchanged sources, while requiring an explicit
  replay request because validation itself runs simulations. In the first
  adversarial audit, this new replay unintentionally ran seed 43000 in
  memory before rejecting the forgery. The auditor saw no performance
  output and saved no 43000 artifact. It is nonetheless an opened seed;
  43200 replaces it as the prospectively reserved smoke. The complete
  source/model/manifest contract must be re-frozen before 43200 runs.
- Stage authorization cannot be represented by changing a frozen contract
  status after smoke, because the contract is an input in `SOURCE_FILES` and
  changing it would invalidate the smoke manifest's source hashes. Separate
  later-stage JSON permits avoid that problem. Their exact bytes matter:
  appending whitespace preserves JSON semantics but changes the permit
  SHA-256, so validation must compare the supplied exploration permit's
  byte hash with the saved exploration manifest before replaying any seed.
- The frozen 43001--43020 exploration has enough observational support
  (697 eligible initial R rows, 508 guard ACKs, 189 misses), but its first
  M0 leave-one-seed-out fit failed. Independent arithmetic diagnosis found
  floating-point absolute-loss cancellation near a Newton stationary point:
  a candidate with gradient about 2.53e-15 was rejected by Armijo even
  though its stable directional loss difference was about -2.76e-15. Since
  M0 excludes q, this NO-GO does not establish q's predictive value or lack
  thereof. The frozen fit/result must remain unchanged; fix under a new
  source/contract freeze and fresh research seeds.
- A four-row synthetic M0 fixture gives a real full-Newton objective decrease
  of about 8.56e-17 near iteration two (independent 70-digit Decimal check),
  while subtraction of separately rounded total losses reports a 4.44e-16
  increase. This confirms the Armijo false rejection at the public `fit_logistic`
  API. A direct softplus/ridge loss difference with compensated accumulation
  evaluates that small decrease while retaining the original objective,
  derivative and 1e-8 stopping rule.
- The corrected model can fit all 20 LOSO folds of the *inspected* 430xx
  rows for both q definitions, confirming the solver defect was operative.
  The q mean LOSO Brier gains over M0/T are only 0.002972/0.004080, versus
  the prespecified later validation mean-improvement threshold of 0.005 for
  both. q_clean is similarly 0.003024/0.004133; q-only rank AUC is 0.658058.
  These old-data diagnostics cannot reverse the frozen numerical NO-GO or
  substitute for fresh validation. They weaken the case for making q the
  new core's sole decision signal; alternative device-observable mechanisms
  need separate exposure and novelty review.
- An independently audited 37xxx failure-cause screen found only one strict
  post-delivery ACK-intent cancellation opportunity among 24 delivered-but-
  unACKed flows (4.17%), below both prespecified exposure minima. That
  branch cannot plausibly anchor the core rewrite in the tested workload.
  The fixed 2-s FLOOD ACK delay instead gave exploratory +0.2251 source-ACK
  PDR and -16.73% whole-network airtime versus immediate ACK across 20
  paired seeds, but is a simple timing control chosen after earlier traces.
  A successor must beat it and same-budget repeats with device-visible
  behavior; neither observation establishes new algorithm novelty.
- The audited fixed-2-s same-path ACK-repeat control gained only +0.01956
  source-ACK PDR in its 20-seed exploratory cohort, with -0.00572 destination
  PDR and an uncertain +1.769% whole-network airtime change. Shortening the
  R guard from 15 s to 1/2/4/8 s showed no reliable source-ACK gain and
  tended toward higher airtime. Both are important matched controls, not
  sufficient source/feedback/recovery redesigns.
- A 2026-10-05 targeted source check reverified RFC 4728's separate DSR
  software ACK-request retransmission and Lee et al. 2020's abstract-level
  adaptive ACK-copy waiting/multipath primitive. Crossref and Semantic
  Scholar metadata matched the Lee, Sole 2026 and JMAC 2020 DOI records.
  The checked sources preclude first-of-kind claims for the primitives but
  neither prove nor disprove novelty of a future joint MeshEcho contract.
  See `docs/research/meshecho_feedback_prior_art_factcheck_20261005.md`.
- The saved fixed-2-s cohort gives an unfavorable STATUS-query split: only
  18/164 initial-R no-ACK guards had already delivered DATA by the guard,
  and only eight of those still lacked a deadline source ACK after existing
  useful-DATA recovery. An unconditional query would burden all 164 guards;
  an optimistic routed-query/reply airtime calculation allows some saving
  on delivered flows but leaves about 2.22 s for query/response before the
  nominal F+2-s-ACK reserve, excluding queueing. This is a read-only upper-
  bound screen on divergent historical traces, not a counterfactual outcome.
  Reject unconditional query as the next full core; a selective variant
  needs a source-visible trigger and a new prospective passive gate.
- In audited 420xx first-edge diagnostics, 20 reverse ACK attempts failed
  physically at the source-final hop; 15 were direct destination-to-source
  paths and only five had a distinct source-adjacent relay. A perfect extra
  tail-only copy could directly touch at most 20/820 historical flows and
  relay-only saving at most five/820 before changed-trajectory effects.
  Nominal 0.5-s-spaced tail copies fit all 20 original deadlines, but the
  same-flow first-edge q has insufficient verified path-type support and
  a local sender cannot know whether its first ACK reached the source.
  Tail-only repetition is a potential component/control, not yet a full
  source-policy rewrite or demonstrated improvement over full-path repeat.
- A read-only 42xxx route-generation join identified a more exposed *forward*
  backup hypothesis than the previously rejected alternate reverse-ACK
  hypothesis: 186/201 source-confirmed F routes had a distinct destination-
  decoded path in the 2-s collection window; 108/141 later R no-ACK guards
  had one from their matching F generation. The old fixed-F rescue already
  delivered 107/108 and source-ACKed 94/108 of these 108 flows, so there is
  little delivery headroom and the backup-R counterfactual is unknown.
  Moreover 84/108 backups were at least one 60-s fading block old at guard.
  Carrying one path in ACK is estimated to add 8--12 bytes before changed
  collision/queue outcomes; it must be charged in all protocol accounting.
  These numbers motivate a falsifiable candidate only, not a new result.
- Independent prior-art critique found that ACK-carried backup plus simple
  primary-to-backup failover is too close to DSR cached alternate routes
  (RFC 4728) and AOMDV disjoint paths (DOI 10.1002/wcm.432) to stand alone
  as an ICC core claim. The only defensible candidate is a narrower joint
  on-wire/airtime/deadline policy that beats a same-information DSR-style
  first-alternate control and fixed-F rescue. If its decisions are equivalent
  to that simple control, the novelty gate is NO-GO. Historical 42xxx marked
  recovery TX used 336.853 s of 999.576 s complete-network TX airtime, a
  potential cost target but not an attainable saving estimate.
- An end-to-end public test showed an ACK with a valid encoded path could be
  accepted even when physically transmitted by a node not adjacent on that
  path. The DBR-specific receive hook now checks `RxInfo.sender` against the
  encoded next reverse hop before forwarding or source acceptance. This is
  a protocol-validity correction for the candidate, not measured gain.
- The DBR comparison modes now expose the intended decision contrasts under
  identical local feedback: same-path repeats the original DATA route;
  first-alternate uses an old backup that DBR's 120-s freshness rule rejects;
  padded fixed-F ignores a carried backup while plain fixed-F omits its
  bytes. A three-node backup adds seven bytes to the ACK. These are public
  behavior tests, not population results; full-airtime and source-ACK effects
  remain unknown until a frozen, audited prospective run.
- Independent algorithm review found that selective DBR and the DSR-like
  first-alternate control make the same path choice whenever a fresh backup
  exists; their main current branch difference is the 120-s rejection rule.
  This may be too narrow to sustain a new-core ICC contribution even though
  old F/R/D decisions were replaced. Require measured branch divergence and
  outcome/cost advantage; otherwise reject or redesign DBR. The draft also
  lacks complete capacity-overflow reason accounting, recovery admission/
  actual-start reporting, and tests for generation, late ACK, malformed path
  and delayed cancellation boundaries. No paper claim follows yet.
- Public simulation reproduced two protocol-invalid outcomes: an expired
  primary route still admitted a backup DATA probe, and a decoded FLOOD with
  the wrong claimed origin but a reused `flow_id` falsely marked another
  source's flow delivered. Both now have red/green end-to-end regressions and
  source checks. A guard event also now distinguishes stale-backup F fallback
  from a backup admission, allowing a future runner to count true branches.
- Independent runner review confirmed that generic SR totals still account
  for physical DBR TX but its DHR-specific recovery counts omit marker 3;
  source hash selection may identify DBR as LPR, and saved artifacts omit
  the complete TX stream. New DBR results cannot use those fields or claim
  strict replay without a dedicated runner and tuple restoration for
  `alternate_path` as well as `path` and `learned_path`.
- At SF12 with six hops, the prior FLOOD admission formula's omission of a
  maximum-length backup field in the reverse ACK undercounted its nominal
  round trip by 2.94912 s in a public test. The estimator now charges those
  bytes; it is still an admission bound, not a physical-delivery guarantee.
  The ninth concurrent feedback window also now emits a capacity-overflow
  event while sending exactly one unaugmented ACK.
- A same-time radio-busy test exposed a silent recovery hole: guard selected
  B but its pending TX was canceled after the source became busy, leaving no
  physical recovery. A related F request canceled when its actual start
  moved later. Both now emit request-drop reasons and use a fresh timer at
  radio idle to reconsider F under the original deadline. A late R ACK
  accepted before that timer prevents the extra F.
- A reordered-flow/ACK test exposed an old-generation backup ACK rolling
  back a newer FLOOD route commit because the old check compared only flow
  IDs. Route promotion now also requires the active R flow's captured route
  generation and sent primary path to match current source state. The old
  B ACK still counts as its own flow confirmation; it cannot rewrite the
  newer route. This must be reported separately from source-ACK PDR.
- Marker-3 backup ACKs bypass DHR's source-ACK event path, so a runner using
  `dhr_source_ack_rx` alone would undercount the candidate's acknowledged
  recoveries. DBR now logs `dbr_source_ack_rx` with acceptance determined by
  the flow's `acked_at` state change, including the actual ACK path; duplicate
  or invalid copies cannot be counted as a second accepted source ACK.
- Independent DBR contract review did not reproduce duplicate F or route
  rollback after the latest fixes, but same-time queued requests and all
  R/B/F ACK arrival orders still need explicit boundary coverage. SF10/two-hop
  backup nominal round-trip is about 1.89 s against a 2-s guard; even small
  queueing can trigger an extra F, so PHY sensitivity is material.
- The first dedicated DBR runner does not yet produce publication-grade
  evidence. Its module-level capture token can bypass the stage gate; its
  permit is same-worktree self-generated, not independent authorization;
  it does not persist/reload TX or audit per-flow and paired-arm invariants;
  and its TX writer expects objects while capture returns dictionaries.
  Single-arm strict replay and packet tuple normalization are present, but
  cannot substitute for a complete audited experiment. No 44xxx seed ran.
- A new read-only join of the previously inspected 42001--42020 artifacts
  limited each R no-ACK guard to its latest preceding F/F-recovery route
  commit on the same source/destination, required the commit path to match
  that FLOOD epoch, and selected a first-hop-diverse destination-observed
  alternative. This yielded 105 exposed guards, of which 32 had a backup
  older than DBR's 120-s cutoff (17 in seeds 42001--42010). Thus the current
  DBR-versus-first-alternate age rule has at most a modest old-trace branch
  exposure, near or below the draft's 20-divergences-in-ten-seeds gate.
  This is not the counterfactual DBR population, and changed trajectories,
  radio-start/deadline admission, or ACK-field cost can change all counts.
  The older 108/141 exposure used a different join/eligibility definition;
  do not pool or substitute these denominators.
- Open device-observability issue: DBR's destination `on_fallback` checks
  `self.sim.metrics.flows` for the registered flow's true source/destination
  before acknowledging a packet. A real destination does not have the
  simulator's global application registry, and an unauthenticated packet
  cannot be proven to originate from its claimed source using the current
  header alone. This may only affect malformed injected packets in tests,
  but the code and draft must either move identity checks to analysis-only
  accounting and state an explicit non-adversarial threat model, or supply
  a genuine on-wire/local validation mechanism with charged cost. Do not
  claim unconditional device-local behavior until resolved.
- Resolution for the destination portion: DBR's ACK decision now validates
  only packet header/path coherence and local feedback state, then may ACK a
  spoofed-but-coherent claim. `Simulator.mark_delivered` checks the packet's
  claimed source/destination against its registered flow solely before
  crediting measured delivery and invoking the delivery callback. This
  removes the destination oracle from physical protocol behavior while
  preventing a forged origin from inflating another flow's PDR. It does not
  authenticate senders or cover malicious injection; those remain outside
  the candidate model and must be disclosed. Source-side uses of global
  metrics as a stand-in for local ACK/deadline state still merit audit.
- A 2026-10-05 independent runner audit found that `run_one_sr` has no DBR
  reserved-seed guard; `--split custom` can therefore begin 44200/440xx/441xx
  simulation before any dedicated authorization, even through a comparator
  policy. The existing public regression fails at `generate_nodes`, proving
  the bypass without running a reserved topology. The saved-artifact audit
  also lacks canonical manifest/row identity checks and action-to-physical-TX
  reconciliation. These are provenance defects, not DBR performance data.
- The guarded `run_one_sr` interface now rejects the smoke, development and
  holdout representative seeds before topology for DBR and non-DBR policies;
  its required capture token and stage permit are supplied only by the
  dedicated DBR capture path. A nonreserved fixture seed 73 was deliberately
  marked protected in tests to exercise the authorized path without exposing
  a real 44xxx cohort. This closes the accidental generic-entry bypass but
  is not a security boundary against a caller intentionally importing the
  private token or monkeypatching Python modules.
- Independent device-locality review found no confirmed DBR policy use of
  global delivery outcomes, channel truth or future TX. The source's
  `Metrics.flows[flow_id].acked_at` is updated after a physical ACK reaches
  the source; destination backup selection uses decoded FLOOD paths and its
  local feedback window. The remaining P2 coupling is source decision code
  reading this global metrics object rather than mirroring source-local
  `{src,dst,enqueue_time,accepted_ack}` state. This is currently local-
  equivalent but should be decoupled and tested before a firmware claim.
- Persisted evidence can still accept an invented `dbr_backup_tx` action
  when file hashes and the run's replay digest are recomputed: a new public
  fixture test appends such an action, rehashes the archive, and currently
  fails because `audit_artifacts` raises nothing. Action-to-full-TX matching
  is the next red/green audit slice; no actual backup run was inferred.
- That persisted-action gap is now closed for physical recovery starts:
  `audit_artifacts` compares multisets of marker-3 backup DATA and inherited
  marker-1/2 recovery actions against full source TX records, including flow,
  endpoints, path where available, and exact start/end times. Forged B and F
  actions with recomputed artifact/replay hashes both fail. A separate
  red/green test requires `strict_replay_exact is True` in the manifest.
  These checks do not prove each ACK receive from TX alone because decoded
  receptions are not archived, and the archive's input hashes lack an
  external signature/trust anchor.
- Independent post-fix review found no new P0/P1 runner defect; its GO is
  limited to a mechanical smoke after contract freeze, not scientific value.
  Scientific review recommends NO-GO for spending current DBR development or
  holdout on this mechanism. Selective DBR and first-alternate are identical
  when the same-generation backup is no older than 120 s. The strict old-data
  join finds 105 candidate guards in 820 scheduled flows, 32 older than
  120 s across 20 seeds (17 in the first ten), before actual-start/deadline
  attrition; these are exposure, not causal results. Existing fixed-F already
  destination-delivered 107/108 and source-ACKed 94/108 exposed flows in a
  different old join. The draft's formal thresholds are >=20 physical backup
  starts spanning ten seeds and >=20 DBR/first-alternate branch differences
  overall, not 20 branch differences in ten seeds. No threshold has yet been
  tested prospectively. A more distinct decision rule is needed before
  fresh cohorts are spent.
- Two device-observable redesign leads remain pre-implementation questions,
  not selected algorithms. Prior source-accepted ACK SINR/quality is available
  without new bytes for some subsequent R decisions, but old 430xx logistic
  fitting had a numerical failure; after solver correction on inspected rows,
  its leave-one-seed-out Brier gain over hop/miss/age controls was about
  0.003--0.004, below the planned 0.005 validation target. It needs a new
  passive train/validation split and link-asymmetry/PHY check before action
  code. A charged first-hop receipt might disambiguate some R forward loss,
  but prior source-overheard progress covered only three no-ACK multihop
  flows, and DSR passive/software ACK plus link ARQ are close prior art. It
  needs a new branch/exposure and complete-cost screen against early F and R
  repeat. Neither lead justifies an ICC method claim or fresh holdout yet.
- The next pre-implementation screen is an actively charged first-hop
  receipt, **not** a claim that the existing source can observe intended
  first-hop DATA decoding. Prior passive witness evidence found only 86
  initial R first-hop starts across 12001--12003: 31 direct/55 multihop,
  with 14/8 respective intended-hop failures. This supports a new
  prospective exposure question, not a gain estimate. A 17-byte modeled
  one-hop receipt has 0.051456-s ToA at the current SF7/BW125/CR1 case;
  every successfully decoded multihop R would pay that lower-bound cost,
  including those already ACKed end to end. Receipt loss, queueing and
  collision can only be assessed by an implemented protocol. The design
  now requires physical first-hop failure plus residual deadline-unACKed
  opportunity and a complete-network cost gate before behavior coding;
  merely conditioning early F on a receipt is a prior-art-adjacent simple
  control. The existing ICC bibliography lacks several nearest ACK/ARQ/
  alternate-route works, which must be verified and cited before a new
  contribution claim.
- A separate 2026-10-05 read-only quiet-window ACK review is NO-GO as a
  complete new MeshEcho core. Under the old fixed-2-s control, all 42
  first-FLOOD-ACK flows that were delivered but source-unACKed had on-time
  ACK starts and at least 10.6845 s from their last recorded reverse TX
  to the original deadline; 37 reached a final TX toward the source, and
  17 had no overlapping other TX at their last observed ACK. A local
  min-1-s/quiet-0.5-s/max-3-s timer would expose timing branches in the
  inspected traces, but the source cannot see destination quiet state
  when its ACK is lost. Those branch counts are not causal outcomes, and
  changing only ACK wait plus deadline accounting does not replace the
  source decision/recovery core. Fixed ACK timing and adaptive waiting
  also have close prior art. Keep this as a possible component, not a
  main-algorithm result or a reason to edit the ICC paper.
- The first-hop receipt diagnostic now has a guarded reserved-seed entry,
  complete initial-R physical-start/decision reconciliation, passive-label
  archive checks, and 2-s ACK-hold timing accounting. These are evidence
  integrity properties, not an algorithm result. Its 19 fixture tests and
  the 903-test full regression pass; no 45xxx observation exists yet.
- Post-fix independent audit found a P1 stage-integrity gap despite those
  fixture passes: the importable `_RUNNER_AUTHORIZATION` token alone permits
  a direct 45001 run before the smoke prerequisite, and smoke lacks a
  prespecified frozen-input authorization file. The scientific readout is
  unchanged: no 45xxx result exists and no full-core algorithm is selected.
  Repair the stage boundary and independently re-audit before opening 45000.
- First-hop receipt has limited information even under an optimistic pass:
  success proves only first-edge progress; it cannot distinguish later DATA
  loss from reverse ACK loss, and absence mixes DATA and receipt loss.
  Conditional early F is itself the simple control, not a novel joint rule.
  A future core needs a different device-visible branch and measured gain
  beyond receipt-equipped and receipt-free early-F, fixed-F, R-repeat and
  alternate-route controls. The fixed-2-s residual study has 44 delivered-
  but-unACKed flows among 781 scheduled, including 42 with on-time FLOOD
  ACK starts, so the reverse-confirmation problem remains central.
- A read-only ICC baseline fidelity audit found three material threats to
  a future superiority claim: Meshtastic-like unicasts always flood rather
  than learn directed next hops; MeshCore-like first sends a separate
  RREQ/RREP rather than useful DATA on first contact and omits native
  retries; and the current single reverse-path ACK/report model can drive
  large conditional ACK discrepancies even when destination delivery is
  high. These are disclosed stylizations in the current manuscript, not
  production-firmware comparisons. Before a rewritten paper, run
  source-trace-matched learning/first-contact/retry and ACK-route
  sensitivities, charge all control bytes and network airtime, and stratify
  first versus later pair contact. A role-mix sensitivity should separate
  client and repeater nodes rather than treating every node as a router.
- The stage-authorized first-hop receipt seed-45000 mechanical smoke produced
  42 scheduled unicasts, 34 initial-R rows (27 multihop, 7 direct), and a
  complete 719-TX archive. Among eight multihop R flows lacking an ACK at
  the initial guard, three failed the intended first DATA hop, but all three
  received a source ACK by the original 30-s deadline under stock fixed-F.
  The nominal early-F timing admitted the same three as fixed-F; no early-
  only or residual-unACKed opportunity remained in this *one seed*. Charged
  17-byte receipt lower-bound airtime was 1.234944 s, 2.125% of complete
  network TX airtime. These values are smoke observations, not a 20-seed
  feasibility verdict or a causal estimate of a new policy.
- The first formal 45001 exploration attempt exposed a capture-composition
  defect, not a protocol outcome: generic stage validation strictly replayed
  the smoke while `sr.RecordingSimulator` was patched by the outer 45001
  capture. The nested stock capture resolved that patched factory and
  appended the smoke simulator to the 45001 capture list, then the 45001
  simulator raised a two-instance assertion. The 45001 stock run occurred
  once but no outcome archive was written; 45002--45020 were untouched.
  Binding the true stock recorder class before any capture patch closed the
  deterministic seed-73 reproduction. The old permits/manifests remain
  historical only because the diagnostic and test source hashes changed.
- The audited 45001--45020 passive receipt screen is a preregistered NO-GO.
  Among 783 scheduled flows, 778 were destination-delivered and 742 got a
  source ACK; 36 were delivered-but-unACKed and five undelivered. First-hop
  failure exposure passed (57/90 multihop R no-guard-ACK flows, 19 seeds),
  nominal residual source-ACK opportunity passed (10 flows, seven seeds),
  and 17-byte receipt airtime lower bound passed (2.3604% of complete TX
  airtime). Yet all ten residual flows had already reached the destination;
  no early-only deadline admission occurred; the equal-seed optimistic
  source-ACK ceiling was 0.0128713, below frozen 0.02, with zero destination
  ceiling. Four more receipt-positive, source-unACKed multihop R flows were
  likewise delivered. The first-hop receipt and suffix-rescue RCR branches
  lack this workload's forward-rescue headroom and should not be coded or
  claimed. The successful CLI strict replay and independent saved-artifact
  audit agree; see the dedicated result note and manifest.
- Independent online-controller exposure review also rejects an unpooled
  per-pair three-arm F/R/D bandit on these traces: 80 pairs had only 6--13
  flows each, only one pair had at least two observations of each initial
  action, and 47 pairs had no source-ACK miss. Initial F/R/D decisions were
  95/612/76; these are selection-biased old-policy outcomes, not causal arm
  estimates. A pooled model would still require prospective device-local
  controls and cannot use global TX airtime or hidden destination delivery
  as source inputs. Existing firmware already has online profile learning.
- A no-rerun, structured JSONL join of the audited 45001--45020 archive
  found 36 flows delivered by deadline without a source ACK. All 36 have
  at least one ACK TX starting and ending by deadline, but only 30 have a
  path-index-0 ACK TX (the final reverse-path transmission toward source)
  by deadline. For those 30, the maximum observed final-leg completion
  slack before the original deadline ranges from 11.43 to 29.85 s; all
  exceed 5 s. This is a physical-TX opportunity **upper bound**, not a
  source decode, causal rescue estimate, or device-local failure signal.
  The 450xx archive has complete TX and flow records but not full ACK
  decode rows, so successful final-relay reception and a selective retry
  trigger cannot be inferred from this join alone. An independent audit
  and comparison with the 41xxx charged same-path repeat are needed before
  choosing a reverse-ACK contract.
- Independent saved-row review refined that bound: the 30 timely final-hop
  ACK flows comprise 24 direct destination-to-source paths and only six
  multihop relay-to-source paths; 19 of their first final-hop TXs overlap
  some other TX, two with source TX, and 11 have no overlap. A last-hop
  sender has no local evidence that its ACK was decoded by source. Thus
  unconditional final-hop repetition is a simple control, while a
  selective repeat requires charged source confirmation. The distinct
  relay-only population is just six residual flows here. Detailed audit:
  `docs/research/meshecho_reverse_ack_last_hop_screen_450xx.md`.
- A second no-rerun JSONL join screened piggybacked cumulative ACK on the
  next same-source/destination application flow. Seven of the 36 delivered-
  unACKed flows had another same-pair send before the earlier 30-s deadline;
  all seven later flows reached the destination by that earlier deadline,
  but only five got their own ACK back to source in time. Even granting
  free, perfect bitmap piggybacking and no changed collisions, the archived
  all-flow source-ACK gain ceiling is five of 783 (0.00639). The initial
  `jq` query mistakenly compared a nested next-flow record against its
  absent `.deadline` field and reported zero; rebinding the outer target
  deadline corrected the counts to 7/7/5. This is an optimistic timing
  bound, not a causal protocol result or a novel selective-ACK claim.
- The destination-certified backup candidate's initial passive gate
  incorrectly counted every physically plausible local rescue toward an
  all-flow source-ACK gain ceiling. Fixed-F later source-ACKs on those same
  stock flows already satisfy that endpoint, so they cannot be new ACK
  successes. The gate now separates only deadline-unACKed stock flows as
  reliability headroom from already-ACKed stock F rescues as possible
  airtime substitution, with explicit lower-bound added costs. This was
  corrected before the reserved 46xxx screen was opened.
- The current `Packet.wire_size_bytes` charges the base 32-bit flow ID but
  only charges `request_id` on RREQ/RREP, not DATA/ACK. A nominated backup
  therefore needs charged fields: at minimum a 16-bit relay ID in F ACK
  and a 16-bit relay ID plus 32-bit earlier F epoch ID in later R DATA.
  Existing `alternate_path` can encode a full route at higher cost; metadata
  alone cannot make the new signal free on air.
- Mugerwa et al., Sensors 2023, DOI 10.3390/s23083874, use LoRa overhearing
  relays and cancel a pending retransmission on hearing a destination ACK.
  This close prior art rules out ACK-gated forwarding as a stand-alone
  novelty claim. Any new core must test the added destination-observed
  prior-path feedback and cross-flow nomination against an IOMC-like
  same-information/same-budget control. Full-method comparison and causal
  experiment are still pending.
- A corrected no-rerun jq join of the old 42001--42020 archive found 131
  *initial-decision R* one-hop DATA flows, only eight source-unACKed and one
  destination-undelivered by the original deadline. Fifty-seven of the 131
  later launched marked F recovery; 49 of those reached source ACK, and
  their F/ACK physical TX airtime totaled 116.945152 s out of 999.575552 s
  complete network airtime. This 11.7% gross cost pool is before certified
  backup eligibility, new bytes, relay/ACK TX or collision changes; it is
  not an effect estimate. The first jq filter incorrectly used `index(.)`
  with the array as current input and reported 133; explicit key binding
  excludes two D-to-R fallback flows and yields the audited 131. The
  candidate is therefore prospectively cost-first with source-ACK
  noninferiority, not a claim of material ACK-PDR uplift from these traces.
- Independent near-prior-art critique found a logical comparator trap: an
  IOMC-style arm given the same nominated relay, timer and ACK suppression
  rule is identical to the proposed mechanism and serves only as a parity
  control. The meaningful comparison is a same-byte, same-time local/current-
  overhearing relay selector versus the destination-certified historical
  selector, plus an unconditional-forward ablation. The source must also
  validate a backup reverse ACK against the active flow, nominee, F epoch,
  marked physical start, exact reverse path and original deadline before
  crediting or committing it. A 46xxx screen passing would license a
  prototype, not a novelty or ICC performance claim.
- Under the current backup contract all eligible alternatives are two-hop
  paths, so "shortest then earliest decoded" chooses the first eligible
  alternative. A first-alternate control with identical eligibility is
  another parity check, not an independent algorithmic comparator.
- Stock delayed-F-ACK code constructs the ACK immediately at first
  destination decode and schedules only its TX two seconds later. A
  destination-certified successor would have to construct the ACK at
  window close to include later decoded paths; passive 42xxx/46xxx path
  windows are hypothetical exposure, not actual ACK contents. Current SF7
  modeled ToA is stepwise: 16-byte direct ACK and 18-byte ACK are both
  0.051456 s, while adding six charged bytes to 48-byte direct DATA raises
  ToA from 0.097536 to 0.102656 s. Full-path/per-hop costs still govern.
- The fixed-F DHR control schedules recovery at the initial R physical
  start plus a 15-s ACK guard. Complete F-recovery airtime can be credited
  as a hypothetical substitution only when a candidate reverse ACK could
  reach the source before that guard, not merely by the 30-s application
  deadline. The 46xxx screen now predeclares 2 s as the primary relay timer
  and 0.5 s as sensitivity; both remain optimistic no-queue proxies.
- The generic `run_one_sr` entry initially had no 46xxx seed reservation,
  so a direct call could generate those topologies before the staged
  observer's own guard ran. It now rejects the exact backup-screen range
  before topology unless the matching protocol, case, deadline, token and
  validated stage permit are present. The runner must still prove its
  authorized path and archival integrity end to end.
- An independent cost audit caught two opposing bound errors before 46xxx:
  charging a two-hop ACK for every nominal relay start assumes successes
  that need not occur and can falsely depress an optimistic savings ceiling;
  omitting the explicit backup marker from relay DATA/reverse ACK omits
  required on-wire bytes. The primary screen now specifies ACK cost for
  each credited F substitution and at least one marker byte on the relay
  DATA and both reverse ACK hops. Observer fixes and tests are in progress.
- The first staged-runner implementation exposed a nested capture hazard:
  generic `run_one_sr` revalidates exploration, which strict-replays the
  smoke manifest while an outer `capture_run` has patched the simulator
  factory. The stock recorder must be bound before any patch; otherwise a
  nested replay may capture multiple simulator instances or alter provenance.
  A nonreserved nested-replay regression is required before 46000.
- The direct-script 46000 smoke initially stopped before topology because
  `__main__` and the canonical `tools.run_destination_backup_screen` module
  held distinct identity tokens. A red subprocess guard test and canonical
  entry repair resolved this; the first permit is invalid and produced no
  outcome artifact. The v2 smoke passed strict replay and independent
  arithmetic/parity audit under new hashes.
- The saved 46001--46020 passive screen reports 36 failed-primary/current-
  relay decodes across 17 seeds and a 0.0552837 equal-seed *optimistic*
  whole-network airtime substitution fraction after minimum charged costs.
  The source-ACK gain proxy is only 6/872 scheduled flows. These are
  eligibility/cost ceilings from unchanged stock behavior, not an effect;
  independent cohort audit remains pending. The pass is narrow relative to
  the predeclared 0.05 cost gate, so actual queue/interference costs could
  erase it.
- Current packet `request_id` is not charged on DATA/ACK, while `path`,
  `alternate_path`, and `repair_index` are explicitly charged. A new F-ACK
  nominee and subsequent R/DATA binding need their own modeled bytes;
  copying simulator metadata cannot satisfy the wire contract. Also,
  `begin_transmission` can commit a queued transmission whose physical
  `start` is later than the request event. Cancellation at the nominal
  relay timer is insufficient: the implementation must defer or recheck
  the relay's physical radio start, local ACK reception, and deadline.
- On this macOS host, default `tar -czf` silently adds AppleDouble `._*`
  files and PAX metadata while the ordinary tar list hides them. The first
  frozen-source archive contained 36 raw entries, not the intended twelve.
  `COPYFILE_DISABLE=1 tar --format=ustar` produced a clean twelve-member
  archive, verified by a raw TarReader and decompressed member hashes.
- The DCB contract audit found that `begin_transmission` can call
  `on_transmit` before a queued packet's physical start. A nominated R packet
  therefore needs an immutable enqueue snapshot and a separate start-time
  activation; direct R ACKs do not need to echo its extension, while marked
  backup DATA/ACK carry a charged epoch and marker. The source cannot observe
  a remote relay's TX start. An older screen clause demanding that check is
  superseded by local ACK validation plus independent provenance audit.
- The 46xxx screen's 5.528% optimistic airtime opportunity remains narrow and
  used lower byte costs than the revised contract. It justifies a test-first
  prototype, not confidence that DCB will beat the fixed-2-s F control or
  provide an ICC-worthy algorithm contribution.
- The independent control review specified a current-overhearing selector
  that ignores the DCB nominee, uses only physical destination reception
  history and current DATA reception, and contends in deterministic slots
  within the same 2-s budget. Its source must accept a marked ACK through
  whichever relay actually forwarded; otherwise the comparison is biased.
  Prespecified 20-seed development and 40-seed holdout gates now demand
  reliable delivery and positive paired whole-network airtime evidence, not
  merely an optimistic passive opportunity bound.
- The first DCB prototype now produces charged F-ACK relay feedback, a
  source-nominated direct R header, and an early marked relay DATA with an
  epoch-carrying reverse ACK. A normal successful direct R ACK was physically
  decoded by the nominated relay but initially failed to suppress backup:
  the ACK forwarding-path filter ran before off-path overhear recording.
  Reordering those local operations fixed the measured redundant TX without
  allowing the relay to forward an off-path ACK.
- A malformed FLOOD path index was physically decoded and incorrectly
  produced destination delivery/ACK; validating its incoming path index
  before feedback admission fixed the false positive. A marked backup DATA
  with source repeated as relay likewise reached destination; requiring
  three distinct path nodes fixed it. The current-overhear contender also
  needed that same validity check before suppressing on another marked DATA.
- One-shot relay forwarding failed after the first backup TX removed its
  pending entry: a duplicate current R DATA caused a second marked TX.
  Source flow IDs are monotonic in this simulator, so a bounded per-relay,
  per-source high-water mark now rejects late copies of already forwarded
  flows. The corresponding physical duplicate test is green.
- Independent code review found the inherited `seen_floods` set is unbounded,
  so the contract must not call it bounded. The pending F windows are capped
  at eight, but that is not a whole-protocol memory bound. Rejection-cause
  logging and additional boundary tests remain before any causal cohort.
- The resumed DCB check confirms a partial core rewrite: destination feedback,
  charged nomination and relay forwarding differ from the old ICC policy,
  but the F/R/D source action controller is inherited. A positive same-budget
  causal result and a prior-art distinction are still needed before calling
  this a paper-ready algorithm; the passive 5.528% bound is not that result.
- A new public-flow test passed: certification still appears on direct R DATA
  at 119 s after the accepted F ACK, but is absent at 121 s while the cached
  direct route remains in use. This verifies the age gate without implying
  any delivery or airtime gain.
- A physically decoded marked ACK from an incorrect transmitter was already
  rejected by ACK-path validation, but its cause was invisible. The new
  source-side rejection event identifies `path-or-sender-mismatch` without
  changing radio decisions. An ACK arriving after the original 30-s deadline
  also remains unconfirmed in a complete flow test.
- Destination backup-DATA validation had a real identity gap: a physically
  received marker-4 packet with a correct three-node path but a foreign
  `request_id` was counted as delivered. A red public-flow test reproduced
  this; requiring request ID equal to flow ID before destination processing
  made it green. This is a correctness fix, not performance evidence.
- The staged runner now has a separate accepted-backup-ACK provenance audit
  requiring matching destination physical-decode action, backup TX, and
  reverse ACK TX, in addition to paired complete-network costs. It remains
  fail-closed while the DCB contract is draft.
- Independent review reproduced a real early-state defect: `begin_transmission`
  can commit an R DATA with physical start in the future, and inherited DHR
  inserted `active_flows` before that start. The DCB-specific deferred
  activation now binds both recovery state and nomination at actual start.
  When that start is after the original deadline, DCB creates neither state
  nor a cleanup event in the past; the late physical TX is still charged.
- Direct CLI execution originally had a separate `__main__` authorization
  token and would fail all reserved cohorts before topology. It now dispatches
  to the canonical module; a no-seed subprocess regression verifies that
  identity. The draft contract's extra comparator arms, packet queue-wait
  distribution, and peak state measurements are not yet implemented, so
  source/contract freeze remains NO-GO despite green focused tests.
- The new observability slice can stay DCB-runner-local: subclass the current
  `RecordingSimulator` to pair each committed TX's request time with its
  physical start, then persist that timing beside the existing full TX
  artifact. `queued_future_tx_count` is not a queue-wait metric. Feedback
  window/pending peaks need update-on-admission counters; inherited
  `seen_floods` only grows during a run, so its final per-node size is its
  peak. Report per-node and total sizes without calling the whole protocol
  bounded-memory.
- Comparator mapping confirms `meshecho-dhr-flood-ack-delay` is the existing
  fixed-2-s F ACK and initial-R+15-s fixed-F recovery reference. The four
  DCB variants share source eligibility and on-wire nominee fields; SR-FR
  and LPR differ in feedback/source budgets and are contextual only. There is
  no existing fixed two-hop useful-DATA F arm: changing global `max_hops`
  would alter route budget, so it requires a per-F TTL control. The current
  five-arm runner cannot satisfy the draft's full comparator paragraph.
- A read-only count of the archived 46001--46020 stock actions gives 70 D,
  96 F, and 706 R source decisions. The flow export labels 64 D-candidate
  flows, of which 61 were source-ACKed by deadline (63 destination-delivered).
  These are selected, non-counterfactual groups and do not prove D's benefit;
  they do rule out casually removing D as an obviously harmless core rewrite.
  A proposed no-D source rule remains an untested hypothesis and requires a
  matched source-decision ablation and action-divergence report.
- The audited short-R-guard control already tested 1/2/4/8 s against the
  inherited 15 s and found no reliable ACK improvement, with +2.48% to
  +4.29% whole-network airtime. A new source core cannot use an earlier
  fixed-F timer alone as its novelty/benefit argument; a certificate-aware
  guard needs a fresh matched control and cost evidence.
- Independent review of the new DCB observability slice found its live peak
  counters and TX request/start binding non-perturbative, but `state.jsonl`
  peak values are only range/sum checked, not reconstructed from transitions.
  Request time is also stored beside TX rather than in an independent
  committed-request artifact. Improve both provenance checks before freeze;
  document nearest-rank p95 and final=peak for the add-only seen set.
- The observability re-audit later found no scoped P1/P2: separate committed
  request records join contiguous physical TX IDs; live state transitions
  independently replay the feedback/pending peaks; accepted marked ACK time
  equals the flow's first ACK time. Nonreserved stock/new-recorder TX,
  outcomes and RNG states matched. The full post-observability regression
  passed 1011 tests with one skip; no reserved cohort was opened.
- The new fixed-two-hop-F control uses a useful-DATA F TTL hook only: source
  initial and recovery F are capped at two hops while RREQ discovery remains
  at the case's six-hop budget. A DCB-wire source-FR control changes only
  D-triggered source decisions and preserves nominal F ACK/R DATA bytes in a
  tested F-to-R flow. SR-FR and LPR are contextual, not equivalent budgets.
- A two-hop F control must also use its own two-hop FLOOD/ACK bound for
  deadline admission. The inherited `rescue_round_trip_bound_s()` had
  estimated `sim.max_hops` and could reject an otherwise feasible recovery
  near the deadline. The corrected bound uses `useful_flood_ttl()` for FLOOD
  serialization while preserving the R-path bound and RREQ hop budget;
  a real deadline-edge flow now recovers. This is a comparator fairness fix,
  not evidence for or against a new source algorithm.
- The previously drafted DRC deadline-reservation core was explicitly
  rejected before population runs: zero of 559 route-bearing initial
  actions entered its reserve-caused F-first branch, so rewriting around
  that branch would not create a meaningful source action change in the
  current case. Source-only ACK-risk screening also remained NO-GO because
  the prior-miss cells were sparse and it did not estimate F/R/D treatment
  effects. These records rule out presenting a shorter fixed guard, hop
  threshold, or old route-age feature as the requested algorithm rewrite.
- A future core should be selected by device-local feedback plus charged
  action differences against same-wire controls. In the 46xxx passive
  archive, 61/64 selected D-candidate flows were source-ACKed; removing D
  without a paired causal D ablation could discard an effective mechanism.
- In the tiny nonreserved 49101--49103 DCB-versus-fixed-F pilot, all three
  per-seed ACK and destination counts matched exactly, while only 49101 had
  any DCB backup starts (two). Airtime changed sharply in that one seed and
  was nearly tied in the other two. This motivates testing exposure and
  full-network cost on a frozen larger cohort, not an airtime or ACK claim.
- A read-only 46xxx source-state reconstruction rejects the naive
  `direct-no-fresh-certificate => F` rule: among 144 true initial direct-R
  decisions, 45 lacked an offline-reconstructed <=120-s certificate, yet
  39/45 were source-ACKed and 44/45 delivered. Their observed target-flow
  airtime was 69.966592 s; substituting the cohort's descriptive initial-F
  mean would suggest 106.7958 s, a noncausal +36.83-s cost warning. The
  actual stock ACK had no nominee, so the 99 candidate-certified rows are
  reconstructed offline, not source-visible trial outcomes. Of 70 D
  decisions, 67 were aging and three cold; 66/70 were source-ACKed. Keep
  D and test any source branch against same-wire F/R/D controls.
- Replaying only inspected 49101 as a mechanism diagnostic found accepted
  backup ACKs for flows 20 and 24 on pair (0,29), with later same-pair
  applications at flows 28, 32, 36, 40, 44, 48 and 52. DCB used 11 fixed-F
  recovery starts versus 19 under the fixed-2-s F arm, but its initial
  actions also differed (3 vs 1 D), so the observed one-seed airtime gap
  cannot be attributed solely to the two backup starts. This is a reason
  to test ACK-proven promotion, not evidence that it helps.

## 2026-10-05 Source-Core Clarification

- DCB's conditional relay and the new `meshecho-dcb-promote` route commit
  change feedback/route state, but `MeshEchoSR.send_app` still supplies the
  F/R/D choice and DHR retains a 15-s fixed-F rescue. Neither component is
  the requested complete source decision algorithm rewrite.
- A valid marked backup ACK certifies one two-hop success. It does not
  distinguish direct DATA loss from direct ACK loss, so unconditional route
  promotion may raise later airtime. A future source rule needs a locally
  available discriminating signal or must beat same-wire no-promotion and
  simple switching controls without relying on that distinction.
- Latest post-promotion regression: 114 focused tests and 1020 full-suite
  tests passed, one skipped; no fresh causal cohort was run.
- A new public overlap trace reproduced stale blind promotion: flow 3's
  direct ACK arrived before flow 2's delayed backup ACK, but flow 2 still
  replaced the direct route. The fix tracks the most recent accepted direct
  ACK flow in source-owned destination state; the red test now passes.
- A destination-local direct-receipt status flag is implementable but has
  no demonstrated discriminating exposure in the 46xxx passive archive:
  those traces have no actual backup ACKs, and the three-seed 491xx pilot
  had only two backup starts. Defer the flag; it cannot reduce the already
  sent backup DATA and would require bounded local receipt state and
  same-wire controls. The draft ACK-gated trial policy is a hypothesis,
  not a measured improvement.
- The new trial source controller has physical divergence from inherited
  SR: no proactive age-D, F after one unresolved R miss, and a one-flow
  two-hop trial after a marked backup ACK. Independent concurrency review
  found three P1 paths, all reproduced by public tests and corrected:
  stale backup ACK ordering, active-trial overwrite, and a nontrailing
  unresolved R miss. Additional tests distinguish a late abandoned-trial
  ACK from a newer queued direct ACK. These are protocol correctness
  observations, not effect estimates.
- `r_miss_flows`/`f_miss_flows` and flood seen sets are not memory-bounded;
  the existing eight-destination LRU cannot justify an MCU-memory claim.

## 2026-10-06 - Algorithm-Rewrite Boundary Reconfirmed

- The correct scope is a **core protocol rewrite on a preserved physical
  substrate**, not a wholesale rewrite of the simulator. Reusable layers are
  the LoRa PHY/ToA model, channel/collision model, event queue, packet and
  forwarding mechanics, ACK transmission, energy accounting, and evidence
  ledger. Replacing those would invalidate matched controls and make old
  MeshEcho-SR comparisons difficult to audit.
- The old source policy is not being treated as tunable CPR. The DRC
  successor already failed its predeclared development cost gate (+32.2%
  mean TX airtime versus no-rescue), so changing only guard/TTL/margin would
  be post-hoc tuning rather than a defensible new algorithm. DRC remains a
  sealed negative control.
- CPR is therefore a new source/recovery state machine: initial route/FLOOD,
  one physically started same-path repeat (marker 1), then at most one
  deadline-gated recovery FLOOD (marker 2), with physical ACK cancellation
  of uncommitted relays. This is the algorithmic rewrite; it is layered on
  the preserved PHY and ledger.
- CPR is not yet paper-ready. A delayed marker-2 ACK from an older overlapping
  flow can currently overwrite a newer same-pair route commit. The fix must
  use a captured route-generation/epoch admission check, not merely numeric
  flow IDs. Also, `meshecho-cpr-nocancel` currently shares a bounded relay
  ledger whose eviction can silently cancel pending FLOODs, so that ablation
  is not yet strict.
- CPR action evidence also needs a generation/epoch and request/TX join (or a
  validator that reconstructs it from the flow and physical ledgers). Accepted
  ACK provenance must include both pre-commit and post-commit route
  generations. Do not run confirmatory cohorts or revise the ICC paper until
  stale-ACK rejection, quarantined-route admission, no-cancel semantics, and
  bounded-state evidence tests pass.

## 2026-10-06 - CPR Correctness Repair 1

- Added destination-specific route-generation tombstones to the standalone
  source state. CPR now snapshots the epoch at initial admission and at
  recovery start; marker-none/marker-one/marker-two ACKs are rejected when a
  newer same-destination commit has occurred.
- CPR initial admission now requires `RoutePhase.READY`; a quarantined route
  is not used for routed DATA. Deadline expiry records the first current
  routed miss and mirrors the quarantined state to the protocol cache.
- `_cpr_start_recovery` now constructs a `CprObservation` and invokes the
  public `choose_recovery_action` controller. A stale route or an infeasible
  bound produces a no-start decision.
- Accepted CPR ACK provenance is linked by its event ID and records both the
  pre-commit epoch and the post-commit generation. CPR decision events expose
  route and recovery epochs for independent joining.
- The no-cancel shadow no longer enrolls ACK-cancellable relay records. Relay
  ledger eviction is explicit and returns evidence; the candidate records
  capacity eviction rather than silently hiding it.
- New red/green tests cover quarantine admission, stale recovery ACKs,
  controller usage, post-commit ACK provenance, and non-canceling ledger
  eviction. CPR/DRC focused regression passed `32` tests; CPR controller and
  runner tests passed `15` tests together.

## 2026-10-06 - CPR Mechanical Smoke 92010

- The fresh nonreserved seed `92010` completed through the disk-backed CPR
  runner and independent validator. The bundle contains four paired arms,
  16 scheduled flows, 86 request records, 59 physical transmissions, 472 RX
  attempts, and 10 accepted ACK records; every started TX has four RX rows and
  `incomplete_rx_tx=0`.
- The smoke is mechanism evidence only. It is not a development gate, a
  population estimate, or ICC evidence. Its one-seed CPR result is retained
  for audit and cannot be used to select a holdout or rewrite the paper.

## 2026-10-06 - CPR Evidence v2 Smoke 92011

- After adding action-to-request/TX joins, the evidence schema was bumped to
  `meshecho-cpr-evidence-v2`. Fresh seed `92011` passed the v2 validator with
  four paired arms, 16 scheduled flows, 89 requests, 62 TXs, 496 RX attempts,
  10 accepted ACKs, and zero incomplete TX/RX joins.
- The displayed one-seed metrics (CPR 1.0 ACK/delivery PDR and 1.892352 s
  airtime versus 0.5/5.281792 s in its controls) are smoke-only and are not
  interpreted as a treatment effect.
# 2026-10-06 - CPR Exploratory Resume

- The current goal remains a full MeshEcho-SR core rewrite, fair causal
  simulations, and a major ICC paper revision only from validated artifacts.
- The previous context boundary was recovered with no session-catchup report;
  the authoritative state is the existing `task_plan.md`, `findings.md`, and
  `progress.md` continuation sections.
- Independent architecture review agrees that the algorithmic core must be
  replaced, but the PHY/ToA/channel/event/forwarding/ACK/energy substrate must
  remain fixed for fair paired controls. CPR is a successor source/recovery
  policy, not a claim of a wholly new routing stack.
- CPR evidence-v2 smoke and the focused/full tests are implementation and
  integrity evidence only. No CPR population effect, ICC result, VERSION bump,
  GitHub push, or EDAS action is authorized yet.
- Next action is to freeze and run the fresh `92020..92029` exploratory matrix;
  all seeds are distinct from smoke `92010/92011` and DRC `610xx/620xx/630xx`.
- The first run exposed a runner path-normalization defect: `run_matrix()`
  hashed a relative contract path under its absolute label, while
  `audit_artifacts()` resolved the manifest path and expected a repository-
  relative label. The resulting bundle failed closed at source-hash audit;
  no performance result was accepted.
- The defect was fixed at the source by normalizing the contract path before
  hashing and by adding `--contract-path` to the runner. A regression test now
  writes and audits an external contract, and a direct relative/absolute hash
  equivalence check passes.
- Seed `92024` exposed a validator assumption rather than a malformed packet:
  the accepted ACK for flow 4 follows reverse path `[6, 2, 5]`, so relay `2`
  transmits the physical ACK that is accepted at source `6`. The validator's
  `sender == destination` check is wrong for multi-hop ACKs; the correct join
  uses ACK origin/final destination, reverse path, reverse hop, and matching
  packet path index.
- The validator was corrected with a public seed-`92024` regression. The
  second invalid exploratory bundle is retained under
  `results/invalid_cpr_multihop_ack_20261006/`; no metrics from either failed
  bundle enter the exploratory decision.
