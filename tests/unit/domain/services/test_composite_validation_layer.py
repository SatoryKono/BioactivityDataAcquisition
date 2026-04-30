"""Unit tests for composite validation layer service."""

from bioetl.domain.services.aggregation_validator import AggregationValidator
from bioetl.domain.services.composite_validation_layer import (
    CompositeValidationConfig,
    CompositeValidator,
)
from bioetl.domain.services.cross_validation_validator import CrossValidationValidator
from bioetl.domain.services.preflight_governance import (
    PreflightGovernor,
)
from bioetl.domain.types.validation_result import CompositeValidationReport
from bioetl.domain.types.validation_severity import (
    IssueCode,
    ValidationLayer,
    ValidationSeverity,
)


def _create_service() -> CompositeValidator:
    return CompositeValidator(
        aggregation_validator=AggregationValidator(),
        cross_validation_validator=CrossValidationValidator(),
        preflight_governance=PreflightGovernor(),
    )


def test_composite_validation_service_creation():
    """Test that validation service uses injected collaborators."""
    aggregation_validator = AggregationValidator()
    cross_validation_validator = CrossValidationValidator()
    preflight_governance = PreflightGovernor()

    service = CompositeValidator(
        aggregation_validator=aggregation_validator,
        cross_validation_validator=cross_validation_validator,
        preflight_governance=preflight_governance,
    )

    assert service._aggregation_validator is aggregation_validator
    assert service._cross_validation_validator is cross_validation_validator
    assert service._preflight_governance is preflight_governance


def test_composite_validation_service_uses_canonical_class() -> None:
    """Composite validation uses the canonical validator class."""
    assert _create_service().__class__ is CompositeValidator


def test_valid_composite_config():
    """Test validation of a valid composite configuration."""
    service = _create_service()
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={
            "sources": ["source1", "source2"],
            "merge_strategy": "prioritize",
            "output_schema": {"fields": ["field1", "field2", "group_field"]},
            "aggregation": {
                "group_by": ["group_field"],
                "aggregations": {"agg_field": "sum"},
            },
            "cross_validation": {
                "pairs": [{"source1": "source2"}],
                "rules": {"rule1": "strict"},
            },
            "lineage": {
                "tracking_level": "full",
                "source_fields": ["field1", "field2"],
            },
            "field_priorities": {
                "field1": {"priority": 1, "source": "source1"},
                "field2": {"priority": 2, "source": "source2"},
            },
        },
    )

    result = service.validate_composite(config)

    assert isinstance(result, CompositeValidationReport)
    assert not result.has_any_blockers()
    assert len(result.get_all_issues()) == 0


def test_missing_required_fields():
    """Test validation when required fields are missing."""
    service = _create_service()
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={
            "sources": ["source1"],
            # Missing merge_strategy and output_schema
        },
    )

    result = service.validate_composite(config)

    assert result.has_any_blockers()
    issues = result.get_all_blockers()
    assert len(issues) == 2

    issue_codes = [issue.code for issue in issues]
    assert IssueCode.CMP_STR_CONFIG_002 in issue_codes

    # Check that issues are in structural layer
    for issue in issues:
        assert issue.layer == ValidationLayer.STRUCTURAL
        assert issue.severity == ValidationSeverity.BLOCKER


def test_invalid_aggregation_config():
    """Test validation of invalid aggregation configuration."""
    service = _create_service()
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={
            "sources": ["source1"],
            "merge_strategy": "prioritize",
            "output_schema": {"fields": ["field1"]},
            "aggregation": {
                "group_by": ["group_field"],
                # Missing aggregations
            },
        },
    )

    result = service.validate_composite(config)

    assert result.has_any_blockers()
    issues = result.get_all_blockers()
    assert (
        len(issues) == 2
    )  # Both missing aggregations and missing group_by field in schema

    issue_codes = {issue.code for issue in issues}
    assert IssueCode.CMP_PF_AGG_002 in issue_codes  # Group_by field not found in schema
    assert IssueCode.CMP_PF_AGG_003 in issue_codes  # Missing aggregations

    for issue in issues:
        assert issue.layer == ValidationLayer.DEEP_PREFLIGHT


def test_invalid_cross_validation_config():
    """Test validation of invalid cross-validation configuration."""
    service = _create_service()
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={
            "sources": ["source1"],
            "merge_strategy": "prioritize",
            "output_schema": {"fields": ["field1"]},
            "cross_validation": {
                "pairs": [{"source1": "source2"}],
                # Missing rules
            },
        },
    )

    result = service.validate_composite(config)

    assert result.has_any_blockers()
    issues = result.get_all_blockers()
    assert len(issues) == 1
    assert issues[0].code == IssueCode.CMP_PF_CV_008  # Rules cannot be empty
    assert issues[0].layer == ValidationLayer.DEEP_PREFLIGHT


