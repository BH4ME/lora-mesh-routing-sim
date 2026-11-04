# Flood reverse-ACK path feasibility screen

Date: 2026-10-04. Status: exploratory, read-only diagnostic contract. This
is not a new routing algorithm, a performance result, or an ICC claim.

## Question and motivation

In the frozen DHR development cohort, the same-trigger fixed-F arm delivered
799/803 unicasts to destinations but produced only 570/803 deadline source
ACKs. Of its 229 delivered-unACKed flows, 224 had no source ACK receive
callback. That gap motivates a local opportunity question: after the first
useful FLOOD reaches a destination, does it physically decode a distinct
inbound path soon enough to choose a different reverse ACK route?
The arm is `meshecho-dhr-flood`: F is its fixed recovery action, not
necessarily the first action for every flow. The aggregate 229-flow gap
does not tell us how many flows were delivered by FLOOD; report that
denominator separately before estimating this branch's reach.

The current source and destination behavior is fixed. `Simulator.handle_tx_end`
passes every successfully decoded packet to `protocol.on_receive`, but
`CalmMesh.on_fallback` acknowledges the first copy and returns on duplicates.
`send_ack_on_reverse_path` immediately uses the first copy's reverse path.
The observer must not alter these outcomes or suppressions.

## Observation and reporting contract

- Use new exploratory seeds, not any inspected development or holdout split.
  Reproduce the fixed-F runner's application trace hash, scheduled flow count,
  destination delivery count, and deadline source ACK count for each seed.
- Count each destination's physically decoded `FLOOD` copy at `on_receive`,
  including copies the current protocol will ignore as duplicates. Define a
  distinct candidate by its full inbound path ending at that destination,
  not merely by a new final transmitter. Report first-arrival-relative
  windows of 0.25, 0.5, 1.0, and 2.0 seconds separately.
- Stratify by on-time delivered-and-ACKed, on-time delivered-but-unACKed,
  and undelivered flows, and separately by whether first delivery was a
  FLOOD. Include the share of *all* delivered-unACKed flows to which the
  FLOOD-path question applies. Report path length and last-hop RSSI/SNR/SINR
  available at reception; do not call model-known upstream PRR a device-local
  observation. If an aggregate link-quality field is absent from `FLOOD`,
  state that limitation explicitly.
- Keep the original 30-second application deadline visible. A path received
  after that deadline cannot be an in-deadline alternative even if it is
  physically distinct. A future delayed-ACK mechanism must charge waiting,
  all ACK/control transmissions, collisions, and any changed DATA forwarding.
- Do not infer alternate-path ACK success from a link PRR product or from the
  original path's observed ACK outcome. These are potential-action exposures,
  not causal per-flow counterfactuals.

## Decision boundary after the screen

If fewer than roughly 5% of all delivered-unACKed flows have a distinct
locally observed FLOOD path by 1 second, this branch cannot plausibly
explain the bulk of the fixed-F ACK gap and should not be the primary new
core. Report the within-F percentage too, so a rare F event cannot make a
large conditional percentage look like broad coverage. If exposure is
substantial, next trace actual reverse ACK failure hops and compare a
predeclared, locally computable selector with first-arrival and simple
shortest-path or matched-score controls. The 5% rule is an exploratory
go/no-go heuristic, not a significance test or a promised performance gate.

Any candidate still needs a separate answer for first-hop R DATA failures.
A reverse-F-ACK branch alone is not a complete replacement for MeshEcho-SR.
The generic notions of multipath forwarding, opportunistic candidates, and
passive/explicit ACKs are established prior art; novelty of a particular
LoRa deadline/airtime/half-duplex decision remains unverified. A broad
Crossref phrase search for reverse ACK path choice returned mostly generic
wireless multipath work and is not a clearance search.

A targeted DOI/abstract verification adds a direct caution: Lee et al.,
"Avoiding Spurious Retransmission over Flooding-Based Routing Protocol for
Underwater Sensor Networks," *Wireless Communications and Mobile
Computing* (2020), DOI `10.1155/2020/8839541`, explicitly describes both
DATA and ACK traversing multiple flood routes and a waiting-time rule based
on ACK-copy path similarity. It is not a demonstrated duplicate-DATA-to-
single-reverse-ACK selection under LoRa, but it rules out any broad
"first multipath ACK" claim. Joy and Branch's "Flooding in LoRa Mesh
Networks" (ITNAC 2024), DOI `10.1109/ITNAC62915.2024.10815298`, is
relevant to duplicate LoRa reception. AODV (RFC 3561) establishes reverse
reply paths. Close novelty remains unverified pending fuller source review.
