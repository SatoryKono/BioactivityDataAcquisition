# Host attrs/methods provided by concrete composition.
"""Metadata handling mixin for ChEMBL adapter."""

from __future__ import annotations

__all__ = ["ChemblMetadataMixin"]


from typing import TYPE_CHECKING, Any, cast

from bioetl.infrastructure.adapters.chembl.constants import CHEMBL_API_BASE
from bioetl.infrastructure.adapters.common.source_metadata_capability import (
    clear_source_metadata_collector,
    consume_source_metadata,
    get_request_count,
)

if TYPE_CHECKING:
    from bioetl.domain.models.filter import ExtractionParams
    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )


class ChemblMetadataMixin:
    """Mixin for metadata-related logic in ChEMBL adapter."""

    _request_collector: APIRequestCollector = cast(
        Any, None
    )  # Any: host attr default (PD3)
    _extraction_params: ExtractionParams = cast(
        Any, None
    )  # Any: host attr default (PD3)

    def get_source_metadata(self, api_version: str | None = None) -> SourceMetadata:
        """Get API request metadata and clear collector.

        Args:
            api_version: ChEMBL API version string to embed in metadata
                (e.g., ``"34"``); omitted from metadata when None.

        Returns:
            SourceMetadata with aggregated request statistics and extraction params;
            the internal request collector is cleared after construction.
        """
        extraction_qs = self._extraction_params.to_query_string() or None
        return consume_source_metadata(
            collector=self._request_collector,
            url=CHEMBL_API_BASE,
            api_version=api_version,
            query_string=extraction_qs,
        )

    def clear_request_collector(self) -> None:
        """Clear the collector without returning metadata."""
        clear_source_metadata_collector(collector=self._request_collector)

    @property
    def request_count(self) -> int:
        """Number of recorded API requests since last clear."""
        return int(get_request_count(collector=self._request_collector))
