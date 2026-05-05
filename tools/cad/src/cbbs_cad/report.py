from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cbbs_cad.models import ConceptSpec, SpecBundle
from cbbs_cad.specs import REPO_ROOT

DEFAULT_REPORT_DIR = REPO_ROOT / "3d-print-work" / "generated" / "evidence"


def _concepts_by_hardware(bundle: SpecBundle) -> dict[str, list[ConceptSpec]]:
    result: dict[str, list[ConceptSpec]] = {hardware.id: [] for hardware in bundle.hardware}
    for concept in bundle.concepts:
        for hardware_id in concept.hardware_refs:
            result.setdefault(hardware_id, []).append(concept)
    return result


def build_evidence_report(bundle: SpecBundle) -> dict[str, Any]:
    concepts_by_hardware = _concepts_by_hardware(bundle)

    hardware_records: list[dict[str, Any]] = []
    for hardware in bundle.hardware:
        hardware_records.append(
            {
                "id": hardware.id,
                "name": hardware.name,
                "truth_state": hardware.truth_state,
                "measurement_status": hardware.measurement_status,
                "derivation_state": hardware.derivation_state,
                "public_release": hardware.public_release,
                "dimensions": {
                    name: {
                        "value_mm": value,
                        "evidence": hardware.dimension_sources[name].model_dump(mode="json"),
                    }
                    for name, value in hardware.dimensions.items()
                },
                "source_refs": [source.model_dump(mode="json") for source in hardware.source_refs],
                "image_refs": [image.model_dump(mode="json") for image in hardware.image_refs],
                "source_conflicts": [
                    conflict.model_dump(mode="json") for conflict in hardware.source_conflicts
                ],
                "open_measurement_blockers": hardware.open_measurement_blockers,
                "allowed_model_outputs": [
                    {
                        "concept_id": concept.id,
                        "model_family": concept.model_family,
                        "outputs": concept.outputs,
                        "blocked_full_case": concept.blocked_full_case,
                    }
                    for concept in concepts_by_hardware.get(hardware.id, [])
                ],
            }
        )

    return {
        "schema": "cbbs-cad/evidence-report/v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "hardware": hardware_records,
        "printers": [
            {
                "id": printer.id,
                "name": printer.name,
                "truth_state": printer.truth_state,
                "measurement_status": printer.measurement_status,
                "public_release": printer.public_release,
                "printer_type": printer.printer_type,
                "build_volume_kind": printer.build_volume_kind,
                "dimensions": {
                    name: {
                        "value_mm": value,
                        "evidence": printer.dimension_sources[name].model_dump(mode="json"),
                    }
                    for name, value in printer.dimensions.items()
                },
                "default_material": printer.default_material,
                "material_policies": [
                    policy.model_dump(mode="json") for policy in printer.material_policies
                ],
                "source_refs": [source.model_dump(mode="json") for source in printer.source_refs],
                "source_conflicts": [
                    conflict.model_dump(mode="json") for conflict in printer.source_conflicts
                ],
                "open_measurement_blockers": printer.open_measurement_blockers,
            }
            for printer in bundle.printers
        ],
        "concepts": [
            {
                "id": concept.id,
                "name": concept.name,
                "model_family": concept.model_family,
                "hardware_refs": concept.hardware_refs,
                "truth_state": concept.truth_state,
                "measurement_status": concept.measurement_status,
                "public_release": concept.public_release,
                "blocked_full_case": concept.blocked_full_case,
                "environmental_context": (
                    concept.environmental_context.model_dump(mode="json")
                    if concept.environmental_context
                    else None
                ),
                "outputs": concept.outputs,
                "open_measurement_blockers": concept.open_measurement_blockers,
            }
            for concept in bundle.concepts
        ],
        "tooling": [
            {
                "id": tooling.id,
                "name": tooling.name,
                "truth_state": tooling.truth_state,
                "category": tooling.category,
                "current_repo_status": tooling.current_repo_status,
                "recommendation": tooling.recommendation,
                "dependency_policy": tooling.dependency_policy,
                "automation_safety": tooling.automation_safety,
                "public_release": tooling.public_release,
                "public_claims_allowed": tooling.public_claims_allowed,
                "gcode_generation_allowed": tooling.gcode_generation_allowed,
                "direct_import_allowed": tooling.direct_import_allowed,
                "source_refs": [source.model_dump(mode="json") for source in tooling.source_refs],
                "evidence_refs": [
                    evidence.model_dump(mode="json") for evidence in tooling.evidence_refs
                ],
                "integration_paths": tooling.integration_paths,
                "blockers": tooling.blockers,
                "blocked_claims": tooling.blocked_claims,
            }
            for tooling in bundle.tooling
        ],
    }


