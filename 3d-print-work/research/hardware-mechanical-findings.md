# Hardware Mechanical Findings

Truth state: internal review / concept.

This file executes Phase 1 of `research-plan.md`. It separates verified public facts from open physical confirmation tasks. Do not promote any item here to public site copy unless the claim is already supported by `docs/verified-sources.md` and approved `src/content/**`.

## Source Hierarchy

Use this order for enclosure-critical facts:

1. Actual hardware in hand, measured with calipers and photographed with scale.
2. Official mechanical drawings or vendor datasheets for the exact model and revision.
3. Current public CBBS content for product role and public truth state.
4. Community CAD/STL models only as visual references, never as source dimensions.

## Raspberry Pi Hub

Current CBBS source facts:
- `src/content/systems/pi-hub.md` identifies the hub role as durable coordinator, archive, scheduler, browser operator surface, and radio-head attachment point.
- Current public CBBS content does not identify the exact Raspberry Pi model.

Verified external facts:
- Raspberry Pi publishes model-specific schematics and mechanical drawings from its official documentation.
- The Raspberry Pi documentation currently lists mechanical drawing assets for Raspberry Pi 5 and Raspberry Pi 4 Model B, and a STEP file for Raspberry Pi 5.
- Raspberry Pi documentation states all Raspberry Pi models require a 5.1 V supply, with power connector/current recommendations varying by model.
- Raspberry Pi documentation says a heatsink or fan can reduce thermal throttling and improve performance, and notes that vertical mounting improves airflow.

Enclosure impact:
- Do not start hub CAD until the exact Pi model, installed HATs/radio heads, cooling approach, storage access, and power connector path are known.
- Use official model drawings to set board outline and mounting hole placement.
- Treat any fan, vent, or heatsink opening as model-specific.

Open confirmations:
- Exact Raspberry Pi model.
- Whether a HAT, USB radio, cabled radio head, display, or storage device is installed.
- Required access for microSD, USB, Ethernet, HDMI, GPIO, power, fan, and shutdown/reset service.
- Whether the hub case is desk, shelf, wall, or panel mounted.

Sources:
- https://www.raspberrypi.com/documentation/computers/raspberry-pi.html
- https://datasheets.raspberrypi.com/rpi5/raspberry-pi-5-mechanical-drawing.pdf
- `src/content/systems/pi-hub.md`

## Heltec WiFi LoRa32 V2 Field Nodes

Current CBBS source facts:
- `src/content/systems/heltec-field-nodes.md` identifies Heltec WiFi LoRa32 V2 nodes as smart radio heads, relays, field terminals, and local room servers.
- Current public CBBS content identifies a local SoftAP browser surface, onboard OLED quick checks, LoRa mesh traffic, nearby Wi-Fi presentation, and optional build-flag-gated microSD cold storage.

Verified external facts:
- Heltec's current V2 product page labels the product as phaseout and recommends WiFi LoRa 32 (V3) for new projects.
- Heltec's current V2 product page says the onboard OLED can show system status and parameters.
- Heltec's FAQ states the onboard 2.4 GHz antenna is a spring antenna and that there is no additional interface on the board for 2.4 GHz wireless signals.
- Heltec's FAQ states the battery socket type can be found by searching `SH1.25 x 2`.
- Heltec's V2 PDF describes Wi-Fi, BLE, LoRa, Li-Po battery management, a 0.96-inch OLED, Micro USB, LoRa antenna IPEX interface, two 18-pin 2.54 mm headers, a 3.7 V lithium battery connector, and dimensions of 51 x 25.5 x 10.6 mm.
- Source tension: Heltec's current product page title references SX1262, while the linked 2020 PDF describes SX1276/SX1278. Do not name the LoRa chipset in enclosure notes until the physical board revision is confirmed.

Enclosure impact:
- Prioritize a V2 fit-test case for currently described public CBBS nodes, not a new V3 migration case.
- Create a separate future concept only if CBBS public content changes to identify V3 or another board.
- The enclosure must account for OLED visibility, Micro USB access, LoRa antenna routing, reset/program button access, battery connector/cable exit if used, and header population if present.
- Do not enclose the antenna path blindly. Final antenna placement requires RF smoke testing with the actual antenna and case material.

Open confirmations:
- Board revision and installed antenna configuration.
- Whether headers are populated.
- Whether battery power is used and whether the battery lives inside the same enclosure.
- Whether optional microSD storage is present on the CBBS build, and whether it requires external access.
- Button locations, cable clearance, tallest component, and underside component clearance from the actual board.

Sources:
- https://heltec.org/project/wifi-lora-32v2/
- https://resource.heltec.cn/download/WiFi_LoRa_32/WiFi%20Lora32.pdf
- `src/content/systems/heltec-field-nodes.md`

## OLED Quick-Check Display

Current CBBS source facts:
- `src/content/systems/display-surfaces.md` identifies onboard OLED quick screens as part of the display surface story.
- Current public CBBS content ties OLED quick checks to Heltec field nodes.

Enclosure impact:
- Treat the OLED as integrated with the Heltec node unless a separate OLED module is explicitly selected.
- Design a separate OLED window coupon before a full node case.
- Confirm viewing angle, window dimensions, contrast, lens material, and glare by physical prototype.

Open confirmations:
- Exact OLED active area, board position, lens/window material, and bezel clearance on the actual Heltec board.

