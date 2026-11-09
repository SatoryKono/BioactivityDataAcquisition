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
from pathlib import Path
from urllib.parse import urlencode

import yaml

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
_RANKED_EVIDENCE_PANEL = 2010
_DQ_CONDITIONS_PANEL = 4
_DQ_EVENT_INPUTS = {
    "bioetl_runtime_alert_condition_dq_soft_threshold_15m": 'bioetl_dq_soft_threshold_exceeded_total{pipeline=~"$pipeline"}[15m]',
    "bioetl_runtime_alert_condition_dq_hard_fail_15m": 'bioetl_dq_validation_failures_total{pipeline=~"$pipeline",severity="hard_fail"}[15m]',
    "bioetl_runtime_alert_condition_dq_critical_anomaly_30m": 'bioetl_dq_anomaly_detected_total{pipeline=~"$pipeline",severity="critical"}[30m]',
    "bioetl_runtime_alert_condition_silver_validation_failures_30m": 'bioetl_silver_validation_failures_total{pipeline=~"$pipeline"}[30m]',
}
_RANKED_EVIDENCE_DEPENDENCIES = frozenset(
    {
        "bioetl_incident_ranked_runtime",
        "bioetl_incident_ranked_provider",
        "bioetl_incident_ranked_dq",
    }
)
_WORKFLOW_PANELS = frozenset({9701, 9997})
_STANDALONE_DEPENDENCIES = {
    "bioetl_overview_pipeline_run_type_universe",
    "bioetl_standalone_pipeline_universe",
    "bioetl_workflow_scope_universe",
}
_WORKFLOW_INPUT_DEPENDENCIES = {
    "bioetl_workflow_scope_input_status",
    "bioetl_workflow_scope_published_seconds",
    "bioetl_workflow_scope_status",
    "bioetl_workflow_scope_status_priority",
    "bioetl_workflow_scope_qualified_status",
}
_METRIC = re.compile(r"\bbioetl_\w+", re.ASCII)
_EVENT_RANGE = re.compile(
    r"\b(increase|rate|changes)\(\s*"
    r"(bioetl_\w+)((?:\{[^}]*\})?\s*\[[^\]]+\])\s*\)",
    re.ASCII,
)
_SCOPE_METRIC = "bioetl_runtime_pipeline_run_type_universe_scoped"
type WitnessVector = Callable[[str], list[dict[str, Any]] | None]


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
    if panel_id in _EVENT_PANELS or panel_id in {4, 220, 259, 2006}:
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

    def vector(query: str) -> list[dict[str, Any]] | None:
        parameters = {"query": substitute(query)}
        if as_of is not None:
            parameters["time"] = as_of
        payload = request("/api/v1/query", parameters)
        return _vector_result(payload)

    scope = _observed_scope(vector)
    if not scope:
        return False, evidence
    if panel_id == 2006:
        return _alert_history_available(expr, vector, request), evidence
    if panel_id in _WORKFLOW_PANELS:
        return _standalone_confirmed(
            panel_id, scope, substitute, vector, request
        ), evidence
    if panel_id in _SIGNAL_WITNESSES:
        if not _signal_metrics_available(panel_id, expr, request):
            return False, evidence
        if panel_id == _DQ_CONDITIONS_PANEL and not _dq_operands_confirmed(
            expr, vector, request
        ):
            return False, evidence
        witnesses = vector(_SIGNAL_WITNESSES[panel_id]) or []
        return _signal_witness_confirms_empty(panel_id, witnesses), evidence
    return (
        _event_families_available(expr, request)
        and _event_sample_coverage_confirmed(expr, vector),
        evidence,
    )


def _standalone_confirmed(
    panel_id: int,
    scope: list[dict[str, Any]],
    substitute: Callable[[str], str],
    vector: WitnessVector,
    request: Callable[..., Any],
) -> bool:
    # A concrete workflow selection must never be excused by standalone data.
    if substitute("$workflow") != ".*":
        return False
    dependencies = _STANDALONE_DEPENDENCIES
    if panel_id == 9701:
        dependencies = dependencies | _WORKFLOW_INPUT_DEPENDENCIES
    if not _healthy_rules(
        _response_data(request("/api/v1/rules", {})), "recording", dependencies
    ):
        return False
    selected = _scope_pairs(scope)
    standalone = 'bioetl_standalone_pipeline_universe{pipeline=~"$pipeline",run_type=~"$run_type"}'
    return bool(selected) and selected == _scope_pairs(vector(standalone) or [])


