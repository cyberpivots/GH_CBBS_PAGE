# Concept Brief: Gateway And Sensor Case

Truth state: concept / hardware TBD.

## Goal

Prepare a placeholder enclosure family for future agriculture gateway and sensor hardware without inventing dimensions or capabilities.

## Verified Inputs

- Current public CBBS content identifies agriculture-facing records, review desks, advisory analysis, and guarded gateway integration.
- Current public CBBS content names Modbus, MQTT, HTTP, and normalized CBBS records as interface roles.
- Current public CBBS content does not select a specific gateway board or sensor board.

Source:
- `src/content/systems/agriculture-runtime.md`

## Variants

- `gateway-wall-box`: future wall-mounted gateway enclosure.
- `sensor-node-box`: future local sensor-node case.
- `cable-entry-coupon`: cable gland, strain-relief, and label test piece.
- `din-adapter`: future DIN rail or panel adapter if hardware and mounting justify it.

## Required Features After Hardware Selection

- Board-specific mounting.
- Power entry and polarity/service labeling.
- Cable glands or strain relief matched to real cable diameters.
- Service access for reset, programming, logs, and connectors.
- Mounting appropriate to the installed location.
- Separation between advisory/record hardware and any guarded control interface.

## Blockers Before CAD

- Exact gateway/sensor board model.
- Sensor interface hardware.
- Cable count, cable diameter, and connector types.
- Power method.
- Indoor/outdoor/environmental target.
- Mounting surface and service access requirements.

## Boundaries

- Do not model a dimensioned gateway enclosure before hardware is selected.
- Do not claim autonomous irrigation control or live relay, valve, or pump execution.
- Do not claim environmental protection without a selected rating target and validation plan.
