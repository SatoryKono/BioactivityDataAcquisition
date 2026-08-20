"""One-shot D6-IA layout apply. Run then delete; not a shipped CLI."""

from __future__ import annotations

import json
from pathlib import Path

PATH = Path("grafana/dashboards/bioetl-run-explorer-v1.json")

REPORT_URL = (
    "/ops/observability/pipeline-run-report?pipeline=${pipeline}&run_id=${run_id}"
)
TRUST_URL = (
    "/d/bioetl-control-plane-v1/bioetl-control-plane-v1?var-workflow=$workflow"
    "&var-pipeline=$pipeline&var-run_type=$run_type&var-run_id=$run_id"
    "&${__url_time_range}"
)
RUNBOOK_URL = (
    "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/"
    "docs/05-operations/runbooks/run-manifest-inspection.md"
)
SELECT_RUN_URL = (
    "/d/bioetl-run-explorer-v1/6-run-explorer?var-workflow=$workflow"
    "&var-pipeline=${__data.fields.Pipeline}&var-run_type=$run_type"
    "&var-run_id=${__value.raw}&viewPanel=3022&${__url_time_range}"
)

SCOPE_HTML = (
    '<div style="padding:6px 10px;border-left:4px solid #ff9830;'
    "background:rgba(255,152,48,0.08);font-size:16px;line-height:1.35;"
    'white-space:normal;overflow-wrap:anywhere"><div style="max-width:96ch">'
    '<div style="font-size:18px;font-weight:700">Which exact run should be inspected?</div>'
    "<div>BROWSE is the last 4 reports in the table below. SELECTED RUN identity "
    "and counts are in <em>Selected Run Details</em> after you click a run. "
    'Selected <code style="font-size:16px">run_id</code> is '
    '<code style="font-size:16px">$run_id</code>.</div>'
    "<div>Open/Copy FULL PATHS are report artifacts, not triage bodies. "
    '<code style="font-size:16px">pipeline=unknown</code> and '
    '<code style="font-size:16px">run_id=-</code> mean pick a pipeline and a run first. '
    "Then open <b>0. Trust</b> for recovery/replay safety. Run Explorer is evidence-only.</div>"
    "<div>Run coverage: IN RANGE / OUT OF RANGE / UNKNOWN compares this run to the time picker. "
    "Set range to run when OUT OF RANGE.</div></div></div>"
)


def _ops_target(root_selector: str, ref_id: str = "A") -> dict:
    return {
        "format": "table",
        "parser": "backend",
        "refId": ref_id,
        "root_selector": root_selector,
        "source": "url",
        "type": "json",
        "url": REPORT_URL,
        "url_options": {"data": "", "method": "GET"},
        "expr": "",
    }


def _kv_table(
    *,
    panel_id: int,
    title: str,
    description: str,
    no_value: str,
    root_selectors: tuple[str, ...],
    y: int,
    h: int = 8,
) -> dict:
    targets = [
        _ops_target(selector, ref_id=chr(ord("A") + index))
        for index, selector in enumerate(root_selectors)
    ]
    panel = {
        "id": panel_id,
        "type": "table",
        "title": title,
        "description": description,
        "gridPos": {"h": h, "w": 24, "x": 0, "y": y},
        "datasource": "BioETL Ops HTTP",
        "fieldConfig": {
            "defaults": {
                "custom": {"align": "left", "inspect": True},
                "noValue": no_value,
            },
            "overrides": [
                {
                    "matcher": {"id": "byName", "options": "value"},
                    "properties": [
                        {"id": "displayName", "value": "Value"},
                        {"id": "custom.align", "value": "left"},
                    ],
                }
            ],
        },
        "options": {"showHeader": True, "footer": {"show": False}, "cellHeight": "sm"},
        "targets": targets,
        "transformations": [{"id": "merge", "options": {}}],
        "links": [],
    }
    if len(targets) == 1:
        panel["transformations"] = []
    return panel


def _status_options() -> dict:
    return {
        "TREE_MISSING": {"text": "TREE_MISSING", "color": "red"},
        "LAYOUT_UNHEALTHY": {"text": "LAYOUT_UNHEALTHY", "color": "orange"},
        "IDENTITY_UNHEALTHY": {"text": "IDENTITY_UNHEALTHY", "color": "orange"},
        "success": {"text": "success", "color": "green"},
        "failed": {"text": "failed", "color": "red"},
        "partial": {"text": "partial", "color": "orange"},
        "shutdown": {"text": "shutdown", "color": "orange"},
        "dry_run": {"text": "dry_run", "color": "blue"},
    }


