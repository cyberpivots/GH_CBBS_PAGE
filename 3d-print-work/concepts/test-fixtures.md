# Concept Brief: Test Fixtures

Truth state: concept.

## Goal

Use small, fast prints to reduce enclosure iteration risk before full cases are printed.

## Fixture Candidates

- `board-outline-card`: flat outline with mounting holes and connector keepouts.
- `standoff-coupon`: board standoff height and screw engagement test.
- `insert-coupon`: heat-set insert hole, boss diameter, and wall thickness test for a selected insert part.
- `snap-coupon`: snap tab geometry test for selected material.
- `oled-window-coupon`: OLED opening, lens, glare, and bezel test.
- `p070-bezel-card`: P070 active-area and mount-hole test.
- `usb-cable-gauge`: connector insertion and cable bend envelope gauge.
- `antenna-relief-coupon`: antenna cable routing and strain-relief test.
- `label-plate`: QR/serial label, embossed text, and adhesive label test.

## Rules

- Print coupons before full cases.
- Keep each coupon tied to a specific material and slicer profile.
- Do not reuse a coupon result across materials without retesting.
- Record all results in `prints/prototype-log-template.md`.
