"""Canonical saved-run summaries; current readiness remains a separate telemetry view."""

from __future__ import annotations

from copy import deepcopy

STATUS_URL = "/ops/observability/selected-run-status?pipeline=${pipeline}&run_id=${run_id}&run_type=${run_type:csv}&workflow=${workflow:csv}"
DESCRIPTION = (
    "SELECTED RUN · Saved evidence for the exact Run ID. Completion age and chart range "
    "do not change this verdict. CURRENT uses fresh telemetry and retains its 15-minute "
    "freshness rule. Historical Trust never authorizes replay now. Missing checks are "
    "INCOMPLETE; missing selection is SELECT RUN; request failure is QUERY ERROR. "
    "N/A means explicitly inapplicable. VALID EMPTY is an empty successful query; backend down is QUERY ERROR. Chart coverage is separate: use Set range to run "
    "in Run Explorer to inspect a partial or outside range. Inspect the report for rules, "
    "revision, completion and the saved source evidence."
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
            DESCRIPTION
            + " Observed is the saved completion-time assessment. processing_status success does not imply trust_status OK."
        )
    if panel.get("id") == 9421:
        panel["description"] = (
            DESCRIPTION + " SELECTED RUN search: find an exact persisted identity."
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
            _panel(9002, "Review Selected Run Domains", panel["gridPos"], domains=True)
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


def _append_saved_run_evidence_row(panels: list[object]) -> None:
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
    details = _panel(
        9451,
        "Inspect Selected Run Domains",
        {"x": 0, "y": y + 1, "w": 24, "h": 10},
        domains=True,
    )
    _detail_fields(details, ["domain", "verdict", "reason", "action", "evidence_ref"])
    summary = _panel(
        9452,
        "Inspect Selected Run Identity",
        {"x": 0, "y": y + 11, "w": 24, "h": 8},
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
    panels.append(
        {
            "id": 9450,
            "type": "row",
            "title": "Inspect Saved Run Evidence",
            "collapsed": True,
            "gridPos": {"x": 0, "y": y, "w": 24, "h": 1},
            "panels": [details, deepcopy(summary)],
        }
    )


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
    _append_saved_run_evidence_row(panels)


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
        infinity["parser"] = "simple"
        infinity["root_selector"] = "items"
        variable["definition"] = url
        infinity["columns"] = [
            {"selector": field, "text": f"__{field}", "type": "string"}
            for field in ("text", "value")
        ]
