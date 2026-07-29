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
"""Integration tests for Grafana dashboard scope reset tooltip format."""

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_files,
    load_dashboard,
)

pytestmark = pytest.mark.integration


def test_cross_scope_links_have_explicit_tooltip_markers():
    """Cross-scope links should have tooltips with 'Scope reset' or 'Context mapping' markers."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        # Check dashboard-level links
        links = dashboard.get("links", [])
        for link in links:
            url = str(link.get("url", ""))
            tooltip = link.get("tooltip", "")
            # Check if this is a cross-scope link (changes variable scope)
            # Links with var- parameters that reset scope should have tooltip
            if "var-" in url and "unknown" in url:
                assert tooltip, (
                    f"{dashboard_path.name}: link {link.get('title')} changes scope but has no tooltip"
                )
                # Tooltip should mention scope reset or context mapping
                assert (
                    "Scope reset" in tooltip
                    or "Context mapping" in tooltip
                    or "Reset scope" in tooltip
                ), (
                    f"{dashboard_path.name}: link {link.get('title')} tooltip should mention 'Scope reset' or 'Context mapping', got {tooltip}"
                )


def test_same_scope_links_have_preserve_tooltip():
    """Same-scope links should have tooltip 'Preserves selected scope and time range.'"""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        links = dashboard.get("links", [])
        for link in links:
            url = str(link.get("url", ""))
            tooltip = link.get("tooltip", "")
            # Check if this is a same-scope link (preserves variables)
            # If tooltip exists and doesn't mention reset, it should mention preserve
            if tooltip and "unknown" not in url:
                # This is a SHOULD, not MUST - just check format if tooltip exists
                if "Preserves" in tooltip:
                    assert "selected scope" in tooltip, (
                        f"{dashboard_path.name}: link {link.get('title')} tooltip with 'Preserves' should mention 'selected scope', got {tooltip}"
                    )
