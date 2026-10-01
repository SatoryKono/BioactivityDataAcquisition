"""Compact saved provider evidence; deliberately skipped checks are not unknown."""

from copy import deepcopy


def _provider_evidence_columns(panel: dict) -> None:
    """Present saved provider facts without conflating skipped and unknown checks."""
    fields = {
        "provider": "Provider",
        "data_source": "Data source",
        "check_performed": "Performed",
        "check_result": "Result",
        "reason": "Reason",
        "observed_display": "Observed at",
        "report_label": "Evidence",
    }
    panel["targets"][0]["root_selector"] = (
        "($d := presentation_domains[domain = 'Provider'][0]; "
        "$cached := $d.reason = 'cached_bronze_no_remote_probe'; "
        "$saved := evidence_availability in ['AVAILABLE', 'legacy_no_snapshot']; "
        "[$map(provider_checks, function($p) { $merge([$p, {"
        "'data_source': $cached ? 'Cached Bronze' : ($p.data_source ? $p.data_source : 'UNKNOWN'), "
        "'check_performed': $cached ? 'No' : ($p.evidence = 'PRESENT' ? 'Yes' : 'UNKNOWN'), "
        "'check_result': $cached ? '—' : "
        "($p.evidence = 'PRESENT' and $p.check_result ? $p.check_result : 'UNKNOWN'), "
        "'reason': $cached ? 'Cached Bronze used; provider API was not called.' : "
        "($d.reason = 'run_preflight_provider_observation' ? 'Saved provider preflight check.' : "
        "($d.reason_display ? $d.reason_display : 'Provider check evidence was not recorded.')), "
        "'observed_display': $cached ? '—' : ($p.observed_at ? "
        "$substring($p.observed_at,0,10) & ' ' & $substring($p.observed_at,11,5) & ' ' & "
        "($substring($p.observed_at,-1) = 'Z' ? 'UTC' : $substring($p.observed_at,-6)) : 'UNKNOWN'), "
        "'report_label': $saved or $cached ? 'Open report' : '—' }]) })])"
    )
    panel["targets"][0].update(
        parser="uql",
        uql='parse-json | jsonata "' + panel["targets"][0]["root_selector"] + '"',
    )
    panel["description"] = (
        "SELECTED RUN · Saved provider evidence for this Run ID. Cached Bronze means "
        "the provider API was not called: Check performed is No and Check result is —. "
        "UNKNOWN means the performed state or result is unknown. Observed at preserves "
        "the saved timezone. Expand Provider HTTP details for recorded response time, "
        "HTTP status and endpoint; missing details are not invented. VALID EMPTY is an "
        "empty successful response. SELECT RUN requires context; QUERY ERROR is a failed request."
    )
    panel["transformations"] = [
        {"id": "filterFieldsByName", "options": {"include": {"names": list(fields)}}},
        {
            "id": "organize",
            "options": {
                "indexByName": {name: index for index, name in enumerate(fields)},
                "renameByName": fields,
            },
        },
    ]
    defaults = panel["fieldConfig"]["defaults"]
    defaults["custom"]["cellOptions"]["wrapText"] = True
    defaults["custom"]["minWidth"] = 50
    panel["options"]["cellHeight"] = "lg"
    panel["options"]["footer"] = {"show": False, "enablePagination": False}
    widths = {
        "Provider": 75,
        "Data source": 105,
        "Performed": 90,
        "Result": 75,
        "Observed at": 155,
        "Evidence": 95,
    }
    panel["fieldConfig"]["overrides"] = [
        {
            "matcher": {"id": "byName", "options": name},
            "properties": [{"id": "custom.width", "value": width}],
        }
        for name, width in widths.items()
    ]
    panel["fieldConfig"]["overrides"].append(
        {
            "matcher": {"id": "byName", "options": "Evidence"},
            "properties": [
                {
                    "id": "links",
                    "value": [
                        {
                            "title": "Open report",
                            "url": "/api/datasources/proxy/uid/bioetl-ops-http/ops/observability/"
                            "pipeline-run-report-artifact?pipeline=${pipeline:percentencode}"
                            "&run_id=${run_id:percentencode}&format=pipeline_run_report_json",
                            "targetBlank": True,
                        }
                    ],
                }
            ],
        }
    )


