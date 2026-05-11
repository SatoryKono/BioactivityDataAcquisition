"""Integration tests for provider context mapping contract - source dashboard values."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    _collect_dashboard_links,
    load_dashboard,
)

pytestmark = pytest.mark.integration


def test_provider_context_mapping_preserves_source_values():
    """Provider health handoffs must preserve source dashboard provider/adapter values."""
    # bioetl-runtime → bioetl-provider-health-v2 should preserve provider context
    runtime_dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    runtime_links = _collect_dashboard_links(runtime_dashboard)

    for link in runtime_links:
        url = str(link.get("url", ""))
        title = str(link.get("title", ""))

        # Check links to provider-health
        if "/d/bioetl-provider-health-v2/" in url:
            # Runtime to provider-health should preserve pipeline context
            # This is a SHOULD check - just verify the pattern exists
            assert "var-pipeline_context" in url or "var-provider" in url, (
                f"Runtime link '{title}' to Provider Health should include provider context mapping"
            )

    # bioetl-dq-v2 → bioetl-provider-health-v2 should preserve provider context
    dq_dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    dq_links = _collect_dashboard_links(dq_dashboard)

    for link in dq_links:
        url = str(link.get("url", ""))
        title = str(link.get("title", ""))

        # Check links to provider-health
        if "/d/bioetl-provider-health-v2/" in url:
            # DQ to provider-health should preserve pipeline context
            assert "var-pipeline_context" in url or "var-provider" in url, (
                f"DQ link '{title}' to Provider Health should include provider context mapping"
            )
