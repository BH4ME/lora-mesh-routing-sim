# MeshEcho-SR core rewrite checkpoint (2026-10-05)

## Latest verified 493xx decision (supersedes earlier prospective notes)

The once-only, nonreserved 49301--49310 seven-arm diagnostic archive passed
independent read-only integrity audit: 70 runs, 2,793 paired flow records,
16,935 actions, 35,574 physical TXs, all saved/source hashes and 54 paired
intervals reconcile; no out-of-window TXs were found. This is exploratory
mechanism evidence, not a frozen-core or ICC result.

Old DCB achieved 376/399 source ACKs with 500.36 s whole-network airtime.
D-to-R/F achieved 373/399 with 395.95 s; equal-seed relative airtime was
-20.97% (descriptive 95% interval [-30.88%, -11.06%]) but source ACK was
-0.73 percentage points ([-3.33, +1.87]), so reliability noninferiority is
not established. All 35 old D actions had candidate DATA and no discovery
timeout fallback; RREQ/RREP consumed 20.6% of old-DCB airtime. Trial and
blind had identical first physical actions/paths, ACK/delivery outcomes and
normalized physical TXs in this workload. A local trial patch is not a
demonstrated new algorithm. The trigger-F and source-FR controls also differ
in source-token/discovery-time bookkeeping, so their contrast is not a pure
physical-action effect.

**Decision:** reuse simulator, PHY, accounting and historical controls but
rewrite the source action, feedback interpretation and failure-recovery
decision core. First predeclare a common-prefix D/R/useful-F branch test
with matched bookkeeping and recovery budget on new nonreserved seeds;
then design a device-observable controller with an actual causal ablation
and prospectively evaluate it. Do not open 47xxx/48xxx or revise the ICC
manuscript/PDF, version, GitHub or EDAS on these exploratory results.
The audit interpretation is in
`meshecho_source_action_public_49301_49310_results.md`; the next
same-prefix branch experiment is a not-yet-authorized draft in
`meshecho_d_trigger_matched_branch_design.md`. Its candidate 49401--49440
range has not been run. The corrected source-visible accepted-ACK count is
32/34 aging-D triggers with an ACK younger than 120 s, so that threshold
does not presently identify a supported subgroup.

The first TDD implementation slice is now present in
`tools/diagnose_matched_d_trigger.py` and its focused tests. It provides a
target-only old-DCB D/R/F replay, equal D-trigger token/timestamp accounting,
role-keyed common-random-number streams, stable prefix/event serialization,
and fail-closed artifact helpers. This is diagnostic infrastructure only;
the new online source controller and paper results remain unverified. The
49400 mechanical smoke is the next gated action, followed by independent
artifact review; no 494xx seed has run at this checkpoint.

## Public trial screen and next decision

The prospectively specified nonreserved 49201--49210 five-arm screen ran
once. Its saved artifact is `results/meshecho_trial_public_49201_49210.json`.
It found 14 physical two-hop trials in eight seeds, 11 ordinary trial ACK
commits, and three source-guard abandonments. Exposure alone passed, but
trial and blind switch had zero physical action/path divergence and zero
source-ACK, destination-delivery, or whole-network-airtime difference across
all ten seeds. Trial versus old DCB saved 18.09% mean relative airtime while
losing 2.49 percentage points source ACK; these are exploratory means, not
confirmatory effects. Do not freeze this controller or claim trial advantage.

The runner now has an independent `trial_project_gate` rather than borrowing
the old DCB gate. Provenance-hardened DCB/runner tests pass 87 tests; the
latest full regression remains due. Diagnose the trial/blind identity and
redesign the device-local source action/recovery core with observable-only
inputs and same-wire controls. 47xxx/48xxx, ICC claims/PDF, VERSION, GitHub,
and EDAS remain closed. Preserve the dirty worktree.

