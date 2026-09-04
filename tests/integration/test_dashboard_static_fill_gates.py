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
"""Static fill/design gates that are not already covered by existing tests.

DES-03  includeAll query vars must ship a PromQL-safe allValue
FILL-08 panel target refId values must be unique
DES-02  /d/ handoff URLs must preserve the dashboard time window
FILL-06 Infinity / Ops HTTP target URLs must stay on /ops/ allowlist
FILL-07 root data-typed panels must have at least one visible target
DES-07  navigation panel id=1000 must occupy a full-width short band
"""

from __future__ import annotations

from collections import Counter
from urllib.parse import urlparse

import pytest

from tests.integration._grafana_test_support import (
    _collect_dashboard_links,
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
)

pytestmark = pytest.mark.integration

_SAFE_ALL_VALUES = {".*", "$__all"}
_DATA_PANEL_TYPES = {
    "stat",
    "gauge",
    "timeseries",
    "table",
    "bargauge",
    "heatmap",
    "histogram",
    "state-timeline",
    "status-history",
    "piechart",
    "xychart",
}
_HTTP_DATASOURCE_TYPES = {
    "yesoreyeram-infinity-datasource",
    "grafana-infinity-datasource",
    "marcusolsson-json-datasource",
}
_OPS_PATH_PREFIXES = (
    "/ops/control-plane/",
    "/ops/observability/",
    "/ops/quarantine/",
)


def _datasource_type(obj: object) -> str:
    if isinstance(obj, dict):
        return str(obj.get("type") or "")
    return ""


def _datasource_uid(obj: object) -> str:
    if isinstance(obj, dict):
        return str(obj.get("uid") or "")
    if isinstance(obj, str):
        return obj
    return ""


def _is_ops_http_source(*, typ: str, uid: str) -> bool:
    if typ in _HTTP_DATASOURCE_TYPES:
        return True
    blob = f"{typ} {uid}".lower()
    return "ops-http" in blob or "bioetl-ops" in blob or "ops http" in blob


def _target_url(target: dict[str, object]) -> str | None:
    for key in ("url", "urlPath"):
        value = target.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    options = target.get("url_options")
    if isinstance(options, dict):
        value = options.get("url")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _ops_path_allowed(url: str) -> bool:
    path = urlparse(url).path or url.split("?", 1)[0]
    return any(path.startswith(prefix) for prefix in _OPS_PATH_PREFIXES)


def _visible_targets(panel: dict[str, object]) -> list[dict[str, object]]:
    targets = panel.get("targets")
    if not isinstance(targets, list):
        return []
    return [
        target
        for target in targets
        if isinstance(target, dict) and target.get("hide") is not True
    ]


def _preserves_time_window(url: str) -> bool:
    return "${__url_time_range}" in url or ("from=" in url and "to=" in url)


def test_include_all_query_variables_use_promql_safe_all_value() -> None:
    offenders: list[str] = []
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for variable in dashboard.get("templating", {}).get("list", []):
            if not isinstance(variable, dict) or variable.get("includeAll") is not True:
                continue
            name = variable.get("name")
            all_value = variable.get("allValue")
            if all_value not in _SAFE_ALL_VALUES:
                offenders.append(f"{path.name}:${name} allValue={all_value!r}")
    assert not offenders, (
        "includeAll variables must set allValue to '.*' or '$__all':\n"
        + "\n".join(offenders)
    )


def test_panel_target_ref_ids_are_unique() -> None:
    offenders: list[str] = []
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for panel in get_dashboard_panels(dashboard):
            ref_ids = [
                str(target.get("refId"))
                for target in panel.get("targets", [])
                if isinstance(target, dict) and target.get("refId")
            ]
            duplicates = sorted(
                ref_id for ref_id, count in Counter(ref_ids).items() if count > 1
            )
            if duplicates:
                offenders.append(
                    f"{path.name}:id={panel.get('id')} title={panel.get('title')!r} "
                    f"duplicates={duplicates}"
                )
    assert not offenders, "panel targets must use unique refId values:\n" + "\n".join(
        offenders
    )


def test_dashboard_handoff_urls_preserve_time_window() -> None:
    offenders: list[str] = []
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for link in _collect_dashboard_links(dashboard):
            if not isinstance(link, dict):
                continue
            url = str(link.get("url") or "")
            if not url.startswith("/d/"):
                continue
            if not _preserves_time_window(url):
                offenders.append(f"{path.name}:{link.get('title')!r} -> {url}")
    assert not offenders, (
        "/d/ handoffs must include ${__url_time_range} or from=/to=:\n"
        + "\n".join(offenders)
    )


