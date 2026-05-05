from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from math import atan2, degrees, hypot, pi
from pathlib import Path
from typing import Any

from cbbs_cad.models import ConceptSpec, HardwareSpec, SpecBundle
from cbbs_cad.primitives import (
    add_box_feature,
    add_cylindrical_boss,
    box,
    rectangular_ring,
    rounded_plate,
)
from cbbs_cad.specs import REPO_ROOT

DEFAULT_OUTPUT_DIR = REPO_ROOT / "3d-print-work" / "generated" / "cad"


@dataclass(frozen=True)
class GeneratedAssemblyPart:
    id: str
    name: str
    model: Any
    role: str
    material_hint: str
    notes: str | None = None
    occurrence: dict[str, Any] = field(default_factory=dict)
    support_risk: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GeneratedAssembly:
    parts: list[GeneratedAssemblyPart]
    views: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GeneratedModel:
    model: Any
    assembly: GeneratedAssembly | None = None


def _require_cadquery() -> Any:
    try:
        import cadquery as cq
    except ImportError as exc:
        raise RuntimeError(
            "CadQuery is required for generation. Run "
            "`uv run --project tools/cad cbbs-cad generate` from the repo root."
        ) from exc
    return cq


def _number(params: dict[str, Any], name: str, default: float) -> float:
    value = params.get(name, default)
    if not isinstance(value, int | float):
        raise ValueError(f"parameter {name} must be numeric")
    return float(value)


def _integer(params: dict[str, Any], name: str, default: int) -> int:
    value = params.get(name, default)
    if not isinstance(value, int):
        raise ValueError(f"parameter {name} must be an integer")
    return value


def _number_list(params: dict[str, Any], name: str, default: list[float]) -> list[float]:
    value = params.get(name, default)
    if not isinstance(value, list) or not value:
        raise ValueError(f"parameter {name} must be a non-empty numeric list")
    numbers: list[float] = []
    for item in value:
        if not isinstance(item, int | float):
            raise ValueError(f"parameter {name} must be a non-empty numeric list")
        numbers.append(float(item))
    return numbers


def _box(cq: Any, x: float, y: float, z: float) -> Any:
    return box(cq, x, y, z)


def _combine_models(cq: Any, models: list[Any]) -> Any:
    if not models:
        raise ValueError("at least one model is required")
    combined = models[0]
    for model in models[1:]:
        combined = combined.union(model)
    return combined


def _model_bounds_mm(model: Any) -> dict[str, float]:
    bb = model.val().BoundingBox()
    return {
        "x": round(float(bb.xlen), 4),
        "y": round(float(bb.ylen), 4),
        "z": round(float(bb.zlen), 4),
    }


def _fits_single_plate(
    bounds: dict[str, float],
    plate_x: float,
    plate_y: float,
    brim_margin_each_side: float,
) -> bool:
    return (
        bounds["x"] + brim_margin_each_side * 2 <= plate_x
        and bounds["y"] + brim_margin_each_side * 2 <= plate_y
    )


def _fits_two_part_plate(
    first: dict[str, float],
    second: dict[str, float],
    plate_x: float,
    plate_y: float,
    brim_margin_each_side: float,
    spacing: float,
) -> dict[str, Any]:
    side_by_side_bounds = {
        "x": round(first["x"] + second["x"] + spacing, 4),
        "y": round(max(first["y"], second["y"]), 4),
    }
    stacked_bounds = {
        "x": round(max(first["x"], second["x"]), 4),
        "y": round(first["y"] + second["y"] + spacing, 4),
    }
    side_by_side_fits = _fits_single_plate(side_by_side_bounds, plate_x, plate_y, brim_margin_each_side)
    stacked_fits = _fits_single_plate(stacked_bounds, plate_x, plate_y, brim_margin_each_side)
    return {
        "side_by_side_bounds_mm": side_by_side_bounds,
        "side_by_side_fits": side_by_side_fits,
        "stacked_bounds_mm": stacked_bounds,
        "stacked_fits": stacked_fits,
        "fits_with_6mm_brim": side_by_side_fits or stacked_fits,
        "selected_orientation": "stacked-y" if stacked_fits else None,
    }


def _transform_about_hinge(model: Any, hinge_x: float, hinge_z: float, angle_degrees: float) -> Any:
    return model.rotate((hinge_x, 0, hinge_z), (hinge_x, 1, hinge_z), angle_degrees)


def _build_heltec_fit_card(cq: Any, concept: ConceptSpec, hardware: HardwareSpec) -> Any:
    d = hardware.dimensions
    thickness = _number(concept.parameters, "card_thickness_mm", 1.6)
    model = _box(cq, d["board_length_mm"], d["board_width_mm"], thickness)

    usb_relief_width = _number(concept.parameters, "usb_relief_width_mm", 8.0)
    usb_relief_depth = _number(concept.parameters, "usb_relief_depth_mm", 3.0)
    model = (
        model.faces(">Z")
        .workplane()
        .center(-d["board_length_mm"] / 2 + usb_relief_depth / 2, 0)
        .rect(usb_relief_depth, usb_relief_width)
        .cutThruAll()
    )
    return model


def _build_p070_fit_frame(cq: Any, concept: ConceptSpec, hardware: HardwareSpec) -> Any:
    d = hardware.dimensions
    thickness = _number(concept.parameters, "frame_thickness_mm", 2.0)
    opening_margin = _number(concept.parameters, "active_area_margin_mm", 0.6)

    model = _box(cq, d["outsize_x_mm"], d["outsize_y_mm"], thickness)
    model = (
        model.faces(">Z")
        .workplane()
        .rect(
            d["active_area_x_mm"] + (opening_margin * 2),
            d["active_area_y_mm"] + (opening_margin * 2),
        )
        .cutThruAll()
    )

    hole_span_x = d["mount_hole_span_x_mm"]
    hole_span_y = d["mount_hole_span_y_mm"]
    hole_points = [
        (-hole_span_x / 2, -hole_span_y / 2),
        (-hole_span_x / 2, hole_span_y / 2),
        (hole_span_x / 2, -hole_span_y / 2),
        (hole_span_x / 2, hole_span_y / 2),
    ]
    model = (
        model.faces(">Z")
        .workplane()
        .pushPoints(hole_points)
        .hole(d["mount_hole_diameter_mm"])
    )
    return model


def _build_rugged_wall_section_coupon(cq: Any, concept: ConceptSpec) -> Any:
    params = concept.parameters
    length = _number(params, "length_mm", 80.0)
    width = _number(params, "width_mm", 50.0)
    wall = _number(params, "wall_thickness_mm", 3.0)
    corner = _number(params, "corner_radius_mm", 3.0)
    rib_width = _number(params, "rib_width_mm", 4.0)
    rib_height = _number(params, "rib_height_mm", 4.0)
    rib_inset = _number(params, "rib_inset_mm", 8.0)

    model = rounded_plate(cq, length, width, wall, corner)
    rail_length = max(rib_width, length - (rib_inset * 2))
    rail_y = max(0.0, width / 2 - rib_inset)
    for y in (-rail_y, rail_y):
        model = add_box_feature(model, cq, rail_length, rib_width, rib_height, 0, y, wall)

    rib_span = max(rib_width, width - (rib_inset * 2))
    for x in (-length / 4, length / 4):
        model = add_box_feature(model, cq, rib_width, rib_span, rib_height, x, 0, wall)
    return model


def _build_gasket_flange_coupon(cq: Any, concept: ConceptSpec) -> Any:
    params = concept.parameters
    outer_x = _number(params, "outer_x_mm", 90.0)
    outer_y = _number(params, "outer_y_mm", 58.0)
    opening_x = _number(params, "opening_x_mm", 62.0)
    opening_y = _number(params, "opening_y_mm", 30.0)
    thickness = _number(params, "flange_thickness_mm", 4.0)
    corner = _number(params, "corner_radius_mm", 3.0)
    groove_outer_x = _number(params, "gasket_groove_outer_x_mm", 80.0)
    groove_outer_y = _number(params, "gasket_groove_outer_y_mm", 48.0)
    groove_inner_x = _number(params, "gasket_groove_inner_x_mm", 68.0)
    groove_inner_y = _number(params, "gasket_groove_inner_y_mm", 36.0)
    groove_depth = _number(params, "gasket_groove_depth_mm", 1.0)
    screw_span_x = _number(params, "screw_span_x_mm", 78.0)
    screw_span_y = _number(params, "screw_span_y_mm", 46.0)
    screw_hole = _number(params, "screw_clearance_diameter_mm", 3.4)

    model = rectangular_ring(cq, outer_x, outer_y, opening_x, opening_y, thickness, corner)
    model = (
        model.faces(">Z")
        .workplane()
        .rect(groove_outer_x, groove_outer_y)
        .rect(groove_inner_x, groove_inner_y)
        .cutBlind(-groove_depth)
    )
    points = [
        (-screw_span_x / 2, -screw_span_y / 2),
        (-screw_span_x / 2, screw_span_y / 2),
        (screw_span_x / 2, -screw_span_y / 2),
        (screw_span_x / 2, screw_span_y / 2),
    ]
    return model.faces(">Z").workplane().pushPoints(points).hole(screw_hole)


def _build_reinforced_mount_tab_coupon(cq: Any, concept: ConceptSpec) -> Any:
    params = concept.parameters
    body_x = _number(params, "body_x_mm", 60.0)
    body_y = _number(params, "body_y_mm", 36.0)
    tab_x = _number(params, "tab_x_mm", 22.0)
    tab_y = _number(params, "tab_y_mm", 26.0)
    thickness = _number(params, "base_thickness_mm", 3.0)
    corner = _number(params, "corner_radius_mm", 2.0)
    boss_outer = _number(params, "boss_outer_diameter_mm", 14.0)
    boss_height = _number(params, "boss_height_mm", 4.0)
    mount_hole = _number(params, "mount_hole_diameter_mm", 5.0)
    rib_width = _number(params, "rib_width_mm", 3.0)
    rib_height = _number(params, "rib_height_mm", 4.0)
    rib_length = _number(params, "rib_length_mm", 20.0)

    model = rounded_plate(cq, body_x, body_y, thickness, corner)
    tab_center_x = body_x / 2 + tab_x / 2
    model = model.union(rounded_plate(cq, tab_x, tab_y, thickness, corner).translate((tab_center_x, 0, 0)))
    model = add_cylindrical_boss(
        model, cq, tab_center_x, 0, boss_outer, boss_height, thickness
    )
    rib_center_x = body_x / 2 + rib_length / 2 - 2
    rib_y = max(0.0, tab_y / 2 - rib_width)
    for y in (-rib_y, rib_y):
        model = add_box_feature(
            model, cq, rib_length, rib_width, rib_height, rib_center_x, y, thickness
        )
    return model.faces(">Z").workplane().center(tab_center_x, 0).hole(mount_hole)


def _build_cable_entry_boss_coupon(cq: Any, concept: ConceptSpec) -> Any:
    params = concept.parameters
    plate_x = _number(params, "plate_x_mm", 70.0)
    plate_y = _number(params, "plate_y_mm", 45.0)
    wall = _number(params, "wall_thickness_mm", 4.0)
    corner = _number(params, "corner_radius_mm", 3.0)
    boss_outer = _number(params, "boss_outer_diameter_mm", 24.0)
    boss_height = _number(params, "boss_height_mm", 8.0)
    cable_hole = _number(params, "cable_clearance_diameter_mm", 8.0)
    rib_width = _number(params, "rib_width_mm", 4.0)
    rib_height = _number(params, "rib_height_mm", 4.0)
    rib_length = _number(params, "rib_length_mm", 18.0)

    model = rounded_plate(cq, plate_x, plate_y, wall, corner)
    model = add_cylindrical_boss(model, cq, 0, 0, boss_outer, boss_height, wall, cable_hole)

    x_offset = min(boss_outer / 2 + rib_length / 2 - 1, plate_x / 2 - rib_length / 2 - 2)
    y_offset = min(boss_outer / 2 + rib_length / 2 - 1, plate_y / 2 - rib_length / 2 - 2)
    for x in (-x_offset, x_offset):
        model = add_box_feature(model, cq, rib_length, rib_width, rib_height, x, 0, wall)
    for y in (-y_offset, y_offset):
        model = add_box_feature(model, cq, rib_width, rib_length, rib_height, 0, y, wall)
    return model.faces(">Z").workplane().hole(cable_hole)


def _build_npt_3_4_thread_fit_coupon(cq: Any, concept: ConceptSpec) -> Any:
    params = concept.parameters
    plate_x = _number(params, "coupon_plate_x_mm", 118.0)
    plate_y = _number(params, "coupon_plate_y_mm", 58.0)
    wall = _number(params, "coupon_wall_thickness_mm", 6.0)
    corner = _number(params, "coupon_corner_radius_mm", 3.0)
    boss_outer = _number(params, "npt_boss_outer_diameter_mm", 44.0)
    thread_depth = _number(params, "npt_thread_depth_mm", 15.0)
    major_diameter = _number(params, "npt_thread_major_diameter_mm", 26.67)
    threads_per_inch = _number(params, "npt_threads_per_inch", 14.0)
    taper = _number(params, "npt_taper_diameter_per_length_mm_per_mm", 0.0625)
    clearances = _number_list(params, "npt_thread_clearance_variants_mm", [0.35, 0.55])

    model = rounded_plate(cq, plate_x, plate_y, wall, corner)
    spacing = plate_x / (len(clearances) + 1)
    centers = [(-plate_x / 2 + spacing * (index + 1), 0.0) for index in range(len(clearances))]
    for center, clearance in zip(centers, clearances, strict=True):
        cut_depth = wall + 0.8
        bore_geometry = _npt_thread_geometry(
            major_diameter,
            threads_per_inch,
            taper,
            clearance,
            cut_depth,
        )
        wall_cut = cq.Solid.makeCone(
            float(bore_geometry["minor_radius_start_mm"]),
            float(bore_geometry["minor_radius_end_mm"]),
            cut_depth,
            pnt=cq.Vector(center[0], center[1], -0.4),
            dir=cq.Vector(0, 0, 1),
        )
        model = model.cut(wall_cut)
        boss, _record = _build_segmented_npt_boss_z(
            cq,
            boss_outer,
            thread_depth,
            major_diameter,
            threads_per_inch,
            taper,
            clearance,
        )
        model = model.union(boss.translate((center[0], center[1], wall)))

    label_rail_width = 1.2
    for center, clearance in zip(centers, clearances, strict=True):
        marker_length = max(8.0, min(18.0, boss_outer * 0.35 + clearance * 6))
        model = add_box_feature(
            model,
            cq,
            marker_length,
            label_rail_width,
            0.8,
            center[0],
            -plate_y / 2 + 7.0,
            wall,
        )
    return model


def _build_drip_lip_seam_coupon(cq: Any, concept: ConceptSpec) -> Any:
    params = concept.parameters
    base_x = _number(params, "base_x_mm", 80.0)
    base_y = _number(params, "base_y_mm", 40.0)
    base_thickness = _number(params, "base_thickness_mm", 3.0)
    corner = _number(params, "corner_radius_mm", 3.0)
    wall_outer_x = _number(params, "inner_wall_outer_x_mm", 68.0)
    wall_outer_y = _number(params, "inner_wall_outer_y_mm", 28.0)
    wall_opening_x = _number(params, "inner_wall_opening_x_mm", 58.0)
    wall_opening_y = _number(params, "inner_wall_opening_y_mm", 18.0)
    wall_height = _number(params, "inner_wall_height_mm", 4.0)
    lip_outer_x = _number(params, "lip_outer_x_mm", 76.0)
    lip_outer_y = _number(params, "lip_outer_y_mm", 36.0)
    lip_opening_x = _number(params, "lip_opening_x_mm", 66.0)
    lip_opening_y = _number(params, "lip_opening_y_mm", 26.0)
    lip_height = _number(params, "lip_height_mm", 2.0)

    model = rounded_plate(cq, base_x, base_y, base_thickness, corner)
    wall = rectangular_ring(cq, wall_outer_x, wall_outer_y, wall_opening_x, wall_opening_y, wall_height)
    lip = rectangular_ring(cq, lip_outer_x, lip_outer_y, lip_opening_x, lip_opening_y, lip_height)
    model = model.union(wall.translate((0, 0, base_thickness)))
    model = model.union(lip.translate((0, 0, base_thickness + wall_height)))
    return model.faces(">Z").workplane().rect(wall_opening_x, wall_opening_y).cutThruAll()


def _build_p070_rugged_bezel_fit_frame(
    cq: Any, concept: ConceptSpec, hardware: HardwareSpec
) -> Any:
    d = hardware.dimensions
    params = concept.parameters
    border = _number(params, "border_overhang_mm", 12.0)
    thickness = _number(params, "frame_thickness_mm", 4.0)
    opening_margin = _number(params, "active_area_margin_mm", 0.8)
    corner = _number(params, "corner_radius_mm", 4.0)
    lip_width = _number(params, "raised_lip_width_mm", 3.0)
    lip_height = _number(params, "raised_lip_height_mm", 1.5)
    hole_clearance = _number(params, "mount_hole_clearance_mm", 0.4)

    outer_x = d["outsize_x_mm"] + border * 2
    outer_y = d["outsize_y_mm"] + border * 2
    opening_x = d["active_area_x_mm"] + opening_margin * 2
    opening_y = d["active_area_y_mm"] + opening_margin * 2
    model = rectangular_ring(cq, outer_x, outer_y, opening_x, opening_y, thickness, corner)
    lip = rectangular_ring(
        cq,
        opening_x + lip_width * 2,
        opening_y + lip_width * 2,
        opening_x,
        opening_y,
        lip_height,
    )
    model = model.union(lip.translate((0, 0, thickness)))

    hole_span_x = d["mount_hole_span_x_mm"]
    hole_span_y = d["mount_hole_span_y_mm"]
    hole_points = [
        (-hole_span_x / 2, -hole_span_y / 2),
        (-hole_span_x / 2, hole_span_y / 2),
        (hole_span_x / 2, -hole_span_y / 2),
        (hole_span_x / 2, hole_span_y / 2),
    ]
    return (
        model.faces(">Z")
        .workplane()
        .pushPoints(hole_points)
        .hole(d["mount_hole_diameter_mm"] + hole_clearance)
    )


