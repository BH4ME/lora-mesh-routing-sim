# MeshEcho ACK-proven route promotion candidate

Date: 2026-10-05. Status: unfrozen source-core hypothesis. This is neither
an ICC method nor a measured improvement. Keep `meshecho-dcb` unchanged as
the no-promotion control. No 47xxx/48xxx seed is authorized by this note.

## Observation and decision

The existing DCB relay can physically forward a current direct R DATA over
the nominated `(source, relay, destination)` path. A marked reverse ACK that
passes DCB's source-side flow, epoch, path, physical-sender and original
deadline checks is the source's first device-visible proof that this exact
two-hop path carried and confirmed the current application flow. Nomination
in an older F ACK, current DATA overhearing, a relay timer, or destination
delivery in simulator metrics is not enough to commit a route.

In a separately named `meshecho-dcb-promote` candidate, the first accepted
marked backup ACK for a flow promotes its ACKed path to the source's next
confirmed route generation. This is permitted only if the original direct
route and certificate generation are still current when the ACK arrives.
The new route's commit generation is the just-ACKed flow ID, its lifetime
starts at ACK reception, and the old direct-route certificate is cleared.
An accepted direct R ACK retains the direct route; an accepted F ACK keeps
the existing realized-F route commit. An older, duplicate, late, malformed,
wrong-sender, wrong-epoch or merely nominated path cannot replace a newer
route. The following application uses the promoted path as its normal R
route if still valid, with all physical DATA/ACK transmissions charged.

This first vertical slice changes route state and subsequent source actions,
but it still inherits SR's F/R/D selector and DHR's 15-s recovery. A complete
replacement of the source controller remains required. Do not describe this
slice by itself as the requested full core rewrite. Route switching after
acknowledgement has DSR-like precedents; the possible research question is
whether DCB's physically confirmed local repair can supply useful online
route evidence under LoRa cost, not whether route switching was invented.

## Test and evidence boundary

Write one public end-to-end RED/GREEN test: first useful F yields a direct
ACK with a nominated two-hop relay; the next direct R DATA fails on the
primary but is physically backed up; its marked ACK reaches the source;
the next application sends R on exactly that proven two-hop path. Compare
the same flow under unchanged `meshecho-dcb`, which retains the direct
primary. Add separate generation/late-ACK tests before any population run.

The candidate must have a same-wire no-promotion control plus an
ACK-unproven first-alternate route-switch control. Compare per-seed all-
scheduled-flow deadline source ACK and destination PDR, complete-network
TX airtime/energy, physical backup ACK count, later route/action divergence,
queueing and collisions. Count only route changes caused by first accepted
in-deadline backup ACKs; a passive 46xxx nomination is not exposure. The
three inspected 49101--49103 pilot seeds are development diagnostics, never
untouched confirmation. A future contract must freeze new disjoint seed
cohorts, source hashes and a quantitative go/no-go gate before simulation.
If proven backup paths are rare or subsequent routing is worse than the
same-wire controls, reject promotion and seek a different full core.
