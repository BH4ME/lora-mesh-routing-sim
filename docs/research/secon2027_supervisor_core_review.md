# SECON 2027 CPR core supervision review

Status: **COMPLETE for the reviewed snapshots; the confirmed P1 is CLOSED by the subsequent confirmation-revision fix, independently rechecked below. No additional blocker was found in the requested core scope.**. Read-only review of the execution checkout; fixes remain the execution thread's responsibility. No file in that checkout was written by this review. No `Simulator.run`, channel sampling, performance experiment, holdout run or new seed was used. The deterministic interface probe reused the existing test fixture's seed 23 and disabled bytecode writes (`-B`, `PYTHONDONTWRITEBYTECODE=1`).

## Snapshot

Execution checkout: `/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo`.

Review timestamp UTC: 2026-11-04T07:34:42.884233+00:00.

Base HEAD: `a0ee4ce7bb96592c57dc5f389cf4c1958bec0069`; reviewed changes are uncommitted.

| File | SHA-256 at first read and confirmed probe |
|---|---|
| `lora_mesh_sim.py` | `b5332b0e6c07f1a218719946e27993b6614814d00acf732cbfcf2991da917e3b` |
| `meshecho_cpr.py` | `33de078b38878a724c7d341741f9dc8ff26b926ab87354a76e5f575eb4a5d8bc` |
| `meshecho_drc.py` | `de9f26de7bf9008d931090ddb8906bcee26c84b63445b7f01fadfcd2a931f0b0` |
| `tests/test_secon_cpr_correctness.py` | `6d5204b1885254b0d6685a11c547418f59e4f2c481730a1fe48f84f280e5917b` |
| `tests/test_meshecho_cpr_controller.py` | `bdd8699e36e9a08a4e64ac370ab57601d7f7cb2e1aa051be0914219a531a2207` |

The five hashes above were identical before and after the deterministic probe. Development is concurrent; these findings attach to these bytes, not to subsequent edits. Other dirty runner/config files were visible but are outside this core review.

## Historical P1 (now CLOSED) — A stale flow's deadline quarantines a route refreshed by a different successful flow

**Locations:** `lora_mesh_sim.py`, `MeshEchoCPR._cpr_expire_deadline`, lines 4336–4350 (condition at 4342; mutation 4344–4346); `meshecho_drc.py`, `DrcSourceState.refresh_same_ready_route`, lines 284–304. The refresh call is in `MeshEchoCPR.on_ack`, lines 4619–4622.

**What happens:** The new refresh correctly keeps the same-path route generation unchanged and updates `last_accepted_ack_at`. Deadline expiry still compares only that generation and does not compare the confirmation revision/timestamp. Consequently, the old unconfirmed flow still has authority to quarantine the freshly confirmed route. This is not merely a mislabeled log: the next application's initial action changes from routed DATA to FLOOD.

**Reproduction using existing fixture and production methods:**

```python
import sys, runpy
from pathlib import Path
repo = Path('/Users/bh4me_macair/Documents/Codex/2026-11-04/meshecho-secon2027/work/repo')
sys.path.insert(0, str(repo))
ns = runpy.run_path(str(repo / 'tests/test_secon_cpr_correctness.py'))
p, s = ns['fixture_protocol']()
state = p._state(0)
state.install_route(4, (0, 4), now=0.0, ttl_s=100.0)
f1 = ns['start_flow'](p, s, 1, now=1.0)  # deadline 31
f2 = ns['start_flow'](p, s, 2, now=2.0)
s.now = 3.0
p.on_receive(0, ns['ack'](p, 2), ns['rx'](4))
route = state.routes[4]
print(route.phase.value, route.generation, route.last_accepted_ack_at, f2.acked_at)
s.now = f1.deadline
p._cpr_expire_deadline(1)
print(route.phase.value, route.generation, route.last_accepted_ack_at, route.miss_streak)
f3 = ns['start_flow'](p, s, 3, now=31.1)
print(f3.initial_action)
```

**Observed output:**

```text
READY 1 3.0 3.0
QUARANTINED 1 3.0 1
F
```

**Why existing focused tests miss it:** The new tests cover two valid ACKs and preservation of a distinct newer route, but no test places an unacknowledged older flow's deadline after another same-path ACK refresh. A changed path increments generation and is protected; a same-path refresh is precisely the uncovered case.

**Fix recommendation:** Keep application ACK acceptance independent of cache state, and keep unchanged-path generation stable, but distinguish a route's confirmation revision from its structural generation. Capture the confirmation revision used by the relevant source attempt and allow its later miss to quarantine only if no newer matching-path confirmation superseded that attempt. A timestamp comparison can work only with an explicitly defined attempt boundary and equal-time ordering; a monotonically increasing confirmation revision avoids same-time ambiguity. Do not reintroduce unconditional generation increments that reject concurrent valid flow ACKs.

Add a deterministic regression with an old unconfirmed flow and a successful same-path flow, advance the old flow to its deadline, and assert that the refreshed route stays READY, keeps its fresh expiry/confirmation, and is reused by the next application. A late ACK for a *different* path must continue to confirm its flow without rolling back a newer route.

