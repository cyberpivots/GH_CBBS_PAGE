import { existsSync, readdirSync, statSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const distRoot = join(root, 'dist');
const basePath = '/GH_CBBS_PAGE/';
const attributePattern = /\s(?:href|src)=["']([^"']+)["']/gi;

function walk(dir) {
  const files = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...walk(fullPath));
    } else if (entry.isFile() && entry.name.endsWith('.html')) {
      files.push(fullPath);
    }
  }
  return files;
}

function stripUrl(value) {
  return value.split('#')[0].split('?')[0];
}

function isExternal(value) {
  return /^(?:[a-z][a-z0-9+.-]*:|\/\/)/i.test(value);
}

function targetForPath(value) {
  const clean = stripUrl(value);
  if (clean === '' || isExternal(clean)) {
    return null;
  }

  if (!clean.startsWith(basePath)) {
    if (clean.startsWith('/')) {
      return { error: `absolute path does not include configured base ${basePath}` };
    }
    return null;
  }

  const relativeTarget = clean.slice(basePath.length);
  const target = join(distRoot, relativeTarget);

  if (clean.endsWith('/')) {
    return { path: join(target, 'index.html') };
  }

  if (!/\.[a-z0-9]+$/i.test(relativeTarget)) {
    return { path: join(target, 'index.html') };
  }

  return { path: target };
}

if (!existsSync(distRoot)) {
  console.error('Missing dist directory. Run pnpm build before check:links.');
  process.exit(1);
}

const failures = [];
const htmlFiles = walk(distRoot);

for (const file of htmlFiles) {
  const html = await readFile(file, 'utf8');
  const displayPath = relative(root, file);
  let match;

  while ((match = attributePattern.exec(html)) !== null) {
    const target = targetForPath(match[1]);
    if (!target) {
      continue;
    }

    if (target.error) {
      failures.push(`${displayPath}: ${match[1]} ${target.error}.`);
      continue;
    }

    if (!existsSync(target.path)) {
      failures.push(`${displayPath}: ${match[1]} does not resolve to ${relative(root, target.path)}.`);
      continue;
    }

    if (statSync(target.path).isDirectory()) {
      failures.push(`${displayPath}: ${match[1]} resolves to a directory, not a file.`);
    }
  }
}

if (failures.length > 0) {
  console.error('Link check failed:');
  for (const failure of failures) {
    console.error(`- ${failure}`);
  }
  process.exit(1);
}

console.log(`Link check passed for ${htmlFiles.length} HTML files.`);

