# Research brief: ACK timing and local flood quiescence

Date: 2026-10-04. Mode: targeted quick research brief. AI-assisted source
discovery, verification, and synthesis were used; human full-text review has
not been claimed. This is a prior-art boundary for protocol design, not an
exhaustive novelty opinion.

## Executive summary

The fixed-2-s MeshEcho control improved source acknowledgment in one
exploratory recurring-fading simulation, motivating a device-local timing
controller. The literature already contains preset LoRa ACK delay [1],
dynamic waiting for ACK copies in a flooding network [2], synchronized
group ACK slots [3], and multihop LoRa hop ACKs [4]. Thus neither delayed
ACK, adaptive waiting, overhearing, nor reliable LoRa mesh is a defensible
broad novelty claim. In this bounded search, no checked source described
exactly one destination-originated reverse ACK triggered by a quiet period
in that destination's *successfully decoded same-flow FLOOD copies*. That
narrow gap is only a hypothesis: full text for [2] remains unavailable,
and a finite search cannot establish absence.
The next step is a falsifiable device-local contract and matched controls,
not immediate promotion to the ICC manuscript.

## Question and search

Question: does published LoRa or flooding work already specify a
destination-local duplicate-decode quiet window for scheduling a single
end-to-end reverse ACK, and what controls would a MeshEcho successor need?

On 2026-10-04, the targeted Crossref/OpenAlex search used the phrases
`LoRa multi-hop acknowledgement routing`, `LoRa mesh reliable delivery
acknowledgment`, `LoRa mesh ACK reverse path scheduling`, `LoRa
acknowledgment quiescence overhearing`, `flooding ACK wait quiet period
channel idle`, and `adaptive ACK LoRa`. Inclusion required direct ACK
timing, LoRa multihop/mesh reliability, or local overhearing relevant to
the proposed mechanism. Seven distinct DOI-bearing studies were retained;
DOI, title, authors, year, and venue were cross-checked against Crossref.
Five source texts were accessible in the initial screen; [7] was later
verified against an open CC BY full text, while [2] remains abstract-only.
This was targeted screening, not PRISMA or
a comprehensive search, and no claim of an exhaustive hit count is made.

## Findings and design implications

1. Sukeguchi et al. [1] implemented ACK delay for a Private-LoRa/QUIC
   handshake, setting 2.1--25.2-s waits by SF/bandwidth and combining an
   ACK after a third packet. Their original text describes real radio
   evaluation but only a small successful-communication sample. This
   directly defeats any claim that MeshEcho invented LoRa delayed ACK;
   their preset single-hop handshake differs from destination-local
   multihop FLOOD-copy observations.
2. Lee et al. [2] describe flooding of both DATA and ACK in an underwater
   sensor network and dynamically change an ACK-copies waiting time using
   path similarity to prevent spurious retransmission. The checked abstract
   points to source-side waiting for ACK copies, not a verified formula
   for destination ACK launch. The full PDF returned 403, so that narrower
   distinction must be rechecked before a novelty claim.
3. DG-LoRa [3] uses synchronized LoRaWAN frames, SF/time-slot assignment,
   and group ACKs at a server/gateway. JMAC [4] schedules multihop LoRa
   wakeups and hop-level DATA/ACK timing. These are important ACK timing
   and multihop controls, but their checked original methods are not the
   proposed unsynchronized destination-local end-to-end rule.
4. Berto et al. [5] show a peer-to-peer LoRa mesh prototype with optional
   reliable datagrams and ACK testing. Mugerwa et al. [6] use overhearing
   and relay backoff for LoRaWAN forwarding. Both restrict broad claims
   about mesh ACKs or overhearing; neither checked original text specifies
   the proposed destination quiet timer.
5. Solé et al. [7] report a reliable LoRaMesher large-data service with ten
   physical nodes and a message/latency trade-off. Their [open CC BY full
   text](https://upcommons.upc.edu/bitstreams/55c698b0-c18a-4d2a-b202-0a08bdfe2d27/download),
   Sections 2.1 and 2.5--2.6 and Figures 5--6, describes proactive NextHop
   routing, per-chunk end-to-end stop-and-wait ACK, source SYNC retry after
   missing ACK, and destination LOST_P/NAK (repeated when needed) for
   missing chunks. Its RTT-based timeout has a 20-s experimental minimum
   and default ten-timeout limit. The paper does not describe selecting a
   reverse ACK path from same-FLOOD decoded copies; it does not specify
   enough ACK-return and duplicate-DATA behavior to rule out every such
   implementation detail. Its real-node evidence raises the evaluation
   bar for a simulation-only MeshEcho claim.

The currently plausible *limited* research hypothesis is a bounded timer
driven only by successful same-flow destination FLOOD decodes, coupled to a
source recovery/deadline rule. It is not yet a novel or successful
algorithm. Compare at minimum immediate ACK, fixed-2-s single ACK,
parameter-only SF/ToA timing, same-path ACK repeat at equal packet/airtime
budget, and fixed F/R-F source recovery. Charge every packet and preserve
source ACK, destination delivery, delay, and whole-network airtime as
separate endpoints. An offline quiet gap in the current saved trace is
exposure, not a counterfactual effect.

## Limitations

The search was bounded, English-oriented, and not systematic. Lee et al.
[2] still lacked inspectable full text; absence of an identical phrase is
not evidence that an identical algorithm does not exist. The empirical
MeshEcho timing result is simulator- and workload-specific, with a 2-s
parameter chosen after earlier trace inspection. Hardware transfer and
ICC acceptance probability are not established by this brief.

## References

1. Sukeguchi, H., Nobayashi, D., Tsukamoto, K., Ikenaga, T., Sato, G., &
   Takizawa, K. (2025). An adaptive delayed ACK strategy over QUIC for
   efficient 920 MHz Private LoRa communication. *Lecture Notes on Data
   Engineering and Communications Technologies*.
   https://doi.org/10.1007/978-3-032-05781-5_23
2. Lee, S., Bae, Y., Khan, M. T. R., Seo, J., & Kim, D. (2020). Avoiding
   spurious retransmission over flooding-based routing protocol for
   underwater sensor networks. *Wireless Communications and Mobile
   Computing*. https://doi.org/10.1155/2020/8839541
3. Lee, J., Yoon, Y. S., Oh, H. W., & Park, K. R. (2021). DG-LoRa:
   Deterministic group acknowledgment transmissions in LoRa networks for
   industrial IoT applications. *Sensors, 21*(4), 1444.
   https://doi.org/10.3390/s21041444
4. López Escobar, J. J. L., Gil-Castiñeira, F., & Díaz Redondo, R. P. D.
   (2020). JMAC protocol: A cross-layer multi-hop protocol for LoRa.
   *Sensors, 20*(23), 6893. https://doi.org/10.3390/s20236893
5. Berto, R., Napoletano, P., & Savi, M. (2021). A LoRa-based mesh network
   for peer-to-peer long-range communication. *Sensors, 21*(13), 4314.
   https://doi.org/10.3390/s21134314
6. Mugerwa, D., Nam, Y., Choi, H., Shin, Y., & Lee, E. (2023). Implicit
   overhearing node-based multi-hop communication scheme in IoT LoRa
   networks. *Sensors, 23*(8), 3874.
   https://doi.org/10.3390/s23083874
7. Solé, J. M., Pueyo Centelles, R., Freitag, F., Meseguer, R., & Baig
   Viñas, R. (2026). Large and reliable data transfer service for LoRa
   mesh network applications. *Computer Communications*.
   https://doi.org/10.1016/j.comcom.2025.108404
