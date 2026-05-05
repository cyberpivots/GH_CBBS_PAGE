# P070 Heltec Outdoor Power/RF Findings

Truth state: internal review.

This note records the source-derived hardware basis for the P070 Heltec
outdoor-blocked controller enclosure concept. It is not public product copy and
does not approve any enclosure protection class, runtime claim, or field
availability claim.

## Selected Hardware Basis

- Heltec WiFi LoRa 32 V2 remains the target board for this concept. The vendor
  PDF lists a 51 x 25.5 x 10.6 mm board envelope, SH1.25 x 2 battery socket,
  Micro USB, and IPEX LoRa antenna interface. The board is still
  measurement-blocked because the exact revision, connector population, button
  access, OLED position, and antenna route must be confirmed.
- The external antenna reference is Taoglas TI.96.A113 for the 900-940 MHz
  band. The product page lists SMA(M), 203 mm length, approximately 12.7 mm
  diameter, and an IP67 component rating. This rating applies only to the
  antenna component and does not create any CBBS enclosure claim.
- The RF pigtail reference is Adafruit product 851, a 15 cm SMA to uFL/IPEX
  panel-mount cable. The CAD concept routes it with strain relief and blocks
  release until SMA versus RP-SMA, board-side mating, bend radius, and panel
  stack are physically checked.
- The long-run battery/BMS reference is Bioenno BLF-0612C, a 6V 12Ah LiFePO4
  pack listed at 115 x 63 x 75 mm with built-in PCM. Runtime remains blocked
  until measured with the actual P070 brightness, Heltec transmit duty cycle,
  regulator heat, cable loss, and enclosure temperature.
- The default regulator reference is Pololu S13V30F5, a 5V buck-boost regulator
  in a 22.9 x 22.9 x 9.7 mm envelope. The CAD bay keeps 33 x 33 x 18 mm for
  wiring, terminal/header options, and thermal review.
- Charging remains external. Bioenno BPC-0602DC is documented as the charger
  reference for the 6V LiFePO4 workflow and must not be mounted inside the
  enclosure concept.
- Adafruit PowerBoost 1000C remains acceptable research for a small
  Heltec-only backup path, but it is rejected as the whole-P070 default because
  the display-plus-radio supply recommendation needs more headroom than a
  compact 1S LiPo boost/charger path.

## CAD Keepouts

- Heltec bay: 61 x 36 x 18 mm minimum.
- Regulator bay: 33 x 33 x 18 mm minimum.
- Battery service bay: 125 x 73 x 90 mm minimum.
- Antenna external sweep: 25 mm diameter x 230 mm minimum.

## Validation Blockers

- Measure the actual Heltec V2 board, display stack, battery pack, regulator
  assembly, RF pigtail, SMA bulkhead hardware, and cable bend envelopes.
- Validate RF performance with the actual antenna, printed material, bulkhead
  location, and display electronics installed.
- Validate heat rise for the regulator and battery bay with realistic P070
  brightness and Heltec transmit behavior.
- Validate retention straps, service access, connector strain relief, gasket
  surface, drip-lip surface, venting approach, wall mounting, and repeated
  open/close service cycles.

## Sources

- Heltec WiFi LoRa 32 V2 PDF: https://resource.heltec.cn/download/WiFi_LoRa_32/WiFi%20Lora32.pdf
- Taoglas TI.96.A113 product page: https://www.taoglas.com/product/900-940mhz-ip67-terminal-antenna/
- Adafruit product 851 RF adapter cable: https://www.adafruit.com/product/851
- Bioenno BLF-0612C battery product page: https://www.bioennopower.com/en-gb/collections/6v-lifepo4-batteries/products/copy-of-6v-12ah-lfp-battery-abs-sealed
- Pololu S13V30F5 regulator product page: https://www.pololu.com/product/4082
- Bioenno BPC-0602DC charger product page: https://www.bioennopower.com/products/7-3v-2a-ac-to-dc-charger-dc-plug-for-6v-lifepo4-batteries-bpc-0602dc
- Adafruit PowerBoost 1000C product page: https://www.adafruit.com/product/2465
