# Verified routing, suppression, and feedback literature for the ICC manuscript

Verification date: 2026-11-04. Read-only manuscript review; this task did not edit the main TeX/Bib or run simulations.

## Selection and evidence standard

Five closely relevant works are recommended: ETX, DSR, broadcast-storm analysis, Trickle, and ExOR. ETX is already present in `references.bib` and needs a more specific use in the mathematical discussion; the other four are new recommendations. These works support the mechanism background, not the numerical MeshEcho-CPR results or claims of superiority over official Meshtastic/MeshCore firmware. All have a positive citation count from a named index. Those counts are database snapshots, not exhaustive citation totals, and must not be summed across duplicated publication records.

The insertion sentences below are proposals, not claims that the main manuscript has already been changed. Each recommended reference should appear in a substantive `\\cite{...}` in the manuscript rather than being included with `\\nocite` solely to enlarge the bibliography.

| Work | Verified publication | DOI | Crossref referenced-by count | OpenAlex cited-by count |
|---|---|---|---:|---:|
| ETX | ACM MobiCom 2003, pp. 134–146 | 10.1145/938985.939000 | 1744 | Not queried |
| DSR | *Mobile Computing*, 1996, pp. 153–181 | 10.1007/978-0-585-29603-6_5 | 4552 | Not queried |
| Broadcast storm | ACM/IEEE MobiCom 1999, pp. 151–162 | 10.1145/313451.313525 | 1597 | 3162 |
| Trickle | USENIX NSDI 2004 | No DOI verified; leave DOI field absent | No exact work returned by title search | 1150, record W2058632086 |
| ExOR | ACM SIGCOMM 2005, pp. 133–144 | 10.1145/1080091.1080108 | 536 | 1356 |

Crossref counts for the first three are preserved in `routing_crossref_raw.json`. ExOR's conference record and the parallel CCR publication record are in `exor_crossref_search.json`; use the conference DOI above and do not add the CCR count (527). OpenAlex records are preserved in `broadcast_openalex.json`, `trickle_openalex.json`, and `exor2005_openalex.json`. Trickle also has a distinct duplicate-looking OpenAlex record W308222514 with 76 citations; it is not aggregated here.

## 1. ETX — existing citation, sharpen the formula connection

