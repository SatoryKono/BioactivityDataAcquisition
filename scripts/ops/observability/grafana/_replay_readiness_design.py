"""Compact replay verdict with a separate, readable evidence table."""

from copy import deepcopy


def stamp_exact_replay_queries(payload: dict) -> None:
    """Retain approved backend exact-run guards after legacy layout passes."""
    if payload.get("uid") != "bioetl-control-plane-v1":
        return
    from scripts.ops.observability.grafana.apply_phase25_srs_prr_budget import _CP_DONOR

    panels = {panel["id"]: panel for panel in payload["panels"]}
    evidence = panels[9408]
    evidence["description"] = (
        "SELECTED RUN · Identity anchors, missing first. Presence is not verification. "
        "SELECT RUN requests an explicit Run ID; UNKNOWN means the reply lacks required "
        "anchor evidence. A valid empty response (no required anchors returned) is not "
        "verification. QUERY ERROR means the source reported a query failure or Grafana "
        "could not complete the query; inspect the query for details. Exact Replay "
        "Checks determines readiness. Inspect a value to copy it in full. Exact Run ID "
        "selects evidence; the Workflow filter only narrows the run catalog. Catalog "
        "freshness does not establish evidence freshness."
    )
    evidence["fieldConfig"]["defaults"]["noValue"] = "No result · inspect this query"
    evidence_target = evidence["targets"][0]
    evidence_target.update(
        parser="backend",
        root_selector=(
            "(status = 'scope_resolve_timeout' or status = 'evidence_build_timeout' "
            "or status = 'QUERY ERROR' or summary.overall_status = 'QUERY ERROR') ? "
            "[{'status':'QUERY ERROR','label':'Run selection',"
            "'value_full':'Exact-run evidence unavailable','present':false}] : "
            "(summary.overall_status = 'SELECT RUN' ? "
            "[{'status':'SELECT RUN','label':'Run selection',"
            "'value_full':'Choose a Run ID','present':false}] : "
            "($count(rows) > 0 ? [rows^(present ? 1 : 0, priority, name)] : "
            "[{'status':'UNKNOWN','label':'Run selection',"
            "'value_full':'No anchor evidence returned','present':false}]))"
        ),
    )
    evidence_target.pop("uql", None)
    trust_target = panels[9418]["targets"][0]
    # The exact-run endpoint emits donor rows for SELECT RUN and unavailable states.
    # Reuse them so Dashboard datasource consumers receive the same frame types.
    trust_target.update(parser="backend", root_selector=_CP_DONOR)
    trust_target.pop("uql", None)


def apply_trust_action_display(payload: dict) -> None:
    """Only materialize a linked Action field when a saved reason exists."""
    trust = next(p for p in payload["panels"] if p.get("id") == 9418)
    expression = (
        '[presentation_trust.($base := $sift($, function($v,$k){$k != "trust_reasons_action"}); '
        '$merge([$base, ($type(reasons_count)="number" ? reasons_count > 0 : false) ? {"trust_reasons_action":"View trust reasons"} : '
        '{"trust_action_note": reasons_count = 0 ? "No trust issues" : "Not assessed"}]))]'
    )
    trust["targets"][0].update(
        parser="uql",
        root_selector="",
        uql='parse-json | jsonata "' + expression.replace('"', '\\"') + '"',
    )
    for transform in trust["transformations"]:
        options = transform["options"]
        if transform["id"] == "filterFieldsByName":
            names = options["include"]["names"]
            if "trust_action_note" not in names:
                names.append("trust_action_note")
        if transform["id"] == "organize":
            options["renameByName"].pop("trust_reasons_action", None)
            options["indexByName"]["trust_action_note"] = 4
    overrides = trust["fieldConfig"]["overrides"]
    if any(item["matcher"].get("options") == "Action" for item in overrides):
        overrides[:] = [
            item
            for item in overrides
            if item["matcher"].get("options") != "trust_reasons_action"
        ]
    for item in overrides:
        if item["matcher"].get("options") == "Action":
            item["matcher"]["options"] = "trust_reasons_action"
            item["properties"].append({"id": "displayName", "value": "Action"})
    overrides[:] = [
        item
        for item in overrides
        if item["matcher"].get("options") != "trust_action_note"
    ]
    overrides.append(
        {
            "matcher": {"id": "byName", "options": "trust_action_note"},
            "properties": [
                {"id": "displayName", "value": "Action"},
                {"id": "links", "value": []},
            ],
        }
    )


