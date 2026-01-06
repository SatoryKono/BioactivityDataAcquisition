"""ID Mapping Data Source.

Implements DataSourcePort for ChEMBL → UniProt ID mapping pipeline.
Reads ChEMBL target IDs from CSV and maps them to UniProt accessions.
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

from bioetl.domain.types import HealthStatus

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.domain.ports import IDMappingClientPort, LoggerPort


class IDMappingDataSource:
    """Data source for ChEMBL → UniProt ID mapping.

    Reads target_chembl_id values from input CSV file and maps them
    to UniProt accessions using the UniProt ID Mapping REST API.

    Implements DataSourcePort protocol for integration with GenericPipeline.

    Example:
        >>> data_source = IDMappingDataSource(
        ...     idmapping_client=client,
        ...     input_path=Path("data/input/target.csv"),
        ...     logger=logger,
        ... )
        >>> async for record in data_source.fetch("idmapping"):
        ...     logger.info("record_fetched", record=record)
        # Output: {"target_chembl_id": "CHEMBL204", "uniprot_accession": "P00742"}
    """

    provider_name: str = "uniprot_idmapping"

    def __init__(
        self,
        idmapping_client: IDMappingClientPort,
        input_path: Path,
        logger: LoggerPort,
        from_db: str = "ChEMBL",
        to_db: str = "UniProtKB",
        id_column: str = "target_chembl_id",
    ) -> None:
        """Initialize ID Mapping data source.

        Args:
            idmapping_client: UniProt ID Mapping client for API calls.
            input_path: Path to CSV file containing ChEMBL target IDs.
            logger: LoggerPort for structured logging.
            from_db: Source database for ID mapping (default: 'ChEMBL').
            to_db: Target database for ID mapping (default: 'UniProtKB').
            id_column: Column name in CSV containing ChEMBL IDs.
        """
        self._client = idmapping_client
        self._input_path = input_path
        self._logger = logger
        self._from_db = from_db
        self._to_db = to_db
        self._id_column = id_column
        self._is_open = False

    async def __aenter__(self) -> Self:
        """Enter async context manager."""
        self._is_open = True
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit async context manager."""
        await self.aclose()

    async def aclose(self) -> None:
        """Close data source and release resources."""
        self._is_open = False

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Fetch ID mapping records.

        Reads ChEMBL IDs from CSV and maps them to UniProt accessions.
        Returns records with target_chembl_id and uniprot_accession fields.

        Args:
            entity_type: Entity type (should be 'idmapping').
            limit: Optional limit on number of records.
            query: Unused (for interface compatibility).
            filter_ids: Unused (IDs come from CSV).
            filter_field: Unused.

        Yields:
            Dicts with target_chembl_id and uniprot_accession fields.

        Raises:
            FileNotFoundError: If input CSV file doesn't exist.
            ValueError: If required column is missing from CSV.
        """
        # Ignore unused parameters (interface compatibility)
        _ = query, filter_ids, filter_field

        if entity_type != "idmapping":
            self._logger.warning(
                "unexpected_entity_type",
                expected="idmapping",
                received=entity_type,
            )

        # Step 1: Read ChEMBL IDs from CSV
        chembl_ids = self._read_chembl_ids()

        # Apply limit if specified
        if limit is not None:
            chembl_ids = chembl_ids[:limit]

        if not chembl_ids:
            self._logger.warning("no_ids_to_map", input_path=str(self._input_path))
            return

        self._logger.info(
            "idmapping_fetch_started",
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
            uniprot_accession = mapping_results.get(chembl_id)
            if uniprot_accession:
                found_count += 1

            yield {
                "target_chembl_id": chembl_id,
                "uniprot_accession": uniprot_accession,
            }

        self._logger.info(
            "idmapping_fetch_completed",
            total_ids=len(chembl_ids),
            mapped=found_count,
            not_mapped=len(chembl_ids) - found_count,
        )

    def _read_chembl_ids(self) -> list[str]:
        """Read ChEMBL target IDs from input CSV file.

        Returns:
            List of ChEMBL target IDs.

        Raises:
            FileNotFoundError: If input file doesn't exist.
            ValueError: If required column is missing.
        """
        if not self._input_path.exists():
            raise FileNotFoundError(f"Input file not found: {self._input_path}")

        ids: list[str] = []

        with self._input_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            if self._id_column not in (reader.fieldnames or []):
                raise ValueError(
                    f"Missing required column '{self._id_column}' in {self._input_path}"
                )

            for row in reader:
                chembl_id = row.get(self._id_column, "").strip()
                if chembl_id:
                    ids.append(chembl_id)

        self._logger.debug(
            "csv_read_complete",
            filepath=str(self._input_path),
            record_count=len(ids),
        )

        return ids

    async def health_check(self) -> HealthStatus:
        """Check data source health.

        Verifies:
        1. Input file exists
        2. ID Mapping API is healthy

        Returns:
            HealthStatus indicating overall health.
        """
        # Check input file
        if not self._input_path.exists():
            self._logger.warning(
                "health_check_failed",
                reason="input_file_missing",
                path=str(self._input_path),
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
