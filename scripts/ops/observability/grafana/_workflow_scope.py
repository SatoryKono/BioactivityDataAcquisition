"""Keep CURRENT workflow selection separate from persisted selected-run evidence."""

from __future__ import annotations

from copy import deepcopy

_SCOPE = 'workflow=~"$workflow",pipeline=~"$pipeline",run_type=~"$run_type"'
_FIRST_ACTION_EXPR = (
    'bioetl_first_action{workflow=~"$workflow",pipeline=~"$pipeline",run_type=~"$run_type"}>0'
    ' or on() label_replace(label_replace(bioetl_fa_gap,"pipeline","$pipeline","",""),'
    '"workflow","$workflow","","")'
)
_ACTION_HREF = "${__data.fields.action_href:raw}"
# Run ID is always selected on Overview. These panels do not assess that run.
_NON_RUN_PANEL_IDS = frozenset(
    {
        214,
        215,
        9600,
        9601,
        9030,
        9031,
        9018,
        9019,
        9020,
        9009,
        9010,
        9011,
        9015,
        9012,
        9006,
        9003,
        9004,
        9007,
        9005,
        9013,
        9021,
        30215,
        20215,
        9700,
        9701,
    }
)
_FIRST_ACTION_DESCRIPTION = (
    "CURRENT · Each row keeps pipeline and run type. Workflow All uses workflow series plus "
    "standalone pipelines that have no workflow membership. A concrete workflow does not borrow "
    "another workflow or a pipeline fallback. VERIFY means required telemetry is missing, "
    "publication evidence is stale, or the selected scope has no current series. "
    "No action required means every applicable check is confirmed. "
    "REVIEW, HIGH, URGENT, and CRIT are confirmed problems. "
    "Run ID does not change CURRENT. A datasource error stays a query error. "
    "UNKNOWN remains a health state on Monitor Scope Health, not a First Action priority."
)
_PRIORITIES = {
    "0": {"text": "OK", "color": "green"},
    "1": {"text": "UNKNOWN", "color": "#555555"},
    "2": {"text": "WARN", "color": "orange"},
    "3": {"text": "CRIT", "color": "red"},
}


def _walk(panels: list[dict]):
    for panel in panels:
        yield panel
        yield from _walk(panel.get("panels", []))


def _evidence_row(payload: dict, source: dict) -> None:
    panels = payload["panels"]
    panels[:] = [p for p in panels if p["id"] != 9700]
    y = max(p["gridPos"]["y"] + p["gridPos"]["h"] for p in panels)
    evidence = deepcopy(source)
    evidence.update(
        id=9701,
        title="Review Current Workflow Evidence",
        gridPos={"x": 0, "y": y + 1, "w": 24, "h": 9},
    )
    evidence["description"] = (
        "CURRENT · Workflow/pipeline/run-type scope, independent of Selected Run. "
        "Published at is the gateway publication clock, not the Prometheus evaluation clock. "
        "Retained publications do not expire after 15 minutes. "
        "Reason unavailable means no diagnostic cause is exposed by this metric."
    )
    evidence["datasource"] = {"type": "prometheus", "uid": "prometheus"}
    evidence["targets"] = [
        {
            "refId": "A",
            "instant": True,
            "format": "table",
            "expr": 'label_replace(max by(workflow)(bioetl_workflow_scope_input_status{input="workflow",'
            + _SCOPE
            + '}),"reason","Reason unavailable","","")',
        },
        {
            "refId": "B",
            "instant": True,
            "format": "table",
            "expr": "bioetl_workflow_scope_published_seconds * on(workflow) group by(workflow)(bioetl_workflow_scope_universe{"
            + _SCOPE
            + "}) * 1000",
        },
    ]
    evidence["transformations"] = [
        {"id": "joinByField", "options": {"byField": "workflow", "mode": "outer"}},
        {
            "id": "filterFieldsByName",
            "options": {
                "include": {
                    "names": [
                        "workflow",
                        "pipeline",
                        "run_type",
                        "Value #A",
                        "Value #B",
                        "reason",
                    ]
                }
            },
        },
        {
            "id": "organize",
            "options": {
                "renameByName": {
                    "workflow": "Workflow",
                    "pipeline": "Pipeline",
                    "run_type": "Run Type",
                    "Value #A": "Status",
                    "Value #B": "Published at",
                    "reason": "Reason",
                }
            },
        },
    ]
    evidence["fieldConfig"] = {
        "defaults": {
            "custom": {
                "wrapText": True,
                "inspect": True,
                "cellOptions": {"type": "auto", "wrapText": True},
            },
            "noValue": "UNKNOWN",
        },
        "overrides": [
            {
                "matcher": {"id": "byName", "options": "Status"},
                "properties": [
                    {
                        "id": "mappings",
                        "value": [
                            {
                                "type": "value",
                                "options": {
                                    "0": {"text": "OK"},
                                    "1": {"text": "WARN"},
                                    "2": {"text": "CRIT"},
                                    "3": {"text": "UNKNOWN"},
                                },
                            }
                        ],
                    }
                ],
            },
            {
                "matcher": {"id": "byName", "options": "Published at"},
                "properties": [{"id": "unit", "value": "time:YYYY-MM-DD HH:mm"}],
            },
        ],
    }
    evidence["options"] = {
        "showHeader": True,
        "cellHeight": "sm",
        "footer": {"show": False},
    }
    panels.append(
        {
            "id": 9700,
            "type": "row",
            "title": "Inspect Current Workflow Evidence",
            "collapsed": True,
            "gridPos": {"x": 0, "y": y, "w": 24, "h": 1},
            "panels": [evidence],
        }
    )


