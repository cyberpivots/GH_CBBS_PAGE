# P070 Structural Strengthening Findings

Truth state: internal review.

This note records the source basis for reinforcing the generated
`p070_hinged_wall_enclosure` and
`p070_heltec_outdoor_controller_enclosure` CAD assemblies. It is not public
product copy and does not approve any weather, ingress, impact, runtime, RF
range, or field-readiness claim.

## Verified Design Basis

- Prusa's FDM modeling guidance supports designing walls, ribs, chamfers,
  orientation, split parts, and clearances around the actual nozzle and
  material process. The existing CBBS K1/ASA path uses 3.2 mm walls and shallow
  ribs as review geometry, not release-approved structure.
- Prusa's ASA guidance supports ASA as an outdoor-facing prototype material, but
  it also keeps warping, ventilation, fumes, and large-part process control in
  review. ASA material selection alone is not a strength, weather, or service
  claim.
- The Creality K1-class record keeps the constrained build volume at
  220 x 220 x 250 mm. The current P070 K1 component margin is tight, so
  strengthening must stay inside the existing part X/Y envelopes.
- The Nextion NX8048P070-011C drawing provides the verified P070 outsize,
  active/LCD areas, and 174.6 x 101.6 mm mounting-hole spans. Boss placement may
  use those coordinates, while printed pilot behavior remains physical-print
  validation.
- The Heltec V2 and Pololu regulator source records provide board envelopes,
  not verified mounting-hole locations. Alignment rails and stops may clarify
  placement, but screw-hole claims remain blocked until the physical boards are
  measured.
- CadQuery supports exporting STEP/STL review solids from the generated model
  path, and trimesh supports mesh inspection including watertightness and broken
  face checks. These are export and inspection gates, not field validation.
- Autodesk Fusion Animation and Drawing workspaces are the correct native place
  for exploded views, callouts, trails, 2D drawings, dimensions, and assembly
  documentation. Generated solid arrows or text callouts in CadQuery are not a
  substitute for Fusion-native documentation.
- Heat-set insert suppliers publish insert-specific hole, depth, tooling, and
  material guidance. McMaster and Tappex-style references support deferring
  insert holes until a specific insert part number, material, and installation
  method are selected.

## CAD Placement Rules

- Keep the existing 5-knuckle hinge pattern, hinge pin diameter, bore diameter,
  print flat, and end chamfer.
- Add tray-owned reinforcement only to tray-owned hinge knuckles and door-owned
  reinforcement only to door-owned knuckles. Pads and webs must remain inside
  the existing hinge barrel bounds and must not bridge the alternating owners.
- Use rounded root saddles, rounded load-spreader rails, and chamfered triangular
  webs at the hinge root to reduce sharp stress transitions while preserving the
  existing hinge owner pattern and K1 X/Y bounds.
- Add rear-panel floor ribs, display-boss webbing, and inner perimeter rails
  using existing wall and ASA rib parameters.
- Add front-door edge and corner reinforcement outside the display window only.
  Do not cover the P070 active/LCD window.
- Add rear-pod floor ribs and side-wall ledges inside the existing pod envelope.
  Re-cut battery strap slots after rib additions so the slots remain visible in
  the review mesh.
- Prefer capsule-profile ribs, rounded route nodes, and chamfered cable-entry
  saddle webs over square-ended rectangular ribs where the resulting mesh remains
  watertight and print-package bounds remain accepted.
- Use alignment rails/stops for battery, Heltec, regulator, and RF route. Do not
  model Heltec or regulator screw holes as verified features.
- Keep component-level K1 plates limited to `rear_panel_core`,
  `rear_battery_pod`, and `front_display_door`. Keep monolithic or combined K1
  plates blocked.

## Remaining Blockers

- Physical ASA print and slicer review for every reinforced component.
- Hinge cycling, hinge pin retention, and door-open service handling.
- Fastener pullout, printed pilot behavior, and any future heat-set insert
  selection.
- Display, Heltec, regulator, battery, cable, SMA, RF, heat, and service
  validation with the actual parts.
- Condensation, venting, gasket, drip-lip, UV, weather, dust, impact, and field
  validation before any environmental or readiness claim.

## Sources

- Prusa FDM modeling guidance: https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135/
- Prusa ASA material guidance: https://help.prusa3d.com/article/asa_1809
- Creality K1 flagship series comparison: https://www.creality.com/compare/compare-k1-flagship-series/
- Nextion NX8048P070-011C dimension drawing: https://cdn.nextion.tech/wp-content/uploads/2022/03/NX8048P070-011C_dimension.pdf
- Heltec WiFi LoRa 32 V2 product page: https://heltec.org/project/wifi-lora-32v2/
- Heltec WiFi LoRa 32 V2 PDF: https://resource.heltec.cn/download/WiFi_LoRa_32/WiFi%20Lora32.pdf
- Pololu S13V30F5 product page: https://www.pololu.com/product/4082
- CadQuery import/export documentation: https://cadquery.readthedocs.io/en/latest/importexport.html
- trimesh documentation: https://trimesh.org/trimesh.html
- Autodesk Fusion Animation overview: https://help.autodesk.com/cloudhelp/ENU/Fusion-Animate/files/GUID-25E6D2E0-8057-4BFF-93B3-E7AEE2C4404A.htm
- Autodesk Fusion Drawings: https://help.autodesk.com/view/fusion360/ENU/?contextId=DRAWINGS-CREATE-FROM-DESIGN-CMD
- McMaster heat-set inserts: https://www.mcmaster.com/products/heat-set-inserts
- Tappex threaded inserts for 3D printed products or prototypes: https://www.tappex.co.uk/threaded-inserts-for-3d-printed-products-or-prototypes/
