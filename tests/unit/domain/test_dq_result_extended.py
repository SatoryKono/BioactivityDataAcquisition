"""Unit tests for extended DQResult with contract-based fields."""

from __future__ import annotations

import pytest
from bioetl.domain.value_objects.dq_result import DQResult, DQEvaluationStatus
from bioetl.domain.types.dq_contracts import (
    DQDisposition,
    DQViolationKind,
    DQPolicyRef,
    DQRuleOutcome,
)


pytestmark = pytest.mark.unit

class TestDQResultExtended:
    """Test extended DQResult with contract-based fields."""

    def test_d_q_result_extended__with_rule_outcomes__3c9e4d1c(self):
        """Test DQResult creation with rule outcomes."""
        policy_ref = DQPolicyRef("chembl_molecule", "1.0.0", "1.0.0")

        rule_outcomes = [
            DQRuleOutcome(
                rule_id="schema.not_null",
                violation_kind=DQViolationKind.SCHEMA_VIOLATION,
                severity="high",
                disposition=DQDisposition.FAIL,
                affected_fields=["id"],
            ),
            DQRuleOutcome(
                rule_id="threshold.completeness",
                violation_kind=DQViolationKind.THRESHOLD_BREACH,
                severity="medium",
                disposition=DQDisposition.WARN,
                affected_fields=["email"],
            ),
        ]

        result = DQResult(
            error_rate=0.15,
            status=DQEvaluationStatus.WARNING,
            anomalies=(),
            has_critical=False,
            check_duration_ms=120.5,
            rule_outcomes=tuple(rule_outcomes),
            policy_ref=policy_ref,
        )

        # Test basic fields
        assert result.error_rate == pytest.approx(0.15)
        assert result.status == DQEvaluationStatus.WARNING
        assert result.anomalies_count == 0
        assert result.has_critical is False
        assert result.check_duration_ms == pytest.approx(120.5)

        # Test new fields
        assert result.rule_outcomes_count == 2
        assert result.policy_ref == policy_ref
        assert result.has_rule_violations is True
        assert result.has_quarantine_decisions is False
        assert result.has_fail_decisions is True

    def test_dq_result_without_contract_fields(self):
        """Test backward compatibility - DQResult without contract fields."""
        result = DQResult(
            error_rate=0.05,
            status=DQEvaluationStatus.PASSED,
            anomalies=(),
            has_critical=False,
            check_duration_ms=80.0,
        )

        assert result.error_rate == pytest.approx(0.05)
        assert result.status == DQEvaluationStatus.PASSED
        assert result.rule_outcomes_count == 0
        assert result.policy_ref is None
        assert result.has_rule_violations is False

    def test_rule_outcomes_filtering(self):
        """Test filtering rule outcomes by violation kind and severity."""
        rule_outcomes = [
            DQRuleOutcome(
                rule_id="schema.not_null",
                violation_kind=DQViolationKind.SCHEMA_VIOLATION,
                severity="high",
                disposition=DQDisposition.FAIL,
            ),
            DQRuleOutcome(
                rule_id="threshold.completeness",
                violation_kind=DQViolationKind.THRESHOLD_BREACH,
                severity="medium",
                disposition=DQDisposition.WARN,
            ),
            DQRuleOutcome(
                rule_id="anomaly.detection",
                violation_kind=DQViolationKind.ANOMALY_SIGNAL,
                severity="low",
                disposition=DQDisposition.PASS,
            ),
        ]

        result = DQResult(
            error_rate=0.1,
            status=DQEvaluationStatus.WARNING,
            rule_outcomes=tuple(rule_outcomes),
        )

        # Test filtering by violation kind
        schema_violations = result.get_outcomes_by_violation_kind(
            DQViolationKind.SCHEMA_VIOLATION
        )
        assert len(schema_violations) == 1
        assert schema_violations[0].rule_id == "schema.not_null"

        threshold_breaches = result.get_outcomes_by_violation_kind(
            DQViolationKind.THRESHOLD_BREACH
        )
        assert len(threshold_breaches) == 1
        assert threshold_breaches[0].rule_id == "threshold.completeness"

        # Test filtering by severity
        high_severity = result.get_outcomes_by_severity("high")
        assert len(high_severity) == 1
        assert high_severity[0].rule_id == "schema.not_null"

        medium_severity = result.get_outcomes_by_severity("medium")
        assert len(medium_severity) == 1
        assert medium_severity[0].rule_id == "threshold.completeness"

    def test_dq_result_immutability(self):
        """Test that DQResult remains immutable with new fields."""
        policy_ref = DQPolicyRef("test", "1.0.0", "1.0.0")
        outcome = DQRuleOutcome(
            "test", DQViolationKind.SCHEMA_VIOLATION, "high", DQDisposition.FAIL
        )

        result = DQResult(
            error_rate=0.1,
            status=DQEvaluationStatus.WARNING,
            rule_outcomes=(outcome,),
            policy_ref=policy_ref,
        )

        # Test that rule_outcomes is immutable
        with pytest.raises(Exception):  # frozen dataclass should prevent modification
            result.rule_outcomes = ()  # type: ignore

        # Test that policy_ref is immutable
        with pytest.raises(Exception):  # frozen dataclass should prevent modification
            result.policy_ref = None  # type: ignore

    def test_dq_result_serialization(self):
        """Test serialization of extended DQResult."""
        from dataclasses import asdict

        policy_ref = DQPolicyRef("chembl", "1.0.0", "1.0.0")
        outcome = DQRuleOutcome(
            "schema.not_null",
            DQViolationKind.SCHEMA_VIOLATION,
            "high",
            DQDisposition.FAIL,
        )

        result = DQResult(
            error_rate=0.15,
            status=DQEvaluationStatus.WARNING,
            rule_outcomes=(outcome,),
            policy_ref=policy_ref,
        )

        result_dict = asdict(result)

        # Check that all fields are serialized
        assert result_dict["error_rate"] == pytest.approx(0.15)
        assert result_dict["status"] == "warning"
        assert result_dict["policy_ref"]["contract_ref"] == "chembl"
        assert len(result_dict["rule_outcomes"]) == 1
        assert result_dict["rule_outcomes"][0]["rule_id"] == "schema.not_null"


