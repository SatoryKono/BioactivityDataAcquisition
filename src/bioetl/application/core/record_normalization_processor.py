"""Application-owned record normalization stage for Bronze -> Silver flow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from bioetl.application.core._record_normalization_hash_support import (
    RecordNormalizationHashSupportMixin,
    _NormalizationProfileLike,
)
from bioetl.application.core.config import ContentHashPolicyByVersion
from bioetl.application.core.normalization_fallbacks import (
    UNHANDLED_FALLBACK_NORMALIZATION,
    canonicalize_json_like_string,
    normalize_named_text_field,
    normalize_special_fallback_field,
)
from bioetl.application.core.normalization_rules import NormalizationRulesPolicy
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.domain.normalization.json import (
    canonicalize_json_string,
    serialize_json_canonical,
)
from bioetl.domain.normalization.profiles import (
    FieldRule,
    resolve_normalization_profile,
)
from bioetl.domain.normalization.profiles.profile_normalizers import (
    normalize_profile_passthrough,
    normalize_profile_smiles,
)
from bioetl.domain.normalization.text import (
    normalize_string,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import JsonDict

__all__ = ["NormalizationContractError", "RecordNormalizationProcessor"]

_MALFORMED_JSON_REASON_CODE = "malformed_json_normalized_to_null"
_MALFORMED_JSON_EVENT = "silver_normalization_malformed_json"


@dataclass(frozen=True, slots=True)
class _NormalizationFinding:
    field_name: str
    reason_code: str
    action_taken: str
    dq_warn: bool = True


class NormalizationContractError(ValueError):
    """Raised when profile-backed runtime normalization would fall back implicitly."""


@dataclass(frozen=True, slots=True)
class RecordNormalizationProcessor(RecordNormalizationHashSupportMixin):
    """Normalize transformed Silver payloads before hash and merge steps."""

    provider: str
    entity_type: str | None = None
    profile: _NormalizationProfileLike | None = None
    rule_set: NormalizationRulesPolicy = field(default_factory=NormalizationRulesPolicy)
    allow_compatibility_fallback: bool = False
    content_hash_include_fields: frozenset[str] = frozenset()
    content_hash_exclude_fields: frozenset[str] = frozenset()
    content_hash_policy_by_version: ContentHashPolicyByVersion | None = None
    _normalization_findings: tuple[_NormalizationFinding, ...] = field(
        default=(),
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        if self.profile is not None or self.entity_type is None:
            return
        resolved_profile = resolve_normalization_profile(
            self.provider,
            self.entity_type,
        )
        if resolved_profile is not None:
            object.__setattr__(
                self,
                "profile",
                cast(_NormalizationProfileLike, resolved_profile),
            )

    def normalize_record(self, record: JsonDict) -> JsonDict:
        """Apply deterministic normalization to one transformed Silver record."""
        normalized = self._normalize_mapping(record)

        if "content_hash" in normalized:
            normalized["content_hash"] = self.compute_content_hash(normalized)
        version_hashes = self.compute_content_hashes_by_version(normalized)
        if self._should_project_hashes_by_version():
            normalized["_content_hashes_by_version"] = version_hashes
        return normalized

    def normalize_business_data(self, business_data: JsonDict) -> JsonDict:
        """Normalize extracted business data before Silver finalization."""
        return self._normalize_mapping(business_data)

    @property
    def normalization_findings(self) -> tuple[_NormalizationFinding, ...]:
        """Return transient runtime findings collected during the latest pass."""
        return self._normalization_findings

    def finalize_pre_silver(
        self,
        pre_silver: PreSilverRecord,
        context: PipelineContext,
        index: int,
    ) -> JsonDict | None:
        """Finalize an intermediate pre-silver payload into a Silver record."""
        normalized_business_data = self.normalize_business_data(
            pre_silver.business_data
        )
        version_hashes = self.compute_content_hashes_by_version(
            normalized_business_data
        )
        content_hash = (
            version_hashes.get(self.content_hash_policy_by_version.active_version)
            if self.content_hash_policy_by_version is not None
            else None
        )
        if content_hash is None:
            content_hash = self.compute_content_hash(normalized_business_data)
        silver_record = pre_silver.build_silver_record(
            context,
            pre_silver.entity_id,
            content_hash,
            index,
            normalized_business_data,
        )
        silver_record = self.project_normalization_findings(
            silver_record,
            context=context,
            index=index,
        )
        if self._should_project_hashes_by_version():
            silver_record["_content_hashes_by_version"] = version_hashes
        if pre_silver.apply_structural_policy is not None:
            projected_record = pre_silver.apply_structural_policy(
                context,
                silver_record,
                index,
            )
            if projected_record is None:
                return None
            silver_record = projected_record
        if pre_silver.apply_silver_filter is not None:
            pre_silver.apply_silver_filter(context, silver_record, index)
        return silver_record

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
                finding = self._profile_json_runtime_finding(
                    profile_rule,
                    field_name=field_name,
                    raw_value=value,
                    normalized_value=normalized_value,
                )
                if finding is not None:
                    findings.append(finding)
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
        if self._should_forbid_fallback(field_name):
            self._raise_profile_gap(field_name)
        normalized_special = self._normalize_special_field(field_name, value)
        if normalized_special is not UNHANDLED_FALLBACK_NORMALIZATION:
            return normalized_special
        if field_name == "issn" and isinstance(value, list):
            return list(value)
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

        stripped = normalize_string(value)
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
        if rule.normalizer is normalize_profile_passthrough:
            return value
        normalized = rule.apply(value, record=record)
        if isinstance(normalized, dict | list):
            return serialize_json_canonical(normalized)
        if isinstance(normalized, str):
            return self._normalize_string_field(rule.field_name, normalized)
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
        return normalize_profile_smiles(
            value,
            is_canonical=(field_name == "canonical_smiles"),
        )

    def project_normalization_findings(
        self,
        record: JsonDict,
        *,
        context: PipelineContext | None = None,
        index: int | None = None,
    ) -> JsonDict:
        """Project transient normalization findings into DQ flags and logs."""
        if not self._normalization_findings:
            return record

        projected = dict(record)
        projected["_dq_warn"] = True

        if context is not None:
            for finding in self._normalization_findings:
                context.logger.warning(
                    _MALFORMED_JSON_EVENT,
                    provider=self.provider,
                    entity_type=self.entity_type,
                    record_index=index,
                    reason_code=finding.reason_code,
                    field=finding.field_name,
                    action_taken=finding.action_taken,
                    dq_warn=finding.dq_warn,
                    proposed_normalized_outcome=None,
                )

        return projected

    def _profile_json_runtime_finding(
        self,
        rule: FieldRule,
        *,
        field_name: str,
        raw_value: object,
        normalized_value: object,
    ) -> _NormalizationFinding | None:
        if normalized_value is not None or not isinstance(raw_value, str):
            return None

        normalized_text = normalize_string(raw_value)
        if normalized_text is None:
            return None
        if not self._rule_uses_json_policy(rule):
            return None

        try:
            canonicalize_json_string(normalized_text)
        except ValueError:
            return _NormalizationFinding(
                field_name=field_name,
                reason_code=_MALFORMED_JSON_REASON_CODE,
                action_taken="set_null_and_warn",
            )
        return None

    def _rule_uses_json_policy(self, rule: FieldRule) -> bool:
        notes = (rule.notes or "").casefold()
        normalizer_name = getattr(rule.normalizer, "__name__", "").casefold()
        return "json" in notes or "json" in normalizer_name

    def _should_forbid_fallback(self, field_name: str) -> bool:
        return (
            self.profile is not None
            and not self.allow_compatibility_fallback
            and not field_name.startswith("_")
            and field_name not in self.rule_set.passthrough_fields
        )

    def _raise_profile_gap(self, field_name: str) -> None:
        entity_label = self.entity_type or "<unknown>"
        raise NormalizationContractError(
            "profile-backed normalization cannot fall back implicitly for "
            f"{self.provider}.{entity_label} field {field_name!r}; "
            "add an explicit normalization profile rule or enable "
            "allow_compatibility_fallback for bounded compatibility paths"
        )
