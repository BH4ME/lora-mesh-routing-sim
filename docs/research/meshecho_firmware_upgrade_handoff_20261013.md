# MeshEcho Firmware Upgrade Handoff (2026-10-13)

## Active firmware continuation supersedes manuscript boundary

The latest goal continuation resumes full firmware work, not paper editing.
Current exclusive ownership: core.hpp/lifecycle tests = paper_comparison_check;
runtime tests = canonical_target_inventory; production node/runtime/unified
runner = root; token/driver/budget audit = firmware_budget_adapter (read-only).
First vertical slice is physical-start-anchored per-flow ACK wait followed by
recovery FLOOD generation. Preserve all39 green native cases, then complete
deep-path/lifecycle/queue/modular-time gates and all canonical board builds.
No paper edits, GitHub/EDAS write, reserved-seed run or physical flashing.

## Latest boundary: manuscript verification and current firmware state

The latest live request is the same open ICC manuscript's Meshtastic/MeshCore
comparison and formula exposition. That revision was already present and
has been recompiled successfully. Firmware work is preserved, not complete;
do not let older continuation headings override this current turn boundary.

Collected native PlatformIO session 16324: **39/39 Unity cases passed**.
No latest-board success is claimed from this result. All firmware agents
stopped further implementation; no owned test session remains running.

Production changes present in the canonical tree:

- CprRuntime::prepareTx checks original source budget, flow lifecycle, route
  and generation before radio send; rejects call CprNode::onTxDiscarded so
  app/controller capacity is released. Enqueue/encode/discard paths share it.
- CprNode::onFrame rejects RREQ/RREP; unsolicited RREP no longer installs a
  route. Legacy private discovery helpers remain and still need cleanup.
- Source ACK generation is strict, including zero. Off-path terminal-ACK
  cancellation validates physical sender/path/index/payload and requires the
  cancelled relay to be absent from the ACK path.
- Wire version 2 renames the duration field to remaining_budget_ms; old v1
  frames are rejected even with valid CRC. created_at_ms is opaque metadata,
  not comparable to a receiver's clock. Header/max frame stay 36/86 bytes.
- CprOutboundFrame and pending relay slots carry local expires_at_ms.
  pushImmediate uses local now; receive subtracts configured worst-case frame
  airtime; prepareTx rewrites the countdown and reencodes. Clock-offset test
  forwards budget 9690 ms on relays with different boot epochs. Modular
  cprTimeBefore assumes all compared intervals are below 2^31.
- Budget helper plus main use encoded wire size and LoRa ToA, 8 nodes/7 hops,
  default 30000-ms deadline and 200-ms per-hop guard. Default max exchange is
  10591 ms; SF12 is 58660 ms. All 9 helper cases pass within the native gate.
  Main passes fresh millis() after serial/radio processing.
- Combined ASan/UBSan helper run stopped before main in host ASan initializer
  recursion; owning agent terminated exact PID 76568 (session 97610 exit143).
  Diagnostic: /tmp/meshecho-cpr-budget-tests.7qKs0H/sanitizer-sample.txt.
  Do not report ASan or combined sanitizer success.

Required next firmware work, not part of the current paper request:

1. Cover full routed initial/repeat/recovery/ACK sequence; set recovery FLOOD
   generation and use per-flow route_bound rather than default500-ms timeout.
2. Generation-match route invalidation, retired-ID replay protection, endpoint
   validation, expired route-slot reuse, DATA/FLOOD admission/dedup and ACK TTL
   sufficient for all7 reverse hops.
3. Complete modular-time audit, including source/controller/route expiry;
   cover queued repeat/recovery under ACK, route changes and congestion.
4. Make runtime multi-node helpers use prepareTx, then rerun native, three
   canonical board targets, radio adapter suite and nonreserved simulator smoke.
5. Only after those gates, update version/docs/artifact checksums and audit
   every CPR requirement. Current firmware0.1.4/repository2.1.27 stay unchanged.

