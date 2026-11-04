# MeshEcho-DRC Independent Contract Audit

Date: 2026-10-06  
Scope: read-only audit of the current `MeshEchoDRC` implementation, the
simulator evidence hooks, and the proposed DRC runner contract. This audit did
not edit implementation or paper files, run a reserved cohort, change
`VERSION`, publish artifacts, or submit anything.

## Executive result

No P0 failure was found in the source decision path: the DRC controller is a
separate class, and its initial and recovery decisions are reached through the
simulator's physical-start hook. The current implementation is therefore a
credible implementation slice, not yet a publishable evidence pipeline.

There are seven P1 blockers before a DRC result can replace the ICC results:

1. No independent DRC runner writes the request, transmission, RX-attempt, ACK,
   application-order, and bounded-state artifacts.
2. The request ledger is not complete or automatically finalized at the drain
   cutoff, and it omits fields needed to classify deadline/cutoff behavior.
3. RX and ACK provenance is only partially populated; the RX deadline field is
   always null and an accepted F ACK is recorded before its new route generation
   exists.
4. Same-time deadline, timer, application, TX-end, and TX-request ordering is
   implicit rather than part of a tested contract.
5. The existing paired runner does not guarantee identical protocol-level random
   streams for the DRC controls.
6. The source-hash, trace, and flow/action interfaces in the generic SR runner
   do not identify or serialize DRC state and actions.
7. Operational state is bounded only inside `DrcSourceState` and `_DrcSeenTable`;
   several DRC maps used during the run grow without a corresponding cap or
   eviction audit.

Until these are closed, DRC numbers may be useful for debugging but must not be
called development/holdout evidence or inserted into the ICC manuscript.

## What is already correct

### Physical-start decision boundary

`Simulator.begin_transmission()` computes the actual queue-available start as
`max(self.now, node.tx_available_at)` and calls `protocol.on_tx_request()` only
after that value is known (`lora_mesh_sim.py:1116-1146`). DRC maps its placeholder
request to `_start_initial()` or `_start_recovery()` at that hook
(`lora_mesh_sim.py:3363-3370`). The controller itself is independent of
`MeshEchoSR` (`lora_mesh_sim.py:3155-3163`), and the standalone action rule is
implemented in `meshecho_drc.py:97-156`.

The route/recovery admission rule is conservative and uses complete modeled
packet ToA bounds rather than a future delivery oracle
(`lora_mesh_sim.py:3260-3301`). DRC's ACK path validation checks endpoints,
path loops, encoded next hop, marker, deadline, and route generation
(`lora_mesh_sim.py:3575-3614`). No direct destination-delivery oracle or true
PRR input was found in this source decision path.

### Basic physical evidence hooks

Started requests are joined to a `Transmission` at
`lora_mesh_sim.py:1160-1176`; per-receiver attempts are recorded for self,
half-duplex, capture collision, success, and PRR failure at
`lora_mesh_sim.py:1227-1337`; and source ACK events retain the physical TX and
RX-attempt identifiers at `lora_mesh_sim.py:1339-1368`. These hooks are useful,
but they are not yet exported or independently recomputed.

## P1 findings

### P1-1: There is no independent DRC evidence runner

`SrRun` and `SrExperiment` only carry `row`, `flows`, `actions`, and paired
summaries (`tools/run_sr_experiment.py:73-92`). `run_one_sr()` runs the generic
experiment and returns only those three evidence classes
(`tools/run_sr_experiment.py:2026-2036,2152-2245,2400-2401`). The artifact writer
creates only `runs.csv`, `paired.csv`, `flows.jsonl`, `actions.jsonl`, and a
manifest (`tools/run_sr_experiment.py:2817-2850`). It never writes
`Simulator.tx_requests`, `transmissions`, `rx_attempts`, `ack_provenance`,
`application_events`, or DRC state transitions.

The current DRC protocol names are registered only in the simulator
(`lora_mesh_sim.py:89-94,8305-8316`); the runner has no DRC split, arm contract,
or DRC-specific manifest. Reusing the generic runner would silently turn a
physical evidence requirement into a metrics/action-log requirement.

**Required repair:** add a DRC-only runner and artifact schema. Every
seed/arm must emit immutable rows for scheduled flows, actions, requests,
physical TXs, RX attempts, ACK provenance, and state transitions. Add an
independent validator that joins every `started` request to exactly one TX and
every accepted ACK to one successful RX attempt and ACK TX. Fail closed on a
missing arm, missing flow, duplicate join, zero-flow seed, or hash mismatch.

### P1-2: Request ledger is incomplete and not closed at cutoff

`transmit_later()` records only a subset of request metadata
(`lora_mesh_sim.py:1057-1098`). It has no `action`, route generation, guard
generation, `toa_s`, `deadline_class`, or `cutoff_class`. The status vocabulary
also contains implementation-specific `protocol-no-start`, while the contract
requires an auditable distinction among state-capacity, guard/deadline reject,
explicit cancel, and cutoff censoring.

