"""Focused selected-run replay workspace; preserve diagnostics behind two rows."""


def apply_replay_layout(payload: dict) -> None:
    """Keep verdict, checks and evidence together without deleting backend checks."""
    pending = list(payload["panels"])
    by_id = {}
    while pending:
        panel = pending.pop()
        by_id[panel["id"]] = panel
        pending.extend(panel.get("panels", []))

    def place(panel_id: int, x: int, y: int, w: int, h: int) -> dict:
        panel = by_id[panel_id]
        panel["gridPos"] = {"x": x, "y": y, "w": w, "h": h}
        return panel

    checks = place(9423, 0, 5, 24, 13)
    checks["options"].update(
        cellHeight="sm", sortBy=[{"displayName": "Result", "desc": False}]
    )
    # Alphabetic order is fail, n/a, pass, unknown; explicit sorting puts unknown
    # immediately after fail while preserving every check and evidence reference.
    target = checks["targets"][0]
    target.update(
        parser="uql",
        root_selector="",
        uql=(
            "parse-json | jsonata \"replay_checks^(result='fail' ? 0 : "
            "result='unknown' ? 1 : result='pass' ? 2 : 3)\""
        ),
    )
    checks["options"].pop("sortBy", None)
    evidence = place(9408, 0, 18, 24, 10)
    evidence["title"] = "Review Replay Evidence"
    evidence["description"] = (
        "SELECTED RUN · All identity anchors, missing first. Presence is not verification. VALID EMPTY means the successful response contains no anchors. "
        "Exact Replay Checks determines readiness. Inspect a value to copy it in full. "
        "No rows is not a pass; missing evidence is UNKNOWN and failed requests are QUERY ERROR."
    )
    target = evidence["targets"][0]
    target["url"] = target["url"].replace("&priority=P1", "")
    target.update(
        parser="uql",
        root_selector="",
        uql='parse-json | jsonata "rows^(present ? 1 : 0, priority, name)"',
    )
    names = ["label", "priority", "present", "status", "value_full", "why"]
    evidence["transformations"] = [
        {"id": "filterFieldsByName", "options": {"include": {"names": names}}},
        {
            "id": "organize",
            "options": {
                "indexByName": {name: index for index, name in enumerate(names)},
                "renameByName": dict(
                    zip(
                        names,
                        [
                            "Parameter",
                            "Priority",
                            "Present",
                            "Result",
                            "Value",
                            "Purpose",
                        ],
                        strict=True,
                    )
                ),
            },
        },
    ]
    evidence["fieldConfig"] = {
        "defaults": {
            "noValue": "UNKNOWN",
            "custom": {"inspect": True, "wrapText": False},
        },
        "overrides": [
            {
                "matcher": {"id": "byName", "options": name},
                "properties": [{"id": "custom.width", "value": width}],
            }
            for name, width in (
                ("Parameter", 230),
                ("Priority", 75),
                ("Present", 80),
                ("Result", 100),
                ("Value", 310),
            )
        ],
    }
    base = "/api/datasources/proxy/uid/bioetl-ops-http"
    query = "pipeline=${pipeline:percentencode}&run_type=${run_type:percentencode}&run_id=${run_id:percentencode}"
    evidence["links"] = [
        {
            "title": "Full identity report",
            "url": base
            + "/ops/control-plane/identity-evidence?"
            + query
            + "&view=copy_values",
            "targetBlank": True,
        },
        {
            "title": "Find complete runs",
            "url": base
            + "/ops/control-plane/latest-complete-run?"
            + query
            + "&workflow=${workflow:percentencode}&error_as_row=1",
            "targetBlank": True,
        },
    ]
    verdict = place(9422, 15, 2, 9, 3)
    verdict["fieldConfig"]["overrides"] = []
    verdict["options"].update(
        textMode="value",
        reduceOptions={
            "values": True,
            "calcs": ["lastNotNull"],
            "fields": "/^verdict$/",
        },
    )
    verdict["transformations"] = [
        {"id": "filterFieldsByName", "options": {"include": {"names": ["verdict"]}}}
    ]
    note = " Occurrence-only versus semantic drift still requires exact-run evidence; current write-risk telemetry is not proof for this run."
    if note not in verdict["description"]:
        verdict["description"] += note
    trust = place(9418, 0, 28, 24, 5)
    trust["fieldConfig"]["defaults"]["links"] = [
        {
            "title": "Open Run Explorer",
            "url": "/d/bioetl-run-explorer-v1/run-explorer?${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}&${run_id:queryparam}&${__url_time_range}",
            "includeVars": False,
            "targetBlank": False,
        }
    ]
    trust["options"]["cellHeight"] = "sm"
    trust["options"]["footer"] = {"show": False, "enablePagination": False}

    def row(panel_id: int, title: str, y: int, ids: tuple[int, ...]) -> dict:
        return {
            "id": panel_id,
            "type": "row",
            "title": title,
            "collapsed": True,
            "gridPos": {"x": 0, "y": y, "w": 24, "h": 1},
            "panels": [
                place(child, 0, y + 1 + index * 9, 24, 9)
                for index, child in enumerate(ids)
            ],
        }

    payload["panels"] = [
        place(1000, 0, 0, 24, 2),
        place(9400, 0, 2, 15, 3),
        verdict,
        checks,
        evidence,
        trust,
        row(9430, "Inspect Manifest / Lineage / Retention", 33, (9414, 9415, 9416)),
        row(9431, "Inspect Resume / Checkpoint", 34, (9413, 9406)),
    ]
