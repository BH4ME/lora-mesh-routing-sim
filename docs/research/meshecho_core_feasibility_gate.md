# MeshEcho-SR core-rewrite feasibility gate

Date: 2026-10-04. Status: diagnostic questions, not a new algorithm or
positive paper claim. The active goal is a major ICC paper revision built
on a genuinely revised core mechanism and verified simulation evidence.

## Why the next mechanism cannot be another source timeout threshold

The current ICC manuscript already reports no demonstrated route-score
advantage over its matched PRR-product control. Frozen LPR, DPA, RAC,
CLAR, and DHR development cohorts each failed their own predeclared joint
gate. The latest DHR cohort has 803 scheduled unicasts per arm; its fixed-F
control delivered 799 to destinations but obtained only 570 source ACKs.
Of 229 delivered-unACKed fixed-F flows, 224 generated no source ACK receive
callback. Initial-R DATA loss and reverse-ACK loss therefore both matter.
At the source, a missing end-to-end ACK alone cannot distinguish them.

The next paper must not relabel ordinary retransmission, implicit ACK,
local bypass, or opportunistic forwarding as an invention. Relevant prior
work includes ExOR (DOI 10.1145/1080091.1080108), Bypass Routing/WAR
(DOI 10.1016/j.adhoc.2004.10.004), implicit-ACK candidate coordination
(DOI 10.1109/ISTT.2012.6481577), HOF (DOI 10.1109/ICC.2008.558),
LoRa opportunistic routing (DOI 10.1109/WoWMoM57956.2023.00065), and
network-impact-aware retransmission (DOI 10.1109/ICCW.2013.6649259).
These are a targeted screen, not an exhaustive novelty determination.

## Diagnostic questions before algorithm coding

1. For each first R DATA hop, did the intended next hop physically decode
   it? If it did and forwarded, did the predecessor physically hear that
   forwarding copy (or the destination's reverse ACK on the final hop)?
   Report missed progress evidence separately from actual forward loss;
   half-duplex and interference can make implicit ACK unreliable.
2. At each failed intended R hop, which off-path relays actually decoded
   the DATA? An offline radio-model test may count candidates that could
   reach the next or a later path node, but label this an *oracle upper
   bound*, not device-local knowledge or expected rescue success.
3. How much of the original 30-s application deadline remained at the
   missed hop, after charging candidate queue wait, all added DATA and
   reverse-ACK packet ToA, relay delays, and an explicit safety margin?
   Record insufficiency rather than assuming rescue is timely.
4. On F flows delivered without a source ACK, was the first reverse ACK
   actually emitted and at which intended hop did it stop? Destination
   duplicate receptions are not extra ACK attempts in the current code:
   flood deduplication returns before a second ACK.
5. Before any positive mechanism claim, establish enough target exposure
   and a feasible difference from fixed same-trigger DATA repeat, fixed
   ACK repeat, flood fallback, classic local bypass, and LoRa opportunistic
   forwarding. Cross-arm closed-loop outcomes are not per-flow causal
   counterfactuals.

## Decision rule

Run diagnostics on newly named exploratory seeds only; they are not a
holdout. If there is no substantial device-observable repair opportunity,
or the candidate cannot be distinguished from the cited predecessors
without an oracle, stop coding that candidate. If opportunity and a clear
specific contribution exist, freeze its packet/state/action contract and
fresh matched controls *before* a new development matrix. Reuse tested
simulator and full-network accounting, but not the failed DHR threshold or
its inspected seeds as confirmation. Keep the ICC manuscript/PDF unchanged
until a successor has passed its own frozen gate and an untouched holdout.
