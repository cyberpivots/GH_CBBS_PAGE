# CAD

Future CAD workspace for enclosure source files and mechanical exports.

Suggested layout when modeling begins:
- `native/`: editable source files from the chosen CAD tool.
- `step/`: neutral STEP exports for review and reuse.
- `stl/`: mesh exports for printing.
- `drawings/`: PDF/DXF drawings, if needed.
- `params/`: shared dimensions, keepout tables, and fastener standards.

Rules:
- Do not store only STL files. Keep editable source CAD.
- Name files with hardware target, concept, and revision, for example `heltec-node-case-r01.step`.
- Include a revision note whenever connector openings, standoffs, antenna routing, or display windows change.
