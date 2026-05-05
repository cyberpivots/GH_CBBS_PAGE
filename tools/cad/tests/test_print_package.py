from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from cbbs_cad.models import PrinterSpec
from cbbs_cad.print_package import (
    DEFAULT_PRINT_CONCEPT_ID,
    create_print_package,
    printer_by_id,
    validate_material_for_printer,
    validate_printer_for_package,
)
from cbbs_cad.specs import DEFAULT_DATA_DIR, load_specs


def _write(path: Path, text: str = "fixture") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _fake_p070_manifest(tmp_path: Path) -> tuple[Path, Path]:
    cad_root = tmp_path / "cad"
    fusion_root = tmp_path / "fusion"
    concept_id = DEFAULT_PRINT_CONCEPT_ID
    part_root = cad_root / "assembly" / concept_id / "parts"
    view_root = cad_root / "assembly" / concept_id / "views"

    for part_id in ("rear_tray", "rear_panel_core", "rear_battery_pod", "front_display_door"):
        _write(part_root / f"{part_id}.step")
        _write(part_root / f"{part_id}.stl")
    for view_id in (
        "k1-component-rear-panel",
        "k1-component-rear-pod",
        "k1-component-front-door",
        "k1-plate-tray",
        "k1-plate-door",
    ):
        _write(view_root / f"{concept_id}_{view_id}.step")
    _write(cad_root / f"{concept_id}.step", "combined")
    _write(cad_root / f"{concept_id}.stl", "combined")

    render_path = fusion_root / "renders" / f"fusion-test-{concept_id}__k1-component-rear-panel.png"
    render_path.parent.mkdir(parents=True, exist_ok=True)
    render_path.write_bytes(b"\x89PNG\r\n\x1a\nfixture")

    manifest_path = cad_root / "manifest.json"
    _write_json(
        manifest_path,
        {
            "schema": "cbbs-cad/generated-manifest/v1",
            "output_dir": str(cad_root),
            "artifacts": [
                {
                    "concept_id": concept_id,
                    "name": "P070 fixture",
                    "truth_state": "internal review",
                    "measurement_status": "measurement-required",
                    "files": {
                        "step": str(cad_root / f"{concept_id}.step"),
                        "stl": str(cad_root / f"{concept_id}.stl"),
                    },
                    "bounds_mm": {"x": 220.0, "y": 220.0, "z": 130.0},
                    "assembly": {
                        "schema": "cbbs-cad/generated-assembly/v1",
                        "parts": [
                            {
                                "id": "rear_tray",
                                "name": "Rear tray",
                                "role": "assembly-reference",
                                "files": {
                                    "step": str(part_root / "rear_tray.step"),
                                    "stl": str(part_root / "rear_tray.stl"),
                                },
                                "bounds_mm": {"x": 206.2, "y": 143.6, "z": 126.4},
                            },
                            {
                                "id": "rear_panel_core",
                                "name": "Rear panel core",
                                "role": "print",
                                "files": {
                                    "step": str(part_root / "rear_panel_core.step"),
                                    "stl": str(part_root / "rear_panel_core.stl"),
                                },
                                "bounds_mm": {"x": 206.2, "y": 143.6, "z": 36.2},
                            },
                            {
                                "id": "rear_battery_pod",
                                "name": "Rear battery pod",
                                "role": "print",
                                "files": {
                                    "step": str(part_root / "rear_battery_pod.step"),
                                    "stl": str(part_root / "rear_battery_pod.stl"),
                                },
                                "bounds_mm": {"x": 158.0, "y": 154.0, "z": 97.2},
                            },
                            {
                                "id": "front_display_door",
                                "name": "Front door",
                                "role": "print",
                                "files": {
                                    "step": str(part_root / "front_display_door.step"),
                                    "stl": str(part_root / "front_display_door.stl"),
                                },
                                "bounds_mm": {"x": 206.2, "y": 124.4, "z": 8.8},
                            },
                        ],
                        "views": {
                            "k1-component-rear-panel": {
                                "file": str(
                                    view_root / f"{concept_id}_k1-component-rear-panel.step"
                                ),
                                "bounds_mm": {"x": 206.2, "y": 143.6, "z": 36.2},
                            },
                            "k1-component-rear-pod": {
                                "file": str(
                                    view_root / f"{concept_id}_k1-component-rear-pod.step"
                                ),
                                "bounds_mm": {"x": 158.0, "y": 154.0, "z": 97.2},
                            },
                            "k1-component-front-door": {
                                "file": str(
                                    view_root / f"{concept_id}_k1-component-front-door.step"
                                ),
                                "bounds_mm": {"x": 206.2, "y": 124.4, "z": 8.8},
                            },
                            "k1-plate-tray": {
                                "file": str(view_root / f"{concept_id}_k1-plate-tray.step"),
                                "bounds_mm": {"x": 206.2, "y": 143.6, "z": 126.4},
                            },
                            "k1-plate-door": {
                                "file": str(view_root / f"{concept_id}_k1-plate-door.step"),
                                "bounds_mm": {"x": 206.2, "y": 124.4, "z": 8.8},
                            },
                        },
                        "metadata": {
                            "print_layouts": {
                                "k1-component-rear-panel": {
                                    "parts": ["rear_panel_core"],
                                    "accepted": True,
                                    "fits_with_6mm_brim": True,
                                    "orientation": "rear panel back on build plate",
                                },
                                "k1-component-rear-pod": {
                                    "parts": ["rear_battery_pod"],
                                    "accepted": True,
                                    "fits_with_6mm_brim": True,
                                    "orientation": "pod floor on build plate",
                                },
                                "k1-component-front-door": {
                                    "parts": ["front_display_door"],
                                    "accepted": True,
                                    "fits_with_6mm_brim": True,
                                    "orientation": "front face up",
                                },
                                "k1-plate-tray": {
                                    "parts": ["rear_tray"],
                                    "accepted": False,
                                    "fits_with_6mm_brim": True,
                                    "orientation": "blocked",
                                },
                                "k1-plate-door": {
                                    "parts": ["front_display_door"],
                                    "accepted": False,
                                    "fits_with_6mm_brim": True,
                                    "orientation": "use k1-component-front-door",
                                },
                                "k1-combined": {
                                    "parts": ["rear_tray", "front_display_door"],
                                    "accepted": False,
                                    "fits_with_6mm_brim": False,
                                },
                            }
                        },
                    },
                }
            ],
        },
    )
    summary_path = fusion_root / "run-summary.json"
    _write_json(
        summary_path,
        {
            "schema": "cbbs-cad/fusion-run-summary/v1",
            "run_id": "fusion-test",
            "renders": [
                {
                    "view": f"{concept_id}__k1-component-rear-panel",
                    "path": str(render_path),
                    "status": "completed",
                }
            ],
        },
    )
    return manifest_path, summary_path


