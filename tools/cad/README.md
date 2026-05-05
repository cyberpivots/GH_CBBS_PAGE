# CBBS CAD Automation

This Python package validates public-safe CAD specs and generates source-derived
fit-test artifacts for local review. Rugged and outdoor-facing artifacts are
prototype coupons or fit frames only; they do not imply environmental or impact
ratings. It is intentionally separate from the Astro site so generated CAD,
meshes, renders, and Fusion logs do not become public site assets by accident.

## Commands

```bash
uv run --project tools/cad cbbs-cad validate
uv run --project tools/cad cbbs-cad audit-sources
uv run --project tools/cad cbbs-cad evidence-report
uv run --project tools/cad cbbs-cad manifest
uv run --project tools/cad cbbs-cad generate
uv run --project tools/cad cbbs-cad print-package
uv run --project tools/cad cbbs-cad inspect-mesh 3d-print-work/generated/cad
uv run --project tools/cad cbbs-cad fusion-job
uv run --project tools/cad cbbs-cad fusion-status
uv run --project tools/cad cbbs-cad fusion-install
uv run --project tools/cad cbbs-cad fusion-smoke
uv run --project tools/cad cbbs-cad fusion-agent-status
uv run --project tools/cad cbbs-cad fusion-agent-run
uv run --project tools/cad cbbs-cad fusion-agent-run --action cleanup_owned_documents
uv run --project tools/cad cbbs-cad fusion-agent-restart
uv run --project tools/cad cbbs-cad fusion-ui-snapshot
uv run --project tools/cad cbbs-cad fusion-ui-invoke
uv run --project tools/cad --group monitor cbbs-cad k1-probe
uv run --project tools/cad --group monitor cbbs-cad k1-monitor
```

The default output root is `3d-print-work/generated/`, which is ignored by git.
Review and intentionally promote any artifact before placing it in public content
or downloads.

The Fusion agent commands add a local desktop control layer. The Fusion add-in
watches `3d-print-work/generated/fusion/agent/requests/` for JSON commands and
writes responses, heartbeat state, snapshots, and process-action logs under the
same ignored agent output root. Windows UI Automation commands run through
PowerShell against the local Fusion window and require explicit guard flags for
clicks, key input, or window closing.

Generated Fusion jobs carry a disposable-document lifecycle policy. The default
is to tag CBBS-owned generated documents/components, avoid Fusion cloud saves,
discard generated document changes after local exports/renders, and fail status
if CBBS-owned modified documents are left open outside explicit review mode.

## 3D Print Packages

Printer/process records live in `3d-print-work/data/printers/`. The default
print package target is `creality_k1_modified_asa`; it constrains P070 work to
the K1 `220 x 220 x 250 mm` build envelope and packages the P070 rear tray and
front display door as separate plates. `anycubic_kobra2_max` is a large-bed
PLA/PETG fallback, with ASA blocked by default. `creality_cr30_belt` is
experimental and blocked until belt geometry, slicer behavior, usable volume,
and material limits are measured.

`cbbs-cad print-package` writes internal-review output under
`3d-print-work/generated/print-packages/<run_id>/<concept>/<printer>/`. Packages
include selected STL/STEP files, selected Fusion renders when available,
`README.md`, `guides/<printer>.md`, `print-manifest.json`,
`checksums.sha256`, and `print-log-template.md`. G-code is not generated or
included by default.

Use GUI slicers manually until local profiles are verified. The K1 path is
Creality Print first. PrusaSlicer/OrcaSlicer CLI automation is deferred until
local profiles are reviewed.

## K1 Monitoring

K1 camera monitoring is read-only in v1. Install optional dependencies only when
needed:

```bash
uv sync --project tools/cad --group monitor
```

`k1-probe` checks Moonraker-style webcam metadata, common MJPEG snapshot/stream
URLs, and HTTP availability with GET requests only. `k1-monitor` adds first-pass
snapshot/frame metrics with Pillow/OpenCV when frames are available. Both write
under `3d-print-work/generated/monitoring/k1/<timestamp>/` and never send print,
pause, cancel, restart, upload, or G-code commands.
