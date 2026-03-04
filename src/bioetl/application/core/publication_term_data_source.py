"""Publication term data-source wrapper.

Transforms publication records from wrapped adapter into publication_term records.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Self

__all__ = ["PublicationTermDataSource"]

from bioetl.application.core._data_source_mixins import _SourceMetadataDelegationMixin
from bioetl.application.core.publication_term_extraction_mixin import (
    PublicationTermExtractionMixin,
)
from bioetl.application.core.publication_term_filtering_mixin import (
    PublicationTermFilteringMixin,
)
from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import DataSourcePort
    from bioetl.domain.types import HealthStatus


class PublicationTermDataSource(
    PublicationTermFilteringMixin,
    PublicationTermExtractionMixin,
    _SourceMetadataDelegationMixin,
):
    """Decorator that exposes publication_term by extracting terms from publications."""

    SOURCE_ENTITY_TYPE = "publication"
    TARGET_ENTITY_TYPE = "publication_term"
    PUBLICATION_LIMIT_MULTIPLIER = 50

    def __init__(self, data_source: DataSourcePort) -> None:
        """Initialize wrapper around a publication-capable source adapter."""
        self._data_source = data_source

    @property
    def provider_name(self) -> str:
        """Provider name from wrapped source."""
        return self._data_source.provider_name

    async def __aenter__(self) -> Self:
        """Enter async context."""
        await self._data_source.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,  # Any: context-manager protocol accepts implementation-defined traceback type
    ) -> None:
        """Exit async context."""
        await self._data_source.__aexit__(exc_type, exc_val, exc_tb)

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch records; publication_term is derived from wrapped publication fetch."""
        if entity_type == self.TARGET_ENTITY_TYPE:
            async for term in self._fetch_publication_terms(
                limit, filter_ids, filter_field
            ):
                yield term
            return

        async for record in self._data_source.fetch(
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
            offset=offset,
        ):
            yield record

    async def health_check(self) -> HealthStatus:
        """Delegate health check to wrapped source."""
        return await self._data_source.health_check()

    async def aclose(self) -> None:
        """Delegate close to wrapped source."""
        await self._data_source.aclose()
