# Feedback/ACK primitive prior-art fact check

Date: 2026-10-05. Scope: targeted fact check, not an exhaustive novelty
search or a positive MeshEcho algorithm claim. AI-assisted source discovery
and verification were used.

## Verified sources

| Source | Existence and content check | Relevance and boundary |
| --- | --- | --- |
| Johnson et al., DSR, RFC 4728 (2007), pp. 12-13; https://www.rfc-editor.org/rfc/rfc4728 | Official RFC text, directly checked on 2026-10-05. It explicitly permits a DSR software ACK request and a separate retransmission of that request; a software ACK may return over a different multihop path. | Authoritative protocol standard, not a LoRa experiment. A software ACK request, separate query packet, or alternate ACK path alone is not a new primitive. It describes primarily next-hop acknowledgement, not the exact proposed end-to-end status query. |
| Lee et al., *Avoiding Spurious Retransmission over Flooding-Based Routing Protocol for Underwater Sensor Networks*, *Wireless Communications and Mobile Computing* (2020), DOI 10.1155/2020/8839541 | Semantic Scholar DOI record `bb9f06f46b138a6b0df32b27e8749b28ffacf7c2` and Crossref title/year/venue agree. The indexed abstract explicitly describes multiple ACK paths and ACK-copy waiting time updated by path similarity. | Peer-reviewed primary simulation study in acoustic underwater networks, not LoRa. ACK duplication and adaptive waiting are known concepts; the abstract does not establish whether its exact state machine matches MeshEcho. Full text was not rechecked in this pass. |
| Sole et al., *Large and reliable data transfer service for LoRa mesh network applications*, *Computer Communications* (2026), DOI 10.1016/j.comcom.2025.108404 | Semantic Scholar DOI record `2beecbe31fe63af5717f51055d88e0dcb386bed5` and Crossref title/year/venue agree. A prior local full-text inspection is recorded in `meshecho_ack_timing_prior_art_quick_brief.md`; the protocol passage was not reopened in this check. | Peer-reviewed primary LoRa mesh paper. The prior inspection reports end-to-end ACK, source SYNC retries and receiver LOST_P/NAK, but this pass verifies bibliographic existence only. Do not infer a novel status-query distinction from metadata alone. |
| Escobar et al., *JMAC Protocol: A Cross-Layer Multi-Hop Protocol for LoRa*, *Sensors* (2020), DOI 10.3390/s20236893 | Semantic Scholar DOI record `df1778fe8cfa000fa62af9a24045e7dd6407aa0f` and Crossref title/year/venue agree. | Peer-reviewed LoRa multi-hop protocol context. Its indexed abstract does not describe the exact proposed status-query mechanism, so this source is not used to assert that mechanism already exists. |

## Verdict and limitations

The narrow claim that separate software ACK requests and adaptive/multiple
ACKs have precedents is **verified** by the official RFC and Lee abstract.
No checked source establishes that a future MeshEcho joint source/feedback/
recovery rule is identical to prior work, and none establishes that it is
novel. The Sole protocol detail remains a previously recorded inspection,
not freshly verified content. This is a targeted four-source screen rather
than a systematic review; exact comparative novelty requires full-method
inspection of close LoRa mesh work and measured, same-budget controls.

Source-quality note: the RFC is a standards authority, not an empirical
effect estimate. The three journal papers are primary technical reports;
publication metadata is verified, but this check does not audit their
sample sizes, conflicts of interest, implementation quality or retraction
status. Do not transfer an acoustic-network effect size to LoRa.
