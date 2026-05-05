# Concept Brief: Heltec Node Case

Truth state: concept.

## Goal

Create a compact enclosure family for public CBBS Heltec WiFi LoRa32 V2 field-node concepts, with OLED visibility, antenna relief, USB access, and serviceable assembly.

## Verified Inputs

- Current public CBBS content identifies Heltec WiFi LoRa32 V2 nodes as field nodes, relays, field terminals, and local room servers.
- Current public CBBS content identifies local SoftAP browser access and onboard OLED quick checks.
- Heltec documentation identifies V2 physical features relevant to enclosure work: OLED, Micro USB, LoRa antenna IPEX interface, battery connector, and board dimensions.

Sources:
- `src/content/systems/heltec-field-nodes.md`
- `src/content/systems/display-surfaces.md`
- https://resource.heltec.cn/download/WiFi_LoRa_32/WiFi%20Lora32.pdf
- https://heltec.org/project/wifi-lora-32v2/

## Variants

- `bench-node`: open service case for lab and firmware testing.
- `handheld-node`: closed case with OLED window, antenna relief, and USB/program access.
- `wall-node`: wall-mount case with cable exits and label area.

## Required Features

- OLED window and bezel.
- USB cable access.
- Reset/program access or removable lid for service.
- LoRa antenna strain relief and clear routing.
- Keepout around onboard 2.4 GHz antenna.
- Mounting standoffs matched to measured board holes.
- Label zone for node identity and public-safe setup markings.

## Blockers Before CAD

- Confirm exact board revision in hand.
- Confirm antenna configuration and cable path.
- Confirm battery/no-battery configuration.
- Confirm header population.
- Confirm whether optional microSD storage exists in the target build.

## Prototype Sequence

1. Print board outline and mount-hole fit card.
2. Print open tray with USB, button, and antenna keepouts.
3. Print OLED window coupon.
4. Print antenna/cable strain-relief coupon.
5. Print first two-piece case.
6. Run fit, RF smoke, thermal touch, and assembly checks.

## Boundaries

- Do not claim waterproofing, dust resistance, impact resistance, or RF performance.
- Do not publish internal wiring or firmware details.
- Do not migrate the concept to Heltec V3 unless public CBBS content and hardware selection change.
