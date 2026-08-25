# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Integration tests for Prometheus alert rule configuration."""

from __future__ import annotations

import json
from pathlib import Path
import re

import pytest
from scripts.engineering.qa import check_prometheus_rules
import yaml

RULES_PATH = Path("grafana/prometheus-rules/bioetl_observability.yml")
DASHBOARDS_DIR = Path("grafana/dashboards")
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
_PROMQL_QUOTED_STRING_RE = re.compile(r'"(?:\\.|[^"\\])*"')
_MAX_OVER_COUNTER_RE = re.compile(
    r"max_over_time\(\s*([a-zA-Z_:][a-zA-Z0-9_:]*_total)(?=\{|\[)"
)
_EVENT_DELTA_COUNTERS = frozenset(
    {
        "bioetl_pipeline_runs_total",
        "bioetl_errors_total",
        "bioetl_silver_validation_failures_total",
    }
)
_PUSHED_SNAPSHOT_COUNTERS = frozenset(
    {
        "bioetl_records_processed_total",
        "bioetl_stage_records_total",
        "bioetl_dq_records_quarantined_total",
        "bioetl_silver_filter_rejections_total",
    }
)


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


def test_prometheus_rules_directory_has_no_duplicate_backup_rule_files() -> None:
    """Wildcard rule loading must not pick up backup/scratch copies of rule files."""
    rules_dir = Path("grafana/prometheus-rules")
    duplicate_candidates = sorted(
        path.name
        for path in rules_dir.iterdir()
        if path.is_file()
        and (
            path.suffix == ".bak"
            or path.name.endswith(".yml.bak")
            or "fixed" in path.name.lower()
            or "scratch" in path.name.lower()
        )
    )
    assert not duplicate_candidates, (
        "Prometheus rule_files uses /etc/prometheus/rules/*.yml, so backup/scratch "
        f"copies would be loaded as duplicate rules: {duplicate_candidates}"
    )


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