def test_default_printer_specs_validate() -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)

    assert {printer.id for printer in bundle.printers} >= {
        "creality_k1_modified_asa",
        "anycubic_kobra2_max",
        "creality_cr30_belt",
    }


def test_printer_requires_dimension_evidence() -> None:
    with pytest.raises(ValidationError, match="dimension_sources"):
        PrinterSpec.model_validate(
            {
                "schema": "cbbs-cad/printer/v1",
                "id": "bad_printer",
                "name": "Bad printer",
                "units": "mm",
                "truth_state": "internal review",
                "measurement_status": "source-derived",
                "open_measurement_blockers": ["measure printer"],
                "source_refs": [{"id": "source", "title": "Source", "path": "docs/source.md"}],
                "printer_type": "corexy-enclosed",
                "build_volume_kind": "fixed",
                "dimensions": {"build_x_mm": 220.0, "build_y_mm": 220.0, "build_z_mm": 250.0},
                "material_policies": [{"material": "PLA", "status": "fallback"}],
            }
        )


def test_printer_material_policy_rejects_blocked_asa_fallback() -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)
    printer = printer_by_id(bundle, "anycubic_kobra2_max")

    with pytest.raises(ValueError, match="blocked"):
        validate_material_for_printer(printer, "ASA")

    policy = validate_material_for_printer(printer, "ASA", allow_blocked=True)
    assert policy.status == "blocked"


