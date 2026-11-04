# MeshEcho CPR firmware

This PlatformIO project wires the board-neutral CPR runtime to RadioLib. The
runtime owns bounded frame encoding, queueing, and delivery; the radio adapter
only translates those byte operations to SX1262 or SX127x calls.

Current release: `0.1.4`. This release commits CPR's initial/repeat/recovery
marker at the successful physical TX start, then waits for RadioLib TX
completion without replaying a frame when the completion wait fails. It also
rejects a queued routed transmission when its confirmed route expires before
the physical TX start, uses current-time route lookups for recovery admission,
and keeps forwarded DATA/FLOOD frames separate from source-side CPR TX markers.
Per-flow retry timers wait at least the configured routed-exchange budget.
Reverse ACKs receive a fresh hop budget, and an ACK confirming the same path
refreshes its lifetime without changing its route generation.

Build targets:

```text
native                 host smoke tests (no RadioLib hardware)
esp32dev_sx1262        ESP32 DevKit + SX1262
esp32dev_sx127x         ESP32 DevKit + SX127x/RFM9x
nrf52840_sx1262        Adafruit Feather nRF52840 + external SX1262
```

The pin maps and LoRa defaults are compile-time profiles in `platformio.ini`
and `include/meshecho_cpr_radio.hpp`. They are illustrative wiring profiles;
this repository does not claim board, antenna, or over-the-air validation.

## Radio wiring and module assumptions

| Profile | SPI SCK / MISO / MOSI | NSS | Interrupt | Reset | BUSY / second interrupt |
| --- | --- | --- | --- | --- | --- |
| ESP32 + SX1262 | GPIO18 / GPIO19 / GPIO23 | GPIO5 | DIO1: GPIO26 | GPIO14 | BUSY: GPIO27 |
| ESP32 + SX127x | GPIO18 / GPIO19 / GPIO23 | GPIO5 | DIO0: GPIO26 | GPIO14 | DIO1: GPIO27 |
| Feather nRF52840 + SX1262 | D26 / D24 / D25 | D10 | DIO1: D6 | D5 | BUSY: D9 |

ESP32 uses the Arduino default VSPI bus. Feather numbers are Arduino digital
pin indices, not raw nRF52840 port numbers. NSS must not share SCK, MISO, or
MOSI. The SX127x profile uses the RadioLib `SX1276` driver; other chip variants
need a compatible driver rather than just a pin change.

The SX1262 profiles assume a 1.6 V DIO3-controlled TCXO, DC-DC regulation,
and a DIO2-controlled RF switch. These are module-specific assumptions, not
universal SX1262 defaults. Override `MESHECHO_CPR_LORA_TCXO_VOLTAGE` (use zero
for a crystal module), `MESHECHO_CPR_LORA_USE_LDO`, and
`MESHECHO_CPR_LORA_DIO2_RF_SWITCH` according to the module schematic. DIO2
controls the module's RF switch, not the MCU's packet interrupt.
Match the frequency, antenna, power supply, and local radio rules before
attempting a physical transmission.

## TX completion contract

`transmit()` starts RadioLib's asynchronous TX. A successful start is the CPR
commit boundary; `finishTransmit()` then polls the chip's actual TX_DONE
flag before invoking RadioLib cleanup and attempting RX restart. RadioLib's
cleanup call alone does not wait for TX completion.

The wait is blocking but bounded by `5 + ceil(5 * ToA_us / 1000)` milliseconds.
Elapsed-time arithmetic handles the 32-bit `millis()` rollover. A timeout,
cleanup error, or RX-restart error returns failure without retransmitting an
already started frame. Calls cannot start another TX, enter RX, or read a
packet while TX is active. TX interrupts are cleared from the software RX
flag before receive mode resumes.

Host adapter tests use a fake driver to cover TX_DONE, timeouts, clock
rollover, and error recovery; they do not validate real interrupts, SPI
signals, or RF behavior.

## Retry, ACK, and relay lifecycle

After a physical source TX start, each flow waits
`max(app.route_bound_ms, ack_timeout_ms_)` before requesting its next stage.
The routed-exchange budget therefore takes precedence over a shorter ACK
timeout. Queueing a frame does not start this timer or commit a CPR stage;
successful physical TX start does.

The destination sets a newly generated reverse ACK's TTL to
`path.length - 1`, independently of the received DATA/FLOOD's remaining TTL.
This permits the supported maximum of eight path nodes and seven radio hops
in each direction. A successful ACK confirming the current path calls
`routes_.refresh()` to extend its lifetime while preserving its generation;
a different confirmed path is installed as a new generation. An old flow's
deadline invalidation applies only to its recorded generation.

Pending relays use fixed slots with an incrementing nonzero token `lease`.
Each queued outbound frame retains its `pending_lease`; `canTransmit()`,
`onTxStarted()`, and `onTxDiscarded()` check that it still owns the slot.
Runtime queue purging also checks the lease, so a canceled frame's old
reference cannot transmit, commit, or discard a replacement in the same slot.
ACK cancellation applies only before physical TX start, and cannot undo an
already committed relay transmission.

