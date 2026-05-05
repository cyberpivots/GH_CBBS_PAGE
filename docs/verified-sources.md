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
- Scope: Sanitized public claims verified from private CBBS product documentation, public-site assets, and public-release review materials inspected on 2026-05-01.
- Evidence:
  - Private CBBS product source review notes retained outside this public repository.
  - Approved screenshots and brand assets already copied into this repository.
  - Public-release content entries under `src/content/**`.
- Notes: This source entry approves the summarized public facts in this site, not raw private source publication.

### Heltec firmware source review
- Status: `approved-public`
- Scope: Sanitized public claims verified from private CBBS field-node firmware review materials inspected on 2026-05-01.
- Evidence:
  - Private field-node source review notes retained outside this public repository.
  - Approved summarized claims in published `src/content/**` entries.
- Notes: This source entry approves the summarized public facts in this site, not raw private source publication.

### CBBS asset source review
- Status: `approved-public`
- Scope: Repo-owned logo and screenshot assets imported through `scripts/import-cbbs-assets.mjs`, generated P070 display captures from `scripts/generate-p070-screens.mjs`, and generated social preview artwork from `scripts/generate-social-card.mjs`.
- Evidence:
  - `src/data/cbbs-assets.json`
  - `scripts/generate-p070-screens.mjs`
  - `scripts/generate-social-card.mjs`
  - Private asset approval notes retained outside this public repository.
- Notes: Third-party product photos and official vendor screenshots remain excluded unless separately approved.

### CAD automation tool and vendor references
- Status: `approved-public`
- Scope: Public-safe repo tooling guidance for source-derived local CAD automation, generated artifact handling, Fusion desktop handoff, mesh inspection, and optional future web 3D delivery.
- URLs:
  - https://cadquery.readthedocs.io/en/latest/importexport.html
  - https://trimesh.org/index.html
  - https://docs.astral.sh/uv/concepts/projects/dependencies/
  - https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/WritingDebugging_UM.htm
  - https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/PythonTemplate_UM.htm
  - https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ExportManager_createSTEPExportOptions.htm
  - https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ExportManager_createSTLExportOptions.htm
  - https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/RenderSample_Sample.htm
  - https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Application_registerCustomEvent.htm
  - https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Commands_UM.htm
  - https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/OpeningFilesFromWebPage_UM.htm
  - https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Viewport_saveAsImageFile.htm
  - https://help.autodesk.com/cloudhelp/ENU/Fusion-Animate/files/GUID-25E6D2E0-8057-4BFF-93B3-E7AEE2C4404A.htm
  - https://help.autodesk.com/view/fusion360/ENU/?contextId=DRAWINGS-CREATE-FROM-DESIGN-CMD
  - https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-uiautomationoverview
  - https://aps.autodesk.com/developer/overview/automation-api
  - https://threejs.org/manual/en/loading-3d-models.html
  - https://gltf-transform.dev/
- Notes: Generated CAD, STEP, STL, GLB, renders, and Fusion logs are not approved public product assets unless a later source review explicitly promotes them.

### 3D modeling capability research references
- Status: `approved-public`
- Scope: Public-safe internal tooling guidance for CAD-as-code candidates,
  rendering candidates, mesh diagnostics, screenshot/UI automation review,
  slicer CLI research, and deferred Fusion cloud automation planning.
- URLs:
  - https://build123d.readthedocs.io/en/stable/index.html
  - https://python-mss.readthedocs.io/stable/
  - https://pywinauto.readthedocs.io/en/latest/
  - https://pywinauto.readthedocs.io/en/latest/getting_started.html
  - https://docs.blender.org/manual/en/latest/advanced/command_line/render.html
  - https://docs.blender.org/api/current/bpy.ops.render.html
  - https://www.open3d.org/docs/release/
  - https://www.open3d.org/docs/release/tutorial/geometry/mesh.html
  - https://docs.pyvista.org/
  - https://pyvista.org/
  - https://pypi.org/project/manifold3d/
  - https://github.com/prusa3d/PrusaSlicer/wiki/Command-Line-Interface
  - https://ultimaker.github.io/CuraEngine/
  - https://gltf-transform.dev/cli
  - https://aps.autodesk.com/automation-apis
