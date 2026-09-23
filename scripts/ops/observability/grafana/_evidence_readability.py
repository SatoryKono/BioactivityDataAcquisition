"""Canonical readable evidence views for the seven Grafana dashboards."""

from __future__ import annotations
from scripts.ops.observability.grafana._gr_db_corrections import _override, _panels

_WIDTH = "custom.width"
_HIDDEN = "custom.hidden"
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
            if "action_path" not in names:
                names.append("action_path")
    _override(panel, "action_path", _HIDDEN, True)
    _table(panel, {"Domain": 125, "Status": 115, "Action": 170})
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
    p[9451]["options"]["footer"]["enablePagination"] = False
    p[9452]["options"]["footer"]["enablePagination"] = False
    _stack(p[9450], {9451: 8, 9452: 4})


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
            "custom.cellOptions",
            {"type": "auto", "wrapText": False},
        )
    for pid in (9010, 9011):
        for item in p[pid]["fieldConfig"].get("overrides", []):
            item["properties"] = [
                prop for prop in item["properties"] if prop["id"] != _WIDTH
            ]
        _table(p[pid], {"Run Type": 130, "Status": 110, "Failures": 110, "Runs": 110})


def _trust(p: dict[int, dict]) -> None:
    _table(p[9418], {"Result": 110, "Trust": 105, "Reasons": 90, "Observed": 165})
    for pid in (9408, 9409, 9406):
        _table(p[pid], {"Result": 125, "Status": 115, "Action": 160})
    for pid in (9413, 9414, 9415):
        _table(p[pid], {"check": 220, "status": 110})
        _override(p[pid], "reason", _HIDDEN, True)
        _override(p[pid], "reason_display", _HIDDEN, True)
        _override(p[pid], "detail", "displayName", "Reason")
        _override(p[pid], "check", "displayName", "Check")
        _override(p[pid], "status", "displayName", "Status")
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


def _runtime(p: dict[int, dict]) -> None:
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
    p[9101]["gridPos"]["h"] = p[9107]["gridPos"]["h"] = 7
    p[9104]["gridPos"].update(y=14, h=3)
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
        "TIME RANGE Â· Observed degraded health checks in the selected range; "
        "historical count, not current severity. Missing evidence remains UNKNOWN."
    )


def _dq(p: dict[int, dict]) -> None:
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


def _incident(p: dict[int, dict]) -> None:
    for pid in (2010, 22010):
        _override(
            p[pid],
            "Action",
            "mappings",
            [{"type": "value", "options": {"data_quality": {"text": "DQ"}}}],
        )
    _stack(p[2099], {2002: 7, 2003: 3, 2004: 7})
    p[22010]["options"].setdefault("footer", {}).update(
        enablePagination=False, countRows=False
    )
    p[22010]["gridPos"]["h"] = 12
    for field in ("Object", "Signal", "Details"):
        _override(p[22010], field, "custom.wrapText", True)
        _override(
            p[22010], field, "custom.cellOptions", {"type": "auto", "wrapText": True}
        )
    p[22010]["description"] = (
        "GLOBAL / CURRENT Â· Empty successful result: no ranked suspects. Missing telemetry remains "
        "UNKNOWN; request failures remain QUERY ERROR. Open domain diagnostics from Action."
    )
    p[9400]["options"]["content"] = (
        '<div style="padding:4px 10px;border-left:4px solid #6b7280;font-size:16px;line-height:1.2;white-space:normal;overflow-wrap:anywhere;max-width:96ch">GLOBAL signals are not verified causes. '
        "Selected-scope status is separate. Telemetry gaps remain UNKNOWN; event age and impact need event evidence.</div>"
    )
    p[2001]["options"]["content"] = (
        '<div style="font-size:16px;line-height:1.2">Start with ranked suspects; '
        "open Action for domain evidence. PENDING means the alert has not fired. "
        "Use alert history below to assess timing and impact.</div>"
    )
    for pid in (2005, 22005):
        _table(p[pid], {"severity": 90, "alertstate": 100})
        _override(p[pid], "alertname", "displayName", "Alert")
        _override(p[pid], "alertstate", "displayName", "State")


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
                    "options": {"SELECT RUN": {"text": "â€”", "color": "text"}},
                }
            ],
        )
    _override(panel, "Rules", _HIDDEN, True)
    _override(
        panel,
        "Evidence",
        "mappings",
        [
            {
                "type": "value",
                "options": {"SELECT RUN": {"text": "Choose a run", "color": "text"}},
            }
        ],
    )


def apply_evidence_readability(payload: dict) -> None:
    """Preserve queries while improving evidence readability at narrow widths."""
    p = {panel["id"]: panel for panel in _panels(payload["panels"])}
    for panel in p.values():
        _selection_summary(panel)
        if panel["type"] == "stat":
            panel.setdefault("options", {})["text"] = {"valueSize": 20, "titleSize": 14}
    _saved_run(p)
    handlers = {
        "bioetl-overview-v2": _overview,
        "bioetl-control-plane-v1": _trust,
        "bioetl-runtime": _runtime,
        "bioetl-provider-health-v2": _provider,
        "bioetl-dq-v2": _dq,
        "bioetl-incident-v1": _incident,
    }
    if handler := handlers.get(payload["uid"]):
        handler(p)
    if payload["uid"] == "bioetl-run-explorer-v1":
        _run_explorer(p)
    _first_window_widths(payload, p)


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
                "var-run_id=${__data.fields.run_id:percentencode}",
            )
            .replace(
                "${__data.fields.Run:percentencode}",
                "${__data.fields.run_id:percentencode}",
            )
        )
        if field == "Run":
            link["title"] = "Select ${__data.fields.run_id}"


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
    for transform in run["transformations"]:
        opts = transform["options"]
        if transform["id"] == "filterFieldsByName":
            names = opts["include"]["names"]
            if "run_label" not in names:
                names.append("run_label")
        if transform["id"] == "organize":
            opts["renameByName"].pop("run_id", None)
            opts["renameByName"]["run_label"] = "Run"
            opts["indexByName"]["run_label"] = 4
            opts["indexByName"]["run_id"] = 20
    _override(run, "run_id", _HIDDEN, True)
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
        "bioetl-overview-v2": {215: {"Priority": 90, "Action": 125}},
        "bioetl-dq-v2": {9102: {"severity": 70, "Action": 125}},
        "bioetl-run-explorer-v1": {
            3010: {
                "selected": 28,
                "Started": 145,
                "Run": 115,
                "Trust": 120,
                "Processing": 100,
                "Report": 85,
            }
        },
    }
    for pid, fields in widths.get(payload["uid"], {}).items():
        for item in p[pid]["fieldConfig"].get("overrides", []):
            item["properties"] = [
                prop for prop in item["properties"] if prop["id"] != _WIDTH
            ]
        _table(p[pid], fields)
