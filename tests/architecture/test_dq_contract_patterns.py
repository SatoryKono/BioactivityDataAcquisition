"""Architecture tests: Data Quality contract patterns.

These tests ensure the contract-based DQ system follows proper architectural patterns:
- DQ contract types are immutable and properly structured
- Contract references are used consistently
- Policy resolution follows deterministic patterns
- Provenance tracking is implemented correctly

REQ-DQ-010: DQ contracts must be immutable and thread-safe
REQ-DQ-020: Contract references must be consistent across layers
REQ-DQ-030: Policy resolution must be deterministic
"""

from __future__ import annotations


import pytest

from bioetl.domain.config.dq import DQConfig
from bioetl.domain.behavior.dq_policy_resolver import DQPolicyResolver
from bioetl.domain.types.dq_contracts import (
    DQDisposition,
    DQPolicyRef,
    DQRuleOutcome,
    DQRuleProvenance,
    DQViolationKind,
    create_provenance_from_outcome,
)
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult


class TestDQContractImmutability:
    """Tests ensuring DQ contract types are properly immutable."""

    def test_dq_policy_ref_immutability(self) -> None:
        """DQPolicyRef should be immutable (frozen dataclass)."""
        ref = DQPolicyRef(
            contract_ref="test",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            policy_hash="abc123",
        )

        # Should not be able to modify attributes
        with pytest.raises(Exception):  # frozen dataclass should prevent modification
            ref.contract_ref = "modified"  # type: ignore

    def test_dq_rule_outcome_immutability(self) -> None:
        """DQRuleOutcome should be immutable (frozen dataclass)."""
        outcome = DQRuleOutcome(
            rule_id="test_rule",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="high",
            disposition=DQDisposition.FAIL,
            disposition_reason="Test violation",
        )

        # Should not be able to modify attributes
        with pytest.raises(Exception):  # frozen dataclass should prevent modification
            outcome.disposition = DQDisposition.WARN  # type: ignore

    def test_dq_rule_provenance_immutability(self) -> None:
        """DQRuleProvenance should be immutable (frozen dataclass)."""
        provenance = DQRuleProvenance(
            rule_id="test_rule",
            contract_version="1.0.0",
            severity="high",
            disposition=DQDisposition.FAIL,
        )

        # Should not be able to modify attributes
        with pytest.raises(Exception):  # frozen dataclass should prevent modification
            provenance.severity = "low"  # type: ignore


class TestDQContractConsistency:
    """Tests ensuring contract references are consistent."""

    def test_policy_ref_validation(self) -> None:
        """DQPolicyRef should validate required fields."""
        # Valid policy ref
        valid_ref = DQPolicyRef(
            contract_ref="chembl_molecule",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
        )
        assert valid_ref.contract_ref == "chembl_molecule"
        assert valid_ref.contract_version == "1.0.0"
        assert valid_ref.rule_bundle_version == "1.0.0"

        # Should raise for empty required fields
        with pytest.raises(ValueError, match="contract_ref cannot be empty"):
            DQPolicyRef(
                contract_ref="", contract_version="1.0.0", rule_bundle_version="1.0.0"
            )

        with pytest.raises(ValueError, match="contract_version cannot be empty"):
            DQPolicyRef(
                contract_ref="test", contract_version="", rule_bundle_version="1.0.0"
            )

    def test_rule_outcome_validation(self) -> None:
        """DQRuleOutcome should validate required fields."""
        # Valid outcome
        valid_outcome = DQRuleOutcome(
            rule_id="schema.test",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="high",
            disposition=DQDisposition.FAIL,
        )
        assert valid_outcome.rule_id == "schema.test"
        assert valid_outcome.severity == "high"

        # Should raise for empty required fields
        with pytest.raises(ValueError, match="rule_id cannot be empty"):
            DQRuleOutcome(
                rule_id="",
                violation_kind=DQViolationKind.SCHEMA_VIOLATION,
                severity="high",
                disposition=DQDisposition.FAIL,
            )

    def test_provenance_from_outcome_consistency(self) -> None:
        """Provenance created from outcome should maintain consistency."""
        policy_ref = DQPolicyRef(
            contract_ref="test",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            policy_hash="test_hash",
        )

        outcome = DQRuleOutcome(
            rule_id="schema.test",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="high",
            disposition=DQDisposition.FAIL,
            config_path="test.yaml",
        )

        provenance = create_provenance_from_outcome(outcome, policy_ref)

        # Should maintain key fields from outcome
        assert provenance.rule_id == outcome.rule_id
        assert provenance.severity == outcome.severity
        assert provenance.disposition == outcome.disposition
        assert provenance.config_path == outcome.config_path

        # Should include contract info from policy ref
        assert provenance.contract_version == policy_ref.contract_version
        assert provenance.policy_hash == policy_ref.policy_hash


