"""CI guard: active dashboard docs must stay aligned with shipped JSON contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


def test_active_docs_capture_control_plane_navigation_exception() -> None:
    readme = Path("docs/03-guides/dashboards/README.md").read_text(encoding="utf-8")
    usage = Path("docs/03-guides/dashboards/dashboard-v2-usage.md").read_text(
        encoding="utf-8"
    )

    for token in ("bioetl-control-plane-v1", "Explore Logs", "Explore Traces"):
        assert token in readme
        assert token in usage
    assert "намеренным исключением" in readme
    assert "intentional exception" in usage


def test_active_docs_sync_workflow_selector_and_cta_titles() -> None:
    variable_reference = Path(
        "docs/03-guides/dashboards/variable-reference.md"
    ).read_text(encoding="utf-8")
    panel_inventory = Path(
        "docs/03-guides/dashboards/panel-title-inventory.md"
    ).read_text(encoding="utf-8")
    changelog = Path("docs/03-guides/dashboards/dashboard-v2-updates.md").read_text(
        encoding="utf-8"
    )

    assert "Single-select with Include All" in variable_reference
    assert "single-select with Include All across primary dashboards" in (
        variable_reference
    )
    assert "| bioetl-workflow-overview.json | 9 | First Action |" in panel_inventory
    assert "| bioetl-workflow-overview.json | 1 | Failed Workflow Runs / Range |" in (
        panel_inventory
    )

    for token in ("Next Diagnostic Surface", "Workflow Scope"):
        assert token not in panel_inventory
    assert "Переменные overview: `$pipeline`, `$run_type`." not in changelog


def test_active_dashboard_changelog_stays_current_to_shipped_surface() -> None:
    changelog = Path("docs/03-guides/dashboards/dashboard-v2-updates.md").read_text(
        encoding="utf-8"
    )

    required_tokens = (
        "Shipped Surface 2026-05-19",
        "docs/reports/dashboard-ux-checks/2026-05-19.md",
        "shared context shell",
        "$workflow",
        "$pipeline",
        "$run_type",
        "$run_id",
        "bioetl-control-plane-v1",
        "bioetl-workflow-overview",
        "Runtime Telemetry Gap",
        "First Action",
    )
    for token in required_tokens:
        assert token in changelog
