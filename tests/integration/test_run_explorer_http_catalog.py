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


def _http_targets(panel: dict[str, object]) -> list[dict[str, object]]:
    targets = panel.get("targets")
    if not isinstance(targets, list):
        return []
    http_targets: list[dict[str, object]] = []
    for target in targets:
        if not isinstance(target, dict) or target.get("hide") is True:
            continue
        url = target.get("url")
        if isinstance(url, str) and url.startswith("/ops/"):
            http_targets.append(target)
    return http_targets


def _catalog_target_specs(entry: dict[str, object]) -> list[dict[str, object]]:
    specs = [
        {
            "endpoint": entry["endpoint"],
            "url": entry["url"],
            "root_selector": entry["root_selector"],
        }
    ]
    extra = entry.get("extra_targets") or []
    assert isinstance(extra, list)
    for item in extra:
        assert isinstance(item, dict)
        specs.append(
            {
                "endpoint": item["endpoint"],
                "url": item["url"],
                "root_selector": item["root_selector"],
            }
        )
    return specs


def _assert_infinity_target(
    *,
    panel_id: int,
    target: dict[str, object],
    spec: dict[str, object],
    endpoints: dict[str, object],
    infinity: dict[str, object],
) -> None:
    assert target.get("url") == spec["url"], f"panel {panel_id} url drifted"
    assert target.get("root_selector") == spec["root_selector"], (
        f"panel {panel_id} root_selector drifted"
    )
    for key, value in infinity.items():
        if key == "method":
            options = target.get("url_options")
            assert isinstance(options, dict)
            assert options.get("method") == value
            continue
        assert target.get(key) == value, f"panel {panel_id} infinity {key} drifted"
    endpoint_id = str(spec["endpoint"])
    endpoint = endpoints[endpoint_id]
    assert isinstance(endpoint, dict)
    parsed = urlparse(str(spec["url"]))
    assert parsed.path == endpoint["path"]
    query = {key: values[0] for key, values in parse_qs(parsed.query).items()}
    for required in endpoint["required_query"]:
        assert required in query, f"panel {panel_id} URL missing required {required}"


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
        panel_id for panel_id, panel in live_panels.items() if _http_targets(panel)
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
        live_targets = _http_targets(panel)
        specs = _catalog_target_specs(entry)
        assert live_targets, f"panel {panel_id} lost its Ops HTTP target"
        assert panel.get("title") == entry["title"]
        assert len(live_targets) == len(specs), (
            f"panel {panel_id} HTTP target count drifted: "
            f"live={len(live_targets)} catalog={len(specs)}"
        )
        for target, spec in zip(live_targets, specs, strict=True):
            _assert_infinity_target(
                panel_id=panel_id,
                target=target,
                spec=spec,
                endpoints=endpoints,
                infinity=infinity,
            )

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
        for spec in _catalog_target_specs(entry):
            by_url.setdefault(str(spec["url"]), set()).add(str(spec["endpoint"]))
    drifted = {
        url: sorted(endpoint_ids)
        for url, endpoint_ids in by_url.items()
        if len(endpoint_ids) != 1
    }
    assert drifted == {}, (
        f"Duplicate Run Explorer URLs must share one endpoint_id: {drifted}"
    )
