import type { CollectionEntry } from 'astro:content';

type PublicCollection =
  | 'pages'
  | 'updates'
  | 'resources'
  | 'faqs'
  | 'systems'
  | 'useCases'
  | 'workflows'
  | 'media';

export type PublicEntry = CollectionEntry<PublicCollection>;

export function isPublished<T extends PublicEntry>(entry: T): boolean {
  return (
    entry.data.publicationStatus === 'published' &&
    entry.data.sourceStatus === 'approved-public'
  );
}

export function slugForEntry(entry: { id: string }): string {
  return entry.id.replace(/(?:\/index)?\.mdx?$/i, '').replace(/\.md$/i, '');
}

export function sortByOrderThenTitle<T extends PublicEntry>(entries: T[]): T[] {
  return [...entries].sort((a, b) => {
    const orderA = a.data.order ?? Number.MAX_SAFE_INTEGER;
    const orderB = b.data.order ?? Number.MAX_SAFE_INTEGER;

    if (orderA !== orderB) {
      return orderA - orderB;
    }

    return a.data.title.localeCompare(b.data.title);
  });
}

export function truthStateLabel(value: string): string {
  const labels: Record<string, string> = {
    current: 'Current system',
    'proof-simulator': 'Prototype display',
    'mock-scenario': 'Example scenario',
    projected: 'Roadmap',
    'internal-review': 'Internal review'
  };

  return labels[value] ?? value;
}

export function sortUpdatesNewestFirst(
  entries: CollectionEntry<'updates'>[]
): CollectionEntry<'updates'>[] {
  return [...entries].sort(
    (a, b) => b.data.pubDate.getTime() - a.data.pubDate.getTime()
  );
}
