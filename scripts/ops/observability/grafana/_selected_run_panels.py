"""Canonical saved-run summaries; current readiness remains a separate telemetry view."""

from __future__ import annotations

from copy import deepcopy

STATUS_URL = "/ops/observability/selected-run-status?pipeline=${pipeline}&run_id=${run_id}&run_type=${run_type:csv}&workflow=${workflow:csv}"
DESCRIPTION = (
    "SELECTED RUN · Saved evidence for this Run ID. Missing checks are INCOMPLETE; "
    "missing selection is SELECT RUN; request failure is QUERY ERROR. "
    "N/A means explicitly inapplicable. VALID EMPTY is an empty successful query. "
    "This saved verdict does not authorize replay."
)


def _panel(
    panel_id: int, title: str, grid: dict[str, int], *, domains: bool
) -> dict[str, object]:
    fields = (
        ["domain", "verdict"]
        if domains
        else [
            "execution_state",
            "verdict",
            "evidence_completeness",
            "rules_version",
        ]
    )
    return {
        "id": panel_id,
        "type": "table",
        "title": title,
        "gridPos": grid,
        "datasource": "BioETL Ops HTTP",
        "description": DESCRIPTION,
        "options": {"showHeader": True, "cellHeight": "sm", "footer": {"show": False}},
        "fieldConfig": {
            "defaults": {
                "noValue": "UNKNOWN",
                "unit": "none",
                "custom": {
                    "align": "left",
                    "cellOptions": {"type": "auto", "wrapText": False},
                    "inspect": True,
                },
            },
            "overrides": [],
        },
        "targets": [
            {
                "refId": "A",
                "type": "json",
                "source": "url",
                "parser": "backend",
                "format": "table",
                "root_selector": "domains" if domains else "summary",
                "url": STATUS_URL,
                "url_options": {"method": "GET", "data": ""},
            }
        ],
        "transformations": [
            {"id": "limit", "options": {"limitField": 6 if domains else 1}},
            {"id": "filterFieldsByName", "options": {"include": {"names": fields}}},
            {
                "id": "organize",
                "options": {
                    "indexByName": {name: index for index, name in enumerate(fields)},
                    "renameByName": {
                        "domain": "Domain",
                        "verdict": "Status",
                        "execution_state": "Result",
                        "evidence_completeness": "Evidence",
                        "rules_version": "Rules",
                    },
                },
            },
        ],
        "links": [],
    }


def _detail_fields(panel: dict, fields: list[str]) -> None:
    """Show evidence fields explicitly instead of exposing the entire API envelope."""
    if "completed_at" in fields:
        panel["transformations"].insert(
            0,
            {
                "id": "convertFieldType",
                "options": {
                    "conversions": [
                        {"targetField": "completed_at", "destinationType": "time"}
                    ]
                },
            },
        )
        panel["fieldConfig"]["overrides"].append(
            {
                "matcher": {"id": "byName", "options": "Completed"},
                "properties": [
                    {"id": "unit", "value": "time:YYYY-MM-DD HH:mm"},
                    {"id": "custom.width", "value": 175},
                ],
            }
        )
    for transform in panel["transformations"]:
        if transform["id"] == "filterFieldsByName":
            transform["options"]["include"]["names"] = fields
        if transform["id"] == "organize":
            transform["options"]["indexByName"] = {
                name: index for index, name in enumerate(fields)
            }
            transform["options"]["renameByName"].update(
                {
                    "reason": "Reason",
                    "action": "Action",
                    "evidence_ref": "Evidence reference",
                    "pipeline": "Pipeline",
                    "run_id": "Run ID",
                    "completed_at": "Completed",
                    "revision": "Revision",
                }
            )
    panel["fieldConfig"]["defaults"]["custom"]["cellOptions"]["wrapText"] = True
    panel["fieldConfig"]["defaults"]["custom"]["minWidth"] = 50
    panel["options"]["cellHeight"] = "lg"
    panel["options"]["footer"]["enablePagination"] = True


