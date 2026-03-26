"""Unit tests for file-backed run-manifest storage."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from bioetl.domain.control_plane import (
    RunArtifactRef,
    RunCodeProvenance,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.control_plane import FileRunManifestStore


def test_file_store_round_trips_manifest_by_id_and_run_id(tmp_path) -> None:
    store = FileRunManifestStore(base_path=tmp_path / "run_manifest")
    run_id = RunID(uuid4())
    manifest = RunManifest(
        manifest_id="manifest-1",
        execution_fingerprint="fingerprint-1",
        schema_version="1.0",
        created_at=datetime.now(UTC),
        run_id=run_id,
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={"limit": 100},
        runtime_config={"run_type": "incremental"},
        resolved_config={"provider": "chembl", "entity_type": "activity"},
        code_provenance=RunCodeProvenance(
            pipeline_version="1.0.0",
            git_commit="abc1234",
            config_hash="deadbeef",
        ),
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="activity",
                pipeline_name="chembl_activity",
            ),
        ),
        planned_artifacts=(
            RunArtifactRef(layer="bronze", path="data/output/bronze/chembl/activity"),
        ),
    )

    store.save(manifest)

    assert store.get("manifest-1") == manifest
    assert store.get_by_run_id(run_id) == manifest


def test_file_store_emits_manifest_write_metric(tmp_path) -> None:
    metrics = MagicMock()
    store = FileRunManifestStore(
        base_path=tmp_path / "run_manifest",
        metrics=metrics,
    )
    manifest = RunManifest(
        manifest_id="manifest-2",
        execution_fingerprint="fingerprint-2",
        schema_version="1.0",
        created_at=datetime.now(UTC),
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context={},
        runtime_config={},
        resolved_config={},
        code_provenance=RunCodeProvenance(),
    )

    store.save(manifest)

    metrics.increment_counter.assert_called_once_with(
        "control_plane_manifest_writes_total",
        1,
        {
            "pipeline": "chembl_activity",
            "run_type": "incremental",
            "status": "success",
        },
    )
