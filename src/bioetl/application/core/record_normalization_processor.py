"""Application-owned record normalization stage for Bronze -> Silver flow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.application.core.config import ContentHashPolicyByVersion
from bioetl.application.core.normalization_rules import NormalizationRulesPolicy
from bioetl.application.core.pre_silver_record import PreSilverRecord
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
    rule_set: NormalizationRulesPolicy = field(default_factory=NormalizationRulesPolicy)
    content_hash_include_fields: frozenset[str] = frozenset()
    content_hash_exclude_fields: frozenset[str] = frozenset()
    content_hash_policy_by_version: ContentHashPolicyByVersion | None = None

    def normalize_record(self, record: JsonDict) -> JsonDict:
        """Apply deterministic normalization to one transformed Silver record."""
        normalized = self._normalize_mapping(record)

        if "content_hash" in normalized:
            normalized["content_hash"] = self.compute_content_hash(normalized)
        version_hashes = self.compute_content_hashes_by_version(normalized)
        if self.content_hash_policy_by_version is not None and self.content_hash_policy_by_version.is_multi_version:
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
            )
        )

    def compute_content_hashes_by_version(self, record: JsonDict) -> dict[str, str]:
        """Compute per-version content hashes when rollout policy requires it."""
        if self.content_hash_policy_by_version is None:
            return {}
        return {
            policy.version: self.compute_content_hash(
                record,
                contract_version=policy.version,
            )
            for policy in self.content_hash_policy_by_version.policies
        }

    def _resolve_hash_policy(
        self,
        *,
        contract_version: str | None,
    ) -> tuple[set[str] | None, set[str]]:
        policy = None
        if self.content_hash_policy_by_version is not None:
            target_version = contract_version or self.content_hash_policy_by_version.active_version
            policy = self.content_hash_policy_by_version.for_version(target_version)
            if policy is None:
                policy = self.content_hash_policy_by_version.active_policy
        include_source = (
            policy.include_fields if policy is not None else self.content_hash_include_fields
        )
        exclude_source = (
            policy.exclude_fields if policy is not None else self.content_hash_exclude_fields
        )
        include_fields = set(include_source) if include_source else None
        exclude_fields = set(exclude_source) | {
            "entity_id",
            "content_hash",
            "_content_hashes_by_version",
        }
        return include_fields, exclude_fields

    def finalize_pre_silver(
        self,
        pre_silver: PreSilverRecord,
        context: PipelineContext,
        index: int,
    ) -> JsonDict | None:
        """Finalize an intermediate pre-silver payload into a Silver record."""
        normalized_business_data = self.normalize_business_data(pre_silver.business_data)
        version_hashes = self.compute_content_hashes_by_version(normalized_business_data)
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
        if self.content_hash_policy_by_version is not None and self.content_hash_policy_by_version.is_multi_version:
            silver_record["_content_hashes_by_version"] = version_hashes
        if pre_silver.apply_structural_policy is not None:
            silver_record = pre_silver.apply_structural_policy(
                context,
                silver_record,
                index,
            )
            if silver_record is None:
                return None
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
        return (
            field_name.startswith("_") or field_name in self.rule_set.passthrough_fields
        )

    def _normalize_field_value(self, field_name: str, value: object) -> object:
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

    def _normalize_named_text_field(
        self,
        field_name: str,
        value: str,
    ) -> str | None:
        if field_name in self.rule_set.title_fields:
            return normalize_title(value)
        if field_name in self.rule_set.abstract_fields:
            return normalize_abstract(value)
        if field_name in self.rule_set.oa_status_fields:
            return normalize_oa_status(value)
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
