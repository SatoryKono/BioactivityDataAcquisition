"""Shared metadata sample builders and fixtures for tests."""

from __future__ import annotations

from datetime import UTC, datetime

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
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter
from tests.helpers.deterministic_ids import deterministic_run_id

BRONZE_BASE_PATH = "/virtual/bronze"
SILVER_TABLE_PATH = "/virtual/silver/test/table"
SILVER_BASE_PATH = "/virtual/silver"
GOLD_BASE_PATH = "/virtual/gold"


def build_runtime_metadata(
    *,
    run_id: str | None = None,
    manifest_id: str | None = None,
    run_type: RunTypeEnum = RunTypeEnum.INCREMENTAL,
    started_at_utc: datetime | None = None,
    completed_at_utc: datetime | None = None,
    duration_seconds: float = 300.0,
) -> RuntimeMetadata:
    """Build canonical runtime metadata used across metadata tests."""
    return RuntimeMetadata(
        run_id=run_id or deterministic_run_id("metadata.runtime"),
        manifest_id=manifest_id,
        run_type=run_type,
        started_at_utc=started_at_utc or datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC),
        completed_at_utc=completed_at_utc
        or datetime(2025, 1, 15, 10, 5, 0, 0, tzinfo=UTC),
        duration_seconds=duration_seconds,
    )


def build_pipeline_metadata() -> PipelineMetadata:
    """Build canonical pipeline metadata fixture payload."""
    return PipelineMetadata(
        name="chembl_activity",
        provider="chembl",
        entity="activity",
        version="1.2.0",
        git_commit="abc123def",
        config_hash="sha256:xyz789",
    )


def build_environment_metadata() -> EnvironmentMetadata:
    """Build canonical environment metadata fixture payload."""
    return EnvironmentMetadata(
        hostname="worker-01",
        python_version="3.11.5",
        bioetl_version="5.0.5",
    )


def build_bronze_metadata(
    *,
    version: str = "1.1",
    runtime: RuntimeMetadata | None = None,
    pipeline: PipelineMetadata | None = None,
    environment: EnvironmentMetadata | None = None,
) -> BronzeMetadata:
    """Build canonical Bronze metadata sample."""
    return BronzeMetadata(
        version=version,
        layer=Layer.BRONZE,
        runtime=runtime or build_runtime_metadata(),
        pipeline=pipeline or build_pipeline_metadata(),
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
        environment=environment or build_environment_metadata(),
    )


def build_silver_metadata(
    *,
    runtime: RuntimeMetadata | None = None,
    pipeline: PipelineMetadata | None = None,
    environment: EnvironmentMetadata | None = None,
) -> SilverMetadata:
    """Build canonical Silver metadata sample."""
    return SilverMetadata(
        version="1.1",
        layer=Layer.SILVER,
        runtime=runtime or build_runtime_metadata(),
        pipeline=pipeline or build_pipeline_metadata(),
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
        environment=environment or build_environment_metadata(),
    )


def build_gold_metadata(
    *,
    runtime: RuntimeMetadata | None = None,
    pipeline: PipelineMetadata | None = None,
    environment: EnvironmentMetadata | None = None,
) -> GoldMetadata:
    """Build canonical Gold metadata sample."""
    return GoldMetadata(
        version="1.1",
        layer=Layer.GOLD,
        runtime=runtime or build_runtime_metadata(),
        pipeline=pipeline or build_pipeline_metadata(),
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
        environment=environment or build_environment_metadata(),
    )


# @pytest.fixture
# def metadata_writer(noop_logger: object) -> MetadataWriter:
#     """Create MetadataWriter instance."""
#     return MetadataWriter(logger=noop_logger)


# @pytest.fixture
# def runtime_metadata() -> RuntimeMetadata:
#     """Create sample runtime metadata."""
#     return build_runtime_metadata()
#
#
# @pytest.fixture
# def pipeline_metadata() -> PipelineMetadata:
#     """Create sample pipeline metadata."""
#     return build_pipeline_metadata()
#
#
# @pytest.fixture
# def environment_metadata() -> EnvironmentMetadata:
#     """Create sample environment metadata."""
#     return build_environment_metadata()
#
#
# @pytest.fixture
# def bronze_metadata(
#     runtime_metadata: RuntimeMetadata,
#     pipeline_metadata: PipelineMetadata,
#     environment_metadata: EnvironmentMetadata,
# ) -> BronzeMetadata:
#     """Create sample Bronze metadata."""
#     return build_bronze_metadata(
#         runtime=runtime_metadata,
#         pipeline=pipeline_metadata,
#         environment=environment_metadata,
#     )
#
#
# @pytest.fixture
# def silver_metadata(
#     runtime_metadata: RuntimeMetadata,
#     pipeline_metadata: PipelineMetadata,
#     environment_metadata: EnvironmentMetadata,
# ) -> SilverMetadata:
#     """Create sample Silver metadata."""
#     return build_silver_metadata(
#         runtime=runtime_metadata,
#         pipeline=pipeline_metadata,
#         environment=environment_metadata,
#     )
#
#
# @pytest.fixture
# def gold_metadata(
#     runtime_metadata: RuntimeMetadata,
#     pipeline_metadata: PipelineMetadata,
#     environment_metadata: EnvironmentMetadata,
# ) -> GoldMetadata:
#     """Create sample Gold metadata."""
#     return build_gold_metadata(
#         runtime=runtime_metadata,
#         pipeline=pipeline_metadata,
#         environment=environment_metadata,
#     )