class TestDQResultProperties:
    """Test property methods of extended DQResult."""

    def test_rule_outcomes_count_property(self):
        """Test rule_outcomes_count property."""
        outcomes = [
            DQRuleOutcome(
                "rule1", DQViolationKind.SCHEMA_VIOLATION, "high", DQDisposition.FAIL
            ),
            DQRuleOutcome(
                "rule2", DQViolationKind.THRESHOLD_BREACH, "medium", DQDisposition.WARN
            ),
        ]

        result = DQResult(
            error_rate=0.1,
            status=DQEvaluationStatus.WARNING,
            rule_outcomes=tuple(outcomes),
        )

        assert result.rule_outcomes_count == 2

    def test_has_rule_violations_property(self):
        """Test has_rule_violations property."""
        # Test with violations
        outcomes_with_violations = [
            DQRuleOutcome(
                "rule1", DQViolationKind.SCHEMA_VIOLATION, "high", DQDisposition.FAIL
            ),
            DQRuleOutcome(
                "rule2", DQViolationKind.THRESHOLD_BREACH, "medium", DQDisposition.WARN
            ),
        ]

        result_with_violations = DQResult(
            error_rate=0.1,
            status=DQEvaluationStatus.WARNING,
            rule_outcomes=tuple(outcomes_with_violations),
        )

        assert result_with_violations.has_rule_violations is True

        # Test without violations (only PASS dispositions)
        outcomes_without_violations = [
            DQRuleOutcome(
                "rule1", DQViolationKind.SCHEMA_VIOLATION, "low", DQDisposition.PASS
            ),
            DQRuleOutcome(
                "rule2", DQViolationKind.THRESHOLD_BREACH, "low", DQDisposition.PASS
            ),
        ]

        result_without_violations = DQResult(
            error_rate=0.0,
            status=DQEvaluationStatus.PASSED,
            rule_outcomes=tuple(outcomes_without_violations),
        )

        assert result_without_violations.has_rule_violations is False

        # Test with empty outcomes
        result_empty = DQResult(
            error_rate=0.0,
            status=DQEvaluationStatus.PASSED,
            rule_outcomes=(),
        )

        assert result_empty.has_rule_violations is False

    def test_has_quarantine_decisions_property(self):
        """Test has_quarantine_decisions property."""
        outcomes = [
            DQRuleOutcome(
                "rule1",
                DQViolationKind.SCHEMA_VIOLATION,
                "high",
                DQDisposition.QUARANTINE,
            ),
            DQRuleOutcome(
                "rule2", DQViolationKind.THRESHOLD_BREACH, "medium", DQDisposition.WARN
            ),
        ]

        result = DQResult(
            error_rate=0.1,
            status=DQEvaluationStatus.WARNING,
            rule_outcomes=tuple(outcomes),
        )

        assert result.has_quarantine_decisions is True

    def test_has_fail_decisions_property(self):
        """Test has_fail_decisions property."""
        outcomes = [
            DQRuleOutcome(
                "rule1", DQViolationKind.SCHEMA_VIOLATION, "high", DQDisposition.FAIL
            ),
            DQRuleOutcome(
                "rule2", DQViolationKind.THRESHOLD_BREACH, "medium", DQDisposition.WARN
            ),
        ]

        result = DQResult(
            error_rate=0.1,
            status=DQEvaluationStatus.FAILED,
            rule_outcomes=tuple(outcomes),
        )

        assert result.has_fail_decisions is True
