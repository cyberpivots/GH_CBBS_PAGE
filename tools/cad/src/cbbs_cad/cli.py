from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from cbbs_cad.audit import audit_bundle
from cbbs_cad.fusion_agent import (
    enqueue_agent_command,
    fusion_agent_status,
    fusion_ui_invoke,
    fusion_ui_snapshot,
    restart_fusion,
    start_fusion,
    wait_for_agent_response,
)
from cbbs_cad.fusion_job import DEFAULT_FUSION_JOB, create_fusion_job
from cbbs_cad.fusion_workflow import (
    check_fusion_status,
    default_installed_addin_dir,
    install_fusion_addin,
    is_url_like_path,
    job_pointer_value,
    resolve_local_artifact_path,
    wait_for_new_fusion_log,
)
from cbbs_cad.generate import DEFAULT_OUTPUT_DIR, generate_concepts
from cbbs_cad.k1_monitor import (
    DEFAULT_K1_HOST,
    DEFAULT_K1_MONITOR_ROOT,
    DEFAULT_K1_PORTS,
    monitor_k1_camera,
    probe_k1_camera,
)
from cbbs_cad.mesh import inspect_meshes
from cbbs_cad.print_package import (
    DEFAULT_FUSION_SUMMARY,
    DEFAULT_PRINT_CONCEPT_ID,
    DEFAULT_PRINT_MATERIAL,
    DEFAULT_PRINT_PACKAGE_ROOT,
    DEFAULT_PRINT_PRINTER_ID,
    create_print_package,
)
from cbbs_cad.report import DEFAULT_REPORT_DIR, write_evidence_report
from cbbs_cad.specs import DEFAULT_DATA_DIR, bundle_to_manifest, load_specs

app = typer.Typer(no_args_is_help=True)
console = Console()


def _load_or_exit(paths: list[Path] | None, data_dir: Path):
    try:
        return load_specs(paths=paths, data_dir=data_dir)
    except (ValidationError, ValueError) as exc:
        console.print(f"[red]CAD spec validation failed:[/red]\n{exc}")
        raise typer.Exit(1) from exc


@app.command()
def validate(
    paths: Annotated[
        list[Path] | None,
        typer.Argument(help="Specific YAML/JSON spec files. Defaults to 3d-print-work/data."),
    ] = None,
    data_dir: Annotated[Path, typer.Option(help="CAD data directory.")] = DEFAULT_DATA_DIR,
) -> None:
    """Validate hardware and concept specs."""

    bundle = _load_or_exit(paths, data_dir)
    console.print(
        f"Validated {len(bundle.hardware)} hardware spec(s) and "
        f"{len(bundle.concepts)} concept spec(s) and "
        f"{len(bundle.printers)} printer spec(s) and "
        f"{len(bundle.tooling)} tooling candidate spec(s)."
    )


@app.command()
def manifest(
    data_dir: Annotated[Path, typer.Option(help="CAD data directory.")] = DEFAULT_DATA_DIR,
    out: Annotated[
        Path | None,
        typer.Option("--out", "-o", help="Write the input manifest to this path."),
    ] = None,
) -> None:
    """Emit a manifest of CAD input specs."""

    bundle = _load_or_exit(None, data_dir)
    payload = bundle_to_manifest(bundle)
    if out:
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        console.print(f"Wrote {out}")
    else:
        console.print_json(json.dumps(payload))


@app.command("audit-sources")
def audit_sources(
    data_dir: Annotated[Path, typer.Option(help="CAD data directory.")] = DEFAULT_DATA_DIR,
) -> None:
    """Audit CAD specs for evidence, image provenance, and release blockers."""

    bundle = _load_or_exit(None, data_dir)
    failures = audit_bundle(bundle)
    if failures:
        console.print("[red]CAD source audit failed:[/red]")
        for failure in failures:
            console.print(f"- {failure}")
        raise typer.Exit(1)
    console.print("CAD source audit passed.")


