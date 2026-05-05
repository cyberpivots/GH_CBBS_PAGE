# 3D Print Work

Concept workspace for future CBBS hardware enclosure design and rapid prototyping.

This folder is for public-safe enclosure planning only. Do not place private hardware notes, unreleased board internals, credentials, field logs, or private repository paths here. Keep product claims aligned with `docs/verified-sources.md` and published `src/content/**` entries.

## Current Purpose
- Identify public enclosure targets from the CBBS site content.
- Capture open mechanical questions before CAD work begins.
- Plan rapid enclosure prototyping for field nodes, display surfaces, hub accessories, and gateway/sensor integrations.
- Keep CAD, print profiles, validation notes, and bill-of-material records organized before production enclosure work starts.

## Folder Map
- `hardware-inventory.md`: public-safe list of hardware and enclosure relevance.
- `research-plan.md`: phased research and prototyping plan.
- `research/hardware-mechanical-findings.md`: verified source findings and unresolved source conflicts.
- `research/rapid-prototyping-method.md`: research-backed rapid prototype workflow.
- `research/measurement-checklist.md`: caliper and photo-measurement checklist before CAD.
- `concepts/`: enclosure family briefs and design direction.
- `data/`: structured public-safe hardware, concept, and printer/process inputs for CAD automation.
- `cad/toolchain.md`: recommended source/export file workflow for future models.
- `fusion/CBBSFusionAutomation/`: Fusion desktop add-in for local render/export review.
- `generated/print-packages/`: ignored internal-review STL/STEP print export packages.
- `generated/monitoring/k1/`: ignored read-only K1 probe and monitor session output.
- `prints/prototype-log-template.md`: repeatable print log template.
- `bom/candidate-standards.md`: candidate hardware and material standards, held pending measured hardware.
- `validation/checklists.md`: fit, thermal, RF, assembly, and release validation gates.

## Ground Rules
- Treat dimensions as unverified until confirmed from official mechanical drawings or measured hardware.
- Do not claim waterproofing, dust resistance, impact resistance, thermal performance, or RF performance without test evidence.
- Prefer modular enclosure families over one-off prints: hub accessory case, Heltec node case, display bezel/case, gateway/sensor case.
- Store generated CAD exports separately from editable source files.
- Keep generated CAD, Fusion renders, and mesh inspection output under ignored `generated/` paths until intentionally approved for public release.
- Do not generate or commit G-code by default; print packages are README-first STL/STEP handoff folders.
- Record evidence locators for every CAD-used dimension and numeric concept parameter.
- Keep unselected hardware as blocked records instead of inventing dimensions.
