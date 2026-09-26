"""Canonical presentation fixes from the live September 16 visual inspection."""

from __future__ import annotations

from copy import deepcopy

from scripts.ops.observability.grafana._dashboard_state_followup import override, walk

_WIDTH = "custom.width"
_CELL = "custom.cellOptions"


def _table(panel: dict, *, compact: bool = True) -> None:
    panel.setdefault("options", {}).update(cellHeight="sm" if compact else "md")
    custom = (
        panel.setdefault("fieldConfig", {})
        .setdefault("defaults", {})
        .setdefault("custom", {})
    )
    custom.update(inspect=True)


def _flex(panel: dict, names: set[str]) -> None:
    for item in panel["fieldConfig"].get("overrides", []):
        if item.get("matcher", {}).get("options") in names:
            item["properties"] = [
                p
                for p in item["properties"]
                if p["id"] not in {_WIDTH, "custom.minWidth"}
            ]


def _bands(row: dict, bands: list[list[tuple[int, int, int, int]]]) -> None:
    """Place every child explicitly so repeated generation cannot accumulate shifts."""
    children = {p["id"]: p for p in row["panels"]}
    y = row["gridPos"]["y"] + 1
    placed = []
    for band in bands:
        for panel_id, x, width, height in band:
            panel = children.pop(panel_id)
            panel["gridPos"] = {"x": x, "y": y, "w": width, "h": height}
            placed.append(panel)
        y += max(item[3] for item in band)
    if children:
        raise ValueError(f"Unplaced panels in row {row['id']}: {sorted(children)}")
    row["panels"] = placed


def _runtime(p: dict[int, dict]) -> None:
    p[9400]["options"]["content"] = (
        '<div style="padding:4px 10px;border-left:4px solid #6b7280;font-size:16px;line-height:1.2;white-space:normal;overflow-wrap:anywhere;max-width:96ch">'
        "CURRENT · Pipeline / Run Type. <b>INCOMPLETE / UNKNOWN:</b> expected stage evidence is unverified. "
        "Check <b>Expected stage signals</b>, then open <b>Review Stage Progress</b> below. "
        "SCRAPING is not an active blocker. None observed does not prove completeness or health.</div>"
    )
    # A filtering comparison preserves ages; bool converts each entity to 0/1.
    p[7]["targets"][0]["expr"] = (
        "sum(clamp_min(time() - max by (pipeline, entity) "
        '(bioetl_data_freshness_seconds{pipeline=~"$pipeline"}), 0) > bool 86400) '
        'or (count(bioetl_data_freshness_seconds{pipeline=~"$pipeline"}) * 0)'
    )
    p[7]["targets"][0].update(instant=True, range=False)
    p[7]["fieldConfig"]["defaults"].update(unit="suffix: entities", decimals=0)
    p[7]["description"] = (
        "TIME RANGE · Instant snapshot at the selected range end. Count of distinct pipeline/entity pairs whose last successful ingestion "
        "is over 24h old. Each entity contributes 0 or 1, never its age in seconds. "
        "Missing freshness telemetry stays UNKNOWN; an observed fresh entity gives zero. "
        "Pipeline applies; Run ID and Run Type do not. Use a range ending now for current age. Open Data Quality for diagnosis."
    )
    for panel in p.values():
        if panel.get("title") == "Review Runtime Escalation":
            panel["options"]["mode"] = "html"
            panel["options"]["content"] = (
                '<div style="font-size:16px;line-height:1.2"><b>INCOMPLETE / UNKNOWN:</b> verify Stage Expectedness and Telemetry first. '
                "<b>None observed</b> means no observed blocker, not complete coverage. "
                "Use the Stage Progress panel links for the complete evidence table.</div>"
            )
            panel["gridPos"]["h"] = max(3, panel["gridPos"]["h"])
    note = " INCOMPLETE: inspect expected-stage evidence; no observed blocker is not proof of coverage."
    p[2460]["description"] = p[2460].get("description", "").removesuffix(note) + note


