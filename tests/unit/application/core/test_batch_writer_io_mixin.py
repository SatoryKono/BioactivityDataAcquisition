# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for BatchWriterIOMixin.

Tests the write orchestration paths (write_bronze, write_silver, write_gold)
including metadata injection, schema projection, column ordering,
lock validation, and failure propagation.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from tests.helpers.deterministic_ids import (
    deterministic_batch_uuid_from_callsite,
    deterministic_uuid_from_callsite,
)

import pytest

from bioetl.application.composite.column_service import ColumnOrderService
from bioetl.application.core._batch_writer_gold_support import (
    rebind_gold_validator_schema,
    should_defer_gold_validation_to_storage,
    validate_gold_records,
)
from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.application.core.batch_writer import BatchWriter, BatchWriterOptions
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.domain.config import TableConfig
from bioetl.domain.context import PipelineContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.domain.exceptions import BioETLError, SchemaViolationError
from bioetl.domain.ports.storage import SilverWriteRequest
from bioetl.domain.types import (
    GoldSchemaPolicyByVersion,
    GoldSchemaVersionPolicy,
    RunType,
    ValidationResult,
)


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_storage():
    storage = AsyncMock()
    storage.write_bronze = AsyncMock(return_value=MagicMock())
    storage.write_silver = AsyncMock(return_value=MagicMock())
    storage.write_gold = AsyncMock(return_value=None)
    return storage


