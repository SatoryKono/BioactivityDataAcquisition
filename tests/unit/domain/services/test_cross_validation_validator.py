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
"""Unit tests for CrossValidationValidator service."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.cross_validation_validator import (
    CrossValidationConfig,
    CrossValidationValidator,
)
from bioetl.domain.types.validation_severity import (
    IssueCode,
    ValidationLayer,
    ValidationSeverity,
)


pytestmark = pytest.mark.unit


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

    def test_validation_validator__valid_config__93a72da6(
        self,
        validator: CrossValidationValidator,
        source_names: list[str],
    ) -> None:
        """Test validation of a completely valid configuration."""
        # Disable strict mode to avoid coverage warning for this test
        config = CrossValidationConfig(
            pairs=[{"source1": "source2"}],
            rules={"rule1": "strict"},
            strict_mode=False,  # Disable strict mode
        )
        result = validator.validate_cross_validation_config(config, source_names)

        assert result.issues == []
        assert result.validation_layer == ValidationLayer.DEEP_PREFLIGHT
        assert result.is_valid()

    def test_validate_empty_pairs(
        self, validator: CrossValidationValidator, source_names: list[str]
    ) -> None:
        """Test validation when pairs are empty."""
        config = CrossValidationConfig(
            pairs=[],  # Empty pairs
            rules={"rule1": "strict"},
        )

        result = validator.validate_cross_validation_config(config, source_names)

        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.CMP_PF_CV_002  # Empty pairs
        assert not result.is_valid()

    def test_validate_empty_rules(
        self, validator: CrossValidationValidator, source_names: list[str]
    ) -> None:
        """Test validation when rules are empty."""
        config = CrossValidationConfig(
            pairs=[{"source1": "source2"}],
            rules={},  # Empty rules
        )

        result = validator.validate_cross_validation_config(config, source_names)

        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.CMP_PF_CV_008  # Empty rules
        assert not result.is_valid()

    def test_validate_invalid_pair_structure(
        self, validator: CrossValidationValidator, source_names: list[str]
    ) -> None:
        """Test validation when pair is not a dictionary."""
        config = CrossValidationConfig(
            pairs=["invalid_pair"],  # Not a dictionary
            rules={"rule1": "strict"},
        )

        result = validator.validate_cross_validation_config(config, source_names)

        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.CMP_PF_CV_003  # Invalid structure
        assert not result.is_valid()

    def test_validate_pair_with_multiple_mappings(
        self, validator: CrossValidationValidator, source_names: list[str]
    ) -> None:
        """Test validation when pair has multiple source mappings."""
        config = CrossValidationConfig(
            pairs=[{"source1": "source2", "source3": "source2"}],  # Multiple mappings
            rules={"rule1": "strict"},
        )

        result = validator.validate_cross_validation_config(config, source_names)

        assert len(result.issues) == 1
        main_issue = next(
            issue for issue in result.issues if issue.code == IssueCode.CMP_PF_CV_004
        )
        assert main_issue.severity == ValidationSeverity.BLOCKER
        assert "exactly one source mapping" in main_issue.message
        assert not result.is_valid()

    def test_validate_source_not_in_sources(
        self, validator: CrossValidationValidator, source_names: list[str]
    ) -> None:
        """Test validation when source is not in pipeline sources."""
        config = CrossValidationConfig(
            pairs=[{"nonexistent_source": "source2"}],
            rules={"rule1": "strict"},
        )

        result = validator.validate_cross_validation_config(config, source_names)

        assert len(result.issues) == 1
        assert result.issues[0].code == IssueCode.CMP_PF_CV_005  # Source not found
        assert not result.is_valid()

    def test_validate_comparison_source_not_in_sources(
        self, validator: CrossValidationValidator, source_names: list[str]
    ) -> None:
        """Test validation when comparison source is not in pipeline sources."""
        config = CrossValidationConfig(
            pairs=[{"source1": "nonexistent_source"}],
            rules={"rule1": "strict"},
        )

        result = validator.validate_cross_validation_config(config, source_names)

        assert len(result.issues) == 1
        assert (
            result.issues[0].code == IssueCode.CMP_PF_CV_007
        )  # Comparison source not found
        assert not result.is_valid()

    def test_validate_invalid_rule_type(
        self, validator: CrossValidationValidator, source_names: list[str]
    ) -> None:
        """Test validation when rule type is not a string."""
        config = CrossValidationConfig(
            pairs=[{"source1": "source2"}],
            rules={"rule1": 123},  # Not a string
        )

        result = validator.validate_cross_validation_config(config, source_names)

        assert len(result.issues) == 1
        main_issue = next(
            issue for issue in result.issues if issue.code == IssueCode.CMP_PF_CV_009
        )
        assert main_issue.severity == ValidationSeverity.BLOCKER
        assert "must be a string type" in main_issue.message
        assert not result.is_valid()

    def test_validate_unsupported_rule_type(
        self, validator: CrossValidationValidator, source_names: list[str]
    ) -> None:
        """Test validation when rule type is not supported."""
        config = CrossValidationConfig(
            pairs=[{"source1": "source2"}],
            rules={"rule1": "invalid_type"},
        )

        result = validator.validate_cross_validation_config(config, source_names)

        assert len(result.issues) == 1
        main_issue = next(
            issue for issue in result.issues if issue.code == IssueCode.CMP_PF_CV_010
        )
        assert main_issue.severity == ValidationSeverity.BLOCKER
        assert "Unsupported cross-validation rule type" in main_issue.message
        assert not result.is_valid()

    def test_validate_invalid_coverage_threshold(
        self, validator: CrossValidationValidator, source_names: list[str]
    ) -> None:
        """Test validation when coverage threshold is out of range."""
        config = CrossValidationConfig(
            pairs=[{"source1": "source2"}],
            rules={"rule1": "strict"},
            coverage_threshold=1.5,  # > 1.0
        )

        result = validator.validate_cross_validation_config(config, source_names)

        assert len(result.issues) == 1
        main_issue = next(
            issue for issue in result.issues if issue.code == IssueCode.CMP_PF_CV_011
        )
        assert main_issue.severity == ValidationSeverity.BLOCKER
        assert "must be between 0.0 and 1.0" in main_issue.message
        assert not result.is_valid()

    def test_validate_invalid_consistency_threshold(
        self, validator: CrossValidationValidator, source_names: list[str]
    ) -> None:
        """Test validation when consistency threshold is out of range."""
        config = CrossValidationConfig(
            pairs=[{"source1": "source2"}],
            rules={"rule1": "strict"},
            consistency_threshold=-0.1,  # < 0.0
        )

        result = validator.validate_cross_validation_config(config, source_names)

        assert len(result.issues) == 1
        main_issue = next(
            issue for issue in result.issues if issue.code == IssueCode.CMP_PF_CV_012
        )
        assert main_issue.severity == ValidationSeverity.BLOCKER
        assert "must be between 0.0 and 1.0" in main_issue.message
        assert not result.is_valid()

    def test_validate_coverage_warning(
        self, validator: CrossValidationValidator, source_names: list[str]
    ) -> None:
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

    def test_validation_validator__multiple_issues__81e4d29c(
        self, validator: CrossValidationValidator, source_names: list[str]
    ) -> None:
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

    def test_validate_with_list_comparison_sources(
        self, validator: CrossValidationValidator, source_names: list[str]
    ) -> None:
        """Test validation with list comparison sources."""
        config = CrossValidationConfig(
            pairs=[{"source1": ["source2", "source3"]}],  # List of comparison sources
            rules={"rule1": "strict"},
        )

        result = validator.validate_cross_validation_config(config, source_names)

        assert result.issues == []
        assert result.is_valid()

    def test_validate_supported_rule_types(
        self, validator: CrossValidationValidator, source_names: list[str]
    ) -> None:
        """Test all supported rule types."""
        supported_types = ["strict", "lenient", "warn", "custom"]

        for rule_type in supported_types:
            config = CrossValidationConfig(
                pairs=[{"source1": "source2"}],
                rules={"rule1": rule_type},
            )
            result = validator.validate_cross_validation_config(config, source_names)
            assert result.is_valid(), f"Rule type {rule_type} should be supported"

    def test_constructor(self) -> None:
        """Test the constructor."""
        validator = CrossValidationValidator()
        assert isinstance(validator, CrossValidationValidator)


class TestCrossValidationDisposition:
    """Tests for cross-validation disposition policies."""

    def test_warning_only_policy_downgrades_blockers(self) -> None:
        """Test that WARNING_ONLY policy downgrades blocker issues to warnings."""
        from bioetl.domain.behavior.cross_validation_validator import (
            CrossValidationConfig,
            CrossValidationDispositionPolicy,
            CrossValidationValidator,
        )

        validator = CrossValidationValidator()
        source_names = ["source1", "source2", "source3"]

        # Create a validation result with blocker issues
        config = CrossValidationConfig(
            pairs=[
                {"source1": "source2", "source3": "source2"}
            ],  # Multiple mappings - blocker
            rules={"rule1": "strict"},
            disposition_policy=CrossValidationDispositionPolicy.WARNING_ONLY,
        )
        validation_result = validator.validate_cross_validation_config(
            config, source_names
        )

        # Apply WARNING_ONLY disposition
        disposed_result = validator.apply_disposition(validation_result, config)

        # Should have issues but no blockers
        assert (
            len(disposed_result.issues) == 1
        )  # Only the main issue (coverage warning filtered out)
        assert not disposed_result.has_blockers()

        # Check that blocker was downgraded
        main_issue = next(
            issue
            for issue in disposed_result.issues
            if issue.code == IssueCode.CMP_PF_CV_004
        )
        assert main_issue.severity == ValidationSeverity.WARNING
        assert "downgraded from blocker" in main_issue.message
        assert main_issue.details.get("original_severity") == "blocker"
        assert main_issue.details.get("disposition") == "downgraded"

    def test_quarantine_policy_adds_metadata(self) -> None:
        """Test that QUARANTINE policy keeps blockers but adds quarantine metadata."""
        from bioetl.domain.behavior.cross_validation_validator import (
            CrossValidationConfig,
            CrossValidationDispositionPolicy,
            CrossValidationValidator,
        )

        validator = CrossValidationValidator()
        source_names = ["source1", "source2", "source3"]

        # Create a validation result with blocker issues
        config = CrossValidationConfig(
            pairs=[
                {"source1": "source2", "source3": "source2"}
            ],  # Multiple mappings - blocker
            rules={"rule1": "strict"},
            disposition_policy=CrossValidationDispositionPolicy.QUARANTINE,
        )
        validation_result = validator.validate_cross_validation_config(
            config, source_names
        )

        # Apply QUARANTINE disposition
        disposed_result = validator.apply_disposition(validation_result, config)

        # Should still have blockers
        assert len(disposed_result.issues) == 1  # Only the main issue
        assert disposed_result.has_blockers()

        # Check that blocker has quarantine metadata
        main_issue = next(
            issue
            for issue in disposed_result.issues
            if issue.code == IssueCode.CMP_PF_CV_004
        )
        assert main_issue.severity == ValidationSeverity.BLOCKER
        assert "quarantined" in main_issue.message
        assert main_issue.details.get("disposition") == "quarantined"
        assert main_issue.details.get("quarantine_reason") == "cross_validation_failure"

    def test_fail_policy_keeps_blockers(self) -> None:
        """Test that FAIL policy keeps blockers with fail metadata."""
        from bioetl.domain.behavior.cross_validation_validator import (
            CrossValidationConfig,
            CrossValidationDispositionPolicy,
            CrossValidationValidator,
        )

        validator = CrossValidationValidator()
        source_names = ["source1", "source2", "source3"]

        # Create a validation result with blocker issues
        config = CrossValidationConfig(
            pairs=[
                {"source1": "source2", "source3": "source2"}
            ],  # Multiple mappings - blocker
            rules={"rule1": "strict"},
            disposition_policy=CrossValidationDispositionPolicy.FAIL,  # Default
        )
        validation_result = validator.validate_cross_validation_config(
            config, source_names
        )

        # Apply FAIL disposition (default)
        disposed_result = validator.apply_disposition(validation_result, config)

        # Should still have blockers
        assert len(disposed_result.issues) == 1  # Only the main issue
        assert disposed_result.has_blockers()

        # Check that blocker has fail metadata
        main_issue = next(
            issue
            for issue in disposed_result.issues
            if issue.code == IssueCode.CMP_PF_CV_004
        )
        assert main_issue.severity == ValidationSeverity.BLOCKER
        assert "will fail execution" in main_issue.message
        assert main_issue.details.get("disposition") == "fail"
        assert main_issue.details.get("execution_blocked") is True

    def test_disposition_with_no_issues(self) -> None:
        """Test that disposition with no issues returns unchanged result."""
        from bioetl.domain.behavior.cross_validation_validator import (
            CrossValidationConfig,
            CrossValidationDispositionPolicy,
            CrossValidationValidator,
        )

        validator = CrossValidationValidator()
        source_names = ["source1", "source2"]

        # Create a valid config
        config = CrossValidationConfig(
            pairs=[{"source1": "source2"}],
            rules={"rule1": "strict"},
            disposition_policy=CrossValidationDispositionPolicy.WARNING_ONLY,
        )
        validation_result = validator.validate_cross_validation_config(
            config, source_names
        )

        # Apply disposition - should return unchanged result
        disposed_result = validator.apply_disposition(validation_result, config)

        # Should be identical (no issues since coverage is complete)
        assert len(disposed_result.issues) == 0
        assert disposed_result.issues == validation_result.issues


# Helper function for easier testing
