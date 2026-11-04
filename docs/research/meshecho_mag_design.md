# MeshEcho-MAG controller contract (development hypothesis)

Date: 2026-10-03. Status: development revision 3, not a validated
performance result. MAG means margin-and-airtime-gated route
refresh. It replaces the fixed-age decision rule in MeshEcho-SR; the packet
flood, source-route forwarding, destination candidate collection, and
source-ACK confirmation machinery remain shared and testable separately.

## Source-observable evidence

Every MAG DATA and useful-DATA FLOOD starts with one signed-byte forward
margin field at the `unmeasured` sentinel 127. A successful receiver
quantizes `SNR - required_SNR(SF)` to half-dB units, clamps it to
[-126, 126], and takes the minimum with the inbound field. The destination
copies this minimum into the application ACK. Only an ACK received by its
application deadline may update the source's route-margin history. A missing
ACK is a failure of end-to-end confirmation, not a measured low forward SNR.
An absent optional field is distinct from zero and negative values. MAG and
its matched controls pay the same extra DATA/FLOOD and ACK byte. RREQ
candidate ranking uses a monotone quantization of successfully received
SNR margin, not the simulator's PRR function.

Development revision 3 bounds proactive RREQ propagation to the confirmed
path's hop count plus one, capped by the configured network maximum. The
extra hop permits a local detour; it does not guarantee discovery of every
alternative. MAG and the periodic-D control use this same bound. Lost-RREP
fallback and the source application deadline remain unchanged. The current
destination collection and source wait still use the conservative configured
network maximum, so this revision targets transmission cost, not claimed
latency reduction.

Per destination, the source retains a confirmed route, the last two ACKed
forward margins on that route, last successful ACK time, the last two local
application-send times, recent R ACK failures, cooldown, and pending D state.
No simulator coordinates, hidden delivery flag, true PRR, future traffic,
or network-wide airtime may enter a decision. Source route slots are capped
at eight with six-hop paths. The simulator's diagnostic flow maps are not
equivalent to a bounded firmware implementation.

## Decision rule

The constants below are starting hypotheses. Tune or reject them using only
development seeds 3001--3020. Freeze the final rule before the untouched
4001--4040 holdout.

```text
if no unexpired ACK-confirmed route: F
else if two consecutive R source-ACK misses: F
else if no margin sample or last source ACK is older than 300 s: F
else:
    risk = (latest_margin <= 3 dB)
        or (previous_margin - latest_margin >= 3 dB
            and latest_margin <= 6 dB)
    if not risk: R
    else if recent local demand, D token and 300-s cooldown,
            discovery-plus-data fits the common application deadline,
            and source-estimated full D airtime <= 1.10 * F airtime: D
    else: R
```

Recent demand means at least two earlier sends to this destination in the
preceding 300 s. D uses one source-wide token, initially available and
replenished after ten local application unicasts. Its candidate DATA is sent
once, without a hidden rescue copy. A returned RREP is tentative; only an
ACK for that flow's candidate DATA may commit it. Failed D retains the old
route and sends one fallback DATA according to the existing SR contract.
F sends the current useful DATA and may learn a confirmed route from its ACK.
Route age determines expiry, not proactive D by itself.
After development revision 1 failed the airtime gate, a risk signal by
itself no longer launches an F when D is rejected: a route still confirmed
by ACK and not stale or twice failed is reused. This change was chosen from
development evidence; its own result requires a separately identified replay.

The source uses its radio's packet-length ToA for the following local cost
proxy, with a configured rebroadcast budget `B=16` and confirmed route hop
count `H` (or configured maximum when cold):

```text
C_D = B*T(RREQ at the capped repair path length)
      + H*(T(RREP)+T(DATA)+T(ACK))
C_F = B*T(FLOOD-DATA at maximum path length) + H*T(ACK)
```

The source cannot know how many relays actually transmit or how much future
contention occurs. `C_D <= 1.10*C_F` is a heuristic gate, never a guarantee
on whole-network cost. Actual network-wide TX airtime, source-confirmed PDR,
destination PDR, delay, control TXs, and D exposure are measured separately.
The deadline gate reserves the PHY/hop-aware source RREP wait, path DATA/ACK
ToA, and a documented queue margin inside the common 30-s application
deadline. Its prediction is audited against actual deadline misses.

## Falsification and comparison

Use identical topology, application trace, radio, ACK definition, frame
fields, and seed pairing for MAG and its matched controls:

- Old fixed-age MeshEcho-SR, clearly labeled as a different decision rule.
- F/R-only: first useful-DATA flood, confirmed-route reuse, and flood after
  the same failure/staleness conditions, with no proactive refresh.
- Same-trigger F: every MAG D trigger uses useful-DATA flood instead.
- Equal-token periodic D: identical discovery budget and packet contract,
  but a fixed-age trigger instead of measured-margin risk.

The primary claim gate is paired source-ACK PDR gain with 95% lower bound
above zero against F/R-only **and** same-trigger F, while the 95% upper
bound on relative whole-network TX-airtime cost is below +10% against both.
The +10% is an author-chosen cost budget, not a venue rule. If D is rare,
duplicates periodic D, or fails those gates, report the negative result and
prefer the simpler F/R controller. The prior 20-seed SR run is exploratory
only because its destination collection window was too short for four-hop
RREQ arrivals. Correct the discovery timing before running a new matrix.

This specification does not imply measured nRF52/ESP32-S3 performance,
firmware parity, novelty over all prior routing literature, or an ICC
acceptance probability. Hardware memory, current, duty-cycle, and SNR
calibration remain separate validation tasks.

## Development decision (2026-10-03)

Three separately recorded 20-seed development revisions were evaluated
after the PHY-aware discovery-timing correction. Revision 1 used F after
rejected risk; revision 2 reused the confirmed route; revision 3 also capped
proactive RREQ at confirmed route hops plus one. On revision 3, MAG minus
matched F/R-only has +0.1556 deadline ACK PDR (95% paired CI
[0.1066, 0.2045]) and +0.050 relative whole-network TX airtime
([-0.027, 0.128]). The predeclared +0.10 airtime upper-bound criterion
therefore still fails. MAG beats same-trigger F on the development gate but
has no clear ACK gain over equal-token periodic D. The reserved 4001--4040
holdout was not opened. These results are development evidence only, not a
confirmed ICC claim. See the three versioned research manifests in `results/`.