def _replace_rate_intervals(p: dict[int, dict]) -> None:
    for panel in p.values():
        for target in panel.get("targets", []):
            expr = target.get("expr", "")
            if "increase(" in expr or "rate(" in expr:
                target["expr"] = expr.replace("[$__interval]", "[$__rate_interval]")


def _stamp_counter_no_observations(panel: dict) -> None:
    panel["fieldConfig"]["defaults"]["noValue"] = "NO OBSERVATIONS"
    for mapping in panel["fieldConfig"]["defaults"].get("mappings", []):
        if mapping.get("type") == "special" and mapping["options"].get("match") == "null":
            mapping["options"]["result"]["text"] = "NO OBSERVATIONS"
    note = (
        " No observations means this outcome has no samples in the selected window; "
        "it does not prove zero failures. A measured zero is displayed numerically."
    )
    description = panel.get("description", "")
    panel["description"] = (
        description + note if "No observations means" not in description else description
    )


def _disable_cell_wrap(panel: dict) -> None:
    panel["fieldConfig"]["defaults"]["custom"]["cellOptions"] = {
        "type": "auto",
        "wrapText": False,
    }
    for item in panel["fieldConfig"].get("overrides", []):
        for prop in item["properties"]:
            if prop["id"] != _CELL:
                continue
            if item["matcher"].get("options") in {"value", "percentage", "row_status"}:
                prop["value"].pop("wrapText", None)
            else:
                prop["value"]["wrapText"] = False


def _compact_trust_evidence_table(p: dict[int, dict], panel_id: int) -> None:
    panel = p[panel_id]
    _table(panel, compact=False)
    _flex(panel, {"Current", "Value"})
    if panel_id == 9403:
        override(panel, "value", **{_WIDTH: 70})
    panel["options"].setdefault("footer", {}).update(
        enablePagination=True, countRows=True
    )
    # Grafana pagination uses the configured row height. Wrapped cells can
    # exceed it and hide the last row; full values remain available in Inspect.
    _disable_cell_wrap(panel)
    for name in ("Current", "Parameter", "Action"):
        override(panel, name, **{_CELL: {"type": "auto", "wrapText": False}})


def _trust(p: dict[int, dict]) -> None:
    _replace_rate_intervals(p)
    if 5 in p:
        p[5]["targets"][0]["expr"] = (
            "sum by (disposition) (increase(bioetl_checkpoint_compatibility_events_total"
            '{pipeline=~"$pipeline"}[$__rate_interval]))'
        )
    for panel_id in (3, 104, 120, 101, 102, 103, 4, 136, 122, 137):
        if panel_id in p:
            _stamp_counter_no_observations(p[panel_id])
    if 892 in p:
        p[892]["fieldConfig"]["defaults"]["thresholds"] = {
            "mode": "absolute",
            "steps": [{"color": "blue", "value": None}],
        }
        p[892]["description"] = (
            "Last checkpoint age, informational only; age does not change readiness. "
            "Missing evidence remains UNKNOWN. Pipeline-scoped, independent of Run ID."
        )
    # An empty reasons list is valid; query failures remain explicit in Trust.
<<<<<<< HEAD
    override(p[9418], "Reasons", **{"noValue": "—"})
||||||| 2d9509c4d82f
    override(p[9418], "Reasons", **{"noValue": "—"})
    latency = p[111]
    latency["fieldConfig"]["defaults"]["color"] = {"mode": "palette-classic"}
    latency["options"]["legend"] = {
        "displayMode": "table",
        "placement": "right",
        "showLegend": True,
        "calcs": ["lastNotNull", "max"],
        "width": 430,
    }
    latency["gridPos"]["h"] = 10
=======
    override(p[9418], "Reason count", **{"noValue": "—", "links": []})
