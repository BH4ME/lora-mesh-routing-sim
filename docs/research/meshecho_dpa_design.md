# MeshEcho-DPA: data-path acknowledgment diversity (development contract)

Date: 2026-10-03. Status: design recorded before implementation; simulator
prototype and controls are being built, with no fresh development run yet.
This is not an ICC result or a novelty claim.
The LPR 5001--5020 outcome and passive 5001--5003 path/timing diagnostics
motivated this design; neither cohort is independent validation. The
4001--4040 holdout remains unopened.

## Question and algorithm boundary

Can a destination-confirmed, DATA-first route acquisition return an in-deadline
source ACK more often than both single-path confirmation and an equal-trigger
extra ACK, with less than a 10% upper-confidence-bound airtime penalty? DPA
replaces MeshEcho-SR's RREQ/RREP-before-DATA acquisition with useful-DATA
flooding and at most one second reverse ACK along an actually decoded,
source-adjacent-diverse path. It leaves the shared packet-level PHY, complete
packet airtime, F/R source action rule, and confirmed-route forwarding intact.
It does not claim to fix an R flow whose DATA never reaches the destination.

The three frozen policy arms are:

1. `meshecho-dpa`: first destination-decoded FLOOD receives an immediate ACK
   on its realized path; the first eligible later copy receives one additional
   ACK on that later copy's realized path.
2. `meshecho-dpa-fr`: identical F/R data plane and packet fields, but only
   the first ACK. This isolates the bundle's gain and total radio cost.
3. `meshecho-dpa-repeat`: the same second-copy eligibility event and time as
   DPA, but the additional ACK repeats the first realized path. This tests
   whether diversity helps beyond simply transmitting another ACK. It may
   have a different path length; report complete actual airtime, not an
   imaginary equal-airtime claim.

No arm makes a preliminary RREQ/RREP attempt on F. All three use the same
source F/R decision, traffic trace, reception RNG policy, source ACK guard,
30-s application deadline, 600-s generation horizon, and 630-s TX-cost
window. The source accepts only the first valid in-deadline ACK and commits
its carried route once; later ACKs cannot cause a second delivery or route
overwrite. A valid source ACK must name the registered destination as its
origin and carry a path whose endpoints match the registered source and
destination. ACKs carry no application payload. The existing path encoding
and flow/request IDs suffice; no new modeled on-wire field is allowed.

## Destination-local rule

The destination starts a 3.0-s local window upon its first successfully
decoded FLOOD copy for `(origin, flow_id, request_id)`. It delivers the
application payload once, stores the first loop-free realized path, and sends
the first reverse ACK immediately. A later FLOOD copy is eligible only if
it was physically decoded before that local window closes, carries the same
flow identity and destination, yields a loop-free path of at most `max_hops`
edges, differs from the first path, and has a different source-adjacent hop
(`path[1]`). The destination sends at most one second ACK for this flow,
immediately when the first eligible copy is decoded. Intermediate relays
retain first-copy duplicate suppression, and the destination never forwards
or re-delivers a later copy. Destination state is capped at eight active
FLOOD windows per node and expires after 3.0 s; evict the oldest expiration
when full. Duplicate packets after eviction/expiry remain suppressed by the
existing FLOOD seen set and cannot reopen a window.

All inputs are device-observable: packet IDs and path, local receive time,
and local active-window state. `Packet.created_at` is simulator metadata,
not an on-wire timestamp, so the destination must not consult it or the
source's application deadline. No hidden topology, future traffic, global
PRR, destination-delivery oracle at the source, or post-hoc collision status
may enter the policy. The radio's half-duplex and collision rules determine
which later copies are actually decoded; extra ACKs may reduce that set.

## Implementation and falsification order

Use one red/green public-behavior test at a time: two distinct decoded FLOOD
paths yield exactly two destination ACK transmissions in DPA but one in F/R;
repeat sends its second ACK on the first path; same-first-hop, looped, late,
and third paths do not send another ACK; the source's first valid ACK alone
commits; later/invalid ACKs do not. Confirm both policies charge actual
path-dependent bytes, hop transmissions, airtime, collisions, and energy.
Record destination first/second path arrival, second-ACK start and route,
first/second ACK source arrival, source commit path, duplicate suppression,
and per-flow deadline outcome. Keep diagnostic state bounded and action logs
separate from simulated device state.

Action logs use `dpa_first_path`, `dpa_second_path`, `dpa_ack_tx`, and
`dpa_source_ack_rx`; the latter separates physically decoded off-path ACKs
from route-matched ACKs with `on_path`, and first acceptance with `accepted`.

After the full test suite and a single non-evaluable seed-6000 smoke, run
one complete 20-seed development matrix on 6001--6020 with a frozen case,
source/design hashes, complete run/flow/action artifacts, and seed-paired
analysis. Do not inspect 4001--4040. The prespecified primary gate requires
the lower bound of the nominal two-sided seed-paired 95% ACK-PDR difference
to exceed zero against **both** controls, and the upper bound of paired
relative whole-network TX-airtime change to stay below +10% against both.
Mechanism exposure requires at least 20 eligible second-path opportunities
across at least ten of the 20 seeds. These are project evidence gates, not
ICC acceptance rules; intervals are marginal, not multiplicity-adjusted.
Destination PDR, tail delay, ACK transmissions, source-adjacent diversity,
collisions, cache commits, actual packet bytes/airtime, and adverse cases
must be reported whether or not the gate passes. No post-hoc threshold or
window tuning on 6001--6020. A structural revision would get new 7001--7020
development seeds; only a frozen surviving design may enter the once-only
4001--4040 holdout, followed by independent PHY/load and unconditioned
random-pair robustness.

Multipath discovery and redundant ACK concepts have prior art. DSR (RFC 4728,
DOI 10.17487/RFC4728) can return destination replies for multiple received
request paths and may piggyback small data on a route request; AOMDV (DOI
10.1002/wcm.432) provides alternate loop-free routes. LoRa flooding (DOI
10.1109/ITNAC62915.2024.10815298) and opportunistic LoRa mesh routing
(DOI 10.1109/WoWMoM57956.2023.00065) are also established. A bounded search
has not verified this exact useful-DATA/two-delivery-ACK/source-commit
combination, but that is not proof of global novelty. The defensible claim
requires a measured LoRa deadline/airtime tradeoff against the controls and
DSR-style discovery, not a "first multipath ACK" assertion. The current ICC
manuscript remains the 2.1.26 calibrated-route comparison until evidence
supports a truthful major rewrite.
