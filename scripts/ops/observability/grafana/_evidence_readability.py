"""Canonical readable evidence views for the seven Grafana dashboards."""

from __future__ import annotations
from copy import deepcopy
from scripts.ops.observability.grafana._gr_db_corrections import _override, _panels
from scripts.ops.observability.grafana._visual_usability import _bands

_WIDTH = "custom.width"
_HIDDEN = "custom.hidden"
_WRAP = "custom.wrapText"
_CELL = "custom.cellOptions"
_SELECT_RUN = "SELECT RUN"
_OPEN_REPORT = "Open report"


def _table(panel: dict, widths: dict[str, int] | None = None) -> None:
    custom = panel["fieldConfig"]["defaults"].setdefault("custom", {})
    custom.update(minWidth=50, inspect=True, wrapText=False)
    custom.setdefault("cellOptions", {"type": "auto"})["wrapText"] = False
    panel["options"]["cellHeight"] = "sm"
    for field, width in (widths or {}).items():
        _override(panel, field, _WIDTH, width)


def _stack(row: dict, heights: dict[int, int] | None = None) -> None:
    """Relayout a detail row without dropping evidence."""
    y = row["gridPos"]["y"] + 1
    order = list(heights or {})
    row["panels"].sort(
        key=lambda p: (
            order.index(p["id"]) if p["id"] in order else len(order),
            p["id"],
        )
    )
    for panel in row.get("panels", []):
        grid = panel["gridPos"]
        grid.update(x=0, y=y, w=24, h=(heights or {}).get(panel["id"], grid["h"]))
        y += grid["h"]


def _legend(panel: dict) -> None:
    panel.setdefault("options", {})["legend"] = {
        "showLegend": True,
        "displayMode": "table",
        "placement": "bottom",
        "calcs": ["lastNotNull", "max"],
    }


def _stage_colors(panel: dict) -> None:
    # Stage identity stays stable across Runtime and DQ, independently of severity.
    overrides = panel["fieldConfig"].setdefault("overrides", [])
    for stage, color in {
        "bronze": "#CD7F32",
        "silver": "#C0C0C0",
        "gold": "#E0B400",
        "quarantined": "#B877D9",
    }.items():
        # Grafana anchors patterns without / delimiters to the whole display name.
        matcher = {"id": "byRegexp", "options": "(^|.*[ /])" + stage + "$"}
        legacy = {"id": "byRegexp", "options": "(^|[ /])" + stage + "$"}
        match = next((o for o in overrides if o["matcher"] in (matcher, legacy)), None)
        if match is None:
            match = {"matcher": matcher, "properties": []}
            overrides.append(match)
        match["matcher"] = matcher
        match["properties"] = [p for p in match["properties"] if p["id"] != "color"]
        match["properties"].append(
            {"id": "color", "value": {"mode": "fixed", "fixedColor": color}}
        )


def _selected_run_selectors(p: dict[int, dict]) -> None:
    for candidate in p.values():
        for target in candidate.get("targets", []):
            if "/selected-run-status?" in target.get("url", ""):
                selector = target.get("root_selector")
                if selector in {"summary", "trust", "domains"}:
                    target["root_selector"] = "presentation_" + selector


def _saved_run(p: dict[int, dict]) -> None:
    _selected_run_selectors(p)
    panel = p[9451]
    panel["targets"][0]["root_selector"] = "presentation_domains"
    for transform in panel["transformations"]:
        if transform["id"] == "filterFieldsByName":
            names = transform["options"]["include"]["names"]
            names[:] = [
                "reason_display" if name == "reason" else name for name in names
            ]
            if "action_path" not in names:
                names.append("action_path")
        elif transform["id"] == "organize":
            options = transform["options"]
            options["indexByName"]["reason_display"] = options["indexByName"].pop(
                "reason", 2
            )
            options["renameByName"].pop("reason", None)
            options["renameByName"]["reason_display"] = "Reason"
    _override(panel, "action_path", _HIDDEN, True)
    _table(panel, {"Domain": 125, "Status": 115, "Action": 170})
    _override(panel, "Reason", _WRAP, True)
    _override(panel, "Reason", _CELL, {"type": "auto", "wrapText": True})
    _override(
        panel,
        "Reason",
        "mappings",
        [
            {
                "type": "value",
                "options": {
                    "selection_required": {
                        "text": "Choose a run to inspect saved evidence"
                    }
                },
            }
        ],
    )
    _override(panel, "Evidence reference", _HIDDEN, True)
    _override(
        panel,
        "Action",
        "links",
        [
            {
                "title": "Inspect saved run report",
                "url": "/${__data.fields.action_path}&var-pipeline=${pipeline:percentencode}&var-run_type=${run_type:percentencode}&var-workflow=${workflow:percentencode}&${__url_time_range}",
                "targetBlank": True,
            }
        ],
    )
    _override(
        panel,
        "Action",
        "mappings",
        [
            {
                "type": "value",
                "options": {
                    "Inspect saved evidence": {"text": _OPEN_REPORT},
                    "Inspect reason and evidence": {"text": _OPEN_REPORT},
                    "Select run or inspect evidence": {"text": "Inspect report"},
                },
            }
        ],
    )
    panel["links"] = []
    for field in ("Pipeline", "Run ID"):
        _override(
            p[9452],
            field,
            "mappings",
            [
                {
                    "type": "value",
                    "options": {
                        ".*": {"text": "No run selected"},
                        "-": {"text": "No run selected"},
                    },
                }
            ],
        )
    _table(p[9452])
    # Identity is a single evidence row: retain the full UUID and revision,
    # including on narrow screens, rather than truncating provenance.
    identity_custom = p[9452]["fieldConfig"]["defaults"]["custom"]
    identity_custom["wrapText"] = True
    identity_custom["cellOptions"]["wrapText"] = True
    p[9451]["options"]["footer"]["enablePagination"] = False
    p[9452]["options"]["footer"]["enablePagination"] = True
    _stack(p[9450], {9451: 12, 9452: 8})