`finalize_request_ledger()` exists but is a manual method
(`lora_mesh_sim.py:1100-1115`), and `Simulator.run()` never calls it
(`lora_mesh_sim.py:1395-1437`). The generic runner also never calls it. Thus
requests left in the event queue remain `scheduled` and cannot be distinguished
from a request whose simulation was not drained. DRC capacity rejection creates
only an action event and no request/flow ledger record
(`lora_mesh_sim.py:3337-3355`).

**Required repair:** make cutoff finalization part of the DRC runner's explicit
drain operation. Store one request record for every source admission attempt,
including capacity drops, and add the contract fields:
`action`, route/guard generation, `status_at`, `status_reason`, `toa_s`,
`deadline_class`, and `cutoff_class`. Recompute queue wait and `toa_s` from the
joined TX, not from a summary counter. Keep complete TX cost for a packet that
starts after its flow deadline but before the experiment cutoff.

### P1-3: RX/ACK provenance is not yet sufficient for recomputation

Every RX attempt currently stores `"in_deadline": None` and no code updates it
(`lora_mesh_sim.py:1243-1264`). ACK provenance has `accepted_at` but no explicit
`ack_rx_at` or `deadline_at` field (`lora_mesh_sim.py:1352-1368`). More
importantly, source provenance is written before `state.accept_valid_ack()` can
install a new route (`lora_mesh_sim.py:3697-3715`; route installation is
`meshecho_drc.py:462-479`). Therefore an accepted ACK for an `F_INITIAL` flow is
recorded with the old/`None` route generation even though that ACK creates the
new generation.

The provenance recorder accepts arbitrary `RxInfo.tx_id` and `attempt_id`; it
does not itself verify that those identifiers exist in the RX ledger and point
to a successful attempt. That check is currently left to a nonexistent runner
audit. Invalid ACK paths at intermediate nodes are dropped without a source
provenance record (`lora_mesh_sim.py:3682-3695`), which is acceptable only if
the artifact contract explicitly limits ACK rejection records to source-facing
candidate ACKs and records the physical RX attempt separately.

**Required repair:** persist `ack_rx_at`, `deadline_at`, and the post-commit
generation (or a separate pre/post generation pair). In the independent audit,
verify `accepted` iff the referenced RX attempt is `success`, the receiver is
the current source, the ACK TX/path/request/marker matches the flow, and
`ack_rx_at <= deadline_at`. Populate `in_deadline` for every RX attempt from the
flow ledger and preserve rejected/late/duplicate ACK candidates.

### P1-4: Same-time event ordering and deadline boundary are implicit

The scheduler gives `tx_end` priority 0, all other events priority 1, and
`tx_request` priority 2 (`lora_mesh_sim.py:981-987`). The run loop otherwise
uses insertion order (`lora_mesh_sim.py:1395-1423`). DRC schedules the deadline
timer at the exact deadline (`lora_mesh_sim.py:3356-3361`), schedules the guard
timer at `guard_at` (`lora_mesh_sim.py:3500-3507`), and schedules the recovery
request at zero delay from that timer (`lora_mesh_sim.py:3511-3533`). Thus at an
exact timestamp a deadline/protocol timer runs before a queued TX request, while
a TX ending at that timestamp is processed first. Application sends and timers
share priority 1, so their relative order depends on insertion history.

The boundary is also split across APIs: `_fits()` requires `now < deadline` and
`now + duration <= deadline` (`meshecho_drc.py:81-85`), while source ACK
validation accepts `sim.now == flow.deadline` because it rejects only `>`
(`lora_mesh_sim.py:3584-3588`). This may be intentional, but it is not stated
or tested as a single contract. A request canceled by the exact-deadline timer
can be logged as `canceled-before-start` without a DRC decision event.

**Required repair:** define one event-order enum (TX end/physical RX, ACK
decision, deadline censor, application enqueue, guard, TX request) and use it
for all equal-time events. Add RED/GREEN tests for TX end at deadline, ACK at
deadline, TX request at deadline, guard at deadline, and cutoff at the same
timestamp. Choose and document whether an ACK at exactly the deadline is valid;
make `_fits`, ACK validation, timer cancellation, and artifact classes agree.

### P1-5: Paired controls do not have keyed protocol-level randomness

`Simulator` separates channel randomness into `channel_random`, but DRC flood
forward delay still draws from the event-order-sensitive shared RNG
(`lora_mesh_sim.py:880-884,3641-3649`). A DRC control that changes the number or
order of flood events can consume a different sequence of `self.sim.random`
draws, changing later forwarding jitter even when the seed, topology, and
application trace are identical. The generic runner checks only a sorted trace
hash and deadline (`tools/run_sr_experiment.py:2144-2152,2441-2448`), not random
draw identities or topology/radio hashes.

**Required repair:** derive all DRC role/jitter draws from a stable key such as
`(seed, flow_id, packet generation, sender, receiver, attempt ordinal, role)`;
use the same key for every arm. Include the RNG contract and topology/radio
hashes in the paired manifest, and independently assert equal fixed inputs
before computing paired effects.

