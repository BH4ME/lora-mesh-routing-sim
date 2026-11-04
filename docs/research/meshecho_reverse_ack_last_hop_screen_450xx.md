# Reverse-ACK last-hop opportunity screen (45001--45020)

Date: 2026-10-05. Status: read-only post-exploration screen, **not** a new
protocol trial or an ICC result. The 450xx first-hop-receipt exploratory
cohort and its manifest were already opened and independently audited. This
screen used only saved JSONL; it did not rerun any seed or open a holdout.

## Population and join

Archive prefix:
`results/meshecho_first_hop_receipt_explore_45001_45020_v2_20261005`.
The manifest sidecar and archived artifact digests match the saved archive;
all 20 run rows report stock parity and strict replay. Select flow rows
where `delivery_by_deadline=true` and `ack_by_deadline=false`, then join
ACK transmissions by `(seed, flow_id)` with ACK origin equal to the flow
destination and final destination equal to its source. An ACK TX is an
actual physical transmission, not proof of reception. A final reverse-hop
TX has `packet.path_index == 0` and sender equal to `packet.path[1]`.
The deadline is the flow's original `enqueued_at + 30 s`; for the timing
counts here the ACK TX must **end** by that deadline.

## Saved-trace counts

| Measure | Result |
| --- | ---: |
| Scheduled flows | 783 |
| Destination delivered by deadline | 778 |
| Source ACKed by deadline | 742 |
| Delivered but source-unACKed | 36 |
| At least one destination-originated ACK TX by deadline | 36/36 |
| At least one final reverse-hop ACK TX ending by deadline | 30/36 |
| Final-hop direct destination-to-source / multihop relay-to-source | 24 / 6 |
| ACK chains without final-hop TX | 6 (five stop after destination TX, one after a relay TX) |
| Final-hop TX records for the 30 flows | 32 |

For the 30 flows, slack from the **earliest** final-hop TX end to the
original deadline ranges from 11.427221 to 29.851008 s (median 12.856128
s). Each has at least 5 s nominal slack; a one-hop ACK packet is at most
0.056576 s of nominal radio airtime here. This is only an airtime/deadline
feasibility bound: queueing, half-duplex, interference, fading, and actual
decode were not counterfactually measured. Nineteen of the 30 first
final-hop ACK transmissions overlap some other physical TX, including two
overlapping source TXs; 11 have no TX overlap. Overlap alone does not prove
collision, and absence of overlap does not prove that fading caused loss.

The saved action log has one `dhr_source_ack_rx` callback for a target
flow at an off-index ACK path hop (seed 45016, flow 20). It was not an
accepted source ACK and must not be counted as successful final-hop
reception. No target's final-hop TX produced an accepted source ACK by the
original deadline.

## Decision boundary

The silent last-hop sender cannot know whether the source decoded its
ACK. An event-driven selective retry therefore needs a charged,
device-observable source-confirmation contract, including its own loss and
timing behavior. An unconditional extra copy is a simple comparator,
not a rewritten algorithm; on 24 direct paths it is literally a second
destination ACK. The already audited 41001--41020 fixed-2-s plus
same-path-repeat arm is the closest strong archived control, though it
uses a separate seed cohort and cannot be treated as a paired effect for
450xx. Its exploratory paired ACK-PDR gain over fixed-2-s single ACK was
+0.01956, with +1.769% relative whole-network airtime; destination-PDR
change was -0.00572. A source-adjacent relay-only repeat has at most six
distinct multihop target flows in this archived residual population.

This screen rejects treating a last-hop ACK repeat or its nominal timing
window as the new MeshEcho-SR core. It does **not** reject all reverse-ACK
mechanisms or estimate a new policy's effect. A prospective core must
show a device-local decision branch that materially differs from fixed
2-s ACK and matched repeat, account for every signal byte and all network
TX airtime, and survive fresh development and untouched holdout tests.

Primary records: `docs/research/meshecho_first_hop_receipt_explore_results.md`,
`docs/research/meshecho_delayed_ack_repeat_control_design.md`, and the
saved manifest/flow/action/transmission JSONL under the archive prefix.