def _cylinder_y(
    cq: Any,
    center_x: float,
    y_start: float,
    center_z: float,
    outer_diameter: float,
    length: float,
    hole_diameter: float | None = None,
) -> Any:
    profile = cq.Workplane("XZ").center(center_x, center_z).circle(outer_diameter / 2)
    if hole_diameter:
        profile = profile.circle(hole_diameter / 2)
    return profile.extrude(length).translate((0, y_start, 0))


def _cone_y(
    cq: Any,
    center_x: float,
    y_start: float,
    center_z: float,
    start_diameter: float,
    end_diameter: float,
    length: float,
) -> Any:
    cone = cq.Solid.makeCone(
        start_diameter / 2,
        end_diameter / 2,
        length,
        pnt=cq.Vector(0, 0, 0),
        dir=cq.Vector(0, 0, 1),
    )
    return cq.Workplane("XY").add(cone).rotate((0, 0, 0), (1, 0, 0), -90).translate(
        (center_x, y_start, center_z)
    )


def _npt_thread_geometry(
    major_diameter: float,
    threads_per_inch: float,
    taper_diameter_per_length: float,
    clearance: float,
    depth: float,
) -> dict[str, float | int]:
    pitch = 25.4 / threads_per_inch
    taper_radius_per_length = taper_diameter_per_length / 2
    thread_radial_depth = min(1.25, pitch * 0.68)
    minor_radius_start = major_diameter / 2 - thread_radial_depth + clearance
    radial_width = max(0.9, min(1.15, pitch * 0.62))
    tangential_width = max(1.6, min(2.3, pitch * 1.2))
    axial_width = max(0.55, min(0.9, pitch * 0.45))
    turns = depth / pitch
    segments_per_turn = 6
    segment_count = max(12, int(turns * segments_per_turn))
    return {
        "pitch_mm": round(pitch, 4),
        "minor_radius_start_mm": minor_radius_start,
        "minor_radius_end_mm": minor_radius_start + taper_radius_per_length * depth,
        "taper_radius_per_length_mm_per_mm": taper_radius_per_length,
        "thread_radial_depth_mm": round(thread_radial_depth, 4),
        "ridge_radial_width_mm": round(radial_width, 4),
        "ridge_tangential_width_mm": round(tangential_width, 4),
        "ridge_axial_width_mm": round(axial_width, 4),
        "turns": round(turns, 4),
        "segments_per_turn": segments_per_turn,
        "segment_count": segment_count,
    }


def _build_segmented_npt_boss_z(
    cq: Any,
    outer_diameter: float,
    depth: float,
    major_diameter: float,
    threads_per_inch: float,
    taper_diameter_per_length: float,
    clearance: float,
) -> tuple[Any, dict[str, Any]]:
    if threads_per_inch <= 0:
        raise ValueError("NPT threads_per_inch must be positive")
    if depth <= 0 or outer_diameter <= major_diameter:
        raise ValueError("NPT boss dimensions must be positive and larger than the thread")
    geometry = _npt_thread_geometry(
        major_diameter,
        threads_per_inch,
        taper_diameter_per_length,
        clearance,
        depth,
    )
    model = cq.Workplane("XY").circle(outer_diameter / 2).extrude(depth)
    bore = cq.Solid.makeCone(
        float(geometry["minor_radius_start_mm"]),
        float(geometry["minor_radius_end_mm"]),
        depth + 0.6,
        pnt=cq.Vector(0, 0, -0.3),
        dir=cq.Vector(0, 0, 1),
    )
    model = model.cut(bore)

    turns = float(geometry["turns"])
    segment_count = int(geometry["segment_count"])
    taper_radius_per_length = float(geometry["taper_radius_per_length_mm_per_mm"])
    minor_radius_start = float(geometry["minor_radius_start_mm"])
    radial_width = float(geometry["ridge_radial_width_mm"])
    tangential_width = float(geometry["ridge_tangential_width_mm"])
    axial_width = float(geometry["ridge_axial_width_mm"])
    for index in range(segment_count):
        t = (index + 0.5) / segment_count
        theta = 2 * pi * turns * t
        z = depth * t
        radius = minor_radius_start + taper_radius_per_length * z + radial_width * 0.32
        pad = (
            cq.Workplane("XY")
            .box(radial_width, tangential_width, axial_width, centered=(True, True, True))
            .translate((radius, 0, z))
            .rotate((0, 0, 0), (0, 0, 1), degrees(theta))
        )
        model = model.union(pad)

    return model, {
        "thread_form": "segmented-helical-internal-ridges",
        "clearance_mm": round(clearance, 4),
        "major_diameter_mm": round(major_diameter, 4),
        "threads_per_inch": round(threads_per_inch, 4),
        "pitch_mm": geometry["pitch_mm"],
        "depth_mm": round(depth, 4),
        "taper_diameter_per_length_mm_per_mm": round(taper_diameter_per_length, 6),
        "ridge_segment_count": segment_count,
        "segments_per_turn": geometry["segments_per_turn"],
        "validation_status": "coupon-and-physical-gland-fit-required",
    }


def _build_segmented_npt_boss_y(
    cq: Any,
    center_x: float,
    y_start: float,
    center_z: float,
    outer_diameter: float,
    depth: float,
    major_diameter: float,
    threads_per_inch: float,
    taper_diameter_per_length: float,
    clearance: float,
) -> tuple[Any, dict[str, Any]]:
    boss_z, record = _build_segmented_npt_boss_z(
        cq,
        outer_diameter,
        depth,
        major_diameter,
        threads_per_inch,
        taper_diameter_per_length,
        clearance,
    )
    boss_y = boss_z.rotate((0, 0, 0), (1, 0, 0), -90).translate((center_x, y_start, center_z))
    return boss_y, record


def _npt_wall_cut_y(
    cq: Any,
    center_x: float,
    y_start: float,
    center_z: float,
    depth: float,
    major_diameter: float,
    threads_per_inch: float,
    taper_diameter_per_length: float,
    clearance: float,
) -> Any:
    geometry = _npt_thread_geometry(
        major_diameter,
        threads_per_inch,
        taper_diameter_per_length,
        clearance,
        depth,
    )
    return _cone_y(
        cq,
        center_x,
        y_start,
        center_z,
        float(geometry["minor_radius_start_mm"]) * 2,
        float(geometry["minor_radius_end_mm"]) * 2,
        depth,
    )


def _hinge_barrel_y(
    cq: Any,
    center_x: float,
    y_start: float,
    center_z: float,
    outer_diameter: float,
    length: float,
    hole_diameter: float,
    flat_depth: float,
    end_chamfer: float,
) -> Any:
    barrel = _cylinder_y(cq, center_x, y_start, center_z, outer_diameter, length, hole_diameter)
    if flat_depth > 0:
        flat_cut = _box(cq, outer_diameter + 2.0, length + 0.4, flat_depth + 0.6).translate(
            (
                center_x,
                y_start + length / 2,
                center_z - outer_diameter / 2 + (flat_depth - 0.6) / 2,
            )
        )
        barrel = barrel.cut(flat_cut)
    if end_chamfer > 0:
        try:
            barrel = barrel.edges("%Circle").chamfer(end_chamfer)
        except Exception:
            pass
    return barrel


