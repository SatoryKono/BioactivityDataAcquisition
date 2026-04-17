"""Unit tests for SilverWriter Silver Pandera validation.

Tests for the integration of PanderaSilverValidator with SilverWriter.
"""

from __future__ import annotations

import asyncio
import sys
import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Pandera has compatibility issues with Python 3.14
PYTHON_314 = sys.version_info >= (3, 14)

from bioetl.domain.exceptions import SchemaViolationError
from bioetl.domain.medallion import SilverWriteMode
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.validation.pandera_validator import (
    NoOpValidator,
    PanderaSilverValidator,
)


@pytest.fixture(autouse=True)
def suppress_pandera_future_warnings():
    """Suppress Pandera import FutureWarnings during tests."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning, module="pandera")
        yield


@pytest.fixture
def valid_records():
    """Create valid records with all required metadata."""
    return [
        {
            "entity_id": "CHEMBL123",
            "value": 5.5,
            "_run_id": "uuid-123",
            "_run_type": "incremental",
            "_source_batch_id": "batch-456",
            "_ingestion_ts": "2025-01-15T12:00:00Z",
        },
        {
            "entity_id": "CHEMBL456",
            "value": 7.2,
            "_run_id": "uuid-123",
            "_run_type": "incremental",
            "_source_batch_id": "batch-456",
            "_ingestion_ts": "2025-01-15T12:00:00Z",
        },
    ]


@pytest.mark.unit
class TestSilverWriterSilverValidatorInit:
    """Tests for SilverWriter initialization with Silver validator."""

    def test_init_with_default_validator(self, noop_logger):
        """Test SilverWriter creates NoOpValidator when not provided."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
        assert isinstance(writer._silver_validator, NoOpValidator)

    def test_init_with_custom_validator(self, noop_logger):
        """Test SilverWriter accepts custom SilverValidatorPort."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        custom_validator = PanderaSilverValidator()
        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            silver_validator=custom_validator,
        )
        assert writer._silver_validator is custom_validator

    def test_init_with_pandera_schema_validator(self, noop_logger):
        """Test SilverWriter with PanderaSilverValidator with schema."""
        import pandera as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        schema = pa.DataFrameSchema(
            {
                "entity_id": pa.Column(str),
                "value": pa.Column(float),
            }
        )
        validator = PanderaSilverValidator(schema=schema)
        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            silver_validator=validator,
        )
        assert writer._silver_validator is validator


@pytest.mark.unit
class TestSilverWriterValidateSilverPandera:
    """Tests for _validate_silver_pandera method."""

    def test_validate_silver_pandera_with_noop_validator(self, noop_logger):
        """Test _validate_silver_pandera with NoOp validator passes."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            silver_validator=NoOpValidator(),
        )
        records = [{"entity_id": "CHEMBL123", "value": 5.5}]
        # Should not raise
        writer._validate_silver_pandera(records, "test.table")

    def test_validate_silver_pandera_with_valid_records(self, noop_logger):
        """Test _validate_silver_pandera passes with valid records."""
        import pandera as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        schema = pa.DataFrameSchema(
            {
                "entity_id": pa.Column(str),
                "value": pa.Column(float),
            }
        )
        validator = PanderaSilverValidator(schema=schema)
        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            silver_validator=validator,
        )
        records = [{"entity_id": "CHEMBL123", "value": 5.5}]
        # Should not raise
        writer._validate_silver_pandera(records, "test.table")

    @pytest.mark.skipif(
        PYTHON_314,
        reason="Pandera 0.26.1 has compatibility issues with Python 3.14",
    )
    def test_validate_silver_pandera_with_invalid_records_raises(self, noop_logger):
        """Test _validate_silver_pandera raises SchemaViolationError for invalid records."""
        import pandera as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        schema = pa.DataFrameSchema(
            {
                "entity_id": pa.Column(str),
                "value": pa.Column(float, checks=pa.Check.ge(0)),
            }
        )
        validator = PanderaSilverValidator(schema=schema)
        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            silver_validator=validator,
        )
        records = [{"entity_id": "CHEMBL123", "value": -5.5}]  # Negative value fails

        with pytest.raises(SchemaViolationError) as exc_info:
            writer._validate_silver_pandera(records, "test.table")

        assert exc_info.value.table == "test.table"
        assert len(exc_info.value.errors) > 0

    @pytest.mark.skipif(
        PYTHON_314,
        reason="Pandera 0.26.1 has compatibility issues with Python 3.14",
    )
    def test_validate_silver_pandera_logs_error_on_failure(self):
        """Test _validate_silver_pandera logs error when validation fails."""
        import pandera as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        schema = pa.DataFrameSchema(
            {
                "entity_id": pa.Column(str),
                "value": pa.Column(float, checks=pa.Check.ge(0)),
            }
        )
        validator = PanderaSilverValidator(schema=schema)
        mock_logger = MagicMock()
        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=mock_logger,
            silver_validator=validator,
        )
        records = [{"entity_id": "CHEMBL123", "value": -5.5}]

        with pytest.raises(SchemaViolationError):
            writer._validate_silver_pandera(records, "test.table")

        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        assert call_args[0][0] == "Silver Pandera validation failed"
        assert call_args[1]["table"] == "test.table"

    @pytest.mark.skipif(
        PYTHON_314,
        reason="Pandera 0.26.1 has compatibility issues with Python 3.14",
    )
    def test_validate_silver_pandera_increments_metric_on_failure(self):
        """Test _validate_silver_pandera increments metric when validation fails."""
        import pandera as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        schema = pa.DataFrameSchema(
            {
                "entity_id": pa.Column(str),
                "value": pa.Column(float, checks=pa.Check.ge(0)),
            }
        )
        validator = PanderaSilverValidator(schema=schema)
        mock_metrics = MagicMock()
        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=NoOpLogger(),
            silver_validator=validator,
            metrics=mock_metrics,
        )
        records = [{"entity_id": "CHEMBL123", "value": -5.5}]

        with pytest.raises(SchemaViolationError):
            writer._validate_silver_pandera(records, "test.table")

        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_silver_validation_failures_total",
            1,
            {"table": "test.table", "pipeline": "test_table"},
        )

    @pytest.mark.skipif(
        PYTHON_314,
        reason="Pandera 0.26.1 has compatibility issues with Python 3.14",
    )
    def test_validate_silver_pandera_uses_pipeline_label_for_versioned_tables(self):
        """Validation failure metrics should expose canonical pipeline labels."""
        import pandera as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        schema = pa.DataFrameSchema(
            {
                "entity_id": pa.Column(str),
                "value": pa.Column(float, checks=pa.Check.ge(0)),
            }
        )
        validator = PanderaSilverValidator(schema=schema)
        mock_metrics = MagicMock()
        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=NoOpLogger(),
            silver_validator=validator,
            metrics=mock_metrics,
        )
        records = [{"entity_id": "CHEMBL123", "value": -5.5}]

        with pytest.raises(SchemaViolationError):
            writer._validate_silver_pandera(records, "chembl.activity__v1_0_0")

        mock_metrics.increment_counter.assert_called_once_with(
            "bioetl_silver_validation_failures_total",
            1,
            {
                "table": "chembl.activity__v1_0_0",
                "pipeline": "chembl_activity",
            },
        )