def test_cr30_is_blocked_by_unresolved_geometry_conflict() -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)
    printer = printer_by_id(bundle, "creality_cr30_belt")

    with pytest.raises(ValueError, match="unresolved geometry source conflict"):
        validate_printer_for_package(printer, allow_blocked=True)


def test_print_package_emits_readme_manifest_checksums_and_split_k1_files(tmp_path) -> None:
    manifest_path, summary_path = _fake_p070_manifest(tmp_path)
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)

    package = create_print_package(
        generated_manifest_path=manifest_path,
        fusion_summary_path=summary_path,
        bundle=bundle,
        run_id="print-test",
        output_root=tmp_path / "packages",
    )
    output_dir = Path(package["output_dir"])

    assert (output_dir / "README.md").is_file()
    assert (output_dir / "guides" / "creality_k1_modified_asa.md").is_file()
    assert (output_dir / "print-manifest.json").is_file()
    assert (output_dir / "checksums.sha256").is_file()
    assert (output_dir / "print-log-template.md").is_file()
    assert not (output_dir / "files" / "parts" / "rear_tray.stl").exists()
    assert (output_dir / "files" / "parts" / "rear_panel_core.stl").is_file()
    assert (output_dir / "files" / "parts" / "rear_battery_pod.stl").is_file()
    assert (output_dir / "files" / "parts" / "front_display_door.stl").is_file()
    assert (output_dir / "files" / "plates" / "k1-component-rear-panel.step").is_file()
    assert package["no_gcode"] is True
    assert {plate["id"] for plate in package["plates"]} == {
        "k1-component-rear-panel",
        "k1-component-rear-pod",
        "k1-component-front-door",
    }
    assert {layout["id"] for layout in package["rejected_layouts"]} >= {
        "k1-plate-tray",
        "k1-combined",
    }
    assert package["renders"]
    assert not (output_dir / "files" / "parts" / f"{DEFAULT_PRINT_CONCEPT_ID}.stl").exists()


def test_print_package_includes_native_fusion_assembly_docs_when_present(tmp_path) -> None:
    manifest_path, summary_path = _fake_p070_manifest(tmp_path)
    docs_root = tmp_path / "fusion-docs"
    archive = docs_root / "p070-native-assembly.f3d"
    video = docs_root / "p070-component-print-disassembly.mp4"
    drawing = docs_root / "p070-assembly-packet.pdf"
    screenshot = docs_root / "storyboard-callouts.png"
    for path in (archive, video, drawing, screenshot):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"fixture")
    docs_manifest = docs_root / "storyboard-manifest.json"
    _write_json(
        docs_manifest,
        {
            "schema": "cbbs-cad/fusion-assembly-docs/v1",
            "concept_id": DEFAULT_PRINT_CONCEPT_ID,
            "run_id": "assembly-docs-test",
            "output_dir": str(docs_root),
            "archive": {"path": str(archive)},
            "storyboards": [
                {
                    "id": "component-print-disassembly",
                    "name": "P070 component print disassembly",
                    "video": str(video),
                    "screenshot": str(screenshot),
                }
            ],
            "drawings": [
                {
                    "id": "assembly-packet",
                    "name": "P070 assembly packet",
                    "path": str(drawing),
                }
            ],
            "screenshots": [],
        },
    )
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)

    package = create_print_package(
        generated_manifest_path=manifest_path,
        fusion_summary_path=summary_path,
        bundle=bundle,
        run_id="print-test-docs",
        output_root=tmp_path / "packages",
        assembly_docs_path=docs_manifest,
    )
    output_dir = Path(package["output_dir"])

    assert {item["kind"] for item in package["assembly_docs"]} >= {
        "storyboard-manifest",
        "fusion-archive",
        "storyboard-video",
        "storyboard-screenshot",
        "drawing",
    }
    assert (output_dir / "assembly-docs" / "storyboard-manifest.json").is_file()
    assert (output_dir / "assembly-docs" / archive.name).is_file()
    assert (output_dir / "assembly-docs" / video.name).is_file()
    assert (output_dir / "assembly-docs" / drawing.name).is_file()
    readme = (output_dir / "README.md").read_text(encoding="utf-8")
    assert "Native Fusion assembly documentation files" in readme
    assert "storyboard-manifest.json" in readme
