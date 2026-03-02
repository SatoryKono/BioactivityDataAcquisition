# src/bioetl/infrastructure/adapters/pubmed/pubmed_client.py
"""PubMed adapter for Entrez E-utilities API.

Implements DataSourcePort for PubMed article metadata extraction.
Split into mixins to comply with LOC limits.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from bioetl.domain.entities.pubmed import ArticleRecord
from bioetl.infrastructure.adapters.base import BaseHttpAdapter
from bioetl.infrastructure.adapters.error_handling import ErrorService
from bioetl.infrastructure.adapters.filterable_mixin import NotSupportedMultiFilterMixin
from bioetl.infrastructure.adapters.pubmed._fetch import PubMedFetchMixin
from bioetl.infrastructure.adapters.pubmed._health import PubMedHealthMixin
from bioetl.infrastructure.adapters.pubmed._search import PubMedSearchMixin
from bioetl.infrastructure.adapters.pubmed.constants import (
    ENTREZ_API_BASE as PUBMED_ENTREZ_API_BASE,
)
from bioetl.infrastructure.adapters.pubmed.fallback import TitleFallbackHandler

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import LoggerPort, MetricsPort
    from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
    from bioetl.infrastructure.config import Settings

# Mapping from entity_type to DTO model class
PUBMED_DTO_MODELS: dict[str, type[BaseModel]] = {
    "publication": ArticleRecord,
}

# Re-export for tests/importers expecting this symbol on the client module.
ENTREZ_API_BASE = PUBMED_ENTREZ_API_BASE


@dataclass
class PubMedAdapter(
    NotSupportedMultiFilterMixin,
    PubMedSearchMixin,
    PubMedFetchMixin,
    PubMedHealthMixin,
    BaseHttpAdapter,
):
    """PubMed adapter using UnifiedHTTPClient.

    Implements DataSourcePort and FilterableDataSourcePort.
    Functionality split across mixins:
    - PubMedSearchMixin: esearch and title search
    - PubMedFetchMixin: efetch and record yielding
    - PubMedHealthMixin: health probes and metadata
    """

    http_client: UnifiedHTTPClient
    logger: LoggerPort
    email: str
    api_key: str | None = None
    batch_size: int = 200
    metrics: MetricsPort | None = None

    provider_name: str = field(init=False, default="pubmed")

    _fallback_handler: TitleFallbackHandler | None = field(
        default=None, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Initialize metrics, error handler and fallback handler."""
        self._error_handler = ErrorService(self.logger)
        self._init_adapter_metrics()

        self._fallback_handler = TitleFallbackHandler(
            logger=self.logger,
            search_fn=self._search_by_title,
        )

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch PubMed records by ID list (bypass search).

        Args:
            entity_type: Entity type identifier.
            filter_ids: List of identifiers to filter by.
            filter_field: Field name to apply filter on.
            limit: Maximum number of records to process.

        Returns:
            Async iterator yielding fetched records.
        """
        if entity_type != "publication":
            raise ValueError("PubMedAdapter only supports 'publication'")

        if filter_field != "pmid":
            self.logger.warning(
                "unsupported_filter_field", field=filter_field, msg="Assuming PMIDs"
            )

        async for record in self._yield_articles_from_pmids(filter_ids, limit):
            record["_lookup_method"] = "pmid"
            yield record

    async def fetch_filtered_with_fallback(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        fallback_mapping: dict[str, str],
        limit: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch with fallback to title search when primary lookup fails.

        Args:
            entity_type: Entity type identifier.
            filter_ids: List of identifiers to filter by.
            filter_field: Field name to apply filter on.
            fallback_mapping: Fallback mapping.
            limit: Maximum number of records to process.

        Returns:
            Async iterator yielding fetched records.
        """
        if entity_type != "publication":
            raise ValueError("PubMedAdapter only supports 'publication'")

        valid_ids = [id_ for id_ in filter_ids if id_.strip()]
        title_only_entries = [id_ for id_ in filter_ids if not id_.strip()]

        fetched = 0
        found_ids: set[str] = set()

        if valid_ids:
            async for record in self.fetch_filtered(
                entity_type=entity_type,
                filter_ids=valid_ids,
                filter_field=filter_field,
                limit=limit,
            ):
                record["_lookup_method"] = "pmid"
                found_id = str(record.get("pmid", ""))
                if found_id:
                    found_ids.add(found_id.lower())
                fetched += 1
                yield record
                if limit and fetched >= limit:
                    return

        if self._fallback_handler:
            async for record in self._fallback_handler.process_missing_dois(
                dois=valid_ids,
                found_dois=found_ids,
                fallback_mapping=fallback_mapping,
                normalize_fn=lambda x: x.lower().strip(),
                limit=limit,
                fetched=fetched,
            ):
                fetched += 1
                yield record
                if limit and fetched >= limit:
                    return

            async for record in self._fallback_handler.process_title_only_entries(
                entries=title_only_entries,
                fallback_mapping=fallback_mapping,
                limit=limit,
                fetched=fetched,
            ):
                yield record

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch PubMed records.

        Supports checkpoint resume via ``offset`` by skipping the already
        processed PMID segment before article fetch, which avoids refetching
        records from completed part of the previous run.

        Args:
            entity_type: Entity type identifier.
            limit: Maximum number of records to process.
            query: Search query string.
            filter_ids: List of identifiers to filter by.
            filter_field: Field name to apply filter on.
            offset: Offset.

        Returns:
            Async iterator yielding fetched records.
        """
        if filter_ids:
            effective_filter_field = filter_field or "pmid"
            async for record in self.fetch_filtered(
                entity_type, filter_ids, effective_filter_field, limit
            ):
                yield record
            return

        if entity_type != "publication":
            raise ValueError("PubMedAdapter only supports 'publication'")

        resume_offset = max(0, offset or 0)
        if limit is not None and resume_offset >= limit:
            self.logger.info(
                "pubmed_resume_offset_reached_limit",
                offset=resume_offset,
                limit=limit,
            )
            return

        search_term = query or "pharmacogenomics[Title/Abstract]"
        pmids = await self._get_pmids(search_term, limit or 10000)

        if not pmids:
            return

        if resume_offset:
            self.logger.info(
                "pubmed_resume_skip_processed",
                offset=resume_offset,
                pmids_found=len(pmids),
            )
            pmids = pmids[resume_offset:]

        remaining_limit = None if limit is None else max(0, limit - resume_offset)

        async for record in self._yield_articles_from_pmids(pmids, remaining_limit):
            yield record

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
        """Fetch PubMed records as typed DTO models.

        Args:
            entity_type: Entity type identifier.
            limit: Maximum number of records to process.
            query: Search query string.
            filter_ids: List of identifiers to filter by.
            filter_field: Field name to apply filter on.
            validate: Whether to validate.

        Returns:
            Async iterator yielding fetched records.
        """
        model_class = PUBMED_DTO_MODELS.get(entity_type)
        if model_class is None:
            raise ValueError(f"No DTO model for entity_type '{entity_type}'")

        async for record in self.fetch(
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
        ):
            dto_data = {
                "pmid": record.get("pmid"),
                "title": record.get("article_title"),
                "raw_xml": record.get("_raw_xml"),
            }
            if validate:
                yield model_class.model_validate(dto_data)
            else:
                yield model_class.model_construct(**dto_data)

    async def aclose(self) -> None:
        """Close adapter resources."""
        if self.http_client:
            await self.http_client.__aexit__(None, None, None)


def _create_pubmed_adapter(
    http_client: UnifiedHTTPClient | None,
    logger: LoggerPort | None,
    settings: Settings | None,
    **kwargs: Any,  # Any: forward arbitrary adap...
) -> PubMedAdapter:
    email = kwargs.get("email")
    if not email and settings:
        email = getattr(settings, "default_email", None)
    if not email:
        raise ValueError("PubMed adapter requires email")

    api_key = kwargs.get("api_key")
    if not api_key and settings and hasattr(settings, "pubmed_api_key"):
        pubmed_key = settings.pubmed_api_key
        if pubmed_key:
            api_key = pubmed_key.get_secret_value()

    if http_client is None:
        raise ValueError("PubMed adapter requires http_client")
    if logger is None:
        raise ValueError("PubMed adapter requires logger")

    return PubMedAdapter(
        http_client=http_client,
        logger=logger,
        email=email,
        api_key=api_key,
        batch_size=kwargs.get("batch_size", 200),
        metrics=kwargs.get("metrics"),
    )
