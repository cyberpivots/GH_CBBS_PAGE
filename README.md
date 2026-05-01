# CBBS Public Site

Static GitHub Pages site for public CBBS promotional material and project updates.

The related development repository is private. This repository is the public-facing publication workspace, so content must be sourced, reviewed, and safe to publish.

## Stack
- Astro static output
- TypeScript content collections
- GitHub Pages project-site deployment from the `gh-pages` branch
- Pagefind static search index
- Astro sitemap generation
- Optional static PWA shell caching
- Repo-owned CBBS screenshot imports with provenance manifest

## Commands
```bash
pnpm install
node scripts/import-cbbs-assets.mjs
pnpm dev
pnpm check
pnpm test
pnpm build
pnpm test:browser
```

## Public Content Workflow
1. Add or update approved sources in `docs/verified-sources.md`.
2. Add public-facing content under `src/content/**`.
3. Label product material as current, proof/simulator, mock scenario, projected, or internal review.
4. Keep draft, unsourced, or unapproved capability claims out of production pages.
5. Run `pnpm build` before deployment.

## Deployment
GitHub Pages is configured for a project site at:

`https://cyberpivots.github.io/GH_CBBS_PAGE/`

The source branch is `gh-pages`, generated from `dist/` after `pnpm build`.

If a custom domain is added later, update `astro.config.mjs`, `public/robots.txt`, and the deployment notes in `docs/agent-guidance/deployment.md`.