- Notes: These sources support internal tooling research only. They do not
  approve dependency installation, G-code generation, CAD publication, public
  downloads, print-success claims, environmental claims, RF claims, unattended
  printing, or automatic print intervention.

### 3D print export and monitoring references
- Status: `approved-public`
- Scope: Internal-review printer/process records, STL/STEP print package gating,
  read-only K1 camera endpoint probing, optional local frame metrics, and manual
  slicer/material workflow notes.
- URLs:
  - https://www.creality.com/compare/compare-k1-flagship-series/
  - https://store.creality.com/products/creality-ai-camera-for-k1
  - https://store.anycubic.com/collections/fdm-printer/products/kobra-2-max
  - https://store.anycubic.com/blogs/3d-printing-guides/anycubic-kobra-2-series-specs-and-features-comparison
  - https://www.creality.com/download/creality-cr-30-3d-printer
  - https://store.creality.com/ca/products/cr-30-3d-printer
  - https://creality-3d.jp/shopdetail/000000000009/
  - https://moonraker.readthedocs.io/en/stable/web_api/
  - https://docs.octoprint.org/en/main/configuration/index.html
  - https://mkdocs.octoprint.org/reference/octoprint/schema/config/webcam/
  - https://docs.opencv.org/master/d8/dfe/classcv_1_1VideoCapture.html
  - https://www.obico.io/docs/api/api-objects/
  - https://www.obico.io/docs/user-guides/first_layer_ai/nozzle-ninja-first-layer-ai/
  - https://cadquery.readthedocs.io/en/latest/importexport.html
  - https://trimesh.org/trimesh.html
  - https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135/
  - https://help.prusa3d.com/article/asa_1809
  - https://help.prusa3d.com/article/petg_2059
  - https://www.mcmaster.com/products/heat-set-inserts
  - https://www.tappex.co.uk/threaded-inserts-for-3d-printed-products-or-prototypes/
- Notes: These references support internal print-package selection and
  monitoring-tool safety gates only. They do not approve public download
  publication, G-code publication, print-success claims, environmental rating
  claims, unattended-print claims, or automatic print intervention.

### Public hardware mechanical references
- Status: `approved-public`
- Scope: Source-derived local fit-test dimensions and blockers for Heltec V2 and Nextion/P070 prototype CAD work.
- URLs:
  - https://heltec.org/project/wifi-lora-32v2/
  - https://resource.heltec.cn/download/WiFi_LoRa_32/WiFi%20Lora32.pdf
  - https://itead.cc/product/7-0-nextion-intelligent-series-hmi-resistivecapacitive-touch-display-without-enclosure/
  - https://cdn.nextion.tech/wp-content/uploads/2022/03/NX8048P070-011C_dimension.pdf
  - https://cdn.nextion.tech/wp-content/uploads/2022/03/NX8048P070-011C-Y_dimension.pdf
  - https://cdn.nextion.tech/wp-content/uploads/2019/07/NX8048P070-011C-Y-EMC-Certificate-Report.pdf
- Notes: These references support fit-test CAD inputs and reference-only P070 enclosure envelope comparison. They do not approve full enclosure release, production status, field performance, weather resistance, RF performance, or availability claims.

## Internal Sources Not Approved For Publication

### Private development repositories
- Status: `internal-review`
- Scope: Private CBBS-related development work.
- Notes: Do not publish implementation details, code, issues, screenshots, logs, roadmap items, performance claims, repository names, branch metadata, or private paths unless the specific fact is approved for public release and summarized in an approved public source entry.
