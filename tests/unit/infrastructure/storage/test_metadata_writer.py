"""Unit tests for MetadataWriter."""

from __future__ import annotations

import errno
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from tests.helpers.deterministic_ids import deterministic_uuid_string_from_callsite

import pytest

from tests.helpers.metadata_fixtures import (
    BRONZE_BASE_PATH,
    GOLD_BASE_PATH,
    SILVER_BASE_PATH,
    SILVER_TABLE_PATH,
    bronze_metadata,
    environment_metadata,
    gold_metadata,
    metadata_writer,
    pipeline_metadata,
    runtime_metadata,
    silver_metadata,
)  # noqa: F401

from bioetl.domain.models.metadata import (
    BronzeMetadata,
    DQSummary,
    GoldMetadata,
    RuntimeMetadata,
    RunTypeEnum,
    SilverMetadata,
)
from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter
from bioetl.infrastructure.storage.delta.resilience import AdaptiveRetryPolicy
from bioetl.infrastructure.storage.support.atomic_ops import ReplaceRetryHook


@pytest.mark.unit
class TestMetadataWriter:
    """Tests for MetadataWriter."""

    @pytest.mark.asyncio
    async def test_metadata_writer_emits_retry_telemetry(
        self,
        bronze_metadata: BronzeMetadata,
    ) -> None:
        """Metadata writer should emit retry telemetry without real disk writes."""
        logger = MagicMock()
        writer = MetadataWriter(
            logger=logger,
            atomic_replace_retry_policy=AdaptiveRetryPolicy(
                enabled=True,
                max_retries=2,
                base_delay_seconds=0.01,
                max_delay_seconds=0.1,
                jitter_seconds=0.0,
                adaptive=True,
            ),
        )

        def fake_atomic_write_text(
            path: object,
            content: object,
            *,
            retry_policy: AdaptiveRetryPolicy,
            on_retry: ReplaceRetryHook | None,
        ) -> None:
            del path, content, retry_policy
            assert on_retry is not None
            on_retry(1, 0.01, OSError(errno.EBUSY, "Device or resource busy"))

        with patch(
            "bioetl.infrastructure.storage.metadata_writer.atomic_write_text",
            side_effect=fake_atomic_write_text,
        ):
            await writer.write_bronze_metadata(BRONZE_BASE_PATH, bronze_metadata)

        retry_calls = [
            call
            for call in logger.warning.call_args_list
            if call.args and call.args[0] == "metadata_atomic_replace_retry"
        ]
        assert retry_calls

        completion_calls = [
            call
            for call in logger.info.call_args_list
            if call.args and call.args[0] == "metadata_write_completed"
        ]
        assert completion_calls
        assert completion_calls[-1].kwargs["final_reason"] == "success_after_retry"

    @pytest.mark.asyncio
    async def test_writer_metadata_writer__aclose_is_idempotent__fcefbe68(
        self,
        metadata_writer: MetadataWriter,
    ) -> None:
        """Test that aclose can be called multiple times."""
        await metadata_writer.aclose()
        await metadata_writer.aclose()
        # No exception should be raised


@pytest.mark.unit
class TestMetadataWriterOperationPreparation:
    """Tests for prepared metadata operation handoff."""

    def test_prepare_metadata_write_operation_keeps_run_id_and_pipeline(
        self,
        bronze_metadata: BronzeMetadata,
    ) -> None:
        """Prepared operation should preserve runtime run_id and telemetry pipeline."""
        from bioetl.infrastructure.storage.metadata.writer_operations import (
            _MetadataWriteRequest,
            _prepare_metadata_write_operation,
        )

        operation = _prepare_metadata_write_operation(
            _MetadataWriteRequest(
                base_path=BRONZE_BASE_PATH,
                metadata=bronze_metadata,
                layer="bronze",
                provider="chembl",
                entity="activity",
            )
        )

        assert operation.run_id == bronze_metadata.runtime.run_id
        assert operation.telemetry_context.pipeline == "chembl.activity"

    def test_build_metadata_write_request_keeps_layer_and_identifiers(
        self,
        metadata_writer: MetadataWriter,
        silver_metadata: SilverMetadata,
    ) -> None:
        """Public metadata methods should share one normalized request builder."""
        request = metadata_writer._build_metadata_write_request(
            base_path=SILVER_TABLE_PATH,
            metadata=silver_metadata,
            layer="silver",
            table_name="chembl_activity",
            flat_structure=True,
            provider="chembl",
            entity="activity",
        )

        assert request.layer == "silver"
        assert request.table_name == "chembl_activity"
        assert request.flat_structure is True
        assert request.provider == "chembl"
        assert request.entity == "activity"


