# MeshEcho-SR: demand-gated shadow route refresh (research proposal)

Date: 2026-10-03. Status: unimplemented hypothesis, not a measured result or
part of the current ICC 2027 manuscript. This brief was prepared with
AI-assisted research and checked against the sources below.

## Research question and evidence boundary

Can a sender-only LoRa controller improve source-confirmed delivery under
repeated, changing links by refreshing an aging route *before* its first
observed failure, without paying more whole-network airtime than a faithful
flood-first/route-cache hybrid? The claim is deliberately narrower than
"first flood-then-route protocol" or "globally optimal routing."

The current 2.1.26 experiment motivates the question but cannot answer it.
In the random-pair stress case, calibrated MeshEcho spends 152.8 aggregate
TX seconds for 0.486 source-ACK PDR, versus 38.9 seconds and 0.708 for its
stylized Meshtastic-like flood model. It starts 807 discoveries for 813 flows
and obtains only five cache hits. In recurring-pair traffic it obtains 525
cache hits and 0.624 ACK PDR, but the matched-recovery PRR-product scorer is
essentially tied (0.621). These are simulator-model contrasts, not measured
Meshtastic or MeshCore device performance. See the frozen experiment report
and the manuscript [1].

Meshtastic 2.6+ already learns a next-hop after an initially managed-flooded
direct message and can fall back to a flood [2]. MeshCore already floods the
first message, learns a source route from the delivery report, and falls back
after failed attempts [3]. Thus the F and R primitives below are not new.
The research candidate is the *joint decision rule and ACK-gated shadow
commit*: selectively probe a fresh route while retaining a working old one,
based on past demand and route age, before an ACK failure. Prior proactive
maintenance, LoRa airtime metrics, conservative link estimation, and online
routing are documented [4-7]; distinctness from two products is not proof of
global research novelty.

## Protocol contract

Each source keeps a fixed-size entry per recently used destination:
confirmed path (up to six hops), ACK-confirmed commit time, its last two application-send
times, last shadow-discovery time, consecutive source-ACK misses on that
path, consecutive F ACK misses while no path is confirmed, and one tentative
path for the current flow. A separate `had_R_miss_since_commit` bit remains
set after any R ACK miss, even if a later R succeeds; only committing a
fresh path clears it. A source-wide token
bucket caps extra discoveries. State lives in RAM; no per-packet flash writes
or clock synchronization between nodes is required. Only a route whose DATA
has been acknowledged at the source is **confirmed**. RREP alone never
confirms a path, and destination delivery hidden inside the simulator is
never an online input.

The three mutually exclusive actions for one application flow are:

- **F (flood/learn):** Send one managed-flood DATA. If its ACK returns with a
  realized path, install that path. Otherwise retain any old confirmed path.
- **R (reuse):** Send one DATA on the confirmed path. A missing ACK updates
  the source's failure count but does not erase the path immediately.
- **D (budgeted discovery):** For repeated cold conversations after two F
  attempts without source ACK, or for an aging ACK-confirmed path that has
  **not** failed, send one bounded RREQ. The destination collects the RREQ
  paths during its discovery window, selects one with the matched route
  scorer, and returns at most one RREP; the source does **not** see all
  candidate paths. Send this flow's DATA exactly once on the returned path.
  If no RREP arrives by the source's PHY-aware deadline, send that one DATA
  by F when there is no old path, or by R on the retained old path. In the
  shadow-refresh case, keep the old path until an ACK for candidate DATA
  reaches the source. If that ACK never arrives, retain the old path for
  later flows. A fallback F ACK may itself confirm its realized path; a
  fallback R ACK confirms delivery on the old path, not the tentative new
  one. The RREQ,
  RREP, DATA, ACK, retries (if enabled), and route header bytes all count
  toward cost. Destination-side candidate selection uses the *same*
  RREQ-reception-observable route scorer as the matched baseline, so an
  apparent gain is not silently caused by changing the path metric. The
  selected path and score must be encoded in the RREP; the source cannot
  inspect candidate sets held only at the destination.

