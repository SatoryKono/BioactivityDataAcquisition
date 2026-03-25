"""Simplified unit tests for contract-aware validators focusing on core functionality."""

from __future__ import annotations

from bioetl.domain.config.dq import DQConfig
from bioetl.domain.types.dq_contracts import DQDisposition, DQViolationKind
from bioetl.infrastructure.validation.contract_validator import (
    ContractAwareGoldValidator,
    ContractAwareSilverValidator,
)


class TestContractAwareGoldValidatorSimple:
    """Test contract-aware Gold validator - simplified tests."""

    def test_initialization_without_config(self):
        """Test initialization without DQ config."""
        validator = ContractAwareGoldValidator(schema=None, strict=False)
        
        assert validator.policy_ref is None
        assert validator._policy_resolver is None

    def test_initialization_with_config(self):
        """Test initialization with DQ config."""
        config = DQConfig(
            contract_ref="chembl_molecule",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            default_disposition_policy=DQDisposition.WARN,
        )
        
        validator = ContractAwareGoldValidator(schema=None, strict=False, dq_config=config)
        
        assert validator.policy_ref is not None
        assert validator.policy_ref.contract_ref == "chembl_molecule"
        assert validator._policy_resolver is not None

    def test_policy_summary(self):
        """Test getting policy summary."""
        config = DQConfig(
            contract_ref="pubmed_article",
            contract_version="2.0.0",
            rule_bundle_version="1.5.0",
            default_disposition_policy=DQDisposition.QUARANTINE,
            strictness_mode="strict",
        )
        
        validator = ContractAwareGoldValidator(schema=None, strict=False, dq_config=config)
        summary = validator.get_policy_summary()
        
        assert summary["contract_ref"] == "pubmed_article"
        assert summary["contract_version"] == "2.0.0"
        assert summary["default_disposition"] == "quarantine"
        assert summary["strictness_mode"] == "strict"
        assert summary["policy_hash"] is not None

    def test_validation_without_schema(self):
        """Test validation when no schema is provided."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, strict=False, dq_config=config)
        
        is_valid, outcomes = validator.validate_with_outcomes([])
        assert is_valid is True
        assert outcomes == []

    def test_validation_without_config_fallback(self):
        """Test fallback behavior when no DQ config is provided."""
        validator = ContractAwareGoldValidator(schema=None, strict=False)
        
        is_valid, outcomes = validator.validate_with_outcomes([])
        assert is_valid is True
        assert outcomes == []

    def test_strict_mode_without_schema(self):
        """Test strict mode behavior when schema is missing."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, strict=True, dq_config=config)
        
        is_valid, outcomes = validator.validate_with_outcomes([{"field": "value"}])
        assert is_valid is False
        assert len(outcomes) == 1
        assert outcomes[0].rule_id == "schema.missing"
        assert outcomes[0].violation_kind == DQViolationKind.SCHEMA_VIOLATION
        assert outcomes[0].severity == "high"

    def test_policy_resolver_integration(self):
        """Test that policy resolver is properly integrated."""
        config = DQConfig(
            contract_ref="test_contract",
            contract_version="1.0.0",
            default_disposition_policy=DQDisposition.WARN,
            disposition_overrides={
                "schema.critical_field": DQDisposition.FAIL,
            },
        )
        
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)
        
        # Test that policy resolver can create outcomes
        outcome = validator._policy_resolver.create_rule_outcome(
            rule_id="test.rule",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="high",
        )
        
        assert outcome.rule_id == "test.rule"
        assert outcome.violation_kind == DQViolationKind.SCHEMA_VIOLATION
        assert outcome.severity == "high"
        # Should be escalated from WARN to QUARANTINE due to high severity
        assert outcome.disposition == DQDisposition.QUARANTINE

    def test_disposition_override(self):
        """Test that disposition overrides work correctly."""
        config = DQConfig(
            default_disposition_policy=DQDisposition.WARN,
            disposition_overrides={
                "schema.critical_field": DQDisposition.FAIL,
            },
        )
        
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)
        
        # Test override
        outcome = validator._policy_resolver.create_rule_outcome(
            rule_id="schema.critical_field",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="medium",
        )
        
        assert outcome.disposition == DQDisposition.FAIL  # Override applied

    def test_policy_hash_consistency(self):
        """Test that same configuration produces consistent policy hashes."""
        config1 = DQConfig(
            contract_ref="test",
            contract_version="1.0.0",
            default_disposition_policy=DQDisposition.WARN,
        )
        
        config2 = DQConfig(
            contract_ref="test",
            contract_version="1.0.0",
            default_disposition_policy=DQDisposition.WARN,
        )
        
        validator1 = ContractAwareGoldValidator(schema=None, dq_config=config1)
        validator2 = ContractAwareGoldValidator(schema=None, dq_config=config2)
        
        hash1 = validator1.policy_ref.policy_hash
        hash2 = validator2.policy_ref.policy_hash
        
        assert hash1 == hash2


