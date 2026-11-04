# MeshEcho-CPR algorithm specification for SECON 2027

Specification date: 2026-11-04. This document describes the saved executable
source snapshot
`e8d94c29b3797a55787ee8cc5a60c3d08b4949186f2250581ed36d851ef5b1a2`,
whose tested `VERSION` is **2.1.27**. The source is under
`results/secon2027/snapshots/<snapshot-id>/source/`; `snapshot.json` records
individual input hashes. All function and test references below refer to
that saved tree. A later release version must be mapped to this tested
snapshot by the release record; it does not change the version tested here.

Subsequent development repair: pilot v1 found that the invalid-route recovery
branch referenced an unimported `CprDecision`. The corrected pilot-v2 snapshot
`ee890e25030782fc01208ee4ce1f20863c6ade5322ac954ad67ae48b594056a2`
is tested as VERSION2.1.28 and adds the missing import plus an event-driven
regression; it changes no controller policy or budget. The original snapshot
above did not safely execute that rejection branch. The action enum remains
`DROP_DEADLINE_INFEASIBLE` with reason `stale-route-generation`; this reason
can occur while time remains, so diagnosis must not label it as deadline
shortage. Independent missing/quarantined/replaced/expired route fixtures
verify protocol-no-start without new TX/airtime; READY recovery still starts.

This is an implementation specification, not a performance report. Its scope
is the unicast simulator policy and the explicitly named controls. There are
no hardware measurements or firmware-equivalence results in this document.
Bounded retries, route caching, flooding and duplicate suppression have prior
art. In particular, retry followed by flooding is not claimed as a new idea;
the pinned upstream comparison and limitations are in
`secon2027_baseline_fidelity.md`. The research question concerns this precise
combination of deadline admission, message confirmation, cache evidence and
pre-commit relay cancellation under the declared model.

## 1. State, identity and timing

An application flow is identified by a unique simulator flow ID `i`, source
`s_i`, destination `d_i`, enqueue time `a_i`, and deadline

\[
D_i=a_i+\Delta_i. \tag{A1}
\]

The source registers every scheduled application flow with the metrics layer
before attempting admission. A source has at most eight active controller
flows. Capacity rejection or failure to start a packet therefore does not
remove the application from the scheduled denominator.

The controller stores the initial action and path, captured cache generation
and confirmation revision, stage request flags, stage start timestamps, and
the terminal ACK timestamp. Stage markers are `None` for the initial packet,
`1` for a same-path repeat, and `2` for a recovery FLOOD. CPR sets
`request_id = flow_id`. These markers distinguish stages of the same message;
they do not create new application flows or reset the deadline.

Three times must remain distinct for each radio request `q`:

- `r_q`: creation of a queued request by `transmit_later`;
- `k_q`: processing of its `tx_request` event and, if admitted, commitment;
- `t_q`: reserved physical transmission start after earlier local sends.

If the sender's current reserved busy-until time is `b_v`, the simulator uses

\[
t_q=\max(k_q,b_v),\qquad e_q=t_q+T(p_q). \tag{A2}
\]

At `k_q`, `begin_transmission` first checks the pending handle and optional
guard, then passes `t_q` to the protocol hook. An admitted request becomes
committed immediately, receives a TX ID and a physical interval `[t_q,e_q)`,
and advances `b_v` to `e_q`. Thus `k_q < t_q` is possible. A later ACK can
cancel only an uncommitted handle, even if a committed packet has not yet
reached its reserved start. The `on_transmit` callback runs during this
reservation operation with the physical start/end timestamps; it is not a
separate event at wall-clock `t_q`. Stage start fields contain those timestamps,
and source ACK validation rejects an ACK earlier than its corresponding
recorded start.

The event priority table processes `tx_end` and its decoded receptions before
equal-time timers, then processes new TX requests. An eligible ACK at exactly
`D_i` can therefore complete the flow before its deadline timer. Starting a
new source stage at exactly `D_i` is forbidden. These are simulator ordering
rules, not claims about real interrupt timing or clock synchronization.

## 2. Wire cost and local admission budgets

Let `P` denote application payload bytes, `n` the number of node IDs carried
in the path, and `m` the optional stage marker. In CPR's emitted wire forms,

