"""Application-owned record normalization stage for Bronze -> Silver flow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.application.core.config import (
    ContentHashPolicyByVersion,
    ContentHashVersionPolicy,
)
from bioetl.application.core.normalization_rules import NormalizationRulesPolicy
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.domain.normalization.profiles import (
    FieldRule,
    NormalizationProfile,
    resolve_normalization_profile,
)
from bioetl.domain.normalization.dates import normalize_partial_date
from bioetl.domain.normalization.identifiers import normalize_doi, normalize_pmid
from bioetl.domain.normalization.json import (
    canonicalize_json_string,
    serialize_json_canonical,
)
from bioetl.domain.normalization.text import (
    normalize_abstract,
    normalize_oa_status,
    normalize_string,
    normalize_title,
)
from bioetl.domain.transformations import generate_content_hash

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import JsonDict

__all__ = ["RecordNormalizationProcessor"]


_JSON_START_TOKENS = ("{", "[")
_JSON_END_TOKENS = ("}", "]")
_PMID_SUFFIXES = ("_pmid",)
_DOI_SUFFIXES = ("_doi",)
_UNHANDLED = object()


def _is_json_like_string(value: str) -> bool:
    stripped = value.strip()
    if len(stripped) < 2:
        return False
    return stripped.startswith(_JSON_START_TOKENS) and stripped.endswith(
        _JSON_END_TOKENS
    )


@dataclass(frozen=True, slots=True)
class RecordNormalizationProcessor:
    """Normalize transformed Silver payloads before hash and merge steps."""

    provider: str
    entity_type: str | None = None
    profile: NormalizationProfile | None = None
    rule_set: NormalizationRulesPolicy = field(default_factory=NormalizationRulesPolicy)
    content_hash_include_fields: frozenset[str] = frozenset()
    content_hash_exclude_fields: frozenset[str] = frozenset()
    content_hash_policy_by_version: ContentHashPolicyByVersion | None = None

    def __post_init__(self) -> None:
        if self.profile is not None or self.entity_type is None:
            return
        resolved_profile = resolve_normalization_profile(
            self.provider,
            self.entity_type,
        )
        if resolved_profile is not None:
            object.__setattr__(self, "profile", resolved_profile)

    def _should_project_hashes_by_version(self) -> bool:
        """Return True when rollout semantics require versioned content hashes."""
        policy = self.content_hash_policy_by_version
        return policy is not None and policy.requires_projected_hashes

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

    def compute_content_hash(
        self,
        record: JsonDict,
        *,
        contract_version: str | None = None,
    ) -> str:
        """Compute canonical content hash for an already-normalized payload."""
        include_fields, exclude_fields = self._resolve_hash_policy(
            contract_version=contract_version
        )
        return str(
            generate_content_hash(
                record,
                self.provider,
                exclude_none=True,
                include_fields=include_fields,
                exclude_fields=exclude_fields,
                set_like_fields=(
                    None
                    if self.profile is None
                    else set(self.profile.set_like_fields)
                ),
            )
        )

    def compute_content_hashes_by_version(self, record: JsonDict) -> dict[str, str]:
        """Compute per-version content hashes when rollout policy requires it."""
        if not self._should_project_hashes_by_version():
            return {}
        assert self.content_hash_policy_by_version is not None
        return {
            policy.version: self.compute_content_hash(
                record,
                contract_version=policy.version,
            )
            for policy in self.content_hash_policy_by_version.policies
        }

    def _profile_hash_fields(self) -> tuple[frozenset[str], frozenset[str]]:
        """Return include/exclude fields supplied by the normalization profile."""
        if self.profile is None:
            return frozenset(), frozenset()
        return self.profile.hash_included_fields, self.profile.hash_excluded_fields

    def _select_hash_policy(
        self,
        *,
        contract_version: str | None,
    ) -> ContentHashVersionPolicy | None:
        """Resolve the version-specific hash policy for one contract version."""
        if self.content_hash_policy_by_version is None:
            return None
        target_version = (
            contract_version or self.content_hash_policy_by_version.active_version
        )
        return (
            self.content_hash_policy_by_version.for_version(target_version)
            or self.content_hash_policy_by_version.active_policy
        )

    def _resolve_hash_include_fields(
        self,
        *,
        profile_include: frozenset[str],
        policy: ContentHashVersionPolicy | None,
    ) -> set[str] | None:
        """Return the include-field set for content hash generation."""
        if policy is not None and policy.include_fields:
            include_source = policy.include_fields
        else:
            include_source = profile_include or self.content_hash_include_fields
        return set(include_source) if include_source else None

    def _resolve_hash_exclude_fields(
        self,
        *,
        profile_exclude: frozenset[str],
        policy: ContentHashVersionPolicy | None,
    ) -> set[str]:
        """Return the exclude-field set for content hash generation."""
        return (
            set(self.content_hash_exclude_fields)
            | set(profile_exclude)
            | (set(policy.exclude_fields) if policy is not None else set())
            | {"entity_id", "content_hash", "_content_hashes_by_version"}
        )

    def _resolve_hash_policy(
        self,
        *,
        contract_version: str | None,
    ) -> tuple[set[str] | None, set[str]]:
        profile_include, profile_exclude = self._profile_hash_fields()
        policy = self._select_hash_policy(contract_version=contract_version)
        return (
            self._resolve_hash_include_fields(
                profile_include=profile_include,
                policy=policy,
            ),
            self._resolve_hash_exclude_fields(
                profile_exclude=profile_exclude,
                policy=policy,
            ),
        )

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
        normalized: JsonDict = {}
        for field_name, value in record.items():
            if self._is_passthrough_field(field_name):
                normalized[field_name] = value
                continue
            normalized[field_name] = self._normalize_field_value(field_name, value)
        return normalized

    def _is_passthrough_field(self, field_name: str) -> bool:
        if field_name in self.rule_set.passthrough_fields:
            return True
        if field_name.startswith("_"):
            return self._profile_rule(field_name) is None
        return False

    def _normalize_field_value(self, field_name: str, value: object) -> object:
        profile_rule = self._profile_rule(field_name)
        if profile_rule is not None:
            return self._normalize_profile_field_value(profile_rule, value)
        normalized_special = self._normalize_special_field(field_name, value)
        if normalized_special is not _UNHANDLED:
            return normalized_special
        if field_name == "issn" and isinstance(value, list):
            return list(value)
        if isinstance(value, dict | list):
            return serialize_json_canonical(value)
        if not isinstance(value, str):
            return value
        return self._normalize_string_field(field_name, value)

    def _normalize_special_field(self, field_name: str, value: object) -> object:
        if value is None:
            return None
        if self._is_doi_field(field_name):
            return normalize_doi(value) if isinstance(value, str) else value
        if self._is_pmid_field(field_name):
            if isinstance(value, bool):
                return None
            return normalize_pmid(value) if isinstance(value, str | int) else value
        if self._is_date_field(field_name):
            return normalize_partial_date(value) if isinstance(value, str) else value
        return _UNHANDLED

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

    def _normalize_profile_field_value(self, rule: FieldRule, value: object) -> object:
        normalized = rule.apply(value)
        if isinstance(normalized, dict | list):
            return serialize_json_canonical(normalized)
        return normalized

    def _normalize_named_text_field(
        self,
        field_name: str,
        value: str,
    ) -> str | None:
        if field_name in self.rule_set.title_fields:
            normalized_title: str | None = normalize_title(value)
            return normalized_title
        if field_name in self.rule_set.abstract_fields:
            normalized_abstract: str | None = normalize_abstract(value)
            return normalized_abstract
        if field_name in self.rule_set.oa_status_fields:
            normalized_oa_status: str | None = normalize_oa_status(value)
            return normalized_oa_status
        return None

    def _canonicalize_json_like_string(self, value: str) -> str:
        if not _is_json_like_string(value):
            return value
        try:
            canonical_json = canonicalize_json_string(value)
        except ValueError:
            return value
        return canonical_json if canonical_json is not None else value

    def _is_doi_field(self, field_name: str) -> bool:
        return field_name in self.rule_set.doi_fields or field_name.endswith(
            _DOI_SUFFIXES
        )

    def _is_pmid_field(self, field_name: str) -> bool:
        return field_name in self.rule_set.pmid_fields or field_name.endswith(
            _PMID_SUFFIXES
        )

    def _is_date_field(self, field_name: str) -> bool:
        if field_name.endswith("_ts"):
            return False
        return (
            field_name in self.rule_set.date_fields
            or field_name.endswith("_date")
            or field_name.startswith("date_")
        )
