# Fixed-2-s ACK plus one same-path repeat (simple control)

Date: 2026-10-04. Status: prespecified comparator contract, not a new
MeshEcho core, performance result, or ICC contribution.

The existing `meshecho-dhr-flood-ack-delay` remains the parent behavior:
MeshEcho-SR source F/R/D decisions, DHR R-to-F guard, and one FLOOD ACK
scheduled 2 s after the first destination FLOOD decode. This control adds
at most one destination ACK on exactly that first reverse path, scheduled
0.5 s after the first ACK's **actual** destination TX end. It does not
repeat DATA ACKs, respond to duplicate destination FLOOD decodes, switch
paths, or change the original ACK's timing. The second ACK has the same
wire fields/size as the first, and every actual radio transmission,
forwarding hop, collision, and airtime is fully charged. Source ACK
deduplication and original 30-s acceptance remain unchanged.

The destination can observe its first FLOOD decode and first ACK physical
TX, but cannot observe the source's original application enqueue time:
`Packet.created_at` is simulator metadata, not an on-wire timestamp. The
repeat therefore uses only destination-local timing. To bound queued work,
its physical TX start must be at most 10 s after the first local FLOOD
decode; this is an author-chosen local window, **not** knowledge of the
application deadline. A queued repeat starting later is suppressed and
counted as an attempted but unstarted local action, not as transmitted
airtime. At most eight active per-destination repeat records are allowed;
the local repeat action or local 10-s expiry reclaims records. The
destination cannot observe the source's flow completion. This window and
capacity must be identical for a same-trigger adaptive counterpart.

Synthetic behavior tests must cover exact first ACK timing, second ACK
path and 0.5-s spacing from actual first physical TX end, no repeat for
DATA ACK or duplicate destination FLOOD decode, queued-start suppression,
capacity bound/expiry, and old-arm parity. No new seed runs until the
implementation is independently inspected. A future experiment must pair
this arm with the unchanged fixed-2-s single ACK and any candidate on
identical traces and radio assumptions, report all-flow 30-s source ACK,
destination delivery, full-network airtime, bytes, and actual ACK starts,
and keep selected exploratory seeds separate from untouched holdout.

The repeat control can establish how much reliability is purchasable by
one plain extra ACK. A candidate that does no better at the same trigger
and budget has no supported path-selection or adaptive-feedback benefit.

## Prospective paired measurement

Reserve 41000 for one mechanical smoke and 41001--41020 for a paired
exploration on `recurring_fading`. The current-code fixed-2-s single ACK
and this repeat arm share topology, application trace, radio, SR/DHR
source policy, 600-s generation, original 30-s flow deadline, and TX
starts through 630 s; run a symmetric 660-s continuation to report any
spillover. Freeze simulator, runner, tests, and design hashes before
smoke, then require independent stock replay of the current-code single
arm, strict flow/action/TX and artifact hash reconciliation, and physical
first/second ACK timing checks before opening 41001--41020. The old
38xxx manifest is archival and has a different simulator source hash;
never use its explore gate or overwrite its artifacts. This exploration
estimates the repeat cost/reliability frontier, not novelty or holdout
confirmation. Keep 35001--35040 and 36001--36040 sealed.
