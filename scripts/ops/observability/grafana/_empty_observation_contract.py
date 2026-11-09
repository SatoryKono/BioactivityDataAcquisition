"""Evidence-backed empty states for lazy event series, never healthy zeroes.

Prometheus metadata declares a family even before a labelled child is observed.
An empty event query is therefore valid NO OBSERVATIONS only with an available
producer, an observed scope, and declared event families. Unregistered panels,
unavailable sources and missing status gauges remain review-required.
"""

from __future__ import annotations

import re
from typing import Any
from collections.abc import Callable
from urllib.parse import urlencode

_EVENT_PANELS = frozenset(
    {
        3,
        103,
        105,
        106,
        107,
        108,
        109,
        110,
        120,
        122,
        134,
        137,
        138,
        205,
        207,
        209,
        210,
        239,
        256,
        8805,
    }
)
_SIGNAL_WITNESSES = {
    4: 'bioetl_dq_current_status{pipeline=~"$pipeline"}',
    259: "bioetl_provider_current_status",
    220: 'bioetl_records_processed_total{pipeline=~"$pipeline",stage="bronze"}',
    2002: "bioetl_runtime_current_blocker_reason",
    9101: 'bioetl_runtime_current_blocker_reason_scoped{pipeline=~"$pipeline",run_type=~"$run_type"}',
    242: 'bioetl_runtime_current_blocker_reason_scoped{pipeline=~"$pipeline",run_type=~"$run_type"}',
    2003: "bioetl_provider_current_cause",
    2004: "bioetl_dq_current_reason",
    2010: "bioetl_runtime_current_blocker_reason or bioetl_provider_current_cause or bioetl_dq_current_reason",
    2005: 'up{job="prometheus"}',
    22011: "bioetl_stage_lag_seconds or bioetl_stage_backlog_records",
}
_WORKFLOW_PANELS = frozenset({9701, 9997})
_METRIC = re.compile(r"\bbioetl_[a-zA-Z0-9_]+")


def empty_state_label(panel_id: int) -> str | None:
    """A neutral rendering label; it does not itself qualify audit acceptance."""
    if panel_id == 2010:
        # The empty join exposes only a 50px Rank column, not the full table.
        return "—"
    if panel_id in _EVENT_PANELS or panel_id in {4, 220, 259}:
        return "NO OBSERVATIONS"
    if panel_id in _SIGNAL_WITNESSES:
        return "NO MATCHING SIGNALS"
    if panel_id in _WORKFLOW_PANELS:
        return "NO WORKFLOW OBSERVATIONS"
    return None


def qualify_empty(
    *,
    dashboard_uid: str,
    panel_id: int,
    expr: str,
    base_url: str,
    fetch: Callable[..., Any],
    substitute: Callable[[str], str],
    timeout: float,
) -> tuple[bool, list[dict[str, Any]]]:
    """Return acceptance and exact independent witnesses; fail closed on gaps."""
    if dashboard_uid != "bioetl-incident-v1" or empty_state_label(panel_id) is None:
        return False, []
    evidence: list[dict[str, Any]] = []

    def request(path: str, parameters: dict[str, str]) -> Any:
        url = base_url + path + "?" + urlencode(parameters)
        payload = fetch(url, timeout_seconds=timeout)
        evidence.append(
            {"mode": "empty_state_witness", "request_url": url, "response": payload}
        )
        return payload

    def vector(query: str) -> list[dict[str, Any]]:
        payload = request("/api/v1/query", {"query": substitute(query)})
        if (
            payload.get("status") != "success"
            or payload.get("warnings")
            or payload.get("infos")
        ):
            return []
        data = payload.get("data", {})
        return data.get("result", []) if data.get("resultType") == "vector" else []

    targets = vector('up{job=~"bioetl|pushgateway|prometheus"}')
    if {row.get("metric", {}).get("job") for row in targets} != {
        "bioetl",
        "pushgateway",
        "prometheus",
    }:
        return False, evidence
    if any(float(row["value"][1]) != 1 for row in targets):
        return False, evidence
    scope = 'bioetl_runtime_pipeline_run_type_universe_scoped{pipeline=~"$pipeline",run_type=~"$run_type"}'
    if not vector(scope):
        return False, evidence
    if panel_id in _WORKFLOW_PANELS:
        standalone = 'bioetl_standalone_pipeline_universe{pipeline=~"$pipeline",run_type=~"$run_type"}'
        # A concrete workflow selection must never be excused by standalone data.
        if substitute("$workflow") != ".*":
            return False, evidence
        return bool(vector(standalone)), evidence
    if panel_id in _SIGNAL_WITNESSES:
        payload = request("/api/v1/rules", {})
        rules = {
            rule.get("name"): rule
            for group in payload.get("data", {}).get("groups", [])
            for rule in group.get("rules", [])
        }
        for metric in set(_METRIC.findall(expr)):
            if metric in rules and rules[metric].get("health") != "ok":
                return False, evidence
            if metric not in rules:
                metadata = request("/api/v1/metadata", {"metric": metric})
                if not metadata.get("data", {}).get(metric):
                    return False, evidence
        return bool(vector(_SIGNAL_WITNESSES[panel_id])), evidence
    metrics = set(_METRIC.findall(expr))
    # These are sparse event panels, not a waiver for arbitrary absent gauges.
    families = set()
    for metric in metrics:
        if metric.endswith(("_bucket", "_created")):
            families.add(metric.rsplit("_", 1)[0])
        elif metric.endswith("_total"):
            families.add(metric)
        elif metric != "bioetl_runtime_pipeline_run_type_universe_scoped":
            return False, evidence
    if not families:
        return False, evidence
    for family in sorted(families):
        payload = request("/api/v1/metadata", {"metric": family})
        entries = payload.get("data", {}).get(family, [])
        if payload.get("status") != "success" or not entries:
            return False, evidence
        if any(item.get("type") not in {"counter", "histogram"} for item in entries):
            return False, evidence
    return True, evidence
