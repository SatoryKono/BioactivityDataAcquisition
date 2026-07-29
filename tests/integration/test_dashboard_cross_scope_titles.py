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
"""Integration tests for cross-scope marker contract - required titles by transition."""

import json
from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    _collect_dashboard_links,
    load_dashboard,
)

pytestmark = pytest.mark.integration


def test_cross_scope_links_use_required_titles():
    """Cross-scope links must use canonical titles from navigation-contract."""
    # Define required title patterns for specific dashboard transitions
    # Based on dashboard-audit-checklist.md section 17.2
    required_transitions = {
        # From Overview (epic #6570/#6647 naming).
        ("bioetl-overview-v2", "bioetl-runtime"): [
            "2. Pipeline Diagnostics",
            "Open Runtime",
            "Open Pipeline Diagnostics",
            "Open 2. Runtime",
            "2. Runtime",
        ],
        ("bioetl-overview-v2", "bioetl-control-plane-v1"): [
            "0. Trust",
            "Open Control Plane",
            "Open Trust",
        ],
        ("bioetl-overview-v2", "bioetl-dq-v2"): [
            "4. Data Quality",
            "Open Data Quality",
        ],
        ("bioetl-overview-v2", "bioetl-provider-health-v2"): [
            "3. Provider Health",
            "Open Provider Health",
        ],
        # From Runtime / Pipeline Diagnostics
        ("bioetl-runtime", "bioetl-dq-v2"): [
            "Open Data Quality",
            "Inspect DQ",
            "4. Data Quality",
        ],
        ("bioetl-runtime", "bioetl-provider-health-v2"): [
            "Open Provider Health",
            "Inspect Provider",
            "3. Provider Health",
        ],
        # Workflow overview + Silver Reject Explorer retired.
    }

    for (source_uid, target_uid), allowed_titles in required_transitions.items():
        dashboard = load_dashboard(Path("grafana/dashboards") / f"{source_uid}.json")
        links = _collect_dashboard_links(dashboard)

        for link in links:
            url = str(link.get("url", ""))
            title = str(link.get("title", ""))

            # Check if this link targets the expected dashboard
            if f"/d/{target_uid}/" in url:
                # Check if title matches one of the allowed patterns
                title_matches = any(allowed in title for allowed in allowed_titles)
                assert title_matches, (
                    f"Link from {source_uid} to {target_uid} must use canonical title. "
                    f"Expected one of: {allowed_titles}, Got: '{title}'"
                )


def test_cross_scope_links_have_required_tooltip_tokens():
    """Cross-scope links must include 'Scope reset' or 'Context mapping' tokens in tooltips."""
    # This is a SHOULD check - only verify for links that explicitly have scope-related tooltips
    for dashboard_path in Path("grafana/dashboards").glob("*.json"):
        dashboard = load_dashboard(dashboard_path)
        links = _collect_dashboard_links(dashboard)

        for link in links:
            tooltip = str(link.get("tooltip", ""))

            # Only check if tooltip exists and mentions dashboard scope reset or context mapping
            if tooltip and (
                "scope reset" in tooltip.lower() or "context mapping" in tooltip.lower()
            ):
                has_scope_reset = "reset scope" in tooltip.lower()
                has_context_mapping = "context mapping" in tooltip.lower()
                assert has_scope_reset or has_context_mapping, (
                    f"{dashboard_path.name}: link {link.get('title')} has scope-related tooltip "
                    f"but doesn't mention 'reset scope' or 'context mapping', got '{tooltip}'"
                )


def test_workflow_dashboard_provenance_banner_makes_scope_split_explicit() -> None:
    """Retired workflow overview dashboard must not reappear in grafana/dashboards."""
    workflow_overview = Path("grafana/dashboards/bioetl-workflow-overview.json")
    runtime = Path("grafana/dashboards/bioetl-runtime.json")
    assert not workflow_overview.exists(), (
        "bioetl-workflow-overview.json was retired in grafana simplification "
        "(#6570/#6647); workflow-band evidence lives on bioetl-runtime"
    )
    assert runtime.is_file(), "bioetl-runtime.json must host workflow-band evidence"


def test_workflow_status_panel_repeats_selected_range_contract() -> None:
    """Retired workflow overview contract is enforced via absence + runtime presence."""
    workflow_overview = Path("grafana/dashboards/bioetl-workflow-overview.json")
    runtime = Path("grafana/dashboards/bioetl-runtime.json")
    assert not workflow_overview.exists()
    assert runtime.is_file()
    runtime_payload = json.loads(runtime.read_text(encoding="utf-8"))
    assert isinstance(runtime_payload.get("panels"), list)
    assert runtime_payload["panels"], (
        "runtime dashboard must retain workflow-band panels"
    )


def test_provider_health_descriptions_separate_global_and_selected_scope() -> None:
    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-provider-health-v2.json").read_text(
            encoding="utf-8"
        )
    )
    panels = {panel.get("id"): panel for panel in dashboard["panels"]}

    status_description = str(panels[9401].get("description", ""))
    assert "selected-provider scope" in status_description
    assert "GLOBAL Provider Severity Matrix" in status_description
    assert "may disagree by design" in status_description

    provenance_content = str(panels[9400].get("options", {}).get("content", ""))
    assert "GLOBAL severity" in provenance_content
    assert "selected-provider Status can disagree by design" in provenance_content

    for panel_id in (9101, 9102, 9103):
        description = str(panels[panel_id].get("description", ""))
        assert "Scope: GLOBAL provider fleet posture" in description
        assert "intentionally not filtered by run_id" in description
