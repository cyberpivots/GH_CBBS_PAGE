from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import yaml

from cbbs_cad.models import (
    ConceptSpec,
    HardwareSpec,
    PrinterSpec,
    SpecBundle,
    ToolingCandidateSpec,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DATA_DIR = REPO_ROOT / "3d-print-work" / "data"


def _load_mapping(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".json":
        data = json.loads(text)
    elif path.suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(text)
    else:
        raise ValueError(f"unsupported spec file extension: {path}")

    if not isinstance(data, dict):
        raise ValueError(f"spec file must contain a mapping: {path}")
    return data


def _default_spec_paths(data_dir: Path = DEFAULT_DATA_DIR) -> list[Path]:
    paths: list[Path] = []
    for subdir in ("hardware", "concepts", "printers", "tooling"):
        root = data_dir / subdir
        if root.exists():
            paths.extend(sorted(root.rglob("*.yaml")))
            paths.extend(sorted(root.rglob("*.yml")))
            paths.extend(sorted(root.rglob("*.json")))
    return paths


def load_specs(paths: Iterable[Path] | None = None, data_dir: Path = DEFAULT_DATA_DIR) -> SpecBundle:
    spec_paths = list(paths) if paths else _default_spec_paths(data_dir)
    hardware: list[HardwareSpec] = []
    concepts: list[ConceptSpec] = []
    printers: list[PrinterSpec] = []
    tooling: list[ToolingCandidateSpec] = []

    for path in spec_paths:
        data = _load_mapping(path)
        schema = data.get("schema")
        if schema == "cbbs-cad/hardware/v1":
            hardware.append(HardwareSpec.model_validate(data))
        elif schema == "cbbs-cad/concept/v1":
            concepts.append(ConceptSpec.model_validate(data))
        elif schema == "cbbs-cad/printer/v1":
            printers.append(PrinterSpec.model_validate(data))
        elif schema == "cbbs-cad/tooling-candidate/v1":
            tooling.append(ToolingCandidateSpec.model_validate(data))
        else:
            raise ValueError(f"unknown or missing schema in {path}: {schema!r}")

    return SpecBundle(hardware=hardware, concepts=concepts, printers=printers, tooling=tooling)


def bundle_to_manifest(bundle: SpecBundle) -> dict[str, Any]:
    return {
        "schema": "cbbs-cad/input-manifest/v1",
        "hardware": [item.model_dump(mode="json", by_alias=True) for item in bundle.hardware],
        "concepts": [item.model_dump(mode="json", by_alias=True) for item in bundle.concepts],
        "printers": [item.model_dump(mode="json", by_alias=True) for item in bundle.printers],
        "tooling": [item.model_dump(mode="json", by_alias=True) for item in bundle.tooling],
    }