The structural diagnosis is stronger than a low-exposure explanation.
After a marked backup ACK, blind promotion installs the two-hop route while
the trial arm stores it for one use; both next send the same two-hop R DATA.
An ordinary trial ACK makes their route caches agree. After an R guard miss,
both inherit the same R-miss flag and same-flow F recovery, masking the
different cached routes in the next source decision. This accounts for the
observed first-source action/path identity, not an unrecorded claim that
every physical TX was byte-identical. A new nonreserved interleaved-flow
fixture proves the two controllers can diverge when a second same-pair flow
starts before the active trial ACK: `tests/test_trial_blind_interleaving_witness.py`
passes. The recurring-fading population screen still shows no causal gain.

The next hypothesis is a device-local *selective split ACK corridor*: an
accepted F ACK certifies a direct route plus a two-hop nominee, a later
nominated direct R DATA reaches the destination, and the destination may
choose a charged ACK via that relay using only its current decoded-packet
quality. The relay's physical ACK reception suppresses its pending backup
DATA; a source ACK confirms the direct DATA route, not a two-hop forward
route. This is a candidate only. A read-only archived-exposure calibration
and exact same-wire controls are required before implementation/population;
generic SNR routing and alternate ACK paths are prior art, so no novelty
claim follows from this idea alone.

The authenticated 46xxx DHR archive subsequently showed only three
age-valid direct-DATA deliveries without an initial source ACK among 99
nominated direct R sends, and did not save current DATA SINR. This makes
selective split ACK a NO-GO as the next full core; see
`meshecho_selective_split_ack_triage.md`. The larger forward-failure
opportunity (36 age-valid nominee receptions in 17 seeds) is still only
passive. An independent action/flow/TX join counted 70 DHR D decisions,
67 age-driven, with 64 candidate DATA and 66/70 source ACKs; RREQ+RREP
used 205.987328 s, 19.0% of that archive's complete-network airtime.
This is DHR history, not a DCB ablation. The prospective nonreserved
49301--49310 seven-arm source-action diagnostic compares DCB's original
D with same-wire R/F replacements, including useful-data F at the exact
D trigger, before a new source rule is specified.

## 2026-10-05 trial-core resume

The unfinished commit-helper refactor had an unmatched `)` at
`lora_mesh_sim.py:3805`. It was reproduced by `py_compile`, fixed in place,
and the DCB/DHR/DBR/SR/airtime neighborhood passed 100 tests. Independent
review then reproduced two stale-generation defects (old R timeout after new
F commit; old active trial surviving new F ACK). Both have public RED/GREEN
timelines, and the fix was independently re-audited. Trial/no-switch/blind
runner arms and a nonreserved positive provenance fixture now pass. The full
post-behavior suite passed **1040, one skipped** in 163.69 s; two later
test-only route-expiry/LRU fixtures and the combined DCB/runner suite pass
78 tests. Compilation and `git diff --check` pass. Preserve the dirty
worktree. Causal advantage remains unknown, and the contract remains
**NO-GO** for 47xxx/48xxx, ICC results, VERSION, GitHub, and EDAS.

The subsequent read-only runner audit's suspected trial-abandonment P1 was
falsified on real physical traces; two new tests capture same-flow guard/F
recovery and cross-flow F commit, and 80 combined DCB/runner tests pass.
No audit rule was loosened. A trial-specific paired/exposure gate is drafted
in the trial contract but not implemented or frozen; the current staged
`project_gate` still gates only the old DCB component. A prospective
nonreserved 49201--49210 exploratory screen is specified, but not yet run.

## 2026-10-05 ACK-gated trial implementation checkpoint

This continuation made authoritative code/test progress. The previous
turn's 1020-pass regression was for the pre-trial tree, not the current
tree. The new draft `meshecho-dcb-trial` replaces old SR F/R/D selection:
no ACK-confirmed route -> F; one pending ACK-proven backup path -> one R
trial; unresolved R ACK miss -> F; otherwise confirmed-route R. It removes
the old age/token D branch. A successful ordinary trial R ACK commits the
two-hop path; the 15-s existing same-flow F recovery remains a component.
The same-wire `meshecho-dcb-trial-no-switch` variant ignores trial
nomination but has the same new source selector and DCB packets.

