from __future__ import annotations

import pytest
from pydantic import ValidationError

from cbbs_cad.audit import audit_bundle
from cbbs_cad.models import ConceptSpec, HardwareSpec, ToolingCandidateSpec
from cbbs_cad.report import build_evidence_report
from cbbs_cad.specs import DEFAULT_DATA_DIR, load_specs


def _bundle_with_tooling(data: dict) -> object:
    return load_specs(paths=[], data_dir=DEFAULT_DATA_DIR).model_copy(
        update={
            "hardware": [],
            "concepts": [],
            "printers": [],
            "tooling": [ToolingCandidateSpec.model_validate(data)],
        }
    )


def test_default_specs_validate() -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)

    assert {item.id for item in bundle.hardware} >= {
        "agriculture_gateway_unselected",
        "adafruit_sma_ufl_pigtail_851",
        "bioenno_blf_0612c_lifepo4_pack",
        "bioenno_bpc_0602dc_charger_reference",
        "creality_k1_series_asa_profile",
        "heltec_wifi_lora_32_v2",
        "jst_xh_4p_reference",
        "lapp_skintop_st_m12x15_reference",
        "lapp_skintop_str_npt_3_4_reference",
        "m3_pin_clearance_reference",
        "nextion_nx8048p070_011c",
        "p800_display_unselected",
        "pololu_s13v30f5_regulator",
        "raspberry_pi_hub_unselected",
        "taoglas_ti_96_a113_915mhz_antenna",
    }
    assert {item.id for item in bundle.concepts} >= {
        "heltec_v2_fit_card",
        "heltec_v2_rugged_tray_gauge",
        "p070_fit_frame",
        "p070_hinged_wall_enclosure",
        "p070_heltec_outdoor_controller_enclosure",
        "npt_3_4_thread_fit_coupon",
        "p070_rugged_bezel_fit_frame",
        "p070_surface_treatment_coupon",
        "rugged_wall_section_coupon",
        "gasket_flange_coupon",
        "reinforced_mount_tab_coupon",
        "cable_entry_boss_coupon",
        "drip_lip_seam_coupon",
    }
    assert {item.id for item in bundle.printers} >= {
        "creality_k1_modified_asa",
        "anycubic_kobra2_max",
        "creality_cr30_belt",
    }
    assert {item.id for item in bundle.tooling} >= {
        "cadquery_current_baseline",
        "trimesh_current_baseline",
        "mss_desktop_screenshot_eval",
        "build123d_cad_as_code_eval",
        "manifold3d_mesh_boolean_eval",
        "prusaslicer_cli_profile_research",
        "aps_fusion_automation_deferred",
    }


def test_hardware_requires_source_refs() -> None:
    with pytest.raises(ValidationError):
        HardwareSpec.model_validate(
            {
                "schema": "cbbs-cad/hardware/v1",
                "id": "missing_source",
                "name": "Missing source",
                "units": "mm",
                "truth_state": "internal review",
                "measurement_status": "measurement-required",
                "open_measurement_blockers": ["physical measurement"],
                "dimensions": {"length_mm": 10.0},
                "source_refs": [],
            }
        )


def test_hardware_requires_dimension_evidence() -> None:
    with pytest.raises(ValidationError, match="dimension_sources"):
        HardwareSpec.model_validate(
            {
                "schema": "cbbs-cad/hardware/v1",
                "id": "missing_dimension_evidence",
                "name": "Missing dimension evidence",
                "units": "mm",
                "truth_state": "internal review",
                "measurement_status": "measurement-required",
                "open_measurement_blockers": ["physical measurement"],
                "dimensions": {"length_mm": 10.0},
                "source_refs": [{"id": "source", "title": "Source", "path": "docs/source.md"}],
            }
        )


def test_hardware_requires_units() -> None:
    with pytest.raises(ValidationError):
        HardwareSpec.model_validate(
            {
                "schema": "cbbs-cad/hardware/v1",
                "id": "missing_units",
                "name": "Missing units",
                "truth_state": "internal review",
                "measurement_status": "measurement-required",
                "open_measurement_blockers": ["physical measurement"],
                "dimensions": {"length_mm": 10.0},
                "source_refs": [{"id": "source", "title": "Source", "path": "docs/source.md"}],
            }
        )


