"""Unit tests for SilverWriter Silver Pandera validation.

Tests for the integration of PanderaSilverValidator with SilverWriter.
"""

from __future__ import annotations

import warnings
from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.exceptions import SchemaViolationError
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.validation.pandera_validator import (
    NoOpSilverValidator,
    PanderaSilverValidator,
)


@pytest.fixture(autouse=True)
def suppress_pandera_future_warnings():
    """Suppress Pandera import FutureWarnings during tests."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=FutureWarning, module="pandera")
        yield


@pytest.fixture
def noop_logger():
    """Provide a NoOpLogger for tests."""
    return NoOpLogger()


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
        """Test SilverWriter creates NoOpSilverValidator when not provided."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(
            base_path="/tmp/silver", logger=noop_logger
        )
        assert isinstance(writer._silver_validator, NoOpSilverValidator)

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
            silver_validator=NoOpSilverValidator(),

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
            "silver_validation_failures_total",
            1,
            {"table": "test.table"},
        )


@pytest.mark.unit
class TestSilverWriterWriteSilverWithPanderaValidation:
    """Tests for write_silver with Pandera validation integration."""

    @pytest.mark.asyncio
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
