from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cbbs_cad.specs import REPO_ROOT

DEFAULT_FUSION_JOB = REPO_ROOT / "3d-print-work" / "generated" / "fusion" / "latest-job.json"
DEFAULT_DOCUMENT_LIFECYCLE = {
    "owner": "cbbs-cad",
    "close_generated_documents": True,
    "keep_open_for_review": False,
    "save_policy": "discard_generated",
    "allow_user_prompt": False,
}


def _windows_path(path: Path) -> str | None:
    resolved = path.resolve()
    parts = resolved.parts
    if len(parts) >= 3 and parts[0] == "/" and parts[1] == "mnt" and len(parts[2]) == 1:
        drive = parts[2].upper()
        rest = "\\".join(parts[3:])
        return f"{drive}:\\{rest}"
    return None


def _relative_or_absolute(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def _new_run_id() -> str:
    return f"fusion-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def _artifact_record(artifact: dict[str, Any]) -> dict[str, Any]:
    record = {
        "concept_id": artifact["concept_id"],
        "name": artifact["name"],
        "truth_state": artifact["truth_state"],
        "measurement_status": artifact["measurement_status"],
        "files": artifact["files"],
    }
    if artifact.get("assembly"):
        record["assembly"] = artifact["assembly"]
    return record


def _assembly_artifacts(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for artifact in artifacts:
        assembly = artifact.get("assembly")
        if not isinstance(assembly, dict):
            continue
        records.append(
            {
                "concept_id": artifact.get("concept_id", ""),
                "name": artifact.get("name", ""),
                "parts": assembly.get("parts", []),
                "views": assembly.get("views", {}),
                "metadata": assembly.get("metadata", {}),
            }
        )
    return records


def _render_view_key(artifact: dict[str, Any], view: str) -> str:
    concept_id = str(artifact.get("concept_id", "assembly")) or "assembly"
    return f"{concept_id}__{view}"


def _model_render_key(artifact: dict[str, Any]) -> str:
    concept_id = str(artifact.get("concept_id", "model")) or "model"
    return f"{concept_id}__model"


def _render_view_sources(artifacts: list[dict[str, Any]]) -> dict[str, str]:
    sources: dict[str, str] = {}
    for artifact in artifacts:
        files = artifact.get("files", {})
        step_file = files.get("step") if isinstance(files, dict) else None
        if step_file:
            sources[_model_render_key(artifact)] = str(step_file)

        assembly = artifact.get("assembly", {})
        view_records = assembly.get("views", {}) if isinstance(assembly, dict) else {}
        if not isinstance(view_records, dict):
            continue
        for view, record in view_records.items():
            if isinstance(record, dict) and record.get("file"):
                sources[_render_view_key(artifact, view)] = str(record["file"])
    return sources


def _render_views(artifacts: list[dict[str, Any]]) -> list[str]:
    render_sources = _render_view_sources(artifacts)
    if render_sources:
        return list(render_sources)
    return ["front", "isometric"]


def _print_layouts(assembly_artifacts: list[dict[str, Any]]) -> dict[str, Any]:
    layouts: dict[str, Any] = {}
    for artifact in assembly_artifacts:
        metadata = artifact.get("metadata", {})
        if not isinstance(metadata, dict):
            continue
        artifact_layouts = metadata.get("print_layouts", {})
        if isinstance(artifact_layouts, dict):
            for name, record in artifact_layouts.items():
                layouts[name] = record
    return layouts


def _document_lifecycle(run_id: str, keep_open_for_review: bool) -> dict[str, Any]:
    lifecycle = {**DEFAULT_DOCUMENT_LIFECYCLE, "run_id": run_id}
    if keep_open_for_review:
        lifecycle["keep_open_for_review"] = True
        lifecycle["close_generated_documents"] = False
        lifecycle["review_status"] = "generated documents intentionally left open for manual review"
    return lifecycle


def create_fusion_job(
    generated_manifest_path: Path,
    output_path: Path = DEFAULT_FUSION_JOB,
    *,
    keep_open_for_review: bool = False,
) -> dict[str, Any]:
    manifest = json.loads(generated_manifest_path.read_text(encoding="utf-8"))
    artifacts = manifest.get("artifacts", [])
    assembly_artifacts = _assembly_artifacts(artifacts)
    render_view_sources = _render_view_sources(artifacts)
    render_views = _render_views(artifacts)
    print_layouts = _print_layouts(assembly_artifacts)
    run_id = _new_run_id()

    job = {
        "schema": "cbbs-cad/fusion-job/v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "truth_state": "internal review",
        "repo_root": str(REPO_ROOT),
        "repo_root_windows": _windows_path(REPO_ROOT),
        "source_manifest": _relative_or_absolute(generated_manifest_path),
        "output_root": "3d-print-work/generated/fusion",
        "document_mode": "new",
        "document_lifecycle": _document_lifecycle(run_id, keep_open_for_review),
        "ui_message_box": False,
        "wait_for_renders": True,
        "summary_path": "run-summary.json",
        "assembly": {
            "enabled": bool(assembly_artifacts),
            "artifacts": assembly_artifacts,
        },
        "print_layouts": print_layouts,
        "render": {
            "enabled": True,
            "mode": "per-artifact-source",
            "backend": "viewport_capture",
            "isolate_view_sources": True,
            "resolution": "Mobile960x640RenderResolution",
            "views": render_views,
            "timeout_seconds": 900,
            "outputs": {
                view: f"renders/{run_id}-{view}.png"
                for view in render_views
            },
            "view_sources": render_view_sources,
        },
        "exports": {
            "step": True,
            "stl": True,
            "outputs": {
                "step": f"exports/{run_id}-review.step",
                "stl": f"exports/{run_id}-review.stl",
            },
        },
        "materials": {
            "default": "source-derived fit-test plastic",
            "appearance_hint": "matte neutral gray",
        },
        "artifacts": [_artifact_record(artifact) for artifact in artifacts],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
    return job
