"""Typed Gold business-rule contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from ._gold_contracts_support import (
    GOLD_CONTRACT_VERSION_UNKNOWN,
    GoldBusinessRuleCondition,
    GoldBusinessRuleDecision,
    GoldBusinessRuleSemanticScope,
    GoldBusinessRuleSeverity,
    default_rule_id,
    normalize_column_name,
    normalize_contract_version,
    normalize_optional_text,
    normalize_semantic_scope,
    normalize_text_or_empty,
)
from .gold_contracts_rejects import (
    GoldRejectReason,
    GoldRejectReasonCode,
    build_gold_semantic_reject_reason,
    normalize_reason_code,
)

__all__ = [
    "GoldBusinessRuleCondition",
    "GoldBusinessRuleDecision",
    "GoldBusinessRuleSemanticScope",
    "GoldBusinessRuleSeverity",
    "GoldBusinessRuleSpec",
]


def _decision_literal(raw: str) -> GoldBusinessRuleDecision | None:
    if raw == "pass":
        return "pass"
    if raw == "warn":
        return "warn"
    if raw == "fail":
        return "fail"
    if raw == "quarantine":
        return "quarantine"
    return None


@dataclass(frozen=True, slots=True)
class GoldBusinessRuleSpec:
    """Typed Gold DQ business rule specification."""

    column: str
    condition: GoldBusinessRuleCondition
    rule_id: str = ""
    name: str = ""
    description: str = ""
    minimum: object | None = None
    maximum: object | None = None
    allowed_values: tuple[object, ...] = ()
    pattern: str | None = None
    config_path: str | None = None
    layer: str = "gold"
    field: str | None = None
    severity: GoldBusinessRuleSeverity = "error"
    decision: GoldBusinessRuleDecision | None = None
    contract_version: str = GOLD_CONTRACT_VERSION_UNKNOWN
    semantic_scope: GoldBusinessRuleSemanticScope = "business"
    reject_reason_code: GoldRejectReasonCode | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "column", normalize_column_name(self.column, field_name="column")
        )
        object.__setattr__(self, "pattern", normalize_optional_text(self.pattern))
        object.__setattr__(
            self, "config_path", normalize_optional_text(self.config_path)
        )
        resolved_field = self.field if self.field is not None else self.column
        object.__setattr__(
            self,
            "field",
            normalize_column_name(resolved_field, field_name="field"),
        )
        object.__setattr__(self, "layer", normalize_optional_text(self.layer) or "gold")
        object.__setattr__(self, "rule_id", normalize_text_or_empty(self.rule_id))
        object.__setattr__(self, "name", normalize_text_or_empty(self.name))
        object.__setattr__(
            self, "description", normalize_text_or_empty(self.description)
        )
        object.__setattr__(self, "allowed_values", tuple(self.allowed_values))
        object.__setattr__(
            self,
            "contract_version",
            normalize_contract_version(self.contract_version),
        )
        object.__setattr__(
            self,
            "semantic_scope",
            normalize_semantic_scope(self.semantic_scope),
        )
        if self.reject_reason_code is not None:
            reason_code = normalize_reason_code(self.reject_reason_code)
            if not reason_code.is_semantic:
                raise ValueError("Gold business rules must use gold_semantic_* codes")
            object.__setattr__(self, "reject_reason_code", reason_code)
        _reject_inverted_numeric_range(self.minimum, self.maximum)

    @staticmethod
    def _parse_allowed_values(raw_values: object) -> tuple[object, ...]:
        if raw_values is None:
            return ()
        if isinstance(raw_values, Sequence) and not isinstance(
            raw_values, (str, bytes)
        ):
            return tuple(raw_values)
        raise ValueError("values must be a list or tuple when provided")

    @staticmethod
    def _validate_severity(raw: object) -> GoldBusinessRuleSeverity:
        if raw == "error":
            return "error"
        if raw == "warn":
            return "warn"
        raise ValueError("severity must be 'error' or 'warn'")

    @staticmethod
    def _validate_decision(raw: object) -> GoldBusinessRuleDecision | None:
        if raw is None:
            return None
        if not isinstance(raw, str):
            raise ValueError("decision must be one of: pass, warn, fail, quarantine")
        decision = _decision_literal(raw)
        if decision is None:
            raise ValueError("decision must be one of: pass, warn, fail, quarantine")
        return decision

    @classmethod
    def from_mapping(
        cls,
        raw: Mapping[str, object],
        *,
        default_contract_version: str | None = None,
    ) -> GoldBusinessRuleSpec:
        """Build typed business rule from raw config/test mapping."""
        condition = raw.get("condition")
        if not isinstance(condition, str):
            raise ValueError("condition must be a string")

        return cls(
            rule_id=normalize_text_or_empty(raw.get("rule_id")),
            name=normalize_text_or_empty(raw.get("name")),
            description=normalize_text_or_empty(raw.get("description")),
            column=normalize_column_name(raw.get("column"), field_name="column"),
            condition=cast("GoldBusinessRuleCondition", condition),
            minimum=raw.get("min"),
            maximum=raw.get("max"),
            allowed_values=cls._parse_allowed_values(raw.get("values", ())),
            pattern=normalize_optional_text(raw.get("pattern")),
            config_path=normalize_optional_text(raw.get("config_path")),
            layer=normalize_optional_text(raw.get("layer")) or "gold",
            field=normalize_optional_text(raw.get("field")),
            severity=cls._validate_severity(raw.get("severity", "error")),
            decision=cls._validate_decision(raw.get("decision")),
            contract_version=normalize_contract_version(
                raw.get("contract_version", default_contract_version)
            ),
            semantic_scope=normalize_semantic_scope(
                raw.get("semantic_scope", raw.get("rule_family"))
            ),
            reject_reason_code=(
                normalize_reason_code(raw["reject_reason_code"])
                if raw.get("reject_reason_code") is not None
                else None
            ),
        )

    def build_reject_reason(self, *, violations: int | None) -> GoldRejectReason:
        """Build a semantic reject reason for this failed rule."""
        return build_gold_semantic_reject_reason(
            contract_version=self.contract_version,
            rule_id=self.rule_id or default_rule_id("gold.semantic", self.field),
            field=self.field,
            message=self.description or self.name or "Gold semantic rule failed",
            config_path=self.config_path,
            semantic_scope=self.semantic_scope,
            reason_code=self.reject_reason_code,
            details={
                "condition": self.condition,
                "decision": self.decision or "fail",
                "violations": violations,
            },
        )


def _reject_inverted_numeric_range(minimum: object, maximum: object) -> None:
    if isinstance(minimum, bool) or not isinstance(minimum, (int, float)):
        return
    if isinstance(maximum, bool) or not isinstance(maximum, (int, float)):
        return
    if minimum > maximum:
        raise ValueError("minimum cannot exceed maximum")