@pytest.mark.unit
class TestSilverWriterWriteSilverWithPanderaValidation:
    """Tests for write_silver with Pandera validation integration."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        PYTHON_314,
        reason="Pandera 0.26.1 has compatibility issues with Python 3.14",
    )
    async def test_write_silver_pandera_validation_fails(
        self, valid_records, noop_logger
    ):
        """Test write_silver raises SchemaViolationError when Pandera validation fails."""
        import pandera as pa
        import pyarrow as arrow_pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        # Schema that will fail: requires value >= 100
        pandera_schema = pa.DataFrameSchema(
            {
                "value": pa.Column(float, checks=pa.Check.ge(100)),
            }
        )
        validator = PanderaSilverValidator(schema=pandera_schema)

        arrow_schema = arrow_pa.schema(
            [
                arrow_pa.field("entity_id", arrow_pa.string()),
                arrow_pa.field("value", arrow_pa.float64()),
                arrow_pa.field("_run_id", arrow_pa.string()),
                arrow_pa.field("_run_type", arrow_pa.string()),
                arrow_pa.field("_source_batch_id", arrow_pa.string()),
                arrow_pa.field("_ingestion_ts", arrow_pa.string()),
            ]
        )

        writer = SilverWriter(
            base_path="/tmp/silver",
            logger=noop_logger,
            silver_validator=validator,
        )

        with pytest.raises(SchemaViolationError) as exc_info:
            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=arrow_schema,
                mode="merge",
            )

        assert exc_info.value.table == "test.table"

    @pytest.mark.asyncio
    @pytest.mark.skipif(
        PYTHON_314,
        reason="Pandera 0.26.1 has compatibility issues with Python 3.14",
    )
    async def test_write_silver_pandera_validation_passes(
        self, valid_records, noop_logger
    ):
        """Test write_silver proceeds when Pandera validation passes."""
        import pandera as pa
        import pyarrow as arrow_pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        # Schema that will pass: value >= 0
        pandera_schema = pa.DataFrameSchema(
            {
                "value": pa.Column(float, checks=pa.Check.ge(0)),
            }
        )
        validator = PanderaSilverValidator(schema=pandera_schema)

        arrow_schema = arrow_pa.schema(
            [
                arrow_pa.field("entity_id", arrow_pa.string()),
                arrow_pa.field("value", arrow_pa.float64()),
                arrow_pa.field("_run_id", arrow_pa.string()),
                arrow_pa.field("_run_type", arrow_pa.string()),
                arrow_pa.field("_source_batch_id", arrow_pa.string()),
                arrow_pa.field("_ingestion_ts", arrow_pa.string()),
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
            writer = SilverWriter(
                base_path="/tmp/silver",
                logger=noop_logger,
                silver_validator=validator,
            )

            # Should not raise
            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=arrow_schema,
                mode="merge",
            )

            # Verify write was called (validation passed)
            mock_write.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_silver_noop_validator_allows_write(
        self, valid_records, noop_logger
    ):
        """Test write_silver with NoOp validator allows write without Pandera."""
        import pyarrow as arrow_pa
        from deltalake.exceptions import TableNotFoundError as DeltaTableNotFoundError

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        arrow_schema = arrow_pa.schema(
            [
                arrow_pa.field("entity_id", arrow_pa.string()),
                arrow_pa.field("value", arrow_pa.float64()),
                arrow_pa.field("_run_id", arrow_pa.string()),
                arrow_pa.field("_run_type", arrow_pa.string()),
                arrow_pa.field("_source_batch_id", arrow_pa.string()),
                arrow_pa.field("_ingestion_ts", arrow_pa.string()),
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
            # Default NoOp validator
            writer = SilverWriter(
                base_path="/tmp/silver",
                logger=noop_logger,
            )

            # Should not raise
            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=arrow_schema,
                mode="merge",
            )

            # Verify write was called
            mock_write.assert_called_once()


@pytest.mark.unit
class TestSilverWriterPreparePayloadExecutor:
    """Tests for executor offload in Silver payload preparation."""

    @pytest.mark.asyncio
    async def test_prepare_payload_uses_to_thread(self, noop_logger) -> None:
        """Sync validation should be offloaded from the event loop."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter
        from bioetl.infrastructure.storage.silver.validation_mixin import (
            _ValidatedSilverWriteContext,
        )
        from bioetl.infrastructure.storage.silver.operations.validation_operations import (
            _PreparedSilverWritePayload,
        )
        from bioetl.domain.medallion import WriteModePolicy

        writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
        records = [
            {
                "entity_id": "CHEMBL123",
                "_run_id": "uuid-123",
                "_run_type": "incremental",
                "_source_batch_id": "batch-456",
                "_ingestion_ts": "2025-01-15T12:00:00Z",
            }
        ]
        schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )
        expected_table = pa.Table.from_pylist(records, schema=schema)
        
        # Create validation operations service with proper mocking
        from bioetl.infrastructure.storage.silver.operations.validation_operations import SilverValidationOperations
        from bioetl.infrastructure.storage.silver.pipeline_helpers import execute_silver_write_pipeline
        
        # Create a minimal validation operations instance
        validation_ops = SilverValidationOperations(
            logger=noop_logger,
            _write_policy=WriteModePolicy(),
            _metrics=None,
            _silver_validator=None,  # type: ignore
            _get_table_schema=AsyncMock(return_value=None),  # type: ignore
            _resolve_table_path=lambda x: f"/tmp/silver/{x.replace('.', '/')}",
            _prepare_arrow_data=lambda *args, **kwargs: expected_table,
            _validate_write_mode=lambda x: SilverWriteMode.APPEND,
            _deduplicate_by_primary_keys=lambda records, keys: records,
            _to_policy_write_mode=lambda x: WriteMode.APPEND,
            _validate_key_nullability=lambda *args, **kwargs: None,
        )
        
        # Set up the writer with validation operations
        writer._validation = validation_ops

        with (
            patch.object(
                validation_ops,
                "_sync_validate_and_build_arrow",
                return_value=_ValidatedSilverWriteContext(
                    records=records,
                    validated_mode=SilverWriteMode.APPEND,
                    arrow_data=expected_table,
                ),
            ) as mock_sync,
            patch(
                "bioetl.infrastructure.storage.silver.validation_mixin.asyncio.to_thread",
                wraps=asyncio.to_thread,
            ) as mock_to_thread,
        ):
            payload = await validation_ops._prepare_silver_write_payload(
                table_name="test.table",
                records=records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="append",
                on_schema_mismatch="ignore",
                column_order=None,
                partition_cols=None,
                key_nullability_rules=None,
            )

        assert payload.records == records
        assert payload.validated_mode is SilverWriteMode.APPEND
        assert payload.table_path == "/tmp/silver/test/table"
        assert payload.arrow_data.equals(expected_table)
        mock_sync.assert_called_once()
        writer._check_schema_drift.assert_awaited_once_with(
            "test.table",
            records,
            "ignore",
        )
        assert mock_to_thread.call_count == 1

    @pytest.mark.asyncio
    async def test_prepare_payload_checks_schema_drift_after_executor(
        self, noop_logger
    ) -> None:
        """Schema drift check should happen after sync payload building completes."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter
        from bioetl.infrastructure.storage.silver.validation_mixin import (
            _ValidatedSilverWriteContext,
        )

        writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
        records = [
            {
                "entity_id": "CHEMBL123",
                "_run_id": "uuid-123",
                "_run_type": "incremental",
                "_source_batch_id": "batch-456",
                "_ingestion_ts": "2025-01-15T12:00:00Z",
            }
        ]
        schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )
        expected_table = pa.Table.from_pylist(records, schema=schema)
        call_order: list[str] = []

        def sync_stage(
            *_: object,
            **__: object,
        ) -> _ValidatedSilverWriteContext:
            call_order.append("sync")
            return _ValidatedSilverWriteContext(
                records=records,
                validated_mode=SilverWriteMode.APPEND,
                arrow_data=expected_table,
            )

        async def schema_stage(*_: object) -> None:
            await asyncio.sleep(0)
            call_order.append("schema")

        writer._check_schema_drift = AsyncMock(side_effect=schema_stage)  # type: ignore[method-assign]

        with patch.object(
            writer,
            "_sync_validate_and_build_arrow",
            side_effect=sync_stage,
        ):
            await writer._prepare_silver_write_payload(
                table_name="test.table",
                records=records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="append",
                on_schema_mismatch="ignore",
                column_order=None,
                partition_cols=None,
                key_nullability_rules=None,
            )

        assert call_order == ["sync", "schema"]

    @pytest.mark.asyncio
    async def test_prepare_payload_builds_named_request_for_sync_stage(
        self, noop_logger
    ) -> None:
        """Silver payload preparation should pass one named request into sync stage."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter
        from bioetl.infrastructure.storage.silver.validation_mixin import (
            _SilverWritePreparationRequest,
            _ValidatedSilverWriteContext,
        )

        writer = SilverWriter(base_path="/tmp/silver", logger=noop_logger)
        records = [
            {
                "entity_id": "CHEMBL123",
                "_run_id": "uuid-123",
                "_run_type": "incremental",
                "_source_batch_id": "batch-456",
                "_ingestion_ts": "2025-01-15T12:00:00Z",
            }
        ]
        schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )
        expected_table = pa.Table.from_pylist(records, schema=schema)
        captured_request: _SilverWritePreparationRequest | None = None

        def sync_stage(
            request: _SilverWritePreparationRequest,
        ) -> _ValidatedSilverWriteContext:
            nonlocal captured_request
            captured_request = request
            return _ValidatedSilverWriteContext(
                records=records,
                validated_mode=SilverWriteMode.APPEND,
                arrow_data=expected_table,
            )

        writer._check_schema_drift = AsyncMock(return_value=None)  # type: ignore[method-assign]

        with patch.object(
            writer,
            "_sync_validate_and_build_arrow",
            side_effect=sync_stage,
        ):
            await writer._prepare_silver_write_payload(
                table_name="test.table",
                records=records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="append",
                on_schema_mismatch="ignore",
                column_order=None,
                partition_cols=["entity_id"],
                key_nullability_rules=None,
            )

        assert isinstance(captured_request, _SilverWritePreparationRequest)
        assert captured_request.table_name == "test.table"
        assert captured_request.records == records
        assert captured_request.primary_keys == ["entity_id"]
        assert captured_request.schema == schema
        assert captured_request.mode == "append"
        assert captured_request.partition_cols == ["entity_id"]