Sources:
- `src/content/systems/display-surfaces.md`
- Heltec PDF above.

## Nextion/P070 Display Surface

Current CBBS source facts:
- `src/content/systems/display-surfaces.md` labels P070 captures as prototype controller screens unless explicitly labeled as current system interfaces.
- `src/content/media/p070-home.md`, `p070-rooms.md`, and `p070-files.md` are approved public display-surface content entries.

Verified external facts:
- ITEAD's official page identifies NX8048P070-011C as a 7.0-inch capacitive Intelligent Series HMI touchscreen without enclosure.
- ITEAD lists resolution as 800 x 480, input power as DC 5 V 1 A, and USART port as XH2.54 4P.
- ITEAD lists an XH2.54 4P wire in the box and links certification/documentation assets.
- The NX8048P070-011C dimension drawing is in mm and lists tolerance as +/- 0.2 mm. The drawing includes 181.00 mm and 108.00 mm outsize dimensions, 164.9 mm by 100.00 mm LCD outsize, and 154.08 mm by 85.92 mm LCD active area.

Enclosure impact:
- P070 mechanical work should use a panel/bezel family, not a handheld field-node case.
- The first printable should be a flat bezel/frame fit template with mounting holes and display opening, not a full enclosure.
- The cable exit must account for XH2.54 4P wiring and service strain relief.
- Do not claim a current field interface in enclosure copy. Label this family as prototype display hardware until public CBBS content changes.

Open confirmations:
- Whether the exact physical display is NX8048P070-011C or another P070 variant.
- Mounting orientation, cable exit direction, rear clearance, optional speaker/IO accessories, and protective lens strategy.

Sources:
- https://itead.cc/product/7-0-nextion-intelligent-series-hmi-resistivecapacitive-touch-display-without-enclosure/
- https://cdn.nextion.tech/wp-content/uploads/2022/03/NX8048P070-011C_dimension.pdf
- `src/content/systems/display-surfaces.md`

## P800 Display Branding Assets

Current CBBS source facts:
- `src/content/media/splash-contact-sheet.md` presents P800 splash branding direction.

Enclosure impact:
- P800 is not an enclosure target until an actual display module is selected and approved.
- Keep P800 work limited to branding and possible future concept placeholders.

Open confirmations:
- Exact P800 display module, if one is later selected.

Source:
- `src/content/media/splash-contact-sheet.md`

## Agriculture Gateway And Sensor Roles

Current CBBS source facts:
- `src/content/systems/agriculture-runtime.md` identifies agriculture-facing source paths for observations, review desks, input-cost records, and guarded gateway integration.
- Current public content names Modbus, MQTT, HTTP, and normalized CBBS records as interface roles.
- Current public content limits agriculture claims to review, records, advisory analysis, and approval workflows.

Enclosure impact:
- Gateway/sensor enclosure CAD is blocked until gateway boards, sensor interfaces, cable types, power method, and environment are selected.
- It is acceptable to create generic concept briefs for cable glands, DIN rail, wall mount, and sensor-wire strain relief, but not a dimensioned case.

Open confirmations:
- Exact gateway board, sensor board, power method, cable count/diameter, mounting location, and environmental target.

Source:
- `src/content/systems/agriculture-runtime.md`

## Rugged Outdoor Enclosure Context

Current CBBS source facts:
- Current public CBBS content does not publish a certified outdoor enclosure,
  ingress rating, impact rating, or production case.
- Current CAD automation is limited to fit-test artifacts, coupons, and blocked
  placeholders until exact hardware and measurements are recorded.

Verified external facts:
- NEMA enclosure type guidance describes outdoor enclosure categories and the
  environmental conditions those categories are designed to protect against when
  properly installed.
- IEC 60529 applies to classification of degrees of protection provided by
  electrical enclosures.
- IEC 62262 classifies degrees of protection provided by electrical enclosures
  against external mechanical impacts.
- Prusa documents ASA as suitable for outdoor technical parts due to UV and
  temperature resistance, while noting warping and fume constraints. Prusa also
  documents PETG as suitable for many interior and exterior mechanical parts
  below its temperature limits.
- Gore documents pressure-equalizing vents for sealed outdoor electronics as a
  way to reduce pressure stress and help reduce condensation.

Enclosure impact:
- Treat rugged/outdoor CAD as coupon-driven prototype work until hardware,
  material, gasket, cable, venting, thermal behavior, and service requirements
  are tested.
- Prefer reinforced coupons and fit frames over full cases in the current
  repository state.
- Do not claim enclosure ratings, field readiness, or production suitability
  without a validation plan and approval source.

Open confirmations:
- Exact hardware and installed cables.
- Target material and printer process.
- Gasket, fastener, cable-entry, mounting, and venting hardware.
- Thermal, condensation, service-cycle, pull, and handling test results.

Sources:
- https://www.nema.org/docs/default-source/products-document-library/nema-enclosure-types.pdf
- https://webstore.iec.ch/en/publication/2447
- https://webstore.ansi.org/preview-pages/IEC/preview_iec62262%7Bed1.1%7Db.pdf
- https://help.prusa3d.com/article/asa_1809
- https://help.prusa3d.com/article/petg_2059
- https://www.gore.com/products/screw-protective-vents-outdoor-electronics-enclosures
