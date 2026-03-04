"""Adapter helper mixin for OpenAlex adapter utility and metadata methods."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from bioetl.domain.types import BronzeRecord, HealthStatus

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import SourceMetadata

_OPENALEX_BASE_URL = "https://api.openalex.org"


class _RequestCollectorPort(Protocol):
    """Protocol for request collector used by adapter mixins."""

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


class OpenAlexAdapterHelpersMixin:
    """Utility helpers extracted from the main OpenAlex adapter."""

    # Host-class attributes (provided by OpenAlexAdapter.__post_init__)
    mailto: str
    _request_collector: _RequestCollectorPort

    def _build_headers(self) -> dict[str, str]:
        """Build request headers for OpenAlex API."""
        return {
            "User-Agent": f"BioETL/1.0 (mailto:{self.mailto})",
            "Accept": "application/json",
        }

    def _build_base_params(self) -> dict[str, str]:
        """Build base query parameters with mailto for polite pool."""
        return {"mailto": self.mailto}

    @staticmethod
    def _normalize_doi(doi: str) -> str | None:
        """Normalize DOI by removing URL prefix."""
        if not doi:
            return None
        doi = doi.strip()
        if doi.startswith("https://doi.org/"):
            return doi[16:]
        if doi.startswith("http://doi.org/"):
            return doi[15:]
        if doi.startswith("doi:"):
            return doi[4:]
        return doi

    @staticmethod
    def _escape_title_for_search(title: str) -> str:
        """Escape title for OpenAlex title.search filter."""
        cleaned = title.replace(":", " ").replace("|", " ").replace(",", " ")
        return "+".join(cleaned.split())

    @staticmethod
    def _extract_doi_from_record(record: BronzeRecord) -> str | None:
        """Extract normalized DOI from OpenAlex record."""
        doi_url: str = record.get("doi", "") or ""
        if not doi_url:
            return None
        if doi_url.startswith("https://doi.org/"):
            extracted: str = doi_url[16:].lower()
            return extracted
        lowered: str = doi_url.lower()
        return lowered

    def _fallback_health_status(self) -> HealthStatus:
        """Fallback health status on probe failure."""
        return HealthStatus.UNHEALTHY

    def _get_health_endpoint(self) -> str:
        """Health endpoint path for OpenAlex probes."""
        return "/works"

    def get_source_metadata(
        self,
        api_version: str | None = None,
    ) -> SourceMetadata:
        """Get API request metadata and clear collector."""
        metadata = self._request_collector.to_source_metadata(
            source_type="api", url=_OPENALEX_BASE_URL, api_version=api_version
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


__all__ = ["OpenAlexAdapterHelpersMixin"]
