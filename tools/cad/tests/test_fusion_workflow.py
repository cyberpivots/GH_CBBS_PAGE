from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from cbbs_cad.fusion_agent import enqueue_agent_command
from cbbs_cad.fusion_job import create_fusion_job
from cbbs_cad.fusion_workflow import (
    UnsupportedUrlPathError,
    check_fusion_status,
    install_fusion_addin,
    is_url_like_path,
    resolve_local_artifact_path,
)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _touch(path: Path, text: str = "ok") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _fake_job(tmp_path: Path) -> Path:
    _touch(tmp_path / "cad" / "part.step")
    _touch(tmp_path / "cad" / "part.stl")
    job_path = tmp_path / "fusion" / "latest-job.json"
    job = {
        "schema": "cbbs-cad/fusion-job/v1",
        "created_at": "2026-05-01T00:00:00+00:00",
        "run_id": "fusion-test",
        "truth_state": "internal review",
        "repo_root": str(tmp_path),
        "repo_root_windows": None,
        "source_manifest": "cad/manifest.json",
        "output_root": "fusion",
        "document_mode": "new",
        "ui_message_box": False,
        "wait_for_renders": True,
        "summary_path": "run-summary.json",
        "render": {
            "enabled": True,
            "resolution": "Mobile960x640RenderResolution",
            "views": ["front", "isometric"],
            "outputs": {
                "front": "renders/fusion-test-front.png",
                "isometric": "renders/fusion-test-isometric.png",
            },
        },
        "exports": {
            "step": True,
            "stl": True,
            "outputs": {
                "step": "exports/fusion-test-review.step",
                "stl": "exports/fusion-test-review.stl",
            },
        },
        "artifacts": [
            {
                "concept_id": "part",
                "name": "Part",
                "truth_state": "internal review",
                "measurement_status": "measurement-required",
                "files": {"step": "cad/part.step", "stl": "cad/part.stl"},
            }
        ],
    }
    _write_json(job_path, job)
    return job_path


def _complete_fake_run(tmp_path: Path, job_path: Path) -> None:
    fusion_root = tmp_path / "fusion"
    _touch(
        fusion_root / "logs" / "fusion-job-20260501-000000-fusion-test.log",
        "Imported /tmp/part.step; result=True\n",
    )
    _touch(fusion_root / "exports" / "fusion-test-review.step")
    _touch(fusion_root / "exports" / "fusion-test-review.stl")
    _touch(fusion_root / "renders" / "fusion-test-front.png")
    _touch(fusion_root / "renders" / "fusion-test-isometric.png")
    _write_json(
        fusion_root / "run-summary.json",
        {
            "schema": "cbbs-cad/fusion-run-summary/v1",
            "run_id": "fusion-test",
            "status": "completed",
            "artifact_count": 1,
            "imports": [{"concept_id": "part", "status": "imported", "result": True}],
            "renders": [
                {"view": "front", "status": "completed", "progress": 1.0},
                {"view": "isometric", "status": "completed", "progress": 1.0},
            ],
            "exports": [
                {"kind": "step", "status": "exported", "result": True},
                {"kind": "stl", "status": "exported", "result": True},
            ],
        },
    )
    now = time.time()
    os.utime(job_path, (now, now))
    for output in (tmp_path / "fusion").rglob("*"):
        if output.is_file() and output != job_path:
            os.utime(output, (now + 1, now + 1))


def test_create_fusion_job_includes_run_controls(tmp_path) -> None:
    manifest_path = tmp_path / "manifest.json"
    _write_json(
        manifest_path,
        {
            "schema": "cbbs-cad/generated-manifest/v1",
            "artifacts": [
                {
                    "concept_id": "sample",
                    "name": "Sample",
                    "truth_state": "internal review",
                    "measurement_status": "measurement-required",
                    "files": {"step": "sample.step", "stl": "sample.stl"},
                }
            ],
        },
    )

    job = create_fusion_job(manifest_path, tmp_path / "latest-job.json")

    assert job["run_id"].startswith("fusion-")
    assert job["document_mode"] == "new"
    assert job["document_lifecycle"]["close_generated_documents"] is True
    assert job["document_lifecycle"]["save_policy"] == "discard_generated"
    assert job["document_lifecycle"]["allow_user_prompt"] is False
    assert job["ui_message_box"] is False
    assert job["wait_for_renders"] is True
    assert job["summary_path"] == "run-summary.json"
    assert job["render"]["mode"] == "per-artifact-source"
    assert job["render"]["isolate_view_sources"] is True
    assert job["render"]["views"] == ["sample__model"]
    assert job["render"]["outputs"]["sample__model"].startswith(f"renders/{job['run_id']}")
    assert job["render"]["view_sources"]["sample__model"] == "sample.step"
    assert job["exports"]["outputs"]["step"].startswith(f"exports/{job['run_id']}")


