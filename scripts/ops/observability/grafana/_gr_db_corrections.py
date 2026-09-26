"""Canonical panel corrections from the September 2026 data/readability audit."""

from __future__ import annotations

import re

_HIDDEN = "custom.hidden"
_INSPECT = "custom.inspect"
_WIDTH = "custom.width"
_CELL = "custom.cellOptions"


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


def _guard_histogram_generation(expression: str) -> str:
    """Exclude aggregates spanning producer generations before estimating quantiles."""
    if "_created[" in expression or "_created{" in expression:
        return expression
    match = re.search(
        r"sum by \(([^)]*)\) \((?:increase|rate)\("
        r"(bioetl_\w+)_bucket(\{.*?\})?\[([^]]*)\]\)\)",
        expression,
    )
    if match is None:
        raise ValueError("Unsupported histogram aggregation: " + expression)
    labels = ", ".join(
        label.strip() for label in match[1].split(",") if label.strip() != "le"
    )
    created = f"{match[2]}_created{match[3] or ''}[{match[4]}]"
    aggregate = f"sum by ({labels})" if labels else "sum"
    reset = f"{aggregate} (changes({created}) > 0)"
    # Suppress the whole output group, not just one producer: a partial
    # histogram is not the requested aggregate and must not look complete.
    guarded = f"({match[0]} unless on ({labels}) ({reset}))"
    return expression[: match.start()] + guarded + expression[match.end() :]


_TABLE_TARGETS = {
    "bioetl-dq-v2": (9102,),
    "bioetl-runtime": (9101, 243, 2460),
    "bioetl-overview-v2": (215, 9603),
    "bioetl-run-explorer-v1": (3010,),
    "bioetl-incident-v1": (2010, 22010),
}

_SCOPE_COPY = {
    "bioetl-runtime": (
        "SELECTED RUN. Saved pipeline evidence for this Run ID. "
        "Fleet and time-range charts are on Incident Workspace."
    ),
    "bioetl-incident-v1": (
        "GLOBAL · Signals are not verified causes. Telemetry gaps remain UNKNOWN. "
        "Selected-scope status is separate; event age and impact need event evidence."
    ),
}

_QUERY_ERROR_MAPPINGS = [
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
]


def _correct_action_panel_dq(action_panel: dict) -> None:
    _override(action_panel, "reason", "links", [])
    _override(action_panel, "severity", "links", [])
    _override(action_panel, "severity", _WIDTH, 90)
    _override(action_panel, "Action", _WIDTH, 125)
    runbook = {
        "title": "DQ reason-rules runbook",
        "url": "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/docs/05-operations/runbooks/observability-checklist.md",
        "targetBlank": True,
    }
    if runbook not in action_panel.setdefault("links", []):
        action_panel["links"].append(runbook)


def _correct_action_panel(uid: object, panels: dict[int, dict]) -> None:
    action_panel_id = {"bioetl-overview-v2": 215, "bioetl-dq-v2": 9102}.get(uid)
    if action_panel_id not in panels:
        return
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
        _override(action_panel, field, _HIDDEN, True)
    if pipeline_field == "pipeline":
        _override(action_panel, "pipeline", _HIDDEN, True)
    _override(action_panel, "action_target", _INSPECT, False)
    _override(
        action_panel,
        "action_target",
        "links",
        [
            {
                "title": "Open routed diagnostics",
                "url": "/d/${__data.fields.action_dashboard_uid}/?${workflow:queryparam}"
                + "&${__data.fields.action_scope:raw}&${run_type:queryparam}"
                + "&${run_id:queryparam}&${__url_time_range}",
                "targetBlank": False,
            }
        ],
    )
    if uid == "bioetl-dq-v2":
        _correct_action_panel_dq(action_panel)


def _correct_timeseries_legend(panel: dict) -> None:
    legend = panel.get("options", {}).get("legend", {})
    if not (
        panel.get("type") == "timeseries"
        and "sum" in legend.get("calcs", [])
        and any(
            re.search(r"\b(?:rate|increase)\(", target.get("expr", ""))
            for target in panel.get("targets", [])
        )
    ):
        return
    # Adjacent increase/rate samples overlap. Their sum varies with the
    # evaluation step and is not the number of events in the time range.
    legend["calcs"] = list(
        dict.fromkeys(
            "lastNotNull" if calc == "sum" else calc for calc in legend["calcs"]
        )
    )
    explanation = (
        " Rolling-window samples overlap; legend Last is the last observed "
        "window, not an event total for the selected time range."
    )
    if "Rolling-window samples overlap" not in panel.get("description", ""):
        panel["description"] = panel.get("description", "") + explanation