def _walk_panels(panels):
    for panel in panels:
        if isinstance(panel, dict):
            yield panel
            yield from _walk_panels(panel.get("panels", []))


SELECTED_RUN_STATUS_TITLE = "Review Selected Run Status"
_OVERVIEW_UID = "bioetl-overview-v2"
_CONTROL_PLANE_UID = "bioetl-control-plane-v1"
_CURRENT_PREFIX = "CURRENT · Fresh pipeline/run_type telemetry only. "


def _stamp_control_plane_copy(panel: dict[str, object], uid: object) -> None:
    if uid != _CONTROL_PLANE_UID:
        return
    if panel.get("id") == 9418:
        for target in panel.get("targets", []):
            target["url"] = STATUS_URL
            target["root_selector"] = "trust"
        panel["description"] = (
            "SELECTED RUN · Processing result is the saved ETL outcome. "
            "Saved trust verdict is the historical Trust assessment and does not "
            "authorize replay. Reason count is the number of saved remarks. "
            "Assessed at is when that assessment was recorded."
        )
    if panel.get("id") == 9403:
        description = str(panel.get("description") or "")
        panel["description"] = description.replace(
            "SELECTED RUN · CURRENT · ", "SELECTED RUN · "
        ).replace("Inspect Recent Runs", "Run Explorer")
    if panel.get("id") == 9421:
        panel["description"] = (
            "SELECTED RUN · Search persisted runs and choose one Run ID. "
            "This table does not score the Run ID already selected on this dashboard."
        )


def _rewrite_selected_run_tables(panel: dict[str, object], uid: object) -> None:
    title = panel.get("title")
    if title == "Review Selected Run Summary":
        panel.update(
            _panel(
                panel["id"],
                SELECTED_RUN_STATUS_TITLE,
                panel["gridPos"],
                domains=False,
            )
        )
    elif title == SELECTED_RUN_STATUS_TITLE:
        panel.update(
            _panel(panel["id"], title, panel["gridPos"], domains=False)
        )
    if uid == _OVERVIEW_UID and panel.get("id") == 9002:
        panel.update(
            _panel(9002, "Review Run Domains", panel["gridPos"], domains=True)
        )


def _preserve_existing_links(
    panel: dict[str, object],
    old_links: object,
    old_data_links: object,
) -> None:
    if panel.get("id") not in {9406, 9603, 9402, 9002} and panel.get(
        "title"
    ) != SELECTED_RUN_STATUS_TITLE:
        return
    panel["links"] = old_links
    panel.setdefault("fieldConfig", {}).setdefault("defaults", {})["links"] = (
        old_data_links
    )


def _stamp_status_links(
    panel: dict[str, object], uid: object, panels: list[object]
) -> None:
    if uid == _OVERVIEW_UID and panel.get("id") == 9002:
        panel["fieldConfig"]["defaults"]["links"] = [
            {
                "title": title,
                "url": next(
                    link["url"]
                    for nav in panels
                    if nav.get("id") == 1000
                    for link in nav["links"]
                    if f"/d/{target}/" in link["url"]
                ),
                "targetBlank": False,
                "includeVars": False,
            }
            for title, target in (
                ("Open Runtime", "bioetl-runtime"),
                ("Open Control Plane", "bioetl-control-plane-v1"),
                ("Open Data Quality", "bioetl-dq-v2"),
                ("Open Provider Health", "bioetl-provider-health-v2"),
            )
        ]
    if panel.get("title") != SELECTED_RUN_STATUS_TITLE:
        return
    panel["fieldConfig"]["defaults"]["links"] = [
        {
            "title": "Open Run Explorer",
            "url": "/d/bioetl-run-explorer-v1/bioetl-run-explorer-v1?${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}&${run_id:queryparam}&${__url_time_range}",
            "targetBlank": False,
            "includeVars": False,
        }
    ]
    if uid == "bioetl-incident-v1":
        panel["fieldConfig"]["defaults"]["links"] += [
            {
                "title": "Check BioETL Ops HTTP health",
                "url": "/api/datasources/proxy/uid/bioetl-ops-http/health/live",
                "targetBlank": True,
            }
        ]


