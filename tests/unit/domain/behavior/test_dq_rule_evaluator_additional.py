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
"""Additional deterministic coverage for DQ rule evaluation helpers."""

from __future__ import annotations

import math

import pytest

from bioetl.domain.behavior.dq_rule_evaluator import evaluate_dq_rules_for_record
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.config.validation import FieldValidation
from bioetl.domain.types.dq_contracts import DQDisposition


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("invalid_record_policy", "expected_disposition"),
    [
        ("quarantine", DQDisposition.QUARANTINE),
        ("skip", DQDisposition.SKIP),
        ("fail", DQDisposition.FAIL),
    ],
)
def test_error_rule_outcome_honors_invalid_record_policy(
    invalid_record_policy: str,
    expected_disposition: DQDisposition,
) -> None:
    config = DQConfig(
        contract_ref="chembl.activity",
        field_validations=(
            FieldValidation(
                field="required_field",
                validation_type="required",
                nullable=False,
            ),
        ),
        invalid_record_policy=invalid_record_policy,
    )

    outcomes = evaluate_dq_rules_for_record(
        {"required_field": None},
        dq_config=config,
    )

    assert len(outcomes) == 1
    assert outcomes[0].disposition == expected_disposition
    assert outcomes[0].disposition_reason == (
        f"invalid_record_policy={invalid_record_policy}"
    )
    assert outcomes[0].config_path == "contracts/chembl.activity/dq_rules.yaml"


def test_warning_rule_outcome_does_not_override_warn_disposition() -> None:
    config = DQConfig(
        contract_ref="chembl.activity",
        field_validations=(
            FieldValidation(
                field="required_field",
                validation_type="required",
                nullable=False,
                severity="warn",
            ),
        ),
        invalid_record_policy="fail",
    )

    outcomes = evaluate_dq_rules_for_record(
        {"required_field": None},
        dq_config=config,
    )

    assert len(outcomes) == 1
    assert outcomes[0].disposition == DQDisposition.WARN
    assert outcomes[0].disposition_reason != "invalid_record_policy=fail"


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, "not-a-number"])
def test_range_rule_rejects_non_finite_or_non_numeric_values(value: object) -> None:
    config = DQConfig(
        contract_ref="chembl.activity",
        field_validations=(
            FieldValidation(
                field="standard_value",
                validation_type="range",
                min_value=0,
                max_value=100,
            ),
        ),
        invalid_record_policy="fail",
    )

    outcomes = evaluate_dq_rules_for_record(
        {"standard_value": value},
        dq_config=config,
    )

    assert len(outcomes) == 1
    assert outcomes[0].rule_id == "field.standard_value.range"
    assert outcomes[0].disposition == DQDisposition.FAIL


def test_range_rule_accepts_numeric_strings_inside_bounds() -> None:
    config = DQConfig(
        field_validations=(
            FieldValidation(
                field="standard_value",
                validation_type="range",
                min_value=0,
                max_value=100,
            ),
        ),
    )

    outcomes = evaluate_dq_rules_for_record(
        {"standard_value": "50"},
        dq_config=config,
    )

    assert outcomes == []
