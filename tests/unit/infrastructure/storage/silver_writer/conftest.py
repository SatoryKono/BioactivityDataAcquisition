"""Shared fixtures for split SilverWriter unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from tests.unit.infrastructure.storage._lineage_fragment_helpers import (
    make_produced_artifact_fragment,
)


@pytest.fixture
def noop_logger() -> NoOpLogger:
    """Provide a local no-op logger fixture for split SilverWriter suites."""
    return NoOpLogger()


@pytest.fixture
def valid_records():
    """Create valid records with all required metadata."""
    return [
        {
            "entity_id": "CHEMBL123",
            "value": 5.5,
            "_run_id": "uuid-123",
            "_run_type": "incremental",
            "_source_batch_id": "batch-456",
            "_ingestion_ts": "2025-01-15T12:00:00Z",
        },
        {
            "entity_id": "CHEMBL456",
            "value": 7.2,
            "_run_id": "uuid-123",
            "_run_type": "incremental",
            "_source_batch_id": "batch-456",
            "_ingestion_ts": "2025-01-15T12:00:00Z",
        },
    ]


@pytest.fixture
def mock_metadata_coordinator():
    """Create a mock MetadataCoordinator that returns proper SilverMetadata."""
    from datetime import UTC, datetime

    from bioetl.application.services.lineage import (
        MetadataLineageBundleResult,
    )
    from bioetl.domain.models.metadata import (
        BaseOutputMetadata,
        DeltaMetrics,
        DQSummary,
        EnvironmentMetadata,
        LineageMetadata,
        PipelineMetadata,
        RuntimeMetadata,
        RunTypeEnum,
        SilverMetadata,
        SilverOutputExt,
    )
    from bioetl.domain.ports import SilverMetadataInput

    coordinator = MagicMock()

    def create_silver_metadata(input_data: SilverMetadataInput) -> SilverMetadata:
        """Create a proper SilverMetadata object from input."""
        bronze_paths = []
        if input_data.bronze_refs:
            bronze_paths = [ref.relative_path for ref in input_data.bronze_refs]

        source_batch_ids = list(
            {
                r.get("_source_batch_id", "")
                for r in input_data.records
                if r.get("_source_batch_id")
            }
        )

        return SilverMetadata(
            runtime=RuntimeMetadata(
                run_id="test-run-id",
                run_type=RunTypeEnum.INCREMENTAL,
                started_at_utc=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            ),
            pipeline=PipelineMetadata(
                name="test_pipeline",
                provider="test",
                entity="table",
            ),
            lineage=LineageMetadata(
                source_batch_ids=source_batch_ids,
                bronze_paths=bronze_paths,
            ),
            delta=DeltaMetrics(
                table_path=input_data.table_path,
                operation="merge",
                primary_key=input_data.primary_keys,
            ),
            dq_summary=input_data.dq_metrics.to_dq_summary()
            if input_data.dq_metrics
            else DQSummary(
                total_records=len(input_data.records),
                valid_records=len(input_data.records),
            ),
            output=BaseOutputMetadata(record_count=len(input_data.records)),
            output_ext=SilverOutputExt(
                delta_version_after=input_data.version_after,
            ),
            environment=EnvironmentMetadata(
                hostname="test-host",
                python_version="3.11.0",
                bioetl_version="1.0.0",
            ),
        )

    coordinator.create_silver_metadata = create_silver_metadata
    coordinator.create_silver_metadata_bundle = lambda input_data: (
        MetadataLineageBundleResult(
            metadata=create_silver_metadata(input_data),
            lineage_fragment=make_produced_artifact_fragment(
                fragment_id="silver:fixture-fragment",
                layer="silver",
                logical_name="test.table",
            ),
        )
    )
    return coordinator