def _overview(p: dict[int, dict]) -> None:
    _stack(p[9030], {9031: 9, 9018: 12, 9019: 12, 9020: 12})
    for pid in (9018, 9019, 9020):
        p[pid]["options"].pop("pageSize", None)
        p[pid]["options"].update(perPage=8, rowHeight=0.8, showValue="never")
        p[pid]["fieldConfig"]["defaults"].setdefault("custom", {})["axisWidth"] = 290
    _stack(p[9009], {9010: 9, 9011: 9, 9015: 3})
    _stack(p[9012], dict.fromkeys((9006, 9003, 9004, 9007, 9005, 9013), 8))
    for pid in (215, 20215):
        for field in ("action_scope", "action_dashboard_uid", "run_type"):
            _override(p[pid], field, _HIDDEN, True)
        _table(p[pid], {"Priority": 90, "Pipeline": 280, "Action": 170})
        _override(
            p[pid],
            "Pipeline",
            _CELL,
            {"type": "auto", "wrapText": False},
        )
    for pid in (9010, 9011):
        for item in p[pid]["fieldConfig"].get("overrides", []):
            item["properties"] = [
                prop for prop in item["properties"] if prop["id"] != _WIDTH
            ]
        _table(p[pid], {"Run Type": 130, "Status": 110, "Failures": 110, "Runs": 110})


def _stamp_select_run_states(mapping: dict) -> None:
    if mapping["type"] != "value":
        return
    for state in (_SELECT_RUN, "UNFINISHED"):
        mapping["options"][state] = {"text": state, "color": "#A3A3A3"}


def _stamp_result_mapping_prop(prop: dict) -> None:
    if prop["id"] != "mappings":
        return
    for mapping in prop["value"]:
        _stamp_select_run_states(mapping)


def _trust_select_run_mappings(p: dict[int, dict]) -> None:
    # An unselected run is not a successful processing result.
    for override in p[9418]["fieldConfig"]["overrides"]:
        if override.get("matcher", {}).get("options") != "Result":
            continue
        for prop in override["properties"]:
            _stamp_result_mapping_prop(prop)


def _trust_anchors(p: dict[int, dict]) -> None:
    anchors = p[9404]
    _table(anchors)
    anchors["options"]["cellHeight"] = "lg"
    anchors["fieldConfig"]["defaults"]["custom"]["wrapText"] = True
    anchors["fieldConfig"]["defaults"]["custom"]["cellOptions"]["wrapText"] = True
    _override(anchors, "value_full", _WRAP, True)
    _override(anchors, "value_full", _CELL, {"type": "auto", "wrapText": True})


