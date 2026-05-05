# P070 Futuristic Surface Reinforcement Findings

Truth state: internal review.

This note records the source basis for adding visible surface contours,
macro-texture ribs, and raised CBBS marking to the
`p070_heltec_outdoor_controller_enclosure` CAD concept. It is not public product
copy and does not approve any weather, ingress, impact, runtime, RF range, or
field-readiness claim.

## Verified Design Basis

- Use macro-scale ribs and contours, not fine decorative texture. Prusa's FDM
  modeling guidance ties printability to nozzle diameter, extrusion width,
  orientation, overhangs, and material behavior, and warns that outdoor or
  mechanically strained parts may need to avoid small details.
- The current K1-series CAD process records a 0.4 mm nozzle reference. Prusa's
  FDM guidance gives an approximate 0.45 mm extrusion width for a 0.4 mm nozzle
  and says walls thinner than one perimeter are not printable. Raised contours
  and ribs are therefore kept well above a single perimeter.
- Xometry's FDM guide recommends supporting walls in the 1.2 to 1.5 mm range,
  recommends protruding text thickness and height of at least 1 mm, and gives
  1.5 mm as a safe minimum rib thickness. The selected relief and rib values
  are review defaults that remain blocked until printed.
- eFunda's plastic rib guidance says ribs increase bending stiffness by
  increasing moment of inertia, recommends rib thickness below nominal wall
  thickness, and says multiple ribs are preferable to one high rib. The surface
  treatment uses several shallow ribs instead of a tall decorative fin.
- Prusa's ASA guidance supports ASA as an outdoor-facing prototype material due
  to UV and temperature resistance, but it also documents warping, ventilation,
  fumes, and large-part enclosure constraints. Material choice alone does not
  create a CBBS outdoor rating.
- Gore's outdoor electronics venting guidance supports keeping condensation and
  pressure equalization as a design-review item for sealed electronics.
  Surface contours must not block future vent placement or vent review.
- NEMA enclosure type references describe outdoor enclosure categories, but this
  concept does not claim any NEMA, IP, IK, waterproof, dustproof, weatherproof,
  or field-qualified rating.
- CadQuery 2.7.0 documents `Workplane.text` for adding raised text to a solid.
  The repo does not include Space Grotesk or Inter font files, so the CAD
  marking uses the approved public CBBS brand text with a deterministic local
  font fallback and records exact brand-font reproduction as blocked.

## Selected CAD Defaults

- Front contour rails: 1.8 mm wide x 1.2 mm raised, offset at least 3.0 mm from
  the display window.
- Rear pod macro ribs: 1.8 mm wide x 1.2 mm protrusion, 18.0 mm nominal pitch.
- Raised CBBS text: 10.0 mm font size x 1.2 mm relief.
- Raised brand icon badge: 14.0 mm reference diameter x 1.2 mm relief, recreated
  from simple circle and line primitives visible in the approved public CBBS
  SVG assets.

## CAD Placement Rules

- Keep all raised front-door features outside the P070 display window and away
  from the hinge/latch envelope.
- Keep rear pod rib protrusions within the existing P070 tray X/Y envelope so
  K1 split-plate strategy remains valid.
- Keep RF antenna, SMA boss, cable channel, gasket/drip-lip references, battery
  service bay, and regulator/Heltec alignment aids clear of surface treatment
  features.
- Treat all surface features as prototype print-review geometry until actual
  ASA samples are printed and checked for readability, warping, handling, edge
  feel, service access, and mesh/export quality.

## Blockers

- Print the front door and rear pod sections in the intended material and
  orientation before accepting the relief heights.
- Confirm raised text remains readable after slicing, support strategy, and any
  post-processing.
- Confirm macro ribs do not interfere with wall mounting, service handling,
  cable entry, vent placement, or cleaning.
- Confirm brand typography if exact Inter or Space Grotesk reproduction is
  required in CAD; those font files are not present in this repository.

## Sources

- Prusa FDM modeling guidance: https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135/
- Prusa ASA material guidance: https://help.prusa3d.com/article/asa_1809
- Xometry FDM mini-guide: https://www.xometry.com/resources/3d-printing/mini-guide-fdm-3d-printing/
- eFunda rib design guidance: https://www.efunda.com/designstandards/plastic_design/ribs.cfm
- Gore screw-in vents for outdoor electronics: https://www.gore.com/products/screw-protective-vents-outdoor-electronics-enclosures
- NEMA enclosure types: https://www.nema.org/docs/default-source/products-document-library/nema-enclosure-types.pdf
- CadQuery text API documentation: https://cadquery.readthedocs.io/en/stable/classreference.html
- Approved CBBS brand assets: `src/data/cbbs-assets.json` and `public/assets/brand/logo-primary.svg`