\[
L_{\mathrm{DATA/FLOOD}}(n,m)=12+2n+P+\mathbf1[m\ne\varnothing],
\qquad
L_{\mathrm{ACK}}(n,m)=12+2n+\mathbf1[m\ne\varnothing]. \tag{A3}
\]

The common header has ten bytes; a nonempty path adds one count byte, one
index byte and two bytes per node. CPR's request ID equals its flow ID and
does not add the four-byte RREQ/RREP extension. Cache generation and
confirmation revision are local state, not extra CPR wire fields. The generic
packet class can represent other optional extensions, but the CPR forms in
A3 do not emit them. This custom model is not an implementation of either
product's complete framing, encryption or authentication overhead.

For a full modeled frame length `L`, `RadioConfig.toa_s_for_bytes` computes

\[
T_{\rm sym}=2^{SF}/BW,
\quad
N_{\rm pay}=8+\max\left(0,
\left\lceil\frac{8L-4SF+28+16C-20I}{4(SF-2DE)}\right\rceil(CR+4)\right),
\tag{A4}
\]
\[
T(L)=(N_{\rm pre}+4.25+N_{\rm pay})T_{\rm sym}. \tag{A5}
\]

Here `C` is the CRC indicator, `I` is one for implicit header and zero for
explicit header, and `CR` is the coding-rate index (one means 4/5). This
implementation sets `DE=1` when `SF >= 11` and `BW <= 125000`, otherwise zero.
Physical charging uses `packet_toa_s(packet)`, which supplies the complete
wire length to A4–A5. The legacy payload-only `toa_s` property is not the
per-frame cost used for this evidence ledger.

For a cached path `p` with `h=|p|-1` hops and safety margin `epsilon`, the
local source uses

\[
B_R(p,m)=h\,[T(L_{\rm DATA}(h+1,m))+T(L_{\rm ACK}(h+1,m))]+\epsilon.
\tag{A6}
\]

Initial routed admission uses the unmarked form `m=None`. Repeat admission
and both repeat observation timers use the marked form `m=1`. Let `H` be
the configured maximum hops and `b,j` the FLOOD base delay and jitter width.
The FLOOD budget is

\[
B_F(m)=H\,[T(L_{\rm FLOOD}(H+1,m))+T(L_{\rm ACK}(H+1,m))]
 +(H-1)(b+j+0.35)+\epsilon. \tag{A7}
\]

The budget intentionally sizes a synthetic maximum-length path. Actual
FLOOD frames carry their accumulated path and are charged at their actual
length. An action fits when

\[
\operatorname{fits}(t,B,D)\iff t<D\ \land\ t+B\le D. \tag{A8}
\]

A6–A8 are deterministic, locally computable admission and observation
budgets. They do not bound all relay queues, interference, losses or ACK
return delays. In particular, A7's nominal forwarding allowance is the
literal code expression; configurable timer floors or unusual parameters
must not be used to infer a universal end-to-end guarantee. A decision to
admit a packet is not a guarantee of delivery before the deadline.

## 3. Source state machine and finite source bounds

At the initial request opportunity, the source records the current
destination epoch. It uses a cached path only if that record exists, remains
READY and unexpired at the proposed start, and A8 holds for its unmarked
route budget. It then records `R_INITIAL`, saves the path and its generation
and confirmation revision, and emits unmarked DATA.

Otherwise the source attempts `F_INITIAL` if its unmarked FLOOD budget fits.
This branch includes an absent, expired, quarantined or infeasible cached
route; “cold” below denotes this initial-FLOOD branch and need not mean the
destination has never been contacted. The initial FLOOD carries path `(s_i,)`
and its source seen key is installed before transmission. If neither action
fits, the request emits no radio frame and the flow remains in the denominator.

For full CPR after an initial routed DATA start `t_0`, let
`B_1=B_R(p_i,1)`. The source schedules its repeat observation at
`min(D_i,t_0+B_1)`. At that time it requests one repeat only if the flow is
still live and unACKed. At the repeat's actual proposed start `t_1`, it checks
the deadline again and requires the saved route's generation still to be
READY and unexpired. If admitted, it emits DATA on exactly the initial path
with marker `1`. A failed repeat admission does not silently skip to FLOOD.

