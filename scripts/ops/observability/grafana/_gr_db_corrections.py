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
    action_panel_id = {"bioetl-overview-v2": 215, "bioetl-dq-v2": 9102}.get(uid)
    if action_panel_id in panels:
        action_panel = panels[action_panel_id]
        pipeline_field = "Pipeline" if uid == "bioetl-overview-v2" else "pipeline"
        for transform in action_panel.get("transformations", []):
            if transform["id"] == "organize":
                options = transform["options"]
                options.setdefault("excludeByName", {}).update(
                    pipeline=False, run_type=False, action_dashboard_uid=False
                )
                options.get("renameByName", {}).pop("run_type", None)
        for field in ("run_type", "action_dashboard_uid"):
            _override(action_panel, field, "custom.hidden", True)
        if pipeline_field == "pipeline":
            _override(action_panel, "pipeline", "custom.hidden", True)
        _override(action_panel, "action_target", "custom.inspect", False)
        _override(
            action_panel,
            "action_target",
            "links",
            [
                {
                    "title": "Open routed diagnostics",
                    "url": "/d/${__data.fields.action_dashboard_uid}/?${workflow:queryparam}"
                    + "&var-pipeline=${__data.fields."
                    + pipeline_field
                    + ":percentencode}"
                    + "&${run_type:queryparam}"
                    + "&var-provider=$__all&var-pipeline_context=${__data.fields."
                    + pipeline_field
                    + ":percentencode}"
                    + "&${run_id:queryparam}&var-stage=$__all&${__url_time_range}",
                    "targetBlank": False,
                }
            ],
        )
        if uid == "bioetl-dq-v2":
            _override(action_panel, "reason", "links", [])
            _override(action_panel, "severity", "links", [])
            _override(action_panel, "severity", "custom.width", 90)
            _override(action_panel, "Action", "custom.width", 125)
            runbook = {
                "title": "DQ reason-rules runbook",
                "url": "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/docs/05-operations/runbooks/observability-checklist.md",
                "targetBlank": True,
            }
            if runbook not in action_panel.setdefault("links", []):
                action_panel["links"].append(runbook)
    for panel in panels.values():
        if (
            panel.get("type") == "stat"
            and panel.get("options", {}).get("colorMode") == "value"
        ):
            for mapping in (
                panel.get("fieldConfig", {}).get("defaults", {}).get("mappings", [])
            ):
                for value in mapping.get("options", {}).values():
                    if isinstance(value, dict) and value.get("text") in {
                        "UNKNOWN",
                        "INCOMPLETE",
                    }:
                        value["color"] = "text"
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

    scope_copy = {
        "bioetl-runtime": (
            "CURRENT · Pipeline / Run Type. Missing stages: INCOMPLETE / UNKNOWN. "
            "SCRAPING is not an active blocker; no blockers do not prove completeness."
        ),
        "bioetl-incident-v1": (
            "GLOBAL · Signals are not verified causes. Telemetry gaps remain UNKNOWN. "
            "Selected-scope status is separate; event age and impact need event evidence."
        ),
    }
    if uid in scope_copy:
        panels[9400]["options"]["content"] = (
            '<div style="padding:4px 10px;border-left:4px solid #6b7280;'
            'font-size:16px;line-height:1.2;white-space:normal;overflow-wrap:anywhere;max-width:96ch">'
            + scope_copy[uid]
            + "</div>"
        )

    if uid == "bioetl-incident-v1":
        for panel in panels.values():
            if panel.get("type") != "table":
                continue
            defaults = panel.setdefault("fieldConfig", {}).setdefault("defaults", {})
            if "EMPTY DOMAIN" in defaults.get("noValue", ""):
                # Grafana applies noValue to missing cells inside non-empty rows too.
                defaults["noValue"] = "UNKNOWN"
        for panel_id in (2005, 22005):
            for field in ("instance", "job"):
                _override(panels[panel_id], field, "noValue", "NOT PROVIDED")
            for field, width in (
                ("severity", 85),
                ("alertstate", 95),
                ("instance", 145),
                ("job", 185),
            ):
                _override(panels[panel_id], field, "custom.width", width)

    if uid == "bioetl-provider-health-v2":
        _override(
            panels[9101],
            "provider",
            "custom.cellOptions",
            {"type": "auto", "wrapText": False},
        )
        for field in ("reason", "Reason", "Source state"):
            _override(
                panels[9107],
                field,
                "custom.cellOptions",
                {"type": "auto", "wrapText": False},
            )
        _override(
            panels[9107],
            "reason",
            "mappings",
            [
                {
                    "type": "value",
                    "options": {
                        "observed_health_status": {"text": "Observed"},
                        "invalid_health_timestamp": {"text": "Bad time"},
                        "missing_health_status": {"text": "Missing"},
                    },
                }
            ],
        )
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
            for item in panel["fieldConfig"]["overrides"]:
                item["properties"] = [
                    prop for prop in item["properties"] if prop["id"] != "custom.width"
                ]
            _override(
                panel, "Severity" if panel_id == 9102 else "Status", "custom.width", 130
            )
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
            _override(
                panel,
                "Provider",
                "mappings",
                [
                    {
                        "type": "value",
                        "options": {
                            "VALID EMPTY - fleet observed, no non-OK providers": {
                                "text": "No non-OK providers"
                            }
                        },
                    }
                ],
            )
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
        for panel_id in (9103, 9113):
            panel = panels[panel_id]
            for field in ("cause", "Cause"):
                _override(
                    panel,
                    field,
                    "mappings",
                    [
                        {
                            "type": "value",
                            "options": {
                                "VALID EMPTY - FLEET coverage proven, no active provider causes": {
                                    "text": "VALID EMPTY - no active causes"
                                },
                                "UNKNOWN - FLEET cause coverage unproven, restore provider telemetry": {
                                    "text": "UNKNOWN - restore telemetry"
                                },
                            },
                        }
                    ],
                )
            # The synthetic verdict is a presence marker, not an event count.
            _override(panel, "Value", "custom.hidden", True)

    if uid == "bioetl-control-plane-v1":
        retention = panels[9416]
        for item in retention["fieldConfig"]["overrides"]:
            if item["matcher"].get("options") in ("Check", "Status"):
                item["properties"] = [
                    p for p in item["properties"] if p["id"] != "custom.width"
                ]
        _override(retention, "check", "custom.width", 125)
        _override(retention, "status", "custom.width", 110)
        for field in ("check", "Check", "reason", "Reason"):
            _override(
                retention,
                field,
                "custom.cellOptions",
                {"type": "auto", "wrapText": False},
            )
        for field in ("reason", "Reason"):
            _override(
                retention,
                field,
                "mappings",
                [
                    {
                        "type": "value",
                        "options": {
                            "snapshot_evidence_not_required": {"text": "Not required"},
                        },
                    }
                ],
            )
        _override(
            retention,
            "check",
            "mappings",
            [
                {
                    "type": "value",
                    "options": {
                        "required_evidence": {"text": "Evidence"},
                        "retention_policy": {"text": "Policy"},
                    },
                }
            ],
        )
        for field in ("status", "Status"):
            _override(
                retention,
                field,
                "mappings",
                [
                    {
                        "type": "value",
                        "options": {
                            "OK": {"text": "OK", "color": "green"},
                            "WARN": {"text": "WARN", "color": "orange"},
                            "WARNING": {"text": "WARN", "color": "orange"},
                            "ERROR": {"text": "ERROR", "color": "red"},
                            "UNKNOWN": {"text": "UNKNOWN", "color": "text"},
                            "INCOMPLETE": {"text": "INCOMPLETE", "color": "text"},
                        },
                    }
                ],
            )
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
        if uid == "bioetl-incident-v1" and panel_id in (2010, 22010):
            # Keep the summary readable; duplicated/raw details remain in 22010.
            if panel_id == 2010:
                for field in ("Details", "Domain"):
                    _override(panel, field, "custom.hidden", True)
            for field, width in (
                ("Rank", 50),
                ("Severity", 85),
                ("Confidence", 125),
                ("Action", 90),
            ):
                _override(panel, field, "custom.width", width)
            if panel_id == 22010:
                _override(panel, "Domain", "custom.width", 100)
                # Grafana's linked-cell renderer forces ellipsis; keep the
                # dedicated Action link and render evidence as wrapping text.
                for field in ("Object", "Signal"):
                    _override(panel, field, "links", [])
                for field in ("Object", "Signal", "Details"):
                    _override(panel, field, "custom.wrapText", True)
                    _override(
                        panel,
                        field,
                        "custom.cellOptions",
                        {"type": "auto", "wrapText": True},
                    )
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
        reason_links = [
            {
                **link,
                "title": "Inspect saved Trust reasons",
                "url": link["url"].replace("viewPanel=9414", "viewPanel=9451"),
            }
            for link in trust["links"]
        ]
        _override(trust, "Reasons", "links", reason_links)
        details = panels[9451]
        for transform in details.get("transformations", []):
            options = transform["options"]
            if transform["id"] == "filterFieldsByName":
                options["include"]["names"] = [
                    {"reason": "reason_display", "verdict": "display_verdict"}.get(
                        name, name
                    )
                    for name in options["include"]["names"]
                ]
            elif transform["id"] == "organize":
                options["indexByName"]["reason_display"] = options["indexByName"].pop(
                    "reason", 2
                )
                options["renameByName"].pop("reason", None)
                options["renameByName"]["reason_display"] = "Reason"
                options["indexByName"]["display_verdict"] = options["indexByName"].pop(
                    "verdict", 1
                )
                options["renameByName"].pop("verdict", None)
                options["renameByName"]["display_verdict"] = "Status"
        _override(
            details, "Reason", "custom.cellOptions", {"type": "auto", "wrapText": True}
        )
        _override(details, "Reason", "custom.inspect", True)
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
        _override(panels[243], "Expected", "noValue", "N/A: not declared")
        _override(panels[243], "Expected", "custom.width", 150)
        _override(panels[243], "Observed Records", "custom.width", 150)
        stage_panel = panels[2460]
        for field in ("Backlog", "Lag", "Throughput"):
            _override(stage_panel, field, "custom.width", 100)
        _override(
            stage_panel,
            "scope_stage\\measure",
            "displayName",
            "Pipeline / Run Type / Stage",
        )
        for field in ("reason",):
            _override(panels[9101], field, "links", [])
            _override(
                panels[9101],
                field,
                "custom.cellOptions",
                {"type": "auto", "wrapText": True},
            )
        _override(panels[9101], "severity", "custom.width", 110)
        _override(panels[9101], "Action", "custom.width", 110)
        _override(panels[9101], "action_target", "custom.inspect", False)
        _override(panels[9101], "Count", "custom.hidden", True)
        for transform in panels[9101].get("transformations", []):
            if transform["id"] == "organize":
                transform["options"]["excludeByName"].update(
                    pipeline=False, run_type=False
                )
        for field in ("pipeline", "run_type"):
            _override(panels[9101], field, "custom.hidden", True)
        _override(
            panels[9101],
            "action_target",
            "links",
            [
                {
                    "title": "Open blocker diagnostics",
                    "url": "/d/${__data.fields.action_dashboard_uid}/?${workflow:queryparam}&var-pipeline=${__data.fields.pipeline:percentencode}&var-run_type=${__data.fields.run_type:percentencode}&${run_id:queryparam}&${__url_time_range}",
                    "targetBlank": False,
                }
            ],
        )
        _override(
            panels[9101],
            "Reason",
            "custom.cellOptions",
            {"type": "auto", "wrapText": False},
        )
        for override in panels[9101]["fieldConfig"]["overrides"]:
            if override["matcher"].get("options") in ("Status", "Severity", "Pipeline"):
                override["properties"] = [
                    prop
                    for prop in override["properties"]
                    if prop["id"] != "custom.width"
                ]
        for target in panels[2460].get("targets", []):
            if "legendFormat" in target:
                target["legendFormat"] = "{{stage}}"
    if uid == "bioetl-dq-v2" and 155 in panels:
        soft = 'sum by (pipeline) (increase(bioetl_dq_soft_threshold_exceeded_total{pipeline=~"$pipeline"}[$__rate_interval]))'
        hard = 'sum by (pipeline) (increase(bioetl_dq_validation_failures_total{pipeline=~"$pipeline", severity="hard_fail"}[$__rate_interval]))'
        panels[155]["targets"][0]["expr"] = (
            f"round(sum({soft}) + sum({hard})) unless "
            f"(count({soft} unless on(pipeline) {hard}) or "
            f"count({hard} unless on(pipeline) {soft}))"
        )
        panels[155]["description"] = (
            "TIME RANGE · Total soft plus hard threshold events requires observations "
            "for both counters for every observed pipeline. A missing branch leaves the total UNKNOWN, not zero. "
            "Inspect each counter when coverage is incomplete; resets use increase."
            " Tooltip and inspection expose full series labels; full identifiers remain available."
        )
    if uid == "bioetl-overview-v2" and 215 in panels:
        _override(panels[215], "Action", "custom.width", 150)
