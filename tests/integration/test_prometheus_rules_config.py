"""Integration tests for Prometheus alert rule configuration."""

from __future__ import annotations

from pathlib import Path
import re

import pytest
import yaml

RULES_PATH = Path("grafana/prometheus-rules/bioetl_observability.yml")
CONTROL_PLANE_CURRENT_STATUS_RULES_PATH = Path(
    "grafana/prometheus-rules/bioetl_control_plane_current_status.yml"
)
SLO_ALERT_CONTRACT_PATH = Path("configs/quality/observability_slo_alert_contract.yaml")
PROMETHEUS_CONFIG_PATH = Path("grafana/prometheus.yml")
MONITORING_COMPOSE_PATH = Path("docker-compose.monitoring.yml")
PUSHGATEWAY_RUNTIME_PATH = Path("src/bioetl/infrastructure/observability/server.py")
pytestmark = pytest.mark.integration

_PROMQL_METRIC_SELECTOR_RE = re.compile(r"([a-zA-Z_:][a-zA-Z0-9_:]*)\{([^{}]*)\}")
_PROMQL_LABEL_MATCHER_RE = re.compile(r'([a-zA-Z_]\w*)\s*(=~|=|!=|!~)\s*"')
_PROMQL_BIOETL_METRIC_TOKEN_RE = re.compile(r"\b(bioetl_[a-z0-9_]+)\b")


def _load_rules() -> dict:
    payload = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_control_plane_current_status_rules() -> dict:
    payload = yaml.safe_load(
        CONTROL_PLANE_CURRENT_STATUS_RULES_PATH.read_text(encoding="utf-8")
    )
    assert isinstance(payload, dict)
    return payload


