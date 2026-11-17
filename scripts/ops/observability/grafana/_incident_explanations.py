"""Operator-facing context for global incident evidence tables."""

from __future__ import annotations

from copy import deepcopy

_RECORDED_AT = "Recorded at"
_EVENT_FRESHNESS = "Event freshness"
_GLOBAL_CURRENT = "GLOBAL / CURRENT"
_GLOBAL_RANGE = "GLOBAL / TIME RANGE"
_OPERATOR_TIME_UNIT = "time:YYYY-MM-DD HH:mm"

_WIDTH = "custom.width"
_CELL_OPTIONS = "custom.cellOptions"
_CUSTOM_HIDDEN = "custom.hidden"
_NOT_PROVIDED = "Not provided"
_NOT_VERIFIED = "Not verified"
_SEE_RUNBOOK = "See runbook"
_CELL_NO_WRAP = {"type": "auto", "wrapText": False}


def _alert_provider_rows() -> str:
    """Enrich only missing providers with an unambiguous configured mapping."""
    metric = "bioetl_incident_alert_priority"
    infrastructure = f'{metric}{{provider="",pipeline="",alertname="BioETLDockerRuntimeProbeMissing"}}'
    missing = f'({metric}{{provider=""}} unless {infrastructure})'
    mapping = 'group by(pipeline,provider)(bioetl_workflow_pipeline_expected{pipeline!="",provider!="",provider!="unknown"} > 0)'
    unique = f"({mapping} and on(pipeline) (count by(pipeline)({mapping}) == 1))"
    return (
        f'({metric}{{provider!=""}} or '
        f"({missing} * on(pipeline) group_left(provider) {unique}) or "
        f"({missing} unless on(pipeline) {unique}) or "
        f'label_replace({infrastructure},"provider","N/A — Infrastructure","",""))'
    )


def explain_incident(panels: dict[int, dict], override) -> None:
    """Keep global evidence and row navigation independent of selected history."""
    panels[9400]["options"]["content"] = (
        '<div style="padding:4px 10px;border-left:4px solid #6b7280;font-size:16px;line-height:1.2;white-space:normal;overflow-wrap:anywhere;max-width:96ch">GLOBAL · All pipelines · '
        "independent of selected Pipeline, Provider and Run ID. Suspects are not verified causes. Telemetry gaps are UNKNOWN.</div>"
    )
    panels[2001]["description"] = (
        "The ranked suspect is the first answer. Cause is not confirmed. "
        "Fleet blockers and time-range charts are in Pipeline fleet and range "
        "on this page, not on Pipeline Diagnostics."
    )
    panels[2001]["options"]["content"] = (
        '<div style="font-size:16px;line-height:1.2">Rule triggered; cause not confirmed. '
        "Read the ranked suspect first. Fleet blockers and time-range charts are "
        "in Pipeline fleet and range on this page. PENDING has not fired. "
        '<a href="/d/bioetl-incident-v1/5-incident-workspace?viewPanel=22011'
        "&${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}"
        '&${run_id:queryparam}&${__url_time_range}">'
        "Stage lag/backlog measurements</a>.</div>"
    )
    for panel_id, description in (
        (
            2020,
            "Expand for alert state history and the impact note. "
            "These rows do not replace the ranked suspect.",
        ),
        (
            32010,
            "Expand for the full global suspect table. "
            "The first screen already shows the ranked subset.",
        ),
        (
            32005,
            "Expand for the full global alert table. "
            "The first screen already shows Monitor Global Alerts.",
        ),
        (
            9700,
            "Expand for current workflow evidence. "
            "This table is not the selected Run ID verdict.",
        ),
    ):
        row = panels.get(panel_id)
        if isinstance(row, dict):
            row["description"] = description
    panels[32010]["title"] = "Browse Global Suspects"
    panels[32005]["title"] = "Browse Global Alerts"
    _explain_ranked_suspects(panels, override)
    _explain_global_alerts(panels, override)
    _measurements(panels)


def _set_field_hidden(panel: dict, field: str, *, hidden: bool, override) -> None:
    """Replace any existing custom.hidden property for ``field``."""
    overrides = panel.get("fieldConfig", {}).get("overrides", [])
    field_override = next(
        (o for o in overrides if o.get("matcher", {}).get("options") == field),
        None,
    )
    if field_override is None:
        override(panel, field, _CUSTOM_HIDDEN, hidden)
        return
    props = field_override.get("properties", [])
    props[:] = [p for p in props if p.get("id") != _CUSTOM_HIDDEN]
    props.append({"id": _CUSTOM_HIDDEN, "value": hidden})


