---
title: "Async community boards"
summary: "CBBS can support direct messages, local boards, and future asynchronous game-style exchanges over the BBS record model."
publicationStatus: "published"
sourceStatus: "approved-public"
sourceRefs:
  - "Heltec firmware source review"
truthState: "projected"
tags:
  - "boards"
  - "messages"
problem: "Small off-grid groups benefit from familiar BBS-style communication patterns that do not assume continuous sessions."
cbbsFit: "The CBBS architecture names local boards, direct messages, and asynchronous turn exchange as operator-facing record workflows."
boundary: "Door-game style sessions and real-time chat are out of scope for V2 LoRa links."
order: 6
---

Durable asynchronous exchange remains separate from live interactive sessions.
