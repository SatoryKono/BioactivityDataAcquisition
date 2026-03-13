"""Coverage boost tests for metadata_writer.py.

Targets uncovered lines: 53, 94, 118, 136, 263, 306-315.
"""

from __future__ import annotations

import errno
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
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
from bioetl.infrastructure.storage._atomic import AtomicWriteError
from bioetl.infrastructure.storage.metadata_writer import (
    METADATA_FILENAME,
    MetadataWriter,
    _get_metadata_filename,
)
from bioetl.infrastructure.storage.write_resilience import AdaptiveRetryPolicy


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
    async def test_emit_retry_telemetry_with_metrics(self, tmp_path: Path) -> None:
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
        base_path = tmp_path / "bronze"
        base_path.mkdir(parents=True)

        original_replace = Path.replace
        call_count = {"count": 0}

        def flaky_replace(self: Path, target_path: Path) -> Path:
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise OSError(errno.EBUSY, "busy")
            return original_replace(self, target_path)

        with (
            patch.object(Path, "replace", flaky_replace),
            patch("bioetl.infrastructure.storage._atomic.time.sleep"),
        ):
            await writer.write_bronze_metadata(
                base_path, _make_bronze_metadata(), provider="chembl", entity="activity"
            )

        # metrics should have been called
        assert metrics.increment_counter.call_count >= 1