def _mapping_options(panel: dict, field: str | None) -> list[dict]:
    if field is None:
        mappings = panel["fieldConfig"]["defaults"].get("mappings", [])
    else:
        mappings = []
        for override in panel.get("fieldConfig", {}).get("overrides", []):
            if override.get("matcher", {}).get("options") != field:
                continue
            for prop in override.get("properties", []):
                if prop.get("id") == "mappings":
                    mappings.extend(prop.get("value", []))
    return [
        mapping["options"]
        for mapping in mappings
        if mapping.get("type") == "value" and isinstance(mapping.get("options"), dict)
    ]


def _apply_first_action_panel(panel: dict) -> None:
    """Point Review First Action at scoped routes and VERIFY, not UNKNOWN."""
    for target in panel.get("targets", []):
        if "expr" in target:
            target["expr"] = _FIRST_ACTION_EXPR
    panel["description"] = _FIRST_ACTION_DESCRIPTION
    panel["fieldConfig"]["defaults"]["noValue"] = "Selected scope has no current evidence"
    for options in _mapping_options(panel, None):
        options.pop("0", None)
        options.pop("5", None)
        options["1"] = {"text": "—", "color": "text"}
        options["15"] = {"text": "VERIFY", "color": "#8e8e8e"}
    for options in _mapping_options(panel, "action_target"):
        options["none"] = {"text": "—", "color": "text"}
        options["inspect_evidence"] = {"text": "Inspect evidence", "color": "text"}
        options.pop("no_route", None)
        options.pop("monitor", None)
    for options in _mapping_options(panel, "action_reason"):
        options["no_action_required"] = {"text": "No action required"}
        options["selected_scope_not_present"] = {
            "text": "Selected scope has no current evidence"
        }
        options["workflow_evidence_stale"] = {"text": "Current evidence is stale"}
        options.pop("no_recent_activity_or_unknown_state", None)
        for domain, label in (
            ("runtime", "Runtime"),
            ("control_plane", "Trust"),
            ("gold", "Gold"),
            ("dq", "DQ"),
            ("provider", "Provider"),
            ("workflow", "Workflow"),
        ):
            options[f"{domain}_evidence_missing"] = {"text": f"{label}: telemetry missing"}
    for transform in panel.get("transformations", []):
        if transform.get("id") != "sortBy":
            continue
        transform["options"]["sort"] = [
            {"field": "Value", "desc": True},
            {"field": "action_reason", "desc": False},
        ]
    overrides = panel["fieldConfig"]["overrides"]
    for override in overrides:
        if override.get("matcher", {}).get("options") != "run_type":
            continue
        override["properties"] = [
            prop
            for prop in override.get("properties", [])
            if not (prop.get("id") == "custom.hidden" and prop.get("value") is True)
        ]
    if not any(item.get("matcher", {}).get("options") == "Workflow" for item in overrides):
        overrides.append(
            {"matcher": {"id": "byName", "options": "Workflow"}, "properties": []}
        )
    for override in overrides:
        if override.get("matcher", {}).get("options") != "Workflow":
            continue
        props = override.setdefault("properties", [])
        if not any(prop.get("id") == "mappings" for prop in props):
            props.append(
                {
                    "id": "mappings",
                    "value": [
                        {
                            "type": "value",
                            "options": {"__standalone__": {"text": "—"}},
                        }
                    ],
                }
            )
        for prop in props:
            if prop.get("id") != "links":
                continue
            for link in prop.get("value", []):
                if "action_scope" in link.get("url", "") or "action_href" in link.get(
                    "url", ""
                ):
                    link["url"] = _ACTION_HREF
    for override in overrides:
        if override.get("matcher", {}).get("options") != "action_target":
            continue
        for prop in override.get("properties", []):
            if prop.get("id") != "links":
                continue
            for link in prop.get("value", []):
                link["url"] = _ACTION_HREF


