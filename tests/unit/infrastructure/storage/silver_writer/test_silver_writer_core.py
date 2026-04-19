"""Core SilverWriter unit tests (init, validation, mode, path, predicate)."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = pytest.mark.unit

TEST_ROOT = Path(tempfile.mkdtemp(prefix="bioetl-silver-writer-core-"))
SILVER_ROOT = str(TEST_ROOT / "silver")
SILVER_TABLE_PATH = str(TEST_ROOT / "silver" / "test" / "table")


class TestSilverWriterInit:
    """Tests for SilverWriter initialization."""

    def test_init_strips_trailing_slash(self, noop_logger):
        """Test that trailing slash is stripped from base_path."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="s3://bucket/path/", logger=noop_logger)
        assert writer.base_path == "s3://bucket/path"

    def test_init_with_csv_exporter(self, noop_logger):
        """Test initialization with CSV exporter."""
        from unittest.mock import MagicMock

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        mock_exporter = MagicMock()
        writer = SilverWriter(
            base_path=SILVER_ROOT,
            logger=noop_logger,
            csv_exporter=mock_exporter,
        )
        assert writer.csv_exporter is mock_exporter

    def test_init_without_csv_exporter(self, noop_logger):
        """Test initialization without CSV exporter."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path=SILVER_ROOT, logger=noop_logger)
        assert writer.csv_exporter is None

    def test_runtime_helper_builds_defaults(self) -> None:
        """Runtime helper should resolve the standard SilverWriter defaults."""
        from bioetl.domain.medallion import WriteModePolicy
        from bioetl.domain.ports.noop import NoOpMetadataWriter
        from bioetl.domain.services.dq_metrics_calculator import DQMetricsCalculator
        from bioetl.infrastructure.storage.silver.runtime_helpers import (
            resolve_silver_writer_runtime,
        )
        from bioetl.infrastructure.storage.delta.resilience import (
            DEFAULT_SILVER_MERGE_POLICY,
        )
        from bioetl.infrastructure.validation.pandera_validator import (
            NoOpValidator,
        )

        (
            tracing,
            write_policy,
            silver_validator,
            metadata_writer,
            dq_calculator,
            merge_resilience_policy,
        ) = resolve_silver_writer_runtime(
            tracing=None,
            write_policy=None,
            silver_validator=None,
            metadata_writer=None,
            dq_calculator=None,
            merge_resilience_policy=None,
        )

        assert tracing is None
        assert isinstance(write_policy, WriteModePolicy)
        assert isinstance(silver_validator, NoOpValidator)
        assert isinstance(metadata_writer, NoOpMetadataWriter)
        assert isinstance(dq_calculator, DQMetricsCalculator)
        assert merge_resilience_policy is DEFAULT_SILVER_MERGE_POLICY

    def test_runtime_helper_preserves_custom_dependencies(self) -> None:
        """Runtime helper should preserve explicitly provided dependencies."""
        from bioetl.domain.medallion import WriteModePolicy
        from bioetl.domain.services.dq_metrics_calculator import DQMetricsCalculator
        from bioetl.infrastructure.storage.silver.runtime_helpers import (
            resolve_silver_writer_runtime,
        )
        from bioetl.infrastructure.storage.delta.resilience import (
            build_default_silver_merge_policy,
        )

        custom_tracing = MagicMock()
        custom_policy = WriteModePolicy()
        custom_validator = MagicMock()
        custom_metadata_writer = MagicMock()
        custom_dq_calculator = DQMetricsCalculator()
        custom_merge_policy = build_default_silver_merge_policy()

        resolved = resolve_silver_writer_runtime(
            tracing=custom_tracing,
            write_policy=custom_policy,
            silver_validator=custom_validator,
            metadata_writer=custom_metadata_writer,
            dq_calculator=custom_dq_calculator,
            merge_resilience_policy=custom_merge_policy,
        )

        assert resolved == (
            custom_tracing,
            custom_policy,
            custom_validator,
            custom_metadata_writer,
            custom_dq_calculator,
            custom_merge_policy,
        )


@pytest.mark.unit
class TestSilverWriterValidation:
    """Tests for SilverWriter validation."""

    def test_sync_validate_and_build_arrow_returns_named_context(
        self, noop_logger, valid_records
    ) -> None:
        """Validation helper should return a named pre-write context."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )
        from bioetl.infrastructure.storage.silver.validation_mixin import (
            _SilverWritePreparationRequest,
        )

        writer = SilverWriter(base_path=SILVER_ROOT, logger=noop_logger)
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

        validated = writer._sync_validate_and_build_arrow(
            _SilverWritePreparationRequest(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="merge",
                column_order=None,
                partition_cols=["entity_id"],
                key_nullability_rules=None,
            )
        )

        assert validated.records == valid_records
        assert validated.validated_mode is SilverWriteMode.MERGE
        assert validated.arrow_data.num_rows == len(valid_records)

    @pytest.mark.asyncio
    async def test_execute_silver_write_with_tracing_builds_context_and_runs_pipeline(
        self,
    ) -> None:
        """Tracing helper should create span context and delegate pipeline execution."""
        from datetime import UTC, datetime
        from uuid import uuid4

        import pyarrow as pa

        from bioetl.domain.types import BatchID, RunID, RunType
        from bioetl.infrastructure.storage.silver.pipeline_helpers import (
            _SilverWriteExecutionContext,
            _SilverWriteInvocation,
            execute_silver_write_with_tracing,
        )

        records = [{"entity_id": "CHEMBL123"}]
        schema = pa.Table.from_pylist(records).schema
        tracing = MagicMock()
        tracer = MagicMock()
        span_cm = MagicMock()
        span = MagicMock()
        tracing.get_tracer.return_value = tracer
        tracer.start_as_current_span.return_value = span_cm
        span_cm.__enter__.return_value = span
        expected_result = MagicMock()
        started_at = datetime.now(UTC)
        start_perf = 123.0
        invocation = _SilverWriteInvocation(
            table_name="test.table",
            records=records,
            primary_keys=["entity_id"],
            schema=schema,
            mode="merge",
            partition_cols=["entity_id"],
            on_schema_mismatch="ignore",
            column_order=None,
            bronze_refs=None,
            key_nullability_rules=None,
            run_id=RunID(uuid4()),
            run_type=RunType.INCREMENTAL,
            source_batch_id=BatchID(uuid4()),
            ingestion_ts=datetime.fromisoformat("2025-01-15T12:00:00+00:00"),
        )

        async def execute_pipeline(
            *,
            invocation: _SilverWriteInvocation,
            ctx: _SilverWriteExecutionContext,
        ) -> object:
            await asyncio.sleep(0)
            assert ctx.table_name == "test.table"
            assert ctx.primary_keys == ["entity_id"]
            assert ctx.schema == schema
            assert ctx.mode == "merge"
            assert ctx.partition_cols == ["entity_id"]
            assert ctx.on_schema_mismatch == "ignore"
            assert ctx.bronze_refs is None
            assert ctx.key_nullability_rules is None
            assert ctx.run_id == invocation.run_id
            assert ctx.run_type == invocation.run_type
            assert ctx.source_batch_id == invocation.source_batch_id
            assert ctx.ingestion_ts == invocation.ingestion_ts
            assert ctx.span is span
            assert isinstance(ctx.start_perf, float)
            assert invocation.records == [{"entity_id": "CHEMBL123"}]
            return expected_result

        result = await execute_silver_write_with_tracing(
            tracing=tracing,
            module_name="bioetl.test",
            invocation=invocation,
            started_at=started_at,
            start_perf=start_perf,
            execute_pipeline=execute_pipeline,
        )

        assert result is expected_result
        tracing.get_tracer.assert_called_once_with("bioetl.test")
        tracer.start_as_current_span.assert_called_once_with("write_silver")
        span.set_attribute.assert_any_call("table_name", "test.table")
        span.set_attribute.assert_any_call("mode", "merge")
        span.set_attribute.assert_any_call("record_count", 1)
        span.set_attribute.assert_any_call("bioetl.table_name", "test.table")
        span.set_attribute.assert_any_call("bioetl.write_mode", "merge")
        span.set_attribute.assert_any_call("bioetl.record_count", 1)
        span.set_attribute.assert_any_call("bioetl.provider", "test")
        span.set_attribute.assert_any_call("bioetl.entity_type", "table")
        span.set_attribute.assert_any_call(
            "bioetl.pipeline_run_id",
            str(invocation.run_id),
        )
        span.set_attribute.assert_any_call("bioetl.run_type", "incremental")

    @pytest.mark.asyncio
    async def test_execute_silver_write_with_tracing_emits_operational_context(
        self,
    ) -> None:
        """Tracing helper should expose provider/entity/run context for operations."""
        from datetime import UTC, datetime
        from uuid import UUID

        import pyarrow as pa

        from bioetl.domain.types import BatchID, RunID, RunType
        from bioetl.infrastructure.storage.silver.pipeline_helpers import (
            _SilverWriteExecutionContext,
            _SilverWriteInvocation,
            execute_silver_write_with_tracing,
        )

        records = [{"entity_id": "CHEMBL123"}]
        schema = pa.Table.from_pylist(records).schema
        tracing = MagicMock()
        tracer = MagicMock()
        span_cm = MagicMock()
        span = MagicMock()
        tracing.get_tracer.return_value = tracer
        tracer.start_as_current_span.return_value = span_cm
        span_cm.__enter__.return_value = span
        invocation = _SilverWriteInvocation(
            table_name="chembl.activity",
            records=records,
            primary_keys=["entity_id"],
            schema=schema,
            mode="merge",
            partition_cols=["entity_id"],
            on_schema_mismatch="ignore",
            column_order=None,
            bronze_refs=None,
            key_nullability_rules=None,
            run_id=RunID(UUID("00000000-0000-0000-0000-000000000001")),
            run_type=RunType.INCREMENTAL,
            source_batch_id=BatchID(UUID("00000000-0000-0000-0000-000000000002")),
            ingestion_ts=datetime.fromisoformat("2025-01-15T12:00:00+00:00"),
        )

        async def execute_pipeline(
            *,
            invocation: _SilverWriteInvocation,
            ctx: _SilverWriteExecutionContext,
        ) -> None:
            await asyncio.sleep(0)
            assert ctx.table_name == "chembl.activity"

        await execute_silver_write_with_tracing(
            tracing=tracing,
            module_name="bioetl.test",
            invocation=invocation,
            started_at=datetime.now(UTC),
            start_perf=123.0,
            execute_pipeline=execute_pipeline,
        )

        span.set_attribute.assert_any_call("bioetl.provider", "chembl")
        span.set_attribute.assert_any_call("bioetl.entity_type", "activity")
        span.set_attribute.assert_any_call(
            "bioetl.pipeline_run_id",
            "00000000-0000-0000-0000-000000000001",
        )
        span.set_attribute.assert_any_call("bioetl.run_type", "incremental")

    @pytest.mark.asyncio
    async def test_execute_silver_write_with_tracing_omits_identity_when_unparseable(
        self,
    ) -> None:
        """Tracing helper should not invent provider/entity for opaque table names."""
        from datetime import UTC, datetime

        import pyarrow as pa

        from bioetl.infrastructure.storage.silver.pipeline_helpers import (
            _SilverWriteExecutionContext,
            _SilverWriteInvocation,
            execute_silver_write_with_tracing,
        )

        records = [
            {
                "entity_id": "CHEMBL123",
                "_source_batch_id": "batch-456",
                "_ingestion_ts": "2025-01-15T12:00:00Z",
            }
        ]
        schema = pa.Table.from_pylist(records).schema
        tracing = MagicMock()
        tracer = MagicMock()
        span_cm = MagicMock()
        span = MagicMock()
        tracing.get_tracer.return_value = tracer
        tracer.start_as_current_span.return_value = span_cm
        span_cm.__enter__.return_value = span
        invocation = _SilverWriteInvocation(
            table_name="singletable",
            records=records,
            primary_keys=["entity_id"],
            schema=schema,
            mode="append",
            partition_cols=None,
            on_schema_mismatch="ignore",
            column_order=None,
            bronze_refs=None,
            key_nullability_rules=None,
            run_id=None,
            run_type=None,
            source_batch_id=None,
            ingestion_ts=None,
        )

        async def execute_pipeline(
            *,
            invocation: _SilverWriteInvocation,
            ctx: _SilverWriteExecutionContext,
        ) -> None:
            await asyncio.sleep(0)
            assert ctx.table_name == "singletable"

        await execute_silver_write_with_tracing(
            tracing=tracing,
            module_name="bioetl.test",
            invocation=invocation,
            started_at=datetime.now(UTC),
            start_perf=123.0,
            execute_pipeline=execute_pipeline,
        )

        attr_calls = [call.args for call in span.set_attribute.call_args_list]
        assert ("bioetl.provider", "singletable") not in attr_calls
        assert ("bioetl.entity_type", "singletable") not in attr_calls
        assert ("bioetl.pipeline_run_id", "singletable") not in attr_calls

    @pytest.mark.asyncio
    async def test_execute_silver_write_pipeline_helper_runs_stages_in_order(
        self,
    ) -> None:
        """Pipeline helper should prepare, dispatch, and finalize in sequence."""
        from datetime import UTC, datetime

        import pyarrow as pa

        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.infrastructure.storage.silver.pipeline_helpers import (
            _SilverWriteExecutionContext,
            _SilverWriteInvocation,
            execute_silver_write_pipeline,
        )
        from bioetl.infrastructure.storage.silver.validation_mixin import (
            _PreparedSilverWritePayload,
        )

        payload_records = [
            {
                "entity_id": "CHEMBL123",
                "_run_id": "uuid-123",
                "_run_type": "incremental",
                "_source_batch_id": "batch-456",
                "_ingestion_ts": "2025-01-15T12:00:00Z",
            }
        ]
        # Create proper Arrow table with explicit schema to avoid Delta Lake errors
        schema = pa.schema(
            [
                pa.field("entity_id", pa.string()),
                pa.field("_run_id", pa.string()),
                pa.field("_run_type", pa.string()),
                pa.field("_source_batch_id", pa.string()),
                pa.field("_ingestion_ts", pa.string()),
            ]
        )
        payload = _PreparedSilverWritePayload(
            records=payload_records,
            validated_mode=SilverWriteMode.MERGE,
            table_path=SILVER_TABLE_PATH,
            arrow_data=pa.Table.from_pylist(payload_records, schema=schema),
            schema_mode=None,
            merge_schema=False,
        )
        prepare_payload = AsyncMock(return_value=payload)
        dispatch_write = AsyncMock()
        expected_result = MagicMock()
        complete_pipeline = AsyncMock(return_value=expected_result)
        span = MagicMock()
        invocation = _SilverWriteInvocation(
            table_name="test.table",
            records=payload_records,
            primary_keys=["entity_id"],
            schema=payload.arrow_data.schema,
            mode="merge",
            partition_cols=["entity_id"],
            on_schema_mismatch="ignore",
            column_order=None,
            bronze_refs=None,
            key_nullability_rules=None,
            run_id=None,
            run_type=None,
            source_batch_id=None,
            ingestion_ts=None,
        )
        ctx = _SilverWriteExecutionContext(
            table_name="test.table",
            primary_keys=["entity_id"],
            schema=payload.arrow_data.schema,
            mode="merge",
            partition_cols=["entity_id"],
            on_schema_mismatch="ignore",
            column_order=None,
            bronze_refs=None,
            key_nullability_rules=None,
            run_id=None,
            run_type=None,
            source_batch_id=None,
            ingestion_ts=None,
            started_at=datetime.now(UTC),
            start_perf=123.0,
            span=span,
        )

        result = await execute_silver_write_pipeline(
            invocation=invocation,
            ctx=ctx,
            prepare_payload=prepare_payload,
            dispatch_write=dispatch_write,
            complete_pipeline=complete_pipeline,
        )

        assert result is expected_result
        prepare_payload.assert_awaited_once_with(
            table_name="test.table",
            records=payload_records,
            primary_keys=["entity_id"],
            schema=payload.arrow_data.schema,
            mode="merge",
            on_schema_mismatch="ignore",
            column_order=None,
            partition_cols=["entity_id"],
            key_nullability_rules=None,
        )
        dispatch_write.assert_awaited_once()
        complete_pipeline.assert_awaited_once_with(ctx=ctx, payload=payload)
        span.set_attribute.assert_called_once_with("record_count", len(payload.records))

    @pytest.mark.asyncio
    async def test_execute_pipeline_builds_delta_request_and_forwards_payload(
        self,
        noop_logger,
    ) -> None:
        """Writer-level pipeline should pass a typed Delta request and payload onward."""
        from datetime import UTC, datetime

        import pyarrow as pa

        from bioetl.domain.medallion import SilverWriteMode
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriter,
            _SilverWriteExecutionContext,
        )
        from bioetl.infrastructure.storage.silver.pipeline_helpers import (
            _SilverWriteInvocation,
        )
        from bioetl.infrastructure.storage.silver.delta_mixin import (
            _DeltaWriteRequest,
        )
        from bioetl.infrastructure.storage.silver.validation_mixin import (
            _PreparedSilverWritePayload,
        )

        writer = SilverWriter(base_path=SILVER_ROOT, logger=noop_logger)
        payload_records = [
            {
                "entity_id": "CHEMBL123",
                "_run_id": "uuid-123",
                "_run_type": "incremental",
                "_source_batch_id": "batch-456",
                "_ingestion_ts": "2025-01-15T12:00:00Z",
            }
        ]
        payload = _PreparedSilverWritePayload(
            records=payload_records,
            validated_mode=SilverWriteMode.MERGE,
            table_path=SILVER_TABLE_PATH,
            arrow_data=pa.Table.from_pylist(payload_records),
            schema_mode=None,
            merge_schema=False,
        )
        writer._prepare_silver_write_payload = AsyncMock(  # type: ignore[method-assign]
            return_value=payload
        )
        writer._dispatch_write_with_domain_errors = AsyncMock()  # type: ignore[method-assign]
        expected_result = MagicMock()
        writer._complete_silver_write_pipeline = AsyncMock(  # type: ignore[method-assign]
            return_value=expected_result
        )
        span = MagicMock()
        invocation = _SilverWriteInvocation(
            table_name="test.table",
            records=payload_records,
            primary_keys=["entity_id"],
            schema=payload.arrow_data.schema,
            mode="merge",
            partition_cols=["entity_id"],
            on_schema_mismatch="ignore",
            column_order=None,
            bronze_refs=None,
            key_nullability_rules=None,
            run_id=None,
            run_type=None,
            source_batch_id=None,
            ingestion_ts=None,
        )
        ctx = _SilverWriteExecutionContext(
            table_name="test.table",
            primary_keys=["entity_id"],
            schema=payload.arrow_data.schema,
            mode="merge",
            partition_cols=["entity_id"],
            on_schema_mismatch="ignore",
            column_order=None,
            bronze_refs=None,
            key_nullability_rules=None,
            run_id=None,
            run_type=None,
            source_batch_id=None,
            ingestion_ts=None,
            started_at=datetime.now(UTC),
            start_perf=123.0,
            span=span,
        )

        result = await writer._execute_silver_write_pipeline(
            invocation=invocation,
            ctx=ctx,
        )

        assert result is expected_result
        writer._prepare_silver_write_payload.assert_awaited_once_with(
            table_name="test.table",
            records=payload_records,
            primary_keys=["entity_id"],
            schema=payload.arrow_data.schema,
            mode="merge",
            on_schema_mismatch="ignore",
            column_order=None,
            partition_cols=["entity_id"],
            key_nullability_rules=None,
        )
        dispatch_kwargs = writer._dispatch_write_with_domain_errors.await_args.kwargs
        assert dispatch_kwargs["table_name"] == "test.table"
        request = dispatch_kwargs["request"]
        assert isinstance(request, _DeltaWriteRequest)
        assert request.validated_mode is SilverWriteMode.MERGE
        assert request.table_path == payload.table_path
        assert request.arrow_data.equals(payload.arrow_data)
        assert request.primary_keys == ["entity_id"]
        assert request.partition_cols == ["entity_id"]
        writer._complete_silver_write_pipeline.assert_awaited_once_with(
            ctx=ctx,
            payload=payload,
        )
        span.set_attribute.assert_called_once_with("record_count", len(payload.records))

    @pytest.mark.asyncio
    async def test_write_silver_invalid_mode_raises(self, noop_logger, valid_records):
        """Test write_silver raises ValueError for invalid mode."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="s3://bucket", logger=noop_logger)
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

        with pytest.raises(ValueError, match="Invalid Silver write mode 'invalid'"):
            await writer.write_silver(
                table_name="test.table",
                records=valid_records,
                primary_keys=["entity_id"],
                schema=schema,
                mode="invalid",
            )

    @pytest.mark.asyncio
    async def test_write_silver_empty_records_raises(self, noop_logger):
        """Test write_silver raises ValueError for empty records."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="s3://bucket", logger=noop_logger)

        dummy_schema = pa.schema([pa.field("entity_id", pa.string())])

        with pytest.raises(ValueError, match="No records to write"):
            await writer.write_silver(
                table_name="test.table",
                records=[],
                primary_keys=["entity_id"],
                schema=dummy_schema,
            )

    @pytest.mark.asyncio
    async def test_write_silver_allows_records_without_runtime_metadata(
        self, noop_logger
    ):
        """Public Silver write accepts records without embedded runtime provenance."""
        from unittest.mock import AsyncMock

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="s3://bucket", logger=noop_logger)
        records = [{"entity_id": "CHEMBL123", "value": 5.5}]

        import pyarrow as pa

        dummy_schema = pa.schema([pa.field("entity_id", pa.string())])

        writer._write_single_target = AsyncMock(return_value=None)  # type: ignore[method-assign]

        await writer.write_silver(
            table_name="test.table",
            records=records,
            primary_keys=["entity_id"],
            schema=dummy_schema,
        )

        writer._write_single_target.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_write_silver_passes_explicit_runtime_provenance(self, noop_logger):
        """Public Silver write forwards provenance outside the row payload."""
        from datetime import UTC, datetime
        from unittest.mock import AsyncMock
        from uuid import UUID

        from bioetl.domain.types import BatchID, RunID, RunType
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="s3://bucket", logger=noop_logger)
        records = [{"entity_id": "CHEMBL123"}]

        import pyarrow as pa

        dummy_schema = pa.schema([pa.field("entity_id", pa.string())])
        writer._write_single_target = AsyncMock(return_value=None)  # type: ignore[method-assign]
        run_id = RunID(UUID("00000000-0000-0000-0000-000000000010"))
        source_batch_id = BatchID(UUID("00000000-0000-0000-0000-000000000011"))
        ingestion_ts = datetime(2025, 1, 15, 12, 0, tzinfo=UTC)

        await writer.write_silver(
            table_name="test.table",
            records=records,
            primary_keys=["entity_id"],
            schema=dummy_schema,
            run_id=run_id,
            run_type=RunType.INCREMENTAL,
            source_batch_id=source_batch_id,
            ingestion_ts=ingestion_ts,
        )

        writer._write_single_target.assert_awaited_once()
        kwargs = writer._write_single_target.await_args.kwargs
        assert kwargs["run_id"] == run_id
        assert kwargs["run_type"] == RunType.INCREMENTAL
        assert kwargs["source_batch_id"] == source_batch_id
        assert kwargs["ingestion_ts"] == ingestion_ts

    @pytest.mark.asyncio
    async def test_write_silver_builds_invocation_and_delegates_to_tracing_helper(
        self,
        noop_logger,
        monkeypatch,
    ) -> None:
        """Public write path should build one invocation object for tracing helper."""
        import pyarrow as pa

        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="s3://bucket", logger=noop_logger)
        records = [
            {
                "entity_id": "CHEMBL123",
                "value": 5.5,
                "_run_id": "uuid-123",
                "_run_type": "incremental",
                "_source_batch_id": "batch-456",
                "_ingestion_ts": "2025-01-15T12:00:00Z",
            }
        ]
        schema = pa.Table.from_pylist(records).schema
        expected_result = MagicMock()
        captured: dict[str, object] = {}

        async def fake_execute_silver_write_with_tracing(**kwargs):
            await asyncio.sleep(0)
            captured.update(kwargs)
            return expected_result

        monkeypatch.setattr(
            "bioetl.infrastructure.storage.silver_writer.execute_silver_write_with_tracing",
            fake_execute_silver_write_with_tracing,
        )

        result = await writer.write_silver(
            table_name="test.table",
            records=records,
            primary_keys=["entity_id"],
            schema=schema,
            mode="merge",
            partition_cols=["entity_id"],
            on_schema_mismatch="ignore",
        )

        assert result is expected_result
        invocation = captured["invocation"]
        assert invocation.table_name == "test.table"
        assert invocation.records == records
        assert invocation.primary_keys == ["entity_id"]
        assert invocation.schema == schema
        assert invocation.mode == "merge"
        assert invocation.partition_cols == ["entity_id"]
        assert invocation.on_schema_mismatch == "ignore"
        assert captured["tracing"] is writer._tracing
        assert captured["module_name"] == "bioetl.infrastructure.storage.silver_writer"
        assert captured["execute_pipeline"] == writer._execute_silver_write_pipeline


