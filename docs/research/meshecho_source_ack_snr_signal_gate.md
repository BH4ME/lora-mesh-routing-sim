# Source-local ACK-quality signal gate (SINR primary)

Date: 2026-10-04. Status: frozen for 43200 mechanical smoke only; exploration
and validation remain unauthorized. This is an observational
signal test, not a new MeshEcho algorithm, counterfactual F/R result, or
ICC claim. It uses the current fixed-2-s single-FLOOD-ACK DHR policy and
retains its packet bytes, source rules, 30-s application deadline and
radio/traffic configuration unchanged.

## Research question and prior-art boundary

Does the post-interference quality of an ACK accepted by a source on its
current confirmed route predict failure of the next initial R transmission
to receive its own R ACK by the 15-s guard, beyond path hop count, recent
ACK misses and the age of that ACK? This is more directly source-visible
than the destination-side first-edge q signal and needs no packet byte.
It may still be biased because only successfully decoded ACKs yield RxInfo.
Generic ACK/SNR link estimation and route adaptation are prior art; see
`meshecho_feedback_prior_art_boundary.md`. A positive signal would only
justify a prospective action experiment against simple SNR/ETX policies.

## Split and passive capture

Reserve 43200 for one mechanical smoke; 43001--43020 for exploratory
training; 43101--43120 for untouched signal validation only after smoke,
strict parity/replay, input freeze, and both pooled exploratory support
and at least one claimed path type's exploratory support gates.
These are disjoint from 42xxx and previously reserved 35001--35040/
36001--36040. Seed 43000 was inadvertently replayed once while auditing
an untrusted manifest; its result was neither saved nor used, but it is no
longer an untouched smoke seed. The new 43200 smoke seed was checked absent
from code/doc seed plans and result filenames before preregistration. The
first source/contract freeze authorizes only the 43200 smoke; no exploration
or validation seed may run without its own stage authorization. Record
the exact source, test,
contract and case hashes before 43200, and preserve each split's own
manifest, hashed artifacts and link to its prerequisite manifest.
After an independent smoke artifact/replay audit, exploration may receive
a separate immutable JSON authorization file. Validation may receive a
different authorization only after the independent exploration audit and
the prespecified support gates pass. Neither file is part of `SOURCE_FILES`:
creating a later approval must not change the frozen smoke input hashes.
Each authorization has exactly `mode`, `seeds`, `protocol`, `case_sha256`,
`application_deadline_s`, `source_sha256`, and
`prerequisite_manifest_sha256`. `mode` is `explore` or `validation`;
`seeds` must equal the exact reserved cohort; `source_sha256` must equal
the frozen input map; the predecessor map must contain the actual smoke
manifest hash for exploration, and actual smoke plus exploration manifest
hashes for validation. The runner takes `--stage-authorization` for the
current stage and also `--explore-authorization` for validation. It rejects
missing/mismatched permits before any seed or predecessor replay, stores
the current permit's byte hash in the report/manifest, and requires the
actual permit file when independently validating a later-stage manifest.
Validation also checks the saved exploration permit hash before replay.
Do not modify or replace a permit after its cohort starts.
An independent manifest validation must receive and audit the actual smoke
manifest for exploration, and both actual smoke and exploration manifests
for validation; the recorded predecessor hashes and frozen exploration fits
must match those verified files, not only fields within a validation report.
For each real split, explicitly authorized independent validation also
reruns the declared seed
and case under unchanged frozen sources and compares its complete
JSON-normalized diagnostic record, so a self-hashed report cannot merely
rename a synthetic trace as a reserved-seed run.
Merely reading or inspecting a real manifest must not start a seed;
`validate_manifest` requires an explicit replay flag before real validation.

