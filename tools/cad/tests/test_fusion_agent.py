from __future__ import annotations

import json
from pathlib import Path

import pytest

from cbbs_cad.fusion_agent import (
    AGENT_COMMAND_SCHEMA,
    agent_paths,
    enqueue_agent_command,
    fresh_bridge_document_inventory,
    fusion_agent_status,
    fusion_ui_invoke,
    output_root_for_job,
    restart_fusion,
    wait_for_agent_response,
)
from cbbs_cad.fusion_workflow import install_fusion_addin


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _fake_job(tmp_path: Path) -> Path:
    job_path = tmp_path / "fusion" / "latest-job.json"
    _write_json(
        job_path,
        {
            "schema": "cbbs-cad/fusion-job/v1",
            "run_id": "fusion-agent-test",
            "repo_root": str(tmp_path),
            "repo_root_windows": None,
            "output_root": "fusion",
            "artifacts": [],
        },
    )
    return job_path


def test_enqueue_agent_command_writes_request(tmp_path) -> None:
    job_path = _fake_job(tmp_path)

    request_id, request_path = enqueue_agent_command(
        "ui_state",
        job_path=job_path,
        request_id="request-1",
        payload={"extra": "value"},
    )

    request = json.loads(request_path.read_text(encoding="utf-8"))
    assert request_id == "request-1"
    assert request["schema"] == AGENT_COMMAND_SCHEMA
    assert request["action"] == "ui_state"
    assert request["extra"] == "value"
    assert request["job_path"] == str(job_path.resolve())


def test_enqueue_cleanup_owned_documents_action(tmp_path) -> None:
    job_path = _fake_job(tmp_path)

    _, request_path = enqueue_agent_command(
        "cleanup_owned_documents",
        job_path=job_path,
        request_id="cleanup-1",
    )

    request = json.loads(request_path.read_text(encoding="utf-8"))
    assert request["action"] == "cleanup_owned_documents"


def test_wait_for_agent_response_reads_response(tmp_path) -> None:
    job_path = _fake_job(tmp_path)
    paths = agent_paths(job_path, ensure=True)
    _write_json(
        paths.responses / "request-1.json",
        {
            "schema": "cbbs-cad/fusion-agent-response/v1",
            "request_id": "request-1",
            "status": "ok",
        },
    )

    response = wait_for_agent_response("request-1", job_path=job_path, timeout_seconds=1)

    assert response["status"] == "ok"


def test_fusion_agent_status_reports_fresh_heartbeat_and_installed_addin(tmp_path, monkeypatch) -> None:
    job_path = _fake_job(tmp_path)
    installed = tmp_path / "installed" / "CBBSFusionAutomation"
    install_fusion_addin(job_path=job_path, addin_dir=installed)
    paths = agent_paths(job_path, ensure=True)
    _write_json(
        paths.heartbeat,
        {
            "schema": "cbbs-cad/fusion-agent-heartbeat/v1",
            "updated_at": "2026-05-02T00:00:00+00:00",
        },
    )
    paths.heartbeat.touch()
    monkeypatch.setattr(
        "cbbs_cad.fusion_agent.fusion_processes",
        lambda: [{"id": 123, "main_window_title": "Fusion"}],
    )

    status = fusion_agent_status(job_path=job_path, addin_dir=installed)

    assert status["heartbeat_fresh"] is True
    assert status["heartbeat_age_seconds"] >= 0
    checks = {check["name"]: check for check in status["checks"]}
    assert checks["Fusion process"]["ok"] is True
    assert checks["Installed add-in source"]["ok"] is True


def test_fresh_bridge_document_inventory_reads_heartbeat_documents(tmp_path) -> None:
    job_path = _fake_job(tmp_path)
    paths = agent_paths(job_path, ensure=True)
    documents = [{"name": "CBBS generated fusion-agent-test job", "cbbs_owned": True}]
    _write_json(
        paths.heartbeat,
        {
            "schema": "cbbs-cad/fusion-agent-heartbeat/v1",
            "updated_at": "2026-05-02T00:00:00+00:00",
            "documents": documents,
        },
    )

    assert fresh_bridge_document_inventory(job_path=job_path) == documents


