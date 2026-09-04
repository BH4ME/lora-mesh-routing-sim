import { ESPLoader, Transport, type FlashOptions, type IEspLoaderTerminal } from 'esptool-js';

export interface ReleaseManifestTarget {
  id: string;
  chip: string;
  radio: string;
  display_name: string;
  manifest_url: string;
  support?: string;
}

export interface ReleaseManifest {
  project: string;
  version: string;
  released_at: string;
  schema: string;
  targets: ReleaseManifestTarget[];
}

export interface TargetManifestFile {
  name: string;
  offset: string;
  url: string;
  sha256: string;
  bytes: number;
}

export interface TargetManifest {
  project: string;
  schema: string;
  version: string;
  target: string;
  platformio_target?: string;
  chip: string;
  radio: string;
  flash_mode: 'esptool-js' | 'uf2-dfu';
  support?: string;
  files: TargetManifestFile[];
  notes?: string[];
}

export interface SerialSession {
  port: SerialPort;
  close: () => Promise<void>;
  sendLine: (line: string) => Promise<void>;
}

export interface BleSession {
  close: () => Promise<void>;
  sendLine: (line: string) => Promise<void>;
}

export const hasWebBluetooth = () => typeof navigator !== 'undefined' && 'bluetooth' in navigator;
export const hasWebSerial = () => typeof navigator !== 'undefined' && 'serial' in navigator;

export async function loadReleaseManifest(path = '/firmware/firmware-v2.json'): Promise<ReleaseManifest> {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error(`Could not load release manifest: ${response.status}`);
  }
  return (await response.json()) as ReleaseManifest;
}

export async function loadTargetManifest(manifestUrl: string): Promise<TargetManifest> {
  const response = await fetch(manifestUrl);
  if (!response.ok) {
    throw new Error(`Could not load target manifest: ${response.status}`);
  }
  return (await response.json()) as TargetManifest;
}

export async function openSerialConsole(onData: (text: string) => void, baudRate = 115200): Promise<SerialSession> {
  if (!hasWebSerial()) {
    throw new Error('Web Serial is not available in this browser.');
  }

  const port = await navigator.serial.requestPort();
  await port.open({ baudRate });

  const encoder = new TextEncoder();
  const decoder = new TextDecoder();
  let keepReading = true;
  const reader = port.readable?.getReader();
  const writer = port.writable?.getWriter();

  if (!reader || !writer) {
    await port.close();
    throw new Error('Serial port streams are unavailable.');
  }

  void (async () => {
    try {
      while (keepReading) {
        const { value, done } = await reader.read();
        if (done) break;
        if (value) onData(decoder.decode(value, { stream: true }));
      }
    } catch (error) {
      onData(`\n[MeshEcho Web] serial read stopped: ${formatError(error)}\n`);
    }
  })();

  return {
    port,
    sendLine: async (line: string) => {
      await writer.write(encoder.encode(`${line.trim()}\n`));
    },
    close: async () => {
      keepReading = false;
      try {
        await reader.cancel();
      } catch {
        // Ignore cancellation races.
      }
      reader.releaseLock();
      writer.releaseLock();
      await port.close();
    }
  };
}

export async function openBleUartConsole(onData: (text: string) => void): Promise<BleSession> {
  if (!hasWebBluetooth()) {
    throw new Error('Web Bluetooth is not available in this browser.');
  }

  const nusService = '6e400001-b5a3-f393-e0a9-e50e24dcca9e';
  const nusRx = '6e400002-b5a3-f393-e0a9-e50e24dcca9e';
  const nusTx = '6e400003-b5a3-f393-e0a9-e50e24dcca9e';
  const device = await navigator.bluetooth.requestDevice({
    filters: [{ namePrefix: 'MeshEcho' }],
    optionalServices: [nusService]
  });
  const server = await device.gatt?.connect();
  if (!server) {
    throw new Error('BLE GATT server is unavailable.');
  }
  const service = await server.getPrimaryService(nusService);
  const rx = await service.getCharacteristic(nusRx);
  const tx = await service.getCharacteristic(nusTx);
  const decoder = new TextDecoder();
  const encoder = new TextEncoder();
  const onCharacteristic = (event: Event) => {
    const characteristic = event.target as BluetoothRemoteGATTCharacteristic;
    if (characteristic.value) {
      onData(decoder.decode(characteristic.value));
    }
  };
  tx.addEventListener('characteristicvaluechanged', onCharacteristic);
  await tx.startNotifications();

  return {
    sendLine: async (line: string) => {
      await rx.writeValue(encoder.encode(`${line.trim()}\n`));
    },
    close: async () => {
      try {
        await tx.stopNotifications();
      } catch {
        // Ignore disconnect races.
      }
      tx.removeEventListener('characteristicvaluechanged', onCharacteristic);
      device.gatt?.disconnect();
    }
  };
}

