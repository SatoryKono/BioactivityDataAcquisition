"""First-screen provenance for automatic and explicit run selection (LA-12)."""

from __future__ import annotations

# Share the offset-safe parser with Incident; never compare missing dates.
_OPERATOR_TIME_UNIT = "time:YYYY-MM-DD HH:mm"

_TIMESTAMP_SECONDS = (
    "$secs := function($t){( "
    "$tail := $substring($t, 19); "
    "$rest := $substring($tail, 0, 1) = '.' ? $substringAfter($tail, '.') : ''; "
    "$zone := $contains($rest, 'Z') ? 'Z' : ($contains($rest, 'z') ? 'z' : "
    "($contains($rest, '+') ? '+' : '-')); "
    "$digits := $rest != '' ? $substringBefore($rest, $zone) : ''; "
    "$frac := $digits != '' ? $number('0.' & $digits) : 0; "
    "$sign := $contains($tail, '+') ? 1 : ($contains($tail, '-') ? -1 : 0); "
    "$off := $sign = 0 ? '' : ($contains($tail, '+') ? $substringAfter($tail, '+') : "
    "$substringAfter($tail, '-')); "
    "$oh := $off != '' ? $number($substring($off, 0, 2)) : 0; "
    "$om := $length($off) >= 4 ? $number($substring($off, $contains($off, ':') ? 3 : 2, 2)) : 0; "
    "$toMillis($substring($t, 0, 10))/1000 + $number($substring($t,11,2))*3600 "
    "+ $number($substring($t,14,2))*60 + $number($substring($t,17,2)) + $frac "
    "- $sign * ($oh*3600 + $om*60) )}; "
)

RUN_SELECTION_CONTEXT = (
    '($requested := "${run_id:percentencode}"; '
    "$auto := $requested in ['', '-', 'All', '$__all', '%24__all', '__all', '*', '%2A']; "
    "$hasRun := $type(run_id) = 'string' and run_id != '' and run_id != '-'; "
    '$requestedPipeline := "${pipeline:percentencode}"; '
    "$pipelineAll := $requestedPipeline in ['', 'All', '$__all', '%24__all', '.*', '*', '%2A', '.%2A']; "
    "$pipelineMismatch := $hasRun and $type(pipeline) = 'string' and $not($pipelineAll) "
    "and $encodeUrlComponent(pipeline) != $requestedPipeline; "
    "$savedAt := summary[0].evaluation_at; "
    + _TIMESTAMP_SECONDS
    + "$savedMillis := $type($savedAt) = 'string' ? ($savedAt != '' ? $secs($savedAt) * 1000 : null) : null; "
    "$savedAge := $type($savedMillis) = 'number' ? ($savedMillis <= $millis() "
    "? $floor(($millis() - $savedMillis) / 1000) : null) : null; "
    "[{'_bioetl_frame':'selection_context', "
    "'context': $auto ? ($hasRun ? 'AUTO · latest run in scope' : "
    "(reason = 'no_runs_in_scope' ? 'NO RUN · empty scope' : 'Context unavailable')) "
    ": ($pipelineMismatch ? 'EXPLICIT · Run ID overrides Pipeline filter' "
    ": 'EXPLICIT · requested Run ID'), "
    "'run_id': $type(run_id) = 'string' ? run_id : $requested, "
    "'execution_state': $type(execution_state) = 'string' and execution_state != '' "
    "? execution_state : 'UNKNOWN', "
    "'verdict': $type(verdict) = 'string' and verdict != '' ? verdict : 'UNKNOWN', "
    "'context_checked_at': $now(), "
    "'saved_assessment_at': $savedAt, 'assessment_age_seconds': $savedAge, "
    "'evidence_freshness': ($cache := status_cache; "
    "$saved := summary[0].evaluation_at; "
    "($cache.state = 'fresh' ? 'Cache FRESH' : $cache.state = 'stale' ? 'Cache STALE' : 'Cache UNKNOWN') "
    "& ($type($cache.fresh_seconds)='number' ? ' (fresh < ' & $string($cache.fresh_seconds) & ' s)' : '') "
    "& '; saved ' & ($saved ? $substring($saved,0,10) & ' ' & $substring($saved,11,5) & ' ' & ($substring($saved,-1)='Z' ? 'UTC' : $substring($saved,-6)) : 'Not recorded'))}])"
)


