from __future__ import annotations

import json
import os
import re
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

import adsk.core
import adsk.fusion

AGENT_COMMAND_SCHEMA = "cbbs-cad/fusion-agent-command/v1"
AGENT_RESPONSE_SCHEMA = "cbbs-cad/fusion-agent-response/v1"
AGENT_HEARTBEAT_SCHEMA = "cbbs-cad/fusion-agent-heartbeat/v1"
AGENT_EVENT_ID = "cbbs.cad.fusion.agent.command"
CBBS_ATTR_GROUP = "cbbs-cad"
CBBS_OWNER = "cbbs-cad"
WINDOWS_PATH_RE = re.compile(r"^([A-Za-z]):[\\/](.*)$")
URL_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")

_handlers = []
_agent_bridge = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _resolve_job_path(repo_root: Path) -> Path:
    addin_dir = Path(__file__).resolve().parent
    override = addin_dir / "job_path.txt"
    if override.exists():
        raw_path = override.read_text(encoding="utf-8").strip()
        if raw_path:
            path = Path(raw_path)
            return path if path.is_absolute() else repo_root / path
    return repo_root / "3d-print-work" / "generated" / "fusion" / "latest-job.json"


def _load_job(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _job_repo_root(fallback_root: Path, job: dict) -> Path:
    raw_root = job.get("repo_root_windows") or job.get("repo_root")
    if not raw_root:
        return fallback_root
    return Path(raw_root)


def _output_root(repo_root: Path, job: dict) -> Path:
    root = Path(job.get("output_root", "3d-print-work/generated/fusion"))
    if not root.is_absolute():
        root = repo_root / root
    root.mkdir(parents=True, exist_ok=True)
    return root


def _log_path(output_root: Path, run_id: str) -> Path:
    logs = output_root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = f"-{run_id}" if run_id else ""
    return logs / f"fusion-job-{stamp}{suffix}.log"


def _write_log(log_file: Path, message: str) -> None:
    with log_file.open("a", encoding="utf-8") as handle:
        handle.write(message.rstrip() + "\n")


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp_path.replace(path)


def _localize_agent_path(raw_path: str | Path) -> Path:
    raw = str(raw_path)
    if raw.startswith("/mnt/") and len(raw) > 7 and raw[6] == "/":
        drive = raw[5].upper()
        rest = raw[7:].replace("/", "\\")
        return Path(f"{drive}:\\{rest}")
    return Path(raw)


def _looks_like_url_path(raw_path: str | Path | None) -> bool:
    if raw_path is None:
        return False
    raw = str(raw_path).strip()
    if not raw:
        return False
    if WINDOWS_PATH_RE.match(raw):
        return False
    normalized = raw.replace("\\", "/")
    return bool(URL_SCHEME_RE.match(normalized))


def _unsupported_url_path(raw_path: str | Path | None) -> dict:
    return {
        "status": "unsupported_url_path",
        "path": str(raw_path) if raw_path is not None else "",
        "error": "Only local filesystem paths or artifact IDs are supported.",
    }


def _resolve_local_file_path(repo_root: Path, raw_path: str | Path) -> Path:
    if _looks_like_url_path(raw_path):
        raise ValueError(f"unsupported_url_path: {raw_path}")
    path = _localize_agent_path(raw_path)
    return path if path.is_absolute() else repo_root / path


def _lifecycle_policy(job: dict) -> dict:
    policy = {
        "owner": CBBS_OWNER,
        "close_generated_documents": True,
        "keep_open_for_review": False,
        "save_policy": "discard_generated",
        "allow_user_prompt": False,
    }
    raw_policy = job.get("document_lifecycle", {})
    if isinstance(raw_policy, dict):
        policy.update(raw_policy)
    return policy


def _safe_attr(target, group: str, name: str) -> str | None:
    try:
        attrs = getattr(target, "attributes", None)
        if not attrs:
            return None
        item = attrs.itemByName(group, name)
        return item.value if item else None
    except Exception:
        return None


def _tag_entity(target, job: dict, role: str, label: str | None = None) -> bool:
    try:
        attrs = getattr(target, "attributes", None)
        if not attrs:
            return False
        run_id = str(job.get("run_id", ""))
        attrs.add(CBBS_ATTR_GROUP, "owner", CBBS_OWNER)
        attrs.add(CBBS_ATTR_GROUP, "run_id", run_id)
        attrs.add(CBBS_ATTR_GROUP, "role", role)
        attrs.add(CBBS_ATTR_GROUP, "save_policy", _lifecycle_policy(job).get("save_policy", ""))
        if label:
            attrs.add(CBBS_ATTR_GROUP, "label", label)
        return True
    except Exception:
        return False


def _design_from_document(document) -> adsk.fusion.Design | None:
    try:
        return adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
    except Exception:
        return None


def _generated_document_name(job: dict, role: str) -> str:
    run_id = str(job.get("run_id", "fusion-review")) or "fusion-review"
    safe_role = role.replace("_", "-")
    return f"CBBS generated {run_id} {safe_role}"


def _prepare_generated_document(
    document,
    job: dict,
    role: str,
    log_file: Path | None = None,
) -> None:
    label = _generated_document_name(job, role)
    try:
        if not getattr(document, "isSaved", False):
            document.name = label
    except Exception:
        if log_file:
            _write_log(log_file, f"Failed to set generated document name {label}")
    _tag_entity(document, job, role, label)
    design = _design_from_document(document)
    if design and design.rootComponent:
        try:
            design.rootComponent.name = label
        except Exception:
            pass
        _tag_entity(design.rootComponent, job, role, label)


def _document_state(app: adsk.core.Application, document) -> dict:
    try:
        is_valid = bool(getattr(document, "isValid", True))
    except Exception:
        is_valid = False
    if not is_valid:
        return {
            "name": None,
            "isValid": False,
            "isSaved": False,
            "isModified": False,
            "isVisible": False,
            "isActive": False,
            "owner": None,
            "run_id": None,
            "role": None,
            "label": None,
            "cbbs_owned": False,
        }
    design = _design_from_document(document)
    root = design.rootComponent if design else None
    owner = _safe_attr(document, CBBS_ATTR_GROUP, "owner") or (
        _safe_attr(root, CBBS_ATTR_GROUP, "owner") if root else None
    )
    run_id = _safe_attr(document, CBBS_ATTR_GROUP, "run_id") or (
        _safe_attr(root, CBBS_ATTR_GROUP, "run_id") if root else None
    )
    role = _safe_attr(document, CBBS_ATTR_GROUP, "role") or (
        _safe_attr(root, CBBS_ATTR_GROUP, "role") if root else None
    )
    label = _safe_attr(document, CBBS_ATTR_GROUP, "label") or (
        _safe_attr(root, CBBS_ATTR_GROUP, "label") if root else None
    )
    try:
        name = getattr(document, "name", "")
    except Exception:
        name = ""
    try:
        is_saved = bool(getattr(document, "isSaved", False))
    except Exception:
        is_saved = False
    try:
        is_modified = bool(getattr(document, "isModified", False))
    except Exception:
        is_modified = False
    try:
        is_visible = bool(getattr(document, "isVisible", True))
    except Exception:
        is_visible = False
    cbbs_owned = owner == CBBS_OWNER or str(name).startswith("CBBS generated ")
    return {
        "name": name,
        "isValid": True,
        "isSaved": is_saved,
        "isModified": is_modified,
        "isVisible": is_visible,
        "isActive": document == app.activeDocument,
        "owner": owner,
        "run_id": run_id,
        "role": role,
        "label": label,
        "cbbs_owned": cbbs_owned,
    }


def _document_inventory(app: adsk.core.Application) -> list[dict]:
    records = []
    try:
        documents = app.documents
        for index in range(documents.count):
            try:
                document = documents.item(index)
            except Exception as exc:
                records.append(
                    {
                        "status": "skipped_invalid_document_proxy",
                        "index": index,
                        "error": str(exc),
                    }
                )
                continue
            if document:
                records.append(_document_state(app, document))
    except Exception as exc:
        records.append({"status": "inventory_failed", "error": str(exc)})
    return records


def _close_owned_documents(
    app: adsk.core.Application,
    job: dict,
    log_file: Path | None = None,
    *,
    run_id_only: bool = True,
) -> list[dict]:
    policy = _lifecycle_policy(job)
    current_run_id = str(job.get("run_id", ""))
    documents = []
    try:
        for index in range(app.documents.count):
            try:
                document = app.documents.item(index)
            except Exception as exc:
                documents.append(
                    {
                        "status": "skipped_invalid_document_proxy",
                        "index": index,
                        "error": str(exc),
                    }
                )
                continue
            if document:
                documents.append(document)
    except Exception as exc:
        return [{"status": "failed", "error": f"document inventory failed: {exc}"}]

    records = []
    for document in documents:
        if isinstance(document, dict):
            records.append(document)
            continue
        state = _document_state(app, document)
        if not state.get("isValid", True):
            records.append({**state, "status": "skipped_invalid_document"})
            continue
        if not state.get("cbbs_owned"):
            continue
        if run_id_only and current_run_id and state.get("run_id") not in {current_run_id, None, ""}:
            continue
        record = {
            **state,
            "save_policy": policy.get("save_policy"),
            "close_attempted": False,
            "close_result": None,
        }
        if policy.get("keep_open_for_review") and run_id_only:
            record["status"] = "kept_open_for_review"
            records.append(record)
            continue
        if not policy.get("close_generated_documents", True) and run_id_only:
            record["status"] = "left_open_by_policy"
            records.append(record)
            continue
        try:
            record["close_attempted"] = True
            record["close_result"] = bool(document.close(False))
            record["status"] = "closed" if record["close_result"] else "close_failed"
        except Exception as exc:
            record["status"] = "close_failed"
            record["error"] = str(exc)
        if log_file:
            _write_log(
                log_file,
                f"Generated document cleanup {record.get('name')}: {record.get('status')}",
            )
        records.append(record)
    return records


def _close_owned_document(
    app: adsk.core.Application,
    document,
    job: dict,
    log_file: Path | None = None,
) -> dict:
    policy = _lifecycle_policy(job)
    state = _document_state(app, document)
    record = {
        **state,
        "save_policy": policy.get("save_policy"),
        "close_attempted": False,
        "close_result": None,
    }
    if not state.get("cbbs_owned"):
        record["status"] = "skipped_not_cbbs_owned"
        return record
    if policy.get("keep_open_for_review"):
        record["status"] = "kept_open_for_review"
        return record
    if not policy.get("close_generated_documents", True):
        record["status"] = "left_open_by_policy"
        return record
    try:
        record["close_attempted"] = True
        record["close_result"] = bool(document.close(False))
        record["status"] = "closed" if record["close_result"] else "close_failed"
    except Exception as exc:
        record["status"] = "close_failed"
        record["error"] = str(exc)
    if log_file:
        _write_log(log_file, f"Generated document cleanup {record.get('name')}: {record.get('status')}")
    return record


def _active_design(app: adsk.core.Application) -> adsk.fusion.Design:
    product = app.activeProduct
    design = adsk.fusion.Design.cast(product)
    if design:
        return design
    active_document = getattr(app, "activeDocument", None)
    if active_document:
        design = _design_from_document(active_document)
        if design:
            return design
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    return adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))


