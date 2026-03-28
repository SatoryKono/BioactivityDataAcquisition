"""Integration tests for Prometheus alert rule configuration."""

from __future__ import annotations

from pathlib import Path

import yaml

RULES_PATH = Path("grafana/prometheus-rules/bioetl_observability.yml")


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


def test_rules_file_contains_control_plane_traceability_group() -> None:
    payload = _load_rules()
    group_names = [group.get("name") for group in payload.get("groups", [])]
    assert "bioetl_control_plane_traceability_observability" in group_names
    assert "bioetl_dq_observability" in group_names
    assert "bioetl_provider_health_observability" in group_names


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
        "BioETLProviderRetriesExhausted": (
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