def _build_p070_hinged_wall_enclosure(
    cq: Any, concept: ConceptSpec, hardware: HardwareSpec
) -> GeneratedModel:
    d = hardware.dimensions
    params = concept.parameters
    wall = _number(params, "wall_thickness_mm", 3.2)
    side_clearance = _number(params, "display_side_clearance_mm", 5.0)
    floor = _number(params, "floor_thickness_mm", 3.2)
    rear_depth = _number(params, "rear_clearance_depth_mm", 26.0)
    door_thickness = _number(params, "front_door_thickness_mm", 3.2)
    door_gap = _number(params, "door_gap_mm", 1.0)
    corner = _number(params, "corner_radius_mm", 4.0)
    rib_width = _number(params, "asa_rib_width_mm", 1.6)
    rib_height = _number(params, "asa_rib_height_mm", 2.4)

    cavity_x = d["outsize_x_mm"] + side_clearance * 2
    cavity_y = d["outsize_y_mm"] + side_clearance * 2
    outer_x = cavity_x + wall * 2
    outer_y = cavity_y + wall * 2
    shell_z = floor + rear_depth
    door_z = shell_z + door_gap
    door_top_z = door_z + door_thickness

    tray = rounded_plate(cq, outer_x, outer_y, shell_z, corner)
    tray = tray.faces(">Z").workplane().rect(cavity_x, cavity_y).cutBlind(-rear_depth)

    boss_outer = _number(params, "display_mount_boss_outer_diameter_mm", 8.0)
    boss_height = _number(params, "display_mount_boss_height_mm", 6.0)
    boss_clearance_hole = _number(params, "display_mount_hole_clearance_diameter_mm", 3.4)
    display_mount_thread_mode = str(params.get("display_mount_thread_mode", "m3_printed_pilot"))
    display_mount_thread_nominal = str(params.get("display_mount_thread_nominal", "M3x0.5"))
    display_mount_thread_pilot = _number(params, "display_mount_thread_pilot_diameter_mm", 2.6)
    if display_mount_thread_mode != "m3_printed_pilot":
        raise ValueError(
            "display_mount_thread_mode must be 'm3_printed_pilot' for generated P070 trays"
        )
    if display_mount_thread_pilot >= d["mount_hole_diameter_mm"]:
        raise ValueError("display_mount_thread_pilot_diameter_mm must be smaller than display holes")
    boss_hole = display_mount_thread_pilot
    hole_span_x = d["mount_hole_span_x_mm"]
    hole_span_y = d["mount_hole_span_y_mm"]
    display_mount_points = [
        {"x": round(x, 4), "y": round(y, 4)}
        for x in (-hole_span_x / 2, hole_span_x / 2)
        for y in (-hole_span_y / 2, hole_span_y / 2)
    ]
    for point in display_mount_points:
        x = point["x"]
        y = point["y"]
        tray = add_cylindrical_boss(tray, cq, x, y, boss_outer, boss_height, floor, boss_hole)

    display_boss_web_records: list[dict[str, Any]] = []
    boss_web_length = max(wall * 2, boss_outer * 0.8)
    boss_web_overlap = min(0.4, rib_width / 4)
    for point in display_mount_points:
        x = point["x"]
        y = point["y"]
        sx = 1.0 if x >= 0 else -1.0
        sy = 1.0 if y >= 0 else -1.0
        x_web_center = x + sx * (boss_outer / 2 + boss_web_length / 2 - boss_web_overlap)
        y_web_center = y + sy * (boss_outer / 2 + boss_web_length / 2 - boss_web_overlap)
        tray = add_box_feature(
            tray,
            cq,
            boss_web_length,
            rib_width,
            rib_height,
            x_web_center,
            y,
            floor,
        )
        tray = add_box_feature(
            tray,
            cq,
            rib_width,
            boss_web_length,
            rib_height,
            x,
            y_web_center,
            floor,
        )
        display_boss_web_records.append(
            {
                "boss_x_mm": round(x, 4),
                "boss_y_mm": round(y, 4),
                "webs": ["outboard-x", "outboard-y"],
                "web_length_mm": round(boss_web_length, 4),
                "web_width_mm": round(rib_width, 4),
                "web_height_mm": round(rib_height, 4),
            }
        )

    rib_span_x = max(0.0, cavity_x - boss_outer * 4)
    rib_span_y = max(0.0, cavity_y - boss_outer * 4)
    floor_lattice_records: list[dict[str, Any]] = []
    if rib_span_x > 20:
        for y in (-cavity_y / 3, 0.0, cavity_y / 3):
            tray = add_box_feature(tray, cq, rib_span_x, rib_width, rib_height, 0, y, floor)
            floor_lattice_records.append(
                {
                    "axis": "X",
                    "center_x_mm": 0.0,
                    "center_y_mm": round(y, 4),
                    "length_mm": round(rib_span_x, 4),
                }
            )
    if rib_span_y > 20:
        for x in (-cavity_x / 3, 0.0, cavity_x / 3):
            tray = add_box_feature(tray, cq, rib_width, rib_span_y, rib_height, x, 0, floor)
            floor_lattice_records.append(
                {
                    "axis": "Y",
                    "center_x_mm": round(x, 4),
                    "center_y_mm": 0.0,
                    "length_mm": round(rib_span_y, 4),
                }
            )

    inner_perimeter_rail_records: list[dict[str, Any]] = []
    rail_wall_overlap = min(0.3, rib_width / 4)
    rail_outer_x = cavity_x + rail_wall_overlap * 2
    rail_outer_y = cavity_y + rail_wall_overlap * 2
    rail_inner_x = max(rib_width, cavity_x - rib_width * 2)
    rail_inner_y = max(rib_width, cavity_y - rib_width * 2)
    rail = rectangular_ring(cq, rail_outer_x, rail_outer_y, rail_inner_x, rail_inner_y, rib_height)
    tray = tray.union(rail.translate((0, 0, floor)))
    rail_x_length = rail_outer_x
    rail_y_length = rail_outer_y
    rail_y_offset = (rail_outer_y + rail_inner_y) / 4
    rail_x_offset = (rail_outer_x + rail_inner_x) / 4
    for y in (-rail_y_offset, rail_y_offset):
        inner_perimeter_rail_records.append(
            {
                "axis": "X",
                "center_y_mm": round(y, 4),
                "length_mm": round(rail_x_length, 4),
            }
        )
    for x in (-rail_x_offset, rail_x_offset):
        inner_perimeter_rail_records.append(
            {
                "axis": "Y",
                "center_x_mm": round(x, 4),
                "length_mm": round(rail_y_length, 4),
            }
        )

    wall_hole = _number(params, "wall_mount_hole_diameter_mm", 4.5)
    wall_inset_x = _number(params, "wall_mount_inset_x_mm", 18.0)
    wall_inset_y = _number(params, "wall_mount_inset_y_mm", 16.0)
    wall_points = [
        (-outer_x / 2 + wall_inset_x, -outer_y / 2 + wall_inset_y),
        (-outer_x / 2 + wall_inset_x, outer_y / 2 - wall_inset_y),
        (outer_x / 2 - wall_inset_x, -outer_y / 2 + wall_inset_y),
        (outer_x / 2 - wall_inset_x, outer_y / 2 - wall_inset_y),
    ]
    tray = tray.faces("<Z").workplane().pushPoints(wall_points).hole(wall_hole)

    cable_boss_outer = _number(params, "bottom_gland_boss_outer_diameter_mm", 22.0)
    cable_hole = _number(params, "bottom_gland_clearance_diameter_mm", 12.4)
    cable_length = _number(params, "bottom_gland_boss_length_mm", 8.0)
    gland_outer = _number(params, "bottom_gland_reference_outer_diameter_mm", 16.6)
    gland_length = _number(params, "bottom_gland_reference_length_mm", 30.0)
    gland_cable_hole = _number(params, "bottom_gland_reference_cable_range_max_mm", 7.0)
    cable_z = floor + rear_depth / 2
    cable_boss = _cylinder_y(
        cq,
        0,
        -outer_y / 2 - cable_length,
        cable_z,
        cable_boss_outer,
        cable_length + wall,
        cable_hole,
    )
    cable_cut = _cylinder_y(
        cq,
        0,
        -outer_y / 2 - cable_length - 0.2,
        cable_z,
        cable_hole,
        wall + cable_length + 0.4,
    )
    tray = tray.union(cable_boss).cut(cable_cut)

    window_clearance = _number(params, "display_window_clearance_mm", 1.0)
    window_x = min(d["lcd_outsize_x_mm"] - 0.8, d["active_area_x_mm"] + window_clearance * 2)
    window_y = min(d["lcd_outsize_y_mm"] - 0.8, d["active_area_y_mm"] + window_clearance * 2)
    door = rectangular_ring(cq, outer_x, outer_y, window_x, window_y, door_thickness, corner)
    door = door.translate((0, 0, door_z))

    door_reinforcement_records: list[dict[str, Any]] = []
    edge_rail_offset_y = window_y / 2 + wall / 2
    edge_rail_offset_x = window_x / 2 + wall / 2
    for y in (-edge_rail_offset_y, edge_rail_offset_y):
        door = add_box_feature(door, cq, window_x, rib_width, rib_height, 0, y, door_top_z)
        door_reinforcement_records.append(
            {
                "kind": "edge_rail",
                "axis": "X",
                "center_y_mm": round(y, 4),
                "outside_display_window": True,
            }
        )
    for x in (-edge_rail_offset_x, edge_rail_offset_x):
        door = add_box_feature(door, cq, rib_width, window_y, rib_height, x, 0, door_top_z)
        door_reinforcement_records.append(
            {
                "kind": "edge_rail",
                "axis": "Y",
                "center_x_mm": round(x, 4),
                "outside_display_window": True,
            }
        )
    corner_pad_x = max(wall * 2, rib_width * 4)
    corner_pad_y = max(wall * 2, rib_width * 4)
    corner_pad_center_x = window_x / 2 + wall + corner_pad_x / 2
    corner_pad_center_y = window_y / 2 + wall + corner_pad_y / 2
    for x in (-corner_pad_center_x, corner_pad_center_x):
        for y in (-corner_pad_center_y, corner_pad_center_y):
            door = add_box_feature(
                door,
                cq,
                corner_pad_x,
                corner_pad_y,
                rib_height,
                x,
                y,
                door_top_z,
            )
            door_reinforcement_records.append(
                {
                    "kind": "corner_pad",
                    "center_x_mm": round(x, 4),
                    "center_y_mm": round(y, 4),
                    "outside_display_window": True,
                }
            )

    hinge_outer = _number(params, "hinge_barrel_outer_diameter_mm", 8.8)
    hinge_pin = _number(params, "hinge_pin_diameter_mm", 3.0)
    hinge_bore = _number(params, "hinge_pin_clearance_diameter_mm", 3.4)
    hinge_length = _number(params, "hinge_barrel_length_mm", 18.0)
    hinge_gap = _number(params, "hinge_barrel_gap_mm", 1.2)
    hinge_count = _integer(params, "hinge_knuckle_count", 5)
    hinge_flat_depth = _number(params, "hinge_barrel_print_flat_depth_mm", 0.8)
    hinge_end_chamfer = _number(params, "hinge_barrel_end_chamfer_mm", 0.25)
    if hinge_count < 3 or hinge_count % 2 == 0:
        raise ValueError("hinge_knuckle_count must be an odd integer >= 3")
    hinge_x = -outer_x / 2 - hinge_outer / 2 + min(1.2, hinge_outer / 4)
    hinge_z = door_z + door_thickness / 2
    total_hinge_span = hinge_count * hinge_length + (hinge_count - 1) * hinge_gap
    if total_hinge_span >= outer_y:
        raise ValueError("hinge knuckles exceed enclosure height")
    hinge_y_start = -total_hinge_span / 2
    hinge_records = []
    for index in range(hinge_count):
        y_start = hinge_y_start + index * (hinge_length + hinge_gap)
        center_y = y_start + hinge_length / 2
        owner = "tray" if index % 2 == 0 else "door"
        hinge = _hinge_barrel_y(
            cq,
            hinge_x,
            y_start,
            hinge_z,
            hinge_outer,
            hinge_length,
            hinge_bore,
            hinge_flat_depth,
            hinge_end_chamfer,
        )
        if owner == "tray":
            tray = tray.union(hinge)
        else:
            door = door.union(hinge)
        hinge_records.append(
            {
                "index": index,
                "owner": owner,
                "center_y_mm": round(center_y, 4),
                "length_mm": round(hinge_length, 4),
            }
        )

    hinge_pre_root_pad_bounds = {
        "rear_tray": _model_bounds_mm(tray),
        "front_display_door": _model_bounds_mm(door),
    }
    hinge_root_pad_records: list[dict[str, Any]] = []
    root_pad_y_trim = min(0.6, hinge_gap / 2)
    root_pad_y_length = max(rib_width, hinge_length - root_pad_y_trim * 2)
    root_pad_x_min = hinge_x - hinge_outer / 2 + min(0.4, rib_width / 4)
    root_pad_x_max = -outer_x / 2 + min(1.0, wall / 3)
    root_pad_x_length = max(rib_width, root_pad_x_max - root_pad_x_min)
    root_pad_x_center = root_pad_x_min + root_pad_x_length / 2
    root_pad_z_base = hinge_z - hinge_outer / 2 + max(0.0, hinge_flat_depth - 0.1)
    root_pad_z_height = max(rib_height, hinge_outer - hinge_flat_depth)
    for record in hinge_records:
        y_center = record["center_y_mm"]
        pad = _box(cq, root_pad_x_length, root_pad_y_length, root_pad_z_height).translate(
            (root_pad_x_center, y_center, root_pad_z_base)
        )
        if record["owner"] == "tray":
            tray = tray.union(pad)
        else:
            door = door.union(pad)
        hinge_root_pad_records.append(
            {
                "index": record["index"],
                "owner": record["owner"],
                "center_y_mm": round(y_center, 4),
                "length_mm": round(root_pad_y_length, 4),
                "x_min_mm": round(root_pad_x_min, 4),
                "x_max_mm": round(root_pad_x_max, 4),
                "z_base_mm": round(root_pad_z_base, 4),
                "height_mm": round(root_pad_z_height, 4),
                "owner_specific": True,
            }
        )
    hinge_post_root_pad_bounds = {
        "rear_tray": _model_bounds_mm(tray),
        "front_display_door": _model_bounds_mm(door),
    }
    hinge_backer_rail_records: list[dict[str, Any]] = []
    hinge_gusset_records: list[dict[str, Any]] = []
    backer_x_length = max(wall * 2.0, rib_width * 4)
    backer_x_center = -outer_x / 2 + wall + backer_x_length / 2
    backer_z_height = min(rib_height * 1.1, hinge_outer / 2 - door_thickness / 2)
    gusset_y_length = max(rib_width, min(3.2, root_pad_y_length / 4))
    gusset_x_start = root_pad_x_min + min(rib_width, hinge_outer / 5)
    gusset_x_end = -outer_x / 2 + max(wall * 2.2, backer_x_length)
    gusset_z_start = root_pad_z_base + min(0.3, rib_height / 6)
    gusset_z_end = min(
        hinge_z + hinge_outer / 2 - 0.2,
        root_pad_z_base + root_pad_z_height,
    )
    for record in hinge_records:
        y_center = record["center_y_mm"]
        if record["owner"] == "tray":
            z_base = max(floor, hinge_z - backer_z_height / 2)
            tray = add_box_feature(
                tray,
                cq,
                backer_x_length,
                root_pad_y_length,
                backer_z_height,
                backer_x_center,
                y_center,
                z_base,
            )
        else:
            z_base = door_top_z
            door = add_box_feature(
                door,
                cq,
                backer_x_length,
                root_pad_y_length,
                backer_z_height,
                backer_x_center,
                y_center,
                z_base,
            )
        hinge_backer_rail_records.append(
            {
                "index": record["index"],
                "owner": record["owner"],
                "center_y_mm": round(y_center, 4),
                "x_length_mm": round(backer_x_length, 4),
                "y_length_mm": round(root_pad_y_length, 4),
                "height_mm": round(backer_z_height, 4),
                "owner_specific": True,
            }
        )

        for y_offset in (-root_pad_y_length * 0.32, root_pad_y_length * 0.32):
            gusset = (
                cq.Workplane("XZ")
                .polyline(
                    [
                        (gusset_x_start, gusset_z_start),
                        (gusset_x_end, gusset_z_start),
                        (gusset_x_end, gusset_z_end),
                    ]
                )
                .close()
                .extrude(gusset_y_length)
                .translate((0, y_center + y_offset - gusset_y_length / 2, 0))
            )
            if record["owner"] == "tray":
                tray = tray.union(gusset)
            else:
                door = door.union(gusset)
            hinge_gusset_records.append(
                {
                    "index": record["index"],
                    "owner": record["owner"],
                    "center_y_mm": round(y_center + y_offset, 4),
                    "length_y_mm": round(gusset_y_length, 4),
                    "x_start_mm": round(gusset_x_start, 4),
                    "x_end_mm": round(gusset_x_end, 4),
                    "z_start_mm": round(gusset_z_start, 4),
                    "z_end_mm": round(gusset_z_end, 4),
                    "owner_specific": True,
                }
            )

    pin_y_start = hinge_y_start - 1.0
    pin_length = total_hinge_span + 2.0
    hinge_pin_model = _cylinder_y(cq, hinge_x, pin_y_start, hinge_z, hinge_pin, pin_length)

    latch_width = _number(params, "snap_latch_width_mm", 14.0)
    latch_depth = _number(params, "snap_latch_depth_mm", 5.0)
    latch_height = _number(params, "snap_latch_height_mm", 4.0)
    latch_protrusion = min(1.2, latch_depth / 3)
    latch_x = outer_x / 2 - latch_depth / 2 + latch_protrusion
    latch_z = door_z + max(0.0, door_thickness - latch_height / 2)
    door = add_box_feature(door, cq, latch_depth, latch_width, latch_height, latch_x, 0, latch_z)

    catch_depth = max(latch_depth, wall)
    catch_z = max(floor, shell_z - latch_height)
    tray = add_box_feature(
        tray,
        cq,
        catch_depth,
        latch_width * 1.4,
        latch_height,
        outer_x / 2 - catch_depth / 2 + latch_protrusion,
        0,
        catch_z,
    )

    display_reference_z = max(floor + 1.0, door_z - d["front_stack_thickness_mm"] - 0.2)
    display_reference = rounded_plate(
        cq,
        d["outsize_x_mm"],
        d["outsize_y_mm"],
        d["front_stack_thickness_mm"],
        min(2.0, corner),
    ).translate((0, 0, display_reference_z))
    active_area_face = _box(cq, d["active_area_x_mm"], d["active_area_y_mm"], 0.6)
    active_area_face = active_area_face.translate(
        (0, 0, display_reference_z + d["front_stack_thickness_mm"] + 0.05)
    )
    display_reference = display_reference.union(active_area_face)

    gland_reference = _cylinder_y(
        cq,
        0,
        -outer_y / 2 - gland_length,
        cable_z,
        gland_outer,
        gland_length,
        gland_cable_hole,
    )

    closed_models = [tray, door, hinge_pin_model, display_reference, gland_reference]
    closed = _combine_models(cq, closed_models)

    open_angle = _number(params, "assembly_door_open_angle_degrees", 72.0)
    door_open_group = _combine_models(cq, [door, display_reference])
    door_open_group = _transform_about_hinge(door_open_group, hinge_x, hinge_z, -open_angle)
    door_open = _combine_models(cq, [tray, door_open_group, hinge_pin_model, gland_reference])

    exploded = _combine_models(
        cq,
        [
            tray.translate((-12, 0, 0)),
            door.translate((34, 0, 10)),
            hinge_pin_model.translate((-18, 0, 6)),
            display_reference.translate((34, 0, -10)),
            gland_reference.translate((0, -18, 0)),
        ],
    )
    door_print = door.translate((0, 0, -door_z))
    k1_plate_tray = tray
    k1_plate_door = door_print
    k1_max_combined_gap = 8.0
    k1_max_combined = _combine_models(
        cq,
        [
            tray.translate((0, -(outer_y + k1_max_combined_gap) / 2, 0)),
            door_print.translate((0, (outer_y + k1_max_combined_gap) / 2, 0)),
        ],
    )
    hardware_reference_layout = _combine_models(
        cq,
        [
            display_reference.translate((0, 0, -display_reference_z)),
            gland_reference.translate((0, 26, -cable_z)),
            hinge_pin_model.translate((0, -36, -hinge_z)),
        ],
    )

    parts = [
        GeneratedAssemblyPart(
            id="rear_tray",
            name="Rear tray with M12 gland pad",
            model=tray,
            role="print",
            material_hint="ASA, 3.2 mm walls, ribbed floor",
            occurrence={
                "name": "CBBS P070 rear tray",
                "transform": {
                    "translation_mm": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "rotation_degrees": {"x": 0.0, "y": 0.0, "z": 0.0},
                },
            },
            support_risk={
                "level": "medium",
                "notes": "Hinge barrels include print flats and end chamfers; ASA warping remains unvalidated.",
            },
        ),
        GeneratedAssemblyPart(
            id="front_display_door",
            name="Front hinged display-bezel door",
            model=door,
            role="print",
            material_hint="ASA, 3.2 mm bezel door",
            occurrence={
                "name": "CBBS P070 front display door",
                "transform": {
                    "translation_mm": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "rotation_degrees": {"x": 0.0, "y": 0.0, "z": 0.0},
                },
            },
            support_risk={
                "level": "medium",
                "notes": "Hinge barrels include print flats and end chamfers; latch cycling is blocked.",
            },
        ),
        GeneratedAssemblyPart(
            id="hinge_pin",
            name="M3 or 3 mm removable hinge pin reference",
            model=hinge_pin_model,
            role="hardware-reference",
            material_hint="3.0 mm metal pin or M3 smooth shank",
            occurrence={
                "name": "CBBS P070 hinge pin reference",
                "transform": {
                    "translation_mm": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "rotation_degrees": {"x": 0.0, "y": 0.0, "z": 0.0},
                },
            },
        ),
        GeneratedAssemblyPart(
            id="display_reference",
            name="Nextion P070 display reference envelope",
            model=display_reference,
            role="hardware-reference",
            material_hint="reference only",
            occurrence={
                "name": "CBBS P070 display reference",
                "transform": {
                    "translation_mm": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "rotation_degrees": {"x": 0.0, "y": 0.0, "z": 0.0},
                },
            },
        ),
        GeneratedAssemblyPart(
            id="m12_gland_reference",
            name="LAPP SKINTOP ST-M M12 gland reference",
            model=gland_reference,
            role="hardware-reference",
            material_hint="reference only",
            occurrence={
                "name": "CBBS P070 M12 gland reference",
                "transform": {
                    "translation_mm": {"x": 0.0, "y": 0.0, "z": 0.0},
                    "rotation_degrees": {"x": 0.0, "y": 0.0, "z": 0.0},
                },
            },
        ),
    ]

    print_part_bounds = {
        part.id: _model_bounds_mm(part.model)
        for part in parts
        if part.role == "print"
    }
    fits_k1_with_brim = all(
        bounds["x"] + 12.0 <= 220.0 and bounds["y"] + 12.0 <= 220.0
        for bounds in print_part_bounds.values()
    )
    tray_bounds = print_part_bounds["rear_tray"]
    door_bounds = print_part_bounds["front_display_door"]
    brim_margin = 6.0
    layout_spacing = 8.0
    k1_combined_fit = _fits_two_part_plate(
        tray_bounds,
        door_bounds,
        220.0,
        220.0,
        brim_margin,
        layout_spacing,
    )
    k1_max_combined_fit = _fits_two_part_plate(
        tray_bounds,
        door_bounds,
        300.0,
        300.0,
        brim_margin,
        layout_spacing,
    )
    metadata = {
        "schema": "cbbs-cad/p070-assembly-metadata/v1",
        "truth_state": concept.truth_state,
        "printer_target": "Creality K1 series ASA",
        "smallest_supported_build_volume_mm": {"x": 220.0, "y": 220.0, "z": 250.0},
        "asa_print_defaults": {
            "wall_thickness_mm": wall,
            "floor_thickness_mm": floor,
            "door_thickness_mm": door_thickness,
            "rib_width_mm": rib_width,
            "rib_height_mm": rib_height,
            "door_reveal_mm": door_gap,
            "brim_margin_each_side_mm": 6.0,
        },
        "k1_fit": {
            "print_part_bounds_mm": print_part_bounds,
            "fits_xy_with_6mm_brim": fits_k1_with_brim,
            "combined_k1_plate": {
                **k1_combined_fit,
                "accepted": False,
                "reason": "Tray and door do not fit together on a 220 x 220 mm plate with 6 mm brim margin.",
            },
            "combined_k1_max_plate": {
                **k1_max_combined_fit,
                "accepted": bool(k1_max_combined_fit["fits_with_6mm_brim"]),
            },
        },
        "print_layouts": {
            "k1-plate-tray": {
                "printer": "Creality K1/K1C/K1 SE",
                "plate_mm": {"x": 220.0, "y": 220.0},
                "brim_margin_each_side_mm": brim_margin,
                "parts": ["rear_tray"],
                "bounds_mm": tray_bounds,
                "fits_with_6mm_brim": _fits_single_plate(tray_bounds, 220.0, 220.0, brim_margin),
                "orientation": "tray back on build plate; hinge axis along Y",
            },
            "k1-plate-door": {
                "printer": "Creality K1/K1C/K1 SE",
                "plate_mm": {"x": 220.0, "y": 220.0},
                "brim_margin_each_side_mm": brim_margin,
                "parts": ["front_display_door"],
                "bounds_mm": door_bounds,
                "fits_with_6mm_brim": _fits_single_plate(door_bounds, 220.0, 220.0, brim_margin),
                "orientation": "front face up; door translated to bed Z for slicer review",
            },
            "k1-combined": {
                "printer": "Creality K1/K1C/K1 SE",
                "plate_mm": {"x": 220.0, "y": 220.0},
                "brim_margin_each_side_mm": brim_margin,
                "parts": ["rear_tray", "front_display_door"],
                **k1_combined_fit,
                "accepted": False,
            },
            "k1-max-combined": {
                "printer": "Creality K1 Max",
                "plate_mm": {"x": 300.0, "y": 300.0},
                "brim_margin_each_side_mm": brim_margin,
                "part_spacing_mm": layout_spacing,
                "parts": ["rear_tray", "front_display_door"],
                **k1_max_combined_fit,
                "accepted": bool(k1_max_combined_fit["fits_with_6mm_brim"]),
            },
            "hardware-reference": {
                "parts": ["hinge_pin", "display_reference", "m12_gland_reference"],
                "purpose": "Reference-only hardware envelopes for Fusion review.",
            },
        },
        "display_window_mm": {"x": round(window_x, 4), "y": round(window_y, 4)},
        "display_mount": {
            "schema": "cbbs-cad/p070-display-mount/v1",
            "hardware_ref": "nextion_nx8048p070_011c",
            "mount_hole_count": len(display_mount_points),
            "hole_span_mm": {"x": round(hole_span_x, 4), "y": round(hole_span_y, 4)},
            "positions_mm": display_mount_points,
            "source_mount_hole_diameter_mm": round(d["mount_hole_diameter_mm"], 4),
            "clearance_reference_diameter_mm": round(boss_clearance_hole, 4),
            "boss_outer_diameter_mm": round(boss_outer, 4),
            "boss_height_mm": round(boss_height, 4),
            "boss_hole_diameter_mm": round(boss_hole, 4),
            "thread_mode": display_mount_thread_mode,
            "nominal_thread": display_mount_thread_nominal,
            "pilot_diameter_mm": round(display_mount_thread_pilot, 4),
            "boss_to_floor_webs": {
                "count": len(display_boss_web_records) * 2,
                "owner": "rear_tray",
                "records": display_boss_web_records,
                "hole_clearance_preserved": True,
                "verification_status": "physical-print-required",
            },
            "validation_status": "physical-print-required",
            "notes": (
                "M3 screws pass through the Nextion 3.2 mm display holes and "
                "tap or screw-form into printed ASA pilot bosses."
            ),
        },
        "hinge": {
            "axis": "Y",
            "axis_x_mm": round(hinge_x, 4),
            "axis_z_mm": round(hinge_z, 4),
            "pin_diameter_mm": hinge_pin,
            "bore_diameter_mm": hinge_bore,
            "barrel_outer_diameter_mm": hinge_outer,
            "gap_mm": hinge_gap,
            "print_flat_depth_mm": hinge_flat_depth,
            "end_chamfer_mm": hinge_end_chamfer,
            "support_risk": "medium until ASA hinge coupons are printed and cycled",
            "knuckles": hinge_records,
            "root_reinforcement": {
                "count": len(hinge_root_pad_records),
                "records": hinge_root_pad_records,
                "owner_pattern": [record["owner"] for record in hinge_root_pad_records],
                "backer_rails": {
                    "count": len(hinge_backer_rail_records),
                    "records": hinge_backer_rail_records,
                    "owner_pattern": [record["owner"] for record in hinge_backer_rail_records],
                },
                "gusset_webs": {
                    "count": len(hinge_gusset_records),
                    "records": hinge_gusset_records,
                    "owner_pattern": [record["owner"] for record in hinge_gusset_records],
                },
                "minimum_gap_between_pads_mm": round(
                    hinge_gap + root_pad_y_trim * 2,
                    4,
                ),
                "bounds_before_mm": hinge_pre_root_pad_bounds,
                "bounds_after_mm": hinge_post_root_pad_bounds,
                "bounds_unchanged": hinge_pre_root_pad_bounds == hinge_post_root_pad_bounds,
                "does_not_bridge_opposing_owners": True,
            },
        },
        "mechanical_reinforcement": {
            "hinge_backer_rails": {
                "count": len(hinge_backer_rail_records),
                "records": hinge_backer_rail_records,
                "owner_specific": True,
            },
            "hinge_gusset_webs": {
                "count": len(hinge_gusset_records),
                "records": hinge_gusset_records,
                "owner_specific": True,
            },
            "rear_panel_floor_rib_lattice": {
                "count": len(floor_lattice_records),
                "records": floor_lattice_records,
                "width_mm": rib_width,
                "height_mm": rib_height,
                "symmetric": True,
            },
            "rear_panel_inner_perimeter_rails": {
                "count": len(inner_perimeter_rail_records),
                "records": inner_perimeter_rail_records,
                "width_mm": rib_width,
                "height_mm": rib_height,
            },
            "display_boss_to_floor_webs": {
                "count": len(display_boss_web_records) * 2,
                "width_mm": rib_width,
                "height_mm": rib_height,
            },
            "front_door_edge_corner_reinforcement": {
                "count": len(door_reinforcement_records),
                "records": door_reinforcement_records,
                "outside_display_window": True,
            },
        },
        "structural_review": {
            "schema": "cbbs-cad/structural-review/v1",
            "truth_state": concept.truth_state,
            "source_refs": [
                "p070_structural_strengthening_findings",
                "prusa_modeling_guidance",
                "prusa_asa_guidance",
                "nextion_p070_dimension_pdf",
                "creality_k1_series_compare",
            ],
            "strengthened_features": {
                "hinge_root_pads": len(hinge_root_pad_records),
                "hinge_backer_rails": len(hinge_backer_rail_records),
                "hinge_gusset_webs": len(hinge_gusset_records),
                "rear_panel_floor_ribs": len(floor_lattice_records),
                "rear_panel_inner_perimeter_rails": len(inner_perimeter_rail_records),
                "display_boss_webs": len(display_boss_web_records) * 2,
                "front_door_edge_corner_features": len(door_reinforcement_records),
            },
            "k1_margins_mm": {
                "rear_tray": {
                    "x": round(208.0 - tray_bounds["x"], 4),
                    "y": round(208.0 - tray_bounds["y"], 4),
                },
                "front_display_door": {
                    "x": round(208.0 - door_bounds["x"], 4),
                    "y": round(208.0 - door_bounds["y"], 4),
                },
            },
            "weak_points_addressed": [
                "hinge barrel root contact",
                "hinge leaf root shear at printed door knuckles",
                "hinge-side frame flex at alternating knuckle gaps",
                "rear panel floor oil-canning",
                "display mount boss floor pull-through",
                "front display door corner and edge flex",
            ],
            "remaining_blockers": concept.open_measurement_blockers,
            "blocked_claims": [
                "strength rating",
                "impact rating",
                "weatherproofing",
                "dustproofing",
                "IP rating",
                "NEMA rating",
                "field readiness",
            ],
            "validation_required": [
                "physical ASA print",
                "hinge cycling",
                "fastener pullout",
                "display fit",
                "heat behavior",
                "RF behavior",
                "service validation",
            ],
        },
        "cable_entry": {
            "gland_thread": "M12x1.5",
            "clearance_diameter_mm": cable_hole,
            "reference_outer_diameter_mm": gland_outer,
            "reference_length_mm": gland_length,
        },
    }
    assembly = GeneratedAssembly(
        parts=parts,
        views={
            "closed-front": closed,
            "closed-isometric": closed,
            "door-open": door_open,
            "exploded": exploded,
            "k1-plate-tray": k1_plate_tray,
            "k1-plate-door": k1_plate_door,
            "k1-max-combined": k1_max_combined,
            "hardware-reference": hardware_reference_layout,
        },
        metadata=metadata,
    )
    return GeneratedModel(model=closed, assembly=assembly)


