"""Silver layer storage port."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

from bioetl.domain.types import ArrowSchema, BronzeRecord
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.silver_result import SilverWriteResult

if TYPE_CHECKING:
    from bioetl.domain.config import KeyNullabilityRule

__all__ = ["SilverStoragePort"]


@runtime_checkable
class SilverStoragePort(Protocol):
    """Port for Silver layer storage operations.

    Covers Silver write (with schema), read-back, and layer clear.
    """

    async def write_silver(
        self,
        table_name: str,
        records: list[
            BronzeRecord
        ],  # BronzeRecord: normalized records before Silver write
        primary_keys: list[str],
        schema: ArrowSchema,
        mode: Literal["merge", "append", "delete"] = "merge",
        partition_cols: list[str] | None = None,
        on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error",
        column_order: list[str] | None = None,
        bronze_refs: list[BronzeWriteResult] | None = None,
        key_nullability_rules: list[KeyNullabilityRule] | None = None,
    ) -> SilverWriteResult | None:
        """Write transformed records to the Silver layer.

        Args:
            table_name: The name of the table to write to.
            records: A list of dictionaries, where each dictionary is a transformed record.
            primary_keys: A list of column names that form the primary key.
            schema: The PyArrow schema definition for the records (ArrowSchema alias).
            mode: The write mode (e.g., 'merge', 'append', 'delete').
            partition_cols: Optional list of columns to partition by.
            on_schema_mismatch: How to handle schema drift:
                - 'error': Raise SchemaEvolutionError (default)
                - 'evolve': Allow schema evolution (add new columns)
                - 'ignore': Proceed without changes (filter to existing schema)
            column_order: Optional explicit column order to apply.
            bronze_refs: Optional list of BronzeWriteResult from Bronze writes.
                If provided, bronze_paths will be populated in Silver metadata
                for complete lineage tracking (REQ-LINEAGE-001).
            key_nullability_rules: Optional rules for key nullability handling.

        Returns:
            SilverWriteResult with table info and Delta version for Gold lineage tracking
            (REQ-LINEAGE-002), or None if no records were written.

        Raises:
            SchemaEvolutionError: If schema drift detected and on_schema_mismatch='error'
        """
        ...

    async def read_silver(
        self,
        table_name: str,
        columns: list[str] | None = None,
    ) -> list[
        BronzeRecord
    ]:  # BronzeRecord: read-back Silver records share the same shape
        """Read records from a Silver layer Delta table.

        Args:
            table_name: The name of the table to read (e.g., 'chembl/activity').
            columns: Optional list of columns to select. If None, reads all columns.

        Returns:
            List of dictionaries, where each dictionary represents a record.

        Raises:
            FileNotFoundError: If the table does not exist.
        """
        ...

    async def clear_silver(self, table_name: str, dry_run: bool = False) -> int:
        """Clear Silver layer data for a specific table.

        Clears both Delta tables and CSV exports (if configured).
        Should only be called for rebuild/backfill runs, NOT for incremental.

        Args:
            table_name: The name of the table to clear.
            dry_run: If True, only count what would be deleted.

        Returns:
            Count of cleared items (tables + files).
        """
        ...
