# Passive terminal-ACK FLOOD-cancellation exposure

Date: 2026-10-04. Status: exploratory diagnostic, not an implemented protocol
or causal performance result. No BAR holdout seed (17001--17040) was opened.

## Question and baseline

Can a relay with an uncommitted same-flow FLOOD forward physically decode an
on-air destination ACK before that relay transmits, especially when the relay
is not on the ACK's reverse path? The unchanged `meshecho-dhr-flood` arm is a
F-rich baseline: its source uses F on an admitted R timeout. The canonical
`recurring_fading` case used fresh seeds 22001--22003 and a 30-s application
deadline. The observer changes no packet, event, state, random draw, or metric.

`PendingSend.committed` becomes true in `begin_transmission` before the
simulated physical TX start, which may be later because of sender queueing.
Only an identical, uncanceled, **uncommitted** handle still present in the
relay's `pending_fallback` state is counted as strictly cancelable under the
current API. Committed handles whose TX start is still future are a separate
optional upper-bound stratum, never part of the strict set.

## Strict on-air match

The observer runs only after `try_receive` reports a physical ACK decode.
It checks a valid source-to-destination ACK path, the actual ACK transmitter's
position on that path, the reversed source/destination fields, the same flow
and request ID, and the same FLOOD recovery marker (`repair_index`). The
local queued FLOOD path must start at the source, end at this relay, have the
expected path index and no loop. The relay must be **off the ACK path**. No
global delivery timestamp, radio-model oracle, or future event is used for
the decision predicate. In particular, an initial routed-DATA ACK with no
repair marker cannot match a recovery-F forward marked `2`.

For the airtime opportunity bound, the offline report then asks which
strictly nominated handles actually transmitted after the ACK and first
destination delivery in the unchanged baseline. Handles that the baseline
later suppressed through ordinary duplicate-F reception contribute zero.
This counts only the nominated relay's own TX airtime, not downstream effects.

## Observed exposure

All three observed runs reproduced the `run_one_sr` application schedule,
per-flow delivery/ACK timestamps and source actions, every protocol action,
raw TX counts, and the full packet-by-packet TX trace hash exactly. Source
hashes and each run's parity hashes are in
`results/meshecho_ack_overhear_cancel_seed22001_22003_20261004_v2.json`.
The JSON artifact SHA-256 is
`3d5df0c10887fdbb9f611bd8337f060a364788024970a151361b242cb6b12a31`.

| Measure, three exploratory seeds | Initial F | Same-flow recovery F | Total |
| --- | ---: | ---: | ---: |
| Unique strict pending handles nominated by an off-path ACK decode | 666 | 454 | 1,120 |
| Nominated handles that later actually transmitted | 362 | 229 | 591 |
| Potentially avoidable relay TX airtime (s) | 35.318272 | 22.596864 | 57.915136 |
| All post-delivery FLOOD relay TX airtime (s) | 53.629184 | 46.692352 | 100.321536 |

There were 124 scheduled unicast flows, 123 destination deliveries by the
deadline, and 84 source ACKs by the deadline. The observer saw 7,129
physically decoded natural destination ACK copies across all nodes. The
observer counted 1,203 individual ACK-decode events with a strict pending
candidate; deduplication by pending handle yields the 1,120 unique
opportunities in the table. The
separate committed-but-future-start stratum was zero in this sample. These
are counts of exposures and charged transmissions, not independent trials
or an estimated improvement in delivery or ACK probability.

## Interpretation and next gate

The strict set is sizeable, including the recovery-F epoch, but it does not
establish that cancellation is safe or beneficial in a closed loop. Removing
one relay TX can alter later FLOOD paths, ACK receptions, collisions, and
source-ACK completion. Only three exploratory seeds were inspected, so no
population effect or confidence interval follows. An ACK heard by an
on-path relay was deliberately excluded; this report cannot quantify that
broader implementation choice.

This is not a claim that ACK-based suppression is new. MeshEchoLPR already
cancels a pending `PATCH_RELAY` when it overhears successor DATA/ACK, subject
to `!pending.committed`. Meshtastic's documented managed flooding also
suppresses a pending rebroadcast when another rebroadcast is heard. The
candidate distinction is a terminal destination ACK suppressing a queued
general FLOOD forward, particularly at off-ACK-path relays. Exact prior-art
novelty remains unverified.

Before changing the protocol, freeze an on-wire and local-state cancellation
contract and compare it with ACK-oblivious fixed F under identical triggers,
ordinary duplicate suppression, a same-opportunity nonterminal suppression
control, and the existing source-recovery alternatives. The acceptance gate
must require source ACK by the original deadline and complete-network TX
airtime, alongside destination delivery, delay, collision, and per-epoch
coverage. Any on-path cancellation needs its own exposure accounting.