>>>>>>> main
    if 111 in p:
        latency = p[111]
        latency["fieldConfig"]["defaults"]["color"] = {"mode": "palette-classic"}
        latency["options"]["legend"] = {
            "displayMode": "table",
            "placement": "right",
            "showLegend": True,
            "calcs": ["lastNotNull", "max"],
            "width": 430,
        }
        latency["gridPos"]["h"] = 10
    for panel_id in (9404, 9405, 9406, 9407, 9408, 9409, 9402, 9403, 9417):
        if panel_id in p:
            _compact_trust_evidence_table(p, panel_id)
    _bands(
        p[905],
        [
            [(9404, 0, 24, 12)],
            [(9407, 0, 24, 8)],
            [(9410, 0, 12, 5), (9411, 12, 12, 5)],
            [(9405, 0, 24, 7)],
            [(9408, 0, 24, 12)],
            [(9406, 0, 24, 12)],
            [(9409, 0, 24, 12)],
            [(139, 0, 24, 4)],
        ],
    )
    _bands(p[9412], [[(9402, 0, 24, 12)], [(9403, 0, 24, 12)], [(9417, 0, 24, 7)]])


_ACTION_LABELS = {
    "Runtime": "Pipeline Diagnostics",
    "Runtime (wf)": "Pipeline Diagnostics",
    "Control Plane": "Trust",
    "DQ": "Data Quality",
    "Provider": "Provider Health",
}


def _remap_action_label_texts(panel: dict) -> None:
    for item in panel["fieldConfig"]["overrides"]:
        for prop in item["properties"]:
            if prop["id"] != "mappings":
                continue
            for mapping in prop["value"]:
                _remap_mapping_texts(mapping)


def _remap_mapping_texts(mapping: dict) -> None:
    for value in mapping.get("options", {}).values():
        if isinstance(value, dict):
            value["text"] = _ACTION_LABELS.get(
                value.get("text"), value.get("text", "")
            )


def _overview(p: dict[int, dict]) -> None:
    # Run ID is always selected. Fleet cards are removed before this pass on
    # later renders; nothing here should recreate them.
    if 214 not in p or 215 not in p:
        return
    # Align the current verdict with the selected-run domains column below it.
    p[99]["gridPos"].update(x=0, w=16)
    p[214]["gridPos"].update(x=16, w=p[9002]["gridPos"]["w"])
    for panel_id in (215, 20215):
        panel = p[panel_id]
        _table(panel)
        _flex(panel, {"action_reason", "Priority", "Action"})
        for name in ("action_target",):
            override(
                panel,
                name,
                **{
                    _WIDTH: 210,
                    _CELL: {"type": "auto", "wrapText": True},
                },
            )
        _remap_action_label_texts(panel)
    _table(p[20215], compact=False)
    # Reserve only the short label columns; leave the explanation responsive.
    for name, width in (("Priority", 80), ("Pipeline", 120), ("action_target", 190)):
        override(p[215], name, **{_WIDTH: width})
    p[20215]["gridPos"]["h"] = 14
    # Retain domain-specific links and queries, but compare the six diagnostics in one banded grid.
    _bands(
        p[9012],
        [
            [(9006, 0, 8, 4), (9003, 8, 8, 4), (9004, 16, 8, 4)],
            [(9007, 0, 8, 4), (9005, 8, 8, 4), (9013, 16, 8, 4)],
            [(9021, 0, 24, 3)],
        ],
    )


def _provider_status_columns(p: dict[int, dict]) -> None:
    # Compact categorical columns; let the explanatory column take spare width.
    _flex(p[9101], {"provider", "Provider", "Value", "Severity"})
    override(p[9101], "Severity", **{_WIDTH: 130, "custom.align": "left"})
    _flex(p[9107], {"provider", "Provider", "reason", "Source state", "Status"})
    for name, width in (("Provider", 105), ("Source state", 105), ("Status", 110)):
        override(p[9107], name, **{_WIDTH: width, "custom.align": "left"})
    override(p[9107], "reason", **{"displayName": "Reason"})
    for panel_id in (9103, 9113):
        _table(p[panel_id])
        _flex(p[panel_id], {"cause", "Cause"})
        override(
            p[panel_id],
            "cause",
            **{_CELL: {"type": "auto", "wrapText": True}},
        )


