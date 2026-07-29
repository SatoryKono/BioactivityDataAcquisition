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
"""Unit tests for Gold contract reject taxonomy."""

from __future__ import annotations

import pytest

from bioetl.domain.types import (
    GOLD_CONTRACT_VERSION_UNKNOWN,
    GoldRejectReasonCode,
    build_gold_contract_reject_reason,
    build_gold_semantic_reject_reason,
    classify_gold_schema_error_reason,
    resolve_gold_contract_version,
)

pytestmark = pytest.mark.unit


class _SchemaWithMetadata:
    metadata = {"contract_version": "2.0.0"}


def test_gold_reject_taxonomy_separates_contract_and_semantic_families() -> None:
    assert GoldRejectReasonCode.CONTRACT_SCHEMA_FAILURE.is_contract is True
    assert GoldRejectReasonCode.CONTRACT_REFERENCE_FAILURE.is_contract is True
    assert GoldRejectReasonCode.CONTRACT_REQUIRED_FAILURE.is_contract is True
    assert GoldRejectReasonCode.SEMANTIC_BUSINESS_EXCLUSION.is_semantic is True
    assert GoldRejectReasonCode.SEMANTIC_PROFILE_EXCLUSION.is_semantic is True


def test_gold_contract_reject_reason_requires_contract_code() -> None:
    with pytest.raises(ValueError, match="gold_contract"):
        build_gold_contract_reject_reason(
            reason_code=GoldRejectReasonCode.SEMANTIC_BUSINESS_EXCLUSION,
            contract_version="1.0.0",
            rule_id="gold.semantic.business",
        )


def test_gold_semantic_reject_reason_carries_contract_version_and_rule_id() -> None:
    reason = build_gold_semantic_reject_reason(
        contract_version="1.0.0",
        rule_id="gold.semantic.profile.active_source",
        field="source_profile",
        semantic_scope="profile",
    )

    assert reason.reason_code == GoldRejectReasonCode.SEMANTIC_PROFILE_EXCLUSION
    assert reason.contract_version == "1.0.0"
    assert reason.rule_id == "gold.semantic.profile.active_source"
    assert reason.field == "source_profile"


def test_gold_contract_version_resolution_uses_schema_metadata() -> None:
    assert resolve_gold_contract_version(_SchemaWithMetadata()) == "2.0.0"
    assert resolve_gold_contract_version(None) == GOLD_CONTRACT_VERSION_UNKNOWN


def test_gold_schema_error_classifier_marks_required_failures() -> None:
    error = ValueError("column 'entity_id' not in dataframe")

    assert (
        classify_gold_schema_error_reason(error)
        == GoldRejectReasonCode.CONTRACT_REQUIRED_FAILURE
    )
