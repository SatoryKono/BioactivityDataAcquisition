"""Lightweight guard for dashboard UX report artifacts on dashboard JSON changes."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import subprocess

import pytest

pytestmark = pytest.mark.integration

_DASHBOARD_GLOB = "grafana/dashboards/*.json"
_REPORTS_DIR = Path("docs/reports/dashboard-ux-checks")
_CHANGE_NOTES_PATH = Path("docs/03-guides/dashboards/dashboard-v2-updates.md")
POLICY_REVIEW_DATE = date(2026, 5, 19)


def _git_changed_files() -> list[str]:
    commands = (
        ["git", "diff", "--name-only", "origin/main...HEAD"],
        ["git", "diff", "--name-only", "HEAD~1..HEAD"],
        ["git", "diff", "--name-only", "--cached"],
    )
    for cmd in commands:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0 and result.stdout.strip():
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return []


def test_dashboard_json_changes_require_fresh_ux_report_and_change_note_link() -> None:
    changed_files = _git_changed_files()
    dashboard_changed = any(
        path.startswith("grafana/dashboards/") and path.endswith(".json")
        for path in changed_files
    )

    if not dashboard_changed:
        pytest.skip("No grafana/dashboards/*.json changes detected in git diff.")

    assert _REPORTS_DIR.is_dir(), "Missing docs/reports/dashboard-ux-checks directory"

    today = POLICY_REVIEW_DATE
    fresh_dates = {today.isoformat(), (today - timedelta(days=1)).isoformat()}
    fresh_reports = [
        _REPORTS_DIR / f"{report_date}.md"
        for report_date in sorted(fresh_dates)
        if (_REPORTS_DIR / f"{report_date}.md").exists()
    ]
    assert fresh_reports, (
        "Dashboard JSON changed, but no fresh UX report found. "
        "Expected docs/reports/dashboard-ux-checks/<today|yesterday>.md"
    )

    change_notes = _CHANGE_NOTES_PATH.read_text(encoding="utf-8")
    assert "docs/reports/dashboard-ux-checks/" in change_notes, (
        "Dashboard change notes must include a link to the UX report artifact path."
    )
