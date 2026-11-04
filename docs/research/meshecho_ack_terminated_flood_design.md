# MeshEcho ACK-terminated FLOOD: prospective component contract

Date: 2026-10-04. Status: draft before protocol implementation or population
experiments. This is a relay-side vertical slice on the DHR fixed-F source
scaffold, **not** the completed MeshEcho-SR core rewrite or an ICC result.

## Research question and prior-art boundary

Can a relay that actually decodes the destination's ordinary application ACK
cancel its own still-pending useful-DATA FLOOD forward for the same flow and
recovery epoch, reducing whole-network LoRa airtime without reducing source
ACK or destination delivery by the original 30-s deadline? The ACK is a
locally observed terminal-delivery certificate; no global delivered flag or
new STOP packet is permitted.

Generic rebroadcast suppression and last-retry DATA flooding are already
documented by Meshtastic. AODV RFC 3561 uses route-hop-limited repair search;
DSR RFC 4728 salvages packets. This repository's MeshEchoLPR already cancels
queued PATCH_RELAY traffic after overheard successor DATA/ACK. A bounded
search did not verify an identical LoRa off-path terminal-ACK FLOOD rule,
but search absence does not establish novelty. Do not claim first invention.
The distinction to test is terminal ACK cancellation of ordinary queued
useful-DATA FLOOD, beyond existing duplicate-DATA suppression.

## Device-local rule

The source keeps the existing fixed-F DHR initial action, 15-s ACK guard,
30-s application deadline, one same-flow F rescue cap, and ACK-confirmed
route state for this component test. Any later source-side redesign must be
specified and evaluated separately. Every relay applies the existing
duplicate-DATA suppression unchanged. It adds at most eight active local
records, each containing the FLOOD key, source, destination, recovery marker,
validated local forward path, and the exact `PendingSend` handle for this
relay's delayed FLOOD forward. Enroll only a newly received app-payload
FLOOD that actually creates a pending relay forward. Its path after relay
append must begin at the source, end at this relay, have unique nodes,
`path_index == len(path)-1`, `2 <= len(path) <= max_hops`, and `ttl >= 1`;
the relay is not the source, and the incoming path's last hop equals the
actual physical `rx.sender`. An entry expires by a relay-local timer 30 s
after its FLOOD receipt, or is retired when its pending request commits or
is canceled. Expiration cannot read `Packet.created_at` or the source's
deadline. If capacity is full, the relay retains baseline forwarding and
does not enroll the new cancellation rule for that FLOOD.

On a physically decoded ACK, an off-ACK-path relay may cancel only if all
conditions hold at the decode callback:

1. Its matching FLOOD record exists, its handle is identical to
   `pending_fallback[(receiver, flood_key)]`, and that handle is neither
   `canceled` nor `committed`. Commitment occurs at the TX request, possibly
   before physical start; a committed future-start TX is **not** cancelable.
2. The ACK is control-only and has `request_id == flow_id`, matching the
   recorded FLOOD's `request_id == flow_id`. Match the reconstructed key
   `('FLOOD', ACK.final_dst, ACK.flow_id, ACK.request_id)`, not
   `ACK.flood_key` (which has the wrong kind and origin). `ACK.final_dst`
   equals the FLOOD source, `ACK.origin` equals its destination, and
   `repair_index` matches exactly (`None` for initial F, `2` for recovery
   F). An earlier R-stage ACK must never cancel a later F-stage rescue.
   The request ID here aliases the already charged flow ID; it is not a
   separately added on-wire field. `Packet.protocol` is simulator metadata
   and must not be tested as a received field.
3. The ACK path begins at the stored source and ends at its destination,
   has `2 <= len(path) <= max_hops+1` and unique nodes,
   `0 <= path_index < len(path)-1`, and
   `path[path_index+1] == rx.sender`. This relay is outside that ACK path.

The relay then cancels only that handle and records an action. It still
passes the ACK to the inherited protocol handler. No ACK transmission,
packet byte, route commit, duplicate delivery, or destination ACK-copy rule
is added by this slice. The added relay cancellation predicate does not
read global simulation metrics. The inherited DHR source policy already
reads its registered flow records; that behavior is unchanged. The
inherited full-protocol FLOOD deduplication set is
unbounded in the current simulator; an eight-entry added record is not a
claim that the whole protocol fits an MCU.

## Controls, split, and prospective gate

Use a no-cancel arm with the **identical** fixed-F source policy, FLOOD,
ACK path/copy rule, packet fields, deadlines, local record cap, and receiver
logic except the final pending-handle cancellation. It must mechanically
match unchanged `meshecho-dhr-flood` before population experiments in
per-flow times, source actions, metrics, and complete TX trace after
normalizing `Packet.protocol`, which is simulator metadata rather than a
wire field. Both arms must perform the same shadow registration, validation,
retirement, timers, and ACK delegation without extra random draws. The
normal duplicate-DATA suppression remains enabled in both arms. A broader
paper matrix, if the component survives, must also include fixed TTL,
full FLOOD, R repeat, Meshtastic-like fallback, and the old SR policy under
clearly separated feedback semantics; the simplified product models are
not firmware implementations.

Reserve seed 23000 for mechanical smoke; development is 23001--23040 and
holdout is 24001--24040, all disjoint from diagnostic seeds and prior
cohorts. The primary matched case is the existing recurring-fading traffic
with identical topology/application traces within each seed, 600-s flow
generation, 30-s original per-flow deadline, and complete TXs starting by
630 s charged at full packet ToA. Freeze source, design, runner, and tests
with SHA-256 before smoke/development. Do not open holdout if development
fails; no retuning and rerun on the same development seeds as confirmation.

The primary claim is **cost reduction with reliability noninferiority**,
not ACK-PDR superiority. Using seed-paired nominal two-sided 95% intervals
for AFS minus no-cancel, require all of:

- upper CI for relative complete-network TX airtime below -5%;
- lower CI for deadline source-ACK PDR difference above -0.02;
- lower CI for deadline destination-PDR difference above -0.01;
- at least 100 actual off-path pending-F cancellations across at least 20
  development seeds, with zero invalid-marker/path/late-handle cancellations.

These are author-chosen falsification margins, not ICC rules. Report mean
completion delay, collision failures, packet classes, modeled energy,
first-F versus recovery-F cancellation exposure, and physical ACK-overhear
counts even if the gate fails. Whole-run effects are closed-loop; do not
attribute every saved TX or later ACK to an individual cancellation.

An unchanged-hash 40-seed holdout must replicate the same four gates before
any positive manuscript claim. Then test unconditioned random pairs and a
second PHY/load regime, including cases where ACK overhearing is rare. If
this component passes, a separate source-side routing/recovery decision and
its matched controls are still required for the requested **full** core
rewrite. No paper/PDF/VERSION/GitHub/EDAS promotion follows from this draft.
