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

_EMPTY_EVENT_GUIDANCE = (
    " Empty result: UNKNOWN until producer availability, observed scope and "
    "event-family coverage are verified. Check Monitor Metrics Coverage, the "
    "selector and time window. NO OBSERVATIONS requires those witnesses; "
    "TELEMETRY MISSING requires a confirmed coverage gap. Only an actual "
    "sample can establish a measured zero."
)


def apply_event_empty_copy(panels: list[dict[str, Any]]) -> None:
    """Keep static rendering neutral; only qualify_empty can verify emptiness.

    Grafana's noValue also applies to missing cells in populated frames. It
    cannot distinguish an unavailable family from a valid empty event query.
    Do not change targets, numeric samples or the failed-run coverage guard.
    """
    for panel in panels:
        apply_event_empty_copy(panel.get("panels", []))
        if panel.get("id") not in _EVENT_PANELS | {112, 135, 8807}:
            continue
        defaults = panel.setdefault("fieldConfig", {}).setdefault("defaults", {})
        defaults["noValue"] = (
            "UNKNOWN — terminal histogram samples unavailable"
            if panel.get("id") == 239
            else "UNKNOWN"
        )
        for mapping in defaults.get("mappings", []):
            options = mapping.get("options", {})
            if (
                mapping.get("type") == "special"
                and options.get("match") in {"null", "nan", "null+nan"}
                and options.get("result", {}).get("text") == "NO OBSERVATIONS"
            ):
                options["result"]["text"] = "UNKNOWN"
        description = panel.get("description", "")
        if _EMPTY_EVENT_GUIDANCE not in description:
            panel["description"] = description + _EMPTY_EVENT_GUIDANCE


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
_RUNTIME_ERROR_RATE_PANEL = 220
_PROVIDER_CONDITIONS_PANEL = 259
_PROVIDER_EVENT_INPUTS = {
    "bioetl_runtime_alert_condition_provider_adapter_latency_high_30m": "bioetl_adapter_request_duration_seconds_bucket[30m]",
    "bioetl_runtime_alert_condition_provider_rate_limiter_wait_high_30m": "bioetl_rate_limiter_wait_seconds_bucket[30m]",
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
_CONDITION_SUM_OPERAND = re.compile(
    r'\bsum\(\s*(?:(bioetl_\w+)|\{\s*__name__\s*=~\s*"(bioetl_\w+(?:\|bioetl_\w+)*)")',
    re.ASCII,
)
_EVENT_RANGE = re.compile(
    r"\b(increase|rate|changes)\(\s*"
    r"(bioetl_\w+)((?:\{[^}]*\})?\s*\[[^\]]+\])\s*\)",
    re.ASCII,
)
_SCOPE_METRIC = "bioetl_runtime_pipeline_run_type_universe_scoped"
_RULES_ENDPOINT = "/api/v1/rules"
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
    historical_reset: bool = False,
    range_bounds: dict[str, str] | None = None,
) -> tuple[bool, list[dict[str, Any]]]:
    """Return acceptance and exact independent witnesses; fail closed on gaps."""
    if dashboard_uid != "bioetl-incident-v1" or empty_state_label(panel_id) is None:
        return False, []
    if historical_reset and not _checkpoint_generation_guard(panel_id, expr):
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

    def sample_vector(query: str) -> list[dict[str, Any]] | None:
        if range_bounds is None:
            return vector(query)
        return _matrix_samples(
            request("/api/v1/query_range", {**range_bounds, "query": substitute(query)})
        )

    scope = _observed_scope(vector)
    if not scope:
        return False, evidence
    if panel_id == 2006:
        return _alert_history_available(expr, vector, request), evidence
    if panel_id in _WORKFLOW_PANELS:
        return _workflow_scope_confirms_empty(
            panel_id, scope, request, vector, substitute
        ), evidence
    if panel_id in _SIGNAL_WITNESSES:
        return _qualify_signal_empty(panel_id, expr, request, sample_vector), evidence
    return (
        _event_families_available(expr, request)
        and _event_sample_coverage_confirmed(
            expr, sample_vector, require_reset=historical_reset
        ),
        evidence,
    )


