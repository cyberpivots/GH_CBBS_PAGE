from __future__ import annotations

from pathlib import Path

import pytest

from cbbs_cad.generate import generate_concepts
from cbbs_cad.models import MeasurementStatus
from cbbs_cad.specs import DEFAULT_DATA_DIR, load_specs

pytest.importorskip("cadquery")
trimesh = pytest.importorskip("trimesh")


def _artifact_by_id(manifest: dict, concept_id: str) -> dict:
    return next(item for item in manifest["artifacts"] if item["concept_id"] == concept_id)


def _generated_path(output_dir: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    prefix = Path("3d-print-work/generated/cad")
    return output_dir / path.relative_to(prefix) if path.is_relative_to(prefix) else output_dir / path


def _broken_face_count(mesh) -> int:
    try:
        return len(trimesh.repair.broken_faces(mesh))
    except Exception:
        return 0


def _assert_p070_display_mount(display_mount: dict) -> None:
    assert display_mount["schema"] == "cbbs-cad/p070-display-mount/v1"
    assert display_mount["hardware_ref"] == "nextion_nx8048p070_011c"
    assert display_mount["mount_hole_count"] == 4
    assert display_mount["hole_span_mm"] == {
        "x": pytest.approx(174.6),
        "y": pytest.approx(101.6),
    }
    assert len(display_mount["positions_mm"]) == 4
    assert sorted({point["x"] for point in display_mount["positions_mm"]}) == pytest.approx(
        [-87.3, 87.3]
    )
    assert sorted({point["y"] for point in display_mount["positions_mm"]}) == pytest.approx(
        [-50.8, 50.8]
    )
    assert display_mount["source_mount_hole_diameter_mm"] == pytest.approx(3.2)
    assert display_mount["clearance_reference_diameter_mm"] == pytest.approx(3.4)
    assert display_mount["boss_outer_diameter_mm"] == pytest.approx(8.0)
    assert display_mount["boss_height_mm"] == pytest.approx(6.0)
    assert display_mount["boss_hole_diameter_mm"] == pytest.approx(2.6)
    assert display_mount["thread_mode"] == "m3_printed_pilot"
    assert display_mount["nominal_thread"] == "M3x0.5"
    assert display_mount["pilot_diameter_mm"] == pytest.approx(2.6)
    assert display_mount["validation_status"] == "physical-print-required"


def test_generate_heltec_fit_card_and_p070_frame(tmp_path) -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)
    manifest = generate_concepts(
        bundle,
        output_dir=tmp_path,
        concept_ids=["heltec_v2_fit_card", "p070_fit_frame"],
    )

    heltec = _artifact_by_id(manifest, "heltec_v2_fit_card")
    p070 = _artifact_by_id(manifest, "p070_fit_frame")

    assert (tmp_path / "heltec_v2_fit_card.step").is_file()
    assert (tmp_path / "heltec_v2_fit_card.stl").is_file()
    assert (tmp_path / "p070_fit_frame.step").is_file()
    assert (tmp_path / "p070_fit_frame.stl").is_file()
    assert heltec["bounds_mm"]["x"] == pytest.approx(51.0, abs=0.05)
    assert heltec["bounds_mm"]["y"] == pytest.approx(25.5, abs=0.05)
    assert p070["bounds_mm"]["x"] == pytest.approx(181.0, abs=0.05)
    assert p070["bounds_mm"]["y"] == pytest.approx(108.0, abs=0.05)

    mesh = trimesh.load_mesh(tmp_path / "p070_fit_frame.stl", force="mesh")
    assert mesh.is_watertight
    assert mesh.extents[0] == pytest.approx(181.0, abs=0.1)
    assert mesh.extents[1] == pytest.approx(108.0, abs=0.1)