def _provider_latency_panels(p: dict[int, dict]) -> None:
    p[102]["options"]["textMode"] = "value_and_name"
    p[102]["fieldConfig"]["defaults"].pop("displayName", None)
    p[102]["gridPos"]["h"] = 5
    for panel_id in (1, 110):
        panel = p[panel_id]
        panel["options"]["legend"] = {
            "displayMode": "table",
            "placement": "bottom",
            "showLegend": True,
            "calcs": ["lastNotNull"],
        }
        custom = panel["fieldConfig"]["defaults"].setdefault("custom", {})
        custom.update(
            drawStyle="line",
            showPoints="always",
            stacking={"mode": "none", "group": "A"},
        )
        panel["description"] = (
            "TIME RANGE · Optional latency samples only. Empty/NaN is TELEMETRY MISSING, not zero latency or a healthy provider. Check telemetry presence above."
        )
        panel["fieldConfig"]["defaults"]["noValue"] = "TELEMETRY MISSING"
    p[110]["options"]["legend"].update(placement="right", width=400)


def _rename_raw_count_header(raw: dict) -> None:
    for item in raw["fieldConfig"]["overrides"]:
        for prop in item["properties"]:
            if prop["id"] == "displayName" and prop["value"] == "Count":
                prop["value"] = "Best raw status in range"


def _provider_raw_health(raw: dict) -> None:
    _table(raw)
    _rename_raw_count_header(raw)
    _flex(raw, {"Value"})
    raw["description"] = (
        "TIME RANGE / DIAGNOSTIC · 0=UNHEALTHY, 1=DEGRADED, 2=HEALTHY; null/NaN=UNKNOWN. Raw provider health enum evidence: best observed status in the selected range, "
        "not the canonical first-screen verdict. When raw status is absent, status is UNKNOWN. "
        "A past HEALTHY observation does not establish current freshness. "
        "Last check and age describe the latest observation, not necessarily the best status. "
        "Use Status Reason / Telemetry Presence for the current verdict."
    )
    raw["targets"] = raw["targets"][:1]
    universe = 'max by (provider) (max_over_time(bioetl_provider_health_check_provider_universe_15m{provider=~"$provider"}[${__range_s}s]))'
    raw["targets"][0]["expr"] = (
        'max by (provider) (max_over_time(bioetl_provider_health_status{provider=~"$provider"}[${__range_s}s])) '
        f"or on (provider) (({universe} * 0) / ({universe} * 0))"
    )
    for ref, expression in (
        (
            "B",
            'max by (provider) (max_over_time(bioetl_provider_health_observed_timestamp_seconds{provider=~"$provider"}[${__range_s}s])) * 1000',
        ),
        (
            "C",
            'clamp_min(time() - max by (provider) (max_over_time(bioetl_provider_health_observed_timestamp_seconds{provider=~"$provider"}[${__range_s}s])), 0)',
        ),
    ):
        raw["targets"].append(
            {"refId": ref, "expr": expression, "format": "table", "instant": True}
        )
    raw["transformations"] = [
        {
            "id": "joinByField",
            "options": {"byField": "provider", "mode": "outer"},
        },
        {
            "id": "organize",
            "options": {
                "excludeByName": {
                    "Time": True,
                    "Time 1": True,
                    "Time 2": True,
                    "Time 3": True,
                    "__name__": True,
                },
                "renameByName": {
                    "Value #A": "Best status · range",
                    "Value #B": "Last check",
                    "Value #C": "Observation age",
                },
            },
        },
    ]
    raw["fieldConfig"]["overrides"] = [
        item
        for item in raw["fieldConfig"]["overrides"]
        if item["matcher"]["id"] != "byRegexp"
    ]
    for name, unit in (
        ("Last check", "time:YYYY-MM-DD HH:mm"),
        ("Observation age", "s"),
    ):
        override(
            raw,
            name,
            **{
                "unit": unit,
                "mappings": [],
                "color": {"mode": "fixed", "fixedColor": "text"},
                "noValue": "UNKNOWN",
            },
        )


def _provider_disable_summary_wrap(p: dict[int, dict]) -> None:
    for panel_id in (9402, 9403):
        _table(p[panel_id], compact=False)
        p[panel_id]["options"].pop("enablePagination", None)
        p[panel_id]["options"]["footer"].update(enablePagination=True, countRows=True)
        for item in p[panel_id]["fieldConfig"].get("overrides", []):
            _clear_wrap_text(item)


