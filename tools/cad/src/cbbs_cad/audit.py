from __future__ import annotations

import re

from cbbs_cad.models import (
    ConceptSpec,
    HardwareSpec,
    ImageUse,
    MeasurementStatus,
    PrinterSpec,
    SpecBase,
    SpecBundle,
    ToolingCandidateSpec,
    ToolingDependencyPolicy,
    ToolingRecommendation,
    ToolingRepoStatus,
    VerificationStatus,
)

RATING_CLAIM_PATTERN = re.compile(
    r"\b(ip\s*\d{2}|nema\s*(type\s*)?\d+[a-z]*|ik\s*\d{2}|"
    r"waterproof|dustproof|weatherproof|ip-rated|nema-rated|ik-rated)\b",
    re.IGNORECASE,
)


def _has_public_approval(item: SpecBase) -> bool:
    return any(source.status == "approved-public" for source in item.release_approval_refs)


def _audit_common(
    item: SpecBase,
    kind: str,
    *,
    allow_blocked_geometry_conflicts: bool = False,
) -> list[str]:
    failures: list[str] = []
    label = f"{kind} {item.id}"

    if item.public_release and not _has_public_approval(item):
        failures.append(f"{label}: public_release requires an approved release_approval_refs entry")

    if item.public_release:
        internal_refs = [source.id for source in item.source_refs if source.status != "approved-public"]
        if internal_refs:
            failures.append(f"{label}: public_release cannot use internal source_refs: {internal_refs}")

    for image in item.image_refs:
        if image.allowed_use == ImageUse.PUBLIC_APPROVED and not image.approval_ref:
            failures.append(
                f"{label}: image_ref {image.id} is public-approved without an approval_ref"
            )

    for conflict in item.source_conflicts:
        if conflict.affects_geometry and not conflict.resolved:
            if allow_blocked_geometry_conflicts and item.measurement_status == MeasurementStatus.BLOCKED:
                continue
            failures.append(f"{label}: unresolved geometry conflict {conflict.id}")

    return failures


def _audit_hardware(hardware: HardwareSpec) -> list[str]:
    failures = _audit_common(hardware, "hardware")

    if hardware.measurement_status == MeasurementStatus.BLOCKED and hardware.dimensions:
        failures.append(f"hardware {hardware.id}: blocked hardware must not carry dimensions")

    if hardware.measurement_status != MeasurementStatus.BLOCKED and not hardware.dimensions:
        failures.append(f"hardware {hardware.id}: non-blocked hardware requires dimensions")

    for name, evidence in hardware.dimension_sources.items():
        if evidence.verification_status == VerificationStatus.CONFLICT:
            failures.append(f"hardware {hardware.id}: dimension {name} has conflict evidence")
        if evidence.verification_status == VerificationStatus.BLOCKED:
            failures.append(f"hardware {hardware.id}: dimension {name} is blocked")
        if not evidence.locator.strip():
            failures.append(f"hardware {hardware.id}: dimension {name} lacks evidence locator")

    return failures


def _audit_concept(concept: ConceptSpec, hardware_by_id: dict[str, HardwareSpec]) -> list[str]:
    failures = _audit_common(concept, "concept")
    source_by_id = {source.id: source for source in concept.source_refs + concept.release_approval_refs}

    for name, evidence in concept.parameter_sources.items():
        if evidence.verification_status == VerificationStatus.CONFLICT:
            failures.append(f"concept {concept.id}: parameter {name} has conflict evidence")
        if evidence.verification_status == VerificationStatus.BLOCKED:
            failures.append(f"concept {concept.id}: parameter {name} is blocked")
        if not evidence.locator.strip():
            failures.append(f"concept {concept.id}: parameter {name} lacks evidence locator")

    if not concept.blocked_full_case:
        unmeasured = [
            hardware_id
            for hardware_id in concept.hardware_refs
            if hardware_by_id[hardware_id].measurement_status != MeasurementStatus.MEASURED
        ]
        if unmeasured:
            failures.append(
                f"concept {concept.id}: full enclosure generation requires measured hardware, "
                f"not {', '.join(unmeasured)}"
            )

    claim_text = " ".join(
        part
        for part in (
            concept.id,
            concept.name,
            concept.notes or "",
            " ".join(concept.open_measurement_blockers),
        )
        if part
    )
    if RATING_CLAIM_PATTERN.search(claim_text):
        failures.append(
            f"concept {concept.id}: environmental rating or protection claim appears in "
            "free text; use environmental_context.rating_claims with approved evidence instead"
        )

    if concept.environmental_context and concept.environmental_context.rating_claims:
        context = concept.environmental_context
        if not context.validation_plan:
            failures.append(
                f"concept {concept.id}: environmental rating claims require a validation_plan"
            )
        if not context.source_refs:
            failures.append(f"concept {concept.id}: environmental rating claims require source_refs")
        unapproved = [
            source_ref
            for source_ref in context.source_refs
            if source_by_id[source_ref].status != "approved-public"
        ]
        if unapproved:
            failures.append(
                f"concept {concept.id}: environmental rating claims require approved-public "
                f"source_refs, not {unapproved}"
            )
        if concept.measurement_status != MeasurementStatus.MEASURED:
            failures.append(
                f"concept {concept.id}: environmental rating claims require measured hardware"
            )
        if concept.blocked_full_case:
            failures.append(
                f"concept {concept.id}: environmental rating claims cannot be made on a "
                "blocked full-case concept"
            )

    return failures


