import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const publicationStatus = z.enum(['published', 'draft']);
const sourceStatus = z.enum(['approved-public', 'internal-review']);
const truthState = z.enum([
  'current',
  'proof-simulator',
  'mock-scenario',
  'projected',
  'internal-review'
]);

const sourcedContent = z.object({
  title: z.string().min(3),
  summary: z.string().min(20),
  publicationStatus: publicationStatus.default('draft'),
  sourceStatus: sourceStatus.default('internal-review'),
  sourceRefs: z.array(z.string()).default([]),
  order: z.number().int().nonnegative().optional(),
  updatedDate: z.coerce.date().optional()
});

const pages = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/pages' }),
  schema: sourcedContent
});

const updates = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/updates' }),
  schema: sourcedContent.extend({
    pubDate: z.coerce.date()
  })
});

const resources = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/resources' }),
  schema: sourcedContent.extend({
    audience: z.enum(['public', 'contributors', 'agents']).default('public')
  })
});

const faqs = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/faqs' }),
  schema: sourcedContent
});

const productContent = sourcedContent.extend({
  truthState,
  tags: z.array(z.string()).default([]),
  evidenceLabel: z.string().optional(),
  boundary: z.string().optional()
});

const systems = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/systems' }),
  schema: productContent.extend({
    role: z.string(),
    surface: z.string().optional(),
    capabilities: z.array(z.string()).default([])
  })
});

const useCases = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/use-cases' }),
  schema: productContent.extend({
    problem: z.string(),
    cbbsFit: z.string()
  })
});

const workflows = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/workflows' }),
  schema: productContent.extend({
    scenarioType: z.enum(['operator', 'field', 'agriculture', 'emergency', 'diagnostics']),
    steps: z.array(z.string()).min(2)
  })
});

const media = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/media' }),
  schema: productContent.extend({
    image: z.string(),
    alt: z.string().min(20),
    caption: z.string().min(20),
    assetType: z.enum(['screenshot', 'prototype-capture', 'contact-sheet', 'logo']),
    assetSourceStatus: z.enum([
      'approved-public',
      'approved-public-current',
      'approved-public-prototype'
    ]),
    sourcePath: z.string()
  })
});

export const collections = {
  pages,
  updates,
  resources,
  faqs,
  systems,
  useCases,
  workflows,
  media
};