def _design_for_job(
    app: adsk.core.Application,
    job: dict,
    role: str = "job",
    log_file: Path | None = None,
) -> adsk.fusion.Design:
    if job.get("document_mode", "new") == "active":
        return _active_design(app)
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    _prepare_generated_document(document, job, role, log_file)
    return adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))


def _artifact_file(repo_root: Path, artifact: dict) -> Path | None:
    files = artifact.get("files", {})
    raw = files.get("step") or files.get("stl")
    if not raw:
        return None
    return _resolve_local_file_path(repo_root, raw)


def _repo_relative_path(repo_root: Path, raw: str | Path) -> Path:
    return _resolve_local_file_path(repo_root, raw)


def _iter_import_artifacts(job: dict) -> list[dict]:
    records = []
    for artifact in job.get("artifacts", []):
        assembly = artifact.get("assembly", {})
        parts = assembly.get("parts", []) if isinstance(assembly, dict) else []
        if parts:
            for part in parts:
                if not isinstance(part, dict):
                    continue
                records.append(
                    {
                        "concept_id": f"{artifact.get('concept_id', '')}:{part.get('id', '')}",
                        "name": part.get("name", ""),
                        "truth_state": artifact.get("truth_state", ""),
                        "measurement_status": artifact.get("measurement_status", ""),
                        "files": part.get("files", {}),
                        "assembly_parent_id": artifact.get("concept_id", ""),
                        "assembly_part_id": part.get("id", ""),
                        "role": part.get("role", ""),
                        "occurrence": part.get("occurrence", {}),
                        "support_risk": part.get("support_risk", {}),
                    }
                )
        else:
            records.append(artifact)
    return records