def _stamp_overview_derived_panels(panel: dict[str, object], uid: object) -> None:
    if uid != _OVERVIEW_UID:
        return
    if panel.get("id") == 9603:
        panel["datasource"] = {"type": "datasource", "uid": "-- Dashboard --"}
        panel["targets"] = [{"panelId": 9002, "refId": "A", "withTransforms": False}]
        for transform in panel["transformations"]:
            if transform["id"] == "filterFieldsByName":
                transform["options"]["include"]["names"][1] = "run_verdict"
            if transform["id"] == "organize":
                transform["options"]["indexByName"].pop("verdict")
                transform["options"]["indexByName"]["run_verdict"] = 1
                transform["options"]["renameByName"]["run_verdict"] = "Status"
    if panel.get("id") == 215:
        panel["title"] = "Review First Action"
        panel["description"] = _CURRENT_PREFIX + str(
            panel.get("description", "")
        ).removeprefix(_CURRENT_PREFIX)


def _stage_panel(grid: dict[str, int]) -> dict[str, object]:
    """Saved stage rows for the selected Run ID. They precede domain evidence."""
    return {
        "id": 9460,
        "type": "table",
        "title": "Inspect Selected Run Stages",
        "gridPos": grid,
        "datasource": "BioETL Ops HTTP",
        "description": (
            "SELECTED RUN · Stage rows for this Run ID. "
            "SUCCESS with missing stage evidence stays INCOMPLETE. "
            "A recorded zero stays 0. An unknown count is empty, not 0."
        ),
        "options": {
            "showHeader": True,
            "cellHeight": "sm",
            "footer": {"show": False},
        },
        "fieldConfig": {
            "defaults": {
                "noValue": "UNKNOWN",
                "unit": "none",
                "custom": {
                    "align": "left",
                    "cellOptions": {"type": "auto", "wrapText": False},
                    "inspect": True,
                },
            },
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": "duration_seconds"},
                    "properties": [
                        {"id": "noValue", "value": "Not recorded"},
                        {"id": "unit", "value": "s"},
                    ],
                },
                {
                    "matcher": {"id": "byName", "options": "source"},
                    "properties": [
                        {
                            "id": "mappings",
                            "value": [{"type": "value", "options": {
                                "report.funnel": {"text": "Open report"},
                                "report.stage_timings": {"text": "Open report"},
                            }}],
                        },
                        {
                            "id": "links",
                            "value": [{
                                "title": "Open saved run report (JSON)",
                                "url": "/api/datasources/proxy/uid/bioetl-ops-http/ops/observability/pipeline-run-report-artifact?pipeline=${pipeline:percentencode}&run_id=${run_id:percentencode}&format=pipeline_run_report_json",
                                "targetBlank": True,
                            }],
                        },
                    ],
                },
            ],
        },
        "targets": [
            {
                "refId": "A",
                "type": "json",
                "source": "url",
                "parser": "backend",
                "format": "table",
                "root_selector": "stage_diagnostics",
                "url": STATUS_URL,
                "url_options": {"method": "GET", "data": ""},
            }
        ],
        "transformations": [{"id": "limit", "options": {"limitField": 12}}],
        "links": [],
    }


