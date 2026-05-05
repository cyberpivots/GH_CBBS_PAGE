from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cbbs_cad.fusion_job import DEFAULT_FUSION_JOB
from cbbs_cad.specs import REPO_ROOT

ADDIN_NAME = "CBBSFusionAutomation"
ADDIN_MANIFEST = f"{ADDIN_NAME}.manifest"
JOB_POINTER = "job_path.txt"
REPO_ADDIN_DIR = REPO_ROOT / "3d-print-work" / "fusion" / ADDIN_NAME
WINDOWS_PATH_RE = re.compile(r"^([A-Za-z]):[\\/](.*)$")
URL_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


class UnsupportedUrlPathError(ValueError):
    def __init__(self, raw_path: str):
        super().__init__(f"unsupported_url_path: {raw_path}")
        self.raw_path = raw_path


def is_url_like_path(value: str | Path) -> bool:
    raw = str(value).strip()
    if not raw:
        return False
    if WINDOWS_PATH_RE.match(raw):
        return False
    normalized = raw.replace("\\", "/")
    return bool(URL_SCHEME_RE.match(normalized))


def localize_path(value: str | Path) -> Path:
    raw = str(value).strip()
    match = WINDOWS_PATH_RE.match(raw)
    if match and os.name != "nt":
        rest = match.group(2).replace("\\", "/")
        return Path(f"/mnt/{match.group(1).lower()}/{rest}")
    return Path(raw)


def resolve_local_artifact_path(
    value: str | Path,
    repo_root: Path = REPO_ROOT,
    *,
    must_exist: bool = True,
) -> Path:
    raw = str(value).strip()
    if is_url_like_path(raw):
        raise UnsupportedUrlPathError(raw)
    path = localize_path(raw)
    resolved = path if path.is_absolute() else repo_root / path
    if must_exist and not resolved.exists():
        raise FileNotFoundError(f"artifact path does not exist: {resolved}")
    return resolved


