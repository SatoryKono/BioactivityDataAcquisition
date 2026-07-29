"""PreSilver finalization helper for record normalization processors."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.application.core.pre_silver_record import PreSilverRecord

if TYPE_CHECKING:
    from bioetl.application.core.record_processor_config import (
        ContentHashPolicyByVersion,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import JsonDict

__all__ = ["PreSilverFinalizerProtocol", "finalize_pre_silver_record"]


class PreSilverFinalizerProtocol(Protocol):
    """Normalization surface required to finalize a staged Silver payload."""
    @property
    def content_hash_policy_by_version(
        self,
    ) -> ContentHashPolicyByVersion | None: ...
    def normalize_business_data(self, business_data: JsonDict) -> JsonDict:
        """Normalize extracted business data before Silver finalization."""
        ...
    def compute_content_hashes_by_version(self, record: JsonDict) -> dict[str, str]:
        """Compute rollout-aware content hashes for normalized business data."""
        ...
    def compute_content_hash(self, record: JsonDict) -> str:
        """Compute the active content hash for normalized business data."""
        ...
    def project_normalization_findings(
        self,
        record: JsonDict,
        *,
        context: PipelineContext | None = None,
        index: int | None = None,
    ) -> JsonDict:
        """Project transient normalization findings into a Silver record."""
        ...
    def _should_project_hashes_by_version(self) -> bool:
        """Return whether versioned hash payload should be projected."""
        ...


def _active_content_hash(
    normalizer: PreSilverFinalizerProtocol,
    normalized_business_data: JsonDict,
    version_hashes: dict[str, str],
) -> str:
    policy = normalizer.content_hash_policy_by_version
    active_version = getattr(policy, "active_version", None)
    content_hash = version_hashes.get(active_version) if active_version else None
    return content_hash or normalizer.compute_content_hash(normalized_business_data)


def finalize_pre_silver_record(
    normalizer: PreSilverFinalizerProtocol,
    pre_silver: PreSilverRecord,
    *,
    context: PipelineContext,
    index: int,
) -> JsonDict | None:
    """Finalize an intermediate pre-silver payload into a Silver record."""
    normalized_business_data = normalizer.normalize_business_data(
        pre_silver.business_data
    )
    version_hashes = normalizer.compute_content_hashes_by_version(
        normalized_business_data
    )
    content_hash = _active_content_hash(
        normalizer,
        normalized_business_data,
        version_hashes,
    )
    silver_record = pre_silver.build_silver_record(
        context,
        pre_silver.entity_id,
        content_hash,
        index,
        normalized_business_data,
    )
    silver_record = normalizer.project_normalization_findings(
        silver_record,
        context=context,
        index=index,
    )
    if normalizer._should_project_hashes_by_version():
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
