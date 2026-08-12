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
"""Unit tests for aggregation validation behavior."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.aggregation_validator import (
    AggregationConfig,
    AggregationValidator,
)
from bioetl.domain.types.validation_severity import IssueCode

pytestmark = pytest.mark.unit


def test_validate_aggregation_config_accepts_properties_schema() -> None:
    result = AggregationValidator().validate_aggregation_config(
        AggregationConfig(group_by=["target_id"], aggregations={"activity": "avg"}),
        {"properties": {"target_id": {}, "activity": {}}},
        {"run_id": "run-1"},
    )

    assert result.is_valid()
    assert result.execution_context == {"run_id": "run-1"}


def test_validate_aggregation_config_reports_missing_and_unsupported_fields() -> None:
    result = AggregationValidator().validate_aggregation_config(
        AggregationConfig(
            group_by=[],
            aggregations={},
            source_field="missing",
        ),
        {"fields": ["target_id"]},
    )

    assert [issue.code for issue in result.issues] == [
        IssueCode.CMP_PF_AGG_001,
        IssueCode.CMP_PF_AGG_003,
        IssueCode.CMP_PF_AGG_005,
    ]
    assert result.has_blockers()


def test_validate_aggregation_config_reports_missing_group_unsupported_and_shadowing() -> (
    None
):
    result = AggregationValidator().validate_aggregation_config(
        AggregationConfig(
            group_by=["target_id", "missing"],
            aggregations={"target_id": "unsupported"},
        ),
        {"properties": {"target_id": {}}},
    )

    codes = [issue.code for issue in result.issues]
    assert IssueCode.CMP_PF_AGG_002 in codes
    assert IssueCode.CMP_PF_AGG_004 in codes
    assert IssueCode.CMP_PF_AGG_006 in codes


def test_source_field_collection_supports_fallback_nested_schema() -> None:
    # Arbitrary nested keys are no longer treated as source fields.
    fields = AggregationValidator()._get_source_fields(
        {"outer": {"nested": "value"}, "plain": "value"}
    )
    assert fields == set()

    fields = AggregationValidator()._get_source_fields(
        {"columns": ["a", "b"], "noise": {"x": 1}}
    )
    assert fields == {"a", "b"}


def test_post_aggregation_uniqueness_reports_duplicate_group_samples() -> None:
    result = AggregationValidator().validate_post_aggregation_uniqueness(
        [
            {"target_id": "CHEMBL1", "organism": "human"},
            {"target_id": "CHEMBL2", "organism": "mouse"},
            {"target_id": "CHEMBL1", "organism": "human"},
            {"target_id": "CHEMBL3"},
            {"target_id": "CHEMBL3"},
        ],
        ["target_id", "organism"],
    )

    assert result.has_blockers()
    issue = result.issues[0]
    assert issue.code == IssueCode.CMP_RT_GRAIN_001
    assert issue.details is not None
    assert issue.details["duplicate_count"] == 2
    # Type-tagged keys: (presence, type_name, repr)
    assert issue.details["sample_duplicates"][0]["group_key"] == [
        ["present", "str", "'CHEMBL1'"],
        ["present", "str", "'human'"],
    ]
    assert issue.details["sample_duplicates"][1]["group_key"] == [
        ["present", "str", "'CHEMBL3'"],
        ["absent", "", ""],
    ]


def test_generate_aggregation_provenance_counts_available_source_fields() -> None:
    provenance = AggregationValidator().generate_aggregation_provenance(
        AggregationConfig(
            group_by=["target_id"],
            aggregations={"activity_mean": "avg", "activity_count": "count"},
            source_field="activity",
        ),
        [{"activity": 1}, {"activity": 2}, {"other": 3}],
    )

    assert [item.field_name for item in provenance] == [
        "activity_mean",
        "activity_count",
    ]
    assert all(item.source_field == "activity" for item in provenance)
    assert all(item.source_count == 2 for item in provenance)
