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


def test_provider_context_mapping_preserves_source_values():
    """Provider evidence is a saved-run handoff after workspace retirement."""
    from tests.integration._grafana_test_support import get_dashboard_files

    retired = {"bioetl-runtime", "bioetl-provider-health-v2"}
    overview = load_dashboard(Path("grafana/dashboards/bioetl-overview-v2.json"))
    links = _collect_dashboard_links(overview)
    provider = [link for link in links if link.get("title") == "Open Provider Evidence"]
    assert provider
    for link in provider:
        assert "/d/bioetl-overview-v2/2-overview?" in link["url"]
        assert "viewPanel=9480" in link["url"]
        assert "run_id" in link["url"]
        assert "${__url_time_range}" in link["url"]
        assert not any(
            "var-" + name + "=" in link["url"]
            for name in ("provider", "adapter", "pipeline_context", "stage")
        )
    for path in get_dashboard_files():
        for link in _collect_dashboard_links(load_dashboard(path)):
            assert not any("/d/" + uid + "/" in str(link.get("url")) for uid in retired)
