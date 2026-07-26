"""Internal DOI batch workflow for the CrossRef adapter."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from httpx import Response

from bioetl.domain.normalization import normalize_doi
from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.crossref._batch_support import (
    CROSSREF_FALLBACK_ERRORS,
    CROSSREF_RUNTIME_ERRORS,
    BaseMetrics,
    HeadersProvider,
    HttpTransport,
    perform_timed_crossref_get,
)
from bioetl.infrastructure.adapters.crossref.exceptions import CrossRefApiError

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )


class DoiBatchProcessor:
    """Handles batch DOI resolution for CrossRef API."""

    def __init__(
        self,
        http: HttpTransport,
        logger: LoggerPort,
        metrics: BaseMetrics,
        mailto: str,
        api_base: str,
        headers_fn: HeadersProvider,
        request_collector: APIRequestCollector | None = None,
    ) -> None:
        self._http = http
        self._logger = logger
        self._metrics = metrics
        self._mailto = mailto
        self._api_base = api_base
        self._headers_fn = headers_fn
        self._request_collector = request_collector

    async def fetch_single(self, doi: str) -> BronzeRecord | None:
        """Fetch a single publication by DOI."""
        normalized_doi = normalize_doi(doi) or ""
        url = f"{self._api_base}/works/{normalized_doi}"
        response: Response | None = None

        try:
            response = await perform_timed_crossref_get(
                http=self._http,
                metrics=self._metrics,
                route="/works/{doi}",
                url=url,
                headers=self._headers_fn(),
                request_collector=self._request_collector,
            )

            if response is None:
                raise CrossRefApiError(
                    f"Failed to fetch DOI {normalized_doi}: no response"
                )

            if response.status_code == 404:
                self._logger.debug("crossref_doi_not_found", doi=normalized_doi)
                return None

            if response.status_code != 200:
                raise CrossRefApiError(
                    f"CrossRef API error for DOI {normalized_doi}",
                    status_code=response.status_code,
                )

            data = response.json()
            return cast(BronzeRecord, data.get("message", {}))

        except CrossRefApiError:
            raise
        except CROSSREF_RUNTIME_ERRORS as error:
            self._logger.error(
                "crossref_fetch_failed",
                doi=normalized_doi,
                error=str(error),
            )
            raise CrossRefApiError(
                f"Failed to fetch DOI {normalized_doi}: {error}"
            ) from error

    async def _fallback_individual_fetch(
        self, dois: list[str]
    ) -> AsyncIterator[BronzeRecord]:
        """Fall back to individual DOI fetches."""
        for doi in dois:
            try:
                publication = await self.fetch_single(doi)
                if publication:
                    yield publication
            except CROSSREF_FALLBACK_ERRORS as error:
                self._logger.debug(
                    "crossref_individual_fetch_failed",
                    doi=doi,
                    error=str(error),
                )

    def _normalize_dois(self, dois: list[str]) -> list[str]:
        """Normalize and filter DOI list, removing invalid entries."""
        normalized: list[str] = []
        for doi in dois:
            value = normalize_doi(doi)
            if value:
                normalized.append(value)
        return normalized

    async def _execute_batch_request(
        self, normalized_dois: list[str]
    ) -> Response | None:
        """Execute the batch DOI filter request."""
        filter_value = ",".join(f"doi:{doi}" for doi in normalized_dois)
        url = f"{self._api_base}/works"
        params = {
            "filter": filter_value,
            "rows": str(len(normalized_dois)),
            "mailto": self._mailto,
        }
        return await perform_timed_crossref_get(
            http=self._http,
            metrics=self._metrics,
            route="/works?filter=doi",
            url=url,
            params=params,
            headers=self._headers_fn(),
            request_collector=self._request_collector,
        )

    def _batch_items_from_response(self, response: Response) -> list[BronzeRecord]:
        """Extract Bronze records from a successful CrossRef batch response."""
        data = response.json()
        message = data.get("message", {})
        items = message.get("items", []) if isinstance(message, dict) else []
        return [cast(BronzeRecord, item) for item in items if isinstance(item, dict)]

    async def _yield_batch_or_fallback(
        self,
        *,
        response: Response | None,
        original_dois: list[str],
    ) -> AsyncIterator[BronzeRecord]:
        """Yield batch items or fall back to individual DOI fetches."""
        if response is None:
            raise CrossRefApiError("CrossRef batch request returned no response")
        status_code = getattr(response, "status_code", None)
        if status_code != 200:
            self._logger.warning(
                "crossref_batch_fetch_failed",
                status_code=status_code,
                doi_count=len(original_dois),
            )
            async for publication in self._fallback_individual_fetch(original_dois):
                yield publication
            return
        for item in self._batch_items_from_response(response):
            yield item

    async def fetch_batch(self, dois: list[str]) -> AsyncIterator[BronzeRecord]:
        """Fetch multiple publications by DOI batch."""
        if not dois:
            return

        normalized_dois = self._normalize_dois(dois)
        if not normalized_dois:
            return

        try:
            response = await self._execute_batch_request(normalized_dois)
            async for publication in self._yield_batch_or_fallback(
                response=response,
                original_dois=dois,
            ):
                yield publication
        except CROSSREF_RUNTIME_ERRORS as error:
            self._logger.warning(
                "crossref_batch_fetch_error",
                error=str(error),
                doi_count=len(dois),
            )
            async for publication in self._fallback_individual_fetch(dois):
                yield publication