"Shadow" here protects the **cached route for later flows**, not this
flow's payload: candidate DATA can fail even when the old route would have
worked. The mechanism experiment must count that harm. A stricter
make-before-break variant would send this DATA on the old route and validate
the candidate using a separate PROBE/PROBE-ACK transaction. That is a
different, higher-airtime protocol requiring a new wire frame and is not the
primary SR candidate until measured packet costs and hardware tests exist.

One transparent, frozen **starting policy** is below. Its constants are
design hypotheses, not fitted optima. Any tuning uses development seeds
only; the final values and evaluation seeds must be frozen before the
independent holdout. `age` is since the *old path's ACK-confirmed commit*,
not since the last discovery or application send. A failed D never resets
this age. `recent_sends` counts only the source's own earlier
sends to this destination in the preceding 300 seconds.

```text
on_app_send(dst, now):
    if no unexpired ACK-confirmed route:
        if last two F attempts to dst lacked source ACK
           and recent_sends >= 2
           and now - last_D >= 300 s
           and source has one discovery token: choose D; consume one token
        else: choose F
    else if two consecutive R DATA transmissions lack source ACK: choose F
    else if route_age >= 180 s
         and recent_sends >= 2
         and now - last_D >= 300 s
         and source has one discovery token
         and not had_R_miss_since_commit:
         choose D; consume one token
    else: choose R

after F ACK: confirm the realized path; clear route miss count
after R ACK: clear route miss count
after D candidate ACK: confirm candidate (replace old path if present)
after D with no RREP: process ACK by its actual F/R DATA action
after D candidate timeout: keep old path if any; apply 300-s D cooldown
```

Initially the source has one D token; a token is replenished after every
ten of its application unicasts, with capacity one. At most one D attempt
per destination may occur in 300 seconds. An unused `last_D` starts in a
sentinel state that permits the first eligible D; it is not initialized to
time zero. The starting policy fixes a 600-s confirmed-route TTL, six-hop
maximum, eight destination slots, and least-recently-used eviction; eviction
discards the route and history together. The persistent miss bit deliberately
disables pre-failure shadow D after any R miss until a fresh path is
ACK-committed. If this makes D too rare, it fails the exposure gate rather
than being silently relaxed on test seeds. These rules cap exploration and
allow a deterministic replay. The first no-route attempt intentionally uses
F: "first flood then cache" is a strong product behavior, not a new feature.
Cold D can occur only on the third or later repeated attempt and must be
evaluated separately from pre-failure shadow D. The **F/R-only ablation** is
identical except cold D becomes F and shadow D becomes R.
A periodic-refresh control receives the *same* RREQ token budget. If D does
not beat these controls, the simplest F/R policy wins and SR should not be
claimed as an improvement.

ACK timeout begins at actual source DATA transmission, not application
enqueue time. Its value must cover worst-case path airtime and bounded relay
queuing; a late ACK corrects a prior timeout instead of counting both
success and failure. A source flow id and candidate-path id bind the ACK to
the action that actually sent DATA. No same-flow rescue transmission is
hidden inside F, R, or D during the mechanism-isolation experiment. A
separate deployment-style comparison can enable matched retry budgets for
all policies. The destination's RREQ collection window and the source's
RREP deadline must be fixed for each PHY/hop configuration, include actual
TX/relay timing, and be identical for matched discovery controls. At most
one D may be pending for a destination. A late ACK can correct that flow's
outcome, but cannot overwrite a newer committed path.

For the on-wire scorer, each RREQ relay appends its node id and updates a
quantized minimum of *measured reception SNR margin*; the destination
compares only paths it actually receives and returns one selected path and
score. The simulator's current logistic SINR-to-PRR curve is a model, not a
device measurement. The same measured-input score and frame-length rules
must be used for SR and its matched discovery controls. Before a hardware
claim, calibrate the SNR mapping on the actual radios or use the monotone
minimum-margin ranking on both simulator and device, then rerun comparisons.

