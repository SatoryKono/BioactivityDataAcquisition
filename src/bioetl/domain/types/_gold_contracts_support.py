"""Shared support helpers for Gold contract domain types."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal, Protocol, cast, runtime_checkable

GOLD_CONTRACT_VERSION_UNKNOWN = "0.0.0"
GoldBusinessRuleCondition = Literal["not_null", "range", "in_list", "regex"]
GoldBusinessRuleSeverity = Literal["error", "warn"]
GoldBusinessRuleDecision = Literal["pass", "warn", "fail", "quarantine"]
GoldBusinessRuleSemanticScope = Literal["business", "profile"]


@runtime_checkable
class _SchemaConvertible(Protocol):
    def to_schema(self) -> object:
        """Return the concrete schema represented by this object."""
        ...


def invoke_to_schema(schema: object) -> object | None:
    """Resolve a schema factory without weakening the input type to Any."""
    if not isinstance(schema, _SchemaConvertible):
        return None
    try:
        return schema.to_schema()
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None


def normalize_column_name(value: object, *, field_name: str) -> str:
    """Normalize one required column-like string."""
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")
    return normalized


def normalize_business_key_sequence(value: Sequence[object]) -> tuple[str, ...]:
    """Normalize one non-empty business-key sequence."""
    normalized = tuple(
        normalize_column_name(item, field_name="business_key item") for item in value
    )
    if not normalized:
        raise ValueError("business_key sequence must not be empty")
    return normalized


def normalize_business_key(value: object) -> str | tuple[str, ...]:
    """Normalize one business key string or sequence."""
    if isinstance(value, str):
        return normalize_column_name(value, field_name="business_key")
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return normalize_business_key_sequence(value)
    raise ValueError("business_key must be a string or a non-empty sequence of strings")


def normalize_optional_text(value: object | None) -> str | None:
    """Normalize nullable string input."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("optional text fields must be strings when provided")
    normalized = value.strip()
    return normalized or None


def normalize_text_or_empty(value: object | None) -> str:
    """Normalize nullable text, returning an empty string on absence."""
    return normalize_optional_text(value) or ""


def coerce_mapping(value: Mapping[str, object] | None) -> Mapping[str, object]:
    """Freeze nullable mapping-like payloads into a plain dict-backed mapping."""
    return dict(value) if value is not None else {}


def normalize_contract_version(value: object | None) -> str:
    """Normalize contract version text or return the unknown sentinel."""
    return normalize_optional_text(value) or GOLD_CONTRACT_VERSION_UNKNOWN


def normalize_semantic_scope(value: object | None) -> GoldBusinessRuleSemanticScope:
    """Normalize semantic scope to the canonical enum-like literal."""
    normalized = normalize_optional_text(value) or "business"
    if normalized not in ("business", "profile"):
        raise ValueError("semantic_scope must be 'business' or 'profile'")
    return cast("GoldBusinessRuleSemanticScope", normalized)


def default_rule_id(prefix: str, field_name: str | None) -> str:
    """Build a stable default rule ID when the caller did not supply one."""
    suffix = normalize_optional_text(field_name) or "record"
    return f"{prefix}.{suffix}"
