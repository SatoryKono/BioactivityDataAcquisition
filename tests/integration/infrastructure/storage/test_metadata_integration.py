"""Integration tests for metadata writing with Silver and Gold writers."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock
from tests.helpers.deterministic_ids import (
    deterministic_run_uuid_from_callsite,
    deterministic_uuid_string_from_callsite,
)

import pyarrow as pa
import pytest

from bioetl.application.services.lineage import MetadataLineageBundleResult
from bioetl.domain.models.metadata import (
    DeltaMetrics,
    EnvironmentMetadata,
    GoldMetadata,
    PipelineMetadata,
    RuntimeMetadata,
    RunTypeEnum,
    SilverMetadata,
)
from bioetl.infrastructure.storage.gold.runtime_helpers import GoldWriterRuntimeServices
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver.runtime_helpers import (
    SilverWriterRuntimeServicesRequest,
)
from bioetl.infrastructure.storage.silver_writer import SilverWriter
from tests.unit.infrastructure.storage._lineage_fragment_helpers import (
    make_produced_artifact_fragment,
)

pytestmark = pytest.mark.integration


class MockMetadataCoordinator:
    """Mock MetadataCoordinator that creates minimal metadata objects."""

    def create_silver_metadata(self, input_data: Any) -> SilverMetadata:
        """Create minimal SilverMetadata for testing."""
        provider, entity = str(input_data.table_name).split(".", 1)
        runtime = RuntimeMetadata(
            run_id=input_data.records[0].get("_run_id", "test-run-id"),
            run_type=RunTypeEnum.INCREMENTAL,
            started_at_utc=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
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
            started_at_utc=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )
        pipeline = PipelineMetadata(name="test", provider=provider, entity=entity)
        environment = EnvironmentMetadata(
            hostname="test", python_version="3.11", bioetl_version="1.0"
        )
        output = BaseOutputMetadata(record_count=len(input_data.records))
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
    ) -> MetadataLineageBundleResult[SilverMetadata]:
        """Wrap Silver metadata in the canonical bundle contract."""
        return MetadataLineageBundleResult(
            metadata=self.create_silver_metadata(input_data),
            lineage_fragment=make_produced_artifact_fragment(
                fragment_id="silver:integration-fragment",
                layer="silver",
                logical_name="test.table",
            ),
        )

    def create_gold_metadata_bundle(
        self, input_data: Any
    ) -> MetadataLineageBundleResult[GoldMetadata]:
        """Wrap Gold metadata in the canonical bundle contract."""
        return MetadataLineageBundleResult(
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
        del base_path, metadata, provider, entity
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
        del table_name, flat_structure, provider, entity
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
        del table_name, flat_structure, provider, entity
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
        del (
            table_name,
            flat_structure,
            provider,
            entity,
            dq_report_path,
            completed_at,
            delta_version_after,
        )
        await asyncio.sleep(0)
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
        del (
            table_name,
            flat_structure,
            provider,
            entity,
            dq_report_path,
            completed_at,
        )
        await asyncio.sleep(0)
        return str(Path(base_path) / "_metadata.yaml")

    async def aclose(self) -> None:
        await asyncio.sleep(0)


@pytest.fixture
def mock_logger() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_metadata_writer() -> MockMetadataWriter:
    return MockMetadataWriter()


@pytest.fixture
def mock_metadata_coordinator() -> MockMetadataCoordinator:
    return MockMetadataCoordinator()


@pytest.fixture
def sample_records() -> list[dict[str, Any]]:
    run_id = deterministic_uuid_string_from_callsite("test_metadata_integration")
    batch_id = deterministic_uuid_string_from_callsite("test_metadata_integration")
    return [
        {
            "id": "record1",
            "value": 42,
            "_run_id": run_id,
            "_run_type": "incremental",
            "_source_batch_id": batch_id,
            "_ingestion_ts": datetime(2026, 1, 1, 12, 0, tzinfo=UTC).isoformat(),
        },
        {
            "id": "record2",
            "value": 43,
            "_run_id": run_id,
            "_run_type": "incremental",
            "_source_batch_id": batch_id,
            "_ingestion_ts": datetime(2026, 1, 1, 12, 0, tzinfo=UTC).isoformat(),
        },
    ]


@pytest.fixture
def silver_schema() -> pa.Schema:
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
    """Create a mock metadata coordinator returning mock metadata objects."""
    mock = MagicMock()
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
        side_effect=lambda input_data: MetadataLineageBundleResult(
            metadata=mock_silver_metadata,
            lineage_fragment=make_produced_artifact_fragment(
                fragment_id="silver:integration-mock-fragment",
                layer="silver",
                logical_name=getattr(input_data, "table_name", "test.table"),
            ),
        )
    )

    mock_gold_metadata = MagicMock(spec=GoldMetadata)
    mock_gold_metadata.runtime = MagicMock()
    mock_gold_metadata.runtime.run_id = sample_records[0]["_run_id"]
    mock_gold_metadata.delta = MagicMock()
    mock_gold_metadata.delta.rows_inserted = len(sample_records)
    mock_gold_metadata.delta.operation = "overwrite"
    mock.create_gold_metadata.return_value = mock_gold_metadata
    mock.create_gold_metadata_bundle = MagicMock(
        side_effect=lambda input_data: MetadataLineageBundleResult(
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
        writer = SilverWriter(
            base_path=tmp_path,
            logger=mock_logger,
            runtime_request=SilverWriterRuntimeServicesRequest(
                metadata_writer=mock_metadata_writer,
                metadata_coordinator=mock_metadata_coordinator_with_records,
            ),
        )

        await writer.write_silver(
            table_name="test.table",
            records=sample_records,
            primary_keys=["id"],
            schema=silver_schema,
            mode="merge",
        )

        assert len(mock_metadata_writer.silver_calls) == 1
        table_path, metadata = mock_metadata_writer.silver_calls[0]
        assert Path(table_path) == tmp_path / "test" / "table"
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
        writer = SilverWriter(
            base_path=tmp_path,
            logger=mock_logger,
        )

        await writer.write_silver(
            table_name="test.table",
            records=sample_records,
            primary_keys=["id"],
            schema=silver_schema,
            mode="merge",
        )

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
            runtime_services=GoldWriterRuntimeServices(
                csv_exporter=None,
                tracing=MagicMock(),
                metrics=None,
                audit=None,
                metadata_writer=mock_metadata_writer,
                metadata_coordinator=mock_metadata_coordinator,
                lineage_store=None,
            ),
        )

        records = [
            {"id": "record1", "value": 42},
            {"id": "record2", "value": 43},
        ]

        await writer.write_gold(
            table_name="test.gold_table",
            records=records,
            schema=schema,
            primary_keys=["id"],
            mode="overwrite",
            ingestion_ts=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            run_id=deterministic_run_uuid_from_callsite("test_metadata_integration"),
        )

        assert len(mock_metadata_writer.gold_calls) == 1
        table_path, metadata = mock_metadata_writer.gold_calls[0]
        assert Path(table_path) == tmp_path / "test" / "gold_table"
        assert metadata.output.record_count == 2
        assert metadata.pipeline.provider == "test"
        assert metadata.pipeline.entity == "gold_table"

    @pytest.mark.asyncio
    async def test_gold_writer_uses_noop_when_no_metadata_writer(
        self,
        tmp_path: Path,
        mock_logger: MagicMock,
    ) -> None:
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
        )

        await writer.write_gold(
            table_name="test.gold_table",
            records=[{"id": "record1", "value": 42}],
            schema=schema,
            primary_keys=["id"],
            mode="overwrite",
            ingestion_ts=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            run_id=deterministic_run_uuid_from_callsite("test_metadata_integration"),
        )

        metadata_file = tmp_path / "test" / "gold_table" / "_metadata.yaml"
        assert not metadata_file.exists()
