"""In-memory storage implementation for testing.

Implements StoragePort interface without filesystem I/O.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import datetime

    from bioetl.domain.types import ArrowSchema, BatchID, RunID, RunType


class InMemoryStorage:
    """In-memory storage for tests.

    Implements StoragePort interface from domain/ports.py.
    """

    def __init__(self) -> None:
        """Initialize in-memory storage."""
        # Bronze: keyed by path pattern
        self.bronze: dict[str, list[bytes]] = defaultdict(list)
        self.bronze_metadata: dict[str, dict[str, Any]] = {}

        # Silver: keyed by table name
        self.silver: dict[str, list[dict[str, Any]]] = defaultdict(list)

        # Gold: keyed by table name
        self.gold: dict[str, list[dict[str, Any]]] = defaultdict(list)

        # Track operations for verification
        self.operations: list[dict[str, Any]] = []

    async def write_bronze(
        self,
        records: Iterator[bytes],
        provider: str,
        entity: str,
        date: datetime,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
        ingestion_ts: datetime,
    ) -> Path:
        """Write raw records to the Bronze layer.

        Args:
            records: Iterator of JSON-encoded record bytes.
            provider: Provider name.
            entity: Entity type.
            date: Date for path partitioning.
            batch_id: Unique batch identifier.
            run_id: Pipeline run identifier.
            run_type: Type of run.
            ingestion_ts: Ingestion timestamp from application layer.

        Returns:
            Path: Relative path to the written file.
        """
        key = f"v1/{provider}/{entity}/{date.strftime('%Y-%m-%d')}/{batch_id}.jsonl.zst"
        record_list = list(records)
        self.bronze[key].extend(record_list)
        self.bronze_metadata[key] = {
            "run_id": str(run_id),
            "run_type": run_type.value if hasattr(run_type, "value") else str(run_type),
            "ingestion_ts": ingestion_ts.isoformat(),
        }
        self.operations.append(
            {
                "operation": "write_bronze",
                "key": key,
                "record_count": len(record_list),
            }
        )
        return Path(key)

    async def write_silver(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        schema: ArrowSchema,
        mode: Literal["merge", "append", "delete"] = "merge",
        partition_cols: list[str] | None = None,
        on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error",
        column_order: list[str] | None = None,
        bronze_refs: list[Any] | None = None,
        key_nullability_rules: list[Any] | None = None,
        *,
        run_id: RunID | None = None,
        run_type: RunType | None = None,
        source_batch_id: BatchID | None = None,
        ingestion_ts: datetime | None = None,
    ) -> None:
        """Write transformed records to the Silver layer."""
        del (
            schema,
            partition_cols,
            on_schema_mismatch,
            column_order,
            bronze_refs,
            key_nullability_rules,
            run_id,
            run_type,
            source_batch_id,
            ingestion_ts,
        )
        if mode == "merge":
            # Simple merge: replace by primary keys
            pk_set = set(primary_keys)
            existing_by_pk: dict[tuple, dict[str, Any]] = {}
            for rec in self.silver[table_name]:
                pk_vals = tuple(rec.get(k) for k in pk_set)
                existing_by_pk[pk_vals] = rec

            for rec in records:
                pk_vals = tuple(rec.get(k) for k in pk_set)
                existing_by_pk[pk_vals] = rec

            self.silver[table_name] = list(existing_by_pk.values())
        elif mode == "append":
            self.silver[table_name].extend(records)
        elif mode == "delete":
            pk_set = set(primary_keys)
            to_delete = {tuple(rec.get(k) for k in pk_set) for rec in records}
            self.silver[table_name] = [
                rec
                for rec in self.silver[table_name]
                if tuple(rec.get(k) for k in pk_set) not in to_delete
            ]

        self.operations.append(
            {
                "operation": "write_silver",
                "table_name": table_name,
                "mode": mode,
                "record_count": len(records),
            }
        )

    async def write_gold(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        schema: Any,
        primary_keys: list[str] | None = None,
        mode: Literal["overwrite", "append", "scd2"] = "overwrite",
    ) -> None:
        """Write aggregated records to the Gold layer."""
        del schema, primary_keys
        if mode == "overwrite":
            self.gold[table_name] = list(records)
        elif mode == "append":
            self.gold[table_name].extend(records)
        elif mode == "scd2":
            # Simplified SCD2: just append with active flag
            self.gold[table_name].extend(records)

        self.operations.append(
            {
                "operation": "write_gold",
                "table_name": table_name,
                "mode": mode,
                "record_count": len(records),
            }
        )

    async def clear_silver(self, table_name: str, dry_run: bool = False) -> int:
        """Clear Silver layer data for a specific table."""
        if table_name in self.silver:
            count = len(self.silver[table_name])
            if not dry_run:
                del self.silver[table_name]
            return count
        return 0

    async def clear_gold(self, table_name: str, dry_run: bool = False) -> int:
        """Clear Gold layer data for a specific table."""
        if table_name in self.gold:
            count = len(self.gold[table_name])
            if not dry_run:
                del self.gold[table_name]
            return count
        return 0

    async def clear_csv(self, table_name: str | None = None) -> int:
        """Clear CSV export files (no-op for in-memory)."""
        del table_name
        return 0

    async def clear_delta(self, table_name: str | None = None) -> int:
        """Clear Delta tables (no-op for in-memory)."""
        del table_name
        return 0

    async def vacuum(
        self,
        table_name: str,
        retention_hours: int = 168,
        dry_run: bool = False,
    ) -> int:
        """Vacuum Delta table (simulated for in-memory).

        Returns simulated file count based on table content.
        """
        # In-memory storage doesn't have old files, return 0
        self.operations.append(
            {
                "operation": "vacuum",
                "table_name": table_name,
                "retention_hours": retention_hours,
                "dry_run": dry_run,
            }
        )
        return 0

    async def archive(
        self,
        table_name: str,
        target_path: str,
        remove_source: bool = False,
    ) -> int:
        """Archive table to target path (simulated for in-memory).

        Returns count of records as simulated file count.
        """
        file_count = 0

        # Count Silver records as "files"
        if table_name in self.silver:
            file_count += len(self.silver[table_name])
            if remove_source:
                del self.silver[table_name]

        # Count Gold records as "files"
        if table_name in self.gold:
            file_count += len(self.gold[table_name])
            if remove_source:
                del self.gold[table_name]

        self.operations.append(
            {
                "operation": "archive",
                "table_name": table_name,
                "target_path": target_path,
                "remove_source": remove_source,
                "file_count": file_count,
            }
        )

        return file_count

    def preview_cleanup(
        self,
        silver_table: str,
        gold_table: str | None = None,
    ) -> dict[str, Any]:
        """Preview what would be cleared."""
        silver_count = len(self.silver.get(silver_table, []))
        gold_count = len(self.gold.get(gold_table or "", [])) if gold_table else 0

        result = {
            "silver": {
                "path": f"memory://silver/{silver_table}",
                "file_count": silver_count,
                "exists": silver_table in self.silver,
            },
            "total_files": silver_count + gold_count,
        }

        if gold_table:
            result["gold"] = {
                "path": f"memory://gold/{gold_table}",
                "file_count": gold_count,
                "exists": gold_table in self.gold,
            }

        return result

    async def aclose(self) -> None:
        """Close storage connection (no-op for in-memory)."""
        return

    def clear(self) -> None:
        """Clear all data (test utility)."""
        self.bronze.clear()
        self.bronze_metadata.clear()
        self.silver.clear()
        self.gold.clear()
        self.operations.clear()
