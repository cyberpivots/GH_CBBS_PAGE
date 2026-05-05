# CAD Automation Guidance

This repository may contain public-safe CAD planning and automation files, but
generated CAD artifacts are not public site assets by default. Keep outputs under
`3d-print-work/generated/` until they are intentionally reviewed, labeled, and
promoted.

## Source Hierarchy

Use this order for enclosure-critical dimensions:

1. Measured hardware in hand, with public-safe measurement notes.
2. Official mechanical drawings or vendor datasheets for the exact model and revision.
3. Approved public CBBS content for role and truth-state context.
4. Community CAD/STL models only as visual references, never as dimensional evidence.

Do not infer dimensions from screenshots, marketing photos, generated images, or
private firmware/project material. If the exact board or display variant is not
confirmed, generate only fit-test coupons or mark the concept blocked.

## Truth States

Use the site truth-state labels consistently:

- `current`
- `proof/simulator`
- `mock scenario`
- `projected`
- `internal review`

Generated CAD concepts must not use `current` or `production`. Use
`measurement_status` and `derivation_state` to say whether a model is measured,
source-derived, measurement-required, or blocked.

## Local Data And Outputs

- Structured inputs live in `3d-print-work/data/hardware/` and
  `3d-print-work/data/concepts/`.
- Every CAD-used hardware dimension must have a `dimension_sources` evidence
  entry with source id, locator, retrieval date, evidence type, and verification
  status.
- Every numeric concept parameter must have a `parameter_sources` evidence
  entry. Design parameters are allowed only for coupons and fit-test artifacts,
  not final enclosures.
- Vendor images are `reference-only` unless an explicit public approval source
  is recorded. Do not copy vendor product images into public assets.
- The Python package lives in `tools/cad/`.
- Generated STEP/STL/manifests go under `3d-print-work/generated/cad/`.
- Fusion job JSON, logs, renders, and exports go under
  `3d-print-work/generated/fusion/`.
- Printer/process records live in `3d-print-work/data/printers/`.
- Generated print export packages go under
  `3d-print-work/generated/print-packages/`.
- K1 read-only probe and monitor output goes under
  `3d-print-work/generated/monitoring/k1/`.
- Do not copy generated CAD, renders, or GLB previews into `public/` or
  `src/content/**` without a public-release source review.

Default commands:

```bash
pnpm run cad:validate
pnpm run cad:audit
pnpm run cad:evidence-report
pnpm run cad:manifest
pnpm run cad:generate
pnpm run cad:inspect
pnpm run cad:fusion-job
pnpm run cad:fusion-status
pnpm run cad:print-package
```

The repo scripts use `uv`. If `uv` is not installed, install it before running
the CAD package or use an equivalent isolated Python 3.12 environment.

For Fusion desktop handoff work, use the global Codex skill
`$cbbs-fusion360-workflows`. It documents the CBBS-safe install, status, and
manual smoke-test sequence.

For native Fusion assembly instructions and 2D drawings, see
`docs/agent-guidance/fusion-assembly-documentation.md`. Assembly instructions
must be authored with Fusion Animation storyboards/callouts and Drawing
workspace sheets, not generated solid arrows or text geometry.

For skill applicability notes, see `docs/agent-guidance/skill-inventory.md`.

## Current CAD Scope

Allowed generated artifacts:

- Heltec V2 board-envelope fit card, source-derived and measurement-required.
- P070 flat fit-frame from official NX8048P070-011C dimensions, prototype only.
- Screw boss, heat-set insert, OLED window, cable relief, and label plate coupons.
- Rugged/outdoor prototype coupons for wall sections, gasket flanges, reinforced
  mount tabs, cable-entry bosses, and drip-lip seams.
- Source-derived rugged fit artifacts for Heltec V2 tray-gauge and P070 bezel
  fit-frame work, still blocked from full-case status.
- Measurement-gated P070 hinged wall enclosure record. It may generate
  internal-review CAD, including separate tray, display-door, hinge-pin,
  display-reference, cable-gland-reference, and assembly-view STEP files for
  Fusion review. It remains blocked from full-case/release status until
  measured rear clearance, cable/gland, hinge, and latch inputs are recorded.
- Blocked placeholder records for unselected Raspberry Pi hub, radio-head,
  agriculture gateway, agriculture sensor, and P800 display hardware. These
  records exist to prevent accidental dimension invention.

Blocked artifacts:

- Full Heltec node cases until the physical board revision, antenna route,
  connector clearances, button locations, and header population are measured.
