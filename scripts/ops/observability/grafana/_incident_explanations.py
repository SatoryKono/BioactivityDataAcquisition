"""Operator-facing context for global incident evidence tables."""

from __future__ import annotations


def explain_incident(panels: dict[int, dict], override) -> None:
    """Keep global evidence and row navigation independent of selected history."""
    panels[9400]["options"]["content"] = (
        '<div style="font-size:16px;line-height:1.2">GLOBAL · All pipelines · '
        "independent of selected Pipeline, Provider and Run ID.</div>"
    )
    panels[2001]["options"]["content"] = (
        '<div style="font-size:16px;line-height:1.2">Rule triggered; cause not confirmed. '
        "Open Action to verify. PENDING has not fired. "
        '<a href="/d/bioetl-incident-v1/6-incident-workspace?viewPanel=22011&from=${__from}&to=${__to}">'
        "Stage lag/backlog measurements</a>.</div>"
    )
    for pid in (2010, 22010):
        panel = panels[pid]
        panel["title"] = "Inspect Global Suspects"
        panel["targets"][0]["expr"] = (
            "label_replace(label_replace(bioetl_incident_ranked_evidence,"
            '"object","$1","object","(.*) / $"),'
            '"route_pipeline",".*","pipeline","unknown")'
        )
        panel["description"] = (
            "GLOBAL · All pipelines; independent of selected Pipeline, Provider and Run ID. "
            "Severity is rule urgency, not cause verification. Rule triggered; cause not confirmed. "
            "Recording sample time is not event time. Missing telemetry remains UNKNOWN. "
            "Summary shows up to two rows; open all rows for complete evidence."
        )
        override(panel, "Confidence", "displayName", "Cause verification")
        override(panel, "Confidence", "custom.width", 155)
        override(panel, "Confidence", "noValue", "Not verified")
        override(
            panel,
            "Confidence",
            "mappings",
            [{"type": "value", "options": {"UNVERIFIED": {"text": "Not verified"}}}],
        )
        panel["fieldConfig"]["defaults"]["links"] = []
        override(
            panel,
            "Action",
            "links",
            [
                {
                    "title": "Verify this object's evidence",
                    "url": "/d/${__data.fields.action_dashboard_uid}/${__data.fields.action_dashboard_uid}"
                    "?var-workflow=$__all&var-pipeline=${__data.fields.route_pipeline:percentencode}"
                    "&var-run_type=$__all&var-run_id=-&${__data.fields.action_scope}&from=${__from}&to=${__to}",
                    "targetBlank": False,
                    "includeVars": False,
                }
            ],
        )
        override(panel, "Signal", "links", [])
    for pid in (2005, 22005):
        panel = panels[pid]
        panel["title"] = "Monitor Global Alerts"
        # Query-local presentation label also creates a field when every row
        # lacks provider; original ALERTS labels remain untouched.
        panel["targets"][0]["expr"] = (
            'label_replace(bioetl_incident_alert_priority,"provider",'
            '"Not provided","provider","^$")'
        )
        panel["description"] = (
            "GLOBAL · All pipelines; independent of selected Pipeline, Provider and Run ID. "
            "Not provided means the alert has no provider attribute, not unknown provider health. "
            "FIRING and PENDING retain their original alert state."
        )
        override(panel, "provider", "noValue", "Not provided")
        override(panel, "provider", "custom.width", 130)
        override(panel, "provider", "displayName", "Provider")
        override(panel, "pipeline", "displayName", "Pipeline")
        override(panel, "severity", "displayName", "Severity")
    _measurements(panels)