def test_ops_http_targets_use_allowlisted_ops_paths() -> None:
    offenders: list[str] = []
    scanned = 0
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for panel in get_dashboard_panels(dashboard):
            panel_type = _datasource_type(panel.get("datasource"))
            panel_uid = _datasource_uid(panel.get("datasource"))
            for target in panel.get("targets", []):
                if not isinstance(target, dict):
                    continue
                typ = _datasource_type(target.get("datasource")) or panel_type
                uid = _datasource_uid(target.get("datasource")) or panel_uid
                if not _is_ops_http_source(typ=typ, uid=uid):
                    continue
                url = _target_url(target)
                if url is None:
                    offenders.append(f"{path.name}:id={panel.get('id')} missing url")
                    continue
                scanned += 1
                if not _ops_path_allowed(url):
                    offenders.append(f"{path.name}:id={panel.get('id')} url={url}")
        for variable in dashboard.get("templating", {}).get("list", []):
            if not isinstance(variable, dict):
                continue
            typ = _datasource_type(variable.get("datasource"))
            uid = _datasource_uid(variable.get("datasource"))
            query = variable.get("query")
            url = query if isinstance(query, str) else None
            if url is None and isinstance(query, dict):
                raw = query.get("url")
                url = raw if isinstance(raw, str) else None
            if not url or not _is_ops_http_source(typ=typ, uid=uid):
                continue
            scanned += 1
            if not _ops_path_allowed(url):
                offenders.append(f"{path.name}:var=${variable.get('name')} url={url}")
    assert scanned > 0, "expected at least one Ops HTTP / Infinity target"
    assert not offenders, (
        "Ops HTTP / Infinity URLs must stay on /ops/ allowlist:\n"
        + "\n".join(offenders)
    )


def test_root_data_panels_have_a_visible_target() -> None:
    offenders: list[str] = []
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        for panel in dashboard.get("panels", []):
            if not isinstance(panel, dict):
                continue
            if panel.get("type") not in _DATA_PANEL_TYPES:
                continue
            if not _visible_targets(panel):
                offenders.append(
                    f"{path.name}:id={panel.get('id')} type={panel.get('type')} "
                    f"title={panel.get('title')!r}"
                )
    assert not offenders, (
        "root data-typed panels must expose at least one visible target:\n"
        + "\n".join(offenders)
    )


def test_navigation_bus_uses_full_width_short_band() -> None:
    for path in get_dashboard_files():
        dashboard = load_dashboard(path)
        buses = [
            panel
            for panel in get_dashboard_panels(dashboard)
            if panel.get("id") == 1000
        ]
        assert len(buses) == 1, f"{path.name} must define exactly one id=1000"
        grid = buses[0].get("gridPos") or {}
        assert grid.get("w") == 24, (
            f"{path.name}:id=1000 must use w=24, got {grid.get('w')}"
        )
        assert grid.get("h") in {3, 4}, (
            f"{path.name}:id=1000 must use h=3 or h=4 for title + reflow-safe bus, "
            f"got {grid.get('h')}"
        )
        options = buses[0].get("options") or {}
        assert buses[0].get("title") == "", (
            f"{path.name}:id=1000 must suppress the 14px Grafana native title"
        )
        assert options.get("bioetlDisplayTitle") == "Navigate Dashboards"
        content = str(options.get("content", ""))
        assert 'data-bioetl-panel-title="Navigate Dashboards"' in content
        assert "font-size:19px" in content
        assert "font-size:16px" in content
        assert "flex-wrap:nowrap" in content
        assert "flex:1 1 0" in content
        assert "min-width:0" in content
        assert "overflow-wrap:anywhere" in content
        assert "flex-wrap:wrap" not in content
        assert "overflow:hidden" not in content


def test_static_fill_helpers_fail_closed() -> None:
    assert not _preserves_time_window("/d/bioetl-runtime/bioetl-runtime")
    assert _preserves_time_window(
        "/d/bioetl-runtime/bioetl-runtime?${__url_time_range}"
    )
    assert _preserves_time_window("/d/x?from=now-12h&to=now")
    assert _ops_path_allowed("/ops/observability/pipeline-run-reports?limit=1")
    assert not _ops_path_allowed("https://example.test/health")
    assert _visible_targets({"targets": [{"hide": True}, {"refId": "A"}]}) == [
        {"refId": "A"}
    ]
    assert _visible_targets({"targets": [{"hide": True}]}) == []
    assert _is_ops_http_source(typ="", uid="BioETL Ops HTTP")
    assert not _is_ops_http_source(typ="prometheus", uid="prometheus")
