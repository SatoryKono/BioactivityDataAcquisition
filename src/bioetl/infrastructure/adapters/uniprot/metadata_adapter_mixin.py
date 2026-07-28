# pyright: reportUninitializedInstanceVariable=false
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Metadata/introspection adapter mixin for UniProt adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.common.source_metadata_capability import (
    clear_source_metadata_collector,
    consume_source_metadata,
    get_request_count,
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
        return consume_source_metadata(
            collector=self._request_collector,
            url=self.base_url,
            api_version=api_version,
        )

    def clear_request_collector(self) -> None:
        """Clear the request collector without returning metadata."""
        clear_source_metadata_collector(collector=self._request_collector)

    @property
    def request_count(self) -> int:
        """Number of recorded API requests since last clear."""
        return get_request_count(collector=self._request_collector)


__all__ = ["UniProtAdapterMetadataMixin"]
