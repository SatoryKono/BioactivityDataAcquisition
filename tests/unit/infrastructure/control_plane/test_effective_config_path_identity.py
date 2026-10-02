"""Equivalent local paths must remain persistable under one semantic identity."""

from __future__ import annotations

import json
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.effective_config.service import (
    create_effective_config_service,
)
from bioetl.domain.normalization.json import stable_json_hash
from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane.file_effective_config_artifact_store import (
    EffectiveConfigArtifactConflictError,
    FileEffectiveConfigArtifactStore,
)

pytestmark = pytest.mark.unit


def _artifact(data_dir: str, bronze_path: str, limit: int = 1000):
    settings = {"settings": {"data_root_mode": "explicit", "data_dir": data_dir}}
    settings["snapshot_hash"] = f"sha256:{stable_json_hash(settings)}"
    service = create_effective_config_service()
    artifact = service.create_effective_config_artifact(
        pipeline_name="chembl_assay",
        pipeline_kind="standard",
        resolved_config={"batch_size": 1000},
        runtime_overrides={
            "cli": {"limit": limit, "cached_bronze": {"bronze_path": bronze_path}},
            "env": {
                "execution_environment": {
                    "settings_snapshot_hash": settings["snapshot_hash"],
                }
            },
            "runtime": {"settings_snapshot": settings},
        },
        source_refs=[],
        required_persistence_profile="degraded_observable",
    )
    return artifact.artifact_id, json.loads(service.serialize_artifact(artifact))


def test_same_identity_across_paths_persists_without_rewriting_evidence(tmp_path):
    first_id, first = _artifact("data", "data/output/bronze")
    second_id, second = _artifact("E:/repo/data", "E:/repo/data/output/bronze")
    assert first_id == second_id
    store = FileEffectiveConfigArtifactStore(base_path=tmp_path)
    first_run = RunID(UUID("00000000-0000-0000-0000-000000000001"))
    second_run = RunID(UUID("00000000-0000-0000-0000-000000000002"))
    store.save(artifact_id=first_id, run_id=first_run, payload=first)
    original = (tmp_path / f"{first_id}.json").read_bytes()
    original_payload = json.dumps(second, sort_keys=True)
    store.save(artifact_id=second_id, run_id=second_run, payload=second)
    assert (tmp_path / f"{first_id}.json").read_bytes() == original
    assert json.dumps(second, sort_keys=True) == original_payload
    assert store.get_occurrence_by_run_id(second_run) is not None


def test_path_normalization_still_rejects_changed_execution_semantics(tmp_path):
    artifact_id, first = _artifact("data", "bronze", limit=1000)
    _, different = _artifact("E:/repo/data", "E:/repo/bronze", limit=2000)
    different["artifact_id"] = artifact_id
    different["semantic_artifact"]["artifact_id"] = artifact_id
    store = FileEffectiveConfigArtifactStore(base_path=tmp_path)
    run_id = RunID(UUID("00000000-0000-0000-0000-000000000003"))
    store.save(artifact_id=artifact_id, run_id=run_id, payload=first)
    with pytest.raises(EffectiveConfigArtifactConflictError):
        store.save(artifact_id=artifact_id, run_id=run_id, payload=different)
