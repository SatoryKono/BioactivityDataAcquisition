"""Compact, persisted identity for the Overview first window."""

from copy import deepcopy

from scripts.ops.observability.grafana._incident_explanations import (
    preserve_evidence_rows,
)
from scripts.ops.observability.grafana._overview_global_alerts import (
    build_fleet_alert_card,
)

CUSTOM_WIDTH = "custom.width"
OVERALL_VERDICT = "Overall verdict"


def apply_overview_identity(payload: dict) -> None:
    """Keep only the compact exact-run identity on Overview."""
    panels = payload["panels"]
    panels[:] = [panel for panel in panels if panel.get("id") not in {9301, 9399, 9390}]
    by_id = {panel["id"]: panel for panel in panels}
    by_id[9002]["gridPos"].update(x=0, y=5, w=15, h=8)
    by_id[9603]["gridPos"].update(x=15, y=5, w=9, h=5)
    identity = next(p for p in panels if p.get("id") == 9300)
    identity["gridPos"].update(x=15, y=10, w=9, h=8)
    for pid in (9002, 9603):
        by_id[pid]["options"]["cellHeight"] = "sm"
    # Preserve the shipped 200% CSS budget and leave Reason flexible.
    widths = {OVERALL_VERDICT: 60, "Processing": 95, "Trust": 60, "Result": 80}
    for override in by_id[9603]["fieldConfig"]["overrides"]:
        field = override["matcher"].get("options")
        if field not in widths and field != "Status":
            continue
        props = override["properties"]
        width = widths.get(field)
        if field == OVERALL_VERDICT and not any(
            prop.get("id") == "displayName" for prop in props
        ):
            width = None
        current = [prop for prop in props if prop.get("id") == CUSTOM_WIDTH]
        expected = [] if width is None else [{"id": CUSTOM_WIDTH, "value": width}]
        if current != expected:
            override["properties"] = [
                prop for prop in props if prop.get("id") != CUSTOM_WIDTH
            ] + expected
    # Provider evidence is now local. Keep the three domain actions discoverable
    # without forwarding legacy provider selectors that Overview does not own.
    links = by_id[9002]["fieldConfig"]["defaults"].setdefault("links", [])
    links[:] = [link for link in links if link.get("title") != "Open Provider Evidence"]
    links.append(
        {
            "title": "Open Provider Evidence",
            "url": "/d/bioetl-overview-v2/3-run-overview?${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}&${run_id:queryparam}&viewPanel=9480&${__url_time_range}",
            "includeVars": False,
            "targetBlank": False,
        }
    )
    target = identity["targets"][0]
    target.update(
        url="/ops/observability/selected-run-status?pipeline=${selected_pipeline}&run_type=${run_type:csv}&run_id=${selected_run_id}&workflow=${workflow:csv}",
        root_selector=(
            '($v := function($x){$exists($x) and $x != "" ? $string($x) : '
            '"Not recorded in saved run evidence"}; '
            "$s := summary[0]; "
            "$start := $s.started_at ? $toMillis($s.started_at) : null; "
            "$end := $s.completed_at ? $toMillis($s.completed_at) : null; ["
            '{"parameter":"Run ID","value":$v(run_id)},'
            '{"parameter":"Pipeline","value":$v(pipeline)},'
            '{"parameter":"Run Type","value":$v(run_type)},'
            '{"parameter":"Started at","value":'
            'started_at ? $substring(started_at,0,10) & " " & '
            '$substring(started_at,11,5) & " " & '
            '($substring(started_at,-1) = "Z" ? "UTC" : $substring(started_at,-6)) : '
            '"Not recorded in saved run evidence"},'
            '{"parameter":"Total Run Duration","value":'
            "$start != null and $end != null and $end >= $start ? "
            "($n := $floor(($end - $start) / 1000 + 0.5); "
            "$parts := [$floor($n / 86400), $floor(($n % 86400) / 3600), "
            "$floor(($n % 3600) / 60), $n % 60]; "
            '$units := [" d", " h", " min", " s"]; '
            '$n = 0 ? "0 s" : $join($map($parts, function($v, $i){'
            '$v > 0 ? $string($v) & $units[$i]}), " ")) : '
            '"Not recorded in saved run evidence"}])'
        ),
    )
    # Use the same browser JSONata evaluator as the duration stat. The backend
    # evaluator does not preserve these ISO timestamp conversions correctly.
    target.update(
        parser="uql",
        uql='parse-json | jsonata "'
        + target["root_selector"].replace('"', '\\"')
        + '"',
    )
    identity["description"] = (
        "SELECTED RUN · Pipeline and full Run ID identify the saved run. "
        "Run Type and Started at (with saved UTC offset) characterize its execution. "
        "SELECT RUN means no selected run context. Missing saved values are Not recorded; request failures remain QUERY ERROR."
    )
    identity["options"] = {
        "showHeader": True,
        "cellHeight": "sm",
        "footer": {"show": False, "enablePagination": False},
    }
    identity["fieldConfig"] = {
        "defaults": {
            "custom": {
                "align": "left",
                "inspect": True,
                "wrapText": True,
                "cellOptions": {"type": "auto", "wrapText": True},
            }
        },
        "overrides": [
            {
                "matcher": {"id": "byName", "options": "Parameter"},
                "properties": [{"id": CUSTOM_WIDTH, "value": 100}],
            }
        ],
    }

    # The fixed five-parameter projection retains every identity value.
    identity["transformations"] = [
        {"id": "limit", "options": {"limitField": 5}},
        {
            "id": "organize",
            "options": {
                "indexByName": {"parameter": 0, "value": 1},
                "renameByName": {"parameter": "Parameter", "value": "Value"},
            },
        },
    ]