def _part_model(parts: list[GeneratedAssemblyPart], part_id: str) -> Any:
    for part in parts:
        if part.id == part_id:
            return part.model
    raise ValueError(f"generated assembly missing part: {part_id}")


def _hardware_by_required_id(
    hardware_by_id: dict[str, HardwareSpec],
    hardware_id: str,
) -> HardwareSpec:
    try:
        return hardware_by_id[hardware_id]
    except KeyError as exc:
        raise ValueError(f"missing hardware spec: {hardware_id}") from exc


def _build_reference_board(cq: Any, x: float, y: float, z: float, corner: float = 1.0) -> Any:
    board = rounded_plate(cq, x, y, z, corner)
    face = _box(cq, max(2.0, x * 0.35), max(2.0, y * 0.45), 0.45).translate(
        (0, 0, z + 0.05)
    )
    return board.union(face)


def _centered_pattern_positions(span: float, pitch: float) -> list[float]:
    if span <= 0 or pitch <= 0:
        return []
    positions = [0.0]
    step = pitch
    while step <= span / 2 + 0.001:
        positions.extend([-step, step])
        step += pitch
    return sorted(positions)


def _raised_bar_between(
    cq: Any,
    start: tuple[float, float],
    end: tuple[float, float],
    width: float,
    height: float,
    z_base: float,
    chamfer: float = 0.0,
) -> Any:
    length = hypot(end[0] - start[0], end[1] - start[1])
    if length <= 0:
        feature = _box(cq, width, width, height).translate((start[0], start[1], z_base))
        return _try_chamfer_vertical_edges(feature, chamfer, width, width, height)
    angle = degrees(atan2(end[1] - start[1], end[0] - start[0]))
    midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
    feature = (
        _box(cq, length, width, height)
        .rotate((0, 0, 0), (0, 0, 1), angle)
        .translate((midpoint[0], midpoint[1], z_base))
    )
    return _try_chamfer_vertical_edges(feature, chamfer, length, width, height)


def _add_route_rail_pair_between(
    model: Any,
    cq: Any,
    start: tuple[float, float],
    end: tuple[float, float],
    channel_width: float,
    rail_width: float,
    rail_height: float,
    z_base: float,
    route_id: str,
    chamfer: float = 0.0,
) -> tuple[Any, list[dict[str, Any]]]:
    length = hypot(end[0] - start[0], end[1] - start[1])
    if length <= 0:
        return model, []
    dx = (end[0] - start[0]) / length
    dy = (end[1] - start[1]) / length
    px = -dy
    py = dx
    records: list[dict[str, Any]] = []
    for side, sign in (("left", -1.0), ("right", 1.0)):
        offset = channel_width / 2 * sign
        rail_start = (start[0] + px * offset, start[1] + py * offset)
        rail_end = (end[0] + px * offset, end[1] + py * offset)
        model = model.union(
            _raised_bar_between(
                cq,
                rail_start,
                rail_end,
                rail_width,
                rail_height,
                z_base,
                chamfer,
            )
        )
        records.append(
            {
                "route_id": route_id,
                "side": side,
                "start_mm": {"x": round(rail_start[0], 4), "y": round(rail_start[1], 4)},
                "end_mm": {"x": round(rail_end[0], 4), "y": round(rail_end[1], 4)},
                "length_mm": round(length, 4),
                "rail_width_mm": round(rail_width, 4),
                "rail_height_mm": round(rail_height, 4),
            }
        )
    return model, records


def _raised_annular_badge(
    cq: Any,
    center_x: float,
    center_y: float,
    outer_diameter: float,
    wall_width: float,
    height: float,
    z_base: float,
    chamfer: float = 0.0,
) -> Any:
    inner_radius = max(0.1, outer_diameter / 2 - wall_width)
    badge = (
        cq.Workplane("XY")
        .center(center_x, center_y)
        .circle(outer_diameter / 2)
        .circle(inner_radius)
        .extrude(height)
        .translate((0, 0, z_base))
    )
    return _try_chamfer_vertical_edges(badge, chamfer, wall_width, height)


def _try_chamfer_vertical_edges(model: Any, chamfer: float, *dimensions: float) -> Any:
    if chamfer <= 0:
        return model
    positive = [dimension for dimension in dimensions if dimension > 0]
    if not positive:
        return model
    safe = min(chamfer, min(positive) / 3)
    if safe <= 0:
        return model
    try:
        return model.edges("|Z").chamfer(safe)
    except Exception:
        return model


def _add_raised_text(
    model: Any,
    cq: Any,
    text: str,
    center_x: float,
    center_y: float,
    font_size: float,
    relief: float,
    z_base: float,
) -> tuple[Any, str]:
    for font in ("DejaVu Sans", "Arial"):
        try:
            text_model = cq.Workplane("XY").text(
                text,
                font_size,
                relief,
                combine=False,
                font=font,
                kind="bold",
                halign="center",
                valign="center",
            )
            return model.union(text_model.translate((center_x, center_y, z_base))), font
        except Exception:
            continue

    # Keep generation available if host fonts are unavailable. The metadata
    # records this fallback so it cannot be mistaken for exact brand typography.
    fallback = _box(cq, font_size * len(text) * 0.62, font_size * 0.72, relief).translate(
        (center_x, center_y, z_base)
    )
    return model.union(fallback), "block-letter-fallback"