def _audit_printer(printer: PrinterSpec) -> list[str]:
    failures = _audit_common(
        printer,
        "printer",
        allow_blocked_geometry_conflicts=True,
    )

    for name, evidence in printer.dimension_sources.items():
        if evidence.verification_status == VerificationStatus.CONFLICT:
            failures.append(f"printer {printer.id}: dimension {name} has conflict evidence")
        if evidence.verification_status == VerificationStatus.BLOCKED:
            failures.append(f"printer {printer.id}: dimension {name} is blocked")
        if not evidence.locator.strip():
            failures.append(f"printer {printer.id}: dimension {name} lacks evidence locator")

    return failures


def _audit_tooling(tooling: ToolingCandidateSpec) -> list[str]:
    failures: list[str] = []
    label = f"tooling {tooling.id}"

    if tooling.public_release:
        failures.append(f"{label}: tooling research records cannot be marked public_release")

    if tooling.public_claims_allowed:
        failures.append(f"{label}: tooling research cannot allow public product capability claims")

    if tooling.gcode_generation_allowed:
        failures.append(f"{label}: tooling research cannot allow G-code generation")

    if tooling.install_commands and tooling.recommendation != ToolingRecommendation.KEEP_BASELINE:
        failures.append(
            f"{label}: non-baseline tooling candidates must not include install commands"
        )

    if (
        tooling.current_repo_status == ToolingRepoStatus.TRANSITIVE_DEPENDENCY
        and tooling.direct_import_allowed
    ):
        failures.append(
            f"{label}: transitive dependencies are not approved direct import surfaces"
        )

    if (
        tooling.dependency_policy == ToolingDependencyPolicy.CURRENT_DIRECT
        and tooling.current_repo_status != ToolingRepoStatus.DIRECT_DEPENDENCY
    ):
        failures.append(f"{label}: current-direct policy requires a direct dependency")

    if (
        tooling.dependency_policy == ToolingDependencyPolicy.CURRENT_OPTIONAL
        and tooling.current_repo_status != ToolingRepoStatus.OPTIONAL_DEPENDENCY
    ):
        failures.append(f"{label}: current-optional policy requires an optional dependency")

    for index, evidence in enumerate(tooling.evidence_refs):
        if evidence.verification_status == VerificationStatus.CONFLICT:
            failures.append(f"{label}: evidence_ref {index} has conflict evidence")
        if evidence.verification_status == VerificationStatus.BLOCKED:
            failures.append(f"{label}: evidence_ref {index} is blocked")
        if not evidence.locator.strip():
            failures.append(f"{label}: evidence_ref {index} lacks evidence locator")

    return failures


def audit_bundle(bundle: SpecBundle) -> list[str]:
    hardware_by_id = {item.id: item for item in bundle.hardware}
    failures: list[str] = []

    for hardware in bundle.hardware:
        failures.extend(_audit_hardware(hardware))

    for concept in bundle.concepts:
        failures.extend(_audit_concept(concept, hardware_by_id))

    for printer in bundle.printers:
        failures.extend(_audit_printer(printer))

    for tooling in bundle.tooling:
        failures.extend(_audit_tooling(tooling))

    return failures