def _workflow_scope_confirms_empty(
    panel_id: int,
    scope: list[dict[str, Any]],
    request: Callable[..., Any],
    vector: WitnessVector,
    substitute: Callable[[str], str],
) -> bool:
    if substitute("$workflow") != ".*":
        return False
    dependencies = _STANDALONE_DEPENDENCIES
    if panel_id == 9701:
        dependencies = dependencies | _WORKFLOW_INPUT_DEPENDENCIES
    if not _healthy_rules(
        _response_data(request(_RULES_ENDPOINT, {})), "recording", dependencies
    ):
        return False
    standalone = 'bioetl_standalone_pipeline_universe{pipeline=~"$pipeline",run_type=~"$run_type"}'
    selected = _scope_pairs(scope)
    return bool(selected) and selected == _scope_pairs(vector(standalone) or [])


def _qualify_signal_empty(
    panel_id: int, expr: str, request: Callable[..., Any], vector: WitnessVector
) -> bool:
    if not _signal_metrics_available(panel_id, expr, request):
        return False
    if panel_id in {_DQ_CONDITIONS_PANEL, _PROVIDER_CONDITIONS_PANEL}:
        if not _condition_operands_confirmed(panel_id, expr, vector, request):
            return False
    if panel_id == _RUNTIME_ERROR_RATE_PANEL and not _unobserved_event_input(
        'bioetl_errors_total{pipeline=~"$pipeline"}[30m]', vector, request
    ):
        return False
    if (
        panel_id == 242
        and "bioetl_runtime_alert_condition_pipeline_runs_failed_15m" in expr
        and not _unobserved_failed_blocker_input(vector, request)
    ):
        return False
    witnesses = vector(_SIGNAL_WITNESSES[panel_id]) or []
    return _signal_witness_confirms_empty(panel_id, witnesses)


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


def _signal_witness_confirms_empty(
    panel_id: int, witnesses: list[dict[str, Any]]
) -> bool:
    if panel_id == _PROVIDER_CONDITIONS_PANEL:
        # Independent operand evidence proves no latency/wait observations.
        # UNKNOWN health is retained; it is not an observed alert condition.
        return bool(witnesses) and all(
            float(row["value"][1]) in {0, 3} for row in witnesses
        )
    if panel_id in {
        _RANKED_EVIDENCE_PANEL,
        _DQ_CONDITIONS_PANEL,
    } and any(float(row["value"][1]) > 0 for row in witnesses):
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
        data = _response_data(request(_RULES_ENDPOINT, {}))
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


def _checkpoint_generation_guard(panel_id: int, expr: str) -> bool:
    guards = {
        105: ("bioetl_checkpoint_save_duration_seconds", "pipeline, operation"),
        207: ("bioetl_phase_duration_seconds", "phase, status"),
        239: ("bioetl_pipeline_duration_seconds", "stage, status, run_type"),
    }
    family, labels = guards.get(panel_id, ("", ""))
    return (
        bool(family)
        and "histogram_quantile(" in expr
        and f"unless on ({labels})" in expr
        and set(_METRIC.findall(expr))
        == {
            f"{family}_bucket",
            f"{family}_created",
        }
        and bool(re.search(r"changes\(.+?\)\s*>\s*0", expr))
    )


def _event_sample_coverage_confirmed(
    expr: str, vector: WitnessVector, *, require_reset: bool = False
) -> bool:
    """A known event series needs two samples in the panel's own selector window."""
    selectors = set(_EVENT_RANGE.findall(expr))
    if not selectors or set(_METRIC.findall(expr)) - {_SCOPE_METRIC} != {
        metric for _, metric, _ in selectors
    }:
        return False
    reset_observed = False
    for operation, metric, window in sorted(selectors):
        samples = vector(f"count_over_time({metric}{window})")
        if not _event_samples_sufficient(samples, require_reset=require_reset):
            return False
        if operation == "changes" and metric.endswith("_created"):
            resets = vector(f"changes({metric}{window})")
            if resets is None:
                return False
            reset_observed |= any(float(row["value"][1]) > 0 for row in resets)
    return reset_observed if require_reset else not reset_observed


