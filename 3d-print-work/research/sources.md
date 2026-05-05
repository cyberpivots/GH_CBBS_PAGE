# Research Sources

Use this file to track public sources for mechanical design, hardware dimensions, and rapid prototyping practices.

Research execution date: 2026-05-01.

## Current Public CBBS Sources
- `src/content/resources/system-brief.md`
- `src/content/systems/pi-hub.md`
- `src/content/systems/heltec-field-nodes.md`
- `src/content/systems/display-surfaces.md`
- `src/content/systems/transport-layers.md`
- `src/content/systems/agriculture-runtime.md`
- `src/content/media/p070-home.md`
- `src/content/media/p070-rooms.md`
- `src/content/media/p070-files.md`

## Hardware Mechanical Sources To Review
- Raspberry Pi official hardware documentation and mechanical drawings:
  - https://www.raspberrypi.com/documentation/computers/raspberry-pi.html
- Raspberry Pi 5 official mechanical drawing:
  - https://datasheets.raspberrypi.com/rpi5/raspberry-pi-5-mechanical-drawing.pdf
- Heltec WiFi LoRa 32 V2 product page:
  - https://heltec.org/project/wifi-lora-32v2/
- Heltec WiFi LoRa 32 V2 PDF:
  - https://resource.heltec.cn/download/WiFi_LoRa_32/WiFi%20Lora32.pdf
- Taoglas TI.96.A113 900-940MHz terminal antenna product page:
  - https://www.taoglas.com/product/900-940mhz-ip67-terminal-antenna/
- Adafruit SMA to uFL/u.FL/IPX/IPEX RF adapter cable:
  - https://www.adafruit.com/product/851
- Bioenno BLF-0612C 6V 12Ah LiFePO4 battery product page:
  - https://www.bioennopower.com/en-gb/collections/6v-lifepo4-batteries/products/copy-of-6v-12ah-lfp-battery-abs-sealed
- Pololu S13V30F5 5V 3A buck-boost regulator product page:
  - https://www.pololu.com/product/4082
- Bioenno BPC-0602DC charger product page:
  - https://www.bioennopower.com/products/7-3v-2a-ac-to-dc-charger-dc-plug-for-6v-lifepo4-batteries-bpc-0602dc
- Adafruit PowerBoost 1000C product page:
  - https://www.adafruit.com/product/2465
- ITEAD official Nextion 7.0 inch Intelligent Series product page:
  - https://itead.cc/product/7-0-nextion-intelligent-series-hmi-resistivecapacitive-touch-display-without-enclosure/
- Nextion P070 official dimension drawing:
  - https://cdn.nextion.tech/wp-content/uploads/2022/03/NX8048P070-011C_dimension.pdf
- Creality K1 flagship series comparison:
  - https://www.creality.com/compare/compare-k1-flagship-series/
- Creality K1C support/specification page:
  - https://www.creality.com/support/k1c-carbon-3d-printer
- JST XH connector datasheet:
  - https://www.jst-mfg.com/product/pdf/eng/eXH.pdf
- LAPP SKINTOP ST-M M12x1.5 cable gland data:
  - https://products.lappgroup.com/online-catalogue/cable-glands/skintop-cable-glands-plastic-metric/standard/skintop-st-m.html
- NBK metric clearance holes and counterbores:
  - https://www.nbk1560.com/en-US/resources/other/article/technical-20-diameter-of-clearance-holes-and-counterbores-for-bolts-and-screws

## 3D Printing Design Sources To Review
- Prusa modeling guidance:
  - https://help.prusa3d.com/article/modeling-with-3d-printing-in-mind_164135/
- Prusa 3MF project file guidance:
  - https://help.prusa3d.com/article/saving-projects-as-3mf_1773
- Prusa ASA material guidance:
  - https://help.prusa3d.com/article/asa_1809
- UltiMaker design-for-3D-printing guide:
  - https://ultimaker.com/learn/how-to-design-for-3d-printing-a-comprehensive-guide-to-creating-3d-printable-designs/
- FreeCAD feature overview:
  - https://www.freecad.org/features.php?lang=en
- GitHub Git LFS documentation:
  - https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-git-large-file-storage

## Research Notes
- Use official hardware drawings over community models for enclosure-critical dimensions.
- Treat online STLs as references only unless their dimensions are independently verified.
- Record measured dimensions and source drawings separately from public marketing copy.
- Do not publish raw private project details in this folder or derive public claims from unapproved private notes.
- The current Heltec V2 source set has source tension: the current product page title references SX1262, while the linked 2020 PDF describes SX1276/SX1278. Confirm the actual board in hand before naming a LoRa chipset in enclosure notes or public-facing copy.