def _run_duration_panel(grid: dict[str, int]) -> dict[str, object]:
    """Calculate total elapsed time from the selected run's saved timestamps."""
    expression = (
        "($s := summary[0]; $start := $s.started_at ? $toMillis($s.started_at) : null; "
        "$end := $s.completed_at ? $toMillis($s.completed_at) : null; "
        "[{'Run duration': $start != null and $end != null and $end >= $start "
        "? ($end - $start) / 1000 : null}])"
    )
    return {
        "id": 9463,
        "type": "stat",
        "title": "Review Total Run Duration",
        "description": "SELECTED RUN · Completed at minus started at, as in Run Explorer. This is the entire run, not individual stage timing.",
        "gridPos": grid,
        "datasource": "BioETL Ops HTTP",
        "fieldConfig": {"defaults": {"unit": "s", "decimals": 2, "noValue": "Not recorded"}, "overrides": []},
        "options": {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False}, "colorMode": "none", "graphMode": "none", "textMode": "value"},
        "targets": [{"refId": "A", "type": "json", "source": "url", "parser": "uql", "format": "table", "url": STATUS_URL, "url_options": {"method": "GET", "data": ""}, "uql": 'parse-json | jsonata "' + expression + '"'}],
    }


def _append_saved_run_evidence_row(
    panels: list[object], *, include_identity: bool = True, include_duration: bool = False
) -> None:
    panels[:] = [
        panel
        for panel in panels
        if not isinstance(panel, dict) or panel.get("id") != 9450
    ]
    y = max(
        (
            panel.get("gridPos", {}).get("y", 0) + panel.get("gridPos", {}).get("h", 1)
            for panel in panels
        ),
        default=0,
    )
    offset = 3 if include_duration else 0
    stages = _stage_panel({"x": 0, "y": y + 1 + offset, "w": 24, "h": 8})
    details = _panel(
        9451,
        "Inspect Selected Run Domains",
        {"x": 0, "y": y + 9 + offset, "w": 24, "h": 10},
        domains=True,
    )
    _detail_fields(details, ["domain", "verdict", "reason", "action", "evidence_ref"])
    children: list[object] = [stages, details]
    if include_duration:
        children.insert(0, _run_duration_panel({"x": 0, "y": y + 1, "w": 24, "h": 3}))
    if include_identity:
        summary = _panel(
            9452,
            "Inspect Selected Run Identity",
            {"x": 0, "y": y + 19 + offset, "w": 24, "h": 8},
            domains=False,
        )
        _detail_fields(
            summary,
            [
                "pipeline",
                "run_id",
                "completed_at",
                "rules_version",
                "revision",
                "evidence_completeness",
            ],
        )
        children.append(deepcopy(summary))
    else:
        empty = (
            "SELECT RUN if no Run ID is selected. QUERY ERROR if the request failed."
        )
        details["description"] = (
            "SELECTED RUN · Domain reasons for this Run ID. "
            "Open this table from View trust reasons only when the reason count is greater than zero."
        )
        details["fieldConfig"]["defaults"]["noValue"] = empty
        stages["fieldConfig"]["defaults"]["noValue"] = empty
    panels.append(
        {
            "id": 9450,
            "type": "row",
            "title": "Inspect Saved Run Evidence",
            "collapsed": True,
            "description": (
                "Expand for saved stage rows, then domain trust reasons, "
                "for the selected Run ID."
            ),
            "gridPos": {"x": 0, "y": y, "w": 24, "h": 1},
            "panels": children,
        }
    )


_PROVIDER_HEALTH_UID = "bioetl-provider-health-v2"
_DROP_PROVIDER_PANEL_IDS = frozenset(
    {
        9002,
        9401,
        9101,
        9104,
        9107,
        9102,
        9111,
        9112,
        9103,
        9113,
        114,
        106,
        107,
        108,
        109,
        1,
        2,
        7,
        31,
        32,
        102,
        104,
        105,
        110,
        111,
        112,
        113,
        115,
        91,
        9105,
        9106,
        9404,
        9450,
        9451,
        9452,
    }
)


def _without_panel_ids(panels: list[object], dropped: frozenset[int]) -> list[object]:
    kept: list[object] = []
    for panel in panels:
        if not isinstance(panel, dict):
            kept.append(panel)
            continue
        if panel.get("id") in dropped:
            continue
        children = panel.get("panels")
        if isinstance(children, list):
            panel["panels"] = _without_panel_ids(children, dropped)
            if panel.get("type") == "row" and not panel["panels"]:
                continue
        kept.append(panel)
    return kept


