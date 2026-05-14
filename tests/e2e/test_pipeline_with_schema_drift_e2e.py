"""E2E tests for pipeline schema evolution handling.

Tests the pipeline's handling of schema drift scenarios:
- New fields added to incoming data (schema evolution)
- Fields removed from incoming data
- Schema mismatch handling modes: error, evolve, ignore

Per domain/config.py TableConfig:
- on_schema_mismatch: Literal["error", "evolve", "ignore"] = "error"
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pyarrow as pa
import pytest

from bioetl.domain.exceptions import SchemaEvolutionError
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from tests.helpers.deterministic_ids import deterministic_batch_id, deterministic_run_id


@pytest.fixture
def base_schema() -> pa.Schema:
    """Create base schema for testing."""
    return pa.schema(
        [
            pa.field("entity_id", pa.string()),
            pa.field("name", pa.string()),
            pa.field("value", pa.float64()),
            pa.field("_run_id", pa.string()),
            pa.field("_run_type", pa.string()),
            pa.field("_source_batch_id", pa.string()),
            pa.field("_ingestion_ts", pa.string()),
        ]
    )


@pytest.fixture
def evolved_schema() -> pa.Schema:
    """Create schema with additional field (evolution)."""
    return pa.schema(
        [
            pa.field("entity_id", pa.string()),
            pa.field("name", pa.string()),
            pa.field("value", pa.float64()),
            pa.field("new_field", pa.string()),  # New field added
            pa.field("_run_id", pa.string()),
            pa.field("_run_type", pa.string()),
            pa.field("_source_batch_id", pa.string()),
            pa.field("_ingestion_ts", pa.string()),
        ]
    )


@pytest.fixture
def base_records() -> list[dict[str, Any]]:
    """Create records matching base schema."""
    return [
        {
            "entity_id": "entity_1",
            "name": "Test Entity 1",
            "value": 1.0,
            "_run_id": deterministic_run_id("schema_drift.base.entity_1"),
            "_run_type": "incremental",
            "_source_batch_id": deterministic_batch_id("schema_drift.base.entity_1"),
            "_ingestion_ts": "2025-01-15T12:00:00Z",
        },
        {
            "entity_id": "entity_2",
            "name": "Test Entity 2",
            "value": 2.0,
            "_run_id": deterministic_run_id("schema_drift.base.entity_2"),
            "_run_type": "incremental",
            "_source_batch_id": deterministic_batch_id("schema_drift.base.entity_2"),
            "_ingestion_ts": "2025-01-15T12:00:00Z",
        },
    ]


@pytest.fixture
def evolved_records() -> list[dict[str, Any]]:
    """Create records with new field (schema evolution)."""
    return [
        {
            "entity_id": "entity_3",
            "name": "Test Entity 3",
            "value": 3.0,
            "new_field": "extra_data",  # New field
            "_run_id": deterministic_run_id("schema_drift.evolved.entity_3"),
            "_run_type": "incremental",
            "_source_batch_id": deterministic_batch_id(
                "schema_drift.evolved.entity_3"
            ),
            "_ingestion_ts": "2025-01-15T12:00:00Z",
        },
    ]


@pytest.fixture
def reduced_records() -> list[dict[str, Any]]:
    """Create records missing a field (schema reduction)."""
    return [
        {
            "entity_id": "entity_4",
            # "name" field is missing
            "value": 4.0,
            "_run_id": deterministic_run_id("schema_drift.reduced.entity_4"),
            "_run_type": "incremental",
            "_source_batch_id": deterministic_batch_id(
                "schema_drift.reduced.entity_4"
            ),
            "_ingestion_ts": "2025-01-15T12:00:00Z",
        },
    ]


@pytest.mark.e2e
@pytest.mark.asyncio
class TestSchemaEvolutionErrorMode:
    """Tests for schema drift with on_schema_mismatch='error' mode."""

    async def test_schema_drift_error_mode_raises_on_new_field(
        self, e2e_data_dir: Path, base_schema: pa.Schema, base_records, evolved_records
    ):
        """E2E: Schema drift with 'error' mode raises SchemaEvolutionError.

        When on_schema_mismatch='error' and incoming data has new fields,
        the write operation should fail with SchemaEvolutionError.
        """
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        logger = NoOpLogger()
        table_name = "test_schema_error"
        table_path = e2e_data_dir / "silver" / table_name

        writer = SilverWriter(
            base_path=str(e2e_data_dir / "silver"),
            logger=logger,
        )

        # First write establishes the schema
        await writer.write_silver(
            table_name=table_name,
            records=base_records,
            primary_keys=["entity_id"],
            schema=base_schema,
            mode="merge",
            on_schema_mismatch="error",
        )

        # Verify table was created
        assert table_path.exists()

        # Second write with new field should fail
        with pytest.raises(SchemaEvolutionError) as exc_info:
            await writer.write_silver(
                table_name=table_name,
                records=evolved_records,
                primary_keys=["entity_id"],
                schema=base_schema,  # Using original schema
                mode="merge",
                on_schema_mismatch="error",
            )

        assert "new_field" in str(exc_info.value.new_fields)

    async def test_schema_drift_error_mode_raises_on_removed_field(
        self, e2e_data_dir: Path, base_schema: pa.Schema, base_records, reduced_records
    ):
        """E2E: Schema drift with 'error' mode raises on removed field."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        logger = NoOpLogger()
        table_name = "test_schema_removed"

        writer = SilverWriter(
            base_path=str(e2e_data_dir / "silver"),
            logger=logger,
        )

        # First write establishes the schema
        await writer.write_silver(
            table_name=table_name,
            records=base_records,
            primary_keys=["entity_id"],
            schema=base_schema,
            mode="merge",
            on_schema_mismatch="error",
        )

        # Second write with missing field should fail
        with pytest.raises(SchemaEvolutionError) as exc_info:
            await writer.write_silver(
                table_name=table_name,
                records=reduced_records,
                primary_keys=["entity_id"],
                schema=base_schema,
                mode="merge",
                on_schema_mismatch="error",
            )

        assert "name" in str(exc_info.value.removed_fields)


