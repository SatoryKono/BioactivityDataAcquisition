"""Metadata/introspection adapter mixin for UniProt adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import SourceMetadata


class UniProtAdapterMetadataMixin:
    """Adds request-metadata and repr helpers to UniProt adapter."""

    # Host-class attributes (provided by UniProtAdapter.__init__)
    api_key: str | None
    base_url: str
    _request_collector: APIRequestCollector

    def _get_health_endpoint(self) -> str:
        """Return health check endpoint.

        Returns:
            Endpoint path string used for UniProt health probe requests.
        """
        return "/uniprotkb/search"

    def __repr__(self) -> str:
        key_info = "with API key" if self.api_key else "without API key"
        return f"UniProtAdapter(base_url='{self.base_url}', {key_info})"

    def get_source_metadata(
        self,
        api_version: str | None = None,
    ) -> SourceMetadata:
        """Get API request metadata and clear collector.

        Returns:
            SourceMetadata aggregated from all recorded API requests since last clear.
        """
        metadata = self._request_collector.to_source_metadata(
            source_type="api", url=self.base_url, api_version=api_version
        )
        self._request_collector.clear()
        return metadata

    def clear_request_collector(self) -> None:
        """Clear the request collector without returning metadata."""
        self._request_collector.clear()

    @property
    def request_count(self) -> int:
        """Number of recorded API requests since last clear."""
        return self._request_collector.request_count


__all__ = ["UniProtAdapterMetadataMixin"]
