"""Unit tests for MetadataWriter."""

from __future__ import annotations

import errno
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import yaml

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
from bioetl.infrastructure.storage.metadata_writer import (
    METADATA_FILENAME,
    MetadataWriter,
)
from bioetl.infrastructure.storage.delta.resilience import AdaptiveRetryPolicy


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
    async def test_write_bronze_metadata_creates_file(
        self,
        tmp_path: Path,
        metadata_writer: MetadataWriter,
        bronze_metadata: BronzeMetadata,
    ) -> None:
        """Test that write_bronze_metadata creates _metadata.yaml."""
        base_path = tmp_path / "bronze" / "v1" / "chembl" / "activity" / "2025-01-15"
        base_path.mkdir(parents=True)

        result = await metadata_writer.write_bronze_metadata(base_path, bronze_metadata)

        metadata_path = base_path / METADATA_FILENAME
        assert metadata_path.exists()
        assert result == str(metadata_path.resolve())

    @pytest.mark.asyncio
    async def test_write_bronze_metadata_valid_yaml(
        self,
        tmp_path: Path,
        metadata_writer: MetadataWriter,
        bronze_metadata: BronzeMetadata,
    ) -> None:
        """Test that Bronze metadata is valid YAML."""
        base_path = tmp_path / "bronze"
        base_path.mkdir(parents=True)

        await metadata_writer.write_bronze_metadata(base_path, bronze_metadata)

        metadata_path = base_path / METADATA_FILENAME
        content = yaml.safe_load(metadata_path.read_text())

        assert content["version"] == "1.1"  # ADR-029 version bump
        assert content["layer"] == "bronze"
        assert content["pipeline"]["name"] == "chembl_activity"
        assert content["pipeline"]["provider"] == "chembl"
        assert content["source"]["type"] == "api"
        assert content["output"]["record_count"] == 10000  # ADR-029: unified field name

    @pytest.mark.asyncio
    async def test_write_silver_metadata_creates_file(
        self,
        tmp_path: Path,
        metadata_writer: MetadataWriter,
        silver_metadata: SilverMetadata,
    ) -> None:
        """Test that write_silver_metadata creates _metadata.yaml."""
        base_path = tmp_path / "silver" / "chembl" / "activity"
        base_path.mkdir(parents=True)

        result = await metadata_writer.write_silver_metadata(base_path, silver_metadata)

        metadata_path = base_path / METADATA_FILENAME
        assert metadata_path.exists()
        assert result == str(metadata_path.resolve())

    @pytest.mark.asyncio
    async def test_write_silver_metadata_includes_lineage(
        self,
        tmp_path: Path,
        metadata_writer: MetadataWriter,
        silver_metadata: SilverMetadata,
    ) -> None:
        """Test that Silver metadata includes lineage information."""
        base_path = tmp_path / "silver"
        base_path.mkdir(parents=True)

        await metadata_writer.write_silver_metadata(base_path, silver_metadata)

        metadata_path = base_path / METADATA_FILENAME
        content = yaml.safe_load(metadata_path.read_text())

        assert "lineage" in content
        assert "source_batch_ids" in content["lineage"]
        assert "bronze_paths" in content["lineage"]
        assert "transform_steps" in content["lineage"]

    @pytest.mark.asyncio
    async def test_write_silver_metadata_includes_dq_summary(
        self,
        tmp_path: Path,
        metadata_writer: MetadataWriter,
        silver_metadata: SilverMetadata,
    ) -> None:
        """Test that Silver metadata includes DQ summary."""
        base_path = tmp_path / "silver"
        base_path.mkdir(parents=True)

        await metadata_writer.write_silver_metadata(base_path, silver_metadata)

        metadata_path = base_path / METADATA_FILENAME
        content = yaml.safe_load(metadata_path.read_text())

        assert "dq_summary" in content
        assert content["dq_summary"]["total_records"] == 15000
        assert content["dq_summary"]["error_rate"] == pytest.approx(0.05)

    @pytest.mark.asyncio
    async def test_write_gold_metadata_creates_file(
        self,
        tmp_path: Path,
        metadata_writer: MetadataWriter,
        gold_metadata: GoldMetadata,
    ) -> None:
        """Test that write_gold_metadata creates _metadata.yaml."""
        base_path = tmp_path / "gold" / "chembl" / "activity_aggregated"
        base_path.mkdir(parents=True)

        result = await metadata_writer.write_gold_metadata(base_path, gold_metadata)

        metadata_path = base_path / METADATA_FILENAME
        assert metadata_path.exists()
        assert result == str(metadata_path.resolve())

    @pytest.mark.asyncio
    async def test_write_gold_metadata_includes_schema_contract(
        self,
        tmp_path: Path,
        metadata_writer: MetadataWriter,
        gold_metadata: GoldMetadata,
    ) -> None:
        """Test that Gold metadata includes schema contract reference."""
        base_path = tmp_path / "gold"
        base_path.mkdir(parents=True)

        await metadata_writer.write_gold_metadata(base_path, gold_metadata)

        metadata_path = base_path / METADATA_FILENAME
        content = yaml.safe_load(metadata_path.read_text())

        assert "schema" in content
        assert (
            content["schema"]["contract_path"]
            == "docs/contracts/gold/activity_v1.0.json"
        )
        assert content["schema"]["validation"] == "strict"

    @pytest.mark.asyncio
    async def test_finalize_silver_metadata_updates_existing_sidecar(
        self,
        tmp_path: Path,
        metadata_writer: MetadataWriter,
        silver_metadata: SilverMetadata,
    ) -> None:
        """Silver finalization should patch the existing sidecar in place."""
        base_path = tmp_path / "silver"
        base_path.mkdir(parents=True)
        await metadata_writer.write_silver_metadata(base_path, silver_metadata)

        completed_at = datetime(2025, 1, 16, 12, 0, 0, tzinfo=UTC)
        result = await metadata_writer.finalize_silver_metadata(
            base_path,
            dq_report_path="/tmp/dq/silver-report.json",
            completed_at=completed_at,
            delta_version_after=99,
        )

        metadata_path = base_path / METADATA_FILENAME
        content = yaml.safe_load(metadata_path.read_text())
        expected_completed_at = completed_at.isoformat().replace("+00:00", "Z")
        assert result == str(metadata_path.resolve())
        assert content["dq_report_path"] == "/tmp/dq/silver-report.json"
        assert content["runtime"]["completed_at_utc"] == expected_completed_at
        assert content["output"]["write_completed_at"] == expected_completed_at
        assert content["delta"]["version_after"] == 99
        assert content["output_ext"]["delta_version_after"] == 99

    @pytest.mark.asyncio
    async def test_finalize_gold_metadata_updates_existing_sidecar(
        self,
        tmp_path: Path,
        metadata_writer: MetadataWriter,
        gold_metadata: GoldMetadata,
    ) -> None:
        """Gold finalization should patch the existing sidecar in place."""
        base_path = tmp_path / "gold"
        base_path.mkdir(parents=True)
        await metadata_writer.write_gold_metadata(base_path, gold_metadata)

        completed_at = datetime(2025, 1, 16, 12, 5, 0, tzinfo=UTC)
        result = await metadata_writer.finalize_gold_metadata(
            base_path,
            dq_report_path="/tmp/dq/gold-report.json",
            completed_at=completed_at,
        )

        metadata_path = base_path / METADATA_FILENAME
        content = yaml.safe_load(metadata_path.read_text())
        expected_completed_at = completed_at.isoformat().replace("+00:00", "Z")
        assert result == str(metadata_path.resolve())
        assert content["dq_report_path"] == "/tmp/dq/gold-report.json"
        assert content["runtime"]["completed_at_utc"] == expected_completed_at
        assert content["output"]["write_completed_at"] == expected_completed_at

    @pytest.mark.asyncio
    async def test_atomic_write_creates_no_temp_files(
        self,
        tmp_path: Path,
        metadata_writer: MetadataWriter,
        bronze_metadata: BronzeMetadata,
    ) -> None:
        """Test that atomic write leaves no temp files."""
        base_path = tmp_path / "bronze"
        base_path.mkdir(parents=True)

        await metadata_writer.write_bronze_metadata(base_path, bronze_metadata)

        # Check no .tmp files remain
        tmp_files = list(base_path.glob("*.tmp"))
        assert len(tmp_files) == 0

    @pytest.mark.asyncio
    async def test_metadata_writer_emits_retry_telemetry(
        self,
        tmp_path: Path,
        bronze_metadata: BronzeMetadata,
    ) -> None:
        """Metadata writer should emit retry telemetry for atomic replace retries."""
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
        base_path = tmp_path / "bronze"
        base_path.mkdir(parents=True)

        original_replace = Path.replace
        call_count = {"count": 0}

        def flaky_replace(self: Path, target_path: Path) -> Path:
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise OSError(errno.EBUSY, "Device or resource busy")
            return original_replace(self, target_path)

        with (
            patch.object(Path, "replace", flaky_replace),
            patch("bioetl.infrastructure.storage.support.atomic_ops.time.sleep"),
        ):
            await writer.write_bronze_metadata(base_path, bronze_metadata)

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
    async def test_write_metadata_overwrites_existing(
        self,
        tmp_path: Path,
        metadata_writer: MetadataWriter,
        bronze_metadata: BronzeMetadata,
    ) -> None:
        """Test that metadata can be overwritten."""
        base_path = tmp_path / "bronze"
        base_path.mkdir(parents=True)

        # Write initial metadata
        await metadata_writer.write_bronze_metadata(base_path, bronze_metadata)

        # Modify and write again
        updated_metadata = BronzeMetadata(
            version="1.0",
            layer=Layer.BRONZE,
            runtime=RuntimeMetadata(
                run_id=str(uuid4()),
                run_type=RunTypeEnum.REBUILD,
                started_at_utc=datetime(2025, 1, 16, 10, 0, 0, tzinfo=UTC),
                completed_at_utc=datetime(2025, 1, 16, 10, 5, 0, tzinfo=UTC),
            ),
            pipeline=bronze_metadata.pipeline,
            source=bronze_metadata.source,
            output=bronze_metadata.output,
            environment=bronze_metadata.environment,
        )

        await metadata_writer.write_bronze_metadata(base_path, updated_metadata)

        metadata_path = base_path / METADATA_FILENAME
        content = yaml.safe_load(metadata_path.read_text())

        assert content["runtime"]["run_type"] == "rebuild"

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
                base_path="/tmp/bronze",
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
            base_path="/tmp/silver/test/table",
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
        result = await writer.write_bronze_metadata("/tmp/bronze", bronze_metadata)
        assert result == ""

    @pytest.mark.asyncio
    async def test_noop_write_silver_returns_empty(
        self,
        silver_metadata: SilverMetadata,
    ) -> None:
        """Test NoOp Silver write returns empty string."""
        writer = NoOpMetadataWriter()
        result = await writer.write_silver_metadata("/tmp/silver", silver_metadata)
        assert result == ""

    @pytest.mark.asyncio
    async def test_noop_write_gold_returns_empty(
        self,
        gold_metadata: GoldMetadata,
    ) -> None:
        """Test NoOp Gold write returns empty string."""
        writer = NoOpMetadataWriter()
        result = await writer.write_gold_metadata("/tmp/gold", gold_metadata)
        assert result == ""

    @pytest.mark.asyncio
    async def test_noop_finalize_methods_return_empty(
        self,
    ) -> None:
        """Test NoOp finalize helpers return empty strings."""
        writer = NoOpMetadataWriter()
        assert await writer.finalize_silver_metadata("/tmp/silver") == ""
        assert await writer.finalize_gold_metadata("/tmp/gold") == ""

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
