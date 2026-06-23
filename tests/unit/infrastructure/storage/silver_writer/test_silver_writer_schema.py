"""SilverWriter schema-drift unit tests."""

from __future__ import annotations

from tests.helpers.synthetic_paths import synthetic_test_root
from unittest.mock import MagicMock, patch

import pytest


pytestmark = pytest.mark.unit

TEST_ROOT = synthetic_test_root("bioetl-silver-writer-schema")
SILVER_BASE_PATH = TEST_ROOT / "silver"


class TestSilverWriterSchemaDrift:
    """Tests for schema drift detection and handling."""

    @pytest.mark.asyncio
    async def test_get_table_schema_returns_none_for_missing_table(self, noop_logger):
        """Test _get_table_schema returns None when table doesn't exist."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)
            result = await writer._get_table_schema("test.table")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_table_schema_returns_schema_for_existing_table(
        self, noop_logger
    ):
        """Test _get_table_schema returns schema for existing table."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        expected_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = expected_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        # Patch in base_delta_writer where _get_table_schema is defined
        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)
            result = await writer._get_table_schema("test.table")
            assert result == expected_schema

    @pytest.mark.asyncio
    async def test_schema_drift_raises_error_on_new_fields(
        self, valid_records, noop_logger
    ):
        """Test schema drift detection raises error when new fields detected."""
        import pyarrow as pa

        from bioetl.domain.exceptions import SchemaEvolutionError
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        # Existing schema has fewer fields than incoming records
        existing_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)

            with pytest.raises(SchemaEvolutionError) as exc_info:
                await writer._check_schema_drift("test.table", valid_records, "error")

            assert "value" in exc_info.value.new_fields
            assert exc_info.value.table == "test.table"

    @pytest.mark.asyncio
    async def test_schema_drift_raises_error_on_removed_fields(self, noop_logger):
        """Test schema drift detection raises error when fields are removed."""
        import pyarrow as pa

        from bioetl.domain.exceptions import SchemaEvolutionError
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        # Existing schema has more fields than incoming records
        existing_schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("extra_field", pa.string()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        records = [
            {
                "entity_id": "CHEMBL123",
                "_run_id": "uuid-123",
                "_run_type": "incremental",
                "_source_batch_id": "batch-456",
                "_ingestion_ts": "2025-01-15T12:00:00Z",
            }
        ]

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)

            with pytest.raises(SchemaEvolutionError) as exc_info:
                await writer._check_schema_drift("test.table", records, "error")

            assert "extra_field" in exc_info.value.removed_fields
            assert exc_info.value.table == "test.table"

    @pytest.mark.asyncio
    async def test_schema_drift_evolve_mode_does_not_raise(
        self, valid_records, noop_logger
    ):
        """Test schema drift with evolve mode proceeds without error."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        existing_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)

            # Should not raise
            await writer._check_schema_drift("test.table", valid_records, "evolve")

    @pytest.mark.asyncio
    async def test_schema_drift_ignore_mode_does_not_raise(
        self, valid_records, noop_logger
    ):
        """Test schema drift with ignore mode proceeds without error."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        existing_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)

            # Should not raise
            await writer._check_schema_drift("test.table", valid_records, "ignore")

    @pytest.mark.asyncio
    async def test_schema_drift_no_error_when_no_drift(
        self, valid_records, noop_logger
    ):
        """Test no error raised when schema matches."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        # Schema matches incoming records exactly
        existing_schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("value", pa.float64()),
            ]
        )
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)

            # Should not raise even in error mode
            await writer._check_schema_drift("test.table", valid_records, "error")

    @pytest.mark.asyncio
    async def test_schema_drift_skipped_for_new_table(self, valid_records, noop_logger):
        """Test schema drift check is skipped for new tables."""
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            side_effect=DeltaTableNotFoundError("Not found"),
        ):
            writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)

            # Should not raise for new table
            await writer._check_schema_drift("test.table", valid_records, "error")

    @pytest.mark.asyncio
    async def test_schema_drift_skipped_for_empty_records(self, noop_logger):
        """Test schema drift check is skipped for empty records."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        existing_schema = pa.schema([pa.field("entity_id", pa.string())])
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)

            # Should not raise for empty records
            await writer._check_schema_drift("test.table", [], "error")

    @pytest.mark.asyncio
    async def test_schema_drift_error_mode(self, valid_records, noop_logger):
        """Test schema drift error mode raises SchemaEvolutionError via write_silver.

        Acceptance criterion for M4: Schema Drift Handling.
        When on_schema_mismatch='error' is set and schema drift is detected,
        write_silver must raise SchemaEvolutionError before writing.
        """
        import pyarrow as pa

        from bioetl.domain.exceptions import SchemaEvolutionError
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        # Schema for incoming records
        incoming_schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("value", pa.float64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )

        # Existing table has a different schema (missing 'value' field)
        existing_table_schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )
        mock_delta_schema = MagicMock()
        mock_delta_schema.to_arrow.return_value = existing_table_schema

        mock_table = MagicMock()
        mock_table.schema.return_value = mock_delta_schema

        with patch(
            "bioetl.infrastructure.storage.base_delta_writer.DeltaTable",
            return_value=mock_table,
        ):
            writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)

            # write_silver with on_schema_mismatch="error" should raise
            with pytest.raises(SchemaEvolutionError) as exc_info:
                await writer.write_silver(
                    table_name="test.table",
                    records=valid_records,
                    primary_keys=["entity_id"],
                    schema=incoming_schema,
                    mode="merge",
                    on_schema_mismatch="error",
                )

            # Verify error details
            assert "value" in exc_info.value.new_fields
            assert exc_info.value.table == "test.table"
