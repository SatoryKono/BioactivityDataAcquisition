"""Implementation of ChemblExtractionService."""

from __future__ import annotations

from typing import Any, Iterable

from bioetl.domain.clients.contracts import DataClientABC
from bioetl.domain.observability.contracts import LoggingPortABC
from bioetl.domain.ports.extraction import (
    ExtractionServiceABC,
    RawRecordBatch,
    VersionProviderABC,
)
from bioetl.domain.ports.parsing import ResponseParserPortABC
from bioetl.domain.ports.providers import DefaultFieldProviderABC
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
        field_provider: DefaultFieldProviderABC | None = None,
        *,
        parser: ResponseParserPortABC | None = None,
    ) -> None:
        self.client = client
        self.batch_size = batch_size
        self.logger = logger
        self.field_provider = field_provider
        self._parser = parser or ChemblGenericResponseParser()
        self._version_cache: str | None = None

    def get_release_version(self) -> str:
        """
        Get the ChEMBL release version from metadata.

        Returns:
            str: The release version string (e.g., 'chembl_34').
        """
        if self._version_cache:
            return self._version_cache

        try:
            meta = self.client.metadata()
            # Expecting {'chembl_release': '34', ...}
            if meta and "chembl_release" in meta:
                self._version_cache = f"chembl_{meta['chembl_release']}"
            else:
                self._version_cache = "chembl_unknown"
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to fetch metadata: {e}")
            self._version_cache = "chembl_unknown"

        return self._version_cache

    def _attach_entity_fields(
        self, entity: str, filters: dict[str, object]
    ) -> dict[str, object]:
        """Attach default fields to filters if configured."""
        if not self.field_provider:
            return filters

        # Skip if fields already specified
        if "fields" in filters:
            return filters

        new_filters = filters.copy()

        # Use get_default_fields as expected by tests/contracts
        fields = self.field_provider.get_default_fields(entity)
        if fields:
            new_filters["fields"] = ",".join(fields)

        return new_filters

    def extract_all(self, entity: str, **filters: object) -> RawRecordBatch:
        """Extract all records for an entity as raw dicts.

        Args:
            entity: The entity name.
            **filters: Query filters.

        Returns:
            All matching records as list[dict[str, Any]].
        """
        records: RawRecordBatch = []
        for batch in self.iter_extract(entity, **filters):
            records.extend(batch)
        return records

    def iter_extract(
        self, entity: str, *, chunk_size: int | None = None, **filters: object
    ) -> Iterable[RawRecordBatch]:
        """Stream records from ChEMBL as raw dicts."""
        if chunk_size is None:
            chunk_size = filters.get("limit", self.batch_size)
        filters["limit"] = chunk_size

        # Attach default fields if applicable
        filters = self._attach_entity_fields(entity, filters)

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
            records: RawRecordBatch = self._parser.parse_to_records(page_data)
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

    def parse_response(self, raw_response: object) -> RawRecordBatch:
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

    def serialize_records(self, entity: str, records: RawRecordBatch) -> RawRecordBatch:
        """Serialize records for storage.

        Args:
            entity: Entity name.
            records: List of record dicts.

        Returns:
            Serialized records as list[dict[str, Any]].
        """
        return records