def _provider_check_panel(
    panel_id: int,
    title: str,
    grid: dict[str, int],
    fields: list[str],
    *,
    limit: int | None,
) -> dict:
    panel = _panel(panel_id, title, grid, domains=False)
    panel["description"] = (
        "SELECTED RUN · Saved provider check for this Run ID. "
        "PRESENT means applicable saved evidence exists, not that the check passed. "
        "Run ID is always set on this dashboard. A report without a provider id is not OK."
    )
    panel["targets"][0]["root_selector"] = "provider_checks"
    labels = {
        "provider": "Provider",
        "check_result": "Check result",
        "evidence": "Evidence",
        "observed_at": "Observed at",
    }
    transforms = [
        item
        for item in panel["transformations"]
        if not (limit is None and item.get("id") == "limit")
    ]
    for item in transforms:
        if item.get("id") == "limit" and limit is not None:
            item["options"]["limitField"] = limit
        if item.get("id") == "filterFieldsByName":
            item["options"]["include"]["names"] = fields
        if item.get("id") == "organize":
            item["options"]["indexByName"] = {
                name: index for index, name in enumerate(fields)
            }
            item["options"]["renameByName"] = {
                name: labels[name] for name in fields
            }
    panel["transformations"] = transforms
    return panel


_PROVIDER_SELECTOR_URL = (
    "/ops/observability/selected-run-status?pipeline=${pipeline}"
    "&run_id=${run_id}&run_type=${run_type:csv}&workflow=${workflow:csv}"
)
_PROVIDER_SELECTOR_ROOT = (
    '$exists(provider_options) and $count(provider_options) > 0 '
    '? provider_options : [{"text":"unknown","value":"unknown"}]'
)


def _bind_provider_variable_to_run(variable: dict) -> None:
    """Options come from the selected run. All is not a choice."""
    variable["includeAll"] = False
    variable["allValue"] = None
    variable["type"] = "query"
    variable["datasource"] = "BioETL Ops HTTP"
    variable["definition"] = _PROVIDER_SELECTOR_URL
    variable["refresh"] = 1
    variable["sort"] = 0
    variable["multi"] = False
    variable["current"] = {"selected": True, "text": "unknown", "value": "unknown"}
    variable["description"] = (
        "Provider for the selected Run ID. Options are the saved run participants. "
        "All is not available. Run ID is always set on this dashboard."
    )
    variable["query"] = {
        "queryType": "infinity",
        "refId": "variable",
        "infinityQuery": {
            "format": "table",
            "parser": "backend",
            "root_selector": _PROVIDER_SELECTOR_ROOT,
            "type": "json",
            "source": "url",
            "url_options": {"method": "GET", "data": ""},
            "url": _PROVIDER_SELECTOR_URL,
            "columns": [
                {"selector": "text", "text": "__text", "type": "string"},
                {"selector": "value", "text": "__value", "type": "string"},
            ],
        },
    }


