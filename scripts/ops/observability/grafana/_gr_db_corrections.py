"""Canonical panel corrections from the September 2026 data/readability audit."""

from __future__ import annotations

import re


def _panels(items: list[dict]):
    for panel in items:
        yield panel
        yield from _panels(panel.get("panels", []))


def _override(panel: dict, field: str, prop: str, value: object) -> None:
    overrides = panel.setdefault("fieldConfig", {}).setdefault("overrides", [])
    matcher = {"id": "byName", "options": field}
    entry = next((o for o in overrides if o.get("matcher") == matcher), None)
    if entry is None:
        entry = {"matcher": matcher, "properties": []}
        overrides.append(entry)
    if prop == "mappings":
        existing = [
            *panel["fieldConfig"].get("defaults", {}).get("mappings", []),
            *(
                mapping
                for other in overrides
                if other.get("matcher", {}).get("id") == "byName"
                and str(other["matcher"].get("options", "")).casefold()
                == field.casefold()
                for item in other.get("properties", [])
                if item["id"] == prop
                for mapping in item["value"]
            ),
        ]
        incoming = value[0]["options"]
        previous = {}
        for mapping in existing:
            if mapping.get("type") == "value":
                previous.update(mapping.get("options", {}))
        value = [{"type": "value", "options": {**previous, **incoming}}]
        for mapping in existing:
            if mapping.get("type") != "value" and mapping not in value:
                value.append(mapping)
    entry["properties"] = [p for p in entry["properties"] if p["id"] != prop]
    entry["properties"].append({"id": prop, "value": value})