def _build_p070_heltec_outdoor_controller_enclosure(
    cq: Any,
    concept: ConceptSpec,
    hardware_by_id: dict[str, HardwareSpec],
) -> GeneratedModel:
    display = _hardware_by_required_id(hardware_by_id, "nextion_nx8048p070_011c")
    heltec = _hardware_by_required_id(hardware_by_id, "heltec_wifi_lora_32_v2")
    battery = _hardware_by_required_id(hardware_by_id, "bioenno_blf_0612c_lifepo4_pack")
    regulator = _hardware_by_required_id(hardware_by_id, "pololu_s13v30f5_regulator")
    antenna = _hardware_by_required_id(hardware_by_id, "taoglas_ti_96_a113_915mhz_antenna")
    field_gland = _hardware_by_required_id(hardware_by_id, "lapp_skintop_str_npt_3_4_reference")

    base = _build_p070_hinged_wall_enclosure(cq, concept, display)
    if not base.assembly:
        raise ValueError("base P070 enclosure did not produce an assembly")

    d = display.dimensions
    params = concept.parameters
    wall = _number(params, "wall_thickness_mm", 3.2)
    side_clearance = _number(params, "display_side_clearance_mm", 5.0)
    floor = _number(params, "floor_thickness_mm", 3.2)
    rear_depth = _number(params, "rear_clearance_depth_mm", 26.0)
    door_thickness = _number(params, "front_door_thickness_mm", 3.2)
    door_gap = _number(params, "door_gap_mm", 1.0)
    rib_width = _number(params, "asa_rib_width_mm", 1.6)
    rib_height = _number(params, "asa_rib_height_mm", 2.4)
    window_clearance = _number(params, "display_window_clearance_mm", 1.0)

    cavity_x = d["outsize_x_mm"] + side_clearance * 2
    cavity_y = d["outsize_y_mm"] + side_clearance * 2
    outer_x = cavity_x + wall * 2
    outer_y = cavity_y + wall * 2
    shell_z = floor + rear_depth
    door_z = shell_z + door_gap
    door_top_z = door_z + door_thickness
    window_x = min(d["lcd_outsize_x_mm"] - 0.8, d["active_area_x_mm"] + window_clearance * 2)
    window_y = min(d["lcd_outsize_y_mm"] - 0.8, d["active_area_y_mm"] + window_clearance * 2)

    pod_wall = _number(params, "rear_pod_wall_thickness_mm", 3.2)
    pod_floor = _number(params, "rear_pod_floor_thickness_mm", 3.2)
    battery_bay_x = _number(params, "battery_service_bay_x_mm", 125.0)
    battery_bay_y = _number(params, "battery_service_bay_y_mm", 73.0)
    battery_bay_z = _number(params, "battery_service_bay_z_mm", 90.0)
    heltec_bay = {
        "x": _number(params, "heltec_bay_x_mm", 61.0),
        "y": _number(params, "heltec_bay_y_mm", 36.0),
        "z": _number(params, "heltec_bay_z_mm", 18.0),
    }
    regulator_bay = {
        "x": _number(params, "regulator_bay_x_mm", 33.0),
        "y": _number(params, "regulator_bay_y_mm", 33.0),
        "z": _number(params, "regulator_bay_z_mm", 18.0),
    }
    antenna_keepout_diameter = _number(params, "antenna_keepout_diameter_mm", 25.0)
    antenna_keepout_sweep = _number(params, "antenna_keepout_sweep_mm", 230.0)
    strap_slot_width = _number(params, "battery_strap_slot_width_mm", 6.0)
    strap_slot_length = _number(params, "battery_strap_slot_length_mm", 82.0)
    standoff_height = _number(params, "electronics_standoff_height_mm", 4.0)
    standoff_outer = _number(params, "electronics_standoff_outer_diameter_mm", 7.0)
    sma_boss_outer = _number(params, "sma_boss_outer_diameter_mm", 18.0)
    sma_clearance = _number(params, "sma_bulkhead_clearance_diameter_mm", 6.5)
    sma_boss_length = _number(params, "sma_boss_length_mm", 12.0)
    wire_channel_width = _number(params, "wire_channel_width_mm", 5.0)
    front_rail_width = _number(params, "front_contour_rail_width_mm", 1.8)
    front_rail_height = _number(params, "front_contour_rail_height_mm", 1.2)
    front_rail_clearance = _number(params, "front_contour_rail_clearance_mm", 3.0)
    macro_rib_width = _number(params, "rear_pod_macro_rib_width_mm", 1.8)
    macro_rib_height = _number(params, "rear_pod_macro_rib_height_mm", 1.2)
    macro_rib_pitch = _number(params, "rear_pod_macro_rib_pitch_mm", 18.0)
    raised_brand_relief = _number(params, "raised_brand_relief_mm", 1.2)
    raised_brand_text_font_size = _number(params, "raised_brand_text_font_size_mm", 10.0)
    raised_brand_icon_diameter = _number(params, "raised_brand_icon_diameter_mm", 14.0)
    surface_chamfer = _number(params, "surface_feature_edge_chamfer_mm", 0.2)
    field_gland_boss_outer = _number(params, "field_gland_boss_outer_diameter_mm", 44.0)
    field_gland_thread_depth = _number(params, "field_gland_thread_depth_mm", 15.0)
    field_gland_thread_major = _number(params, "field_gland_thread_major_diameter_mm", 26.67)
    field_gland_threads_per_inch = _number(params, "field_gland_threads_per_inch", 14.0)
    field_gland_taper = _number(
        params,
        "field_gland_taper_diameter_per_length_mm_per_mm",
        0.0625,
    )
    field_gland_clearance = _number(params, "field_gland_thread_clearance_mm", 0.45)
    field_wire_trunk_width = _number(params, "field_wire_trunk_channel_width_mm", 12.0)

    pod_outer_x = min(outer_x - 16.0, battery_bay_x + pod_wall * 2)
    pod_outer_y = battery_bay_y + pod_wall * 2
    pod_outer_z = battery_bay_z + pod_floor
    pod_base_z = shell_z
    pod_connector_width = min(
        _number(params, "rear_pod_connector_width_mm", 54.0),
        pod_outer_x - pod_wall * 2,
    )
    pod_connector_length = _number(params, "rear_pod_connector_length_mm", 18.0)
    pod_connector_overlap = _number(params, "rear_pod_connector_overlap_mm", 2.0)
    pod_body_min_y = outer_y / 2 + pod_connector_length
    pod_center_y = pod_body_min_y + pod_outer_y / 2

    # Keep the deep rear pod orthogonal for reliable STEP/STL export; the
    # release surface treatment is still blocked on printed samples.
    pod_shell = _box(cq, pod_outer_x, pod_outer_y, pod_outer_z)
    pod_shell = pod_shell.translate((0, pod_center_y, pod_base_z))
    pod_shell = pod_shell.faces(">Z").workplane().rect(battery_bay_x, battery_bay_y).cutBlind(
        -battery_bay_z
    )

    rear_pod_floor_rib_records: list[dict[str, Any]] = []
    pod_floor_rib_span_y = max(rib_width, battery_bay_y - rib_width * 2)
    pod_floor_rib_span_x = max(rib_width, battery_bay_x - rib_width * 2)
    pod_floor_z = pod_base_z + pod_floor
    for x in (-battery_bay_x / 4, 0.0, battery_bay_x / 4):
        pod_shell = add_box_feature(
            pod_shell,
            cq,
            rib_width,
            pod_floor_rib_span_y,
            rib_height,
            x,
            pod_center_y,
            pod_floor_z,
        )
        rear_pod_floor_rib_records.append(
            {
                "axis": "Y",
                "center_x_mm": round(x, 4),
                "length_mm": round(pod_floor_rib_span_y, 4),
            }
        )
    for y in (-battery_bay_y / 4, battery_bay_y / 4):
        pod_shell = add_box_feature(
            pod_shell,
            cq,
            pod_floor_rib_span_x,
            rib_width,
            rib_height,
            0,
            pod_center_y + y,
            pod_floor_z,
        )
        rear_pod_floor_rib_records.append(
            {
                "axis": "X",
                "center_y_mm": round(pod_center_y + y, 4),
                "length_mm": round(pod_floor_rib_span_x, 4),
            }
        )

    rear_pod_side_ledge_records: list[dict[str, Any]] = []
    pod_side_ledge_z = pod_base_z + pod_outer_z - rib_height
    for y in (
        pod_center_y - battery_bay_y / 2 + rib_width / 2,
        pod_center_y + battery_bay_y / 2 - rib_width / 2,
    ):
        pod_shell = add_box_feature(
            pod_shell,
            cq,
            battery_bay_x,
            rib_width,
            rib_height,
            0,
            y,
            pod_side_ledge_z,
        )
        rear_pod_side_ledge_records.append(
            {
                "axis": "X",
                "center_y_mm": round(y, 4),
                "length_mm": round(battery_bay_x, 4),
            }
        )
    for x in (-battery_bay_x / 2 + rib_width / 2, battery_bay_x / 2 - rib_width / 2):
        pod_shell = add_box_feature(
            pod_shell,
            cq,
            rib_width,
            battery_bay_y,
            rib_height,
            x,
            pod_center_y,
            pod_side_ledge_z,
        )
        rear_pod_side_ledge_records.append(
            {
                "axis": "Y",
                "center_x_mm": round(x, 4),
                "length_mm": round(battery_bay_y, 4),
            }
        )

    for slot_x in (-battery_bay_x / 3, battery_bay_x / 3):
        slot = _box(cq, strap_slot_width, strap_slot_length, pod_floor + 0.8).translate(
            (slot_x, pod_center_y, pod_base_z - 0.4)
        )
        pod_shell = pod_shell.cut(slot)

    rib_z = max(8.0, heltec_bay["z"] / 2)
    for y in (-pod_outer_y / 2 + pod_wall / 2, pod_outer_y / 2 - pod_wall / 2):
        pod_shell = add_box_feature(
            pod_shell,
            cq,
            pod_outer_x - 18.0,
            rib_width,
            rib_z,
            0,
            pod_center_y + y,
            pod_base_z + pod_floor,
        )
    for x in (-pod_outer_x / 2 + pod_wall / 2, pod_outer_x / 2 - pod_wall / 2):
        pod_shell = add_box_feature(
            pod_shell,
            cq,
            rib_width,
            pod_outer_y - 18.0,
            rib_z,
            x,
            pod_center_y,
            pod_base_z + pod_floor,
        )

    macro_rib_count = 0
    macro_rib_z_base = pod_base_z + pod_floor + 6.0
    macro_rib_z = max(12.0, pod_outer_z - pod_floor - 18.0)
    for x in _centered_pattern_positions(pod_outer_x - 28.0, macro_rib_pitch):
        for y in (-pod_outer_y / 2 - macro_rib_height / 2, pod_outer_y / 2 + macro_rib_height / 2):
            pod_shell = add_box_feature(
                pod_shell,
                cq,
                macro_rib_width,
                macro_rib_height,
                macro_rib_z,
                x,
                pod_center_y + y,
                macro_rib_z_base,
            )
            macro_rib_count += 1
    for y in _centered_pattern_positions(pod_outer_y - 28.0, macro_rib_pitch):
        for x in (-pod_outer_x / 2 - macro_rib_height / 2, pod_outer_x / 2 + macro_rib_height / 2):
            pod_shell = add_box_feature(
                pod_shell,
                cq,
                macro_rib_height,
                macro_rib_width,
                macro_rib_z,
                x,
                pod_center_y + y,
                macro_rib_z_base,
            )
            macro_rib_count += 1

    rear_panel_core = _part_model(base.assembly.parts, "rear_tray")
    connector_center_y = outer_y / 2 + pod_connector_length / 2
    connector_length = pod_connector_length + pod_connector_overlap * 2
    rear_pod_connector = _box(cq, pod_connector_width, connector_length, pod_floor).translate(
        (0, connector_center_y, pod_base_z)
    )
    rear_pod_module = pod_shell.union(rear_pod_connector)
    rear_panel_connector_landing = _box(
        cq,
        pod_connector_width + pod_wall * 2,
        pod_connector_overlap * 2,
        pod_floor,
    ).translate((0, outer_y / 2 - pod_connector_overlap, pod_base_z))
    rear_panel_core = rear_panel_core.union(rear_panel_connector_landing)

    wall_inset_x = _number(params, "wall_mount_inset_x_mm", 18.0)
    wall_inset_y = _number(params, "wall_mount_inset_y_mm", 16.0)
    wall_points = [
        (-outer_x / 2 + wall_inset_x, -outer_y / 2 + wall_inset_y),
        (-outer_x / 2 + wall_inset_x, outer_y / 2 - wall_inset_y),
        (outer_x / 2 - wall_inset_x, -outer_y / 2 + wall_inset_y),
        (outer_x / 2 - wall_inset_x, outer_y / 2 - wall_inset_y),
    ]
    mount_tab_accent_count = 0
    for x, y in wall_points:
        pad = rounded_plate(cq, 22.0, 16.0, rib_height, 2.0).translate((x, y, floor))
        rear_panel_core = rear_panel_core.union(pad)
        for rail_y in (y - 4.0, y + 4.0):
            rear_panel_core = add_box_feature(
                rear_panel_core,
                cq,
                14.0,
                macro_rib_width,
                macro_rib_height,
                x,
                rail_y,
                floor + rib_height,
            )
            mount_tab_accent_count += 1

    top_z = pod_base_z + pod_outer_z
    heltec_d = heltec.dimensions
    regulator_d = regulator.dimensions
    battery_d = battery.dimensions
    antenna_d = antenna.dimensions
    heltec_center = (
        -pod_outer_x / 2 + heltec_d["board_length_mm"] / 2 + 7.0,
        pod_center_y + pod_outer_y / 2 - heltec_d["board_width_mm"] / 2 - 5.0,
    )
    regulator_center = (
        pod_outer_x / 2 - regulator_d["board_length_mm"] / 2 - 8.0,
        pod_center_y - pod_outer_y / 2 + regulator_d["board_width_mm"] / 2 + 5.0,
    )

    hardware_alignment_records: dict[str, Any] = {}

    def add_rectangular_alignment_aids(
        model: Any,
        label: str,
        center: tuple[float, float],
        board_x: float,
        board_y: float,
        bay_x: float,
        bay_y: float,
        z_base: float,
        feature_height: float,
    ) -> Any:
        rail_width = max(rib_width, min(standoff_outer / 3, rib_width * 1.5))
        clearance = max(0.8, rib_width / 2)
        rail_x = min(board_x, bay_x - rail_width * 2)
        rail_y = min(board_y, bay_y - rail_width * 2)
        y_offset = min(
            bay_y / 2 - rail_width / 2,
            board_y / 2 + clearance + rail_width / 2,
        )
        x_offset = min(
            bay_x / 2 - rail_width / 2,
            board_x / 2 + clearance + rail_width / 2,
        )
        records: list[dict[str, Any]] = []
        for y in (center[1] - y_offset, center[1] + y_offset):
            model = add_box_feature(
                model,
                cq,
                rail_x,
                rail_width,
                feature_height,
                center[0],
                y,
                z_base,
            )
            records.append(
                {
                    "kind": "side_rail",
                    "axis": "X",
                    "center_x_mm": round(center[0], 4),
                    "center_y_mm": round(y, 4),
                    "length_mm": round(rail_x, 4),
                }
            )
        for x in (center[0] - x_offset, center[0] + x_offset):
            model = add_box_feature(
                model,
                cq,
                rail_width,
                rail_y,
                feature_height,
                x,
                center[1],
                z_base,
            )
            records.append(
                {
                    "kind": "end_stop",
                    "axis": "Y",
                    "center_x_mm": round(x, 4),
                    "center_y_mm": round(center[1], 4),
                    "length_mm": round(rail_y, 4),
                }
            )
        if label in {"heltec_v2", "regulator"}:
            corner_pad = rail_width * 1.8
            for sx in (-1.0, 1.0):
                for sy in (-1.0, 1.0):
                    pad_x = center[0] + sx * x_offset
                    pad_y = center[1] + sy * y_offset
                    model = add_box_feature(
                        model,
                        cq,
                        corner_pad,
                        corner_pad,
                        feature_height,
                        pad_x,
                        pad_y,
                        z_base,
                    )
                    records.append(
                        {
                            "kind": "corner_capture_pad",
                            "center_x_mm": round(pad_x, 4),
                            "center_y_mm": round(pad_y, 4),
                            "length_mm": round(corner_pad, 4),
                        }
                    )
        hardware_alignment_records[label] = {
            "type": "alignment rails and stops",
            "feature_count": len(records),
            "records": records,
            "verified_screw_holes": False,
            "mounting_holes_modeled": False,
            "verification_status": "pending-measurement",
        }
        return model

    pod_shell = add_rectangular_alignment_aids(
        pod_shell,
        "battery",
        (0.0, pod_center_y),
        battery_d["case_length_mm"],
        battery_d["case_width_mm"],
        battery_bay_x,
        battery_bay_y,
        pod_floor_z + rib_height,
        rib_height,
    )
    rear_pod_module = rear_pod_module.union(pod_shell)

    rear_pod_module = add_rectangular_alignment_aids(
        rear_pod_module,
        "heltec_v2",
        heltec_center,
        heltec_d["board_length_mm"],
        heltec_d["board_width_mm"],
        heltec_bay["x"],
        heltec_bay["y"],
        top_z,
        standoff_height,
    )
    rear_pod_module = add_rectangular_alignment_aids(
        rear_pod_module,
        "regulator",
        regulator_center,
        regulator_d["board_length_mm"],
        regulator_d["board_width_mm"],
        regulator_bay["x"],
        regulator_bay["y"],
        top_z,
        standoff_height,
    )

    sma_x = min(outer_x / 2 - 24.0, pod_outer_x / 2 + sma_boss_outer / 2 - 2.0)
    sma_z = top_z - 17.0
    sma_y_start = pod_center_y + pod_outer_y / 2 - 1.0
    sma_print_boss = _cylinder_y(
        cq,
        sma_x,
        sma_y_start,
        sma_z,
        sma_boss_outer,
        sma_boss_length + 1.0,
        sma_clearance,
    )
    rear_pod_module = rear_pod_module.union(sma_print_boss)
    rf_route_alignment_records: list[dict[str, Any]] = []
    for x_offset in (-wire_channel_width, wire_channel_width):
        rear_pod_module = add_box_feature(
            rear_pod_module,
            cq,
            4.0,
            18.0,
            3.0,
            sma_x + x_offset,
            pod_center_y + pod_outer_y / 2 - 12.0,
            sma_z - 1.5,
        )
        rf_route_alignment_records.append(
            {
                "kind": "rf_pigtail_channel_rail",
                "center_x_mm": round(sma_x + x_offset, 4),
                "center_y_mm": round(pod_center_y + pod_outer_y / 2 - 12.0, 4),
                "verification_status": "pending-measurement",
            }
        )
    hardware_alignment_records["rf_route"] = {
        "type": "alignment rails for RF pigtail route",
        "feature_count": len(rf_route_alignment_records),
        "records": rf_route_alignment_records,
        "verified_screw_holes": False,
        "mounting_holes_modeled": False,
        "verification_status": "pending-measurement",
    }

    field_gland_x = max(
        -pod_outer_x / 2 + field_gland_boss_outer / 2 + pod_wall,
        -pod_outer_x / 2 + field_gland_boss_outer / 2 + 4.0,
    )
    field_gland_z = pod_base_z + pod_floor + max(field_gland_boss_outer / 2 + 8.0, 32.0)
    field_gland_y_start = pod_center_y + pod_outer_y / 2 - 1.0
    field_wall_cut = _npt_wall_cut_y(
        cq,
        field_gland_x,
        pod_center_y + pod_outer_y / 2 - pod_wall - 0.6,
        field_gland_z,
        pod_wall + 1.2,
        field_gland_thread_major,
        field_gland_threads_per_inch,
        field_gland_taper,
        field_gland_clearance,
    )
    rear_pod_module = rear_pod_module.cut(field_wall_cut)
    field_thread_boss, field_thread_record = _build_segmented_npt_boss_y(
        cq,
        field_gland_x,
        field_gland_y_start,
        field_gland_z,
        field_gland_boss_outer,
        field_gland_thread_depth,
        field_gland_thread_major,
        field_gland_threads_per_inch,
        field_gland_taper,
        field_gland_clearance,
    )
    rear_pod_module = rear_pod_module.union(field_thread_boss)
    field_gland_support_records: list[dict[str, Any]] = []
    field_web_depth = min(field_gland_thread_depth, max(pod_wall * 2, 8.0))
    field_web_y = field_gland_y_start + field_web_depth / 2 - 0.3
    field_web_height = max(rib_height, macro_rib_height * 1.5)
    for z_offset, label in (
        (-field_gland_boss_outer / 2 + field_web_height / 2, "lower_saddle"),
        (field_gland_boss_outer / 2 - field_web_height / 2, "upper_saddle"),
    ):
        rear_pod_module = add_box_feature(
            rear_pod_module,
            cq,
            field_gland_boss_outer * 0.86,
            field_web_depth,
            field_web_height,
            field_gland_x,
            field_web_y,
            field_gland_z + z_offset - field_web_height / 2,
        )
        field_gland_support_records.append(
            {
                "kind": label,
                "center_x_mm": round(field_gland_x, 4),
                "center_y_mm": round(field_web_y, 4),
                "center_z_mm": round(field_gland_z + z_offset, 4),
                "verification_status": "physical-print-required",
            }
        )
    for x_offset, label in (
        (-field_gland_boss_outer / 2 + field_web_height / 2, "left_side_web"),
        (field_gland_boss_outer / 2 - field_web_height / 2, "right_side_web"),
    ):
        rear_pod_module = add_box_feature(
            rear_pod_module,
            cq,
            field_web_height,
            field_web_depth,
            field_gland_boss_outer * 0.72,
            field_gland_x + x_offset,
            field_web_y,
            field_gland_z - field_gland_boss_outer * 0.36,
        )
        field_gland_support_records.append(
            {
                "kind": label,
                "center_x_mm": round(field_gland_x + x_offset, 4),
                "center_y_mm": round(field_web_y, 4),
                "center_z_mm": round(field_gland_z, 4),
                "verification_status": "physical-print-required",
            }
        )

    wire_route_records: list[dict[str, Any]] = []
    route_rail_height = max(1.2, rib_height * 0.75)
    route_z_base = top_z
    route_rail_width = max(rib_width, min(2.4, wire_channel_width * 0.35))
    field_route_start = (field_gland_x, pod_center_y + pod_outer_y / 2 - field_gland_boss_outer / 2)
    field_route_end = (regulator_center[0], regulator_center[1])
    rear_pod_module, records = _add_route_rail_pair_between(
        rear_pod_module,
        cq,
        field_route_start,
        field_route_end,
        field_wire_trunk_width,
        route_rail_width,
        route_rail_height,
        route_z_base,
        "field_entry_to_regulator",
        surface_chamfer,
    )
    wire_route_records.extend(records)
    rear_pod_module, records = _add_route_rail_pair_between(
        rear_pod_module,
        cq,
        field_route_end,
        (heltec_center[0], heltec_center[1]),
        wire_channel_width,
        route_rail_width,
        route_rail_height,
        route_z_base,
        "regulator_to_heltec_power",
        surface_chamfer,
    )
    wire_route_records.extend(records)
    rear_pod_module, records = _add_route_rail_pair_between(
        rear_pod_module,
        cq,
        (heltec_center[0], heltec_center[1]),
        (sma_x, pod_center_y + pod_outer_y / 2 - 12.0),
        wire_channel_width,
        route_rail_width,
        route_rail_height,
        route_z_base,
        "heltec_to_sma_rf",
        surface_chamfer,
    )
    wire_route_records.extend(records)

    tray = rear_panel_core.union(rear_pod_module)

    battery_reference = rounded_plate(
        cq,
        battery_d["case_length_mm"],
        battery_d["case_width_mm"],
        battery_d["case_height_mm"],
        3.0,
    ).translate((0, pod_center_y, pod_base_z + pod_floor))
    heltec_reference = _build_reference_board(
        cq,
        heltec_d["board_length_mm"],
        heltec_d["board_width_mm"],
        heltec_d["envelope_height_mm"],
        1.0,
    ).translate((heltec_center[0], heltec_center[1], top_z + standoff_height))
    regulator_reference = _build_reference_board(
        cq,
        regulator_d["board_length_mm"],
        regulator_d["board_width_mm"],
        regulator_d["envelope_height_mm"],
        1.0,
    ).translate((regulator_center[0], regulator_center[1], top_z + standoff_height))
    sma_bulkhead_reference = _cylinder_y(
        cq,
        sma_x,
        pod_center_y + pod_outer_y / 2 - 4.0,
        sma_z,
        max(8.0, sma_clearance + 3.0),
        24.0,
        sma_clearance,
    )
    antenna_keepout_reference = (
        cq.Workplane("XY")
        .center(sma_x, pod_center_y + pod_outer_y / 2 + 20.0)
        .circle(antenna_keepout_diameter / 2)
        .extrude(antenna_keepout_sweep)
        .translate((0, 0, sma_z))
    )
    antenna_body_reference = (
        cq.Workplane("XY")
        .center(sma_x, pod_center_y + pod_outer_y / 2 + 20.0)
        .circle(antenna_d["body_diameter_mm"] / 2)
        .extrude(antenna_d["body_length_mm"])
        .translate((0, 0, sma_z))
    )
    antenna_keepout_reference = antenna_keepout_reference.union(antenna_body_reference)
    wire_channel_reference = _box(
        cq,
        abs(heltec_center[0] - sma_x) + 18.0,
        wire_channel_width,
        wire_channel_width,
    ).translate(
        (
            (heltec_center[0] + sma_x) / 2,
            min(pod_center_y + pod_outer_y / 2 - 12.0, heltec_center[1] + 4.0),
            top_z + standoff_height + 2.0,
        )
    )
    field_gland_reference = _cylinder_y(
        cq,
        field_gland_x,
        field_gland_y_start + field_gland_thread_depth,
        field_gland_z,
        field_gland.dimensions["outer_diameter_a_mm"],
        field_gland.dimensions["dimension_d_mm"],
        field_gland.dimensions["cable_clamp_max_mm"],
    )

    door = _part_model(base.assembly.parts, "front_display_door")
    hinge_pin_model = _part_model(base.assembly.parts, "hinge_pin")
    display_reference = _part_model(base.assembly.parts, "display_reference")
    gland_reference = _part_model(base.assembly.parts, "m12_gland_reference")

    front_contour_rail_count = 0
    horizontal_span = min(outer_x - 36.0, window_x + front_rail_clearance * 2 + front_rail_width * 2)
    center_gap = min(32.0, max(20.0, horizontal_span * 0.22))
    horizontal_segment = max(front_rail_width * 3, (horizontal_span - center_gap) / 2)
    rail_y = window_y / 2 + front_rail_clearance + front_rail_width / 2
    for y in (-rail_y, rail_y):
        for sx in (-1.0, 1.0):
            center_x = sx * (center_gap / 2 + horizontal_segment / 2)
            door = door.union(
                _raised_bar_between(
                    cq,
                    (center_x - horizontal_segment / 2, y),
                    (center_x + horizontal_segment / 2, y),
                    front_rail_width,
                    front_rail_height,
                    door_top_z,
                    surface_chamfer,
                )
            )
            front_contour_rail_count += 1

    vertical_span = min(outer_y - 36.0, window_y + front_rail_clearance * 2)
    rail_x = window_x / 2 + front_rail_clearance + front_rail_width / 2
    for x in (-rail_x, rail_x):
        door = door.union(
            _raised_bar_between(
                cq,
                (x, -vertical_span / 2),
                (x, vertical_span / 2),
                front_rail_width,
                front_rail_height,
                door_top_z,
                surface_chamfer,
            )
        )
        front_contour_rail_count += 1

    brand_text_y = -outer_y / 2 + max(raised_brand_text_font_size * 0.78, 7.6)
    door, brand_text_font_used = _add_raised_text(
        door,
        cq,
        "CBBS",
        0,
        brand_text_y,
        raised_brand_text_font_size,
        raised_brand_relief,
        door_top_z,
    )

    icon_center = (-outer_x / 2 + raised_brand_icon_diameter / 2 + 4.0, outer_y / 2 - 9.0)
    icon_line_width = max(1.0, front_rail_width * 0.55)
    icon_ring_width = max(1.0, raised_brand_icon_diameter * 0.08)
    door = door.union(
        _raised_annular_badge(
            cq,
            icon_center[0],
            icon_center[1],
            raised_brand_icon_diameter,
            icon_ring_width,
            raised_brand_relief,
            door_top_z,
            surface_chamfer,
        )
    )
    icon_scale = raised_brand_icon_diameter / 14.0
    icon_nodes = [
        (0.0, 0.0, 2.8),
        (-4.2, 3.2, 2.4),
        (4.2, 3.2, 2.4),
        (4.4, -3.4, 2.4),
    ]
    for dx, dy, diameter in icon_nodes:
        door = add_cylindrical_boss(
            door,
            cq,
            icon_center[0] + dx * icon_scale,
            icon_center[1] + dy * icon_scale,
            diameter * icon_scale,
            raised_brand_relief,
            door_top_z,
        )
    for start, end in [
        ((-4.2, 3.2), (0.0, 0.0)),
        ((4.2, 3.2), (0.0, 0.0)),
        ((4.4, -3.4), (0.0, 0.0)),
    ]:
        door = door.union(
            _raised_bar_between(
                cq,
                (
                    icon_center[0] + start[0] * icon_scale,
                    icon_center[1] + start[1] * icon_scale,
                ),
                (
                    icon_center[0] + end[0] * icon_scale,
                    icon_center[1] + end[1] * icon_scale,
                ),
                icon_line_width,
                raised_brand_relief,
                door_top_z,
                surface_chamfer,
            )
        )
    brand_icon_feature_count = len(icon_nodes) + 4

    reference_models = [
        battery_reference,
        heltec_reference,
        regulator_reference,
        sma_bulkhead_reference,
        antenna_keepout_reference,
        wire_channel_reference,
        field_gland_reference,
    ]
    closed = _combine_models(
        cq,
        [tray, door, hinge_pin_model, display_reference, gland_reference, *reference_models],
    )
    hinge_outer = _number(params, "hinge_barrel_outer_diameter_mm", 8.8)
    hinge_x = -outer_x / 2 - hinge_outer / 2 + min(1.2, hinge_outer / 4)
    hinge_z = door_z + door_thickness / 2
    open_angle = _number(params, "assembly_door_open_angle_degrees", 72.0)
    door_open_group = _combine_models(cq, [door, display_reference])
    door_open_group = _transform_about_hinge(door_open_group, hinge_x, hinge_z, -open_angle)
    door_open = _combine_models(
        cq,
        [tray, door_open_group, hinge_pin_model, gland_reference, *reference_models],
    )
    exploded = _combine_models(
        cq,
        [
            rear_panel_core.translate((-12, -10, 0)),
            rear_pod_module.translate((-12, 24, 18)),
            door.translate((34, 0, 10)),
            hinge_pin_model.translate((-18, 0, 6)),
            display_reference.translate((34, 0, -10)),
            gland_reference.translate((0, -18, 0)),
            battery_reference.translate((0, 0, 34)),
            heltec_reference.translate((-18, 18, 26)),
            regulator_reference.translate((18, -18, 26)),
            sma_bulkhead_reference.translate((16, 8, 10)),
            field_gland_reference.translate((-18, 24, 14)),
            antenna_keepout_reference.translate((24, 16, 0)),
            wire_channel_reference.translate((0, 12, 20)),
        ],
    )
    power_rf_layout = _combine_models(
        cq,
        [
            battery_reference.translate((0, 0, -pod_base_z - pod_floor)),
            heltec_reference.translate((0, 0, -top_z - standoff_height)),
            regulator_reference.translate((0, 0, -top_z - standoff_height)),
            sma_bulkhead_reference.translate((0, 0, -sma_z)),
            field_gland_reference.translate((0, 0, -field_gland_z)),
            wire_channel_reference.translate((0, 0, -top_z - standoff_height)),
            antenna_keepout_reference.translate((0, 0, -sma_z)),
        ],
    )

    door_print = door.translate((0, 0, -door_z))
    rear_panel_print = rear_panel_core
    rear_pod_print = rear_pod_module.translate((0, -pod_center_y, -pod_base_z))

    k1_max_combined_gap = 8.0
    k1_max_combined = _combine_models(
        cq,
        [
            tray.translate((0, -(outer_y + k1_max_combined_gap) / 2, 0)),
            door_print.translate((0, (outer_y + k1_max_combined_gap) / 2, 0)),
        ],
    )

    part_replacements = {
        "rear_tray": replace(
            next(part for part in base.assembly.parts if part.id == "rear_tray"),
            name="Rear tray with long-run battery pod, SMA boss, and macro ribs",
            model=tray,
            role="assembly-reference",
            material_hint="reference only; monolithic rear tray is blocked for printing",
            notes=(
                "Assembly-review body only. Use rear_panel_core and rear_battery_pod "
                "for component-level K1 print plates."
            ),
        ),
        "front_display_door": replace(
            next(part for part in base.assembly.parts if part.id == "front_display_door"),
            name="Front display door with raised CBBS surface treatment",
            model=door_print,
            material_hint="ASA, raised CBBS lettering and contour rails",
            notes=(
                "Component-level print body translated to build-plate Z; raised branding "
                "and contour rails are internal-review printability features."
            ),
            occurrence={
                "name": "CBBS P070 front display door",
                "transform": {
                    "translation_mm": {"x": 0.0, "y": 0.0, "z": door_z},
                    "rotation_degrees": {"x": 0.0, "y": 0.0, "z": 0.0},
                },
            },
        ),
    }
    parts = [part_replacements.get(part.id, part) for part in base.assembly.parts]
    parts.extend(
        [
            GeneratedAssemblyPart(
                id="rear_panel_core",
                name="Rear panel core with hinge and mount tabs",
                model=rear_panel_print,
                role="print",
                material_hint="ASA, 3.2 mm walls, panel-only plate",
                notes=(
                    "Component-level K1 print body. Battery pod is separated to avoid a "
                    "single-piece rear tray print."
                ),
                occurrence={
                    "name": "CBBS P070 rear panel core print body",
                    "transform": {
                        "translation_mm": {"x": 0.0, "y": 0.0, "z": 0.0},
                        "rotation_degrees": {"x": 0.0, "y": 0.0, "z": 0.0},
                    },
                },
                support_risk={
                    "level": "medium",
                    "notes": "Hinge barrels remain ASA validation blockers; print as its own plate.",
                },
            ),
            GeneratedAssemblyPart(
                id="rear_battery_pod",
                name="Separate rear battery and electronics pod",
                model=rear_pod_print,
                role="print",
                material_hint="ASA, pod-only plate with macro ribs and electronics bosses",
                notes=(
                    "Component-level K1 print body centered for slicing. In assembly it is "
                    "a sidecar pod connected to the display rear panel by a narrow printed tongue."
                ),
                occurrence={
                    "name": "CBBS P070 rear battery/electronics pod print body",
                    "transform": {
                        "translation_mm": {"x": 0.0, "y": pod_center_y, "z": pod_base_z},
                        "rotation_degrees": {"x": 0.0, "y": 0.0, "z": 0.0},
                    },
                },
                support_risk={
                    "level": "high",
                    "notes": "Deep pod, SMA boss, and macro ribs require local ASA support review.",
                },
            ),
            GeneratedAssemblyPart(
                id="heltec_v2_reference",
                name="Heltec WiFi LoRa 32 V2 reference envelope",
                model=heltec_reference,
                role="hardware-reference",
                material_hint="reference only",
                notes="Board revision, connector height, and antenna route remain measurement blockers.",
            ),
            GeneratedAssemblyPart(
                id="lifepo4_battery_reference",
                name="Bioenno BLF-0612C battery reference envelope",
                model=battery_reference,
                role="hardware-reference",
                material_hint="reference only",
                notes="Battery cable exits, retention strap, and heat behavior remain measurement blockers.",
            ),
            GeneratedAssemblyPart(
                id="buckboost_regulator_reference",
                name="Pololu S13V30F5 regulator reference envelope",
                model=regulator_reference,
                role="hardware-reference",
                material_hint="reference only",
                notes="Terminal/header height and regulator heat must be measured.",
            ),
            GeneratedAssemblyPart(
                id="sma_bulkhead_reference",
                name="Panel SMA bulkhead reference",
                model=sma_bulkhead_reference,
                role="hardware-reference",
                material_hint="reference only",
                notes="SMA versus RP-SMA and panel stack must be physically verified.",
            ),
            GeneratedAssemblyPart(
                id="field_gland_reference",
                name="LAPP SKINTOP STR NPT 3/4 field-entry reference",
                model=field_gland_reference,
                role="hardware-reference",
                material_hint="reference only",
                notes="Article 53016150 fit, torque, cable stack, and printed thread behavior must be physically verified.",
            ),
            GeneratedAssemblyPart(
                id="antenna_keepout_reference",
                name="External 915 MHz antenna keepout reference",
                model=antenna_keepout_reference,
                role="hardware-reference",
                material_hint="reference only",
                notes="Keepout is oversized for antenna sweep and RF review; no enclosure class is claimed.",
            ),
            GeneratedAssemblyPart(
                id="wire_channel_reference",
                name="RF pigtail wire-channel reference",
                model=wire_channel_reference,
                role="hardware-reference",
                material_hint="reference only",
                notes="Cable strain relief and bend radius must be measured with the actual pigtail.",
            ),
        ]
    )

    print_part_bounds = {
        part.id: _model_bounds_mm(part.model)
        for part in parts
        if part.role == "print"
    }
    brim_margin = 6.0
    layout_spacing = 8.0
    rear_panel_bounds = print_part_bounds["rear_panel_core"]
    rear_pod_bounds = print_part_bounds["rear_battery_pod"]
    door_bounds = print_part_bounds["front_display_door"]
    monolithic_tray_bounds = _model_bounds_mm(tray)
    rear_panel_fits_k1 = _fits_single_plate(rear_panel_bounds, 220.0, 220.0, brim_margin)
    rear_pod_fits_k1 = _fits_single_plate(rear_pod_bounds, 220.0, 220.0, brim_margin)
    door_fits_k1 = _fits_single_plate(door_bounds, 220.0, 220.0, brim_margin)
    component_fits_k1 = rear_panel_fits_k1 and rear_pod_fits_k1 and door_fits_k1
    monolithic_tray_fits_k1 = _fits_single_plate(
        monolithic_tray_bounds,
        220.0,
        220.0,
        brim_margin,
    )
    k1_combined_fit = _fits_two_part_plate(
        monolithic_tray_bounds,
        door_bounds,
        220.0,
        220.0,
        brim_margin,
        layout_spacing,
    )
    k1_max_combined_fit = _fits_two_part_plate(
        monolithic_tray_bounds,
        door_bounds,
        300.0,
        300.0,
        brim_margin,
        layout_spacing,
    )
    effective_xy_limit = {"x": 208.0, "y": 208.0}
    k1_component_layouts = {
        "k1-component-rear-panel": {
            "printer": "Creality K1/K1C/K1 SE",
            "plate_mm": {"x": 220.0, "y": 220.0},
            "effective_xy_limit_with_6mm_brim_mm": effective_xy_limit,
            "brim_margin_each_side_mm": brim_margin,
            "parts": ["rear_panel_core"],
            "bounds_mm": rear_panel_bounds,
            "fits_with_6mm_brim": rear_panel_fits_k1,
            "accepted": rear_panel_fits_k1,
            "orientation": "rear panel back on build plate; hinge axis along Y",
        },
        "k1-component-rear-pod": {
            "printer": "Creality K1/K1C/K1 SE",
            "plate_mm": {"x": 220.0, "y": 220.0},
            "effective_xy_limit_with_6mm_brim_mm": effective_xy_limit,
            "brim_margin_each_side_mm": brim_margin,
            "parts": ["rear_battery_pod"],
            "bounds_mm": rear_pod_bounds,
            "fits_with_6mm_brim": rear_pod_fits_k1,
            "accepted": rear_pod_fits_k1,
            "orientation": "pod floor on build plate; inspect SMA boss support before ASA print",
        },
        "k1-component-front-door": {
            "printer": "Creality K1/K1C/K1 SE",
            "plate_mm": {"x": 220.0, "y": 220.0},
            "effective_xy_limit_with_6mm_brim_mm": effective_xy_limit,
            "brim_margin_each_side_mm": brim_margin,
            "parts": ["front_display_door"],
            "bounds_mm": door_bounds,
            "fits_with_6mm_brim": door_fits_k1,
            "accepted": door_fits_k1,
            "orientation": "front face up; door translated to bed Z for slicer review",
        },
    }
    k1_margins = {
        part_id: {
            axis: round(effective_xy_limit[axis] - bounds[axis], 4)
            for axis in ("x", "y")
        }
        for part_id, bounds in print_part_bounds.items()
    }
    minimum_k1_margin = round(
        min(axis_margin for margins in k1_margins.values() for axis_margin in margins.values()), 4
    )

    metadata = {
        **base.assembly.metadata,
        "schema": "cbbs-cad/p070-heltec-outdoor-assembly-metadata/v1",
        "variant": "p070_heltec_outdoor_controller_enclosure",
        "outdoor_exposure_mapping": "outdoor-blocked",
        "review": {
            "baseline_run_id": "fusion-20260503T022638Z",
            "review_status": "generated-fusion-baseline-clean; physical-validation-blocked",
            "review_record": "3d-print-work/reviews/p070-heltec-outdoor-model-review.md",
            "k1_margin_mm": {
                "by_part": k1_margins,
                "minimum_split_margin_mm": minimum_k1_margin,
            },
            "k1_margin_warning": minimum_k1_margin < 2.0,
            "surface_feature_clearance_mm": front_rail_clearance,
            "surface_feature_edge_chamfer_mm": surface_chamfer,
            "physical_validation_blockers": concept.open_measurement_blockers,
        },
        "blocked_claims": [
            "enclosure protection class",
            "whole-system runtime",
            "RF range",
            "field readiness",
        ],
        "power_layout": {
            "battery_reference": "bioenno_blf_0612c_lifepo4_pack",
            "regulator_reference": "pololu_s13v30f5_regulator",
            "charger_reference": "bioenno_bpc_0602dc_charger_reference",
            "charger_location": "external-only",
            "battery_service_bay_mm": {
                "x": battery_bay_x,
                "y": battery_bay_y,
                "z": battery_bay_z,
            },
            "battery_orientation": (
                "115 mm battery length along pod X; battery pod is a sidecar connected "
                "along +Y instead of a vertical stack on the display enclosure"
            ),
            "regulator_bay_mm": regulator_bay,
            "runtime_status": "blocked until measured with display brightness, radio duty cycle, regulator heat, and enclosure temperature",
        },
        "rf_layout": {
            "heltec_reference": "heltec_wifi_lora_32_v2",
            "antenna_reference": "taoglas_ti_96_a113_915mhz_antenna",
            "pigtail_reference": "adafruit_sma_ufl_pigtail_851",
            "heltec_bay_mm": heltec_bay,
            "antenna_keepout_mm": {
                "diameter": antenna_keepout_diameter,
                "external_sweep": antenna_keepout_sweep,
            },
            "connector_blockers": [
                "Confirm IPEX/uFL fit on the actual Heltec V2 board.",
                "Confirm SMA versus RP-SMA before drilling or release review.",
                "Confirm RF behavior with printed material and installed display electronics.",
            ],
        },
        "field_cable_entry": {
            "schema": "cbbs-cad/field-cable-entry/v1",
            "hardware_ref": "lapp_skintop_str_npt_3_4_reference",
            "article_number": str(field_gland.features.get("article_number", "53016150")),
            "thread": "3/4 NPT",
            "thread_mode": "segmented_printed_internal_thread",
            "thread_generation_status": "prototype-modeled; coupon-fit-required",
            "placement": {
                "part": "rear_battery_pod",
                "face": "+Y side wall",
                "center_mm": {
                    "x": round(field_gland_x, 4),
                    "y": round(field_gland_y_start, 4),
                    "z": round(field_gland_z, 4),
                },
                "separated_from_rf_sma": True,
            },
            "boss_outer_diameter_mm": round(field_gland_boss_outer, 4),
            "prototype_thread": field_thread_record,
            "support_features": {
                "count": len(field_gland_support_records),
                "records": field_gland_support_records,
                "verification_status": "physical-print-required",
            },
            "source_refs": [
                "p070_npt_thread_entry_findings",
                "lapp_skintop_str_npt_3_4_reference",
            ],
            "blocked_claims": [
                "enclosure rating",
                "cable pullout rating",
                "thread torque rating",
                "field readiness",
            ],
            "validation_required": [
                "thread-fit coupon",
                "physical LAPP 53016150 gland engagement",
                "service torque check",
                "cable stack and bend-radius measurement",
                "cable retention test",
            ],
        },
        "wire_routing": {
            "schema": "cbbs-cad/wire-routing/v1",
            "truth_state": "internal review",
            "routes": [
                {
                    "id": "field_entry_to_regulator",
                    "purpose": "main field-wire trunk from 3/4 NPT entry toward regulator bay",
                    "channel_width_mm": round(field_wire_trunk_width, 4),
                    "verification_status": "pending-measurement",
                },
                {
                    "id": "regulator_to_heltec_power",
                    "purpose": "low-voltage regulator-to-Heltec routing aid",
                    "channel_width_mm": round(wire_channel_width, 4),
                    "verification_status": "pending-measurement",
                },
                {
                    "id": "heltec_to_sma_rf",
                    "purpose": "RF pigtail routing aid kept separate from main field-wire trunk",
                    "channel_width_mm": round(wire_channel_width, 4),
                    "verification_status": "pending-measurement",
                },
            ],
            "rail_count": len(wire_route_records),
            "rail_records": wire_route_records,
            "blocked_claims": [
                "measured bend radius",
                "field cable stack fit",
                "RF performance",
                "strain-relief acceptance",
            ],
        },
        "mechanical_reinforcement": {
            **base.assembly.metadata.get("mechanical_reinforcement", {}),
            "rear_pod_wall_thickness_mm": pod_wall,
            "rear_pod_floor_thickness_mm": pod_floor,
            "rear_pod_sidecar_connected": True,
            "rear_pod_floor_ribs": {
                "count": len(rear_pod_floor_rib_records),
                "records": rear_pod_floor_rib_records,
                "width_mm": rib_width,
                "height_mm": rib_height,
                "symmetric": True,
            },
            "rear_pod_side_wall_ledges": {
                "count": len(rear_pod_side_ledge_records),
                "records": rear_pod_side_ledge_records,
                "width_mm": rib_width,
                "height_mm": rib_height,
            },
            "ribbed_battery_pod_walls": True,
            "battery_strap_slots": 2,
            "reinforced_wall_tabs": len(wall_points),
            "field_gland_support_webs": {
                "count": len(field_gland_support_records),
                "records": field_gland_support_records,
                "threaded_boss_outer_diameter_mm": round(field_gland_boss_outer, 4),
            },
            "wire_route_rails": {
                "count": len(wire_route_records),
                "records": wire_route_records,
                "verification_status": "pending-measurement",
            },
            "drip_lip_reference_surface": True,
            "gasket_reference_surface": True,
            "venting_review": "blocked",
        },
        "hardware_placement": {
            "truth_state": "internal review",
            "display_mount": {
                "verified_pattern": "Nextion P070 174.6 x 101.6 mm boss coordinates",
                "thread_mode": "m3_printed_pilot",
                "validation_status": "physical-print-required",
            },
            "alignment_aids": hardware_alignment_records,
            "blocked_mounting_claims": [
                "Heltec screw-hole coordinates",
                "regulator screw-hole coordinates",
                "heat-set insert hole sizes",
                "RF route strain-relief acceptance",
                "field-wire cable-stack fit",
            ],
            "heat_set_inserts": {
                "status": "deferred",
                "selected_insert_part_number": None,
                "reason": (
                    "Insert hole diameter, depth, and boss sizing require a selected "
                    "insert part number, material, and installation method."
                ),
            },
            "source_refs": [
                "p070_structural_strengthening_findings",
                "p070_npt_thread_entry_findings",
                "heltec_v2_pdf",
                "pololu_s13v30f5_product_page",
                "cbbs_candidate_bom_standards",
            ],
        },
        "mechanical_interface": {
            "schema": "cbbs-cad/p070-pod-interface/v1",
            "rear_pod_relation": "sidecar-connected",
            "connector_axis": "+Y",
            "display_body_y_max_mm": round(outer_y / 2, 4),
            "rear_pod_body_y_min_mm": round(pod_body_min_y, 4),
            "rear_pod_body_center_y_mm": round(pod_center_y, 4),
            "body_clearance_from_display_y_mm": round(pod_connector_length, 4),
            "connector": {
                "type": "printed tongue and landing",
                "width_mm": round(pod_connector_width, 4),
                "length_mm": round(pod_connector_length, 4),
                "overlap_each_end_mm": round(pod_connector_overlap, 4),
                "z_base_mm": round(pod_base_z, 4),
                "height_mm": round(pod_floor, 4),
            },
            "anti_mash_rule": (
                "Rear pod body must remain outside the display enclosure Y footprint; "
                "only the connector tongue may overlap the display-side landing."
            ),
        },
        "surface_treatment": {
            "truth_state": "internal review",
            "style_intent": "futuristic macro contour ribs with raised CBBS marking",
            "source_refs": [
                "p070_futuristic_surface_reinforcement_findings",
                "cbbs_brand_assets",
                "cbbs_brand_logo_primary_svg",
                "prusa_fdm_modeling_guidance",
                "xometry_fdm_mini_guide",
                "efunda_rib_design_guidance",
                "cadquery_text_docs",
            ],
            "front_contour_rails": {
                "count": front_contour_rail_count,
                "width_mm": front_rail_width,
                "height_mm": front_rail_height,
                "window_clearance_mm": front_rail_clearance,
                "placement": "raised segmented rails outside the P070 display window",
            },
            "rear_pod_macro_ribs": {
                "count": macro_rib_count,
                "width_mm": macro_rib_width,
                "protrusion_mm": macro_rib_height,
                "pitch_mm": macro_rib_pitch,
                "placement": "external sidecar pod rails outside the display enclosure footprint",
            },
            "mount_tab_accent_ribs": {
                "count": mount_tab_accent_count,
                "width_mm": macro_rib_width,
                "height_mm": macro_rib_height,
            },
            "raised_brand": {
                "text": "CBBS",
                "text_source": "public/assets/brand/logo-primary.svg",
                "icon_source": "public/assets/brand/logo-primary.svg",
                "text_font_requested": "DejaVu Sans bold",
                "text_font_used": brand_text_font_used,
                "text_font_size_mm": raised_brand_text_font_size,
                "relief_mm": raised_brand_relief,
                "icon_reference_diameter_mm": raised_brand_icon_diameter,
                "icon_feature_count": brand_icon_feature_count,
                "edge_chamfer_mm": surface_chamfer,
                "exact_brand_font_blocker": (
                    "Inter and Space Grotesk font files are not present in this repository."
                ),
            },
            "printability_blockers": [
                "Print raised lettering and contour rails before accepting relief heights.",
                "Confirm macro ribs do not interfere with wall mounting or service handling.",
                "Confirm future vent placement remains clear before sealing review.",
            ],
            "blocked_claims": [
                "weatherproofing",
                "dustproofing",
                "IP rating",
                "NEMA rating",
                "IK rating",
                "RF range",
                "field readiness",
            ],
        },
        "structural_review": {
            **base.assembly.metadata.get("structural_review", {}),
            "schema": "cbbs-cad/structural-review/v1",
            "truth_state": concept.truth_state,
            "source_refs": [
                "p070_structural_strengthening_findings",
                "p070_npt_thread_entry_findings",
                "p070_hinged_wall_enclosure_spec",
                "p070_futuristic_surface_reinforcement_findings",
                "p070_heltec_power_rf_findings",
                "heltec_v2_pdf",
                "pololu_s13v30f5_product_page",
                "lapp_skintop_str_npt_3_4_reference",
                "prusa_fdm_modeling_guidance",
                "prusa_asa_guidance",
            ],
            "strengthened_features": {
                **base.assembly.metadata.get("structural_review", {}).get(
                    "strengthened_features",
                    {},
                ),
                "rear_pod_floor_ribs": len(rear_pod_floor_rib_records),
                "rear_pod_side_wall_ledges": len(rear_pod_side_ledge_records),
                "battery_alignment_aids": hardware_alignment_records["battery"]["feature_count"],
                "heltec_alignment_aids": hardware_alignment_records["heltec_v2"]["feature_count"],
                "regulator_alignment_aids": hardware_alignment_records["regulator"][
                    "feature_count"
                ],
                "rf_route_alignment_rails": hardware_alignment_records["rf_route"][
                    "feature_count"
                ],
                "field_gland_threaded_boss": 1,
                "field_gland_support_webs": len(field_gland_support_records),
                "wire_route_rails": len(wire_route_records),
            },
            "k1_margins_mm": {
                "by_part": k1_margins,
                "minimum_component_margin_mm": minimum_k1_margin,
                "legacy_or_combined_plate_accepted": False,
            },
            "weak_points_addressed": [
                *base.assembly.metadata.get("structural_review", {}).get(
                    "weak_points_addressed",
                    [],
                ),
                "rear pod floor flex",
                "rear pod side-wall flex",
                "large cable-entry boss root stress",
                "field-wire route ambiguity",
                "unmeasured electronics placement ambiguity",
                "RF pigtail route ambiguity",
            ],
            "remaining_blockers": [
                *concept.open_measurement_blockers,
                "physical ASA print of rear panel, rear pod, and front door",
                "hinge cycling and pin retention",
                "fastener pullout and printed-pilot behavior",
                "3/4 NPT printed thread fit, torque, cable stack, and cable retention",
                "heat, RF, and service validation with actual hardware",
            ],
            "blocked_claims": [
                "strength rating",
                "impact rating",
                "weatherproofing",
                "dustproofing",
                "IP rating",
                "NEMA rating",
                "runtime",
                "RF range",
                "field readiness",
            ],
            "validation_required": [
                "physical ASA print",
                "hinge cycling",
                "fastener pullout",
                "3/4 NPT thread-fit coupon",
                "field cable retention",
                "heat validation",
                "RF validation",
                "service validation",
            ],
        },
        "k1_fit": {
            "print_part_bounds_mm": print_part_bounds,
            "effective_xy_limit_with_6mm_brim_mm": effective_xy_limit,
            "component_split_required": True,
            "component_margin_mm": k1_margins,
            "minimum_component_margin_mm": minimum_k1_margin,
            "fits_xy_with_6mm_brim": component_fits_k1,
            "component_level_plates": k1_component_layouts,
            "monolithic_rear_tray": {
                "parts": ["rear_tray"],
                "bounds_mm": monolithic_tray_bounds,
                "fits_with_6mm_brim": monolithic_tray_fits_k1,
                "accepted": False,
                "reason": "Rear panel and rear battery pod must be printed as separate components.",
            },
            "combined_k1_plate": {
                **k1_combined_fit,
                "accepted": False,
                "reason": "P070 outdoor enclosure is blocked from single-piece or combined K1 printing.",
            },
            "combined_k1_max_plate": {
                **k1_max_combined_fit,
                "accepted": False,
                "reason": "Large-format combined layout is not accepted for component-level validation.",
            },
        },
        "print_layouts": {
            **k1_component_layouts,
            "k1-plate-tray": {
                "printer": "Creality K1/K1C/K1 SE",
                "plate_mm": {"x": 220.0, "y": 220.0},
                "effective_xy_limit_with_6mm_brim_mm": {"x": 208.0, "y": 208.0},
                "brim_margin_each_side_mm": brim_margin,
                "parts": ["rear_tray"],
                "bounds_mm": monolithic_tray_bounds,
                "fits_with_6mm_brim": monolithic_tray_fits_k1,
                "accepted": False,
                "reason": "Legacy monolithic rear tray view retained for assembly review only.",
                "orientation": "blocked; use k1-component-rear-panel and k1-component-rear-pod",
            },
            "k1-plate-door": {
                "printer": "Creality K1/K1C/K1 SE",
                "plate_mm": {"x": 220.0, "y": 220.0},
                "effective_xy_limit_with_6mm_brim_mm": {"x": 208.0, "y": 208.0},
                "brim_margin_each_side_mm": brim_margin,
                "parts": ["front_display_door"],
                "bounds_mm": door_bounds,
                "fits_with_6mm_brim": door_fits_k1,
                "accepted": False,
                "alias_for": "k1-component-front-door",
                "reason": "Legacy door plate key retained only for compatibility.",
                "orientation": "use k1-component-front-door",
            },
            "k1-combined": {
                "printer": "Creality K1/K1C/K1 SE",
                "plate_mm": {"x": 220.0, "y": 220.0},
                "brim_margin_each_side_mm": brim_margin,
                "parts": ["rear_tray", "front_display_door"],
                **k1_combined_fit,
                "accepted": False,
                "reason": "Single-piece or combined K1 printing is blocked for this model.",
            },
            "k1-max-combined": {
                "printer": "Creality K1 Max",
                "plate_mm": {"x": 300.0, "y": 300.0},
                "brim_margin_each_side_mm": brim_margin,
                "part_spacing_mm": layout_spacing,
                "parts": ["rear_tray", "front_display_door"],
                **k1_max_combined_fit,
                "accepted": False,
                "reason": "Large-format combined layout is blocked until component prints are validated.",
            },
            "hardware-reference": {
                "parts": [
                    "hinge_pin",
                    "display_reference",
                    "m12_gland_reference",
                    "heltec_v2_reference",
                    "lifepo4_battery_reference",
                    "buckboost_regulator_reference",
                    "sma_bulkhead_reference",
                    "field_gland_reference",
                    "antenna_keepout_reference",
                    "wire_channel_reference",
                ],
                "purpose": "Reference-only hardware envelopes for Fusion review.",
            },
        },
    }
    if not component_fits_k1:
        metadata["print_layouts"]["k1-segmented-fallback"] = {
            "accepted": True,
            "reason": "One or more component print parts exceeds the 208 x 208 mm effective K1 brim envelope.",
            "fallbacks": ["K1 Max", "segmented rear pod review"],
        }

    assembly = GeneratedAssembly(
        parts=parts,
        views={
            **base.assembly.views,
            "closed-front": closed,
            "closed-isometric": closed,
            "door-open": door_open,
            "exploded": exploded,
            "k1-component-rear-panel": rear_panel_print,
            "k1-component-rear-pod": rear_pod_print,
            "k1-component-front-door": door_print,
            "k1-plate-tray": tray,
            "k1-plate-door": door_print,
            "k1-max-combined": k1_max_combined,
            "power-rf-layout": power_rf_layout,
        },
        metadata=metadata,
    )
    return GeneratedModel(model=closed, assembly=assembly)


