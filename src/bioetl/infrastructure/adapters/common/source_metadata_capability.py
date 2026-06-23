"""Shared helpers for adapter request-metadata capabilities."""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from bioetl.domain.models.metadata import SourceMetadata

__all__ = [
    "SourceMetadataCollectorProtocol",
    "clear_source_metadata_collector",
    "consume_source_metadata",
    "get_request_count",
]


@runtime_checkable
class SourceMetadataCollectorProtocol(Protocol):
    """Minimal collector surface required for source-metadata helpers."""

    def to_source_metadata(
        self,
        source_type: Literal["api", "csv", "parquet"] = "api",
        url: str | None = None,
        api_version: str | None = None,
        query_string: str | None = None,
    ) -> SourceMetadata:
        """Build source metadata snapshot from collected request data."""
        ...

    def clear(self) -> None:
        """Reset collected request state."""
        ...

    @property
    def request_count(self) -> int:
        """Return the number of HTTP requests recorded so far."""
        ...


def consume_source_metadata(
    *,
    collector: SourceMetadataCollectorProtocol,
    url: str | None,
    api_version: str | None = None,
    query_string: str | None = None,
    source_type: Literal["api", "csv", "parquet"] = "api",
    default_api_version: str | None = None,
) -> SourceMetadata:
    """Return a metadata snapshot and clear the underlying request collector."""
    resolved_api_version = (
        api_version if api_version is not None else default_api_version
    )
    metadata = collector.to_source_metadata(
        source_type=source_type,
        url=url,
        api_version=resolved_api_version,
        query_string=query_string,
    )
    collector.clear()
    return metadata


def clear_source_metadata_collector(
    *,
    collector: SourceMetadataCollectorProtocol,
) -> None:
    """Clear request metadata state without returning a snapshot."""
    collector.clear()


def get_request_count(
    *,
    collector: SourceMetadataCollectorProtocol,
) -> int:
    """Return the number of recorded requests in the collector."""
    return collector.request_count
