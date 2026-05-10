# ESP32 Smart-CALM Direct-LoRa Firmware

This directory contains the first burnable ESP32 firmware prototype for the
Smart-CALM controller on directly attached LoRa radios. It is a self-written
control layer inspired by source-routing and managed-flooding ideas, not a fork
of MeshCore or Meshtastic.

## What it does

- Hosts the Smart-CALM profile selector and tabular Q-learning controller.
- Loads the offline prior from `include/smart_calm_prior.hpp`.
- Initializes SX1262 or SX127x/RFM9x radios via RadioLib on ESP32.
- Encodes a compact Smart-CALM application frame with magic, version, sequence,
  source/destination, TTL, confidence, payload length, and CRC-16.
- Sends periodic status/hello frames and prints controller state over Serial.
- Receives Smart-CALM frames, rejects malformed/CRC-failed packets, and runs a
  custom mesh data plane with `RREQ`, `RREP`, `DATA`, `ACK`, and bounded
  fallback frame types.
- Keeps the controller logic separate from the radio driver so the data-plane
  can be expanded later.

## Design Boundary

The firmware follows familiar mesh-routing mechanics without copying another
project's protocol:

- MeshCore-like idea: discover a route first, then send unicast over a compact
  source path.
- Meshtastic-like idea: when confidence is weak or route discovery is missing,
  use bounded broadcast/fallback behavior instead of unbounded flooding.
- Smart-CALM-specific implementation: all frame fields, route payload encoding,
  confidence scoring, online profile selection, and learning hooks are defined
  in this repository.

## Frame format

The current over-the-air frame is defined in `include/smart_calm_types.hpp` and
serialized in `include/smart_calm_wire.hpp`.

Fields:

- `magic/version/type`
- `src/dst/seq`
- `flow_id/created_at_ms/ttl`
- `state_index/action_index/flags`
- `confidence_milli`
- `payload_len + payload`
- `crc16`

Maximum encoded size is `56 bytes` with the default `32 byte` payload.

## Build

1. Install PlatformIO.
2. Adjust the LoRa pin macros in `platformio.ini` if your board wiring differs.
3. If your board uses a different TCXO/LDO setup, tweak the `SMART_CALM_LORA_TCXO_VOLTAGE`
   and `SMART_CALM_LORA_USE_LDO` build flags.
4. Run:

```bash
pio run -e esp32dev_sx1262
pio run -e esp32dev_sx1262 -t upload
pio device monitor
```

For SX1276/SX1278/RFM9x boards:

```bash
pio run -e esp32dev_sx127x
pio run -e esp32dev_sx127x -t upload
```

## Serial Smoke Test

After flashing multiple nodes, set a unique `SMART_CALM_NODE_ID` per node and
open the serial monitor. From one node:

```text
send 3 hello
```

This asks node `1` to discover a route to node `3`, send a Smart-CALM `DATA`
frame over the discovered source path, and receive an `ACK` back along that
path.

## Notes

- Default frequency is `915 MHz`, which is the usual US ISM band setting.
- The current firmware is a direct LoRa prototype, not a UART transparent modem.
- It already has an over-the-air packet format, route discovery, source-route
  forwarding, ACK return path, and a serial-triggered application send path.
- The next firmware step is to add timeout retry, persistent route aging,
  neighbor/link-quality tables, and richer delivery telemetry.
