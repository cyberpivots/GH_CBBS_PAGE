from __future__ import annotations

import base64
import json
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cbbs_cad.fusion_job import DEFAULT_FUSION_JOB
from cbbs_cad.fusion_workflow import (
    ADDIN_MANIFEST,
    ADDIN_NAME,
    JOB_POINTER,
    REPO_ADDIN_DIR,
    CheckResult,
    default_installed_addin_dir,
    install_fusion_addin,
    job_pointer_value,
    localize_path,
)
from cbbs_cad.specs import REPO_ROOT

AGENT_COMMAND_SCHEMA = "cbbs-cad/fusion-agent-command/v1"
AGENT_RESPONSE_SCHEMA = "cbbs-cad/fusion-agent-response/v1"
AGENT_STATUS_SCHEMA = "cbbs-cad/fusion-agent-status/v1"
AGENT_ROOT_NAME = "agent"
HEARTBEAT_STALE_SECONDS = 20.0


@dataclass(frozen=True)
class AgentPaths:
    root: Path
    requests: Path
    responses: Path
    logs: Path
    snapshots: Path
    process_actions: Path
    heartbeat: Path


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return data


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def _repo_root_for_job(job: dict[str, Any]) -> Path:
    raw = job.get("repo_root") or job.get("repo_root_windows")
    return localize_path(raw) if raw else REPO_ROOT


def _resolve_job_relative(raw: str | Path, repo_root: Path) -> Path:
    path = localize_path(raw)
    return path if path.is_absolute() else repo_root / path


def output_root_for_job(job_path: Path = DEFAULT_FUSION_JOB) -> Path:
    if not job_path.exists():
        return REPO_ROOT / "3d-print-work" / "generated" / "fusion"
    job = _load_json(job_path)
    repo_root = _repo_root_for_job(job)
    return _resolve_job_relative(job.get("output_root", "3d-print-work/generated/fusion"), repo_root)


def agent_paths(job_path: Path = DEFAULT_FUSION_JOB, *, ensure: bool = False) -> AgentPaths:
    root = output_root_for_job(job_path) / AGENT_ROOT_NAME
    paths = AgentPaths(
        root=root,
        requests=root / "requests",
        responses=root / "responses",
        logs=root / "logs",
        snapshots=root / "snapshots",
        process_actions=root / "process-actions",
        heartbeat=root / "heartbeat.json",
    )
    if ensure:
        for path in (
            paths.requests,
            paths.responses,
            paths.logs,
            paths.snapshots,
            paths.process_actions,
        ):
            path.mkdir(parents=True, exist_ok=True)
    return paths


def _request_path(paths: AgentPaths, request_id: str) -> Path:
    return paths.requests / f"{request_id}.json"


def _response_path(paths: AgentPaths, request_id: str) -> Path:
    return paths.responses / f"{request_id}.json"


