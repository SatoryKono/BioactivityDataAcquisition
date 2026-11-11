"""Embed Incident Workspace's global alert donor independently of saved runs."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from scripts.ops.observability.grafana.dashboard_context_links import (
    GRAFANA_ALL,
    DashboardContext,
    build_handoff_url,
)

_INCIDENT_URL = build_handoff_url(
    "bioetl-incident-v1",
    context=DashboardContext(GRAFANA_ALL, GRAFANA_ALL, GRAFANA_ALL, "-"),
    template=False,
    extras={"viewPanel": "22005"},
)


def _apply_overview_alert_handoff(panel: dict[str, Any]) -> None:
    """Use the dashboard handoff; the Incident donor retains runbook actions."""
    panel["links"] = [
        {
            "title": "Open Incident Workspace (all global alerts)",
            "url": _INCIDENT_URL,
            "includeVars": False,
            "targetBlank": False,
        }
    ]
    config = panel["fieldConfig"]
    config["defaults"]["links"] = []
    for override in config["overrides"]:
        for prop in override["properties"]:
            if prop["id"] == "links":
                prop["value"] = []
            if (
                prop["id"] == "custom.cellOptions"
                and prop["value"].get("type") == "color-background"
            ):
                prop["value"]["type"] = "color-text"


def _reserve_alert_band(panels: list[dict[str, Any]], bottom: int) -> None:
    """Translate lower saved-run evidence past the alert band as one block."""
    lower = [panel for panel in panels if panel["gridPos"]["y"] >= 18]
    if not lower:
        return
    delta = max(0, bottom - min(panel["gridPos"]["y"] for panel in lower))
    while lower:
        panel = lower.pop()
        panel["gridPos"]["y"] += delta
        lower.extend(panel.get("panels", []))


def embed_global_alerts(overview: dict[str, Any], incident: dict[str, Any]) -> None:
    """Copy the global summary/full-list pair after selected-run layout builders.

    The caller rebuilds the local layout before this pass. Reserve y=19 for
    the summary and translate the lower local blocks together, preserving
    their queries, sizes and relative positions. No selected-run datasource
    participates in the global query or its Dashboard-datasource consumer.
    """
    donors = {panel["id"]: panel for panel in incident["panels"]}
    summary = deepcopy(donors[2005])
    full = deepcopy(donors[32005])
    panels = overview["panels"]
    panels[:] = [panel for panel in panels if panel["id"] not in {2005, 32005}]
    summary["gridPos"] = {"x": 0, "y": 19, "w": 24, "h": 5}
    # This existing recording rule evaluates the Incident donor expression.
    # Reuse its samples instead of recomputing the long expression on first load.
    summary["targets"][0]["expr"] = "bioetl_incident_global_alerts"
    _apply_overview_alert_handoff(summary)
    summary["description"] += (
        " Fleet alert urgency is independent of the saved run verdict. "
        "Summary shows up to two highest-priority alerts; open Incident "
        "Workspace or Browse Global Alerts for all rows."
    )
    _reserve_alert_band(panels, bottom=24)
    delta = 18 - full["gridPos"]["y"]
    full["gridPos"]["y"] = 18
    for child in full["panels"]:
        child["gridPos"]["y"] += delta
        _apply_overview_alert_handoff(child)
    full["description"] = (
        "GLOBAL / CURRENT · Expand for all fleet alerts, independently of "
        "the selected Run ID. The summary below shows up to two rows."
    )
    panels.extend([summary, full])
    panels.sort(key=lambda panel: (panel["gridPos"]["y"], panel["gridPos"]["x"]))
    overview["description"] = (
        "SELECTED RUN · Saved status, domain verdicts and identity assess only "
        "the selected Run ID. GLOBAL / CURRENT · Fleet alerts are independent "
        "of Run ID, Pipeline, Provider and Workflow, including without a selected "
        "run. Open Incident Workspace for triage. Missing saved evidence remains "
        "UNKNOWN; global alerts never overwrite the saved run verdict."
    )
    scope = next(panel for panel in panels if panel["id"] == 99)
    if scope["type"] == "text":
        scope["options"]["content"] = scope["options"]["content"].replace(
            "This page assesses that run only.",
            "Saved evidence assesses that run only; GLOBAL alerts below assess the fleet.",
        )
