# Fusion Assembly Documentation

This repo should prepare Fusion-ready components and handoff notes, then use
Fusion's native Animation and Drawing workspaces for assembly instructions. Do
not generate CadQuery arrows, text, or callout solids as substitutes for Fusion
animation or drawings.

## Animated Assembly Method

Use the generated Fusion job to import named components, then build storyboards
inside Fusion's Animation workspace.

Recommended storyboards for the P070 enclosure:

1. `P070 component print disassembly`: shows the print split into
   `rear_panel_core`, `rear_battery_pod`, and `front_display_door`.
2. `P070 final assembly`: starts from the separated print components, inserts
   hardware references, then returns parts to their home positions.
3. `P070 service access`: shows the door opening, hinge pin path, display
   reference, cable gland reference, battery reference, board reference, and RF
   pigtail path as inspection-only references.

Use native storyboard actions:

- Move the playhead before each step and use `Transform Components` or
  `Manual Explode` for controlled part motion.
- Keep the battery/electronics pod as a +Y sidecar connected to the rear panel;
  only the connector tongue should overlap the display enclosure footprint.
- Use `Restore Home` to show the final assembled state without changing Design
  workspace positions.
- Use `Show/Hide` and appearance overrides to focus each step.
- Use `Create Callout` for notes attached to components or hardware references.
- Enable trail lines for exploded views that will be reused in drawings.
- Use `Publish Video` for review videos after the storyboard is approved.

## 2D Drawing Method

Use Fusion's Drawing workspace to document the same design and storyboards.

Recommended sheets:

1. Assembly exploded sheet from `Drawing > From Animation`, using the approved
   storyboard at its final exploded position.
2. Assembly closed sheet from `Drawing > From Design`, with isometric,
   orthographic, section, and detail views.
3. Component sheets for `rear_panel_core`, `rear_battery_pod`, and
   `front_display_door`, created from selected components/bodies.
4. Reference hardware sheet for inspection-only envelopes:
   `display_reference`, `hinge_pin`, `m12_gland_reference`,
   `heltec_v2_reference`, `lifepo4_battery_reference`,
   `buckboost_regulator_reference`, `sma_bulkhead_reference`,
   `antenna_keepout_reference`, and `wire_channel_reference`.

Use native Drawing tools:

- Base, projected, section, detail, and break views for geometry.
- Dimensions, ordinate dimensions, center marks, center lines, text, and leaders
  for measurements and notes.
- Parts lists and balloons for assembly and storyboard references.
- Templates and placeholder views/tables when a reusable CBBS drawing style is
  needed.
- Export PDF for review packets; export DWG/DXF only when a downstream CAD
  workflow needs 2D geometry.

## Automation Boundary

Repo automation may create:

- Named STEP/STL parts and assembly-layout review files.
- Fusion job JSON for import, render, and export.
- Print packages and generated handoff notes under `3d-print-work/generated/`.

Repo automation must not:

- Create fake assembly-instruction geometry.
- Treat generated renders as native Fusion storyboards.
- Claim the model has native Fusion assembly documentation until a storyboard
  or drawing is created in Fusion and reviewed.

Native storyboard and drawing authoring should stay in Fusion UI/manual review
until an explicit, tested Fusion-side automation path is added.

## Autodesk References

- Animation workspace overview: storyboards, actions, visibility, callouts, and
  view actions are native animation constructs.
  https://help.autodesk.com/cloudhelp/ENU/Fusion-Animate/files/GUID-25E6D2E0-8057-4BFF-93B3-E7AEE2C4404A.htm
- Animation transformations: `Transform Components`, `Restore Home`,
  `Auto Explode`, `Manual Explode`, `Show/Hide`, and appearance overrides.
  https://help.autodesk.com/cloudhelp/ENU/Fusion-Animate/files/ANI-TRANSFORM.htm
- Animation callouts: callouts can be attached to geometry and follow component
  transforms.
  https://help.autodesk.com/view/fusion360/ENU/?contextId=ANI-CALLOUT-CREATE
- Publish animation video:
  https://help.autodesk.com/cloudhelp/ENU/Fusion-Animate/files/GUID-5C687D49-7714-469F-A8CA-FA0C5A89F823.htm
- Drawings from design and animation:
  https://help.autodesk.com/view/NINVFUS/ENU/?guid=GUID-54D1504C-8885-4EF7-A60E-8E3B902A2632
- Drawing workspace reference:
  https://help.autodesk.com/cloudhelp/ENU/Fusion-Drawing/files/DWG-REF-DRAWING-TAB.htm
- Parts lists and balloons:
  https://help.autodesk.com/view/fusion360/ENU/?contextId=DWG-PARTS-LIST
- Drawing automation and auto dimensions:
  https://help.autodesk.com/view/fusion360/ENU/?contextId=DWG-AUTO-DRAWING
- Drawing export:
  https://help.autodesk.com/view/fusion360/ENU/?contextId=DWG-EXPORT
