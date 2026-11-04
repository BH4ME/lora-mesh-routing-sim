# MeshEcho feedback-core research question brief

Date: 2026-10-04. Stage: scoping, not an algorithm contract or a result.
The user's standing objective is a substantive MeshEcho-SR core rewrite and
ICC paper revision. The fixed-2-s FLOOD ACK control is now a strong simple
comparator, not a candidate contribution.

## Primary question

Can a bounded, node-local feedback controller improve deadline source-ACK
delivery over fixed-2-s destination ACK delay without increasing complete-
network LoRa airtime?

## FINER assessment (provisional)

| Criterion | Score | Basis |
| --- | ---: | --- |
| Feasible | 3/5 | Current simulator exposes decoded packets, local timers, and TX queues; the useful local signal and safe state bound remain unproved. |
| Interesting | 5/5 | In 38001--38020, fixed waiting materially improved source ACKs over immediate ACK under matched traffic. |
| Novel | 2/5 | ACK waiting, repetition, and multipath ACK are prior art; a distinctive controller and close-source verification are still missing. |
| Ethical | 5/5 | Packet-level simulation poses no participant risk; false novelty or hardware claims must be avoided. |
| Relevant | 5/5 | Deadline confirmation and channel occupancy are directly relevant to constrained LoRa mesh operation. |
| **Average** | **4.0/5** | Provisional; novelty is the gating criterion. |

## Boundaries and subquestions

In scope: same 30-s application deadline, complete TX airtime, source ACK
and destination delivery reported separately, MCU-bounded state, actual
on-wire bytes, fresh paired development and untouched holdout, immediate
and fixed-2-s ACK controls, and same-budget ACK repetition. Source choices
may use only locally decoded packets and timers. Out of scope: treating
simulation-global delivery/collision state as a protocol input, describing
stylized Meshtastic/MeshCore models as firmware measurements, or claiming
radio hardware validity without calibration/measurement.

1. What destination/relay observations before ACK transmission actually
   predict a safer ACK time or path beyond a fixed 2-s wait?
2. Can a bounded source/recovery rule use those observations through a real
   packet signal, or must it act safely under the no-ACK ambiguity?
3. Does the resulting full protocol beat the strongest simple control on
   the prespecified joint reliability/airtime gate in more than one workload?

## Alternatives screened at scoping

| Candidate question | Preliminary FINER average | Concern |
| --- | ---: | --- |
| Node-local feedback controller versus fixed-2-s ACK | 4.0/5 | Selected for exposure/prior-art screening; novelty unverified. |
| Source-only timeout threshold versus fixed R/F | 3.4/5 | No-ACK cannot identify forward DATA versus reverse ACK loss; novelty below 2/5. |
| Extra destination certificate versus same-path ACK repeat | 3.2/5 | Functionally another ACK; earlier CLAR/BAR controls failed incremental gates. |

Next gate: inspect already saved delayed-arm receptions for a truly local
adaptive signal and check directly related ACK-waiting literature before
writing behavior code or opening fresh seeds. A positive exposure is only
necessary, not evidence of benefit or originality.