def _without_non_run_panels(panels: list[dict]) -> list[dict]:
    kept: list[dict] = []
    for panel in panels:
        if panel.get("id") in _NON_RUN_PANEL_IDS:
            continue
        nested = panel.get("panels")
        if isinstance(nested, list):
            panel["panels"] = _without_non_run_panels(nested)
        if panel.get("type") == "row" and not panel.get("panels"):
            continue
        kept.append(panel)
    return kept


def _place_selected_run_window(panels: list[dict]) -> None:
    by_id = {panel.get("id"): panel for panel in panels}
    nav = by_id.get(1000)
    y = 0
    if isinstance(nav, dict) and isinstance(nav.get("gridPos"), dict):
        y = int(nav["gridPos"]["y"]) + int(nav["gridPos"]["h"])
    banner = by_id.get(99)
    if isinstance(banner, dict):
        banner["gridPos"] = {"x": 0, "y": y, "w": 24, "h": 3}
        y += 3
    for panel_id, x_pos in ((9603, 0), (9002, 12)):
        panel = by_id.get(panel_id)
        if isinstance(panel, dict):
            panel["gridPos"] = {"x": x_pos, "y": y, "w": 12, "h": 6}
    y += 6
    pinned = {1000, 99, 9603, 9002}
    rest = [panel for panel in panels if panel.get("id") not in pinned]
    rest.sort(key=lambda panel: (panel["gridPos"]["y"], panel["gridPos"]["x"]))
    for panel in rest:
        height = int(panel["gridPos"]["h"])
        panel["gridPos"].update(x=0, y=y, w=24, h=height)
        y += height


def _retain_selected_run_overview(payload: dict) -> None:
    """Overview always has a Run ID. Drop panels that do not assess that run."""
    variables = payload.setdefault("templating", {}).setdefault("list", [])
    payload["templating"]["list"] = [
        variable
        for variable in variables
        if variable.get("name") != "overview_fleet"
    ]
    payload["panels"] = _without_non_run_panels(payload.get("panels") or [])
    description = str(payload.get("description") or "")
    note = (
        " Run ID is always selected. This page shows saved evidence for that run. "
        "CURRENT fleet panels and TIME RANGE history are not on Overview."
    )
    if "Run ID is always selected" not in description:
        payload["description"] = description.rstrip() + note
    for panel in payload["panels"]:
        if panel.get("id") != 99:
            continue
        panel["options"]["content"] = (
            '<div style="padding:4px 10px;border-left:4px solid #6b7280;'
            'font-size:16px;line-height:1.2;overflow-wrap:anywhere">'
            "SELECTED RUN · ${pipeline:text} / ${run_type:text} / ${run_id}. "
            "This page assesses that run only. "
            "UNKNOWN means saved evidence is missing."
            "</div>"
        )
        panel["description"] = (
            "SELECTED RUN · Saved evidence for the selected Run ID. "
            "UNKNOWN means the saved assessment is missing, not a healthy empty run. "
            "A request failure is QUERY ERROR."
        )
    _place_selected_run_window(payload["panels"])
    domains = next(
        panel for panel in payload["panels"] if panel.get("id") == 9002
    )
    handoff = domains.get("fieldConfig", {}).get("defaults", {}).get("links") or []
    domains["links"] = [dict(link) for link in handoff]