After the repeat has a recorded physical start `t_1`, the source schedules
its recovery observation at `min(D_i,t_1+B_1)`. If still live and unACKed,
it can request one recovery FLOOD. Recovery admission at `t_2` again requires
the same current READY route generation, no previous recovery start, and
`fits(t_2,B_F(2),D_i)`. It captures the destination epoch, emits path `(s_i,)`
with marker `2`, and records that stage's seen key at the source. The source
does not read a fault oracle to decide whether the route has physically
failed: the trigger is the missing matching ACK after the local observation
interval.

An initial-FLOOD flow arms no repeat or recovery timer. A matching source ACK
from any actually started eligible stage completes the application once and
cancels its remaining uncommitted source requests. Deadline expiry retires
the flow, cancels remaining uncommitted source requests, and may update cache
state as specified in Section 5. Already committed packets remain charged.

For one unique application flow, let `N_i(m)` count DATA/FLOOD transmissions
by its original source with stage marker `m`. The implementation guards and
source-return rejection enforce

\[
N_i(m)\le1\quad(m\in\{\varnothing,1,2\}),
\qquad
N_i^{\rm source}=\sum_m N_i(m)\le
\begin{cases}1,&F_{\rm INITIAL},\\3,&R_{\rm INITIAL}\text{ in full CPR}.
\end{cases} \tag{A9}
\]

These are upper bounds, not obligations to transmit. They exclude ACKs,
other flows and other nodes' relays. They do not imply three network-wide
transmissions or one forwarding event per node over an arbitrarily long
history. Bounded seen state can expire or be evicted; each accepted FLOOD
path remains simple, while separate copies may follow different paths.

## 4. Forwarding, ACK validation and relay cancellation

Routed DATA is accepted only at the next path node. At the destination it
records delivery and generates a reverse-path ACK. Intermediate forwarding
requires remaining TTL and a relay-capable node. A decoded routed packet
overheard at its final destination before the designated last hop is not
destination delivery.

Before any inherited FLOOD delivery, ACK or forwarding side effect, CPR
requires useful payload, marker `None` or `2`, equal request/flow IDs, a
nonempty simple path beginning at the origin, the decoded sender at the
path end, the correct last-path index, and a receiver absent from that path
and different from the origin. With incoming path length `n`, it requires
`1 <= n <= H` and `1 <= TTL <= H-n+1`. Valid reception appends the receiver;
destination reception may ACK even on the final permitted hop. A valid
non-destination relay also requires TTL greater than one and relay eligibility.

The duplicate key is `(kind, origin, flow_id, request_id, marker)`. A duplicate
can suppress the matching uncommitted pending relay, but cannot relabel a
committed request canceled. Initial and recovery keys remain distinct. A
return to the source is rejected by the path rule even after its seen entry
has expired.

At an addressed ACK hop, the receiver must equal the node at `path_index`,
and the decoded previous transmitter must be the next index in that stored
source-to-destination path. Intermediate ACK forwarding follows the reverse
path and remaining TTL. At the source, acceptance additionally requires:

1. ACK kind; the live flow ID and equal request ID; reversed source/destination
   endpoints; no application payload; a live, not already completed flow.
2. `now <= D_i`; source path index zero; a simple path of two through `H+1`
   nodes, starting at the flow source and ending at its destination; decoded
   sender equal to `path[1]`; and an existing local flow-state association.
3. A supported marker whose stage has a recorded start no later than this
   reception. Initial routed and repeat ACKs must exactly match the saved
   initial path. Initial-FLOOD and recovery ACKs may confirm the simple path
   discovered by their corresponding FLOOD.

Shared cache generation changes are not ACK rejection conditions. An older
valid in-flight message can finish even if another message has since updated
the route. Cache mutation is a separate operation. Replay after retirement,
unknown flow identity, wrong marker and a stage that never started do not
complete a flow. These checks describe the honest-packet simulator; they are
not an authentication protocol or a proof against malicious forgery or
application ID reuse after a reset.

