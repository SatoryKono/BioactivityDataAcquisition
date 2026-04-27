"""Coverage boost tests for metadata_writer.py.

Targets uncovered lines: 53, 94, 118, 136, 263, 306-315.
"""

from __future__ import annotations

import errno
from collections.abc import Callable
from datetime import UTC, datetime
from typing import cast
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from bioetl.domain.medallion import Layer
from bioetl.domain.models.metadata import (
    BaseOutputMetadata,
    BronzeMetadata,
    BronzeOutputExt,
    DeltaMetrics,
    DQSummary,
    EnvironmentMetadata,
    FileOutputMetadata,
    GoldMetadata,
    GoldOutputExt,
    LineageMetadata,
    PipelineMetadata,
    RuntimeMetadata,
    RunTypeEnum,
    SchemaMetadata,
    SilverMetadata,
    SilverOutputExt,
    SourceMetadata,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.support.atomic_ops import AtomicWriteError
from bioetl.infrastructure.storage.metadata_writer import (
    METADATA_FILENAME,
    MetadataWriter,
    _get_metadata_filename,
)
from bioetl.infrastructure.storage.delta.resilience import AdaptiveRetryPolicy


def _fake_atomic_write_text(
    path: object,
    content: object,
    *,
    retry_policy: object,
    on_retry: Callable[[int, float, OSError], None],
) -> None:
    del path, content, retry_policy, on_retry


def _retry_once_atomic_write_text(
    path: object,
    content: object,
    *,
    retry_policy: object,
    on_retry: Callable[[int, float, OSError], None],
) -> None:
    del path, content, retry_policy
    retry_callback = cast(Callable[[int, float, OSError], None], on_retry)
    retry_callback(1, 0.001, OSError(errno.EBUSY, "busy"))


def _make_runtime() -> RuntimeMetadata:
    return RuntimeMetadata(
        run_id=str(uuid4()),
        run_type=RunTypeEnum.INCREMENTAL,
        started_at_utc=datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
        completed_at_utc=datetime(2025, 1, 15, 10, 5, 0, tzinfo=UTC),
    )


def _make_pipeline() -> PipelineMetadata:
    return PipelineMetadata(
        name="chembl_activity",
        provider="chembl",
        entity="activity",
        version="1.0.0",
    )


def _make_environment() -> EnvironmentMetadata:
    return EnvironmentMetadata(
        hostname="test-host",
        python_version="3.11.0",
        bioetl_version="5.0.0",
    )


def _make_bronze_metadata() -> BronzeMetadata:
    return BronzeMetadata(
        version="1.1",
        layer=Layer.BRONZE,
        runtime=_make_runtime(),
        pipeline=_make_pipeline(),
        source=SourceMetadata(type="api", url="https://api.example.com"),
        output=BaseOutputMetadata(record_count=100),
        output_ext=BronzeOutputExt(
            files=[
                FileOutputMetadata(
                    path="batch.jsonl.zst",
                    size_bytes=1024,
                    record_count=100,
                )
            ],
            format="jsonl+zstd",
            compression="zstd",
        ),
        environment=_make_environment(),
    )


def _make_silver_metadata() -> SilverMetadata:
    return SilverMetadata(
        version="1.1",
        layer=Layer.SILVER,
        runtime=_make_runtime(),
        pipeline=_make_pipeline(),
        lineage=LineageMetadata(
            source_batch_ids=["batch-001"],
            bronze_paths=["bronze/path"],
        ),
        delta=DeltaMetrics(
            table_path="silver/chembl/activity",
            operation="merge",
            primary_key=["id"],
        ),
        output=BaseOutputMetadata(record_count=95),
        output_ext=SilverOutputExt(delta_version_before=0, delta_version_after=1),
        environment=_make_environment(),
    )


def _make_gold_metadata() -> GoldMetadata:
    return GoldMetadata(
        version="1.1",
        layer=Layer.GOLD,
        runtime=_make_runtime(),
        pipeline=_make_pipeline(),
        lineage=LineageMetadata(source_tables={"silver/chembl/activity": 1}),
        schema_info=SchemaMetadata(
            contract_path="docs/contracts/activity_v1.json",
            version="1.0",
            validation="strict",
        ),
        dq_summary=DQSummary(
            total_records=90, valid_records=90, validation_passed=True
        ),
        output=BaseOutputMetadata(record_count=90),
        output_ext=GoldOutputExt(partition_count=3, format="delta"),
        environment=_make_environment(),
    )


@pytest.mark.unit
class TestGetMetadataFilename:
    """Tests for _get_metadata_filename (line 53)."""

    def test_provider_and_entity_returns_named_file(self) -> None:
        """Line 52: both provider and entity generate named filename."""
        result = _get_metadata_filename("chembl", "activity")
        assert result == "chembl_activity_metadata.yaml"

    def test_no_provider_returns_default(self) -> None:
        """Line 53: missing provider returns _metadata.yaml."""
        result = _get_metadata_filename(None, "activity")
        assert result == METADATA_FILENAME

    def test_no_entity_returns_default(self) -> None:
        """Line 53: missing entity returns _metadata.yaml."""
        result = _get_metadata_filename("chembl", None)
        assert result == METADATA_FILENAME

    def test_both_none_returns_default(self) -> None:
        """Line 53: both None returns _metadata.yaml."""
        result = _get_metadata_filename(None, None)
        assert result == METADATA_FILENAME

    def test_empty_provider_returns_default(self) -> None:
        """Line 53: empty string provider treated as falsy."""
        result = _get_metadata_filename("", "activity")
        assert result == METADATA_FILENAME

    def test_empty_entity_returns_default(self) -> None:
        """Line 53: empty string entity treated as falsy."""
        result = _get_metadata_filename("chembl", "")
        assert result == METADATA_FILENAME


@pytest.mark.unit
class TestEmitRetryTelemetry:
    """Tests for _emit_retry_telemetry with metrics (line 94)."""

    @pytest.mark.asyncio
    async def test_emit_retry_telemetry_with_metrics(self) -> None:
        """Line 94: metrics.increment_counter called during retry."""
        logger = MagicMock()
        metrics = MagicMock()
        writer = MetadataWriter(
            logger=logger,
            metrics=metrics,
            atomic_replace_retry_policy=AdaptiveRetryPolicy(
                enabled=True,
                max_retries=2,
                base_delay_seconds=0.001,
                max_delay_seconds=0.01,
                jitter_seconds=0.0,
            ),
        )
        with patch(
            "bioetl.infrastructure.storage.metadata_writer.atomic_write_text",
            side_effect=_retry_once_atomic_write_text,
        ):
            await writer.write_bronze_metadata(
                "/virtual/bronze",
                _make_bronze_metadata(),
                provider="chembl",
                entity="activity",
            )

        # metrics should have been called
        assert metrics.increment_counter.call_count >= 1


@pytest.mark.unit
class TestEmitFinalTelemetry:
    """Tests for _emit_final_telemetry (lines 118, 136)."""

    def test_build_final_telemetry_outcome_keeps_status_mapping(self) -> None:
        """Outcome builder should keep canonical status->event/severity mapping."""
        from bioetl.infrastructure.storage.metadata.writer_operations import (
            _build_metadata_write_final_telemetry,
        )

        failed = _build_metadata_write_final_telemetry(
            status="failed",
            retry_count=2,
            final_reason="atomic_write_error",
        )
        succeeded = _build_metadata_write_final_telemetry(
            status="succeeded",
            retry_count=0,
            final_reason="success_without_retry",
        )

        assert failed.event_name == "metadata_write_failed"
        assert failed.severity == "error"
        assert succeeded.event_name == "metadata_write_completed"
        assert succeeded.severity == "info"

    def test_final_telemetry_outcome_encodes_event_name_and_severity(self) -> None:
        """Final telemetry outcome should keep canonical event/severity pairing."""
        from bioetl.infrastructure.storage.metadata.writer_operations import (
            _MetadataWriteFinalTelemetry,
        )

        failed = _MetadataWriteFinalTelemetry(
            event_name="metadata_write_failed",
            severity="error",
            retry_count=2,
            final_reason="atomic_write_error",
        )
        succeeded = _MetadataWriteFinalTelemetry(
            event_name="metadata_write_completed",
            severity="info",
            retry_count=0,
            final_reason="success_without_retry",
        )

        assert failed.event_name == "metadata_write_failed"
        assert failed.severity == "error"
        assert succeeded.event_name == "metadata_write_completed"
        assert succeeded.severity == "info"

    @pytest.mark.asyncio
    async def test_final_telemetry_failed_path_uses_error(self, tmp_path: Path) -> None:
        """Line 118: status='failed' calls logger.error."""
        logger = MagicMock()
        writer = MetadataWriter(logger=logger)

        base_path = Path("/virtual/bronze")

        with patch(
            "bioetl.infrastructure.storage.metadata_writer.atomic_write_text",
            side_effect=AtomicWriteError(base_path / "test.yaml", "simulated_error"),
        ):
            with pytest.raises(AtomicWriteError):
                await writer.write_bronze_metadata(base_path, _make_bronze_metadata())

        error_calls = [
            call
            for call in logger.error.call_args_list
            if call.args and call.args[0] == "metadata_write_failed"
        ]
        assert len(error_calls) >= 1
        # status is not passed as kwarg to logger — it routes to error vs info
        assert "final_reason" in error_calls[0].kwargs

    @pytest.mark.asyncio
    async def test_final_telemetry_succeeded_path_uses_info(self) -> None:
        """Line 127-133: status='succeeded' calls logger.info."""
        logger = MagicMock()
        writer = MetadataWriter(logger=logger)

        with patch(
            "bioetl.infrastructure.storage.metadata_writer.atomic_write_text",
            side_effect=_fake_atomic_write_text,
        ):
            await writer.write_bronze_metadata(
                "/virtual/bronze", _make_bronze_metadata()
            )

        info_calls = [
            call
            for call in logger.info.call_args_list
            if call.args and call.args[0] == "metadata_write_completed"
        ]
        assert len(info_calls) >= 1

    @pytest.mark.asyncio
    async def test_emit_final_telemetry_with_metrics_on_success(self) -> None:
        """Line 136: metrics.increment_counter called on successful write."""
        logger = MagicMock()
        metrics = MagicMock()
        writer = MetadataWriter(logger=logger, metrics=metrics)

        with patch(
            "bioetl.infrastructure.storage.metadata_writer.atomic_write_text",
            side_effect=_fake_atomic_write_text,
        ):
            await writer.write_bronze_metadata(
                "/virtual/bronze", _make_bronze_metadata()
            )

        assert metrics.increment_counter.call_count >= 1

    @pytest.mark.asyncio
    async def test_emit_final_telemetry_with_metrics_on_failure(self) -> None:
        """Line 136: metrics.increment_counter called on failed write."""
        logger = MagicMock()
        metrics = MagicMock()
        writer = MetadataWriter(logger=logger, metrics=metrics)
        base_path = Path("/virtual/bronze")

        with patch(
            "bioetl.infrastructure.storage.metadata_writer.atomic_write_text",
            side_effect=AtomicWriteError(base_path / "test.yaml", "simulated"),
        ):
            with pytest.raises(AtomicWriteError):
                await writer.write_bronze_metadata(base_path, _make_bronze_metadata())

        assert metrics.increment_counter.call_count >= 1


@pytest.mark.unit
class TestWriteMetadataPathLogic:
    """Tests for _write_metadata path resolution (lines 263)."""

    @pytest.mark.asyncio
    async def test_flat_structure_with_table_name_uses_table_name_path(self) -> None:
        """Line 262-263: flat_structure + table_name uses {table_name}_metadata.yaml."""

        writer = MetadataWriter(logger=NoOpLogger())
        base_path = Path("/virtual/silver")

        with patch(
            "bioetl.infrastructure.storage.metadata_writer.atomic_write_text",
            side_effect=_fake_atomic_write_text,
        ):
            result = await writer.write_silver_metadata(
                base_path,
                _make_silver_metadata(),
                table_name="chembl_activity",
                flat_structure=True,
            )

        expected_path = base_path / "chembl_activity_metadata.yaml"
        assert result == str(expected_path.resolve())

    @pytest.mark.asyncio
    async def test_flat_structure_without_table_name_uses_default(self) -> None:
        """Line 265: flat_structure=True but no table_name falls back to default."""
        writer = MetadataWriter(logger=NoOpLogger())
        base_path = Path("/virtual/silver")

        with patch(
            "bioetl.infrastructure.storage.metadata_writer.atomic_write_text",
            side_effect=_fake_atomic_write_text,
        ):
            result = await writer.write_silver_metadata(
                base_path,
                _make_silver_metadata(),
                flat_structure=True,
            )

        expected_path = base_path / METADATA_FILENAME
        assert result == str(expected_path.resolve())

    @pytest.mark.asyncio
    async def test_provider_entity_overrides_flat_structure(self) -> None:
        """Lines 258-260: provider+entity takes priority over flat_structure."""
        writer = MetadataWriter(logger=NoOpLogger())
        base_path = Path("/virtual/gold")

        with patch(
            "bioetl.infrastructure.storage.metadata_writer.atomic_write_text",
            side_effect=_fake_atomic_write_text,
        ):
            result = await writer.write_gold_metadata(
                base_path,
                _make_gold_metadata(),
                provider="chembl",
                entity="activity",
                flat_structure=True,
                table_name="chembl_activity",
            )

        expected_path = base_path / "chembl_activity_metadata.yaml"
        assert result == str(expected_path.resolve())

    @pytest.mark.asyncio
    async def test_pipeline_label_uses_provider_entity_when_available(self) -> None:
        """Line 279: pipeline_label built from provider.entity."""
        logger = MagicMock()
        writer = MetadataWriter(logger=logger)

        with patch(
            "bioetl.infrastructure.storage.metadata_writer.atomic_write_text",
            side_effect=_fake_atomic_write_text,
        ):
            await writer.write_bronze_metadata(
                "/virtual/bronze",
                _make_bronze_metadata(),
                provider="chembl",
                entity="activity",
            )

        # Check logger was called with metadata_write_completed
        info_calls = [
            call
            for call in logger.info.call_args_list
            if call.args and call.args[0] == "metadata_write_completed"
        ]
        assert len(info_calls) >= 1
        # pipeline label should be chembl.activity
        assert info_calls[0].kwargs.get("pipeline") == "chembl.activity"

    @pytest.mark.asyncio
    async def test_pipeline_label_uses_layer_when_no_provider_entity(self) -> None:
        """Line 279: pipeline_label falls back to {layer}_metadata."""
        logger = MagicMock()
        writer = MetadataWriter(logger=logger)

        with patch(
            "bioetl.infrastructure.storage.metadata_writer.atomic_write_text",
            side_effect=_fake_atomic_write_text,
        ):
            await writer.write_bronze_metadata(
                "/virtual/bronze", _make_bronze_metadata()
            )

        info_calls = [
            call
            for call in logger.info.call_args_list
            if call.args and call.args[0] == "metadata_write_completed"
        ]
        assert len(info_calls) >= 1
        # pipeline label should be bronze_metadata
        assert info_calls[0].kwargs.get("pipeline") == "bronze_metadata"

    @pytest.mark.asyncio
    async def test_metadata_written_log_uses_resolved_operation_context(self) -> None:
        """metadata_written log keeps layer, path, and run_id after request wrapping."""
        logger = MagicMock()
        writer = MetadataWriter(logger=logger)
        metadata = _make_gold_metadata()
        base_path = Path("/virtual/gold")

        with patch(
            "bioetl.infrastructure.storage.metadata_writer.atomic_write_text",
            side_effect=_fake_atomic_write_text,
        ):
            result = await writer.write_gold_metadata(
                base_path,
                metadata,
                provider="chembl",
                entity="activity",
            )

        written_calls = [
            call
            for call in logger.info.call_args_list
            if call.args and call.args[0] == "metadata_written"
        ]
        assert len(written_calls) == 1
        assert written_calls[0].kwargs == {
            "layer": "gold",
            "path": str(base_path / "chembl_activity_metadata.yaml"),
            "run_id": metadata.runtime.run_id,
            "dataset_ref": "gold:chembl.activity",
            "lineage_fragment_id": None,
        }
        assert result == str((base_path / "chembl_activity_metadata.yaml").resolve())

    @pytest.mark.asyncio
    async def test_success_after_retry_final_reason(self) -> None:
        """Lines 306-315: final_reason = 'success_after_retry' when retry_count > 0."""
        logger = MagicMock()
        writer = MetadataWriter(
            logger=logger,
            atomic_replace_retry_policy=AdaptiveRetryPolicy(
                enabled=True,
                max_retries=2,
                base_delay_seconds=0.001,
                max_delay_seconds=0.01,
                jitter_seconds=0.0,
            ),
        )
        with patch(
            "bioetl.infrastructure.storage.metadata_writer.atomic_write_text",
            side_effect=_retry_once_atomic_write_text,
        ):
            await writer.write_bronze_metadata(
                "/virtual/bronze", _make_bronze_metadata()
            )

        info_calls = [
            call
            for call in logger.info.call_args_list
            if call.args and call.args[0] == "metadata_write_completed"
        ]
        assert len(info_calls) >= 1
        assert info_calls[0].kwargs["final_reason"] == "success_after_retry"

    @pytest.mark.asyncio
    async def test_success_without_retry_final_reason(self) -> None:
        """Lines 306-315: final_reason = 'success_without_retry' on clean write."""
        logger = MagicMock()
        writer = MetadataWriter(logger=logger)

        with patch(
            "bioetl.infrastructure.storage.metadata_writer.atomic_write_text",
            side_effect=_fake_atomic_write_text,
        ):
            await writer.write_bronze_metadata(
                "/virtual/bronze", _make_bronze_metadata()
            )

        info_calls = [
            call
            for call in logger.info.call_args_list
            if call.args and call.args[0] == "metadata_write_completed"
        ]
        assert len(info_calls) >= 1
        assert info_calls[0].kwargs["final_reason"] == "success_without_retry"

    @pytest.mark.asyncio
    async def test_write_metadata_delegates_prepared_operation_execution(self) -> None:
        """_write_metadata should pass one prepared operation into the execution helper."""
        from bioetl.infrastructure.storage.metadata.writer_operations import (
            _MetadataWriteRequest,
        )

        writer = MetadataWriter(logger=NoOpLogger())
        request = _MetadataWriteRequest(
            base_path=Path("/virtual/gold"),
            metadata=_make_gold_metadata(),
            layer="gold",
            provider="chembl",
            entity="activity",
        )

        with patch(
            "bioetl.infrastructure.storage.metadata_writer._execute_prepared_metadata_write_operation",
            new_callable=AsyncMock,
        ) as mock_execute:
            mock_execute.return_value = "ok"
            result = await writer._write_metadata(request)

        assert result == "ok"
        _, kwargs = mock_execute.call_args
        assert kwargs["operation"].prepared_write.pipeline_label == "chembl.activity"
        assert kwargs["operation"].telemetry_context.pipeline == "chembl.activity"