def apply_corrections(payload: dict) -> None:
    """Apply idempotent source-level corrections before dashboard serialization."""
    uid = payload.get("uid")
    panels = {p["id"]: p for p in _panels(payload.get("panels", []))}
    for panel in panels.values():
        if (
            any(
                "/ops/control-plane/" in target.get("url", "")
                for target in panel.get("targets", [])
            )
            and panel.get("type") == "table"
        ):
            for field in ("reason", "Reason"):
                _override(
                    panel,
                    field,
                    "mappings",
                    [
                        {
                            "type": "value",
                            "options": {
                                "deadline_exceeded": {
                                    "text": "QUERY ERROR — deadline exceeded",
                                    "color": "red",
                                },
                                "capacity_exhausted": {
                                    "text": "QUERY ERROR — capacity exhausted",
                                    "color": "red",
                                },
                                "catalog_unavailable": {
                                    "text": "QUERY ERROR — catalog unavailable",
                                    "color": "red",
                                },
                            },
                        }
                    ],
                )
        for target in panel.get("targets", []):
            if "expr" not in target:
                continue
            expression = target.get("expr", "")
            target["expr"] = (
                re.sub(
                    r"((?:rate|increase)\([^\[\]]*)\[\$__interval\]",
                    r"\1[$__rate_interval]",
                    expression,
                )
                if expression
                else expression
            )

    if uid == "bioetl-provider-health-v2":
        _override(panels[9107], "Provider", "custom.width", 95)
        _override(panels[9107], "Source state", "custom.width", 105)
        _override(panels[9107], "Status", "custom.width", 100)
        fleet = "max by (provider) (bioetl_provider_current_status)"
        health = "max by (provider) (bioetl_provider_health_status)"
        coverage = (
            f"((count({fleet}) > 0) * 0 + 1)"
            f" * absent({fleet} != 0)"
            f" * absent({fleet} unless on(provider) {health})"
        )
        empty = f'label_replace((({coverage}) * 0 - 1), "provider", "VALID EMPTY - fleet observed, no non-OK providers", "", "")'
        empty = f'label_replace({empty}, "provider_target", "$$__all", "", "")'
        for panel_id in (9102, 9112):
            panel = panels[panel_id]
            expr = f"{fleet} >= 1"
            if panel_id == 9102:
                expr = f"topk(4, {expr})"
            expr = (
                f'label_replace(({expr}), "provider_target", "$1", "provider", "(.*)")'
            )
            panel["targets"][0]["expr"] = f"({expr}) or {empty}"
            _override(
                panel,
                "Severity" if panel_id == 9102 else "Status",
                "mappings",
                [
                    {
                        "type": "value",
                        "options": {
                            "-1": {"text": "VALID EMPTY", "color": "text"},
                            "1": {"text": "WARN", "color": "yellow"},
                            "2": {"text": "CRIT", "color": "red"},
                            "3": {"text": "UNKNOWN", "color": "gray"},
                        },
                    }
                ],
            )
            _override(panel, "provider_target", "custom.hidden", True)
            for link in panel["fieldConfig"].get("defaults", {}).get("links", []):
                link["url"] = link.get("url", "").replace(
                    "${__data.fields.provider:percentencode}",
                    "${__data.fields.provider_target:percentencode}",
                )
            panel["description"] = (
                "GLOBAL · Current fleet, independent of the selected Provider. "
                "VALID EMPTY requires every observed "
                "provider to have health evidence and current status OK. Missing coverage "
                "remains UNKNOWN; query failure is not a healthy empty fleet."
            )

    if uid == "bioetl-control-plane-v1":
        panels[892]["description"] = (
            "CURRENT · Last checkpoint age, informational only; age does not change readiness. "
            "Missing evidence remains UNKNOWN. Pipeline-scoped, independent of Run ID."
        )
        for panel_id in (3, 104, 120, 101, 102, 103, 4, 137):
            panel = panels[panel_id]
            if "UNKNOWN" not in panel.get("description", ""):
                panel["description"] = panel.get("description", "") + (
                    " Missing counter evidence is UNKNOWN; measured zero means no observed events."
                )

    targets = {
        "bioetl-dq-v2": (9102,),
        "bioetl-runtime": (9101, 243, 2460),
        "bioetl-overview-v2": (215, 9603),
        "bioetl-run-explorer-v1": (3010,),
        "bioetl-incident-v1": (2010, 22010),
    }
    if uid == "bioetl-control-plane-v1" and 5 in panels:
        panels[5]["description"] = (
            "TIME RANGE · Checkpoint compatibility decisions by outcome. "
            "An absent series is TELEMETRY MISSING and remains UNKNOWN. "
            "Run Type does not affect this panel."
        )
    for panel_id in targets.get(uid, ()):
        panel = panels.get(panel_id)
        if panel is None or panel.get("type") != "table":
            continue
        custom = (
            panel.setdefault("fieldConfig", {})
            .setdefault("defaults", {})
            .setdefault("custom", {})
        )
        custom.setdefault("cellOptions", {"type": "auto"})["wrapText"] = False
        custom["wrapText"] = False
        panel.setdefault("options", {})["cellHeight"] = (
            "sm" if uid == "bioetl-incident-v1" and panel_id == 2010 else "lg"
        )
        for transform in panel.get("transformations", []):
            if transform.get("id") == "organize":
                transform.setdefault("options", {}).setdefault(
                    "excludeByName", {}
                ).update({"__name__": True, "job": True})
                transform["options"]["excludeByName"]["action_dashboard_uid"] = False
        # Hide routing metadata visually while retaining it for data links.
        _override(panel, "action_dashboard_uid", "custom.hidden", True)
        # Reserve only compact categorical fields; explanations share free width.
        for item in panel.get("fieldConfig", {}).get("overrides", []):
            item["properties"] = [
                prop
                for prop in item["properties"]
                if prop["id"] not in {"custom.width", "custom.minWidth"}
            ]
        widths = (
            (("Pipeline", 140),)
            if uid == "bioetl-overview-v2" and panel_id == 215
            else (("Status", 90), ("Severity", 90), ("Pipeline", 140))
        )
        for field, width in widths:
            _override(panel, field, "custom.width", width)
        if uid == "bioetl-overview-v2" and panel_id == 9603:
            _override(panel, "Status", "custom.width", 130)
        if uid == "bioetl-run-explorer-v1" and panel_id == 3010:
            # The ten-run index stays compact; cell inspection exposes full IDs.
            custom["wrapText"] = False
            custom["cellOptions"]["wrapText"] = False
            _override(panel, "selected", "custom.width", 28)
            _override(panel, "Started", "custom.width", 145)
            _override(
                panel,
                "Status",
                "mappings",
                [
                    {
                        "type": "value",
                        "options": {
                            "unfinished": {"text": "unfinished", "color": "gray"}
                        },
                    }
                ],
            )
        if uid == "bioetl-overview-v2" and panel_id == 215:
            panel["gridPos"]["h"] = 6
            panels[9603]["gridPos"].update(y=11, h=6)
            _override(panel, "Priority", "custom.width", 90)
            _override(panel, "Action", "custom.width", 125)
            _override(
                panel,
                "action_target",
                "mappings",
                [
                    {
                        "type": "value",
                        "options": {
                            key: {"text": "Diagnostics", "color": "text"}
                            for key in ("runtime", "workflow")
                        },
                    }
                ],
            )
            _override(
                panel,
                "action_reason",
                "mappings",
                [
                    {
                        "type": "value",
                        "options": {
                            f"{key}_evidence_missing": {
                                "text": f"{label}: evidence missing"
                            }
                            for key, label in (
                                ("control_plane", "Control Plane"),
                                ("runtime", "Runtime"),
                                ("gold", "Gold"),
                                ("dq", "DQ"),
                                ("provider", "Provider"),
                                ("workflow", "Workflow"),
                            )
                        },
                    }
                ],
            )
        panel["options"]["cellHeight"] = "sm"
    if uid == "bioetl-control-plane-v1" and 9418 in panels:
        trust = panels[9418]
        trust["fieldConfig"]["defaults"]["custom"]["cellOptions"] = {
            "type": "auto",
            "wrapText": False,
        }
        for transform in trust.get("transformations", []):
            if transform.get("id") == "organize":
                options = transform["options"]
                options.setdefault("excludeByName", {})["reasons_display"] = True
                options["renameByName"].pop("reasons_display", None)
                options["renameByName"]["reasons_count"] = "Reasons"
                options["indexByName"]["reasons_count"] = 2
        for field, width in (
            ("Result", 80),
            ("Trust", 115),
            ("Reasons", 65),
        ):
            _override(trust, field, "custom.width", width)
        for item in trust["fieldConfig"]["overrides"]:
            if item["matcher"].get("options") == "Observed":
                item["properties"] = [
                    p for p in item["properties"] if p["id"] != "custom.width"
                ]
        _override(trust, "Reasons", "custom.cellOptions", {"type": "auto"})
        _override(trust, "Reasons", "custom.hidden", False)
        _override(trust, "Reasons", "noValue", "Inspect")
        _override(trust, "Reasons", "links", trust["links"])
        for item in trust["fieldConfig"]["overrides"]:
            for prop in item["properties"]:
                if prop["id"] == "mappings":
                    for mapping in prop["value"]:
                        if mapping.get("type") == "value":
                            for value in mapping["options"].values():
                                if value.get("color") == "#555555":
                                    value["color"] = "#A3A3A3"
    # A display-name alias must not reserve the same column's width twice.
    for panel in panels.values():
        width_fields = set()
        for override in panel.get("fieldConfig", {}).get("overrides", []):
            matcher = override.get("matcher", {})
            if matcher.get("id") != "byName":
                continue
            field = str(matcher.get("options", "")).casefold()
            properties = override.get("properties", [])
            if any(prop["id"] == "custom.width" for prop in properties):
                if field in width_fields:
                    override["properties"] = [
                        prop for prop in properties if prop["id"] != "custom.width"
                    ]
                width_fields.add(field)
    if uid == "bioetl-runtime" and 2460 in panels:
        for target in panels[2460].get("targets", []):
            if "legendFormat" in target:
                target["legendFormat"] = "{{stage}}"
    if uid == "bioetl-dq-v2" and 155 in panels:
        panels[155]["description"] = (
            "TIME RANGE · Total soft plus hard threshold events requires observations "
            "for both counters. A missing branch leaves the total UNKNOWN, not zero. "
            "Inspect each counter when coverage is incomplete; resets use increase."
            " Tooltip and inspection expose full series labels; full identifiers remain available."
        )
