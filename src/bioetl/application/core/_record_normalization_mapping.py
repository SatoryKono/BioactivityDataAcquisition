# Host attrs/methods provided by concrete composition.
"""Field-mapping normalization helpers for RecordNormalizationProcessor."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core._record_normalization_contract import (
    _NormalizationFinding,
)
from bioetl.application.core._record_normalization_runtime_support import (
    profile_json_runtime_finding,
    raise_profile_gap,
    should_forbid_fallback,
)
from bioetl.application.core.normalization_fallbacks import (
    UNHANDLED_FALLBACK_NORMALIZATION,
    canonicalize_json_like_string,
    normalize_named_text_field,
    normalize_plain_text,
    normalize_special_fallback_field,
)
from bioetl.domain.normalization.json import serialize_json_canonical
from bioetl.domain.normalization.profiles.base import (
    _normalizer_accepts_record_context as _profile_rule_accepts_record_context,
)

if TYPE_CHECKING:
    from bioetl.application.core._record_normalization_hash_support import (
        _NormalizationProfileLike,
    )
    from bioetl.application.core.normalization_rules import NormalizationRulesPolicy
    from bioetl.domain.normalization.profiles import FieldRule
    from bioetl.domain.types import JsonDict


class RecordNormalizationMappingMixin:
    """Own field-by-field mapping normalization for Silver record payloads."""

    provider: str = cast(Any, None)  # Any: host attr default (PD6)
    entity_type: str | None = cast(Any, None)  # Any: host attr default (PD6)
    profile: _NormalizationProfileLike | None = cast(
        Any, None
    )  # Any: host attr default (PD6)
    rule_set: NormalizationRulesPolicy = cast(Any, None)  # Any: host attr default (PD6)
    allow_compatibility_fallback: bool = cast(Any, None)  # Any: host attr default (PD6)

    def _normalize_mapping(self, record: JsonDict) -> JsonDict:
        object.__setattr__(self, "_normalization_findings", ())
        normalized: JsonDict = {}
        findings: list[_NormalizationFinding] = []
        for field_name, value in record.items():
            if self._is_passthrough_field(field_name):
                normalized[field_name] = value
                continue
            normalized_value = self._normalize_field_value(
                field_name,
                value,
                record,
            )
            normalized[field_name] = normalized_value
            profile_rule = self._profile_rule(field_name)
            if profile_rule is not None:
                finding = profile_json_runtime_finding(
                    profile_rule,
                    field_name=field_name,
                    raw_value=value,
                    normalized_value=normalized_value,
                    finding_factory=_NormalizationFinding,
                )
                if finding is not None:
                    findings.append(finding)
        normalized = self._reapply_record_aware_profile_rules(normalized)
        object.__setattr__(self, "_normalization_findings", tuple(findings))
        return normalized

    def _is_passthrough_field(self, field_name: str) -> bool:
        if field_name in self.rule_set.passthrough_fields:
            return True
        if field_name.startswith("_"):
            return self._profile_rule(field_name) is None
        return False

    def _normalize_field_value(
        self,
        field_name: str,
        value: object,
        record: JsonDict,
    ) -> object:
        profile_rule = self._profile_rule(field_name)
        if profile_rule is not None:
            return self._normalize_profile_field_value(profile_rule, value, record)
        if should_forbid_fallback(
            has_profile=self.profile is not None,
            allow_compatibility_fallback=self.allow_compatibility_fallback,
            field_name=field_name,
            passthrough_fields=self.rule_set.passthrough_fields,
        ):
            raise_profile_gap(self.provider, self.entity_type, field_name)
        normalized_special = self._normalize_special_field(field_name, value)
        if normalized_special is not UNHANDLED_FALLBACK_NORMALIZATION:
            return normalized_special
        if isinstance(value, dict | list):
            return serialize_json_canonical(value)
        if not isinstance(value, str):
            return value
        return self._normalize_string_field(field_name, value)

    def _normalize_special_field(self, field_name: str, value: object) -> object:
        return normalize_special_fallback_field(
            field_name,
            value,
            rule_set=self.rule_set,
        )

    def _normalize_string_field(self, field_name: str, value: str) -> str | None:
        normalized_text = self._normalize_named_text_field(field_name, value)
        if normalized_text is not None:
            return normalized_text

        stripped = normalize_plain_text(value)
        if stripped is None:
            return None
        return self._canonicalize_json_like_string(stripped)

    def _profile_rule(self, field_name: str) -> FieldRule | None:
        if self.profile is None:
            return None
        return self.profile.rule_for(field_name)

    def _normalize_profile_field_value(
        self,
        rule: FieldRule,
        value: object,
        record: JsonDict,
    ) -> object:
        from bioetl.domain.normalization.profiles.profile_normalizers import (
            normalize_profile_passthrough,
        )

        if rule.normalizer is normalize_profile_passthrough:
            return value
        normalized = rule.apply(value, record=record)
        if isinstance(normalized, dict | list):
            return serialize_json_canonical(normalized)
        if isinstance(normalized, str):
            return self._normalize_string_field(rule.field_name, normalized)
        return normalized

    def _reapply_record_aware_profile_rules(self, record: JsonDict) -> JsonDict:
        """Recompute derived profile fields against the normalized sibling context.

        Some profile-backed fields are intentionally derived from sibling values
        instead of from their own raw input slot. Reapplying only record-aware
        rules against the normalized payload preserves deterministic derivation
        for ontology companions, publication taxonomy, and other profile-backed
        sidecars without broadening the payload beyond fields already staged by
        the transformer.
        """
        if self.profile is None:
            return record

        normalized = dict(record)
        for field_name in tuple(normalized.keys()):
            rule = self._profile_rule(field_name)
            if rule is None or not _profile_rule_accepts_record_context(
                rule.normalizer
            ):
                continue
            normalized[field_name] = self._normalize_profile_field_value(
                rule,
                normalized.get(field_name),
                normalized,
            )
        return normalized

    def _normalize_named_text_field(
        self,
        field_name: str,
        value: str,
    ) -> str | None:
        return normalize_named_text_field(
            field_name,
            value,
            rule_set=self.rule_set,
        )

    def _canonicalize_json_like_string(self, value: str) -> str:
        return canonicalize_json_like_string(value)

    def _normalize_smiles_field(self, field_name: str, value: object) -> str | None:
        from bioetl.domain.normalization.profiles.profile_normalizers import (
            normalize_profile_smiles,
        )

        return normalize_profile_smiles(
            value,
            is_canonical=(field_name == "canonical_smiles"),
        )
