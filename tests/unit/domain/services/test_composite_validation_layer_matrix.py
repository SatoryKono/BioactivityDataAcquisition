"""Parametrized matrix for composite validation layer severities."""

from __future__ import annotations

import pytest

from bioetl.domain.behavior.composite_validation_layer import (
    CompositeValidationConfig,
    CompositeValidator,
)
from bioetl.domain.behavior.aggregation_validator import AggregationValidator
from bioetl.domain.behavior.cross_validation_validator import CrossValidationValidator
from bioetl.domain.behavior.preflight_governance import PreflightGovernor
from bioetl.domain.types.validation_severity import IssueCode, ValidationLayer

pytestmark = pytest.mark.unit


def _validator() -> CompositeValidator:
    return CompositeValidator(
        aggregation_validator=AggregationValidator(),
        cross_validation_validator=CrossValidationValidator(),
        preflight_governance=PreflightGovernor(),
    )


@pytest.mark.parametrize(
    ("composite_config", "expected_blocker_codes"),
    [
        (
            {"sources": ["source1"]},
            {IssueCode.CMP_STR_CONFIG_002},
        ),
        (
            {
                "sources": ["source1"],
                "merge_strategy": "prioritize",
                "output_schema": {"fields": ["field1"]},
                "aggregation": {"group_by": ["missing_field"]},
            },
            {IssueCode.CMP_PF_AGG_002, IssueCode.CMP_PF_AGG_003},
        ),
        (
            {
                "sources": ["source1"],
                "merge_strategy": "prioritize",
                "output_schema": {"fields": ["field1"]},
                "cross_validation": {"pairs": [{"source1": "source2"}]},
            },
            {IssueCode.CMP_PF_CV_008},
        ),
    ],
)
def test_composite_validation_matrix_surfaces_expected_blockers(
    composite_config: dict[str, object],
    expected_blocker_codes: set[IssueCode],
) -> None:
    """Invalid composite configs must surface deterministic blocker issue codes."""
    report = _validator().validate_composite(
        CompositeValidationConfig(
            pipeline_name="matrix_test",
            composite_config=composite_config,
        )
    )

    assert report.has_any_blockers()
    codes = {issue.code for issue in report.get_all_blockers()}
    assert expected_blocker_codes <= codes
    assert all(
        issue.layer in {ValidationLayer.STRUCTURAL, ValidationLayer.DEEP_PREFLIGHT}
        for issue in report.get_all_blockers()
    )