def _trust_layout(p: dict[int, dict]) -> None:
    _legend(p[7])
    y = p[901]["gridPos"]["y"] + 1
    p[908]["gridPos"].update(x=0, y=y, w=24, h=4)
    y += 4
    for index, pid in enumerate((2, 1, 132, 133)):
        p[pid]["gridPos"].update(x=index * 6, y=y, w=6, h=3)
    y += 3
    for pid, height in ((131, 9), (7, 12), (9414, 9)):
        p[pid]["gridPos"].update(x=0, y=y, w=24, h=height)
        y += height
    for pid, title in {
        3: "Track Incompatibilities",
        104: "Track Unreconstructable",
        101: "Track Load Failures",
        102: "Track Save Failures",
        103: "Track Global Admin Failures",
        2: "Track Ledger Failures",
        1: "Track Manifest Failures",
        132: "Monitor Manifest (30m)",
        133: "Monitor Ledger (30m)",
        122: "Track Missing Lineage",
        137: "Track Lineage Failures",
    }.items():
        p[pid]["title"] = title
        p[pid]["fieldConfig"]["defaults"]["displayName"] = title
    # Three readable cards per band preserve the detail density contract.
    _bands(
        p[902],
        [
            [(894, 0, 24, 5)],
            [(130, 0, 8, 3), (3, 8, 8, 3), (104, 16, 8, 3)],
            [(120, 0, 8, 3), (101, 8, 8, 3), (102, 16, 8, 3)],
            [(103, 0, 8, 3), (121, 8, 8, 3)],
            [(134, 0, 12, 6), (5, 12, 12, 6)],
            [(135, 0, 24, 6)],
            [(105, 0, 24, 7)],
            [(106, 0, 24, 7)],
            [(9413, 0, 24, 6)],
        ],
    )
    _bands(
        p[901],
        [
            [(908, 0, 24, 4)],
            [(2, 0, 8, 3), (1, 8, 8, 3)],
            [(132, 0, 8, 3), (133, 8, 8, 3)],
            [(131, 0, 24, 9)],
            [(7, 0, 24, 12)],
            [(9414, 0, 24, 9)],
        ],
    )
    p[122]["gridPos"].update(x=0, w=8, h=3)
    p[137]["gridPos"].update(x=8, w=8, h=3)


def _trust(p: dict[int, dict]) -> None:
    _trust_select_run_mappings(p)
    _table(p[9418], {"Result": 110, "Trust": 105, "Reasons": 90, "Observed": 165})
    _trust_anchors(p)
    for pid in (9408, 9409, 9406):
        _table(p[pid], {"Result": 125, "Status": 115, "Action": 160})
    # A missing cell is not an empty table: retain the per-row MISSING result
    # without repeating the panel-level no-rows explanation in each cell.
    _override(p[9406], "checkpoint_value_short", "noValue", "UNKNOWN")
    _override(p[9409], "Action", _WIDTH, 190)
    for pid in (9413, 9414, 9415):
        _table(p[pid], {"check": 220, "status": 110})
        _override(p[pid], "reason", _HIDDEN, True)
        _override(p[pid], "reason_display", _HIDDEN, True)
        _override(p[pid], "detail", "displayName", "Reason")
        _override(p[pid], "check", "displayName", "Check")
        _override(p[pid], "status", "displayName", "Status")
    _trust_layout(p)


def _runtime(p: dict[int, dict]) -> None:
    p[9102]["title"] = "Monitor Coverage"
    for pid, title in {
        230: "Monitor Pipeline Alerts",
        21: "Monitor Memory Pressure",
        5: "Inspect Control Plane Alerts",
        6: "Inspect Provider Alerts",
    }.items():
        p[pid]["title"] = title
    for pid in (241, 256):
        _override(p[pid], "stage", _WIDTH, 130)
    for pid in (238, 240, 9105):
        _legend(p[pid])
        _stage_colors(p[pid])
    p[9105]["fieldConfig"]["defaults"].setdefault("custom", {})["axisLabel"] = (
        "Stage lag"
    )
    _stack(p[252], {238: 10, 240: 10, 242: 9, 9105: 10, 243: 9, 220: 3})
    _stack(p[32460], {22460: 14, 2461: 14})
    _table(p[22460], {"Backlog": 100, "Lag": 100, "Throughput": 130})
    _table(p[2461], {"Pipeline": 240, "Run type": 130})
    for pid in (2460, 22460, 2461, 243):
        _override(p[pid], "Throughput", "unit", "suffix: records/s")
        _override(p[pid], "scope_stage\\measure", "displayName", "Pipeline / Stage")
        _override(p[pid], "scope_stage", "displayName", "Pipeline / Stage")


