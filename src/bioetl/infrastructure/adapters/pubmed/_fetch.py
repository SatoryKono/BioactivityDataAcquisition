"""Fetch functionality for PubMed adapter.

Part of PubMedAdapter split to comply with LOC limits.
"""

from __future__ import annotations

from bioetl.domain.types import JsonDict

__all__ = ["PUBMED_FETCH_ERRORS", "PubMedFetchMixin"]

import contextlib
import time
from typing import TYPE_CHECKING

from bioetl.infrastructure.adapters.pubmed._errors import (
    PUBMED_RECORD_ERRORS as PUBMED_FETCH_ERRORS,
)
from bioetl.infrastructure.adapters.pubmed.xml_processor import PubMedXmlProcessor

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import ErrorHandlerPort, LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.base_metrics import AdapterMetricsRecorder
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient

from .constants import ENTREZ_API_BASE


class PubMedFetchMixin:
    """Mixin providing record fetching capabilities for PubMed."""

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    email: str
    api_key: str | None
    _http_client: UnifiedHTTPClient
    _logger: LoggerPort
    _adapter_metrics: AdapterMetricsRecorder
    _request_collector: APIRequestCollector
    _error_handler: ErrorHandlerPort
    provider_name: str
    batch_size: int
    metrics: MetricsPort | None

    def _build_fetch_params(self, id_batch: list[str]) -> dict[str, str]:
        """Build parameters for efetch API call.

        Args:
            id_batch: List of PubMed IDs (PMIDs) to fetch in a single request.

        Returns:
            Dictionary of query parameters for the efetch API request.
        """
        params = {
            "db": "pubmed",
            "id": ",".join(id_batch),
            "retmode": "xml",
            "rettype": "abstract",
            "email": self.email,
        }
        if self.api_key and "your_" not in self.api_key:
            params["api_key"] = self.api_key
        return params

    async def _fetch_batch(
        self, id_batch: list[str]
    ) -> list[JsonDict]:  # Any: untyped API JSON record
        """Fetch a batch of articles and return parsed records.

        Returns:
            List of parsed article record dictionaries from the efetch response.
        """
        params = self._build_fetch_params(id_batch)
        try:
            start_time = time.perf_counter()
            with self._adapter_metrics.measure_request("/efetch"):
                response = await self._http_client.get(
                    f"{ENTREZ_API_BASE}efetch.fcgi", params=params
                )
            duration_ms = (time.perf_counter() - start_time) * 1000

            with contextlib.suppress(Exception):
                self._request_collector.record_from_response(response, duration_ms)

            root = PubMedXmlProcessor.parse_response(response.text)
            if root is None:
                self._logger.error(
                    "external_api_error",
                    provider=self.provider_name,
                    operation="batch_fetch",
                    error_category="DATA_QUALITY",
                    error="XML parse error",
                    batch_size=len(id_batch),
                )
                return []
            return PubMedXmlProcessor.extract_all_records(root)
        except PUBMED_FETCH_ERRORS as e:
            wrapped = self._error_handler.handle_error(
                error=e,
                provider=self.provider_name,
                operation="batch_fetch",
                context={"batch_size": len(id_batch)},
            )
            raise wrapped from e

    async def _yield_articles_from_pmids(
        self, pmids: list[str], limit: int | None
    ) -> AsyncIterator[JsonDict]:  # Any: untyped API JSON record
        """Yield article records from a list of PMIDs."""
        total_fetched = 0
        for i in range(0, len(pmids), self.batch_size):
            records = await self._fetch_batch(pmids[i : i + self.batch_size])
            for record in records:
                yield record
                total_fetched += 1
                if limit and total_fetched >= limit:
                    return
