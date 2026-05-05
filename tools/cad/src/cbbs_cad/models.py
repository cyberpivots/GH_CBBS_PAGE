from __future__ import annotations

from enum import StrEnum
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class TruthState(StrEnum):
    CURRENT = "current"
    PROOF_SIMULATOR = "proof/simulator"
    MOCK_SCENARIO = "mock scenario"
    PROJECTED = "projected"
    INTERNAL_REVIEW = "internal review"


class MeasurementStatus(StrEnum):
    MEASURED = "measured"
    SOURCE_DERIVED = "source-derived"
    MEASUREMENT_REQUIRED = "measurement-required"
    BLOCKED = "blocked"


class EvidenceType(StrEnum):
    OFFICIAL_DRAWING = "official-drawing"
    VENDOR_DATASHEET = "vendor-datasheet"
    VENDOR_PRODUCT_PAGE = "vendor-product-page"
    REPO_PUBLIC_CONTENT = "repo-public-content"
    INTERNAL_REVIEW = "internal-review"
    LOCAL_MEASUREMENT = "local-measurement"
    DESIGN_PARAMETER = "design-parameter"
    TOOL_DOCUMENTATION = "tool-documentation"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    PENDING_MEASUREMENT = "pending-measurement"
    CONFLICT = "conflict"
    BLOCKED = "blocked"


class ImageUse(StrEnum):
    REFERENCE_ONLY = "reference-only"
    LOCAL_MEASUREMENT = "local-measurement"
    PUBLIC_APPROVED = "public-approved"


class ToolingCategory(StrEnum):
    COMPUTER_VISION_SCREEN = "computer-vision-screen"
    RENDERING = "rendering"
    DESIGN_ENGINEERING = "design-engineering"
    PRINT_METHODS = "3d-print-methods"
    MODELING = "3d-modeling"
    FUSION360 = "fusion360"
    WEB_PREVIEW = "web-preview"


class ToolingRepoStatus(StrEnum):
    DIRECT_DEPENDENCY = "direct-dependency"
    OPTIONAL_DEPENDENCY = "optional-dependency"
    TRANSITIVE_DEPENDENCY = "transitive-dependency"
    EXTERNAL_WORKFLOW = "external-workflow"
    NOT_PRESENT = "not-present"
    BLOCKED_SOURCE = "blocked-source"


class ToolingRecommendation(StrEnum):
    KEEP_BASELINE = "keep-baseline"
    EVALUATE_SANDBOX = "evaluate-sandbox"
    DEFER = "defer"
    BLOCKED = "blocked"
    INVENTORY_ONLY = "inventory-only"


class ToolingDependencyPolicy(StrEnum):
    CURRENT_DIRECT = "current-direct"
    CURRENT_OPTIONAL = "current-optional"
    TRANSITIVE_DO_NOT_IMPORT = "transitive-do-not-import"
    CANDIDATE_DO_NOT_INSTALL = "candidate-do-not-install"
    EXTERNAL_TOOL_NO_INSTALL = "external-tool-no-install"
    MANUAL_ONLY = "manual-only"
    DEFERRED_CREDENTIALS_REQUIRED = "deferred-credentials-required"
    BLOCKED_NO_USE = "blocked-no-use"


class ToolingAutomationSafety(StrEnum):
    READ_ONLY = "read-only"
    LOCAL_GENERATED_ARTIFACTS = "local-generated-artifacts"
    MANUAL_ONLY = "manual-only"
    NO_AUTOMATION = "no-automation"
    DEFERRED_CREDENTIALS = "deferred-credentials"
    BLOCKED = "blocked"