def _provider(p: dict[int, dict]) -> None:
    p[9101]["title"] = "Monitor Fleet Status"
    p[9107]["title"] = "Inspect Health Evidence"
    for pid in (9101, 9107):
        p[pid]["options"]["cellHeight"] = "lg"
        target = p[pid]["targets"][0]
        if target["expr"].startswith("topk(3, ") and target["expr"].endswith(")"):
            target["expr"] = target["expr"][8:-1]
        p[pid]["description"] = (
            "GLOBAL / CURRENT · All observed provider status series, paginated; independent of "
            "Pipeline and Run ID; independent of the selected Provider. Missing series are not proof of "
            "health. Status is the current assessment; evidence describes observation "
            "availability, not the selected historical run."
        )
    _override(p[9101], "Severity", "displayName", "Status")
    _override(p[9101], "Provider", "custom.wrapText", True)
    _override(p[9101], "Provider", _CELL, {"type": "auto", "wrapText": True})
    p[9101]["options"]["sortBy"] = [{"displayName": "Status", "desc": True}]
    for transform in p[9107]["transformations"]:
        if transform["id"] == "organize":
            transform["options"]["excludeByName"]["source_state"] = True
    _override(p[9107], "reason", "displayName", "Evidence")
    # The mapped explanation must remain readable in the narrow fleet table.
    _override(p[9107], "reason", _WRAP, True)
    _override(p[9107], "reason", _CELL, {"type": "auto", "wrapText": True})
    _override(p[9107], "reason", "custom.inspect", True)
    _override(
        p[9107],
        "reason",
        "mappings",
        [
            {
                "type": "value",
                "options": {
                    "observed_health_status": {"text": "Health observation available"},
                    "invalid_health_timestamp": {"text": "Invalid observation time"},
                    "missing_health_status": {"text": "No health check result available"},
                },
            }
        ],
    )
    p[9002]["options"]["content"] = (
        '<div style="font-size:16px;line-height:1">Next action: inspect non-OK Fleet Status rows.</div>'
    )
    p[9002]["gridPos"]["h"] = 2
    p[102]["title"] = "Inspect Health p95"
    for field, width in {"Provider": 140, "Source state": 70, "Status": 90}.items():
        _override(p[9107], field, _WIDTH, width)
    _override(p[9107], "Source state", "displayName", "Source")
    _override(p[9111], "Provider", _WIDTH, 200)
    _override(
        p[9111], "Provider", _CELL, {"type": "auto", "wrapText": False}
    )
    for pid in (9101, 9107):
        p[pid]["gridPos"].update(y=7, h=8)
        p[pid]["options"].setdefault("footer", {})["enablePagination"] = True
    p[9104]["gridPos"].update(y=15, h=3)
    p[9104]["options"]["colorMode"] = "value"
    _stack(p[9404], {114: 10, 1: 10, 2: 3, 105: 3, 104: 3, 7: 3})
    _table(
        p[114],
        {"Provider": 125, "Status": 110, "Last check": 175, "Observation age": 145},
    )
    p[105]["fieldConfig"]["defaults"]["color"] = {"mode": "thresholds"}
    p[105]["fieldConfig"]["defaults"]["thresholds"] = {
        "mode": "absolute",
        "steps": [{"value": None, "color": "text"}],
    }
    p[105]["options"]["colorMode"] = "value"
    p[105]["description"] = (
        "TIME RANGE · Observed degraded health checks in the selected range; "
        "historical count, not current severity. Missing evidence remains UNKNOWN."
    )
    for y, pid in enumerate((9106, 9105, 91, 9404, 9405, 9450), start=18):
        p[pid]["gridPos"]["y"] = y
        _stack(
            p[pid], {child["id"]: child["gridPos"]["h"] for child in p[pid]["panels"]}
        )


def _dq(p: dict[int, dict]) -> None:
    p[2]["title"] = "Monitor Weighted DQ"
    p[8]["targets"][0].update(
        expr='(max(clamp_min(time() - max_over_time(bioetl_data_freshness_seconds{pipeline=~"$pipeline"}[$__range]), 0))) / 3600',
        instant=True,
        range=False,
    )
    p[8]["description"] = (
        "TIME RANGE · Worst age in hours at the selected range end, using the "
        "latest timestamp observed per series within that range. Missing series "
        "show TELEMETRY MISSING (UNKNOWN); an older non-null age is never carried forward. "
        "SLA 24/72: WARN at 24h and CRIT at 72h apply only to observed evidence. "
        "This is range evidence, not a selected-run or CURRENT completeness verdict."
    )
    _table(
        p[156], {"Pipeline": 200, "Quarantined records": 100, "Excluded records": 80}
    )
    _override(p[156], "Quarantined records", "displayName", "Quarantined")
    _override(p[156], "Excluded records", "displayName", "Excluded")
    p[5]["title"] = "Monitor Worst DQ"
    coverage_delta = 4 - p[157]["gridPos"]["h"]
    p[157]["gridPos"]["h"] = 4
    for panel in p[9404]["panels"]:
        if panel["id"] != 157:
            panel["gridPos"]["y"] += coverage_delta
    _table(p[9102], {"pipeline": 160, "severity": 70, "Action": 140})
    _override(p[9102], "pipeline", _HIDDEN, False)
    _override(p[9102], "pipeline", "displayName", "Pipeline")
    _override(
        p[9102],
        "reason",
        "mappings",
        [
            {
                "type": "value",
                "options": {
                    "gold_contract_exclusions": {"text": "Gold contract exclusions"},
                },
            }
        ],
    )
    _override(
        p[9102],
        "action_target",
        "mappings",
        [
            {
                "type": "value",
                "options": {
                    "data_quality": {"text": "Rejects", "color": "orange"},
                    "verify_dq_reason_rules": {
                        "text": "Verify DQ rules",
                        "color": "gray",
                    },
                },
            }
        ],
    )
    for item in p[9102]["fieldConfig"]["overrides"]:
        if item["matcher"].get("options") == "action_target":
            for prop in item["properties"]:
                if prop["id"] == "links":
                    base = prop["value"][0]["url"].split("&viewPanel=")[0]
                    prop["value"] = [
                        {
                            "title": "Inspect Gold exclusions",
                            "url": base + "&viewPanel=156",
                            "targetBlank": False,
                        },
                        {
                            "title": "Inspect Silver rejects",
                            "url": base + "&viewPanel=121",
                            "targetBlank": False,
                        },
                        {
                            "title": "Verify DQ recording rules",
                            "url": "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/docs/05-operations/runbooks/observability-checklist.md",
                            "targetBlank": True,
                        },
                    ]
    _legend(p[1])
    _stage_colors(p[1])
    p[9]["options"].update(orientation="horizontal", displayMode="basic")
    _stack(p[221], {1: 10, 4: 3, 3: 3, 101: 3, 9: 7, 12: 3, 151: 3})