def _build_heltec_v2_rugged_tray_gauge(
    cq: Any, concept: ConceptSpec, hardware: HardwareSpec
) -> Any:
    d = hardware.dimensions
    params = concept.parameters
    clearance = _number(params, "board_clearance_mm", 1.5)
    wall = _number(params, "wall_thickness_mm", 3.0)
    floor = _number(params, "floor_thickness_mm", 2.0)
    side_height = _number(params, "side_wall_height_mm", 8.0)
    corner = _number(params, "corner_radius_mm", 3.0)
    service_notch_width = _number(params, "service_notch_width_mm", 10.0)
    service_notch_depth = _number(params, "service_notch_depth_mm", 4.0)

    inner_x = d["board_length_mm"] + clearance * 2
    inner_y = d["board_width_mm"] + clearance * 2
    outer_x = inner_x + wall * 2
    outer_y = inner_y + wall * 2
    total_z = floor + side_height

    model = rounded_plate(cq, outer_x, outer_y, total_z, corner)
    model = model.faces(">Z").workplane().rect(inner_x, inner_y).cutBlind(-side_height)
    notch = box(cq, service_notch_depth, service_notch_width, side_height + 0.2).translate(
        (-outer_x / 2 + service_notch_depth / 2, 0, floor)
    )
    return model.cut(notch)