def _correct_stat_unknown_color(panel: dict) -> None:
    if not (
        panel.get("type") == "stat"
        and panel.get("options", {}).get("colorMode") == "value"
    ):
        return
    for mapping in panel.get("fieldConfig", {}).get("defaults", {}).get("mappings", []):
        for value in mapping.get("options", {}).values():
            if isinstance(value, dict) and value.get("text") in {
                "UNKNOWN",
                "INCOMPLETE",
            }:
                value["color"] = "text"


def _correct_deadline_reason_mappings(panel: dict) -> None:
    if not (
        any(
            "/ops/control-plane/" in target.get("url", "")
            for target in panel.get("targets", [])
        )
        and panel.get("type") == "table"
    ):
        return
    for field in ("reason", "Reason"):
        _override(panel, field, "mappings", _QUERY_ERROR_MAPPINGS)


def _annotate_histogram_panel(panel: dict, target: dict) -> None:
    target["expr"] = _guard_histogram_generation(target["expr"])
    explanation = (
        " Histogram generation guard: windows with a changed producer "
        "creation timestamp are omitted for the whole aggregate. "
        "A repeated batch snapshot is not a continuous counter; "
        "narrow the window to one stable generation. "
        "Omitted values do not mean zero latency."
    )
    if "Histogram generation guard:" not in panel.get("description", ""):
        panel["description"] = panel.get("description", "") + explanation
    if not target["expr"].endswith(" >= 0"):
        target["expr"] = f"({target['expr']}) >= 0"
    defaults = panel.setdefault("fieldConfig", {}).setdefault("defaults", {})
    if not defaults.get("noValue", "").startswith("No GLOBAL"):
        defaults["noValue"] = "NO OBSERVATIONS — no usable histogram increments"
    defaults.setdefault("custom", {})["showPoints"] = "always"


def _guard_panel_histograms(panel: dict) -> None:
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
        if re.match(r"^\(*histogram_quantile\(", target["expr"]):
            _annotate_histogram_panel(panel, target)


def _apply_per_panel_corrections(panels: dict[int, dict]) -> None:
    for panel in panels.values():
        _correct_timeseries_legend(panel)
        _correct_stat_unknown_color(panel)
        _correct_deadline_reason_mappings(panel)
        _guard_panel_histograms(panel)


def _stamp_scope_copy(uid: object, panels: dict[int, dict]) -> None:
    if uid not in _SCOPE_COPY:
        return
    panels[9400]["options"]["content"] = (
        '<div style="padding:4px 10px;border-left:4px solid #6b7280;'
        'font-size:16px;line-height:1.2;white-space:normal;overflow-wrap:anywhere;max-width:96ch">'
        + _SCOPE_COPY[uid]
        + "</div>"
    )


def _correct_incident(uid: object, panels: dict[int, dict]) -> None:
    if uid != "bioetl-incident-v1":
        return
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
            _override(panels[panel_id], field, _WIDTH, width)


