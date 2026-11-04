# SECON development pilot preflight

2026-11-04 (Asia/Shanghai). **Configuration preflight passed; no pilot execution or performance result is asserted here.** Reviewed `configs/secon2027/development_pilot.json`, file SHA-256 `8e91e49204b33cff34c77bd1fc1620e8fc1ee10b4fcc32d2227a199a21cedd2e`, actual constructors and runner/scenario semantics. No `Simulator.run`, research-seed trace generation or new seed exposure occurred in this review. Structural graph checks used a non-running seed-0 fixture only; positions have no effect on the declared neighbor graph.

## Planned inventory and configuration

- Matrix schema and closed-field checks pass. `generate_runs` produces **72 unique planned keys**: 3 development seeds × 3 scenarios × 4 models × 2 configuration regimes. Each of the six scenario/regime cases has 12 runs. Per-case arm selection is explicit and correct; there is no accidental six-case × eight-arm cross product.
- Seeds are the already registered development cohort `2027000, 2027001, 2027002`. They were exposed by P0 smoke and remain development data. This pilot must never be called a new holdout.
- Traffic rates are **network-total** Poisson rates: S1=8, S2=8, S3=40 flows/min. The scheduler inserts a first flow at t=1 s, then exponential interarrivals until t<240 s; four endpoint pairs are selected in fixed round-robin order. These are not per-node or per-pair rates. The same seed gives the same environment/arrival process within a scenario and regime; S3 changes arrival times through its fivefold rate, not topology or fault settings.
- All cases use a 240-s generation window, 30-s application deadline, and 270-s accounting cutoff. Effective defaults additionally resolve to maximum 6 hops, 32-byte app payload, 17 dBm, path-loss exponent 2.75, SF7/BW125 kHz/CR index1 (4/5), capture threshold6 dB, and route/flood settings below. Static shadowing and temporal fading have sigma2 dB; fading blocks are60 s. The full resolved values must remain in the saved identities/manifest.
- `area_m=5000` is metadata for the case; the opt-in grid environment constructs actual coordinates from four rows × five columns at1000-m spacing plus ±2.5% positional jitter. It does not sample a uniform5000-m square. This is a synthetic obstruction/multihop experiment, not a calibrated field deployment.

## Effective model parameters

Constructor-only validation succeeded for all eight arm declarations; every requested override names a supported numeric attribute.

| Model | Default TTL / base / jitter (seconds) | Matched TTL / base / jitter | Retained difference |
| --- | --- | --- | --- |
| MeshEcho-CPR | 600 / 0.45 / 0.65 | 600 / 0.45 / 0.65 | Deadline30 s, safety margin0.25 s, repeat/recovery/ACK cancellation and ledger enabled |
| Legacy MeshEcho | 600 / 0.45 / 0.65 | 600 / 0.45 / 0.65 | Discovery collection2 s; nominal RREP wait10 s |
| Meshtastic-like | none / 0.75 / 0.75 | none / 0.45 / 0.65 | SNR-dependent delay term and no route cache/application retry |
| MeshCore-like | 300 / 0.50 / 0.70 | 600 / 0.45 / 0.65 | Discovery collection remains0 s, nominal RREP wait10 s, no application retry |

CPR and Legacy MeshEcho have identical effective default/matched parameters. The72-run budget explicitly includes both executions, which is permissible; their duplicated seed outcomes are not additional independent samples. Any later storage/reuse optimization requires a declared identical-source/config/seed alias, not silent omission. Matching covers comparable TTL/base/jitter values, not all timers, source FSMs, ACK semantics or retry budgets. All nodes use router role; repeater discounts have no exposure.

## Structural fault and alternate-route checks

Endpoint pairs are5→9,9→5,10→14,14→10. Their neighbor-graph shortest path is **4 hops** in S1 and S3. S2 attenuates unordered edges(7,8) and(12,13) by an additional80 dB during **80≤t<160 s**; all four endpoint pairs retain **6-hop** alternatives through the outer rows. Checks at79.999,80,159.999 and160 s confirm the intended boundary. The6-hop route fits the declared maximum, but it does not guarantee a successful discovered or decoded path under interference and fading.

Neighbor links already receive20 dB synthetic attenuation and nonneighbors80 dB; S2 fault attenuation is additive, so affected neighbor links receive100 dB total obstruction while the fault is active. The simulator applies power/fading/fault state at each TX start. A frame spanning a fault boundary retains the field sampled at its start. The keyed reception uniform uses directed link and10-ms time bin; it does not depend on packet/TX IDs or protocol draw counts. Half duplex and interference remain protocol-induced physical effects.

Code search finds fault/environment evaluation only in the scenario and recording-simulator physical layer. Protocol implementations do not read `common_environment`, fault lists or offline `shortest_hops`. Controllers see local timestamps, cached routes and received packets; offline graph analysis is not algorithm input. The synthetic graph determines structural exposure only: weak nonneighbor reception is probabilistically possible, so actual paths must be reported rather than assumed equal to the graph distance.

## Required diagnostics after the complete pilot

All diagnostics must retain the full scheduled population and all72 planned outcomes, including negative results.

1. **Common inputs:** compare exported topology, endpoint, application-trace, static-shadowing and common-environment hashes across each seed's paired models. Verify resolved scalar parameters match this table. CPR/ME duplicate regimes should be identical where their full effective inputs match; investigate any difference before freezing formal evaluation.
2. **Actual depth:** report successful destination and ACK path-hop distributions, cold-start versus routed-initial requests, and all scheduled flow count. Four structural hops and a6-hop limit are not measured multihop evidence by themselves.
3. **S2 fault exposure:** count flows enqueued within[80,160), still active during that interval, and whose **actually started cached initial DATA route** contains(7,8) or(12,13) while the fault is active. Report overlaps separately from realized next-hop attempts on faulted edges. Distinguish a cached route fault from a flow that merely happened during the fault interval. Report offline6-hop alternatives as structural facts, never use reachability to remove denominators.
4. **Recovery:** join source request→physical TX for marker1 repeat and marker2 recovery; do not count timer requests as actual sends. Break down ACK absence after real destination delivery versus lack of DATA delivery, no-start/deadline reasons, late ACKs and route-refresh outcomes. Record whether failed cached paths were actually recovered.
5. **S3 contention:** compare actual offered flow counts, capture-collision and half-duplex outcomes, positive queue waits, queue/deadline rejection, actual source retry/recovery starts, capacity eviction and ACK cancellation request/success counts. A configured40/min rate does not by itself prove meaningful pressure or nonzero ledger eviction.
6. **Cost and resources:** check packet-kind × stage partition sums to actual physical airtime; use physical-start fields rather than `legacy_reserved_*`. Measure per-case/regime wall time, peak RSS, raw/archived bytes and all failures before selecting formal sample size and concurrency. Do not promote an incomplete matrix to a complete pilot.

No numerical exposure success threshold is retroactively imposed by this preflight. The pilot diagnoses whether the intended mechanisms activate; any development changes must be recorded in a new configuration/version. Formal scenario-validity criteria, sample size, clean ablation matrix, finite robustness axes and analysis policy still require their one-time freeze after the development review.
