"""In-memory storage for integration tests."""

from __future__ import annotations

from collections import defaultdict

from bioetl.domain.ports import StoragePort


class MemoryStorage(StoragePort):
    def __init__(self):
        self.data = defaultdict(list)
        self.bronze_metadata = {}  # Store run metadata for verification

    async def write_bronze(
        self, records, provider, entity, date, batch_id, run_id, run_type, ingestion_ts
    ):
        key = f"bronze/{provider}/{entity}/{date}/{batch_id}.jsonl.zst"
        # Consume iterator if necessary
        if hasattr(records, "__iter__") and not isinstance(records, list):
             records_list = list(records)
        else:
             records_list = records

        self.data[key].extend(records_list)
        # Store metadata for test verification
        self.bronze_metadata[key] = {
            "run_id": str(run_id),
            "run_type": run_type.value if hasattr(run_type, "value") else str(run_type),
            "ingestion_ts": ingestion_ts.isoformat() if ingestion_ts else None,
        }

    async def write_silver(
        self,
        table_name,
        records,
        primary_keys,
        schema,
        mode="merge",
        partition_cols=None,
        on_schema_mismatch=None,
    ):
        self.data[table_name].extend(records)

    async def write_gold(
        self,
        table_name,
        records,
        schema,
        primary_keys=None,
        mode="overwrite",
        ingestion_ts=None,
    ):
        self.data[table_name].extend(records)

    async def clear_silver(self, table_name, dry_run=False):
        if not dry_run:
            self.data[table_name] = []
        return 0

    async def clear_gold(self, table_name, dry_run=False):
        if not dry_run:
            self.data[table_name] = []
        return 0

    async def health_check(self):
        from bioetl.domain.types import HealthStatus
        return HealthStatus.HEALTHY

    async def aclose(self):
        pass

    async def clear_csv(self, table_name=None):
        return 0

    async def clear_delta(self, table_name=None):
        return 0

    async def vacuum(self, table_name, retention_hours=168, dry_run=False):
        return 0

    async def archive(self, table_name, target_path, remove_source=False):
        return 0

    def preview_cleanup(self, silver_table, gold_table=None):
        return {
            "silver": {"path": silver_table, "file_count": 0, "exists": True},
            "gold": {"path": gold_table, "file_count": 0, "exists": True} if gold_table else None,
            "total_files": 0
        }
