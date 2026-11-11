"""First-screen provenance for automatic and explicit run selection (LA-12)."""

from __future__ import annotations


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
                "Resolved at is the server selection resolution time, retained on cache "
                "hits, not run start or browser click time. Refresh re-evaluates AUTO "
                "after the cache refresh. UNKNOWN is missing evidence; request failure "
                "is Source unavailable. This context is not a fleet verdict. "
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
                        "cellOptions": {"type": "auto", "wrapText": True},
                    },
                },
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "Resolved at"},
                        "properties": [
                            {"id": "unit", "value": "time:YYYY-MM-DD HH:mm"}
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
                                "run_id",
                                "execution_state",
                                "verdict",
                                "resolved_at",
                            ]
                        }
                    },
                },
                {
                    "id": "convertFieldType",
                    "options": {
                        "conversions": [
                            {"targetField": "resolved_at", "destinationType": "time"}
                        ]
                    },
                },
                {
                    "id": "organize",
                    "options": {
                        "indexByName": {
                            "context": 0,
                            "run_id": 1,
                            "execution_state": 2,
                            "verdict": 3,
                            "resolved_at": 4,
                        },
                        "renameByName": {
                            "context": "Context",
                            "run_id": "Run ID",
                            "execution_state": "Execution",
                            "verdict": "Verdict",
                            "resolved_at": "Resolved at",
                        },
                    },
                },
            ],
            "links": [],
        }
    )
