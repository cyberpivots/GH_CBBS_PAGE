# Research Plan For CBBS 3D-Printed Enclosures

## Objective
Develop a public-safe, repeatable process for rapid enclosure concepts that can move from paper requirements to fit-test prints, validated prototypes, and future field-ready designs.

## Phase 1: Hardware Confirmation
- Confirm exact Raspberry Pi model and download official mechanical drawings.
- Confirm Heltec WiFi LoRa32 V2 board revision, antenna connector/location, OLED position, USB port, button access, and header population.
- Confirm display module model for P070 concepts and collect official panel dimensions.
- Identify any gateway/sensor boards before modeling gateway enclosures.
- Photograph and measure actual hardware with calipers before CAD.

## Phase 2: Enclosure Families
- `node-case`: handheld or wall-mount Heltec node case with OLED window and antenna routing.
- `hub-case`: Raspberry Pi hub case or radio-head accessory case with ventilation and service access.
- `display-panel`: Nextion/P070 bezel or desktop/wall display case.
- `gateway-case`: sensor/gateway enclosure once hardware is selected.
- `test-fixtures`: programming, SD-writing, display alignment, and assembly jigs.

## Phase 3: Rapid Prototype Method
- Start with simple bounding-box CAD using verified board outlines and connector keepouts.
- Print fit-test frames before full cases.
- Print coupons for screw bosses, heat-set inserts, snap tabs, gasket grooves, and cable glands.
- Use parametric dimensions for board clearances, wall thickness, standoff height, and fastener sizes.
- Keep print logs with material, layer height, nozzle size, orientation, support strategy, and fit result.

## Phase 4: Design Constraints To Research
- Thermal airflow for Raspberry Pi hub cases and enclosed electronics.
- RF and antenna clearance for LoRa/Wi-Fi field nodes.
- OLED and P070 screen visibility, bezel depth, glare, and lens material.
- Cable strain relief for USB, power, antenna, and sensor wiring.
- Field mounting: wall, pole, DIN rail, magnetic, screw tabs, and lanyard options.
- Serviceability: tool access, reset/program buttons, SD access, battery access, and label placement.
- Material choice: PLA for fit tests; PETG/ASA/PC-class materials for heat, outdoor, or mechanically stressed prototypes after printer capability is confirmed.

## Phase 5: Validation
- Fit check with actual boards, cables, antennas, and displays installed.
- Thermal check under realistic hub/node workload before claiming field suitability.
- RF smoke check with final antenna routing and case material.
- Drop/handling check for field-node prototypes.
- Assembly check: repeatability, screw engagement, insert retention, and service access.
- Documentation check: every printable file has source CAD, export date, material recommendation, and revision notes.

## Decisions Deferred
- Exact CAD toolchain.
- Exact printer model and slicer.
- Exact enclosure materials.
- Weather resistance targets.
- Fastener system and insert standard.
- Public release license for printable files.

Do not fill these decisions with assumptions. Record evidence and rationale in `research/sources.md` or concept notes before modeling around them.