@app.command("evidence-report")
def evidence_report(
    data_dir: Annotated[Path, typer.Option(help="CAD data directory.")] = DEFAULT_DATA_DIR,
    out_dir: Annotated[
        Path,
        typer.Option(help="Evidence report output directory."),
    ] = DEFAULT_REPORT_DIR,
) -> None:
    """Write a local hardware evidence report as Markdown and JSON."""

    bundle = _load_or_exit(None, data_dir)
    paths = write_evidence_report(bundle, out_dir)
    console.print(f"Wrote {paths['markdown']}")
    console.print(f"Wrote {paths['json']}")


@app.command()
def generate(
    concept: Annotated[
        list[str] | None,
        typer.Option("--concept", "-c", help="Concept id to generate. Can be repeated."),
    ] = None,
    data_dir: Annotated[Path, typer.Option(help="CAD data directory.")] = DEFAULT_DATA_DIR,
    out_dir: Annotated[Path, typer.Option(help="Generated CAD output directory.")] = DEFAULT_OUTPUT_DIR,
) -> None:
    """Generate source-derived STEP/STL fit-test artifacts."""

    bundle = _load_or_exit(None, data_dir)
    try:
        generated = generate_concepts(bundle, output_dir=out_dir, concept_ids=concept)
    except (RuntimeError, ValueError) as exc:
        console.print(f"[red]CAD generation failed:[/red]\n{exc}")
        raise typer.Exit(1) from exc

    table = Table(title="Generated CAD Artifacts")
    table.add_column("Concept")
    table.add_column("Truth state")
    table.add_column("Bounds mm")
    table.add_column("Files")
    for artifact in generated["artifacts"]:
        table.add_row(
            artifact["concept_id"],
            artifact["truth_state"],
            json.dumps(artifact["bounds_mm"]),
            ", ".join(artifact["files"].values()),
        )
    console.print(table)
    console.print(f"Wrote {out_dir / 'manifest.json'}")


@app.command("print-package")
def print_package(
    concept_id: Annotated[
        str,
        typer.Option("--concept", "-c", help="Generated CAD concept id to package."),
    ] = DEFAULT_PRINT_CONCEPT_ID,
    printer_id: Annotated[
        str,
        typer.Option("--printer", "-p", help="Printer/process id from 3d-print-work/data/printers."),
    ] = DEFAULT_PRINT_PRINTER_ID,
    material: Annotated[
        str,
        typer.Option("--material", "-m", help="Print material policy to apply."),
    ] = DEFAULT_PRINT_MATERIAL,
    run_id: Annotated[
        str | None,
        typer.Option("--run-id", help="Optional deterministic print package run id."),
    ] = None,
    manifest_path: Annotated[
        Path,
        typer.Option("--manifest", help="Generated CAD manifest path."),
    ] = DEFAULT_OUTPUT_DIR / "manifest.json",
    fusion_summary_path: Annotated[
        Path,
        typer.Option("--fusion-summary", help="Fusion run summary path for selected renders."),
    ] = DEFAULT_FUSION_SUMMARY,
    assembly_docs_path: Annotated[
        Path | None,
        typer.Option(
            "--assembly-docs",
            help="Fusion assembly documentation manifest or run directory to include.",
        ),
    ] = None,
    data_dir: Annotated[Path, typer.Option(help="CAD data directory.")] = DEFAULT_DATA_DIR,
    out_root: Annotated[
        Path,
        typer.Option("--out-root", help="Print package output root."),
    ] = DEFAULT_PRINT_PACKAGE_ROOT,
    allow_experimental: Annotated[
        bool,
        typer.Option("--allow-experimental", help="Allow experimental material/printer policies."),
    ] = False,
    allow_blocked: Annotated[
        bool,
        typer.Option("--allow-blocked", help="Allow blocked material/printer policies where safe."),
    ] = False,
) -> None:
    """Create an internal-review STL/STEP print package without G-code."""

    bundle = _load_or_exit(None, data_dir)
    try:
        package = create_print_package(
            generated_manifest_path=manifest_path,
            fusion_summary_path=fusion_summary_path,
            concept_id=concept_id,
            printer_id=printer_id,
            run_id=run_id,
            bundle=bundle,
            material=material,
            output_root=out_root,
            assembly_docs_path=assembly_docs_path,
            allow_experimental=allow_experimental,
            allow_blocked=allow_blocked,
        )
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        console.print(f"[red]Print package creation failed:[/red]\n{exc}")
        raise typer.Exit(1) from exc

    console.print(f"Wrote {package['output_dir']}")
    console.print(
        f"Files: {len(package['files'])}; renders: {len(package['renders'])}; "
        f"assembly docs: {len(package.get('assembly_docs', []))}"
    )