No reserved seeds, GitHub push, EDAS action, flash or physical RF/PDR test.

## Firmware objective resumed after latest paper closeout

The active goal now explicitly resumes algorithm and dual-MCU firmware work.
Historical manuscript-priority sections below no longer stop firmware work.
Root owns production core/node/runtime. An agent owns one runtime preflight
regression; another owns budget.hpp/main/budget tests/README. An independent
audit checks provenance, relay cancellation and clock semantics. No builds or
new tests from this resumed slice are claimed yet. Current exact next action:
late queued initial-flood budget RED, then implement physical-start preflight
and source lifecycle cleanup; follow with RREP/generation/relay corrections.

## Latest paper-request boundary and collected native result

The newest user request again concerns the existing ICC manuscript's baseline
comparison and formula explanation. The original source was revised and compiled
in place; firmware changes are preserved, not certified complete.

- Collected pending native PlatformIO session 97104: 23 Unity cases passed
  (7 core, 14 wire, 2 runtime). The runtime cases cover serialized three-node
  cold FLOOD/ACK/path learning and rejection of a valid-CRC wrong-sender ACK.
- Root fixes include rejection of duplicate live IDs, retirement of expired
  never-started apps, cold initial DATA flooding, and ACK path installation
  with 600000-ms TTL. Do not mistake this for complete ACK-only provenance:
  the old RREP installation branch remains to be removed.
- prepareTx remains missing although main calls it. Queue-drop lifecycle
  cleanup, recovery generation and all canonical board gates remain open.
- Radio/wire agents saved their verification below; no agents are still
  running firmware tests. Firmware version remains 0.1.4; no push or flash.

## Active firmware goal resumed

The user resumed algorithm upgrade and PlatformIO firmware work after the
completed manuscript turn. The manuscript boundary below is historical,
not an instruction to stop the active firmware goal. Current plan: TDD
source/runtime and ACK-proven route corrections, independent TX_DONE and
codec repairs, real Unity/runtime coverage, canonical builds and smoke.
No reserved seeds, new paper edits, push or EDAS actions are authorized.

## Latest boundary: manuscript request takes priority

The current user request concerns baseline comparison and formulas in the
open ICC source. Firmware implementation is incomplete and was stopped at
a safe boundary; do not continue it instead of answering the paper request.

Firmware recovery facts:

- Completed-flow retirement caching was added to the core; direct C++ tests
  pass, but current PlatformIO native and board gates have not been rerun.
- Board configuration uses ESP32 NSS GPIO5, exact-one radio kind validation,
  and explicit SX1262 DIO2 RF switch configuration. Four board config tests
  pass. main.cpp now calls runtime.prepareTx(now_ms), still unimplemented.
- New TX_DONE tests fail for both radio adapters: finishTransmit() is called
  immediately and truncates an asynchronous transmission. A bounded IRQ
  completion wait remains required; no post-change board build is valid.
- Wire fixed header size changed 35 to 36 and maximum frame 85 to 86. Two
  standalone Unity cases pass, including the maximum path/payload red-green
  case. Register them in the unified runner and add remaining wire cases.
- ACK physical sender/payload validation, pending discovery/RREP endpoint
  validation and deduplication, physical-start deadline/generation gating,
  unstarted-flow expiry/drop cleanup, nonzero recovery generation, duplicate
  live flow rejection, and ACK-confirmed route provenance remain unresolved.
- No version bump, simulator smoke, push, flashing or RF validation occurred.

Current manuscript closeout: the same open ICC source now has 28 equation
groups, with full baseline names and formula references, corrected simulator
commit-versus-air-start timing, ACK route lifecycle, conditional stage gains
and pooled delivery-cost comparison. Built-in compilation and four metadata
tests pass. No standalone PDF export or new simulation was performed. This
does not resolve any of the incomplete firmware gates above.

## Objective