def _clear_wrap_text(item: dict) -> None:
    for prop in item["properties"]:
        if prop["id"] == _CELL and "wrapText" in prop["value"]:
            prop["value"]["wrapText"] = False


def _provider(p: dict[int, dict]) -> None:
    if 9105 not in p or 91 not in p or 9404 not in p:
        if 9402 in p and 9403 in p:
            _provider_disable_summary_wrap(p)
        return
    _provider_status_columns(p)
    _bands(p[9105], [[(9111, 0, 12, 5), (9112, 12, 12, 5)], [(9113, 0, 24, 5)]])
    _provider_latency_panels(p)
    _provider_raw_health(p[114])
    _bands(
        p[9404],
        [
            [(114, 0, 12, 7), (1, 12, 12, 7)],
            [(2, 0, 12, 3), (105, 12, 12, 3)],
            [(104, 0, 12, 3), (7, 12, 12, 3)],
        ],
    )
    _bands(
        p[91],
        [
            [(106, 0, 24, 5)],
            [(107, 0, 24, 4)],
            [(108, 0, 24, 4)],
            [(109, 0, 24, 5)],
            [(102, 0, 8, 10), (110, 8, 16, 10)],
            [(111, 0, 12, 5), (115, 12, 12, 5)],
            [(112, 0, 12, 5), (113, 12, 12, 5)],
            [(31, 0, 12, 5), (32, 12, 12, 5)],
        ],
    )
    _provider_disable_summary_wrap(p)
    _bands(p[9405], [[(9402, 0, 24, 12)], [(9403, 0, 24, 12)]])


def _dq(p: dict[int, dict]) -> None:
    if 2 not in p:
        return
    for panel_id in (2, 5):
        p[panel_id]["options"]["textMode"] = "value_and_name"
        p[panel_id]["fieldConfig"]["defaults"]["displayName"] = (
            "Measured scores · 7d lookback"
        )
    graph = p[153]
    graph["fieldConfig"]["defaults"]["color"] = {
        "mode": "thresholds",
        "seriesBy": "min",
    }
    graph["fieldConfig"]["defaults"].setdefault("custom", {}).update(
        gradientMode="none", spanNulls=False, showPoints="always", fillOpacity=0
    )
    graph["fieldConfig"]["defaults"]["thresholds"] = deepcopy(
        p[2]["fieldConfig"]["defaults"]["thresholds"]
    )
    graph["options"]["legend"] = {
        "displayMode": "list",
        "placement": "bottom",
        "showLegend": True,
    }
    graph["targets"][0]["legendFormat"] = "DQ score (color=minimum observed)"
    graph["description"] = (
        "TIME RANGE · Observed volume-weighted DQ score, separate from current "
        "operational status and the 7d retained stat. Line and legend color use "
        "the minimum observed score in this range, with the stat's thresholds. "
        "Missing intervals remain gaps and do not recolor history. "
        "100% does not prove current completeness. UNKNOWN / TELEMETRY MISSING "
        "means no observed samples, not zero; full identifiers remain available "
        "in the series legend and tooltip."
    )
    row = p[9404]
    row["panels"] = [child for child in row["panels"] if child["id"] not in {157, 158}]
    context = {
        "id": 157,
        "type": "text",
        "title": "Review DQ Coverage",
        "options": {
            "mode": "markdown",
            "content": "**Measured data only · last 7 days.** Record count below is the score denominator; entity count is observed score coverage, not expected coverage. DQ validation time is not recorded by these metrics. Data freshness is separate. Run ID does not filter these scores; 100% does not prove current completeness.",
        },
    }
    coverage = deepcopy(p[2])
    coverage.update(id=158, title="Inspect DQ Sample Coverage")
    coverage["fieldConfig"]["defaults"] = {
        "unit": "short",
        "decimals": 0,
        "noValue": "UNKNOWN",
        "color": {"mode": "thresholds"},
        "thresholds": {"mode": "absolute", "steps": [{"color": "gray", "value": None}]},
        "mappings": [
            {
                "type": "special",
                "options": {
                    "match": "null",
                    "result": {"text": "UNKNOWN", "color": "gray"},
                },
            }
        ],
    }
    coverage["description"] = (
        "TIME RANGE · Observed coverage over the fixed 7d score lookback. Not expected coverage; missing telemetry remains UNKNOWN."
    )
    coverage["targets"] = [
        {
            "refId": "A",
            "expr": 'sum(last_over_time(bioetl_dq_validation_record_count{pipeline=~"$pipeline"}[7d]))',
            "legendFormat": "Records in denominator",
            "instant": True,
        },
        {
            "refId": "B",
            "expr": 'count(last_over_time(bioetl_dq_validation_score{pipeline=~"$pipeline"}[7d]))',
            "legendFormat": "Observed score series",
            "instant": True,
        },
    ]
    row["panels"].extend([context, coverage])
    _bands(
        row,
        [
            [(157, 0, 24, 3)],
            [(2, 0, 8, 4), (5, 8, 8, 4), (8, 16, 8, 4)],
            [(158, 0, 24, 4)],
            [(154, 0, 8, 3), (6, 8, 8, 3), (117, 16, 8, 3)],
        ],
    )


