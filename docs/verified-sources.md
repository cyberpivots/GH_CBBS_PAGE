# Verified Public Sources

This file is the source register for public claims used on the CBBS site. Agents must add source entries here before publishing specific claims in `src/content/**`.

## Source Status
- `approved-public`: safe to use in published pages.
- `internal-review`: not safe to publish yet.
- `retired`: do not use for new content.

## Approved Sources

### CBBS promotional repository
- Status: `approved-public`
- Scope: Facts about this GitHub Pages workspace, its build tooling, and its static deployment process.
- Evidence: Repository-local files in this workspace.
- Notes: Do not use this as evidence for product capability claims.

### GitHub Pages documentation
- Status: `approved-public`
- Scope: GitHub Pages static hosting, public visibility, publishing source configuration, limits, custom domains, and HTTPS.
- URLs:
  - https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages
  - https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site
  - https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
  - https://docs.github.com/en/pages/getting-started-with-github-pages/securing-your-github-pages-site-with-https
- Notes: Pages output is public on the internet even when the source repository is private on supported plans.

### Astro documentation
- Status: `approved-public`
- Scope: Astro static output, GitHub Pages deployment, content collections, image handling, and sitemap integration.
- URLs:
  - https://docs.astro.build/en/guides/deploy/github/
  - https://docs.astro.build/en/guides/content-collections/
  - https://docs.astro.build/en/guides/images/
  - https://docs.astro.build/en/guides/view-transitions/
  - https://docs.astro.build/en/guides/integrations-guide/sitemap/

### Pagefind documentation
- Status: `approved-public`
- Scope: Static search indexing, search UI, and search filters for the generated site.
- URLs:
  - https://pagefind.app/docs/
  - https://pagefind.app/docs/filtering/
- Notes: Pagefind produces static search assets and does not require a hosted search service.

### Web platform PWA references
- Status: `approved-public`
- Scope: Web app manifest and service-worker behavior for optional offline browsing of the static public site.
- URLs:
  - https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API
  - https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Manifest
- Notes: Service workers require secure contexts, with localhost treated as secure for development.

### Web quality references
- Status: `approved-public`
- Scope: Accessibility, SEO, and performance quality gates.
- URLs:
  - https://www.w3.org/TR/WCAG22/
  - https://web.dev/articles/vitals
  - https://developers.google.com/search/docs/fundamentals/seo-starter-guide
  - https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data

### CBBS product source review
- Status: `approved-public`
- Scope: Sanitized public claims verified from private CBBS product docs and data files inspected on 2026-05-01.
- Evidence:
  - `cyberpivots/ClaRTK-MeshBBS:README.md`
  - `cyberpivots/ClaRTK-MeshBBS:branding/README.md`
  - `cyberpivots/ClaRTK-MeshBBS:docs/guides/client-installation-overview.md`
  - `cyberpivots/ClaRTK-MeshBBS:docs/guides/no-code-room-client-guide.md`
  - `cyberpivots/ClaRTK-MeshBBS:docs/guides/no-code-agriculture-grower-ops-guide.md`
  - `cyberpivots/ClaRTK-MeshBBS:docs/design/windows-sysop-manager-architecture.md`
  - `cyberpivots/ClaRTK-MeshBBS:docs/design/gis-geospatial-architecture.md`
  - `cyberpivots/ClaRTK-MeshBBS:javascript/field/stakeholder-deck/public/assets/data/*.json`
- Notes: This source entry approves the summarized public facts in this site, not raw private source publication.

### Heltec firmware source review
- Status: `approved-public`
- Scope: Sanitized public claims verified from the private Heltec firmware workspace inspected on 2026-05-01.
- Evidence:
  - `cyberpivots/Heltec_Wifi_Lora32_V2:README.md`
  - `cyberpivots/Heltec_Wifi_Lora32_V2:firmware/README.md`
  - `cyberpivots/Heltec_Wifi_Lora32_V2:docs/design/off-grid-bbs-architecture.md`
  - `cyberpivots/Heltec_Wifi_Lora32_V2:docs/design/hub-spoke-mesh-design.md`
- Notes: This source entry approves the summarized public facts in this site, not raw private source publication.

### CBBS asset source review
- Status: `approved-public`
- Scope: Repo-owned logo and screenshot assets imported through `scripts/import-cbbs-assets.mjs`, plus generated P070 display captures from `scripts/generate-p070-screens.mjs`.
- Evidence:
  - `src/data/cbbs-assets.json`
  - `scripts/generate-p070-screens.mjs`
  - `cyberpivots/ClaRTK-MeshBBS:javascript/field/stakeholder-deck/sources.md`
- Notes: Third-party product photos and official vendor screenshots remain excluded unless separately approved.

## Internal Sources Not Approved For Publication

### Private firmware repository
- Status: `internal-review`
- Scope: Private CBBS-related development work.
- URL: https://github.com/cyberpivots/Heltec_Wifi_Lora32_V2
- Verified metadata: private repository, default branch `main`, description says it demonstrates microcontroller capability and includes example use cases and programming tools.
- Notes: Do not publish implementation details, code, issues, screenshots, logs, roadmap items, performance claims, or architecture details from this repository unless the specific fact is copied into an approved public source entry.
