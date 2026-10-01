"""Readable saved provider evidence without inferring a probe from N/A."""

from scripts.ops.observability.grafana._gr_db_corrections import _override


def apply_provider_evidence_columns(payload: dict) -> None:
    if payload.get("uid") != "bioetl-provider-health-v2":
        return
    panel = next(p for p in payload["panels"] if p["id"] == 9460)
    projection = (
        "($d := domains[domain = 'Provider'][0]; "
        "$display := presentation_domains[domain = 'Provider'][0]; "
        "$cached := $d.reason = 'cached_bronze_no_remote_probe'; "
        "$map(provider_checks, function($p){ {"
        "'provider': $p.provider, "
        "'data_source': $cached ? 'Cached Bronze' : 'UNKNOWN', "
        "'check_performed': $cached ? 'No' : ($p.evidence = 'PRESENT' ? 'Yes' : 'UNKNOWN'), "
        "'check_result': $cached ? '—' : ($p.evidence = 'PRESENT' ? $p.check_result : 'UNKNOWN'), "
        "'reason': $cached ? 'Cached Bronze used; provider API was not called.' : "
        "($display.reason_display ? $display.reason_display : 'Provider check evidence is unavailable.'), "
        "'observed_at': $cached ? '—' : ($p.observed_at ? $p.observed_at : 'UNKNOWN'), "
        "'evidence': $cached or $p.evidence = 'PRESENT' ? 'Open report' : 'UNKNOWN'"
        "} }))"
    )
    panel["targets"][0].update(
        parser="uql",
        root_selector=projection,
        uql='parse-json | jsonata "' + projection + '"',
    )
    labels = {
        "provider": "Provider",
        "data_source": "Data source",
        "check_performed": "Check performed",
        "check_result": "Check result",
        "reason": "Reason",
        "observed_at": "Observed at",
        "evidence": "Evidence",
    }
    panel["transformations"] = [
        {
            "id": "organize",
            "options": {
                "indexByName": {name: i for i, name in enumerate(labels)},
                "renameByName": labels,
            },
        },
    ]
    panel["options"].update(
        cellHeight="lg", footer={"show": False, "enablePagination": False}
    )
    panel["gridPos"]["h"] = 6
    for name, width in {
        "Provider": 85,
        "Data source": 120,
        "Check performed": 125,
        "Check result": 105,
        "Observed at": 170,
        "Evidence": 105,
    }.items():
        _override(panel, name, "custom.width", width)
    _override(panel, "Reason", "custom.wrapText", True)
    _override(panel, "Reason", "custom.cellOptions", {"type": "auto", "wrapText": True})
    _override(panel, "Reason", "links", [])
    _override(
        panel,
        "Evidence",
        "links",
        [
            {
                "title": "Open report",
                "targetBlank": True,
                "url": "/api/datasources/proxy/uid/bioetl-ops-http/ops/observability/pipeline-run-report-artifact?pipeline=${pipeline:percentencode}&run_id=${run_id:percentencode}&format=pipeline_run_report_json",
            }
        ],
    )
