"""First-screen provenance for automatic and explicit run selection (LA-12)."""

from __future__ import annotations

RUN_SELECTION_CONTEXT = (
    '($requested := "${run_id:percentencode}"; '
    "$auto := $requested in ['', '-', 'All', '$__all', '%24__all', '__all', '*', '%2A']; "
    "$hasRun := $type(run_id) = 'string' and run_id != '' and run_id != '-'; "
    "[{'_bioetl_frame':'selection_context', "
    "'context': $auto ? ($hasRun ? 'AUTO · latest run in scope' : "
    "(reason = 'no_runs_in_scope' ? 'NO RUN · empty scope' : 'Context unavailable')) "
    ": 'EXPLICIT · requested Run ID', "
    "'run_id': $type(run_id) = 'string' ? run_id : $requested, "
    "'execution_state': $type(execution_state) = 'string' and execution_state != '' "
    "? execution_state : 'UNKNOWN', "
    "'verdict': $type(verdict) = 'string' and verdict != '' ? verdict : 'UNKNOWN', "
    "'context_checked_at': $now()}])"
)


def _shift_children(panel: dict, delta: int) -> None:
    for child in panel.get("panels", []):
        child["gridPos"]["y"] += delta
        _shift_children(child, delta)


def stamp_run_selection_context(payload: dict) -> None:
    """Replace the old static scope banner; retain its identity and layout slot."""
    panel_id = {"bioetl-overview-v2": 99, "bioetl-dq-v2": 9400}.get(payload.get("uid"))
    if panel_id is None:
        return
    panel = next(p for p in payload["panels"] if p.get("id") == panel_id)
    grid = dict(panel["gridPos"])
    old_bottom = grid["y"] + grid["h"]
    delta = 5 - grid["h"]
    if payload["uid"] == "bioetl-dq-v2":
        for other in payload["panels"]:
            if other["gridPos"]["y"] >= old_bottom:
                other["gridPos"]["y"] += delta
                _shift_children(other, delta)
        # Accounting already paginates. Keep its row budget and all values;
        # the first page adapts to the space left by the context block.
        next(p for p in payload["panels"] if p["id"] == 9403)["gridPos"]["h"] = 6
    else:
        # Only the domains under the left-hand banner need to move. Preserve
        # the right-hand status/identity stack so all five identity rows fit.
        next(p for p in payload["panels"] if p["id"] == 9002)["gridPos"]["y"] = (
            grid["y"] + 5
        )
        next(p for p in payload["panels"] if p["id"] == 9002)["gridPos"]["h"] = 8
    if payload["uid"] == "bioetl-dq-v2":
        # Close the two-row gap left when accounting shrinks from eight to six.
        next(p for p in payload["panels"] if p["id"] == 9402)["gridPos"]["y"] = 18
        # Shift disclosure and its nested evidence together to follow identity.
        for other in payload["panels"]:
            if other["gridPos"]["y"] >= 23:
                other["gridPos"]["y"] -= 2
                _shift_children(other, -2)
    grid["h"] = 5
    panel.clear()
    panel.update(
        {
            "id": panel_id,
            "title": "Review Run Context",
            "type": "table",
            "gridPos": grid,
            "datasource": {"type": "datasource", "uid": "-- Dashboard --"},
            "description": (
                "SELECTED RUN · AUTO shows the latest run by start time in the current "
                "scope, including unfinished runs. EXPLICIT keeps the requested Run ID. "
                "Context checked at is this Grafana query evaluation time, not run "
                "start, browser click, server cache load or catalog freshness. Refresh "
                "re-evaluates the displayed context. UNKNOWN is missing evidence; request failure "
                "is Source unavailable. This context assesses that run only, not a fleet verdict. "
                "TIME RANGE telemetry never proves this run. Empty is a coverage gap, "
                "not a pass. Backend failure indicates an unavailable source and must "
                "not be interpreted as an empty successful response."
            ),
            "targets": [
                {
                    "refId": "A",
                    "panelId": 9002 if payload["uid"] == "bioetl-overview-v2" else 9406,
                    "withTransforms": False,
                    "datasource": {"type": "datasource", "uid": "-- Dashboard --"},
                }
            ],
            "options": {
                "showHeader": True,
                "cellHeight": "sm",
                "footer": {"show": False},
            },
            "fieldConfig": {
                "defaults": {
                    "noValue": "Not verified",
                    "custom": {
                        "align": "left",
                        "minWidth": 50,
                        "inspect": True,
                        "cellOptions": {"type": "auto", "wrapText": True},
                    },
                },
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "Context checked at"},
                        "properties": [
                            {"id": "unit", "value": "time:YYYY-MM-DD HH:mm"},
                        ],
                    }
                ],
            },
            "transformations": [
                {
                    "id": "filterByValue",
                    "options": {
                        "type": "include",
                        "match": "all",
                        "filters": [
                            {
                                "fieldName": "_bioetl_frame",
                                "config": {
                                    "id": "equal",
                                    "options": {"value": "selection_context"},
                                },
                            }
                        ],
                    },
                },
                {"id": "limit", "options": {"limitField": 1}},
                {
                    "id": "filterFieldsByName",
                    "options": {
                        "include": {
                            "names": [
                                "context",
                                "context_checked_at",
                            ]
                        }
                    },
                },
                {
                    "id": "convertFieldType",
                    "options": {
                        "conversions": [
                            {
                                "targetField": "context_checked_at",
                                "destinationType": "time",
                            }
                        ]
                    },
                },
                {
                    "id": "organize",
                    "options": {
                        "indexByName": {
                            "context": 0,
                            "context_checked_at": 1,
                        },
                        "renameByName": {
                            "context": "Context",
                            "context_checked_at": "Context checked at",
                        },
                    },
                },
            ],
            "links": [],
        }
    )
