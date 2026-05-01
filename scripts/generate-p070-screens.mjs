import { createHash } from 'node:crypto';
import { mkdir, readFile, stat, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const root = fileURLToPath(new URL('..', import.meta.url));
const outDir = join(root, 'src/assets/cbbs');
const manifestPath = join(root, 'src/data/cbbs-assets.json');

function escape(value) {
  return String(value)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function text(x, y, value, options = {}) {
  const {
    size = 18,
    fill = '#dbeafe',
    weight = 600,
    family = 'Inter, Segoe UI, Arial, sans-serif',
    anchor = 'start'
  } = options;
  return `<text x="${x}" y="${y}" fill="${fill}" font-family="${family}" font-size="${size}" font-weight="${weight}" text-anchor="${anchor}">${escape(value)}</text>`;
}

function rect(x, y, width, height, options = {}) {
  const {
    fill = '#0b1726',
    stroke = '#1f4e62',
    strokeWidth = 1,
    radius = 6,
    opacity = 1
  } = options;
  return `<rect x="${x}" y="${y}" width="${width}" height="${height}" rx="${radius}" fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}" opacity="${opacity}"/>`;
}

function line(x1, y1, x2, y2, options = {}) {
  const { stroke = '#1f4e62', strokeWidth = 1, opacity = 1 } = options;
  return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="${strokeWidth}" opacity="${opacity}"/>`;
}

function dot(cx, cy, fill = '#22c55e') {
  return `<circle cx="${cx}" cy="${cy}" r="5" fill="${fill}"/>`;
}

function button(x, y, width, label, options = {}) {
  const { fill = '#10283a', stroke = '#2dd4bf', textFill = '#dffefb' } = options;
  return [
    rect(x, y, width, 34, { fill, stroke, radius: 6 }),
    text(x + width / 2, y + 22, label, {
      size: 13,
      fill: textFill,
      weight: 800,
      anchor: 'middle'
    })
  ].join('');
}

function topBar(title, status = 'LINK READY') {
  return [
    rect(0, 0, 800, 48, { fill: '#07111f', stroke: '#07111f', radius: 0 }),
    text(24, 30, title, { size: 18, fill: '#67e8f9', weight: 900 }),
    rect(584, 12, 108, 24, { fill: '#0b2a1c', stroke: '#22c55e', radius: 12 }),
    dot(604, 24),
    text(618, 29, status, { size: 11, fill: '#bbf7d0', weight: 900 }),
    rect(704, 12, 72, 24, { fill: '#1c1917', stroke: '#f59e0b', radius: 12 }),
    text(740, 29, '09:42', { size: 12, fill: '#fde68a', weight: 900, anchor: 'middle' })
  ].join('');
}

function nav(active) {
  const items = ['HOME', 'ROOMS', 'FILES', 'TOOLS', 'LOGS'];
  return items
    .map((item, index) => {
      const x = 28 + index * 150;
      const selected = item === active;
      return [
        rect(x, 430, 118, 34, {
          fill: selected ? '#0891b2' : '#0b1726',
          stroke: selected ? '#67e8f9' : '#1f4e62',
          radius: 5
        }),
        text(x + 59, 452, item, {
          size: 12,
          fill: selected ? '#ecfeff' : '#a7f3d0',
          weight: 900,
          anchor: 'middle'
        })
      ].join('');
    })
    .join('');
}

function screen(content, activeNav) {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="480" viewBox="0 0 800 480">
  <rect width="800" height="480" fill="#06101c"/>
  <path d="M0 48H800M0 424H800" stroke="#12334a" stroke-width="1"/>
  ${content}
  ${nav(activeNav)}
</svg>`;
}

function homeScreen() {
  const content = [
    topBar('CBBS P070 GLOBAL CONTROLLER'),
    rect(24, 70, 240, 152),
    text(44, 100, 'HUB CONNECTION', { size: 13, fill: '#f59e0b', weight: 900 }),
    text(44, 132, 'CBBS-HUB-01', { size: 28, fill: '#f8fafc', weight: 900 }),
    dot(47, 158),
    text(64, 164, 'authenticated / queue active', { size: 13, fill: '#bbf7d0' }),
    text(44, 194, 'Last sync 00:14   RSSI -71 dBm', { size: 13, fill: '#a7f3d0' }),
    rect(24, 238, 240, 164),
    text(44, 268, 'FIELD STATUS', { size: 13, fill: '#f59e0b', weight: 900 }),
    text(44, 302, '12', { size: 42, fill: '#67e8f9', weight: 900 }),
    text(98, 302, 'active nodes', { size: 17, fill: '#e0f2fe', weight: 800 }),
    text(44, 334, '3 pending records', { size: 15, fill: '#dbeafe' }),
    text(44, 362, '0 blocked actions', { size: 15, fill: '#dbeafe' }),
    rect(286, 70, 240, 332),
    text(306, 100, 'NETWORK MAP', { size: 13, fill: '#f59e0b', weight: 900 }),
    line(402, 154, 348, 218, { stroke: '#22d3ee', strokeWidth: 2 }),
    line(402, 154, 472, 220, { stroke: '#22d3ee', strokeWidth: 2 }),
    line(402, 154, 398, 294, { stroke: '#22d3ee', strokeWidth: 2 }),
    '<circle cx="402" cy="154" r="26" fill="#0e7490" stroke="#67e8f9" stroke-width="3"/>',
    text(402, 161, 'HUB', { size: 13, fill: '#ecfeff', weight: 900, anchor: 'middle' }),
    '<circle cx="348" cy="218" r="22" fill="#0f172a" stroke="#22c55e" stroke-width="2"/>',
    text(348, 224, 'N1', { size: 13, fill: '#bbf7d0', weight: 900, anchor: 'middle' }),
    '<circle cx="472" cy="220" r="22" fill="#0f172a" stroke="#22c55e" stroke-width="2"/>',
    text(472, 226, 'N2', { size: 13, fill: '#bbf7d0', weight: 900, anchor: 'middle' }),
    '<circle cx="398" cy="294" r="22" fill="#0f172a" stroke="#f59e0b" stroke-width="2"/>',
    text(398, 300, 'R3', { size: 13, fill: '#fde68a', weight: 900, anchor: 'middle' }),
    text(306, 372, 'LoRa store-and-forward active', { size: 14, fill: '#dbeafe' }),
    rect(548, 70, 228, 332),
    text(568, 100, 'QUICK ACTIONS', { size: 13, fill: '#f59e0b', weight: 900 }),
    button(568, 124, 188, 'DISCOVER NODES'),
    button(568, 170, 188, 'OPEN ROOMS'),
    button(568, 216, 188, 'REVIEW QUEUE'),
    button(568, 262, 188, 'DIAGNOSTICS'),
    text(568, 338, 'Operator mode', { size: 15, fill: '#dbeafe', weight: 800 }),
    rect(568, 354, 188, 28, { fill: '#0b2a1c', stroke: '#22c55e', radius: 14 }),
    text(662, 373, 'LOCAL APPROVAL REQUIRED', {
      size: 11,
      fill: '#bbf7d0',
      weight: 900,
      anchor: 'middle'
    })
  ].join('');
  return screen(content, 'HOME');
}

function roomsScreen() {
  const content = [
    topBar('CBBS P070 ROOM BOARD'),
    rect(22, 66, 190, 336),
    text(42, 96, 'ROOMS', { size: 13, fill: '#f59e0b', weight: 900 }),
    ...['Field Ops', 'Irrigation', 'Weather', 'Diagnostics', 'Trade Board'].flatMap((label, i) => {
      const y = 116 + i * 48;
      const selected = i === 0;
      return [
        rect(42, y, 150, 34, {
          fill: selected ? '#0e7490' : '#0b1726',
          stroke: selected ? '#67e8f9' : '#1f4e62',
          radius: 5
        }),
        text(56, y + 22, label, {
          size: 13,
          fill: selected ? '#ecfeff' : '#dbeafe',
          weight: 800
        })
      ];
    }),
    rect(232, 66, 334, 336),
    text(252, 96, 'FIELD OPS RECORDS', { size: 13, fill: '#f59e0b', weight: 900 }),
    rect(252, 118, 294, 52, { fill: '#0a2430', stroke: '#22d3ee', radius: 5 }),
    text(268, 140, '09:35  Route check complete', { size: 14, fill: '#ecfeff', weight: 800 }),
    text(268, 160, 'Node N2 delivered queue batch 18.', { size: 12, fill: '#bae6fd' }),
    rect(252, 184, 294, 52, { fill: '#101827', stroke: '#1f4e62', radius: 5 }),
    text(268, 206, '09:28  Water team staged', { size: 14, fill: '#ecfeff', weight: 800 }),
    text(268, 226, 'Awaiting hub acknowledgement.', { size: 12, fill: '#bae6fd' }),
    rect(252, 250, 294, 52, { fill: '#101827', stroke: '#1f4e62', radius: 5 }),
    text(268, 272, '09:11  Repair note added', { size: 14, fill: '#ecfeff', weight: 800 }),
    text(268, 292, 'Relay R3 battery swapped.', { size: 12, fill: '#bae6fd' }),
    rect(252, 326, 142, 44, { fill: '#0b2a1c', stroke: '#22c55e', radius: 6 }),
    text(323, 354, 'ACK SELECTED', { size: 12, fill: '#bbf7d0', weight: 900, anchor: 'middle' }),
    rect(404, 326, 142, 44, { fill: '#1c1917', stroke: '#f59e0b', radius: 6 }),
    text(475, 354, 'POST NOTE', { size: 12, fill: '#fde68a', weight: 900, anchor: 'middle' }),
    rect(586, 66, 190, 336),
    text(606, 96, 'QUEUE', { size: 13, fill: '#f59e0b', weight: 900 }),
    text(606, 132, 'Outbound', { size: 13, fill: '#dbeafe', weight: 800 }),
    text(744, 132, '03', { size: 22, fill: '#67e8f9', weight: 900, anchor: 'end' }),
    line(606, 150, 756, 150),
    text(606, 184, 'Inbound', { size: 13, fill: '#dbeafe', weight: 800 }),
    text(744, 184, '07', { size: 22, fill: '#67e8f9', weight: 900, anchor: 'end' }),
    line(606, 202, 756, 202),
    text(606, 236, 'Last relay', { size: 13, fill: '#dbeafe', weight: 800 }),
    text(744, 236, 'R3', { size: 22, fill: '#fde68a', weight: 900, anchor: 'end' }),
    rect(606, 286, 150, 52, { fill: '#0b2a1c', stroke: '#22c55e', radius: 6 }),
    text(681, 317, 'SYNC READY', { size: 13, fill: '#bbf7d0', weight: 900, anchor: 'middle' })
  ].join('');
  return screen(content, 'ROOMS');
}

function filesScreen() {
  const content = [
    topBar('CBBS P070 FILE CONTROL'),
    rect(24, 70, 224, 332),
    text(44, 100, 'LOCAL STORE', { size: 13, fill: '#f59e0b', weight: 900 }),
    text(44, 132, 'microSD archive', { size: 20, fill: '#f8fafc', weight: 900 }),
    text(44, 166, 'Used  1.8 GB', { size: 14, fill: '#dbeafe', weight: 800 }),
    rect(44, 184, 164, 12, { fill: '#0f172a', stroke: '#1f4e62', radius: 6 }),
    rect(44, 184, 96, 12, { fill: '#22d3ee', stroke: '#22d3ee', radius: 6 }),
    text(44, 232, 'Ready packages', { size: 14, fill: '#dbeafe', weight: 800 }),
    text(214, 232, '05', { size: 24, fill: '#67e8f9', weight: 900, anchor: 'end' }),
    text(44, 270, 'Held for review', { size: 14, fill: '#dbeafe', weight: 800 }),
    text(214, 270, '02', { size: 24, fill: '#fde68a', weight: 900, anchor: 'end' }),
    button(44, 326, 164, 'MOUNT STORE'),
    rect(270, 70, 282, 332),
    text(290, 100, 'PACKAGE LIST', { size: 13, fill: '#f59e0b', weight: 900 }),
    ...[
      ['ops-brief-0940.txt', '2 KB', '#22c55e'],
      ['weather-bulletin.bin', '6 KB', '#22c55e'],
      ['field-log-n2.csv', '14 KB', '#22c55e'],
      ['display-theme.p070', '48 KB', '#f59e0b'],
      ['gateway-report.json', '9 KB', '#22c55e']
    ].flatMap(([name, size, color], i) => {
      const y = 122 + i * 48;
      return [
        rect(290, y, 242, 34, { fill: '#101827', stroke: '#1f4e62', radius: 5 }),
        dot(306, y + 17, color),
        text(322, y + 21, name, { size: 13, fill: '#ecfeff', weight: 800 }),
        text(518, y + 21, size, { size: 12, fill: '#bae6fd', weight: 800, anchor: 'end' })
      ];
    }),
    button(290, 356, 112, 'SEND'),
    button(420, 356, 112, 'HOLD', { fill: '#1c1917', stroke: '#f59e0b', textFill: '#fde68a' }),
    rect(574, 70, 202, 332),
    text(594, 100, 'TRANSFER', { size: 13, fill: '#f59e0b', weight: 900 }),
    text(594, 136, 'Target node', { size: 13, fill: '#dbeafe', weight: 800 }),
    rect(594, 150, 150, 30, { fill: '#0a2430', stroke: '#22d3ee', radius: 5 }),
    text(669, 170, 'N2 / Field Ops', { size: 12, fill: '#ecfeff', weight: 900, anchor: 'middle' }),
    text(594, 214, 'Window', { size: 13, fill: '#dbeafe', weight: 800 }),
    rect(594, 228, 150, 30, { fill: '#0a2430', stroke: '#22d3ee', radius: 5 }),
    text(669, 248, 'store-forward', { size: 12, fill: '#ecfeff', weight: 900, anchor: 'middle' }),
    rect(594, 292, 150, 48, { fill: '#0b2a1c', stroke: '#22c55e', radius: 6 }),
    text(669, 321, 'QUEUE READY', { size: 13, fill: '#bbf7d0', weight: 900, anchor: 'middle' })
  ].join('');
  return screen(content, 'FILES');
}

const screens = [
  {
    filename: 'p070-home.png',
    label: 'P070 global controller home generated screen',
    sourcePath: 'scripts/generate-p070-screens.mjs#homeScreen',
    svg: homeScreen()
  },
  {
    filename: 'p070-rooms.png',
    label: 'P070 room board generated screen',
    sourcePath: 'scripts/generate-p070-screens.mjs#roomsScreen',
    svg: roomsScreen()
  },
  {
    filename: 'p070-files.png',
    label: 'P070 file control generated screen',
    sourcePath: 'scripts/generate-p070-screens.mjs#filesScreen',
    svg: filesScreen()
  }
];

await mkdir(outDir, { recursive: true });

for (const screenDef of screens) {
  await sharp(Buffer.from(screenDef.svg)).png().toFile(join(outDir, screenDef.filename));
}

let manifest = { assets: [] };
try {
  manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
} catch {
  await mkdir(dirname(manifestPath), { recursive: true });
}

const destinations = new Set(
  screens.map((screenDef) => `src/assets/cbbs/${screenDef.filename}`)
);
const generatedEntries = await Promise.all(
  screens.map(async (screenDef) => {
    const destination = `src/assets/cbbs/${screenDef.filename}`;
    const filePath = join(root, destination);
    const data = await readFile(filePath);
    const fileStat = await stat(filePath);
    return {
      label: screenDef.label,
      sourcePath: screenDef.sourcePath,
      destination,
      status: 'approved-public-prototype',
      sha256: createHash('sha256').update(data).digest('hex'),
      size: fileStat.size,
      generatedBy: 'scripts/generate-p070-screens.mjs'
    };
  })
);

const retainedEntries = Array.isArray(manifest.assets)
  ? manifest.assets.filter((entry) => !destinations.has(entry.destination))
  : [];

await writeFile(
  manifestPath,
  `${JSON.stringify({ assets: [...retainedEntries, ...generatedEntries] }, null, 2)}\n`
);

console.log(`Generated ${screens.length} clean P070 screen captures.`);