@pytest.mark.unit
class TestSilverWriterWriteModeEnum:
    """Tests for SilverWriteMode enum."""

    def test_silver_write_mode_values(self):
        """Test all valid SilverWriteMode values."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriteMode

        assert SilverWriteMode.MERGE.value == "merge"
        assert SilverWriteMode.APPEND.value == "append"
        assert SilverWriteMode.DELETE.value == "delete"

    def test_silver_write_mode_from_string(self):
        """Test creating SilverWriteMode from string."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriteMode

        assert SilverWriteMode("merge") == SilverWriteMode.MERGE
        assert SilverWriteMode("append") == SilverWriteMode.APPEND
        assert SilverWriteMode("delete") == SilverWriteMode.DELETE

    def test_silver_write_mode_invalid_raises(self):
        """Test invalid mode string raises ValueError."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriteMode

        with pytest.raises(ValueError):
            SilverWriteMode("invalid")

        with pytest.raises(ValueError):
            SilverWriteMode("MERGE")  # Case sensitive

    def test_validate_write_mode_method(self, noop_logger):
        """Test _validate_write_mode returns correct enum."""
        from bioetl.infrastructure.storage.silver_writer import (
            SilverWriteMode,
            SilverWriter,
        )

        writer = SilverWriter(base_path=SILVER_ROOT, logger=noop_logger)

        assert writer._validate_write_mode("merge") == SilverWriteMode.MERGE
        assert writer._validate_write_mode("append") == SilverWriteMode.APPEND
        assert writer._validate_write_mode("delete") == SilverWriteMode.DELETE

        with pytest.raises(ValueError, match="Invalid Silver write mode 'invalid'"):
            writer._validate_write_mode("invalid")

        with pytest.raises(ValueError, match="Allowed"):
            writer._validate_write_mode("overwrite")  # Valid for Gold, not Silver


@pytest.mark.unit
class TestSilverWriterTablePath:
    """Tests for table path construction."""

    def test_table_path_construction(self, noop_logger):
        """Test table path is constructed correctly."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

        # Access internal path construction
        table_name = "chembl.activity"
        expected_path = "s3://bucket/silver/chembl/activity"
        actual_path = f"{writer.base_path}/{table_name.replace('.', '/')}"

        assert actual_path == expected_path

    def test_table_path_with_nested_name(self, noop_logger):
        """Test table path with nested table name."""
        from bioetl.infrastructure.storage.silver_writer import SilverWriter

        writer = SilverWriter(base_path="s3://bucket/silver", logger=noop_logger)

        table_name = "provider.schema.table"
        expected_path = "s3://bucket/silver/provider/schema/table"
        actual_path = f"{writer.base_path}/{table_name.replace('.', '/')}"

        assert actual_path == expected_path


@pytest.mark.unit
class TestSilverWriterMergePredicate:
    """Tests for merge predicate building."""

    def test_build_single_key_predicate(self):
        """Test predicate building with single primary key."""
        primary_keys = ["entity_id"]
        predicate = " AND ".join(f"target.{key} = source.{key}" for key in primary_keys)

        assert predicate == "target.entity_id = source.entity_id"

    def test_build_multi_key_predicate(self):
        """Test predicate building with multiple primary keys."""
        primary_keys = ["entity_id", "version"]
        predicate = " AND ".join(f"target.{key} = source.{key}" for key in primary_keys)

        assert (
            predicate
            == "target.entity_id = source.entity_id AND target.version = source.version"
        )

    def test_build_compound_key_predicate(self):
        """Test predicate building with compound primary keys."""
        primary_keys = ["provider", "entity_type", "entity_id"]
        predicate = " AND ".join(f"target.{key} = source.{key}" for key in primary_keys)

        expected = (
            "target.provider = source.provider AND "
            "target.entity_type = source.entity_type AND "
            "target.entity_id = source.entity_id"
        )
        assert predicate == expected
