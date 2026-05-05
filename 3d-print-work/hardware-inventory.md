# CBBS Hardware Inventory For Enclosure Concepts

This inventory is derived from current public CBBS content and approved public source review notes. It is a concept starting point, not a final mechanical bill of materials.

## Enclosure Targets

### Raspberry Pi Hub
- Public role: durable coordinator, archive, scheduler, and browser operator surface for the CBBS mesh.
- Enclosure relevance: hub case, wall or shelf mount, protected cable access, ventilation, radio-head attachment, service access.
- Known public constraints:
  - The exact Raspberry Pi model is not named in current public content.
  - Attached radio heads are mentioned, but the physical radio-head hardware is not yet specified publicly.
- Mechanical status: `needs model selection and official drawing review`.

### Heltec WiFi LoRa32 V2 Field Nodes
- Public role: smart radio heads, relays, field terminals, and local room servers.
- Public surfaces: local SoftAP browser room and onboard OLED quick checks.
- Public capabilities relevant to enclosure work:
  - LoRa mesh traffic and queue/status records.
  - Nearby Wi-Fi presentation.
  - Optional microSD cold storage in configured builds.
- Enclosure relevance: compact node case, OLED window, antenna strain relief, USB access, reset/program access, mounting points, weather-aware field handling.
- Mechanical status: `official Heltec dimensions and physical board revision must be confirmed before CAD`.

### OLED Quick-Check Display
- Public role: quick local field status on Heltec node surfaces.
- Enclosure relevance: display window, front-panel visibility, glare control, gasket or bezel strategy.
- Mechanical status: `part of Heltec node enclosure unless a separate display module is selected`.

### Nextion/P070 Display Surface
- Public role: prototype controller screen for richer field-visible status.
- Public status: prototype display, not a current system interface unless separately labeled.
- Enclosure relevance: panel bezel, display mount, cable routing, service access, possible desktop/wall/field-panel variants.
- Mechanical status: `official P070 drawing review required before CAD`.

### P800 Display Branding Assets
- Public role: display branding direction shown as a prototype contact sheet.
- Enclosure relevance: future larger display or splash-screen enclosure concepts only.
- Mechanical status: `concept only until an actual display module is selected`.

### Agriculture Gateway And Sensor Roles
- Public role: review, records, advisory analysis, and guarded gateway integration.
- Public interfaces mentioned: Modbus, MQTT, HTTP, and normalized CBBS records.
- Enclosure relevance: gateway box, sensor-node box, cable glands, strain relief, mounting, environmental exposure controls.
- Mechanical status: `hardware selection TBD; no enclosure dimensions yet`.

## Non-Enclosure Or Indirect Hardware

### Windows Operator Workstation
- Public role: lab and operator workstation layer for provisioning, image building, SD writing, device lab work, and operations.
- Enclosure relevance: not a direct 3D-printed CBBS enclosure target; may influence dock, jig, or test-fixture design later.

### Nearby Room Clients
- Public role: phones, tablets, or laptops that connect by local Wi-Fi to room nodes.
- Enclosure relevance: not CBBS hardware to enclose; may influence field signage, QR/SSID label plates, or phone stand accessories.

## Open Identification Tasks
- Select exact Raspberry Pi model and radio-head interface hardware.
- Confirm exact Heltec board revision and antenna configuration.
- Confirm whether microSD storage requires case access or remains internal-only.
- Confirm exact Nextion/P070 model and mounting approach.
- Identify gateway/sensor hardware before any field enclosure CAD.
- Identify power approach for each enclosure family: USB, battery, fixed DC, or mixed.
