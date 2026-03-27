"""ID Mapping Data Source.

Implements DataSourcePort for ChEMBL → UniProt ID mapping pipeline.
Loads ChEMBL target IDs via a reader port and maps them to UniProt accessions.
"""

from __future__ import annotations

__all__ = ["IDMappingDataSource"]


from typing import TYPE_CHECKING, Self

from bioetl.application.core import (
    _idmapping_fetch_support as fetch_support,
)
from bioetl.application.core import _idmapping_lifecycle_support as lifecycle_support
from bioetl.domain.types import HealthStatus, JsonDict

if TYPE_CHECKING:
    from collections.abc import AsyncIterator
    from types import TracebackType

    from bioetl.domain.ports import (
        IDMappingPort,
        IDMappingSourceReaderPort,
        LoggerPort,
    )


class IDMappingDataSource:
    """Data source for ChEMBL → UniProt ID mapping.

    Reads target_id values from seed filter IDs (composite mode)
    or external source reader (standalone mode), then maps them to UniProt
    accessions using the UniProt ID Mapping REST API.

    Implements DataSourcePort protocol for integration with GenericPipeline.

    Example:
        >>> data_source = IDMappingDataSource(
        ...     idmapping_client=client,
        ...     id_source_reader=reader,
        ...     input_path="data/input/target.csv",
        ...     logger=logger,
        ... )
        >>> async for record in data_source.fetch("idmapping"):
        ...     logger.info("record_fetched", record=record)
        # Output: {"target_id": "CHEMBL204", "uniprot_accession": "P00742"}
    """

    provider_name: str = "uniprot_idmapping"

    def __init__(
        self,
        idmapping_client: IDMappingPort,
        id_source_reader: IDMappingSourceReaderPort,
        input_path: str,
        logger: LoggerPort,
        from_db: str = "ChEMBL",
        to_db: str = "UniProtKB",
        id_column: str = "target_id",
        seed_ids: list[str] | None = None,
    ) -> None:
        """Initialize ID Mapping data source.

        Args:
            idmapping_client: UniProt ID Mapping client for API calls.
            id_source_reader: Reader port for loading source IDs.
            input_path: Source path containing ChEMBL target IDs.
                Used as fallback when seed_ids is not provided.
            logger: LoggerPort for structured logging.
            from_db: Source database for ID mapping (default: 'ChEMBL').
            to_db: Target database for ID mapping (default: 'UniProtKB').
            id_column: Column name containing ChEMBL IDs.
            seed_ids: Pre-extracted ChEMBL target IDs from composite seed phase.
                When provided, source reader is not used.
        """
        self._client = idmapping_client
        self._id_source_reader = id_source_reader
        self._input_path = str(input_path)
        self._logger = logger
        self._from_db = from_db
        self._to_db = to_db
        self._id_column = id_column
        self._seed_ids = seed_ids
        self._is_open = False

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        await lifecycle_support.enter_data_source(self)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit async context manager."""
        await self.aclose()

    async def aclose(self) -> None:
        """Close data source and release resources."""
        await lifecycle_support.close_data_source(self)

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:  # Any: record values are heterogeneous
        """Fetch ID mapping records.

        Args:
            entity_type: Entity type string; validated against configured entity type.
            limit: Maximum number of records to yield, or None for all.
            query: Unused; kept for interface compatibility.
            filter_ids: Optional list of ChEMBL IDs to map; overrides CSV input.
            filter_field: Unused; filtering uses internal config.
            offset: Unused; all IDs are resolved upfront from CSV or filter_ids.
        """
        async for record in fetch_support.fetch_records(
            self,
            entity_type=entity_type,
            limit=limit,
            query=query,
            filter_ids=filter_ids,
            filter_field=filter_field,
            offset=offset,
        ):
            yield record

    async def health_check(self) -> HealthStatus:
        """Check data source health.

        Verifies:
        1. Input source exists (only in standalone mode, skipped when seed_ids provided)
        2. ID Mapping API is healthy

        Returns:
            HealthStatus indicating overall health.
        """
        return await lifecycle_support.health_check(self)

    def __repr__(self) -> str:
        """Return string representation."""
        return fetch_support.format_repr(self)
