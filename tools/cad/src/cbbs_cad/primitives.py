from __future__ import annotations

from typing import Any


def box(cq: Any, x: float, y: float, z: float) -> Any:
    return cq.Workplane("XY").box(x, y, z, centered=(True, True, False))


def _safe_radius(radius: float, *dimensions: float) -> float:
    if radius <= 0:
        return 0
    positive = [dimension for dimension in dimensions if dimension > 0]
    if not positive:
        return 0
    return max(0, min(radius, min(positive) / 2 - 0.01))


def fillet_vertical_edges(model: Any, radius: float, *dimensions: float) -> Any:
    safe_radius = _safe_radius(radius, *dimensions)
    if safe_radius <= 0:
        return model
    try:
        return model.edges("|Z").fillet(safe_radius)
    except Exception:
        return model


def rounded_plate(cq: Any, x: float, y: float, z: float, corner_radius: float = 0) -> Any:
    model = box(cq, x, y, z)
    return fillet_vertical_edges(model, corner_radius, x, y)


def rectangular_ring(
    cq: Any,
    outer_x: float,
    outer_y: float,
    inner_x: float,
    inner_y: float,
    z: float,
    corner_radius: float = 0,
) -> Any:
    model = cq.Workplane("XY").rect(outer_x, outer_y).rect(inner_x, inner_y).extrude(z)
    return fillet_vertical_edges(model, corner_radius, outer_x, outer_y, inner_x, inner_y)


def add_box_feature(
    model: Any,
    cq: Any,
    x: float,
    y: float,
    z: float,
    center_x: float,
    center_y: float,
    z_base: float,
) -> Any:
    feature = box(cq, x, y, z).translate((center_x, center_y, z_base))
    return model.union(feature)


def add_cylindrical_boss(
    model: Any,
    cq: Any,
    center_x: float,
    center_y: float,
    outer_diameter: float,
    height: float,
    z_base: float,
    hole_diameter: float | None = None,
) -> Any:
    boss = cq.Workplane("XY").center(center_x, center_y).circle(outer_diameter / 2)
    if hole_diameter:
        boss = boss.circle(hole_diameter / 2)
    boss = boss.extrude(height).translate((0, 0, z_base))
    return model.union(boss)