def _tune_saved_status_properties(name: str, properties: list[dict]) -> None:
    for prop in properties:
        if prop["id"] == CUSTOM_WIDTH and name in {"Processing", "Trust"}:
            prop["value"] = 95 if name == "Processing" else 60
        if prop["id"] == "mappings" and name == "Reason":
            mapping = {
                "type": "value",
                "options": {
                    "Saved run evidence; CURRENT and chart coverage are separate": {
                        "text": "Saved run evidence"
                    }
                },
            }
            if mapping not in prop["value"]:
                prop["value"].append(mapping)


def _tune_saved_status_overrides(overrides: list[dict]) -> None:
    for item in overrides:
        name = item["matcher"].get("options")
        _tune_saved_status_properties(name, item["properties"])
    verdict_override = {
        "matcher": {"id": "byName", "options": OVERALL_VERDICT},
        "properties": [
            {"id": "displayName", "value": "Verdict"},
            {"id": CUSTOM_WIDTH, "value": 60},
        ],
    }
    if verdict_override not in overrides:
        overrides.append(verdict_override)


def _link_saved_status(overrides: list[dict]) -> None:
    for item in overrides:
        if item["matcher"].get("options") == "Status":
            for prop in item["properties"]:
                if prop["id"] == "links":
                    prop["value"] = [
                        {
                            "title": "Open saved run report",
                            "url": "/api/datasources/proxy/uid/bioetl-ops-http/ops/observability/pipeline-run-report-artifact?pipeline=${selected_pipeline:percentencode}&run_id=${selected_run_id:percentencode}&format=pipeline_run_report_json",
                            "targetBlank": True,
                        }
                    ]


def _link_saved_evidence(overview: dict) -> None:
    for pid in (9002, 9603):
        for item in overview[pid]["fieldConfig"]["overrides"]:
            if item["matcher"].get("options") == "Reason":
                mappings = next(
                    p["value"] for p in item["properties"] if p["id"] == "mappings"
                )
                mappings.append(
                    {
                        "type": "regex",
                        "options": {
                            "pattern": "^(Workflow: )?workflow_parent_not_finalized$",
                            "result": {
                                "text": "Parent workflow completion has not been recorded"
                            },
                        },
                    }
                )
    _link_saved_status(overview[9002]["fieldConfig"]["overrides"])


