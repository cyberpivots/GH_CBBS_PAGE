# Concept Brief: Raspberry Pi Hub Case

Truth state: concept.

## Goal

Create an enclosure family for the CBBS hub once the exact Raspberry Pi model and attached radio-head hardware are confirmed.

## Verified Inputs

- Current public CBBS content identifies the Raspberry Pi hub as the durable coordinator, archive, scheduler, browser operator surface, and radio-head attachment point.
- Raspberry Pi publishes model-specific mechanical drawings and, for Raspberry Pi 5, an official STEP file.
- Raspberry Pi documentation identifies model-specific power recommendations and active-cooling guidance.

Sources:
- `src/content/systems/pi-hub.md`
- https://www.raspberrypi.com/documentation/computers/raspberry-pi.html
- https://datasheets.raspberrypi.com/rpi5/raspberry-pi-5-mechanical-drawing.pdf

## Variants

- `bench-hub`: open-lid lab case with high service access.
- `vertical-hub`: vertical airflow case for shelf or wall use.
- `hub-radio-accessory`: separate radio-head carrier or bracket after radio hardware is selected.

## Required Features

- Pi model-specific mounting bosses.
- Power, Ethernet, USB, and storage service access.
- Cooling path matched to exact model and workload.
- Cable strain relief for persistent field use.
- Mounting option for shelf, wall, or panel.
- Label zone for hub identity and service notes.

## Blockers Before CAD

- Exact Raspberry Pi model.
- Exact radio-head connection method and hardware.
- Whether active cooling is used.
- Whether the hub requires direct microSD access.
- Whether any HAT, USB storage, display cable, or UPS/power board is installed.

## Prototype Sequence

1. Select exact Pi model and collect official drawing/STEP source.
2. Print mounting-hole and connector clearance card.
3. Print an open tray with actual cables installed.
4. Print airflow/cooling mockup and record temperatures under realistic workload.
5. Add mounting and cable management only after thermal behavior is acceptable.

## Boundaries

- Do not imply the hub enclosure is rugged, weatherproof, or production-ready without tests.
- Do not expose private radio-head internals or wiring in public files.
