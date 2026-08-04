"""Subprocess contracts for directly executed Zed Python helpers."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]

ROOT = Path(__file__).resolve().parents[4]
DEV_SCRIPTS = ROOT / "scripts" / "engineering" / "dev"


@pytest.mark.parametrize(
    "script_name",
    [
        "zed_lint_imports.py",
        "zed_mypy.py",
        "zed_pytest_lane.py",
        "zed_run.py",
        "zed_vulture.py",
        "zed_xenon.py",
    ],
)
def test_zed_helper_bootstraps_repo_package_imports(
    script_name: str,
    tmp_path: Path,
) -> None:
    """A direct helper import must not rely on pytest adding the repo to sys.path."""
    script_path = DEV_SCRIPTS / script_name
    probe = f"import runpy; runpy.run_path({str(script_path)!r})"

    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", probe],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
