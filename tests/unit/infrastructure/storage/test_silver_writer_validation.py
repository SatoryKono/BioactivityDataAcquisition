"""Unit tests for SilverWriter Silver Pandera validation.

Tests for the integration of PanderaSilverValidator with SilverWriter.
"""

from __future__ import annotations

import asyncio
import sys
import warnings
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Pandera has compatibility issues with Python 3.14
PYTHON_314 = sys.version_info >= (3, 14)

from bioetl.domain.exceptions import SchemaViolationError
from bioetl.application.services.lineage import MetadataCoordinator
from bioetl.domain.types import RunID, RunType
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.medallion import SilverWriteMode, WriteMode
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.validation.pandera_validator import (
    NoOpValidator,
    PanderaSilverValidator,
)
from tests.unit.infrastructure.storage.silver_writer._test_support import (
    assert_standard_silver_write_succeeds,
    make_silver_writer,
    silver_table_path,
    write_standard_silver,
)
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite


def _build_pandera_validator(
    *, min_value: float | None = None
) -> PanderaSilverValidator:
    """Create a simple validator for ``entity_id``/``value`` test records."""
    import pandera as pa

    value_kwargs = {"checks": pa.Check.ge(min_value)} if min_value is not None else {}
    return PanderaSilverValidator(
        schema=pa.DataFrameSchema(
            {
                "entity_id": pa.Column(str),
                "value": pa.Column(float, **value_kwargs),
            }
        )
    )


def _build_validation_writer(
    *,
    logger: object,
    validator: PanderaSilverValidator | NoOpValidator | None = None,
    metrics: object | None = None,
) -> object:
    """Create ``SilverWriter`` with the standard validation-oriented defaults."""
    return make_silver_writer(
        logger=logger,
        runtime_request=SilverWriterRuntimeServicesRequest(
            silver_validator=validator,
            metrics=metrics,
        ),
    )


def _sample_prepare_payload_records() -> list[dict[str, str]]:
    """Return the canonical minimal record batch for payload preparation tests."""
    return [
        {
            "entity_id": "CHEMBL123",
            "_run_id": "uuid-123",
            "_run_type": "incremental",
            "_source_batch_id": "batch-456",
            "_ingestion_ts": "2025-01-15T12:00:00Z",
        }
    ]


def _sample_prepare_payload_schema():
    """Return the canonical schema used by payload preparation tests."""
    import pyarrow as pa

    return pa.schema(
        [
            pa.field("entity_id", pa.string()),
            pa.field("_run_id", pa.string()),
            pa.field("_run_type", pa.string()),
            pa.field("_source_batch_id", pa.string()),
            pa.field("_ingestion_ts", pa.string()),
        ]
    )


def _sample_prepare_payload_fixture():
    """Build the repeated records/schema/arrow triple for payload preparation."""
    import pyarrow as pa

    records = _sample_prepare_payload_records()
    schema = _sample_prepare_payload_schema()
    expected_table = pa.Table.from_pylist(records, schema=schema)
    return records, schema, expected_table


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
        writer = make_silver_writer(logger=noop_logger)
        assert isinstance(writer._silver_validator, NoOpValidator)

    def test_init_with_custom_validator(self, noop_logger):
        """Test SilverWriter accepts custom SilverValidatorPort."""
        custom_validator = PanderaSilverValidator()
        writer = _build_validation_writer(
            logger=noop_logger,
            validator=custom_validator,
        )
        assert writer._silver_validator is custom_validator

    def test_init_with_pandera_schema_validator(self, noop_logger):
        """Test SilverWriter with PanderaSilverValidator with schema."""
        validator = _build_pandera_validator()
        writer = _build_validation_writer(logger=noop_logger, validator=validator)
        assert writer._silver_validator is validator