F must carry a bounded realized-hop trace and return an explicit
application-level confirmation with that trace; duplicate suppression and
ACK routing are specified identically for every policy in the
mechanism-isolation comparison. This is not claimed to reproduce either
product's native acknowledgement semantics. A separate product-behavior
comparison reports each native ACK/delivery-report outcome and destination
delivery without treating those different feedback definitions as
interchangeable.

## Why this may fail

An initial DATA flood can both deliver the packet and learn a route. D pays
for discovery before sending DATA, so its control overhead may never
amortize; a shorter route TTL or periodic refresh may work just as well.
Past send frequency may not predict future demand, and route age may be a
poor predictor of link change. An ACK miss may be a reverse-path problem,
not evidence that the forward route is stale. The present random-pair
workload provides almost no reusable per-destination data, so a per-dest
three-arm bandit or TinyML model is unjustified. The existing ESP32
Smart-CALM firmware already uses tabular Q-learning to select three global
redundancy profiles; renaming that mechanism would not create a new
contribution [8]. If learning later proves useful, first test a tiny pooled
age/demand hazard table against this frozen deterministic controller on new
traces; keep any model within fixed RAM and measure its exploration cost.

## Evaluation gates before a paper claim

1. **Simulator validity:** Packet types and path lengths determine actual
   serialized bytes, LoRa time-on-air, collision interval, and modeled
   energy. The current simulator charges every packet as 32 bytes, so no
   current airtime result validates SR [1]. Record every action, candidate,
   ACK/timeout, control packet, route switch, and total TX airtime.
2. **No oracle:** A paired-history test must produce identical decisions
   before two schedules diverge, regardless of different future traffic.
   The policy may not read true link PRR, coordinates, future flows,
   destination-delivered flags, or global TX airtime.
3. **Fair controls:** Reproduce documented Meshtastic 2.6+ direct-message
   route learning and MeshCore DATA-flood/delivery-report/source-route
   behavior, not the current flood-only and RREQ-first `-like` shortcuts.
   Include current calibrated MeshEcho, matched-recovery PRR-product,
   F/R-only, an **age-triggered F** that uses the exact shadow-D trigger but
   sends DATA by flood instead of RREQ+RREP+DATA, equal-budget periodic
   refresh, and no-demand-gate/no-shadow-commit ablations. The age-triggered
   F control tests whether useful DATA flooding dominates D. Product-native
   retries and matched-budget, common-confirmation isolation are separate
   experiments.
4. **Independent tests:** Freeze development and test seeds and packet
   accounting in advance. Include random pairs, recurring pairs, a mixture
   whose composition changes mid-run, link drift/mobility, topology density,
   and offered load. The mechanism-isolation denominator is every scheduled
   unicast up to a fixed generation horizon. Success is source confirmation
   by the same application deadline, measured from application enqueue for
   F/R/D alike; the simulator then drains pending events to a fixed bound.
   Before looking at independent seeds, fix this deadline, the
   fading/traffic strata, the primary comparator, and a paired result gate.
   A candidate reliability-first intersection-union gate requires, against
   **each** of F/R-only and age-triggered F in the changing recurring
   stratum, a positive 95% paired lower bound on confirmation-PDR gain and
   a paired 95% upper bound below +10% on relative whole-network TX-airtime
   cost. All four inequalities must pass; the 10% is an author design
   budget, not an ICC rule or acceptance probability. Airtime includes
   all control, ACK and retry transmissions. Report destination PDR, delay
   tail, device energy, duty-cycle violations, and confidence intervals
   separately. Product-native comparisons are descriptive unless their
   end-to-end confirmation contracts are made equivalent. Report D-exposed
   flow ACK PDR and deadline misses descriptively; for an action-level
   counterfactual, replay R and F from a matched pre-decision state with
   fixed exogenous channel draws. This keeps current-packet exploration harm
   visible without pretending that different policy histories select the
   same flows. Also report pre-failure D count,
   fraction finding a different route, ACK-confirmed switches, and net
   airtime after the expected number of subsequent sends. Report cold D and
   pre-failure shadow D as separate exposure and outcome groups.
