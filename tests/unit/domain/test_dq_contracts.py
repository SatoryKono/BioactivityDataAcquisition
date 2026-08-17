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
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Unit tests for DQ contract types."""

from __future__ import annotations

import pytest
from bioetl.domain.types.dq_contracts import (
    DQDisposition,
    DQViolationKind,
    DQPolicyRef,
    DQRuleOutcome,
    DQRuleProvenance,
    create_provenance_from_outcome,
)


pytestmark = pytest.mark.unit


class TestDQDisposition:
    """Test DQDisposition enum."""

    def test_disposition_values(self):
        """Test that all expected disposition values are present."""
        expected_values = {"pass", "warn", "quarantine", "skip", "fail"}
        actual_values = {d.value for d in DQDisposition}
        assert actual_values == expected_values

    def test_disposition_str_representation(self):
        """Test string representation of dispositions."""
        assert DQDisposition.PASS.value == "pass"
        assert DQDisposition.FAIL.value == "fail"


class TestDQViolationKind:
    """Test DQViolationKind enum."""

    def test_violation_kind_values(self):
        """Test that all expected violation kinds are present."""
        expected_values = {
            "schema_violation",
            "threshold_breach",
            "business_rule_violation",
            "cross_validation_mismatch",
            "anomaly_signal",
        }
        actual_values = {v.value for v in DQViolationKind}
        assert actual_values == expected_values


class TestDQPolicyRef:
    """Test DQPolicyRef dataclass."""

    def test_valid_policy_ref_creation(self):
        """Test creation of valid policy reference."""
        policy_ref = DQPolicyRef(
            contract_ref="chembl_molecule",
            contract_version="1.2.0",
            rule_bundle_version="2.1.0",
            policy_hash="abc123",
        )

        assert policy_ref.contract_ref == "chembl_molecule"
        assert policy_ref.contract_version == "1.2.0"
        assert policy_ref.rule_bundle_version == "2.1.0"
        assert policy_ref.policy_hash == "abc123"

    def test_d_q_policy_ref__ref_validation__f746d0a6(self):
        """Test validation of required fields."""
        with pytest.raises(ValueError, match="contract_ref cannot be empty"):
            DQPolicyRef("", "1.0.0", "1.0.0")

        with pytest.raises(ValueError, match="contract_version cannot be empty"):
            DQPolicyRef("test", "", "1.0.0")

        with pytest.raises(ValueError, match="rule_bundle_version cannot be empty"):
            DQPolicyRef("test", "1.0.0", "")

    def test_policy_ref_immutability(self):
        """Test that policy ref is immutable."""
        policy_ref = DQPolicyRef("test", "1.0.0", "1.0.0")

        with pytest.raises(Exception):  # frozen dataclass should prevent modification
            policy_ref.contract_ref = "new_value"  # type: ignore


class TestDQRuleOutcome:
    """Test DQRuleOutcome dataclass."""

    def test_valid_rule_outcome_creation(self):
        """Test creation of valid rule outcome."""
        outcome = DQRuleOutcome(
            rule_id="schema.not_null",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="high",
            disposition=DQDisposition.FAIL,
            disposition_reason="Field 'id' cannot be null",
            affected_fields=["id"],
            config_path="configs/quality/chembl.yaml",
        )

        assert outcome.rule_id == "schema.not_null"
        assert outcome.violation_kind == DQViolationKind.SCHEMA_VIOLATION
        assert outcome.severity == "high"
        assert outcome.disposition == DQDisposition.FAIL
        assert outcome.disposition_reason == "Field 'id' cannot be null"
        assert outcome.affected_fields == ("id",)
        assert outcome.config_path == "configs/quality/chembl.yaml"

    def test_d_q_rule_outcome__outcome_validation__bfc5d651(self):
        """Test validation of required fields."""
        with pytest.raises(ValueError, match="rule_id cannot be empty"):
            DQRuleOutcome(
                "", DQViolationKind.SCHEMA_VIOLATION, "high", DQDisposition.FAIL
            )

        with pytest.raises(ValueError, match="severity cannot be empty"):
            DQRuleOutcome(
                "test", DQViolationKind.SCHEMA_VIOLATION, "", DQDisposition.FAIL
            )

    def test_rule_outcome_immutability(self):
        """Test that rule outcome is immutable."""
        outcome = DQRuleOutcome(
            "test", DQViolationKind.SCHEMA_VIOLATION, "high", DQDisposition.FAIL
        )

        with pytest.raises(Exception):  # frozen dataclass should prevent modification
            outcome.rule_id = "new_value"  # type: ignore

    def test_affected_fields_default(self):
        """Test that affected_fields defaults to an empty tuple."""
        outcome = DQRuleOutcome(
            "test", DQViolationKind.SCHEMA_VIOLATION, "high", DQDisposition.FAIL
        )
        assert outcome.affected_fields == ()


class TestDQRuleProvenance:
    """Test DQRuleProvenance dataclass."""

    def test_valid_provenance_creation(self):
        """Test creation of valid provenance."""
        provenance = DQRuleProvenance(
            rule_id="schema.not_null",
            contract_version="1.2.0",
            severity="high",
            disposition=DQDisposition.FAIL,
            config_path="configs/quality/chembl.yaml",
            report_artifact_path="/reports/dq_report_20230101.json",
            policy_hash="abc123",
        )

        assert provenance.rule_id == "schema.not_null"
        assert provenance.contract_version == "1.2.0"
        assert provenance.severity == "high"
        assert provenance.disposition == DQDisposition.FAIL
        assert provenance.config_path == "configs/quality/chembl.yaml"
        assert provenance.report_artifact_path == "/reports/dq_report_20230101.json"
        assert provenance.policy_hash == "abc123"

    def test_provenance_validation(self):
        """Test validation of required fields."""
        with pytest.raises(ValueError, match="rule_id cannot be empty"):
            DQRuleProvenance("", "1.0.0", "high", DQDisposition.FAIL)

        with pytest.raises(ValueError, match="contract_version cannot be empty"):
            DQRuleProvenance("test", "", "high", DQDisposition.FAIL)

        with pytest.raises(ValueError, match="severity cannot be empty"):
            DQRuleProvenance("test", "1.0.0", "", DQDisposition.FAIL)

    def test_provenance_immutability(self):
        """Test that provenance is immutable."""
        provenance = DQRuleProvenance("test", "1.0.0", "high", DQDisposition.FAIL)

        with pytest.raises(Exception):  # frozen dataclass should prevent modification
            provenance.rule_id = "new_value"  # type: ignore


class TestProvenanceCreation:
    """Test provenance creation helper function."""

    def test_create_provenance_from_outcome(self):
        """Test creating provenance from rule outcome."""
        outcome = DQRuleOutcome(
            rule_id="threshold.completeness",
            violation_kind=DQViolationKind.THRESHOLD_BREACH,
            severity="medium",
            disposition=DQDisposition.WARN,
            affected_fields=["email"],
            config_path="configs/quality/common.yaml",
        )

        policy_ref = DQPolicyRef(
            contract_ref="pubmed_article",
            contract_version="2.0.0",
            rule_bundle_version="1.5.0",
            policy_hash="def456",
        )

        provenance = create_provenance_from_outcome(
            outcome, policy_ref, report_path="/reports/pubmed_dq_20230101.json"
        )

        assert provenance.rule_id == "threshold.completeness"
        assert provenance.contract_version == "2.0.0"
        assert provenance.severity == "medium"
        assert provenance.disposition == DQDisposition.WARN
        assert provenance.config_path == "configs/quality/common.yaml"
        assert provenance.report_artifact_path == "/reports/pubmed_dq_20230101.json"
        assert provenance.policy_hash == "def456"


class TestSerialization:
    """Test serialization of DQ contract types."""

    def test_policy_ref_serialization(self):
        """Test that policy ref can be serialized/deserialized."""
        import json
        from dataclasses import asdict

        policy_ref = DQPolicyRef("test", "1.0.0", "1.0.0", "abc123")

        # Convert to dict
        policy_dict = asdict(policy_ref)
        assert policy_dict == {
            "contract_ref": "test",
            "contract_version": "1.0.0",
            "rule_bundle_version": "1.0.0",
            "policy_hash": "abc123",
        }

        # Convert to JSON
        json_str = json.dumps(policy_dict)
        assert "test" in json_str
        assert "1.0.0" in json_str

    def test_rule_outcome_serialization(self):
        """Test that rule outcome can be serialized."""
        from dataclasses import asdict

        outcome = DQRuleOutcome(
            rule_id="test",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="high",
            disposition=DQDisposition.FAIL,
            affected_fields=["field1"],
        )

        outcome_dict = asdict(outcome)
        assert outcome_dict["rule_id"] == "test"
        assert outcome_dict["violation_kind"] == "schema_violation"
        assert outcome_dict["severity"] == "high"
        assert outcome_dict["disposition"] == "fail"
        assert list(outcome_dict["affected_fields"]) == ["field1"]
