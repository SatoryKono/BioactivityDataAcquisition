"""Keep saved outcomes, current alerts and evidence clocks distinct."""

from __future__ import annotations
from copy import deepcopy

from scripts.ops.observability.grafana._stage_source_clocks import (
    add_stage_source_clocks,
)


def _remove_row_limit(panel: dict) -> None:
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
        _explain_missing_samples(item.get("panels", []))


def _provider_card(panels):
    """Show a skipped probe reason without inventing a provider observation time."""
    provider = panels[9481]
    provider["type"] = "canvas"
    provider["options"] = deepcopy(panels[9482]["options"])
    elements = provider["options"]["root"]["elements"]
    for element, field, top, height, size in (
        (elements[0], "check_result_display", 4, 46, 28),
        (elements[1], "provider_check_note", 54, 78, 16),
    ):
        element["config"]["text"]["field"] = field
        element["config"]["color"]["field"] = "check_result_display"
        element["config"]["size"] = size
        element["placement"].update(top=top, height=height)
    provider["transformations"] = [
        item
        for item in provider["transformations"]
        if item["id"] != "filterFieldsByName"
    ] + [
        {
            "id": "filterFieldsByName",
            "options": {
                "include": {"names": ["check_result_display", "provider_check_note"]}
            },
        }
    ]
    provider["description"] += (
        " The visible note distinguishes a deliberately skipped provider probe from absent evidence; only the recorded provider observation is labelled Probe time. Run completion is not probe time."
    )


def _fleet_alert_card(panels):
    """Count active alerts, allowing empty zero only with an observed healthy Prometheus scrape; zero never certifies pipeline health."""
    targets = []
    for ref, state in (("A", "firing"), ("B", "pending")):
        targets.append(
            {
                "refId": ref,
                "instant": True,
                "format": "time_series",
                "legendFormat": state.upper(),
                "expr": f'((count(ALERTS{{alertname=~"BioETL.*",alertstate="{state}"}}) or vector(0)) and on() (max(up{{job="prometheus"}}) == 1))',
                "datasource": {"type": "prometheus", "uid": "prometheus"},
            }
        )
    health = {
        "id": 9605,
        "type": "stat",
        "title": "Review Current Fleet Alerts",
        "gridPos": {"x": 5, "y": 2, "w": 5, "h": 3},
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "targets": targets,
        "transformations": [],
        "description": "GLOBAL / CURRENT · Counts of BioETL FIRING and PENDING alerts, independent of Selected Run and all selectors. FIRING has satisfied the rule's for duration; PENDING has not. A saved SUCCESS/OK never clears these counts. A valid zero means no active alerts, not verified pipeline health. Missing Prometheus scrape or request failure is UNKNOWN/source unavailable. Zero fallback is valid only for this active-alert count, guarded by up{job=prometheus}=1. Refreshes every 30s.",
        "fieldConfig": {
            "defaults": {
                "unit": "short",
                "decimals": 0,
                "noValue": "UNKNOWN",
                "color": {"mode": "thresholds"},
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "text", "value": None},
                        {"color": "orange", "value": 1},
                    ],
                },
            },
            "overrides": [],
        },
        "options": {
            "colorMode": "value",
            "graphMode": "none",
            "textMode": "value_and_name",
            "orientation": "horizontal",
            "text": {"valueSize": 24, "titleSize": 14},
            "reduceOptions": {"calcs": ["last"], "fields": "", "values": False},
        },
        "links": deepcopy(panels[2005]["links"]),
    }
    return health


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
    kept = [o for o in kept if o.get("matcher", {}).get("options") != "Event freshness"]
    kept.append(
        {
            "matcher": {"id": "byName", "options": "Event freshness"},
            "properties": [
                {"id": "custom.hidden", "value": False},
                {"id": "custom.width", "value": 140},
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
                    "id": "custom.cellOptions",
                    "value": {"type": "auto", "wrapText": True},
                },
            ],
        }
    )
    panel["fieldConfig"]["overrides"] = kept
    for item in panel.get("transformations", []):
        if item["id"] == "organize":
            item["options"]["renameByName"].update(
                Value="Severity", freshness="Event freshness"
            )
            order = item["options"]["indexByName"]
            fields = [
                name for name in sorted(order, key=order.get) if name != "freshness"
            ]
            fields.insert(fields.index("confidence") + 1, "freshness")
            item["options"]["indexByName"] = {
                name: index for index, name in enumerate(fields)
            }


