# Deployment

## Current Target
- Host: GitHub Pages
- Site type: project site
- Default URL: `https://cyberpivots.github.io/GH_CBBS_PAGE/`
- Astro config: `site: "https://cyberpivots.github.io"` and `base: "/GH_CBBS_PAGE"`

## Publish Model
- `main` contains the Astro source workspace.
- `gh-pages` contains the generated static output from `dist/`.
- GitHub Pages should be configured to deploy from the `gh-pages` branch root.

## Publish Steps
1. Run `pnpm build`.
2. Replace the `gh-pages` branch contents with the generated files from `dist/`.
3. Push `main` and `gh-pages`.
4. Verify the Pages settings report `gh-pages` as the publishing source.

## Custom Domain Migration
If a custom domain is added:
- Verify the domain in GitHub account or organization settings before use.
- Update `astro.config.mjs` to the custom domain and set `base: "/"`.
- Update `public/robots.txt`.
- Configure the domain in repository Pages settings.
- Enforce HTTPS after certificate provisioning succeeds.

## Constraints
- GitHub Pages is static hosting. Do not add server-only code paths.
- Avoid collecting sensitive user data.
- Keep build time and site size inside GitHub Pages limits.