def _matrix_from_occurrence(occurrence_cfg: dict) -> adsk.core.Matrix3D:
    matrix = adsk.core.Matrix3D.create()
    transform = occurrence_cfg.get("transform", {}) if isinstance(occurrence_cfg, dict) else {}
    translation = transform.get("translation_mm", {}) if isinstance(transform, dict) else {}
    if isinstance(translation, dict) and translation:
        try:
            matrix.translation = adsk.core.Vector3D.create(
                float(translation.get("x", 0.0)) / 10.0,
                float(translation.get("y", 0.0)) / 10.0,
                float(translation.get("z", 0.0)) / 10.0,
            )
        except Exception:
            pass
    return matrix


def _component_target_for_artifact(
    design: adsk.fusion.Design,
    artifact: dict,
    job: dict,
    log_file: Path,
):
    if not artifact.get("assembly_part_id"):
        return design.rootComponent, None
    occurrence_cfg = artifact.get("occurrence", {})
    occurrence_name = (
        occurrence_cfg.get("name")
        if isinstance(occurrence_cfg, dict) and occurrence_cfg.get("name")
        else artifact.get("name") or artifact.get("assembly_part_id")
    )
    try:
        occurrence = design.rootComponent.occurrences.addNewComponent(
            _matrix_from_occurrence(occurrence_cfg if isinstance(occurrence_cfg, dict) else {})
        )
        component = occurrence.component
        component.name = str(occurrence_name)
        try:
            occurrence.transform2 = _matrix_from_occurrence(
                occurrence_cfg if isinstance(occurrence_cfg, dict) else {}
            )
        except Exception:
            pass
        _tag_entity(component, job, "assembly_component", str(occurrence_name))
        _tag_entity(occurrence, job, "assembly_occurrence", str(occurrence_name))
        return component, {
            "component_name": component.name,
            "occurrence_name": getattr(occurrence, "name", ""),
            "label": str(occurrence_name),
            "occurrence_transform": occurrence_cfg,
        }
    except Exception as exc:
        _write_log(
            log_file,
            f"Failed to create component target for {artifact.get('concept_id')}: {exc}",
        )
        return design.rootComponent, {"component_error": str(exc)}


def _import_file_to_design(
    app: adsk.core.Application,
    design: adsk.fusion.Design,
    artifact_path: Path,
    concept_id: str,
    log_file: Path,
    target_component=None,
) -> dict:
    import_manager = app.importManager
    import_target = target_component or design.rootComponent
    suffix = artifact_path.suffix.lower()
    _write_log(log_file, f"Importing {artifact_path}")

    if suffix in {".step", ".stp"}:
        options = import_manager.createSTEPImportOptions(str(artifact_path))
        result = import_manager.importToTarget(options, import_target)
    elif suffix == ".stl":
        options = import_manager.createSTLImportOptions(str(artifact_path))
        result = import_manager.importToTarget(options, import_target)
    else:
        _write_log(log_file, f"Unsupported artifact type: {artifact_path}")
        return {
            "concept_id": concept_id,
            "path": str(artifact_path),
            "status": "unsupported",
            "result": None,
        }

    _write_log(log_file, f"Imported {artifact_path}; result={result}")
    return {
        "concept_id": concept_id,
        "path": str(artifact_path),
        "status": "imported",
        "result": bool(result),
    }


def _import_artifact(
    app: adsk.core.Application,
    design: adsk.fusion.Design,
    repo_root: Path,
    artifact: dict,
    job: dict,
    log_file: Path,
) -> dict:
    concept_id = artifact.get("concept_id", "")
    try:
        artifact_path = _artifact_file(repo_root, artifact)
    except ValueError as exc:
        raw_files = artifact.get("files", {})
        raw_path = ""
        if isinstance(raw_files, dict):
            raw_path = raw_files.get("step") or raw_files.get("stl") or ""
        if str(exc).startswith("unsupported_url_path"):
            _write_log(log_file, f"Unsupported URL-like artifact path for {concept_id}: {raw_path}")
            return {
                "concept_id": concept_id,
                "path": str(raw_path),
                "status": "unsupported_url_path",
                "result": None,
                "error": "Only local filesystem paths or artifact IDs are supported.",
            }
        raise
    if not artifact_path or not artifact_path.exists():
        _write_log(log_file, f"Missing artifact for {concept_id}: {artifact_path}")
        return {
            "concept_id": concept_id,
            "path": str(artifact_path),
            "status": "missing",
            "result": None,
        }

    target_component, component_record = _component_target_for_artifact(design, artifact, job, log_file)
    record = _import_file_to_design(
        app,
        design,
        artifact_path,
        concept_id,
        log_file,
        target_component=target_component,
    )
    for key in ("assembly_parent_id", "assembly_part_id", "role"):
        if artifact.get(key):
            record[key] = artifact[key]
    if component_record:
        record["component"] = component_record
    if artifact.get("support_risk"):
        record["support_risk"] = artifact["support_risk"]
    return record


def _set_render_resolution(job: dict, render: adsk.fusion.Rendering) -> None:
    resolution_name = job.get("render", {}).get("resolution", "Mobile960x640RenderResolution")
    if hasattr(adsk.fusion.RenderResolutions, resolution_name):
        render.resolution = getattr(adsk.fusion.RenderResolutions, resolution_name)


