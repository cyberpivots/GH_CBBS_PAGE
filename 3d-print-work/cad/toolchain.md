# CAD Toolchain

Truth state: internal review / concept.

## Decision

Use a source-first CAD workflow with agent-friendly text inputs:

- Primary automation source: YAML specs under `3d-print-work/data/`.
- Primary headless generator: CadQuery through the repo-local Python package in `tools/cad/`.
- Interchange export: STEP for board/display/enclosure solids.
- Print export: STL for fit-test coupons and simple geometry exchange.
- Visual review and Fusion-native export: Autodesk Fusion desktop add-in under `3d-print-work/fusion/`.
- Optional future web preview format: GLB/glTF only after public preview approval.

## Rationale

- CadQuery keeps simple fit-test geometry in reviewable Python while supporting STEP, STL, 3MF, and glTF exports.
- STEP exports are better than mesh-only files for downstream CAD review.
- trimesh gives a repeatable mesh inspection pass for STL/3MF health checks.
- Fusion desktop scripting supports local script/add-in automation, local rendering, and STEP/STL export handoff.
- Three.js recommends glTF/GLB for web 3D delivery when public previews are later approved.
- GitHub documents that Git LFS cannot be used with GitHub Pages sites, so public-site-served assets should not depend on LFS behavior.

Sources:
- https://cadquery.readthedocs.io/en/latest/importexport.html
- https://trimesh.org/index.html
- https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/WritingDebugging_UM.htm
- https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ExportManager_createSTEPExportOptions.htm
- https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ExportManager_createSTLExportOptions.htm
- https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/RenderSample_Sample.htm
- https://threejs.org/manual/en/loading-3d-models.html
- https://help.prusa3d.com/article/saving-projects-as-3mf_1773
- https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage

## Folder Conventions

- `3d-print-work/data/hardware/`: source-derived hardware dimensions and blockers.
- `3d-print-work/data/concepts/`: printable fit-test and coupon parameters.
- `tools/cad/`: CadQuery generator, validators, mesh inspection, and Fusion job tooling.
- `3d-print-work/generated/cad/`: ignored local STEP/STL/manifests.
- `3d-print-work/generated/fusion/`: ignored local Fusion renders, logs, exports, and job JSON.
- `3d-print-work/cad/reference/`: future vendor drawings, downloaded only when redistribution terms permit it.

Keep generated exports separate from editable source files. Do not store private board photos in this public repository unless they are approved for public release.

## File Naming

Use lowercase names with a family, part, and revision:

Use lowercase concept ids and generated stems:

- `heltec_v2_fit_card.step`
- `heltec_v2_fit_card.stl`
- `p070_fit_frame.step`
- `screw_boss_coupon.stl`
- `p070_hinged_wall_enclosure.step` only after measured full-case inputs are
  recorded and generation is explicitly enabled.

Use `r01`, `r02`, and so on only after a physical fit-test artifact is promoted
out of the ignored generated folder. Do not overwrite successful fit-test
artifacts.

## Units And Origin

- Use millimeters for all CAD dimensions.
- Put the hardware origin at a measurable board/display corner.
- Document origin choice in each concept notes file.
- Keep display active area, board outline, mounting holes, connector envelopes, cable bend envelopes, antenna zones, and keepout volumes as named reference features.
- Keep rugged/outdoor features as named prototype features: wall sections,
  reinforcement ribs, gasket seats, drip lips, cable-entry bosses, mounting
  tabs, and venting placeholders.

## Export Rules

- Export STEP/STL from CadQuery for fit-test coupons.
- Keep measurement-gated full enclosures disabled in their concept spec until
  required local measurements and selected hardware are recorded.
- Create a Fusion job JSON with `pnpm run cad:fusion-job` after generation.
- Check the generated job and local Fusion handoff with
  `pnpm run cad:fusion-status`.
- Use `pnpm run cad:fusion-install` to sync the Fusion add-in when a desktop
  handoff is intended.
- Export STEP after every enclosure revision that passes a physical fit check.
- Export STL only from reviewed solid geometry.
- Save 3MF slicer projects for prints that were actually attempted.
- Do not commit G-code unless a printer-specific production release later requires it and the target printer is documented.
- Do not promote rugged/outdoor outputs as rated, sealed, field-ready, or
  production-ready without validation and release approval.
- Do not rely on Windows STEP file association for automation. Use the Fusion
  add-in plus generated job JSON workflow.

## Large File Rules

- Keep generated files small and intentional.
- Avoid committing duplicate binary exports.
- Do not rely on Git LFS for assets that must be served by GitHub Pages.
- If future CAD assets become large, use GitHub Releases or a separate artifact workflow rather than bloating the public site source.