def test_fusion_artifact_path_validation_rejects_url_like_paths(tmp_path) -> None:
    for raw in (
        "http://example.test/part.step",
        "https://example.test/part.step",
        "file:///tmp/part.step",
        "fusion360://design/abc",
        "urn:artifact:part",
    ):
        assert is_url_like_path(raw) is True
        with pytest.raises(UnsupportedUrlPathError):
            resolve_local_artifact_path(raw, tmp_path)


def test_fusion_artifact_path_validation_accepts_local_paths(tmp_path) -> None:
    part = tmp_path / "part.step"
    _touch(part)

    assert resolve_local_artifact_path("part.step", tmp_path) == part
    assert resolve_local_artifact_path(part, tmp_path) == part
    assert str(
        resolve_local_artifact_path(r"C:\cbbs\part.step", tmp_path, must_exist=False)
    ).endswith("/mnt/c/cbbs/part.step")

    repo_file = Path(__file__).resolve().parents[3] / "package.json"
    if repo_file.exists():
        assert resolve_local_artifact_path(repo_file, tmp_path) == repo_file


def test_fusion_artifact_path_validation_requires_existing_import_file(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        resolve_local_artifact_path("missing.step", tmp_path)


def test_fusion_archive_export_agent_request_is_local_file_only(tmp_path) -> None:
    job_path = _fake_job(tmp_path)
    output_path = tmp_path / "fusion" / "assembly-documentation" / "run" / "review.f3d"

    request_id, request_path = enqueue_agent_command(
        "export_active_archive",
        job_path=job_path,
        request_id="archive-test",
        payload={"path": str(output_path)},
    )
    payload = json.loads(request_path.read_text(encoding="utf-8"))

    assert request_id == "archive-test"
    assert payload["schema"] == "cbbs-cad/fusion-agent-command/v1"
    assert payload["action"] == "export_active_archive"
    assert payload["path"] == str(output_path)


def test_create_fusion_job_includes_assembly_views(tmp_path) -> None:
    manifest_path = tmp_path / "manifest.json"
    _touch(tmp_path / "cad" / "p070.step")
    _touch(tmp_path / "cad" / "assembly" / "p070" / "parts" / "rear_tray.step")
    _touch(tmp_path / "cad" / "assembly" / "p070" / "views" / "p070_exploded.step")
    _write_json(
        manifest_path,
        {
            "schema": "cbbs-cad/generated-manifest/v1",
            "artifacts": [
                {
                    "concept_id": "p070_hinged_wall_enclosure",
                    "name": "P070 hinged wall enclosure",
                    "truth_state": "internal review",
                    "measurement_status": "measurement-required",
                    "files": {"step": "cad/p070.step"},
                    "assembly": {
                        "schema": "cbbs-cad/generated-assembly/v1",
                        "mode": "component-parts",
                        "parts": [
                            {
                                "id": "rear_tray",
                                "name": "Rear tray",
                                "role": "print",
                                "files": {"step": "cad/assembly/p070/parts/rear_tray.step"},
                            }
                        ],
                        "views": {
                            "exploded": {
                                "file": "cad/assembly/p070/views/p070_exploded.step",
                            }
                        },
                        "metadata": {
                            "printer_target": "Creality K1 series ASA",
                            "print_layouts": {
                                "k1-plate-tray": {"fits_with_6mm_brim": True},
                                "k1-plate-door": {"fits_with_6mm_brim": True},
                                "k1-combined": {
                                    "fits_with_6mm_brim": False,
                                    "accepted": False,
                                },
                            },
                        },
                    },
                }
            ],
        },
    )

    job = create_fusion_job(manifest_path, tmp_path / "latest-job.json")

    assert job["assembly"]["enabled"] is True
    assert job["render"]["views"] == [
        "p070_hinged_wall_enclosure__model",
        "p070_hinged_wall_enclosure__exploded",
    ]
    assert job["render"]["outputs"]["p070_hinged_wall_enclosure__model"].startswith(
        f"renders/{job['run_id']}"
    )
    assert (
        job["render"]["outputs"]["p070_hinged_wall_enclosure__exploded"]
        .startswith(f"renders/{job['run_id']}")
    )
    assert job["render"]["view_sources"]["p070_hinged_wall_enclosure__model"] == "cad/p070.step"
    assert (
        job["render"]["view_sources"]["p070_hinged_wall_enclosure__exploded"]
        == "cad/assembly/p070/views/p070_exploded.step"
    )
    assert job["artifacts"][0]["assembly"]["parts"][0]["id"] == "rear_tray"
    assert job["print_layouts"]["k1-plate-tray"]["fits_with_6mm_brim"] is True
    assert job["print_layouts"]["k1-combined"]["accepted"] is False


def test_create_fusion_job_renders_standalone_models_separately(tmp_path) -> None:
    manifest_path = tmp_path / "manifest.json"
    _write_json(
        manifest_path,
        {
            "schema": "cbbs-cad/generated-manifest/v1",
            "artifacts": [
                {
                    "concept_id": "surface_coupon",
                    "name": "Surface coupon",
                    "truth_state": "internal review",
                    "measurement_status": "measurement-required",
                    "files": {"step": "cad/surface_coupon.step", "stl": "cad/surface_coupon.stl"},
                },
                {
                    "concept_id": "wall_coupon",
                    "name": "Wall coupon",
                    "truth_state": "internal review",
                    "measurement_status": "measurement-required",
                    "files": {"step": "cad/wall_coupon.step", "stl": "cad/wall_coupon.stl"},
                },
            ],
        },
    )

    job = create_fusion_job(manifest_path, tmp_path / "latest-job.json")

    assert job["assembly"]["enabled"] is False
    assert job["render"]["views"] == ["surface_coupon__model", "wall_coupon__model"]
    assert job["render"]["view_sources"] == {
        "surface_coupon__model": "cad/surface_coupon.step",
        "wall_coupon__model": "cad/wall_coupon.step",
    }
    assert set(job["render"]["outputs"]) == {"surface_coupon__model", "wall_coupon__model"}


def test_create_fusion_job_namespaces_duplicate_assembly_view_names(tmp_path) -> None:
    manifest_path = tmp_path / "manifest.json"
    _touch(tmp_path / "cad" / "assembly" / "first" / "views" / "first_exploded.step")
    _touch(tmp_path / "cad" / "assembly" / "second" / "views" / "second_exploded.step")
    _write_json(
        manifest_path,
        {
            "schema": "cbbs-cad/generated-manifest/v1",
            "artifacts": [
                {
                    "concept_id": "first_assembly",
                    "name": "First assembly",
                    "truth_state": "internal review",
                    "measurement_status": "measurement-required",
                    "files": {},
                    "assembly": {
                        "parts": [],
                        "views": {
                            "exploded": {
                                "file": "cad/assembly/first/views/first_exploded.step",
                            }
                        },
                    },
                },
                {
                    "concept_id": "second_assembly",
                    "name": "Second assembly",
                    "truth_state": "internal review",
                    "measurement_status": "measurement-required",
                    "files": {},
                    "assembly": {
                        "parts": [],
                        "views": {
                            "exploded": {
                                "file": "cad/assembly/second/views/second_exploded.step",
                            }
                        },
                    },
                },
            ],
        },
    )

    job = create_fusion_job(manifest_path, tmp_path / "latest-job.json")

    assert job["render"]["views"] == [
        "first_assembly__exploded",
        "second_assembly__exploded",
    ]
    assert (
        job["render"]["view_sources"]["first_assembly__exploded"]
        == "cad/assembly/first/views/first_exploded.step"
    )
    assert (
        job["render"]["view_sources"]["second_assembly__exploded"]
        == "cad/assembly/second/views/second_exploded.step"
    )


def test_create_fusion_job_can_keep_documents_open_for_review(tmp_path) -> None:
    manifest_path = tmp_path / "manifest.json"
    _write_json(
        manifest_path,
        {
            "schema": "cbbs-cad/generated-manifest/v1",
            "artifacts": [
                {
                    "concept_id": "sample",
                    "name": "Sample",
                    "truth_state": "internal review",
                    "measurement_status": "measurement-required",
                    "files": {"step": "sample.step", "stl": "sample.stl"},
                }
            ],
        },
    )

    job = create_fusion_job(
        manifest_path,
        tmp_path / "latest-job.json",
        keep_open_for_review=True,
    )

    assert job["document_lifecycle"]["keep_open_for_review"] is True
    assert job["document_lifecycle"]["close_generated_documents"] is False


def test_install_fusion_addin_sets_manifest_and_job_pointer(tmp_path) -> None:
    job_path = _fake_job(tmp_path)
    installed = tmp_path / "installed" / "CBBSFusionAutomation"

    result = install_fusion_addin(job_path=job_path, addin_dir=installed)

    manifest = json.loads((installed / "CBBSFusionAutomation.manifest").read_text(encoding="utf-8"))
    assert manifest["runOnStartup"] is True
    assert (installed / "CBBSFusionAutomation.py").is_file()
    assert Path(result["job_pointer"]).read_text(encoding="utf-8").strip() == str(job_path.resolve())


def test_fusion_status_passes_for_complete_fake_run(tmp_path) -> None:
    job_path = _fake_job(tmp_path)
    installed = tmp_path / "installed" / "CBBSFusionAutomation"
    install_fusion_addin(job_path=job_path, addin_dir=installed)
    _complete_fake_run(tmp_path, job_path)

    results = check_fusion_status(job_path=job_path, addin_dir=installed)

    assert all(result.ok for result in results)


def test_fusion_status_fails_for_leftover_cbbs_owned_modified_document(tmp_path) -> None:
    job_path = _fake_job(tmp_path)
    installed = tmp_path / "installed" / "CBBSFusionAutomation"
    install_fusion_addin(job_path=job_path, addin_dir=installed)
    _complete_fake_run(tmp_path, job_path)
    summary_path = tmp_path / "fusion" / "run-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["documents"] = [
        {
            "name": "CBBS generated fusion-test job",
            "cbbs_owned": True,
            "isModified": True,
            "status": "close_failed",
        }
    ]
    _write_json(summary_path, summary)

    results = check_fusion_status(job_path=job_path, addin_dir=installed)

    cleanup = next(result for result in results if result.name == "Generated document cleanup")
    assert cleanup.ok is False


