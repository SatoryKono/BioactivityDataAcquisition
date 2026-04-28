"""Typed Gold-layer configuration contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, cast

__all__ = [
    "GoldBusinessRuleCondition",
    "GoldBusinessRuleDecision",
    "GoldBusinessRuleSeverity",
    "GoldBusinessRuleSpec",
    "ScdConfig",
]

GoldBusinessRuleCondition = Literal["not_null", "range", "in_list", "regex"]
GoldBusinessRuleSeverity = Literal["error", "warn"]
GoldBusinessRuleDecision = Literal["pass", "warn", "fail", "quarantine"]


def _normalize_column_name(value: object, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a non-empty string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")
    return normalized


def _normalize_business_key_sequence(value: Sequence[object]) -> tuple[str, ...]:
    normalized = tuple(
        _normalize_column_name(item, field_name="business_key item") for item in value
    )
    if not normalized:
        raise ValueError("business_key sequence must not be empty")
    return normalized


def _normalize_business_key(
    value: object,
) -> str | tuple[str, ...]:
    if isinstance(value, str):
        return _normalize_column_name(value, field_name="business_key")
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return _normalize_business_key_sequence(value)
    raise ValueError("business_key must be a string or a non-empty sequence of strings")


def _normalize_optional_text(value: object | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("optional text fields must be strings when provided")
    normalized = value.strip()
    return normalized or None


def _normalize_text_or_empty(value: object | None) -> str:
    """Normalize optional text, returning empty string instead of None."""
    return _normalize_optional_text(value) or ""


@dataclass(frozen=True, slots=True)
class ScdConfig:
    """Typed SCD Type 2 configuration used inside the runtime."""

    business_key: str | tuple[str, ...] | None = None
    valid_from_col: str = "valid_from"
    valid_to_col: str = "valid_to"
    current_flag_col: str = "is_current"
    version_col: str = "version"
    scd_type: int = 2

    def __post_init__(self) -> None:
        if self.business_key is not None:
            object.__setattr__(
                self,
                "business_key",
                _normalize_business_key(self.business_key),
            )
        object.__setattr__(
            self,
            "valid_from_col",
            _normalize_column_name(self.valid_from_col, field_name="valid_from_col"),
        )
        object.__setattr__(
            self,
            "valid_to_col",
            _normalize_column_name(self.valid_to_col, field_name="valid_to_col"),
        )
        object.__setattr__(
            self,
            "current_flag_col",
            _normalize_column_name(
                self.current_flag_col, field_name="current_flag_col"
            ),
        )
        object.__setattr__(
            self,
            "version_col",
            _normalize_column_name(self.version_col, field_name="version_col"),
        )
        if self.scd_type <= 0:
            raise ValueError("scd_type must be positive")

    @property
    def business_keys(self) -> tuple[str, ...]:
        """Return the business key as a normalized tuple."""
        if self.business_key is None:
            return ()
        if isinstance(self.business_key, str):
            return (self.business_key,)
        return self.business_key

    @property
    def entity_key(self) -> str | None:
        """Return single-column entity key when applicable."""
        return self.business_key if isinstance(self.business_key, str) else None

    @classmethod
    def _resolve_business_key(
        cls,
        raw: Mapping[str, object],
        primary_keys: Sequence[str] | None,
    ) -> str | tuple[str, ...] | None:
        business_key = raw.get("business_key", raw.get("entity_key"))
        if business_key is not None:
            return _normalize_business_key(business_key)
        if primary_keys:
            return primary_keys[0] if len(primary_keys) == 1 else tuple(primary_keys)
        return None

    @classmethod
    def from_mapping(
        cls,
        raw: Mapping[str, object],
        *,
        primary_keys: Sequence[str] | None = None,
    ) -> ScdConfig:
        """Build typed config from YAML/test mapping input."""
        scd_type_raw = raw.get("type", 2)
        if not isinstance(scd_type_raw, int):
            raise ValueError("type must be an integer when provided")

        return cls(
            business_key=cls._resolve_business_key(raw, primary_keys),
            valid_from_col=_normalize_column_name(
                raw.get("valid_from_col", raw.get("valid_from", "valid_from")),
                field_name="valid_from_col",
            ),
            valid_to_col=_normalize_column_name(
                raw.get("valid_to_col", raw.get("valid_to", "valid_to")),
                field_name="valid_to_col",
            ),
            current_flag_col=_normalize_column_name(
                raw.get("current_flag_col", raw.get("is_current", "is_current")),
                field_name="current_flag_col",
            ),
            version_col=_normalize_column_name(
                raw.get("version_col", raw.get("version", "version")),
                field_name="version_col",
            ),
            scd_type=scd_type_raw,
        )


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

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "column", _normalize_column_name(self.column, field_name="column")
        )
        object.__setattr__(self, "pattern", _normalize_optional_text(self.pattern))
        object.__setattr__(
            self, "config_path", _normalize_optional_text(self.config_path)
        )
        field = self.field if self.field is not None else self.column
        object.__setattr__(
            self, "field", _normalize_column_name(field, field_name="field")
        )
        object.__setattr__(
            self, "layer", _normalize_optional_text(self.layer) or "gold"
        )
        object.__setattr__(self, "rule_id", _normalize_text_or_empty(self.rule_id))
        object.__setattr__(self, "name", _normalize_text_or_empty(self.name))
        object.__setattr__(
            self, "description", _normalize_text_or_empty(self.description)
        )
        object.__setattr__(self, "allowed_values", tuple(self.allowed_values))

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
        if raw not in ("error", "warn"):
            raise ValueError("severity must be 'error' or 'warn'")
        return raw

    @staticmethod
    def _validate_decision(raw: object) -> GoldBusinessRuleDecision | None:
        if raw is not None and raw not in ("pass", "warn", "fail", "quarantine"):
            raise ValueError("decision must be one of: pass, warn, fail, quarantine")
        return raw

    @classmethod
    def from_mapping(cls, raw: Mapping[str, object]) -> GoldBusinessRuleSpec:
        """Build typed business rule from raw config/test mapping."""
        condition = raw.get("condition")
        if not isinstance(condition, str):
            raise ValueError("condition must be a string")

        return cls(
            rule_id=_normalize_text_or_empty(raw.get("rule_id")),
            name=_normalize_text_or_empty(raw.get("name")),
            description=_normalize_text_or_empty(raw.get("description")),
            column=_normalize_column_name(raw.get("column"), field_name="column"),
            condition=cast("GoldBusinessRuleCondition", condition),
            minimum=raw.get("min"),
            maximum=raw.get("max"),
            allowed_values=cls._parse_allowed_values(raw.get("values", ())),
            pattern=_normalize_optional_text(raw.get("pattern")),
            config_path=_normalize_optional_text(raw.get("config_path")),
            layer=_normalize_optional_text(raw.get("layer")) or "gold",
            field=_normalize_optional_text(raw.get("field")),
            severity=cls._validate_severity(raw.get("severity", "error")),
            decision=cls._validate_decision(raw.get("decision")),
        )
