---
title: "Heltec V2 field nodes"
summary: "Heltec WiFi LoRa32 V2 nodes act as smart radio heads, relays, field terminals, and local room servers."
publicationStatus: "published"
sourceStatus: "approved-public"
sourceRefs:
  - "Heltec firmware source review"
  - "CBBS product source review"
truthState: "current"
tags:
  - "hardware"
  - "lora"
  - "room-node"
role: "Field node and relay"
surface: "Local SoftAP browser room and OLED quick checks"
capabilities:
  - "Relays LoRa mesh traffic and publishes state deltas, queue status, and command acknowledgements."
  - "Serves a local room-oriented WPA2 SoftAP browser interface for up to four nearby clients in the full room-node build."
  - "Supports optional build-flag-gated microSD cold storage."
boundary: "The local browser surface can be omitted in configurations that only need mesh relay behavior."
order: 1
---

Heltec nodes act as field terminals and radio participants, not general-purpose cloud devices.
