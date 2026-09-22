# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture tests for scripts deprecation backlog report generation."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest
from tests.helpers import repo_root


@pytest.mark.slow
@pytest.mark.timeout(600)
def test_scripts_deprecation_report_generation(
    tmp_path: Path, cached_subprocess_run
) -> None:
    """Inventory tool should generate markdown backlog for non-active scripts with cached results."""
    root = repo_root()

    cache_report = tmp_path / "scripts_deprecation_backlog_cached.md"

    result = cached_subprocess_run(
        [
            sys.executable,
            "scripts/engineering/repo/check_scripts_inventory.py",
            "--deprecation-report",
            str(cache_report),
        ],
        timeout=600,
        cwd=root,
    )
    assert result.returncode == 0, result.stderr
    assert cache_report.exists()

    # Copy to tmp_path for test isolation
    report_rel = tmp_path / "scripts_deprecation_backlog.md"
    report_rel.write_text(cache_report.read_text(encoding="utf-8"), encoding="utf-8")

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
