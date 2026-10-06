import { createHash } from 'node:crypto';
import { mkdir, readFile, stat, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { copyFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(scriptDir, '..');
const repoRoot = resolve(webRoot, '..', '..');
const firmwareBuildRoot = resolve(repoRoot, 'firmware', 'esp32_smart_calm', '.pio', 'build');
const publicFirmwareRoot = resolve(webRoot, 'public', 'firmware');

const targets = [
  {
    id: 'esp32dev_sx1262',
    files: [
      { name: 'bootloader', source: 'bootloader.bin', output: 'bootloader.bin', offset: '0x1000' },
      { name: 'partitions', source: 'partitions.bin', output: 'partitions.bin', offset: '0x8000' },
      { name: 'firmware', source: 'firmware.bin', output: 'firmware.bin', offset: '0x10000' }
    ]
  },
  {
    id: 'esp32dev_sx127x',
    files: [
      { name: 'bootloader', source: 'bootloader.bin', output: 'bootloader.bin', offset: '0x1000' },
      { name: 'partitions', source: 'partitions.bin', output: 'partitions.bin', offset: '0x8000' },
      { name: 'firmware', source: 'firmware.bin', output: 'firmware.bin', offset: '0x10000' }
    ]
  }
];

let missing = 0;

for (const target of targets) {
  const sourceDir = resolve(firmwareBuildRoot, target.id);
  const outputDir = resolve(publicFirmwareRoot, target.id);
  const manifestPath = resolve(outputDir, `firmware-${target.id}-v2.me.json`);
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  const updatedFiles = [];

  await mkdir(outputDir, { recursive: true });

  for (const file of target.files) {
    const sourcePath = resolve(sourceDir, file.source);
    const outputPath = resolve(outputDir, file.output);

    try {
      await stat(sourcePath);
    } catch {
      console.error(`Missing ${sourcePath}. Run: pio run -d firmware/esp32_smart_calm -e ${target.id}`);
      missing += 1;
      continue;
    }

    await copyFile(sourcePath, outputPath);
    const bytes = await readFile(outputPath);
    updatedFiles.push({
      name: file.name,
      offset: file.offset,
      url: `/firmware/${target.id}/${file.output}`,
      sha256: createHash('sha256').update(bytes).digest('hex'),
      bytes: bytes.byteLength
    });
  }

  if (updatedFiles.length !== target.files.length) {
    continue;
  }

  manifest.files = updatedFiles;
  manifest.generated_at = new Date().toISOString();
  await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  console.log(`Updated ${manifestPath}`);
}

if (missing > 0) {
  process.exit(1);
}