def _style_provider_check(panels: list[dict]) -> None:
    by_id = {panel["id"]: panel for panel in panels}
    by_id[9400]["gridPos"].update(x=0, y=2, w=18, h=3)
    review = by_id[9461]
    review["gridPos"].update(x=18, y=2, w=6, h=3)
    review["type"] = "stat"
    review["description"] = "SELECTED RUN · Saved provider check result. Missing evidence stays UNKNOWN. This is not live fleet health."
    review["transformations"] = [{"id": "limit", "options": {"limitField": 1}}, {"id": "filterFieldsByName", "options": {"include": {"names": ["check_result"]}}}]
    review["options"] = {"reduceOptions": {"calcs": ["lastNotNull"], "fields": "/^check_result$/", "values": True}, "colorMode": "background", "graphMode": "none", "textMode": "value"}
    review["fieldConfig"] = {"defaults": {"noValue": "UNKNOWN", "mappings": [{"type": "value", "options": {
        "OK": {"text": "OK", "color": "green"},
        "HEALTHY": {"text": "HEALTHY", "color": "green"},
        "WARN": {"text": "WARN", "color": "orange"},
        "DEGRADED": {"text": "DEGRADED", "color": "orange"},
        "ERROR": {"text": "ERROR", "color": "red"},
        "FAIL": {"text": "FAIL", "color": "red"},
        "FAILING": {"text": "FAILING", "color": "red"},
        "CRIT": {"text": "CRIT", "color": "red"},
        "UNKNOWN": {"text": "UNKNOWN", "color": "gray"},
        "N/A": {"text": "N/A", "color": "gray"},
        "SELECT RUN": {"text": "SELECT RUN", "color": "gray"},
        "INCOMPLETE": {"text": "INCOMPLETE", "color": "orange"},
    }}], "color": {"mode": "fixed", "fixedColor": "gray"}}, "overrides": []}
    evidence = by_id[9460]
    evidence["gridPos"].update(y=5)
    if not any(t["id"] == "convertFieldType" for t in evidence["transformations"]):
        evidence["transformations"].insert(0, {"id": "convertFieldType", "options": {"conversions": [{"targetField": "observed_at", "destinationType": "time"}]}})
    evidence["fieldConfig"]["overrides"] = [{"matcher": {"id": "byName", "options": "Observed at"}, "properties": [{"id": "unit", "value": "time:YYYY-MM-DD HH:mm"}]}]
    for panel_id in (9402, 9403):
        by_id[panel_id]["gridPos"]["y"] = 10


def prune_provider_health_panels(payload: dict[str, object]) -> None:
    """Drop Provider Health panels that do not assess the selected Run ID."""
    if payload.get("uid") != _PROVIDER_HEALTH_UID:
        return
    panels = payload.get("panels")
    if not isinstance(panels, list):
        return
    payload["panels"] = _without_panel_ids(panels, _DROP_PROVIDER_PANEL_IDS)
    payload["description"] = (
        "SELECTED RUN. Saved provider evidence for this Run ID. "
        "Fleet and current telemetry are not on this page."
    )
    panels = payload["panels"]
    lifted: list[dict] = []

    def _lift(items: list[object]) -> None:
        for panel in items:
            if not isinstance(panel, dict):
                continue
            children = panel.get("panels")
            if isinstance(children, list):
                kept_children = []
                for child in children:
                    if isinstance(child, dict) and child.get("id") in {9402, 9403}:
                        lifted.append(child)
                    else:
                        kept_children.append(child)
                panel["panels"] = kept_children
                _lift(kept_children)

    _lift(panels)
    panels[:] = [
        panel
        for panel in panels
        if not (
            isinstance(panel, dict)
            and panel.get("type") == "row"
            and not panel.get("panels")
        )
    ]
    panels.extend(lifted)
    for panel in panels:
        if isinstance(panel, dict) and panel.get("id") == 9400:
            options = panel.setdefault("options", {})
            options["content"] = (
                '<div style="padding:4px 10px;border-left:4px solid #6b7280;'
                "font-size:16px;line-height:1.2;white-space:normal;"
                'overflow-wrap:anywhere;max-width:96ch">'
                "SELECTED RUN · Provider evidence is the saved check for this Run ID. "
                "Fleet and current telemetry are not shown here.</div>"
            )
            options["bioetlDisplayTitle"] = "Understand Selected Run"
            panel["description"] = (
                "SELECTED RUN · Run ID is always set. "
                "Provider evidence is the saved check for this run. "
                "Fleet and current telemetry are not shown here."
            )
    templating = payload.get("templating")
    if isinstance(templating, dict):
        variables = templating.get("list")
        if isinstance(variables, list):
            for variable in variables:
                if isinstance(variable, dict) and variable.get("name") == "provider":
                    _bind_provider_variable_to_run(variable)
    panels[:] = [
        panel
        for panel in panels
        if not isinstance(panel, dict) or panel.get("id") not in {9460, 9461, 9462}
    ]
    evidence = _provider_check_panel(
        9460,
        "Review Provider Evidence",
        {"x": 0, "y": 7, "w": 24, "h": 5},
        ["provider", "check_result", "evidence", "observed_at"],
        limit=None,
    )
    evidence.setdefault("options", {}).setdefault("footer", {})["enablePagination"] = True
    review = _provider_check_panel(
        9461,
        "Review Provider Check",
        {"x": 0, "y": 4, "w": 24, "h": 3},
        ["check_result", "evidence"],
        limit=1,
    )
    review.setdefault("fieldConfig", {}).setdefault("defaults", {})["noValue"] = "UNKNOWN"
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        if panel.get("id") == 9400:
            panel["gridPos"] = {"x": 0, "y": 2, "w": 24, "h": 2}
        if panel.get("id") == 9402:
            panel["gridPos"] = {"x": 0, "y": 12, "w": 12, "h": 5}
            panel.setdefault("options", {}).setdefault("footer", {})[
                "enablePagination"
            ] = True
        if panel.get("id") == 9403:
            panel["gridPos"] = {"x": 12, "y": 12, "w": 12, "h": 5}
            panel.setdefault("options", {}).setdefault("footer", {})[
                "enablePagination"
            ] = True
    panels.extend([review, evidence])
    _style_provider_check(panels)