def test_concept_requires_parameter_evidence() -> None:
    with pytest.raises(ValidationError, match="parameter_sources"):
        ConceptSpec.model_validate(
            {
                "schema": "cbbs-cad/concept/v1",
                "id": "missing_parameter_evidence",
                "name": "Missing parameter evidence",
                "units": "mm",
                "truth_state": "internal review",
                "measurement_status": "measurement-required",
                "open_measurement_blockers": ["physical measurement"],
                "source_refs": [{"id": "source", "title": "Source", "path": "docs/source.md"}],
                "model_family": "p070_fit_frame",
                "parameters": {"length_mm": 10.0},
            }
        )


def test_tooling_candidate_requires_source_refs() -> None:
    with pytest.raises(ValidationError):
        ToolingCandidateSpec.model_validate(
            {
                "schema": "cbbs-cad/tooling-candidate/v1",
                "id": "missing_tool_source",
                "name": "Missing Tool Source",
                "truth_state": "internal review",
                "category": "3d-modeling",
                "current_repo_status": "not-present",
                "recommendation": "evaluate-sandbox",
                "dependency_policy": "candidate-do-not-install",
                "automation_safety": "local-generated-artifacts",
                "source_refs": [],
                "evidence_refs": [],
                "integration_paths": ["research only"],
                "blocked_claims": ["No public product capability claims."],
            }
        )


def test_tooling_candidate_rejects_unknown_evidence_ref() -> None:
    with pytest.raises(ValidationError, match="unknown source_ref"):
        ToolingCandidateSpec.model_validate(
            {
                "schema": "cbbs-cad/tooling-candidate/v1",
                "id": "unknown_tool_source",
                "name": "Unknown Tool Source",
                "truth_state": "internal review",
                "category": "3d-modeling",
                "current_repo_status": "not-present",
                "recommendation": "evaluate-sandbox",
                "dependency_policy": "candidate-do-not-install",
                "automation_safety": "local-generated-artifacts",
                "source_refs": [
                    {"id": "source", "title": "Source", "path": "docs/source.md"}
                ],
                "evidence_refs": [
                    {
                        "source_ref": "missing",
                        "locator": "line 1",
                        "retrieved_on": "2026-05-05",
                        "evidence_type": "tool-documentation",
                        "verification_status": "verified",
                    }
                ],
                "integration_paths": ["research only"],
                "blocked_claims": ["No public product capability claims."],
            }
        )


def test_concept_rejects_current_truth_state() -> None:
    with pytest.raises(ValidationError, match="cannot use truth_state 'current'"):
        ConceptSpec.model_validate(
            {
                "schema": "cbbs-cad/concept/v1",
                "id": "bad_current",
                "name": "Bad current concept",
                "units": "mm",
                "truth_state": "current",
                "measurement_status": "measurement-required",
                "open_measurement_blockers": ["physical measurement"],
                "source_refs": [{"id": "source", "title": "Source", "path": "docs/source.md"}],
                "model_family": "p070_fit_frame",
                "hardware_refs": [],
            }
        )


def test_default_source_audit_passes() -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)

    assert audit_bundle(bundle) == []


def test_tooling_audit_rejects_public_claims_and_gcode_generation() -> None:
    data = {
        "schema": "cbbs-cad/tooling-candidate/v1",
        "id": "bad_tooling_claim",
        "name": "Bad Tooling Claim",
        "truth_state": "internal review",
        "category": "3d-print-methods",
        "current_repo_status": "not-present",
        "recommendation": "evaluate-sandbox",
        "dependency_policy": "candidate-do-not-install",
        "automation_safety": "manual-only",
        "source_refs": [{"id": "source", "title": "Source", "path": "docs/source.md"}],
        "evidence_refs": [
            {
                "source_ref": "source",
                "locator": "line 1",
                "retrieved_on": "2026-05-05",
                "evidence_type": "tool-documentation",
                "verification_status": "verified",
            }
        ],
        "integration_paths": ["research only"],
        "blocked_claims": ["No public product capability claims."],
        "public_claims_allowed": True,
        "gcode_generation_allowed": True,
    }
    bundle = _bundle_with_tooling(data)

    failures = audit_bundle(bundle)
    assert any("public product capability claims" in item for item in failures)
    assert any("G-code generation" in item for item in failures)


