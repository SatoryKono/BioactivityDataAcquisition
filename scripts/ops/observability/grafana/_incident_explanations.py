"""Operator-facing context for global incident evidence tables."""

from __future__ import annotations

_WIDTH = "custom.width"
_NOT_PROVIDED = "Not provided"


def explain_incident(panels: dict[int, dict], override) -> None:
    """Keep global evidence and row navigation independent of selected history."""
    panels[9400]["options"]["content"] = (
        '<div style="padding:4px 10px;border-left:4px solid #6b7280;font-size:16px;line-height:1.2;white-space:normal;overflow-wrap:anywhere;max-width:96ch">GLOBAL · All pipelines · '
        "independent of selected Pipeline, Provider and Run ID. Suspects are not verified causes. Telemetry gaps are UNKNOWN.</div>"
    )
    panels[2001]["options"]["content"] = (
        '<div style="font-size:16px;line-height:1.2">Rule triggered; cause not confirmed. '
        "Open Pipeline Diagnostics via Action to verify. PENDING has not fired. "
        '<a href="/d/bioetl-incident-v1/6-incident-workspace?viewPanel=22011&from=${__from}&to=${__to}">'
        "Stage lag/backlog measurements</a>.</div>"
    )
    panels[32010]["title"] = "Browse Global Suspects"
    panels[32005]["title"] = "Browse Global Alerts"
    _explain_ranked_suspects(panels, override)
    _explain_global_alerts(panels, override)
    _measurements(panels)


def _explain_ranked_suspects(panels: dict[int, dict], override) -> None:
    for pid in (2010, 22010):
        panel = panels[pid]
        panel["title"] = (
            "Inspect Ranked Suspects"
            if pid == 2010
            else "Inspect Global Suspects (Full)"
        )
        if pid == 2010:
            panel["targets"][0]["expr"] = (
                "label_replace(label_replace(bioetl_incident_ranked_evidence,"
                '"object","$1","object","(.*) / $"),'
                '"route_pipeline",".*","pipeline","unknown")'
            )
        else:
            panel["targets"][0].pop("expr", None)
        panel["description"] = (
            "GLOBAL / TIME RANGE · All pipelines; independent of selected Pipeline, Provider and Run ID. "
            "Severity is rule urgency, not cause verification. UNVERIFIED means rule triggered; cause not confirmed. All rows use the same GLOBAL scope. "
            "Recording sample time is not event time. Missing telemetry remains UNKNOWN. "
            "Open Pipeline Diagnostics via Action to verify the source evidence."
            + (
                " Summary shows up to two rows; open all rows for complete evidence."
                if pid == 2010
                else ""
            )
        )
        override(panel, "Confidence", "displayName", "Cause verification")
        override(panel, "Confidence", _WIDTH, 155)
        override(panel, "Confidence", "noValue", "Not verified")
        override(
            panel,
            "Confidence",
            "mappings",
            [{"type": "value", "options": {"UNVERIFIED": {"text": "Not verified"}}}],
        )
        override(
            panel,
            "Action",
            "links",
            [
                {
                    "title": "Open domain diagnostics",
                    "url": "/d/${__data.fields.action_dashboard_uid}/${__data.fields.action_dashboard_uid}"
                    "?var-workflow=$__all&var-pipeline=${__data.fields.route_pipeline:percentencode}"
                    "&var-run_type=$__all&var-run_id=-&${__data.fields.action_scope}&from=${__from}&to=${__to}",
                    "targetBlank": False,
                    "includeVars": False,
                }
            ],
        )
        override(panel, "Signal", "links", [])
        panel["links"] = [
            link
            for link in panel.get("links", [])
            if link.get("title", "").startswith("Show all")
        ]
        panel["fieldConfig"]["defaults"]["links"] = []
        if pid == 2010:
            panel["links"] = [
                {
                    "title": "Show all rows and total (summary: up to 2)",
                    "url": "/d/bioetl-incident-v1/6-incident-workspace?viewPanel=22010&from=${__from}&to=${__to}",
                    "targetBlank": False,
                    "includeVars": False,
                }
            ]


def _explain_global_alerts(panels: dict[int, dict], override) -> None:
    for pid in (2005, 22005):
        panel = panels[pid]
        panel["title"] = (
            "Monitor Global Alerts" if pid == 2005 else "Monitor Global Alerts (Full)"
        )
        # Query-local presentation label also creates a field when every row
        # lacks provider; original ALERTS labels remain untouched.
        if pid == 2005:
            panel["targets"][0]["expr"] = (
                'label_replace(bioetl_incident_alert_priority,"provider",'
                f'"{_NOT_PROVIDED}","provider","^$")'
            )
        else:
            panel["targets"][0].pop("expr", None)
        panel["description"] = (
            "GLOBAL / CURRENT · All pipelines; independent of selected Pipeline, Provider and Run ID. "
            "Not provided means the alert has no provider attribute, not unknown provider health. "
            "FIRING and PENDING retain their original alert state."
        )
        override(panel, "provider", "noValue", _NOT_PROVIDED)
        override(panel, "provider", _WIDTH, 130)
        override(panel, "provider", "displayName", "Provider")
        override(panel, "pipeline", "displayName", "Pipeline")
        override(panel, "severity", "displayName", "Severity")


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
            "observation_time": _NOT_PROVIDED,
            "publication_time": _NOT_PROVIDED,
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
        "description": "GLOBAL / TIME RANGE · Exact runtime rule operands at the same query evaluation time. Lag uses a 15m maximum; backlog uses the latest non-validation sample. Validation backlog is a separate signal, validation_backlog; this table does not represent the BioETLStageBacklogActive alert window. Event and publication timestamps are not provided by these gauges: freshness and current run liveness cannot be verified. Persisted gauges can outlive a finished run or exporter restart. Evaluation time is not observation time. Empty successful result means no matching threshold crossings; query failures are errors.",
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
                    "excludeByName": dict.fromkeys(
                        (
                            "__name__",
                            "pipeline",
                            "run_type",
                            "stage",
                            "observation_time",
                            "publication_time",
                        ),
                        True,
                    ),
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
                        "Value": "Value",
                        "unit": "Unit",
                        "threshold": "Threshold",
                        "window": "Window",
                        "freshness": "Freshness",
                        "observation_time": "Observed",
                        "publication_time": "Published",
                        "Time": "Evaluated",
                        "scope": "Scope",
                    },
                },
            },
        ],
        "fieldConfig": {
            "defaults": {
                "noValue": _NOT_PROVIDED,
                "custom": {
                    "align": "left",
                    "minWidth": 50,
                    "inspect": True,
                    "cellOptions": {"type": "auto", "wrapText": True},
                },
            },
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": name},
                    "properties": [{"id": _WIDTH, "value": width}],
                }
                for name, width in (
                    ("Scope", 185),
                    ("Signal", 85),
                    ("Value", 75),
                    ("Unit", 75),
                    ("Threshold", 100),
                    ("Window", 90),
                    ("Freshness", 165),
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
                "matcher": {"id": "byName", "options": "Value"},
                "properties": [{"id": "decimals", "value": 3}],
            },
        ]
    )
    row = panels[2099]
    row["panels"] = [p for p in row["panels"] if p["id"] != 22011] + [detail]
