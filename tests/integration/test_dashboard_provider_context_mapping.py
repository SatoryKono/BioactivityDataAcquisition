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


@pytest.mark.parametrize(
    "source", ["bioetl-overview-v2", "bioetl-run-explorer-v1", "bioetl-incident-v1"]
)
def test_provider_context_mapping_preserves_source_values(source: str) -> None:
    """Current Provider Evidence handoffs retain exact identity and own no legacy vars."""
    dashboard = load_dashboard(Path("grafana/dashboards") / (source + ".json"))
    links = [
        link
        for link in _collect_dashboard_links(dashboard)
        if link.get("title") in {"Open Provider Evidence", "Provider Evidence"}
    ]
    if source != "bioetl-incident-v1":
        assert links
    for link in links:
        url = link["url"]
        assert url.startswith("/d/bioetl-overview-v2/")
        assert "var-provider=" not in url and "var-pipeline_context=" not in url
        assert "var-adapter=" not in url
        assert "${__url_time_range}" in url
        assert "run_id" in url and "pipeline" in url
    assert not Path("grafana/dashboards/bioetl-provider-health-v2.json").exists()
