"""Unit tests for preflight governance service."""

from bioetl.domain.behavior.aggregation_validator import AggregationValidator
from bioetl.domain.behavior.composite_validation_layer import (
    CompositeValidationConfig,
    CompositeValidator,
)
from bioetl.domain.behavior.cross_validation_validator import CrossValidationValidator
from bioetl.domain.behavior.preflight_governance import (
    GovernancePolicy,
    PreflightGovernanceConfig,
    PreflightGovernor,
)
from bioetl.domain.types.validation_severity import ValidationSeverity


def _create_validation_service() -> CompositeValidator:
    return CompositeValidator(
        aggregation_validator=AggregationValidator(),
        cross_validation_validator=CrossValidationValidator(),
        preflight_governance=PreflightGovernor(),
    )


def test_preflight_governance_service_creation():
    """Test that governance service can be created."""
    service = PreflightGovernor()
    assert service.config.policy == GovernancePolicy.BLOCK_ON_BLOCKERS_ONLY


def test_custom_config():
    """Test service with custom configuration."""
    config = PreflightGovernanceConfig(
        policy=GovernancePolicy.CI_STRICT,
        ci_integration=True,
        fail_fast=False,
    )
    service = PreflightGovernor(config)
    assert service.config.policy == GovernancePolicy.CI_STRICT
    assert service.config.ci_integration is True
    assert service.config.fail_fast is False


def test_block_on_blockers_only_policy():
    """Test BLOCK_ON_BLOCKERS_ONLY policy (default)."""
    # Create a validation report with blockers
    validation_service = _create_validation_service()
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={"sources": ["source1"]},  # Missing required fields
    )
    validation_report = validation_service.validate_composite(config)

    # Apply governance
    governance_service = PreflightGovernor()
    governance_report = governance_service.apply_governance(validation_report)

    # Should block execution due to blockers
    decision = governance_report["execution_decision"]
    assert decision["execution_allowed"] is False
    assert decision["reason"] == "blocker_issues_found"
    assert decision["policy_applied"] == "block_on_blockers_only"


def test_block_on_any_issue_policy():
    """Test BLOCK_ON_ANY_ISSUE policy."""
    # Create a validation report with only warnings
    validation_service = _create_validation_service()
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={
            "sources": ["source1"],
            "merge_strategy": "prioritize",
            "output_schema": {"fields": ["field1"]},
            "field_priorities": "invalid",  # Will create warning
        },
    )
    validation_report = validation_service.validate_composite(config)

    # Apply strict governance
    governance_config = PreflightGovernanceConfig(
        policy=GovernancePolicy.BLOCK_ON_ANY_ISSUE
    )
    governance_service = PreflightGovernor(governance_config)
    governance_report = governance_service.apply_governance(validation_report)

    # Should block execution due to any issue
    decision = governance_report["execution_decision"]
    assert decision["execution_allowed"] is False
    assert decision["reason"] == "any_issue_found"


def test_warning_only_policy():
    """Test WARNING_ONLY policy."""
    # Create a validation report with blockers
    validation_service = _create_validation_service()
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={"sources": ["source1"]},  # Missing required fields
    )
    validation_report = validation_service.validate_composite(config)

    # Apply warning-only governance
    governance_config = PreflightGovernanceConfig(policy=GovernancePolicy.WARNING_ONLY)
    governance_service = PreflightGovernor(governance_config)
    governance_report = governance_service.apply_governance(validation_report)

    # Should allow execution despite blockers
    decision = governance_report["execution_decision"]
    assert decision["execution_allowed"] is True
    assert decision["reason"] == "warning_only_mode"


def test_ci_strict_policy():
    """Test CI_STRICT policy."""
    # Create a validation report with only warnings
    validation_service = _create_validation_service()
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={
            "sources": ["source1"],
            "merge_strategy": "prioritize",
            "output_schema": {"fields": ["field1"]},
            "field_priorities": "invalid",  # Will create warning
        },
    )
    validation_report = validation_service.validate_composite(config)

    # Apply CI strict governance
    governance_config = PreflightGovernanceConfig(
        policy=GovernancePolicy.CI_STRICT, ci_integration=True
    )
    governance_service = PreflightGovernor(governance_config)
    governance_report = governance_service.apply_governance(validation_report)

    # Should block execution due to any issue in CI strict mode
    decision = governance_report["execution_decision"]
    assert decision["execution_allowed"] is False
    assert decision["reason"] == "ci_strict_mode_violation"


def test_ci_relaxed_policy():
    """Test CI_RELAXED policy."""
    # Create a validation report with only warnings
    validation_service = _create_validation_service()
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={
            "sources": ["source1"],
            "merge_strategy": "prioritize",
            "output_schema": {"fields": ["field1"]},
            "field_priorities": "invalid",  # Will create warning
        },
    )
    validation_report = validation_service.validate_composite(config)

    # Apply CI relaxed governance
    governance_config = PreflightGovernanceConfig(
        policy=GovernancePolicy.CI_RELAXED, ci_integration=True
    )
    governance_service = PreflightGovernor(governance_config)
    governance_report = governance_service.apply_governance(validation_report)

    # Should allow execution with only warnings in CI relaxed mode
    decision = governance_report["execution_decision"]
    assert decision["execution_allowed"] is True


