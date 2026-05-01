---
title: "Offline-first communication model"
summary: "CBBS communication model across hub services, local nodes, room clients, and transport layers."
publicationStatus: "published"
sourceStatus: "approved-public"
sourceRefs:
  - "CBBS product source review"
  - "Heltec firmware source review"
audience: "public"
order: 2
updatedDate: "2026-05-01"
---

## Hub and field nodes

CBBS uses the hub as the durable coordinator, archive, scheduler, and operator surface. Field nodes participate as radio heads, relays, room servers, and local terminals.

## Local access

Nearby users can connect to a room-node Wi-Fi surface and use a browser client for account access, room browsing, local board visibility, and policy views.

## Transport direction

The system treats LoRa as the authoritative long-range store-and-forward path, with local Wi-Fi used for nearby presentation and access.
