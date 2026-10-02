"""Canonical ten-column Run Explorer and dashboard display names."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from copy import deepcopy

TITLES = {
    "bioetl-control-plane-v1": "Replay Readiness",
    "bioetl-overview-v2": "Run Overview",
    "bioetl-runtime": "Pipeline Diagnostics",
    "bioetl-provider-health-v2": "Provider Health",
    "bioetl-dq-v2": "Data Quality",
}
_RENAMES = {
    "1. Trust": "Replay Readiness",
    "2. Overview": "Run Overview",
    "3. Pipeline Diagnostics": "Pipeline Diagnostics",
    "4. Provider Health": "Provider Health",
    "5. Data Quality": "Data Quality",
}
_COLORS = {
    "OK": "#73BF69",
    "WARN": "#F2CC0C",
    "ERROR": "#F2495C",
    "INCOMPLETE": "#FF9830",
    "IN PROGRESS": "#5794F2",
    "N/A": "#9CA3AF",
    "QUERY ERROR": "#F2495C",
    "success": "#73BF69",
    "failed": "#F2495C",
    "fail": "#F2495C",
    "partial": "#F2CC0C",
    "running": "#5794F2",
    "unfinished": "#FF9830",
    "shutdown": "#F2CC0C",
    "dry_run": "#B877D9",
    "unknown": "#9CA3AF",
    "TREE_MISSING": "#F2495C",
    "LAYOUT_UNHEALTHY": "#F2495C",
    "IDENTITY_UNHEALTHY": "#F2495C",
}
_COLUMNS = {
    "workflow_id": ("Workflow", None, 100),
    "pipeline": ("Pipeline", None, 80),
    "provider": ("Provider", 85, 50),
    "run_label": ("Run ID", 90, 50),
    "started_at": ("Started", 115, 50),
    "duration_display": ("Duration", 75, 50),
    "status": ("Overview", 85, 50),
    "saved_evidence_status": ("Saved Evidence", None, 90),
    "data_quality_status": ("Data Quality", None, 90),
    "replay_readiness_status": ("Replay Readiness", 125, 90),
}
_CONTEXT = "var-workflow=${__data.fields.workflow_scope:percentencode}&var-pipeline=${__data.fields.Pipeline:percentencode}&var-run_type=${__data.fields.run_type:percentencode}&var-run_id=${__data.fields.run_id:percentencode}&${__url_time_range}"
_SELECT_RUN_URL = (
    "/d/bioetl-run-explorer-v1/run-explorer?" + _CONTEXT + "&var-lookup_run_id="
)
_RESET_FILTERS = (
    "/d/bioetl-run-explorer-v1/run-explorer"
    "?var-workflow=.*&var-pipeline=.*&var-run_type=.*&var-run_id=-"
    "&var-lookup_run_id=&${__url_time_range}"
)
_OPS_HTTP = "BioETL Ops HTTP"
_FILTER_ROOT = (
    '$exists(items) and $count(items) = 0 ? [{"text":"NO MATCHES","value":"-"}] : items'
)


def apply_overall_verdict(payload: dict) -> None:
    """Keep the headline and status table bound to the same saved assessment."""
    if payload.get("uid") != "bioetl-overview-v2":
        return
    panels = payload["panels"]
    source = next(p for p in panels if p["id"] == 9603)
    next(p for p in panels if p["id"] == 99)["gridPos"].update(w=source["gridPos"]["x"])
    panel = {
        "id": 9604,
        "type": "stat",
        "title": "Review Overall Verdict",
        "description": "SELECTED RUN · Saved overall verdict for the selected Run ID, identical to Review Selected Run Status. This verdict does not authorize replay. Missing evidence remains UNKNOWN; request errors remain errors.",
        "gridPos": {
            "x": source["gridPos"]["x"],
            "y": 2,
            "w": source["gridPos"]["w"],
            "h": 3,
        },
        "datasource": deepcopy(source["datasource"]),
        "targets": deepcopy(source["targets"]),
        "transformations": [
            {"id": "limit", "options": {"limitField": 1}},
            {
                "id": "filterFieldsByName",
                "options": {"include": {"names": ["run_verdict"]}},
            },
        ],
        "fieldConfig": {
            "defaults": {
                "unit": "none",
                "noValue": "UNKNOWN",
                "mappings": [
                    {
                        "type": "value",
                        "options": {
                            value: {"text": value, "color": color}
                            for value, color in {
                                "OK": "green",
                                "WARN": "yellow",
                                "ERROR": "red",
                                "INCOMPLETE": "orange",
                                "UNKNOWN": "gray",
                                "N/A": "gray",
                                "QUERY ERROR": "red",
                                "SELECT RUN": "gray",
                            }.items()
                        },
                    },
                    {
                        "type": "special",
                        "options": {
                            "match": "null",
                            "result": {"text": "UNKNOWN", "color": "gray"},
                        },
                    },
                ],
                "color": {"mode": "thresholds"},
                "thresholds": {
                    "mode": "absolute",
                    "steps": [{"color": "green", "value": None}],
                },
            },
            "overrides": [],
        },
        "options": {
            "reduceOptions": {
                "values": False,
                "calcs": ["lastNotNull"],
                "fields": "/.*/",
            },
            "orientation": "auto",
            "textMode": "value",
            "colorMode": "value",
            "graphMode": "none",
            "justifyMode": "center",
        },
    }
    panels[:] = [p for p in panels if p["id"] != panel["id"]]
    panels.insert(2, panel)


def _rename_text(value: Any) -> Any:
    if isinstance(value, str):
        for old, new in _RENAMES.items():
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [_rename_text(item) for item in value]
    if isinstance(value, dict):
        return {key: _rename_text(item) for key, item in value.items()}
    return value


def apply_run_explorer_columns(payload: dict[str, Any]) -> None:
    """Run last so older readability passes cannot restore obsolete columns."""
    payload.update(_rename_text(payload))
    if payload.get("uid") in TITLES:
        payload["title"] = TITLES[payload["uid"]]
    apply_overall_verdict(payload)
    if payload.get("uid") != "bioetl-run-explorer-v1":
        return
    _apply_run_explorer_templating(payload)
    panels = {panel["id"]: panel for panel in payload["panels"]}
    panels[1]["gridPos"]["h"] = 3
    content = panels[1]["options"]["content"].replace(
        "Select a Run ID to view details.", "Select a status to view details."
    )
    content = content.replace(
        "var-workflow=$__all&amp;var-pipeline=$__all&amp;var-run_type=$__all&amp;var-run_id=-&amp;var-lookup_run_id=",
        "var-workflow=.*&amp;var-pipeline=.*&amp;var-run_type=.*&amp;var-run_id=-&amp;var-lookup_run_id=",
    )
    content = content.replace(
        "var-workflow=$__all&amp;var-pipeline=$__all&amp;var-run_type=$__all&amp;var-run_id=-",
        "var-workflow=.*&amp;var-pipeline=.*&amp;var-run_type=.*&amp;var-run_id=-",
    )
    panels[1]["options"]["content"] = content
    panel = panels[3010]
    panel["gridPos"].update(y=3, h=13)
    panel["description"] = (
        "GLOBAL · BROWSE the launch catalog filtered by Workflow/Pipeline/Run Type. "
        "Last 10 launches, newest Started first, independent of the time range. "
        "Workflow and Pipeline open passports. Run ID opens the persisted Report; "
        "inspect its full UUID in the cell. Overview is processing status, not replay readiness. "
        "Saved Evidence, Data Quality and Replay Readiness use exact-run verified evidence. "
        "N/A means unsupported/legacy assessment. INCOMPLETE means missing required evidence. "
        "IN PROGRESS requires an explicit assessment queue/running signal and is never inferred. "
        "QUERY ERROR is a source failure; VALID EMPTY means no matching launches. "
        "Rows are artifact-backed: a tree_missing index means saved run artifacts are absent; "
        "verify backing with verify_report_bind.py. "
        "Running is a recorded state, not proof of current liveness. Missing reports have no link."
    )
    hidden = [
        "run_id",
        "workflow_scope",
        "run_type",
        "report_url",
        "report_label",
        "workflow_passport_url",
        "workflow_passport_path",
        "pipeline_passport_url",
        "pipeline_passport_path",
    ]
    names = [*_COLUMNS, *hidden]
    panel["targets"][0]["root_selector"] = (
        'index_state = "valid_empty" and $exists(items) and $count(items) = 0 '
        '? [{"pipeline": "VALID EMPTY"}] : items.($merge([$, '
        '{"workflow_id": workflow_id != "" ? workflow_id : "N/A", "run_label": run_id, '
        '"workflow_passport_path": $substringAfter(workflow_passport_url, '
        '"https://github.com/SatoryKono/BioactivityDataAcquisition/"), '
        '"pipeline_passport_path": $substringAfter(pipeline_passport_url, '
        '"https://github.com/SatoryKono/BioactivityDataAcquisition/"), '
        '"overview_handoff": "Open", "diagnostics_handoff": "Open", '
        '"provider_handoff": "Open", "quality_handoff": "Open"}]))'
    )
    panel["transformations"] = [
        {
            "id": "convertFieldType",
            "options": {
                "conversions": [
                    {"targetField": "started_at", "destinationType": "time"}
                ]
            },
        },
        {"id": "filterFieldsByName", "options": {"include": {"names": names}}},
        {
            "id": "organize",
            "options": {
                "indexByName": {name: i for i, name in enumerate(names)},
                "renameByName": {name: value[0] for name, value in _COLUMNS.items()},
                "excludeByName": {
                    "json_path": True,
                    "markdown_path": True,
                    "row_kind": True,
                },
            },
        },
        {"id": "limit", "options": {"limitField": 10}},
    ]
    defaults = panel["fieldConfig"]["defaults"]
    defaults.update(
        noValue=(
            "UNKNOWN — the launches table returned no rows for these filters. "
            "QUERY ERROR means the backend request failed, not an empty fleet."
        ),
        color={"mode": "fixed", "fixedColor": "#E5E7EB"},
    )
    defaults["custom"].update(
        minWidth=50, wrapText=False, cellOptions={"type": "auto", "wrapText": False}
    )
    links = {
        "Workflow": (
            "Workflow passport",
            "https://github.com/SatoryKono/BioactivityDataAcquisition/"
            "${__data.fields.workflow_passport_path:raw}",
        ),
        "Pipeline": (
            "Pipeline passport",
            "https://github.com/SatoryKono/BioactivityDataAcquisition/"
            "${__data.fields.pipeline_passport_path:raw}",
        ),
        "Run ID": (
            "Report \u00b7 ${__data.fields.run_id}",
            "${__data.fields.report_url:raw}",
        ),
        "Provider": (
            "Provider Evidence",
            "/d/bioetl-overview-v2/2-overview?" + _CONTEXT + "&viewPanel=9480",
        ),
        "Overview": ("Run Overview", "/d/bioetl-overview-v2/2-overview?" + _CONTEXT),
        "Saved Evidence": (
            "Saved Evidence",
            "/d/bioetl-control-plane-v1/1-trust?" + _CONTEXT + "&viewPanel=9418",
        ),
        "Data Quality": ("Data Quality", "/d/bioetl-dq-v2/5-data-quality?" + _CONTEXT),
        "Replay Readiness": (
            "Replay Readiness",
            "/d/bioetl-control-plane-v1/1-trust?" + _CONTEXT,
        ),
    }
    overrides: list[dict[str, Any]] = []
    for name, width, min_width in _COLUMNS.values():
        properties: list[dict[str, Any]] = [
            {"id": "custom.minWidth", "value": min_width},
            {
                "id": "custom.inspect",
                "value": name in {"Workflow", "Pipeline", "Run ID"},
            },
        ]
        if width is not None:
            properties.append({"id": "custom.width", "value": width})
        if name in links:
            title, url = links[name]
            link_items = [
                {
                    "title": title,
                    "url": url,
                    "includeVars": False,
                    "targetBlank": name in {"Workflow", "Pipeline", "Run ID"},
                }
            ]
            if name == "Run ID":
                link_items.insert(
                    0,
                    {
                        "title": "Select this run",
                        "url": _SELECT_RUN_URL,
                        "includeVars": False,
                        "targetBlank": False,
                    },
                )
            properties.append({"id": "links", "value": link_items})
        if name in {"Overview", "Saved Evidence", "Data Quality", "Replay Readiness"}:
            properties.extend(
                [
                    {
                        "id": "custom.cellOptions",
                        "value": {
                            "type": "color-text",
                            "mode": "basic",
                            "wrapText": False,
                        },
                    },
                    {
                        "id": "mappings",
                        "value": [
                            {
                                "type": "value",
                                "options": {
                                    s: {
                                        "text": s
                                        if s in {"OK", "N/A", "ERROR"}
                                        else s.lower(),
                                        "color": c,
                                    }
                                    for s, c in _COLORS.items()
                                },
                            }
                        ],
                    },
                ]
            )
        elif name in links:
            properties.append(
                {"id": "color", "value": {"mode": "fixed", "fixedColor": "#93C5FD"}}
            )
        if name == "Started":
            properties.append({"id": "unit", "value": "time:YY-MM-DD:HH:mm"})
        if name == "Workflow":
            properties.append(
                {
                    "id": "custom.cellOptions",
                    "value": {"type": "auto"},
                }
            )
        if name == "Duration":
            properties.append({"id": "noValue", "value": "UNKNOWN"})
        overrides.append(
            {"matcher": {"id": "byName", "options": name}, "properties": properties}
        )
    for name in hidden:
        overrides.append(
            {
                "matcher": {"id": "byName", "options": name},
                "properties": [{"id": "custom.hidden", "value": True}],
            }
        )
    overrides.append(
        {
            "matcher": {"id": "byName", "options": "status"},
            "properties": [
                {
                    "id": "mappings",
                    "value": [
                        {
                            "type": "value",
                            "options": {
                                s: {"text": s, "color": c} for s, c in _COLORS.items()
                            },
                        }
                    ],
                }
            ],
        }
    )
    panel["fieldConfig"]["overrides"] = overrides
    panel["options"]["sortBy"] = [{"displayName": "Started", "desc": True}]
    for item in panel.get("links") or []:
        if item.get("title") == "Browse all pipelines":
            item["url"] = _RESET_FILTERS


def _infinity_filter_query(url: str) -> dict[str, object]:
    return {
        "queryType": "infinity",
        "refId": "variable",
        "infinityQuery": {
            "format": "table",
            "parser": "backend",
            "root_selector": _FILTER_ROOT,
            "type": "json",
            "source": "url",
            "url_options": {"method": "GET", "data": ""},
            "url": url,
            "columns": [
                {"selector": "text", "text": "__text", "type": "string"},
                {"selector": "value", "text": "__value", "type": "string"},
            ],
        },
    }


def _http_filter_variable(
    *,
    name: str,
    label: str,
    url: str,
    description: str,
    include_all: bool = True,
    multi: bool = False,
    sort: int = 0,
) -> dict[str, object]:
    return {
        "allValue": ".*",
        "current": {"selected": True, "text": "All", "value": "$__all"},
        "datasource": _OPS_HTTP,
        "definition": url,
        "description": description,
        "hide": 0,
        "includeAll": include_all,
        "label": label,
        "multi": multi,
        "name": name,
        "options": [],
        "query": _infinity_filter_query(url),
        "refresh": 1,
        "regex": "",
        "skipUrlSync": False,
        "sort": sort,
        "tagValuesQuery": "",
        "tags": [],
        "tagsQuery": "",
        "type": "query",
        "useTags": False,
    }


def _apply_run_explorer_templating(payload: dict[str, Any]) -> None:
    variables = {item["name"]: item for item in payload["templating"]["list"]}
    variables["workflow"] = _http_filter_variable(
        name="workflow",
        label="Workflow",
        url="/ops/control-plane/filter-options?dimension=workflow&response_shape=options",
        description=(
            "Browse scope from the local control-plane catalog. Default All "
            "includes every workflow. Filters the recent-launches table."
        ),
        sort=1,
    )
    variables["pipeline"]["query"] = _infinity_filter_query(
        str(variables["pipeline"]["definition"])
    )
    variables["run_type"]["multi"] = False
    variables["run_type"]["query"] = _infinity_filter_query(
        str(variables["run_type"]["definition"])
    )
    variables["lookup_run_id"]["description"] = (
        "Exact UUID within the current Workflow/Pipeline/Run Type, including "
        "launches older than the latest ten. Does not replace Selected Run until "
        "a matching row is found. Clear to browse recent launches."
    )
    provider = variables.get("provider_for_pipeline")
    if provider is not None:
        provider["description"] = (
            "Hidden selector: provider for a concrete Pipeline. Unused when "
            "Pipeline is All ($__all / .*). Table Provider handoff uses the row field."
        )
    payload["templating"]["list"] = list(variables.values())


def main() -> int:
    """Refresh this scoped presentation without unrelated layout migrations."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    directory = Path(__file__).resolve().parents[4] / "grafana" / "dashboards"
    drift = False
    for path in sorted(directory.glob("*.json")):
        original = path.read_text(encoding="utf-8")
        payload = json.loads(original)
        apply_run_explorer_columns(payload)
        rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
        if args.check:
            if original != rendered:
                print(f"drift {path.name}")
                drift = True
        else:
            path.write_text(rendered, encoding="utf-8")
    return int(drift)


if __name__ == "__main__":
    raise SystemExit(main())
