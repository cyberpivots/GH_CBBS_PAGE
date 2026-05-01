# Quality Gates

## Required Commands
- `pnpm check` for content and type-level validation.
- `pnpm test` for unit tests.
- `pnpm build` for production output, Pagefind indexing, publication checks, and link checks.
- `pnpm test:browser` for navigation, responsive behavior, gallery labels, and workflow explorer smoke coverage after public UI changes.

## Browser Smoke Tests
Run `pnpm test:browser` after a production build when changing:
- Navigation
- Layouts
- Responsive behavior
- Search UI
- Deployment paths or Astro base configuration

## Accessibility
Target WCAG 2.2 AA-oriented implementation:
- Semantic landmarks and headings.
- Keyboard-visible focus states.
- Sufficient contrast.
- Meaningful labels and alt text.
- No hover-only access to important content.

## Performance
Keep pages static and lightweight:
- Prefer Astro components and minimal client JavaScript.
- Use local assets.
- Avoid remote scripts and embeds unless documented.
- Watch Core Web Vitals: LCP, INP, and CLS.

## SEO And Discovery
- Keep descriptive URLs.
- Maintain page titles and descriptions.
- Generate sitemaps in production builds.
- Keep crawlable HTML content for important pages.
- Use Pagefind filters for source-backed sections and truth-state labels where useful.
