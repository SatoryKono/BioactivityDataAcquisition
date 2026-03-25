"""Unit tests for CrossValidationValidator service."""

from __future__ import annotations

import pytest

from bioetl.domain.services.cross_validation_validator import (
    CrossValidationConfig,
    CrossValidationValidator,
)
from bioetl.domain.types.validation_result import ValidationResult
from bioetl.domain.types.validation_severity import IssueCode, ValidationLayer, ValidationSeverity


class TestCrossValidationValidator:
    """Tests for CrossValidationValidator."""

    @pytest.fixture
    def validator(self) -> CrossValidationValidator:
        """Create a CrossValidationValidator instance."""
        return CrossValidationValidator()

    @pytest.fixture
    def valid_config(self) -> CrossValidationConfig:
        """Create a valid cross-validation configuration."""
        return CrossValidationConfig(
            pairs=[{"source1": "source2"}],
            rules={"rule1": "strict"},
        )

    @pytest.fixture
    def source_names(self) -> list[str]:
        """Create a list of source names."""
        return ["source1", "source2", "source3"]

    # ==========================================================================
    # validate_cross_validation_config() tests
    # ==========================================================================

    def test_validate_valid_config(self, validator: CrossValidationValidator, valid_config: CrossValidationConfig, source_names: list[str]) -> None:
        """Test validation of a completely valid configuration."""
        # Disable strict mode to avoid coverage warning for this test
        valid_config = CrossValidationConfig(
            pairs=[{"source1": "source2"}],
            rules={"rule1": "strict"},
            strict_mode=False,  # Disable strict mode
        )
        result = validator.validate_cross_validation_config(valid_config, source_names)
        
        assert result.issues == []
        assert result.validation_layer == ValidationLayer.DEEP_PREFLIGHT
        assert result.is_valid()

    def test_validate_empty_pairs(self, validator: CrossValidationValidator, source_names: list[str]) -> None:
        """Test validation when pairs are empty."""
        config = CrossValidationConfig(
            pairs=[],  # Empty pairs
            rules={"rule1": "strict"},
        )
        
        result = validator.validate_cross_validation_config(config, source_names)
        
        assert len(result.issues) == 2  # Empty pairs + coverage warning
        issue_codes = {issue.code for issue in result.issues}
        assert IssueCode.CMP_PF_CV_002 in issue_codes  # Empty pairs
        assert IssueCode.CMP_PF_CV_013 in issue_codes  # Coverage warning
        assert not result.is_valid()

    def test_validate_empty_rules(self, validator: CrossValidationValidator, source_names: list[str]) -> None:
        """Test validation when rules are empty."""
        config = CrossValidationConfig(
            pairs=[{"source1": "source2"}],
            rules={},  # Empty rules
        )
        
        result = validator.validate_cross_validation_config(config, source_names)
        
        assert len(result.issues) == 2  # Empty rules + coverage warning
        issue_codes = {issue.code for issue in result.issues}
        assert IssueCode.CMP_PF_CV_008 in issue_codes  # Empty rules
        assert IssueCode.CMP_PF_CV_013 in issue_codes  # Coverage warning
        assert not result.is_valid()

    def test_validate_invalid_pair_structure(self, validator: CrossValidationValidator, source_names: list[str]) -> None:
        """Test validation when pair is not a dictionary."""
        config = CrossValidationConfig(
            pairs=["invalid_pair"],  # Not a dictionary
            rules={"rule1": "strict"},
        )
        
        result = validator.validate_cross_validation_config(config, source_names)
        
        assert len(result.issues) == 2  # Invalid structure + coverage warning
        issue_codes = {issue.code for issue in result.issues}
        assert IssueCode.CMP_PF_CV_003 in issue_codes  # Invalid structure
        assert IssueCode.CMP_PF_CV_013 in issue_codes  # Coverage warning
        assert not result.is_valid()

    def test_validate_pair_with_multiple_mappings(self, validator: CrossValidationValidator, source_names: list[str]) -> None:
        """Test validation when pair has multiple source mappings."""
        config = CrossValidationConfig(
            pairs=[{"source1": "source2", "source3": "source2"}],  # Multiple mappings
            rules={"rule1": "strict"},
        )
        
        result = validator.validate_cross_validation_config(config, source_names)
        
        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.CMP_PF_CV_004
        assert result.issues[0].severity == ValidationSeverity.BLOCKER
        assert "exactly one source mapping" in result.issues[0].message
        assert not result.is_valid()

    def test_validate_source_not_in_sources(self, validator: CrossValidationValidator, source_names: list[str]) -> None:
        """Test validation when source is not in pipeline sources."""
        config = CrossValidationConfig(
            pairs=[{"nonexistent_source": "source2"}],
            rules={"rule1": "strict"},
        )
        
        result = validator.validate_cross_validation_config(config, source_names)
        
        assert len(result.issues) == 2  # Source not found + coverage warning
        issue_codes = {issue.code for issue in result.issues}
        assert IssueCode.CMP_PF_CV_005 in issue_codes  # Source not found
        assert IssueCode.CMP_PF_CV_013 in issue_codes  # Coverage warning
        assert not result.is_valid()

    def test_validate_comparison_source_not_in_sources(self, validator: CrossValidationValidator, source_names: list[str]) -> None:
        """Test validation when comparison source is not in pipeline sources."""
        config = CrossValidationConfig(
            pairs=[{"source1": "nonexistent_source"}],
            rules={"rule1": "strict"},
        )
        
        result = validator.validate_cross_validation_config(config, source_names)
        
        assert len(result.issues) == 2  # Comparison source not found + coverage warning
        issue_codes = {issue.code for issue in result.issues}
        assert IssueCode.CMP_PF_CV_007 in issue_codes  # Comparison source not found
        assert IssueCode.CMP_PF_CV_013 in issue_codes  # Coverage warning
        assert not result.is_valid()

    def test_validate_invalid_rule_type(self, validator: CrossValidationValidator, source_names: list[str]) -> None:
        """Test validation when rule type is not a string."""
        config = CrossValidationConfig(
            pairs=[{"source1": "source2"}],
            rules={"rule1": 123},  # Not a string
        )
        
        result = validator.validate_cross_validation_config(config, source_names)
        
        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.CMP_PF_CV_009
        assert result.issues[0].severity == ValidationSeverity.BLOCKER
        assert "must be a string type" in result.issues[0].message
        assert not result.is_valid()

    def test_validate_unsupported_rule_type(self, validator: CrossValidationValidator, source_names: list[str]) -> None:
        """Test validation when rule type is not supported."""
        config = CrossValidationConfig(
            pairs=[{"source1": "source2"}],
            rules={"rule1": "invalid_type"},
        )
        
        result = validator.validate_cross_validation_config(config, source_names)
        
        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.CMP_PF_CV_010
        assert result.issues[0].severity == ValidationSeverity.BLOCKER
        assert "Unsupported cross-validation rule type" in result.issues[0].message
        assert not result.is_valid()

    def test_validate_invalid_coverage_threshold(self, validator: CrossValidationValidator, source_names: list[str]) -> None:
        """Test validation when coverage threshold is out of range."""
        config = CrossValidationConfig(
            pairs=[{"source1": "source2"}],
            rules={"rule1": "strict"},
            coverage_threshold=1.5,  # > 1.0
        )
        
        result = validator.validate_cross_validation_config(config, source_names)
        
        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.CMP_PF_CV_011
        assert result.issues[0].severity == ValidationSeverity.BLOCKER
        assert "must be between 0.0 and 1.0" in result.issues[0].message
        assert not result.is_valid()

    def test_validate_invalid_consistency_threshold(self, validator: CrossValidationValidator, source_names: list[str]) -> None:
        """Test validation when consistency threshold is out of range."""
        config = CrossValidationConfig(
            pairs=[{"source1": "source2"}],
            rules={"rule1": "strict"},
            consistency_threshold=-0.1,  # < 0.0
        )
        
        result = validator.validate_cross_validation_config(config, source_names)
        
        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.CMP_PF_CV_012
        assert result.issues[0].severity == ValidationSeverity.BLOCKER
        assert "must be between 0.0 and 1.0" in result.issues[0].message
        assert not result.is_valid()

    def test_validate_coverage_warning(self, validator: CrossValidationValidator, source_names: list[str]) -> None:
        """Test validation when not all sources are covered in strict mode."""
        config = CrossValidationConfig(
            pairs=[{"source1": "source2"}],  # Missing source3
            rules={"rule1": "strict"},
            strict_mode=True,
        )
        
        result = validator.validate_cross_validation_config(config, source_names)
        
        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.CMP_PF_CV_013
        assert result.issues[0].severity == ValidationSeverity.WARNING
        assert "does not cover all sources" in result.issues[0].message
        # Should still be valid since it's just a warning
        assert result.is_valid()

    def test_validate_multiple_issues(self, validator: CrossValidationValidator, source_names: list[str]) -> None:
        """Test validation with multiple issues."""
        config = CrossValidationConfig(
            pairs=[{"nonexistent_source": "also_nonexistent"}],
            rules={"rule1": "invalid_type"},
        )
        
        result = validator.validate_cross_validation_config(config, source_names)
        
        # Should have multiple issues
        assert len(result.issues) >= 2
        assert not result.is_valid()
        
        issue_codes = {issue.code for issue in result.issues}
        assert IssueCode.CMP_PF_CV_005 in issue_codes  # Source not found
        assert IssueCode.CMP_PF_CV_007 in issue_codes  # Comparison source not found
        assert IssueCode.CMP_PF_CV_010 in issue_codes  # Unsupported rule type

    def test_validate_with_list_comparison_sources(self, validator: CrossValidationValidator, source_names: list[str]) -> None:
        """Test validation with list comparison sources."""
        config = CrossValidationConfig(
            pairs=[{"source1": ["source2", "source3"]}],  # List of comparison sources
            rules={"rule1": "strict"},
        )
        
        result = validator.validate_cross_validation_config(config, source_names)
        
        assert result.issues == []
        assert result.is_valid()

    def test_validate_supported_rule_types(self, validator: CrossValidationValidator, source_names: list[str]) -> None:
        """Test all supported rule types."""
        supported_types = ["strict", "lenient", "warn", "custom"]
        
        for rule_type in supported_types:
            config = CrossValidationConfig(
                pairs=[{"source1": "source2"}],
                rules={"rule1": rule_type},
            )
            result = validator.validate_cross_validation_config(config, source_names)
            assert result.is_valid(), f"Rule type {rule_type} should be supported"

    def test_factory_function(self) -> None:
        """Test the factory function."""
        validator = create_cross_validation_validator()
        assert isinstance(validator, CrossValidationValidator)


# Helper function for easier testing

def create_cross_validation_validator() -> CrossValidationValidator:
    """Factory function for CrossValidationValidator."""
    return CrossValidationValidator()