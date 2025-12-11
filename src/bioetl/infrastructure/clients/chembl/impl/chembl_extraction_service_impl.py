"""Implementation of ChemblExtractionService."""

from __future__ import annotations

from typing import Any, Iterable

from bioetl.domain.clients.contracts import DataClientWithBuilderProtocol
from bioetl.domain.clients.resilience import RetryExhaustedError
from bioetl.domain.data import RecordBatch
from bioetl.domain.errors import (
    ClientError,
    MetadataFetchError,
)
from bioetl.domain.observability.contracts import LoggingPortABC
from bioetl.domain.ports.extraction import (
    ExtractionServiceABC,
    VersionProviderABC,
)
from bioetl.domain.ports.filters import FilterEnricherABC
from bioetl.domain.ports.parsing import ResponseParserPortABC
from bioetl.infrastructure.clients.chembl.constants import resolve_endpoint
from bioetl.infrastructure.clients.chembl.response_parser import (
    ChemblGenericResponseParser,
)


class ChemblExtractionServiceImpl(ExtractionServiceABC, VersionProviderABC):
    """Extraction service for ChEMBL data.

    Returns raw dicts - domain model mapping is application layer responsibility.
    All dependencies must be explicitly injected - no default fallbacks.
    Use composition root or factories to create instances.

    Args:
        client: Data client with request builder support. Must implement
            DataClientWithBuilderProtocol for typed access to request_builder.
        logger: Logger for observability.
        batch_size: Default batch size for extraction.
        filter_enricher: Optional filter enricher for query augmentation.
        parser: Response parser. Defaults to ChemblGenericResponseParser.
    """

    def __init__(
        self,
        client: DataClientWithBuilderProtocol,
        logger: LoggingPortABC,
        batch_size: int = 1000,
        filter_enricher: FilterEnricherABC | None = None,
        *,
        parser: ResponseParserPortABC | None = None,
    ) -> None:
        self._client = client
        self._batch_size = batch_size
        self._logger = logger
        self._filter_enricher = filter_enricher
        self._parser = parser or ChemblGenericResponseParser()
        self._version_cache: str | None = None

    @property
    def client(self) -> DataClientWithBuilderProtocol:
        """Return the underlying data client."""
        return self._client

    @property
    def batch_size(self) -> int:
        """Return the default batch size."""
        return self._batch_size

    @property
    def logger(self) -> LoggingPortABC:
        """Return the logger."""
        return self._logger

    def get_release_version(self) -> str:
        """Get the raw ChEMBL release version from metadata.

        Returns:
            str: The raw release version string (e.g., '34', '35').

        Raises:
            MetadataFetchError: If metadata cannot be fetched after retries.

        Note:
            This returns raw version without 'chembl_' prefix.
            Use domain.services.version_formatter.format_chembl_version()
            in application layer for formatted version.
        """
        if self._version_cache:
            return self._version_cache

        try:
            meta = self.client.metadata()
            # API returns {'chembl_db_version': 'ChEMBL_36', ...}
            if meta and "chembl_db_version" in meta:
                raw_version = str(meta["chembl_db_version"])
                # Extract version number from format 'ChEMBL_36' -> '36'
                self._version_cache = self._parse_version_string(raw_version)
            else:
                self._logger.warning(
                    "metadata_missing_release",
                    message=(
                        "ChEMBL metadata response missing 'chembl_db_version' field"
                    ),
                    response_keys=list(meta.keys()) if meta else [],
                )
                self._version_cache = "unknown"
        except (ConnectionError, TimeoutError) as exc:
            self._logger.error(
                "metadata_fetch_network_error",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise MetadataFetchError(
                provider="chembl",
                message=f"Network error fetching ChEMBL metadata: {exc}",
                cause=exc,
                fallback_value="unknown",
            ) from exc
        except (ClientError, RetryExhaustedError) as exc:
            self._logger.error(
                "metadata_fetch_client_error",
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise MetadataFetchError(
                provider="chembl",
                message=f"Client error fetching ChEMBL metadata: {exc}",
                cause=exc,
                fallback_value="unknown",
            ) from exc

        return self._version_cache

    @staticmethod
    def _parse_version_string(version_str: str) -> str:
        """Parse version string from ChEMBL API format.

        Handles formats:
            - 'ChEMBL_36' -> '36'
            - 'chembl_36' -> '36'
            - 'chembl36' -> '36' (without underscore)
            - '36' -> '36'

        Args:
            version_str: Raw version string from API.

        Returns:
            Extracted version number as string, or 'unknown' if parsing fails.
        """
        if not version_str:
            return "unknown"

        lower = version_str.lower()

        # Handle 'ChEMBL_XX' or 'chembl_XX' format (with underscore)
        if lower.startswith("chembl_"):
            result = version_str[7:]  # Remove 'ChEMBL_' or 'chembl_' prefix
            return result if result else "unknown"

        # Handle 'chemblXX' format (without underscore)
        if lower.startswith("chembl"):
            result = version_str[6:]  # Remove 'ChEMBL' or 'chembl' prefix
            return result if result else "unknown"

        # Already a plain number or other format
        return version_str

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
        """Stream records from ChEMBL as raw dicts.

        Args:
            entity: Entity name to extract (e.g., 'activity', 'assay').
            chunk_size: Records per batch. Defaults to batch_size.
            **filters: Additional query filters.

        Yields:
            RecordBatch: Batches of raw record dictionaries.
        """
        # Use limit from filters as chunk_size if chunk_size not explicitly provided
        if chunk_size is None and "limit" in filters:
            effective_chunk_size = int(filters["limit"])
        else:
            effective_chunk_size = chunk_size or self._batch_size
        filters["limit"] = effective_chunk_size

        # Enrich filters using application-layer logic if available
        filters = self._enrich_filters(entity, filters)

        # Resolve entity to API endpoint using domain mapping
        endpoint = resolve_endpoint(entity)

        # Build request URL using typed builder - no runtime checks needed
        builder = self._client.request_builder
        url = builder.build_for_endpoint(endpoint).build_request(dict(filters))

        # Iterate pages and parse responses
        for page_data in self._client.iter_pages(url):
            records: RecordBatch = self._parser.parse_to_records(page_data)
            yield records

    def request_batch(
        self,
        entity: str,
        batch_ids: list[str],
        filter_key: str,
    ) -> dict[str, Any]:
        """Request a batch of records by IDs.

        Args:
            entity: Entity name.
            batch_ids: List of IDs.
            filter_key: Filter parameter key.

        Returns:
            dict[str, Any]: Raw API response.
        """
        filters = {filter_key: ",".join(batch_ids), "limit": len(batch_ids)}
        return self._client.fetch(entity, **filters)

    def parse_response(self, raw_response: object) -> RecordBatch:
        """Parse raw response into record dicts.

        Args:
            raw_response: Raw API response object.

        Returns:
            Parsed records as list[dict[str, Any]].
            Returns empty list if raw_response is None or not a dict.

        Raises:
            TypeError: If raw_response cannot be parsed.
        """
        if raw_response is None:
            return []

        # Parser expects a dict - return empty list for non-dict input
        if not isinstance(raw_response, dict):
            return []

        # Use the injected parser - no fallback to client parser
        # This enforces consistent parsing through the configured parser
        return self._parser.parse_to_records(raw_response)

    def serialize_records(self, entity: str, records: RecordBatch) -> RecordBatch:
        """Serialize records for storage.

        Args:
            entity: Entity name.
            records: List of record dicts.

        Returns:
            Serialized records as list[dict[str, Any]].
        """
        return records