Public end-to-end RED/GREEN tests exposed and fixed: blind promotion by an
old backup ACK after a newer direct ACK; an old marked ACK replacing a
newer pending trial; two simultaneous trial flows; loss of an unresolved
older R miss after a newer R ACK; an abandoned trial's late ACK committing
its path; and a newer queued direct ACK not superseding an older trial
commit. The new source differs from stock on the 180-s D branch and one-R-
miss branch. Focused DCB/SR/DHR/airtime regression: **74 passed**; compile
and `git diff --check` passed. A full regression after these edits is still
required.

Independent audit identified remaining NO-GO items: inherited R/F miss
sets are unbounded despite the eight-destination LRU; the draft runner has
not yet integrated the trial and same-wire no-switch arms; and same-source
blind-promotion/old-D controls plus exposure/causal gates are incomplete.
The optional destination direct-receipt tri-state flag is deferred because
existing passive traces contain no actual `seen` backup ACK exposure.
Do not claim a bounded MCU implementation, algorithm advantage or ICC
novelty. No 47xxx/48xxx seed, paper/PDF, VERSION, GitHub or EDAS changed.

## 2026-10-05 source-core decision after route-promotion slice

The user's challenge is correct: DCB and ACK-proven route promotion are
components, not a replacement for the inherited F/R/D source controller.
`MeshEchoSR.send_app` still selects D from cold/aging rules, F after two R
misses or without a route, and R otherwise; DHR still makes a fixed 15-s
same-flow recovery decision. Keep the simulator, PHY, accounting, old SR/DHR
and DCB as infrastructure/controls, but specify and test a new device-local
joint source/feedback/recovery rule before claiming a core rewrite.

The latest promotion implementation passed 114 focused tests and the full
suite passed **1020 tests, one skipped** in 161.71 s; `git diff --check` is
clean. This establishes regression health only. A marked backup ACK proves
that the two-hop backup succeeded once, not that the direct DATA failed:
direct DATA might have arrived while its ACK was lost. Blind promotion can
increase subsequent airtime. No 47xxx/48xxx seed, ICC source/PDF, VERSION,
GitHub or EDAS was changed. The contract is still draft and NO-GO to freeze.

Next decision gate: define one explicit source action/recovery policy using
only device-observable state, with a same-wire no-promotion control and
simple F/R/D alternatives. Require action/path divergence, paired ACK and
delivery noninferiority, and charged complete-network airtime improvement
on fresh development before opening an untouched holdout or revising ICC.

## 2026-10-05 resumed-core update

The preceding answer-only goal turn was no authoritative-state progress.
This continuation revalidated the dirty worktree and planning files.
The two-hop useful-DATA F contextual arm had an unfair six-hop FLOOD/ACK
deadline bound; a public deadline-edge test was RED before a targeted fix
and GREEN after `rescue_round_trip_bound_s()` used the arm's actual useful
F TTL. R-path and global RREQ budgets remain unchanged. The focused suite
passed 19 tests and the complete suite passed **1017 tests, one skipped**
in 161.92 s; Python compilation and `git diff --check` passed. No 47xxx or
48xxx seed has run. Independent source-core design is in progress. DCB
still inherits the old source controller, the contract is draft, and paper,
PDF, VERSION, GitHub and EDAS remain unchanged. Next: define a genuinely
different device-local source decision rule and same-wire source controls,
then independent pre-freeze review before any reserved smoke.

## Latest continuation (after nine-arm observability/control work)

The full user goal remains open: redesign the core algorithm, run matched
causal simulations, and substantially revise the ICC manuscript only from
verified results. The user's question about reusing versus rewriting was
answered directly: reuse simulator/baselines, rewrite the decision core.
The immediately preceding question-answer turn made no authoritative-state
progress, so this continuation resumed the plan and preserved the dirty
worktree. `task_plan.md`, `findings.md` and `progress.md` have current details.

DCB now records per-committed-TX request time and physical start, nearest-rank
queue-wait p95 over starts by 630 s, and per-node feedback/pending/seen-set
peaks. Separate committed-request artifacts join contiguous physical TX IDs;
feedback/pending open/close events replay archived peaks; accepted marked
ACK events must coincide with first flow ACK time. Independent re-audit found
no scoped P1/P2 and checked nonreserved TX/outcome/RNG parity. The complete
post-observability suite passed **1011 tests, one skipped**; compilation and
diff whitespace checks passed. Later comparator edits have not yet received
a new full suite.

