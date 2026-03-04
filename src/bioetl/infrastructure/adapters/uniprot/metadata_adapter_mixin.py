"""Metadata/introspection adapter mixin for UniProt adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import SourceMetadata


class _RequestCollectorPort(Protocol):
    """Protocol for request collector used by metadata mixin."""

    def to_source_metadata(
        self,
        source_type: str = "api",
        url: str | None = None,
        api_version: str | None = None,
        query_string: str | None = None,
    ) -> SourceMetadata:
        """Build source metadata from collected requests."""
        ...

    def clear(self) -> None:
        """Clear collected request snapshots."""
        ...

    @property
    def request_count(self) -> int:
        """Current number of captured requests."""
        ...


class UniProtAdapterMetadataMixin:
    """Adds request-metadata and repr helpers to UniProt adapter."""

    # Host-class attributes (provided by UniProtAdapter.__init__)
    api_key: str | None
    base_url: str
    _request_collector: _RequestCollectorPort

    def _get_health_endpoint(self) -> str:
        """Return health check endpoint."""
        return "/uniprotkb/search"

    def __repr__(self) -> str:
        key_info = "with API key" if self.api_key else "without API key"
        return f"UniProtAdapter(base_url='{self.base_url}', {key_info})"

    def get_source_metadata(
        self,
        api_version: str | None = None,
    ) -> SourceMetadata:
        """Get API request metadata and clear collector."""
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
