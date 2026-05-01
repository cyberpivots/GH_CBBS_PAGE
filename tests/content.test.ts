import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { navigation, SITE } from '../src/data/site';

const contentRoot = join(process.cwd(), 'src', 'content');

function walkMarkdown(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory()) {
      return walkMarkdown(fullPath);
    }
    return entry.isFile() && entry.name.endsWith('.md') ? [fullPath] : [];
  });
}

describe('site metadata', () => {
  it('uses the GitHub Pages project base path', () => {
    expect(SITE.repositoryBase).toBe('/GH_CBBS_PAGE');
  });

  it('has unique navigation hrefs', () => {
    const hrefs = navigation.map((item) => item.href);
    expect(new Set(hrefs).size).toBe(hrefs.length);
  });
});

describe('content files', () => {
  it('include frontmatter and source status fields', () => {
    const files = walkMarkdown(contentRoot);
    expect(files.length).toBeGreaterThan(0);

    for (const file of files) {
      expect(statSync(file).isFile()).toBe(true);
      const text = readFileSync(file, 'utf8');
      expect(text).toMatch(/^---\n[\s\S]*?\n---/);
      expect(text).toContain('publicationStatus:');
      expect(text).toContain('sourceStatus:');
      expect(text).toContain('sourceRefs:');
    }
  });
});

