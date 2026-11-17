"""Expose application and publication clocks without fabricating event time."""

from __future__ import annotations


def stage_clock_query() -> str:
    """One row per threshold-crossing stage and clock; absent clocks stay NaN."""
    scope = (
        "group by(pipeline,run_type,stage)("
        "(max by(pipeline,run_type,stage)(max_over_time(bioetl_stage_lag_seconds[15m])) >= 300) or "
        '(max by(pipeline,run_type,stage)(bioetl_stage_backlog_records{stage!="validation"}) > 0))'
    )
    observed = "max by(pipeline,run_type,stage)((bioetl_stage_snapshot_observed_timestamp_seconds > 0) <= time())"
    published = 'max by(pipeline,run_type)((push_time_seconds{job="bioetl",pipeline!="",run_type!=""} > 0) <= time())'
    missing = f"({scope} * NaN)"
    clocks = (
        (
            "Latest stage projection",
            f"(({observed} and on(pipeline,run_type,stage) {scope}) or {missing})",
            "Application projection; not input-record event time",
        ),
        (
            "Gateway publication",
            f"(({scope} * on(pipeline,run_type) group_left {published}) or {missing})",
            "Pushgateway job=bioetl; not stage observation time",
        ),
        (
            "Input-record event",
            missing,
            "Not instrumented; no source event clock in these metrics",
        ),
    )
    rows = []
    for clock, expr, basis in clocks:
        expr = f'label_replace(({expr} * 1000),"clock","{clock}","","")'
        expr = f'label_replace({expr},"basis","{basis}","","")'
        rows.append(f'label_join({expr},"scope"," / ","pipeline","run_type","stage")')
    return " or ".join(f"({row})" for row in rows)


def add_stage_source_clocks(payload: dict) -> None:
    """Attach a bounded clock drilldown to the existing diagnostic row."""
    detail = {
        "id": 22012,
        "type": "table",
        "title": "Inspect Stage Snapshot Clocks",
        "description": (
            "GLOBAL / CURRENT · Same threshold-crossing pipeline / run type / stage scope as Signal Measurements. "
            "Stage lag is elapsed run time sampled when backlog is nonzero, not the age of the oldest source record; retained lag does not keep increasing. "
            "Latest stage projection is the application's latest snapshot clock, only when emitted; it does not date the selected 15m maximum, which may belong to an earlier projection. Gateway publication is the retained job=bioetl push time, not event, scrape or run-start time. "
            "Input-record event time is not instrumented. Missing, zero or future clocks remain UNKNOWN; a recent publication never fills a missing observation. "
            "Do not associate a newer backfill or an entity-level processing anchor with an old incremental stage snapshot. Dates use dashboard timezone. "
            "Legacy snapshots cannot establish their producing run or input-event freshness. Cause verification remains separate."
        ),
        "gridPos": {"x": 0, "y": 47, "w": 24, "h": 10},
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "targets": [
            {
                "refId": "A",
                "expr": stage_clock_query(),
                "instant": True,
                "range": False,
                "format": "table",
            }
        ],
        "transformations": [
            {
                "id": "organize",
                "options": {
                    "excludeByName": dict.fromkeys(
                        ("__name__", "pipeline", "run_type", "stage", "Time"), True
                    ),
                    "indexByName": {"scope": 0, "clock": 1, "Value": 2, "basis": 3},
                    "renameByName": {
                        "scope": "Scope",
                        "clock": "Clock",
                        "Value": "Recorded at",
                        "basis": "Basis",
                    },
                },
            }
        ],
        "fieldConfig": {
            "defaults": {
                "noValue": "UNKNOWN · not recorded",
                "unit": "none",
                "custom": {
                    "align": "left",
                    "minWidth": 50,
                    "wrapText": True,
                    "cellOptions": {"type": "auto", "wrapText": True},
                },
            },
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": name},
                    "properties": [{"id": "custom.width", "value": width}],
                }
                for name, width in (
                    ("Scope", 360),
                    ("Clock", 180),
                    ("Recorded at", 230),
                    ("Basis", 420),
                )
            ]
            + [
                {
                    "matcher": {"id": "byName", "options": "Recorded at"},
                    "properties": [
                        {"id": "unit", "value": "time:YYYY-MM-DD HH:mm"},
                        {
                            "id": "mappings",
                            "value": [
                                {
                                    "type": "special",
                                    "options": {
                                        "match": "null+nan",
                                        "result": {
                                            "text": "UNKNOWN · not recorded",
                                            "color": "gray",
                                        },
                                    },
                                }
                            ],
                        },
                    ],
                }
            ],
        },
        "options": {
            "showHeader": True,
            "cellHeight": "lg",
            "enablePagination": False,
            "footer": {"enablePagination": False},
        },
    }
    row = next(p for p in payload["panels"] if p["id"] == 2099)
    row["panels"] = [p for p in row["panels"] if p["id"] != 22012] + [detail]
    measurements = next(p for p in row["panels"] if p["id"] == 22011)
    measurements["links"] = [
        {
            "title": "Inspect stage snapshot clocks",
            "url": "/d/bioetl-incident-v1/5-incident-workspace?viewPanel=22012"
            "&${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}"
            "&${run_id:queryparam}&${__url_time_range}",
            "targetBlank": False,
        }
    ]