## Airtime-derived admission and deadlines

The application no longer supplies fixed 5-second routed and 10-second flood
budgets. `include/meshecho_cpr_budget.hpp` calculates LoRa time on air from the
configured bandwidth, spreading factor, coding-rate denominator, preamble,
PHY CRC, explicit/implicit header, and low-data-rate optimization (LDRO).
Both current radio adapters use explicit headers, PHY CRC and automatic
LDRO. The helper supports their common SF7--SF12 range; changing the radio's
packet-mode defaults also requires changing its matching budget configuration.

The CPR wire length is `38 + 2 * path_nodes + payload_bytes`, including the
two-byte CPR CRC. The current limit is eight path nodes, therefore seven
radio hops, not eight. Each routed exchange budgets DATA and a zero-payload
reverse ACK on every hop. Flood admission uses a worst-case seven-hop corridor
and maximum path overhead on each hop. The application conservatively uses
that same worst-case path length for routed admission, too.

The default per-hop scheduler guard is 200 ms, applied once for DATA and once
for ACK. It includes the current maximum 140 ms flood relay jitter. This is
a bounded-scheduler assumption, not a deterministic upper latency bound for
arbitrary collisions, queues, interference or duty-cycle restrictions. At
SF9/BW125/CR4/7 with 32 payload bytes, maximum DATA takes 657 ms and ACK takes
456 ms after upward millisecond rounding. Seven-hop admission reserves
`7 * (657 + 456 + 2 * 200) = 10591 ms`. With SF12 and automatic LDRO, the same
exchange reserves 58660 ms. A 30-second deadline must reject the latter
instead of claiming that it fits.

Build flags `MESHECHO_CPR_APP_DEADLINE_MS` (default 30000) and
`MESHECHO_CPR_HOP_GUARD_MS` (default 200) configure these assumptions. Deadlines
must be between 1 and `0x7fffffff` milliseconds; the hop guard must cover the
configured relay jitter. The serial command is
`send <destination> <flow_id> <payload>` with a non-space payload of at most
32 bytes. Use a unique nonzero node ID on every board and a fresh nonzero flow
ID for each message. `queued=0` includes rejected, duplicate or
deadline-infeasible sends; it is not evidence of an over-the-air transmission.

Wire version 2 carries a *remaining duration*, not a remotely comparable
absolute deadline. Startup calls `runtime.setAirtimeConfig(budget_config)`
with the matching PHY configuration. The source retains its local deadline.
Each receiver calculates ToA from the actual received wire length, subtracts
that packet's airtime, and establishes a deadline on its own local clock.
Immediately before physical TX, preflight checks that the actual encoded
frame's airtime still fits, then updates its wire duration to reflect time
already spent queued. It does not subtract the upcoming airtime from the
encoded duration: the next receiver accounts for that hop's airtime once.
Worst-case exchange admission remains separate from this per-frame countdown.

`created_at_ms` remains source-clock metadata and is not synchronized wall
time. Rollover-safe duration comparisons work within the half-range clock
horizon. This countdown does not synchronize independent clocks or eliminate
oscillator drift. The current radio API does not timestamp RX completion, so
IRQ-to-poll delay is covered only by the scheduler-guard assumption. Hard
real-time validation would need measured scheduling bounds and RX timestamps.

## Memory and verification boundaries

The CPR state machine, fixed queues, wire buffers, and airtime-budget helper
do not require heap allocation. This does not make the entire firmware or
RadioLib heap-free: RadioLib's default SPI transfer path uses dynamic
allocation, and constructing a `Module` may allocate its HAL. Whole-firmware
memory claims require a separate dependency and runtime audit.

CPR CRC detects accidental byte corruption; it does not authenticate an ACK
or prevent a malicious radio from impersonating a node. These firmware
profiles are experimental and not a replacement for authenticated production
mesh protocols. They have not been flashed or RF-tested on physical hardware.

Available native tests cover encoded frame validation; physical-start stage
commitment; cold flood delivery and reverse-ACK route learning; routed
repeat/recovery; independent node clocks; deadline rejection and slot release;
seven-hop DATA/FLOOD and ACK round trips; same-path generation refresh;
rollover-safe route expiry; ACK identity and repair markers; relay lease reuse
and bounded capacity; and frame-length/PHY airtime calculations. Test presence
does not assert that the final native and board gates have been rerun for the
latest changes.

Run the host gate from `firmware/meshecho_cpr`:

```bash
pio test -e native
```

Run each board compile gate from the same directory:

```bash
pio run -e esp32dev_sx1262
pio run -e esp32dev_sx127x
pio run -e nrf52840_sx1262
```

Run the adapter configuration/driver checks from the repository root:

```bash
python3 -m unittest discover -s tests -p 'test_cpr_board_config.py'
```

Those checks cover SPI chip-select separation, exactly one selected radio
kind, SX1262 module flags, TX_DONE waiting, timeouts, rollover, cleanup,
RX restart, failed physical starts, and TX-overlap prevention using a fake
driver. Successful host tests or board compilation do not establish radio
interoperability, measured packet delivery, or over-the-air validation.
