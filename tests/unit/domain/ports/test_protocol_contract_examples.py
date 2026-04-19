"""Illustrative contract examples for richer domain port protocols.

This file intentionally keeps only ports where example implementations add
signal beyond generic runtime-checkable and stub coverage.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Literal

import pytest

from bioetl.domain.ports import (
    QuarantinePort,
    StoragePort,
)
from bioetl.domain.types import BatchID, RunID


async def _yield_once() -> None:
    """Exercise async paths in protocol examples."""
    await asyncio.sleep(0)


@pytest.mark.unit
class TestStoragePortProtocol:
    """StoragePort warrants concrete examples because of its wide API surface."""

    def test_write_silver_signature(self) -> None:
        """StoragePort should require a specific write_silver signature."""
        from collections.abc import Iterator

        from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
        from bioetl.domain.value_objects.silver_result import SilverWriteResult

        class ValidStorage:
            def write_bronze(
                self,
                records: Iterator[bytes],
                provider: str,
                entity: str,
                date: Any,
                batch_id: BatchID,
                run_id: Any,
                run_type: Any,
                ingestion_ts: Any,  # Required per ADR-014
                source_metadata: Any = None,
            ) -> BronzeWriteResult:
                return BronzeWriteResult(
                    path="bronze/test",
                    record_count=0,
                    compressed_size=0,
                    raw_size=0,
                    checksum="sha256:test",
                )

            def write_silver(
                self,
                table_name: str,
                records: list[dict[str, Any]],
                primary_keys: list[str],
                schema: Any,
                mode: Literal["merge", "append", "delete"] = "merge",
                partition_cols: list[str] | None = None,
                on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error",
                column_order: list[str] | None = None,
                bronze_refs: list[BronzeWriteResult] | None = None,
                key_nullability_rules: list[Any] | None = None,
                *,
                run_id: RunID | None = None,
                run_type: Any = None,
                source_batch_id: BatchID | None = None,
                ingestion_ts: datetime | None = None,
            ) -> SilverWriteResult | None:
                return None

            async def write_gold(
                self,
                table_name: str,
                records: list[dict[str, Any]],
                schema: Any,
                primary_keys: list[str] | None = None,
                mode: Literal["overwrite", "append", "scd2"] = "overwrite",
                *,
                scd_config: dict[str, Any] | None = None,
                column_order: list[str] | None = None,
                ingestion_ts: datetime | None = None,
                run_id: RunID | None = None,
                silver_refs: list[Any] | None = None,
            ) -> None:
                await _yield_once()

            def get_table_path(
                self,
                table_name: str,
                layer: Literal["silver", "gold"] = "silver",
            ) -> Any:
                from pathlib import Path

                del layer
                return Path("test-output") / table_name

            def read_silver(
                self,
                table_name: str,
                columns: list[str] | None = None,
            ) -> list[dict[str, Any]]:
                return []

            async def write_silver_merged(
                self,
                table_name: str,
                records: list[dict[str, Any]],
                primary_keys: list[str] | None = None,
                *,
                run_id: str | None = None,
                sources_used: list[str] | None = None,
                preserve_column_order: bool = False,
            ) -> None:
                await _yield_once()

            async def write_gold_merged(
                self,
                table_name: str,
                records: list[dict[str, Any]],
                primary_keys: list[str] | None = None,
                *,
                completed_at: datetime | None = None,
                run_id: str | None = None,
                sources_used: list[str] | None = None,
                preserve_column_order: bool = False,
            ) -> None:
                await _yield_once()
                del completed_at

            def aclose(self) -> None:
                return None

            def clear_silver(self, table_name: str, dry_run: bool = False) -> int:
                return 0

            def clear_gold(self, table_name: str, dry_run: bool = False) -> int:
                return 0

            def clear_csv(self, table_name: str | None = None) -> int:
                return 0

            def clear_delta(self, table_name: str | None = None) -> int:
                return 0

            def vacuum(
                self,
                table_name: str,
                retention_hours: int = 168,
                dry_run: bool = False,
            ) -> int:
                return 0

            def archive(
                self,
                table_name: str,
                target_path: str,
                remove_source: bool = False,
            ) -> int:
                return 0

            def health_check(self) -> Any:
                from bioetl.domain.types import HealthStatus

                return HealthStatus.HEALTHY

            def preview_cleanup(
                self,
                silver_table: str,
                gold_table: str | None = None,
            ) -> dict[str, Any]:
                return {}

            async def optimize(
                self,
                table_name: str,
                retention_hours: int = 168,
                dry_run: bool = False,
            ) -> None:
                await _yield_once()

            def is_table_initialized(
                self,
                table_name: str,
                layer: Literal["silver", "gold"] = "silver",
            ) -> bool:
                del table_name, layer
                return True

            def cleanup_bronze(
                self,
                cutoff_date: Any,
                dry_run: bool = False,
            ) -> dict[str, int]:
                return {"files_removed": 0, "bytes_freed": 0, "directories_removed": 0}

            def deduplicate_silver(
                self,
                table_name: str,
                primary_keys: list[str],
            ) -> int:
                return 0

            def get_table_version(
                self,
                table_path: str,
            ) -> int | None:
                return None

        assert isinstance(ValidStorage(), StoragePort)

        # Note: @runtime_checkable protocols only check for method presence,
        # not signatures. Test missing methods instead.
        class InvalidStorage:
            def write_bronze(self, *args, **kwargs):
                del args, kwargs
                return "bronze"

            # Missing write_silver method entirely
            def write_gold(self, *args, **kwargs):
                del args, kwargs
                return "gold"

            def aclose(self):
                return None

        assert not isinstance(InvalidStorage(), StoragePort)


@pytest.mark.unit
class TestQuarantinePortProtocol:
    """QuarantinePort examples document the richer replay/write contract."""

    def test_valid_quarantine_implementation(self) -> None:
        """QuarantinePort should accept valid implementations."""
        from collections.abc import Iterator

        from bioetl.domain.types import QuarantineRecordStatus

        class ValidQuarantine:
            async def write(
                self,
                pipeline: str,
                error_code: str,
                payload: dict[str, Any],
                bronze_batch_id: BatchID,
                run_id: RunID | None = None,
                metadata: dict[str, Any] | None = None,
                *,
                ingestion_ts: datetime,
            ) -> None:
                await _yield_once()

            async def write_many(self, records: list[dict[str, Any]]) -> None:
                await _yield_once()

            def inspect(
                self,
                pipeline: str,
                limit: int = 10,
                error_code: str | None = None,
            ) -> list[dict[str, Any]]:
                return []

            def get_stats(
                self, pipeline: str, error_code: str | None = None
            ) -> dict[str, Any]:
                return {}

            def list_filtered_records(
                self,
                *,
                pipeline: str | None = None,
                run_type: str | None = None,
                reason_code: str | None = None,
                field: str | None = None,
                run_id: str | None = None,
                payload_hash: str | None = None,
                from_ts: str | None = None,
                to_ts: str | None = None,
                limit: int = 50,
                offset: int = 0,
                sort: str = "ingestion_ts_desc",
            ) -> dict[str, Any]:
                return {"items": [], "total": 0, "limit": limit, "offset": offset}

            def get_filtered_record(
                self,
                *,
                payload_hash: str,
                pipeline: str | None = None,
            ) -> dict[str, Any] | None:
                return None

            def get_record(
                self,
                *,
                payload_hash: str,
                pipeline: str | None = None,
            ) -> dict[str, Any] | None:
                return None

            def get_filtered_stats(
                self,
                *,
                pipeline: str | None = None,
                run_type: str | None = None,
                reason_code: str | None = None,
                field: str | None = None,
                run_id: str | None = None,
                payload_hash: str | None = None,
                from_ts: str | None = None,
                to_ts: str | None = None,
            ) -> dict[str, Any]:
                return {"total": 0}

            def get_filtered_filter_options(
                self,
                *,
                pipeline: str | None = None,
                run_type: str | None = None,
                reason_code: str | None = None,
                field: str | None = None,
                run_id: str | None = None,
                from_ts: str | None = None,
                to_ts: str | None = None,
            ) -> dict[str, Any]:
                return {
                    "pipelines": [pipeline],
                    "run_types": [],
                    "reason_codes": [],
                    "fields": [],
                    "run_ids": [],
                }

            def replay(
                self,
                pipeline: str,
                error_code: str | None = None,
                max_age_days: int = 7,
                *,
                now: datetime,
            ) -> Iterator[dict[str, Any]]:
                return iter([])

            def purge(
                self,
                pipeline: str,
                older_than_days: int = 30,
                *,
                now: datetime,
            ) -> int:
                return 0

            def update_status(
                self,
                payload_hash: str,
                new_status: QuarantineRecordStatus,
            ) -> bool:
                return True

            def aclose(self) -> None:
                return None

        assert isinstance(ValidQuarantine(), QuarantinePort)

    def test_missing_write_fails(self) -> None:
        """QuarantinePort should reject implementations missing write."""
        from collections.abc import Iterator

        from bioetl.domain.types import QuarantineRecordStatus

        class InvalidQuarantine:
            # Missing write method
            def inspect(
                self,
                pipeline: str,
                limit: int = 10,
                error_code: str | None = None,
            ) -> list[dict[str, Any]]:
                return []

            def get_stats(
                self, pipeline: str, error_code: str | None = None
            ) -> dict[str, Any]:
                return {}

            def replay(
                self,
                pipeline: str,
                error_code: str | None = None,
                max_age_days: int = 7,
                *,
                now: datetime,
            ) -> Iterator[dict[str, Any]]:
                return iter([])

            def purge(
                self,
                pipeline: str,
                older_than_days: int = 30,
                *,
                now: datetime,
            ) -> int:
                return 0

            def update_status(
                self,
                payload_hash: str,
                new_status: QuarantineRecordStatus,
            ) -> bool:
                return True

            async def aclose(self) -> None:
                await _yield_once()

        assert not isinstance(InvalidQuarantine(), QuarantinePort)
