# Fusion Document Lifecycle Findings

Verification date: 2026-05-02.

This note records the public API basis for the CBBS Fusion generated-document
policy. It is internal CAD workflow knowledge; it is not public product content.

## Verified API Facts

- Autodesk documents `Document.close(saveChanges)`. Passing `false` closes a
  modified document and discards changes; passing `true` can prompt the user.
  Closing documents is not supported from command-related events.
- `Documents.add(documentType)` creates and opens a new document, and Autodesk
  gives the same warning about command-related events for document creation.
- `Application.documents`, `Documents.count`, and `Documents.item(index)` expose
  the current open-document inventory.
- `Document` exposes `attributes`, `isSaved`, `isModified`, `isVisible`, and a
  settable `name` before first save. These are sufficient for CBBS ownership
  tagging and non-destructive inventory.
- Fusion assembly structure should use components and occurrences. Autodesk
  documents `Occurrences.addNewComponent(transform)` for creating a component
  with an occurrence, and `Occurrence.transform2` for setting occurrence
  position/orientation.
- `Rendering.startLocalRender(filename, camera)` starts a local render tied to
  the running Fusion process. Multiple local renders are queued and only one
  runs at a time.

## CBBS Policy

- Generated Fusion documents are disposable. The durable outputs are local
  STEP/STL files, render images, logs, and `run-summary.json` under
  `3d-print-work/generated/`.
- Default generated jobs use:
  - `close_generated_documents: true`
  - `save_policy: discard_generated`
  - `allow_user_prompt: false`
  - `keep_open_for_review: false`
- Manual review jobs must explicitly set `keep_open_for_review: true`. In that
  mode, status may report the open document as intentional.
- The add-in must tag generated documents and assembly components with CBBS
  owner/run metadata before importing geometry.
- Cleanup may close only CBBS-owned generated documents. It must not close or
  discard user-owned documents.
- Managed restart decisions should use the bridge document inventory when
  available. `--allow-unsaved-close` applies only to user-owned modified work.

## Sources

- Autodesk `Document.close`: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Document_close.htm
- Autodesk `Document` object: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Document.htm
- Autodesk `Documents.add`: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Documents_add.htm
- Autodesk `Application.documents`: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Application_documents.htm
- Autodesk components/occurrences overview: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/ComponentsProxies_UM.htm
- Autodesk `Occurrences.addNewComponent`: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Occurrences_addNewComponent.htm
- Autodesk `Occurrence.transform2`: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Occurrence_transform2.htm
- Autodesk `Rendering.startLocalRender`: https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/Rendering_startLocalRender.htm
