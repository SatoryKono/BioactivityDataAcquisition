"""Fallback search utilities for Semantic Scholar DOI resolution.

Provides title-based search fallback when DOI resolution fails.
Supports three-phase fallback strategy:
- Phase 2: Title fallback for unresolved DOIs
- Phase 3: Title-only lookup for entries without DOIs

Uses unified HTTP client for API requests with proper metrics tracking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast, override

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.common import BaseTitleFallbackHandler, titles_match
from bioetl.infrastructure.adapters.common.error_bundles import (
    COMMON_TITLE_FALLBACK_ERRORS,
)
from bioetl.infrastructure.adapters.semanticscholar.constants import (
    SEMANTICSCHOLAR_BASE_URL,
)
from bioetl.infrastructure.adapters.semanticscholar.request_headers import (
    build_semanticscholar_headers,
)

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

# Re-export for backwards compatibility
__all__ = [
    "SemanticScholarTitleFallbackHandler",
    "TitleFallbackHandler",
    "titles_match",
]

# Semantic Scholar API configuration
DEFAULT_SEARCH_FIELDS = (
    "paperId,externalIds,title,abstract,year,publicationDate,"
    "venue,authors,citationCount,referenceCount,isOpenAccess,"
    "openAccessPdf,tldr,fieldsOfStudy,publicationTypes,journal"
)

SEMANTICSCHOLAR_FALLBACK_ERRORS = COMMON_TITLE_FALLBACK_ERRORS


class SemanticScholarTitleFallbackHandler(BaseTitleFallbackHandler):
    """Title fallback handler for Semantic Scholar API.

    Handles fallback search by title when DOI lookup fails.
    Uses direct HTTP client injection for API requests.

    Attributes:
        _http_client: UnifiedHTTPClient for making HTTP requests.
        _metrics: Optional AdapterMetricsRecorder for recording request metrics.
        _api_key: Optional API key for stable rate limits.
        _fields: Comma-separated list of fields to retrieve.
    """

    def __init__(
        self,
        http_client: UnifiedHTTPClient,
        logger: LoggerPort,
        metrics: AdapterMetricsRecorder | None = None,
        api_key: str = "",
        fields: str = DEFAULT_SEARCH_FIELDS,
    ) -> None:
        """Initialize fallback handler.

        Args:
            http_client: UnifiedHTTPClient instance for API requests.
            logger: Logger port for structured logging.
            metrics: Optional AdapterMetricsRecorder for tracking request metrics.
            api_key: Optional API key for stable rate limits.
            fields: Comma-separated list of fields to retrieve.
        """
        super().__init__(logger)
        self._http_client = http_client
        self._metrics = metrics
        self._api_key = api_key
        self._fields = fields

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with API key if available.

        Returns:
            Dictionary of HTTP headers including optional x-api-key if configured.
        """
        return build_semanticscholar_headers(
            self._api_key,
            include_content_type=False,
            skip_placeholder_api_key=True,
        )

    @property
    @override
    def _event_no_fallback_title(self) -> str:
        """Return log event name for missing fallback title."""
        return "semanticscholar_no_fallback_title"

    @property
    @override
    def _event_fallback_attempt(self) -> str:
        """Return log event name for fallback attempt."""
        return "title_fallback_search"

    @property
    @override
    def _event_fallback_success(self) -> str:
        """Return log event name for successful fallback."""
        return "title_fallback_found"

    @property
    @override
    def _event_fallback_not_found(self) -> str:
        """Return log event name for failed fallback."""
        return "title_fallback_not_found"

    @property
    @override
    def _event_title_only_attempt(self) -> str:
        """Return log event name for title-only lookup attempt."""
        return "title_only_search"

    @property
    @override
    def _event_title_only_success(self) -> str:
        """Return log event name for successful title-only lookup."""
        return "semanticscholar_title_only_success"

    @property
    @override
    def _event_title_only_not_found(self) -> str:
        """Return log event name for failed title-only lookup."""
        return "semanticscholar_title_only_not_found"

    async def _search_by_title(
        self, title: str
    ) -> JsonDict | None:  # Any: untyped API JSON record
        """Search Semantic Scholar by title and return best matching record.

        Args:
            title: Publication title to search for.

        Returns:
            Matching publication record dict if a title match is found, None otherwise.
        """
        try:
            cleaned_title = self._escape_title_for_search(title)

            params: JsonDict = {  # Any: untyped API JSON record
                "query": cleaned_title,
                "fields": self._fields,
                "limit": 5,  # Return top matches for validation
            }

            self._logger.debug(
                "semanticscholar_title_search",
                title=title[:100],
            )

            url = f"{SEMANTICSCHOLAR_BASE_URL}/paper/search"

            if self._metrics:
                with self._metrics.measure_request("/paper/search"):
                    response = await self._http_client.get_once(
                        url, params=params, headers=self._build_headers()
                    )
            else:
                response = await self._http_client.get_once(
                    url, params=params, headers=self._build_headers()
                )

            data = response.json()

            for record in data.get("data", []):
                # Validate title match to reduce false positives
                found_title = record.get("title", "")
                if found_title and titles_match(title, found_title):
                    return cast(JsonDict, record)  # Any: untyped API JSON record
                # If no title in record, return first result
                if not found_title:
                    return cast(JsonDict, record)  # Any: untyped API JSON record

        except SEMANTICSCHOLAR_FALLBACK_ERRORS as e:
            self._logger.debug(
                "semanticscholar_title_search_failed",
                title=title[:50],
                error=str(e),
            )
        return None

    def titles_match(self, expected: str, actual: str) -> bool:
        """Check if titles match (case-insensitive substring).

        Args:
            expected: Expected title from the original query.
            actual: Actual title from the search result.

        Returns:
            True if titles match, False otherwise.
        """
        return titles_match(expected, actual)

    @staticmethod
    def _escape_title_for_search(title: str) -> str:
        """Escape title for Semantic Scholar search query.

        Args:
            title: Publication title to clean.

        Returns:
            Cleaned title suitable for search query.
        """
        # Remove special characters that might break the query
        cleaned = title.replace('"', " ").replace("'", " ")
        # Normalize whitespace
        return " ".join(cleaned.split())

    @override
    def _get_result_identifier(
        self,
        result: JsonDict,  # Any: untyped API JSON record
    ) -> tuple[str, str]:  # Any: untyped API JSON record
        """Return Semantic Scholar paper ID for logging.

        Args:
            result: BronzeRecord or raw API dict from the search response.

        Returns:
            Tuple of (identifier key name, paper ID string) for structured log output.
        """
        return ("found_paper_id", str(result.get("paperId", "unknown")))


# Backwards compatibility alias
TitleFallbackHandler = SemanticScholarTitleFallbackHandler