@pytest.mark.e2e
@pytest.mark.asyncio
class TestSchemaEvolutionEvolveMode:
    """Tests for schema drift with on_schema_mismatch='evolve' mode."""

    async def test_schema_evolve_mode_allows_new_fields(
        self,
        e2e_data_dir: Path,
        base_schema: pa.Schema,
        evolved_schema: pa.Schema,
        base_records,
        evolved_records,
    ):
        """E2E: Schema evolution with 'evolve' mode allows new fields.

        When on_schema_mismatch='evolve', new fields should be added
        to the table schema and data written successfully.
        """
        pytest.importorskip("deltalake")
        from deltalake import DeltaTable

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        logger = NoOpLogger()
        table_name = "test_schema_evolve"
        table_path = e2e_data_dir / "silver" / table_name

        writer = SilverWriter(
            base_path=str(e2e_data_dir / "silver"),
            logger=logger,
        )

        # First write establishes the base schema
        await writer.write_silver(
            table_name=table_name,
            records=base_records,
            primary_keys=["entity_id"],
            schema=base_schema,
            mode="merge",
            on_schema_mismatch="evolve",
        )

        initial_count = len(DeltaTable(str(table_path)).to_pyarrow_table())
        assert initial_count == 2

        # Second write with evolved schema (new field)
        await writer.write_silver(
            table_name=table_name,
            records=evolved_records,
            primary_keys=["entity_id"],
            schema=evolved_schema,
            mode="merge",
            on_schema_mismatch="evolve",
        )

        # Verify records were added
        dt = DeltaTable(str(table_path))
        final_count = len(dt.to_pyarrow_table())
        assert final_count == 3  # 2 original + 1 new
        assert "new_field" in dt.schema().to_arrow().names

    async def test_schema_evolve_mode_logs_warning(
        self,
        e2e_data_dir: Path,
        base_schema: pa.Schema,
        evolved_schema: pa.Schema,
        base_records,
        evolved_records,
    ):
        """E2E: Schema evolution logs warning about drift."""
        pytest.importorskip("deltalake")
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_logger = MagicMock()
        mock_logger.warning = MagicMock()
        mock_logger.debug = MagicMock()
        table_name = "test_schema_evolve_log"

        writer = SilverWriter(
            base_path=str(e2e_data_dir / "silver"),
            logger=mock_logger,
        )

        # First write
        await writer.write_silver(
            table_name=table_name,
            records=base_records,
            primary_keys=["entity_id"],
            schema=base_schema,
            mode="merge",
            on_schema_mismatch="evolve",
        )

        # Second write with new field
        await writer.write_silver(
            table_name=table_name,
            records=evolved_records,
            primary_keys=["entity_id"],
            schema=evolved_schema,
            mode="merge",
            on_schema_mismatch="evolve",
        )

        # Verify warning was logged
        warning_calls = [
            call
            for call in mock_logger.warning.call_args_list
            if "Schema drift" in str(call)
        ]
        assert len(warning_calls) == 1

        # Third write with the same evolved schema should not trigger drift again.
        await writer.write_silver(
            table_name=table_name,
            records=evolved_records,
            primary_keys=["entity_id"],
            schema=evolved_schema,
            mode="merge",
            on_schema_mismatch="evolve",
        )

        repeated_warning_calls = [
            call
            for call in mock_logger.warning.call_args_list
            if "Schema drift" in str(call)
        ]
        assert len(repeated_warning_calls) == 1