def apply_saved_evidence_readability(payload: dict) -> None:
    """Present saved domains and full identity without redundant table columns."""
    if payload.get("uid") != "bioetl-overview-v2":
        return
    row = next(p for p in payload["panels"] if p.get("id") == 9450)
    row["panels"] = [p for p in row["panels"] if p.get("id") != 9451]
    row["description"] = (
        "Expand for full saved identity of the selected Run ID. Stages are shown above."
    )
    panels = {p["id"]: p for p in row["panels"]}
    overview = {p["id"]: p for p in payload["panels"]}
    _tune_saved_status_overrides(overview[9603]["fieldConfig"]["overrides"])
    _link_saved_evidence(overview)
    stages = panels[9460]
    provider = next(p for p in payload["panels"] if p.get("id") == 9480)
    stages["gridPos"]["w"] = provider["gridPos"]["w"]
    # Filter after the outer join so artifact counters cannot restore extract.
    stages["transformations"].insert(
        1,
        {
            "id": "filterByValue",
            "options": {
                "type": "exclude",
                "match": "any",
                "filters": [
                    {
                        "fieldName": "stage_id",
                        "config": {"id": "equal", "options": {"value": "extract"}},
                    }
                ],
            },
        },
    )
    for transform in stages["transformations"]:
        if transform["id"] == "filterFieldsByName":
            names = transform["options"]["include"]["names"]
            transform["options"]["include"]["names"] = [
                name
                for name in names
                if name not in {"reason", "source", "Source", "Evidence"}
            ]
        elif transform["id"] == "organize":
            transform["options"].setdefault("excludeByName", {}).update(
                reason=True,
                source=True,
                Source=True,
                Evidence=True,
            )

    report_links = next(
        prop["value"]
        for item in stages["fieldConfig"]["overrides"]
        if item["matcher"].get("options") == "source"
        for prop in item["properties"]
        if prop["id"] == "links"
    )
    stages["fieldConfig"]["overrides"].append(
        {
            "matcher": {"id": "byRegexp", "options": "^(state|Status)$"},
            "properties": [{"id": "links", "value": report_links}],
        }
    )

    def override(name, properties):
        return {"matcher": {"id": "byName", "options": name}, "properties": properties}

    identity = panels[9452]
    expression = (
        '($s := summary[0]; $v := function($x){$exists($x) and $x != null and $x != "" ? $string($x) : "Not recorded"}; ['
        '{"parameter":"Pipeline","value":$v($s.pipeline)},'
        '{"parameter":"Run ID","value":$v($s.run_id)},'
        '{"parameter":"Completed","value":$v($s.completed_at)},'
        '{"parameter":"Assessment rules","value":$v($s.rules_version)},'
        '{"parameter":"Source revision","value":$v($s.revision)},'
        '{"parameter":"Evidence completeness","value":$v($s.evidence_completeness)}])'
    )
    identity["targets"][0].update(
        parser="uql",
        root_selector=expression,
        uql='parse-json | jsonata "' + expression.replace('"', '\\"') + '"',
    )
    identity["transformations"] = [
        {
            "id": "organize",
            "options": {
                "indexByName": {"parameter": 0, "value": 1},
                "renameByName": {"parameter": "Parameter", "value": "Value"},
            },
        }
    ]
    identity["options"].update(
        cellHeight="sm", footer={"show": False, "enablePagination": False}
    )
    identity["fieldConfig"]["defaults"]["custom"].update(
        inspect=True,
        cellOptions={"type": "auto", "wrapText": True},
        wrapText=True,
    )
    identity["fieldConfig"]["overrides"] = [
        override("Parameter", [{"id": CUSTOM_WIDTH, "value": 210}]),
        override(
            "Value",
            [
                {"id": "custom.inspect", "value": True},
                {
                    "id": "mappings",
                    "value": [
                        {
                            "type": "regex",
                            "options": {
                                "pattern": "^([a-fA-F0-9]{12})(?:[a-fA-F0-9]{28}|[a-fA-F0-9]{52})$",
                                "result": {"text": "$1…"},
                            },
                        }
                    ],
                },
            ],
        ),
    ]
    identity["description"] = (
        "SELECTED RUN · Full Run ID can be copied through cell inspection. Inspect Source revision to view and copy the complete hash. Missing values are Not recorded; failed requests remain QUERY ERROR."
    )
    identity["gridPos"]["h"] = 7
    _place_stages_and_quality(payload, row, stages)
    y = row["gridPos"]["y"] + 1
    for panel in row["panels"]:
        panel["gridPos"]["y"] = y
        y += panel["gridPos"]["h"]