def _incident_audit(payload, panels):
    """Retain every current suspect and explain missing event clocks and samples."""
    add_stage_source_clocks(payload)
    for item in _walk_panels(payload["panels"]):
        if item["id"] in {907, 893}:
            item["description"] = item["description"].replace(
                "TIME RANGE · CURRENT", "CURRENT"
            )
        elif item["id"] == 2460:
            _remove_row_limit(item)
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
        elif item["id"] == 8807:
            item["description"] = item["description"].replace(
                "CURRENT · TIME RANGE", "TIME RANGE"
            )
        elif item["id"] == 22011:
            # This drilldown explains the CURRENT ranked answer. It must not
            # evaluate its 15m operands at a historical dashboard end.
            item["description"] = item["description"].replace(
                "GLOBAL / TIME RANGE", "GLOBAL / CURRENT"
            )
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
                        if prop["id"] == "custom.width":
                            prop["value"] = widths[field]
                if field == "Evaluated":
                    override["properties"].append(
                        {"id": "unit", "value": "time:YYYY-MM-DD HH:mm"}
                    )
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
                                            "text": "Not verified"
                                        }
                                    },
                                }
                            ],
                        }
                    ],
                }
            )
    suspect = panels[2010]
    suspect["targets"][0]["expr"] = (
        "label_replace("
        + suspect["targets"][0]["expr"]
        + ',"freshness","Not verified: no event timestamp","","")'
    )
    organize = next(t for t in suspect["transformations"] if t["id"] == "organize")
    organize["options"]["renameByName"]["freshness"] = "Event freshness"
    _urgency_label(suspect)
    _remove_row_limit(suspect)
    suspect["description"] = (
        suspect["description"]
        .replace("GLOBAL / TIME RANGE", "GLOBAL / CURRENT")
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
    _remove_row_limit(panels[2005])
    panels[2005]["links"][0]["title"] = "Open all global alerts (no row truncation)"
    fleet = panels.get(8808)
    if fleet:
        _explain_missing_samples(fleet.get("panels", []))
    for row in payload["panels"]:
        for child in row.get("panels", []):
            if child["id"] == 9701:
                child["links"] = [
                    {
                        "title": "Inspect current workflow evidence",
                        "url": "/d/bioetl-incident-v1/5-incident-workspace?viewPanel=9701&${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}&${__url_time_range}",
                        "targetBlank": False,
                    }
                ]
            if child["id"] == 22010:
                child["datasource"] = deepcopy(suspect["datasource"])
                child["targets"] = deepcopy(suspect["targets"])
                child["description"] = child["description"].replace(
                    "GLOBAL / TIME RANGE", "GLOBAL / CURRENT"
                )
                _urgency_label(child)


def _walk_panels(items):
    for item in items:
        yield item
        yield from _walk_panels(item.get("panels", []))


def _ingestion_age_card() -> dict:
    """Expose observed ingestion age with the alert's 24h/72h bounds."""
    metric = 'bioetl_data_freshness_seconds{pipeline=~"$pipeline"}'
    # Match the rules' per-entity deduplication, then reject future timestamps.
    # Disjoint targets avoid repeating this aggregation in a long union query.
    age = f"max((time()-max by(pipeline,entity)({metric}>0))>=0)"
    branches = [
        ("<=86400", "Within 24h (observed only)"),
        (">86400<=259200", "STALE 24-72h (observed)"),
        (">259200", "STALE >72h (observed)"),
    ]
    return {
        "id": 9606,
        "type": "stat",
        "title": "Review Processing Anchor Age · 24h / 72h",
        "gridPos": {"x": 10, "y": 2, "w": 14, "h": 3},
        "datasource": {"type": "prometheus", "uid": "prometheus"},
        "targets": [
            {
                "refId": chr(65 + index),
                "instant": True,
                "format": "time_series",
                "legendFormat": "{{freshness}}",
                "expr": f'label_replace(({age}{condition}),"freshness","{label}","","")',
            }
            for index, (condition, label) in enumerate(branches)
        ],
        "transformations": [],
        "description": (
            "CURRENT · Visible Pipeline filter; independent of Run ID, Workflow, Run Type and the historical range. "
            "Age of the oldest observed successful-run START processing anchor, from bioetl_data_freshness_seconds (emitted by successful DQ evaluation). "
            "This is not completion time or the provider's input-record event time; source-record freshness is unverified. "
            "Per-entity duplicate sources use max timestamp, matching the alert rules. "
            "STALE >24h is warning and >72h is critical, matching BioETLDataFreshnessLagHigh/Critical; both alerts additionally require 15m pending. "
            "Within 24h applies only to observed entities and does not prove complete coverage, a live provider probe or saved-run health. "
            "Entities with missing/invalid/future timestamps are unverified; no valid entities remains UNKNOWN. Inspect Telemetry Coverage for missing entities; query time is not primary event time."
        ),
        "fieldConfig": {
            "defaults": {
                "unit": "s",
                "decimals": 1,
                "noValue": "UNKNOWN · no processing anchor",
                "color": {"mode": "thresholds"},
                "thresholds": {
                    "mode": "absolute",
                    "steps": [
                        {"color": "text", "value": None},
                        {"color": "orange", "value": 86400.000001},
                        {"color": "red", "value": 259200.000001},
                    ],
                },
            },
            "overrides": [],
        },
        "options": {
            "colorMode": "value",
            "graphMode": "none",
            "textMode": "value_and_name",
            "text": {"valueSize": 24, "titleSize": 14},
            "reduceOptions": {"calcs": ["last"], "fields": "", "values": False},
        },
        "links": [
            {
                "title": "Inspect current telemetry coverage",
                "url": "/d/bioetl-incident-v1/5-incident-workspace?viewPanel=9491",
                "includeVars": False,
                "targetBlank": False,
            }
        ],
    }


def _overview_audit(payload, panels):
    """Separate saved verdicts, current alerts and complete alert evidence."""
    panels[9604]["title"] = "Review Saved Run Verdict"
    panels[9604]["description"] += (
        " This is the saved run assessment, not current fleet health or active alerts."
    )
    panels[9604]["gridPos"].update(x=0, y=2, w=5, h=3)
    panels[9603]["gridPos"].update(x=0, y=5, w=10, h=5)
    panels[9300]["gridPos"].update(x=0, y=10, w=10, h=8)
    panels[99]["gridPos"].update(x=10, y=5, w=14, h=5)
    panels[9002]["gridPos"].update(x=10, y=10, w=14, h=8)
    _provider_card(panels)
    health = _fleet_alert_card(panels)
    payload["panels"] = [
        p for p in payload["panels"] if p["id"] not in {9605, 9606}
    ] + [health, _ingestion_age_card()]
    alerts = panels[2005]
    alerts["targets"][0]["expr"] = "bioetl_incident_global_alerts"
    _remove_row_limit(alerts)
    for transform in alerts["transformations"]:
        if transform["id"] == "organize":
            transform["options"].setdefault("excludeByName", {}).update(
                alert_runbook=True, pipeline_context=True, owner=True, next_step=True
            )
    alerts["description"] = alerts["description"].replace(
        "Summary shows up to two highest-priority alerts; open Incident Workspace or Browse Global Alerts for all rows.",
        "All returned alerts remain available through pagination; the visible row count includes every alert.",
    )
    payload["panels"].sort(key=lambda p: (p["gridPos"]["y"], p["gridPos"]["x"]))


def apply_evening_audit(payload: dict) -> None:
    """Apply only confirmed presentation fixes after older layout migrations."""
    uid = payload.get("uid")
    note = (
        " Canonical presentation contract: dashboard-2.0; UID v1/v2 suffixes are stable compatibility identifiers. "
        "Shared selectors are Workflow, Pipeline, Run Type and Run ID; local lookup, derived selectors and diagnostic views have role-specific scope. "
        "Saved outcomes, current alert urgency, coverage and replay readiness are distinct state vocabularies."
    )
    if note not in payload.get("description", ""):
        payload["description"] = payload.get("description", "") + note
    panels = {p["id"]: p for p in payload.get("panels", [])}
    if uid == "bioetl-run-explorer-v1":
        panels[1]["description"] = (
            panels[1].get("description", "").replace("latest 10", "latest 20")
        )
    if uid == "bioetl-dq-v2":
        payload["description"] = payload.get("description", "").replace(
            "Run ID is always selected",
            "Run ID '-' resolves AUTO to the latest run in scope; an explicit UUID stays selected",
        )
    if uid == "bioetl-incident-v1":
        _incident_audit(payload, panels)
    if uid == "bioetl-overview-v2":
        _overview_audit(payload, panels)