def _run_type_variable() -> dict:
    return {
        "allValue": None,
        "current": {"selected": True, "text": "backfill", "value": "backfill"},
        "datasource": "BioETL Ops HTTP",
        "definition": (
            "/ops/control-plane/filter-options?dimension=run_type"
            "&response_shape=list&workflow=${workflow}&pipeline=${pipeline}"
        ),
        "hide": 0,
        "includeAll": True,
        "label": "Run Type",
        "multi": True,
        "name": "run_type",
        "options": [],
        "query": {
            "queryType": "infinity",
            "refId": "variable",
            "infinityQuery": {
                "format": "table",
                "parser": "backend",
                "root_selector": "$.items",
                "type": "json",
                "source": "url",
                "url_options": {"method": "GET", "data": ""},
                "url": (
                    "/ops/control-plane/filter-options?dimension=run_type"
                    "&response_shape=list&workflow=${workflow}&pipeline=${pipeline}"
                ),
            },
        },
        "refresh": 1,
        "regex": "",
        "skipUrlSync": False,
        "sort": 1,
        "tagValuesQuery": "",
        "tags": [],
        "tagsQuery": "",
        "type": "query",
        "useTags": False,
        "description": (
            "Core scope: run_type option list from the local control-plane catalog "
            "(/ops/control-plane/filter-options?dimension=run_type), not the Prometheus "
            "universe. Default is backfill. Include All remains available for aggregate "
            "HTTP identity queries (csv). A catalog run_type stays selectable even when "
            "Prometheus has no series."
        ),
    }


def _panel_links() -> list[dict]:
    return [
        {
            "title": "Open Trust",
            "url": TRUST_URL,
            "targetBlank": False,
            "includeVars": False,
        },
        {
            "title": "Run-manifest inspection runbook",
            "url": RUNBOOK_URL,
            "targetBlank": True,
            "includeVars": False,
        },
    ]


def _find(panels: list, panel_id: int) -> dict:
    for panel in panels:
        if panel.get("id") == panel_id:
            return panel
        nested = panel.get("panels")
        if isinstance(nested, list):
            try:
                return _find(nested, panel_id)
            except KeyError:
                continue
    raise KeyError(panel_id)


