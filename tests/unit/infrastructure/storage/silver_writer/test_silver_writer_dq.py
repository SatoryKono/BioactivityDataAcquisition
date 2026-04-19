"""SilverWriter write-policy (DQ-governance) unit tests."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

TEST_ROOT = Path(tempfile.mkdtemp(prefix="bioetl-silver-writer-dq-"))
SILVER_BASE_PATH = TEST_ROOT / "silver"


class TestSilverWriterWriteModePolicy:
    """Tests for WriteModePolicy integration in SilverWriter."""

    def test_init_with_default_policy(self, noop_logger):
        """Test SilverWriter creates default WriteModePolicy when not provided."""
        from bioetl.domain.medallion import WriteModePolicy
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)
        assert isinstance(writer._write_policy, WriteModePolicy)

    def test_init_with_custom_policy(self, noop_logger):
        """Test SilverWriter accepts custom WriteModePolicy."""
        from bioetl.domain.medallion import WriteModePolicy
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        custom_policy = WriteModePolicy()
        writer = SilverWriter(
            base_path=str(SILVER_BASE_PATH),
            logger=noop_logger,
            write_policy=custom_policy,
        )
        assert writer._write_policy is custom_policy

    def test_init_with_metrics_port(self, noop_logger):
        """Test SilverWriter accepts optional MetricsPort."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_metrics = MagicMock()
        writer = SilverWriter(
            base_path=str(SILVER_BASE_PATH),
            logger=noop_logger,
            metrics=mock_metrics,
        )
        assert writer._metrics is mock_metrics

    def test_to_policy_write_mode_merge(self, noop_logger):
        """Test MERGE mode maps correctly."""
        from bioetl.domain.medallion import WriteMode
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)
        result = writer._to_policy_write_mode(SilverWriteMode.MERGE)
        assert result == WriteMode.MERGE

    def test_to_policy_write_mode_append(self, noop_logger):
        """Test APPEND mode maps correctly."""
        from bioetl.domain.medallion import WriteMode
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)
        result = writer._to_policy_write_mode(SilverWriteMode.APPEND)
        assert result == WriteMode.APPEND

    def test_to_policy_write_mode_delete_maps_to_overwrite(self, noop_logger):
        """Test DELETE mode maps to OVERWRITE (critical for policy enforcement)."""
        from bioetl.domain.medallion import WriteMode
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)
        result = writer._to_policy_write_mode(SilverWriteMode.DELETE)
        assert result == WriteMode.OVERWRITE

    def test_enforce_write_policy_allows_merge(self, noop_logger):
        """Test policy enforcement allows MERGE mode for Silver."""
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)
        # Should not raise
        writer._enforce_write_policy(SilverWriteMode.MERGE, "test.table")

    def test_enforce_write_policy_allows_append(self, noop_logger):
        """Test policy enforcement allows APPEND mode for Silver."""
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)
        # Should not raise
        writer._enforce_write_policy(SilverWriteMode.APPEND, "test.table")

    def test_enforce_write_policy_rejects_delete(self, noop_logger):
        """Test policy enforcement rejects DELETE mode for Silver (maps to OVERWRITE)."""
        from bioetl.domain.exceptions import PolicyViolationError
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)
        with pytest.raises(PolicyViolationError) as exc_info:
            writer._enforce_write_policy(SilverWriteMode.DELETE, "test.table")
        assert "silver does not allow overwrite" in str(exc_info.value)

    def test_enforce_write_policy_increments_metric_on_violation(self, noop_logger):
        """Test policy violation increments policy_violations_total metric."""
        from bioetl.domain.exceptions import PolicyViolationError
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        mock_metrics = MagicMock()
        writer = SilverWriter(
            base_path=str(SILVER_BASE_PATH),
            logger=noop_logger,
            metrics=mock_metrics,
        )

        with pytest.raises(PolicyViolationError):
            writer._enforce_write_policy(SilverWriteMode.DELETE, "test.table")

        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_policy_violations_total",
            1,
            {"layer": "silver", "mode": "overwrite"},
        )

    def test_enforce_write_policy_logs_error_on_violation(self, noop_logger):
        """Test policy violation logs error with context."""
        from bioetl.domain.exceptions import PolicyViolationError
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        mock_logger = MagicMock()
        writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=mock_logger)

        with pytest.raises(PolicyViolationError):
            writer._enforce_write_policy(SilverWriteMode.DELETE, "test.table")

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args[0][0] == "Write mode policy violation"
        assert call_args[1]["layer"] == "silver"
        assert call_args[1]["mode"] == "delete"
        assert call_args[1]["policy_mode"] == "overwrite"
        assert call_args[1]["table"] == "test.table"

    @pytest.mark.asyncio
    async def test_write_silver_delete_mode_raises_policy_violation(
        self, valid_records, noop_logger
    ):
        """Test write_silver with delete mode raises PolicyViolationError.

        This is the critical acceptance criterion: write_silver(mode="delete")
        must raise PolicyViolationError because DELETE maps to OVERWRITE
        which is not allowed for Silver layer.
        """
        import pyarrow as pa

        from bioetl.domain.exceptions import PolicyViolationError
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("value", pa.float64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )

        writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)

        with pytest.raises(PolicyViolationError) as exc_info:
            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="delete",
            )
        assert "silver does not allow overwrite" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_write_silver_merge_mode_passes_policy(
        self, valid_records, noop_logger
    ):
        """Test write_silver with merge mode passes policy validation."""
        import pyarrow as pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("value", pa.float64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )

        with (
            patch(
                "bioetl.infrastructure.storage.silver_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch(
                "bioetl.infrastructure.storage.silver_writer.write_deltalake"
            ) as mock_write,
        ):
            writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)

            # Should not raise PolicyViolationError
            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="merge",
            )

            # Verify write was called (policy passed)
            mock_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_silver_append_mode_passes_policy(
        self, valid_records, noop_logger
    ):
        """Test write_silver with append mode passes policy validation."""
        import pyarrow as pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("value", pa.float64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )

        with (
            patch(
                "bioetl.infrastructure.storage.silver_writer.DeltaTable",
                side_effect=DeltaTableNotFoundError("Not found"),
            ),
            patch(
                "bioetl.infrastructure.storage.silver_writer.write_deltalake"
            ) as mock_write,
        ):
            writer = SilverWriter(base_path=str(SILVER_BASE_PATH), logger=noop_logger)

            # Should not raise PolicyViolationError
            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="append",
            )

            # Verify write was called (policy passed)
            mock_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_silver_delete_mode_increments_metric(
        self, valid_records, noop_logger
    ):
        """Test write_silver with delete mode increments policy_violations_total."""
        import pyarrow as pa

        from bioetl.domain.exceptions import PolicyViolationError
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("value", pa.float64()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )

        mock_metrics = MagicMock()
        writer = SilverWriter(
            base_path=str(SILVER_BASE_PATH),
            logger=noop_logger,
            metrics=mock_metrics,
        )

        with pytest.raises(PolicyViolationError):
            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="delete",
            )

        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_policy_violations_total",
            1,
            {"layer": "silver", "mode": "overwrite"},
        )
