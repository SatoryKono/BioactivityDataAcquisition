"""Apply the September dashboard audit follow-up to the shipped JSON models.

Run before render_nav_bus; changes are idempotent. No live services are mutated.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
DASH = ROOT / "grafana/dashboards"
MISSING = "TELEMETRY MISSING — no series for this scope; not a zero"


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


def clean_links(value: Any) -> None:
    if isinstance(value, dict):
        for key, child in list(value.items()):
            if key in {"links", "dataLinks"} and isinstance(child, list):
                value[key] = [
                    link
                    for link in child
                    if not str(link.get("url", "")).startswith("data:text/plain")
                ]
            if key == "properties" and isinstance(child, list):
                for prop in child:
                    if prop.get("id") == "links":
                        prop["value"] = [
                            link
                            for link in prop["value"]
                            if not str(link.get("url", "")).startswith(
                                "data:text/plain"
                            )
                        ]
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
        if not link.get("title", "").startswith("Show all rows")
    ]
    clone["id"] = 20000 + panel["id"]
    clone["title"] = "Inspect Full " + panel["title"].removeprefix(
        "Inspect "
    ).removeprefix("Review ").removeprefix("Monitor ")
    all_rows(clone)
    clone["datasource"] = {"type": "datasource", "uid": "-- Dashboard --"}
    clone["targets"] = [{"panelId": panel["id"], "refId": "A", "withTransforms": False}]

    def neutral(value):
        if isinstance(value, dict):
            if value.get("type") == "color-background":
                value["type"] = "color-text"
            for child in value.values():
                neutral(child)
        elif isinstance(value, list):
            for child in value:
                neutral(child)

    neutral(clone)
    clone["description"] = "TIME RANGE · " + clone.get("description", "").removeprefix(
        "TIME RANGE · "
    )
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
        link for link in links if not link.get("title", "").startswith("Show all rows")
    ]
    links.append(
        {
            "includeVars": False,
            "title": title,
            "url": f"/d/{dashboard['uid']}/{dashboard['uid']}?${{workflow:queryparam}}&${{pipeline:queryparam}}&${{run_type:queryparam}}&${{run_id:queryparam}}&viewPanel={clone['id']}&${{__url_time_range}}",
            "targetBlank": False,
        }
    )


def apply_dashboard(dashboard: dict[str, Any]) -> None:
    uid = dashboard["uid"]
    dashboard["panels"] = [
        p for p in dashboard["panels"] if p["id"] not in {30215, 32010, 32005, 32460}
    ]
    clean_links(dashboard)
    panels = {p["id"]: p for p in walk(dashboard["panels"])}
    for panel in panels.values():
        if "Identity" in panel.get("title", "") and panel.get("type") == "table":
            panel["fieldConfig"]["defaults"]["custom"]["inspect"] = True
            panel["description"] += (
                ""
                if "Inspect value opens" in panel.get("description", "")
                else " Inspect value opens full identifiers as selectable plain text."
            )
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

    if uid == "bioetl-run-explorer-v1":
        p = panels[3010]
        for transform in p["transformations"]:
            options = transform["options"]
            if transform["id"] == "filterFieldsByName":
                options["include"]["names"] = [
                    "event_age_display" if n == "last_event_age_seconds" else n
                    for n in options["include"]["names"]
                ]
            if transform["id"] == "organize":
                for key in ("indexByName", "renameByName"):
                    if "last_event_age_seconds" in options[key]:
                        options[key]["event_age_display"] = options[key].pop(
                            "last_event_age_seconds"
                        )
        override(
            p,
            "Event age",
            **{"unit": "none", "custom.width": 140, "noValue": "UNKNOWN"},
        )
        content = panels[1]["options"]["content"]
        panels[1]["options"]["content"] = content.replace(
            ". Find Run ID: ${lookup_run_id}.", "."
        ).replace("6-run-explorer", "0-run-explorer")
        for variable in dashboard["templating"]["list"]:
            if variable["name"] == "run_id":
                variable["label"] = "Selected Run"
            elif variable["name"] == "lookup_run_id":
                variable["label"] = "Find exact Run ID"

    if uid == "bioetl-control-plane-v1":
        p = panels[9418]
        p["options"]["cellHeight"] = "auto"
        p["options"]["maxRowHeight"] = 230
        for name, width in (("Processing", 70), ("Trust", 110), ("Observed at", 120)):
            override(p, name, **{"custom.width": width})
        override(
            p,
            "Reasons",
            **{
                "custom.cellOptions": {"type": "auto", "wrapText": True},
                "custom.inspect": True,
                "links": [],
            },
        )
        # Give detailed accounting the full width of its own row.
        p = panels[9403]
        p["gridPos"].update(x=0, w=24)
        identity = panels[9402]
        p["gridPos"]["y"] = identity["gridPos"]["y"] + identity["gridPos"]["h"]
        for row in dashboard["panels"]:
            if p in row.get("panels", []):
                cursor = p["gridPos"]["y"] + p["gridPos"]["h"]
                for other in row["panels"]:
                    if other["id"] not in {9402, 9403}:
                        other["gridPos"].update(x=0, w=24, y=cursor)
                        cursor += other["gridPos"]["h"]

    if uid == "bioetl-overview-v2":
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
        override(panels[9603], "status", **{"custom.width": 145})
        panels[9603]["fieldConfig"]["defaults"]["noValue"] = (
            "UNKNOWN — summary unavailable; check Ops HTTP. No selection is SELECT RUN; absent report is REPORT MISSING."
        )
        full_list(dashboard, p, 2)
        detail_link = next(
            link for link in p["links"] if link["title"].startswith("Show all rows")
        )
        override(p, "Priority", links=[detail_link])
        p["links"] = [
            link for link in p["links"] if not link["title"].startswith("Show all rows")
        ]

    if uid == "bioetl-runtime":
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
        detail_row = next(row for row in dashboard["panels"] if row["id"] == 32460)
        detail_row["panels"].append({
            "id": 2461, "type": "table", "title": "Inspect Missing Stage Signals",
            "description": "CURRENT · Expected stage coverage for Pipeline / Run Type. Missing lag/backlog signals are listed individually. Undefined expected stages are UNKNOWN. VALID EMPTY requires a recorded complete stage catalog and every expected signal. Query failures are QUERY ERROR.",
            "gridPos": {"x": 0, "y": detail_row["gridPos"]["y"] + 13, "w": 24, "h": 8},
            "datasource": {"type": "prometheus", "uid": "prometheus"},
            "targets": [{"refId": "A", "expr": 'bioetl_runtime_stage_evidence_detail{pipeline=~"$pipeline",run_type=~"$run_type"}', "format": "table", "instant": True}],
            "fieldConfig": {"defaults": {"custom": {"inspect": True, "minWidth": 70, "cellOptions": {"type": "auto"}}, "noValue": "UNKNOWN — stage coverage unavailable", "unit": "none"}, "overrides": []},
            "options": {"showHeader": True, "cellHeight": "sm", "footer": {"show": False, "enablePagination": True}},
            "transformations": [{"id": "organize", "options": {"excludeByName": {"Time": True, "__name__": True, "Value": True}, "renameByName": {"pipeline": "Pipeline", "run_type": "Run type", "stage": "Stage", "signal": "Evidence"}}}],
        })
        coverage_link = {"title": "Inspect missing stage signals", "url": "/d/bioetl-runtime/3-pipeline-diagnostics?${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}&${run_id:queryparam}&var-stage=$__all&viewPanel=2461&${__url_time_range}", "includeVars": False, "targetBlank": False}
        links = panels[9102].setdefault("links", [])
        if coverage_link not in links:
            links.append(coverage_link)
        groups = "bioetl_runtime_dashboard_recording|bioetl_monitoring_stack_observability|bioetl_optional_docker_runtime_stability|bioetl_pipeline_runtime_observability|bioetl_control_plane_traceability_observability|bioetl_dq_observability|bioetl_provider_health_observability"
        selector = f'prometheus_rule_group_last_evaluation_timestamp_seconds{{rule_group=~".*;({groups})"}}'
        panels[9102]["targets"][2]["expr"] = "bioetl_runtime_required_rule_age_seconds"
        panels[9102]["description"] += (
            ""
            if "oldest required" in panels[9102]["description"]
            else " Rule age is the oldest required group; missing groups return UNKNOWN."
        )

    if uid == "bioetl-provider-health-v2":
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

    if uid == "bioetl-dq-v2":
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
                o["excludeByName"]["started_at"] = False
                o["renameByName"].update(started_at="Started", coverage_chip="Coverage")
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
        override(p, "Started", **{"unit": "time:YYYY-MM-DD HH:mm", "custom.width": 155})
        override(p, "Coverage", **{"custom.width": 130})
        p["description"] += (
            ""
            if "Silver Q means" in p["description"]
            else " Silver Q means Silver quarantine; Gold Q means Gold quarantine. Excl % = contract exclusions / Silver accepted records × 100. Started and Coverage describe persisted history, not current health."
        )

    if uid == "bioetl-incident-v1":
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
                "custom.width": 130,
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

        def route_links(value):
            if isinstance(value, dict):
                if "${__data.fields.action_dashboard_uid}" in str(value.get("url", "")):
                    value["url"] = value["url"].replace(
                        "${__data.fields.Pipeline}", "${__data.fields.route_pipeline}"
                    )
                    value["title"] = "Open domain diagnostics"
                for child in value.values():
                    route_links(child)
            elif isinstance(value, list):
                for child in value:
                    route_links(child)

        route_links(p)
        for pid in (2010, 2005):
            full_list(dashboard, panels[pid], 4 if pid == 2010 else 3)


def main() -> None:
    for path in DASH.glob("*.json"):
        original = json.loads(path.read_text(encoding="utf-8"))
        dashboard = copy.deepcopy(original)
        apply_dashboard(dashboard)
        clean_links(dashboard)
        if dashboard != original:
            path.write_text(
                json.dumps(dashboard, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )


if __name__ == "__main__":
    main()