def test_tooling_audit_rejects_candidate_install_commands() -> None:
    data = {
        "schema": "cbbs-cad/tooling-candidate/v1",
        "id": "bad_tooling_install",
        "name": "Bad Tooling Install",
        "truth_state": "internal review",
        "category": "rendering",
        "current_repo_status": "not-present",
        "recommendation": "evaluate-sandbox",
        "dependency_policy": "candidate-do-not-install",
        "automation_safety": "local-generated-artifacts",
        "source_refs": [{"id": "source", "title": "Source", "path": "docs/source.md"}],
        "evidence_refs": [
            {
                "source_ref": "source",
                "locator": "line 1",
                "retrieved_on": "2026-05-05",
                "evidence_type": "tool-documentation",
                "verification_status": "verified",
            }
        ],
        "integration_paths": ["research only"],
        "blocked_claims": ["No public product capability claims."],
        "install_commands": ["uv add package"],
    }
    bundle = _bundle_with_tooling(data)

    assert "must not include install commands" in audit_bundle(bundle)[0]


def test_tooling_audit_rejects_transitive_direct_imports() -> None:
    data = {
        "schema": "cbbs-cad/tooling-candidate/v1",
        "id": "bad_transitive_import",
        "name": "Bad Transitive Import",
        "truth_state": "internal review",
        "category": "3d-modeling",
        "current_repo_status": "transitive-dependency",
        "recommendation": "evaluate-sandbox",
        "dependency_policy": "transitive-do-not-import",
        "automation_safety": "local-generated-artifacts",
        "source_refs": [{"id": "source", "title": "Source", "path": "docs/source.md"}],
        "evidence_refs": [
            {
                "source_ref": "source",
                "locator": "line 1",
                "retrieved_on": "2026-05-05",
                "evidence_type": "tool-documentation",
                "verification_status": "verified",
            }
        ],
        "integration_paths": ["research only"],
        "blocked_claims": ["No public product capability claims."],
        "direct_import_allowed": True,
    }
    bundle = _bundle_with_tooling(data)

    assert "not approved direct import surfaces" in audit_bundle(bundle)[0]


def test_p070_hinged_enclosure_is_measurement_gated() -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)
    concept = next(item for item in bundle.concepts if item.id == "p070_hinged_wall_enclosure")

    assert concept.blocked_full_case is True
    assert concept.generation_enabled is True
    assert concept.measurement_status == "measurement-required"
    assert concept.generation_blockers


def test_p070_heltec_outdoor_concept_is_internal_review_and_rating_blocked() -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)
    concept = next(
        item for item in bundle.concepts if item.id == "p070_heltec_outdoor_controller_enclosure"
    )
    required_hardware = {
        "heltec_wifi_lora_32_v2",
        "taoglas_ti_96_a113_915mhz_antenna",
        "adafruit_sma_ufl_pigtail_851",
        "bioenno_blf_0612c_lifepo4_pack",
        "pololu_s13v30f5_regulator",
        "bioenno_bpc_0602dc_charger_reference",
        "lapp_skintop_str_npt_3_4_reference",
    }

    assert concept.truth_state == "internal review"
    assert concept.public_release is False
    assert concept.blocked_full_case is True
    assert concept.environmental_context
    assert concept.environmental_context.exposure == "outdoor-blocked"
    assert concept.environmental_context.rating_claims == []
    assert required_hardware <= set(concept.hardware_refs)
    assert concept.parameters["front_contour_rail_width_mm"] == 1.8
    assert concept.parameters["rear_pod_macro_rib_pitch_mm"] == 18.0
    assert concept.parameters["raised_brand_text_font_size_mm"] == 10.0
    assert concept.parameters["field_gland_boss_outer_diameter_mm"] == 44.0
    assert concept.parameters["field_gland_thread_major_diameter_mm"] == 26.67
    assert concept.parameters["field_gland_threads_per_inch"] == 14.0
    assert "p070_structural_strengthening_findings" in {
        source.id for source in concept.source_refs
    }
    assert "p070_npt_thread_entry_findings" in {source.id for source in concept.source_refs}
    for parameter in (
        "front_contour_rail_width_mm",
        "front_contour_rail_height_mm",
        "front_contour_rail_clearance_mm",
        "rear_pod_macro_rib_width_mm",
        "rear_pod_macro_rib_height_mm",
        "rear_pod_macro_rib_pitch_mm",
        "raised_brand_relief_mm",
        "raised_brand_text_font_size_mm",
        "raised_brand_icon_diameter_mm",
    ):
        evidence = concept.parameter_sources[parameter]
        assert evidence.source_ref == "p070_futuristic_surface_reinforcement_findings"
        assert evidence.verification_status == "pending-measurement"
    assert concept.parameters["surface_feature_edge_chamfer_mm"] == 0.2
    assert (
        concept.parameter_sources["surface_feature_edge_chamfer_mm"].source_ref
        == "p070_model_review"
    )
    for parameter in (
        "field_gland_boss_outer_diameter_mm",
        "field_gland_thread_clearance_mm",
        "field_wire_trunk_channel_width_mm",
    ):
        evidence = concept.parameter_sources[parameter]
        assert evidence.source_ref == "p070_npt_thread_entry_findings"
        assert evidence.verification_status == "pending-measurement"
    assert (
        concept.parameter_sources["field_gland_thread_major_diameter_mm"].source_ref
        == "lapp_skintop_str_npt_3_4_reference"
    )