def _event_samples_sufficient(
    samples: list[dict[str, Any]] | None, *, require_reset: bool
) -> bool:
    if samples is None or (require_reset and not samples):
        return False
    if not require_reset:
        return all(float(row["value"][1]) >= 2 for row in samples)
    # A historical creation boundary may have one sample; every distinct
    # series must subsequently have enough observations to verify its reset.
    coverage: dict[tuple, float] = {}
    for row in samples:
        key = tuple(sorted(row.get("metric", {}).items()))
        coverage[key] = max(coverage.get(key, 0), float(row["value"][1]))
    return all(count >= 2 for count in coverage.values())


def _matrix_samples(payload: Any) -> list[dict[str, Any]] | None:
    data = _response_data(payload)
    result = data.get("result")
    if data.get("resultType") != "matrix" or not isinstance(result, list):
        return None
    samples = []
    for series in result:
        if not isinstance(series, dict) or not isinstance(series.get("values"), list):
            return None
        samples.extend(
            {"metric": series.get("metric", {}), "value": value}
            for value in series["values"]
        )
    return samples


def _vector_result(payload: dict[str, Any]) -> list[dict[str, Any]] | None:
    """Distinguish verified empty vectors from unsuccessful or annotated replies."""
    data = _response_data(payload)
    result = data.get("result")
    return (
        result
        if data.get("resultType") == "vector" and isinstance(result, list)
        else None
    )


def _alert_history_available(
    expr: str, vector: WitnessVector, request: Callable[..., Any]
) -> bool:
    if expr != 'ALERTS{alertstate="firing"} or (ALERTS{alertstate="pending"} * 2)':
        return False
    expected = _expected_alert_names()
    if not expected or not _healthy_rules(
        _response_data(request(_RULES_ENDPOINT, {})), "alerting", expected
    ):
        return False
    # Probe at 30-second steps against the default 15-second self-scrape.
    # A 45-second lookback tolerates scrape jitter without excusing long gaps.
    coverage = vector(
        'count_over_time((min_over_time(up{job="prometheus"}[45s]) == 1)[$__range:30s])'
        " / scalar(count_over_time(vector(1)[$__range:30s]))"
    )
    return bool(coverage) and all(float(row["value"][1]) == 1 for row in coverage)


def _condition_operands_confirmed(
    panel_id: int, expr: str, vector: WitnessVector, request: Callable[..., Any]
) -> bool:
    """Reject hidden active signals; prove absent lazy events at their raw source."""
    operands = {
        name
        for bare, alternatives in _CONDITION_SUM_OPERAND.findall(expr)
        for name in (bare or alternatives).split("|")
    }
    is_dq = panel_id == _DQ_CONDITIONS_PANEL
    sources = _DQ_EVENT_INPUTS if is_dq else _PROVIDER_EVENT_INPUTS
    selector = '{pipeline=~"$pipeline"}' if is_dq else ""
    if not operands or operands - sources.keys():
        return False
    for metric in sorted(operands):
        rows = vector(metric + selector)
        if rows is None or any(float(row["value"][1]) != 0 for row in rows):
            return False
        if not rows and not _unobserved_event_input(sources[metric], vector, request):
            return False
    return True


def _unobserved_failed_blocker_input(
    vector: WitnessVector, request: Callable[..., Any]
) -> bool:
    source = 'bioetl_pipeline_runs_total{status="failed",run_type=~"$run_type"}[15m]'
    if not _event_families_available(source, request):
        return False
    # A complete zero is valid for a threshold query. Partial or growing
    # sources require review, including the dashboard's workflow-prefix fallback.
    scoped = source.replace("{", '{pipeline=~"$pipeline",', 1)
    direct = f"(count_over_time({scoped}) < 2 or increase({scoped}) > 0)"
    fallback = f"(count_over_time({source}) < 2 or increase({source}) > 0)"
    return (
        vector(
            f"{direct} or ({fallback} and on (pipeline) "
            'label_replace(label_replace(vector(1), "pipeline_raw", "$pipeline", "", ""), '
            '"pipeline", "$1", "pipeline_raw", "^(?:workflow_)?(.*)$"))'
        )
        == []
    )


def _unobserved_event_input(
    source: str, vector: WitnessVector, request: Callable[..., Any]
) -> bool:
    # Any raw samples with an absent derived condition require review,
    # including one-sample windows and rule evaluation lag.
    return (
        _event_families_available(source, request)
        and vector(f"count_over_time({source})") == []
    )
