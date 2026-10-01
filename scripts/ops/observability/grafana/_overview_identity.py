"""Compact, persisted identity for the Overview first window."""


def apply_overview_identity(payload: dict) -> None:
    """Keep only the compact exact-run identity on Overview."""
    panels = payload["panels"]
    panels[:] = [panel for panel in panels if panel.get("id") not in {9301, 9399, 9390}]
    by_id = {panel["id"]: panel for panel in panels}
    by_id[9002]["gridPos"].update(x=0, y=5, w=15, h=12)
    by_id[9603]["gridPos"].update(x=15, y=5, w=9, h=4)
    identity = next(p for p in panels if p.get("id") == 9300)
    identity["gridPos"].update(x=15, y=9, w=9, h=8)
    target = identity["targets"][0]
    target.update(
        url="/ops/observability/selected-run-status?pipeline=${pipeline}&run_type=${run_type:csv}&run_id=${run_id}&workflow=${workflow:csv}",
        root_selector=(
            '($v := function($x){$exists($x) and $x != "" ? $string($x) : '
            '"Not recorded in saved run evidence"}; '
            '$s := summary[0]; '
            '$start := $s.started_at ? $toMillis($s.started_at) : null; '
            '$end := $s.completed_at ? $toMillis($s.completed_at) : null; ['
            '{"parameter":"Run ID","value":$v(run_id)},'
            '{"parameter":"Pipeline","value":$v(pipeline)},'
            '{"parameter":"Run Type","value":$v(run_type)},'
            '{"parameter":"Started at","value":'
            'started_at ? $substring(started_at,0,10) & " " & '
            '$substring(started_at,11,5) & " " & '
            '($substring(started_at,-1) = "Z" ? "UTC" : $substring(started_at,-6)) : '
            '"Not recorded in saved run evidence"},'
            '{"parameter":"Total Run Duration","value":'
            '$start != null and $end != null and $end >= $start ? '
            '($n := $floor(($end - $start) / 1000 + 0.5); '
            '$parts := [$floor($n / 86400), $floor(($n % 86400) / 3600), '
            '$floor(($n % 3600) / 60), $n % 60]; '
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
        uql='parse-json | jsonata "' + target["root_selector"].replace('"', '\\"') + '"',
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
    identity["transformations"] = [
        {
            "id": "organize",
            "options": {
                "indexByName": {"parameter": 0, "value": 1},
                "renameByName": {"parameter": "Parameter", "value": "Value"},
            },
        }
    ]


def apply_saved_evidence_readability(payload: dict) -> None:
    """Present saved domains and full identity without redundant table columns."""
    if payload.get("uid") != "bioetl-overview-v2":
        return
    row = next(p for p in payload["panels"] if p.get("id") == 9450)
    row["panels"] = [p for p in row["panels"] if p.get("id") != 9451]
    row["description"] = "Expand for saved stage rows and full identity of the selected Run ID."
    panels = {p["id"]: p for p in row["panels"]}

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
    y = row["gridPos"]["y"] + 1
    for panel in row["panels"]:
        panel["gridPos"]["y"] = y
        y += panel["gridPos"]["h"]