- Full P070 case generation until the exact display variant, cable exit, rear
  clearance, mounting target, hinge pin, latch tolerance, and gland/strain
  relief strategy are confirmed.
- Hub, gateway, and agriculture enclosures until exact boards, cable paths,
  mounting environment, and material targets are selected.
- Any environmental or impact rating claim until there is measured hardware,
  selected material, selected gasket/cable/vent hardware, a validation plan, and
  approved evidence. Rugged/outdoor prototype geometry is not an IP, NEMA, IK,
  waterproof, dustproof, or field-qualified claim.

## Evidence Audit

`pnpm run cad:audit` must fail if:

- A dimension or numeric parameter lacks an evidence locator.
- Geometry uses conflict-marked or blocked evidence.
- An unresolved source conflict affects geometry.
- A public-release CAD record lacks an approved release source.
- A vendor image is marked public-approved without approval.
- A full enclosure is enabled before referenced hardware is measured.
- Free text includes environmental rating/protection claims instead of using
  `environmental_context.rating_claims`.
- Rating claims are present without measured hardware, unblocked full-case
  status, approved-public evidence, and a validation plan.

`pnpm run cad:evidence-report` writes local Markdown and JSON summaries under
`3d-print-work/generated/evidence/`. Treat those files as local review output.

## Fusion Handoff

The Fusion desktop add-in under
`3d-print-work/fusion/CBBSFusionAutomation/` reads a generated Fusion job JSON,
imports STEP/STL artifacts, starts local RenderManager jobs, and can export STEP
or STL through Fusion ExportManager. Treat Fusion output as local review output
until explicitly approved.

Use `pnpm run cad:fusion-install` to sync the repo add-in into Fusion's default
AddIns folder, write the installed `job_path.txt`, and set the installed manifest
to `runOnStartup: true`. The repo add-in remains the source of truth; the
installed copy is disposable sync output and may drift.

Use `pnpm run cad:fusion-status` to check the generated job, artifact count,
installed manifest, `job_path.txt`, latest Fusion log, review exports, render
outputs, generated-document cleanup, and `run-summary.json`. Use
`pnpm run cad:fusion-smoke` only after the user has started or restarted Fusion
or manually run the add-in; the command watches for a new log and does not
control the Fusion process.

Generated Fusion documents are disposable review workspaces. Generated jobs
default to `close_generated_documents: true`, `save_policy:
discard_generated`, `allow_user_prompt: false`, and `keep_open_for_review:
false`. The add-in tags generated documents/components with CBBS owner and run
metadata, records document state and close results in `run-summary.json`, and
closes only CBBS-owned generated documents with `Document.close(False)`.

Do not save generated Fusion designs to Fusion cloud automatically. Local
STEP/STL exports, render files, logs, and run summaries under
`3d-print-work/generated/` are the durable outputs. To intentionally inspect a
generated Fusion document, create the job with review mode enabled
(`cad:fusion-job --keep-open-for-review`) so status treats the open document as
intentional.

P070 assembly-capable jobs include render views named `closed-front`,
`closed-isometric`, `door-open`, `exploded`, `k1-plate-tray`,
`k1-plate-door`, optional `k1-max-combined`, and `hardware-reference`. The
generated job also includes view-specific STEP sources so Fusion can render
assembly layouts without promoting CAD or render output into public assets.

The installed add-in also provides a local agent bridge. It watches
`3d-print-work/generated/fusion/agent/requests/` for JSON commands, executes
supported Fusion API actions inside Fusion, and writes responses, heartbeat
state, viewport snapshots, UI logs, and process-action logs under the ignored
agent output root. Use `pnpm run cad:fusion-agent-status` to check whether the
bridge is loaded, and `pnpm run cad:fusion-agent-run` to request actions such as
`run_job`, `cleanup_owned_documents`, `open_artifact`, `capture_viewport`,
`ui_state`, `execute_command_id`, or guarded `execute_text_command`. Use
`pnpm run cad:fusion-clean-owned` to close leftover CBBS-owned generated
documents through the bridge without restarting Fusion.

Agents may inspect and manipulate the Fusion desktop UI with
`pnpm run cad:fusion-ui-snapshot` and `pnpm run cad:fusion-ui-invoke`. UIA
commands run through Windows PowerShell/.NET UI Automation and require explicit
guard flags before clicking fallback coordinates, sending keys, or closing a
window.

Do not restart, kill, or force-reload Fusion implicitly. Managed process control
is allowed only through explicit commands such as
`pnpm run cad:fusion-agent-restart` or `pnpm run cad:fusion-agent-run
--allow-restart`. Restart uses bridge document inventory when available and
refuses user-owned modified documents unless `--allow-unsaved-close` is
explicitly provided. CBBS-owned generated leftovers should be closed with
`cad:fusion-clean-owned` rather than treated as user work. STEP file association
is not reliable enough for this workflow; use the add-in plus generated job JSON
or the agent bridge instead.

