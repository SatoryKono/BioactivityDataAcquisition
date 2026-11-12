"""Keep complete table *headers* readable after specialized panel builders run.

Value wrapping stays with the specialized builders (Reason-only wrap, inspect for
full identity, compact trust drilldown). This helper must not override those
Class-lane contracts or F-30 domains height (h in 7–8).
"""

from __future__ import annotations

WIDTH = "custom.width"
# Fields whose value wrap is owned by specialized builders / contracts.
_VALUE_WRAP_FIELDS = frozenset(
    {
        "Reason",
        "reason",
        "value_full",
        "Provider",
        "alertname",
        "Confidence",
    }
)


def _wrap_header_defaults(panel: dict) -> None:
    # Grafana Table reads wrapHeaderText from fieldConfig.defaults.custom.
    panel.setdefault("options", {}).pop("wrapHeaderText", None)
    config = panel.setdefault("fieldConfig", {})
    custom = config.setdefault("defaults", {}).setdefault("custom", {})
    custom["wrapHeaderText"] = True


def _strip_value_wrap_property(prop: dict, *, keep: bool) -> None:
    """Apply allowlist-aware value-wrap stripping to one override property."""
    if prop["id"] == "custom.wrapText":
        if keep:
            return
        prop["value"] = False
        return
    if prop["id"] != "custom.cellOptions":
        return
    value = prop.get("value")
    if not isinstance(value, dict):
        return
    # Contracts assert wrapText when cellOptions is present.
    value["wrapText"] = bool(keep and value.get("wrapText", keep))


def _strip_stale_value_wrap(
    overrides: list[dict], *, preserve_evidence: bool = False
) -> None:
    """Drop blanket value-wrap left by earlier helper revisions.

    Specialized builders set intentional wraps (e.g. Reason) before this runs.
    Compact-trust / Run ID contracts require those keys absent or false.
    """
    for override in overrides:
        name = override.get("matcher", {}).get("options")
        keep = name in _VALUE_WRAP_FIELDS or (
            preserve_evidence and name in {"Signal", "Object", "Details"}
        )
        for prop in override.get("properties", []):
            _strip_value_wrap_property(prop, keep=keep)


def _rank_width(overrides: list[dict]) -> None:
    for override in overrides:
        if override.get("matcher") != {"id": "byName", "options": "Rank"}:
            continue
        for prop in override.get("properties", []):
            if prop["id"] == WIDTH:
                prop["value"] = max(80, prop["value"])


def _pipeline_widths(overrides: list[dict]) -> None:
    # Underscored identifiers need a readable floor, but must stay flex columns:
    # custom.width on Workflow/Pipeline blows the first-window 200% CSS budget.
    min_width = "custom.minWidth"
    for name, width in (("Pipeline", 80), ("Workflow", 80)):
        override = next(
            (
                o
                for o in overrides
                if o.get("matcher") == {"id": "byName", "options": name}
            ),
            None,
        )
        if override is None:
            continue
        override["properties"] = [
            p for p in override["properties"] if p["id"] not in {WIDTH, min_width}
        ]
        override["properties"].append({"id": min_width, "value": width})


def _provider_reason(overrides: list[dict]) -> None:
    # Translate only the display; preserve the raw reason and saved WARN.
    for override in overrides:
        if override.get("matcher") != {"id": "byName", "options": "Reason"}:
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
    _wrap_header_defaults(panel)
    if panel.get("id") in {138, 241, 243, 256, 908}:
        # Expanded Incident evidence has no row cap: keep every row reachable.
        options = panel.setdefault("options", {})
        options["enablePagination"] = True
        options.setdefault("footer", {})["enablePagination"] = True
    overrides = panel.setdefault("fieldConfig", {}).get("overrides", [])
    _strip_stale_value_wrap(overrides, preserve_evidence=panel.get("id") == 22010)
    if panel.get("id") == 9416:
        panel["fieldConfig"]["defaults"]["custom"].setdefault("cellOptions", {})[
            "wrapText"
        ] = False
    _rank_width(overrides)
    if panel.get("id") == 3010:
        _pipeline_widths(overrides)
    if panel.get("id") in (9603, 2101):
        _provider_reason(overrides)


def apply_table_wrapping(panels: list[dict]) -> None:
    """Wrap headers and widen identity columns without changing value-wrap contracts."""
    for panel in panels:
        apply_table_wrapping(panel.get("panels", []))
        if panel.get("type") == "table":
            _wrap_table(panel)
