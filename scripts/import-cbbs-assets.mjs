import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { promisify } from 'node:util';
import { execFile as execFileCallback } from 'node:child_process';

const execFile = promisify(execFileCallback);
const root = fileURLToPath(new URL('..', import.meta.url));
const repo = 'cyberpivots/ClaRTK-MeshBBS';

const assets = [
  {
    label: 'CBBS primary logo',
    sourcePath: 'branding/logo/svg/logo-primary.svg',
    destination: 'public/assets/brand/logo-primary.svg',
    status: 'approved-public'
  },
  {
    label: 'CBBS reversed logo',
    sourcePath: 'branding/logo/svg/logo-reversed.svg',
    destination: 'public/assets/brand/logo-reversed.svg',
    status: 'approved-public'
  },
  {
    label: 'CBBS icon logo',
    sourcePath: 'branding/logo/svg/logo-icon.svg',
    destination: 'public/assets/brand/logo-icon.svg',
    status: 'approved-public'
  },
  {
    label: 'CBBS wordmark',
    sourcePath: 'branding/logo/svg/logo-wordmark.svg',
    destination: 'public/assets/brand/logo-wordmark.svg',
    status: 'approved-public'
  },
  {
    label: 'Current dashboard screenshot',
    sourcePath: 'javascript/field/stakeholder-deck/public/assets/img/current-dashboard.png',
    destination: 'src/assets/cbbs/current-dashboard.png',
    status: 'approved-public-current'
  },
  {
    label: 'Current hub monitor screenshot',
    sourcePath: 'javascript/field/stakeholder-deck/public/assets/img/current-hub-monitor.png',
    destination: 'src/assets/cbbs/current-hub-monitor.png',
    status: 'approved-public-current'
  },
  {
    label: 'Current node UI screenshot',
    sourcePath: 'javascript/field/stakeholder-deck/public/assets/img/current-node.png',
    destination: 'src/assets/cbbs/current-node.png',
    status: 'approved-public-current'
  },
  {
    label: 'Current Windows command deck screenshot',
    sourcePath: 'javascript/field/stakeholder-deck/public/assets/img/current-windows-command-deck.png',
    destination: 'src/assets/cbbs/current-windows-command-deck.png',
    status: 'approved-public-current'
  },
  {
    label: 'Current Windows Device Lab screenshot',
    sourcePath: 'javascript/field/stakeholder-deck/public/assets/img/current-windows-device-lab.png',
    destination: 'src/assets/cbbs/current-windows-device-lab.png',
    status: 'approved-public-current'
  },
  {
    label: 'Current Windows Image Build Queue screenshot',
    sourcePath: 'javascript/field/stakeholder-deck/public/assets/img/current-windows-build-queue.png',
    destination: 'src/assets/cbbs/current-windows-build-queue.png',
    status: 'approved-public-current'
  },
  {
    label: 'P800 splash contact sheet',
    sourcePath: 'branding/nextion/animations/splash-v1/p800/cbbs-splash-p800-contact-sheet.png',
    destination: 'src/assets/cbbs/cbbs-splash-p800-contact-sheet.png',
    status: 'approved-public-prototype'
  }
];

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
  const metadata = await fetchMetadata(asset.sourcePath);
  const raw = await fetchRaw(asset.sourcePath);
  const destination = join(root, asset.destination);

  await mkdir(dirname(destination), { recursive: true });
  await writeFile(destination, raw);
  manifest.push({ ...asset, ...metadata });
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
