"""Mutator for Review First Action panel (RFA-00 / #7569)."""

from __future__ import annotations

import json
from pathlib import Path

PATH = (
    Path(__file__).resolve().parents[4]
    / "grafana"
    / "dashboards"
    / "bioetl-overview-v2.json"
)

NEXT_ACTION_EXPR = (
    'topk(4, bioetl_l0_next_action_route{pipeline=~"$pipeline",run_type=~"$run_type"} '
    'or label_replace(label_replace(label_replace(vector(0), "action_target", "no_route", "", ""), '
    '"action_reason", "selected_scope_not_present", "", ""), '
    '"action_dashboard_uid", "bioetl-overview-v2", "", ""))'
)


def main() -> None:
    data = json.loads(PATH.read_text(encoding="utf-8"))
    panel = next(
        p
        for p in data["panels"]
        if p.get("title") == "Review First Action" and p.get("id") == 215
    )

    # Ensure GOLD mapping exists on Priority value.
    defaults = panel.setdefault("fieldConfig", {}).setdefault("defaults", {})
    mappings = defaults.setdefault("mappings", [])
    for mapping in mappings:
        if mapping.get("type") != "value":
            continue
        options = mapping.setdefault("options", {})
        options.setdefault("0", {"text": "NO_ROUTE", "color": "gray"})
        options.setdefault("5", {"text": "MONITOR", "color": "gray"})
        options.setdefault("10", {"text": "WORKFLOW", "color": "green"})
        options.setdefault("20", {"text": "PROVIDER", "color": "orange"})
        options.setdefault("30", {"text": "DQ", "color": "orange"})
        options["35"] = {"text": "GOLD", "color": "orange"}
        options.setdefault("40", {"text": "CONTROL PLANE", "color": "red"})
        options.setdefault("50", {"text": "RUNTIME", "color": "red"})

    panel["description"] = (
        "Shows up to four highest-priority next actions for the current fleet/selectors "
        "(priority: Runtime > Control Plane > Gold lifecycle > DQ > Provider > Workflow > Monitor). "
        "Click Action to open the recommended board with the row pipeline preserved. "
        "Priority uses text color (not fill). Missing/empty scope falls back to NO_ROUTE. "
        "run_id is handoff context only — never a Prometheus label. "
        "When Priority is MONITOR and Fleet Health is OK, continue monitoring rather than escalating."
    )
    panel["targets"] = [
        {
            "expr": NEXT_ACTION_EXPR,
            "refId": "A",
            "format": "table",
            "instant": True,
        }
    ]

    defaults["custom"] = {
        "align": "left",
        "cellOptions": {"type": "auto"},
        "inspect": False,
    }
    panel["fieldConfig"]["overrides"] = [
        {
            "matcher": {"id": "byName", "options": "Value"},
            "properties": [
                {"id": "displayName", "value": "Priority"},
                {"id": "custom.width", "value": 110},
                {"id": "custom.align", "value": "left"},
                {"id": "custom.cellOptions", "value": {"type": "color-text"}},
                {"id": "color", "value": {"mode": "thresholds"}},
            ],
        },
        {
            "matcher": {"id": "byName", "options": "Priority"},
            "properties": [
                {"id": "custom.width", "value": 110},
                {"id": "custom.cellOptions", "value": {"type": "color-text"}},
                {"id": "color", "value": {"mode": "thresholds"}},
            ],
        },
        {
            "matcher": {"id": "byName", "options": "action_target"},
            "properties": [
                {"id": "displayName", "value": "Action"},
                {
                    "id": "mappings",
                    "value": [
                        {
                            "type": "value",
                            "options": {
                                "control_plane": {
                                    "text": "Open Control Plane",
                                    "color": "red",
                                },
                                "dq": {"text": "Open DQ", "color": "orange"},
                                "monitor": {
                                    "text": "Monitor / no urgent action",
                                    "color": "gray",
                                },
                                "no_route": {
                                    "text": "No route — check selectors",
                                    "color": "gray",
                                },
                                "provider": {
                                    "text": "Open Provider",
                                    "color": "orange",
                                },
                                "runtime": {
                                    "text": "Open Runtime",
                                    "color": "red",
                                },
                                "workflow": {
                                    "text": "Open Runtime (workflow)",
                                    "color": "green",
                                },
                            },
                        }
                    ],
                },
                {"id": "custom.width", "value": 150},
                {"id": "custom.cellOptions", "value": {"type": "color-text"}},
                {"id": "color", "value": {"mode": "thresholds"}},
                {
                    # Fixed target UIDs keep navigation contracts valid; pipeline is
                    # row-aware via ${__data.fields.pipeline}. Operators pick the
                    # board matching Action text (action_dashboard_uid remains hidden).
                    # Use $var form (not ${var}) so link allowlists accept handoffs.
                    "id": "links",
                    "value": [
                        {
                            "title": "Open Runtime",
                            "url": (
                                "/d/bioetl-runtime/bioetl-runtime"
                                "?var-pipeline=${__data.fields.pipeline}"
                                "&var-run_type=$run_type"
                                "&var-stage=unknown"
                                "&var-workflow=$workflow"
                                "&var-run_id=$run_id"
                                "&${__url_time_range}"
                            ),
                            "targetBlank": False,
                            "includeVars": False,
                        },
                        {
                            "title": "Open Control Plane",
                            "url": (
                                "/d/bioetl-control-plane-v1/bioetl-control-plane-v1"
                                "?var-pipeline=${__data.fields.pipeline}"
                                "&var-run_type=$run_type"
                                "&var-workflow=$workflow"
                                "&var-run_id=$run_id"
                                "&${__url_time_range}"
                            ),
                            "targetBlank": False,
                            "includeVars": False,
                        },
                        {
                            "title": "Open Data Quality",
                            "url": (
                                "/d/bioetl-dq-v2/bioetl-dq-v2"
                                "?var-pipeline=${__data.fields.pipeline}"
                                "&var-run_type=$run_type"
                                "&var-stage=unknown"
                                "&var-workflow=$workflow"
                                "&var-run_id=$run_id"
                                "&${__url_time_range}"
                            ),
                            "targetBlank": False,
                            "includeVars": False,
                        },
                        {
                            "title": "Open Provider Health",
                            "url": (
                                "/d/bioetl-provider-health-v2/bioetl-provider-health-v2"
                                "?var-provider=unknown"
                                "&var-pipeline_context=${__data.fields.pipeline}"
                                "&var-adapter=unknown"
                                "&var-pipeline=${__data.fields.pipeline}"
                                "&var-run_type=$run_type"
                                "&var-workflow=$workflow"
                                "&var-run_id=$run_id"
                                "&${__url_time_range}"
                            ),
                            "targetBlank": False,
                            "includeVars": False,
                        },
                    ],
                },
            ],
        },
        {
            "matcher": {"id": "byName", "options": "action_reason"},
            "properties": [
                {"id": "displayName", "value": "Why"},
                {
                    "id": "mappings",
                    "value": [
                        {
                            "type": "value",
                            "options": {
                                "control_plane_guardrail_active": {
                                    "text": "Control-plane issue"
                                },
                                "dq_threshold_or_validation_signal": {
                                    "text": "DQ issue"
                                },
                                "no_recent_activity_or_unknown_state": {
                                    "text": "No recent activity"
                                },
                                "selected_scope_not_present": {
                                    "text": "Selector not present"
                                },
                                "provider_global_degradation": {
                                    "text": "Provider issue"
                                },
                                "gold_lifecycle_blocking": {
                                    "text": "Gold lifecycle blocked"
                                },
                                "runtime_blockers_active": {
                                    "text": "Runtime blocked"
                                },
                                "workflow_scope_requires_review": {
                                    "text": "Workflow review"
                                },
                            },
                        }
                    ],
                },
                {"id": "custom.width", "value": 150},
                {
                    "id": "custom.cellOptions",
                    "value": {"type": "auto", "wrapText": True},
                },
            ],
        },
        {
            "matcher": {"id": "byName", "options": "pipeline"},
            "properties": [
                {"id": "displayName", "value": "Pipeline"},
                {"id": "custom.width", "value": 160},
                {
                    "id": "custom.cellOptions",
                    "value": {"type": "auto", "wrapText": True},
                },
            ],
        },
        {
            "matcher": {"id": "byName", "options": "Pipeline"},
            "properties": [
                {"id": "custom.width", "value": 160},
                {
                    "id": "custom.cellOptions",
                    "value": {"type": "auto", "wrapText": True},
                },
            ],
        },
        {
            "matcher": {"id": "byName", "options": "action_dashboard_uid"},
            "properties": [
                {"id": "displayName", "value": ""},
                {"id": "custom.width", "value": 1},
                {
                    "id": "custom.hideFrom",
                    "value": {"tooltip": False, "viz": True, "legend": True},
                },
            ],
        },
    ]

    # Contract tests expect panel.links (not only options.dataLinks).
    panel_links = [
        {
            "title": "Open Runtime",
            "url": (
                "/d/bioetl-runtime/bioetl-runtime?var-pipeline=$pipeline"
                "&var-run_type=$run_type&var-stage=unknown&${__url_time_range}"
                "&var-workflow=$workflow&var-run_id=$run_id"
            ),
            "targetBlank": False,
            "includeVars": False,
        },
        {
            "title": "Open Control Plane",
            "url": (
                "/d/bioetl-control-plane-v1/bioetl-control-plane-v1"
                "?var-pipeline=$pipeline&var-run_type=$run_type"
                "&${__url_time_range}&var-workflow=$workflow&var-run_id=$run_id"
            ),
            "targetBlank": False,
            "includeVars": False,
        },
        {
            "title": "Open Data Quality",
            "url": (
                "/d/bioetl-dq-v2/bioetl-dq-v2?var-pipeline=$pipeline"
                "&var-run_type=$run_type&var-stage=unknown&${__url_time_range}"
                "&var-workflow=$workflow&var-run_id=$run_id"
            ),
            "targetBlank": False,
            "includeVars": False,
        },
        {
            "title": "Open Provider Health",
            "url": (
                "/d/bioetl-provider-health-v2/bioetl-provider-health-v2"
                "?var-provider=unknown&var-pipeline_context=$pipeline"
                "&var-adapter=unknown&${__url_time_range}&var-workflow=$workflow"
                "&var-pipeline=$pipeline&var-run_type=$run_type&var-run_id=$run_id"
            ),
            "targetBlank": False,
            "includeVars": False,
        },
    ]
    panel["links"] = panel_links
    panel["options"] = {
        "showHeader": True,
        "footer": {"show": False},
        "cellHeight": "sm",
        "sortBy": [{"desc": True, "displayName": "Priority"}],
        "dataLinks": panel_links,
    }

    panel["transformations"] = [
        {
            "id": "organize",
            "options": {
                "excludeByName": {
                    "Time": True,
                    "__name__": True,
                    "bioetl_l0_next_action_route": True,
                    "input": True,
                    "run_type": True,
                },
                "indexByName": {
                    "Value": 0,
                    "action_target": 1,
                    "action_reason": 2,
                    "pipeline": 3,
                    "action_dashboard_uid": 4,
                },
                "renameByName": {
                    "Value": "Priority",
                    "pipeline": "Pipeline",
                },
            },
        }
    ]

    PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("PATH", PATH)
    print("expr_len", len(NEXT_ACTION_EXPR))
    print("links", [link["title"] for link in panel_links])


if __name__ == "__main__":
    main()
