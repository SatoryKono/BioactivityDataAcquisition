# mypy: disable-error-code=attr-defined
"""Batch request internals for SemanticScholarAdapter."""

from __future__ import annotations

import contextlib
import time
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.semanticscholar.constants import (
    SEMANTICSCHOLAR_BASE_URL,
)

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class SemanticScholarBatchRequestMixin:
    """Raw batch request and DOI normalization helpers."""

    async def _fetch_by_dois(
        self,
        dois: list[str],
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch batch DOIs and filter out null/not-found entries."""
        if not dois:
            return
        results = await self._fetch_batch_with_nulls(dois)
        for record in results:
            if record is not None:
                yield record

    async def _fetch_batch_with_nulls(
        self,
        dois: list[str],
    ) -> list[BronzeRecord | None]:
        """Fetch batch preserving null slots for not-found IDs.

        Returns:
            List of BronzeRecord or None values preserving position of not-found DOIs.
        """
        if not dois:
            return []

        formatted_ids = [f"DOI:{self._normalize_doi(doi)}" for doi in dois if doi]
        return await self._fetch_batch_raw(formatted_ids)

    async def _fetch_batch_raw(
        self,
        paper_ids: list[str],
    ) -> list[BronzeRecord | None]:
        """Execute raw batch request and return response array.

        Returns:
            List of BronzeRecord or None values from the batch API response array.
        """
        self.logger.debug(
            "semanticscholar_batch_request",
            paper_count=len(paper_ids),
        )
        url = f"{SEMANTICSCHOLAR_BASE_URL}/paper/batch?fields={self.fields}"
        json_body = {"ids": paper_ids}

        start_time = time.perf_counter()
        with self._adapter_metrics.measure_request("/paper/batch"):
            response = await self.http_client.post(
                url,
                json=json_body,
                headers=self._build_headers(),
            )
        duration_ms = (time.perf_counter() - start_time) * 1000
        with contextlib.suppress(Exception):
            self._request_collector.record_from_response(response, duration_ms)

        result: list[BronzeRecord | None] = response.json()
        return result

    @staticmethod
    def _normalize_doi(doi: str) -> str:
        """Normalize DOI by removing URL-style prefixes.

        Returns:
            DOI string with URL prefix (https://doi.org/, doi:, DOI:) removed.
        """
        if doi.startswith("https://doi.org/"):
            return doi[16:]
        if doi.startswith("http://doi.org/"):
            return doi[15:]
        if doi.startswith("doi:"):
            return doi[4:]
        if doi.startswith("DOI:"):
            return doi[4:]
        return doi
