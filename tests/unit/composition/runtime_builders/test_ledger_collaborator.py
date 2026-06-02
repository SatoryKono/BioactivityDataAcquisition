"""Tests for control-plane ledger collaborator attachment."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite

import pytest

from bioetl.application.services.control_plane import RunLedgerService
from bioetl.composition.runtime_builders.ledger_collaborator import (
    attach_control_plane_collaborators,
)
from bioetl.domain.models.metadata import InputSnapshotRef
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter
from tests.helpers.control_plane import InMemoryRunLedgerStore
from tests.unit.infrastructure.storage.test_metadata_writer_control_plane import (
    _make_bronze_metadata,
)


class _Runner:
    def __init__(self, metadata_writer: MetadataWriter) -> None:
        self.services = SimpleNamespace(metadata_writer=metadata_writer)
        self.run_ledger_service: RunLedgerService | None = None

    def attach_run_ledger_service(self, service: RunLedgerService) -> None:
        self.run_ledger_service = service


@pytest.mark.unit
@pytest.mark.asyncio
async def test_artifact_recorder_publishes_bronze_input_snapshot_events(
    tmp_path,
) -> None:
    ledger_store = InMemoryRunLedgerStore()
    run_id = deterministic_run_uuid_from_callsite("test_ledger_collaborator")
    ledger_service = RunLedgerService(
        ledger_port=ledger_store,
        manifest_id="manifest-1",
        run_id=run_id,
    )
    writer = MetadataWriter(logger=NoOpLogger())
    runner = _Runner(writer)
    metadata = _make_bronze_metadata()
    metadata.runtime.run_id = str(run_id)
    metadata.runtime.manifest_id = "manifest-1"
    metadata.source.input_snapshots = [
        InputSnapshotRef(
            snapshot_id="sha256:bronze-live-1",
            content_hash="a" * 64,
            immutable_uri="bronze://chembl/activity/batch-1.jsonl.zst",
            query_fingerprint="f" * 64,
            captured_at=datetime(2026, 5, 19, 12, 0, tzinfo=UTC),
        )
    ]

    attachment = attach_control_plane_collaborators(runner, ledger_service)
    await writer.write_bronze_metadata(
        tmp_path / "bronze" / "chembl" / "activity",
        metadata,
        provider="chembl",
        entity="activity",
    )

    entries = ledger_store.list_entries("manifest-1")
    assert attachment.attached_count == 1
    assert runner.run_ledger_service is ledger_service
    assert [entry.event_type for entry in entries] == [
        "artifact_published",
        "input_snapshot_published",
    ]
    snapshot_entry = entries[1]
    assert snapshot_entry.details["snapshot_id"] == "sha256:bronze-live-1"
    assert snapshot_entry.details["content_hash"] == "a" * 64
    assert snapshot_entry.details["immutable_uri"] == (
        "bronze://chembl/activity/batch-1.jsonl.zst"
    )