**Verified bibliographic identity:** Douglas S. J. De Couto, Daniel Aguayo, John Bicket, and Robert Morris, “A High-Throughput Path Metric for Multi-Hop Wireless Routing,” *Proceedings of the 9th Annual International Conference on Mobile Computing and Networking (MobiCom)*, 2003, pp. 134–146. DOI: [10.1145/938985.939000](https://doi.org/10.1145/938985.939000).

**Metadata/count source:** [Crossref exact work](https://api.crossref.org/works/10.1145/938985.939000); the live title-query response was retrieved and saved in `routing_crossref_raw.json`.

**Content actually inspected:** Author-hosted PDF was downloaded; abstract, introduction, and Section 3.1 were read from extracted text. This is more than an abstract check, but does not claim an exhaustive review of every experiment. [Full text](https://pdos.csail.mit.edu/papers/grid:mobicom03/paper.pdf). Local files: `etx_pdf.pdf`, `etx_pdf.txt`.

**Supported statement:** ETX measures expected packet transmissions including retransmissions. Section 3.1 defines forward DATA delivery probability `d_f`, reverse ACK delivery probability `d_r`, link cost `1/(d_f d_r)`, and route cost as a sum of link ETXs. This is an established metric; it does not validate our deadline-admission logic or prove independence between the recovery stages.

**Small evidence excerpt:** “including retransmissions” (abstract); “The ETX of a route is the sum” (Section 3.1; wording to be read with its sentence in the saved text).

**Proposed insertion — Introduction and/or `eq:path-reliability` / `eq:unified-cost`:**

```latex
ETX assigns a link the cost $1/(d_f d_r)$ from forward DATA and reverse
ACK delivery ratios and sums these costs along a route
\cite{decouto2003etx}. Our ledger in (\ref{eq:unified-cost}) instead records
the airtime of transmissions that actually start, including discovery,
recovery, and feedback.
```

Use the existing key `decouto2003etx`; no duplicate BibTeX entry is needed. If the inserted formula is retained, explicitly describe it as the prior ETX definition, not a new implemented CPR estimator. The manuscript's conditional path/recovery probability identities are its own analytical definitions and should not be falsely attributed to ETX.

## 2. DSR — source routing and topology-dependent overhead

**Verified identity:** David B. Johnson and David A. Maltz, “Dynamic Source Routing in Ad Hoc Wireless Networks,” in *Mobile Computing*, Tomasz Imielinski and Henry F. Korth, eds., The Kluwer International Series in Engineering and Computer Science, vol. 353, 1996, pp. 153–181. DOI: [10.1007/978-0-585-29603-6_5](https://doi.org/10.1007/978-0-585-29603-6_5).

**Metadata/count source:** Crossref title-query response in `routing_crossref_raw.json` supplies DOI/authors/pages/publisher and count 4552. Crossref's issued date is empty; the year 1996 was separately checked in the publisher's “Cite this chapter” block and copyright information.

**Content actually inspected:** [Springer chapter page and abstract](https://link.springer.com/chapter/10.1007/978-0-585-29603-6_5); saved `dsr_springer.html` and extracted `dsr_springer.txt`. The chapter full text was not available in this retrieval and was not claimed as read. As an additional protocol check, the RFC Editor's [RFC 4728 full text](https://www.rfc-editor.org/rfc/rfc4728.txt) was downloaded as `dsr_rfc.txt`; it is a later normative description and must not be mislabeled as the 1996 chapter.

**Supported statement:** The chapter describes dynamic source routing in infrastructure-free mobile networks, adapts to routing changes, and reports low overhead during periods of low movement. Its abstract does not by itself justify detailed claims about current MeshCore firmware or the exact cache-lifetime equation in this manuscript.

**Evidence excerpt:** “requires little or no overhead during periods in which hosts move less frequently.”

**Proposed insertion — Related Work, preceding the source-routing baseline discussion:**

```latex
Dynamic source routing adapts routes to topology changes while limiting
routing overhead during relatively stable periods \cite{johnson1996dsr}.
The cache-hit and cache-miss decomposition in (\ref{eq:meshcore-mixture})
makes this state-dependent overhead explicit for our MeshCore-like model.
```

This is conceptual antecedent plus our own model, not a claim that DSR and MeshCore share the same implementation.

**Proposed BibTeX:**

```bibtex
@incollection{johnson1996dsr,
  author = {Johnson, David B. and Maltz, David A.},
  title = {Dynamic Source Routing in Ad Hoc Wireless Networks},
  booktitle = {Mobile Computing},
  editor = {Imielinski, Tomasz and Korth, Henry F.},
  series = {The Kluwer International Series in Engineering and Computer Science},
  volume = {353},
  publisher = {Kluwer Academic Publishers},
  pages = {153--181},
  year = {1996},
  doi = {10.1007/978-0-585-29603-6_5}
}
```

## 3. Broadcast storm — why duplicate rebroadcasting and timing matter

**Verified identity:** Sze-Yao Ni, Yu-Chee Tseng, Yuh-Shyan Chen, and Jang-Ping Sheu, “The Broadcast Storm Problem in a Mobile Ad Hoc Network,” *Proceedings of the 5th Annual ACM/IEEE International Conference on Mobile Computing and Networking*, 1999, pp. 151–162. DOI: [10.1145/313451.313525](https://doi.org/10.1145/313451.313525).

**Metadata/count sources:** Crossref in `routing_crossref_raw.json`, count 1597; [OpenAlex exact DOI lookup](https://api.openalex.org/works/https://doi.org/10.1145/313451.313525), count 3162, saved `broadcast_openalex.json`.

**Content actually inspected:** The indexed abstract in the exact OpenAlex DOI record was reconstructed and read. The ACM page returned 403 and the historical author-site host failed DNS; no full-text reading is claimed.

**Supported statement:** Naive flooding can generate redundant rebroadcasts, contention, and collisions; the paper proposes reducing redundant rebroadcasts and differentiating rebroadcast timing. Its abstract supports this broad mechanism motivation, not a specific SNR-backoff formula or a guarantee that suppressing a local copy reduces network-wide cost.

**Evidence excerpt:** “serious redundancy, contention, and collision”.

**Proposed insertion — start of Meshtastic-like subsection, before `eq:meshtastic-delay`:**

```latex
Broadcast-storm analysis identifies redundancy, contention, and collisions
as costs of naive flooding, motivating selective rebroadcasting and
separated transmission times \cite{ni1999broadcaststorm}.
```

The following sentence can then introduce the implemented Meshtastic-like SNR-dependent delay. Do not attribute that specific delay function to Ni et al.

**Proposed BibTeX:**

```bibtex
@inproceedings{ni1999broadcaststorm,
  author = {Ni, Sze-Yao and Tseng, Yu-Chee and Chen, Yuh-Shyan and Sheu, Jang-Ping},
  title = {The Broadcast Storm Problem in a Mobile Ad Hoc Network},
  booktitle = {Proceedings of the 5th Annual ACM/IEEE International Conference on Mobile Computing and Networking},
  pages = {151--162},
  year = {1999},
  doi = {10.1145/313451.313525}
}
```

## 4. Trickle — overhearing-based suppression is established prior art

**Verified identity:** Philip Levis, Neil Patel, David Culler, and Scott Shenker, “Trickle: A Self-Regulating Algorithm for Code Propagation and Maintenance in Wireless Sensor Networks,” *USENIX Symposium on Networked Systems Design and Implementation (NSDI)*, 2004. No DOI is verified; omit the DOI field rather than inventing one.

**Metadata/count/content source:** [OpenAlex W2058632086](https://api.openalex.org/works/W2058632086). The live title-search response and its abstract are saved in `trickle_openalex.json`; the title, four authors, 2004 year, NSDI venue, and count 1150 were checked. OpenAlex also exposes a second record W308222514; no counts are combined. Publisher/author links attempted in the fetch logs returned 404/403 or DNS failure. The indexed abstract, not a retrieved full text, supports the proposed sentence.

**Supported statement:** Trickle disseminates and maintains code updates using a polite-gossip policy: a node stays quiet after recently hearing an identical summary and adjusts listening periods to control overhead. This is strong prior art against describing overhearing-based suppression in general as novel. It is not a destination-specific terminal-ACK mechanism and its dissemination objective differs from CPR's unicast delivery/confirmation objective.

**Evidence excerpt:** “stay quiet if they have recently heard a summary identical to theirs.”

**Proposed insertion — Related Work, then cross-reference from `eq:cancel` discussion:**

```latex
Trickle suppresses redundant code-summary broadcasts after a node overhears
consistent information \cite{levis2004trickle}. Our rule in
(\ref{eq:cancel}) specializes the suppression signal to a matching terminal
ACK that arrives before a pending relay commits.
```

Do not claim Trickle's full adaptive-interval algorithm is implemented in the Meshtastic-like model. Do not cite Trickle as evidence for the CPR numerical gains.

**Proposed BibTeX (minimal verified fields):**

```bibtex
@inproceedings{levis2004trickle,
  author = {Levis, Philip and Patel, Neil and Culler, David and Shenker, Scott},
  title = {Trickle: A Self-Regulating Algorithm for Code Propagation and Maintenance in Wireless Sensor Networks},
  booktitle = {Proceedings of the 1st Symposium on Networked Systems Design and Implementation (NSDI)},
  publisher = {USENIX Association},
  year = {2004}
}
```

## 5. ExOR — receiver coordination and ACK feedback predate CPR

**Verified identity:** Sanjit Biswas and Robert Morris, “ExOR: Opportunistic Multi-Hop Routing for Wireless Networks,” *Proceedings of the ACM SIGCOMM 2005 Conference*, 2005, pp. 133–144. DOI: [10.1145/1080091.1080108](https://doi.org/10.1145/1080091.1080108).

**Metadata/count sources:** `exor_crossref_search.json` has the conference title as `title=ExOR` plus `subtitle=opportunistic multi-hop routing for wireless networks`, the two authors, publication date, event SIGCOMM05, pages, and count 536. [OpenAlex conference DOI record](https://api.openalex.org/works/https://doi.org/10.1145/1080091.1080108) supplies count 1356. The parallel CCR DOI `10.1145/1090191.1080108` is the same conference-era work in a different bibliographic container, not a second independent prior method.

**Content actually inspected:** The Crossref abstract of the parallel CCR record was read. Subsequently the [author-hosted full text](https://pdos.csail.mit.edu/papers/roofnet:exor-sigcomm05/roofnet_exor-sigcomm05.pdf) was successfully downloaded, and its abstract, introduction, and batch-map forwarding passages were inspected (`exor_full.pdf`, `exor_full.txt`). The introduction explains that lower-priority forwarders send only packets not acknowledged in the batch maps of higher-priority nodes. These passages support the cautious insertion below. This is not a claim to have exhaustively re-audited all experiments or protocol details.

**Evidence excerpt:** “robust acknowledgments prevent unnecessary retransmissions”.

**Proposed insertion — Related Work and/or before `eq:cancel-signal-contrast`:**

```latex
ExOR selects forwarders after observing reception outcomes and coordinates
receivers to limit duplicate forwarding; its acknowledgment mechanism also
avoids unnecessary retransmissions \cite{biswas2005exor}.
CPR studies the narrower event in (\ref{eq:cancel-signal-contrast}): a
matching terminal ACK suppressing a relay copy that remains uncommitted.
```

This prevents an unjustified claim that ACK-assisted suppression itself is unprecedented. ExOR concerns opportunistic forwarding in an 802.11b testbed; it does not establish the behavior of our LoRa PHY or permit importing its reported throughput gains into this manuscript.

**Proposed BibTeX:**

```bibtex
@inproceedings{biswas2005exor,
  author = {Biswas, Sanjit and Morris, Robert},
  title = {{ExOR}: Opportunistic Multi-Hop Routing for Wireless Networks},
  booktitle = {Proceedings of the 2005 Conference on Applications, Technologies, Architectures, and Protocols for Computer Communications},
  pages = {133--144},
  year = {2005},
  doi = {10.1145/1080091.1080108}
}
```

## Rejections and limitations

- MORE was not selected: the manuscript does not implement network coding, and a bare citation would not support its current mathematical core.
- Gossip routing was considered but not selected: broadcast-storm analysis plus Trickle already directly cover the suppression motivation. Crossref attempts also encountered HTTP 429; no unchecked metadata is included.
- Two exploratory remembered DOI lookups were rejected after title verification: `10.1145/1080091.1080118` is **Mining anomalies using traffic feature distributions**, not ExOR; `10.1109/INFCOM.2002.1019368` is **Effective location-guided tree construction algorithms for small group multicast in MANET**, not Gossip routing. Neither belongs in the bibliography. The wrong-candidate raw files are retained only as rejected lookup evidence, not selected sources.
- For Trickle, the original DOI is unverified; missing DOI is preferable to a fabricated identifier. The indexed abstract is sufficient for the proposed narrow suppression sentence, but not for detailed claims about its timer mathematics.
- Broadcast storm and Trickle are supported by exact-record indexed abstracts. ETX and ExOR also have directly inspected author-hosted full-text passages. DSR is supported by the publisher abstract. Do not report that every selected paper was read end-to-end. The attempted Trickle DBLP BibTeX URL returned an anti-bot page, not a BibTeX record; it was not used as metadata evidence.
- These references establish context and novelty boundaries. They do not certify the current implementation defects, improve measured results, or establish a probability of ICC acceptance.
