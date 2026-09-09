"""Apply Flow 3 Grafana JSON mutations for #10249/#10250/#10254/#10255/#10256."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DASH_DIR = ROOT / "grafana" / "dashboards"

RUN_ID_COLUMNS = [
    {"selector": "text", "text": "__text", "type": "string"},
    {"selector": "value", "text": "__value", "type": "string"},
]
IDENTITY_URL = (
    "/ops/control-plane/identity-table?pipeline=${pipeline}"
    "&run_type=${run_type:csv}&run_id=${run_id}&timezone=${__timezone}"
)
RUNBOOK_URL = (
    "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/"
    "docs/05-operations/runbooks/incident-response.md"
)
DQ_HANDOFF = (
    "/d/bioetl-dq-v2/bioetl-dq-v2?${workflow:queryparam}&${pipeline:queryparam}"
    "&${run_type:queryparam}&${run_id:queryparam}&var-stage=$__all&${__url_time_range}"
)
NAV_LINKS = {
    "bioetl-overview-v2": (
        '<div style="padding:2px 8px;line-height:1.25;font-size:16px;white-space:normal">'
        "<strong>Next dashboard:</strong> "
        '<a href="/d/bioetl-control-plane-v1/bioetl-control-plane-v1?'
        "${workflow:queryparam}&amp;${pipeline:queryparam}&amp;${run_type:queryparam}"
        '&amp;${run_id:queryparam}&amp;${__url_time_range}">Trust</a> for evidence · '
        '<a href="/d/bioetl-runtime/bioetl-runtime?${workflow:queryparam}'
        "&amp;${pipeline:queryparam}&amp;${run_type:queryparam}&amp;${run_id:queryparam}"
        '&amp;var-stage=$__all&amp;${__url_time_range}">Pipeline Diagnostics</a> '
        "for runtime blockers · "
        f'<a href="{DQ_HANDOFF.replace("&", "&amp;")}">Data Quality</a> '
        "for DQ reasons · "
        '<a href="/d/bioetl-provider-health-v2/bioetl-provider-health-v2?'
        "${workflow:queryparam}&amp;${pipeline:queryparam}&amp;${run_type:queryparam}"
        "&amp;${run_id:queryparam}&amp;${provider:queryparam}"
        '&amp;var-pipeline_context=${pipeline:percentencode}&amp;${__url_time_range}">'
        "Provider Health</a> for provider causes. "
        '<a href="/d/bioetl-overview-v2/bioetl-overview-v2?${workflow:queryparam}'
        "&amp;${pipeline:queryparam}&amp;${run_type:queryparam}&amp;${run_id:queryparam}"
        '&amp;${__url_time_range}">Back to top</a>.'
        "</div>"
    ),
}


def _walk(panels: list[object]) -> list[dict[str, object]]:
    found: list[dict[str, object]] = []
    for panel in panels:
        if not isinstance(panel, dict):
            continue
        found.append(panel)
        nested = panel.get("panels")
        if isinstance(nested, list):
            found.extend(_walk(nested))
    return found


def _patch_run_id_variable(variable: dict[str, object]) -> None:
    if variable.get("name") != "run_id":
        return
    for key in ("definition",):
        value = variable.get(key)
        if isinstance(value, str) and "dimension=run_id" in value:
            variable[key] = value.replace("response_shape=list", "response_shape=options")
    query = variable.get("query")
    if not isinstance(query, dict):
        return
    infinity_query = query.get("infinityQuery")
    if not isinstance(infinity_query, dict):
        return
    url = str(infinity_query.get("url") or "")
    if "dimension=run_id" in url:
        infinity_query["url"] = url.replace(
            "response_shape=list", "response_shape=options"
        )
    infinity_query["columns"] = list(RUN_ID_COLUMNS)


def _identity_overrides() -> list[dict[str, object]]:
    return [
        {
            "matcher": {"id": "byName", "options": "parameter"},
            "properties": [
                {"id": "displayName", "value": "Parameter"},
                {"id": "custom.width", "value": 210},
                {"id": "custom.align", "value": "left"},
                {
                    "id": "custom.cellOptions",
                    "value": {"type": "auto", "wrapText": True},
                },
            ],
        },
        {
            "matcher": {"id": "byName", "options": "value"},
            "properties": [
                {"id": "displayName", "value": "Value"},
                {"id": "custom.align", "value": "left"},
                {"id": "custom.inspect", "value": True},
                {
                    "id": "links",
                    "value": [
                        {
                            "title": "Copy/Open full value (plain text)",
                            "url": "data:text/plain,${__value.raw}",
                            "targetBlank": True,
                            "includeVars": False,
                        }
                    ],
                },
            ],
        },
        {
            "matcher": {"id": "byName", "options": "raw_value"},
            "properties": [{"id": "custom.hidden", "value": True}],
        },
    ]


def _patch_identity_panel(panel: dict[str, object]) -> None:
    for target in panel.get("targets") or []:
        if not isinstance(target, dict):
            continue
        url = str(target.get("url") or "")
        if "/ops/control-plane/identity-table?" not in url:
            continue
        target["url"] = IDENTITY_URL
        target["root_selector"] = "display_rows"
        field = panel.setdefault("fieldConfig", {})
        if not isinstance(field, dict):
            continue
        field["overrides"] = _identity_overrides()
        organize = None
        for transform in panel.get("transformations") or []:
            if isinstance(transform, dict) and transform.get("id") == "organize":
                organize = transform.setdefault("options", {})
        if isinstance(organize, dict):
            exclude = organize.setdefault("excludeByName", {})
            if isinstance(exclude, dict):
                exclude["Time"] = True
                exclude["__name__"] = True
                exclude["Value"] = True
                exclude["raw_value"] = True
            rename = organize.setdefault("renameByName", {})
            if isinstance(rename, dict):
                rename["parameter"] = "Parameter"
                rename["value"] = "Value"


def _replace_set_range_titles(node: object) -> None:
    if isinstance(node, dict):
        title = node.get("title")
        if title == "Set range to run":
            node["title"] = "Open run in Run Explorer"
        for value in node.values():
            _replace_set_range_titles(value)
    elif isinstance(node, list):
        for item in node:
            _replace_set_range_titles(item)


def _all_label_replace(expr: str) -> str:
    if '"pipeline","$pipeline","",""' in expr:
        expr = expr.replace(
            '"pipeline","$pipeline","",""',
            '"pipeline","${pipeline:text}","",""',
        )
    if '"run_type","$run_type","",""' in expr:
        expr = expr.replace(
            '"run_type","$run_type","",""',
            '"run_type","${run_type:text}","",""',
        )
    return expr


def _patch_overview_timelines(dashboard: dict[str, object]) -> None:
    for panel in _walk(list(dashboard.get("panels") or [])):
        if panel.get("type") != "state-timeline":
            continue
        options = panel.get("options")
        if isinstance(options, dict):
            options["showValue"] = "never"
        for target in panel.get("targets") or []:
            if not isinstance(target, dict):
                continue
            expr = target.get("expr")
            if isinstance(expr, str):
                target["expr"] = _all_label_replace(expr)


def _patch_overview_nav(dashboard: dict[str, object]) -> None:
    for panel in _walk(list(dashboard.get("panels") or [])):
        if panel.get("id") != 9021:
            continue
        options = panel.setdefault("options", {})
        if isinstance(options, dict):
            options["content"] = NAV_LINKS["bioetl-overview-v2"]


def _patch_dq_handoffs(dashboard: dict[str, object]) -> None:
    replacements = (
        (
            "open the canonical Control Plane",
            '<a href="/d/bioetl-control-plane-v1/bioetl-control-plane-v1?'
            "${workflow:queryparam}&amp;${pipeline:queryparam}&amp;${run_type:queryparam}"
            '&amp;${run_id:queryparam}&amp;${__url_time_range}">Control Plane</a>',
        ),
        (
            "open Trust for store/manifest failures",
            '<a href="/d/bioetl-control-plane-v1/bioetl-control-plane-v1?'
            "${workflow:queryparam}&amp;${pipeline:queryparam}&amp;${run_type:queryparam}"
            '&amp;${run_id:queryparam}&amp;${__url_time_range}">Trust</a> for store/manifest failures',
        ),
    )
    for panel in _walk(list(dashboard.get("panels") or [])):
        options = panel.get("options")
        if not isinstance(options, dict):
            continue
        content = options.get("content")
        if not isinstance(content, str):
            continue
        updated = content
        if "<a href=" in updated:
            continue
        for needle, link in replacements:
            updated = updated.replace(needle, link, 1)
        options["content"] = updated


def _extract_alert_panel(dashboard: dict[str, object]) -> dict[str, object] | None:
    for panel in dashboard.get("panels") or []:
        if not isinstance(panel, dict) or panel.get("id") != 2020:
            continue
        nested = panel.get("panels")
        if not isinstance(nested, list):
            return None
        for index, child in enumerate(nested):
            if isinstance(child, dict) and child.get("id") == 2005:
                return nested.pop(index)
    return None


def _ensure_limit(panel: dict[str, object], limit: int) -> None:
    transforms = panel.setdefault("transformations", [])
    if not isinstance(transforms, list):
        return
    if any(isinstance(item, dict) and item.get("id") == "limit" for item in transforms):
        return
    transforms.insert(0, {"id": "limit", "options": {"limitField": limit}})


def _patch_incident(dashboard: dict[str, object]) -> None:
    root = dashboard.get("panels")
    if not isinstance(root, list):
        return
    alert = next(
        (
            panel
            for panel in root
            if isinstance(panel, dict) and panel.get("id") == 2005
        ),
        None,
    )
    if alert is None:
        alert = _extract_alert_panel(dashboard)
        if alert is None:
            return
        insert_at = next(
            (
                index
                for index, panel in enumerate(root)
                if isinstance(panel, dict) and panel.get("id") == 2010
            ),
            len(root),
        )
        root.insert(insert_at + 1, alert)
    alert["gridPos"] = {"h": 5, "w": 24, "x": 0, "y": 13}
    defaults = (alert.get("fieldConfig") or {}).get("defaults") or {}
    links = list(defaults.get("links") or []) if isinstance(defaults, dict) else []
    if not any(
        isinstance(item, dict) and "runbook" in str(item.get("title", "")).lower()
        for item in links
    ):
        links.append(
            {
                "title": "Open incident response runbook",
                "url": RUNBOOK_URL,
                "targetBlank": True,
                "includeVars": False,
            }
        )
        if isinstance(defaults, dict):
            defaults["links"] = links
    _ensure_limit(alert, 3)
    for panel in _walk(list(dashboard.get("panels") or [])):
        if panel.get("id") == 2010:
            panel["gridPos"] = {"h": 5, "w": 24, "x": 0, "y": 8}


def _patch_run_explorer_reasons_artifacts(dashboard: dict[str, object]) -> None:
    for panel in _walk(list(dashboard.get("panels") or [])):
        if panel.get("id") == 3012:
            overrides = (panel.get("fieldConfig") or {}).get("overrides")
            if isinstance(overrides, list):
                overrides.append(
                    {
                        "matcher": {"id": "byName", "options": "reason_label"},
                        "properties": [
                            {"id": "displayName", "value": "Reason"},
                            {"id": "custom.width", "value": 280},
                            {
                                "id": "custom.cellOptions",
                                "value": {"type": "auto", "wrapText": True},
                            },
                        ],
                    }
                )
                overrides.append(
                    {
                        "matcher": {"id": "byName", "options": "explain"},
                        "properties": [
                            {"id": "displayName", "value": "Next step"},
                            {
                                "id": "links",
                                "value": [
                                    {
                                        "title": "Open Data Quality",
                                        "url": DQ_HANDOFF,
                                        "targetBlank": False,
                                        "includeVars": False,
                                    }
                                ],
                            },
                        ],
                    }
                )
        if panel.get("id") != 3013:
            continue
        organize = None
        for transform in panel.get("transformations") or []:
            if isinstance(transform, dict) and transform.get("id") == "organize":
                organize = transform.setdefault("options", {})
        if isinstance(organize, dict):
            rename = organize.setdefault("renameByName", {})
            if isinstance(rename, dict):
                rename["title"] = "Artifact"
                rename["action"] = "Action"
                rename["format"] = "Format"
                rename["kind"] = "Format"
            exclude = organize.setdefault("excludeByName", {})
            if isinstance(exclude, dict):
                exclude["ref"] = True
        overrides = (panel.get("fieldConfig") or {}).get("overrides")
        if isinstance(overrides, list):
            overrides.append(
                {
                    "matcher": {"id": "byName", "options": "title"},
                    "properties": [
                        {"id": "displayName", "value": "Artifact"},
                        {
                            "id": "links",
                            "value": [
                                {
                                    "title": "${__data.fields.action} ${__data.fields.title}",
                                    "url": (
                                        "/api/datasources/proxy/uid/bioetl-ops-http"
                                        "/ops/observability/pipeline-run-report-artifact"
                                        "?pipeline=${pipeline:percentencode}"
                                        "&run_id=${run_id:percentencode}"
                                        "&format=${__data.fields.format}"
                                    ),
                                    "targetBlank": True,
                                }
                            ],
                        },
                    ],
                }
            )


def patch_dashboard(path: Path) -> None:
    dashboard = json.loads(path.read_text(encoding="utf-8"))
    templating = dashboard.get("templating") or {}
    for variable in templating.get("list") or []:
        if isinstance(variable, dict):
            _patch_run_id_variable(variable)
    for panel in _walk(list(dashboard.get("panels") or [])):
        _patch_identity_panel(panel)
    _replace_set_range_titles(dashboard)
    uid = str(dashboard.get("uid") or "")
    if uid == "bioetl-overview-v2":
        _patch_overview_timelines(dashboard)
        _patch_overview_nav(dashboard)
    if uid == "bioetl-dq-v2":
        _patch_dq_handoffs(dashboard)
    if uid == "bioetl-incident-v1":
        _patch_incident(dashboard)
    if uid == "bioetl-run-explorer-v1":
        _patch_run_explorer_reasons_artifacts(dashboard)
    path.write_text(
        json.dumps(dashboard, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    for path in sorted(DASH_DIR.glob("bioetl-*.json")):
        patch_dashboard(path)


if __name__ == "__main__":
    main()