def _incident_row_limits(p: dict[int, dict]) -> None:
    for panel_id, limit in ((2010, 2), (2005, 2)):
        for transform in p[panel_id]["transformations"]:
            if transform["id"] == "limit":
                transform["options"]["limitField"] = limit
        for link in p[panel_id].get("links", []):
            if link.get("title", "").startswith("Show all rows"):
                link["title"] = f"Show all rows and total (summary: up to {limit})"


def _incident_alert_tables(p: dict[int, dict]) -> None:
    for pid in (2005, 22005):
        _table(p[pid], {"severity": 90, "alertstate": 100})
        _override(p[pid], "alertname", "displayName", "Alert")
        _override(p[pid], "alertstate", "displayName", "State")
    for override in p[2005]["fieldConfig"]["overrides"]:
        if override.get("matcher", {}).get("options") in {"instance", "job", "Value"}:
            override["properties"] = [
                prop for prop in override["properties"] if prop["id"] != _WIDTH
            ]
    p[2006]["options"].pop("pageSize", None)
    p[2006]["options"].update(perPage=8, rowHeight=0.85, showValue="never")
    p[2006]["fieldConfig"]["defaults"]["custom"]["axisWidth"] = 650
    _table(p[2005], {"severity": 75, "provider": 110, "alertstate": 75})
    _override(p[2005], "alertname", _CELL, {"type": "auto", "wrapText": False})


def _incident(p: dict[int, dict]) -> None:
    p[9401]["title"] = "Monitor Scope Status"
    p[9400]["gridPos"]["h"] = 3
    p[9401]["gridPos"]["h"] = 3
    p[9401]["fieldConfig"]["defaults"]["displayName"] = "Monitor Scope Status"
    p[2001]["gridPos"].update(y=5, h=2)
    p[2010]["gridPos"].update(y=7, h=5)
    p[2005]["gridPos"].update(y=12, h=5)
    _incident_row_limits(p)
    _override(p[2010], "Confidence", _CELL, {"type": "auto", "wrapText": False})
    for pid in (2010, 22010):
        _override(
            p[pid],
            "Action",
            "mappings",
            [{"type": "value", "options": {"data_quality": {"text": "DQ"}}}],
        )
    _stack(p[2099], {2002: 7, 2003: 4, 2004: 7})
    _table(p[2002], {"pipeline": 230, "reason": 300, "run_type": 110})
    _override(p[2002], "reason", _WRAP, True)
    _table(p[2004], {"Pipeline": 250, "Signal": 88})
    p[22010]["options"].setdefault("footer", {}).update(
        enablePagination=False, countRows=False
    )
    p[22010]["gridPos"]["h"] = 12
    for field in ("Object", "Signal", "Details"):
        _override(p[22010], field, _WRAP, True)
        _override(p[22010], field, _CELL, {"type": "auto", "wrapText": True})
    p[22010]["description"] = (
        "GLOBAL / CURRENT · Empty successful result: no ranked suspects. Missing telemetry remains "
        "UNKNOWN; request failures remain QUERY ERROR. Open domain diagnostics from Action."
    )
    p[9400]["options"]["content"] = (
        '<div style="padding:4px 10px;border-left:4px solid #6b7280;font-size:16px;line-height:1.2;white-space:normal;overflow-wrap:anywhere;max-width:96ch">GLOBAL suspects are not verified causes. Telemetry gaps are UNKNOWN.</div>'
    )
    p[2001]["options"]["content"] = (
        '<div style="font-size:16px;line-height:1.2">Open Action for evidence; PENDING has not fired. Use alert history.</div>'
    )
    _incident_alert_tables(p)


