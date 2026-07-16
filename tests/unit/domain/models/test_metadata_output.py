"""Unit tests for unified output metadata classes (ADR-029).

Tests BaseOutputMetadata and layer-specific output extensions.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from bioetl.domain.models.metadata import (
    BaseOutputMetadata,
    BronzeMetadata,
    BronzeOutputExt,
    DeltaMetrics,
    EnvironmentMetadata,
    FileOutputMetadata,
    GoldMetadata,
    GoldOutputExt,
    PipelineMetadata,
    RuntimeMetadata,
    RunTypeEnum,
    SilverMetadata,
    SilverOutputExt,
)
from tests.helpers.clock import FIXED_TEST_TIME

pytestmark = pytest.mark.unit


class TestBaseOutputMetadata:
    """Test base output metadata contract."""

    def test_base_output_metadata__default_values__229a2993(self) -> None:
        """GIVEN no arguments WHEN creating BaseOutputMetadata THEN defaults applied."""
        output = BaseOutputMetadata()

        assert output.artifact_id is None
        assert output.record_count == 0
        assert output.total_bytes == 0
        assert output.content_hash is None
        assert output.write_started_at is None
        assert output.write_completed_at is None
        assert output.write_duration_ms is None

    def test_with_all_fields(self) -> None:
        """GIVEN all fields WHEN creating BaseOutputMetadata THEN all stored."""
        started = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        completed = datetime(2025, 1, 1, 12, 0, 5, 500000, tzinfo=UTC)

        output = BaseOutputMetadata(
            artifact_id="silver:chembl.activity@7",
            record_count=1000,
            total_bytes=50000,
            content_hash="sha256:abc123",
            write_started_at=started,
            write_completed_at=completed,
        )

        assert output.artifact_id == "silver:chembl.activity@7"
        assert output.record_count == 1000
        assert output.total_bytes == 50000
        assert output.content_hash == "sha256:abc123"
        assert output.write_started_at == started
        assert output.write_completed_at == completed

    def test_write_duration_calculation(self) -> None:
        """GIVEN started and completed timestamps WHEN accessing write_duration_ms THEN returns correct duration."""
        started = datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC)
        completed = datetime(2025, 1, 1, 12, 0, 5, 500000, tzinfo=UTC)  # 5.5 seconds

        output = BaseOutputMetadata(
            record_count=100,
            total_bytes=1024,
            write_started_at=started,
            write_completed_at=completed,
        )

        assert output.write_duration_ms == 5500

    def test_write_duration_none_when_missing_started(self) -> None:
        """GIVEN missing started_at WHEN accessing write_duration_ms THEN returns None."""
        output = BaseOutputMetadata(
            record_count=100,
            write_completed_at=FIXED_TEST_TIME,
        )
        assert output.write_duration_ms is None

    def test_write_duration_none_when_missing_completed(self) -> None:
        """GIVEN missing completed_at WHEN accessing write_duration_ms THEN returns None."""
        output = BaseOutputMetadata(
            record_count=100,
            write_started_at=FIXED_TEST_TIME,
        )
        assert output.write_duration_ms is None

    def test_write_duration_none_when_both_missing(self) -> None:
        """GIVEN missing timestamps WHEN accessing write_duration_ms THEN returns None."""
        output = BaseOutputMetadata(record_count=100, total_bytes=1024)
        assert output.write_duration_ms is None

    def test_negative_record_count_rejected(self) -> None:
        """GIVEN negative record_count WHEN creating THEN validation error."""
        with pytest.raises(ValidationError):
            BaseOutputMetadata(record_count=-1)

    def test_negative_total_bytes_rejected(self) -> None:
        """GIVEN negative total_bytes WHEN creating THEN validation error."""
        with pytest.raises(ValidationError):
            BaseOutputMetadata(total_bytes=-1)

    def test_extra_fields_forbidden(self) -> None:
        """GIVEN extra field WHEN creating THEN validation error (extra=forbid)."""
        with pytest.raises(ValidationError):
            BaseOutputMetadata(unknown_field="value")  # type: ignore[call-arg]


class TestBronzeOutputExt:
    """Test Bronze-specific output extension."""

    def test_bronze_output_ext__default_values__9f95bd09(self) -> None:
        """GIVEN no arguments WHEN creating BronzeOutputExt THEN defaults applied."""
        ext = BronzeOutputExt()

        assert ext.files == []
        assert ext.format == "jsonl+zstd"
        assert ext.compression == "zstd"

    def test_with_files(self) -> None:
        """GIVEN file list WHEN creating BronzeOutputExt THEN files stored."""
        files = [
            FileOutputMetadata(
                path="batch_001.jsonl.zst",
                size_bytes=10000,
                record_count=100,
            ),
            FileOutputMetadata(
                path="batch_002.jsonl.zst",
                size_bytes=15000,
                record_count=150,
            ),
        ]

        ext = BronzeOutputExt(files=files)

        assert len(ext.files) == 2
        assert ext.files[0].path == "batch_001.jsonl.zst"
        assert ext.files[1].record_count == 150

    def test_bronze_output_ext__custom_format__da649897(self) -> None:
        """GIVEN custom format WHEN creating BronzeOutputExt THEN format stored."""
        ext = BronzeOutputExt(format="jsonl", compression="gzip")

        assert ext.format == "jsonl"
        assert ext.compression == "gzip"


class TestSilverOutputExt:
    """Test Silver-specific output extension."""

    def test_silver_output_ext__default_values__8804504f(self) -> None:
        """GIVEN no arguments WHEN creating SilverOutputExt THEN defaults applied."""
        ext = SilverOutputExt()

        assert ext.delta_version_before is None
        assert ext.delta_version_after is None

    def test_with_delta_versions(self) -> None:
        """GIVEN delta versions WHEN creating SilverOutputExt THEN both tracked."""
        ext = SilverOutputExt(delta_version_before=5, delta_version_after=6)

        assert ext.delta_version_before == 5
        assert ext.delta_version_after == 6
        assert ext.delta_version_after - ext.delta_version_before == 1

    def test_only_version_after(self) -> None:
        """GIVEN only version_after WHEN creating SilverOutputExt THEN valid."""
        ext = SilverOutputExt(delta_version_after=10)

        assert ext.delta_version_before is None
        assert ext.delta_version_after == 10


class TestGoldOutputExt:
    """Test Gold-specific output extension."""

    def test_output_gold_output_ext__default_values__79c21c7d(self) -> None:
        """GIVEN no arguments WHEN creating GoldOutputExt THEN defaults applied."""
        ext = GoldOutputExt()

        assert ext.partition_count == 0
        assert ext.format == "delta"

    def test_with_partition_count(self) -> None:
        """GIVEN partition count WHEN creating GoldOutputExt THEN stored."""
        ext = GoldOutputExt(partition_count=4)

        assert ext.partition_count == 4

    def test_parquet_format_rejected(self) -> None:
        """GIVEN raw Parquet format WHEN creating GoldOutputExt THEN reject it."""
        with pytest.raises(ValidationError, match="Input should be 'delta'"):
            GoldOutputExt(format="parquet")  # type: ignore[arg-type]

    def test_invalid_format_rejected(self) -> None:
        """GIVEN invalid format WHEN creating GoldOutputExt THEN validation error."""
        with pytest.raises(ValidationError):
            GoldOutputExt(format="csv")  # type: ignore[arg-type]

    def test_negative_partition_count_rejected(self) -> None:
        """GIVEN negative partition_count WHEN creating THEN validation error."""
        with pytest.raises(ValidationError):
            GoldOutputExt(partition_count=-1)


class TestLayerMetadataComposition:
    """Test layer metadata classes with output composition."""

    @pytest.fixture
    def runtime(self) -> RuntimeMetadata:
        """Create test RuntimeMetadata."""
        return RuntimeMetadata(
            run_id="test-run-123",
            run_type=RunTypeEnum.INCREMENTAL,
            started_at_utc=FIXED_TEST_TIME,
        )

    @pytest.fixture
    def pipeline(self) -> PipelineMetadata:
        """Create test PipelineMetadata."""
        return PipelineMetadata(
            name="test_pipeline",
            provider="test",
            entity="activity",
        )

    @pytest.fixture
    def environment(self) -> EnvironmentMetadata:
        """Create test EnvironmentMetadata."""
        return EnvironmentMetadata(
            hostname="test-host",
            python_version="3.11.0",
            bioetl_version="5.10.0",
        )

    def test_bronze_metadata_has_unified_output(
        self,
        runtime: RuntimeMetadata,
        pipeline: PipelineMetadata,
        environment: EnvironmentMetadata,
    ) -> None:
        """GIVEN BronzeMetadata WHEN accessing output THEN BaseOutputMetadata returned."""
        metadata = BronzeMetadata(
            runtime=runtime,
            pipeline=pipeline,
            environment=environment,
        )

        assert isinstance(metadata.output, BaseOutputMetadata)
        assert isinstance(metadata.output_ext, BronzeOutputExt)

    def test_bronze_metadata_output_fields(
        self,
        runtime: RuntimeMetadata,
        pipeline: PipelineMetadata,
        environment: EnvironmentMetadata,
    ) -> None:
        """GIVEN BronzeMetadata with output data THEN fields accessible."""
        started = FIXED_TEST_TIME
        completed = started + timedelta(seconds=5)

        metadata = BronzeMetadata(
            runtime=runtime,
            pipeline=pipeline,
            environment=environment,
            output=BaseOutputMetadata(
                record_count=1000,
                total_bytes=50000,
                write_started_at=started,
                write_completed_at=completed,
            ),
            output_ext=BronzeOutputExt(
                files=[
                    FileOutputMetadata(
                        path="batch_001.jsonl.zst",
                        size_bytes=50000,
                        record_count=1000,
                    )
                ],
            ),
        )

        assert metadata.output.record_count == 1000
        assert metadata.output.total_bytes == 50000
        assert metadata.output.write_duration_ms == 5000
        assert len(metadata.output_ext.files) == 1
        assert metadata.output_ext.format == "jsonl+zstd"

    def test_silver_metadata_has_unified_output(
        self,
        runtime: RuntimeMetadata,
        pipeline: PipelineMetadata,
        environment: EnvironmentMetadata,
    ) -> None:
        """GIVEN SilverMetadata WHEN accessing output THEN BaseOutputMetadata returned."""
        metadata = SilverMetadata(
            runtime=runtime,
            pipeline=pipeline,
            delta=DeltaMetrics(table_path="/silver/test", operation="merge"),
            environment=environment,
        )

        assert isinstance(metadata.output, BaseOutputMetadata)
        assert isinstance(metadata.output_ext, SilverOutputExt)

    def test_silver_metadata_output_fields(
        self,
        runtime: RuntimeMetadata,
        pipeline: PipelineMetadata,
        environment: EnvironmentMetadata,
    ) -> None:
        """GIVEN SilverMetadata with output data THEN fields accessible."""
        metadata = SilverMetadata(
            runtime=runtime,
            pipeline=pipeline,
            delta=DeltaMetrics(table_path="/silver/test", operation="merge"),
            environment=environment,
            output=BaseOutputMetadata(
                record_count=950,
                total_bytes=48000,
                content_hash="sha256:abc123",
            ),
            output_ext=SilverOutputExt(
                delta_version_before=5,
                delta_version_after=6,
            ),
        )

        assert metadata.output.record_count == 950
        assert metadata.output.total_bytes == 48000
        assert metadata.output.content_hash == "sha256:abc123"
        assert metadata.output_ext.delta_version_before == 5
        assert metadata.output_ext.delta_version_after == 6

    def test_gold_metadata_has_unified_output(
        self,
        runtime: RuntimeMetadata,
        pipeline: PipelineMetadata,
        environment: EnvironmentMetadata,
    ) -> None:
        """GIVEN GoldMetadata WHEN accessing output THEN BaseOutputMetadata returned."""
        metadata = GoldMetadata(
            runtime=runtime,
            pipeline=pipeline,
            environment=environment,
        )

        assert isinstance(metadata.output, BaseOutputMetadata)
        assert isinstance(metadata.output_ext, GoldOutputExt)

    def test_gold_metadata_output_fields(
        self,
        runtime: RuntimeMetadata,
        pipeline: PipelineMetadata,
        environment: EnvironmentMetadata,
    ) -> None:
        """GIVEN GoldMetadata with output data THEN fields accessible."""
        metadata = GoldMetadata(
            runtime=runtime,
            pipeline=pipeline,
            environment=environment,
            output=BaseOutputMetadata(
                record_count=900,
                total_bytes=45000,
            ),
            output_ext=GoldOutputExt(
                partition_count=4,
                format="delta",
            ),
        )

        assert metadata.output.record_count == 900
        assert metadata.output.total_bytes == 45000
        assert metadata.output_ext.partition_count == 4
        assert metadata.output_ext.format == "delta"


class TestMetadataVersionBump:
    """Test metadata version is updated for ADR-029."""

    @pytest.fixture
    def runtime(self) -> RuntimeMetadata:
        """Create test RuntimeMetadata."""
        return RuntimeMetadata(
            run_id="test-run-123",
            run_type=RunTypeEnum.INCREMENTAL,
            started_at_utc=FIXED_TEST_TIME,
        )

    @pytest.fixture
    def pipeline(self) -> PipelineMetadata:
        """Create test PipelineMetadata."""
        return PipelineMetadata(
            name="test_pipeline",
            provider="test",
            entity="activity",
        )

    @pytest.fixture
    def environment(self) -> EnvironmentMetadata:
        """Create test EnvironmentMetadata."""
        return EnvironmentMetadata(
            hostname="test-host",
            python_version="3.11.0",
            bioetl_version="5.10.0",
        )

    def test_bronze_metadata_version(
        self,
        runtime: RuntimeMetadata,
        pipeline: PipelineMetadata,
        environment: EnvironmentMetadata,
    ) -> None:
        """GIVEN BronzeMetadata WHEN checking version THEN 1.1 for ADR-029."""
        metadata = BronzeMetadata(
            runtime=runtime,
            pipeline=pipeline,
            environment=environment,
        )
        assert metadata.version == "1.1"

    def test_silver_metadata_version(
        self,
        runtime: RuntimeMetadata,
        pipeline: PipelineMetadata,
        environment: EnvironmentMetadata,
    ) -> None:
        """GIVEN SilverMetadata WHEN checking version THEN 1.1 for ADR-029."""
        metadata = SilverMetadata(
            runtime=runtime,
            pipeline=pipeline,
            delta=DeltaMetrics(table_path="/silver/test", operation="merge"),
            environment=environment,
        )
        assert metadata.version == "1.1"

    def test_gold_metadata_version(
        self,
        runtime: RuntimeMetadata,
        pipeline: PipelineMetadata,
        environment: EnvironmentMetadata,
    ) -> None:
        """GIVEN GoldMetadata WHEN checking version THEN 1.1 for ADR-029."""
        metadata = GoldMetadata(
            runtime=runtime,
            pipeline=pipeline,
            environment=environment,
        )
        assert metadata.version == "1.1"
