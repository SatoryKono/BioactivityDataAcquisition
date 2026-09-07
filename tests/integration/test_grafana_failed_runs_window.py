"""Bind panel 205 to the PromQL cases executed by the existing promtool CI gate."""

from pathlib import Path

import pytest
import yaml

from tests.integration._grafana_test_support import (
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration


def test_failed_runs_uses_one_selected_window_evaluation() -> None:
    """The stat must not reduce a rolling 15-minute series into a six-hour claim."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel = next(p for p in get_dashboard_panels(dashboard) if p["id"] == 205)
    (target,) = panel["targets"]
    assert target["instant"] is True
    assert target["range"] is False
    assert "[$__range]" in target["expr"]
    assert "[15m]" not in target["expr"]
    assert " or " not in target["expr"]
    assert panel["fieldConfig"]["defaults"]["noValue"] == "UNKNOWN"
    assert "insufficient samples remain UNKNOWN" in panel["description"]
    assert panel["options"]["reduceOptions"]["calcs"] == ["lastNotNull"]


def test_failed_runs_promtool_cases_execute_the_shipped_expression() -> None:
    """Keep engine-level expected values tied to the shipped query, including resets."""
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-runtime.json"))
    panel = next(p for p in get_dashboard_panels(dashboard) if p["id"] == 205)
    expression = panel["targets"][0]["expr"]
    expression = expression.replace("$pipeline", "chembl_assay").replace(
        "$run_type", "backfill"
    )
    path = Path("grafana/prometheus-rules/tests/bioetl_observability.test.yml")
    cases = {
        case["name"].removeprefix("runtime-selected-window-"): case
        for case in yaml.safe_load(path.read_text(encoding="utf-8"))["tests"]
        if case["name"].startswith("runtime-selected-window-")
    }
    assert set(cases) == {
        "earlier-failures",
        "counter-reset",
        "measured-zero",
        "missing-counter",
        "single-sample",
        "stale-counter",
    }
    for case in cases.values():
        assert {test["expr"] for test in case["promql_expr_test"]} == {
            expression.replace("$__range", window) for window in ("15m", "6h")
        }
        assert all(test["eval_time"] == "6h" for test in case["promql_expr_test"])
