"""Intermediate staged payload for application-owned Silver finalization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import JsonDict

__all__ = ["PreSilverRecord"]


class PreSilverBuilderProtocol(Protocol):
    """Build a final Silver record from normalized business data."""

    def __call__(
        self,
        context: PipelineContext,
        entity_id: str,
        content_hash: str,
        index: int,
        business_data: JsonDict,
    ) -> JsonDict:
        """Build finalized Silver record."""
        ...


class PreSilverStructuralPolicy(Protocol):
    """Apply structural policy to a finalized Silver record."""

    def __call__(
        self,
        context: PipelineContext,
        record: JsonDict,
        index: int,
    ) -> JsonDict | None:
        """Return updated record or ``None`` when it should be dropped."""
        ...


class PreSilverFilterProtocol(Protocol):
    """Apply Silver filter semantics to a finalized Silver record."""

    def __call__(
        self,
        context: PipelineContext,
        record: JsonDict,
        index: int,
    ) -> None:
        """Raise when the finalized record should be filtered out."""
        ...


class PreSilverEnrichmentProtocol(Protocol):
    """Pure, optional enrichment after canonical normalization and before hash."""

    def __call__(
        self, context: PipelineContext, index: int, business_data: JsonDict
    ) -> JsonDict: ...


class PreSilverEvidenceProtocol(Protocol):
    """Application-owned publication of evidence for a finalized row."""

    def __call__(self, context: PipelineContext, index: int) -> None: ...


@dataclass(frozen=True, slots=True)
class PreSilverRecord:
    """Intermediate business payload awaiting normalization and hash finalization."""

    entity_id: str
    business_data: JsonDict
    build_silver_record: PreSilverBuilderProtocol
    apply_structural_policy: PreSilverStructuralPolicy | None = None
    apply_silver_filter: PreSilverFilterProtocol | None = None
    enrich_normalized_business_data: PreSilverEnrichmentProtocol | None = None
    publish_business_evidence: PreSilverEvidenceProtocol | None = None