def stamp_selected_run_panels(payload: dict[str, object]) -> None:
    """Replace selected-run summaries through the generator, keeping CURRENT distinct."""
    panels = payload.get("panels", [])
    uid = payload.get("uid")
    for panel in _walk_panels(panels):
        if not isinstance(panel, dict):
            continue
        old_links = deepcopy(panel.get("links", []))
        old_data_links = deepcopy(
            panel.get("fieldConfig", {}).get("defaults", {}).get("links", [])
        )
        _stamp_control_plane_copy(panel, uid)
        if uid == _OVERVIEW_UID and panel.get("id") in {9006, 9003, 9004, 9005, 9013}:
            panel["description"] = str(panel.get("description", "")).replace(
                "as Review Domain Status", "as Review All Domain Status (CURRENT)"
            )
        _rewrite_selected_run_tables(panel, uid)
        _preserve_existing_links(panel, old_links, old_data_links)
        _stamp_status_links(panel, uid, panels)
        _stamp_overview_derived_panels(panel, uid)
    prune_provider_health_panels(payload)
    panels = payload.get("panels", [])
    if uid in {
        "bioetl-overview-v2",
        "bioetl-control-plane-v1",
        "bioetl-provider-health-v2",
    }:
        payload["panels"] = [
            panel
            for panel in panels
            if not isinstance(panel, dict) or panel.get("id") != 9450
        ]
    elif uid != "bioetl-run-explorer-v1":
        _append_saved_run_evidence_row(
            panels,
            include_identity=uid != _CONTROL_PLANE_UID,
            include_duration=uid == "bioetl-runtime",
        )


SELECTOR_ROWS = (
    '$exists(items) and $count(items) = 0 ? '
    '[{"text":"NO MATCHES","value":"-"}] : items'
)


def stamp_selector_columns(payload: dict[str, object]) -> None:
    """Keep Infinity variable frames typed even when the catalog is empty."""
    for variable in payload.get("templating", {}).get("list", []):
        if variable.get("name") == "run_id":
            variable["regex"] = ""
        query = variable.get("query")
        if not isinstance(query, dict):
            continue
        infinity = query.get("infinityQuery", {})
        url = infinity.get("url", "")
        if not url.startswith("/ops/control-plane/filter-options?"):
            continue
        url = url.replace("response_shape=list", "response_shape=options")
        infinity["url"] = url
        infinity["parser"] = "backend"
        infinity["root_selector"] = SELECTOR_ROWS
        variable["definition"] = url
        infinity["columns"] = [
            {"selector": field, "text": f"__{field}", "type": "string"}
            for field in ("text", "value")
        ]
