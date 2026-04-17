"""Architecture tests for scripts lifecycle registry coverage."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.mark.slow
@pytest.mark.timeout(300)
def test_scripts_lifecycle_registry_check_passes() -> None:
    """Lifecycle registry must cover all non-active scripts with valid entries."""
    root = _project_root()
    result = subprocess.run(
        [
            sys.executable,
            "scripts/engineering/repo/check_scripts_inventory.py",
            "--check-lifecycle",
            "--forbid-evaluate-active",
            "--lifecycle-registry",
            "configs/quality/scripts_lifecycle_registry.json",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "Scripts lifecycle registry validation failed.\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}\n"
    )