def test_fusion_status_allows_leftover_document_in_review_mode(tmp_path) -> None:
    job_path = _fake_job(tmp_path)
    job = json.loads(job_path.read_text(encoding="utf-8"))
    job["document_lifecycle"] = {
        "owner": "cbbs-cad",
        "close_generated_documents": False,
        "keep_open_for_review": True,
        "save_policy": "discard_generated",
        "allow_user_prompt": False,
    }
    _write_json(job_path, job)
    installed = tmp_path / "installed" / "CBBSFusionAutomation"
    install_fusion_addin(job_path=job_path, addin_dir=installed)
    _complete_fake_run(tmp_path, job_path)
    summary_path = tmp_path / "fusion" / "run-summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    summary["documents"] = [
        {
            "name": "CBBS generated fusion-test job",
            "cbbs_owned": True,
            "isModified": True,
            "status": "kept_open_for_review",
        }
    ]
    _write_json(summary_path, summary)

    results = check_fusion_status(job_path=job_path, addin_dir=installed)

    cleanup = next(result for result in results if result.name == "Generated document cleanup")
    assert cleanup.ok is True


def test_fusion_status_detects_bad_installed_manifest(tmp_path) -> None:
    job_path = _fake_job(tmp_path)
    installed = tmp_path / "installed" / "CBBSFusionAutomation"
    install_fusion_addin(job_path=job_path, addin_dir=installed)
    manifest_path = installed / "CBBSFusionAutomation.manifest"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["runOnStartup"] = False
    _write_json(manifest_path, manifest)
    _complete_fake_run(tmp_path, job_path)

    results = check_fusion_status(job_path=job_path, addin_dir=installed)

    run_on_startup = next(result for result in results if result.name == "Installed runOnStartup")
    assert run_on_startup.ok is False