Instrument the successful return of the simulator's **single** physical
`try_receive(tx, receiver)` call. For an ACK physically decoded at its
intended source, record `(seed, flow, source, destination, packet path,
repair_index, physical_sender, TX ID/end, RxInfo.sinr_db,
RxInfo.snr_db, RxInfo.collided)`. The `collided` flag is an offline audit
field only. The primary q feature uses `sinr_db`, the simulator's
post-interference reception-quality proxy on a successfully decoded
packet. The clean `snr_db` excludes interference and is saved only for
offline sensitivity. Neither field is proven equivalent to an actual
LoRa modem's reported packet SNR. Never call the receive model a second
time, consume new random draws, or use coordinates,
true PRR, fading state, future traffic, destination delivery or the
`collided` flag as a policy feature. The accepted `dhr_source_ack_rx`
action does **not** log a path: join it to exactly one source-facing ACK
TX with end equal to action time (tolerance 1e-7 s), matching seed,
flow/endpoints/repair marker, `path_index=0`, `final_dst=source`, and
sender equal to packet path `P[1]`; derive P from that TX. Reject an
ambiguous or missing physical-action join, and require the ACK to pass
the inherited identity/deadline acceptance rule. Off-index, late,
invalid and duplicate decodes remain audit rows but cannot update the
source feature history.
Record and compare digests of both RNG states and require exact stock/passive parity for the
complete metrics row, scheduled-traffic hash, every flow/action/TX row,
and original packet bytes. Strictly replay every opened seed.
The direct passive-diagnostic entry point rejects reserved research seeds
unless the frozen runner passes its private in-process capability after
contract and predecessor checks. This guard prevents accidental direct
calls; Python module privacy is not a security boundary against code that
intentionally imports private symbols.

## Decision-time population and label

Include every unique initial `decision=R` with one unmarked source DATA
physical start strictly before (`<`, not `<=`) its original enqueue+30-s
deadline. Do not include
an initial D that later falls back to R; do not relabel an R-to-F recovery
ACK as an initial R success. At the original decision event, select only
the most recent **earlier accepted** same-pair ACK on the currently
committed exact route **and in its current route generation**, whose
physical final sender is that route's source-adjacent `P[1]`. Give every
accepted route commit a new generation ID, including a recommit of the
same node sequence. The commit-triggering ACK belongs to the new
generation if it passes the physical-action join above; ACKs from all
older generations remain in the audit but cannot supply q, even if a
later generation returns to the identical path. Use action-list event
order when commit and accepted ACK share the same timestamp; test this
ordering against the real DHR callback. The current route is the path
chosen for this initial R DATA at the decision, verified
against its later physical TX; reject a path change between decision
and TX. Quantize the prior ACK's primary local quality margin as
`q=clamp(round(2*(sinr_db-required_snr_db(sf))),-126,126)`; retain its
actual age in seconds, the path hop count, route-generation prior R miss
indicator, and an explicit missing indicator (no arbitrary stale cutoff).
Set `prior_r_miss=1` only when the most recent earlier initial R in the
current committed-route generation timed out without a subsequently
accepted unmarked R ACK before this decision; otherwise set it to zero.
An accepted F/recovery-F/D-candidate route commit clears that history
and resets the route generation as defined above. No event at or after
the decision is a feature. The success label is an accepted unmarked R
ACK by both
`physical_R_start+15 s` and original enqueue+30 s. Separately report
destination delivery, later recovery, and why any R physical start or
feature join is excluded. An ACK timeout is not proof of forward DATA
loss. The primary denominator remains **all** initial R decisions with
valid physical starts; an eligible-feature subset is reported separately.
Report the missing-feature count, source-ACK outcome and path type for
the full denominator, not only the eligible subset. An eventual policy
must retain a predeclared fallback for missing q; this screen changes no
action.

For the separate later-recovery report, `later_recovery_attempted` means
that a same-flow source physical DATA (`repair_index=1`) or FLOOD
(`repair_index=2`) TX started after the initial R TX and before the original
application deadline, with a unique matching `dhr_recovery_tx` action.
`later_recovery_ack_by_deadline` additionally requires a physically joined,
accepted source ACK carrying the same repair marker after that TX and no
later than the original deadline. A guard decision or queued but unstarted
repair is not a physical attempt; a rejected or late ACK is not recovery
success.