def _load_slo_alert_contract() -> dict:
    payload = yaml.safe_load(SLO_ALERT_CONTRACT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_prometheus_config() -> dict:
    payload = yaml.safe_load(PROMETHEUS_CONFIG_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _load_monitoring_compose() -> dict:
    payload = yaml.safe_load(MONITORING_COMPOSE_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _build_rule_map(payload: dict) -> dict[str, dict]:
    rule_map: dict[str, dict] = {}
    for group in payload.get("groups", []):
        for rule in group.get("rules", []):
            alert_name = rule.get("alert")
            if isinstance(alert_name, str):
                rule_map[alert_name] = rule
    return rule_map


def _build_record_map(payload: dict) -> dict[str, dict]:
    record_map: dict[str, dict] = {}
    for group in payload.get("groups", []):
        for rule in group.get("rules", []):
            record_name = rule.get("record")
            if isinstance(record_name, str):
                record_map[record_name] = rule
    return record_map


def _recording_rules_named(payload: dict, record_name: str) -> list[dict]:
    rules: list[dict] = []
    for group in payload.get("groups", []):
        for rule in group.get("rules", []):
            if rule.get("record") == record_name:
                rules.append(rule)
    return rules


def _infer_recording_rule_labels(expr: str) -> frozenset[str]:
    match = re.search(r"\b(?:sum|max|min|avg|count)\s+by\s*\(([^)]*)\)", expr)
    if not match:
        return frozenset()
    return frozenset(
        label.strip() for label in match.group(1).split(",") if label.strip()
    )


def _extract_selector_labels(selector_body: str) -> set[str]:
    labels: set[str] = set()
    for label_name, _operator in _PROMQL_LABEL_MATCHER_RE.findall(selector_body):
        if label_name == "__name__":
            continue
        labels.add(label_name)
    return labels


def _build_metric_label_sets(payload: dict) -> dict[str, frozenset[str]]:
    from bioetl.infrastructure.observability.prometheus_metric_registries import (
        COUNTERS,
        GAUGES,
        HISTOGRAMS,
    )

    label_sets: dict[str, frozenset[str]] = {
        "up": frozenset({"job", "instance"}),
    }

    for name, metric in COUNTERS.items():
        label_sets[name] = frozenset(metric._labelnames)
    for name, metric in GAUGES.items():
        label_sets[name] = frozenset(metric._labelnames)
    for name, metric in HISTOGRAMS.items():
        base_labels = frozenset(metric._labelnames)
        label_sets[name] = base_labels
        label_sets[f"{name}_bucket"] = base_labels | {"le"}
        label_sets[f"{name}_sum"] = base_labels
        label_sets[f"{name}_count"] = base_labels

    for group in payload.get("groups", []):
        for rule in group.get("rules", []):
            record_name = rule.get("record")
            expr = rule.get("expr")
            if isinstance(record_name, str) and isinstance(expr, str):
                static_labels = frozenset(
                    str(label_name)
                    for label_name in rule.get("labels", {})
                    if isinstance(label_name, str)
                )
                label_sets[record_name] = (
                    _infer_recording_rule_labels(expr) | static_labels
                )

    return label_sets


def _collect_rule_expression_label_schema_errors(
    payload: dict,
    *,
    label_sets: dict[str, frozenset[str]],
) -> list[str]:
    errors: list[str] = []
    for group in payload.get("groups", []):
        group_name = group.get("name", "<unknown>")
        for rule in group.get("rules", []):
            rule_name = rule.get("alert") or rule.get("record") or "<unnamed>"
            expr = rule.get("expr")
            if not isinstance(expr, str):
                continue

            for metric_name, selector_body in _PROMQL_METRIC_SELECTOR_RE.findall(expr):
                error = _rule_expression_label_schema_error(
                    group_name=group_name,
                    rule_name=rule_name,
                    metric_name=metric_name,
                    selector_body=selector_body,
                    expr=expr,
                    label_sets=label_sets,
                )
                if error is not None:
                    errors.append(error)
    return errors


def _rule_expression_label_schema_error(
    *,
    group_name: object,
    rule_name: object,
    metric_name: str,
    selector_body: str,
    expr: str,
    label_sets: dict[str, frozenset[str]],
) -> str | None:
    expected_labels = label_sets.get(metric_name)
    if expected_labels is None:
        return None
    selector_labels = _extract_selector_labels(selector_body)
    unknown_labels = sorted(selector_labels - expected_labels)
    if not unknown_labels:
        return None
    return (
        f"group={group_name} rule={rule_name} metric={metric_name} "
        f"selector_labels={unknown_labels} allowed={sorted(expected_labels)} "
        f"expr={expr}"
    )


def _unknown_bioetl_metrics_for_expr(
    expr: str,
    *,
    label_sets: dict[str, frozenset[str]],
) -> list[str]:
    """Return BioETL metric tokens not declared in registries or recording rules."""
    unknown: set[str] = set()
    for metric_name in _PROMQL_BIOETL_METRIC_TOKEN_RE.findall(expr):
        if metric_name in label_sets:
            continue
        base_name = re.sub(r"(_total|_bucket|_sum|_count|_created)$", "", metric_name)
        if base_name not in label_sets:
            unknown.add(metric_name)
    return sorted(unknown)


def _iter_contract_alerts(contract: dict) -> list[tuple[str, dict, set[str]]]:
    contracts = contract.get("slo_contracts")
    assert isinstance(contracts, dict), "SLO alert contract must define contracts"
    alerts: list[tuple[str, dict, set[str]]] = []
    for slo_name, slo in contracts.items():
        assert isinstance(slo, dict), f"{slo_name} SLO entry must be a mapping"
        metrics = slo.get("metrics")
        assert isinstance(metrics, list), f"{slo_name} must declare metrics"
        assert metrics, f"{slo_name} must declare at least one source metric"
        metric_set = {metric for metric in metrics if isinstance(metric, str)}
        assert len(metric_set) == len(metrics), f"{slo_name} metrics must be strings"
        raw_alerts = slo.get("alerts")
        assert isinstance(raw_alerts, list), f"{slo_name} must declare alerts"
        assert raw_alerts, f"{slo_name} must declare at least one alert"
        for alert in raw_alerts:
            assert isinstance(alert, dict), f"{slo_name} alert entry invalid"
            alert_name = alert.get("name")
            assert isinstance(alert_name, str), f"{slo_name} alert name missing"
            alerts.append((slo_name, alert, metric_set))
    return alerts


def _classify_quarantine_rate(
    *, bronze_records: int, quarantine_rate: float
) -> str | None:
    """Return expected alert severity for quarantine-rate thresholds."""
    if bronze_records < 20 or quarantine_rate <= 0.05:
        return None
    if quarantine_rate <= 0.2:
        return "warning"
    return "critical"


def _classify_freshness(seconds: int) -> str | None:
    """Return expected alert severity for freshness-lag thresholds."""
    if seconds <= 86400:
        return None
    if seconds <= 259200:
        return "warning"
    return "critical"


def _classify_retry_exhaustions(exhaustions_per_hour: int) -> str | None:
    """Return expected alert severity for retry-exhaustion thresholds."""
    if exhaustions_per_hour <= 0:
        return None
    if exhaustions_per_hour < 3:
        return "warning"
    return "critical"


_TUNED_ALERT_EXPECTATIONS: dict[str, dict[str, object]] = {
    "BioETLMetricsEndpointUnavailable": {
        "severity": "critical",
        "for": "2m",
        "fragments": ['up{job="bioetl"}', "== 0"],
    },
    "BioETLMetricsEndpointScrapeMissing": {
        "severity": "critical",
        "for": "1m",
        "fragments": ['up{job="bioetl"}', "absent_over_time"],
    },
    "BioETLPrometheusUnavailable": {
        "severity": "critical",
        "for": "2m",
        "fragments": ['up{job="prometheus"}', "== 0"],
    },
    "BioETLGrafanaUnavailable": {
        "severity": "critical",
        "for": "2m",
        "fragments": ['up{job="grafana"}', "== 0"],
    },
    "BioETLPushgatewayUnavailable": {
        "severity": "warning",
        "for": "5m",
        "fragments": ['up{job="pushgateway"}', "== 0"],
    },
    "BioETLNoRecordsProcessed": {
        "severity": "warning",
        "for": "10m",
        "fragments": [
            "bioetl_pipeline_runs_total",
            "bioetl_records_processed_total",
            "unless on (pipeline, run_type)",
            "[30m]",
        ],
    },
    "BioETLRuntimeErrorRateHigh": {
        "severity": "warning",
        "for": "10m",
        "fragments": [
            "bioetl_errors_total",
            'stage="bronze"',
            "bioetl_records_processed_total",
            "clamp_min",
            "> 0.05",
            ">= 20",
            "[30m]",
        ],
    },
    "BioETLRecordFlowInvariantViolated": {
        "severity": "critical",
        "for": "5m",
        "fragments": [
            "bioetl_record_flow_invariants_total",
            'status="violated"',
            "[15m]",
            "> 0",
        ],
    },
    "BioETLIngestionThroughputDegraded": {
        "severity": "warning",
        "for": "1m",
        "fragments": [
            "bioetl_stage_backlog_records",
            'stage="ingestion"',
            "bioetl_stage_lag_seconds",
            ">= 300",
            "[15m]",
        ],
    },
    "BioETLStageBacklogActive": {
        "severity": "warning",
        "for": "5m",
        "fragments": [
            "bioetl_stage_backlog_records",
            "max_over_time",
            "[15m]",
            "> 0",
        ],
    },
    "BioETLStageLagHigh": {
        "severity": "warning",
        "for": "5m",
        "fragments": [
            "bioetl_stage_lag_seconds",
            "max_over_time",
            "[15m]",
            ">= 300",
        ],
    },
    "BioETLMemoryPressureActive": {
        "severity": "warning",
        "for": "10m",
        "fragments": [
            "bioetl_memory_pressure_state",
            "max_over_time",
            "[15m]",
            "> 0",
        ],
    },
    "BioETLDQQuarantineRateHigh": {
        "severity": "warning",
        "for": "10m",
        "fragments": ["> 0.05", "<= 0.2", ">= 20", "[30m]"],
    },
    "BioETLDQQuarantineRateCritical": {
        "severity": "critical",
        "for": "5m",
        "fragments": ["> 0.2", ">= 20", "[15m]"],
    },
    "BioETLGoldValidationFailuresCritical": {
        "severity": "critical",
        "for": "2m",
        "fragments": ['stage="gold"', 'severity="hard_fail"', "[15m]", "> 0"],
    },
    "BioETLDataFreshnessLagHigh": {
        "severity": "warning",
        "for": "15m",
        "fragments": [
            "clamp_min(time() - max by (pipeline, entity) (bioetl_data_freshness_seconds), 0)",
            "> 86400",
            "<= 259200",
        ],
    },
    "BioETLDataFreshnessLagCritical": {
        "severity": "critical",
        "for": "15m",
        "fragments": [
            "clamp_min(time() - max by (pipeline, entity) (bioetl_data_freshness_seconds), 0)",
            "> 259200",
        ],
    },
    "BioETLPipelinePreflightDataSourceFailed": {
        "severity": "critical",
        "for": "2m",
        "fragments": [
            "bioetl_pipeline_health_check_passed",
            "bioetl_pipeline_runs_total",
            'component="data_source"',
            "unless on (pipeline)",
            "[15m]",
            "== 0",
        ],
    },
    "BioETLPipelineInfrastructureValidationFailed": {
        "severity": "critical",
        "for": "2m",
        "fragments": [
            "bioetl_infrastructure_validated",
            "bioetl_pipeline_runs_total",
            "unless on (pipeline)",
            "[15m]",
            "< 1",
        ],
    },
    "BioETLPipelineRunFailed": {
        "severity": "critical",
        "for": "1m",
        "fragments": ["bioetl_pipeline_runs_total", 'status="failed"', "[15m]", "> 0"],
    },
    "BioETLProviderHealthCheckFailuresDetected": {
        "severity": "warning",
        "for": "2m",
        "fragments": ["bioetl_health_check_failures_total", "[10m]", "> 0"],
    },
    "BioETLProviderFailureRateHigh": {
        "severity": "warning",
        "for": "5m",
        "fragments": [
            "bioetl_provider_health_check_failures_15m",
            "bioetl_provider_health_check_total_15m",
            "> 0.2",
        ],
    },
    "BioETLSilverFilterRejectAccountingMismatch": {
        "severity": "warning",
        "for": "5m",
        "fragments": [
            "bioetl_silver_filter_reject_total_mismatch_15m",
            "> 0",
        ],
    },
    "BioETLProviderRetriesExhausted": {
        "severity": "warning",
        "for": "5m",
        "fragments": ["> 0", "< 3", "[1h]"],
    },
    "BioETLProviderRetriesExhaustedPersistent": {
        "severity": "critical",
        "for": "10m",
        "fragments": [">= 3", "[1h]"],
    },
    "BioETLCircuitBreakerStuckOpen": {
        "severity": "warning",
        "for": "10m",
        "fragments": ["bioetl_circuit_breaker_state", "max_over_time", "[15m]", ">= 2"],
    },
    "BioETLProviderAdapterLatencyHigh": {
        "severity": "warning",
        "for": "15m",
        "fragments": [
            "bioetl_adapter_request_duration_seconds_bucket",
            "histogram_quantile",
            "[30m]",
            "> 5",
        ],
    },
    "BioETLProviderHttpErrorRateHigh": {
        "severity": "warning",
        "for": "10m",
        "fragments": [
            "bioetl_http_request_errors_total",
            "bioetl_http_request_duration_seconds_count",
            "clamp_min",
            "[15m]",
            "> 0.1",
        ],
    },
    "BioETLProviderRateLimiterWaitHigh": {
        "severity": "warning",
        "for": "10m",
        "fragments": [
            "bioetl_rate_limiter_wait_seconds_bucket",
            "histogram_quantile",
            "[30m]",
            "> 1",
        ],
    },
    "BioETLProviderRateLimiterTokensDepleted": {
        "severity": "warning",
        "for": "10m",
        "fragments": [
            "bioetl_rate_limiter_tokens_available",
            "min_over_time",
            "[15m]",
            "< 1",
        ],
    },
    "BioETLCheckpointLoadFailed": {
        "severity": "warning",
        "for": "5m",
        "fragments": [
            "bioetl_checkpoint_load_events_total",
            'status="failed"',
            "[15m]",
            "> 0",
        ],
    },
    "BioETLCheckpointSaveFailed": {
        "severity": "warning",
        "for": "5m",
        "fragments": [
            "bioetl_checkpoint_save_events_total",
            'status="failed"',
            "[15m]",
            "> 0",
        ],
    },
    "BioETLCheckpointOperatorFailed": {
        "severity": "warning",
        "for": "5m",
        "fragments": [
            "bioetl_checkpoint_operator_operations_total",
            'status="failed"',
            "[15m]",
            "> 0",
        ],
    },
    "BioETLCheckpointSaveLatencyHigh": {
        "severity": "warning",
        "for": "15m",
        "fragments": [
            "bioetl_checkpoint_save_duration_seconds_bucket",
            "histogram_quantile",
            "[30m]",
            "> 1",
        ],
    },
    "BioETLCheckpointOperatorLatencyHigh": {
        "severity": "warning",
        "for": "15m",
        "fragments": [
            "bioetl_checkpoint_operator_duration_seconds_bucket",
            "histogram_quantile",
            "[30m]",
            "> 1",
        ],
    },
    "BioETLReplayNotReconstructable": {
        "severity": "critical",
        "for": "5m",
        "fragments": [
            "bioetl_replay_reconstructability_events_total",
            'status="not_reconstructable"',
            "[30m]",
            "> 0",
        ],
    },
    "BioETLReplayLagHigh": {
        "severity": "warning",
        "for": "15m",
        "fragments": [
            "bioetl_runtime_alert_condition_replay_lag_high_15m",
            "> 0",
        ],
    },
    "BioETLReplayDriftDetected": {
        "severity": "critical",
        "for": "5m",
        "fragments": [
            "bioetl_runtime_alert_condition_replay_drift_detected_30m",
            "> 0",
        ],
    },
    "BioETLControlPlaneReadFailureRate": {
        "severity": "warning",
        "for": "15m",
        "fragments": [
            "bioetl_control_plane_reads_total",
            "increase",
            "clamp_min",
            "[30m]",
            'status="failed"',
            "store",
            "operation",
        ],
    },
}


def _assert_tuned_alert_expectations(rule_map: dict[str, dict]) -> None:
    for alert_name, expectation in _TUNED_ALERT_EXPECTATIONS.items():
        rule = rule_map[alert_name]
        expr = rule.get("expr", "")
        assert rule.get("labels", {}).get("severity") == expectation["severity"]
        assert rule.get("for") == expectation["for"]
        for fragment in expectation["fragments"]:
            assert fragment in expr, (
                f"{alert_name} expression missing expected fragment: {fragment}"
            )


def test_rules_file_contains_control_plane_traceability_group() -> None:
    payload = _load_rules()
    group_names = [group.get("name") for group in payload.get("groups", [])]
    assert "bioetl_runtime_dashboard_recording" in group_names
    assert "bioetl_monitoring_stack_observability" in group_names
    assert "bioetl_pipeline_runtime_observability" in group_names
    assert "bioetl_control_plane_traceability_observability" in group_names
    assert "bioetl_dq_observability" in group_names
    assert "bioetl_provider_health_observability" in group_names
    assert "bioetl_chembl_assay_observability" not in group_names


def test_monitoring_stack_scrape_jobs_and_grafana_metrics_are_enabled() -> None:
    prometheus_config = _load_prometheus_config()
    compose = _load_monitoring_compose()

    scrape_jobs = {
        job.get("job_name")
        for job in prometheus_config.get("scrape_configs", [])
        if isinstance(job, dict)
    }
    assert {"bioetl", "prometheus", "grafana", "pushgateway"} <= scrape_jobs

    grafana_service = compose.get("services", {}).get("grafana", {})
    environment = grafana_service.get("environment", [])
    assert "GF_METRICS_ENABLED=true" in environment, (
        "Grafana metrics must be enabled so the monitoring stack can self-monitor."
    )


def test_prometheus_config_loads_repo_rule_directory() -> None:
    prometheus_config = _load_prometheus_config()
    rule_files = prometheus_config.get("rule_files", [])

    assert "/etc/prometheus/rules/*.yml" in rule_files


def test_pushgateway_default_target_has_bounded_replace_and_cleanup_lifecycle() -> None:
    """Default Pushgateway must be backed by bounded replace/delete semantics."""
    prometheus_config = _load_prometheus_config()
    compose = _load_monitoring_compose()
    server_source = PUSHGATEWAY_RUNTIME_PATH.read_text(encoding="utf-8")

    pushgateway_jobs = [
        job
        for job in prometheus_config.get("scrape_configs", [])
        if isinstance(job, dict) and job.get("job_name") == "pushgateway"
    ]
    assert pushgateway_jobs, "Default Prometheus config must scrape Pushgateway."
    assert "pushgateway" in compose.get("services", {}), (
        "Default monitoring compose stack must provision the Pushgateway service."
    )
    assert '_PUSHGATEWAY_GROUPING_LABELS = ("pipeline", "run_type")' in server_source
    assert "pushadd_to_gateway" not in server_source, (
        "Pushgateway publication must use replace-style push_to_gateway, not "
        "additive pushadd_to_gateway."
    )
    assert "push_to_gateway(" in server_source
    assert "delete_metrics_from_gateway" in server_source
    assert "delete_from_gateway(" in server_source


def test_slo_alert_contract_matches_shipped_prometheus_rules() -> None:
    """Every contracted SLO alert must match shipped rule metadata and metrics."""
    rules = _load_rules()
    contract = _load_slo_alert_contract()
    rule_map = _build_rule_map(rules)
    contracted_alerts = _iter_contract_alerts(contract)

    for slo_name, alert_contract, source_metrics in contracted_alerts:
        alert_name = alert_contract["name"]
        assert alert_name in rule_map, (
            f"{slo_name} references missing alert {alert_name}"
        )
        rule = rule_map[alert_name]
        expr = rule.get("expr", "")
        labels = rule.get("labels", {})
        annotations = rule.get("annotations", {})
        assert isinstance(expr, str)
        assert labels.get("severity") == alert_contract["severity"]
        assert rule.get("for") == alert_contract["for"]
        assert annotations.get("runbook") == alert_contract["runbook"]
        assert any(metric in expr for metric in source_metrics), (
            f"{alert_name} must reference at least one {slo_name} source metric"
        )


def test_all_shipped_alerts_are_bound_to_an_slo_contract() -> None:
    """Avoid orphan alerts that are not tied to an operational objective."""
    rules = _load_rules()
    contract = _load_slo_alert_contract()
    rule_map = _build_rule_map(rules)
    contracted_alert_names = {
        alert["name"] for _, alert, _ in _iter_contract_alerts(contract)
    }

    orphan_alerts = sorted(set(rule_map) - contracted_alert_names)
    assert not orphan_alerts, f"Alerts missing SLO contract binding: {orphan_alerts}"


def test_runtime_dashboard_recording_rules_exist_and_reference_source_metrics() -> None:
    payload = _load_rules()
    record_map = _build_record_map(payload)

    expected = {
        "bioetl_runtime_alert_condition_pipeline_preflight_failed_15m": "bioetl_pipeline_health_check_passed",
        "bioetl_runtime_alert_condition_pipeline_infrastructure_failed_15m": "bioetl_infrastructure_validated",
        "bioetl_runtime_alert_condition_pipeline_runs_failed_15m": "bioetl_pipeline_runs_total",
        "bioetl_runtime_alert_condition_runtime_error_rate_high_30m": "bioetl_errors_total",
        "bioetl_runtime_alert_condition_record_flow_invariant_violated_15m": "bioetl_record_flow_invariants_total",
        "bioetl_runtime_alert_condition_ingestion_throughput_degraded_15m": "bioetl_stage_backlog_records",
        "bioetl_runtime_alert_condition_stage_backlog_active_15m": "bioetl_stage_backlog_records",
        "bioetl_runtime_alert_condition_stage_lag_high_15m": "bioetl_stage_lag_seconds",
        "bioetl_runtime_alert_condition_dq_soft_threshold_15m": "bioetl_dq_soft_threshold_exceeded",
        "bioetl_runtime_alert_condition_dq_hard_fail_15m": "bioetl_dq_validation_failures_total",
        "bioetl_runtime_alert_condition_dq_critical_anomaly_30m": "bioetl_dq_anomaly_detected",
        "bioetl_runtime_alert_condition_silver_validation_failures_30m": "bioetl_silver_validation_failures_total",
        "bioetl_runtime_alert_condition_manifest_write_failed_15m": "bioetl_control_plane_manifest_writes_total",
        "bioetl_runtime_alert_condition_ledger_append_failed_15m": "bioetl_control_plane_ledger_appends_total",
        "bioetl_runtime_alert_condition_checkpoint_incompatible_30m": "bioetl_checkpoint_compatibility_events_total",
        "bioetl_runtime_alert_condition_replay_lag_high_15m": "bioetl_replay_lag_seconds",
        "bioetl_runtime_alert_condition_replay_drift_detected_30m": "bioetl_replay_drift_events_total",
        "bioetl_runtime_alert_condition_lineage_refs_missing_15m": "bioetl_lineage_refs_missing_total",
        "bioetl_provider_health_check_provider_universe_15m": "bioetl_health_check_success_total",
        "bioetl_provider_health_check_success_15m": "bioetl_health_check_success_total",
        "bioetl_provider_health_check_degraded_15m": "bioetl_health_check_degraded_total",
        "bioetl_provider_health_check_failures_15m": "bioetl_health_check_failures_total",
        "bioetl_provider_health_check_total_15m": "bioetl_provider_health_check_success_15m",
        "bioetl_runtime_alert_condition_provider_failure_rate_high_15m": "bioetl_provider_health_check_failures_15m",
        "bioetl_runtime_alert_condition_provider_retries_exhausted_1h": "bioetl_data_source_retry_exhausted_total",
        "bioetl_silver_filter_rejects_stage_total_15m": "bioetl_records_processed_total",
        "bioetl_silver_filter_rejections_breakdown_total_15m": "bioetl_silver_filter_rejections_total",
        "bioetl_silver_filter_reject_total_mismatch_15m": "bioetl_silver_filter_rejects_stage_total_15m",
    }

    missing = [name for name in expected if name not in record_map]
    assert not missing, f"Missing expected recording rules: {missing}"

    for record_name, source_metric in expected.items():
        expr = record_map[record_name].get("expr", "")
        assert source_metric in expr, (
            f"{record_name} must reference {source_metric} to avoid semantic drift"
        )


def test_control_plane_current_status_recording_rules_exist_and_reference_source_metrics() -> (
    None
):
    payload = _load_control_plane_current_status_rules()
    record_map = _build_record_map(payload)

    expected = {
        "bioetl_control_plane_run_type_universe": "bioetl_control_plane_manifest_writes_total",
        "bioetl_replay_safety_blockers_15m": "bioetl_replay_drift_events_total",
        "bioetl_manifest_ledger_failures_15m": "bioetl_control_plane_ledger_appends_total",
        "bioetl_control_plane_telemetry_missing_5m": "bioetl_control_plane_manifest_writes_total",
        "bioetl_terminal_events_15m": "bioetl_control_plane_terminal_events_total",
    }

    missing = [name for name in expected if name not in record_map]
    assert not missing, f"Missing expected control-plane recording rules: {missing}"

    for record_name, source_metric in expected.items():
        expr = record_map[record_name].get("expr", "")
        assert source_metric in expr, (
            f"{record_name} must reference {source_metric} to avoid semantic drift"
        )


def test_canonical_current_status_recording_rules_exist() -> None:
    """Dashboard first screens must consume canonical current-status records."""
    payload = _load_rules()
    record_map = _build_record_map(payload)

    expected = {
        "bioetl_runtime_current_activity_15m": "bioetl_pipeline_runs_total",
        "bioetl_runtime_current_failure_signals_15m": "bioetl_runtime_alert_condition_pipeline_runs_failed_15m",
        "bioetl_runtime_current_degraded_signals_15m": "bioetl_runtime_alert_condition_no_terminal_run_30m",
        "bioetl_runtime_current_status": "bioetl_runtime_current_failure_signals_15m",
        "bioetl_provider_current_status": "bioetl_provider_health_status",
        "bioetl_provider_current_cause": "bioetl_provider_health_status",
        "bioetl_dq_current_activity_15m": "bioetl_records_processed_total",
        "bioetl_dq_current_failure_signals_15m": "bioetl_runtime_alert_condition_dq_hard_fail_15m",
        "bioetl_dq_current_degraded_signals_15m": "bioetl_runtime_alert_condition_dq_soft_threshold_15m",
        "bioetl_dq_current_status": "bioetl_dq_current_failure_signals_15m",
        "bioetl_dq_current_reason": "bioetl_runtime_alert_condition_dq_hard_fail_15m",
    }

    missing = [name for name in expected if name not in record_map]
    assert not missing, f"Missing canonical current-status records: {missing}"

    for record_name, expected_fragment in expected.items():
        expressions = [
            str(rule.get("expr", ""))
            for rule in _recording_rules_named(payload, record_name)
        ]
        assert any(expected_fragment in expr for expr in expressions), (
            f"{record_name} must reference {expected_fragment}"
        )


def test_canonical_current_status_rules_do_not_use_grafana_range_or_zero_fallback() -> (
    None
):
    """Current status must not be calculated from selected range evidence."""
    payload = _load_rules()
    record_map = _build_record_map(payload)

    current_status_records = (
        "bioetl_runtime_current_status",
        "bioetl_provider_current_status",
        "bioetl_dq_current_status",
    )
    for record_name in current_status_records:
        expr = record_map[record_name].get("expr", "")
        assert "$__range" not in expr
        assert "or vector(0)" not in expr


def test_canonical_reason_records_expose_operator_routing_labels() -> None:
    payload = _load_rules()

    reason_expectations = {
        "bioetl_runtime_current_blocker_reason": {
            "reason",
            "severity",
            "action_target",
        },
        "bioetl_provider_current_cause": {"cause", "severity"},
        "bioetl_dq_current_reason": {"reason", "severity", "action_target"},
    }

    for record_name, expected_labels in reason_expectations.items():
        rules = _recording_rules_named(payload, record_name)
        assert rules, f"Missing reason record {record_name}"
        for rule in rules:
            labels = rule.get("labels", {})
            assert expected_labels <= set(labels), (
                f"{record_name} must expose {sorted(expected_labels)} labels"
            )


def test_runtime_pipeline_level_blocker_reasons_are_projected_to_run_type() -> None:
    """Pipeline-level runtime blockers must stay visible after dashboard run_type filtering."""
    payload = _load_rules()
    rules = _recording_rules_named(payload, "bioetl_runtime_current_blocker_reason")

    expectations = {
        "preflight_failed": "bioetl_runtime_alert_condition_pipeline_preflight_failed_15m",
        "infrastructure_failed": "bioetl_runtime_alert_condition_pipeline_infrastructure_failed_15m",
    }
    seen_reasons: set[str] = set()
    for rule in rules:
        labels = rule.get("labels", {})
        reason = labels.get("reason")
        if reason not in expectations:
            continue
        seen_reasons.add(reason)
        expr = str(rule.get("expr", ""))
        assert expectations[reason] in expr
        assert "* on (pipeline) group_left(run_type)" in expr
        assert "bioetl_runtime_current_activity_15m" in expr

    assert seen_reasons == set(expectations)


def test_provider_current_status_preserves_provider_health_status_mapping() -> None:
    payload = _load_rules()
    record_map = _build_record_map(payload)
    expr = record_map["bioetl_provider_current_status"].get("expr", "")

    assert "bioetl_provider_health_status == bool 0" in expr
    assert "* 2" in expr
    assert "bioetl_provider_health_status == bool 1" in expr
    assert "bioetl_provider_health_status == bool 2" in expr
    assert "* 0" in expr
    assert "max by (provider)" in expr
    assert "bioetl_provider_health_check_provider_universe_15m * 0" in expr
    assert "/" in expr
    assert " or " in expr


def test_provider_current_status_fails_closed_on_missing_raw_status_series() -> None:
    payload = _load_rules()
    record_map = _build_record_map(payload)
    expr = record_map["bioetl_provider_current_status"].get("expr", "")

    assert "bioetl_provider_health_check_provider_universe_15m" in expr
    assert "(bioetl_provider_health_check_provider_universe_15m * 0)" in expr
    assert "bioetl_provider_health_status" in expr


def test_dq_current_status_splits_hard_failures_from_degraded_warnings() -> None:
    payload = _load_rules()
    record_map = _build_record_map(payload)

    failure_expr = record_map["bioetl_dq_current_failure_signals_15m"].get("expr", "")
    degraded_expr = record_map["bioetl_dq_current_degraded_signals_15m"].get("expr", "")
    status_expr = record_map["bioetl_dq_current_status"].get("expr", "")

    assert "bioetl_runtime_alert_condition_dq_hard_fail_15m" in failure_expr
    assert "bioetl_runtime_alert_condition_dq_critical_anomaly_30m" in failure_expr
    assert "bioetl_runtime_alert_condition_dq_soft_threshold_15m" in degraded_expr
    assert "* 2" in status_expr
    assert "* 0" in status_expr


def test_rule_expressions_use_real_metric_label_schemas() -> None:
    """Repo-backed alert/record expressions must only use real metric labels."""
    payload = _load_rules()
    label_sets = _build_metric_label_sets(payload)
    errors = _collect_rule_expression_label_schema_errors(
        payload,
        label_sets=label_sets,
    )

    assert not errors, (
        "Prometheus rules use selectors with nonexistent labels:\n" + "\n".join(errors)
    )


def test_rule_expressions_reference_declared_metrics_or_recording_rules() -> None:
    """Every BioETL metric token in rules must be declared by registry or rules."""
    payload = _load_rules()
    label_sets = _build_metric_label_sets(payload)
    errors: list[str] = []

    for group in payload.get("groups", []):
        group_name = group.get("name", "<unknown>")
        for rule in group.get("rules", []):
            rule_name = rule.get("alert") or rule.get("record") or "<unnamed>"
            expr = rule.get("expr")
            if not isinstance(expr, str):
                continue
            unknown_metrics = _unknown_bioetl_metrics_for_expr(
                expr,
                label_sets=label_sets,
            )
            if unknown_metrics:
                errors.append(
                    f"group={group_name} rule={rule_name} "
                    f"unknown_metrics={unknown_metrics} expr={expr}"
                )

    assert not errors, (
        "Prometheus rules reference undeclared metric names:\n" + "\n".join(errors)
    )


def test_pipeline_health_rules_fail_closed_on_absent_expected_series() -> None:
    """Pipeline health rules must detect observed runs with missing health gauges."""
    payload = _load_rules()
    record_map = _build_record_map(payload)
    rule_map = _build_rule_map(payload)

    expectations = {
        "bioetl_runtime_alert_condition_pipeline_preflight_failed_15m": (
            "bioetl_pipeline_health_check_passed",
            'component="data_source"',
        ),
        "bioetl_runtime_alert_condition_pipeline_infrastructure_failed_15m": (
            "bioetl_infrastructure_validated",
            None,
        ),
        "BioETLPipelinePreflightDataSourceFailed": (
            "bioetl_pipeline_health_check_passed",
            'component="data_source"',
        ),
        "BioETLPipelineInfrastructureValidationFailed": (
            "bioetl_infrastructure_validated",
            None,
        ),
    }

    for rule_name, (health_metric, component_selector) in expectations.items():
        rule = record_map.get(rule_name) or rule_map.get(rule_name)
        assert rule is not None, f"Missing rule {rule_name}"
        expr = rule.get("expr", "")
        assert "bioetl_pipeline_runs_total" in expr
        assert "unless on (pipeline)" in expr
        assert health_metric in expr
        if component_selector is not None:
            assert component_selector in expr


def test_provider_failure_rate_rules_are_sparse_counter_safe() -> None:
    """Provider failure-rate rules must not add sparse outcome counters directly."""
    payload = _load_rules()
    record_map = _build_record_map(payload)
    rule_map = _build_rule_map(payload)
    rules = [
        record_map["bioetl_runtime_alert_condition_provider_failure_rate_high_15m"],
        rule_map["BioETLProviderFailureRateHigh"],
    ]

    for rule in rules:
        expr = rule.get("expr", "")
        assert "bioetl_provider_health_check_failures_15m" in expr
        assert "bioetl_provider_health_check_total_15m" in expr
        assert "clamp_min" in expr
        assert (
            "increase(bioetl_health_check_success_total[15m]) + increase(" not in expr
        )

    record_map = _build_record_map(payload)
    for record_name in (
        "bioetl_provider_health_check_success_15m",
        "bioetl_provider_health_check_degraded_15m",
        "bioetl_provider_health_check_failures_15m",
    ):
        expr = record_map[record_name].get("expr", "")
        assert "bioetl_provider_health_check_provider_universe_15m * 0" in expr
        assert " or " in expr


def test_silver_filter_reject_accounting_has_reconciliation_rule_and_alert() -> None:
    """Filtered-out stage totals and bounded breakdown totals need drift detection."""
    payload = _load_rules()
    record_map = _build_record_map(payload)
    rule_map = _build_rule_map(payload)

    assert "bioetl_silver_filter_rejects_stage_total_15m" in record_map
    assert "bioetl_silver_filter_rejections_breakdown_total_15m" in record_map
    mismatch_rule = record_map["bioetl_silver_filter_reject_total_mismatch_15m"]
    mismatch_expr = mismatch_rule.get("expr", "")
    assert "bioetl_silver_filter_rejects_stage_total_15m" in mismatch_expr
    assert "bioetl_silver_filter_rejections_breakdown_total_15m" in mismatch_expr
    assert "abs(" in mismatch_expr
    assert "> bool 0" in mismatch_expr

    alert = rule_map["BioETLSilverFilterRejectAccountingMismatch"]
    assert "bioetl_silver_filter_reject_total_mismatch_15m" in alert.get("expr", "")
    assert alert.get("labels", {}).get("severity") == "warning"


def test_runtime_and_provider_rules_are_fleet_wide_not_chembl_specific() -> None:
    payload = _load_rules()
    rule_map = _build_rule_map(payload)
    chembl_specific = [
        alert_name
        for alert_name in rule_map
        if isinstance(alert_name, str) and alert_name.startswith("BioETLChembl")
    ]
    assert not chembl_specific, (
        "Alert rules should be fleet-wide and must not ship BioETLChembl-specific packs: "
        f"{chembl_specific}"
    )


def test_monitoring_stack_alerts_reference_up_metric_and_checklist_runbook() -> None:
    payload = _load_rules()
    rule_map = _build_rule_map(payload)

    expected = {
        "BioETLMetricsEndpointUnavailable": "2m",
        "BioETLMetricsEndpointScrapeMissing": "1m",
        "BioETLPrometheusUnavailable": "2m",
        "BioETLGrafanaUnavailable": "2m",
        "BioETLPushgatewayUnavailable": "5m",
    }

    for alert_name, expected_for in expected.items():
        rule = rule_map[alert_name]
        expr = rule.get("expr", "")
        annotations = rule.get("annotations", {})
        assert "up" in expr
        assert rule.get("for") == expected_for
        assert annotations.get("runbook") == (
            "docs/05-operations/runbooks/observability-checklist.md"
        )


def test_pipeline_runtime_alerts_reference_expected_metrics() -> None:
    payload = _load_rules()
    rule_map = _build_rule_map(payload)

    expected = {
        "BioETLPipelinePreflightDataSourceFailed": (
            "bioetl_pipeline_health_check_passed",
            "docs/05-operations/runbooks/pipeline-failure-critical.md",
        ),
        "BioETLPipelineInfrastructureValidationFailed": (
            "bioetl_infrastructure_validated",
            "docs/05-operations/runbooks/pipeline-failure-critical.md",
        ),
        "BioETLPipelineRunFailed": (
            "bioetl_pipeline_runs_total",
            "docs/05-operations/runbooks/pipeline-failure-critical.md",
        ),
        "BioETLNoRecordsProcessed": (
            "bioetl_records_processed_total",
            "docs/05-operations/runbooks/pipeline-failure-critical.md",
        ),
        "BioETLRuntimeErrorRateHigh": (
            "bioetl_errors_total",
            "docs/05-operations/runbooks/observability-checklist.md",
        ),
        "BioETLRecordFlowInvariantViolated": (
            "bioetl_record_flow_invariants_total",
            "docs/05-operations/runbooks/observability-checklist.md",
        ),
        "BioETLIngestionThroughputDegraded": (
            "bioetl_stage_backlog_records",
            "docs/05-operations/runbooks/observability-checklist.md",
        ),
        "BioETLStageBacklogActive": (
            "bioetl_stage_backlog_records",
            "docs/05-operations/runbooks/observability-checklist.md",
        ),
        "BioETLStageLagHigh": (
            "bioetl_stage_lag_seconds",
            "docs/05-operations/runbooks/observability-checklist.md",
        ),
        "BioETLMemoryPressureActive": (
            "bioetl_memory_pressure_state",
            "docs/05-operations/runbooks/observability-checklist.md",
        ),
    }

    missing = [name for name in expected if name not in rule_map]
    assert not missing, f"Missing expected alerts: {missing}"

    for alert_name, (metric_name, runbook_path) in expected.items():
        rule = rule_map[alert_name]
        expr = rule.get("expr", "")
        annotations = rule.get("annotations", {})
        assert metric_name in expr
        assert annotations.get("runbook") == runbook_path


def test_control_plane_traceability_alerts_reference_expected_metrics() -> None:
    payload = _load_rules()
    rule_map = _build_rule_map(payload)

    expected = {
        "BioETLControlPlaneManifestWriteFailed": (
            "bioetl_control_plane_manifest_writes_total",
            "docs/05-operations/runbooks/run-manifest-inspection.md",
        ),
        "BioETLRunLedgerAppendFailed": (
            "bioetl_control_plane_ledger_appends_total",
            "docs/05-operations/runbooks/run-manifest-inspection.md",
        ),
        "BioETLCheckpointCompatibilityBlocked": (
            "bioetl_checkpoint_compatibility_events_total",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "BioETLCheckpointLoadFailed": (
            "bioetl_checkpoint_load_events_total",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "BioETLCheckpointSaveFailed": (
            "bioetl_checkpoint_save_events_total",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "BioETLCheckpointOperatorFailed": (
            "bioetl_checkpoint_operator_operations_total",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "BioETLCheckpointSaveLatencyHigh": (
            "bioetl_checkpoint_save_duration_seconds",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "BioETLCheckpointOperatorLatencyHigh": (
            "bioetl_checkpoint_operator_duration_seconds",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "BioETLReplayNotReconstructable": (
            "bioetl_replay_reconstructability_events_total",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "BioETLReplayLagHigh": (
            "bioetl_replay_lag_seconds",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "BioETLReplayDriftDetected": (
            "bioetl_replay_drift_events_total",
            "docs/05-operations/runbooks/checkpoint-debugging.md",
        ),
        "BioETLLineageFragmentPersistenceFailed": (
            "bioetl_lineage_fragments_emitted_total",
            "docs/05-operations/runbooks/traceability-signal-ownership.md",
        ),
        "BioETLLineageRefsMissing": (
            "bioetl_lineage_refs_missing_total",
            "docs/05-operations/runbooks/traceability-signal-ownership.md",
        ),
        "BioETLControlPlaneReadFailureRate": (
            "bioetl_control_plane_reads_total",
            "docs/05-operations/runbooks/observability-checklist.md",
        ),
    }

    missing = [name for name in expected if name not in rule_map]
    assert not missing, f"Missing expected alerts: {missing}"

    for alert_name, (metric_name, runbook_path) in expected.items():
        rule = rule_map[alert_name]
        expr = rule.get("expr", "")
        annotations = rule.get("annotations", {})
        assert metric_name in expr
        assert annotations.get("runbook") == runbook_path


def test_dq_and_provider_alerts_reference_expected_metrics() -> None:
    payload = _load_rules()
    rule_map = _build_rule_map(payload)

    expected = {
        "BioETLDQSoftThresholdExceeded": (
            "bioetl_dq_soft_threshold_exceeded",
            "docs/05-operations/runbooks/dq-failure-investigation.md",
        ),
        "BioETLDQQuarantineRateHigh": (
            "bioetl_dq_records_quarantined_total",
            "docs/05-operations/runbooks/dq-failure-investigation.md",
        ),
        "BioETLDQQuarantineRateCritical": (
            "bioetl_dq_records_quarantined_total",
            "docs/05-operations/runbooks/dq-failure-investigation.md",
        ),
        "BioETLDQValidationFailuresCritical": (
            "bioetl_dq_validation_failures_total",
            "docs/05-operations/runbooks/dq-failure-investigation.md",
        ),
        "BioETLGoldValidationFailuresCritical": (
            "bioetl_dq_validation_failures_total",
            "docs/05-operations/runbooks/dq-failure-investigation.md",
        ),
        "BioETLDQCriticalAnomaliesDetected": (
            "bioetl_dq_anomaly_detected",
            "docs/05-operations/runbooks/dq-failure-investigation.md",
        ),
        "BioETLSilverValidationFailuresDetected": (
            "bioetl_silver_validation_failures_total",
            "docs/05-operations/runbooks/dq-failure-investigation.md",
        ),
        "BioETLSilverFilterRejectAccountingMismatch": (
            "bioetl_silver_filter_reject_total_mismatch_15m",
            "docs/05-operations/runbooks/dq-failure-investigation.md",
        ),
        "BioETLDataFreshnessLagHigh": (
            "bioetl_data_freshness_seconds",
            "docs/05-operations/runbooks/dq-failure-investigation.md",
        ),
        "BioETLDataFreshnessLagCritical": (
            "bioetl_data_freshness_seconds",
            "docs/05-operations/runbooks/dq-failure-investigation.md",
        ),
        "BioETLProviderFailureRateHigh": (
            "bioetl_provider_health_check_failures_15m",
            "docs/05-operations/runbooks/incident-response.md",
        ),
        "BioETLProviderHealthCheckFailuresDetected": (
            "bioetl_health_check_failures_total",
            "docs/05-operations/runbooks/incident-response.md",
        ),
        "BioETLProviderRetriesExhausted": (
            "bioetl_data_source_retry_exhausted_total",
            "docs/05-operations/runbooks/incident-response.md",
        ),
        "BioETLProviderRetriesExhaustedPersistent": (
            "bioetl_data_source_retry_exhausted_total",
            "docs/05-operations/runbooks/incident-response.md",
        ),
        "BioETLCircuitBreakerStuckOpen": (
            "bioetl_circuit_breaker_state",
            "docs/05-operations/runbooks/incident-response.md",
        ),
        "BioETLProviderAdapterLatencyHigh": (
            "bioetl_adapter_request_duration_seconds_bucket",
            "docs/05-operations/runbooks/incident-response.md",
        ),
        "BioETLProviderHttpErrorRateHigh": (
            "bioetl_http_request_errors_total",
            "docs/05-operations/runbooks/incident-response.md",
        ),
        "BioETLProviderRateLimiterWaitHigh": (
            "bioetl_rate_limiter_wait_seconds_bucket",
            "docs/05-operations/runbooks/incident-response.md",
        ),
        "BioETLProviderRateLimiterTokensDepleted": (
            "bioetl_rate_limiter_tokens_available",
            "docs/05-operations/runbooks/incident-response.md",
        ),
    }

    missing = [name for name in expected if name not in rule_map]
    assert not missing, f"Missing expected alerts: {missing}"

    for alert_name, (metric_name, runbook_path) in expected.items():
        rule = rule_map[alert_name]
        expr = rule.get("expr", "")
        annotations = rule.get("annotations", {})
        assert metric_name in expr
        assert annotations.get("runbook") == runbook_path


def test_tuned_alerts_use_expected_severities_and_threshold_windows() -> None:
    payload = _load_rules()
    rule_map = _build_rule_map(payload)
    _assert_tuned_alert_expectations(rule_map)


def test_silver_validation_alert_groups_by_pipeline_and_table() -> None:
    payload = _load_rules()
    rule_map = _build_rule_map(payload)

    rule = rule_map["BioETLSilverValidationFailuresDetected"]
    expr = rule.get("expr", "")
    description = rule.get("annotations", {}).get("description", "")

    assert "sum by (pipeline, table)" in expr
    assert "{{ $labels.pipeline }}" in description
    assert "{{ $labels.table }}" in description


def test_dq_validation_failure_alert_tracks_hard_fail_runtime_vocabulary() -> None:
    payload = _load_rules()
    rule_map = _build_rule_map(payload)

    rule = rule_map["BioETLDQValidationFailuresCritical"]
    expr = rule.get("expr", "")
    description = rule.get("annotations", {}).get("description", "")

    assert 'bioetl_dq_validation_failures_total{severity="hard_fail"}' in expr
    assert "severity=hard_fail" in description
    assert "severity=critical" not in description


def test_threshold_smoke_examples_cover_warning_and_critical_boundaries() -> None:
    """Smoke representative threshold scenarios to guard boundary regressions."""
    quarantine_cases = [
        {"bronze_records": 19, "quarantine_rate": 0.30, "expected": None},
        {"bronze_records": 20, "quarantine_rate": 0.05, "expected": None},
        {"bronze_records": 20, "quarantine_rate": 0.051, "expected": "warning"},
        {"bronze_records": 20, "quarantine_rate": 0.20, "expected": "warning"},
        {"bronze_records": 20, "quarantine_rate": 0.201, "expected": "critical"},
    ]
    freshness_cases = [
        {"seconds": 86400, "expected": None},
        {"seconds": 86401, "expected": "warning"},
        {"seconds": 259200, "expected": "warning"},
        {"seconds": 259201, "expected": "critical"},
    ]
    retry_cases = [
        {"exhaustions_per_hour": 0, "expected": None},
        {"exhaustions_per_hour": 1, "expected": "warning"},
        {"exhaustions_per_hour": 2, "expected": "warning"},
        {"exhaustions_per_hour": 3, "expected": "critical"},
    ]

    for case in quarantine_cases:
        assert (
            _classify_quarantine_rate(
                bronze_records=case["bronze_records"],
                quarantine_rate=case["quarantine_rate"],
            )
            == case["expected"]
        )

    for case in freshness_cases:
        assert _classify_freshness(case["seconds"]) == case["expected"]

    for case in retry_cases:
        assert (
            _classify_retry_exhaustions(case["exhaustions_per_hour"])
            == case["expected"]
        )