def test_fusion_status_fails_when_log_is_missing_or_stale(tmp_path) -> None:
    job_path = _fake_job(tmp_path)
    installed = tmp_path / "installed" / "CBBSFusionAutomation"
    install_fusion_addin(job_path=job_path, addin_dir=installed)

    missing_results = check_fusion_status(job_path=job_path, addin_dir=installed)
    assert next(result for result in missing_results if result.name == "Latest Fusion log").ok is False

    _complete_fake_run(tmp_path, job_path)
    stale_log = tmp_path / "fusion" / "logs" / "fusion-job-20260501-000000-fusion-test.log"
    now = time.time()
    os.utime(stale_log, (now - 10, now - 10))
    os.utime(job_path, (now, now))

    stale_results = check_fusion_status(job_path=job_path, addin_dir=installed)
    latest_log = next(result for result in stale_results if result.name == "Latest Fusion log")
    assert latest_log.ok is False


def test_fusion_status_requires_assembly_source_render_records(tmp_path) -> None:
    _touch(tmp_path / "cad" / "assembly" / "p070" / "parts" / "rear_tray.step")
    _touch(tmp_path / "cad" / "assembly" / "p070" / "views" / "p070_exploded.step")
    job_path = tmp_path / "fusion" / "latest-job.json"
    _write_json(
        job_path,
        {
            "schema": "cbbs-cad/fusion-job/v1",
            "created_at": "2026-05-01T00:00:00+00:00",
            "run_id": "fusion-assembly-test",
            "truth_state": "internal review",
            "repo_root": str(tmp_path),
            "repo_root_windows": None,
            "source_manifest": "cad/manifest.json",
            "output_root": "fusion",
            "document_mode": "new",
            "ui_message_box": False,
            "wait_for_renders": True,
            "summary_path": "run-summary.json",
            "assembly": {"enabled": True, "artifacts": []},
            "render": {
                "enabled": True,
                "resolution": "Mobile960x640RenderResolution",
                "views": ["exploded"],
                "outputs": {"exploded": "renders/fusion-assembly-test-exploded.png"},
                "view_sources": {
                    "exploded": "cad/assembly/p070/views/p070_exploded.step",
                },
            },
            "exports": {
                "step": False,
                "stl": False,
                "outputs": {},
            },
            "artifacts": [
                {
                    "concept_id": "p070_hinged_wall_enclosure",
                    "name": "P070 hinged wall enclosure",
                    "truth_state": "internal review",
                    "measurement_status": "measurement-required",
                    "files": {},
                    "assembly": {
                        "parts": [
                            {
                                "id": "rear_tray",
                                "files": {
                                    "step": "cad/assembly/p070/parts/rear_tray.step",
                                },
                            }
                        ],
                        "views": {
                            "exploded": {
                                "file": "cad/assembly/p070/views/p070_exploded.step",
                            }
                        },
                    },
                }
            ],
        },
    )
    installed = tmp_path / "installed" / "CBBSFusionAutomation"
    install_fusion_addin(job_path=job_path, addin_dir=installed)
    _touch(
        tmp_path / "fusion" / "logs" / "fusion-job-20260501-000000-fusion-assembly-test.log",
        "Imported /tmp/rear_tray.step; result=True\n",
    )
    _touch(tmp_path / "fusion" / "renders" / "fusion-assembly-test-exploded.png")
    _write_json(
        tmp_path / "fusion" / "run-summary.json",
        {
            "schema": "cbbs-cad/fusion-run-summary/v1",
            "run_id": "fusion-assembly-test",
            "status": "completed",
            "artifact_count": 1,
            "imports": [{"concept_id": "p070_hinged_wall_enclosure", "status": "imported"}],
            "renders": [{"view": "exploded", "status": "completed"}],
            "exports": [],
        },
    )

    results = check_fusion_status(job_path=job_path, addin_dir=installed)

    render_sources = next(result for result in results if result.name == "Render source imports")
    assert render_sources.ok is False
