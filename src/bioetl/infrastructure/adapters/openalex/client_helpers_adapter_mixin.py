"""Adapter helper mixin for OpenAlex adapter utility and metadata methods."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord, HealthStatus
from bioetl.infrastructure.adapters.base import (
    build_json_accept_headers,
    build_mailto_user_agent_headers,
)
from bioetl.infrastructure.adapters.common.api_request_collector import (
    APIRequestCollector,
)
from bioetl.infrastructure.adapters.common.doi_helpers import (
    strip_doi_transport_prefix,
)
from bioetl.infrastructure.adapters.common.source_metadata_capability import (
    clear_source_metadata_collector,
    consume_source_metadata,
    get_request_count,
)
from bioetl.infrastructure.adapters.openalex.query_builder import (
    build_openalex_base_params,
)

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import SourceMetadata

from bioetl.infrastructure.adapters.openalex._constants import OPENALEX_API_BASE


class OpenAlexAdapterHelpersMixin:
    """Utility helpers extracted from the main OpenAlex adapter."""

    # Host-class attributes (provided by OpenAlexAdapter.__post_init__)
    mailto: str | None
    api_key: str | None
    _request_collector: APIRequestCollector

    def _build_headers(self) -> dict[str, str]:
        """Build request headers for OpenAlex API.

        Returns:
            Dictionary of HTTP headers with User-Agent and Accept fields.
        """
        if self.mailto:
            return build_mailto_user_agent_headers(self.mailto)
        return build_json_accept_headers("BioETL/1.0")

    def _build_base_params(self) -> dict[str, str]:
        """Build base query parameters with mailto for polite pool.

        Returns:
            Dictionary containing the mailto parameter for polite pool access.
        """
        return build_openalex_base_params(self.mailto, api_key=self.api_key)

    @staticmethod
    def _normalize_doi(doi: str) -> str | None:
        """Normalize DOI by removing URL prefix.

        Args:
            doi: Raw DOI string potentially including URL-style prefix.

        Returns:
            Normalized DOI string without URL prefix, or None if input is empty.
        """
        if not doi:
            return None
        normalized = strip_doi_transport_prefix(doi.strip())
        return normalized or None

    @staticmethod
    def _escape_title_for_search(title: str) -> str:
        """Escape title for OpenAlex title.search filter.

        Args:
            title: Publication title to clean and escape for API search.

        Returns:
            Plus-separated token string with special characters removed for API compatibility.
        """
        cleaned = title.replace(":", " ").replace("|", " ").replace(",", " ")
        return "+".join(cleaned.split())

    @staticmethod
    def _extract_doi_from_record(record: BronzeRecord) -> str | None:
        """Extract normalized DOI from OpenAlex record.

        Args:
            record: BronzeRecord from the OpenAlex API response.

        Returns:
            Lowercased DOI string without URL prefix, or None if absent.
        """
        doi_url: str = record.get("doi", "") or ""
        if not doi_url:
            return None
        if doi_url.startswith("https://doi.org/"):
            extracted: str = doi_url[16:].lower()
            return extracted
        lowered: str = doi_url.lower()
        return lowered

    def _fallback_health_status(self) -> HealthStatus:
        """Fallback health status on probe failure.

        Returns:
            HealthStatus.UNHEALTHY as the safe default when health probe cannot execute.
        """
        return HealthStatus.UNHEALTHY

    def _get_health_endpoint(self) -> str:
        """Health endpoint path for OpenAlex probes.

        Returns:
            Endpoint path string used for health probe requests.
        """
        return "/works"

    def get_source_metadata(
        self,
        api_version: str | None = None,
    ) -> SourceMetadata:
        """Get API request metadata and clear collector.

        Args:
            api_version: Optional API version string to embed in the metadata.

        Returns:
            SourceMetadata aggregated from all recorded API requests since last clear.
        """
        return consume_source_metadata(
            collector=self._request_collector,
            url=OPENALEX_API_BASE,
            api_version=api_version,
        )

    def clear_request_collector(self) -> None:
        """Clear the collector without returning metadata."""
        clear_source_metadata_collector(collector=self._request_collector)

    @property
    def request_count(self) -> int:
        """Number of recorded API requests since last clear."""
        return get_request_count(collector=self._request_collector)


__all__ = ["OpenAlexAdapterHelpersMixin"]
