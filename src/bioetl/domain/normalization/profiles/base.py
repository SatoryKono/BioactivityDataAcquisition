"""Domain contracts for field-by-field normalization profiles."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass, field
from functools import cache

__all__ = [
    "FieldRule",
    "NormalizationProfile",
]

FieldNormalizer = Callable[..., object]


@cache
def _normalizer_accepts_record_context(normalizer: FieldNormalizer) -> bool:
    try:
        parameters = tuple(inspect.signature(normalizer).parameters.values())
    except (TypeError, ValueError):
        return False
    return any(
        parameter.name == "record"
        or parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters
    )


def _identity(value: object) -> object:
    return value


@dataclass(frozen=True, slots=True)
class FieldRule:
    """Normalization and hash policy for one schema field."""

    field_name: str
    normalizer: FieldNormalizer = _identity
    include_in_hash: bool = True
    set_like: bool = False
    notes: str | None = None

    def apply(
        self,
        value: object,
        *,
        record: Mapping[str, object] | None = None,
    ) -> object:
        """Apply one pure field normalizer."""
        if record is not None and _normalizer_accepts_record_context(self.normalizer):
            return self.normalizer(value, record=record)
        return self.normalizer(value)


@dataclass(frozen=True, slots=True)
class NormalizationProfile:
    """Domain normalization contract for one provider/entity schema."""

    profile_name: str
    field_rules: Mapping[str, FieldRule]
    meta_fields: frozenset[str] = field(default_factory=frozenset)
    description: str | None = None

    def __post_init__(self) -> None:
        normalized_rules = dict(
            sorted(self.field_rules.items(), key=lambda item: item[0])
        )
        if not normalized_rules:
            raise ValueError("field_rules cannot be empty")
        for field_name, rule in normalized_rules.items():
            if field_name != rule.field_name:
                raise ValueError(
                    f"FieldRule key {field_name!r} does not match field_name {rule.field_name!r}"
                )
        if not self.meta_fields.issubset(normalized_rules.keys()):
            missing = sorted(self.meta_fields.difference(normalized_rules.keys()))
            raise ValueError(
                f"meta_fields must be present in field_rules: {', '.join(missing)}"
            )
        object.__setattr__(self, "field_rules", normalized_rules)

    def rule_for(self, field_name: str) -> FieldRule | None:
        """Return the rule for one field when present."""
        return self.field_rules.get(field_name)

    @property
    def fields(self) -> frozenset[str]:
        """Return all known schema fields in the profile."""
        return frozenset(self.field_rules.keys())

    @property
    def hash_included_fields(self) -> frozenset[str]:
        """Return fields that contribute to content_hash."""
        return frozenset(
            field_name
            for field_name, rule in self.field_rules.items()
            if rule.include_in_hash
        )

    @property
    def hash_excluded_fields(self) -> frozenset[str]:
        """Return fields that are explicitly excluded from content_hash."""
        return frozenset(
            field_name
            for field_name, rule in self.field_rules.items()
            if not rule.include_in_hash
        )

    @property
    def set_like_fields(self) -> frozenset[str]:
        """Return fields whose list-like values are order-insensitive for hashing."""
        return frozenset(
            field_name for field_name, rule in self.field_rules.items() if rule.set_like
        )

    def coverage_gaps(
        self,
        schema_fields: Collection[str],
    ) -> tuple[frozenset[str], frozenset[str]]:
        """Return missing and extra fields against one schema field set."""
        schema_field_set = frozenset(schema_fields)
        missing = schema_field_set.difference(self.fields)
        extra = self.fields.difference(schema_field_set)
        return frozenset(sorted(missing)), frozenset(sorted(extra))

    def assert_covers_schema(self, schema_fields: Collection[str]) -> None:
        """Raise when the profile does not exactly cover the target schema."""
        missing, extra = self.coverage_gaps(schema_fields)
        if not missing and not extra:
            return
        parts: list[str] = []
        if missing:
            parts.append(f"missing={sorted(missing)}")
        if extra:
            parts.append(f"extra={sorted(extra)}")
        raise ValueError(
            f"{self.profile_name} does not cover schema fields exactly: {'; '.join(parts)}"
        )
