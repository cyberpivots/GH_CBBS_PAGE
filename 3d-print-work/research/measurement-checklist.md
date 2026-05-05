# Measurement Checklist Before CAD

Truth state: internal review / concept.

Use this checklist before creating a dimensioned enclosure model. Record measurements in a concept-specific notes file and keep original photos with scale references.

## Tooling

- Digital calipers.
- Metric ruler or scale card for photos.
- Camera with top, bottom, side, connector, and angled views.
- Printed square/grid reference for distortion checks.
- Small probe or pin gauge for hole checks, if available.

## Shared Board Measurements

- Board length, width, thickness, and corner radius.
- Mounting hole diameter, plated/non-plated status, and center coordinates from one fixed origin.
- Top-side tallest component and height above PCB.
- Bottom-side tallest component and clearance requirement.
- Connector dimensions, protrusion past board edge, cable plug overhang, and bend direction.
- Button positions, required actuation clearance, and whether buttons need external access.
- Header population, pin height, shroud height, and side clearance.
- Heat-generating components that must not touch plastic.
- Label zones and serial/QR label visibility.

## Heltec Node Measurements

- Exact board revision markings.
- Micro USB connector location and required cable insertion envelope.
- Reset and program button locations.
- OLED active area, visible bezel area, and display-to-board-edge coordinates.
- LoRa antenna connector location, antenna type, bend radius, and strain-relief need.
- 2.4 GHz antenna location and required plastic clearance.
- Battery connector position, battery cable exit, and battery envelope if battery is enclosed.
- Header population and whether future sensor wiring exits the case.
- Any microSD module or storage accessory actually installed in the CBBS build.

## Raspberry Pi Hub Measurements

- Exact Raspberry Pi model and board revision.
- Installed HATs, coolers, fans, radio heads, cables, or storage devices.
- Required access to USB, Ethernet, power, HDMI, microSD, GPIO, camera/display connectors, fan connector, and power button.
- Clearance for active cooler or heatsink, including intake and exhaust path.
- Cable insertion/removal envelope for every connected cable.
- Mounting orientation: desk, shelf, wall, panel, or DIN accessory.

## P070 / Nextion Measurements

- Exact model number printed on display or PCB.
- Front glass/touch outline, LCD outline, active area, PCB outline, and total thickness.
- Mount hole locations and diameter.
- Rear component heights and cable connector envelope.
- Cable exit direction for XH2.54 4P harness.
- Service access for firmware/design updates and any optional accessory port actually used.
- Bezel overlap allowed without covering active display or touch-critical region.

## Gateway/Sensor Measurements

Do not start dimensioned work until hardware is selected.

When hardware exists, capture:
- Board and enclosure-target dimensions.
- Cable count, cable diameter, gland/thread requirements, and strain relief.
- Sensor connector type and service loop.
- Power connector type and polarity labeling requirements.
- Mounting surface, expected handling, and environmental exposure.

## Outdoor And Rugged Prototype Measurements

Record these before moving from coupons or fit frames to an enclosure:

- Intended exposure: indoor, sheltered outdoor, direct rain path, dust path,
  sunlight, freeze/thaw, and handling expectations.
- Material, color, slicer profile, wall count, infill, orientation, and support
  strategy.
- Gasket material, uncompressed thickness, target compression, groove geometry,
  screw spacing, and torque method.
- Fastener family, insert part number, boss dimensions, mount-tab thickness, and
  mounting surface.
- Cable outer diameter, connector body size, bend radius, service loop, strain
  relief, and gland or clamp part number if selected.
- Vent or pressure-equalization hardware part number if selected.
- Expected heat sources, airflow path, and measured temperatures with the real
  electronics installed.
- Drop, pull, service-cycle, and bench ingress-oriented checks attempted, with
  pass/fail notes and photos.

## Photo Set

For each hardware item, capture:
- Top view with scale.
- Bottom view with scale.
- All four sides with connector/cable installed.
- Oblique view showing tallest components.
- Close-up of antenna, buttons, display, and power entry.
- Assembled test configuration matching intended CBBS use.
