"""Focused coverage for composition residuals moved in #11250."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.control_plane.ledger.artifact_recording import (
    canonical_lineage_fragment_id,
    record_input_snapshots_from_artifact,
)
from bioetl.infrastructure.control_plane.provider_health_evidence import (
    persist_probe_health_observation,
)


def test_lineage_fragment_id_rejects_layer_alias() -> None:
    assert canonical_lineage_fragment_id("bronze") is None
    assert canonical_lineage_fragment_id("frag-1") == "frag-1"


def test_bronze_snapshots_update_manifest_capability() -> None:
    from uuid import UUID

    from bioetl.domain.control_plane import ReplayCapability, RunManifest, RunSourceRef
    from bioetl.domain.types import RunID, RunType

    manifest = RunManifest(
        manifest_id="m1",
        execution_fingerprint="legacy-fingerprint",
        run_id=RunID(UUID(int=1)),
        run_type=RunType.BACKFILL,
        pipeline_name="chembl_tissue",
        provider="chembl",
        entity="tissue",
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="tissue",
                pipeline_name="chembl_tissue",
            ),
        ),
        replay_capability=ReplayCapability.REBUILD_ONLY,
    )
    port = MagicMock()
    port.get.return_value = manifest
    service = MagicMock()
    service.manifest_port = port
    service.manifest_id = "m1"
    record_input_snapshots_from_artifact(
        service,
        layer="bronze",
        artifact_path="bronze/batch",
        details={
            "provider": "chembl",
            "entity": "tissue",
            "pipeline_name": "chembl_tissue",
            "input_snapshots": [
                {
                    "snapshot_id": "snap-1",
                    "content_hash": "abc",
                    "immutable_uri": "bronze://chembl/tissue/2026-09-27",
                }
            ],
        },
    )
    service.record_input_snapshot_published.assert_called_once()
    port.save.assert_called_once()
    saved = port.save.call_args[0][0]
    assert saved.replay_capability == ReplayCapability.EXACT_REPLAY_SUPPORTED
    assert saved.source_refs[0].input_snapshots[0].snapshot_id == "snap-1"
    assert saved.source_refs[0].input_snapshots[0].content_hash == "abc"


def test_bronze_attach_records_verified_snapshot_object(tmp_path) -> None:
    from uuid import UUID

    from bioetl.domain.control_plane import ReplayCapability, RunManifest, RunSourceRef
    from bioetl.domain.types import RunID, RunType

    batch = tmp_path / "bronze-batch.json"
    batch.write_text("{}", encoding="utf-8")
    manifest = RunManifest(
        manifest_id="m1",
        execution_fingerprint="legacy-fingerprint",
        run_id=RunID(UUID(int=1)),
        run_type=RunType.BACKFILL,
        pipeline_name="chembl_tissue",
        provider="chembl",
        entity="tissue",
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="tissue",
                pipeline_name="chembl_tissue",
            ),
        ),
        replay_capability=ReplayCapability.REBUILD_ONLY,
    )
    port = MagicMock()
    port.get.return_value = manifest
    service = MagicMock()
    service.manifest_port = port
    service.manifest_id = "m1"
    record_input_snapshots_from_artifact(
        service,
        layer="bronze",
        artifact_path=str(batch),
        details={
            "provider": "chembl",
            "entity": "tissue",
            "pipeline_name": "chembl_tissue",
            "input_snapshots": [
                {
                    "snapshot_id": "snap-1",
                    "content_hash": "abc",
                    "immutable_uri": str(batch),
                }
            ],
        },
    )
    port.save.assert_called_once()
    saved = port.save.call_args[0][0]
    assert dict(saved.objects) == {"input_snapshot_fingerprint": True}


def test_bronze_attach_without_batch_file_leaves_objects_unset(tmp_path) -> None:
    from uuid import UUID

    from bioetl.domain.control_plane import ReplayCapability, RunManifest, RunSourceRef
    from bioetl.domain.types import RunID, RunType

    manifest = RunManifest(
        manifest_id="m1",
        execution_fingerprint="legacy-fingerprint",
        run_id=RunID(UUID(int=1)),
        run_type=RunType.BACKFILL,
        pipeline_name="chembl_tissue",
        provider="chembl",
        entity="tissue",
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="tissue",
                pipeline_name="chembl_tissue",
            ),
        ),
        replay_capability=ReplayCapability.REBUILD_ONLY,
    )
    port = MagicMock()
    port.get.return_value = manifest
    service = MagicMock()
    service.manifest_port = port
    service.manifest_id = "m1"
    record_input_snapshots_from_artifact(
        service,
        layer="bronze",
        artifact_path=str(tmp_path / "absent-batch.json"),
        details={
            "provider": "chembl",
            "entity": "tissue",
            "pipeline_name": "chembl_tissue",
            "input_snapshots": [
                {
                    "snapshot_id": "snap-1",
                    "content_hash": "abc",
                    "immutable_uri": str(tmp_path / "absent-batch.json"),
                }
            ],
        },
    )
    port.save.assert_called_once()
    saved = port.save.call_args[0][0]
    assert dict(saved.objects) == {}


def test_input_snapshot_requires_snapshot_id() -> None:
    service = MagicMock()
    with pytest.raises(ValueError, match="snapshot_id"):
        record_input_snapshots_from_artifact(
            service,
            layer="bronze",
            artifact_path="bronze/batch",
            details={
                "input_snapshots": [
                    {"immutable_uri": "s3://snap", "content_hash": "abc"}
                ]
            },
        )
    service.record_input_snapshot_published.assert_not_called()


def test_probe_health_observation_persists_known_status() -> None:
    store = MagicMock()
    store.list_all.return_value = []
    metrics = MagicMock()
    checked = datetime(2026, 1, 1, tzinfo=UTC)
    persist_probe_health_observation(
        store=store,
        metrics=metrics,
        provider="chembl",
        status_name="healthy",
        checked_at=checked,
        endpoint="https://example.test/health",
        error=None,
        now=checked,
    )
    store.persist.assert_called_once()
    store.list_all.assert_called()
