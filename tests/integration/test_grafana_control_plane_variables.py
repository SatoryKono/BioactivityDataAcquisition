"""Integration contracts for Grafana control-plane variable sources."""

from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest

from tests.integration._grafana_test_support import load_dashboard

pytestmark = pytest.mark.integration


def test_control_plane_dashboard_uses_control_plane_native_variable_sources() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-control-plane-v1.json"))
    variable_map = {
        var.get("name"): var
        for var in dashboard.get("templating", {}).get("list", [])
        if var.get("name")
    }

    scopes = {
        "pipeline": {"workflow": ["${workflow}"]},
        "run_type": {"workflow": ["${workflow}"], "pipeline": ["${pipeline}"]},
    }
    for dimension, scope in scopes.items():
        variable = variable_map[dimension]
        assert variable["datasource"] == {
            "type": "yesoreyeram-infinity-datasource",
            "uid": "bioetl-ops-http",
        }
        query = variable["query"]
        assert query["queryType"] == "infinity"
        url = urlsplit(query["infinityQuery"]["url"])
        assert url.path == "/ops/control-plane/filter-options"
        assert parse_qs(url.query) == {
            "dimension": [dimension],
            "response_shape": ["options"],
            "allow_stale": ["1"],
            **scope,
        }
