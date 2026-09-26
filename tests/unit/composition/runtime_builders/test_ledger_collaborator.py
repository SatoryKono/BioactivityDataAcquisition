# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for control-plane ledger collaborator attachment."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from tests.helpers.deterministic_ids import deterministic_run_uuid_from_callsite
from typing import Any

import pytest

from bioetl.application.services.control_plane import RunLedgerService
from bioetl.composition.runtime_builders.ledger_collaborator import (
    _attach_artifact_recorder,
    _collect_metadata_writer_candidates,
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


class _BareRunner:
    services = None

    def __init__(self) -> None:
        self.run_ledger_service: object | None = None

    def attach_run_ledger_service(self, service: object) -> None:
        self.run_ledger_service = service


class _RecorderTarget:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.recorder: object | None = None

    def attach_artifact_recorder(self, recorder: object) -> None:
        if self.fail:
            raise RuntimeError("recorder rejected")
        self.recorder = recorder


class _FakeRunLedgerService:
    def __init__(self) -> None:
        self.artifacts: list[dict[str, object]] = []
        self.input_snapshots: list[dict[str, object]] = []

    def record_artifact_published(
        self,
        *,
        layer: str,
        artifact_path: str,
        artifact_content_hash: str,
        dataset_ref: str | None,
        lineage_fragment_id: str | None,
        details: dict[str, object] | None,
    ) -> object:
        entry = {
            "layer": layer,
            "artifact_path": artifact_path,
            "artifact_content_hash": artifact_content_hash,
            "dataset_ref": dataset_ref,
            "lineage_fragment_id": lineage_fragment_id,
            "details": details,
        }
        self.artifacts.append(entry)
        return entry

    def record_input_snapshot_published(self, **kwargs: Any) -> None:
        self.input_snapshots.append(kwargs)


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
        _entry_id_factory=lambda: "entry-bronze-input-snapshot",
        _occurred_at_factory=lambda: datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )
    writer = MetadataWriter(logger=NoOpLogger())
    runner = _Runner(writer)
    metadata = _make_bronze_metadata()
    metadata.runtime.run_id = str(run_id)
    metadata.runtime.manifest_id = "manifest-1"
    metadata.output.content_hash = "b" * 64
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


@pytest.mark.unit
def test_attach_control_plane_collaborators_handles_runner_without_services() -> None:
    runner = _BareRunner()
    ledger_service = _FakeRunLedgerService()

    attachment = attach_control_plane_collaborators(runner, ledger_service)  # type: ignore[arg-type]

    assert runner.run_ledger_service is ledger_service
    assert attachment.candidate_count == 0
    assert attachment.attached_count == 0
    assert attachment.missing_attach_method_count == 0
    assert attachment.failed_count == 0


@pytest.mark.unit
def test_attach_control_plane_collaborators_summarizes_unique_writer_outcomes() -> None:
    attached = _RecorderTarget()
    missing = object()
    failed = _RecorderTarget(fail=True)
    services = SimpleNamespace(
        metadata_writer=attached,
        storage=SimpleNamespace(
            bronze=SimpleNamespace(_metadata_writer=attached),
            silver=SimpleNamespace(_metadata_writer=missing),
            gold=SimpleNamespace(_metadata_writer=failed),
        ),
    )
    runner = SimpleNamespace(
        services=services,
        attach_run_ledger_service=lambda service: None,
    )

    attachment = attach_control_plane_collaborators(
        runner,  # type: ignore[arg-type]
        _FakeRunLedgerService(),  # type: ignore[arg-type]
    )

    assert attachment.candidate_count == 3
    assert attachment.attached_count == 1
    assert attachment.missing_attach_method_count == 1
    assert attachment.failed_count == 1


@pytest.mark.unit
def test_attached_artifact_recorder_records_only_valid_bronze_snapshots() -> None:
    target = _RecorderTarget()
    ledger_service = _FakeRunLedgerService()
    runner = SimpleNamespace(
        services=SimpleNamespace(metadata_writer=target),
        attach_run_ledger_service=lambda service: None,
    )

    attach_control_plane_collaborators(
        runner,  # type: ignore[arg-type]
        ledger_service,  # type: ignore[arg-type]
    )
    assert callable(target.recorder)
    target.recorder(  # type: ignore[operator]
        "bronze",
        "bronze/path",
        {
            "dataset_ref": 42,
            "lineage_fragment_id": "lineage-1",
            "content_hash": "a" * 64,
            "provider": "chembl",
            "entity": "activity",
            "pipeline_name": "chembl_activity",
            "input_snapshots": [
                "not-a-dict",
                {"snapshot_id": "missing-uri", "content_hash": "hash"},
                {
                    "snapshot_id": "snapshot-1",
                    "content_hash": "hash-1",
                    "immutable_uri": "bronze://snapshot-1",
                    "query_fingerprint": None,
                    "extra": "kept",
                },
            ],
        },
    )
    target.recorder("gold", "gold/path", None)  # type: ignore[operator]

    assert ledger_service.artifacts[0]["dataset_ref"] == "42"
    assert ledger_service.artifacts[0]["lineage_fragment_id"] == "lineage-1"
    assert ledger_service.artifacts[1]["dataset_ref"] is None
    assert ledger_service.input_snapshots == [
        {
            "provider": "chembl",
            "entity": "activity",
            "pipeline_name": "chembl_activity",
            "snapshot_id": "snapshot-1",
            "content_hash": "hash-1",
            "immutable_uri": "bronze://snapshot-1",
            "bronze_batch_ref": "bronze/path",
            "query_fingerprint": None,
            "details": {"query_fingerprint": None, "extra": "kept"},
        }
    ]


@pytest.mark.unit
def test_artifact_recorder_ignores_bronze_snapshot_payloads_that_are_not_lists() -> (
    None
):
    target = _RecorderTarget()
    ledger_service = _FakeRunLedgerService()
    runner = SimpleNamespace(
        services=SimpleNamespace(metadata_writer=target),
        attach_run_ledger_service=lambda service: None,
    )

    attach_control_plane_collaborators(
        runner,  # type: ignore[arg-type]
        ledger_service,  # type: ignore[arg-type]
    )
    assert callable(target.recorder)
    target.recorder(  # type: ignore[operator]
        "bronze",
        "bronze/path",
        {
            "provider": "chembl",
            "entity": "activity",
            "pipeline_name": "chembl_activity",
            "content_hash": "b" * 64,
            "input_snapshots": object(),
        },
    )

    assert len(ledger_service.artifacts) == 1
    assert ledger_service.input_snapshots == []


@pytest.mark.unit
def test_attach_artifact_recorder_returns_false_without_attach_method() -> None:
    assert (
        _attach_artifact_recorder(
            object(),
            _FakeRunLedgerService(),  # type: ignore[arg-type]
        )
        is False
    )


@pytest.mark.unit
def test_collect_metadata_writer_candidates_handles_storage_only_slots() -> None:
    storage_writer = _RecorderTarget()
    services = SimpleNamespace(
        storage=SimpleNamespace(
            bronze=None,
            silver=SimpleNamespace(),
            gold=SimpleNamespace(_metadata_writer=storage_writer),
        )
    )

    assert _collect_metadata_writer_candidates(services) == [storage_writer]
