"""Integration tests for Grafana dashboard row visibility policy."""

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration


OPTIONAL_COLLAPSED_ROWS = {
    (
        "bioetl-runtime.json",
        "Tracing-only Log Hygiene (requires optional tracing profile)",
    )
}


def test_dashboard_rows_are_expanded_and_have_descriptive_titles():
    """Dashboard rows should be expanded unless they are optional drilldown rows."""
    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            if panel.get("type") == "row":
                title = panel.get("title", "")
                row_key = (dashboard_path.name, title)
                if row_key in OPTIONAL_COLLAPSED_ROWS:
                    assert panel.get("collapsed") is True, (
                        f"{dashboard_path.name}: optional row {title!r} must stay "
                        "collapsed by default"
                    )
                    assert panel.get("panels"), (
                        f"{dashboard_path.name}: collapsed row {title!r} must keep "
                        "its child panels nested under row.panels"
                    )
                else:
                    assert panel.get("collapsed") is False, (
                        f"{dashboard_path.name}: row {title!r} must be expanded "
                        "by default"
                    )
                    assert not panel.get("panels"), (
                        f"{dashboard_path.name}: expanded row {title!r} must not "
                        "keep panels nested under row.panels"
                    )
                assert title, f"{dashboard_path.name}: row must have title"
