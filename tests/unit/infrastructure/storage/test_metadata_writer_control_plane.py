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
    DeltaMetrics,
    DQSummary,
    EnvironmentMetadata,
    FileOutputMetadata,
    InputSnapshotRef,
    LineageMetadata,
    PipelineMetadata,
    RuntimeMetadata,
    RunTypeEnum,
    SilverMetadata,
    SilverOutputExt,
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
        output=BaseOutputMetadata(
            artifact_id="bronze_batch:batch-1",
            record_count=7,
            total_bytes=1024,
            lineage_fragment_id="bronze:fragment-1",
        ),
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


def _make_silver_metadata() -> SilverMetadata:
    return SilverMetadata(
        version="1.1",
        layer=Layer.SILVER,
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
        lineage=LineageMetadata(),
        delta=DeltaMetrics(
            table_path="silver/chembl/activity",
            operation="merge",
            primary_key=["id"],
            version_after=7,
        ),
        dq_summary=DQSummary(total_records=7, valid_records=7),
        output=BaseOutputMetadata(
            artifact_id="silver:chembl.activity@7",
            record_count=7,
            total_bytes=2048,
            lineage_fragment_id="silver:fragment-1",
        ),
        output_ext=SilverOutputExt(delta_version_after=7),
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
    metadata = _make_bronze_metadata()
    writer.attach_artifact_recorder(
        lambda layer, artifact_path, details=None: captured.append(
            (layer, artifact_path, details)
        )
    )

    base_path = tmp_path / "output" / "bronze" / "chembl" / "activity"
    result = await writer.write_bronze_metadata(
        base_path=base_path,
        metadata=metadata,
        provider="chembl",
        entity="activity",
    )

    assert result.endswith("chembl_activity_metadata.yaml")
    assert len(captured) == 1
    layer, artifact_path, details = captured[0]
    assert layer == "bronze"
    assert artifact_path == str(base_path.resolve())
    assert details is not None
    assert details["artifact_id"] == "bronze_batch:batch-1"
    assert details["metadata_path"].endswith("chembl_activity_metadata.yaml")
    assert details["record_count"] == 7
    assert details["run_id"] == str(metadata.runtime.run_id)
    assert details["manifest_id"] == "manifest-1"
    assert details["provider"] == "chembl"
    assert details["dataset_ref"] is None
    assert details["lineage_fragment_id"] == "bronze:fragment-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_bronze_metadata_records_input_snapshot_refs(tmp_path) -> None:
    writer = MetadataWriter(logger=NoOpLogger())
    captured: list[tuple[str, str, dict[str, object] | None]] = []
    metadata = _make_bronze_metadata()
    metadata.source.input_snapshots = [
        InputSnapshotRef(
            snapshot_id="chembl-activity-batch-001",
            content_hash="a" * 64,
            immutable_uri="snapshots/chembl/activity/batch-001.jsonl.zst",
            query_fingerprint="f" * 64,
        )
    ]
    writer.attach_artifact_recorder(
        lambda layer, artifact_path, details=None: captured.append(
            (layer, artifact_path, details)
        )
    )

    await writer.write_bronze_metadata(
        base_path=tmp_path / "output" / "bronze" / "chembl" / "activity",
        metadata=metadata,
        provider="chembl",
        entity="activity",
    )

    assert len(captured) == 1
    details = captured[0][2]
    assert details is not None
    assert details["input_snapshot_count"] == 1
    assert details["input_snapshot_ids"] == ["chembl-activity-batch-001"]
    assert details["input_snapshot_content_hashes"] == ["a" * 64]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_silver_metadata_records_dataset_ref_and_fragment_id(
    tmp_path,
) -> None:
    writer = MetadataWriter(logger=NoOpLogger())
    captured: list[tuple[str, str, dict[str, object] | None]] = []
    metadata = _make_silver_metadata()
    writer.attach_artifact_recorder(
        lambda layer, artifact_path, details=None: captured.append(
            (layer, artifact_path, details)
        )
    )

    base_path = tmp_path / "output" / "silver" / "chembl" / "activity"
    result = await writer.write_silver_metadata(
        base_path=base_path,
        metadata=metadata,
        provider="chembl",
        entity="activity",
    )

    assert result.endswith("chembl_activity_metadata.yaml")
    assert len(captured) == 1
    layer, artifact_path, details = captured[0]
    assert layer == "silver"
    assert artifact_path == str(base_path.resolve())
    assert details is not None
    assert details["run_id"] == str(metadata.runtime.run_id)
    assert details["manifest_id"] == "manifest-1"
    assert details["artifact_id"] == "silver:chembl.activity@7"
    assert details["dataset_ref"] == "silver:chembl.activity@7"
    assert details["lineage_fragment_id"] == "silver:fragment-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_metadata_fails_when_control_plane_manifest_id_is_missing(
    tmp_path,
) -> None:
    writer = MetadataWriter(logger=NoOpLogger())
    writer.attach_artifact_recorder(lambda *_args, **_kwargs: None)
    metadata = _make_bronze_metadata()
    metadata.runtime.manifest_id = None

    with pytest.raises(
        RuntimeError,
        match="Control-plane artifact publication requires metadata.runtime.manifest_id",
    ):
        await writer.write_bronze_metadata(
            base_path=tmp_path / "output" / "bronze" / "chembl" / "activity",
            metadata=metadata,
            provider="chembl",
            entity="activity",
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_write_metadata_fails_when_control_plane_artifact_id_is_missing(
    tmp_path,
) -> None:
    writer = MetadataWriter(logger=NoOpLogger())
    writer.attach_artifact_recorder(lambda *_args, **_kwargs: None)
    metadata = _make_bronze_metadata()
    metadata.output.artifact_id = None

    with pytest.raises(
        RuntimeError,
        match="Control-plane artifact publication requires metadata.output.artifact_id",
    ):
        await writer.write_bronze_metadata(
            base_path=tmp_path / "output" / "bronze" / "chembl" / "activity",
            metadata=metadata,
            provider="chembl",
            entity="activity",
        )
