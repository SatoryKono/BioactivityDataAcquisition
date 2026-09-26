"""Canonical ten-column Run Explorer and dashboard display names."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.ops.observability.grafana._overall_verdict import apply_overall_verdict

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
    "workflow_id": ("Workflow", 120),
    "pipeline": ("Pipeline", 160),
    "provider": ("Provider", 85),
    "run_label": ("Run ID", 90),
    "started_at": ("Started", 115),
    "duration_display": ("Duration", 75),
    "status": ("Overview", 85),
    "saved_evidence_status": ("Saved Evidence", 120),
    "data_quality_status": ("Data Quality", 110),
    "replay_readiness_status": ("Replay Readiness", 125),
}
_CONTEXT = "var-workflow=${__data.fields.workflow_scope:percentencode}&var-pipeline=${__data.fields.Pipeline:percentencode}&var-run_type=${__data.fields.run_type:percentencode}&var-run_id=${__data.fields.run_id:percentencode}&${__url_time_range}"


def _rename_text(value: object) -> object:
    if isinstance(value, str):
        for old, new in _RENAMES.items():
            value = value.replace(old, new)
        return value
    if isinstance(value, list):
        return [_rename_text(item) for item in value]
    if isinstance(value, dict):
        return {key: _rename_text(item) for key, item in value.items()}
    return value


def apply_run_explorer_columns(payload: dict) -> None:
    """Run last so older readability passes cannot restore obsolete columns."""
    payload.update(_rename_text(payload))
    if payload.get("uid") in TITLES:
        payload["title"] = TITLES[payload["uid"]]
    apply_overall_verdict(payload)
    if payload.get("uid") != "bioetl-run-explorer-v1":
        return
    panels = {panel["id"]: panel for panel in payload["panels"]}
    panels[1]["gridPos"]["h"] = 2
    panels[1]["options"]["content"] = panels[1]["options"]["content"].replace(
        "Select a Run ID to view details.", "Select a status to view details."
    )
    panel = panels[3010]
    panel["gridPos"].update(y=2, h=14)
    panel["description"] = (
        "Last 10 launches, newest Started first, independent of the time range. "
        "Workflow and Pipeline open passports. Run ID opens the persisted Report; "
        "inspect its full UUID in the cell. Overview is processing status, not replay readiness. "
        "Saved Evidence, Data Quality and Replay Readiness use exact-run verified evidence. "
        "N/A means unsupported/legacy assessment. INCOMPLETE means missing required evidence. "
        "IN PROGRESS requires an explicit assessment queue/running signal and is never inferred. "
        "QUERY ERROR is a source failure; VALID EMPTY means no matching launches. "
        "Running is a recorded state, not proof of current liveness. Missing reports have no link."
    )
    hidden = [
        "run_id",
        "workflow_scope",
        "run_type",
        "report_url",
        "report_label",
        "workflow_passport_url",
        "pipeline_passport_url",
    ]
    names = [*_COLUMNS, *hidden]
    panel["targets"][0]["root_selector"] = (
        'index_state = "valid_empty" and $exists(items) and $count(items) = 0 ? [{"pipeline": "VALID EMPTY"}] : (items ~> | $ | {"duration_display": $replace(duration_display, /([0-9])\\s+([a-z])/, "$1$2")} |)'
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
                "excludeByName": {},
            },
        },
        {"id": "limit", "options": {"limitField": 10}},
    ]
    defaults = panel["fieldConfig"]["defaults"]
    defaults.update(noValue="N/A", color={"mode": "fixed", "fixedColor": "#E5E7EB"})
    defaults["custom"].update(
        minWidth=50, wrapText=False, cellOptions={"type": "auto", "wrapText": False}
    )
    links = {
        "Workflow": ("Workflow passport", "${__data.fields.workflow_passport_url:raw}"),
        "Pipeline": ("Pipeline passport", "${__data.fields.pipeline_passport_url:raw}"),
        "Run ID": (
            "Report Â· ${__data.fields.run_id}",
            "${__data.fields.report_url:raw}",
        ),
        "Provider": (
            "Provider Health",
            "/d/bioetl-provider-health-v2/4-provider-health?"
            + _CONTEXT
            + "&var-provider=${__data.fields.Provider:percentencode}",
        ),
        "Overview": ("Run Overview", "/d/bioetl-overview-v2/2-overview?" + _CONTEXT),
        "Saved Evidence": (
            "Saved Evidence",
            "/d/bioetl-runtime/3-pipeline-diagnostics?" + _CONTEXT,
        ),
        "Data Quality": ("Data Quality", "/d/bioetl-dq-v2/5-data-quality?" + _CONTEXT),
        "Replay Readiness": (
            "Replay Readiness",
            "/d/bioetl-control-plane-v1/1-trust?" + _CONTEXT,
        ),
    }
    overrides = []
    for name, width in _COLUMNS.values():
        properties = [
            {"id": "custom.width", "value": width},
            {"id": "custom.inspect", "value": name in {"Workflow", "Pipeline"}},
        ]
        if name in links:
            title, url = links[name]
            properties.append(
                {
                    "id": "links",
                    "value": [
                        {
                            "title": title,
                            "url": url,
                            "includeVars": False,
                            "targetBlank": name in {"Workflow", "Pipeline", "Run ID"},
                        }
                    ],
                }
            )
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
                                    s: {"text": s if s in {"OK", "N/A", "ERROR"} else s.lower(), "color": c}
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
                    "id": "mappings",
                    "value": [
                        {
                            "type": "value",
                            "options": {"â€”": {"text": "N/A", "color": "#9CA3AF"}},
                        }
                    ],
                }
            )
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
    panel["fieldConfig"]["overrides"] = overrides
    panel["options"]["sortBy"] = [{"displayName": "Started", "desc": True}]


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