def enqueue_agent_command(
    action: str,
    *,
    job_path: Path = DEFAULT_FUSION_JOB,
    request_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> tuple[str, Path]:
    paths = agent_paths(job_path, ensure=True)
    request_id = request_id or f"agent-{uuid.uuid4().hex}"
    body = dict(payload or {})
    body.update(
        {
            "schema": AGENT_COMMAND_SCHEMA,
            "request_id": request_id,
            "action": action,
            "created_at": _utc_now(),
            "job_path": job_pointer_value(job_path),
        }
    )
    path = _request_path(paths, request_id)
    _write_json(path, body)
    return request_id, path


def wait_for_agent_response(
    request_id: str,
    *,
    job_path: Path = DEFAULT_FUSION_JOB,
    timeout_seconds: int = 300,
    poll_seconds: float = 1.0,
) -> dict[str, Any]:
    paths = agent_paths(job_path)
    response_path = _response_path(paths, request_id)
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if response_path.exists():
            return _load_json(response_path)
        time.sleep(poll_seconds)
    raise TimeoutError(f"no Fusion agent response for {request_id} within {timeout_seconds}s")


def _powershell() -> str:
    for candidate in ("powershell.exe", "pwsh.exe"):
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise RuntimeError("PowerShell is required for Windows Fusion desktop automation")


def run_powershell_json(script: str, *, timeout_seconds: int = 30) -> Any:
    result = subprocess.run(
        [_powershell(), "-NoProfile", "-NonInteractive", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    stdout = result.stdout.strip()
    if result.returncode != 0:
        raise RuntimeError((result.stderr or stdout or "PowerShell command failed").strip())
    if not stdout:
        return None
    return json.loads(stdout)


def _json_payload_script(payload: dict[str, Any]) -> str:
    encoded = base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")
    return (
        "$payloadJson = [Text.Encoding]::UTF8.GetString("
        f"[Convert]::FromBase64String('{encoded}'));"
        "$payload = $payloadJson | ConvertFrom-Json;"
    )


def fusion_processes() -> list[dict[str, Any]]:
    script = r"""
$items = @(Get-Process Fusion360 -ErrorAction SilentlyContinue | ForEach-Object {
  [ordered]@{
    process_name = $_.ProcessName
    id = $_.Id
    main_window_title = $_.MainWindowTitle
    path = $_.Path
    start_time = if ($_.StartTime) { $_.StartTime.ToString("o") } else { $null }
  }
})
$items | ConvertTo-Json -Compress -Depth 5
"""
    data = run_powershell_json(script, timeout_seconds=10)
    if data is None:
        return []
    if isinstance(data, dict):
        return [data]
    return [item for item in data if isinstance(item, dict)] if isinstance(data, list) else []


def _installed_addin_checks(job_path: Path, addin_dir: Path | None = None) -> list[CheckResult]:
    checks: list[CheckResult] = []
    installed_dir = addin_dir or default_installed_addin_dir()
    manifest_path = installed_dir / ADDIN_MANIFEST
    if manifest_path.exists():
        try:
            manifest = _load_json(manifest_path)
            checks.append(CheckResult("Installed manifest", True, str(manifest_path)))
            checks.append(
                CheckResult(
                    "Installed runOnStartup",
                    manifest.get("runOnStartup") is True,
                    str(manifest.get("runOnStartup")),
                )
            )
        except (json.JSONDecodeError, ValueError) as exc:
            checks.append(CheckResult("Installed manifest", False, f"invalid JSON: {exc}"))
    else:
        checks.append(CheckResult("Installed manifest", False, f"missing: {manifest_path}"))

    installed_py = installed_dir / f"{ADDIN_NAME}.py"
    repo_py = REPO_ADDIN_DIR / f"{ADDIN_NAME}.py"
    if installed_py.exists() and repo_py.exists():
        checks.append(
            CheckResult(
                "Installed add-in source",
                installed_py.read_bytes() == repo_py.read_bytes(),
                "matches repo" if installed_py.read_bytes() == repo_py.read_bytes() else "differs from repo",
            )
        )
    else:
        checks.append(CheckResult("Installed add-in source", False, f"missing: {installed_py}"))

    pointer_path = installed_dir / JOB_POINTER
    if pointer_path.exists():
        raw = pointer_path.read_text(encoding="utf-8").strip()
        expected = job_pointer_value(job_path)
        checks.append(CheckResult("Installed job_path.txt", raw == expected, raw))
    else:
        checks.append(CheckResult("Installed job_path.txt", False, f"missing: {pointer_path}"))
    return checks


def fusion_agent_status(
    *,
    job_path: Path = DEFAULT_FUSION_JOB,
    addin_dir: Path | None = None,
    stale_seconds: float = HEARTBEAT_STALE_SECONDS,
) -> dict[str, Any]:
    paths = agent_paths(job_path, ensure=True)
    processes = fusion_processes()
    heartbeat: dict[str, Any] | None = None
    heartbeat_age: float | None = None
    heartbeat_fresh = False
    if paths.heartbeat.exists():
        heartbeat = _load_json(paths.heartbeat)
        heartbeat_age = time.time() - paths.heartbeat.stat().st_mtime
        heartbeat_fresh = heartbeat_age <= stale_seconds

    checks = [
        CheckResult("Fusion process", bool(processes), f"{len(processes)} running"),
        CheckResult("Agent root", paths.root.exists(), str(paths.root)),
        CheckResult(
            "Agent heartbeat",
            heartbeat_fresh,
            (
                f"fresh age={heartbeat_age:.1f}s"
                if heartbeat_age is not None and heartbeat_fresh
                else (
                    f"stale age={heartbeat_age:.1f}s"
                    if heartbeat_age is not None
                    else f"missing: {paths.heartbeat}"
                )
            ),
        ),
    ]
    checks.extend(_installed_addin_checks(job_path, addin_dir))
    return {
        "schema": AGENT_STATUS_SCHEMA,
        "job_path": str(job_path.resolve()),
        "agent_root": str(paths.root),
        "heartbeat": heartbeat,
        "heartbeat_age_seconds": heartbeat_age,
        "heartbeat_fresh": heartbeat_fresh,
        "processes": processes,
        "checks": [check.__dict__ for check in checks],
    }


def fresh_bridge_document_inventory(
    *,
    job_path: Path = DEFAULT_FUSION_JOB,
    max_age_seconds: float = HEARTBEAT_STALE_SECONDS * 3,
) -> list[dict[str, Any]] | None:
    paths = agent_paths(job_path)
    if not paths.heartbeat.exists():
        return None
    age = time.time() - paths.heartbeat.stat().st_mtime
    if age > max_age_seconds:
        return None
    try:
        heartbeat = _load_json(paths.heartbeat)
    except (json.JSONDecodeError, ValueError):
        return None
    documents = heartbeat.get("documents")
    if not isinstance(documents, list):
        return None
    return [item for item in documents if isinstance(item, dict)]


def _log_process_action(job_path: Path, action: dict[str, Any]) -> Path:
    paths = agent_paths(job_path, ensure=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    action_id = action.get("action_id") or f"{stamp}-{uuid.uuid4().hex[:8]}"
    payload = {"schema": "cbbs-cad/fusion-process-action/v1", **action, "action_id": action_id}
    path = paths.process_actions / f"{action_id}.json"
    _write_json(path, payload)
    return path


def _fusion_executable_start_script() -> str:
    return r"""
function Resolve-FusionExecutable {
  $running = Get-Process Fusion360 -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -and (Test-Path $_.Path) } |
    Select-Object -First 1
  if ($running) { return $running.Path }

  $webDeploy = Join-Path $env:LOCALAPPDATA 'Autodesk\webdeploy\production'
  if (Test-Path $webDeploy) {
    $candidate = Get-ChildItem -Path $webDeploy -Filter Fusion360.exe -Recurse -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 1
    if ($candidate) { return $candidate.FullName }
  }
  return $null
}
$fusionExe = Resolve-FusionExecutable
if (-not $fusionExe) {
  @{ status = "failed"; reason = "missing-fusion-executable" } | ConvertTo-Json -Compress -Depth 5
  exit 2
}
Start-Process -FilePath $fusionExe
"""


def start_fusion(*, job_path: Path = DEFAULT_FUSION_JOB, reason: str = "agent-start") -> Path:
    action: dict[str, Any] = {
        "action": "start",
        "reason": reason,
        "requested_at": _utc_now(),
        "status": "started",
    }
    try:
        script = (
            _fusion_executable_start_script()
            + '@{ status = "started"; launcher = $fusionExe } | ConvertTo-Json -Compress -Depth 5'
        )
        action["result"] = run_powershell_json(script, timeout_seconds=15)
    except Exception as exc:
        action["status"] = "failed"
        action["error"] = str(exc)
        path = _log_process_action(job_path, action)
        raise RuntimeError(f"Fusion start failed; logged {path}: {exc}") from exc
    return _log_process_action(job_path, action)


def restart_fusion(
    *,
    job_path: Path = DEFAULT_FUSION_JOB,
    allow_unsaved_close: bool = False,
    allow_force: bool = False,
    timeout_seconds: int = 90,
    install_first: bool = True,
) -> Path:
    if install_first:
        install_fusion_addin(job_path=job_path)

    processes = fusion_processes()
    document_inventory = fresh_bridge_document_inventory(job_path=job_path)
    owned_modified_documents: list[dict[str, Any]] = []
    if document_inventory is not None:
        unsaved = [
            document
            for document in document_inventory
            if not document.get("cbbs_owned")
            and (document.get("isModified") or document.get("isSaved") is False)
        ]
        owned_modified_documents = [
            document
            for document in document_inventory
            if document.get("isModified") and document.get("cbbs_owned")
        ]
        inventory_source = "bridge-heartbeat"
        refusal_reason = "user-unsaved-documents"
    else:
        unsaved = [
            process
            for process in processes
            if "*" in str(process.get("main_window_title") or "")
            or str(process.get("main_window_title") or "").startswith("Untitled - ")
        ]
        inventory_source = "window-title"
        refusal_reason = "unsaved-window"
    if unsaved and not allow_unsaved_close:
        action = {
            "action": "restart",
            "requested_at": _utc_now(),
            "status": "refused",
            "reason": refusal_reason,
            "processes": processes,
            "document_inventory_source": inventory_source,
            "unsaved": unsaved,
            "owned_modified_documents": owned_modified_documents,
        }
        path = _log_process_action(job_path, action)
        raise RuntimeError(f"Fusion has unsaved user-owned work; refused restart and logged {path}")

    payload = {
        "timeout_seconds": timeout_seconds,
        "allow_force": allow_force,
        "had_processes": bool(processes),
    }
    script = (
        _json_payload_script(payload)
        + r"""
$deadline = (Get-Date).AddSeconds([int]$payload.timeout_seconds)
$initial = @(Get-Process Fusion360 -ErrorAction SilentlyContinue)
foreach ($proc in $initial) { $null = $proc.CloseMainWindow() }
while ((Get-Date) -lt $deadline) {
  $remaining = @(Get-Process Fusion360 -ErrorAction SilentlyContinue)
  if ($remaining.Count -eq 0) { break }
  Start-Sleep -Milliseconds 500
}
$remaining = @(Get-Process Fusion360 -ErrorAction SilentlyContinue)
if ($remaining.Count -gt 0 -and [bool]$payload.allow_force) {
  $remaining | Stop-Process -Force
  Start-Sleep -Seconds 2
  $remaining = @(Get-Process Fusion360 -ErrorAction SilentlyContinue)
}
if ($remaining.Count -gt 0) {
  @{ status = "failed"; remaining = $remaining.Count } | ConvertTo-Json -Compress -Depth 5
  exit 2
}
"""
        + _fusion_executable_start_script()
        + r"""
@{ status = "restarted"; closed = $initial.Count; launcher = $fusionExe } | ConvertTo-Json -Compress -Depth 5
"""
    )
    action: dict[str, Any] = {
        "action": "restart",
        "requested_at": _utc_now(),
        "allow_unsaved_close": allow_unsaved_close,
        "allow_force": allow_force,
        "status": "restarted",
        "processes": processes,
        "document_inventory_source": inventory_source,
        "owned_modified_documents": owned_modified_documents,
    }
    try:
        action["result"] = run_powershell_json(script, timeout_seconds=timeout_seconds + 20)
    except Exception as exc:
        action["status"] = "failed"
        action["error"] = str(exc)
        path = _log_process_action(job_path, action)
        raise RuntimeError(f"Fusion restart failed; logged {path}: {exc}") from exc
    return _log_process_action(job_path, action)


def fusion_ui_snapshot(
    *,
    process_id: int | None = None,
    max_depth: int = 4,
    max_nodes: int = 300,
) -> dict[str, Any]:
    payload = {"process_id": process_id, "max_depth": max_depth, "max_nodes": max_nodes}
    script = (
        _json_payload_script(payload)
        + r"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$targetPid = $payload.process_id
if (-not $targetPid) {
  $proc = Get-Process Fusion360 -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $proc) {
    @{ schema = "cbbs-cad/fusion-uia-snapshot/v1"; status = "missing-process" } |
      ConvertTo-Json -Compress -Depth 5
    exit 0
  }
  $targetPid = $proc.Id
}
$root = [System.Windows.Automation.AutomationElement]::RootElement
$cond = New-Object System.Windows.Automation.PropertyCondition(
  [System.Windows.Automation.AutomationElement]::ProcessIdProperty,
  [int]$targetPid
)
$window = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $cond)
if (-not $window) {
  @{ schema = "cbbs-cad/fusion-uia-snapshot/v1"; status = "missing-window"; process_id = $targetPid } |
    ConvertTo-Json -Compress -Depth 5
  exit 0
}
$script:count = 0
function Convert-Node($element, [int]$depth) {
  if ($script:count -ge [int]$payload.max_nodes) { return $null }
  $script:count += 1
  $rect = $element.Current.BoundingRectangle
  $node = [ordered]@{
    name = $element.Current.Name
    automation_id = $element.Current.AutomationId
    class_name = $element.Current.ClassName
    control_type = $element.Current.ControlType.ProgrammaticName
    native_window_handle = $element.Current.NativeWindowHandle
    is_enabled = $element.Current.IsEnabled
    has_keyboard_focus = $element.Current.HasKeyboardFocus
    bounding_rect = [ordered]@{
      x = $rect.X
      y = $rect.Y
      width = $rect.Width
      height = $rect.Height
    }
    children = @()
  }
  if ($depth -lt [int]$payload.max_depth) {
    $children = $element.FindAll(
      [System.Windows.Automation.TreeScope]::Children,
      [System.Windows.Automation.Condition]::TrueCondition
    )
    foreach ($child in $children) {
      $childNode = Convert-Node $child ($depth + 1)
      if ($childNode) { $node.children += $childNode }
    }
  }
  return $node
}
$rootNode = Convert-Node $window 0
@{
  schema = "cbbs-cad/fusion-uia-snapshot/v1"
  status = "ok"
  process_id = $targetPid
  node_count = $script:count
  root = $rootNode
} | ConvertTo-Json -Compress -Depth 40
"""
    )
    return run_powershell_json(script, timeout_seconds=45)


def fusion_ui_invoke(
    *,
    name: str | None = None,
    automation_id: str | None = None,
    control_type: str | None = None,
    process_id: int | None = None,
    allow_click: bool = False,
    allow_keys: bool = False,
    keys: str | None = None,
    close_window: bool = False,
    allow_close_window: bool = False,
) -> dict[str, Any]:
    if not any([name, automation_id, close_window]):
        raise ValueError("provide --name, --automation-id, or --close-window")
    if keys and not allow_keys:
        raise ValueError("--keys requires --allow-keys")
    if close_window and not allow_close_window:
        raise ValueError("--close-window requires --allow-close-window")

    payload = {
        "name": name,
        "automation_id": automation_id,
        "control_type": control_type,
        "process_id": process_id,
        "allow_click": allow_click,
        "allow_keys": allow_keys,
        "keys": keys,
        "close_window": close_window,
        "allow_close_window": allow_close_window,
    }
    script = (
        _json_payload_script(payload)
        + r"""
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$targetPid = $payload.process_id
if (-not $targetPid) {
  $proc = Get-Process Fusion360 -ErrorAction SilentlyContinue | Select-Object -First 1
  if (-not $proc) {
    @{ status = "missing-process" } | ConvertTo-Json -Compress -Depth 5
    exit 0
  }
  $targetPid = $proc.Id
}
$root = [System.Windows.Automation.AutomationElement]::RootElement
$pidCond = New-Object System.Windows.Automation.PropertyCondition(
  [System.Windows.Automation.AutomationElement]::ProcessIdProperty,
  [int]$targetPid
)
$window = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $pidCond)
if (-not $window) {
  @{ status = "missing-window"; process_id = $targetPid } | ConvertTo-Json -Compress -Depth 5
  exit 0
}
if ([bool]$payload.close_window) {
  $pattern = $null
  if ($window.TryGetCurrentPattern(
    [System.Windows.Automation.WindowPattern]::Pattern,
    [ref]$pattern
  )) {
    $pattern.Close()
    @{ status = "closed-window"; process_id = $targetPid } | ConvertTo-Json -Compress -Depth 5
    exit 0
  }
  @{ status = "missing-window-pattern"; process_id = $targetPid } | ConvertTo-Json -Compress -Depth 5
  exit 0
}
$conditions = New-Object System.Collections.Generic.List[System.Windows.Automation.Condition]
if ($payload.automation_id) {
  $conditions.Add((New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::AutomationIdProperty,
    [string]$payload.automation_id
  )))
}
if ($payload.name) {
  $conditions.Add((New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::NameProperty,
    [string]$payload.name
  )))
}
$cond = [System.Windows.Automation.Condition]::TrueCondition
if ($conditions.Count -eq 1) {
  $cond = $conditions[0]
} elseif ($conditions.Count -gt 1) {
  $cond = New-Object System.Windows.Automation.AndCondition($conditions.ToArray())
}
$matches = $window.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond)
$target = $null
foreach ($item in $matches) {
  if ($payload.control_type -and $item.Current.ControlType.ProgrammaticName -ne $payload.control_type) {
    continue
  }
  $target = $item
  break
}
if (-not $target) {
  @{ status = "missing-target"; process_id = $targetPid; matches = $matches.Count } |
    ConvertTo-Json -Compress -Depth 5
  exit 0
}
$target.SetFocus()
$invoke = $null
if ($target.TryGetCurrentPattern(
  [System.Windows.Automation.InvokePattern]::Pattern,
  [ref]$invoke
)) {
  $invoke.Invoke()
  @{
    status = "invoked"
    name = $target.Current.Name
    automation_id = $target.Current.AutomationId
    control_type = $target.Current.ControlType.ProgrammaticName
  } | ConvertTo-Json -Compress -Depth 5
  exit 0
}
if ([bool]$payload.allow_click) {
  Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class NativeMouse {
  [DllImport("user32.dll")] public static extern bool SetCursorPos(int X, int Y);
  [DllImport("user32.dll")] public static extern void mouse_event(int dwFlags, int dx, int dy, int dwData, int dwExtraInfo);
  public const int LEFTDOWN = 0x0002;
  public const int LEFTUP = 0x0004;
}
"@
  $rect = $target.Current.BoundingRectangle
  $x = [int]($rect.X + ($rect.Width / 2))
  $y = [int]($rect.Y + ($rect.Height / 2))
  [NativeMouse]::SetCursorPos($x, $y) | Out-Null
  [NativeMouse]::mouse_event([NativeMouse]::LEFTDOWN, 0, 0, 0, 0)
  [NativeMouse]::mouse_event([NativeMouse]::LEFTUP, 0, 0, 0, 0)
  @{ status = "clicked"; x = $x; y = $y; name = $target.Current.Name } |
    ConvertTo-Json -Compress -Depth 5
  exit 0
}
if ([bool]$payload.allow_keys -and $payload.keys) {
  Add-Type -AssemblyName System.Windows.Forms
  [System.Windows.Forms.SendKeys]::SendWait([string]$payload.keys)
  @{ status = "sent-keys"; name = $target.Current.Name } | ConvertTo-Json -Compress -Depth 5
  exit 0
}
@{
  status = "missing-invoke-pattern"
  name = $target.Current.Name
  automation_id = $target.Current.AutomationId
  control_type = $target.Current.ControlType.ProgrammaticName
} | ConvertTo-Json -Compress -Depth 5
"""
    )
    return run_powershell_json(script, timeout_seconds=45)
