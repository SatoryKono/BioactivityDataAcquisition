# mypy: disable-error-code=attr-defined
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportAttributeAccessIssue=false
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Batch request internals for SemanticScholarAdapter."""

from __future__ import annotations

import contextlib
import time
from typing import TYPE_CHECKING

from bioetl.domain.types import BronzeRecord
from bioetl.infrastructure.adapters.common.doi_helpers import (
    strip_doi_transport_prefix,
)
from bioetl.infrastructure.adapters.common.response_shapes import (
    normalize_response_items,
)
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
        """Fetch batch DOIs and filter out null/not-found entries.

        Args:
            dois: List of DOI strings to resolve via batch API.

        Yields:
            Non-null BronzeRecord entries from the batch API response.
        """
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

        Args:
            dois: List of DOI strings to resolve via batch API.

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

        Args:
            paper_ids: List of formatted paper ID strings (e.g., "DOI:10.1234/...") for the batch request.

        Returns:
            List of BronzeRecord or None values from the batch API response array.
        """
        self._logger.debug(
            "semanticscholar_batch_request",
            paper_count=len(paper_ids),
        )
        url = f"{SEMANTICSCHOLAR_BASE_URL}/paper/batch?fields={self.fields}"
        json_body = {"ids": paper_ids}

        start_time = time.perf_counter()
        with self._adapter_metrics.measure_request("/paper/batch"):
            response = await self._http_client.post(
                url,
                json=json_body,
                headers=self._build_headers(),
            )
        duration_ms = (time.perf_counter() - start_time) * 1000
        with contextlib.suppress(Exception):
            self._request_collector.record_from_response(response, duration_ms)

        return [
            record if isinstance(record, dict) else None
            for record in normalize_response_items(response.json())
        ]

    @staticmethod
    def _normalize_doi(doi: str) -> str:
        """Normalize DOI by removing URL-style prefixes.

        Args:
            doi: Raw DOI string potentially including URL-style prefix.

        Returns:
            DOI string with URL prefix (https://doi.org/, doi:, DOI:) removed.
        """
        return strip_doi_transport_prefix(doi, allow_uppercase_prefix=True)
