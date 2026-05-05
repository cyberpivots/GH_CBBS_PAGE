# CBBS Fusion Automation Add-In

This Fusion desktop Python add-in reads a generated job JSON and imports local
STEP/STL artifacts for visual review, rendering, and Fusion-native export.
When loaded, it also runs a local agent bridge that watches generated request
JSON files and executes supported commands inside Fusion.

Default job path:

```text
3d-print-work/generated/fusion/latest-job.json
```

To point Fusion at a different job, create a local `job_path.txt` beside
`CBBSFusionAutomation.py`. That file is ignored by the repo-level workflow when
kept local and should not contain secrets.

Generated renders, logs, and exports stay under `3d-print-work/generated/fusion/`
until explicitly approved for public release.

## Repo Workflow

From the repo root:

```bash
pnpm run cad:validate
pnpm run cad:audit
pnpm run cad:generate
pnpm run cad:inspect
pnpm run cad:fusion-job
pnpm run cad:fusion-status
```

Install or sync the add-in only when a Fusion desktop handoff is intended:

```bash
pnpm run cad:fusion-install
```

The install command copies this directory to Fusion's default AddIns folder,
writes the installed `job_path.txt`, sets the installed manifest
`runOnStartup` value to `true`, and validates the manifest JSON. The repo copy
remains canonical; the installed copy is disposable and may drift.

## Manual Smoke Test

After `cad:fusion-install`, ask the user to start or restart Fusion manually or
run the add-in from Fusion's Scripts and Add-Ins dialog. Then run:

```bash
pnpm run cad:fusion-smoke
pnpm run cad:fusion-status
```

The smoke command only watches for a new log. It does not start, stop, kill, or
restart Fusion.

## Agent Bridge

After the updated add-in is installed and Fusion has loaded it, check the bridge:

```bash
pnpm run cad:fusion-agent-status
```

Agent requests live under:

```text
3d-print-work/generated/fusion/agent/requests/
```

Responses, heartbeat JSON, viewport snapshots, UI/process logs, and process
action records stay under `3d-print-work/generated/fusion/agent/`. Supported
bridge actions include `run_job`, `open_artifact`, `open_assembly_artifact`,
`capture_viewport`, `ui_state`, `cleanup_owned_documents`, `export_active_archive`,
`command_inventory`, `activate_workspace`, `execute_command_id`, and guarded
`execute_text_command`.

Run the generated job through the bridge:

```bash
pnpm run cad:fusion-agent-run
```

If Fusion has not loaded the bridge yet, sync the add-in, then use the managed
restart command only when intentionally closing/reloading Fusion:

```bash
pnpm run cad:fusion-install
pnpm run cad:fusion-agent-restart
```

The restart command refuses unsaved Fusion windows by default. Closing an
unsaved user-owned Fusion document requires the explicit
`--allow-unsaved-close` flag. Use `pnpm run cad:fusion-clean-owned` to close
leftover CBBS-owned generated documents without restarting Fusion.

Windows UI Automation helpers are available for direct interface inspection and
guarded interaction:

```bash
pnpm run cad:fusion-ui-snapshot
pnpm run cad:fusion-ui-invoke
```

`fusion-ui-invoke` requires explicit guard flags before it sends keys, clicks a
target without `InvokePattern`, or closes a window.

## Outputs

Generated jobs include a run id, fresh-document mode, generated-document
lifecycle policy, quiet UI behavior, run-id-specific render/export names, and
`wait_for_renders: true`. New add-in runs write `run-summary.json` with
import/export return values, render completion state, and generated-document
close results so "started", "finished", and "closed" are distinguishable.
Render jobs are source-isolated: each top-level artifact render uses a
`<concept_id>__model` key and each assembly view uses a
`<concept_id>__<view>` key, with a dedicated STEP source imported into a
temporary generated document for that output.

Native Fusion assembly documentation is authored in Fusion's Animation and
Drawing workspaces. The bridge may support setup, viewport captures, command
inventory, workspace activation, and local `.f3d` archive export, but it must not
create fake assembly-instruction solids or claim generated renders are native
storyboards.

P070 hinged enclosure jobs may include generated assembly metadata. When
present, the add-in imports the part-level tray, display-door, hinge-pin,
display reference, and M12 gland reference files as named components and
occurrences instead of duplicating the monolithic review artifact. Assembly
render views use generated STEP sources for:

```text
closed-front
closed-isometric
door-open
exploded
k1-plate-tray
k1-plate-door
k1-max-combined
hardware-reference
```

The output remains internal review material under
`3d-print-work/generated/fusion/`; do not copy renders, exports, or logs into
public assets without a separate source-review decision.

Windows STEP file association is not a reliable automation path for this repo.
Use `cad:fusion-job` plus this add-in instead.