class SourceRef(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    title: str
    status: Literal["approved-public", "internal-review"] = "approved-public"
    url: str | None = None
    path: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def require_locator(self) -> SourceRef:
        if not self.url and not self.path:
            raise ValueError("source_refs entries require a url or path")
        return self


class EvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_ref: str
    locator: str
    retrieved_on: date
    evidence_type: EvidenceType
    verification_status: VerificationStatus
    notes: str | None = None


class ImageRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    allowed_use: ImageUse
    provenance: str
    source_ref: str | None = None
    url: str | None = None
    path: str | None = None
    approval_ref: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def require_locator(self) -> ImageRef:
        if not self.url and not self.path and not self.source_ref:
            raise ValueError("image_refs entries require a url, path, or source_ref")
        return self


class SourceConflict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    summary: str
    source_refs: list[str] = Field(min_length=1)
    affects_geometry: bool
    resolved: bool = False
    blocked_claims: list[str] = Field(default_factory=list)
    notes: str | None = None


class MaterialPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material: str
    status: Literal["primary", "supported", "fallback", "experimental", "blocked"]
    source_refs: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("material")
    @classmethod
    def material_is_uppercase(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("material must not be empty")
        return cleaned


class SpecBase(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: str
    name: str
    units: Literal["mm"]
    truth_state: TruthState
    measurement_status: MeasurementStatus
    source_refs: list[SourceRef] = Field(min_length=1)
    derivation_state: MeasurementStatus = MeasurementStatus.SOURCE_DERIVED
    open_measurement_blockers: list[str] = Field(default_factory=list)
    release_approval_refs: list[SourceRef] = Field(default_factory=list)
    image_refs: list[ImageRef] = Field(default_factory=list)
    source_conflicts: list[SourceConflict] = Field(default_factory=list)
    public_release: bool = False
    notes: str | None = None

    @field_validator("id")
    @classmethod
    def id_is_slug(cls, value: str) -> str:
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_-")
        if not value or any(char not in allowed for char in value):
            raise ValueError(
                "id must be a lowercase slug using letters, numbers, hyphens, or underscores"
            )
        return value

    @model_validator(mode="after")
    def require_blockers_for_unmeasured_specs(self) -> SpecBase:
        if (
            self.measurement_status != MeasurementStatus.MEASURED
            and not self.open_measurement_blockers
        ):
            raise ValueError("unmeasured specs require open_measurement_blockers")
        return self

    def source_ref_ids(self) -> set[str]:
        ids = {source.id for source in self.source_refs}
        ids.update(source.id for source in self.release_approval_refs)
        return ids

    def validate_evidence_source_refs(self, evidence: dict[str, EvidenceRef], label: str) -> None:
        ids = self.source_ref_ids()
        unknown = [
            f"{key}:{value.source_ref}"
            for key, value in evidence.items()
            if value.source_ref not in ids
        ]
        if unknown:
            raise ValueError(f"{label} reference unknown source_ref ids: {', '.join(unknown)}")

    def validate_supporting_refs(self) -> None:
        ids = self.source_ref_ids()
        unknown_images = []
        for image in self.image_refs:
            if image.source_ref and image.source_ref not in ids:
                unknown_images.append(f"{image.id}:source_ref={image.source_ref}")
            if image.approval_ref and image.approval_ref not in ids:
                unknown_images.append(f"{image.id}:approval_ref={image.approval_ref}")
        if unknown_images:
            raise ValueError(f"image_refs reference unknown source ids: {', '.join(unknown_images)}")

        unknown_conflicts = [
            f"{conflict.id}:{source_id}"
            for conflict in self.source_conflicts
            for source_id in conflict.source_refs
            if source_id not in ids
        ]
        if unknown_conflicts:
            raise ValueError(
                f"source_conflicts reference unknown source ids: {', '.join(unknown_conflicts)}"
            )


class HardwareSpec(SpecBase):
    schema_id: Literal["cbbs-cad/hardware/v1"] = Field(alias="schema")
    dimensions: dict[str, float] = Field(default_factory=dict)
    dimension_sources: dict[str, EvidenceRef] = Field(default_factory=dict)
    features: dict[str, Any] = Field(default_factory=dict)

    @field_validator("dimensions")
    @classmethod
    def dimensions_are_positive(cls, value: dict[str, float]) -> dict[str, float]:
        bad = [key for key, number in value.items() if number <= 0]
        if bad:
            raise ValueError(f"dimensions must be positive: {', '.join(sorted(bad))}")
        return value

    @model_validator(mode="after")
    def dimensions_have_evidence(self) -> HardwareSpec:
        if self.measurement_status != MeasurementStatus.BLOCKED and not self.dimensions:
            raise ValueError("non-blocked hardware specs require dimensions")

        missing = sorted(set(self.dimensions) - set(self.dimension_sources))
        extra = sorted(set(self.dimension_sources) - set(self.dimensions))
        if missing:
            raise ValueError(f"dimensions require dimension_sources: {', '.join(missing)}")
        if extra:
            raise ValueError(f"dimension_sources without dimensions: {', '.join(extra)}")

        self.validate_evidence_source_refs(self.dimension_sources, "dimension_sources")
        self.validate_supporting_refs()
        return self


class PrinterSpec(SpecBase):
    schema_id: Literal["cbbs-cad/printer/v1"] = Field(alias="schema")
    printer_type: Literal["corexy-enclosed", "bedslinger-large", "belt"]
    build_volume_kind: Literal["fixed", "belt", "blocked"]
    dimensions: dict[str, float] = Field(default_factory=dict)
    dimension_sources: dict[str, EvidenceRef] = Field(default_factory=dict)
    default_material: str | None = None
    material_policies: list[MaterialPolicy] = Field(default_factory=list)
    capabilities: dict[str, Any] = Field(default_factory=dict)
    slicer_guidance: list[str] = Field(default_factory=list)
    process_notes: list[str] = Field(default_factory=list)
    monitoring: dict[str, Any] = Field(default_factory=dict)

    @field_validator("dimensions")
    @classmethod
    def dimensions_are_positive(cls, value: dict[str, float]) -> dict[str, float]:
        bad = [key for key, number in value.items() if number <= 0]
        if bad:
            raise ValueError(f"dimensions must be positive: {', '.join(sorted(bad))}")
        return value

    @field_validator("default_material")
    @classmethod
    def default_material_is_uppercase(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None

    @model_validator(mode="after")
    def dimensions_have_evidence(self) -> PrinterSpec:
        if self.measurement_status != MeasurementStatus.BLOCKED and self.build_volume_kind != "blocked":
            required = {"build_x_mm", "build_y_mm", "build_z_mm"}
            missing_required = sorted(required - set(self.dimensions))
            if missing_required:
                raise ValueError(
                    "printer build volume requires dimensions: "
                    + ", ".join(missing_required)
                )

        missing = sorted(set(self.dimensions) - set(self.dimension_sources))
        extra = sorted(set(self.dimension_sources) - set(self.dimensions))
        if missing:
            raise ValueError(f"dimensions require dimension_sources: {', '.join(missing)}")
        if extra:
            raise ValueError(f"dimension_sources without dimensions: {', '.join(extra)}")

        self.validate_evidence_source_refs(self.dimension_sources, "dimension_sources")
        self.validate_supporting_refs()
        return self

    @model_validator(mode="after")
    def material_policies_are_supported(self) -> PrinterSpec:
        if not self.material_policies:
            raise ValueError("printer specs require material_policies")

        materials = [policy.material for policy in self.material_policies]
        duplicates = sorted({material for material in materials if materials.count(material) > 1})
        if duplicates:
            raise ValueError(f"duplicate material_policies: {', '.join(duplicates)}")

        source_ids = self.source_ref_ids()
        unknown = sorted(
            source_ref
            for policy in self.material_policies
            for source_ref in policy.source_refs
            if source_ref not in source_ids
        )
        if unknown:
            raise ValueError("material_policies reference unknown source ids: " + ", ".join(unknown))

        if self.default_material and self.default_material not in set(materials):
            raise ValueError("default_material must have a material_policies entry")
        return self


ModelFamily = Literal[
    "heltec_v2_fit_card",
    "heltec_v2_rugged_tray_gauge",
    "p070_fit_frame",
    "p070_rugged_bezel_fit_frame",
    "p070_hinged_wall_enclosure",
    "p070_heltec_outdoor_controller_enclosure",
    "p070_surface_treatment_coupon",
    "rugged_wall_section_coupon",
    "gasket_flange_coupon",
    "reinforced_mount_tab_coupon",
    "cable_entry_boss_coupon",
    "drip_lip_seam_coupon",
    "screw_boss_coupon",
    "heat_set_insert_coupon",
    "oled_window_coupon",
    "cable_relief_coupon",
    "label_plate_coupon",
]


class EnvironmentalContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exposure: Literal["lab", "outdoor-prototype", "outdoor-blocked"]
    ruggedization: list[
        Literal[
            "reinforced-walls",
            "gasket-seat",
            "drip-lip",
            "cable-entry",
            "mounting-tabs",
            "uv-material-review",
            "venting-review",
        ]
    ] = Field(default_factory=list)
    source_refs: list[str] = Field(default_factory=list)
    validation_plan: list[str] = Field(default_factory=list)
    rating_claims: list[str] = Field(default_factory=list)


class ConceptSpec(SpecBase):
    schema_id: Literal["cbbs-cad/concept/v1"] = Field(alias="schema")
    model_family: ModelFamily
    hardware_refs: list[str] = Field(default_factory=list)
    parameters: dict[str, Any] = Field(default_factory=dict)
    parameter_sources: dict[str, EvidenceRef] = Field(default_factory=dict)
    outputs: list[Literal["step", "stl"]] = Field(default_factory=lambda: ["step", "stl"])
    blocked_full_case: bool = True
    generation_enabled: bool = True
    generation_blockers: list[str] = Field(default_factory=list)
    environmental_context: EnvironmentalContext | None = None

    @model_validator(mode="after")
    def concepts_are_not_current_claims(self) -> ConceptSpec:
        if self.truth_state == TruthState.CURRENT:
            raise ValueError("generated CAD concept artifacts cannot use truth_state 'current'")
        return self

    @model_validator(mode="after")
    def parameters_have_evidence(self) -> ConceptSpec:
        dimension_like_params = {
            key
            for key, value in self.parameters.items()
            if isinstance(value, int | float)
            or (
                isinstance(value, list)
                and value
                and all(isinstance(item, int | float) for item in value)
            )
        }
        missing = sorted(dimension_like_params - set(self.parameter_sources))
        extra = sorted(set(self.parameter_sources) - set(self.parameters))
        if missing:
            raise ValueError(f"parameters require parameter_sources: {', '.join(missing)}")
        if extra:
            raise ValueError(f"parameter_sources without parameters: {', '.join(extra)}")

        self.validate_evidence_source_refs(self.parameter_sources, "parameter_sources")
        self.validate_supporting_refs()

        if self.environmental_context:
            source_ids = self.source_ref_ids()
            unknown = sorted(
                source_ref
                for source_ref in self.environmental_context.source_refs
                if source_ref not in source_ids
            )
            if unknown:
                raise ValueError(
                    "environmental_context references unknown source_ref ids: "
                    + ", ".join(unknown)
                )
        return self

    @model_validator(mode="after")
    def disabled_generation_has_blockers(self) -> ConceptSpec:
        if not self.generation_enabled and not self.generation_blockers:
            raise ValueError("disabled CAD generation requires generation_blockers")
        return self


class ToolingCandidateSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_id: Literal["cbbs-cad/tooling-candidate/v1"] = Field(alias="schema")
    id: str
    name: str
    truth_state: Literal[TruthState.INTERNAL_REVIEW]
    category: ToolingCategory
    current_repo_status: ToolingRepoStatus
    recommendation: ToolingRecommendation
    dependency_policy: ToolingDependencyPolicy
    automation_safety: ToolingAutomationSafety
    source_refs: list[SourceRef] = Field(min_length=1)
    evidence_refs: list[EvidenceRef] = Field(min_length=1)
    integration_paths: list[str] = Field(min_length=1)
    risks: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    blocked_claims: list[str] = Field(min_length=1)
    source_notes: list[str] = Field(default_factory=list)
    public_release: bool = False
    public_claims_allowed: bool = False
    gcode_generation_allowed: bool = False
    direct_import_allowed: bool = False
    install_commands: list[str] = Field(default_factory=list)
    notes: str | None = None

    @field_validator("id")
    @classmethod
    def id_is_slug(cls, value: str) -> str:
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_-")
        if not value or any(char not in allowed for char in value):
            raise ValueError(
                "id must be a lowercase slug using letters, numbers, hyphens, or underscores"
            )
        return value

    @model_validator(mode="after")
    def evidence_refs_are_known(self) -> ToolingCandidateSpec:
        source_ids = {source.id for source in self.source_refs}
        unknown = [
            f"{index}:{evidence.source_ref}"
            for index, evidence in enumerate(self.evidence_refs)
            if evidence.source_ref not in source_ids
        ]
        if unknown:
            raise ValueError(
                "evidence_refs reference unknown source_ref ids: " + ", ".join(unknown)
            )

        missing_locators = [
            str(index)
            for index, evidence in enumerate(self.evidence_refs)
            if not evidence.locator.strip()
        ]
        if missing_locators:
            raise ValueError(
                "evidence_refs require non-empty locators: " + ", ".join(missing_locators)
            )
        return self


class SpecBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hardware: list[HardwareSpec]
    concepts: list[ConceptSpec]
    printers: list[PrinterSpec] = Field(default_factory=list)
    tooling: list[ToolingCandidateSpec] = Field(default_factory=list)

    @model_validator(mode="after")
    def concept_hardware_refs_exist(self) -> SpecBundle:
        hardware_ids = {item.id for item in self.hardware}
        unknown: list[str] = []
        for concept in self.concepts:
            unknown.extend(ref for ref in concept.hardware_refs if ref not in hardware_ids)
        if unknown:
            raise ValueError(f"unknown hardware_refs: {', '.join(sorted(set(unknown)))}")
        return self

    @model_validator(mode="after")
    def ids_are_unique_by_kind(self) -> SpecBundle:
        for kind, items in (
            ("hardware", self.hardware),
            ("concepts", self.concepts),
            ("printers", self.printers),
            ("tooling", self.tooling),
        ):
            ids = [item.id for item in items]
            duplicates = sorted({item_id for item_id in ids if ids.count(item_id) > 1})
            if duplicates:
                raise ValueError(f"duplicate {kind} ids: {', '.join(duplicates)}")
        return self
