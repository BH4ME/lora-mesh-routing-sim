# SECON 2027 baseline fidelity and parameter contract

Audited 2026-11-04 from the imported 2.1.27 simulator and the SECON runner interface under implementation. Historical import is pinned by `secon2027_provenance/source_import.json`; final experiments must record their own full source/config hashes and resolved parameters. Function/class names below are stable references; line numbers can change during P0 repairs.

The four primary arms compare **implemented behavioral models**. `meshtastic` means Meshtastic-like and `meshcore` means MeshCore-like in every table, figure and claim. Neither implements a pinned official firmware release, and parameter matching does not establish firmware equivalence. New results must not be labeled product performance measurements.

## Official references and fidelity limits

| Project | Read-only upstream snapshot checked on 2026-11-04 | Relationship to this model |
| --- | --- | --- |
| Meshtastic | GitHub latest-release API returned [v2.7.26.54e0d8d](https://github.com/meshtastic/firmware/releases/tag/v2.7.26.54e0d8d), target `54e0d8d0ab2ff56b3a9ce967e53f79e49af560fb`; published 2026-06-24. Current default-branch head was `51ac6ea7b7d7cb430acee10fcff41fbca94a20ba`. Reviewed FloodingRouter, NextHopRouter and ReliableRouter at the **release commit**, not the moving head. | The model captures delayed managed flooding and duplicate suppression. It omits the official next-hop learning, reliable retransmission/implicit ACK system and last-retry return to flooding. It is not a complete or necessarily strong representation of current Meshtastic. |
| MeshCore | GitHub latest-release API returned [companion-v1.18.0](https://github.com/meshcore-dev/MeshCore/releases/tag/companion-v1.18.0), published 2026-10-15. Annotated tag object `7d6d255104eadbfccd85ceae4ccbc14133946f7e` resolves to commit `81dbae592ffad40b4212bc0b37e82b38da08f4bc`. Reviewed pinned [FAQ](https://github.com/meshcore-dev/MeshCore/blob/81dbae592ffad40b4212bc0b37e82b38da08f4bc/docs/faq.md). | The model captures cached source routes after an initial discovery exchange. It uses RREQ/RREP, whereas FAQ §5.4 describes first-message DATA flooding and a flooded delivery report carrying the route. FAQ §5.3 describes broken-route retries followed by flood; the model omits this retry behavior. FAQ §5.2 says companion clients do not relay; simulated relay eligibility is a common environment assumption. |
| Legacy MeshEcho | Imported project source, `MeshEcho(CalmMesh)`; no external official product counterpart | Research reference policy with confidence-ranked discovery, source-route cache and limited fallback. |
| MeshEcho-CPR | `MeshEchoCPR` and `meshecho_cpr.py`; repaired source pinned separately before running | Research method, evaluated only within the declared model and common environment. |

Pinned Meshtastic source explicitly implements ACK/reply-based next-hop updates, retransmission state and clearing next-hop preference for final-retry flooding in [NextHopRouter.cpp](https://github.com/meshtastic/firmware/blob/54e0d8d0ab2ff56b3a9ce967e53f79e49af560fb/src/mesh/NextHopRouter.cpp) (reviewed lines 93–116, 265–314). [ReliableRouter.cpp](https://github.com/meshtastic/firmware/blob/54e0d8d0ab2ff56b3a9ce967e53f79e49af560fb/src/mesh/ReliableRouter.cpp) handles `want_ack`, implicit ACK and retransmission cancellation. Therefore bounded retransmission followed by flooding is **not by itself a new CPR contribution**. Claims must identify the actual deadline/pre-commit rules and their measured effects, while acknowledging these antecedents.

The official [Meshtastic mesh-algorithm webpage](https://meshtastic.org/docs/overview/mesh-algo/) timed out during this recheck; the prior verified bibliography entry remains available. Direct raw GitHub delivery of MeshCore FAQ failed, but the GitHub contents API successfully returned the same pinned file. These access failures do not affect the successfully retrieved release/source facts. This was a focused mechanism audit, not a complete upstream code review or wire-equivalence test.

## Exact implemented mechanisms

| Dimension | MeshEcho-CPR | Legacy MeshEcho | Meshtastic-like | MeshCore-like |
| --- | --- | --- | --- | --- |
| Implementation | `MeshEchoCPR`, independent recovery selector in `meshecho_cpr.py`; reuses DRC PHY helpers | `MeshEcho(CalmMesh)` | `MeshtasticLike` | `MeshCoreLike` |
| Cold start | Useful DATA FLOOD; matching source ACK confirms the traversed path | RREQ flood, destination candidate collection, reverse RREP, then DATA | Useful DATA flood for every flow | RREQ flood, first RREP, queued DATA |
| Cached path | ACK-confirmed source route | Confidence-ranked source route | None | Source route learned from RREP |
| ACK | Destination reverse-path ACK with flow/marker/path/generation validation; overheard matching ACK can cancel eligible relay | Destination reverse-path ACK; may cancel pending source fallback | Destination reverse-path ACK along path accumulated by model | Destination reverse-path ACK along stored route |
| Source retry/recovery | At most one same-path repeat and one deadline-feasible recovery flood after routed initial transmission; cold-start behavior specified by FSM | No general reliable application-retry loop; failed discovery can trigger TTL-limited fallback | No application retransmission | No application retransmission; expired discovery drops pending queue |
| De-duplication | Bounded seen state plus CPR relay ledger; independent ACK/capacity switches required for clean ablations | Flood keys and pending fallback suppression | Per-node seen keys; overheard duplicate cancels pending copy | RREQ seen set; source-route DATA follows designated next hop |
| Discovery packets | None | RREQ/RREP | None | RREQ/RREP |
| Default cache TTL | 600 s | 600 s | Not applicable | 300 s |
| Local inputs | Current flow, cached confirmed route, local radio opportunity/time and decoded ACK; no future/fault oracle | Received SNR/collision proxy → carried confidence, route age and cache | Received SNR, role, duplicates | Received discovery path and route cache |
| Memory boundary | CPR cancellation ledger initially 8 records per relay; seen/pending/controller bounds must be reported separately | Several unbounded Python maps/sets | Unbounded Python seen/pending structures | Unbounded Python cache/discovery structures |

The CPR ledger bound does not prove a bound on all simulator or firmware memory. A canceled send is counted separately from committed or started sends; only started sends enter airtime. Protocols use the same half-duplex radio/queue and receive model. The higher layer may have different admission/expiry behavior, so an equal application deadline is an equal measurement horizon, not a claim of identical source FSMs.

## Default configuration and matching

Defaults here mean the implemented model's constructor/factory defaults, with the shared experiment PHY, traffic and deadline supplied separately. They are not official firmware defaults. Export both the requested overrides and resolved effective values in each run.

| Parameter | CPR default | Legacy ME default | MT-like default | MC-like default | Matched rule |
| --- | --- | --- | --- | --- | --- |
| Route TTL | 600 s | 600 s | None | 300 s | MC → 600 s; others unchanged |
| Flood base delay | 0.45 s | 0.45 s | 0.75 s | 0.5 s | Common 0.45 s |
| Uniform flood jitter width | 0.65 s | 0.65 s | 0.75 s | 0.7 s | Common 0.65 s |
| SNR delay adjustment | Weak-link term ≤0.35 s | Weak-link term ≤0.35 s | SNR penalty ≤0.6 s | None | Retain protocol-specific functions; equal base/jitter is not equal total forwarding delay |
| Repeater discount | 0.15 s | 0.15 s | `role_bonus_s=0.25` s | None | Retain; zero repeater-role fraction means no discount exposure |
| Discovery collection window | None | Nominal 2 s | None | 0 s, first reply | Retain policy difference; do not silently convert MC to best-of-window routing |
| RREP wait lower bound | None | 10 s | None | 10 s | Same nominal minimum; actual wait also accounts for PHY/hop bounds |
| Fallback TTL | Recovery uses declared hop budget | 2 | Not applicable | Not applicable | Retain; mechanisms differ |
| Confidence fallback threshold | Not used | 0.0 | Not used | Not used | Retain; normal cached confidence is nonnegative, so this threshold does not create routine confidence-triggered fallback |
| Additional legacy values | Not used | delay margin 0.6 s; hop penalty 0.025; age penalty 0.1; route-miss recovery enabled | Not used | Not used | Retain and disclose |
| CPR values | deadline from case; safety margin 0.25 s; fixed-guard constructor value 15 s inherited, but not the active CPR repeat selector | Not applicable | Not applicable | Not applicable | Same CPR configuration; no artificial baseline cloning |

The implementation uses a 0.05-s forwarding-delay floor. The nominal discovery collection/wait values can be enlarged by `Simulator.discovery_collection_window_s` and `route_discovery_rrep_wait_s` to respect serialized frame travel; record the resolved behavior and do not equate the nominal 2/10 seconds with every actual wait.

The old `build_protocol('meshtastic', args)` ignored `args` entirely. Its `meshcore` branch accepted only `meshcore_route_ttl_s`, `meshcore_discovery_window_s` and `sr_rrep_wait_s`; CALM flood parameters did not override MC delay defaults. The SECON explicit per-arm `protocol_parameters` mapping must validate actual supported attributes and serialize resolved values. Intended matched overrides are:

```json
{
  "meshtastic": {"base_delay_s": 0.45, "jitter_s": 0.65},
  "meshcore": {
    "route_ttl_s": 600.0,
    "flood_base_delay_s": 0.45,
    "flood_jitter_s": 0.65
  }
}
```

CPR and legacy ME use the same values in both regimes unless the frozen configuration explicitly states otherwise. Their identical runs may be reused only with a hash-checked alias. MC's discovery window remains zero. Other timers, cache semantics, retry counts, duplicate rules, source information and SNR-dependent terms remain distinct and are not claimed to be matched. `meshtastic-common-ack`/`meshcore-common-ack` are separately named supplemental policies with DATA-first ACK route learning and different flow semantics; they are not replacements for the four registered primary models.

## Wire, PHY and environmental assumptions

All arms use the simulator's custom `Packet.wire_size_bytes`: 10-byte base header (kind, TTL, 32-bit flow ID and 16-bit endpoint IDs), +4 bytes for RREQ/RREP request IDs, +2+2×path length for a carried path, +1 byte for relevant confidence/repair fields, and application payload only on useful DATA. Reverse-equivalent RREP paths are not double-encoded. Further optional path/feedback fields add their modeled bytes. Timestamps, class names and bookkeeping IDs are simulator metadata. This format is **not** Meshtastic protobuf framing or MeshCore 1/2/3-byte path hashes, encryption/authentication and full radio protocol overhead.

Use per-frame `RadioConfig.packet_toa_s`, never payload-only `toa_s`, for physical airtime. Shared PHY starts from explicit-header, CRC, eight-symbol preamble, 125-kHz BW, coding-rate index 1 (=4/5), 32-byte useful payload, and the frozen SF/power/hop settings. The imported generic radio default is 915 MHz, SF9 and 17 dBm; the old exposure profile overrides SF to 7. The new experiment matrix must state its actual values rather than inherit a manuscript caption. No regional duty-cycle/LBT compliance follows from using a carrier frequency. The simulator includes half duplex, overlapping-frame interference/capture threshold and probabilistic reception, but does not implement full regulatory access, hardware CAD timing, synchronization error or device energy measurement.

The planned common SECON scenario API uses a declared grid/obstruction environment and common link/time-bin reception field; the pilot configuration, not this draft, freezes numerical losses, endpoints, fault intervals and load. Source controllers receive no future fault or global reachability oracle. Environmental graph analysis is descriptive and retains all scheduled flows. Static shadowing and block fading in the imported model are already keyed by seed/link/time; a separate sequential channel RNG alone does not guarantee identical exogenous draws when protocols transmit different numbers of frames. The SECON common field and its identity audit must close that gap before main evaluation.

## Claims this comparison can support

After correctness and evidence gates, the comparison can describe costs and timely reliability of these four explicit model configurations, their sensitivity to the declared scenarios and the effect of clean CPR controls. It cannot establish superiority over official firmware, RF deployment performance, whole-device battery life, unqualified general LoRa-mesh performance or novelty of generic retry-then-flood recovery. A performance advantage against simplified no-retry models must be interpreted alongside this table and mechanism ablations.

## Upstream content fingerprints

| Pinned file | SHA-256 of decoded content |
| --- | --- |
| Meshtastic release `src/mesh/FloodingRouter.cpp` | `4c4ec5e1dfa0d2ee4f1ef8495cbc157d5749d232632f4a0af85792bdd7e63b06` |
| Meshtastic release `src/mesh/NextHopRouter.cpp` | `f73923666cbe55e2404e2fed74ff226e6c918c478557db52c30534b363134dac` |
| Meshtastic release `src/mesh/ReliableRouter.cpp` | `855065f84959a935e55ad54c1bc93c29387f0a958997a3d610adc00f0db5f9b2` |
| MeshCore pinned `docs/faq.md` | `72bf92b9bf78be9520103533c43782e49d5c80ca26e1296e686debaa3e0e1d64` |

These fingerprints and pinned links identify read scope. No upstream firmware was compiled, executed or measured during this audit.