def _iter_dashboard_promql() -> list[tuple[str, str, str]]:
    expressions: list[tuple[str, str, str]] = []
    for path in sorted(DASHBOARDS_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        source_name = path.name

        def _visit(
            node: object,
            panel_title: str = "<dashboard>",
            source_name: str = source_name,
        ) -> None:
            if isinstance(node, dict):
                current_title = str(node.get("title") or panel_title)
                expr = node.get("expr")
                if isinstance(expr, str):
                    expressions.append((source_name, current_title, expr))
                for value in node.values():
                    _visit(value, current_title)
            elif isinstance(node, list):
                for item in node:
                    _visit(item, panel_title)

        _visit(payload)
    return expressions


def _iter_rule_promql(payload: dict) -> list[tuple[str, str, str]]:
    expressions: list[tuple[str, str, str]] = []
    for group in payload.get("groups", []):
        group_name = str(group.get("name", "<group>"))
        for rule in group.get("rules", []):
            name = str(rule.get("record") or rule.get("alert") or "<rule>")
            expr = rule.get("expr")
            if isinstance(expr, str):
                expressions.append((group_name, name, expr))
    return expressions


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
        # Health /metrics scrape liveness gauge is emitted as plain exposition
        # text (not Prometheus client registry) from the health server path.
        "bioetl_health_server_scrape_up": frozenset({"job", "instance"}),
    }
    docker_contract = yaml.safe_load(
        Path("configs/quality/docker_runtime_contracts.yaml").read_text(
            encoding="utf-8"
        )
    )
    for name, labels in docker_contract["host_probe"]["metric_labels"].items():
        label_sets[str(name)] = frozenset(map(str, labels))

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
    expr_without_string_literals = _PROMQL_QUOTED_STRING_RE.sub('""', expr)
    for metric_name in _PROMQL_BIOETL_METRIC_TOKEN_RE.findall(
        expr_without_string_literals
    ):
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
    if quarantine_rate <= 0.5:
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
        "for": "5m",
        "fragments": ["absent_over_time(bioetl_pipeline_runs_total[10m])"],
    },
    "BioETLMetricsEndpointScrapeMissing": {
        "severity": "warning",
        "for": "10m",
        "fragments": [
            'up{job="bioetl"}',
            "absent_over_time",
            "bioetl_pipeline_runs_total",
            "== 0",
            "unless on()",
        ],
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
    "BioETLGrafanaRendererUnavailable": {
        "severity": "warning",
        "for": "2m",
        "fragments": ['up{job="grafana-image-renderer"}', "== 0"],
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
        "fragments": ["> 0.05", "<= 0.5", ">= 20", "[30m]"],
    },
    "BioETLDQQuarantineRateCritical": {
        "severity": "critical",
        "for": "5m",
        "fragments": ["> 0.5", ">= 20", "[15m]"],
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
    assert {
        "bioetl",
        "prometheus",
        "grafana",
        "pushgateway",
        "grafana-image-renderer",
    } <= scrape_jobs
    assert "quarantine-explorer" not in scrape_jobs
    assert "loki" not in scrape_jobs

    grafana_service = compose.get("services", {}).get("grafana", {})
    environment = grafana_service.get("environment", [])
    assert "GF_METRICS_ENABLED=true" in environment, (
        "Grafana metrics must be enabled so the monitoring stack can self-monitor."
    )


def test_monitoring_images_match_documented_qa_compatibility_series() -> None:
    compose = _load_monitoring_compose()
    services = compose["services"]

    assert services["prometheus"]["image"] == check_prometheus_rules.PROMETHEUS_IMAGE
    assert services["pushgateway"]["image"] == (
        "prom/pushgateway:v1.11.3@sha256:"
        "74fa117cef2d7e383112d25139ff1c2d2e309c35389a9e0554a47136a1482e48"
    )
    assert check_prometheus_rules.PROMETHEUS_COMPATIBILITY_SERIES == "3.13.x"
    assert check_prometheus_rules.PUSHGATEWAY_COMPATIBILITY_SERIES == "1.11.x"


def test_prometheus_config_loads_repo_rule_directory() -> None:
    prometheus_config = _load_prometheus_config()
    rule_files = prometheus_config.get("rule_files", [])

    assert "/etc/prometheus/rules/*.yml" in rule_files


def test_prometheus_routes_alerts_to_the_optional_alertmanager_helper() -> None:
    """The helper is optional, but its configured transport must be usable."""
    prometheus_config = _load_prometheus_config()
    alertmanagers = prometheus_config.get("alerting", {}).get("alertmanagers", [])

    assert alertmanagers == [{"static_configs": [{"targets": ["alertmanager:9093"]}]}]


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
    # Check that replace-style functions are imported for dependency injection
    assert (
        "from prometheus_client.exposition import delete_from_gateway, push_to_gateway"
        in server_source
    )
    # Check that wrapper functions are used (dependency injection pattern)
    assert "publish_metrics_to_gateway" in server_source
    assert "remove_metrics_from_gateway" in server_source
    assert "push_gateway=push_to_gateway" in server_source
    assert "delete_gateway=delete_from_gateway" in server_source


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
        "bioetl_runtime_error_rate_30m": "bioetl_errors_total",
        "bioetl_runtime_alert_condition_runtime_error_rate_high_30m": "bioetl_runtime_error_rate_30m",
        "bioetl_runtime_alert_condition_record_flow_invariant_violated_15m": "bioetl_record_flow_invariants_total",
        "bioetl_runtime_alert_condition_ingestion_throughput_degraded_15m": "bioetl_stage_backlog_records",
        "bioetl_runtime_alert_condition_stage_backlog_active_15m": "bioetl_stage_backlog_records",
        "bioetl_runtime_alert_condition_stage_lag_high_15m": "bioetl_stage_lag_seconds",
        "bioetl_gold_terminal_records_15m": "bioetl_stage_records_total",
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
        "bioetl_processed_records_bronze_current": "bioetl_stage_records_total",
        "bioetl_processed_records_silver_valid_current": "bioetl_stage_records_total",
        "bioetl_processed_records_silver_quarantined_current": "bioetl_stage_records_total",
        "bioetl_processed_records_silver_skipped_current": "bioetl_stage_records_total",
        "bioetl_processed_records_silver_filtered_out_current": "bioetl_stage_records_total",
        "bioetl_processed_records_silver_deduplicated_current": "bioetl_stage_records_total",
        "bioetl_processed_records_silver_accounted_current": "bioetl_stage_records_total",
        "bioetl_processed_records_silver_delta_current": "bioetl_processed_records_silver_accounted_current",
        "bioetl_processed_records_gold_written_current": "bioetl_stage_records_total",
        "bioetl_processed_records_gold_quarantined_current": "bioetl_stage_records_total",
        "bioetl_processed_records_gold_skipped_current": "bioetl_stage_records_total",
        "bioetl_processed_records_gold_excluded_by_contract_current": "bioetl_stage_records_total",
        "bioetl_processed_records_gold_deduplicated_current": "bioetl_stage_records_total",
        "bioetl_processed_records_gold_accounted_current": "bioetl_stage_records_total",
        "bioetl_processed_records_gold_delta_current": "bioetl_processed_records_gold_accounted_current",
        "bioetl_processed_records_delta_abs_current": "bioetl_processed_records_silver_delta_current",
        "bioetl_processed_records_reconciliation_status": "bioetl_processed_records_delta_abs_current",
    }

    missing = [name for name in expected if name not in record_map]
    assert not missing, f"Missing expected recording rules: {missing}"

    for record_name, source_metric in expected.items():
        expr = record_map[record_name].get("expr", "")
        assert source_metric in expr, (
            f"{record_name} must reference {source_metric} to avoid semantic drift"
        )


def test_processed_records_reconciliation_rules_preserve_semantic_contract() -> None:
    payload = _load_rules()
    record_map = _build_record_map(payload)
    rules = {
        name: rule
        for name, rule in record_map.items()
        if name.startswith("bioetl_processed_records_")
    }
    assert rules

    for record_name, rule in rules.items():
        expr = rule.get("expr", "")
        assert "run_id" not in expr
        assert "manifest_id" not in expr
        assert "payload_hash" not in expr
        assert "raw_path" not in expr
        assert "error_message" not in expr
        assert "$__range" not in expr
        assert "or vector(0)" not in expr
        assert "run_id" not in str(rule.get("labels", {}))
        assert "run_id" not in str(rule.get("annotations", {}))
        assert "bioetl_records_processed_total" not in expr, (
            f"{record_name} must use canonical stage/outcome accounting, "
            "not legacy processed-record stage counters"
        )

    status_expr = str(
        record_map["bioetl_processed_records_reconciliation_status"].get("expr", "")
    )
    assert "bioetl_overview_pipeline_run_type_universe * 0" in status_expr
    assert 'status=~"success|completed|failed|shutdown"' in status_expr


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
        "bioetl_checkpoint_age_seconds": "bioetl_checkpoint_saved_at_seconds",
        "bioetl_terminal_events_15m": "bioetl_control_plane_terminal_events_total",
    }

    missing = [name for name in expected if name not in record_map]
    assert not missing, f"Missing expected control-plane recording rules: {missing}"

    for record_name, source_metric in expected.items():
        expr = record_map[record_name].get("expr", "")
        assert source_metric in expr, (
            f"{record_name} must reference {source_metric} to avoid semantic drift"
        )


