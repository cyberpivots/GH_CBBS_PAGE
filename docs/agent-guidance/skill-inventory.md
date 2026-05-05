# Agent Skill Inventory

Use this note to avoid re-auditing the same Codex skills during CBBS public-site
CAD work.

## Applies To CBBS Fusion Work

- `$cbbs-fusion360-workflows`: Use for Fusion desktop CAD automation, generated
  CAD artifacts, add-in install/sync, Fusion bridge actions, status checks,
  renders, exports, and documentation of Fusion handoff boundaries.
- `$cbbs-3d-print-export-workflows`: Use for repo-native STL/STEP print
  packages, typed printer/process records, P070 K1 split-plate guidance, and
  read-only K1 camera probe/monitor outputs under `3d-print-work/generated/`.
- `$cbbs-cad-model-strength-review`: Use for CAD reinforcement, structural
  weak-point review, assembly clarity, component-print fit, and evidence-gated
  model-strength changes under `3d-print-work/`.
- `$cbbs-3d-modeling-tool-research`: Use for evidence-gated research of CAD,
  rendering, CV/screen viewing, slicer, mesh diagnostics, and Fusion-specific
  packages/tools before changing dependencies or automation paths.

## Skill Authoring

- `$skill-creator`: Use when creating or updating Codex skills for this
  workspace. Keep skills concise and validate them after editing.
- `$plugin-creator`: Use only when creating Codex plugins, not ordinary CAD or
  site edits.
- `$skill-installer`: Use only when installing external skills into
  `$CODEX_HOME/skills`.

## Usually Not Applicable

- `$imagegen`: Only use when the task needs generated bitmap imagery. Do not use
  it for CAD geometry, SVG/code-native assets, deterministic technical
  diagrams, or Fusion automation.
- `$openai-docs`: Use for OpenAI product/API questions, not CAD automation or
  non-OpenAI modeling tools.
- Canva skills: Use only for Canva design/presentation work.
- GitHub skills: Use for GitHub issue, PR, CI, or publishing workflows.
- `$valley-fusion-modeling`: Specific to the Valley Model 8000 Fusion model, not
  the CBBS public-site repository.

## Current Direct Skill Set

- Available system skills: `$imagegen`, `$openai-docs`, `$plugin-creator`,
  `$skill-creator`, `$skill-installer`.
- Available CBBS skills: `$cbbs-fusion360-workflows`,
  `$cbbs-3d-print-export-workflows`, `$cbbs-cad-model-strength-review`,
  `$cbbs-3d-modeling-tool-research`.
- Available unrelated workspace skill: `$valley-fusion-modeling`.
