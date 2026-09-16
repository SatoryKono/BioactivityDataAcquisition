"""Bind the stale entity stat to engine-level count/absence regression vectors."""

from pathlib import Path

import pytest
import yaml

from tests.integration._grafana_test_support import get_dashboard_panels, load_dashboard

pytestmark = pytest.mark.integration


def test_stale_entity_promtool_cases_execute_the_shipped_expression() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel = next(p for p in get_dashboard_panels(dashboard) if p["id"] == 7)
    target = panel["targets"][0]
    assert target["instant"] is True and target["range"] is False
    assert panel["fieldConfig"]["defaults"]["decimals"] == 0
    assert panel["fieldConfig"]["defaults"]["unit"] == "suffix: entities"
    expression = target["expr"].replace("$pipeline", "chembl_assay")
    suite = yaml.safe_load(
        Path("grafana/prometheus-rules/tests/bioetl_observability.test.yml").read_text(
            encoding="utf-8"
        )
    )
    cases = [
        case
        for case in suite["tests"]
        if case["name"].startswith("runtime-stale-entity-count-")
    ]
    assert len(cases) == 5
    for case in cases:
        assert case["promql_expr_test"][0]["expr"] == expression
