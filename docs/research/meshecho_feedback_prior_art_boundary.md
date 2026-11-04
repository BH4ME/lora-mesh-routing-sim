# MeshEcho feedback-core prior-art and model boundary

Date: 2026-10-04. Status: targeted source check, not an exhaustive novelty
search, a new algorithm, or an ICC claim. Bibliographic identifiers below
were checked against DOI/publisher or RFC records; the Lee et al. full text
was not available in this pass.

| Candidate primitive | Closest verified precedent | Claim boundary |
| --- | --- | --- |
| LoRa hop DATA/ACK and reverse repair | JMAC, *Sensors* 2020, DOI `10.3390/s20236893`; DSR, RFC 4728, Section 3.2 | Neither hop ACK nor a retransmitted/software ACK request is independently new. DSR also permits a software ACK to take another multihop path. |
| ACK or physical signal as link-quality evidence | ETX, MobiCom 2003, DOI `10.1145/938985.939000`; Fonseca et al., *Four-Bit Wireless Link Estimation*, HotNets 2007, [official PDF](https://conferences.sigcomm.org/hotnets/2007/papers/hotnets6-final131.pdf); MRHOF, RFC 6719 | A source-local ACK SNR or copy index is a specific observation, not first use of ACK/signal measurements for routing. Missing end-to-end ACK conflates forward and reverse loss. |
| Delayed or multiple ACKs | Lee et al., 2020, DOI `10.1155/2020/8839541`; Sukeguchi et al., DOI `10.1007/978-3-032-05781-5_23` | Available Lee abstract describes multipath ACK copies and path-similarity-dependent waiting; its full mechanism was not verified here. Sukeguchi has online-first 2025 metadata and a 2026 book-chapter citation. Do not claim these ideas as firsts. |
| Route repair or useful-payload rescue | AODV, RFC 3561; DSR, RFC 4728 | R-to-F or local salvage alone is not new. An integrated rule must beat fixed R/F, same-trigger repeat/fallback, and other same-budget controls. |

The current simulator keys link shadowing and 60-s fading by an unordered
node pair and uses one transmit power and noise floor. Within one fading
block, reverse ACK last-hop clean SNR therefore closely mirrors forward
DATA first-hop clean SNR by construction. Its `RxInfo` exists only after
successful decode; interference, half-duplex and a new packet-reception
draw can still break prediction. This is a legitimate device-local
observation but may overstate real-world transfer. Sang, Arora and Zhang,
*On Link Asymmetry and One-way Estimation in Wireless Sensor Networks*,
ACM TOSN 2010, DOI `10.1145/1689239.1689242`, documents asymmetric and
unidirectional links in another WSN radio setting. It motivates an
asymmetric-link/power/noise sensitivity or physical trace check, not a
numerical LoRa claim.

A defensible MeshEcho contribution would have to be a specified joint
source/feedback/recovery rule, using only information available at each
device before its action, and demonstrate incremental benefit against the
simple controls with charged packet bytes and complete-network airtime.
The targeted check did not find an identical full rule, but absence from
this small source set does not establish novelty or submission readiness.
