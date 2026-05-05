# 3D Modeling Tooling Capability Review

Truth state: internal review.

Retrieved on: 2026-05-05.

This note records current, directly verified tooling sources for improving CBBS
repo-native 3D modeling, rendering, computer-vision/screen viewing, print-method
awareness, and Fusion automation. It is tooling guidance only. It does not
approve new product claims, generated CAD publication, G-code generation, print
success claims, unattended printing, field readiness, environmental ratings,
RF behavior, runtime, or structural performance.

## Current Baseline To Keep

- CadQuery remains the primary CAD-as-code generator. Its documentation covers
  STEP import/export, assembly export, and assembly metadata; this matches the
  current `tools/cad` source-first workflow.
- trimesh remains the mesh inspection baseline. Its documentation emphasizes
  triangular mesh loading/analysis with watertight-surface checks and repair
  helpers; in this repo, repair should stay diagnostic unless separately
  approved.
- Autodesk Fusion desktop API remains the active Fusion review path. The
  verified API pages cover export execution, STEP/STL export options, viewport
  image capture, and render APIs; the repo add-in keeps these outputs under
  `3d-print-work/generated/fusion/`.
- OpenCV and Pillow remain optional K1 monitoring dependencies. OpenCV
  `VideoCapture` supports video files, cameras, and stream URLs; Pillow provides
  image loading/processing for local metrics. The repo must keep K1 monitoring
  read-only.
- Microsoft UI Automation remains the lower-level Windows UI inspection path for
  guarded Fusion UI state checks. Fusion add-in commands should still be
  preferred before direct UI driving.

## Sandbox Evaluation Candidates

- `mss`: Verified documentation describes fast cross-platform screenshots,
  Python 3.9+, no runtime dependencies, and integration with NumPy/OpenCV/Pillow.
  Evaluate only for desktop screenshot capture when Fusion viewport capture is
  insufficient, with strict output scoping to avoid private-window capture.
- `pywinauto`: Verified documentation describes Windows GUI automation with
  Win32 and UIA backends. Evaluate only if current direct UIA code becomes hard
  to maintain; keep the same allowlists and safety boundaries.
- Blender CLI/API: Verified docs cover background command-line rendering and
  render operators. Evaluate as an external review renderer only after
  source-derived STEP/GLB export exists; do not use Blender renders as geometry
  evidence.
- build123d: Verified documentation describes a Python, parametric BREP CAD
  framework using Open Cascade. Evaluate on isolated coupons only; do not port
  existing CadQuery generators until a side-by-side prototype proves lower
  maintenance cost.
- Open3D: Verified docs cover geometry, visualization, headless rendering, and
  mesh properties including manifold, self-intersection, watertight, and
  orientable checks. Evaluate as a diagnostics overlay that complements
  trimesh.
- PyVista/VTK: Verified docs describe PyVista as a Pythonic VTK interface for
  mesh analysis and 3D plotting, with Python 3.10+ and MIT license noted by the
  project overview. Evaluate only in generated visualization sandboxes because
  direct adoption would add a large dependency surface.
- manifold3d: Verified PyPI metadata describes Manifold as a library for
  manifold triangle meshes with internal Python bindings and trimesh
  interoperability examples. It is present in the current lockfile only as a
  transitive dependency through trimesh extras, so direct imports remain blocked
  until promoted to a direct dependency.

## Deferred Or Blocked Paths

- PrusaSlicer CLI: The verified PrusaSlicer wiki page explicitly says the page
  is no longer maintained and recommends using local `--help` for the current
  interface. Defer automation until local CLI help, K1/ASA profiles, and G-code
  policy are verified.
- CuraEngine: Verified developer docs identify it as Cura's back-end slicer and
  document the slicing pipeline and G-code export topic. Defer direct engine
  automation until complete local printer/material settings are verified.
- Three.js and glTF Transform: Verified docs support future web preview
  research, GLTFLoader use, and glTF inspection/optimization. Defer public GLB
  previews until assets, size budget, and public-release approval are decided.
- Autodesk Platform Services Fusion Automation: Verified APS docs describe a
  Fusion Automation API, but this repo keeps the cloud path deferred until the
  user explicitly provides credentials/PAT and requests cloud workflow design.
- FreeCAD CLI/API: Official FreeCAD wiki pages were not accessible in this
  browser session because the site returned an access-denied page. Do not add a
  FreeCAD candidate record until official docs or local CLI behavior are
  directly verified.
- OrcaSlicer CLI: Current official CLI behavior was not directly verified from a
  primary source in this session. Do not add an automation record until official
  docs or local `--help` output are captured.

## Storage And Validation Decisions

- Structured tooling records live under `3d-print-work/data/tooling/` using
  schema `cbbs-cad/tooling-candidate/v1`.
- Every record must cite verified source refs and at least one internal-review
  rationale locator.
- Candidate tools must not include install commands unless they are already a
  baseline direct dependency.
- Transitive dependencies, including `manifold3d` and `vtk`, are not direct
  import surfaces unless promoted by a later direct dependency decision.
- Slicer records must keep `gcode_generation_allowed: false`.
- Generated evaluation outputs, if later approved, must stay under
  `3d-print-work/generated/tool-evals/`.

## Source URLs

- CadQuery import/export: https://cadquery.readthedocs.io/en/latest/importexport.html
- trimesh: https://trimesh.org/index.html
- Autodesk Fusion ExportManager execute: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ExportManager_execute.htm
- Autodesk Fusion STEP export options: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ExportManager_createSTEPExportOptions.htm
- Autodesk Fusion STL export options: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ExportManager_createSTLExportOptions.htm
- Autodesk Fusion viewport capture: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Viewport_saveAsImageFile.htm
- OpenCV VideoCapture: https://docs.opencv.org/4.x/d8/dfe/classcv_1_1VideoCapture.html
- Pillow: https://pillow.readthedocs.io/en/stable/
- Microsoft UI Automation: https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-uiautomationoverview
- Python MSS: https://python-mss.readthedocs.io/stable/
- pywinauto: https://pywinauto.readthedocs.io/en/latest/
- pywinauto getting started: https://pywinauto.readthedocs.io/en/latest/getting_started.html
- Blender command-line rendering: https://docs.blender.org/manual/en/latest/advanced/command_line/render.html
- Blender render operators: https://docs.blender.org/api/current/bpy.ops.render.html
- build123d: https://build123d.readthedocs.io/en/stable/index.html
- Open3D: https://www.open3d.org/docs/release/
- Open3D mesh tutorial: https://www.open3d.org/docs/release/tutorial/geometry/mesh.html
- PyVista docs: https://docs.pyvista.org/
- PyVista overview: https://pyvista.org/
- manifold3d: https://pypi.org/project/manifold3d/
- PrusaSlicer CLI: https://github.com/prusa3d/PrusaSlicer/wiki/Command-Line-Interface
- CuraEngine: https://ultimaker.github.io/CuraEngine/
- Three.js loading 3D models: https://threejs.org/manual/en/loading-3d-models.html
- glTF Transform CLI: https://gltf-transform.dev/cli
- Autodesk Platform Services Automation APIs: https://aps.autodesk.com/automation-apis