def test_pipeline_universe_rules_include_workflow_planned_scopes() -> None:
    """Pipeline selectors must include planned workflow child pipelines before completion."""
    payload = _load_rules()
    record_map = _build_record_map(payload)

    for record_name in (
        "bioetl_overview_pipeline_universe",
        "bioetl_runtime_pipeline_run_type_universe",
    ):
        expr = record_map[record_name].get("expr", "")
        assert "bioetl_workflow_pipeline_expected" in expr

    control_plane_payload = _load_control_plane_current_status_rules()
    control_plane_record_map = _build_record_map(control_plane_payload)
    control_plane_expr = control_plane_record_map[
        "bioetl_control_plane_run_type_universe"
    ].get("expr", "")
    assert "bioetl_workflow_pipeline_expected" in control_plane_expr


def test_workflow_universe_rule_includes_started_workflows() -> None:
    """Workflow selectors must include started workflows before terminal outcomes."""
    payload = _load_rules()
    record_map = _build_record_map(payload)

    expr = record_map["bioetl_workflow_universe"].get("expr", "")
    assert "bioetl_workflow_runs_total" in expr
    assert "bioetl_workflow_expected" in expr


def test_canonical_current_status_recording_rules_exist() -> None:
    """Dashboard first screens must consume canonical current-status records."""
    payload = _load_rules()
    record_map = _build_record_map(payload)

    expected = {
        "bioetl_runtime_pipeline_run_type_universe": "bioetl_pipeline_runs_total",
        "bioetl_runtime_current_activity_15m": "bioetl_pipeline_runs_total",
        "bioetl_runtime_current_failure_signals_15m": "bioetl_runtime_alert_condition_pipeline_runs_failed_15m",
        "bioetl_runtime_current_degraded_signals_15m": "bioetl_runtime_alert_condition_no_terminal_run_30m",
        "bioetl_runtime_current_status": "bioetl_runtime_current_failure_signals_15m",
        "bioetl_runtime_trust_gap_status_10m": "absent_over_time(bioetl_pipeline_runs_total[10m])",
        "bioetl_runtime_trust_gap_active_10m": "bioetl_runtime_trust_gap_status_10m",
        "bioetl_runtime_pipeline_run_type_universe_scoped": "bioetl_runtime_pipeline_run_type_universe",
        "bioetl_runtime_current_status_scoped": "bioetl_runtime_current_status",
        "bioetl_runtime_current_status_trusted": "bioetl_runtime_current_status_scoped",
        "bioetl_runtime_current_blocker_reason_scoped": "bioetl_runtime_current_blocker_reason",
        "bioetl_provider_current_status": "bioetl_provider_health_status",
        "bioetl_provider_current_cause": "bioetl_provider_health_status",
        "bioetl_dq_current_activity_15m": "bioetl_records_processed_total",
        "bioetl_dq_current_failure_signals_15m": "bioetl_runtime_alert_condition_dq_hard_fail_15m",
        "bioetl_dq_current_degraded_signals_15m": "bioetl_runtime_alert_condition_dq_soft_threshold_15m",
        "bioetl_dq_current_status": 'bioetl_dq_current_reason{severity="crit"}',
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


def test_overview_workflow_input_uses_workflow_evidence_not_pipeline_counter_delta() -> (
    None
):
    """Workflow overview summaries must stay queryable after short-lived CLI runs exit."""
    payload = _load_rules()
    workflow_rules = [
        rule
        for rule in _recording_rules_named(payload, "bioetl_l0_input_status")
        if rule.get("labels", {}).get("input") == "workflow"
    ]
    assert workflow_rules, "Missing workflow input projection rule"

    expr = "\n".join(str(rule.get("expr", "")) for rule in workflow_rules)
    expr_compact = re.sub(r"\s+", " ", expr)
    assert "bioetl_workflow_current_status" in expr
    assert "bioetl_overview_pipeline_run_type_universe" in expr
    assert '"pipeline", "$1", "pipeline_context"' in expr_compact
    assert '"run_type", "$1", "run_type_context"' in expr_compact
    assert (
        "max by (pipeline, run_type) (bioetl_workflow_current_status)"
        not in expr_compact
    )
    assert (
        "unless on (pipeline, run_type) max by (pipeline, run_type) (" in expr_compact
    )
    assert "bioetl_workflow_runs_total" not in expr
    assert "bioetl_pipeline_runs_total" not in expr


def test_canonical_current_status_rules_do_not_use_grafana_range_or_zero_fallback() -> (
    None
):
    """Current status must not be calculated from selected range evidence."""
    payload = _load_rules()
    record_map = _build_record_map(payload)

    current_status_records = (
        "bioetl_runtime_current_status",
        "bioetl_runtime_current_status_scoped",
        "bioetl_runtime_current_status_trusted",
        "bioetl_provider_current_status",
        "bioetl_dq_current_status",
    )
    for record_name in current_status_records:
        expr = record_map[record_name].get("expr", "")
        assert "$__range" not in expr
        assert "or vector(0)" not in expr


def test_counter_window_promql_semantics_are_classified() -> None:
    """Counters in max_over_time windows must be reviewed as snapshots, not events."""
    payload = _load_rules()
    offenders: list[str] = []
    snapshot_hits: set[str] = set()

    for source, owner, expr in [
        *_iter_rule_promql(payload),
        *_iter_dashboard_promql(),
    ]:
        for metric in _MAX_OVER_COUNTER_RE.findall(expr):
            if metric in _EVENT_DELTA_COUNTERS:
                offenders.append(
                    f"{source}::{owner}: event counter {metric} must use increase()"
                )
            elif metric in _PUSHED_SNAPSHOT_COUNTERS:
                snapshot_hits.add(metric)
            else:
                offenders.append(
                    f"{source}::{owner}: unclassified max_over_time counter {metric}"
                )

    assert not offenders, "\n".join(offenders[:40])
    assert snapshot_hits == _PUSHED_SNAPSHOT_COUNTERS


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
    """Pipeline-level runtime blockers must stay visible after run_type filtering."""
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
        assert (
            "bioetl_runtime_pipeline_run_type_universe * on (pipeline) group_left()"
            in expr
        )
        assert "bioetl_runtime_pipeline_run_type_universe" in expr

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
    assert "bioetl_provider_health_check_provider_universe_15m * 0 + 3" in expr
    assert "bioetl_provider_observed_universe * 0 + 3" in expr
    assert "/" not in expr
    assert " or " in expr
    info_rules = [
        rule
        for group in payload.get("groups", [])
        for rule in group.get("rules", [])
        if rule.get("record") == "bioetl_provider_current_status_info"
    ]
    assert info_rules
    reasons = {rule.get("labels", {}).get("reason") for rule in info_rules}
    assert "missing_health_status" in reasons
    assert "observed_health_status" in reasons
    completeness = {rule.get("labels", {}).get("completeness") for rule in info_rules}
    assert completeness == {"incomplete", "complete"}
    health_present = {
        rule.get("labels", {}).get("health_status_present") for rule in info_rules
    }
    assert health_present == {"0", "1"}


def test_provider_current_status_fails_closed_on_missing_raw_status_series() -> None:
    payload = _load_rules()
    record_map = _build_record_map(payload)
    expr = record_map["bioetl_provider_current_status"].get("expr", "")

    assert "bioetl_provider_health_check_provider_universe_15m" in expr
    assert "bioetl_provider_health_check_provider_universe_15m * 0 + 3" in expr
    assert "bioetl_provider_observed_universe * 0 + 3" in expr
    assert "bioetl_provider_health_status" in expr
    assert "/" not in expr


def test_overview_l0_status_aggregates_selected_scope_rows() -> None:
    payload = _load_rules()
    record_map = _build_record_map(payload)
    expr = record_map["bioetl_l0_status"].get("expr", "")

    assert "bioetl_l0_input_status_selected" in expr
    assert 'input=~"runtime|dq|control_plane|workflow|gold"' not in expr
    assert "bioetl_l0_input_status_selected == 2" in expr
    assert "bioetl_l0_input_status_selected == 1" in expr
    assert "bioetl_l0_input_status_selected == 3" in expr
    assert "bioetl_l0_input_status_selected == 0" in expr
    assert (
        "max by (pipeline, run_type) (\n            bioetl_l0_input_status_selected\n          )"
        not in expr
    )


def test_overview_next_action_routes_use_selected_scope_rows() -> None:
    payload = _load_rules()
    route_rules = _recording_rules_named(payload, "bioetl_l0_next_action_route")
    expressions = "\n".join(str(rule.get("expr", "")) for rule in route_rules)

    assert 'bioetl_l0_input_status_selected{input="runtime"}' in expressions
    assert 'bioetl_l0_input_status_selected{input="control_plane"}' in expressions
    assert 'bioetl_l0_input_status_selected{input="gold"}' in expressions
    assert 'bioetl_l0_input_status_selected{input="dq"}' in expressions
    assert 'bioetl_l0_input_status_selected{input="provider"}' in expressions
    assert 'bioetl_l0_input_status_selected{input="workflow"}' in expressions


def test_overview_next_action_route_priority_scores_are_ordered() -> None:
    """RFA-P2: Runtime > Control Plane > Gold > DQ > Provider > Workflow > Monitor."""
    payload = _load_rules()
    route_rules = _recording_rules_named(payload, "bioetl_l0_next_action_route")

    def _score(rule: dict) -> int:
        expr = str(rule.get("expr", "")).replace(" ", "")
        # Patterns like ") * 50" or "universe * 5"
        for token in ("*50", "*40", "*35", "*30", "*20", "*10", "*5"):
            if token in expr:
                return int(token.removeprefix("*"))
        raise AssertionError(f"No priority score found in expr: {rule.get('expr')}")

    by_reason = {
        str(rule.get("labels", {}).get("action_reason")): _score(rule)
        for rule in route_rules
    }
    assert by_reason["runtime_blockers_active"] == 50
    assert by_reason["control_plane_guardrail_active"] == 40
    assert by_reason["gold_lifecycle_blocking"] == 35
    assert by_reason["dq_threshold_or_validation_signal"] == 30
    assert by_reason["provider_global_degradation"] == 20
    assert by_reason["workflow_scope_requires_review"] == 10
    assert by_reason["no_recent_activity_or_unknown_state"] == 5

    # Gold lifecycle handoff stays on Runtime board (gold write missing is runtime-owned).
    gold_rule = next(
        rule
        for rule in route_rules
        if rule.get("labels", {}).get("action_reason") == "gold_lifecycle_blocking"
    )
    assert gold_rule.get("labels", {}).get("action_target") == "runtime"
    assert gold_rule.get("labels", {}).get("action_dashboard_uid") == "bioetl-runtime"

    workflow_rule = next(
        rule
        for rule in route_rules
        if rule.get("labels", {}).get("action_reason")
        == "workflow_scope_requires_review"
    )
    assert workflow_rule.get("labels", {}).get("action_dashboard_uid") == (
        "bioetl-runtime"
    )

    provider_rule = next(
        rule
        for rule in route_rules
        if rule.get("labels", {}).get("action_reason") == "provider_global_degradation"
    )
    assert provider_rule.get("labels", {}).get("action_dashboard_uid") == (
        "bioetl-provider-health-v2"
    )
    # Provider severity remains global (scalar max); pipeline context is URL-layer only.
    assert "scalar(" in str(provider_rule.get("expr", ""))


def test_overview_runtime_and_dq_inputs_materialize_from_stable_projected_shapes() -> (
    None
):
    payload = _load_rules()
    runtime_rule = next(
        rule
        for rule in _recording_rules_named(payload, "bioetl_l0_input_status")
        if rule.get("labels", {}).get("input") == "runtime"
    )
    dq_rule = next(
        rule
        for rule in _recording_rules_named(payload, "bioetl_l0_input_status")
        if rule.get("labels", {}).get("input") == "dq"
    )

    runtime_expr = str(runtime_rule.get("expr", ""))
    dq_expr = str(dq_rule.get("expr", ""))

    assert "max by (pipeline, run_type)" in runtime_expr
    assert "bioetl_runtime_alert_condition_stage_backlog_active_15m" in runtime_expr
    assert "bioetl_runtime_alert_condition_stage_lag_high_15m" in runtime_expr
    assert "unless on (pipeline, run_type)" in runtime_expr
    assert "bioetl_dq_current_status" in dq_expr
    assert "bioetl_overview_pipeline_run_type_universe" in dq_expr
    assert "* on (pipeline) group_left() bioetl_dq_current_status" in dq_expr


def test_runtime_backlog_and_gold_missing_current_status_rules_use_current_gauges() -> (
    None
):
    payload = _load_rules()
    record_map = _build_record_map(payload)

    backlog_expr = str(
        record_map["bioetl_runtime_alert_condition_stage_backlog_active_15m"].get(
            "expr", ""
        )
    )
    gold_expr = str(
        record_map["bioetl_runtime_alert_condition_gold_write_missing_15m"].get(
            "expr", ""
        )
    )

    assert "bioetl_stage_backlog_records" in backlog_expr
    assert "max_over_time(bioetl_stage_backlog_records" not in backlog_expr
    assert 'bioetl_stage_backlog_records{stage="output"}' in gold_expr
    assert (
        'max_over_time(bioetl_stage_backlog_records{stage="output"}[15m])'
        not in gold_expr
    )


def test_overview_control_plane_input_coalesces_absent_alert_series_to_zero() -> None:
    payload = _load_rules()
    control_plane_rule = next(
        rule
        for rule in _recording_rules_named(payload, "bioetl_l0_input_status")
        if rule.get("labels", {}).get("input") == "control_plane"
    )

    expr = str(control_plane_rule.get("expr", ""))

    assert "bioetl_runtime_alert_condition_manifest_write_failed_15m" in expr
    assert "bioetl_runtime_alert_condition_ledger_append_failed_15m" in expr
    assert "bioetl_runtime_alert_condition_checkpoint_incompatible_30m" in expr
    assert "bioetl_runtime_alert_condition_lineage_refs_missing_15m" in expr
    assert "bioetl_overview_pipeline_run_type_universe * 0" in expr
    assert "(max by (pipeline) (" in expr
    assert "== bool 0" in expr


def test_runtime_no_terminal_run_treats_success_as_terminal() -> None:
    payload = _load_rules()
    record_map = _build_record_map(payload)
    expr = record_map["bioetl_runtime_alert_condition_no_terminal_run_30m"].get(
        "expr", ""
    )

    assert 'status=~"success|completed|failed"' in expr


def test_control_plane_current_status_rules_project_pipeline_signals_to_run_type() -> (
    None
):
    payload = _load_control_plane_current_status_rules()
    record_map = _build_record_map(payload)

    replay_expr = record_map["bioetl_replay_safety_blockers_15m"].get("expr", "")
    failures_expr = record_map["bioetl_manifest_ledger_failures_15m"].get("expr", "")
    telemetry_expr = record_map["bioetl_control_plane_telemetry_missing_5m"].get(
        "expr", ""
    )
    checkpoint_age_expr = record_map["bioetl_checkpoint_age_seconds"].get("expr", "")

    assert "bioetl_control_plane_run_type_universe" in replay_expr
    assert "* on (pipeline) group_left()" in replay_expr
    assert "bioetl_control_plane_run_type_universe" in failures_expr
    assert "* on (pipeline) group_left()" in failures_expr
    assert "bioetl_control_plane_run_type_universe" in telemetry_expr
    assert "* on (pipeline) group_left()" in telemetry_expr
    assert "time()" in checkpoint_age_expr
    assert (
        "max by (pipeline) (bioetl_checkpoint_saved_at_seconds)" in checkpoint_age_expr
    )


def test_control_plane_rules_require_replay_risk_and_integrity_telemetry() -> None:
    payload = _load_control_plane_current_status_rules()
    record_map = _build_record_map(payload)

    universe_expr = record_map["bioetl_control_plane_run_type_universe"]["expr"]
    replay_expr = record_map["bioetl_replay_safety_blockers_15m"]["expr"]
    failures_expr = record_map["bioetl_manifest_ledger_failures_15m"]["expr"]
    telemetry_expr = record_map["bioetl_control_plane_telemetry_missing_5m"]["expr"]

    assert "bioetl_manifest_ledger_integrity_ratio" in universe_expr
    assert "increase(bioetl_replay_duplicate_overwrite_risk_total[15m])" in (
        replay_expr
    )
    assert 'integrity_type="inconsistent"' in replay_expr
    assert 'integrity_type="inconsistent"' in failures_expr
    assert 'risk_type=~"duplicate|overwrite"' in telemetry_expr
    assert 'integrity_type=~"consistent|inconsistent"' in telemetry_expr
    assert telemetry_expr.count("== 2") == 2
    assert re.search(r",\s*4\s*\)\s*$", telemetry_expr)


def test_dq_current_status_splits_hard_failures_from_degraded_warnings() -> None:
    payload = _load_rules()
    record_map = _build_record_map(payload)

    silver_validation_expr = record_map[
        "bioetl_runtime_alert_condition_silver_validation_failures_30m"
    ].get("expr", "")
    failure_expr = record_map["bioetl_dq_current_failure_signals_15m"].get("expr", "")
    monitor_disabled_expr = record_map["bioetl_dq_monitor_disabled_current"].get(
        "expr", ""
    )
    degraded_expr = record_map["bioetl_dq_current_degraded_signals_15m"].get("expr", "")

    assert "increase(bioetl_silver_validation_failures_total[30m])" in (
        silver_validation_expr
    )
    assert "bioetl_overview_pipeline_universe * 0" in silver_validation_expr
    assert "or on (pipeline)" in silver_validation_expr
    assert "max_over_time(bioetl_silver_validation_failures_total[30m])" not in (
        silver_validation_expr
    )
    status_expr = record_map["bioetl_dq_current_status"].get("expr", "")
    quarantined_reason_rules = [
        rule
        for rule in _recording_rules_named(payload, "bioetl_dq_current_reason")
        if rule.get("labels", {}).get("reason") == "quarantined_records"
    ]
    dq_disabled_reason_rules = [
        rule
        for rule in _recording_rules_named(payload, "bioetl_dq_current_reason")
        if rule.get("labels", {}).get("reason") == "dq_monitor_disabled"
    ]

    assert "bioetl_runtime_alert_condition_dq_hard_fail_15m" in failure_expr
    assert "bioetl_runtime_alert_condition_dq_critical_anomaly_30m" in failure_expr
    assert "bioetl_runtime_alert_condition_silver_validation_failures_30m" in (
        failure_expr
    )
    assert "bioetl_overview_pipeline_universe * 0" in failure_expr
    assert "bioetl_dq_monitor_enabled == bool 0" in monitor_disabled_expr
    assert "bioetl_runtime_alert_condition_dq_soft_threshold_15m" in degraded_expr
    assert "max_over_time(bioetl_dq_records_quarantined_total[15m])" in degraded_expr
    assert "max_over_time(bioetl_silver_filter_rejections_total[15m])" in degraded_expr
    assert "bioetl_overview_pipeline_universe * 0" in degraded_expr
    assert "bioetl_dq_monitor_disabled_current" in degraded_expr
    assert 'bioetl_dq_current_reason{severity="crit"}' in status_expr
    assert 'bioetl_dq_current_reason{severity="warn"}' in status_expr
    assert "bioetl_dq_current_activity_15m * 0" in status_expr
    assert len(dq_disabled_reason_rules) == 1
    assert len(quarantined_reason_rules) == 1
    contract_exclude_reason_rules = [
        rule
        for rule in _recording_rules_named(payload, "bioetl_dq_current_reason")
        if rule.get("labels", {}).get("reason") == "gold_contract_exclusions"
    ]
    assert len(contract_exclude_reason_rules) == 1
    assert contract_exclude_reason_rules[0].get("labels", {}).get("severity") == "warn"
    assert "excluded_by_contract" in contract_exclude_reason_rules[0].get("expr", "")
    assert (
        dq_disabled_reason_rules[0].get("expr", "")
        == "bioetl_dq_monitor_disabled_current"
    )
    assert (
        quarantined_reason_rules[0].get("expr", "")
        == "max by (pipeline) (max_over_time(bioetl_dq_records_quarantined_total[15m])) > bool 0"
    )


def test_dq_first_window_reason_record_keeps_status_gap_fallback() -> None:
    """#9561: first-window DQ reasons stay short in Grafana; fallback lives in rules."""
    payload = _load_rules()
    expr = str(_build_record_map(payload)["bioetl_dq_first_window_reason"].get("expr", ""))
    compact = expr.replace(" ", "").replace("\n", "")
    assert "bioetl_dq_current_reason" in compact
    assert "bioetl_dq_current_status" in compact
    for marker in (
        "reason_evidence_unavailable",
        "verify_dq_reason_rules",
        '"severity","warn"',
        '"severity","crit"',
        "unlesson(pipeline)",
    ):
        assert marker in compact


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
        "BioETLMetricsEndpointUnavailable": (
            "5m",
            "absent_over_time(bioetl_pipeline_runs_total[10m])",
        ),
        "BioETLMetricsEndpointScrapeMissing": ("10m", "up"),
        "BioETLPrometheusUnavailable": ("2m", "up"),
        "BioETLGrafanaUnavailable": ("2m", "up"),
        "BioETLPushgatewayUnavailable": ("5m", "up"),
        "BioETLGrafanaRendererUnavailable": ("2m", "up"),
    }

    for alert_name, (expected_for, expected_metric) in expected.items():
        rule = rule_map[alert_name]
        expr = rule.get("expr", "")
        annotations = rule.get("annotations", {})
        assert expected_metric in expr
        assert rule.get("for") == expected_for
        assert annotations.get("runbook") == (
            "docs/05-operations/runbooks/observability-checklist.md"
        )


