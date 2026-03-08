"""Architecture tests for scripts catalog governance policy."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_scripts_catalog_governance_check_passes() -> None:
    """Scripts catalog policy must pass structural and lifecycle checks."""
    root = _project_root()
    result = subprocess.run(
        [
            sys.executable,
            "scripts/check_scripts_catalog.py",
            "--catalog",
            "scripts/catalog.yaml",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "Scripts catalog governance validation failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}\n"
    )
