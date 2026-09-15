"""Canonical opt-in aggregate-complete run discovery panel."""

from __future__ import annotations


def stamp_latest_complete_run_panel(panels: list[object]) -> None:
    """Keep expensive discovery collapsed and preserve history in a new tab."""
    panels[:] = [p for p in panels if not isinstance(p, dict) or p.get("id") != 9420]
    y = (
        max(
            (p.get("gridPos", {}).get("y", 0) for p in panels if isinstance(p, dict)),
            default=0,
        )
        + 1
    )
    panel = {
        "id": 9421,
        "type": "table",
        "title": "Inspect Latest Complete Run",
        "gridPos": {"x": 0, "y": y + 1, "w": 24, "h": 6},
        "datasource": "BioETL Ops HTTP",
        "description": (
            "Search the same workflow/pipeline/run_type, newest manifest first. "
            "Only processing success plus aggregate Trust OK qualifies. Search "
            "is bounded: INCOMPLETE means the scan limit, not no complete runs. "
            "Open a candidate in a new tab; this historical selection and time "
            "range remain unchanged. The link preserves the time range, so the "
            "candidate may be OUT OF RANGE. This is not replay authorization."
        ),
        "options": {"showHeader": True, "cellHeight": "sm"},
        "fieldConfig": {
            "defaults": {
                "noValue": "—",
                # Grafana's table auto-height reads the first string cell's
                # .length without a null guard when default wrapText is true.
                # Empty candidate identity must remain null, never a fake ID.
                "custom": {
                    "cellOptions": {"type": "auto", "wrapText": False},
                    "inspect": True,
                },
            },
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": "Candidate run"},
                    "properties": [
                        {
                            "id": "links",
                            "value": [
                                {
                                    "title": "Open aggregate-complete run",
                                    "url": "/d/bioetl-control-plane-v1/1-trust?${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}&var-run_id=${__value.raw}&${__url_time_range}",
                                    "targetBlank": True,
                                    "includeVars": False,
                                }
                            ],
                        }
                    ],
                },
                {
                    "matcher": {"id": "byName", "options": "Created at"},
                    "properties": [{"id": "unit", "value": "time:YYYY-MM-DD HH:mm"}],
                },
                {
                    "matcher": {"id": "byName", "options": "Reason"},
                    "properties": [
                        {
                            "id": "mappings",
                            "value": [
                                {
                                    "type": "value",
                                    "options": {
                                        "complete_run_scan_limit": {
                                            "text": "Search limit reached"
                                        },
                                        "no_complete_run_in_scope": {
                                            "text": "No complete run in scope"
                                        },
                                        "aggregate_complete_run_found": {
                                            "text": "Aggregate evidence complete"
                                        },
                                    },
                                }
                            ],
                        }
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
                "root_selector": "rows",
                "url": "/ops/control-plane/latest-complete-run?workflow=${workflow:csv}&pipeline=${pipeline}&run_type=${run_type:csv}&run_id=${run_id}&error_as_row=1",
                "url_options": {"method": "GET", "data": ""},
            }
        ],
        "transformations": [
            {
                "id": "convertFieldType",
                "options": {
                    "conversions": [
                        {"targetField": "observed_at", "destinationType": "time"}
                    ]
                },
            },
            {
                "id": "organize",
                "options": {
                    "indexByName": {
                        "status": 0,
                        "reason": 1,
                        "candidate_run_id": 2,
                        "observed_at": 3,
                        "pipeline": 4,
                        "run_type": 5,
                    },
                    "renameByName": {
                        "status": "Search",
                        "reason": "Reason",
                        "candidate_run_id": "Candidate run",
                        "observed_at": "Created at",
                        "pipeline": "Pipeline",
                        "run_type": "Run type",
                    },
                },
            },
        ],
    }
    panels.append(
        {
            "id": 9420,
            "type": "row",
            "title": "Inspect Complete Run Discovery",
            "collapsed": True,
            "gridPos": {"x": 0, "y": y, "w": 24, "h": 1},
            "panels": [panel],
        }
    )


__all__ = ["stamp_latest_complete_run_panel"]
