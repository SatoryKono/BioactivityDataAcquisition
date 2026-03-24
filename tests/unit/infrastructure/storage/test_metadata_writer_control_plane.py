"""Focused tests for MetadataWriter control-plane artifact recording."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from bioetl.domain.medallion import Layer
from bioetl.domain.models.metadata import (
    BaseOutputMetadata,
    BronzeMetadata,
    BronzeOutputExt,
    EnvironmentMetadata,
    FileOutputMetadata,
    PipelineMetadata,
    RuntimeMetadata,
    RunTypeEnum,
    SourceMetadata,
)
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter


def _make_bronze_metadata() -> BronzeMetadata:
    return BronzeMetadata(
        version="1.1",
        layer=Layer.BRONZE,
        runtime=RuntimeMetadata(
            run_id=str(uuid4()),
            manifest_id="manifest-1",
            run_type=RunTypeEnum.INCREMENTAL,
            started_at_utc=datetime(2026, 3, 24, 10, 0, tzinfo=UTC),
        ),
        pipeline=PipelineMetadata(
            name="chembl_activity",
            provider="chembl",
            entity="activity",
            version="1.0.0",
        ),
        source=SourceMetadata(type="api", url="https://example.org"),
        output=BaseOutputMetadata(record_count=7, total_bytes=1024),
        output_ext=BronzeOutputExt(
            files=[
                FileOutputMetadata(
                    path="batch.jsonl.zst",
                    size_bytes=1024,
                    record_count=7,
                )
            ]
        ),
        environment=EnvironmentMetadata(
            hostname="host",
            python_version="3.13.0",
            bioetl_version="6.0.0",
        ),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_bronze_metadata_records_artifact_publication(tmp_path) -> None:
    writer = MetadataWriter(logger=NoOpLogger())
    captured: list[tuple[str, str, dict[str, object] | None]] = []
    writer.attach_artifact_recorder(
        lambda layer, artifact_path, details=None: captured.append(
            (layer, artifact_path, details)
        )
    )

    base_path = tmp_path / "output" / "bronze" / "chembl" / "activity"
    result = await writer.write_bronze_metadata(
        base_path=base_path,
        metadata=_make_bronze_metadata(),
        provider="chembl",
        entity="activity",
    )

    assert result.endswith("chembl_activity_metadata.yaml")
    assert len(captured) == 1
    layer, artifact_path, details = captured[0]
    assert layer == "bronze"
    assert artifact_path == str(base_path.resolve())
    assert details is not None
    assert details["metadata_path"].endswith("chembl_activity_metadata.yaml")
    assert details["record_count"] == 7
    assert details["provider"] == "chembl"