def main() -> None:
    dashboard = json.loads(PATH.read_text(encoding="utf-8"))
    dashboard["description"] = (
        "Run Explorer 2.0 narrative. Exact completed run via Ops HTTP "
        "pipeline_run_report_v1. run_id never a Prometheus label. First screen: "
        "browse last-4 pipeline-run reports (3010). Identity, processed records, "
        "and selected-run forensics live under collapsed Selected Run Details. "
        "Older runs: pick Run ID from the control-plane catalog."
    )

    scope = _find(dashboard["panels"], 1)
    scope["options"]["content"] = SCOPE_HTML
    scope["description"] = (
        "Run Explorer has two modes. Browse mode lists the last 4 run-report artifacts "
        "for the selected pipeline. Selected-run mode uses BioETL Ops HTTP under "
        "Selected Run Details to show identity, accounting, layers, timings/failure, "
        "reasons, reconciliation, and artifacts for one exact run. Default "
        "pipeline=unknown and run_id=- intentionally show no runs (not a missing data "
        "store and not a healthy run). Older than last 4: pick a concrete run_id from "
        "the catalog (not -). Then open Trust for recovery/replay safety. Run Explorer "
        "is evidence-only. Run ID is never a Prometheus label. Full filesystem paths "
        "belong to report-artifact Open/Copy actions. Run coverage: IN RANGE / "
        "OUT OF RANGE / UNKNOWN. Set range to run when OUT OF RANGE. Effective "
        "refresh: 60s · timezone: browser."
    )
    scope["links"] = _panel_links()

    browse = _find(dashboard["panels"], 3010)
    browse["description"] = (
        "SELECTED RUN · Browse mode: latest four pipeline-run reports found on disk "
        "for the selected pipeline. Click a Run cell to set var-run_id and open "
        "Inspect Run Identity. Older runs: use the Run ID catalog selector (newest "
        "first); they are omitted from this first-screen index by design (limit=4). "
        "$pipeline is a pipeline name, not a workflow. An empty table is valid when "
        "no matching reports exist (index_state=valid_empty). A TREE_MISSING / "
        "LAYOUT_UNHEALTHY / IDENTITY_UNHEALTHY row is bind or origin failure. "
        "SELECT RUN / VALID EMPTY is not OK."
    )
    browse["links"] = _panel_links()
    for override in browse["fieldConfig"]["overrides"]:
        matcher = override.get("matcher") or {}
        if matcher.get("options") == "status":
            override["properties"][1]["value"][0]["options"] = _status_options()
        if matcher.get("options") == "Run":
            override["properties"][0]["value"][0]["url"] = SELECT_RUN_URL

    details = _find(dashboard["panels"], 3099)
    children = [
        panel
        for panel in details.get("panels") or []
        if panel.get("id") not in {3021, 3001}
    ]
    by_id = {panel["id"]: panel for panel in children}

    by_id[3022]["title"] = "Inspect Run Identity"
    by_id[3022]["description"] = (
        "SELECTED RUN · Identity rows for the selected run (control-plane table plus "
        "pipeline_run_report_v1 identity/tracking_coverage). Selection required when "
        "no run ID is set. VALID EMPTY means the selected run has no identity; "
        "backend failure renders as QUERY ERROR."
    )
    by_id[3022]["targets"] = [
        {
            "format": "table",
            "parser": "backend",
            "refId": "A",
            "root_selector": "rows",
            "source": "url",
            "type": "json",
            "url": (
                "/ops/control-plane/identity-table?pipeline=${pipeline}"
                "&run_type=${run_type:csv}&run_id=${run_id}"
            ),
            "url_options": {"data": "", "method": "GET"},
            "expr": "",
        },
        _ops_target("identity_rows", ref_id="B"),
    ]
    by_id[3022]["transformations"] = [{"id": "merge", "options": {}}]

    by_id[3023]["title"] = "Inspect Processed Records"
    by_id[3023]["description"] = (
        "SELECTED RUN · TIME RANGE · Complete Bronze/Silver/Gold accounting. "
        "Zero-valued outcomes remain evidence. Exact layer rollup is Inspect Layer "
        "Accounting. SELECT RUN / VALID EMPTY is not OK."
    )

    artifacts = by_id[3013]
    artifacts["fieldConfig"]["defaults"]["custom"]["inspect"] = True
    artifacts["fieldConfig"]["overrides"].append(
        {
            "matcher": {"id": "byName", "options": "ref"},
            "properties": [
                {
                    "id": "links",
                    "value": [
                        {
                            "title": "Copy artifact ref",
                            "url": "data:text/plain,${__value.raw}",
                            "targetBlank": True,
                            "includeVars": False,
                        }
                    ],
                },
                {"id": "custom.inspect", "value": True},
            ],
        }
    )
    artifacts["fieldConfig"]["overrides"].append(
        {
            "matcher": {"id": "byName", "options": "kind"},
            "properties": [
                {
                    "id": "links",
                    "value": [
                        {
                            "title": "Copy artifact ref",
                            "url": "data:text/plain,${__data.fields.ref}",
                            "targetBlank": True,
                            "includeVars": False,
                        }
                    ],
                }
            ],
        }
    )

    recon = by_id[3015]
    recon["description"] = recon["description"].replace(
        "SELECTED RUN · TIME RANGE · ", "SELECTED RUN · "
    )
    recon["links"] = [
        *(recon.get("links") or []),
        {
            "title": "Open Trust",
            "url": TRUST_URL,
            "targetBlank": False,
            "includeVars": False,
        },
    ]

    y = 14
    by_id[3022]["gridPos"] = {"h": 8, "w": 10, "x": 0, "y": y}
    by_id[3023]["gridPos"] = {"h": 8, "w": 14, "x": 10, "y": y}
    y = 22
    by_id[3011]["gridPos"]["y"] = y
    y = 28
    by_id[3012]["gridPos"]["y"] = y
    y = 33
    by_id[3015]["gridPos"]["y"] = y
    layers = _kv_table(
        panel_id=3016,
        title="Inspect Layer Accounting",
        description=(
            "SELECTED RUN · pipeline_run_report_v1.layers rollup (bronze/silver/gold "
            "counts including quarantined/dedup/excluded). Distinct from Inspect "
            "Processed Records stage/outcome percentages. Selection required when no "
            "run ID is set. VALID EMPTY means no layer rows; backend failure renders "
            "as QUERY ERROR. SELECT RUN / VALID EMPTY is not OK."
        ),
        no_value=(
            "VALID EMPTY — selected run report has no layer-accounting rows. "
            "Backend failure renders as QUERY ERROR."
        ),
        root_selectors=("layers",),
        y=41,
    )
    timings = _kv_table(
        panel_id=3014,
        title="Inspect Timings & Failure",
        description=(
            "SELECTED RUN · Optional pipeline_run_report_v1 failure and stage_timings "
            "blocks. Empty means those optional blocks were not recorded — not zero "
            "duration and not proof of success. Selection required when no run ID is "
            "set. VALID EMPTY / PARTIAL is not OK. Backend failure renders as QUERY ERROR."
        ),
        no_value=(
            "VALID EMPTY — selected run report has no failure or stage_timings rows "
            "(optional blocks not recorded; not zero duration and not proof of success). "
            "Backend failure renders as QUERY ERROR."
        ),
        root_selectors=("failure", "stage_timings"),
        y=54,
    )
    by_id[3013]["gridPos"]["y"] = 49

    ordered = [
        by_id[3022],
        by_id[3023],
        by_id[3011],
        by_id[3012],
        by_id[3015],
        layers,
        by_id[3013],
        timings,
    ]
    details["panels"] = ordered
    details["gridPos"]["y"] = 13

    workflow = _find(dashboard["panels"], 3098)
    workflow["gridPos"]["y"] = 62
    wf_table = _find(workflow.get("panels") or [], 3020)
    wf_table["gridPos"]["y"] = 62

    templating = dashboard["templating"]["list"]
    dashboard["templating"]["list"] = [
        _run_type_variable() if item.get("name") == "run_type" else item
        for item in templating
    ]

    PATH.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("wrote", PATH)
    print("root", [p.get("id") for p in dashboard["panels"]])
    print("details", [p.get("id") for p in details["panels"]])


if __name__ == "__main__":
    main()
