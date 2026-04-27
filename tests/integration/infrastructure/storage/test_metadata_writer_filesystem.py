"""Integration tests for MetadataWriter filesystem behavior."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
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
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.metadata_writer import (
    METADATA_FILENAME,
    MetadataWriter,
)

pytestmark = pytest.mark.integration


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


@pytest.mark.asyncio
async def test_write_bronze_metadata_creates_file(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    bronze_metadata: BronzeMetadata,
) -> None:
    """Bronze metadata writes should create one persisted sidecar."""
    base_path = tmp_path / "bronze" / "v1" / "chembl" / "activity" / "2025-01-15"
    base_path.mkdir(parents=True)

    result = await metadata_writer.write_bronze_metadata(base_path, bronze_metadata)

    metadata_path = base_path / METADATA_FILENAME
    assert metadata_path.exists()
    assert result == str(metadata_path.resolve())


@pytest.mark.asyncio
async def test_write_bronze_metadata_valid_yaml(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    bronze_metadata: BronzeMetadata,
) -> None:
    """Bronze metadata sidecars should serialize to canonical YAML."""
    base_path = tmp_path / "bronze"
    base_path.mkdir(parents=True)

    await metadata_writer.write_bronze_metadata(base_path, bronze_metadata)

    content = yaml.safe_load((base_path / METADATA_FILENAME).read_text())
    assert content["version"] == "1.1"
    assert content["layer"] == "bronze"
    assert content["pipeline"]["name"] == "chembl_activity"
    assert content["pipeline"]["provider"] == "chembl"
    assert content["source"]["type"] == "api"
    assert content["output"]["record_count"] == 10000


@pytest.mark.asyncio
async def test_write_silver_metadata_creates_file(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    silver_metadata: SilverMetadata,
) -> None:
    """Silver metadata writes should create one persisted sidecar."""
    base_path = tmp_path / "silver" / "chembl" / "activity"
    base_path.mkdir(parents=True)

    result = await metadata_writer.write_silver_metadata(base_path, silver_metadata)

    metadata_path = base_path / METADATA_FILENAME
    assert metadata_path.exists()
    assert result == str(metadata_path.resolve())


@pytest.mark.asyncio
async def test_write_silver_metadata_includes_lineage(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    silver_metadata: SilverMetadata,
) -> None:
    """Silver metadata sidecars should persist lineage fields."""
    base_path = tmp_path / "silver"
    base_path.mkdir(parents=True)

    await metadata_writer.write_silver_metadata(base_path, silver_metadata)

    content = yaml.safe_load((base_path / METADATA_FILENAME).read_text())
    assert "lineage" in content
    assert "source_batch_ids" in content["lineage"]
    assert "bronze_paths" in content["lineage"]
    assert "transform_steps" in content["lineage"]


@pytest.mark.asyncio
async def test_write_silver_metadata_includes_dq_summary(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    silver_metadata: SilverMetadata,
) -> None:
    """Silver metadata sidecars should persist DQ summary fields."""
    base_path = tmp_path / "silver"
    base_path.mkdir(parents=True)

    await metadata_writer.write_silver_metadata(base_path, silver_metadata)

    content = yaml.safe_load((base_path / METADATA_FILENAME).read_text())
    assert "dq_summary" in content
    assert content["dq_summary"]["total_records"] == 15000
    assert content["dq_summary"]["error_rate"] == pytest.approx(0.05)


@pytest.mark.asyncio
async def test_write_gold_metadata_creates_file(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    gold_metadata: GoldMetadata,
) -> None:
    """Gold metadata writes should create one persisted sidecar."""
    base_path = tmp_path / "gold" / "chembl" / "activity_aggregated"
    base_path.mkdir(parents=True)

    result = await metadata_writer.write_gold_metadata(base_path, gold_metadata)

    metadata_path = base_path / METADATA_FILENAME
    assert metadata_path.exists()
    assert result == str(metadata_path.resolve())


@pytest.mark.asyncio
async def test_write_gold_metadata_includes_schema_contract(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    gold_metadata: GoldMetadata,
) -> None:
    """Gold metadata sidecars should persist schema contract fields."""
    base_path = tmp_path / "gold"
    base_path.mkdir(parents=True)

    await metadata_writer.write_gold_metadata(base_path, gold_metadata)

    content = yaml.safe_load((base_path / METADATA_FILENAME).read_text())
    assert "schema" in content
    assert (
        content["schema"]["contract_path"] == "docs/contracts/gold/activity_v1.0.json"
    )
    assert content["schema"]["validation"] == "strict"


@pytest.mark.asyncio
async def test_finalize_silver_metadata_updates_existing_sidecar(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    silver_metadata: SilverMetadata,
) -> None:
    """Silver finalization should patch the persisted sidecar in place."""
    base_path = tmp_path / "silver"
    base_path.mkdir(parents=True)
    await metadata_writer.write_silver_metadata(base_path, silver_metadata)
    dq_report_path = str(tmp_path / "dq" / "silver-report.json")

    completed_at = datetime(2025, 1, 16, 12, 0, 0, tzinfo=UTC)
    result = await metadata_writer.finalize_silver_metadata(
        base_path,
        dq_report_path=dq_report_path,
        completed_at=completed_at,
        delta_version_after=99,
    )

    content = yaml.safe_load((base_path / METADATA_FILENAME).read_text())
    expected_completed_at = completed_at.isoformat().replace("+00:00", "Z")
    assert result == str((base_path / METADATA_FILENAME).resolve())
    assert content["dq_report_path"] == dq_report_path
    assert content["runtime"]["completed_at_utc"] == expected_completed_at
    assert content["output"]["write_completed_at"] == expected_completed_at
    assert content["delta"]["version_after"] == 99
    assert content["output_ext"]["delta_version_after"] == 99


@pytest.mark.asyncio
async def test_finalize_gold_metadata_updates_existing_sidecar(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    gold_metadata: GoldMetadata,
) -> None:
    """Gold finalization should patch the persisted sidecar in place."""
    base_path = tmp_path / "gold"
    base_path.mkdir(parents=True)
    await metadata_writer.write_gold_metadata(base_path, gold_metadata)
    dq_report_path = str(tmp_path / "dq" / "gold-report.json")

    completed_at = datetime(2025, 1, 16, 12, 5, 0, tzinfo=UTC)
    result = await metadata_writer.finalize_gold_metadata(
        base_path,
        dq_report_path=dq_report_path,
        completed_at=completed_at,
    )

    content = yaml.safe_load((base_path / METADATA_FILENAME).read_text())
    expected_completed_at = completed_at.isoformat().replace("+00:00", "Z")
    assert result == str((base_path / METADATA_FILENAME).resolve())
    assert content["dq_report_path"] == dq_report_path
    assert content["runtime"]["completed_at_utc"] == expected_completed_at
    assert content["output"]["write_completed_at"] == expected_completed_at


@pytest.mark.asyncio
async def test_atomic_write_creates_no_temp_files(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    bronze_metadata: BronzeMetadata,
) -> None:
    """Atomic metadata writes should not leak temporary files."""
    base_path = tmp_path / "bronze"
    base_path.mkdir(parents=True)

    await metadata_writer.write_bronze_metadata(base_path, bronze_metadata)

    assert list(base_path.glob("*.tmp")) == []


@pytest.mark.asyncio
async def test_write_metadata_overwrites_existing(
    tmp_path: Path,
    metadata_writer: MetadataWriter,
    bronze_metadata: BronzeMetadata,
) -> None:
    """Repeated metadata writes should replace prior file contents."""
    base_path = tmp_path / "bronze"
    base_path.mkdir(parents=True)
    await metadata_writer.write_bronze_metadata(base_path, bronze_metadata)

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

    content = yaml.safe_load((base_path / METADATA_FILENAME).read_text())
    assert content["runtime"]["run_type"] == "rebuild"
