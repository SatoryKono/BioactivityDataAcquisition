"""ID Mapping Data Source.

Implements DataSourcePort for ChEMBL → UniProt ID mapping pipeline.
Loads ChEMBL target IDs via a reader port and maps them to UniProt accessions.
"""

from __future__ import annotations

__all__ = ["IDMappingDataSource"]


from typing import TYPE_CHECKING, Any, Self

from bioetl.domain.types import HealthStatus, JsonDict

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

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
        # Enter the underlying client's context (opens HTTP client)
        await self._client.__aenter__()
        self._is_open = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,  # Any: TracebackType | None per async context manager protocol
    ) -> None:
        """Exit async context manager."""
        await self.aclose()

    async def aclose(self) -> None:
        """Close data source and release resources."""
        # Exit the underlying client's context (closes HTTP client)
        if self._is_open:
            await self._client.__aexit__(None, None, None)
        self._is_open = False

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

        Resolves ChEMBL IDs from one of three sources (priority order):
        1. seed_ids from constructor (composite pipeline mode)
        2. filter_ids parameter (if passed by caller)
        3. source reader at input_path (standalone mode)

        Then maps them to UniProt accessions via UniProt ID Mapping API.

        Args:
            entity_type: Entity type (should be 'idmapping').
            limit: Optional limit on number of records.
            query: Unused (for interface compatibility).
            filter_ids: Optional ChEMBL IDs passed by caller.
            filter_field: Unused (for interface compatibility).

        Yields:
            Dicts with target_id and uniprot_accession fields.

        Raises:
            FileNotFoundError: If input source doesn't exist (standalone mode).
            ValueError: If required column is missing in the source.

        Returns:
            Async iterator yielding fetched records.
        """
        _ = query, filter_field

        if entity_type != "idmapping":
            self._logger.warning(
                "unexpected_entity_type",
                expected="idmapping",
                received=entity_type,
            )

        # Step 1: Resolve ChEMBL IDs — seed_ids > filter_ids > source reader
        if self._seed_ids:
            chembl_ids = list(self._seed_ids)
            source = "seed"
            self._logger.info(
                "idmapping_using_seed_ids",
                count=len(chembl_ids),
            )
        elif filter_ids:
            chembl_ids = list(filter_ids)
            source = "filter"
            self._logger.info(
                "idmapping_using_filter_ids",
                count=len(chembl_ids),
            )
        else:
            chembl_ids = await self._read_chembl_ids()
            source = "csv"

        # Apply limit if specified
        if limit is not None:
            chembl_ids = chembl_ids[:limit]

        if not chembl_ids:
            self._logger.warning("no_ids_to_map", input_path=str(self._input_path))
            return

        self._logger.info(
            "idmapping_fetch_started",
            source=source,
            input_path=str(self._input_path),
            chembl_id_count=len(chembl_ids),
        )

        # Step 2: Call UniProt ID Mapping API
        mapping_results = await self._client.map_ids(
            from_db=self._from_db,
            to_db=self._to_db,
            ids=chembl_ids,
        )

        # Step 3: Yield records for each ChEMBL ID
        found_count = 0
        for chembl_id in chembl_ids:
            entry_data = mapping_results.get(chembl_id)
            if entry_data is not None and isinstance(entry_data, dict):
                found_count += 1
                result: JsonDict = {  # Any: record values are heterogeneous
                    "target_id": chembl_id
                }  # Any: record values are heterogeneous
                result.update(entry_data)
                yield result
            else:
                yield {
                    "target_id": chembl_id,
                    "uniprot_accession": None,
                }

        self._logger.info(
            "idmapping_fetch_completed",
            total_ids=len(chembl_ids),
            mapped=found_count,
            not_mapped=len(chembl_ids) - found_count,
        )

    async def _read_chembl_ids(self) -> list[str]:
        """Read ChEMBL target IDs through the injected source reader.

        Returns:
            List of ChEMBL target IDs.

        Raises:
            FileNotFoundError: If input source doesn't exist.
            ValueError: If required column is missing.
        """
        return await self._id_source_reader.read_ids(
            source_path=self._input_path,
            id_column=self._id_column,
        )

    async def health_check(self) -> HealthStatus:
        """Check data source health.

        Verifies:
        1. Input source exists (only in standalone mode, skipped when seed_ids provided)
        2. ID Mapping API is healthy

        Returns:
            HealthStatus indicating overall health.
        """
        # Skip file check when seed_ids are provided (composite mode)
        if not self._seed_ids:
            file_exists = await self._id_source_reader.source_exists(
                source_path=self._input_path
            )
            if not file_exists:
                self._logger.warning(
                    "health_check_failed",
                    reason="input_file_missing",
                    path=self._input_path,
                )
                return HealthStatus.UNHEALTHY

        # Check API health
        api_status = await self._client.health_check()
        if api_status != HealthStatus.HEALTHY:
            return api_status

        return HealthStatus.HEALTHY

    def __repr__(self) -> str:
        """Return string representation."""
        return (
            f"IDMappingDataSource("
            f"input_path='{self._input_path}', "
            f"from_db='{self._from_db}', "
            f"to_db='{self._to_db}')"
        )
