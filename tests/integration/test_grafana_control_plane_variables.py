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

    pipeline_var = variable_map.get("pipeline")
    run_type_var = variable_map.get("run_type")
    assert pipeline_var is not None
    assert run_type_var is not None

    for name, variable in (("pipeline", pipeline_var), ("run_type", run_type_var)):
        assert variable["datasource"] == {
            "type": "yesoreyeram-infinity-datasource",
            "uid": "bioetl-ops-http",
        }
        query = variable["query"]["infinityQuery"]
        assert query["parser"] == "backend"
        assert query["url_options"]["method"] == "GET"
        url = urlsplit(query["url"])
        assert url.path == "/ops/control-plane/filter-options"
        parameters = parse_qs(url.query)
        assert parameters["dimension"] == [name]
        assert parameters["response_shape"] == ["options"]
        assert parameters["workflow"] == ["${workflow}"]
        assert "expr" not in query
        if name == "run_type":
            assert parameters["pipeline"] == ["${pipeline}"]
    assert run_type_var["allValue"] == ".*"
    assert run_type_var["multi"] is False
