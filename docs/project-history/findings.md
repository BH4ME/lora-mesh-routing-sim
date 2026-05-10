# Findings

## Existing Project Shape

The repository is a compact packet-level Python simulator for LoRa Mesh routing research. It compares two behavior-equivalent baselines:

- `meshtastic-like`: managed flooding with delayed rebroadcast and duplicate suppression.
- `meshcore-like`: RREQ/RREP route discovery with cached source routes.

The simulator includes a shared PHY/channel model:

- LoRa time-on-air.
- Log-distance path loss and log-normal shadowing.
- Half-duplex reception.
- Collision failure with capture effect.
- SNR-margin-based probabilistic reception.

## Current Baseline Results

Repeated unicast, 50 nodes:

- `meshtastic-like`: unicast PDR about `0.946`, airtime about `1129 s`, TX about `4575`.
- `meshcore-like`: unicast PDR about `0.833`, airtime about `335 s`, TX about `1356`.

Mixed traffic, 50 nodes:

- `meshtastic-like`: unicast PDR about `0.948`, broadcast coverage about `0.949`, airtime about `1170 s`.
- `meshcore-like`: unicast PDR about `0.642`, broadcast coverage about `0.967`, airtime about `962 s`.

Interpretation:

- Managed flooding is robust but expensive.
- Source-route caching is efficient but path-quality sensitive.
- Mixed traffic exposes the weakness of fixed forwarding behavior.

## Research Framing

The stronger conference framing is not "fusion of two protocols." It is:

> LoRa Mesh routing should be formulated as a reliability-airtime optimization problem under uncertain links and sparse feedback.

The proposed protocol should allocate redundancy based on route confidence.

Protocol lineage note:

- `calm-mesh` and `smart-calm` are self-defined routing/control layers in this repository.
- They are inspired by source-routing and managed-flooding ideas, but they are not a copy of Meshtastic or MeshCore internals.
- The ESP32 version should therefore be implemented as our own controller sitting above the radio driver, not as a fork of an existing mesh stack.

Working name:

**CALM: Confidence-Aware LoRa Mesh Routing**

Why this is better:

- Baselines become evidence, not ingredients.
- The contribution is a model and adaptive mechanism.
- The method can be evaluated with reproducible simulation.

## Useful Existing Design Notes

The archived draft `archive/research-drafts/ei-mesh-research-plan.md` already proposes:

- Link cost using ToA, PER estimate, congestion, energy risk, route age, and SNR margin.
- Candidate path collection instead of accepting the first RREQ.
- Adaptive forwarding based on route confidence.
- Controlled opportunistic redundancy for weak links.

This should be reframed for conference presentation as confidence-aware redundancy allocation.

## Tuned CALM Results

After parameter tuning, CALM uses a longer RREQ candidate collection window and longer route TTL. The key change is quality-aware route admission, not constant fallback flooding.

The tuned defaults are:

- `calm_route_ttl_s = 600`
- `calm_discovery_window_s = 2.0`
- `calm_fallback_confidence_threshold = 0.0`
- `calm_fallback_ttl = 2`
- `calm_fallback_delay_margin_s = 0.6`
- `calm_hop_penalty_per_hop = 0.025`
- `calm_route_age_penalty = 0.1`

Repeated unicast, 50 nodes, 20 seeds:

- `meshcore-like`: unicast PDR about `0.833`, airtime about `335 s`, collision failures about `26643`.
- `calm-mesh`: unicast PDR about `0.847`, airtime about `224 s`, collision failures about `16619`.
- Interpretation: CALM keeps airtime and collision pressure below MeshCore-like while staying slightly better on unicast PDR.

Mixed traffic, 50 nodes, 20 seeds:

- `meshcore-like`: unicast PDR about `0.642`, broadcast coverage about `0.967`, airtime about `962 s`.
- `calm-mesh`: unicast PDR about `0.755`, broadcast coverage about `0.967`, airtime about `830 s`.
- Interpretation: CALM recovers a meaningful part of the mixed-traffic unicast reliability gap while keeping broadcast coverage high and reducing airtime.

Higher shadowing check, 50 nodes, mixed traffic, `shadow-sigma-db = 6`:

- `meshcore-like`: unicast PDR about `0.633`, broadcast coverage about `0.971`, airtime about `970 s`.
- `calm-mesh`: unicast PDR about `0.736`, broadcast coverage about `0.970`, airtime about `830 s`.
- Interpretation: the tuned defaults remain on the same tradeoff curve under harsher shadowing.