@app.command("k1-probe")
def k1_probe(
    host: Annotated[
        str,
        typer.Option("--host", help="K1 host or IP address to probe read-only."),
    ] = DEFAULT_K1_HOST,
    port: Annotated[
        list[int] | None,
        typer.Option("--port", help="HTTP port to probe. Can be repeated."),
    ] = None,
    run_id: Annotated[
        str | None,
        typer.Option("--run-id", help="Optional deterministic monitoring run id."),
    ] = None,
    out_root: Annotated[
        Path,
        typer.Option("--out-root", help="K1 monitoring output root."),
    ] = DEFAULT_K1_MONITOR_ROOT,
    timeout_seconds: Annotated[
        float,
        typer.Option("--timeout", help="Per-endpoint HTTP timeout in seconds."),
    ] = 2.0,
) -> None:
    """Probe K1 camera/webcam endpoints with read-only GET requests."""

    try:
        manifest = probe_k1_camera(
            host=host,
            ports=tuple(port or DEFAULT_K1_PORTS),
            output_root=out_root,
            run_id=run_id,
            timeout_seconds=timeout_seconds,
        )
    except RuntimeError as exc:
        console.print(f"[red]K1 probe failed:[/red]\n{exc}")
        raise typer.Exit(1) from exc

    color = "green" if manifest["status"] == "reachable" else "yellow"
    console.print(f"[{color}]K1 probe status: {manifest['status']}[/]")
    console.print(f"Wrote {manifest['output_dir']}")


@app.command("k1-monitor")
def k1_monitor(
    host: Annotated[
        str,
        typer.Option("--host", help="K1 host or IP address to monitor read-only."),
    ] = DEFAULT_K1_HOST,
    port: Annotated[
        list[int] | None,
        typer.Option("--port", help="HTTP port to probe. Can be repeated."),
    ] = None,
    run_id: Annotated[
        str | None,
        typer.Option("--run-id", help="Optional deterministic monitoring run id."),
    ] = None,
    out_root: Annotated[
        Path,
        typer.Option("--out-root", help="K1 monitoring output root."),
    ] = DEFAULT_K1_MONITOR_ROOT,
    timeout_seconds: Annotated[
        float,
        typer.Option("--timeout", help="Per-endpoint HTTP timeout in seconds."),
    ] = 2.0,
    stream_frames: Annotated[
        int,
        typer.Option("--stream-frames", help="Maximum OpenCV frames to sample from one stream."),
    ] = 3,
) -> None:
    """Capture read-only K1 probe data plus first-pass frame quality metrics."""

    try:
        session = monitor_k1_camera(
            host=host,
            ports=tuple(port or DEFAULT_K1_PORTS),
            output_root=out_root,
            run_id=run_id,
            timeout_seconds=timeout_seconds,
            stream_frames=stream_frames,
        )
    except RuntimeError as exc:
        console.print(f"[red]K1 monitor failed:[/red]\n{exc}")
        raise typer.Exit(1) from exc

    console.print(f"Wrote {session['output_dir']}")
    console.print(f"Snapshot metrics: {len(session['snapshot_metrics'])}")
    console.print(f"Stream metrics: {len(session['stream_metrics'])}")


