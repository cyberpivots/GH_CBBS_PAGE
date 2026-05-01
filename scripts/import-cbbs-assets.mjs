import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { execFile as execFileCallback } from 'node:child_process';

const execFile = promisify(execFileCallback);
const root = fileURLToPath(new URL('..', import.meta.url));
const repo = process.env.CBBS_ASSET_SOURCE_REPO;

const assets = [
  {
    sourceKey: 'brand-primary-logo',
    label: 'CBBS primary logo',
    destination: 'public/assets/brand/logo-primary.svg',
    status: 'approved-public'
  },
  {
    sourceKey: 'brand-reversed-logo',
    label: 'CBBS reversed logo',
    destination: 'public/assets/brand/logo-reversed.svg',
    status: 'approved-public'
  },
  {
    sourceKey: 'brand-icon-logo',
    label: 'CBBS icon logo',
    destination: 'public/assets/brand/logo-icon.svg',
    status: 'approved-public'
  },
  {
    sourceKey: 'brand-wordmark',
    label: 'CBBS wordmark',
    destination: 'public/assets/brand/logo-wordmark.svg',
    status: 'approved-public'
  },
  {
    sourceKey: 'current-dashboard',
    label: 'Current dashboard screenshot',
    destination: 'src/assets/cbbs/current-dashboard.png',
    status: 'approved-public-current'
  },
  {
    sourceKey: 'current-hub-monitor',
    label: 'Current hub monitor screenshot',
    destination: 'src/assets/cbbs/current-hub-monitor.png',
    status: 'approved-public-current'
  },
  {
    sourceKey: 'current-node-ui',
    label: 'Current node UI screenshot',
    destination: 'src/assets/cbbs/current-node.png',
    status: 'approved-public-current'
  },
  {
    sourceKey: 'current-windows-command-deck',
    label: 'Current Windows command deck screenshot',
    destination: 'src/assets/cbbs/current-windows-command-deck.png',
    status: 'approved-public-current'
  },
  {
    sourceKey: 'current-windows-device-lab',
    label: 'Current Windows Device Lab screenshot',
    destination: 'src/assets/cbbs/current-windows-device-lab.png',
    status: 'approved-public-current'
  },
  {
    sourceKey: 'current-windows-build-queue',
    label: 'Current Windows Image Build Queue screenshot',
    destination: 'src/assets/cbbs/current-windows-build-queue.png',
    status: 'approved-public-current'
  },
  {
    sourceKey: 'p800-splash-contact-sheet',
    label: 'P800 splash contact sheet',
    destination: 'src/assets/cbbs/cbbs-splash-p800-contact-sheet.png',
    status: 'approved-public-prototype'
  }
];

const sourceMapPath = process.env.CBBS_ASSET_SOURCE_MAP;

if (!repo || !sourceMapPath) {
  console.error(
    'Set CBBS_ASSET_SOURCE_REPO and CBBS_ASSET_SOURCE_MAP to import approved private-source assets.'
  );
  console.error(
    'The source map must be an untracked JSON object keyed by sourceKey with private repository paths as values.'
  );
  process.exit(1);
}

const sourceMap = JSON.parse(await readFile(sourceMapPath, 'utf8'));

async function gh(args, options = {}) {
  const { stdout } = await execFile('gh', args, {
    cwd: root,
    encoding: options.encoding ?? 'utf8',
    maxBuffer: 20 * 1024 * 1024
  });
  return stdout;
}

async function fetchMetadata(sourcePath) {
  const stdout = await gh(['api', `repos/${repo}/contents/${sourcePath}`]);
  const metadata = JSON.parse(stdout);
  return {
    sha: metadata.sha,
    size: metadata.size,
    sourceRepo: repo,
    sourcePath
  };
}

async function fetchRaw(sourcePath) {
  return gh(
    [
      'api',
      `repos/${repo}/contents/${sourcePath}`,
      '-H',
      'Accept: application/vnd.github.raw'
    ],
    { encoding: 'buffer' }
  );
}

const manifest = [];
const manifestPath = join(root, 'src/data/cbbs-assets.json');

for (const asset of assets) {
  const sourcePath = sourceMap[asset.sourceKey];

  if (!sourcePath) {
    throw new Error(`Missing source path for ${asset.sourceKey} in ${sourceMapPath}.`);
  }

  const metadata = await fetchMetadata(sourcePath);
  const raw = await fetchRaw(sourcePath);
  const destination = join(root, asset.destination);

  await mkdir(dirname(destination), { recursive: true });
  await writeFile(destination, raw);
  manifest.push({
    ...asset,
    ...metadata,
    sourcePath: `approved-private-source:${asset.sourceKey}`,
    sourceRepo: 'approved-private-source-review'
  });
  console.log(`Imported ${asset.label} -> ${asset.destination}`);
}

let preservedGeneratedAssets = [];
try {
  const existingManifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  preservedGeneratedAssets = Array.isArray(existingManifest.assets)
    ? existingManifest.assets.filter((entry) =>
        String(entry.generatedBy || '').endsWith('generate-p070-screens.mjs')
      )
    : [];
} catch {
  preservedGeneratedAssets = [];
}

await writeFile(
  manifestPath,
  `${JSON.stringify({ assets: [...manifest, ...preservedGeneratedAssets] }, null, 2)}\n`
);

console.log(`Imported ${manifest.length} CBBS public-site assets.`);