@pytest.mark.unit
class TestSilverWriterValidateSilverPandera:
    """Tests for _validate_silver_pandera method."""

    def test_validate_silver_pandera_with_noop_validator(self, noop_logger):
        """Test _validate_silver_pandera with NoOp validator passes."""
        writer = _build_validation_writer(
            logger=noop_logger,
            validator=NoOpValidator(),
        )
        records = [{"entity_id": "CHEMBL123", "value": 5.5}]
        # Should not raise
        writer._validate_silver_pandera(records, "test.table")

    def test_validate_silver_pandera_with_valid_records(self, noop_logger):
        """Test _validate_silver_pandera passes with valid records."""
        writer = _build_validation_writer(
            logger=noop_logger,
            validator=_build_pandera_validator(),
        )
        records = [{"entity_id": "CHEMBL123", "value": 5.5}]
        # Should not raise
        writer._validate_silver_pandera(records, "test.table")

    @pytest.mark.skipif(
        PYTHON_314,
        reason="Pandera 0.26.1 has compatibility issues with Python 3.14",
    )
    def test_validate_silver_pandera_accepts_target_records_without_removed_fields(
        self, noop_logger
    ):
        """chembl.target should validate without removed legacy contract fields."""
        writer = _build_validation_writer(
            logger=noop_logger,
            validator=PanderaSilverValidator(schema=TargetSchema.to_schema()),
        )
        records = [
            {
                "entity_id": "chembl_target:CHEMBL1",
                "content_hash": "a" * 64,
                "_run_id": "run-1",
                "_run_type": "backfill",
                "_source_batch_id": "batch-1",
                "_ingestion_ts": "2026-05-11T14:55:44Z",
                "_index": 0,
                "_dq_warn": False,
                "_dq_error": False,
                "target_id": "CHEMBL1",
                "target_type": "SINGLE PROTEIN",
                "pref_name": "Target one",
                "organism": "Homo sapiens",
                "species_group_flag": False,
            },
            {
                "entity_id": "chembl_target:CHEMBL2",
                "content_hash": "b" * 64,
                "_run_id": "run-1",
                "_run_type": "backfill",
                "_source_batch_id": "batch-1",
                "_ingestion_ts": "2026-05-11T14:55:45Z",
                "_index": 1,
                "_dq_warn": False,
                "_dq_error": False,
                "target_id": "CHEMBL2",
                "target_type": "SINGLE PROTEIN",
                "pref_name": "Target two",
                "organism": "Homo sapiens",
                "species_group_flag": False,
            },
        ]

        writer._validate_silver_pandera(records, "chembl.target")

    @pytest.mark.skipif(
        PYTHON_314,
        reason="Pandera 0.26.1 has compatibility issues with Python 3.14",
    )
    def test_validate_silver_pandera_with_invalid_records_raises(self, noop_logger):
        """Test _validate_silver_pandera raises SchemaViolationError for invalid records."""
        writer = _build_validation_writer(
            logger=noop_logger,
            validator=_build_pandera_validator(min_value=0),
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
        mock_logger = MagicMock()
        writer = _build_validation_writer(
            logger=mock_logger,
            validator=_build_pandera_validator(min_value=0),
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
        mock_metrics = MagicMock()
        writer = _build_validation_writer(
            logger=NoOpLogger(),
            validator=_build_pandera_validator(min_value=0),
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
        mock_metrics = MagicMock()
        writer = _build_validation_writer(
            logger=NoOpLogger(),
            validator=_build_pandera_validator(min_value=0),
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
        writer = _build_validation_writer(
            logger=noop_logger,
            validator=_build_pandera_validator(min_value=100),
        )

        with pytest.raises(SchemaViolationError) as exc_info:
            await write_standard_silver(
                writer,
                records=valid_records,
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
        writer = _build_validation_writer(
            logger=noop_logger,
            validator=_build_pandera_validator(min_value=0),
        )
        await assert_standard_silver_write_succeeds(
            writer,
            records=valid_records,
            mode="merge",
        )

    @pytest.mark.asyncio
    async def test_write_silver_noop_validator_allows_write(
        self, valid_records, noop_logger
    ):
        """Test write_silver with NoOp validator allows write without Pandera."""
        writer = make_silver_writer(logger=noop_logger)
        await assert_standard_silver_write_succeeds(
            writer,
            records=valid_records,
            mode="merge",
        )


@pytest.mark.unit
class TestSilverWriterPreparePayloadExecutor:
    """Tests for executor offload in Silver payload preparation."""

    @pytest.mark.asyncio
    async def test_prepare_payload_uses_to_thread(self, noop_logger) -> None:
        """Sync validation should be offloaded from the event loop."""
        from bioetl.infrastructure.storage.silver.validation_mixin import (
            _ValidatedSilverWriteContext,
        )
        from bioetl.domain.medallion import WriteModePolicy

        writer = make_silver_writer(logger=noop_logger)
        records, schema, expected_table = _sample_prepare_payload_fixture()

        # Create validation operations service with proper mocking
        from bioetl.infrastructure.storage.silver.operations.validation_operations import (
            SilverValidationOperations,
        )

        # Create a minimal validation operations instance
        validation_ops = SilverValidationOperations(
            logger=noop_logger,
            _write_policy=WriteModePolicy(),
            _metrics=None,
            _silver_validator=None,  # type: ignore
            _get_table_schema=AsyncMock(return_value=None),  # type: ignore
            _resolve_table_path=silver_table_path,
            _prepare_arrow_data=lambda *args, **kwargs: expected_table,
            _validate_write_mode=lambda x: SilverWriteMode.APPEND,
            _deduplicate_by_primary_keys=lambda records, keys: records,
            _to_policy_write_mode=lambda x: WriteMode.APPEND,
            _validate_key_nullability=lambda *args, **kwargs: None,
        )

        # Set up the writer with validation operations
        writer._validation = validation_ops
        writer._check_schema_drift = AsyncMock(return_value=None)  # type: ignore[method-assign]

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
                "bioetl.infrastructure.storage.silver.operations.validation_operations.asyncio.to_thread",
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
        # Normalize paths for comparison to handle different separators across platforms
        expected_path = str(Path(silver_table_path("test.table")).resolve())
        actual_path = str(Path(payload.table_path).resolve())
        assert expected_path == actual_path, (
            f"Expected {expected_path}, got {actual_path}"
        )
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
        from bioetl.infrastructure.storage.silver.validation_mixin import (
            _ValidatedSilverWriteContext,
        )

        writer = make_silver_writer(logger=noop_logger)
        records, schema, expected_table = _sample_prepare_payload_fixture()
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
        from bioetl.infrastructure.storage.silver.validation_mixin import (
            _SilverWritePreparationRequest,
            _ValidatedSilverWriteContext,
        )

        writer = make_silver_writer(logger=noop_logger)
        records, schema, expected_table = _sample_prepare_payload_fixture()
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

    @pytest.mark.asyncio
    async def test_prepare_payload_fails_closed_for_strict_merge_without_content_hash(
        self, noop_logger
    ) -> None:
        from bioetl.infrastructure.storage.silver.validation_mixin import (
            _ValidatedSilverWriteContext,
        )

        records, schema, expected_table = _sample_prepare_payload_fixture()
        context = RunContext.create(
            run_id=RunID(deterministic_uuid_from_callsite("strict-silver-merge")),
            run_type=RunType.INCREMENTAL,
            started_at=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
            provider="chembl",
            entity="activity",
            required_persistence_profile="replay_ready",
        )
        writer = make_silver_writer(
            logger=noop_logger,
            runtime_request=SilverWriterRuntimeServicesRequest(
                metadata_coordinator=MetadataCoordinator(context),
            ),
        )
        writer._check_schema_drift = AsyncMock(return_value=None)  # type: ignore[method-assign]

        with patch.object(
            writer,
            "_sync_validate_and_build_arrow",
            return_value=_ValidatedSilverWriteContext(
                records=records,
                validated_mode=SilverWriteMode.MERGE,
                arrow_data=expected_table,
            ),
        ):
            with pytest.raises(
                ValueError,
                match="Replay-capable Silver merge requires content_hash",
            ):
                await writer._prepare_silver_write_payload(
                    table_name="test.table",
                    records=records,
                    primary_keys=["entity_id"],
                    schema=schema,
                    mode="merge",
                    on_schema_mismatch="ignore",
                    column_order=None,
                    partition_cols=None,
                    key_nullability_rules=None,
                )
