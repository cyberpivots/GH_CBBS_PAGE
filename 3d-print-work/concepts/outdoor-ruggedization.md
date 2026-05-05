# Concept Brief: Outdoor Ruggedization Test Artifacts

Truth state: internal review / concept.

## Goal

Create print-test artifacts that improve the next CBBS enclosure iterations for
outdoor-facing and reinforced use without claiming a certified environmental or
impact rating.

## Verified Design Context

- NEMA enclosure type documents describe outdoor enclosure categories, but CBBS
  printed prototypes do not carry a NEMA type claim.
- IEC 60529 defines IP-code enclosure protection classification, but CBBS printed
  prototypes do not carry an IP claim.
- IEC 62262 defines IK-code mechanical impact classification, but CBBS printed
  prototypes do not carry an IK claim.
- ASA is suitable for outdoor technical parts when printing conditions and
  ventilation support it. PETG remains useful for many interior and exterior
  mechanical prototypes below its temperature limits.
- Printed enclosure geometry should be validated with the actual hardware,
  cables, fasteners, gasket material, print material, orientation, and service
  cycle before being promoted beyond fit-test status.

## Prototype Artifacts

- Wall-section coupon for wall thickness, ribs, corner radius, and material
  behavior.
- Gasket-flange coupon for gasket seat geometry and screw spacing checks.
- Drip-lip seam coupon for rain-shedding geometry and fit checks.
- Cable-entry boss coupon for cable clearance, strain relief, and future gland
  candidate checks.
- Reinforced mount-tab coupon for wall/panel mounting and fastener tear-out
  checks.
- P070 rugged bezel fit frame for display-facing reinforcement and service
  clearance checks.
- Heltec V2 rugged tray gauge for board-envelope clearance and reinforced tray
  fit checks.

## Blockers Before Full Outdoor Cases

- Select exact hardware and confirm physical measurements.
- Select target material, slicer profile, print orientation, wall count, and
  infill.
- Select gasket material and compression target.
- Select cable diameter, connector, bend radius, and strain-relief hardware.
- Select mounting surface and fastener standard.
- Run physical fit, thermal, condensation, cable pull, fastener cycling, and
  ingress-oriented smoke tests before any protection claim.

## Boundaries

- Do not publish generated CAD, renders, or previews from these artifacts without
  public-release review.
- Do not describe these artifacts as sealed, certified, production-ready, or
  field-qualified.
- Do not model a full hub, gateway, agriculture sensor, or Heltec case until the
  exact hardware and measurements are recorded.

Sources:
- https://www.nema.org/docs/default-source/products-document-library/nema-enclosure-types.pdf
- https://webstore.iec.ch/en/publication/2447
- https://webstore.ansi.org/preview-pages/IEC/preview_iec62262%7Bed1.1%7Db.pdf
- https://help.prusa3d.com/article/asa_1809
- https://help.prusa3d.com/article/petg_2059
- https://www.hubs.com/knowledge-base/enclosure-design-3d-printing-step-step-guide/
- https://discover.parker.com/Parker-ORing-Handbook-ORD-5700
- https://www.gore.com/products/screw-protective-vents-outdoor-electronics-enclosures