Upgrade MeshEcho-CPR from a simulator-only policy into a portable, fixed-memory
firmware core with PlatformIO targets for ESP32 and nRF52840. Preserve the
simulation-only and no-hardware-claim boundary until a real radio testbed is
available.

## Current State

- Repository release: `2.1.27`.
- Existing firmware: `firmware/esp32_smart_calm/`, identity
  `meshecho-firmware-v2.1.2`, Arduino + RadioLib, ESP32 SX1262/SX127x only.
- Existing host smoke test passes with `g++ -std=c++17` against the Smart-CALM
  headers.
- PlatformIO 6.1.19 is available. Board inventory includes `esp32dev`,
  `adafruit_feather_nrf52840`, `nrf52840_dk`, and `nrf52840_dk_adafruit`.
- Existing core has fixed arrays but is an older Smart-CALM route/fallback
  implementation, not the ICC MeshEcho-CPR state machine.

## 2026-10-13 continuation checkpoint

- The new implementation is being created under `firmware/meshecho_cpr/`.
- The existing Smart-CALM project is intentionally not being relabeled as CPR;
  its headers and tests remain a historical compatibility reference.
- The first implementation slice will be a platform-independent C++17 core
  with no heap allocation. RadioLib adapters will only translate transmit,
  receive, RSSI/SNR, and millisecond clock events.

## CPR Requirements

1. Confirmed route state includes endpoint, path, route generation/epoch,
   expiry, and ACK-confirmed provenance.
2. A routed flow may issue one same-path repeat only after the first physical
   TX has started and no matching ACK has been accepted.
3. At most one recovery flood is admitted, and only when its conservative
   deadline budget fits at physical TX admission time.
4. Relays keep bounded pending-flood handles. Cancellation requires matching
   flow/request/endpoints, generation/marker/sender, valid reverse path, and an
   uncommitted handle. A committed TX remains charged.
5. State is fixed-size and heap-free; no simulator-only API or global PRR
   oracle may be required by the core.

## Planned Project

```text
firmware/meshecho_cpr/
  platformio.ini
  include/meshecho_cpr_core.hpp
  include/meshecho_cpr_wire.hpp
  src/main.cpp
  test/test_cpr_core.cpp
```

Target environments: `native`, `esp32dev_sx1262`, `esp32dev_sx127x`, and
`nrf52840_sx1262` using `adafruit_feather_nrf52840` unless the physical board
is later specified otherwise.

## Verification Gate

- Host/native CPR tests pass.
- ESP32 SX1262 and SX127x PlatformIO builds pass.
- nRF52840 SX1262 PlatformIO build passes.
- A simulator smoke run is executed after the release version increment.
- Only then update `VERSION`/firmware metadata and changelog. Compile success is
  not hardware validation; flashing and RF measurements remain separate.

## Recovery Rule

Before context compression, update `task_plan.md`, `findings.md`, `progress.md`,
and this handoff file. After resuming, read all four files before making new
implementation decisions.

## ICC manuscript comparison revision

- The open ICC source now contains explicit ACK and destination-delivery
  branches for legacy MeshEcho, Meshtastic-like flooding, MeshCore-like
  cache/discovery routing, and MeshEcho-CPR.
- The results section also reports normalized mechanism counters for cache hits,
  discovery success, suppressed relays, and fallback forwards.
- The source compiled successfully to a six-page PDF with 30 numbered
  equations; no overfull boxes or undefined cross-references were reported.
- Product rows remain behavior-level simulator models, not official firmware or
  hardware measurements.

## Canonical Target Recovery Checkpoint (2026-10-13)

- Canonical delivery tree: `/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2`.
- Only `firmware/meshecho_cpr/test/test_cpr_core.cpp` exists in the target
  firmware directory at this checkpoint; it defines the required `CprCore`
  compatibility surface.
- The complete implementation in `/Users/bh4me_macair/Documents/Codex/lora_mesh`
  is a reference only. Its successful `0.1.4` builds must not be used as target
  completion evidence.
