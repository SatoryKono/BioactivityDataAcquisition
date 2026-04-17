"""Integration tests for Prometheus alert rule configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

RULES_PATH = Path("grafana/prometheus-rules/bioetl_observability.yml")
pytestmark = pytest.mark.integration


def _load_rules() -> dict:
    payload = yaml.safe_load(RULES_PATH.read_text(encoding="utf-8"))
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


def test_rules_file_contains_control_plane_traceability_group() -> None:
    payload = _load_rules()
    group_names = [group.get("name") for group in payload.get("groups", [])]
    assert "bioetl_runtime_dashboard_recording" in group_names
    assert "bioetl_pipeline_runtime_observability" in group_names
    assert "bioetl_control_plane_traceability_observability" in group_names
    assert "bioetl_dq_observability" in group_names
    assert "bioetl_provider_health_observability" in group_names
    assert "bioetl_chembl_assay_observability" not in group_names


def test_runtime_dashboard_recording_rules_exist_and_reference_source_metrics() -> None:
    payload = _load_rules()
    record_map = _build_record_map(payload)

    expected = {
        "bioetl_runtime_alert_condition_pipeline_preflight_failed_15m": "bioetl_pipeline_health_check_passed",
        "bioetl_runtime_alert_condition_pipeline_infrastructure_failed_15m": "bioetl_infrastructure_validated",
        "bioetl_runtime_alert_condition_pipeline_runs_failed_15m": "bioetl_pipeline_runs_total",
        "bioetl_runtime_alert_condition_dq_soft_threshold_15m": "bioetl_dq_soft_threshold_exceeded",
        "bioetl_runtime_alert_condition_dq_hard_fail_15m": "bioetl_dq_validation_failures_total",
        "bioetl_runtime_alert_condition_dq_critical_anomaly_30m": "bioetl_dq_anomaly_detected",
        "bioetl_runtime_alert_condition_silver_validation_failures_30m": "bioetl_silver_validation_failures_total",
        "bioetl_runtime_alert_condition_manifest_write_failed_15m": "bioetl_control_plane_manifest_writes_total",
        "bioetl_runtime_alert_condition_ledger_append_failed_15m": "bioetl_control_plane_ledger_appends_total",
        "bioetl_runtime_alert_condition_checkpoint_incompatible_30m": "bioetl_checkpoint_compatibility_events_total",
        "bioetl_runtime_alert_condition_lineage_refs_missing_15m": "bioetl_lineage_refs_missing_total",
        "bioetl_runtime_alert_condition_provider_failure_rate_high_15m": "bioetl_health_check_failures_total",
        "bioetl_runtime_alert_condition_provider_retries_exhausted_1h": "bioetl_data_source_retry_exhausted_total",
    }

    missing = [name for name in expected if name not in record_map]
    assert not missing, f"Missing expected recording rules: {missing}"

    for record_name, source_metric in expected.items():
        expr = record_map[record_name].get("expr", "")
        assert source_metric in expr, (
            f"{record_name} must reference {source_metric} to avoid semantic drift"
        )


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
        "BioETLDQCriticalAnomaliesDetected": (
            "bioetl_dq_anomaly_detected",
            "docs/05-operations/runbooks/dq-failure-investigation.md",
        ),
        "BioETLSilverValidationFailuresDetected": (
            "bioetl_silver_validation_failures_total",
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
            "bioetl_health_check_failures_total",
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

    expected_labels = {
        "BioETLDQQuarantineRateHigh": "warning",
        "BioETLDQQuarantineRateCritical": "critical",
        "BioETLDataFreshnessLagHigh": "warning",
        "BioETLDataFreshnessLagCritical": "critical",
        "BioETLPipelinePreflightDataSourceFailed": "critical",
        "BioETLPipelineInfrastructureValidationFailed": "critical",
        "BioETLPipelineRunFailed": "critical",
        "BioETLProviderHealthCheckFailuresDetected": "warning",
        "BioETLProviderFailureRateHigh": "warning",
        "BioETLProviderRetriesExhausted": "warning",
        "BioETLProviderRetriesExhaustedPersistent": "critical",
        "BioETLControlPlaneReadFailureRate": "warning",
    }
    expected_expr_fragments = {
        "BioETLDQQuarantineRateHigh": ["> 0.05", "<= 0.2", ">= 20", "[30m]"],
        "BioETLDQQuarantineRateCritical": ["> 0.2", ">= 20", "[15m]"],
        "BioETLDataFreshnessLagHigh": [
            "clamp_min(time() - max by (pipeline, entity) (bioetl_data_freshness_seconds), 0)",
            "> 86400",
            "<= 259200",
        ],
        "BioETLDataFreshnessLagCritical": [
            "clamp_min(time() - max by (pipeline, entity) (bioetl_data_freshness_seconds), 0)",
            "> 259200",
        ],
        "BioETLPipelinePreflightDataSourceFailed": [
            "bioetl_pipeline_health_check_passed",
            'component="data_source"',
            "[15m]",
            "== 0",
        ],
        "BioETLPipelineInfrastructureValidationFailed": [
            "bioetl_infrastructure_validated",
            "[15m]",
            "< 1",
        ],
        "BioETLPipelineRunFailed": [
            "bioetl_pipeline_runs_total",
            'status="failed"',
            "[15m]",
            "> 0",
        ],
        "BioETLProviderHealthCheckFailuresDetected": [
            "bioetl_health_check_failures_total",
            "[10m]",
            "> 0",
        ],
        "BioETLProviderFailureRateHigh": [
            "bioetl_health_check_failures_total",
            "bioetl_health_check_success_total",
            "bioetl_health_check_degraded_total",
            "[15m]",
            "> 0.2",
        ],
        "BioETLProviderRetriesExhausted": ["> 0", "< 3", "[1h]"],
        "BioETLProviderRetriesExhaustedPersistent": [">= 3", "[1h]"],
        "BioETLControlPlaneReadFailureRate": [
            "bioetl_control_plane_reads_total",
            "increase",
            "clamp_min",
            "[30m]",
            'status="failed"',
            "store",
            "operation",
        ],
    }
    expected_for = {
        "BioETLDQQuarantineRateHigh": "10m",
        "BioETLDQQuarantineRateCritical": "5m",
        "BioETLDataFreshnessLagHigh": "15m",
        "BioETLDataFreshnessLagCritical": "15m",
        "BioETLPipelinePreflightDataSourceFailed": "2m",
        "BioETLPipelineInfrastructureValidationFailed": "2m",
        "BioETLPipelineRunFailed": "1m",
        "BioETLProviderHealthCheckFailuresDetected": "2m",
        "BioETLProviderFailureRateHigh": "5m",
        "BioETLProviderRetriesExhausted": "5m",
        "BioETLProviderRetriesExhaustedPersistent": "10m",
        "BioETLControlPlaneReadFailureRate": "15m",
    }

    for alert_name, severity in expected_labels.items():
        rule = rule_map[alert_name]
        expr = rule.get("expr", "")
        assert rule.get("labels", {}).get("severity") == severity
        assert rule.get("for") == expected_for[alert_name]
        for fragment in expected_expr_fragments[alert_name]:
            assert fragment in expr, (
                f"{alert_name} expression missing expected fragment: {fragment}"
            )


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