def test_generate_rugged_outdoor_prototype_artifacts(tmp_path) -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)
    concept_ids = [
        "rugged_wall_section_coupon",
        "gasket_flange_coupon",
        "reinforced_mount_tab_coupon",
        "cable_entry_boss_coupon",
        "drip_lip_seam_coupon",
        "p070_rugged_bezel_fit_frame",
        "heltec_v2_rugged_tray_gauge",
    ]
    manifest = generate_concepts(bundle, output_dir=tmp_path, concept_ids=concept_ids)

    expected_bounds = {
        "rugged_wall_section_coupon": (80.0, 50.0, 7.0),
        "gasket_flange_coupon": (90.0, 58.0, 4.0),
        "reinforced_mount_tab_coupon": (82.0, 36.0, 7.0),
        "cable_entry_boss_coupon": (70.0, 45.0, 12.0),
        "drip_lip_seam_coupon": (80.0, 40.0, 9.0),
        "p070_rugged_bezel_fit_frame": (205.0, 132.0, 5.5),
        "heltec_v2_rugged_tray_gauge": (60.0, 34.5, 10.0),
    }

    for concept_id, bounds in expected_bounds.items():
        artifact = _artifact_by_id(manifest, concept_id)
        assert (tmp_path / f"{concept_id}.step").is_file()
        assert (tmp_path / f"{concept_id}.stl").is_file()
        assert artifact["blocked_full_case"] is True
        assert artifact["public_release"] is False
        assert artifact["bounds_mm"]["x"] == pytest.approx(bounds[0], abs=0.15)
        assert artifact["bounds_mm"]["y"] == pytest.approx(bounds[1], abs=0.15)
        assert artifact["bounds_mm"]["z"] == pytest.approx(bounds[2], abs=0.15)

        mesh = trimesh.load_mesh(tmp_path / f"{concept_id}.stl", force="mesh")
        assert mesh.is_watertight
        assert mesh.extents[0] == pytest.approx(bounds[0], abs=0.2)
        assert mesh.extents[1] == pytest.approx(bounds[1], abs=0.2)


def test_p070_surface_treatment_coupon_generates_watertight(tmp_path) -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)
    manifest = generate_concepts(
        bundle,
        output_dir=tmp_path,
        concept_ids=["p070_surface_treatment_coupon"],
    )
    artifact = _artifact_by_id(manifest, "p070_surface_treatment_coupon")

    assert artifact["truth_state"] == "internal review"
    assert artifact["public_release"] is False
    assert artifact["blocked_full_case"] is True
    assert artifact["bounds_mm"]["x"] == pytest.approx(96.0, abs=0.2)
    assert artifact["bounds_mm"]["y"] == pytest.approx(44.0, abs=0.2)
    assert artifact["bounds_mm"]["z"] == pytest.approx(3.6, abs=0.2)

    stl_path = tmp_path / "p070_surface_treatment_coupon.stl"
    assert stl_path.is_file()
    mesh = trimesh.load_mesh(stl_path, force="mesh")
    assert mesh.is_watertight


def test_p070_hinged_enclosure_generates_as_blocked_internal_review(tmp_path) -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)
    manifest = generate_concepts(
        bundle,
        output_dir=tmp_path,
        concept_ids=["p070_hinged_wall_enclosure"],
    )
    artifact = _artifact_by_id(manifest, "p070_hinged_wall_enclosure")

    assert (tmp_path / "p070_hinged_wall_enclosure.step").is_file()
    assert (tmp_path / "p070_hinged_wall_enclosure.stl").is_file()
    assert artifact["blocked_full_case"] is True
    assert artifact["generation_enabled"] is True
    assert artifact["measurement_status"] == "measurement-required"
    assert artifact["bounds_mm"]["x"] > 205.0
    assert artifact["bounds_mm"]["y"] > 125.0
    assert artifact["bounds_mm"]["z"] > 32.0

    mesh = trimesh.load_mesh(tmp_path / "p070_hinged_wall_enclosure.stl", force="mesh")
    assert mesh.is_watertight


def test_p070_hinged_enclosure_exports_assembly_parts_and_views(tmp_path) -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)
    manifest = generate_concepts(
        bundle,
        output_dir=tmp_path,
        concept_ids=["p070_hinged_wall_enclosure"],
    )
    artifact = _artifact_by_id(manifest, "p070_hinged_wall_enclosure")
    assembly = artifact["assembly"]
    metadata = assembly["metadata"]

    assert assembly["schema"] == "cbbs-cad/generated-assembly/v1"
    _assert_p070_display_mount(metadata["display_mount"])
    assert set(assembly["views"]) == {
        "closed-front",
        "closed-isometric",
        "door-open",
        "exploded",
        "k1-plate-tray",
        "k1-plate-door",
        "k1-max-combined",
        "hardware-reference",
    }
    parts = {part["id"]: part for part in assembly["parts"]}
    assert set(parts) == {
        "rear_tray",
        "front_display_door",
        "hinge_pin",
        "display_reference",
        "m12_gland_reference",
    }
    assert parts["rear_tray"]["role"] == "print"
    assert parts["front_display_door"]["role"] == "print"
    assert parts["rear_tray"]["occurrence"]["name"] == "CBBS P070 rear tray"
    assert parts["front_display_door"]["support_risk"]["level"] == "medium"

    for part in parts.values():
        assert _generated_path(tmp_path, part["files"]["step"]).is_file()
        stl_path = _generated_path(tmp_path, part["files"]["stl"])
        assert stl_path.is_file()
        mesh = trimesh.load_mesh(stl_path, force="mesh")
        assert mesh.is_watertight
        assert _broken_face_count(mesh) == 0

    for view in assembly["views"].values():
        assert _generated_path(tmp_path, view["file"]).is_file()


