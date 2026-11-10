"""Keep complete table labels readable after specialized panel builders run."""

from __future__ import annotations

_WIDTH = "custom.width"


def apply_table_wrapping(panels: list[dict]) -> None:
    """Wrap headers and values without changing queries, columns, or verdicts."""
    for panel in panels:
        apply_table_wrapping(panel.get("panels", []))
        if panel.get("type") != "table":
            continue
        panel.setdefault("options", {}).pop("wrapHeaderText", None)
        config = panel.setdefault("fieldConfig", {})
        custom = config.setdefault("defaults", {}).setdefault("custom", {})
        custom["wrapText"] = True
        custom["wrapHeaderText"] = True
        custom.setdefault("cellOptions", {"type": "auto"})["wrapText"] = True
        if panel.get("id") == 9002:
            panel["gridPos"]["h"] = 10
        _wrap_overrides(config)
        if panel.get("id") == 3010:
            _reserve_identifier_width(config)
        if panel.get("id") in (9603, 2101):
            _map_provider_reason(config)


def _wrap_overrides(config: dict) -> None:
    for override in config.get("overrides", []):
        for prop in override.get("properties", []):
            if (
                override["matcher"] == {"id": "byName", "options": "Rank"}
                and prop["id"] == _WIDTH
            ):
                prop["value"] = max(80, prop["value"])
            if prop["id"] == "custom.wrapText":
                prop["value"] = True
            elif prop["id"] == "custom.cellOptions":
                prop["value"]["wrapText"] = True


def _reserve_identifier_width(config: dict) -> None:
    # Identifiers with underscores have no native word-break opportunities.
    # Reserve enough width rather than adding invisible characters to data.
    for name, width in (("Pipeline", 210), ("Workflow", 80)):
        override = next(
            o
            for o in config["overrides"]
            if o["matcher"] == {"id": "byName", "options": name}
        )
        override["properties"] = [
            p for p in override["properties"] if p["id"] != _WIDTH
        ]
        override["properties"].append({"id": _WIDTH, "value": width})


def _map_provider_reason(config: dict) -> None:
    # Translate a machine reason only at the display layer; raw evidence
    # and the saved WARN remain available through Inspect value.
    for override in config.get("overrides", []):
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