class TestContractAwareSilverValidatorSimple:
    """Test contract-aware Silver validator - simplified tests."""

    def test_initialization(self):
        """Test Silver validator initialization."""
        config = DQConfig(
            contract_ref="test_entity",
            contract_version="1.0.0",
        )
        
        validator = ContractAwareSilverValidator(schema=None, dq_config=config)
        
        assert validator.policy_ref is not None
        assert validator.policy_ref.contract_ref == "test_entity"

    def test_policy_summary(self):
        """Test Silver validator policy summary."""
        config = DQConfig(
            contract_ref="chembl_assay",
            contract_version="1.5.0",
            default_disposition_policy=DQDisposition.WARN,
        )
        
        validator = ContractAwareSilverValidator(schema=None, dq_config=config)
        summary = validator.get_policy_summary()
        
        assert summary["contract_ref"] == "chembl_assay"
        assert summary["contract_version"] == "1.5.0"
        assert summary["default_disposition"] == "warn"

    def test_validation_fallback(self):
        """Test Silver validator fallback behavior."""
        validator = ContractAwareSilverValidator(schema=None)
        
        is_valid, outcomes = validator.validate_with_outcomes([])
        assert is_valid is True
        assert outcomes == []


class TestProvenanceInformationSimple:
    """Test provenance information in outcomes - simplified."""

    def test_outcome_provenance(self):
        """Test that outcomes contain proper provenance information."""
        config = DQConfig(
            contract_ref="provenance_test",
            contract_version="2.0.0",
            rule_bundle_version="1.5.0",
        )
        
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)
        
        # Create a test outcome using the policy resolver
        config_path = "contracts/provenance_test/dq_rules.yaml"
        outcome = validator._policy_resolver.create_rule_outcome(
            rule_id="schema.required_field",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="high",
            affected_fields=["required_field"],
            config_path=config_path,
        )
        
        assert outcome.rule_id == "schema.required_field"
        assert outcome.violation_kind == DQViolationKind.SCHEMA_VIOLATION
        assert outcome.affected_fields == ["required_field"]
        assert outcome.config_path == config_path
        # Test policy ref separately
        assert validator.policy_ref is not None
        assert validator.policy_ref.contract_ref == "provenance_test"
        assert validator.policy_ref.contract_version == "2.0.0"


class TestDispositionResolutionSimple:
    """Test disposition resolution in validators - simplified."""

    def test_disposition_override_applied(self):
        """Test that disposition overrides are applied correctly."""
        config = DQConfig(
            default_disposition_policy=DQDisposition.WARN,
            disposition_overrides={
                "schema.critical_field": DQDisposition.FAIL,
            },
        )
        
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)
        
        outcome = validator._policy_resolver.create_rule_outcome(
            rule_id="schema.critical_field",
            violation_kind=DQViolationKind.BUSINESS_RULE_VIOLATION,
            severity="high",
        )
        
        assert outcome.disposition == DQDisposition.FAIL  # Override applied

    def test_default_disposition_applied(self):
        """Test that default disposition is applied when no override exists."""
        config = DQConfig(
            default_disposition_policy=DQDisposition.QUARANTINE,
        )
        
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)
        
        outcome = validator._policy_resolver.create_rule_outcome(
            rule_id="schema.normal_field",
            violation_kind=DQViolationKind.THRESHOLD_BREACH,
            severity="medium",
        )
        
        assert outcome.disposition == DQDisposition.QUARANTINE  # Default applied

    def test_strict_mode_escalation(self):
        """Test that strict mode escalates dispositions."""
        config = DQConfig(
            default_disposition_policy=DQDisposition.WARN,
            strictness_mode="strict",
        )
        
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)
        
        outcome = validator._policy_resolver.create_rule_outcome(
            rule_id="schema.test_field",
            violation_kind=DQViolationKind.SCHEMA_VIOLATION,
            severity="medium",
        )
        
        # WARN -> QUARANTINE due to strict mode
        assert outcome.disposition == DQDisposition.QUARANTINE

    def test_lenient_mode_de_escalation(self):
        """Test that lenient mode de-escalates dispositions."""
        config = DQConfig(
            default_disposition_policy=DQDisposition.QUARANTINE,
            strictness_mode="lenient",
        )
        
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)
        
        outcome = validator._policy_resolver.create_rule_outcome(
            rule_id="schema.test_field",
            violation_kind=DQViolationKind.THRESHOLD_BREACH,
            severity="medium",
        )
        
        # QUARANTINE -> WARN due to lenient mode
        assert outcome.disposition == DQDisposition.WARN