def _resolve_output_path(output_root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    return path if path.is_absolute() else output_root / path


def _render_output_path(job: dict, output_root: Path, view: str) -> Path:
    run_id = job.get("run_id", "fusion-review")
    outputs = job.get("render", {}).get("outputs", {})
    if isinstance(outputs, dict) and outputs.get(view):
        return _resolve_output_path(output_root, outputs[view])
    return output_root / "renders" / f"{run_id}-{view}.png"


def _save_viewport_render_fallback(viewport, filename: Path, log_file: Path) -> dict | None:
    if not viewport:
        return None
    try:
        try:
            result = viewport.saveAsImageFile(str(filename), 960, 640)
        except TypeError:
            result = viewport.saveAsImageFile(str(filename))
    except Exception as exc:
        _write_log(log_file, f"Viewport render fallback failed {filename}: {exc}")
        return {
            "fallback": "viewport_capture",
            "fallback_status": "failed",
            "fallback_error": str(exc),
        }
    if result and filename.exists():
        _write_log(log_file, f"Viewport render fallback wrote {filename}")
        return {"fallback": "viewport_capture", "fallback_status": "completed"}
    _write_log(log_file, f"Viewport render fallback did not write {filename}; result={result}")
    return {"fallback": "viewport_capture", "fallback_status": "missing", "result": bool(result)}


def _wait_for_render(
    future,
    filename: Path,
    timeout_seconds: int,
    log_file: Path,
    viewport=None,
    missing_output_fallback_seconds: int = 45,
) -> dict:
    started_at = time.time()
    last_logged_second = -1
    progress_complete_at = None

    while True:
        try:
            state = getattr(future, "renderState", None)
            progress = float(getattr(future, "progress", 0.0) or 0.0)
        except Exception as exc:
            elapsed = time.time() - started_at
            if filename.exists():
                _write_log(
                    log_file,
                    f"Render future unavailable after output appeared {filename}: {exc}",
                )
                return {
                    "path": str(filename),
                    "status": "completed",
                    "state": "unavailable",
                    "progress": 1.0,
                    "elapsed_seconds": round(elapsed, 3),
                    "future_error": str(exc),
                }
            _write_log(log_file, f"Render future failed {filename}: {exc}")
            return {
                "path": str(filename),
                "status": "failed",
                "state": "unavailable",
                "progress": 0.0,
                "elapsed_seconds": round(elapsed, 3),
                "error": str(exc),
            }
        elapsed = time.time() - started_at
        elapsed_second = int(elapsed)

        if elapsed_second >= last_logged_second + 10:
            _write_log(
                log_file,
                f"Render polling {filename}; state={state}; progress={progress}; "
                f"elapsed_seconds={elapsed_second}",
            )
            last_logged_second = elapsed_second

        if progress >= 1.0 and filename.exists():
            _write_log(log_file, f"Render completed {filename}; state={state}; progress={progress}")
            return {
                "path": str(filename),
                "status": "completed",
                "state": state,
                "progress": progress,
                "elapsed_seconds": round(elapsed, 3),
            }

        if progress >= 1.0:
            if progress_complete_at is None:
                progress_complete_at = time.time()
                _write_log(
                    log_file,
                    f"Render reached complete progress before output existed {filename}; "
                    "waiting before viewport fallback",
                )
            elif time.time() - progress_complete_at >= missing_output_fallback_seconds:
                fallback = _save_viewport_render_fallback(viewport, filename, log_file)
                if fallback and fallback.get("fallback_status") == "completed":
                    return {
                        "path": str(filename),
                        "status": "completed",
                        "state": state,
                        "progress": progress,
                        "elapsed_seconds": round(elapsed, 3),
                        "completion_mode": "viewport_fallback_after_missing_local_render",
                        **fallback,
                    }

        if elapsed >= timeout_seconds:
            _write_log(log_file, f"Render timed out {filename}; state={state}; progress={progress}")
            return {
                "path": str(filename),
                "status": "timeout",
                "state": state,
                "progress": progress,
                "elapsed_seconds": round(elapsed, 3),
            }

        adsk.doEvents()
        time.sleep(1)


def _start_local_renders(
    app: adsk.core.Application,
    design: adsk.fusion.Design,
    repo_root: Path,
    job: dict,
    output_root: Path,
    log_file: Path,
) -> list[dict]:
    render_cfg = job.get("render", {})
    if not render_cfg.get("enabled", True):
        _write_log(log_file, "Rendering disabled by job.")
        return [{"status": "disabled"}]

    renders = output_root / "renders"
    renders.mkdir(parents=True, exist_ok=True)
    views = render_cfg.get("views", ["front", "isometric"])
    view_sources = render_cfg.get("view_sources", {})
    wait_for_renders = bool(job.get("wait_for_renders", True))
    timeout_seconds = int(render_cfg.get("timeout_seconds", 900))
    backend = str(render_cfg.get("backend", "viewport_capture"))
    records = []

    for view in views:
        render_design = design
        render_document = None
        source_record = None
        if isinstance(view_sources, dict) and view_sources.get(view):
            raw_source_path = view_sources[view]
            if _looks_like_url_path(raw_source_path):
                source_record = _unsupported_url_path(raw_source_path)
                _write_log(log_file, f"Unsupported URL-like render view source for {view}: {raw_source_path}")
                records.append(
                    {
                        "view": view,
                        "path": str(_render_output_path(job, output_root, view)),
                        **source_record,
                    }
                )
                continue
            source_path = _repo_relative_path(repo_root, raw_source_path)
            source_record = {"view_source": str(source_path)}
            if source_path.exists():
                render_job = {**job, "document_mode": "new"}
                render_design = _design_for_job(
                    app,
                    render_job,
                    role=f"render-view:{view}",
                    log_file=log_file,
                )
                render_document = app.activeDocument
                import_record = _import_file_to_design(
                    app,
                    render_design,
                    source_path,
                    f"render-view:{view}",
                    log_file,
                )
                source_record["view_source_import"] = import_record
                try:
                    app.activeViewport.fit()
                    adsk.doEvents()
                except Exception:
                    _write_log(log_file, f"Viewport fit failed for render view {view}")
            else:
                source_record["view_source_import"] = {
                    "status": "missing",
                    "path": str(source_path),
                }
                _write_log(log_file, f"Missing render view source for {view}: {source_path}")
                records.append(
                    {
                        "view": view,
                        "path": str(_render_output_path(job, output_root, view)),
                        "status": "missing",
                        **source_record,
                    }
                )
                continue

        if backend == "viewport_capture":
            filename = _render_output_path(job, output_root, view)
            filename.parent.mkdir(parents=True, exist_ok=True)
            fallback = _save_viewport_render_fallback(app.activeViewport, filename, log_file)
            record = {
                "view": view,
                "path": str(filename),
                "status": (
                    "completed"
                    if fallback and fallback.get("fallback_status") == "completed"
                    else "failed"
                ),
                "completion_mode": "viewport_capture",
            }
            if fallback:
                record.update(fallback)
            if source_record:
                record.update(source_record)
            records.append(record)
            if render_document:
                close_record = _close_owned_document(app, render_document, job, log_file)
                records[-1]["render_document_close"] = close_record
            continue

        render = render_design.renderManager.rendering
        _set_render_resolution(job, render)
        camera = app.activeViewport.camera
        filename = _render_output_path(job, output_root, view)
        filename.parent.mkdir(parents=True, exist_ok=True)
        future = render.startLocalRender(str(filename), camera)
        _write_log(
            log_file,
            f"Started local render {filename}; state={future.renderState}; progress={future.progress}",
        )
        if wait_for_renders:
            record = _wait_for_render(
                future,
                filename,
                timeout_seconds,
                log_file,
                app.activeViewport,
            )
            record["view"] = view
            if source_record:
                record.update(source_record)
            records.append(record)
        else:
            record = {
                "view": view,
                "path": str(filename),
                "status": "started",
                "state": future.renderState,
                "progress": float(future.progress),
            }
            if source_record:
                record.update(source_record)
            records.append(record)
        if render_document:
            close_record = _close_owned_document(app, render_document, job, log_file)
            if records and records[-1].get("view") == view:
                records[-1]["render_document_close"] = close_record
    return records


def _export_review_files(
    design: adsk.fusion.Design,
    job: dict,
    output_root: Path,
    log_file: Path,
) -> list[dict]:
    export_cfg = job.get("exports", {})
    if not export_cfg.get("step") and not export_cfg.get("stl"):
        _write_log(log_file, "Review exports disabled by job.")
        return [{"status": "disabled"}]

    exports = output_root / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    export_manager = design.exportManager
    root_component = design.rootComponent
    output_names = export_cfg.get("outputs", {})
    records = []

    if export_cfg.get("step"):
        raw_step_path = output_names.get("step") if isinstance(output_names, dict) else None
        step_path = _resolve_output_path(output_root, raw_step_path) if raw_step_path else (
            exports / f"{job.get('run_id', 'cbbs-fusion')}-review.step"
        )
        step_path.parent.mkdir(parents=True, exist_ok=True)
        step_options = export_manager.createSTEPExportOptions(str(step_path), root_component)
        result = export_manager.execute(step_options)
        _write_log(log_file, f"Exported STEP review file {step_path}; result={result}")
        records.append({"kind": "step", "path": str(step_path), "status": "exported", "result": bool(result)})

    if export_cfg.get("stl"):
        raw_stl_path = output_names.get("stl") if isinstance(output_names, dict) else None
        stl_path = _resolve_output_path(output_root, raw_stl_path) if raw_stl_path else (
            exports / f"{job.get('run_id', 'cbbs-fusion')}-review.stl"
        )
        stl_path.parent.mkdir(parents=True, exist_ok=True)
        stl_options = export_manager.createSTLExportOptions(root_component, str(stl_path))
        result = export_manager.execute(stl_options)
        _write_log(log_file, f"Exported STL review file {stl_path}; result={result}")
        records.append({"kind": "stl", "path": str(stl_path), "status": "exported", "result": bool(result)})
    return records


def _summary_path(output_root: Path, job: dict) -> Path:
    raw_path = job.get("summary_path", "run-summary.json")
    return _resolve_output_path(output_root, raw_path)


def _write_summary(output_root: Path, job: dict, summary: dict) -> None:
    summary_path = _summary_path(output_root, job)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    run_id = job.get("run_id")
    if run_id:
        archive_path = output_root / f"run-summary-{run_id}.json"
        archive_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _execute_job_path(app: adsk.core.Application, job_path: Path) -> dict:
    job = {}
    output_root = None
    log_file = None

    try:
        job = _load_job(job_path)
        repo_root = _repo_root()
        job_repo_root = _job_repo_root(repo_root, job)
        output_root = _output_root(job_repo_root, job)
        run_id = job.get("run_id", datetime.now().strftime("fusion-%Y%m%d-%H%M%S"))
        log_file = _log_path(output_root, run_id)
        started_at = _utc_now()
        _write_log(log_file, f"CBBS Fusion job: {job_path}")
        _write_log(log_file, f"Run id: {run_id}")
        _write_log(log_file, f"Document mode: {job.get('document_mode', 'new')}")

        design = _design_for_job(app, job, role="job", log_file=log_file)
        import_records = []
        import_items = _iter_import_artifacts(job)
        for artifact in import_items:
            import_records.append(_import_artifact(app, design, job_repo_root, artifact, job, log_file))

        render_records = _start_local_renders(app, design, job_repo_root, job, output_root, log_file)
        export_records = _export_review_files(design, job, output_root, log_file)
        failed_records = [
            item
            for item in import_records + render_records + export_records
            if item.get("status") in {"missing", "unsupported", "timeout", "failed"}
        ]
        document_records = _close_owned_documents(app, job, log_file, run_id_only=True)
        summary = {
            "schema": "cbbs-cad/fusion-run-summary/v1",
            "run_id": run_id,
            "status": "completed" if not failed_records else "completed_with_warnings",
            "started_at": started_at,
            "completed_at": _utc_now(),
            "job_path": str(job_path),
            "log_path": str(log_file),
            "document_mode": job.get("document_mode", "new"),
            "artifact_count": len(job.get("artifacts", [])),
            "import_item_count": len(import_items),
            "document_lifecycle": _lifecycle_policy(job),
            "documents": document_records,
            "assembly": job.get("assembly", {}),
            "imports": import_records,
            "renders": render_records,
            "exports": export_records,
        }
        _write_summary(output_root, job, summary)
        _write_log(log_file, f"Wrote run summary {_summary_path(output_root, job)}")

        app.log(f"CBBS Fusion Automation wrote log {log_file}")
        return summary
    except Exception:
        details = traceback.format_exc()
        app.log(details)
        if log_file:
            _write_log(log_file, details)
        if output_root and job:
            document_records = _close_owned_documents(app, job, log_file, run_id_only=True)
            summary = {
                "schema": "cbbs-cad/fusion-run-summary/v1",
                "run_id": job.get("run_id", ""),
                "status": "failed",
                "completed_at": _utc_now(),
                "log_path": str(log_file) if log_file else "",
                "document_lifecycle": _lifecycle_policy(job),
                "documents": document_records,
                "error": details,
            }
            _write_summary(output_root, job, summary)
        raise


def _agent_root_for_job_path(job_path: Path) -> Path:
    try:
        job = _load_job(job_path)
        repo_root = _job_repo_root(_repo_root(), job)
        output_root = _output_root(repo_root, job)
    except Exception:
        output_root = job_path.parent if job_path else _repo_root() / "3d-print-work" / "generated" / "fusion"
        output_root.mkdir(parents=True, exist_ok=True)
    return output_root / "agent"


def _agent_paths(job_path: Path) -> dict[str, Path]:
    root = _agent_root_for_job_path(job_path)
    paths = {
        "root": root,
        "requests": root / "requests",
        "responses": root / "responses",
        "logs": root / "logs",
        "snapshots": root / "snapshots",
        "heartbeat": root / "heartbeat.json",
    }
    for key, path in paths.items():
        if key != "heartbeat":
            path.mkdir(parents=True, exist_ok=True)
    return paths


def _write_agent_log(job_path: Path, message: str) -> None:
    paths = _agent_paths(job_path)
    stamp = datetime.now().strftime("%Y%m%d")
    log_file = paths["logs"] / f"agent-{stamp}.log"
    _write_log(log_file, f"{_utc_now()} {message}")


def _request_response_path(job_path: Path, request: dict) -> Path:
    paths = _agent_paths(job_path)
    request_id = request.get("request_id") or "missing-request-id"
    return paths["responses"] / f"{request_id}.json"


def _write_agent_response(job_path: Path, request: dict, response: dict) -> None:
    payload = {
        "schema": AGENT_RESPONSE_SCHEMA,
        "request_id": request.get("request_id", ""),
        "action": request.get("action", ""),
        "started_at": response.pop("started_at", _utc_now()),
        "completed_at": _utc_now(),
        **response,
    }
    _write_json(_request_response_path(job_path, request), payload)


def _active_document_state(app: adsk.core.Application) -> dict:
    document = app.activeDocument
    viewport = app.activeViewport
    state = {
        "active_document": document.name if document else None,
        "active_product_type": app.activeProduct.productType if app.activeProduct else None,
        "documents": _document_inventory(app),
    }
    try:
        camera = viewport.camera if viewport else None
        if camera:
            state["camera"] = {
                "is_smooth_transition": camera.isSmoothTransition,
                "is_perspective": camera.isPerspective,
            }
    except Exception:
        state["camera"] = {"error": "unavailable"}
    return state


def _cleanup_owned_documents(app: adsk.core.Application, job_path: Path, request: dict) -> dict:
    job = _load_job(job_path)
    paths = _agent_paths(job_path)
    log_file = paths["logs"] / f"cleanup-owned-{request.get('request_id', 'manual')}.log"
    before = _document_inventory(app)
    records = _close_owned_documents(app, job, log_file, run_id_only=False)
    after = _document_inventory(app)
    return {
        "status": "completed",
        "before": before,
        "documents": records,
        "after": after,
        "closed_count": sum(1 for record in records if record.get("status") == "closed"),
    }


def _agent_job_path(request: dict, fallback_job_path: Path) -> Path:
    raw = request.get("job_path")
    if _looks_like_url_path(raw):
        raise ValueError(f"unsupported_url_path: {raw}")
    return _localize_agent_path(raw) if raw else fallback_job_path


def _capture_viewport(app: adsk.core.Application, job_path: Path, request: dict) -> dict:
    paths = _agent_paths(job_path)
    request_id = request.get("request_id") or datetime.now().strftime("%Y%m%d-%H%M%S")
    raw_output = request.get("output_path") or request.get("path")
    if _looks_like_url_path(raw_output):
        return _unsupported_url_path(raw_output)
    output = _localize_agent_path(raw_output) if raw_output else paths["snapshots"] / f"{request_id}.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    width = int(request.get("width", 1280))
    height = int(request.get("height", 800))
    viewport = app.activeViewport
    try:
        result = viewport.saveAsImageFile(str(output), width, height)
    except TypeError:
        result = viewport.saveAsImageFile(str(output))
    return {"path": str(output), "result": bool(result), "status": "completed"}


def _export_active_archive(app: adsk.core.Application, job_path: Path, request: dict) -> dict:
    raw_path = request.get("path") or request.get("output_path")
    if raw_path and _looks_like_url_path(raw_path):
        return _unsupported_url_path(raw_path)
    job = _load_job(job_path)
    repo_root = _job_repo_root(_repo_root(), job)
    output_root = _output_root(repo_root, job)
    run_id = str(job.get("run_id", "fusion-review"))
    if raw_path:
        output = _resolve_local_file_path(repo_root, raw_path)
    else:
        output = output_root / "assembly-documentation" / run_id / f"{run_id}-active-review.f3d"
    output.parent.mkdir(parents=True, exist_ok=True)

    design = adsk.fusion.Design.cast(app.activeProduct)
    if not design and getattr(app, "activeDocument", None):
        design = _design_from_document(app.activeDocument)
    if not design:
        raise ValueError("active product is not a Fusion design")
    options = design.exportManager.createFusionArchiveExportOptions(str(output))
    result = design.exportManager.execute(options)
    return {
        "status": "completed",
        "kind": "fusion-archive",
        "path": str(output),
        "result": bool(result),
    }


def _command_inventory(app: adsk.core.Application, request: dict) -> dict:
    query = str(request.get("query") or "").strip().lower()
    max_items = int(request.get("max_items") or 250)
    ui = app.userInterface

    workspaces = []
    try:
        for workspace in ui.workspaces:
            item = {
                "id": workspace.id,
                "name": workspace.name,
                "is_active": bool(getattr(workspace, "isActive", False)),
            }
            haystack = f"{item['id']} {item['name']}".lower()
            if not query or query in haystack:
                workspaces.append(item)
            if len(workspaces) >= max_items:
                break
    except Exception as exc:
        workspaces.append({"error": str(exc)})

    commands = []
    try:
        definitions = ui.commandDefinitions
        for index in range(definitions.count):
            try:
                command = definitions.item(index)
                if not command:
                    continue
                item = {
                    "id": command.id,
                    "name": command.name,
                    "tooltip": getattr(command, "tooltip", ""),
                }
                haystack = f"{item['id']} {item['name']} {item['tooltip']}".lower()
                if not query or query in haystack:
                    commands.append(item)
                if len(commands) >= max_items:
                    break
            except Exception as exc:
                if not query:
                    commands.append({"index": index, "error": str(exc)})
    except Exception as exc:
        commands.append({"error": str(exc)})

    return {
        "status": "completed",
        "query": query,
        "workspaces": workspaces,
        "commands": commands,
    }


def _activate_workspace(app: adsk.core.Application, request: dict) -> dict:
    workspace_id = request.get("workspace_id") or request.get("command_id")
    if not workspace_id:
        raise ValueError("activate_workspace requires workspace_id")
    workspace = app.userInterface.workspaces.itemById(str(workspace_id))
    if not workspace:
        raise ValueError(f"Fusion workspace not found: {workspace_id}")
    result = workspace.activate()
    return {
        "status": "completed",
        "workspace_id": str(workspace_id),
        "workspace_name": workspace.name,
        "result": bool(result),
    }


def _find_artifact(job: dict, artifact_id: str) -> dict | None:
    for artifact in job.get("artifacts", []):
        if artifact.get("concept_id") == artifact_id:
            return artifact
    return None


def _open_artifact(app: adsk.core.Application, job_path: Path, request: dict) -> dict:
    job = _load_job(job_path)
    repo_root = _job_repo_root(_repo_root(), job)
    artifact_id = request.get("artifact_id")
    raw_path = request.get("path")
    if artifact_id:
        artifact = _find_artifact(job, artifact_id)
        if not artifact:
            raise ValueError(f"artifact not found: {artifact_id}")
    elif raw_path:
        if _looks_like_url_path(raw_path):
            return _unsupported_url_path(raw_path)
        path = _resolve_local_file_path(repo_root, raw_path)
        if not path.exists():
            return {
                "status": "missing",
                "path": str(path),
                "error": "Artifact path does not exist.",
            }
        artifact = {
            "concept_id": path.stem,
            "files": {path.suffix.lower().lstrip("."): str(path)},
        }
    else:
        raise ValueError("open_artifact requires artifact_id or path")

    design = _design_for_job(
        app,
        {**job, "document_mode": request.get("document_mode", "new")},
        role="open-artifact",
    )
    paths = _agent_paths(job_path)
    log_file = paths["logs"] / f"open-artifact-{request.get('request_id', 'manual')}.log"
    record = _import_artifact(app, design, repo_root, artifact, job, log_file)
    return {"status": "completed", "import": record}


def _assembly_part_artifacts(artifact: dict) -> list[dict]:
    assembly = artifact.get("assembly", {})
    parts = assembly.get("parts", []) if isinstance(assembly, dict) else []
    records = []
    for part in parts:
        if not isinstance(part, dict):
            continue
        records.append(
            {
                "concept_id": f"{artifact.get('concept_id', '')}:{part.get('id', '')}",
                "name": part.get("name", ""),
                "truth_state": artifact.get("truth_state", ""),
                "measurement_status": artifact.get("measurement_status", ""),
                "files": part.get("files", {}),
                "assembly_parent_id": artifact.get("concept_id", ""),
                "assembly_part_id": part.get("id", ""),
                "role": part.get("role", ""),
                "occurrence": part.get("occurrence", {}),
                "support_risk": part.get("support_risk", {}),
            }
        )
    return records


def _open_assembly_artifact(app: adsk.core.Application, job_path: Path, request: dict) -> dict:
    job = _load_job(job_path)
    repo_root = _job_repo_root(_repo_root(), job)
    artifact_id = request.get("artifact_id")
    if not artifact_id:
        raise ValueError("open_assembly_artifact requires artifact_id")
    artifact = _find_artifact(job, artifact_id)
    if not artifact:
        raise ValueError(f"artifact not found: {artifact_id}")
    part_artifacts = _assembly_part_artifacts(artifact)
    if not part_artifacts:
        raise ValueError(f"artifact has no assembly parts: {artifact_id}")

    authoring_job = {
        **job,
        "document_mode": "new",
        "document_lifecycle": {
            **_lifecycle_policy(job),
            "close_generated_documents": False,
            "keep_open_for_review": True,
            "save_policy": "local_archive_required",
            "review_status": "native Fusion assembly documentation authoring",
        },
    }
    design = _design_for_job(app, authoring_job, role=f"assembly-doc:{artifact_id}")
    paths = _agent_paths(job_path)
    log_file = paths["logs"] / f"open-assembly-artifact-{request.get('request_id', 'manual')}.log"
    records = [
        _import_artifact(app, design, repo_root, part_artifact, authoring_job, log_file)
        for part_artifact in part_artifacts
    ]
    return {
        "status": "completed",
        "artifact_id": artifact_id,
        "imports": records,
        "document": _active_document_state(app).get("active_document"),
    }


def _execute_command_id(app: adsk.core.Application, request: dict) -> dict:
    command_id = request.get("command_id")
    if not command_id:
        raise ValueError("execute_command_id requires command_id")
    command = app.userInterface.commandDefinitions.itemById(command_id)
    if not command:
        raise ValueError(f"Fusion commandDefinition not found: {command_id}")
    result = command.execute()
    return {"status": "completed", "command_id": command_id, "result": bool(result)}


def _execute_text_command(app: adsk.core.Application, request: dict) -> dict:
    if not request.get("allow_text_command"):
        raise ValueError("execute_text_command requires allow_text_command=true")
    text_command = request.get("text_command")
    if not text_command:
        raise ValueError("execute_text_command requires text_command")
    result = app.executeTextCommand(text_command)
    return {"status": "completed", "result": result}


def _execute_agent_request(app: adsk.core.Application, fallback_job_path: Path, request_path: Path) -> None:
    started_at = _utc_now()
    request = {}
    job_path = fallback_job_path
    try:
        request = _load_job(request_path)
        if request.get("schema") != AGENT_COMMAND_SCHEMA:
            raise ValueError(f"unsupported agent command schema: {request.get('schema')}")
        job_path = _agent_job_path(request, fallback_job_path)
        action = request.get("action")
        _write_agent_log(job_path, f"processing request {request.get('request_id')} action={action}")

        if action == "run_job":
            summary = _execute_job_path(app, job_path)
            result = {"status": "completed", "summary": summary}
        elif action == "cleanup_owned_documents":
            result = _cleanup_owned_documents(app, job_path, request)
        elif action == "open_artifact":
            result = _open_artifact(app, job_path, request)
        elif action == "open_assembly_artifact":
            result = _open_assembly_artifact(app, job_path, request)
        elif action == "capture_viewport":
            result = _capture_viewport(app, job_path, request)
        elif action == "ui_state":
            result = {"status": "ok", **_active_document_state(app)}
        elif action == "export_active_archive":
            result = _export_active_archive(app, job_path, request)
        elif action == "command_inventory":
            result = _command_inventory(app, request)
        elif action == "activate_workspace":
            result = _activate_workspace(app, request)
        elif action == "execute_command_id":
            result = _execute_command_id(app, request)
        elif action == "execute_text_command":
            result = _execute_text_command(app, request)
        else:
            raise ValueError(f"unsupported Fusion agent action: {action}")

        _write_agent_response(job_path, request, {"started_at": started_at, **result})
        _write_agent_log(job_path, f"completed request {request.get('request_id')}")
    except Exception:
        details = traceback.format_exc()
        app.log(details)
        if request:
            _write_agent_response(
                job_path,
                request,
                {
                    "started_at": started_at,
                    "status": "failed",
                    "error": details,
                },
            )
        _write_agent_log(job_path, f"failed request {request_path}: {details}")


class _AgentCommandHandler(adsk.core.CustomEventHandler):
    def __init__(self, app: adsk.core.Application, job_path: Path):
        super().__init__()
        self.app = app
        self.job_path = job_path

    def notify(self, args: adsk.core.CustomEventArgs):
        info = str(args.additionalInfo or "").strip()
        paths = _agent_paths(self.job_path)
        if info and not info.endswith(".json") and not any(sep in info for sep in ("/", "\\")):
            request_path = paths["requests"] / f"{info}.json"
        else:
            request_path = _localize_agent_path(info)
        _execute_agent_request(self.app, self.job_path, request_path)


class _FusionAgentBridge:
    def __init__(self, app: adsk.core.Application, job_path: Path):
        self.app = app
        self.job_path = job_path
        self._stop = threading.Event()
        self._seen: set[str] = set()
        self._thread = threading.Thread(target=self._poll_loop, name="CBBSFusionAgentBridge", daemon=True)
        self._handler = _AgentCommandHandler(app, job_path)

    def start(self) -> None:
        event = self.app.registerCustomEvent(AGENT_EVENT_ID)
        event.add(self._handler)
        _handlers.append(self._handler)
        self._thread.start()
        _write_agent_log(self.job_path, "agent bridge started")

    def stop(self) -> None:
        self._stop.set()
        try:
            self.app.unregisterCustomEvent(AGENT_EVENT_ID)
        except Exception:
            pass
        _write_agent_log(self.job_path, "agent bridge stopped")

    def _write_heartbeat(self) -> None:
        paths = _agent_paths(self.job_path)
        heartbeat = {
            "schema": AGENT_HEARTBEAT_SCHEMA,
            "updated_at": _utc_now(),
            "process_id": os.getpid(),
            "event_id": AGENT_EVENT_ID,
            "job_path": str(self.job_path),
            "request_dir": str(paths["requests"]),
            "response_dir": str(paths["responses"]),
            "documents": _document_inventory(self.app),
        }
        _write_json(paths["heartbeat"], heartbeat)

    def _poll_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._write_heartbeat()
                paths = _agent_paths(self.job_path)
                for request_path in sorted(paths["requests"].glob("*.json")):
                    key = str(request_path)
                    if key in self._seen:
                        continue
                    request = _load_job(request_path)
                    request_id = request.get("request_id") or request_path.stem
                    response_path = paths["responses"] / f"{request_id}.json"
                    if response_path.exists():
                        self._seen.add(key)
                        continue
                    self._seen.add(key)
                    self.app.fireCustomEvent(AGENT_EVENT_ID, str(request_id))
            except Exception:
                try:
                    _write_agent_log(self.job_path, traceback.format_exc())
                except Exception:
                    pass
            time.sleep(1)


def _start_agent_bridge(app: adsk.core.Application, job_path: Path) -> None:
    global _agent_bridge
    if _agent_bridge:
        _agent_bridge.stop()
    _agent_bridge = _FusionAgentBridge(app, job_path)
    _agent_bridge.start()


def run(context):
    app = adsk.core.Application.get()
    ui = app.userInterface
    job = {}
    job_path = _resolve_job_path(_repo_root())
    _start_agent_bridge(app, job_path)

    try:
        job = _load_job(job_path)
        summary = _execute_job_path(app, job_path)
        if job.get("ui_message_box", True):
            ui.messageBox(f"CBBS Fusion Automation completed. Log:\n{summary.get('log_path')}")
    except Exception:
        details = traceback.format_exc()
        if job.get("ui_message_box", True):
            ui.messageBox(f"CBBS Fusion Automation failed:\n{details}")


def stop(context):
    app = adsk.core.Application.get()
    global _agent_bridge
    if _agent_bridge:
        _agent_bridge.stop()
        _agent_bridge = None
    app.log("CBBS Fusion Automation stopped.")
