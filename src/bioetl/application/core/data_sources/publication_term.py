"""Publication term data-source wrapper.

Transforms publication records from wrapped adapter into publication_term records.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

__all__ = ["PublicationTermDataSource"]

from bioetl.application.core.data_source_mixins import (
    _SourceMetadataDelegationMixin,
    _WrappedDataSourceDelegationMixin,
)
from bioetl.application.core.publication_term_extraction_mixin import (
    PublicationTermExtractionMixin,
)
from bioetl.application.core.publication_term_filtering_mixin import (
    PublicationTermFilteringMixin,
)
from bioetl.application.core.target_data_source_mixins import (
    _TargetEntityFetchDelegationMixin,
)
from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import DataSourcePort


class PublicationTermDataSource(
    PublicationTermFilteringMixin,
    PublicationTermExtractionMixin,
    _TargetEntityFetchDelegationMixin,
    _WrappedDataSourceDelegationMixin,
    _SourceMetadataDelegationMixin,
):
    """Decorator that exposes publication_term by extracting terms from publications."""

    SOURCE_ENTITY_TYPE = "publication"
    TARGET_ENTITY_TYPE = "publication_term"
    PUBLICATION_LIMIT_MULTIPLIER = 50

    def __init__(self, data_source: DataSourcePort) -> None:
        self._data_source = data_source

    async def _fetch_target_records(
        self,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        _ = query, offset
        async for term in self._fetch_publication_terms(
            limit, filter_ids, filter_field
        ):
            yield term