For relay cancellation, each pending ledger record contains the relay,
original endpoints, flow/request IDs, marker, observed path and exact pending
send handle. A physically decoded ACK must have a positive flow ID, equal
request ID, no payload, supported marker, a simple correctly oriented path,
a valid reverse index and preceding transmitter, and matching record
endpoints/marker. The canceling relay must be **off the ACK path**. Cancellation
also requires a handle that is neither already canceled nor committed. The
function has no access to a global “destination delivered” flag. It does not
require knowledge of the source's deadline or current cache generation.

## 5. Message confirmation and cache evidence

For a destination, write a cache record as `(p,g,rho,expiry,phase)`, with path
generation `g` and confirmation revision `rho`. Installation of a new route
increments the source's generation counter, stores that destination epoch,
and begins a confirmation revision at one. The destination epoch remains
available in bounded tombstone state when appropriate.

After accepting a source ACK, CPR considers cache changes in this order:

| Condition | Cache operation and recorded `cache_update` |
| --- | --- |
| ACK path equals the current READY, unexpired path | Refresh expiry and last-ACK time, reset miss streak, keep `g`, increment `rho`; `refreshed-same-path`. |
| Otherwise, the stage's captured destination epoch equals the current epoch | Install the ACK-confirmed path with a new generation; `installed-matching-epoch`. |
| Otherwise | Confirm this application but preserve the newer cache; `preserved-newer-route`. |

The captured epoch is the initial epoch for initial-FLOOD flows, the saved
route generation for routed initial/repeat stages, and the recovery epoch for
recovery ACKs. A stale ACK therefore cannot replace a newer different route.
A valid confirmation of the same currently live path can refresh it without
invalidating concurrent flows through a needless generation change.

At a routed flow's deadline, cache miss handling requires a current READY
record matching **both** its saved generation and saved confirmation revision.
If a newer ACK has increased `rho`, the older timeout records
`preserved-newer-confirmation`. Comparing revisions, rather than just floating
timestamps, distinguishes confirmations occurring at the same time. This
guard affects cache invalidation only; it does not reject ACKs.

An eligible miss invokes the inherited bounded miss counter and quarantines
the record. That helper can evict at its second miss, but CPR's READY check
means a quarantined record is not repeatedly penalized by every older timeout.
A new initial send cannot use a quarantined or expired path. No claim of
unconditional “evict after two failed application flows” is made for CPR.

## 6. Exact controls

| Protocol ID | Change from full CPR |
| --- | --- |
| `meshecho-cpr-noackcancel` | Disable relay ACK cancellation only. Keep relay enrollment, capacity, retirement, capacity cancellation, source ACK processing and source-request cancellation. |
| `meshecho-cpr-norepeat` | Omit the same-path repeat. Reserve its nominal observation slot before recovery; no fake repeat request or physical start. |
| `meshecho-cpr-norecovery` | Retain initial/repeat scheduling and admission; never request or start recovery. |
| Historical `meshecho-cpr-nocancel` | Disable the CPR relay-ledger component and ACK cancellation together. Keep the separate inherited pending table. It is not an ACK-only control. |

For no-repeat, after routed initial start `t_0`, recovery eligibility begins
at

\[
t_{\rm slot}=t_0+2B_R(p_i,1). \tag{A10}
\]

The callback is scheduled at `min(D_i,t_slot)`; it issues no recovery at or
after the deadline and none before the slot ends. The skipped interval is
left idle rather than reassigned to an earlier recovery. Recovery still
passes its own proposed-start budget and cache-generation checks. The event
`repeat-slot-skipped` records the slot boundary, while `repeat_started_at`
remains absent. This preserves the nominal unqueued observation opportunity;
it does not promise identical full-policy and control event times when queues
differ. Source DATA/FLOOD bounds are two for routed no-repeat and no-recovery
flows, and one for all initial-FLOOD branches.

## 7. State bounds, computation and local information