5. **Falsification:** If D barely fires, usually returns the same path, has
   no paired delivery or cost gain over F/R-only and equal-budget periodic
   refresh, or helps only the scenario used to tune thresholds, drop the
   novel-algorithm claim. A positive result under only stylized product
   models does not support superiority to real firmware.

## Device implementation boundary

Use fixed route slots (start with the firmware's eight-route capacity), a
six-hop `uint16_t` path, two past-send timestamps, small counters and one
tentative path per active D. Decision work is O(route slots + hop count) and
can use integer milliseconds/counters; no neural network or floating-point
inference is required. Exact `sizeof`, static RAM, flash, worst-case timing,
and power must be measured on both requested targets. The repository's
available C++ source builds for `esp32dev` with Arduino/RadioLib, **not**
ESP32-S3; the nRF52840 web manifest is marked planned, without a flashable
image. Neither target-specific SR implementation nor radio test is present
[8]. Port and test the *same wire format and decision trace* on nRF52 and
ESP32-S3 after the simulator contract passes. `nRF52` names a family: choose
the exact board/SKU and measure RAM/stack headroom. Use monotonic source
elapsed time; 32-bit deadline comparisons need rollover-safe arithmetic,
and sleep/reboot must invalidate or rebase route age. Minimum radio tests
are a three-node blocked-direct path and a four-node two-relay route-change
case, with controlled ACK loss, late ACK, and route break. In Shenzhen, set
a locally permitted LoRa band and power rather than copying the
prototype's 915-MHz default.

## Sources and reproducibility

This is a targeted mechanism/prior-art brief, not an exhaustive systematic
review. Official product documentation states product behavior; it is not a
firmware-code audit. Peer-reviewed papers establish nearby components, not
an exact SR precedent. A targeted DOI/title/abstract search found no exact
LoRa F/R/D match but cannot prove firstness.

1. Local `paper/icc2027/icc2027_lora_mesh.tex`,
   `docs/results/meshecho_v2_1_25_icc2027_baseline_feedback_fading.md`,
   and `docs/results/meshecho_v2_1_25_icc2027_random_sparse_fading_2001_2020.md`,
   repository `version/v2`
   commit `78ffb6e` (2026-10-03).
2. Meshtastic, [Mesh Algorithm: direct messages using next-hop routing](https://meshtastic.org/docs/overview/mesh-algo/#direct-messages-using-next-hop-routing).
3. MeshCore, [FAQ sections 5.3-5.4](https://github.com/meshcore-dev/MeshCore/blob/main/docs/faq.md).
4. Pueyo Centelles et al., "A Minimalistic Distance-Vector Routing Protocol
   for LoRa Mesh Networks," *IEEE Access* 12 (2024), 128941-128962,
   [doi:10.1109/ACCESS.2024.3443605](https://doi.org/10.1109/ACCESS.2024.3443605).
5. Mathews and Gotzhein, "OB-EWMA: A Link Metric for Reliability-constrained
   Routing in Wireless Networks," *IEEE WCNC* (2021), 1-7,
   [doi:10.1109/WCNC49053.2021.9417117](https://doi.org/10.1109/WCNC49053.2021.9417117).
6. Dai and Wu, "Proactive route maintenance in wireless ad hoc networks,"
   *IEEE ICC* 2 (2005), 1236-1240,
   [doi:10.1109/ICC.2005.1494544](https://doi.org/10.1109/ICC.2005.1494544).
7. Amar, Sarfati, and Cohen, "An Online Learning Approach to Shortest Path
   and Backpressure Routing in Wireless Networks," *IEEE Access* 11
   (2023), 57253-57267,
   [doi:10.1109/ACCESS.2023.3282365](https://doi.org/10.1109/ACCESS.2023.3282365).
8. Local `firmware/esp32_smart_calm/include/smart_calm_controller.hpp`,
   `firmware/esp32_smart_calm/platformio.ini`, and
   `web/meshecho/public/firmware/nrf52840_sx1262/firmware-nrf52840_sx1262-v2.me.json`.