## Smart-CALM High-Reliability Training Results

After training experiments, directly transferring an unconstrained Q-table prior proved too rescue-biased. The stronger training outcome is a bounded timeout-retry action: when a unicast flow is still undelivered after the learned timeout, Smart-CALM triggers at most one limited fallback retry. This is a high-reliability mode, not the lowest-airtime mode.

Mixed traffic, 50 nodes, 20 seeds:

- `meshtastic-like`: unicast PDR about `0.948`, broadcast coverage about `0.949`, airtime about `1170 s`, collision failures about `122048`.
- `meshcore-like`: unicast PDR about `0.642`, broadcast coverage about `0.967`, airtime about `962 s`, collision failures about `82047`.
- `calm-mesh`: unicast PDR about `0.768`, broadcast coverage about `0.970`, airtime about `835 s`, collision failures about `73923`.
- `smart-calm`: unicast PDR about `0.962`, broadcast coverage about `0.968`, airtime about `935 s`, collision failures about `83492`.

High shadowing, 50 nodes, mixed traffic, `shadow-sigma-db = 6`, 20 seeds:

- `meshtastic-like`: unicast PDR about `0.950`, broadcast coverage about `0.954`, airtime about `1178 s`, collision failures about `121836`.
- `meshcore-like`: unicast PDR about `0.633`, broadcast coverage about `0.971`, airtime about `970 s`, collision failures about `83424`.
- `calm-mesh`: unicast PDR about `0.733`, broadcast coverage about `0.975`, airtime about `830 s`, collision failures about `74048`.
- `smart-calm`: unicast PDR about `0.963`, broadcast coverage about `0.969`, airtime about `914 s`, collision failures about `82047`.

Interpretation:

- Smart-CALM high-reliability mode now exceeds the managed-flooding baseline's unicast PDR in mixed and high-shadowing scenarios while still using less airtime than flooding.
- Compared with MeshCore-like, it trades modest extra redundancy for a large reliability gain.

High offered load, 50 nodes, mixed traffic, `rate-per-min = 10`, 20 seeds:

- `meshtastic-like`: unicast PDR about `0.917`, broadcast coverage about `0.915`, airtime about `1875 s`, collision failures about `198166`.
- `meshcore-like`: unicast PDR about `0.488`, broadcast coverage about `0.936`, airtime about `1415 s`, collision failures about `125205`.
- `calm-mesh`: unicast PDR about `0.596`, broadcast coverage about `0.939`, airtime about `1233 s`, collision failures about `113447`.
- `smart-calm`: unicast PDR about `0.923`, broadcast coverage about `0.923`, airtime about `1506 s`, collision failures about `140102`.

Interpretation:

- Under heavier traffic, Smart-CALM high-reliability mode nearly matches flooding reliability while still saving substantial airtime compared with flooding.
- It no longer has the lowest airtime; the honest claim is a selectable high-reliability mode learned from timeout feedback.

## ESP32 Direct-LoRa Firmware Packet Layer

The first firmware milestone targets ESP32 directly controlling an SX1262 or
SX127x/RFM9x LoRa radio through RadioLib. This is not a UART transparent-modem
port and not a MeshCore/Meshtastic fork.

The over-the-air Smart-CALM packet is now explicit rather than a raw C++ struct
copy. It includes:

- magic/version/type
- source, destination, and sequence number
- flow ID, creation timestamp, and TTL
- state/action indexes and flags
- confidence in milli-units
- payload length and payload
- CRC-16

Both PlatformIO build targets compile:

- `esp32dev_sx1262`
- `esp32dev_sx127x`

The current firmware can initialize the radio, transmit status/hello frames,
receive and validate Smart-CALM frames, reject malformed/CRC-failed packets, and
run a custom mesh data plane with `RREQ`, `RREP`, `DATA`, and `ACK` frames.

Design boundary for the conference narrative:

- It may be described as borrowing the general source-route discovery idea that
  MeshCore-like systems make useful.
- It may be described as borrowing the controlled fallback/limited broadcast
  idea that managed-flooding systems make useful.
- It should not be described as a MeshCore or Meshtastic protocol fork. The
  frame format, route payload, confidence fields, controller hooks, and learning
  behavior are Smart-CALM-specific.

Remaining firmware work:

- timeout retry on missing ACK
- persistent route aging and eviction policy
- neighbor/link-quality table using RSSI/SNR
- richer delivery telemetry back into the online controller
