"""ID Mapping Data Source.

Implements DataSourcePort for ChEMBL → UniProt ID mapping pipeline.
Loads ChEMBL target IDs via a reader port and maps them to UniProt accessions.
"""

from __future__ import annotations

__all__ = ["IDMappingDataSource"]


from typing import TYPE_CHECKING, Self

from bioetl.domain.types import HealthStatus, JsonDict

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Mapping
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
        # Enter the underlying client's context (opens HTTP client)
        await self._client.__aenter__()
        self._is_open = True
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

        Args:
            entity_type: Entity type string; validated against configured entity type.
            limit: Maximum number of records to yield, or None for all.
            query: Unused; kept for interface compatibility.
            filter_ids: Optional list of ChEMBL IDs to map; overrides CSV input.
            filter_field: Unused; filtering uses internal config.
            offset: Unused; all IDs are resolved upfront from CSV or filter_ids.
        """
        _ = query, filter_field
        self._warn_unexpected_entity_type(entity_type)
        chembl_ids, source = await self._resolve_chembl_ids(filter_ids, limit)
        if not chembl_ids:
            self._logger.warning("no_ids_to_map", input_path=str(self._input_path))
            return

        self._logger.info(
            "idmapping_fetch_started",
            source=source,
            input_path=str(self._input_path),
            chembl_id_count=len(chembl_ids),
        )
        mapping_results = await self._client.map_ids(
            from_db=self._from_db,
            to_db=self._to_db,
            ids=chembl_ids,
        )
        found_count = 0
        for chembl_id in chembl_ids:
            record, is_mapped = self._build_mapping_record(chembl_id, mapping_results)
            if is_mapped:
                found_count += 1
            yield record

        self._logger.info(
            "idmapping_fetch_completed",
            total_ids=len(chembl_ids),
            mapped=found_count,
            not_mapped=len(chembl_ids) - found_count,
        )

    def _warn_unexpected_entity_type(self, entity_type: str) -> None:
        """Warn when fetch is called with unsupported entity type."""
        if entity_type == "idmapping":
            return
        self._logger.warning(
            "unexpected_entity_type",
            expected="idmapping",
            received=entity_type,
        )

    async def _resolve_chembl_ids(
        self,
        filter_ids: list[str] | None,
        limit: int | None,
    ) -> tuple[list[str], str]:
        """Resolve ChEMBL IDs from seed, filter, or configured source."""
        if self._seed_ids:
            chembl_ids = list(self._seed_ids)
            self._logger.info("idmapping_using_seed_ids", count=len(chembl_ids))
            source = "seed"
        elif filter_ids:
            chembl_ids = list(filter_ids)
            self._logger.info("idmapping_using_filter_ids", count=len(chembl_ids))
            source = "filter"
        else:
            chembl_ids = await self._read_chembl_ids()
            source = "csv"
        return self._apply_limit(chembl_ids, limit), source

    @staticmethod
    def _apply_limit(ids: list[str], limit: int | None) -> list[str]:
        """Apply optional limit to ID list."""
        if limit is None:
            return ids
        return ids[:limit]

    @staticmethod
    def _build_mapping_record(
        chembl_id: str,
        mapping_results: Mapping[
            str, JsonDict | None
        ],  # Any: mapping payload values vary by provider
    ) -> tuple[JsonDict, bool]:
        """Build output record and mapped flag for one ChEMBL ID."""
        entry_data = mapping_results.get(chembl_id)
        if entry_data is not None and isinstance(entry_data, dict):
            result: JsonDict = {"target_id": chembl_id}
            result.update(entry_data)
            return result, True

        return {
            "target_id": chembl_id,
            "uniprot_accession": None,
        }, False

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
