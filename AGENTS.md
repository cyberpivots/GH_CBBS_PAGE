# AGENTS.md

## Purpose
- This repository builds the public GitHub Pages site for CBBS promotional and documentation content.
- The related firmware/project repository is private. Do not publish private implementation details, secrets, credentials, board-specific internals, screenshots, logs, or unreleased claims unless they are already present in an approved public source in this repo.
- Treat `docs/verified-sources.md` and `src/content/**` as the source of truth for public claims.
- Product-facing entries must carry a truth-state label: current, proof/simulator, mock scenario, projected, or internal review.

## Read First
- Publication policy: `docs/agent-guidance/publication-policy.md`
- Content style: `docs/agent-guidance/content-style.md`
- Quality gates: `docs/agent-guidance/quality-gates.md`
- Deployment notes: `docs/agent-guidance/deployment.md`
- Current decisions: `docs/decisions/`

## Development Commands
- Install dependencies: `pnpm install`
- Start local dev server: `pnpm dev`
- Run type/content checks: `pnpm check`
- Run unit tests: `pnpm test`
- Build production site: `pnpm build`
- Run browser smoke tests after a build: `pnpm test:browser`

## Engineering Rules
- Use `rg` for search and inspect existing files before editing.
- Keep `AGENTS.md` concise. Add durable detail to `docs/agent-guidance/` and link it here.
- Prefer typed Astro content collections for public pages, updates, resources, and FAQs.
- Any promotional claim must be traceable to an approved public source. If a fact is not verified, omit it or mark the content as draft.
- Do not add analytics, forms, tracking, third-party embeds, or remote scripts without documenting the privacy and security tradeoff first.
- Keep the site static. GitHub Pages cannot run server-side logic.

## UI And Content Expectations
- Build accessible pages with semantic HTML, useful headings, descriptive links, visible focus states, and meaningful image alt text.
- Use local optimized assets whenever possible. Store approved public media in `public/assets/` or colocated imported assets under `src/`.
- Keep copy public-facing, accurate, and conservative. Do not imply certifications, performance guarantees, partnerships, or availability unless verified.
- Agriculture and control content may describe records, review, observations, advisory notes, approvals, and guarded command records. Do not claim autonomous irrigation control or live relay, valve, or pump execution unless a future approved source explicitly supports it.

## Verification Before Finishing
- Run the narrowest relevant check for small edits.
- For site structure, dependencies, deployment, or public content changes, run `pnpm build`.
- For navigation or layout changes, run `pnpm test:browser` after `pnpm build` when browser dependencies are available.
