# Destination-local ACK quiescence exposure

Date: 2026-10-04. Status: read-only screen on already opened
38001--38020 fixed-2-s delayed-ACK exploratory artifacts. This is not a
closed-loop algorithm trial, novel-method claim, or ICC result.

## Device-visible boundary

`Simulator.handle_tx_end` calls protocol `on_receive` only after a physical
decode succeeds. A destination can then see the FLOOD's wire-carried origin,
flow/request ID, path, TTL, repair marker, local receive time, sender, and
plausible RSSI/SNR. DHR logs destination FLOOD receptions before the base
duplicate-suppression return, so locally decoded copies are observable even
when no further delivery/ACK action follows. A real node cannot read the
simulator's global collision counts, future transmissions, other nodes'
queues, or whether the source received an ACK. `Packet.created_at` is not
on wire, so the destination cannot infer the source's original 30-s deadline
from that field. These restrictions govern any future controller.

## Saved-trace screen

The independent read-only join matched all 251 delayed-arm first-FLOOD
receipts to a destination `dhr_destination_rx` action and matched ACK TX.
Each observed first ACK started exactly 2.0 s after that first decode.

| Exposure in first 2 s | Flows |
| --- | ---: |
| At least one later successful same-flow FLOOD decode | 235/251 (93.6%) |
| First duplicate by 0.25 s | 48/251 |
| First duplicate by 0.5 s | 86/251 |
| First duplicate by 1.0 s | 197/251 |
| First duplicate by 2.0 s | 235/251 |
| No later successful decode by 2.0 s | 16/251 |

There were 539 duplicate-decode events within the two-second window. The
first duplicate's delay from first receipt had median 0.614 s, p90 1.153 s,
and range 0.098--1.862 s. Exposure spans all 20 seeds; each has 10--22
first-FLOOD receipts and 9--21 with a local duplicate in that window.
At the fixed ACK start, the backward interval since the last successful
same-flow decode was at least 0.25 s for 223/251, at least 0.5 s for
180/251, and at least 1 s for 85/251. Yet 47/251 flows had 54 further
successful destination decodes after the 2-s ACK start; the earliest was
at +2.158 s. Global timing shows 20/251 flows with a same-flow FLOOD TX
overlapping destination ACK airtime, but overlap alone does not establish
that those transmissions could have decoded locally.

## Decision boundary

These records establish variation in a **local observation**, not that a
quiet-window rule improves outcomes. Sending earlier or later changes
half-duplex, interference, subsequent FLOOD decodes, source retries, and
future traffic; even post-2-s observations are conditioned on the actual
fixed-delay ACK. A device-local candidate could retain a bounded pending
record for the first FLOOD, update its last-decode time on duplicates, and
send one same-path ACK when a local quiet timer fires subject to a fixed
maximum hold. Its quiet threshold, minimum hold, capacity/retirement, and
source recovery deadline must be specified before implementation, not fit
after seeing the new trial. It must compare with immediate ACK, fixed 2 s,
and same-budget same-path ACK repetition. The DHR source admission bound
currently omits the ACK hold; a full-core design must account for that
delay at actual TX start. No new seed or source/paper code follows from
this screen alone.
