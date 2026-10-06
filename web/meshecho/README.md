# MeshEcho Web

Browser-first product surface for MeshEcho:

- official website
- Meshtastic-style Web Flasher shell
- Web Serial / BLE / WiFi configuration console

This package is original MeshEcho code. Meshtastic Web Flasher is used as a
product and architecture reference only; its GPL-3.0 source is not copied here.

## Run

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```

## Firmware Artifacts

Build ESP32 firmware targets from the repository root:

```bash
pio run -d firmware/esp32_smart_calm -e esp32dev_sx1262 -e esp32dev_sx127x
```

Then sync the PlatformIO binaries into the Web Flasher public artifact layout:

```bash
npm run firmware:sync
```

The sync command copies:

- `bootloader.bin`
- `partitions.bin`
- `firmware.bin`

for both `esp32dev_sx1262` and `esp32dev_sx127x`, then updates each target
manifest with real `bytes`, `sha256`, and `generated_at` values.

The current flasher UI includes target selection, firmware selection, release
and target manifest loading, placeholder-artifact preflight, ESP chip detection
through `esptool-js`, and a serial monitor/log surface.

Real ESP32 flashing is wired through `esptool-js`. The flash button is enabled
only when the target manifest points to real `.bin` files with non-placeholder
checksums and byte sizes.

The configuration console includes a live Web Serial transport path backed by
the firmware `meshecho-config-v1` command protocol:

- `Connect Serial` opens `navigator.serial.requestPort()`.
- Command buttons send `version`, `show`, `get config`, `save`, and `reboot`.
- Form writes generate `set <field> <value>` commands and then `save`.
- Serial output is streamed into the raw console.

The web client also includes BLE UART and WiFi HTTP command clients:

- BLE uses Nordic UART Service UUIDs and the same text/JSON-line command
  surface once firmware exposes the service.
- WiFi sends `POST /api/config` with `{ "cmd": "..." }` to a MeshEcho SoftAP or
  LAN endpoint. Browser pages cannot use raw UDP directly.
