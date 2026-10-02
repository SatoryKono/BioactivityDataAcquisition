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
"""Integration tests for provider context mapping contract - source dashboard values."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    _collect_dashboard_links,
    load_dashboard,
)

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("source", ["bioetl-incident-v1", "bioetl-run-explorer-v1"])
def test_provider_context_mapping_preserves_source_values(source: str) -> None:
    """Provider evidence handoffs retain exact run identity on Run Overview."""
    dashboard = load_dashboard(Path(f"grafana/dashboards/{source}.json"))
    links = [
        link
        for link in _collect_dashboard_links(dashboard)
        if "provider" in str(link.get("title", "")).lower()
        and str(link.get("url", "")).startswith("/d/")
    ]
    assert links, f"{source} must expose provider evidence navigation"
    for link in links:
        url = link["url"]
        assert url.startswith("/d/bioetl-overview-v2/")
        assert "${__url_time_range}" in url
        if source == "bioetl-run-explorer-v1":
            assert "var-pipeline=${__data.fields.Pipeline:percentencode}" in url
            assert "var-run_id=${__data.fields.run_id:percentencode}" in url
        else:
            assert "${pipeline:queryparam}" in url
            assert "${run_id:queryparam}" in url
        for retired in ("var-provider=", "var-pipeline_context=", "var-adapter="):
            assert retired not in url
