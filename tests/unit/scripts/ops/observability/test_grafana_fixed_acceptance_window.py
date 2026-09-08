"""Ensure fixed acceptance windows reach actual requests, not just labels."""

from urllib.parse import parse_qs, urlsplit

import pytest

from scripts.ops.observability.grafana import audit_live_grafana_panels as live
from scripts.ops.observability.grafana import run_grafana_dashboard_audit_cycle as cycle

pytestmark = pytest.mark.unit
WINDOW = ["--range-from", "1788782400000", "--range-to", "1788783000000"]


def test_fractional_window_is_not_silently_truncated():
    config = live._parse_args(
        ["--range-from", "1788782400000", "--range-to", "1788782401500"]
    )
    assert (
        live._substitute_dashboard_tokens("x[$__range] / ${__range_s}", config)
        == "x[1500ms] / 1.5"
    )


def test_exact_prometheus_evaluation_and_macro_window(monkeypatch):
    config = live._parse_args(WINDOW)
    calls = []
    response = {"status": "success", "data": {"resultType": "vector", "result": []}}

    def fetch(url, **kwargs):
        calls.append(url)
        return response

    monkeypatch.setattr(live, "_fetch_json", fetch)
    spec = live.PanelAuditSpec(
        "bioetl-runtime", 1, "Test", "prometheus", "prometheus_query"
    )
    result = live._audit_prometheus_panel(
        spec, {"targets": [{"expr": "increase(x[$__range]) / ${__range_s}"}]}, config
    )
    query = parse_qs(urlsplit(calls[0]).query)
    assert query["time"] == ["1788783000.0"]
    assert query["query"] == ["increase(x[600s]) / 600"]
    assert result.response == response
    assert result.request_url == calls[0]
    assert live._time_window(config) == live._time_window(config)


def test_cycle_propagates_fixed_window_to_live_and_render(monkeypatch, tmp_path):
    config = cycle._parse_args([*WINDOW, "--screenshot-dir", str(tmp_path)])
    calls = []
    monkeypatch.setattr(cycle.live_audit, "main", lambda argv: calls.append(argv) or 0)
    cycle._run_live_audit(config, app_base_url="http://localhost:8000")
    argv = calls[0]
    assert argv[argv.index("--range-from") + 1] == WINDOW[1]
    assert argv[argv.index("--range-to") + 1] == WINDOW[3]
    monkeypatch.setattr(cycle.rerender, "main", lambda argv: calls.append(argv) or 0)
    cycle._run_rerender(config, screenshot_uids=())
    argv = calls[-1]
    assert argv[argv.index("--range-from") + 1] == WINDOW[1]
    assert argv[argv.index("--range-to") + 1] == WINDOW[3]


@pytest.mark.parametrize(
    "args",
    [
        ["--range-from", "1000"],
        ["--range-from", "now-1h", "--range-to", "now"],
        ["--range-from", "20", "--range-to", "10"],
    ],
)
def test_invalid_fixed_windows_rejected(args):
    for parser in (live._parse_args, cycle._parse_args):
        with pytest.raises(SystemExit):
            parser(args)
