"""Key Extractor Service.

Application Service that extracts join keys from seed Silver tables
for enrichment pipeline coordination.

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import polars as pl

    from bioetl.domain.ports import LoggerPort, StoragePort


class KeyExtractorService:
    """Extracts join keys from seed Silver tables.

    This service reads the seed Silver table and extracts only the
    columns needed for enrichment joins. This minimizes memory usage
    when coordinating enrichers.

    Attributes:
        storage: Storage port for reading Silver tables.
        logger: Structured logger.

    Example:
        >>> extractor = KeyExtractorService(storage=storage, logger=logger)
        >>> keys_df = await extractor.extract(
        ...     silver_table="silver/chembl/publication",
        ...     keys=("document_id", "doi", "pmid"),
        ... )
        >>> keys_df.columns
        ['document_id', 'doi', 'pmid']
    """

    def __init__(
        self,
        storage: StoragePort,
        logger: LoggerPort,
    ) -> None:
        """Initialize key extractor service.

        Args:
            storage: Storage port for reading tables.
            logger: Structured logger.
        """
        self._storage = storage
        self._logger = logger

    async def _read_silver_table(self, path: str) -> pl.DataFrame:
        """Read a Silver table.

        TODO: This requires a DeltaReaderPort extension to StoragePort.
        Current implementation uses direct deltalake access.
        """
        import polars as pl
        from deltalake import DeltaTable

        table = DeltaTable(path)
        result = pl.from_arrow(table.to_pyarrow_table())
        # from_arrow may return Series for single-column tables
        if isinstance(result, pl.Series):
            return result.to_frame()
        return result

    async def extract(
        self,
        silver_table: str,
        keys: Sequence[str],
    ) -> pl.DataFrame:
        """Extract join keys from seed Silver table.

        Reads only the specified key columns from the Silver table.
        Removes duplicates and null-only rows.

        Args:
            silver_table: Path to seed Silver table.
            keys: Column names to extract as join keys.

        Returns:
            DataFrame with only the key columns, deduplicated.

        Raises:
            ValueError: If Silver table is empty or keys not found.

        Example:
            >>> keys_df = await extractor.extract(
            ...     silver_table="silver/chembl/publication",
            ...     keys=("doi", "pmid"),
            ... )
            >>> len(keys_df)
            1000
        """
        import polars as pl

        self._logger.info(
            "Extracting keys from seed Silver",
            table=silver_table,
            keys=list(keys),
        )

        # Read full table
        # TODO: Use DeltaReaderPort when available
        full_df = await self._read_silver_table(silver_table)

        if len(full_df) == 0:
            raise ValueError(f"Seed Silver table is empty: {silver_table}")

        # Validate keys exist
        available_cols = set(full_df.columns)
        missing_keys = set(keys) - available_cols
        if missing_keys:
            raise ValueError(
                f"Keys not found in seed table: {missing_keys}. "
                f"Available: {available_cols}"
            )

        # Select only key columns
        keys_df = full_df.select(list(keys))

        # Remove rows where ALL keys are null
        # (but keep rows where at least one key is non-null)
        null_check = pl.all_horizontal([pl.col(k).is_null() for k in keys])
        keys_df = keys_df.filter(~null_check)

        # Deduplicate
        original_count = len(keys_df)
        keys_df = keys_df.unique()
        dedup_count = len(keys_df)

        self._logger.info(
            "Keys extracted",
            table=silver_table,
            original_records=original_count,
            unique_keys=dedup_count,
            duplicates_removed=original_count - dedup_count,
        )

        return keys_df