### P1-6: DRC actions and source hashes are lost or misidentified by the generic runner

Flow rows extract `source_action` only from `protocol.flow_data_actions`
(`tools/run_sr_experiment.py:2174-2178`), but DRC writes actions into
`protocol.flow_actions` (`lora_mesh_sim.py:3422-3444,3476-3484`). A real DRC run
therefore returns rows whose per-flow source action is `None` even though the
action log contains decisions. A read-only smoke using
`run_one_sr(SR_CASES["recurring_fading"], "meshecho-drc", 12345)` produced 48
flow rows and 132 action rows; the first flow's `source_action` was `None`.

Additionally, `run_matrix()` selects source-suite `lpr` as the fallback for a
DRC protocol (`tools/run_sr_experiment.py:2766-2773`), so `source_hashes()` hashes
`lora_mesh_sim.py`, the generic probe, the generic runner, and the LPR design,
but not `meshecho_drc.py` or the DRC contract (`tools/run_sr_experiment.py:212-230,304-315`).
The runner can therefore report a source-hash-stable DRC artifact after the
standalone controller or contract changes.

**Required repair:** create a DRC `Run`/`Experiment` schema that reads
`flow_actions`, stores decision/request/TX joins, includes `meshecho_drc.py`
and the DRC contract in the source hash, and hashes the actual application
ordinal trace rather than the current sorted `(time, src, dst, flow_id)` tuple.

### P1-7: Finite-state claim is not closed beyond the helper classes

The standalone source state caps route and active-flow records at eight
(`meshecho_drc.py:17-19,195-215`), and `_DrcSeenTable` caps 128 entries with a
TTL (`lora_mesh_sim.py:3125-3152`). However, the protocol keeps several
per-flow histories for the full run: `flow_records`, `flow_states`,
`flow_actions`, `flow_sent_paths`, `flow_ack_paths`, `retired_flows`, and the
unbounded `action_events` list (`lora_mesh_sim.py:3195-3210`). `_retire()` removes
only active/pending entries and deliberately leaves these histories
(`lora_mesh_sim.py:3567-3573`).

`pending_fallback` is especially problematic: it is populated for each unique
flood receiver/key (`lora_mesh_sim.py:3651-3680`) and is read for duplicate
suppression, but no normal start/cancel path removes its entry. The bounded seen
table can expire while this dictionary retains historical keys. `_mirror_route()`
can also leave stale entries in `route_cache` after an LRU route eviction because
the eviction in `DrcSourceState.install_route()` does not notify the mirror
(`meshecho_drc.py:233-260`; `lora_mesh_sim.py:3248-3258`).

**Required repair:** specify which collections are diagnostic-only and exclude
them from an embedded-memory claim, or add explicit caps/eviction and tests for
every operational map (`pending_fallback`, `route_cache`, `last_commit_flow`,
and active flow metadata). Emit state-capacity/eviction events into the ledger
so a state drop is measurable rather than inferred from an in-memory count.

## P2 observations

* `rx_attempts` has no protocol-level `invalid_path` outcome; physical success
  followed by path rejection is visible only in an ACK/action path, not as a
  unified attempt reason (`lora_mesh_sim.py:1261-1264,3682-3695`). This is not a
  blocker if the contract clearly separates PHY attempts from protocol rejects,
  but the schema should say so.
* DRC's `DrcObservation` API accepts caller-supplied route/flood bounds and does
  not encode their provenance (`meshecho_drc.py:43-72`). The production adapter
  currently supplies bounds from local packet/ToA accounting, but an independent
  audit should hash and validate the bound calculator rather than treating the
  standalone controller unit tests as proof of locality.
* The DRC simulator default enables RX recording by protocol name, but callers
  can disable it with `record_rx_attempts=False`
  (`lora_mesh_sim.py:901-904`). A DRC evidence runner should force the recorder
  on or fail closed when it is disabled.

## Recommended closure order

1. Freeze the DRC wire/action/control contract and event-order semantics; add
   equal-time RED/GREEN tests.
2. Add the DRC runner and complete request/flow/TX/RX/ACK/state ledgers; close
   every request at the declared cutoff.
3. Add a source/contract/case/radio/topology/trace/RNG manifest and independent
   recomputation checks. Verify same-wire controls before any performance gate.
4. Run one new mechanical smoke only. Audit all joins, counts, deadline classes,
   byte/ToA/energy arithmetic, and zero-event seeds.
5. Freeze development and holdout inputs. Only after development passes its
   predeclared exposure/reliability/airtime gates may an untouched holdout run.
6. Rewrite the ICC paper only from the audited holdout artifacts; keep the old
   paper and `VERSION` unchanged if any gate fails.

## Final disposition

The implementation has a sound source-decision boundary and enough low-level
hooks to continue. It is **not yet eligible for DRC performance claims** because
the evidence, deadline ordering, paired-control, source-hash, and state-capacity
contracts are incomplete. No P0 was found; the seven P1 findings above are
release-blocking until independently fixed and re-audited.
