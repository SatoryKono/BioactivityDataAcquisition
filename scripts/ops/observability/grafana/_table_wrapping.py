"""Keep complete table labels readable after specialized panel builders run."""

from __future__ import annotations

WIDTH = "custom.width"


def _wrap_overrides(overrides: list[dict]) -> None:
    for override in overrides:
        for prop in override.get("properties", []):
            if prop["id"] == WIDTH and override["matcher"] == {
                "id": "byName",
                "options": "Rank",
            }:
                prop["value"] = max(80, prop["value"])
            if prop["id"] == "custom.wrapText":
                prop["value"] = True
            elif prop["id"] == "custom.cellOptions":
                prop["value"]["wrapText"] = True


def _pipeline_widths(overrides: list[dict]) -> None:
    # Underscored identifiers have no native word-break opportunities.
    for name, width in (("Pipeline", 210), ("Workflow", 80)):
        override = next(
            o for o in overrides if o["matcher"] == {"id": "byName", "options": name}
        )
        override["properties"] = [p for p in override["properties"] if p["id"] != WIDTH]
        override["properties"].append({"id": WIDTH, "value": width})


def _provider_reason(overrides: list[dict]) -> None:
    # Translate only the display; preserve the raw reason and saved WARN.
    for override in overrides:
        if override["matcher"] != {"id": "byName", "options": "Reason"}:
            continue
        mappings = next(
            (p for p in override["properties"] if p["id"] == "mappings"), None
        )
        if mappings is None:
            mappings = {"id": "mappings", "value": []}
            override["properties"].append(mappings)
        value = {
            "type": "value",
            "options": {
                "Provider: run_preflight_provider_observation": {
                    "text": "Provider: saved preflight observation"
                }
            },
        }
        if value not in mappings["value"]:
            mappings["value"].append(value)


def _wrap_table(panel: dict) -> None:
    panel.setdefault("options", {}).pop("wrapHeaderText", None)
    config = panel.setdefault("fieldConfig", {})
    custom = config.setdefault("defaults", {}).setdefault("custom", {})
    custom["wrapText"] = True
    custom["wrapHeaderText"] = True
    custom.setdefault("cellOptions", {"type": "auto"})["wrapText"] = True
    overrides = config.get("overrides", [])
    _wrap_overrides(overrides)
    if panel.get("id") == 9002:
        panel["gridPos"]["h"] = 10
    if panel.get("id") == 3010:
        _pipeline_widths(overrides)
    if panel.get("id") in (9603, 2101):
        _provider_reason(overrides)


def apply_table_wrapping(panels: list[dict]) -> None:
    """Wrap headers and values without changing queries, columns, or verdicts."""
    for panel in panels:
        apply_table_wrapping(panel.get("panels", []))
        if panel.get("type") == "table":
            _wrap_table(panel)
