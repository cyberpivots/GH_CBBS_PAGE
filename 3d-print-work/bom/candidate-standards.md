# Candidate BOM Standards

Truth state: internal review / concept.

This file lists candidate standards to keep future prototypes consistent. Nothing here is final until hardware is measured and a concept revision passes validation.

## Fasteners

Candidate families:
- M2 for small board/display accessory screws.
- M2.5 for small electronics standoffs where board holes support it.
- M3 for larger enclosure screws, wall tabs, and panel hardware.

Rules:
- Match screw size to actual board/display holes and vendor drawings.
- Use one primary screw family per enclosure when practical.
- Use stainless hardware only when corrosion resistance is needed and RF/mechanical impact is acceptable.
- Do not drive screws into plastic for repeated-service parts unless intentionally validated.

## Inserts

Candidate approach:
- Heat-set inserts for repeated service lids and mounting points.
- Direct plastic screws only for early fit checks or low-service prototypes.

Rules:
- Select an insert manufacturer and part number before boss CAD.
- Use the insert datasheet for hole diameter, depth, wall thickness, and installation temperature.
- Print an insert coupon in the exact material before using inserts in a full case.

## Gaskets And Seals

Candidate approach:
- Use foam or elastomer only after a weather/dust target is defined.
- Use gasket groove coupons before full enclosure work.
- Use the rugged gasket-flange and drip-lip seam coupons before modeling a
  two-piece outdoor-facing enclosure.

Rules:
- No waterproof, dustproof, or IP-rated claims without a rating target and validation plan.
- Do not add seals that trap heat or block service access without thermal testing.
- Do not treat a printed gasket groove as a validated seal until the gasket
  material, fastener torque, service-cycle behavior, and print material are
  physically checked.

## Cables And Strain Relief

Candidate items:
- USB cable clamp.
- Antenna cable relief.
- XH2.54 display harness relief.
- Gateway cable gland after cable diameter is known.
- Cable-entry boss coupon for gland/strain-relief clearance checks before
  enclosure integration.

Rules:
- Measure actual cable outer diameter and bend radius.
- Test with the actual cable and connector installed.
- Leave service loops where field replacement is expected.
- Do not model gland threads or final boss thickness until a gland or strain
  relief part number is selected.

## Materials

Candidate path:
- PLA for fit cards, coupons, and first visual tests.
- PETG for functional indoor prototypes.
- ASA for outdoor-facing prototypes only when printer ventilation and enclosure conditions support it.
- PC-class materials only after printer capability and safety controls are confirmed.

Rules:
- Material choice does not prove field suitability.
- Record material, manufacturer, color, nozzle, layer height, wall count, infill, orientation, and supports for every prototype.

## Rugged Outdoor Prototype Defaults

Candidate approach:
- Start with 3.0 mm wall-section coupons, reinforced ribs, mount-tab coupons,
  gasket-flange coupons, drip-lip seam coupons, and cable-entry boss coupons.
- Use the coupons to tune print orientation, wall count, fastener behavior,
  gasket seating, and cable clearance before full enclosure work.

Rules:
- Rugged/outdoor wording describes prototype intent only.
- Do not claim NEMA, IP, IK, field readiness, or production durability from a
  generated model or material name.
- Record physical tests before promoting any geometry out of
  `3d-print-work/generated/`.
