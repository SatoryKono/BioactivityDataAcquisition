"""Public facade for Gold-layer typed contracts."""

from __future__ import annotations

from ._gold_contracts_support import (
    GOLD_CONTRACT_VERSION_UNKNOWN,
    GoldBusinessRuleCondition,
    GoldBusinessRuleDecision,
    GoldBusinessRuleSemanticScope,
    GoldBusinessRuleSeverity,
)
from .gold_contracts_rejects import (
    GoldContractValidationError,
    GoldRejectReason,
    GoldRejectReasonCode,
    build_gold_contract_reject_reason,
    build_gold_semantic_reject_reason,
    classify_gold_schema_error_reason,
    resolve_gold_contract_version,
)
from .gold_contracts_rules import GoldBusinessRuleSpec
from .gold_contracts_scd import ScdConfig

__all__ = [
    "GOLD_CONTRACT_VERSION_UNKNOWN",
    "GoldBusinessRuleCondition",
    "GoldBusinessRuleDecision",
    "GoldBusinessRuleSemanticScope",
    "GoldBusinessRuleSeverity",
    "GoldBusinessRuleSpec",
    "GoldContractValidationError",
    "GoldRejectReason",
    "GoldRejectReasonCode",
    "ScdConfig",
    "build_gold_contract_reject_reason",
    "build_gold_semantic_reject_reason",
    "classify_gold_schema_error_reason",
    "resolve_gold_contract_version",
]
