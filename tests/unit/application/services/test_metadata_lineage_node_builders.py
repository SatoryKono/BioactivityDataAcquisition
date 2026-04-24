"""Unit tests for metadata lineage node builders."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from bioetl.application.services.lineage.metadata_lineage_node_builders import (
    fragment_timestamp,
    source_request_node,
    source_system_node,
)
from bioetl.domain.models.metadata import InputSnapshotRef, SourceMetadata
from bioetl.domain.ports import BronzeMetadataInput
from bioetl.domain.types import BatchID, RunID, RunType
from bioetl.domain.value_objects.run_context import RunContext


def _make_run_context() -> RunContext:
    return RunContext.create(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        started_at=datetime.now(UTC),
        provider="chembl",
        entity="activity",
    )


def _make_source_metadata() -> SourceMetadata:
    return SourceMetadata(
        type="api",
        url="https://www.ebi.ac.uk/chembl/api/data/activity",
        api_version="v1",
        input_snapshots=[
            InputSnapshotRef(
                snapshot_id="chembl-activity-batch-001",
                content_hash="a" * 64,
                immutable_uri="snapshots/chembl/activity/batch-001.jsonl.zst",
                query_fingerprint="f" * 64,
            )
        ],
    )


def test_source_system_node_exposes_snapshot_count() -> None:
    node = source_system_node(
        run_context=_make_run_context(),
        source_metadata=_make_source_metadata(),
    )

    assert node.attributes["input_snapshot_count"] == 1


def test_source_request_node_exposes_snapshot_identity() -> None:
    source_metadata = _make_source_metadata()
    node = source_request_node(
        run_context=_make_run_context(),
        input_data=BronzeMetadataInput(
            batch_id=BatchID(uuid4()),
            record_count=10,
            compressed_size=512,
            output_path="v1/chembl/activity/2026-04-09/batch.jsonl.zst",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            source_metadata=source_metadata,
            query_string="assay_type=B",
        ),
    )

    assert node is not None
    assert node.attributes["input_snapshot_count"] == 1
    assert node.attributes["input_snapshot_ids"] == ["chembl-activity-batch-001"]
    assert node.attributes["input_snapshot_content_hashes"] == ["a" * 64]


def test_fragment_timestamp_falls_back_to_sanctioned_time_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(
        "bioetl.application.services.lineage.metadata_lineage_node_builders.current_utc_time",
        lambda: fixed_now,
    )

    assert fragment_timestamp(None, None) == fixed_now
