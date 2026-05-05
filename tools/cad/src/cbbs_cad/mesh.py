from __future__ import annotations

from pathlib import Path
from typing import Any


def _require_trimesh() -> Any:
    try:
        import trimesh
    except ImportError as exc:
        raise RuntimeError(
            "trimesh is required for mesh inspection. Run "
            "`uv run --project tools/cad cbbs-cad inspect-mesh ...` from the repo root."
        ) from exc
    return trimesh


def expand_mesh_paths(paths: list[Path]) -> list[Path]:
    expanded: list[Path] = []
    for path in paths:
        if path.is_dir():
            expanded.extend(sorted(path.rglob("*.stl")))
            expanded.extend(sorted(path.rglob("*.3mf")))
        elif path.exists():
            expanded.append(path)
        else:
            raise FileNotFoundError(path)
    return expanded


def inspect_meshes(paths: list[Path]) -> list[dict[str, Any]]:
    trimesh = _require_trimesh()
    records: list[dict[str, Any]] = []

    for path in expand_mesh_paths(paths):
        mesh = trimesh.load_mesh(path, force="mesh")
        broken_faces = []
        try:
            broken_faces = trimesh.repair.broken_faces(mesh)
        except Exception:
            broken_faces = []

        records.append(
            {
                "path": str(path),
                "faces": int(len(mesh.faces)),
                "vertices": int(len(mesh.vertices)),
                "watertight": bool(mesh.is_watertight),
                "bounds": mesh.bounds.round(4).tolist(),
                "extents_mm": mesh.extents.round(4).tolist(),
                "euler_number": int(mesh.euler_number),
                "broken_faces": int(len(broken_faces)),
            }
        )
    return records
