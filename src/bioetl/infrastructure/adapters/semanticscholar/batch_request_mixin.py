# mypy: disable-error-code=attr-defined
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Batch request internals for SemanticScholarAdapter."""

from __future__ import annotations

import contextlib
import time
from typing import TYPE_CHECKING, Any, Protocol

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
from bioetl.typing_support import as_mixin_host

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
        results = await as_mixin_host(self)._fetch_batch_with_nulls(dois)  # Any: mixin host surface (self attrs/methods)
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

        formatted_ids = [f"DOI:{as_mixin_host(self)._normalize_doi(doi)}" for doi in dois if doi]  # Any: mixin host surface (self attrs/methods)
        return await as_mixin_host(self)._fetch_batch_raw(formatted_ids)  # Any: mixin host surface (self attrs/methods)

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
        as_mixin_host(self)._logger.debug(  # Any: mixin host surface (self attrs/methods)
            "semanticscholar_batch_request",
            paper_count=len(paper_ids),
        )
        url = f"{SEMANTICSCHOLAR_BASE_URL}/paper/batch?fields={as_mixin_host(self).fields}"  # Any: mixin host surface (self attrs/methods)
        json_body = {"ids": paper_ids}

        start_time = time.perf_counter()
        with as_mixin_host(self)._adapter_metrics.measure_request("/paper/batch"):  # Any: mixin host surface (self attrs/methods)
            response = await as_mixin_host(self)._http_client.post(  # Any: mixin host surface (self attrs/methods)
                url,
                json=json_body,
                headers=as_mixin_host(self)._build_headers(),  # Any: mixin host surface (self attrs/methods)
            )
        duration_ms = (time.perf_counter() - start_time) * 1000
        with contextlib.suppress(Exception):
            as_mixin_host(self)._request_collector.record_from_response(response, duration_ms)  # Any: mixin host surface (self attrs/methods)

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