def _one_line(value: str) -> str:
    return " ".join(value.split())


def render_markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# CBBS Hardware Evidence Report",
        "",
        f"Generated: {report['created_at']}",
        "",
        "This report is local review output. Do not publish it without source review.",
        "",
        "## Hardware",
    ]

    for hardware in report["hardware"]:
        lines.extend(
            [
                "",
                f"### {hardware['name']}",
                "",
                f"- ID: `{hardware['id']}`",
                f"- Truth state: `{hardware['truth_state']}`",
                f"- Measurement status: `{hardware['measurement_status']}`",
                f"- Public release: `{str(hardware['public_release']).lower()}`",
            ]
        )

        if hardware["dimensions"]:
            lines.extend(["", "| Dimension | Value mm | Evidence |", "| --- | ---: | --- |"])
            for name, payload in hardware["dimensions"].items():
                evidence = payload["evidence"]
                lines.append(
                    f"| `{name}` | {payload['value_mm']} | "
                    f"{evidence['source_ref']} ({evidence['locator']}) |"
                )
        else:
            lines.extend(["", "No verified dimensions recorded."])

        if hardware["source_conflicts"]:
            lines.extend(["", "Conflicts:"])
            for conflict in hardware["source_conflicts"]:
                lines.append(
                    f"- `{conflict['id']}`: {_one_line(conflict['summary'])} "
                    f"(affects geometry: {conflict['affects_geometry']}, "
                    f"resolved: {conflict['resolved']})"
                )

        if hardware["image_refs"]:
            lines.extend(["", "Images:"])
            for image in hardware["image_refs"]:
                lines.append(
                    f"- `{image['id']}`: {image['title']} "
                    f"({image['allowed_use']}; {image['provenance']})"
                )

        if hardware["open_measurement_blockers"]:
            lines.extend(["", "Measurement blockers:"])
            lines.extend(f"- {blocker}" for blocker in hardware["open_measurement_blockers"])

        if hardware["allowed_model_outputs"]:
            lines.extend(["", "Allowed model outputs:"])
            for concept in hardware["allowed_model_outputs"]:
                lines.append(
                    f"- `{concept['concept_id']}`: {', '.join(concept['outputs'])}; "
                    f"blocked full case: {concept['blocked_full_case']}"
                )

    lines.extend(["", "## Concepts"])
    for concept in report["concepts"]:
        lines.append(
            f"- `{concept['id']}`: {concept['model_family']} "
            f"({', '.join(concept['outputs'])}); blocked full case: {concept['blocked_full_case']}"
        )
        if concept["environmental_context"]:
            context = concept["environmental_context"]
            lines.append(
                f"  Environmental context: {context['exposure']}; "
                f"ruggedization: {', '.join(context['ruggedization']) or 'none'}; "
                f"rating claims: {', '.join(context['rating_claims']) or 'none'}"
            )

    if report.get("printers"):
        lines.extend(["", "## Printers"])
        for printer in report["printers"]:
            lines.append(
                f"- `{printer['id']}`: {printer['printer_type']}; "
                f"build volume kind: {printer['build_volume_kind']}; "
                f"default material: {printer['default_material'] or 'none'}"
            )

    if report.get("tooling"):
        lines.extend(["", "## Tooling Candidates"])
        for tooling in report["tooling"]:
            lines.append(
                f"- `{tooling['id']}`: {tooling['category']}; "
                f"status: {tooling['current_repo_status']}; "
                f"recommendation: {tooling['recommendation']}; "
                f"dependency policy: {tooling['dependency_policy']}"
            )

    return "\n".join(lines) + "\n"


def write_evidence_report(bundle: SpecBundle, output_dir: Path = DEFAULT_REPORT_DIR) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    report = build_evidence_report(bundle)
    json_path = output_dir / "hardware-evidence-report.json"
    md_path = output_dir / "hardware-evidence-report.md"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown_report(report), encoding="utf-8")
    return {"json": json_path, "markdown": md_path}