| State | Bound in this snapshot | Overflow/retirement behavior |
| --- | --- | --- |
| Authoritative route records | 8 per source | LRU replacement on installation. |
| Active controller flows | 8 per source | Reject new registration with `state-capacity-drop`; keep it in the scheduled denominator. |
| Destination epoch tombstones | Route plus active-flow capacity (16 by default) | Preserve destinations protected by current routes/live flows while pruning others. |
| CPR cancelable relay ledger | 8 records per relay by default | Oldest entry at that relay is evicted; full CPR cancels its uncommitted handle. Committed/canceled records are retired. |
| Inherited pending FLOOD table | 128 entries per node | Evict oldest local handle and cancel it only if uncommitted. This remains in every control. |
| Duplicate seen table | 128 entries per node, 30-second TTL | Purge expired entries and evict oldest entries; path validity still blocks source return. |
| CPR retired-flow ring | 256 IDs across the protocol instance | Retain recent retirement identities; live-flow lookup is independently required for ACK acceptance. |

Let `H` be path depth, `R,F,K,S` the above route, active-flow, relay-ledger
and seen capacities. The authoritative per-node records store at most
`O((R+F+K)H+S)` path/key data, plus bounded pending handles. Path uniqueness
and endpoint checks cost `O(H)`. Dictionary lookups have their usual expected
constant cost. The actual Python ledger combines all simulated nodes: its
enrollment/retirement scans can cost `O(NK)`, and inherited pending scans can
cost `O(N*128)` for `N` nodes. It would be inaccurate to claim those simulator
operations are constant time.

These component limits do not bound the entire Python process. Event queues,
packet/RX/action evidence, retained flow-to-state mappings, mirrored route
metadata and other diagnostics can grow with nodes or experiment history.
No measured RAM saving, full firmware memory bound, or device energy saving
follows from the eight-entry cancellation ledger alone.

Protocol decisions use the current flow's local state, cached ACK-confirmed
path, local radio queue opportunity, configured PHY/hop/timer values,
received packet fields and locally decoded ACKs/duplicates. Forwarding delay
uses received SNR and a configured role discount; its reproducible jitter is
keyed to packet/node context. Shared channel/fault traces and offline graph
reachability characterize the experiment environment and are not supplied
as observations to the source FSM. No source action conditions on future
channel outcomes, counterfactual success or remote delivery flags.

## 8. Accounting and evidence interpretation

For the fixed generation-plus-drain cutoff `C`, charge complete frame ToA
for every distinct physical TX starting by `C`:

\[
A=\sum_{q:t_q\le C}T(p_q). \tag{A11}
\]

This includes useful DATA, FLOOD, ACK and every actual duplicate/recovery
transmission. A frame that begins before the cutoff is charged in full even
if its end crosses the cutoff; RX-attempt availability then follows whether
its `tx_end` event was processed. Requests, decisions and cancellations are
separate event categories. A request is not a TX, and a post-ACK observation
does not erase a committed TX's airtime. Reporting uses timestamped physical
ledgers, not an undifferentiated event-handler counter that may already
contain reserved future sends.

`cpr-cancel-check` counts each decoded ACK passed to the enabled relay
cancellation function, including checks with no matching pending handle,
on-path relays or committed handles. Its `canceled` flag reports the outcome;
`cpr-cancel` separately records success. Therefore

