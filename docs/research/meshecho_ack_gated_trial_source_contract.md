# MeshEcho ACK-gated trial source controller

Date: 2026-10-05. Status: draft, untested full-core candidate. This is not
an ICC method, a measured gain, or a novelty claim. It does not authorize
reserved 47xxx/48xxx runs, manuscript result changes, a version bump, or
GitHub/EDAS action.

## Reason for this candidate

The existing DCB relay and ACK-proven route promotion do not replace SR's
F/R/D source selector. Blind promotion also treats a successful two-hop
backup ACK as if the direct DATA failed, although the direct DATA may have
arrived and only its reverse ACK failed. The proposed controller uses that
ACK solely to authorize one reversible route trial. It needs no new wire
field beyond DCB's already charged relay, epoch and repair marker.

The proposed destination-local `seen/not-seen/unknown` flag is deferred:
the 46xxx passive archive had no actual backup ACK and no demonstrated
`seen` backup opportunity. A flag may later be studied in a separate,
same-wire factorial test; it is not a prerequisite or assumed benefit here.

## Source-owned state and actions

Each source-destination record remains within the existing eight-entry
source LRU. Add at most one pending `(two-hop path, backup ACK flow,
confirmed-route generation)` trial and at most one active trial flow per
record. The source may use only its own route cache, accepted ACKs, local
transmission/timeout events and packet fields. The simulator's global
delivery outcome, true link PRR, remote queue, and future events are not
protocol inputs.

The inherited `r_miss_flows`, `f_miss_flows` and flood seen sets are not
bounded in the current simulator. The eight-entry destination LRU only
bounds the number of pair records, not their total bytes. This draft makes
no whole-protocol MCU-memory claim; a bounded history implementation and
parity/sensitivity tests are required before such a claim.

On the first valid, in-deadline marked backup ACK for a direct nominated R
flow, record the ACKed two-hop path as a pending trial only if the direct
route and its F certificate generation still match. A newer accepted
direct R ACK, a newer pending backup ACK in the same generation, an active
trial, or any newer committed route wins over this older evidence.
Recording a trial does not change the confirmed route cache.

For the next application, choose at enqueue using this order:

1. No live ACK-confirmed route: initial useful-DATA F.
2. Live pending trial for the current route generation: consume it and
   send exactly one initial R DATA over the two-hop trial path, but never
   while a prior trial for this pair is active.
3. Otherwise, one unresolved initial-R source ACK miss in the current
   route generation: initial useful-DATA F.
4. Otherwise: initial R DATA on the confirmed route.

This replaces the old proactive D/token/180-s route-age branch and the
two-consecutive-R-miss F trigger. It deliberately retains the already
tested 15-s, deadline-admitted same-flow fixed-F recovery as a component,
not as new timing novelty. A candidate-route D action may be removed only
after same-wire DCB and no-D controls show that removal does not sacrifice
reliability; archived D successes are not a causal counterfactual.

An ordinary, first accepted R ACK on the active trial path commits that
path as the new confirmed route generation and clears the old direct F
certificate and miss history. An unACKed trial at its guard discards the
trial; the current same-flow F recovery remains eligible, and the next
application uses F unless a newer ACK has committed a route. An accepted
F or F-recovery ACK commits its own observed path and invalidates any older
trial. A newer direct R ACK from an already queued flow may supersede an
older trial commit, but an abandoned trial's late two-hop ACK may confirm
its application flow without committing the abandoned path. Late,
duplicate, wrong-sender, wrong-path, wrong-epoch or older backup ACKs
never create or commit a trial.

## Required falsification and controls

Public end-to-end tests must show: backup ACK creates a pending trial but
does not commit; the next R physically uses exactly that two-hop path;
its ordinary R ACK commits; its ACK miss reverts to F; a newer direct R ACK
suppresses an older backup trial; route expiry, source-state eviction,
wrong generation and deadline prevent stale use. Test one source decision
that differs from the inherited age-D rule and one that differs from the
two-R-miss rule. The same scheduled flows, original 30-s deadline, packet
length and physical TX accounting must hold for each comparator.

Controls include unchanged DCB, DCB-wire source-FR, blind promotion,
same-source-rule no-trial, and fixed-2-s useful-F. DCB-wire one-miss-F and
old-D controls isolate the source selector; contextual two-hop-F and
LPR-like arms cannot be called same-budget mechanism controls. Report
backup ACK exposure, pending/attempted/ACKed trials, initial F/R/D and
path divergence, per-seed all-flow source ACK and destination PDR, and
complete-network airtime/energy, queueing and collisions. Freeze exact
inputs and quantitative gates before any reserved smoke, development or
untouched holdout. Reject or redesign this controller if its trial branch
is too rare, its paired gains fail, or simpler same-wire controls match it.

## Proposed trial-core gate before the reserved cohorts

This is an author-chosen research threshold, not an ICC acceptance rule.
It remains draft until a separate pre-freeze audit checks the code, controls,
and artifacts. Use equal-weight per-seed paired two-sided 95% intervals over
all scheduled unicasts, not pooled exposed flows. For airtime, each seed's
contrast is `T_trial/T_control - 1` using complete-network TX airtime.
Development has exactly 20 seeds (47001--47020); an unchanged rule must
pass the same gate on the once-only 40-seed holdout (48001--48040).

| Control | Source-ACK lower CI | Destination-PDR lower CI | Airtime requirement |
| --- | ---: | ---: | --- |
| Same-source no-switch | greater than -0.02 | greater than -0.01 | upper CI below zero, mean at most -0.02 |
| Same-source blind switch | greater than zero | greater than -0.01 | upper CI below +0.05 |
| Old DCB F/R/D selector | greater than -0.02 | greater than -0.01 | upper CI below zero, mean at most -0.02 |
| Fixed-2-s F ACK/recovery | greater than -0.02 | greater than -0.01 | upper CI below zero, mean at most -0.05 |
| Current-packet overhearing | greater than -0.02 | greater than -0.01 | upper CI below zero, mean at most -0.02 |

The blind-switch row chooses a reliability advantage as the reversible
trial's specific claim; do not replace it with an airtime alternative after
looking at 47xxx. Require at least 20 physically started trial R flows in
at least ten seeds, ten ordinary trial-ACK route commits in at least five
seeds, and ten source-guard abandonments followed by path or action
divergence from blind in at least five seeds. Also require 20 initial F/R/D
decision differences from old DCB in at least ten seeds and zero invalid
accepted backup ACKs or trial-action provenance events. Physical starts,
ACKs, and post-abandonment decisions must be joined to saved packet/flow
artifacts rather than inferred from intent logs alone.

The old DCB component gate must remain separately reported. Only a new
`trial_project_gate`, conjoining the table, exposure and provenance, may
authorize a trial-core holdout; a successful old DCB component gate alone
cannot do so. If development fails, do not tune this candidate on 47xxx
and call a rerun confirmation. The ten nonreserved 492xx public screen is
an exploratory feasibility check, never an input to an ICC effect estimate.
