"""Extraction helpers for PublicationTermDataSource."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from typing import TYPE_CHECKING, ClassVar, Protocol, cast

from bioetl.application.core.publication_term_runtime import (
    compute_term_entity_id,
    create_term_record,
    extract_terms_from_publication,
)
from bioetl.domain.types import BronzeRecord

if TYPE_CHECKING:
    from bioetl.domain.ports import DataSourcePort, FilterableDataSourcePort


def normalize_publication_term_limit(limit: int | None) -> int | None:
    """Validate and normalize an optional term-record limit.

    Returns:
        ``None`` when unlimited, otherwise a non-negative integer.

    Raises:
        TypeError: If limit is not an int (bool rejected).
        ValueError: If limit is negative.
    """
    if limit is None:
        return None
    if isinstance(limit, bool) or not isinstance(limit, int):
        raise TypeError(f"limit must be int | None, got {type(limit).__name__}")
    if limit < 0:
        raise ValueError("limit must be >= 0")
    return limit


def resolve_publication_upstream_limit(
    limit: int | None,
    *,
    multiplier: int,
) -> tuple[int | None, int | None] | None:
    """Normalize term limit and derive upstream publication budget.

    Returns:
        ``None`` when the call must yield zero records (hard limit 0).
        Otherwise ``(normalized_term_limit, publication_limit)``.
    """
    normalized_limit = normalize_publication_term_limit(limit)
    if normalized_limit == 0:
        return None
    publication_limit = (
        normalized_limit * multiplier if normalized_limit is not None else None
    )
    return normalized_limit, publication_limit


class PublicationTermExtractionHost(Protocol):
    """Structural host required by publication-term extraction mixins.

    Composed adapters (e.g. ``PublicationTermDataSource``) provide these
    attributes; mixin methods use the protocol instead of ``self: Any``.
    """

    SOURCE_ENTITY_TYPE: ClassVar[str]
    PUBLICATION_LIMIT_MULTIPLIER: ClassVar[int]
    _data_source: DataSourcePort

    def _extract_terms_from_publication(
        self,
        record: BronzeRecord,
        publication_id: str,
    ) -> list[BronzeRecord]: ...

    def _yield_terms_from_publications(
        self,
        publications: AsyncIterator[BronzeRecord],
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]: ...


class PublicationTermExtractionMixin:
    """Shared publication->term extraction flow."""

    async def _yield_terms_from_publications(
        self: PublicationTermExtractionHost,
        publications: AsyncIterator[BronzeRecord],
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Expand a publication stream into term records with optional limit."""
        normalized_limit = normalize_publication_term_limit(limit)
        if normalized_limit == 0:
            aclose = getattr(publications, "aclose", None)
            if callable(aclose):
                aclose_fn = cast(Callable[[], Awaitable[object]], aclose)
                await aclose_fn()
            return

        term_count = 0
        try:
            async for publication in publications:
                publication_id = publication.get("publication_id") or publication.get(
                    "document_chembl_id"
                )
                if not publication_id:
                    continue
                terms = self._extract_terms_from_publication(
                    publication, str(publication_id)
                )
                for term in terms:
                    yield term
                    term_count += 1
                    if normalized_limit is not None and term_count >= normalized_limit:
                        return
        finally:
            aclose = getattr(publications, "aclose", None)
            if callable(aclose):
                aclose_fn = cast(Callable[[], Awaitable[object]], aclose)
                await aclose_fn()

    async def _fetch_publication_terms(
        self: PublicationTermExtractionHost,
        limit: int | None,
        filter_ids: list[str] | None,
        filter_field: str | None,
        query: str | None = None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch publications from wrapped source and yield extracted terms."""
        resolved = resolve_publication_upstream_limit(
            limit, multiplier=self.PUBLICATION_LIMIT_MULTIPLIER
        )
        if resolved is None:
            return
        normalized_limit, publication_limit = resolved
        publications = self._data_source.fetch(
            entity_type=self.SOURCE_ENTITY_TYPE,
            limit=publication_limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        )
        async for term in self._yield_terms_from_publications(
            publications, normalized_limit
        ):
            yield term

    def _extract_terms_from_publication(
        self: PublicationTermExtractionHost,
        record: BronzeRecord,
        publication_id: str,
    ) -> list[BronzeRecord]:
        """Extract and flatten all terms from a publication record."""
        return extract_terms_from_publication(record, publication_id)

    def _create_term_record(
        self: PublicationTermExtractionHost,
        publication_id: str,
        term: str,
        term_type: str,
        mesh_id: str | None,
        qualifier: str | None,
    ) -> BronzeRecord:
        """Create a single publication-term record."""
        return create_term_record(
            publication_id=publication_id,
            term=term,
            term_type=term_type,
            mesh_id=mesh_id,
            qualifier=qualifier,
        )

    def _compute_entity_id(
        self: PublicationTermExtractionHost,
        publication_id: str,
        term_type: str,
        term: str,
    ) -> str:
        """Compute deterministic term entity ID."""
        return compute_term_entity_id(
            publication_id=publication_id,
            term_type=term_type,
            term=term,
        )

    async def _fetch_filtered_publication_terms(
        self: PublicationTermExtractionHost,
        filterable: FilterableDataSourcePort,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None,
    ) -> AsyncIterator[BronzeRecord]:
        """Fetch filtered publications and yield extracted terms."""
        resolved = resolve_publication_upstream_limit(
            limit, multiplier=self.PUBLICATION_LIMIT_MULTIPLIER
        )
        if resolved is None:
            return
        normalized_limit, publication_limit = resolved
        publications = filterable.fetch_filtered(
            entity_type=self.SOURCE_ENTITY_TYPE,
            filter_ids=filter_ids,
            filter_field=filter_field,
            limit=publication_limit,
        )
        async for term in self._yield_terms_from_publications(
            publications, normalized_limit
        ):
            yield term
