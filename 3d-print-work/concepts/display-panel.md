# Concept Brief: P070 Display Panel

Truth state: concept / prototype display surface.

## Goal

Create a panel, bezel, and desktop/wall display enclosure family for P070 prototype controller screens.

## Verified Inputs

- Current public CBBS content labels P070 captures as prototype controller screens unless explicitly labeled as current system interfaces.
- ITEAD identifies NX8048P070-011C as a 7.0-inch capacitive Intelligent Series HMI touchscreen without enclosure.
- ITEAD lists 800 x 480 resolution, DC 5 V 1 A input power, and XH2.54 4P USART port.
- The NX8048P070-011C drawing is in millimeters with +/- 0.2 mm tolerance and includes front outsize, LCD outsize, and active area dimensions.

Sources:
- `src/content/systems/display-surfaces.md`
- `src/content/media/p070-home.md`
- `src/content/media/p070-rooms.md`
- `src/content/media/p070-files.md`
- https://itead.cc/product/7-0-nextion-intelligent-series-hmi-resistivecapacitive-touch-display-without-enclosure/
- https://cdn.nextion.tech/wp-content/uploads/2022/03/NX8048P070-011C_dimension.pdf

## Variants

- `p070-fit-frame`: flat dimensional fit template.
- `p070-bezel`: front bezel with display opening and mounting points.
- `p070-desktop`: angled desk stand for demo and lab use.
- `p070-wall-panel`: wall/panel mount after cable path is confirmed.
- `p070-hinged-wall-enclosure`: measurement-gated wall/panel enclosure with a
  left-hinged front display-bezel door, symmetric removable-pin hinge,
  snap-latch placeholder, bottom M12 gland reference, and assembly-style render
  outputs for local Fusion review.

## Required Features

- Display opening based on active area and LCD outsize.
- Bezel overlap that does not block active touch/display area.
- Mounting holes matched to the official drawing and measured hardware.
- XH2.54 4P cable exit with strain relief.
- Rear service clearance.
- Hinged front service access that does not imply weather sealing.
- Label area that clearly marks prototype display status.

## Blockers Before CAD

- Confirm exact physical display model.
- Confirm front/rear orientation and cable exit direction.
- Confirm whether any speaker, IO board, SD extender, or other accessory is installed.
- Confirm mounting target: demo stand, wall panel, bench fixture, or field case.
- Select and measure bottom cable gland or strain-relief hardware.
- Select hinge pin stock and validate snap-latch tolerance in the intended material.

## Prototype Sequence

1. Print flat fit frame from official dimensions.
2. Verify active area, LCD outsize, mount holes, and cable direction.
3. Print front bezel only.
4. Add rear cover and stand/wall features after fit passes.
5. Add hinged wall enclosure only after measured rear/cable/hinge/latch inputs exist.
6. Run display visibility, touch edge, cable strain, hinge, latch, and assembly checks.

## Boundaries

- Do not describe P070 as a current production interface.
- Do not claim weather resistance or field ruggedness.