def _build_screw_boss_coupon(cq: Any, concept: ConceptSpec) -> Any:
    params = concept.parameters
    length = _number(params, "length_mm", 60.0)
    width = _number(params, "width_mm", 24.0)
    base = _number(params, "base_thickness_mm", 3.0)
    boss_outer = _number(params, "boss_outer_diameter_mm", 7.0)
    boss_height = _number(params, "boss_height_mm", 6.0)
    pilot_sizes = params.get("pilot_hole_diameters_mm", [2.0, 2.4, 2.8])
    if not isinstance(pilot_sizes, list) or not pilot_sizes:
        raise ValueError("pilot_hole_diameters_mm must be a non-empty list")

    spacing = length / (len(pilot_sizes) + 1)
    points = [(-length / 2 + spacing * (index + 1), 0) for index in range(len(pilot_sizes))]
    model = _box(cq, length, width, base)
    bosses = cq.Workplane("XY").pushPoints(points).circle(boss_outer / 2).extrude(boss_height)
    bosses = bosses.translate((0, 0, base))
    model = model.union(bosses)
    for point, diameter in zip(points, pilot_sizes, strict=True):
        model = model.faces(">Z").workplane().center(point[0], point[1]).hole(float(diameter))
    return model


def _build_heat_set_insert_coupon(cq: Any, concept: ConceptSpec) -> Any:
    params = concept.parameters
    length = _number(params, "length_mm", 58.0)
    width = _number(params, "width_mm", 22.0)
    thickness = _number(params, "thickness_mm", 7.0)
    holes = params.get("insert_hole_diameters_mm", [3.8, 4.0, 4.2])
    if not isinstance(holes, list) or not holes:
        raise ValueError("insert_hole_diameters_mm must be a non-empty list")

    spacing = length / (len(holes) + 1)
    points = [(-length / 2 + spacing * (index + 1), 0) for index in range(len(holes))]
    model = _box(cq, length, width, thickness)
    for point, diameter in zip(points, holes, strict=True):
        model = model.faces(">Z").workplane().center(point[0], point[1]).hole(float(diameter))
    return model