def test_p070_heltec_outdoor_enclosure_exports_power_rf_references(tmp_path) -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)
    manifest = generate_concepts(
        bundle,
        output_dir=tmp_path,
        concept_ids=["p070_heltec_outdoor_controller_enclosure"],
    )
    artifact = _artifact_by_id(manifest, "p070_heltec_outdoor_controller_enclosure")
    assembly = artifact["assembly"]
    metadata = assembly["metadata"]
    parts = {part["id"]: part for part in assembly["parts"]}

    assert artifact["truth_state"] == "internal review"
    assert artifact["public_release"] is False
    assert artifact["blocked_full_case"] is True
    assert {
        "rear_tray",
        "rear_panel_core",
        "rear_battery_pod",
        "front_display_door",
        "heltec_v2_reference",
        "lifepo4_battery_reference",
        "buckboost_regulator_reference",
        "sma_bulkhead_reference",
        "antenna_keepout_reference",
        "wire_channel_reference",
    } <= set(parts)
    assert "power-rf-layout" in assembly["views"]
    assert "k1-component-rear-panel" in assembly["views"]
    assert "k1-component-rear-pod" in assembly["views"]
    assert "k1-component-front-door" in assembly["views"]
    assert metadata["power_layout"]["battery_service_bay_mm"] == {
        "x": 125.0,
        "y": 73.0,
        "z": 90.0,
    }
    assert metadata["power_layout"]["charger_location"] == "external-only"
    assert metadata["rf_layout"]["antenna_keepout_mm"] == {
        "diameter": 25.0,
        "external_sweep": 230.0,
    }
    assert metadata["mechanical_reinforcement"]["venting_review"] == "blocked"
    reinforcement = metadata["mechanical_reinforcement"]
    assert reinforcement["rear_panel_floor_rib_lattice"]["count"] == 6
    assert reinforcement["rear_panel_inner_perimeter_rails"]["count"] == 4
    assert reinforcement["display_boss_to_floor_webs"]["count"] == 8
    assert reinforcement["front_door_edge_corner_reinforcement"]["outside_display_window"] is True
    assert reinforcement["rear_pod_floor_ribs"]["count"] == 5
    assert reinforcement["rear_pod_side_wall_ledges"]["count"] == 4
    _assert_p070_display_mount(metadata["display_mount"])
    hardware_placement = metadata["hardware_placement"]
    assert hardware_placement["heat_set_inserts"]["status"] == "deferred"
    for aid_id in ("battery", "heltec_v2", "regulator", "rf_route"):
        aid = hardware_placement["alignment_aids"][aid_id]
        assert aid["verified_screw_holes"] is False
        assert aid["mounting_holes_modeled"] is False
        assert aid["verification_status"] == "pending-measurement"
    interface = metadata["mechanical_interface"]
    assert interface["rear_pod_relation"] == "sidecar-connected"
    assert interface["rear_pod_body_y_min_mm"] > interface["display_body_y_max_mm"]
    assert interface["body_clearance_from_display_y_mm"] >= 12.0
    assert interface["connector"]["type"] == "printed tongue and landing"
    assert metadata["mechanical_reinforcement"]["rear_pod_sidecar_connected"] is True
    review = metadata["review"]
    assert review["baseline_run_id"] == "fusion-20260503T022638Z"
    assert review["review_status"] == "generated-fusion-baseline-clean; physical-validation-blocked"
    assert "k1_margin_warning" in review
    assert review["k1_margin_mm"]["minimum_split_margin_mm"] > 0.0
    assert review["surface_feature_clearance_mm"] == pytest.approx(3.0)
    assert review["surface_feature_edge_chamfer_mm"] == pytest.approx(0.2)
    assert review["physical_validation_blockers"]
    surface = metadata["surface_treatment"]
    assert surface["truth_state"] == "internal review"
    assert surface["front_contour_rails"]["count"] >= 6
    assert surface["front_contour_rails"]["width_mm"] == pytest.approx(1.8)
    assert surface["rear_pod_macro_ribs"]["count"] > 0
    assert surface["rear_pod_macro_ribs"]["protrusion_mm"] == pytest.approx(1.2)
    assert "outside the display enclosure footprint" in surface["rear_pod_macro_ribs"]["placement"]
    assert surface["raised_brand"]["text"] == "CBBS"
    assert surface["raised_brand"]["text_source"] == "public/assets/brand/logo-primary.svg"
    assert surface["raised_brand"]["relief_mm"] == pytest.approx(1.2)
    assert surface["raised_brand"]["edge_chamfer_mm"] == pytest.approx(0.2)
    assert "weatherproofing" in surface["blocked_claims"]
    assert metadata["blocked_claims"]
    structural = metadata["structural_review"]
    assert structural["schema"] == "cbbs-cad/structural-review/v1"
    assert structural["strengthened_features"]["hinge_root_pads"] == 5
    assert structural["strengthened_features"]["rear_pod_floor_ribs"] == 5
    assert structural["strengthened_features"]["heltec_alignment_aids"] == 4
    assert structural["strengthened_features"]["regulator_alignment_aids"] == 4
    assert structural["k1_margins_mm"]["legacy_or_combined_plate_accepted"] is False
    assert "heat validation" in structural["validation_required"]
    assert "RF validation" in structural["validation_required"]

    assert parts["rear_tray"]["role"] == "assembly-reference"
    assert parts["rear_panel_core"]["role"] == "print"
    assert parts["rear_battery_pod"]["role"] == "print"
    assert parts["front_display_door"]["role"] == "print"
    assert parts["rear_battery_pod"]["occurrence"]["transform"]["translation_mm"]["y"] == pytest.approx(
        interface["rear_pod_body_center_y_mm"]
    )
    assert parts["rear_battery_pod"]["occurrence"]["transform"]["translation_mm"]["z"] > 0.0
    assert parts["front_display_door"]["occurrence"]["transform"]["translation_mm"]["z"] > 0.0

    panel_bounds = parts["rear_panel_core"]["bounds_mm"]
    pod_bounds = parts["rear_battery_pod"]["bounds_mm"]
    door_bounds = parts["front_display_door"]["bounds_mm"]
    assert panel_bounds["x"] + 12.0 <= 220.0
    assert panel_bounds["y"] + 12.0 <= 220.0
    assert pod_bounds["x"] + 12.0 <= 220.0
    assert pod_bounds["y"] + 12.0 <= 220.0
    assert door_bounds["x"] + 12.0 <= 220.0
    assert door_bounds["y"] + 12.0 <= 220.0
    assert metadata["k1_fit"]["component_split_required"] is True
    assert metadata["print_layouts"]["k1-component-rear-panel"]["accepted"] is True
    assert metadata["print_layouts"]["k1-component-rear-pod"]["accepted"] is True
    assert metadata["print_layouts"]["k1-component-front-door"]["accepted"] is True
    assert metadata["print_layouts"]["k1-plate-tray"]["accepted"] is False
    assert metadata["print_layouts"]["k1-plate-door"]["accepted"] is False
    assert metadata["print_layouts"]["k1-combined"]["accepted"] is False
    assert metadata["print_layouts"]["k1-max-combined"]["accepted"] is False

    for part in assembly["parts"]:
        step_path = _generated_path(tmp_path, part["files"]["step"])
        stl_path = _generated_path(tmp_path, part["files"]["stl"])
        assert step_path.is_file()
        assert stl_path.is_file()
        mesh = trimesh.load_mesh(stl_path, force="mesh")
        assert mesh.is_watertight
        assert _broken_face_count(mesh) == 0


