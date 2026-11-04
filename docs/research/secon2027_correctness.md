# SECON CPR correctness and isolated controls

Date: 2026-11-04 (Asia/Shanghai). Implementation checkout: the isolated
`work/repo` imported at `a0ee4ce`, not the original source tree. No version
bump, commit, or push was made by this implementation subtask. The parent
release record binds these changes to the tested snapshot and promoted version.

## Correctness changes

1. CPR now validates FLOOD payload/request identity, supported marker, origin,
   simple path, preceding transmitter, path index, remaining hop budget and
   receiver absence from the path **before** inherited delivery/ACK/forwarding
   side effects. Source-return packets remain rejected after seen-table expiry.
   Initial and recovery source injections register their distinct seen keys.
   Last-hop destination receipt at the maximum permitted path length still
   delivers and acknowledges. Repeated source placeholders cannot initiate
   another initial, repeat or recovery stage.
2. A live message's ACK is validated against that message's endpoints,
   request/flow IDs, immutable routed path, stage marker, actual recorded stage
   start, deadline, and simple reverse path. Shared cache generation no longer
   rejects an otherwise valid application confirmation. A valid ACK refreshes
   the same READY, unexpired path without changing its generation. A changed
   path can replace the cache only when its stage's captured epoch matches the
   current destination epoch. Otherwise the message is confirmed while the
   newer route remains intact. `cache_update` records which case occurred;
   accepted ACKs retain generation-before/after provenance.
   A separate per-route `confirmation_revision` increments on each same-path
   ACK refresh. A routed flow captures this revision at its initial send;
   timeout can quarantine that route only if both generation and confirmation
   revision still match. Thus an older unACKed flow cannot invalidate a newer
   successful confirmation, even when confirmations share a timestamp. This
   revision is a cache-evidence guard and never rejects a valid flow ACK.
3. Duplicate FLOOD suppression and source deadline expiry cannot mark already
   committed requests canceled or count them as successful suppression. No
   physical TX/airtime is removed from accounting. The event priority contract
   already processes physical RX (`tx_end`) before equal-time timeout/request
   events; a deterministic regression now checks an exact-deadline ACK.
4. Each enabled cancellation handler records `cpr-cancel-check` after a decoded
   ACK, with receiver node, flow, marker, time, physical ACK RX ID and canceled
   boolean. `cpr-cancel` remains success only. The count is **decoded ACK
   cancellation checks**, including checks with no eligible pending handle;
   it is not an eligible-opportunity denominator. Disabled cancellation arms
   emit neither check nor success events.

The historical `DrcSourceState.install_route` operation still creates a new
generation. A separate `refresh_same_ready_route` operation is used by CPR, so
unrelated DRC semantics and historic snapshot interpretation are preserved.
An old CPR test that explicitly required rejection after a same-path cache
refresh was replaced with confirmation plus generation-preservation assertions.

## Controls and schedule rules

| ID | ACK cancellation | Relay ledger / capacity cancellation | Same-path repeat | Recovery |
| --- | --- | --- | --- | --- |
| `meshecho-cpr` | on | on, 8 records per relay by default | on | on |
| `meshecho-cpr-noackcancel` | off | identical to full CPR | on | on |
| `meshecho-cpr-norepeat` | on | identical to full CPR | omitted | after reserved observation slot |
| `meshecho-cpr-norecovery` | on | identical to full CPR | on | omitted |
| historical `meshecho-cpr-nocancel` | off | CPR ledger component off | on | on |

The inherited pending-forward table still has its independent 128-record
limit in all arms. The new ACK-only control preserves both capacity mechanisms;
the historical component-off arm is not relabeled as an ACK-only ablation.
`cpr_relay_capacity` exposes the CPR ledger limit through `build_protocol`.

For no-repeat, let `t0` be the initial DATA physical-start timestamp and `B_R`
the same marked-DATA route bound used by full CPR's repeat timers. Recovery
becomes eligible at `t0 + 2 B_R`: the initial observation interval plus one
nominal repeat observation interval. The freed interval is idle; the budget
is not reassigned to an earlier flood. This is the full policy's nominal
unqueued recovery opportunity, not a promise of identical event times under
queueing. A `repeat-slot-skipped` event records the boundary; no repeat
request/TX/start is fabricated. Recovery still needs the same current route
generation and sufficient remaining deadline. No-recovery leaves initial and
repeat scheduling intact and never requests or starts a recovery FLOOD.
All controls retain the same wire markers and real-TX cost accounting.

Constructor options: `cancel_on_ack`, `relay_ledger_enabled=None` (default
follows cancellation to preserve legacy behavior),
`evict_pending_on_capacity=None` (default follows ledger), `enable_repeat`,
`enable_recovery`, `relay_capacity=8`, and optional `protocol_name`.

## Verification and failure log

Only deterministic regression fixtures and existing unit/controller tests were
run here. No development/validation performance cohort was executed or reused.

| Step | Exact command / outcome |
| --- | --- |
| Runtime discovery | `python3 -m pytest tests/test_secon_cpr_correctness.py -q` failed: default Homebrew Python 3.14 has no pytest. |
| Executable fallback | `pytest tests/test_secon_cpr_correctness.py -q` failed collection because repo root was absent from that executable's import path. |
| Red regression | `/usr/bin/python3 -m pytest tests/test_secon_cpr_correctness.py -q`: **13 failed, 8 passed** before fixes. Failures reproduce concurrent cold/routed ACK rejection; old valid ACK after replacement; source return after seen expiry; malformed FLOOD delivery; missing source seen; unchecked packet flow ID. |
| First green pass | New suite plus existing CPR tests: 34 passed, one old test still expected stale-route rejection. Replaced that obsolete assertion with application confirmation and unchanged current epoch. |
| Controls | CPR suite including new controls: **45 passed**. |
| Final focused pass | `/usr/bin/python3 -m pytest tests/test_secon_cpr_correctness.py tests/test_meshecho_cpr.py tests/test_meshecho_cpr_controller.py tests/test_meshecho_drc.py tests/test_meshecho_drc_controller.py -q`: **71 passed**, 0.16 s. |
| Timeout regression from independent supervisor review | Added newer-confirmation and same-timestamp regressions: **2 failed, 1 passed** before the fix. Same focused command after separate confirmation revision: **74 passed**, 0.16 s. |
| Cancellation observation | Added absent/committed/cancelable pending and disabled-handler fixtures. Same focused command: **78 passed**, 0.13 s. |

Coverage includes concurrent cold/routed ACKs; initial/repeat/recovery ACKs
after a distinct newer route; flow/request/path/marker checks; late/replayed
ACKs; exact-deadline event ordering; source-return and expired seen state;
malformed and maximum-hop paths; unique source stages/physical TX upper bound;
capacity eviction in the pure ACK control; skipped-repeat timing without fake
TX; disabled recovery; cancellation before versus after commitment; and
independent initial/recovery deduplication keys.
The review regression also verifies flow 1 at t=1, flow 2 at t=2, ACK 2 at
t=3, timeout 1 at t=31: the refreshed route remains READY, and a new flow at
t=31.1 starts routed. A flow started after the latest confirmation still
quarantines on a genuine subsequent timeout.

These tests establish targeted implementation invariants. They do not estimate
performance, demonstrate statistical gains, replace final evidence-package
audits, or establish RF/firmware equivalence. Historical performance results
remain results of their historical implementation and must not be relabeled.
