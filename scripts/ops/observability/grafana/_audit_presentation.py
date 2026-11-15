"""Presentation-only safeguards shared by canonical dashboard generators."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml
from typing import Any

_WRAP_TEXT = "custom.wrapText"
_CELL_OPTIONS = "custom.cellOptions"

_LABEL_TRANSLATIONS = {
    "НЕТ ЗАПУСКОВ": "NO RUNS",
    "нет данных": "NO DATA",
    "нет записей": "NO RECORDS",
    "не применимо": "N/A",
}
_TRANSLATABLE_KEYS = frozenset({"text", "title", "description", "noValue"})


def enable_adaptive_catalog(dashboard: dict[str, Any]) -> None:
    """Select the managed adaptive plugin after its runtime has been deployed.

    Deliberately explicit: a native selector-only plugin must never receive
    a responsive-table panel merely because a source generator was invoked.
    """
    if dashboard.get("uid") != "bioetl-run-explorer-v1":
        raise ValueError("Adaptive catalog is only applicable to Run Explorer")
    panel = next(p for p in dashboard["panels"] if p.get("id") == 3010)
    panel["type"] = "bioetl-selectorshell-panel"
    panel["options"].update(
        viewMode="runs",
        compactFields=["Provider", "Pipeline", "Run ID", "Overview"],
    )


def _translate_label_text(item: str) -> str:
    """Apply the English label map to one presentation string."""
    for source, target in _LABEL_TRANSLATIONS.items():
        item = item.replace(source, target)
    return item


def _translate_mapping(value: dict[str, Any]) -> None:
    """Translate string labels in one mapping node, then descend."""
    for key, item in value.items():
        if key in _TRANSLATABLE_KEYS and isinstance(item, str):
            value[key] = _translate_label_text(item)
            continue
        _translate_audit_labels(item)


def _translate_audit_labels(value: Any) -> None:
    """Replace legacy Russian presentation tokens with English labels."""
    if isinstance(value, dict):
        _translate_mapping(value)
        return
    if isinstance(value, list):
        for item in value:
            _translate_audit_labels(item)


def _set_wrap(properties: list[dict[str, Any]], *, enabled: bool) -> None:
    """Toggle wrapText / cellOptions.wrapText on one override property list."""
    seen: set[str] = set()
    for prop in properties:
        prop_id = prop.get("id")
        if isinstance(prop_id, str):
            seen.add(prop_id)
        if prop_id == _WRAP_TEXT:
            prop["value"] = enabled
        elif prop_id == _CELL_OPTIONS:
            prop["value"]["wrapText"] = enabled
    if _WRAP_TEXT not in seen:
        properties.append({"id": _WRAP_TEXT, "value": enabled})
    if _CELL_OPTIONS not in seen:
        properties.append(
            {"id": _CELL_OPTIONS, "value": {"type": "auto", "wrapText": enabled}}
        )


def _stamp_run_explorer_wrap(panel: dict[str, Any]) -> None:
    """Keep ten native rows stable; full identity stays available in Inspect."""
    panel["options"].setdefault("footer", {})["enablePagination"] = False
    custom = panel["fieldConfig"]["defaults"]["custom"]
    custom.update(
        wrapText=False,
        wrapHeaderText=True,
        cellOptions={"type": "auto", "wrapText": False},
    )
    overrides = panel["fieldConfig"].get("overrides", [])
    for override in overrides:
        properties = override.get("properties", [])
        # TableRT can apply one field's wrap option to every cell in a row.
        _set_wrap(properties, enabled=False)
    run_id = next(
        item for item in overrides if item.get("matcher", {}).get("options") == "Run ID"
    )
    _set_wrap(run_id["properties"], enabled=False)


def _stamp_overview_widths(panel: dict[str, Any]) -> None:
    """Match Overview verdict column widths before displayName remapping."""
    widths = {"Processing": None, "Overall verdict": 75, "Trust": 95}
    for override in panel["fieldConfig"].get("overrides", []):
        name = override.get("matcher", {}).get("options")
        if name not in widths:
            continue
        width = widths[name]
        props = override["properties"]
        props[:] = [p for p in props if p.get("id") != "custom.width"]
        if width is not None:
            props.append({"id": "custom.width", "value": width})


def _ensure_cached_bronze_reason_mapping(prop: dict[str, Any]) -> None:
    """Insert or merge the cached-Bronze reason value mapping."""
    mapping = {
        "type": "value",
        "options": {
            "cached_bronze_no_remote_probe": {
                "text": "Cached Bronze used; provider API was not called."
            }
        },
    }
    value_map = next(
        (item for item in prop["value"] if item.get("type") == "value"),
        None,
    )
    if value_map is not None:
        value_map["options"].update(mapping["options"])
        return
    prop["value"].insert(0, mapping)


def _stamp_overview_reason_mapping(panel: dict[str, Any]) -> None:
    """Expose the cached-Bronze reason as readable English copy."""
    for override in panel.get("fieldConfig", {}).get("overrides", []):
        if override.get("matcher", {}).get("options") != "Reason":
            continue
        for prop in override.get("properties", []):
            if prop.get("id") == "mappings":
                _ensure_cached_bronze_reason_mapping(prop)


def _stamp_panel_presentation(dashboard: dict[str, Any], panel: dict[str, Any]) -> None:
    """Apply dashboard-specific presentation rules to one panel."""
    uid = dashboard.get("uid")
    panel_id = panel.get("id")
    if uid == "bioetl-run-explorer-v1" and panel_id == 3010:
        _stamp_run_explorer_wrap(panel)
        return
    if uid == "bioetl-dq-v2" and panel_id == 9406:
        for override in panel.get("fieldConfig", {}).get("overrides", []):
            if override.get("matcher", {}).get("options") == "Reason":
                override["properties"][:] = [
                    prop
                    for prop in override["properties"]
                    if prop.get("id") != "custom.width"
                ]
        return
    if uid != "bioetl-overview-v2":
        return
    if panel_id == 9604:
        panel.setdefault("options", {})["text"] = {"valueSize": 24}
        return
    if panel_id == 9603:
        _stamp_overview_widths(panel)
        return
    if panel_id == 9002:
        _stamp_overview_reason_mapping(panel)


def _shift_panel(panel: dict[str, Any], delta: int) -> None:
    panel["gridPos"]["y"] += delta
    for child in panel.get("panels", []):
        _shift_panel(child, delta)


def _fit_coverage_stats(dashboard: dict[str, Any]) -> None:
    """Allocate a readable line per series without changing status semantics."""
    for row in dashboard.get("panels", []):
        if row.get("id") != 8809:
            continue
        children = row.get("panels", [])
        old_bottom = max(
            (p["gridPos"]["y"] + p["gridPos"]["h"] for p in children),
            default=row["gridPos"]["y"] + 1,
        )
        for panel in children:
            if panel.get("id") in {9102, 9491}:
                panel["gridPos"]["h"] = max(8, panel["gridPos"]["h"])
                panel["options"]["orientation"] = "vertical"
        new_bottom = max(
            (p["gridPos"]["y"] + p["gridPos"]["h"] for p in children),
            default=old_bottom,
        )
        if new_bottom > old_bottom:
            for panel in dashboard["panels"]:
                if panel is not row and panel["gridPos"]["y"] >= old_bottom:
                    _shift_panel(panel, new_bottom - old_bottom)


def stamp_audit_presentation(dashboard: dict[str, Any]) -> None:
    """Keep cached-provider explanations and long verdicts readable."""
    _translate_audit_labels(dashboard)
    if dashboard.get("uid") == "bioetl-incident-v1":
        _fit_coverage_stats(dashboard)
    for panel in dashboard.get("panels", []):
        stamp_audit_presentation(panel)
        _stamp_panel_presentation(dashboard, panel)


def _project_current_time(dashboard: dict) -> None:
    """Use an independent query clock for source-declared CURRENT telemetry."""
    root = Path(__file__).resolve().parents[4]
    contract = yaml.safe_load(
        (
            root / "docs/03-guides/dashboards/contracts/panel-content-contract.yaml"
        ).read_text(encoding="utf-8")
    )
    specs = contract["dashboards"].get(dashboard.get("uid"), {}).get("panels", {})

    def walk(panels: list[dict]):
        for panel in panels:
            yield panel
            yield from walk(panel.get("panels", []))

    panels = {panel["id"]: panel for panel in walk(dashboard.get("panels", []))}
    native_panels = deepcopy(panels)
    for panel_id, panel in panels.items():
        if "${workflow_evidence_freshness}" in panel.get("title", ""):
            panel["title"] = panel["title"].replace(
                " · ${workflow_evidence_freshness}", ""
            )
        spec = specs.get(str(panel_id), {})
        if spec.get("evidence_source") not in {"prometheus", "grafana_builtin"}:
            continue
        current = spec.get("scope") == "current" or (
            "CURRENT" in panel.get("description", "")[:45]
        )
        if not current or panel.get("type") not in {"stat", "table", "timeseries"}:
            continue
        queries = panel.get("targets", [])
        if len(queries) == 1 and "panelId" in queries[0]:
            # A Dashboard datasource consumer requests the donor's raw frames.
            donor = native_panels.get(queries[0]["panelId"])
            if queries[0].get("withTransforms") or donor is None:
                raise ValueError("Current consumer requires an untransformed donor")
            queries = donor.get("targets", [])
        if not queries or any("expr" not in query for query in queries):
            raise ValueError(f"Current panel {panel_id} requires Prometheus queries")
        view = {
            "pluginId": panel["type"],
            "queries": deepcopy(queries),
            "transformations": deepcopy(panel.get("transformations", [])),
            "options": deepcopy(panel.get("options", {})),
        }
        panel["type"] = "bioetl-selectorshell-panel"
        panel["options"] = {"viewMode": "current", "currentView": view}
        # The managed runner owns these queries and transformations. Leaving
        # them on the host panel would also execute a misleading historical
        # request and duplicate the query cost on every dashboard refresh.
        panel["targets"] = []
        panel["transformations"] = []
        panel["description"] += (
            " Managed CURRENT queries use an independent clock and refresh every 30s. "
            "The timestamp is query evaluation time, not publication or event time. "
            "The historical dashboard interval does not set the current query end; "
            "current trends retain the selected duration and end at now. "
            "Timeouts, failed queries and unverified response time remain unavailable."
        )
        if panel_id == 9701:
            panel["title"] = "Review Current Workflow Evidence · threshold 24h"
    for panel in panels.values():
        for query in panel.get("targets", []):
            donor = panels.get(query.get("panelId"), {})
            if donor.get("options", {}).get("viewMode") == "current":
                raise ValueError("Historical consumer cannot reuse a CURRENT donor")
    if "templating" in dashboard:
        dashboard["templating"]["list"] = [
            item
            for item in dashboard["templating"]["list"]
            if item.get("name") != "workflow_evidence_freshness"
        ]


def project_adaptive_dashboard(source: dict) -> dict:
    """Preserve queries and identity; adapt the catalog and prioritize the verdict."""
    result = deepcopy(source)
    _project_current_time(result)
    if result.get("uid") == "bioetl-run-explorer-v1":
        enable_adaptive_catalog(result)
    if result.get("uid") == "bioetl-dq-v2":
        panel = next((p for p in result["panels"] if p["id"] == 9406), None)
        if panel is not None:
            panel["type"] = "bioetl-selectorshell-panel"
            panel["options"].update(
                viewMode="record",
                compactFields=["Processing", "Overall verdict", "Trust"],
            )
    if result.get("uid") == "bioetl-overview-v2":
        # Keep the main answer first when Grafana stacks columns at 200%.
        # Give the status stack one additional column so docked-menu desktop
        # widths retain complete status words. Scope and queries are unchanged.
        panels = {panel["id"]: panel for panel in result["panels"]}
        for panel_id in (9604, 9603, 9300):
            panels[panel_id]["gridPos"]["x"] = 0
            panels[panel_id]["gridPos"]["w"] = 10
        for panel_id in (99, 9002):
            panels[panel_id]["gridPos"].update(x=10, w=14)
    return result
