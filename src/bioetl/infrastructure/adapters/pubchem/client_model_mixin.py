# pyright: reportUninitializedInstanceVariable=false
# pyright: reportAttributeAccessIssue=false
# Host attrs/methods are initialized by concrete classes (PD2 W1 host surface).
"""Model and metadata helpers for `PubChemAdapter`."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from bioetl.infrastructure.adapters.common.source_metadata_capability import (
    clear_source_metadata_collector,
    consume_source_metadata,
    get_request_count,
)
from bioetl.infrastructure.adapters.pubchem.client_builders import PUBCHEM_DTO_MODELS
from bioetl.infrastructure.adapters.pubchem.constants import PUBCHEM_API_BASE

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.models.metadata import SourceMetadata
    from bioetl.domain.types import JsonDict
    from bioetl.infrastructure.adapters.common.api_request_collector import (
        APIRequestCollector,
    )
    from bioetl.infrastructure.adapters.http.rate_limiter import TokenBucketRateLimiter


class PubChemAdapterModelMixin:
    """Adds DTO conversion and request metadata methods to `PubChemAdapter`."""

    _request_collector: APIRequestCollector
    rate_limiter: TokenBucketRateLimiter

    def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        """Fetch raw PubChem records.

        Args:
            entity_type: Entity type to fetch (e.g., "compound").
            limit: Optional maximum number of records to yield.
            query: Optional search query string.
            filter_ids: Optional list of IDs to filter by.
            filter_field: Optional field name to filter on.
            offset: Optional record offset (unused in PubChem).

        Raises:
            NotImplementedError: This is an abstract placeholder; implemented by PubChemAdapter.
        """
        raise NotImplementedError

    async def fetch_as_models(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        *,
        validate: bool = True,
    ) -> AsyncIterator[BaseModel]:
        """Fetch records from PubChem as typed DTO models.

        Args:
            entity_type: Entity type to fetch; must map to a supported DTO model (e.g., "compound").
            limit: Optional maximum number of records to yield.
            query: Optional search query string passed to fetch.
            filter_ids: Optional list of IDs to filter by.
            filter_field: Optional field name to filter on.
            validate: Whether to use model_validate (True) or model_construct (False).

        Yields:
            Typed Pydantic model instances for each fetched record.

        Raises:
            ValueError: If entity_type has no registered DTO model.
        """
        model_class = PUBCHEM_DTO_MODELS.get(entity_type)
        if model_class is None:
            raise ValueError(
                f"No DTO model for entity_type '{entity_type}'. "
                f"Supported: {', '.join(PUBCHEM_DTO_MODELS.keys())}"
            )

        async for record in self.fetch(
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        ):
            if "cid" in record and record["cid"] is not None:
                record["cid"] = str(record["cid"])

            if validate:
                yield model_class.model_validate(record)
            else:
                yield model_class.model_construct(**record)

    def get_source_metadata(self, api_version: str | None = None) -> SourceMetadata:
        """Get accumulated API request metadata for Bronze layer enrichment.

        Args:
            api_version: Optional API version string to embed in the metadata.

        Returns:
            SourceMetadata aggregated from recorded API requests since last clear.
        """
        return consume_source_metadata(
            collector=self._request_collector,
            url=PUBCHEM_API_BASE,
            api_version=api_version,
        )

    def clear_request_collector(self) -> None:
        """Clear the API request collector without generating metadata."""
        clear_source_metadata_collector(collector=self._request_collector)

    @property
    def request_count(self) -> int:
        """Get the number of recorded API requests since last clear."""
        return get_request_count(collector=self._request_collector)

    def __repr__(self) -> str:
        """Return string representation."""
        return f"PubChemAdapter(rate={self.rate_limiter.rate})"


__all__ = ["PubChemAdapterModelMixin"]
