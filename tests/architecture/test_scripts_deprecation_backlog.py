"""Architecture tests for scripts deprecation backlog report generation."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.mark.slow
def test_scripts_deprecation_report_generation(tmp_path: Path) -> None:
    """Inventory tool should generate markdown backlog for non-active scripts."""
    root = _project_root()
    report_rel = tmp_path / "scripts_deprecation_backlog.md"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/engineering/repo/check_scripts_inventory.py",
            "--deprecation-report",
            str(report_rel),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert report_rel.exists()

    content = report_rel.read_text(encoding="utf-8")
    assert "# Scripts Deprecation Backlog" in content
    assert "## unknown" in content
    assert "## orphan" in content
    assert "## legacy" in content