@app.command("inspect-mesh")
def inspect_mesh(
    paths: Annotated[
        list[Path] | None,
        typer.Argument(help="STL/3MF files or directories. Defaults to generated CAD output."),
    ] = None,
) -> None:
    """Inspect STL/3MF mesh health with trimesh."""

    try:
        records = inspect_meshes(paths or [DEFAULT_OUTPUT_DIR])
    except (RuntimeError, FileNotFoundError) as exc:
        console.print(f"[red]Mesh inspection failed:[/red]\n{exc}")
        raise typer.Exit(1) from exc

    if not records:
        console.print("[yellow]No mesh files found.[/yellow]")
        raise typer.Exit(1)

    table = Table(title="Mesh Inspection")
    table.add_column("Path")
    table.add_column("Watertight")
    table.add_column("Faces")
    table.add_column("Extents mm")
    table.add_column("Broken faces")
    failed = False
    for record in records:
        if not record["watertight"] or record["broken_faces"]:
            failed = True
        table.add_row(
            record["path"],
            str(record["watertight"]),
            str(record["faces"]),
            json.dumps(record["extents_mm"]),
            str(record["broken_faces"]),
        )
    console.print(table)
    if failed:
        raise typer.Exit(1)


@app.command("fusion-job")
def fusion_job(
    manifest_path: Annotated[
        Path,
        typer.Option(
            "--manifest",
            "-m",
            help="Generated CAD manifest path.",
        ),
    ] = DEFAULT_OUTPUT_DIR / "manifest.json",
    out: Annotated[
        Path,
        typer.Option("--out", "-o", help="Fusion job JSON output path."),
    ] = DEFAULT_FUSION_JOB,
    keep_open_for_review: Annotated[
        bool,
        typer.Option(
            "--keep-open-for-review",
            help="Leave generated Fusion documents open intentionally for manual review.",
        ),
    ] = False,
) -> None:
    """Create a Fusion desktop render/export job JSON file."""

    try:
        job = create_fusion_job(
            manifest_path,
            out,
            keep_open_for_review=keep_open_for_review,
        )
    except FileNotFoundError as exc:
        console.print(f"[red]Fusion job creation failed:[/red]\n{exc}")
        raise typer.Exit(1) from exc
    console.print(f"Wrote {out} with {len(job['artifacts'])} artifact(s).")


@app.command("fusion-install")
def fusion_install(
    job_path: Annotated[
        Path,
        typer.Option("--job", "-j", help="Fusion job JSON path."),
    ] = DEFAULT_FUSION_JOB,
    addin_dir: Annotated[
        Path | None,
        typer.Option(
            "--addin-dir",
            help="Installed CBBSFusionAutomation directory. Defaults to Fusion's AddIns folder.",
        ),
    ] = None,
) -> None:
    """Sync the Fusion desktop add-in and point it at the current job."""

    try:
        result = install_fusion_addin(job_path=job_path, addin_dir=addin_dir)
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        console.print(f"[red]Fusion add-in install failed:[/red]\n{exc}")
        raise typer.Exit(1) from exc

    console.print(f"Installed add-in: {result['installed_dir']}")
    console.print(f"Manifest: {result['manifest']}")
    console.print(f"Job pointer: {result['job_pointer']} -> {result['job_path']}")
    console.print("Fusion was not restarted. Restart or run the add-in manually only when approved.")


@app.command("fusion-status")
def fusion_status(
    job_path: Annotated[
        Path,
        typer.Option("--job", "-j", help="Fusion job JSON path."),
    ] = DEFAULT_FUSION_JOB,
    addin_dir: Annotated[
        Path | None,
        typer.Option(
            "--addin-dir",
            help="Installed CBBSFusionAutomation directory. Defaults to Fusion's AddIns folder.",
        ),
    ] = None,
) -> None:
    """Check generated Fusion job, installed add-in, logs, renders, and exports."""

    results = check_fusion_status(job_path=job_path, addin_dir=addin_dir)
    table = Table(title="Fusion Desktop Automation Status")
    table.add_column("Check")
    table.add_column("Status")
    table.add_column("Detail")
    failed = False
    for result in results:
        failed = failed or not result.ok
        table.add_row(
            result.name,
            "[green]ok[/green]" if result.ok else "[red]fail[/red]",
            result.detail,
        )
    console.print(table)
    if failed:
        raise typer.Exit(1)