Report direct and multihop strata, ACK age <=30 versus >30 s, source
ACK capture/interference and same-versus-different 60-s fading block.
The latter three splits use eligible rows only, report their own ACK
success/miss counts, and never alter the full denominator or primary gate.
`prior_ack_collided=True` identifies a successful ACK decoded despite
overlapping interference; same fading block compares the saved exact prior
ACK physical TX end with the next initial R's physical TX start using the
case's 60-s interval, without reconstructing TX end from ACK age.
The last two are offline diagnostics only; no model block index or hidden
failure cause enters a source policy. Prespecify an offline sensitivity
that replaces primary q with
`q_clean=clamp(round(2*(snr_db-required_snr_db(sf))),-126,126)` on the
same eligible ACK rows and repeats the same exploration-only M1/T fits
and validation scoring if validation opens. It cannot change the primary
SINR gate, rescue a failed screen or select a model/cut from validation.
If the prespecified clean-SNR fit itself fails, validation remains closed
because its required sensitivity score cannot be generated; clean-SNR
performance never supplies a GO when the primary SINR gate fails.
The simulator's clean SNR is pre-interference and must never be presented
as hardware-equivalent in interfered receptions. At current shared
power/noise and unordered-link fading, reverse ACK last-hop and forward
DATA first-hop **clean** SNR are reciprocal only within one block;
primary SINR is not, because interference can differ. Random reception
can differ too, and real hardware may be asymmetric.

## Frozen-before-data model proposal and stop rules

Before any new 43xxx seed, an independent review must freeze the fitting
implementation, tests, Python minor version and a bootstrap draw-sequence
fixture. On the eligible-feature cohort, predict
`Y=1` for **no initial R ACK by guard**. `M0` uses one-hop status,
route-generation prior R miss and `log1p(ACK_age/30)`; `M1` adds only
`q/12`. Fit each with a standard-library deterministic ridge logistic
solver minimizing the **sum**
`sum_i[log(1+exp(z_i))-Y_i*z_i] + 0.5*sum_{j>=1} beta_j^2`, with
`z_i=beta_0+sum_j beta_j*x_ij`. The intercept is unpenalized. `M1`'s q
slope is constrained `<=0`: fit unconstrained first; if its optimum has
positive q slope, fix that slope at zero and refit the other coefficients.
Initialize the intercept at `log((failures+0.5)/(successes+0.5))` and
slopes at zero. Use a 100-iteration Newton solver with deterministic
partial-pivot linear solve and backtracking steps `1,1/2,...,2^-30`
for Newton direction `d=-H^-1*g`, requiring `g^T*d<0` and the Armijo
condition `L(beta+step*d) <= L(beta)+1e-4*step*(g^T*d)` (equivalently,
an objective decrease `>=-1e-4*step*(g^T*d)`). Reject a nonfinite
objective/derivative, nonsolvable Hessian, non-descent direction or
failed line search. Stop at maximum free-coordinate absolute gradient
`<=1e-8`, otherwise fail rather than emit a model. For M1 with an
unconstrained optimum at `beta_q>0`, fix `beta_q=0`, refit the remaining
coordinates and check the boundary KKT conditions: maximum absolute
free-coordinate gradient `<=1e-8` and `g_q<=1e-8`. An interior M1 fit
requires `beta_q<0` and maximum absolute full gradient `<=1e-8`;
`beta_q=0` is accepted only with the boundary conditions. Failure of
either check is a fit failure, not a sign-clipped model. Use stable
log-sum-exp/sigmoid arithmetic. Test gradient/Hessian against finite
differences and coefficients and boundary KKT against independently
calculated frozen synthetic fixtures; NumPy is optional QA, not a
runtime dependency.

Before fitting, report eligible-row and both-label counts for every
exploratory seed and the pooled cohort. A seed with zero eligible rows
has no held-out loss, is omitted from exploratory leave-one-seed-out
folds and threshold selection, and remains in the coverage denominator;
it is never assigned an artificial score. If pooled exploration has
zero rows or only one label, or if removing any contributing held-out
seed leaves a one-class/empty training cohort, the screen is NO-GO:
do not fit M0/M1, select T, or open validation. Do not replace such a
fit with an intercept-only constant, seed exclusion or a different
split. For each exploratory seed with at least one eligible row, fit
M0/M1 on eligible rows from all other exploration seeds and record its
eligible-row Brier loss; this is a diagnostic, not final inference.
Choose a separate simple two-bin q-threshold comparator `T` from frozen
q cuts `{-12,-6,0,6,12}` by lowest equal-seed exploratory
leave-one-seed-out Brier. The lower bin is `q<=cut`, the upper `q>cut`.
Each fold fits its two failure rates on the other exploration seeds'
eligible rows with `(failures+1)/(records+2)`;
an empty bin is 0.5.
Break equal-loss ties by smaller absolute cut, then lower numeric cut.
After selection, refit M0, M1 and T's two bin rates on all exploration
seeds and freeze coefficients/cut/rates before validation. Never choose
a threshold, transform, endpoint or subgroup from validation outcomes.

