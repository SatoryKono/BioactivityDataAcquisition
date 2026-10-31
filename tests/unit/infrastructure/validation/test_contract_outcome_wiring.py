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
"""Outcome channel: contract rules, attribution, and strict-validate parity."""

from __future__ import annotations

import pandera.pandas as pa
import pytest

from bioetl.domain.behavior.dq_contract_rule_source import (
    load_executable_contract_rules,
)
from bioetl.domain.config.dq import DQConfig
from bioetl.domain.config.validation import FieldValidation
from bioetl.domain.types.dq_contracts import DQDisposition
from bioetl.infrastructure.validation.contract_validator import (
    ContractAwareGoldValidator,
    ContractAwareSilverValidator,
)

pytestmark = pytest.mark.unit

_SCHEMA = pa.DataFrameSchema(
    {
        "entity_id": pa.Column(str),
        "name": pa.Column(str, nullable=True),
    }
)


def _rules() -> tuple[FieldValidation, ...]:
    return (
        FieldValidation(field="name", validation_type="required", severity="error"),
        FieldValidation(field="smiles", validation_type="required", severity="error"),
    )


def _policy(**overrides: object) -> DQConfig:
    payload: dict[str, object] = {
        "contract_ref": "gold.molecule",
        "contract_version": "1.0.0",
        "rule_bundle_version": "1.0.0",
        "field_validations": _rules(),
    }
    payload.update(overrides)
    return DQConfig(**payload)  # type: ignore[arg-type]


def test_contract_rules_load_from_dq_config_not_contract_ref() -> None:
    config = _policy()
    bundle = load_executable_contract_rules(config)
    assert bundle.source.startswith("dq_config.field_validations")
    assert len(bundle.field_validations) == 2
    assert load_executable_contract_rules(
        DQConfig(contract_ref="gold.molecule")
    ).is_empty


def test_apply_contract_validations_emits_real_outcomes() -> None:
    import pandas as pd

    validator = ContractAwareGoldValidator(schema=_SCHEMA, dq_config=_policy())
    frame = pd.DataFrame(
        [
            {"entity_id": "a", "name": None, "smiles": "C"},
            {"entity_id": "b", "name": "ok", "smiles": "C"},
        ]
    )
    outcomes = validator._apply_contract_validations(frame)
    assert [outcome.rule_id for outcome in outcomes] == ["field.name.required"]
    assert outcomes[0].disposition == DQDisposition.QUARANTINE
    assert outcomes[0].policy_ref is not None
    assert outcomes[0].policy_ref.contract_ref == "gold.molecule"
    assert outcomes[0].config_path == "contracts/gold.molecule/dq_rules.yaml"


@pytest.mark.parametrize("missing", [None, float("nan")])
def test_dataframe_missing_values_keep_required_rule_outcomes(missing: object) -> None:
    import pandas as pd

    validator = ContractAwareGoldValidator(schema=_SCHEMA, dq_config=_policy())
    frame = pd.DataFrame(
        [
            {"entity_id": "a", "name": missing, "smiles": "C"},
            {"entity_id": "b", "name": "kept", "smiles": "C"},
        ]
    )
    outcomes = validator._apply_contract_validations(frame)
    assert [outcome.rule_id for outcome in outcomes] == ["field.name.required"]
    assert outcomes[0].disposition == DQDisposition.QUARANTINE


@pytest.mark.parametrize("present", [0, False, "kept"])
def test_dataframe_present_values_are_not_converted_to_null(present: object) -> None:
    import pandas as pd

    validator = ContractAwareGoldValidator(schema=_SCHEMA, dq_config=_policy())
    frame = pd.DataFrame([{"entity_id": "a", "name": present, "smiles": "C"}])
    assert validator._apply_contract_validations(frame) == []


def test_multiple_errors_share_one_source_index() -> None:
    validator = ContractAwareGoldValidator(schema=_SCHEMA, dq_config=_policy())
    records = [
        {"entity_id": "a", "name": None},
        {"entity_id": "b", "name": "ok", "smiles": "C"},
    ]
    _valid, outcomes = validator.validate_with_outcomes(records)
    violations = validator.validate_with_outcomes(records).violations
    name_and_smiles = [
        item for item in violations if item.outcome.rule_id.startswith("field.")
    ]
    assert {item.outcome.rule_id for item in name_and_smiles} == {
        "field.name.required",
        "field.smiles.required",
    }
    assert {item.record.source_index for item in name_and_smiles if item.record} == {0}
    assert [
        outcome.rule_id for outcome in outcomes if outcome.rule_id.startswith("field.")
    ] == [
        "field.name.required",
        "field.smiles.required",
    ]


def test_schema_level_error_has_no_row_identity() -> None:
    strict = pa.DataFrameSchema({"field": pa.Column(str)}, strict=True)
    validator = ContractAwareGoldValidator(schema=strict, dq_config=_policy())
    channel = validator.validate_with_outcomes([{"field": "a", "extra": 1}])
    schema_hits = [
        item
        for item in channel.violations
        if item.outcome.violation_kind.value == "schema_violation"
    ]
    assert schema_hits
    assert all(item.record is None for item in schema_hits)
    assert all(item.attributable is False for item in schema_hits)


def test_outcome_channel_replay_is_identical() -> None:
    validator = ContractAwareGoldValidator(schema=_SCHEMA, dq_config=_policy())
    records = [{"entity_id": "a", "name": None}, {"entity_id": "b", "name": "ok"}]
    first = validator.validate_with_outcomes(records)
    second = validator.validate_with_outcomes(records)
    assert first.outcomes == second.outcomes
    assert first.violations == second.violations
    assert [item.outcome.disposition for item in first.violations] == [
        item.outcome.disposition for item in second.violations
    ]


def test_strict_validate_parity_without_explicit_policy() -> None:
    schema = pa.DataFrameSchema({"field": pa.Column(str, nullable=False)})
    validator = ContractAwareGoldValidator(schema=schema, dq_config=DQConfig())
    records = [{"field": None}]
    direct = validator.validate(records)
    channel = validator.validate_with_outcomes(records)
    assert direct.valid is False
    assert channel.is_valid is False
    assert channel.violations
    assert channel.violations[0].record is not None
    assert channel.violations[0].record.source_index == 0


def test_silver_validate_with_outcomes_returns_contract_rules() -> None:
    schema = pa.DataFrameSchema(
        {
            "entity_id": pa.Column(str),
            "name": pa.Column(str, nullable=True),
            "smiles": pa.Column(str, nullable=True),
        }
    )
    validator = ContractAwareSilverValidator(schema=schema, dq_config=_policy())
    channel = validator.validate_with_outcomes(
        [
            {"entity_id": "a", "name": None},
            {"entity_id": "b", "name": "kept", "smiles": "C"},
        ]
    )
    assert channel.is_valid is False
    assert [item.outcome.rule_id for item in channel.violations] == [
        "field.name.required",
        "field.smiles.required",
    ]
    assert channel.violations[0].record is not None
    assert channel.violations[0].record.record_key == "a"
