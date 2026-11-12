"""Presentation-only safeguards shared by canonical dashboard generators."""

from __future__ import annotations

from typing import Any

_LABEL_TRANSLATIONS = {
    "НЕТ ЗАПУСКОВ": "NO RUNS",
    "нет данных": "NO DATA",
    "нет записей": "NO RECORDS",
    "не применимо": "N/A",
}


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


def _translate_audit_labels(value: Any) -> None:
    """Replace legacy Russian presentation tokens with English labels."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"text", "title", "description", "noValue"} and isinstance(
                item, str
            ):
                for source, target in _LABEL_TRANSLATIONS.items():
                    item = item.replace(source, target)
                value[key] = item
            else:
                _translate_audit_labels(item)
    elif isinstance(value, list):
        for item in value:
            _translate_audit_labels(item)


def _stamp_run_explorer_wrap(panel: dict[str, Any]) -> None:
    """Keep Run Explorer cells readable without wrapping the Run ID column."""
    panel["options"].setdefault("footer", {})["enablePagination"] = True
    custom = panel["fieldConfig"]["defaults"]["custom"]
    custom.update(
        wrapText=True,
        wrapHeaderText=True,
        cellOptions={"type": "auto", "wrapText": True},
    )
    for override in panel["fieldConfig"].get("overrides", []):
        for prop in override.get("properties", []):
            if prop.get("id") == "custom.wrapText":
                prop["value"] = True
            if prop.get("id") == "custom.cellOptions":
                prop["value"]["wrapText"] = True
    run_id = next(
        item
        for item in panel["fieldConfig"]["overrides"]
        if item.get("matcher", {}).get("options") == "Run ID"
    )
    for prop in run_id["properties"]:
        if prop["id"] == "custom.wrapText":
            prop["value"] = False
        if prop["id"] == "custom.cellOptions":
            prop["value"]["wrapText"] = False


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


def _stamp_overview_reason_mapping(panel: dict[str, Any]) -> None:
    """Expose the cached-Bronze reason as readable English copy."""
    for override in panel.get("fieldConfig", {}).get("overrides", []):
        if override.get("matcher", {}).get("options") != "Reason":
            continue
        for prop in override.get("properties", []):
            if prop.get("id") != "mappings":
                continue
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
            else:
                prop["value"].insert(0, mapping)


def _stamp_panel_presentation(dashboard: dict[str, Any], panel: dict[str, Any]) -> None:
    """Apply dashboard-specific presentation rules to one panel."""
    uid = dashboard.get("uid")
    panel_id = panel.get("id")
    if uid == "bioetl-run-explorer-v1" and panel_id == 3010:
        _stamp_run_explorer_wrap(panel)
        return
    if uid != "bioetl-overview-v2":
        return
    if panel_id == 9604:
        panel.setdefault("options", {})["text"] = {"valueSize": 24}
    elif panel_id == 9603:
        _stamp_overview_widths(panel)
    elif panel_id == 9002:
        _stamp_overview_reason_mapping(panel)


def stamp_audit_presentation(dashboard: dict[str, Any]) -> None:
    """Keep cached-provider explanations and long verdicts readable."""
    _translate_audit_labels(dashboard)
    for panel in dashboard.get("panels", []):
        stamp_audit_presentation(panel)
        _stamp_panel_presentation(dashboard, panel)
