import { readFile } from 'node:fs/promises';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { readdirSync, statSync } from 'node:fs';

const root = fileURLToPath(new URL('..', import.meta.url));
const contentRoot = join(root, 'src', 'content');
const sourcesPath = join(root, 'docs', 'verified-sources.md');
const publicSafetyPaths = [sourcesPath, join(root, 'src', 'data', 'cbbs-assets.json')];
const privateDevelopmentReferencePattern =
  /github\.com\/cyberpivots\/(?!GH_CBBS_PAGE(?:[\s/#?)]|$))|cyberpivots\/[^`\s]+:/i;
const productContentPattern = /src\/content\/(?:systems|use-cases|workflows|media)\//;
const allowedTruthStates = new Set([
  'current',
  'proof-simulator',
  'mock-scenario',
  'projected',
  'internal-review'
]);
const prohibitedPublicClaims = [
  /autonomous irrigation control/i,
  /live relay switching/i,
  /live valve control/i,
  /live pump execution/i,
  /cloud-required loop/i
];

function walk(dir) {
  const entries = readdirSync(dir, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...walk(fullPath));
    } else if (entry.isFile() && /\.mdx?$/i.test(entry.name)) {
      files.push(fullPath);
    }
  }

  return files;
}

function parseFrontmatter(text) {
  const match = /^---\n([\s\S]*?)\n---/.exec(text);
  if (!match) {
    return {};
  }

  const raw = match[1];
  const data = {};
  const lines = raw.split('\n');

  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const pair = /^([A-Za-z0-9_-]+):\s*(.*)$/.exec(line);
    if (!pair) {
      continue;
    }

    const [, key, value] = pair;
    if (value === '') {
      const values = [];
      let next = index + 1;
      while (next < lines.length && /^\s+-\s+/.test(lines[next])) {
        values.push(lines[next].replace(/^\s+-\s+/, '').replace(/^["']|["']$/g, ''));
        next += 1;
      }
      data[key] = values;
      index = next - 1;
    } else {
      data[key] = value.replace(/^["']|["']$/g, '');
    }
  }

  return data;
}

function approvedSourceNames(sourceRegister) {
  const names = new Set();
  const sourceBlocks = sourceRegister.split(/^### /m).slice(1);

  for (const block of sourceBlocks) {
    const [heading, ...rest] = block.split('\n');
    const body = rest.join('\n');
    if (/^- Status:\s*`approved-public`/m.test(body)) {
      names.add(heading.trim());
    }
  }

  return names;
}

const sourceRegister = await readFile(sourcesPath, 'utf8');
const approvedSources = approvedSourceNames(sourceRegister);
const failures = [];

if (!statSync(contentRoot).isDirectory()) {
  failures.push('Missing src/content directory.');
}

for (const file of walk(contentRoot)) {
  const text = await readFile(file, 'utf8');
  const data = parseFrontmatter(text);
  const displayPath = relative(root, file);

  if (privateDevelopmentReferencePattern.test(text)) {
    failures.push(`${displayPath}: content references a private development repository or private source path.`);
  }

  if (/AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/u.test(text)) {
    failures.push(`${displayPath}: content appears to contain a credential or private key.`);
  }

  if (data.publicationStatus === 'published') {
    if (data.sourceStatus !== 'approved-public') {
      failures.push(`${displayPath}: published content must use sourceStatus approved-public.`);
    }

    if (!Array.isArray(data.sourceRefs) || data.sourceRefs.length === 0) {
      failures.push(`${displayPath}: published content must list sourceRefs.`);
    } else {
      for (const sourceRef of data.sourceRefs) {
        if (!approvedSources.has(sourceRef)) {
          failures.push(`${displayPath}: sourceRef "${sourceRef}" is not approved in docs/verified-sources.md.`);
        }
      }
    }

    if (productContentPattern.test(displayPath)) {
      if (!allowedTruthStates.has(data.truthState)) {
        failures.push(`${displayPath}: product content must include a valid truthState.`);
      }

      if (data.truthState === 'internal-review') {
        failures.push(`${displayPath}: internal-review product content cannot be published.`);
      }

      for (const claim of prohibitedPublicClaims) {
        if (claim.test(text)) {
          failures.push(`${displayPath}: content contains a prohibited public capability claim (${claim}).`);
        }
      }
    }
  }
}

for (const file of publicSafetyPaths) {
  const text = await readFile(file, 'utf8');
  const displayPath = relative(root, file);

  if (privateDevelopmentReferencePattern.test(text)) {
    failures.push(`${displayPath}: public source metadata references a private development repository or private source path.`);
  }
}

if (failures.length > 0) {
  console.error('Publication check failed:');
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log(`Publication check passed for ${walk(contentRoot).length} content files.`);
