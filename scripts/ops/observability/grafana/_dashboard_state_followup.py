"""Apply the September dashboard audit follow-up to the shipped JSON models.

Internal transformations for render_nav_bus --state-followup. No live services
are mutated; this module is not a standalone command.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
DASH = ROOT / "grafana/dashboards"
MISSING = "TELEMETRY MISSING — no series for this scope; not a zero"
SHOW_ALL_ROWS_PREFIX = "Show all rows"
CUSTOM_WIDTH = "custom.width"
_DATA_TEXT_PREFIX = "data:text/plain"
_RETIRED_PANEL_IDS = {30215, 32010, 32005, 32460}


def walk(panels: list[dict[str, Any]]):
    for panel in panels:
        yield panel
        yield from walk(panel.get("panels", []))


def override(panel: dict[str, Any], name: str, **properties: Any) -> None:
    overrides = panel["fieldConfig"].setdefault("overrides", [])
    item = next(
        (o for o in overrides if o["matcher"] == {"id": "byName", "options": name}),
        None,
    )
    if item is None:
        item = {"matcher": {"id": "byName", "options": name}, "properties": []}
        overrides.append(item)
    for key, value in properties.items():
        item["properties"] = [p for p in item["properties"] if p["id"] != key]
        item["properties"].append({"id": key, "value": value})


def _scrub_link_list(links: list[Any]) -> list[Any]:
    return [
        link
        for link in links
        if not str(link.get("url", "")).startswith(_DATA_TEXT_PREFIX)
    ]


def _scrub_property_links(properties: list[Any]) -> None:
    for prop in properties:
        if prop.get("id") == "links":
            prop["value"] = _scrub_link_list(prop["value"])


def clean_links(value: Any) -> None:
    if isinstance(value, dict):
        for key in tuple(value):
            child = value[key]
            if key in {"links", "dataLinks"} and isinstance(child, list):
                value[key] = _scrub_link_list(child)
            if key == "properties" and isinstance(child, list):
                _scrub_property_links(child)
            if "url" in value and str(value["url"]).startswith("/d/"):
                value["includeVars"] = False
            clean_links(value[key])
    elif isinstance(value, list):
        for child in value:
            clean_links(child)


def all_rows(panel: dict[str, Any]) -> None:
    """Keep the full result accessible; pagination shows the total row count."""
    panel["transformations"] = [
        t for t in panel.get("transformations", []) if t["id"] != "limit"
    ]
    panel["options"]["footer"] = {
        "show": False,
        "enablePagination": True,
        "countRows": True,
    }


def _neutralize_full_list_clone(value: Any) -> None:
    if isinstance(value, dict):
        if value.get("id") == "links":
            value["value"] = [
                link
                for link in value["value"]
                if not link.get("title", "").startswith(SHOW_ALL_ROWS_PREFIX)
            ]
        if value.get("type") == "color-background":
            value["type"] = "color-text"
        for child in value.values():
            _neutralize_full_list_clone(child)
    elif isinstance(value, list):
        for child in value:
            _neutralize_full_list_clone(child)


def full_list(dashboard: dict[str, Any], panel: dict[str, Any], limit: int) -> None:
    """Keep the first-screen budget while exposing the complete paginated table."""
    if panel["id"] == 215 and not any(
        t["id"] == "sortBy" for t in panel["transformations"]
    ):
        panel["transformations"].insert(
            0, {"id": "sortBy", "options": {"sort": [{"field": "Value", "desc": True}]}}
        )
    clone = copy.deepcopy(panel)
    clone["links"] = [
        link
        for link in clone.get("links", [])
        if not link.get("title", "").startswith(SHOW_ALL_ROWS_PREFIX)
    ]
    clone["id"] = 20000 + panel["id"]
    clone["title"] = "Inspect Full " + panel["title"].removeprefix(
        "Inspect "
    ).removeprefix("Review ").removeprefix("Monitor ")
    all_rows(clone)
    clone["datasource"] = {"type": "datasource", "uid": "-- Dashboard --"}
    clone["targets"] = [{"panelId": panel["id"], "refId": "A", "withTransforms": False}]
    _neutralize_full_list_clone(clone)
    clone["description"] = "CURRENT · " + clone.get("description", "").removeprefix(
        "TIME RANGE · "
    ).removeprefix("CURRENT · ")
    row_id = 30000 + panel["id"]
    dashboard["panels"] = [p for p in dashboard["panels"] if p["id"] != row_id]
    y = max(p["gridPos"]["y"] + p["gridPos"]["h"] for p in dashboard["panels"])
    clone["gridPos"] = {"x": 0, "y": y + 1, "w": 24, "h": 12}
    dashboard["panels"].append(
        {
            "id": row_id,
            "type": "row",
            "title": clone["title"],
            "collapsed": True,
            "gridPos": {"x": 0, "y": y, "w": 24, "h": 1},
            "panels": [clone],
        }
    )
    panel["transformations"] = [
        t for t in panel.get("transformations", []) if t["id"] != "limit"
    ]
    # Sort first, then limit. Retain the complete vector in the detail table.
    pos = next(
        (i + 1 for i, t in enumerate(panel["transformations"]) if t["id"] == "sortBy"),
        len(panel["transformations"]),
    )
    panel["transformations"].insert(
        pos, {"id": "limit", "options": {"limitField": limit}}
    )
    panel["options"]["footer"] = {"show": False, "enablePagination": False}
    title = f"Show all rows and total (summary: up to {limit})"
    links = panel.setdefault("links", [])
    links[:] = [
        link for link in links if not link.get("title", "").startswith(SHOW_ALL_ROWS_PREFIX)
    ]
    links.append(
        {
            "includeVars": False,
            "title": title,
            "url": f"/d/{dashboard['uid']}/{dashboard['uid']}?${{workflow:queryparam}}&${{pipeline:queryparam}}&${{run_type:queryparam}}&${{run_id:queryparam}}&viewPanel={clone['id']}&${{__url_time_range}}",
            "targetBlank": False,
        }
    )


def _strip_retired_panels(dashboard: dict[str, Any]) -> None:
    dashboard["panels"] = [
        p for p in dashboard["panels"] if p["id"] not in _RETIRED_PANEL_IDS
    ]


def _normalize_identity_inspect(panels: dict[int, dict[str, Any]]) -> None:
    for panel in panels.values():
        if "Identity" in panel.get("title", "") and panel.get("type") == "table":
            panel["fieldConfig"]["defaults"]["custom"]["inspect"] = True
            panel["description"] += (
                ""
                if "Inspect value opens" in panel.get("description", "")
                else " Inspect value opens full identifiers as selectable plain text."
            )


def _normalize_missing_series(panels: dict[int, dict[str, Any]]) -> None:
    for panel in panels.values():
        defaults = panel.get("fieldConfig", {}).get("defaults", {})
        if defaults.get("noValue", "").startswith("VALID EMPTY — no events"):
            defaults["noValue"] = MISSING
            defaults["mappings"] = [
                {
                    "type": "special",
                    "options": {
                        "match": "null+nan",
                        "result": {"text": "UNKNOWN", "color": "gray"},
                    },
                }
            ]
            panel["description"] = panel.get("description", "").replace(
                "VALID EMPTY (no events) is not TELEMETRY MISSING.",
                "A measured zero means no events (VALID EMPTY); absent series mean TELEMETRY MISSING. Query failures remain QUERY ERROR.",
            )


def apply_dashboard(dashboard: dict[str, Any]) -> None:
    _strip_retired_panels(dashboard)
    clean_links(dashboard)
    panels = {p["id"]: p for p in walk(dashboard["panels"])}
    _normalize_identity_inspect(panels)
    _normalize_missing_series(panels)
    applier = _UID_APPLIERS.get(dashboard["uid"])
    if applier is not None:
        applier(dashboard, panels)


def _rename_event_age_fields(panel: dict[str, Any]) -> None:
    for transform in panel["transformations"]:
        options = transform["options"]
        if transform["id"] == "filterFieldsByName":
            options["include"]["names"] = [
                "event_age_display" if name == "last_event_age_seconds" else name
                for name in options["include"]["names"]
            ]
        if transform["id"] == "organize":
            for key in ("indexByName", "renameByName"):
                if "last_event_age_seconds" in options[key]:
                    options[key]["event_age_display"] = options[key].pop(
                        "last_event_age_seconds"
                    )


def _relabel_run_variables(dashboard: dict[str, Any]) -> None:
    for variable in dashboard["templating"]["list"]:
        if variable["name"] == "run_id":
            variable["label"] = "Selected Run"
        elif variable["name"] == "lookup_run_id":
            variable["label"] = "Find exact Run ID"


def _apply_run_explorer(
    dashboard: dict[str, Any], panels: dict[int, dict[str, Any]]
) -> None:
    panel = panels[3010]
    _rename_event_age_fields(panel)
    override(
        panel,
        "Event age",
        **{"unit": "none", CUSTOM_WIDTH: 140, "noValue": "UNKNOWN"},
    )
    content = panels[1]["options"]["content"]
    panels[1]["options"]["content"] = content.replace(
        ". Find Run ID: ${lookup_run_id}.", "."
    ).replace("6-run-explorer", "0-run-explorer")
    _relabel_run_variables(dashboard)


def _clear_wrap_overrides(panel: dict[str, Any]) -> None:
    for item in panel["fieldConfig"]["overrides"]:
        for prop in item["properties"]:
            if prop["id"] == "custom.cellOptions":
                prop["value"].pop("wrapText", None)


def _stamp_trust_table(panel: dict[str, Any]) -> None:
    panel["options"]["cellHeight"] = "sm"
    panel["options"].pop("maxRowHeight", None)
    # Grafana 12 can measure only one wrapped field per row. Let its
    # longest-field measurement select Reasons instead of the timestamp.
    panel["fieldConfig"]["defaults"]["custom"]["cellOptions"] = {
        "type": "auto",
        "wrapText": True,
    }
    _clear_wrap_overrides(panel)
    for name, width in (("Processing", 85), ("Trust", 100), ("Observed at", 115)):
        override(panel, name, **{CUSTOM_WIDTH: width})
    override(panel, "Reasons", **{"custom.inspect": True, "links": []})
    panel["description"] = panel["description"].replace(
        "Select Reasons to inspect", "Use the panel link to inspect"
    )
    panel["links"] = [
        {
            "title": "Inspect all trust reasons",
            "url": "/d/bioetl-control-plane-v1/1-trust?${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}&${run_id:queryparam}&viewPanel=9414&${__url_time_range}",
            "includeVars": False,
            "targetBlank": False,
        }
    ]


def _restack_accounting_row(
    dashboard: dict[str, Any], panel: dict[str, Any], identity: dict[str, Any]
) -> None:
    panel["gridPos"].update(x=0, w=24)
    panel["gridPos"]["y"] = identity["gridPos"]["y"] + identity["gridPos"]["h"]
    for row in dashboard["panels"]:
        if panel not in row.get("panels", []):
            continue
        cursor = panel["gridPos"]["y"] + panel["gridPos"]["h"]
        for other in row["panels"]:
            if other["id"] not in {9402, 9403}:
                other["gridPos"].update(x=0, w=24, y=cursor)
                cursor += other["gridPos"]["h"]


def _apply_control_plane(
    dashboard: dict[str, Any], panels: dict[int, dict[str, Any]]
) -> None:
    _stamp_trust_table(panels[9418])
    _restack_accounting_row(dashboard, panels[9403], panels[9402])

def _apply_overview(
    dashboard: dict[str, Any], panels: dict[int, dict[str, Any]]
) -> None:
        p = panels[215]
        p["targets"][0]["expr"] = (
            'max without(run_type)(bioetl_l0_next_action_route{pipeline=~"$pipeline",run_type=~"$run_type"}>0) or on() bioetl_l0_next_action_no_route'
        )
        p["description"] = p["description"].replace(
            "before the two-row limit", "with all routes available through pagination"
        )
        panels[9601]["fieldConfig"]["defaults"]["noValue"] = (
            "UNKNOWN — no alert rows; verify rule evaluation and telemetry coverage"
        )
        override(panels[9603], "status", **{CUSTOM_WIDTH: 145})
        panels[9603]["fieldConfig"]["defaults"]["noValue"] = (
            "UNKNOWN — summary unavailable; check Ops HTTP. No selection is SELECT RUN; absent report is REPORT MISSING."
        )
        full_list(dashboard, p, 2)
        detail_link = next(
            link for link in p["links"] if link["title"].startswith(SHOW_ALL_ROWS_PREFIX)
        )
        override(p, "Priority", links=[detail_link])
        p["links"] = [
            link for link in p["links"] if not link["title"].startswith(SHOW_ALL_ROWS_PREFIX)
        ]

def _apply_runtime(
    dashboard: dict[str, Any], panels: dict[int, dict[str, Any]]
) -> None:
        panels[9401]["options"]["colorMode"] = "value"
        p = panels[2460]
        p["targets"][0]["expr"] = (
            'bioetl_runtime_stage_progress_by_scope{pipeline=~"$pipeline",run_type=~"$run_type"}'
        )
        # A row retains its pipeline and run type even when a caller passes All.
        for t in p.get("transformations", []):
            if t["id"] == "groupingToMatrix":
                t["options"]["rowField"] = "scope_stage"
            if t["id"] == "organize":
                for key in ("pipeline", "run_type"):
                    t["options"].setdefault("excludeByName", {})[key] = False
        full_list(dashboard, p, 3)
        if not any(child.get("id") == 2461 for child in walk(dashboard["panels"])):
            detail_row = next(row for row in dashboard["panels"] if row["id"] == 32460)
            detail_row["panels"].append(
                {
                    "id": 2461,
                    "type": "table",
                    "title": "Inspect Current Missing Stage Signals",
                    "description": "CURRENT · Expected stage coverage for Pipeline / Run Type. Missing lag/backlog signals are listed individually. Undefined expected stages are UNKNOWN. VALID EMPTY requires a recorded complete stage catalog and every expected signal. Query failures are QUERY ERROR.",
                    "gridPos": {
                        "x": 0,
                        "y": detail_row["gridPos"]["y"] + 13,
                        "w": 24,
                        "h": 8,
                    },
                    "datasource": {"type": "prometheus", "uid": "prometheus"},
                    "targets": [
                        {
                            "refId": "A",
                            "expr": 'bioetl_runtime_stage_evidence_detail{pipeline=~"$pipeline",run_type=~"$run_type"}',
                            "format": "table",
                            "instant": True,
                        }
                    ],
                    "fieldConfig": {
                        "defaults": {
                            "custom": {
                                "inspect": True,
                                "minWidth": 70,
                                "cellOptions": {"type": "auto"},
                            },
                            "noValue": "UNKNOWN — stage coverage unavailable",
                            "unit": "none",
                        },
                        "overrides": [],
                    },
                    "options": {
                        "showHeader": True,
                        "cellHeight": "sm",
                        "footer": {"show": False, "enablePagination": True},
                    },
                    "transformations": [
                        {
                            "id": "organize",
                            "options": {
                                "excludeByName": {
                                    "Time": True,
                                    "__name__": True,
                                    "Value": True,
                                },
                                "renameByName": {
                                    "pipeline": "Pipeline",
                                    "run_type": "Run type",
                                    "stage": "Stage",
                                    "signal": "Evidence",
                                },
                            },
                        }
                    ],
                }
            )
        coverage_link = {
            "title": "Inspect missing stage signals",
            "url": "/d/bioetl-runtime/3-pipeline-diagnostics?${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}&${run_id:queryparam}&var-stage=$__all&viewPanel=2461&${__url_time_range}",
            "includeVars": False,
            "targetBlank": False,
        }
        links = panels[9102].setdefault("links", [])
        if coverage_link not in links:
            links.append(coverage_link)
        panels[9102]["targets"][2]["expr"] = "bioetl_runtime_required_rule_age_seconds"
        panels[9102]["description"] += (
            ""
            if "oldest required" in panels[9102]["description"]
            else " Rule age is the oldest required group; missing groups return UNKNOWN."
        )

def _apply_provider_health(
    _dashboard: dict[str, Any], panels: dict[int, dict[str, Any]]
) -> None:
        # Legacy context remains a compatibility input, never the authority over
        # the visible Pipeline selector. Adapter evidence is explicitly global.
        for pid in (31, 32):
            p = panels[pid]
            p["description"] += (
                ""
                if "GLOBAL ADAPTER" in p["description"]
                else " GLOBAL ADAPTER evidence: covers all adapters, independent of Provider and Pipeline."
            )
            p["title"] = (
                p["title"]
                .replace("Monitor Circuit", "Monitor Global Circuit")
                .replace("Track Circuit", "Track Global Circuit")
            )
        for pid in (9103,):
            p = panels[pid]
            p["fieldConfig"]["defaults"]["links"] = [
                {
                    "title": "Inspect fleet telemetry coverage",
                    "url": "/d/bioetl-provider-health-v2/4-provider-health?${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}&${run_id:queryparam}&var-provider=$__all&viewPanel=9104&${__url_time_range}",
                }
            ]

def _apply_dq(
    _dashboard: dict[str, Any], panels: dict[int, dict[str, Any]]
) -> None:
        p = panels[9406]
        for t in p["transformations"]:
            if t["id"] == "filterFieldsByName":
                names = t["options"]["include"]["names"]
                for name in ("started_at", "coverage_chip"):
                    if name not in names:
                        names.insert(0, name)
            if t["id"] == "organize":
                o = t["options"]
                names = ["started_at", "coverage_chip"] + [
                    n
                    for n in o["indexByName"]
                    if n not in {"started_at", "coverage_chip"}
                ]
                o["indexByName"] = {n: i for i, n in enumerate(names)}
                o.setdefault("excludeByName", {})["started_at"] = False
                o.setdefault("renameByName", {}).update(
                    started_at="Started", coverage_chip="Coverage"
                )
        if not any(t["id"] == "convertFieldType" for t in p["transformations"]):
            p["transformations"].insert(
                0,
                {
                    "id": "convertFieldType",
                    "options": {
                        "conversions": [
                            {"targetField": "started_at", "destinationType": "time"}
                        ]
                    },
                },
            )
        override(p, "Started", **{"unit": "time:YYYY-MM-DD HH:mm", CUSTOM_WIDTH: 155})
        override(p, "Coverage", **{CUSTOM_WIDTH: 150})
        p["description"] += (
            ""
            if "Silver Q means" in p["description"]
            else " Silver Q means Silver quarantine; Gold Q means Gold quarantine. Excl % = contract exclusions / Silver accepted records × 100. Started and Coverage describe persisted history, not current health."
        )

def _apply_incident(
    dashboard: dict[str, Any], panels: dict[int, dict[str, Any]]
) -> None:
        for pid in (2010, 2005):
            for target in panels[pid]["targets"]:
                expr = target.get("expr", "")
                if expr.startswith("topk("):
                    # These shipped targets wrap a single ranked vector.
                    prefix, rest = expr.split(",", 1)
                    if prefix in {"topk(3", "topk(4"} and rest.endswith(")"):
                        target["expr"] = rest[:-1].strip()
        override(
            panels[2010],
            "Confidence",
            **{
                CUSTOM_WIDTH: 130,
                "custom.cellOptions": {"type": "auto", "wrapText": True},
            },
        )
        p = panels[2010]
        p["targets"][0]["expr"] = (
            'label_replace(bioetl_incident_ranked_evidence,"route_pipeline","$pipeline","pipeline","unknown")'
        )
        override(p, "route_pipeline", **{"custom.hidden": True})
        override(
            p,
            "Action",
            links=[
                {
                    "title": "Open domain diagnostics",
                    "url": "/d/${__data.fields.action_dashboard_uid}/${__data.fields.action_dashboard_uid}?${workflow:queryparam}&var-pipeline=${__data.fields.route_pipeline}&${run_type:queryparam}&var-run_id=-&${__data.fields.action_scope}&${__url_time_range}",
                    "targetBlank": False,
                }
            ],
        )

        _rewrite_incident_route_links(p)
        for pid in (2010, 2005):
            full_list(dashboard, panels[pid], 4 if pid == 2010 else 3)


def _rewrite_incident_route_links(value: Any) -> None:
    if isinstance(value, dict):
        if "${__data.fields.action_dashboard_uid}" in str(value.get("url", "")):
            value["url"] = value["url"].replace(
                "${__data.fields.Pipeline}", "${__data.fields.route_pipeline}"
            )
            value["title"] = "Open domain diagnostics"
        for child in value.values():
            _rewrite_incident_route_links(child)
    elif isinstance(value, list):
        for child in value:
            _rewrite_incident_route_links(child)


_UID_APPLIERS = {
    "bioetl-run-explorer-v1": _apply_run_explorer,
    "bioetl-control-plane-v1": _apply_control_plane,
    "bioetl-overview-v2": _apply_overview,
    "bioetl-runtime": _apply_runtime,
    "bioetl-provider-health-v2": _apply_provider_health,
    "bioetl-dq-v2": _apply_dq,
    "bioetl-incident-v1": _apply_incident,
}