## Preliminary checks that did not reveal a counterexample

- FLOOD validation runs before inherited delivery/ACK/forwarding side effects; origin return, repeated nodes, invalid last physical sender, invalid path index, and excessive hop/path length are rejected. The maximum valid final hop is allowed.
- Source initial/recovery injections now seed seen state, and repeated source request placeholders are gated.
- ACK flow identity and physical reverse-hop checks remain in front of application confirmation. Shared cache generation no longer rejects an otherwise valid live flow ACK.
- `noackcancel` retains relay ledger and capacity eviction; legacy `nocancel` remains distinct. `norecovery` prevents both requesting and starting recovery.
- `norepeat` explicitly uses the nominal `t0 + 2 B_R` opportunity and records the skipped slot without fake repeat TX. The accompanying correctness document states that this does not preserve exact event times under queueing; no stronger equivalence was assumed in this review.

The following final recheck supersedes this preliminary status; these are scoped correctness observations, not performance claims.

## Fix recheck and closure

Independent recheck completed UTC 2026-11-04T07:37:21.545191+00:00. Execution-thread edits were detected during review; no old and new code claims were conflated.

| File | SHA-256 of fixed snapshot (unchanged during verification) |
|---|---|
| `lora_mesh_sim.py` | `5d000beab9692997dbf5aebe147a41b75276563c08bf670054011c0414b49962` |
| `meshecho_cpr.py` | `c7e24fdfdbbdf5b27d2da5dba7ced73ba6d8c2a3178d3197bb202b5409067d8e` |
| `meshecho_drc.py` | `db1fca8012eb1225c7a77385d2b121be5c04c4bf99264e4ceec4b0acc907019e` |
| `tests/test_secon_cpr_correctness.py` | `b38a05b6dba86aa780399be2e47fd31bf27b6fa2ccdf773ae44c13864ae13d98` |
| `tests/test_meshecho_cpr_controller.py` | `bdd8699e36e9a08a4e64ac370ab57601d7f7cb2e1aa051be0914219a531a2207` |

`DrcRouteRecord.confirmation_revision` now starts at 1 and increments on each accepted same-path refresh (`meshecho_drc.py:169,303`). CPR captures that revision with the route used for its initial committed action (`lora_mesh_sim.py:4058`). Deadline expiry first requires the same structural generation and READY route, then preserves it when its confirmation revision differs (`lora_mesh_sim.py:4338–4360`). Timeout evidence records both revisions and the selected cache effect.

The **original counterexample was rerun unchanged**. Observed output now:

```text
AFTER_REFRESH       READY 1 2 1 3.0
AFTER_OLD_DEADLINE  READY 1 2 0 preserved-newer-confirmation
NEXT_FLOW           R
```

Interpretation: the structural generation stays 1, current confirmation revision advances to 2, the older flow retains revision 1, the missed old flow does not quarantine the route, and the next flow reuses it. This closes the demonstrated P1 without restoring the original concurrent-ACK rejection bug.

In addition, **11 deterministic fixture invocations passed**, invoked directly from the existing test module (no pytest cache, no event loop / channel sampling):

1. `test_older_flow_timeout_cannot_quarantine_a_newer_same_path_confirmation`
2. `test_timeout_after_same_timestamp_ack_refresh_uses_revision_not_float_time`
3. `test_a_flow_started_after_latest_confirmation_can_still_quarantine_on_timeout`
4. `test_concurrent_valid_acks_confirm_both_flows_and_refresh_without_new_epoch(False)`
5. The same test with `True` (cached/routed start).
6. `test_valid_old_flow_ack_confirms_without_overwriting_newer_different_route(None)`
7. The same test with marker `1`.
8. The same test with marker `2`.
9. `test_noackcancel_preserves_capacity_cancellation_and_only_disables_ack_cancellation`
10. `test_no_repeat_reserves_observation_slot_without_inventing_physical_repeat`
11. `test_no_recovery_retains_repeat_and_never_requests_or_starts_recovery`

These checks confirm that the new revision is not used to reject live application ACKs; initial/repeat/recovery ACKs for old flows still confirm their own message while a different newer cached route remains unchanged. Same-time confirmations have distinct revisions. A flow committed after the latest confirmation still can quarantine on timeout if no subsequent confirmation arrives. The suppression and source-ablation switches retain their declared behavior under the direct fixtures.

The invalidation snapshot is deliberately the route confirmation at the **initial request commitment**. This review does not claim a different “most recent retry” or future physical-start snapshot policy. The code's time reservation semantics remain the existing commit-time model.

### Final scope and limitations

No execution-workspace file was changed by this review. No performance matrix, statistical seed, propagation/channel trial or `Simulator.run` was executed. The full 45/71/etc. suites reported by the execution thread were not independently rerun here. Static inspection covered the requested production paths and tests; dynamic verification was confined to the exact counterexample and the 11 named deterministic fixture invocations. The outcome is a scoped implementation review for the recorded hashes, not a claim of general protocol optimality or publication readiness. Further execution-thread changes require checking their diff against this snapshot before using this result as a freeze gate.