def _selection_summary(panel: dict) -> None:
    """Present one selection action; preserve the selected-run verdict values."""
    if panel.get("title") != "Review Selected Run Status":
        return
    for field in ("Result", "Status"):
        _override(panel, field, "links", [])
        _override(
            panel,
            field,
            "mappings",
            [
                {
                    "type": "value",
                    "options": {_SELECT_RUN: {"text": "—", "color": "text"}},
                }
            ],
        )
    _override(panel, "Rules", _HIDDEN, True)
    links = panel["fieldConfig"]["defaults"].get("links", [])
    _override(panel, "Evidence", "links", links[:1])
    _override(
        panel,
        "Evidence",
        "mappings",
        [
            {
                "type": "value",
                "options": {_SELECT_RUN: {"text": "Choose a run", "color": "text"}},
            }
        ],
    )


_REASON_MAPPINGS = {
    "execution_success": {"text": "Processing completed"},
    "standalone_pipeline": {"text": "Standalone pipeline"},
    "run_dq_threshold_evaluation": {"text": "Data quality checks"},
    "run_preflight_provider_observation": {"text": "Provider preflight check"},
    "run_gold_schema_validation": {"text": "Gold schema validation"},
    "Archive missing": {"text": "No verified archive"},
    "archive_evidence_not_recorded": {"text": "No verified archive"},
}


def _bind_selected_run_envelope(summary: dict, source: dict) -> None:
    # The previous Dashboard datasource reused domain rows. Query the envelope
    # directly: the first domain's verdict is not the aggregate run verdict.
    summary["datasource"] = deepcopy(source["datasource"])
    summary["targets"] = deepcopy(source["targets"])
    summary["targets"][0]["root_selector"] = (
        '[$merge([presentation_summary[0], {"reason_display": '
        "presentation_trust[0].reasons_display ? "
        "presentation_trust[0].reasons_display : presentation_summary[0].reason}])]"
    )
    target = summary["targets"][0]
    target["parser"] = "uql"
    target["uql"] = (
        'parse-json | jsonata "' + target["root_selector"].replace('"', "'") + '"'
    )


def _overview_share_envelope(summary: dict, source: dict) -> list[str]:
    # Share one envelope; never substitute the first domain verdict for trust.
    source_target = source["targets"][0]
    projection = (
        "($s := presentation_summary[0]; $r := presentation_trust[0].reasons_display; "
        "$map(presentation_domains, function($d) { $merge([$d, {"
        "'run_execution': $s.execution_state, 'run_verdict': $s.verdict, "
        "'run_reason': $r ? $r : $s.reason}]) }))"
    )
    source_target["parser"] = "uql"
    source_target["root_selector"] = projection
    source_target["uql"] = 'parse-json | jsonata "' + projection + '"'
    summary["datasource"] = {"type": "datasource", "uid": "-- Dashboard --"}
    summary["targets"] = [{"panelId": 9002, "refId": "A", "withTransforms": False}]
    for transform in summary["transformations"]:
        if transform["id"] == "organize":
            transform["options"]["renameByName"].update(
                run_execution="Result", run_verdict="Status", run_reason="Reason"
            )
    return ["run_execution", "run_verdict", "run_reason"]


def _apply_reason_columns(panel: dict, fields: list[str]) -> None:
    for transform in panel["transformations"]:
        if transform["id"] == "filterFieldsByName":
            transform["options"]["include"]["names"] = fields
        elif transform["id"] == "organize":
            transform["options"]["indexByName"] = {
                name: index for index, name in enumerate(fields)
            }
            transform["options"]["renameByName"]["reason_display"] = "Reason"
    _override(panel, "Reason", _WRAP, True)
    _override(panel, "Reason", _CELL, {"type": "auto", "wrapText": True})
    _override(panel, "Reason", "displayName", "Reason")
    if panel.get("title") == "Review Selected Run Status":
        # Linked table text is ellipsized even with wrapping enabled. Keep the
        # existing panel-header Run Explorer link and make the reason readable.
        _override(panel, "Reason", "links", [])
        panel["options"]["cellHeight"] = "lg"
    _override(
        panel,
        "Reason",
        "mappings",
        [{"type": "value", "options": _REASON_MAPPINGS}],
    )
    panel["description"] += (
        (
            " Reason explains the saved assessment; missing archive evidence remains "
            "INCOMPLETE. Evidence completeness remains available in the saved report."
        )
        if "Reason explains the saved assessment" not in panel["description"]
        else ""
    )


