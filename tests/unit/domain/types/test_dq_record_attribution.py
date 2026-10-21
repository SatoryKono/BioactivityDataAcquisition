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
"""Record-attribution contract for rule-level DQ outcomes."""

from __future__ import annotations

from bioetl.domain.types.dq_contracts import (
    DQDisposition,
    DQRuleOutcome,
    DQViolationKind,
)
from bioetl.domain.types.dq_record_attribution import (
    AttributedDQViolation,
    record_identity,
    sort_attributed_violations,
)

import pytest

pytestmark = pytest.mark.unit


def _outcome(rule_id: str, field: str) -> DQRuleOutcome:
    return DQRuleOutcome(
        rule_id=rule_id,
        violation_kind=DQViolationKind.BUSINESS_RULE_VIOLATION,
        severity="error",
        disposition=DQDisposition.QUARANTINE,
        affected_fields=(field,),
    )


def test_record_key_uses_canonical_id_not_affected_field() -> None:
    """A shared column name is not a record identifier."""
    identity = record_identity(
        {"name": "shared-column", "entity_id": "CHEMBL1"},
        2,
    )
    assert identity.source_index == 2
    assert identity.record_key == "CHEMBL1"
    assert identity.record_key != "shared-column"


def test_record_without_canonical_id_keeps_index_only() -> None:
    identity = record_identity({"name": "only-a-field"}, 0)
    assert identity.record_key is None
    assert identity.source_index == 0


def test_several_violations_share_one_record_and_schema_errors_do_not() -> None:
    record = record_identity({"activity_id": "A1"}, 1)
    violations = [
        AttributedDQViolation(_outcome("field.smiles.required", "smiles"), record),
        AttributedDQViolation(_outcome("field.name.required", "name"), record),
        AttributedDQViolation(_outcome("schema.column", "column"), None),
    ]
    ordered = sort_attributed_violations(violations)
    assert ordered[0].record is None
    assert ordered[0].attributable is False
    assert [item.outcome.rule_id for item in ordered[1:]] == [
        "field.name.required",
        "field.smiles.required",
    ]
    assert ordered[1].record == ordered[2].record
    assert ordered[1].record is not None
    assert ordered[1].record.source_index == 1


def test_replay_sort_is_identical() -> None:
    record = record_identity({"id": "7"}, 3)
    first = sort_attributed_violations(
        [
            AttributedDQViolation(_outcome("field.b.required", "b"), record),
            AttributedDQViolation(_outcome("schema.missing", "missing"), None),
            AttributedDQViolation(_outcome("field.a.required", "a"), record),
        ]
    )
    second = sort_attributed_violations(list(reversed(first)))
    assert first == second
    assert [item.outcome.rule_id for item in first] == [
        "schema.missing",
        "field.a.required",
        "field.b.required",
    ]