def _measurements(panels: dict[int, dict]) -> None:
    """Retain stage and show the exact operands used by the runtime rules."""
    targets = []
    for ref, metric, signal, window, comparator, threshold, unit in (
        (
            "A",
            "max_over_time(bioetl_stage_lag_seconds[15m])",
            "stage_lag",
            "15m maximum",
            ">=",
            "300",
            "s",
        ),
        (
            "B",
            'bioetl_stage_backlog_records{stage!="validation"}',
            "stage_backlog",
            "instant",
            ">",
            "0",
            "records",
        ),
    ):
        expr = f"max by (pipeline, run_type, stage) ({metric}) {comparator} {threshold}"
        for label, value in {
            "signal": signal,
            "window": window,
            "threshold": f"{comparator} {threshold} {unit} ({window})",
            "unit": unit,
            "observation_time": "Not provided",
            "publication_time": "Not provided",
            "freshness": "Not verified: observed/published timestamps not provided",
        }.items():
            expr = f'label_replace({expr},"{label}","{value}","","")'
        targets.append(
            {
                "refId": ref,
                "expr": f'label_join({expr},"scope"," / ","pipeline","run_type","stage")',
                "instant": True,
                "range": False,
                "format": "table",
            }
        )
    detail = {
        "id": 22011,
        "type": "table",
        "title": "Inspect Global Signal Measurements",
        "description": "GLOBAL · Exact runtime rule operands at the same query evaluation time. Lag uses a 15m maximum; backlog uses the latest sample. Event and publication timestamps are not provided by these gauges: freshness and current run liveness cannot be verified. Persisted gauges can outlive a finished run or exporter restart. Evaluation time is not observation time. Empty successful result means no matching threshold crossings; query failures are errors.",
        "gridPos": {"x": 0, "y": 37, "w": 24, "h": 10},
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "targets": [
            {**targets[0], "expr": " or ".join(f"({t['expr']})" for t in targets)}
        ],
        "transformations": [
            {"id": "merge", "options": {}},
            {
                "id": "organize",
                "options": {
                    "excludeByName": dict.fromkeys(("__name__", "pipeline", "run_type", "stage", "window", "observation_time", "publication_time"), True),
                    "indexByName": {
                        "scope": 0,
                        "signal": 3,
                        "Value": 4,
                        "unit": 5,
                        "threshold": 6,
                        "window": 7,
                        "freshness": 8,
                        "observation_time": 9,
                        "publication_time": 10,
                        "Time": 11,
                    },
                    "renameByName": {
                        "pipeline": "Pipeline",
                        "run_type": "Run type",
                        "stage": "Stage",
                        "signal": "Signal",
                        "Value": "Measured",
                        "unit": "Unit",
                        "threshold": "Threshold",
                        "window": "Window",
                        "freshness": "Freshness",
                        "observation_time": "Observed",
                        "publication_time": "Published",
                        "Time": "Evaluated",
                        "scope": "Pipeline / Run type / Stage",
                    },
                },
            },
        ],
        "fieldConfig": {
            "defaults": {
                "noValue": "Not provided",
                "custom": {
                    "align": "left",
                    "inspect": True,
                    "cellOptions": {"type": "auto", "wrapText": True},
                },
            },
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": name},
                    "properties": [{"id": "custom.width", "value": width}],
                }
                for name, width in (
                    ("Pipeline / Run type / Stage", 205),
                    ("Signal", 100),
                    ("Measured", 85),
                    ("Unit", 65),
                    ("Threshold", 140),
                    ("Freshness", 190),
                    ("Evaluated", 160),
                )
            ],
        },
        "options": {
            "showHeader": True,
            "cellHeight": "lg",
            "footer": {"enablePagination": True},
        },
    }
    detail["fieldConfig"]["overrides"].extend(
        [
            {
                "matcher": {"id": "byName", "options": "Signal"},
                "properties": [
                    {
                        "id": "mappings",
                        "value": [
                            {
                                "type": "value",
                                "options": {
                                    "stage_lag": {"text": "Stage lag"},
                                    "stage_backlog": {"text": "Stage backlog"},
                                },
                            }
                        ],
                    }
                ],
            },
            {
                "matcher": {"id": "byName", "options": "Measured"},
                "properties": [{"id": "decimals", "value": 3}],
            },
        ]
    )
    row = panels[2099]
    row["panels"] = [p for p in row["panels"] if p["id"] != 22011] + [detail]
