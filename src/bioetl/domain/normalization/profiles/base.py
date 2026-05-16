"""Domain contracts for field-by-field normalization profiles."""

from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Callable, Collection, Mapping
from dataclasses import dataclass, field
from functools import cache

__all__ = [
    "FieldRule",
    "FieldRuleIdentity",
    "NormalizationProfile",
    "NormalizationProfileIdentity",
]

FieldNormalizer = Callable[..., object]


@cache
def _normalizer_accepts_record_context(normalizer: FieldNormalizer) -> bool:
    try:
        parameters = tuple(inspect.signature(normalizer).parameters.values())
    except (TypeError, ValueError):
        return False
    return any(
        parameter.name == "record" or parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters
    )


def _identity(value: object) -> object:
    return value


def _normalizer_ref(normalizer: FieldNormalizer) -> str:
    """Return a deterministic reference string for one field normalizer."""
    module_name = getattr(normalizer, "__module__", None)
    qualname = getattr(normalizer, "__qualname__", None)
    if isinstance(module_name, str) and isinstance(qualname, str):
        return f"{module_name}:{qualname}"
    return repr(normalizer)


def _sha256_hex(payload: object) -> str:
    """Return canonical SHA256 hex digest for one JSON-serializable payload."""
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class FieldRuleIdentity:
    """Deterministic compatibility surface for one normalized field."""

    field_name: str
    normalizer_ref: str
    include_in_hash: bool
    set_like: bool
    compatibility_hash: str


@dataclass(frozen=True, slots=True)
class NormalizationProfileIdentity:
    """Deterministic identity for one normalization profile."""

    profile_name: str
    profile_version: str
    profile_hash: str


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

    @property
    def identity(self) -> FieldRuleIdentity:
        """Return deterministic compatibility metadata for one field rule."""
        payload = {
            "field_name": self.field_name,
            "normalizer_ref": _normalizer_ref(self.normalizer),
            "include_in_hash": self.include_in_hash,
            "set_like": self.set_like,
        }
        return FieldRuleIdentity(
            field_name=self.field_name,
            normalizer_ref=payload["normalizer_ref"],
            include_in_hash=self.include_in_hash,
            set_like=self.set_like,
            compatibility_hash=_sha256_hex(payload),
        )


@dataclass(frozen=True, slots=True)
class NormalizationProfile:
    """Domain normalization contract for one provider/entity schema."""

    profile_name: str
    field_rules: Mapping[str, FieldRule]
    profile_version: str = "1.0.0"
    meta_fields: frozenset[str] = field(default_factory=frozenset)
    field_aliases: Mapping[str, str] = field(default_factory=dict)
    description: str | None = None

    def __post_init__(self) -> None:
        normalized_rules = dict(
            sorted(self.field_rules.items(), key=lambda item: item[0])
        )
        normalized_aliases = dict(
            sorted(
                (
                    (str(alias), str(target))
                    for alias, target in self.field_aliases.items()
                ),
                key=lambda item: item[0],
            )
        )
        if not normalized_rules:
            raise ValueError("field_rules cannot be empty")
        for field_name, rule in normalized_rules.items():
            if field_name != rule.field_name:
                raise ValueError(
                    f"FieldRule key {field_name!r} does not match field_name {rule.field_name!r}"
                )
        for alias, target in normalized_aliases.items():
            if alias in normalized_rules:
                raise ValueError(
                    f"field_aliases cannot shadow canonical field {alias!r}"
                )
            if target not in normalized_rules:
                raise ValueError(
                    f"field_alias target {target!r} is missing from field_rules"
                )
        if not self.meta_fields.issubset(normalized_rules.keys()):
            missing = sorted(self.meta_fields.difference(normalized_rules.keys()))
            raise ValueError(
                f"meta_fields must be present in field_rules: {', '.join(missing)}"
            )
        object.__setattr__(self, "field_rules", normalized_rules)
        object.__setattr__(self, "field_aliases", normalized_aliases)

    def rule_for(self, field_name: str) -> FieldRule | None:
        """Return the rule for one field when present."""
        rule = self.field_rules.get(field_name)
        if rule is not None:
            return rule
        alias_target = self.field_aliases.get(field_name)
        if alias_target is None:
            return None
        return self.field_rules.get(alias_target)

    def field_identity(self, field_name: str) -> FieldRuleIdentity | None:
        """Return deterministic compatibility metadata for one field."""
        rule = self.rule_for(field_name)
        return None if rule is None else rule.identity

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

    @property
    def identity(self) -> NormalizationProfileIdentity:
        """Return deterministic identity for the full profile surface."""
        payload = {
            "profile_name": self.profile_name,
            "profile_version": self.profile_version,
            "meta_fields": sorted(self.meta_fields),
            "field_aliases": [
                {"alias": alias, "target": target}
                for alias, target in sorted(self.field_aliases.items())
            ],
            "field_rules": [
                {
                    "field_name": rule_identity.field_name,
                    "normalizer_ref": rule_identity.normalizer_ref,
                    "include_in_hash": rule_identity.include_in_hash,
                    "set_like": rule_identity.set_like,
                }
                for _, rule in sorted(self.field_rules.items())
                for rule_identity in (rule.identity,)
            ],
        }
        return NormalizationProfileIdentity(
            profile_name=self.profile_name,
            profile_version=self.profile_version,
            profile_hash=_sha256_hex(payload),
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
