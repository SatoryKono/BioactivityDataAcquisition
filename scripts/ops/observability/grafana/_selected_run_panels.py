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
        "links": [
            {
                "title": "Open run in Run Explorer",
                "url": "/d/bioetl-run-explorer-v1/bioetl-run-explorer-v1?${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}&${run_id:queryparam}&${__url_time_range}",
                "targetBlank": False,
                "includeVars": False,
            },
        ],
    }


def _walk_panels(panels):
    for panel in panels:
        if isinstance(panel, dict):
            yield panel
            yield from _walk_panels(panel.get("panels", []))


def stamp_selected_run_panels(payload: dict[str, object]) -> None:
    """Replace selected-run summaries through the generator, keeping CURRENT distinct."""
    panels = payload.get("panels", [])
    uid = payload.get("uid")
    for panel in _walk_panels(panels):
        if not isinstance(panel, dict):
            continue
        if uid == "bioetl-control-plane-v1" and panel.get("id") == 9418:
            for target in panel.get("targets", []):
                target["url"] = STATUS_URL
                target["root_selector"] = "trust"
            panel["description"] = (
                DESCRIPTION
                + " Observed is the saved completion-time assessment. processing_status success does not imply trust_status OK."
            )
        if uid == "bioetl-overview-v2" and panel.get("id") in {
            9006,
            9003,
            9004,
            9005,
            9013,
        }:
            panel["description"] = str(panel.get("description", "")).replace(
                "as Review Domain Status", "as Review All Domain Status (CURRENT)"
            )
        if uid == "bioetl-control-plane-v1" and panel.get("id") == 9421:
            panel["description"] = (
                DESCRIPTION + " SELECTED RUN search: find an exact persisted identity."
            )
        if panel.get("title") == "Review Selected Run Summary":
            panel.update(
                _panel(
                    panel["id"],
                    "Review Selected Run Status",
                    panel["gridPos"],
                    domains=False,
                )
            )
        elif panel.get("title") == "Review Selected Run Status":
            panel.update(
                _panel(panel["id"], panel["title"], panel["gridPos"], domains=False)
            )
        if uid == "bioetl-overview-v2" and panel.get("id") == 9002:
            panel.update(
                _panel(
                    9002, "Review Selected Run Domains", panel["gridPos"], domains=True
                )
            )
        if uid == "bioetl-overview-v2" and panel.get("id") == 215:
            panel["title"] = "Review Current First Action"
            panel["description"] = (
                "CURRENT · Fresh pipeline/run_type telemetry only. "
                + str(panel.get("description", "")).removeprefix(
                    "CURRENT · Fresh pipeline/run_type telemetry only. "
                )
            )
    # A common expandable detail view avoids widening the first screen on narrow windows.
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
    details["transformations"] = []
    summary = _panel(
        9452,
        "Inspect Selected Run Identity",
        {"x": 0, "y": y + 11, "w": 24, "h": 6},
        domains=False,
    )
    summary["transformations"] = []
    panels.append(
        {
            "id": 9450,
            "type": "row",
            "title": "Inspect Saved Run Evidence",
            "collapsed": True,
            "gridPos": {"x": 0, "y": y, "w": 24, "h": 1},
            "panels": [deepcopy(summary), details],
        }
    )
