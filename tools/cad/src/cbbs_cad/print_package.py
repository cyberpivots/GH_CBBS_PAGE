from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cbbs_cad.fusion_workflow import localize_path
from cbbs_cad.models import MaterialPolicy, PrinterSpec, SpecBundle
from cbbs_cad.specs import REPO_ROOT

DEFAULT_PRINT_PACKAGE_ROOT = REPO_ROOT / "3d-print-work" / "generated" / "print-packages"
DEFAULT_FUSION_SUMMARY = REPO_ROOT / "3d-print-work" / "generated" / "fusion" / "run-summary.json"
DEFAULT_ASSEMBLY_DOC_ROOT = REPO_ROOT / "3d-print-work" / "generated" / "fusion" / "assembly-documentation"
DEFAULT_PRINT_CONCEPT_ID = "p070_heltec_outdoor_controller_enclosure"
DEFAULT_PRINT_PRINTER_ID = "creality_k1_modified_asa"
DEFAULT_PRINT_MATERIAL = "ASA"
GCODE_SUFFIXES = {".gcode", ".gco", ".gc", ".gx"}


def new_print_run_id() -> str:
    return f"print-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"


def _load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return data


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def printer_by_id(bundle: SpecBundle, printer_id: str) -> PrinterSpec:
    for printer in bundle.printers:
        if printer.id == printer_id:
            return printer
    raise ValueError(f"unknown printer id: {printer_id}")


def material_policy_for_printer(printer: PrinterSpec, material: str) -> MaterialPolicy:
    normalized = material.strip().upper()
    for policy in printer.material_policies:
        if policy.material == normalized:
            return policy
    raise ValueError(f"printer {printer.id} has no material policy for {normalized}")


def validate_material_for_printer(
    printer: PrinterSpec,
    material: str,
    *,
    allow_experimental: bool = False,
    allow_blocked: bool = False,
) -> MaterialPolicy:
    policy = material_policy_for_printer(printer, material)
    if policy.status == "experimental" and not (allow_experimental or allow_blocked):
        raise ValueError(
            f"printer {printer.id} material {policy.material} is experimental; "
            "rerun with explicit experimental/blocked approval"
        )
    if policy.status == "blocked" and not allow_blocked:
        raise ValueError(
            f"printer {printer.id} material {policy.material} is blocked; "
            "rerun only with explicit blocked review approval"
        )
    return policy


def validate_printer_for_package(
    printer: PrinterSpec,
    *,
    allow_blocked: bool = False,
) -> None:
    unresolved = [
        conflict.id
        for conflict in printer.source_conflicts
        if conflict.affects_geometry and not conflict.resolved
    ]
    if unresolved:
        raise ValueError(
            f"printer {printer.id} has unresolved geometry source conflict(s): "
            + ", ".join(unresolved)
        )
    if (
        printer.measurement_status == "blocked" or printer.build_volume_kind == "blocked"
    ) and not allow_blocked:
        raise ValueError(f"printer {printer.id} is blocked for package generation")


def _artifact_by_concept(manifest: dict[str, Any], concept_id: str) -> dict[str, Any]:
    for artifact in manifest.get("artifacts", []):
        if artifact.get("concept_id") == concept_id:
            return artifact
    raise ValueError(f"generated manifest does not contain concept: {concept_id}")


def _manifest_output_dir(manifest: dict[str, Any], manifest_path: Path) -> Path | None:
    raw = manifest.get("output_dir")
    if not raw:
        return None
    path = localize_path(raw)
    return path if path.is_absolute() else REPO_ROOT / path