@pytest.mark.e2e
@pytest.mark.asyncio
class TestSchemaEvolutionIgnoreMode:
    """Tests for schema drift with on_schema_mismatch='ignore' mode."""

    async def test_schema_ignore_mode_proceeds_silently(
        self, e2e_data_dir: Path, base_schema: pa.Schema, base_records, evolved_records
    ):
        """E2E: Schema ignore mode proceeds without error.

        When on_schema_mismatch='ignore', schema drift is detected
        but processing continues without modification.
        """
        from deltalake import DeltaTable

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        logger = NoOpLogger()
        table_name = "test_schema_ignore"
        table_path = e2e_data_dir / "silver" / table_name

        writer = SilverWriter(
            base_path=str(e2e_data_dir / "silver"),
            logger=logger,
        )

        # First write
        await writer.write_silver(
            table_name=table_name,
            records=base_records,
            primary_keys=["entity_id"],
            schema=base_schema,
            mode="merge",
            on_schema_mismatch="ignore",
        )

        # Verify initial write succeeded
        assert len(DeltaTable(str(table_path)).to_pyarrow_table()) > 0

        # Second write with evolved records - should not raise
        await writer.write_silver(
            table_name=table_name,
            records=evolved_records,
            primary_keys=["entity_id"],
            schema=base_schema,  # Original schema
            mode="merge",
            on_schema_mismatch="ignore",
        )

        # Records should be written (new_field filtered out)
        dt = DeltaTable(str(table_path))
        final_count = len(dt.to_pyarrow_table())
        assert final_count == 3


