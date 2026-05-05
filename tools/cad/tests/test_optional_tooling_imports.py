from __future__ import annotations

import importlib.util
import subprocess
import sys
import textwrap

import pytest


@pytest.mark.skipif(
    importlib.util.find_spec("pyvista") is None,
    reason="PyVista is only installed with the optional mesh-eval dependency group",
)
def test_pyvista_import_does_not_emit_vtkgenericcell_errors() -> None:
    script = textwrap.dedent(
        """
        import importlib.metadata as md
        import pyvista as pv

        cube = pv.Cube()
        print(md.version("pyvista"), cube.n_points, cube.n_cells)
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    assert "vtkGenericCell" not in result.stderr
    assert "8 6" in result.stdout
