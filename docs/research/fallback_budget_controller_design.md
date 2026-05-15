# Fallback Budget Controller Design

Smart-CALM v1.1.3 replaces the v1.1.2 instant threshold fallback cap with a
small fallback budget controller (FBC).

## Literature Basis

- RPL metric guidance says low-power lossy links change quickly, so dynamic
  metrics should be smoothed and use multi-threshold schemes to avoid routing
  oscillation.
- MRHOF keeps path selection stable with hysteresis: it does not switch just
  because a candidate is slightly better.
- Trickle uses suppression so redundant transmissions stay low when state is
  consistent, while still reacting quickly to inconsistency.
- Broadcast-storm work shows plain flooding creates redundancy, contention, and
  collision, so fallback rescue needs an explicit budget.
- ETX motivates using expected transmission cost and link reliability rather
  than hop count alone.

## Controller

FBC computes a pressure score from four MCU-friendly counters:

- collision failures per transmission
- fallback forwards per unicast flow
- transmissions per minute
- current unicast miss ratio

The score is smoothed with an EWMA and mapped to three states:

- `0`: open, use the active rescue TTL
- `1`: moderate cap, limit timeout fallback TTL to `2`
- `2`: strong cap, limit timeout fallback TTL to `1`

The controller reacts quickly to high pressure but exits slowly with hysteresis.
This is meant to preserve rescue behavior under real reachability pressure while
preventing fallback from amplifying congestion.

## Boundary

Route-miss recovery is still conservative by default. FBC only controls late
timeout rescue after Smart-CALM has already selected the rescue profile.