Exploration support requires a valid same-route/source-neighbor ACK-quality
feature for at least 75% of all initial-R decisions and at least 200
eligible R records with at least 20 successes and 20 misses over at
least 10 seeds. At least one path type must also meet its own exploratory
support before the untouched validation cohort may open. Each path type
claimed for a follow-on controller needs, in **both** exploration and
validation, at least 80 eligible R records, 20 R-ACK successes, 20
misses, and 10 seeds.
Pooled validation also needs at least 200 eligible records, 20 successes,
20 misses and 10 seeds. Every pooled validation seed must have at least
one eligible record; zero eligible rows in any such seed are a validation
NO-GO before scoring, not an exclusion or imputation. A path-type
analysis uses all and only its contributing seeds (at least one eligible
row in that type) and must have at least 10; report zero-row seeds for
each type rather than adding them to the bootstrap. Average Brier
*within* each seed first, then average those seed values equally. For
paired improvement define
`Delta_0=Brier(M0)-Brier(M1)` and
`Delta_T=Brier(T)-Brier(M1)` on the same eligible rows. Use 1000
deterministic seed-resampling bootstrap attempts per statistic. Order
contributing numeric seed IDs ascending within each population, and
within a seed order rows by numeric flow ID then initial R DATA TX ID;
reject duplicate row keys. Use an independent Python
`random.Random(43000+10*s+m)` stream, where `s=0`
for pooled, `1` for direct, `2` for multihop, and `m=0` for `Delta_0`,
`1` for `Delta_T`, `2` for q-only AUC. For each attempt draw exactly `n`
indices by successive `randrange(n)` calls, where `n` is that
population's contributing-seed count; retain multiplicities. For each
Delta, average the sampled per-seed paired Brier differences, including
repeated seeds. For AUC, concatenate each sampled seed's eligible rows
with multiplicity and calculate one pooled rank AUC; ties count half.
A one-label AUC resample is invalid and is not replaced or redrawn.
For each statistic with `v` valid values, sort them ascending and take
nearest-rank percentile indices `ceil(0.025*v)-1` and
`ceil(0.975*v)-1` (zero-based; 24 and 974 when `v=1000`). Require at
least 950 valid attempts per reported statistic; a nonfinite Delta or
fewer valid attempts is NO-GO. Pooled validation requires both mean
improvements `>=0.005` and both nominal 95% lower bounds `>0`. A claimed
path type also requires its own `Delta_0` **and** `Delta_T` means
`>=0.005` and
both lower bounds `>0`, plus a seed-bootstrap 95% lower AUC bound
`>0.5` for the **q-only** risk score `-q`. A pooled-only gain authorizes
no path-type claim. Failure of all path types is NO-GO. These internal
necessary gates are not ICC criteria or corrected multiple-testing
claims. This screen does not claim superiority over ACK-history ETX;
that remains a mandatory later
action-level control.

Even a passing signal screen predicts only outcomes under an already
selected R action. It does not establish whether F, D, repeat-R or R-to-F
would deliver better, whether whole-network airtime falls, whether the
rule is novel, or whether it transfers outside the symmetric PHY model.
Before manuscript promotion, a new device-local joint contract and
fresh matched action experiment must beat fixed-2-s single ACK, equal-
budget repeat, fixed F/R, hop/prior-miss, simple SNR threshold, source-
local ACK-history ETX proxy and same-trigger R-to-F/R-to-R policies, then
pass an untouched holdout plus a separately frozen directional-link,
power/noise, fading-interval and load robustness design before any
general LoRa claim.
Define ACK-history ETX only from prior route-generation R attempts and
accepted R ACKs, never from future, true link PRR or destination truth.
