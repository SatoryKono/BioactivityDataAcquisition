"""
Implementation of ChemblExtractionService.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

from bioetl.domain.clients.contracts import DataClientABC
from bioetl.domain.observability.contracts import LoggingPortABC
from bioetl.domain.ports.extraction import RecordFetcherABC, VersionProviderABC
from bioetl.domain.ports.providers import DefaultFieldProviderABC
from bioetl.domain.schemas.chembl.raw_models import ActivityRawModel
from bioetl.infrastructure.observability.factories import default_logging_port

if TYPE_CHECKING:
    from bioetl.domain.record_source import RawRecord


class ChemblExtractionServiceImpl(RecordFetcherABC, VersionProviderABC):
    """
    Implementation of record fetcher for ChEMBL.
    Uses DataClientABC (expected to be ChemblHttpClientImpl) to fetch data.
    """

    def __init__(
        self,
        client: DataClientABC,
        batch_size: int = 1000,
        logger: LoggingPortABC | None = None,
        field_provider: DefaultFieldProviderABC | None = None,
    ) -> None:
        self.client = client
        self.batch_size = batch_size
        self.logger = logger or default_logging_port()
        self.field_provider = field_provider
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

    def extract_all(self, entity: str, **filters: object) -> list[RawRecord]:
        """
        Extract all records for an entity matching the filters.

        Args:
            entity: The entity name.
            **filters: Query filters.

        Returns:
            list[RawRecord]: List of extracted records.
        """
        records = []
        for batch in self.iter_extract(entity, **filters):
            records.extend(batch)
        return records

    def iter_extract(
        self, entity: str, *, chunk_size: int | None = None, **filters: object
    ) -> Iterable[list[RawRecord]]:
        """Stream records from ChEMBL."""
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
        aliases = {
            "publication": "document",
            "molecule": "molecule",
            "activity": "activity",
            "assay": "assay",
            "target": "target",
        }
        mapped_entity = aliases.get(entity, entity)

        # Configure builder via legacy fluent methods expected in tests
        if hasattr(builder, "build_for_endpoint"):
            builder.build_for_endpoint(mapped_entity)
        elif hasattr(builder, "for_endpoint"):
            builder.for_endpoint(mapped_entity)

        # Build URL using dict-style params
        url = builder.build(filters)

        # Iterate pages
        for page_data in self.client.iter_pages(url):
            records = self.parse_response(page_data)
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

    def parse_response(self, raw_response: dict[str, object]) -> list[ActivityRawModel]:
        """
        Parse raw response into a list of records.

        Args:
            raw_response: The raw API response.

        Returns:
            list[dict[str, Any]]: List of parsed records.
        """
        if hasattr(self.client, "response_parser"):
            parser = getattr(self.client, "response_parser")
            if hasattr(parser, "parse_response"):
                return parser.parse_response(raw_response)
            if hasattr(parser, "parse"):
                return parser.parse(raw_response)

        # Fallback simple parsing
        for value in raw_response.values():
            if isinstance(value, list):
                return [ActivityRawModel.model_validate(item) for item in value]
        return []

    def serialize_records(
        self, entity: str, records: list[ActivityRawModel]
    ) -> list[ActivityRawModel]:
        """
        Serialize records for storage.

        Args:
            entity: Entity name.
            records: List of records.

        Returns:
            list[dict[str, Any]]: Serialized records.
        """
        return records
