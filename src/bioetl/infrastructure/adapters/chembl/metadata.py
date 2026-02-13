"""Metadata handling mixin for ChEMBL adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.infrastructure.adapters.chembl.constants import CHEMBL_API_BASE

if TYPE_CHECKING:
    from bioetl.domain.models.filter import ExtractionParams
    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )


class ChemblMetadataMixin:
    """Mixin for metadata-related logic in ChEMBL adapter."""

    _request_collector: APIRequestCollector
    _extraction_params: ExtractionParams

    def get_source_metadata(self, api_version: str | None = None) -> SourceMetadata:
        """Get API request metadata and clear collector."""
        extraction_qs = self._extraction_params.to_query_string() or None
        metadata = self._request_collector.to_source_metadata(
            source_type="api",
            url=CHEMBL_API_BASE,
            api_version=api_version,
            query_string=extraction_qs,
        )
        self._request_collector.clear()
        return metadata

    def clear_request_collector(self) -> None:
        """Clear the collector without returning metadata."""
        self._request_collector.clear()

    @property
    def request_count(self) -> int:
        """Number of recorded API requests since last clear."""
        return self._request_collector.request_count