def _overview_selected_run_layout(p: dict[int, dict], summary: dict) -> None:
    _table(p[9002], {"Domain": 120, "Status": 115})
    # Three evidence columns need half the first-screen width at narrow viewports.
    p[9002]["gridPos"].update(x=12, w=12)
    p[214]["gridPos"].update(x=16, w=8)
    p[215]["gridPos"]["w"] = 12
    p[215]["options"]["cellHeight"] = "sm"
    summary["gridPos"]["w"] = 12
    for rule in summary["fieldConfig"]["overrides"]:
        if rule["matcher"].get("options") in {
            "Evidence",
            "Reason",
            "Pipeline",
            "Severity",
        }:
            rule["properties"] = [v for v in rule["properties"] if v["id"] != _WIDTH]
    _override(summary, "Result", _WIDTH, 100)
    _override(summary, "Status", _WIDTH, 115)
    p[9002]["options"]["cellHeight"] = "sm"
    p[9002]["fieldConfig"]["defaults"]["custom"]["wrapText"] = True
    for field in ("Domain", "Status", "Reason"):
        _override(p[9002], field, "links", [])
    _override(p[9002], "Reason", _WRAP, True)
    _override(p[9002], "Reason", _CELL, {"type": "auto", "wrapText": True})


def _selected_verdict_reasons(p: dict[int, dict], *, overview: bool) -> None:
    """Expose explanations without replacing the aggregate saved-run verdict."""
    summary = next(
        panel
        for panel in p.values()
        if panel.get("title") == "Review Selected Run Status"
    )
    source = p[9002] if overview else p[9451]
    _bind_selected_run_envelope(summary, source)
    summary_fields = ["execution_state", "verdict", "reason_display"]
    if overview:
        summary_fields = _overview_share_envelope(summary, source)
    views = [(summary, summary_fields)]
    if overview:
        views.append((p[9002], ["domain", "verdict", "reason_display"]))
    for panel, fields in views:
        _apply_reason_columns(panel, fields)
    _override(summary, "Result", "displayName", "Processing")
    _override(summary, "Status", "displayName", "Overall verdict")
    if overview:
        _overview_selected_run_layout(p, summary)


def _apply_stat_value_sizes(p: dict[int, dict]) -> None:
    for panel in p.values():
        _selection_summary(panel)
        if panel["type"] == "stat":
            panel.setdefault("options", {})["text"] = {"valueSize": 20, "titleSize": 14}


def _apply_enum_verdict_copy(uid: object, p: dict[int, dict]) -> None:
    # These are enum verdicts, not blocker counts: code 3 is UNKNOWN.
    # Counter panels intentionally retain their >=2=CRIT threshold copy.
    enum_panels = {
        "bioetl-dq-v2": (9401,),
        "bioetl-provider-health-v2": (9401,),
        "bioetl-overview-v2": (9031, 9007),
    }
    for pid in enum_panels.get(uid, ()):
        p[pid]["description"] = (
            p[pid]["description"]
            .replace(">=2=CRIT", "2=CRIT")
            .replace("`null=UNKNOWN`", "`3/null=UNKNOWN`")
        )


def _apply_run_summary_wrap(p: dict[int, dict]) -> None:
    if 9402 not in p or p[9402].get("title") != "Review Run Summary":
        return
    # Hashes and composite parameter names need two lines at 900px.
    # Large rows keep pagination from placing wrapped text under its footer.
    summary = p[9402]
    _table(summary, {"Parameter": 300})
    summary["options"]["cellHeight"] = "lg"
    summary["fieldConfig"]["defaults"]["custom"]["wrapText"] = True
    summary["fieldConfig"]["defaults"]["custom"]["cellOptions"]["wrapText"] = True
    for field in ("Parameter", "Value"):
        _override(summary, field, _WRAP, True)
        _override(summary, field, _CELL, {"type": "auto", "wrapText": True})


def _rename_trust_monitor_titles(p: dict[int, dict]) -> None:
    for pid, title in {
        9401: "Monitor Readiness",
        891: "Monitor Replay",
        892: "Track Checkpoint",
        893: "Monitor Ledger",
    }.items():
        if pid in p:
            p[pid]["title"] = title
            p[pid].setdefault("fieldConfig", {}).setdefault("defaults", {})[
                "displayName"
            ] = title


def apply_evidence_readability(payload: dict) -> None:
    """Preserve queries while improving evidence readability at narrow widths."""
    p = {panel["id"]: panel for panel in _panels(payload["panels"])}
    _apply_stat_value_sizes(p)
    _saved_run(p)
    handlers = {
        "bioetl-overview-v2": _overview,
        "bioetl-control-plane-v1": _trust,
        "bioetl-runtime": _runtime,
        "bioetl-provider-health-v2": _provider,
        "bioetl-dq-v2": _dq,
        "bioetl-incident-v1": _incident,
    }
    if handler := handlers.get(payload.get("uid")):
        handler(p)
    if payload.get("uid") == "bioetl-run-explorer-v1":
        _run_explorer(p)
    _first_window_widths(payload, p)
    if payload.get("uid") == "bioetl-incident-v1":
        from ._incident_explanations import explain_incident

        explain_incident(p, _override)
    if payload.get("uid") in {"bioetl-overview-v2", "bioetl-dq-v2"}:
        _selected_verdict_reasons(p, overview=payload["uid"] == "bioetl-overview-v2")
    _apply_enum_verdict_copy(payload.get("uid"), p)
    _apply_run_summary_wrap(p)
    if payload.get("uid") == "bioetl-control-plane-v1":
        _rename_trust_monitor_titles(p)


