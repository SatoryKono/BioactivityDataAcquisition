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
"""Fail-closed Run Explorer HTTP target catalog (V5 R-B)."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
import yaml

from tests.integration._grafana_test_support import get_dashboard_panels, load_dashboard

pytestmark = pytest.mark.integration

_CATALOG_PATH = Path(
    "docs/03-guides/dashboards/contracts/run-explorer-http-catalog.yaml"
)
_FORBIDDEN_NOVALUE_VARS = ("$pipeline", "$workflow", "$run_id", "$run_type")


def _load_catalog() -> dict[str, object]:
    payload = yaml.safe_load(_CATALOG_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _http_target(panel: dict[str, object]) -> dict[str, object] | None:
    targets = panel.get("targets")
    if not isinstance(targets, list) or not targets:
        return None
    target = targets[0]
    if not isinstance(target, dict):
        return None
    url = target.get("url")
    if isinstance(url, str) and url.startswith("/ops/"):
        return target
    return None


def test_run_explorer_http_catalog_matches_live_dashboard() -> None:
    catalog = _load_catalog()
    dashboard = load_dashboard(Path(str(catalog["dashboard_path"])))
    assert dashboard.get("uid") == catalog["dashboard_uid"]

    endpoints = catalog["endpoints"]
    assert isinstance(endpoints, dict)
    expected_panels = catalog["panels"]
    assert isinstance(expected_panels, list)

    live_panels = {
        panel.get("id"): panel
        for panel in get_dashboard_panels(dashboard)
        if isinstance(panel.get("id"), int)
    }
    live_http_ids = {
        panel_id
        for panel_id, panel in live_panels.items()
        if _http_target(panel) is not None
    }
    catalog_ids = {int(entry["id"]) for entry in expected_panels}
    assert live_http_ids == catalog_ids, (
        "Run Explorer HTTP panels drifted from the catalog: "
        f"extra={sorted(live_http_ids - catalog_ids)} "
        f"missing={sorted(catalog_ids - live_http_ids)}"
    )

    infinity = catalog["infinity"]
    assert isinstance(infinity, dict)
    for entry in expected_panels:
        assert isinstance(entry, dict)
        panel_id = int(entry["id"])
        panel = live_panels[panel_id]
        target = _http_target(panel)
        assert target is not None, f"panel {panel_id} lost its Ops HTTP target"
        assert panel.get("title") == entry["title"]
        assert target.get("url") == entry["url"]
        assert target.get("root_selector") == entry["root_selector"]
        for key, value in infinity.items():
            if key == "method":
                options = target.get("url_options")
                assert isinstance(options, dict)
                assert options.get("method") == value
                continue
            assert target.get(key) == value, f"panel {panel_id} infinity {key} drifted"

        endpoint_id = str(entry["endpoint"])
        endpoint = endpoints[endpoint_id]
        assert isinstance(endpoint, dict)
        parsed = urlparse(str(entry["url"]))
        assert parsed.path == endpoint["path"]
        query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
        for required in endpoint["required_query"]:
            assert required in query, f"panel {panel_id} URL missing required {required}"

        no_value = str(
            panel.get("fieldConfig", {}).get("defaults", {}).get("noValue", "")
        )
        description = str(panel.get("description") or "")
        copy = f"{no_value}\n{description}"
        for token in entry["no_value_tokens"]:
            assert token in no_value, f"panel {panel_id} noValue missing {token!r}"
        for token in entry["copy_tokens"]:
            assert token in copy, f"panel {panel_id} copy missing {token!r}"
        for forbidden in _FORBIDDEN_NOVALUE_VARS:
            assert forbidden not in no_value, (
                f"panel {panel_id} noValue still interpolates {forbidden}"
            )


def test_run_explorer_duplicate_http_targets_share_endpoint_id() -> None:
    catalog = _load_catalog()
    panels = catalog["panels"]
    assert isinstance(panels, list)
    by_url: dict[str, set[str]] = {}
    for entry in panels:
        assert isinstance(entry, dict)
        by_url.setdefault(str(entry["url"]), set()).add(str(entry["endpoint"]))
    drifted = {
        url: sorted(endpoint_ids)
        for url, endpoint_ids in by_url.items()
        if len(endpoint_ids) != 1
    }
    assert drifted == {}, (
        "Duplicate Run Explorer URLs must share one endpoint_id: " f"{drifted}"
    )