def _shift_children(panel: dict, delta: int) -> None:
    for child in panel.get("panels", []):
        child["gridPos"]["y"] += delta
        _shift_children(child, delta)


def stamp_run_selection_context(payload: dict) -> None:
    """Replace the old static scope banner; retain its identity and layout slot."""
    panel_id = {"bioetl-overview-v2": 99, "bioetl-dq-v2": 9400}.get(payload.get("uid"))
    if panel_id is None:
        return
    panel = next(p for p in payload["panels"] if p.get("id") == panel_id)
    grid = dict(panel["gridPos"])
    old_bottom = grid["y"] + grid["h"]
    delta = 5 - grid["h"]
    if payload["uid"] == "bioetl-dq-v2":
        for other in payload["panels"]:
            if other["gridPos"]["y"] >= old_bottom:
                other["gridPos"]["y"] += delta
                _shift_children(other, delta)
        # Accounting already paginates. Keep its row budget and all values;
        # the first page adapts to the space left by the context block.
        next(p for p in payload["panels"] if p["id"] == 9403)["gridPos"]["h"] = 6
    else:
        # Only the domains under the left-hand banner need to move. Preserve
        # the right-hand status/identity stack so all five identity rows fit.
        next(p for p in payload["panels"] if p["id"] == 9002)["gridPos"]["y"] = (
            grid["y"] + 5
        )
        # Retain the compact eight-row budget; full reasons remain inspectable.
        next(p for p in payload["panels"] if p["id"] == 9002)["gridPos"]["h"] = 8
    if payload["uid"] == "bioetl-dq-v2":
        # Close the two-row gap left when accounting shrinks from eight to six.
        next(p for p in payload["panels"] if p["id"] == 9402)["gridPos"]["y"] = 18
        # Anchor disclosure below identity; repeated generation must not drift.
        disclosure = next(p for p in payload["panels"] if p["id"] == 9450)
        identity = next(p for p in payload["panels"] if p["id"] == 9402)
        target_y = identity["gridPos"]["y"] + identity["gridPos"]["h"]
        disclosure_delta = target_y - disclosure["gridPos"]["y"]
        disclosure["gridPos"]["y"] = target_y
        _shift_children(disclosure, disclosure_delta)
    grid["h"] = 5
    panel.clear()
    panel.update(
        {
            "id": panel_id,
            "title": "Review Run Context",
            "type": "table",
            "gridPos": grid,
            "datasource": {"type": "datasource", "uid": "-- Dashboard --"},
            "description": (
                "SELECTED RUN · AUTO shows the latest run by start time in the current "
                "scope, including unfinished runs. EXPLICIT keeps the requested Run ID "
                "and shows evidence for that run only. An explicit Run ID takes precedence "
                "over Pipeline; an overridden Pipeline filter is identified in Context. "
                "Context checked at is this Grafana query evaluation time, not run "
                "start, browser click, server cache load or catalog freshness. Refresh "
                "re-evaluates the displayed context. UNKNOWN is missing evidence; request failure "
                "is Source unavailable. This context assesses that run only, not a fleet verdict. "
                "TIME RANGE telemetry never proves this run. Empty is a coverage gap, "
                "not a pass. Backend failure indicates an unavailable source and must "
                "not be interpreted as an empty successful response."
            ),
            "targets": [
                {
                    "refId": "A",
                    "panelId": 9002 if payload["uid"] == "bioetl-overview-v2" else 9406,
                    "withTransforms": False,
                    "datasource": {"type": "datasource", "uid": "-- Dashboard --"},
                }
            ],
            "options": {
                "showHeader": True,
                "cellHeight": "sm",
                "footer": {"show": False},
            },
            "fieldConfig": {
                "defaults": {
                    "noValue": "Not verified",
                    "custom": {
                        "align": "left",
                        "minWidth": 50,
                        "inspect": True,
                        "cellOptions": {"type": "auto", "wrapText": True},
                    },
                },
                "overrides": [
                    {
                        "matcher": {"id": "byName", "options": "Evidence freshness"},
                        "properties": [
                            {
                                "id": "custom.cellOptions",
                                "value": {"type": "color-text", "wrapText": True},
                            },
                            {
                                "id": "mappings",
                                "value": [
                                    {
                                        "type": "regex",
                                        "options": {
                                            "pattern": "^Cache STALE.*",
                                            "result": {"color": "orange"},
                                        },
                                    },
                                    {
                                        "type": "regex",
                                        "options": {
                                            "pattern": "^Cache UNKNOWN.*",
                                            "result": {"color": "gray"},
                                        },
                                    },
                                ],
                            },
                        ],
                    },
                    {
                        "matcher": {"id": "byName", "options": "Context checked at"},
                        "properties": [
                            {"id": "unit", "value": _OPERATOR_TIME_UNIT},
                        ],
                    },
                ],
            },
            "transformations": [
                {
                    "id": "filterByValue",
                    "options": {
                        "type": "include",
                        "match": "all",
                        "filters": [
                            {
                                "fieldName": "_bioetl_frame",
                                "config": {
                                    "id": "equal",
                                    "options": {"value": "selection_context"},
                                },
                            }
                        ],
                    },
                },
                {"id": "limit", "options": {"limitField": 1}},
                {
                    "id": "filterFieldsByName",
                    "options": {
                        "include": {
                            "names": [
                                "context",
                                "context_checked_at",
                                "evidence_freshness",
                            ]
                        }
                    },
                },
                {
                    "id": "convertFieldType",
                    "options": {
                        "conversions": [
                            {
                                "targetField": "context_checked_at",
                                "destinationType": "time",
                            }
                        ]
                    },
                },
                {
                    "id": "organize",
                    "options": {
                        "indexByName": {
                            "context": 0,
                            "context_checked_at": 1,
                            "evidence_freshness": 2,
                        },
                        "renameByName": {
                            "context": "Context",
                            "context_checked_at": "Context checked at",
                            "evidence_freshness": "Evidence freshness",
                        },
                    },
                },
            ],
            "links": [],
        }
    )
    # A fresh HTTP cache is not fresh source evidence. Display the saved clock
    # and its age; keep cache policy in the raw context for inspection only.
    names = [
        "context",
        "context_checked_at",
        "saved_assessment_at",
        "assessment_age_seconds",
    ]
    for transform in panel["transformations"]:
        options = transform["options"]
        if transform["id"] == "filterFieldsByName":
            options["include"]["names"] = names
        elif transform["id"] == "convertFieldType":
            options["conversions"].append(
                {"targetField": "saved_assessment_at", "destinationType": "time"}
            )
        elif transform["id"] == "organize":
            options["indexByName"] = {name: index for index, name in enumerate(names)}
            options["renameByName"] = dict(
                zip(
                    names,
                    [
                        "Context",
                        "Read at",
                        "Saved assessment at",
                        "Saved age · not source age",
                    ],
                    strict=True,
                )
            )
    panel["fieldConfig"]["overrides"].extend(
        [
            {
                "matcher": {"id": "byName", "options": "Read at"},
                "properties": [{"id": "unit", "value": _OPERATOR_TIME_UNIT}],
            },
            {
                "matcher": {"id": "byName", "options": "Saved assessment at"},
                "properties": [
                    {"id": "unit", "value": _OPERATOR_TIME_UNIT},
                    {"id": "noValue", "value": "Not recorded"},
                ],
            },
            {
                "matcher": {
                    "id": "byName",
                    "options": "Saved age · not source age",
                },
                "properties": [
                    {"id": "unit", "value": "s"},
                    {"id": "noValue", "value": "Not recorded"},
                    {"id": "color", "value": {"mode": "fixed", "fixedColor": "text"}},
                ],
            },
        ]
    )
    panel["description"] += (
        " Saved assessment at is the persisted assessment clock, and Saved age is elapsed time since that clock. "
        "No cadence or freshness threshold for the run's source data is provided by this endpoint: source freshness remains Not verified. "
        "The reader cache policy does not establish source freshness and is available only in raw context inspection."
    )
