"""Keep CURRENT workflow selection separate from persisted selected-run evidence."""

from __future__ import annotations

from copy import deepcopy

_SCOPE = 'workflow=~"$workflow",pipeline=~"$pipeline",run_type=~"$run_type"'
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


def apply_workflow_scope(payload: dict) -> None:
    """Apply scoped queries after general dashboard corrections; remain idempotent."""
    if payload.get("uid") not in {"bioetl-overview-v2", "bioetl-incident-v1"}:
        return
    panels = list(_walk(payload["panels"]))
    if not any(
        p.get("title") in {"Monitor Scope Health", "Monitor Scope Status"}
        for p in panels
    ):
        return
    for panel in panels:
        if panel.get("type") == "text" and panel.get("id") in {99, 9400}:
            suffix = (
                "GLOBAL tables below cover all pipelines; suspects are not verified causes."
                if payload["uid"] == "bioetl-incident-v1"
                else "Open First Action; VERIFY means evidence is missing. SELECTED RUN is persisted history."
            )
            panel["options"]["content"] = (
                '<div style="padding:4px 10px;border-left:4px solid #6b7280;'
                'font-size:16px;line-height:1.2;overflow-wrap:anywhere">'
                "CURRENT card: ${workflow:text} / ${pipeline:text} / ${run_type:text}.<br>"
                + suffix
                + "</div>"
            )
        if panel.get("title") in {"Monitor Scope Health", "Monitor Scope Status"}:
            panel["targets"] = [
                {
                    "refId": "A",
                    "instant": True,
                    "expr": f"max(bioetl_workflow_scope_priority{{{_SCOPE}}})",
                }
            ]
            panel["description"] = (
                "CURRENT · Selected workflow, pipeline and run type; not Selected Run. Inspect Current Workflow Evidence below for the source and publication clock."
            )
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
            panel.setdefault("options", {})["cellHeight"] = "lg"
            for override in panel.get("fieldConfig", {}).get("overrides", []):
                for prop in override.get("properties", []):
                    if prop["id"] == "custom.width":
                        field = override["matcher"].get("options")
                        if field in {"Priority", "Action"}:
                            prop["value"] = 90 if field == "Priority" else 120
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
    source = next(p for p in panels if p.get("type") == "table")
    _evidence_row(payload, source)