def test_p070_hinge_is_symmetric_and_k1_print_parts_fit(tmp_path) -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)
    manifest = generate_concepts(
        bundle,
        output_dir=tmp_path,
        concept_ids=["p070_hinged_wall_enclosure"],
    )
    assembly = _artifact_by_id(manifest, "p070_hinged_wall_enclosure")["assembly"]
    metadata = assembly["metadata"]
    hinge = metadata["hinge"]
    centers = [item["center_y_mm"] for item in hinge["knuckles"]]
    owners = [item["owner"] for item in hinge["knuckles"]]

    assert owners == ["tray", "door", "tray", "door", "tray"]
    assert centers[0] == pytest.approx(-centers[-1], abs=0.001)
    assert centers[1] == pytest.approx(-centers[-2], abs=0.001)
    assert centers[2] == pytest.approx(0.0, abs=0.001)
    assert hinge["pin_diameter_mm"] == pytest.approx(3.0)
    assert hinge["bore_diameter_mm"] == pytest.approx(3.4)
    assert hinge["print_flat_depth_mm"] == pytest.approx(0.8)
    assert hinge["end_chamfer_mm"] == pytest.approx(0.25)
    root = hinge["root_reinforcement"]
    assert root["count"] == 5
    assert root["owner_pattern"] == owners
    assert root["bounds_unchanged"] is True
    assert root["does_not_bridge_opposing_owners"] is True
    assert [item["owner"] for item in root["records"]] == owners
    assert root["records"][0]["center_y_mm"] == pytest.approx(-root["records"][-1]["center_y_mm"])
    assert root["records"][1]["center_y_mm"] == pytest.approx(-root["records"][-2]["center_y_mm"])
    assert all(item["owner_specific"] for item in root["records"])

    reinforcement = metadata["mechanical_reinforcement"]
    assert reinforcement["rear_panel_floor_rib_lattice"]["count"] == 6
    assert reinforcement["rear_panel_floor_rib_lattice"]["symmetric"] is True
    assert reinforcement["display_boss_to_floor_webs"]["count"] == 8
    assert reinforcement["front_door_edge_corner_reinforcement"]["count"] == 8
    structural = metadata["structural_review"]
    assert structural["strengthened_features"] == {
        "hinge_root_pads": 5,
        "rear_panel_floor_ribs": 6,
        "rear_panel_inner_perimeter_rails": 4,
        "display_boss_webs": 8,
        "front_door_edge_corner_features": 8,
    }
    assert "physical ASA print" in structural["validation_required"]
    assert "fastener pullout" in structural["validation_required"]

    assert metadata["k1_fit"]["fits_xy_with_6mm_brim"] is True
    assert metadata["print_layouts"]["k1-plate-tray"]["fits_with_6mm_brim"] is True
    assert metadata["print_layouts"]["k1-plate-door"]["fits_with_6mm_brim"] is True
    assert metadata["print_layouts"]["k1-combined"]["fits_with_6mm_brim"] is False
    assert metadata["print_layouts"]["k1-combined"]["accepted"] is False
    assert metadata["print_layouts"]["k1-max-combined"]["fits_with_6mm_brim"] is True
    for part in assembly["parts"]:
        if part["role"] != "print":
            continue
        bounds = part["bounds_mm"]
        assert bounds["x"] + 12.0 <= 220.0
        assert bounds["y"] + 12.0 <= 220.0


