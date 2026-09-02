#!/usr/bin/env python3
"""Allowlisted Grafana routes for recording-rule ``action_target`` values.

Dashboard JSON binds these maps through ``action_dashboard_uid`` plus a single
row-aware field link. Unknown future targets must stay visible as
UNSUPPORTED/UNKNOWN instead of inheriting a generic sibling URL.
"""

from __future__ import annotations

from typing import TypedDict

from scripts.ops.observability.grafana.dashboard_context_links import (
    PATH_BY_UID,
    TIME_TOKEN,
)

DQ_REASON_RULES_RUNBOOK = (
    "https://github.com/SatoryKono/BioactivityDataAcquisition/blob/main/"
    "docs/05-operations/runbooks/observability-checklist.md"
)
OPEN_PIPELINE_DIAGNOSTICS_TITLE = "Open Pipeline Diagnostics"


class ActionRoute(TypedDict):
    """One allowlisted operator handoff for a recording-rule action_target."""

    uid: str | None
    title: str
    kind: str


RUNTIME_BLOCKER_ACTION_MAP: dict[str, ActionRoute] = {
    "runtime": {
        "uid": "bioetl-runtime",
        "title": OPEN_PIPELINE_DIAGNOSTICS_TITLE,
        "kind": "dashboard",
    },
    "control_plane": {
        "uid": "bioetl-control-plane-v1",
        "title": "Open Trust",
        "kind": "dashboard",
    },
    "data_quality": {
        "uid": "bioetl-dq-v2",
        "title": "Open Data Quality",
        "kind": "dashboard",
    },
    "workflow": {
        "uid": "bioetl-runtime",
        "title": OPEN_PIPELINE_DIAGNOSTICS_TITLE,
        "kind": "dashboard",
    },
}

DQ_REASON_ACTION_MAP: dict[str, ActionRoute] = {
    "data_quality": {
        "uid": "bioetl-dq-v2",
        "title": "Open Data Quality evidence",
        "kind": "dashboard",
    },
    "verify_dq_reason_rules": {
        "uid": None,
        "title": "Open DQ reason-rules runbook",
        "kind": "runbook",
    },
}

INCIDENT_DOMAIN_ACTION_MAP: dict[str, ActionRoute] = {
    "runtime": {
        "uid": "bioetl-runtime",
        "title": OPEN_PIPELINE_DIAGNOSTICS_TITLE,
        "kind": "dashboard",
    },
    "provider": {
        "uid": "bioetl-provider-health-v2",
        "title": "Open Provider Health",
        "kind": "dashboard",
    },
    "dq": {
        "uid": "bioetl-dq-v2",
        "title": "Open Data Quality",
        "kind": "dashboard",
    },
}

ACTION_DASHBOARD_UID_BY_TARGET: dict[str, str] = {
    key: str(route["uid"])
    for key, route in {
        **RUNTIME_BLOCKER_ACTION_MAP,
        "data_quality": DQ_REASON_ACTION_MAP["data_quality"],
        **INCIDENT_DOMAIN_ACTION_MAP,
    }.items()
    if route["uid"]
}

UNSUPPORTED_ACTION_TEXT = "UNSUPPORTED"
UNKNOWN_ACTION_TEXT = "UNKNOWN"


def row_aware_dashboard_url() -> str:
    """Return a fail-closed dashboard link populated from the selected row.

    Grafana field links cannot branch on the dynamic destination UID, so the
    URL carries the union of destination selectors. Dashboards ignore selectors
    they do not declare, while Runtime/DQ receive stage=All and Provider Health
    receives an explicit provider reset plus row pipeline context.
    """
    uid = "${__data.fields.action_dashboard_uid}"
    row = "${__data.fields"
    return (
        f"/d/{uid}/{uid}?var-workflow={row}.workflow}}"
        f"&var-pipeline={row}.pipeline}}"
        f"&var-run_type={row}.run_type}}"
        f"&var-run_id={row}.run_id}}"
        "&var-stage=$__all&var-provider=unknown"
        f"&var-pipeline_context={row}.pipeline}}&{TIME_TOKEN}"
    )


def dashboard_uid_for_target(action_target: str) -> str | None:
    """Return the allowlisted UID, or None for runbook/unknown targets."""
    route = (
        RUNTIME_BLOCKER_ACTION_MAP.get(action_target)
        or DQ_REASON_ACTION_MAP.get(action_target)
        or INCIDENT_DOMAIN_ACTION_MAP.get(action_target)
    )
    if route is None:
        return None
    uid = route["uid"]
    if uid is not None and uid not in PATH_BY_UID:
        raise ValueError(f"action_target {action_target!r} maps to unknown uid {uid!r}")
    return uid


__all__ = [
    "ACTION_DASHBOARD_UID_BY_TARGET",
    "DQ_REASON_ACTION_MAP",
    "DQ_REASON_RULES_RUNBOOK",
    "INCIDENT_DOMAIN_ACTION_MAP",
    "RUNTIME_BLOCKER_ACTION_MAP",
    "UNKNOWN_ACTION_TEXT",
    "UNSUPPORTED_ACTION_TEXT",
    "ActionRoute",
    "dashboard_uid_for_target",
    "row_aware_dashboard_url",
]
