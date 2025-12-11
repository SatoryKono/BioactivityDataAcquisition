"""Implementation of ChemblExtractionService."""

from __future__ import annotations

from typing import Any, Iterable

from bioetl.domain.clients.contracts import DataClientABC
from bioetl.domain.data import RecordBatch
from bioetl.domain.observability.contracts import LoggingPortABC
from bioetl.domain.ports.extraction import (
    ExtractionServiceABC,
    VersionProviderABC,
)
from bioetl.domain.ports.filters import FilterEnricherABC
from bioetl.domain.ports.parsing import ResponseParserPortABC
from bioetl.infrastructure.clients.chembl.constants import ENTITY_ENDPOINT_ALIASES
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblGenericResponseParser,
)


class ChemblExtractionServiceImpl(ExtractionServiceABC, VersionProviderABC):
    """Extraction service for ChEMBL data.

    Returns raw dicts - domain model mapping is application layer responsibility.
    All dependencies must be explicitly injected - no default fallbacks.
    Use composition root or factories to create instances.
    """

    def __init__(
        self,
        client: DataClientABC,
        logger: LoggingPortABC,
        batch_size: int = 1000,
        filter_enricher: FilterEnricherABC | None = None,
        *,
        parser: ResponseParserPortABC | None = None,
    ) -> None:
        self.client = client
        self.batch_size = batch_size
        self.logger = logger
        self._filter_enricher = filter_enricher
        self._parser = parser or ChemblGenericResponseParser()
        self._version_cache: str | None = None

    def get_release_version(self) -> str:
        """
        Get the raw ChEMBL release version from metadata.

        Returns:
            str: The raw release version string (e.g., '34', '35').
                 Returns 'unknown' if metadata is unavailable.

        Note:
            This returns raw version without 'chembl_' prefix.
            Use domain.services.version_formatter.format_chembl_version()
            in application layer for formatted version.
        """
        if self._version_cache:
            return self._version_cache

        try:
            meta = self.client.metadata()
            # Expecting {'chembl_release': '34', ...}
            if meta and "chembl_release" in meta:
                self._version_cache = str(meta["chembl_release"])
            else:
                self._version_cache = "unknown"
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to fetch metadata: {e}")
            self._version_cache = "unknown"

        return self._version_cache

    def _enrich_filters(
        self, entity: str, filters: dict[str, object]
    ) -> dict[str, object]:
        """Enrich filters using injected enricher if available."""
        if self._filter_enricher is None:
            return filters
        return self._filter_enricher.enrich_filters(entity, filters)

    def extract_all(self, entity: str, **filters: object) -> RecordBatch:
        """Extract all records for an entity as raw dicts.

        Args:
            entity: The entity name.
            **filters: Query filters.

        Returns:
            All matching records as list[dict[str, Any]].
        """
        records: RecordBatch = []
        for batch in self.iter_extract(entity, **filters):
            records.extend(batch)
        return records

    def iter_extract(
        self, entity: str, *, chunk_size: int | None = None, **filters: object
    ) -> Iterable[RecordBatch]:
        """Stream records from ChEMBL as raw dicts."""
        if chunk_size is None:
            chunk_size = filters.get("limit", self.batch_size)
        filters["limit"] = chunk_size

        # Enrich filters using application-layer logic if available
        filters = self._enrich_filters(entity, filters)

        # Ensure client has request_builder (runtime check)
        if not hasattr(self.client, "request_builder"):
            raise TypeError("Client must have request_builder (ChemblHttpClientImpl)")

        # Prepare limit
        limit = chunk_size or self.batch_size
        filters["limit"] = limit

        builder = getattr(self.client, "request_builder")

        # Resolve entity alias manually if needed (matches ChemblHttpClientImpl)
        mapped_entity = ENTITY_ENDPOINT_ALIASES.get(entity, entity)

        # Configure builder via legacy fluent methods expected in tests
        if hasattr(builder, "build_for_endpoint"):
            builder.build_for_endpoint(mapped_entity)
        elif hasattr(builder, "for_endpoint"):
            builder.for_endpoint(mapped_entity)

        # Build URL using dict-style params
        url = builder.build(filters)

        # Iterate pages
        for page_data in self.client.iter_pages(url):
            # Use generic parser for raw dict output
            records: RecordBatch = self._parser.parse_to_records(page_data)
            yield records

    def request_batch(
        self,
        entity: str,
        batch_ids: list[str],
        filter_key: str,
    ) -> dict[str, Any]:
        """
        Request a batch of records by IDs.

        Args:
            entity: Entity name.
            batch_ids: List of IDs.
            filter_key: Filter parameter key.

        Returns:
            dict[str, Any]: Raw API response.
        """
        filters = {filter_key: ",".join(batch_ids), "limit": len(batch_ids)}
        return self.client.fetch(entity, **filters)

    def parse_response(self, raw_response: object) -> RecordBatch:
        """Parse raw response into record dicts.

        Args:
            raw_response: Raw API response object.

        Returns:
            Parsed records as list[dict[str, Any]].
        """
        # Handle None or invalid input
        if raw_response is None:
            return []

        # Try client's parser first (for backward compatibility)
        if hasattr(self.client, "response_parser"):
            parser = getattr(self.client, "response_parser")
            if hasattr(parser, "parse"):
                try:
                    return parser.parse(raw_response)
                except (AttributeError, TypeError):
                    # Parser failed, fall through to internal parser
                    pass

        # Use internal parser (injected or default)
        try:
            return self._parser.parse_to_records(raw_response)
        except (AttributeError, TypeError):
            # Parser can't handle this input type, return empty list
            return []

    def serialize_records(self, entity: str, records: RecordBatch) -> RecordBatch:
        """Serialize records for storage.

        Args:
            entity: Entity name.
            records: List of record dicts.

        Returns:
            Serialized records as list[dict[str, Any]].
        """
        return records