def _resolve_manifest_path(
    raw: str | Path,
    manifest_path: Path,
    manifest: dict[str, Any],
) -> Path:
    path = localize_path(raw)
    if path.is_absolute():
        return path

    candidates = [REPO_ROOT / path, manifest_path.parent / path]
    output_dir = _manifest_output_dir(manifest, manifest_path)
    if output_dir:
        candidates.append(output_dir / path.name)

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _safe_copy(source: Path, destination: Path) -> None:
    if source.suffix.lower() in GCODE_SUFFIXES:
        raise ValueError(f"G-code files are not allowed in print packages: {source}")
    if not source.is_file():
        raise FileNotFoundError(f"package source file does not exist: {source}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _print_parts(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    assembly = artifact.get("assembly", {})
    if not isinstance(assembly, dict):
        return []
    return [
        part
        for part in assembly.get("parts", [])
        if isinstance(part, dict) and part.get("role") == "print"
    ]


def _part_by_id(parts: list[dict[str, Any]], part_id: str) -> dict[str, Any]:
    for part in parts:
        if part.get("id") == part_id:
            return part
    raise ValueError(f"generated assembly missing print part: {part_id}")


def _printer_build_volume(printer: PrinterSpec) -> dict[str, float]:
    return {
        "x": printer.dimensions.get("build_x_mm", 0.0),
        "y": printer.dimensions.get("build_y_mm", 0.0),
        "z": printer.dimensions.get("build_z_mm", 0.0),
    }


def _part_fits_printer(part: dict[str, Any], printer: PrinterSpec, brim_margin: float) -> bool:
    bounds = part.get("bounds_mm", {})
    volume = _printer_build_volume(printer)
    if not all(axis in bounds for axis in ("x", "y", "z")):
        return False
    return (
        bounds["x"] + brim_margin * 2 <= volume["x"]
        and bounds["y"] + brim_margin * 2 <= volume["y"]
        and bounds["z"] <= volume["z"]
    )


def _select_plate_plan(
    artifact: dict[str, Any],
    printer: PrinterSpec,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    assembly = artifact.get("assembly", {})
    metadata = assembly.get("metadata", {}) if isinstance(assembly, dict) else {}
    layouts = metadata.get("print_layouts", {}) if isinstance(metadata, dict) else {}
    parts = _print_parts(artifact)
    rejected: list[dict[str, Any]] = []

    if not parts:
        bounds = artifact.get("bounds_mm", {})
        if not bounds:
            raise ValueError(f"artifact {artifact.get('concept_id')} has no print bounds")
        return (
            [
                {
                    "id": "single-model",
                    "parts": [artifact.get("concept_id")],
                    "bounds_mm": bounds,
                    "orientation": "manual slicer review required",
                    "accepted": True,
                }
            ],
            [
                {
                    "id": artifact.get("concept_id"),
                    "name": artifact.get("name"),
                    "role": "print",
                    "files": artifact.get("files", {}),
                    "bounds_mm": bounds,
                }
            ],
            rejected,
        )

    if (
        printer.id == DEFAULT_PRINT_PRINTER_ID
        and artifact.get("concept_id") == DEFAULT_PRINT_CONCEPT_ID
    ):
        component_layouts = [
            "k1-component-rear-panel",
            "k1-component-rear-pod",
            "k1-component-front-door",
        ]
        legacy_layouts = ["k1-plate-tray", "k1-plate-door"]
        required_layouts = (
            component_layouts
            if all(layout_id in layouts for layout_id in component_layouts)
            else legacy_layouts
        )
        selected_plates = []
        selected_parts = []
        for layout_id in required_layouts:
            layout = layouts.get(layout_id)
            if not isinstance(layout, dict) or not layout.get("accepted", layout.get("fits_with_6mm_brim")):
                raise ValueError(f"K1 P070 package requires accepted component layout: {layout_id}")
            part_ids = layout.get("parts", [])
            for part_id in part_ids:
                selected_parts.append(_part_by_id(parts, part_id))
            selected_plates.append({"id": layout_id, **layout})

        for layout_id in (
            "k1-plate-tray",
            "k1-plate-door",
            "k1-combined",
            "k1-max-combined",
            "k1-monolithic-rear-tray",
        ):
            if layout_id in required_layouts:
                continue
            layout = layouts.get(layout_id)
            if isinstance(layout, dict):
                rejected.append({"id": layout_id, **layout})
                if layout_id in {"k1-plate-tray", "k1-combined", "k1-max-combined"} and layout.get(
                    "accepted"
                ):
                    raise ValueError(f"K1 P070 legacy/single-piece layout must remain rejected: {layout_id}")
        return selected_plates, selected_parts, rejected

    brim_margin = 6.0
    selected_plates = []
    for part in parts:
        accepted = _part_fits_printer(part, printer, brim_margin)
        selected_plates.append(
            {
                "id": f"single-part-{part['id']}",
                "parts": [part["id"]],
                "bounds_mm": part.get("bounds_mm", {}),
                "brim_margin_each_side_mm": brim_margin,
                "accepted": accepted,
                "orientation": "manual slicer review required",
            }
        )
        if not accepted:
            raise ValueError(
                f"part {part['id']} does not fit printer {printer.id} with {brim_margin} mm brim"
            )
    return selected_plates, parts, rejected


def _copy_part_files(
    *,
    parts: list[dict[str, Any]],
    output_dir: Path,
    manifest_path: Path,
    generated_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    for part in parts:
        files = part.get("files", {})
        if not isinstance(files, dict):
            continue
        for kind, raw_path in sorted(files.items()):
            if not raw_path:
                continue
            source = _resolve_manifest_path(raw_path, manifest_path, generated_manifest)
            destination = output_dir / "files" / "parts" / f"{part['id']}.{kind}"
            _safe_copy(source, destination)
            copied.append(
                {
                    "kind": "part",
                    "part_id": part["id"],
                    "format": kind,
                    "source": str(source),
                    "path": _relative(destination, output_dir),
                    "bounds_mm": part.get("bounds_mm", {}),
                }
            )
    return copied


def _copy_plate_views(
    *,
    plates: list[dict[str, Any]],
    artifact: dict[str, Any],
    output_dir: Path,
    manifest_path: Path,
    generated_manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    assembly = artifact.get("assembly", {})
    views = assembly.get("views", {}) if isinstance(assembly, dict) else {}
    copied: list[dict[str, Any]] = []
    for plate in plates:
        view = views.get(plate["id"]) if isinstance(views, dict) else None
        if not isinstance(view, dict) or not view.get("file"):
            continue
        source = _resolve_manifest_path(view["file"], manifest_path, generated_manifest)
        destination = output_dir / "files" / "plates" / f"{plate['id']}.step"
        _safe_copy(source, destination)
        copied.append(
            {
                "kind": "plate-view",
                "plate_id": plate["id"],
                "format": "step",
                "source": str(source),
                "path": _relative(destination, output_dir),
                "bounds_mm": view.get("bounds_mm", {}),
            }
        )
    return copied


def _render_candidates_from_summary(
    fusion_summary_path: Path,
    concept_id: str,
    preferred_suffixes: list[str],
) -> list[Path]:
    if not fusion_summary_path.is_file():
        return []
    summary = _load_json(fusion_summary_path)
    preferred_views = {f"{concept_id}__{suffix}" for suffix in preferred_suffixes}
    candidates: list[Path] = []
    for render in summary.get("renders", []):
        if not isinstance(render, dict):
            continue
        view = render.get("view")
        raw_path = render.get("path")
        if view not in preferred_views or not raw_path:
            continue
        path = localize_path(raw_path)
        candidates.append(path)
    return candidates


def _render_candidates_by_glob(concept_id: str, preferred_suffixes: list[str]) -> list[Path]:
    render_root = REPO_ROOT / "3d-print-work" / "generated" / "fusion" / "renders"
    candidates: list[Path] = []
    for suffix in preferred_suffixes:
        candidates.extend(sorted(render_root.glob(f"*-{concept_id}__{suffix}.png")))
    return candidates


def _copy_renders(
    *,
    concept_id: str,
    fusion_summary_path: Path,
    output_dir: Path,
    preferred_suffixes: list[str],
) -> list[dict[str, Any]]:
    seen: set[Path] = set()
    candidates = _render_candidates_from_summary(
        fusion_summary_path,
        concept_id,
        preferred_suffixes,
    )
    if not candidates:
        candidates = _render_candidates_by_glob(concept_id, preferred_suffixes)
    copied: list[dict[str, Any]] = []
    for source in candidates:
        source = source.resolve()
        if source in seen or not source.is_file():
            continue
        seen.add(source)
        destination = output_dir / "renders" / source.name
        _safe_copy(source, destination)
        copied.append(
            {
                "kind": "fusion-render",
                "source": str(source),
                "path": _relative(destination, output_dir),
            }
        )
    return copied


def _manifest_concept_matches(path: Path, concept_id: str) -> bool:
    try:
        manifest = _load_json(path)
    except (OSError, json.JSONDecodeError, ValueError):
        return False
    return manifest.get("concept_id") == concept_id


def _assembly_docs_manifest_path(
    concept_id: str,
    assembly_docs_path: Path | None,
) -> Path | None:
    if assembly_docs_path:
        path = assembly_docs_path / "storyboard-manifest.json" if assembly_docs_path.is_dir() else assembly_docs_path
        if not path.is_file():
            raise FileNotFoundError(f"assembly documentation manifest does not exist: {path}")
        if not _manifest_concept_matches(path, concept_id):
            raise ValueError(f"assembly documentation manifest does not match concept: {concept_id}")
        return path

    candidates = [
        path
        for path in DEFAULT_ASSEMBLY_DOC_ROOT.glob("*/storyboard-manifest.json")
        if _manifest_concept_matches(path, concept_id)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _resolve_assembly_doc_path(raw: str | Path, manifest_path: Path, manifest: dict[str, Any]) -> Path:
    path = localize_path(raw)
    if path.is_absolute():
        return path
    raw_output_dir = manifest.get("output_dir")
    if raw_output_dir:
        output_dir = localize_path(raw_output_dir)
        if not output_dir.is_absolute():
            output_dir = manifest_path.parent / output_dir
        candidate = output_dir / path
        if candidate.exists():
            return candidate
    return manifest_path.parent / path


def _assembly_doc_manifest_entries(
    manifest_path: Path,
    manifest: dict[str, Any],
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = [
        {
            "kind": "storyboard-manifest",
            "source": manifest_path,
            "destination_name": "storyboard-manifest.json",
        }
    ]

    archive = manifest.get("archive")
    if isinstance(archive, dict) and archive.get("path"):
        entries.append(
            {
                "kind": "fusion-archive",
                "source": _resolve_assembly_doc_path(archive["path"], manifest_path, manifest),
                "destination_name": Path(str(archive["path"])).name,
            }
        )

    for storyboard in manifest.get("storyboards", []):
        if not isinstance(storyboard, dict):
            continue
        for field, kind in (("video", "storyboard-video"), ("screenshot", "storyboard-screenshot")):
            raw = storyboard.get(field)
            if raw:
                entries.append(
                    {
                        "kind": kind,
                        "storyboard_id": storyboard.get("id"),
                        "source": _resolve_assembly_doc_path(raw, manifest_path, manifest),
                        "destination_name": Path(str(raw)).name,
                    }
                )

    for drawing in manifest.get("drawings", []):
        if not isinstance(drawing, dict):
            continue
        raw = drawing.get("path")
        if raw:
            entries.append(
                {
                    "kind": "drawing",
                    "drawing_id": drawing.get("id"),
                    "source": _resolve_assembly_doc_path(raw, manifest_path, manifest),
                    "destination_name": Path(str(raw)).name,
                }
            )

    for screenshot in manifest.get("screenshots", []):
        if not isinstance(screenshot, dict):
            continue
        raw = screenshot.get("path")
        if raw:
            entries.append(
                {
                    "kind": "verification-screenshot",
                    "screenshot_id": screenshot.get("id"),
                    "source": _resolve_assembly_doc_path(raw, manifest_path, manifest),
                    "destination_name": Path(str(raw)).name,
                }
            )
    return entries


def _copy_assembly_docs(
    *,
    concept_id: str,
    output_dir: Path,
    assembly_docs_path: Path | None,
) -> list[dict[str, Any]]:
    manifest_path = _assembly_docs_manifest_path(concept_id, assembly_docs_path)
    if manifest_path is None:
        return []
    manifest = _load_json(manifest_path)
    if manifest.get("schema") != "cbbs-cad/fusion-assembly-docs/v1":
        raise ValueError(f"unsupported assembly documentation manifest schema: {manifest_path}")
    copied: list[dict[str, Any]] = []
    used_names: set[str] = set()
    for entry in _assembly_doc_manifest_entries(manifest_path, manifest):
        source = Path(entry.pop("source"))
        if not source.is_file():
            raise FileNotFoundError(f"assembly documentation file does not exist: {source}")
        destination_name = str(entry.pop("destination_name"))
        if destination_name in used_names:
            stem = Path(destination_name).stem
            suffix = Path(destination_name).suffix
            destination_name = f"{stem}-{len(used_names)}{suffix}"
        used_names.add(destination_name)
        destination = output_dir / "assembly-docs" / destination_name
        _safe_copy(source, destination)
        copied.append(
            {
                **entry,
                "source": str(source),
                "path": _relative(destination, output_dir),
            }
        )
    return copied


def _readme_text(
    *,
    run_id: str,
    concept_id: str,
    printer: PrinterSpec,
    material_policy: MaterialPolicy,
    plates: list[dict[str, Any]],
    rejected_layouts: list[dict[str, Any]],
    assembly_docs: list[dict[str, Any]],
) -> str:
    lines = [
        f"# CBBS 3D Print Package: {concept_id}",
        "",
        "Truth state: `internal review`",
        f"Run ID: `{run_id}`",
        f"Printer: `{printer.id}`",
        f"Material: `{material_policy.material}` ({material_policy.status})",
        "",
        "This package is local review output. It is not a public download, release asset, or print-success claim.",
        "",
        "## Package Rules",
        "",
        "- STL/STEP only; no G-code is generated or included.",
        "- Open the files in the printer-specific guide before slicing.",
        "- Validate material, bed adhesion, chamber behavior, ventilation, and first-layer setup on the physical printer.",
        "- Keep notes in `print-log-template.md` during the run.",
        "",
        "## Plates",
        "",
    ]
    for plate in plates:
        lines.append(
            f"- `{plate['id']}`: parts {', '.join(plate.get('parts', []))}; "
            f"accepted: {str(bool(plate.get('accepted', False))).lower()}"
        )
        if plate.get("orientation"):
            lines.append(f"  Orientation: {plate['orientation']}")

    if rejected_layouts:
        lines.extend(["", "## Rejected Layouts", ""])
        for layout in rejected_layouts:
            lines.append(
                f"- `{layout['id']}`: accepted "
                f"{str(bool(layout.get('accepted', False))).lower()}; "
                f"fits with brim: {str(bool(layout.get('fits_with_6mm_brim', False))).lower()}"
            )
    if assembly_docs:
        lines.extend(["", "## Assembly Documentation", ""])
        lines.append("- Native Fusion assembly documentation files are in `assembly-docs/`.")
        lines.append("- Check `assembly-docs/storyboard-manifest.json` for storyboard and drawing status.")
        lines.append("- Use these as local review references only; they are not public release assets.")
    return "\n".join(lines) + "\n"


def _printer_guide_text(printer: PrinterSpec, material_policy: MaterialPolicy) -> str:
    lines = [
        f"# {printer.name}",
        "",
        "Truth state: `internal review`",
        "",
        "## Material Gate",
        "",
        f"- Selected material: `{material_policy.material}`",
        f"- Policy status: `{material_policy.status}`",
    ]
    if material_policy.notes:
        lines.append(f"- Notes: {material_policy.notes}")

    lines.extend(["", "## Slicer Guidance", ""])
    lines.extend(f"- {item}" for item in printer.slicer_guidance)
    lines.extend(["", "## Process Notes", ""])
    lines.extend(f"- {item}" for item in printer.process_notes)

    if printer.id == DEFAULT_PRINT_PRINTER_ID:
        lines.extend(
            [
                "",
                "## K1 P070 Plate Order",
                "",
                "1. Slice `files/parts/rear_panel_core.stl` as its own K1 plate.",
                "2. Slice `files/parts/rear_battery_pod.stl` as its own K1 plate.",
                "3. Slice `files/parts/front_display_door.stl` as its own K1 plate.",
                "4. Do not print the rear panel and rear pod as one piece.",
                "5. Do not combine components on the 220 x 220 mm K1 plate.",
                "6. Keep any camera monitoring read-only until local endpoints are verified.",
            ]
        )
    return "\n".join(lines) + "\n"


def _print_log_template() -> str:
    return """# CBBS Print Log

Truth state: `internal review`

## Setup

- Printer:
- Material / brand / color:
- Nozzle:
- Plate:
- Slicer and profile:
- Chamber / ventilation notes:

## Preflight

- Files sliced:
- Bed adhesion plan:
- Supports:
- Brim/skirt:
- First-layer observation:

## Result

- Status:
- Issues:
- Fit observations:
- Next action:
"""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_checksums(output_dir: Path) -> Path:
    checksum_path = output_dir / "checksums.sha256"
    records = []
    for path in sorted(output_dir.rglob("*")):
        if path.is_file() and path != checksum_path:
            records.append(f"{_sha256(path)}  {_relative(path, output_dir)}")
    checksum_path.write_text("\n".join(records) + "\n", encoding="utf-8")
    return checksum_path


def create_print_package(
    *,
    generated_manifest_path: Path,
    fusion_summary_path: Path = DEFAULT_FUSION_SUMMARY,
    concept_id: str = DEFAULT_PRINT_CONCEPT_ID,
    printer_id: str = DEFAULT_PRINT_PRINTER_ID,
    run_id: str | None = None,
    bundle: SpecBundle,
    material: str = DEFAULT_PRINT_MATERIAL,
    output_root: Path = DEFAULT_PRINT_PACKAGE_ROOT,
    assembly_docs_path: Path | None = None,
    allow_experimental: bool = False,
    allow_blocked: bool = False,
) -> dict[str, Any]:
    generated_manifest = _load_json(generated_manifest_path)
    artifact = _artifact_by_concept(generated_manifest, concept_id)
    printer = printer_by_id(bundle, printer_id)
    validate_printer_for_package(printer, allow_blocked=allow_blocked)
    material_policy = validate_material_for_printer(
        printer,
        material,
        allow_experimental=allow_experimental,
        allow_blocked=allow_blocked,
    )

    selected_plates, selected_parts, rejected_layouts = _select_plate_plan(artifact, printer)
    actual_run_id = run_id or new_print_run_id()
    output_dir = output_root / actual_run_id / concept_id / printer_id
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    files = []
    files.extend(
        _copy_part_files(
            parts=selected_parts,
            output_dir=output_dir,
            manifest_path=generated_manifest_path,
            generated_manifest=generated_manifest,
        )
    )
    files.extend(
        _copy_plate_views(
            plates=selected_plates,
            artifact=artifact,
            output_dir=output_dir,
            manifest_path=generated_manifest_path,
            generated_manifest=generated_manifest,
        )
    )
    render_suffixes = [
        "k1-component-rear-panel",
        "k1-component-rear-pod",
        "k1-component-front-door",
        "closed-isometric",
        "closed-front",
        "model",
    ]
    renders = _copy_renders(
        concept_id=concept_id,
        fusion_summary_path=fusion_summary_path,
        output_dir=output_dir,
        preferred_suffixes=render_suffixes,
    )
    assembly_docs = _copy_assembly_docs(
        concept_id=concept_id,
        output_dir=output_dir,
        assembly_docs_path=assembly_docs_path,
    )

    guide_path = output_dir / "guides" / f"{printer_id}.md"
    guide_path.parent.mkdir(parents=True, exist_ok=True)
    guide_path.write_text(_printer_guide_text(printer, material_policy), encoding="utf-8")
    readme_path = output_dir / "README.md"
    readme_path.write_text(
        _readme_text(
            run_id=actual_run_id,
            concept_id=concept_id,
            printer=printer,
            material_policy=material_policy,
            plates=selected_plates,
            rejected_layouts=rejected_layouts,
            assembly_docs=assembly_docs,
        ),
        encoding="utf-8",
    )
    log_template_path = output_dir / "print-log-template.md"
    log_template_path.write_text(_print_log_template(), encoding="utf-8")

    manifest_payload = {
        "schema": "cbbs-cad/print-package/v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "truth_state": "internal review",
        "run_id": actual_run_id,
        "concept_id": concept_id,
        "printer_id": printer_id,
        "material": material_policy.material,
        "material_policy": material_policy.model_dump(mode="json"),
        "source_manifest": str(generated_manifest_path),
        "fusion_summary": str(fusion_summary_path),
        "output_dir": str(output_dir),
        "no_gcode": True,
        "plates": selected_plates,
        "rejected_layouts": rejected_layouts,
        "files": files,
        "renders": renders,
        "assembly_docs": assembly_docs,
        "guides": [_relative(guide_path, output_dir)],
        "log_template": _relative(log_template_path, output_dir),
        "readme": _relative(readme_path, output_dir),
    }
    manifest_path = output_dir / "print-manifest.json"
    _write_json(manifest_path, manifest_payload)
    checksum_path = _write_checksums(output_dir)
    manifest_payload["checksums"] = _relative(checksum_path, output_dir)
    _write_json(manifest_path, manifest_payload)
    _write_checksums(output_dir)
    return manifest_payload