def test_p070_surface_treatment_coupon_is_internal_review() -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)
    concept = next(item for item in bundle.concepts if item.id == "p070_surface_treatment_coupon")

    assert concept.truth_state == "internal review"
    assert concept.public_release is False
    assert concept.blocked_full_case is True
    assert concept.model_family == "p070_surface_treatment_coupon"
    assert concept.parameters["coupon_length_mm"] == 96.0
    assert concept.parameters["raised_brand_relief_mm"] == 1.2
    assert concept.parameters["surface_feature_edge_chamfer_mm"] == 0.2
    assert concept.parameter_sources["coupon_length_mm"].source_ref == "p070_model_review"


def test_npt_thread_fit_coupon_is_measurement_gated() -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)
    concept = next(item for item in bundle.concepts if item.id == "npt_3_4_thread_fit_coupon")

    assert concept.truth_state == "internal review"
    assert concept.public_release is False
    assert concept.blocked_full_case is True
    assert concept.model_family == "npt_3_4_thread_fit_coupon"
    assert "lapp_skintop_str_npt_3_4_reference" in concept.hardware_refs
    assert concept.parameters["npt_thread_major_diameter_mm"] == 26.67
    assert concept.parameters["npt_threads_per_inch"] == 14.0
    assert concept.parameters["npt_thread_clearance_variants_mm"] == [0.35, 0.55]
    assert (
        concept.parameter_sources["npt_thread_clearance_variants_mm"].verification_status
        == "pending-measurement"
    )
    assert concept.environmental_context
    assert concept.environmental_context.rating_claims == []


def test_p070_hinged_structural_strengthening_source_is_registered() -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)
    concept = next(item for item in bundle.concepts if item.id == "p070_hinged_wall_enclosure")

    assert "p070_structural_strengthening_findings" in {
        source.id for source in concept.source_refs
    }


def test_p070_heltec_outdoor_hardware_specs_capture_selected_basis() -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)
    hardware = {item.id: item for item in bundle.hardware}

    assert hardware["taoglas_ti_96_a113_915mhz_antenna"].dimensions["body_length_mm"] == 203.0
    assert hardware["adafruit_sma_ufl_pigtail_851"].dimensions["cable_length_mm"] == 150.0
    assert hardware["bioenno_blf_0612c_lifepo4_pack"].dimensions["case_length_mm"] == 115.0
    assert hardware["pololu_s13v30f5_regulator"].dimensions["board_length_mm"] == 22.9
    assert hardware["lapp_skintop_str_npt_3_4_reference"].dimensions["cable_clamp_min_mm"] == 9.0
    assert hardware["lapp_skintop_str_npt_3_4_reference"].dimensions["cable_clamp_max_mm"] == 16.0
    assert hardware["lapp_skintop_str_npt_3_4_reference"].dimensions["npt_3_4_threads_per_inch"] == 14.0
    assert hardware["bioenno_bpc_0602dc_charger_reference"].features["enclosure_use"].startswith(
        "External charger"
    )

    for hardware_id in (
        "taoglas_ti_96_a113_915mhz_antenna",
        "adafruit_sma_ufl_pigtail_851",
        "bioenno_blf_0612c_lifepo4_pack",
        "pololu_s13v30f5_regulator",
        "bioenno_bpc_0602dc_charger_reference",
        "lapp_skintop_str_npt_3_4_reference",
    ):
        assert hardware[hardware_id].source_refs
        assert hardware[hardware_id].open_measurement_blockers