def _configure_confidence(panel: dict, override) -> None:
    override(panel, "Confidence", "displayName", "Cause verification")
    override(panel, "Confidence", _WIDTH, 155)
    override(panel, "Confidence", "noValue", _NOT_VERIFIED)
    override(
        panel,
        "Confidence",
        _CELL_OPTIONS,
        {"type": "color-text", "wrapText": False},
    )
    override(
        panel,
        "Confidence",
        "mappings",
        [
            {
                "type": "value",
                "options": {
                    "UNVERIFIED": {"text": _NOT_VERIFIED},
                    "UNVERIFIED_STALE": {"text": _NOT_VERIFIED, "color": "orange"},
                },
            }
        ],
    )


def _configure_owner_next_step(panel: dict, override) -> None:
    for field, display in (("owner", "Owner"), ("next_step", "Next step")):
        override(panel, field, "displayName", display)
        override(panel, field, "noValue", _SEE_RUNBOOK)
        override(panel, field, _CELL_OPTIONS, dict(_CELL_NO_WRAP))
        _set_field_hidden(panel, field, hidden=False, override=override)


def _configure_ranked_action(panel: dict, override) -> None:
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


def _ranked_suspect_description(*, summary: bool) -> str:
    text = (
        "GLOBAL / TIME RANGE · All pipelines; independent of selected Pipeline, Provider and Run ID. "
        "Severity is rule urgency, not cause verification. UNVERIFIED means rule triggered; cause not confirmed. All rows use the same GLOBAL scope. "
        "Recording sample time is not event time. Missing telemetry remains UNKNOWN. "
        "Action opens the domain page named on the row. "
        "Fleet charts for pipeline signals stay on this page."
    )
    if summary:
        return (
            text + " Summary shows up to two rows; open all rows for complete evidence."
        )
    return text


_NAMED_ALERT_RUNBOOKS = (
    ("BioETLPipelineInfrastructureValidationFailed", "pipeline-failure-critical"),
    ("BioETLDataFreshnessLagCritical", "pipeline-failure-dq"),
)


def _stamp_named_alert_runbooks(expr: str) -> str:
    """Point the two critical alerts at their own runbook, owner and next step."""
    for alertname, stem in _NAMED_ALERT_RUNBOOKS:
        expr = (
            f'label_replace({expr},"alert_runbook","{stem}","alertname","{alertname}")'
        )
    return (
        "label_replace(label_replace(label_replace("
        f'{expr},"owner","BioETL Team","alertname",'
        '"BioETLPipelineInfrastructureValidationFailed|BioETLDataFreshnessLagCritical"),'
        '"next_step","Open pipeline-failure-critical.md","alertname",'
        '"BioETLPipelineInfrastructureValidationFailed"),'
        '"next_step","Open pipeline-failure-dq.md","alertname",'
        '"BioETLDataFreshnessLagCritical")'
    )


def _stamp_ranked_suspect_expr(panel: dict, *, summary: bool) -> None:
    if not summary:
        # Legacy Dashboard-DS consumers inherit their donor. CURRENT detail
        # consumers deliberately own the same query at their own current clock.
        if "panelId" in panel["targets"][0]:
            panel["targets"][0].pop("expr", None)
        return
    panel["targets"][0]["expr"] = (
        "label_replace(label_replace(label_replace(label_replace(label_replace(label_replace(label_replace("
        "bioetl_incident_ranked_evidence,"
        '"object","$1","object","(.*) / $"),'
        '"route_pipeline",".*","pipeline","unknown"),'
        '"owner","BioETL Team","reason","infrastructure_failed"),'
        '"next_step","Open pipeline-failure-critical.md","reason","infrastructure_failed"),'
        '"owner","See runbook","owner","^$"),'
        '"next_step","See runbook","next_step","^$"),'
        '"freshness","Not verified: no event timestamp","","")'
    )