- Porting must preserve fixed memory, route generation, physical-start repeat,
  deadline-gated single recovery flood, strict ACK identity, and bounded relay
  cancellation, then provide PlatformIO `native`, ESP32 SX1262/SX127x, and
  nRF52840 SX1262 environments.
- No hardware validation has been performed. After porting, rerun target-tree
  tests/builds and append exact results and artifact paths before any automatic
  context compression.

## 2026-10-13 integration audit continuation

- The requested PlatformIO environments compile and the native executable exits
  successfully, but the current test does not exercise the production node and
  runtime path.
- Before claiming the algorithm upgrade complete, add tests for multi-hop
  route/data/ACK forwarding and for a recovery-flood relay canceled by a
  matching ACK before its due time.
- The next implementation fix must copy wire `route_generation` into the ACK
  observation and require the ACK path to preserve the pending relay path
  prefix; otherwise the relay ledger is weaker than the CPR contract.

## 2026-10-13 Paper formula checkpoint

- The open ICC LaTeX source now includes an explicit Results-side comparison
  equation for the four protocol families and numerical CPR-relative airtime
  and TX-count ratios from the existing holdout ledger.
- Full XeLaTeX/BibTeX build `build-user-baseline-formula-results-20261013i`
  produced a verified six-page PDF. References [1]--[5] were checked in the
  rendered page, and no overfull/undefined/fatal diagnostics were observed.
- This checkpoint is manuscript-only; it does not change firmware version,
  establish RF hardware validation, push GitHub, or submit EDAS.

## 2026-10-13 manuscript checkpoint

- The open ICC manuscript was revised independently of the firmware audit.
- It now contains explicit state-transition equations for Meshtastic-like,
  MeshCore-like, legacy MeshEcho, and MeshEcho-CPR, plus a formula-reference
  row in the protocol comparison table.
- The manuscript source compiles with the desktop LaTeX diagnostic. Do not
  infer a fresh canonical PDF export or hardware evidence from that result.

## 2026-10-13 wire-test closeout before manuscript handoff

- Wire validation work is paused for the newer manuscript request. Only
  `firmware/meshecho_cpr/include/meshecho_cpr_wire.hpp` and
  `firmware/meshecho_cpr/test/test_cpr_wire.cpp` were changed in this slice.
- `runCprWireTests()` registers 14 Unity cases covering identity round trips,
  maximum path/payload, every single-byte CRC mutation, invalid magic/version,
  truncation/trailing bytes, null decode inputs, reserved addresses, invalid
  envelope/path fields, oversized payloads, ACK payload rejection, and minimum
  FLOOD/RREQ frames. The repository test has no standalone `main`, `setUp`, or
  `tearDown`; the unified runner must call the aggregator.
- Test-proven fixes: fixed header size is 36 bytes (maximum frame 86 bytes),
  and both encoder and decoder reject broadcast source/path addresses.
- Strict C++17 standalone aggregate and UBSan-only aggregate both completed
  with `14 Tests 0 Failures 0 Ignored`, exit 0. Temporary runner and binaries:
  `/tmp/meshecho-cpr-wire-tests.nBGDcd/`.
- ASan/UBSan compilation succeeded, but the executable hung before `main` in
  macOS dyld/malloc/ASan initialization (`StaticSpinMutex::LockSlow`). Sampling
  evidence is `sanitizer-sample.txt` in the temporary directory. Exact PID
  69954 was terminated (exit 143); this is not an ASan pass or a codec failure.
- Scoped `git diff --check` passed; the firmware directory is untracked, so
  this does not certify all new-file whitespace. No simulation, canonical
  PlatformIO rerun, board build, version bump, commit, push, or RF test was
  performed by this wire slice. Root owns the remaining firmware gates.

## 2026-10-13 radio adapter verification checkpoint

