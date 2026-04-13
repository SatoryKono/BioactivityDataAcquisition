"""Unit tests for file-backed effective-config artifact storage."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest

from bioetl.domain.types import RunID
from bioetl.infrastructure.control_plane import FileEffectiveConfigArtifactStore


def test_file_store_round_trips_payload_by_id_and_run_id(tmp_path: Path) -> None:
    store = FileEffectiveConfigArtifactStore(base_path=tmp_path / "effective_config")
    run_id = RunID(uuid4())
    payload: dict[str, object] = {
        "artifact_id": "effective-config-1",
        "pipeline_name": "chembl_activity",
        "effective_config_hash": "sha256:abc123",
    }

    store.save(
        artifact_id="effective-config-1",
        run_id=run_id,
        payload=payload,
    )

    assert store.get("effective-config-1") == payload
    assert store.get_by_run_id(run_id) == payload


def test_file_store_returns_none_when_item_is_missing(tmp_path: Path) -> None:
    store = FileEffectiveConfigArtifactStore(base_path=tmp_path / "effective_config")
    run_id = RunID(uuid4())

    assert store.get("missing-artifact") is None
    assert store.get_by_run_id(run_id) is None


def test_file_store_rejects_non_object_json_payload(tmp_path: Path) -> None:
    store = FileEffectiveConfigArtifactStore(base_path=tmp_path / "effective_config")
    artifact_file = store.base_path / "bad-artifact.json"
    artifact_file.parent.mkdir(parents=True, exist_ok=True)
    artifact_file.write_text(
        json.dumps(["not", "an", "object"]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="JSON object"):
        store.get("bad-artifact")


def test_file_store_rolls_back_artifact_when_run_index_write_fails(
    tmp_path: Path,
) -> None:
    store = FileEffectiveConfigArtifactStore(base_path=tmp_path / "effective_config")
    run_id = RunID(uuid4())
    payload: dict[str, object] = {
        "artifact_id": "effective-config-rollback",
        "pipeline_name": "chembl_activity",
        "effective_config_hash": "sha256:def456",
    }
    written_paths: list[Path] = []

    def fake_atomic_write_text(path: Path, content: str) -> None:
        written_paths.append(path)
        if len(written_paths) == 1:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return
        raise OSError("simulated run-index write failure")

    with (
        patch(
            "bioetl.infrastructure.control_plane.file_effective_config_artifact_store.atomic_write_text",
            side_effect=fake_atomic_write_text,
        ),
        pytest.raises(OSError, match="simulated run-index write failure"),
    ):
        store.save(
            artifact_id="effective-config-rollback",
            run_id=run_id,
            payload=payload,
        )

    artifact_path = store.base_path / "effective-config-rollback.json"
    run_index_path = store.base_path / "_by_run_id" / f"{run_id}.txt"
    assert not artifact_path.exists()
    assert not run_index_path.exists()


def test_get_by_run_id_returns_none_when_index_points_to_missing_artifact(
    tmp_path: Path,
) -> None:
    store = FileEffectiveConfigArtifactStore(base_path=tmp_path / "effective_config")
    run_id = RunID(uuid4())
    run_index_path = store.base_path / "_by_run_id" / f"{run_id}.txt"
    run_index_path.parent.mkdir(parents=True, exist_ok=True)
    run_index_path.write_text("missing-artifact", encoding="utf-8")

    assert store.get_by_run_id(run_id) is None
