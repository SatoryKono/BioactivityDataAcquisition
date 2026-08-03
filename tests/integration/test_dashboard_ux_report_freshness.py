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
"""Lightweight guard for dashboard UX report artifacts on dashboard JSON changes."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
import subprocess

import pytest

pytestmark = pytest.mark.integration

_DASHBOARD_GLOB = "grafana/dashboards/*.json"
_REPORTS_DIR = Path("docs/reports/dashboard-ux-checks")
_CHANGE_NOTES_PATH = Path("docs/03-guides/dashboards/dashboard-v2-updates.md")


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


def _repository_utc_date() -> date:
    """Return the deterministic UTC calendar date of the checked-out revision."""
    result = subprocess.run(
        ["git", "log", "-1", "--format=%cI"],
        capture_output=True,
        text=True,
        check=True,
    )
    return datetime.fromisoformat(result.stdout.strip()).astimezone(UTC).date()


def _fresh_report_dates(today: date | None = None) -> set[str]:
    """Accept today or yesterday (UTC calendar date of the PR host)."""
    anchor = today or _repository_utc_date()
    return {anchor.isoformat(), (anchor - timedelta(days=1)).isoformat()}


def test_dashboard_json_changes_require_fresh_ux_report_and_change_note_link() -> None:
    changed_files = _git_changed_files()
    dashboard_changed = any(
        path.startswith("grafana/dashboards/") and path.endswith(".json")
        for path in changed_files
    )

    if not dashboard_changed:
        pytest.skip("No grafana/dashboards/*.json changes detected in git diff.")

    assert _REPORTS_DIR.is_dir(), "Missing docs/reports/dashboard-ux-checks directory"

    host_today = _repository_utc_date()
    fresh_dates = _fresh_report_dates(host_today)
    fresh_reports = [
        _REPORTS_DIR / f"{report_date}.md"
        for report_date in sorted(fresh_dates)
        if (_REPORTS_DIR / f"{report_date}.md").exists()
    ]
    assert fresh_reports, (
        "Dashboard JSON changed, but no fresh UX report found. "
        "Expected docs/reports/dashboard-ux-checks/<today|yesterday>.md "
        f"(today={host_today.isoformat()})."
    )

    change_notes = _CHANGE_NOTES_PATH.read_text(encoding="utf-8")
    assert "docs/reports/dashboard-ux-checks/" in change_notes, (
        "Dashboard change notes must include a link to the UX report artifact path."
    )


def test_ux_report_freshness_helper_accepts_today_and_yesterday() -> None:
    """Gate must not hardcode a frozen calendar date (DRM-01)."""
    anchor = date(2030, 1, 15)
    assert _fresh_report_dates(anchor) == {"2030-01-15", "2030-01-14"}