@pytest.mark.unit
class TestEmitFinalTelemetry:
    """Tests for _emit_final_telemetry (lines 118, 136)."""

    @pytest.mark.asyncio
    async def test_final_telemetry_failed_path_uses_error(self, tmp_path: Path) -> None:
        """Line 118: status='failed' calls logger.error."""
        logger = MagicMock()
        writer = MetadataWriter(logger=logger)

        base_path = tmp_path / "bronze"
        base_path.mkdir(parents=True)

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
    async def test_final_telemetry_succeeded_path_uses_info(
        self, tmp_path: Path
    ) -> None:
        """Line 127-133: status='succeeded' calls logger.info."""
        logger = MagicMock()
        writer = MetadataWriter(logger=logger)
        base_path = tmp_path / "bronze"
        base_path.mkdir(parents=True)

        await writer.write_bronze_metadata(base_path, _make_bronze_metadata())

        info_calls = [
            call
            for call in logger.info.call_args_list
            if call.args and call.args[0] == "metadata_write_completed"
        ]
        assert len(info_calls) >= 1

    @pytest.mark.asyncio
    async def test_emit_final_telemetry_with_metrics_on_success(
        self, tmp_path: Path
    ) -> None:
        """Line 136: metrics.increment_counter called on successful write."""
        logger = MagicMock()
        metrics = MagicMock()
        writer = MetadataWriter(logger=logger, metrics=metrics)
        base_path = tmp_path / "bronze"
        base_path.mkdir(parents=True)

        await writer.write_bronze_metadata(base_path, _make_bronze_metadata())

        assert metrics.increment_counter.call_count >= 1

    @pytest.mark.asyncio
    async def test_emit_final_telemetry_with_metrics_on_failure(
        self, tmp_path: Path
    ) -> None:
        """Line 136: metrics.increment_counter called on failed write."""
        logger = MagicMock()
        metrics = MagicMock()
        writer = MetadataWriter(logger=logger, metrics=metrics)
        base_path = tmp_path / "bronze"
        base_path.mkdir(parents=True)

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
    async def test_flat_structure_with_table_name_uses_table_name_path(
        self, tmp_path: Path
    ) -> None:
        """Line 262-263: flat_structure + table_name uses {table_name}_metadata.yaml."""
        writer = MetadataWriter(logger=NoOpLogger())
        base_path = tmp_path / "silver"
        base_path.mkdir(parents=True)

        result = await writer.write_silver_metadata(
            base_path,
            _make_silver_metadata(),
            table_name="chembl_activity",
            flat_structure=True,
        )

        expected_path = base_path / "chembl_activity_metadata.yaml"
        assert expected_path.exists()
        assert result == str(expected_path.resolve())

    @pytest.mark.asyncio
    async def test_flat_structure_without_table_name_uses_default(
        self, tmp_path: Path
    ) -> None:
        """Line 265: flat_structure=True but no table_name falls back to default."""
        writer = MetadataWriter(logger=NoOpLogger())
        base_path = tmp_path / "silver"
        base_path.mkdir(parents=True)

        result = await writer.write_silver_metadata(
            base_path,
            _make_silver_metadata(),
            flat_structure=True,
        )

        expected_path = base_path / METADATA_FILENAME
        assert expected_path.exists()
        assert result == str(expected_path.resolve())

    @pytest.mark.asyncio
    async def test_provider_entity_overrides_flat_structure(
        self, tmp_path: Path
    ) -> None:
        """Lines 258-260: provider+entity takes priority over flat_structure."""
        writer = MetadataWriter(logger=NoOpLogger())
        base_path = tmp_path / "gold"
        base_path.mkdir(parents=True)

        result = await writer.write_gold_metadata(
            base_path,
            _make_gold_metadata(),
            provider="chembl",
            entity="activity",
            flat_structure=True,
            table_name="chembl_activity",
        )

        expected_path = base_path / "chembl_activity_metadata.yaml"
        assert expected_path.exists()
        assert result == str(expected_path.resolve())

    @pytest.mark.asyncio
    async def test_pipeline_label_uses_provider_entity_when_available(
        self, tmp_path: Path
    ) -> None:
        """Line 279: pipeline_label built from provider.entity."""
        logger = MagicMock()
        writer = MetadataWriter(logger=logger)
        base_path = tmp_path / "bronze"
        base_path.mkdir(parents=True)

        await writer.write_bronze_metadata(
            base_path,
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
    async def test_pipeline_label_uses_layer_when_no_provider_entity(
        self, tmp_path: Path
    ) -> None:
        """Line 279: pipeline_label falls back to {layer}_metadata."""
        logger = MagicMock()
        writer = MetadataWriter(logger=logger)
        base_path = tmp_path / "bronze"
        base_path.mkdir(parents=True)

        await writer.write_bronze_metadata(base_path, _make_bronze_metadata())

        info_calls = [
            call
            for call in logger.info.call_args_list
            if call.args and call.args[0] == "metadata_write_completed"
        ]
        assert len(info_calls) >= 1
        # pipeline label should be bronze_metadata
        assert info_calls[0].kwargs.get("pipeline") == "bronze_metadata"

    @pytest.mark.asyncio
    async def test_metadata_written_log_uses_resolved_operation_context(
        self, tmp_path: Path
    ) -> None:
        """metadata_written log keeps layer, path, and run_id after request wrapping."""
        logger = MagicMock()
        writer = MetadataWriter(logger=logger)
        metadata = _make_gold_metadata()
        base_path = tmp_path / "gold"
        base_path.mkdir(parents=True)

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
        }
        assert result == str((base_path / "chembl_activity_metadata.yaml").resolve())

    @pytest.mark.asyncio
    async def test_success_after_retry_final_reason(self, tmp_path: Path) -> None:
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
        base_path = tmp_path / "bronze"
        base_path.mkdir(parents=True)

        original_replace = Path.replace
        call_count = {"count": 0}

        def flaky_replace(self: Path, target_path: Path) -> Path:
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise OSError(errno.EBUSY, "busy")
            return original_replace(self, target_path)

        with (
            patch.object(Path, "replace", flaky_replace),
            patch("bioetl.infrastructure.storage._atomic.time.sleep"),
        ):
            await writer.write_bronze_metadata(base_path, _make_bronze_metadata())

        info_calls = [
            call
            for call in logger.info.call_args_list
            if call.args and call.args[0] == "metadata_write_completed"
        ]
        assert len(info_calls) >= 1
        assert info_calls[0].kwargs["final_reason"] == "success_after_retry"

    @pytest.mark.asyncio
    async def test_success_without_retry_final_reason(self, tmp_path: Path) -> None:
        """Lines 306-315: final_reason = 'success_without_retry' on clean write."""
        logger = MagicMock()
        writer = MetadataWriter(logger=logger)
        base_path = tmp_path / "bronze"
        base_path.mkdir(parents=True)

        await writer.write_bronze_metadata(base_path, _make_bronze_metadata())

        info_calls = [
            call
            for call in logger.info.call_args_list
            if call.args and call.args[0] == "metadata_write_completed"
        ]
        assert len(info_calls) >= 1
        assert info_calls[0].kwargs["final_reason"] == "success_without_retry"