def test_monitoring_stack_contract_declares_service_ownership_before_thresholds() -> (
    None
):
    payload = _load_slo_alert_contract()
    contract = payload["slo_contracts"]["monitoring_stack_health"]

    assert contract["owner"] == "@bioetl-observability"
    boundaries = contract["service_boundaries"]
    assert set(boundaries) == {"bioetl_ops_http", "grafana_image_renderer"}
    for boundary in boundaries.values():
        assert boundary["owner"] == "@bioetl-observability"
        assert str(boundary["slo_intent"]).strip()


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
            "docs/05-operations/runbooks/pipeline-failure-dq.md",
        ),
        "BioETLDQQuarantineRateHigh": (
            "bioetl_dq_records_quarantined_total",
            "docs/05-operations/runbooks/pipeline-failure-dq.md",
        ),
        "BioETLDQQuarantineRateCritical": (
            "bioetl_dq_records_quarantined_total",
            "docs/05-operations/runbooks/pipeline-failure-dq.md",
        ),
        "BioETLDQValidationFailuresCritical": (
            "bioetl_dq_validation_failures_total",
            "docs/05-operations/runbooks/pipeline-failure-dq.md",
        ),
        "BioETLGoldValidationFailuresCritical": (
            "bioetl_dq_validation_failures_total",
            "docs/05-operations/runbooks/pipeline-failure-dq.md",
        ),
        "BioETLDQCriticalAnomaliesDetected": (
            "bioetl_dq_anomaly_detected",
            "docs/05-operations/runbooks/pipeline-failure-dq.md",
        ),
        "BioETLSilverValidationFailuresDetected": (
            "bioetl_silver_validation_failures_total",
            "docs/05-operations/runbooks/pipeline-failure-dq.md",
        ),
        "BioETLSilverFilterRejectAccountingMismatch": (
            "bioetl_silver_filter_reject_total_mismatch_15m",
            "docs/05-operations/runbooks/pipeline-failure-dq.md",
        ),
        "BioETLDataFreshnessLagHigh": (
            "bioetl_data_freshness_seconds",
            "docs/05-operations/runbooks/pipeline-failure-dq.md",
        ),
        "BioETLDataFreshnessLagCritical": (
            "bioetl_data_freshness_seconds",
            "docs/05-operations/runbooks/pipeline-failure-dq.md",
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
    assert set(_TUNED_ALERT_EXPECTATIONS) <= set(rule_map)


def test_silver_validation_alert_groups_by_pipeline_and_table() -> None:
    payload = _load_rules()
    rule_map = _build_rule_map(payload)

    rule = rule_map["BioETLSilverValidationFailuresDetected"]
    expr = rule.get("expr", "")
    description = rule.get("annotations", {}).get("description", "")

    assert "sum by (pipeline, table)" in expr
    assert "increase(bioetl_silver_validation_failures_total[30m])" in expr
    assert "max_over_time(bioetl_silver_validation_failures_total[30m])" not in expr
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
        {"bronze_records": 20, "quarantine_rate": 0.50, "expected": "warning"},
        {"bronze_records": 20, "quarantine_rate": 0.501, "expected": "critical"},
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


def test_recording_and_alert_rules_forbid_run_id_promql_filter() -> None:
    payload = _load_rules()
    offenders: list[str] = []
    for group in payload.get("groups", []):
        if not isinstance(group, dict):
            continue
        for rule in group.get("rules", []):
            if not isinstance(rule, dict):
                continue
            expr = str(rule.get("expr") or "").replace(" ", "")
            name = str(rule.get("record") or rule.get("alert") or "?")
            if "run_id=" in expr:
                offenders.append(name)
            if "run_id" in f"{rule.get('labels')}{rule.get('annotations')}":
                offenders.append(f"{name}:labels")
    msg = "PromQL/recording-rule run_id= is forbidden:\n" + "\n".join(offenders)
    assert not offenders, msg