def test_issue_code_overrides():
    """Test issue code severity overrides."""
    # Create a validation report with blockers
    validation_service = _create_validation_service()
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={"sources": ["source1"]},  # Missing required fields
    )
    validation_report = validation_service.validate_composite(config)

    # Apply governance with overrides (downgrade blocker to warning)
    governance_config = PreflightGovernanceConfig(
        policy=GovernancePolicy.BLOCK_ON_BLOCKERS_ONLY,
        issue_code_overrides={
            "CMP-STR-CONFIG-002": ValidationSeverity.WARNING,  # Downgrade missing field
        },
    )
    governance_service = PreflightGovernor(governance_config)
    governance_report = governance_service.apply_governance(validation_report)

    # Should allow execution since blocker was downgraded
    decision = governance_report["execution_decision"]
    assert decision["execution_allowed"] is True


def test_governance_report_structure():
    """Test governance report structure and content."""
    # Create a validation report
    validation_service = _create_validation_service()
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={"sources": ["source1"]},
    )
    validation_report = validation_service.validate_composite(config)

    # Apply governance
    governance_service = PreflightGovernor()
    governance_report = governance_service.apply_governance(
        validation_report,
        execution_context={"environment": "test", "user": "test_user"},
    )

    # Verify report structure
    assert "governance_metadata" in governance_report
    assert "execution_decision" in governance_report
    assert "validation_summary" in governance_report
    assert "execution_context" in governance_report
    assert "detailed_issues" in governance_report

    # Verify metadata
    metadata = governance_report["governance_metadata"]
    assert metadata["policy"] == "block_on_blockers_only"
    assert metadata["ci_integration"] is False
    assert metadata["fail_fast"] is True
    assert "execution_timestamp" in metadata

    # Verify summary
    summary = governance_report["validation_summary"]
    assert summary["total_issues"] > 0
    assert summary["total_blockers"] > 0
    assert "layers" in summary

    # Verify execution context
    assert governance_report["execution_context"]["environment"] == "test"
    assert governance_report["execution_context"]["user"] == "test_user"

    # Verify detailed issues
    detailed_issues = governance_report["detailed_issues"]
    assert len(detailed_issues) > 0
    for issue in detailed_issues:
        assert "code" in issue
        assert "severity" in issue
        assert "layer" in issue
        assert "message" in issue
        assert "governance_impact" in issue


def test_ci_gate_report():
    """Test CI gate report generation."""
    # Create a validation report with blockers
    validation_service = _create_validation_service()
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={"sources": ["source1"]},
    )
    validation_report = validation_service.validate_composite(config)

    # Apply governance
    governance_service = PreflightGovernor()
    governance_report = governance_service.apply_governance(validation_report)

    # Create CI gate report
    ci_report = governance_service.create_ci_gate_report(governance_report)

    # Verify CI report structure
    assert "ci_gate" in ci_report
    assert "metrics" in ci_report
    assert "critical_issues" in ci_report

    # Verify CI gate status
    ci_gate = ci_report["ci_gate"]
    assert ci_gate["status"] == "FAIL"
    assert ci_gate["reason"] == "blocker_issues_found"

    # Verify metrics
    metrics = ci_report["metrics"]
    assert metrics["total_issues"] > 0
    assert metrics["blockers"] > 0

    # Verify critical issues
    critical_issues = ci_report["critical_issues"]
    assert len(critical_issues) > 0


def test_no_issues_scenario():
    """Test governance with no validation issues."""
    # Create a valid validation report
    validation_service = _create_validation_service()
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={
            "sources": ["source1", "source2"],
            "merge_strategy": "prioritize",
            "output_schema": {"fields": ["field1", "field2"]},
        },
    )
    validation_report = validation_service.validate_composite(config)

    # Apply governance
    governance_service = PreflightGovernor()
    governance_report = governance_service.apply_governance(validation_report)

    # Should allow execution with no issues
    decision = governance_report["execution_decision"]
    assert decision["execution_allowed"] is True
    assert decision["reason"] == "no_blocking_issues"

    # Verify summary shows no issues
    summary = governance_report["validation_summary"]
    assert summary["total_issues"] == 0
    assert summary["total_blockers"] == 0


def test_governance_impact_determination():
    """Test governance impact determination for different issue types."""
    # Create a validation report with mixed issues
    validation_service = _create_validation_service()
    config = CompositeValidationConfig(
        pipeline_name="test_pipeline",
        composite_config={
            "sources": ["source1"],  # Missing required fields - will create blockers
            # Missing merge_strategy and output_schema to trigger structural blockers
            "field_priorities": "invalid",  # Will create warning
        },
    )
    validation_report = validation_service.validate_composite(config)

    # Apply governance
    governance_service = PreflightGovernor()
    governance_report = governance_service.apply_governance(validation_report)

    # Check governance impacts
    detailed_issues = governance_report["detailed_issues"]

    blocker_issues = [
        issue
        for issue in detailed_issues
        if issue["governance_impact"] == "execution_blocker"
    ]
    warning_issues = [
        issue
        for issue in detailed_issues
        if issue["governance_impact"] == "warning_with_blocker_severity"
    ]
    informational_issues = [
        issue
        for issue in detailed_issues
        if issue["governance_impact"] == "informational"
    ]

    # Should have at least one execution blocker
    assert len(blocker_issues) > 0
    # Warning issues should be empty in default policy
    assert len(warning_issues) == 0
    # Should have one informational issue (the field priorities warning)
    assert len(informational_issues) == 1