The draft DCB staged matrix is now nine arms: the five original component
arms, `meshecho-dcb-source-fr` with identical DCB feedback/nomination format,
and contextual two-hop useful-DATA F, ordinary SR-FR and LPR arms. Public
nonreserved tests show initial/recovery F TTL 2 without changing global
RREQ route budget and the DCB-wire source-FR decision/wire behavior. No
47000/47001--47020/48001--48040 seed has run. The contract remains **NO-GO
to freeze** because additional matched source/LPR-like controls and a full
new source algorithm remain absent.

Read-only stock 46xxx counts were 70 D, 96 F, 706 R decisions; 61/64
exported D-candidate flows were deadline source-ACKed. This is not a
counterfactual benefit estimate, but it makes a naive no-D rewrite risky.
Earlier audited 1/2/4/8-s R-guard controls increased airtime without
reliable ACK improvement. The DCB passive 5.528% opportunity is not a
measured treatment effect. Do not update ICC PDF, VERSION, GitHub or EDAS.
Next: verify the nine-arm edits with full regression and independent review,
complete control/algorithm contract, then consider freezing and one staged
mechanical 47000 smoke. A DCB component pass alone cannot prove the full
new source core.

## Latest continuation state (supersedes older prospective notes below)

**Pre-freeze decision: NO-GO.** An independent review found and helped fix
early DHR active-flow allocation before a future physical R start, a
past-event risk after the application deadline, and the direct-CLI
`__main__` authorization-token split. Public tests went red then green;
the adjacent DCB/runner/DHR/DBR/SR suite passed 264 tests, and the final
full regression passed 1007 tests with one skip in 162.48 s. The independent review also found that the
five-arm runner does not yet deliver every additional comparator promised
by the draft contract and does not report per-packet queue wait or peak
feedback/pending/seen-set state. Keep the contract draft and 47xxx/48xxx
cohorts closed until those gaps are resolved and a new audit passes.

The DCB protocol prototype and fail-closed five-arm staged experiment runner
are now implemented, but neither reserved 47000/47001--47020 nor untouched
48001--48040 has run. The contract remains draft pending an independent
pre-freeze audit. The full current test suite passed 1005 tests with one skip
in 162.00 s; Python compilation and `git diff --check` passed. This does not
establish protocol performance or novelty. The five-page ICC paper/PDF,
VERSION, GitHub, and EDAS have not been updated.

New public tests confirm 120-s nomination expiry, same-time ACK suppression,
wrong-sender and late-ACK rejection, and rejection of a marked backup DATA
whose request ID differs from its flow ID. The wrong-sender rejection is now
logged without changing radio decisions. The runner records all physical TXs
and rejects unproven accepted backup ACKs unless a matching destination
decode, relay backup TX, and reverse ACK chain are present. The independent
audit must report GO, then inputs/contract must be frozen and a distinct
authorization created before **one** 47000 mechanical smoke. Development and
holdout remain closed until their predecessor gates pass.

The scientific interpretation is unchanged: old max-min PRR scoring has no
demonstrated advantage over matched PRR-product, while DCB changes feedback
and relay decisions but inherits the old F/R/D source controller. The 5.528%
46xxx passive airtime bound only justified prototyping. DCB needs measured
same-budget gains and a prior-art distinction; otherwise redesign the core
again rather than update ICC from a negative candidate.

## Goal and current truth

The user requested a substantive MeshEcho-SR core algorithm rewrite,
simulation evidence and major ICC paper revision. Keep this objective
intact. The current five-page ICC LaTeX/PDF still present the old calibrated
max-min-PRR policy (version 2.1.26); neither a replacement algorithm nor a
new ICC result has been established. Do not update the paper's numeric
claims, VERSION, GitHub or EDAS from a passive screen or a candidate design.

The current worktree is intentionally dirty with prior research; preserve
existing files. `task_plan.md`, `findings.md` and `progress.md` are the
long-form recovery records. The prior 45001--45020 first-hop receipt screen
was NO-GO. The 42xxx and 45xxx archives are inspected exploratory history,
not validation. Sealed 35001--35040 and 36001--36040 remain unopened.

