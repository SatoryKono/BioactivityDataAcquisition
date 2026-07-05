"""Architecture tests for scripts deprecation backlog report generation."""

from __future__ import annotations

from pathlib import Path

import pytest
from tests.helpers import repo_root, run_repo_python


@pytest.mark.slow
def test_scripts_deprecation_report_generation(tmp_path: Path) -> None:
    """Inventory tool should generate markdown backlog for non-active scripts."""
    root = repo_root()
    report_rel = tmp_path / "scripts_deprecation_backlog.md"

    result = run_repo_python(
        "scripts/engineering/repo/check_scripts_inventory.py",
        "--deprecation-report",
        str(report_rel),
        cwd=root,
    )
    assert result.returncode == 0, result.stderr
    assert report_rel.exists()

    content = report_rel.read_text(encoding="utf-8")
    assert "# Scripts Deprecation Backlog" in content
    assert (
        "| Script Path | Type | Reference Count | Owner | Lifecycle Decision | Suggested Next Step |"
        in content
    )
    assert "@bioetl-platform" in content
    assert "`internal_helper_orphan`" in content
    assert "## unknown" in content
    assert "## orphan" in content
    assert "## legacy" in content