@pytest.mark.unit
class TestNoOpMetadataWriter:
    """Tests for NoOpMetadataWriter."""

    @pytest.mark.asyncio
    async def test_noop_write_bronze_returns_empty(
        self,
        bronze_metadata: BronzeMetadata,
    ) -> None:
        """Test NoOp Bronze write returns empty string."""
        writer = NoOpMetadataWriter()
        result = await writer.write_bronze_metadata(BRONZE_BASE_PATH, bronze_metadata)
        assert result == ""

    @pytest.mark.asyncio
    async def test_noop_write_silver_returns_empty(
        self,
        silver_metadata: SilverMetadata,
    ) -> None:
        """Test NoOp Silver write returns empty string."""
        writer = NoOpMetadataWriter()
        result = await writer.write_silver_metadata(SILVER_BASE_PATH, silver_metadata)
        assert result == ""

    @pytest.mark.asyncio
    async def test_noop_write_gold_returns_empty(
        self,
        gold_metadata: GoldMetadata,
    ) -> None:
        """Test NoOp Gold write returns empty string."""
        writer = NoOpMetadataWriter()
        result = await writer.write_gold_metadata(GOLD_BASE_PATH, gold_metadata)
        assert result == ""

    @pytest.mark.asyncio
    async def test_noop_finalize_methods_return_empty(
        self,
    ) -> None:
        """Test NoOp finalize helpers return empty strings."""
        writer = NoOpMetadataWriter()
        assert await writer.finalize_silver_metadata(SILVER_BASE_PATH) == ""
        assert await writer.finalize_gold_metadata(GOLD_BASE_PATH) == ""

    @pytest.mark.asyncio
    async def test_noop_aclose_is_idempotent(self) -> None:
        """Test NoOp aclose can be called multiple times."""
        writer = NoOpMetadataWriter()
        await writer.aclose()
        await writer.aclose()


@pytest.mark.unit
class TestMetadataModels:
    """Tests for metadata Pydantic models."""

    def test_bronze_metadata_serialization(
        self,
        bronze_metadata: BronzeMetadata,
    ) -> None:
        """Test Bronze metadata can be serialized to dict."""
        data = bronze_metadata.model_dump(mode="json")

        assert data["version"] == "1.1"  # ADR-029 version bump
        assert data["layer"] == "bronze"
        assert data["runtime"]["run_type"] == "incremental"
        assert "started_at_utc" in data["runtime"]

    def test_writer_metadata_models__serialization__906c269c(
        self,
        silver_metadata: SilverMetadata,
    ) -> None:
        """Test Silver metadata can be serialized to dict."""
        data = silver_metadata.model_dump(mode="json")

        assert data["version"] == "1.1"  # ADR-029 version bump
        assert data["layer"] == "silver"
        assert "lineage" in data
        assert "delta" in data
        assert "dq_summary" in data

    def test_writer_metadata_models__serialization__6554bbad(
        self,
        gold_metadata: GoldMetadata,
    ) -> None:
        """Test Gold metadata can be serialized to dict."""
        data = gold_metadata.model_dump(mode="json", by_alias=True)

        assert data["version"] == "1.1"  # ADR-029 version bump
        assert data["layer"] == "gold"
        assert "schema" in data  # Uses alias
        assert "dq_summary" in data

    def test_dq_summary_null_rates_property(self) -> None:
        """Test DQSummary null_rates property."""
        from bioetl.domain.models.metadata import ColumnMetrics

        dq = DQSummary(
            total_records=100,
            valid_records=95,
            column_metrics={
                "activity_id": ColumnMetrics(null_rate=0.0),
                "standard_value": ColumnMetrics(null_rate=0.12),
            },
        )

        null_rates = dq.null_rates
        assert null_rates["activity_id"] == pytest.approx(0.0)
        assert null_rates["standard_value"] == pytest.approx(0.12)

    def test_runtime_metadata_datetime_serialization(self) -> None:
        """Test datetime fields are serialized as ISO strings."""
        runtime = RuntimeMetadata(
            run_id=deterministic_uuid_string_from_callsite("test_metadata_writer"),
            run_type=RunTypeEnum.INCREMENTAL,
            started_at_utc=datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
            completed_at_utc=datetime(2025, 1, 15, 10, 5, 0, tzinfo=UTC),
        )

        data = runtime.model_dump(mode="json")

        assert "2025-01-15" in data["started_at_utc"]
        assert "10:00:00" in data["started_at_utc"]