def apply_workflow_scope(payload: dict) -> None:
    """Apply scoped queries after general dashboard corrections; remain idempotent."""
    if payload.get("uid") not in {"bioetl-overview-v2", "bioetl-incident-v1"}:
        return
    panels = list(_walk(payload["panels"]))
    has_scope_card = any(
        p.get("title") in {"Monitor Scope Health", "Monitor Scope Status"}
        for p in panels
    )
    if not has_scope_card and payload.get("uid") != "bioetl-overview-v2":
        return
    if not has_scope_card:
        _retain_selected_run_overview(payload)
        return
    for panel in panels:
        if panel.get("type") == "text" and panel.get("id") in {99, 9400}:
            suffix = (
                "GLOBAL tables below cover all pipelines; suspects are not verified causes. VALID_EMPTY is an empty suspect list, not a healthy fleet."
                if payload["uid"] == "bioetl-incident-v1"
                else (
                    "Open First Action; VERIFY means evidence is missing. "
                    "SELECTED RUN is persisted history. "
                    "A concrete Run ID hides this fleet card."
                )
            )
            panel["options"]["content"] = (
                '<div style="padding:4px 10px;border-left:4px solid #6b7280;'
                'font-size:16px;line-height:1.2;overflow-wrap:anywhere">'
                "CURRENT: ${workflow:text} / ${pipeline:text} / ${run_type:text}; Run ID does not filter this card.<br>"
                + suffix
                + "</div>"
            )
        if panel.get("title") in {"Monitor Scope Health", "Monitor Scope Status"}:
            panel["targets"] = [
                {
                    "refId": "A",
                    "instant": True,
                    "expr": f"topk(1, bioetl_workflow_scope_priority_by_input{{{_SCOPE}}})",
                    "legendFormat": "{{workflow}} · {{input}}",
                }
            ]
            panel["description"] = (
                "CURRENT · Worst domain in the selected workflow/pipeline/run-type scope; Run ID does not filter this card. Mapping: 0=OK, 1=UNKNOWN, 2=WARN, 3=CRIT. The label identifies one highest-priority workflow and domain (ties may exist). Open the card for workflow evidence and its publication clock; a workflow-wide failure does not prove this pipeline failed."
            )
            panel["options"]["textMode"] = "value_and_name"
            panel["options"]["text"] = {"valueSize": 20, "titleSize": 12}
            defaults = panel["fieldConfig"]["defaults"]
            defaults.pop("displayName", None)
            defaults["links"] = [
                {
                    "title": "Inspect current workflow evidence and publication time",
                    "url": "/d/"
                    + payload["uid"]
                    + "/?viewPanel=9701&var-workflow=${__field.labels.workflow:percentencode}&${pipeline:queryparam}&${run_type:queryparam}&${run_id:queryparam}&${__url_time_range}",
                    "targetBlank": False,
                }
            ]
            panel["fieldConfig"]["defaults"]["mappings"] = [
                {"type": "value", "options": deepcopy(_PRIORITIES)},
                {
                    "type": "special",
                    "options": {"match": "null", "result": _PRIORITIES["1"]},
                },
            ]
        for target in panel.get("targets", []):
            if "bioetl_l0_next_action_route{" in target.get("expr", ""):
                target["expr"] = target["expr"].replace(
                    "bioetl_l0_next_action_route{",
                    'bioetl_workflow_scope_action{workflow=~"$workflow",',
                )
        if panel.get("id") in {215, 20215}:
            for mapping in panel["fieldConfig"]["defaults"].get("mappings", []):
                if mapping.get("type") == "value":
                    mapping["options"]["60"] = {"text": "CRIT", "color": "red"}
            panel.setdefault("options", {})["cellHeight"] = "lg"
            for override in panel.get("fieldConfig", {}).get("overrides", []):
                if override["matcher"].get("options") == "Priority":
                    # Full-action navigation remains in the panel header; a
                    # duplicate link reserves space and clips UNKNOWN.
                    override["properties"] = [
                        p
                        for p in override["properties"]
                        if p["id"] not in {"links", "custom.inspect"}
                    ]
                    override["properties"].append(
                        {"id": "custom.inspect", "value": False}
                    )
                for prop in override.get("properties", []):
                    if (
                        override["matcher"].get("options") == "action_target"
                        and prop["id"] == "mappings"
                    ):
                        for mapping in prop["value"]:
                            if mapping.get("type") == "value":
                                for target in ("runtime", "workflow"):
                                    mapping["options"][target]["text"] = "Diagnose"
                    if prop["id"] == "custom.width":
                        field = override["matcher"].get("options")
                        if field in {"Priority", "Action"}:
                            prop["value"] = 100 if field == "Priority" else 110
                    if (
                        override["matcher"].get("options") == "action_reason"
                        and prop["id"] == "mappings"
                    ):
                        for mapping in prop["value"]:
                            if mapping.get("type") == "value":
                                for domain, label in (
                                    ("runtime", "runtime"),
                                    ("control_plane", "Trust"),
                                    ("gold", "Gold"),
                                    ("dq", "DQ"),
                                    ("provider", "provider"),
                                    ("workflow", "workflow"),
                                ):
                                    mapping["options"][f"{domain}_evidence_missing"] = {
                                        "text": f"{label.capitalize()}: no evidence"
                                    }
                                mapping["options"]["provider_scope_degradation"] = {
                                    "text": "Provider degraded"
                                }
                                mapping["options"]["workflow_scope_critical"] = {
                                    "text": "Workflow CRIT"
                                }
                    if prop["id"] == "links":
                        for link in prop["value"]:
                            if "${__data.fields.action_scope" in link.get("url", ""):
                                link["url"] = link["url"].replace(
                                    "${workflow:queryparam}",
                                    "var-workflow=${__data.fields.Workflow:percentencode}",
                                )
            for transform in panel.get("transformations", []):
                if transform["id"] == "organize":
                    opts = transform["options"]
                    opts.setdefault("excludeByName", {})["workflow"] = False
                    opts.setdefault("renameByName", {})["workflow"] = "Workflow"
                    # Pipeline is already visible in the selector; identify the
                    # workflow responsible for each CURRENT action instead.
                    opts["excludeByName"]["pipeline"] = False
                    order = opts.setdefault("indexByName", {})
                    order["workflow"] = order.get("pipeline", 1)
            overrides = panel["fieldConfig"]["overrides"]
            pipeline = next(
                (o for o in overrides if o["matcher"].get("options") == "Pipeline"),
                None,
            )
            if pipeline is None:
                pipeline = {
                    "matcher": {"id": "byName", "options": "Pipeline"},
                    "properties": [],
                }
                overrides.append(pipeline)
            pipeline["properties"] = [
                p for p in pipeline["properties"] if p["id"] != "custom.hidden"
            ]
            pipeline["properties"].append({"id": "custom.hidden", "value": True})
            overrides[:] = [
                o for o in overrides if o["matcher"].get("options") != "Workflow"
            ]
            overrides.append(
                {
                    "matcher": {"id": "byName", "options": "Workflow"},
                    "properties": [
                        {
                            "id": "custom.cellOptions",
                            "value": {"type": "auto", "wrapText": True},
                        },
                        {"id": "custom.wrapText", "value": True},
                        {"id": "custom.inspect", "value": True},
                    ],
                }
            )
            _apply_first_action_panel(panel)
    if payload.get("uid") == "bioetl-overview-v2":
        _retain_selected_run_overview(payload)
        return
    source = next(p for p in panels if p.get("type") == "table")
    _evidence_row(payload, source)
