# P070 Heltec Outdoor Model Review

Truth state: internal review.

Review baseline: Fusion run `fusion-20260503T030037Z`.

This review records the current CAD/Fusion state for
`p070_heltec_outdoor_controller_enclosure`. It is not public product copy and
does not approve any enclosure protection class, runtime, RF range, impact
rating, or field-readiness claim.

## Baseline Artifacts

- CAD manifest: `3d-print-work/generated/cad/manifest.json`
- Fusion job: `3d-print-work/generated/fusion/latest-job.json`
- Fusion summary: `3d-print-work/generated/fusion/run-summary.json`
- Fusion review exports:
  - `3d-print-work/generated/fusion/exports/fusion-20260503T030037Z-review.step`
  - `3d-print-work/generated/fusion/exports/fusion-20260503T030037Z-review.stl`

## P070 Heltec Assembly State

- Full assembly bounds: 206.2099 x 239.9135 x 335.4204 mm. This includes the
  external antenna keepout and is not a K1 print footprint.
- Rear tray print-part bounds: 206.2094 x 143.6185 x 126.4092 mm.
- Front display door print-part bounds: 206.2055 x 124.4096 x 8.8106 mm.
- Effective K1 split-plate limit with 6 mm brim: 208 x 208 mm.
- Tightest K1 split-print X margin: 1.7906 mm before the configured brim
  envelope is exceeded.
- Combined K1 plate remains rejected; K1 Max combined layout remains accepted.
- Surface treatment baseline:
  - 6 raised front contour rails.
  - 20 rear-pod macro ribs.
  - 8 mount-tab accent ribs.
  - Raised `CBBS` text using DejaVu Sans as the local deterministic font
    fallback.

## Fusion Status

- Fusion status command passed for run `fusion-20260503T030037Z`.
- Imports: 31/31.
- Assembly import items: 31/31.
- Render source imports: all 34 sourced.
- Fusion renders: 34 separate render outputs all present.
- Fusion exports: all present.
- Generated document cleanup: no leftover CBBS-owned modified documents.
- Fusion job render mode: `per-artifact-source`; each top-level model uses a
  `<concept_id>__model` render key and each assembly view uses a
  `<concept_id>__<view>` render key.

Review render paths:

- `3d-print-work/generated/fusion/renders/fusion-20260503T030037Z-p070_heltec_outdoor_controller_enclosure__model.png`
- `3d-print-work/generated/fusion/renders/fusion-20260503T030037Z-p070_heltec_outdoor_controller_enclosure__closed-front.png`
- `3d-print-work/generated/fusion/renders/fusion-20260503T030037Z-p070_heltec_outdoor_controller_enclosure__closed-isometric.png`
- `3d-print-work/generated/fusion/renders/fusion-20260503T030037Z-p070_heltec_outdoor_controller_enclosure__door-open.png`
- `3d-print-work/generated/fusion/renders/fusion-20260503T030037Z-p070_heltec_outdoor_controller_enclosure__exploded.png`
- `3d-print-work/generated/fusion/renders/fusion-20260503T030037Z-p070_heltec_outdoor_controller_enclosure__k1-plate-tray.png`
- `3d-print-work/generated/fusion/renders/fusion-20260503T030037Z-p070_heltec_outdoor_controller_enclosure__k1-plate-door.png`
- `3d-print-work/generated/fusion/renders/fusion-20260503T030037Z-p070_heltec_outdoor_controller_enclosure__hardware-reference.png`
- `3d-print-work/generated/fusion/renders/fusion-20260503T030037Z-p070_heltec_outdoor_controller_enclosure__power-rf-layout.png`
- `3d-print-work/generated/fusion/renders/fusion-20260503T030037Z-p070_surface_treatment_coupon__model.png`

## Review Findings

- Keep the model internal-review and blocked. The exact Heltec board revision,
  installed cables, battery pack behavior, regulator heat, RF route, gasket,
  venting, material, and service-cycle behavior still require physical
  validation.
- The K1 split-print footprint currently passes but has a tight X margin.
  Further cosmetic protrusions should be tested against the 208 x 208 mm
  effective envelope before generation is accepted.
- The raised surface treatment should be tested as a coupon before relying on a
  full enclosure print. Exact Inter or Space Grotesk brand typography is blocked
  until approved font files are present in the repository.

## Checklist Snapshot

- Fit check: blocked until physical hardware is measured.
- Assembly check: blocked until printed parts, fasteners, straps, and service
  cycles are tested.
- Thermal check: blocked until P070 brightness, Heltec transmit behavior,
  regulator heat, and enclosure orientation are measured.
- RF smoke check: blocked until antenna placement and pigtail strain relief are
  tested with the actual printed configuration.
- Field handling check: blocked until mount tabs, raised features, edges, and
  cable exits are checked on printed parts.
