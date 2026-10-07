"""Compact, persisted identity for the Overview first window."""


def apply_overview_identity(payload: dict) -> None:
    """Keep only the compact exact-run identity on Overview."""
    panels = payload["panels"]
    panels[:] = [panel for panel in panels if panel.get("id") not in {9301, 9399, 9390}]
    by_id = {panel["id"]: panel for panel in panels}
    by_id[9002]["gridPos"].update(x=0, y=5, w=15, h=13)
    by_id[9603]["gridPos"].update(x=15, y=5, w=9, h=5)
    identity = next(p for p in panels if p.get("id") == 9300)
    identity["gridPos"].update(x=15, y=10, w=9, h=8)
    for pid in (9002, 9603):
        by_id[pid]["options"]["cellHeight"] = "sm"
    # Fixed status widths must fit the existing 200% CSS budget; Reason stays flexible.
    for override in by_id[9603]["fieldConfig"]["overrides"]:
        field = override["matcher"].get("options")
        if field in {"Status", "Result", "Trust"}:
            override["properties"] = [
                prop for prop in override["properties"] if prop["id"] != "custom.width"
            ]
            if field in {"Result", "Trust"}:
                override["properties"].append({"id": "custom.width", "value": 80})
    # Provider evidence is now local. Keep the three domain actions discoverable
    # without forwarding legacy provider selectors that Overview does not own.
    links = by_id[9002]["fieldConfig"]["defaults"].setdefault("links", [])
    links[:] = [link for link in links if link.get("title") != "Open Provider Evidence"]
    links.append(
        {
            "title": "Open Provider Evidence",
            "url": "/d/bioetl-overview-v2/2-overview?${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}&${run_id:queryparam}&viewPanel=9480&${__url_time_range}",
            "includeVars": False,
            "targetBlank": False,
        }
    )
    target = identity["targets"][0]
    target.update(
        url="/ops/observability/selected-run-status?pipeline=${pipeline}&run_type=${run_type:csv}&run_id=${run_id}&workflow=${workflow:csv}",
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
                "properties": [{"id": "custom.width", "value": 125}],
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
    for item in overview[9002]["fieldConfig"]["overrides"]:
        if item["matcher"].get("options") == "Status":
            for prop in item["properties"]:
                if prop["id"] == "links":
                    prop["value"] = [
                        {
                            "title": "Open saved run report",
                            "url": "/api/datasources/proxy/uid/bioetl-ops-http/ops/observability/pipeline-run-report-artifact?pipeline=${pipeline:percentencode}&run_id=${run_id:percentencode}&format=pipeline_run_report_json",
                            "targetBlank": True,
                        }
                    ]
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
        override("Parameter", [{"id": "custom.width", "value": 210}]),
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
                    {"id": "custom.width", "value": width},
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
            prop for prop in override["properties"] if prop["id"] != "custom.width"
        ]
    row["panels"] = [p for p in row["panels"] if p.get("id") != 9460]
    row["gridPos"]["y"] = y + 6
    quality = deepcopy(next(p for p in panels if p.get("id") == 9481))
    quality.update(
        id=9482,
        title="Review Data Quality",
        gridPos={"x": 15, "y": y, "w": 9, "h": 6},
        description=(
            "SELECTED RUN · Excluded-by-contract records summed across Bronze, Silver and Gold. "
            "Exclusion rate uses Bronze records out: below soft limit OK, at soft limit WARN, at hard limit ERROR. "
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
                    "options": {"pattern": "^ERROR.*", "result": {"color": "red"}},
                },
                {
                    "type": "value",
                    "options": {"UNKNOWN": {"text": "UNKNOWN", "color": "gray"}},
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
                    "constraint": {"horizontal": "leftright", "vertical": "center"},
                    "placement": {"left": 8, "right": 8, "top": offset, "height": 60},
                    "background": {"color": {"fixed": "transparent"}},
                }
                for field, size, offset in (("status", 48, 30), ("detail", 42, -30))
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
            "gridPos": {"x": 0, "y": 29, "w": 24, "h": 12},
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
                        "/ops/observability/selected-run-status?pipeline=${pipeline}"
                        "&run_id=${run_id}&run_type=${run_type:csv}&workflow=${workflow:csv}"
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
                "overrides": [],
            },
            "options": {
                "showHeader": True,
                "cellHeight": "lg",
                "footer": {"show": False, "enablePagination": True},
            },
        }
    )