def _place_stages_and_quality(payload: dict, row: dict, stages: dict) -> None:
    """Pair saved stages with a count-based exclusion assessment outside the row."""
    from copy import deepcopy

    panels = payload["panels"]
    provider = next(p for p in panels if p.get("id") == 9480)
    y = provider["gridPos"]["y"] + provider["gridPos"]["h"]
    stages["gridPos"] = {"x": 0, "y": y, "w": 15, "h": 6}
    stages["options"].update(cellHeight="sm", footer={"show": False})
    percentages = (
        "($ratio := function($s,$n){$s.tracking='full' and $type($s.records_in)='number' "
        "and $type($n)='number' ? ($s.records_in>0 and $n>=0 and $n<=$s.records_in "
        "? 100*$n/$s.records_in : null) : null}; "
        "$map(funnel,function($s){($excluded := $s.tracking='full' and $type($s.removals)='array' "
        "? $sum($append([0],$s.removals[outcome='excluded_by_contract'].count)) : null; "
        "{'stage_id':$s.stage_id,'excluded_pct':$ratio($s,$excluded),"
        "'saved_pct':$ratio($s,$s.records_out)})}))"
    )
    percentage_target = deepcopy(stages["targets"][1])
    percentage_target.update(
        refId="C",
        root_selector=percentages,
        uql='parse-json | jsonata "' + percentages + '"',
    )
    stages["targets"].append(percentage_target)
    for transform in stages["transformations"]:
        if transform["id"] == "filterFieldsByName":
            transform["options"]["include"]["names"].extend(
                ["excluded_pct", "saved_pct"]
            )
    stages["description"] += (
        " Excluded % is excluded_by_contract / stage records in; Saved % is records out / stage records in. Empty or incomplete inputs are UNKNOWN."
    )
    for field, label, width in (
        ("stage_id|Stage", "Stage", 65),
        ("records_in|Records in", "In", 50),
        ("records_out|Records out", "Out", 50),
        ("state|Status", "Status", 65),
        ("source|Source", "Evidence", 90),
        ("quarantined|Quarantined", "Quar.", 60),
        ("excluded|Excluded", "Excluded", 85),
        ("deduplicated|Deduplicated", "Dedup.", 65),
        ("filtered_out|Filtered out", "Filtered", 65),
        ("excluded_pct", "Excl. %", 70),
        ("saved_pct", "Saved %", 75),
    ):
        stages["fieldConfig"]["overrides"].append(
            {
                "matcher": {"id": "byRegexp", "options": f"^({field})( [BC])?$"},
                "properties": [
                    {"id": "displayName", "value": label},
                    {"id": CUSTOM_WIDTH, "value": width},
                ],
            }
        )
    stages["fieldConfig"]["overrides"].append(
        {
            "matcher": {
                "id": "byRegexp",
                "options": "^(excluded_pct|saved_pct|Excl[.] %|Saved %)( C)?$",
            },
            "properties": [
                {"id": "unit", "value": "percent"},
                {"id": "decimals", "value": 1},
            ],
        }
    )
    # Let Grafana distribute available panel width across visible columns.
    stages["fieldConfig"]["defaults"].setdefault("custom", {}).pop("width", None)
    stages["fieldConfig"]["defaults"]["custom"]["minWidth"] = 50
    for override in stages["fieldConfig"]["overrides"]:
        override["properties"] = [
            prop for prop in override["properties"] if prop["id"] != CUSTOM_WIDTH
        ]
    row["panels"] = [p for p in row["panels"] if p.get("id") != 9460]
    row["gridPos"]["y"] = y + 6
    quality = deepcopy(next(p for p in panels if p.get("id") == 9481))
    quality.update(
        id=9482,
        title="Review Contract Exclusions",
        gridPos={"x": 15, "y": y, "w": 9, "h": 6},
        description=(
            "SELECTED RUN · Excluded-by-contract records summed across Bronze, Silver and Gold. "
            "Exclusion rate uses Bronze records out: below soft limit OK, at soft limit WARN, at hard limit CRIT. "
            "Limits come from pipeline configuration at dashboard generation, not historical run overrides. "
            "UNKNOWN means incomplete tracking or invalid counters; SELECT RUN requires a Run ID. "
            "Failed requests remain QUERY ERROR. Quarantined, filtered and deduplicated records "
            "are separate outcomes and are not included."
        ),
    )
    from ._overview_quality import exclusion_quality_expression

    expression = exclusion_quality_expression()
    target = deepcopy(stages["targets"][1])
    target.update(
        refId="A",
        url=(
            "/ops/observability/selected-run-status?pipeline=${pipeline:percentencode}"
            "&run_id=${run_id:percentencode}&run_type=${run_type:csv}&workflow=${workflow:csv}"
        ),
        root_selector=expression,
        uql='parse-json | jsonata "' + expression.replace('"', '\\"') + '"',
    )
    quality["targets"] = [target]
    quality["transformations"] = []
    quality["fieldConfig"] = {
        "defaults": {
            "noValue": "UNKNOWN",
            "mappings": [
                {
                    "type": "regex",
                    "options": {"pattern": "^OK.*", "result": {"color": "green"}},
                },
                {
                    "type": "regex",
                    "options": {"pattern": "^WARN.*", "result": {"color": "orange"}},
                },
                {
                    "type": "regex",
                    "options": {"pattern": "^CRIT.*", "result": {"color": "red"}},
                },
                {
                    "type": "regex",
                    "options": {"pattern": "^ERROR.*", "result": {"color": "red"}},
                },
                {
                    "type": "value",
                    "options": {
                        "UNKNOWN": {"text": "UNKNOWN", "color": "gray"},
                        "SELECT RUN": {"text": "SELECT RUN", "color": "gray"},
                        "NO RUNS": {
                            "text": "NO RUNS",
                            "color": "gray",
                        },
                    },
                },
            ],
            "color": {"mode": "fixed", "fixedColor": "gray"},
        },
        "overrides": [],
    }
    # Native Stat titles ignore field colors. Canvas binds both lines to status.
    quality["type"] = "canvas"
    quality["options"] = {
        "inlineEditing": False,
        "panZoom": False,
        "zoomToContent": False,
        "tooltip": {"mode": "none"},
        "root": {
            "name": "Quality assessment",
            "type": "frame",
            "elements": [
                {
                    "name": field,
                    "type": "metric-value",
                    "config": {
                        "align": "center",
                        "valign": "middle",
                        "size": size,
                        "text": {"mode": "field", "field": field, "fixed": ""},
                        "color": {"field": "status", "fixed": "gray"},
                    },
                    # F-05 / §1.3: top/bottom halves — no overlapping ±center offsets.
                    "constraint": {"horizontal": "leftright", "vertical": "top"},
                    "placement": {"left": 8, "right": 8, "top": top, "height": 70},
                    "background": {"color": {"fixed": "transparent"}},
                }
                for field, size, top in (("status", 40, 8), ("detail", 16, 88))
            ],
        },
    }
    panels[:] = [p for p in panels if p.get("id") not in {9460, 9482}]
    panels.extend([stages, quality])
    _apply_reconciliation_evidence(payload)
    panels.sort(key=lambda p: (p["gridPos"]["y"], p["gridPos"]["x"]))