\[
\text{success per decoded ACK check}
=\frac{\#\{\text{checks with canceled=true}\}}
       {\#\{\text{decoded ACK cancellation checks}\}} \tag{A12}
\]

is undefined when the denominator is zero. It is not the probability of
canceling an eligible pending relay. Capacity evictions and duplicate-based
suppression are reported separately. Cancellation counts also do not equal
counterfactual network airtime savings: removing a relay can change later
traffic, receptions and contention. The clean control comparison is needed
to measure that total policy effect.

Each flow's first eligible destination delivery and first accepted source
ACK are separate outcomes. Deadline flags use their own timestamps relative
to `D_i`; all scheduled flows remain in the denominator. Request/TX/RX/ACK
identities and source-stage invariants are audited from saved events. No
independence between DATA loss and ACK loss is assumed. Fixed-current TX
energy is a linear conversion of A11, not a measured battery-life endpoint.

## 9. Implementation and regression map

The following map identifies executable definitions and relevant tests; it
does not claim that every listed test was rerun while writing this document.
Frozen-test execution records and the correctness report provide run evidence.

| Definition/claim | Frozen implementation | Frozen test reference |
| --- | --- | --- |
| A1, registration and full scheduled denominator | `MeshEchoCPR.send_app`; `DrcSourceState.register_flow`; runner `_flow_rows` | `test_drc_applies_the_eight_active_flow_capacity_at_enqueue`; orchestration denominator/audit tests |
| A2, request/commit/start distinction | `Simulator.transmit_later`, `begin_transmission`; `PendingSend` | `test_committed_future_start_is_not_cancelable_by_later_ack` in `test_meshecho_afs.py`; CPR committed-handle tests |
| A3–A5, full wire-length ToA | `Packet.wire_size_bytes`; `RadioConfig.toa_s_for_bytes`, `packet_toa_s` | `test_field_bytes_and_nominal_relay_airtime_are_charged_by_packet_toa` in `test_destination_certified_backup.py`; request/TX physical audit |
| A6–A8, source admission | `MeshEchoDRC._route_bound_s`, `_flood_bound_s`; `MeshEchoCPR._cpr_route_bound_s`; `choose_recovery_action` | `test_cpr_uses_a_same_path_repeat_before_flood_recovery`; `test_cpr_recovery_start_uses_public_controller` |
| A9, source bound and simple FLOOD paths | `_cpr_start_initial/repeat/recovery`, `_cpr_on_flood` | `test_source_physical_stage_bound_and_recovery_seen_key`; source-return/expired-seen/malformed-path tests in `test_secon_cpr_correctness.py` |
| Stage-bound ACK identity | `_cpr_on_ack_packet`, `_cpr_ack_rejection_reason`, `on_ack` | `test_ack_identity_and_stage_checks_survive_decoupled_cache`; `test_ack_after_deadline_and_replay_cannot_finish_a_flow_twice`; `test_exact_deadline_ack_precedes_expiration_independent_of_enqueue_order` |
| Concurrent confirmation without cache rollback | CPR `on_ack`; `DrcSourceState.refresh_same_ready_route`, `install_route` | `test_concurrent_valid_acks_confirm_both_flows_and_refresh_without_new_epoch`; `test_valid_old_flow_ack_confirms_without_overwriting_newer_different_route` |
| New confirmation survives old timeout | `_cpr_expire_deadline`; `confirmation_revision` fields | `test_older_flow_timeout_cannot_quarantine_a_newer_same_path_confirmation`; `test_timeout_after_same_timestamp_ack_refresh_uses_revision_not_float_time`; subsequent legitimate miss test |
| Exact pre-commit relay cancellation | `CprRelayLedger.cancel_for_ack`, `enroll`, `retire`; `_cpr_cancel_relay` | `test_cpr_cancels_only_a_matching_uncommitted_relay_after_physical_ack`; `test_cpr_does_not_cancel_a_committed_or_mismatched_relay`; initial/recovery relay tests |
| A10 and independent controls | `CPR_PROTOCOL_MODES`, CPR factory branch, `CprObservation`; `_cpr_arm_repeat/recovery`, `on_transmit` | `test_noackcancel_preserves_capacity_cancellation_and_only_disables_ack_cancellation`; `test_no_repeat_reserves_observation_slot_without_inventing_physical_repeat`; `test_no_recovery_retains_repeat_and_never_requests_or_starts_recovery` |
| A11 and event provenance | `tools/run_cpr_experiment.py` exports/audit; `tools/secon2027_experiment.py` independent audit | `test_accepted_source_ack_has_physical_tx_and_rx_provenance`; `test_impossible_destination_delivery_cannot_pass_independent_audit`; `test_overheard_routed_data_is_not_destination_delivery`; stage/cold-source audit tests |
| A12, observation versus success | `_cpr_cancel_relay` event emission | `test_decoded_ack_cancellation_checks_and_successes_are_observed_separately`; `test_disabled_ack_cancellation_emits_no_cancellation_check` |

All `test_secon_cpr_correctness.py` references above target the repaired
snapshot. Historical results from the pre-repair implementation cannot be
reinterpreted as observations of this specification. Subsequent experimental
evidence must retain its own source, configuration and cohort identities.
