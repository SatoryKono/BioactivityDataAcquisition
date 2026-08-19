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
"""Unit tests for composite validation layer behavior."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.aggregation_validator import AggregationValidator
from bioetl.domain.behavior.composite_validation_helpers import (
    _extract_priority,
    _is_valid_lineage_config,
)
from bioetl.domain.behavior.composite_validation_layer import (
    CompositeValidationConfig,
    CompositeValidator,
)
from bioetl.domain.behavior.cross_validation_validator import CrossValidationValidator
from bioetl.domain.behavior.preflight_governance import PreflightGovernor
from bioetl.domain.types.validation_severity import IssueCode

pytestmark = pytest.mark.unit


def _validator() -> CompositeValidator:
    return CompositeValidator(
        aggregation_validator=AggregationValidator(),
        cross_validation_validator=CrossValidationValidator(),
        preflight_governance=PreflightGovernor(),
    )


def test_structural_validation_reports_non_dict_and_missing_required_fields() -> None:
    result = _validator()._run_structural_validation(
        CompositeValidationConfig(
            pipeline_name="composite",
            composite_config=[],  # type: ignore[arg-type]
        )
    )

    codes = [issue.code for issue in result.issues]
    # Non-dict payload fails closed immediately (CR-20260811-A-S01-domain-behavior-035).
    assert codes == [IssueCode.CMP_STR_SCHEMA_001]


def test_deep_preflight_reports_invalid_sections() -> None:
    result = _validator()._run_deep_preflight_validation(
        CompositeValidationConfig(
            pipeline_name="composite",
            composite_config={
                "sources": ["chembl", "pubmed"],
                "merge_strategy": "prioritize",
                "output_schema": {"properties": {"id": {}, "value": {}}},
                "aggregation": "bad",
                "cross_validation": {"rules": {}},
                "field_priorities": {"title": "pubmed"},
                "lineage": {"track_source_records": False},
            },
        )
    )

    codes = [issue.code for issue in result.issues]
    assert IssueCode.CMP_PF_AGG_001 in codes
    assert IssueCode.CMP_PF_CV_008 in codes
    assert IssueCode.CMP_PF_FIELD_001 in codes
    assert IssueCode.CMP_PF_LIN_001 in codes


def test_validate_composite_includes_governance_execution_decision() -> None:
    report = _validator().validate_composite(
        CompositeValidationConfig(
            pipeline_name="composite",
            composite_config={
                "sources": ["chembl", "pubmed"],
                "merge_strategy": "prioritize",
                "output_schema": {"properties": {"id": {}, "value": {}}},
            },
            execution_context={"ci_integration": True},
        )
    )

    assert report.structural_result.is_valid()
    assert report.deep_preflight_result.is_valid()
    assert report.execution_decision is not None
    assert report.execution_decision["execution_decision"]["execution_allowed"] is True


def test_aggregation_and_cross_validation_config_conversion_paths() -> None:
    validator = _validator()

    aggregation_issues = validator._validate_aggregation_config(
        {"group_by": ["id"], "aggregations": {"value": "avg"}},
        {"properties": {"id": {}, "value": {}}},
    )
    cross_validation_issues = validator._validate_cross_validation_config(
        {
            "pairs": [{"chembl": ["pubmed"]}],
            "rules": {"identity": "strict"},
            "coverage_threshold": 0.5,
        },
        ["chembl", "pubmed"],
    )

    assert aggregation_issues == []
    assert cross_validation_issues == []
    assert _extract_priority({"priority": ["a"]}) == ["a"]
    assert _extract_priority("bad") is None
    assert _is_valid_lineage_config(
        {"tracking_level": "record", "source_fields": ["id"]}
    )


def test_validate_composite_non_mapping_does_not_raise() -> None:
    """CR-20260816-A-S01-domain-behavior-051: skip deep probe on non-dict config."""
    report = _validator().validate_composite(
        CompositeValidationConfig(
            pipeline_name="composite",
            composite_config=[],  # type: ignore[arg-type]
        )
    )

    structural_codes = [issue.code for issue in report.structural_result.issues]
    assert structural_codes == [IssueCode.CMP_STR_SCHEMA_001]
    assert report.deep_preflight_result.issues == []
    assert report.execution_decision is not None


def test_deep_preflight_rejects_non_mapping_output_schema() -> None:
    result = _validator()._run_deep_preflight_validation(
        CompositeValidationConfig(
            pipeline_name="composite",
            composite_config={
                "sources": ["chembl"],
                "merge_strategy": "prioritize",
                "output_schema": "not-a-mapping",
                "aggregation": {"group_by": ["id"], "aggregations": {"value": "avg"}},
            },
        )
    )

    codes = [issue.code for issue in result.issues]
    assert IssueCode.CMP_STR_SCHEMA_001 in codes
    assert all(issue.code != IssueCode.CMP_PF_AGG_002 for issue in result.issues)


def test_deep_preflight_rejects_string_sources() -> None:
    result = _validator()._run_deep_preflight_validation(
        CompositeValidationConfig(
            pipeline_name="composite",
            composite_config={
                "sources": "chembl",
                "merge_strategy": "prioritize",
                "output_schema": {"properties": {"id": {}}},
                "cross_validation": {"rules": {"identity": "strict"}},
            },
        )
    )

    codes = [issue.code for issue in result.issues]
    assert IssueCode.CMP_STR_FORMAT_003 in codes
