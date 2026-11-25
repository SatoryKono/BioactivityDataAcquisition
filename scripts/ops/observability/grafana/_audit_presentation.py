"""Presentation-only safeguards shared by canonical dashboard generators."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import yaml
from typing import Any

from scripts.ops.observability.grafana._incident_explanations import (
    apply_incident_evidence_clocks,
)
from scripts.ops.observability.grafana._overview_identity import (
    apply_overview_evidence_clocks,
)

_RUN_ID = "Run ID"
_DATA_QUALITY = "Data Quality"

_WRAP_TEXT = "custom.wrapText"
_CELL_OPTIONS = "custom.cellOptions"
_CUSTOM_WIDTH = "custom.width"
_CURRENT_PRESENTATION = "bioetlCurrentPresentation"
_SNAPSHOT_PREFIX = "TIME RANGE SNAPSHOT · "

_LABEL_TRANSLATIONS = {
    "НЕТ ЗАПУСКОВ": "NO RUNS",
    "нет данных": "NO DATA",
    "нет записей": "NO RECORDS",
    "не применимо": "N/A",
}
_TRANSLATABLE_KEYS = frozenset({"text", "title", "description", "noValue"})


def enable_adaptive_catalog(dashboard: dict[str, Any]) -> None:
    """Select the managed adaptive plugin after its runtime has been deployed.

    Deliberately explicit: a native selector-only plugin must never receive
    a responsive-table panel merely because a source generator was invoked.
    """
    if dashboard.get("uid") != "bioetl-run-explorer-v1":
        raise ValueError("Adaptive catalog is only applicable to Run Explorer")
    panel = next(p for p in dashboard["panels"] if p.get("id") == 3010)
    panel["type"] = "bioetl-selectorshell-panel"
    panel["options"].update(
        viewMode="runs",
        compactFields=["Provider", "Pipeline", _RUN_ID, "Overview"],
    )
    overrides = panel.get("fieldConfig", {}).get("overrides", [])
    run_id = next(
        (
            item
            for item in overrides
            if item.get("matcher", {}).get("options") == _RUN_ID
        ),
        {},
    )
    actions = next(
        (
            prop["value"]
            for prop in run_id.get("properties", [])
            if prop["id"] == "links"
        ),
        [],
    )
    # Native compact tables move hidden-column actions into the Run ID menu.
    # Restoring a wide column must restore its row-bound action as well, while
    # retaining that menu for the narrow view and full details.
    for override in panel.get("fieldConfig", {}).get("overrides", []):
        _restore_catalog_field(override, actions)
    if "description" in panel:
        panel["description"] = panel["description"].replace(
            "Compact view: Pipeline, Run ID, Started, Overview and Replay Readiness. "
            "Workflow, Provider, Duration, Saved Evidence and Data Quality remain "
            "in the table data inspector.",
            "Wide table: Workflow, Pipeline, Run ID, Started, Duration, Overview, "
            "Data Quality and Replay Readiness. Compact view: Provider, Pipeline, "
            "Run ID and Overview. Details retains all fields.",
        )


def _translate_label_text(item: str) -> str:
    """Apply the English label map to one presentation string."""
    for source, target in _LABEL_TRANSLATIONS.items():
        item = item.replace(source, target)
    return item


def _translate_mapping(value: dict[str, Any]) -> None:
    """Translate string labels in one mapping node, then descend."""
    for key, item in value.items():
        if key in _TRANSLATABLE_KEYS and isinstance(item, str):
            value[key] = _translate_label_text(item)
            continue
        _translate_audit_labels(item)


def _translate_audit_labels(value: Any) -> None:
    """Replace legacy Russian presentation tokens with English labels."""
    if isinstance(value, dict):
        _translate_mapping(value)
        return
    if isinstance(value, list):
        for item in value:
            _translate_audit_labels(item)


def _set_wrap(properties: list[dict[str, Any]], *, enabled: bool) -> None:
    """Toggle wrapText / cellOptions.wrapText on one override property list."""
    seen: set[str] = set()
    for prop in properties:
        prop_id = prop.get("id")
        if isinstance(prop_id, str):
            seen.add(prop_id)
        if prop_id == _WRAP_TEXT:
            prop["value"] = enabled
        elif prop_id == _CELL_OPTIONS:
            prop["value"]["wrapText"] = enabled
    if _WRAP_TEXT not in seen:
        properties.append({"id": _WRAP_TEXT, "value": enabled})
    if _CELL_OPTIONS not in seen:
        properties.append(
            {"id": _CELL_OPTIONS, "value": {"type": "auto", "wrapText": enabled}}
        )


def _stamp_run_explorer_wrap(panel: dict[str, Any]) -> None:
    """Keep twenty native rows stable; full identity stays available in Inspect."""
    panel["options"].setdefault("footer", {})["enablePagination"] = False
    custom = panel["fieldConfig"]["defaults"]["custom"]
    custom.update(
        wrapText=False,
        wrapHeaderText=True,
        cellOptions={"type": "auto", "wrapText": False},
    )
    overrides = panel["fieldConfig"].get("overrides", [])
    for override in overrides:
        properties = override.get("properties", [])
        # TableRT can apply one field's wrap option to every cell in a row.
        _set_wrap(properties, enabled=False)
    run_id = next(
        item for item in overrides if item.get("matcher", {}).get("options") == _RUN_ID
    )
    _set_wrap(run_id["properties"], enabled=False)


def _stamp_overview_widths(panel: dict[str, Any]) -> None:
    """Match Overview verdict column widths before displayName remapping."""
    widths = {"Processing": None, "Overall verdict": 75, "Trust": 95}
    for override in panel["fieldConfig"].get("overrides", []):
        name = override.get("matcher", {}).get("options")
        if name not in widths:
            continue
        width = widths[name]
        props = override["properties"]
        props[:] = [p for p in props if p.get("id") != _CUSTOM_WIDTH]
        if width is not None:
            props.append({"id": _CUSTOM_WIDTH, "value": width})


def _ensure_cached_bronze_reason_mapping(prop: dict[str, Any]) -> None:
    """Insert or merge the cached-Bronze reason value mapping."""
    mapping = {
        "type": "value",
        "options": {
            "cached_bronze_no_remote_probe": {
                "text": "Cached Bronze used; provider API was not called."
            }
        },
    }
    value_map = next(
        (item for item in prop["value"] if item.get("type") == "value"),
        None,
    )
    if value_map is not None:
        value_map["options"].update(mapping["options"])
        return
    prop["value"].insert(0, mapping)


def _stamp_overview_reason_mapping(panel: dict[str, Any]) -> None:
    """Expose the cached-Bronze reason as readable English copy."""
    for override in panel.get("fieldConfig", {}).get("overrides", []):
        if override.get("matcher", {}).get("options") != "Reason":
            continue
        for prop in override.get("properties", []):
            if prop.get("id") == "mappings":
                _ensure_cached_bronze_reason_mapping(prop)


def _stamp_panel_presentation(dashboard: dict[str, Any], panel: dict[str, Any]) -> None:
    """Apply dashboard-specific presentation rules to one panel."""
    uid = dashboard.get("uid")
    panel_id = panel.get("id")
    if uid == "bioetl-run-explorer-v1" and panel_id == 3010:
        _stamp_run_explorer_wrap(panel)
        return
    if uid == "bioetl-dq-v2" and panel_id == 9406:
        for override in panel.get("fieldConfig", {}).get("overrides", []):
            if override.get("matcher", {}).get("options") == "Reason":
                override["properties"][:] = [
                    prop
                    for prop in override["properties"]
                    if prop.get("id") != _CUSTOM_WIDTH
                ]
        return
    if uid != "bioetl-overview-v2":
        return
    if panel_id == 9604:
        panel.setdefault("options", {})["text"] = {"valueSize": 24}
        return
    if panel_id == 9603:
        _stamp_overview_widths(panel)
        return
    if panel_id == 9002:
        _stamp_overview_reason_mapping(panel)


def _shift_panel(panel: dict[str, Any], delta: int) -> None:
    panel["gridPos"]["y"] += delta
    for child in panel.get("panels", []):
        _shift_panel(child, delta)


def _fit_coverage_stats(dashboard: dict[str, Any]) -> None:
    """Allocate a readable line per series without changing status semantics."""
    for row in dashboard.get("panels", []):
        if row.get("id") != 8809:
            continue
        old_bottom, delta = _expand_coverage_row(row)
        if delta <= 0:
            continue
        for panel in dashboard["panels"]:
            if panel is not row and panel["gridPos"]["y"] >= old_bottom:
                _shift_panel(panel, delta)


def _expand_coverage_row(row: dict[str, Any]) -> tuple[int, int]:
    children = row.get("panels", [])
    old_bottom = max(
        (p["gridPos"]["y"] + p["gridPos"]["h"] for p in children),
        default=row["gridPos"]["y"] + 1,
    )
    for panel in children:
        if panel.get("id") in {9102, 9491}:
            panel["gridPos"]["h"] = max(8, panel["gridPos"]["h"])
            # Preserve the main branch's explicit per-field reduction while
            # stacking readable named rows in the narrower coverage panel.
            panel["options"]["orientation"] = "horizontal"
            reduction = {
                "id": "reduce",
                "options": {"reducers": ["lastNotNull"], "mode": "reduceFields"},
            }
            transformations = panel.setdefault("transformations", [])
            if reduction not in transformations:
                transformations.append(reduction)
            panel["options"].setdefault("reduceOptions", {})["values"] = True
    new_bottom = max(
        (p["gridPos"]["y"] + p["gridPos"]["h"] for p in children),
        default=old_bottom,
    )
    # Grafana's v2 conversion preserves array order. Keep that order aligned
    # with the declared grid, including short explanatory cards above stats.
    children.sort(key=lambda panel: (panel["gridPos"]["y"], panel["gridPos"]["x"]))
    return old_bottom, new_bottom - old_bottom


def stamp_audit_presentation(dashboard: dict[str, Any]) -> None:
    """Keep cached-provider explanations and long verdicts readable."""
    _translate_audit_labels(dashboard)
    if dashboard.get("uid") == "bioetl-run-explorer-v1":
        for item in [dashboard, *dashboard.get("panels", [])]:
            if "description" in item:
                item["description"] = item["description"].replace(
                    "latest 10 launches", "latest 20 launches"
                )
    if dashboard.get("refresh") in {"60s", "1m"}:
        dashboard["refresh"] = "1m"
        old_note = " Saved refresh is 60s; Grafana suspends automatic refresh for an absolute time range. CURRENT managed panels use their own clock."
        refresh_note = " Saved refresh is 1m (60 seconds), matching the refresh selector. CURRENT managed panels use their own clock."
        description = dashboard.get("description", "").replace(old_note, "")
        if refresh_note not in description:
            dashboard["description"] = description + refresh_note
    if dashboard.get("uid") == "bioetl-incident-v1":
        _fit_coverage_stats(dashboard)
    for panel in dashboard.get("panels", []):
        stamp_audit_presentation(panel)
        _stamp_panel_presentation(dashboard, panel)


def _walk_panels(panels: list[dict]):
    for panel in panels:
        yield panel
        yield from _walk_panels(panel.get("panels", []))


def _is_current_panel(panel: dict, spec: dict) -> bool:
    if spec.get("evidence_source") not in {"prometheus", "grafana_builtin"}:
        return False
    scope = spec.get("scope")
    prefix = panel.get("description", "").split("·", 1)[0]
    declared_current = "CURRENT" in prefix and "TIME RANGE" not in prefix
    current = (
        scope == "current"
        or declared_current
        or _CURRENT_PRESENTATION in panel.get("options", {})
    )
    return current and panel.get("type") in {"stat", "table", "timeseries"}


def restore_native_current_presentation(
    dashboard: dict, *, remove: bool = False
) -> None:
    """Restore source presentation before a deterministic projection/rebuild."""
    for panel in _walk_panels(dashboard.get("panels", [])):
        options = panel.get("options", {})
        original = options.get(_CURRENT_PRESENTATION)
        if original is None:
            continue
        panel.update(title=original["title"], description=original["description"])
        if "content" in original:
            options["content"] = original["content"]
        if remove:
            options.pop(_CURRENT_PRESENTATION)


def mark_native_snapshot_clocks(dashboard: dict) -> None:
    """Native Grafana instant queries use the selected end, including absolute ranges.

    Only the managed CURRENT renderer owns an independent clock. Native values
    therefore remain usable historical snapshots and never claim live health.
    Keep the original presentation as projection metadata, not a second query.
    """
    root = Path(__file__).resolve().parents[4]
    contract = yaml.safe_load(
        (
            root / "docs/03-guides/dashboards/contracts/panel-content-contract.yaml"
        ).read_text(encoding="utf-8")
    )
    specs = contract["dashboards"].get(dashboard.get("uid"), {}).get("panels", {})
    for panel in _walk_panels(dashboard.get("panels", [])):
        options = panel.get("options", {})
        content = options.get("content", "")
        if panel.get("type") == "text" and "CURRENT:" in content:
            options[_CURRENT_PRESENTATION] = {
                "title": panel["title"],
                "description": panel.get("description", ""),
                "content": content,
            }
            options["content"] = content.replace("CURRENT:", "PERIOD END SNAPSHOT:")
        if panel.get("type") == "text" and "PERIOD END SNAPSHOT:" in options.get(
            "content", ""
        ):
            panel["description"] = (
                options[_CURRENT_PRESENTATION]["description"]
                .replace("CURRENT", "PERIOD END SNAPSHOT")
                .replace(
                    "current fleet telemetry",
                    "fleet telemetry at the selected period end",
                )
                .replace("current scope", "selected period-end scope")
            )
        if panel.get("description", "").startswith(_SNAPSHOT_PREFIX):
            original = panel["options"][_CURRENT_PRESENTATION]
            panel.update(title=original["title"], description=original["description"])
        if not _is_current_panel(panel, specs.get(str(panel["id"]), {})):
            continue
        panel.setdefault("options", {})[_CURRENT_PRESENTATION] = {
            "title": panel["title"],
            "description": panel.get("description", ""),
        }
        title = (
            panel["title"].replace("Current", "Snapshot").replace("CURRENT", "SNAPSHOT")
        )
        if panel["id"] in {9606, 22012}:
            title += " · period end"
        panel["title"] = title
        panel["description"] = (
            _SNAPSHOT_PREFIX
            + "Evaluated at the selected period end, including absolute historical periods; not live data. "
            "Independent CURRENT clocks and the live-clock instructions below apply only in the managed adaptive profile. "
            + panel["description"]
        )


def _current_queries(panel: dict, native_panels: dict) -> list[dict]:
    queries = panel.get("targets", [])
    if len(queries) == 1 and "panelId" in queries[0]:
        # Dashboard datasource consumers request the donor's raw frames.
        donor = native_panels.get(queries[0]["panelId"])
        if queries[0].get("withTransforms") or donor is None:
            raise ValueError("Current consumer requires an untransformed donor")
        queries = donor.get("targets", [])
    if not queries or any("expr" not in query for query in queries):
        raise ValueError(f"Current panel {panel['id']} requires Prometheus queries")
    return queries


def _wrap_current_panel(panel: dict, queries: list[dict]) -> None:
    view = {
        "pluginId": panel["type"],
        "queries": deepcopy(queries),
        "transformations": deepcopy(panel.get("transformations", [])),
        "options": deepcopy(panel.get("options", {})),
    }
    panel["type"] = "bioetl-selectorshell-panel"
    panel["options"] = {"viewMode": "current", "currentView": view}
    # The host must not also execute a historical request or duplicate queries.
    panel["targets"] = []
    panel["transformations"] = []
    panel["description"] += (
        " Managed CURRENT queries use an independent clock and refresh every 30s. "
        "The timestamp is query evaluation time, not publication or event time. "
        "The historical dashboard interval does not set the current query end; "
        "current trends retain the selected duration and end at now. "
        "Timeouts, failed queries and unverified response time remain unavailable."
    )
    if panel["id"] == 9701:
        panel["title"] = "Review Current Workflow Evidence · threshold 24h"


def _verify_current_donors(panels: dict) -> None:
    for panel in panels.values():
        for query in panel.get("targets", []):
            donor = panels.get(query.get("panelId"), {})
            if donor.get("options", {}).get("viewMode") == "current":
                raise ValueError("Historical consumer cannot reuse a CURRENT donor")


def _project_current_time(dashboard: dict) -> None:
    """Use an independent query clock for source-declared CURRENT telemetry."""
    restore_native_current_presentation(dashboard)
    root = Path(__file__).resolve().parents[4]
    contract = yaml.safe_load(
        (
            root / "docs/03-guides/dashboards/contracts/panel-content-contract.yaml"
        ).read_text(encoding="utf-8")
    )
    specs = contract["dashboards"].get(dashboard.get("uid"), {}).get("panels", {})
    panels = {panel["id"]: panel for panel in _walk_panels(dashboard.get("panels", []))}
    native_panels = deepcopy(panels)
    for panel_id, panel in panels.items():
        if "${workflow_evidence_freshness}" in panel.get("title", ""):
            panel["title"] = panel["title"].replace(
                " · ${workflow_evidence_freshness}", ""
            )
        current = _is_current_panel(panel, specs.get(str(panel_id), {}))
        panel.get("options", {}).pop(_CURRENT_PRESENTATION, None)
        if current:
            _wrap_current_panel(panel, _current_queries(panel, native_panels))
    _verify_current_donors(panels)
    if "templating" in dashboard:
        dashboard["templating"]["list"] = [
            item
            for item in dashboard["templating"]["list"]
            if item.get("name") != "workflow_evidence_freshness"
        ]


def _adapt_replay(dashboard: dict) -> None:
    for panel in dashboard["panels"]:
        if panel["id"] == 9423:
            # Keep all checks available through the existing pagination.
            panel["gridPos"]["h"] = 11


def _adapt_dq(dashboard: dict) -> None:
    for panel in dashboard["panels"]:
        if panel["id"] == 9406:
            panel["type"] = "bioetl-selectorshell-panel"
            panel["options"].update(
                viewMode="record",
                compactFields=["Processing", "Overall verdict", "Trust"],
            )
            panel["gridPos"]["h"] = 4
        elif panel["id"] == 9403:
            panel["gridPos"].update(y=11, h=5)


def _adapt_incident(dashboard: dict) -> None:
    panels = {panel["id"]: panel for panel in dashboard["panels"]}
    suspects, alerts = panels.get(2010), panels.get(2005)
    if suspects is None or alerts is None:
        return
    suspects["gridPos"].update(x=0, y=7, w=12, h=8)
    alerts["gridPos"].update(x=12, y=7, w=12, h=8)
    fields = [
        "Rank",
        "Diagnostic priority",
        "Cause verification",
        "Event freshness",
        "Signal",
        "Object",
    ]
    if suspects["options"].get("viewMode") == "current":
        suspects["options"]["currentView"]["compactFields"] = fields
    else:
        suspects["type"] = "bioetl-selectorshell-panel"
        suspects["options"].update(viewMode="rows", compactFields=fields)
    alerts["options"]["currentView"]["compactFields"] = [
        "Severity",
        "Alert",
        "Pipeline",
        "State",
    ]


def _adapt_overview(dashboard: dict) -> None:
    # The native saved verdict/current cards already lead the answer. Preserve
    # main's extra domain-row height and move later evidence out of its way.
    panels = {panel["id"]: panel for panel in dashboard["panels"]}
    domains = panels[9002]
    bottom = domains["gridPos"]["y"] + domains["gridPos"]["h"]
    delta = max(0, 9 - domains["gridPos"]["h"])
    domains["gridPos"]["h"] += delta
    for panel in dashboard["panels"]:
        if panel is not domains and panel["gridPos"]["y"] >= bottom:
            _shift_panel(panel, delta)


def project_adaptive_dashboard(source: dict) -> dict:
    """Preserve queries and identity; adapt the catalog and prioritize the verdict."""
    result = deepcopy(source)
    _project_current_time(result)
    projectors = {
        "bioetl-run-explorer-v1": enable_adaptive_catalog,
        "bioetl-control-plane-v1": _adapt_replay,
        "bioetl-dq-v2": _adapt_dq,
        "bioetl-incident-v1": _adapt_incident,
        "bioetl-overview-v2": _adapt_overview,
    }
    projector = projectors.get(result.get("uid"))
    if projector is not None:
        projector(result)
    return result


def apply_portfolio_evidence_contract(payload: dict) -> None:
    """Apply only confirmed presentation fixes after older layout migrations."""
    uid = payload.get("uid")
    note = (
        " Canonical presentation contract: dashboard-2.0; UID v1/v2 suffixes are stable compatibility identifiers. "
        "Shared selectors are Workflow, Pipeline, Run Type and Run ID; local lookup, derived selectors and diagnostic views have role-specific scope. "
        "Saved outcomes, current alert urgency, coverage and replay readiness are distinct state vocabularies."
    )
    if note not in payload.get("description", ""):
        payload["description"] = payload.get("description", "") + note
    panels = {p["id"]: p for p in payload.get("panels", [])}
    if uid == "bioetl-run-explorer-v1":
        panels[1]["description"] = (
            panels[1].get("description", "").replace("latest 10", "latest 20")
        )
    if uid == "bioetl-dq-v2":
        payload["description"] = payload.get("description", "").replace(
            "Run ID is always selected",
            "Run ID '-' resolves AUTO to the latest run in scope; an explicit UUID stays selected",
        )
    if uid == "bioetl-incident-v1":
        apply_incident_evidence_clocks(payload, panels)
    if uid == "bioetl-overview-v2":
        apply_overview_evidence_clocks(payload, panels)


def _restore_catalog_field(override: dict, actions: list[dict]) -> None:
    restored_actions = {"Workflow": "Workflow passport", _DATA_QUALITY: _DATA_QUALITY}
    name = override.get("matcher", {}).get("options")
    for prop in override.get("properties", []):
        if name in restored_actions and prop["id"] == "links":
            prop["value"] = deepcopy(
                [
                    action
                    for action in actions
                    if action.get("title") == restored_actions[name]
                ]
            )
        if (
            name in {"Workflow", "Duration", "Replay Readiness", _DATA_QUALITY}
            and prop.get("id") == "custom.hidden"
        ):
            prop["value"] = False


def stamp_overview_query_diagnostics(dashboard: dict) -> None:
    """Retain approved source/error guidance on rebuilt Overview panels."""
    uid = dashboard.get("uid")
    if uid not in {"bioetl-overview-v2", "bioetl-incident-v1", "bioetl-dq-v2"}:
        return
    pending = list(dashboard.get("panels", []))
    while pending:
        panel = pending.pop()
        pending.extend(panel.get("panels", []))
        panel_id = panel.get("id")
        if uid == "bioetl-dq-v2":
            if panel_id in {9400, 9460, 9451}:
                panel["fieldConfig"]["defaults"]["noValue"] = (
                    "No result · inspect source panel 9406"
                )
                _append_query_guidance(
                    panel,
                    "If this panel has no result, inspect Review Selected Run Status "
                    "(panel 9406) and its query status. No result alone cannot distinguish "
                    "a successful query without evidence from a source query error.",
                )
            if panel_id == 9400:
                _append_query_guidance(
                    panel,
                    "AUTO is local to Run Overview and Data Quality; Replay Readiness "
                    "and Incident Workspace request an explicit exact run.",
                )
            elif panel_id == 9406:
                _append_query_guidance(
                    panel,
                    "QUERY ERROR means the request or query evaluation failed; use Query "
                    "Inspector for the cause. A failed expression does not establish a backend outage.",
                )
            elif panel_id == 9403:
                for target in panel.get("targets", []):
                    if target.get("parser") == "backend":
                        target.pop("uql", None)
            continue
        if uid == "bioetl-incident-v1":
            if panel_id == 2101:
                _append_query_guidance(
                    panel,
                    "Requires an exact Run ID; '-' prompts selection and does not request AUTO. "
                    "The Provider selector is not an input for this saved-run request.",
                )
            continue
        if panel_id in {99, 9300, 9480, 9481, 9482, 9483, 9603, 9604}:
            panel["fieldConfig"]["defaults"]["noValue"] = (
                "No result · inspect source panel 9002"
            )
        if panel_id in {99, 9300, 9603, 9604}:
            _append_query_guidance(
                panel,
                "If this panel has no result, inspect Review Run Domains (panel 9002) "
                "and its query status. No result alone cannot distinguish a successful "
                "query without evidence from a source query error.",
            )
        if panel_id == 99:
            _append_query_guidance(
                panel,
                "AUTO is local to Run Overview and Data Quality; Replay Readiness "
                "and Incident Workspace request an explicit exact run.",
            )
        elif panel_id == 9002:
            _append_query_guidance(
                panel,
                "QUERY ERROR means the request or query evaluation failed; use Query "
                "Inspector for the cause. A failed expression does not establish a backend outage.",
            )
        elif panel_id == 9605:
            panel["fieldConfig"]["overrides"] = [
                {
                    "matcher": {"id": "byName", "options": "FIRING"},
                    "properties": [
                        {"id": "color", "value": {"mode": "thresholds"}},
                        {
                            "id": "thresholds",
                            "value": {
                                "mode": "absolute",
                                "steps": [
                                    {"value": None, "color": "text"},
                                    {"value": 1, "color": "red"},
                                ],
                            },
                        },
                    ],
                }
            ]


def _append_query_guidance(panel: dict, guidance: str) -> None:
    description = panel.get("description", "")
    if guidance not in description:
        panel["description"] = f"{description} {guidance}".strip()
