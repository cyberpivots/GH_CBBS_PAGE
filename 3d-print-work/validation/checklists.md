# Validation Checklists

Truth state: internal review / concept.

Use these checklists before labeling any enclosure prototype as fit-checked, functional, or ready for public release.

## Fit Check

- Exact hardware model and revision recorded.
- Board/display installs without force.
- Mounting holes align without bending the board.
- Tallest top and bottom components clear the enclosure.
- Connectors are reachable with actual cables.
- Cables can bend without sharp stress.
- Buttons, reset/program controls, and service openings are reachable.
- OLED/P070 viewing area is not blocked.
- Antenna path is not pinched.
- Lid closes without compressing electronics.

## Assembly Check

- Fasteners engage consistently.
- Inserts, if used, are square and retained.
- No loose plastic strands or debris remain inside.
- Assembly order is documented.
- Disassembly does not damage the board, display, antenna cable, or harness.
- Labels remain visible after assembly.

## Thermal Check

- Test workload is documented.
- Ambient temperature is recorded.
- Enclosure orientation is recorded.
- Temperature readings are recorded before, during, and after workload.
- Case surface hot spots are noted.
- Fan/heatsink airflow is not blocked.
- No thermal claim is made unless the test supports it.

## RF Smoke Check

- Antenna model and placement are recorded.
- Case material and wall thickness around the antenna are recorded.
- Baseline test outside the case is recorded.
- Test inside the final case configuration is recorded.
- Antenna cable strain relief is checked after opening/closing the case.
- No range or reliability claim is made from a single smoke test.

## Display Check

- OLED/P070 content is readable from intended angle and distance.
- Bezel does not cover critical screen content.
- Touch edges work on P070 prototypes, if touch is used.
- Glare, lens, and dust behavior are noted.
- Display cable remains secure after handling.

## Field Handling Check

- Mounting feature supports intended orientation.
- Cable exits point in a defensible direction for service and drip management.
- Case survives normal hand handling without creaks, cracks, or fastener pullout.
- Edges are not sharp.
- Labels and public-safe markings are readable.
- Weather, dust, UV, and impact claims remain omitted unless separately validated.

## Rugged Outdoor Prototype Check

- Rugged/outdoor label is recorded as prototype intent only.
- Wall-section coupon has been printed in the intended material and orientation.
- Gasket-flange or drip-lip coupon has been checked before adding seam geometry
  to a full enclosure.
- Cable-entry boss has been tested with the actual cable and connector.
- Mount-tab coupon has been tested with the intended fastener and surface.
- Condensation, pressure equalization, and thermal behavior are documented.
- No environmental or impact rating claim appears in CAD manifests, public copy,
  renders, or release notes unless separately validated and approved.

## Release Check

- Source CAD is present.
- STEP export is present for a fit-checked revision.
- Print file or 3MF project is present for the printed revision.
- Prototype log is complete.
- BOM candidates are listed.
- Known risks and limitations are documented.
- Public copy uses the correct truth-state label.
- No private implementation details, credentials, logs, board internals, or private repo paths are included.
