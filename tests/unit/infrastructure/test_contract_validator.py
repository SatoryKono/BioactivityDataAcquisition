# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for contract-aware validators."""

from __future__ import annotations

from unittest.mock import patch

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

    def test_validation_without_schema_and_nonempty_records_in_nonstrict_mode(self):
        """Non-strict mode should accept records when no schema has been configured."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(
            schema=None, strict=False, dq_config=config
        )

        is_valid, outcomes = validator.validate_with_outcomes([{"field": "value"}])
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
        assert outcome.affected_fields == ("required_field",)
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


class TestInternalMethods:
    """Test internal helper methods for better coverage."""

    def test_prepare_df_for_validation_with_missing_nullable(self):
        """Test _prepare_df_for_validation adds missing nullable columns."""
        import pandera.pandas as pa

        schema = pa.DataFrameSchema(
            {
                "required_field": pa.Column(str, nullable=False),
                "optional_field": pa.Column(str, nullable=True),
            }
        )

        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=schema, dq_config=config)

        import pandas as pd

        df = pd.DataFrame({"required_field": ["value"]})
        prepared = validator._prepare_df_for_validation(df)

        assert "optional_field" in prepared.columns
        assert prepared["optional_field"].isna().all()

    def test_extract_schema_error_field_name_with_column_name(self):
        """Test _extract_schema_error_field_name extracts column_name attribute."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        # Create a mock error with column_name
        class MockError:
            column_name = "test_field"

        field_name = validator._extract_schema_error_field_name(MockError())
        assert field_name == "test_field"

    def test_extract_schema_error_field_name_with_failure_cases(self):
        """Test _extract_schema_error_field_name extracts failure_cases."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        class MockError:
            failure_cases = "test_field"

        field_name = validator._extract_schema_error_field_name(MockError())
        assert field_name == "test_field"

    def test_extract_schema_error_field_name_with_loc(self):
        """Test _extract_schema_error_field_name extracts loc attribute."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        class MockError:
            loc = "test_field"

        field_name = validator._extract_schema_error_field_name(MockError())
        assert field_name == "test_field"

    def test_extract_schema_error_field_name_with_message(self):
        """Test _extract_schema_error_field_name parses error message."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        class MockError:
            def __str__(self):
                return "Expected column 'my_field' to be present"

        field_name = validator._extract_schema_error_field_name(MockError())
        assert field_name == "my_field"

    def test_extract_schema_error_field_name_with_empty_message_match(self):
        """Empty extracted column names should fall back to ``None``."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        class MockError:
            def __str__(self):
                return "Expected column '' to be present"

        field_name = validator._extract_schema_error_field_name(MockError())
        assert field_name is None

    def test_extract_schema_error_field_name_fallback(self):
        """Test _extract_schema_error_field_name returns None when no info found."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        class MockError:
            def __str__(self):
                return "Some generic error"

        field_name = validator._extract_schema_error_field_name(MockError())
        assert field_name is None

    def test_determine_severity_null_violation(self):
        """Test _determine_severity returns high for null violations."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        class MockError:
            def __str__(self):
                return "Expected column to not have null values"

        severity = validator._determine_severity(MockError())
        assert severity == "high"

    def test_determine_severity_type_violation(self):
        """Test _determine_severity returns high for type violations."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        class MockError:
            def __str__(self):
                return "Expected type str but got int"

        severity = validator._determine_severity(MockError())
        assert severity == "high"

    def test_determine_severity_regex_violation(self):
        """Test _determine_severity returns medium for regex violations."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        class MockError:
            def __str__(self):
                return "Value does not match regex pattern"

        severity = validator._determine_severity(MockError())
        assert severity == "medium"

    def test_determine_severity_range_violation(self):
        """Test _determine_severity returns medium for range violations."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        class MockError:
            def __str__(self):
                return "Value is outside min-max range"

        severity = validator._determine_severity(MockError())
        assert severity == "medium"

    def test_determine_severity_default(self):
        """Test _determine_severity returns high as default."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        class MockError:
            def __str__(self):
                return "Some unknown error"

        severity = validator._determine_severity(MockError())
        assert severity == "high"

    def test_get_config_path_with_policy_ref(self):
        """Test _get_config_path returns path when policy_ref exists."""
        config = DQConfig(contract_ref="test_contract")
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        path = validator._get_config_path()
        assert path == "contracts/test_contract/dq_rules.yaml"

    def test_get_config_path_without_policy_ref(self):
        """Test _get_config_path returns None when no policy_ref."""
        validator = ContractAwareGoldValidator(schema=None, strict=False)

        path = validator._get_config_path()
        assert path is None

    def test_policy_summary_without_policy_resolver(self):
        """Gold validator without DQ config should expose an empty policy summary."""
        validator = ContractAwareGoldValidator(schema=None, strict=False)

        assert validator.get_policy_summary() == {
            "contract_ref": None,
            "policy_hash": None,
        }

    def test_apply_contract_validations_gold_contract(self):
        """Test _apply_contract_validations for Gold contracts."""
        import pandas as pd

        config = DQConfig(contract_ref="gold_molecule")
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        df = pd.DataFrame({"field": ["value"]})
        outcomes = validator._apply_contract_validations(df)

        # Currently placeholder, should return empty list
        assert outcomes == []

    def test_apply_contract_validations_non_gold_contract(self):
        """Test _apply_contract_validations for non-Gold contracts."""
        import pandas as pd

        config = DQConfig(contract_ref="silver_entity")
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        df = pd.DataFrame({"field": ["value"]})
        outcomes = validator._apply_contract_validations(df)

        # Currently placeholder, should return empty list
        assert outcomes == []

    def test_prepare_df_for_validation_without_schema_columns_attribute(self):
        """Schemas without a ``columns`` attribute should still be reordered cleanly."""
        import pandas as pd

        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)
        validator._schema = object()  # type: ignore[assignment]

        df = pd.DataFrame({"required_field": ["value"]})
        prepared = validator._prepare_df_for_validation(df)

        assert list(prepared.columns) == ["required_field"]

    def test_validate_with_outcomes_empty_records(self):
        """Test validation with empty records list."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        is_valid, outcomes = validator.validate_with_outcomes([])
        assert is_valid is True
        assert outcomes == []

    def test_validate_with_outcomes_key_error_in_schema(self):
        """Test handling of KeyError during schema validation."""
        import pandera.pandas as pa

        schema = pa.DataFrameSchema({"field": pa.Column(str)})
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=schema, dq_config=config)

        # Mock schema validation to raise KeyError
        with patch.object(schema, "validate", side_effect=KeyError("missing_key")):
            is_valid, outcomes = validator.validate_with_outcomes([{"field": "test"}])
            assert is_valid is False
            assert len(outcomes) > 0

    def test_validate_with_outcomes_type_error_in_schema(self):
        """Test handling of TypeError during schema validation."""
        import pandera.pandas as pa

        schema = pa.DataFrameSchema({"field": pa.Column(str)})
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=schema, dq_config=config)

        # Mock schema validation to raise TypeError
        with patch.object(schema, "validate", side_effect=TypeError("type_error")):
            is_valid, outcomes = validator.validate_with_outcomes([{"field": "test"}])
            assert is_valid is False
            assert len(outcomes) > 0

    def test_validate_with_outcomes_value_error_in_schema(self):
        """Test handling of ValueError during schema validation."""
        import pandera.pandas as pa

        schema = pa.DataFrameSchema({"field": pa.Column(str)})
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=schema, dq_config=config)

        # Mock schema validation to raise ValueError
        with patch.object(schema, "validate", side_effect=ValueError("value_error")):
            is_valid, outcomes = validator.validate_with_outcomes([{"field": "test"}])
            assert is_valid is False
            assert len(outcomes) > 0

    def test_convert_schema_errors_with_complex_loc(self):
        """Test _convert_schema_errors_to_outcomes with complex loc."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        class MockError:
            loc = ["field1", "field2", "index"]

        outcomes = validator._convert_schema_errors_to_outcomes(MockError())
        assert len(outcomes) == 1
        assert outcomes[0].rule_id == "schema.field1.field2.index"

    def test_convert_schema_errors_with_list_loc(self):
        """Test _convert_schema_errors_to_outcomes with list loc."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        class MockError:
            loc = ["field1", 0]

        outcomes = validator._convert_schema_errors_to_outcomes(MockError())
        assert len(outcomes) == 1

    def test_prepare_df_with_schema_none(self):
        """Test _prepare_df_for_validation when schema is None."""
        import pandas as pd

        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        df = pd.DataFrame({"field1": ["value"], "field2": [42]})
        # When schema is None, _prepare_df_for_validation should raise an assertion error
        # because _reorder_to_schema requires a non-None schema
        with pytest.raises(AssertionError):
            validator._prepare_df_for_validation(df)

    def test_silver_validator_validate_with_outcomes(self):
        """Test Silver validator validate_with_outcomes method."""
        config = DQConfig(contract_ref="test_silver")
        validator = ContractAwareSilverValidator(schema=None, dq_config=config)

        is_valid, outcomes = validator.validate_with_outcomes([])
        assert is_valid is True
        assert outcomes == []

    def test_silver_validator_without_config(self):
        """Test Silver validator without DQ config."""
        validator = ContractAwareSilverValidator(schema=None)

        assert validator.policy_ref is None
        assert validator._policy_resolver is None

    def test_validate_with_outcomes_multiple_errors(self):
        """Test validation with multiple schema errors."""
        import pandera.pandas as pa

        schema = pa.DataFrameSchema(
            {
                "field1": pa.Column(str, nullable=False),
                "field2": pa.Column(int, nullable=False),
            }
        )

        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=schema, dq_config=config)

        # Create records with multiple violations
        records = [{"field1": None, "field2": None}]
        is_valid, outcomes = validator.validate_with_outcomes(records)

        assert is_valid is False
        # Should have outcomes for each violation
        assert len(outcomes) >= 1

    def test_validate_with_outcomes_quarantine_disposition(self):
        """Test that quarantine disposition is handled correctly."""
        import pandera.pandas as pa

        schema = pa.DataFrameSchema({"field": pa.Column(str, nullable=False)})

        config = DQConfig(
            default_disposition_policy=DQDisposition.QUARANTINE,
        )

        validator = ContractAwareGoldValidator(schema=schema, dq_config=config)

        records = [{"field": None}]
        is_valid, outcomes = validator.validate_with_outcomes(records)

        assert is_valid is False
        assert len(outcomes) == 1

    def test_extract_schema_error_with_empty_message(self):
        """Test _extract_schema_error_field_name with empty message."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        class MockError:
            def __str__(self):
                return ""

        field_name = validator._extract_schema_error_field_name(MockError())
        assert field_name is None

    def test_extract_schema_error_with_no_column_marker(self):
        """Test _extract_schema_error_field_name without column marker."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        class MockError:
            def __str__(self):
                return "Some error without column reference"

        field_name = validator._extract_schema_error_field_name(MockError())
        assert field_name is None

    def test_determine_severity_unknown_marker(self):
        """Test _determine_severity with unknown error marker."""
        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=None, dq_config=config)

        class MockError:
            def __str__(self):
                return "Unknown error type"

        severity = validator._determine_severity(MockError())
        assert severity == "high"  # Default

    def test_reorder_to_schema_preserves_data(self):
        """Test that _reorder_to_schema preserves data integrity."""
        import pandas as pd
        import pandera.pandas as pa

        schema = pa.DataFrameSchema(
            {"field2": pa.Column(int), "field1": pa.Column(str)}
        )

        config = DQConfig()
        validator = ContractAwareGoldValidator(schema=schema, dq_config=config)

        df = pd.DataFrame({"field1": ["a", "b"], "field2": [1, 2]})
        prepared = validator._prepare_df_for_validation(df)

        # Data should be preserved
        assert len(prepared) == len(df)
        assert list(prepared["field1"]) == list(df["field1"])
        assert list(prepared["field2"]) == list(df["field2"])

    def test_contract_validations_with_none_policy_ref(self):
        """Test _apply_contract_validations when policy_ref is None."""
        import pandas as pd

        validator = ContractAwareGoldValidator(schema=None, strict=False)

        df = pd.DataFrame({"field": ["value"]})
        outcomes = validator._apply_contract_validations(df)

        assert outcomes == []

    def test_get_config_path_returns_none_without_policy_ref(self):
        """Test _get_config_path when policy_ref is None."""
        validator = ContractAwareGoldValidator(schema=None, strict=False)

        path = validator._get_config_path()
        assert path is None

    def test_silver_validator_policy_summary_without_config(self):
        """Test Silver validator policy summary without config."""
        validator = ContractAwareSilverValidator(schema=None)

        summary = validator.get_policy_summary()
        assert summary["contract_ref"] is None
        assert summary["policy_hash"] is None