def apply_replay_readiness_design(payload: dict) -> None:
    if payload.get("uid") != "bioetl-control-plane-v1":
        return
    panels = payload["panels"]
    card = next((p for p in panels if p.get("id") == 9422), None)
    row = next((p for p in panels if p.get("id") == 902), None)
    if card is None:
        return
    card.update(type="stat", title="Review Exact Replay Readiness")
    card["description"] = (
        "SELECTED RUN · Saved exact-replay assessment, not CURRENT health. "
        "OK/WARN/CRIT palette: READY=OK, INSUFFICIENT=WARN, BLOCKED=CRIT. "
        "UNSUPPORTED/UNKNOWN/INCOMPLETE are gray. SELECT RUN means no Run ID is "
        "selected; Source unavailable means backend unavailable or request failure. "
        "UNKNOWN means no assessed value, never READY. Open replay checks for basis."
    )
    card["options"] = {
        "reduceOptions": {
            "values": False,
            "calcs": ["lastNotNull"],
            "fields": "verdict",
        },
        "orientation": "horizontal",
        "textMode": "value_and_name",
        "colorMode": "background",
        "graphMode": "none",
        "justifyMode": "center",
        "text": {"valueSize": 22, "titleSize": 12},
    }
    card["transformations"] = [
        {
            "id": "filterFieldsByName",
            "options": {"include": {"names": ["verdict", "explanation"]}},
        }
    ]
    colors = {
        "READY": "green",
        "BLOCKED": "red",
        "INSUFFICIENT": "orange",
        "UNSUPPORTED": "#555555",
        "SELECT RUN": "#555555",
        "QUERY ERROR": "red",
        "UNKNOWN": "#555555",
        "INCOMPLETE": "#555555",
    }
    card["fieldConfig"] = {
        "defaults": {
            "unit": "none",
            "noValue": "UNKNOWN",
            "mappings": [
                {
                    "type": "value",
                    "options": {
                        state: {
                            "text": "Source unavailable"
                            if state == "QUERY ERROR"
                            else state,
                            "color": color,
                        }
                        for state, color in colors.items()
                    },
                },
                {
                    "type": "special",
                    "options": {
                        "match": "null",
                        "result": {"text": "UNKNOWN", "color": "#555555"},
                    },
                },
            ],
            "color": {"mode": "thresholds"},
            "thresholds": {
                "mode": "absolute",
                "steps": [{"color": "#555555", "value": None}],
            },
        },
        "overrides": [
            {
                "matcher": {"id": "byName", "options": "verdict"},
                "properties": [
                    {"id": "displayName", "value": "${__data.fields.explanation}"}
                ],
            }
        ],
    }
    card["links"] = [
        {
            "title": "View replay checks",
            "includeVars": False,
            "url": "/d/bioetl-control-plane-v1/2-replay-readiness?${workflow:queryparam}&${pipeline:queryparam}&${run_type:queryparam}&${run_id:queryparam}&viewPanel=9423&${__url_time_range}",
            "targetBlank": False,
        }
    ]
    if row is None:
        return
    children = row.setdefault("panels", [])
    children[:] = [p for p in children if p.get("id") != 9423]
    target = deepcopy(card["targets"][0])
    target["root_selector"] = "replay_checks"
    bottom = max(
        (p["gridPos"]["y"] + p["gridPos"]["h"] for p in children),
        default=row["gridPos"]["y"] + 1,
    )
    children.append(
        {
            "id": 9423,
            "type": "table",
            "title": "Review Exact Replay Checks",
            "description": (
                "SELECTED RUN · One row per readiness check for this Run ID. "
                "Fail blocks replay. Unknown is not a pass. "
                "Valid-empty check output stays VALID EMPTY. "
                "Request failure is Source unavailable."
            ),
            "datasource": card["datasource"],
            "targets": [target],
            "gridPos": {"x": 0, "y": bottom, "w": 24, "h": 8},
            "options": {
                "showHeader": True,
                "cellHeight": "lg",
                "footer": {"show": False, "enablePagination": True},
            },
            "transformations": [
                {
                    "id": "organize",
                    "options": {
                        "indexByName": {
                            "code": 0,
                            "result": 1,
                            "reason": 2,
                            "evidence_ref": 3,
                        },
                        "renameByName": {
                            "code": "Check",
                            "result": "Result",
                            "reason": "Reason",
                            "evidence_ref": "Evidence reference",
                        },
                    },
                }
            ],
            "fieldConfig": {
                "defaults": {
                    "noValue": "—",
                    "custom": {
                        "align": "left",
                        "inspect": True,
                        "wrapText": True,
                        "cellOptions": {"type": "auto", "wrapText": True},
                    },
                },
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "Check"},
                        "properties": [
                            {
                                "id": "mappings",
                                "value": [
                                    {
                                        "type": "value",
                                        "options": {
                                            "manifest_not_recorded": {
                                                "text": "manifest for this run was not recorded"
                                            }
                                        },
                                    }
                                ],
                            }
                        ],
                    }
                ],
            },
        }
    )
