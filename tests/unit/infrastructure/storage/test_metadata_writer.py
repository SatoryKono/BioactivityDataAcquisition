"""Unit tests for MetadataWriter."""

from __future__ import annotations

import errno
from datetime import UTC, datetime
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
from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter
from bioetl.infrastructure.storage.delta.resilience import AdaptiveRetryPolicy

BRONZE_BASE_PATH = "/virtual/bronze"
SILVER_TABLE_PATH = "/virtual/silver/test/table"
SILVER_BASE_PATH = "/virtual/silver"
GOLD_BASE_PATH = "/virtual/gold"


@pytest.fixture
def metadata_writer(noop_logger: NoOpLogger) -> MetadataWriter:
    """Create MetadataWriter instance."""
    return MetadataWriter(logger=noop_logger)


@pytest.fixture
def runtime_metadata() -> RuntimeMetadata:
    """Create sample runtime metadata."""
    return RuntimeMetadata(
        run_id=str(uuid4()),
        run_type=RunTypeEnum.INCREMENTAL,
        started_at_utc=datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
        completed_at_utc=datetime(2025, 1, 15, 10, 5, 0, tzinfo=UTC),
        duration_seconds=300.0,
    )


@pytest.fixture
def pipeline_metadata() -> PipelineMetadata:
    """Create sample pipeline metadata."""
    return PipelineMetadata(
        name="chembl_activity",
        provider="chembl",
        entity="activity",
        version="1.2.0",
        git_commit="abc123def",
        config_hash="sha256:xyz789",
    )


@pytest.fixture
def environment_metadata() -> EnvironmentMetadata:
    """Create sample environment metadata."""
    return EnvironmentMetadata(
        hostname="worker-01",
        python_version="3.11.5",
        bioetl_version="5.0.5",
    )


@pytest.fixture
def bronze_metadata(
    runtime_metadata: RuntimeMetadata,
    pipeline_metadata: PipelineMetadata,
    environment_metadata: EnvironmentMetadata,
) -> BronzeMetadata:
    """Create sample Bronze metadata."""
    return BronzeMetadata(
        version="1.1",
        layer=Layer.BRONZE,
        runtime=runtime_metadata,
        pipeline=pipeline_metadata,
        source=SourceMetadata(
            type="api",
            url="https://www.ebi.ac.uk/chembl/api/data/activity",
            api_version="33",
        ),
        output=BaseOutputMetadata(
            record_count=10000,
            total_bytes=1048576,
        ),
        output_ext=BronzeOutputExt(
            files=[
                FileOutputMetadata(
                    path="batch_001.jsonl.zst",
                    size_bytes=1048576,
                    record_count=10000,
                    checksum_blake2="abc123",
                ),
            ],
            format="jsonl+zstd",
            compression="zstd",
        ),
        environment=environment_metadata,
    )


@pytest.fixture
def silver_metadata(
    runtime_metadata: RuntimeMetadata,
    pipeline_metadata: PipelineMetadata,
    environment_metadata: EnvironmentMetadata,
) -> SilverMetadata:
    """Create sample Silver metadata."""
    return SilverMetadata(
        version="1.1",
        layer=Layer.SILVER,
        runtime=runtime_metadata,
        pipeline=pipeline_metadata,
        lineage=LineageMetadata(
            source_batch_ids=["batch-uuid-001"],
            bronze_paths=["bronze/v1/chembl/activity/2025-01-15/batch_001.jsonl.zst"],
            transform_version="1.2.0",
            transform_steps=["normalize_units", "validate_smiles"],
        ),
        delta=DeltaMetrics(
            table_path="silver/chembl/activity/",
            operation="merge",
            primary_key=["activity_id"],
            version_before=42,
            version_after=43,
            rows_inserted=5000,
            rows_updated=2000,
        ),
        dq_summary=DQSummary(
            total_records=15000,
            valid_records=14250,
            error_records=750,
            error_rate=0.05,
        ),
        output=BaseOutputMetadata(
            record_count=14250,
            content_hash="sha256:abc123",
        ),
        output_ext=SilverOutputExt(
            delta_version_before=42,
            delta_version_after=43,
        ),
        environment=environment_metadata,
    )


@pytest.fixture
def gold_metadata(
    runtime_metadata: RuntimeMetadata,
    pipeline_metadata: PipelineMetadata,
    environment_metadata: EnvironmentMetadata,
) -> GoldMetadata:
    """Create sample Gold metadata."""
    return GoldMetadata(
        version="1.1",
        layer=Layer.GOLD,
        runtime=runtime_metadata,
        pipeline=pipeline_metadata,
        lineage=LineageMetadata(
            source_tables={"silver/chembl/activity": 43},
        ),
        schema_info=SchemaMetadata(
            contract_path="docs/contracts/gold/activity_v1.0.json",
            version="1.0",
            validation="strict",
        ),
        dq_summary=DQSummary(
            total_records=1250,
            valid_records=1250,
            validation_passed=True,
        ),
        output=BaseOutputMetadata(
            record_count=1250,
            total_bytes=10485760,
        ),
        output_ext=GoldOutputExt(
            partition_count=50,
            format="delta",
        ),
        environment=environment_metadata,
    )


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
            retry_policy: object,
            on_retry: object,
        ) -> None:
            del path, content, retry_policy
            assert callable(on_retry)
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
    async def test_aclose_is_idempotent(
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

    def test_silver_metadata_serialization(
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

    def test_gold_metadata_serialization(
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
            run_id=str(uuid4()),
            run_type=RunTypeEnum.INCREMENTAL,
            started_at_utc=datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
            completed_at_utc=datetime(2025, 1, 15, 10, 5, 0, tzinfo=UTC),
        )

        data = runtime.model_dump(mode="json")

        assert "2025-01-15" in data["started_at_utc"]
        assert "10:00:00" in data["started_at_utc"]