def _alert_history_available(
    expr: str, vector: WitnessVector, request: Callable[..., Any]
) -> bool:
    if expr != 'ALERTS{alertstate="firing"} or (ALERTS{alertstate="pending"} * 2)':
        return False
    expected = _expected_alert_names()
    if not expected or not _healthy_rules(
        _response_data(request("/api/v1/rules", {})), "alerting", expected
    ):
        return False
    healthy = vector('min_over_time(up{job="prometheus"}[$__range])')
    samples = vector('count_over_time(up{job="prometheus"}[$__range])')
    return (
        bool(healthy)
        and bool(samples)
        and all(float(row["value"][1]) == 1 for row in healthy)
        and all(float(row["value"][1]) >= 2 for row in samples)
    )


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
    vector: WitnessVector,
) -> list[dict[str, Any]]:
    targets = vector('up{job=~"bioetl|pushgateway|prometheus"}') or []
    if {row.get("metric", {}).get("job") for row in targets} != {
        "bioetl",
        "pushgateway",
        "prometheus",
    } or any(float(row["value"][1]) != 1 for row in targets):
        return []
    scope = 'bioetl_runtime_pipeline_run_type_universe_scoped{pipeline=~"$pipeline",run_type=~"$run_type"}'
    return vector(scope) or []


def _dq_operands_confirmed(
    expr: str, vector: WitnessVector, request: Callable[..., Any]
) -> bool:
    """Reject hidden active signals; prove absent lazy events at their raw source."""
    operands = set(_METRIC.findall(expr)) - {
        "bioetl_runtime_pipeline_run_type_universe"
    }
    if not operands or operands - _DQ_EVENT_INPUTS.keys():
        return False
    for metric in sorted(operands):
        rows = vector(f'{metric}{{pipeline=~"$pipeline"}}')
        if rows is None or any(float(row["value"][1]) != 0 for row in rows):
            return False
        if not rows:
            source = _DQ_EVENT_INPUTS[metric]
            if not _event_families_available(source, request):
                return False
            # Any raw samples with an absent derived condition require review:
            # this includes one-sample windows and rule evaluation lag.
            if vector(f"count_over_time({source})") != []:
                return False
    return True


def _signal_witness_confirms_empty(
    panel_id: int, witnesses: list[dict[str, Any]]
) -> bool:
    if panel_id in {_RANKED_EVIDENCE_PANEL, _DQ_CONDITIONS_PANEL} and any(
        float(row["value"][1]) > 0 for row in witnesses
    ):
        return False
    return bool(witnesses)


def _expected_alert_names() -> set[str]:
    rules_dir = Path(__file__).resolve().parents[4] / "grafana/prometheus-rules"
    try:
        return {
            rule["alert"]
            for path in sorted(rules_dir.glob("*.yml"))
            for group in yaml.safe_load(path.read_text(encoding="utf-8"))["groups"]
            for rule in group["rules"]
            if "alert" in rule
        }
    except (OSError, TypeError, KeyError, yaml.YAMLError):
        return set()


def _healthy_rules(data: dict[str, Any], kind: str, expected: set[str]) -> bool:
    rules = [
        rule
        for group in data.get("groups", [])
        for rule in group.get("rules", [])
        if rule.get("type") == kind
        and (kind == "alerting" or rule.get("name") in expected)
    ]
    return expected <= {rule.get("name") for rule in rules} and all(
        rule.get("health") == "ok" for rule in rules
    )


def _signal_metrics_available(
    panel_id: int, expr: str, request: Callable[..., Any]
) -> bool:
    """Require healthy recording rules or declared raw metric families."""
    metrics = set(_METRIC.findall(expr))
    if not metrics:
        return False
    raw_metrics = metrics & _RAW_SIGNAL_METRICS
    expected_rules = metrics - raw_metrics
    if panel_id == _RANKED_EVIDENCE_PANEL:
        expected_rules.update(_RANKED_EVIDENCE_DEPENDENCIES)
    if expected_rules:
        data = _response_data(request("/api/v1/rules", {}))
        if not _healthy_rules(data, "recording", expected_rules):
            return False
        if panel_id == 2005:
            alerts = _expected_alert_names()
            if not alerts or not _healthy_rules(data, "alerting", alerts):
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
        elif metric != _SCOPE_METRIC:
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


def _event_sample_coverage_confirmed(expr: str, vector: WitnessVector) -> bool:
    """A known event series needs two samples in the panel's own selector window."""
    selectors = set(_EVENT_RANGE.findall(expr))
    if not selectors or set(_METRIC.findall(expr)) - {_SCOPE_METRIC} != {
        metric for _, metric, _ in selectors
    }:
        return False
    for operation, metric, window in sorted(selectors):
        samples = vector(f"count_over_time({metric}{window})")
        if samples is None or any(float(row["value"][1]) < 2 for row in samples):
            return False
        if operation == "changes" and metric.endswith("_created"):
            resets = vector(f"changes({metric}{window})")
            if resets is None or any(float(row["value"][1]) > 0 for row in resets):
                return False
    return True


def _vector_result(payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Distinguish verified empty vectors from unsuccessful or annotated replies."""
    data = _response_data(payload)
    result = data.get("result")
    return (
        result
        if data.get("resultType") == "vector" and isinstance(result, list)
        else None
    )
