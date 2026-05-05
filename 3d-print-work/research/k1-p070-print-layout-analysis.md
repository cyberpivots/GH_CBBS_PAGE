# K1 P070 Print Layout Analysis

Verification date: 2026-05-02.

This note records the current generated P070 split-plate strategy. It is
internal CAD workflow knowledge; it is not a release claim.

## Verified Source Facts

- Creality lists K1, K1C, and K1 SE build volume as `220 x 220 x 250 mm`.
- Creality lists K1 Max build volume as `300 x 300 x 300 mm`.
- Creality lists ASA support for K1C, while K1/K1 SE material support differs.
  CBBS keeps K1-series ASA as a process target, not a public product claim.
- Prusa FFF guidance records the common `0.4 mm` desktop nozzle baseline, warns
  that orientation and support surfaces affect results, and recommends splitting
  parts where that improves orientation and placement.
- Prusa ASA guidance records significant warping risk, high bed/nozzle
  temperature needs, enclosure/ambient-temperature sensitivity, and ventilation
  concerns.

## Current Generated P070 Bounds

Generated with:

```bash
uv run --project tools/cad cbbs-cad generate --concept p070_hinged_wall_enclosure --out-dir /tmp/cbbs-p070-layout-check
```

Part bounds from the generated assembly manifest:

| Part | Role | Bounds mm |
| --- | --- | --- |
| `rear_tray` | print | `206.2 x 143.6 x 36.2` |
| `front_display_door` | print | `206.2 x 124.4 x 8.8` |
| `hinge_pin` | hardware-reference | `3.0 x 96.8 x 3.0` |
| `display_reference` | hardware-reference | `181.0 x 108.0 x 8.3` |
| `m12_gland_reference` | hardware-reference | `16.6 x 30.0 x 16.6` |

The tray and door each fit on a `220 x 220 mm` K1/K1C/K1 SE plate with a `6 mm`
brim margin on each side:

- Tray: `206.2 + 12 = 218.2 mm` by `143.6 + 12 = 155.6 mm`.
- Door: `206.2 + 12 = 218.2 mm` by `124.4 + 12 = 136.4 mm`.

They do not fit together on one `220 x 220 mm` plate with that margin:

- Side by side: `206.2 + 206.2 + 8 + 12 = 432.4 mm`.
- Stacked along Y: `143.6 + 124.4 + 8 + 12 = 288.0 mm`.

The same stacked layout fits a K1 Max plate:

- K1 Max stacked: `206.2 + 12 = 218.2 mm` by `288.0 mm`, within
  `300 x 300 mm`.

## Selected Layout Strategy

- `k1-plate-tray`: tray-only K1 plate, accepted for internal review.
- `k1-plate-door`: door-only K1 plate, accepted for internal review.
- `k1-combined`: explicit rejected metadata record so automation does not place
  tray and door together on a K1/K1C/K1 SE plate.
- `k1-max-combined`: optional stacked K1 Max review layout.
- `hardware-reference`: display, gland, and hinge-pin reference envelopes for
  Fusion review only.

Physical release remains blocked until the exact display variant, rear component
envelope, cable bend radius, selected gland hardware, pin stock, and ASA latch
cycling are measured or validated.

## Sources

- Creality K1 series comparison: https://www.creality.com/compare/compare-k1-flagship-series/
- Prusa modeling guidance: https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135/
- Prusa ASA material guidance: https://help.prusa3d.com/article/asa_1809
