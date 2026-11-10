"""Embed Incident Workspace's global alert donor independently of saved runs."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

_INCIDENT_URL = (
    "/d/bioetl-incident-v1/5-incident-workspace"
    "?var-workflow=$__all&var-pipeline=$__all&var-run_type=$__all"
    "&var-run_id=-&viewPanel=22005&${__url_time_range}"
)


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
    summary["gridPos"] = {"x": 0, "y": 19, "w": 24, "h": 4}
    summary["links"] = [
        {
            "title": "Open Incident Workspace (all global alerts)",
            "url": _INCIDENT_URL,
            "includeVars": False,
            "targetBlank": False,
        }
    ]
    summary["description"] += (
        " Fleet alert urgency is independent of the saved run verdict. "
        "Summary shows up to two highest-priority alerts; open Incident "
        "Workspace or Browse Global Alerts for all rows."
    )
    # Provider/stage evidence currently starts at y=18. Move the complete
    # lower band past the new summary without compressing any local panel.
    lower = [panel for panel in panels if panel["gridPos"]["y"] >= 18]
    if lower:
        delta = max(0, 23 - min(panel["gridPos"]["y"] for panel in lower))
        pending = list(lower)
        while pending:
            panel = pending.pop()
            panel["gridPos"]["y"] += delta
            pending.extend(panel.get("panels", []))
    full_y = max(p["gridPos"]["y"] + p["gridPos"]["h"] for p in panels)
    old_y = full["gridPos"]["y"]
    full["gridPos"]["y"] = full_y
    for child in full["panels"]:
        child["gridPos"]["y"] += full_y - old_y
        child["links"] = deepcopy(summary["links"])
    full["description"] = (
        "GLOBAL / CURRENT · Expand for all fleet alerts, independently of "
        "the selected Run ID. The summary above shows up to two rows."
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
    scope["options"]["content"] = scope["options"]["content"].replace(
        "This page assesses that run only.",
        "Saved evidence assesses that run only; GLOBAL alerts below assess the fleet.",
    )