def _explain_ranked_suspects(panels: dict[int, dict], override) -> None:
    for pid in (2010, 22010):
        panel = panels[pid]
        summary = pid == 2010
        panel["title"] = (
            "Inspect Ranked Suspects" if summary else "Inspect Global Suspects (Full)"
        )
        _stamp_ranked_suspect_expr(panel, summary=summary)
        panel["description"] = _ranked_suspect_description(summary=summary)
        _configure_confidence(panel, override)
        _configure_owner_next_step(panel, override)
        _configure_ranked_action(panel, override)
        if summary:
            panel["links"] = [
                {
                    "title": "Show all rows and total (summary: up to 2)",
                    "url": "/d/bioetl-incident-v1/5-incident-workspace?viewPanel=22010&from=${__from}&to=${__to}",
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
            # A temporary label guards the presentation rewrite on both name
            # and empty pipeline; provider identifiers remain unchanged.
            scoped = f'label_join({_alert_provider_rows()},"pipeline_context",";","alertname","pipeline")'
            scoped = f'label_replace({scoped},"pipeline","N/A — Docker infrastructure","pipeline_context","BioETLDockerRuntimeProbeMissing;")'
            panel["targets"][0]["expr"] = (
                f'label_replace(label_replace(({scoped}),"pipeline",'
                f'"{_NOT_PROVIDED}","pipeline","^$"),"provider",'
                f'"{_NOT_PROVIDED}","provider","^$")'
            )
            expr = panel["targets"][0]["expr"]
            panel["targets"][0]["expr"] = _stamp_named_alert_runbooks(
                f'label_replace(label_replace({expr},"alert_runbook",'
                '"incident-response","",""),"alert_runbook","docker-stability",'
                '"alertname","BioETLDockerRuntimeProbeMissing")'
            )
        else:
            panel["targets"][0].pop("expr", None)
        panel["description"] = (
            "GLOBAL / CURRENT · All pipelines; independent of selected Pipeline, Provider and Run ID. "
            "Provider preserves the alert label or uses an unambiguous configured pipeline mapping. Not provided means missing or ambiguous attribution, not unknown provider health. N/A — Infrastructure is not a provider. "
            "Pipeline: N/A — Docker infrastructure for the Docker probe alert without a pipeline label; Not provided for other alerts without that label. "
            "FIRING and PENDING retain their original alert state."
        )
        override(panel, "provider", "noValue", _NOT_PROVIDED)
        override(panel, "provider", _WIDTH, 190)
        override(panel, "provider", "displayName", "Provider")
        override(
            panel,
            "provider",
            "mappings",
            [{"type": "value", "options": {"chembl": {"text": "ChEMBL"}}}],
        )
        override(panel, "pipeline_context", _CUSTOM_HIDDEN, True)
        override(panel, "pipeline", "displayName", "Pipeline")
        override(panel, "pipeline", "noValue", _NOT_PROVIDED)
        override(panel, "pipeline", "links", [])
        override(panel, "alert_runbook", _CUSTOM_HIDDEN, True)
        override(panel, "owner", "displayName", "Owner")
        override(panel, "owner", "noValue", _SEE_RUNBOOK)
        override(panel, "next_step", "displayName", "Next step")
        override(panel, "next_step", "noValue", _SEE_RUNBOOK)
        override(
            panel,
            "alertname",
            "links",
            [
                {
                    "title": "Open alert runbook",
                    "url": "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/docs/05-operations/runbooks/${__data.fields.alert_runbook}.md",
                    "targetBlank": True,
                }
            ],
        )
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
            "freshness": f"{_NOT_VERIFIED}: observed/published timestamps not provided",
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
                "unit": "none",
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
                "datasource": {"type": "prometheus", "uid": "prometheus"},
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
                        "Value": _RECORDED_AT,
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
                    "inspect": True,
                    "wrapText": True,
                    "cellOptions": {"type": "auto", "wrapText": True},
                },
            },
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": name},
                    "properties": [{"id": _WIDTH, "value": width}],
                }
                for name, width in (
                    ("Scope", 360),
                    ("Clock", 180),
                    (_RECORDED_AT, 230),
                    ("Basis", 420),
                )
            ]
            + [
                {
                    "matcher": {"id": "byName", "options": _RECORDED_AT},
                    "properties": [
                        {"id": "unit", "value": _OPERATOR_TIME_UNIT},
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
            "enablePagination": True,
            "footer": {"enablePagination": True},
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
            "includeVars": False,
        }
    ]


def preserve_evidence_rows(panel: dict) -> None:
    panel["transformations"] = [
        item for item in panel.get("transformations", []) if item["id"] != "limit"
    ]
    panel["options"].setdefault("footer", {})["enablePagination"] = True


def _explain_missing_samples(items: list[dict]) -> None:
    for item in items:
        if item["id"] == 9991:
            item["options"]["content"] = (
                '<div style="font-size:16px;line-height:20px">UNKNOWN means no matching samples or an unpublished reason. Check Observability Signals and <a href="/d/bioetl-incident-v1/5-incident-workspace?viewPanel=2461&amp;${workflow:queryparam}&amp;${pipeline:queryparam}&amp;${run_type:queryparam}&amp;${__url_time_range}">missing stage signals</a>. Query time is not event time.</div>'
            )
        if item.get("type") in {"stat", "gauge", "bargauge"}:
            item.setdefault("fieldConfig", {}).setdefault("defaults", {})["noValue"] = (
                "UNKNOWN · no samples"
            )
        if item["id"] in {9996, 9997}:
            item["description"] = item["description"].replace(
                ", including when an empty selected-range result is rendered through noValue",
                " in observed counter samples; missing samples remain UNKNOWN",
            )
        _explain_missing_samples(item.get("panels", []))


def _urgency_label(panel: dict) -> None:
    """Change the display label while retaining the canonical Severity field."""
    matches = [
        o
        for o in panel["fieldConfig"]["overrides"]
        if o.get("matcher", {}).get("options") in {"Severity", "Signal urgency"}
    ]
    properties = {p["id"]: p for override in matches for p in override["properties"]}
    properties["displayName"] = {"id": "displayName", "value": "Diagnostic priority"}
    # Ranked-runtime rules encode failing=2 / degraded=1. These are ranking
    # scores, not the warning/critical severity labels on ALERTS. In particular,
    # a 300s stage lag produces a warning alert, not a verified critical cause.
    properties["mappings"] = {
        "id": "mappings",
        "value": [
            {
                "type": "value",
                "options": {
                    "0": {"text": "UNKNOWN", "color": "gray"},
                    "1": {"text": "ELEVATED", "color": "orange"},
                    "2": {"text": "HIGH", "color": "red"},
                },
            }
        ],
    }
    normalized = {
        "matcher": {"id": "byName", "options": "Severity"},
        "properties": [properties[key] for key in sorted(properties)],
    }
    kept = [o for o in panel["fieldConfig"]["overrides"] if o not in matches]
    kept.insert(1, normalized)
    kept = [o for o in kept if o.get("matcher", {}).get("options") != _EVENT_FRESHNESS]
    kept.append(
        {
            "matcher": {"id": "byName", "options": _EVENT_FRESHNESS},
            "properties": [
                {"id": "custom.hidden", "value": False},
                {"id": _WIDTH, "value": 140},
                {
                    "id": "mappings",
                    "value": [
                        {
                            "type": "value",
                            "options": {
                                "Not verified: no event timestamp": {
                                    "text": "UNKNOWN · no event time"
                                }
                            },
                        }
                    ],
                },
                {
                    "id": _CELL_OPTIONS,
                    "value": {"type": "auto", "wrapText": True},
                },
            ],
        }
    )
    panel["fieldConfig"]["overrides"] = kept
    for item in panel.get("transformations", []):
        if item["id"] == "organize":
            item["options"]["renameByName"].update(
                Value="Severity", freshness=_EVENT_FRESHNESS
            )
            order = item["options"]["indexByName"]
            fields = [
                name for name in sorted(order, key=order.get) if name != "freshness"
            ]
            fields.insert(fields.index("confidence") + 1, "freshness")
            item["options"]["indexByName"] = {
                name: index for index, name in enumerate(fields)
            }


def apply_incident_evidence_clocks(payload, panels):
    """Retain every current suspect and explain missing event clocks and samples."""
    add_stage_source_clocks(payload)
    for item in _walk_panels(payload["panels"]):
        if item["id"] in {907, 893}:
            item["description"] = item["description"].replace(
                "TIME RANGE · CURRENT", "CURRENT"
            )
        elif item["id"] == 2460:
            _configure_stage_progress(item)
        elif item["id"] == 8807:
            item["description"] = item["description"].replace(
                "CURRENT · TIME RANGE", "TIME RANGE"
            )
        elif item["id"] == 22011:
            _configure_current_measurements(item)
    suspect = panels[2010]
    _stamp_ranked_suspect_expr(suspect, summary=True)
    organize = next(t for t in suspect["transformations"] if t["id"] == "organize")
    organize["options"]["renameByName"]["freshness"] = _EVENT_FRESHNESS
    _urgency_label(suspect)
    preserve_evidence_rows(suspect)
    suspect["description"] = (
        suspect["description"]
        .replace(_GLOBAL_RANGE, _GLOBAL_CURRENT)
        .replace(
            "Summary shows up to two rows; open all rows for complete evidence.",
            "All returned suspects remain available through pagination; the row count includes every suspect. Severity is retained even when cause and event freshness are Not verified.",
        )
    )
    suspect["links"][0]["title"] = "Open all suspects (no row truncation)"
    suspect["description"] += (
        " Diagnostic priority HIGH=2 / ELEVATED=1 is ranking, not Prometheus alert severity. "
        "Neither this rank nor FIRING verifies a cause or an event timestamp."
    )
    preserve_evidence_rows(panels[2005])
    panels[2005]["links"][0]["title"] = "Open all global alerts (no row truncation)"
    fleet = panels.get(8808)
    if fleet:
        _explain_missing_samples(fleet.get("panels", []))
    _configure_incident_detail_rows(payload["panels"], suspect)


def _walk_panels(items):
    for item in items:
        yield item
        yield from _walk_panels(item.get("panels", []))


def _configure_stage_progress(item: dict) -> None:
    preserve_evidence_rows(item)
    # Direct Grafana 13 table rendering uses the top-level option;
    # retain the legacy footer option for native dashboard migration.
    item["options"]["enablePagination"] = True
    item["options"]["sortBy"] = [{"displayName": "Lag", "desc": True}]
    item["description"] = item["description"].replace(
        "CURRENT stage snapshots and TIME RANGE-independent 5m throughput.",
        "CURRENT · Stage snapshots and fixed 5m throughput; the historical dashboard range does not set this clock.",
    )
    item["description"] = item["description"].replace(
        "Maximum observed value per stage across selected run types; inspect one Run Type for exact values.",
        "One row per observed pipeline / run type / stage. All returned groups remain available through pagination, sorted by lag; missing measures stay UNKNOWN. Inspect Selected Run separately for exact-run evidence.",
    )


def _configure_current_measurements(item: dict) -> None:
    # This drilldown explains the CURRENT ranked answer. It must not
    # evaluate its 15m operands at a historical dashboard end.
    item["description"] = item["description"].replace(_GLOBAL_RANGE, _GLOBAL_CURRENT)
    item["description"] = item["description"].replace(
        "Event and publication timestamps are not provided by these gauges: freshness and current run liveness cannot be verified.",
        "Lag is elapsed run time sampled when backlog is nonzero, not input-record event age. Inspect Stage Snapshot Clocks for application observation and Pushgateway publication; legacy observation and source-event times remain UNKNOWN.",
    )
    item["fieldConfig"]["defaults"]["custom"]["wrapText"] = True
    widths = {
        "Scope": 320,
        "Signal": 140,
        "Value": 90,
        "Unit": 90,
        "Threshold": 220,
        "Window": 140,
        "Freshness": 130,
        "Evaluated": 160,
    }
    for override in item["fieldConfig"]["overrides"]:
        field = override.get("matcher", {}).get("options")
        if field in widths:
            for prop in override["properties"]:
                if prop["id"] == _WIDTH:
                    prop["value"] = widths[field]
        if field == "Evaluated":
            override["properties"].append({"id": "unit", "value": _OPERATOR_TIME_UNIT})
    item["fieldConfig"]["overrides"].append(
        {
            "matcher": {"id": "byName", "options": "Freshness"},
            "properties": [
                {
                    "id": "mappings",
                    "value": [
                        {
                            "type": "value",
                            "options": {
                                "Not verified: observed/published timestamps not provided": {
                                    "text": _NOT_VERIFIED
                                }
                            },
                        }
                    ],
                }
            ],
        }
    )


def _configure_incident_detail_rows(rows: list[dict], suspect: dict) -> None:
    for row in rows:
        for child in row.get("panels", []):
            if child["id"] == 9701:
                child["links"] = [
                    {
                        "title": "Inspect current workflow evidence",
                        "url": "/d/bioetl-incident-v1/5-incident-workspace?viewPanel=9701&${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}&${__url_time_range}",
                        "targetBlank": False,
                        "includeVars": False,
                    }
                ]
            if child["id"] == 22010:
                child["datasource"] = deepcopy(suspect["datasource"])
                child["targets"] = deepcopy(suspect["targets"])
                child["description"] = child["description"].replace(
                    _GLOBAL_RANGE, _GLOBAL_CURRENT
                )
                _urgency_label(child)