def _incident(p: dict[int, dict]) -> None:
    timeline = p[2006]
    timeline["targets"][0]["legendFormat"] = (
        "{{alertname}} · {{pipeline}} / {{entity}} {{provider}} · {{alertstate}}"
    )
    timeline["options"].update(pageSize=10, rowHeight=0.85)
    timeline["fieldConfig"]["defaults"]["custom"]["axisWidth"] = 650
    timeline["gridPos"]["h"] = 14
    p[2007]["gridPos"]["y"] = timeline["gridPos"]["y"] + 14
    for panel_id in (2005, 22005):
        override(
            p[panel_id],
            "alertstate",
            **{
                "mappings": [
                    {
                        "type": "value",
                        "options": {
                            "firing": {"text": "FIRING", "color": "#ff7383"},
                            "pending": {"text": "PENDING", "color": "#ffb357"},
                        },
                    }
                ],
                _CELL: {"type": "color-text"},
            },
        )


def apply_visual_usability(payload: dict) -> None:
    """Apply presentation-only fixes, plus the explicitly tested stale-entity count."""
    if "uid" not in payload:
        return
    p = {panel["id"]: panel for panel in walk(payload["panels"])}
    handlers = {
        "bioetl-runtime": _runtime,
        "bioetl-control-plane-v1": _trust,
        "bioetl-overview-v2": _overview,
        "bioetl-provider-health-v2": _provider,
        "bioetl-dq-v2": _dq,
        "bioetl-incident-v1": _incident,
    }
    if handler := handlers.get(payload["uid"]):
        handler(p)
    if payload["uid"] == "bioetl-dq-v2" and 9103 in p:
        p[9103]["gridPos"]["h"] = 2
    if payload["uid"] == "bioetl-incident-v1":
        p[2001]["gridPos"].update(y=5, h=3)
    # Keep useful evidence tables compact with explicit pagination, not huge repeated placeholders.
    p[9452]["gridPos"].update(y=p[9451]["gridPos"]["y"] + 12, h=7)
    p[9451]["gridPos"]["h"] = 12
    for panel_id in (9451, 9452):
        _table(p[panel_id], compact=False)
    if payload["uid"] == "bioetl-run-explorer-v1":
        _table(p[3010])
        _flex(p[3010], {"Run", "run_id"})
    # Native title chrome and typography remain untouched; preserve two wrapped link rows.
    p[1000]["gridPos"]["h"] = 2
    first_y = min(
        panel["gridPos"]["y"] for panel in payload["panels"] if panel["id"] != 1000
    )
    shift = max(0, first_y - 2)
    first_window = [
        panel
        for panel in payload["panels"]
        if panel["id"] != 1000 and panel["type"] != "row"
    ]
    bottom = max(
        panel["gridPos"]["y"] + panel["gridPos"]["h"] for panel in first_window
    )
    for panel in first_window:
        if panel["gridPos"]["y"] + panel["gridPos"]["h"] == bottom:
            panel["gridPos"]["h"] += shift
        if panel["id"] != 1000:
            panel["gridPos"]["y"] -= shift
