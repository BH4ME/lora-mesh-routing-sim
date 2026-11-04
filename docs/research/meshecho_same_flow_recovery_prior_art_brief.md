# Research brief: same-flow recovery after MeshEcho-SR route failure

Date: 2026-10-04. Mode: targeted quick research brief. This brief used
AI-assisted source discovery and synthesis; titles, authors, dates, DOIs,
and the cited abstracts or RFC passages were checked against Crossref,
OpenAlex, or the RFC Editor. It is not an exhaustive novelty search.

## Question and scope

Can a source-local, deadline-limited recovery decision for an unACKed
MeshEcho-SR routed DATA flow improve deadline source-ACK delivery while
containing *complete-network* LoRa airtime, compared with fixed-time route
repeat and fixed-time flood fallback? This question concerns simulated
unicast R flows after an ACK guard, not a claim about Meshtastic/MeshCore
firmware, a hardware testbed, or a first invention of ARQ or route repair.

The failed frozen CLAR development set motivates the target, but cannot
validate a successor: among 279 CLAR unACKed flows, 196 were R DATA
non-deliveries. Its source ACK guard fired about 15 s before the 30-s
application deadline for those misses. This is an observed opportunity
window, not proof that a retransmission would work or satisfy an airtime
constraint [7].

## Verified prior-art boundaries

1. AODV specifies route-error handling and local repair, including
   buffering currently undeliverable packets while a repair request is
   attempted [1, Secs. 6.11--6.12]. DSR specifies route maintenance and
   packet salvaging [2, Secs. 3.2 and 3.4.1]. Thus route failure detection,
   same-packet salvage, and reactive path repair are established ideas.
   A new paper cannot claim those primitives as novel.
2. Relay-assisted ARQ for multihop ad-hoc networks was studied analytically
   and by simulation by Onat and Avidor [3]. An ICC 2010 mesh protocol
   used a primary path plus mini-path copies to compensate for failures
   while limiting redundant traffic [4]. A broad "diversity on failure"
   claim also lacks novelty.
3. LoRa-specific evidence complicates an assumed routing-versus-flooding
   cost hierarchy. Joy and Branch report that LoRa receiver behavior can
   limit duplicate forwarding and make flooding efficient in their mesh
   setting [5]. Rösler et al. show opportunistic candidate forwarding can
   exploit spatial diversity in 2.4-GHz LoRa [6]. Their radio setting is
   not identical to MeshEcho's model, so neither result can be imported as
   a numerical prediction, but both demand direct matched controls.
4. Solé et al. implemented a reliable large-message service in LoRaMesher
   and evaluated ten physical nodes in two topologies; the abstract reports
   improved reliability with more messages and longer delivery time [8].
   A simulation-only MeshEcho paper must explicitly limit its claim and
   account for the airtime/delay cost of reliability.

## Research implication

The next mechanism should operate on the **forward DATA failure** that
ACK-only CLAR cannot resolve. A one-shot source fallback is feasible to
implement, but by itself resembles established route maintenance and ARQ.
The defensible contribution would be a precise, device-observable decision
rule for *when and how* to spend a fixed LoRa rescue budget within the
remaining application deadline, plus evidence that it beats controls that
share the same trigger and packets. A branch that simply always floods on
timeout must be a comparator, not the alleged innovation.

Before writing code, fix the rule's inputs (source-local ACK history, route
state, actual source TX start and time left), permitted on-wire fields,
one-flow action cap, duplicate suppression, and route-commit semantics.
Compare it with: no same-flow recovery, same-time R repeat, and same-time
F fallback. Charge every DATA, FLOOD, ACK, control byte, queue delay and
collision. Separate destination delivery from source ACK and report both
whole-flow outcomes and recovery exposure. Use a fresh development split;
the inspected 8001--8020 CLAR set is algorithm-selection history only.

## Limitations

The search was targeted, not systematic. Crossref/OpenAlex metadata and
abstracts do not substitute for full-text comparison, and the exact
candidate policy has not yet been frozen. The local 15-s opportunity and
failure composition are workload-specific. No acceptance probability or
performance gain follows from this brief.

## References

1. Perkins, C., Belding-Royer, E., & Das, S. (2003). *Ad hoc On-Demand
   Distance Vector (AODV) Routing*. RFC 3561.
   https://doi.org/10.17487/RFC3561
2. Johnson, D., Hu, Y., & Maltz, D. (2007). *The Dynamic Source Routing
   Protocol (DSR) for Mobile Ad Hoc Networks for IPv4*. RFC 4728.
   https://doi.org/10.17487/RFC4728
3. Onat, F. A., & Avidor, D. (2008). Relay-assisted ARQ in wireless
   ad-hoc networks. *IEEE WCNC 2008*.
   https://doi.org/10.1109/WCNC.2008.93
4. Javadi, F., Munasinghe, K. S., & Jamalipour, A. (2010). Rapid and
   reliable routing mesh protocol (RRRMP). *IEEE ICC 2010*.
   https://doi.org/10.1109/ICC.2010.5502412
5. Joy, M. J. R., & Branch, P. (2024). Flooding in LoRa mesh networks.
   *ITNAC 2024*. https://doi.org/10.1109/ITNAC62915.2024.10815298
6. Rösler, S., Zubow, A., & Dressler, F. (2023). Opportunistic routing
   in LoRa-based wireless mesh networks. *WoWMoM 2023*.
   https://doi.org/10.1109/WoWMoM57956.2023.00065
7. MeshEcho-CLAR frozen development evidence (2026-10-04).
   `docs/research/meshecho_clar_dev_results.md`.
8. Solé, J. M., Centelles, R. P., Freitag, F., Meseguer, R., & Viñas,
   R. B. (2026). Large and reliable data transfer service for LoRa mesh
   network applications. *Computer Communications*.
   https://doi.org/10.1016/j.comcom.2025.108404