def windows_path(path: Path) -> str | None:
    resolved = path.resolve()
    if os.name == "nt":
        return str(resolved)
    parts = resolved.parts
    if len(parts) >= 3 and parts[0] == "/" and parts[1] == "mnt" and len(parts[2]) == 1:
        drive = parts[2].upper()
        rest = "\\".join(parts[3:])
        return f"{drive}:\\{rest}"
    return None


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _appdata_from_cmd() -> Path | None:
    if shutil.which("cmd.exe") is None:
        return None
    try:
        result = subprocess.run(
            ["cmd.exe", "/c", "echo", "%APPDATA%"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    raw = result.stdout.strip()
    if not raw or raw == "%APPDATA%":
        return None
    return localize_path(raw)


def _appdata_dir() -> Path | None:
    raw = os.environ.get("APPDATA")
    if raw:
        return localize_path(raw)
    cmd_appdata = _appdata_from_cmd()
    if cmd_appdata:
        return cmd_appdata
    userprofile = os.environ.get("USERPROFILE")
    if userprofile:
        return localize_path(userprofile) / "AppData" / "Roaming"
    return None


def candidate_addins_roots() -> list[Path]:
    roots: list[Path] = []
    appdata = _appdata_dir()
    if appdata:
        roots.extend(
            [
                appdata / "Autodesk" / "Autodesk Fusion 360" / "API" / "AddIns",
                appdata / "Autodesk" / "Autodesk Fusion" / "API" / "AddIns",
            ]
        )
    roots.append(
        Path.home()
        / "Library"
        / "Application Support"
        / "Autodesk"
        / "Autodesk Fusion"
        / "API"
        / "AddIns"
    )
    deduped: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        key = str(root)
        if key not in seen:
            deduped.append(root)
            seen.add(key)
    return deduped


def default_installed_addin_dir() -> Path:
    candidates = [root / ADDIN_NAME for root in candidate_addins_roots()]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    for candidate in candidates:
        if candidate.parent.exists():
            return candidate
    return candidates[0]


def job_pointer_value(job_path: Path) -> str:
    return windows_path(job_path) or str(job_path.resolve())


def install_fusion_addin(
    job_path: Path = DEFAULT_FUSION_JOB,
    addin_dir: Path | None = None,
    repo_addin_dir: Path = REPO_ADDIN_DIR,
) -> dict[str, Path | str]:
    if not repo_addin_dir.exists():
        raise FileNotFoundError(f"repo add-in source not found: {repo_addin_dir}")

    target = addin_dir or default_installed_addin_dir()
    target.mkdir(parents=True, exist_ok=True)

    for source in repo_addin_dir.iterdir():
        if source.name in {JOB_POINTER, "__pycache__"}:
            continue
        destination = target / source.name
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)

    manifest_path = target / ADDIN_MANIFEST
    manifest = _load_json(manifest_path)
    manifest["runOnStartup"] = True
    _write_json(manifest_path, manifest)

    pointer_value = job_pointer_value(job_path)
    (target / JOB_POINTER).write_text(pointer_value + "\n", encoding="utf-8")
    return {
        "installed_dir": target,
        "manifest": manifest_path,
        "job_pointer": target / JOB_POINTER,
        "job_path": pointer_value,
    }


def _result(name: str, ok: bool, detail: str) -> CheckResult:
    return CheckResult(name=name, ok=ok, detail=detail)


def _job_repo_root(job: dict[str, Any]) -> Path:
    return localize_path(job.get("repo_root") or job.get("repo_root_windows") or REPO_ROOT)


def _resolve_job_relative(raw: str | Path, repo_root: Path) -> Path:
    path = localize_path(raw)
    return path if path.is_absolute() else repo_root / path


def _output_root(job: dict[str, Any], repo_root: Path) -> Path:
    return _resolve_job_relative(job.get("output_root", "3d-print-work/generated/fusion"), repo_root)


def _latest_log(logs_dir: Path) -> Path | None:
    if not logs_dir.exists():
        return None
    logs = sorted(logs_dir.glob("fusion-job-*.log"), key=lambda path: path.stat().st_mtime)
    return logs[-1] if logs else None


def _summary_path(job: dict[str, Any], output_root: Path) -> Path:
    raw = job.get("summary_path", "run-summary.json")
    path = localize_path(raw)
    return path if path.is_absolute() else output_root / path


def _agent_heartbeat_path(output_root: Path) -> Path:
    return output_root / "agent" / "heartbeat.json"


def _paths_equivalent(left: str | Path, right: str | Path) -> bool:
    left_path = localize_path(left)
    right_path = localize_path(right)
    try:
        return left_path.resolve() == right_path.resolve()
    except OSError:
        return left_path.absolute() == right_path.absolute()


def _artifact_paths(job: dict[str, Any], repo_root: Path) -> list[Path]:
    paths: list[Path] = []
    for artifact in job.get("artifacts", []):
        files = artifact.get("files", {})
        if isinstance(files, dict):
            for raw in files.values():
                if raw:
                    paths.append(_resolve_job_relative(raw, repo_root))
        assembly = artifact.get("assembly", {})
        if isinstance(assembly, dict):
            for part in assembly.get("parts", []):
                if not isinstance(part, dict):
                    continue
                part_files = part.get("files", {})
                if isinstance(part_files, dict):
                    for raw in part_files.values():
                        if raw:
                            paths.append(_resolve_job_relative(raw, repo_root))
            views = assembly.get("views", {})
            if isinstance(views, dict):
                for view in views.values():
                    if isinstance(view, dict) and view.get("file"):
                        paths.append(_resolve_job_relative(view["file"], repo_root))
    return paths


def _render_outputs(job: dict[str, Any], output_root: Path) -> list[Path]:
    render_cfg = job.get("render", {})
    if not render_cfg.get("enabled", True):
        return []
    outputs = render_cfg.get("outputs", {})
    paths: list[Path] = []
    if isinstance(outputs, dict) and outputs:
        for raw in outputs.values():
            paths.append(_resolve_job_relative(raw, output_root))
    else:
        for view in render_cfg.get("views", ["front", "isometric"]):
            paths.append(output_root / "renders" / f"cbbs-cad-{view}.png")
    return paths


def _export_outputs(job: dict[str, Any], output_root: Path) -> list[Path]:
    export_cfg = job.get("exports", {})
    outputs = export_cfg.get("outputs", {})
    paths: list[Path] = []
    for kind in ("step", "stl"):
        if not export_cfg.get(kind):
            continue
        if isinstance(outputs, dict) and outputs.get(kind):
            paths.append(_resolve_job_relative(outputs[kind], output_root))
        else:
            paths.append(output_root / "exports" / f"cbbs-fusion-review.{kind}")
    return paths


def _count_log_imports(log_path: Path) -> int:
    text = log_path.read_text(encoding="utf-8", errors="replace")
    return sum(
        1
        for line in text.splitlines()
        if line.startswith("Importing ") or line.startswith("Imported ")
    )


def _summary_records(summary: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = summary.get(key, [])
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _expected_import_item_count(job: dict[str, Any]) -> int:
    count = 0
    for artifact in job.get("artifacts", []):
        assembly = artifact.get("assembly", {})
        parts = assembly.get("parts", []) if isinstance(assembly, dict) else []
        count += len(parts) if parts else 1
    return count


def _document_lifecycle_policy(job: dict[str, Any]) -> dict[str, Any]:
    policy = {
        "owner": "cbbs-cad",
        "close_generated_documents": True,
        "keep_open_for_review": False,
        "save_policy": "discard_generated",
        "allow_user_prompt": False,
    }
    raw_policy = job.get("document_lifecycle", {})
    if isinstance(raw_policy, dict):
        policy.update(raw_policy)
    return policy


def _owned_modified_documents(
    *,
    job: dict[str, Any],
    job_path: Path,
    output_root: Path,
    summary: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    policy = _document_lifecycle_policy(job)
    if policy.get("keep_open_for_review"):
        return []

    leftovers: list[dict[str, Any]] = []
    if summary:
        for record in _summary_records(summary, "documents"):
            if not record.get("cbbs_owned") or not record.get("isModified"):
                continue
            if record.get("status") not in {"closed"}:
                leftovers.append(record)

    heartbeat_path = _agent_heartbeat_path(output_root)
    if heartbeat_path.exists() and heartbeat_path.stat().st_mtime + 0.001 >= job_path.stat().st_mtime:
        try:
            heartbeat = _load_json(heartbeat_path)
        except (json.JSONDecodeError, ValueError):
            heartbeat = {}
        documents = heartbeat.get("documents", [])
        if isinstance(documents, list):
            for record in documents:
                if (
                    isinstance(record, dict)
                    and record.get("cbbs_owned")
                    and record.get("isModified")
                ):
                    leftovers.append(record)
    return leftovers


def check_fusion_status(
    job_path: Path = DEFAULT_FUSION_JOB,
    addin_dir: Path | None = None,
) -> list[CheckResult]:
    results: list[CheckResult] = []
    job_path = job_path.resolve()
    if not job_path.exists():
        return [_result("Fusion job", False, f"missing: {job_path}")]

    try:
        job = _load_json(job_path)
        results.append(_result("Fusion job", True, str(job_path)))
    except (json.JSONDecodeError, ValueError) as exc:
        return [_result("Fusion job", False, f"invalid JSON: {exc}")]

    schema_ok = job.get("schema") == "cbbs-cad/fusion-job/v1"
    results.append(_result("Job schema", schema_ok, str(job.get("schema"))))
    run_id = str(job.get("run_id", ""))
    results.append(_result("Run id", bool(run_id), run_id or "missing"))
    results.append(
        _result(
            "Document mode",
            job.get("document_mode") == "new",
            str(job.get("document_mode")),
        )
    )
    lifecycle = _document_lifecycle_policy(job)
    lifecycle_ok = (
        lifecycle.get("owner") == "cbbs-cad"
        and lifecycle.get("save_policy") == "discard_generated"
        and lifecycle.get("allow_user_prompt") is False
        and (
            lifecycle.get("close_generated_documents") is True
            or lifecycle.get("keep_open_for_review") is True
        )
    )
    results.append(
        _result(
            "Document lifecycle",
            lifecycle_ok,
            (
                "review mode"
                if lifecycle.get("keep_open_for_review")
                else f"close={lifecycle.get('close_generated_documents')} "
                f"save_policy={lifecycle.get('save_policy')}"
            ),
        )
    )
    results.append(
        _result(
            "UI message boxes",
            job.get("ui_message_box") is False,
            "disabled" if job.get("ui_message_box") is False else str(job.get("ui_message_box")),
        )
    )
    results.append(
        _result(
            "Render wait",
            job.get("wait_for_renders") is True,
            str(job.get("wait_for_renders")),
        )
    )

    repo_root = _job_repo_root(job)
    output_root = _output_root(job, repo_root)
    artifacts = job.get("artifacts", [])
    artifact_count = len(artifacts) if isinstance(artifacts, list) else 0
    assembly_enabled = bool(job.get("assembly", {}).get("enabled"))
    results.append(_result("Artifact count", artifact_count > 0, str(artifact_count)))

    print_layouts = job.get("print_layouts", {})
    if isinstance(print_layouts, dict) and print_layouts:
        component_layouts = {
            "k1-component-rear-panel",
            "k1-component-rear-pod",
            "k1-component-front-door",
        }
        required_layouts = (
            component_layouts
            if component_layouts <= set(print_layouts)
            else {"k1-plate-tray", "k1-plate-door", "k1-combined"}
        )
        missing_layouts = required_layouts - set(print_layouts)
        k1_combined = print_layouts.get("k1-combined", {})
        combined_rejected = (
            isinstance(k1_combined, dict)
            and k1_combined.get("accepted") is False
        )
        status_label = (
            "component K1 plates, combined layouts rejected"
            if required_layouts == component_layouts
            else "split tray/door, combined K1 rejected"
        )
        results.append(
            _result(
                "K1 plate layouts",
                not missing_layouts and combined_rejected,
                (
                    status_label
                    if not missing_layouts and combined_rejected
                    else f"missing={sorted(missing_layouts)} combined={k1_combined}"
                ),
            )
        )

    missing_artifacts = [path for path in _artifact_paths(job, repo_root) if not path.exists()]
    results.append(
        _result(
            "Artifact files",
            not missing_artifacts,
            "all present" if not missing_artifacts else f"missing {len(missing_artifacts)} file(s)",
        )
    )

    installed_dir = addin_dir or default_installed_addin_dir()
    installed_manifest = installed_dir / ADDIN_MANIFEST
    if installed_manifest.exists():
        try:
            manifest = _load_json(installed_manifest)
            results.append(_result("Installed manifest", True, str(installed_manifest)))
            results.append(
                _result(
                    "Installed runOnStartup",
                    manifest.get("runOnStartup") is True,
                    str(manifest.get("runOnStartup")),
                )
            )
        except (json.JSONDecodeError, ValueError) as exc:
            results.append(_result("Installed manifest", False, f"invalid JSON: {exc}"))
    else:
        results.append(_result("Installed manifest", False, f"missing: {installed_manifest}"))

    installed_py = installed_dir / f"{ADDIN_NAME}.py"
    repo_py = REPO_ADDIN_DIR / f"{ADDIN_NAME}.py"
    if installed_py.exists() and repo_py.exists():
        installed_bytes = installed_py.read_bytes()
        repo_bytes = repo_py.read_bytes()
        source_matches = installed_bytes == repo_bytes
        results.append(
            _result(
                "Installed add-in source",
                source_matches,
                "matches repo" if source_matches else "differs from repo",
            )
        )
    else:
        results.append(_result("Installed add-in source", False, f"missing: {installed_py}"))

    pointer = installed_dir / JOB_POINTER
    if pointer.exists():
        raw_pointer = pointer.read_text(encoding="utf-8").strip()
        results.append(
            _result(
                "Installed job_path.txt",
                _paths_equivalent(raw_pointer, job_path),
                raw_pointer,
            )
        )
    else:
        results.append(_result("Installed job_path.txt", False, f"missing: {pointer}"))

    latest_log = _latest_log(output_root / "logs")
    summary: dict[str, Any] | None = None
    if latest_log:
        log_fresh = latest_log.stat().st_mtime + 0.001 >= job_path.stat().st_mtime
        results.append(
            _result(
                "Latest Fusion log",
                log_fresh,
                f"{latest_log} ({'fresh' if log_fresh else 'stale'})",
            )
        )
    else:
        results.append(_result("Latest Fusion log", False, f"missing under {output_root / 'logs'}"))

    run_summary = _summary_path(job, output_root)
    if run_summary.exists():
        try:
            summary = _load_json(run_summary)
            summary_run_id = str(summary.get("run_id", ""))
            results.append(
                _result(
                    "Run summary",
                    not run_id or summary_run_id == run_id,
                    f"{run_summary} run_id={summary_run_id}",
                )
            )
        except (json.JSONDecodeError, ValueError) as exc:
            results.append(_result("Run summary", False, f"invalid JSON: {exc}"))
    else:
        results.append(_result("Run summary", False, f"missing: {run_summary}"))

    if summary:
        import_count = sum(
            1
            for item in _summary_records(summary, "imports")
            if item.get("status") in {"imported", "ok"}
        )
        expected_import_count = _expected_import_item_count(job)
    elif latest_log:
        import_count = _count_log_imports(latest_log)
        expected_import_count = artifact_count
    else:
        import_count = 0
        expected_import_count = artifact_count
    results.append(
        _result(
            "Fusion imports",
            artifact_count > 0 and import_count >= expected_import_count,
            f"{import_count}/{expected_import_count}",
        )
    )

    view_sources = job.get("render", {}).get("view_sources", {})
    source_views = set(view_sources) if isinstance(view_sources, dict) else set()
    if summary and source_views:
        render_records = _summary_records(summary, "renders")
        sourced_views = {
            item.get("view")
            for item in render_records
            if isinstance(item.get("view_source_import"), dict)
            and item["view_source_import"].get("status") == "imported"
        }
        results.append(
            _result(
                "Render source imports",
                source_views <= sourced_views,
                (
                    "all sourced"
                    if source_views <= sourced_views
                    else f"missing {len(source_views - sourced_views)} source import(s)"
                ),
            )
        )
    elif source_views:
        results.append(_result("Render source imports", False, "missing run summary"))
    else:
        results.append(_result("Render source imports", True, "no source-isolated renders configured"))

    if assembly_enabled:
        if summary:
            summary_import_items = summary.get("import_item_count")
            results.append(
                _result(
                    "Assembly import items",
                    summary_import_items == expected_import_count,
                    f"{summary_import_items}/{expected_import_count}",
                )
            )
        else:
            results.append(_result("Assembly import items", False, "missing run summary"))

    leftovers = _owned_modified_documents(
        job=job,
        job_path=job_path,
        output_root=output_root,
        summary=summary,
    )
    results.append(
        _result(
            "Generated document cleanup",
            not leftovers,
            (
                "no leftover CBBS-owned modified documents"
                if not leftovers
                else f"{len(leftovers)} CBBS-owned modified document(s) still open"
            ),
        )
    )

    stale_outputs: list[Path] = []
    missing_exports: list[Path] = []
    for path in _export_outputs(job, output_root):
        if not path.exists():
            missing_exports.append(path)
        elif path.stat().st_mtime + 0.001 < job_path.stat().st_mtime:
            stale_outputs.append(path)
    results.append(
        _result(
            "Fusion exports",
            not missing_exports and not stale_outputs,
            "all present"
            if not missing_exports and not stale_outputs
            else f"missing={len(missing_exports)} stale={len(stale_outputs)}",
        )
    )

    missing_renders: list[Path] = []
    stale_renders: list[Path] = []
    for path in _render_outputs(job, output_root):
        if not path.exists():
            missing_renders.append(path)
        elif path.stat().st_mtime + 0.001 < job_path.stat().st_mtime:
            stale_renders.append(path)
    if summary:
        incomplete = [
            item
            for item in _summary_records(summary, "renders")
            if item.get("status") not in {"completed", "disabled"}
        ]
    else:
        incomplete = []
    results.append(
        _result(
            "Fusion renders",
            not missing_renders and not stale_renders and not incomplete,
            "all present"
            if not missing_renders and not stale_renders and not incomplete
            else (
                f"missing={len(missing_renders)} stale={len(stale_renders)} "
                f"incomplete={len(incomplete)}"
            ),
        )
    )

    return results


def wait_for_new_fusion_log(
    job_path: Path = DEFAULT_FUSION_JOB,
    timeout_seconds: int = 300,
    poll_seconds: float = 2.0,
) -> Path:
    job = _load_json(job_path)
    output_root = _output_root(job, _job_repo_root(job))
    logs_dir = output_root / "logs"
    start_time = time.time()
    deadline = start_time + timeout_seconds
    seen = {path.resolve() for path in logs_dir.glob("fusion-job-*.log")} if logs_dir.exists() else set()

    while time.time() < deadline:
        latest = _latest_log(logs_dir)
        if latest and latest.resolve() not in seen and latest.stat().st_mtime >= start_time:
            return latest
        time.sleep(poll_seconds)

    raise TimeoutError(f"no new Fusion log under {logs_dir} within {timeout_seconds}s")