def _provider_http_details(panel: dict) -> dict:
    """Keep optional saved HTTP facts out of the first-window table."""
    detail = deepcopy(panel)
    detail.update(
        id=9462,
        title="Inspect Provider HTTP Details",
        gridPos={"x": 0, "y": 19, "w": 24, "h": 6},
    )
    fields = {
        "provider": "Provider",
        "response_time_ms": "Response time, ms",
        "http_status": "HTTP status",
        "checked_endpoint": "Checked endpoint",
    }
    detail["targets"][0]["root_selector"] = (
        "provider_checks[($exists(response_time_ms) and response_time_ms != null) or "
        "($exists(http_status) and http_status != null) or "
        "($exists(checked_endpoint) and checked_endpoint != null and checked_endpoint != '')]"
    )
    detail["targets"][0]["uql"] = (
        'parse-json | jsonata "[' + detail["targets"][0]["root_selector"] + ']"'
    )
    detail["description"] = (
        "SELECTED RUN · Optional recorded HTTP facts only. VALID EMPTY means no saved "
        "response time, HTTP status or checked endpoint. QUERY ERROR is a failed request."
    )
    detail["fieldConfig"]["defaults"]["noValue"] = "—"
    detail["fieldConfig"]["overrides"] = []
    detail["transformations"] = [
        {"id": "filterFieldsByName", "options": {"include": {"names": list(fields)}}},
        {
            "id": "organize",
            "options": {
                "indexByName": {name: index for index, name in enumerate(fields)},
                "renameByName": fields,
            },
        },
    ]
    return {
        "id": 9471,
        "title": "Inspect Provider HTTP Details",
        "type": "row",
        "collapsed": True,
        "gridPos": {"x": 0, "y": 18, "w": 24, "h": 1},
        "panels": [detail],
    }


def apply_provider_evidence_columns(payload: dict) -> None:
    if payload.get("uid") == "bioetl-overview-v2":
        from scripts.ops.observability.grafana._selected_run_panels import (
            _provider_check_panel,
            _style_provider_check,
        )

        panels = payload["panels"]
        panels[:] = [panel for panel in panels if panel.get("title") not in {"Review Provider Evidence", "Review Provider Check"}]
        evidence = _provider_check_panel(
            9460,
            "Review Provider Evidence",
            {"x": 0, "y": 18, "w": 20, "h": 6},
            ["provider", "check_result", "evidence", "observed_at"],
            limit=None,
        )
        check = _provider_check_panel(
            9461,
            "Review Provider Check",
            {"x": 20, "y": 18, "w": 4, "h": 6},
            ["check_result", "evidence"],
            limit=1,
        )
        _style_provider_check([evidence, check])
        # Overview already owns stage panel 9460 inside saved evidence.
        evidence["id"] = 9480
        check["id"] = 9481
        _provider_evidence_columns(evidence)
        evidence["gridPos"] = {"x": 0, "y": 18, "w": 20, "h": 6}
        check["gridPos"] = {"x": 20, "y": 18, "w": 4, "h": 6}
        for panel in panels:
            if panel.get("id") == 9450:
                panel["gridPos"]["y"] = 24
                for child in panel.get("panels", []):
                    child["gridPos"]["y"] = 25
        panels.extend([evidence, check])
        return
    if payload.get("uid") != "bioetl-provider-health-v2":
        return
    panels = payload["panels"]
    panels[:] = [panel for panel in panels if panel.get("id") not in {9400, 9471}]
    evidence = next(panel for panel in panels if panel["id"] == 9460)
    _provider_evidence_columns(evidence)
    evidence["gridPos"] = {"x": 0, "y": 2, "w": 20, "h": 6}
    check = next(panel for panel in panels if panel["id"] == 9461)
    check["gridPos"] = {"x": 20, "y": 2, "w": 4, "h": 6}
    details = _provider_http_details(evidence)
    details["gridPos"]["y"] = 8
    details["panels"][0]["gridPos"]["y"] = 9
    panels.append(details)
    panels[:] = [panel for panel in panels if panel.get("id") not in {9460, 9461}]
    details["gridPos"]["y"] = 2
    details["panels"][0]["gridPos"]["y"] = 3