export async function sendWifiConfigCommand(baseUrl: string, line: string): Promise<string> {
  const normalizedBase = baseUrl.trim().replace(/\/+$/, '');
  if (!normalizedBase) {
    throw new Error('Enter a MeshEcho HTTP endpoint first.');
  }
  const response = await fetch(`${normalizedBase}/api/config`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ cmd: line.trim() })
  });
  const text = await response.text();
  if (!response.ok) {
    throw new Error(text || `WiFi endpoint returned ${response.status}`);
  }
  return text;
}

export async function detectEspChip(onLog: (line: string) => void, baudRate = 115200): Promise<string> {
  if (!hasWebSerial()) {
    throw new Error('Web Serial is not available in this browser.');
  }

  const port = await navigator.serial.requestPort();
  const transport = new Transport(port, true);
  const loader = new ESPLoader({
    transport,
    baudrate: baudRate,
    terminal: makeTerminal(onLog),
    debugLogging: false
  });

  try {
    const chipName = await loader.main();
    onLog(`[MeshEcho Web] detected ${chipName}`);
    return chipName;
  } finally {
    await transport.disconnect();
  }
}

export async function flashEspTarget(
  manifest: TargetManifest,
  eraseAll: boolean,
  onLog: (line: string) => void,
  onProgress: (percent: number) => void,
  baudRate = 115200
): Promise<void> {
  if (!hasWebSerial()) {
    throw new Error('Web Serial is not available in this browser.');
  }
  if (manifest.flash_mode !== 'esptool-js') {
    throw new Error(`Target ${manifest.target} is not an ESP Web Serial target.`);
  }
  if (manifest.files.length === 0 || manifest.files.some((file) => file.bytes <= 0 || file.sha256.includes('placeholder'))) {
    throw new Error('Firmware artifacts are placeholders. Publish real .bin files and checksums before flashing.');
  }

  const port = await navigator.serial.requestPort();
  const transport = new Transport(port, true);
  const loader = new ESPLoader({
    transport,
    baudrate: baudRate,
    terminal: makeTerminal(onLog),
    debugLogging: false
  });

  try {
    const chipName = await loader.main();
    onLog(`[MeshEcho Web] connected to ${chipName}`);

    const fileArray = await Promise.all(
      manifest.files.map(async (file) => {
        const response = await fetch(file.url);
        if (!response.ok) {
          throw new Error(`Could not download ${file.name}: ${response.status}`);
        }
        return {
          address: Number.parseInt(file.offset, 16),
          data: new Uint8Array(await response.arrayBuffer())
        };
      })
    );

    const options: FlashOptions = {
      fileArray,
      flashMode: 'dio',
      flashFreq: '40m',
      flashSize: '4MB',
      eraseAll,
      compress: true,
      reportProgress: (_fileIndex, written, total) => {
        onProgress(Math.round((written / total) * 100));
      }
    };

    await loader.writeFlash(options);
    await loader.after('hard_reset');
    onProgress(100);
    onLog('[MeshEcho Web] flash complete; device reset requested.');
  } finally {
    await transport.disconnect();
  }
}

export function formatError(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function makeTerminal(onLog: (line: string) => void): IEspLoaderTerminal {
  return {
    clean: () => undefined,
    writeLine: (data: string) => onLog(data),
    write: (data: string) => onLog(data)
  };
}
