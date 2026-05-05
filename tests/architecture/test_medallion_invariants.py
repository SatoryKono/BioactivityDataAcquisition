"""Architecture test: Medallion layer invariants.

REQ-LINEAGE-001: Bronze metadata for data lineage tracking.
Bronze layer MUST include metadata fields for traceability.

See docs/02-architecture/decisions/ADR-014-deterministic-writes.md
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Path relative to project root
BRONZE_WRITER_PATH = Path("src/bioetl/infrastructure/storage/bronze_writer.py")


class TestBronzeMetadataInvariants:
    """Tests ensuring Bronze writer includes required metadata fields."""

    @pytest.fixture
    def bronze_writer_source(self) -> str:
        """Get Bronze writer source code."""
        # Handle both running from project root and tests directory
        if BRONZE_WRITER_PATH.exists():
            path = BRONZE_WRITER_PATH
        else:
            path = Path(__file__).parent.parent.parent / BRONZE_WRITER_PATH

        return path.read_text(encoding="utf-8")

    def test_bronze_writer_requires_metadata(self, bronze_writer_source: str) -> None:
        """Bronze writer MUST include metadata fields for lineage tracking.

        These fields are essential for data provenance and audit trail.
        Removing any of them breaks the ability to trace data origins.

        Metadata is stored in separate .meta.json files alongside data.
        """
        # Bronze metadata uses non-prefixed keys in _build_bronze_metadata method
        # These are the canonical field names in Bronze layer
        required_fields = [
            "ingestion_ts",  # When data was ingested (ISO timestamp)
            "run_id",  # Pipeline run identifier
            "run_type",  # Type of run (incremental, backfill, rebuild)
            "batch_id",  # Source batch identifier for traceability
        ]

        missing_fields = []
        for field in required_fields:
            # Check for field as dictionary key in metadata construction
            # Pattern: "field_name": ... in _build_bronze_metadata
            if f'"{field}"' not in bronze_writer_source:
                missing_fields.append(field)

        assert not missing_fields, (
            f"Bronze writer missing required metadata fields: {missing_fields}\n\n"
            "Bronze metadata is essential for data lineage tracking.\n"
            "These fields MUST be present in _build_bronze_metadata():\n"
            "  - ingestion_ts: Timestamp of data ingestion\n"
            "  - run_id: Pipeline run identifier\n"
            "  - run_type: Type of run (incremental/backfill/rebuild)\n"
            "  - batch_id: Source batch identifier\n\n"
            "See REQ-LINEAGE-001 and RULES.md §2.1.1"
        )

    def test_bronze_writer_has_metadata_builder(
        self, bronze_writer_source: str
    ) -> None:
        """Bronze writer MUST have _build_bronze_metadata method.

        This method centralizes metadata construction for consistency.
        """
        assert "_build_bronze_metadata" in bronze_writer_source, (
            "Bronze writer missing _build_bronze_metadata method.\n"
            "Metadata construction must be centralized in this method."
        )

    def test_bronze_writer_writes_metadata_file(
        self, bronze_writer_source: str
    ) -> None:
        """Bronze writer MUST write metadata to separate .meta.json file.

        Metadata is stored alongside data for atomic consistency.
        """
        assert ".meta.json" in bronze_writer_source, (
            "Bronze writer must write metadata to .meta.json files.\n"
            "Metadata files ensure data lineage is preserved with data."
        )

    def test_bronze_writer_validates_timestamps(self, bronze_writer_source: str) -> None:
        """Bronze writer MUST validate UTC timestamps.

        Per ADR-014, timestamps must be timezone-aware and in UTC
        for deterministic behavior and lineage consistency.
        """
        assert "_validate_utc_datetime" in bronze_writer_source, (
            "Bronze writer must validate UTC timestamps.\n"
            "Timestamps must be timezone-aware and in UTC per ADR-014."
        )

    def test_bronze_path_includes_date_partition(self) -> None:
        """Bronze paths MUST include date partitioning.

        Path format: bronze/{provider}/{entity}/{date}/
        """
        from unittest.mock import Mock

        from bioetl.domain.ports.noop import NoOpMetrics
        from bioetl.infrastructure.storage.bronze_writer import BronzeWriter

        writer = BronzeWriter(
            base_path="data/output/bronze",
            logger=Mock(),
            metrics=NoOpMetrics(),
        )
        path = writer._resolve_bronze_path(
            provider="chembl",
            entity="activity",
            date_str="2026-01-21",
            filename="batch_2026-01-21_123.jsonl.zst",
        )
        normalized = path.replace("\\", "/")
        assert normalized == "chembl/activity/2026-01-21/batch_2026-01-21_123.jsonl.zst"
        assert re.match(
            r"^chembl/activity/\d{4}-\d{2}-\d{2}/.+\.jsonl\.zst$",
            normalized,
        )


class TestSilverLayerInvariants:
    """Tests ensuring Silver layer strictly uses Delta Lake and policies."""

    @pytest.fixture
    def silver_writer_source(self) -> str:
        """Get Silver writer source code (main module + all mixins)."""
        base = Path("src/bioetl/infrastructure/storage")
        if not base.exists():
            base = Path(__file__).parent.parent.parent / base
        parts: list[str] = []
        for py_file in sorted(base.glob("silver_writer*.py")):
            parts.append(py_file.read_text(encoding="utf-8"))
        return "\n".join(parts)

    def test_silver_writer_uses_delta_lake(self, silver_writer_source: str) -> None:
        """Silver layer MUST use Delta Lake for storage.

        REQ-DATA-006: Silver layer must use Delta Lake format.
        Parquet files without Delta log are strictly prohibited in Silver.
        """
        assert (
            (
                "from deltalake import DeltaTable" in silver_writer_source
                and "from deltalake import write_deltalake" in silver_writer_source
            )
            or "from deltalake import DeltaTable, write_deltalake"
            in silver_writer_source
        ), (
            "SilverWriter must import DeltaTable and write_deltalake from deltalake.\n"
            "This confirms compliance with Delta Lake requirement."
        )

    def test_silver_writer_enforces_write_policy(
        self, silver_writer_source: str
    ) -> None:
        """Silver layer MUST enforce write mode policies.

        RULES.md §2.1.1: Silver allows Merge/Upsert.
        """
        assert "_enforce_write_policy" in silver_writer_source, (
            "SilverWriter must have _enforce_write_policy method.\n"
            "This ensures only allowed write modes (MERGE, APPEND) are used."
        )

    def test_silver_writer_validates_schema(self, silver_writer_source: str) -> None:
        """Silver layer MUST validate schema (Pandera or drift check)."""
        has_pandera = "_validate_silver_pandera" in silver_writer_source
        has_drift = "_check_schema_drift" in silver_writer_source

        assert has_pandera or has_drift, (
            "SilverWriter must implement schema validation (Pandera or Drift Check).\n"
            "Silver layer requires schema enforcement (Schema on Write)."
        )

    def test_silver_writer_no_pandas_parquet(self, silver_writer_source: str) -> None:
        """Silver layer MUST NOT use raw parquet writes (pandas/pyarrow).

        REQ-DATA-006: Direct Parquet writes bypass Delta transaction log.
        """
        forbidden = [
            "to_parquet",
            "write_table",  # pyarrow.parquet.write_table
        ]

        # We check for direct usage. Note: _prepare_arrow_data uses pyarrow, but
        # actual writing should be via write_deltalake.
        # We need to be careful not to flag valid imports, but function calls.

        # This is a heuristic check.
        for method in forbidden:
            # If method is used, it should be commented or part of some internal logic,
            # but ideally we rely on write_deltalake.
            # However, BaseDeltaWriter or others might use it for internal stuff?
            # silver_writer.py does NOT seem to use to_parquet or write_table.
            if f".{method}(" in silver_writer_source:
                pytest.fail(
                    f"SilverWriter seems to use raw '{method}()'. MUST use write_deltalake()."
                )

    def test_silver_path_is_delta_table_location(self) -> None:
        """Silver paths MUST resolve to Delta table directories."""
        from unittest.mock import Mock

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="data/output/silver", logger=Mock())
        path = writer._resolve_table_path("chembl.activity")
        normalized = path.replace("\\", "/")
        assert normalized == "data/output/silver/chembl/activity"


class TestGoldLayerInvariants:
    """Tests ensuring Gold layer uses Delta table locations."""

    def test_gold_path_is_delta_table_location(self) -> None:
        """Gold paths MUST resolve to Delta table directories."""
        from unittest.mock import Mock

        from bioetl.infrastructure.storage.gold_writer import GoldWriter

        writer = GoldWriter(base_path="data/output/gold", logger=Mock())
        path = writer._resolve_table_path("chembl.activity")
        normalized = path.replace("\\", "/")
        assert normalized == "data/output/gold/chembl/activity"


from unittest.mock import AsyncMock, Mock

from bioetl.application.services.medallion_lifecycle import MedallionLifecycleService
from bioetl.domain.medallion import MedallionPolicy
from bioetl.domain.types import RunType


class TestMedallionClearPolicy:
    @pytest.mark.asyncio
    async def test_rebuild_clears_silver_and_gold(self) -> None:
        storage = Mock()
        storage.clear_silver = AsyncMock(return_value=1)
        storage.clear_gold = AsyncMock(return_value=1)
        service = MedallionLifecycleService(storage=storage, logger=Mock())

        await service.clear(
            policy=MedallionPolicy.for_run_type(RunType.REBUILD),
            silver_table="chembl.activity",
            gold_table="chembl.activity",
        )

        storage.clear_silver.assert_awaited_once()
        storage.clear_gold.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_backfill_clears_silver_and_gold(self) -> None:
        storage = Mock()
        storage.clear_silver = AsyncMock(return_value=1)
        storage.clear_gold = AsyncMock(return_value=1)
        service = MedallionLifecycleService(storage=storage, logger=Mock())

        await service.clear(
            policy=MedallionPolicy.for_run_type(RunType.BACKFILL),
            silver_table="chembl.activity",
            gold_table="chembl.activity",
        )

        storage.clear_silver.assert_awaited_once()
        storage.clear_gold.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_incremental_does_not_clear_silver_and_gold(self) -> None:
        storage = Mock()
        storage.clear_silver = AsyncMock(return_value=1)
        storage.clear_gold = AsyncMock(return_value=1)
        service = MedallionLifecycleService(storage=storage, logger=Mock())

        await service.clear(
            policy=MedallionPolicy.for_run_type(RunType.INCREMENTAL),
            silver_table="chembl.activity",
            gold_table="chembl.activity",
        )

        storage.clear_silver.assert_not_awaited()
        storage.clear_gold.assert_not_awaited()