def test_conflicting_field_priorities():
    """Test detection of conflicting field priorities."""
    service = _create_service()
    # Create a config with invalid priority structure (not a dict)
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={
            "sources": ["source1"],
            "merge_strategy": "prioritize",
            "output_schema": {"fields": ["field1"]},
            "field_priorities": "invalid_string",  # Not a dict
        },
    )

    result = service.validate_composite(config)

    assert not result.has_any_blockers()  # Invalid structure is warning, not blocker
    warnings = result.deep_preflight_result.get_warnings()
    assert len(warnings) == 1
    assert warnings[0].code == IssueCode.CMP_PF_FIELD_001
    assert warnings[0].severity == ValidationSeverity.WARNING


def test_invalid_lineage_config():
    """Test validation of invalid lineage configuration."""
    service = _create_service()
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={
            "sources": ["source1"],
            "merge_strategy": "prioritize",
            "output_schema": {"fields": ["field1"]},
            "lineage": {
                "tracking_level": "full",
                # Missing source_fields
            },
        },
    )

    result = service.validate_composite(config)

    assert result.has_any_blockers()
    issues = result.get_all_blockers()
    assert len(issues) == 1
    assert issues[0].code == IssueCode.CMP_PF_LIN_001
    assert issues[0].layer == ValidationLayer.DEEP_PREFLIGHT


def test_ci_format_output():
    """Test CI/CD compatible format output."""
    service = _create_service()
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={
            "sources": ["source1"],
            # Missing required fields to trigger issues
        },
    )

    result = service.validate_composite(config)
    ci_format = result.to_ci_format()

    assert "validation_layers" in ci_format
    assert "structural" in ci_format["validation_layers"]
    assert "deep_preflight" in ci_format["validation_layers"]
    assert "summary" in ci_format

    summary = ci_format["summary"]
    assert summary["total_issues"] > 0
    assert summary["total_blockers"] > 0
    assert summary["execution_blocked"] is True


def test_layer_separation():
    """Test that validation layers are properly separated."""
    service = _create_service()
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={
            "sources": ["source1"],  # Missing required fields (structural)
            "aggregation": {
                "group_by": ["field"]
            },  # Missing aggregations (deep preflight)
        },
    )

    result = service.validate_composite(config)

    # Structural layer should have issues
    structural_issues = result.structural_result.issues
    assert len(structural_issues) > 0
    for issue in structural_issues:
        assert issue.layer == ValidationLayer.STRUCTURAL

    # Deep preflight layer should have issues
    deep_issues = result.deep_preflight_result.issues
    assert len(deep_issues) > 0
    for issue in deep_issues:
        assert issue.layer == ValidationLayer.DEEP_PREFLIGHT

    # Runtime guard should be None (not run during preflight)
    assert result.runtime_guard_result is None


def test_preflight_governance_integration():
    """Test that preflight governance is properly integrated."""
    from bioetl.domain.services.preflight_governance import GovernancePolicy

    # Test with default governance policy
    service = _create_service()
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={
            "sources": ["source1"],  # Missing required fields
            "aggregation": {"group_by": ["field"]},
        },
        governance_policy=GovernancePolicy.BLOCK_ON_BLOCKERS_ONLY,
    )
    result = service.validate_composite(config)

    # Verify that execution_decision is present
    assert result.execution_decision is not None
    assert "governance_metadata" in result.execution_decision
    assert "execution_decision" in result.execution_decision
    assert "validation_summary" in result.execution_decision

    # Check governance metadata
    governance_metadata = result.execution_decision["governance_metadata"]
    assert governance_metadata["policy"] == "block_on_blockers_only"

    # Check execution decision
    execution_decision = result.execution_decision["execution_decision"]
    assert "execution_allowed" in execution_decision
    # Should block because there are blocker issues
    assert execution_decision["execution_allowed"] is False


def test_preflight_governance_warning_only():
    """Test warning-only governance policy."""
    from bioetl.domain.services.preflight_governance import GovernancePolicy

    service = _create_service()
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={
            "sources": ["source1"],  # Missing required fields
            "aggregation": {"group_by": ["field"]},
        },
        governance_policy=GovernancePolicy.WARNING_ONLY,
    )
    result = service.validate_composite(config)

    # Warning only should allow execution even with issues
    assert result.execution_decision is not None
    governance_metadata = result.execution_decision["governance_metadata"]
    assert governance_metadata["policy"] == "warning_only"

    execution_decision = result.execution_decision["execution_decision"]
    assert execution_decision["execution_allowed"] is True
