# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
from __future__ import annotations

from typing import Any

import pytest

from scripts.ops import __main__ as ops_router
from scripts.ops.observability.grafana import check_dashboard_panel_fill as fill
from tests.helpers import assert_router_python_command
from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.repo_backed


def _config(**overrides: Any) -> fill.FillConfig:
    payload = {
        "grafana_base_url": "http://127.0.0.1:3000",
        "grafana_username": "admin",
        "grafana_password": "secret",
        "pipeline": "chembl_target",
        "run_type": "incremental",
        "run_id": "-",
        "workflow": "All",
        "range_hours": 24,
        "request_timeout_seconds": 15.0,
        "output_path": None,
    }
    payload.update(overrides)
    return fill.FillConfig(**payload)


def test_router_exposes_panel_fill_command() -> None:
    assert_router_python_command(
        ops_router,
        "check-dashboard-panel-fill",
        expected_target="observability/grafana/check_dashboard_panel_fill.py",
    )


@pytest.mark.parametrize(
    ("status", "body", "transport", "needle"),
    [
        (504, "Gateway Timeout", None, "HTTP 504"),
        (502, "Bad Gateway", None, "HTTP 502"),
        (503, "Service Unavailable", None, "HTTP 503"),
        (505, "HTTP Version Not Supported", None, "HTTP 505"),
        (
            200,
            {"results": {"A": {"error": "Gateway Timeout"}}},
            None,
            "gateway timeout",
        ),
        (200, {"results": {"A": {"error": "query error"}}}, None, "query error"),
        (
            200,
            {
                "results": {
                    "A": {
                        "frames": [
                            {
                                "meta": {
                                    "notices": [
                                        {
                                            "severity": "error",
                                            "text": "failed to get data from url",
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                }
            },
            None,
            "failed to get data from url",
        ),
        (None, None, "timed out", "transport: timed out"),
    ],
)
def test_classify_fill_error_detects_gateway_and_query_failures(
    status: int | None,
    body: object,
    transport: str | None,
    needle: str,
) -> None:
    verdict = fill.classify_fill_error(
        http_status=status, body=body, transport_error=transport
    )
    assert verdict.kind == "fill_error"
    assert needle.lower() in verdict.reason.lower()


@pytest.mark.parametrize(
    "body",
    [
        {"results": {"A": {"status": 200, "frames": []}}},
        {
            "results": {
                "A": {"frames": [{"schema": {"name": "A"}, "data": {"values": []}}]}
            }
        },
        {"message": "No data"},
        None,
    ],
)
def test_classify_fill_error_treats_empty_or_no_data_as_ok(body: object) -> None:
    verdict = fill.classify_fill_error(http_status=200, body=body)
    assert verdict.kind == "ok"


def test_classify_fill_error_does_not_treat_timeout_in_payload_values_as_error() -> (
    None
):
    verdict = fill.classify_fill_error(
        http_status=200,
        body={
            "results": {
                "A": {
                    "status": 200,
                    "frames": [
                        {
                            "data": {
                                "values": [["timeout_seconds"], [15]],
                            }
                        }
                    ],
                }
            }
        },
    )
    assert verdict.kind == "ok"


def test_iter_queryable_panels_covers_every_shipped_data_panel() -> None:
    discovered = fill.iter_queryable_panels()
    assert discovered
    uids = {item["dashboard_uid"] for item in discovered}
    shipped = {load_dashboard(path).get("uid") for path in get_dashboard_files()}
    assert uids == shipped

    expected: set[tuple[str, int]] = set()
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        uid = str(dashboard.get("uid") or path.stem)
        for panel in get_dashboard_panels(dashboard):
            if fill._is_queryable_panel(panel):
                expected.add((uid, int(panel["id"])))
    actual = {
        (str(item["dashboard_uid"]), int(item["panel"]["id"])) for item in discovered
    }
    assert actual == expected
    assert len(actual) >= 50


def test_build_ds_query_payload_substitutes_scope_and_skips_hidden_targets() -> None:
    panel = {
        "id": 891,
        "type": "stat",
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "targets": [
            {
                "refId": "A",
                "expr": 'max(bioetl_x{pipeline=~"$pipeline",run_type=~"$run_type"})',
                "instant": True,
            },
            {
                "refId": "B",
                "hide": True,
                "expr": "vector(1)",
            },
        ],
    }
    payload = fill.build_ds_query_payload(panel, config=_config())
    assert len(payload["queries"]) == 1
    expr = payload["queries"][0]["expr"]
    assert "chembl_target" in expr
    assert "incremental" in expr
    assert "$pipeline" not in expr
    assert payload["queries"][0]["datasource"]["uid"] == "prometheus"
    assert payload["from"].isdigit()
    assert payload["to"].isdigit()


def test_build_ds_query_payload_maps_ops_http_string_datasource() -> None:
    panel = {
        "id": 9418,
        "type": "table",
        "datasource": "BioETL Ops HTTP",
        "targets": [
            {
                "refId": "A",
                "url": "/ops/control-plane/manifest-validation?pipeline=${pipeline}",
                "type": "json",
            }
        ],
    }
    payload = fill.build_ds_query_payload(panel, config=_config())
    query = payload["queries"][0]
    assert query["datasource"] == {
        "type": "yesoreyeram-infinity-datasource",
        "uid": "bioetl-ops-http",
    }
    assert "chembl_target" in query["url"]


def test_query_panel_fill_maps_gateway_timeout_from_grafana_api(
    monkeypatch: Any,
) -> None:
    panel = {
        "id": 9401,
        "type": "stat",
        "title": "Monitor Replay Readiness",
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "targets": [{"refId": "A", "expr": "up", "instant": True}],
    }

    def _fake_post(
        url: str,
        payload: dict[str, Any],
        *,
        auth_header: str,
        timeout_seconds: float,
    ) -> tuple[int, object]:
        assert url.endswith("/api/ds/query")
        assert payload["queries"]
        return 504, "Gateway Timeout"

    monkeypatch.setattr(fill, "_post_json", _fake_post)
    verdict = fill.query_panel_fill(panel, config=_config())
    assert verdict.kind == "fill_error"
    assert verdict.http_status == 504
    assert "504" in verdict.reason


def test_query_panel_fill_accepts_successful_empty_frames(monkeypatch: Any) -> None:
    panel = {
        "id": 9401,
        "type": "stat",
        "title": "Monitor Replay Readiness",
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "targets": [{"refId": "A", "expr": "up", "instant": True}],
    }
    monkeypatch.setattr(
        fill,
        "_post_json",
        lambda *args, **kwargs: (
            200,
            {"results": {"A": {"status": 200, "frames": []}}},
        ),
    )
    verdict = fill.query_panel_fill(panel, config=_config())
    assert verdict.kind == "ok"


def test_text_and_row_panels_are_not_queryable() -> None:
    assert (
        fill._is_queryable_panel({"id": 1000, "type": "text", "targets": []}) is False
    )
    assert fill._is_queryable_panel({"id": 902, "type": "row", "panels": []}) is False
    assert (
        fill._is_queryable_panel(
            {"id": 891, "type": "stat", "targets": [{"expr": "up"}]}
        )
        is True
    )