def _build_oled_window_coupon(cq: Any, concept: ConceptSpec) -> Any:
    params = concept.parameters
    outer_x = _number(params, "outer_x_mm", 42.0)
    outer_y = _number(params, "outer_y_mm", 22.0)
    thickness = _number(params, "thickness_mm", 2.0)
    window_x = _number(params, "window_x_mm", 28.0)
    window_y = _number(params, "window_y_mm", 12.0)
    return _box(cq, outer_x, outer_y, thickness).faces(">Z").workplane().rect(
        window_x, window_y
    ).cutThruAll()


def _build_cable_relief_coupon(cq: Any, concept: ConceptSpec) -> Any:
    params = concept.parameters
    length = _number(params, "length_mm", 50.0)
    width = _number(params, "width_mm", 30.0)
    thickness = _number(params, "thickness_mm", 3.0)
    slot_x = _number(params, "slot_x_mm", 18.0)
    slot_y = _number(params, "slot_y_mm", 6.0)
    model = _box(cq, length, width, thickness)
    return model.faces(">Z").workplane().rect(slot_x, slot_y).cutThruAll()


def _build_label_plate_coupon(cq: Any, concept: ConceptSpec) -> Any:
    params = concept.parameters
    length = _number(params, "length_mm", 64.0)
    width = _number(params, "width_mm", 22.0)
    thickness = _number(params, "thickness_mm", 1.2)
    hole_dia = _number(params, "corner_hole_diameter_mm", 2.5)
    inset = _number(params, "corner_hole_inset_mm", 5.0)
    model = _box(cq, length, width, thickness)
    points = [
        (-length / 2 + inset, -width / 2 + inset),
        (-length / 2 + inset, width / 2 - inset),
        (length / 2 - inset, -width / 2 + inset),
        (length / 2 - inset, width / 2 - inset),
    ]
    return model.faces(">Z").workplane().pushPoints(points).hole(hole_dia)


def _build_p070_surface_treatment_coupon(cq: Any, concept: ConceptSpec) -> Any:
    params = concept.parameters
    length = _number(params, "coupon_length_mm", 96.0)
    width = _number(params, "coupon_width_mm", 44.0)
    thickness = _number(params, "coupon_thickness_mm", 2.4)
    rail_width = _number(params, "front_contour_rail_width_mm", 1.8)
    rail_height = _number(params, "front_contour_rail_height_mm", 1.2)
    macro_rib_width = _number(params, "rear_pod_macro_rib_width_mm", 1.8)
    macro_rib_height = _number(params, "rear_pod_macro_rib_height_mm", 1.2)
    macro_rib_pitch = _number(params, "rear_pod_macro_rib_pitch_mm", 18.0)
    brand_relief = _number(params, "raised_brand_relief_mm", 1.2)
    brand_font_size = _number(params, "raised_brand_text_font_size_mm", 10.0)
    icon_diameter = _number(params, "raised_brand_icon_diameter_mm", 14.0)
    chamfer = _number(params, "surface_feature_edge_chamfer_mm", 0.2)

    model = rounded_plate(cq, length, width, thickness, 2.0)
    top_z = thickness

    rail_y = width / 2 - 8.0
    rail_span = length * 0.32
    rail_gap = length * 0.18
    for y in (-rail_y, rail_y):
        for sx in (-1.0, 1.0):
            center_x = sx * (rail_gap / 2 + rail_span / 2)
            model = model.union(
                _raised_bar_between(
                    cq,
                    (center_x - rail_span / 2, y),
                    (center_x + rail_span / 2, y),
                    rail_width,
                    rail_height,
                    top_z,
                    chamfer,
                )
            )

    rib_span = width - 16.0
    for x in _centered_pattern_positions(length - 36.0, macro_rib_pitch):
        if abs(x) < brand_font_size * 1.8:
            continue
        model = model.union(
            _raised_bar_between(
                cq,
                (x, -rib_span / 2),
                (x, rib_span / 2),
                macro_rib_width,
                macro_rib_height,
                top_z,
                chamfer,
            )
        )

    text_y = -width / 2 + 11.0
    model, _font_used = _add_raised_text(
        model,
        cq,
        "CBBS",
        4.0,
        text_y,
        brand_font_size,
        brand_relief,
        top_z,
    )

    icon_center = (-length / 2 + icon_diameter / 2 + 8.0, width / 2 - icon_diameter / 2 - 5.0)
    icon_ring_width = max(1.0, icon_diameter * 0.08)
    icon_line_width = max(1.0, rail_width * 0.55)
    model = model.union(
        _raised_annular_badge(
            cq,
            icon_center[0],
            icon_center[1],
            icon_diameter,
            icon_ring_width,
            brand_relief,
            top_z,
            chamfer,
        )
    )
    icon_scale = icon_diameter / 14.0
    icon_nodes = [
        (0.0, 0.0, 2.8),
        (-4.2, 3.2, 2.4),
        (4.2, 3.2, 2.4),
        (4.4, -3.4, 2.4),
    ]
    for dx, dy, diameter in icon_nodes:
        model = add_cylindrical_boss(
            model,
            cq,
            icon_center[0] + dx * icon_scale,
            icon_center[1] + dy * icon_scale,
            diameter * icon_scale,
            brand_relief,
            top_z,
        )
    for start, end in [
        ((-4.2, 3.2), (0.0, 0.0)),
        ((4.2, 3.2), (0.0, 0.0)),
        ((4.4, -3.4), (0.0, 0.0)),
    ]:
        model = model.union(
            _raised_bar_between(
                cq,
                (
                    icon_center[0] + start[0] * icon_scale,
                    icon_center[1] + start[1] * icon_scale,
                ),
                (
                    icon_center[0] + end[0] * icon_scale,
                    icon_center[1] + end[1] * icon_scale,
                ),
                icon_line_width,
                brand_relief,
                top_z,
                chamfer,
            )
        )

    return model


def _build_model(cq: Any, concept: ConceptSpec, hardware_by_id: dict[str, HardwareSpec]) -> Any:
    if concept.model_family == "heltec_v2_fit_card":
        return _build_heltec_fit_card(cq, concept, hardware_by_id[concept.hardware_refs[0]])
    if concept.model_family == "heltec_v2_rugged_tray_gauge":
        return _build_heltec_v2_rugged_tray_gauge(
            cq, concept, hardware_by_id[concept.hardware_refs[0]]
        )
    if concept.model_family == "p070_fit_frame":
        return _build_p070_fit_frame(cq, concept, hardware_by_id[concept.hardware_refs[0]])
    if concept.model_family == "p070_rugged_bezel_fit_frame":
        return _build_p070_rugged_bezel_fit_frame(
            cq, concept, hardware_by_id[concept.hardware_refs[0]]
        )
    if concept.model_family == "p070_hinged_wall_enclosure":
        return _build_p070_hinged_wall_enclosure(
            cq, concept, hardware_by_id[concept.hardware_refs[0]]
        )
    if concept.model_family == "p070_heltec_outdoor_controller_enclosure":
        return _build_p070_heltec_outdoor_controller_enclosure(cq, concept, hardware_by_id)
    if concept.model_family == "npt_3_4_thread_fit_coupon":
        return _build_npt_3_4_thread_fit_coupon(cq, concept)
    if concept.model_family == "p070_surface_treatment_coupon":
        return _build_p070_surface_treatment_coupon(cq, concept)
    if concept.model_family == "rugged_wall_section_coupon":
        return _build_rugged_wall_section_coupon(cq, concept)
    if concept.model_family == "gasket_flange_coupon":
        return _build_gasket_flange_coupon(cq, concept)
    if concept.model_family == "reinforced_mount_tab_coupon":
        return _build_reinforced_mount_tab_coupon(cq, concept)
    if concept.model_family == "cable_entry_boss_coupon":
        return _build_cable_entry_boss_coupon(cq, concept)
    if concept.model_family == "drip_lip_seam_coupon":
        return _build_drip_lip_seam_coupon(cq, concept)
    if concept.model_family == "screw_boss_coupon":
        return _build_screw_boss_coupon(cq, concept)
    if concept.model_family == "heat_set_insert_coupon":
        return _build_heat_set_insert_coupon(cq, concept)
    if concept.model_family == "oled_window_coupon":
        return _build_oled_window_coupon(cq, concept)
    if concept.model_family == "cable_relief_coupon":
        return _build_cable_relief_coupon(cq, concept)
    if concept.model_family == "label_plate_coupon":
        return _build_label_plate_coupon(cq, concept)
    raise ValueError(f"unsupported model_family: {concept.model_family}")


def _bounds_mm(model: Any) -> dict[str, float]:
    return _model_bounds_mm(model)


def _primary_model(generated: Any) -> Any:
    return generated.model if isinstance(generated, GeneratedModel) else generated


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _export_step(model: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    model.val().exportStep(str(path))


def _export_stl(model: Any, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    model.val().exportStl(
        str(path),
        tolerance=0.01,
        angularTolerance=0.2,
        ascii=True,
    )


def _export_assembly(
    concept: ConceptSpec,
    generated: GeneratedModel,
    output_dir: Path,
) -> dict[str, Any] | None:
    if not generated.assembly:
        return None

    assembly_dir = output_dir / "assembly" / concept.id
    part_records: list[dict[str, Any]] = []
    for part in generated.assembly.parts:
        files: dict[str, str] = {}
        if "step" in concept.outputs:
            step_path = assembly_dir / "parts" / f"{part.id}.step"
            _export_step(part.model, step_path)
            files["step"] = _display_path(step_path)
        if "stl" in concept.outputs:
            stl_path = assembly_dir / "parts" / f"{part.id}.stl"
            _export_stl(part.model, stl_path)
            files["stl"] = _display_path(stl_path)
        record = {
            "id": part.id,
            "name": part.name,
            "role": part.role,
            "material_hint": part.material_hint,
            "files": files,
            "bounds_mm": _bounds_mm(part.model),
        }
        if part.notes:
            record["notes"] = part.notes
        if part.occurrence:
            record["occurrence"] = part.occurrence
        if part.support_risk:
            record["support_risk"] = part.support_risk
        part_records.append(record)

    view_records: dict[str, dict[str, Any]] = {}
    for view, model in generated.assembly.views.items():
        step_path = assembly_dir / "views" / f"{concept.id}_{view}.step"
        _export_step(model, step_path)
        view_records[view] = {
            "file": _display_path(step_path),
            "bounds_mm": _bounds_mm(model),
        }

    return {
        "schema": "cbbs-cad/generated-assembly/v1",
        "mode": "component-parts",
        "parts": part_records,
        "views": view_records,
        "metadata": generated.assembly.metadata,
    }


def generate_concepts(
    bundle: SpecBundle,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    concept_ids: list[str] | None = None,
) -> dict[str, Any]:
    cq = _require_cadquery()
    output_dir.mkdir(parents=True, exist_ok=True)
    hardware_by_id = {item.id: item for item in bundle.hardware}
    requested = set(concept_ids or [])

    records: list[dict[str, Any]] = []
    skipped_records: list[dict[str, Any]] = []
    for concept in bundle.concepts:
        if requested and concept.id not in requested:
            continue
        if not concept.generation_enabled:
            message = "; ".join(concept.generation_blockers)
            if concept.id in requested:
                raise ValueError(f"concept {concept.id} is disabled for generation: {message}")
            skipped_records.append(
                {
                    "concept_id": concept.id,
                    "name": concept.name,
                    "model_family": concept.model_family,
                    "reason": message,
                }
            )
            continue
        generated_model = _build_model(cq, concept, hardware_by_id)
        model = _primary_model(generated_model)
        files: dict[str, str] = {}
        stem = concept.id

        if "step" in concept.outputs:
            step_path = output_dir / f"{stem}.step"
            _export_step(model, step_path)
            files["step"] = _display_path(step_path)

        if "stl" in concept.outputs:
            stl_path = output_dir / f"{stem}.stl"
            _export_stl(model, stl_path)
            files["stl"] = _display_path(stl_path)

        record: dict[str, Any] = {
            "concept_id": concept.id,
            "name": concept.name,
            "model_family": concept.model_family,
            "truth_state": concept.truth_state,
            "measurement_status": concept.measurement_status,
            "derivation_state": concept.derivation_state,
            "public_release": concept.public_release,
            "blocked_full_case": concept.blocked_full_case,
            "generation_enabled": concept.generation_enabled,
            "hardware_refs": concept.hardware_refs,
            "source_refs": [source.model_dump(mode="json") for source in concept.source_refs],
            "parameter_sources": {
                key: evidence.model_dump(mode="json")
                for key, evidence in concept.parameter_sources.items()
            },
            "image_refs": [image.model_dump(mode="json") for image in concept.image_refs],
            "source_conflicts": [
                conflict.model_dump(mode="json") for conflict in concept.source_conflicts
            ],
            "bounds_mm": _bounds_mm(model),
            "files": files,
        }
        if isinstance(generated_model, GeneratedModel):
            assembly = _export_assembly(concept, generated_model, output_dir)
            if assembly:
                record["assembly"] = assembly
        records.append(record)

    missing = requested - {record["concept_id"] for record in records}
    if missing:
        raise ValueError(f"unknown concept id(s): {', '.join(sorted(missing))}")

    manifest = {
        "schema": "cbbs-cad/generated-manifest/v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "generator": "cbbs-cad",
        "output_dir": _display_path(output_dir),
        "artifacts": records,
        "skipped_artifacts": skipped_records,
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
