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
"""Focused tests for Gold contract domain type helper modules."""

from __future__ import annotations

import pytest

from bioetl.domain.types._gold_contracts_support import (
    GOLD_CONTRACT_VERSION_UNKNOWN,
    default_rule_id,
    normalize_business_key,
    normalize_contract_version,
)
from bioetl.domain.types.gold_contracts_rejects import (
    GoldRejectReasonCode,
    build_gold_contract_reject_reason,
    build_gold_semantic_reject_reason,
    classify_gold_schema_error_reason,
    resolve_gold_contract_version,
)
from bioetl.domain.types.gold_contracts_rules import GoldBusinessRuleSpec
from bioetl.domain.types.gold_contracts_scd import ScdConfig

pytestmark = pytest.mark.unit


def test_gold_contract_support_normalizes_business_keys_and_versions() -> None:
    assert normalize_business_key(" activity_id ") == "activity_id"
    assert normalize_business_key([" molecule_id ", " assay_id "]) == (
        "molecule_id",
        "assay_id",
    )
    assert normalize_contract_version(None) == GOLD_CONTRACT_VERSION_UNKNOWN
    assert default_rule_id("gold.contract", " activity_id ") == (
        "gold.contract.activity_id"
    )


def test_gold_contract_support_rejects_empty_business_key_sequence() -> None:
    with pytest.raises(ValueError, match="business_key sequence must not be empty"):
        normalize_business_key([])


def test_gold_reject_reason_builders_enforce_reason_code_family() -> None:
    contract_reason = build_gold_contract_reject_reason(
        reason_code=GoldRejectReasonCode.CONTRACT_REQUIRED_FAILURE,
        field=" activity_id ",
        message="missing activity id",
        details={"missing": "activity_id"},
        contract_version=" 2.0.0 ",
    )

    assert contract_reason.reason_code.is_contract is True
    assert contract_reason.field == "activity_id"
    assert contract_reason.rule_id == "gold.contract.activity_id"
    assert contract_reason.contract_version == "2.0.0"
    assert dict(contract_reason.details) == {"missing": "activity_id"}

    with pytest.raises(ValueError, match="requires a semantic code"):
        build_gold_semantic_reject_reason(
            reason_code=GoldRejectReasonCode.CONTRACT_SCHEMA_FAILURE,
            field="activity_id",
        )


def test_gold_schema_error_classification_and_version_resolution() -> None:
    assert (
        classify_gold_schema_error_reason(ValueError("missing required column"))
        == GoldRejectReasonCode.CONTRACT_REQUIRED_FAILURE
    )
    assert (
        classify_gold_schema_error_reason(ValueError("foreign key orphan"))
        == GoldRejectReasonCode.CONTRACT_REFERENCE_FAILURE
    )

    class _SchemaWithConfig:
        class Config:
            contract_version = "3.1.4"

    assert resolve_gold_contract_version(_SchemaWithConfig) == "3.1.4"
    assert (
        resolve_gold_contract_version(None, explicit_contract_version=" 4.0.0 ")
        == "4.0.0"
    )


def test_gold_business_rule_spec_builds_semantic_reject_reason() -> None:
    rule = GoldBusinessRuleSpec.from_mapping(
        {
            "rule_id": "gold.semantic.activity_value",
            "column": " standard_value ",
            "condition": "range",
            "min": 0,
            "severity": "error",
            "decision": "quarantine",
            "semantic_scope": "profile",
            "description": "standard_value must be non-negative",
        },
        default_contract_version="1.2.0",
    )

    reason = rule.build_reject_reason(violations=2)

    assert rule.column == "standard_value"
    assert rule.field == "standard_value"
    assert reason.reason_code == GoldRejectReasonCode.SEMANTIC_PROFILE_EXCLUSION
    assert reason.contract_version == "1.2.0"
    assert reason.details["decision"] == "quarantine"
    assert reason.details["violations"] == 2


def test_scd_config_from_mapping_resolves_keys_and_columns() -> None:
    config = ScdConfig.from_mapping(
        {
            "entity_key": " molecule_id ",
            "valid_from": " _valid_from ",
            "valid_to": "_valid_to",
            "is_current": "_is_current",
            "version": "_version",
            "type": 2,
        },
        primary_keys=("fallback_id",),
    )

    assert config.business_key == "molecule_id"
    assert config.business_keys == ("molecule_id",)
    assert config.entity_key == "molecule_id"
    assert config.valid_from_col == "_valid_from"


def test_scd_config_uses_composite_primary_keys_when_business_key_missing() -> None:
    config = ScdConfig.from_mapping({}, primary_keys=("provider", "entity_id"))

    assert config.business_key == ("provider", "entity_id")
    assert config.business_keys == ("provider", "entity_id")
    assert config.entity_key is None
