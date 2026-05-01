---
title: "Raspberry Pi hub"
summary: "The CBBS hub is the durable coordinator, archive, scheduler, and browser operator surface for the mesh."
publicationStatus: "published"
sourceStatus: "approved-public"
sourceRefs:
  - "CBBS product source review"
  - "Heltec firmware source review"
truthState: "current"
tags:
  - "hub"
  - "operator"
  - "sqlite"
role: "Durable coordinator and archive"
surface: "Browser sysop console"
capabilities:
  - "Coordinates hub-side records, scheduling, account review, and operator views."
  - "Persists hub state in SQLite-backed services."
  - "Uses attached radio heads for access and federation paths."
boundary: "The hub is the authority for durable coordination; degraded node coordination is not a replacement for hub authority."
order: 0
---

CBBS presents the hub as the durable field anchor for records, operator review, and mesh coordination.