def test_source_audit_rejects_unapproved_public_image() -> None:
    data = {
        "schema": "cbbs-cad/hardware/v1",
        "id": "bad_public_image",
        "name": "Bad public image",
        "units": "mm",
        "truth_state": "internal review",
        "measurement_status": "measurement-required",
        "open_measurement_blockers": ["physical measurement"],
        "dimensions": {"length_mm": 10.0},
        "dimension_sources": {
            "length_mm": {
                "source_ref": "source",
                "locator": "line 1",
                "retrieved_on": "2026-05-01",
                "evidence_type": "vendor-datasheet",
                "verification_status": "verified",
            }
        },
        "source_refs": [{"id": "source", "title": "Source", "path": "docs/source.md"}],
        "image_refs": [
            {
                "id": "bad_image",
                "title": "Bad image",
                "allowed_use": "public-approved",
                "provenance": "vendor product page",
                "source_ref": "source",
            }
        ],
    }
    bundle = load_specs(paths=[], data_dir=DEFAULT_DATA_DIR).model_copy(
        update={"hardware": [HardwareSpec.model_validate(data)], "concepts": []}
    )

    assert "public-approved without an approval_ref" in audit_bundle(bundle)[0]


def test_source_audit_rejects_unresolved_geometry_conflict() -> None:
    data = {
        "schema": "cbbs-cad/hardware/v1",
        "id": "bad_geometry_conflict",
        "name": "Bad geometry conflict",
        "units": "mm",
        "truth_state": "internal review",
        "measurement_status": "measurement-required",
        "open_measurement_blockers": ["physical measurement"],
        "dimensions": {"length_mm": 10.0},
        "dimension_sources": {
            "length_mm": {
                "source_ref": "source",
                "locator": "line 1",
                "retrieved_on": "2026-05-01",
                "evidence_type": "vendor-datasheet",
                "verification_status": "verified",
            }
        },
        "source_refs": [{"id": "source", "title": "Source", "path": "docs/source.md"}],
        "source_conflicts": [
            {
                "id": "dimensional_conflict",
                "summary": "Two source drawings disagree.",
                "source_refs": ["source"],
                "affects_geometry": True,
                "resolved": False,
            }
        ],
    }
    bundle = load_specs(paths=[], data_dir=DEFAULT_DATA_DIR).model_copy(
        update={"hardware": [HardwareSpec.model_validate(data)], "concepts": []}
    )

    assert "unresolved geometry conflict" in audit_bundle(bundle)[0]


def test_source_audit_rejects_full_case_from_unmeasured_hardware() -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)
    concept = next(item for item in bundle.concepts if item.id == "heltec_v2_fit_card").model_copy(
        update={"blocked_full_case": False}
    )
    bad_bundle = bundle.model_copy(update={"concepts": [concept]})

    assert "full enclosure generation requires measured hardware" in audit_bundle(bad_bundle)[0]


def test_source_audit_rejects_unverified_environmental_rating_claim() -> None:
    data = {
        "schema": "cbbs-cad/concept/v1",
        "id": "bad_environmental_claim",
        "name": "Bad environmental claim",
        "units": "mm",
        "truth_state": "internal review",
        "measurement_status": "measurement-required",
        "open_measurement_blockers": ["physical validation"],
        "source_refs": [{"id": "source", "title": "Source", "path": "docs/source.md"}],
        "model_family": "label_plate_coupon",
        "environmental_context": {
            "exposure": "outdoor-prototype",
            "ruggedization": ["reinforced-walls"],
            "source_refs": ["source"],
            "validation_plan": ["bench validation"],
            "rating_claims": ["IP65"],
        },
    }
    bundle = load_specs(paths=[], data_dir=DEFAULT_DATA_DIR).model_copy(
        update={"hardware": [], "concepts": [ConceptSpec.model_validate(data)]}
    )

    failures = audit_bundle(bundle)
    assert any("environmental rating claims require measured hardware" in item for item in failures)
    assert any("blocked full-case concept" in item for item in failures)


def test_evidence_report_lists_blocked_hardware() -> None:
    report = build_evidence_report(load_specs(data_dir=DEFAULT_DATA_DIR))
    hardware_ids = {item["id"] for item in report["hardware"]}

    assert "raspberry_pi_hub_unselected" in hardware_ids


def test_concept_rejects_production_label() -> None:
    with pytest.raises(ValidationError):
        ConceptSpec.model_validate(
            {
                "schema": "cbbs-cad/concept/v1",
                "id": "bad_production",
                "name": "Bad production concept",
                "units": "mm",
                "truth_state": "production",
                "measurement_status": "measurement-required",
                "open_measurement_blockers": ["physical measurement"],
                "source_refs": [{"id": "source", "title": "Source", "path": "docs/source.md"}],
                "model_family": "p070_fit_frame",
                "hardware_refs": [],
            }
        )