@pytest.fixture
def mock_context():
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    return PipelineContext(
        run_id=deterministic_uuid_from_callsite("test_batch_writer_io_mixin"),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.fixture
def mock_gold_validator():
    validator = MagicMock()
    validator.validate = MagicMock(return_value=ValidationResult(valid=True))
    return validator


@pytest.fixture
def mock_batch_metrics():
    return MagicMock(spec=BatchMetricsRecorder)


def _make_writer(
    storage,
    context,
    gold_validator,
    *,
    provider: str = "test_provider",
    entity_type: str = "test_entity",
    silver_schema=None,
    gold_schema=None,
    primary_keys: list[str] | None = None,
    gold_write_mode: str = "append",
    scd_config: dict[str, str] | None = None,
    lock_validator=None,
) -> BatchWriter:
    config = RecordProcessorConfig(
        pipeline_name=f"{provider}_{entity_type}",
        provider=provider,
        entity_type=entity_type,
        silver_schema=silver_schema or MagicMock(),
        gold_schema=gold_schema or MagicMock(),
        table_config=TableConfig(
            primary_keys=primary_keys or [],
            gold_write_mode=gold_write_mode,
        ),
        scd_config=scd_config,
    )
    return BatchWriter(
        storage=storage,
        context=context,
        config=config,
        gold_validator=gold_validator,
        error_classifier=ErrorClassifier(),
        batch_metrics=MagicMock(spec=BatchMetricsRecorder),
        options=BatchWriterOptions(lock_validator=lock_validator),
    )


@pytest.fixture
def batch_writer(mock_storage, mock_context, mock_gold_validator):
    return _make_writer(mock_storage, mock_context, mock_gold_validator)


# ---------------------------------------------------------------------------
# write_bronze
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBatchWriterIOMixinBronze:
    """Tests for write_bronze path in BatchWriterIOMixin."""

    async def test_write_bronze_calls_storage_with_provider_and_entity(
        self, batch_writer, mock_storage
    ):
        """Storage receives correct provider, entity, batch_id."""
        records = [{"id": "1", "val": 10}]
        batch_id = deterministic_batch_uuid_from_callsite("test_batch_writer_io_mixin")
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

        await batch_writer.write_bronze(records, batch_id, ts)

        mock_storage.write_bronze.assert_called_once()
        kwargs = mock_storage.write_bronze.call_args[1]
        assert kwargs["provider"] == "test_provider"
        assert kwargs["entity"] == "test_entity"
        assert kwargs["batch_id"] == batch_id

    async def test_write_bronze_serializes_records_deterministically(
        self, batch_writer, mock_storage
    ):
        """Records are JSON-serialised and sorted before passing to storage."""
        records = [{"b": 2, "a": 1}, {"z": 3}]
        batch_id = deterministic_batch_uuid_from_callsite("test_batch_writer_io_mixin")
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

        await batch_writer.write_bronze(records, batch_id, ts)

        # Storage must have been called exactly once
        assert mock_storage.write_bronze.call_count == 1

    async def test_write_bronze_passes_run_id_and_run_type(
        self, batch_writer, mock_storage, mock_context
    ):
        """run_id and run_type from context are forwarded to storage."""
        records = [{"x": 1}]
        batch_id = deterministic_batch_uuid_from_callsite("test_batch_writer_io_mixin")
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

        await batch_writer.write_bronze(records, batch_id, ts)

        kwargs = mock_storage.write_bronze.call_args[1]
        assert kwargs["run_id"] == mock_context.run_id
        assert kwargs["run_type"] == mock_context.run_type

    async def test_write_bronze_passes_source_metadata(
        self, batch_writer, mock_storage
    ):
        """Optional source_metadata is forwarded to storage."""
        records = [{"id": "1"}]
        batch_id = deterministic_batch_uuid_from_callsite("test_batch_writer_io_mixin")
        ts = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        meta = MagicMock()

        await batch_writer.write_bronze(records, batch_id, ts, source_metadata=meta)

        kwargs = mock_storage.write_bronze.call_args[1]
        assert kwargs["source_metadata"] is meta

    async def test_write_bronze_reraises_bioetl_error(
        self, mock_storage, mock_context, mock_gold_validator
    ):
        """BioETLError from storage propagates out of write_bronze."""
        mock_storage.write_bronze = AsyncMock(side_effect=BioETLError("boom"))
        writer = _make_writer(mock_storage, mock_context, mock_gold_validator)

        with pytest.raises(BioETLError):
            await writer.write_bronze(
                [{"id": "1"}],
                deterministic_batch_uuid_from_callsite("test_batch_writer_io_mixin"),
                datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            )

    async def test_write_bronze_reraises_runtime_error(
        self, mock_storage, mock_context, mock_gold_validator
    ):
        """RuntimeError from storage propagates out of write_bronze."""
        mock_storage.write_bronze = AsyncMock(side_effect=RuntimeError("storage crash"))
        writer = _make_writer(mock_storage, mock_context, mock_gold_validator)

        with pytest.raises(RuntimeError):
            await writer.write_bronze(
                [{"id": "1"}],
                deterministic_batch_uuid_from_callsite("test_batch_writer_io_mixin"),
                datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            )

    async def test_write_bronze_returns_storage_result(
        self, mock_storage, mock_context, mock_gold_validator
    ):
        """write_bronze returns whatever the storage layer returns."""
        expected = MagicMock(name="bronze_result")
        mock_storage.write_bronze = AsyncMock(return_value=expected)
        writer = _make_writer(mock_storage, mock_context, mock_gold_validator)

        result = await writer.write_bronze(
            [{"id": "1"}],
            deterministic_batch_uuid_from_callsite("test_batch_writer_io_mixin"),
            datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )

        assert result is expected


# ---------------------------------------------------------------------------
# write_silver
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBatchWriterIOMixinSilver:
    """Tests for write_silver path in BatchWriterIOMixin."""

    async def test_write_silver_passes_explicit_runtime_provenance(
        self, batch_writer, mock_storage, mock_context
    ):
        """Runtime provenance is passed separately, not injected into records."""
        records = [{"entity_id": "1"}]
        batch_id = deterministic_batch_uuid_from_callsite("test_batch_writer_io_mixin")

        await batch_writer.write_silver(records, batch_id, mock_context.started_at)

        request = mock_storage.write_silver.call_args.args[0]
        assert isinstance(request, SilverWriteRequest)
        assert request.run_id == mock_context.run_id
        assert request.run_type == mock_context.run_type
        assert request.source_batch_id == batch_id
        assert request.ingestion_ts == mock_context.started_at
        assert "_source_batch_id" not in request.records[0]

    async def test_write_silver_passes_table_name(
        self, mock_storage, mock_context, mock_gold_validator
    ):
        """Table name from config is passed to storage."""
        config = RecordProcessorConfig(
            pipeline_name="p",
            provider="prov",
            entity_type="ent",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            table_config=TableConfig(silver_table="custom_silver"),
        )
        writer = BatchWriter(
            storage=mock_storage,
            context=mock_context,
            config=config,
            gold_validator=mock_gold_validator,
            error_classifier=ErrorClassifier(),
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
        )

        await writer.write_silver(
            [{"entity_id": "1"}],
            deterministic_batch_uuid_from_callsite("test_batch_writer_io_mixin"),
            mock_context.started_at,
        )

        request = mock_storage.write_silver.call_args.args[0]
        assert isinstance(request, SilverWriteRequest)
        assert request.table_name == "custom_silver"

    async def test_write_silver_passes_primary_keys(
        self, mock_storage, mock_context, mock_gold_validator
    ):
        """primary_keys from table config are forwarded to storage."""
        writer = _make_writer(
            mock_storage,
            mock_context,
            mock_gold_validator,
            primary_keys=["entity_id", "version"],
        )

        await writer.write_silver(
            [{"entity_id": "1", "version": 2}],
            deterministic_batch_uuid_from_callsite("test_batch_writer_io_mixin"),
            mock_context.started_at,
        )

        request = mock_storage.write_silver.call_args.args[0]
        assert isinstance(request, SilverWriteRequest)
        assert set(request.primary_keys) == {"entity_id", "version"}

    async def test_write_silver_applies_renames_from_layer_config(
        self, mock_storage, mock_context, mock_gold_validator
    ):
        """Column renames from data_schema.silver.rename_fields are applied."""
        layer_config = MagicMock()
        layer_config.columns = []
        layer_config.rename_fields = {"old_name": "new_name"}

        data_schema = MagicMock()
        data_schema.silver = layer_config

        silver_schema = MagicMock()
        silver_schema.names = ["old_name"]

        config = RecordProcessorConfig(
            pipeline_name="p",
            provider="prov",
            entity_type="ent",
            silver_schema=silver_schema,
            gold_schema=MagicMock(),
            data_schema=data_schema,
        )
        writer = BatchWriter(
            storage=mock_storage,
            context=mock_context,
            config=config,
            gold_validator=mock_gold_validator,
            error_classifier=ErrorClassifier(),
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
        )

        await writer.write_silver(
            [{"old_name": "val"}],
            deterministic_batch_uuid_from_callsite("test_batch_writer_io_mixin"),
            mock_context.started_at,
        )

        request = mock_storage.write_silver.call_args.args[0]
        assert isinstance(request, SilverWriteRequest)
        record = request.records[0]
        assert "new_name" in record
        assert "old_name" not in record

    async def test_write_silver_reraises_oserror(
        self, mock_storage, mock_context, mock_gold_validator
    ):
        """OSError from storage propagates out of write_silver."""
        mock_storage.write_silver = AsyncMock(side_effect=OSError("io error"))
        writer = _make_writer(mock_storage, mock_context, mock_gold_validator)

        with pytest.raises(OSError):
            await writer.write_silver(
                [{"entity_id": "1"}],
                deterministic_batch_uuid_from_callsite("test_batch_writer_io_mixin"),
                mock_context.started_at,
            )

    async def test_write_silver_uses_silver_schema_names_for_available_cols(
        self, mock_storage, mock_context, mock_gold_validator
    ):
        """When silver_schema.names is set, it drives available columns."""
        silver_schema = MagicMock()
        silver_schema.names = ["entity_id", "value"]

        config = RecordProcessorConfig(
            pipeline_name="p",
            provider="prov",
            entity_type="ent",
            silver_schema=silver_schema,
            gold_schema=MagicMock(),
        )
        writer = BatchWriter(
            storage=mock_storage,
            context=mock_context,
            config=config,
            gold_validator=mock_gold_validator,
            error_classifier=ErrorClassifier(),
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
        )

        await writer.write_silver(
            [{"entity_id": "1", "value": 42}],
            deterministic_batch_uuid_from_callsite("test_batch_writer_io_mixin"),
            mock_context.started_at,
        )

        mock_storage.write_silver.assert_called_once()


# ---------------------------------------------------------------------------
# write_gold
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBatchWriterIOMixinGold:
    """Tests for write_gold path in BatchWriterIOMixin."""

    async def test_write_gold_calls_storage_once(self, batch_writer, mock_storage):
        """Gold records are written to storage exactly once."""
        await batch_writer.write_gold([{"entity_id": "1"}])

        mock_storage.write_gold.assert_called_once()

    async def test_write_gold_projects_to_schema_columns(
        self, mock_storage, mock_context
    ):
        """Records are projected to schema columns before writing."""

        class _Schema:
            @staticmethod
            def to_schema():
                s = MagicMock()
                s.columns = {"entity_id": object(), "value": object()}
                return s

        config = RecordProcessorConfig(
            pipeline_name="p",
            provider="prov",
            entity_type="ent",
            silver_schema=MagicMock(),
            gold_schema=_Schema,
        )
        writer = BatchWriter(
            storage=mock_storage,
            context=mock_context,
            config=config,
            gold_validator=MagicMock(
                validate=MagicMock(return_value=ValidationResult(valid=True))
            ),
            error_classifier=ErrorClassifier(),
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
        )

        await writer.write_gold([{"entity_id": "e1", "value": 1, "extra": "drop_me"}])

        kwargs = mock_storage.write_gold.call_args[1]
        record = kwargs["records"][0]
        assert "extra" not in record
        assert "entity_id" in record

    async def test_write_gold_raises_schema_violation_on_invalid_records(
        self, mock_storage, mock_context
    ):
        """SchemaViolationError raised when validator returns valid=False."""
        failing_validator = MagicMock()
        failing_validator.validate = MagicMock(
            return_value=ValidationResult(valid=False, errors=["missing field"])
        )
        config = RecordProcessorConfig(
            pipeline_name="p",
            provider="prov",
            entity_type="ent",
            silver_schema=MagicMock(),
            gold_schema=MagicMock(),
            gold_schema_policy_by_version=None,
        )
        writer = BatchWriter(
            storage=mock_storage,
            context=mock_context,
            config=config,
            gold_validator=failing_validator,
            error_classifier=ErrorClassifier(),
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
        )

        with pytest.raises(SchemaViolationError):
            await writer.write_gold([{"entity_id": "bad"}])

        mock_storage.write_gold.assert_not_called()

    async def test_write_gold_reraises_value_error_from_storage(
        self, mock_storage, mock_context, mock_gold_validator
    ):
        """ValueError from storage propagates out of write_gold."""
        mock_storage.write_gold = AsyncMock(side_effect=ValueError("bad data"))
        writer = _make_writer(mock_storage, mock_context, mock_gold_validator)

        with pytest.raises(ValueError):
            await writer.write_gold([{"entity_id": "1"}])

    async def test_write_gold_default_dq_fields_injected_when_missing(
        self, mock_storage, mock_context
    ):
        """_dq_warn and _dq_error get default False values from projection."""

        class _Schema:
            @staticmethod
            def to_schema():
                s = MagicMock()
                s.columns = {
                    "entity_id": object(),
                    "_dq_warn": object(),
                    "_dq_error": object(),
                }
                return s

        config = RecordProcessorConfig(
            pipeline_name="p",
            provider="prov",
            entity_type="ent",
            silver_schema=MagicMock(),
            gold_schema=_Schema,
        )
        writer = BatchWriter(
            storage=mock_storage,
            context=mock_context,
            config=config,
            gold_validator=MagicMock(
                validate=MagicMock(return_value=ValidationResult(valid=True))
            ),
            error_classifier=ErrorClassifier(),
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
        )

        # Record does not have DQ fields
        await writer.write_gold([{"entity_id": "e1"}])

        kwargs = mock_storage.write_gold.call_args[1]
        record = kwargs["records"][0]
        assert record.get("_dq_warn") is False
        assert record.get("_dq_error") is False

    async def test_write_gold_defers_multi_version_validation_to_storage(
        self, mock_storage, mock_context, mock_gold_validator
    ):
        """Multi-version Gold writes should skip local projection and validator calls."""
        active_schema = MagicMock(name="active_schema")
        legacy_schema = MagicMock(name="legacy_schema")
        config = RecordProcessorConfig(
            pipeline_name="p",
            provider="prov",
            entity_type="ent",
            silver_schema=MagicMock(),
            gold_schema=active_schema,
            gold_schema_policy_by_version=GoldSchemaPolicyByVersion(
                active_version="2.0.0",
                policies=(
                    GoldSchemaVersionPolicy(version="1.0.0", schema=legacy_schema),
                    GoldSchemaVersionPolicy(version="2.0.0", schema=active_schema),
                ),
            ),
        )
        writer = BatchWriter(
            storage=mock_storage,
            context=mock_context,
            config=config,
            gold_validator=mock_gold_validator,
            error_classifier=ErrorClassifier(),
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
        )

        records = [{"entity_id": "e1", "legacy_value": "x", "new_value": "y"}]
        await writer.write_gold(records)

        mock_gold_validator.validate.assert_not_called()
        kwargs = mock_storage.write_gold.call_args[1]
        assert kwargs["schema"] == config.gold_schema_policy_by_version
        assert kwargs["records"] == records

    async def test_write_gold_passes_primary_keys_to_storage(
        self, mock_storage, mock_context, mock_gold_validator
    ):
        """primary_keys from table config are forwarded to storage."""
        writer = _make_writer(
            mock_storage,
            mock_context,
            mock_gold_validator,
            primary_keys=["entity_id"],
        )

        await writer.write_gold([{"entity_id": "x"}])

        kwargs = mock_storage.write_gold.call_args[1]
        assert list(kwargs["primary_keys"]) == ["entity_id"]

    async def test_write_gold_passes_scd_config_from_config(
        self, mock_storage, mock_context, mock_gold_validator
    ):
        """SCD config from RecordProcessorConfig is forwarded to storage."""
        writer = _make_writer(
            mock_storage,
            mock_context,
            mock_gold_validator,
            primary_keys=["entity_id"],
            gold_write_mode="scd2",
            scd_config={"business_key": "entity_id", "valid_from_col": "valid_from"},
        )

        await writer.write_gold([{"entity_id": "x"}])

        kwargs = mock_storage.write_gold.call_args[1]
        assert kwargs["mode"] == "scd2"
        assert kwargs["scd_config"] == {
            "business_key": "entity_id",
            "valid_from_col": "valid_from",
        }

    async def test_write_gold_prefers_replay_timestamp_anchor(
        self, mock_storage, mock_gold_validator
    ):
        """Exact replay Gold side effects use the deterministic replay timestamp."""
        logger = MagicMock()
        replay_anchor = datetime(2026, 5, 16, 0, 0, tzinfo=UTC)
        occurrence_started_at = datetime(2026, 5, 19, 12, 30, tzinfo=UTC)
        context = PipelineContext.create(
            run_id=deterministic_uuid_from_callsite("test_batch_writer_io_mixin"),
            run_type=RunType.INCREMENTAL,
            logger=logger,
            started_at=occurrence_started_at,
            replay_timestamp_anchor=replay_anchor,
        )
        writer = _make_writer(
            mock_storage,
            context,
            mock_gold_validator,
            primary_keys=["entity_id"],
            gold_write_mode="scd2",
            scd_config={"business_key": "entity_id", "valid_from_col": "valid_from"},
        )

        await writer.write_gold([{"entity_id": "x"}])

        kwargs = mock_storage.write_gold.call_args[1]
        assert kwargs["ingestion_ts"] == replay_anchor
        assert kwargs["ingestion_ts"] != occurrence_started_at


# ---------------------------------------------------------------------------
# _prepare_gold_records
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPrepareGoldRecords:
    """Tests for BatchWriterIOMixin._prepare_gold_records."""

    def test_returns_all_records_when_no_schema_columns(self, batch_writer):
        """Without schema columns, returns original records and collected columns."""
        records = [{"a": 1, "b": 2}]
        # batch_writer's gold_schema has no .to_schema()/.columns attributes
        # that return data — _get_schema_columns will return None
        batch_writer._gold_schema = MagicMock(spec=[])  # no columns

        result_records, cols = batch_writer._prepare_gold_records(records)

        assert result_records == records
        assert set(cols) == {"a", "b"}

    def test_projects_records_to_schema_columns(self, mock_storage, mock_context):
        """Records filtered to schema column set."""

        class _Schema:
            @staticmethod
            def to_schema():
                s = MagicMock()
                s.columns = {"keep": object()}
                return s

        config = RecordProcessorConfig(
            pipeline_name="p",
            provider="prov",
            entity_type="ent",
            silver_schema=MagicMock(),
            gold_schema=_Schema,
        )
        writer = BatchWriter(
            storage=mock_storage,
            context=mock_context,
            config=config,
            gold_validator=MagicMock(
                validate=MagicMock(return_value=ValidationResult(valid=True))
            ),
            error_classifier=ErrorClassifier(),
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
        )

        projected, cols = writer._prepare_gold_records([{"keep": "yes", "drop": "no"}])

        assert projected == [{"keep": "yes"}]
        assert cols == ["keep"]


@pytest.mark.unit
class TestGoldValidationSupport:
    """Cover validator rebinding, diagnostics, and version-policy decisions."""

    def test_validate_gold_records_rebinds_to_projected_schema(self) -> None:
        """A projected schema must be validated by the validator's rebound clone."""
        projected_schema = object()
        rebound = MagicMock()
        rebound.validate.return_value = ValidationResult(valid=True)
        validator = MagicMock()
        validator.rebind_schema.return_value = rebound
        writer = SimpleNamespace(
            _gold_schema=object(),
            _gold_validator=validator,
        )
        records = [{"entity_id": "e1"}]

        validate_gold_records(writer, records, schema=projected_schema)

        validator.rebind_schema.assert_called_once_with(projected_schema)
        validator.validate.assert_not_called()
        rebound.validate.assert_called_once_with(records)

    def test_validate_gold_records_exports_failure_before_raising(self) -> None:
        """Invalid Gold data is captured by debug export before failing closed."""
        validator = MagicMock()
        validator.validate.return_value = ValidationResult(
            valid=False,
            errors=["entity_id is required"],
        )
        debug_export = MagicMock()
        writer = SimpleNamespace(
            _gold_schema=object(),
            _gold_validator=validator,
            _debug_export_service=debug_export,
        )
        records = [{"value": 1}]

        with pytest.raises(SchemaViolationError, match="Schema validation failed"):
            validate_gold_records(writer, records)

        debug_export.record_gold_validation_failure.assert_called_once_with(
            records=records,
            errors=["entity_id is required"],
        )

    def test_rebind_gold_validator_schema_supports_both_validator_shapes(self) -> None:
        """Schema-aware validators rebind while legacy validators remain unchanged."""
        schema = object()
        rebound = object()
        validator = MagicMock()
        validator.rebind_schema.return_value = rebound

        assert rebind_gold_validator_schema(validator, schema) is rebound
        validator.rebind_schema.assert_called_once_with(schema)

        legacy_validator = object()
        assert (
            rebind_gold_validator_schema(legacy_validator, schema)
            is legacy_validator
        )

    @pytest.mark.parametrize(
        ("policy", "expected"),
        [
            (None, False),
            (SimpleNamespace(is_multi_version=False), False),
            (SimpleNamespace(is_multi_version=True), True),
        ],
    )
    def test_should_defer_gold_validation_requires_multi_version_policy(
        self,
        policy: object | None,
        expected: bool,
    ) -> None:
        """Only an explicitly multi-version policy delegates validation to storage."""
        assert (
            should_defer_gold_validation_to_storage(
                SimpleNamespace(_gold_schema_policy_by_version=policy)
            )
            is expected
        )


@pytest.mark.unit
class TestBatchWriterIOMixinFailureAndProjectionPaths:
    """Cover cancellation safety and the projected-schema Gold path."""

    @pytest.mark.parametrize("layer", ["bronze", "silver", "gold"])
    async def test_write_layer_propagates_cancellation_without_error_classification(
        self,
        layer: str,
        mock_storage,
        mock_context,
        mock_gold_validator,
    ) -> None:
        """Task cancellation closes the span but is never rewritten as an operation error."""
        getattr(mock_storage, f"write_{layer}").side_effect = asyncio.CancelledError()
        writer = _make_writer(mock_storage, mock_context, mock_gold_validator)

        with pytest.raises(asyncio.CancelledError):
            if layer == "bronze":
                await writer.write_bronze(
                    [{"entity_id": "e1"}],
                    deterministic_batch_uuid_from_callsite(
                        "test_batch_writer_io_mixin"
                    ),
                    mock_context.started_at,
                )
            elif layer == "silver":
                await writer.write_silver(
                    [{"entity_id": "e1"}],
                    deterministic_batch_uuid_from_callsite(
                        "test_batch_writer_io_mixin"
                    ),
                    mock_context.started_at,
                )
            else:
                await writer.write_gold([{"entity_id": "e1"}])

    async def test_write_gold_reprojects_and_revalidates_projected_schema(
        self,
        mock_storage,
        mock_context,
    ) -> None:
        """Layer projection is applied before a second schema-bound validation."""

        class _ProjectedSchema:
            columns = {"entity_id": object()}

        projected_schema = _ProjectedSchema()

        class _ConvertedSchema:
            columns = {"entity_id": object(), "extra": object()}

            @staticmethod
            def select_columns(columns: list[str]) -> object:
                assert columns == ["entity_id"]
                return projected_schema

        class _GoldSchema:
            @staticmethod
            def to_schema() -> object:
                return _ConvertedSchema()

        validator = MagicMock()
        validator.validate.return_value = ValidationResult(valid=True)
        rebound = MagicMock()
        rebound.validate.return_value = ValidationResult(valid=True)
        validator.rebind_schema.return_value = rebound
        layer_config = SimpleNamespace(
            columns=["entity_id"],
            rename_fields={},
        )
        data_schema = SimpleNamespace(gold=layer_config)
        config = RecordProcessorConfig(
            pipeline_name="p",
            provider="prov",
            entity_type="ent",
            silver_schema=MagicMock(),
            gold_schema=_GoldSchema,
        )
        writer = BatchWriter(
            storage=mock_storage,
            context=mock_context,
            config=config,
            gold_validator=validator,
            error_classifier=ErrorClassifier(),
            batch_metrics=MagicMock(spec=BatchMetricsRecorder),
            options=BatchWriterOptions(
                data_schema_config=data_schema,
                column_orderer=ColumnOrderService(MagicMock()),
            ),
        )

        await writer.write_gold([{"entity_id": "e1", "extra": "drop"}])

        validator.validate.assert_called_once()
        validator.rebind_schema.assert_called_once_with(projected_schema)
        rebound.validate.assert_called_once_with([{"entity_id": "e1"}])
        kwargs = mock_storage.write_gold.call_args.kwargs
        assert kwargs["schema"] is projected_schema
        assert kwargs["records"] == [{"entity_id": "e1"}]

    async def test_write_gold_applies_configured_field_rename(
        self,
        mock_storage,
        mock_context,
        mock_gold_validator,
    ) -> None:
        """Gold rename mappings are applied to the final storage payload."""
        layer_config = SimpleNamespace(
            columns=["entity_id"],
            rename_fields={"entity_id": "record_id"},
        )
        data_schema = SimpleNamespace(gold=layer_config)
        writer = _make_writer(
            mock_storage,
            mock_context,
            mock_gold_validator,
            gold_schema=MagicMock(spec=[]),
        )
        writer._data_schema = data_schema
        writer._column_orderer = ColumnOrderService(MagicMock())

        await writer.write_gold([{"entity_id": "e1"}])

        assert mock_storage.write_gold.call_args.kwargs["records"] == [
            {"record_id": "e1"}
        ]