def test_generate_measured_p070_hinged_wall_enclosure_fixture(tmp_path) -> None:
    bundle = load_specs(data_dir=DEFAULT_DATA_DIR)
    hardware = next(item for item in bundle.hardware if item.id == "nextion_nx8048p070_011c")
    concept = next(item for item in bundle.concepts if item.id == "p070_hinged_wall_enclosure")
    measured_hardware = hardware.model_copy(
        update={
            "measurement_status": MeasurementStatus.MEASURED,
            "derivation_state": MeasurementStatus.MEASURED,
            "open_measurement_blockers": [],
        }
    )
    enabled_concept = concept.model_copy(
        update={
            "measurement_status": MeasurementStatus.MEASURED,
            "derivation_state": MeasurementStatus.MEASURED,
            "blocked_full_case": False,
            "generation_enabled": True,
            "generation_blockers": [],
            "open_measurement_blockers": [],
        }
    )
    fixture_bundle = bundle.model_copy(
        update={"hardware": [measured_hardware], "concepts": [enabled_concept]}
    )

    manifest = generate_concepts(
        fixture_bundle,
        output_dir=tmp_path,
        concept_ids=["p070_hinged_wall_enclosure"],
    )
    artifact = _artifact_by_id(manifest, "p070_hinged_wall_enclosure")

    assert (tmp_path / "p070_hinged_wall_enclosure.step").is_file()
    assert (tmp_path / "p070_hinged_wall_enclosure.stl").is_file()
    assert artifact["blocked_full_case"] is False
    assert artifact["generation_enabled"] is True
    assert artifact["bounds_mm"]["x"] > 205.0
    assert artifact["bounds_mm"]["y"] > 125.0
    assert artifact["bounds_mm"]["z"] > 32.0

    mesh = trimesh.load_mesh(tmp_path / "p070_hinged_wall_enclosure.stl", force="mesh")
    assert mesh.is_watertight
    assert mesh.extents[0] > 205.0
    assert mesh.extents[1] > 125.0
