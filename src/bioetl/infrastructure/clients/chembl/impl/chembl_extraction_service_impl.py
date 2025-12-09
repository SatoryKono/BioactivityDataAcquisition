"""
Implementation of ChemblExtractionService.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

from bioetl.domain.clients.contracts import DataClientABC
from bioetl.domain.observability.contracts import LoggingPortABC
from bioetl.domain.ports.extraction import ExtractionServiceABC
from bioetl.domain.ports.providers import DefaultFieldProviderABC

if TYPE_CHECKING:
    from bioetl.domain.record_source import RawRecord


class ChemblExtractionServiceImpl(ExtractionServiceABC):
    """
    Implementation of ExtractionServiceABC for ChEMBL.
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
        self.logger = logger
        self.field_provider = field_provider
        self._version_cache: str | None = None

    def get_release_version(self) -> str:
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

    def extract_all(self, entity: str, **filters: Any) -> list[RawRecord]:
        records = []
        for batch in self.iter_extract(entity, **filters):
            records.extend(batch)
        return records

    def iter_extract(
        self, entity: str, *, chunk_size: int | None = None, **filters: Any
    ) -> Iterable[list[RawRecord]]:
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

        # Configure builder
        if hasattr(builder, "build_for_endpoint"):
            builder.build_for_endpoint(mapped_entity)
        elif hasattr(builder, "for_endpoint"):
            builder.for_endpoint(mapped_entity)

        # Build URL
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
        filters = {filter_key: ",".join(batch_ids), "limit": len(batch_ids)}
        return self.client.fetch(entity, **filters)

    def parse_response(self, raw_response: dict[str, Any]) -> list[dict[str, Any]]:
        if hasattr(self.client, "response_parser"):
            return getattr(self.client, "response_parser").parse(raw_response)

        # Fallback simple parsing
        for value in raw_response.values():
            if isinstance(value, list):
                return value
        return []

    def serialize_records(
        self, entity: str, records: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return records
