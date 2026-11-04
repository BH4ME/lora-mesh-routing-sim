# CCF-A venue deadline check for the current MeshEcho-CPR manuscript

Checked: 2026-11-04, Asia/Shanghai.
Method: AI-assisted quick research; primary CCF and conference sources,
independently checked in parallel. No submission or manuscript mutation.

## Scope

The current paper studies LoRa mesh recovery, one same-path repeat,
deadline-gated recovery flooding and ACK-terminated relay cancellation.
Evidence is a 20-node, 20-seed paired simulation with behavior-level
Meshtastic-like, MeshCore-like and legacy MeshEcho baselines. This is not
an official firmware benchmark or an over-the-air evaluation.

The CCF computer-networking A list contains SIGCOMM, MobiCom, INFOCOM and
NSDI. The same official page lists SenSys, SECON and MobiSys as B, ICC as C.
Source: https://www.ccf.org.cn/Academic_Evaluation/CN/

## Verified deadlines and status

| Main conference | Official deadline | Status on check date |
| --- | --- | --- |
| SIGCOMM 2027 | Full paper: 2027-02-02 | Future deadline published. Linked HotCRP site returns “No such conference”; immediate upload availability is not confirmed. |
| MobiCom 2027 | Summer abstract 2026-08-26, full paper 2026-09-02, 23:59 AoE. Winter abstract/full paper: TBD. | Summer closed. A second cycle is announced, but its dates are not published. |
| INFOCOM 2027 | Abstract 2026-07-24; full paper 2026-07-31, 23:59 AoE. | Main-conference deadline passed. |
| NSDI 2027 | Spring full paper 2026-04-23; fall full paper 2026-09-17, 23:59 US EDT. | Both cycles passed. |

SIGCOMM's retrieved submission instructions do not state a cutoff time zone
or separate abstract deadline. Do not invent either or convert to Beijing time.
NSDI 2028 is listed for 2028-05-09 to 11 in Santa Clara, but its expected
CFP URL returned Page not found. It cannot be treated as confirmed open.

## Fit and recommendation

- SIGCOMM 2027: a verified future-deadline CCF-A candidate. Its research
  scope explicitly includes wireless networks, reliability, performance,
  energy, theory, analysis and experimentation. Conference dates are
  2027-08-08 to 12, Bangkok. Body limit: 12 pages, double-blind ACM format.
  A distinct 2027 decision can accept a paper into CCR while rejecting it
  from the SIGCOMM conference; a CCR acceptance is not a SIGCOMM main-paper
  acceptance. The current ICC-format manuscript is not submission-ready.
- MobiCom 2027: strong topic alignment; the CFP explicitly includes LPWAN,
  energy-efficient networks and resource-constrained systems. Prepare for
  the announced winter round, whose dates remain TBD. Conference dates:
  2027-10-18 to 22; location was not stated on the retrieved pages. Body
  limit: 12 pages plus references, double-blind ACM format.
- INFOCOM: a natural methodological/topic fit, but the 2027 window is shut.
- None of these CFPs supports a blanket claim that physical hardware is a
  mandatory prerequisite for every paper. For this manuscript, however,
  stronger baselines, multi-scenario sensitivity, causal component ablations
  and measured-channel or hardware evidence are substantive weaknesses to
  address. Additional equation count alone does not establish novelty.

## Primary sources

1. CCF networking ranking: https://www.ccf.org.cn/Academic_Evaluation/CN/
2. SIGCOMM 2027 CFP: https://conferences.sigcomm.org/sigcomm/2027/cfp/
3. SIGCOMM 2027 submission instructions: https://conferences.sigcomm.org/sigcomm/2027/submission/
4. SIGCOMM 2027 dates/location: https://conferences.sigcomm.org/sigcomm/2027/
5. Linked SIGCOMM submission site: https://sigcomm27.hotcrp.com/
6. MobiCom 2027 CFP: https://www.sigmobile.org/mobicom/2027/cfp.html
7. INFOCOM 2027 CFP: https://infocom2027.ieee-infocom.org/call-papers
8. NSDI 2027 CFP: https://www.usenix.org/conference/nsdi27/call-for-papers
9. NSDI future meetings: https://www.usenix.org/conferences/byname/178

## Retrieval limitations

The initial HTML-extraction attempt lacked BeautifulSoup; standard-library
HTMLParser sufficed. Bare sigmobile.org DNS failed for a worker, which then
verified the official pages in Safari; www.sigmobile.org subsequently worked
via curl. Future dates remain subject to official updates. Workshops,
posters and demos were excluded from main-conference deadline claims.