def _correct_provider_fleet_panel(
    panel: dict, panel_id: int, fleet: str, empty: str
) -> None:
    for item in panel["fieldConfig"]["overrides"]:
        item["properties"] = [
            prop for prop in item["properties"] if prop["id"] != _WIDTH
        ]
    status_field = "Severity" if panel_id == 9102 else "Status"
    _override(panel, status_field, _WIDTH, 130)
    expr = f"{fleet} >= 1"
    if panel_id == 9102:
        expr = f"topk(4, {expr})"
    expr = f'label_replace(({expr}), "provider_target", "$1", "provider", "(.*)")'
    panel["targets"][0]["expr"] = f"({expr}) or {empty}"
    _override(
        panel,
        status_field,
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
    _override(panel, "provider_target", _HIDDEN, True)
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


def _correct_provider_cause_panel(panel: dict) -> None:
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
    _override(panel, "Value", _HIDDEN, True)


def _correct_provider(uid: object, panels: dict[int, dict]) -> None:
    if uid != "bioetl-provider-health-v2":
        return
    if 9401 not in panels or 9101 not in panels or 9107 not in panels:
        return
    # Sparse real counter observations (including a single zero) need a
    # marker; a line alone renders an indistinguishable empty chart.
    panels[32]["fieldConfig"]["defaults"]["custom"]["showPoints"] = "always"
    panels[32]["options"]["legend"].update(showLegend=True, displayMode="list")
    _override(
        panels[9101],
        "provider",
        _CELL,
        {"type": "auto", "wrapText": False},
    )
    for field in ("reason", "Reason", "Source state"):
        _override(
            panels[9107],
            field,
            _CELL,
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
    _override(panels[9107], "Provider", _WIDTH, 95)
    _override(panels[9107], "Source state", _WIDTH, 105)
    _override(panels[9107], "Status", _WIDTH, 100)
    panels[9401]["targets"] = [
        {
            "expr": 'count(bioetl_pstatus{provider=~"$provider"} == 0)',
            "legendFormat": "OK",
            "instant": True,
            "refId": "A",
        },
        {
            "expr": 'count(bioetl_pstatus{provider=~"$provider"} == 1)',
            "legendFormat": "WARN",
            "instant": True,
            "refId": "B",
        },
        {
            "expr": 'count(bioetl_pstatus{provider=~"$provider"} == 2)',
            "legendFormat": "CRIT",
            "instant": True,
            "refId": "C",
        },
        {
            "expr": 'count(bioetl_pstatus{provider=~"$provider"} == 3)',
            "legendFormat": "UNKNOWN",
            "instant": True,
            "refId": "D",
        },
    ]
    panels[9401]["fieldConfig"]["defaults"]["mappings"] = []
    panels[9401]["title"] = "Monitor Provider Status"
    panels[9401]["fieldConfig"]["defaults"]["noValue"] = "TELEMETRY MISSING"
    panels[9401]["description"] = (
        "CURRENT · выбранный провайдер, не история Run ID. "
        "Run ID — контекст навигации. "
        "UNKNOWN: нет или недостоверно наблюдение (в том числе invalid_health_timestamp). "
        "TELEMETRY MISSING: нет серии. QUERY ERROR: сбой запроса. "
        "Если провайдер не определён — выберите его. "
        "All — общий текущий статус; одна серия не означает полноту всего набора."
    )
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
        _correct_provider_fleet_panel(panels[panel_id], panel_id, fleet, empty)
    for panel_id in (9103, 9113):
        _correct_provider_cause_panel(panels[panel_id])


def _correct_control_plane(uid: object, panels: dict[int, dict]) -> None:
    if uid != "bioetl-control-plane-v1":
        return
    retention = panels[9416]
    # B repeated the full retention/hash verification only to rename a header.
    # Keep the evidence rows from A; their statuses already convey the result.
    retention["targets"] = [
        target for target in retention["targets"] if target.get("refId") != "B"
    ]
    retention["transformations"] = [
        transform
        for transform in retention.get("transformations", [])
        if not (
            transform.get("id") == "configFromData"
            and transform.get("options", {}).get("configRefId") == "B"
        )
    ]
    for item in retention["fieldConfig"]["overrides"]:
        if item["matcher"].get("options") in ("Check", "Status"):
            item["properties"] = [p for p in item["properties"] if p["id"] != _WIDTH]
    _override(retention, "check", _WIDTH, 125)
    _override(retention, "status", _WIDTH, 110)
    for field in ("check", "Check", "reason", "Reason"):
        _override(
            retention,
            field,
            _CELL,
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
    if 892 in panels:
        panels[892]["description"] = (
            "CURRENT · Last checkpoint age, informational only; age does not change readiness. "
            "Missing evidence remains UNKNOWN. Pipeline-scoped, independent of Run ID."
        )
    for panel_id in (3, 104, 120, 101, 102, 103, 4, 137):
        panel = panels.get(panel_id)
        if panel is None:
            continue
        if "UNKNOWN" not in panel.get("description", ""):
            panel["description"] = panel.get("description", "") + (
                " Missing counter evidence is UNKNOWN; measured zero means no observed events."
            )
    if 5 in panels:
        panels[5]["description"] = (
            "TIME RANGE · Checkpoint compatibility decisions by outcome. "
            "An absent series is TELEMETRY MISSING and remains UNKNOWN. "
            "Run Type does not affect this panel."
        )


def _compact_table_base(uid: object, panel_id: int, panel: dict) -> None:
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
            transform.setdefault("options", {}).setdefault("excludeByName", {}).update(
                {"__name__": True, "job": True}
            )
            transform["options"]["excludeByName"]["action_dashboard_uid"] = False
    # Hide routing metadata visually while retaining it for data links.
    _override(panel, "action_dashboard_uid", _HIDDEN, True)
    # Reserve only compact categorical fields; explanations share free width.
    for item in panel.get("fieldConfig", {}).get("overrides", []):
        item["properties"] = [
            prop
            for prop in item["properties"]
            if prop["id"] not in {_WIDTH, "custom.minWidth"}
        ]
    widths = (
        (("Pipeline", 140),)
        if uid == "bioetl-overview-v2" and panel_id == 215
        else (("Status", 90), ("Severity", 90), ("Pipeline", 140))
    )
    for field, width in widths:
        _override(panel, field, _WIDTH, width)


def _correct_incident_table(panel: dict, panel_id: int) -> None:
    # Keep the summary readable; duplicated/raw details remain in 22010.
    if panel_id == 2010:
        for field in ("Details", "Domain"):
            _override(panel, field, _HIDDEN, True)
    for field, width in (
        ("Rank", 50),
        ("Severity", 85),
        ("Confidence", 125),
        ("Action", 90),
    ):
        _override(panel, field, _WIDTH, width)
    if panel_id != 22010:
        return
    _override(panel, "Domain", _WIDTH, 100)
    # Grafana's linked-cell renderer forces ellipsis; keep the
    # dedicated Action link and render evidence as wrapping text.
    for field in ("Object", "Signal"):
        _override(panel, field, "links", [])
    for field in ("Object", "Signal", "Details"):
        _override(panel, field, "custom.wrapText", True)
        _override(panel, field, _CELL, {"type": "auto", "wrapText": True})


def _correct_run_explorer_index_compact(panel: dict) -> None:
    # The ten-run index stays compact; cell inspection exposes full IDs.
    custom = panel["fieldConfig"]["defaults"]["custom"]
    custom["wrapText"] = False
    custom["cellOptions"]["wrapText"] = False
    _override(panel, "selected", _WIDTH, 28)
    _override(panel, "Started", _WIDTH, 145)
    _override(
        panel,
        "Status",
        "mappings",
        [
            {
                "type": "value",
                "options": {"unfinished": {"text": "unfinished", "color": "gray"}},
            }
        ],
    )


def _correct_overview_action_table(panel: dict, panels: dict[int, dict]) -> None:
    panel["gridPos"]["h"] = 6
    panels[9603]["gridPos"].update(y=11, h=6)
    _override(panel, "Priority", _WIDTH, 90)
    _override(panel, "Action", _WIDTH, 125)
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
                    f"{key}_evidence_missing": {"text": f"{label}: evidence missing"}
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


def _apply_table_uid_extras(
    uid: object, panel_id: int, panel: dict, panels: dict[int, dict]
) -> None:
    if uid == "bioetl-incident-v1" and panel_id in (2010, 22010):
        _correct_incident_table(panel, panel_id)
    if uid == "bioetl-overview-v2" and panel_id == 9603:
        _override(panel, "Status", _WIDTH, 130)
    if uid == "bioetl-run-explorer-v1" and panel_id == 3010:
        _correct_run_explorer_index_compact(panel)
    if uid == "bioetl-overview-v2" and panel_id == 215:
        _correct_overview_action_table(panel, panels)


def _apply_table_targets(uid: object, panels: dict[int, dict]) -> None:
    for panel_id in _TABLE_TARGETS.get(uid, ()):
        panel = panels.get(panel_id)
        if panel is None or panel.get("type") != "table":
            continue
        _compact_table_base(uid, panel_id, panel)
        _apply_table_uid_extras(uid, panel_id, panel, panels)
        panel["options"]["cellHeight"] = "sm"


def _lighten_mapping_value(value: dict) -> None:
    if value.get("color") == "#555555":
        value["color"] = "#A3A3A3"


def _lighten_override_mappings(item: dict) -> None:
    for prop in item["properties"]:
        if prop["id"] != "mappings":
            continue
        for mapping in prop["value"]:
            if mapping.get("type") == "value":
                for value in mapping["options"].values():
                    _lighten_mapping_value(value)


def _organize_trust_reasons(trust: dict) -> None:
    for transform in trust.get("transformations", []):
        if transform.get("id") == "organize":
            options = transform["options"]
            options.setdefault("excludeByName", {})["reasons_display"] = True
            options["renameByName"].pop("reasons_display", None)
            options["renameByName"]["reasons_count"] = "Reason count"
            options["renameByName"]["processing_status"] = "Processing result"
            options["renameByName"]["trust_status"] = "Saved trust verdict"
            options["renameByName"]["evidence_observed_at"] = "Assessed at"
            options["renameByName"]["trust_reasons_action"] = "Action"
            options["indexByName"]["reasons_count"] = 2
            options["indexByName"]["trust_reasons_action"] = 4


def _organize_trust_details(details: dict) -> None:
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


def _correct_control_plane_trust(uid: object, panels: dict[int, dict]) -> None:
    if uid != "bioetl-control-plane-v1" or 9418 not in panels:
        return
    trust = panels[9418]
    trust["fieldConfig"]["defaults"]["custom"]["cellOptions"] = {
        "type": "auto",
        "wrapText": False,
    }
    _organize_trust_reasons(trust)
    for field, width in (
        ("Processing result", 110),
        ("Saved trust verdict", 110),
        ("Reason count", 70),
    ):
        _override(trust, field, _WIDTH, width)
    for item in trust["fieldConfig"]["overrides"]:
        if item["matcher"].get("options") in {"Observed", "Assessed at"}:
            item["properties"] = [p for p in item["properties"] if p["id"] != _WIDTH]
    _override(trust, "Reason count", _CELL, {"type": "auto"})
    _override(trust, "Reason count", _HIDDEN, False)
    _override(trust, "Reason count", "noValue", "—")
    _override(trust, "Reason count", "links", [])
    _override(
        trust,
        "Reason count",
        "mappings",
        [{"type": "value", "options": {"0": {"text": "no"}}}],
    )
    _override(trust, "Action", "noValue", "")
    _override(
        trust,
        "Action",
        "links",
        [
            {
                "title": "View trust reasons",
                "url": (
                    "/d/bioetl-control-plane-v1/1-trust?${workflow:queryparam}"
                    "&${pipeline:queryparam}&${run_type:queryparam}"
                    "&${run_id:queryparam}&viewPanel=9418&${__url_time_range}"
                ),
                "includeVars": False,
                "targetBlank": False,
            }
        ],
    )
    if 9451 in panels:
        details = panels[9451]
        _organize_trust_details(details)
        _override(details, "Reason", _CELL, {"type": "auto", "wrapText": True})
        _override(details, "Reason", _INSPECT, True)
    for item in trust["fieldConfig"]["overrides"]:
        _lighten_override_mappings(item)


def _dedupe_width_overrides(panels: dict[int, dict]) -> None:
    # A display-name alias must not reserve the same column's width twice.
    for panel in panels.values():
        width_fields = set()
        for override in panel.get("fieldConfig", {}).get("overrides", []):
            matcher = override.get("matcher", {})
            if matcher.get("id") != "byName":
                continue
            field = str(matcher.get("options", "")).casefold()
            properties = override.get("properties", [])
            if any(prop["id"] == _WIDTH for prop in properties):
                if field in width_fields:
                    override["properties"] = [
                        prop for prop in properties if prop["id"] != _WIDTH
                    ]
                width_fields.add(field)


def _strip_named_widths(panel: dict, names: tuple[str, ...]) -> None:
    for override in panel["fieldConfig"]["overrides"]:
        if override["matcher"].get("options") in names:
            override["properties"] = [
                prop for prop in override["properties"] if prop["id"] != _WIDTH
            ]


def _correct_runtime_evidence_actions(panels: dict[int, dict]) -> None:
    """Explain saved evidence without changing its verdict or raw report."""
    if 9451 in panels:
        reasons = {
            "execution_success": "Processing completed",
            "standalone_pipeline": "Standalone pipeline; no workflow applies",
            "run_dq_threshold_evaluation": "Saved data-quality threshold evaluation",
            "run_preflight_provider_observation": "Saved provider preflight check",
            "run_gold_schema_validation": "Saved Gold schema validation",
        }
        _override(
            panels[9451],
            "Reason",
            "mappings",
            [{"type": "value", "options": {
                code: {"text": label} for code, label in reasons.items()
            }}],
        )
    if 9403 in panels:
        panels[9403]["fieldConfig"]["defaults"]["links"] = [{
            "title": "Open saved run report",
            "url": (
                "/api/datasources/proxy/uid/bioetl-ops-http/ops/observability/"
                "pipeline-run-report-artifact?pipeline=${pipeline:percentencode}"
                "&run_id=${run_id:percentencode}&format=pipeline_run_report_json"
            ),
            "targetBlank": True,
        }]


def _correct_runtime(uid: object, panels: dict[int, dict]) -> None:
    if uid == "bioetl-runtime":
        _correct_runtime_evidence_actions(panels)
    if uid == "bioetl-runtime" and 9998 in panels:
        # Reserve room for long verdicts; evidence uses the remaining panel width.
        _override(panels[9998], "Result", _WIDTH, 125)
        _override(panels[9998], "Status", _WIDTH, 125)
    if uid != "bioetl-runtime" or 2460 not in panels:
        return
    coverage = panels[9102]
    merged = (
        'label_replace(min(bioetl_rt_stage_ratio{pipeline=~"$pipeline",run_type=~"$run_type"}) '
        'or on() vector(-1),"k","stages","","") or '
        'label_replace(bioetl_runtime_trust_gap_active_10m,"k","quality","","")'
    )
    kept = [t for t in coverage["targets"] if t.get("refId") not in {"B", "D"}]
    kept.append(
        {
            "expr": merged,
            "refId": "B",
            "instant": True,
            "legendFormat": "{{k}}",
        }
    )
    coverage["targets"] = sorted(kept, key=lambda item: str(item.get("refId")))
    _override(coverage, "stages", "displayName", "Expected stage signals")
    _override(coverage, "quality", "displayName", "Monitoring quality (10m)")
    _override(
        coverage,
        "quality",
        "mappings",
        [
            {
                "type": "value",
                "options": {
                    "0": {"text": "OK", "color": "green"},
                    "1": {"text": "DEGRADED", "color": "orange"},
                },
            }
        ],
    )
    coverage["description"] = (
        "CURRENT · Endpoint is scrape availability; expected stage signals measure presence, not freshness. "
        "Rule age is evaluation age, not event freshness. Monitoring quality (10m) reports missing telemetry, "
        "rule failures or missed evaluations in the last 10 minutes, including recovered events. "
        "DEGRADED is a monitoring warning, not proof that the selected pipeline has incomplete stage evidence."
    )
    _override(panels[243], "Expected", "noValue", "N/A: not declared")
    _override(panels[243], "Expected", _WIDTH, 150)
    _override(panels[243], "Observed Records", _WIDTH, 150)
    stage_panel = panels[2460]
    for field in ("Backlog", "Lag", "Throughput"):
        _override(stage_panel, field, _WIDTH, 100)
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
            _CELL,
            {"type": "auto", "wrapText": True},
        )
    _override(panels[9101], "severity", _WIDTH, 110)
    _override(panels[9101], "Action", _WIDTH, 110)
    _override(panels[9101], "action_target", _INSPECT, False)
    _override(panels[9101], "Count", _HIDDEN, True)
    for transform in panels[9101].get("transformations", []):
        if transform["id"] == "organize":
            transform["options"]["excludeByName"].update(pipeline=False, run_type=False)
    for field in ("pipeline", "run_type"):
        _override(panels[9101], field, _HIDDEN, True)
    _override(
        panels[9101],
        "action_target",
        "links",
        [
            {
                "title": "Open blocker diagnostics",
                "url": "/d/${__data.fields.action_dashboard_uid}/?${workflow:queryparam}&${__data.fields.action_scope:raw}&var-run_type=${__data.fields.run_type:percentencode}&${run_id:queryparam}&${__url_time_range}",
                "targetBlank": False,
            }
        ],
    )
    _override(
        panels[9101],
        "Reason",
        _CELL,
        {"type": "auto", "wrapText": False},
    )
    _strip_named_widths(panels[9101], ("Status", "Severity", "Pipeline"))
    for target in panels[2460].get("targets", []):
        if "legendFormat" in target:
            target["legendFormat"] = "{{stage}}"


def _dq_processed_records(panel: dict) -> None:
    """Join saved stage inputs to the existing outcome accounting rows."""
    names = ["01 bronze_records", "02 silver_valid_records", "03 silver_filtered_out_records", "04 silver_quarantined_records", "05 silver_skipped_records", "06 silver_deduplicated_records", "07 gold_written_records", "08 gold_excluded_by_contract_records", "09 gold_quarantined_records", "10 gold_skipped_records", "11 gold_deduplicated_records"]
    names = [name for name in names if "_skipped_" not in name]
    parameters = "[" + ",".join("'" + name + "'" for name in names) + "]"
    expression = (
        "($f := funnel; $map(" + parameters + ", function($p) { "
        "($layerName := $contains($p, 'bronze') ? 'bronze' : ($contains($p, 'silver') ? 'silver' : 'gold'); "
        "{'parameter': $p, 'count in': $f[stage_id = $layerName].records_in}) }))"
    )
    panel["targets"] = [t for t in panel["targets"] if t.get("refId") != "StageInput"]
    outcome_expression = (
        "$map(rows[parameter != '05 silver_skipped_records' and "
        "parameter != '10 gold_skipped_records'], function($r) {"
        "$merge([$r, {'percentage': $contains($string($r.percentage), '%') ? "
        "$formatNumber($number($substringBefore($r.percentage, '%')), '0.0') & '%' : $r.percentage}])})"
    )
    panel["targets"][0].update(parser="uql", uql='parse-json | jsonata "' + outcome_expression + '"')
    panel["targets"].append({"refId": "StageInput", "type": "json", "source": "url", "parser": "uql", "format": "table", "url": "/ops/observability/pipeline-run-report?pipeline=${pipeline}&run_id=${run_id}", "url_options": {"method": "GET", "data": ""}, "uql": 'parse-json | jsonata "' + expression + '"'})
    panel["transformations"] = [
        {"id": "joinByField", "options": {"byField": "parameter", "mode": "outer"}},
        {"id": "organize", "options": {"excludeByName": {"row_status": True}, "indexByName": {"parameter": 0, "count in": 1, "count in StageInput": 1, "value": 2, "value A": 2, "percentage": 3, "percentage A": 3}, "renameByName": {"value": "count out", "value A": "count out", "count in StageInput": "count in", "percentage A": "percentage"}}},
    ]
    for override in panel["fieldConfig"]["overrides"]:
        for prop in override["properties"]:
            if prop["id"] == "displayName" and prop["value"] == "count":
                prop["value"] = "count out"
            if prop["id"] == _CELL:
                prop["value"]["wrapText"] = False
    for field in ("count in", "count out"):
        _override(panel, field, _WIDTH, 90)
        _override(panel, field, "custom.align", "right")
    for field in ("value", "value A", "count", "count out"):
        _override(panel, field, _WIDTH, 100)
    _override(panel, "percentage", _WIDTH, 100)
    _override(panel, "percentage", "displayName", "percentage")
    _override(panel, "percentage A", "displayName", "percentage")
    for field in ("value", "value A", "count", "count in", "count out", "percentage", "percentage A"):
        _override(panel, field, "noValue", "N/A")
        _override(panel, field, "mappings", [{"type": "value", "options": {"UNKNOWN": {"text": "N/A", "color": "gray"}, "No data": {"text": "N/A", "color": "gray"}}}])
    panel["options"]["footer"]["enablePagination"] = False
    panel["options"]["cellHeight"] = "sm"
    panel["gridPos"]["h"] = 13
    panel["description"] = "SELECTED RUN · count in is the saved input of each stage, repeated across its outcome rows. count out is the outcome count. Percentages retain their original denominator and display one decimal place. N/A means the value was not recorded. Skipped outcomes are hidden."


def _correct_dq(uid: object, panels: dict[int, dict]) -> None:
    if uid == "bioetl-dq-v2" and 9403 in panels:
        _dq_processed_records(panels[9403])
        summary = panels[9406]
        summary["transformations"] = [
            {"id": "limit", "options": {"limitField": 1}},
            {"id": "filterFieldsByName", "options": {"include": {"names": ["verdict"]}}},
            {"id": "organize", "options": {"renameByName": {"verdict": "Overall verdict"}}},
        ]
        summary["options"]["cellHeight"] = "sm"
        summary["fieldConfig"]["defaults"].setdefault("custom", {}).update(wrapText=False, inspect=True)
        for field in ("Result", "Status", "Trust", "Reason"):
            _override(summary, field, "custom.wrapText", False)
            _override(summary, field, _CELL, {"type": "auto", "wrapText": False})
    if uid != "bioetl-dq-v2" or 155 not in panels:
        return
    panels[10]["fieldConfig"]["defaults"]["noValue"] = (
        "No anomaly samples in range; telemetry may be absent"
    )
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


def _correct_overview(uid: object, panels: dict[int, dict]) -> None:
    if uid != "bioetl-overview-v2" or 215 not in panels:
        return
    _override(panels[215], "Action", _WIDTH, 150)


def _correct_run_explorer(uid: object, panels: dict[int, dict]) -> None:
    if uid != "bioetl-run-explorer-v1" or 3010 not in panels:
        return
    _override(
        panels[3010],
        "Pipeline",
        _CELL,
        {"type": "auto", "wrapText": False},
    )
    # Processing replaced Status; Severity is not a field in this table.
    # Keep presentation on the visible field, without reserving phantom widths.
    overrides = panels[3010]["fieldConfig"]["overrides"]
    status = next(
        (item for item in overrides if item["matcher"].get("options") == "Status"),
        None,
    )
    if status is not None:
        for prop in status["properties"]:
            _override(panels[3010], "Processing", prop["id"], prop["value"])
    overrides[:] = [
        item
        for item in overrides
        if item["matcher"].get("options") not in ("Status", "Severity")
    ]
    panels[3010]["options"].setdefault("footer", {}).update(
        enablePagination=False, countRows=False
    )
    _override(panels[3010], "Report", _WIDTH, 110)
    _override(panels[3010], "Replay readiness", _WIDTH, 50)
    _override(
        panels[3010],
        "Replay readiness",
        "links",
        [
            {
                "title": "Open 1. Trust",
                "url": "/d/bioetl-control-plane-v1/1-trust?var-workflow=${__data.fields.workflow_scope}&var-pipeline=${__data.fields.Pipeline:percentencode}&var-run_type=${__data.fields.run_type:percentencode}&var-run_id=${__data.fields.Run:percentencode}&${__url_time_range}",
                "includeVars": False,
            }
        ],
    )
    _override(
        panels[3010],
        "Workflow",
        _CELL,
        {"type": "auto", "wrapText": False},
    )
    _override(
        panels[3010],
        "Workflow",
        "mappings",
        [
            {
                "type": "value",
                "options": {"— (no workflow data)": {"text": "No workflow"}},
            }
        ],
    )


def _include_action_scope(routed_panel: dict) -> None:
    for transform in routed_panel.get("transformations", []):
        options = transform.get("options", {})
        if transform["id"] == "organize":
            options.setdefault("excludeByName", {})["action_scope"] = False
        elif transform["id"] == "filterFieldsByName":
            names = options.get("include", {}).get("names", [])
            if names and "action_scope" not in names:
                names.append("action_scope")


def _correct_routed_action_scope(uid: object, panels: dict[int, dict]) -> None:
    routed_panel_id = {
        "bioetl-overview-v2": 215,
        "bioetl-runtime": 9101,
        "bioetl-dq-v2": 9102,
    }.get(uid)
    if routed_panel_id not in panels:
        return
    routed_panel = panels[routed_panel_id]
    _include_action_scope(routed_panel)
    _override(routed_panel, "action_scope", _HIDDEN, True)


def apply_corrections(payload: dict) -> None:
    """Apply idempotent source-level corrections before dashboard serialization."""
    uid = payload.get("uid")
    panels = {p["id"]: p for p in _panels(payload.get("panels", []))}
    _correct_action_panel(uid, panels)
    _apply_per_panel_corrections(panels)
    _stamp_scope_copy(uid, panels)
    _correct_incident(uid, panels)
    _correct_provider(uid, panels)
    _correct_control_plane(uid, panels)
    _apply_table_targets(uid, panels)
    _correct_control_plane_trust(uid, panels)
    _dedupe_width_overrides(panels)
    _correct_runtime(uid, panels)
    _correct_dq(uid, panels)
    _correct_overview(uid, panels)
    _correct_run_explorer(uid, panels)
    _correct_routed_action_scope(uid, panels)
