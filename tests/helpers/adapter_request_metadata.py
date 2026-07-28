"""Shared request-metadata contract helpers for provider adapters (T-TEST-008 / #6781)."""

from __future__ import annotations

from typing import Protocol

from bioetl.domain.models.metadata import SourceMetadata


class _RequestMetadataAdapter(Protocol):
    request_count: int

    def get_source_metadata(self, api_version: str | None = None) -> SourceMetadata: ...

    def clear_request_collector(self) -> None: ...


def assert_request_count_starts_at_zero(adapter: _RequestMetadataAdapter) -> None:
    """New adapters expose an empty request collector."""
    assert adapter.request_count == 0


def assert_metadata_snapshot_consumes_requests(
    adapter: _RequestMetadataAdapter,
    *,
    expected_url: str,
    api_version: str | None = "1",
    expected_total_requests: int = 1,
) -> None:
    """get_source_metadata returns SourceMetadata and clears the collector."""
    metadata = (
        adapter.get_source_metadata(api_version=api_version)
        if api_version is not None
        else adapter.get_source_metadata()
    )
    assert isinstance(metadata, SourceMetadata)
    assert metadata.type == "api"
    assert metadata.url == expected_url
    if api_version is not None:
        assert metadata.api_version == api_version
    assert metadata.total_requests == expected_total_requests
    assert adapter.request_count == 0


def assert_clear_request_collector_resets_count(
    adapter: _RequestMetadataAdapter,
) -> None:
    """clear_request_collector drops accumulated request state."""
    adapter.clear_request_collector()
    assert adapter.request_count == 0