- Canonical tree: `/Users/bh4me_macair/Documents/Codex/lora_mesh_current_version_v2`.
- RadioLib 7.6.0 `finishTransmit()` only clears IRQs and enters standby. The
  SX1262/SX127x adapters now explicitly poll their actual TX_DONE masks before
  cleanup. Other IRQ flags must not complete TX.
- Timeout is `5 + ceil(5 * ToA_us / 1000)` ms with a 64-bit intermediate and
  unsigned elapsed-time arithmetic across 32-bit `millis()` rollover. The
  wait is bounded but blocking. Timeout/cleanup errors still attempt RX
  restart and do not replay an already started frame.
- `tx_in_progress_` prevents overlapping starts, premature RX restart and
  double completion. A new failing test demonstrated that direct `receive()`
  still read the radio during TX after a shared IRQ; both adapters now reject
  receive while TX is active. TX IRQs do not become received DATA afterward.
- Earlier configuration fixes are preserved: ESP32 NSS is GPIO5 instead of
  the conflicting VSPI SCK GPIO18; board builds require exactly one radio;
  TCXO, LDO and DIO2 RF-switch flags reach the SX1262 driver.
- Wiring/module assumptions and TX completion behavior are documented in
  `firmware/meshecho_cpr/README.md`. Feather SPI is SCK D26 / MISO D24 / MOSI
  D25 (Arduino pin indices), verified against the installed board variant.
- Verification: `python3 -m unittest tests/test_cpr_board_config.py -v`
  passed all 12 tests in 18.582 s, with both-chip subcases for TX completion,
  missing TX_DONE, ToA rounding, rollover, cleanup failure, failed physical
  start, overlap/receive rejection and RX restart failure. Compiler and test
  subprocesses have 30 s / 5 s timeouts respectively.
- The receive-during-TX test was observed RED for both chips and then GREEN
  after the guard fix. `git diff --check` was clean for the owned radio/test
  paths. No full board builds were run after this continuation's edits.
- Pending before release: run native and all three complete PlatformIO board
  builds from the canonical tree, then the release/version and simulator gates
  under the parent workflow. No push, flash, or RF measurement was performed.
- Firmware work is paused on the newest user redirect to manuscript revision;
  all current firmware changes remain preserved for later resumption.

## 2026-10-13 retained firmware state at manuscript redirect

- Latest user request is manuscript-only: explicit Meshtastic/MeshCore
  comparisons and mathematical explanation. Do not resume firmware from an
  older objective without checking the latest user message.
- Preserve node/runtime changes for own-source route validation, failed-flow
  slot release, per-flow ACK timing from actual TX start, recovery epochs,
  reverse ACK TTL, route refresh/generation checks, DATA/FLOOD sender checks,
  wrap-safe deadlines, pending-slot lease validation and actual-byte ToA.
- Core/lifecycle agent completed 17/17 standalone cases, including accepting
  a valid wire-generation-zero cold F_INITIAL ACK after another flow installs
  a route, and clearing initial route metadata when falling back to F_INITIAL.
  Do not describe this as a complete native aggregate pass.
- Latest full native session 54449 failed on the concurrent cold-start ACK
  case before that core fix. Native aggregate must be rerun after remaining
  production fixes; no root exec sessions remain running.
- Runtime test agent froze 12 registered cases. The retained RED is
  testRuntimeAlternatePathFloodDuplicateCancelsPendingRelay: same origin/flow
  arriving through different preceding senders still queues one relay when
  zero is expected. DATA dedup has not yet been added. No aggregate of all
  12 runtime tests was run after the last test addition.
- Remaining risks: a late cold-start ACK must confirm the application without
  overwriting a newer different route; an older flow deadline must not
  invalidate a same-generation route freshly refreshed by another ACK.
- Relay agent's six standalone cases passed; README updates are retained.
  Final canonical native, 12 radio/board checks, three PlatformIO targets,
  fresh authorized nonreserved-seed smoke and release gates remain required.
  No version bump, push, flash or physical RF validation was performed.
