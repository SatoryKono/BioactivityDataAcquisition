"""Unit tests for metadata writing integration with Silver and Gold writers.

Tests that SilverWriter and GoldWriter correctly delegate to MetadataWriterPort
when configured to write metadata sidecar files.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pyarrow as pa
import pytest

from bioetl.application.services.lineage import MetadataLineageBundle
from bioetl.domain.models.metadata import (
    DeltaMetrics,
    EnvironmentMetadata,
    GoldMetadata,
    PipelineMetadata,
    RuntimeMetadata,
    RunTypeEnum,
    SilverMetadata,
)
from bioetl.domain.ports.noop import NoOpMetadataWriter
from bioetl.domain.types import RunID
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter
from tests.unit.infrastructure.storage._lineage_fragment_helpers import (
    make_produced_artifact_fragment,
)


class MockMetadataCoordinator:
    """Mock MetadataCoordinator that creates minimal metadata objects."""

    def create_silver_metadata(self, input_data: Any) -> SilverMetadata:
        """Create minimal SilverMetadata for testing."""
        provider, entity = str(input_data.table_name).split(".", 1)
        runtime = RuntimeMetadata(
            run_id=input_data.records[0].get("_run_id", "test-run-id"),
            run_type=RunTypeEnum.INCREMENTAL,
            started_at_utc=datetime.now(UTC),
        )
        pipeline = PipelineMetadata(name="test", provider=provider, entity=entity)
        environment = EnvironmentMetadata(
            hostname="test", python_version="3.11", bioetl_version="1.0"
        )
        delta = DeltaMetrics(
            table_path=str(input_data.table_path),
            operation=str(input_data.mode.value)
            if hasattr(input_data.mode, "value")
            else str(input_data.mode),
            rows_inserted=len(input_data.records),
            primary_key=input_data.primary_keys,
        )
        return SilverMetadata(
            runtime=runtime,
            pipeline=pipeline,
            delta=delta,
            environment=environment,
        )

    def create_gold_metadata(self, input_data: Any) -> GoldMetadata:
        """Create minimal GoldMetadata for testing."""
        from bioetl.domain.models.metadata import BaseOutputMetadata, GoldOutputExt

        provider, entity = str(input_data.table_name).split(".", 1)
        runtime = RuntimeMetadata(
            run_id="test-run-id",
            run_type=RunTypeEnum.INCREMENTAL,
            started_at_utc=datetime.now(UTC),
        )
        pipeline = PipelineMetadata(name="test", provider=provider, entity=entity)
        environment = EnvironmentMetadata(
            hostname="test", python_version="3.11", bioetl_version="1.0"
        )
        output = BaseOutputMetadata(
            record_count=len(input_data.records),
        )
        output_ext = GoldOutputExt()
        return GoldMetadata(
            runtime=runtime,
            pipeline=pipeline,
            output=output,
            output_ext=output_ext,
            environment=environment,
        )

    def create_silver_metadata_bundle(
        self, input_data: Any
    ) -> MetadataLineageBundle[SilverMetadata]:
        """Wrap Silver metadata in the canonical bundle contract."""
        return MetadataLineageBundle(
            metadata=self.create_silver_metadata(input_data),
            lineage_fragment=make_produced_artifact_fragment(
                fragment_id="silver:integration-fragment",
                layer="silver",
                logical_name="test.table",
            ),
        )

    def create_gold_metadata_bundle(
        self, input_data: Any
    ) -> MetadataLineageBundle[GoldMetadata]:
        """Wrap Gold metadata in the canonical bundle contract."""
        return MetadataLineageBundle(
            metadata=self.create_gold_metadata(input_data),
            lineage_fragment=make_produced_artifact_fragment(
                fragment_id="gold:integration-fragment",
                layer="gold",
                logical_name="test.gold_table",
            ),
        )


class MockMetadataWriter:
    """Mock MetadataWriter that records calls."""

    def __init__(self) -> None:
        """Initialize mock writer."""
        self.silver_calls: list[tuple[str | Path, SilverMetadata]] = []
        self.gold_calls: list[tuple[str | Path, GoldMetadata]] = []

    async def write_bronze_metadata(
        self,
        base_path: str | Path,
        metadata: Any,
        *,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Mock Bronze metadata write."""
        await asyncio.sleep(0)
        return ""

    async def write_silver_metadata(
        self,
        base_path: str | Path,
        metadata: SilverMetadata,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Record Silver metadata write."""
        await asyncio.sleep(0)
        self.silver_calls.append((base_path, metadata))
        return str(Path(base_path) / "_metadata.yaml")

    async def write_gold_metadata(
        self,
        base_path: str | Path,
        metadata: GoldMetadata,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
    ) -> str:
        """Record Gold metadata write."""
        await asyncio.sleep(0)
        self.gold_calls.append((base_path, metadata))
        return str(Path(base_path) / "_metadata.yaml")

    async def finalize_silver_metadata(
        self,
        base_path: str | Path,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
        dq_report_path: str | None = None,
        completed_at: datetime | None = None,
        delta_version_after: int | None = None,
    ) -> str | None:
        """Record Silver metadata finalization as a no-op compatible seam."""
        await asyncio.sleep(0)
        _ = (
            table_name,
            flat_structure,
            provider,
            entity,
            dq_report_path,
            completed_at,
            delta_version_after,
        )
        return str(Path(base_path) / "_metadata.yaml")

    async def finalize_gold_metadata(
        self,
        base_path: str | Path,
        *,
        table_name: str | None = None,
        flat_structure: bool = False,
        provider: str | None = None,
        entity: str | None = None,
        dq_report_path: str | None = None,
        completed_at: datetime | None = None,
    ) -> str | None:
        """Record Gold metadata finalization as a no-op compatible seam."""
        await asyncio.sleep(0)
        _ = (
            table_name,
            flat_structure,
            provider,
            entity,
            dq_report_path,
            completed_at,
        )
        return str(Path(base_path) / "_metadata.yaml")

    async def aclose(self) -> None:
        """No-op close."""
        await asyncio.sleep(0)


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    return MagicMock()


@pytest.fixture
def mock_metadata_writer() -> MockMetadataWriter:
    """Create a mock metadata writer."""
    return MockMetadataWriter()


@pytest.fixture
def mock_metadata_coordinator() -> MockMetadataCoordinator:
    """Create a mock metadata coordinator."""
    return MockMetadataCoordinator()


@pytest.fixture
def sample_records() -> list[dict[str, Any]]:
    """Create sample records for testing."""
    run_id = str(uuid4())
    batch_id = str(uuid4())
    return [
        {
            "id": "record1",
            "value": 42,
            "_run_id": run_id,
            "_run_type": "incremental",
            "_source_batch_id": batch_id,
            "_ingestion_ts": datetime.now(UTC).isoformat(),
        },
        {
            "id": "record2",
            "value": 43,
            "_run_id": run_id,
            "_run_type": "incremental",
            "_source_batch_id": batch_id,
            "_ingestion_ts": datetime.now(UTC).isoformat(),
        },
    ]


@pytest.fixture
def silver_schema() -> pa.Schema:
    """Create sample PyArrow schema for Silver layer."""
    return pa.schema(
        [
            pa.field("id", pa.string()),
            pa.field("value", pa.int64()),
            pa.field("_run_id", pa.string()),
            pa.field("_run_type", pa.string()),
            pa.field("_source_batch_id", pa.string()),
            pa.field("_ingestion_ts", pa.string()),
        ]
    )


@pytest.fixture
def mock_metadata_coordinator_with_records(
    sample_records: list[dict[str, Any]],
) -> MagicMock:
    """Create a mock metadata coordinator that returns mock metadata objects.

    Uses MagicMock for the metadata objects to avoid complex Pydantic model setup.
    The test verifies that metadata_writer is called, not the exact metadata content.
    """
    mock = MagicMock()

    # Create mock SilverMetadata with required attributes for the test assertions
    mock_silver_metadata = MagicMock(spec=SilverMetadata)
    mock_silver_metadata.runtime = MagicMock()
    mock_silver_metadata.runtime.run_id = sample_records[0]["_run_id"]
    mock_silver_metadata.delta = MagicMock()
    mock_silver_metadata.delta.rows_inserted = len(sample_records)
    mock_silver_metadata.delta.operation = "merge"
    mock_silver_metadata.delta.primary_key = ["id"]
    mock_silver_metadata.output = MagicMock()
    mock_silver_metadata.output.artifact_id = None
    mock_silver_metadata.output.lineage_fragment_id = None
    mock.create_silver_metadata.return_value = mock_silver_metadata
    mock.create_silver_metadata_bundle = MagicMock(
        side_effect=lambda input_data: MetadataLineageBundle(
            metadata=mock_silver_metadata,
            lineage_fragment=make_produced_artifact_fragment(
                fragment_id="silver:integration-mock-fragment",
                layer="silver",
                logical_name=getattr(input_data, "table_name", "test.table"),
            ),
        )
    )

    # Create mock GoldMetadata
    mock_gold_metadata = MagicMock(spec=GoldMetadata)
    mock_gold_metadata.runtime = MagicMock()
    mock_gold_metadata.runtime.run_id = sample_records[0]["_run_id"]
    mock_gold_metadata.delta = MagicMock()
    mock_gold_metadata.delta.rows_inserted = len(sample_records)
    mock_gold_metadata.delta.operation = "overwrite"
    mock.create_gold_metadata.return_value = mock_gold_metadata
    mock.create_gold_metadata_bundle = MagicMock(
        side_effect=lambda input_data: MetadataLineageBundle(
            metadata=mock_gold_metadata,
            lineage_fragment=make_produced_artifact_fragment(
                fragment_id="gold:integration-mock-fragment",
                layer="gold",
                logical_name=getattr(input_data, "table_name", "test.gold_table"),
            ),
        )
    )

    return mock


class TestSilverWriterMetadataIntegration:
    """Tests for SilverWriter metadata integration."""

    @pytest.mark.asyncio
    async def test_silver_writer_calls_metadata_writer(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        mock_metadata_writer: MockMetadataWriter,
        mock_metadata_coordinator_with_records: MagicMock,
        sample_records: list[dict[str, Any]],
        silver_schema: pa.Schema,
    ) -> None:
        """Test that SilverWriter calls metadata writer after write."""
        writer = SilverWriter(
            base_path=tmp_path,
            logger=mock_logger,
            metadata_writer=mock_metadata_writer,
            metadata_coordinator=mock_metadata_coordinator_with_records,
        )

        await writer.write_silver(
            table_name="test.table",
            records=sample_records,
            primary_keys=["id"],
            schema=silver_schema,
            mode="merge",
        )

        # Verify metadata writer was called
        assert len(mock_metadata_writer.silver_calls) == 1
        table_path, metadata = mock_metadata_writer.silver_calls[0]

        # Verify path
        assert str(table_path) == f"{tmp_path}/test/table"

        # Verify metadata content
        assert metadata.runtime.run_id == sample_records[0]["_run_id"]
        assert metadata.delta.rows_inserted == 2
        assert metadata.delta.operation == "merge"
        assert metadata.delta.primary_key == ["id"]

    @pytest.mark.asyncio
    async def test_silver_writer_uses_noop_when_no_metadata_writer(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        sample_records: list[dict[str, Any]],
        silver_schema: pa.Schema,
    ) -> None:
        """Test that SilverWriter uses NoOpMetadataWriter when not provided."""
        writer = SilverWriter(
            base_path=tmp_path,
            logger=mock_logger,
            # No metadata_writer provided
        )

        # Should not raise an error
        await writer.write_silver(
            table_name="test.table",
            records=sample_records,
            primary_keys=["id"],
            schema=silver_schema,
            mode="merge",
        )

        # Verify NoOp was used (no metadata file created)
        metadata_file = tmp_path / "test" / "table" / "_metadata.yaml"
        assert not metadata_file.exists()


class TestGoldWriterMetadataIntegration:
    """Tests for GoldWriter metadata integration."""

    @pytest.mark.asyncio
    async def test_gold_writer_calls_metadata_writer(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
        mock_metadata_writer: MockMetadataWriter,
        mock_metadata_coordinator: MockMetadataCoordinator,
    ) -> None:
        """Test that GoldWriter calls metadata writer after write."""
        import pandera.pandas as pa_pandera

        schema = pa_pandera.DataFrameSchema(
            columns={
                "id": pa_pandera.Column(str),
                "value": pa_pandera.Column(int),
            },
            strict=True,
        )

        writer = GoldWriter(
            base_path=tmp_path,
            logger=mock_logger,
            metadata_writer=mock_metadata_writer,
            metadata_coordinator=mock_metadata_coordinator,
        )

        records = [
            {"id": "record1", "value": 42},
            {"id": "record2", "value": 43},
        ]

        ingestion_ts = datetime.now(UTC)
        run_id = RunID(uuid4())

        await writer.write_gold(
            table_name="test.gold_table",
            records=records,
            schema=schema,
            primary_keys=["id"],
            mode="overwrite",
            ingestion_ts=ingestion_ts,
            run_id=run_id,
        )

        # Verify metadata writer was called
        assert len(mock_metadata_writer.gold_calls) == 1
        table_path, metadata = mock_metadata_writer.gold_calls[0]

        # Verify path
        assert str(table_path) == f"{tmp_path}/test/gold_table"

        # Verify metadata content
        assert metadata.output.record_count == 2
        assert metadata.pipeline.provider == "test"
        assert metadata.pipeline.entity == "gold_table"

    @pytest.mark.asyncio
    async def test_gold_writer_uses_noop_when_no_metadata_writer(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
    ) -> None:
        """Test that GoldWriter uses NoOpMetadataWriter when not provided."""
        import pandera.pandas as pa_pandera

        schema = pa_pandera.DataFrameSchema(
            columns={
                "id": pa_pandera.Column(str),
                "value": pa_pandera.Column(int),
            },
            strict=True,
        )

        writer = GoldWriter(
            base_path=tmp_path,
            logger=mock_logger,
            # No metadata_writer provided
        )

        records = [{"id": "record1", "value": 42}]
        ingestion_ts = datetime.now(UTC)
        run_id = RunID(uuid4())

        # Should not raise an error
        await writer.write_gold(
            table_name="test.gold_table",
            records=records,
            schema=schema,
            primary_keys=["id"],
            mode="overwrite",
            ingestion_ts=ingestion_ts,
            run_id=run_id,
        )

        # Verify NoOp was used (no metadata file created)
        metadata_file = tmp_path / "test" / "gold_table" / "_metadata.yaml"
        assert not metadata_file.exists()


class TestNoOpMetadataWriter:
    """Tests for NoOpMetadataWriter behavior."""

    @pytest.mark.asyncio
    async def test_noop_returns_empty_string(self) -> None:
        """Test that NoOpMetadataWriter returns empty strings."""
        noop = NoOpMetadataWriter()

        # Create minimal metadata objects for testing
        from bioetl.domain.models.metadata import (
            EnvironmentMetadata,
            PipelineMetadata,
            RuntimeMetadata,
            RunTypeEnum,
            SilverMetadata,
            DeltaMetrics,
        )

        runtime = RuntimeMetadata(
            run_id="test",
            run_type=RunTypeEnum.INCREMENTAL,
            started_at_utc=datetime.now(UTC),
        )
        pipeline = PipelineMetadata(name="test", provider="test", entity="test")
        environment = EnvironmentMetadata(
            hostname="test", python_version="3.11", bioetl_version="1.0"
        )
        delta = DeltaMetrics(table_path="/test", operation="merge")

        metadata = SilverMetadata(
            runtime=runtime,
            pipeline=pipeline,
            delta=delta,
            environment=environment,
        )

        result = await noop.write_silver_metadata("/tmp/test", metadata)
        assert result == ""
