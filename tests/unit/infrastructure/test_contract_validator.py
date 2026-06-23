"""Unit tests for contract-aware validators."""

from __future__ import annotations

import pytest

import warnings

pytestmark = pytest.mark.unit

# Suppress Pandera deprecation warnings for cleaner test output
warnings.filterwarnings("ignore", category=FutureWarning, module="pandera")

from bioetl.domain.config.dq import DQConfig
from bioetl.domain.types.dq_contracts import DQDisposition, DQViolationKind
from bioetl.infrastructure.validation.contract_validator import (
    ContractAwareGoldValidator,
    ContractAwareSilverValidator,
)


class TestContractAwareGoldValidator:
    """Test contract-aware Gold validator."""

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

        validator = ContractAwareGoldValidator(
            schema=None, strict=False, dq_config=config
        )

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

        validator = ContractAwareGoldValidator(
            schema=None, strict=False, dq_config=config
        )
        summary = validator.get_policy_summary()

        assert summary["contract_ref"] == "pubmed_article"
        assert summary["contract_version"] == "2.0.0"
        assert summary["default_disposition"] == "quarantine"
        assert summary["strictness_mode"] == "strict"
        assert summary["policy_hash"] is not None

    def test_validation_without_schema(self):
        """Test validation when no schema is provided."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(
            schema=None, strict=False, dq_config=config
        )

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
        validator = ContractAwareGoldValidator(
            schema=None, strict=True, dq_config=config
        )

        is_valid, outcomes = validator.validate_with_outcomes([{"field": "value"}])
        assert is_valid is False
        assert len(outcomes) == 1
        assert outcomes[0].rule_id == "schema.missing"
        assert outcomes[0].violation_kind == DQViolationKind.SCHEMA_VIOLATION
        assert outcomes[0].severity == "high"


class TestContractAwareSilverValidator:
    """Test contract-aware Silver validator."""

    def test_aware_silver_validator__initialization__1f613ba2(self):
        """Test Silver validator initialization."""
        config = DQConfig(
            contract_ref="test_entity",
            contract_version="1.0.0",
        )

        validator = ContractAwareSilverValidator(schema=None, dq_config=config)

        assert validator.policy_ref is not None
        assert validator.policy_ref.contract_ref == "test_entity"

    def test_aware_silver_validator__policy_summary__1fd8532d(self):
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


class TestValidatorIntegration:
    """Integration tests for contract validators."""

    def test_gold_validator_with_schema_errors(self):
        """Test Gold validator handling of schema errors."""
        import pandera.pandas as pa

        # Create a simple schema
        schema = pa.DataFrameSchema(
            {
                "required_field": pa.Column(str, nullable=False),
                "optional_field": pa.Column(str, nullable=True),
            }
        )

        config = DQConfig(
            contract_ref="test_contract",
            contract_version="1.0.0",
            default_disposition_policy=DQDisposition.WARN,
            disposition_overrides={
                "schema.required_field": DQDisposition.FAIL,
            },
        )

        validator = ContractAwareGoldValidator(schema=schema, dq_config=config)

        # Test with missing required field
        records = [{"optional_field": "value"}]
        is_valid, outcomes = validator.validate_with_outcomes(records)

        assert is_valid is False
        assert len(outcomes) == 1
        assert outcomes[0].rule_id == "schema.required_field"
        assert outcomes[0].violation_kind == DQViolationKind.SCHEMA_VIOLATION
        assert outcomes[0].disposition == DQDisposition.FAIL  # Uses override
        assert outcomes[0].severity == "high"

    def test_gold_validator_with_valid_data(self):
        """Test Gold validator with valid data."""
        import pandera.pandas as pa

        # Create a simple schema
        schema = pa.DataFrameSchema(
            {
                "field1": pa.Column(str),
                "field2": pa.Column(int),
            }
        )

        config = DQConfig(
            contract_ref="test_contract",
            contract_version="1.0.0",
        )

        validator = ContractAwareGoldValidator(schema=schema, dq_config=config)

        # Test with valid data
        records = [
            {"field1": "test", "field2": 42},
            {"field1": "another", "field2": 100},
        ]
        is_valid, outcomes = validator.validate_with_outcomes(records)

        assert is_valid is True
        assert outcomes == []

    def test_policy_consistency(self):
        """Test that same configuration produces consistent results."""
        config = DQConfig(
            contract_ref="consistency_test",
            contract_version="1.0.0",
            rule_bundle_version="1.0.0",
            default_disposition_policy=DQDisposition.QUARANTINE,
            strictness_mode="strict",
        )

        validator1 = ContractAwareGoldValidator(schema=None, dq_config=config)
        validator2 = ContractAwareGoldValidator(schema=None, dq_config=config)

        summary1 = validator1.get_policy_summary()
        summary2 = validator2.get_policy_summary()

        assert summary1["policy_hash"] == summary2["policy_hash"]
        assert summary1["contract_ref"] == summary2["contract_ref"]


class TestSeverityDetermination:
    """Test severity determination logic."""

    def test_null_violation_severity(self):
        """Test that null violations get high severity."""
        import pandera.pandas as pa

        # Create a validator with a non-nullable field
        schema = pa.DataFrameSchema(
            {
                "non_null_field": pa.Column(str, nullable=False),
            }
        )

        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=schema, dq_config=config)

        # Create a record with null value
        records = [{"non_null_field": None}]
        is_valid, outcomes = validator.validate_with_outcomes(records)

        assert is_valid is False
        assert len(outcomes) == 1
        assert outcomes[0].severity == "high"

    def test_type_violation_severity(self):
        """Test that type violations get high severity."""
        import pandera.pandas as pa

        # Create a validator with a string field
        schema = pa.DataFrameSchema(
            {
                "string_field": pa.Column(str),
            }
        )

        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=schema, dq_config=config)

        # Create a record with wrong type
        records = [{"string_field": 123}]  # int instead of str
        is_valid, outcomes = validator.validate_with_outcomes(records)

        assert is_valid is False
        assert len(outcomes) == 1
        assert outcomes[0].severity == "high"

    def test_range_violation_severity(self):
        """Test that range violations get medium severity."""
        import pandera.pandas as pa

        # Create a validator with a range constraint
        schema = pa.DataFrameSchema(
            {
                "age": pa.Column(int, checks=pa.Check.in_range(0, 120)),
            }
        )

        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=schema, dq_config=config)

        # Create a record with out-of-range value
        records = [{"age": 150}]  # Too high
        is_valid, outcomes = validator.validate_with_outcomes(records)

        assert is_valid is False
        assert len(outcomes) == 1
        assert outcomes[0].severity == "medium"


class TestProvenanceInformation:
    """Test provenance information in outcomes."""

    def test_outcome_provenance(self):
        """Test that outcomes contain proper provenance information."""
        import pandera.pandas as pa

        schema = pa.DataFrameSchema(
            {
                "required_field": pa.Column(str, nullable=False),
            }
        )

        config = DQConfig(
            contract_ref="provenance_test",
            contract_version="2.0.0",
            rule_bundle_version="1.5.0",
        )

        validator = ContractAwareGoldValidator(schema=schema, dq_config=config)

        # Create invalid record
        records = [{"required_field": None}]
        is_valid, outcomes = validator.validate_with_outcomes(records)

        assert is_valid is False
        assert len(outcomes) == 1

        outcome = outcomes[0]
        assert outcome.rule_id == "schema.required_field"
        assert outcome.violation_kind == DQViolationKind.SCHEMA_VIOLATION
        assert outcome.affected_fields == ["required_field"]
        assert outcome.config_path == "contracts/provenance_test/dq_rules.yaml"
        assert outcome.policy_ref is not None
        assert outcome.policy_ref.contract_ref == "provenance_test"
        assert outcome.policy_ref.contract_version == "2.0.0"


class TestDispositionResolution:
    """Test disposition resolution in validators."""

    def test_disposition_override_applied(self):
        """Test that disposition overrides are applied correctly."""
        import pandera.pandas as pa

        schema = pa.DataFrameSchema(
            {
                "critical_field": pa.Column(str, nullable=False),
            }
        )

        config = DQConfig(
            default_disposition_policy=DQDisposition.WARN,
            disposition_overrides={
                "schema.critical_field": DQDisposition.FAIL,
            },
        )

        validator = ContractAwareGoldValidator(schema=schema, dq_config=config)

        # Create invalid record
        records = [{"critical_field": None}]
        is_valid, outcomes = validator.validate_with_outcomes(records)

        assert is_valid is False
        assert len(outcomes) == 1
        assert outcomes[0].disposition == DQDisposition.FAIL  # Override applied

    def test_default_disposition_applied(self):
        """Test that default disposition is applied when no override exists."""
        import pandera.pandas as pa

        schema = pa.DataFrameSchema(
            {
                "normal_field": pa.Column(str, nullable=False),
            }
        )

        config = DQConfig(
            default_disposition_policy=DQDisposition.QUARANTINE,
        )

        validator = ContractAwareGoldValidator(schema=schema, dq_config=config)

        # Create invalid record
        records = [{"normal_field": None}]
        is_valid, outcomes = validator.validate_with_outcomes(records)

        assert is_valid is False
        assert len(outcomes) == 1
        assert outcomes[0].disposition == DQDisposition.FAIL  # High severity escalates
