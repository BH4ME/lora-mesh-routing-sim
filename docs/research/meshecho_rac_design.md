# MeshEcho-RAC: data-conditioned reverse ACK corridor

Date: 2026-10-03. Status: simulator prototype, pre-development contract.
RAC is a falsifiable simulator hypothesis, not an ICC result, firmware
design, or verified novelty claim. LPR seeds 5001--5020 and DPA seeds 6001--6020 have
already influenced this design; neither may validate RAC. The 4001--4040
holdout remains unopened for this mechanism.

## Research question and core change

Can a single, locally selected off-path relay rescue an ACK whose next
on-path hop did not forward, while improving deadline source-ACK delivery
over both a single ACK and a same-time on-path ACK repeat at less than a
10% upper-confidence-bound full-network TX-airtime penalty? RAC changes
the reverse confirmation algorithm after useful DATA flooding; it does not
change the shared PHY, application trace, or confirmed-route R forwarding.
It cannot repair a DATA packet that never reaches the destination.

RAC uses a data-conditioned corridor, not a global topology query. During
an F flow, a node stores at most two recent upstream senders from FLOODs it
actually decoded. A destination sends one ACK immediately on the first
realized DATA path A. The intended next ACK recipient `v` is encoded by
the path index. An off-path candidate `w` may hear that ACK from downstream
sender `u` and may attempt one delayed relay toward `v` only if it also
heard `v`'s FLOOD for the same flow. If `w` hears `v` forward the ACK before
its timer, it cancels. Candidate timers use local receive time plus
`0.20 + 0.15*((node_id + flow_id) mod 4)` seconds of deterministic backoff;
hidden terminals may still make
several candidates transmit. There is no global one-relay-per-flow oracle.

The extra transmission repeats the same ACK payload but sets an ACK repair
marker. The ACK path field continues to certify the DATA path A and to name
the intended next on-path hop; it is **not** a claim that every physical ACK
transmitter is on A. `w` is an opportunistic transport relay, and the source
may cache A only after receiving a valid in-deadline destination ACK. A
single repair marker prevents a second off-path repair for that ACK. This
decouples ACK transport from the DATA route without adding a second path
list; actual extra hop transmissions and full frame ToA remain charged.

## On-wire and device-local state

- F ACKs in every matched RAC arm carry one modeled `repair_index` byte:
  `255` means the initial ACK, `0` means an off-path relay was used, and `1`
  means an on-path repeat was used. This reuses the
  simulator's existing optional packet byte but has ACK-specific semantics.
  R ACKs are unchanged. Every forwarding/copy operation preserves the byte.
- A valid candidate must decode a FLOOD from `v` and then an unrepaired ACK
  physically sent by on-path `u`, all for matching source, destination,
  flow, request ID, and ACK path. It must be off A, able to relay, and must
  not exceed the configured hop budget. It cannot consult coordinates,
  true PRR, destination-delivery metrics, future receptions, or another
  device's state.
- Per-node F observations are capped at eight live flow keys and two
  upstream senders per key, with 30-s expiry. Per-node pending repair and
  repeat timers are capped at eight live flow/hop keys and expire by the
  application deadline. Duplicate-suppression history expires at the flow
  deadline; unlike pending timers, its peak size is traffic-dependent.
- A recipient `v` processes only the first valid ACK for a flow/path at
  that hop, preventing a successful original ACK and a late repair from
  multiplying upstream forwards. The source accepts only the first valid
  in-deadline ACK and commits the certified DATA path A once.

## Frozen policy arms and controls

1. `meshecho-rac`: single initial ACK on A; an eligible off-path `w` can
   relay once after a 0.20-s local ACK-continuation wait, canceling if it
   decodes `v`'s valid forward.
2. `meshecho-rac-repeat`: same F/R source policy and F ACK marker. After an
   on-path `u` sends an F ACK to `v`, `u` waits 0.20 s after that packet's
   airtime and repeats once unless it decodes `v`'s forward. This is the
   simple local ARQ comparator; its exposure can differ from RAC's because
   `u` and candidate `w` do not observe identical receptions.
3. `meshecho-rac-fr`: the same F/R source policy and F ACK marker, with no
   local ACK rescue. It isolates the full mechanism's reliability and cost.

These arms share the 30-s application deadline, 600-s generation horizon,
630-s TX-cost start window, packet PHY, source route TTL, first-F path
validation, source ACK guard, and application trace. Keep the older DPA
first-path-repeat, DPA diverse, MeshEcho-SR, and stylized product baselines
as clearly labeled external comparisons, not interchangeable controls.
The matched repeat is intentionally allowed to trigger at every on-path
hop even where no off-path candidate exists; measure actual attempts and
airtime, and do not call the event sets identical.

## Implementation and evidence gates

The simulator prototype and its three RAC arms now pass deterministic
real-packet safety/feasibility checks, including duplicate and late ACKs,
TTL and deadline limits, bounded pending/observation state, marker bytes,
charged airtime/energy, and a same-slot candidate collision. These tests
do not imply a population-level gain or hardware feasibility.

Build one public-behavior red/green vertical slice at a time: a diamond
where `u -> v` ACK reception fails but `u -> w -> v` succeeds; an on-path
continuation that cancels the candidate; a repeat-arm rescue; no DATA
observation/no repair; duplicate and late ACK suppression; one-repair cap;
bounded state/expiry; source-origin/path validity; byte/airtime/energy
accounting. Include an adverse case where a redundant candidate collides.
Record per-flow F delivery, ACK stage, candidate exposure, cancellation,
repair TX, source acceptance, subsequent R state, and actual full TX cost.

After full regression, run one non-evaluable seed-7000 smoke and one frozen
20-seed development matrix on 7001--7020. Never use 5001--5020 or
6001--6020 as independent RAC evidence. Predeclare a joint primary gate:
for RAC minus each of `rac-fr` and `rac-repeat`, the nominal seed-paired
two-sided 95% ACK-PDR lower bound must exceed zero and the upper bound of
relative complete-network TX-airtime change must stay below +10%.
Mechanism exposure requires at least 20 eligible corridor events across
at least ten seeds. Report destination PDR, ACK delay, per-hop/repeat TX,
collisions, route commits, bytes and energy regardless of outcome. These
are author-chosen project gates, not ICC acceptance rules; the two marginal
intervals are not multiplicity-adjusted. Do not tune the 0.20-s wait or
candidate rule after viewing this cohort. A structural revision gets a new
development split. Open 4001--4040 once only if frozen RAC passes all
development gates, then run random-pair and radio/load robustness.

## Prior-art boundary

DSR (RFC 4728, DOI 10.17487/RFC4728) already separates the return path of
a route reply from the discovered forward route. AODV (RFC 3561, DOI
10.17487/RFC3561) addresses reverse route state and RREP acknowledgment.
ExOR (DOI 10.1145/1080091.1080108), Bypass Routing (DOI
10.1016/j.adhoc.2004.10.004), and opportunistic LoRa routing (DOI
10.1109/WoWMoM57956.2023.00065) cover opportunistic relays and related
repair ideas. RAC cannot claim to invent alternate ACK paths or local
forwarding. A possible distinction is the bounded, actually decoded
DATA-conditioned reverse ACK continuation rule under LoRa full-packet
airtime and application deadlines. That exact combination and any benefit
still require wider literature verification and matched positive evidence.