@app.command("fusion-smoke")
def fusion_smoke(
    job_path: Annotated[
        Path,
        typer.Option("--job", "-j", help="Fusion job JSON path."),
    ] = DEFAULT_FUSION_JOB,
    timeout_seconds: Annotated[
        int,
        typer.Option("--timeout", help="Seconds to wait for a new Fusion log."),
    ] = 300,
    poll_seconds: Annotated[
        float,
        typer.Option("--poll", help="Polling interval in seconds."),
    ] = 2.0,
) -> None:
    """Wait for a new Fusion log after the user starts or manually runs Fusion."""

    console.print(
        "Waiting for a new Fusion log. Start/restart Fusion or run the add-in manually; "
        "this command will not control the Fusion process."
    )
    try:
        log_path = wait_for_new_fusion_log(
            job_path=job_path,
            timeout_seconds=timeout_seconds,
            poll_seconds=poll_seconds,
        )
    except (FileNotFoundError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        console.print(f"[red]Fusion smoke check failed:[/red]\n{exc}")
        raise typer.Exit(1) from exc
    console.print(f"New Fusion log: {log_path}")
    console.print(f"Installed add-in default: {default_installed_addin_dir()}")


@app.command("fusion-agent-status")
def fusion_agent_status_command(
    job_path: Annotated[
        Path,
        typer.Option("--job", "-j", help="Fusion job JSON path."),
    ] = DEFAULT_FUSION_JOB,
    addin_dir: Annotated[
        Path | None,
        typer.Option(
            "--addin-dir",
            help="Installed CBBSFusionAutomation directory. Defaults to Fusion's AddIns folder.",
        ),
    ] = None,
    stale_seconds: Annotated[
        float,
        typer.Option("--stale-seconds", help="Heartbeat age threshold for a live agent bridge."),
    ] = 20.0,
    as_json: Annotated[
        bool,
        typer.Option("--json", help="Print machine-readable status JSON."),
    ] = False,
) -> None:
    """Check Fusion process, installed bridge, and agent heartbeat state."""

    try:
        status = fusion_agent_status(
            job_path=job_path,
            addin_dir=addin_dir,
            stale_seconds=stale_seconds,
        )
    except (RuntimeError, json.JSONDecodeError, ValueError) as exc:
        console.print(f"[red]Fusion agent status failed:[/red]\n{exc}")
        raise typer.Exit(1) from exc

    if as_json:
        console.print_json(json.dumps(status))
    else:
        table = Table(title="Fusion Agent Status")
        table.add_column("Check")
        table.add_column("Status")
        table.add_column("Detail")
        failed = False
        for result in status["checks"]:
            ok = bool(result["ok"])
            failed = failed or not ok
            table.add_row(
                result["name"],
                "[green]ok[/green]" if ok else "[red]fail[/red]",
                result["detail"],
            )
        console.print(table)
        console.print(f"Agent root: {status['agent_root']}")
        if failed:
            raise typer.Exit(1)


@app.command("fusion-agent-run")
def fusion_agent_run(
    action: Annotated[
        str,
        typer.Option(
            "--action",
            help=(
                "Agent bridge action: run_job, cleanup_owned_documents, open_artifact, "
                "open_assembly_artifact, capture_viewport, ui_state, export_active_archive, "
                "command_inventory, activate_workspace, execute_command_id, execute_text_command."
            ),
        ),
    ] = "run_job",
    job_path: Annotated[
        Path,
        typer.Option("--job", "-j", help="Fusion job JSON path."),
    ] = DEFAULT_FUSION_JOB,
    artifact_id: Annotated[
        str | None,
        typer.Option("--artifact-id", help="Artifact concept id for open_artifact/open_assembly_artifact."),
    ] = None,
    path: Annotated[
        Path | None,
        typer.Option("--path", help="File path for open_artifact or output path for capture_viewport."),
    ] = None,
    command_id: Annotated[
        str | None,
        typer.Option("--command-id", help="Fusion commandDefinition id for execute_command_id."),
    ] = None,
    workspace_id: Annotated[
        str | None,
        typer.Option("--workspace-id", help="Fusion workspace id for activate_workspace."),
    ] = None,
    query: Annotated[
        str | None,
        typer.Option("--query", help="Search query for command_inventory."),
    ] = None,
    max_items: Annotated[
        int,
        typer.Option("--max-items", help="Maximum command_inventory matches."),
    ] = 250,
    text_command: Annotated[
        str | None,
        typer.Option("--text-command", help="Fusion text command. Requires --allow-text-command."),
    ] = None,
    allow_text_command: Annotated[
        bool,
        typer.Option("--allow-text-command", help="Permit execute_text_command."),
    ] = False,
    allow_restart: Annotated[
        bool,
        typer.Option("--allow-restart", help="Restart Fusion if the agent bridge heartbeat is stale."),
    ] = False,
    allow_unsaved_close: Annotated[
        bool,
        typer.Option(
            "--allow-unsaved-close",
            help="Allow managed restart to close unsaved Fusion windows.",
        ),
    ] = False,
    timeout_seconds: Annotated[
        int,
        typer.Option("--timeout", help="Seconds to wait for the agent response."),
    ] = 1200,
) -> None:
    """Enqueue a command for the Fusion add-in bridge and wait for its response."""

    payload: dict[str, object] = {}
    if artifact_id:
        payload["artifact_id"] = artifact_id
    if path:
        if is_url_like_path(path):
            console.print_json(
                json.dumps(
                    {
                        "schema": "cbbs-cad/fusion-agent-response/v1",
                        "action": action,
                        "status": "unsupported_url_path",
                        "path": str(path),
                    }
                )
            )
            raise typer.Exit(1)
        payload_path = path
        if action == "open_artifact":
            try:
                payload_path = resolve_local_artifact_path(path)
            except FileNotFoundError as exc:
                console.print_json(
                    json.dumps(
                        {
                            "schema": "cbbs-cad/fusion-agent-response/v1",
                            "action": action,
                            "status": "missing",
                            "path": str(path),
                            "error": str(exc),
                        }
                    )
                )
                raise typer.Exit(1) from exc
        payload["path"] = job_pointer_value(payload_path)
        if action == "capture_viewport":
            payload["output_path"] = job_pointer_value(path)
    if command_id:
        payload["command_id"] = command_id
    if workspace_id:
        payload["workspace_id"] = workspace_id
    if query:
        payload["query"] = query
    if action == "command_inventory":
        payload["max_items"] = max_items
    if text_command:
        payload["text_command"] = text_command
    if allow_text_command:
        payload["allow_text_command"] = True

    try:
        status = fusion_agent_status(job_path=job_path)
        if allow_restart and not status["heartbeat_fresh"]:
            restart_fusion(
                job_path=job_path,
                allow_unsaved_close=allow_unsaved_close,
                install_first=True,
            )
        request_id, request_path = enqueue_agent_command(
            action,
            job_path=job_path,
            payload=payload,
        )
        console.print(f"Queued Fusion agent request: {request_path}")
        response = wait_for_agent_response(
            request_id,
            job_path=job_path,
            timeout_seconds=timeout_seconds,
        )
    except (RuntimeError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
        console.print(f"[red]Fusion agent run failed:[/red]\n{exc}")
        raise typer.Exit(1) from exc

    console.print_json(json.dumps(response))
    if response.get("status") not in {"completed", "ok"}:
        raise typer.Exit(1)


@app.command("fusion-agent-restart")
def fusion_agent_restart(
    job_path: Annotated[
        Path,
        typer.Option("--job", "-j", help="Fusion job JSON path."),
    ] = DEFAULT_FUSION_JOB,
    allow_unsaved_close: Annotated[
        bool,
        typer.Option("--allow-unsaved-close", help="Allow closing unsaved Fusion windows."),
    ] = False,
    allow_force: Annotated[
        bool,
        typer.Option("--allow-force", help="Force-kill Fusion if graceful close times out."),
    ] = False,
    timeout_seconds: Annotated[
        int,
        typer.Option("--timeout", help="Seconds to wait for graceful close."),
    ] = 90,
    start_only: Annotated[
        bool,
        typer.Option("--start-only", help="Start Fusion without closing any existing process."),
    ] = False,
) -> None:
    """Start or explicitly managed-restart Fusion for the agent bridge."""

    try:
        if start_only:
            log_path = start_fusion(job_path=job_path, reason="agent-start-only")
        else:
            log_path = restart_fusion(
                job_path=job_path,
                allow_unsaved_close=allow_unsaved_close,
                allow_force=allow_force,
                timeout_seconds=timeout_seconds,
            )
    except RuntimeError as exc:
        console.print(f"[red]Fusion managed restart failed:[/red]\n{exc}")
        raise typer.Exit(1) from exc
    console.print(f"Fusion process action log: {log_path}")


@app.command("fusion-ui-snapshot")
def fusion_ui_snapshot_command(
    process_id: Annotated[
        int | None,
        typer.Option("--process-id", help="Fusion process id. Defaults to the first Fusion360 process."),
    ] = None,
    max_depth: Annotated[int, typer.Option("--max-depth", help="UIA tree depth.")] = 4,
    max_nodes: Annotated[int, typer.Option("--max-nodes", help="Maximum UIA nodes.")] = 300,
) -> None:
    """Print a Windows UI Automation snapshot of the Fusion window."""

    try:
        snapshot = fusion_ui_snapshot(
            process_id=process_id,
            max_depth=max_depth,
            max_nodes=max_nodes,
        )
    except (RuntimeError, json.JSONDecodeError, ValueError) as exc:
        console.print(f"[red]Fusion UIA snapshot failed:[/red]\n{exc}")
        raise typer.Exit(1) from exc
    console.print_json(json.dumps(snapshot))


@app.command("fusion-ui-invoke")
def fusion_ui_invoke_command(
    name: Annotated[
        str | None,
        typer.Option("--name", help="UIA element name to target."),
    ] = None,
    automation_id: Annotated[
        str | None,
        typer.Option("--automation-id", help="UIA AutomationId to target."),
    ] = None,
    control_type: Annotated[
        str | None,
        typer.Option("--control-type", help="Optional UIA control type, such as ControlType.Button."),
    ] = None,
    process_id: Annotated[
        int | None,
        typer.Option("--process-id", help="Fusion process id. Defaults to the first Fusion360 process."),
    ] = None,
    allow_click: Annotated[
        bool,
        typer.Option("--allow-click", help="Click the target center if InvokePattern is unavailable."),
    ] = False,
    allow_keys: Annotated[
        bool,
        typer.Option("--allow-keys", help="Permit sending keys to the focused target."),
    ] = False,
    keys: Annotated[
        str | None,
        typer.Option("--keys", help="SendKeys payload. Requires --allow-keys."),
    ] = None,
    close_window: Annotated[
        bool,
        typer.Option("--close-window", help="Close the Fusion main window through UIA."),
    ] = False,
    allow_close_window: Annotated[
        bool,
        typer.Option("--allow-close-window", help="Required with --close-window."),
    ] = False,
) -> None:
    """Invoke or guarded-click a Fusion UI element through Windows UI Automation."""

    try:
        result = fusion_ui_invoke(
            name=name,
            automation_id=automation_id,
            control_type=control_type,
            process_id=process_id,
            allow_click=allow_click,
            allow_keys=allow_keys,
            keys=keys,
            close_window=close_window,
            allow_close_window=allow_close_window,
        )
    except (RuntimeError, json.JSONDecodeError, ValueError) as exc:
        console.print(f"[red]Fusion UIA invoke failed:[/red]\n{exc}")
        raise typer.Exit(1) from exc
    console.print_json(json.dumps(result))
    if result.get("status") in {"missing-process", "missing-window", "missing-target"}:
        raise typer.Exit(1)
