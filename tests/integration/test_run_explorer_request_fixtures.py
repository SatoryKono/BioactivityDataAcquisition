# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict.
"""Committed Run Explorer request fixtures stay generated (V5 R-C)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.integration._grafana_test_support import get_dashboard_panels, load_dashboard
from tests.integration._run_explorer_request_fixtures import (
    CONTRACT,
    DEFAULT_OUT,
    build_matrix,
    materialize_ops_url,
)

pytestmark = pytest.mark.integration


def test_committed_run_explorer_fixtures_match_generator() -> None:
    matrix = build_matrix()
    index = json.loads((DEFAULT_OUT / "INDEX.json").read_text(encoding="utf-8"))
    expected_index = {key: value for key, value in matrix.items() if key != "payloads"}
    assert index == expected_index
    payloads: dict[str, object] = matrix["payloads"]
    assert set(payloads) == set(index["scenarios"])
    for name, meta in index["scenarios"].items():
        committed = json.loads(
            (DEFAULT_OUT / f"{name}.json").read_text(encoding="utf-8")
        )
        assert committed == payloads[name]
        assert committed["contract"] == CONTRACT
        assert committed["panel_id"] == meta["panel_id"]
        assert committed["url"].startswith("/ops/")
        assert "$" not in committed["url"]
        assert not committed["url"].startswith(("http://", "https://"))


def test_selected_and_sentinel_urls_follow_live_catalog_templates() -> None:
    dashboard = load_dashboard(Path("grafana/dashboards/bioetl-run-explorer-v1.json"))
    live = {
        panel.get("id"): panel
        for panel in get_dashboard_panels(dashboard)
        if isinstance(panel.get("id"), int)
    }
    matrix = build_matrix()
    payloads: dict[str, dict[str, object]] = matrix["payloads"]
    for name in (
        "selected_recent_runs",
        "selected_identity",
        "selected_processed_records",
        "empty_selection",
    ):
        snapshot = payloads[name]
        panel = live[int(snapshot["panel_id"])]
        template = str(panel["targets"][0]["url"])
        assert template == snapshot["url_template"]
        assert materialize_ops_url(template, snapshot["selectors"]) == snapshot["url"]