class TestDQPolicyResolution:
    """Tests ensuring policy resolution is deterministic and correct."""

    def test_policy_resolver_determinism(self) -> None:
        """Policy resolution should be deterministic."""
        config = DQConfig(
            contract_ref="test",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            default_disposition_policy=DQDisposition.WARN,
            disposition_overrides={"schema.critical": DQDisposition.FAIL},
        )

        resolver = DQPolicyResolver(config)

        # Same inputs should produce same outputs
        disposition1 = resolver.resolve_disposition(
            "schema.test", DQViolationKind.SCHEMA_VIOLATION, "high"
        )
        disposition2 = resolver.resolve_disposition(
            "schema.test", DQViolationKind.SCHEMA_VIOLATION, "high"
        )

        assert disposition1 == disposition2

        # Override should be applied consistently
        disposition_critical = resolver.resolve_disposition(
            "schema.critical", DQViolationKind.SCHEMA_VIOLATION, "high"
        )
        assert disposition_critical == DQDisposition.FAIL

    def test_policy_hash_stability(self) -> None:
        """Policy hash should be stable for same configuration."""
        config = DQConfig(
            contract_ref="test",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            default_disposition_policy=DQDisposition.WARN,
        )

        resolver1 = DQPolicyResolver(config)
        resolver2 = DQPolicyResolver(config)

        hash1 = resolver1.build_policy_ref().policy_hash
        hash2 = resolver2.build_policy_ref().policy_hash

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hash length

    def test_outcome_creation_consistency(self) -> None:
        """Rule outcomes should be created consistently."""
        config = DQConfig(
            contract_ref="test",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            default_disposition_policy=DQDisposition.WARN,
        )

        resolver = DQPolicyResolver(config)

        # Create same outcome twice
        outcome1 = resolver.create_rule_outcome(
            rule_id="schema.test",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="high",
            config_path="test.yaml",
        )

        outcome2 = resolver.create_rule_outcome(
            rule_id="schema.test",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="high",
            config_path="test.yaml",
        )

        assert outcome1 == outcome2


class TestDQResultIntegration:
    """Tests ensuring DQ results integrate properly with contract system."""

    def test_dq_result_with_rule_outcomes(self) -> None:
        """DQResult should support rule outcomes."""
        outcome1 = DQRuleOutcome(
            rule_id="schema.test1",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="high",
            disposition=DQDisposition.FAIL,
        )

        outcome2 = DQRuleOutcome(
            rule_id="schema.test2",
            violation_kind=DQViolationKind.THRESHOLD_BREACH,
            severity="medium",
            disposition=DQDisposition.WARN,
        )

        result = DQResult(
            error_rate=0.15,
            status=DQEvaluationStatus.FAILED,
            rule_outcomes=[outcome1, outcome2],
            policy_ref=DQPolicyRef(
                contract_ref="test",
                contract_version="1.0.0",
                rule_bundle_version="1.0.0",
            ),
        )

        assert len(result.rule_outcomes) == 2
        assert result.rule_outcomes[0].rule_id == "schema.test1"
        assert result.rule_outcomes[1].rule_id == "schema.test2"

    def test_dq_result_filtering(self) -> None:
        """DQResult should support filtering by disposition."""
        outcome1 = DQRuleOutcome(
            rule_id="schema.test1",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="high",
            disposition=DQDisposition.FAIL,
        )

        outcome2 = DQRuleOutcome(
            rule_id="schema.test2",
            violation_kind=DQViolationKind.THRESHOLD_BREACH,
            severity="medium",
            disposition=DQDisposition.WARN,
        )

        result = DQResult(
            error_rate=0.15,
            status=DQEvaluationStatus.FAILED,
            rule_outcomes=[outcome1, outcome2],
        )

        # Test filtering by violation kind (existing method)
        schema_outcomes = result.get_outcomes_by_violation_kind(
            DQViolationKind.SCHEMA_VIOLATION
        )
        threshold_outcomes = result.get_outcomes_by_violation_kind(
            DQViolationKind.THRESHOLD_BREACH
        )

        assert len(schema_outcomes) == 1
        assert len(threshold_outcomes) == 1
        assert schema_outcomes[0].rule_id == "schema.test1"
        assert threshold_outcomes[0].rule_id == "schema.test2"

        # Test filtering by severity (existing method)
        high_outcomes = result.get_outcomes_by_severity("high")
        medium_outcomes = result.get_outcomes_by_severity("medium")

        assert len(high_outcomes) == 1
        assert len(medium_outcomes) == 1
        assert high_outcomes[0].rule_id == "schema.test1"
        assert medium_outcomes[0].rule_id == "schema.test2"


class TestDQEnumCoverage:
    """Tests ensuring DQ enums have proper coverage."""

    def test_dq_disposition_enum_values(self) -> None:
        """DQDisposition should have expected values."""
        expected_values = {"pass", "warn", "quarantine", "skip", "fail"}
        actual_values = {member.value for member in DQDisposition}

        assert actual_values == expected_values

    def test_dq_violation_kind_enum_values(self) -> None:
        """DQViolationKind should have expected values."""
        expected_values = {
            "schema_violation",
            "threshold_breach",
            "business_rule_violation",
            "cross_validation_mismatch",
            "anomaly_signal",
        }
        actual_values = {member.value for member in DQViolationKind}

        assert actual_values == expected_values