Fusion Automation API cloud execution is deferred. It requires Autodesk Platform
Services application credentials/PAT and a separate TypeScript workflow, so do
not add cloud automation or credentials to this public repository.

## Print Export Packages

Use `pnpm run cad:print-package` to build internal-review STL/STEP print
packages from the generated CAD manifest and latest Fusion summary. The default
target is `creality_k1_modified_asa`, using the official K1-class
`220 x 220 x 250 mm` envelope and separate P070 tray/door plates. Do not accept
the combined P070 K1 plate.

`anycubic_kobra2_max` is a fallback for large PLA/PETG fit checks; ASA is
blocked unless explicitly reviewed as a blocked/experimental process. The
`creality_cr30_belt` path is blocked until CR-30 source conflicts, belt
orientation, slicer profile, usable volume, and material limits are measured.

Packages must include README-first guidance, printer guide, copied STL/STEP
files, selected renders when available, `print-manifest.json`,
`checksums.sha256`, and a print log template. Do not generate or commit G-code
by default. Use Creality Print manually for the K1 path until local profiles are
verified; slicer CLI automation is deferred.

## K1 Read-Only Monitoring

Use `pnpm run cad:k1-probe` and `pnpm run cad:k1-monitor` only for read-only
camera endpoint discovery and frame-quality capture. These commands may probe
Moonraker webcam metadata, common MJPEG snapshot/stream URLs, and HTTP
availability with GET requests only. They must not send print, pause, cancel,
restart, upload, or G-code commands.

Install monitor dependencies only when needed:

```bash
uv sync --project tools/cad --group monitor
```

Automatic print-failure decisions are deferred until local camera access is
verified and reviewed.

## Web Delivery

If interactive previews are later approved, prefer GLB/glTF for web delivery and
optimize with glTF Transform. Keep CAD-grade STEP files out of public downloads
unless the release decision explicitly approves them.

## References

- CadQuery import/export: https://cadquery.readthedocs.io/en/latest/importexport.html
- trimesh: https://trimesh.org/index.html
- uv dependencies: https://docs.astral.sh/uv/concepts/projects/dependencies/
- Fusion scripts/add-ins: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/WritingDebugging_UM.htm
- Fusion Python add-in template: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/PythonTemplate_UM.htm
- Fusion STEP export: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ExportManager_createSTEPExportOptions.htm
- Fusion STL export: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ExportManager_createSTLExportOptions.htm
- Fusion rendering sample: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/RenderSample_Sample.htm
- Fusion custom events: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Application_registerCustomEvent.htm
- Fusion commands: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Commands_UM.htm
- Fusion URL protocol: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/OpeningFilesFromWebPage_UM.htm
- Fusion viewport snapshots: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Viewport_saveAsImageFile.htm
- Windows UI Automation: https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-uiautomationoverview
- Autodesk Automation API: https://aps.autodesk.com/developer/overview/automation-api
- Creality K1 series comparison: https://www.creality.com/compare/compare-k1-flagship-series/
- JST XH connector datasheet: https://www.jst-mfg.com/product/pdf/eng/eXH.pdf
- LAPP SKINTOP ST-M cable gland data: https://products.lappgroup.com/online-catalogue/cable-glands/skintop-cable-glands-plastic-metric/standard/skintop-st-m.html
- NBK metric clearance holes: https://www.nbk1560.com/en-US/resources/other/article/technical-20-diameter-of-clearance-holes-and-counterbores-for-bolts-and-screws
- Three.js glTF workflow: https://threejs.org/manual/en/loading-3d-models.html
- glTF Transform: https://gltf-transform.dev/
- NEMA enclosure types: https://www.nema.org/docs/default-source/products-document-library/nema-enclosure-types.pdf
- IEC 60529 IP code: https://webstore.iec.ch/en/publication/2447
- IEC 62262 IK code preview: https://webstore.ansi.org/preview-pages/IEC/preview_iec62262%7Bed1.1%7Db.pdf
- Prusa ASA: https://help.prusa3d.com/article/asa_1809
- Prusa PETG: https://help.prusa3d.com/article/petg_2059
- Parker O-Ring Handbook: https://discover.parker.com/Parker-ORing-Handbook-ORD-5700
- GORE protective vents: https://www.gore.com/products/screw-protective-vents-outdoor-electronics-enclosures
