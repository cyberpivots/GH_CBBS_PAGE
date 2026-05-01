# Decision 0001: Static Site Stack

## Decision
Use Astro static output with TypeScript content collections, GitHub Pages deployment, official sitemap generation, and Pagefind static search.

## Rationale
- Astro produces static HTML suitable for GitHub Pages.
- Content collections provide typed frontmatter and safer public content workflows.
- Pagefind adds search without a hosted service or server component.
- The sitemap integration supports search discovery for generated static routes.

## Consequences
- Dynamic server features are out of scope for this repository.
- Public claims must be represented as repository-local content and verified before publication.
- Deployment path handling must account for the GitHub project site base path until a custom domain exists.

