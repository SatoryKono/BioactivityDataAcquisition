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
_METRIC = re.compile(r"\bbioetl_\w+", re.ASCII)


_RAW_SIGNAL_METRICS = frozenset(
    {
        "bioetl_stage_backlog_records",
        "bioetl_stage_lag_seconds",
        "bioetl_workflow_pipeline_expected",
    }
)


def _response_data(payload: Any) -> dict[str, Any]:
    if (
        not isinstance(payload, dict)
        or payload.get("status") != "success"
        or payload.get("warnings")
        or payload.get("infos")
    ):
        return {}
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


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
    as_of: str | None = None,
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
        parameters = {"query": substitute(query)}
        if as_of is not None:
            parameters["time"] = as_of
        payload = request("/api/v1/query", parameters)
        return _vector_result(payload)

    scope = _observed_scope(vector)
    if not scope:
        return False, evidence
    if panel_id in _WORKFLOW_PANELS:
        standalone = 'bioetl_standalone_pipeline_universe{pipeline=~"$pipeline",run_type=~"$run_type"}'
        # A concrete workflow selection must never be excused by standalone data.
        if substitute("$workflow") != ".*":
            return False, evidence
        selected = _scope_pairs(scope)
        return bool(selected) and selected == _scope_pairs(vector(standalone)), evidence
    if panel_id in _SIGNAL_WITNESSES:
        if not _signal_metrics_available(expr, request):
            return False, evidence
        return bool(vector(_SIGNAL_WITNESSES[panel_id])), evidence
    return _event_families_available(expr, request), evidence


def _scope_pairs(rows: list[dict[str, Any]]) -> set[tuple[str, str]]:
    pairs = set()
    for row in rows:
        labels = row.get("metric", {})
        pipeline = labels.get("pipeline")
        run_type = labels.get("run_type")
        if not pipeline or not run_type:
            return set()
        pairs.add((pipeline, run_type))
    return pairs


def _observed_scope(
    vector: Callable[[str], list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    targets = vector('up{job=~"bioetl|pushgateway|prometheus"}')
    if {row.get("metric", {}).get("job") for row in targets} != {
        "bioetl",
        "pushgateway",
        "prometheus",
    } or any(float(row["value"][1]) != 1 for row in targets):
        return []
    scope = 'bioetl_runtime_pipeline_run_type_universe_scoped{pipeline=~"$pipeline",run_type=~"$run_type"}'
    return vector(scope)


def _signal_metrics_available(expr: str, request: Callable[..., Any]) -> bool:
    """Require healthy recording rules or declared raw metric families."""
    metrics = set(_METRIC.findall(expr))
    if not metrics:
        return False
    raw_metrics = metrics & _RAW_SIGNAL_METRICS
    expected_rules = metrics - raw_metrics
    if expected_rules:
        data = _response_data(request("/api/v1/rules", {}))
        rules = [
            rule
            for group in data.get("groups", [])
            for rule in group.get("rules", [])
            if rule.get("type") == "recording" and rule.get("name") in expected_rules
        ]
        if not expected_rules <= {rule["name"] for rule in rules} or any(
            rule.get("health") != "ok" for rule in rules
        ):
            return False
    for metric in sorted(raw_metrics):
        data = _response_data(request("/api/v1/metadata", {"metric": metric}))
        if not data.get(metric):
            return False
    return True


def _event_families_available(expr: str, request: Callable[..., Any]) -> bool:
    """Accept only declared counter and histogram event families."""
    metrics = set(_METRIC.findall(expr))
    # These are sparse event panels, not a waiver for arbitrary absent gauges.
    families = set()
    for metric in metrics:
        if metric.endswith(("_bucket", "_created")):
            families.add(metric.rsplit("_", 1)[0])
        elif metric.endswith("_total"):
            families.add(metric)
        elif metric != "bioetl_runtime_pipeline_run_type_universe_scoped":
            return False
    if not families:
        return False
    for family in sorted(families):
        data = _response_data(request("/api/v1/metadata", {"metric": family}))
        entries = data.get(family, [])
        if not entries:
            return False
        if any(item.get("type") not in {"counter", "histogram"} for item in entries):
            return False
    return True


def _vector_result(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Reject annotated, unsuccessful and non-vector responses."""
    data = _response_data(payload)
    return data.get("result", []) if data.get("resultType") == "vector" else []