def test_restart_fusion_refuses_unsaved_window(tmp_path, monkeypatch) -> None:
    job_path = _fake_job(tmp_path)
    monkeypatch.setattr(
        "cbbs_cad.fusion_agent.fusion_processes",
        lambda: [{"id": 123, "main_window_title": "Untitled* - Autodesk Fusion"}],
    )

    with pytest.raises(RuntimeError, match="unsaved"):
        restart_fusion(job_path=job_path, allow_unsaved_close=False, install_first=False)

    process_logs = list((output_root_for_job(job_path) / "agent" / "process-actions").glob("*.json"))
    assert process_logs
    logged = json.loads(process_logs[0].read_text(encoding="utf-8"))
    assert logged["status"] == "refused"
    assert logged["reason"] == "unsaved-window"


def test_restart_fusion_refuses_untitled_window_without_star(tmp_path, monkeypatch) -> None:
    job_path = _fake_job(tmp_path)
    monkeypatch.setattr(
        "cbbs_cad.fusion_agent.fusion_processes",
        lambda: [{"id": 123, "main_window_title": "Untitled - Autodesk Fusion"}],
    )

    with pytest.raises(RuntimeError, match="unsaved"):
        restart_fusion(job_path=job_path, allow_unsaved_close=False, install_first=False)

    process_logs = list((output_root_for_job(job_path) / "agent" / "process-actions").glob("*.json"))
    logged = json.loads(process_logs[0].read_text(encoding="utf-8"))
    assert logged["reason"] == "unsaved-window"


def test_restart_fusion_prefers_bridge_inventory_for_unsaved_user_documents(
    tmp_path, monkeypatch
) -> None:
    job_path = _fake_job(tmp_path)
    paths = agent_paths(job_path, ensure=True)
    _write_json(
        paths.heartbeat,
        {
            "schema": "cbbs-cad/fusion-agent-heartbeat/v1",
            "updated_at": "2026-05-02T00:00:00+00:00",
            "documents": [
                {
                    "name": "User design",
                    "cbbs_owned": False,
                    "isModified": True,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "cbbs_cad.fusion_agent.fusion_processes",
        lambda: [{"id": 123, "main_window_title": "Fusion"}],
    )

    with pytest.raises(RuntimeError, match="unsaved user-owned work"):
        restart_fusion(job_path=job_path, allow_unsaved_close=False, install_first=False)

    process_logs = list((output_root_for_job(job_path) / "agent" / "process-actions").glob("*.json"))
    logged = json.loads(process_logs[0].read_text(encoding="utf-8"))
    assert logged["reason"] == "user-unsaved-documents"
    assert logged["document_inventory_source"] == "bridge-heartbeat"


def test_restart_fusion_does_not_require_unsaved_flag_for_owned_generated_docs(
    tmp_path, monkeypatch
) -> None:
    job_path = _fake_job(tmp_path)
    paths = agent_paths(job_path, ensure=True)
    _write_json(
        paths.heartbeat,
        {
            "schema": "cbbs-cad/fusion-agent-heartbeat/v1",
            "updated_at": "2026-05-02T00:00:00+00:00",
            "documents": [
                {
                    "name": "CBBS generated fusion-agent-test job",
                    "cbbs_owned": True,
                    "isModified": True,
                }
            ],
        },
    )
    monkeypatch.setattr(
        "cbbs_cad.fusion_agent.fusion_processes",
        lambda: [{"id": 123, "main_window_title": "Fusion"}],
    )
    monkeypatch.setattr(
        "cbbs_cad.fusion_agent.run_powershell_json",
        lambda *_args, **_kwargs: {"status": "restarted", "closed": 1},
    )

    restart_fusion(job_path=job_path, allow_unsaved_close=False, install_first=False)

    process_logs = list((output_root_for_job(job_path) / "agent" / "process-actions").glob("*.json"))
    logged = json.loads(process_logs[0].read_text(encoding="utf-8"))
    assert logged["status"] == "restarted"
    assert logged["document_inventory_source"] == "bridge-heartbeat"
    assert logged["owned_modified_documents"][0]["cbbs_owned"] is True


def test_ui_invoke_requires_explicit_guards() -> None:
    with pytest.raises(ValueError, match="provide"):
        fusion_ui_invoke()

    with pytest.raises(ValueError, match="allow-keys"):
        fusion_ui_invoke(name="Search", keys="^p")