def _run_links(run: dict):
    for item in run["fieldConfig"]["overrides"]:
        for prop in item["properties"]:
            if prop["id"] != "links":
                continue
            for link in prop["value"]:
                yield item["matcher"].get("options"), link


def _rewrite_run_links(run: dict) -> None:
    for field, link in _run_links(run):
        link["url"] = (
            link["url"]
            .replace(
                "var-run_id=${__value.raw}",
                "var-run_id=${__data.fields.Run:percentencode}",
            )
            .replace(
                "${__data.fields.run_id:percentencode}",
                "${__data.fields.Run:percentencode}",
            )
        )
        if field == "Run":
            link["title"] = "Select ${__data.fields.Run}"


def _run_explorer(p: dict[int, dict]) -> None:
    _table(
        p[3010],
        {
            "selected": 28,
            "Started": 145,
            "Pipeline": 185,
            "Run": 135,
            "Duration": 85,
            "Event age": 95,
            "Processing": 100,
            "Report": 125,
        },
    )

    run = p[3010]
    # Grafana also renders noValue when a request fails. Empty-state claims
    # must come from a successful, explicitly classified backend response.
    run["fieldConfig"]["defaults"]["noValue"] = (
        "UNKNOWN — response unavailable; inspect panel status for QUERY ERROR."
    )
    for target in run["targets"]:
        target["root_selector"] = (
            'index_state = "valid_empty" and $exists(items) and $count(items) = 0 '
            '? [{"pipeline": "VALID EMPTY"}] : items'
        )
    _override(run, "Trust", "noValue", "Open")
    _override(
        run,
        "Trust",
        "mappings",
        [{"type": "value", "options": {"Inspect in 1. Trust": {"text": "Open"}}}],
    )
    # Keep the timestamp and both action links visible. Event age remains in
    # the source frame for Inspect data; it is not a selected-run verdict.
    _override(run, "Event age", _HIDDEN, True)
    _override(run, "Report", "displayName", "Report")
    for transform in run["transformations"]:
        opts = transform["options"]
        if transform["id"] == "filterFieldsByName":
            names = opts["include"]["names"]
            names[:] = [name for name in names if name != "run_label"]
        if transform["id"] == "organize":
            opts["renameByName"].pop("run_label", None)
            opts["renameByName"]["run_id"] = "Run"
            opts["indexByName"].pop("run_label", None)
            opts["indexByName"]["run_id"] = 4
    # Inspect value must receive the complete UUID, not the shortened API label.
    run["fieldConfig"]["overrides"] = [
        item
        for item in run["fieldConfig"]["overrides"]
        if item["matcher"].get("options") != "run_id"
    ]
    for item in run["fieldConfig"]["overrides"]:
        if item["matcher"].get("options") == "^(workflow_id|Workflow)$":
            item["properties"] = [
                prop for prop in item["properties"] if prop["id"] != _HIDDEN
            ]
    _override(run, "Workflow", _HIDDEN, False)
    _override(run, "Run", "custom.inspect", True)
    _override(
        run,
        "Report",
        "mappings",
        [
            {
                "type": "value",
                "options": {
                    "REPORT MISSING": {"text": "Missing"},
                    _OPEN_REPORT: {"text": "Open"},
                },
            }
        ],
    )
    _rewrite_run_links(run)


def _first_window_widths(payload: dict, p: dict[int, dict]) -> None:
    widths = {
        "bioetl-control-plane-v1": {
            9418: {"Result": 100, "Trust": 105, "reasons_count": 80}
        },
        "bioetl-overview-v2": {215: {"Priority": 90, "Action": 155}},
        "bioetl-dq-v2": {9102: {"severity": 70, "Action": 125}},
        "bioetl-run-explorer-v1": {
            3010: {
                "selected": 28,
                "Started": 145,
                "Duration": 90,
                "Trust": 120,
                "Processing": 100,
                "Report": 80,
            }
        },
    }
    for pid, fields in widths.get(payload.get("uid"), {}).items():
        for item in p[pid]["fieldConfig"].get("overrides", []):
            item["properties"] = [
                prop for prop in item["properties"] if prop["id"] != _WIDTH
            ]
        _table(p[pid], fields)
        if payload.get("uid") == "bioetl-run-explorer-v1" and pid == 3010:
            _override(p[pid], "selected", "custom.minWidth", 28)
            # Native Grafana Table accepts px or auto, not percentage strings.
            # These three auto columns share the remaining width equally.