## Active candidate and next action

`docs/research/meshecho_destination_certified_backup_screen.md` specifies
an unimplemented candidate: an F ACK reports a destination-observed two-hop
backup; a later direct R DATA nominates that relay, which sends one early
copy only if it did not locally hear the destination ACK. IOMC (Sensors
2023, DOI 10.3390/s23083874) already has ACK-gated LoRa overhearing
relays, so the candidate needs a real distinction and an IOMC-like control.
An arm receiving the identical nominee, timer and ACK gate is behaviorally
identical and should only check parity; the real ablation uses local or
current-packet overhearing to choose a relay under matched byte/time cost.

Before any behavior code, complete a passive physical-reception observer
and tests with exact stock flow/action/TX/metric/RNG parity. The new
observer must measure whether the nominated relay decoded the *current*
R DATA and the destination's ACK, rather than infer this from older F
paths. The benefit gate was corrected before opening 46xxx: only stock
deadline-unACKed flows count toward possible ACK gain; stock-ACKed F
rescues may instead contribute to a charged airtime-substitution potential.
The candidate is cost-first with source-ACK noninferiority; physical
exposure and >=0.05 optimistic net whole-network airtime potential are
necessary before protocol coding. The already inspected 42xxx stock rows
have only 8/131 direct initial R flows deadline-unACKed and a broad
116.945152/999.575552-s marked-F/whole-network airtime pool among
stock-ACKed direct-R/F rescues. These are not candidate effect estimates.
The passive observer in `tools/diagnose_destination_certified_backup.py`
now computes the physical exposure, timing, and charged optimistic cost
screen. `tools/run_destination_backup_screen.py` implements an exact-scope
staged manifest/strict-replay runner; a separate read-only audit reported no
P0/P1 findings. The observer still changes no protocol behavior. A full
959-pass/one-skip regression, input hash freeze, and staged smoke preceded
the formal passive exploration.
Seed 46000 is reserved for one mechanical smoke and 46001--46020 for one
passive exploration, subject to frozen inputs and independent audit. A first
direct-script smoke attempt was rejected before topology because its
`__main__` authorization token differed from the canonical imported module;
it wrote no artifacts. A red subprocess regression and canonical-entry fix
passed the 959-test full suite. The old permit is invalid. The v2 46000
mechanical smoke then completed under the new permit; independent artifact,
parity, cost-arithmetic and strict-replay audit passed. Its manifest SHA-256
is `2481924958228b44686f1e5c2571175cdb94c15137a8748a8a04fdabe5b24b31`.
The one-seed 11.18% optimistic cost-substitution bound is not an algorithm
effect. A separate 46001--46020 exploration permit, SHA-256
`a4c046bd8bec1f7a6753ce539ff3682138397eb4723b2c92667655411d266ad9`,
passed independent pre-run audit. Its formal direct CLI completed once and
wrote the archive with manifest SHA-256
`c51e55cbac2c8a5ae00de23001f008b3402360c3357430ff212d0f213ed9a385`.
Local no-rerun manifest validation passed. The saved 2-s primary gate reports
36 exposed failed primaries across 17 seeds, 36 proxy-feasible flows, and
0.0552837 equal-seed optimistic net airtime substitution; both necessary
screen flags are true. This is a passive prospective prototype-permission
screen only, not a causal treatment or manuscript result. Independent
artifact/row/cost audit passed and independently reproduced the primary
gate. Details are in
`docs/research/meshecho_destination_certified_backup_explore_results.md`.
This is GO-to-prototype only, not a performance/novelty/ICC claim. No new
protocol behavior has been implemented.

If the passive gate passes, freeze packet/state semantics, implement the
new protocol test-first, compare with fixed-2-s F, same-field no-forward,
unconditional nominated relay, IOMC-like, first-alternate and other named
controls on fresh development, then a once-only untouched holdout. Rewrite
the ICC LaTeX and regenerate/inspect the PDF only from verified results.
If the gate fails, record NO-GO and choose a different device-observable
core instead of rebranding a control as a new algorithm.
