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
"""Split-out Prometheus rule status/threshold tests (LOC budget)."""

from __future__ import annotations

import pytest

from tests.integration.test_prometheus_rules_config import (
    _TUNED_ALERT_EXPECTATIONS,
    _assert_tuned_alert_expectations,
    _build_rule_map,
    _classify_freshness,
    _classify_quarantine_rate,
    _classify_retry_exhaustions,
    _load_rules,
)

pytestmark = pytest.mark.integration


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
