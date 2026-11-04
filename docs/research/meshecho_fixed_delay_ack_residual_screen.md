# Fixed-2-s ACK residual screen

Date: 2026-10-04. Read-only forensic screen of the already opened
38001--38020 delayed-ACK exploratory artifacts. This is neither a new
simulation run nor a causal comparison or a core-algorithm result.

## Population and reverse path

The delayed arm contains 781 scheduled flows, 726 in-deadline source ACKs,
and 770 destination deliveries. The 55 source-ACK misses comprise 11
destination non-deliveries and 44 delivered-but-unACKed flows. Of the 44,
42 had a first destination FLOOD decode and matching destination FLOOD ACK
TX; two were routed DATA deliveries with an immediate DATA ACK and no
FLOOD decode. All 42 FLOOD ACKs started exactly 2 s after the first
decode, ended before the original per-flow deadline, and their last
recorded reverse-path TX ended at least 10.6845 s before that deadline.
Of those 42, 12 were initial FLOODs (`repair_index=null`) and 30 were
same-flow recovery FLOODs (`repair_index=2`) after a routed DATA attempt.
This 12/30 split was independently recomputed from the saved flow JSONL.

Among those 42 reverse chains, 22 had a direct ACK path, 15 a two-hop path,
and five a three-hop path. Five chains stopped before completing all relay
TXs; 37 reached the final transmission toward the source, but none yielded
an accepted source ACK. At each last observed ACK TX, the intended next hop
was not transmitting. Some other TX overlapped that ACK in 25/42 chains;
17/42 had no overlap. Overlap establishes collision opportunity only, not
an actual physical collision; the saved artifacts do not retain all
per-receiver power and RX-failure outcomes needed to classify those misses.
The unobscured failures are compatible with link PRR/fading, but cannot be
assigned a unique cause from these records.

During the fixed wait, 40/42 of these flows had 89 additional destination-
decoded same-flow FLOOD copies on paths distinct from the first. Relative
to the first path, zero were shorter, ten equally long, and 79 longer.
These are locally observable alternative path *candidates*, not evidence
that any would have delivered the ACK. The saved logs include first-receipt
path and destination action times, but not per-candidate destination
RSSI/SNR or counterfactual reverse reception. A candidate using path
quality must charge and validate its actual on-wire margin field; forward
margin is not measured reverse-link success. All 5,891 saved FLOOD TX rows
have null forward-margin fields, so this run cannot retrospectively score
the alternative paths by a packet-carried whole-path quality metric.

## Design consequence

The principal residual problem after fixed 2 s is reverse confirmation,
not simply insufficient ACK waiting or late deadline admission. Quiet-only
ACK timing leaves the source's F/R/D and ambiguous 15-s miss rule intact.
Choosing a different decoded path at the same 2-s timer is a testable
component, but existing BAR/DPA negative comparisons and conventional
multipath routing make it an unproven core claim. A full rewrite still
requires a source/feedback state-machine contract and prospective evidence
against fixed 2 s, same-budget ACK repetition, and fixed source recovery.

Provenance: `results/meshecho_delayed_ack_control_explore_38001_38020_20261004.manifest.json`
and its saved `flows`, `actions`, and `tx` JSONL artifacts, joined by seed,
flow ID, event time, ACK path, and hop transmission order. This screen was
independently delegated but was not a new frozen or strict-replay audit; the
underlying paired run's earlier manifest/replay audit is documented in
`meshecho_delayed_ack_control_explore_results.md`.
The flow denominator and 55/44/42 split were independently recomputed
from the saved `flows` JSONL with `jq`; this screen did not rerun a simulator.