@pytest.mark.e2e
@pytest.mark.asyncio
class TestSchemaEvolutionEdgeCases:
    """Tests for edge cases in schema evolution."""

    async def test_first_write_no_existing_table(
        self, e2e_data_dir: Path, base_schema: pa.Schema, base_records
    ):
        """E2E: First write creates table without schema drift check."""
        from deltalake import DeltaTable

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        logger = NoOpLogger()
        table_name = "test_new_table"
        table_path = e2e_data_dir / "silver" / table_name

        writer = SilverWriter(
            base_path=str(e2e_data_dir / "silver"),
            logger=logger,
        )

        # Table doesn't exist yet
        assert not table_path.exists()

        # First write should succeed regardless of on_schema_mismatch
        await writer.write_silver(
            table_name=table_name,
            records=base_records,
            primary_keys=["entity_id"],
            schema=base_schema,
            mode="merge",
            on_schema_mismatch="error",  # Error mode but no existing table
        )

        # Table should now exist
        assert table_path.exists()
        dt = DeltaTable(str(table_path))
        assert len(dt.to_pyarrow_table()) == 2

    async def test_same_schema_no_drift(
        self, e2e_data_dir: Path, base_schema: pa.Schema, base_records
    ):
        """E2E: Same schema in subsequent writes does not trigger drift."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_logger = MagicMock()
        mock_logger.warning = MagicMock()
        mock_logger.debug = MagicMock()
        table_name = "test_no_drift"

        writer = SilverWriter(
            base_path=str(e2e_data_dir / "silver"),
            logger=mock_logger,
        )

        # First write
        await writer.write_silver(
            table_name=table_name,
            records=base_records,
            primary_keys=["entity_id"],
            schema=base_schema,
            mode="merge",
            on_schema_mismatch="error",
        )

        # Second write with same schema
        more_records = [
            {
                "entity_id": "entity_5",
                "name": "Test Entity 5",
                "value": 5.0,
                "_run_id": deterministic_run_id("schema_drift.no_drift.entity_5"),
                "_run_type": "incremental",
                "_source_batch_id": deterministic_batch_id(
                    "schema_drift.no_drift.entity_5"
                ),
                "_ingestion_ts": "2025-01-15T12:00:00Z",
            },
        ]

        # Should succeed without warning
        await writer.write_silver(
            table_name=table_name,
            records=more_records,
            primary_keys=["entity_id"],
            schema=base_schema,
            mode="merge",
            on_schema_mismatch="error",
        )

        # No schema drift warnings
        drift_warnings = [
            call
            for call in mock_logger.warning.call_args_list
            if "Schema drift" in str(call)
        ]
        assert len(drift_warnings) == 0

    async def test_multiple_schema_evolutions(
        self, e2e_data_dir: Path, base_schema: pa.Schema
    ):
        """E2E: Multiple schema evolutions are handled correctly."""
        pytest.importorskip("deltalake")
        from deltalake import DeltaTable

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        logger = NoOpLogger()
        table_name = "test_multi_evolve"
        table_path = e2e_data_dir / "silver" / table_name

        writer = SilverWriter(
            base_path=str(e2e_data_dir / "silver"),
            logger=logger,
        )

        # First write - base schema
        records_v1 = [
            {
                "entity_id": "v1",
                "name": "Version 1",
                "value": 1.0,
                "_run_id": deterministic_run_id("schema_drift.multi.v1"),
                "_run_type": "incremental",
                "_source_batch_id": deterministic_batch_id("schema_drift.multi.v1"),
                "_ingestion_ts": "2025-01-15T12:00:00Z",
            },
        ]

        await writer.write_silver(
            table_name=table_name,
            records=records_v1,
            primary_keys=["entity_id"],
            schema=base_schema,
            mode="merge",
            on_schema_mismatch="evolve",
        )

        # Second write - add field_a
        schema_v2 = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("name", pa.string()),
                pa.field("value", pa.float64()),
                pa.field("field_a", pa.string()),  # New field
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )

        records_v2 = [
            {
                "entity_id": "v2",
                "name": "Version 2",
                "value": 2.0,
                "field_a": "added_a",
                "_run_id": deterministic_run_id("schema_drift.multi.v2"),
                "_run_type": "incremental",
                "_source_batch_id": deterministic_batch_id("schema_drift.multi.v2"),
                "_ingestion_ts": "2025-01-15T12:00:00Z",
            },
        ]

        await writer.write_silver(
            table_name=table_name,
            records=records_v2,
            primary_keys=["entity_id"],
            schema=schema_v2,
            mode="merge",
            on_schema_mismatch="evolve",
        )

        # Third write - add field_b
        schema_v3 = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("name", pa.string()),
                pa.field("value", pa.float64()),
                pa.field("field_a", pa.string()),
                pa.field("field_b", pa.int64()),  # Another new field
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )

        records_v3 = [
            {
                "entity_id": "v3",
                "name": "Version 3",
                "value": 3.0,
                "field_a": "still_a",
                "field_b": 42,
                "_run_id": deterministic_run_id("schema_drift.multi.v3"),
                "_run_type": "incremental",
                "_source_batch_id": deterministic_batch_id("schema_drift.multi.v3"),
                "_ingestion_ts": "2025-01-15T12:00:00Z",
            },
        ]

        await writer.write_silver(
            table_name=table_name,
            records=records_v3,
            primary_keys=["entity_id"],
            schema=schema_v3,
            mode="merge",
            on_schema_mismatch="evolve",
        )

        # Verify all records present
        dt = DeltaTable(str(table_path))
        table = dt.to_pyarrow_table()
        assert len(table) == 3
