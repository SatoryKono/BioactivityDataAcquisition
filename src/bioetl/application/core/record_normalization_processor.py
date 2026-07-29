# pyright: reportInvalidCast=false
# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Application-owned record normalization stage for Bronze -> Silver flow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from bioetl.application.core._record_normalization_contract import (
    NormalizationContractError,
    _NormalizationFinding,
)
from bioetl.application.core._record_normalization_hash_support import (
    RecordNormalizationHashSupportMixin,
    _NormalizationProfileLike,
)
from bioetl.application.core._record_normalization_mapping import (
    RecordNormalizationMappingMixin,
)
from bioetl.application.core._record_normalization_runtime_support import (
    project_normalization_findings as _project_normalization_findings,
)
from bioetl.application.core.normalization_rules import NormalizationRulesPolicy
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.core.record_normalization_finalization import (
    finalize_pre_silver_record,
)
from bioetl.application.core.record_processor_config import ContentHashPolicyByVersion

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import JsonDict

__all__ = ["NormalizationContractError", "RecordNormalizationProcessor"]


@dataclass(frozen=True, slots=True)
class RecordNormalizationProcessor(
    RecordNormalizationMappingMixin,
    RecordNormalizationHashSupportMixin,
):
    """Normalize transformed Silver payloads before hash and merge steps."""

    provider: str
    entity_type: str | None = None
    profile: _NormalizationProfileLike | None = None
    rule_set: NormalizationRulesPolicy = field(default_factory=NormalizationRulesPolicy)
    allow_compatibility_fallback: bool = False
    content_hash_policy_authoritative: bool = False
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
        from bioetl.domain.normalization.profiles import resolve_normalization_profile

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
        return finalize_pre_silver_record(
            self,
            pre_silver,
            context=context,
            index=index,
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

        return _project_normalization_findings(
            self._normalization_findings,
            record,
            context=context,
            index=index,
            provider=self.provider,
            entity_type=self.entity_type,
        )
