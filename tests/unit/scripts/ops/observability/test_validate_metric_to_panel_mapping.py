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
"""Unit tests for metric-to-panel PromQL helpers."""

from __future__ import annotations

import pytest

from scripts.ops.observability import validate_metric_to_panel_mapping as vmap


pytestmark = pytest.mark.unit


def test_extract_panel_metrics_is_sorted_and_deduped() -> None:
    panel = {
        "targets": [
            {"expr": "bioetl_b_total + bioetl_a_total"},
            {"expr": "bioetl_a_total"},
        ]
    }
    metrics = vmap.extract_panel_metrics(panel)
    assert metrics == sorted(metrics)
    assert metrics == sorted(set(metrics))


def test_validate_metric_exists_empty_vector_is_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        vmap,
        "_fetch_json",
        lambda *args, **kwargs: {
            "status": "success",
            "data": {"resultType": "vector", "result": []},
        },
    )
    ok, message = vmap.validate_metric_exists(
        "bioetl_missing", set(), "http://prometheus:9090", 1.0
    )
    assert ok is False
    assert "not found" in message


def test_validate_metric_exists_nonempty_vector_is_queryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        vmap,
        "_fetch_json",
        lambda *args, **kwargs: {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [{"metric": {"__name__": "bioetl_ok"}, "value": [1, "1"]}],
            },
        },
    )
    ok, message = vmap.validate_metric_exists(
        "bioetl_ok", set(), "http://prometheus:9090", 1.0
    )
    assert ok is True
    assert "queryable" in message


def test_validate_panel_query_empty_results_uses_result_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        vmap,
        "_fetch_json",
        lambda *args, **kwargs: {
            "status": "success",
            "data": {"resultType": "vector", "result": []},
        },
    )
    panel = {"targets": [{"expr": "up"}]}
    ok, message = vmap.validate_panel_query(panel, "http://prometheus:9090", 1.0)
    assert ok is False
    assert "resultType: vector" in message