def _apply_reconciliation_evidence(payload: dict) -> None:
    """Show bounded comparison separately from saved trust and replay verdicts."""
    panels = payload["panels"]
    panels[:] = [panel for panel in panels if panel.get("id") != 9483]
    columns = {
        "step_id": "Workflow step",
        "mode": "Mode",
        "scope": "Row scope",
        "pins": "Compared snapshots",
        "limit": "Limit",
        "result": "Result",
        "meaning": "Interpretation",
    }
    panels.append(
        {
            "id": 9483,
            "type": "table",
            "title": "Review FK Comparison Scope",
            "description": (
                "SELECTED RUN · Persisted FK comparison in the exact parent workflow. "
                "selected-snapshot means absence only inside the pinned reference, "
                "not absence from the complete provider. Expiry can affect all selected "
                "rows while execution succeeds; remaining rows and scope stay explicit. "
                "Missing evidence is UNKNOWN and failed requests remain QUERY ERROR. "
                "Saved Evidence and Replay Readiness retain their independent checks."
            ),
            "gridPos": {"x": 0, "y": 29, "w": 24, "h": 6},
            "datasource": {
                "type": "yesoreyeram-infinity-datasource",
                "uid": "bioetl-ops-http",
            },
            "targets": [
                {
                    "refId": "A",
                    "type": "json",
                    "source": "url",
                    "format": "table",
                    "parser": "backend",
                    "url": (
                        "/ops/observability/selected-run-status?pipeline=${selected_pipeline}"
                        "&run_id=${selected_run_id}&run_type=${run_type:csv}&workflow=${workflow:csv}"
                    ),
                    "url_options": {"method": "GET", "data": ""},
                    "root_selector": "reconciliation_display",
                    "columns": [
                        {"selector": key, "text": title, "type": "string"}
                        for key, title in columns.items()
                    ],
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "noValue": "UNKNOWN",
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
                        "properties": [{"id": CUSTOM_WIDTH, "value": width}],
                    }
                    for name, width in (
                        ("Workflow step", 240),
                        ("Mode", 100),
                        ("Row scope", 100),
                        ("Compared snapshots", 150),
                        ("Limit", 80),
                        ("Result", 90),
                    )
                ]
                + [
                    {
                        "matcher": {"id": "byName", "options": "Interpretation"},
                        "properties": [{"id": "custom.minWidth", "value": 360}],
                    }
                ],
            },
            "options": {
                "showHeader": True,
                "cellHeight": "lg",
                "footer": {"show": False, "enablePagination": True},
            },
        }
    )


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
                "datasource": {"type": "prometheus", "uid": "prometheus"},
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
                "url": "/d/bioetl-incident-v1/5-incident-workspace?viewPanel=9491"
                "&${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}"
                "&${run_id:queryparam}&${__url_time_range}",
                "includeVars": False,
                "targetBlank": False,
            }
        ],
    }


def place_overview_evidence(panels: dict) -> None:
    """Keep the shared scope pass on the approved saved/current evidence layout."""
    if 9604 in panels:
        panels[9604]["gridPos"].update(x=0, y=2, w=5, h=3)
    panels[9603]["gridPos"].update(x=0, y=5, w=10, h=5)
    panels[9300]["gridPos"].update(x=0, y=10, w=10, h=8)
    panels[99]["gridPos"].update(x=10, y=5, w=14, h=5)
    panels[9002]["gridPos"].update(x=10, y=10, w=14, h=8)


def apply_overview_evidence_clocks(payload, panels):
    """Separate saved verdicts, current alerts and complete alert evidence."""
    panels[9604]["title"] = "Review Saved Run Verdict"
    panels[9604]["description"] += (
        " This is the saved run assessment, not current fleet health or active alerts."
    )
    place_overview_evidence(panels)
    _provider_card(panels)
    health = build_fleet_alert_card()
    payload["panels"] = [
        p for p in payload["panels"] if p["id"] not in {9605, 9606}
    ] + [health, _ingestion_age_card()]
    alerts = panels[2005]
    alerts["targets"][0]["expr"] = "bioetl_incident_global_alerts"
    preserve_evidence_rows(alerts)
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
