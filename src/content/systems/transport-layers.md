---
title: "Transport layers"
summary: "CBBS treats LoRa as the authoritative long-range store-and-forward path, with local Wi-Fi for nearby browser presentation."
publicationStatus: "published"
sourceStatus: "approved-public"
sourceRefs:
  - "Heltec firmware source review"
  - "CBBS product source review"
truthState: "current"
tags:
  - "lora"
  - "wifi"
  - "mesh"
role: "Message and control transport"
surface: "LoRa mesh, local Wi-Fi, and reserved adjacent acceleration paths"
capabilities:
  - "Carries BBS records, alerts, listings, troubleshooting notes, telemetry, and command acknowledgements over the same mesh substrate."
  - "Uses Wi-Fi for local access and presentation near nodes."
  - "Keeps ESP-NOW reserved for adjacent acceleration rather than the authoritative long-range path."
boundary: "Large files are not positioned for spoke LoRa mesh transport."
order: 5
---

Transport value centers on resilient records and store-and-forward behavior rather than real-time chat claims.
